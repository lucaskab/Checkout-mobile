import type { GameState } from "@/@types/game";
import type {
	SecurityEffect,
	SecurityShelfSlot,
	StoreSecuritySnapshot,
	StoreSecurityState,
	StoreThief,
	StoreThiefCatcher,
} from "@/@types/security";
import { getMarketEra } from "@/data/economy";
import { getUnlockedProductIds, itemCatalog } from "@/data/market-products";
import {
	CATCH_EXPERIENCE,
	CATCH_REPUTATION,
	CATCH_REWARD_MIN,
	CATCH_REWARD_SHARE,
	CAUGHT_REMOVE_MS,
	DOG_BARK_EXTRA_MS,
	ESCAPED_REMOVE_MS,
	FIRST_THIEF_DELAY_MS,
	GUARD_CATCH_MS,
	GUARD_INTERVAL_MULTIPLIER,
	GUARD_REWARD_SHARE,
	SECURITY_OUTCOME_MS,
	SECURITY_STALE_TICK_MS,
	THIEF_FIRST_ERA,
	THIEF_FLEE_MS,
	THIEF_GRAB_DELAY_MS,
	THIEF_INTERVAL_MS,
	THIEF_TILL_CASH,
	THIEF_TILL_ID,
	THIEF_TILL_NAME,
	THIEF_TILL_SHARE,
} from "@/data/security";
import { getPhysicalShelfId, isShelfSlotUnlocked, resolveShelfSlotCounts, shelfProductSlots } from "@/data/shelf-slots";
import { reconcileInventoryLots, takeInventoryLots } from "@/services/inventory-lots";
import { applyExperience } from "@/services/progression";
import { getSlotCapacity } from "@/services/tier-rewards";

// "Ladrão e segurança" (types: src/@types/security.ts, numbers: src/data/security.ts). Pure rules: the store calls
// processStoreSecurity every second (desktop/host.ts) and catchThief when the player taps the thief in Unity.

type Random = () => number;
// Same seeded generator as src/services/store-incidents.ts: the same save always draws the same thieves.
function seeded(seed: number): Random {
	let state = (seed * 2246822519) >>> 0;
	return () => {
		state += 0x6d2b79f5;
		let value = state;
		value = Math.imul(value ^ (value >>> 15), value | 1);
		value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
		return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
	};
}
const between = (random: Random, range: { min: number; max: number }) =>
	range.min + random() * (range.max - range.min);

export function createStoreSecurityState(): StoreSecurityState {
	return {
		thief: null,
		nextAt: null,
		seed: 1,
		statsDay: 0,
		caughtToday: 0,
		escapedToday: 0,
		lostValueToday: 0,
		totalCaught: 0,
		totalEscaped: 0,
		lastOutcome: null,
		tickAt: 0,
	};
}

const num = (value: unknown, fallback = 0) => (typeof value === "number" && Number.isFinite(value) ? value : fallback);
const str = (value: unknown) => (typeof value === "string" ? value : "");
const phases = ["entering", "fleeing", "caught", "escaped"];

function normalizeThief(value: unknown): StoreThief | null {
	if (!value || typeof value !== "object") return null;
	const thief = value as Partial<StoreThief>;
	if (!str(thief.id) || !phases.includes(String(thief.phase))) return null;
	return {
		id: str(thief.id),
		phase: thief.phase as StoreThief["phase"],
		spawnedAt: num(thief.spawnedAt),
		grabAt: num(thief.grabAt),
		fleeDeadline: num(thief.fleeDeadline),
		guardCatchAt: num(thief.guardCatchAt),
		removeAt: num(thief.removeAt),
		productId: num(thief.productId),
		productName: str(thief.productName),
		slotId: str(thief.slotId),
		shelfId: str(thief.shelfId),
		quantity: Math.max(0, Math.floor(num(thief.quantity))),
		value: Math.max(0, num(thief.value)),
		dogBarked: thief.dogBarked === true,
		caughtBy: thief.caughtBy === "player" || thief.caughtBy === "guard" ? thief.caughtBy : "",
		coins: Math.max(0, num(thief.coins)),
	};
}

