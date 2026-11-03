import type { LeagueDivision } from "@/@types/rankings";
import { isLeagueDivision, LEAGUE_DEMOTE, LEAGUE_PROMOTE, RANKING_TAB_REFRESH_MS, RANKING_TOP } from "@/data/rankings";
import { t } from "@/i18n";
import { type FriendsColumn, FRIENDS_COLUMNS, isoWeek, rolloverWeek, shouldSendPoints, sortFriendsBoard } from "@/services/rankings";
import type { RankingsState } from "@/@types/rankings";
import { normalizeRankingsState } from "@/services/rankings";
import { useGameStore } from "@/stores/game-store";
import { ensureSocialProfile, isVisiting, socialCall, socialIcon, socialMock, socialStore, socialTouched, type SocialReply } from "./social";

// Rankings v1 on the host (docs/rankings-api.md): the four boards of the "Ranking" window (Amigos · Liga · Mundo ·
// País), read only while the window is open (each tab at most every 60 s), the week's league points sent to the server
// (at most every 10 min, at the end of a day and when the app is paused or closed) and the window's actions. The calls
// go through Unity like social's (desktop/social.ts socialCall); in the Editor the fake server answers
// (desktop/rankings-mock.ts). The end-of-week reward arrives as a `league_reward` social inbox item
// (src/services/social.ts), so it is applied exactly once with the other inbox items.

export type RankingTab = "amigos" | "liga" | "mundo" | "pais";
export const RANKING_TABS: RankingTab[] = ["amigos", "liga", "mundo", "pais"];
/** One player on Mundo / País (and Amigos, with its extra columns). rank null = not ranked (opted out, hidden, no save). */
export type RankRow = {
	rank: number | null;
	id: string;
	code: string;
	marketName: string | null;
	avatar: string | null;
	level: number;
	xp: number;
	era: string;
	country: string | null;
};
export type FriendRank = RankRow & { weekPoints: number; likes: number; marketRating: number | null };
export type LeagueRow = { place: number; id: string; code: string; marketName: string | null; avatar: string | null; level: number; points: number; isFriend: boolean };
export type LevelBoard = { top: RankRow[]; me: RankRow | null; total: number; updatedAt: number; country?: string };
export type LeagueBoard = {
	week: string;
	endsAt: number;
	division: LeagueDivision;
	group: LeagueRow[];
	me: LeagueRow | null;
	promote: number;
	demote: number;
	rewards: { place: number; diamonds: number }[];
	lastWeek: { division: LeagueDivision; place: number; movedTo: LeagueDivision } | null;
};

type Loaded<T> = { data: T | null; loadedAt: number; error: string };
const empty = <T,>(): Loaded<T> => ({ data: null, loadedAt: 0, error: "" });

export const rankingsStore = {
	tab: "mundo" as RankingTab,
	column: "nivel" as FriendsColumn,
	world: empty<LevelBoard>(),
	country: empty<LevelBoard>(),
	friends: empty<FriendRank[]>(),
	league: empty<LeagueBoard>(),
	loading: new Set<RankingTab>(),
	busy: new Set<string>(),
	/** "Ver minha posição": the tile to scroll to, with a counter so pressing again scrolls again. */
	scroll: "",
	scrollCount: 0,
	/** The last league group seen this session, by week (the end-of-week card's podium uses its top 3). */
	podiums: new Map<string, LeagueRow[]>(),
	sending: false,
	lastSendCheck: 0,
	/** The window is open (boards are read only then). */
	open: false,
	/** Signed in when the boards were last read (signing in or out reloads every tab). */
	lastOnline: null as boolean | null,
	/** The Amigos board as the player had last opened it (the save's seenRanks when this opening began): the ▲/▼. */
	friendsBefore: null as RankingsState["seenRanks"] | null,
};

let send: (message: unknown) => void = () => {};
let refresh: () => void = () => {};
export function initRankings(options: { send: (message: unknown) => void; refresh: () => void }) {
	send = options.send;
	refresh = options.refresh;
}
export function resetRankings() {
	Object.assign(rankingsStore, {
		tab: "mundo",
		column: "nivel",
		world: empty(),
		country: empty(),
		friends: empty(),
		league: empty(),
		loading: new Set(),
		busy: new Set(),
		scroll: "",
		scrollCount: 0,
		podiums: new Map(),
		sending: false,
		lastSendCheck: 0,
		open: false,
		lastOnline: null,
		friendsBefore: null,
	});
}

