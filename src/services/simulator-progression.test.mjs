import { expect, test } from "bun:test";
import { getNextSimulatorUnlocks } from "./simulator-progression.ts";

test("prioritizes major gameplay unlocks at the next level", () => {
	const unlocks = getNextSimulatorUnlocks(1, 4);

	expect(unlocks.every((unlock) => unlock.requiredLevel === 2)).toBe(true);
	expect(unlocks[0]).toMatchObject({ label: "Padaria", panel: "sectors" });
	expect(unlocks.some((unlock) => unlock.panel === "team")).toBe(true);
	expect(unlocks.some((unlock) => unlock.panel === "products")).toBe(true);
});

test("keeps shelf expansion in the shared level roadmap", () => {
	const unlocks = getNextSimulatorUnlocks(2, 4);

	expect(unlocks).toEqual(
		expect.arrayContaining([
			expect.objectContaining({
				label: "Nova gôndola",
				panel: "store",
				requiredLevel: 3,
			}),
		]),
	);
});

test("returns no future milestone after the progression catalogue is complete", () => {
	expect(getNextSimulatorUnlocks(100, 7)).toEqual([]);
});
