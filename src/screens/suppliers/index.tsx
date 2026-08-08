import { useState } from "react";
import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type {
	SupplierCategory,
	SupplierCategoryOption,
} from "@/@types/supplier";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import { itemCatalog, itemCategories } from "@/data/market-products";
import { getActiveGameEventEffects } from "@/services/game-events";
import { useGameStore } from "@/stores/game-store";
import { CategoryList } from "./components/category-list";
import { ItemsList } from "./components/items-list";
import { initialProducts } from "./components/items-list/static";
import { LogisticsPanel } from "./components/logistics-panel";

const categories: SupplierCategoryOption[] = [
	{ id: "todos", label: "Todos" },
	...itemCategories,
];

export function SuppliersScreen() {
	const [activeCategory, setActiveCategory] =
		useState<SupplierCategory>("todos");
	const coins = useGameStore((state) => state.coins);
	const events = useGameStore((state) => state.events);
	const inventory = useGameStore((state) => state.inventory);
	const inventoryCapacityLevels = useGameStore(
		(state) => state.inventoryCapacityLevels,
	);
	const orders = useGameStore((state) => state.logistics.orders);
	const emergencyTokens = useGameStore(
		(state) => state.logistics.emergencyTokens,
	);
	const supplierOrderSlots = useGameStore(
		(state) => state.logistics.supplierOrderSlots,
	);
	const unlockedProductIds = useGameStore(
		(state) => state.market.unlockedProductIds,
	);
	const placeSupplierOrder = useGameStore((state) => state.placeSupplierOrder);
	const completeOrderFinalStage = useGameStore(
		(state) => state.completeOrderFinalStage,
	);
	const deliverOrderInstantly = useGameStore(
		(state) => state.deliverOrderInstantly,
	);
	const eventEffects = getActiveGameEventEffects(events);
	const products = initialProducts
		.filter((product) => unlockedProductIds.includes(product.id))
		.map((product) => {
			const catalogProduct = itemCatalog.find((item) => item.id === product.id);

			return {
				...product,
				capacity: catalogProduct
					? getInventoryCapacity(
							catalogProduct,
							inventoryCapacityLevels[product.id],
						)
					: 0,
				owned: inventory[product.id] ?? 0,
				price: Math.ceil(product.price * eventEffects.supplierCostMultiplier),
				shelfTime: formatSupplierTime(
					product.shelfTime,
					eventEffects.supplierDurationMultiplier,
				),
			};
		});

	const totalOwned = products.reduce(
		(total, product) => total + product.owned,
		0,
	);
	const totalCapacity = products.reduce(
		(total, product) => total + product.capacity,
		0,
	);

	function selectCategory(category: SupplierCategory) {
		setActiveCategory(category);
	}

	function placeOrder(product: (typeof products)[number]) {
		return placeSupplierOrder({
			productId: product.id,
			quantity: product.quantity,
		});
	}

	return (
		<View style={styles.screen}>
			<View style={styles.header}>
				<View style={styles.stockSummary}>
					<View style={styles.stockIconWrap}>
						<GameIcon icon="package" style={styles.stockIcon} />
					</View>
					<View style={styles.stockCopy}>
						<View style={styles.stockTitleRow}>
							<Text style={styles.stockTitle}>Meu estoque</Text>
							<Text style={styles.stockValue}>
								{totalOwned} / {totalCapacity} unid.
							</Text>
						</View>
						<View style={styles.progressTrack}>
							<View
								style={[
									styles.progressFill,
									{
										width: `${Math.min(
											(totalOwned / Math.max(totalCapacity, 1)) * 100,
											100,
										)}%`,
									},
								]}
							/>
						</View>
					</View>
				</View>
				<LogisticsPanel />
			</View>

			<CategoryList
				activeCategory={activeCategory}
				categories={categories}
				onSelectCategory={selectCategory}
			/>
			<ItemsList
				products={products}
				activeCategory={activeCategory}
				coins={coins}
				emergencyTokens={emergencyTokens}
				orders={orders}
				onCompleteOrderFinalStage={completeOrderFinalStage}
				onDeliverOrderInstantly={deliverOrderInstantly}
				onPlaceOrder={placeOrder}
				supplierOrderSlots={supplierOrderSlots}
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	screen: {
		flex: 1,
		backgroundColor: theme.colors["neutral-50"],
	},
	header: {
		paddingHorizontal: theme.gap(2),
		paddingVertical: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
		borderBottomWidth: 1,
		borderBottomColor: theme.colors["neutral-150"],
	},
	stockSummary: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-50"],
	},
	stockIconWrap: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	stockIcon: {
		width: theme.gap(3.5),
		height: theme.gap(3.5),
	},
	stockCopy: {
		flex: 1,
	},
	stockTitleRow: {
		flexDirection: "row",
		justifyContent: "space-between",
	},
	stockTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	stockValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	progressTrack: {
		height: theme.gap(0.75),
		overflow: "hidden",
		marginTop: theme.gap(0.75),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-100"],
	},
	progressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-500"],
	},
	toast: {
		position: "absolute",
		left: theme.gap(2),
		right: theme.gap(2),
		bottom: theme.gap(2),
		paddingHorizontal: theme.gap(1.5),
		paddingVertical: theme.gap(1.25),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-600"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 5 },
		shadowOpacity: 0.2,
		shadowRadius: 12,
		elevation: 5,
	},
	errorToast: {
		backgroundColor: theme.colors["red-500"],
	},
	toastText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
		textAlign: "center",
	},
}));

function formatSupplierTime(supplierTime: string, multiplier: number) {
	const minutes = Number.parseInt(supplierTime, 10);

	return `${Math.max(1, Math.ceil(minutes * multiplier))}m`;
}
