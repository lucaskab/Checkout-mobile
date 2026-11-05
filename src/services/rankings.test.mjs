import { afterAll, beforeEach, expect, mock, test } from "bun:test";

// Rankings v1 on the save (src/services/rankings.ts and the store): league points where the actions happen, the ISO
// week reset by the device clock, the server's wrong-week, the league_reward applied exactly once, sorting, opt-out.
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
const rankings = await import("./rankings.ts");
const { applyInboxItems } = await import("./social.ts");
const { LEAGUE_POINTS, LEAGUE_SEND_EVERY_MS, leagueRewardDiamonds, maxLeaguePointsPerDay } = await import("../data/rankings.ts");
const { getSocialRewards } = await import("../data/social.ts");

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();
const DAY = 86_400_000;
// Tuesday 3 Nov 2026 15:00 UTC (ISO week 45).
const NOW = Date.UTC(2026, 10, 3, 15, 0, 0);

test("ISO weeks: Monday 00:00 UTC starts a week; the year edges follow ISO 8601", () => {
	expect(rankings.isoWeek(NOW)).toBe("2026-W45");
	expect(rankings.isoWeek(Date.UTC(2026, 10, 2, 0, 0, 0))).toBe("2026-W45");
	expect(rankings.isoWeek(Date.UTC(2026, 10, 1, 23, 59, 59))).toBe("2026-W44");
	expect(rankings.isoWeek(Date.UTC(2021, 0, 3))).toBe("2020-W53");
	expect(rankings.isoWeek(Date.UTC(2024, 11, 30))).toBe("2025-W01");
	expect(rankings.weekStart("2026-W45")).toBe(Date.UTC(2026, 10, 2));
	expect(rankings.weekEndsAt("2026-W45")).toBe(Date.UTC(2026, 10, 9));
	expect(rankings.timeLeftText(Date.UTC(2026, 10, 9), Date.UTC(2026, 10, 6, 10, 0))).toBe("2d 14h");
});

test("old saves (no rankings field) load with defaults and nothing else changes (no version bump)", async () => {
	const options = useGameStore.persist.getOptions();
	expect(options.version).toBe(51);
	const old = JSON.parse(initial);
	delete old.rankings;
	const migrated = await options.migrate(old, 49);
	expect(migrated.rankings).toMatchObject({ points: 0, optOut: false, cards: [], rewardedWeeks: [] });
	expect(migrated.coins).toBe(old.coins);
	// garbage in the field keeps what is valid
	const odd = rankings.normalizeRankingsState({ week: "2026-W45", points: 12.7, optOut: true, cards: [{ id: 1 }], rewardedWeeks: ["x", "2026-W44"] }, NOW);
	expect(odd).toMatchObject({ week: "2026-W45", points: 12, optOut: true, cards: [], rewardedWeeks: ["2026-W44"] });
	// the persisted slice carries it
	expect(Object.keys(options.partialize(game()))).toContain("rankings");
});

test("addLeaguePoints counts this week and starts over when the ISO week changes", () => {
	let state = rankings.addLeaguePoints(undefined, 5, NOW);
	state = rankings.addLeaguePoints(state, 25, NOW + 60_000);
	expect(state).toMatchObject({ week: "2026-W45", points: 30, pointsAt: NOW + 60_000 });
	state = { ...state, sentPoints: 30, lastSent: NOW };
	const next = rankings.addLeaguePoints(state, 1, NOW + 7 * DAY);
	expect(next).toMatchObject({ week: "2026-W46", points: 1, sentPoints: 0 });
	// zero or negative never adds
	expect(rankings.addLeaguePoints(state, -4, NOW).points).toBe(30);
});

test("points are added where the actions happen: a paid customer, the day's end, builds, a friend's build helped", () => {
	const before = game().rankings.points;
	game().claimSocialHelperReward("help");
	expect(game().rankings.points).toBe(before + LEAGUE_POINTS.help);
	// the end of a day: the contract kept and the rating stars, once (the phase moves open → results)
	const day = game().day;
	useGameStore.setState({ day: { ...day, phase: "open", startedAt: Date.now() - 1000, endsAt: Date.now() - 1 } });
	const stats = { ...game().day.stats, satisfactionSamples: 2, satisfactionTotal: 160 };
	useGameStore.setState({ day: { ...game().day, stats } });
	const points0 = game().rankings.points;
	game().closeDay();
	expect(game().day.phase).toBe("results");
	const result = game().day.result;
	expect(game().rankings.points - points0).toBe(rankings.dayLeaguePoints(result));
	expect(rankings.dayStars(result)).toBe(4);
	game().closeDay();
	expect(game().rankings.points - points0).toBe(rankings.dayLeaguePoints(result));
	// a lot clearing finished
	const points1 = game().rankings.points;
	useGameStore.setState({ lots: { ...game().lots, clearing: { lotId: "B2", startedAt: Date.now() - 2000, endsAt: Date.now() - 1000 } } });
	expect(game().processLotClearing()).toBe(true);
	expect(game().rankings.points - points1).toBe(LEAGUE_POINTS.build);
	// an evolution finished
	const points2 = game().rankings.points;
	useGameStore.setState({ evolutions: [{ id: "e1", kind: "shelf", targetId: "produce", toTier: 2, durationMs: 1000, startedAt: Date.now() - 2000, endsAt: Date.now() - 1000 }] });
	expect(game().processFixtureEvolutions()).toBe(true);
	expect(game().rankings.points - points2).toBe(LEAGUE_POINTS.build);
});

