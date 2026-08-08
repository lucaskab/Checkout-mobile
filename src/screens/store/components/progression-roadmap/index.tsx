import { type Href, router } from "expo-router";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { employeeDefinitions } from "@/data/employees";
import { marketExpansions } from "@/data/market-expansions";
import { itemCatalog } from "@/data/market-products";
import { productionSectors } from "@/data/production-sectors";
import { getNextShelfSlotUpgrade } from "@/data/shelf-capacity";
import { getExperienceToNextLevel } from "@/services/progression";
import { useGameStore } from "@/stores/game-store";

export function ProgressionRoadmap() {
	const daily = useGameStore((state) => state.daily);
	const dismissOfflineSummary = useGameStore(
		(state) => state.dismissOfflineSummary,
	);
	const employees = useGameStore((state) => state.employees.employees);
	const market = useGameStore((state) => state.market);
	const offlineSummary = useGameStore((state) => state.offlineSummary);
	const unlockedExpansions = useGameStore(
		(state) => state.unlockedMarketExpansionIds,
	);
	const unlockedShelfSlots = useGameStore((state) => state.unlockedShelfSlots);
	const claimDailyGoal = useGameStore((state) => state.claimDailyGoal);
	const experienceToNextLevel = getExperienceToNextLevel(market.level);
	const experienceProgress = Math.min(
		100,
		Math.round((market.experience / experienceToNextLevel) * 100),
	);
	const nextProduct = itemCatalog.find(
		(product) => product.unlockLevel > market.level,
	);
	const nextSector = productionSectors.find(
		(sector) => sector.requiredLevel > market.level,
	);
	const nextExpansion = marketExpansions.find(
		(expansion) => !unlockedExpansions.includes(expansion.id),
	);
	const nextEmployee = employeeDefinitions.find(
		(definition) =>
			market.level >= definition.level &&
			!employees.some((employee) => employee.role === definition.id),
	);
	const nextShelfSlot = getNextShelfSlotUpgrade(unlockedShelfSlots);

	function open(path: string) {
		router.push(path as Href);
	}

	return (
		<View style={styles.container}>
			<View style={styles.headingRow}>
				<View style={styles.headingIcon}>
					<GameIcon icon="trophy" style={styles.headingIconImage} />
				</View>
				<View style={styles.headingCopy}>
					<Text style={styles.eyebrow}>SEU PRÓXIMO PASSO</Text>
					<Text style={styles.title}>Central de evolução</Text>
				</View>
				<Text style={styles.streak}>🔥 {daily.streak}</Text>
			</View>

			<View style={styles.levelCard}>
				<View style={styles.levelRow}>
					<Text style={styles.level}>Nível {market.level}</Text>
					<Text style={styles.xp}>
						{market.experience}/{experienceToNextLevel} XP
					</Text>
				</View>
				<View style={styles.progressTrack}>
					<View
						style={[styles.progressFill, { width: `${experienceProgress}%` }]}
					/>
				</View>
				<Text style={styles.levelHint}>
					{nextProduct
						? `Faltam ${experienceToNextLevel - market.experience} XP para liberar ${nextProduct.name}.`
						: "Você desbloqueou todo o catálogo disponível."}
				</Text>
			</View>

			<Pressable
				onPress={() => open("/market-evolution")}
				style={({ pressed }) => [
					styles.evolutionCard,
					pressed && styles.pressed,
				]}
			>
				<View style={styles.evolutionBadge}>
					<GameIcon icon="market" style={styles.evolutionIcon} />
				</View>
				<View style={styles.evolutionCopy}>
					<Text style={styles.cardEyebrow}>MAPA VIVO EM 3D</Text>
					<Text style={styles.cardTitle}>Ver a cidade do mercado</Text>
					<Text style={styles.evolutionHint}>
						{nextExpansion
							? `Próxima construção: ${nextExpansion.name} · nível ${nextExpansion.requiredLevel}`
							: "Todas as áreas do bairro estão abertas."}
					</Text>
				</View>
				<Text style={styles.cardArrow}>›</Text>
			</Pressable>

			<View style={styles.dailyCard}>
				<View style={styles.dailyCopy}>
					<Text style={styles.cardEyebrow}>DESAFIO DE HOJE</Text>
					<Text style={styles.cardTitle}>Caixa cheio, mercado feliz</Text>
					<Text style={styles.dailyProgress}>
						{daily.revenue.toLocaleString("pt-BR")} /{" "}
						{daily.goal.toLocaleString("pt-BR")} moedas
					</Text>
					<View style={styles.dailyTrack}>
						<View
							style={[
								styles.dailyFill,
								{
									width: `${Math.min(100, (daily.revenue / daily.goal) * 100)}%`,
								},
							]}
						/>
					</View>
				</View>
				<GameButton
					disabled={!daily.goalReached || daily.claimed}
					label={daily.claimed ? "Resgatado" : "Resgatar + moedas"}
					onPress={claimDailyGoal}
					size="small"
					variant="coin"
				/>
			</View>

			<View style={styles.milestonesHeader}>
				<Text style={styles.sectionTitle}>Metas que já estão no radar</Text>
				<Text style={styles.sectionHint}>toque para continuar</Text>
			</View>
			<View style={styles.milestones}>
				<Milestone
					complete={!nextProduct}
					detail={
						nextProduct
							? `Nível ${nextProduct.unlockLevel}`
							: "Catálogo completo"
					}
					icon="basket"
					label={
						nextProduct ? `Liberar ${nextProduct.name}` : "Catálogo completo"
					}
					onPress={() => open("/products")}
				/>
				<Milestone
					complete={!nextSector}
					detail={
						nextSector ? `Nível ${nextSector.requiredLevel}` : "Tudo produzido"
					}
					icon="conveyor"
					label={nextSector ? `Abrir ${nextSector.name}` : "Todos os setores"}
					onPress={() => open("/sectors")}
				/>
				<Milestone
					complete={!nextEmployee}
					detail={
						nextEmployee
							? `${nextEmployee.hireCost.toLocaleString("pt-BR")} moedas`
							: "Equipe formada"
					}
					icon="manager"
					label={
						nextEmployee ? `Contratar ${nextEmployee.name}` : "Equipe completa"
					}
					onPress={() => open("/team")}
				/>
				{nextShelfSlot && (
					<Milestone
						complete={false}
						detail={`Nível ${nextShelfSlot.playerLevel}`}
						icon="shelf"
						label="Abrir nova gôndola"
						onPress={() => open("/")}
					/>
				)}
			</View>

			{market.lastShiftSummary && (
				<View style={styles.lastShift}>
					<View style={styles.lastShiftCopy}>
						<Text style={styles.cardEyebrow}>ÚLTIMO TURNO</Text>
						<Text style={styles.cardTitle}>
							+{market.lastShiftSummary.revenue.toLocaleString("pt-BR")} moedas
							· {market.lastShiftSummary.customersServed} clientes
						</Text>
					</View>
					<Text style={styles.lastShiftXp}>
						+{market.lastShiftSummary.experienceGained} XP
					</Text>
				</View>
			)}

			{offlineSummary && (
				<View style={styles.offlineCard}>
					<View style={styles.offlineCopy}>
						<Text style={styles.cardEyebrow}>ENQUANTO VOCÊ ESTAVA FORA</Text>
						<Text style={styles.cardTitle}>O mercado continuou girando</Text>
						<Text style={styles.offlineText}>
							+{offlineSummary.customers} clientes · +
							{offlineSummary.coins.toLocaleString("pt-BR")} moedas
						</Text>
					</View>
					<Pressable onPress={dismissOfflineSummary} style={styles.dismiss}>
						<Text style={styles.dismissText}>OK</Text>
					</Pressable>
				</View>
			)}
		</View>
	);
}

