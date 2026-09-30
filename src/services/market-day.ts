import type { CustomerMood } from "@/@types/customer-simulation";
import type {
	DayCatalogProduct,
	DayContract,
	DayCustomerInput,
	DayGrade,
	DayReward,
	DayStats,
	DayStoreContext,
	GameDayState,
	SpecialRequest,
	SpecialRequestKind,
	SpecialRequestOption,
	SpecialRequestQuality,
} from "@/@types/market-day";
import {
	type DayContractDefinition,
	dayContractDefinitions,
	dayContractRewardMultiplier,
} from "@/data/day-contracts";
import {
	getContractCoins,
	getContractExperience,
	TURN_DURATION_MS,
} from "@/data/economy";

// One turn of the market. The same rules run in System (React Native) and Simulator (Unity);
// only the interface differs.
export const DAY_DURATION_MS = TURN_DURATION_MS;
export const SPECIAL_REQUEST_CHANCE = 0.34;
export const MAX_PENDING_REQUESTS = 3;
// Give the player a moment to settle in before the first request of the day.
export const FIRST_REQUEST_DELAY_MS = 12_000;
export const INITIAL_LOYALTY = 20;
// Contract id used to open the market without a contract ("dia livre").
export const FREE_DAY_CONTRACT_ID = "livre";
const MAX_REQUEST_HISTORY = 40;

export const requestDeadlineMs: Record<CustomerMood, number> = {
	"com-pressa": 30_000,
	estressado: 35_000,
	feliz: 50_000,
	calmo: 60_000,
};

// Store-wide consequences of a request outcome (satisfaction is the store reputation).
export const requestEffects: Record<
	SpecialRequestQuality | "expired",
	{ loyalty: number; satisfaction: number }
> = {
	best: { loyalty: 3, satisfaction: 1.5 },
	good: { loyalty: 1, satisfaction: 0.5 },
	bad: { loyalty: -1, satisfaction: -1 },
	expired: { loyalty: -3, satisfaction: -2.5 },
};

const gradeMultiplier: Record<DayGrade, number> = {
	S: 1.5,
	A: 1.25,
	B: 1,
	C: 0.7,
	D: 0.4,
};

type Random = () => number;

function seeded(seed: number): Random {
	let state = (seed * 2654435761) >>> 0;
	return () => {
		state += 0x6d2b79f5;
		let value = state;
		value = Math.imul(value ^ (value >>> 15), value | 1);
		value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
		return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
	};
}

function pick<T>(items: readonly T[], random: Random): T | undefined {
	return items.length ? items[Math.floor(random() * items.length)] : undefined;
}

function shuffle<T>(items: readonly T[], random: Random): T[] {
	const copy = [...items];
	for (let index = copy.length - 1; index > 0; index--) {
		const other = Math.floor(random() * (index + 1));
		[copy[index], copy[other]] = [copy[other], copy[index]];
	}
	return copy;
}

const clamp = (value: number, min: number, max: number) =>
	Math.min(max, Math.max(min, value));

export function createEmptyDayStats(): DayStats {
	return {
		checkoutsLost: 0,
		incidentsFixed: 0,
		customers: 0,
		loyaltyChange: 0,
		profit: 0,
		reputationChange: 0,
		requestsExpired: 0,
		requestsFailed: 0,
		requestsPartial: 0,
		requestsServed: 0,
		revenue: 0,
		satisfactionSamples: 0,
		satisfactionTotal: 0,
		soldByCategory: {},
		tips: 0,
		unitsSold: 0,
	};
}

// ---------------------------------------------------------------- contracts

function buildContract(
	definition: DayContractDefinition,
	level: number,
	category?: { id: string; label: string },
): DayContract {
	const target = definition.target(level);
	const multiplier = dayContractRewardMultiplier[definition.difficulty];
	const label = category?.label ?? "";
	return {
		id: category ? `${definition.id}:${category.id}` : definition.id,
		kind: definition.kind,
		difficulty: definition.difficulty,
		icon: definition.icon,
		title: definition.title(label),
		description: definition.description(target, label),
		target,
		category: category?.id,
		categoryLabel: category?.label,
		reward: {
			coins: Math.round((getContractCoins(level) * multiplier) / 5) * 5,
			experience: Math.round(getContractExperience(level) * multiplier),
			diamonds: definition.difficulty === 3 ? 1 : 0,
		},
	};
}

