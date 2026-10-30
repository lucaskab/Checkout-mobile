import type { GameCelebration, GameCelebrationKind } from "@/@types/game";

// Conquests worth a celebration on screen (Township's "new area", Hay Day's "building ready"): a lot the crew
// finished clearing, a new expansion of the market, a production sector, shelf or installation that the
// builders finished. The store queues them as they happen (also while the game was closed) and the HUD
// plays them one by one (desktop/celebration.ts, CheckoutDesktopHUD.Conquest.cs) until the player closes
// each one (dismissCelebration).

const KINDS: GameCelebrationKind[] = ["lot", "era", "sector", "shelf", "shop", "tier"];
/** Older ones are dropped: after a long time away only the latest conquests are worth replaying. */
const MAX_QUEUED = 4;

export function pushCelebration(
	list: readonly GameCelebration[] | undefined,
	kind: GameCelebrationKind,
	targetId: string,
	at = Date.now(),
): GameCelebration[] {
	const queue = (list ?? []).filter((item) => !(item.kind === kind && item.targetId === targetId));
	return [...queue, { id: `${kind}:${targetId}:${at}`, kind, targetId, at }].slice(-MAX_QUEUED);
}

export function normalizeCelebrations(value: unknown): GameCelebration[] {
	if (!Array.isArray(value)) return [];
	return value
		.filter(
			(item): item is GameCelebration =>
				!!item &&
				typeof item === "object" &&
				typeof item.id === "string" &&
				typeof item.targetId === "string" &&
				KINDS.includes(item.kind) &&
				typeof item.at === "number",
		)
		.slice(-MAX_QUEUED);
}
