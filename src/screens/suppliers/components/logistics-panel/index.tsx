import { Pressable, Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { useIap } from "@/components/iap-provider";
import { logisticsIapProducts } from "@/data/iap-products";
import { useGameStore } from "@/stores/game-store";

export function LogisticsPanel() {
	const { openBottomSheet } = useBottomSheet();
	const logistics = useGameStore((state) => state.logistics);

	return (
		<Pressable
			onPress={() => openBottomSheet(<LogisticsSheet />)}
			style={styles.trigger}
		>
			<View style={styles.triggerIcon}>
				<Text style={styles.triggerEmoji}>🚚</Text>
			</View>
			<View style={styles.triggerCopy}>
				<Text style={styles.triggerTitle}>Central logística</Text>
				<Text style={styles.triggerSubtitle}>
					{
						logistics.orders.filter((order) => order.status !== "entregue")
							.length
					}{" "}
					pedido(s) em andamento
				</Text>
			</View>
			<Text style={styles.triggerValue}>💎 {logistics.premiumCurrency}</Text>
		</Pressable>
	);
}

function LogisticsSheet() {
	const { connected, purchaseLogisticsProduct } = useIap();
	const activateLogisticsBoost = useGameStore(
		(state) => state.activateLogisticsBoost,
	);
	const logistics = useGameStore((state) => state.logistics);

	function activateBoost() {
		activateLogisticsBoost();
	}

	function purchase(productId: string) {
		purchaseLogisticsProduct(productId).catch(() => undefined);
	}

	return (
		<View style={styles.sheet}>
			<Text style={styles.sheetTitle}>Logística premium</Text>
			<Text style={styles.sheetSubtitle}>
				Acelere entregas sem remover a importância do planejamento.
			</Text>
			<View style={styles.balanceRow}>
				<Text style={styles.balanceText}>💎 {logistics.premiumCurrency}</Text>
				<Text style={styles.balanceText}>🎫 {logistics.emergencyTokens}</Text>
				<Text style={styles.connectionText}>
					{connected ? "Loja conectada" : "Conectando à loja"}
				</Text>
			</View>
			<PremiumOption
				description="Pedidos novos chegam 30% mais rápido por 15 minutos."
				onPress={activateBoost}
				title="Turbo logística · 3 💎"
			/>
			<PremiumOption
				description="Receba 50 diamantes para entregas instantâneas e atalhos."
				onPress={() => purchase(logisticsIapProducts.gemsSmall)}
				title="Pacote de diamantes"
			/>
			<PremiumOption
				description="Ganha 3 fichas para resolver faltas críticas imediatamente."
				onPress={() => purchase(logisticsIapProducts.emergencyPack)}
				title="Kit de emergência"
			/>
			<PremiumOption
				description="Um caminhão extra por 30 minutos para pedidos simultâneos."
				onPress={() => purchase(logisticsIapProducts.extraTruck)}
				title="Caminhão adicional"
			/>
			<PremiumOption
				description="10% menos tempo em entregas e relatórios detalhados."
				onPress={() => purchase(logisticsIapProducts.vipMonthly)}
				title="VIP mensal"
			/>
		</View>
	);
}

type PremiumOptionProps = {
	description: string;
	onPress: () => void;
	title: string;
};

function PremiumOption({ description, onPress, title }: PremiumOptionProps) {
	return (
		<Pressable onPress={onPress} style={styles.option}>
			<View style={styles.optionCopy}>
				<Text style={styles.optionTitle}>{title}</Text>
				<Text style={styles.optionDescription}>{description}</Text>
			</View>
			<Text style={styles.optionArrow}>›</Text>
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	trigger: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginTop: theme.gap(1.25),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-50"],
	},
	triggerIcon: {
		width: theme.gap(4.5),
		height: theme.gap(4.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	triggerEmoji: {
		fontSize: 20,
	},
	triggerCopy: {
		flex: 1,
	},
	triggerTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	triggerSubtitle: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	triggerValue: {
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	sheet: {
		gap: theme.gap(1),
		paddingHorizontal: theme.gap(2),
		paddingBottom: theme.gap(3),
	},
	sheetTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	sheetSubtitle: {
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		lineHeight: theme.gap(2),
	},
	balanceRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginBottom: theme.gap(0.5),
	},
	balanceText: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	connectionText: {
		marginLeft: "auto",
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	option: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	optionCopy: {
		flex: 1,
	},
	optionTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	optionDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	optionArrow: {
		color: theme.colors["blue-500"],
		fontSize: 26,
		fontWeight: "400",
	},
}));
