import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

// Store rating after an expansion arrives and the new-version prompt (Lucas 10/11).
globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const prompts = await import("./app-prompts.ts");
const { useGameStore } = await import("../stores/game-store.ts");
// Leave the shared store as it was found (the test files share it).
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const DAY = 86_400_000;
const now = new Date(2026, 10, 10, 12).getTime();

describe("review", () => {
	test("from the banca on, never during the tutorial, at most once in 30 days and 3 a year", () => {
		const ctx = { onboardingActive: false };
		expect(prompts.shouldAskForReview(undefined, "tenda", ctx, now)).toBe(false);
		expect(prompts.shouldAskForReview(undefined, "banca", { onboardingActive: true }, now)).toBe(false);
		expect(prompts.shouldAskForReview(undefined, "conteiner", ctx, now)).toBe(true);
		let state = prompts.noteReviewAsked(undefined, now);
		expect(prompts.shouldAskForReview(state, "spati", ctx, now + 10 * DAY)).toBe(false);
		expect(prompts.shouldAskForReview(state, "spati", ctx, now + 31 * DAY)).toBe(true);
		state = prompts.noteReviewAsked(state, now + 31 * DAY);
		state = prompts.noteReviewAsked(state, now + 62 * DAY);
		expect(prompts.shouldAskForReview(state, "rede", ctx, now + 100 * DAY)).toBe(false);
		expect(prompts.shouldAskForReview(state, "rede", ctx, now + 366 * DAY)).toBe(true);
	});

	test("closing the expansion's celebration asks once; the next one 30 days later", () => {
		const s = () => useGameStore.getState();
		const celebrate = (id) => useGameStore.setState({ celebrations: [{ id, kind: "era", targetId: "conteiner", at: now }], onboarding: { ...s().onboarding, status: "done" } });
		celebrate("era:conteiner:1");
		expect(s().dismissCelebration("era:conteiner:1")).toBe("review");
		expect(s().appPrompts.reviewAsks).toHaveLength(1);
		celebrate("era:conteiner:2");
		expect(s().dismissCelebration("era:conteiner:2")).toBeUndefined();
		expect(s().celebrations).toHaveLength(0);
	});
});

describe("update", () => {
	test("version compare", () => {
		expect(prompts.isNewerVersion("1.0.3", "1.0.2")).toBe(true);
		expect(prompts.isNewerVersion("1.0.10", "1.0.9")).toBe(true);
		expect(prompts.isNewerVersion("1.0.2", "1.0.2")).toBe(false);
		expect(prompts.isNewerVersion("1.0", "1.0.1")).toBe(false);
		expect(prompts.isNewerVersion("", "1.0.1")).toBe(false);
	});

	test("Agora não waits 2 days for the same version, not for a newer one", () => {
		const state = prompts.snoozeUpdate(undefined, "1.0.3", now);
		expect(prompts.isUpdateSnoozed(state, "1.0.3", now + DAY)).toBe(true);
		expect(prompts.isUpdateSnoozed(state, "1.0.3", now + 3 * DAY)).toBe(false);
		expect(prompts.isUpdateSnoozed(state, "1.0.4", now + DAY)).toBe(false);
	});
});
