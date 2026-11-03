import type { DayResult } from "@/@types/market-day";
import type { FriendsRankColumn, LeagueRewardCard, LeagueTopRow, RankingsState } from "@/@types/rankings";
import { isLeagueDivision, LEAGUE_POINTS, LEAGUE_SEND_EVERY_MS, RANKING_CARDS_KEEP, RANKING_SEEN_KEEP, RANKING_WEEKS_KEEP } from "@/data/rankings";

// Rankings v1 on the player's own save (docs/rankings-api.md). Pure functions: the store applies what they return.
// League points live in the save for the current ISO week (Monday 00:00 UTC → next Monday, by the device clock) and the
// game sends the week total; when the server answers 409 `wrong-week` its week wins (`skew`).

const DAY = 86_400_000;
const WEEK = 7 * DAY;

export function createRankingsState(now = Date.now()): RankingsState {
	return { week: isoWeek(now), points: 0, pointsAt: 0, lastSent: 0, sentPoints: 0, optOut: false, skew: null, rewardedWeeks: [], cards: [], seenRanks: {} };
}

const num = (value: unknown, fallback = 0) => (typeof value === "number" && Number.isFinite(value) ? value : fallback);
const str = (value: unknown) => (typeof value === "string" ? value : "");
const WEEK_ID = /^\d{4}-W\d{2}$/;

function normalizeCard(value: unknown): LeagueRewardCard | null {
	const card = value as Partial<LeagueRewardCard> | null;
	if (!card || typeof card !== "object" || !str(card.id) || !WEEK_ID.test(str(card.week))) return null;
	return {
		id: str(card.id),
		week: str(card.week),
		division: isLeagueDivision(card.division) ? card.division : "bronze",
		place: Math.max(0, Math.floor(num(card.place))),
		diamonds: Math.max(0, Math.floor(num(card.diamonds))),
		coins: Math.max(0, Math.floor(num(card.coins))),
		movedTo: isLeagueDivision(card.movedTo) ? card.movedTo : isLeagueDivision(card.division) ? card.division : "bronze",
		at: num(card.at),
		top: normalizeLeagueTop(card.top),
		points: Math.max(0, Math.floor(num(card.points))),
		size: Math.max(0, Math.floor(num(card.size))),
	};
}

/** Saves from before rankings (no field) and anything odd in it: defaults, keeping whatever is valid (no version bump). */
export function normalizeRankingsState(value: unknown, now = Date.now()): RankingsState {
	const base = createRankingsState(now);
	const state = value as Partial<RankingsState> | null | undefined;
	if (!state || typeof state !== "object") return base;
	const skew = state.skew && WEEK_ID.test(str(state.skew.week)) && WEEK_ID.test(str(state.skew.deviceWeek)) ? { week: state.skew.week, deviceWeek: state.skew.deviceWeek } : null;
	return {
		week: WEEK_ID.test(str(state.week)) ? str(state.week) : base.week,
		points: Math.max(0, Math.floor(num(state.points))),
		pointsAt: num(state.pointsAt),
		lastSent: num(state.lastSent),
		sentPoints: Math.max(0, Math.floor(num(state.sentPoints))),
		optOut: state.optOut === true,
		skew,
		rewardedWeeks: Array.isArray(state.rewardedWeeks) ? state.rewardedWeeks.filter((week) => WEEK_ID.test(str(week))).slice(-RANKING_WEEKS_KEEP) : [],
		cards: Array.isArray(state.cards) ? state.cards.map(normalizeCard).filter((card): card is LeagueRewardCard => !!card).slice(-RANKING_CARDS_KEEP) : [],
		seenRanks: normalizeSeenRanks(state.seenRanks),
	};
}

function normalizeSeenRanks(value: unknown): RankingsState["seenRanks"] {
	const out: RankingsState["seenRanks"] = {};
	if (!value || typeof value !== "object") return out;
	for (const column of FRIENDS_COLUMNS) {
		const map = (value as Record<string, unknown>)[column];
		if (!map || typeof map !== "object") continue;
		const clean: Record<string, number> = {};
		for (const [id, rank] of Object.entries(map as Record<string, unknown>).slice(0, RANKING_SEEN_KEEP)) if (id && typeof rank === "number" && rank >= 1) clean[id] = Math.floor(rank);
		out[column] = clean;
	}
	return out;
}