// Three offers per day: an easy, a medium and a hard contract, varied by day number.
export function createDayOffers(
	dayNumber: number,
	level: number,
	context?: Pick<DayStoreContext, "catalog" | "shelfProductIds">,
): DayContract[] {
	const random = seeded(dayNumber * 97 + level * 13);
	const categories = Array.from(
		new Map(
			(context?.shelfProductIds ?? []).flatMap((id) => {
				const product = context?.catalog.find((item) => item.id === id);
				return product
					? [
							[
								product.category,
								{ id: product.category, label: product.categoryLabel },
							] as const,
						]
					: [];
			}),
		).values(),
	);
	const offers: DayContract[] = [];
	for (const difficulty of [1, 2, 3] as const) {
		const candidates = dayContractDefinitions.filter(
			(definition) =>
				definition.difficulty === difficulty &&
				(definition.kind !== "category" || categories.length > 0),
		);
		const definition = pick(candidates, random);
		if (!definition) continue;
		offers.push(
			buildContract(
				definition,
				level,
				definition.kind === "category" ? pick(categories, random) : undefined,
			),
		);
	}
	return offers;
}

export type ContractProgress = {
	current: number;
	target: number;
	ratio: number;
	completed: boolean;
	label: string;
};

export function getAverageSatisfaction(stats: DayStats) {
	return stats.satisfactionSamples > 0
		? Math.round(stats.satisfactionTotal / stats.satisfactionSamples)
		: 0;
}

export function getContractProgress(
	contract: DayContract | null,
	stats: DayStats,
): ContractProgress {
	if (!contract)
		return {
			current: 0,
			target: 0,
			ratio: 0,
			completed: false,
			label: "Dia livre",
		};
	const goodRequests = stats.requestsServed + stats.requestsPartial;
	const current = (() => {
		switch (contract.kind) {
			case "revenue":
				return stats.revenue;
			case "profit":
				return stats.profit;
			case "customers":
				return stats.customers;
			case "requests":
				return goodRequests;
			case "satisfaction":
				return getAverageSatisfaction(stats);
			case "no-expired":
				return stats.requestsExpired > 0 ? 0 : goodRequests;
			case "category":
				return stats.soldByCategory[contract.category ?? ""] ?? 0;
		}
	})();
	const completed =
		current >= contract.target &&
		(contract.kind !== "satisfaction" || stats.satisfactionSamples >= 3);
	const unit =
		contract.kind === "satisfaction"
			? "%"
			: contract.kind === "revenue" || contract.kind === "profit"
				? " moedas"
				: "";
	return {
		current: Math.round(current),
		target: contract.target,
		ratio: clamp(current / Math.max(1, contract.target), 0, 1),
		completed,
		label: `${Math.round(current).toLocaleString("pt-BR")} / ${contract.target.toLocaleString("pt-BR")}${unit}`,
	};
}

// ---------------------------------------------------------------- day lifecycle

export function createInitialDayState(
	level: number,
	context?: Pick<DayStoreContext, "catalog" | "shelfProductIds">,
): GameDayState {
	return {
		contract: null,
		dayNumber: 1,
		endsAt: null,
		loyalty: INITIAL_LOYALTY,
		offers: createDayOffers(1, level, context),
		phase: "planning",
		requests: [],
		result: null,
		startedAt: null,
		stats: createEmptyDayStats(),
	};
}

