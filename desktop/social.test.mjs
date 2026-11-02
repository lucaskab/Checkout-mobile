import { plugin } from "bun";
import { afterAll, beforeAll, expect, mock, test } from "bun:test";

plugin({
	name: "png-as-id",
	setup(build) {
		build.onLoad({ filter: /\.png$/ }, (args) => ({
			contents: `const path = ${JSON.stringify(args.path)}; export default path; export const toString = () => path;`,
			loader: "js",
		}));
	},
});

// Social v1 on the host (desktop/social.ts) against the fake server (desktop/social-mock.ts): the same flows the
// Amigos pages and the visit drive, with the real store. The QA list of the job: add/accept, gift/like/help/delivery
// applied exactly once across a crash before the ack, request fulfil, visit save-identical, invite redeem/reward.
globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../src/stores/game-store.ts");
const social = await import("./social.ts");
const { exportSave } = await import("./cloud.ts");
const { pages } = await import("./pages/index.ts");
const { createDesktopView } = await import("./view.ts");
const { getSocialRewards, getDeliveryReward } = await import("../src/data/social.ts");
const { itemCatalog } = await import("../src/data/market-products.ts");

const initial = JSON.stringify(useGameStore.getState());
const sent = [];
const game = () => useGameStore.getState();
const settle = async () => {
	for (let i = 0; i < 5; i++) await Bun.sleep(1);
};
const act = async (action, ...args) => {
	const result = social.requestSocialAction(action, args);
	await settle();
	return result;
};
const toasts = () => sent.filter((m) => m.kind === "social-toast").map((m) => m.text);
// The save as the storage holds it (the JSON storage parses it: compared as text again).
const storedSave = () => JSON.stringify(useGameStore.persist.getOptions().storage.getItem("checkout.game"));

beforeAll(() => {
	useGameStore.setState(JSON.parse(initial));
	social.resetSocial();
	social.initSocial({ send: (m) => sent.push(m), refresh: () => {}, onVisit: () => {}, unity: false });
	social.applySocialStatus({ mock: true, platform: "editor", canShare: true, avatars: 12 });
});
afterAll(() => {
	social.resetSocial();
	useGameStore.setState(JSON.parse(initial));
});

test("before Amigos is opened once, nothing is polled in the background", async () => {
	expect(social.socialTouched()).toBe(false);
	expect(await social.runInboxCycle("start")).toEqual({ applied: 0, acked: 0 });
	expect(social.socialMock().log).toEqual([]);
});

test("first time on Amigos: the profile asks for a market name and a face", async () => {
	social.onSocialRoute("amigos");
	await settle();
	expect(social.socialStore.me.code).toBe("K7Q2MX4P");
	expect(social.socialStore.me.marketName).toBe(null);
	const first = pages(game(), "amigos");
	expect(first.cards[0].title).toBe("Dê um nome ao seu mercado");
	expect(first.cards[0].input).toMatchObject({ id: "name", max: 20 });
	expect(first.cards.slice(1).flatMap((c) => c.buttons).filter((b) => b.action === "socialPickAvatar")).toHaveLength(12);
	await act("socialPickAvatar", "shopper-4");
	await act("socialSaveProfile", "ab", "shopper-4");
	expect(toasts().at(-1)).toBe("Esse nome não é permitido. Escolha outro.");
	await act("socialSaveProfile", "Mercadinho do Lucas", "shopper-4");
	expect(social.socialStore.me).toMatchObject({ marketName: "Mercadinho do Lucas", avatar: "shopper-4" });
	// The save keeps the code: from now on the inbox is polled.
	expect(game().social.profile).toEqual({ code: "K7Q2MX4P", marketName: "Mercadinho do Lucas", avatar: "shopper-4" });
	expect(social.socialTouched()).toBe(true);
	const main = pages(game(), "amigos");
	expect(main.cards[0]).toMatchObject({ title: "Mercadinho do Lucas", subtitle: "K7Q2-MX4P" });
	expect(main.cards.some((c) => c.title === "Mercado da Ana" && c.buttons.some((b) => b.action === "socialVisit"))).toBe(true);
	expect(main.cards.some((c) => c.eyebrow === "QUER SER SEU AMIGO")).toBe(true);
});

