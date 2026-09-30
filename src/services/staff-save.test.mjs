import { expect, mock, test } from "bun:test";

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

// Saves written before the staff jobs existed have employees without tasks, nextTaskNumber or lastPayroll.
// Loading one used to crash the snapshot (desktop host: "Cannot read properties of undefined (reading 'map')").
test("a save from before the staff jobs loads, snapshots and plans work", async () => {
	const old = JSON.parse(JSON.stringify(useGameStore.getState()));
	old.employees = {
		employees: [{ efficiency: 2, experience: 0, id: "stock_clerk-1", isWorking: true, level: 1, name: "Repositor 1", role: "stock_clerk", salary: 240 }],
		nextHireNumber: 2,
		nextPayrollAt: 0,
		totalSalariesPaid: 0,
	};
	for (const key of Object.keys(old)) if (typeof old[key] === "function") delete old[key];
	memory.set("checkout.game", JSON.stringify({ state: old, version: 34 }));
	await useGameStore.persist.rehydrate();
	const state = useGameStore.getState();
	expect(state.employees.tasks).toEqual([]);
	expect(state.employees.nextTaskNumber).toBe(1);
	expect(state.employees.lastPayroll).toBe(null);
	expect(createSimulatorSnapshot(state, "old-save", 1).staffTasks).toEqual([]);
	expect(() => useGameStore.getState().processEmployeeWork()).not.toThrow();
});
