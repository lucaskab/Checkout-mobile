import type { SupplierOrder } from "@/@types/logistics";
import { getMarketCategoryProductId } from "@/data/game-icon-assets";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import { itemCatalog, itemCategories } from "@/data/market-products";
import { productionRecipes } from "@/data/production-sectors";
import { getNextSupplierOrderSlotUpgrade } from "@/data/supplier-capacity";
import {
	formatSupplierDeliveryTime,
	getOrderProgress,
	getOrderRemainingTime,
	getSupplierOrderStatus,
} from "@/services/logistics";
import { getProductionEconomy } from "@/services/production";
import {
	getMaxShelfOrderQuantity,
	getShelfOrderQuote,
} from "@/services/shelf-order-quote";
import type { Routes } from ".";
import {
	act,
	type Card,
	card,
	fmt,
	gameIcon,
	go,
	page,
	productIcon,
	ratio,
	type State,
	swap,
} from "../view-kit";

const categories = [{ id: "todos", label: "Todos" }, ...itemCategories];

// Same as src/screens/suppliers/components/items-list/static.ts (initialProducts).
const supplierProducts = itemCatalog.map((product) => {
	const recipe = productionRecipes.find(
		(item) => item.outputProductId === product.id,
	);
	return {
		category: product.category,
		id: product.id,
		name: product.name,
		productionSavingsPercent: recipe
			? getProductionEconomy(recipe).savingsPercent
			: undefined,
		sellPrice: product.sellingPrice,
		shelfTime: product.supplierTime,
	};
});

// Mirrors SuppliersScreen: unlocked products with warehouse capacity and owned units.
function products(state: State) {
	return supplierProducts
		.filter((product) => state.market.unlockedProductIds.includes(product.id))
		.map((product) => {
			const catalogProduct = itemCatalog.find((item) => item.id === product.id);
			return {
				...product,
				capacity: catalogProduct
					? getInventoryCapacity(
							catalogProduct,
							state.inventoryCapacityLevels[product.id],
						)
					: 0,
				owned: state.inventory[product.id] ?? 0,
			};
		});
}

const activeOrders = (state: State, now: number) =>
	state.logistics.orders.filter(
		(order) => getSupplierOrderStatus(order, now) !== "entregue",
	);

const clock = (ms: number) => {
	const seconds = Math.max(0, Math.ceil(ms / 1000));
	return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};

// One "Pedidos em andamento" row of ItemsList.
function orderCard(state: State, order: SupplierOrder, now: number, header: string): Card {
	const product = itemCatalog.find((item) => item.id === order.productId);
	const status = getSupplierOrderStatus(order, now);
	const waiting = status === "entregue" && order.status !== "entregue";
	const tokens = state.logistics.emergencyTokens;
	const buttons = waiting
		? []
		: [
				act(tokens > 0 ? "Entrega agora" : "Entrega agora · 5", "deliverOrderInstantly", [order.id], {
					variant: tokens > 0 ? "success" : "gem",
					icon: gameIcon(tokens > 0 ? "ticket" : "diamond"),
					ok: "Pedido entregue no depósito!",
					fail: "Sem diamantes/tickets ou sem espaço no depósito.",
				}),
				...(status === "em-transporte"
					? [
							act("Finalizar por 2", "completeOrderFinalStage", [order.id], {
								variant: "gem",
								icon: gameIcon("diamond"),
								ok: "Pedido entregue no depósito!",
								fail: "Não foi possível finalizar (diamantes, etapa ou espaço).",
							}),
						]
					: []),
			];
	return card(`${product?.name ?? "Produto"} · ${order.quantity} unid.`, {
		eyebrow: header,
		icon: product ? productIcon(product.id) : gameIcon("package"),
		subtitle: waiting
			? "Aguardando espaço no estoque"
			: status === "em-producao"
				? "Em produção"
				: status === "enviado"
					? "Pedido enviado"
					: "Em transporte",
		lines: [
			waiting
				? "Amplie a capacidade ou libere espaço"
				: `Chega em ${getOrderRemainingTime(order, now)}`,
		],
		tone: waiting ? "warning" : "info",
		progress: getOrderProgress(order, now),
		buttons,
	});
}

