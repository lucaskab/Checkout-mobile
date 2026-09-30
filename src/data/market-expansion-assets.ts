import type { ImageSourcePropType } from "react-native";
import type { MarketExpansionId } from "@/@types/market-expansion";

export const marketExpansionAssets: Record<
	MarketExpansionId,
	ImageSourcePropType
> = {
	"fresh-wing": require("../../assets/game-art/expansions/fresh-wing.png"),
	"grand-warehouse": require("../../assets/game-art/expansions/grand-warehouse.png"),
	"premium-hall": require("../../assets/game-art/expansions/premium-hall.png"),
	"service-wing": require("../../assets/game-art/expansions/service-wing.png"),
	"stock-annex": require("../../assets/game-art/expansions/stock-annex.png"),
};
