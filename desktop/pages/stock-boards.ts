import { t } from "@/i18n";
import type { ItemDefinition } from "@/@types/item";
import type { SupplierOrder } from "@/@types/logistics";
import { MAX_ITEM_LEVEL } from "@/data/economy";
import {
	getInventoryCapacity,
	getNextInventoryCapacityUpgrade,
} from "@/data/inventory-capacity";
import { itemCatalog, itemCategories } from "@/data/market-products";
import {
	albumCollections,
	getCollectionProgress,
	SALES_TO_COLLECT,
} from "@/data/product-album";
import { getShelfCapacity } from "@/data/shelf-capacity";
import { allFixtures, getShelfSlotIds, maximumSlotsPerShelf } from "@/data/shelf-slots";
import { getNextSupplierOrderSlotUpgrade } from "@/data/supplier-capacity";
import { getOrderBoxes, getOrderLines } from "@/services/supplier-cart";
import { getEarliestInventoryExpiry } from "@/services/inventory-lots";
import { describeProductLock } from "@/services/level-unlocks";
import { getOrderProgress, getOrderSkipCost, getSupplierOrderStatus } from "@/services/logistics";
import { getProductLevel, getProductUpgradeCost } from "@/services/product-levels";
import {
	getMaxShelfOrderBoxes,
	getShelfOrderQuote,
} from "@/services/shelf-order-quote";
import type { Routes } from ".";
import {
	act,
	type BoardStat,
	type BoardTile,
	board,
	type Button,
	button,
	fmt,
	gameIcon,
	go,
	meter,
	page,
	productIcon,
	ratio,
	type State,
	stat,
	swap,
	tile,
} from "../view-kit";

// The stock windows of the game (page.layout = "board", drawn by CheckoutDesktopHUD.Board.cs): every product
// is a tile you can act on right there — order it to fill the depot, put it on its shelf, level it up, give
// it more room — instead of a list of cards. Ideas taken from farm and shop games (Hay Day's barn and
// roadside shop, Township's train and helicopter orders, Supermarket Simulator's ordering tablet): stock
// gauges on each product, warning ribbons ("ACABANDO"), one-tap orders, timers ticking on the trucks,
// and big "do it all" buttons at the bottom.

/** Below this share of its room a product counts as running out. */
const LOW = 0.34;

const categoryLabel = (product: ItemDefinition) =>
	itemCategories.find((item) => item.id === product.category)?.label ?? product.category;

/** Every place where products are sold, slot by slot (to count what is already on the shelves). */
const slotFixture: Record<string, string> = Object.fromEntries(
	allFixtures.flatMap((fixture) =>
		getShelfSlotIds(fixture.id, maximumSlotsPerShelf).map((slotId) => [slotId, fixture.id]),
	),
);

const activeOrders = (state: State, now: number) =>
	state.logistics.orders.filter((order) => getSupplierOrderStatus(order, now) !== "entregue");

const orderEnd = (order: SupplierOrder) => order.createdAt + order.deliveryDurationMs;

const clock = (ms: number) => {
	const seconds = Math.max(0, Math.ceil(ms / 1000));
	const minutes = Math.floor(seconds / 60);
	return minutes >= 60
		? `${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}`
		: `${minutes}:${String(seconds % 60).padStart(2, "0")}`;
};

/** Everything the boards need about one product. */
function productInfo(state: State, product: ItemDefinition, now: number) {
	const amount = state.inventory[product.id] ?? 0;
	const capacityLevel = state.inventoryCapacityLevels[product.id] ?? 0;
	const capacity = getInventoryCapacity(product, capacityLevel);
	const nextCapacity = getNextInventoryCapacityUpgrade(capacityLevel);
	// Trucks carrying this product (a cart may have it on any of its lines).
	const orders = activeOrders(state, now)
		.filter((order) => getOrderLines(order).some((line) => line.productId === product.id))
		.sort((a, b) => orderEnd(a) - orderEnd(b));
	const incoming = orders.reduce(
		(total, order) =>
			total +
			getOrderLines(order)
				.filter((line) => line.productId === product.id)
				.reduce((sum, line) => sum + line.quantity, 0),
		0,
	);
	const slots = Object.entries(state.shelfAssignments)
		.filter(([, id]) => id === product.id)
		.map(([slotId]) => {
			const fixtureId = slotFixture[slotId] ?? "";
			const stock = state.shelfStock[slotId] ?? 0;
			const room = getShelfCapacity(state.shelfUpgradeLevels[fixtureId]);
			return { slotId, fixtureId, stock, room };
		});
	const onShelf = slots.reduce((total, slot) => total + slot.stock, 0);
	const level = getProductLevel(state.productLevels, product.id);
	const upgradeCost = getProductUpgradeCost(state.era.id, level);
	const sold = state.market.soldByProduct?.[product.id] ?? 0;
	const isSupplier = product.acquisition === "supplier";
	// Supplier boxes: the most boxes that fit the racks, the coins and a delivery slot.
	const fillQuantity = isSupplier ? getMaxShelfOrderBoxes(state, product.id) : 0;
	const fillQuote = fillQuantity > 0 ? getShelfOrderQuote(state, product.id, fillQuantity, now) : null;
	// The price and time of ONE box.
	const oneQuote = getShelfOrderQuote(state, product.id, 1, now);
	const expiresAt = getEarliestInventoryExpiry(state.inventoryLots?.[product.id]);
	// The shelf place that misses the most units and can be refilled from the depot.
	const refill = slots
		.map((slot) => ({ ...slot, missing: Math.min(amount, slot.room - slot.stock) }))
		.filter((slot) => slot.missing > 0)
		.sort((a, b) => b.missing - a.missing)[0];
	const share = amount / Math.max(1, capacity);
	const status =
		amount === 0 && incoming === 0
			? "empty"
			: share < LOW && incoming === 0
				? "low"
				: incoming > 0
					? "incoming"
					: amount >= capacity
						? "full"
						: "ok";
	return {
		amount,
		capacity,
		capacityLevel,
		nextCapacity,
		orders,
		incoming,
		slots,
		onShelf,
		level,
		upgradeCost,
		sold,
		isSupplier,
		fillQuantity,
		fillQuote,
		oneQuote,
		expiresAt,
		refill,
		status,
	};
}
type Info = ReturnType<typeof productInfo>;

