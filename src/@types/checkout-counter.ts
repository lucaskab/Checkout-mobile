import type { CustomerMood } from "./customer-simulation";

// The checkout counter: customers with a full basket wait in line until someone rings them up.
// System: one tap per customer. Simulator (Unity): scan on the belt, key in the total, take the
// card or cash. A working cashier employee serves the line on their own.
export type PaymentMethod = "cartao" | "dinheiro";

export type CheckoutItem = {
	name: string;
	productId: number;
	quantity: number;
	shelfId: string;
	unitPrice: number;
};

export type PendingCheckout = {
	cashGiven: number;
	categories: Record<string, number>;
	createdAt: number;
	customerId: string;
	customerName: string;
	experience: number;
	expiresAt: number;
	id: string;
	items: CheckoutItem[];
	method: PaymentMethod;
	mood: CustomerMood;
	profit: number;
	// Customers first shop; the checkout becomes actionable once they reach the line.
	readyAt: number;
	satisfaction: number;
	soldByProduct: Record<number, number>;
	total: number;
	units: number;
};

export type CheckoutOutcomeStatus = "paid" | "auto" | "left";

export type CheckoutOutcome = {
	charged: number;
	completedAt: number;
	customerId: string;
	customerName: string;
	id: string;
	mistake: "" | "undercharged" | "overcharged";
	status: CheckoutOutcomeStatus;
	tip: number;
	total: number;
};

export type CheckoutCounterState = {
	lost: number;
	nextAutoAt: number | null;
	perfect: number;
	queue: PendingCheckout[];
	recent: CheckoutOutcome[];
	served: number;
};
