import { itemCatalog, shelves } from "@/data/market-products";
import {
	getNextShelfCapacityUpgrade,
	getNextShelfSlotUpgrade,
	getNextShelfUnlockUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import {
	getShelfSlotCount,
	getShelfSlotIds,
	getUnlockedPhysicalShelfCount,
	resolveShelfSlotCounts,
} from "@/data/shelf-slots";
import {
	formatSupplierDeliveryTime,
	getOrderProgress,
	getOrderRemainingTime,
} from "@/services/logistics";
import {
	getMaxShelfOrderQuantity,
	getShelfOrderQuote,
} from "@/services/shelf-order-quote";
import {
	act,
	button,
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
import type { Routes } from ".";

// Slot ids contain ":" ("dairy:1"), so routes address a slot as <shelfId>:<slotIndex>.
function slotCounts(state: State) {
	return resolveShelfSlotCounts(state.shelfSlotCounts, state.unlockedShelfSlots);
}
function slotsOf(state: State, shelfId: string) {
	return getShelfSlotIds(shelfId, getShelfSlotCount(shelfId, slotCounts(state)));
}
const shelfName = (shelfId: string) =>
	shelves.find((shelf) => shelf.id === shelfId)?.name ?? "Prateleira";
const productOf = (state: State, slotId: string) =>
	itemCatalog.find((item) => item.id === state.shelfAssignments[slotId]);

// ShelfListScreen
function storePage(state: State) {
	const counts = slotCounts(state);
	const unlockedShelves = getUnlockedPhysicalShelfCount(counts);
	const nextShelfUpgrade = getNextShelfUnlockUpgrade(unlockedShelves);
	const cards: Card[] = shelves.slice(0, unlockedShelves).map((shelf) => {
		const slotCount = getShelfSlotCount(shelf.id, counts);
		const slotUpgrade = getNextShelfSlotUpgrade(slotCount);
		const slotIds = getShelfSlotIds(shelf.id, slotCount);
		const filled = slotIds.filter((id) => state.shelfAssignments[id]).length;
		const buttons = [go("Gerenciar prateleira", `shelf:${shelf.id}`, { variant: "primary" })];
		if (slotUpgrade)
			buttons.push(
				act(
					`Expandir slots · Nv. ${slotUpgrade.playerLevel} · ${fmt(slotUpgrade.coinCost)}`,
					"expandShelfSlots",
					[shelf.id],
					{
						variant: "coin",
						icon: gameIcon("coin"),
						enabled:
							state.market.level >= slotUpgrade.playerLevel &&
							state.coins >= slotUpgrade.coinCost,
						ok: "Espaço adicional liberado nesta prateleira.",
						fail: "Confira seu nível e saldo.",
					},
				),
			);
		return card(shelfName(shelf.id), {
			icon: gameIcon("shelf"),
			badge: `${filled}/${slotIds.length}`,
			lines: slotIds.map((slotId, index) => {
				const product = productOf(state, slotId);
				return `${index + 1}. ${product ? `${product.name} · ${state.shelfStock[slotId] ?? 0} unid.` : "Livre"}`;
			}),
			buttons,
		});
	});
	if (nextShelfUpgrade)
		cards.push(
			card("Nova prateleira", {
				icon: gameIcon("shelf"),
				tone: "locked",
				subtitle: "Cada prateleira começa com quatro espaços.",
				lines: [`Nível ${nextShelfUpgrade.playerLevel}`],
				buttons: [
					act(
						`Nova prateleira · Nv. ${nextShelfUpgrade.playerLevel} · ${fmt(nextShelfUpgrade.coinCost)} moedas`,
						"unlockNextShelf",
						[],
						{
							variant: "coin",
							icon: gameIcon("coin"),
							enabled:
								state.market.level >= nextShelfUpgrade.playerLevel &&
								state.coins >= nextShelfUpgrade.coinCost,
							ok: "Prateleira liberada com quatro espaços disponíveis.",
							fail: "Confira seu nível e saldo.",
						},
					),
				],
			}),
		);
	return page("store", "Prateleiras", cards, {
		icon: gameIcon("shelf"),
		subtitle:
			"Seu mix de produtos, do seu jeito. Cada prateleira começa com quatro espaços.",
	});
}

// ShelfManagementScreen, "slots" page
function slotCard(state: State, shelfId: string, slotId: string, index: number) {
	const product = productOf(state, slotId);
	const capacity = getShelfCapacity(state.shelfUpgradeLevels[shelfId]);
	if (!product)
		return card("Que tal algo novo?", {
			eyebrow: `ESPAÇO ${index + 1}`,
			icon: gameIcon("basket"),
			subtitle: "Um espaço esperando seu próximo sucesso.",
			badge: "Livre",
			buttons: [go("Adicionar produto", `picker:${shelfId}:${index}:all`, { variant: "primary" })],
		});
	const stock = state.shelfStock[slotId] ?? 0;
	const price = state.shelfPrices[slotId] ?? product.sellingPrice ?? 0;
	const reserve = state.inventory[product.id] ?? 0;
	const incomingOrder = state.logistics.orders
		.filter((order) => order.productId === product.id && order.status !== "entregue")
		.sort(
			(first, second) =>
				first.createdAt + first.deliveryDurationMs - (second.createdAt + second.deliveryDurationMs),
		)[0];
	const now = Date.now();
	const lines = [
		`Na prateleira: ${stock} / ${capacity}`,
		`No depósito: ${reserve}`,
		`Preço de venda: ${price} (${product.minPrice}–${product.maxPrice})`,
	];
	const restock =
		incomingOrder && reserve === 0
			? button(`A caminho · ${getOrderRemainingTime(incomingOrder, now)}`, {
					icon: gameIcon("deliveryTruck"),
					variant: "secondary",
					enabled: false,
				})
			: reserve === 0
				? go("Pedir estoque", `shelforder:${product.id}:1`, {
						variant: "coin",
						icon: gameIcon("deliveryTruck"),
					})
				: act(
						stock >= capacity
							? "Prateleira cheia"
							: `Reabastecer +${Math.min(reserve, capacity - stock)}`,
						"restockShelf",
						[{ shelfId: slotId, productId: product.id, amount: Math.min(reserve, capacity - stock) }],
						{ variant: "success", icon: gameIcon("basket"), enabled: stock < capacity },
					);
	if (incomingOrder && reserve === 0)
		lines.push(`Entrega: ${Math.round(getOrderProgress(incomingOrder, now) * 100)}%`);
	return card(product.name, {
		eyebrow: `ESPAÇO ${index + 1}`,
		icon: productIcon(product.id),
		subtitle: `Venda: ${price} moedas`,
		badge: `x${stock}`,
		tone: stock === 0 ? "warning" : "",
		progress: ratio(stock, capacity),
		lines,
		buttons: [
			act("−", "setShelfPrice", [slotId, price - 1], {
				variant: "secondary",
				enabled: price > product.minPrice,
			}),
			act("+", "setShelfPrice", [slotId, price + 1], {
				variant: "secondary",
				enabled: price < product.maxPrice,
			}),
			restock,
			act("Remover", "clearShelf", [slotId], {
				variant: "danger",
				ok: "Produto devolvido ao depósito.",
				fail: "Libere espaço no depósito para devolver este produto.",
			}),
		],
	});
}

function shelfPage(state: State, [shelfId = ""]: string[]) {
	const route = `shelf:${shelfId}`;
	const counts = slotCounts(state);
	const slotCount = getShelfSlotCount(shelfId, counts);
	const slotIds = getShelfSlotIds(shelfId, slotCount);
	const unlockedShelves = getUnlockedPhysicalShelfCount(counts);
	const shelfIndex = shelves.findIndex((shelf) => shelf.id === shelfId);
	const nextShelfUpgrade = getNextShelfUnlockUpgrade(unlockedShelves);
	const canUnlockHere = shelfIndex === unlockedShelves && !!nextShelfUpgrade;
	const options = { icon: gameIcon("shelf"), subtitle: "SEU MERCADO" };
	if (slotCount <= 0) {
		const lockedCard = card(shelfName(shelfId), {
			tone: "locked",
			icon: gameIcon("shelf"),
			subtitle: canUnlockHere
				? "Desbloqueie esta prateleira para começar com quatro espaços disponíveis."
				: "Desbloqueie as prateleiras anteriores para acessar esta área.",
		});
		if (canUnlockHere && nextShelfUpgrade) {
			lockedCard.lines = [`Nível ${nextShelfUpgrade.playerLevel}`];
			lockedCard.buttons = [
				act(`Desbloquear · ${fmt(nextShelfUpgrade.coinCost)}`, "unlockNextShelf", [], {
					variant: "coin",
					icon: gameIcon("coin"),
					enabled:
						state.market.level >= nextShelfUpgrade.playerLevel &&
						state.coins >= nextShelfUpgrade.coinCost,
					ok: "Prateleira liberada com quatro espaços disponíveis.",
					fail: "Confira seu nível e saldo.",
				}),
			];
		}
		return page(route, shelfName(shelfId), [lockedCard], options);
	}
	const cards = slotIds.map((slotId, index) => slotCard(state, shelfId, slotId, index));
	const slotUpgrade = getNextShelfSlotUpgrade(slotCount);
	if (slotUpgrade)
		cards.push(
			card("Mais espaços nesta prateleira", {
				icon: gameIcon("shelf"),
				subtitle: `Aumente esta prateleira para ${slotUpgrade.unlockedSlots} espaços · Nível ${slotUpgrade.playerLevel}`,
				buttons: [
					act(`Expandir · ${fmt(slotUpgrade.coinCost)} moedas`, "expandShelfSlots", [shelfId], {
						variant: "coin",
						icon: gameIcon("coin"),
						enabled:
							state.market.level >= slotUpgrade.playerLevel &&
							state.coins >= slotUpgrade.coinCost,
						ok: "Espaço adicional liberado nesta prateleira.",
						fail: "Confira seu nível e saldo.",
					}),
				],
			}),
		);
	const upgrade = getNextShelfCapacityUpgrade(state.shelfUpgradeLevels[shelfId]);
	if (upgrade) {
		const levelOk = state.market.level >= upgrade.playerLevel;
		const messages = {
			ok: "Capacidade ampliada nos quatro espaços!",
			fail: "Confira seu nível e saldo.",
		};
		cards.push(
			card("Mais produtos para vender", {
				icon: gameIcon("basket"),
				subtitle: `Aumente cada espaço para ${upgrade.capacity} unidades · Nível ${upgrade.playerLevel}`,
				lines: [`Capacidade atual: ${getShelfCapacity(state.shelfUpgradeLevels[shelfId])} unid.`],
				buttons: [
					act(`Ampliar · ${fmt(upgrade.coinCost)} moedas`, "upgradeShelfCapacity", [shelfId, "coins"], {
						variant: "coin",
						icon: gameIcon("coin"),
						enabled: levelOk && state.coins >= upgrade.coinCost,
						...messages,
					}),
					act(
						`Ampliar · ${fmt(upgrade.diamondCost)} diamantes`,
						"upgradeShelfCapacity",
						[shelfId, "diamonds"],
						{
							variant: "gem",
							icon: gameIcon("diamond"),
							enabled: levelOk && state.logistics.premiumCurrency >= upgrade.diamondCost,
							...messages,
						},
					),
				],
			}),
		);
	}
	return page(route, shelfName(shelfId), cards, options);
}

// ShelfManagementScreen, "picker" page. RN has a text search; here categories act as the filter.
function pickerPage(state: State, [shelfId = "", slot = "0", filter = "all"]: string[]) {
	const slotId = slotsOf(state, shelfId)[Number(slot)] ?? shelfId;
	const route = (value: string) => `picker:${shelfId}:${slot}:${value}`;
	const available = itemCatalog.filter(
		(product) =>
			state.market.unlockedProductIds.includes(product.id) &&
			!Object.entries(state.shelfAssignments).some(
				([id, assigned]) => assigned === product.id && id !== slotId,
			),
	);
	const categories = [...new Set(available.map((product) => product.category))];
	const products = available.filter((product) => filter === "all" || product.category === filter);
	const cards = products.map((product) =>
		card(product.name, {
			icon: productIcon(product.id),
			eyebrow: product.category.toLocaleUpperCase("pt-BR"),
			subtitle: `Depósito: ${state.inventory[product.id] ?? 0} unid.`,
			badge: `${product.sellingPrice}`,
			buttons: [
				act("Adicionar produto", "assignProductToShelf", [slotId, product.id, true], {
					after: "back",
					ok: `${product.name} adicionado. Reabasteça para começar a vender.`,
					fail: "Não foi possível adicionar o produto.",
				}),
			],
		}),
	);
	if (!cards.length)
		cards.push(
			card("Nenhum produto disponível", {
				tone: "info",
				subtitle: "Novos produtos são liberados com seu progresso.",
			}),
		);
	return page(route(filter), "Escolher produto", cards, {
		icon: gameIcon("shelf"),
		subtitle: "Escolha um produto diferente para este espaço.",
		chips: [
			swap("Todos", route("all"), filter === "all"),
			...categories.map((category) => swap(category, route(category), filter === category)),
		],
	});
}

// ShelfManagementScreen, "order" page (SupplierOrderSheet opened from "Pedir estoque").
function orderPage(state: State, [id = "0", qty = "1"]: string[]) {
	const productId = Number(id);
	const product = itemCatalog.find((item) => item.id === productId);
	const quantity = Math.max(0, Math.floor(Number(qty) || 0));
	const quote = getShelfOrderQuote(state, productId, quantity);
	const unitQuote = getShelfOrderQuote(state, productId, 1);
	if (!product || !quote) return page(`shelforder:${id}:${qty}`, "Pedir estoque", []);
	const maxQuantity = getMaxShelfOrderQuantity(state, productId);
	const route = (value: number) => `shelforder:${productId}:${value}`;
	const step = (label: string, value: number, enabled: boolean) => ({
		...swap(label, route(value), false),
		enabled,
	});
	const unitPrice =
		quantity > 0 ? Number((quote.total / quantity).toFixed(2)) : (unitQuote?.total ?? 0);
	return page(
		route(quantity),
		"Pedir estoque",
		[
			card(`Pedir ${product.name}`, {
				eyebrow: "FORNECEDORES",
				icon: productIcon(product.id),
				subtitle: `Entrega no depósito em cerca de ${formatSupplierDeliveryTime(quote.duration)}.`,
				lines: [
					`Espaço no depósito: ${state.inventory[productId] ?? 0}/${quote.capacity} unid.`,
					`${quote.availableSpace} livre${quote.availableSpace === 1 ? "" : "s"}`,
				],
				progress: ratio(state.inventory[productId] ?? 0, quote.capacity),
			}),
			card("Quantidade exata", {
				badge: `${quantity} unid.`,
				subtitle: `${quantity} unidades`,
				buttons: [
					step("−", quantity - 1, quantity > 0),
					step("+", quantity + 1, quantity < quote.availableSpace),
					step("0", 0, quantity !== 0),
					step(`Máx · ${maxQuantity}`, maxQuantity, quantity !== maxQuantity),
				],
			}),
			card("Total do pedido", {
				icon: gameIcon("coin"),
				badge: fmt(quote.total),
				tone: quote.reason ? "warning" : "",
				lines: [
					`Preço por unidade: ${unitPrice} moedas`,
					`Seu saldo: ${fmt(state.coins)} moedas`,
					...(quote.reason ? [quote.reason] : []),
				],
				buttons: [
					act(`Confirmar pedido · ${fmt(quote.total)}`, "placeSupplierOrder", [{ productId, quantity }], {
						variant: "coin",
						icon: gameIcon("deliveryTruck"),
						enabled: !quote.reason,
						after: "back",
						ok: `Pedido de ${quantity} ${product.name} confirmado! Acompanhe em Entregas.`,
						fail: "As condições do pedido mudaram. Confira saldo, espaço e entregas disponíveis.",
					}),
				],
			}),
		],
		{ icon: gameIcon("deliveryTruck"), subtitle: "Do fornecedor direto para o seu depósito." },
	);
}

export const routes: Routes = {
	store: (state) => storePage(state),
	shelf: shelfPage,
	picker: pickerPage,
	shelforder: orderPage,
};