/** Products the player can sell, low stock first. */
const unlockedProducts = (state: State) =>
	itemCatalog.filter((product) => state.market.unlockedProductIds.includes(product.id));
const needsStock = (info: Info) => info.status === "empty" || info.status === "low";

// ---------------------------------------------------------------- shared buttons
/** "1 caixa" or "N caixas", whole strings so each can be translated. */
const boxesText = (boxes: number) => (boxes === 1 ? "1 caixa" : `${boxes} caixas`);

function fillButton(product: ItemDefinition, info: Info, label?: string): Button {
	if (!info.isSupplier)
		return go("Produzir", "sectors", { icon: gameIcon("conveyor"), variant: "primary" });
	if (info.fillQuantity > 0 && info.fillQuote)
		return act(label ?? `Pedir ${boxesText(info.fillQuantity)}`, "placeSupplierOrder", [{ productId: product.id, boxes: info.fillQuantity }], {
			variant: "coin",
			icon: gameIcon("deliveryTruck"),
			ok: `${boxesText(info.fillQuantity)} de ${product.name} a caminho!`,
			fail: "As condições do pedido mudaram.",
		});
	const reason = info.oneQuote?.reason;
	return button(info.amount >= info.capacity ? "Estoque cheio" : info.incoming > 0 ? "A caminho" : "Sem vaga", {
		icon: gameIcon(info.incoming > 0 ? "deliveryTruck" : "package"),
		variant: "secondary",
		enabled: false,
		fail: reason ?? "",
	});
}

function upgradeButton(state: State, product: ItemDefinition, info: Info): Button | null {
	if (info.upgradeCost === null) return null;
	return act(`Melhorar Nv ${info.level + 1} · ${fmt(info.upgradeCost)}`, "upgradeProduct", [product.id], {
		variant: "success",
		icon: gameIcon("hammer"),
		enabled: state.coins >= info.upgradeCost,
		ok: `${product.name} agora é nível ${info.level + 1}: +10% de lucro por venda!`,
		fail: "Moedas insuficientes.",
	});
}

function capacityButton(state: State, product: ItemDefinition, info: Info): Button | null {
	const next = info.nextCapacity;
	if (!next) return null;
	const room = getInventoryCapacity(product, info.capacityLevel + 1);
	const levelOk = state.market.level >= next.playerLevel;
	return act(`Ampliar para ${room} · ${fmt(next.coinCost)}`, "upgradeInventoryCapacity", [product.id], {
		variant: "coin",
		icon: gameIcon("warehouse"),
		enabled: levelOk && state.coins >= next.coinCost,
		ok: `Agora cabem ${room} ${product.name} no estoque!`,
		fail: levelOk ? "Moedas insuficientes." : `Disponível no nível ${next.playerLevel}.`,
	});
}

function refillButton(product: ItemDefinition, info: Info): Button | null {
	if (!info.refill) return null;
	return act(`Repor prateleira +${info.refill.missing}`, "restockShelf", [{ productId: product.id, shelfId: info.refill.slotId, amount: info.refill.missing }], {
		variant: "primary",
		icon: gameIcon("shelf"),
		ok: `${info.refill.missing} ${product.name} na prateleira!`,
		fail: "Não deu para repor agora.",
	});
}

function expiryText(info: Info, now: number) {
	if (info.expiresAt === null) return "";
	const left = info.expiresAt - now;
	return left <= 0 ? "Um lote venceu" : `Lote mais velho vence em ${clock(left)}`;
}

function productFacts(product: ItemDefinition, info: Info): BoardStat[] {
	return [
		stat(gameIcon("warehouse"), `${info.amount}/${info.capacity}`, "No estoque", needsStock(info) ? "danger" : ""),
		stat(gameIcon("shelf"), String(info.onShelf), "Nas prateleiras"),
		stat(gameIcon("deliveryTruck"), info.incoming ? `+${info.incoming}` : "—", "A caminho", info.incoming ? "info" : ""),
		stat(gameIcon("coin"), `${product.sellingPrice}`, `Venda · lucro +${product.profitPerUnit}`),
		stat(gameIcon("crown"), `${info.level}/${MAX_ITEM_LEVEL}`, "Nível do produto", info.level > 0 ? "gold" : ""),
		stat(gameIcon("medal"), `${Math.min(info.sold, SALES_TO_COLLECT)}/${SALES_TO_COLLECT}`, "Figurinha do álbum", info.sold >= SALES_TO_COLLECT ? "success" : ""),
	];
}

