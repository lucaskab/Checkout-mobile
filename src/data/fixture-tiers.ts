import type { MarketEraId } from "@/@types/economy";
import type {
	CarrierChoice,
	CartCarrier,
	DecorTierDefinition,
	FixtureKind,
	FixtureTierDefinition,
	SectorTierDefinition,
	SectorTierPrice,
} from "@/@types/fixture-tiers";
import type { ProductionSectorId } from "@/@types/production";
import type { ShelfTypeId } from "@/data/shelf-types";

// "Evoluções dos móveis" (Mari's idea, approved by Lucas 30/10; docs-drafts/evolucoes-moveis.md).
//
// The furniture inside the shop evolves in tiers: a new model, a bigger footprint and more room. For the product
// fixtures the tier IS the capacity upgrade that already existed (shelfUpgradeLevels 0..4 → T1..T4 and the premium
// finish ★): prices, diamonds and levels stay as they were, so the balance does not move and saves need nothing new.
// The small shops have small furniture: each expansion caps the look (and the next purchase), what was already
// bought is never taken away.

const ERA_ORDER: MarketEraId[] = [
	"mesinha",
	"tenda",
	"banca",
	"conteiner",
	"spati",
	"quitanda",
	"minimercado",
	"mercadinho",
	"supermercado",
	"hipermercado",
	"rede",
];
const eraIndex = (eraId: MarketEraId) => Math.max(0, ERA_ORDER.indexOf(eraId));

/** The ★ premium finish of the shelves: the T4 model with gold trims and an LED skirting. */
export const PREMIUM_TIER = 5;

/** Product fixtures by kind of model. The three gondolas (snacks, groceries, home) share the shelf models. */
export const shelfFixtureKinds: Record<ShelfTypeId, FixtureKind> = {
	produce: "produce",
	drinks: "drinks",
	bakery: "bakery",
	dairy: "dairy",
	snacks: "shelf",
	coffee: "shelf",
	home: "shelf",
	pizza: "freezer",
	icecream: "icecream",
};

const t = (tier: number, name: string, width: number, depth: number): FixtureTierDefinition => ({ tier, name, width, depth });

/** Names and footprints (metres) of every tier, from the approved models (ArtSource/fixture_tiers/export/README.md). */
export const fixtureTiers: Record<FixtureKind, FixtureTierDefinition[]> = {
	shelf: [
		t(1, "Estante de madeira", 1, 0.5),
		t(2, "Estante grande de madeira", 1.5, 0.5),
		t(3, "Gôndola de metal", 2, 0.75),
		t(4, "Gôndola iluminada", 2.5, 1),
		t(5, "Gôndola iluminada premium", 2.5, 1),
	],
	produce: [
		t(1, "Banca de caixotes", 1, 0.75),
		t(2, "Banca inclinada de madeira", 1.5, 0.75),
		t(3, "Banca em degraus", 2, 1),
		t(4, "Ilha refrigerada com névoa", 2.5, 1.25),
		t(5, "Ilha refrigerada premium", 2.5, 1.25),
	],
	drinks: [
		t(1, "Geladeira de 1 porta", 0.75, 0.75),
		t(2, "Geladeira de 2 portas", 1.25, 0.75),
		t(3, "Geladeira de 3 portas", 2, 0.75),
		t(4, "Parede de portas com LED", 2.5, 1),
		t(5, "Parede de portas premium", 2.5, 1),
	],
	dairy: [
		t(1, "Expositor refrigerado pequeno", 1, 0.75),
		t(2, "Balcão refrigerado", 1.5, 0.75),
		t(3, "Expositor aberto", 2, 1),
		t(4, "Ilha de laticínios e frios", 2.5, 1),
		t(5, "Ilha de laticínios premium", 2.5, 1),
	],
	bakery: [
		t(1, "Estante de pães", 1, 0.5),
		t(2, "Estante de cestos inclinados", 1.5, 0.5),
		t(3, "Vitrine de acrílico", 2, 0.75),
		t(4, "Vitrine aquecida iluminada", 2, 1),
		t(5, "Vitrine aquecida premium", 2, 1),
	],
	freezer: [
		t(1, "Freezer horizontal pequeno", 1, 0.75),
		t(2, "Freezer horizontal grande", 1.5, 0.75),
		t(3, "Freezer vertical de 2 portas", 1.5, 0.9),
		t(4, "Ilha de congelados", 2.5, 1.25),
		t(5, "Ilha de congelados premium", 2.5, 1.25),
	],
	icecream: [
		t(1, "Freezer de sorvetes", 1, 0.75),
		t(2, "Freezer de sorvetes grande", 1.5, 0.75),
		t(3, "Ilha de sorvetes", 2, 1),
		t(4, "Vitrine de gelato", 2.5, 1),
		t(5, "Vitrine de gelato premium", 2.5, 1),
	],
	checkout: [
		t(1, "Caixinha no balcão", 1.25, 1.25),
		t(2, "Caixa registradora", 1.75, 1.5),
		t(3, "Caixa com esteira", 2.5, 1.75),
		t(4, "Caixa premium", 3, 1.75),
	],
	coldroom: [
		t(1, "Freezer de estoque", 1.25, 0.75),
		t(2, "Mini câmara fria", 2, 2),
		t(3, "Câmara fria", 3, 2.5),
		t(4, "Câmara frigorífica", 5, 4),
	],
	atm: [
		t(1, "Caixa eletrônico", 0.75, 0.85),
		t(2, "Dois caixas na parede", 1.5, 0.85),
		t(3, "Sala de autoatendimento bancário", 2.25, 1.5),
	],
	gumball: [t(1, "Máquina de chiclete", 0.5, 0.5), t(2, "Máquina de chiclete dupla", 1, 0.5)],
	claw: [
		t(1, "Máquina de pelúcia", 0.75, 0.75),
		t(2, "Máquina de pelúcia dupla", 1.5, 0.85),
		t(3, "Pelúcia gigante", 1.5, 1.5),
	],
};

