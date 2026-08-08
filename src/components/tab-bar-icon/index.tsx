import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";
import type { GameIconId } from "@/data/game-icon-assets";

type TabBarIconProps = {
	icon: GameIconId;
	focused: boolean;
};

export function TabBarIcon({ focused, icon }: TabBarIconProps) {
	return (
		<View style={[styles.container, focused && styles.focusedContainer]}>
			<GameIcon icon={icon} style={styles.icon} />
			{focused && <View style={styles.activeDot} />}
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	container: {
		position: "relative",
		width: theme.gap(4.5),
		height: theme.gap(3.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
	},
	focusedContainer: {
		backgroundColor: theme.colors["blue-100"],
	},
	icon: {
		width: 24,
		height: 24,
	},
	activeDot: {
		position: "absolute",
		bottom: 2,
		width: theme.gap(0.5),
		height: theme.gap(0.5),
		borderRadius: theme.gap(0.5),
		backgroundColor: theme.colors["red-500"],
	},
}));