/** Signed in (or the Editor's fake server, unless a QA run plays "signed out" there). */
export function rankingsOnline() {
	if (socialStore.mock) return !socialMock().rankings.signedOut;
	return socialStore.signedIn;
}
const errorOf = (reply: SocialReply) => (reply.body && typeof reply.body === "object" ? String((reply.body as { error?: unknown }).error ?? "") : "");
function trouble(reply: SocialReply) {
	if (reply.network || reply.code === 0) return "Sem conexão. Tente de novo daqui a pouco.";
	if (reply.code === 401) return "Entre na sua conta para aparecer no ranking.";
	if (errorOf(reply) === "slow-down") return "Calma! Tente de novo daqui a pouco.";
	return "Não foi possível agora.";
}
function toast(text: string, icon: Parameters<typeof socialIcon>[0] = "trophy", ok = true) {
	send({ kind: "social-toast", text, icon: socialIcon(icon), ok });
}

// ------------------------------------------------------------------------------------------------------------ parsing

const num = (value: unknown, fallback = 0) => (typeof value === "number" && Number.isFinite(value) ? value : fallback);
const text = (value: unknown) => (typeof value === "string" ? value : null);
function rowOf(raw: any): RankRow {
	return {
		rank: typeof raw?.rank === "number" && raw.rank > 0 ? raw.rank : null,
		id: String(raw?.id ?? ""),
		code: String(raw?.code ?? ""),
		marketName: text(raw?.marketName),
		avatar: text(raw?.avatar),
		level: Math.max(1, Math.floor(num(raw?.level, 1))),
		xp: Math.max(0, num(raw?.xp)),
		era: String(raw?.era ?? "mesinha"),
		country: typeof raw?.country === "string" && /^[A-Za-z]{2}$/.test(raw.country) ? raw.country.toUpperCase() : null,
	};
}
function boardOf(raw: any): LevelBoard {
	return {
		top: Array.isArray(raw?.top) ? raw.top.map(rowOf) : [],
		me: raw?.me ? rowOf(raw.me) : null,
		total: Math.max(0, Math.floor(num(raw?.total))),
		updatedAt: num(raw?.updatedAt),
		...(typeof raw?.country === "string" ? { country: raw.country.toUpperCase() } : {}),
	};
}
function leagueRowOf(raw: any): LeagueRow {
	return {
		place: Math.max(0, Math.floor(num(raw?.place))),
		id: String(raw?.id ?? ""),
		code: String(raw?.code ?? ""),
		marketName: text(raw?.marketName),
		avatar: text(raw?.avatar),
		level: Math.max(1, Math.floor(num(raw?.level, 1))),
		points: Math.max(0, Math.floor(num(raw?.points))),
		isFriend: raw?.isFriend === true,
	};
}
function leagueOf(raw: any): LeagueBoard {
	const division = isLeagueDivision(raw?.division) ? raw.division : "bronze";
	const last = raw?.lastWeek;
	return {
		week: typeof raw?.week === "string" ? raw.week : isoWeek(Date.now()),
		endsAt: num(raw?.endsAt),
		division,
		group: Array.isArray(raw?.group) ? raw.group.map(leagueRowOf).sort((a: LeagueRow, b: LeagueRow) => a.place - b.place) : [],
		me: raw?.me ? leagueRowOf(raw.me) : null,
		promote: Math.max(0, Math.floor(num(raw?.promote, LEAGUE_PROMOTE))),
		demote: Math.max(0, Math.floor(num(raw?.demote, LEAGUE_DEMOTE))),
		rewards: Array.isArray(raw?.rewards) ? raw.rewards.map((r: any) => ({ place: Math.floor(num(r?.place)), diamonds: Math.floor(num(r?.diamonds)) })) : [],
		lastWeek:
			last && isLeagueDivision(last.division)
				? { division: last.division, place: Math.floor(num(last.place)), movedTo: isLeagueDivision(last.movedTo) ? last.movedTo : last.division }
				: null,
	};
}

// ------------------------------------------------------------------------------------------------------------ loading

const paths: Record<RankingTab, string> = {
	mundo: `/v1/rankings/world?limit=${RANKING_TOP}`,
	pais: `/v1/rankings/country?limit=${RANKING_TOP}`,
	amigos: "/v1/rankings/friends",
	liga: "/v1/rankings/league",
};
const slot = (tab: RankingTab) => (tab === "mundo" ? rankingsStore.world : tab === "pais" ? rankingsStore.country : tab === "amigos" ? rankingsStore.friends : rankingsStore.league);

