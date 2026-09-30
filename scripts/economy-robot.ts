// Jogador robô: joga o Checkout por 45 dias reais com as fórmulas do próprio jogo e diz em que dia
// cada era chega. Rode com:  bun scripts/economy-robot.ts            (relatório com a tabela atual)
//                            bun scripts/economy-robot.ts --calibrar (procura os multiplicadores de
//                            ticket que fazem o jogador regular chegar em cada era no dia-alvo)
// Saída: tmp/economia-robo.json e tmp/economia-robo.md
//
// O que é simulado com o código real do jogo: chegada de clientes (getCustomerArrivalDelay), a compra de
// cada cliente (simulateMarketVisit), custo do estoque (purchasePrice), XP e nível (applyExperience),
// prêmio dos contratos (createDayOffers) e a renda offline (mesma fórmula de processSessionResume).
// O que ainda é modelo (vem nas próximas etapas): as eras, os níveis dos itens e a parte offline por era.

import { mkdirSync, writeFileSync } from "node:fs";
import type { MarketEraDefinition } from "@/@types/economy";
import {
	getItemIncomeMultiplier,
	getItemUpgradeCost,
	MAX_ITEM_LEVEL,
	marketEras,
	OFFLINE_CAP_MS,
	OFFLINE_XP_SHARE,
	STARTING_COINS,
	TURN_DURATION_MS,
} from "@/data/economy";
import { itemCatalog, marketProducts } from "@/data/market-products";
import {
	getCustomerArrivalDelay,
	simulateMarketVisit,
} from "@/services/customer-simulation";
import { createDayOffers } from "@/services/market-day";
import {
	applyExperience,
	getExperienceFromSales,
} from "@/services/progression";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;
const DAYS = 45;
/** The robot buys an item upgrade when it pays for itself within this many days. */
const UPGRADE_PAYBACK_DAYS = 3;

type Profile = {
	id: string;
	name: string;
	/** Hours of the day when the player opens the game. */
	sessions: number[];
	turnsPerSession: number;
	/** Chance of finishing the day's medium contract. */
	contractRate: number;
};

export const profiles: Profile[] = [
	{ id: "casual", name: "Casual (2 sessões × 1 turno = 20 min/dia)", sessions: [9, 20], turnsPerSession: 1, contractRate: 0.6 },
	{ id: "regular", name: "Regular (3 sessões × 2 turnos = 1 h/dia)", sessions: [8, 13, 20], turnsPerSession: 2, contractRate: 0.8 },
	{ id: "dedicado", name: "Dedicado (5 sessões × 2 turnos = 1h40/dia)", sessions: [8, 11, 14, 18, 22], turnsPerSession: 2, contractRate: 0.9 },
];

/** How the offline income works: as in the game today, or scaled by the era (proposal). */
type OfflineRule = "atual" | "por-era";

type EraLog = { era: string; day: number; level: number };
type DayLog = {
	day: number;
	era: string;
	level: number;
	coins: number;
	sales: number;
	offline: number;
	contracts: number;
	upgrades: number;
	spent: number;
	turns: number;
};
export type RobotRun = {
	profile: string;
	offline: OfflineRule;
	eras: EraLog[];
	days: DayLog[];
	perTurn: Record<string, { profit: number; revenue: number; customers: number; turns: number }>;
};

const ranked = [...marketProducts].sort(
	(a, b) =>
		(b.suggestedPrice - b.purchasePrice) * b.demand -
		(a.suggestedPrice - a.purchasePrice) * a.demand,
);

/** The best products the player can sell: one per place, mixing categories. */
function pickProducts(level: number, slots: number) {
	const unlocked = ranked.filter((product) => product.unlockLevel <= level);
	const chosen: typeof unlocked = [];
	const used = new Set<string>();
	for (const product of unlocked) {
		if (chosen.length >= slots) break;
		if (used.has(product.category) && unlocked.some((p) => !used.has(p.category) && !chosen.includes(p))) continue;
		chosen.push(product);
		used.add(product.category);
	}
	for (const product of unlocked) {
		if (chosen.length >= slots) break;
		if (!chosen.includes(product)) chosen.push(product);
	}
	return chosen;
}

