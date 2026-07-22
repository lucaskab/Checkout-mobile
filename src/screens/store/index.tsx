import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreAlert, StoreShelf } from "@/@types/store";
import { useBottomSheet } from "@/components/bottom-sheet";
import { itemCatalog, marketProducts } from "@/data/market-products";
import {
	getNextShelfCapacityUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import { getExperienceToNextLevel } from "@/services/progression";
import { useGameStore } from "@/stores/game-store";
import { ActiveCustomersCard } from "./components/active-customers-card";
import { AttentionCard } from "./components/attention-card";
import { MarketStatusCard } from "./components/market-status-card";
import { RevenueCard } from "./components/revenue-card";
import { ShelfGrid } from "./components/shelf-grid";
import { TopSellersCard } from "./components/top-sellers-card";
import { dashboardMetrics, lowStockAlerts, shelves } from "./data";

type DashboardSection =
	| "market"
	| "shelves"
	| "revenue"
	| "customers"
	| "attention"
	| "topSellers";

const dashboardSections: DashboardSection[] = [
	"market",
	"shelves",
	"revenue",
	"customers",
	"attention",
	"topSellers",
];

export function StoreScreen() {
	const { openBottomSheet } = useBottomSheet();
	const market = useGameStore((state) => state.market);
	const setMarketOpen = useGameStore((state) => state.setMarketOpen);
	const paidCustomers = market.customersWhoBought;
	const ticketAverage = paidCustomers
		? Math.round(market.todayRevenue / paidCustomers)
		: 0;
	const conversion = market.customersServed
		? Math.round((paidCustomers / market.customersServed) * 100)
		: 0;
	const experienceToNextLevel = getExperienceToNextLevel(market.level);
	const recentUnlocks = itemCatalog
		.filter((product) => market.recentUnlockProductIds.includes(product.id))
		.map((product) => product.name);
	const quickStats = [
		{
			icon: "👥",
			label: "Clientes",
			value: market.customersServed.toString(),
		},
		{ icon: "🛒", label: "Ticket médio", value: `🪙 ${ticketAverage}` },
		{ icon: "📈", label: "Conversão", value: `${conversion}%` },
	];
	const topSellers = marketProducts
		.map((product) => {
			const sold = market.soldByProduct[product.id] ?? 0;

			return {
				emoji: product.emoji,
				id: product.id.toString(),
				name: product.name,
				revenue: sold * product.sellingPrice,
				sold,
			};
		})
		.sort((first, second) => second.sold - first.sold)
		.slice(0, 3);

	function openStock(shelf: StoreShelf) {
		if (shelf.locked) {
			return;
		}

		openBottomSheet(<StockSheet shelf={shelf} />);
	}

	function handleAlertPress(alert: StoreAlert) {
		const shelf = shelves.find((item) => item.id === alert.id);

		if (shelf) {
			openStock(shelf);
		}
	}

	function toggleMarket() {
		setMarketOpen(!market.isOpen);
	}

	function renderSection({
		item,
	}: LegendListRenderItemProps<DashboardSection>) {
		switch (item) {
			case "market":
				return (
					<MarketStatusCard
						experience={market.experience}
						experienceToNextLevel={experienceToNextLevel}
						isOpen={market.isOpen}
						lastExperienceGain={market.lastExperienceGain}
						level={market.level}
						onToggle={toggleMarket}
						recentUnlocks={recentUnlocks}
						unlockedProductCount={market.unlockedProductIds.length}
					/>
				);
			case "shelves":
				return <ShelfGrid onPressShelf={openStock} shelves={shelves} />;
			case "revenue":
				return (
					<RevenueCard
						dailyGoal={dashboardMetrics.dailyGoal}
						quickStats={quickStats}
						revenue={market.todayRevenue}
					/>
				);
			case "customers":
				return <ActiveCustomersCard customers={market.recentCustomers} />;
			case "attention":
				return (
					<AttentionCard
						alerts={lowStockAlerts}
						onPressAlert={handleAlertPress}
					/>
				);
			case "topSellers":
				return <TopSellersCard items={topSellers} />;
		}
	}

	return (
		<LegendList
			contentContainerStyle={styles.content}
			data={dashboardSections}
			estimatedItemSize={220}
			extraData={market}
			keyExtractor={(section) => section}
			renderItem={renderSection}
		/>
	);
}

function StockSheet({ shelf }: { shelf: StoreShelf }) {
	const { closeBottomSheet } = useBottomSheet();
	const coins = useGameStore((state) => state.coins);
	const inventory = useGameStore((state) => state.inventory);
	const marketLevel = useGameStore((state) => state.market.level);
	const premiumCurrency = useGameStore(
		(state) => state.logistics.premiumCurrency,
	);
	const restockShelf = useGameStore((state) => state.restockShelf);
	const shelfStock = useGameStore((state) => state.shelfStock);
	const shelfUpgradeLevels = useGameStore((state) => state.shelfUpgradeLevels);
	const upgradeShelfCapacity = useGameStore(
		(state) => state.upgradeShelfCapacity,
	);
	const [feedback, setFeedback] = useState<string | null>(null);
	const availableQuantity = shelf.productId
		? (inventory[shelf.productId] ?? 0)
		: 0;
	const shelfQuantity = shelfStock[shelf.id] ?? 0;
	const upgradeLevel = shelfUpgradeLevels[shelf.id] ?? 0;
	const capacity = getShelfCapacity(upgradeLevel);
	const nextUpgrade = getNextShelfCapacityUpgrade(upgradeLevel);
	const isShelfFull = shelfQuantity >= capacity;
	const canUnlockUpgrade = Boolean(
		nextUpgrade && marketLevel >= nextUpgrade.playerLevel,
	);

	function restock() {
		if (!shelf.productId) {
			return;
		}

		const restocked = restockShelf({
			productId: shelf.productId,
			shelfId: shelf.id,
		});

		if (restocked) {
			setFeedback(`${shelf.name} foi adicionado à prateleira.`);
			return;
		}

		setFeedback(
			isShelfFull
				? "A prateleira está cheia. Aumente a capacidade para continuar."
				: "Não há unidades disponíveis no estoque.",
		);
	}

	function upgradeCapacity(currency: "coins" | "diamonds") {
		const upgraded = upgradeShelfCapacity(shelf.id, currency);

		if (upgraded && nextUpgrade) {
			setFeedback(`Capacidade ampliada para ${nextUpgrade.capacity} unidades.`);
			return;
		}

		if (nextUpgrade && marketLevel < nextUpgrade.playerLevel) {
			setFeedback(`Alcance o nível ${nextUpgrade.playerLevel} para melhorar.`);
			return;
		}

		setFeedback("Você não tem moeda suficiente para esta melhoria.");
	}

	return (
		<View style={styles.sheetContent}>
			<Text style={styles.sheetTitle}>Reabastecer {shelf.name}</Text>
			<Text style={styles.sheetDescription}>
				Você tem {availableQuantity} unidade
				{availableQuantity === 1 ? "" : "s"} disponível
				{availableQuantity === 1 ? "" : "is"} no estoque.
			</Text>
			<View style={styles.capacityCard}>
				<View>
					<Text style={styles.capacityLabel}>Capacidade da prateleira</Text>
					<Text style={styles.capacityValue}>
						{shelfQuantity}/{capacity} unidades
					</Text>
				</View>
				<Text style={styles.capacityIcon}>📚</Text>
			</View>
			<Pressable
				disabled={availableQuantity === 0 || isShelfFull}
				onPress={restock}
				style={[
					styles.restockButton,
					(availableQuantity === 0 || isShelfFull) &&
						styles.disabledRestockButton,
				]}
			>
				<Text style={styles.restockButtonText}>Adicionar 1 unidade</Text>
			</Pressable>
			{nextUpgrade && (
				<View style={styles.upgradeCard}>
					<Text style={styles.upgradeTitle}>
						Amplie para {nextUpgrade.capacity} unidades
					</Text>
					<Text style={styles.upgradeDescription}>
						Disponível no nível {nextUpgrade.playerLevel}. Melhore o fluxo de
						vendas mantendo mais unidades expostas.
					</Text>
					<View style={styles.upgradeActions}>
						<Pressable
							disabled={!canUnlockUpgrade || coins < nextUpgrade.coinCost}
							onPress={() => upgradeCapacity("coins")}
							style={[
								styles.coinUpgradeButton,
								(!canUnlockUpgrade || coins < nextUpgrade.coinCost) &&
									styles.disabledUpgradeButton,
							]}
						>
							<Text style={styles.coinUpgradeText}>
								🪙 {nextUpgrade.coinCost.toLocaleString("pt-BR")}
							</Text>
						</Pressable>
						<Pressable
							disabled={
								!canUnlockUpgrade || premiumCurrency < nextUpgrade.diamondCost
							}
							onPress={() => upgradeCapacity("diamonds")}
							style={[
								styles.diamondUpgradeButton,
								(!canUnlockUpgrade ||
									premiumCurrency < nextUpgrade.diamondCost) &&
									styles.disabledUpgradeButton,
							]}
						>
							<Text style={styles.diamondUpgradeText}>
								💎 {nextUpgrade.diamondCost}
							</Text>
						</Pressable>
					</View>
					{!canUnlockUpgrade && (
						<Text style={styles.lockedUpgradeText}>
							Faltam {nextUpgrade.playerLevel - marketLevel} nível
							{nextUpgrade.playerLevel - marketLevel === 1 ? "" : "is"}.
						</Text>
					)}
				</View>
			)}
			{feedback && <Text style={styles.feedback}>{feedback}</Text>}
			<Pressable onPress={closeBottomSheet} style={styles.closeButton}>
				<Text style={styles.closeButtonText}>Concluir</Text>
			</Pressable>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		gap: theme.gap(1.5),
		padding: theme.gap(1.75),
		paddingBottom: theme.gap(3),
		backgroundColor: theme.colors["neutral-50"],
	},
	sheetContent: {
		paddingHorizontal: theme.gap(2.75),
	},
	sheetTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large + 4,
		fontWeight: "700",
	},
	sheetDescription: {
		marginTop: theme.gap(0.625),
		color: theme.colors["neutral-600"],
		fontSize: theme.fonts.size.small,
		lineHeight: theme.gap(2),
	},
	capacityCard: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		marginTop: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	capacityLabel: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	capacityValue: {
		marginTop: 2,
		color: theme.colors["blue-700"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	capacityIcon: {
		fontSize: 24,
	},
	restockButton: {
		alignItems: "center",
		justifyContent: "center",
		minHeight: theme.gap(5),
		marginTop: theme.gap(2.25),
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["blue-500"],
	},
	disabledRestockButton: {
		backgroundColor: theme.colors["neutral-200"],
	},
	restockButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	upgradeCard: {
		marginTop: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["violet-100"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["violet-50"],
	},
	upgradeTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	upgradeDescription: {
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-600"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	upgradeActions: {
		flexDirection: "row",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1.25),
	},
	coinUpgradeButton: {
		flex: 1,
		alignItems: "center",
		justifyContent: "center",
		minHeight: theme.gap(4.25),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-50"],
	},
	diamondUpgradeButton: {
		flex: 1,
		alignItems: "center",
		justifyContent: "center",
		minHeight: theme.gap(4.25),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["violet-500"],
	},
	disabledUpgradeButton: {
		opacity: 0.45,
	},
	coinUpgradeText: {
		color: theme.colors["amber-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	diamondUpgradeText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	lockedUpgradeText: {
		marginTop: theme.gap(0.75),
		color: theme.colors["violet-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	feedback: {
		marginTop: theme.gap(1),
		color: theme.colors["green-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
		textAlign: "center",
	},
	closeButton: {
		alignItems: "center",
		justifyContent: "center",
		minHeight: theme.gap(5),
		marginTop: theme.gap(1),
		marginBottom: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(2.5),
	},
	closeButtonText: {
		color: theme.colors["neutral-700"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
}));
