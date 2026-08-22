import { type Href, router } from "expo-router";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";

type GameMode = "system" | "simulator";

export function GameModeToggle({ activeMode = "system" }: { activeMode?: GameMode }) {
	function selectMode(mode: GameMode) {
		if (mode === activeMode) {
			return;
		}

		if (mode === "simulator") {
			router.push("/simulator" as Href);
			return;
		}

		router.replace("/" as Href);
	}

	return (
		<View style={styles.container}>
			<ModeOption
				active={activeMode === "system"}
				icon="computer"
				label="Sistema"
				onPress={() => selectMode("system")}
			/>
			<ModeOption
				active={activeMode === "simulator"}
				icon="controller"
				label="Simulador"
				onPress={() => selectMode("simulator")}
			/>
		</View>
	);
}

function ModeOption({
	active = false,
	icon,
	label,
	onPress,
}: {
	active?: boolean;
	icon: "computer" | "controller";
	label: string;
	onPress: () => void;
}) {
	return (
		<Pressable
			accessibilityLabel={`Ativar modo ${label.toLowerCase()}`}
			accessibilityRole="tab"
			accessibilityState={{ selected: active }}
			disabled={active}
			onPress={onPress}
			style={({ pressed }) => [
				styles.option,
				active && styles.activeOption,
				pressed && !active && styles.pressedOption,
			]}
		>
			<GameIcon icon={icon} style={styles.icon} />
			<Text style={[styles.label, active && styles.activeLabel]}>{label}</Text>
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	container: {
		alignSelf: "center",
		flexDirection: "row",
		padding: theme.gap(0.375),
		borderWidth: 2,
		borderBottomWidth: 5,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["neutral-100"],
	},
	option: {
		minWidth: 106,
		minHeight: 38,
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.5),
		paddingHorizontal: theme.gap(1),
		borderRadius: theme.gap(1.25),
	},
	activeOption: {
		backgroundColor: theme.colors["blue-500"],
	},
	pressedOption: {
		backgroundColor: theme.colors["neutral-200"],
		transform: [{ translateY: 1 }],
	},
	icon: {
		width: 21,
		height: 21,
	},
	label: {
		color: theme.colors["neutral-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
	},
	activeLabel: {
		color: theme.colors["neutral-0"],
	},
}));
