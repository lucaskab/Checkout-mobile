import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { useState } from "react";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreAlert, StoreShelf } from "@/@types/store";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { itemCatalog } from "@/data/market-products";
import {
	getNextShelfCapacityUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import { getExperienceToNextLevel } from "@/services/progression";
import { getCurrentShelf } from "@/services/shelf-selection";
import { useGameStore } from "@/stores/game-store";
import { ActiveCustomersCard } from "./components/active-customers-card";
import { AttentionCard } from "./components/attention-card";
import { ShelfGrid } from "./components/shelf-grid";
import { StorefrontHero } from "./components/storefront-hero";
import { ProgressionRoadmap } from "./components/progression-roadmap";
import { ShiftSummarySheet } from "./components/shift-summary-sheet";
import { TopSellersCard } from "./components/top-sellers-card";
import { shelves } from "./data";

type DashboardSection =
	| "shelves"
	| "progression"
	| "customers"
	| "attention"
	| "topSellers";

const dashboardSections: DashboardSection[] = [
	"progression",
	"shelves",
	"customers",
	"attention",
	"topSellers",
];

export function StoreScreen() {
	const { openBottomSheet } = useBottomSheet();
	const market = useGameStore((state) => state.market);
	const shelfAssignments = useGameStore((state) => state.shelfAssignments);
	const shelfPrices = useGameStore((state) => state.shelfPrices);
	const shelfStock = useGameStore((state) => state.shelfStock);
	const unlockedShelfSlots = useGameStore((state) => state.unlockedShelfSlots);
	const setMarketOpen = useGameStore((state) => state.setMarketOpen);
	const experienceToNextLevel = getExperienceToNextLevel(market.level);
	const recentUnlocks = itemCatalog
		.filter((product) => market.recentUnlockProductIds.includes(product.id))
		.map((product) => product.name);
	const topSellers = itemCatalog
		.map((product) => {
			const sold = market.soldByProduct[product.id] ?? 0;
			const shelfId = Object.entries(shelfAssignments).find(
				([, productId]) => productId === product.id,
			)?.[0];

			return {
				id: product.id.toString(),
				name: product.name,
				productId: product.id,
				revenue:
					sold *
					(shelfId
						? (shelfPrices[shelfId] ?? product.sellingPrice)
						: product.sellingPrice),
				sold,
			};
		})
		.filter((product) => product.sold > 0)
		.sort((first, second) => second.sold - first.sold)
		.slice(0, 3);

	const shelfAlerts: StoreAlert[] = shelves
		.slice(0, unlockedShelfSlots)
		.flatMap((shelf) => {
			const product = itemCatalog.find(
				(item) => item.id === shelfAssignments[shelf.id],
			);
			const quantity = shelfStock[shelf.id] ?? 0;

			if (!product || quantity > 2) {
				return [];
			}

			return [
				{
					actionLabel: "Reabastecer",
					id: shelf.id,
					issue:
						quantity === 0
							? "A prateleira está vazia."
							: `Restam ${quantity} unidades na prateleira.`,
					name: product.name,
					productId: product.id,
					type: "low" as const,
				},
			];
		});

	function openStock(shelf: StoreShelf) {
		if (shelf.locked) {
			openBottomSheet(<ShelfSlotUnlockSheet shelf={shelf} />);
			return;
		}

		const configuredShelf = getCurrentShelf(
			shelf,
			() => useGameStore.getState().shelfAssignments,
		);

		if (!configuredShelf.productId) {
			openBottomSheet(<ShelfProductPicker shelf={configuredShelf} />);
			return;
		}

		openBottomSheet(<StockSheet shelf={configuredShelf} />);
	}

	function handleAlertPress(alert: StoreAlert) {
		const shelf = shelves.find((item) => item.id === alert.id);

		if (shelf) {
			openStock(shelf);
		}
	}

	function toggleMarket() {
		const wasOpen = market.isOpen;
		setMarketOpen(!wasOpen);

		if (wasOpen) {
			const summary = useGameStore.getState().market.lastShiftSummary;

			if (summary) {
				openBottomSheet(<ShiftSummarySheet summary={summary} />);
			}
		}
	}

	function renderSection({
		item,
	}: LegendListRenderItemProps<DashboardSection>) {
			switch (item) {
			case "shelves":
				return <ShelfGrid onPressShelf={openStock} shelves={shelves} />;
			case "progression":
				return <ProgressionRoadmap />;
			case "customers":
				return <ActiveCustomersCard customers={market.recentCustomers} />;
			case "attention":
				return (
					<AttentionCard alerts={shelfAlerts} onPressAlert={handleAlertPress} />
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
			extraData={{
				market,
				shelfAssignments,
				shelfPrices,
				shelfStock,
				unlockedShelfSlots,
			}}
			keyExtractor={(section) => section}
			ListHeaderComponent={
				<StorefrontHero
					activeCustomers={market.recentCustomers.length}
					customerSatisfaction={market.customerSatisfaction}
					experience={market.experience}
					experienceToNextLevel={experienceToNextLevel}
					isOpen={market.isOpen}
					nextCustomerAt={market.nextCustomerAt}
					lastExperienceGain={market.lastExperienceGain}
					level={market.level}
					onToggle={toggleMarket}
					recentUnlocks={recentUnlocks}
					unlockedProductCount={market.unlockedProductIds.length}
				/>
			}
			renderItem={renderSection}
		/>
	);
}

function ShelfSlotUnlockSheet({ shelf }: { shelf: StoreShelf }) {
	const { closeBottomSheet } = useBottomSheet();
	const coins = useGameStore((state) => state.coins);
	const marketLevel = useGameStore((state) => state.market.level);
	const unlockNextShelfSlot = useGameStore(
		(state) => state.unlockNextShelfSlot,
	);
	const [feedback, setFeedback] = useState<string | null>(null);
	if (!shelf.nextSlotUpgrade) {
		return null;
	}

	const nextSlotUpgrade = shelf.nextSlotUpgrade;

	const hasRequiredLevel = marketLevel >= nextSlotUpgrade.playerLevel;
	const hasEnoughCoins = coins >= nextSlotUpgrade.coinCost;

	function unlockShelfSlot() {
		if (unlockNextShelfSlot()) {
			setFeedback("Nova vaga liberada. Agora você pode abastecê-la.");
			return;
		}

		setFeedback(
			hasRequiredLevel
				? "Você não tem moedas suficientes para liberar esta vaga."
				: `Alcance o nível ${nextSlotUpgrade.playerLevel} para liberar esta vaga.`,
		);
	}

	return (
		<View style={styles.sheetContent}>
			<Text style={styles.sheetTitle}>Expanda suas prateleiras</Text>
			<Text style={styles.sheetDescription}>
				Libere uma nova vaga para expor mais produtos e atender mais clientes.
			</Text>
			<View style={styles.shelfSlotCard}>
				<GameIcon icon="market" style={styles.shelfSlotIcon} />
				<View style={styles.shelfSlotDetails}>
					<Text style={styles.shelfSlotTitle}>Próxima vaga de prateleira</Text>
					<Text style={styles.shelfSlotRequirement}>
						Requer nível {nextSlotUpgrade.playerLevel}
					</Text>
				</View>
			</View>
			<GameButton
				disabled={!hasRequiredLevel || !hasEnoughCoins}
				fullWidth
				icon="coin"
				label={`Liberar por ${nextSlotUpgrade.coinCost.toLocaleString("pt-BR")}`}
				onPress={unlockShelfSlot}
				style={styles.sheetActionButton}
				variant="gem"
			/>
			{!hasRequiredLevel && (
				<Text style={styles.lockedUpgradeText}>
					Faltam {nextSlotUpgrade.playerLevel - marketLevel} nível
					{nextSlotUpgrade.playerLevel - marketLevel === 1 ? "" : "is"}.
				</Text>
			)}
			{feedback && <Text style={styles.feedback}>{feedback}</Text>}
			<GameButton
				fullWidth
				label="Concluir"
				onPress={closeBottomSheet}
				style={styles.sheetActionButton}
				variant="secondary"
			/>
		</View>
	);
}

function StockSheet({ shelf }: { shelf: StoreShelf }) {
	const { closeBottomSheet, openBottomSheet } = useBottomSheet();
	const clearShelf = useGameStore((state) => state.clearShelf);
	const coins = useGameStore((state) => state.coins);
	const inventory = useGameStore((state) => state.inventory);
	const marketLevel = useGameStore((state) => state.market.level);
	const premiumCurrency = useGameStore(
		(state) => state.logistics.premiumCurrency,
	);
	const restockShelf = useGameStore((state) => state.restockShelf);
	const shelfStock = useGameStore((state) => state.shelfStock);
	const shelfPrices = useGameStore((state) => state.shelfPrices);
	const setShelfPrice = useGameStore((state) => state.setShelfPrice);
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
	const product = itemCatalog.find((item) => item.id === shelf.productId);
	const shelfPrice = product
		? (shelfPrices[shelf.id] ?? product.sellingPrice)
		: null;
	const nextUpgrade = getNextShelfCapacityUpgrade(upgradeLevel);
	const isShelfFull = shelfQuantity >= capacity;
	const canUnlockUpgrade = Boolean(
		nextUpgrade && marketLevel >= nextUpgrade.playerLevel,
	);

	function restock() {
		if (!shelf.productId) {
			return;
		}

		restockShelf({
			productId: shelf.productId,
			shelfId: shelf.id,
		});

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

	function adjustPrice(amount: number) {
		if (!product || shelfPrice === null) {
			return;
		}

		setShelfPrice(shelf.id, shelfPrice + amount);
	}

	function removeProduct(chooseAnother: boolean) {
		if (!clearShelf(shelf.id)) {
			setFeedback(
				"Não há espaço no estoque para devolver as unidades expostas.",
			);
			return;
		}

		if (chooseAnother) {
			openBottomSheet(<ShelfProductPicker shelf={shelf} />);
			return;
		}

		closeBottomSheet();
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
				<GameIcon icon="shelf" style={styles.capacityIcon} />
			</View>
			{product && shelfPrice !== null && (
				<View style={styles.priceCard}>
					<View style={styles.priceHeader}>
						<View>
							<Text style={styles.priceLabel}>Preço de venda</Text>
							<View style={styles.inlineTextRow}>
								<Text style={styles.priceRange}>Faixa:</Text>
								<GameIcon icon="coin" style={styles.inlineIcon} />
								<Text style={styles.priceRange}>{product.minPrice} a</Text>
								<GameIcon icon="coin" style={styles.inlineIcon} />
								<Text style={styles.priceRange}>{product.maxPrice}</Text>
							</View>
						</View>
						<View style={styles.inlineTextRow}>
							<GameIcon icon="coin" style={styles.inlineIcon} />
							<Text style={styles.priceValue}>{shelfPrice}</Text>
						</View>
					</View>
					<View style={styles.priceControls}>
						<Pressable
							disabled={shelfPrice <= product.minPrice}
							onPress={() => adjustPrice(-1)}
							style={[
								styles.priceControlButton,
								shelfPrice <= product.minPrice && styles.disabledPriceControl,
							]}
						>
							<Text style={styles.priceControlText}>−</Text>
						</Pressable>
						<View style={styles.suggestedPrice}>
							<View style={styles.inlineTextRow}>
								<Text style={styles.suggestedPriceText}>Sugestão:</Text>
								<GameIcon icon="coin" style={styles.inlineIcon} />
								<Text style={styles.suggestedPriceText}>
									{product.suggestedPrice}
								</Text>
							</View>
						</View>
						<Pressable
							disabled={shelfPrice >= product.maxPrice}
							onPress={() => adjustPrice(1)}
							style={[
								styles.priceControlButton,
								shelfPrice >= product.maxPrice && styles.disabledPriceControl,
							]}
						>
							<Text style={styles.priceControlText}>+</Text>
						</Pressable>
					</View>
				</View>
			)}
			<GameButton
				disabled={availableQuantity === 0 || isShelfFull}
				fullWidth
				label="Adicionar 1 unidade"
				onPress={restock}
				style={styles.sheetActionButton}
				variant="primary"
			/>
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
						<GameButton
							disabled={!canUnlockUpgrade || coins < nextUpgrade.coinCost}
							icon="coin"
							label={nextUpgrade.coinCost.toLocaleString("pt-BR")}
							onPress={() => upgradeCapacity("coins")}
							size="small"
							style={styles.upgradeActionButton}
							variant="coin"
						/>
						<GameButton
							disabled={
								!canUnlockUpgrade || premiumCurrency < nextUpgrade.diamondCost
							}
							icon="diamond"
							label={nextUpgrade.diamondCost.toString()}
							onPress={() => upgradeCapacity("diamonds")}
							size="small"
							style={styles.upgradeActionButton}
							variant="gem"
						/>
					</View>
					{!canUnlockUpgrade && (
						<Text style={styles.lockedUpgradeText}>
							Faltam {nextUpgrade.playerLevel - marketLevel} nível
							{nextUpgrade.playerLevel - marketLevel === 1 ? "" : "is"}.
						</Text>
					)}
				</View>
			)}
			<View style={styles.shelfManagementActions}>
				<GameButton
					label="Trocar produto"
					onPress={() => removeProduct(true)}
					size="small"
					style={styles.managementActionButton}
					variant="secondary"
				/>
				<GameButton
					label="Retirar produto"
					onPress={() => removeProduct(false)}
					size="small"
					style={styles.managementActionButton}
					variant="danger"
				/>
			</View>
			{feedback && <Text style={styles.feedback}>{feedback}</Text>}
			<GameButton
				fullWidth
				label="Concluir"
				onPress={closeBottomSheet}
				style={styles.sheetActionButton}
				variant="secondary"
			/>
		</View>
	);
}

function ShelfProductPicker({ shelf }: { shelf: StoreShelf }) {
	const { closeBottomSheet } = useBottomSheet();
	const assignProductToShelf = useGameStore(
		(state) => state.assignProductToShelf,
	);
	const inventory = useGameStore((state) => state.inventory);
	const market = useGameStore((state) => state.market);
	const shelfAssignments = useGameStore((state) => state.shelfAssignments);
	const [feedback, setFeedback] = useState<string | null>(null);
	const assignedProductIds = new Set(
		Object.entries(shelfAssignments)
			.filter(([shelfId]) => shelfId !== shelf.id)
			.map(([, productId]) => productId),
	);
	const availableProducts = itemCatalog.filter(
		(product) =>
			market.unlockedProductIds.includes(product.id) &&
			!assignedProductIds.has(product.id),
	);

	function selectProduct(productId: number) {
		if (!assignProductToShelf(shelf.id, productId)) {
			setFeedback("Não foi possível colocar este produto na prateleira.");
			return;
		}

		closeBottomSheet();
	}

	return (
		<View style={styles.sheetContent}>
			<Text style={styles.sheetTitle}>Escolher produto</Text>
			<Text style={styles.sheetDescription}>
				Selecione um produto desbloqueado para ocupar esta vaga.
			</Text>
			<LegendList
				data={availableProducts}
				estimatedItemSize={72}
				keyExtractor={(product) => product.id.toString()}
				renderItem={({ item: product }) => (
					<Pressable
						onPress={() => selectProduct(product.id)}
						style={styles.productOption}
					>
						<ProductImage
							productId={product.id}
							style={styles.productOptionImage}
						/>
						<View style={styles.productOptionDetails}>
							<Text style={styles.productOptionName}>{product.name}</Text>
							<View style={styles.inlineTextRow}>
								<Text style={styles.productOptionMeta}>
									{inventory[product.id] ?? 0} no estoque · venda
								</Text>
								<GameIcon icon="coin" style={styles.inlineIcon} />
								<Text style={styles.productOptionMeta}>
									{product.sellingPrice}
								</Text>
							</View>
						</View>
						<Text style={styles.productOptionAction}>Colocar</Text>
					</Pressable>
				)}
				style={styles.productList}
			/>
			{feedback && <Text style={styles.feedback}>{feedback}</Text>}
			<GameButton
				fullWidth
				label="Cancelar"
				onPress={closeBottomSheet}
				style={styles.sheetActionButton}
				variant="secondary"
			/>
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
		fontFamily: theme.fonts.family.headline,
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
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["blue-700"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	capacityIcon: {
		width: 34,
		height: 34,
	},
	shelfSlotCard: {
		flexDirection: "row",
		alignItems: "center",
		marginTop: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["violet-100"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["violet-50"],
	},
	shelfSlotIcon: {
		width: 40,
		height: 40,
	},
	shelfSlotDetails: {
		marginLeft: theme.gap(1),
	},
	shelfSlotTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	shelfSlotRequirement: {
		marginTop: theme.gap(0.25),
		color: theme.colors["violet-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	sheetActionButton: {
		marginTop: theme.gap(1.25),
	},
	upgradeActionButton: {
		flex: 1,
	},
	managementActionButton: {
		flex: 1,
	},
	priceCard: {
		marginTop: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-50"],
	},
	priceHeader: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	priceLabel: {
		color: theme.colors["neutral-700"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	priceRange: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-600"],
		fontSize: 10,
	},
	priceValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["amber-600"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	inlineTextRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.2),
	},
	inlineIcon: {
		width: 16,
		height: 16,
	},
	priceControls: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1.25),
	},
	priceControlButton: {
		width: theme.gap(4.25),
		height: theme.gap(4.25),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-400"],
	},
	disabledPriceControl: {
		opacity: 0.35,
	},
	priceControlText: {
		color: theme.colors["neutral-0"],
		fontSize: 22,
		fontWeight: "700",
	},
	suggestedPrice: {
		flex: 1,
		alignItems: "center",
		paddingHorizontal: theme.gap(0.75),
	},
	suggestedPriceText: {
		color: theme.colors["amber-600"],
		fontSize: 11,
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
		fontFamily: theme.fonts.family.headline,
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
	lockedUpgradeText: {
		marginTop: theme.gap(0.75),
		color: theme.colors["violet-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	shelfManagementActions: {
		flexDirection: "row",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1.5),
	},
	productList: {
		maxHeight: 360,
		marginTop: theme.gap(1.5),
	},
	productOption: {
		flexDirection: "row",
		alignItems: "center",
		minHeight: theme.gap(7),
		marginBottom: theme.gap(0.75),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	productOptionImage: {
		width: theme.gap(5),
		height: theme.gap(5),
	},
	productOptionDetails: {
		flex: 1,
		marginLeft: theme.gap(1),
	},
	productOptionName: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	productOptionMeta: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 10,
	},
	productOptionAction: {
		color: theme.colors["blue-600"],
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
}));
