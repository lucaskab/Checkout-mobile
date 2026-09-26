import type {
	CheckoutCounterState,
	CheckoutItem,
	CheckoutOutcome,
	PaymentMethod,
	PendingCheckout,
} from "@/@types/checkout-counter";
import type {
	CustomerArchetype,
	CustomerMood,
} from "@/@types/customer-simulation";

// Shared checkout rules for System, the mobile simulator and desktop.
export const CHECKOUT_READY_DELAY_MS = 10_000;
// One customer every 9 s per unit of cashier efficiency.
export const AUTO_CASHIER_INTERVAL_MS = 9_000;
const MAX_RECENT = 12;

// How long a customer waits in line once they are ready to pay.
export const checkoutPatienceMs: Record<CustomerMood, number> = {
	"com-pressa": 60_000,
	estressado: 70_000,
	feliz: 100_000,
	calmo: 120_000,
};

const cashNotes = [2, 5, 10, 20, 50, 100, 200, 500, 1_000];

type Random = () => number;
function seeded(seed: number): Random {
	let state = (seed * 1597334677) >>> 0;
	return () => {
		state += 0x6d2b79f5;
		let value = state;
		value = Math.imul(value ^ (value >>> 15), value | 1);
		value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
		return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
	};
}

export function createCheckoutCounterState(): CheckoutCounterState {
	return {
		lost: 0,
		nextAutoAt: null,
		perfect: 0,
		queue: [],
		recent: [],
		served: 0,
	};
}

export function normalizeCheckoutCounterState(
	value: Partial<CheckoutCounterState> | undefined,
): CheckoutCounterState {
	const initial = createCheckoutCounterState();
	if (!value || typeof value !== "object") return initial;
	return {
		...initial,
		...value,
		queue: Array.isArray(value.queue) ? value.queue : [],
		recent: Array.isArray(value.recent) ? value.recent : [],
	};
}

// Premium shoppers mostly pay by card, budget shoppers mostly in cash.
export function choosePaymentMethod(
	archetype: CustomerArchetype,
	seed: number,
): PaymentMethod {
	const cardChance: Record<CustomerArchetype, number> = {
		economico: 0.3,
		familia: 0.5,
		impulsivo: 0.6,
		normal: 0.5,
		premium: 0.85,
	};
	return seeded(seed)() < cardChance[archetype] ? "cartao" : "dinheiro";
}

// The smallest banknote (or a round multiple) that covers the purchase.
export function getCashGiven(total: number, seed: number) {
	const note = cashNotes.find((value) => value >= total);
	if (note && (seeded(seed + 7)() < 0.6 || note === total)) return note;
	const step = total > 100 ? 50 : 10;
	return Math.ceil((total + 1) / step) * step;
}

export type CheckoutInput = {
	archetype: CustomerArchetype;
	categories: Record<string, number>;
	customerId: string;
	customerName: string;
	experience: number;
	items: CheckoutItem[];
	mood: CustomerMood;
	profit: number;
	satisfaction: number;
	seed: number;
};

export function createPendingCheckout(
	input: CheckoutInput,
	now: number,
): PendingCheckout | null {
	const items = input.items.filter((item) => item.quantity > 0);
	if (!items.length) return null;
	const total = items.reduce(
		(sum, item) => sum + item.unitPrice * item.quantity,
		0,
	);
	const method = choosePaymentMethod(input.archetype, input.seed);
	const readyAt = now + CHECKOUT_READY_DELAY_MS;
	const soldByProduct: Record<number, number> = {};
	for (const item of items)
		soldByProduct[item.productId] =
			(soldByProduct[item.productId] ?? 0) + item.quantity;
	return {
		cashGiven: method === "dinheiro" ? getCashGiven(total, input.seed) : 0,
		categories: input.categories,
		createdAt: now,
		customerId: input.customerId,
		customerName: input.customerName,
		experience: input.experience,
		expiresAt: readyAt + checkoutPatienceMs[input.mood],
		id: `caixa-${input.seed}`,
		items,
		method,
		mood: input.mood,
		profit: input.profit,
		readyAt,
		satisfaction: input.satisfaction,
		soldByProduct,
		total,
		units: items.reduce((sum, item) => sum + item.quantity, 0),
	};
}

