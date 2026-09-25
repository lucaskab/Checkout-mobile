import { SymbolView } from "expo-symbols";
import { useState } from "react";
import { Pressable, View } from "react-native";
import { StyleSheet, useUnistyles } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { itemCatalog } from "@/data/market-products";
import { formatSupplierDeliveryTime } from "@/services/logistics";
import {
	getMaxShelfOrderQuantity,
	getShelfOrderQuote,
} from "@/services/shelf-order-quote";
import { useGameStore } from "@/stores/game-store";

type SupplierOrderSheetProps = {
	onBack?: () => void;
	onClose?: () => void;
	productId: number;
	onOrdered?: (message: string) => void;
};

export function SupplierOrderSheet({
	onBack,
	onClose,
	productId,
	onOrdered,
}: SupplierOrderSheetProps) {
	const { closeBottomSheet } = useBottomSheet();
	const { theme } = useUnistyles();
	const state = useGameStore();
	const product = itemCatalog.find((item) => item.id === productId);
	const [quantity, setQuantity] = useState(1);
	const [feedback, setFeedback] = useState("");
	const productName = product?.name ?? "produto";
	const quote = getShelfOrderQuote(state, productId, quantity);
	const unitQuote = getShelfOrderQuote(state, productId, 1);
	const maxQuantity = getMaxShelfOrderQuantity(state, productId);

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

	function close() {
		if (onClose) {
			onClose();
			return;
		}

		closeBottomSheet();
	}

	return (
		<View style={styles.content}>
			<View style={styles.header}>
				{onBack ? (
					<Pressable
						accessibilityRole="button"
						accessibilityLabel="Voltar ao depósito"
						onPress={onBack}
						style={styles.backButton}
					>
						<SymbolView
							name={{
								ios: "chevron.left",
								android: "chevron_left",
								web: "chevron_left",
							}}
							size={18}
							tintColor={theme.colors["neutral-700"]}
						/>
					</Pressable>
				) : (
					<View style={styles.productVisual}>
						<ProductImage productId={product.id} style={styles.productImage} />
					</View>
				)}
				<View style={styles.productCopy}>
					<Text style={styles.eyebrow}>FORNECEDORES</Text>
					<Text style={styles.title}>Pedir {product.name}</Text>
					<Text style={styles.subtitle}>
						Entrega no depósito em cerca de{" "}
						{formatSupplierDeliveryTime(quote.duration)}.
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
						disabled={quantity <= 0 || Boolean(feedback)}
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
				<View style={styles.quantityShortcuts}>
					<GameButton
						accessibilityLabel="Definir quantidade como zero"
						disabled={quantity === 0 || Boolean(feedback)}
						label="0"
						onPress={() => setQuantity(0)}
						size="small"
						style={styles.quantityShortcut}
						variant="secondary"
					/>
					<GameButton
						accessibilityLabel={`Definir quantidade máxima: ${maxQuantity}`}
						disabled={quantity === maxQuantity || Boolean(feedback)}
						label={`Máx · ${maxQuantity}`}
						onPress={() => setQuantity(maxQuantity)}
						size="small"
						style={styles.quantityShortcut}
						variant="secondary"
					/>
				</View>
			</View>

			<View style={styles.summaryCard}>
				<View style={styles.summaryRow}>
					<Text style={styles.summaryLabel}>Preço por unidade</Text>
					<Text style={styles.summaryValue}>
						{quantity > 0
							? Number((quote.total / quantity).toFixed(2))
							: (unitQuote?.total ?? 0)}{" "}
						moedas
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
						onPress={close}
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
	backButton: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 1,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
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
		justifyContent: "center",
		gap: theme.gap(2),
		marginTop: theme.gap(1),
	},
	quantityValue: {
		alignItems: "center",
		minWidth: theme.gap(8),
	},
	quantityShortcuts: {
		flexDirection: "row",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1),
	},
	quantityShortcut: {
		flex: 1,
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
