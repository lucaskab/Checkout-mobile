import { afterAll, beforeEach, expect, mock, test } from "bun:test";

// "Evoluções com recompensa" (claude/evolucoes-recompensas.md, Lucas 01/11): every evolution pays places, customers,
// faster restocking and one exclusive product; it takes time (one at a time, the rest queue), can be skipped with
// diamonds, and old saves get what their tiers already earned, once.
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
const rewards = await import("./tier-rewards.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { productionRecipes } = await import("../data/production-sectors.ts");
const { getSkipDiamondCost } = await import("../data/diamond-skip.ts");
const { planStaffTasks } = await import("./staff-work.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();
const snapshot = () => createSimulatorSnapshot(store(), "test", 1);
const rich = () => useGameStore.setState({ coins: 10_000_000, logistics: { ...store().logistics, premiumCurrency: 10_000 } });
const finish = () => store().processFixtureEvolutions(Number.MAX_SAFE_INTEGER);
const exclusives = itemCatalog.filter((product) => product.exclusive);

test("50 exclusive products, ids 122–171: one per fixture tier and per sector tier", () => {
	expect(exclusives.map((product) => product.id).sort((a, b) => a - b)).toEqual(Array.from({ length: 50 }, (_, index) => 122 + index));
	const keys = new Set(exclusives.map((product) => `${product.exclusive.fixture}:${product.exclusive.tier}`));
	expect(keys.size).toBe(50);
	expect(rewards.getExclusiveProductFor("produce", 2).name).toBe("Morango");
	expect(rewards.getExclusiveProductFor("padaria", 3).name).toBe("Torta de morango");
	// sector exclusives are recipes that open with the sector's tier
	for (const product of exclusives.filter((item) => item.acquisition === "production")) {
		const recipe = productionRecipes.find((item) => item.outputProductId === product.id);
		expect(recipe).toMatchObject({ sectorId: product.exclusive.fixture, requiredSectorTier: product.exclusive.tier });
	}
	// they never open with a level
	expect(store().market.unlockedProductIds.some((id) => id >= 122)).toBe(false);
});

test("a shelf evolution: paid now, keeps selling meanwhile, then places, customers, restock and the exclusive", () => {
	rich();
	store().setMarketLevel(30);
	store().devSetMarketEra("spati");
	const coins = store().coins;
	expect(store().upgradeShelfCapacity("produce", "coins")).toBe(true);
	expect(store().coins).toBeLessThan(coins);
	const evolution = store().evolutions[0];
	expect(evolution).toMatchObject({ kind: "shelf", targetId: "produce", toTier: 2, durationMs: 2 * 60_000 });
	// meanwhile: old look, old numbers
	expect(store().shelfUpgradeLevels.produce ?? 0).toBe(0);
	expect(rewards.getFixtureAttraction(store(), "produce")).toBe(0);
	expect(snapshot().evolutions[0]).toMatchObject({ kind: "shelf", targetId: "produce", queued: false });
	// the clock: nothing before its end, everything at its end
	expect(store().processFixtureEvolutions(evolution.endsAt - 1)).toBe(false);
	expect(store().processFixtureEvolutions(evolution.endsAt)).toBe(true);
	expect(store().evolutions).toEqual([]);
	expect(store().shelfUpgradeLevels.produce).toBe(1);
	expect(store().shelfSlotCounts.produce).toBe(5);
	expect(rewards.getFixtureAttraction(store(), "produce")).toBeCloseTo(0.05);
	expect(rewards.getFixtureRestockBonus(store(), "produce")).toBeCloseTo(0.1);
	expect(store().market.unlockedProductIds).toContain(122); // Morango
	expect(store().celebrations.at(-1)).toMatchObject({ kind: "tier", targetId: "shelf:produce:2" });
	// the exclusive goes only on its own fixture
	const morango = itemCatalog.find((product) => product.id === 122);
	expect(rewards.isExclusiveAllowed("produce", morango)).toBe(true);
	expect(rewards.isExclusiveAllowed("drinks", morango)).toBe(false);
	expect(store().assignProductToShelf("produce:4", 122)).toBe(true);
	expect(store().assignProductToShelf("drinks:1", 123)).toBe(false); // Abacate is not open yet anyway
});

test("one evolution at a time: the others queue and start when the one before ends", () => {
	rich();
	store().setMarketLevel(30);
	store().devSetMarketEra("spati");
	expect(store().upgradeShelfCapacity("produce", "coins")).toBe(true);
	expect(store().upgradeShelfCapacity("drinks", "coins")).toBe(true);
	const [first, second] = store().evolutions;
	expect(second.startedAt).toBe(first.endsAt);
	expect(snapshot().evolutions.map((item) => item.queued)).toEqual([false, true]);
	store().processFixtureEvolutions(first.endsAt);
	expect(store().evolutions).toHaveLength(1);
	expect(store().evolutions[0].targetId).toBe("drinks");
	// the queued one starts now, with its whole time ahead
	expect(store().evolutions[0].endsAt - store().evolutions[0].startedAt).toBe(second.durationMs);
	// the evolution crew is not the interior builders: works do not wait for it
	expect(store().interiorConstructions).toEqual([]);
});

test("skip with diamonds: the usual curve on the time left", () => {
	rich();
	store().setMarketLevel(40);
	store().devSetMarketEra("supermercado");
	useGameStore.setState({ shelfUpgradeLevels: { ...store().shelfUpgradeLevels, produce: 3 } });
	expect(store().upgradeShelfCapacity("produce", "coins")).toBe(true); // ★: 1 h
	const evolution = store().evolutions[0];
	expect(evolution.durationMs).toBe(60 * 60_000);
	const cost = snapshot().evolutions[0].skipCost;
	expect(cost).toBe(getSkipDiamondCost(evolution.endsAt - Date.now()));
	const diamonds = store().logistics.premiumCurrency;
	expect(store().finishEvolutionNow(evolution.id)).toBe(true);
	expect(store().logistics.premiumCurrency).toBe(diamonds - cost);
	expect(store().shelfUpgradeLevels.produce).toBe(4);
	expect(store().shelfSlotCounts.produce).toBe(8);
	expect(rewards.getFixtureAttraction(store(), "produce")).toBeCloseTo(0.25);
	// no diamonds, no skip
	useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency: 0 } });
	expect(store().upgradeShelfCapacity("drinks", "coins")).toBe(true);
	expect(store().finishEvolutionNow(store().evolutions[0].id)).toBe(false);
});