export function enqueueCheckout(
	state: CheckoutCounterState,
	checkout: PendingCheckout,
): CheckoutCounterState {
	if (state.queue.some((item) => item.id === checkout.id)) return state;
	return { ...state, queue: [...state.queue, checkout] };
}

export function getReadyCheckouts(state: CheckoutCounterState, now: number) {
	return state.queue
		.filter((checkout) => checkout.readyAt <= now)
		.sort((a, b) => a.readyAt - b.readyAt);
}

function remember(
	state: CheckoutCounterState,
	outcome: CheckoutOutcome,
): CheckoutOutcome[] {
	return [outcome, ...state.recent].slice(0, MAX_RECENT);
}

export type CheckoutPayment = {
	checkout: PendingCheckout;
	outcome: CheckoutOutcome;
	// Coins actually received for the goods (never more than the real total).
	revenue: number;
	satisfactionDelta: number;
	state: CheckoutCounterState;
	tip: number;
};

// charged: the amount keyed in at the register (defaults to the right total).
export function completeCheckout(
	state: CheckoutCounterState,
	checkoutId: string,
	now: number,
	charged?: number,
	auto = false,
): CheckoutPayment | null {
	const checkout = state.queue.find((item) => item.id === checkoutId);
	if (!checkout) return null;
	const amount = Math.max(0, Math.round(charged ?? checkout.total));
	const mistake: CheckoutOutcome["mistake"] =
		amount < checkout.total
			? "undercharged"
			: amount > checkout.total
				? "overcharged"
				: "";
	// Overcharged customers point it out and pay the right price, annoyed.
	const revenue = Math.min(amount, checkout.total);
	const perfect = !auto && mistake === "";
	const tip = perfect ? Math.max(1, Math.round(checkout.total * 0.06)) : 0;
	const satisfactionDelta = auto
		? 0
		: mistake === "overcharged"
			? -1.5
			: mistake === "undercharged"
				? 0.2
				: 0.4;
	const outcome: CheckoutOutcome = {
		charged: revenue,
		completedAt: now,
		customerId: checkout.customerId,
		customerName: checkout.customerName,
		id: checkout.id,
		mistake,
		status: auto ? "auto" : "paid",
		tip,
		total: checkout.total,
	};
	return {
		checkout,
		outcome,
		revenue,
		satisfactionDelta,
		state: {
			...state,
			perfect: state.perfect + (perfect ? 1 : 0),
			queue: state.queue.filter((item) => item.id !== checkoutId),
			recent: remember(state, outcome),
			served: state.served + 1,
		},
		tip,
	};
}

// Customers who waited too long leave their basket at the register.
export function expireCheckouts(state: CheckoutCounterState, now: number) {
	const expired = state.queue.filter((checkout) => now >= checkout.expiresAt);
	if (!expired.length) return { expired, satisfactionDelta: 0, state };
	let recent = state.recent;
	for (const checkout of expired)
		recent = [
			{
				charged: 0,
				completedAt: now,
				customerId: checkout.customerId,
				customerName: checkout.customerName,
				id: checkout.id,
				mistake: "" as const,
				status: "left" as const,
				tip: 0,
				total: checkout.total,
			},
			...recent,
		].slice(0, MAX_RECENT);
	return {
		expired,
		satisfactionDelta: -3 * expired.length,
		state: {
			...state,
			lost: state.lost + expired.length,
			queue: state.queue.filter((checkout) => now < checkout.expiresAt),
			recent,
		},
	};
}

// A working cashier rings up the oldest ready customer at a steady pace.
export function nextAutoCheckout(
	state: CheckoutCounterState,
	now: number,
	cashierEfficiency: number,
): { checkoutId: string | null; state: CheckoutCounterState } {
	if (cashierEfficiency <= 0)
		return {
			checkoutId: null,
			state: state.nextAutoAt === null ? state : { ...state, nextAutoAt: null },
		};
	const interval = AUTO_CASHIER_INTERVAL_MS / cashierEfficiency;
	const ready = getReadyCheckouts(state, now);
	if (!ready.length)
		return {
			checkoutId: null,
			state: state.nextAutoAt === null ? state : { ...state, nextAutoAt: null },
		};
	if (state.nextAutoAt === null)
		return { checkoutId: null, state: { ...state, nextAutoAt: now + interval } };
	if (now < state.nextAutoAt) return { checkoutId: null, state };
	return {
		checkoutId: ready[0].id,
		state: { ...state, nextAutoAt: now + interval },
	};
}