const sticker: Record<string, [string, string]> = {
	empty: ["ESGOTADO", "danger"],
	low: ["ACABANDO", "warning"],
	incoming: ["A CAMINHO", "info"],
	full: ["CHEIO", "success"],
	ok: ["", ""],
};

// ---------------------------------------------------------------- Estoque: every product as a tile
function stockTile(state: State, product: ItemDefinition, now: number, group: string): BoardTile {
	const info = productInfo(state, product, now);
	const isNew = state.market.recentUnlockProductIds.includes(product.id);
	const [label, tone] = isNew ? ["NOVO", "gold"] : sticker[info.status];
	const first = info.orders[0];
	const actions = [
		fillButton(product, info, info.fillQuantity > 0 ? `Encher estoque · ${boxesText(info.fillQuantity)} por ${fmt(info.fillQuote?.total ?? 0)}` : undefined),
		...(info.isSupplier && info.oneQuote && !info.oneQuote.reason
			? [go("Escolher quantidade", `order:${product.id}:1`, { icon: gameIcon("calculator") })]
			: []),
		refillButton(product, info),
		upgradeButton(state, product, info),
		capacityButton(state, product, info),
		...info.slots.slice(0, 1).map((slot) => go("Ver na prateleira", `shelf:${slot.fixtureId}`, { icon: gameIcon("shelf") })),
	].filter((item): item is Button => item !== null);
	return tile(`p${product.id}`, product.name, {
		group,
		icon: productIcon(product.id),
		subtitle: `Vende ${product.sellingPrice} · +${product.profitPerUnit} lucro`,
		sticker: label,
		tone,
		badge: String(info.amount),
		stars: info.level,
		maxStars: MAX_ITEM_LEVEL,
		fill: ratio(info.amount, info.capacity),
		fillText: `${info.amount}/${info.capacity}`,
		timerEnd: first ? orderEnd(first) : 0,
		timerTotal: first ? first.deliveryDurationMs : 0,
		state: isNew || info.status === "empty" ? "ready" : "",
		action: fillButton(product, info),
		detail:
			info.status === "empty"
				? "Acabou! Os clientes que procurarem este produto vão embora sem levar. Peça agora."
				: info.status === "low"
					? "Está acabando. Peça antes que a prateleira fique vazia."
					: info.status === "incoming"
						? "O caminhão já está a caminho. Quando chegar, descarregue na doca."
						: info.level < MAX_ITEM_LEVEL
							? "Estoque em dia. Cada nível do produto dá +10% de lucro por venda."
							: "Produto no nível máximo e estoque em dia.",
		facts: productFacts(product, info),
		lines: [expiryText(info, now)].filter(Boolean),
		actions,
	});
}

function lockedTile(state: State, product: ItemDefinition): BoardTile {
	const lock = describeProductLock(product, state.market.level, state.era.id);
	return tile(`p${product.id}`, product.name, {
		group: "PRÓXIMOS PRODUTOS",
		icon: productIcon(product.id),
		subtitle: categoryLabel(product),
		sticker: lock.levelsLeft === 0 && lock.eraMissing ? "EXPANSÃO" : `NV ${product.unlockLevel}`,
		tone: "locked",
		state: "locked",
		fill: lock.levelsLeft === 0 ? (lock.eraMissing ? 0.9 : 1) : Math.min(1, state.market.level / Math.max(1, product.unlockLevel)),
		fillText: lock.progress,
		detail: `${lock.detail} Vende por ${product.sellingPrice} e dá +${product.xpPerSale} XP por venda.`,
		facts: [
			stat(gameIcon("lock"), `Nv ${product.unlockLevel}`, "Libera no nível"),
			...(lock.eraMissing ? [stat(gameIcon("market"), lock.eraMissing, "Precisa da expansão")] : []),
			stat(gameIcon("coin"), String(product.sellingPrice), "Preço de venda"),
			stat(gameIcon("crown"), `+${product.xpPerSale}`, "XP por venda"),
		],
	});
}

type StockTab = "tudo" | "acabando" | "doca" | "vencendo" | "melhorar" | "ampliar" | "proximos";
/** Old Depósito tabs, now inside the stock window. */
const storageAlias: Record<string, StockTab> = { doca: "doca", prateleiras: "tudo", vencendo: "vencendo", ampliar: "ampliar" };
const EXPIRING_MS = 30 * 60_000;

