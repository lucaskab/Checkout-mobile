import { LegendList } from "@legendapp/list/react-native";
import { SymbolView } from "expo-symbols";
import { useState } from "react";
import { Pressable, ScrollView, useWindowDimensions, View } from "react-native";
import { StyleSheet, useUnistyles } from "react-native-unistyles";
import type { ItemDefinition } from "@/@types/item";
import type { SupplierOrder } from "@/@types/logistics";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import {
	getInventoryCapacity,
	getNextInventoryCapacityUpgrade,
} from "@/data/inventory-capacity";
import { itemCatalog, itemCategories } from "@/data/market-products";
import {
	formatSupplierDeliveryTime,
	getOrderRemainingTime,
	getSupplierOrderStatus,
} from "@/services/logistics";
import { getShelfOrderQuote } from "@/services/shelf-order-quote";
import { useGameStore } from "@/stores/game-store";
import { InventoryCapacitySheet } from "../products/components/inventory-capacity-sheet";
import { SupplierOrderSheet } from "../suppliers/components/supplier-order-sheet";

type StorageScreenProps = {
	presentation?: "inline" | "page";
};

type StorageInlineView =
	| "storage"
	| "product"
	| "expansion"
	| "capacity"
	| "order";

type StorageProduct = {
	product: ItemDefinition;
	capacity: number;
	quantity: number;
	supplierWaitTime: string;
	incomingOrder?: SupplierOrder;
};

const allCategories = { id: "todos", label: "Todos" };
const bottomSheetChromeHeight = 56;
const emptyShelfSlotIds = ["empty-1", "empty-2", "empty-3"];

export function getStorageSheetDetent(windowHeight: number) {
	return Math.min(windowHeight * 0.86, 800);
}