export function runRobot(
	profile: Profile,
	eras: MarketEraDefinition[],
	offline: OfflineRule = "por-era",
	stopAtEra = eras.length - 1,
): RobotRun {
	let coins = STARTING_COINS;
	let level = 1;
	let experience = 0;
	let eraIndex = 0;
	let building: { index: number; endsAt: number } | null = null;
	let seed = 1;
	let totalRevenue = 0;
	let buyers = 0;
	let lastSessionAt = 0;
	let averageTurnProfit = 0;
	let averageTurnXp = 0;
	/** Yesterday's (sales + offline) / sales: an item upgrade also raises what the market sells offline. */
	let offlineFactor = 1;
	const slotLevels: number[] = [];
	const slotProfit: number[] = []; // profit of each place over the last day, to value upgrades
	const eraLog: EraLog[] = [{ era: eras[0].name, day: 1, level: 1 }];
	const dayLogs: DayLog[] = [];
	const perTurn: RobotRun["perTurn"] = {};
	let today: DayLog = newDay(1);

	function newDay(day: number): DayLog {
		return { day, era: eras[eraIndex].name, level, coins, sales: 0, offline: 0, contracts: 0, upgrades: 0, spent: 0, turns: 0 };
	}

	function finishBuild(now: number) {
		if (building && now >= building.endsAt) {
			eraIndex = building.index;
			eraLog.push({ era: eras[eraIndex].name, day: building.endsAt / DAY + 1, level });
			building = null;
		}
	}

	function playTurn(now: number, night: boolean) {
		const era = eras[eraIndex];
		const products = pickProducts(level, era.productSlots);
		while (slotLevels.length < products.length) {
			slotLevels.push(0);
			slotProfit.push(0);
		}
		const simulated = products.map((product, slot) => ({
			...product,
			availableQuantity: 99,
			marketPrice: product.suggestedPrice,
			necessity: product.demand,
			productId: product.id,
			promotionRate: 0,
			sellingPrice: product.suggestedPrice,
			shelfId: String(slot),
		}));
		const arrival = era.arrivalMultiplier * (night ? 0.7 : 1);
		const ticket = era.ticketMultiplier * (night ? 1.2 : 1);
		let t = getCustomerArrivalDelay(level, products.length, seed, arrival) * 0.4;
		let profit = 0;
		let revenue = 0;
		let turnXp = 0;
		let customers = 0;
		while (t < TURN_DURATION_MS) {
			seed += 1;
			const visit = simulateMarketVisit({
				budgetMultiplier: (1 + Math.max(level - 1, 0) * 0.08) * ticket,
				products: simulated,
				revenueMultiplier: ticket,
				seed,
				storeReputation: 60,
			});
			customers += 1;
			for (const purchase of visit.purchases) {
				const product = itemCatalog.find((item) => item.id === purchase.productId);
				const slot = Number(purchase.shelfId);
				const bonus = getItemIncomeMultiplier(slotLevels[slot] ?? 0);
				// Stock is bought at the supplier price: a bigger era sells pricier baskets of the same goods.
				const cost = (product?.purchasePrice ?? 0) * purchase.quantity;
				// An upgraded item earns more per sale (better display, better goods): +10% profit per level.
				const gain = (purchase.revenue - cost) * bonus;
				profit += gain;
				revenue += purchase.revenue + gain - (purchase.revenue - cost);
				slotProfit[slot] = (slotProfit[slot] ?? 0) + gain;
			}
			if (visit.purchases.length) buyers += 1;
			const xp = getExperienceFromSales(visit.purchases, itemCatalog);
			turnXp += xp;
			const next = applyExperience(level, experience, xp);
			level = next.level;
			experience = next.experience;
			t += getCustomerArrivalDelay(level, products.length, seed, arrival);
		}
		totalRevenue += revenue;
		averageTurnProfit = averageTurnProfit === 0 ? profit : averageTurnProfit * 0.7 + profit * 0.3;
		averageTurnXp = averageTurnXp === 0 ? turnXp : averageTurnXp * 0.7 + turnXp * 0.3;
		coins += profit;
		today.sales += profit;
		today.turns += 1;
		const bucket = (perTurn[era.name] ??= { profit: 0, revenue: 0, customers: 0, turns: 0 });
		bucket.profit += profit;
		bucket.revenue += revenue;
		bucket.customers += customers;
		bucket.turns += 1;

		// The day's contract: the medium one, done most of the time.
		const offers = createDayOffers(Math.floor(now / MINUTE), level);
		const contract = offers[1] ?? offers[0];
		const hash = ((seed * 2654435761) >>> 0) / 4294967296;
		if (contract && hash < profile.contractRate) {
			const reward = contract.reward.coins * era.ticketMultiplier;
			coins += reward;
			today.contracts += reward;
			const next = applyExperience(level, experience, contract.reward.experience);
			level = next.level;
			experience = next.experience;
		}
	}

	function shop(now: number) {
		const next = eras[eraIndex + 1];
		if (!building && next && eraIndex < stopAtEra && coins >= next.coinCost) {
			coins -= next.coinCost;
			today.spent += next.coinCost;
			building = { index: eraIndex + 1, endsAt: now + next.buildDurationMs };
			finishBuild(now);
			return shop(now);
		}
		// Upgrades that pay for themselves in about a day and a half, without eating the era savings
		// when the era is close.
		const era = eras[eraIndex];
		for (let guard = 0; guard < 200; guard++) {
			let best = -1;
			let bestScore = 0;
			for (let slot = 0; slot < Math.min(slotLevels.length, era.productSlots); slot++) {
				if (slotLevels[slot] >= MAX_ITEM_LEVEL) continue;
				const cost = getItemUpgradeCost(era.itemUpgradeBaseCost, slotLevels[slot]);
				const gainPerDay = Math.max(0, slotProfit[slot]) * offlineFactor * (getItemIncomeMultiplier(slotLevels[slot] + 1) / getItemIncomeMultiplier(slotLevels[slot]) - 1);
				const score = gainPerDay / cost;
				if (score > bestScore) {
					bestScore = score;
					best = slot;
				}
			}
			if (best < 0 || bestScore < 1 / UPGRADE_PAYBACK_DAYS) return;
			const cost = getItemUpgradeCost(era.itemUpgradeBaseCost, slotLevels[best]);
			const reserve = next && !building && next.coinCost - coins < cost * 2 ? next.coinCost : 0;
			if (coins - cost < Math.min(reserve, coins)) return;
			if (coins < cost) return;
			coins -= cost;
			today.upgrades += cost;
			slotLevels[best] += 1;
		}
	}

	for (let day = 1; day <= DAYS; day++) {
		const dayStart = (day - 1) * DAY;
		for (const hour of profile.sessions) {
			const now = dayStart + hour * HOUR;
			finishBuild(now);
			// Coming back: customers who came while the player was away.
			if (lastSessionAt > 0 && now - lastSessionAt >= MINUTE) {
				let gained: number;
				if (offline === "atual") {
					// processSessionResume today: 1 customer per 90 s (max 120), paying the average ticket.
					const customers = Math.min(120, Math.floor(Math.min(now - lastSessionAt, 8 * HOUR) / 90_000));
					gained = Math.floor(customers * (buyers > 0 ? totalRevenue / buyers : 18));
				} else {
					const hours = Math.min(now - lastSessionAt, OFFLINE_CAP_MS) / HOUR;
					const turns = hours * eras[eraIndex].offlineTurnsPerHour;
					gained = Math.floor(turns * averageTurnProfit);
					// Offline sales also give experience (a fraction of a played turn's).
					const next = applyExperience(level, experience, Math.round(turns * averageTurnXp * OFFLINE_XP_SHARE));
					level = next.level;
					experience = next.experience;
				}
				coins += gained;
				today.offline += gained;
			}
			shop(now);
			let time = now;
			const night = hour >= 20 && eras[eraIndex].nightTurn;
			for (let turn = 0; turn < profile.turnsPerSession; turn++) {
				playTurn(time, night);
				time += TURN_DURATION_MS + MINUTE;
				finishBuild(time);
				shop(time);
			}
			lastSessionAt = time;
		}
		today.coins = Math.round(coins);
		today.level = level;
		today.era = eras[eraIndex].name;
		dayLogs.push(today);
		offlineFactor = today.sales > 0 ? (today.sales + today.offline) / today.sales : 1;
		for (let slot = 0; slot < slotProfit.length; slot++) slotProfit[slot] = 0;
		today = newDay(day + 1);
		if (eraIndex >= stopAtEra && !building) break;
	}
	return { profile: profile.id, offline, eras: eraLog, days: dayLogs, perTurn };
}

