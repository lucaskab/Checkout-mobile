import type {
	LogisticsState,
	SupplierOrder,
	SupplierOrderStatus,
} from "@/@types/logistics";

const minuteInMilliseconds = 60_000;
const hourInMilliseconds = 60 * minuteInMilliseconds;
const dayInMinutes = 24 * 60;

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
	const timeParts = [...supplierTime.matchAll(/(\d+)\s*([hm])/gi)];
	const parsedMinutes = timeParts.reduce((total, [, amount, unit]) => {
		const value = Number.parseInt(amount, 10);
		return total + value * (unit.toLowerCase() === "h" ? 60 : 1);
	}, 0);
	const fallbackMinutes = Number.parseInt(supplierTime, 10);
	const baseDuration = Math.max(
		1,
		timeParts.length > 0
			? parsedMinutes
			: Number.isFinite(fallbackMinutes)
				? fallbackMinutes
				: 5,
	);
	const hasBoost = (logistics.logisticsBoostExpiresAt ?? 0) > now;
	const multiplier = hasBoost ? 0.7 : 1;

	return Math.round(baseDuration * minuteInMilliseconds * multiplier);
}

export function formatSupplierDeliveryTime(duration: number) {
	const totalMinutes = Math.max(1, Math.ceil(duration / minuteInMilliseconds));
	const days = Math.floor(totalMinutes / dayInMinutes);
	const remainingAfterDays = totalMinutes % dayInMinutes;
	const hours = Math.floor(remainingAfterDays / 60);
	const minutes = remainingAfterDays % 60;

	if (days > 0) {
		return [
			`${days} ${days === 1 ? "dia" : "dias"}`,
			hours > 0 ? `${hours} h` : null,
			minutes > 0 ? `${minutes} min` : null,
		]
			.filter(Boolean)
			.join(" ");
	}

	if (hours > 0) {
		return minutes > 0 ? `${hours} h ${minutes} min` : `${hours} h`;
	}

	return `${totalMinutes} min`;
}

export function getOrderRemainingTime(order: SupplierOrder, now = Date.now()) {
	const remaining = Math.max(
		0,
		order.createdAt + order.deliveryDurationMs - now,
	);
	if (remaining >= hourInMilliseconds) {
		return formatSupplierDeliveryTime(remaining);
	}

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