export const routes: Routes = {
	// "suppliers:<category>" — SuppliersScreen (stock summary, logistics trigger, orders, products).
	suppliers: (state, [category = "todos"]) => {
		const now = Date.now();
		const all = products(state);
		const active = category && categories.some((item) => item.id === category) ? category : "todos";
		const filtered = active === "todos" ? all : all.filter((product) => product.category === active);
		const totalOwned = all.reduce((total, product) => total + product.owned, 0);
		const totalCapacity = all.reduce((total, product) => total + product.capacity, 0);
		const { orders, supplierOrderSlots, premiumCurrency } = state.logistics;
		const running = activeOrders(state, now);
		const visible = orders.filter(
			(order) => getSupplierOrderStatus(order, now) !== "entregue" || order.status !== "entregue",
		);
		const header = `PEDIDOS EM ANDAMENTO · ${running.length}/${supplierOrderSlots} ATIVO(S)`;
		const cards: Card[] = [
			card("Meu estoque", {
				icon: gameIcon("package"),
				badge: `${fmt(totalOwned)} / ${fmt(totalCapacity)}`,
				lines: [`${fmt(totalOwned)} / ${fmt(totalCapacity)} unid.`],
				progress: Math.min(totalOwned / Math.max(totalCapacity, 1), 1),
			}),
			card("Central logística", {
				icon: gameIcon("deliveryTruck"),
				subtitle: `${running.length}/${supplierOrderSlots} pedidos em andamento`,
				badge: `${fmt(premiumCurrency)} diam.`,
				buttons: [go("Abrir", "logistics", { icon: gameIcon("deliveryTruck") })],
			}),
			...visible.map((order) => orderCard(state, order, now, header)),
			...filtered.map((product) =>
				card(product.name, {
					eyebrow: `PRODUTOS DISPONÍVEIS · ${filtered.length} ITENS`,
					icon: productIcon(product.id),
					badge: product.owned > 0 ? `${product.owned}/${product.capacity}` : "",
					lines: [
						...(product.productionSavingsPercent !== undefined
							? [`Fabricar economiza ${product.productionSavingsPercent}%`]
							: []),
						`Escolha a quantidade · Entrega: ${product.shelfTime}`,
						`Vende por ${product.sellPrice}/un`,
					],
					buttons: [
						go("Escolher quantidade", `order:${product.id}:1`, {
							variant: "primary",
							icon: gameIcon("deliveryTruck"),
						}),
					],
				}),
			),
		];
		return page(`suppliers:${active}`, "Entregas", cards, {
			icon: gameIcon("deliveryTruck"),
			subtitle: `Produtos disponíveis · ${filtered.length} itens`,
			chips: categories.map((item) =>
				swap(
					item.label,
					`suppliers:${item.id}`,
					item.id === active,
					item.id === "todos"
						? gameIcon("cart")
						: productIcon(getMarketCategoryProductId(item.id)),
				),
			),
		});
	},
	// "order:<productId>:<qty>" — SupplierOrderSheet.
	order: (state, [id, qty]) => {
		const productId = Number(id);
		const product = itemCatalog.find((item) => item.id === productId);
		const parsed = Number.parseInt(qty ?? "1", 10);
		const quantity = Number.isFinite(parsed) ? Math.max(0, parsed) : 1;
		const quote = getShelfOrderQuote(state, productId, quantity);
		if (!product || !quote) return page(`order:${id}:${qty}`, "Produto não encontrado", []);
		const unitQuote = getShelfOrderQuote(state, productId, 1);
		const maxQuantity = getMaxShelfOrderQuantity(state, productId);
		const owned = state.inventory[productId] ?? 0;
		const to = (value: number) => `order:${productId}:${value}`;
		const step = (label: string, value: number, enabled: boolean) => ({
			...swap(label, to(value), false),
			enabled,
		});
		const unitPrice =
			quantity > 0 ? Number((quote.total / quantity).toFixed(2)) : (unitQuote?.total ?? 0);
		const message = `Pedido de ${quantity} ${product.name} confirmado! Acompanhe em Entregas.`;
		return page(to(quantity), `Pedir ${product.name}`, [
			card("Espaço no depósito", {
				eyebrow: "FORNECEDORES",
				icon: gameIcon("warehouse"),
				subtitle: `${owned}/${quote.capacity} unid.`,
				badge: `${quote.availableSpace} livre${quote.availableSpace === 1 ? "" : "s"}`,
				lines: quote.incoming > 0 ? [`A caminho: ${quote.incoming} unid.`] : [],
				progress: ratio(owned, quote.capacity),
			}),
			card("Quantidade exata", {
				subtitle: `${quantity} unidades`,
				badge: `x${quantity}`,
				buttons: [
					step("−10", Math.max(0, quantity - 10), quantity > 0),
					step("−", quantity - 1, quantity > 0),
					step("+", quantity + 1, quantity < quote.availableSpace),
					step("+10", Math.min(quote.availableSpace, quantity + 10), quantity < quote.availableSpace),
				],
			}),
			card("Atalhos", {
				buttons: [
					step("0", 0, quantity !== 0),
					step(`Máx · ${maxQuantity}`, maxQuantity, quantity !== maxQuantity),
				],
			}),
			card("Total do pedido", {
				icon: gameIcon("coin"),
				badge: fmt(quote.total),
				tone: quote.reason ? "warning" : "",
				subtitle: quote.reason ?? "",
				lines: [
					`Preço por unidade: ${unitPrice.toLocaleString("pt-BR")} moedas`,
					`Total do pedido: ${fmt(quote.total)} moedas`,
					`Seu saldo: ${fmt(state.coins)} moedas`,
				],
				buttons: [
					act(`Confirmar pedido · ${quote.total}`, "placeSupplierOrder", [{ productId, quantity }], {
						variant: "coin",
						icon: gameIcon("deliveryTruck"),
						enabled: !quote.reason,
						ok: message,
						fail:
							quote.reason ??
							"As condições do pedido mudaram. Confira saldo, espaço e entregas disponíveis.",
						after: "back",
					}),
				],
			}),
		], {
			icon: productIcon(product.id),
			subtitle: `Entrega no depósito em cerca de ${formatSupplierDeliveryTime(quote.duration)}.`,
		});
	},
	// "logistics" — LogisticsSheet (turbo + simultaneous order slots).
	logistics: (state) => {
		const now = Date.now();
		const { logistics, coins } = state;
		const level = state.market.level;
		const next = getNextSupplierOrderSlotUpgrade(logistics.supplierOrderSlots);
		const boostLeft = (logistics.logisticsBoostExpiresAt ?? 0) - now;
		const running = activeOrders(state, now);
		const upgradeFail = (currency: "coins" | "diamonds") =>
			next && level < next.playerLevel
				? `Alcance o nível ${next.playerLevel} para liberar mais um pedido.`
				: currency === "coins"
					? "Você não tem moedas suficientes para este upgrade."
					: "Você não tem diamantes suficientes para este upgrade.";
		return page("logistics", "Central logística", [
			card("Saldo", {
				icon: gameIcon("diamond"),
				lines: [
					`Diamantes: ${fmt(logistics.premiumCurrency)}`,
					`Tickets de entrega: ${fmt(logistics.emergencyTokens)}`,
					`${running.length}/${logistics.supplierOrderSlots} pedidos em andamento`,
				],
			}),
			card("Turbo logística · 3 diamantes", {
				icon: gameIcon("lightning"),
				subtitle: "Pedidos novos chegam 30% mais rápido por 15 minutos.",
				tone: boostLeft > 0 ? "success" : "",
				badge: boostLeft > 0 ? clock(boostLeft) : "",
				lines: boostLeft > 0 ? [`Turbo ativo · faltam ${clock(boostLeft)}`] : [],
				buttons: [
					act("Ativar · 3", "activateLogisticsBoost", [], {
						variant: "gem",
						icon: gameIcon("diamond"),
						enabled: logistics.premiumCurrency >= 3,
						ok: "Turbo ativado. Novos pedidos chegam 30% mais rápido por 15 minutos.",
						fail: "Você precisa de 3 diamantes para ativar o turbo.",
					}),
				],
			}),
			card("Pedidos simultâneos", {
				icon: gameIcon("deliveryTruck"),
				subtitle: `Você pode manter ${logistics.supplierOrderSlots} pedidos ativos ao mesmo tempo.`,
				badge: String(logistics.supplierOrderSlots),
				lines: next
					? [`Próximo slot: ${next.slots} pedidos · requer nível ${next.playerLevel}`]
					: [],
				tone: next && level < next.playerLevel ? "locked" : "",
				buttons: next
					? [
							act(next.coinCost.toLocaleString("pt-BR"), "upgradeSupplierOrderSlots", ["coins"], {
								variant: "coin",
								icon: gameIcon("coin"),
								enabled: level >= next.playerLevel && coins >= next.coinCost,
								ok: `Agora você pode manter ${next.slots} pedidos ativos.`,
								fail: upgradeFail("coins"),
							}),
							act(next.diamondCost.toString(), "upgradeSupplierOrderSlots", ["diamonds"], {
								variant: "gem",
								icon: gameIcon("diamond"),
								enabled:
									level >= next.playerLevel && logistics.premiumCurrency >= next.diamondCost,
								ok: `Agora você pode manter ${next.slots} pedidos ativos.`,
								fail: upgradeFail("diamonds"),
							}),
						]
					: [],
			}),
		], {
			icon: gameIcon("deliveryTruck"),
			subtitle: "Acelere entregas sem remover a importância do planejamento.",
		});
	},
};
