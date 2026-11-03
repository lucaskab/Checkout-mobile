import type { LeagueDivision } from "@/@types/rankings";

// Rankings v1 numbers (docs/rankings-api.md). The server keeps the boards, the groups and the end of the week; these are
// the game's side: what earns league points, the divisions and rewards as the window shows them (mirror of the Worker's
// limits.ts) and how often the game talks to the server. Tune here.

/** League points per action (the server caps the week at maxPointsPerDay(level) × days, only to catch the impossible). */
export const LEAGUE_POINTS = {
	/** Each customer who bought (paid at the register). */
	customer: 1,
	/** The day's contract delivered (kept). */
	contract: 25,
	/** End of a day: each star of the day's rating (0–5, the customers' average satisfaction). */
	dayStar: 10,
	/** An evolution, an interior build, a stage (era) works or a lot clearing finished. */
	build: 50,
	/** A help on a friend's build (counted by the friends' server). */
	help: 5,
} as const;

/** The Worker's cap, for tests and the "how to earn" card: a day can never give more than this. */
export const maxLeaguePointsPerDay = (level: number) => 2000 + 300 * Math.max(1, Math.floor(level));

export const LEAGUE_DIVISIONS: readonly LeagueDivision[] = ["bronze", "silver", "gold", "sapphire", "ruby", "emerald", "diamond"];
export const isLeagueDivision = (value: unknown): value is LeagueDivision => LEAGUE_DIVISIONS.includes(value as LeagueDivision);
/** Division names (Portuguese; the game translates them) and their badge icon (Resources/CheckoutDesktop/Icons). */
export const LEAGUE_DIVISION_NAMES: Record<LeagueDivision, string> = {
	bronze: "Bronze",
	silver: "Prata",
	gold: "Ouro",
	sapphire: "Safira",
	ruby: "Rubi",
	emerald: "Esmeralda",
	diamond: "Diamante",
};
/** Colour of each division (the header band and the badge's glow), hex without #. */
export const LEAGUE_DIVISION_TINTS: Record<LeagueDivision, string> = {
	bronze: "8A4E24",
	silver: "5E6B7D",
	gold: "B07A12",
	sapphire: "1F4FA8",
	ruby: "A3213A",
	emerald: "1C7A4A",
	diamond: "2A8FA8",
};
export const leagueBadgeFile = (division: LeagueDivision) => `league-${division}`;
/** The division badges are placeholders (the medal recoloured) until the painted icons arrive under the same names. */
export const LEAGUE_ART_PLACEHOLDER = true;

/** Group size, promotion and demotion zones (the server sends promote/demote too; these are the defaults). */
export const LEAGUE_GROUP_MAX = 30;
export const LEAGUE_PROMOTE = 5;
export const LEAGUE_DEMOTE = 5;

/** Diamonds by final place before the division multiplier (the Worker's limits.ts; Lucas may tune). */
export const LEAGUE_PLACE_DIAMONDS: { place: number; diamonds: number }[] = [
	{ place: 1, diamonds: 20 },
	{ place: 2, diamonds: 15 },
	{ place: 3, diamonds: 10 },
	...[4, 5, 6, 7, 8, 9, 10].map((place) => ({ place, diamonds: 5 })),
];
export const LEAGUE_MULTIPLIER: Record<LeagueDivision, number> = { bronze: 1, silver: 1, gold: 1.5, sapphire: 1.5, ruby: 2, emerald: 2, diamond: 3 };
export const leagueRewardDiamonds = (place: number, division: LeagueDivision) =>
	Math.floor((LEAGUE_PLACE_DIAMONDS.find((row) => row.place === place)?.diamonds ?? 0) * LEAGUE_MULTIPLIER[division]);
/** The promotion chest: coins worth this many of the receiver's gift boxes (getSocialRewards(era).gift). */
export const LEAGUE_CHEST_GIFTS = 3;
/** A bad payload never pays more than this (the highest real reward is 20 × 3 = 60). */
export const LEAGUE_REWARD_DIAMONDS_MAX = 100;

/** Mundo / País: the top of the board the window shows. */
export const RANKING_TOP = 100;
/** Each tab is read at most this often while the window is open (the boards are cached on the server for 10 min). */
export const RANKING_TAB_REFRESH_MS = 60_000;
/** The week total goes out at most this often (plus at the end of a day and when the app is paused or closed). */
export const LEAGUE_SEND_EVERY_MS = 10 * 60_000;
/** End-of-week cards kept waiting, weeks remembered as rewarded. */
export const RANKING_CARDS_KEEP = 4;
export const RANKING_WEEKS_KEEP = 12;
/** Friends kept per column for the ▲/▼ of the Amigos board (a friends list is capped well under this). */
export const RANKING_SEEN_KEEP = 200;
