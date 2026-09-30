import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { ShopItemDefinition } from "@/@types/shop";
import { useGameStore } from "@/stores/game-store";
import { BuildPanel } from "@/components/build-panel";
import { getInteriorBuildName } from "@/data/interior-construction";
import { getShopItemBuildStatus } from "@/services/interior-construction";
import { ItemsList } from "./components/items-list";

export function ShopScreen() {
	const coins = useGameStore((state) => state.coins);
	const diamonds = useGameStore((state) => state.logistics.premiumCurrency);
	const level = useGameStore((state) => state.market.level);
	const shop = useGameStore((state) => state.shop);
	const purchaseShopItem = useGameStore((state) => state.purchaseShopItem);
	const interiorConstructions = useGameStore((state) => state.interiorConstructions);
	const finishInteriorConstructionNow = useGameStore((state) => state.finishInteriorConstructionNow);
	// Fixtures being installed by the builders (second checkout, self-checkout).
	const installing = interiorConstructions.filter((item) => item.kind === "shop");

	function purchase(item: ShopItemDefinition) {
		return purchaseShopItem(item.id, item.diamondPrice ? "diamonds" : "coins");
	}

	return (
		<View style={styles.screen}>
			{installing.map((item) => (
				<View key={item.id} style={styles.build}>
					<BuildPanel
						coins={coins}
						diamonds={diamonds}
						onSpeedUp={() => finishInteriorConstructionNow(item.id)}
						status={getShopItemBuildStatus({ interiorConstructions, shop } as Parameters<typeof getShopItemBuildStatus>[0], item.targetId) ?? {
							status: "built", reason: "", coinCost: 0, diamondCost: 0, durationMs: 0, construction: null, remainingMs: 0, progress: 0, skipCost: 0,
						}}
						title={`Instalando ${getInteriorBuildName(item.kind, item.targetId)}`}
					/>
				</View>
			))}
			<ItemsList
				coins={coins}
				consumableAmounts={shop.consumableAmounts}
				diamonds={diamonds}
				level={level}
				onPurchase={purchase}
				ownedItemIds={[...shop.ownedItemIds, ...installing.map((item) => item.targetId)]}
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	screen: { flex: 1, backgroundColor: theme.colors["neutral-50"] },
	build: { paddingHorizontal: theme.gap(1.5), paddingTop: theme.gap(1) },
}));
