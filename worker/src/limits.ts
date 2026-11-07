/**
 * Social v1 numbers (docs/social-api.md › Numbers) — the server's side of the table, all in one place. Days are UTC
 * days (`dayOf(now)`); times are milliseconds since 1970.
 */
export const SOCIAL = {
	/** Friends per player. */
	maxFriends: 50,
	/** Pending outgoing friend requests per player. */
	maxOutgoingRequests: 20,
	/** Gifts: one per friend per day (sender side); the receiver is offered at most this many per day. */
	maxGiftsClaimedPerDay: 25,
	/** Helps: one per helper per build, at most this many per build. */
	maxHelpsPerBuild: 10,
	/** Helps given by one helper per day. */
	maxHelpsGivenPerDay: 30,
	/** Minutes one help takes off a build (inbox payload). */
	helpMinutes: 5,
	/** Product requests: open at once per player, units per request, lifetime. */
	maxOpenRequests: 2,
	minRequestQty: 1,
	maxRequestQty: 20,
	requestTtlMs: 24 * 60 * 60_000,
	/** Invite codes are redeemable only by accounts younger than this. */
	inviteRedeemWindowMs: 7 * 24 * 60 * 60_000,
	/** The invited player's level that rewards both players (8 = Späti). */
	inviteRewardLevel: 8,
	inviteRewardDiamonds: 30,
	/** The inviter's rewarded-invite counts that also unlock a decoration (`invite-reward-<n>`). */
	inviteMilestones: [1, 3, 5] as readonly number[],
	/** Market names. */
	nameMinChars: 3,
	nameMaxChars: 20,
	/** Distinct reporters that hide a market name until it is changed. */
	reportsToHide: 3,
	/** The public block sent with the save. */
	maxPublicBytes: 4 * 1024,
	maxPublicBuilds: 12,
	/** GET /v1/social/inbox answers at most this many items; POST …/ack takes at most this many ids. */
	inboxPage: 100,
	maxAckIds: 300,
	/** Housekeeping, done on the player's own writes (no cron): acked inbox items, closed product requests and
	 * build helps older than this are deleted; daily counters of past days too. */
	keepAckedMs: 7 * 24 * 60 * 60_000,
	keepClosedRequestsMs: 7 * 24 * 60 * 60_000,
	keepHelpsMs: 30 * 24 * 60 * 60_000,
} as const;

export const DAY_MS = 24 * 60 * 60_000;
/** The UTC day number (days since 1970-01-01). */
export const dayOf = (now: number) => Math.floor(now / DAY_MS);

/**
 * Rankings v1 numbers (docs/rankings-api.md) — the server's side, all in one place. Weeks are ISO weeks in UTC
 * (Monday 00:00 → next Monday 00:00), ids `YYYY-Www`.
 */
export const RANKINGS = {
	/** World / country boards: top N (default and maximum). */
	defaultTop: 100,
	maxTop: 100,
	/** How long a board's top list (and its total) is reused before D1 is asked again. */
	topCacheMs: 10 * 60_000,
	/** League groups: members at most, players in a level band (levels 1–5, 6–10, …). */
	groupSize: 30,
	levelBand: 5,
	/** Promotion / relegation zone of a group (top N / bottom N), see zoneOf for small groups. */
	zone: 5,
	/** League points cap: maxPointsPerDay(level) × days elapsed in the week (1–7). */
	pointsPerDayBase: 2000,
	pointsPerDayPerLevel: 300,
	/** Anything above this in a points body is a bad request (not a strike). */
	maxPointsBody: 1_000_000_000,
	/** Anti-cheat: more than this many levels in one upload is a strike (except while still in the early levels). */
	maxLevelJump: 5,
	/**
	 * The early levels cost minutes, not hours (src/services/progression.ts: EARLY_LEVELS = 12, they cost 12–100 % of the
	 * full price): a player who plays offline for a while can legitimately jump more than 5 of them in one upload.
	 */
	earlyLevels: 12,
	/**
	 * Anti-cheat climb clock (store.ts afterUpload): past the early levels, at most `climbBurstLevels` levels at once and
	 * then one level per `climbMsPerLevel` (7.5 levels an hour, for hours on end). Levels 13→23 cost ~55 k XP
	 * (src/services/progression.ts): even a binge player doing 10 levels an hour needs ~8 hours non-stop to overrun it
	 * once, and each overrun is one strike (the bucket refills). An edited save that climbs 5 levels every 5-minute
	 * upload overruns it about every 25 minutes.
	 */
	climbMsPerLevel: 8 * 60_000,
	climbBurstLevels: 20,
	/** Strikes that hide a player from every board (league points ignored, no league rewards). */
	strikesToHide: 3,
	/** League closes: groups per D1 batch (one transaction) and batches per cron run / per lazy close. */
	closeChunk: 100,
	lazyCloseChunks: 1,
	/** League rows of weeks older than this many weeks are deleted by the cron. */
	keepWeeks: 8,
} as const;