test("sectors: lines, faster, bigger batches, the counter's places and units, the exclusive recipe", () => {
	rich();
	store().setMarketLevel(40);
	store().devSetMarketEra("supermercado");
	const counts = { ...store().shelfSlotCounts, "sector-padaria": 4 };
	useGameStore.setState({ builtSectorIds: ["padaria"], shelfSlotCounts: counts, unlockedShelfSlots: Object.values(counts).reduce((a, b) => a + b, 0) });
	const counter = "sector-padaria";
	expect(rewards.getTierPlaces(store(), counter)).toBe(4);
	const exclusive = productionRecipes.find((recipe) => recipe.outputProductId === 158);
	for (const ingredient of exclusive.ingredients)
		useGameStore.setState({ inventory: { ...store().inventory, [ingredient.productId]: 50 } });
	expect(store().startProduction({ recipeId: exclusive.id, sectorId: "padaria" })).toBe(false); // needs T2
	const capacity = rewards.getSlotCapacity(store(), counter);
	expect(store().upgradeSectorTier("padaria")).toBe(true);
	expect(store().evolutions[0]).toMatchObject({ kind: "sector", durationMs: 30 * 60_000 });
	finish();
	expect(store().sectorTiers.padaria).toBe(2);
	expect(store().shelfSlotCounts[counter]).toBe(5);
	expect(rewards.getSlotCapacity(store(), counter)).toBe(capacity + 5);
	expect(store().market.unlockedProductIds).toContain(158);
	expect(store().startProduction({ recipeId: exclusive.id, sectorId: "padaria" })).toBe(true);
	const job = store().production.jobs.at(-1);
	expect(job.outputQuantity).toBe(Math.ceil(exclusive.outputQuantity * 1.25));
	expect(job.endsAt - job.startedAt).toBeLessThanOrEqual(Math.round(exclusive.durationMs * 0.85) + 5);
	expect(store().upgradeSectorTier("padaria")).toBe(true);
	// (the bakery opens in the minimercado since 04/11: its T3 takes 1 h 15, in that expansion's band)
	expect(store().evolutions[0].durationMs).toBe(75 * 60_000);
	finish();
	expect(store().shelfSlotCounts[counter]).toBe(6);
	expect(rewards.getSlotCapacity(store(), counter)).toBe(capacity + 10);
	expect(store().market.unlockedProductIds).toContain(159);
});

test("checkout and machines take their own times; the cold room ends with the reveal too", () => {
	rich();
	store().setMarketLevel(40);
	store().devSetMarketEra("spati");
	expect(store().purchaseShopItem("checkout-register", "coins")).toBe(true);
	expect(store().evolutions[0]).toMatchObject({ kind: "checkout", toTier: 2, durationMs: 5 * 60_000, itemId: "checkout-register" });
	expect(store().shop.ownedItemIds).not.toContain("checkout-register");
	finish();
	expect(store().shop.ownedItemIds).toContain("checkout-register");
	expect(store().celebrations.at(-1)).toMatchObject({ kind: "tier", targetId: "checkout:checkout:2" });
	expect(store().purchaseDecor("gumball")).toBe(true);
	expect(store().upgradeDecorTier("gumball")).toBe(true);
	expect(store().evolutions[0].durationMs).toBe(10 * 60_000);
	finish();
	store().devSetMarketEra("minimercado");
	expect(store().purchaseShopItem("cold-room-2", "coins")).toBe(true);
	store().devFinishInteriorConstructions();
	expect(store().celebrations.at(-1)).toMatchObject({ kind: "tier", targetId: "coldroom:coldroom:2" });
});