export function StorageScreen({ presentation = "page" }: StorageScreenProps) {
	const { closeBottomSheet, openBottomSheet } = useBottomSheet();
	const { height, width } = useWindowDimensions();
	const sheetContentHeight =
		getStorageSheetDetent(height) - bottomSheetChromeHeight;
	const isInline = presentation === "inline";
	const [inlineView, setInlineView] = useState<StorageInlineView>("storage");
	const [activeProduct, setActiveProduct] = useState<ItemDefinition | null>(
		null,
	);
	const [activeCategory, setActiveCategory] = useState("todos");
	const state = useGameStore();
	const unlockedProducts = itemCatalog.filter((product) =>
		state.market.unlockedProductIds.includes(product.id),
	);
	const products: StorageProduct[] = unlockedProducts.map((product) => {
		const quote = getShelfOrderQuote(state, product.id, 1);

		return {
			product,
			capacity: getInventoryCapacity(
				product,
				state.inventoryCapacityLevels[product.id],
			),
			quantity: state.inventory[product.id] ?? 0,
			supplierWaitTime: quote
				? `~${formatSupplierDeliveryTime(quote.duration)}`
				: product.supplierTime,
			incomingOrder: state.logistics.orders.find(
				(order) =>
					order.productId === product.id &&
					getSupplierOrderStatus(order) !== "entregue",
			),
		};
	});
	const availableCategories = itemCategories.filter((category) =>
		unlockedProducts.some((product) => product.category === category.id),
	);
	const categories = [allCategories, ...availableCategories];
	const visibleProducts = products.filter(
		({ product }) =>
			activeCategory === "todos" || product.category === activeCategory,
	);
	const shelfColumns = width < 380 ? 3 : 4;
	const shelfRows: StorageProduct[][] = [];
	for (let index = 0; index < visibleProducts.length; index += shelfColumns) {
		shelfRows.push(visibleProducts.slice(index, index + shelfColumns));
	}
	const totalQuantity = products.reduce(
		(total, item) => total + item.quantity,
		0,
	);
	const totalCapacity = products.reduce(
		(total, item) => total + item.capacity,
		0,
	);
	const fillPercent = Math.min(
		100,
		Math.round((totalQuantity / Math.max(totalCapacity, 1)) * 100),
	);

	function openCapacityUpgrade(product: ItemDefinition) {
		if (isInline) {
			setActiveProduct(product);
			setInlineView("capacity");
			return;
		}

		openBottomSheet(<InventoryCapacitySheet product={product} />);
	}

	function openStorageExpansion() {
		if (isInline) {
			setInlineView("expansion");
			return;
		}

		openBottomSheet(
			<StorageExpansionSheet
				contentHeight={sheetContentHeight}
				onBack={closeBottomSheet}
				products={unlockedProducts}
			/>,
		);
	}

	function openSupplierOrder(product: ItemDefinition) {
		if (isInline) {
			setActiveProduct(product);
			setInlineView("order");
			return;
		}

		openBottomSheet(
			<SupplierOrderSheet onBack={closeBottomSheet} productId={product.id} />,
		);
	}

	function openProductDetail(item: StorageProduct) {
		if (isInline) {
			setActiveProduct(item.product);
			setInlineView("product");
			return;
		}

		openBottomSheet(
			<View style={styles.productDetailSheet}>
				<StorageShelf
					item={item}
					onExpand={() => openCapacityUpgrade(item.product)}
					onOrder={() => openSupplierOrder(item.product)}
				/>
				<GameButton
					fullWidth
					label="Voltar ao depósito"
					onPress={closeBottomSheet}
					variant="secondary"
				/>
			</View>,
		);
	}

	if (isInline && activeProduct && inlineView === "product") {
		const item = products.find(
			({ product }) => product.id === activeProduct.id,
		);
		if (item) {
			return (
				<ScrollView contentContainerStyle={styles.productDetailSheet}>
					<StorageShelf
						item={item}
						onExpand={() => openCapacityUpgrade(item.product)}
						onOrder={() => openSupplierOrder(item.product)}
					/>
					<GameButton
						fullWidth
						label="Voltar ao depósito"
						onPress={() => setInlineView("storage")}
						variant="secondary"
					/>
				</ScrollView>
			);
		}
	}

	if (isInline && inlineView === "expansion") {
		return (
			<StorageExpansionSheet
				contentHeight={sheetContentHeight}
				onBack={() => setInlineView("storage")}
				onSelectProduct={(product) => {
					setActiveProduct(product);
					setInlineView("capacity");
				}}
				products={unlockedProducts}
			/>
		);
	}

	if (isInline && activeProduct && inlineView === "capacity") {
		return (
			<View style={styles.inlineDetailScreen}>
				<GameButton
					label="Voltar ao depósito"
					onPress={() => setInlineView("storage")}
					variant="secondary"
				/>
				<ScrollView contentContainerStyle={styles.inlineDetailContent}>
					<InventoryCapacitySheet
						onClose={() => setInlineView("storage")}
						product={activeProduct}
					/>
				</ScrollView>
			</View>
		);
	}

	if (isInline && activeProduct && inlineView === "order") {
		return (
			<View style={styles.inlineOrderScreen}>
				<ScrollView contentContainerStyle={styles.inlineDetailContent}>
					<SupplierOrderSheet
						onBack={() => setInlineView("storage")}
						onClose={() => setInlineView("storage")}
						productId={activeProduct.id}
					/>
				</ScrollView>
			</View>
		);
	}

	return (
		<View style={styles.screen}>
			<LegendList
				contentContainerStyle={styles.listContent}
				data={shelfRows}
				extraData={{
					inventory: state.inventory,
					orders: state.logistics.orders,
				}}
				keyExtractor={(row) => row[0].product.id.toString()}
				ListEmptyComponent={
					<Text style={styles.emptyText}>Nenhum produto nesta categoria.</Text>
				}
				ListHeaderComponent={
					<View style={styles.listHeader}>
						<View style={styles.heroCard}>
							<View style={styles.heroTopRow}>
								<View style={styles.heroIconWrap}>
									<GameIcon icon="warehouse" style={styles.heroIcon} />
								</View>
								<View style={styles.heroCopy}>
									<Text style={styles.eyebrow}>CHECKOUT MARKET</Text>
									<Text style={styles.heroTitle}>Meu depósito</Text>
									<Text style={styles.heroDescription}>
										Produtos, quantidades e entregas em um só lugar.
									</Text>
								</View>
							</View>
							<View style={styles.capacityHeader}>
								<Text style={styles.capacityLabel}>Espaço ocupado</Text>
								<Text style={styles.capacityValue}>
									{totalQuantity.toLocaleString("pt-BR")} /{" "}
									{totalCapacity.toLocaleString("pt-BR")} unid.
								</Text>
							</View>
							<View style={styles.progressTrack}>
								<View
									style={[styles.progressFill, { width: `${fillPercent}%` }]}
								/>
							</View>
							<View style={styles.heroFooter}>
								<View style={styles.heroStat}>
									<GameIcon icon="package" style={styles.statIcon} />
									<Text style={styles.statText}>
										{products.length} produtos disponíveis
									</Text>
								</View>
								<GameButton
									icon="warehouse"
									label="Expandir espaço"
									onPress={openStorageExpansion}
									size="small"
									variant="coin"
								/>
							</View>
						</View>
						<View style={styles.sectionHeading}>
							<View>
								<Text style={styles.sectionTitle}>Prateleiras do depósito</Text>
								<Text style={styles.sectionDescription}>
									Acompanhe o estoque e o prazo de cada fornecedor.
								</Text>
							</View>
							<GameIcon icon="shelf" style={styles.sectionIcon} />
						</View>
						<LegendList
							contentContainerStyle={styles.categoryList}
							data={categories}
							horizontal
							keyExtractor={(item) => item.id}
							renderItem={({ item }) => (
								<Pressable
									accessibilityRole="button"
									accessibilityState={{ selected: activeCategory === item.id }}
									onPress={() => setActiveCategory(item.id)}
									style={[
										styles.categoryChip,
										activeCategory === item.id && styles.activeCategoryChip,
									]}
								>
									<Text
										style={[
											styles.categoryText,
											activeCategory === item.id && styles.activeCategoryText,
										]}
									>
										{item.label}
									</Text>
								</Pressable>
							)}
							showsHorizontalScrollIndicator={false}
						/>
					</View>
				}
				renderItem={({ item }) => (
					<StorageShelfRow
						columns={shelfColumns}
						items={item}
						onSelect={openProductDetail}
					/>
				)}
				showsVerticalScrollIndicator={false}
				style={styles.productList}
			/>
		</View>
	);
}

