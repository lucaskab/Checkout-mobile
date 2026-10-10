import type { MarketEraId } from "@/@types/economy";
import type {
	DeliveryCourier,
	DeliveryItem,
	DeliveryOrder,
	DeliveryOrderStatus,
	DeliveryState,
} from "@/@types/delivery";
import {
	deliveryCouriers,
	deliveryFirstNames,
	deliveryLastInitials,
	deliveryNeighborhoods,
	deliveryNotes,
} from "@/data/delivery-data";
import { getMarketEra } from "@/data/economy";

// Shared rules for the Delivery app (store computer: online orders packed and handed to a motoboy).
// Pure functions only: the store (src/stores/game-store.ts) owns the stock, the coins and the clock.

/** The app opens with the minimercado; mercadinho and supermercado add places for accepted orders. */
export const DELIVERY_UNLOCK_ERA_ID: MarketEraId = "minimercado";
export const OFFER_EXPIRY_MS = 90_000;
export const OFFER_INTERVAL_MS = { min: 75_000, max: 150_000 };
export const MAX_WAITING_OFFERS = 3;
export const PACK_WINDOW_MS = 4 * 60_000;
export const COURIER_ARRIVAL_MS = { min: 15_000, max: 35_000 };
/** The motoboy waits at the door this long before he takes the bag himself (stars −1). */
export const DOOR_WAIT_MS = 60_000;
export const TRIP_BASE_MS = 40_000;
export const TRIP_PER_KM_MS = 25_000;
export const DISTANCE_KM = { min: 0.6, max: 4.5 };
export const MIN_ORDER_LINES = 2;
export const MAX_ORDER_LINES = 7;
export const MAX_UNITS_PER_LINE = 4;
export const FEE_BASE = 4;
export const FEE_PER_KM = 2;
/** Packing slower than this costs stars (the mini-game takes 20–40 s). */
export const SLOW_PACK_SECONDS = 90;
export const VERY_SLOW_PACK_SECONDS = 150;
export const RATING_START = 4.6;
/** The rating moves by 1/20 of the gap to each new delivery (about the average of the last 20). */
export const RATING_WINDOW = 20;
export const LATE_CANCEL_RATING_PENALTY = 0.3;
export const STREAK_BONUS_STEP = 0.1;
export const MAX_STREAK_BONUS = 0.5;
export const MAX_FINISHED_ORDERS = 15;

export const ACTIVE_DELIVERY_STATUSES: DeliveryOrderStatus[] = [
	"aceito",
	"aguardando-moto",
	"moto-na-porta",
	"a-caminho",
];
export const FINISHED_DELIVERY_STATUSES: DeliveryOrderStatus[] = [
	"entregue",
	"expirado",
	"recusado",
	"cancelado",
];

const ORDER_STATUSES: DeliveryOrderStatus[] = [
	...ACTIVE_DELIVERY_STATUSES,
	"oferta",
	...FINISHED_DELIVERY_STATUSES,
];

/** Random numbers in [0, 1) from a seed (the same seed always draws the same numbers). */
export function createDeliveryRandom(seed: number): () => number {
	let state = (Math.floor(seed) * 2246822519) >>> 0;
	return () => {
		state += 0x6d2b79f5;
		let value = state;
		value = Math.imul(value ^ (value >>> 15), value | 1);
		value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
		return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
	};
}

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const clamp01 = (value: number) => clamp(Number.isFinite(value) ? value : 0, 0, 1);
const round2 = (value: number) => Math.round(value * 100) / 100;

function pick<T>(list: readonly T[], random: () => number): T {
	return list[Math.min(list.length - 1, Math.floor(random() * list.length))];
}

function between(random: () => number, min: number, max: number) {
	return min + random() * (max - min);
}

export function createInitialDeliveryState(): DeliveryState {
	return {
		orders: [],
		nextOfferAt: null,
		rating: RATING_START,
		ratings: [],
		streak: 0,
		bestStreak: 0,
		delivered: 0,
		earnings: 0,
		seed: 1,
	};
}