export function normalizeDayState(
	value: Partial<GameDayState> | undefined,
	level: number,
	marketOpen: boolean,
	now = Date.now(),
): GameDayState {
	const initial = createInitialDayState(level);
	if (!value || typeof value !== "object") {
		// Saves from before turns: a market that was open keeps running as a free day.
		return marketOpen
			? { ...(startDay(initial, null, now) ?? initial) }
			: initial;
	}
	const phase =
		value.phase === "open" || value.phase === "results"
			? value.phase
			: "planning";
	return {
		...initial,
		...value,
		phase,
		dayNumber: Math.max(1, Math.floor(value.dayNumber ?? 1)),
		loyalty: clamp(value.loyalty ?? INITIAL_LOYALTY, 0, 100),
		offers:
			Array.isArray(value.offers) && value.offers.length
				? value.offers
				: initial.offers,
		requests: Array.isArray(value.requests) ? value.requests : [],
		stats: { ...createEmptyDayStats(), ...value.stats },
		result: phase === "results" ? (value.result ?? null) : null,
	};
}

export function startDay(
	day: GameDayState,
	contractId: string | null,
	now: number,
): GameDayState | null {
	if (day.phase !== "planning") return null;
	const wanted = contractId === FREE_DAY_CONTRACT_ID ? null : contractId;
	const contract = wanted
		? (day.offers.find((offer) => offer.id === wanted) ?? null)
		: null;
	if (wanted && !contract) return null;
	return {
		...day,
		contract,
		endsAt: now + DAY_DURATION_MS,
		phase: "open",
		requests: [],
		result: null,
		startedAt: now,
		stats: createEmptyDayStats(),
	};
}

export function isDayOver(day: GameDayState, now: number) {
	return day.phase === "open" && day.endsAt !== null && now >= day.endsAt;
}

export function acceptsCustomers(day: GameDayState, now: number) {
	return day.phase === "open" && !isDayOver(day, now);
}

export type DaySale = {
	categories: Record<string, number>;
	profit: number;
	revenue: number;
	satisfaction: number;
	units: number;
};

export function recordDayCustomer(
	day: GameDayState,
	sale: DaySale,
): GameDayState {
	if (day.phase !== "open") return day;
	const soldByCategory = { ...day.stats.soldByCategory };
	for (const [category, units] of Object.entries(sale.categories))
		soldByCategory[category] = (soldByCategory[category] ?? 0) + units;
	return {
		...day,
		stats: {
			...day.stats,
			customers: day.stats.customers + 1,
			profit: day.stats.profit + sale.profit,
			revenue: day.stats.revenue + sale.revenue,
			satisfactionSamples: day.stats.satisfactionSamples + 1,
			satisfactionTotal: day.stats.satisfactionTotal + sale.satisfaction,
			soldByCategory,
			unitsSold: day.stats.unitsSold + sale.units,
		},
	};
}

// Money arrives at the register, after the customer was counted on arrival.
export function recordDaySale(
	day: GameDayState,
	sale: Omit<DaySale, "satisfaction">,
): GameDayState {
	if (day.phase !== "open") return day;
	const soldByCategory = { ...day.stats.soldByCategory };
	for (const [category, units] of Object.entries(sale.categories))
		soldByCategory[category] = (soldByCategory[category] ?? 0) + units;
	return {
		...day,
		stats: {
			...day.stats,
			profit: day.stats.profit + sale.profit,
			revenue: day.stats.revenue + sale.revenue,
			soldByCategory,
			unitsSold: day.stats.unitsSold + sale.units,
		},
	};
}

export function recordDayIncidentFixed(day: GameDayState): GameDayState {
	if (day.phase !== "open") return day;
	return { ...day, stats: { ...day.stats, incidentsFixed: day.stats.incidentsFixed + 1 } };
}

export function recordDayCheckoutLost(day: GameDayState, count: number): GameDayState {
	if (day.phase !== "open" || count <= 0) return day;
	return { ...day, stats: { ...day.stats, checkoutsLost: day.stats.checkoutsLost + count } };
}

// ---------------------------------------------------------------- special requests

export function getPendingRequests(day: GameDayState) {
	return day.requests.filter((request) => request.status === "pending");
}

