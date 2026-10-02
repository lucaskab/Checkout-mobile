import { beforeEach, expect, mock, test } from "bun:test";

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
const { getSectorBuildStatus, getNextShelfBuildStatus, getShopItemBuildStatus } =
	await import("./interior-construction.ts");
const { sectorBuildPlans } = await import("../data/interior-construction.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();
const snapshot = () => createSimulatorSnapshot(game(), "builds", 1);
const finishAll = () => game().processInteriorConstructions(Number.MAX_SAFE_INTEGER);
// The player drags a bought piece out of the inventory and confirms the layout.
const place = (...ids) =>
	game().saveInteriorLayout([
		...game().interior.items,
		...ids.map((id, i) => ({ id, type: id.split(":")[0], x: -4 + i * 2.5, z: 1, rot: 0 })),
	]);

test("reaching a sector's level does not open it: it is bought, placed and built", () => {
	// The bakery comes with the mercadinho (the market building).
	game().devSetMarketEra("mercadinho");
	game().setMarketLevel(19);
	useGameStore.setState({ coins: 50_000 });
	expect(snapshot().sectors.find((s) => s.id === "padaria").unlocked).toBe(false);
	expect(getSectorBuildStatus(game(), "padaria").status).toBe("available");
	expect(game().startProduction({ sectorId: "padaria", recipeId: "baguete-rustica" })).toBe(false);

	expect(game().buildSector("padaria", "coins")).toBe(true);
	expect(game().coins).toBe(50_000 - sectorBuildPlans.padaria.coinCost);
	// Bought: it waits in the inventory until the player picks its spot.
	expect(getSectorBuildStatus(game(), "padaria").status).toBe("stored");
	expect(snapshot().builds).toEqual([
		expect.objectContaining({ kind: "sector", targetId: "padaria", name: "Padaria", pending: true }),
	]);
	expect(finishAll()).toBe(false);
	expect(game().builtSectorIds).not.toContain("padaria");
	expect(game().buildSector("padaria", "coins")).toBe(false);

	expect(place("sector:padaria")).toBe(true);
	expect(getSectorBuildStatus(game(), "padaria").status).toBe("building");
	expect(snapshot().builds[0].pending).toBe(false);
	expect(snapshot().sectors.find((s) => s.id === "padaria").building).toBe(true);

	expect(finishAll()).toBe(true);
	expect(game().builtSectorIds).toContain("padaria");
	expect(snapshot().sectors.find((s) => s.id === "padaria").unlocked).toBe(true);
	expect(snapshot().builds).toEqual([]);
});

test("stored purchases never keep the market from opening", () => {
	game().setMarketLevel(5);
	game().devSetMarketEra("banca");
	useGameStore.setState({ coins: 50_000 });
	expect(game().unlockNextShelf()).toBe(true);
	// The build mode reports the bought shelf as still stored: it stays owned by its construction.
	const id = `shelf:${getNextShelfBuildStatus(game()).shelf.id}`;
	game().saveInteriorLayout([...game().interior.items, { id, type: "shelf", x: 0, z: 0, rot: 0, stored: true }]);
	expect(game().interior.items.some((item) => item.id === id)).toBe(false);
	expect(getNextShelfBuildStatus(game()).status).toBe("stored");
});

test("sectors need their expansion, their level and the market wing that has room for them", () => {
	useGameStore.setState({ coins: 1_000_000 });
	game().setMarketLevel(1);
	expect(game().buildSector("padaria", "coins")).toBe(false);
	game().setMarketLevel(30);
	// Açougue lives in the service wing, which is not built yet.
	expect(getSectorBuildStatus(game(), "acougue").status).toBe("locked");
	expect(game().buildSector("acougue", "coins")).toBe(false);
});

test("placed works wait in the builders' queue and diamonds finish them", () => {
	game().setMarketLevel(30);
	game().devSetMarketEra("mercadinho");
	useGameStore.setState({
		coins: 1_000_000,
		logistics: { ...game().logistics, premiumCurrency: 500 },
	});
	expect(game().buildSector("padaria", "coins")).toBe(true);
	// Buying more is always allowed: everything waits in the inventory.
	expect(game().unlockNextShelf()).toBe(true);
	const shelfId = getNextShelfBuildStatus(game()).shelf.id;
	expect(place("sector:padaria", `shelf:${shelfId}`)).toBe(true);
	expect(getSectorBuildStatus(game(), "padaria").status).toBe("building");
	const shelfStatus = getNextShelfBuildStatus(game());
	expect(shelfStatus.status).toBe("queued");
	const sector = game().interiorConstructions.find((item) => item.kind === "sector");
	const shelf = game().interiorConstructions.find((item) => item.kind === "shelf");
	// The shelf starts when the sector's works end.
	expect(shelf.startedAt).toBe(sector.endsAt);

	const cost = snapshot().builds.find((item) => item.kind === "sector").skipCost;
	expect(cost).toBeGreaterThan(0);
	expect(game().finishInteriorConstructionNow(sector.id)).toBe(true);
	expect(game().logistics.premiumCurrency).toBe(500 - cost);
	expect(game().builtSectorIds).toContain("padaria");
	// The queued shelf moves up and starts now.
	expect(getNextShelfBuildStatus(game()).status).toBe("building");
});

test("a new shelf is built where the player places it and opens when the works end", () => {
	game().setMarketLevel(5);
	game().devSetMarketEra("banca");
	useGameStore.setState({ coins: 50_000 });
	expect(game().unlockNextShelf()).toBe(true);
	const next = getNextShelfBuildStatus(game());
	expect(next.status).toBe("stored");
	expect(snapshot().shelves.find((s) => s.id === next.shelf.id).building).toBe(true);
	place(`shelf:${next.shelf.id}`);
	expect(getNextShelfBuildStatus(game()).status).toBe("building");
	finishAll();
	expect(snapshot().shelves.find((s) => s.id === next.shelf.id).unlocked).toBe(true);
});

test("the second checkout waits in the inventory, then the builders install it", () => {
	game().setMarketLevel(10);
	useGameStore.setState({ coins: 100_000 });
	expect(game().purchaseShopItem("extra-checkout", "coins")).toBe(true);
	expect(game().shop.ownedItemIds).not.toContain("extra-checkout");
	expect(getShopItemBuildStatus(game(), "extra-checkout").status).toBe("stored");
	expect(snapshot().builds[0]).toMatchObject({ kind: "shop", targetId: "extra-checkout", pending: true });
	expect(game().purchaseShopItem("extra-checkout", "coins")).toBe(false);
	place("checkout:extra");
	expect(getShopItemBuildStatus(game(), "extra-checkout").status).toBe("building");
	finishAll();
	expect(game().shop.ownedItemIds).toContain("extra-checkout");
	// Other shop items keep working instantly.
	expect(game().purchaseShopItem("simple-cart", "coins")).toBe(true);
	expect(game().shop.ownedItemIds).toContain("simple-cart");
});

test("old saves keep the sectors their level had already opened", async () => {
	const old = JSON.parse(initial);
	old.market.level = 25;
	delete old.builtSectorIds;
	delete old.interiorConstructions;
	const next = await useGameStore.persist.getOptions().migrate(old, 35);
	expect(next.builtSectorIds).toEqual(
		expect.arrayContaining(["padaria", "queijaria", "acougue", "bebidas"]),
	);
	expect(next.builtSectorIds).not.toContain("peixaria");
	expect(next.interiorConstructions).toEqual([]);
});