/** One tab's board (only while the window is open; at most every 60 s unless forced). Public boards load signed out. */
export async function loadRankingTab(tab: RankingTab, force = false) {
	const open = tab === "mundo" || tab === "pais";
	const online = rankingsOnline();
	if (rankingsStore.lastOnline !== online) {
		for (const each of RANKING_TABS) slot(each).loadedAt = 0;
		rankingsStore.lastOnline = online;
	}
	if (!online && !open) return false;
	const loaded = slot(tab);
	if (rankingsStore.loading.has(tab) || (!force && loaded.loadedAt && Date.now() - loaded.loadedAt < RANKING_TAB_REFRESH_MS)) return false;
	rankingsStore.loading.add(tab);
	refresh();
	try {
		// The first board of a signed-in player creates their social profile (opening Ranking counts, the contract).
		if (online) await ensureSocialProfile();
		const reply = await socialCall("GET", paths[tab], undefined, open);
		loaded.loadedAt = Date.now();
		if (reply.code !== 200 || !reply.body) {
			loaded.error = trouble(reply);
			return false;
		}
		loaded.error = "";
		if (tab === "mundo") rankingsStore.world.data = boardOf(reply.body);
		else if (tab === "pais") rankingsStore.country.data = boardOf(reply.body);
		else if (tab === "amigos") {
			rankingsStore.friends.data = Array.isArray(reply.body.rows) ? reply.body.rows.map((raw: any) => ({ ...rowOf(raw), weekPoints: Math.max(0, num(raw?.weekPoints)), likes: Math.max(0, num(raw?.likes)), marketRating: typeof raw?.marketRating === "number" ? Math.max(0, Math.min(5, raw.marketRating)) : null })) : [];
			noteFriendsSeen();
		}
		else {
			const league = leagueOf(reply.body);
			rankingsStore.league.data = league;
			if (league.group.length) rankingsStore.podiums.set(league.week, league.group.slice(0, 3));
		}
		return true;
	} finally {
		rankingsStore.loading.delete(tab);
		refresh();
	}
}

/** Opening the Ranking window (or one of its tabs): that tab loads; leaving it stops every read. */
export function onRankingRoute(route: string) {
	const [name, arg] = route.split(":");
	rankingsStore.open = name === "ranking";
	// (closing the window ends this opening: the next one shows ▲/▼ against what was seen now)
	if (!rankingsStore.open) {
		rankingsStore.friendsBefore = null;
		return;
	}
	const tab = RANKING_TABS.includes(arg as RankingTab) ? (arg as RankingTab) : rankingsStore.tab;
	rankingsStore.tab = tab;
	void loadRankingTab(tab, false);
}

/** The friends board rows as the Amigos tab sorts them (my own week points as this phone counts them). */
export function friendsRows(): FriendRank[] {
	const id = socialStore.me?.id ?? "";
	const points = useGameStore.getState().rankings?.points ?? 0;
	return (rankingsStore.friends.data ?? []).map((row) => (row.id === id ? { ...row, weekPoints: Math.max(row.weekPoints, points) } : row));
}

/**
 * The Amigos board was just read: the first time in this opening of the window, what the save remembers becomes the
 * baseline of the ▲/▼, and the places of now (every column) are remembered for the next opening.
 */
function noteFriendsSeen() {
	const rows = friendsRows();
	if (!rows.length) return;
	const store = useGameStore.getState();
	if (!rankingsStore.friendsBefore) rankingsStore.friendsBefore = normalizeRankingsState(store.rankings).seenRanks;
	const seen: RankingsState["seenRanks"] = {};
	for (const column of FRIENDS_COLUMNS) seen[column] = Object.fromEntries(sortFriendsBoard(rows, column).map((row, i) => [row.id, i + 1]));
	store.setRankingSeenRanks(seen);
}

/** While the window is open the shown tab refreshes on its own (each tab at most every 60 s). */
export function rankingTick() {
	if (rankingsStore.open && !isVisiting()) void loadRankingTab(rankingsStore.tab, false);
}

// ------------------------------------------------------------------------------------------------------------ league points

