import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import type { EvolutionAreaId } from "./market-evolution-scene";

type MarketEvolutionCanvasProps = {
	activeArea: EvolutionAreaId;
	rotation: number;
	zoom: number;
	unlockedAreaIds: EvolutionAreaId[];
};

export function MarketEvolutionCanvas({
	activeArea,
	rotation,
	zoom,
	unlockedAreaIds,
}: MarketEvolutionCanvasProps) {
	return (
		<View style={styles.frame}>
			<View style={styles.webPreview}>
				<GameIcon icon="market" style={styles.icon} />
				<Text style={styles.title}>Cidade do mercado</Text>
				<Text style={styles.description}>
					A visualização 3D está disponível no app mobile.
				</Text>
				<Text style={styles.status}>
					{unlockedAreaIds.length}/5 áreas conquistadas · área selecionada:{" "}
					{activeArea}
				</Text>
				<Text style={styles.rotation}>
					Rotação {Math.round(rotation * 100)}°
				</Text>
				<Text style={styles.rotation}>Zoom {Math.round(zoom)}x</Text>
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	frame: {
		height: 350,
		overflow: "hidden",
		borderWidth: 2,
		borderColor: theme.colors["green-100"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["green-50"],
	},
	webPreview: {
		flex: 1,
		alignItems: "center",
		justifyContent: "center",
		padding: theme.gap(2),
		backgroundColor: theme.colors["green-100"],
	},
	icon: { width: theme.gap(7), height: theme.gap(7) },
	title: {
		marginTop: theme.gap(1),
		color: theme.colors["blue-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 22,
	},
	description: {
		marginTop: theme.gap(0.5),
		color: theme.colors["blue-700"],
		fontSize: 12,
		textAlign: "center",
	},
	status: {
		marginTop: theme.gap(1),
		color: theme.colors["green-600"],
		fontFamily: theme.fonts.family.number,
		fontSize: 10,
		textAlign: "center",
	},
	rotation: {
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-600"],
		fontSize: 10,
	},
}));
