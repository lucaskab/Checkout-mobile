import type { GameState } from "@/@types/game";
import { getCaseSize } from "@/data/case-sizes";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import { getMaxBoxesPerOrder } from "@/data/supplier-capacity";
import { itemCatalog } from "@/data/market-products";
import { getActiveGameEventEffects } from "./game-events";
import {
	getSupplierDeliveryDuration,
	getSupplierOrderStatus,
} from "./logistics";
import { getSupplierOrderPrice } from "./production";
import { getShopEffects } from "./shop-effects";
import { getSupplierIncoming } from "./supplier-cart";
import { getFreeBoxPlaces } from "./stockroom";

/**
 * What an order of `boxes` supplier boxes of a product costs and whether it can be placed. Suppliers sell
 * whole boxes (src/data/case-sizes.ts); the stockroom room and the stock are counted in units.
 */
export function getShelfOrderQuote(
	state: GameState,
	productId: number,
	boxes: number,
	now = Date.now(),
) {
	const product = itemCatalog.find((item) => item.id === productId);
	if (!product) return null;
	const caseSize = getCaseSize(product);
	const units = Math.max(0, Math.floor(boxes)) * caseSize;
	const event = getActiveGameEventEffects(state.events, now);
	const shop = getShopEffects(state.shop);
	const activeOrders = state.logistics.orders.filter(
		(order) => getSupplierOrderStatus(order, now) !== "entregue",
	);
	// On the way, plus what already waits at the dock to be unloaded (every product of a cart counts).
	const incoming = getSupplierIncoming(state, productId, now).units;
	const maxBoxes = getMaxBoxesPerOrder(state.logistics.supplierOrderSlots);
	const capacity = getInventoryCapacity(
		product,
		state.inventoryCapacityLevels[productId],
	);
	const availableSpace = Math.max(
		0,
		capacity - (state.inventory[productId] ?? 0) - incoming,
	);
	// Free box places on the stockroom racks, after the stock and what is on the way.
	const availableBoxes = getFreeBoxPlaces(
		product,
		state.inventory[productId] ?? 0,
		state.inventoryCapacityLevels[productId],
		incoming,
	);
	const boxPrice = Math.ceil(
		getSupplierOrderPrice(productId, caseSize) *
			event.supplierCostMultiplier *
			shop.supplierCostMultiplier,
	);
	const total = Math.ceil(
		getSupplierOrderPrice(productId, units) *
			event.supplierCostMultiplier *
			shop.supplierCostMultiplier,
	);
	const duration = Math.round(
		getSupplierDeliveryDuration(product.supplierTime, state.logistics, now) *
			event.supplierDurationMultiplier *
			shop.supplierDurationMultiplier,
	);
	const reason =
		!Number.isInteger(boxes) || boxes < 1
			? "Escolha quantas caixas."
			: boxes > availableBoxes
				? "Sem espaço suficiente no depósito."
				: boxes > maxBoxes
					? `O caminhão leva no máximo ${maxBoxes} caixas por pedido.`
					: activeOrders.length >= state.logistics.supplierOrderSlots
						? "Todas as entregas estão ocupadas."
						: total > state.coins
							? "Moedas insuficientes."
							: null;
	return {
		boxes: Math.max(0, Math.floor(boxes)),
		caseSize,
		units,
		boxPrice,
		total,
		duration,
		incoming,
		availableSpace,
		availableBoxes,
		capacity,
		maxBoxes,
		reason,
	};
}

/** The most boxes of this product that can be ordered now (room, money and free delivery slots). */
export function getMaxShelfOrderBoxes(state: GameState, productId: number) {
	const quote = getShelfOrderQuote(state, productId, 1);
	if (!quote) return 0;

	let minimum = 0;
	let maximum = quote.availableBoxes;
	while (minimum < maximum) {
		const boxes = Math.ceil((minimum + maximum) / 2);
		if (getShelfOrderQuote(state, productId, boxes)?.reason === null) {
			minimum = boxes;
		} else {
			maximum = boxes - 1;
		}
	}

	return minimum;
}
