import type { Row } from "./cf.ts";
import { HEADERS, HttpError, json } from "./http.ts";
import {
	type Division,
	DIVISIONS,
	levelBandOf,
	maxPointsPerDay,
	PLACE_DIAMONDS,
	RANKINGS,
	rewardDiamonds,
	WEEK_ID,
	weekDayOf,
	weekOf,
	weekStartOf,
	zoneOf,
} from "./limits.ts";
import { previousWeek, RankingStore } from "./ranking-store.ts";
import { readBody } from "./social.ts";
import { type Profile, type Store, toProfile } from "./store.ts";

/**
 * Rankings v1 routes (docs/rankings-api.md — the contract with the game), all under /v1/rankings/:
 * - GET world?limit=100 and GET country?country=BR&limit=100 (signing in optional): the top list comes from the
 *   isolate's memory or the Cache API (10 min per board, country and limit), else one D1 query; `me` is one indexed
 *   COUNT, in the same round trip as the profile.
 * - GET friends, GET league, POST league/points, PUT settings (signed in).
 * Answers are ids and numbers only; times are milliseconds since 1970.
 */
export type BoardCache = {
	match(key: string): Promise<Response | undefined | null>;
	put(key: string, response: Response): Promise<void>;
};

export type RankingOptions = {
	store: Store;
	now: () => number;
	log: (line: string) => void;
	sessionOf: (request: Request) => Promise<string>;
	/** The player id of a valid session, null without one (rate limited like sessionOf). */
	maybeSessionOf: (request: Request) => Promise<string | null>;
	cache: BoardCache | null;
};

const fail = (status: number, error: string): never => {
	throw new HttpError(status, { error });
};

/** Cloudflare's request.cf.country, checked: two capital letters; "XX" (unknown), "T1" (Tor) and anything else → null. */
export function countryOf(value: unknown): string | null {
	return typeof value === "string" && /^[A-Z]{2}$/.test(value) && value !== "XX" ? value : null;
}

type Top = { top: ReturnType<typeof boardRow>[]; total: number; updatedAt: number };

/** Row = {rank, id, code, marketName, avatar, level, xp, era, country}. `own`: my own row (my name even when hidden). */
function boardRow(row: Row, rank: number | null, own = false) {
	return {
		rank,
		id: String(row.player_id),
		code: String(row.code),
		marketName: !own && Number(row.name_hidden) ? null : typeof row.market_name === "string" ? row.market_name : null,
		avatar: typeof row.avatar === "string" ? row.avatar : null,
		level: Number(row.level),
		xp: Number(row.xp ?? 0),
		era: String(row.era ?? ""),
		country: typeof row.country === "string" ? row.country : null,
	};
}

const division = (value: string): Division => ((DIVISIONS as readonly string[]).includes(value) ? (value as Division) : "bronze");
const rewardsOf = (d: Division) => PLACE_DIAMONDS.map((_, i) => ({ place: i + 1, diamonds: rewardDiamonds(i + 1, d) }));

