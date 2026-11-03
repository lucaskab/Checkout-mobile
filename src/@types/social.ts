/**
 * Social v1 (docs/social-api.md, Lucas 01/11): friends, invites, visits, help, gifts and product requests.
 * The save stays device-authoritative: what a friend does to the player arrives as an inbox item and the player's own
 * game applies it to its own save, exactly once (`appliedInbox`).
 */

/** Who did it (the server's short profile of the friend; null for system items). */
export type SocialSender = { id: string; code: string; marketName: string | null; avatar: string };

export type SocialInboxKind =
	| "gift"
	| "like"
	| "help"
	| "delivery"
	| "friend_request"
	| "friend_added"
	| "invite_reward"
	| "request_fulfilled"
	| "league_reward";

/** One unacked inbox item as `GET /v1/social/inbox` returns it. */
export type SocialInboxItem = {
	id: number | string;
	kind: string;
	from: SocialSender | null;
	payload: Record<string, unknown>;
	createdAt: number | string;
};

/** One of the player's open "Pedir aos amigos" requests (mirror of the server's, for the stock page). */
export type SocialRequestMirror = { id: number; productId: number; qty: number; createdAt: number; expiresAt: number };

export type SocialState = {
	/** Ids of the inbox items already applied to this save (newest last, at most SOCIAL_APPLIED_KEEP). */
	appliedInbox: string[];
	/** Gifts opened on `day` (UTC "YYYY-MM-DD"): at most SOCIAL_GIFTS_PER_DAY a day, the rest wait for tomorrow. */
	gifts: { day: string; claimed: number };
	/** The player's own social profile as last seen (code "" = never loaded). */
	profile: { code: string; marketName: string; avatar: string };
	/** The player's open product requests. */
	requests: SocialRequestMirror[];
	/** Invite rewards: milestones (1 / 3 / 5 rewarded invites) whose decoration was given, and the invited bonus. */
	invites: { milestones: number[]; invited: boolean };
	/** Lifetime counts (the Amigos page shows them; nothing depends on them). */
	totals: { gifts: number; likes: number; helpsReceived: number; helpsGiven: number; deliveries: number; sent: number };
	/** Gift boxes from friends waiting in the Correio (applied from the inbox exactly once; "Abrir" pays them). */
	mailbox: SocialMail[];
	/** The latest things friends did for the player (the Correio's history), newest first. */
	history: SocialLogEntry[];
	/** Helps given on `day` (UTC): the Amigos page's "Ajudas hoje" meter (the server allows 30 a day). */
	daily: { day: string; helps: number };
};

/** One unopened gift box in the Correio. */
export type SocialMail = { id: string; kind: "gift"; name: string; avatar: string; coins: number; at: number };
/** One line of the Correio's history: the toast's text (Portuguese template) and its numbers, translated when shown. */
export type SocialLogEntry = {
	kind: string;
	text: string;
	icon: string;
	name: string;
	avatar: string;
	coins: number;
	diamonds: number;
	minutes: number;
	productId: number;
	qty: number;
	at: number;
};

/** The small public block sent with every cloud save (`PUT /v1/save` → `public`). */
export type SocialPublicBuild = { id: string; kind: "interior" | "evolution" | "era" | "lot"; item: string; tier: number; endsAt: number };
export type SocialPublicBlock = { builds: SocialPublicBuild[]; stage: string; marketRating: number };

/** What applying one inbox item did (the toast and whether the server may forget it). */
export type SocialInboxOutcome = {
	id: string;
	kind: string;
	/** The item changed the save now. */
	applied: boolean;
	/** Ack it (applied now or before, or nothing to apply). False = keep it for later (daily gift cap). */
	ack: boolean;
	/** Toast text (Portuguese, `{0}` = the friend's name) and the coins / diamonds / minutes it gave. */
	text: string;
	icon: string;
	name: string;
	coins: number;
	diamonds: number;
	minutes: number;
	productId: number;
	qty: number;
};
