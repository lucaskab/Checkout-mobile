import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { useEffect, useState } from "react";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { GameInventoryCapacityLevels } from "@/@types/game";
import type { ItemDefinition } from "@/@types/item";
import type { SupplierOrder } from "@/@types/logistics";
import { GameText as Text } from "@/components/game-text";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import { itemCatalog } from "@/data/market-products";
import {
	getOrderRemainingTime,
	getSupplierOrderStatus,
} from "@/services/logistics";
import { LockedProductCard } from "./components/locked-product-card";
import { UnlockedProductCard } from "./components/unlocked-product-card";

type ProductFilter = "todos" | "desbloqueados" | "bloqueados";

type ProductListProps = {
	inventory: Record<number, number>;
	inventoryCapacityLevels: GameInventoryCapacityLevels;
	level: number;
	onUpgradeProduct: (product: ItemDefinition) => void;
	onRestockProduct: (product: ItemDefinition) => void;
	orders: SupplierOrder[];
	unlockedProductIds: number[];
};

const filters: { id: ProductFilter; label: string }[] = [
	{ id: "todos", label: "Todos" },
	{ id: "desbloqueados", label: "Desbloqueados" },
	{ id: "bloqueados", label: "Bloqueados" },
];

export function ProductList({
	inventory,
	inventoryCapacityLevels,
	level,
	onUpgradeProduct,
	onRestockProduct,
	orders,
	unlockedProductIds,
}: ProductListProps) {
	const [filter, setFilter] = useState<ProductFilter>("todos");
	const [currentTime, setCurrentTime] = useState(Date.now());
	const hasActiveOrders = orders.some(
		(order) => getSupplierOrderStatus(order, currentTime) !== "entregue",
	);
	const filteredProducts = itemCatalog
		.filter((product) => {
			const isUnlocked = unlockedProductIds.includes(product.id);

			if (filter === "desbloqueados") {
				return isUnlocked;
			}

			if (filter === "bloqueados") {
				return !isUnlocked;
			}

			return true;
		})
		.sort(
			(firstProduct, secondProduct) =>
				firstProduct.unlockLevel - secondProduct.unlockLevel ||
				firstProduct.name.localeCompare(secondProduct.name, "pt-BR"),
		);

	useEffect(() => {
		if (!hasActiveOrders) {
			return;
		}

		const interval = setInterval(() => setCurrentTime(Date.now()), 1_000);

		return () => clearInterval(interval);
	}, [hasActiveOrders]);

	function renderProduct({ item }: LegendListRenderItemProps<ItemDefinition>) {
		const isUnlocked = unlockedProductIds.includes(item.id);
		const incomingOrder = orders.find(
			(order) =>
				order.productId === item.id &&
				getSupplierOrderStatus(order, currentTime) !== "entregue",
		);

		return isUnlocked ? (
			<UnlockedProductCard
				inventoryAmount={inventory[item.id] ?? 0}
				inventoryCapacity={getInventoryCapacity(
					item,
					inventoryCapacityLevels[item.id],
				)}
				incomingQuantity={incomingOrder?.quantity}
				incomingTime={
					incomingOrder
						? getOrderRemainingTime(incomingOrder, currentTime)
						: undefined
				}
				onUpgrade={() => onUpgradeProduct(item)}
				onRestock={() => onRestockProduct(item)}
				product={item}
			/>
		) : (
			<LockedProductCard playerLevel={level} product={item} />
		);
	}

	return (
		<LegendList
			contentContainerStyle={styles.content}
			data={filteredProducts}
			estimatedItemSize={120}
			extraData={{
				currentTime,
				inventory,
				inventoryCapacityLevels,
				level,
				orders,
				unlockedProductIds,
			}}
			keyExtractor={(product) => product.id.toString()}
			ListHeaderComponent={
				<View>
					<View style={styles.filterRow}>
						{filters.map((filterOption) => {
							const isActive = filter === filterOption.id;

							return (
								<Pressable
									key={filterOption.id}
									onPress={() => setFilter(filterOption.id)}
									style={[styles.filter, isActive && styles.activeFilter]}
								>
									<Text
										style={[
											styles.filterText,
											isActive && styles.activeFilterText,
										]}
									>
										{filterOption.label}
									</Text>
								</Pressable>
							);
						})}
					</View>
					<View style={styles.listHeader}>
						<Text style={styles.listTitle}>Catálogo por nível</Text>
						<Text style={styles.listCount}>
							{filteredProducts.length} itens
						</Text>
					</View>
				</View>
			}
			renderItem={renderProduct}
		/>
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		paddingHorizontal: theme.gap(1.75),
		paddingTop: theme.gap(1.25),
		paddingBottom: theme.gap(3),
		backgroundColor: theme.colors["neutral-50"],
	},
	filterRow: {
		flexDirection: "row",
		gap: theme.gap(0.75),
	},
	filter: {
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(0.75),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-100"],
	},
	activeFilter: {
		backgroundColor: theme.colors["blue-500"],
	},
	filterText: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	activeFilterText: {
		color: theme.colors["neutral-0"],
	},
	listHeader: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		marginTop: theme.gap(2),
		marginBottom: theme.gap(0.5),
	},
	listTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	listCount: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		fontWeight: "600",
	},
}));