test("the inbox: applied once, toasts, badge, then acked", async () => {
	const coins = game().coins;
	const result = await social.runInboxCycle("start");
	expect(result).toEqual({ applied: 3, acked: 3 });
	const rewards = getSocialRewards(game().era.id);
	expect(game().coins).toBe(coins + rewards.gift + rewards.like);
	expect(toasts().slice(-3)).toEqual([
		`Mercado da Ana te mandou um presente: +${rewards.gift} moedas`,
		`Banca do Bruno curtiu seu mercado: +${rewards.like} moedas`,
		"Quitanda da Duda quer ser seu amigo",
	]);
	expect(social.socialBadge()).toBe(3);
	const view = createDesktopView(game(), 1, []);
	expect(view.quick.find((b) => b.label === "Amigos").badge).toBe("3");
	expect(view.quickMain.badge).not.toBe("");
	social.onSocialRoute("amigos");
	expect(social.socialBadge()).toBe(0);
	expect(await social.runInboxCycle()).toEqual({ applied: 0, acked: 0 });
});

test("a crash between the save and the ack: the gift comes again and is acked without paying twice", async () => {
	const server = social.socialMock();
	server.control("gift");
	server.control("fail", "/v1/social/inbox/ack");
	const coins = game().coins;
	expect(await social.runInboxCycle()).toEqual({ applied: 1, acked: 0 });
	const paid = game().coins;
	expect(paid).toBe(coins + getSocialRewards(game().era.id).gift);
	// The game restarts from the save on disk (written before the ack) and asks again.
	const saved = JSON.parse(storedSave());
	useGameStore.setState(JSON.parse(initial));
	await useGameStore.persist.getOptions().storage.setItem("checkout.game", saved);
	await useGameStore.persist.rehydrate();
	expect(await social.runInboxCycle()).toEqual({ applied: 0, acked: 1 });
	expect(game().coins).toBe(paid);
	expect(server.inbox.filter((row) => row.to === "qa-player" && !row.acked)).toEqual([]);
});

test("add by code and accept a request", async () => {
	await act("socialAddFriend", "ab");
	expect(toasts().at(-1)).toBe("O código tem 8 letras e números, como K7Q2-MX4P.");
	await act("socialAddFriend", "eva3-v4rt");
	expect(toasts().at(-1)).toBe("Pedido de amizade enviado!");
	expect(social.socialStore.outgoing.map((p) => p.code)).toEqual(["EVA3V4RT"]);
	await act("socialAddFriend", "K7Q2MX4P");
	expect(toasts().at(-1)).toBe("Esse é o seu próprio código.");
	await act("socialAccept", "u-duda");
	expect(social.socialStore.friends.map((f) => f.id)).toContain("u-duda");
	expect(social.socialStore.incoming).toEqual([]);
});

test("gift, like and help at home: the helper's coins only after the server said OK", async () => {
	const rewards = getSocialRewards(game().era.id);
	let coins = game().coins;
	await act("socialGift", "u-bruno");
	expect(toasts().at(-1)).toBe("Presente enviado para Banca do Bruno!");
	await act("socialGift", "u-bruno");
	expect(toasts().at(-1)).toBe("Você já mandou um presente hoje. Volte amanhã!");
	expect(game().coins).toBe(coins);
	await act("socialLike", "u-bruno");
	expect(game().coins).toBe(coins + rewards.like);
	coins = game().coins;
	await act("socialLike", "u-bruno");
	expect(game().coins).toBe(coins);
	const bruno = social.socialStore.friends.find((f) => f.id === "u-bruno");
	const build = social.helpableBuilds(bruno)[0];
	await act("socialHelp", "u-bruno", build.id);
	expect(game().coins).toBe(coins + rewards.help);
	expect(social.helpableBuilds(bruno)).toEqual([]);
	await act("socialHelp", "u-bruno", build.id);
	expect(toasts().at(-1)).toBe("Você já ajudou nesta obra.");
	expect(game().coins).toBe(coins + rewards.help);
	expect(game().social.totals.helpsGiven).toBe(1);
	// What Bruno's game will get from the server.
	expect(social.socialMock().inbox.filter((row) => row.to === "u-bruno").map((row) => row.kind)).toEqual(["gift", "like", "help"]);
});

