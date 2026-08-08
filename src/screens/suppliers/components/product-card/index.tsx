import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { SupplierProduct } from "@/@types/supplier";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";

type ProductCardProps = {
	isBuying: boolean;
	canAfford: boolean;
	onBuy: (product: SupplierProduct) => void;
	product: SupplierProduct;
};

export function ProductCard({
	isBuying,
	canAfford,
	onBuy,
	product,
}: ProductCardProps) {
	return (
		<View style={styles.wrapper}>
			<View style={styles.card}>
				{product.owned > 0 && (
					<View style={styles.ownedBadge}>
						<Text style={styles.ownedBadgeText}>
							{product.owned}/{product.capacity}
						</Text>
					</View>
				)}
				<View style={styles.productVisual}>
					<ProductImage productId={product.id} style={styles.productImage} />
				</View>
				<Text numberOfLines={1} style={styles.productName}>
					{product.name}
				</Text>
				{product.productionSavingsPercent !== undefined && (
					<View style={styles.productionBadge}>
						<View style={styles.inlineRow}>
							<GameIcon icon="warehouse" style={styles.inlineIcon} />
							<Text style={styles.productionBadgeText}>
								Fabricar economiza {product.productionSavingsPercent}%
							</Text>
						</View>
					</View>
				)}
				<View style={styles.productDetails}>
					<View style={styles.detailChip}>
						<View style={styles.inlineRow}>
							<GameIcon icon="package" style={styles.inlineIcon} />
							<Text style={styles.detailText}>{product.quantity} unid.</Text>
						</View>
					</View>
					<View style={styles.detailChip}>
						<View style={styles.inlineRow}>
							<GameIcon icon="deliveryTruck" style={styles.inlineIcon} />
							<Text style={styles.detailText}>{product.shelfTime}</Text>
						</View>
					</View>
				</View>
				<Text style={styles.deliveryEstimate}>
					Entrega estimada: {product.shelfTime}
				</Text>
				<View style={styles.sellValue}>
					<Text style={styles.sellValueLabel}>Vende por</Text>
					<View style={styles.inlineRow}>
						<GameIcon icon="coin" style={styles.inlineIcon} />
						<Text style={styles.sellValueText}>{product.sellPrice}/un</Text>
					</View>
				</View>
				<GameButton
					disabled={!canAfford || isBuying}
					fullWidth
					icon={isBuying ? undefined : "coin"}
					label={isBuying ? "Criando pedido..." : `Pedir · ${product.price}`}
					onPress={() => onBuy(product)}
					style={styles.buyButton}
					variant="primary"
				/>
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	wrapper: {
		padding: theme.gap(0.75),
	},
	card: {
		alignItems: "center",
		padding: theme.gap(1.5),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-0"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 3 },
		shadowOpacity: 0.08,
		shadowRadius: 8,
		elevation: 2,
	},
	inlineRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	inlineIcon: {
		width: 18,
		height: 18,
	},
	ownedBadge: {
		position: "absolute",
		top: theme.gap(1),
		right: theme.gap(1),
		zIndex: 1,
		minWidth: theme.gap(2.75),
		height: theme.gap(2.75),
		alignItems: "center",
		justifyContent: "center",
		paddingHorizontal: theme.gap(0.5),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-500"],
	},
	ownedBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["neutral-0"],
		fontSize: 11,
		fontWeight: "700",
	},
	productVisual: {
		width: theme.gap(8),
		height: theme.gap(8),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 1,
		borderColor: theme.colors["blue-100"],
		borderRadius: theme.gap(2.25),
		backgroundColor: theme.colors["blue-50"],
	},
	productImage: {
		width: theme.gap(7),
		height: theme.gap(7),
	},
	productName: {
		width: "100%",
		marginTop: theme.gap(1.25),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
		textAlign: "center",
	},
	productionBadge: {
		marginTop: theme.gap(0.75),
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderWidth: 1,
		borderColor: theme.colors["violet-100"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["violet-50"],
	},
	productionBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["violet-600"],
		fontSize: 9,
		fontWeight: "700",
	},
	productDetails: {
		flexDirection: "row",
		justifyContent: "center",
		gap: theme.gap(0.5),
		width: "100%",
		marginTop: theme.gap(1),
	},
	detailChip: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.4),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	detailText: {
		color: theme.colors["neutral-600"],
		fontSize: 10,
		fontWeight: "600",
	},
	deliveryEstimate: {
		marginTop: theme.gap(0.75),
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "600",
	},
	sellValue: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		marginVertical: theme.gap(1.25),
	},
	sellValueLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 11,
	},
	sellValueText: {
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
		fontWeight: "700",
	},
	buyButton: {
		marginTop: "auto",
	},
}));