// Estoque and Depósito were the same thing: one window with the products, the trucks at the dock, what is
// about to spoil and the room of each product.
function stockBoard(state: State, args: string[], aliasOf?: string) {
	const now = Date.now();
	const products = unlockedProducts(state);
	const infos = new Map(products.map((product) => [product.id, productInfo(state, product, now)]));
	const low = products.filter((product) => needsStock(infos.get(product.id)!));
	const dock = state.receiving.dock.filter((delivery) => delivery.quantity > delivery.unloaded);
	const expiring = products.filter((product) => {
		const at = infos.get(product.id)!.expiresAt;
		return at !== null && at - now < EXPIRING_MS;
	});
	const upgradable = products.filter((product) => {
		const cost = infos.get(product.id)!.upgradeCost;
		return cost !== null && state.coins >= cost;
	});
	const expandable = products.filter((product) => {
		const next = infos.get(product.id)!.nextCapacity;
		return next && state.market.level >= next.playerLevel && state.coins >= next.coinCost;
	});
	const locked = itemCatalog
		.filter((product) => !state.market.unlockedProductIds.includes(product.id))
		.sort((a, b) => a.unlockLevel - b.unlockLevel);
	const tabs: { id: StockTab; label: string; icon: string; count: number }[] = [
		{ id: "tudo", label: "Tudo", icon: gameIcon("basket"), count: 0 },
		{ id: "acabando", label: "Acabando", icon: gameIcon("flame"), count: low.length },
		{ id: "doca", label: "Doca", icon: gameIcon("forklift"), count: dock.length },
		{ id: "vencendo", label: "Vencendo", icon: gameIcon("warning"), count: expiring.length },
		{ id: "melhorar", label: "Melhorar", icon: gameIcon("hammer"), count: upgradable.length },
		{ id: "ampliar", label: "Ampliar", icon: gameIcon("warehouse"), count: expandable.length },
		{ id: "proximos", label: "Próximos", icon: gameIcon("lock"), count: 0 },
	];
	const asked = aliasOf ? (storageAlias[args[0] ?? ""] ?? (dock.length ? "doca" : "tudo")) : args[0];
	const active = (tabs.find((tab) => tab.id === asked)?.id ?? "tudo") as StockTab;
	const urgency = (product: ItemDefinition) => {
		const info = infos.get(product.id)!;
		return info.status === "empty" ? 0 : info.status === "low" ? 1 : 2;
	};
	const byCategory = (list: ItemDefinition[]) =>
		[...list].sort(
			(a, b) =>
				categoryLabel(a).localeCompare(categoryLabel(b), "pt-BR") ||
				urgency(a) - urgency(b) ||
				a.name.localeCompare(b.name, "pt-BR"),
		);
	const tiles =
		active === "proximos"
			? locked.slice(0, 24).map((product) => lockedTile(state, product))
			: active === "acabando"
				? [...low].sort((a, b) => urgency(a) - urgency(b)).map((product) => stockTile(state, product, now, "PEÇA ANTES QUE ACABE"))
				: active === "doca"
					? dock.map((delivery) => dockTile(state, delivery))
					: active === "vencendo"
						? expiring.map((product) => rackTile(state, product, now, "VENDA ANTES QUE ESTRAGUE"))
						: active === "melhorar"
							? upgradable.map((product) => stockTile(state, product, now, "DÁ PARA MELHORAR AGORA"))
							: active === "ampliar"
								? expandable.map((product) => rackTile(state, product, now, "DÁ PARA AMPLIAR AGORA"))
								: byCategory(products).map((product) => stockTile(state, product, now, categoryLabel(product).toUpperCase()));
	const albumProgress = albumCollections.map((collection) => getCollectionProgress(collection, state.market.soldByProduct));
	const prizes = albumCollections.filter(
		(collection, index) => albumProgress[index].complete && !(state.albumClaimedIds ?? []).includes(collection.id),
	).length;
	const orderable = low.filter((product) => infos.get(product.id)!.fillQuantity > 0).length;
	const used = products.reduce((total, product) => total + infos.get(product.id)!.amount, 0);
	const room = products.reduce((total, product) => total + infos.get(product.id)!.capacity, 0);
	const share = ratio(used, room);
	return page(`products:${active}`, "Estoque", [], {
		layout: "board",
		icon: gameIcon("warehouse"),
		subtitle: "Peça, descarregue, reponha e amplie seus produtos",
		tabs: tabs.map((tab) => ({
			...swap(tab.label, `products:${tab.id}`, tab.id === active, tab.icon),
			badge: tab.count > 0 ? String(tab.count) : "",
		})),
		board: board(tiles, {
			tint: "3C8D5A",
			backdrop: active === "doca" ? "Game/dock_backdrop" : "Game/wall_backdrop",
			columns: 5,
			stats: [
				stat(gameIcon("basket"), `${products.length}/${itemCatalog.length}`, "Produtos"),
				stat(gameIcon("flame"), String(low.length), "Acabando", low.length ? "danger" : "success"),
				stat(gameIcon("forklift"), String(dock.length), "Na doca", dock.length ? "success" : ""),
			],
			meter: meter("Espaço do estoque", used, room, {
				icon: gameIcon("warehouse"),
				text: `${fmt(used)} de ${fmt(room)} unidades · ${Math.round(share * 100)}% ocupado`,
				tone: share > 0.9 ? "danger" : share > 0.7 ? "warning" : "success",
			}),
			footer: [
				act(orderable > 0 ? `Pedir tudo (${orderable})` : "Nada acabando", "orderLowStock", [], {
					variant: "coin",
					icon: gameIcon("deliveryTruck"),
					enabled: orderable > 0,
					ok: "Pedidos feitos! Os caminhões já saíram.",
					fail: orderable > 0 ? "Sem moedas, sem vagas de entrega ou sem espaço no estoque." : "Nada está acabando agora.",
				}),
				act(dock.length ? `Descarregar tudo (${dock.length})` : "Doca vazia", "unloadAllDeliveries", [], {
					variant: "success",
					icon: gameIcon("forklift"),
					enabled: dock.length > 0,
					ok: "Tudo guardado no estoque!",
					fail: "Sem espaço no estoque para essas caixas.",
				}),
				go(prizes > 0 ? prizes === 1 ? "Álbum · 1 prêmio" : `Álbum · ${prizes} prêmios` : "Álbum", "album", {
					icon: gameIcon("medal"),
					variant: prizes > 0 ? "success" : "secondary",
				}),
			],
			tip: dock.length
				? dock.length === 1
					? "Chegou 1 caminhão na doca! Descarregue para os produtos irem às prateleiras."
					: `Chegaram ${dock.length} caminhões na doca! Descarregue para os produtos irem às prateleiras.`
				: low.length > 0
					? low.length === 1
						? "1 produto está acabando. Peça agora, antes que os clientes saiam de mãos vazias!"
						: `${low.length} produtos estão acabando. Peça agora, antes que os clientes saiam de mãos vazias!`
					: expiring.length
						? expiring.length === 1
							? "1 produto está vencendo. Reponha as prateleiras para vender a tempo."
							: `${expiring.length} produtos estão vencendo. Reponha as prateleiras para vender a tempo.`
						: share > 0.85
							? "O estoque está quase cheio. Amplie os produtos que mais vendem."
							: upgradable.length > 0
								? upgradable.length === 1
									? "Estoque em dia! Você já pode melhorar 1 produto: cada nível dá +10% de lucro."
									: `Estoque em dia! Você já pode melhorar ${upgradable.length} produtos: cada nível dá +10% de lucro.`
								: "Estoque em dia! Venda bastante para liberar novos produtos.",
			empty:
				active === "acabando"
					? "Nada acabando. Seu estoque está em dia!"
					: active === "doca"
						? "Nenhum caminhão na doca. Os pedidos chegam por Entregas."
						: active === "vencendo"
							? "Nada vencendo. Tudo fresquinho!"
							: active === "melhorar"
								? "Junte moedas para melhorar seus produtos."
								: active === "ampliar"
									? "Nenhuma ampliação disponível agora (nível ou moedas)."
									: "Nada por aqui ainda.",
		}),
	});
}

