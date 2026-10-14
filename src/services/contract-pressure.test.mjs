import { describe, expect, test } from "bun:test";
import {
	canClaimConsolation,
	getConsolationOffer,
	getContractPressure,
	nextContractMomentum,
	rollConsolation,
} from "./contract-pressure.ts";

const contract = { id: "c", kind: "revenue", difficulty: 2, icon: "coin", title: "C", description: "", target: 100, reward: { coins: 200, diamonds: 0, experience: 40 } };
const result = (completed, extra = {}) => ({ contract, contractCompleted: completed, contractProgress: completed ? 1 : 0.8, ...extra });

describe("contract pacing", () => {
	test("wins climb, the third in a row is a challenge, a miss eases the next day", () => {
		expect(getContractPressure(0, 10)).toEqual({ factor: 1, challenge: false });
		expect(getContractPressure(1, 10).factor).toBeCloseTo(1.08);
		const third = getContractPressure(2, 10);
		expect(third.challenge).toBe(true);
		expect(third.factor).toBeCloseTo(1.28);
		expect(getContractPressure(9, 10).factor).toBeCloseTo(1.32); // capped
		expect(getContractPressure(-1, 10).factor).toBeCloseTo(0.92);
		expect(getContractPressure(-5, 10).factor).toBeCloseTo(0.84);
		expect(getContractPressure(3, 2)).toEqual({ factor: 1, challenge: false }); // first days do not climb
	});
	test("momentum: kept +1, missed resets below zero, a free day keeps it", () => {
		expect(nextContractMomentum(2, true, true)).toBe(3);
		expect(nextContractMomentum(2, true, false)).toBe(-1);
		expect(nextContractMomentum(-1, true, false)).toBe(-2);
		expect(nextContractMomentum(-2, true, true)).toBe(1);
		expect(nextContractMomentum(2, false, false)).toBe(2);
	});
});

describe("consolation video", () => {
	test("only a missed contract offers it, once", () => {
		expect(canClaimConsolation(result(false))).toBe(true);
		expect(canClaimConsolation(result(true))).toBe(false);
		expect(canClaimConsolation(result(false, { consolation: { coins: 1, diamonds: 0, experience: 0, label: "" } }))).toBe(false);
		expect(canClaimConsolation({ contract: null, contractCompleted: false })).toBe(false);
	});
	test("half the contract's coins for sure plus one surprise", () => {
		expect(getConsolationOffer(result(false)).coins).toBe(100);
		expect(rollConsolation(result(false), 0.1)).toMatchObject({ coins: 100, diamonds: 3, experience: 0 });
		expect(rollConsolation(result(false), 0.5)).toMatchObject({ coins: 100, diamonds: 0, experience: 20 });
		expect(rollConsolation(result(false), 0.9)).toMatchObject({ coins: 200, diamonds: 0 });
		expect(rollConsolation(result(true), 0.1)).toBe(null);
	});
});

describe("offers with pacing", async () => {
	const { createDayOffers } = await import("./market-day.ts");
	test("a challenge day makes only the hard offer the Desafio, and every offer harder than a plain day", () => {
		const plain = createDayOffers(10, 8, undefined, 0);
		const climbing = createDayOffers(10, 8, undefined, 2);
		expect(climbing.filter((c) => c.challenge).length).toBe(1);
		expect(climbing.at(-1).challenge).toBe(true);
		for (let i = 0; i < plain.length; i++) {
			if (plain[i].kind === "satisfaction") expect(climbing[i].target).toBeGreaterThanOrEqual(plain[i].target);
			else expect(climbing[i].target).toBeGreaterThan(plain[i].target);
			expect(climbing[i].reward.coins).toBeGreaterThan(plain[i].reward.coins);
		}
		const eased = createDayOffers(10, 8, undefined, -1);
		expect(eased[0].target).toBeLessThanOrEqual(plain[0].target);
	});
});
