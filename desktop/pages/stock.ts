import type { ItemDefinition, ItemRarity } from "@/@types/item";
import {
	getInventoryCapacity,
	getNextInventoryCapacityUpgrade,
} from "@/data/inventory-capacity";
import { itemCatalog, itemCategories } from "@/data/market-products";
import { getEarliestInventoryExpiry } from "@/services/inventory-lots";
import {
	formatSupplierDeliveryTime,
	getOrderRemainingTime,
	getSupplierOrderStatus,
} from "@/services/logistics";
import { getShelfOrderQuote } from "@/services/shelf-order-quote";
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

type ProductFilter = "todos" | "desbloqueados" | "bloqueados";

const productFilters: { id: ProductFilter; label: string }[] = [
	{ id: "todos", label: "Todos" },
	{ id: "desbloqueados", label: "Desbloqueados" },
	{ id: "bloqueados", label: "Bloqueados" },
];

const rarityTone: Record<ItemRarity, string> = {
	colecionavel: "info",
	comum: "",
	epico: "info",
	incomum: "success",
	lendario: "warning",
	luxo: "warning",
	raro: "info",
};

const formatRarity = (rarity: ItemRarity) =>
	rarity.charAt(0).toUpperCase() + rarity.slice(1);

const categoryLabel = (product: ItemDefinition) =>
	itemCategories.find((item) => item.id === product.category)?.label ??
	product.category;

const findProduct = (id: string | undefined) =>
	itemCatalog.find((product) => product.id === Number(id));

function incomingOrder(state: State, productId: number, now: number) {
	return state.logistics.orders.find(
		(order) =>
			order.productId === productId &&
			getSupplierOrderStatus(order, now) !== "entregue",
	);
}

function capacityOf(state: State, product: ItemDefinition) {
	return getInventoryCapacity(product, state.inventoryCapacityLevels[product.id]);
}

// Lots are not shown in RN; kept as a short info line only.
function expiryLine(state: State, productId: number, now: number) {
	const expiresAt = getEarliestInventoryExpiry(state.inventoryLots?.[productId]);
	if (expiresAt === null) return [];
	const minutes = Math.max(0, Math.round((expiresAt - now) / 60_000));
	return [
		minutes >= 60
			? `Lote mais antigo vence em ${Math.floor(minutes / 60)}h${String(minutes % 60).padStart(2, "0")}`
			: `Lote mais antigo vence em ${minutes} min`,
	];
}

function lockedProductCard(state: State, product: ItemDefinition): Card {
	const level = state.market.level;
	const levelsLeft = product.unlockLevel - level;
	return card(product.name, {
		eyebrow: categoryLabel(product),
		icon: productIcon(product.id),
		badge: `Nv ${product.unlockLevel}`,
		tone: "locked",
		progress: Math.min(1, level / product.unlockLevel),
		lines: [
			`${product.sellingPrice} por venda · +${product.xpPerSale} XP`,
			levelsLeft > 0
				? `Faltam ${levelsLeft} ${levelsLeft === 1 ? "nível" : "níveis"} para desbloquear`
				: "Pronto para desbloquear",
		],
	});
}

function unlockedProductCard(state: State, product: ItemDefinition, now: number): Card {
	const amount = state.inventory[product.id] ?? 0;
	const capacity = capacityOf(state, product);
	const order = incomingOrder(state, product.id, now);
	return card(product.name, {
		eyebrow: categoryLabel(product),
		icon: productIcon(product.id),
		badge: formatRarity(product.rarity),
		tone: rarityTone[product.rarity],
		progress: Math.min(1, amount / capacity),
		lines: [
			`Venda ${product.sellingPrice} · Lucro +${product.profitPerUnit} · XP +${product.xpPerSale}`,
			`Depósito: ${amount} / ${capacity} unid.`,
			...(order
				? [`A caminho · +${order.quantity} unid. · ${getOrderRemainingTime(order, now)}`]
				: []),
			...expiryLine(state, product.id, now),
		],
		buttons: [
			go("Ampliar", `capacity:${product.id}`, { icon: gameIcon("warehouse") }),
			go("Abastecer", `order:${product.id}:1`, {
				icon: gameIcon("deliveryTruck"),
				variant: "primary",
			}),
		],
	});
}

