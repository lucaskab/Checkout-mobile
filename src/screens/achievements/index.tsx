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
	AchievementCategory,
	AchievementDefinition,
	AchievementRarity,
} from "@/@types/achievement";
import type { EmbeddedNavigationProps } from "@/@types/embedded-navigation";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { achievementRarityOrder, achievements } from "@/data/achievements";
import { getAchievementIcon } from "@/data/game-icon-assets";
import {
	getAchievementProgress,
	getAchievementStars,
	getAchievementTotals,
} from "@/services/achievements";
import { useGameStore } from "@/stores/game-store";

type AchievementFilter = "all" | AchievementCategory;

const categoryFilters: { id: AchievementFilter; label: string }[] = [
	{ id: "all", label: "Todas" },
	{ id: "progression", label: "Evolução" },
	{ id: "sales", label: "Vendas" },
	{ id: "customers", label: "Clientes" },
	{ id: "production", label: "Produção" },
	{ id: "management", label: "Gestão" },
	{ id: "logistics", label: "Logística" },
	{ id: "collection", label: "Coleção" },
	{ id: "specialist", label: "Especialistas" },
];

const categoryLabels: Record<AchievementCategory, string> = {
	collection: "COLEÇÃO",
	customers: "CLIENTES",
	logistics: "LOGÍSTICA",
	management: "GESTÃO",
	production: "PRODUÇÃO",
	progression: "EVOLUÇÃO",
	sales: "VENDAS",
	specialist: "ESPECIALISTA",
};

const rarityLabels: Record<AchievementRarity, string> = {
	common: "Comum",
	uncommon: "Incomum",
	rare: "Rara",
	epic: "Épica",
	legendary: "Lendária",
};