function StorageShelfRow({
	columns,
	items,
	onSelect,
}: {
	columns: number;
	items: StorageProduct[];
	onSelect: (item: StorageProduct) => void;
}) {
	return (
		<View style={styles.shelfUnit}>
			<View style={styles.shelfSlots}>
				{items.map((item) => {
					const { product, quantity, capacity, incomingOrder } = item;
					const deliveryTime = incomingOrder
						? getOrderRemainingTime(incomingOrder)
						: item.supplierWaitTime;
					const status = incomingOrder
						? `Chega em ${deliveryTime}`
						: product.acquisition === "supplier"
							? `Fornecedor · ${deliveryTime}`
							: "Produção própria";

					return (
						<Pressable
							accessibilityRole="button"
							accessibilityLabel={`${product.name}, ${quantity} de ${capacity} unidades no depósito. ${status}. Ver detalhes`}
							key={product.id}
							onPress={() => onSelect(item)}
							style={({ pressed }) => [
								styles.shelfSlot,
								pressed && styles.pressedButton,
							]}
						>
							<View
								style={[
									styles.shelfCrate,
									quantity === 0 && styles.emptyShelfCrate,
								]}
							>
								<ProductImage
									productId={product.id}
									style={styles.shelfProductImage}
								/>
								<View style={styles.shelfStockBadge}>
									<Text style={styles.shelfStockText}>
										{quantity}/{capacity}
									</Text>
								</View>
							</View>
							<Text numberOfLines={1} style={styles.shelfSlotName}>
								{product.name}
							</Text>
							<View style={styles.shelfSlotStatus}>
								<GameIcon
									icon={
										product.acquisition === "supplier"
											? "deliveryTruck"
											: "package"
									}
									style={styles.shelfStatusIcon}
								/>
								<Text numberOfLines={1} style={styles.shelfStatusText}>
									{incomingOrder
										? `Chega ${deliveryTime}`
										: product.acquisition === "supplier"
											? deliveryTime
											: "Produção"}
								</Text>
							</View>
						</Pressable>
					);
				})}
				{emptyShelfSlotIds.slice(0, columns - items.length).map((slotId) => (
					<View key={slotId} style={styles.shelfSlot} />
				))}
			</View>
			<View style={styles.shelfPlank}>
				<View style={styles.shelfPlankEdge} />
			</View>
		</View>
	);
}

