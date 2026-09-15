import { router, usePathname } from "expo-router";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";

export function GameModeToggle() {
	const simulator = usePathname() === "/simulator";

	return (
		<View style={styles.container}>
			<ModeOption
				active={!simulator}
				icon="computer"
				label="Sistema"
				onPress={() => router.replace("/")}
			/>
			<ModeOption
				active={simulator}
				icon="controller"
				label="Simulador"
				onPress={() => router.push("/simulator")}
			/>
		</View>
	);
}

function ModeOption({
	active = false,
	disabled = false,
	icon,
	label,
	onPress,
}: {
	active?: boolean;
	disabled?: boolean;
	icon: "computer" | "controller";
	label: string;
	onPress: () => void;
}) {
	return (
		<Pressable
			onPress={onPress}
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
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	container: {
		flexDirection: "row",
		padding: 2,
		borderWidth: 1,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-50"],
	},
	option: {
		width: theme.gap(3.5),
		height: theme.gap(3.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1),
	},
	activeOption: {
		backgroundColor: theme.colors["blue-500"],
	},
	disabledOption: {
		opacity: 0.45,
	},
	pressedOption: {
		backgroundColor: theme.colors["neutral-200"],
		transform: [{ scale: 0.94 }],
	},
	icon: {
		width: theme.gap(2),
		height: theme.gap(2),
	},
}));