function option(
	id: string,
	label: string,
	detail: string,
	quality: SpecialRequestQuality,
	extra: Partial<SpecialRequestOption> = {},
): SpecialRequestOption {
	return { id, label, detail, quality, ...extra };
}

function otherCategories(
	catalog: DayCatalogProduct[],
	exclude: string,
	random: Random,
	count: number,
) {
	const labels = Array.from(
		new Set(
			catalog
				.filter((product) => product.category !== exclude)
				.map((product) => product.categoryLabel),
		),
	);
	return shuffle(labels, random).slice(0, count);
}

function buildRequest(
	kind: SpecialRequestKind,
	customer: DayCustomerInput,
	context: DayStoreContext,
	random: Random,
): Omit<
	SpecialRequest,
	"createdAt" | "expiresAt" | "id" | "resolvedAt" | "status" | "tip" | "outcome"
> | null {
	const product = (id: number) =>
		context.catalog.find((item) => item.id === id);
	const onShelf = context.shelfProductIds
		.map(product)
		.filter(Boolean) as DayCatalogProduct[];
	const missing = context.unlockedProductIds
		.filter((id) => !context.shelfProductIds.includes(id))
		.map(product)
		.filter(Boolean) as DayCatalogProduct[];
	const base = {
		archetype: customer.archetype,
		customerId: customer.customerId,
		customerName: customer.customerName,
		kind,
		mood: customer.mood,
	};

	if (kind === "ajuda") {
		const wanted = pick(onShelf, random);
		if (!wanted) return null;
		const decoys = otherCategories(context.catalog, wanted.category, random, 2);
		if (decoys.length < 2) return null;
		return {
			...base,
			productId: wanted.id,
			productName: wanted.name,
			message: `Pode me ajudar a encontrar ${wanted.name}?`,
			options: shuffle(
				[
					option(
						"secao-certa",
						`Levar até ${wanted.categoryLabel}`,
						"Acompanhar até a seção certa",
						"best",
						{ productId: wanted.id, source: "shelf" },
					),
					...decoys.map((label, index) =>
						option(
							`secao-${index}`,
							`Levar até ${label}`,
							"Acompanhar até esta seção",
							"bad",
							{ source: "none" },
						),
					),
				],
				random,
			),
		};
	}

	const wanted = pick(missing, random);
	if (!wanted) return null;
	const sameCategory = onShelf.filter(
		(item) => item.category === wanted.category,
	);
	const byPrice = [...onShelf].sort(
		(a, b) =>
			Math.abs(a.sellingPrice - wanted.sellingPrice) -
			Math.abs(b.sellingPrice - wanted.sellingPrice),
	);

	if (kind === "produto") {
		const inStorage = context.storageProductIds.includes(wanted.id);
		const alternative = pick(sameCategory, random) ?? byPrice[0];
		const options: SpecialRequestOption[] = [];
		if (inStorage)
			options.push(
				option(
					"deposito",
					"Buscar no depósito",
					`Vender 1 ${wanted.name} do estoque`,
					"best",
					{ productId: wanted.id, source: "stock" },
				),
			);
		if (alternative)
			options.push(
				option(
					"alternativa",
					`Oferecer ${alternative.name}`,
					alternative.category === wanted.category
						? "Mesma seção, preço parecido"
						: "Outra opção na loja",
					inStorage
						? "good"
						: alternative.category === wanted.category
							? "best"
							: "good",
					{ productId: alternative.id, source: "shelf" },
				),
			);
		options.push(
			option(
				"encomenda",
				"Anotar encomenda",
				"Prometer para a próxima entrega",
				options.length ? "bad" : "good",
				{ source: "none" },
			),
		);
		if (options.length < 2)
			options.push(
				option(
					"desculpas",
					"Pedir desculpas",
					"Dizer que está em falta",
					"bad",
					{ source: "none" },
				),
			);
		return {
			...base,
			productId: wanted.id,
			productName: wanted.name,
			message: `Vocês têm ${wanted.name}? Não encontrei na prateleira.`,
			options: shuffle(options, random),
		};
	}

	// "alternativa": the customer's usual product is missing and they want a recommendation.
	const best = pick(sameCategory, random) ?? byPrice[0];
	if (!best) return null;
	const rest = shuffle(
		onShelf.filter((item) => item.id !== best.id),
		random,
	);
	const good = rest.find(
		(item) =>
			Math.abs(item.sellingPrice - wanted.sellingPrice) <=
			wanted.sellingPrice * 0.5,
	);
	const bad = rest
		.filter((item) => item.id !== good?.id)
		.slice(0, good ? 1 : 2);
	if (!good && bad.length < 1) return null;
	return {
		...base,
		productId: wanted.id,
		productName: wanted.name,
		message: `${wanted.name} acabou... o que você me recomenda no lugar?`,
		options: shuffle(
			[
				option(
					`produto-${best.id}`,
					best.name,
					best.category === wanted.category ? "Mesma seção" : "Preço parecido",
					"best",
					{ productId: best.id, source: "shelf" },
				),
				...(good
					? [
							option(
								`produto-${good.id}`,
								good.name,
								"Preço parecido",
								"good",
								{ productId: good.id, source: "shelf" } as const,
							),
						]
					: []),
				...bad.map((item) =>
					option(`produto-${item.id}`, item.name, item.categoryLabel, "bad", {
						productId: item.id,
						source: "shelf",
					}),
				),
			],
			random,
		),
	};
}

