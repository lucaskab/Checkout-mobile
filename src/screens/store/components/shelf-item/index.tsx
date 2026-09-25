import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreShelf } from "@/@types/store";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";

const STOCK_PIPS = ["pip-1", "pip-2", "pip-3", "pip-4"] as const;

export const ShelfItem = ({
	availableQuantity,
	capacity,
	onPress,
	price,
	shelf,
	shelfQuantity,
	size,
}: {
	availableQuantity: number;
	capacity: number;
	onPress: (shelf: StoreShelf) => void;
	price?: number;
	shelf: StoreShelf;
	shelfQuantity: number;
	size: number;
}) => {
	const hasProduct = Boolean(shelf.productId);
	const isEmpty = !shelf.locked && hasProduct && shelfQuantity === 0;
	const fillRatio = capacity > 0 ? shelfQuantity / capacity : 0;

	return (
		<Pressable
			onPress={() => onPress(shelf)}
			style={({ pressed }) => [
				styles.slot,
				{ width: size, height: size + 34 },
				pressed && styles.pressedSlot,
			]}
		>
			<View
				style={[
					styles.crate,
					{ height: size - 10 },
					shelf.locked && styles.lockedCrate,
					isEmpty && styles.emptyCrate,
					!shelf.locked && !hasProduct && styles.availableCrate,
				]}
			>
				{!shelf.locked && hasProduct && (
					<View style={styles.priceTag}>
						<View style={styles.inlineRow}>
							<GameIcon icon="coin" style={styles.inlineIcon} />
							<Text style={styles.priceText}>{price ?? 0}</Text>
						</View>
					</View>
				)}
				{!shelf.locked && hasProduct && (
					<View style={[styles.stockBadge, isEmpty && styles.stockBadgeEmpty]}>
						<Text style={styles.stockBadgeText}>
							{shelfQuantity}/{capacity}
						</Text>
					</View>
				)}

				{shelf.locked ? (
					<GameIcon icon="lock" style={styles.product} />
				) : shelf.productId ? (
					<ProductImage
						productId={shelf.productId}
						style={styles.productImage}
					/>
				) : (
					<GameIcon
						accessibilityLabel="Slot livre para adicionar produto"
						icon="emptyShelfSlot"
						style={styles.product}
					/>
				)}

				{!shelf.locked && hasProduct && (
					<View style={styles.pips}>
						{STOCK_PIPS.map((pipKey, index) => (
							<View
								key={pipKey}
								style={[
									styles.pip,
									index < Math.ceil(fillRatio * 4) && styles.pipFilled,
									isEmpty && styles.pipEmpty,
								]}
							/>
						))}
					</View>
				)}
			</View>

			{/* wooden plank the crate rests on */}
			<View style={styles.plank}>
				<View style={styles.plankFace} />
				<View style={styles.plankEdge} />
			</View>

			<View style={styles.caption}>
				{shelf.locked && shelf.nextShelfUpgrade ? (
					<View style={styles.captionRow}>
						<Text numberOfLines={1} style={styles.captionMeta}>
							Nv.{shelf.nextShelfUpgrade.playerLevel} ·
						</Text>
						<GameIcon icon="coin" style={styles.captionIcon} />
						<Text numberOfLines={1} style={styles.captionMeta}>
							{shelf.nextShelfUpgrade.coinCost.toLocaleString("pt-BR")}
						</Text>
					</View>
				) : shelf.locked ? (
					<Text numberOfLines={1} style={styles.captionMeta}>
						Bloqueado
					</Text>
				) : !hasProduct ? (
					<Text numberOfLines={1} style={styles.captionMeta}>
						Escolher
					</Text>
				) : availableQuantity > 0 ? (
					<View style={styles.captionRow}>
						<GameIcon icon="package" style={styles.captionIcon} />
						<Text numberOfLines={1} style={styles.captionMeta}>
							{availableQuantity}
						</Text>
					</View>
				) : (
					<Text numberOfLines={1} style={styles.captionMeta}>
						Sem estoque
					</Text>
				)}
			</View>
		</Pressable>
	);
};

const styles = StyleSheet.create((theme) => ({
	slot: {
		alignItems: "center",
		justifyContent: "flex-end",
	},
	pressedSlot: {
		transform: [{ scale: 0.96 }],
	},
	crate: {
		width: "100%",
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 2,
		borderColor: theme.colors.gameShelfBorder,
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors.gameShelf,
	},
	lockedCrate: {
		borderStyle: "dashed",
		borderColor: theme.colors["neutral-300"],
		backgroundColor: theme.colors.gameLockedShelf,
	},
	emptyCrate: {
		borderColor: theme.colors["red-400"],
		backgroundColor: theme.colors["red-50"],
	},
	availableCrate: {
		borderStyle: "dashed",
		borderColor: theme.colors["green-500"],
		backgroundColor: theme.colors["green-50"],
	},
	priceTag: {
		position: "absolute",
		top: -theme.gap(0.75),
		left: -theme.gap(0.5),
		paddingHorizontal: theme.gap(0.625),
		paddingVertical: 2,
		borderWidth: 1.5,
		borderColor: theme.colors["amber-600"],
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["amber-100"],
		transform: [{ rotate: "-8deg" }],
	},
	priceText: {
		color: theme.colors["amber-600"],
		fontSize: 9,
		fontWeight: "800",
	},
	inlineRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.15),
	},
	inlineIcon: {
		width: 15,
		height: 15,
	},
	stockBadge: {
		position: "absolute",
		top: theme.gap(0.5),
		right: theme.gap(0.5),
		paddingHorizontal: theme.gap(0.5),
		paddingVertical: 1,
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-700"],
	},
	stockBadgeEmpty: {
		backgroundColor: theme.colors["red-500"],
	},
	stockBadgeText: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-0"],
		fontSize: 9,
		fontWeight: "800",
	},
	product: {
		width: 38,
		height: 38,
	},
	productImage: {
		width: theme.gap(6),
		height: theme.gap(6),
	},
	pips: {
		flexDirection: "row",
		gap: 2,
		position: "absolute",
		bottom: theme.gap(0.5),
	},
	pip: {
		width: theme.gap(0.875),
		height: theme.gap(0.5),
		borderRadius: 2,
		backgroundColor: theme.colors["neutral-200"],
	},
	pipFilled: {
		backgroundColor: theme.colors["green-500"],
	},
	pipEmpty: {
		backgroundColor: theme.colors["red-200"],
	},
	plank: {
		width: "108%",
	},
	plankFace: {
		height: theme.gap(0.75),
		borderTopLeftRadius: theme.gap(0.5),
		borderTopRightRadius: theme.gap(0.5),
		backgroundColor: theme.colors["neutral-300"],
	},
	plankEdge: {
		height: theme.gap(0.5),
		borderBottomLeftRadius: theme.gap(0.75),
		borderBottomRightRadius: theme.gap(0.75),
		backgroundColor: theme.colors["neutral-400"],
	},
	caption: {
		alignItems: "center",
		height: theme.gap(3.5),
		justifyContent: "flex-start",
		marginTop: theme.gap(0.375),
	},
	captionTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-700"],
		fontSize: 9,
		fontWeight: "800",
	},
	captionMeta: {
		color: theme.colors["neutral-600"],
		fontSize: 9,
		fontWeight: "700",
	},
	captionRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.15),
	},
	captionIcon: {
		width: 14,
		height: 14,
	},
}));
