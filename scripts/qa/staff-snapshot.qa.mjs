// QA fixture for the Unity staff playback (CheckoutStaff): builds real snapshots from the game store with a hired
// stock clerk, cleaner and cashier at work, floor dirt, a spill and emptied shelves, for each storage stage.
// Run: bun test ./scripts/qa/staff-snapshot.qa.mjs   (writes unity/CheckoutSimulator/Temp/staff-qa-*.json)
import { expect, mock, test } from "bun:test";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../../src/stores/game-store.ts");
const { createSimulatorSnapshot } = await import("../../src/services/simulator-snapshot.ts");
const { spawnFloorDirt } = await import("../../src/services/store-incidents.ts");
const initial = JSON.stringify(useGameStore.getState());
const out = join(import.meta.dir, "..", "..", "unity", "CheckoutSimulator", "Temp");

function stage(expansions) {
	useGameStore.setState(JSON.parse(initial));
	const s = useGameStore.getState();
	useGameStore.setState({ coins: 5_000_000, diamonds: 50_000, market: { ...s.market, level: 30 } });
	for (const id of expansions) {
		useGameStore.getState().unlockMarketExpansion(id, "coins");
		useGameStore.getState().processMarketExpansionConstruction(Number.MAX_SAFE_INTEGER);
	}
	for (const role of ["stock_clerk", "stock_clerk", "cleaner", "cashier"]) useGameStore.getState().hireEmployee(role);
	useGameStore.getState().setMarketOpen(true);
	// Emptied shelves for the clerks, floor dirt and a spill for the cleaner.
	const stock = { ...useGameStore.getState().shelfStock };
	for (const key of Object.keys(stock).slice(0, 6)) stock[key] = 0;
	useGameStore.setState({ shelfStock: stock });
	const shelves = useGameStore.getState().shelves ?? [];
	let incidents = useGameStore.getState().incidents;
	const now = Date.now();
	const list = Object.keys(useGameStore.getState().shelfStock).map((id, i) => ({
		category: "mercearia", price: 5, productId: i + 1, productName: "P" + i, shelfId: id.split(":")[0], shelfName: id, stock: 5,
	}));
	for (let t = 0; t < 4; t++) incidents = spawnFloorDirt(incidents, list, now + t * 200_000, true).state;
	const dirt = incidents.active.filter((i) => i.kind === "sujeira");
	const spill = { ...dirt[0], id: "qa-spill", kind: "derramado", createdAt: dirt[0].createdAt - 1 };
	useGameStore.setState({ incidents: { ...incidents, active: [...incidents.active, spill].map((i) => ({ ...i, createdAt: Math.min(i.createdAt, now) })) } });
	useGameStore.getState().processEmployeeWork();
	return createSimulatorSnapshot(useGameStore.getState(), "staff-qa-" + expansions.length, 1);
}

test("staff QA snapshots", () => {
	mkdirSync(out, { recursive: true });
	const variants = { doorstep: [], depot: ["fresh-wing", "service-wing", "stock-annex"], warehouse: ["fresh-wing", "service-wing", "stock-annex", "grand-warehouse"] };
	for (const [name, expansions] of Object.entries(variants)) {
		const snap = stage(expansions);
		writeFileSync(join(out, `staff-qa-${name}.json`), JSON.stringify(snap));
		console.log(name, JSON.stringify({ layout: snap.layout, tasks: snap.staffTasks.map((t) => [t.role, t.kind, t.shelfId, t.box ?? t.incidentKind, Math.round((t.endsAt - t.startedAt) / 1000)]) }));
		expect(snap.staffTasks.length).toBeGreaterThan(0);
	}
});