test("a visit never touches the player's save; what was earned there is booked on the way back", async () => {
	const apple = itemCatalog[0];
	useGameStore.setState({ inventory: { ...game().inventory, [apple.id]: 9 } });
	await settle();
	const before = { data: exportSave().data, stored: storedSave() };
	expect(await social.startVisit("u-ana")).toEqual({ ok: true, reason: "" });
	const snapshot = social.visitSnapshot();
	expect(snapshot.session).toMatch(/^visit-u-ana-/);
	expect(snapshot.era.id).toBe("spati");
	expect(snapshot.paint.primary).toBe("1F4D36");
	expect(snapshot.isOpen).toBe(false);
	expect(snapshot.customers).toEqual([]);
	const visit = social.visitView();
	expect(visit.friendName).toBe("Mercado da Ana");
	// Ana's builds: the evolution of her produce crates and the bakery being built in her yard.
	expect(visit.builds.map((build) => build.kind).sort()).toEqual(["evolution", "interior"]);
	const evolution = visit.builds.find((build) => build.kind === "evolution");
	expect(evolution).toMatchObject({ helped: false, button: { label: "Ajudar" } });
	expect(visit.builds.find((build) => build.kind === "interior")).toMatchObject({ targetId: "obra-shelf-bakery-ana", helped: false });
	// The HUD at home waits: no tools, no corner menu, no tutorial.
	const hud = createDesktopView(game(), 2, []);
	expect(hud.visit.active).toBe(true);
	expect(hud.tools).toEqual([]);
	expect(hud.quick).toEqual([]);
	// Only the visit's actions go through.
	expect(social.requestSocialAction("socialAddFriend", ["EVA3V4RT"]).ok).toBe(false);
	await act("socialLike", "u-ana");
	await act("socialHelp", "u-ana", evolution.buildId);
	const request = social.socialStore.visit.friend.openRequests[0];
	expect(request).toMatchObject({ productId: apple.id, qty: 6 });
	expect(pages(game(), "visita").cards[0].buttons[0]).toMatchObject({ label: "Enviar", enabled: true });
	await act("socialSend", request.id, "u-ana", apple.id, 6);
	expect(social.sendableStock(apple.id)).toBe(3);
	expect(social.visitView().builds.find((build) => build.kind === "evolution").button.label).toBe("Ajudado");
	// Frozen: byte for byte, in memory and on disk.
	expect(exportSave().data).toBe(before.data);
	expect(storedSave()).toBe(before.stored);
	const coins = game().coins;
	expect(social.endVisit()).toBe(true);
	const rewards = getSocialRewards(game().era.id);
	expect(game().coins).toBe(coins + rewards.like + rewards.help + getDeliveryReward(apple.purchasePrice, 6));
	expect(game().inventory[apple.id]).toBe(3);
	expect(social.visitSnapshot()).toBe(null);
});

