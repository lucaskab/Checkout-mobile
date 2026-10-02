import { expect, test } from "bun:test";
import { getNextSimulatorUnlocks } from "./simulator-progression.ts";

test("shows what the next level brings", () => {
	const unlocks = getNextSimulatorUnlocks(1, 3);

	expect(unlocks.length).toBeGreaterThan(0);
	expect(unlocks.every((unlock) => unlock.requiredLevel === 2)).toBe(true);
	expect(unlocks.some((unlock) => unlock.panel === "products")).toBe(true);
});

test("the sectors come later in the roadmap, with the market building", () => {
	const unlocks = getNextSimulatorUnlocks(18, 7);

	expect(unlocks.every((unlock) => unlock.requiredLevel === 19)).toBe(true);
	expect(unlocks[0]).toMatchObject({ label: "Padaria", panel: "sectors" });
});

test("returns no future milestone after the progression catalogue is complete", () => {
	expect(getNextSimulatorUnlocks(100, 9)).toEqual([]);
});