function productsPage(state: State, args: string[]) {
	const filter = (productFilters.find((item) => item.id === args[0])?.id ??
		"todos") as ProductFilter;
	const now = Date.now();
	const unlocked = state.market.unlockedProductIds;
	const list = itemCatalog
		.filter((product) => {
			const isUnlocked = unlocked.includes(product.id);
			if (filter === "desbloqueados") return isUnlocked;
			if (filter === "bloqueados") return !isUnlocked;
			return true;
		})
		.sort(
			(first, second) =>
				first.unlockLevel - second.unlockLevel ||
				first.name.localeCompare(second.name, "pt-BR"),
		);
	return page(
		`products:${filter}`,
		"Estoque",
		list.map((product) =>
			unlocked.includes(product.id)
				? unlockedProductCard(state, product, now)
				: lockedProductCard(state, product),
		),
		{
			subtitle: `Catálogo por nível · ${list.length} itens`,
			icon: gameIcon("basket"),
			chips: productFilters.map((item) =>
				swap(item.label, `products:${item.id}`, item.id === filter),
			),
		},
	);
}

function capacityPage(state: State, args: string[]) {
	const product = findProduct(args[0]);
	if (!product) return page(`capacity:${args[0]}`, "Produto não encontrado", []);
	const marketLevel = state.market.level;
	const upgradeLevel = state.inventoryCapacityLevels[product.id] ?? 0;
	const capacity = getInventoryCapacity(product, upgradeLevel);
	const nextUpgrade = getNextInventoryCapacityUpgrade(upgradeLevel);
	const amount = state.inventory[product.id] ?? 0;
	const cards: Card[] = [
		card("Capacidade atual", {
			icon: gameIcon("package"),
			tone: "info",
			lines: [`${amount} / ${capacity} unidades`],
			progress: ratio(amount, capacity),
		}),
	];
	if (nextUpgrade) {
		const hasRequiredLevel = marketLevel >= nextUpgrade.playerLevel;
		const hasEnoughCoins = state.coins >= nextUpgrade.coinCost;
		const nextCapacity = getInventoryCapacity(product, upgradeLevel + 1);
		const missing = nextUpgrade.playerLevel - marketLevel;
		cards.push(
			card(`Amplie para ${nextCapacity} unidades`, {
				icon: gameIcon("warehouse"),
				tone: hasRequiredLevel ? "" : "locked",
				badge: `Nv ${nextUpgrade.playerLevel}`,
				lines: [
					`Disponível no nível ${nextUpgrade.playerLevel}.`,
					"Mais espaço para pedidos e produção.",
					...(!hasRequiredLevel
						? [`Faltam ${missing} ${missing === 1 ? "nível" : "níveis"}.`]
						: []),
				],
				buttons: [
					act(
						`Ampliar por ${nextUpgrade.coinCost.toLocaleString("pt-BR")}`,
						"upgradeInventoryCapacity",
						[product.id],
						{
							variant: "coin",
							icon: gameIcon("coin"),
							enabled: hasRequiredLevel && hasEnoughCoins,
							ok: `Capacidade ampliada para ${nextCapacity} unidades.`,
							fail: !hasRequiredLevel
								? `Alcance o nível ${nextUpgrade.playerLevel} para ampliar este estoque.`
								: "Você não tem moedas suficientes para esta ampliação.",
						},
					),
				],
			}),
		);
	} else {
		cards.push(
			card("Este item já está na capacidade máxima.", {
				icon: gameIcon("success"),
				tone: "success",
			}),
		);
	}
	return page(`capacity:${product.id}`, `Estoque de ${product.name}`, cards, {
		subtitle: "Escolha quais itens terão mais espaço no seu depósito.",
		icon: productIcon(product.id),
	});
}

