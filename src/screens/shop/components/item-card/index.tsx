import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { ShopItemDefinition, ShopItemQuality } from "@/@types/shop";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getShopItemIcon } from "@/data/game-icon-assets";

type ItemCardProps = {
	canAfford: boolean;
	consumableAmount: number;
	isLocked: boolean;
	isOwned: boolean;
	onPurchase: (item: ShopItemDefinition) => void;
	item: ShopItemDefinition;
};

const qualityStars: Record<ShopItemQuality, number> = {
	comum: 1,
	incomum: 2,
	raro: 3,
	epico: 4,
	lendario: 5,
	mitico: 6,
};

export function ItemCard({
	canAfford,
	consumableAmount,
	isLocked,
	isOwned,
	item,
	onPurchase,
}: ItemCardProps) {
	const quality = getItemQuality(item);
	const isDiamondPurchase = Boolean(item.diamondPrice);
	const price = item.diamondPrice ?? item.coinPrice ?? 0;
	const isLegendary = quality === "lendario" || quality === "mitico";

	return (
		<View style={styles.wrapper}>
			<View
				style={[
					styles.card,
					isLegendary && styles.legendaryCard,
					isLocked && styles.lockedCard,
				]}
			>
				<View style={styles.cardTopRow}>
					<View style={[styles.visual, getQualityVisualStyle(quality)]}>
						<GameIcon icon={getShopItemIcon(item.id)} style={styles.itemIcon} />
						{isLocked && (
							<View style={styles.lockBadge}>
								<GameIcon icon="lock" style={styles.lockIcon} />
							</View>
						)}
					</View>
					<View style={styles.qualityColumn}>
						<View style={[styles.qualityChip, getQualityChipStyle(quality)]}>
							<Text style={styles.qualityText}>{formatQuality(quality)}</Text>
						</View>
						<Text numberOfLines={1} style={styles.stars}>
							{"★".repeat(qualityStars[quality])}
						</Text>
					</View>
				</View>

				<Text numberOfLines={2} style={styles.name}>
					{item.name}
				</Text>

				<View style={styles.priceBlock}>
					<Text style={styles.levelText}>Nível {item.level}</Text>
					<Text
						style={[
							styles.priceText,
							isDiamondPurchase && styles.diamondPriceText,
						]}
					>
						<GameIcon
							icon={isDiamondPurchase ? "diamond" : "coin"}
							style={styles.priceIcon}
						/>{" "}
						{formatPrice(price)}
					</Text>
				</View>

				<Text numberOfLines={3} style={styles.description}>
					{item.description}
				</Text>

				<View style={styles.spacer} />

				{item.isConsumable && consumableAmount > 0 && (
					<View style={styles.amountBadge}>
						<Text style={styles.amountText}>
							No inventário: {consumableAmount}
						</Text>
					</View>
				)}

				<GameButton
					disabled={isOwned || isLocked || !canAfford}
					fullWidth
					label={
						isOwned
							? "Instalado"
							: isLocked
								? `Nível ${item.level}`
								: item.isConsumable
									? "Comprar"
									: isLegendary
										? "Desbloquear"
										: "Comprar"
					}
					onPress={() => onPurchase(item)}
					variant={isOwned ? "success" : isDiamondPurchase ? "gem" : "primary"}
				/>
			</View>
		</View>
	);
}

function getItemQuality(item: ShopItemDefinition): ShopItemQuality {
	if (item.quality) {
		return item.quality;
	}

	if (item.level >= 50) {
		return "lendario";
	}

	if (item.level >= 24) {
		return "epico";
	}

	if (item.level >= 10) {
		return "raro";
	}

	if (item.level >= 5) {
		return "incomum";
	}

	return "comum";
}

function formatQuality(quality: ShopItemQuality) {
	const labels: Record<ShopItemQuality, string> = {
		comum: "Comum",
		incomum: "Incomum",
		raro: "Raro",
		epico: "Épico",
		lendario: "Lendário",
		mitico: "Mítico",
	};

	return labels[quality];
}

