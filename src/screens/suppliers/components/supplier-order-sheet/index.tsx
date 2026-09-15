import { useState } from "react";
import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { itemCatalog } from "@/data/market-products";
import { getShelfOrderQuote } from "@/services/shelf-order-quote";
import { useGameStore } from "@/stores/game-store";

type SupplierOrderSheetProps = {
	productId: number;
	onOrdered?: (message: string) => void;
};

export function SupplierOrderSheet({
	productId,
	onOrdered,
}: SupplierOrderSheetProps) {
	const { closeBottomSheet } = useBottomSheet();
	const state = useGameStore();
	const product = itemCatalog.find((item) => item.id === productId);
	const [quantity, setQuantity] = useState(1);
	const [feedback, setFeedback] = useState("");
	const productName = product?.name ?? "produto";
	const quote = getShelfOrderQuote(state, productId, quantity);

	if (!product || !quote) {
		return null;
	}

	function confirmOrder() {
		const current = useGameStore.getState();

		if (current.placeSupplierOrder({ productId, quantity })) {
			const message = `Pedido de ${quantity} ${productName} confirmado! Acompanhe em Entregas.`;

			if (onOrdered) {
				onOrdered(message);
				return;
			}

			setFeedback(message);
			return;
		}

		setFeedback(
			"As condições do pedido mudaram. Confira saldo, espaço e entregas disponíveis.",
		);
	}

	return (
		<View style={styles.content}>
			<View style={styles.header}>
				<View style={styles.productVisual}>
					<ProductImage productId={product.id} style={styles.productImage} />
				</View>
				<View style={styles.productCopy}>
					<Text style={styles.eyebrow}>FORNECEDORES</Text>
					<Text style={styles.title}>Pedir {product.name}</Text>
					<Text style={styles.subtitle}>
						Entrega no depósito em cerca de {Math.ceil(quote.duration / 60_000)}{" "}
						min.
					</Text>
				</View>
			</View>

			<View style={styles.stockCard}>
				<View>
					<Text style={styles.stockLabel}>Espaço no depósito</Text>
					<Text style={styles.stockValue}>
						{state.inventory[productId] ?? 0}/{quote.capacity} unid.
					</Text>
				</View>
				<Text style={styles.availableSpace}>
					{quote.availableSpace} livre{quote.availableSpace === 1 ? "" : "s"}
				</Text>
			</View>

			<View style={styles.quantitySection}>
				<Text style={styles.sectionTitle}>Quantidade exata</Text>
				<View style={styles.quantityControl}>
					<GameButton
						accessibilityLabel="Diminuir quantidade"
						disabled={quantity <= 1 || Boolean(feedback)}
						label="−"
						onPress={() => setQuantity(quantity - 1)}
						size="small"
						variant="secondary"
					/>
					<View style={styles.quantityValue}>
						<Text style={styles.quantityNumber}>{quantity}</Text>
						<Text style={styles.quantityLabel}>unidades</Text>
					</View>
					<GameButton
						accessibilityLabel="Aumentar quantidade"
						disabled={quantity >= quote.availableSpace || Boolean(feedback)}
						label="+"
						onPress={() => setQuantity(quantity + 1)}
						size="small"
						variant="secondary"
					/>
				</View>
			</View>

			<View style={styles.summaryCard}>
				<View style={styles.summaryRow}>
					<Text style={styles.summaryLabel}>Preço por unidade</Text>
					<Text style={styles.summaryValue}>
						{Number((quote.total / quantity).toFixed(2))} moedas
					</Text>
				</View>
				<View style={styles.summaryRow}>
					<Text style={styles.summaryLabel}>Total do pedido</Text>
					<View style={styles.totalRow}>
						<GameIcon icon="coin" style={styles.coinIcon} />
						<Text style={styles.totalValue}>{quote.total}</Text>
					</View>
				</View>
				<Text style={styles.balanceText}>Seu saldo: {state.coins} moedas</Text>
			</View>

			{feedback ? (
				<>
					<Text accessibilityLiveRegion="polite" style={styles.feedback}>
						{feedback}
					</Text>
					<GameButton
						fullWidth
						label="Concluir"
						onPress={closeBottomSheet}
						variant="secondary"
					/>
				</>
			) : (
				<>
					{quote.reason && (
						<Text accessibilityLiveRegion="polite" style={styles.notice}>
							{quote.reason}
						</Text>
					)}
					<GameButton
						disabled={Boolean(quote.reason)}
						fullWidth
						icon="deliveryTruck"
						label={`Confirmar pedido · ${quote.total}`}
						onPress={confirmOrder}
						variant="coin"
					/>
				</>
			)}
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		paddingHorizontal: theme.gap(2.75),
		gap: theme.gap(1.25),
	},
	header: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
	},
	productVisual: {
		width: theme.gap(6.5),
		height: theme.gap(6.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-50"],
	},
	productImage: {
		width: theme.gap(5.5),
		height: theme.gap(5.5),
	},
	productCopy: {
		flex: 1,
	},
	eyebrow: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "800",
		letterSpacing: 0.8,
	},
	title: {
		marginTop: 2,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.large + 1,
		fontWeight: "700",
	},
	subtitle: {
		marginTop: 2,
		color: theme.colors["neutral-600"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	stockCard: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	stockLabel: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	stockValue: {
		marginTop: 2,
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	availableSpace: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-0"],
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
	},
	quantitySection: {
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.5),
	},
	sectionTitle: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	quantityControl: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		marginTop: theme.gap(1),
	},
	quantityValue: {
		alignItems: "center",
	},
	quantityNumber: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.large + 2,
		fontWeight: "700",
	},
	quantityLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "600",
	},
	summaryCard: {
		padding: theme.gap(1.25),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	summaryRow: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	summaryLabel: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	summaryValue: {
		color: theme.colors["neutral-700"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
		fontWeight: "700",
	},
	totalRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
		marginTop: theme.gap(0.75),
	},
	coinIcon: {
		width: 18,
		height: 18,
	},
	totalValue: {
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	balanceText: {
		marginTop: theme.gap(0.75),
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "600",
		textAlign: "right",
	},
	notice: {
		color: theme.colors["red-500"],
		fontSize: 11,
		fontWeight: "700",
		textAlign: "center",
	},
	feedback: {
		color: theme.colors["green-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
		lineHeight: theme.gap(2),
		textAlign: "center",
	},
}));
