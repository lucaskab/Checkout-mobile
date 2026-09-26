import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getRemainingUnits } from "@/services/receiving";
import { useGameStore } from "@/stores/game-store";

// System mode: a supplier truck is parked at the dock. One tap unloads everything that fits into
// the stockroom. (The simulator unloads it box by box in Unity.)
export function DeliveryAlert() {
	const dock = useGameStore((state) => state.receiving.dock);
	const unloadAll = useGameStore((state) => state.unloadAllDeliveries);
	const delivery = dock[0];
	if (!delivery) return null;
	const units = dock.reduce((total, item) => total + getRemainingUnits(item), 0);

	return (
		<View style={styles.alert}>
			<GameIcon icon="deliveryTruck" style={styles.icon} />
			<View style={styles.copy}>
				<Text numberOfLines={1} style={styles.title}>
					Caminhão no pátio · {getRemainingUnits(delivery)}x {delivery.productName}
					{dock.length > 1 ? ` (+${dock.length - 1})` : ""}
				</Text>
				<Text numberOfLines={1} style={styles.detail}>
					{units} unidades esperando para entrar no depósito
				</Text>
			</View>
			<GameButton
				icon="package"
				label="Descarregar"
				onPress={unloadAll}
				size="small"
				variant="primary"
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
		borderColor: theme.colors["blue-400"],
		backgroundColor: theme.colors["blue-50"],
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
