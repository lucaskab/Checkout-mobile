import { router } from "expo-router";
import { useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { MarketExpansionId } from "@/@types/market-expansion";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import type { GameIconId } from "@/data/game-icon-assets";
import { marketExpansions } from "@/data/market-expansions";
import { useGameStore } from "@/stores/game-store";
import { MarketEvolutionCanvas } from "./components/market-evolution-canvas";
import type { EvolutionAreaId } from "./components/market-evolution-scene";

type AreaDefinition = {
	description: string;
	icon: GameIconId;
	id: EvolutionAreaId;
	name: string;
	requiredLevel?: number;
};

const coreArea: AreaDefinition = {
	description:
		"O coração do negócio: organize seus setores e acompanhe o crescimento do mercado.",
	icon: "market",
	id: "core",
	name: "Mercado central",
};

const expansionIcons: Record<MarketExpansionId, GameIconId> = {
	"fresh-wing": "garden",
	"service-wing": "calculator",
	"stock-annex": "warehouse",
	"premium-hall": "crown",
};

export function MarketEvolutionScreen() {
	const level = useGameStore((state) => state.market.level);
	const coins = useGameStore((state) => state.coins);
	const unlockedExpansionIds = useGameStore(
		(state) => state.unlockedMarketExpansionIds,
	);
	const [activeArea, setActiveArea] = useState<EvolutionAreaId>("core");
	const [rotation, setRotation] = useState(0.35);
	const [zoom, setZoom] = useState(30);

	const unlockedAreaIds: EvolutionAreaId[] = ["core", ...unlockedExpansionIds];
	const areas: AreaDefinition[] = [
		coreArea,
		...marketExpansions.map((expansion) => ({
			description: expansion.description,
			icon: expansionIcons[expansion.id],
			id: expansion.id,
			name: expansion.name,
			requiredLevel: expansion.requiredLevel,
		})),
	];
	const selectedArea = areas.find((area) => area.id === activeArea) ?? coreArea;
	const selectedIsUnlocked = unlockedAreaIds.includes(selectedArea.id);
	const unlockedCount = unlockedExpansionIds.length + 1;

	function rotate(direction: number) {
		setRotation((currentRotation) => currentRotation + direction * 0.55);
	}

	function changeZoom(direction: number) {
		setZoom((currentZoom) =>
			Math.min(42, Math.max(18, currentZoom + direction * 4)),
		);
	}

	return (
		<ScrollView contentContainerStyle={styles.content}>
			<View style={styles.hero}>
				<View style={styles.heroTopRow}>
					<View style={styles.heroIcon}>
						<GameIcon icon="market" style={styles.heroImage} />
					</View>
					<View style={styles.heroCopy}>
						<Text style={styles.eyebrow}>MAPA VIVO EM 3D</Text>
						<Text style={styles.title}>Cidade do mercado</Text>
					</View>
				</View>
				<Text style={styles.description}>
					Veja cada conquista virar um lugar no seu bairro. Toque em uma área
					para inspecionar e gire a cidade para encontrar o próximo objetivo.
				</Text>
				<View style={styles.heroStats}>
					<Text style={styles.heroStat}>Nível {level}</Text>
					<Text style={styles.heroStat}>{unlockedCount}/5 áreas</Text>
					<Text style={styles.heroStat}>
						🪙 {coins.toLocaleString("pt-BR")}
					</Text>
				</View>
			</View>

			<MarketEvolutionCanvas
				activeArea={activeArea}
				rotation={rotation}
				zoom={zoom}
				unlockedAreaIds={unlockedAreaIds}
			/>

			<View style={styles.cameraControls}>
				<GameButton
					icon="conveyor"
					label="Girar esquerda"
					onPress={() => rotate(-1)}
					size="small"
					variant="secondary"
				/>
				<GameButton
					icon="market"
					label="Girar direita"
					onPress={() => rotate(1)}
					size="small"
					variant="secondary"
				/>
				<Pressable
					accessibilityLabel="Afastar mapa"
					accessibilityRole="button"
					onPress={() => changeZoom(-1)}
					style={({ pressed }) => [
						styles.zoomButton,
						pressed && styles.pressed,
					]}
				>
					<Text style={styles.zoomButtonText}>−</Text>
				</Pressable>
				<Pressable
					accessibilityLabel="Aproximar mapa"
					accessibilityRole="button"
					onPress={() => changeZoom(1)}
					style={({ pressed }) => [
						styles.zoomButton,
						pressed && styles.pressed,
					]}
				>
					<Text style={styles.zoomButtonText}>+</Text>
				</Pressable>
			</View>

			<View style={styles.sectionHeader}>
				<View>
					<Text style={styles.sectionEyebrow}>CONQUISTAS DO BAIRRO</Text>
					<Text style={styles.sectionTitle}>O que já virou realidade?</Text>
				</View>
				<Text style={styles.sectionCount}>{unlockedCount}/5</Text>
			</View>

			<View style={styles.areaGrid}>
				{areas.map((area) => {
					const unlocked = unlockedAreaIds.includes(area.id);
					const selected = activeArea === area.id;

					return (
						<Pressable
							accessibilityRole="button"
							key={area.id}
							onPress={() => setActiveArea(area.id)}
							style={({ pressed }) => [
								styles.areaCard,
								unlocked && styles.areaCardUnlocked,
								selected && styles.areaCardSelected,
								pressed && styles.pressed,
							]}
						>
							<View
								style={[styles.areaIcon, unlocked && styles.areaIconUnlocked]}
							>
								<GameIcon
									icon={unlocked ? area.icon : "lock"}
									style={styles.areaIconImage}
								/>
							</View>
							<View style={styles.areaCopy}>
								<Text numberOfLines={2} style={styles.areaName}>
									{area.name}
								</Text>
								<Text
									style={[
										styles.areaStatus,
										unlocked && styles.areaStatusUnlocked,
									]}
								>
									{unlocked ? "CONQUISTADO" : `NÍVEL ${area.requiredLevel}`}
								</Text>
							</View>
						</Pressable>
					);
				})}
			</View>

			<View style={styles.selectedCard}>
				<View style={styles.selectedTopRow}>
					<View style={styles.selectedTitleCopy}>
						<Text style={styles.selectedEyebrow}>
							{selectedIsUnlocked ? "ÁREA CONQUISTADA" : "PRÓXIMA CONQUISTA"}
						</Text>
						<Text style={styles.selectedTitle}>{selectedArea.name}</Text>
					</View>
					<GameIcon
						icon={selectedIsUnlocked ? selectedArea.icon : "lock"}
						style={styles.selectedIcon}
					/>
				</View>
				<Text style={styles.selectedDescription}>
					{selectedArea.description}
				</Text>
				{selectedIsUnlocked ? (
					<Text style={styles.selectedStatus}>
						Essa construção já está no mapa. Continue evoluindo para decorar e
						ativar novos pontos do mercado.
					</Text>
				) : (
					<Text style={styles.selectedLocked}>
						Chegue ao nível {selectedArea.requiredLevel} e desbloqueie a área na
						Central de evolução.
					</Text>
				)}
			</View>

			<Pressable onPress={() => router.back()} style={styles.backButton}>
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
		backgroundColor: theme.colors["blue-800"],
	},
	heroTopRow: { flexDirection: "row", alignItems: "center", gap: theme.gap(1) },
	heroIcon: {
		width: theme.gap(5.5),
		height: theme.gap(5.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["green-500"],
	},
	heroImage: { width: theme.gap(3.25), height: theme.gap(3.25) },
	heroCopy: { flex: 1 },
	eyebrow: {
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
		marginTop: theme.gap(1),
		color: theme.colors["blue-100"],
		fontSize: 13,
		lineHeight: 19,
	},
	heroStats: {
		flexDirection: "row",
		justifyContent: "space-between",
		marginTop: theme.gap(1.25),
		paddingTop: theme.gap(1),
		borderTopWidth: 1,
		borderTopColor: theme.colors["blue-700"],
	},
	heroStat: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
	},
	cameraControls: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.75),
	},
	zoomButton: {
		width: theme.gap(4.25),
		height: theme.gap(4.25),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 2,
		borderBottomWidth: 4,
		borderColor: theme.colors["green-500"],
		borderBottomColor: theme.colors["green-600"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["green-500"],
	},
	zoomButtonText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 22,
		lineHeight: 22,
	},
	sectionHeader: {
		flexDirection: "row",
		justifyContent: "space-between",
		alignItems: "flex-end",
		paddingTop: theme.gap(0.25),
	},
	sectionEyebrow: {
		color: theme.colors["green-600"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1,
	},
	sectionTitle: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 18,
	},
	sectionCount: {
		color: theme.colors["green-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 13,
	},
	areaGrid: { flexDirection: "row", flexWrap: "wrap", gap: theme.gap(0.75) },
	areaCard: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.6),
		width: "48%",
		minHeight: theme.gap(6),
		padding: theme.gap(0.75),
		borderWidth: 2,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	areaCardUnlocked: { borderColor: theme.colors["green-100"] },
	areaCardSelected: {
		borderColor: theme.colors["amber-400"],
		backgroundColor: theme.colors["amber-50"],
	},
	areaIcon: {
		width: theme.gap(3.5),
		height: theme.gap(3.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	areaIconUnlocked: { backgroundColor: theme.colors["green-100"] },
	areaIconImage: { width: theme.gap(2.25), height: theme.gap(2.25) },
	areaCopy: { flex: 1 },
	areaName: {
		color: theme.colors["neutral-700"],
		fontSize: 10,
		fontWeight: "800",
	},
	areaStatus: {
		marginTop: 2,
		color: theme.colors["amber-600"],
		fontSize: 8,
		fontWeight: "800",
	},
	areaStatusUnlocked: { color: theme.colors["green-600"] },
	selectedCard: {
		padding: theme.gap(1.25),
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["green-50"],
	},
	selectedTopRow: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(1),
	},
	selectedTitleCopy: { flex: 1 },
	selectedEyebrow: {
		color: theme.colors["green-600"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1,
	},
	selectedTitle: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 20,
	},
	selectedIcon: { width: theme.gap(4), height: theme.gap(4) },
	selectedDescription: {
		marginTop: theme.gap(0.7),
		color: theme.colors["neutral-600"],
		fontSize: 12,
		lineHeight: 17,
	},
	selectedStatus: {
		marginTop: theme.gap(0.7),
		color: theme.colors["green-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	selectedLocked: {
		marginTop: theme.gap(0.7),
		color: theme.colors["amber-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	pressed: { opacity: 0.78 },
	backButton: { alignItems: "center", padding: theme.gap(1) },
	backText: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.bodyBold,
		fontSize: 13,
	},
}));
