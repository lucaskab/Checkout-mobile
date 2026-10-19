import { afterAll, afterEach, beforeEach, expect, mock, test } from "bun:test";

globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../stores/game-store.ts");
const { getCoachView, getNextGoal, normalizeOnboardingState, ONBOARDING_EXPRESS_MS } = await import("./onboarding.ts");
const { onboardingSteps } = await import("../data/onboarding.ts");
const { itemCatalog } = await import("../data/market-products.ts");

// Test files share the store module: leave it as we found it.
const initial = JSON.stringify(useGameStore.getState());
const realNow = Date.now;
let clock = 1_800_000_000_000;
beforeEach(() => {
	useGameStore.setState(JSON.parse(initial));
	clock = 1_800_000_000_000;
	Date.now = () => clock;
});
afterEach(() => {
	Date.now = realNow;
});
afterAll(() => useGameStore.setState(JSON.parse(initial)));

const store = () => useGameStore.getState();
const step = () => store().onboarding.step;
const tick = (route = "", ms = 1_000) => {
	clock += ms;
	store().processOnboarding(route);
	store().processOnboarding(route);
};
const icons = { lot: "lot", coin: "coin", build: "build", done: "done" };

test("a new game starts the tutorial on the welcome card, with skip", () => {
	expect(store().onboarding.status).toBe("active");
	expect(step()).toBe("boas-vindas");
	const coach = getCoachView(store(), "", clock);
	expect(coach.mode).toBe("modal");
	expect(coach.canSkip).toBe(true);
	expect(coach.path[0]).toBe("Mesinha");
	expect(coach.path.at(-1)).toBe("Rede");
});

test("skipping ends the tutorial and later tips still show", () => {
	expect(store().skipOnboarding()).toBe(true);
	expect(store().onboarding.status).toBe("skipped");
	expect(getCoachView(store(), "", clock).key).toBe("");
	expect(store().skipOnboarding()).toBe(false);
	useGameStore.setState({ market: { ...store().market, level: 3 } });
	tick("");
	expect(store().onboarding.tip).toBe("loja");
	expect(getCoachView(store(), "", clock).isTip).toBe(true);
	expect(store().dismissOnboardingTip()).toBe(true);
	expect(store().onboarding.tipsSeen).toContain("loja");
});

