/**
 * Rankings v1 (docs/rankings-api.md, Lucas 02/11): the friends ranking, the weekly league and the world / country
 * ranking by level. The save only keeps the player's own week (league points earned on this device), the opt-out and
 * the end-of-week card waiting to be seen; the boards themselves come from the server while the Ranking window is open.
 */

/** League divisions, lowest first (ids: the game localizes their names). */
export type LeagueDivision = "bronze" | "silver" | "gold" | "sapphire" | "ruby" | "emerald" | "diamond";

/** The `league_reward` inbox item as the receiving game shows it (the end-of-week card). */
export type LeagueRewardCard = {
	/** The inbox item id it came from (the card is shown once per item). */
	id: string;
	week: string;
	division: LeagueDivision;
	place: number;
	diamonds: number;
	/** Coins of the chest (3 × the receiver's gift value; 0 = no chest). */
	coins: number;
	movedTo: LeagueDivision;
	at: number;
};

export type RankingsState = {
	/** ISO week of `points` ("2026-W45"): by the device clock, unless the server said otherwise (`skew`). */
	week: string;
	/** League points earned this week (the week total is what the game sends). */
	points: number;
	/** When `points` last went up (ms). */
	pointsAt: number;
	/** When the week total was last sent (ms, 0 = never) and the total the server answered then. */
	lastSent: number;
	sentPoints: number;
	/** "Aparecer no ranking" switched off (mirrors the server's ranking_opt_out). */
	optOut: boolean;
	/**
	 * The server's 409 `wrong-week` wins: while the device clock says `deviceWeek`, the points count for `week` (the
	 * server's). Null = the device clock is right.
	 */
	skew: { week: string; deviceWeek: string } | null;
	/** Weeks whose league reward this save already got (belt and braces next to social.appliedInbox; last 12). */
	rewardedWeeks: string[];
	/** End-of-week cards not seen yet (oldest first; the diamonds and coins are already in the save). */
	cards: LeagueRewardCard[];
};
