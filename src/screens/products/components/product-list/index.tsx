import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { useState } from "react";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { GameInventoryCapacityLevels } from "@/@types/game";
import type { ItemDefinition } from "@/@types/item";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import type { GameIconId } from "@/data/game-icon-assets";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import { itemCatalog } from "@/data/market-products";
import { LockedProductCard } from "./components/locked-product-card";
import { UnlockedProductCard } from "./components/unlocked-product-card";

type ProductFilter = "todos" | "desbloqueados" | "bloqueados";

type ProductListProps = {
	inventory: Record<number, number>;
	inventoryCapacityLevels: GameInventoryCapacityLevels;
	level: number;
	onPressProduct: (product: ItemDefinition) => void;
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
	onPressProduct,
	unlockedProductIds,
}: ProductListProps) {
	const [filter, setFilter] = useState<ProductFilter>("todos");
	const unlockedProducts = itemCatalog.filter((product) =>
		unlockedProductIds.includes(product.id),
	);
	const filteredProducts = itemCatalog.filter((product) => {
		const isUnlocked = unlockedProductIds.includes(product.id);

		if (filter === "desbloqueados") {
			return isUnlocked;
		}

		if (filter === "bloqueados") {
			return !isUnlocked;
		}

		return true;
	});

	function renderProduct({ item }: LegendListRenderItemProps<ItemDefinition>) {
		const isUnlocked = unlockedProductIds.includes(item.id);

		return isUnlocked ? (
			<UnlockedProductCard
				inventoryAmount={inventory[item.id] ?? 0}
				inventoryCapacity={getInventoryCapacity(
					item,
					inventoryCapacityLevels[item.id],
				)}
				onPress={() => onPressProduct(item)}
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
			estimatedItemSize={145}
			extraData={{
				inventory,
				inventoryCapacityLevels,
				level,
				unlockedProductIds,
			}}
			keyExtractor={(product) => product.id.toString()}
			ListHeaderComponent={
				<View>
					<View style={styles.summaryRow}>
						<SummaryCard
							icon="success"
							label="Desbloqueados"
							value={unlockedProducts.length.toString()}
						/>
						<SummaryCard
							icon="package"
							label="Em estoque"
							value={unlockedProducts
								.reduce(
									(total, product) => total + (inventory[product.id] ?? 0),
									0,
								)
								.toString()}
						/>
						<SummaryCard
							icon="lock"
							label="Próximo nível"
							value={`Nv ${getNextUnlockLevel(level)}`}
						/>
					</View>
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
						<Text style={styles.listTitle}>Catálogo de produtos</Text>
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

type SummaryCardProps = {
	icon: GameIconId;
	label: string;
	value: string;
};

function SummaryCard({ icon, label, value }: SummaryCardProps) {
	return (
		<View style={styles.summaryCard}>
			<GameIcon icon={icon} style={styles.summaryIcon} />
			<Text style={styles.summaryValue}>{value}</Text>
			<Text style={styles.summaryLabel}>{label}</Text>
		</View>
	);
}

function getNextUnlockLevel(level: number) {
	return (
		itemCatalog.find((product) => product.unlockLevel > level)?.unlockLevel ??
		level
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		paddingHorizontal: theme.gap(1.75),
		paddingTop: theme.gap(1.25),
		paddingBottom: theme.gap(3),
		backgroundColor: theme.colors["neutral-50"],
	},
	summaryRow: {
		flexDirection: "row",
		gap: theme.gap(0.75),
	},
	summaryCard: {
		flex: 1,
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["neutral-0"],
	},
	summaryIcon: {
		width: 24,
		height: 24,
	},
	summaryValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: theme.gap(0.5),
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	summaryLabel: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "600",
	},
	filterRow: {
		flexDirection: "row",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1.5),
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