export function getFixtureTierDefinition(kind: FixtureKind, tier: number) {
	const list = fixtureTiers[kind];
	return list.find((item) => item.tier === tier) ?? list[Math.min(list.length, Math.max(1, tier)) - 1];
}

/** Unity template of a tier (Resources/CheckoutFixtureTiers/<kind>_T<n>); the premium finish uses the T4 model. */
export function getFixtureTierTemplate(kind: FixtureKind, tier: number) {
	return `${kind}_T${Math.min(4, Math.max(1, tier))}`;
}

// ------------------------------------------------------------------ product fixtures (shelves, fridges, freezers)

/**
 * The biggest look the shop has room for. The stalls (mesinha → contêiner) still sell from the crates and the
 * cooler of their own model ("T0"); their capacity may still grow up to the T2 numbers, like the Conveniência.
 * Conveniência and Quitanda: up to T2; Minimercado T3; Mercadinho T4; Supermercado on: the premium finish.
 */
export function getEraFixtureTierCap(eraId: MarketEraId) {
	const index = eraIndex(eraId);
	if (index <= eraIndex("quitanda")) return 2;
	if (index === eraIndex("minimercado")) return 3;
	if (index === eraIndex("mercadinho")) return 4;
	return PREMIUM_TIER;
}

/** The first expansion whose shops show `tier` (for "Disponível no Minimercado"). */
export function getFixtureTierEra(tier: number): MarketEraId {
	if (tier <= 2) return "mesinha";
	if (tier === 3) return "minimercado";
	if (tier === 4) return "mercadinho";
	return "supermercado";
}

/** The stalls of the first expansions bring their own crates and cooler: nothing to place or evolve visually. */
export function isStallEra(eraId: MarketEraId) {
	return eraIndex(eraId) < eraIndex("spati");
}

/** Tier the capacity bought stands for (upgrade level 0 → T1 … 4 → ★). */
export function getCapacityTier(upgradeLevel = 0) {
	return Math.min(PREMIUM_TIER, Math.max(0, Math.floor(upgradeLevel)) + 1);
}

/** The tier a product fixture shows: what was bought, as big as this shop allows. */
export function getShelfFixtureTier(upgradeLevel: number | undefined, eraId: MarketEraId) {
	return Math.min(getCapacityTier(upgradeLevel ?? 0), getEraFixtureTierCap(eraId));
}

/** Can the next capacity step be bought in this shop? (It must fit the shop's furniture size.) */
export function canBuyCapacityTier(upgradeLevel: number | undefined, eraId: MarketEraId) {
	return getCapacityTier((upgradeLevel ?? 0) + 1) <= getEraFixtureTierCap(eraId);
}

/** Product places a fixture of this tier has room for: T1 up to 5, T2 up to 6, T3 on up to 7. */
export function getTierSlotLimit(tier: number) {
	if (tier <= 1) return 5;
	if (tier === 2) return 6;
	return 7;
}