/** Day (1-based, fractional) when `run` reached era index `index`, or Infinity. */
function reachedDay(run: RobotRun, eras: MarketEraDefinition[], index: number) {
	return run.eras.find((log) => log.era === eras[index].name)?.day ?? Number.POSITIVE_INFINITY;
}

/**
 * Finds, era by era, what makes the regular player reach the NEXT era on its target day (evening of
 * that day) by giving the era bigger baskets of pricier goods (the 3D market can only show so many
 * customers at once: the arrival rate is capped at one every 15 s). Eras that are already early with
 * the plain ticket are left as they are.
 */
export function calibrate(base: MarketEraDefinition[]) {
	const eras = base.map((era) => ({ ...era }));
	const regular = profiles.find((profile) => profile.id === "regular") as Profile;
	const dayOf = (index: number) =>
		reachedDay(runRobot(regular, eras, "por-era", index + 1), eras, index + 1);
	for (let index = 1; index < eras.length - 1; index++) {
		const target = eras[index + 1].targetDay + 0.85;
		const floor = Math.max(1, eras[index - 1].ticketMultiplier);
		eras[index].ticketMultiplier = floor;
		const search = (set: (value: number) => void, low: number, high: number, slower: "low" | "high") => {
			for (let step = 0; step < 24; step++) {
				const mid = Math.sqrt(low * high);
				set(mid);
				const late = dayOf(index) > target;
				// "late" means the era must earn more: move towards the faster side.
				if ((slower === "low") === late) low = mid;
				else high = mid;
			}
			return slower === "low" ? high : low;
		};
		if (dayOf(index) < target) {
			// Even the plain ticket gets there sooner than planned: leave it (the report shows how much
			// sooner; raising that era's price is a design choice, not the robot's).
			continue;
		} else {
			const ticket = search((value) => (eras[index].ticketMultiplier = value), floor, 400, "low");
			eras[index].ticketMultiplier = Math.round(ticket * 100) / 100;
		}
	}
	eras[eras.length - 1].ticketMultiplier = eras[eras.length - 2].ticketMultiplier;
	return eras;
}