// ---------------------------------------------------------------- the dock and the racks (tabs Doca / Vencendo / Ampliar)
function dockTile(state: State, delivery: State["receiving"]["dock"][number]): BoardTile {
	const left = delivery.quantity - delivery.unloaded;
	const product = itemCatalog.find((item) => item.id === delivery.productId);
	const room = product
		? getInventoryCapacity(product, state.inventoryCapacityLevels[product.id]) - (state.inventory[product.id] ?? 0)
		: 0;
	return tile(`d${delivery.id}`, delivery.productName, {
		group: "NA DOCA · DESCARREGUE",
		icon: productIcon(delivery.productId),
		subtitle: left === 1 ? "1 caixa esperando" : `${left} caixas esperando`,
		sticker: "CHEGOU!",
		tone: "success",
		badge: `x${left}`,
		state: "ready",
		fill: ratio(delivery.unloaded, delivery.quantity),
		fillText: `${delivery.unloaded}/${delivery.quantity} guardadas`,
		action: act("Descarregar", "unloadDelivery", [delivery.id, left], {
			variant: "success",
			icon: gameIcon("forklift"),
			enabled: room > 0,
			ok: `${delivery.productName} guardado no estoque!`,
			fail: "Sem espaço no estoque para este produto. Amplie ou venda um pouco antes.",
		}),
		detail: "O caminhão deixou as caixas na doca. Descarregue para elas irem para o estoque e poderem ir às prateleiras.",
		facts: [
			stat(gameIcon("package"), `x${left}`, "Caixas na doca"),
			stat(gameIcon("warehouse"), String(Math.max(0, room)), "Espaço livre"),
		],
		actions: [
			act(`Descarregar ${left}`, "unloadDelivery", [delivery.id, left], {
				variant: "success",
				icon: gameIcon("forklift"),
				enabled: room > 0,
				ok: `${delivery.productName} guardado no estoque!`,
				fail: "Sem espaço no estoque para este produto.",
			}),
		],
	});
}

function rackTile(state: State, product: ItemDefinition, now: number, group: string): BoardTile {
	const info = productInfo(state, product, now);
	const expiresIn = info.expiresAt === null ? Number.POSITIVE_INFINITY : info.expiresAt - now;
	const expiring = expiresIn < 30 * 60_000;
	const full = info.amount >= info.capacity;
	const [label, tone] = expiring
		? ["VENCENDO", "danger"]
		: full
			? ["CHEIO", "warning"]
			: sticker[info.status];
	const room = info.nextCapacity ? getInventoryCapacity(product, info.capacityLevel + 1) : info.capacity;
	const capacity = capacityButton(state, product, info);
	return tile(`r${product.id}`, product.name, {
		group,
		icon: productIcon(product.id),
		subtitle: info.nextCapacity ? `Espaço ${info.capacity} → ${room}` : "Espaço no máximo",
		sticker: label,
		tone,
		badge: `${info.amount}/${info.capacity}`,
		stars: info.capacityLevel,
		maxStars: 0,
		fill: ratio(info.amount, info.capacity),
		fillText: `${info.amount}/${info.capacity} no estoque`,
		timerEnd: expiring && info.expiresAt ? info.expiresAt : 0,
		timerTotal: expiring ? 30 * 60_000 : 0,
		state: capacity?.enabled && full ? "ready" : "",
		action: capacity ?? button("Máximo", { variant: "secondary", enabled: false, icon: gameIcon("success") }),
		detail: expiring
			? "O lote mais velho está vencendo: leve para a prateleira para vender antes que estrague."
			: full
				? "Espaço lotado. Amplie para pedir caixas maiores e repor menos vezes."
				: "Mais espaço no estoque = pedidos maiores e menos viagens do caminhão.",
		facts: [
			...productFacts(product, info).slice(0, 3),
			stat(gameIcon("warehouse"), info.nextCapacity ? `${info.capacity} → ${room}` : String(info.capacity), "Espaço"),
		],
		lines: [expiryText(info, now)].filter(Boolean),
		actions: [capacity, refillButton(product, info), fillButton(product, info)].filter(
			(item): item is Button => item !== null,
		),
	});
}

