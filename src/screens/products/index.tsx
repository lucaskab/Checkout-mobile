import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { ItemDefinition } from "@/@types/item";
import { useBottomSheet } from "@/components/bottom-sheet";
import { useGameStore } from "@/stores/game-store";
import { InventoryCapacitySheet } from "./components/inventory-capacity-sheet";
import { ProductList } from "./components/product-list";

export function ProductsScreen() {
	const { openBottomSheet } = useBottomSheet();
	const inventory = useGameStore((state) => state.inventory);
	const inventoryCapacityLevels = useGameStore(
		(state) => state.inventoryCapacityLevels,
	);
	const market = useGameStore((state) => state.market);

	function openInventoryCapacity(product: ItemDefinition) {
		openBottomSheet(<InventoryCapacitySheet product={product} />);
	}

	return (
		<View style={styles.screen}>
			<ProductList
				inventory={inventory}
				inventoryCapacityLevels={inventoryCapacityLevels}
				level={market.level}
				onPressProduct={openInventoryCapacity}
				unlockedProductIds={market.unlockedProductIds}
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	screen: {
		flex: 1,
		backgroundColor: theme.colors["neutral-50"],
	},
}));
