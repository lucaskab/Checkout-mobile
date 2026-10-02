import type { MarketEraId } from "@/@types/economy";
import { getBuildDurationForCost, getMarketEra, MIN_BUILD_MS } from "@/data/economy";
import { ERA_LOTS, FIRST_LOT, getMarketLot, MARKET_LOTS, type MarketLot, OLD_LOT_IDS, PLAZA_LOTS } from "@/data/market-lots";

// Land (terrenos), the way Township, Hay Day and the idle tycoons do it:
//  - the lots around the market are visible from the start, fenced, with a "VENDE-SE" sign and their price;
//  - A1 (the corner on the left of the avenue) comes first; then only lots next to land you already have;
//  - a bought lot still has its old building (an abandoned house, a shed, rubble): clearing it takes a timer
//    that grows with the lot (and can be sped up with diamonds) and pays some experience when it is done;
//  - expansions need their lots (src/data/market-lots.ts ERA_LOTS): the tenda moves from the sidewalk onto A1,
//    the minimercado needs B1 too, the supermercado six lots, the hipermercado the whole block.

export type LotsState = {
	/** Lots bought (cleared or not). */
	owned: string[];
	/** Lots bought and cleared: ready for the market. */
	cleared: string[];
	/** The lot being cleared now (one at a time). */
	clearing: { lotId: string; startedAt: number; endsAt: number } | null;
};

export type LotStatus = "praca" | "venda" | "bloqueado" | "comprado" | "limpando" | "seu";

export function createLotsState(): LotsState {
	return { owned: [], cleared: [], clearing: null };
}

const buyable = new Set(MARKET_LOTS.filter((lot) => lot.price > 0).map((lot) => lot.id));

/** Old saves (before the lots) get the lots their expansion already stands on, bought and cleared. */
export function normalizeLotsState(value: unknown, eraId: MarketEraId): LotsState {
	const fallback = ERA_LOTS[eraId] ?? [];
	if (!value || typeof value !== "object")
		return { owned: [...fallback], cleared: [...fallback], clearing: null };
	const item = value as Partial<LotsState>;
	// Saves from before the grid used lots "1"–"6": each becomes the grid lot that took its place.
	const ids = (list: unknown) =>
		Array.isArray(list)
			? list
					.map((id) => (typeof id === "string" ? (OLD_LOT_IDS[id] ?? id) : id))
					.filter((id): id is string => typeof id === "string" && buyable.has(id))
			: [];
	const owned = Array.from(new Set([...ids(item.owned), ...fallback]));
	const cleared = Array.from(new Set([...ids(item.cleared), ...fallback])).filter((id) => owned.includes(id));
	const c = item.clearing ? { ...item.clearing, lotId: OLD_LOT_IDS[item.clearing.lotId] ?? item.clearing.lotId } : null;
	const clearing =
		c && typeof c === "object" && owned.includes(c.lotId) && !cleared.includes(c.lotId) &&
		typeof c.startedAt === "number" && typeof c.endsAt === "number"
			? { lotId: c.lotId, startedAt: c.startedAt, endsAt: c.endsAt }
			: null;
	return { owned, cleared, clearing };
}

const touches = (a: MarketLot, b: MarketLot) => {
	const eps = 0.01;
	const overlapX = Math.min(a.x1, b.x1) - Math.max(a.x0, b.x0);
	const overlapZ = Math.min(a.z1, b.z1) - Math.max(a.z0, b.z0);
	return (overlapX > eps && Math.abs(overlapZ) <= eps) || (overlapZ > eps && Math.abs(overlapX) <= eps);
};

/** Lots that can be bought now: A1 first, then any lot next to land the player owns. */
export function isLotReachable(lots: LotsState, lotId: string) {
	if (lotId === FIRST_LOT) return true;
	if (!lots.owned.includes(FIRST_LOT)) return false;
	const lot = getMarketLot(lotId);
	if (!lot) return false;
	return [...lots.owned, ...PLAZA_LOTS].some((id) => {
		const other = getMarketLot(id);
		return other ? touches(lot, other) : false;
	});
}

