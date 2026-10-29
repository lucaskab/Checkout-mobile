import type {
	DayCatalogProduct,
	DayContract,
	DayGrade,
	DayReward,
	DayStats,
	DayStoreContext,
	GameDayState,
} from "@/@types/market-day";
import {
	type DayContractDefinition,
	dayContractDefinitions,
	dayContractRewardMultiplier,
} from "@/data/day-contracts";
import { type DayForecast, getFallbackDayForecast } from "@/services/day-forecast";
import { CHALLENGE_EXTRA, type ContractPressure, getContractPressure, nextContractMomentum } from "@/services/contract-pressure";
import {
	getContractCoins,
	getContractExperience,
	TURN_DURATION_MS,
	TURN_SHARE,
} from "@/data/economy";

// One turn of the market. The same rules run in System (React Native) and Simulator (Unity);
// only the interface differs.
export const DAY_DURATION_MS = TURN_DURATION_MS;
// Customers' special requests ("pedidos especiais") were removed from the game (Lucas 29/10): they had been switched
// off since October, and now their rules, contracts, stats and texts are gone too. Old saves are cleaned up by
// normalizeDayState (see stripRequestFields).
export const INITIAL_LOYALTY = 20;
// Rules the day's offers are sized with: offers made under an older revision (or without the store's own
// forecast) are made again while the day is still being planned (see refreshDayOffers).
export const DAY_OFFERS_REVISION = 3;
// Contract id used to open the market without a contract ("dia livre").
export const FREE_DAY_CONTRACT_ID = "livre";
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

/** Spreads close seeds apart (murmur3 finaliser). */
function mixSeed(seed: number) {
	let value = seed >>> 0;
	value = Math.imul(value ^ (value >>> 16), 0x85ebca6b);
	value = Math.imul(value ^ (value >>> 13), 0xc2b2ae35);
	return (value ^ (value >>> 16)) >>> 0;
}

function pick<T>(items: readonly T[], random: Random): T | undefined {
	return items.length ? items[Math.floor(random() * items.length)] : undefined;
}

const clamp = (value: number, min: number, max: number) =>
	Math.min(max, Math.max(min, value));

export function createEmptyDayStats(): DayStats {
	return {
		checkoutsLost: 0,
		incidentsFixed: 0,
		customers: 0,
		profit: 0,
		revenue: 0,
		satisfactionSamples: 0,
		satisfactionTotal: 0,
		soldByCategory: {},
		unitsSold: 0,
	};
}

// ---------------------------------------------------------------- contracts

function scaleForecast(forecast: DayForecast, factor: number): DayForecast {
	if (factor === 1) return forecast;
	return {
		...forecast,
		revenue: forecast.revenue * factor,
		profit: forecast.profit * factor,
		customers: forecast.customers * factor,
		units: forecast.units * factor,
		unitsByCategory: Object.fromEntries(Object.entries(forecast.unitsByCategory).map(([id, units]) => [id, units * factor])),
	};
}

function buildContract(
	definition: DayContractDefinition,
	level: number,
	forecast: DayForecast,
	category?: { id: string; label: string },
	pressure: ContractPressure = { factor: 1, challenge: false },
): DayContract {
	// Satisfaction is a percentage: harder means a few points more (capped), not a multiple.
	const target =
		definition.kind === "satisfaction"
			? Math.min(90, definition.target(level, forecast, category?.id) + Math.round((pressure.factor - 1) * 25))
			: definition.target(level, scaleForecast(forecast, pressure.factor), category?.id);
	// A harder day pays in proportion (and a challenge a little more on top); an easier one pays its share.
	const multiplier = dayContractRewardMultiplier[definition.difficulty] * pressure.factor * (pressure.challenge ? 1.25 : 1);
	const label = category?.label ?? "";
	return {
		id: category ? `${definition.id}:${category.id}` : definition.id,
		kind: definition.kind,
		difficulty: definition.difficulty,
		icon: definition.icon,
		title: definition.title(label),
		description: definition.description(target, label),
		target,
		...(pressure.challenge ? { challenge: true } : {}),
		category: category?.id,
		categoryLabel: category?.label,
		reward: {
			coins: Math.round((getContractCoins(level) * multiplier) / 5) * 5,
			experience: Math.round(getContractExperience(level) * multiplier),
			// No diamonds from contracts (Lucas 12/10): diamonds come from the store, so playing hard pays in coins and XP.
			diamonds: 0,
		},
	};
}

