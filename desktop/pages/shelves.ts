import { getEraOrder, itemCatalog, itemCategories, shelves } from "@/data/market-products";
import {
	getNextShelfCapacityUpgrade,
	getNextShelfSlotUpgrade,
	getNextShelfUnlockUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import { canShelfHold } from "@/data/shelf-categories";
import { getFixtureName, getShelfType } from "@/data/shelf-types";
import { describeFixtureProducts } from "@/data/fixture-products";
import { getItemIncomeMultiplier, getMarketEra, MAX_ITEM_LEVEL } from "@/data/economy";
import { getProductLevel, getProductUpgradeCost } from "@/services/product-levels";
import { isMarketBuilding } from "@/services/market-era";
import {
	getShelfSlotCount,
	getShelfSlotIds,
	sectorShelves,
	isShelfSlotUnlocked,
	shelfProductSlots,
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
import { getNextShelfBuildStatus } from "@/services/interior-construction";
import { buildCard, shelfThumb } from "./build-cards";
import { shelfViewPage } from "./shelf-view";

// The next shelf: bought, it goes to the inventory and is built where the player places it.
function shelfBuild(state: State, title: string): Card {
	const build = getNextShelfBuildStatus(state);
	return buildCard(state, {
		title: build.shelf ? `${title}: ${getFixtureName(build.shelf.id, state.era.id)}` : title,
		icon: build.shelf ? shelfThumb(build.shelf.id) : gameIcon("shelf"),
		subtitle: build.shelf
			? `${acceptsNow(state, build.shelf.id)} Começa com quatro espaços.`
			: "Cada prateleira começa com quatro espaços.",
		status: build,
		coins: { action: "unlockNextShelf", args: [], price: build.coinCost },
	});
}

// Slot ids contain ":" ("dairy:1"), so routes address a slot as <shelfId>:<slotIndex>.
function slotCounts(state: State) {
	return resolveShelfSlotCounts(state.shelfSlotCounts, state.unlockedShelfSlots);
}
function slotsOf(state: State, shelfId: string) {
	return getShelfSlotIds(shelfId, getShelfSlotCount(shelfId, slotCounts(state)));
}
const shelfName = (shelfId: string, state?: State) => getFixtureName(shelfId, state?.era.id);
/** What the fixture sells today: only the products already open ("Aceita: água mineral e refrigerante."). */
function acceptsNow(state: State, shelfId: string) {
	const list = describeFixtureProducts(shelfId, state.market.unlockedProductIds);
	if (list) return `Aceita: ${list}.`;
	const shelf = getShelfType(shelfId);
	return shelf && getEraOrder(shelf.eraId) > getEraOrder(state.era.id)
		? `Os produtos dele chegam com: ${getMarketEra(shelf.eraId).name}.`
		: "Ainda não há produto liberado para este móvel.";
}
const productOf = (state: State, slotId: string) =>
	itemCatalog.find((item) => item.id === state.shelfAssignments[slotId]);

// Before the market building the stall shows only a few products: the first ones with stock, in shelf order.
function stallCard(state: State): Card[] {
	if (isMarketBuilding(state.era.id)) return [];
	const era = getMarketEra(state.era.id);
	const counts = slotCounts(state);
	const stocked = shelfProductSlots.filter(
		(slot) =>
			isShelfSlotUnlocked(slot.id, counts) &&
			state.shelfAssignments[slot.id] != null &&
			(state.shelfStock[slot.id] ?? 0) > 0,
	);
	const onSale = stocked.slice(0, era.productSlots);
	const waiting = stocked.slice(era.productSlots);
	const name = (slotId: string) => productOf(state, slotId)?.name ?? "?";
	return [
		card(`${era.name}: ${era.productSlots} lugares de produto`, {
			eyebrow: "À VENDA AGORA",
			icon: gameIcon("market"),
			badge: `${onSale.length}/${era.productSlots}`,
			subtitle:
				"Antes do mercadinho cabem poucos produtos à mostra. Ficam à venda os primeiros com estoque, na ordem das prateleiras; quando um acaba, o próximo entra no lugar. Cada expansão traz mais lugares.",
			lines: [
				onSale.length
					? `À venda: ${onSale.map((slot) => name(slot.id)).join(", ")}`
					: "Nada à venda: coloque estoque nas prateleiras.",
				...(waiting.length ? [`Esperando lugar: ${waiting.map((slot) => name(slot.id)).join(", ")}`] : []),
			],
			tone: onSale.length ? "featured" : "warning",
		}),
	];
}

// ShelfListScreen
function storePage(state: State) {
	const counts = slotCounts(state);
	const unlockedShelves = getUnlockedPhysicalShelfCount(counts);
	const nextShelfUpgrade = getNextShelfUnlockUpgrade(unlockedShelves);
	// The shelves bought so far, then the counters of the sectors built (they sell like shelves).
	const fixtures = [
		...shelves.slice(0, unlockedShelves),
		...sectorShelves.filter((counter) => getShelfSlotCount(counter.id, counts) > 0),
	];
	const cards: Card[] = fixtures.map((shelf) => {
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
		return card(shelfName(shelf.id, state), {
			icon: gameIcon("shelf"),
			subtitle: acceptsNow(state, shelf.id),
			badge: `${filled}/${slotIds.length}`,
			lines: slotIds.map((slotId, index) => {
				const product = productOf(state, slotId);
				return `${index + 1}. ${product ? `${product.name} · ${state.shelfStock[slotId] ?? 0} unid.` : "Livre"}`;
			}),
			buttons,
		});
	});
	if (nextShelfUpgrade) cards.push(shelfBuild(state, "Nova prateleira"));
	return page("store", "Prateleiras", [...stallCard(state), ...cards], {
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
	// A working stock clerk refills from the depot on his own: no manual "Reabastecer" then.
	const clerk = (state.employees?.employees ?? []).some(
		(employee) => employee.isWorking && employee.role === "stock_clerk",
	);
	if (clerk && reserve > 0)
		lines.push(stock >= capacity ? "Repositor: prateleira cheia" : "Repositor: reposição automática");
	const restock =
		clerk && reserve > 0
			? null
			: incomingOrder && reserve === 0
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
	// Product level: more profit per sale and more attractive (src/services/product-levels.ts).
	const level = getProductLevel(state.productLevels, product.id);
	const upgradeCost = getProductUpgradeCost(state.era.id, level);
	lines.push(
		level > 0
			? `Nível do produto: ${level}/${MAX_ITEM_LEVEL} · +${Math.round((getItemIncomeMultiplier(level) - 1) * 100)}% de lucro`
			: `Nível do produto: 0/${MAX_ITEM_LEVEL}`,
	);
	if (upgradeCost != null) lines.push(`Próximo nível: ${fmt(upgradeCost)} moedas · +10% de lucro e mais atrativo`);
	const upgrade =
		upgradeCost == null
			? null
			: act("Nível +", "upgradeProduct", [product.id], {
					variant: "coin",
					icon: gameIcon("coin"),
					enabled: state.coins >= upgradeCost,
					ok: `${product.name} subiu para o nível ${level + 1}: +10% de lucro em cada venda.`,
					fail: "Moedas insuficientes.",
				});
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
			...(restock ? [restock] : []),
			...(upgrade ? [upgrade] : []),
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
		const lockedCard = card(shelfName(shelfId, state), {
			tone: "locked",
			icon: gameIcon("shelf"),
			subtitle: canUnlockHere
				? "Desbloqueie esta prateleira para começar com quatro espaços disponíveis."
				: "Desbloqueie as prateleiras anteriores para acessar esta área.",
		});
		if (canUnlockHere && nextShelfUpgrade)
			return page(route, shelfName(shelfId, state), [shelfBuild(state, shelfName(shelfId, state))], options);
		return page(route, shelfName(shelfId, state), [lockedCard], options);
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
	return page(route, shelfName(shelfId, state), cards, options);
}

// ShelfManagementScreen, "picker" page. RN has a text search; here categories act as the filter.
function pickerPage(state: State, [shelfId = "", slot = "0", filter = "all"]: string[]) {
	const slotId = slotsOf(state, shelfId)[Number(slot)] ?? shelfId;
	const route = (value: string) => `picker:${shelfId}:${slot}:${value}`;
	// Only what this fixture holds (the produce stand only fruit and vegetables, the cooler only drinks...).
	const available = itemCatalog.filter(
		(product) =>
			state.market.unlockedProductIds.includes(product.id) &&
			canShelfHold(shelfId, product.category).ok &&
			!Object.entries(state.shelfAssignments).some(
				([id, assigned]) => assigned === product.id && id !== slotId,
			),
	);
	const categories = [...new Set(available.map((product) => product.category))];
	const products = available.filter((product) => filter === "all" || product.category === filter);
	const fits = (product: (typeof products)[number]) => canShelfHold(shelfId, product.category);
	const cards = products.map((product) =>
		card(product.name, {
			icon: productIcon(product.id),
			eyebrow: (itemCategories.find((item) => item.id === product.category)?.label ?? product.category).toLocaleUpperCase("pt-BR"),
			subtitle: fits(product).ok
				? `Depósito: ${state.inventory[product.id] ?? 0} unid.`
				: fits(product).reason,
			tone: fits(product).ok ? "" : "locked",
			badge: `${product.sellingPrice}`,
			buttons: [
				act("Adicionar produto", "assignProductToShelf", [slotId, product.id, true], {
					enabled: fits(product).ok,
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
				subtitle: "Os produtos deste móvel já estão em outros espaços. Novos produtos chegam com as expansões e os níveis.",
			}),
		);
	return page(route(filter), "Escolher produto", cards, {
		icon: gameIcon("shelf"),
		subtitle: `${shelfName(shelfId, state)}. ${acceptsNow(state, shelfId)}`,
		chips: [
			swap("Todos", route("all"), filter === "all"),
			...categories.map((category) =>
				swap(itemCategories.find((item) => item.id === category)?.label ?? category, route(category), filter === category),
			),
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
	// The shelf window of the game (desktop/pages/shelf-view.ts); the old card pages stay as "shelves" and
	// "shelfcards" for the screens that still link to them.
	store: (state) => shelfViewPage(state, ""),
	shelf: (state, [shelfId = ""]) => shelfViewPage(state, shelfId),
	shelves: (state) => storePage(state),
	shelfcards: shelfPage,
	picker: pickerPage,
	shelforder: orderPage,
};
