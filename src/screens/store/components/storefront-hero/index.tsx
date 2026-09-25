import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";

type StorefrontHeroProps = {
	customerSatisfaction: number;
	experience: number;
	experienceToNextLevel: number;
	isOpen: boolean;
	lastExperienceGain: number;
	onToggle: () => void;
	onOpenExpansions: () => void;
	recentUnlocks: string[];
	unlockedProductCount: number;
};

export function StorefrontHero({
	customerSatisfaction,
	experience,
	experienceToNextLevel,
	isOpen,
	lastExperienceGain,
	onToggle,
	onOpenExpansions,
	recentUnlocks,
	unlockedProductCount,
}: StorefrontHeroProps) {
	const experienceProgress = Math.min(
		Math.round((experience / experienceToNextLevel) * 100),
		100,
	);
	const activityUpdate = recentUnlocks.length
		? recentUnlocks.join(" · ")
		: lastExperienceGain > 0
			? `+${lastExperienceGain} XP na última venda`
			: `${unlockedProductCount} produtos desbloqueados`;

	return (
		<View style={styles.frame}>
			<View style={styles.signRow}>
				<View style={styles.sign}>
					<View style={styles.signEyebrowRow}>
						<GameIcon icon="market" style={styles.signEyebrowIcon} />
						<Text style={styles.signEyebrow}>SEU MERCADINHO</Text>
					</View>
					<Text style={styles.signTitle}>CHECKOUT MARKET</Text>
				</View>
				<Pressable
					accessibilityLabel="Ver expansões do mercado"
					accessibilityRole="button"
					onPress={onOpenExpansions}
					style={({ pressed }) => [
						styles.expansionButton,
						pressed && styles.expansionButtonPressed,
					]}
				>
					<GameIcon icon="construction" style={styles.expansionButtonIcon} />
					<Text style={styles.expansionButtonText}>EXPANDIR</Text>
				</Pressable>
				<View style={[styles.openPill, !isOpen && styles.closedPill]}>
					<View style={[styles.openDot, !isOpen && styles.closedDot]} />
					<Text style={[styles.openPillText, !isOpen && styles.closedPillText]}>
						{isOpen ? "ABERTO" : "FECHADO"}
					</Text>
				</View>
			</View>

			<View style={styles.footer}>
				<View style={styles.storeSummary}>
					<View style={styles.storeSummaryRow}>
						<View style={styles.storeStatusRow}>
							<GameIcon
								icon={isOpen ? "cart" : "broom"}
								style={styles.storeStatusIcon}
							/>
							<Text numberOfLines={1} style={styles.footerText}>
								{isOpen
									? "Loja em funcionamento"
									: "Loja pronta para o próximo turno"}
							</Text>
						</View>
						<Text style={styles.productCount}>
							{unlockedProductCount} produtos ·{" "}
							{Math.round(customerSatisfaction)}% satisfação
						</Text>
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
						<Text style={styles.experienceText}>
							{experience}/{experienceToNextLevel} XP
						</Text>
					</View>
					<Text numberOfLines={1} style={styles.activityUpdate}>
						{activityUpdate}
					</Text>
				</View>
				<GameButton
					icon={isOpen ? "lock" : "key"}
					label={isOpen ? "Fechar" : "Abrir"}
					onPress={onToggle}
					variant={isOpen ? "danger" : "success"}
				/>
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	frame: {
		overflow: "hidden",
		borderWidth: 3,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-100"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 4 },
		shadowOpacity: 0.18,
		shadowRadius: 10,
		elevation: 4,
		marginBottom: theme.gap(2),
	},
	signRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(0.75),
		backgroundColor: theme.colors["neutral-200"],
		borderBottomWidth: 2,
		borderBottomColor: theme.colors["neutral-300"],
	},
	sign: {
		flex: 1,
	},
	signEyebrow: {
		color: theme.colors["neutral-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "800",
		letterSpacing: 1,
	},
	signEyebrowRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.35),
	},
	signEyebrowIcon: {
		width: 18,
		height: 18,
	},
	signTitle: {
		marginTop: 1,
		color: theme.colors["red-600"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.medium,
		fontWeight: "800",
		letterSpacing: 0.4,
	},
	openPill: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		paddingHorizontal: theme.gap(0.875),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["green-500"],
	},
	closedPill: {
		backgroundColor: theme.colors["neutral-400"],
	},
	expansionButton: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.35),
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderWidth: 1,
		borderColor: theme.colors["blue-400"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-50"],
	},
	expansionButtonPressed: { opacity: 0.72 },
	expansionButtonIcon: { width: 16, height: 16 },
	expansionButtonText: {
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "800",
		letterSpacing: 0.4,
	},
	openDot: {
		width: theme.gap(0.75),
		height: theme.gap(0.75),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-0"],
	},
	closedDot: {
		backgroundColor: theme.colors["neutral-100"],
	},
	openPillText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 0.5,
	},
	closedPillText: {
		color: theme.colors["neutral-100"],
	},
	footer: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(1),
		borderTopWidth: 2,
		borderTopColor: theme.colors["neutral-300"],
		backgroundColor: theme.colors["neutral-100"],
	},
	storeSummary: {
		flex: 1,
	},
	storeSummaryRow: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(0.75),
	},
	storeStatusRow: {
		flex: 1,
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.4),
	},
	storeStatusIcon: {
		width: 20,
		height: 20,
	},
	footerText: {
		flex: 1,
		color: theme.colors["neutral-700"],
		fontSize: 11,
		fontWeight: "700",
	},
	productCount: {
		color: theme.colors["neutral-500"],
		fontFamily: theme.fonts.family.number,
		fontSize: 9,
		fontWeight: "700",
	},
	experienceRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginTop: theme.gap(0.625),
	},
	experienceTrack: {
		flex: 1,
		height: theme.gap(0.625),
		overflow: "hidden",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-100"],
	},
	experienceFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-500"],
	},
	experienceText: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 9,
		fontWeight: "700",
	},
	activityUpdate: {
		marginTop: theme.gap(0.375),
		color: theme.colors["green-600"],
		fontSize: 9,
		fontWeight: "700",
	},
}));