/** Saves from before the thieves (no field) or with a broken slice start clean; nothing else changes. */
export function normalizeStoreSecurityState(value: unknown): StoreSecurityState {
	const initial = createStoreSecurityState();
	if (!value || typeof value !== "object") return initial;
	const state = value as Partial<StoreSecurityState>;
	const outcome = state.lastOutcome;
	return {
		thief: normalizeThief(state.thief),
		nextAt: typeof state.nextAt === "number" && Number.isFinite(state.nextAt) ? state.nextAt : null,
		seed: Math.max(1, Math.floor(num(state.seed, 1))),
		statsDay: num(state.statsDay),
		caughtToday: num(state.caughtToday),
		escapedToday: num(state.escapedToday),
		lostValueToday: num(state.lostValueToday),
		totalCaught: num(state.totalCaught),
		totalEscaped: num(state.totalEscaped),
		lastOutcome:
			outcome && typeof outcome === "object" && ["caught", "escaped", "guard"].includes(String(outcome.kind))
				? {
						kind: outcome.kind,
						coins: num(outcome.coins),
						productName: str(outcome.productName),
						quantity: num(outcome.quantity),
						at: num(outcome.at),
					}
				: null,
		tickAt: num(state.tickAt),
	};
}

/** Thieves only come from the quitanda on. */
export function canThievesComeIn(eraId: GameState["era"]["id"]) {
	return getMarketEra(eraId).index >= getMarketEra(THIEF_FIRST_ERA).index;
}

export function isThiefActive(thief: StoreThief | null): thief is StoreThief {
	return !!thief && (thief.phase === "entering" || thief.phase === "fleeing");
}

/** The most expensive product on the shelves that has stock (first one on a tie). Old shelf thieves / tools. */
export function pickThiefTarget(slots: SecurityShelfSlot[]): SecurityShelfSlot | null {
	let best: SecurityShelfSlot | null = null;
	for (const slot of slots) if (slot.stock > 0 && (!best || slot.price > best.price)) best = slot;
	return best;
}

/** Coins for a thief stopped: half the goods' value (at least 10); the guard's catch pays half of that. */
export function getThiefReward(value: number, by: Exclude<StoreThiefCatcher, "">) {
	const coins = Math.max(CATCH_REWARD_MIN, Math.round(value * CATCH_REWARD_SHARE));
	return by === "guard" ? Math.max(1, Math.round(coins * GUARD_REWARD_SHARE)) : coins;
}

export type SecurityTickContext = {
	now: number;
	/** The market is open and the day is running. */
	isOpen: boolean;
	/** The era has thieves (quitanda on). */
	canSpawn: boolean;
	slots: SecurityShelfSlot[];
	/** Cash a thief can take from the till right now (getTillCash). */
	till: number;
	/** Efficiency of the security guard on duty (0 = none). */
	guardEfficiency: number;
	/** A store dog was adopted: he barks at the grab. */
	petAdopted: boolean;
	dayNumber: number;
};

export type SecurityStep = { state: StoreSecurityState; effects: SecurityEffect[]; changed: boolean };

function withDay(state: StoreSecurityState, dayNumber: number): StoreSecurityState {
	if (state.statsDay === dayNumber) return state;
	return { ...state, statsDay: dayNumber, caughtToday: 0, escapedToday: 0, lostValueToday: 0 };
}

/** The cash in the till a thief can take: a share of the day's takings, within bounds, never more than the coins. */
export function getTillCash(coins: number, todayRevenue: number) {
	const share = Math.round(Math.max(0, todayRevenue) * THIEF_TILL_SHARE);
	return Math.max(0, Math.min(Math.floor(Math.max(0, coins)), THIEF_TILL_CASH.max, Math.max(THIEF_TILL_CASH.min, share)));
}

const isTillThief = (thief: StoreThief) => thief.slotId === "till";