const isRecord = (value: unknown): value is Record<string, unknown> =>
	Boolean(value) && typeof value === "object" && !Array.isArray(value);
const finiteOr = (value: unknown, fallback: number) =>
	typeof value === "number" && Number.isFinite(value) ? value : fallback;

function normalizeItems(value: unknown): DeliveryItem[] {
	if (!Array.isArray(value)) return [];
	return value.flatMap((item) =>
		isRecord(item) && Number.isFinite(item.productId) && Number.isFinite(item.quantity)
			? [{ productId: Number(item.productId), quantity: Math.max(0, Math.floor(Number(item.quantity))) }]
			: [],
	);
}

/** Couriers renamed since older saves: the old id maps to the current profile. */
const LEGACY_COURIER_IDS: Record<string, string> = { preta: "carla" };

/** The saved courier keeps its timings; id, name and colour always come from the current profile. */
function normalizeCourier(value: unknown): DeliveryOrder["courier"] {
	if (!isRecord(value) || typeof value.id !== "string") return undefined;
	const id = LEGACY_COURIER_IDS[value.id] ?? value.id;
	const profile = getCourierProfile(id);
	const courier = value as unknown as NonNullable<DeliveryOrder["courier"]>;
	return profile ? { ...courier, id, name: profile.name, color: profile.color } : courier;
}

function normalizeOrder(value: unknown): DeliveryOrder[] {
	if (!isRecord(value) || typeof value.id !== "string") return [];
	if (!ORDER_STATUSES.includes(value.status as DeliveryOrderStatus)) return [];
	const customer = isRecord(value.customer) ? value.customer : {};
	return [
		{
			...(value as unknown as DeliveryOrder),
			customer: {
				name: typeof customer.name === "string" ? customer.name : "Cliente",
				neighborhood: typeof customer.neighborhood === "string" ? customer.neighborhood : "",
				avatar: finiteOr(customer.avatar, 1),
			},
			note: typeof value.note === "string" ? value.note : "",
			courier: normalizeCourier(value.courier),
			items: normalizeItems(value.items),
			packed: value.packed === undefined ? undefined : normalizeItems(value.packed),
			distanceKm: finiteOr(value.distanceKm, DISTANCE_KM.min),
			fee: finiteOr(value.fee, FEE_BASE),
			itemsValue: finiteOr(value.itemsValue, 0),
			createdAt: finiteOr(value.createdAt, 0),
			expiresAt: finiteOr(value.expiresAt, 0),
		},
	];
}

/** Old saves have no delivery slice: they start with an empty app. Broken orders are dropped. */
export function normalizeDeliveryState(value: unknown): DeliveryState {
	const initial = createInitialDeliveryState();
	if (!isRecord(value)) return initial;
	const ratings = Array.isArray(value.ratings)
		? value.ratings.filter((star): star is number => typeof star === "number" && Number.isFinite(star))
		: [];
	return {
		orders: Array.isArray(value.orders) ? value.orders.flatMap(normalizeOrder) : [],
		nextOfferAt: typeof value.nextOfferAt === "number" && Number.isFinite(value.nextOfferAt) ? value.nextOfferAt : null,
		rating: clamp(finiteOr(value.rating, RATING_START), 1, 5),
		ratings: ratings.slice(-RATING_WINDOW),
		streak: Math.max(0, Math.floor(finiteOr(value.streak, 0))),
		bestStreak: Math.max(0, Math.floor(finiteOr(value.bestStreak, 0))),
		delivered: Math.max(0, Math.floor(finiteOr(value.delivered, 0))),
		earnings: Math.max(0, finiteOr(value.earnings, 0)),
		seed: Math.max(1, Math.floor(finiteOr(value.seed, 1))),
	};
}

export function isDeliveryUnlocked(eraId: MarketEraId) {
	return getMarketEra(eraId).index >= getMarketEra(DELIVERY_UNLOCK_ERA_ID).index;
}

