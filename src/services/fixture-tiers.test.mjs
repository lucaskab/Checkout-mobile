import { afterAll, beforeEach, expect, mock, test } from "bun:test";

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
const { simulateMarketVisit } = await import("./customer-simulation.ts");
const { getShelfTierInfo, getShelfEvolution, getShelfSlotLimit } = await import("./fixture-tiers.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { getDecorEffects } = await import("./decor-effects.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();
const snapshot = () => createSimulatorSnapshot(store(), "test", 1);
const rich = () => useGameStore.setState({ coins: 10_000_000, logistics: { ...store().logistics, premiumCurrency: 10_000 } });

test("a v47 save keeps every coin, upgrade, piece and box; old items become their stations and steps", async () => {
	const old = JSON.parse(initial);
	const dairy = itemCatalog.find((p) => p.category === "laticinios");
	old.coins = 98_765;
	old.era = { ...old.era, id: "supermercado" };
	old.market = { ...old.market, level: 40 };
	old.shop.ownedItemIds = ["shopping-basket", "large-cart", "simple-cart", "smart-conveyor", "auto-scanner", "cold-storage"];
	old.shelfUpgradeLevels = { ...old.shelfUpgradeLevels, produce: 4, drinks: 2 };
	old.inventoryCapacityLevels = { [dairy.id]: 4 };
	old.inventory = { ...old.inventory, [dairy.id]: 30 };
	old.interior = {
		items: [
			{ id: "shelf:produce", type: "shelf", x: -6.96, z: 2.32, rot: 0 },
			{ id: "decor-1", type: "cart-corral", x: 1, z: 1, rot: 0 },
		],
		owned: { "cart-corral": 1 },
	};
	const next = await useGameStore.persist.getOptions().migrate(old, 47);
	expect(next.coins).toBe(98_765);
	expect(next.shelfUpgradeLevels.produce).toBe(4);
	expect(next.inventoryCapacityLevels[dairy.id]).toBe(4); // over the T1 cap, kept
	expect(next.inventory[dairy.id]).toBe(30);
	// furniture stays where it was (Unity grows it only if it fits, CheckoutInterior)
	expect(next.interior.items.find((i) => i.id === "shelf:produce")).toMatchObject({ x: -6.96, z: 2.32 });
	expect(next.interior.items.find((i) => i.id === "decor-1")).toBeTruthy();
	// the old basket/cart upgrades are stations to place; the placed corral stays
	expect(next.interior.owned).toMatchObject({ "basket-station": 1, "big-cart-corral": 1, "cart-corral": 1 });
	expect(next.shop.ownedItemIds).not.toContain("shopping-basket");
	expect(next.shop.ownedItemIds).not.toContain("large-cart");
	// the checkout: register given, conveyor and scanner kept; the old Câmara Fria is the T4
	expect(next.shop.ownedItemIds).toEqual(expect.arrayContaining(["smart-conveyor", "auto-scanner", "cold-storage", "checkout-register"]));
	useGameStore.setState(next);
	const snap = snapshot();
	expect(snap.fixtureTiers).toMatchObject({ checkout: 3, scanner: true, coldRoom: 4, coldRoomTemplate: "coldroom_T4" });
	expect(snap.shelves.find((s) => s.id === "produce")).toMatchObject({ tier: 5, tierTemplate: "produce_T4", premium: true });
	expect(snap.shelves.find((s) => s.id === "drinks")).toMatchObject({ tier: 3, tierTemplate: "drinks_T3" });
	// migrating twice gives nothing more
	const again = await useGameStore.persist.getOptions().migrate(JSON.parse(JSON.stringify(next)), 48);
	expect(again.interior.owned).toEqual(next.interior.owned);
	expect(again.shop.ownedItemIds.filter((id) => id === "checkout-register").length).toBe(1);
});

test("shelves evolve with the capacity steps, capped by the shop's size", () => {
	rich();
	store().setMarketLevel(30);
	store().devSetMarketEra("spati");
	expect(getShelfTierInfo(store(), "produce")).toMatchObject({ tier: 1, template: "produce_T1", width: 1 });
	expect(store().upgradeShelfCapacity("produce", "coins")).toBe(true); // T2
	expect(getShelfTierInfo(store(), "produce")).toMatchObject({ tier: 2, name: "Banca inclinada de madeira" });
	expect(store().celebrations.at(-1)).toMatchObject({ kind: "tier", targetId: "shelf:produce:2" });
	// the Conveniência has no room for T3
	expect(getShelfEvolution(store(), "produce").blockedUntil).toBe("Minimercado");
	expect(store().upgradeShelfCapacity("produce", "coins")).toBe(false);
	store().devSetMarketEra("minimercado");
	expect(store().upgradeShelfCapacity("produce", "diamonds")).toBe(true); // T3
	expect(getShelfTierInfo(store(), "produce").tier).toBe(3);
	// at the stalls the crates of the model stay (T0) but the numbers may still grow up to T2
	store().devSetMarketEra("banca");
	expect(getShelfTierInfo(store(), "drinks").tier).toBe(0);
	expect(store().upgradeShelfCapacity("drinks", "coins")).toBe(true);
	expect(store().upgradeShelfCapacity("drinks", "coins")).toBe(false);
});

test("product places are limited by the fixture's size (T1 5, T2 6, then 7)", () => {
	rich();
	store().setMarketLevel(30);
	store().devSetMarketEra("spati");
	expect(getShelfSlotLimit(store(), "produce")).toBe(5);
	expect(store().expandShelfSlots("produce")).toBe(true); // 5
	expect(store().expandShelfSlots("produce")).toBe(false); // 6 needs T2
	expect(store().upgradeShelfCapacity("produce", "coins")).toBe(true);
	expect(store().expandShelfSlots("produce")).toBe(true); // 6
	expect(store().expandShelfSlots("produce")).toBe(false); // 7 needs T3 (Minimercado)
});

test("the cold room caps the boxes of chilled products only; its tiers are built outside the depot", () => {
	rich();
	store().setMarketLevel(60);
	store().devSetMarketEra("minimercado");
	const dairy = itemCatalog.find((p) => p.category === "laticinios");
	const rice = itemCatalog.find((p) => p.category === "mercearia");
	expect(store().upgradeInventoryCapacity(dairy.id)).toBe(true); // 3 boxes: T1 cap
	expect(store().upgradeInventoryCapacity(dairy.id)).toBe(false);
	for (let i = 0; i < 3; i++) expect(store().upgradeInventoryCapacity(rice.id)).toBe(true); // dry goods: no cap
	// T2: the works start right away (no piece to place)
	expect(store().purchaseShopItem("cold-room-3", "coins")).toBe(false); // needs T2 first (and the supermarket)
	expect(store().purchaseShopItem("cold-room-2", "coins")).toBe(true);
	const works = store().interiorConstructions.find((c) => c.targetId === "cold-room-2");
	expect(works.pending).toBeUndefined();
	expect(snapshot().fixtureTiers.coldRoomBuilding).toBe("coldroom_T2");
	store().devFinishInteriorConstructions();
	expect(store().shop.ownedItemIds).toContain("cold-room-2");
	expect(snapshot().fixtureTiers.coldRoom).toBe(2);
	expect(store().upgradeInventoryCapacity(dairy.id)).toBe(true); // 5 boxes
	expect(store().upgradeInventoryCapacity(dairy.id)).toBe(false);
	// the T4 needs the central warehouse
	store().devSetMarketEra("supermercado");
	expect(store().purchaseShopItem("cold-room-3", "coins")).toBe(true);
	store().devFinishInteriorConstructions();
	expect(store().purchaseShopItem("cold-storage", "coins")).toBe(false);
	useGameStore.setState({ unlockedMarketExpansionIds: [...store().unlockedMarketExpansionIds, "grand-warehouse"] });
	expect(store().purchaseShopItem("cold-storage", "diamonds")).toBe(true);
	store().devFinishInteriorConstructions();
	expect(snapshot().fixtureTiers.coldRoom).toBe(4);
});

test("checkout steps are bought in order, from the shop that has room for them", () => {
	rich();
	store().setMarketLevel(40);
	store().devSetMarketEra("tenda");
	expect(store().purchaseShopItem("checkout-register", "coins")).toBe(false); // the stalls' own register
	store().devSetMarketEra("spati");
	expect(store().purchaseShopItem("smart-conveyor", "coins")).toBe(false);
	expect(store().purchaseShopItem("checkout-register", "diamonds")).toBe(true);
	expect(snapshot().fixtureTiers.checkout).toBe(2);
	expect(store().purchaseShopItem("smart-conveyor", "coins")).toBe(false); // needs a placed checkout (minimercado)
	store().devSetMarketEra("minimercado");
	expect(store().purchaseShopItem("smart-conveyor", "coins")).toBe(true);
	expect(store().purchaseShopItem("checkout-premium", "coins")).toBe(false); // scanner first
	expect(store().purchaseShopItem("auto-scanner", "coins")).toBe(true);
	expect(store().purchaseShopItem("checkout-premium", "coins")).toBe(false); // supermarket
	store().devSetMarketEra("supermercado");
	expect(store().purchaseShopItem("checkout-premium", "coins")).toBe(true);
	expect(snapshot().fixtureTiers).toMatchObject({ checkout: 4, checkoutTemplate: "checkout_T4" });
});

test("a new shop reaching the minimercado gets the register for free", () => {
	store().devSetMarketEra("minimercado");
	expect(store().shop.ownedItemIds).toContain("checkout-register");
});

test("cart stations: bought from their shop, customers take the smallest that holds their plan", () => {
	rich();
	store().setMarketLevel(30);
	store().devSetMarketEra("quitanda");
	expect(store().purchaseDecor("basket-station")).toBe(true);
	expect(store().purchaseDecor("cart-corral")).toBe(false); // bays come with the mercadinho
	expect(snapshot().decorCatalog.find((d) => d.id === "cart-corral").lockedNote).toBe("Chega com: Mercadinho");
	store().devSetMarketEra("mercadinho");
	expect(store().purchaseDecor("cart-corral")).toBe(true);
	expect(store().purchaseDecor("big-cart-corral")).toBe(true);
	const piece = (id, type) => ({ id, type, x: 0, z: 0, rot: 0 });
	const fx = getDecorEffects({ items: [piece("a", "basket-station"), piece("b", "cart-corral"), piece("c", "big-cart-corral")], owned: {} });
	expect(fx.carriers.sort()).toEqual(["basket", "bigCart", "cart"]);
	const products = itemCatalog.slice(0, 40).map((p, i) => ({ ...p, productId: p.id, availableQuantity: 99, marketPrice: p.suggestedPrice, necessity: 95, promotionRate: 0, shelfId: `s${i}` }));
	const counts = { hands: 0, basket: 0, cart: 0, bigCart: 0 };
	let shortfall = 0;
	for (let seed = 1; seed <= 300; seed++) {
		const all = simulateMarketVisit({ products, seed, storeReputation: 60, carriers: fx.carriers });
		counts[all.carrier]++;
		expect(all.cartShortfall).toBe(0);
		const basketsOnly = simulateMarketVisit({ products, seed, storeReputation: 60, carriers: ["basket"] });
		shortfall += basketsOnly.cartShortfall;
		expect(["hands", "basket"]).toContain(basketsOnly.carrier);
		// without stations given, the old visit is unchanged (same draw)
		const legacy = simulateMarketVisit({ products, seed, storeReputation: 60 });
		expect(legacy.carrier).toBeUndefined();
	}
	for (const carrier of ["hands", "basket", "cart", "bigCart"]) expect(counts[carrier]).toBeGreaterThan(0);
	expect(shortfall).toBeGreaterThan(0);
});

test("ATM, gumball and claw machine evolve every piece of their kind", () => {
	rich();
	store().setMarketLevel(40);
	expect(store().upgradeDecorTier("atm")).toBe(false); // none owned
	expect(store().purchaseDecor("atm")).toBe(true);
	expect(store().upgradeDecorTier("atm")).toBe(true);
	expect(store().interior.tiers.atm).toBe(2);
	const placed = { ...store().interior, items: [{ id: "decor-1", type: "atm", x: 0, z: 0, rot: 0 }] };
	expect(getDecorEffects(placed).budgetMultiplier).toBeCloseTo(1.2);
	expect(store().upgradeDecorTier("atm")).toBe(true);
	expect(store().upgradeDecorTier("atm")).toBe(false); // T3 is the last
	expect(store().purchaseDecor("gumball")).toBe(true);
	expect(store().upgradeDecorTier("gumball")).toBe(true);
	expect(store().upgradeDecorTier("gumball")).toBe(false); // no tower: two tiers
	const machines = getDecorEffects({ ...store().interior, items: [{ id: "g", type: "gumball", x: 0, z: 0, rot: 0 }] }).machines;
	expect(machines[0].coins).toBe(3); // 2 × 1.5
	const diamonds = store().logistics.premiumCurrency;
	expect(store().purchaseDecor("claw-machine")).toBe(true);
	expect(store().upgradeDecorTier("claw-machine")).toBe(true);
	expect(store().logistics.premiumCurrency).toBe(diamonds - 25 - 30);
	expect(snapshot().interior.tiers.find((t) => t.type === "claw-machine")).toMatchObject({ tier: 2, template: "claw_T2" });
});

test("special sectors: built ones are T1; T2 adds a line, T3 cuts the time and sells dearer; nothing produced is lost", async () => {
	// a v47 save with a built bakery producing: it migrates to T1 with its jobs untouched
	const old = JSON.parse(initial);
	old.era = { ...old.era, id: "supermercado" };
	old.market = { ...old.market, level: 40 };
	old.builtSectorIds = ["padaria"];
	const job = { endsAt: Date.now() + 60_000, id: "padaria-x-1", outputProductId: 1, outputQuantity: 2, recipeId: "x", sectorId: "padaria", slotIndex: 1, startedAt: Date.now() };
	old.production = { ...old.production, jobs: [job] };
	const next = await useGameStore.persist.getOptions().migrate(old, 47);
	expect(next.sectorTiers).toEqual({});
	expect(next.production.jobs).toEqual([job]);
	useGameStore.setState({ ...next, coins: 10_000_000, logistics: { ...next.logistics, premiumCurrency: 10_000 } });
	expect(snapshot().sectors.find((s) => s.id === "padaria")).toMatchObject({ tier: 1, tierTemplate: "sector-padaria_T1" });
	// not built: no evolution
	expect(store().upgradeSectorTier("adega")).toBe(false);
	const coins = store().coins;
	expect(store().upgradeSectorTier("padaria")).toBe(true);
	expect(store().coins).toBe(coins - 30_000); // the Supermercado's price
	expect(store().celebrations.at(-1)).toMatchObject({ kind: "tier", targetId: "sector:padaria:2" });
	expect(store().production.jobs).toEqual([job]);
	expect(snapshot().sectors.find((s) => s.id === "padaria")).toMatchObject({ tier: 2, tierTemplate: "sector-padaria_T2" });
	const diamonds = store().logistics.premiumCurrency;
	expect(store().upgradeSectorTier("padaria", "diamonds")).toBe(true);
	expect(store().logistics.premiumCurrency).toBe(diamonds - 80);
	expect(store().upgradeSectorTier("padaria")).toBe(false); // T3 is the last
	// saved and loaded again: the tier stays, unknown ids are dropped
	const saved = await useGameStore.persist.getOptions().migrate({ ...JSON.parse(JSON.stringify(store())), sectorTiers: { padaria: 3, nope: 2 } }, 48);
	expect(saved.sectorTiers).toEqual({ padaria: 3 });
});

test("sector boards: the counter's products at the price paid there, or the sector's menu", () => {
	useGameStore.setState({ builtSectorIds: ["padaria"], sectorTiers: { padaria: 3 } });
	const board = snapshot().sectors.find((s) => s.id === "padaria").board;
	expect(board.length).toBeGreaterThan(0);
	const first = itemCatalog.find((p) => p.id === board[0].productId);
	expect(board[0].price).toBe(Math.max(1, Math.round(first.sellingPrice * 1.1)));
});
