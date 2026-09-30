import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { EmbeddedNavigationProps } from "@/@types/embedded-navigation";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import {
	formatBuildDuration,
	formatConstructionCountdown,
	getMarketExpansion,
	getMarketExpansionSkipCost,
	getMissingMarketExpansionPrerequisites,
	marketExpansions,
} from "@/data/market-expansions";
import { useGameStore } from "@/stores/game-store";

export function ExpansionsScreen({ onBack }: EmbeddedNavigationProps = {}) {
	const coins = useGameStore((state) => state.coins);
	const level = useGameStore((state) => state.market.level);
	const unlockedIds = useGameStore((state) => state.unlockedMarketExpansionIds);
	const unlockMarketExpansion = useGameStore(
		(state) => state.unlockMarketExpansion,
	);
	const construction = useGameStore(
		(state) => state.marketExpansionConstruction,
	);
	const diamonds = useGameStore((state) => state.logistics.premiumCurrency);
	const finishMarketExpansionNow = useGameStore(
		(state) => state.finishMarketExpansionNow,
	);
	const [feedback, setFeedback] = useState<string | null>(null);
	const [now, setNow] = useState(() => Date.now());

	useEffect(() => {
		if (!construction) return;
		const timer = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(timer);
	}, [construction]);

	const building = construction
		? getMarketExpansion(construction.expansionId)
		: null;
	const remainingMs = construction ? construction.endsAt - now : 0;
	const skipCost = getMarketExpansionSkipCost(remainingMs);
	const progress = construction
		? Math.min(
				1,
				Math.max(
					0,
					(now - construction.startedAt) /
						Math.max(1, construction.endsAt - construction.startedAt),
				),
			)
		: 0;

	function unlock(expansionId: (typeof marketExpansions)[number]["id"]) {
		const didStart = unlockMarketExpansion(expansionId);
		setFeedback(
			didStart
				? "Obra iniciada! Acompanhe os guindastes no mapa do mercado."
				: "Suba de nível e junte moedas para liberar esta área.",
		);
	}

	function finishNow() {
		const didFinish = finishMarketExpansionNow();
		setFeedback(
			didFinish
				? "Obra concluída! O mapa do seu mercado cresceu."
				: `Você precisa de 💎 ${skipCost} para acelerar a obra.`,
		);
	}

	return (
		<ScrollView contentContainerStyle={styles.content}>
			<View style={styles.hero}>
				<View style={styles.heroIcon}>
					<GameIcon icon="market" style={styles.heroImage} />
				</View>
				<Text style={styles.eyebrow}>VISÃO DO BAIRRO</Text>
				<Text style={styles.title}>Expanda seu mercado</Text>
				<Text style={styles.description}>
					Cada nova ala abre espaço para uma estratégia diferente: produtos
					frescos, atendimento rápido, logística e experiências premium.
				</Text>
				<View style={styles.heroStats}>
					<Text style={styles.heroStat}>Nível {level}</Text>
					<Text style={styles.heroStat}>
						🪙 {coins.toLocaleString("pt-BR")}
					</Text>
					<Text style={styles.heroStat}>
						{unlockedIds.length}/{marketExpansions.length} áreas
					</Text>
				</View>
			</View>

			<View style={styles.mapPreview}>
				<View style={styles.mapRoadVertical} />
				<View style={styles.mapRoadHorizontal} />
				<View style={styles.mapMarket}>
					<Text style={styles.mapMarketText}>SEU MERCADO</Text>
				</View>
				{marketExpansions.map((expansion, index) => {
					const unlocked = unlockedIds.includes(expansion.id);

					return (
						<View
							key={expansion.id}
							style={[
								styles.mapExpansion,
								...(index < 4
									? [
											index < 2 ? styles.mapTop : styles.mapBottom,
											index % 2 === 0 ? styles.mapLeft : styles.mapRight,
										]
									: [styles.mapTop, styles.mapBack]),
								unlocked ? styles.mapUnlocked : styles.mapLocked,
							]}
						>
							<Text style={styles.mapExpansionText}>
								{unlocked ? "✓" : "?"}
							</Text>
						</View>
					);
				})}
			</View>

			{construction && building && (
				<View style={styles.works}>
					<Text style={styles.worksEyebrow}>🏗️ OBRA EM ANDAMENTO</Text>
					<Text style={styles.worksTitle}>{building.name}</Text>
					<View style={styles.worksTrack}>
						<View
							style={[styles.worksFill, { width: `${progress * 100}%` }]}
						/>
					</View>
					<Text style={styles.worksTime}>
						{remainingMs > 0
							? `Fica pronta em ${formatConstructionCountdown(remainingMs)}`
							: "Finalizando a obra..."}
					</Text>
					{remainingMs > 0 && (
						<GameButton
							disabled={diamonds < skipCost}
							label={`Acelerar agora por 💎 ${skipCost}`}
							onPress={finishNow}
							size="small"
							variant="success"
						/>
					)}
				</View>
			)}

			{feedback && <Text style={styles.feedback}>{feedback}</Text>}

			{marketExpansions.map((expansion) => {
				const unlocked = unlockedIds.includes(expansion.id);
				const underConstruction = construction?.expansionId === expansion.id;
				const levelLocked = level < expansion.requiredLevel;
				const coinLocked = coins < expansion.coinCost;
				const missing = getMissingMarketExpansionPrerequisites(
					expansion,
					unlockedIds,
				);

				return (
					<Pressable key={expansion.id} style={styles.card}>
						<View
							style={[styles.cardIcon, unlocked && styles.cardIconUnlocked]}
						>
							<GameIcon
								icon={unlocked ? "success" : "lock"}
								style={styles.cardIconImage}
							/>
						</View>
						<View style={styles.cardCopy}>
							<View style={styles.cardTitleRow}>
								<Text style={styles.cardTitle}>{expansion.name}</Text>
								<Text
									style={[styles.status, unlocked && styles.statusUnlocked]}
								>
									{unlocked
										? "LIBERADA"
										: underConstruction
											? "EM OBRA"
											: `NÍVEL ${expansion.requiredLevel}`}
								</Text>
							</View>
							<Text style={styles.cardDescription}>
								{expansion.description}
							</Text>
							{!unlocked && !underConstruction && (
								<Text style={styles.buildTime}>
									⏱ Obra de {formatBuildDuration(expansion.buildDurationMs)}
								</Text>
							)}
							{unlocked ? (
								<Text style={styles.unlockedText}>
									Área ativa no mapa do mercado
								</Text>
							) : underConstruction ? (
								<Text style={styles.buildingText}>
									Em construção · {formatConstructionCountdown(remainingMs)}
								</Text>
							) : (
								<GameButton
									disabled={
										levelLocked ||
										coinLocked ||
										missing.length > 0 ||
										construction !== null
									}
									label={
										levelLocked
											? `Chegue ao nível ${expansion.requiredLevel}`
											: missing.length > 0
												? `Construa antes: ${missing.map((item) => item.name).join(" e ")}`
												: construction
													? "Aguarde a obra atual terminar"
													: `Construir por ${expansion.coinCost.toLocaleString("pt-BR")}`
									}
									onPress={() => unlock(expansion.id)}
									size="small"
									variant="success"
								/>
							)}
						</View>
					</Pressable>
				);
			})}

			<Pressable onPress={onBack ?? router.back} style={styles.backButton}>
				<Text style={styles.backText}>Voltar para o mercado</Text>
			</Pressable>
		</ScrollView>
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		gap: theme.gap(1.25),
		padding: theme.gap(1.5),
		paddingBottom: theme.gap(4),
		backgroundColor: theme.colors["neutral-50"],
	},
	hero: {
		padding: theme.gap(1.5),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["green-600"],
	},
	heroIcon: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["green-500"],
	},
	heroImage: { width: theme.gap(3), height: theme.gap(3) },
	eyebrow: {
		marginTop: theme.gap(1),
		color: theme.colors["green-100"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1.2,
	},
	title: {
		marginTop: theme.gap(0.35),
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 27,
		fontWeight: "700",
	},
	description: {
		marginTop: theme.gap(0.75),
		color: theme.colors["green-100"],
		fontSize: 13,
		lineHeight: 19,
	},
	heroStats: {
		flexDirection: "row",
		justifyContent: "space-between",
		marginTop: theme.gap(1.25),
		paddingTop: theme.gap(1),
		borderTopWidth: 1,
		borderTopColor: theme.colors["green-500"],
	},
	heroStat: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
	},
	mapPreview: {
		height: 145,
		position: "relative",
		overflow: "hidden",
		borderWidth: 2,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["green-100"],
	},
	mapRoadVertical: {
		position: "absolute",
		top: 0,
		bottom: 0,
		left: "47%",
		width: 16,
		backgroundColor: theme.colors["neutral-200"],
		transform: [{ rotate: "12deg" }],
	},
	mapRoadHorizontal: {
		position: "absolute",
		top: "47%",
		right: 0,
		left: 0,
		height: 16,
		backgroundColor: theme.colors["neutral-200"],
		transform: [{ rotate: "-8deg" }],
	},
	mapMarket: {
		position: "absolute",
		top: 51,
		left: "37%",
		width: "26%",
		height: 43,
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 3,
		borderColor: theme.colors["red-400"],
		borderRadius: 10,
		backgroundColor: theme.colors["blue-500"],
	},
	mapMarketText: {
		color: theme.colors["neutral-0"],
		fontSize: 8,
		fontWeight: "800",
		textAlign: "center",
	},
	mapExpansion: {
		position: "absolute",
		width: 35,
		height: 35,
		alignItems: "center",
		justifyContent: "center",
		borderRadius: 11,
	},
	mapTop: { top: 14 },
	mapBottom: { bottom: 14 },
	mapLeft: { left: 22 },
	mapRight: { right: 22 },
	// The central warehouse sits behind the shop, at the back of the block.
	mapBack: { left: "50%", marginLeft: -17.5 },
	mapUnlocked: { backgroundColor: theme.colors["green-500"] },
	mapLocked: { backgroundColor: theme.colors["neutral-400"] },
	mapExpansionText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 18,
	},
	feedback: {
		padding: theme.gap(0.75),
		borderRadius: theme.gap(1),
		color: theme.colors["blue-700"],
		backgroundColor: theme.colors["blue-50"],
		fontSize: 12,
		textAlign: "center",
	},
	card: {
		flexDirection: "row",
		gap: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 2,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["neutral-0"],
	},
	cardIcon: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	cardIconUnlocked: { backgroundColor: theme.colors["green-100"] },
	cardIconImage: { width: theme.gap(2.75), height: theme.gap(2.75) },
	cardCopy: { flex: 1, gap: theme.gap(0.5) },
	cardTitleRow: {
		flexDirection: "row",
		justifyContent: "space-between",
		alignItems: "center",
		gap: theme.gap(0.5),
	},
	cardTitle: {
		flex: 1,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 16,
	},
	status: { color: theme.colors["amber-600"], fontSize: 9, fontWeight: "800" },
	statusUnlocked: { color: theme.colors["green-600"] },
	cardDescription: {
		color: theme.colors["neutral-600"],
		fontSize: 12,
		lineHeight: 17,
	},
	works: {
		gap: theme.gap(0.6),
		padding: theme.gap(1.25),
		borderWidth: 2,
		borderColor: theme.colors["amber-600"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["blue-50"],
	},
	worksEyebrow: {
		color: theme.colors["amber-600"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1.2,
	},
	worksTitle: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 17,
	},
	worksTrack: {
		height: 10,
		overflow: "hidden",
		borderRadius: 5,
		backgroundColor: theme.colors["neutral-200"],
	},
	worksFill: { height: "100%", backgroundColor: theme.colors["amber-600"] },
	worksTime: {
		color: theme.colors["neutral-700"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 12,
	},
	buildTime: { color: theme.colors["neutral-600"], fontSize: 11 },
	buildingText: {
		color: theme.colors["amber-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	unlockedText: {
		color: theme.colors["green-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	backButton: { alignItems: "center", padding: theme.gap(1) },
	backText: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.bodyBold,
		fontSize: 13,
	},
}));