// ---------------------------------------------------------------- Entregas: the trucks on the road
// Each truck slot is a lane: a road from the supplier of the product (the meat comes from the frigorífico,
// the bread flour from the mill…) to the supermarket; the truck drives along it like a loading bar.
type Origin = { art: string; name: string };
const origins: Record<string, Origin> = {
	fazenda: { art: "Game/lane_fazenda", name: "Fazenda Sol Nascente" },
	laticinio: { art: "Game/lane_laticinio", name: "Laticínio Vale Verde" },
	frigorifico: { art: "Game/lane_frigorifico", name: "Frigorífico Boi Bom" },
	porto: { art: "Game/lane_porto", name: "Porto dos Pescadores" },
	moinho: { art: "Game/lane_moinho", name: "Moinho Trigo de Ouro" },
	engarrafadora: { art: "Game/lane_engarrafadora", name: "Engarrafadora Fonte Clara" },
	vinicola: { art: "Game/lane_vinicola", name: "Vinícola Serra Alta" },
	fabrica: { art: "Game/lane_fabrica", name: "Fábrica Sabor Bom" },
	distribuidora: { art: "Game/lane_distribuidora", name: "Distribuidora Central" },
};
const originOfCategory: Record<string, keyof typeof origins> = {
	hortifruti: "fazenda", organicos: "fazenda", ovos: "fazenda",
	laticinios: "laticinio", queijos: "laticinio",
	carnes: "frigorifico", frios: "frigorifico",
	peixes: "porto",
	padaria: "moinho",
	bebidas: "engarrafadora", refrigerantes: "engarrafadora", aguas: "engarrafadora", energeticos: "engarrafadora",
	alcoolicos: "vinicola",
	doces: "fabrica", chocolates: "fabrica", bolachas: "fabrica", sazonais: "fabrica", mercearia: "fabrica",
	massas: "fabrica", congelados: "fabrica", sorvetes: "fabrica",
};
const originOf = (category: string) => origins[originOfCategory[category] ?? "distribuidora"];
const vehicleOf = (category: string) =>
	category === "peixes" ? "Game/lane_truck_fish" : category === "sorvetes" || category === "congelados" ? "Game/lane_truck_ice" : "Game/lane_truck";

const statusLabel: Record<string, [string, string, string]> = {
	"em-producao": ["CARREGANDO", "info", "O fornecedor está carregando o caminhão com o seu pedido."],
	enviado: ["SAIU", "info", "O caminhão saiu do fornecedor e pegou a estrada."],
	"em-transporte": ["NA ESTRADA", "warning", "O caminhão está na estrada, chegando ao mercado."],
	entregue: ["CHEGANDO", "success", "O caminhão está estacionando na doca."],
};

const productName = (productId: number) => itemCatalog.find((item) => item.id === productId)?.name ?? "Produto";

/** A truck's name: its product, or how many products it carries. */
function orderTitle(order: SupplierOrder) {
	const lines = getOrderLines(order);
	return lines.length === 1 ? productName(lines[0].productId) : `Pedido · ${lines.length} produtos`;
}

/** What a truck carries, in boxes: "2 cx Tomate, 1 cx Leite e mais 2". */
function orderContents(order: SupplierOrder) {
	const lines = getOrderLines(order);
	const shown = lines.slice(0, 2).map((line) => t(`${line.boxes} cx ${productName(line.productId)}`));
	const rest = lines.length - shown.length;
	return rest > 0 ? `${shown.join(", ")} e mais ${rest}` : shown.join(", ");
}

function orderLane(state: State, order: SupplierOrder, now: number): BoardTile {
	const lines = getOrderLines(order);
	const product = itemCatalog.find((item) => item.id === lines[0]?.productId);
	const category = product?.category ?? "";
	const origin = originOf(category);
	const status = getSupplierOrderStatus(order, now);
	const [label, tone, detail] = statusLabel[status] ?? statusLabel.enviado;
	const tokens = state.logistics.emergencyTokens;
	// "Chegar já": an emergency ticket, or diamonds for the time the truck still has to go (the price falls as it
	// gets closer: src/data/diamond-skip.ts).
	const cost = getOrderSkipCost(order, now);
	const rush = act(tokens > 0 ? "Chegar já · ticket" : `Chegar já · ${cost}`, "deliverOrderInstantly", [order.id], {
		variant: tokens > 0 ? "success" : "gem",
		icon: gameIcon(tokens > 0 ? "ticket" : "diamond"),
		ok: "Vruum! O caminhão chegou na doca!",
		fail: "Sem espaço no estoque agora.",
	});
	const finish: Button | null = null;
	const contents = orderContents(order);
	return tile(`o${order.id}`, orderTitle(order), {
		group: "CAMINHÕES NA ESTRADA",
		icon: product ? productIcon(product.id) : gameIcon("package"),
		subtitle: lines.length === 1 ? `${contents} · ${origin.name}` : contents,
		sticker: label,
		tone,
		badge: `${getOrderBoxes(order)} cx`,
		fill: getOrderProgress(order, now),
		timerEnd: orderEnd(order),
		timerTotal: order.deliveryDurationMs,
		state: "busy",
		action: rush,
		detail,
		actions: [rush, finish].filter((item): item is Button => item !== null),
		origin: origin.art,
		originLabel: origin.name,
		vehicle: vehicleOf(category),
		lane: "road",
	});
}

