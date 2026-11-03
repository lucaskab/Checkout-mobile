import type { LeagueDivision } from "@/@types/rankings";
import { LEAGUE_DEMOTE, LEAGUE_DIVISIONS, LEAGUE_PLACE_DIAMONDS, LEAGUE_PROMOTE, leagueRewardDiamonds, maxLeaguePointsPerDay } from "@/data/rankings";
import { compareLevelRows, isoWeek, weekEndsAt, weekStart } from "@/services/rankings";
import { useGameStore } from "@/stores/game-store";

// A stand-in for the rankings routes of docs/rankings-api.md, in this process, for the Editor's QA and the tests (the
// Worker side is built in parallel). desktop/social-mock.ts forwards every /v1/rankings/* call here, so the same
// switch (Unity's "mock" status) answers both. A world of a few hundred made-up players over a dozen countries, a
// league group of 30 for the QA player once they send points, and the end-of-week reward as a social inbox item.
// The QA player's level and XP are read from the game (read-only); nothing here writes the player's store.

export type RankReply = { code: number; body: unknown; network: boolean };
type Player = {
	id: string;
	code: string;
	marketName: string | null;
	avatar: string;
	level: number;
	xp: number;
	levelAt: number;
	era: string;
	country: string | null;
	likes: number;
	marketRating: number;
	weekPoints: number;
	optOut: boolean;
};
type Member = { id: string; points: number; pointsAt: number };
export type RankingsMockLinks = {
	me: () => { id: string; code: string; marketName: string | null; avatar: string; likes: number };
	friendIds: () => string[];
	person: (id: string) => { id: string; code: string; marketName: string | null; avatar: string; level: number; era: string; likes: number } | undefined;
	push: (to: string, kind: string, from: string | null, payload: Record<string, unknown>) => unknown;
	now: () => number;
};

/** Promotion / demotion zone of a group of n (the Worker's rule). */
const zoneOf = (n: number) => Math.min(5, Math.floor(n / 2));
const reply = (code: number, body: unknown = null): RankReply => ({ code, body, network: false });
const fail = (code: number, error: string, extra: Record<string, unknown> = {}) => reply(code, { error, ...extra });
const CODE = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
/** The stage a level reaches (roughly the game's ladder). */
const eraOf = (level: number) =>
	level >= 40 ? "hipermercado" : level >= 30 ? "supermercado" : level >= 22 ? "mercadinho" : level >= 16 ? "minimercado" : level >= 12 ? "quitanda" : level >= 8 ? "spati" : level >= 5 ? "conteiner" : level >= 3 ? "banca" : level >= 2 ? "tenda" : "mesinha";

// Countries and some first names for the made-up markets (plain first names only).
const COUNTRIES: { code: string; weight: number; names: string[]; word: string }[] = [
	{ code: "BR", weight: 22, word: "Mercado", names: ["Ana", "João", "Carla", "Pedro", "Lia", "Rafa", "Bia", "Duda", "Léo", "Nina", "Caio", "Malu"] },
	{ code: "US", weight: 14, word: "Market", names: ["Emma", "Noah", "Olivia", "Liam", "Ava", "Mason", "Mia", "Ethan", "Grace", "Lucas"] },
	{ code: "DE", weight: 10, word: "Laden", names: ["Lena", "Paul", "Mia", "Jonas", "Hanna", "Felix", "Lea", "Max", "Emil", "Ida"] },
	{ code: "FR", weight: 8, word: "Épicerie", names: ["Léa", "Hugo", "Chloé", "Louis", "Manon", "Jules", "Inès", "Arthur"] },
	{ code: "ES", weight: 7, word: "Tienda", names: ["Lucía", "Hugo", "Sofía", "Pablo", "Martina", "Álvaro", "Carmen"] },
	{ code: "PT", weight: 5, word: "Mercearia", names: ["Inês", "Tomás", "Beatriz", "Diogo", "Leonor", "Rodrigo"] },
	{ code: "MX", weight: 6, word: "Tiendita", names: ["Valeria", "Diego", "Ximena", "Mateo", "Regina", "Emiliano"] },
	{ code: "AR", weight: 4, word: "Almacén", names: ["Sol", "Bautista", "Delfina", "Thiago", "Morena"] },
	{ code: "GB", weight: 6, word: "Shop", names: ["Amelia", "Oliver", "Isla", "George", "Poppy", "Harry"] },
	{ code: "IT", weight: 5, word: "Bottega", names: ["Giulia", "Leonardo", "Sofia", "Francesco", "Aurora"] },
	{ code: "JP", weight: 5, word: "Mart", names: ["Yui", "Haruto", "Aoi", "Sota", "Hina"] },
	{ code: "CA", weight: 4, word: "Market", names: ["Chloe", "Liam", "Maya", "Owen", "Zoe"] },
	{ code: "PL", weight: 2, word: "Sklep", names: ["Zofia", "Jan", "Hanna", "Antoni"] },
	{ code: "NL", weight: 2, word: "Winkel", names: ["Sanne", "Daan", "Fleur", "Bram"] },
];