export function getLotStatus(lots: LotsState | undefined, lotId: string): LotStatus {
	if (PLAZA_LOTS.includes(lotId)) return "praca";
	const state = lots ?? createLotsState();
	if (state.cleared.includes(lotId)) return "seu";
	if (state.clearing?.lotId === lotId) return "limpando";
	if (state.owned.includes(lotId)) return "comprado";
	return isLotReachable(state, lotId) ? "venda" : "bloqueado";
}

/** Coins to clear a bought lot (a tenth of its price). */
export function getLotClearCost(lot: MarketLot) {
	return Math.max(30, Math.round((lot.price * 0.1) / 10) * 10);
}

/** Time the crew takes to clear a lot: a little shorter than an expansion obra of the same price. */
export function getLotClearDuration(lot: MarketLot) {
	return Math.max(MIN_BUILD_MS / 3, Math.round(getBuildDurationForCost(lot.price) * 0.6));
}

/** Experience for clearing a lot (the junk sold to the scrap dealer pays the crew). */
export function getLotClearExperience(lot: MarketLot) {
	return Math.round(10 + Math.sqrt(lot.price) * 0.6);
}

export type LotCheck = { ok: true; lot: MarketLot } | { ok: false; reason: string };

export function checkBuyLot(lots: LotsState, coins: number, lotId: string): LotCheck {
	const lot = getMarketLot(lotId);
	if (!lot || !buyable.has(lotId)) return { ok: false, reason: "Este terreno não está à venda." };
	if (lots.owned.includes(lotId)) return { ok: false, reason: "Você já comprou este terreno." };
	if (!isLotReachable(lots, lotId)) return { ok: false, reason: "Compre antes um terreno vizinho." };
	if (coins < lot.price) return { ok: false, reason: "Moedas insuficientes" };
	return { ok: true, lot };
}

export function checkClearLot(lots: LotsState, coins: number, lotId: string): LotCheck {
	const lot = getMarketLot(lotId);
	if (!lot || !lots.owned.includes(lotId)) return { ok: false, reason: "Compre o terreno primeiro." };
	if (lots.cleared.includes(lotId)) return { ok: false, reason: "O terreno já está limpo." };
	if (lots.clearing) return { ok: false, reason: "A equipe já está limpando outro terreno." };
	if (coins < getLotClearCost(lot)) return { ok: false, reason: "Moedas insuficientes" };
	return { ok: true, lot };
}

export function startLotClearing(lots: LotsState, lot: MarketLot, now: number): LotsState {
	return { ...lots, clearing: { lotId: lot.id, startedAt: now, endsAt: now + getLotClearDuration(lot) } };
}

/** Finishes the clearing when its time has come. Returns the same object when nothing changed. */
export function finishLotClearing(lots: LotsState, now: number): LotsState {
	if (!lots.clearing || lots.clearing.endsAt > now) return lots;
	return { ...lots, cleared: [...lots.cleared, lots.clearing.lotId], clearing: null };
}

/** Lots the expansion `eraId` needs that are not bought and cleared yet. */
export function getMissingLots(lots: LotsState | undefined, eraId: MarketEraId) {
	const cleared = lots?.cleared ?? [];
	return (ERA_LOTS[eraId] ?? []).filter((id) => !cleared.includes(id));
}

/** Total land an expansion still needs: price to buy plus price to clear. */
export function getMissingLotsCost(lots: LotsState | undefined, eraId: MarketEraId) {
	return getMissingLots(lots, eraId).reduce((total, id) => {
		const lot = getMarketLot(id);
		if (!lot) return total;
		return total + (lots?.owned.includes(id) ? 0 : lot.price) + getLotClearCost(lot);
	}, 0);
}

export function describeMissingLots(lots: LotsState | undefined, eraId: MarketEraId) {
	const names = getMissingLots(lots, eraId).map((id) => getMarketLot(id)?.label ?? id);
	if (!names.length) return "";
	return `Precisa ${names.length === 1 ? "do terreno" : "dos terrenos"} ${names.join(", ")} (comprado${names.length === 1 ? "" : "s"} e limpo${names.length === 1 ? "" : "s"}) para ${getMarketEra(eraId).name}.`;
}