/** A new thief at the door, after the cash in the till (null when there is too little to bother). */
export function createThief(state: StoreSecurityState, till: number, now: number): StoreThief | null {
	if (till < THIEF_TILL_CASH.min) return null;
	return {
		id: `ladrao-${state.seed}`,
		phase: "entering",
		spawnedAt: now,
		grabAt: now + THIEF_GRAB_DELAY_MS,
		fleeDeadline: 0,
		guardCatchAt: 0,
		removeAt: 0,
		productId: 0,
		productName: THIEF_TILL_NAME,
		slotId: "till",
		shelfId: THIEF_TILL_ID,
		quantity: 0,
		value: 0,
		dogBarked: false,
		caughtBy: "",
		coins: 0,
	};
}

function grab(state: StoreSecurityState, thief: StoreThief, ctx: SecurityTickContext): SecurityStep {
	// The till as it is now (the takings grew while he hung around); too little left: he leaves empty-handed.
	const value = isTillThief(thief) ? ctx.till : 0;
	if (value < 1) return { state: { ...state, thief: null }, effects: [], changed: true };
	const at = thief.grabAt;
	return {
		state: {
			...state,
			thief: {
				...thief,
				phase: "fleeing",
				quantity: 0,
				value,
				// The dog barks at him: a little more time to catch him.
				fleeDeadline: at + THIEF_FLEE_MS + (ctx.petAdopted ? DOG_BARK_EXTRA_MS : 0),
				dogBarked: ctx.petAdopted,
				guardCatchAt: ctx.guardEfficiency > 0 ? at + Math.round(GUARD_CATCH_MS / Math.max(1, ctx.guardEfficiency)) : 0,
			},
		},
		effects: [{ kind: "cash", coins: -value }],
		changed: true,
	};
}

/** What he gives back: the cash to the till, or an old shelf thief's units to their shelf. */
function giveBack(thief: StoreThief): SecurityEffect[] {
	if (isTillThief(thief)) return thief.value > 0 ? [{ kind: "cash", coins: thief.value }] : [];
	return thief.quantity > 0 ? [{ kind: "return", slotId: thief.slotId, productId: thief.productId, quantity: thief.quantity }] : [];
}

function caught(state: StoreSecurityState, thief: StoreThief, by: Exclude<StoreThiefCatcher, "">, at: number): SecurityStep {
	const coins = getThiefReward(thief.value, by);
	return {
		state: {
			...state,
			thief: { ...thief, phase: "caught", caughtBy: by, coins, removeAt: at + CAUGHT_REMOVE_MS },
			caughtToday: state.caughtToday + 1,
			totalCaught: state.totalCaught + 1,
			lastOutcome: { kind: by === "guard" ? "guard" : "caught", coins, productName: thief.productName, quantity: thief.quantity, at },
		},
		effects: [...giveBack(thief), { kind: "reward", coins, experience: CATCH_EXPERIENCE, reputation: CATCH_REPUTATION }],
		changed: true,
	};
}

function escaped(state: StoreSecurityState, thief: StoreThief, at: number): SecurityStep {
	return {
		state: {
			...state,
			thief: { ...thief, phase: "escaped", removeAt: at + ESCAPED_REMOVE_MS },
			escapedToday: state.escapedToday + 1,
			totalEscaped: state.totalEscaped + 1,
			lostValueToday: state.lostValueToday + thief.value,
			lastOutcome: { kind: "escaped", coins: 0, productName: thief.productName, quantity: thief.quantity, at },
		},
		effects: [],
		changed: true,
	};
}

/** He just walks out (market closed, game reopened): whatever he held goes back, nothing is counted. */
function leaveQuietly(state: StoreSecurityState, thief: StoreThief): SecurityStep {
	return {
		state: { ...state, thief: null },
		effects: thief.phase === "fleeing" ? giveBack(thief) : [],
		changed: true,
	};
}

