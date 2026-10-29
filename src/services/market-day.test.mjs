import { expect, test } from "bun:test";
import {
	advanceMarketDay,
	closeMarketDay,
	createDayOffers,
	createInitialDayState,
	DAY_DURATION_MS,
	getContractProgress,
	getDayGrade,
	getDayScore,
	INITIAL_LOYALTY,
	normalizeDayState,
	recordDayCustomer,
	startDay,
} from "./market-day";

const catalog = [
	{
		id: 1,
		name: "Leite",
		category: "laticinios",
		categoryLabel: "Laticínios",
		purchasePrice: 3,
		sellingPrice: 6,
	},
	{
		id: 2,
		name: "Iogurte",
		category: "laticinios",
		categoryLabel: "Laticínios",
		purchasePrice: 2,
		sellingPrice: 5,
	},
	{
		id: 3,
		name: "Pão francês",
		category: "padaria",
		categoryLabel: "Padaria",
		purchasePrice: 1,
		sellingPrice: 2,
	},
	{
		id: 4,
		name: "Suco",
		category: "bebidas",
		categoryLabel: "Bebidas",
		purchasePrice: 3,
		sellingPrice: 7,
	},
	{
		id: 5,
		name: "Queijo",
		category: "laticinios",
		categoryLabel: "Laticínios",
		purchasePrice: 8,
		sellingPrice: 14,
	},
];
const context = {
	catalog,
	shelfProductIds: [1, 3, 4],
	storageProductIds: [5],
	unlockedProductIds: [1, 2, 3, 4, 5],
};
const t0 = 1_000_000;

function openDay(contractIndex = 0) {
	const day = createInitialDayState(3, context);
	return startDay(day, day.offers[contractIndex].id, t0);
}

test("offers one easy, one medium and one hard contract every day", () => {
	const offers = createDayOffers(4, 5, context);
	expect(offers.map((offer) => offer.difficulty)).toEqual([1, 2, 3]);
	expect(new Set(offers.map((offer) => offer.id)).size).toBe(3);
	for (const offer of offers) {
		expect(offer.target).toBeGreaterThan(0);
		expect(offer.reward.coins).toBeGreaterThan(0);
	}
	// Diamonds are the store's currency: no contract pays them, the hard one pays more coins instead.
	for (const offer of offers) expect(offer.reward.diamonds).toBe(0);
	expect(offers[2].reward.coins).toBeGreaterThan(offers[0].reward.coins);
});

test("a day runs for five minutes and only opens from planning", () => {
	const day = openDay();
	expect(day.phase).toBe("open");
	expect(day.endsAt).toBe(t0 + DAY_DURATION_MS);
	expect(startDay(day, null, t0)).toBeNull();
	expect(startDay(createInitialDayState(1), "unknown", t0)).toBeNull();
});

test("contract progress follows the day's sales", () => {
	let day = openDay();
	const revenueContract = { ...day.offers[0], kind: "revenue", target: 100 };
	day = { ...day, contract: revenueContract };
	day = recordDayCustomer(day, {
		revenue: 60,
		profit: 20,
		units: 3,
		satisfaction: 80,
		categories: { padaria: 3 },
	});
	expect(getContractProgress(day.contract, day.stats).completed).toBe(false);
	day = recordDayCustomer(day, {
		revenue: 50,
		profit: 20,
		units: 1,
		satisfaction: 70,
		categories: { bebidas: 1 },
	});
	const progress = getContractProgress(day.contract, day.stats);
	expect(progress.completed).toBe(true);
	expect(progress.current).toBe(110);
	expect(day.stats.soldByCategory).toEqual({ padaria: 3, bebidas: 1 });
});

test("closing the day grades it and grants the contract reward only when completed", () => {
	let day = openDay();
	day = {
		...day,
		contract: { ...day.offers[0], kind: "customers", target: 2 },
	};
	for (let index = 0; index < 3; index++)
		day = recordDayCustomer(day, {
			revenue: 30,
			profit: 10,
			units: 2,
			satisfaction: 90,
			categories: {},
		});
	const closed = closeMarketDay(day, t0 + DAY_DURATION_MS, 3);
	expect(closed.phase).toBe("results");
	expect(closed.result.contractCompleted).toBe(true);
	expect(closed.result.total.coins).toBe(
		day.contract.reward.coins + closed.result.bonus.coins,
	);
	expect(["S", "A"]).toContain(closed.result.grade);

	const failed = closeMarketDay(
		{ ...day, contract: { ...day.contract, target: 50 } },
		t0 + 1,
		3,
	);
	expect(failed.result.contractCompleted).toBe(false);
	expect(failed.result.total.coins).toBe(failed.result.bonus.coins);
});

test("the next day starts fresh and keeps the customers' loyalty", () => {
	const closed = closeMarketDay({ ...openDay(), loyalty: 42 }, t0 + 30_000, 3);
	const next = advanceMarketDay(closed, 3, context);
	expect(next.phase).toBe("planning");
	expect(next.dayNumber).toBe(2);
	expect(next.loyalty).toBe(42);
	expect(advanceMarketDay(next, 3, context)).toBeNull();
});

