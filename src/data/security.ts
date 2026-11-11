import type { MarketEraId } from "@/@types/economy";
import type { StoreSecurityOutcomeKind } from "@/@types/security";

// "Ladrão e segurança" numbers (rules: src/services/store-security.ts). All times in ms on the game clock.

/** Thieves start with the quitanda (the first stage with a door to run out of). */
export const THIEF_FIRST_ERA: MarketEraId = "quitanda";
/** The first thief of a turn comes 100–160 s after opening… */
export const FIRST_THIEF_DELAY_MS = { min: 100_000, max: 160_000 };
/** …then one every 150–260 s (never two at once). */
export const THIEF_INTERVAL_MS = { min: 150_000, max: 260_000 };
/** A security guard on duty scares half of them away: the wait between thieves is ×1.6. */
export const GUARD_INTERVAL_MULTIPLIER = 1.6;
/** He walks in and browses for 7 s, then grabs the goods. */
export const THIEF_GRAB_DELAY_MS = 7_000;
/** Once he has the goods the player has 11 s to tap him before he is out of the door. */
export const THIEF_FLEE_MS = 11_000;
/** The store dog barks at the grab: 3 s more to catch him. */
export const DOG_BARK_EXTRA_MS = 3_000;
/** A guard on duty stops him 3.5 s after the grab (faster with more efficiency). */
export const GUARD_CATCH_MS = 3_500;
/** Units he grabs: 1–3 (never more than the shelf has). Old saves only: thieves now go for the till. */
export const THIEF_UNITS = { min: 1, max: 3 };
/** He robs the till (Lucas 08/11: "o caixa, pq lá que fica o dinheiro"): a share of the day's takings, between the
 * bounds, never more than the player has. Less than the minimum in the till: no thief comes in. */
export const THIEF_TILL_SHARE = 0.15;
export const THIEF_TILL_CASH = { min: 20, max: 2_000 };
/** The till, as the thief's target (the main checkout piece in Unity). */
export const THIEF_TILL_ID = "checkout:main";
export const THIEF_TILL_NAME = "Dinheiro do caixa";
/** Caught: he stays on screen a moment (handcuffs, the goods back on the shelf) before leaving. */
export const CAUGHT_REMOVE_MS = 4_000;
/** Escaped: he is gone after a short moment. */
export const ESCAPED_REMOVE_MS = 2_500;
/** Catching him pays half the stolen value (at least 10 moedas); the guard's catch pays half of that. */
export const CATCH_REWARD_SHARE = 0.5;
export const CATCH_REWARD_MIN = 10;
export const GUARD_REWARD_SHARE = 0.5;
export const CATCH_EXPERIENCE = 8;
/** Reputation (satisfaction) for a thief stopped, like a mishap fixed. */
export const CATCH_REPUTATION = 1;
/** The HUD toast of the last outcome is shown for this long. */
export const SECURITY_OUTCOME_MS = 6_000;
/** A gap this long between ticks means the game was closed: an active thief leaves and the goods go back. */
export const SECURITY_STALE_TICK_MS = 15_000;

/** Tapping him before he took anything. */
export const THIEF_NOT_YET_MESSAGE = "Ele ainda não fez nada";
export const THIEF_GONE_MESSAGE = "Ele já foi embora";

export const securityOutcomeMessages: Record<StoreSecurityOutcomeKind, string> = {
	caught: "Ladrão pego! O dinheiro voltou para o caixa.",
	guard: "O segurança pegou o ladrão!",
	escaped: "O ladrão fugiu com o dinheiro do caixa.",
};
