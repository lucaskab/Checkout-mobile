import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { ItemDefinition, ItemRarity } from "@/@types/item";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { getMarketCategoryProductId } from "@/data/game-icon-assets";
import { itemCategories } from "@/data/market-products";

export const UnlockedProductCard = ({
	inventoryAmount,
	inventoryCapacity,
	onPress,
	product,
}: {
	inventoryAmount: number;
	inventoryCapacity: number;
	onPress: () => void;
	product: ItemDefinition;
}) => {
	const category = itemCategories.find((item) => item.id === product.category);

	function getRarityChipStyle(rarity: ItemRarity) {
		return {
			colecionavel: styles.collectibleChip,
			comum: styles.commonChip,
			epico: styles.epicChip,
			incomum: styles.uncommonChip,
			lendario: styles.legendaryChip,
			luxo: styles.luxuryChip,
			raro: styles.rareChip,
		}[rarity];
	}

	function getRarityTextStyle(rarity: ItemRarity) {
		return {
			colecionavel: styles.collectibleText,
			comum: styles.commonText,
			epico: styles.epicText,
			incomum: styles.uncommonText,
			lendario: styles.legendaryText,
			luxo: styles.luxuryText,
			raro: styles.rareText,
		}[rarity];
	}

	function getRarityCardStyle(rarity: ItemRarity) {
		return {
			colecionavel: styles.collectibleCard,
			comum: styles.commonCard,
			epico: styles.epicCard,
			incomum: styles.uncommonCard,
			lendario: styles.legendaryCard,
			luxo: styles.luxuryCard,
			raro: styles.rareCard,
		}[rarity];
	}

	function formatRarity(rarity: ItemRarity) {
		return rarity.charAt(0).toUpperCase() + rarity.slice(1);
	}

	function Metric({
		icon,
		label,
		value,
	}: {
		icon?: "coin";
		label: string;
		value: string;
	}) {
		return (
			<View style={styles.metric}>
				<View style={styles.metricValueRow}>
					{icon && <GameIcon icon={icon} style={styles.metricIcon} />}
					<Text style={styles.metricValue}>{value}</Text>
				</View>
				<Text style={styles.metricLabel}>{label}</Text>
			</View>
		);
	}

	return (
		<Pressable
			onPress={onPress}
			style={[styles.card, getRarityCardStyle(product.rarity)]}
		>
			<View style={styles.cardTopRow}>
				<View style={styles.productIdentity}>
					<View style={styles.productVisual}>
						<ProductImage productId={product.id} style={styles.productImage} />
					</View>
					<View style={styles.productCopy}>
						<Text numberOfLines={1} style={styles.productName}>
							{product.name}
						</Text>
						<View style={styles.categoryRow}>
							<ProductImage
								productId={getMarketCategoryProductId(product.category)}
								style={styles.categoryIcon}
							/>
							<Text style={styles.categoryText}>
								{category?.label ?? product.category}
							</Text>
						</View>
					</View>
				</View>
				<View style={[styles.rarityChip, getRarityChipStyle(product.rarity)]}>
					<Text style={[styles.rarityText, getRarityTextStyle(product.rarity)]}>
						{formatRarity(product.rarity)}
					</Text>
				</View>
			</View>
			<View style={styles.metricsRow}>
				<Metric
					icon="coin"
					label="Venda"
					value={product.sellingPrice.toString()}
				/>
				<Metric icon="coin" label="Lucro" value={`+${product.profitPerUnit}`} />
				<Metric label="XP" value={`+${product.xpPerSale}`} />
			</View>
			<View style={styles.stockRow}>
				<View style={styles.stockCopy}>
					<Text style={styles.stockLabel}>Estoque atual</Text>
					<Text style={styles.stockValue}>
						{inventoryAmount} / {inventoryCapacity} unid.
					</Text>
				</View>
				<View style={styles.stockTrack}>
					<View
						style={[
							styles.stockFill,
							{
								width: `${Math.min(
									100,
									Math.round((inventoryAmount / inventoryCapacity) * 100),
								)}%`,
							},
						]}
					/>
				</View>
				<Text
					style={[
						styles.stockStatus,
						inventoryAmount > 0 ? styles.stockReady : styles.stockEmpty,
					]}
				>
					{inventoryAmount > 0 ? "Disponível" : "Reabasteça"}
				</Text>
			</View>
			<Text style={styles.upgradeHint}>Toque para ampliar o estoque</Text>
		</Pressable>
	);
};