test("the guided first day is finished by playing, step by step", () => {
	store().onboardingNext();
	tick();
	expect(step()).toBe("mesinha");
	// The shelf window opens: next step explains it, closing the window moves on.
	tick("shelf:produce");
	expect(step()).toBe("vitrine");
	tick("shelf:produce");
	expect(step()).toBe("vitrine");
	tick("", 2_000);
	expect(step()).toBe("abrir");
	expect(getCoachView(store(), "", clock).target).toBe("market");
	tick("day");
	expect(step()).toBe("dia-livre");
	expect(getCoachView(store(), "day", clock).target).toBe("action:startDay");
	expect(store().startDay("livre")).toBe(true);
	tick("");
	expect(step()).toBe("primeiro-cliente");

	// The first customer is called in quickly and reaches the register.
	tick("");
	expect(store().market.nextCustomerAt).toBeLessThanOrEqual(clock + 2_500);
	let guard = 0;
	while (store().checkout.queue.length === 0 && guard++ < 120) {
		clock += 1_000;
		store().processNextCustomer();
	}
	expect(store().checkout.queue.length).toBeGreaterThan(0);
	clock = Math.max(clock, ...store().checkout.queue.map((item) => item.readyAt)) + 10;
	tick("");
	expect(step()).toBe("caixa");
	expect(getCoachView(store(), "", clock).target).toBe("fab:caixa|world:checkout");
	const coins = store().coins;
	const first = store().checkout.queue[0];
	expect(store().completeCheckout(first.id, first.total)).toBe(true);
	tick("");
	expect(step()).toBe("estoque");
	// +20 for the first sale on top of what the customer paid.
	expect(store().coins).toBeGreaterThanOrEqual(coins + first.total + 20);
	expect(getCoachView(store(), "", clock).rewardText).toContain("Primeira venda!");

	tick("products");
	expect(step()).toBe("deposito");
	expect(store().onboardingNext()).toBe(true);
	expect(step()).toBe("entregas");
	tick("suppliers");
	expect(step()).toBe("pedir");

	// An order the stockroom has room for: one box of the product with the most free space.
	const product = itemCatalog.find((item) => store().market.unlockedProductIds.includes(item.id) && item.acquisition === "supplier" && item.id === 21)
		?? itemCatalog.find((item) => store().market.unlockedProductIds.includes(item.id) && item.acquisition === "supplier");
	useGameStore.setState({ inventory: { ...store().inventory, [product.id]: 0 } });
	expect(store().placeSupplierCart({ lines: [{ productId: product.id, boxes: 1 }] })).toBe(true);
	tick("suppliers");
	expect(step()).toBe("caminhao");
	// The tutorial's truck is express.
	const order = store().logistics.orders.at(-1);
	expect(order.deliveryDurationMs).toBe(ONBOARDING_EXPRESS_MS);
	clock += ONBOARDING_EXPRESS_MS + 1_000;
	store().processSupplierOrders();
	tick("");
	expect(step()).toBe("descarregar");
	const delivery = store().receiving.dock[0];
	expect(store().unloadDelivery(delivery.id)).toBe(true);
	tick("");
	expect(step()).toBe("missoes");
	tick("missions");
	// Lucas 19/10: where to keep the progress (Opções › Conta); "Depois" moves on.
	expect(step()).toBe("conta");
	const conta = getCoachView(store(), "", clock);
	expect(conta.target).toBe("settings");
	expect(conta.buttonAction).toBe("onboardingNext");
	expect(store().onboardingNext()).toBe(true);
	expect(step()).toBe("objetivo");
	const diamonds = store().logistics.premiumCurrency;
	expect(store().onboardingNext()).toBe(true);
	expect(store().onboarding.status).toBe("done");
	expect(store().logistics.premiumCurrency).toBe(diamonds + 5);
	expect(store().onboarding.completed).toEqual(onboardingSteps.map((item) => item.id));
	// After the tutorial the next big objective shows: the lot of the tenda.
	expect(getNextGoal(store(), icons).text).toContain("Lote");
});

test("a closed market mid-tutorial points back at ABRIR", () => {
	useGameStore.setState({ onboarding: { ...store().onboarding, step: "primeiro-cliente", stepStartedAt: clock } });
	const coach = getCoachView(store(), "", clock);
	expect(coach.target).toBe("market");
	expect(getCoachView(store(), "day", clock).target).toBe("action:startDay");
});

test("replaying the tutorial does not pay its prizes again", () => {
	useGameStore.setState({ onboarding: { ...store().onboarding, status: "done", step: "", completed: onboardingSteps.map((item) => item.id) } });
	expect(store().restartOnboarding()).toBe(true);
	expect(step()).toBe("mesinha");
	useGameStore.setState({ onboarding: { ...store().onboarding, step: "objetivo" } });
	const diamonds = store().logistics.premiumCurrency;
	store().onboardingNext();
	expect(store().logistics.premiumCurrency).toBe(diamonds);
});

test("old saves: a market that already played skips the guided day", () => {
	expect(normalizeOnboardingState(undefined, { level: 4, dayNumber: 3, served: 20 }).status).toBe("done");
	expect(normalizeOnboardingState(undefined, { level: 1, dayNumber: 1, served: 0 }).status).toBe("active");
	expect(normalizeOnboardingState({ status: "active", step: "nope" }, { level: 1, dayNumber: 1, served: 0 }).step).toBe("boas-vindas");
});

test("the day's results interrupt the tutorial with a pointer to collect them", () => {
	useGameStore.setState({
		onboarding: { ...store().onboarding, step: "estoque", stepStartedAt: clock },
		day: { ...store().day, phase: "results" },
	});
	const coach = getCoachView(store(), "", clock);
	expect(coach.key).toBe("fim-do-dia");
	expect(coach.target).toContain("claimDayResult");
});

test("every step has a title and text, and steps that end by tapping a button have one", () => {
	for (const item of onboardingSteps) {
		expect(item.title.length).toBeGreaterThan(0);
		expect(item.text.length).toBeGreaterThan(0);
		if (item.mode === "modal") expect(item.button?.length ?? 0).toBeGreaterThan(0);
	}
});
