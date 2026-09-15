import { expect, test } from "bun:test";
import { getUnlockedSimulatorSectorId } from "./simulator-sector-selection.ts";

test("opens the clicked sector directly when it is unlocked", () => {
	expect(getUnlockedSimulatorSectorId("padaria", 2)).toBe("padaria");
	expect(getUnlockedSimulatorSectorId("queijaria", 6)).toBe("queijaria");
});

test("falls back to the sector list for locked or unknown sectors", () => {
	expect(getUnlockedSimulatorSectorId("padaria", 1)).toBeNull();
	expect(getUnlockedSimulatorSectorId("acougue", 7)).toBeNull();
	expect(getUnlockedSimulatorSectorId("unknown", 100)).toBeNull();
});