/**
 * The game's top level, for the anti-cheat "level above the game's max level". The game has no hard cap:
 * src/services/progression.ts applyExperience levels up forever (getExperienceToNextLevel has no table end) and the
 * unlock ladder ends at level 52 (src/data/level-ladder.test.mjs LAST_LADDER_LEVEL, from scripts/economy/catalog.py
 * SCHEDULE). Level 52 costs ~531 k XP in total (the designed ~1 month of play); level 200 costs ~14.5 M XP, ~27 times
 * that — years of play. So 200 only catches impossible numbers and never a real late-game player.
 */
export const MAX_LEVEL = 200;

/** League divisions, lowest first (ids; the game localizes). */
export const DIVISIONS = ["bronze", "silver", "gold", "sapphire", "ruby", "emerald", "diamond"] as const;
export type Division = (typeof DIVISIONS)[number];
/** Diamonds × this, rounded down (bronze 1, silver 1, gold 1.5, sapphire 1.5, ruby 2, emerald 2, diamond 3). */
export const DIVISION_MULTIPLIER: Record<Division, number> = { bronze: 1, silver: 1, gold: 1.5, sapphire: 1.5, ruby: 2, emerald: 2, diamond: 3 };
/** End-of-week diamonds by final place (before the multiplier): 1st 20, 2nd 15, 3rd 10, 4th–10th 5. */
export const PLACE_DIAMONDS: readonly number[] = [20, 15, 10, 5, 5, 5, 5, 5, 5, 5];

export const maxPointsPerDay = (level: number) => RANKINGS.pointsPerDayBase + RANKINGS.pointsPerDayPerLevel * level;
export const levelBandOf = (level: number) => Math.floor((Math.max(1, level) - 1) / RANKINGS.levelBand);
/** Diamonds for a final place in a division (0 past 10th). */
export const rewardDiamonds = (place: number, division: Division) => Math.floor((PLACE_DIAMONDS[place - 1] ?? 0) * DIVISION_MULTIPLIER[division]);
/**
 * Promotion / relegation zone size of a group with n ranked players: 5, but at most half the group, so a small group
 * never has a player both promoted and relegated (n = 30 → 5, 10 → 5, 6 → 3, 2 → 1, 1 → 0).
 */
export const zoneOf = (n: number) => Math.min(RANKINGS.zone, Math.floor(n / 2));

const WEEK_MS = 7 * DAY_MS;
/** Monday 00:00 UTC of the week holding `now` (1970-01-01 was a Thursday). */
export const weekStartOf = (now: number) => Math.floor((now - 4 * DAY_MS) / WEEK_MS) * WEEK_MS + 4 * DAY_MS;
/** The ISO week id of `now`, e.g. "2026-W45" (the ISO year is the year of the week's Thursday). */
export function weekOf(now: number) {
	const thursday = new Date(weekStartOf(now) + 3 * DAY_MS);
	const year = thursday.getUTCFullYear();
	const week = Math.floor((thursday.getTime() - Date.UTC(year, 0, 1)) / WEEK_MS) + 1;
	return `${year}-W${String(week).padStart(2, "0")}`;
}
/** Days of the week elapsed, the current one included (Monday = 1 … Sunday = 7). */
export const weekDayOf = (now: number) => Math.floor((now - weekStartOf(now)) / DAY_MS) + 1;
export const WEEK_ID = /^\d{4}-W(0[1-9]|[1-4]\d|5[0-3])$/;
