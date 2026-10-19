import type { GameStore } from "@/@types/game";
import { getMarketEra } from "@/data/economy";
import { useGameStore } from "@/stores/game-store";

/**
 * Cloud saves as the host sees them (Lucas 12/10: "o progresso e os diamantes continuam se ele trocar de celular").
 *
 * Unity (CheckoutCloud.cs) owns the login (Google; Apple on the iPhone), the session and the network: it talks to the server
 * (server/, Render + Prisma Postgres) and decides when to upload. The host owns the save itself and the pages:
 * - `cloud-export` → the whole save as the store persists it ("checkout.game"), and what it holds;
 * - `cloud-import` → replaces the progress on this device with the cloud's (then the game resumes from it);
 * - `cloud` status messages (signed in or out, syncing, offline, a conflict to choose) drive the "Conta" page;
 * - the page's buttons (cloudSignIn, cloudSync, cloudResolve, cloudSignOut, cloudDeleteAccount) become messages
 *   for Unity.
 */
export type SaveSummary = { level: number; era: string; coins: number; diamonds: number; day: number; version: number };
export type CloudStatus = "unavailable" | "signed-out" | "signing-in" | "synced" | "syncing" | "offline" | "conflict" | "error";
/** Who the player signs in with: Google (Android, PC, iPhone) or Apple (iPhone). */
export type CloudProvider = "google" | "apple";

export const cloudStore = {
	status: "unavailable" as CloudStatus,
	email: "",
	name: "",
	/** The signed-in account's provider ("" when signed out). */
	provider: "" as CloudProvider | "",
	/** The logins this device offers, in button order (Unity decides: Apple only on the iPhone). */
	providers: [] as CloudProvider[],
	/** When the progress was last saved in the cloud (ms). */
	lastSyncAt: 0,
	error: "",
	/** Both versions of the progress, when they went separate ways (two phones). */
	conflict: null as null | { cloud: SaveSummary; cloudAt: number; cloudDevice: string; otherAccount: boolean },
	/** "Apagar conta" asks twice: the second press must come before this time. */
	confirmDeleteUntil: 0,
};

const num = (value: unknown) => (typeof value === "number" && Number.isFinite(value) ? value : 0);

/** The same summary the server keeps (server/src/save.ts readSave). */
export function summarize(state: Partial<GameStore> | Record<string, any>, version = 0): SaveSummary {
	const s = state as Record<string, any>;
	return {
		level: num(s.market?.level) || 1,
		era: typeof s.era?.id === "string" ? s.era.id : "",
		coins: num(s.coins),
		diamonds: num(s.logistics?.premiumCurrency),
		day: num(s.day?.dayNumber),
		version,
	};
}

/**
 * A game that was never really played (a new phone): the cloud progress replaces it without asking. Anything bought
 * (a diamond pack, more diamonds than the 10 a new game starts with) makes it a real game, so the player is asked.
 */
export function isFreshGame(summary: SaveSummary, purchases = 0) {
	return summary.level <= 1 && summary.day <= 1 && summary.diamonds <= 10 && purchases === 0;
}

/** The save exactly as the store persists it, and what it holds. */
export function exportSave() {
	const options = useGameStore.persist.getOptions();
	const state = useGameStore.getState();
	const version = options.version ?? 0;
	const persisted = options.partialize ? options.partialize(state) : state;
	const summary = summarize(state, version);
	const purchases = (state.currencyPurchases?.processedTransactionIds?.length ?? 0) + (state.currencyPurchases?.purchasedPackIds?.length ?? 0);
	return { data: JSON.stringify({ state: persisted, version }), summary, fresh: isFreshGame(summary, purchases) };
}

/** Replaces this device's progress with `data` (a cloud save). Older save versions are migrated on the way in. */
export async function importSave(data: unknown) {
	if (typeof data !== "string") return false;
	let parsed: { state?: unknown; version?: unknown };
	try {
		parsed = JSON.parse(data);
	} catch {
		return false;
	}
	if (!parsed || typeof parsed.state !== "object" || parsed.state === null || Array.isArray(parsed.state)) return false;
	const options = useGameStore.persist.getOptions();
	if (!options.storage || !options.name) return false;
	const previous = await options.storage.getItem(options.name);
	try {
		await options.storage.setItem(options.name, { state: parsed.state, version: num(parsed.version) } as never);
		await useGameStore.persist.rehydrate();
	} catch (error) {
		// Never leave the device half-replaced: put this device's save back.
		if (previous) await options.storage.setItem(options.name, previous);
		console.error(`CHECKOUT_CLOUD import failed: ${error}`);
		return false;
	}
	// The other phone was closed since its last upload: the market catches up like after any pause.
	useGameStore.getState().processSessionResume();
	return true;
}

export type CloudUnityMessage = {
	kind: "cloud";
	status?: unknown;
	email?: unknown;
	name?: unknown;
	provider?: unknown;
	providers?: unknown;
	lastSyncAt?: unknown;
	error?: unknown;
	conflict?: unknown;
};