/**
 * Sends this week's league total when it changed: at most every 10 minutes (`force`: the end of a day, the app paused
 * or closed). Never while visiting a friend (the save is frozen), signed out, opted out or before the player has a
 * social profile (opened Amigos or Ranking once). A 409 `wrong-week` resets the week to the server's and sends again.
 */
export async function sendLeaguePoints(reason = "timer", force = false, now = Date.now()) {
	const store = useGameStore.getState();
	if (rankingsStore.sending || isVisiting() || !rankingsOnline() || !socialTouched()) return { sent: false, reason: "skip" };
	if (!shouldSendPoints(store.rankings, now, force)) return { sent: false, reason: "nothing" };
	rankingsStore.sending = true;
	try {
		for (let attempt = 0; attempt < 2; attempt++) {
			const state = rolloverWeek(useGameStore.getState().rankings, now);
			if (state.points <= 0) return { sent: false, reason: "nothing" };
			const reply = await socialCall("POST", "/v1/rankings/league/points", { week: state.week, points: state.points });
			if (isVisiting()) return { sent: false, reason: "visiting" };
			if (reply.code === 200 && reply.body) {
				useGameStore.getState().markLeaguePointsSent(state.week, Number(reply.body.points) || 0, now);
				// The league tab shows the new place next time it is read.
				rankingsStore.league.loadedAt = 0;
				return { sent: true, reason, points: Number(reply.body.points) || 0, place: Number(reply.body.place) || 0 };
			}
			if (reply.code === 409 && errorOf(reply) === "wrong-week") {
				useGameStore.getState().applyLeagueWrongWeek((reply.body as { week?: unknown })?.week, now);
				continue;
			}
			return { sent: false, reason: `http-${reply.code}` };
		}
		return { sent: false, reason: "wrong-week" };
	} finally {
		rankingsStore.sending = false;
	}
}

// ------------------------------------------------------------------------------------------------------------ actions

export const rankingActions = ["rankingColumn", "rankingOptOut", "rankingMyPosition", "rankingDismissCard", "rankingRefresh"];
type Result = { ok: boolean; reason: string };
const done = (ok: boolean, reason = ""): Result => ({ ok, reason });

export function requestRankingAction(action: string, args: unknown[]): Result {
	if (!rankingActions.includes(action)) return done(false, "invalid-action");
	if (isVisiting() && action !== "rankingRefresh") return done(false, "Volte ao seu mercado primeiro.");
	const [a] = args;
	switch (action) {
		case "rankingColumn": {
			const column = String(a ?? "") as FriendsColumn;
			if (!FRIENDS_COLUMNS.includes(column)) return done(false, "invalid-action");
			rankingsStore.column = column;
			return done(true);
		}
		case "rankingRefresh":
			void loadRankingTab(rankingsStore.tab, true);
			return done(true);
		case "rankingMyPosition": {
			const id = String(a ?? "");
			if (!id) return done(false, "Você está fora do top 100.");
			rankingsStore.scroll = id;
			rankingsStore.scrollCount++;
			return done(true);
		}
		case "rankingDismissCard":
			return done(useGameStore.getState().dismissLeagueCard(String(a ?? "all")));
		case "rankingOptOut": {
			if (!rankingsOnline()) return done(false, "Entre na sua conta para aparecer no ranking.");
			const optOut = a === true || a === "true";
			if (rankingsStore.busy.has("optout")) return done(false, "");
			rankingsStore.busy.add("optout");
			void setOptOut(optOut).finally(() => {
				rankingsStore.busy.delete("optout");
				refresh();
			});
			return done(true);
		}
	}
	return done(false, "invalid-action");
}

async function setOptOut(optOut: boolean) {
	const reply = await socialCall("PUT", "/v1/rankings/settings", { optOut });
	if (reply.code !== 204 && reply.code !== 200) {
		toast(t(trouble(reply)), "warning", false);
		return false;
	}
	useGameStore.getState().setRankingOptOut(optOut);
	toast(t(optOut ? "Você não aparece mais no ranking." : "Você aparece no ranking!"), "trophy");
	// Every board changes with it.
	for (const tab of RANKING_TABS) slot(tab).loadedAt = 0;
	void loadRankingTab(rankingsStore.tab, true);
	return true;
}

/** The week as the window shows it (never written by viewing: a new week only changes the save when points come). */
export const viewRankings = (now = Date.now()) => rolloverWeek(normalizeRankingsState(useGameStore.getState().rankings, now), now);
