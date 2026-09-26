import { expect, test } from "bun:test";
import {
	AUTO_CASHIER_INTERVAL_MS,
	CHECKOUT_READY_DELAY_MS,
	checkoutPatienceMs,
	completeCheckout,
	createCheckoutCounterState,
	createPendingCheckout,
	enqueueCheckout,
	expireCheckouts,
	getCashGiven,
	getReadyCheckouts,
	nextAutoCheckout,
} from "./checkout-counter";

const t0 = 5_000_000;
const basket = (seed = 1, mood = "calmo", archetype = "normal") =>
	createPendingCheckout(
		{
			archetype,
			categories: { padaria: 3 },
			customerId: `cliente-${seed}`,
			customerName: "Ana",
			experience: 12,
			items: [
				{ name: "Pão", productId: 9, quantity: 2, shelfId: "bakery", unitPrice: 4 },
				{ name: "Leite", productId: 5, quantity: 1, shelfId: "dairy", unitPrice: 7 },
			],
			mood,
			profit: 6,
			satisfaction: 70,
			seed,
		},
		t0,
	);

test("a basket waits for the register with its total and payment method", () => {
	const checkout = basket();
	expect(checkout.total).toBe(15);
	expect(checkout.units).toBe(3);
	expect(checkout.readyAt).toBe(t0 + CHECKOUT_READY_DELAY_MS);
	expect(checkout.expiresAt).toBe(checkout.readyAt + checkoutPatienceMs.calmo);
	expect(["cartao", "dinheiro"]).toContain(checkout.method);
	if (checkout.method === "dinheiro") expect(checkout.cashGiven).toBeGreaterThanOrEqual(15);
	expect(createPendingCheckout({ ...basket(), items: [], archetype: "normal", seed: 2, customerId: "x", customerName: "x", categories: {}, experience: 0, mood: "calmo", profit: 0, satisfaction: 0 }, t0)).toBeNull();
});

test("cash is paid with a banknote that covers the total", () => {
	for (const total of [3, 15, 48, 120, 999]) expect(getCashGiven(total, total)).toBeGreaterThanOrEqual(total);
});

test("the right total is a perfect sale with a tip", () => {
	const state = enqueueCheckout(createCheckoutCounterState(), basket());
	const payment = completeCheckout(state, "caixa-1", t0 + 20_000, 15);
	expect(payment.revenue).toBe(15);
	expect(payment.tip).toBeGreaterThan(0);
	expect(payment.outcome.mistake).toBe("");
	expect(payment.state.queue).toEqual([]);
	expect(payment.state.perfect).toBe(1);
	expect(completeCheckout(payment.state, "caixa-1", t0, 15)).toBeNull();
});

test("undercharging loses money and overcharging upsets the customer", () => {
	const state = enqueueCheckout(createCheckoutCounterState(), basket());
	const under = completeCheckout(state, "caixa-1", t0, 10);
	expect(under.revenue).toBe(10);
	expect(under.tip).toBe(0);
	expect(under.outcome.mistake).toBe("undercharged");
	const over = completeCheckout(state, "caixa-1", t0, 30);
	expect(over.revenue).toBe(15);
	expect(over.satisfactionDelta).toBeLessThan(0);
});

test("customers who wait too long leave the line", () => {
	const checkout = basket(3, "com-pressa");
	const state = enqueueCheckout(createCheckoutCounterState(), checkout);
	expect(getReadyCheckouts(state, t0)).toEqual([]);
	expect(getReadyCheckouts(state, checkout.readyAt).length).toBe(1);
	expect(expireCheckouts(state, checkout.expiresAt - 1).expired).toEqual([]);
	const gone = expireCheckouts(state, checkout.expiresAt);
	expect(gone.expired.length).toBe(1);
	expect(gone.satisfactionDelta).toBeLessThan(0);
	expect(gone.state.recent[0].status).toBe("left");
	expect(gone.state.lost).toBe(1);
});

test("a working cashier serves the line at a steady pace", () => {
	const checkout = basket();
	let state = enqueueCheckout(createCheckoutCounterState(), checkout);
	expect(nextAutoCheckout(state, checkout.readyAt, 0).checkoutId).toBeNull();
	let step = nextAutoCheckout(state, checkout.readyAt, 1);
	expect(step.checkoutId).toBeNull();
	state = step.state;
	step = nextAutoCheckout(state, checkout.readyAt + AUTO_CASHIER_INTERVAL_MS, 1);
	expect(step.checkoutId).toBe(checkout.id);
	const payment = completeCheckout(step.state, step.checkoutId, checkout.readyAt, undefined, true);
	expect(payment.outcome.status).toBe("auto");
	expect(payment.tip).toBe(0);
});
