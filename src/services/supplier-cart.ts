import type { GameState } from "@/@types/game";
import type {
	PlaceSupplierCartInput,
	SupplierOrder,
	SupplierOrderLine,
} from "@/@types/logistics";
import { getBoxCount, getCaseSize } from "@/data/case-sizes";
import { getMaxBoxesPerOrder } from "@/data/supplier-capacity";
import { itemCatalog } from "@/data/market-products";
import { getActiveGameEventEffects } from "./game-events";
import {
	getSupplierDeliveryDuration,
	getSupplierOrderStatus,
} from "./logistics";
import { getSupplierOrderPrice } from "./production";
import { getShopEffects } from "./shop-effects";
import { getRemainingBoxes, getRemainingUnits } from "./receiving";
import { getFreeBoxPlaces } from "./stockroom";

// One supplier order is one truck. It carries boxes of several products (a cart), up to the truck cap of
// src/data/supplier-capacity.ts, and the trucks on the road are the supplier slots.

/** Below this share of its room a product counts as running out ("Pedir tudo que está acabando"). */
export const LOW_STOCK_SHARE = 0.34;

/** Share of the freight coupon: 10% off the whole truck. */
const FREIGHT_COUPON_KEEP = 0.9;

/** The lines of an order. Orders from before carts have none: their one product becomes the only line. */
export function getOrderLines(order: SupplierOrder): SupplierOrderLine[] {
	if (order.lines?.length) return order.lines;
	const product = itemCatalog.find((item) => item.id === order.productId);
	const caseSize = order.caseSize ?? (product ? getCaseSize(product) : 1);
	return [
		{
			productId: order.productId,
			boxes: order.boxes ?? getBoxCount(order.quantity, caseSize),
			caseSize,
			quantity: order.quantity,
			cost: order.totalCost,
		},
	];
}

/** Boxes on the truck in all. */
export function getOrderBoxes(order: SupplierOrder) {
	return order.boxes ?? getOrderLines(order).reduce((total, line) => total + line.boxes, 0);
}

/** Whether a product is on the truck, whichever line carries it. */
export function orderIncludesProduct(order: SupplierOrder, productId: number) {
	return getOrderLines(order).some((line) => line.productId === productId);
}

/** The order's product when it has one line, else "Pedido · n produtos". */
export function getOrderTitle(order: SupplierOrder) {
	const lines = getOrderLines(order);
	if (lines.length === 1) {
		const product = itemCatalog.find((item) => item.id === lines[0].productId);
		return product?.name ?? "Produto";
	}
	return `Pedido · ${lines.length} produtos`;
}

export function getActiveSupplierOrders(state: Pick<GameState, "logistics">, now = Date.now()) {
	return state.logistics.orders.filter((order) => getSupplierOrderStatus(order, now) !== "entregue");
}

/** What `units` of a product cost the player from the supplier now (events and shop items included). */
export function getSupplierCost(state: GameState, productId: number, units: number, now = Date.now()) {
	const event = getActiveGameEventEffects(state.events, now);
	const shop = getShopEffects(state.shop);
	return Math.ceil(
		getSupplierOrderPrice(productId, units) * event.supplierCostMultiplier * shop.supplierCostMultiplier,
	);
}

/** Delivery time of a truck with this product now (events, shop items and the logistics boost included). */
export function getSupplierDurationMs(state: GameState, supplierTime: string, now = Date.now()) {
	const event = getActiveGameEventEffects(state.events, now);
	const shop = getShopEffects(state.shop);
	return Math.round(
		getSupplierDeliveryDuration(supplierTime, state.logistics, now) *
			event.supplierDurationMultiplier *
			shop.supplierDurationMultiplier,
	);
}

/** Units and boxes of a product already on the road or waiting at the dock. */
export function getSupplierIncoming(state: GameState, productId: number, now = Date.now()) {
	let units = 0;
	let boxes = 0;
	for (const order of getActiveSupplierOrders(state, now))
		for (const line of getOrderLines(order))
			if (line.productId === productId) {
				units += line.quantity;
				boxes += line.boxes;
			}
	for (const delivery of state.receiving?.dock ?? [])
		if (delivery.productId === productId) {
			units += getRemainingUnits(delivery);
			boxes += getRemainingBoxes(delivery).length;
		}
	return { units, boxes };
}