function storageProductCard(state: State, product: ItemDefinition, now: number): Card {
	const quantity = state.inventory[product.id] ?? 0;
	const capacity = capacityOf(state, product);
	const quote = getShelfOrderQuote(state, product.id, 1, now);
	const waitTime = quote
		? `~${formatSupplierDeliveryTime(quote.duration)}`
		: product.supplierTime;
	const order = incomingOrder(state, product.id, now);
	const deliveryTime = order ? getOrderRemainingTime(order, now) : waitTime;
	const isSupplier = product.acquisition === "supplier";
	return card(product.name, {
		eyebrow: categoryLabel(product),
		icon: productIcon(product.id),
		badge: `${quantity}/${capacity}`,
		tone: quantity === 0 ? "warning" : "",
		progress: ratio(quantity, capacity),
		lines: [
			`${quantity} / ${capacity} no depósito`,
			isSupplier
				? order
					? `Chega em ${deliveryTime}`
					: `Fornecedor · ${deliveryTime}`
				: "Produção própria",
			...expiryLine(state, product.id, now),
		],
		buttons: [
			...(isSupplier
				? [
						go("Pedir ao fornecedor", `order:${product.id}:1`, {
							icon: gameIcon("deliveryTruck"),
							variant: "primary",
						}),
					]
				: []),
			go("Expandir", `capacity:${product.id}`, { icon: gameIcon("warehouse") }),
		],
	});
}

function unlockedProducts(state: State) {
	return itemCatalog.filter((product) =>
		state.market.unlockedProductIds.includes(product.id),
	);
}

function storagePage(state: State, args: string[]) {
	const now = Date.now();
	const products = unlockedProducts(state);
	const categories = [
		{ id: "todos", label: "Todos" },
		...itemCategories.filter((category) =>
			products.some((product) => product.category === category.id),
		),
	];
	const active = categories.some((item) => item.id === args[0]) ? args[0] : "todos";
	const visible = products.filter(
		(product) => active === "todos" || product.category === active,
	);
	const totalQuantity = products.reduce(
		(total, product) => total + (state.inventory[product.id] ?? 0),
		0,
	);
	const totalCapacity = products.reduce(
		(total, product) => total + capacityOf(state, product),
		0,
	);
	const hero = card("Meu depósito", {
		eyebrow: "CHECKOUT MARKET",
		subtitle: "Produtos, quantidades e entregas em um só lugar.",
		icon: gameIcon("warehouse"),
		tone: "info",
		progress: ratio(totalQuantity, totalCapacity),
		lines: [
			`Espaço ocupado: ${fmt(totalQuantity)} / ${fmt(totalCapacity)} unid.`,
			`${products.length} produtos disponíveis`,
		],
		buttons: [
			go("Expandir espaço", "storageexpand", {
				icon: gameIcon("warehouse"),
				variant: "coin",
			}),
		],
	});
	const cards = visible.length
		? visible.map((product) => storageProductCard(state, product, now))
		: [card("Nenhum produto nesta categoria.", { tone: "locked" })];
	return page(`storage:${active}`, "Depósito", [hero, ...cards], {
		subtitle: "Acompanhe o estoque e o prazo de cada fornecedor.",
		icon: gameIcon("warehouse"),
		chips: categories.map((item) =>
			swap(item.label, `storage:${item.id}`, item.id === active),
		),
	});
}

function storageExpandPage(state: State) {
	const cards = unlockedProducts(state).map((product) => {
		const level = state.inventoryCapacityLevels[product.id] ?? 0;
		const upgrade = getNextInventoryCapacityUpgrade(level);
		const capacity = getInventoryCapacity(product, level);
		const nextCapacity = upgrade ? getInventoryCapacity(product, level + 1) : capacity;
		const isLocked = Boolean(upgrade && state.market.level < upgrade.playerLevel);
		return card(product.name, {
			icon: productIcon(product.id),
			badge: upgrade
				? isLocked
					? `Nv. ${upgrade.playerLevel}`
					: upgrade.coinCost.toLocaleString("pt-BR")
				: "Máx",
			tone: upgrade ? (isLocked ? "locked" : "") : "success",
			lines: [
				upgrade
					? `${capacity} → ${nextCapacity} unid.`
					: `${capacity} unid. · capacidade máxima`,
			],
			buttons: upgrade
				? [go("Expandir", `capacity:${product.id}`, { icon: gameIcon("warehouse") })]
				: [],
		});
	});
	return page("storageexpand", "Expandir depósito", cards, {
		subtitle: "Escolha uma prateleira para aumentar a capacidade daquele produto.",
		icon: gameIcon("warehouse"),
	});
}

export const routes: Routes = {
	products: productsPage,
	capacity: capacityPage,
	storage: storagePage,
	storageexpand: storageExpandPage,
};