const statuses: CloudStatus[] = ["unavailable", "signed-out", "signing-in", "synced", "syncing", "offline", "conflict", "error"];

export function applyCloudMessage(message: CloudUnityMessage) {
	if (statuses.includes(message.status as CloudStatus)) cloudStore.status = message.status as CloudStatus;
	if (typeof message.email === "string") cloudStore.email = message.email;
	if (typeof message.name === "string") cloudStore.name = message.name;
	if (message.provider === "google" || message.provider === "apple" || message.provider === "") cloudStore.provider = message.provider;
	if (Array.isArray(message.providers))
		cloudStore.providers = message.providers.filter((p): p is CloudProvider => p === "google" || p === "apple");
	if (typeof message.lastSyncAt === "number") cloudStore.lastSyncAt = message.lastSyncAt;
	cloudStore.error = typeof message.error === "string" ? message.error : "";
	const conflict = message.conflict as { cloud?: unknown; cloudAt?: unknown; cloudDevice?: unknown; otherAccount?: unknown } | undefined;
	cloudStore.conflict =
		cloudStore.status === "conflict" && conflict && typeof conflict.cloud === "object" && conflict.cloud
			? { cloud: conflict.cloud as SaveSummary, cloudAt: num(conflict.cloudAt), cloudDevice: String(conflict.cloudDevice ?? ""), otherAccount: conflict.otherAccount === true }
			: null;
	if (cloudStore.status === "signed-out") {
		// The error (a refused login) stays on the page until the next try.
		cloudStore.email = cloudStore.name = cloudStore.provider = "";
		cloudStore.lastSyncAt = 0;
	}
}

export type CloudRequest = { ok: true; message: Record<string, unknown> } | { ok: false; reason: string };

/** A button of the "Conta" page: the message for Unity, or why not now. */
export function requestCloudAction(action: string, args: unknown[], now = Date.now()): CloudRequest {
	const signedIn = !["unavailable", "signed-out", "signing-in"].includes(cloudStore.status);
	switch (action) {
		case "cloudSignIn": {
			if (cloudStore.status === "unavailable") return { ok: false, reason: "O login não está disponível nesta versão do jogo." };
			if (signedIn) return { ok: false, reason: "Você já entrou." };
			const provider = args[0] === "apple" ? "apple" : "google";
			if (cloudStore.providers.length && !cloudStore.providers.includes(provider)) return { ok: false, reason: "Este login não está disponível neste aparelho." };
			return { ok: true, message: { kind: "cloud-signin", provider } };
		}
		case "cloudSync":
			if (!signedIn) return { ok: false, reason: "Entre na sua conta primeiro." };
			return { ok: true, message: { kind: "cloud-sync" } };
		case "cloudResolve": {
			const keep = args[0];
			if (cloudStore.status !== "conflict" || (keep !== "cloud" && keep !== "device")) return { ok: false, reason: "Nada para escolher agora." };
			return { ok: true, message: { kind: "cloud-resolve", keep } };
		}
		case "cloudSignOut":
			if (!signedIn) return { ok: false, reason: "Você não entrou." };
			return { ok: true, message: { kind: "cloud-signout" } };
		case "cloudDeleteAccount":
			if (!signedIn) return { ok: false, reason: "Você não entrou." };
			if (cloudStore.confirmDeleteUntil < now) {
				cloudStore.confirmDeleteUntil = now + 10_000;
				return { ok: false, reason: "Toque de novo para apagar a conta de vez." };
			}
			cloudStore.confirmDeleteUntil = 0;
			return { ok: true, message: { kind: "cloud-delete" } };
	}
	return { ok: false, reason: "invalid-action" };
}

export const cloudActions = ["cloudSignIn", "cloudSync", "cloudResolve", "cloudSignOut", "cloudDeleteAccount"];

export function describeSummary(summary: SaveSummary) {
	const era = summary.era ? getMarketEra(summary.era as never).name : "";
	return [
		`Nível ${summary.level}${era ? ` · ${era}` : ""}`,
		`${Math.round(summary.coins).toLocaleString("pt-BR")} moedas · ${Math.round(summary.diamonds).toLocaleString("pt-BR")} diamantes · dia ${summary.day}`,
	];
}

export function formatAgo(at: number, now = Date.now()) {
	const minutes = Math.floor((now - at) / 60_000);
	if (minutes < 1) return "agora mesmo";
	if (minutes < 60) return minutes === 1 ? "há 1 minuto" : `há ${minutes} minutos`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return hours === 1 ? "há 1 hora" : `há ${hours} horas`;
	const days = Math.floor(hours / 24);
	return days === 1 ? "há 1 dia" : `há ${days} dias`;
}

/** Which progress went further (to recommend it when the player must choose). */
export const isAhead = (a: SaveSummary, b: SaveSummary) => a.level > b.level || (a.level === b.level && a.day >= b.day);

export function resetCloudStore() {
	Object.assign(cloudStore, { status: "unavailable", email: "", name: "", provider: "", providers: [], lastSyncAt: 0, error: "", conflict: null, confirmDeleteUntil: 0 });
}
