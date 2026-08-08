import type {
	CustomerArchetype,
	CustomerMood,
	CustomerProfile,
	MarketSimulationProduct,
	MarketVisit,
	MarketVisitOptions,
	PurchaseDecision,
	SimulatedProduct,
	SimulationOptions,
	SimulationResult,
} from "@/@types/customer-simulation";

type Random = () => number;

const archetypes: CustomerArchetype[] = [
	"economico",
	"normal",
	"impulsivo",
	"familia",
	"premium",
];

const moods: CustomerMood[] = ["calmo", "com-pressa", "feliz", "estressado"];

const archetypeSettings: Record<
	CustomerArchetype,
	Pick<CustomerProfile, "impulsivity" | "priceSensitivity"> & {
		budget: number;
		quantityBonus: number;
	}
> = {
	economico: {
		budget: 26,
		impulsivity: 0.12,
		priceSensitivity: 0.9,
		quantityBonus: 0,
	},
	normal: {
		budget: 34,
		impulsivity: 0.4,
		priceSensitivity: 0.5,
		quantityBonus: 0,
	},
	impulsivo: {
		budget: 30,
		impulsivity: 0.86,
		priceSensitivity: 0.22,
		quantityBonus: 0,
	},
	familia: {
		budget: 56,
		impulsivity: 0.32,
		priceSensitivity: 0.58,
		quantityBonus: 1,
	},
	premium: {
		budget: 72,
		impulsivity: 0.54,
		priceSensitivity: 0.16,
		quantityBonus: 0,
	},
};

const moodSettings: Record<
	CustomerMood,
	{ impulseMultiplier: number; priceMultiplier: number }
> = {
	calmo: { impulseMultiplier: 0.8, priceMultiplier: 1.15 },
	"com-pressa": { impulseMultiplier: 1.15, priceMultiplier: 0.55 },
	feliz: { impulseMultiplier: 1.3, priceMultiplier: 0.85 },
	estressado: { impulseMultiplier: 0.55, priceMultiplier: 1.05 },
};

export function simulateCustomers(
	options: SimulationOptions,
): SimulationResult {
	const random = createSeededRandom(options.seed);
	const decisions = Array.from(
		{ length: options.customerCount },
		(_, index) => {
			const customer = createCustomer(index, random);
			return evaluatePurchase(
				customer,
				options.product,
				options.storeReputation,
				random,
			);
		},
	);
	const purchases = decisions.filter((decision) => decision.didBuy);
	const revenue = purchases.reduce(
		(total, decision) =>
			total + decision.quantity * options.product.sellingPrice,
		0,
	);
	const totalUnits = purchases.reduce(
		(total, decision) => total + decision.quantity,
		0,
	);
	const averageChance =
		decisions.reduce((total, decision) => total + decision.chance, 0) /
		decisions.length;

	return {
		averageChance,
		conversionRate: purchases.length / decisions.length,
		decisions,
		revenue,
		totalUnits,
	};
}

export function simulateMarketVisit(options: MarketVisitOptions): MarketVisit {
	const random = createSeededRandom(options.seed);
	const customer = createCustomer(
		options.seed,
		random,
		options.budgetMultiplier ?? 1,
	);
	const products = shuffleProducts(options.products, random);
	const maxProducts =
		getMaxProducts(customer, random) + (options.maxProductsBonus ?? 0);
	let remainingBudget = customer.budget;
	const purchases = [];

	for (const product of products) {
		if (
			purchases.length === maxProducts ||
			product.sellingPrice > remainingBudget
		) {
			continue;
		}

		const decision = evaluatePurchase(
			customer,
			product,
			options.storeReputation,
			random,
		);

		if (!decision.didBuy) {
			continue;
		}

		const quantity = Math.min(
			decision.quantity,
			product.availableQuantity,
			Math.floor(remainingBudget / product.sellingPrice),
		);

		if (quantity === 0) {
			continue;
		}

		const revenue = Math.round(
			quantity * product.sellingPrice * (options.revenueMultiplier ?? 1),
		);
		purchases.push({
			productId: product.productId,
			quantity,
			revenue,
			shelfId: product.shelfId,
		});
		remainingBudget -= revenue;
	}

	return {
		customer,
		purchases,
		revenue: purchases.reduce((total, purchase) => total + purchase.revenue, 0),
		totalUnits: purchases.reduce(
			(total, purchase) => total + purchase.quantity,
			0,
		),
	};
}

export function getCustomerArrivalDelay(
	level: number,
	unlockedProductCount: number,
	seed: number,
	arrivalMultiplier = 1,
) {
	const random = createSeededRandom(seed);
	const levelBonus = Math.max(level - 1, 0) * 0.08;
	const varietyBonus = Math.max(unlockedProductCount - 1, 0) * 0.025;
	const averageDelay =
		32_000 / ((1 + levelBonus + varietyBonus) * arrivalMultiplier);
	const randomVariation = randomBetween(random, 0.75, 1.25);

	return Math.round(clamp(averageDelay * randomVariation, 15_000, 60_000));
}