const styles = StyleSheet.create((theme) => ({
	card: {
		marginTop: theme.gap(1),
		padding: theme.gap(1.5),
		borderLeftWidth: theme.gap(0.5),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	cardTopRow: {
		flexDirection: "row",
		alignItems: "flex-start",
		justifyContent: "space-between",
	},
	productIdentity: {
		flex: 1,
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		paddingRight: theme.gap(1),
	},
	productVisual: {
		width: theme.gap(5.5),
		height: theme.gap(5.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	productImage: {
		width: theme.gap(5),
		height: theme.gap(5),
	},
	productCopy: {
		flex: 1,
	},
	productName: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	categoryText: {
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	categoryRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
		marginTop: 2,
	},
	categoryIcon: {
		width: 18,
		height: 18,
	},
	rarityChip: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.375),
		borderRadius: theme.gap(1),
	},
	rarityText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
	},
	metricsRow: {
		flexDirection: "row",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1.25),
	},
	metric: {
		flex: 1,
		paddingVertical: theme.gap(0.75),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-100"],
		alignItems: "center",
	},
	metricValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-800"],
		fontSize: 11,
		fontWeight: "700",
	},
	metricValueRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.2),
	},
	metricIcon: {
		width: 16,
		height: 16,
	},
	metricLabel: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 9,
		fontWeight: "600",
	},
	stockRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginTop: theme.gap(1.25),
	},
	stockCopy: {
		width: theme.gap(12),
	},
	stockLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "600",
	},
	stockValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["neutral-700"],
		fontSize: 11,
		fontWeight: "700",
	},
	stockTrack: {
		flex: 1,
		height: theme.gap(0.75),
		overflow: "hidden",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-150"],
	},
	stockFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["green-500"],
	},
	stockStatus: {
		fontSize: 10,
		fontWeight: "700",
	},
	stockReady: { color: theme.colors["green-600"] },
	stockEmpty: { color: theme.colors["red-500"] },
	upgradeHint: {
		marginTop: theme.gap(0.75),
		color: theme.colors["violet-600"],
		fontSize: 10,
		fontWeight: "700",
		textAlign: "right",
	},
	commonCard: { borderLeftColor: theme.colors["blue-400"] },
	uncommonCard: { borderLeftColor: theme.colors["green-500"] },
	rareCard: { borderLeftColor: theme.colors["violet-500"] },
	epicCard: { borderLeftColor: theme.colors["amber-500"] },
	legendaryCard: { borderLeftColor: theme.colors["amber-400"] },
	luxuryCard: { borderLeftColor: theme.colors["red-500"] },
	collectibleCard: { borderLeftColor: theme.colors["violet-400"] },

	commonChip: { backgroundColor: theme.colors["blue-50"] },
	uncommonChip: { backgroundColor: theme.colors["green-50"] },
	rareChip: { backgroundColor: theme.colors["violet-50"] },
	epicChip: { backgroundColor: theme.colors["amber-50"] },
	legendaryChip: { backgroundColor: theme.colors["amber-100"] },
	luxuryChip: { backgroundColor: theme.colors["red-50"] },
	collectibleChip: { backgroundColor: theme.colors["violet-100"] },
	commonText: { color: theme.colors["blue-600"] },
	uncommonText: { color: theme.colors["green-600"] },
	rareText: { color: theme.colors["violet-600"] },
	epicText: { color: theme.colors["amber-600"] },
	legendaryText: { color: theme.colors["amber-600"] },
	luxuryText: { color: theme.colors["red-600"] },
	collectibleText: { color: theme.colors["violet-600"] },
}));