/** A league `top` list from an inbox payload or a saved card: at most 3 well-formed rows. */
export function normalizeLeagueTop(value: unknown): LeagueTopRow[] {
	if (!Array.isArray(value)) return [];
	return value
		.slice(0, 3)
		.map((row) => {
			const r = row as Record<string, unknown> | null;
			if (!r || typeof r !== "object" || !str(r.id)) return null;
			return { id: str(r.id), code: str(r.code), marketName: str(r.marketName) || null, avatar: str(r.avatar) || null, points: Math.max(0, Math.floor(num(r.points))) };
		})
		.filter((row): row is LeagueTopRow => !!row);
}

/** ▲/▼ of a friend since the board was last opened: places gained (> 0), lost (< 0), 0 = same or new. */
export function rankTrend(seen: Record<string, number> | undefined, id: string, place: number): number {
	const before = seen?.[id];
	return before ? before - place : 0;
}

// ------------------------------------------------------------------------------------------------------------ weeks

/** ISO 8601 week of a moment in UTC: "2026-W45" (weeks start on Monday; week 1 holds the year's first Thursday). */
export function isoWeek(now: number): string {
	const date = new Date(now);
	const day = (date.getUTCDay() + 6) % 7; // Monday 0 … Sunday 6
	const thursday = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() - day + 3);
	const year = new Date(thursday).getUTCFullYear();
	const week = 1 + Math.floor((thursday - Date.UTC(year, 0, 1)) / WEEK);
	return `${year}-W${String(week).padStart(2, "0")}`;
}

/** Monday 00:00 UTC that starts an ISO week. */
export function weekStart(week: string): number {
	const [year, w] = week.split("-W").map(Number);
	const jan4 = Date.UTC(year, 0, 4);
	const monday1 = jan4 - ((new Date(jan4).getUTCDay() + 6) % 7) * DAY;
	return monday1 + (w - 1) * WEEK;
}
export const weekEndsAt = (week: string) => weekStart(week) + WEEK;

/** The week the points count for now: the device's, unless the server said otherwise while the device says that week. */
export function currentWeek(state: Pick<RankingsState, "skew">, now: number): string {
	const device = isoWeek(now);
	return state.skew && state.skew.deviceWeek === device ? state.skew.week : device;
}

/** A new week: last week's points are left behind (the server keeps its own copy) and the counter starts over. */
export function rolloverWeek(value: RankingsState | undefined, now: number): RankingsState {
	const loaded = normalizeRankingsState(value, now);
	// (a skew only holds while the device clock still says the week it was learned in)
	const state = loaded.skew && loaded.skew.deviceWeek !== isoWeek(now) ? { ...loaded, skew: null } : loaded;
	const week = currentWeek(state, now);
	if (week === state.week) return state;
	return { ...state, week, points: 0, pointsAt: 0, sentPoints: 0 };
}

/** The one helper every action calls: `n` league points this week (a new week starts the counter over). */
export function addLeaguePoints(value: RankingsState | undefined, n: number, now = Date.now()): RankingsState {
	const state = rolloverWeek(value, now);
	const points = Math.max(0, Math.floor(n));
	if (points <= 0) return state;
	return { ...state, points: state.points + points, pointsAt: now };
}

/** The end of a day: the contract kept and the day's rating stars (0–5 from the customers' average satisfaction). */
export function dayStars(result: Pick<DayResult, "averageSatisfaction">) {
	return Math.max(0, Math.min(5, Math.round(num(result.averageSatisfaction) / 20)));
}
export function dayLeaguePoints(result: Pick<DayResult, "averageSatisfaction" | "contractCompleted">) {
	return (result.contractCompleted ? LEAGUE_POINTS.contract : 0) + dayStars(result) * LEAGUE_POINTS.dayStar;
}

// ------------------------------------------------------------------------------------------------------------ sending