function createCustomer(
	index: number,
	random: Random,
	budgetMultiplier = 1,
): CustomerProfile {
	const archetype = archetypes[index % archetypes.length];
	const settings = archetypeSettings[archetype];

	return {
		archetype,
		budget: roundCurrency(
			settings.budget * randomBetween(random, 0.75, 1.3) * budgetMultiplier,
		),
		id: `customer-${index + 1}`,
		impulsivity: clamp(
			settings.impulsivity + randomBetween(random, -0.1, 0.1),
			0,
			1,
		),
		loyalty: randomBetween(random, 0.05, 0.9),
		mood: moods[Math.floor(random() * moods.length)],
		priceSensitivity: clamp(
			settings.priceSensitivity + randomBetween(random, -0.1, 0.1),
			0,
			1,
		),
	};
}

function evaluatePurchase(
	customer: CustomerProfile,
	product: SimulatedProduct,
	storeReputation: number,
	random: Random,
): PurchaseDecision {
	const mood = moodSettings[customer.mood];
	const marketDifference =
		(product.sellingPrice - product.marketPrice) / product.marketPrice;
	const pricePenalty =
		Math.max(marketDifference, 0) *
		100 *
		customer.priceSensitivity *
		mood.priceMultiplier *
		1.35;
	const fairPriceBonus = Math.max(-marketDifference, 0) * 100 * 0.32;
	const promotionBonus =
		product.promotionRate *
		100 *
		(customer.archetype === "economico" ? 0.58 : 0.3);
	const necessityScore = product.necessity * 0.65;
	const popularityBonus = (product.popularity ?? product.necessity) * 0.1;
	const customerAffinity = product.preferredCustomers?.includes(
		customer.archetype,
	)
		? 11
		: 0;
	const visualImpulseBonus =
		((product.visualAttractiveness ?? 0) / 100) * customer.impulsivity * 10;
	const loyaltyBonus = customer.loyalty * storeReputation * 0.22;
	const impulseBonus = customer.impulsivity * mood.impulseMultiplier * 16;
	const budgetPenalty = product.sellingPrice > customer.budget ? 34 : 0;
	const randomVariation = randomBetween(random, -7, 7);
	const score = clamp(
		necessityScore +
			popularityBonus +
			customerAffinity +
			visualImpulseBonus +
			fairPriceBonus +
			promotionBonus +
			loyaltyBonus +
			impulseBonus +
			randomVariation -
			pricePenalty -
			budgetPenalty,
		0,
		100,
	);
	const chance = score / 100;
	const didBuy = random() < chance;
	const quantity = didBuy
		? calculateQuantity(customer, product, marketDifference, random)
		: 0;

	return {
		chance,
		customer,
		didBuy,
		marketDifference,
		pricePenalty,
		quantity,
		score,
	};
}

function calculateQuantity(
	customer: CustomerProfile,
	product: SimulatedProduct,
	marketDifference: number,
	random: Random,
) {
	const settings = archetypeSettings[customer.archetype];
	const priceBonus = marketDifference < -0.1 ? 1 : 0;
	const maxAffordable = Math.max(
		1,
		Math.floor(customer.budget / product.sellingPrice),
	);
	const quantity =
		1 + settings.quantityBonus + priceBonus + (random() > 0.78 ? 1 : 0);

	return Math.min(quantity, maxAffordable);
}

function getMaxProducts(customer: CustomerProfile, random: Random) {
	switch (customer.archetype) {
		case "economico":
			return random() > 0.86 ? 2 : 1;
		case "familia":
			return random() > 0.72 ? 3 : 2;
		case "impulsivo":
			return random() > 0.55 ? 2 : 1;
		case "premium":
			return random() > 0.58 ? 2 : 1;
		case "normal":
			return random() > 0.74 ? 2 : 1;
	}
}

function shuffleProducts(products: MarketSimulationProduct[], random: Random) {
	return [...products].sort(() => random() - 0.5);
}

function createSeededRandom(seed: number): Random {
	let state = seed >>> 0;

	return () => {
		state += 0x6d2b79f5;
		let value = state;
		value = Math.imul(value ^ (value >>> 15), value | 1);
		value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
		return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
	};
}

function clamp(value: number, minimum: number, maximum: number) {
	return Math.min(Math.max(value, minimum), maximum);
}

function randomBetween(random: Random, minimum: number, maximum: number) {
	return minimum + (maximum - minimum) * random();
}

function roundCurrency(value: number) {
	return Math.round(value * 100) / 100;
}
