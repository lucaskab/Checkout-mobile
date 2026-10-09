import { expect, test } from "bun:test";
import { gameEvents, getGameEvent } from "@/data/game-events";
import {
	advanceGameEvents,
	applyPassiveEventWear,
	createInitialGameEventsState,
	getActiveGameEventEffects,
	getAvailableGameEvents,
	getEventDemandMultiplier,
	getReferencePrice,
	inspectFixtures,
	pickFeaturedProduct,
} from "./game-events";

const MIN = 60_000;
const start = new Date(2026, 9, 3, 15, 0).getTime();
const turn = (open = true, key = "1:dia:" + start) => ({ endsAt: start + 5 * MIN, key, open, startedAt: start });

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

test("one event per open turn, starting 0:40–1:40 in, 1:30–2:30 long, never past the turn", () => {
	let state = createInitialGameEventsState(start);
	const seen = [];
	let length = 0;
	for (let now = start; now <= start + 5 * MIN; now += 1000) {
		const next = advanceGameEvents(state, now, turn());
		if (next) state = next;
		if (state.activeEvent && !seen.includes(state.activeEvent.startedAt)) {
			seen.push(state.activeEvent.startedAt);
			length = state.activeEvent.endsAt - state.activeEvent.startedAt;
		}
	}
	expect(seen.length).toBe(1);
	expect(seen[0] - start).toBeGreaterThanOrEqual(40_000);
	expect(seen[0] - start).toBeLessThanOrEqual(100_000 + 1000);
	expect(length).toBeGreaterThanOrEqual(90_000);
	expect(length).toBeLessThanOrEqual(150_000);
	expect(state.activeEvent).toBe(null);
});

test("closing the market ends the event at once and nothing runs while closed", () => {
	const t = (now) => turn(now < start + 2.5 * MIN);
	let { state } = run(createInitialGameEventsState(start), start, start + 2 * MIN, t);
	expect(state.activeEvent).not.toBe(null);
	({ state } = run(state, start + 2.5 * MIN, start + 30 * MIN, t));
	expect(state.activeEvent).toBe(null);
});

test("the next turn gets its own event", () => {
	const first = run(createInitialGameEventsState(start), start, start + 5 * MIN, turn()).state;
	const s2 = start + 7 * MIN;
	const second = run(first, s2, s2 + 5 * MIN, { endsAt: s2 + 5 * MIN, key: "1:noite:" + s2, open: true, startedAt: s2 });
	expect(second.seen.length).toBe(1);
});

test("a dev-triggered event survives a closed market and runs its full time", () => {
	const ev = { activeEvent: { endsAt: start + 4 * MIN, eventId: "hora-do-rush", startedAt: start }, lastEventId: "hora-do-rush", nextEventAt: 0, randomSeed: 3, turnKey: null };
	expect(advanceGameEvents(ev, start + MIN, turn(false))).toBe(null);
	expect(advanceGameEvents(ev, start + 4 * MIN + 1, turn(false)).activeEvent).toBe(null);
});

const ids = (context) => getAvailableGameEvents(context).map((event) => event.id);
const effectsOf = (id) => getActiveGameEventEffects(
	{ activeEvent: { endsAt: start + MIN, eventId: id, startedAt: start }, lastEventId: null, nextEventAt: 0, randomSeed: 1 },
	start,
);

test("the sidewalk table only draws events that fit a table on the sidewalk", () => {
	const table = ids({ eraId: "mesinha", hasRefrigeration: false, hasWorkingStaff: false });
	expect(table).toContain("hora-do-rush");
	expect(table).toContain("onda-de-calor");
	for (const id of ["sorteio-na-porta", "queda-de-energia", "cafe-com-a-equipe", "turno-puxado", "viralizou", "vigilancia-sanitaria", "carro-de-som", "dia-de-jogo"])
		expect(table).not.toContain(id);
});

test("team events need someone working, the power cut needs a fridge", () => {
	const noTeam = ids({ eraId: "spati", hasRefrigeration: false, hasWorkingStaff: false });
	expect(noTeam).not.toContain("cafe-com-a-equipe");
	expect(noTeam).not.toContain("queda-de-energia");
	const full = ids({ eraId: "spati", hasRefrigeration: true, hasWorkingStaff: true });
	expect(full).toContain("cafe-com-a-equipe");
	expect(full).toContain("turno-puxado");
	expect(full).toContain("queda-de-energia");
	expect(full).toContain("viralizou");
	expect(getAvailableGameEvents({ eraId: "rede", hasRefrigeration: true, hasWorkingStaff: true }).length).toBe(
		gameEvents.filter((event) => !event.retired).length,
	);
	expect(ids({ eraId: "rede", hasRefrigeration: true, hasWorkingStaff: true })).toContain("vigilancia-sanitaria");
	expect(ids({ eraId: "spati", hasRefrigeration: true, hasWorkingStaff: true })).not.toContain("vigilancia-sanitaria");
});