/** One tick: the thief's timeline (grab → guard / escape → leave), closing time, and the next spawn. */
export function stepStoreSecurity(input: StoreSecurityState, ctx: SecurityTickContext): SecurityStep {
	const { now } = ctx;
	let state = withDay(input, ctx.dayNumber);
	let changed = state !== input;
	const effects: SecurityEffect[] = [];
	const apply = (step: SecurityStep) => {
		state = step.state;
		effects.push(...step.effects);
		changed = changed || step.changed;
	};
	// The game was closed for a while with a thief inside: he is simply gone and the goods are back.
	if (state.thief && state.tickAt > 0 && now - state.tickAt > SECURITY_STALE_TICK_MS) {
		if (isThiefActive(state.thief)) apply(leaveQuietly(state, state.thief));
		else apply({ state: { ...state, thief: null }, effects: [], changed: true });
		// (and the next one comes a while after, like after opening)
		apply({ state: { ...state, nextAt: null }, effects: [], changed: true });
	}
	// Every moment due, in order (a slow tick can hold the grab and the guard's catch).
	for (let guard = 0; guard < 6 && state.thief; guard++) {
		const thief: StoreThief = state.thief;
		if (thief.phase === "entering" && now >= thief.grabAt) {
			apply(grab(state, thief, ctx));
			continue;
		}
		if (thief.phase === "fleeing") {
			if (thief.guardCatchAt > 0 && thief.guardCatchAt < thief.fleeDeadline && now >= thief.guardCatchAt) {
				apply(caught(state, thief, "guard", thief.guardCatchAt));
				continue;
			}
			if (now >= thief.fleeDeadline) {
				apply(escaped(state, thief, thief.fleeDeadline));
				continue;
			}
		}
		if ((thief.phase === "caught" || thief.phase === "escaped") && now >= thief.removeAt) {
			apply({ state: { ...state, thief: null }, effects: [], changed: true });
			continue;
		}
		break;
	}
	// Closing time / end of the day: an active thief walks out and leaves the goods (fair to the player).
	if (!ctx.isOpen && isThiefActive(state.thief)) apply(leaveQuietly(state, state.thief));
	// The next thief: only while open, from the quitanda on, never two at once.
	if (!ctx.isOpen || !ctx.canSpawn) {
		if (state.nextAt !== null) apply({ state: { ...state, nextAt: null }, effects: [], changed: true });
	} else if (state.nextAt === null) {
		const random = seeded(state.seed + 7);
		apply({ state: { ...state, nextAt: Math.round(now + between(random, FIRST_THIEF_DELAY_MS)) }, effects: [], changed: true });
	} else if (now >= state.nextAt) {
		const random = seeded(state.seed + 99);
		const wait = between(random, THIEF_INTERVAL_MS) * (ctx.guardEfficiency > 0 ? GUARD_INTERVAL_MULTIPLIER : 1);
		const thief = state.thief ? null : createThief(state, ctx.till, now);
		apply({
			state: { ...state, thief: thief ?? state.thief, nextAt: Math.round(now + wait), seed: state.seed + 1 },
			effects: [],
			changed: true,
		});
	}
	// The clock only moves in the save while something happens (no save write every second for nothing).
	if (changed || isThiefActive(state.thief)) {
		state = { ...state, tickAt: now };
		changed = true;
	}
	return { state: changed ? state : input, effects, changed };
}

export type CatchResult =
	| { ok: true; state: StoreSecurityState; effects: SecurityEffect[] }
	| { ok: false; reason: "gone" | "not-yet" };

/** The player taps the thief: only once he has the goods and before he is out of the door. */
export function catchStoreThief(input: StoreSecurityState, thiefId: string, now: number): CatchResult {
	const thief = input.thief;
	if (!thief || thief.id !== thiefId) return { ok: false, reason: "gone" };
	if (thief.phase === "entering") return { ok: false, reason: "not-yet" };
	if (thief.phase !== "fleeing" || now > thief.fleeDeadline) return { ok: false, reason: "gone" };
	const step = caught(input, thief, "player", now);
	return { ok: true, state: { ...step.state, tickAt: now }, effects: step.effects };
}

/** DEV / QA: a thief right now, whatever the clock or the era (null with one already inside or too little in the till). */
export function spawnThiefNow(input: StoreSecurityState, till: number, now: number) {
	if (isThiefActive(input.thief)) return null;
	const thief = createThief(input, till, now);
	if (!thief) return null;
	return { ...input, thief, seed: input.seed + 1, tickAt: now };
}

