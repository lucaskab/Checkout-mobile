import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";
import {
	CATCH_EXPERIENCE,
	CAUGHT_REMOVE_MS,
	DOG_BARK_EXTRA_MS,
	ESCAPED_REMOVE_MS,
	FIRST_THIEF_DELAY_MS,
	GUARD_CATCH_MS,
	GUARD_INTERVAL_MULTIPLIER,
	THIEF_FLEE_MS,
	THIEF_GRAB_DELAY_MS,
	THIEF_INTERVAL_MS,
	THIEF_TILL_CASH,
	THIEF_TILL_ID,
} from "../data/security";
import {
	canThievesComeIn,
	catchStoreThief,
	createSecuritySnapshot,
	createStoreSecurityState,
	getThiefReward,
	getTillCash,
	normalizeStoreSecurityState,
	pickThiefTarget,
	spawnThiefNow,
	stepStoreSecurity,
} from "./store-security";

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
const { createSimulatorSnapshot } = await import("./simulator-snapshot.ts");
const { createSimulatorCommandHandler, simulatorActions } = await import("./simulator-protocol.ts");
const pristine = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(pristine)));
afterAll(() => useGameStore.setState(JSON.parse(pristine)));
const store = () => useGameStore.getState();

const t0 = 50_000_000;
const slots = [
	{ slotId: "drinks", shelfId: "drinks", productId: 14, productName: "Refrigerante", price: 6, stock: 5 },
	{ slotId: "produce", shelfId: "produce", productId: 1, productName: "Tomate", price: 3, stock: 9 },
	{ slotId: "dairy", shelfId: "dairy", productId: 5, productName: "Queijo", price: 20, stock: 0 },
];
const ctx = (now, extra = {}) => ({
	now,
	isOpen: true,
	canSpawn: true,
	slots,
	till: 120,
	guardEfficiency: 0,
	petAdopted: false,
	dayNumber: 1,
	...extra,
});
/** A state with a thief already inside, browsing. */
function withThief(now = t0) {
	return spawnThiefNow(createStoreSecurityState(), 120, now);
}

describe("thieves come in", () => {
	test("only from the quitanda on", () => {
		expect(canThievesComeIn("spati")).toBe(false);
		expect(canThievesComeIn("quitanda")).toBe(true);
		expect(canThievesComeIn("supermercado")).toBe(true);
		const step = stepStoreSecurity({ ...createStoreSecurityState(), statsDay: 1 }, ctx(t0, { canSpawn: false }));
		expect(step.changed).toBe(false);
		expect(step.state.nextAt).toBeNull();
	});

	test("the first comes 100–160 s after opening, then one every 150–260 s (×1.6 with a guard)", () => {
		let state = stepStoreSecurity(createStoreSecurityState(), ctx(t0)).state;
		expect(state.thief).toBeNull();
		expect(state.nextAt).toBeGreaterThanOrEqual(t0 + FIRST_THIEF_DELAY_MS.min);
		expect(state.nextAt).toBeLessThanOrEqual(t0 + FIRST_THIEF_DELAY_MS.max);
		const at = state.nextAt;
		state = stepStoreSecurity(state, ctx(at - 1)).state;
		expect(state.thief).toBeNull();
		state = stepStoreSecurity(state, ctx(at)).state;
		expect(state.thief.phase).toBe("entering");
		expect(state.nextAt - at).toBeGreaterThanOrEqual(THIEF_INTERVAL_MS.min);
		expect(state.nextAt - at).toBeLessThanOrEqual(THIEF_INTERVAL_MS.max);
		// With a guard on duty the next one takes 1.6× longer.
		const guarded = stepStoreSecurity({ ...state, thief: null, nextAt: at }, ctx(at, { guardEfficiency: 1 })).state;
		expect(guarded.nextAt - at).toBeGreaterThanOrEqual(THIEF_INTERVAL_MS.min * GUARD_INTERVAL_MULTIPLIER);
		expect(guarded.nextAt - at).toBeLessThanOrEqual(THIEF_INTERVAL_MS.max * GUARD_INTERVAL_MULTIPLIER);
	});

	test("never two at once, none when the till is (nearly) empty, and the clock stops when the market closes", () => {
		const inside = withThief();
		const step = stepStoreSecurity({ ...inside, nextAt: t0 + 1 }, ctx(t0 + 2));
		expect(step.state.thief.id).toBe(inside.thief.id);
		const empty = stepStoreSecurity({ ...createStoreSecurityState(), nextAt: t0 }, ctx(t0, { till: THIEF_TILL_CASH.min - 1 }));
		expect(empty.state.thief).toBeNull();
		expect(empty.state.nextAt).toBeGreaterThan(t0);
		expect(stepStoreSecurity({ ...createStoreSecurityState(), nextAt: t0 }, ctx(t0, { isOpen: false })).state.nextAt).toBeNull();
	});

	test("he goes for the till: a share of the day's takings, within bounds, never more than the coins", () => {
		expect(withThief().thief).toMatchObject({ shelfId: THIEF_TILL_ID, slotId: "till", productId: 0, phase: "entering", grabAt: t0 + THIEF_GRAB_DELAY_MS, value: 0 });
		expect(getTillCash(10_000, 1_000)).toBe(150);
		expect(getTillCash(10_000, 0)).toBe(THIEF_TILL_CASH.min);
		expect(getTillCash(1_000_000, 1_000_000)).toBe(THIEF_TILL_CASH.max);
		expect(getTillCash(12, 1_000)).toBe(12);
		expect(spawnThiefNow(createStoreSecurityState(), THIEF_TILL_CASH.min - 1, t0)).toBeNull();
		// (old shelf thieves and tools: the most expensive product with stock)
		expect(pickThiefTarget(slots).productId).toBe(14);
	});
});