test("the best day (hard contract done, top grade) pays coins and XP, never diamonds (Lucas 12/10)", () => {
	let day = openDay(2);
	day = { ...day, contract: { ...day.offers[2], kind: "customers", target: 2 } };
	for (let index = 0; index < 12; index++)
		day = recordDayCustomer(day, { revenue: 60, profit: 30, units: 3, satisfaction: 100, categories: {} });
	const closed = closeMarketDay(day, t0 + DAY_DURATION_MS, 3);
	expect(closed.result.contractCompleted).toBe(true);
	expect(closed.result.total.diamonds).toBe(0);
	expect(closed.result.bonus.diamonds).toBe(0);
	expect(closed.result.total.coins).toBeGreaterThan(0);
});

test("grades cover the whole score range", () => {
	expect([95, 80, 65, 50, 10].map(getDayGrade)).toEqual([
		"S",
		"A",
		"B",
		"C",
		"D",
	]);
});

test("old saves without turns keep an open market running as a free day", () => {
	const open = normalizeDayState(undefined, 2, true, t0);
	expect(open.phase).toBe("open");
	expect(open.contract).toBeNull();
	expect(normalizeDayState(undefined, 2, false, t0).phase).toBe("planning");
});

test("the special requests are gone: no contract about them and the grade is the contract and the satisfaction", () => {
	for (let dayNumber = 1; dayNumber <= 60; dayNumber++)
		for (const offer of createDayOffers(dayNumber, 8, context))
			expect(["requests", "no-expired"]).not.toContain(offer.kind);
	// No contract (0.6) and no customers: only the contract part counts.
	expect(getDayScore({ contract: null, stats: { satisfactionTotal: 0, satisfactionSamples: 0 } })).toBe(33);
	// A met contract and 80% satisfaction: 55 + 36.
	const day = openDay();
	const contract = { ...day.offers[0], kind: "customers", target: 1 };
	const done = recordDayCustomer({ ...day, contract }, { revenue: 10, profit: 4, units: 1, satisfaction: 80, categories: {} });
	expect(getDayScore(done)).toBe(91);
});

test("old saves with special requests load cleaned up, without losing progress or customers", () => {
	const fresh = createInitialDayState(3, context);
	const requestContract = { ...fresh.offers[1], id: "atendimento-ouro", kind: "requests", title: "Atendimento de ouro" };
	const oldStats = {
		...fresh.stats,
		customers: 7,
		revenue: 120,
		loyaltyChange: 3,
		reputationChange: 1.5,
		requestsServed: 1,
		requestsPartial: 0,
		requestsFailed: 0,
		requestsExpired: 2,
		tips: 4,
	};
	const saved = {
		...fresh,
		dayNumber: 9,
		phase: "open",
		contract: requestContract,
		offers: [fresh.offers[0], requestContract, fresh.offers[2]],
		offersRevision: 3,
		startedAt: t0,
		endsAt: t0 + DAY_DURATION_MS,
		loyalty: 47,
		requests: [{ id: "r1", customerId: "c-1", status: "pending", expiresAt: t0 + 30_000 }],
		stats: oldStats,
	};
	const day = normalizeDayState(saved, 3, true, t0);
	expect(day.requests).toBeUndefined();
	expect(day.dayNumber).toBe(9);
	expect(day.phase).toBe("open");
	// A contract that can no longer be met goes on as a contract-free day.
	expect(day.contract).toBeNull();
	expect(day.offers.map((offer) => offer.kind)).not.toContain("requests");
	expect(day.offersRevision).toBe(0);
	expect(day.stats).toEqual({ ...fresh.stats, customers: 7, revenue: 120 });
	// Loyalty is frozen at what the save earned, never below the start (no market gets fewer customers).
	expect(day.loyalty).toBe(47);
	expect(normalizeDayState({ ...saved, loyalty: 4 }, 3, true, t0).loyalty).toBe(INITIAL_LOYALTY);
	expect(normalizeDayState({ ...saved, loyalty: undefined }, 3, true, t0).loyalty).toBe(INITIAL_LOYALTY);
	// A results screen about a request contract shows a plain day; what it pays stays the same.
	const closed = closeMarketDay({ ...day, contract: requestContract }, t0 + DAY_DURATION_MS, 3);
	const results = normalizeDayState({ ...closed, result: { ...closed.result, stats: oldStats } }, 3, false, t0);
	expect(results.phase).toBe("results");
	expect(results.result.contract).toBeNull();
	expect(results.result.stats.requestsExpired).toBeUndefined();
	expect(results.result.total).toEqual(closed.result.total);
	// The day closes and the next one is planned normally.
	const next = advanceMarketDay(closeMarketDay(day, t0 + DAY_DURATION_MS, 3), 3, context);
	expect(next.phase).toBe("planning");
	expect(next.dayNumber).toBe(10);
});
