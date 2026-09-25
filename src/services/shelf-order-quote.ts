import type { GameState } from "@/@types/game";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import { itemCatalog } from "@/data/market-products";
import { getActiveGameEventEffects } from "./game-events";
import {
	getSupplierDeliveryDuration,
	getSupplierOrderStatus,
} from "./logistics";
import { getSupplierOrderPrice } from "./production";
import { getShopEffects } from "./shop-effects";

export function getShelfOrderQuote(
	state: GameState,
	productId: number,
	quantity: number,
	now = Date.now(),
) {
	const product = itemCatalog.find((item) => item.id === productId);
	if (!product) return null;
	const event = getActiveGameEventEffects(state.events, now);
	const shop = getShopEffects(state.shop.ownedItemIds);
	const activeOrders = state.logistics.orders.filter(
		(order) => getSupplierOrderStatus(order, now) !== "entregue",
	);
	const incoming = activeOrders
		.filter((order) => order.productId === productId)
		.reduce((total, order) => total + order.quantity, 0);
	const capacity = getInventoryCapacity(
		product,
		state.inventoryCapacityLevels[productId],
	);
	const availableSpace = Math.max(
		0,
		capacity - (state.inventory[productId] ?? 0) - incoming,
	);
	const total = Math.ceil(
		getSupplierOrderPrice(productId, quantity) *
			event.supplierCostMultiplier *
			shop.supplierCostMultiplier,
	);
	const duration = Math.round(
		getSupplierDeliveryDuration(product.supplierTime, state.logistics, now) *
			event.supplierDurationMultiplier *
			shop.supplierDurationMultiplier,
	);
	const reason =
		!Number.isInteger(quantity) || quantity < 1
			? "Escolha a quantidade."
			: quantity > availableSpace
				? "Sem espaço suficiente no depósito."
				: activeOrders.length >= state.logistics.supplierOrderSlots
					? "Todas as entregas estão ocupadas."
					: total > state.coins
						? "Moedas insuficientes."
						: null;
	return { total, duration, incoming, availableSpace, capacity, reason };
}

export function getMaxShelfOrderQuantity(state: GameState, productId: number) {
	const quote = getShelfOrderQuote(state, productId, 1);
	if (!quote) return 0;

	let minimum = 0;
	let maximum = quote.availableSpace;
	while (minimum < maximum) {
		const quantity = Math.ceil((minimum + maximum) / 2);
		if (getShelfOrderQuote(state, productId, quantity)?.reason === null) {
			minimum = quantity;
		} else {
			maximum = quantity - 1;
		}
	}

	return minimum;
}