function dockLane(state: State, delivery: State["receiving"]["dock"][number]): BoardTile {
	const left = delivery.quantity - delivery.unloaded;
	const product = itemCatalog.find((item) => item.id === delivery.productId);
	const origin = originOf(delivery.category || product?.category || "");
	const room = product
		? getInventoryCapacity(product, state.inventoryCapacityLevels[product.id]) - (state.inventory[product.id] ?? 0)
		: 0;
	const unload = act(`Descarregar ${left}`, "unloadDelivery", [delivery.id, left], {
		variant: "success",
		icon: gameIcon("forklift"),
		enabled: room > 0,
		ok: `${delivery.productName} guardado no estoque!`,
		fail: "Sem espaço no estoque para este produto. Amplie ou venda um pouco antes.",
	});
	return tile(`d${delivery.id}`, delivery.productName, {
		group: "NA DOCA · DESCARREGUE",
		icon: productIcon(delivery.productId),
		subtitle: left === 1 ? `1 caixa esperando · ${origin.name}` : `${left} caixas esperando · ${origin.name}`,
		sticker: room > 0 ? "CHEGOU!" : "SEM ESPAÇO",
		tone: room > 0 ? "success" : "danger",
		badge: `x${left}`,
		fill: ratio(delivery.unloaded, delivery.quantity),
		fillText: `${delivery.unloaded}/${delivery.quantity} guardadas`,
		state: "ready",
		action: unload,
		actions: room > 0 ? [unload] : [unload, go("Ampliar o estoque", "!products:ampliar", { icon: gameIcon("warehouse") })],
		origin: origin.art,
		originLabel: origin.name,
		vehicle: vehicleOf(delivery.category || product?.category || ""),
		lane: "dock",
	});
}

function freeLane(index: number, _orderable: number): BoardTile {
	return tile(`slot${index}`, "Caminhão livre", {
		group: "CAMINHÕES NA ESTRADA",
		icon: gameIcon("deliveryTruck"),
		action: go("Fazer pedido", "@shop", { icon: gameIcon("cart"), variant: "primary" }),
		// "Pedir tudo" lives once, in the footer of the board (it was here too, per free truck).
		actions: [go("Fazer pedido", "@shop", { icon: gameIcon("cart"), variant: "primary" })],
		vehicle: "Game/lane_truck",
		lane: "free",
	});
}

function lockedLane(state: State): BoardTile | null {
	const next = getNextSupplierOrderSlotUpgrade(state.logistics.supplierOrderSlots);
	if (!next) return null;
	const levelOk = state.market.level >= next.playerLevel;
	const fail = levelOk ? "Moedas insuficientes." : `Disponível no nível ${next.playerLevel}.`;
	const coins = act(`Liberar · ${fmt(next.coinCost)}`, "upgradeSupplierOrderSlots", ["coins"], {
		variant: "coin",
		icon: gameIcon("coin"),
		enabled: levelOk && state.coins >= next.coinCost,
		ok: `Agora você tem ${next.slots} caminhões!`,
		fail,
	});
	const gems = act(`Liberar · ${next.diamondCost}`, "upgradeSupplierOrderSlots", ["diamonds"], {
		variant: "gem",
		icon: gameIcon("diamond"),
		enabled: levelOk,
		ok: `Agora você tem ${next.slots} caminhões!`,
		fail: levelOk ? "Diamantes insuficientes." : fail,
	});
	return tile("slotnext", "Mais um caminhão", {
		group: "CAMINHÕES NA ESTRADA",
		icon: gameIcon("deliveryTruck"),
		subtitle: levelOk ? "Mais caminhões = mais pedidos ao mesmo tempo" : `Libera no nível ${next.playerLevel}`,
		sticker: levelOk ? "NOVA PISTA" : `NV ${next.playerLevel}`,
		tone: levelOk ? "gold" : "locked",
		state: levelOk ? "" : "locked",
		action: coins,
		actions: [coins, gems],
		vehicle: "Game/lane_truck",
		lane: "locked",
	});
}

type DeliveryTab = "estrada" | "central";

const withBadge = (button: Button, count: number): Button => ({ ...button, badge: count > 0 ? String(count) : "" });