/** Accepted orders the player can carry at once: 2, 3 from the mercadinho, 4 from the supermercado. */
export function getDeliverySlots(eraId: MarketEraId) {
	const index = getMarketEra(eraId).index;
	if (index >= getMarketEra("supermercado").index) return 4;
	if (index >= getMarketEra("mercadinho").index) return 3;
	return 2;
}

export function isActiveDeliveryOrder(order: Pick<DeliveryOrder, "status">) {
	return ACTIVE_DELIVERY_STATUSES.includes(order.status);
}

/** Shelf value of the units (the store passes the price each product has on its shelf now). */
export function getItemsValue(items: DeliveryItem[], priceOf: (productId: number) => number) {
	return Math.round(items.reduce((total, item) => total + item.quantity * priceOf(item.productId), 0));
}

export type DeliveryStockLine = {
	productId: number;
	/** Units in the stockroom now. */
	units: number;
	/** Price on the shelf (or the base price when the product has no shelf). */
	price: number;
};

/**
 * A new order: 2–7 different products, 1–4 units each, never more units than the stockroom holds.
 * Null when the stockroom has fewer than two products to send.
 */
export function createDeliveryOffer(input: {
	id: string;
	now: number;
	random: () => number;
	stock: DeliveryStockLine[];
}): DeliveryOrder | null {
	const pool = input.stock.filter((line) => line.units > 0);
	if (pool.length < MIN_ORDER_LINES) return null;
	const { random } = input;
	const lineCount = Math.min(
		pool.length,
		MIN_ORDER_LINES + Math.floor(random() * (MAX_ORDER_LINES - MIN_ORDER_LINES + 1)),
	);
	const items: DeliveryItem[] = [];
	let itemsValue = 0;
	for (let index = 0; index < lineCount; index++) {
		const [line] = pool.splice(Math.floor(random() * pool.length), 1);
		const wanted = 1 + Math.floor(random() * MAX_UNITS_PER_LINE);
		const quantity = Math.min(wanted, line.units);
		items.push({ productId: line.productId, quantity });
		itemsValue += quantity * line.price;
	}
	const distanceKm = Math.round(between(random, DISTANCE_KM.min, DISTANCE_KM.max) * 10) / 10;
	const customerName = `${pick(deliveryFirstNames, random)} ${pick(deliveryLastInitials, random)}.`;
	const neighborhood = pick(deliveryNeighborhoods, random);
	const avatar = 1 + Math.floor(random() * 999);
	const note = random() < 0.5 ? pick(deliveryNotes, random) : "";
	return {
		id: input.id,
		status: "oferta",
		customer: { name: customerName, neighborhood, avatar },
		note,
		items,
		distanceKm,
		fee: getDeliveryFee(distanceKm),
		itemsValue: Math.round(itemsValue),
		createdAt: input.now,
		expiresAt: input.now + OFFER_EXPIRY_MS,
	};
}

export function getDeliveryFee(distanceKm: number) {
	return Math.ceil(FEE_BASE + FEE_PER_KM * distanceKm);
}

/**
 * Time until the next offer wave: better rating, more orders (a wave every 75–150 s at 4.6 stars). A rush
 * (an event that brings more customers, `customerArrivalMultiplier`) brings the waves closer.
 */
export function getOfferIntervalMs(rating: number, random: () => number, rushMultiplier = 1) {
	const factor = clamp(1 - (rating - RATING_START) * 0.15, 0.8, 1.2);
	const rush = Math.max(1, rushMultiplier);
	return Math.round((between(random, OFFER_INTERVAL_MS.min, OFFER_INTERVAL_MS.max) * factor) / rush);
}

export function getTripMs(distanceKm: number) {
	return Math.round(TRIP_BASE_MS + TRIP_PER_KM_MS * distanceKm);
}

