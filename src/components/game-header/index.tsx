import { type Href, router, usePathname } from "expo-router";
import { Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { DevCheatSheet } from "@/components/dev-cheat-sheet";
import { GameEventBanner } from "@/components/game-event-banner";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProfileAvatar } from "@/components/profile-avatar";
import { SupermarketAwning } from "@/components/supermarket-awning";
import type { GameIconId } from "@/data/game-icon-assets";
import { getClaimableMissionCount } from "@/services/missions";
import { useGameStore } from "@/stores/game-store";

export const GameHeader = () => {
	const { openBottomSheet } = useBottomSheet();
	const insets = useSafeAreaInsets();
	const pathname = usePathname();
	const game = useGameStore();
	const coins = game.coins;
	const diamonds = game.logistics.premiumCurrency;
	const claimableMissions = getClaimableMissionCount(game);
	const isCurrencyStoreScreen = pathname === "/currency-store";
	const isMissionsScreen = pathname === "/missions";

	function openCurrencyStore() {
		if (!isCurrencyStoreScreen) {
			router.push("/currency-store" as Href);
		}
	}

	function openMissions() {
		if (!isMissionsScreen) {
			router.push("/missions" as Href);
		}
	}

	return (
		<View style={[styles.safeArea, { paddingTop: insets.top }]}>
			<View style={styles.content}>
				<View style={styles.leadingActions}>
					<ProfileAvatar />
					<View style={styles.brandPlate}>
						<Text style={styles.brandEyebrow}>CHECKOUT</Text>
						<Text style={styles.brandTitle}>MARKET</Text>
					</View>
					{__DEV__ && (
						<Pressable
							accessibilityLabel="Abrir menu de desenvolvimento"
							onPress={() => openBottomSheet(<DevCheatSheet />)}
							style={({ pressed }) => [
								styles.devButton,
								pressed && styles.pressedDevButton,
							]}
						>
							<GameIcon icon="toolbox" style={styles.devButtonEmoji} />
							<Text style={styles.devButtonText}>DEV</Text>
						</Pressable>
					)}
				</View>
				<View style={styles.trailingActions}>
					<Pressable
						accessibilityLabel="Abrir missões"
						disabled={isMissionsScreen}
						onPress={openMissions}
						style={({ pressed }) => [
							styles.missionsButton,
							isMissionsScreen && styles.activeMissionsButton,
							pressed && styles.pressedMissionsButton,
						]}
					>
						<GameIcon icon="target" style={styles.missionsEmoji} />
						<Text style={styles.missionsLabel}>Missões</Text>
						{claimableMissions > 0 && (
							<View style={styles.missionsBadge}>
								<Text style={styles.missionsBadgeText}>
									{claimableMissions > 9 ? "9+" : claimableMissions}
								</Text>
							</View>
						)}
					</Pressable>
					<View style={styles.currencyList}>
						<CurrencyChip
							accessibilityLabel="Comprar moedas"
							disabled={isCurrencyStoreScreen}
							icon="coin"
							onPress={openCurrencyStore}
							value={coins.toLocaleString("pt-BR")}
							variant="coin"
						/>
						<CurrencyChip
							accessibilityLabel="Comprar diamantes"
							disabled={isCurrencyStoreScreen}
							icon="diamond"
							onPress={openCurrencyStore}
							value={diamonds.toLocaleString("pt-BR")}
							variant="gem"
						/>
					</View>
				</View>
			</View>
			<GameEventBanner />
			<SupermarketAwning />
		</View>
	);
};

const CurrencyChip = ({
	accessibilityLabel,
	disabled,
	icon,
	onPress,
	value,
	variant,
}: {
	accessibilityLabel: string;
	disabled: boolean;
	icon: GameIconId;
	onPress: () => void;
	value: string;
	variant: "coin" | "gem";
}) => {
	return (
		<Pressable
			accessibilityLabel={accessibilityLabel}
			disabled={disabled}
			onPress={onPress}
			style={({ pressed }) => [
				styles.currencyChip,
				styles.currencyChipVariant(variant),
				pressed && styles.pressedCurrencyChip,
				disabled && styles.activeCurrencyChip,
			]}
		>
			<View style={styles.currencyIcon}>
				<GameIcon icon={icon} style={styles.currencyEmoji} />
			</View>
			<Text
				adjustsFontSizeToFit
				minimumFontScale={0.7}
				numberOfLines={1}
				style={styles.currencyValue}
			>
				{value}
			</Text>
		</Pressable>
	);
};