test("the turn only draws from the events it is given", () => {
	const only = [getGameEvent("chuva-forte")];
	let state = createInitialGameEventsState(start);
	for (let now = start; now <= start + 5 * MIN; now += 1000) state = advanceGameEvents(state, now, turn(), only) ?? state;
	expect(state.lastEventId).toBe("chuva-forte");
});

test("heat wave: cold drinks wanted twice as much, produce untouched by demand", () => {
	const heat = effectsOf("onda-de-calor");
	expect(getEventDemandMultiplier(heat, { category: "refrigerantes", productId: 1, sellingPrice: 5 }, undefined, 0)).toBe(2);
	expect(getEventDemandMultiplier(heat, { category: "hortifruti", productId: 2, sellingPrice: 5 }, undefined, 0)).toBe(1);
});

test("end of the month: cheaper products wanted more, dearer ones less", () => {
	const month = effectsOf("fim-do-mes");
	const reference = getReferencePrice([4, 6, 10, 30]);
	expect(reference).toBe(8);
	const cheap = getEventDemandMultiplier(month, { category: "mercearia", productId: 1, sellingPrice: 4 }, undefined, reference);
	const dear = getEventDemandMultiplier(month, { category: "mercearia", productId: 2, sellingPrice: 30 }, undefined, reference);
	expect(cheap).toBeGreaterThan(1.2);
	expect(dear).toBeLessThan(0.7);
});

test("viralizou: only the product in the video gets the boost", () => {
	const viral = effectsOf("viralizou");
	const featured = pickFeaturedProduct([7, 3, 3, 9], 5);
	expect([3, 7, 9]).toContain(featured);
	expect(getEventDemandMultiplier(viral, { category: "doces", productId: featured, sellingPrice: 5 }, featured, 0)).toBe(2);
	expect(getEventDemandMultiplier(viral, { category: "doces", productId: -1, sellingPrice: 5 }, featured, 0)).toBe(1);
	expect(pickFeaturedProduct([], 5)).toBe(undefined);
});

test("no event wears the shelves any more (the cleaning mechanic was removed)", () => {
	for (const event of gameEvents) {
		expect(event.effects.passiveWear ?? null).toBe(null);
		expect(event.effects.shelfWearMultiplier ?? 1).toBe(1);
	}
});

test("passive wear still only touches the listed categories", () => {
	const outage = { ...effectsOf("queda-de-energia"), passiveWear: { categories: ["laticinios"], perMinute: 5 } };
	const heat = { ...effectsOf("onda-de-calor"), passiveWear: { categories: ["hortifruti"], perMinute: 4 } };
	const fixtures = [
		{ id: "dairy", categories: ["laticinios"] },
		{ id: "produce", categories: ["hortifruti"] },
		{ id: "bakery", categories: [] },
	];
	const care = applyPassiveEventWear({ dairy: 90 }, outage, fixtures, 2 * MIN);
	expect(care.dairy).toBe(80);
	expect(care.produce).toBe(undefined);
	const wilted = applyPassiveEventWear({}, heat, fixtures, MIN);
	expect(wilted.produce).toBe(96);
	expect(wilted.dairy).toBe(undefined);
	const untouched = {};
	expect(applyPassiveEventWear(untouched, effectsOf("hora-do-rush"), fixtures, MIN)).toBe(untouched);
});

test("inspectFixtures fines each messy fixture and rewards a tidy market", () => {
	const rule = { minCondition: 60, fineShareOfGoal: 0.08, cleanReputationBonus: 3 };
	const messy = inspectFixtures({ produce: 40, drinks: 59, dairy: 80 }, ["produce", "drinks", "dairy"], rule, 1000);
	expect(messy.writtenUp).toEqual(["produce", "drinks"]);
	expect(messy.fine).toBe(160);
	expect(messy.reputationBonus).toBe(0);
	const tidy = inspectFixtures({ produce: 100 }, ["produce", "drinks"], rule, 1000);
	expect(tidy.fine).toBe(0);
	expect(tidy.reputationBonus).toBe(3);
});

test("card machine down: cash only and smaller budgets", () => {
	const card = effectsOf("maquininha-fora-do-ar");
	expect(card.cashOnly).toBe(true);
	expect(card.customerBudgetMultiplier).toBe(0.8);
	expect(card.revenueMultiplier).toBe(1);
	expect(effectsOf("sorteio-na-porta").extraBasketItems).toBe(1);
	expect(effectsOf("cafe-com-a-equipe").staffSpeedMultiplier).toBe(1.4);
});