describe("the grab, the chase and the endings", () => {
	test("7 s after coming in he grabs the cash in the till (as it is then) and runs for 11 s", () => {
		const step = stepStoreSecurity(withThief(), ctx(t0 + THIEF_GRAB_DELAY_MS, { till: 180 }));
		const thief = step.state.thief;
		expect(thief.phase).toBe("fleeing");
		expect(thief.value).toBe(180);
		expect(thief.fleeDeadline).toBe(t0 + THIEF_GRAB_DELAY_MS + THIEF_FLEE_MS);
		expect(thief.guardCatchAt).toBe(0);
		expect(step.effects).toEqual([{ kind: "cash", coins: -180 }]);
		// the till was emptied meanwhile: he leaves empty-handed
		const none = stepStoreSecurity(withThief(), ctx(t0 + THIEF_GRAB_DELAY_MS, { till: 0 }));
		expect(none.state.thief).toBeNull();
		expect(none.effects).toEqual([]);
	});

	test("tapping him while he hangs around does nothing; while he runs it catches him and the cash goes back", () => {
		const browsing = withThief();
		expect(catchStoreThief(browsing, browsing.thief.id, t0 + 1000)).toEqual({ ok: false, reason: "not-yet" });
		expect(catchStoreThief(browsing, "someone-else", t0 + 1000)).toEqual({ ok: false, reason: "gone" });
		const running = stepStoreSecurity(browsing, ctx(t0 + THIEF_GRAB_DELAY_MS)).state;
		const thief = running.thief;
		const at = t0 + THIEF_GRAB_DELAY_MS + 2000;
		const result = catchStoreThief(running, thief.id, at);
		expect(result.ok).toBe(true);
		expect(result.state.thief).toMatchObject({ phase: "caught", caughtBy: "player", removeAt: at + CAUGHT_REMOVE_MS });
		const coins = Math.max(10, Math.round(thief.value * 0.5));
		expect(result.effects).toEqual([
			{ kind: "cash", coins: thief.value },
			{ kind: "reward", coins, experience: CATCH_EXPERIENCE, reputation: 1 },
		]);
		expect(result.state.caughtToday).toBe(1);
		expect(result.state.lastOutcome).toMatchObject({ kind: "caught", coins });
		// He leaves the scene 4 s later.
		expect(stepStoreSecurity(result.state, ctx(at + CAUGHT_REMOVE_MS - 1)).state.thief).not.toBeNull();
		expect(stepStoreSecurity(result.state, ctx(at + CAUGHT_REMOVE_MS)).state.thief).toBeNull();
		// Too late: he is out of the door.
		expect(catchStoreThief(running, thief.id, thief.fleeDeadline + 1).ok).toBe(false);
	});

	test("the reward is half the stolen value, at least 10 moedas (the guard's catch pays half)", () => {
		expect(getThiefReward(6, "player")).toBe(10);
		expect(getThiefReward(100, "player")).toBe(50);
		expect(getThiefReward(100, "guard")).toBe(25);
		expect(getThiefReward(6, "guard")).toBe(5);
	});

	test("not caught in time: he escapes with the cash (lost) and is gone 2.5 s later", () => {
		const running = stepStoreSecurity(withThief(), ctx(t0 + THIEF_GRAB_DELAY_MS)).state;
		const deadline = running.thief.fleeDeadline;
		const step = stepStoreSecurity(running, ctx(deadline));
		expect(step.state.thief.phase).toBe("escaped");
		expect(step.effects).toEqual([]);
		expect(step.state).toMatchObject({ escapedToday: 1, lostValueToday: running.thief.value, totalEscaped: 1 });
		expect(step.state.lastOutcome.kind).toBe("escaped");
		expect(stepStoreSecurity(step.state, ctx(deadline + ESCAPED_REMOVE_MS)).state.thief).toBeNull();
	});

	test("a security guard on duty catches him 3.5 s after the grab (faster when trained)", () => {
		const grabAt = t0 + THIEF_GRAB_DELAY_MS;
		const running = stepStoreSecurity(withThief(), ctx(grabAt, { guardEfficiency: 1 })).state;
		expect(running.thief.guardCatchAt).toBe(grabAt + GUARD_CATCH_MS);
		const step = stepStoreSecurity(running, ctx(grabAt + GUARD_CATCH_MS, { guardEfficiency: 1 }));
		expect(step.state.thief).toMatchObject({ phase: "caught", caughtBy: "guard", coins: getThiefReward(running.thief.value, "guard") });
		expect(step.state.lastOutcome.kind).toBe("guard");
		expect(step.effects[0]).toEqual({ kind: "cash", coins: running.thief.value });
		const fast = stepStoreSecurity(withThief(), ctx(grabAt, { guardEfficiency: 2 })).state;
		expect(fast.thief.guardCatchAt).toBe(grabAt + GUARD_CATCH_MS / 2);
		// A slow tick holding the grab and the catch resolves both, in order.
		const late = stepStoreSecurity(withThief(), ctx(grabAt + GUARD_CATCH_MS + 100, { guardEfficiency: 1 }));
		expect(late.state.thief.phase).toBe("caught");
		expect(late.effects.map((e) => e.kind)).toEqual(["cash", "cash", "reward"]);
	});

	test("the store dog barks at the grab: 3 s more to catch him", () => {
		const running = stepStoreSecurity(withThief(), ctx(t0 + THIEF_GRAB_DELAY_MS, { petAdopted: true })).state;
		expect(running.thief.dogBarked).toBe(true);
		expect(running.thief.fleeDeadline).toBe(t0 + THIEF_GRAB_DELAY_MS + THIEF_FLEE_MS + DOG_BARK_EXTRA_MS);
	});

	test("closing time: an active thief leaves and the cash goes back, nothing is counted", () => {
		const running = stepStoreSecurity(withThief(), ctx(t0 + THIEF_GRAB_DELAY_MS)).state;
		const step = stepStoreSecurity(running, ctx(t0 + THIEF_GRAB_DELAY_MS + 1000, { isOpen: false }));
		expect(step.state.thief).toBeNull();
		expect(step.effects).toEqual([{ kind: "cash", coins: running.thief.value }]);
		expect(step.state.escapedToday).toBe(0);
		// browsing: he just leaves
		const browsing = stepStoreSecurity(withThief(), ctx(t0 + 1000, { isOpen: false }));
		expect(browsing.state.thief).toBeNull();
		expect(browsing.effects).toEqual([]);
	});

	test("the game closed with a thief inside: on the way back he is gone and the cash is back", () => {
		const running = stepStoreSecurity(withThief(), ctx(t0 + THIEF_GRAB_DELAY_MS)).state;
		const step = stepStoreSecurity(running, ctx(t0 + 3_600_000));
		expect(step.state.thief).toBeNull();
		expect(step.effects[0]).toEqual({ kind: "cash", coins: running.thief.value });
		expect(step.state.escapedToday).toBe(0);
		// and the next one comes a while after, not at once
		expect(step.state.nextAt).toBeGreaterThanOrEqual(t0 + 3_600_000 + FIRST_THIEF_DELAY_MS.min);
	});

	test("the day counters start over on a new day", () => {
		const state = { ...createStoreSecurityState(), statsDay: 1, caughtToday: 3, escapedToday: 2, lostValueToday: 40, totalCaught: 9 };
		const next = stepStoreSecurity(state, ctx(t0, { dayNumber: 2, isOpen: false })).state;
		expect(next).toMatchObject({ statsDay: 2, caughtToday: 0, escapedToday: 0, lostValueToday: 0, totalCaught: 9 });
	});

	test("nothing happening: the slice is left untouched (no save write every second)", () => {
		const state = { ...createStoreSecurityState(), statsDay: 1, nextAt: t0 + 60_000 };
		const step = stepStoreSecurity(state, ctx(t0));
		expect(step.changed).toBe(false);
		expect(step.state).toBe(state);
	});
});