test("restocking an evolved fixture is faster for the stock clerk and in the mini-game", () => {
	const base = { available: 50, capacity: 20, category: "hortifruti", productId: 1, productName: "Tomate", shelfId: "produce", slotId: "produce", stock: 0 };
	const employee = { efficiency: 2, experience: 0, id: "stock_clerk-1", isWorking: true, level: 1, name: "Rui", role: "stock_clerk", speed: 1 };
	const plan = (restockBonus) =>
		planStaffTasks({ employees: [employee], incidents: [], isOpen: true, nextTaskNumber: 1, now: 0, slots: [{ ...base, restockBonus }], storage: "depot", tasks: [] }).started[0];
	const slow = plan(0);
	const fast = plan(0.4);
	expect(fast.endsAt).toBeCloseTo(slow.endsAt * 0.6, -1);
	useGameStore.setState({ era: { ...store().era, id: "supermercado" }, shelfUpgradeLevels: { ...store().shelfUpgradeLevels, produce: 4 }, shelfAssignments: { ...store().shelfAssignments, produce: 1 } });
	expect(snapshot().restockSlots.find((slot) => slot.slotId === "produce").restockBonus).toBeCloseTo(0.4);
});

test("old saves: fixtures already evolved get their places and products once, with one card; nothing goes down", async () => {
	const old = JSON.parse(initial);
	old.era = { ...old.era, id: "supermercado" };
	old.market = { ...old.market, level: 45 };
	old.shelfUpgradeLevels = { ...old.shelfUpgradeLevels, produce: 4, drinks: 2, bakery: 1 };
	old.shelfSlotCounts = { ...old.shelfSlotCounts, produce: 6, drinks: 7, bakery: 4 };
	old.builtSectorIds = ["padaria"];
	old.sectorTiers = { padaria: 3 };
	old.shelfStock = { ...old.shelfStock, drinks: 9 };
	const job = { endsAt: Date.now() + 60_000, id: "padaria-x-1", outputProductId: 1, outputQuantity: 2, recipeId: "x", sectorId: "padaria", slotIndex: 0, startedAt: Date.now() };
	old.production = { ...old.production, jobs: [job] };
	delete old.evolutions;
	const next = await useGameStore.persist.getOptions().migrate(old, 48);
	expect(next.shelfSlotCounts.produce).toBe(8); // ★
	expect(next.shelfSlotCounts.drinks).toBe(7); // bought 7 at T3: kept (T3 gives 6)
	expect(next.shelfSlotCounts.bakery).toBe(5); // T2
	expect(next.shelfSlotCounts["sector-padaria"]).toBe(6);
	expect(next.shelfStock.drinks).toBe(9);
	expect(next.production.jobs).toEqual([job]);
	expect(next.evolutions).toEqual([]);
	const earned = [122, 123, 124, 125, 126, 127, 130, 158, 159];
	for (const id of earned) expect(next.market.unlockedProductIds).toContain(id);
	expect(next.market.unlockedProductIds).not.toContain(128); // drinks T4 not reached
	const cards = next.celebrations.filter((item) => item.targetId.startsWith("unlocks:"));
	expect(cards).toHaveLength(1);
	expect(cards[0].targetId.slice("unlocks:".length).split(",").map(Number).sort((a, b) => a - b)).toEqual(earned);
	// migrating again gives nothing more
	const again = await useGameStore.persist.getOptions().migrate(JSON.parse(JSON.stringify(next)), 48);
	expect(again.celebrations.filter((item) => item.targetId.startsWith("unlocks:"))).toHaveLength(1);
	expect(again.shelfSlotCounts).toEqual(next.shelfSlotCounts);
});

test("customers pick an evolved fixture more often (the day forecast follows)", () => {
	const product = itemCatalog.find((item) => item.id === 1);
	useGameStore.setState({ era: { ...store().era, id: "supermercado" }, shelfAssignments: { produce: 1 }, shelfStock: { produce: 20 } });
	const before = rewards.getFixtureAttraction(store(), "produce");
	useGameStore.setState({ shelfUpgradeLevels: { ...store().shelfUpgradeLevels, produce: 4 } });
	expect(before).toBe(0);
	expect(rewards.getFixtureAttraction(store(), "produce")).toBeCloseTo(0.25);
	expect(product).toBeTruthy();
});
