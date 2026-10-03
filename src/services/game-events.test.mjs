import { expect, test } from "bun:test";
import { advanceGameEvents, createInitialGameEventsState } from "./game-events";

const MIN = 60_000;
const start = new Date(2026, 9, 3, 15, 0).getTime();
const turn = (open = true, key = "1:dia:" + start) => ({ endsAt: start + 10 * MIN, key, open, startedAt: start });

function run(events, from, to, t, step = 1000) {
	let state = events;
	const seen = [];
	for (let now = from; now <= to; now += step) {
		const next = advanceGameEvents(state, now, typeof t === "function" ? t(now) : t);
		if (next) state = next;
		if (state.activeEvent && !seen.includes(state.activeEvent.startedAt)) seen.push(state.activeEvent.startedAt);
	}
	return { state, seen };
}

test("one event per open turn, starting 1–4 min in, 3–5 min long, never past the turn", () => {
	const { state, seen } = run(createInitialGameEventsState(start), start, start + 10 * MIN, turn());
	expect(seen.length).toBe(1);
	expect(seen[0] - start).toBeGreaterThanOrEqual(MIN);
	expect(seen[0] - start).toBeLessThanOrEqual(4 * MIN + 1000);
	expect(state.activeEvent).toBe(null);
});

test("closing the market ends the event at once and nothing runs while closed", () => {
	const t = (now) => turn(now < start + 6 * MIN);
	let { state } = run(createInitialGameEventsState(start), start, start + 5 * MIN, t);
	expect(state.activeEvent).not.toBe(null);
	({ state } = run(state, start + 6 * MIN, start + 30 * MIN, t));
	expect(state.activeEvent).toBe(null);
});

test("the next turn gets its own event", () => {
	const first = run(createInitialGameEventsState(start), start, start + 10 * MIN, turn()).state;
	const s2 = start + 12 * MIN;
	const second = run(first, s2, s2 + 10 * MIN, { endsAt: s2 + 10 * MIN, key: "1:noite:" + s2, open: true, startedAt: s2 });
	expect(second.seen.length).toBe(1);
});

test("a dev-triggered event survives a closed market and runs its full time", () => {
	const ev = { activeEvent: { endsAt: start + 4 * MIN, eventId: "hora-do-rush", startedAt: start }, lastEventId: "hora-do-rush", nextEventAt: 0, randomSeed: 3, turnKey: null };
	expect(advanceGameEvents(ev, start + MIN, turn(false))).toBe(null);
	expect(advanceGameEvents(ev, start + 4 * MIN + 1, turn(false)).activeEvent).toBe(null);
});