function formatPrice(price: number) {
	if (price >= 1_000_000_000) {
		return `${(price / 1_000_000_000).toFixed(0)}B`;
	}

	if (price >= 1_000_000) {
		const value = price / 1_000_000;
		return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}M`;
	}

	if (price >= 1_000) {
		return price.toLocaleString("pt-BR");
	}

	return price.toString();
}

function getQualityVisualStyle(quality: ShopItemQuality) {
	return {
		comum: styles.commonVisual,
		incomum: styles.uncommonVisual,
		raro: styles.rareVisual,
		epico: styles.epicVisual,
		lendario: styles.legendaryVisual,
		mitico: styles.mythicVisual,
	}[quality];
}

function getQualityChipStyle(quality: ShopItemQuality) {
	return {
		comum: styles.commonChip,
		incomum: styles.uncommonChip,
		raro: styles.rareChip,
		epico: styles.epicChip,
		lendario: styles.legendaryChip,
		mitico: styles.mythicChip,
	}[quality];
}

const styles = StyleSheet.create((theme) => ({
	wrapper: {
		flex: 1,
		padding: theme.gap(0.625),
	},
	card: {
		flex: 1,
		minHeight: theme.gap(34),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-0"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 4 },
		shadowOpacity: 0.08,
		shadowRadius: 10,
		elevation: 3,
	},
	legendaryCard: {
		borderWidth: 2,
		borderColor: theme.colors["amber-400"],
		backgroundColor: theme.colors["amber-50"],
		shadowColor: theme.colors["amber-500"],
		shadowOpacity: 0.22,
	},
	lockedCard: {
		borderColor: theme.colors["neutral-200"],
	},
	cardTopRow: {
		flexDirection: "row",
		alignItems: "flex-start",
		justifyContent: "space-between",
		gap: theme.gap(0.75),
	},
	visual: {
		position: "relative",
		width: theme.gap(7),
		height: theme.gap(7),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.75),
	},
	commonVisual: {
		backgroundColor: theme.colors["green-50"],
	},
	uncommonVisual: {
		backgroundColor: theme.colors["blue-50"],
	},
	rareVisual: {
		backgroundColor: theme.colors["blue-100"],
	},
	epicVisual: {
		backgroundColor: theme.colors["red-50"],
	},
	legendaryVisual: {
		backgroundColor: theme.colors["amber-100"],
	},
	mythicVisual: {
		backgroundColor: theme.colors["violet-100"],
	},
	itemIcon: {
		width: 76,
		height: 76,
	},
	lockBadge: {
		position: "absolute",
		right: -theme.gap(0.25),
		bottom: -theme.gap(0.25),
		width: theme.gap(2.5),
		height: theme.gap(2.5),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 1,
		borderColor: theme.colors["neutral-0"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-700"],
	},
	lockIcon: {
		width: 18,
		height: 18,
	},
	priceIcon: {
		width: 17,
		height: 17,
	},
	qualityColumn: {
		flex: 1,
		alignItems: "flex-end",
		gap: theme.gap(0.5),
	},
	qualityChip: {
		maxWidth: "100%",
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.375),
		borderRadius: theme.gap(1.5),
	},
	commonChip: {
		backgroundColor: theme.colors["green-500"],
	},
	uncommonChip: {
		backgroundColor: theme.colors["blue-400"],
	},
	rareChip: {
		backgroundColor: theme.colors["blue-500"],
	},
	epicChip: {
		backgroundColor: theme.colors["amber-500"],
	},
	legendaryChip: {
		backgroundColor: theme.colors["amber-600"],
	},
	mythicChip: {
		backgroundColor: theme.colors["violet-600"],
	},
	qualityText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
	},
	stars: {
		color: theme.colors["amber-400"],
		fontSize: 11,
		letterSpacing: -1,
	},
	name: {
		minHeight: theme.gap(4.5),
		marginTop: theme.gap(1.25),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
		lineHeight: theme.gap(2.25),
	},
	priceBlock: {
		marginTop: theme.gap(0.5),
	},
	levelText: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	priceText: {
		marginTop: 2,
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	diamondPriceText: {
		color: theme.colors["violet-600"],
	},
	description: {
		minHeight: theme.gap(5),
		marginTop: theme.gap(0.75),
		color: theme.colors["neutral-700"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	spacer: {
		flex: 1,
	},
	amountBadge: {
		alignSelf: "flex-start",
		marginBottom: theme.gap(0.75),
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.375),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["violet-50"],
	},
	amountText: {
		color: theme.colors["violet-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 9,
		fontWeight: "700",
	},
}));
