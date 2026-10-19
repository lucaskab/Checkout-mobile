import { plugin } from "bun";
import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

plugin({
	name: "png-as-id",
	setup(build) {
		build.onLoad({ filter: /\.png$/ }, (args) => ({
			contents: `const path = ${JSON.stringify(args.path)}; export default path; export const toString = () => path;`,
			loader: "js",
		}));
	},
});

// Cloud saves on the host (desktop/cloud.ts, page "conta"): Unity signs in and uploads; the host exports and
// imports the save and draws the page.
globalThis.__DEV__ = false;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../src/stores/game-store.ts");
const { pages } = await import("./pages/index.ts");
const cloud = await import("./cloud.ts");

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => {
	useGameStore.setState(JSON.parse(initial));
	cloud.resetCloudStore();
});
afterAll(() => {
	useGameStore.setState(JSON.parse(initial));
	cloud.resetCloudStore();
});
const store = () => useGameStore.getState();
const buttons = (route) => pages(store(), route).cards.flatMap((c) => c.buttons);

describe("the save goes to the cloud and comes back", () => {
	test("export: the whole persisted save and what it holds", () => {
		useGameStore.setState({ coins: 12345, logistics: { ...store().logistics, premiumCurrency: 321 }, market: { ...store().market, level: 9 } });
		const exported = cloud.exportSave();
		const parsed = JSON.parse(exported.data);
		expect(parsed.version).toBe(45);
		expect(parsed.state.coins).toBe(12345);
		expect(parsed.state.logistics.premiumCurrency).toBe(321);
		expect(exported.summary).toMatchObject({ level: 9, coins: 12345, diamonds: 321, version: 45 });
		expect(exported.fresh).toBe(false);
		// Only persisted fields travel (no transient UI state such as a diamond shortfall).
		expect("diamondShortfall" in parsed.state).toBe(false);
	});

	test("import: another phone's progress replaces this one's (coins, diamonds, level)", async () => {
		useGameStore.setState({ coins: 777, logistics: { ...store().logistics, premiumCurrency: 999 }, market: { ...store().market, level: 12 } });
		const other = cloud.exportSave().data;
		useGameStore.setState(JSON.parse(initial));
		expect(store().coins).not.toBe(777);
		expect(await cloud.importSave(other)).toBe(true);
		expect(store().coins).toBeGreaterThanOrEqual(777);
		expect(store().logistics.premiumCurrency).toBe(999);
		expect(store().market.level).toBe(12);
	});

	test("the save holds everything the player has (a new phone continues exactly where the old one was)", () => {
		const saved = Object.keys(JSON.parse(cloud.exportSave().data).state);
		const data = Object.entries(store())
			.filter(([, value]) => typeof value !== "function")
			.map(([key]) => key);
		// Left out on purpose: a store page waiting to open (not progress).
		const transient = ["diamondShortfall"];
		expect(data.filter((key) => !saved.includes(key) && !transient.includes(key))).toEqual([]);
	});

	test("trucks waiting at the dock survive a reload (they were lost before 12/10)", async () => {
		globalThis.__DEV__ = true;
		expect(store().devArriveDelivery(1, 30)).toBe(true);
		globalThis.__DEV__ = false;
		const dock = store().receiving.dock.length;
		expect(dock).toBeGreaterThan(0);
		const data = cloud.exportSave().data;
		useGameStore.setState({ receiving: { ...store().receiving, dock: [] } });
		expect(await cloud.importSave(data)).toBe(true);
		expect(store().receiving.dock.length).toBe(dock);
	});

	test("import refuses what is not a save and keeps the progress", async () => {
		useGameStore.setState({ coins: 4242 });
		for (const bad of ["", "{", "[]", JSON.stringify({ version: 1 }), 42]) expect(await cloud.importSave(bad)).toBe(false);
		expect(store().coins).toBe(4242);
	});

	test("a new game is fresh (a new phone takes the cloud's progress without asking) — unless something was bought", () => {
		expect(cloud.exportSave().fresh).toBe(true);
		useGameStore.setState({ currencyPurchases: { ...store().currencyPurchases, processedTransactionIds: ["tx-1"] } });
		expect(cloud.exportSave().fresh).toBe(false);
		useGameStore.setState(JSON.parse(initial));
		useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency: 230 } });
		expect(cloud.exportSave().fresh).toBe(false);
	});
});