describe("saves", () => {
	test("old saves (no slice) and broken slices load as a fresh slice", () => {
		expect(normalizeStoreSecurityState(undefined)).toEqual(createStoreSecurityState());
		expect(normalizeStoreSecurityState("x")).toEqual(createStoreSecurityState());
		const broken = normalizeStoreSecurityState({ thief: { id: "", phase: "???" }, seed: -4, nextAt: "soon", lastOutcome: { kind: "boom" } });
		expect(broken).toMatchObject({ thief: null, seed: 1, nextAt: null, lastOutcome: null });
		const kept = withThief();
		expect(normalizeStoreSecurityState(JSON.parse(JSON.stringify(kept)))).toEqual(kept);
	});

	test("an older save version migrates with both new slices", () => {
		const { migrate } = useGameStore.persist.getOptions();
		const old = JSON.parse(pristine);
		delete old.security;
		delete old.pet;
		const migrated = migrate(old, 50);
		expect(migrated.security).toEqual(createStoreSecurityState());
		expect(migrated.pet.adopted).toBe(false);
		expect(migrated.coins).toBe(old.coins);
	});

	test("a current-version save written before the thieves loads with the progress and fresh slices", async () => {
		const saved = JSON.parse(pristine);
		delete saved.security;
		delete saved.pet;
		saved.coins = 4321;
		// (every setState writes the save: the old one goes in last)
		useGameStore.setState({ security: undefined, pet: undefined });
		memory.set("checkout.game", JSON.stringify({ state: saved, version: useGameStore.persist.getOptions().version }));
		await useGameStore.persist.rehydrate();
		expect(store().coins).toBe(4321);
		// the tick gives the slice back on its own
		store().processStoreSecurity(Date.now());
		expect(store().security).toBeTruthy();
		expect(createSimulatorSnapshot(store(), "t", 1).security.thief).toBeNull();
		memory.delete("checkout.game");
	});
});

