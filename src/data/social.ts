import type { MarketEraId } from "@/@types/economy";
import { getMarketEra } from "@/data/economy";

// Social v1 numbers (docs/social-api.md). The server enforces the daily limits; these are the game's side: what each
// thing pays and how much the save remembers. Tune here.

/** Inbox ids remembered as applied (exactly-once across a crash between apply and ack). */
export const SOCIAL_APPLIED_KEEP = 300;
/** Gifts the player opens per UTC day; the rest stay unacked on the server until the next day. */
export const SOCIAL_GIFTS_PER_DAY = 25;
/** Minutes one friend's help takes off a running build. */
export const SOCIAL_HELP_MINUTES = 5;
/** Units a product request asks for, at least / at most. */
export const SOCIAL_REQUEST_MIN = 1;
export const SOCIAL_REQUEST_MAX = 20;
/** Open product requests per player. */
export const SOCIAL_REQUESTS_OPEN = 2;
/** Diamonds an invite reward may carry at most (the contract says 30; a bad payload never pays more). */
export const SOCIAL_INVITE_DIAMONDS_MAX = 100;
/** Rewarded invites that give an exclusive decoration, and its id. */
export const SOCIAL_INVITE_MILESTONES = [1, 3, 5] as const;
export const inviteRewardDecorId = (milestone: number) => `invite-reward-${milestone}`;
/** Builds listed in the public block (the server takes at most 12). */
export const SOCIAL_PUBLIC_BUILDS = 12;
/** Avatars: the game's own shoppers (rendered portraits in Unity), "shopper-1" … "shopper-12". */
export const SOCIAL_AVATARS = Array.from({ length: 12 }, (_, index) => `shopper-${index + 1}`);
export const SOCIAL_DEFAULT_AVATAR = "shopper-1";
/** Market names: 3–20 characters, letters of any script, digits, space and ' - & . (the server filters words). */
export const SOCIAL_NAME_MIN = 3;
export const SOCIAL_NAME_MAX = 20;
export const isAllowedMarketName = (name: string) => {
	const trimmed = name.trim();
	return trimmed.length >= SOCIAL_NAME_MIN && trimmed.length <= SOCIAL_NAME_MAX && /^[\p{L}\p{N} '&.\-]+$/u.test(trimmed);
};

const round5 = (value: number) => Math.round(value / 5) * 5;
/** Scale of every social reward: the price of an item upgrade in the player's stage (the stage follows the level). */
const scale = (eraId: MarketEraId) => getMarketEra(eraId).itemUpgradeBaseCost;

/**
 * What the social actions pay, in coins (a modest economy). Scaled to the stage: a friend's gift is 30 % of the price
 * of one product upgrade there, a like / a help / a thank-you 10 % (mesinha: gift 10, like 5; Späti: 90 / 30;
 * supermercado: 390 / 130). The receiver opens at most 25 gifts a day.
 */
export function getSocialRewards(eraId: MarketEraId) {
	const base = scale(eraId);
	return {
		/** A friend's gift box. */
		gift: Math.max(10, round5(base * 0.3)),
		/** A like, for the owner (inbox) and for the one who liked (at once). */
		like: Math.max(5, round5(base * 0.1)),
		/** The helper, once the server counted the help. */
		help: Math.max(5, round5(base * 0.1)),
		/** A help that arrived after the build had finished: a small thank-you instead of the minutes. */
		thanks: Math.max(5, round5(base * 0.1)),
	};
}

/** The friend who sends a requested product gets its supplier price back plus 25 % (helping never costs money). */
export const getDeliveryReward = (purchasePrice: number, qty: number) => Math.max(1, Math.round(purchasePrice * qty * 1.25));