function suppliersBoard(state: State, args: string[]) {
	const now = Date.now();
	const running = activeOrders(state, now).sort((a, b) => orderEnd(a) - orderEnd(b));
	const slots = state.logistics.supplierOrderSlots;
	const suppliers = unlockedProducts(state).filter((product) => product.acquisition === "supplier");
	const infos = new Map(suppliers.map((product) => [product.id, productInfo(state, product, now)]));
	const low = suppliers.filter((product) => needsStock(infos.get(product.id)!));
	const boostLeft = (state.logistics.logisticsBoostExpiresAt ?? 0) - now;
	const dock = state.receiving.dock.filter((delivery) => delivery.quantity > delivery.unloaded);
	const active: DeliveryTab = args[0] === "central" ? "central" : "estrada";
	let tiles: BoardTile[] = [];
	const orderableNow = low.filter((product) => infos.get(product.id)!.fillQuantity > 0).length;
	if (active === "estrada") {
		tiles = [
			...dock.map((delivery) => dockLane(state, delivery)),
			...running.map((order) => orderLane(state, order, now)),
			...Array.from({ length: Math.max(0, slots - running.length) }, (_, index) => freeLane(index, orderableNow)),
			lockedLane(state),
		].filter((item): item is BoardTile => item !== null);
	} else {
		const turbo = act("Ativar turbo · 3", "activateLogisticsBoost", [], {
			variant: "gem",
			icon: gameIcon("diamond"),
			enabled: boostLeft <= 0,
			ok: "Turbo ligado: pedidos novos chegam 30% mais rápido por 15 minutos!",
			fail: boostLeft > 0 ? "O turbo já está ligado." : "Você precisa de 3 diamantes.",
		});
		tiles = [
			tile("turbo", "Turbo logística", {
				group: "CENTRAL LOGÍSTICA",
				icon: gameIcon("lightning"),
				subtitle: "Pedidos chegam 30% mais rápido por 15 min",
				sticker: boostLeft > 0 ? "LIGADO" : "",
				tone: boostLeft > 0 ? "success" : "info",
				timerEnd: boostLeft > 0 ? (state.logistics.logisticsBoostExpiresAt ?? 0) : 0,
				timerTotal: 15 * 60_000,
				state: boostLeft > 0 ? "busy" : "",
				action: turbo,
				detail: "Ligue antes de fazer muitos pedidos: todos os novos chegam bem mais rápido.",
				actions: [turbo],
			}),
			tile("tickets", "Tickets de entrega", {
				group: "CENTRAL LOGÍSTICA",
				icon: gameIcon("ticket"),
				subtitle: "Cada ticket faz um caminhão chegar na hora",
				badge: String(state.logistics.emergencyTokens),
				tone: state.logistics.emergencyTokens > 0 ? "gold" : "",
				detail: "Use em \"Chegar já\" nos caminhões da estrada. Sem ticket, custa 5 diamantes.",
				action: go("Ver caminhões", "~suppliers:estrada", { icon: gameIcon("deliveryTruck") }),
				actions: [go("Ver caminhões", "~suppliers:estrada", { icon: gameIcon("deliveryTruck") })],
			}),
			lockedLane(state),
		].filter((item): item is BoardTile => item !== null);
	}
	const orderable = low.filter((product) => infos.get(product.id)!.fillQuantity > 0).length;
	const next = running[0];
	return page(`suppliers:${active}`, "Entregas", [], {
		layout: "board",
		icon: gameIcon("deliveryTruck"),
		subtitle: "Peça aos fornecedores e acompanhe os caminhões",
		tabs: [
			withBadge(swap("Pistas", "suppliers:estrada", active === "estrada", gameIcon("deliveryTruck")), running.length + dock.length),
			// The shop: the catalog, the cart and the boxes (@shop, drawn by Unity).
			withBadge(go("Fazer pedido", "@shop", { icon: gameIcon("cart") }), low.length),
			withBadge(swap("Central", "suppliers:central", active === "central", gameIcon("lightning")), 0),
		],
		board: board(tiles, {
			tint: "1F6A86",
			backdrop: active === "estrada" ? "" : "Game/truck_back",
			style: active === "estrada" ? "road" : "card",
			columns: active === "estrada" ? 1 : 5,
			// Trucks in use: the meter below shows it (no "Caminhões" stat on top of it).
			stats: [
				stat(gameIcon("ticket"), String(state.logistics.emergencyTokens), "Tickets"),
				stat(gameIcon("lightning"), boostLeft > 0 ? clock(boostLeft) : "Desligado", "Turbo", boostLeft > 0 ? "success" : ""),
			],
			meter: meter("Caminhões em uso", running.length, slots, {
				icon: gameIcon("deliveryTruck"),
				text: next ? `Próxima chegada: ${orderTitle(next)} em ${clock(orderEnd(next) - now)}` : "Todos os caminhões livres: faça pedidos!",
				tone: running.length >= slots ? "warning" : "info",
			}),
			footer: [
				act(orderable > 0 ? `Pedir tudo (${orderable})` : "Nada acabando", "orderLowStock", [], {
					variant: "coin",
					icon: gameIcon("deliveryTruck"),
					enabled: orderable > 0,
					ok: "Pedidos feitos! Os caminhões já saíram.",
					fail: "Sem moedas, sem vagas de entrega ou sem espaço no estoque.",
				}),
				...(dock.length
					? [act(`Descarregar tudo (${dock.length})`, "unloadAllDeliveries", [], {
							variant: "success",
							icon: gameIcon("forklift"),
							ok: "Tudo guardado no estoque!",
							fail: "Sem espaço no estoque para essas caixas.",
						})]
					: [go("Abrir o estoque", "!products", { icon: gameIcon("warehouse") })]),
			],
			tip: dock.length
				? dock.length === 1
					? "1 caminhão na doca! Descarregue para liberar o pátio."
					: `${dock.length} caminhões na doca! Descarregue para liberar o pátio.`
				: running.length >= slots
					? "Todos os caminhões estão na estrada. Libere mais um na Central ou acelere com um ticket."
					: low.length > 0
						? low.length === 1
							? '1 produto precisa de pedido. Use "Pedir tudo" e deixe os caminhões trabalharem!'
							: `${low.length} produtos precisam de pedido. Use "Pedir tudo" e deixe os caminhões trabalharem!`
						: "Caminhões livres e estoque em dia. Bom trabalho!",
			empty: "Nada por aqui ainda.",
		}),
	});
}

export const routes: Routes = {
	products: (state, args) => stockBoard(state, args),
	storage: (state, args) => stockBoard(state, args, "storage"),
	suppliers: suppliersBoard,
};
