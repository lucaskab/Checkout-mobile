import { type Href, router } from "expo-router";
import { Pressable, ScrollView, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { achievements } from "@/data/achievements";
import { getGameEvent } from "@/data/game-events";
import {
	type GameIconId,
	getGameEventIcon,
	getShopItemIcon,
} from "@/data/game-icon-assets";
import { marketProducts } from "@/data/market-products";
import { getShelfCapacity } from "@/data/shelf-capacity";
import { shopItems } from "@/data/shop-items";
import { getAchievementTotals } from "@/services/achievements";
import { getActiveGameEventEffects } from "@/services/game-events";
import { getExperienceToNextLevel } from "@/services/progression";
import { getShopEffects } from "@/services/shop-effects";
import { useGameStore } from "@/stores/game-store";

export function ProfileSheet() {
	const { closeBottomSheet } = useBottomSheet();
	const coins = useGameStore((state) => state.coins);
	const events = useGameStore((state) => state.events);
	const inventory = useGameStore((state) => state.inventory);
	const logistics = useGameStore((state) => state.logistics);
	const market = useGameStore((state) => state.market);
	const setMarketOpen = useGameStore((state) => state.setMarketOpen);
	const shelfStock = useGameStore((state) => state.shelfStock);
	const shelfUpgradeLevels = useGameStore((state) => state.shelfUpgradeLevels);
	const shop = useGameStore((state) => state.shop);
	const achievementStars = useGameStore(
		(state) => getAchievementTotals(state).stars,
	);
	const experienceToNextLevel = getExperienceToNextLevel(market.level);
	const experienceProgress = Math.min(
		100,
		Math.round((market.experience / experienceToNextLevel) * 100),
	);
	const shopEffects = getShopEffects(shop.ownedItemIds);
	const eventEffects = getActiveGameEventEffects(events);
	const activeEvent =
		events.activeEvent && events.activeEvent.endsAt > Date.now()
			? getGameEvent(events.activeEvent.eventId)
			: null;
	const customerArrivalMultiplier =
		shopEffects.customerArrivalMultiplier *
		eventEffects.customerArrivalMultiplier;
	const revenueMultiplier =
		shopEffects.revenueMultiplier * eventEffects.revenueMultiplier;
	const ownedItems = shopItems.filter((item) =>
		shop.ownedItemIds.includes(item.id),
	);
	const activeOrders = logistics.orders.filter(
		(order) => order.status !== "entregue",
	).length;
	const warehouseUnits = Object.values(inventory).reduce(
		(total, amount) => total + amount,
		0,
	);
	const shelfUnits = Object.values(shelfStock).reduce(
		(total, amount) => total + amount,
		0,
	);
	const totalShelfCapacity = marketProducts.reduce(
		(total, product) =>
			total + getShelfCapacity(shelfUpgradeLevels[product.shelfId]),
		0,
	);

	function toggleMarket() {
		setMarketOpen(!market.isOpen);
	}

	function openAchievements() {
		closeBottomSheet();
		router.push("/achievements" as Href);
	}

	return (
		<ScrollView
			contentContainerStyle={styles.content}
			showsVerticalScrollIndicator={false}
		>
			<View style={styles.profileHeader}>
				<View style={styles.profileVisual}>
					<GameIcon icon="manager" style={styles.profileEmoji} />
				</View>
				<View style={styles.profileCopy}>
					<Text style={styles.profileTitle}>Gerente do Mercado</Text>
					<Text style={styles.profileSubtitle}>
						Supermercado em crescimento
					</Text>
				</View>
				<Pressable onPress={closeBottomSheet} style={styles.closeButton}>
					<Text style={styles.closeText}>×</Text>
				</Pressable>
			</View>

			<View style={styles.levelCard}>
				<View style={styles.levelRow}>
					<Text style={styles.levelTitle}>Nível {market.level}</Text>
					<Text style={styles.levelValue}>
						{market.experience}/{experienceToNextLevel} XP
					</Text>
				</View>
				<View style={styles.progressTrack}>
					<View
						style={[styles.progressFill, { width: `${experienceProgress}%` }]}
					/>
				</View>
			</View>

			<Pressable
				onPress={openAchievements}
				style={({ pressed }) => [
					styles.achievementsCard,
					pressed && styles.pressedAchievementsCard,
				]}
			>
				<View style={styles.achievementsIcon}>
					<GameIcon icon="trophy" style={styles.achievementsEmoji} />
				</View>
				<View style={styles.achievementsCopy}>
					<Text style={styles.achievementsTitle}>Conquistas</Text>
					<Text style={styles.achievementsDescription}>
						{achievementStars}/{achievements.length * 5} estrelas conquistadas
					</Text>
				</View>
				<Text style={styles.achievementsArrow}>›</Text>
			</Pressable>

			<View style={styles.statGrid}>
				<Stat
					icon="coin"
					label="Moedas"
					value={coins.toLocaleString("pt-BR")}
				/>
				<Stat
					icon="diamond"
					label="Diamantes"
					value={logistics.premiumCurrency.toString()}
				/>
				<Stat
					icon="coin"
					label="Vendas hoje"
					value={market.todayRevenue.toString()}
				/>
				<Stat label="Clientes" value={market.customersServed.toString()} />
				<Stat
					label="Produtos"
					value={market.unlockedProductIds.length.toString()}
				/>
				<Stat label="Pedidos" value={activeOrders.toString()} />
			</View>

			<Section title="Estoque e prateleiras">
				<InfoRow
					label="Estoque no depósito"
					value={`${warehouseUnits} unidades`}
				/>
				<InfoRow
					label="Produtos expostos"
					value={`${shelfUnits}/${totalShelfCapacity}`}
				/>
				<InfoRow
					label="Capacidade máxima por slot"
					value={`${Math.max(
						...marketProducts.map((product) =>
							getShelfCapacity(shelfUpgradeLevels[product.shelfId]),
						),
					)} unid.`}
				/>
			</Section>

			<Section title="Bônus do mercado">
				<InfoRow
					label="Velocidade de chegada"
					value={formatMultiplier(customerArrivalMultiplier)}
				/>
				<InfoRow
					label="Itens extras por cliente"
					value={`+${shopEffects.maxProductsBonus}`}
				/>
				<InfoRow
					label="Receita global"
					value={formatMultiplier(revenueMultiplier)}
				/>
				{eventEffects.customerBudgetMultiplier !== 1 && (
					<InfoRow
						label="Orçamento dos clientes"
						value={formatMultiplier(eventEffects.customerBudgetMultiplier)}
					/>
				)}
				{eventEffects.experienceMultiplier !== 1 && (
					<InfoRow
						label="Experiência por venda"
						value={formatMultiplier(eventEffects.experienceMultiplier)}
					/>
				)}
				{eventEffects.productionDurationMultiplier !== 1 && (
					<InfoRow
						label="Tempo de produção"
						value={formatMultiplier(eventEffects.productionDurationMultiplier)}
					/>
				)}
				{eventEffects.supplierCostMultiplier !== 1 && (
					<InfoRow
						label="Custo de fornecedores"
						value={formatMultiplier(eventEffects.supplierCostMultiplier)}
					/>
				)}
				{eventEffects.supplierDurationMultiplier !== 1 && (
					<InfoRow
						label="Tempo de entrega"
						value={formatMultiplier(eventEffects.supplierDurationMultiplier)}
					/>
				)}
				{activeEvent && (
					<View style={styles.bonusRow}>
						<GameIcon
							icon={getGameEventIcon(activeEvent.id)}
							style={styles.bonusEmoji}
						/>
						<View style={styles.bonusCopy}>
							<Text style={styles.bonusTitle}>{activeEvent.name}</Text>
							<Text style={styles.bonusDescription}>
								{activeEvent.effectLabel}
							</Text>
						</View>
						<Text style={styles.eventStatus}>Evento</Text>
					</View>
				)}
				{ownedItems.length === 0 && !activeEvent ? (
					<Text style={styles.emptyBonus}>
						Compre equipamentos no Shop para liberar bônus.
					</Text>
				) : (
					ownedItems.map((item) => (
						<View key={item.id} style={styles.bonusRow}>
							<GameIcon
								icon={getShopItemIcon(item.id)}
								style={styles.bonusEmoji}
							/>
							<View style={styles.bonusCopy}>
								<Text style={styles.bonusTitle}>{item.name}</Text>
								<Text style={styles.bonusDescription}>{item.description}</Text>
							</View>
							<Text style={styles.bonusStatus}>Ativo</Text>
						</View>
					))
				)}
			</Section>

			<Section title="Ações rápidas">
				<Pressable
					onPress={toggleMarket}
					style={[
						styles.marketButton,
						market.isOpen && styles.closeMarketButton,
					]}
				>
					<Text style={styles.marketButtonText}>
						{market.isOpen ? "Fechar mercado" : "Abrir mercado"}
					</Text>
				</Pressable>
			</Section>
		</ScrollView>
	);
}

function Section({
	children,
	title,
}: {
	children: React.ReactNode;
	title: string;
}) {
	return (
		<View style={styles.section}>
			<Text style={styles.sectionTitle}>{title}</Text>
			{children}
		</View>
	);
}

function Stat({
	icon,
	label,
	value,
}: {
	icon?: GameIconId;
	label: string;
	value: string;
}) {
	return (
		<View style={styles.stat}>
			<View style={styles.statValueRow}>
				{icon && <GameIcon icon={icon} style={styles.statIcon} />}
				<Text style={styles.statValue}>{value}</Text>
			</View>
			<Text style={styles.statLabel}>{label}</Text>
		</View>
	);
}

function InfoRow({ label, value }: { label: string; value: string }) {
	return (
		<View style={styles.infoRow}>
			<Text style={styles.infoLabel}>{label}</Text>
			<Text style={styles.infoValue}>{value}</Text>
		</View>
	);
}

function formatMultiplier(multiplier: number) {
	const percentage = Math.round((multiplier - 1) * 100);
	const sign = percentage > 0 ? "+" : "";

	return `${sign}${percentage}%`;
}

const styles = StyleSheet.create((theme) => ({
	content: { paddingHorizontal: theme.gap(2), paddingBottom: theme.gap(3) },
	profileHeader: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
	},
	profileVisual: {
		width: theme.gap(7),
		height: theme.gap(7),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 2,
		borderColor: theme.colors["blue-300"],
		borderRadius: theme.gap(4),
		backgroundColor: theme.colors["blue-50"],
	},
	profileEmoji: { width: 48, height: 48 },
	profileCopy: { flex: 1 },
	profileTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	profileSubtitle: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
	},
	closeButton: {
		width: theme.gap(4),
		height: theme.gap(4),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-100"],
	},
	closeText: { color: theme.colors["neutral-600"], fontSize: 20 },
	levelCard: {
		marginTop: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	levelRow: { flexDirection: "row", justifyContent: "space-between" },
	levelTitle: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	levelValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["blue-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	progressTrack: {
		height: theme.gap(0.75),
		overflow: "hidden",
		marginTop: theme.gap(0.75),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-100"],
	},
	progressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-500"],
	},
	achievementsCard: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginTop: theme.gap(1.25),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["amber-50"],
	},
	pressedAchievementsCard: { opacity: 0.7 },
	achievementsIcon: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["amber-100"],
	},
	achievementsEmoji: { width: 34, height: 34 },
	achievementsCopy: { flex: 1 },
	achievementsTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "800",
	},
	achievementsDescription: {
		marginTop: 2,
		color: theme.colors["amber-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	achievementsArrow: {
		color: theme.colors["amber-600"],
		fontSize: 28,
		fontWeight: "700",
	},
	statGrid: {
		flexDirection: "row",
		flexWrap: "wrap",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1.5),
	},
	stat: {
		width: "31%",
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	statValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-800"],
		fontSize: 11,
		fontWeight: "700",
	},
	statValueRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	statIcon: {
		width: 18,
		height: 18,
	},
	statLabel: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 9,
		fontWeight: "600",
	},
	section: { marginTop: theme.gap(2) },
	sectionTitle: {
		fontFamily: theme.fonts.family.headline,
		marginBottom: theme.gap(0.75),
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	infoRow: {
		flexDirection: "row",
		justifyContent: "space-between",
		paddingVertical: theme.gap(0.75),
		borderBottomWidth: 1,
		borderBottomColor: theme.colors["neutral-100"],
	},
	infoLabel: {
		color: theme.colors["neutral-600"],
		fontSize: theme.fonts.size.small,
	},
	infoValue: {
		fontFamily: theme.fonts.family.number,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	emptyBonus: {
		padding: theme.gap(1.25),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
	},
	bonusRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		paddingVertical: theme.gap(1),
		borderBottomWidth: 1,
		borderBottomColor: theme.colors["neutral-100"],
	},
	bonusEmoji: { width: 32, height: 32 },
	bonusCopy: { flex: 1 },
	bonusTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	bonusDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
	},
	bonusStatus: {
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	eventStatus: {
		color: theme.colors["violet-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
	},
	marketButton: {
		alignItems: "center",
		justifyContent: "center",
		minHeight: theme.gap(5),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["green-500"],
	},
	closeMarketButton: { backgroundColor: theme.colors["red-500"] },
	marketButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
}));
