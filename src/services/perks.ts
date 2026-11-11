// Three ways to pay for an edge (Lucas 11/11, claude/monetizacao-oportunidades.md):
// - Pacote inicial: a one-time pack (diamonds, coins, +1 truck, 3 freight coupons, a bandana for the dog) for the
//   first 48 h after the tutorial (players from before it get their 48 h from when they first see it).
// - Ganho offline: on the way back "Coletar", "2× com vídeo" or "3× com diamantes", and a longer time away bought once.
// - Recuperar a sequência do Presente do dia: src/services/daily-login.ts.

export type PerksState = {
	/** When the starter pack's 48 h began (0 = not yet: the tutorial is still on). */
	starterStartedAt: number;
	/** The time away that still sells: 0 = 8 h, 1 = 12 h, 2 = 24 h. */
	offlineCapLevel: number;
	/** The offer's page opened on its own once (after that only the HUD button shows it). */
	starterShown: boolean;
};

const HOUR = 60 * 60_000;
export const STARTER_PACK_ID = "bundle-firstdays";
export const STARTER_WINDOW_MS = 48 * HOUR;
/** Hours away that still sell, per level, and the diamonds for each next level. */
export const OFFLINE_CAP_HOURS: readonly number[] = [8, 12, 24];
export const OFFLINE_CAP_PRICES: readonly number[] = [40, 100];

export function createPerksState(): PerksState {
	return { starterStartedAt: 0, offlineCapLevel: 0, starterShown: false };
}

export function normalizePerksState(value: unknown): PerksState {
	const item = (value && typeof value === "object" ? value : {}) as Partial<PerksState>;
	const num = (n: unknown) => (typeof n === "number" && Number.isFinite(n) ? Math.max(0, n) : 0);
	return {
		starterStartedAt: num(item.starterStartedAt),
		offlineCapLevel: Math.min(OFFLINE_CAP_HOURS.length - 1, Math.floor(num(item.offlineCapLevel))),
		starterShown: item.starterShown === true,
	};
}

// ---------------------------------------------------------------- Pacote inicial
/** When the starter offer ends (0 = it has not begun). */
export function getStarterOfferEnd(perks: PerksState | undefined) {
	const started = normalizePerksState(perks).starterStartedAt;
	return started > 0 ? started + STARTER_WINDOW_MS : 0;
}

/** Whether the starter pack can be bought now: begun, inside its 48 h and not bought yet. */
export function isStarterOfferOpen(perks: PerksState | undefined, purchasedPackIds: readonly string[] | undefined, now = Date.now()) {
	const end = getStarterOfferEnd(perks);
	return end > 0 && now < end && !(purchasedPackIds ?? []).includes(STARTER_PACK_ID);
}

// ---------------------------------------------------------------- Ganho offline
export function getOfflineCapHours(perks: PerksState | undefined) {
	return OFFLINE_CAP_HOURS[normalizePerksState(perks).offlineCapLevel] ?? OFFLINE_CAP_HOURS[0];
}

export function getOfflineCapMs(perks: PerksState | undefined) {
	return getOfflineCapHours(perks) * HOUR;
}

/** The next longer time away and its price in diamonds (null at the longest). */
export function getNextOfflineCap(perks: PerksState | undefined) {
	const level = normalizePerksState(perks).offlineCapLevel;
	const hours = OFFLINE_CAP_HOURS[level + 1];
	const price = OFFLINE_CAP_PRICES[level];
	return hours && price ? { hours, price } : null;
}

/** Diamonds for "3×" on the way back: 4 per hour away (at least 5). Cheaper than the coins would cost in a pack. */
export function getOfflineTriplePrice(durationMs: number) {
	return Math.max(5, Math.ceil((Math.max(0, durationMs) / HOUR) * 4));
}