test("each customer who bought (rung up at the register) is one league point", async () => {
	const { FREE_DAY_CONTRACT_ID } = await import("./market-day.ts");
	game().startDay(FREE_DAY_CONTRACT_ID);
	for (let tries = 0; tries < 30 && game().checkout.queue.length === 0; tries++) {
		useGameStore.setState({ market: { ...game().market, nextCustomerAt: 1 } });
		game().processNextCustomer();
	}
	const checkout = game().checkout.queue[0];
	expect(checkout).toBeTruthy();
	const points = game().rankings.points;
	expect(game().completeCheckout(checkout.id, checkout.total)).toBe(true);
	expect(game().rankings.points).toBe(points + LEAGUE_POINTS.customer);
});

test("day stars: 0–5 from the customers' average satisfaction; the contract adds 25", () => {
	expect(rankings.dayStars({ averageSatisfaction: 0 })).toBe(0);
	expect(rankings.dayStars({ averageSatisfaction: 49 })).toBe(2);
	expect(rankings.dayStars({ averageSatisfaction: 100 })).toBe(5);
	expect(rankings.dayLeaguePoints({ averageSatisfaction: 100, contractCompleted: true })).toBe(25 + 50);
	expect(rankings.dayLeaguePoints({ averageSatisfaction: 30, contractCompleted: false })).toBe(20);
});

test("sending: only new points, at most every 10 minutes unless forced, never opted out", () => {
	let state = rankings.addLeaguePoints(undefined, 40, NOW);
	expect(rankings.shouldSendPoints(state, NOW)).toBe(true);
	state = rankings.markPointsSent(state, "2026-W45", 40, NOW);
	expect(rankings.shouldSendPoints(state, NOW + 1000, true)).toBe(false);
	state = rankings.addLeaguePoints(state, 1, NOW + 1000);
	expect(rankings.shouldSendPoints(state, NOW + 2000)).toBe(false);
	expect(rankings.shouldSendPoints(state, NOW + 2000, true)).toBe(true);
	expect(rankings.shouldSendPoints(state, NOW + LEAGUE_SEND_EVERY_MS)).toBe(true);
	expect(rankings.shouldSendPoints({ ...state, optOut: true }, NOW + LEAGUE_SEND_EVERY_MS, true)).toBe(false);
	// the server's capped value is what counts as sent
	expect(rankings.markPointsSent(state, "2026-W45", 30, NOW).sentPoints).toBe(30);
	// an answer for a week already gone does not touch the new week
	const later = rankings.addLeaguePoints(state, 3, NOW + 7 * DAY);
	expect(rankings.markPointsSent(later, "2026-W45", 41, NOW + 7 * DAY).sentPoints).toBe(0);
	expect(maxLeaguePointsPerDay(10)).toBe(5000);
});

test("409 wrong-week: the server's week wins (device behind → counter starts over; device ahead → points kept)", () => {
	// the device still says W45 but the server is in W46
	let state = rankings.addLeaguePoints(undefined, 80, NOW);
	state = rankings.applyWrongWeek(state, "2026-W46", NOW);
	expect(state).toMatchObject({ week: "2026-W46", points: 0, skew: { week: "2026-W46", deviceWeek: "2026-W45" } });
	// points earned now count for the server's week while the device says W45
	state = rankings.addLeaguePoints(state, 5, NOW + 1000);
	expect(state).toMatchObject({ week: "2026-W46", points: 5 });
	// once the device reaches W46 itself the skew is dropped and the week goes on
	state = rankings.addLeaguePoints(state, 5, NOW + 7 * DAY);
	expect(state).toMatchObject({ week: "2026-W46", points: 10, skew: null });
	// the device ran ahead (W46) while the server is still in W45: the points stay, counted for W45
	let ahead = rankings.addLeaguePoints(undefined, 12, NOW + 7 * DAY);
	ahead = rankings.applyWrongWeek(ahead, "2026-W45", NOW + 7 * DAY);
	expect(ahead).toMatchObject({ week: "2026-W45", points: 12, sentPoints: 0 });
	// no week in the answer: start over for the device's week
	expect(rankings.applyWrongWeek(ahead, undefined, NOW)).toMatchObject({ week: "2026-W45", points: 0 });
	// through the store
	game().applyLeagueWrongWeek("2026-W46", NOW);
	expect(game().rankings.week).toBe("2026-W46");
});

