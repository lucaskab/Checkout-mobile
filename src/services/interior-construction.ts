import type { GameState } from "@/@types/game";
import type { InteriorConstruction } from "@/@types/interior-construction";
import {
	constructionDuration,
	findInteriorConstruction,
	getInteriorSkipCost,
	getShelfBuildDurationMs,
	sectorBuildPlans,
	shopItemBuildDurations,
} from "@/data/interior-construction";
import { shelves } from "@/data/market-products";
import { getProductionSector } from "@/data/production-sectors";
import { getNextShelfUnlockUpgrade } from "@/data/shelf-capacity";
import {
	getUnlockedPhysicalShelfCount,
	resolveShelfSlotCounts,
} from "@/data/shelf-slots";
import { getSimulatorLayout } from "@/services/simulator-layout";

/** Where a buildable thing stands, for the screens:
 * - `locked`: the player's level (or a market wing) is still missing;
 * - `available`: can be bought now (it goes to the inventory);
 * - `stored`: bought, waiting in the inventory for the player to place it (build mode);
 * - `queued`: placed, waiting for the builders to finish the works before it;
 * - `busy`: kept for old screens (the crew now works through a queue, so it is not used);
 * - `building`: under construction (see `remainingMs` / `skipCost`);
 * - `built`: ready to use. */
export type InteriorBuildStatus = {
	status: "locked" | "available" | "stored" | "queued" | "busy" | "building" | "built";
	reason: string;
	coinCost: number;
	diamondCost: number;
	durationMs: number;
	construction: InteriorConstruction | null;
	remainingMs: number;
	progress: number;
	skipCost: number;
};

type BuildState = Pick<
	GameState,
	| "builtSectorIds"
	| "interiorConstructions"
	| "market"
	| "shelfSlotCounts"
	| "unlockedShelfSlots"
	| "shop"
	| "unlockedMarketExpansionIds"
>;

function works(
	construction: InteriorConstruction | null,
	now: number,
): Pick<InteriorBuildStatus, "construction" | "remainingMs" | "progress" | "skipCost"> {
	if (!construction) return { construction: null, remainingMs: 0, progress: 0, skipCost: 0 };
	const duration = constructionDuration(construction);
	if (construction.pending)
		return { construction, remainingMs: duration, progress: 0, skipCost: getInteriorSkipCost(duration) };
	if (construction.startedAt > now)
		return { construction, remainingMs: construction.endsAt - now, progress: 0, skipCost: getInteriorSkipCost(duration) };
	const total = Math.max(1, construction.endsAt - construction.startedAt);
	const remainingMs = Math.max(0, construction.endsAt - now);
	return {
		construction,
		remainingMs,
		progress: Math.min(1, Math.max(0, 1 - remainingMs / total)),
		skipCost: getInteriorSkipCost(remainingMs),
	};
}

/** Bought (inventory), queued or building. */
function started(construction: InteriorConstruction, now: number): Pick<InteriorBuildStatus, "status" | "reason"> {
	if (construction.pending) return { status: "stored", reason: "No inventário: coloque no modo construção" };
	if (construction.startedAt > now) return { status: "queued", reason: "Na fila dos construtores" };
	return { status: "building", reason: "Em obra" };
}

export function getSectorBuildStatus(
	state: BuildState,
	sectorId: string,
	now = Date.now(),
): InteriorBuildStatus {
	const sector = getProductionSector(sectorId);
	const plan = sector ? sectorBuildPlans[sector.id] : { coinCost: 0, durationMs: 0 };
	const base = {
		coinCost: plan.coinCost,
		diamondCost: Math.max(1, Math.ceil(plan.coinCost / 1_500)),
		durationMs: plan.durationMs,
	};
	const construction = findInteriorConstruction(state.interiorConstructions, "sector", sectorId);
	if (!sector) return { status: "locked", reason: "Setor desconhecido", ...base, ...works(null, now) };
	if (state.builtSectorIds.includes(sector.id))
		return { status: "built", reason: "", ...base, ...works(null, now) };
	if (construction) return { ...started(construction, now), ...base, ...works(construction, now) };
	if (state.market.level < sector.requiredLevel)
		return { status: "locked", reason: `Nível ${sector.requiredLevel}`, ...base, ...works(null, now) };
	if (!getSimulatorLayout(state.unlockedMarketExpansionIds).sectorIds.includes(sector.id))
		return { status: "locked", reason: "Precisa de uma expansão", ...base, ...works(null, now) };
	return { status: "available", reason: "", ...base, ...works(null, now) };
}

/** The next shelf the player can buy (or the one being built). */
export function getNextShelfBuildStatus(state: BuildState, now = Date.now()) {
	const counts = resolveShelfSlotCounts(state.shelfSlotCounts, state.unlockedShelfSlots);
	const unlocked = getUnlockedPhysicalShelfCount(counts);
	const shelf = shelves[unlocked] ?? null;
	const upgrade = getNextShelfUnlockUpgrade(unlocked);
	const base = {
		coinCost: upgrade?.coinCost ?? 0,
		diamondCost: 0,
		durationMs: getShelfBuildDurationMs(unlocked),
	};
	const construction = shelf
		? findInteriorConstruction(state.interiorConstructions, "shelf", shelf.id)
		: null;
	let result: InteriorBuildStatus;
	if (!shelf || !upgrade) result = { status: "built", reason: "Todas liberadas", ...base, ...works(null, now) };
	else if (construction) result = { ...started(construction, now), ...base, ...works(construction, now) };
	else if (state.market.level < upgrade.playerLevel)
		result = { status: "locked", reason: `Nível ${upgrade.playerLevel}`, ...base, ...works(null, now) };
	else result = { status: "available", reason: "", ...base, ...works(null, now) };
	return { shelf, requiredLevel: upgrade?.playerLevel ?? 1, ...result };
}

/** Fixtures from the shop (second checkout, self-checkout) are installed by the builders. */
export function getShopItemBuildStatus(
	state: BuildState,
	itemId: string,
	now = Date.now(),
): InteriorBuildStatus | null {
	if (!Object.hasOwn(shopItemBuildDurations, itemId)) return null;
	const construction = findInteriorConstruction(state.interiorConstructions, "shop", itemId);
	const base = { coinCost: 0, diamondCost: 0, durationMs: shopItemBuildDurations[itemId] };
	if (state.shop.ownedItemIds.includes(itemId)) return { status: "built", reason: "", ...base, ...works(null, now) };
	if (construction) return { ...started(construction, now), ...base, ...works(construction, now) };
	return { status: "available", reason: "", ...base, ...works(null, now) };
}

/** What the builders are doing right now, if anything. */
export function getActiveInteriorConstruction(state: BuildState, now = Date.now()) {
	const construction =
		state.interiorConstructions.find((item) => !item.pending && item.startedAt <= now) ?? null;
	return construction ? works(construction, now) : null;
}

/** Bought pieces still waiting in the inventory for a spot in the market. */
export function getStoredInteriorBuilds(state: Pick<GameState, "interiorConstructions">) {
	return state.interiorConstructions.filter((item) => item.pending);
}
