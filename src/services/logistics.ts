import type {
	LogisticsState,
	SupplierOrder,
	SupplierOrderStatus,
} from "@/@types/logistics";

const minuteInMilliseconds = 60_000;

export function getSupplierOrderStatus(
	order: SupplierOrder,
	now = Date.now(),
): SupplierOrderStatus {
	if (order.deliveredAt || now >= order.createdAt + order.deliveryDurationMs) {
		return "entregue";
	}

	const progress = (now - order.createdAt) / order.deliveryDurationMs;

	if (progress < 0.25) {
		return "em-producao";
	}

	if (progress < 0.45) {
		return "enviado";
	}

	return "em-transporte";
}

export function getSupplierDeliveryDuration(
	supplierTime: string,
	logistics: LogisticsState,
	now = Date.now(),
) {
	const minutes = Number.parseInt(supplierTime, 10);
	const baseDuration = Math.max(1, Number.isFinite(minutes) ? minutes : 5);
	const hasVip = (logistics.vipExpiresAt ?? 0) > now;
	const hasBoost = (logistics.logisticsBoostExpiresAt ?? 0) > now;
	const multiplier = (hasVip ? 0.9 : 1) * (hasBoost ? 0.7 : 1);

	return Math.round(baseDuration * minuteInMilliseconds * multiplier);
}

export function getOrderRemainingTime(order: SupplierOrder, now = Date.now()) {
	const remaining = Math.max(
		0,
		order.createdAt + order.deliveryDurationMs - now,
	);
	const minutes = Math.floor(remaining / minuteInMilliseconds);
	const seconds = Math.ceil((remaining % minuteInMilliseconds) / 1000);

	return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function getOrderProgress(order: SupplierOrder, now = Date.now()) {
	return Math.min(
		1,
		Math.max(0, (now - order.createdAt) / order.deliveryDurationMs),
	);
}