function StorageShelf({
	item,
	onExpand,
	onOrder,
}: {
	item: StorageProduct;
	onExpand: () => void;
	onOrder: () => void;
}) {
	const { product, quantity, capacity, incomingOrder, supplierWaitTime } = item;
	const fillPercent = Math.min(
		100,
		Math.round((quantity / Math.max(capacity, 1)) * 100),
	);
	const category = itemCategories.find(
		(entry) => entry.id === product.category,
	);
	const deliveryTime = incomingOrder
		? getOrderRemainingTime(incomingOrder)
		: supplierWaitTime;

	return (
		<View style={styles.shelfCard}>
			<View style={styles.shelfRow}>
				<View style={styles.productVisual}>
					<ProductImage productId={product.id} style={styles.productImage} />
				</View>
				<View style={styles.productInfo}>
					<View style={styles.productTitleRow}>
						<View style={styles.productNameWrap}>
							<Text numberOfLines={1} style={styles.productName}>
								{product.name}
							</Text>
							<Text style={styles.productCategory}>
								{category?.label ?? product.category}
							</Text>
						</View>
						<View style={styles.quantityBadge}>
							<Text style={styles.quantityValue}>{quantity}</Text>
							<Text style={styles.quantityUnit}>unid.</Text>
						</View>
					</View>
					<View style={styles.shelfProgressTrack}>
						<View
							style={[styles.shelfProgressFill, { width: `${fillPercent}%` }]}
						/>
					</View>
					<View style={styles.capacityLine}>
						<Text style={styles.capacityLineText}>
							{quantity} / {capacity} no depósito
						</Text>
						{product.acquisition === "supplier" ? (
							<View style={styles.deliveryLine}>
								<GameIcon icon="deliveryTruck" style={styles.deliveryIcon} />
								<Text style={styles.deliveryText}>
									{incomingOrder
										? `Chega em ${deliveryTime}`
										: `Fornecedor · ${deliveryTime}`}
								</Text>
							</View>
						) : (
							<Text style={styles.productionLabel}>Produção própria</Text>
						)}
					</View>
				</View>
			</View>
			<View style={styles.shelfBoard} />
			<View style={styles.shelfActions}>
				{product.acquisition === "supplier" && (
					<Pressable
						accessibilityRole="button"
						accessibilityLabel={`Pedir ${product.name} ao fornecedor`}
						onPress={onOrder}
						style={({ pressed }) => [
							styles.orderButton,
							pressed && styles.pressedButton,
						]}
					>
						<GameIcon icon="deliveryTruck" style={styles.actionIcon} />
						<Text style={styles.orderButtonText}>Pedir ao fornecedor</Text>
					</Pressable>
				)}
				<Pressable
					accessibilityRole="button"
					accessibilityLabel={`Expandir espaço para ${product.name}`}
					onPress={onExpand}
					style={({ pressed }) => [
						styles.expandButton,
						pressed && styles.pressedButton,
					]}
				>
					<GameIcon icon="warehouse" style={styles.actionIcon} />
					<Text style={styles.expandButtonText}>Expandir</Text>
				</Pressable>
			</View>
		</View>
	);
}