describe("in the store", () => {
	function openQuitanda() {
		useGameStore.setState({
			era: { ...store().era, id: "quitanda" },
			market: { ...store().market, isOpen: true },
			day: { ...store().day, phase: "open" },
		});
	}

	test("a thief robs the till, the player catches him, the cash and a reward come back", () => {
		openQuitanda();
		useGameStore.setState({ coins: 5_000, market: { ...store().market, todayRevenue: 1_000 } });
		const coins = store().coins;
		const xp = store().market.totalExperience;
		expect(store().devSpawnThief()).toBe(true);
		expect(store().devSpawnThief()).toBe(false); // one at a time
		const thief = store().security.thief;
		expect(store().catchThief(thief.id)).toBe(false); // still browsing
		const now = Date.now();
		store().processStoreSecurity(thief.grabAt);
		const running = store().security.thief;
		expect(running.phase).toBe("fleeing");
		expect(running.value).toBe(150);
		expect(store().coins).toBe(coins - 150);
		// pretend he grabbed just now so the tap lands in time on the real clock
		useGameStore.setState({ security: { ...store().security, thief: { ...running, fleeDeadline: now + 5000 }, tickAt: now } });
		expect(store().catchThief(running.id)).toBe(true);
		expect(store().coins).toBe(coins + Math.max(10, Math.round(running.value * 0.5)));
		expect(store().market.totalExperience).toBe(xp + CATCH_EXPERIENCE);
		expect(store().security.caughtToday).toBe(1);
	});

	test("an escape loses the cash; the snapshot shows the thief and the toast", () => {
		openQuitanda();
		useGameStore.setState({ coins: 5_000, market: { ...store().market, todayRevenue: 400 } });
		store().devSpawnThief();
		const thief = store().security.thief;
		store().processStoreSecurity(thief.grabAt);
		const running = store().security.thief;
		const snap = createSimulatorSnapshot(store(), "t", 1, running.grabAt + 1000).security;
		expect(snap.thief).toMatchObject({ id: running.id, phase: "fleeing", productName: running.productName, quantity: running.quantity, dogBarked: false, caughtBy: "" });
		expect(snap.thief.fleeLeftMs).toBe(THIEF_FLEE_MS - 1000);
		expect(snap.thief.grabInMs).toBe(0);
		store().processStoreSecurity(running.fleeDeadline);
		expect(store().security.thief.phase).toBe("escaped");
		expect(store().coins).toBe(5_000 - running.value);
		const toast = createSimulatorSnapshot(store(), "t", 1, running.fleeDeadline + 500).security.lastOutcome;
		expect(toast).toMatchObject({ kind: "escaped", coins: 0, quantity: running.quantity, ageMs: 500 });
		expect(createSimulatorSnapshot(store(), "t", 1, running.fleeDeadline + 60_000).security.lastOutcome).toBeNull();
	});

	test("the security guard: hired from the minimercado (level 15), one at a time, catches thieves alone", () => {
		useGameStore.setState({ coins: 100_000, market: { ...store().market, level: 15 } });
		expect(store().hireEmployee("security")).toBe(false); // the quitanda is too small
		useGameStore.setState({ era: { ...store().era, id: "minimercado" } });
		expect(store().hireEmployee("security")).toBe(true);
		expect(store().hireEmployee("security")).toBe(false);
		const guard = store().employees.employees.find((e) => e.role === "security");
		expect(guard).toMatchObject({ name: "Segurança 1", salary: 260, efficiency: 1 });
		expect(createSecuritySnapshot(store(), Date.now()).guardHired).toBe(true);
		openQuitanda();
		useGameStore.setState({ era: { ...store().era, id: "minimercado" } });
		store().devSpawnThief();
		const thief = store().security.thief;
		store().processStoreSecurity(thief.grabAt);
		expect(store().security.thief.guardCatchAt).toBe(thief.grabAt + GUARD_CATCH_MS);
		store().processStoreSecurity(thief.grabAt + GUARD_CATCH_MS);
		expect(store().security.thief.caughtBy).toBe("guard");
		// The guard never takes restock or mishap jobs.
		store().processEmployeeWork();
		expect(store().employees.tasks.some((task) => task.employeeId === guard.id)).toBe(false);
	});

	test("the protocol accepts the tap and the guard's hiring; the dev and tick actions stay out", () => {
		expect(simulatorActions).toEqual(expect.arrayContaining(["catchThief", "adoptPet", "petDog", "buyPetCosmetic", "equipPetCosmetic"]));
		expect(simulatorActions).not.toContain("devSpawnThief");
		expect(simulatorActions).not.toContain("processStoreSecurity");
		let revision = 0;
		const handle = createSimulatorCommandHandler("s", () => store(), () => revision);
		const send = (id, action, args) => handle({ protocol: 1, session: "s", id, revision, action, args });
		expect(send("a", "catchThief", [42]).reason).toBe("invalid-action");
		expect(send("b", "catchThief", ["ladrao-1"]).reason).toBe("game-rule-rejected");
		expect(send("c", "hireEmployee", ["security"]).reason).not.toBe("invalid-action");
	});
});
