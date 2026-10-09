import type { DockDelivery, ReceivingState, WarehouseZone } from "@/@types/receiving";

// Shared rules for unloading supplier trucks (System, mobile simulator and desktop).
// A stock clerk unloads one box every STAFF_UNLOAD_INTERVAL_MS per unit of efficiency.
export const STAFF_UNLOAD_INTERVAL_MS = 12_000;
export const MIN_BOX_UNITS = 1;
export const MAX_BOXES = 8;

const zoneByCategory: Record<string, WarehouseZone> = {
	laticinios: "refrigerados",
	congelados: "refrigerados",
	carnes: "refrigerados",
	peixes: "refrigerados",
	frios: "refrigerados",
	queijos: "refrigerados",
	bebidas: "bebidas",
	refrigerantes: "bebidas",
	aguas: "bebidas",
	energeticos: "bebidas",
	hortifruti: "hortifruti",
	organicos: "hortifruti",
	padaria: "hortifruti",
};

export const warehouseZoneLabels: Record<WarehouseZone, string> = {
	refrigerados: "Refrigerados",
	bebidas: "Bebidas",
	hortifruti: "Hortifruti e padaria",
	mercearia: "Mercearia",
};

export function getWarehouseZone(category: string): WarehouseZone {
	return zoneByCategory[category] ?? "mercearia";
}

export function createReceivingState(): ReceivingState {
	return { dock: [], nextStaffAt: null, unloadedUnits: 0 };
}

export function normalizeReceivingState(
	value: Partial<ReceivingState> | undefined,
): ReceivingState {
	const initial = createReceivingState();
	if (!value || typeof value !== "object") return initial;
	return {
		...initial,
		...value,
		dock: Array.isArray(value.dock) ? value.dock : [],
	};
}

// Deliveries from before supplier boxes: units per box, so an order never needs more than MAX_BOXES boxes.
export function getBoxUnits(quantity: number) {
	return Math.max(MIN_BOX_UNITS, Math.ceil(quantity / MAX_BOXES));
}

/** Units in each box of this delivery: the product's supplier box (older deliveries split their units). */
export function getDeliveryBoxUnits(delivery: Pick<DockDelivery, "quantity" | "caseSize">) {
	return delivery.caseSize && delivery.caseSize > 0 ? delivery.caseSize : getBoxUnits(delivery.quantity);
}

export function getRemainingUnits(delivery: DockDelivery) {
	return Math.max(0, delivery.quantity - delivery.unloaded);
}

// The boxes still in the truck (the last one may be partial).
export function getRemainingBoxes(delivery: DockDelivery) {
	const size = getDeliveryBoxUnits(delivery);
	const boxes: number[] = [];
	for (let left = getRemainingUnits(delivery); left > 0; left -= size)
		boxes.push(Math.min(size, left));
	return boxes;
}

// One truck can carry several products (one dock delivery per product): `deliveryId` names each one.
export function addDockDelivery(
	state: ReceivingState,
	order: { id: string; productId: number; quantity: number; caseSize?: number },
	product: { name: string; category: string; caseSize?: number },
	now: number,
	deliveryId = `entrega-${order.id}`,
): ReceivingState {
	if (state.dock.some((item) => item.id === deliveryId)) return state;
	return {
		...state,
		dock: [
			...state.dock,
			{
				arrivedAt: now,
				caseSize: order.caseSize ?? product.caseSize,
				category: product.category,
				id: deliveryId,
				orderId: order.id,
				productId: order.productId,
				productName: product.name,
				quantity: order.quantity,
				unloaded: 0,
				zone: getWarehouseZone(product.category),
			},
		],
	};
}

// Takes up to `units` off the truck (limited by what is left and by `room` in the stockroom).
export function unloadDock(
	state: ReceivingState,
	deliveryId: string,
	units: number,
	room: number,
): { delivery: DockDelivery; moved: number; state: ReceivingState } | null {
	const delivery = state.dock.find((item) => item.id === deliveryId);
	if (!delivery) return null;
	const moved = Math.min(Math.floor(units), getRemainingUnits(delivery), Math.floor(room));
	if (moved <= 0) return null;
	const next = { ...delivery, unloaded: delivery.unloaded + moved };
	return {
		delivery: next,
		moved,
		state: {
			...state,
			dock:
				getRemainingUnits(next) > 0
					? state.dock.map((item) => (item.id === deliveryId ? next : item))
					: state.dock.filter((item) => item.id !== deliveryId),
			unloadedUnits: state.unloadedUnits + moved,
		},
	};
}

// A working stock clerk takes one box of the oldest delivery now and then.
export function nextStaffUnload(
	state: ReceivingState,
	now: number,
	efficiency: number,
): { box: { deliveryId: string; units: number } | null; state: ReceivingState } {
	const delivery = [...state.dock].sort((a, b) => a.arrivedAt - b.arrivedAt)[0];
	if (!delivery || efficiency <= 0)
		return {
			box: null,
			state: state.nextStaffAt === null ? state : { ...state, nextStaffAt: null },
		};
	if (state.nextStaffAt === null)
		return {
			box: null,
			state: { ...state, nextStaffAt: now + STAFF_UNLOAD_INTERVAL_MS / efficiency },
		};
	if (now < state.nextStaffAt) return { box: null, state };
	return {
		box: { deliveryId: delivery.id, units: getRemainingBoxes(delivery)[0] ?? 0 },
		state: { ...state, nextStaffAt: null },
	};
}
