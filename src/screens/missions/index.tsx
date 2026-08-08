import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { StyleSheet } from "react-native-unistyles";
import type {
	MissionCategory,
	MissionDefinition,
	MissionStatus,
} from "@/@types/mission";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { getMissionIcon } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import { missions } from "@/data/missions";
import { getMissionProgress, getMissionStatus } from "@/services/missions";
import { useGameStore } from "@/stores/game-store";

type MissionFilter = "active" | "claimed" | "locked";

const filters: { id: MissionFilter; label: string }[] = [
	{ id: "active", label: "Em andamento" },
	{ id: "claimed", label: "Concluídas" },
	{ id: "locked", label: "Próximas" },
];

const categoryLabels: Record<MissionCategory, string> = {
	customers: "CLIENTES",
	inventory: "ESTOQUE",
	management: "GESTÃO",
	production: "PRODUÇÃO",
	progression: "PROGRESSÃO",
	sales: "VENDAS",
};

export function MissionsScreen() {
	const [filter, setFilter] = useState<MissionFilter>("active");
	const [feedback, setFeedback] = useState<string | null>(null);
	const game = useGameStore();
	const claimMission = game.claimMission;
	const missionEntries = missions.map((mission) => ({
		mission,
		progress: getMissionProgress(mission, game),
		status: getMissionStatus(mission, game),
	}));
	const claimableCount = missionEntries.filter(
		(entry) => entry.status === "claimable",
	).length;
	const claimedCount = missionEntries.filter(
		(entry) => entry.status === "claimed",
	).length;
	const filteredMissions = missionEntries
		.filter((entry) => {
			if (filter === "active") {
				return entry.status === "active" || entry.status === "claimable";
			}

			return entry.status === filter;
		})
		.sort((first, second) => {
			if (first.status === "claimable" && second.status !== "claimable") {
				return -1;
			}

			if (second.status === "claimable" && first.status !== "claimable") {
				return 1;
			}

			return (
				first.mission.requiredLevel - second.mission.requiredLevel ||
				first.mission.goal - second.mission.goal
			);
		});
	const completionPercent = Math.round((claimedCount / missions.length) * 100);

	function handleClaim(missionId: string) {
		if (claimMission(missionId)) {
			setFeedback("Recompensa resgatada e adicionada ao mercado.");
			return;
		}

		setFeedback(
			"Não foi possível resgatar. Verifique o espaço disponível no estoque.",
		);
	}

	function renderMission({
		index,
		item,
	}: LegendListRenderItemProps<(typeof missionEntries)[number]>) {
		return (
			<Animated.View entering={FadeInDown.delay(index * 45).duration(280)}>
				<MissionCard
					mission={item.mission}
					onClaim={handleClaim}
					progress={item.progress}
					status={item.status}
				/>
			</Animated.View>
		);
	}

	return (
		<View style={styles.screen}>
			<LegendList
				contentContainerStyle={styles.content}
				data={filteredMissions}
				estimatedItemSize={230}
				extraData={game}
				keyExtractor={(entry) => entry.mission.id}
				ListEmptyComponent={
					<View style={styles.emptyState}>
						<GameIcon icon="success" style={styles.emptyEmoji} />
						<Text style={styles.emptyTitle}>Tudo limpo por aqui</Text>
						<Text style={styles.emptyDescription}>
							Continue evoluindo para desbloquear novos objetivos.
						</Text>
					</View>
				}
				ListHeaderComponent={
					<View>
						<View style={styles.hero}>
							<View style={styles.heroTopBar}>
								<Pressable
									accessibilityLabel="Voltar"
									onPress={() => router.back()}
									style={styles.backButton}
								>
									<Text style={styles.backButtonText}>‹</Text>
								</Pressable>
								<View style={styles.heroBadge}>
									<Text style={styles.heroBadgeText}>JORNADA DO MERCADO</Text>
								</View>
								<View style={styles.levelBadge}>
									<Text style={styles.levelBadgeText}>
										Nível {game.market.level}
									</Text>
								</View>
							</View>

							<GameIcon icon="target" style={styles.heroEmoji} />
							<Text style={styles.heroTitle}>Central de missões</Text>
							<Text style={styles.heroDescription}>
								Complete objetivos, planeje sua evolução e resgate recompensas
								para acelerar o seu mercado.
							</Text>

							<View style={styles.overallProgress}>
								<View style={styles.overallProgressHeader}>
									<Text style={styles.overallProgressLabel}>
										PROGRESSO TOTAL
									</Text>
									<Text style={styles.overallProgressValue}>
										{claimedCount}/{missions.length}
									</Text>
								</View>
								<View style={styles.overallProgressTrack}>
									<View
										style={[
											styles.overallProgressFill,
											{ width: `${completionPercent}%` },
										]}
									/>
								</View>
							</View>

							<View style={styles.heroStats}>
								<View style={styles.heroStat}>
									<Text style={styles.heroStatValue}>{claimableCount}</Text>
									<Text style={styles.heroStatLabel}>para resgatar</Text>
								</View>
								<View style={styles.heroStatDivider} />
								<View style={styles.heroStat}>
									<Text style={styles.heroStatValue}>{claimedCount}</Text>
									<Text style={styles.heroStatLabel}>concluídas</Text>
								</View>
								<View style={styles.heroStatDivider} />
								<View style={styles.heroStat}>
									<Text style={styles.heroStatValue}>
										{missions.length - claimedCount}
									</Text>
									<Text style={styles.heroStatLabel}>restantes</Text>
								</View>
							</View>
						</View>
						<View style={styles.filterSection}>
							<View style={styles.sectionHeading}>
								<View>
									<Text style={styles.sectionTitle}>Seus objetivos</Text>
									<Text style={styles.sectionDescription}>
										Missões novas aparecem conforme seu nível aumenta.
									</Text>
								</View>
								{claimableCount > 0 && (
									<View style={styles.readyBadge}>
										<Text style={styles.readyBadgeText}>
											{claimableCount} pronta(s)
										</Text>
									</View>
								)}
							</View>
							{feedback && <Text style={styles.feedback}>{feedback}</Text>}
							<View style={styles.filters}>
								{filters.map((option) => {
									const isActive = option.id === filter;

									return (
										<Pressable
											key={option.id}
											onPress={() => setFilter(option.id)}
											style={[styles.filter, isActive && styles.activeFilter]}
										>
											<Text
												style={[
													styles.filterText,
													isActive && styles.activeFilterText,
												]}
											>
												{option.label}
											</Text>
										</Pressable>
									);
								})}
							</View>
						</View>
					</View>
				}
				renderItem={renderMission}
			/>
		</View>
	);
}