// ------------------------------------------------------------------ the checkout counter

/** Steps of the checkout: shop items bought in order (the conveyor and the scanner are the T3 of today). */
export const CHECKOUT_REGISTER_ITEM = "checkout-register";
export const CHECKOUT_CONVEYOR_ITEM = "smart-conveyor";
export const CHECKOUT_SCANNER_ITEM = "auto-scanner";
export const CHECKOUT_PREMIUM_ITEM = "checkout-premium";
export const checkoutTierItemIds = [
	CHECKOUT_REGISTER_ITEM,
	CHECKOUT_CONVEYOR_ITEM,
	CHECKOUT_SCANNER_ITEM,
	CHECKOUT_PREMIUM_ITEM,
] as const;

/** From the minimercado on the player places the checkout: the first one already is the register (T2). */
export const CHECKOUT_REGISTER_GIFT_ERA: MarketEraId = "minimercado";

/** Checkout tier bought (or given): 1 small till, 2 register, 3 conveyor (+ scanner), 4 premium. */
export function getCheckoutTier(ownedItemIds: readonly string[], eraId: MarketEraId) {
	let tier = 1;
	if (ownedItemIds.includes(CHECKOUT_REGISTER_ITEM)) tier = 2;
	if (ownedItemIds.includes(CHECKOUT_CONVEYOR_ITEM) || ownedItemIds.includes(CHECKOUT_SCANNER_ITEM)) tier = 3;
	if (ownedItemIds.includes(CHECKOUT_PREMIUM_ITEM)) tier = 4;
	if (eraIndex(eraId) >= eraIndex(CHECKOUT_REGISTER_GIFT_ERA)) tier = Math.max(tier, 2);
	return tier;
}

/** The checkout look this shop has room for: the small shops' fixed counter shows up to the register. */
export function getCheckoutVisualTier(ownedItemIds: readonly string[], eraId: MarketEraId) {
	const index = eraIndex(eraId);
	const cap = index < eraIndex("minimercado") ? 2 : index < eraIndex("supermercado") ? 3 : 4;
	return Math.min(cap, getCheckoutTier(ownedItemIds, eraId));
}

/** Who should own the register step without paying: the shops from the minimercado on, and who already has the
 * conveyor or the scanner (bought before the steps existed). Idempotent (src/stores/game-store.ts normalize). */
export function withCheckoutRegister(ownedItemIds: readonly string[], eraId: MarketEraId): string[] {
	if (ownedItemIds.includes(CHECKOUT_REGISTER_ITEM)) return [...ownedItemIds];
	const gift =
		eraIndex(eraId) >= eraIndex(CHECKOUT_REGISTER_GIFT_ERA) ||
		ownedItemIds.includes(CHECKOUT_CONVEYOR_ITEM) ||
		ownedItemIds.includes(CHECKOUT_SCANNER_ITEM) ||
		ownedItemIds.includes(CHECKOUT_PREMIUM_ITEM);
	return gift ? [...ownedItemIds, CHECKOUT_REGISTER_ITEM] : [...ownedItemIds];
}

// ------------------------------------------------------------------ the cold room (câmara fria)

/** Products kept in the cold room: dairy, cheese, cold cuts, meat, fish, frozen food and ice cream. Drinks stay in
 * the depot (they only get cold in the shop's fridge). */
export const CHILLED_CATEGORIES = ["laticinios", "queijos", "frios", "carnes", "peixes", "congelados", "sorvetes"];

export function isChilledCategory(category: string | undefined) {
	return !!category && CHILLED_CATEGORIES.includes(category);
}

/** Shop items of the cold room's tiers (T1, the stock freezer, comes free with every save). The T4 is the old
 * "Câmara Fria" item: who had it is at T4 right away. */
export const coldRoomTierItemIds: Record<number, string> = {
	2: "cold-room-2",
	3: "cold-room-3",
	4: "cold-storage",
};

export function getColdRoomTier(ownedItemIds: readonly string[]) {
	for (const tier of [4, 3, 2]) if (ownedItemIds.includes(coldRoomTierItemIds[tier])) return tier;
	return 1;
}

/**
 * The stockroom upgrade (src/data/inventory-capacity.ts) a chilled product may reach with this cold room: T1 up to
 * upgrade 1 (3 boxes), T2 up to 2 (5), T3 up to 3 (8), T4 up to 4 (12). Levels bought before stay as they are.
 */
