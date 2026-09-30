import type {
	InteriorBuildKind,
	InteriorConstruction,
} from "@/@types/interior-construction";
import type { ProductionSectorId } from "@/@types/production";
import { getMarketExpansionSkipCost } from "./market-expansions";
import { shelves } from "./market-products";
import { productionSectors } from "./production-sectors";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;

/** Builders working inside the market at the same time: placed works wait in a queue. */
export const MAX_INTERIOR_CONSTRUCTIONS = 1;

/** Price and building time of each production sector (the level only makes it available). */
export const sectorBuildPlans: Record<
	ProductionSectorId,
	{ coinCost: number; durationMs: number }
> = {
	padaria: { coinCost: 1_500, durationMs: 2 * MINUTE },
	queijaria: { coinCost: 6_000, durationMs: 10 * MINUTE },
	acougue: { coinCost: 15_000, durationMs: 30 * MINUTE },
	bebidas: { coinCost: 22_000, durationMs: 45 * MINUTE },
	peixaria: { coinCost: 40_000, durationMs: 90 * MINUTE },
	adega: { coinCost: 80_000, durationMs: 3 * HOUR },
	sorvetes: { coinCost: 120_000, durationMs: 4 * HOUR },
};

/** Building time of the n-th shelf (index in `shelves`; the first one comes with the shop). */
const shelfBuildDurations = [
	0,
	1 * MINUTE,
	3 * MINUTE,
	6 * MINUTE,
	12 * MINUTE,
	25 * MINUTE,
	45 * MINUTE,
];

export function getShelfBuildDurationMs(shelfIndex: number) {
	if (shelfIndex < shelfBuildDurations.length)
		return shelfBuildDurations[Math.max(0, shelfIndex)];
	return (shelfIndex - shelfBuildDurations.length + 1) * HOUR;
}

/** Shop items that are furniture in the market: they are installed by the builders. */
export const shopItemBuildDurations: Record<string, number> = {
	"extra-checkout": 15 * MINUTE,
	"self-checkout": 2 * HOUR,
};

export function isBuiltShopItem(itemId: string) {
	return Object.hasOwn(shopItemBuildDurations, itemId);
}

/** Diamonds to finish a build right now: the same rule as the expansions (1 per 10 minutes left). */
export function getInteriorSkipCost(remainingMs: number) {
	return getMarketExpansionSkipCost(remainingMs);
}

export function getInteriorBuildName(kind: InteriorBuildKind, targetId: string) {
	if (kind === "sector")
		return (
			productionSectors.find((sector) => sector.id === targetId)?.name ?? "Setor"
		);
	if (kind === "shelf")
		return shelves.find((shelf) => shelf.id === targetId)?.name ?? "Prateleira";
	if (targetId === "extra-checkout") return "Caixa extra";
	if (targetId === "self-checkout") return "Autoatendimento";
	return "Instalação";
}

const kinds: InteriorBuildKind[] = ["shelf", "sector", "shop"];

export function normalizeInteriorConstructions(
	value: unknown,
): InteriorConstruction[] {
	if (!Array.isArray(value)) return [];
	const seen = new Set<string>();
	const list: InteriorConstruction[] = [];
	for (const raw of value) {
		if (!raw || typeof raw !== "object") continue;
		const item = raw as Partial<InteriorConstruction>;
		if (
			typeof item.id !== "string" ||
			!kinds.includes(item.kind as InteriorBuildKind) ||
			typeof item.targetId !== "string" ||
			typeof item.startedAt !== "number" ||
			typeof item.endsAt !== "number" ||
			!Number.isFinite(item.endsAt) ||
			seen.has(`${item.kind}:${item.targetId}`)
		)
			continue;
		seen.add(`${item.kind}:${item.targetId}`);
		list.push({
			id: item.id,
			kind: item.kind as InteriorBuildKind,
			targetId: item.targetId,
			startedAt: item.startedAt,
			endsAt: item.endsAt,
			...(item.pending ? { pending: true } : {}),
			durationMs:
				typeof item.durationMs === "number" && Number.isFinite(item.durationMs)
					? Math.max(0, item.durationMs)
					: Math.max(0, item.endsAt - item.startedAt),
		});
	}
	return list;
}