const styles = StyleSheet.create((theme) => ({
	safeArea: {
		backgroundColor: theme.colors["neutral-100"],
		borderBottomWidth: 3,
		borderBottomColor: theme.colors["neutral-300"],
	},
	content: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		paddingHorizontal: theme.gap(1.5),
		paddingVertical: theme.gap(0.875),
	},
	leadingActions: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
	},
	brandPlate: {
		justifyContent: "center",
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.375),
		borderWidth: 2,
		borderColor: theme.colors["neutral-300"],
		borderBottomWidth: 4,
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
	},
	brandEyebrow: {
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "800",
		letterSpacing: 1.1,
	},
	brandTitle: {
		marginTop: -1,
		color: theme.colors["red-500"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 11,
		fontWeight: "800",
		letterSpacing: 0.7,
	},
	devButton: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.625),
		borderWidth: 2,
		borderColor: theme.colors["violet-400"],
		borderBottomWidth: 5,
		borderBottomColor: theme.colors["violet-600"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["violet-50"],
	},
	pressedDevButton: {
		borderBottomWidth: 2,
		transform: [{ translateY: 3 }],
	},
	devButtonEmoji: { width: 18, height: 18 },
	devButtonText: {
		color: theme.colors["violet-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
		letterSpacing: 0.5,
	},
	currencyList: {
		alignItems: "flex-end",
		gap: theme.gap(0.5),
	},
	trailingActions: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
	},
	missionsButton: {
		position: "relative",
		alignItems: "center",
		justifyContent: "center",
		minWidth: theme.gap(6.5),
		minHeight: theme.gap(6),
		paddingHorizontal: theme.gap(0.75),
		borderWidth: 2,
		borderColor: theme.colors["blue-400"],
		borderBottomWidth: 5,
		borderBottomColor: theme.colors["blue-600"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-100"],
	},
	activeMissionsButton: {
		borderColor: theme.colors["blue-600"],
		borderBottomWidth: 2,
		backgroundColor: theme.colors["blue-200"],
		transform: [{ translateY: 3 }],
	},
	pressedMissionsButton: {
		borderBottomWidth: 2,
		transform: [{ translateY: 3 }],
	},
	missionsEmoji: {
		width: 24,
		height: 24,
	},
	missionsLabel: {
		marginTop: 1,
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "800",
	},
	missionsBadge: {
		position: "absolute",
		top: -theme.gap(0.5),
		right: -theme.gap(0.5),
		minWidth: theme.gap(2.25),
		height: theme.gap(2.25),
		alignItems: "center",
		justifyContent: "center",
		paddingHorizontal: theme.gap(0.5),
		borderWidth: 2,
		borderColor: theme.colors["neutral-0"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["red-500"],
	},
	missionsBadgeText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 8,
		fontWeight: "800",
	},
	currencyChip: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		minWidth: theme.gap(11),
		maxWidth: theme.gap(18),
		paddingLeft: theme.gap(0.375),
		paddingRight: theme.gap(1.25),
		paddingVertical: theme.gap(0.375),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderRadius: theme.gap(2),
	},
	currencyChipVariant: (variant: "coin" | "gem") => ({
		borderColor:
			variant === "coin"
				? theme.colors["amber-400"]
				: theme.colors["violet-400"],
		borderBottomColor:
			variant === "coin"
				? theme.colors["amber-500"]
				: theme.colors["violet-600"],
		backgroundColor:
			variant === "coin" ? theme.colors["amber-50"] : theme.colors["violet-50"],
	}),
	pressedCurrencyChip: {
		borderBottomWidth: 2,
		transform: [{ translateY: 2 }],
	},
	activeCurrencyChip: { opacity: 0.75 },
	currencyIcon: {
		width: theme.gap(2.75),
		height: theme.gap(2.75),
		flexShrink: 0,
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	currencyEmoji: {
		width: 20,
		height: 20,
	},
	currencyValue: {
		flexShrink: 1,
		textAlign: "right",
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
}));