function StorageExpansionSheet({
	contentHeight,
	onBack,
	onSelectProduct,
	products,
}: {
	contentHeight: number;
	onBack?: () => void;
	onSelectProduct?: (product: ItemDefinition) => void;
	products: ItemDefinition[];
}) {
	const { closeBottomSheet, openBottomSheet } = useBottomSheet();
	const { theme } = useUnistyles();
	const state = useGameStore();
	const handleBack = onBack ?? closeBottomSheet;

	return (
		<View style={[styles.expansionSheet, { height: contentHeight }]}>
			<View style={styles.expansionHeader}>
				<Pressable
					accessibilityRole="button"
					accessibilityLabel="Voltar ao depósito"
					onPress={handleBack}
					style={styles.expansionBackButton}
				>
					<SymbolView
						name={{
							ios: "chevron.left",
							android: "chevron_left",
							web: "chevron_left",
						}}
						size={18}
						tintColor={theme.colors["neutral-700"]}
					/>
				</Pressable>
				<View style={styles.expansionCopy}>
					<Text style={styles.eyebrow}>MAIS ESPAÇO</Text>
					<Text style={styles.expansionTitle}>Expandir depósito</Text>
					<Text style={styles.expansionDescription}>
						Escolha uma prateleira para aumentar a capacidade daquele produto.
					</Text>
				</View>
			</View>
			<LegendList
				contentContainerStyle={styles.expansionList}
				data={products}
				extraData={state.inventoryCapacityLevels}
				keyExtractor={(product) => product.id.toString()}
				renderItem={({ item }) => {
					const level = state.inventoryCapacityLevels[item.id] ?? 0;
					const upgrade = getNextInventoryCapacityUpgrade(level);
					const capacity = getInventoryCapacity(item, level);
					const nextCapacity = upgrade
						? getInventoryCapacity(item, level + 1)
						: capacity;
					const isLocked = upgrade && state.market.level < upgrade.playerLevel;

					return (
						<Pressable
							accessibilityRole="button"
							accessibilityLabel={
								upgrade
									? `Expandir ${item.name} de ${capacity} para ${nextCapacity} unidades`
									: `${item.name} já está na capacidade máxima`
							}
							disabled={!upgrade}
							onPress={() => {
								if (onSelectProduct) {
									onSelectProduct(item);
									return;
								}

								openBottomSheet(<InventoryCapacitySheet product={item} />);
							}}
							style={[styles.expansionProduct, !upgrade && styles.maxedProduct]}
						>
							<ProductImage
								productId={item.id}
								style={styles.expansionProductImage}
							/>
							<View style={styles.expansionProductInfo}>
								<Text numberOfLines={1} style={styles.expansionProductName}>
									{item.name}
								</Text>
								<Text style={styles.expansionProductCapacity}>
									{upgrade
										? `${capacity} → ${nextCapacity} unid.`
										: `${capacity} unid. · capacidade máxima`}
								</Text>
							</View>
							{upgrade ? (
								<View style={styles.expansionCost}>
									{isLocked ? (
										<Text style={styles.expansionCostText}>
											Nv. {upgrade.playerLevel}
										</Text>
									) : (
										<>
											<GameIcon icon="coin" style={styles.expansionCoinIcon} />
											<Text style={styles.expansionCostText}>
												{upgrade.coinCost.toLocaleString("pt-BR")}
											</Text>
										</>
									)}
								</View>
							) : (
								<GameIcon icon="success" style={styles.maxedIcon} />
							)}
						</Pressable>
					);
				}}
				showsVerticalScrollIndicator={false}
				style={styles.expansionProductList}
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	screen: {
		flex: 1,
		backgroundColor: theme.colors["neutral-50"],
	},
	inlineDetailScreen: {
		flex: 1,
		gap: theme.gap(1),
		paddingHorizontal: theme.gap(1.5),
		paddingBottom: theme.gap(1),
	},
	inlineOrderScreen: {
		flex: 1,
		paddingBottom: theme.gap(1),
	},
	inlineDetailContent: {
		gap: theme.gap(1),
		paddingBottom: theme.gap(1),
	},
	productDetailSheet: {
		gap: theme.gap(1.25),
		paddingHorizontal: theme.gap(1.5),
		paddingVertical: theme.gap(1),
	},
	productList: {
		flex: 1,
	},
	listContent: {
		paddingHorizontal: theme.gap(1.75),
		paddingBottom: theme.gap(2),
		gap: theme.gap(1.5),
	},
	listHeader: {
		gap: theme.gap(1.75),
	},
	heroCard: {
		padding: theme.gap(2),
		borderWidth: 1.5,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["blue-50"],
	},
	heroTopRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
	},
	heroIconWrap: {
		width: theme.gap(7),
		height: theme.gap(7),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	heroIcon: { width: theme.gap(5.5), height: theme.gap(5.5) },
	heroCopy: { flex: 1 },
	eyebrow: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 0.8,
	},
	heroTitle: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.large + 2,
		fontWeight: "700",
	},
	heroDescription: {
		marginTop: theme.gap(0.375),
		color: theme.colors["neutral-600"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	capacityHeader: {
		flexDirection: "row",
		justifyContent: "space-between",
		marginTop: theme.gap(1.75),
	},
	capacityLabel: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	capacityValue: {
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
		fontWeight: "700",
	},
	progressTrack: {
		height: theme.gap(0.875),
		marginTop: theme.gap(0.75),
		overflow: "hidden",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-100"],
	},
	progressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["green-500"],
	},
	heroFooter: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(1),
		marginTop: theme.gap(1.75),
	},
	heroStat: { flexDirection: "row", alignItems: "center", gap: theme.gap(0.5) },
	statIcon: { width: theme.gap(2.5), height: theme.gap(2.5) },
	statText: {
		color: theme.colors["neutral-700"],
		fontSize: 10,
		fontWeight: "700",
	},
	sectionHeading: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	sectionTitle: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.medium + 2,
		fontWeight: "700",
	},
	sectionDescription: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 10,
	},
	sectionIcon: { width: theme.gap(4), height: theme.gap(4) },
	categoryList: { gap: theme.gap(0.75), paddingRight: theme.gap(1) },
	categoryChip: {
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	activeCategoryChip: {
		borderColor: theme.colors["blue-500"],
		backgroundColor: theme.colors["blue-500"],
	},
	categoryText: {
		color: theme.colors["neutral-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
	},
	activeCategoryText: { color: theme.colors["neutral-0"] },
	shelfUnit: {
		paddingHorizontal: theme.gap(0.75),
		paddingTop: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	shelfSlots: {
		flexDirection: "row",
		alignItems: "flex-start",
	},
	shelfSlot: {
		flex: 1,
		minWidth: 0,
		alignItems: "center",
		paddingHorizontal: theme.gap(0.375),
	},
	shelfCrate: {
		width: "100%",
		height: theme.gap(9),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 2,
		borderColor: theme.colors.gameShelfBorder,
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors.gameShelf,
	},
	emptyShelfCrate: {
		borderColor: theme.colors["red-400"],
		backgroundColor: theme.colors["red-50"],
	},
	shelfProductImage: {
		width: theme.gap(5.75),
		height: theme.gap(5.75),
	},
	shelfStockBadge: {
		position: "absolute",
		top: theme.gap(0.375),
		right: theme.gap(0.375),
		paddingHorizontal: theme.gap(0.375),
		borderRadius: theme.gap(0.625),
		backgroundColor: theme.colors["neutral-700"],
	},
	shelfStockText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 8,
	},
	shelfSlotName: {
		width: "100%",
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 10,
		textAlign: "center",
	},
	shelfSlotStatus: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.125),
		width: "100%",
		marginTop: theme.gap(0.25),
	},
	shelfStatusIcon: {
		width: theme.gap(1.5),
		height: theme.gap(1.5),
	},
	shelfStatusText: {
		minWidth: 0,
		color: theme.colors["neutral-600"],
		fontSize: 9,
		fontWeight: "700",
	},
	shelfPlank: {
		height: theme.gap(0.75),
		marginTop: theme.gap(0.625),
		borderTopLeftRadius: theme.gap(0.5),
		borderTopRightRadius: theme.gap(0.5),
		backgroundColor: theme.colors["neutral-300"],
	},
	shelfPlankEdge: {
		height: theme.gap(0.375),
		marginTop: theme.gap(0.375),
		borderBottomLeftRadius: theme.gap(0.5),
		borderBottomRightRadius: theme.gap(0.5),
		backgroundColor: theme.colors["neutral-400"],
	},
	shelfCard: {
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 2 },
		shadowOpacity: 0.06,
		shadowRadius: 5,
		elevation: 1,
	},
	shelfRow: { flexDirection: "row", alignItems: "center", gap: theme.gap(1) },
	productVisual: {
		width: theme.gap(7.5),
		height: theme.gap(7.5),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 1,
		borderColor: theme.colors["amber-100"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["amber-50"],
	},
	productImage: { width: theme.gap(6.5), height: theme.gap(6.5) },
	productInfo: { flex: 1, minWidth: 0 },
	productTitleRow: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(0.5),
	},
	productNameWrap: { flex: 1, minWidth: 0 },
	productName: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	productCategory: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 9,
	},
	quantityBadge: {
		alignItems: "center",
		minWidth: theme.gap(4.75),
		paddingHorizontal: theme.gap(0.625),
		paddingVertical: theme.gap(0.375),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["green-50"],
	},
	quantityValue: {
		color: theme.colors["green-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.small,
		fontWeight: "800",
	},
	quantityUnit: {
		color: theme.colors["green-600"],
		fontSize: 8,
		fontWeight: "700",
	},
	shelfProgressTrack: {
		height: theme.gap(0.625),
		marginTop: theme.gap(0.75),
		overflow: "hidden",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	shelfProgressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["green-500"],
	},
	capacityLine: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(0.375),
		marginTop: theme.gap(0.5),
	},
	capacityLineText: { color: theme.colors["neutral-600"], fontSize: 9 },
	deliveryLine: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	deliveryIcon: { width: theme.gap(1.75), height: theme.gap(1.75) },
	deliveryText: {
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "700",
	},
	productionLabel: {
		color: theme.colors["violet-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "700",
	},
	shelfBoard: {
		height: theme.gap(0.75),
		marginTop: theme.gap(0.875),
		borderRadius: theme.gap(0.375),
		borderBottomWidth: 3,
		borderBottomColor: theme.colors["amber-500"],
		backgroundColor: theme.colors["amber-200"],
	},
	shelfActions: {
		flexDirection: "row",
		gap: theme.gap(0.625),
		marginTop: theme.gap(0.875),
	},
	orderButton: {
		flex: 1,
		minHeight: theme.gap(4),
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.5),
		paddingHorizontal: theme.gap(0.75),
		borderWidth: 1.5,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["blue-50"],
	},
	orderButtonText: {
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
	},
	expandButton: {
		minHeight: theme.gap(4),
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.375),
		paddingHorizontal: theme.gap(1),
		borderWidth: 1.5,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["amber-50"],
	},
	expandButtonText: {
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
	},
	actionIcon: { width: theme.gap(2.25), height: theme.gap(2.25) },
	pressedButton: { opacity: 0.75, transform: [{ translateY: 1 }] },
	emptyText: {
		paddingVertical: theme.gap(3),
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		textAlign: "center",
	},
	expansionSheet: {
		paddingHorizontal: theme.gap(2),
		paddingBottom: theme.gap(1),
		gap: theme.gap(1),
	},
	expansionHeader: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
	},
	expansionBackButton: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["amber-50"],
	},
	expansionCopy: { flex: 1 },
	expansionTitle: {
		marginTop: theme.gap(0.125),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.medium + 2,
		fontWeight: "700",
	},
	expansionDescription: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-600"],
		fontSize: 10,
		lineHeight: theme.gap(1.5),
	},
	expansionProductList: { flex: 1 },
	expansionList: { gap: theme.gap(0.625), paddingVertical: theme.gap(0.5) },
	expansionProduct: {
		minHeight: theme.gap(7),
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.875),
		padding: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	maxedProduct: { opacity: 0.72 },
	expansionProductImage: { width: theme.gap(5), height: theme.gap(5) },
	expansionProductInfo: { flex: 1, minWidth: 0 },
	expansionProductName: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	expansionProductCapacity: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 9,
	},
	expansionCost: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["amber-50"],
	},
	expansionCoinIcon: { width: theme.gap(2), height: theme.gap(2) },
	expansionCostText: {
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 9,
		fontWeight: "700",
	},
	maxedIcon: { width: theme.gap(2.5), height: theme.gap(2.5) },
}));
