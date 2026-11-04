import type { MarketEraId } from "@/@types/economy";
import type { SimulatorLayout } from "@/@types/simulator";
import { getMarketEra } from "@/data/economy";
import {
	marketBuildingExpansionIds,
	normalizeMarketExpansionIds,
} from "@/data/market-expansions";
import { productionSectors } from "@/data/production-sectors";

/** The sectors in the order the layout lists them (the order of the wings that used to bring them). */
const SECTOR_ORDER = ["padaria", "queijaria", "acougue", "peixaria", "bebidas", "sorvetes", "adega"];

/**
 * `eraId`: the market's expansion. Every sector whose expansion the market has reached has a place in the shop too
 * (Lucas 04/11: each sector opens one expansion earlier than the wing that used to bring it, e.g. the cheese counter in
 * the mercadinho before the supermarket's fresh wing). Whether it really fits on the floor is Unity's room check
 * (src/services/interior-room.ts). Without it, only the wings count (the old wing purchases).
 */
export function getSimulatorLayout(expansionIds: unknown, eraId?: MarketEraId): SimulatorLayout {
	const ids = normalizeMarketExpansionIds(expansionIds);
	// Only the shop wings enlarge the building; the central warehouse sits out back.
	const stage = ids.filter((id) => marketBuildingExpansionIds.includes(id)).length;
	// Keep in sync with Scales in CheckoutExpansionPreviewWindow.cs (Unity). The block is a grid of equal lots
	// (src/data/market-lots.ts) and the building fills whole lots from the corner on the left of the avenue
	// (CheckoutMarketLayout.Offset puts its west wall at the lot A1 edge): the mercadinho fills A1 + B1, the
	// supermercado the first two rows of A and B, the hipermercado the whole front (A1–C2). One metre of scale
	// is 19 m of width and 20 m of depth of the base building.
	const sizes = [
		[1.18, 0.65],
		[1.18, 0.98],
		[1.18, 1.3],
		[1.48, 1.3],
		[1.78, 1.3],
	];
	const [widthScale, depthScale] = sizes[stage];
	const storageLarge = ids.includes("grand-warehouse");
	return {
		stage,
		widthScale,
		depthScale,
		storage: ids.includes("fresh-wing") || storageLarge,
		parking: ids.includes("service-wing"),
		loadingYard: ids.includes("stock-annex"),
		premium: ids.includes("premium-hall"),
		storageLarge,
		sectorIds: sectorsFor(ids, storageLarge, eraId),
	};
}

function sectorsFor(ids: readonly string[], storageLarge: boolean, eraId?: MarketEraId) {
	const present = new Set<string>(["padaria"]);
	if (ids.includes("fresh-wing")) present.add("queijaria");
	if (ids.includes("service-wing")) {
		present.add("acougue");
		present.add("bebidas");
	}
	if (ids.includes("stock-annex")) present.add("peixaria");
	if (ids.includes("premium-hall")) present.add("sorvetes");
	if (storageLarge) present.add("adega");
	if (eraId) {
		const reached = getMarketEra(eraId).index;
		for (const sector of productionSectors) if (getMarketEra(sector.eraId).index <= reached) present.add(sector.id);
	}
	return SECTOR_ORDER.filter((id) => present.has(id));
}
