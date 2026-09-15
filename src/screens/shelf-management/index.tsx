import { LegendList } from "@legendapp/list/react-native";
import { useEffect, useState } from "react";
import { TextInput, useWindowDimensions, View } from "react-native";
import Animated, { FadeInDown } from "react-native-reanimated";
import { StyleSheet } from "react-native-unistyles";
import type {
	ShelfManagementPage,
	ShelfManagementProps,
} from "@/@types/shelf-management";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { itemCatalog, shelves } from "@/data/market-products";
import {
	getNextShelfCapacityUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import { getShelfSlotIds, isShelfSlotUnlocked } from "@/data/shelf-slots";
import { useGameStore } from "@/stores/game-store";
import { SupplierOrderSheet } from "../suppliers/components/supplier-order-sheet";

export function ShelfManagementScreen({
	shelfId,
	onClose,
}: ShelfManagementProps) {
	const [page, setPage] = useState<ShelfManagementPage>({ kind: "slots" });
	const [notice, setNotice] = useState("");
	const [search, setSearch] = useState("");
	const [state, setState] = useState(() => useGameStore.getState());
	const { height } = useWindowDimensions();

	useEffect(() => useGameStore.subscribe(setState), []);

	const slotIds = getShelfSlotIds(shelfId);
	const capacity = getShelfCapacity(state.shelfUpgradeLevels[shelfId]);
	const upgrade = getNextShelfCapacityUpgrade(
		state.shelfUpgradeLevels[shelfId],
	);
	const occupied = slotIds.filter((id) => state.shelfAssignments[id]).length;
	const unlocked = isShelfSlotUnlocked(shelfId, state.unlockedShelfSlots);
	const products = itemCatalog.filter(
		(product) =>
			state.market.unlockedProductIds.includes(product.id) &&
			product.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()) &&
			!Object.entries(state.shelfAssignments).some(
				([id, assigned]) =>
					assigned === product.id &&
					(page.kind !== "picker" || id !== page.slotId),
			),
	);
	function back() {
		setPage({ kind: "slots" });
		setNotice("");
		setSearch("");
	}
	function picker(slotId: string) {
		setPage({ kind: "picker", slotId });
		setNotice("");
	}
	return (
		<Animated.View
			entering={FadeInDown.duration(220)}
			style={[styles.root, { height: Math.min(height * 0.82, 790) }]}
		>
			<View style={styles.header}>
				<View style={styles.headingRow}>
					<GameIcon
						icon={page.kind === "order" ? "deliveryTruck" : "shelf"}
						style={styles.headerIcon}
					/>
					<View style={styles.flex}>
						<Text style={styles.eyebrow}>SEU MERCADO</Text>
						<Text style={styles.title}>
							{page.kind === "picker"
								? "Escolher produto"
								: page.kind === "order"
									? "Pedir estoque"
									: (shelves.find((shelf) => shelf.id === shelfId)?.name ??
										"Prateleira")}
						</Text>
					</View>
					<GameButton
						label={page.kind === "slots" ? "Fechar" : "Voltar"}
						size="small"
						variant="secondary"
						onPress={page.kind === "slots" ? onClose : back}
					/>
				</View>
				<Text style={styles.subtitle}>
					{page.kind === "slots"
						? `${occupied}/4 espaços ocupados · ${capacity} unidades por produto`
						: page.kind === "picker"
							? "Escolha um produto diferente para este espaço."
							: "Do fornecedor direto para o seu depósito."}
				</Text>
			</View>
			<View style={styles.awning}>
				{[0, 1, 2, 3, 4, 5, 6, 7].map((stripe) => (
					<View
						key={stripe}
						style={[styles.stripe, stripe % 2 === 1 && styles.stripeWarm]}
					/>
				))}
			</View>
			{!!notice && (
				<Text accessibilityLiveRegion="polite" style={styles.notice}>
					{notice}
				</Text>
			)}
			{!unlocked ? (
				<Text style={styles.notice}>
					Desbloqueie esta prateleira no painel do mercado.
				</Text>
			) : page.kind === "order" ? (
				<SupplierOrderSheet
					productId={page.productId}
					onOrdered={(message) => {
						back();
						setNotice(message);
					}}
				/>
			) : page.kind === "picker" ? (
				<>
					<TextInput
						accessibilityLabel="Buscar produto"
						placeholder="Buscar produto…"
						value={search}
						onChangeText={setSearch}
						style={styles.search}
					/>
					<LegendList
						recycleItems={false}
						data={products}
						keyExtractor={(product) => String(product.id)}
						contentContainerStyle={styles.list}
						ListEmptyComponent={
							<Text style={styles.subtitle}>
								Nenhum produto disponível. Novos produtos são liberados com seu
								progresso.
							</Text>
						}
						renderItem={({ item }) => (
							<View style={styles.card}>
								<View style={styles.headingRow}>
									<ProductImage
										productId={item.id}
										style={styles.productImage}
									/>
									<View style={styles.flex}>
										<Text style={styles.productName}>{item.name}</Text>
										<Text style={styles.subtitle}>
											Depósito: {state.inventory[item.id] ?? 0} unid.
										</Text>
									</View>
								</View>
								<GameButton
									label={
										state.shelfAssignments[page.slotId]
											? "Substituir produto"
											: "Adicionar produto"
									}
									fullWidth
									onPress={() => {
										if (
											state.assignProductToShelf(page.slotId, item.id, true)
										) {
											back();
											setNotice(
												`${item.name} adicionado. Reabasteça para começar a vender.`,
											);
										} else
											setNotice(
												"Não foi possível trocar. Confira o espaço no depósito para devolver o produto atual.",
											);
									}}
								/>
							</View>
						)}
					/>
				</>
			) : (
				<LegendList
					recycleItems={false}
					data={slotIds}
					keyExtractor={(id) => id}
					contentContainerStyle={styles.list}
					ListFooterComponent={
						upgrade ? (
							<View style={styles.card}>
								<Text style={styles.productName}>
									Mais produtos para vender
								</Text>
								<Text style={styles.subtitle}>
									Aumente cada espaço para {upgrade.capacity} unidades · Nível{" "}
									{upgrade.playerLevel}
								</Text>
								<GameButton
									label={`Ampliar · ${upgrade.coinCost} moedas`}
									variant="coin"
									fullWidth
									disabled={
										state.market.level < upgrade.playerLevel ||
										state.coins < upgrade.coinCost
									}
									onPress={() =>
										setNotice(
											state.upgradeShelfCapacity(shelfId, "coins")
												? "Capacidade ampliada nos quatro espaços!"
												: "Confira seu nível e saldo.",
										)
									}
								/>
								<GameButton
									label={`Ampliar · ${upgrade.diamondCost} diamantes`}
									variant="gem"
									fullWidth
									disabled={
										state.market.level < upgrade.playerLevel ||
										state.logistics.premiumCurrency < upgrade.diamondCost
									}
									onPress={() =>
										setNotice(
											state.upgradeShelfCapacity(shelfId, "diamonds")
												? "Capacidade ampliada nos quatro espaços!"
												: "Confira seu nível e saldo.",
										)
									}
								/>
							</View>
						) : null
					}
					renderItem={({ item: slotId, index }) => {
						const product = itemCatalog.find(
							(item) => item.id === state.shelfAssignments[slotId],
						);
						const stock = state.shelfStock[slotId] ?? 0;
						const price =
							state.shelfPrices[slotId] ?? product?.sellingPrice ?? 0;
						const reserve = product ? (state.inventory[product.id] ?? 0) : 0;
						return (
							<View style={styles.card}>
								<View style={styles.headingRow}>
									<View style={styles.productWell}>
										{product ? (
											<ProductImage
												productId={product.id}
												style={styles.productImage}
											/>
										) : (
											<GameIcon icon="basket" style={styles.productImage} />
										)}
									</View>
									<View style={styles.flex}>
										<Text style={styles.eyebrow}>ESPAÇO {index + 1}</Text>
										<Text style={styles.productName}>
											{product?.name ?? "Que tal algo novo?"}
										</Text>
										<Text style={styles.subtitle}>
											{product
												? `Venda: ${state.shelfPrices[slotId] ?? product.sellingPrice} moedas`
												: "Um espaço esperando seu próximo sucesso."}
										</Text>
									</View>
								</View>
								{product ? (
									<>
										<View style={styles.headingRow}>
											<GameButton
												label="−"
												size="small"
												variant="secondary"
												accessibilityLabel={`Reduzir preço de ${product.name}`}
												disabled={price <= product.minPrice}
												onPress={() => state.setShelfPrice(slotId, price - 1)}
											/>
											<Text style={[styles.subtitle, styles.quantity]}>
												Preço de venda: {price}
											</Text>
											<GameButton
												label="+"
												size="small"
												variant="secondary"
												accessibilityLabel={`Aumentar preço de ${product.name}`}
												disabled={price >= product.maxPrice}
												onPress={() => state.setShelfPrice(slotId, price + 1)}
											/>
										</View>
										<View style={styles.metrics}>
											<View style={styles.metric}>
												<Text style={styles.number}>
													{stock} / {capacity}
												</Text>
												<Text style={styles.subtitle}>Na prateleira</Text>
											</View>
											<View style={styles.metric}>
												<Text style={styles.number}>{reserve}</Text>
												<Text style={styles.subtitle}>No depósito</Text>
											</View>
										</View>
										<View
											accessibilityLabel={`${stock} de ${capacity} unidades`}
											style={styles.track}
										>
											<View
												style={[
													styles.fill,
													{
														width: `${Math.min(100, (stock / capacity) * 100)}%`,
													},
												]}
											/>
										</View>
										<GameButton
											label={
												reserve === 0
													? "Pedir mais estoque"
													: stock >= capacity
														? "Prateleira cheia"
														: `Reabastecer +${Math.min(reserve, capacity - stock)}`
											}
											icon={reserve === 0 ? "deliveryTruck" : "basket"}
											variant={reserve === 0 ? "coin" : "success"}
											disabled={reserve > 0 && stock >= capacity}
											fullWidth
											onPress={() => {
												if (reserve === 0) {
													setNotice("");
													setPage({ kind: "order", productId: product.id });
												} else
													setNotice(
														state.restockShelf({
															shelfId: slotId,
															productId: product.id,
															amount: Math.min(reserve, capacity - stock),
														})
															? "Tudo pronto para vender!"
															: "O estoque mudou. Confira as quantidades e tente novamente.",
													);
											}}
										/>
										<View style={styles.actions}>
											<View style={styles.flex}>
												<GameButton
													label="Substituir"
													variant="secondary"
													size="small"
													fullWidth
													onPress={() => picker(slotId)}
												/>
											</View>
											<View style={styles.flex}>
												<GameButton
													label="Remover"
													variant="danger"
													size="small"
													fullWidth
													onPress={() =>
														setNotice(
															state.clearShelf(slotId)
																? "Produto devolvido ao depósito."
																: "Libere espaço no depósito para devolver este produto.",
														)
													}
												/>
											</View>
										</View>
									</>
								) : (
									<GameButton
										label="Adicionar produto"
										fullWidth
										onPress={() => picker(slotId)}
									/>
								)}
							</View>
						);
					}}
				/>
			)}
		</Animated.View>
	);
}

