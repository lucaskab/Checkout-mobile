import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import {
	type EvolutionAreaId,
	MarketEvolutionScene,
} from "./market-evolution-scene";
import { Canvas } from "./three-runtime";

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
			<Canvas
				camera={{ position: [8.5, 9.5, 10.5], zoom }}
				dpr={[1, 1.5]}
				orthographic
				style={styles.canvas}
			>
				<MarketEvolutionScene
					activeArea={activeArea}
					rotation={rotation}
					zoom={zoom}
					unlockedAreaIds={unlockedAreaIds}
				/>
			</Canvas>
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
	canvas: { flex: 1 },
}));