export function createSpecialRequest(
	day: GameDayState,
	customer: DayCustomerInput,
	context: DayStoreContext,
	now: number,
	options: { chance?: number; kind?: SpecialRequestKind } = {},
): SpecialRequest | null {
	if (!acceptsCustomers(day, now)) return null;
	if (
		day.startedAt !== null &&
		now - day.startedAt < FIRST_REQUEST_DELAY_MS &&
		!options.kind
	)
		return null;
	if (getPendingRequests(day).length >= MAX_PENDING_REQUESTS) return null;
	const random = seeded(customer.seed * 31 + day.dayNumber);
	if (!options.kind && random() >= (options.chance ?? SPECIAL_REQUEST_CHANCE))
		return null;
	const kinds: SpecialRequestKind[] = options.kind
		? [options.kind]
		: shuffle(["ajuda", "produto", "alternativa"] as const, random);
	for (const kind of kinds) {
		const request = buildRequest(kind, customer, context, random);
		if (!request) continue;
		// A request never outlives the day.
		const deadline = Math.min(
			now + requestDeadlineMs[customer.mood],
			day.endsAt ?? Number.MAX_SAFE_INTEGER,
		);
		return {
			...request,
			createdAt: now,
			expiresAt: deadline,
			id: `pedido-${day.dayNumber}-${customer.seed}`,
			outcome: "",
			resolvedAt: null,
			status: "pending",
			tip: 0,
		};
	}
	return null;
}

export function addSpecialRequest(
	day: GameDayState,
	request: SpecialRequest,
): GameDayState {
	if (day.requests.some((item) => item.id === request.id)) return day;
	return {
		...day,
		requests: [request, ...day.requests].slice(0, MAX_REQUEST_HISTORY),
	};
}

export type RequestResolution = {
	day: GameDayState;
	loyaltyDelta: number;
	option: SpecialRequestOption;
	request: SpecialRequest;
	satisfactionDelta: number;
	tip: number;
};

export function getRequestTip(level: number, mood: CustomerMood) {
	return Math.round(4 + level * 1.5 + (mood === "feliz" ? 3 : 0));
}

const outcomes: Record<
	SpecialRequestQuality,
	(request: SpecialRequest) => string
> = {
	best: (request) =>
		`${request.customerName} saiu encantado com o atendimento!`,
	good: (request) => `${request.customerName} aceitou a sugestão.`,
	bad: (request) => `${request.customerName} não gostou da resposta.`,
};

