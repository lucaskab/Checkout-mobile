import { gameIconAssets } from "@/data/game-icon-assets";
import { marketExpansionAssets } from "@/data/market-expansion-assets";
import { productAssets } from "@/data/product-assets";

export const gameImageAssets = Array.from(
	new Set([
		...Object.values(productAssets),
		...Object.values(gameIconAssets),
		...Object.values(marketExpansionAssets),
	]),
).filter((source): source is number => typeof source === "number");