export function AchievementsScreen({ onBack }: EmbeddedNavigationProps = {}) {
	const [filter, setFilter] = useState<AchievementFilter>("all");
	const game = useGameStore();
	const totals = getAchievementTotals(game);
	const completionPercent = Math.round(
		(totals.stars / totals.totalStars) * 100,
	);
	const legendaryStars = achievements
		.filter((achievement) => achievement.rarity === "legendary")
		.reduce(
			(total, achievement) => total + getAchievementStars(achievement, game),
			0,
		);
	const entries = achievements
		.filter(
			(achievement) => filter === "all" || achievement.category === filter,
		)
		.map((achievement) => ({
			achievement,
			progress: getAchievementProgress(achievement, game),
			stars: getAchievementStars(achievement, game),
		}))
		.sort((first, second) => {
			const firstLocked =
				game.market.level < first.achievement.requiredLevel ? 1 : 0;
			const secondLocked =
				game.market.level < second.achievement.requiredLevel ? 1 : 0;
			const firstComplete =
				first.stars === first.achievement.thresholds.length ? 1 : 0;
			const secondComplete =
				second.stars === second.achievement.thresholds.length ? 1 : 0;

			return (
				firstLocked - secondLocked ||
				firstComplete - secondComplete ||
				second.stars - first.stars ||
				achievementRarityOrder[second.achievement.rarity] -
					achievementRarityOrder[first.achievement.rarity]
			);
		});

	function renderAchievement({
		index,
		item,
	}: LegendListRenderItemProps<(typeof entries)[number]>) {
		return (
			<Animated.View entering={FadeInDown.delay(index * 35).duration(260)}>
				<AchievementCard
					achievement={item.achievement}
					playerLevel={game.market.level}
					progress={item.progress}
					stars={item.stars}
				/>
			</Animated.View>
		);
	}

	return (
		<View style={styles.screen}>
			<LegendList
				contentContainerStyle={styles.content}
				data={entries}
				estimatedItemSize={240}
				extraData={game}
				keyExtractor={(entry) => entry.achievement.id}
				ListHeaderComponent={
					<View>
						<View style={styles.hero}>
							<View style={styles.heroTopBar}>
								<Pressable
									accessibilityLabel="Voltar"
									onPress={onBack ?? router.back}
									style={styles.backButton}
								>
									<Text style={styles.backButtonText}>‹</Text>
								</Pressable>
								<View style={styles.heroBadge}>
									<Text style={styles.heroBadgeText}>SALÃO DA FAMA</Text>
								</View>
								<View style={styles.levelBadge}>
									<Text style={styles.levelBadgeText}>
										Nível {game.market.level}
									</Text>
								</View>
							</View>

							<View style={styles.trophyFrame}>
								<GameIcon icon="trophy" style={styles.heroEmoji} />
								<View style={styles.trophyGlow} />
							</View>
							<Text style={styles.heroTitle}>Conquistas</Text>
							<Text style={styles.heroDescription}>
								Cada nível concluído vale uma estrela. Complete desafios raros e
								construa uma coleção que poucos gerentes terão.
							</Text>

							<View style={styles.starCounter}>
								<GameIcon icon="medal" style={styles.starCounterEmoji} />
								<View style={styles.starCounterCopy}>
									<Text style={styles.starCounterValue}>
										{totals.stars}/{totals.totalStars}
									</Text>
									<Text style={styles.starCounterLabel}>
										ESTRELAS CONQUISTADAS
									</Text>
								</View>
								<Text style={styles.starCounterPercent}>
									{completionPercent}%
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

							<View style={styles.heroStats}>
								<HeroStat
									label="máximas"
									value={totals.achievementsCompleted}
								/>
								<View style={styles.heroStatDivider} />
								<HeroStat label="lendárias" value={legendaryStars} />
								<View style={styles.heroStatDivider} />
								<HeroStat label="desafios" value={achievements.length} />
							</View>
						</View>

						<View style={styles.collectionHeading}>
							<Text style={styles.collectionTitle}>Sua coleção</Text>
							<Text style={styles.collectionDescription}>
								{achievements.length} conquistas · 5 níveis em cada uma
							</Text>
							<View style={styles.filters}>
								{categoryFilters.map((option) => {
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
				renderItem={renderAchievement}
			/>
		</View>
	);
}

function HeroStat({ label, value }: { label: string; value: number }) {
	return (
		<View style={styles.heroStat}>
			<Text style={styles.heroStatValue}>{value}</Text>
			<Text style={styles.heroStatLabel}>{label}</Text>
		</View>
	);
}

type AchievementCardProps = {
	achievement: AchievementDefinition;
	playerLevel: number;
	progress: number;
	stars: number;
};

function AchievementCard({
	achievement,
	playerLevel,
	progress,
	stars,
}: AchievementCardProps) {
	const isLocked = playerLevel < achievement.requiredLevel;
	const isComplete = stars === achievement.thresholds.length;
	const previousGoal = stars === 0 ? 0 : achievement.thresholds[stars - 1];
	const nextGoal =
		achievement.thresholds[stars] ??
		achievement.thresholds[achievement.thresholds.length - 1];
	const levelProgress = isComplete
		? 100
		: Math.min(
				100,
				Math.round(
					((progress - previousGoal) / Math.max(1, nextGoal - previousGoal)) *
						100,
				),
			);

	return (
		<View
			style={[
				styles.achievementCard,
				getRarityCardStyle(achievement.rarity),
				isLocked && styles.lockedCard,
				isComplete && styles.completeCard,
			]}
		>
			<View style={styles.cardHeader}>
				<View
					style={[
						styles.achievementEmojiFrame,
						getRarityEmojiStyle(achievement.rarity),
					]}
				>
					{achievement.targetProductId ? (
						<ProductImage
							productId={achievement.targetProductId}
							style={styles.achievementEmoji}
						/>
					) : (
						<GameIcon
							icon={getAchievementIcon(achievement.id)}
							style={styles.achievementEmoji}
						/>
					)}
				</View>
				<View style={styles.cardCopy}>
					<View style={styles.cardEyebrowRow}>
						<Text style={styles.categoryLabel}>
							{categoryLabels[achievement.category]}
						</Text>
						<View
							style={[
								styles.rarityBadge,
								getRarityBadgeStyle(achievement.rarity),
							]}
						>
							<Text
								style={[
									styles.rarityBadgeText,
									getRarityTextStyle(achievement.rarity),
								]}
							>
								{rarityLabels[achievement.rarity]}
							</Text>
						</View>
						{isLocked && (
							<View style={styles.lockLabel}>
								<GameIcon icon="lock" style={styles.lockIcon} />
								<Text style={styles.lockLabelText}>
									Nível {achievement.requiredLevel}
								</Text>
							</View>
						)}
					</View>
					<Text style={styles.achievementTitle}>{achievement.title}</Text>
					<Text style={styles.achievementDescription}>
						{achievement.description}
					</Text>
				</View>
			</View>

			<View style={styles.starsRow}>
				{achievement.thresholds.map((threshold, index) => {
					const isEarned = index < stars;
					const isNext = index === stars && !isLocked;

					return (
						<View key={threshold} style={styles.starMilestone}>
							<View
								style={[
									styles.starFrame,
									isEarned && styles.earnedStarFrame,
									isNext && styles.nextStarFrame,
								]}
							>
								<Text
									style={[
										styles.star,
										!isEarned && styles.emptyStar,
										isNext && styles.nextStar,
									]}
								>
									★
								</Text>
							</View>
							<Text style={styles.milestoneValue}>
								{formatCompactNumber(threshold)}
							</Text>
						</View>
					);
				})}
			</View>

			<View style={styles.progressHeader}>
				<Text style={styles.progressLabel}>
					{isLocked
						? "CONQUISTA BLOQUEADA"
						: isComplete
							? "NÍVEL MÁXIMO ALCANÇADO"
							: `PRÓXIMA ESTRELA · NÍVEL ${stars + 1}`}
				</Text>
				<Text style={styles.progressValue}>
					{Math.min(progress, nextGoal).toLocaleString("pt-BR")} /{" "}
					{nextGoal.toLocaleString("pt-BR")}
				</Text>
			</View>
			<View style={styles.progressTrack}>
				<View
					style={[
						styles.progressFill,
						isComplete && styles.completeProgressFill,
						{ width: `${isLocked ? 0 : levelProgress}%` },
					]}
				/>
			</View>
			{achievement.rarity === "legendary" && (
				<View style={styles.legendaryHint}>
					<GameIcon icon="crown" style={styles.legendaryIcon} />
					<Text style={styles.legendaryHintText}>
						O quinto nível pertence apenas aos gerentes mais dedicados.
					</Text>
				</View>
			)}
		</View>
	);
}

function formatCompactNumber(value: number) {
	if (value >= 1_000_000) {
		return `${value / 1_000_000}M`;
	}

	if (value >= 1_000) {
		return `${value / 1_000}k`;
	}

	return value.toString();
}

function getRarityCardStyle(rarity: AchievementRarity) {
	switch (rarity) {
		case "common":
			return styles.commonCard;
		case "uncommon":
			return styles.uncommonCard;
		case "rare":
			return styles.rareCard;
		case "epic":
			return styles.epicCard;
		case "legendary":
			return styles.legendaryCard;
	}
}

function getRarityEmojiStyle(rarity: AchievementRarity) {
	switch (rarity) {
		case "common":
			return styles.commonEmoji;
		case "uncommon":
			return styles.uncommonEmoji;
		case "rare":
			return styles.rareEmoji;
		case "epic":
			return styles.epicEmoji;
		case "legendary":
			return styles.legendaryEmoji;
	}
}

function getRarityBadgeStyle(rarity: AchievementRarity) {
	switch (rarity) {
		case "common":
			return styles.commonBadge;
		case "uncommon":
			return styles.uncommonBadge;
		case "rare":
			return styles.rareBadge;
		case "epic":
			return styles.epicBadge;
		case "legendary":
			return styles.legendaryBadge;
	}
}

function getRarityTextStyle(rarity: AchievementRarity) {
	switch (rarity) {
		case "common":
			return styles.commonText;
		case "uncommon":
			return styles.uncommonText;
		case "rare":
			return styles.rareText;
		case "epic":
			return styles.epicText;
		case "legendary":
			return styles.legendaryText;
	}
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
		backgroundColor: theme.colors["neutral-800"],
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
		borderWidth: 1,
		borderColor: theme.colors["amber-400"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["amber-500"],
	},
	heroBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["neutral-0"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 0.9,
	},
	levelBadge: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["violet-500"],
	},
	levelBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["neutral-0"],
		fontSize: 9,
		fontWeight: "800",
	},
	trophyFrame: {
		position: "relative",
		alignSelf: "center",
		alignItems: "center",
		justifyContent: "center",
		width: theme.gap(10),
		height: theme.gap(10),
		marginTop: theme.gap(1),
	},
	trophyGlow: {
		position: "absolute",
		width: theme.gap(8),
		height: theme.gap(8),
		borderRadius: theme.gap(4),
		backgroundColor: theme.colors["amber-400"],
		opacity: 0.2,
	},
	heroEmoji: {
		zIndex: 1,
		width: 72,
		height: 72,
	},
	heroTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-0"],
		fontSize: 28,
		fontWeight: "800",
		textAlign: "center",
	},
	heroDescription: {
		alignSelf: "center",
		maxWidth: 345,
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-200"],
		fontSize: theme.fonts.size.small,
		lineHeight: 18,
		textAlign: "center",
	},
	starCounter: {
		flexDirection: "row",
		alignItems: "center",
		marginTop: theme.gap(1.5),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["amber-500"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-800"],
	},
	starCounterEmoji: {
		width: 38,
		height: 38,
	},
	starCounterCopy: {
		flex: 1,
		marginLeft: theme.gap(0.75),
	},
	starCounterValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["amber-400"],
		fontSize: theme.fonts.size.large,
		fontWeight: "800",
	},
	starCounterLabel: {
		color: theme.colors["blue-200"],
		fontSize: 8,
		fontWeight: "800",
		letterSpacing: 0.7,
	},
	starCounterPercent: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "800",
	},
	overallProgressTrack: {
		height: theme.gap(0.75),
		overflow: "hidden",
		marginTop: theme.gap(0.75),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-700"],
	},
	overallProgressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["amber-400"],
	},
	heroStats: {
		flexDirection: "row",
		alignItems: "center",
		marginTop: theme.gap(1.25),
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
		color: theme.colors["neutral-300"],
		fontSize: 9,
		fontWeight: "600",
	},
	heroStatDivider: {
		width: 1,
		height: theme.gap(3),
		backgroundColor: theme.colors["neutral-600"],
	},
	collectionHeading: {
		padding: theme.gap(1.5),
	},
	collectionTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large,
		fontWeight: "800",
	},
	collectionDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
	},
	filters: {
		flexDirection: "row",
		flexWrap: "wrap",
		gap: theme.gap(0.5),
		marginTop: theme.gap(1),
	},
	filter: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.625),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	activeFilter: {
		borderColor: theme.colors["amber-500"],
		backgroundColor: theme.colors["amber-400"],
	},
	filterText: {
		color: theme.colors["neutral-600"],
		fontSize: 9,
		fontWeight: "700",
	},
	activeFilterText: {
		color: theme.colors["neutral-800"],
	},
	achievementCard: {
		marginHorizontal: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 3 },
		shadowOpacity: 0.07,
		shadowRadius: 8,
		elevation: 2,
	},
	commonCard: {
		borderColor: theme.colors["neutral-200"],
	},
	uncommonCard: {
		borderColor: theme.colors["green-500"],
	},
	rareCard: {
		borderColor: theme.colors["blue-400"],
	},
	epicCard: {
		borderColor: theme.colors["violet-400"],
	},
	legendaryCard: {
		borderColor: theme.colors["amber-400"],
		backgroundColor: theme.colors["amber-50"],
	},
	lockedCard: {
		opacity: 0.58,
	},
	completeCard: {
		borderWidth: 2,
	},
	cardHeader: {
		flexDirection: "row",
		gap: theme.gap(1),
	},
	achievementEmojiFrame: {
		width: theme.gap(6),
		height: theme.gap(6),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 1,
		borderRadius: theme.gap(1.75),
	},
	commonEmoji: {
		borderColor: theme.colors["neutral-200"],
		backgroundColor: theme.colors["neutral-100"],
	},
	uncommonEmoji: {
		borderColor: theme.colors["green-100"],
		backgroundColor: theme.colors["green-50"],
	},
	rareEmoji: {
		borderColor: theme.colors["blue-200"],
		backgroundColor: theme.colors["blue-50"],
	},
	epicEmoji: {
		borderColor: theme.colors["violet-100"],
		backgroundColor: theme.colors["violet-50"],
	},
	legendaryEmoji: {
		borderColor: theme.colors["amber-200"],
		backgroundColor: theme.colors["amber-100"],
	},
	achievementEmoji: {
		width: 46,
		height: 46,
	},
	cardCopy: {
		flex: 1,
	},
	cardEyebrowRow: {
		flexDirection: "row",
		alignItems: "center",
		flexWrap: "wrap",
		gap: theme.gap(0.5),
	},
	categoryLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "800",
		letterSpacing: 0.7,
	},
	rarityBadge: {
		paddingHorizontal: theme.gap(0.625),
		paddingVertical: 2,
		borderRadius: theme.gap(1),
	},
	commonBadge: {
		backgroundColor: theme.colors["neutral-100"],
	},
	uncommonBadge: {
		backgroundColor: theme.colors["green-100"],
	},
	rareBadge: {
		backgroundColor: theme.colors["blue-100"],
	},
	epicBadge: {
		backgroundColor: theme.colors["violet-100"],
	},
	legendaryBadge: {
		backgroundColor: theme.colors["amber-100"],
	},
	rarityBadgeText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "800",
	},
	commonText: {
		color: theme.colors["neutral-600"],
	},
	uncommonText: {
		color: theme.colors["green-600"],
	},
	rareText: {
		color: theme.colors["blue-600"],
	},
	epicText: {
		color: theme.colors["violet-600"],
	},
	legendaryText: {
		color: theme.colors["amber-600"],
	},
	lockLabel: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	lockIcon: {
		width: 14,
		height: 14,
	},
	lockLabelText: {
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "700",
	},
	achievementTitle: {
		fontFamily: theme.fonts.family.headline,
		marginTop: 3,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "800",
	},
	achievementDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
		lineHeight: 14,
	},
	starsRow: {
		flexDirection: "row",
		justifyContent: "space-between",
		marginTop: theme.gap(1.25),
		paddingHorizontal: theme.gap(0.5),
	},
	starMilestone: {
		alignItems: "center",
	},
	starFrame: {
		width: theme.gap(4),
		height: theme.gap(4),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-50"],
	},
	earnedStarFrame: {
		borderColor: theme.colors["amber-400"],
		backgroundColor: theme.colors["amber-100"],
	},
	nextStarFrame: {
		borderColor: theme.colors["blue-400"],
		backgroundColor: theme.colors["blue-50"],
	},
	star: {
		color: theme.colors["amber-400"],
		fontSize: 21,
	},
	emptyStar: {
		color: theme.colors["neutral-200"],
	},
	nextStar: {
		color: theme.colors["blue-400"],
	},
	milestoneValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "700",
	},
	progressHeader: {
		flexDirection: "row",
		justifyContent: "space-between",
		marginTop: theme.gap(1),
	},
	progressLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "800",
		letterSpacing: 0.4,
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
	completeProgressFill: {
		backgroundColor: theme.colors["amber-400"],
	},
	legendaryHint: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.35),
		marginTop: theme.gap(0.75),
	},
	legendaryIcon: {
		width: 18,
		height: 18,
	},
	legendaryHintText: {
		flex: 1,
		color: theme.colors["amber-600"],
		fontSize: 9,
		fontWeight: "700",
	},
}));