test("a visit where the player only looks leaves the save byte-identical", async () => {
	const before = { data: exportSave().data, stored: storedSave() };
	expect((await social.startVisit("u-carla")).ok).toBe(true);
	expect(social.visitSnapshot().era.id).toBe("tenda");
	// An inbox poll during the visit waits for the way back.
	social.socialMock().control("like");
	expect(await social.runInboxCycle()).toEqual({ applied: 0, acked: 0 });
	expect(social.endVisit()).toBe(true);
	expect(exportSave().data).toBe(before.data);
	expect(storedSave()).toBe(before.stored);
	expect(await social.runInboxCycle()).toEqual({ applied: 1, acked: 1 });
});

test("ask friends for a product; the delivery lands in the stock room", async () => {
	const product = itemCatalog[1];
	const page = pages(game(), `amigos:pedir:${product.id}:8`);
	expect(page.cards[2].buttons[0]).toMatchObject({ action: "socialRequest", args: JSON.stringify([product.id, 8]) });
	await act("socialRequest", product.id, 8);
	expect(game().social.requests).toEqual([expect.objectContaining({ productId: product.id, qty: 8 })]);
	const have = game().inventory[product.id] ?? 0;
	social.socialMock().control("deliver");
	expect((await social.runInboxCycle()).applied).toBe(2);
	expect(game().inventory[product.id]).toBe(have + 8);
	expect(game().social.requests).toEqual([]);
	expect(toasts().at(-2)).toBe(`Mercado da Ana te mandou 8× ${product.name}`);
});

test("invite: redeem a code, then the reward at the Späti (diamonds and the first decoration)", async () => {
	await act("socialRedeem", "EVA3-V4RT");
	expect(social.socialStore.friends.map((f) => f.id)).toContain("u-eva");
	// friend_added goes to Eva (the one who did not act), not to the player.
	expect(social.socialMock().inbox.at(-1)).toMatchObject({ to: "u-eva", kind: "friend_added" });
	await act("socialRedeem", "EVA3V4RT");
	expect(toasts().at(-1)).toBe("Você já usou um código de convite.");
	const diamonds = game().logistics.premiumCurrency;
	social.socialMock().control("invite-reward");
	expect((await social.runInboxCycle()).applied).toBe(1);
	expect(game().logistics.premiumCurrency).toBe(diamonds + 30);
	expect(game().interior.owned["invite-reward-1"]).toBe(1);
	expect(toasts().at(-1)).toBe("Convite premiado: +30 diamantes e uma decoração exclusiva!");
});

test("a link or the Play Install Referrer offers the code on Amigos", async () => {
	expect(social.applySocialLink({ code: "bru4-n5pq", source: "deeplink" })).toBe(true);
	const page = pages(game(), "amigos");
	expect(page.cards.find((c) => c.title === "Convite de um amigo").subtitle).toBe("BRU4-N5PQ");
	expect(social.applySocialLink({ code: "nope" })).toBe(false);
});

test("share, copy and the QR code", async () => {
	await act("socialShare");
	expect(sent.at(-1)).toMatchObject({ kind: "social-share", url: "https://checkout-server.lucaslfurini.workers.dev/i/K7Q2MX4P", code: "K7Q2-MX4P" });
	expect(sent.at(-1).text).toContain("K7Q2-MX4P");
	await act("socialCopy");
	expect(sent.find((m) => m.kind === "social-copy").text).toBe("K7Q2-MX4P");
	await act("socialQr");
	expect(pages(game(), "amigos").cards[0].qr).toMatch(/^33:[01]{1089}$/);
});

test("a reported name: the owner is asked for a new one", async () => {
	social.socialMock().control("hide-name");
	await social.loadSocial(true);
	const page = pages(game(), "amigos");
	expect(page.cards[0].title).toBe("Escolha outro nome");
	await act("socialSaveProfile", "mercadinho do lucas", "shopper-4");
	expect(toasts().at(-1)).toBe("Esse nome não é permitido. Escolha outro.");
	await act("socialSaveProfile", "Empório do Lucas", "shopper-4");
	expect(social.socialStore.me).toMatchObject({ marketName: "Empório do Lucas", nameHidden: false });
});
