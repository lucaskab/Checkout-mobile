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
