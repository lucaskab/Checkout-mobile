import { useState } from "react";
import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StyleSheet } from "react-native-unistyles";
import type {
	SupplierCategory,
	SupplierCategoryOption,
} from "@/@types/supplier";
import { itemCategories } from "@/data/market-products";
import { useGameStore } from "@/stores/game-store";
import { CategoryList } from "./components/category-list";
import { ItemsList } from "./components/items-list";
import { initialProducts } from "./components/items-list/static";
import { LogisticsPanel } from "./components/logistics-panel";

const categories: SupplierCategoryOption[] = [
	{ id: "todos", emoji: "🛒", label: "Todos" },
	...itemCategories,
];

export function SuppliersScreen() {
	const insets = useSafeAreaInsets();
	const [activeCategory, setActiveCategory] =
		useState<SupplierCategory>("todos");
	const coins = useGameStore((state) => state.coins);
	const inventory = useGameStore((state) => state.inventory);
	const orders = useGameStore((state) => state.logistics.orders);
	const emergencyTokens = useGameStore(
		(state) => state.logistics.emergencyTokens,
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
	const products = initialProducts
		.filter((product) => unlockedProductIds.includes(product.id))
		.map((product) => ({
			...product,
			owned: inventory[product.id] ?? 0,
		}));

	const totalOwned = products.reduce(
		(total, product) => total + product.owned,
		0,
	);

	function selectCategory(category: SupplierCategory) {
		setActiveCategory(category);
	}

	function placeOrder(product: (typeof products)[number]) {
		return placeSupplierOrder({
			productId: product.id,
			quantity: product.quantity,
			totalCost: product.price,
		});
	}

	return (
		<View style={[styles.screen, { paddingTop: insets.top + 8 }]}>
			<View style={styles.header}>
				<View style={styles.headerRow}>
					<View style={styles.headerCopy}>
						<Text style={styles.title}>Fornecedores</Text>
						<Text style={styles.subtitle}>
							Compre produtos para abastecer suas prateleiras.
						</Text>
					</View>
					<View style={styles.coinChip}>
						<Text style={styles.coinChipText}>
							🪙 {coins.toLocaleString("pt-BR")}
						</Text>
					</View>
				</View>
				<View style={styles.stockSummary}>
					<View style={styles.stockIconWrap}>
						<Text style={styles.stockIcon}>📦</Text>
					</View>
					<View style={styles.stockCopy}>
						<View style={styles.stockTitleRow}>
							<Text style={styles.stockTitle}>Meu estoque</Text>
							<Text style={styles.stockValue}>{totalOwned} unidades</Text>
						</View>
						<View style={styles.progressTrack}>
							<View
								style={[
									styles.progressFill,
									{ width: `${Math.min((totalOwned / 60) * 100, 100)}%` },
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
		paddingBottom: theme.gap(1.75),
		backgroundColor: theme.colors["neutral-0"],
		borderBottomWidth: 1,
		borderBottomColor: theme.colors["neutral-150"],
	},
	headerRow: {
		flexDirection: "row",
		alignItems: "flex-start",
		justifyContent: "space-between",
	},
	headerCopy: {
		flex: 1,
		paddingRight: theme.gap(1),
	},
	title: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large + 4,
		fontWeight: "700",
	},
	subtitle: {
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		lineHeight: theme.gap(2),
	},
	coinChip: {
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(3),
		backgroundColor: theme.colors["amber-50"],
	},
	coinChipText: {
		color: theme.colors["amber-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	stockSummary: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
		marginTop: theme.gap(1.75),
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
		fontSize: 22,
	},
	stockCopy: {
		flex: 1,
	},
	stockTitleRow: {
		flexDirection: "row",
		justifyContent: "space-between",
	},
	stockTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	stockValue: {
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