test("league_reward is applied exactly once: diamonds, the coin chest (3 gifts) and the card", () => {
	const state = game();
	const diamonds0 = state.logistics.premiumCurrency;
	const coins0 = state.coins;
	const reward = { id: 501, kind: "league_reward", from: null, payload: { week: "2026-W44", division: "bronze", place: 2, diamonds: leagueRewardDiamonds(2, "bronze"), chest: true, movedTo: "silver" }, createdAt: NOW };
	const first = game().applySocialInbox([reward], NOW);
	expect(first.ack).toEqual(["501"]);
	expect(game().logistics.premiumCurrency).toBe(diamonds0 + 15);
	expect(game().coins).toBe(coins0 + 3 * getSocialRewards(state.era.id).gift);
	expect(game().rankings.cards).toHaveLength(1);
	expect(game().rankings.cards[0]).toMatchObject({ id: "501", place: 2, division: "bronze", movedTo: "silver", diamonds: 15 });
	// the ack got lost: the same item again is acked without paying
	const again = game().applySocialInbox([reward], NOW + 1000);
	expect(again.ack).toEqual(["501"]);
	expect(again.outcomes[0].applied).toBe(false);
	expect(game().logistics.premiumCurrency).toBe(diamonds0 + 15);
	// a second item for the same week (a server retry with another id) pays nothing either
	game().applySocialInbox([{ ...reward, id: 502 }], NOW + 2000);
	expect(game().logistics.premiumCurrency).toBe(diamonds0 + 15);
	expect(game().rankings.cards).toHaveLength(1);
	// 0 diamonds (every placed player gets the item): the card shows anyway
	game().applySocialInbox([{ ...reward, id: 503, payload: { week: "2026-W43", division: "silver", place: 28, diamonds: 0, chest: false, movedTo: "bronze" } }], NOW);
	expect(game().rankings.cards.map((c) => c.id)).toEqual(["501", "503"]);
	expect(game().logistics.premiumCurrency).toBe(diamonds0 + 15);
	// a bad payload never pays more than the cap
	const capped = applyInboxItems(game(), [{ ...reward, id: 504, payload: { week: "2026-W40", diamonds: 99999 } }], NOW);
	expect(capped.patch.logistics.premiumCurrency - game().logistics.premiumCurrency).toBe(100);
	// the card goes away when seen
	expect(game().dismissLeagueCard("501")).toBe(true);
	expect(game().rankings.cards.map((c) => c.id)).toEqual(["503"]);
});

test("friends board sorting by column; opt-out kept in the save", () => {
	const rows = [
		{ id: "a", level: 9, xp: 100, weekPoints: 10, likes: 4, marketRating: 4.1 },
		{ id: "b", level: 12, xp: 50, weekPoints: 300, likes: 1, marketRating: null },
		{ id: "c", level: 9, xp: 900, weekPoints: 300, likes: 12, marketRating: 4.8 },
	];
	expect(rankings.sortFriendsBoard(rows, "nivel").map((r) => r.id)).toEqual(["b", "c", "a"]);
	expect(rankings.sortFriendsBoard(rows, "semana").map((r) => r.id)).toEqual(["b", "c", "a"]);
	expect(rankings.sortFriendsBoard(rows, "curtidas").map((r) => r.id)).toEqual(["c", "a", "b"]);
	expect(rankings.sortFriendsBoard(rows, "nota").map((r) => r.id)).toEqual(["c", "a", "b"]);
	const level = [
		{ id: "x", level: 10, xp: 5, levelAt: 20 },
		{ id: "y", level: 10, xp: 5, levelAt: 10 },
		{ id: "z", level: 11, xp: 0, levelAt: 99 },
	].sort(rankings.compareLevelRows);
	expect(level.map((r) => r.id)).toEqual(["z", "y", "x"]);
	expect(rankings.isRanked({ rank: null })).toBe(false);
	expect(rankings.isRanked({ rank: 3 })).toBe(true);
	expect(game().setRankingOptOut(true)).toBe(true);
	expect(game().rankings.optOut).toBe(true);
	expect(game().setRankingOptOut(true)).toBe(false);
});