/** A face for a made-up player: shopper-1…12 spread by a hash of the id (FNV-1a + a murmur finish; salt 3 keeps the
 * world's and Brazil's top four apart even when Unity has only 8 shoppers to draw). */
export function faceFor(id: string): string {
	let x = (2166136261 ^ 3) >>> 0;
	for (const ch of id) {
		x ^= ch.charCodeAt(0);
		x = Math.imul(x, 16777619) >>> 0;
	}
	x ^= x >>> 16;
	x = Math.imul(x, 0x85ebca6b) >>> 0;
	x ^= x >>> 13;
	x = Math.imul(x, 0xc2b2ae35) >>> 0;
	x ^= x >>> 16;
	return `shopper-${1 + ((x >>> 0) % 12)}`;
}

/** A small seeded random (the same world every run). */
function random(seed: number) {
	let state = seed >>> 0 || 1;
	return () => {
		state = (state * 1664525 + 1013904223) >>> 0;
		return state / 4294967296;
	};
}

export function createMockRankings(links: RankingsMockLinks, size = 400) {
	const rand = random(4521);
	const pick = <T,>(list: readonly T[]) => list[Math.floor(rand() * list.length)];
	const players = new Map<string, Player>();
	const takenNames = new Set<string>();
	const total = COUNTRIES.reduce((sum, c) => sum + c.weight, 0);
	const start = links.now();
	for (let i = 0; i < size; i++) {
		let roll = rand() * total;
		const country = COUNTRIES.find((c) => (roll -= c.weight) < 0) ?? COUNTRIES[0];
		// A long tail: most players are early, a few are far ahead (level 1–60).
		const level = Math.max(1, Math.min(60, Math.round(1 + 59 * Math.pow(rand(), 2.4))));
		const id = `w-${i + 1}`;
		const code = Array.from({ length: 8 }, () => pick(CODE.split(""))).join("");
		const name = pick(country.names);
		// Some names hidden (reported) or never chosen: the game shows "Mercado #<code>".
		const drawn = rand() < 0.06 ? null : `${country.word} ${name}${rand() < 0.3 ? ` ${1 + Math.floor(rand() * 99)}` : ""}`;
		// (no two markets of the made-up world share a name: a repeat gets the next free number; the draws stay the same)
		let marketName = drawn;
		for (let n = 2; marketName !== null && takenNames.has(marketName); n++) marketName = `${drawn} ${n}`;
		if (marketName !== null) takenNames.add(marketName);
		players.set(id, {
			id,
			code,
			marketName,
			// (the draw is kept so the world stays the same; the face comes from the id: varied, stable people)
			avatar: (rand(), faceFor(id)),
			level,
			xp: Math.floor(level * level * 120 + rand() * level * 200),
			levelAt: start - Math.floor(rand() * 40 * 86_400_000),
			era: eraOf(level),
			country: country.code,
			likes: Math.floor(rand() * 80),
			marketRating: Math.round((2.5 + rand() * 2.5) * 10) / 10,
			weekPoints: Math.floor(rand() * 1800),
			optOut: false,
		});
	}
	// The QA player (the social mock's "me"): BR, level / XP read from the game.
	const myCountry = "BR";
	let optOut = false;
	let signedOut = false;
	const meRow = (): Player => {
		const me = links.me();
		const market = useGameStore.getState().market;
		return {
			id: me.id,
			code: me.code,
			marketName: me.marketName,
			avatar: me.avatar || "",
			level: market.level,
			xp: market.totalExperience ?? 0,
			levelAt: start - 3_600_000,
			era: useGameStore.getState().era?.id ?? "mesinha",
			country: myCountry,
			likes: me.likes,
			marketRating: Math.round(Math.max(0, Math.min(100, market.customerSatisfaction ?? 50)) / 2) / 10,
			weekPoints: league.members.get(me.id)?.points ?? 0,
			optOut,
		};
	};
	const friendRow = (id: string): Player | undefined => {
		const p = links.person(id);
		if (!p) return undefined;
		const known = players.get(id);
		return known ?? { id: p.id, code: p.code, marketName: p.marketName, avatar: p.avatar, level: p.level, xp: p.level * p.level * 110, levelAt: start, era: p.era, country: "BR", likes: p.likes, marketRating: 4.3, weekPoints: 0, optOut: false };
	};
	// The friends are on the boards too (Ana, Bruno, Carla, Gabi of the social mock).
	for (const id of links.friendIds()) {
		const row = friendRow(id);
		if (row) players.set(id, row);
	}

	// ---- the league: one group of 30 (the QA player joins on their first points) ----
	const league = {
		week: isoWeek(start),
		division: "silver" as LeagueDivision,
		members: new Map<string, Member>(),
		lastWeek: { division: "bronze" as LeagueDivision, place: 2, movedTo: "silver" as LeagueDivision },
	};
	const groupIds = [...players.values()]
		.filter((p) => p.level >= 3 && p.level <= 14 && !p.id.startsWith("u-"))
		.slice(0, 26)
		.map((p) => p.id);
	const seedGroup = () => {
		league.members.clear();
		const friends = links.friendIds().slice(0, 3);
		for (const [i, id] of [...friends, ...groupIds].slice(0, 29).entries())
			league.members.set(id, { id, points: Math.max(0, Math.round(1450 - i * 52 - rand() * 30)), pointsAt: weekStart(league.week) + i * 60_000 });
		// a few who did not play yet this week (0 points: they will move down)
		for (const id of groupIds.slice(-3)) league.members.set(id, { id, points: 0, pointsAt: 0 });
	};
	seedGroup();
	let joined = false;

	const short = (p: Player) => ({ id: p.id, code: p.code, marketName: p.marketName, avatar: p.avatar || null });
	const levelRow = (p: Player, rank: number | null) => ({ rank, ...short(p), level: p.level, xp: p.xp, era: p.era, country: p.country });
	const listed = () => [...players.values(), meRow()].filter((p) => !p.optOut);
	function board(country: string | null, limit: number, authed: boolean) {
		const rows = listed()
			.filter((p) => !country || p.country === country)
			.sort(compareLevelRows);
		const me = meRow();
		const index = rows.findIndex((p) => p.id === me.id);
		return {
			top: rows.slice(0, limit).map((p, i) => levelRow(p, i + 1)),
			me: authed ? levelRow(me, me.optOut || index < 0 ? null : index + 1) : null,
			total: rows.length,
			updatedAt: links.now() - 4 * 60_000,
		};
	}
	const standings = () => {
		const me = links.me().id;
		return [...league.members.values()]
			.sort((a, b) => b.points - a.points || a.pointsAt - b.pointsAt || a.id.localeCompare(b.id))
			.map((m, i) => {
				const p = m.id === me ? meRow() : (players.get(m.id) ?? friendRow(m.id));
				return { place: i + 1, ...short(p!), level: p!.level, points: m.points, isFriend: links.friendIds().includes(m.id) };
			});
	};
	const topRow = (row: { id: string; code: string; marketName: string | null; avatar: string | null; points: number }) => ({ id: row.id, code: row.code, marketName: row.marketName, avatar: row.avatar, points: row.points });
	/** A made-up last week for the QA's end-of-week card: "up" (2nd in bronze → silver, the default), "down" (27th in
	 * silver → bronze), "same" (8th, stays in silver), "off" (4th, up but off the podium). The podium is real people of
	 * the group with me on my plinth. */
	function lastWeekReward(week: string, variant: string) {
		const me = links.me().id;
		const v = ({
			up: { division: "bronze", place: 2, movedTo: "silver", chest: true },
			down: { division: "silver", place: 27, movedTo: "bronze", chest: false },
			same: { division: "silver", place: 8, movedTo: "silver", chest: false },
			off: { division: "bronze", place: 4, movedTo: "silver", chest: true },
		} as const)[variant as "up"] ?? { division: "bronze", place: 2, movedTo: "silver", chest: true };
		const others = standings().filter((row) => row.id !== me);
		const mine = { ...standings().find((row) => row.id === me), ...short(meRow()), points: 0 };
		const order = [...others.slice(0, v.place - 1), mine, ...others.slice(v.place - 1)].slice(0, 30);
		const pointsAt = (place: number) => Math.max(0, Math.round(1500 - (place - 1) * 48));
		const top = order.slice(0, 3).map((row, i) => topRow({ ...row, avatar: row.avatar ?? null, points: pointsAt(i + 1) }));
		return {
			week,
			division: v.division,
			place: v.place,
			diamonds: leagueRewardDiamonds(v.place, v.division),
			chest: v.chest,
			movedTo: v.movedTo,
			points: pointsAt(v.place),
			size: 30,
			top,
		};
	}
	const rewardsTable = () => LEAGUE_PLACE_DIAMONDS.map((row) => ({ place: row.place, diamonds: leagueRewardDiamonds(row.place, league.division) }));

	function route(method: string, path: string, query: URLSearchParams, body: Record<string, unknown>): RankReply {
		const now = links.now();
		// a new week (the QA moves the clock): the lazy end of the week
		if (isoWeek(now) !== league.week) endWeek(isoWeek(now));
		const [head, second] = path.replace(/^\/v1\/rankings\/?/, "").split("/").filter(Boolean);
		const authed = !signedOut;
		const limit = Math.max(1, Math.min(100, Number(query.get("limit")) || 100));
		if (method === "GET" && head === "world") return reply(200, board(null, limit, authed));
		if (method === "GET" && head === "country") {
			const country = (query.get("country") || myCountry).toUpperCase();
			return reply(200, { country, ...board(country, limit, authed) });
		}
		if (!authed) return fail(401, "signed-out");
		if (method === "GET" && head === "friends") {
			const ids = [links.me().id, ...links.friendIds()];
			return reply(200, {
				rows: ids
					.map((id) => (id === links.me().id ? meRow() : friendRow(id)))
					.filter((p): p is Player => !!p)
					.map((p) => ({ ...levelRow(p, null), weekPoints: league.members.get(p.id)?.points ?? 0, likes: p.likes, marketRating: p.marketRating })),
			});
		}
		if (method === "GET" && head === "league") {
			const mine = joined && league.members.has(links.me().id);
			const group = mine ? standings() : [];
			return reply(200, {
				week: league.week,
				endsAt: weekEndsAt(league.week),
				division: league.division,
				group,
				me: mine ? (group.find((row) => row.id === links.me().id) ?? null) : null,
				// the server's zone: min(5, ⌊n/2⌋) for n listed players (5 / 5 before joining)
				promote: mine ? zoneOf(group.length) : LEAGUE_PROMOTE,
				demote: mine ? zoneOf(group.length) : LEAGUE_DEMOTE,
				rewards: rewardsTable(),
				lastWeek: league.lastWeek,
			});
		}
		if (method === "POST" && head === "league" && second === "points") {
			const week = body.week;
			const points = body.points;
			if (typeof week !== "string" || !Number.isInteger(points) || (points as number) < 0) return fail(400, "bad-request");
			if (week !== league.week) return fail(409, "wrong-week", { week: league.week });
			const me = links.me().id;
			const days = Math.min(7, Math.max(1, Math.ceil((now - weekStart(league.week)) / 86_400_000)));
			const cap = maxLeaguePointsPerDay(meRow().level) * days;
			const known = league.members.get(me);
			// joining takes at least 1 point (nobody is relegated for opening the app)
			if ((points as number) <= 0 && !known) return reply(200, { points: 0, place: null, groupSize: 0 });
			const stored = Math.max(known?.points ?? 0, Math.min(cap, points as number));
			if (!known || stored > known.points) league.members.set(me, { id: me, points: stored, pointsAt: now });
			// a group holds 30: the one who joins last takes the seat of a player who never played this week
			if (league.members.size > 30) {
				const idle = [...league.members.values()].find((m) => m.points === 0 && m.id !== me);
				if (idle) league.members.delete(idle.id);
			}
			joined = true;
			const group = standings();
			return reply(200, { points: stored, place: group.find((row) => row.id === me)?.place ?? 0, groupSize: group.length });
		}
		if (method === "PUT" && head === "settings") {
			if (typeof body.optOut !== "boolean") return fail(400, "bad-request");
			optOut = body.optOut;
			return reply(204);
		}
		return fail(404, "no-route");
	}

	/** The finished week's results: every place moves, the QA player gets a league_reward in the social inbox. */
	function endWeek(next: string) {
		const me = links.me().id;
		const group = standings();
		const row = group.find((entry) => entry.id === me);
		const zone = zoneOf(group.length);
		// every placed member gets a league_reward (diamonds may be 0), like the Worker
		if (row) {
			const promoted = row.place <= zone && row.points > 0;
			const demoted = row.place > group.length - zone || row.points <= 0;
			const index = LEAGUE_DIVISIONS.indexOf(league.division);
			const movedTo = promoted ? LEAGUE_DIVISIONS[Math.min(index + 1, LEAGUE_DIVISIONS.length - 1)] : demoted ? LEAGUE_DIVISIONS[Math.max(0, index - 1)] : league.division;
			links.push(me, "league_reward", null, {
				week: league.week,
				division: league.division,
				place: row.place,
				diamonds: row.points > 0 ? leagueRewardDiamonds(row.place, league.division) : 0,
				chest: promoted,
				movedTo,
				points: row.points,
				size: group.length,
				top: group.slice(0, 3).map(topRow),
			});
			league.lastWeek = { division: league.division, place: row.place, movedTo };
			league.division = movedTo;
		}
		league.week = next;
		joined = false;
		seedGroup();
	}

	return {
		call(method: string, path: string, body: Record<string, unknown>): RankReply {
			const [route0, search = ""] = path.split("?");
			return route(method.toUpperCase(), route0, new URLSearchParams(search), body);
		},
		/** QA controls (forwarded by the social mock's `control`). */
		control(command: string, arg = ""): boolean {
			if (command === "league-reward") {
				// last week ended ("<week>[:up|down|same|off]"; default: 2nd in bronze, promoted to silver with the chest)
				const [week0, variant = "up"] = arg.split(":");
				const week = week0 || isoWeek(links.now() - 7 * 86_400_000);
				links.push(links.me().id, "league_reward", null, lastWeekReward(week, variant));
				return true;
			}
			if (command === "friend-up") {
				// the last friend by level climbs past every friend (and the most likes): the Amigos ▲/▼ of the QA
				const friends = links.friendIds().map((id) => players.get(id)).filter((p): p is Player => !!p).sort(compareLevelRows);
				const top = friends[0];
				const last = friends.at(-1);
				if (!top || !last || top === last) return false;
				Object.assign(last, { level: top.level + 1, xp: top.xp + 5000, likes: Math.max(...friends.map((p) => p.likes)) + 5, era: eraOf(top.level + 1) });
				return true;
			}
			if (command === "signed-out") {
				signedOut = arg !== "off";
				return true;
			}
			if (command === "league-week") {
				endWeek(isoWeek(links.now() + 7 * 86_400_000));
				return true;
			}
			return false;
		},
		get signedOut() {
			return signedOut;
		},
		get optOut() {
			return optOut;
		},
		league,
		players,
	};
}

export type MockRankings = ReturnType<typeof createMockRankings>;
