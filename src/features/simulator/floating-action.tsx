import { Pressable, StyleSheet, Text, View } from "react-native";

type Props = {
	label: string;
	icon: string;
	color: string;
	onPress: () => void;
};

export function FloatingAction({ color, icon, label, onPress }: Props) {
	return (
		<Pressable
			accessibilityLabel={label}
			accessibilityRole="button"
			onPress={onPress}
			style={({ pressed }) => [
				styles.button,
				{ backgroundColor: color },
				pressed && styles.pressed,
			]}
		>
			<View style={styles.iconBubble}>
				<Text style={styles.icon}>{icon}</Text>
			</View>
			<Text numberOfLines={1} style={styles.label}>
				{label}
			</Text>
		</Pressable>
	);
}

const styles = StyleSheet.create({
	button: {
		minWidth: 112,
		height: 48,
		flexDirection: "row",
		alignItems: "center",
		gap: 8,
		paddingHorizontal: 9,
		borderRadius: 18,
		elevation: 8,
		shadowColor: "#1f392d",
		shadowOffset: { width: 0, height: 7 },
		shadowOpacity: 0.24,
		shadowRadius: 10,
	},
	pressed: { opacity: 0.9, transform: [{ translateY: 2 }] },
	iconBubble: {
		width: 32,
		height: 32,
		alignItems: "center",
		justifyContent: "center",
		borderRadius: 12,
		backgroundColor: "rgba(255,255,255,0.2)",
	},
	icon: { color: "#fffdf7", fontSize: 16, fontWeight: "900" },
	label: { color: "#fffdf7", fontSize: 11, fontWeight: "800" },
});
