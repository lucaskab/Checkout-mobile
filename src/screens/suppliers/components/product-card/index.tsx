import { Pressable, Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { SupplierProduct } from "@/@types/supplier";

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
						<Text style={styles.ownedBadgeText}>{product.owned}</Text>
					</View>
				)}
				<View style={styles.productVisual}>
					<Text style={styles.productEmoji}>{product.emoji}</Text>
				</View>
				<Text numberOfLines={1} style={styles.productName}>
					{product.name}
				</Text>
				<View style={styles.productDetails}>
					<View style={styles.detailChip}>
						<Text style={styles.detailText}>📦 {product.quantity} unid.</Text>
					</View>
					<View style={styles.detailChip}>
						<Text style={styles.detailText}>🚚 {product.shelfTime}</Text>
					</View>
				</View>
				<Text style={styles.deliveryEstimate}>
					Entrega estimada: {product.shelfTime}
				</Text>
				<View style={styles.sellValue}>
					<Text style={styles.sellValueLabel}>Vende por</Text>
					<Text style={styles.sellValueText}>🪙 {product.sellPrice}/un</Text>
				</View>
				<Pressable
					disabled={!canAfford || isBuying}
					onPress={() => onBuy(product)}
					style={[
						styles.buyButton,
						!canAfford && styles.disabledBuyButton,
						isBuying && styles.buyingButton,
					]}
				>
					<Text
						style={[
							styles.buyButtonText,
							!canAfford && styles.disabledBuyButtonText,
						]}
					>
						{isBuying ? "Criando pedido..." : `Pedir · 🪙 ${product.price}`}
					</Text>
				</Pressable>
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
	productEmoji: {
		fontSize: 34,
	},
	productName: {
		width: "100%",
		marginTop: theme.gap(1.25),
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
		textAlign: "center",
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
		fontSize: 11,
		fontWeight: "700",
	},
	buyButton: {
		width: "100%",
		alignItems: "center",
		justifyContent: "center",
		minHeight: theme.gap(4.75),
		marginTop: "auto",
		borderRadius: theme.gap(3),
		backgroundColor: theme.colors["blue-500"],
	},
	disabledBuyButton: {
		backgroundColor: theme.colors["neutral-200"],
	},
	buyingButton: {
		backgroundColor: theme.colors["blue-300"],
	},
	buyButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	disabledBuyButtonText: {
		color: theme.colors["neutral-500"],
	},
}));