// ------------------------------------------------------------------ the game state around the rules

/** Shelf slots with a product (and their stock and price): where a thief can steal from. */
export function getSecurityShelfSlots(
	state: Pick<GameState, "shelfAssignments" | "shelfPrices" | "shelfSlotCounts" | "shelfStock" | "unlockedShelfSlots">,
): SecurityShelfSlot[] {
	const counts = resolveShelfSlotCounts(state.shelfSlotCounts, state.unlockedShelfSlots);
	return shelfProductSlots.flatMap((slot) => {
		const productId = state.shelfAssignments[slot.id];
		if (!productId || !isShelfSlotUnlocked(slot.id, counts)) return [];
		const product = itemCatalog.find((item) => item.id === productId);
		if (!product) return [];
		return [
			{
				slotId: slot.id,
				shelfId: getPhysicalShelfId(slot.id),
				productId,
				productName: product.name,
				price: state.shelfPrices[slot.id] ?? product.sellingPrice,
				stock: state.shelfStock[slot.id] ?? 0,
			},
		];
	});
}

/** The best security guard on duty (0 = none hired or all paused). */
export function getGuardEfficiency(state: Pick<GameState, "employees">) {
	return (state.employees?.employees ?? [])
		.filter((employee) => employee.role === "security" && employee.isWorking)
		.reduce((best, employee) => Math.max(best, employee.efficiency), 0);
}

export function getSecurityContext(state: GameState, now: number): SecurityTickContext {
	return {
		now,
		isOpen: state.market.isOpen && state.day.phase === "open",
		canSpawn: canThievesComeIn(state.era.id),
		slots: getSecurityShelfSlots(state),
		till: getTillCash(state.coins, state.market.todayRevenue),
		guardEfficiency: getGuardEfficiency(state),
		petAdopted: state.pet?.adopted === true,
		dayNumber: state.day.dayNumber,
	};
}

/** Experience given outside a sale (a thief caught, the dog petted): level and unlocked products follow. */
export function withExperience(state: Pick<GameState, "market" | "era">, experience: number): GameState["market"] {
	const { market } = state;
	if (experience <= 0) return market;
	const progression = applyExperience(market.level, market.experience, experience);
	return {
		...market,
		level: progression.level,
		experience: progression.experience,
		lastExperienceGain: experience,
		totalExperience: market.totalExperience + experience,
		unlockedProductIds: Array.from(
			new Set([...market.unlockedProductIds, ...getUnlockedProductIds(progression.level, state.era.id)]),
		),
	};
}

const clampSatisfaction = (value: number) => Math.round(Math.min(100, Math.max(0, value)) * 10) / 10;

