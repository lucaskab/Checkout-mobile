import type { MarketEraId } from "@/@types/economy";
import { getMarketEra, MAX_ITEM_LEVEL } from "@/data/economy";
import { describeFixtureProducts, getFixtureProducts } from "@/data/fixture-products";
import { getEraOrder, itemCategories, itemCatalog, shelves } from "@/data/market-products";
import {
	getNextShelfCapacityUpgrade,
	getNextShelfSlotUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import {
	getShelfSlotCount,
	getShelfSlotIds,
	getUnlockedPhysicalShelfCount,
	maximumSlotsPerShelf,
	resolveShelfSlotCounts,
	sectorShelves,
} from "@/data/shelf-slots";
import { getFixtureName, getSectorCounter } from "@/data/shelf-types";
import { getOrderRemainingTime } from "@/services/logistics";
import { isMarketBuilding } from "@/services/market-era";
import { getProductLevel, getProductUpgradeCost } from "@/services/product-levels";
import { getShelfCondition, SLOTS_PER_ROW } from "@/services/shelf-care";
import {
	button,
	decorIcon,
	gameIcon,
	page,
	productIcon,
	type Page,
	type ShelfPickView,
	type ShelfSlotView,
	type ShelfView,
	type State,
} from "../view-kit";

// The shelf window of the game (page.layout = "shelf"): the fixture drawn as it stands in the shop, with
// its products on it. The player picks a place to see it up close (stock, price tag, level), drags products
// around (eye level sells more), swaps or removes them, and tidies the fixture up in a little tap game of
// its own kind: wilted leaves in the crates, melted ice in the cooler, frost in the freezer, crumbs in the
// bread basket, smudges on the fridge glass, crooked products on the gondola. Unity draws it
// (CheckoutDesktopHUD.Shelf.cs) and sends the store actions back.

type Look = { kind: string; art: string; tint: string; thumb: string };

/** How a fixture looks in an expansion: the crates and the cooler of the sidewalk, the fridge later. */
function lookOf(fixtureId: string, eraId: MarketEraId): Look {
	const from = (era: MarketEraId) => getEraOrder(eraId) >= getEraOrder(era);
	switch (fixtureId) {
		case "produce":
			return from("banca")
				? { kind: "produce", art: "banca", tint: "4E8A3A", thumb: "shelf-produce" }
				: { kind: "crates", art: "caixotes", tint: "8A5A2B", thumb: "shelf-produce" };
		case "drinks":
			return from("conteiner")
				? { kind: "fridge", art: "geladeira", tint: "1F6A86", thumb: "shelf-cooler" }
				: { kind: "cooler", art: "isopor", tint: "2E8CAE", thumb: "shelf-cooler" };
		case "bakery":
			return from("spati")
				? { kind: "bakery", art: "padaria", tint: "B26A2E", thumb: "shelf-bakery" }
				: { kind: "basket", art: "cesto", tint: "B98642", thumb: "shelf-bakery" };
		case "dairy":
			return { kind: "display", art: "expositor", tint: "2E8CAE", thumb: "shelf-dairy" };
		case "snacks":
			return { kind: "gondola", art: "gondola", tint: "E07B2E", thumb: "shelf-snacks" };
		case "coffee":
			return { kind: "gondola", art: "gondola", tint: "5D8B3A", thumb: "shelf-grocery" };
		case "home":
			return { kind: "gondola", art: "gondola", tint: "3E6FB0", thumb: "shelf-cleaning" };
		case "pizza":
			return { kind: "freezer", art: "freezer", tint: "2C5C9E", thumb: "shelf-freezer" };
		case "icecream":
			return { kind: "chest", art: "chest", tint: "D9578F", thumb: "shelf-freezer" };
		default:
			return { kind: "counter", art: "balcao", tint: "8B5C9E", thumb: fixtureId };
	}
}

/** The care game of each kind of fixture: what gets messy and what the player does about it. */
const care: Record<string, { title: string; verb: string; hint: string; spot: string; top: string; bottom: string }> = {
	crates: { title: "Frescor", verb: "Separar os passados", hint: "Toque nas folhas murchas para tirar o que passou do ponto.", spot: "wilted", top: "Na frente", bottom: "Atrás" },
	produce: { title: "Frescor", verb: "Separar os passados", hint: "Toque nas folhas murchas para tirar o que passou do ponto.", spot: "wilted", top: "Na frente", bottom: "Atrás" },
	cooler: { title: "Gelo", verb: "Repor o gelo", hint: "Toque nas poças de gelo derretido para trocar por gelo novo.", spot: "melt", top: "Em cima do gelo", bottom: "No fundo" },
	fridge: { title: "Limpeza", verb: "Limpar o vidro", hint: "Toque nas manchas do vidro e as bebidas voltam a chamar atenção.", spot: "smudge", top: "Altura dos olhos", bottom: "Prateleira de baixo" },
	display: { title: "Limpeza", verb: "Limpar o expositor", hint: "Toque nas manchas do expositor.", spot: "smudge", top: "Altura dos olhos", bottom: "Prateleira de baixo" },
	basket: { title: "Vitrine", verb: "Ajeitar os pães", hint: "Toque nos farelos para deixar o cesto bonito.", spot: "crumbs", top: "Na frente", bottom: "Atrás" },
	bakery: { title: "Vitrine", verb: "Ajeitar a vitrine", hint: "Toque nos farelos para deixar a vitrine bonita.", spot: "crumbs", top: "Altura dos olhos", bottom: "Prateleira de baixo" },
	gondola: { title: "Arrumação", verb: "Alinhar as frentes", hint: "Toque nos produtos tortos para alinhar a gôndola.", spot: "mess", top: "Altura dos olhos", bottom: "Prateleira de baixo" },
	freezer: { title: "Gelo", verb: "Raspar a geada", hint: "Toque nas placas de gelo para raspar o freezer.", spot: "frost", top: "Altura dos olhos", bottom: "Prateleira de baixo" },
	chest: { title: "Gelo", verb: "Raspar a geada", hint: "Toque nas placas de gelo para raspar o freezer.", spot: "frost", top: "Na frente", bottom: "No fundo" },
	counter: { title: "Limpeza", verb: "Limpar o balcão", hint: "Toque nas manchas do vidro do balcão.", spot: "smudge", top: "Na frente", bottom: "Atrás" },
};

/** Fixtures the player has: the shelves bought (in order) and the counters of the sectors built. */
export function ownedFixtures(state: State) {
	const counts = resolveShelfSlotCounts(state.shelfSlotCounts, state.unlockedShelfSlots);
	return [
		...shelves.slice(0, getUnlockedPhysicalShelfCount(counts)).map((shelf) => shelf.id),
		...sectorShelves.filter((counter) => getShelfSlotCount(counter.id, counts) > 0).map((counter) => counter.id),
	];
}

/** What the customers feel about a price, from how far it is from the suggested one. */
function priceMood(price: number, suggested: number) {
	const difference = (price - suggested) / Math.max(1, suggested);
	if (difference <= -0.1) return { mood: "Barato", tone: "success" };
	if (difference <= 0.05) return { mood: "Justo", tone: "info" };
	if (difference <= 0.18) return { mood: "Caro", tone: "warning" };
	return { mood: "Muito caro", tone: "danger" };
}

function slotView(state: State, fixtureId: string, slotId: string, index: number, open: number): ShelfSlotView {
	const empty: ShelfSlotView = {
		slotId,
		index,
		state: "empty",
		row: index < SLOTS_PER_ROW ? "top" : "bottom",
		productId: 0,
		name: "",
		icon: "",
		stock: 0,
		capacity: getShelfCapacity(state.shelfUpgradeLevels[fixtureId]),
		reserve: 0,
		price: 0,
		minPrice: 0,
		maxPrice: 0,
		suggested: 0,
		cost: 0,
		mood: "",
		moodTone: "",
		level: 0,
		maxLevel: MAX_ITEM_LEVEL,
		upgradeCost: -1,
		restockAmount: 0,
		incoming: "",
		unlockCost: 0,
		unlockLevel: 0,
	};
	if (index >= open) {
		// The next place to open shows the price; the ones after it stay hidden.
		const next = index === open ? getNextShelfSlotUpgrade(open) : null;
		return next
			? { ...empty, state: "locked", unlockCost: next.coinCost, unlockLevel: next.playerLevel }
			: { ...empty, state: "hidden" };
	}
	const product = itemCatalog.find((item) => item.id === state.shelfAssignments[slotId]);
	if (!product) return empty;
	const stock = state.shelfStock[slotId] ?? 0;
	const reserve = state.inventory[product.id] ?? 0;
	const price = state.shelfPrices[slotId] ?? product.sellingPrice;
	const level = getProductLevel(state.productLevels, product.id);
	const mood = priceMood(price, product.suggestedPrice);
	const order = state.logistics.orders
		.filter((item) => item.productId === product.id && item.status !== "entregue")
		.sort((a, b) => a.createdAt + a.deliveryDurationMs - (b.createdAt + b.deliveryDurationMs))[0];
	return {
		...empty,
		state: "product",
		productId: product.id,
		name: product.name,
		icon: productIcon(product.id),
		stock,
		reserve,
		price,
		minPrice: product.minPrice,
		maxPrice: product.maxPrice,
		suggested: product.suggestedPrice,
		cost: product.purchasePrice,
		mood: mood.mood,
		moodTone: mood.tone,
		level,
		upgradeCost: getProductUpgradeCost(state.era.id, level) ?? -1,
		restockAmount: Math.max(0, Math.min(reserve, empty.capacity - stock)),
		incoming: order && reserve === 0 ? `A caminho · ${getOrderRemainingTime(order, Date.now())}` : "",
	};
}

export function shelfViewPage(state: State, requested: string): Page {
	const owned = ownedFixtures(state);
	const fixtureId = owned.includes(requested) ? requested : (owned[0] ?? "produce");
	const counts = resolveShelfSlotCounts(state.shelfSlotCounts, state.unlockedShelfSlots);
	const open = getShelfSlotCount(fixtureId, counts);
	const look = lookOf(fixtureId, state.era.id);
	const kind = care[look.kind] ?? care.gondola;
	const name = getFixtureName(fixtureId, state.era.id);
	const slotIds = getShelfSlotIds(fixtureId, maximumSlotsPerShelf);
	const slots = slotIds.map((slotId, index) => slotView(state, fixtureId, slotId, index, open));
	const onShelves = new Set(Object.values(state.shelfAssignments).filter((id): id is number => typeof id === "number"));
	const picks: ShelfPickView[] = getFixtureProducts(fixtureId, state.market.unlockedProductIds)
		.filter((product) => !onShelves.has(product.id))
		.map((product) => ({
			productId: product.id,
			name: product.name,
			icon: productIcon(product.id),
			category: itemCategories.find((item) => item.id === product.category)?.label ?? product.category,
			reserve: state.inventory[product.id] ?? 0,
			price: product.sellingPrice,
			profit: product.sellingPrice - product.purchasePrice,
		}));
	const slotUpgrade = getNextShelfSlotUpgrade(open);
	const capacityUpgrade = getNextShelfCapacityUpgrade(state.shelfUpgradeLevels[fixtureId]);
	const era = getMarketEra(state.era.id);
	const accepts = describeFixtureProducts(fixtureId, state.market.unlockedProductIds);
	const shelf: ShelfView = {
		id: fixtureId,
		kind: look.kind,
		art: `Fixtures/${look.art}`,
		tint: look.tint,
		name,
		accepts: accepts ? `Aceita: ${accepts}.` : "Ainda não há produto liberado para este móvel.",
		condition: Math.round(getShelfCondition(state.shelfCare, fixtureId)),
		careTitle: kind.title,
		careVerb: kind.verb,
		careHint: kind.hint,
		careSpot: kind.spot,
		rowTop: `${kind.top} · vende mais`,
		rowBottom: `${kind.bottom} · vende menos`,
		slotCount: open,
		expandCost: slotUpgrade?.coinCost ?? 0,
		expandLevel: slotUpgrade?.playerLevel ?? 0,
		capacity: getShelfCapacity(state.shelfUpgradeLevels[fixtureId]),
		capacityNext: capacityUpgrade?.capacity ?? 0,
		capacityCost: capacityUpgrade?.coinCost ?? 0,
		capacityLevel: capacityUpgrade?.playerLevel ?? 0,
		stallNote: isMarketBuilding(state.era.id)
			? ""
			: `${era.name}: só cabem ${era.productSlots} produtos à mostra. Ficam à venda os primeiros com estoque, na ordem das prateleiras.`,
		slots,
		picks,
	};
	// The fixtures the player has, as tabs (a "!" asks for care or for stock).
	const tabs = owned.map((id) => {
		const fixtureLook = lookOf(id, state.era.id);
		const condition = getShelfCondition(state.shelfCare, id);
		const idsHere = getShelfSlotIds(id, getShelfSlotCount(id, counts));
		const emptyStock = idsHere.some((slotId) => state.shelfAssignments[slotId] && (state.shelfStock[slotId] ?? 0) === 0);
		return button(getFixtureName(id, state.era.id), {
			route: `~shelf:${id}`,
			variant: "secondary",
			active: id === fixtureId,
			icon: decorIcon(getSectorCounter(id) ? id : fixtureLook.thumb),
			badge: condition < 60 || emptyStock ? "!" : "",
		});
	});
	tabs.push(
		button("Nova prateleira", {
			route: "!loja:moveis",
			variant: "secondary",
			icon: gameIcon("construction"),
		}),
	);
	return page(`shelf:${fixtureId}`, name, [], {
		layout: "shelf",
		icon: decorIcon(getSectorCounter(fixtureId) ? fixtureId : look.thumb),
		subtitle: shelf.accepts,
		tabs,
		shelf,
	});
}