export function resolveSpecialRequest(
	day: GameDayState,
	requestId: string,
	optionId: string,
	now: number,
	level: number,
): RequestResolution | null {
	const request = day.requests.find((item) => item.id === requestId);
	if (request?.status !== "pending" || now >= request.expiresAt)
		return null;
	const chosen = request.options.find((item) => item.id === optionId);
	if (!chosen) return null;
	const effect = requestEffects[chosen.quality];
	const tip =
		chosen.quality === "best" ? getRequestTip(level, request.mood) : 0;
	const status =
		chosen.quality === "best"
			? "served"
			: chosen.quality === "good"
				? "partial"
				: "failed";
	const resolved: SpecialRequest = {
		...request,
		outcome: outcomes[chosen.quality](request),
		resolvedAt: now,
		status,
		tip,
	};
	return {
		day: {
			...day,
			loyalty: clamp(day.loyalty + effect.loyalty, 0, 100),
			requests: day.requests.map((item) =>
				item.id === requestId ? resolved : item,
			),
			stats: {
				...day.stats,
				loyaltyChange: day.stats.loyaltyChange + effect.loyalty,
				reputationChange: day.stats.reputationChange + effect.satisfaction,
				requestsFailed:
					day.stats.requestsFailed + (status === "failed" ? 1 : 0),
				requestsPartial:
					day.stats.requestsPartial + (status === "partial" ? 1 : 0),
				requestsServed:
					day.stats.requestsServed + (status === "served" ? 1 : 0),
				tips: day.stats.tips + tip,
			},
		},
		loyaltyDelta: effect.loyalty,
		option: chosen,
		request: resolved,
		satisfactionDelta: effect.satisfaction,
		tip,
	};
}

// Unanswered customers give up and leave; the store loses satisfaction and loyalty.
export function expireSpecialRequests(day: GameDayState, now: number) {
	const expired = day.requests.filter(
		(request) => request.status === "pending" && now >= request.expiresAt,
	);
	if (!expired.length)
		return { day, expired, loyaltyDelta: 0, satisfactionDelta: 0 };
	const effect = requestEffects.expired;
	const loyaltyDelta = effect.loyalty * expired.length;
	const satisfactionDelta = effect.satisfaction * expired.length;
	const ids = new Set(expired.map((request) => request.id));
	return {
		day: {
			...day,
			loyalty: clamp(day.loyalty + loyaltyDelta, 0, 100),
			requests: day.requests.map((request) =>
				ids.has(request.id)
					? {
							...request,
							outcome: `${request.customerName} cansou de esperar e foi embora.`,
							resolvedAt: now,
							status: "expired" as const,
						}
					: request,
			),
			stats: {
				...day.stats,
				loyaltyChange: day.stats.loyaltyChange + loyaltyDelta,
				reputationChange: day.stats.reputationChange + satisfactionDelta,
				requestsExpired: day.stats.requestsExpired + expired.length,
			},
		},
		expired,
		loyaltyDelta,
		satisfactionDelta,
	};
}

// Loyal customers come back more often: up to +25% arrivals at full loyalty.
export function getLoyaltyArrivalMultiplier(loyalty: number) {
	return 1 + clamp(loyalty, 0, 100) / 400;
}

// ---------------------------------------------------------------- closing

export function getDayScore(day: Pick<GameDayState, "contract" | "stats">) {
	const { stats } = day;
	const contract = day.contract
		? getContractProgress(day.contract, stats).ratio
		: 0.6;
	const satisfaction = getAverageSatisfaction(stats) / 100;
	const totalRequests =
		stats.requestsServed +
		stats.requestsPartial +
		stats.requestsFailed +
		stats.requestsExpired;
	const requests = totalRequests
		? (stats.requestsServed + stats.requestsPartial * 0.6) / totalRequests
		: 0.7;
	return Math.round(contract * 40 + satisfaction * 30 + requests * 30);
}

export function getDayGrade(score: number): DayGrade {
	if (score >= 90) return "S";
	if (score >= 78) return "A";
	if (score >= 62) return "B";
	if (score >= 45) return "C";
	return "D";
}