/**
 * Should the week total go out now? Only with points the server has not seen, never while opted out, and at most every
 * 10 minutes unless forced (end of a day, the app paused or closed).
 */
export function shouldSendPoints(value: RankingsState | undefined, now: number, force = false) {
	const state = rolloverWeek(value, now);
	if (state.optOut || state.points <= 0 || state.points === state.sentPoints) return false;
	return force || now - state.lastSent >= LEAGUE_SEND_EVERY_MS;
}

/** The server stored `points` for `week` (its value after the cap; never above what the game sent). */
export function markPointsSent(value: RankingsState | undefined, week: string, points: number, now: number): RankingsState {
	const state = rolloverWeek(value, now);
	if (week !== state.week) return { ...state, lastSent: now };
	return { ...state, lastSent: now, sentPoints: Math.max(0, Math.floor(num(points))) };
}

/**
 * 409 `wrong-week`: the server is in another week than the device clock. Its week wins: while the device says the week
 * it says now, points count for the server's week. Going forward (the device was behind) starts the counter over;
 * going back (the device ran ahead) keeps the points (they were earned in the server's week). Without a week in the
 * answer the counter starts over for the device's week.
 */
export function applyWrongWeek(value: RankingsState | undefined, serverWeek: unknown, now: number): RankingsState {
	const state = normalizeRankingsState(value, now);
	const device = isoWeek(now);
	const week = typeof serverWeek === "string" && WEEK_ID.test(serverWeek) ? serverWeek : "";
	if (!week) return { ...state, week: device, points: 0, pointsAt: 0, sentPoints: 0, skew: null, lastSent: 0 };
	const skew = week === device ? null : { week, deviceWeek: device };
	if (week === state.week) return { ...state, skew, lastSent: 0 };
	const ahead = state.week > week;
	return { ...state, week, points: ahead ? state.points : 0, pointsAt: ahead ? state.pointsAt : 0, sentPoints: 0, skew, lastSent: 0 };
}

/** "termina em 2d 14h" / "5h 20min" / "12min". */
export function timeLeftText(endsAt: number, now: number) {
	const left = Math.max(0, endsAt - now);
	const days = Math.floor(left / DAY);
	const hours = Math.floor((left % DAY) / 3_600_000);
	const minutes = Math.floor((left % 3_600_000) / 60_000);
	if (days > 0) return `${days}d ${hours}h`;
	if (hours > 0) return `${hours}h ${minutes}min`;
	return `${Math.max(1, minutes)}min`;
}

// ------------------------------------------------------------------------------------------------------------ boards

export type FriendsColumn = FriendsRankColumn;
export const FRIENDS_COLUMNS: FriendsColumn[] = ["nivel", "semana", "curtidas", "nota"];
export type FriendRankRow = { id: string; level: number; xp: number; weekPoints: number; likes: number; marketRating: number | null };

/** The friends board sorted by the chosen column (the server sends it unsorted); ties by level, XP, then id. */
export function sortFriendsBoard<T extends FriendRankRow>(rows: readonly T[], column: FriendsColumn): T[] {
	const key = (row: T) => (column === "semana" ? num(row.weekPoints) : column === "curtidas" ? num(row.likes) : column === "nota" ? num(row.marketRating) : num(row.level));
	return [...rows].sort((a, b) => key(b) - key(a) || num(b.level) - num(a.level) || num(b.xp) - num(a.xp) || String(a.id).localeCompare(String(b.id)));
}

/** Mundo / País order (the server's): level DESC, XP DESC, who got there first, id. */
export function compareLevelRows(a: { level: number; xp: number; levelAt?: number; id: string }, b: { level: number; xp: number; levelAt?: number; id: string }) {
	return b.level - a.level || b.xp - a.xp || num(a.levelAt) - num(b.levelAt) || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0);
}

/** Is this row's player on a board? Opted-out and hidden players (rank null) never are. */
export const isRanked = (row: { rank: number | null } | null | undefined): row is { rank: number } =>
	!!row && typeof row.rank === "number" && row.rank > 0;