/** A motoboy picked at random; he reaches the store front 15–35 s after the packing. */
export function assignCourier(random: () => number, now: number): DeliveryCourier {
	const profile = pick(deliveryCouriers, random);
	return {
		id: profile.id,
		name: profile.name,
		color: profile.color,
		arriveAt: now + Math.round(between(random, COURIER_ARRIVAL_MS.min, COURIER_ARRIVAL_MS.max)),
	};
}

export function getCourierProfile(id: string | undefined) {
	return deliveryCouriers.find((courier) => courier.id === id);
}

/** Packed units that match the order: never more than ordered or in stock. */
export function clampPackedItems(
	order: Pick<DeliveryOrder, "items">,
	requested: DeliveryItem[],
	stockOf: (productId: number) => number,
): DeliveryItem[] {
	const packed = order.items.flatMap((item) => {
		const asked = requested
			.filter((line) => line.productId === item.productId)
			.reduce((total, line) => total + Math.max(0, Math.floor(line.quantity)), 0);
		const quantity = Math.min(asked, item.quantity, Math.max(0, Math.floor(stockOf(item.productId))));
		return quantity > 0 ? [{ productId: item.productId, quantity }] : [];
	});
	// Substitutes (a product that ran out swapped for a similar one in the packing game) fill the missing units only.
	let missing =
		order.items.reduce((total, item) => total + item.quantity, 0) -
		packed.reduce((total, item) => total + item.quantity, 0);
	for (const line of requested) {
		if (missing <= 0) break;
		if (order.items.some((item) => item.productId === line.productId)) continue;
		if (packed.some((item) => item.productId === line.productId)) continue;
		const quantity = Math.min(Math.max(0, Math.floor(line.quantity)), missing, Math.max(0, Math.floor(stockOf(line.productId))));
		if (quantity > 0) {
			packed.push({ productId: line.productId, quantity });
			missing -= quantity;
		}
	}
	return packed;
}

export function getFillRatio(items: DeliveryItem[], packed: DeliveryItem[]) {
	const ordered = items.reduce((total, item) => total + item.quantity, 0);
	const taken = packed.reduce((total, item) => total + item.quantity, 0);
	return ordered > 0 ? Math.min(1, taken / ordered) : 0;
}

/**
 * Stars of a packed bag: 60 % how complete it is, 40 % the packing quality, minus a little for slow packing.
 * Half steps, 1–5.
 */
export function getPackStars(input: { fillRatio: number; quality: number; seconds: number }) {
	const fillPart = 1 + 4 * clamp01(input.fillRatio);
	const qualityPart = 1 + 4 * clamp01(input.quality);
	let score = 0.6 * fillPart + 0.4 * qualityPart;
	if (input.seconds > VERY_SLOW_PACK_SECONDS) score -= 1;
	else if (input.seconds > SLOW_PACK_SECONDS) score -= 0.5;
	return clamp(Math.round(score * 2) / 2, 1, 5);
}

/** Tip share of the items' value: 0 up to 3.5 stars, then 5 %, 10 % (4.5) and 20 % (5 stars). */
export function getTipRate(stars: number) {
	if (stars >= 5) return 0.2;
	if (stars >= 4.5) return 0.1;
	if (stars >= 4) return 0.05;
	return 0;
}

/** Streak bonus on the payment: 10 % per perfect delivery already in a row, at most 50 %. */
export function getStreakBonusRate(streakBefore: number) {
	return Math.min(MAX_STREAK_BONUS, STREAK_BONUS_STEP * Math.max(0, streakBefore));
}

export type DeliverySettlement = {
	goods: number;
	fee: number;
	tip: number;
	bonus: number;
	total: number;
	stars: number;
};

/** What a delivered order pays: goods × fill + fee + tip (+ streak bonus after a 5-star delivery). */
export function settleDelivery(order: DeliveryOrder, streakBefore: number): DeliverySettlement {
	const stars = order.stars ?? 1;
	const goods = Math.round(order.itemsValue * (order.fillRatio ?? 0));
	const tip = Math.round(order.itemsValue * getTipRate(stars));
	const base = goods + order.fee + tip;
	const bonus = stars >= 5 ? Math.round(base * getStreakBonusRate(streakBefore)) : 0;
	return { goods, fee: order.fee, tip, bonus, total: base + bonus, stars };
}