function table(runs: RobotRun[], eras: MarketEraDefinition[]) {
	const lines = [
		`| Era | Dia-alvo | ${runs.map((run) => run.profile).join(" | ")} |`,
		`|---|---|${runs.map(() => "---").join("|")}|`,
	];
	for (const era of eras) {
		const cells = runs.map((run) => {
			const log = run.eras.find((item) => item.era === era.name);
			return log ? `dia ${log.day.toFixed(1)} (nível ${log.level})` : "—";
		});
		lines.push(`| ${era.name} | ${era.targetDay} | ${cells.join(" | ")} |`);
	}
	return lines.join("\n");
}

if (import.meta.main) {
	const calibrating = process.argv.includes("--calibrar");
	const eras = calibrating ? calibrate(marketEras) : marketEras;
	const runs = profiles.map((profile) => runRobot(profile, eras));
	const today = profiles.map((profile) => runRobot(profile, eras, "atual"));
	const report = [
		"# Jogador robô — relatório",
		"",
		calibrating ? "Multiplicadores de ticket calibrados para o jogador regular." : "Tabela atual de src/data/economy.ts.",
		"",
		"## Quando cada era chega (renda offline proposta, por era)",
		"",
		table(runs, eras),
		"",
		"## Mesma coisa com a renda offline de hoje (até 120 clientes pagando o ticket médio a cada volta)",
		"",
		table(today, eras),
		"",
		"## Lucro médio por turno de 10 min (regular)",
		"",
		"| Era | Lucro/turno | Faturamento/turno | Clientes/turno |",
		"|---|---|---|---|",
		...Object.entries(runs[1].perTurn).map(
			([era, b]) =>
				`| ${era} | ${Math.round(b.profit / b.turns)} | ${Math.round(b.revenue / b.turns)} | ${Math.round(b.customers / b.turns)} |`,
		),
		"",
		"## Multiplicadores usados",
		"",
		"| Era | Custo | Obra | Lugares | Chegada | Ticket | Offline (turnos/hora) |",
		"|---|---|---|---|---|---|---|",
		...eras.map(
			(era) =>
				`| ${era.name} | ${era.coinCost} | ${Math.round(era.buildDurationMs / MINUTE)} min | ${era.productSlots} | ×${era.arrivalMultiplier} | ×${era.ticketMultiplier} | ${era.offlineTurnsPerHour} |`,
		),
	].join("\n");
	mkdirSync("tmp", { recursive: true });
	writeFileSync("tmp/economia-robo.md", report);
	writeFileSync("tmp/economia-robo.json", JSON.stringify({ eras, runs, today }, null, 1));
	console.log(report);
}