const styles = StyleSheet.create((theme) => ({
	root: {
		backgroundColor: theme.colors.gameBackground,
		borderRadius: 28,
		overflow: "hidden",
		width: "100%",
	},
	header: { padding: 20, gap: 10 },
	headingRow: { flexDirection: "row", alignItems: "center", gap: 12 },
	flex: { flex: 1 },
	headerIcon: { width: 40, height: 40 },
	title: {
		fontFamily: theme.fonts.family.headline,
		fontSize: 25,
		color: theme.colors.gameText,
	},
	eyebrow: {
		fontFamily: theme.fonts.family.bodyExtraBold,
		fontSize: 11,
		letterSpacing: 1,
		color: theme.colors["blue-600"],
	},
	subtitle: { fontSize: 14, color: theme.colors.gameMuted },
	awning: { height: 8, flexDirection: "row" },
	stripe: { flex: 1, backgroundColor: theme.colors["blue-500"] },
	stripeWarm: { backgroundColor: theme.colors["red-500"] },
	list: { padding: 16, gap: 12, paddingBottom: 28 },
	card: {
		padding: 16,
		gap: 14,
		borderRadius: 22,
		borderWidth: 1.5,
		borderColor: theme.colors.gameBorder,
		backgroundColor: theme.colors["neutral-0"],
	},
	productWell: {
		backgroundColor: theme.colors["blue-50"],
		borderRadius: 18,
		padding: 8,
	},
	productImage: { width: 54, height: 54 },
	productName: {
		fontFamily: theme.fonts.family.headline,
		fontSize: 21,
		color: theme.colors.gameText,
	},
	metrics: { flexDirection: "row", gap: 10 },
	metric: {
		flex: 1,
		backgroundColor: theme.colors["neutral-100"],
		padding: 12,
		gap: 4,
		borderRadius: 15,
	},
	number: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 20,
		color: theme.colors["blue-600"],
	},
	track: {
		height: 8,
		backgroundColor: theme.colors.gameBorder,
		borderRadius: 8,
		overflow: "hidden",
	},
	fill: {
		height: 8,
		borderRadius: 8,
		backgroundColor: theme.colors["green-500"],
	},
	actions: { flexDirection: "row", gap: 10 },
	notice: {
		padding: 12,
		fontSize: 14,
		color: theme.colors["violet-600"],
		backgroundColor: theme.colors["violet-50"],
	},
	search: {
		margin: 16,
		marginBottom: 0,
		backgroundColor: theme.colors["neutral-0"],
		borderWidth: 1,
		borderColor: theme.colors.gameBorder,
		borderRadius: 16,
		padding: 14,
		fontFamily: theme.fonts.family.body,
		color: theme.colors.gameText,
	},
	quantity: { flex: 1, textAlign: "center" },
	total: {
		fontFamily: theme.fonts.family.headline,
		fontSize: 30,
		color: theme.colors["amber-600"],
	},
}));
