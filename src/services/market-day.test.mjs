import { expect, test } from "bun:test";
import {
	addSpecialRequest,
	advanceMarketDay,
	closeMarketDay,
	createDayOffers,
	createInitialDayState,
	createSpecialRequest,
	DAY_DURATION_MS,
	expireSpecialRequests,
	getContractProgress,
	getDayGrade,
	normalizeDayState,
	recordDayCustomer,
	resolveSpecialRequest,
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
const customer = (seed, mood = "calmo") => ({
	archetype: "normal",
	customerId: `c-${seed}`,
	customerName: "Ana",
	mood,
	seed,
});
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
	expect(offers[2].reward.diamonds).toBe(1);
});

test("a day runs for five minutes and only opens from planning", () => {
	const day = openDay();
	expect(day.phase).toBe("open");
	expect(day.endsAt).toBe(t0 + DAY_DURATION_MS);
	expect(startDay(day, null, t0)).toBeNull();
	expect(startDay(createInitialDayState(1), "unknown", t0)).toBeNull();
});

test("customers can ask for help, a product or an alternative", () => {
	const day = openDay();
	const later = t0 + 20_000;
	for (const kind of ["ajuda", "produto", "alternativa"]) {
		const request = createSpecialRequest(day, customer(7), context, later, {
			kind,
		});
		expect(request?.kind).toBe(kind);
		expect(request.options.length).toBeGreaterThanOrEqual(2);
		expect(request.options.some((option) => option.quality === "best")).toBe(
			true,
		);
		expect(request.expiresAt).toBe(later + 60_000);
	}
	const hurried = createSpecialRequest(
		day,
		customer(8, "com-pressa"),
		context,
		later,
		{ kind: "ajuda" },
	);
	expect(hurried.expiresAt).toBe(later + 30_000);
});

test("a product request can be served from the storage room", () => {
	const onlyStorage = { ...context, unlockedProductIds: [1, 3, 4, 5] };
	const request = createSpecialRequest(
		openDay(),
		customer(3),
		onlyStorage,
		t0 + 20_000,
		{ kind: "produto" },
	);
	const best = request.options.find((option) => option.quality === "best");
	expect(request.productId).toBe(5);
	expect(best.source).toBe("stock");
	expect(best.productId).toBe(5);
});

test("serving a request in time improves loyalty and pays a tip", () => {
	const day = openDay();
	const request = createSpecialRequest(
		day,
		customer(11),
		context,
		t0 + 20_000,
		{ kind: "ajuda" },
	);
	const withRequest = addSpecialRequest(day, request);
	const best = request.options.find((option) => option.quality === "best");
	const result = resolveSpecialRequest(
		withRequest,
		request.id,
		best.id,
		t0 + 25_000,
		3,
	);
	expect(result.request.status).toBe("served");
	expect(result.tip).toBeGreaterThan(0);
	expect(result.day.loyalty).toBe(withRequest.loyalty + 3);
	expect(result.day.stats.requestsServed).toBe(1);
	// The same request cannot be answered twice.
	expect(
		resolveSpecialRequest(result.day, request.id, best.id, t0 + 26_000, 3),
	).toBeNull();
});

test("ignored customers leave and cost satisfaction and loyalty", () => {
	const day = openDay();
	const request = createSpecialRequest(
		day,
		customer(12, "com-pressa"),
		context,
		t0 + 20_000,
		{ kind: "ajuda" },
	);
	const withRequest = addSpecialRequest(day, request);
	expect(
		resolveSpecialRequest(
			withRequest,
			request.id,
			request.options[0].id,
			request.expiresAt,
			3,
		),
	).toBeNull();
	const expired = expireSpecialRequests(withRequest, request.expiresAt);
	expect(expired.expired.length).toBe(1);
	expect(expired.satisfactionDelta).toBeLessThan(0);
	expect(expired.day.loyalty).toBe(withRequest.loyalty - 3);
	expect(expired.day.stats.requestsExpired).toBe(1);
});

test("no requests are created before the day opens or while three are pending", () => {
	const planning = createInitialDayState(1, context);
	expect(
		createSpecialRequest(planning, customer(1), context, t0, { kind: "ajuda" }),
	).toBeNull();
	let day = openDay();
	for (const seed of [21, 22, 23])
		day = addSpecialRequest(
			day,
			createSpecialRequest(day, customer(seed), context, t0 + 20_000, {
				kind: "ajuda",
			}),
		);
	expect(
		createSpecialRequest(day, customer(24), context, t0 + 20_000, {
			kind: "ajuda",
		}),
	).toBeNull();
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

test("closing expires pending requests and the next day starts fresh", () => {
	let day = openDay();
	day = addSpecialRequest(
		day,
		createSpecialRequest(day, customer(31), context, t0 + 20_000, {
			kind: "ajuda",
		}),
	);
	const closed = closeMarketDay(day, t0 + 30_000, 3);
	expect(closed.result.stats.requestsExpired).toBe(1);
	const next = advanceMarketDay(closed, 3, context);
	expect(next.phase).toBe("planning");
	expect(next.dayNumber).toBe(2);
	expect(next.requests).toEqual([]);
	expect(next.loyalty).toBe(closed.loyalty);
	expect(advanceMarketDay(next, 3, context)).toBeNull();
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
