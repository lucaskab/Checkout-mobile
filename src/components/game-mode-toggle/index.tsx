import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";

export function GameModeToggle() {
	return (
		<View style={styles.container}>
			<ModeOption active icon="computer" label="Sistema" />
			<ModeOption disabled icon="controller" label="Simulador" />
		</View>
	);
}

function ModeOption({
	active = false,
	disabled = false,
	icon,
	label,
}: {
	active?: boolean;
	disabled?: boolean;
	icon: "computer" | "controller";
	label: string;
}) {
	return (
		<Pressable
			accessibilityLabel={`Ativar modo ${label.toLowerCase()}`}
			accessibilityRole="tab"
			accessibilityState={{ disabled, selected: active }}
			disabled={disabled || active}
			style={({ pressed }) => [
				styles.option,
				active && styles.activeOption,
				disabled && styles.disabledOption,
				pressed && !active && !disabled && styles.pressedOption,
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
	disabledOption: {
		opacity: 0.45,
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