export type SupplierCartQuote = {
	lines: SupplierOrderLine[];
	boxes: number;
	units: number;
	/** The lines before the freight coupon. */
	subtotal: number;
	/** What the truck costs. */
	total: number;
	couponUsed: boolean;
	deliveryDurationMs: number;
	maxBoxes: number;
	/** Why the cart cannot be placed now, or null when it can. */
	reason: string | null;
};

/**
 * What a cart of supplier boxes costs and whether one truck can take it. The same boxes of one product are
 * merged; every line must fit the stockroom, the truck must hold every box, a supplier slot must be free and
 * the coins must cover the total.
 */
export function getSupplierCartQuote(
	state: GameState,
	input: PlaceSupplierCartInput,
	now = Date.now(),
): SupplierCartQuote {
	const maxBoxes = getMaxBoxesPerOrder(state.logistics.supplierOrderSlots);
	const empty = { lines: [], boxes: 0, units: 0, subtotal: 0, total: 0, couponUsed: false, deliveryDurationMs: 0, maxBoxes };
	const fail = (reason: string): SupplierCartQuote => ({ ...empty, reason });

	const requested = Array.isArray(input?.lines) ? input.lines : [];
	if (requested.length === 0) return fail("Escolha pelo menos um produto.");
	const boxesByProduct = new Map<number, number>();
	for (const line of requested) {
		if (!Number.isInteger(line?.productId) || !Number.isInteger(line?.boxes) || line.boxes < 1)
			return fail("Escolha quantas caixas de cada produto.");
		boxesByProduct.set(line.productId, (boxesByProduct.get(line.productId) ?? 0) + line.boxes);
	}

	const lines: SupplierOrderLine[] = [];
	let deliveryDurationMs = 0;
	for (const [productId, boxes] of boxesByProduct) {
		const product = itemCatalog.find((item) => item.id === productId);
		if (
			!product ||
			product.acquisition !== "supplier" ||
			!state.market.unlockedProductIds.includes(productId)
		)
			return fail("Este produto não está disponível para pedido.");
		const caseSize = getCaseSize(product);
		const units = boxes * caseSize;
		const incoming = getSupplierIncoming(state, productId, now);
		const free = getFreeBoxPlaces(
			product,
			state.inventory[productId] ?? 0,
			state.inventoryCapacityLevels[productId],
			incoming.units,
		);
		if (boxes > free)
			return fail(
				boxes === 1
					? `Sem espaço no depósito para 1 caixa de ${product.name}.`
					: `Sem espaço no depósito para ${boxes} caixas de ${product.name}.`,
			);
		const cost = getSupplierCost(state, productId, units, now);
		if (cost <= 0) return fail(`${product.name} não tem preço de fornecedor.`);
		lines.push({ productId, boxes, caseSize, quantity: units, cost });
		deliveryDurationMs = Math.max(deliveryDurationMs, getSupplierDurationMs(state, product.supplierTime, now));
	}

	const boxes = lines.reduce((total, line) => total + line.boxes, 0);
	const units = lines.reduce((total, line) => total + line.quantity, 0);
	const subtotal = lines.reduce((total, line) => total + line.cost, 0);
	const couponUsed = input.useFreightCoupon === true && state.logistics.freightCoupons > 0;
	const total = couponUsed ? Math.ceil(subtotal * FREIGHT_COUPON_KEEP) : subtotal;
	const quote = { lines, boxes, units, subtotal, total, couponUsed, deliveryDurationMs, maxBoxes };

	if (boxes > maxBoxes)
		return { ...quote, reason: `O caminhão leva no máximo ${maxBoxes} caixas. Tire algum produto do pedido.` };
	if (getActiveSupplierOrders(state, now).length >= state.logistics.supplierOrderSlots)
		return { ...quote, reason: "Todos os caminhões estão na estrada. Espere um chegar ou libere mais um." };
	if (total > state.coins) return { ...quote, reason: "Moedas insuficientes para este pedido." };
	return { ...quote, reason: null };
}
