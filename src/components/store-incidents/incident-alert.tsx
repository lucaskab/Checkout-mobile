import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreIncidentKind } from "@/@types/store-incident";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import type { GameIconId } from "@/data/game-icon-assets";
import { incidentLabels } from "@/services/store-incidents";
import { useGameStore } from "@/stores/game-store";

const icons: Record<StoreIncidentKind, GameIconId> = {
	derramado: "broom",
	sujeira: "broom",
	freezer_sorvete: "freezer",
	geladeira_bebidas: "refrigerator",
	etiqueta: "priceTag",
	lampada: "light",
};

const effects: Record<StoreIncidentKind, string> = {
	derramado: "Clientes reclamam e a reputação cai",
	sujeira: "Loja com cara de descuidada",
	freezer_sorvete: "Sorvetes derretendo e prateleira parada",
	geladeira_bebidas: "Bebidas esquentando e prateleira parada",
	etiqueta: "Vendendo pela metade do preço",
	lampada: "Loja escura, clientes menos satisfeitos",
};

// System mode: the oldest store mishap with a one-tap fix. (The simulator plays it in Unity.)
export function IncidentAlert() {
	const active = useGameStore((state) => state.incidents.active);
	const coins = useGameStore((state) => state.coins);
	const fix = useGameStore((state) => state.fixIncident);
	const incident = active[0];
	if (!incident) return null;
	const label = incidentLabels[incident.kind];
	const affordable = coins >= incident.fixCost;

	return (
		<View style={styles.alert}>
			<GameIcon icon={icons[incident.kind]} style={styles.icon} />
			<View style={styles.copy}>
				<Text numberOfLines={1} style={styles.title}>
					{label.title} · {incident.shelfName}
					{active.length > 1 ? ` (+${active.length - 1})` : ""}
				</Text>
				<Text numberOfLines={1} style={styles.detail}>
					{effects[incident.kind]}
				</Text>
			</View>
			<GameButton
				disabled={!affordable}
				icon={incident.fixCost > 0 ? "coin" : "toolbox"}
				label={
					incident.fixCost > 0
						? `${label.action} (${incident.fixCost})`
						: label.action
				}
				onPress={() => fix(incident.id)}
				size="small"
				variant="coin"
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
		borderColor: theme.colors["amber-400"],
		backgroundColor: theme.colors["amber-50"],
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