/** Running rating: each delivery moves it 1/20 of the way to its stars. */
export function applyStarsToRating(rating: number, stars: number) {
	return round2(clamp(rating + (stars - rating) / RATING_WINDOW, 1, 5));
}

export function applyLateCancelToRating(rating: number) {
	return round2(clamp(rating - LATE_CANCEL_RATING_PENALTY, 1, 5));
}

export function pushRating(ratings: number[], stars: number) {
	return [...ratings, stars].slice(-RATING_WINDOW);
}

/** The motoboy's arrival and the hand-over: the bag leaves with the courier (`at`, late or on time). */
function handOver(order: DeliveryOrder, at: number, forced: boolean): DeliveryOrder {
	const courier = order.courier;
	if (!courier) return order;
	const doorSince = courier.doorSince ?? at;
	const late = forced || at - doorSince >= DOOR_WAIT_MS;
	return {
		...order,
		status: "a-caminho",
		stars: late ? Math.max(1, (order.stars ?? 1) - 1) : order.stars,
		courier: { ...courier, doorSince, deliverAt: at + getTripMs(order.distanceKm) },
	};
}

/** The player hands the bag over at the door. Waiting more than DOOR_WAIT_MS costs a star. */
export function handOverOrder(order: DeliveryOrder, now: number): DeliveryOrder {
	if (order.status !== "moto-na-porta") return order;
	return handOver(order, now, false);
}

/**
 * Moves one order forward to what `now` says: offers expire, late packing cancels, the motoboy arrives and
 * waits at the door, and a bag nobody hands over leaves with the courier after DOOR_WAIT_MS.
 * Returns the same object when nothing changed. Payment (status "entregue") is settled by the store.
 */
export function advanceDeliveryOrder(order: DeliveryOrder, now: number): DeliveryOrder {
	let next = order;
	if (next.status === "oferta" && now >= next.expiresAt) next = { ...next, status: "expirado" };
	if (next.status === "aceito" && next.packBy !== undefined && now >= next.packBy)
		next = { ...next, status: "cancelado" };
	if (next.status === "aguardando-moto" && next.courier && now >= next.courier.arriveAt)
		next = {
			...next,
			status: "moto-na-porta",
			courier: { ...next.courier, doorSince: next.courier.arriveAt },
		};
	if (
		next.status === "moto-na-porta" &&
		next.courier?.doorSince !== undefined &&
		now >= next.courier.doorSince + DOOR_WAIT_MS
	)
		next = handOver(next, next.courier.doorSince + DOOR_WAIT_MS, true);
	return next;
}

/** A delivery whose trip is over (status "a-caminho" and the time has come). */
export function isDeliveryArrived(order: DeliveryOrder, now: number) {
	return order.status === "a-caminho" && order.courier?.deliverAt !== undefined && now >= order.courier.deliverAt;
}

export function getNextOrderId(now: number, orders: DeliveryOrder[]) {
	let sequence = orders.length + 1;
	let id = `pedido-${now}-${sequence}`;
	while (orders.some((order) => order.id === id)) id = `pedido-${now}-${++sequence}`;
	return id;
}

/** Keeps every order still in play and the last MAX_FINISHED_ORDERS finished ones (history). */
export function trimDeliveryOrders(orders: DeliveryOrder[]) {
	const finished = orders.filter((order) => FINISHED_DELIVERY_STATUSES.includes(order.status));
	const kept = new Set(finished.slice(-MAX_FINISHED_ORDERS));
	return orders.filter((order) => !FINISHED_DELIVERY_STATUSES.includes(order.status) || kept.has(order));
}

export function replaceDeliveryOrder(orders: DeliveryOrder[], order: DeliveryOrder) {
	return orders.map((item) => (item.id === order.id ? order : item));
}
