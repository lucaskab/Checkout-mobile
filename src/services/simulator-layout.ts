import type { SimulatorLayout } from "@/@types/simulator";
import {
	marketBuildingExpansionIds,
	normalizeMarketExpansionIds,
} from "@/data/market-expansions";

export function getSimulatorLayout(expansionIds: unknown): SimulatorLayout {
	const ids = normalizeMarketExpansionIds(expansionIds);
	// Only the shop wings enlarge the building; the central warehouse sits out back.
	const stage = ids.filter((id) => marketBuildingExpansionIds.includes(id)).length;
	// Keep in sync with Scales in CheckoutExpansionPreviewWindow.cs (Unity). The west wall stays by the
	// parking aisle: the shop grows east until it reaches the street, and back towards the yard.
	const sizes = [
		[0.82, 0.72],
		[0.96, 0.82],
		[1.1, 0.92],
		[1.24, 1.03],
		[1.38, 1.14],
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