type MissionCardProps = {
	mission: MissionDefinition;
	onClaim: (missionId: string) => void;
	progress: number;
	status: MissionStatus;
};

function MissionCard({ mission, onClaim, progress, status }: MissionCardProps) {
	const displayedProgress = Math.min(progress, mission.goal);
	const progressPercent = Math.min(
		100,
		Math.round((displayedProgress / mission.goal) * 100),
	);
	const isLocked = status === "locked";
	const isClaimed = status === "claimed";
	const isClaimable = status === "claimable";

	return (
		<View
			style={[
				styles.missionCard,
				isClaimable && styles.claimableCard,
				isClaimed && styles.claimedCard,
				isLocked && styles.lockedCard,
			]}
		>
			<View style={styles.cardHeader}>
				<View style={styles.missionEmojiFrame}>
					<GameIcon
						icon={getMissionIcon(mission.id)}
						style={styles.missionEmoji}
					/>
				</View>
				<View style={styles.cardCopy}>
					<View style={styles.cardEyebrowRow}>
						<Text style={styles.categoryLabel}>
							{categoryLabels[mission.category]}
						</Text>
						{isLocked && (
							<View style={styles.unlockLabel}>
								<GameIcon icon="lock" style={styles.unlockIcon} />
								<Text style={styles.unlockLabelText}>
									Nível {mission.requiredLevel}
								</Text>
							</View>
						)}
						{isClaimed && <Text style={styles.claimedLabel}>✓ RESGATADA</Text>}
					</View>
					<Text style={styles.missionTitle}>{mission.title}</Text>
					<Text style={styles.missionDescription}>{mission.description}</Text>
				</View>
			</View>

			<View style={styles.progressHeader}>
				<Text style={styles.progressLabel}>
					{isLocked ? "BLOQUEADA" : "PROGRESSO"}
				</Text>
				<Text style={styles.progressValue}>
					{displayedProgress.toLocaleString("pt-BR")} /{" "}
					{mission.goal.toLocaleString("pt-BR")}
				</Text>
			</View>
			<View style={styles.progressTrack}>
				<View
					style={[
						styles.progressFill,
						isClaimable && styles.claimableProgressFill,
						isClaimed && styles.claimedProgressFill,
						{ width: `${progressPercent}%` },
					]}
				/>
			</View>

			<View style={styles.rewardSection}>
				<View>
					<Text style={styles.rewardLabel}>RECOMPENSAS</Text>
					<View style={styles.rewards}>
						<View style={styles.rewardChip}>
							<View style={styles.rewardValueRow}>
								<GameIcon icon="coin" style={styles.rewardIcon} />
								<Text style={styles.rewardText}>
									{mission.reward.coins.toLocaleString("pt-BR")}
								</Text>
							</View>
						</View>
						{mission.reward.items?.map((reward) => {
							const product = itemCatalog.find(
								(item) => item.id === reward.productId,
							);

							return (
								<View key={reward.productId} style={styles.rewardChip}>
									{product && (
										<ProductImage
											productId={product.id}
											style={styles.rewardImage}
										/>
									)}
									<Text style={styles.rewardText}>
										{reward.quantity}× {product?.name}
									</Text>
								</View>
							);
						})}
					</View>
				</View>

				{isClaimable && (
					<Pressable
						onPress={() => onClaim(mission.id)}
						style={({ pressed }) => [
							styles.claimButton,
							pressed && styles.pressedClaimButton,
						]}
					>
						<Text style={styles.claimButtonText}>Resgatar</Text>
					</Pressable>
				)}
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	screen: {
		flex: 1,
		backgroundColor: theme.colors["neutral-50"],
	},
	content: {
		gap: theme.gap(0.75),
		paddingBottom: theme.gap(4),
	},
	hero: {
		paddingHorizontal: theme.gap(2),
		paddingTop: theme.gap(1.25),
		paddingBottom: theme.gap(2),
		backgroundColor: theme.colors["blue-700"],
	},
	heroTopBar: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	backButton: {
		width: theme.gap(4),
		height: theme.gap(4),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	backButtonText: {
		marginTop: -3,
		color: theme.colors["neutral-800"],
		fontSize: 30,
	},
	heroBadge: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-600"],
	},
	heroBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["blue-100"],
		fontSize: 9,
		fontWeight: "700",
		letterSpacing: 0.8,
	},
	levelBadge: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["amber-400"],
	},
	levelBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["neutral-800"],
		fontSize: 9,
		fontWeight: "800",
	},
	heroEmoji: {
		marginTop: theme.gap(1.25),
		width: 64,
		height: 64,
		textAlign: "center",
	},
	heroTitle: {
		fontFamily: theme.fonts.family.headline,
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-0"],
		fontSize: 27,
		fontWeight: "800",
		textAlign: "center",
	},
	heroDescription: {
		alignSelf: "center",
		maxWidth: 340,
		marginTop: theme.gap(0.5),
		color: theme.colors["blue-100"],
		fontSize: theme.fonts.size.small,
		lineHeight: 18,
		textAlign: "center",
	},
	overallProgress: {
		marginTop: theme.gap(1.5),
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-800"],
	},
	overallProgressHeader: {
		flexDirection: "row",
		justifyContent: "space-between",
	},
	overallProgressLabel: {
		color: theme.colors["blue-200"],
		fontSize: 9,
		fontWeight: "700",
		letterSpacing: 0.6,
	},
	overallProgressValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-0"],
		fontSize: 10,
		fontWeight: "700",
	},
	overallProgressTrack: {
		height: theme.gap(0.75),
		overflow: "hidden",
		marginTop: theme.gap(0.75),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-600"],
	},
	overallProgressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["amber-400"],
	},
	heroStats: {
		flexDirection: "row",
		alignItems: "center",
		marginTop: theme.gap(1),
	},
	heroStat: {
		flex: 1,
		alignItems: "center",
	},
	heroStatValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.large,
		fontWeight: "800",
	},
	heroStatLabel: {
		marginTop: 2,
		color: theme.colors["blue-200"],
		fontSize: 9,
		fontWeight: "600",
	},
	heroStatDivider: {
		width: 1,
		height: theme.gap(3),
		backgroundColor: theme.colors["blue-500"],
	},
	filterSection: {
		padding: theme.gap(1.5),
	},
	sectionHeading: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	sectionTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large,
		fontWeight: "800",
	},
	sectionDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
	},
	feedback: {
		marginTop: theme.gap(0.75),
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	readyBadge: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["green-100"],
	},
	readyBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["green-600"],
		fontSize: 9,
		fontWeight: "700",
	},
	filters: {
		flexDirection: "row",
		gap: theme.gap(0.5),
		marginTop: theme.gap(1),
	},
	filter: {
		flex: 1,
		alignItems: "center",
		paddingVertical: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
	},
	activeFilter: {
		borderColor: theme.colors["blue-500"],
		backgroundColor: theme.colors["blue-500"],
	},
	filterText: {
		color: theme.colors["neutral-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	activeFilterText: {
		color: theme.colors["neutral-0"],
	},
	missionCard: {
		marginHorizontal: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 3 },
		shadowOpacity: 0.06,
		shadowRadius: 8,
		elevation: 2,
	},
	claimableCard: {
		borderColor: theme.colors["green-500"],
		backgroundColor: theme.colors["green-50"],
	},
	claimedCard: {
		opacity: 0.72,
		backgroundColor: theme.colors["neutral-100"],
	},
	lockedCard: {
		opacity: 0.62,
	},
	cardHeader: {
		flexDirection: "row",
		gap: theme.gap(1),
	},
	missionEmojiFrame: {
		width: theme.gap(5.5),
		height: theme.gap(5.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	missionEmoji: {
		width: 42,
		height: 42,
	},
	cardCopy: {
		flex: 1,
	},
	cardEyebrowRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
	},
	categoryLabel: {
		color: theme.colors["blue-600"],
		fontSize: 8,
		fontWeight: "800",
		letterSpacing: 0.7,
	},
	unlockLabel: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	unlockIcon: {
		width: 14,
		height: 14,
	},
	unlockLabelText: {
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "700",
	},
	claimedLabel: {
		color: theme.colors["green-600"],
		fontSize: 8,
		fontWeight: "800",
	},
	missionTitle: {
		fontFamily: theme.fonts.family.headline,
		marginTop: 2,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "800",
	},
	missionDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
		lineHeight: 14,
	},
	progressHeader: {
		flexDirection: "row",
		justifyContent: "space-between",
		marginTop: theme.gap(1),
	},
	progressLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "700",
		letterSpacing: 0.5,
	},
	progressValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-700"],
		fontSize: 9,
		fontWeight: "700",
	},
	progressTrack: {
		height: theme.gap(0.75),
		overflow: "hidden",
		marginTop: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	progressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-500"],
	},
	claimableProgressFill: {
		backgroundColor: theme.colors["green-500"],
	},
	claimedProgressFill: {
		backgroundColor: theme.colors["neutral-400"],
	},
	rewardSection: {
		flexDirection: "row",
		alignItems: "flex-end",
		justifyContent: "space-between",
		gap: theme.gap(1),
		marginTop: theme.gap(1),
	},
	rewardLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "700",
		letterSpacing: 0.5,
	},
	rewards: {
		flexDirection: "row",
		flexWrap: "wrap",
		gap: theme.gap(0.5),
		marginTop: theme.gap(0.5),
	},
	rewardChip: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.35),
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["amber-50"],
	},
	rewardText: {
		color: theme.colors["amber-600"],
		fontSize: 9,
		fontWeight: "700",
	},
	rewardValueRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	rewardIcon: {
		width: 18,
		height: 18,
	},
	rewardImage: {
		width: theme.gap(2.75),
		height: theme.gap(2.75),
	},
	claimButton: {
		alignItems: "center",
		justifyContent: "center",
		minWidth: theme.gap(9),
		minHeight: theme.gap(4),
		paddingHorizontal: theme.gap(1),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["green-500"],
	},
	pressedClaimButton: {
		opacity: 0.7,
	},
	claimButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: 10,
		fontWeight: "800",
	},
	emptyState: {
		alignItems: "center",
		marginHorizontal: theme.gap(1.5),
		padding: theme.gap(3),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	emptyEmoji: {
		width: 56,
		height: 56,
	},
	emptyTitle: {
		fontFamily: theme.fonts.family.headline,
		marginTop: theme.gap(0.75),
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "800",
	},
	emptyDescription: {
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		textAlign: "center",
	},
}));