export function rankingRoutes(options: RankingOptions) {
	const { store, now, sessionOf, maybeSessionOf, cache, log } = options;
	const rankings = new RankingStore(store);
	/** The top lists this isolate already holds (key → list), at most one per board, country and limit. */
	const memory = new Map<string, Top>();

	/** A board's top list and total: memory, then the Cache API, then D1 (and both caches are filled). */
	async function topOf(origin: string, country: string | null, limit: number): Promise<{ top: Top; from: string }> {
		const key = `${origin}/__cache/rankings/${country ? `country/${country}` : "world"}/${limit}`;
		const t = now();
		const fresh = (entry: Top | undefined | null) => !!entry && t - entry.updatedAt < RANKINGS.topCacheMs && entry.updatedAt <= t;
		const held = memory.get(key);
		if (fresh(held)) return { top: held as Top, from: "memory" };
		if (cache) {
			try {
				const hit = await cache.match(key);
				const entry = hit ? ((await hit.json()) as Top) : null;
				if (fresh(entry)) {
					memory.set(key, entry as Top);
					return { top: entry as Top, from: "cache" };
				}
			} catch (error) {
				log(`board cache read failed: ${(error as Error)?.message ?? error}`);
			}
		}
		const [rows, count] = await store.db.batch(rankings.top(country, limit));
		const top: Top = { top: rows.results.map((row, i) => boardRow(row, i + 1)), total: Number(count.results[0]?.total ?? 0), updatedAt: t };
		if (memory.size > 500) memory.clear();
		memory.set(key, top);
		if (cache) {
			try {
				await cache.put(key, new Response(JSON.stringify(top), { headers: { "content-type": "application/json", "cache-control": `public, max-age=${RANKINGS.topCacheMs / 1000}` } }));
			} catch (error) {
				log(`board cache write failed: ${(error as Error)?.message ?? error}`);
			}
		}
		return { top, from: "d1" };
	}

	/** Statements that create my profile when missing (opening the Ranking window counts) and keep its country. */
	const ensure = (id: string, country: string | null) => store.ensureProfile(id, country, true);

	/** Runs `[...ensure, ...reads]`; when my profile row is still missing (an invite code clash), socialMe makes it. */
	async function withProfile(id: string, country: string | null, reads: () => import("./cf.ts").D1PreparedStatement[]) {
		const first = ensure(id, country);
		let results = (await store.db.batch([...first, ...reads()])).slice(first.length);
		if (!results[0].results[0]) {
			if (!(await store.socialMe(id, false, country))) fail(401, "signed-out");
			results = await store.db.batch(reads());
		}
		return results;
	}

	async function board(req: Request, url: URL, byCountry: boolean, requestCountry: string | null) {
		const limitText = url.searchParams.get("limit");
		const asked = Number.parseInt(limitText ?? "", 10);
		const limit = Number.isFinite(asked) ? Math.min(RANKINGS.maxTop, Math.max(1, asked)) : RANKINGS.defaultTop;
		let wanted: string | null = null;
		if (byCountry && url.searchParams.has("country")) {
			wanted = countryOf((url.searchParams.get("country") ?? "").toUpperCase());
			if (!wanted) fail(400, "bad-request");
		}
		const id = await maybeSessionOf(req);
		let mine: { row: Row; profile: Profile } | null = null;
		if (id) {
			const [found] = await withProfile(id, requestCountry, () => [rankings.me(id, byCountry)]);
			const row = found.results[0];
			mine = { row, profile: toProfile(row) };
		}
		const country = byCountry ? (wanted ?? mine?.profile.country ?? requestCountry) : null;
		const headers = { ...HEADERS, "cache-control": id ? "private, no-store" : "public, max-age=60" };
		if (byCountry && !country) return new Response(JSON.stringify({ country: null, top: [], me: null, total: 0, updatedAt: now() }), { headers: { ...headers, "x-board-cache": "none" } });
		const { top, from } = await topOf(url.origin, country, limit);
		const onBoard = mine && (!byCountry || mine.profile.country === country);
		const me = mine && onBoard ? boardRow(mine.row, mine.row.rank == null ? null : Number(mine.row.rank), true) : null;
		const body = byCountry ? { country, top: top.top, me, total: top.total, updatedAt: top.updatedAt } : { top: top.top, me, total: top.total, updatedAt: top.updatedAt };
		return new Response(JSON.stringify(body), { status: 200, headers: { ...headers, "x-board-cache": from } });
	}

	/**
	 * Closes what must close before a league read or write: my own group of a past week (it decides my division) and,
	 * on the first calls of a new week when the cron did not run (or not to the end), one chunk of the other groups.
	 * Answers whether anything was closed (the caller reads again).
	 */
	async function lazyClose(state: Row) {
		let closed = 0;
		if (state.stale_group != null) closed += await rankings.closeGroups([Number(state.stale_group)]);
		if (Number(state.stale_any)) closed += (await rankings.closeStale(now(), RANKINGS.lazyCloseChunks)).closed;
		if (closed) log(`league lazy close: ${closed} groups`);
		return closed > 0 || state.stale_group != null;
	}

	return async (req: Request, path: string, method: string, requestCountry: string | null = null): Promise<Response | null> => {
		if (!path.startsWith("/v1/rankings/")) return null;
		const route = `${method} ${path.slice("/v1/rankings/".length)}`;
		try {
			switch (route) {
				case "GET world":
				case "GET country":
					return await board(req, new URL(req.url), route === "GET country", requestCountry);

				case "GET friends": {
					const id = await sessionOf(req);
					const [found] = await withProfile(id, requestCountry, () => [rankings.friends(id, weekOf(now()))]);
					const rows = found.results.map((row) => {
						const rating = Number(row.market_rating);
						return {
							...boardRow(row, null, row.player_id === id),
							weekPoints: Number(row.ranking_hidden) ? 0 : Number(row.week_points ?? 0),
							likes: Number(row.likes_total ?? 0),
							marketRating: row.market_rating == null || !Number.isFinite(rating) ? null : rating,
						};
					});
					// My own row first even when the query returned it elsewhere (the game sorts anyway).
					rows.sort((a, b) => Number(b.id === id) - Number(a.id === id));
					return json(200, { rows });
				}

				case "GET league": {
					const id = await sessionOf(req);
					const t = now();
					const week = weekOf(t);
					const reads = () => [rankings.state(id, week), rankings.group(id, week), rankings.lastWeek(id, previousWeek(t))];
					let [state, group, last] = await withProfile(id, requestCountry, reads);
					if (await lazyClose(state.results[0])) [state, group, last] = await store.db.batch(reads());
					const s = state.results[0];
					const mine = division(String(s.league_division ?? "bronze"));
					const ranked = group.results.filter((r) => r.player_id === id ? !Number(s.ranking_hidden) : true).length;
					const zone = group.results.length ? zoneOf(ranked) : RANKINGS.zone;
					const rows = group.results.map((r, i) => ({
						place: i + 1,
						id: String(r.player_id),
						code: String(r.code),
						marketName: r.player_id !== id && Number(r.name_hidden) ? null : typeof r.market_name === "string" ? r.market_name : null,
						avatar: typeof r.avatar === "string" ? r.avatar : null,
						level: Number(r.level),
						points: Number(r.points),
						isFriend: !!Number(r.is_friend),
					}));
					const l = last.results[0];
					return json(200, {
						week,
						endsAt: weekStartOf(t) + 7 * 24 * 60 * 60_000,
						division: mine,
						group: rows,
						me: rows.find((r) => r.id === id) ?? null,
						promote: zone,
						demote: zone,
						rewards: rewardsOf(mine),
						lastWeek: l ? { division: String(l.division), place: l.final_place == null ? null : Number(l.final_place), movedTo: String(l.moved_to ?? l.division) } : null,
					});
				}

				case "POST league/points": {
					const id = await sessionOf(req);
					const body = await readBody(req);
					const { week, points } = body;
					if (typeof week !== "string" || !WEEK_ID.test(week)) fail(400, "bad-request");
					if (typeof points !== "number" || !Number.isInteger(points) || points < 0 || points > RANKINGS.maxPointsBody) fail(400, "bad-request");
					const t = now();
					const current = weekOf(t);
					if (week !== current) throw new HttpError(409, { error: "wrong-week", week: current });
					let [state] = await withProfile(id, requestCountry, () => [rankings.state(id, current)]);
					if (await lazyClose(state.results[0])) [state] = await store.db.batch([rankings.state(id, current)]);
					const s = state.results[0];
					const stored = s.week_points == null ? null : Number(s.week_points);
					// Hidden players: points are ignored (nothing is written, they never join).
					if (Number(s.ranking_hidden)) return json(200, { points: stored ?? 0, place: null, groupSize: 0 });
					const level = Math.max(1, Number(s.level) || 1);
					const cap = maxPointsPerDay(level) * weekDayOf(t);
					const capped = Math.min(points as number, cap);
					// Above the cap: stored at the cap and one strike — once per crossing (the game resends its week total:
					// the same over-cap total again is not another strike until the cap has grown past what is stored).
					const strike = (points as number) > cap && (stored ?? 0) < cap;
					if (stored === null && capped < 1) {
						if (strike) await rankings.strike(id);
						return json(200, { points: 0, place: null, groupSize: 0 });
					}
					const answer = await rankings.sendPoints(id, current, levelBandOf(level), capped, stored !== null, strike);
					if (strike) log(`league points over the cap for ${id}: ${points} > ${cap}`);
					return json(200, answer);
				}

				case "PUT settings": {
					const id = await sessionOf(req);
					const body = await readBody(req);
					if (typeof body.optOut !== "boolean") fail(400, "bad-request");
					await rankings.setOptOut(id, body.optOut as boolean, ensure(id, requestCountry));
					return json(204, null);
				}
			}
		} catch (error) {
			// Before migrations/0003_rankings.sql: say so in the log (the route answers 500).
			store.missingRankings(error);
			throw error;
		}
		return null;
	};
}
