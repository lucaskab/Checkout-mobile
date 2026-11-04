import { afterAll, beforeEach, expect, mock, test } from "bun:test";

// Lucas 04/11: every special sector opens one expansion earlier ("de cada setor, você diminui uma expansão"), with
// build and evolution times in the band of the expansion it now opens in. Players already past those expansions keep
// everything; players in the minimercado / mercadinho / supermercado simply see the sector become available.
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
const { getSectorBuildStatus } = await import("./interior-construction.ts");
const { getLevelUnlocks } = await import("./level-unlocks.ts");
const { productionSectors, productionRecipes } = await import("../data/production-sectors.ts");
const { sectorBuildPlans } = await import("../data/interior-construction.ts");
const { getEvolutionDurationMs } = await import("../data/fixture-evolution.ts");
const { getSectorTierPrice } = await import("../data/fixture-tiers.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { getMarketEra, marketEras } = await import("../data/economy.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();
const MIN = 60_000;

const moved = {
	padaria: { era: "minimercado", level: 14, was: ["mercadinho", 18], coins: 8_000, ms: 20 * MIN, t2: 30 * MIN, t3: 75 * MIN },
	queijaria: { era: "mercadinho", level: 18, was: ["supermercado", 24], coins: 25_000, ms: 90 * MIN, t2: 60 * MIN, t3: 150 * MIN },
	acougue: { era: "mercadinho", level: 19, was: ["supermercado", 25], coins: 30_000, ms: 105 * MIN, t2: 60 * MIN, t3: 150 * MIN },
	bebidas: { era: "mercadinho", level: 20, was: ["supermercado", 26], coins: 35_000, ms: 120 * MIN, t2: 60 * MIN, t3: 150 * MIN },
	peixaria: { era: "supermercado", level: 25, was: ["hipermercado", 33], coins: 45_000, ms: 120 * MIN, t2: 90 * MIN, t3: 180 * MIN },
	sorvetes: { era: "supermercado", level: 28, was: ["hipermercado", 36], coins: 55_000, ms: 150 * MIN, t2: 90 * MIN, t3: 180 * MIN },
	adega: { era: "supermercado", level: 30, was: ["hipermercado", 38], coins: 65_000, ms: 180 * MIN, t2: 90 * MIN, t3: 180 * MIN },
};

test("each sector opens one expansion earlier, its level with it, the spacing inside each group kept", () => {
	for (const sector of productionSectors) {
		const want = moved[sector.id];
		expect({ id: sector.id, era: sector.eraId, level: sector.requiredLevel }).toEqual({ id: sector.id, era: want.era, level: want.level });
		expect(getMarketEra(sector.eraId).index).toBe(getMarketEra(want.was[0]).index - 1);
		expect(sectorBuildPlans[sector.id]).toEqual({ coinCost: want.coins, durationMs: want.ms });
		expect(getEvolutionDurationMs("sector", sector.id, 2)).toBe(want.t2);
		expect(getEvolutionDurationMs("sector", sector.id, 3)).toBe(want.t3);
		// the first recipe comes with the sector (or within 3 levels: the fresh meat and fish open the counter)
		const first = Math.min(...productionRecipes.filter((r) => r.sectorId === sector.id && !r.requiredSectorTier).map((r) => r.requiredLevel));
		expect(first - sector.requiredLevel).toBeLessThanOrEqual(3);
		expect(first).toBeLessThan(want.was[1] + 1);
	}
	// later sectors of the same expansion build a bit longer and cost a bit more
	for (const group of [["queijaria", "acougue", "bebidas"], ["peixaria", "sorvetes", "adega"]])
		for (let i = 1; i < group.length; i++) {
			expect(sectorBuildPlans[group[i]].durationMs).toBeGreaterThanOrEqual(sectorBuildPlans[group[i - 1]].durationMs);
			expect(sectorBuildPlans[group[i]].coinCost).toBeGreaterThan(sectorBuildPlans[group[i - 1]].coinCost);
		}
	expect(getSectorTierPrice(2, "minimercado")).toEqual({ coins: 10_000, diamonds: 30 });
	expect(getSectorTierPrice(3, "minimercado")).toEqual({ coins: 30_000, diamonds: 80 });
});

test("nothing opens later than before (a player past a level keeps what it opened)", () => {
	const before = { 101: 18, 102: 19, 103: 20, 104: 24, 105: 27, 106: 39, 107: 28, 108: 31, 109: 32, 110: 34, 111: 35, 112: 44, 113: 26, 114: 29, 115: 30, 116: 36, 117: 37, 118: 40, 119: 38, 120: 42, 121: 47, 27: 25, 57: 25, 44: 33, 45: 34, 43: 16, 24: 19 };
	for (const [id, level] of Object.entries(before)) {
		const product = itemCatalog.find((item) => item.id === Number(id));
		expect({ id, ok: product.unlockLevel <= level }).toEqual({ id, ok: true });
	}
});

test("the 'Desbloqueia no nível' list shows each sector at its new level and expansion", () => {
	for (const sector of productionSectors) {
		const at = getLevelUnlocks(sector.requiredLevel - 1, sector.requiredLevel, sector.eraId).find((u) => u.kind === "sector" && u.id === sector.id);
		expect(at).toMatchObject({ level: moved[sector.id].level, waitingEra: undefined });
		// one expansion before it: "chega com" that expansion
		const before = marketEras[getMarketEra(sector.eraId).index - 1].id;
		const early = getLevelUnlocks(sector.requiredLevel - 1, sector.requiredLevel, before).find((u) => u.id === sector.id);
		expect(early.waitingEra).toBe(sector.eraId);
	}
});

test("players now in the minimercado, mercadinho or supermarket see the sector become available", () => {
	useGameStore.setState({ coins: 1_000_000 });
	for (const [era, ids] of [["minimercado", ["padaria"]], ["mercadinho", ["queijaria", "acougue", "bebidas"]], ["supermercado", ["peixaria", "sorvetes", "adega"]]]) {
		game().devSetMarketEra(era);
		game().setMarketLevel(30);
		const layout = createSimulatorSnapshot(game(), "earlier", 1).layout;
		for (const id of ids) {
			expect(layout.sectorIds).toContain(id);
			expect({ era, id, status: getSectorBuildStatus(game(), id).status }).toEqual({ era, id, status: "available" });
		}
		// one expansion before: still "Chega com …"
		const before = marketEras[getMarketEra(era).index - 1].id;
		game().devSetMarketEra(before);
		for (const id of ids) expect(getSectorBuildStatus(game(), id).reason).toBe(`Chega com: ${getMarketEra(era).name}`);
	}
	// the bakery in the minimercado: bought, placed and built in 20 minutes
	game().devSetMarketEra("minimercado");
	game().setMarketLevel(14);
	expect(game().buildSector("padaria", "coins")).toBe(true);
	const works = game().interiorConstructions.find((item) => item.kind === "sector" && item.targetId === "padaria");
	expect(works.durationMs).toBe(20 * MIN);
});

test("a save past those expansions keeps its sectors, tiers, production and works exactly (migration)", async () => {
	const old = JSON.parse(initial);
	old.era = { ...old.era, id: "hipermercado" };
	old.market = { ...old.market, level: 40 };
	old.builtSectorIds = ["padaria", "queijaria", "acougue", "bebidas", "peixaria", "sorvetes"];
	old.sectorTiers = { padaria: 3, queijaria: 2 };
	const t = 1_800_000_000_000;
	// the wine cellar being built with its old time (3 h), an evolution of the ice cream counter with the old 2 h
	old.interiorConstructions = [{ id: "sector-adega-1", kind: "sector", targetId: "adega", startedAt: t, endsAt: t + 3 * 60 * MIN, durationMs: 3 * 60 * MIN }];
	old.evolutions = [{ id: "evolucao-sector-sorvetes-3-1", kind: "sector", targetId: "sorvetes", toTier: 2, durationMs: 30 * MIN, startedAt: t, endsAt: t + 30 * MIN }];
	const version = useGameStore.persist.getOptions().version;
	const next = await useGameStore.persist.getOptions().migrate(JSON.parse(JSON.stringify(old)), version);
	useGameStore.setState(next);
	const state = game();
	expect(state.builtSectorIds).toEqual(old.builtSectorIds);
	expect(state.sectorTiers).toEqual({ padaria: 3, queijaria: 2 });
	expect(state.interiorConstructions.find((c) => c.targetId === "adega")).toMatchObject({ endsAt: t + 3 * 60 * MIN, durationMs: 3 * 60 * MIN });
	expect(state.evolutions[0]).toMatchObject({ targetId: "sorvetes", endsAt: t + 30 * MIN, durationMs: 30 * MIN });
	// and a player in the mercadinho with the bakery built keeps it (it came with the mercadinho before)
	const mid = JSON.parse(initial);
	mid.era = { ...mid.era, id: "mercadinho" };
	mid.market = { ...mid.market, level: 20 };
	mid.builtSectorIds = ["padaria"];
	const back = await useGameStore.persist.getOptions().migrate(JSON.parse(JSON.stringify(mid)), version);
	expect(back.builtSectorIds).toEqual(["padaria"]);
});