const emptyReward = (): DayReward => ({ coins: 0, diamonds: 0, experience: 0 });

export function closeMarketDay(
	day: GameDayState,
	now: number,
	level: number,
): GameDayState | null {
	if (day.phase !== "open") return null;
	// Anyone still waiting when the doors close leaves unhappy.
	const { day: settled } = expireSpecialRequests(
		{
			...day,
			requests: day.requests.map((request) =>
				request.status === "pending"
					? { ...request, expiresAt: Math.min(request.expiresAt, now) }
					: request,
			),
		},
		now,
	);
	const progress = getContractProgress(settled.contract, settled.stats);
	const score = getDayScore(settled);
	const grade = getDayGrade(score);
	const contractReward =
		settled.contract && progress.completed
			? settled.contract.reward
			: emptyReward();
	const bonus: DayReward = {
		coins: Math.round(((30 + level * 12) * gradeMultiplier[grade]) / 5) * 5,
		diamonds: grade === "S" ? 1 : 0,
		experience: Math.round((10 + level * 4) * gradeMultiplier[grade]),
	};
	const stats = settled.stats;
	const highlights: string[] = [];
	if (settled.contract)
		highlights.push(
			progress.completed
				? `Contrato cumprido: ${settled.contract.title}`
				: `Contrato não cumprido: ${settled.contract.title} (${progress.label})`,
		);
	if (stats.requestsServed)
		highlights.push(
			`${stats.requestsServed} pedido${stats.requestsServed > 1 ? "s" : ""} resolvido${stats.requestsServed > 1 ? "s" : ""} com excelência`,
		);
	if (stats.requestsPartial)
		highlights.push(
			`${stats.requestsPartial} cliente${stats.requestsPartial > 1 ? "s aceitaram" : " aceitou"} uma alternativa`,
		);
	if (stats.requestsFailed)
		highlights.push(
			`${stats.requestsFailed} resposta${stats.requestsFailed > 1 ? "s" : ""} errada${stats.requestsFailed > 1 ? "s" : ""}`,
		);
	if (stats.requestsExpired)
		highlights.push(
			`${stats.requestsExpired} cliente${stats.requestsExpired > 1 ? "s foram" : " foi"} embora esperando`,
		);
	if (stats.tips) highlights.push(`${stats.tips} moedas em gorjetas`);
	if (stats.incidentsFixed)
		highlights.push(
			`${stats.incidentsFixed} imprevisto${stats.incidentsFixed > 1 ? "s resolvidos" : " resolvido"} na loja`,
		);
	if (stats.checkoutsLost)
		highlights.push(
			`${stats.checkoutsLost} cliente${stats.checkoutsLost > 1 ? "s desistiram" : " desistiu"} da fila do caixa`,
		);
	return {
		...settled,
		endsAt: now,
		phase: "results",
		result: {
			averageSatisfaction: getAverageSatisfaction(stats),
			bonus,
			closedAt: now,
			contract: settled.contract,
			contractCompleted: progress.completed,
			contractProgress: progress.ratio,
			dayNumber: settled.dayNumber,
			durationMs: Math.max(0, now - (settled.startedAt ?? now)),
			grade,
			highlights,
			score,
			stats,
			total: {
				coins: contractReward.coins + bonus.coins,
				diamonds: contractReward.diamonds + bonus.diamonds,
				experience: contractReward.experience + bonus.experience,
			},
		},
	};
}

// After the player collects the results, the next day starts in planning with new offers.
export function advanceMarketDay(
	day: GameDayState,
	level: number,
	context?: Pick<DayStoreContext, "catalog" | "shelfProductIds">,
): GameDayState | null {
	if (day.phase !== "results") return null;
	const dayNumber = day.dayNumber + 1;
	return {
		...day,
		contract: null,
		dayNumber,
		endsAt: null,
		offers: createDayOffers(dayNumber, level, context),
		phase: "planning",
		requests: [],
		result: null,
		startedAt: null,
		stats: createEmptyDayStats(),
	};
}
