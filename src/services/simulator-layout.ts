import type { SimulatorLayout } from "@/@types/simulator";
import { normalizeMarketExpansionIds } from "@/data/market-expansions";

export function getSimulatorLayout(expansionIds: unknown): SimulatorLayout {
	const ids = normalizeMarketExpansionIds(expansionIds);
	const stage = ids.length;
	const sizes = [
		[0.78, 0.68],
		[0.86, 0.78],
		[0.93, 0.88],
		[1, 1],
		[1.12, 1.12],
	];
	const [widthScale, depthScale] = sizes[stage];
	return {
		stage,
		widthScale,
		depthScale,
		storage: ids.includes("fresh-wing"),
		parking: ids.includes("service-wing"),
		loadingYard: ids.includes("stock-annex"),
		premium: ids.includes("premium-hall"),
		sectorIds: [
			"padaria",
			...(ids.includes("fresh-wing") ? ["queijaria"] : []),
			...(ids.includes("service-wing") ? ["acougue"] : []),
			...(ids.includes("stock-annex") ? ["peixaria"] : []),
			...(ids.includes("service-wing") ? ["bebidas"] : []),
			...(ids.includes("premium-hall") ? ["sorvetes"] : []),
		],
	};
}