export function getColdRoomUpgradeCap(coldRoomTier: number) {
	return Math.min(4, Math.max(1, coldRoomTier));
}

// ------------------------------------------------------------------ decorations that evolve (ATM, gumball, claw)

const dt = (
	tier: number,
	name: string,
	width: number,
	depth: number,
	extra: Omit<DecorTierDefinition, "tier" | "name" | "width" | "depth">,
): DecorTierDefinition => ({ tier, name, width, depth, ...extra });

/** Decoration id → its tiers (tier 1 is the decoration as bought; the next ones are upgrades of every piece). */
export const decorTiers: Record<string, DecorTierDefinition[]> = {
	atm: [
		dt(1, "Caixa eletrônico", 0.75, 0.85, { requiredLevel: 19, budget: 0.15 }),
		dt(2, "Dois caixas na parede", 1.5, 0.85, { requiredLevel: 25, coinPrice: 45_000, budget: 0.2 }),
		dt(3, "Sala de autoatendimento bancário", 2.25, 1.5, { requiredLevel: 33, coinPrice: 120_000, budget: 0.25 }),
	],
	gumball: [
		dt(1, "Máquina de chiclete", 0.5, 0.5, { requiredLevel: 13, playCoins: 1 }),
		dt(2, "Máquina de chiclete dupla", 1, 0.5, { requiredLevel: 18, coinPrice: 6_600, playCoins: 1.5 }),
	],
	"claw-machine": [
		dt(1, "Máquina de pelúcia", 0.75, 0.75, { requiredLevel: 23, playCoins: 1 }),
		dt(2, "Máquina de pelúcia dupla", 1.5, 0.85, { requiredLevel: 28, diamondPrice: 30, playCoins: 1.5 }),
		dt(3, "Pelúcia gigante", 1.5, 1.5, { requiredLevel: 34, diamondPrice: 60, playCoins: 2 }),
	],
};

/** Unity model kind of an evolving decoration. */
export const decorTierKinds: Record<string, FixtureKind> = { atm: "atm", gumball: "gumball", "claw-machine": "claw" };

export function getDecorTier(tiers: Record<string, number> | undefined, decorId: string) {
	const list = decorTiers[decorId];
	if (!list) return 1;
	return Math.min(list.length, Math.max(1, Math.floor(tiers?.[decorId] ?? 1)));
}

export function getNextDecorTier(tiers: Record<string, number> | undefined, decorId: string) {
	const list = decorTiers[decorId];
	if (!list) return null;
	return list[getDecorTier(tiers, decorId)] ?? null;
}

export function normalizeDecorTiers(value: unknown): Record<string, number> {
	const result: Record<string, number> = {};
	if (!value || typeof value !== "object") return result;
	for (const [id, tier] of Object.entries(value as Record<string, unknown>)) {
		const list = decorTiers[id];
		if (!list || typeof tier !== "number" || !Number.isFinite(tier)) continue;
		const clamped = Math.min(list.length, Math.max(1, Math.floor(tier)));
		if (clamped > 1) result[id] = clamped;
	}
	return result;
}

// ------------------------------------------------------------------ baskets and carts (three stations, not tiers)

/** Extra products each carrier holds over what fits in the hands (the archetype's base). */
export const carrierCapacity: Record<CartCarrier, number> = { hands: 0, basket: 1, cart: 2, bigCart: 4 };

/** Station decoration id → the carrier customers take from it. */
export const cartStations: Record<string, Exclude<CartCarrier, "hands">> = {
	"basket-station": "basket",
	"cart-corral": "cart",
	"big-cart-corral": "bigCart",
};

/**
 * Extra products (0..+4) a customer plans on top of the archetype's base, weights for 0, 1, 2, 3, 4. Families buy
 * for the month; thrifty and impulse buyers grab a little; the rest are in the middle.
 */
export const carrierPlanWeights: Record<string, readonly number[]> = {
	economico: [0.4, 0.35, 0.15, 0.07, 0.03],
	impulsivo: [0.35, 0.35, 0.18, 0.08, 0.04],
	normal: [0.2, 0.3, 0.25, 0.15, 0.1],
	premium: [0.2, 0.3, 0.25, 0.15, 0.1],
	familia: [0.05, 0.15, 0.25, 0.3, 0.25],
};

