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
const {
	checkEraEvolution,
	createInitialEraState,
	finishEraConstruction,
	getEraForExpansions,
	getOfflineEraIncome,
	normalizeEraState,
	recordFinishedTurn,
	startEraEvolution,
} = await import("./market-era.ts");
const { getMarketEra } = await import("../data/economy.ts");

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();
const HOUR = 60 * 60_000;

test("a new game starts at the table on the sidewalk", () => {
	expect(store().era.id).toBe("mesinha");
	expect(store().era.construction).toBeNull();
});

test("saves from before the eras keep their market building", () => {
	expect(getEraForExpansions([])).toBe("mercadinho");
	expect(getEraForExpansions(["fresh-wing", "service-wing"])).toBe("supermercado");
	expect(getEraForExpansions(["fresh-wing", "premium-hall"])).toBe("hipermercado");
	expect(normalizeEraState(undefined, "supermercado").id).toBe("supermercado");
	expect(normalizeEraState({ id: "nope" }, "mercadinho").id).toBe("mercadinho");
	// Only the era right after the current one can be under construction.
	expect(
		normalizeEraState({ id: "tenda", construction: { eraId: "spati", startedAt: 0, endsAt: 1 } }, "mesinha")
			.construction,
	).toBeNull();
});

test("evolving pays the next era and opens it when the obra ends", () => {
	const era = createInitialEraState();
	expect(checkEraEvolution(era, 100).ok).toBe(false);
	expect(checkEraEvolution(era, 600).ok).toBe(true);
	const building = startEraEvolution(era, 1_000);
	expect(building.id).toBe("mesinha");
	expect(building.construction?.eraId).toBe("banca");
	const banca = getMarketEra("banca");
	expect(finishEraConstruction(building, 1_000 + banca.buildDurationMs - 1)).toBe(building);
	expect(finishEraConstruction(building, 1_000 + banca.buildDurationMs).id).toBe("banca");
	expect(checkEraEvolution(building, 1e9).ok).toBe(false);
});

test("the store charges the era, runs the obra and can finish it with diamonds", () => {
	useGameStore.setState({ coins: 1_000 });
	expect(store().evolveMarketEra()).toBe(true);
	expect(store().coins).toBe(400);
	expect(store().era.construction?.eraId).toBe("banca");
	expect(store().evolveMarketEra()).toBe(false);
	const diamonds = store().logistics.premiumCurrency;
	expect(store().finishMarketEraNow()).toBe(true);
	expect(store().era.id).toBe("banca");
	expect(store().logistics.premiumCurrency).toBeLessThan(diamonds);
	const snapshot = createSimulatorSnapshot(store(), "test", 1);
	expect(snapshot.era).toMatchObject({ id: "banca", index: 1, construction: null });
});

test("DEV jumps to any era and passing time finishes the obra", () => {
	expect(store().devSetMarketEra("conteiner")).toBe(true);
	expect(store().era.id).toBe("conteiner");
	useGameStore.setState({ coins: 1_000_000 });
	expect(store().evolveMarketEra()).toBe(true);
	expect(store().era.construction?.eraId).toBe("spati");
	expect(store().devPassTime(4)).toBe(true);
	expect(store().era.id).toBe("spati");
});

test("time away is worth part of a turn, more in bigger eras, up to 8 hours", () => {
	const mesinha = recordFinishedTurn(createInitialEraState("mesinha"), { profit: 1_000, customers: 20 });
	const hiper = { ...mesinha, id: "hipermercado" };
	const eightHours = getOfflineEraIncome(hiper, 8 * HOUR);
	expect(eightHours.coins).toBe(Math.floor(8 * getMarketEra("hipermercado").offlineTurnsPerHour * 1_000));
	expect(getOfflineEraIncome(hiper, 30 * HOUR).coins).toBe(eightHours.coins);
	expect(getOfflineEraIncome(mesinha, 8 * HOUR).coins).toBeLessThan(eightHours.coins);
	// Averages follow the finished turns.
	const next = recordFinishedTurn(mesinha, { profit: 2_000, customers: 30 });
	expect(next.averageTurnProfit).toBe(1_300);
	expect(recordFinishedTurn(mesinha, { profit: 5_000, customers: 0 })).toBe(mesinha);
});

test("the market only sells on its own when it was left open", () => {
	useGameStore.setState({
		era: { ...createInitialEraState("mercadinho"), averageTurnProfit: 1_000, averageTurnCustomers: 20 },
		market: { ...store().market, isOpen: false },
		lastSessionAt: Date.now() - 2 * HOUR,
		coins: 0,
	});
	store().processSessionResume();
	expect(store().coins).toBe(0);
	useGameStore.setState({
		market: { ...store().market, isOpen: true },
		lastSessionAt: Date.now() - 2 * HOUR,
	});
	store().processSessionResume();
	expect(store().coins).toBeGreaterThan(0);
	expect(store().offlineSummary?.coins).toBe(store().coins);
});