// Three offers per day: an easy, a medium and a hard contract, varied by day number.
export function createDayOffers(
	dayNumber: number,
	level: number,
	context?: Pick<DayStoreContext, "catalog" | "shelfProductIds" | "forecast">,
	momentum = 0,
): DayContract[] {
	const pressure = getContractPressure(momentum, dayNumber);
	// Neighbouring days hash far apart (plain consecutive seeds kept drawing the same contracts).
	const random = seeded(mixSeed(dayNumber * 97 + level * 13));
	const forecast = context?.forecast ?? getFallbackDayForecast(level);
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
	const picks: { definition: DayContractDefinition; category?: { id: string; label: string } }[] = [];
	for (const difficulty of [1, 2, 3] as const) {
		const candidates = dayContractDefinitions.filter(
			(definition) =>
				definition.difficulty === difficulty &&
				(definition.kind !== "category" || categories.length > 0),
		);
		const definition = pick(candidates, random);
		if (!definition) continue;
		picks.push({ definition, category: definition.kind === "category" ? pick(categories, random) : undefined });
	}
	// The challenge day makes only its hardest offer the "Desafio"; the other ones just climb.
	const climb = { factor: Math.round((pressure.factor - (pressure.challenge ? CHALLENGE_EXTRA : 0)) * 100) / 100, challenge: false };
	return picks.map(({ definition, category }, index) =>
		buildContract(definition, level, forecast, category, pressure.challenge && index === picks.length - 1 ? pressure : climb),
	);
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
	const current = (() => {
		switch (contract.kind) {
			case "revenue":
				return stats.revenue;
			case "profit":
				return stats.profit;
			case "customers":
				return stats.customers;
			case "satisfaction":
				return getAverageSatisfaction(stats);
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
	context?: Pick<DayStoreContext, "catalog" | "shelfProductIds" | "forecast">,
): GameDayState {
	return {
		contract: null,
		dayNumber: 1,
		endsAt: null,
		loyalty: INITIAL_LOYALTY,
		offers: createDayOffers(1, level, context),
		offersRevision: context?.forecast ? DAY_OFFERS_REVISION : 0,
		phase: "planning",
		result: null,
		startedAt: null,
		stats: createEmptyDayStats(),
	};
}

// Contracts about the special requests (removed): "Atendimento de ouro" and "Ninguém fica esperando".
const REMOVED_CONTRACT_KINDS = ["requests", "no-expired"];
const isRemovedContract = (contract: DayContract | null | undefined) =>
	Boolean(contract && REMOVED_CONTRACT_KINDS.includes(contract.kind as string));

/** The day's stats without the counters of the removed special requests (old saves have them). */
function cleanDayStats(stats: Partial<DayStats> | undefined): DayStats {
	const empty = createEmptyDayStats();
	if (!stats || typeof stats !== "object") return empty;
	const kept = Object.fromEntries(Object.keys(empty).filter((key) => key in stats).map((key) => [key, stats[key as keyof DayStats]]));
	return { ...empty, ...kept } as DayStats;
}

/**
 * Saves from before the special requests were removed (Lucas 29/10) carry their list, their stats and maybe a contract
 * about them: the list and the counters are dropped; offers about them are left out (new ones are made if none is
 * left), and a day open with one of those contracts goes on as a contract-free day (it could never be met now).
 * The loyalty they earned stays (never below the starting value), so the market keeps its customers.
 */
function stripRequestFields(value: Partial<GameDayState> & { requests?: unknown }) {
	const { requests: _requests, ...rest } = value;
	const offers = Array.isArray(rest.offers) ? rest.offers.filter((offer) => !isRemovedContract(offer)) : rest.offers;
	const result = rest.result && typeof rest.result === "object"
		? {
				...rest.result,
				stats: cleanDayStats(rest.result.stats),
				highlights: Array.isArray(rest.result.highlights) ? rest.result.highlights : [],
				...(isRemovedContract(rest.result.contract) ? { contract: null } : {}),
			}
		: rest.result;
	return {
		...rest,
		offers,
		...(Array.isArray(rest.offers) && offers?.length !== rest.offers.length ? { offersRevision: 0 } : {}),
		...(isRemovedContract(rest.contract) ? { contract: null } : {}),
		result,
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
	const saved = stripRequestFields(value);
	return {
		...initial,
		...saved,
		phase,
		dayNumber: Math.max(1, Math.floor(saved.dayNumber ?? 1)),
		loyalty: clamp(
			typeof saved.loyalty === "number" && Number.isFinite(saved.loyalty) ? saved.loyalty : INITIAL_LOYALTY,
			INITIAL_LOYALTY,
			100,
		),
		offers:
			Array.isArray(saved.offers) && saved.offers.length
				? saved.offers
				: initial.offers,
		stats: cleanDayStats(saved.stats),
		result: phase === "results" ? (saved.result ?? null) : null,
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
		result: null,
		startedAt: now,
		stats: createEmptyDayStats(),
	};
}

export function isDayOver(day: GameDayState, now: number) {
	return day.phase === "open" && day.endsAt !== null && now >= day.endsAt;
}

// Closing time (Lucas 18/10): when the clock runs out the doors close to new customers, but the ones already inside
// keep shopping, queue and pay; the day's results come once the last one has left. A safety cap ends it anyway
// (whoever is still in line is rung up then, as before) so a forgotten register never holds the day forever.
export const CLOSING_GRACE_MS = 3 * 60_000;

export function isClosing(day: GameDayState, now: number, customersInside: number) {
	return isDayOver(day, now) && customersInside > 0 && now < (day.endsAt ?? now) + CLOSING_GRACE_MS;
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

// Loyal customers come back more often: up to +25% arrivals at full loyalty (frozen since the special requests,
// the only thing that moved it, were removed; see GameDayState.loyalty).
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
	// The contract and the satisfaction make the grade (the same weights days without special requests always had).
	return Math.round(contract * 55 + satisfaction * 45);
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
	closingAt: number,
	level: number,
): GameDayState | null {
	if (day.phase !== "open") return null;
	// A day found over when the app comes back closed at its own end, not when the player returned.
	const now = typeof day.endsAt === "number" && day.endsAt > 0 ? Math.min(closingAt, day.endsAt) : closingAt;
	const progress = getContractProgress(day.contract, day.stats);
	const score = getDayScore(day);
	const grade = getDayGrade(score);
	const contractReward =
		day.contract && progress.completed
			? day.contract.reward
			: emptyReward();
	const bonus: DayReward = {
		// The day's bonus is sized for a 10-minute turn: a shorter turn earns its share.
		coins: Math.max(5, Math.round(((30 + level * 12) * TURN_SHARE * gradeMultiplier[grade]) / 5) * 5),
		diamonds: 0, // the grade pays coins and XP only (diamonds are the store's currency)
		experience: Math.max(1, Math.round((10 + level * 4) * TURN_SHARE * gradeMultiplier[grade])),
	};
	const stats = day.stats;
	const highlights: string[] = [];
	if (day.contract)
		highlights.push(
			progress.completed
				? `Contrato cumprido: ${day.contract.title}`
				: `Contrato não cumprido: ${day.contract.title} (${progress.label})`,
		);
	if (stats.incidentsFixed)
		highlights.push(
			stats.incidentsFixed > 1
				? `${stats.incidentsFixed} imprevistos resolvidos na loja`
				: `${stats.incidentsFixed} imprevisto resolvido na loja`,
		);
	if (stats.checkoutsLost)
		highlights.push(
			stats.checkoutsLost > 1
				? `${stats.checkoutsLost} clientes desistiram da fila do caixa`
				: `${stats.checkoutsLost} cliente desistiu da fila do caixa`,
		);
	return {
		...day,
		endsAt: now,
		phase: "results",
		contractMomentum: nextContractMomentum(day.contractMomentum, Boolean(day.contract), progress.completed),
		result: {
			averageSatisfaction: getAverageSatisfaction(stats),
			bonus,
			closedAt: now,
			contract: day.contract,
			contractCompleted: progress.completed,
			contractProgress: progress.ratio,
			dayNumber: day.dayNumber,
			durationMs: Math.max(0, now - (day.startedAt ?? now)),
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

// Offers of a day still in planning made with older rules, or before the store could forecast its own day,
// are made again (same day number, so the same kinds of contract come back with the new targets).
export function refreshDayOffers(
	day: GameDayState,
	level: number,
	context: Pick<DayStoreContext, "catalog" | "shelfProductIds" | "forecast">,
): GameDayState | null {
	if (day.phase !== "planning" || day.offersRevision === DAY_OFFERS_REVISION || !context.forecast) return null;
	return {
		...day,
		offers: createDayOffers(day.dayNumber, level, context, day.contractMomentum),
		offersRevision: DAY_OFFERS_REVISION,
	};
}

// After the player collects the results, the next day starts in planning with new offers.
export function advanceMarketDay(
	day: GameDayState,
	level: number,
	context?: Pick<DayStoreContext, "catalog" | "shelfProductIds" | "forecast">,
): GameDayState | null {
	if (day.phase !== "results") return null;
	const dayNumber = day.dayNumber + 1;
	return {
		...day,
		contract: null,
		dayNumber,
		endsAt: null,
		offers: createDayOffers(dayNumber, level, context, day.contractMomentum),
		offersRevision: context?.forecast ? DAY_OFFERS_REVISION : 0,
		phase: "planning",
		result: null,
		startedAt: null,
		stats: createEmptyDayStats(),
	};
}
