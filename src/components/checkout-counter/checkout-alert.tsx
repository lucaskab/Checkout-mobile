import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { formatClock, useNow } from "@/components/market-day/use-now";
import { getReadyCheckouts } from "@/services/checkout-counter";
import { useGameStore } from "@/stores/game-store";

// System mode: a customer waits at the register; one tap rings the purchase up.
// (The simulator plays the full register in Unity instead.)
export function CheckoutAlert() {
	const checkout = useGameStore((state) => state.checkout);
	const complete = useGameStore((state) => state.completeCheckout);
	const hasQueue = checkout.queue.length > 0;
	const now = useNow(hasQueue);
	const ready = getReadyCheckouts(checkout, now);
	const next = ready[0];
	if (!next) return null;
	const remaining = next.expiresAt - now;
	const urgent = remaining < 20_000;

	function serveAll() {
		for (const item of ready) complete(item.id, item.total);
	}

	return (
		<View style={[styles.alert, urgent && styles.urgent]}>
			<GameIcon icon="cart" style={styles.icon} />
			<View style={styles.copy}>
				<Text numberOfLines={1} style={styles.title}>
					{ready.length > 1
						? `${ready.length} clientes esperando no caixa`
						: `${next.customerName} está esperando no caixa`}
				</Text>
				<Text numberOfLines={1} style={styles.detail}>
					{next.units} ite{next.units > 1 ? "ns" : "m"} ·{" "}
					{next.total.toLocaleString("pt-BR")} moedas ·{" "}
					{next.method === "cartao" ? "cartão" : "dinheiro"} ·{" "}
					{formatClock(remaining)}
				</Text>
			</View>
			<GameButton
				icon="scanner"
				label={ready.length > 1 ? "Atender todos" : "Passar compras"}
				onPress={() => (ready.length > 1 ? serveAll() : complete(next.id, next.total))}
				size="small"
				variant="success"
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	alert: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginHorizontal: theme.gap(1),
		marginTop: theme.gap(0.75),
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.75),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderRadius: theme.gap(1.5),
		borderColor: theme.colors["green-500"],
		backgroundColor: theme.colors["green-50"],
	},
	urgent: {
		borderColor: theme.colors["red-400"],
		backgroundColor: theme.colors["red-50"],
	},
	icon: { width: theme.gap(3.5), height: theme.gap(3.5) },
	copy: { flex: 1 },
	title: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 13,
	},
	detail: { color: theme.colors["neutral-600"], fontSize: 11 },
}));
