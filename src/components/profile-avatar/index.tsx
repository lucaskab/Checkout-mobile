import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProfileSheet } from "@/components/profile-sheet";
import { useGameStore } from "@/stores/game-store";

export function ProfileAvatar() {
	const { openBottomSheet } = useBottomSheet();
	const level = useGameStore((state) => state.market.level);

	return (
		<Pressable
			onPress={() => openBottomSheet(<ProfileSheet />)}
			style={({ pressed }) => [styles.avatar, pressed && styles.pressedAvatar]}
		>
			<GameIcon icon="manager" style={styles.icon} />
			<View style={styles.levelBadge}>
				<Text style={styles.levelText}>{level}</Text>
			</View>
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	avatar: {
		width: theme.gap(5.25),
		height: theme.gap(5.25),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 2,
		borderColor: theme.colors["blue-400"],
		borderBottomWidth: 5,
		borderBottomColor: theme.colors["blue-600"],
		borderRadius: theme.gap(3),
		backgroundColor: theme.colors["blue-50"],
	},
	pressedAvatar: {
		borderBottomWidth: 2,
		transform: [{ translateY: 3 }],
	},
	icon: {
		width: 34,
		height: 34,
	},
	levelBadge: {
		position: "absolute",
		right: -theme.gap(0.5),
		bottom: -theme.gap(0.5),
		minWidth: theme.gap(2.25),
		height: theme.gap(2.25),
		alignItems: "center",
		justifyContent: "center",
		paddingHorizontal: 2,
		borderWidth: 1.5,
		borderColor: theme.colors["neutral-0"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-600"],
	},
	levelText: {
		color: theme.colors["neutral-0"],
		fontSize: 9,
		fontWeight: "700",
	},
}));
