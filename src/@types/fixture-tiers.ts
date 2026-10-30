import type { MarketEraId } from "./economy";

/**
 * Furniture that evolves in tiers ("Evoluções dos móveis", docs-drafts/evolucoes-moveis.md). Each kind has its own
 * models in Unity (Resources/CheckoutFixtureTiers/<kind>_T<n>): a bigger footprint and more room on every step.
 */
export type FixtureKind =
	| "shelf"
	| "produce"
	| "drinks"
	| "dairy"
	| "bakery"
	| "freezer"
	| "icecream"
	| "checkout"
	| "coldroom"
	| "atm"
	| "gumball"
	| "claw";

/** One visual step of a piece of furniture. */
export type FixtureTierDefinition = {
	/** 1..4 (the shelves' premium finish ★ is tier 5, drawn with the T4 model). */
	tier: number;
	/** Name in pt-BR (translated on the way out like every text). */
	name: string;
	/** Build footprint in metres (whole quarter squares): width along the customer side × depth. */
	width: number;
	depth: number;
};

/** A placed decoration that evolves (ATM, gumball machine, claw machine): every piece of that kind at once. */
export type DecorTierDefinition = FixtureTierDefinition & {
	/** Price of this step (tier 1 is the decoration's own price). */
	coinPrice?: number;
	diamondPrice?: number;
	requiredLevel: number;
	/** ATM: customers bring this share more money (replaces the decoration's own `budget`). */
	budget?: number;
	/** Coin machines: coins per play × this. */
	playCoins?: number;
};

/** What a customer carries while shopping. */
export type CartCarrier = "hands" | "basket" | "cart" | "bigCart";

/** The carrier a customer took and how many extra products their plan wanted but did not fit. */
export type CarrierChoice = {
	carrier: CartCarrier;
	/** Extra products (over the archetype's base) the carrier lets them take. */
	extra: number;
	/** Extra products they wanted and left behind (no carrier big enough in the market). */
	missing: number;
};

/** Per-expansion cap of a fixture's look: the small shops have small furniture. */
export type FixtureEraCap = { eraId: MarketEraId; maxTier: number };
