import type { SimulatorLayout } from "@/@types/simulator";
import {
	marketBuildingExpansionIds,
	normalizeMarketExpansionIds,
} from "@/data/market-expansions";

export function getSimulatorLayout(expansionIds: unknown): SimulatorLayout {
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
		sectorIds: [
			"padaria",
			...(ids.includes("fresh-wing") ? ["queijaria"] : []),
			...(ids.includes("service-wing") ? ["acougue"] : []),
			...(ids.includes("stock-annex") ? ["peixaria"] : []),
			...(ids.includes("service-wing") ? ["bebidas"] : []),
			...(ids.includes("premium-hall") ? ["sorvetes"] : []),
			...(storageLarge ? ["adega"] : []),
		],
	};
}