/** Draws the extra products a customer of this archetype plans (0..4). */
export function drawCarrierPlan(archetype: string, roll: number) {
	const weights = carrierPlanWeights[archetype] ?? carrierPlanWeights.normal;
	let acc = 0;
	for (let extra = 0; extra < weights.length; extra++) {
		acc += weights[extra];
		if (roll < acc) return extra;
	}
	return weights.length - 1;
}

const carrierOrder: CartCarrier[] = ["hands", "basket", "cart", "bigCart"];

/**
 * The smallest carrier that holds the plan; when the market has none that big, the largest it has (and the
 * customer buys only what fits).
 */
export function chooseCarrier(planExtra: number, available: readonly CartCarrier[]): CarrierChoice {
	const owned = carrierOrder.filter((carrier) => carrier === "hands" || available.includes(carrier));
	const fit = owned.find((carrier) => carrierCapacity[carrier] >= planExtra);
	const carrier = fit ?? owned[owned.length - 1];
	const extra = Math.min(planExtra, carrierCapacity[carrier]);
	return { carrier, extra, missing: Math.max(0, planExtra - extra) };
}

// ------------------------------------------------------------------ the special sectors (açougue, padaria…)
// Approved by Lucas 30/10 (docs-drafts/evolucoes-moveis.md, "Setores especiais"). Every sector built so far is T1 (a
// smaller model than the old counter, so it always fits where it stands); T2 adds a production slot, T3 cuts the
// production time by 20% and sells the sector's goods 10% dearer. Production queues and stock are never touched.

export const SECTOR_MAX_TIER = 3;

export const sectorTiers: SectorTierDefinition[] = [
	{ tier: 1, name: "Compacto", width: 2.5, depth: 2, extraSlots: 0, durationMultiplier: 1, priceMultiplier: 1 },
	{ tier: 2, name: "Completo", width: 3.25, depth: 2.5, extraSlots: 1, durationMultiplier: 1, priceMultiplier: 1 },
	{ tier: 3, name: "Premium", width: 4, depth: 3.25, extraSlots: 1, durationMultiplier: 0.8, priceMultiplier: 1.1 },
];

/** Price of T2 / T3 by shop size (~2 h of sales where it opens); the diamond price is the same everywhere. */
export function getSectorTierPrice(tier: number, eraId: MarketEraId): SectorTierPrice | null {
	if (tier < 2 || tier > SECTOR_MAX_TIER) return null;
	const big = eraIndex(eraId) >= eraIndex("hipermercado");
	const mid = eraIndex(eraId) >= eraIndex("supermercado");
	const coins = tier === 2 ? (big ? 70_000 : mid ? 30_000 : 18_000) : big ? 200_000 : mid ? 90_000 : 55_000;
	return { coins, diamonds: tier === 2 ? 30 : 80 };
}

export function getSectorTier(tiers: Partial<Record<string, number>> | undefined, sectorId: string) {
	return Math.min(SECTOR_MAX_TIER, Math.max(1, Math.floor(tiers?.[sectorId] ?? 1)));
}

export function getSectorTierDefinition(tier: number) {
	return sectorTiers[Math.min(SECTOR_MAX_TIER, Math.max(1, Math.floor(tier))) - 1];
}

/** The sector's production slots at its tier. */
export function getSectorSlotCount(baseSlots: number, tiers: Partial<Record<string, number>> | undefined, sectorId: string) {
	return baseSlots + getSectorTierDefinition(getSectorTier(tiers, sectorId)).extraSlots;
}

/** Unity model of a sector at its tier (Resources/CheckoutFixtureTiers/sector-<id>_T<n>). */
export function getSectorTierTemplate(sectorId: string, tier: number) {
	return `sector-${sectorId}_T${Math.min(SECTOR_MAX_TIER, Math.max(1, Math.floor(tier)))}`;
}

/** Saved sector tiers: only the known sectors, only steps above T1. */
export function normalizeSectorTiers(value: unknown, knownIds: readonly ProductionSectorId[]): Partial<Record<ProductionSectorId, number>> {
	const result: Partial<Record<ProductionSectorId, number>> = {};
	if (!value || typeof value !== "object") return result;
	for (const [id, tier] of Object.entries(value as Record<string, unknown>)) {
		if (!knownIds.includes(id as ProductionSectorId) || typeof tier !== "number" || !Number.isFinite(tier)) continue;
		const clamped = Math.min(SECTOR_MAX_TIER, Math.max(1, Math.floor(tier)));
		if (clamped > 1) result[id as ProductionSectorId] = clamped;
	}
	return result;
}