function Milestone({
	complete,
	detail,
	icon,
	label,
	onPress,
}: {
	complete: boolean;
	detail: string;
	icon: "basket" | "conveyor" | "manager" | "shelf";
	label: string;
	onPress: () => void;
}) {
	return (
		<Pressable
			disabled={complete}
			onPress={onPress}
			style={({ pressed }) => [styles.milestone, pressed && styles.pressed]}
		>
			<View
				style={[styles.milestoneIcon, complete && styles.milestoneComplete]}
			>
				<GameIcon icon={icon} style={styles.milestoneImage} />
			</View>
			<View style={styles.milestoneCopy}>
				<Text numberOfLines={2} style={styles.milestoneLabel}>
					{label}
				</Text>
				<Text style={styles.milestoneDetail}>
					{complete ? "concluído" : detail}
				</Text>
			</View>
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	container: {
		gap: theme.gap(1),
		marginBottom: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 2,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	headingRow: { flexDirection: "row", alignItems: "center", gap: theme.gap(1) },
	headingIcon: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-200"],
	},
	headingIconImage: { width: theme.gap(3), height: theme.gap(3) },
	headingCopy: { flex: 1 },
	eyebrow: {
		color: theme.colors["red-600"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1,
	},
	title: {
		marginTop: 2,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 20,
		fontWeight: "700",
	},
	streak: {
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 13,
	},
	levelCard: {
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-800"],
	},
	levelRow: {
		flexDirection: "row",
		justifyContent: "space-between",
		alignItems: "center",
	},
	level: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 18,
	},
	xp: {
		color: theme.colors["blue-100"],
		fontFamily: theme.fonts.family.number,
		fontSize: 11,
	},
	progressTrack: {
		height: 9,
		marginTop: theme.gap(0.75),
		overflow: "hidden",
		borderRadius: 99,
		backgroundColor: theme.colors["blue-700"],
	},
	progressFill: {
		height: "100%",
		borderRadius: 99,
		backgroundColor: theme.colors["amber-400"],
	},
	levelHint: {
		marginTop: theme.gap(0.5),
		color: theme.colors["blue-100"],
		fontSize: 11,
	},
	evolutionCard: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1),
		borderWidth: 2,
		borderColor: theme.colors["green-100"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["green-50"],
	},
	evolutionBadge: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["green-100"],
	},
	evolutionIcon: { width: theme.gap(3), height: theme.gap(3) },
	evolutionCopy: { flex: 1 },
	pressed: { opacity: 0.78 },
	cardEyebrow: {
		color: theme.colors["green-600"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1,
	},
	cardTitle: {
		marginTop: 2,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 15,
		fontWeight: "700",
	},
	cardArrow: { color: theme.colors["green-600"], fontSize: 28, lineHeight: 28 },
	evolutionHint: {
		marginTop: theme.gap(0.35),
		color: theme.colors["neutral-600"],
		fontSize: 11,
	},
	dailyCard: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-50"],
	},
	dailyCopy: { flex: 1 },
	dailyProgress: {
		marginTop: theme.gap(0.4),
		color: theme.colors["neutral-600"],
		fontFamily: theme.fonts.family.number,
		fontSize: 10,
	},
	dailyTrack: {
		height: 7,
		marginTop: theme.gap(0.5),
		overflow: "hidden",
		borderRadius: 99,
		backgroundColor: theme.colors["amber-100"],
	},
	dailyFill: {
		height: "100%",
		borderRadius: 99,
		backgroundColor: theme.colors["amber-400"],
	},
	milestonesHeader: {
		flexDirection: "row",
		justifyContent: "space-between",
		alignItems: "baseline",
		paddingTop: theme.gap(0.25),
	},
	sectionTitle: {
		color: theme.colors["neutral-700"],
		fontFamily: theme.fonts.family.bodyBold,
		fontSize: 12,
	},
	sectionHint: { color: theme.colors["neutral-500"], fontSize: 10 },
	milestones: { flexDirection: "row", flexWrap: "wrap", gap: theme.gap(0.75) },
	milestone: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		width: "48%",
		minHeight: theme.gap(5),
		padding: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-0"],
	},
	milestoneIcon: {
		width: theme.gap(3.5),
		height: theme.gap(3.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-100"],
	},
	milestoneComplete: { backgroundColor: theme.colors["green-100"] },
	milestoneImage: { width: theme.gap(2.25), height: theme.gap(2.25) },
	milestoneCopy: { flex: 1 },
	milestoneLabel: {
		color: theme.colors["neutral-700"],
		fontSize: 10,
		fontWeight: "700",
	},
	milestoneDetail: {
		marginTop: 1,
		color: theme.colors["neutral-500"],
		fontSize: 9,
	},
	offlineCard: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	lastShift: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(1),
		padding: theme.gap(1),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
	},
	lastShiftCopy: { flex: 1 },
	lastShiftXp: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
	},
	offlineCopy: { flex: 1 },
	offlineText: {
		marginTop: theme.gap(0.35),
		color: theme.colors["blue-700"],
		fontSize: 11,
		fontWeight: "700",
	},
	dismiss: {
		width: theme.gap(4),
		height: theme.gap(4),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-500"],
	},
	dismissText: {
		color: theme.colors["neutral-0"],
		fontSize: 10,
		fontWeight: "800",
	},
}));
