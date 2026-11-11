import type { MarketEraId } from "@/@types/economy";

// Two prompts about the app itself (Lucas 10/11):
// - Rate the game: after a moment of triumph ("o jogador conseguiu expandir da tendinha pro container"), once the
//   celebration is closed, the system's own review sheet (App Store: SKStoreReviewController, Google Play: In-App
//   Review). Research 10/11: ask right after a win, never during play, onboarding or a purchase; no pre-question that
//   filters happy players and no reward for a review (both against the store rules). Apple shows the sheet at most
//   3 times a year and Google has its own quota, so the game asks rarely: from the banca on, at most once every 30
//   days and 3 times in 365 days.
// - A new version in the store: Unity checks the store (CheckoutUpdates.cs) and the host offers "Atualizar agora" /
//   "Agora não"; "Agora não" waits 2 days before asking again about that same version.

export type AppPromptsState = {
	/** When the review sheet was asked for (newest last, the last 3). */
	reviewAsks: number[];
	/** The store version the player said "Agora não" to, and until when. */
	updateSnoozedVersion: string;
	updateSnoozedUntil: number;
};

const DAY = 86_400_000;
export const REVIEW_MIN_GAP_MS = 30 * DAY;
export const REVIEW_MAX_PER_YEAR = 3;
export const UPDATE_SNOOZE_MS = 2 * DAY;
/** Expansions whose arrival is worth asking for a rating (the sidewalk table and the tent are too early). */
export const REVIEW_ERAS: readonly MarketEraId[] = [
	"banca", "conteiner", "spati", "quitanda", "minimercado", "mercadinho", "supermercado", "hipermercado", "rede",
];

export function createAppPromptsState(): AppPromptsState {
	return { reviewAsks: [], updateSnoozedVersion: "", updateSnoozedUntil: 0 };
}

export function normalizeAppPromptsState(value: unknown): AppPromptsState {
	const item = (value && typeof value === "object" ? value : {}) as Partial<AppPromptsState>;
	const num = (n: unknown) => (typeof n === "number" && Number.isFinite(n) ? Math.max(0, n) : 0);
	return {
		reviewAsks: (Array.isArray(item.reviewAsks) ? item.reviewAsks : []).map(num).filter((n) => n > 0).slice(-REVIEW_MAX_PER_YEAR),
		updateSnoozedVersion: typeof item.updateSnoozedVersion === "string" ? item.updateSnoozedVersion.slice(0, 32) : "",
		updateSnoozedUntil: num(item.updateSnoozedUntil),
	};
}

/** Is the arrival of `eraId` (its celebration just closed) a good moment to show the review sheet? */
export function shouldAskForReview(
	state: AppPromptsState | undefined,
	eraId: string,
	context: { onboardingActive: boolean },
	now = Date.now(),
) {
	if (context.onboardingActive || !REVIEW_ERAS.includes(eraId as MarketEraId)) return false;
	const asks = normalizeAppPromptsState(state).reviewAsks;
	if (asks.some((at) => now - at < REVIEW_MIN_GAP_MS)) return false;
	return asks.filter((at) => now - at < 365 * DAY).length < REVIEW_MAX_PER_YEAR;
}

export function noteReviewAsked(state: AppPromptsState | undefined, now = Date.now()): AppPromptsState {
	const current = normalizeAppPromptsState(state);
	return { ...current, reviewAsks: [...current.reviewAsks, now].slice(-REVIEW_MAX_PER_YEAR) };
}

/** "1.0.10" > "1.0.9" (numeric parts; missing parts count as 0). */
export function isNewerVersion(latest: string, current: string) {
	const parts = (v: string) => String(v ?? "").split(/[^0-9]+/).filter(Boolean).map(Number);
	const a = parts(latest), b = parts(current);
	if (!a.length) return false;
	for (let i = 0; i < Math.max(a.length, b.length); i++) {
		const x = a[i] ?? 0, y = b[i] ?? 0;
		if (x !== y) return x > y;
	}
	return false;
}

export function isUpdateSnoozed(state: AppPromptsState | undefined, version: string, now = Date.now()) {
	const current = normalizeAppPromptsState(state);
	return current.updateSnoozedVersion === version && now < current.updateSnoozedUntil;
}

export function snoozeUpdate(state: AppPromptsState | undefined, version: string, now = Date.now()): AppPromptsState {
	return { ...normalizeAppPromptsState(state), updateSnoozedVersion: version, updateSnoozedUntil: now + UPDATE_SNOOZE_MS };
}