const sectorIds = productionSectors.map((sector) => sector.id);

/** Built sectors. Saves from before sectors had to be built keep every sector their level had
 * already opened, so nobody loses a working counter. */
export function normalizeBuiltSectorIds(
	value: unknown,
	level: number,
): ProductionSectorId[] {
	if (!Array.isArray(value))
		return productionSectors
			.filter((sector) => level >= sector.requiredLevel)
			.map((sector) => sector.id);
	return Array.from(
		new Set(
			value.filter((id): id is ProductionSectorId =>
				sectorIds.includes(id as ProductionSectorId),
			),
		),
	);
}

export function findInteriorConstruction(
	list: readonly InteriorConstruction[],
	kind: InteriorBuildKind,
	targetId: string,
) {
	return list.find((item) => item.kind === kind && item.targetId === targetId) ?? null;
}

/** Pieces in the build mode that a build becomes (ids of `interior.items`). */
export function interiorPieceIds(kind: InteriorBuildKind, targetId: string): string[] {
	if (kind === "shelf") return [`shelf:${targetId}`];
	if (kind === "sector") return [`sector:${targetId}`];
	if (targetId === "extra-checkout") return ["checkout:extra"];
	if (targetId === "self-checkout") return ["kiosk:1", "kiosk:2"];
	return [];
}

export const constructionDuration = (item: InteriorConstruction) =>
	Math.max(0, item.durationMs ?? item.endsAt - item.startedAt);

/** Bought, not placed yet: waits in the inventory (build mode, "Para colocar"). */
export function createPendingConstruction(
	kind: InteriorBuildKind,
	targetId: string,
	durationMs: number,
	now = Date.now(),
): InteriorConstruction {
	return { id: `${kind}-${targetId}-${now}`, kind, targetId, startedAt: 0, endsAt: 0, pending: true, durationMs };
}

/** The crew builds one thing at a time, in the order the pieces were placed: works already running
 * keep their times, the queued ones start one after the other (earlier when one is finished early). */
export function scheduleInteriorConstructions(
	list: readonly InteriorConstruction[],
	now = Date.now(),
): InteriorConstruction[] {
	const placed = list.filter((item) => !item.pending).sort((a, b) => a.startedAt - b.startedAt);
	let cursor = now;
	const timed = new Map<string, InteriorConstruction>();
	let running = 0;
	for (const item of placed) {
		if (item.startedAt <= now && running < MAX_INTERIOR_CONSTRUCTIONS) {
			running++;
			cursor = Math.max(cursor, item.endsAt);
			timed.set(item.id, item);
			continue;
		}
		const startedAt = Math.max(cursor, now);
		const endsAt = startedAt + constructionDuration(item);
		cursor = endsAt;
		timed.set(item.id, { ...item, startedAt, endsAt });
	}
	return list.map((item) => timed.get(item.id) ?? item);
}

/** The player placed the piece: the works join the builders' queue. */
export function placeInteriorConstruction(
	list: readonly InteriorConstruction[],
	id: string,
	now = Date.now(),
): InteriorConstruction[] {
	const lastEnd = list
		.filter((item) => !item.pending)
		.reduce((end, item) => Math.max(end, item.endsAt), now);
	return scheduleInteriorConstructions(
		list.map((item) => {
			if (item.id !== id || !item.pending) return item;
			const { pending: _pending, ...rest } = item;
			const startedAt = Math.max(now, lastEnd);
			return { ...rest, startedAt, endsAt: startedAt + constructionDuration(item) };
		}),
		now,
	);
}

export const isQueuedConstruction = (item: InteriorConstruction, now = Date.now()) =>
	!item.pending && item.startedAt > now;
