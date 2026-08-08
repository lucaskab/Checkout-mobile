import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { ShopItemDefinition } from "@/@types/shop";
import { useGameStore } from "@/stores/game-store";
import { ItemsList } from "./components/items-list";

export function ShopScreen() {
	const coins = useGameStore((state) => state.coins);
	const diamonds = useGameStore((state) => state.logistics.premiumCurrency);
	const level = useGameStore((state) => state.market.level);
	const shop = useGameStore((state) => state.shop);
	const purchaseShopItem = useGameStore((state) => state.purchaseShopItem);

	function purchase(item: ShopItemDefinition) {
		return purchaseShopItem(item.id, item.diamondPrice ? "diamonds" : "coins");
	}

	return (
		<View style={styles.screen}>
			<ItemsList
				coins={coins}
				consumableAmounts={shop.consumableAmounts}
				diamonds={diamonds}
				level={level}
				onPurchase={purchase}
				ownedItemIds={shop.ownedItemIds}
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	screen: { flex: 1, backgroundColor: theme.colors["neutral-50"] },
}));
