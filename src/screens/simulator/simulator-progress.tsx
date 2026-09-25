import { Pressable, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { StyleSheet } from "react-native-unistyles";
import type { SimulatorPanel } from "@/@types/simulator";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { itemCatalog } from "@/data/market-products";
import {
	getUnlockedPhysicalShelfCount,
	resolveShelfSlotCounts,
} from "@/data/shelf-slots";
import { getClaimableMissionCount } from "@/services/missions";
import { getExperienceToNextLevel } from "@/services/progression";
import { getNextSimulatorUnlocks } from "@/services/simulator-progression";
import { useGameStore } from "@/stores/game-store";

type SimulatorProgressProps = {
	onOpenPanel: (panel: SimulatorPanel) => void;
};

export function SimulatorProgress({ onOpenPanel }: SimulatorProgressProps) {
	const game = useGameStore();
	const experienceGoal = getExperienceToNextLevel(game.market.level);
	const experienceProgress = Math.min(
		100,
		Math.round((game.market.experience / experienceGoal) * 100),
	);
	const nextUnlocks = getNextSimulatorUnlocks(
		game.market.level,
		getUnlockedPhysicalShelfCount(
			resolveShelfSlotCounts(game.shelfSlotCounts, game.unlockedShelfSlots),
		),
	);
	const nextUnlock = nextUnlocks[0];
	const claimableMissions = getClaimableMissionCount(game);
	const dailyProgress = Math.min(
		100,
		Math.round((game.daily.revenue / game.daily.goal) * 100),
	);
	const recentUnlocks = itemCatalog
		.filter((product) =>
			game.market.recentUnlockProductIds.includes(product.id),
		)
		.map((product) => product.name);
	const progressionLabel = recentUnlocks.length
		? `Novo: ${recentUnlocks.slice(0, 2).join(" e ")}`
		: nextUnlock
			? `Próximo: ${nextUnlock.label}${nextUnlocks.length > 1 ? ` +${nextUnlocks.length - 1}` : ""}`
			: "Catálogo completo";

	function handleDailyPress() {
		if (game.daily.goalReached && !game.daily.claimed) {
			game.claimDailyGoal();
			return;
		}

		onOpenPanel("store");
	}

	return (
		<Animated.View entering={FadeInDown.duration(280)} style={styles.container}>
			<Pressable
				accessibilityRole="button"
				accessibilityLabel={`Nível ${game.market.level}. ${game.market.experience} de ${experienceGoal} XP. ${progressionLabel}`}
				onPress={() => onOpenPanel(nextUnlock?.panel ?? "store")}
				style={({ pressed }) => [
					styles.progressCard,
					pressed && styles.pressed,
				]}
			>
				<View style={styles.progressHeading}>
					<View style={styles.levelBadge}>
						<GameIcon icon="crown" style={styles.levelIcon} />
						<Text style={styles.level}>NÍVEL {game.market.level}</Text>
					</View>
					<Text numberOfLines={1} style={styles.nextUnlock}>
						{progressionLabel}
					</Text>
					{nextUnlock && (
						<Text style={styles.unlockLevel}>
							NV. {nextUnlock.requiredLevel}
						</Text>
					)}
				</View>
				<View style={styles.experienceRow}>
					<View style={styles.experienceTrack}>
						<View
							style={[
								styles.experienceFill,
								{ width: `${experienceProgress}%` },
							]}
						/>
					</View>
					<Text style={styles.experienceValue}>
						{game.market.experience}/{experienceGoal} XP
					</Text>
				</View>
			</Pressable>

			<View style={styles.shortcuts}>
				<ProgressShortcut
					accessibilityLabel={`${claimableMissions} missões prontas para resgatar`}
					badge={claimableMissions}
					icon="trophy"
					onPress={() => onOpenPanel("missions")}
				/>
				<ProgressShortcut
					accessibilityLabel={`Meta diária em ${dailyProgress}%${game.daily.goalReached && !game.daily.claimed ? ". Prêmio pronto para resgatar" : ""}`}
					badge={game.daily.goalReached && !game.daily.claimed ? 1 : 0}
					icon="coin"
					onPress={handleDailyPress}
					progress={dailyProgress}
				/>
			</View>
		</Animated.View>
	);
}

function ProgressShortcut({
	accessibilityLabel,
	badge,
	icon,
	onPress,
	progress,
}: {
	accessibilityLabel: string;
	badge: number;
	icon: "coin" | "trophy";
	onPress: () => void;
	progress?: number;
}) {
	return (
		<Pressable
			accessibilityLabel={accessibilityLabel}
			accessibilityRole="button"
			onPress={onPress}
			style={({ pressed }) => [styles.shortcut, pressed && styles.pressed]}
		>
			<GameIcon icon={icon} style={styles.shortcutIcon} />
			{typeof progress === "number" && (
				<View style={styles.shortcutTrack}>
					<View style={[styles.shortcutFill, { width: `${progress}%` }]} />
				</View>
			)}
			{badge > 0 && (
				<View style={styles.badge}>
					<Text style={styles.badgeText}>{badge}</Text>
				</View>
			)}
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	container: {
		flexDirection: "row",
		alignItems: "stretch",
		gap: theme.gap(0.5),
	},
	progressCard: {
		flex: 1,
		minHeight: 54,
		justifyContent: "center",
		paddingHorizontal: theme.gap(0.875),
		paddingVertical: theme.gap(0.5),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	progressHeading: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
	},
	levelBadge: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	levelIcon: { width: 17, height: 17 },
	level: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 11,
		color: theme.colors["blue-700"],
	},
	nextUnlock: {
		flex: 1,
		fontFamily: theme.fonts.family.badge,
		fontSize: 11,
		color: theme.colors["neutral-700"],
	},
	unlockLevel: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 10,
		color: theme.colors["amber-600"],
	},
	experienceRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		marginTop: theme.gap(0.375),
	},
	experienceTrack: {
		flex: 1,
		height: 8,
		overflow: "hidden",
		borderRadius: theme.gap(0.5),
		backgroundColor: theme.colors["blue-100"],
	},
	experienceFill: {
		height: "100%",
		borderRadius: theme.gap(0.5),
		backgroundColor: theme.colors["blue-500"],
	},
	experienceValue: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 10,
		color: theme.colors["neutral-600"],
	},
	shortcuts: { flexDirection: "row", gap: theme.gap(0.375) },
	shortcut: {
		width: 48,
		minHeight: 54,
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 2,
		borderBottomWidth: 4,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	shortcutIcon: { width: 24, height: 24 },
	shortcutTrack: {
		position: "absolute",
		left: theme.gap(0.5),
		right: theme.gap(0.5),
		bottom: theme.gap(0.375),
		height: 4,
		overflow: "hidden",
		borderRadius: 2,
		backgroundColor: theme.colors["amber-100"],
	},
	shortcutFill: {
		height: "100%",
		borderRadius: 2,
		backgroundColor: theme.colors["amber-500"],
	},
	badge: {
		position: "absolute",
		top: -5,
		right: -5,
		minWidth: 20,
		height: 20,
		alignItems: "center",
		justifyContent: "center",
		paddingHorizontal: 4,
		borderWidth: 2,
		borderColor: theme.colors["neutral-0"],
		borderRadius: 10,
		backgroundColor: theme.colors["red-500"],
	},
	badgeText: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 10,
		color: theme.colors["neutral-0"],
	},
	pressed: {
		borderBottomWidth: 2,
		transform: [{ translateY: 2 }],
	},
}));