/** The stock, coins, experience and reputation a security step changes, as a patch for the store. */
export function applySecurityEffects(state: GameState, effects: SecurityEffect[], now: number): Partial<GameState> {
	if (effects.length === 0) return {};
	const shelfStock = { ...state.shelfStock };
	const shelfLots = { ...state.shelfLots };
	const inventory = { ...state.inventory };
	const inventoryLots = { ...state.inventoryLots };
	let coins = state.coins;
	let experience = 0;
	let reputation = 0;
	let stockChanged = false;
	let inventoryChanged = false;
	const toInventory = (productId: number, quantity: number) => {
		if (quantity <= 0) return;
		inventory[productId] = (inventory[productId] ?? 0) + quantity;
		inventoryLots[productId] = reconcileInventoryLots(productId, inventory[productId], inventoryLots[productId], now);
		inventoryChanged = true;
	};
	for (const effect of effects) {
		if (effect.kind === "take") {
			const stock = shelfStock[effect.slotId] ?? 0;
			const quantity = Math.min(stock, effect.quantity);
			if (quantity <= 0) continue;
			shelfLots[effect.slotId] = takeInventoryLots(
				reconcileInventoryLots(effect.productId, stock, shelfLots[effect.slotId], now),
				quantity,
			).remainingLots;
			shelfStock[effect.slotId] = stock - quantity;
			stockChanged = true;
		} else if (effect.kind === "return") {
			// Back where they came from; the stockroom when the slot changed product or is full now.
			if (state.shelfAssignments[effect.slotId] !== effect.productId) {
				toInventory(effect.productId, effect.quantity);
				continue;
			}
			const stock = shelfStock[effect.slotId] ?? 0;
			const room = Math.max(0, getSlotCapacity(state, effect.slotId) - stock);
			const onShelf = Math.min(room, effect.quantity);
			if (onShelf > 0) {
				shelfStock[effect.slotId] = stock + onShelf;
				shelfLots[effect.slotId] = reconcileInventoryLots(effect.productId, stock + onShelf, shelfLots[effect.slotId], now);
				stockChanged = true;
			}
			toInventory(effect.productId, effect.quantity - onShelf);
		} else if (effect.kind === "cash") {
			coins = Math.max(0, coins + effect.coins);
		} else {
			coins += effect.coins;
			experience += effect.experience;
			reputation += effect.reputation;
		}
	}
	const patch: Partial<GameState> = {};
	if (stockChanged) Object.assign(patch, { shelfStock, shelfLots });
	if (inventoryChanged) Object.assign(patch, { inventory, inventoryLots });
	if (coins !== state.coins) patch.coins = coins;
	if (experience > 0 || reputation !== 0) {
		const market = withExperience(state, experience);
		patch.market = {
			...market,
			customerSatisfaction: clampSatisfaction(market.customerSatisfaction + reputation),
		};
		patch.lastSessionAt = now;
	}
	return patch;
}

/** The whole tick for the store: the new slice plus what it changed (null = nothing to save). */
export function processSecurityTick(state: GameState, now: number): Partial<GameState> | null {
	const security = normalizeStoreSecurityState(state.security);
	const step = stepStoreSecurity(security, getSecurityContext(state, now));
	// (a save from before the thieves gets its slice on the first tick)
	if (!step.changed && state.security) return null;
	return { ...applySecurityEffects(state, step.effects, now), security: step.state };
}

// ------------------------------------------------------------------ snapshot

const left = (at: number, now: number) => (at > 0 ? Math.max(0, at - now) : 0);

export function createSecuritySnapshot(state: Pick<GameState, "security" | "employees">, now: number): StoreSecuritySnapshot {
	const security = normalizeStoreSecurityState(state.security);
	const thief = security.thief;
	const outcome = security.lastOutcome;
	return {
		thief: thief
			? {
					id: thief.id,
					phase: thief.phase,
					productId: thief.productId,
					productName: thief.productName,
					slotId: thief.slotId,
					shelfId: thief.shelfId,
					quantity: thief.quantity,
					value: thief.value,
					spawnedAt: thief.spawnedAt,
					grabAt: thief.grabAt,
					fleeDeadline: thief.fleeDeadline,
					guardCatchAt: thief.guardCatchAt,
					removeAt: thief.removeAt,
					grabInMs: thief.phase === "entering" ? left(thief.grabAt, now) : 0,
					fleeLeftMs: thief.phase === "fleeing" ? left(thief.fleeDeadline, now) : 0,
					guardInMs: thief.phase === "fleeing" && thief.guardCatchAt > 0 && thief.guardCatchAt < thief.fleeDeadline ? left(thief.guardCatchAt, now) : 0,
					dogBarked: thief.dogBarked,
					caughtBy: thief.caughtBy,
					coins: thief.coins,
				}
			: null,
		guardHired: (state.employees?.employees ?? []).some((employee) => employee.role === "security"),
		caughtToday: security.caughtToday,
		escapedToday: security.escapedToday,
		lostValueToday: security.lostValueToday,
		lastOutcome:
			outcome && now - outcome.at < SECURITY_OUTCOME_MS
				? {
						kind: outcome.kind,
						coins: outcome.coins,
						productName: outcome.productName,
						quantity: outcome.quantity,
						ageMs: Math.max(0, now - outcome.at),
					}
				: null,
	};
}
