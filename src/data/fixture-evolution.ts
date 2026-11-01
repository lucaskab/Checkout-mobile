import type { EvolutionKind, FixtureEvolution } from "@/@types/fixture-evolution";
import { getSkipDiamondCost } from "./diamond-skip";

// How long each evolution takes (claude/evolucoes-recompensas.md 2.1–2.3, Lucas 01/11) and the evolution crew's
// queue: one evolution at a time, the others wait; the crew is not the interior builders, so evolving never holds up
// the works. Times run while the game is closed. Skipping costs the usual diamond curve (src/data/diamond-skip.ts).

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;

/** Product fixtures: to T2 2 min, T3 10 min, T4 30 min, ★ 1 h. */
export const shelfEvolutionMs: Record<number, number> = { 2: 2 * MINUTE, 3: 10 * MINUTE, 4: 30 * MINUTE, 5: HOUR };
/** Special sectors: T2 30 min, T3 2 h. */
export const sectorEvolutionMs: Record<number, number> = { 2: 30 * MINUTE, 3: 2 * HOUR };
/** The checkout: T2 5 min, T3 20 min, T4 1 h. */
export const checkoutEvolutionMs: Record<number, number> = { 2: 5 * MINUTE, 3: 20 * MINUTE, 4: HOUR };
/** Machines: ATM and claw 15 min / 1 h, gumball 10 min. */
export const decorEvolutionMs: Record<string, Record<number, number>> = {
	atm: { 2: 15 * MINUTE, 3: HOUR },
	"claw-machine": { 2: 15 * MINUTE, 3: HOUR },
	gumball: { 2: 10 * MINUTE },
};

/** Evolution crews working at the same time. */
export const MAX_RUNNING_EVOLUTIONS = 1;

export function getEvolutionDurationMs(kind: EvolutionKind, targetId: string, toTier: number) {
	if (kind === "shelf") return shelfEvolutionMs[toTier] ?? 0;
	if (kind === "sector") return sectorEvolutionMs[toTier] ?? 0;
	if (kind === "checkout") return checkoutEvolutionMs[toTier] ?? 0;
	return decorEvolutionMs[targetId]?.[toTier] ?? 0;
}

/** Times of the queue: the running one keeps its clock, the next ones start when the one before ends. */
export function scheduleEvolutions(list: readonly FixtureEvolution[], now = Date.now()): FixtureEvolution[] {
	const ordered = [...list].sort((a, b) => a.startedAt - b.startedAt);
	let cursor = now;
	let running = 0;
	const timed = new Map<string, FixtureEvolution>();
	for (const item of ordered) {
		if (item.startedAt <= now && running < MAX_RUNNING_EVOLUTIONS) {
			running++;
			cursor = Math.max(cursor, item.endsAt);
			timed.set(item.id, item);
			continue;
		}
		const startedAt = Math.max(cursor, now);
		const endsAt = startedAt + item.durationMs;
		cursor = endsAt;
		timed.set(item.id, { ...item, startedAt, endsAt });
	}
	return list.map((item) => timed.get(item.id) ?? item);
}

/** Adds an evolution at the end of the queue (it starts at once when the crew is free). */
export function enqueueEvolution(
	list: readonly FixtureEvolution[],
	evolution: Omit<FixtureEvolution, "id" | "startedAt" | "endsAt">,
	now = Date.now(),
): FixtureEvolution[] {
	const lastEnd = list.reduce((end, item) => Math.max(end, item.endsAt), now);
	const startedAt = Math.max(now, lastEnd);
	const item: FixtureEvolution = {
		...evolution,
		id: `evolucao-${evolution.kind}-${evolution.targetId}-${evolution.toTier}-${now}`,
		startedAt,
		endsAt: startedAt + evolution.durationMs,
	};
	return scheduleEvolutions([...list, item], now);
}

/** The evolution of this piece in the queue (or running). */
export function findEvolution(list: readonly FixtureEvolution[] | undefined, kind: EvolutionKind, targetId: string) {
	return (list ?? []).find((item) => item.kind === kind && item.targetId === targetId) ?? null;
}

/** Where an evolution stands now, for the screens and Unity's ring. */
export function getEvolutionProgress(item: FixtureEvolution, now = Date.now()) {
	const queued = item.startedAt > now;
	const remainingMs = queued ? item.durationMs : Math.max(0, item.endsAt - now);
	return {
		queued,
		remainingMs,
		progress: queued ? 0 : Math.min(1, Math.max(0, 1 - remainingMs / Math.max(1, item.durationMs))),
		// Queued evolutions cost their own time, not the wait for the ones before.
		skipCost: getSkipDiamondCost(remainingMs),
	};
}

export function normalizeEvolutions(value: unknown): FixtureEvolution[] {
	if (!Array.isArray(value)) return [];
	return value.filter(
		(item): item is FixtureEvolution =>
			!!item &&
			typeof item === "object" &&
			typeof item.id === "string" &&
			["shelf", "sector", "checkout", "decor"].includes(item.kind) &&
			typeof item.targetId === "string" &&
			typeof item.toTier === "number" &&
			typeof item.durationMs === "number" &&
			typeof item.startedAt === "number" &&
			typeof item.endsAt === "number",
	);
}
