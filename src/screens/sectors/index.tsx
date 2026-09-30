import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { Pressable, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { StyleSheet } from "react-native-unistyles";
import type { ProductionSector } from "@/@types/production";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { getProductionSectorProductId } from "@/data/game-icon-assets";
import { productionSectors } from "@/data/production-sectors";
import { SectorDetailScreen } from "@/screens/sector-detail";
import { getSectorBuildStatus } from "@/services/interior-construction";
import { formatConstructionCountdown } from "@/data/market-expansions";
import { useGameStore } from "@/stores/game-store";

export function SectorsScreen() {
	const { closeBottomSheet, openBottomSheet } = useBottomSheet();
	const level = useGameStore((state) => state.market.level);
	const jobs = useGameStore((state) => state.production.jobs);
	const totalCrafted = useGameStore((state) => state.production.totalCrafted);
	// Sectors are paid for and built; the level only lets the player build them.
	const builtSectorIds = useGameStore((state) => state.builtSectorIds);
	const interiorConstructions = useGameStore((state) => state.interiorConstructions);
	const market = useGameStore((state) => state.market);
	const unlockedMarketExpansionIds = useGameStore((state) => state.unlockedMarketExpansionIds);
	const buildState = {
		builtSectorIds,
		interiorConstructions,
		market,
		unlockedMarketExpansionIds,
	} as Parameters<typeof getSectorBuildStatus>[0];
	const unlockedSectors = builtSectorIds.length;

	function openSector(sector: ProductionSector) {
		if (level < sector.requiredLevel) {
			return;
		}

		openBottomSheet(
			<SectorDetailScreen onBack={closeBottomSheet} sectorId={sector.id} />,
		);
	}

	function renderSector({
		index,
		item: sector,
	}: LegendListRenderItemProps<ProductionSector>) {
		const build = getSectorBuildStatus(buildState, sector.id);
		const isLocked = level < sector.requiredLevel;
		const activeJobs = jobs.filter((job) => job.sectorId === sector.id).length;

		return (
			<Animated.View entering={FadeInDown.delay(index * 70).duration(350)}>
				<Pressable
					disabled={isLocked}
					onPress={() => openSector(sector)}
					style={({ pressed }) => [
						styles.sectorCard,
						getSectorCardStyle(sector.id),
						pressed && styles.pressedCard,
						isLocked && styles.lockedCard,
					]}
				>
					<View style={styles.cardHeader}>
						<View style={[styles.iconFrame, getSectorIconStyle(sector.id)]}>
							<ProductImage
								productId={getProductionSectorProductId(sector.id)}
								style={styles.sectorImage}
							/>
						</View>
						<View style={styles.cardTitleCopy}>
							<Text style={styles.sectorName}>{sector.name}</Text>
							<Text style={styles.sectorSubtitle}>{sector.subtitle}</Text>
						</View>
						{isLocked ? (
							<View style={styles.levelBadge}>
								<Text style={styles.levelBadgeText}>
									Nível {sector.requiredLevel}
								</Text>
							</View>
						) : (
							<Text style={styles.arrow}>›</Text>
						)}
					</View>

					<Text style={styles.description}>{sector.description}</Text>

					<View style={styles.cardFooter}>
						<View style={styles.slotStatus}>
							<View style={styles.statusDot} />
							<Text style={styles.slotStatusText}>
								{isLocked
									? "Setor bloqueado"
									: build.status === "building"
										? `Em obra · ${formatConstructionCountdown(build.remainingMs)}`
										: build.status === "stored"
											? "No inventário · coloque no modo construir"
											: build.status === "queued"
												? "Na fila da obra"
										: build.status !== "built"
											? `Construir · ${build.coinCost.toLocaleString("pt-BR")} moedas`
											: activeJobs > 0
												? `${activeJobs} produção(ões) ativa(s)`
												: "Pronto para produzir"}
							</Text>
						</View>
						<Text style={styles.slotCount}>{sector.slotCount} slots</Text>
					</View>
				</Pressable>
			</Animated.View>
		);
	}

	return (
		<LegendList
			contentContainerStyle={styles.content}
			data={productionSectors}
			estimatedItemSize={190}
			keyExtractor={(sector) => sector.id}
			ListHeaderComponent={
				<View>
					<View style={styles.hero}>
						<View style={styles.heroGlow} />
						<Text style={styles.eyebrow}>CENTRAL DE PRODUÇÃO</Text>
						<Text style={styles.title}>Setores especiais</Text>
						<Text style={styles.heroDescription}>
							Transforme produtos básicos em itens exclusivos, mais lucrativos e
							valiosos para o seu mercado.
						</Text>
						<View style={styles.statsRow}>
							<View style={styles.stat}>
								<Text style={styles.statValue}>
									{unlockedSectors}/{productionSectors.length}
								</Text>
								<Text style={styles.statLabel}>setores construídos</Text>
							</View>
							<View style={styles.statDivider} />
							<View style={styles.stat}>
								<Text style={styles.statValue}>{jobs.length}</Text>
								<Text style={styles.statLabel}>em produção</Text>
							</View>
							<View style={styles.statDivider} />
							<View style={styles.stat}>
								<Text style={styles.statValue}>{totalCrafted}</Text>
								<Text style={styles.statLabel}>itens fabricados</Text>
							</View>
						</View>
					</View>

					<View style={styles.sectionHeading}>
						<View>
							<Text style={styles.sectionTitle}>
								Seu mercado, suas receitas
							</Text>
							<Text style={styles.sectionSubtitle}>
								Cada setor tem uma identidade e uma linha de produção.
							</Text>
						</View>
						<GameIcon icon="conveyor" style={styles.factoryEmoji} />
					</View>
				</View>
			}
			renderItem={renderSector}
		/>
	);
}

function getSectorCardStyle(sectorId: ProductionSector["id"]) {
	switch (sectorId) {
		case "padaria":
			return styles.bakeryCard;
		case "queijaria":
			return styles.cheeseCard;
		case "acougue":
			return styles.butcherCard;
		case "peixaria":
			return styles.fishCard;
		case "bebidas":
			return styles.drinksCard;
		case "sorvetes":
			return styles.iceCreamCard;
		case "adega":
			return styles.wineCard;
	}
}

function getSectorIconStyle(sectorId: ProductionSector["id"]) {
	switch (sectorId) {
		case "padaria":
			return styles.bakeryIcon;
		case "queijaria":
			return styles.cheeseIcon;
		case "acougue":
			return styles.butcherIcon;
		case "peixaria":
			return styles.fishIcon;
		case "bebidas":
			return styles.drinksIcon;
		case "sorvetes":
			return styles.iceCreamIcon;
		case "adega":
			return styles.wineIcon;
	}
}

const styles = StyleSheet.create((theme) => ({
	content: {
		gap: theme.gap(1.25),
		paddingHorizontal: theme.gap(1.5),
		paddingBottom: theme.gap(4),
		backgroundColor: theme.colors["neutral-50"],
	},
	hero: {
		overflow: "hidden",
		marginHorizontal: -theme.gap(1.5),
		paddingHorizontal: theme.gap(2),
		paddingTop: theme.gap(2),
		paddingBottom: theme.gap(2.25),
		backgroundColor: theme.colors["blue-800"],
	},
	heroGlow: {
		position: "absolute",
		top: -theme.gap(8),
		right: -theme.gap(4),
		width: theme.gap(22),
		height: theme.gap(22),
		borderRadius: theme.gap(12),
		backgroundColor: theme.colors["blue-500"],
		opacity: 0.35,
	},
	eyebrow: {
		color: theme.colors["blue-200"],
		fontSize: 10,
		fontWeight: "700",
		letterSpacing: 1.4,
	},
	title: {
		fontFamily: theme.fonts.family.headline,
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-0"],
		fontSize: 28,
		fontWeight: "700",
		letterSpacing: -0.7,
	},
	heroDescription: {
		maxWidth: 340,
		marginTop: theme.gap(0.75),
		color: theme.colors["blue-100"],
		fontSize: theme.fonts.size.small,
		lineHeight: 19,
	},
	statsRow: {
		flexDirection: "row",
		alignItems: "center",
		marginTop: theme.gap(2),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["blue-700"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-700"],
	},
	stat: { flex: 1, alignItems: "center" },
	statValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	statLabel: {
		marginTop: 2,
		color: theme.colors["blue-200"],
		fontSize: 9,
		fontWeight: "600",
		textAlign: "center",
	},
	statDivider: {
		width: 1,
		height: theme.gap(3),
		backgroundColor: theme.colors["blue-600"],
	},
	sectionHeading: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		paddingTop: theme.gap(2),
		paddingBottom: theme.gap(0.5),
	},
	sectionTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	sectionSubtitle: {
		marginTop: 3,
		color: theme.colors["neutral-500"],
		fontSize: 11,
	},
	factoryEmoji: { width: 34, height: 34 },
	sectorCard: {
		overflow: "hidden",
		padding: theme.gap(1.5),
		borderWidth: 1,
		borderRadius: theme.gap(2.25),
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 5 },
		shadowOpacity: 0.08,
		shadowRadius: 12,
		elevation: 3,
	},
	bakeryCard: {
		borderColor: theme.colors["amber-200"],
		backgroundColor: theme.colors["amber-50"],
	},
	cheeseCard: {
		borderColor: theme.colors["violet-100"],
		backgroundColor: theme.colors["violet-50"],
	},
	butcherCard: {
		borderColor: theme.colors["red-200"],
		backgroundColor: theme.colors["red-50"],
	},
	fishCard: {
		borderColor: theme.colors["blue-200"],
		backgroundColor: theme.colors["blue-50"],
	},
	drinksCard: {
		borderColor: theme.colors["green-100"],
		backgroundColor: theme.colors["green-50"],
	},
	iceCreamCard: {
		borderColor: theme.colors["violet-100"],
		backgroundColor: theme.colors["violet-50"],
	},
	wineCard: {
		borderColor: theme.colors["red-100"],
		backgroundColor: theme.colors["red-50"],
	},
	pressedCard: { opacity: 0.75, transform: [{ scale: 0.99 }] },
	lockedCard: { opacity: 0.58 },
	cardHeader: { flexDirection: "row", alignItems: "center" },
	iconFrame: {
		width: theme.gap(6),
		height: theme.gap(6),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.75),
	},
	bakeryIcon: { backgroundColor: theme.colors["amber-100"] },
	cheeseIcon: { backgroundColor: theme.colors["violet-100"] },
	butcherIcon: { backgroundColor: theme.colors["red-100"] },
	fishIcon: { backgroundColor: theme.colors["blue-100"] },
	drinksIcon: { backgroundColor: theme.colors["green-100"] },
	iceCreamIcon: { backgroundColor: theme.colors["violet-100"] },
	wineIcon: { backgroundColor: theme.colors["red-100"] },
	sectorImage: { width: 44, height: 44 },
	cardTitleCopy: { flex: 1, marginLeft: theme.gap(1.25) },
	sectorName: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	sectorSubtitle: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	levelBadge: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-0"],
	},
	levelBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["neutral-600"],
		fontSize: 9,
		fontWeight: "700",
	},
	arrow: {
		color: theme.colors["neutral-700"],
		fontSize: 32,
		fontWeight: "400",
	},
	description: {
		marginTop: theme.gap(1.25),
		color: theme.colors["neutral-700"],
		fontSize: theme.fonts.size.small,
		lineHeight: 18,
	},
	cardFooter: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		marginTop: theme.gap(1.25),
		paddingTop: theme.gap(1),
		borderTopWidth: 1,
		borderTopColor: theme.colors["neutral-150"],
	},
	slotStatus: { flexDirection: "row", alignItems: "center", gap: 6 },
	statusDot: {
		width: 7,
		height: 7,
		borderRadius: 4,
		backgroundColor: theme.colors["green-500"],
	},
	slotStatusText: {
		color: theme.colors["neutral-600"],
		fontSize: 10,
		fontWeight: "600",
	},
	slotCount: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-700"],
		fontSize: 10,
		fontWeight: "700",
	},
}));
