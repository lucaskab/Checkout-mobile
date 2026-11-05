import { afterAll, beforeEach, expect, mock, test } from "bun:test";

// Rede de supermercados (Lucas 05/11: ideas 2 + 5 of claude/rede-supermercados-proposta.md, and "mesclar as 3 opções"
// for the distribution centre): the chain's brand and own products, the fleet that restocks the market (cheaper,
// faster, automatic), the city contracts and the branch stores.
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
const chain = await import("./chain.ts");
const data = await import("../data/chain.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { getSupplierCartQuote } = await import("./supplier-cart.ts");
const { createSimulatorSnapshot } = await import("./simulator-snapshot.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();
const MIN = 60_000;
const HOUR = 60 * MIN;

/** A save in the rede, level 55, rich, with the rede's products open. */
function rede(coins = 5_000_000) {
	game().setMarketLevel(55);
	game().devSetMarketEra("rede");
	useGameStore.setState({ coins });
	game().processChain();
}

test("the chain opens only in the rede", () => {
	expect(chain.isChainUnlocked("hipermercado")).toBe(false);
	expect(chain.isChainUnlocked("rede")).toBe(true);
	game().devSetMarketEra("hipermercado");
	expect(game().nameChain("Super Bom", "cesta")).toBe(false);
	expect(game().buyChainBranch("centro")).toBe(false);
	expect(createSimulatorSnapshot(game(), "t", 1).chain.unlocked).toBe(false);
});

test("naming: free the first time, emblem changes free, a new name costs diamonds", () => {
	rede();
	expect(game().chain.brand.namedAt).toBeNull();
	expect(chain.checkChainName("A").ok).toBe(false);
	expect(chain.checkChainName("x".repeat(19)).ok).toBe(false);
	expect(chain.checkChainName("  Super   Bom ").ok && chain.checkChainName("  Super   Bom ").name).toBe("Super Bom");
	expect(chain.checkChainName("Mercado do Zé").ok).toBe(true);
	expect(game().nameChain("Super Bom", "naoexiste")).toBe(false);
	expect(game().nameChain("Super Bom", "coroa")).toBe(true);
	expect(game().chain.brand).toMatchObject({ name: "Super Bom", emblem: "coroa", renames: 0 });
	expect(game().chain.brand.namedAt).toBeGreaterThan(0);
	// only the emblem: free
	const diamonds = game().logistics.premiumCurrency;
	expect(game().nameChain("Super Bom", "sol")).toBe(true);
	expect(game().logistics.premiumCurrency).toBe(diamonds);
	// a new name: diamonds
	useGameStore.setState({ logistics: { ...game().logistics, premiumCurrency: 100 } });
	expect(game().nameChain("Mega Bom", "sol")).toBe(true);
	expect(game().logistics.premiumCurrency).toBe(100 - data.CHAIN_RENAME_DIAMONDS);
	expect(game().chain.brand.renames).toBe(1);
	const snap = createSimulatorSnapshot(game(), "t", 1).chain;
	expect(snap).toMatchObject({ unlocked: true, named: true, name: "Mega Bom", emblem: "sol" });
});

test("the chain's own products open with the rede, cost less, earn more and come only from the centre", () => {
	rede();
	for (const { id, baseId } of data.privateLabelProducts) {
		const item = itemCatalog.find((p) => p.id === id);
		const base = itemCatalog.find((p) => p.id === baseId);
		expect(item.privateLabel).toBe(true);
		expect(game().market.unlockedProductIds).toContain(id);
		expect(item.purchasePrice).toBeLessThan(base.purchasePrice);
		expect(item.sellingPrice - item.purchasePrice).toBeGreaterThanOrEqual(base.sellingPrice - base.purchasePrice);
	}
	const supplier = getSupplierCartQuote(game(), { lines: [{ productId: 172, boxes: 1 }] });
	expect(supplier.reason).toContain("centro de distribuição");
	const fleet = getSupplierCartQuote(game(), { lines: [{ productId: 172, boxes: 1 }], via: "frota" });
	expect(fleet.reason).toBeNull();
	// a save that reached the rede before this version gets them on the next tick
	useGameStore.setState({ market: { ...game().market, unlockedProductIds: game().market.unlockedProductIds.filter((id) => id < 172) } });
	game().processChain();
	expect(game().market.unlockedProductIds).toContain(179);
});

test("restocking through the centre: 10% cheaper, half the time, a fleet truck instead of a supplier slot", () => {
	rede();
	const lines = [{ productId: 51, boxes: 1 }];
	const supplier = getSupplierCartQuote(game(), { lines });
	const fleet = getSupplierCartQuote(game(), { lines, via: "frota" });
	expect(fleet.reason).toBeNull();
	expect(fleet.total).toBe(Math.ceil(supplier.total * data.DC_PRICE_FACTOR));
	expect(fleet.deliveryDurationMs).toBeLessThan(supplier.deliveryDurationMs);
	expect(fleet.fleetTruckId).toBe("truck-1");
	expect(game().orderFromDistributionCenter(lines)).toBe(true);
	const order = game().logistics.orders[0];
	expect(order.fleetTruckId).toBe("truck-1");
	const truck = game().chain.fleet.trucks.find((t) => t.id === "truck-1");
	expect(truck.job).toMatchObject({ kind: "abastecer", refId: order.id });
	expect(truck.job.returnAt).toBeGreaterThan(truck.job.arriveAt);
	// the suppliers' slots stay free: every supplier slot can still be used
	expect(getSupplierCartQuote(game(), { lines }).reason).toBeNull();
	// dry truck busy: a dry load takes the refrigerated one; then no truck is left
	expect(game().orderFromDistributionCenter([{ productId: 52, boxes: 1 }])).toBe(true);
	expect(getSupplierCartQuote(game(), { lines: [{ productId: 55, boxes: 1 }], via: "frota" }).reason).toContain("frota");
	// cold goods need the refrigerated truck
	const cold = itemCatalog.find((p) => p.category === "carnes" && game().market.unlockedProductIds.includes(p.id) && p.acquisition === "supplier");
	useGameStore.setState({ chain: chain.createChainState() });
	useGameStore.setState({ chain: chain.withTruckJob(game().chain, "truck-2", { kind: "contrato", refId: "x", departAt: 0, arriveAt: Date.now() + HOUR, returnAt: Date.now() + 2 * HOUR }) });
	expect(getSupplierCartQuote(game(), { lines: [{ productId: cold.id, boxes: 1 }], via: "frota" }).reason).toContain("refrigerado");
});

test("trucks come back on their own and count the trip", () => {
	rede();
	const now = Date.now();
	const busy = chain.withTruckJob(game().chain, "truck-1", { kind: "abastecer", refId: "o", departAt: now - 3 * MIN, arriveAt: now - 2 * MIN, returnAt: now - MIN });
	const back = chain.releaseTrucks(busy, now);
	expect(back.fleet.trucks[0].job).toBeNull();
	expect(back.fleet.trucks[0].trips).toBe(1);
});

test("automatic restock sends a fleet truck with what runs low, keeping a coin reserve", () => {
	rede();
	game().nameChain("Rede Teste", "cesta");
	useGameStore.setState({ inventory: { ...game().inventory, 51: 0, 52: 0 } });
	expect(game().setChainAutoOrder(true)).toBe(true);
	game().processChain();
	expect(game().logistics.orders.some((order) => order.fleetTruckId)).toBe(true);
	// below the reserve nothing goes out
	useGameStore.setState({ coins: data.AUTO_ORDER_RESERVE - 1, logistics: { ...game().logistics, orders: [] }, chain: { ...chain.createChainState(), autoOrder: { enabled: true, lastAt: 0 } } });
	game().processChain();
	expect(game().logistics.orders.length).toBe(0);
});

test("fleet: buying trucks and the engine upgrades", () => {
	rede(10_000_000);
	const before = game().coins;
	expect(game().buyFleetTruck("seco")).toBe(true);
	expect(game().coins).toBe(before - data.FLEET_TRUCK_PRICES.seco[0]);
	expect(game().chain.fleet.trucks.map((t) => t.kind)).toEqual(["seco", "refrigerado", "seco"]);
	expect(game().chain.fleet.trucks[2].id).toBe("truck-3");
	expect(game().buyFleetTruck("seco")).toBe(true);
	expect(game().buyFleetTruck("seco")).toBe(true);
	expect(game().buyFleetTruck("seco")).toBe(false); // the list ran out
	expect(game().buyFleetTruck("refrigerado")).toBe(true);
	expect(game().upgradeFleetSpeed()).toBe(true);
	expect(chain.getTripFactor(game().chain)).toBe(data.FLEET_SPEED_FACTORS[1]);
	useGameStore.setState({ coins: 0 });
	expect(game().upgradeFleetSpeed()).toBe(false);
});

test("contracts: offers from the city, delivered from the stockroom by a truck, paid on arrival", () => {
	rede();
	game().nameChain("Rede Teste", "cesta");
	game().processChain();
	const offers = game().chain.contracts.offers;
	expect(offers.length).toBe(data.CONTRACT_OFFERS);
	for (const offer of offers) {
		expect(offer.lines.length).toBeGreaterThanOrEqual(2);
		expect(offer.reward).toBeGreaterThan(0);
		for (const line of offer.lines) expect(game().market.unlockedProductIds).toContain(line.productId);
		const cold = offer.lines.some((line) => chain.isColdCategory(itemCatalog.find((p) => p.id === line.productId).category));
		expect(offer.cold).toBe(cold);
	}
	// same serial, same offer (reloading the game does not reroll the board)
	expect(chain.createContractOffer(4, { catalog: itemCatalog, unlockedProductIds: game().market.unlockedProductIds, eraIndex: 10, now: 0 })).toEqual(
		chain.createContractOffer(4, { catalog: itemCatalog, unlockedProductIds: game().market.unlockedProductIds, eraIndex: 10, now: 0 }),
	);
	const offer = offers[0];
	// nothing in the stockroom: refused
	useGameStore.setState({ inventory: {} });
	expect(game().acceptChainContract(offer.id)).toBe(false);
	const inventory = Object.fromEntries(offer.lines.map((line) => [line.productId, line.units + 5]));
	useGameStore.setState({ inventory });
	expect(game().acceptChainContract(offer.id)).toBe(true);
	for (const line of offer.lines) expect(game().inventory[line.productId]).toBe(5);
	const taken = game().chain.contracts.offers.find((o) => o.id === offer.id);
	expect(taken.acceptedAt).toBeGreaterThan(0);
	const truck = game().chain.fleet.trucks.find((t) => t.id === taken.truckId);
	expect(truck.job.kind).toBe("contrato");
	expect(game().acceptChainContract(offer.id)).toBe(false);
	// when the truck reaches the client the reward is paid (coins, xp, maybe diamonds)
	const coins = game().coins;
	const xp = game().market.totalExperience;
	game().processChain(truck.job.arriveAt + 1);
	expect(game().coins).toBe(coins + offer.reward);
	expect(game().market.totalExperience).toBe(xp + offer.xp);
	expect(game().chain.contracts.completed).toBe(1);
	expect(game().chain.contracts.offers.some((o) => o.id === offer.id)).toBe(false);
});

test("contracts expire and new ones come in at the refresh", () => {
	rede();
	const now = Date.now();
	game().processChain(now);
	const ids = game().chain.contracts.offers.map((o) => o.id);
	game().processChain(now + data.CONTRACT_LIFETIME_MS + 1);
	const after = game().chain.contracts.offers.map((o) => o.id);
	expect(after.length).toBe(data.CONTRACT_OFFERS);
	expect(after.some((id) => ids.includes(id))).toBe(false);
});

test("branches: buy, works, income with the shelves going down, cargo refills, collect", () => {
	rede(10_000_000);
	const t0 = Date.now();
	const def = data.chainBranches.find((b) => b.id === "centro");
	expect(game().buyChainBranch("centro")).toBe(true);
	const works = game().chain.branches.centro.works;
	expect(works.level).toBe(1);
	expect(works.endsAt - t0).toBeGreaterThanOrEqual(def.buildMs - 1000);
	expect(game().buyChainBranch("centro")).toBe(false); // works running
	// works end: the store opens with full shelves and earns from then on
	const open = works.endsAt;
	let b = chain.updateBranch(game().chain.branches.centro, open);
	expect(b.level).toBe(1);
	expect(b.supply).toBe(1);
	expect(b.pending).toBe(0);
	// two hours later: about 2 h of income at ~92% shelves on average
	b = chain.updateBranch(b, open + 2 * HOUR);
	const perMin = chain.getBranchIncomePerMin("centro", 1);
	const rate = 1 / (data.BRANCH_SUPPLY_HOURS * 60);
	expect(b.pending).toBeCloseTo(perMin * 120 * (1 - (rate * 120) / 2), 0);
	expect(b.supply).toBeCloseTo(1 - rate * 120, 5);
	// after the shelves are empty it stops; pending is capped
	const later = chain.updateBranch(b, open + 48 * HOUR);
	expect(later.supply).toBe(0);
	expect(later.pending).toBeCloseTo(perMin * (data.BRANCH_SUPPLY_HOURS * 60) / 2, 0);
	// a cargo from the stockroom: favourites fill to the top
	useGameStore.setState({ chain: { ...game().chain, branches: { ...game().chain.branches, centro: later } } });
	const fav = itemCatalog.filter((p) => def.favorites.includes(p.category) && game().market.unlockedProductIds.includes(p.id)).slice(0, 4);
	useGameStore.setState({ inventory: Object.fromEntries(fav.map((p) => [p.id, 60])) });
	const cargo = chain.chooseBranchCargo("centro", 1, game().inventory, itemCatalog, game().market.unlockedProductIds);
	expect(cargo.total).toBe(data.BRANCH_CARGO_UNITS);
	expect(cargo.favoriteShare).toBe(1);
	expect(cargo.supply).toBe(1);
	expect(game().sendChainBranchCargo("centro")).toBe(true);
	const sent = fav.reduce((sum, p) => sum + (60 - game().inventory[p.id]), 0);
	expect(sent).toBe(data.BRANCH_CARGO_UNITS);
	const arrive = game().chain.branches.centro.cargo.arriveAt;
	expect(game().sendChainBranchCargo("centro")).toBe(false); // one at a time
	game().processChain(arrive + 1);
	expect(game().chain.branches.centro.cargo).toBeNull();
	expect(game().chain.branches.centro.supply).toBeGreaterThan(0.99);
	// collect everything waiting
	const coins = game().coins;
	expect(game().collectChainBranches()).toBe(true);
	expect(game().coins).toBeGreaterThan(coins);
	expect(game().chain.branches.centro.earned).toBeGreaterThan(0);
	// upgrading costs more and takes longer
	const step = chain.getBranchNextStep(game().chain.branches.centro);
	expect(step.level).toBe(2);
	expect(step.price).toBeGreaterThan(0);
});

test("diamonds finish a branch's works at once", () => {
	rede(10_000_000);
	game().buyChainBranch("praia");
	useGameStore.setState({ logistics: { ...game().logistics, premiumCurrency: 10_000 } });
	expect(game().finishChainBranchNow("praia")).toBe(true);
	expect(game().chain.branches.praia.level).toBe(1);
	expect(game().chain.branches.praia.works).toBeNull();
});

test("old saves: no chain slice becomes a fresh one; junk is cleaned; nothing else changes", () => {
	const fresh = chain.normalizeChainState(undefined);
	expect(fresh.fleet.trucks.map((t) => t.kind)).toEqual(["seco", "refrigerado"]);
	expect(fresh.brand.namedAt).toBeNull();
	const messy = chain.normalizeChainState({
		brand: { name: "Rede Velha", emblem: "xyz", namedAt: 5 },
		fleet: { trucks: [{ id: "truck-9", kind: "seco" }, { kind: "aviao" }], speedLevel: 99 },
		branches: { centro: { level: 7, supply: 3, pending: -4 } },
	});
	expect(messy.brand).toMatchObject({ name: "Rede Velha", emblem: "cesta", namedAt: 5 });
	expect(messy.fleet.trucks).toEqual([{ id: "truck-9", kind: "seco", job: null, trips: 0 }]);
	expect(messy.fleet.speedLevel).toBe(data.FLEET_SPEED_PRICES.length);
	expect(messy.branches.centro).toMatchObject({ level: 3, supply: 1, pending: 0 });
	expect(messy.branches.praia.level).toBe(0);
	// the store's migration keeps a v50 save as it was and adds the slice
	const persist = useGameStore.persist.getOptions();
	const v50 = JSON.parse(initial);
	delete v50.chain;
	const migrated = persist.migrate(v50, 50);
	expect(migrated.chain.fleet.trucks.length).toBe(2);
	expect(migrated.coins).toBe(v50.coins);
	expect(persist.version).toBe(51);
	expect(Object.keys(persist.partialize(game()))).toContain("chain");
});