describe("the Conta page", () => {
	test("this version without the login: the button is off", () => {
		const signIn = buttons("conta").find((b) => b.action === "cloudSignIn");
		expect(signIn.enabled).toBe(false);
		expect(cloud.requestCloudAction("cloudSignIn", []).ok).toBe(false);
	});

	test("signed out → Entrar com Google sends the login to Unity", () => {
		cloud.applyCloudMessage({ kind: "cloud", status: "signed-out" });
		expect(buttons("conta").find((b) => b.action === "cloudSignIn").enabled).toBe(true);
		expect(cloud.requestCloudAction("cloudSignIn", [])).toEqual({ ok: true, message: { kind: "cloud-signin", provider: "google" } });
		expect(cloud.requestCloudAction("cloudSync", []).ok).toBe(false);
	});

	test("iPhone: Entrar com a Apple next to Google; only the logins the device offers", () => {
		cloud.applyCloudMessage({ kind: "cloud", status: "signed-out", providers: ["apple", "google"] });
		const signIns = buttons("conta").filter((b) => b.action === "cloudSignIn");
		expect(signIns.map((b) => b.label)).toEqual(["Iniciar sessão com a Apple", "Entrar com Google"]);
		expect(cloud.requestCloudAction("cloudSignIn", ["apple"])).toEqual({ ok: true, message: { kind: "cloud-signin", provider: "apple" } });
		cloud.applyCloudMessage({ kind: "cloud", status: "signed-out", providers: ["google"] });
		expect(cloud.requestCloudAction("cloudSignIn", ["apple"]).ok).toBe(false);
		cloud.applyCloudMessage({ kind: "cloud", status: "synced", provider: "apple", name: "", email: "" });
		expect(pages(store(), "conta").cards[0].title).toBe("Conta Apple");
		cloud.applyCloudMessage({ kind: "cloud", status: "signed-out", providers: [] });
	});

	test("signed in: who, when it was saved, save now, sign out; deleting asks twice", () => {
		const now = Date.now();
		cloud.applyCloudMessage({ kind: "cloud", status: "synced", email: "ana@example.com", name: "Ana", lastSyncAt: now - 3 * 60_000 });
		const page = pages(store(), "conta");
		expect(page.cards[0].title).toBe("Ana");
		expect(page.cards[0].subtitle).toBe("ana@example.com");
		expect(page.cards[0].lines[0]).toBe("Tudo salvo na nuvem · há 3 minutos");
		expect(cloud.requestCloudAction("cloudSync", []).message).toEqual({ kind: "cloud-sync" });
		expect(cloud.requestCloudAction("cloudDeleteAccount", [], now)).toEqual({ ok: false, reason: "Toque de novo para apagar a conta de vez." });
		expect(cloud.requestCloudAction("cloudDeleteAccount", [], now + 2_000).message).toEqual({ kind: "cloud-delete" });
		// After 10 s the first press no longer counts.
		cloud.requestCloudAction("cloudDeleteAccount", [], now);
		expect(cloud.requestCloudAction("cloudDeleteAccount", [], now + 11_000).ok).toBe(false);
		cloud.applyCloudMessage({ kind: "cloud", status: "signed-out" });
		expect(cloud.cloudStore.email).toBe("");
	});

	test("conflict: both progresses side by side, the further one recommended, one button each", () => {
		useGameStore.setState({ market: { ...store().market, level: 3 } });
		cloud.applyCloudMessage({
			kind: "cloud",
			status: "conflict",
			conflict: { cloud: { level: 8, era: "mercadinho", coins: 50000, diamonds: 120, day: 14, version: 45 }, cloudAt: Date.now() - 3600_000, cloudDevice: "x" },
		});
		const page = pages(store(), "conta");
		const cloudCard = page.cards.find((c) => c.title === "Progresso da nuvem");
		const deviceCard = page.cards.find((c) => c.title === "Progresso deste aparelho");
		expect(cloudCard.badge).toBe("Mais avançado");
		expect(deviceCard.badge).toBe("");
		expect(cloudCard.lines[0]).toContain("Nível 8");
		expect(cloudCard.eyebrow).toBe("SALVO HÁ 1 HORA");
		expect(JSON.parse(cloudCard.buttons[0].args)).toEqual(["cloud"]);
		expect(cloud.requestCloudAction("cloudResolve", ["device"]).message).toEqual({ kind: "cloud-resolve", keep: "device" });
		expect(cloud.requestCloudAction("cloudResolve", ["other"]).ok).toBe(false);
		// Another Google account's progress on this device: said so.
		cloud.applyCloudMessage({ kind: "cloud", status: "conflict", conflict: { cloud: { level: 2, era: "", coins: 1, diamonds: 1, day: 2, version: 45 }, otherAccount: true } });
		expect(pages(store(), "conta").cards[0].lines[0]).toContain("outra conta Google");
	});

	test("the Guia shows where the progress is saved and opens the Conta page", () => {
		cloud.applyCloudMessage({ kind: "cloud", status: "offline", email: "a@b.c" });
		const guide = pages(store(), "guia").cards[0];
		expect(guide.title).toBe("Conta e nuvem");
		expect(guide.lines[0]).toContain("Sem conexão");
		expect(guide.buttons[0].route).toBe("conta");
	});
});
