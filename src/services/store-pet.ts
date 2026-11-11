import type { GameState } from "@/@types/game";
import type { PetCatalogEntry, PetCosmeticDefinition, PetSnapshot, PetState } from "@/@types/pet";
import { getMarketEra } from "@/data/economy";
import {
	DEFAULT_PET_BED_STYLE,
	DEFAULT_PET_COLLAR,
	getPetCosmetic,
	PET_COOLDOWN_MS,
	PET_FIRST_ERA,
	PET_HAPPY_ARRIVAL_MULTIPLIER,
	PET_HAPPY_MS,
	petCosmetics,
} from "@/data/pet";

// "Mascote caramelo" (types: src/@types/pet.ts, catalogue: src/data/pet.ts). Pure rules; the store actions adoptPet,
// petDog, buyPetCosmetic and equipPetCosmetic call them.

export function createPetState(): PetState {
	return {
		adopted: false,
		adoptedAt: 0,
		lastPetAt: 0,
		happyUntil: 0,
		petsToday: 0,
		petsDay: 0,
		owned: [],
		collar: "",
		bandana: "",
		hasBed: false,
		hasBowls: false,
		bedStyle: "",
	};
}

const num = (value: unknown) => (typeof value === "number" && Number.isFinite(value) ? value : 0);

/** Saves from before the dog (no field) start without one; unknown cosmetics are dropped. */
export function normalizePetState(value: unknown): PetState {
	const initial = createPetState();
	if (!value || typeof value !== "object") return initial;
	const pet = value as Partial<PetState>;
	const adopted = pet.adopted === true;
	const owned = Array.from(
		new Set([
			...(Array.isArray(pet.owned) ? pet.owned.filter((id): id is string => typeof id === "string" && !!getPetCosmetic(id)) : []),
			...(adopted ? [DEFAULT_PET_COLLAR, DEFAULT_PET_BED_STYLE] : []),
		]),
	);
	const wears = (id: unknown, kind: "collar" | "bandana" | "bedStyle") =>
		typeof id === "string" && owned.includes(id) && getPetCosmetic(id)?.kind === kind ? id : "";
	return {
		adopted,
		adoptedAt: num(pet.adoptedAt),
		lastPetAt: num(pet.lastPetAt),
		happyUntil: num(pet.happyUntil),
		petsToday: num(pet.petsToday),
		petsDay: num(pet.petsDay),
		owned,
		collar: wears(pet.collar, "collar") || (adopted ? DEFAULT_PET_COLLAR : ""),
		bandana: wears(pet.bandana, "bandana"),
		hasBed: pet.hasBed === true || owned.includes("pet_bed"),
		hasBowls: pet.hasBowls === true || owned.includes("pet_bowls"),
		bedStyle: wears(pet.bedStyle, "bedStyle") || (adopted ? DEFAULT_PET_BED_STYLE : ""),
	};
}

/** The stray dog waits at the door from the Späti on, until adopted. */
export function isPetEraReached(eraId: GameState["era"]["id"]) {
	return getMarketEra(eraId).index >= getMarketEra(PET_FIRST_ERA).index;
}

export function isPetOfferOpen(pet: PetState, eraId: GameState["era"]["id"]) {
	return !pet.adopted && isPetEraReached(eraId);
}

/** Free: the dog joins the market wearing the navy collar. */
export function adoptPetRule(pet: PetState, eraId: GameState["era"]["id"], now: number): PetState | null {
	if (!isPetOfferOpen(pet, eraId)) return null;
	return {
		...pet,
		adopted: true,
		adoptedAt: now,
		owned: Array.from(new Set([...pet.owned, DEFAULT_PET_COLLAR, DEFAULT_PET_BED_STYLE])),
		collar: pet.collar || DEFAULT_PET_COLLAR,
		bedStyle: pet.bedStyle || DEFAULT_PET_BED_STYLE,
	};
}

export type PetDogResult = { ok: true; pet: PetState } | { ok: false; reason: "not-adopted" | "cooldown"; secondsLeft: number };

/** Petting: a happy dog for a minute, then a 2-minute break before he wants it again. */
export function petDogRule(pet: PetState, now: number, dayNumber: number): PetDogResult {
	if (!pet.adopted) return { ok: false, reason: "not-adopted", secondsLeft: 0 };
	const cooldown = getPetCooldownLeftMs(pet, now);
	if (cooldown > 0) return { ok: false, reason: "cooldown", secondsLeft: Math.ceil(cooldown / 1000) };
	return {
		ok: true,
		pet: {
			...pet,
			lastPetAt: now,
			happyUntil: now + PET_HAPPY_MS,
			petsToday: pet.petsDay === dayNumber ? pet.petsToday + 1 : 1,
			petsDay: dayNumber,
		},
	};
}

export function getPetCooldownLeftMs(pet: PetState, now: number) {
	if (!pet.adopted || pet.lastPetAt <= 0) return 0;
	return Math.max(0, pet.lastPetAt + PET_COOLDOWN_MS - now);
}

export function getPetHappyLeftMs(pet: PetState, now: number) {
	return pet.adopted ? Math.max(0, pet.happyUntil - now) : 0;
}

/** A happy dog at the door brings a few more customers (×1.05). */
export function getPetArrivalMultiplier(pet: PetState | undefined, now: number) {
	return pet?.adopted && now < pet.happyUntil ? PET_HAPPY_ARRIVAL_MULTIPLIER : 1;
}

export type PetPurchaseCheck =
	| { ok: true; item: PetCosmeticDefinition }
	| { ok: false; reason: "not-adopted" | "unknown" | "owned" | "locked" };

/** Can this cosmetic be bought now? (The price itself is checked by the store, which holds the wallet.) */
export function checkPetPurchase(pet: PetState, id: string, level: number): PetPurchaseCheck {
	const item = getPetCosmetic(id);
	if (!item || item.hidden) return { ok: false, reason: "unknown" };
	if (!pet.adopted) return { ok: false, reason: "not-adopted" };
	if (pet.owned.includes(id)) return { ok: false, reason: "owned" };
	if (level < item.requiredLevel) return { ok: false, reason: "locked" };
	return { ok: true, item };
}

/** A cosmetic bought: owned from now on; collars, bandanas and bed fabrics are put on right away, the bowls placed. */
export function withPetCosmetic(pet: PetState, item: PetCosmeticDefinition): PetState {
	const owned = Array.from(new Set([...pet.owned, item.id]));
	return {
		...pet,
		owned,
		collar: item.kind === "collar" ? item.id : pet.collar,
		bandana: item.kind === "bandana" ? item.id : pet.bandana,
		bedStyle: item.kind === "bedStyle" ? item.id : pet.bedStyle,
		hasBed: pet.hasBed || item.kind === "bed",
		hasBowls: pet.hasBowls || item.kind === "bowls",
	};
}

/** Wears an owned collar or bandana; "" takes the bandana off (a collar always stays on). */
export function equipPetCosmeticRule(pet: PetState, id: string): PetState | null {
	if (!pet.adopted) return null;
	if (id === "") return pet.bandana ? { ...pet, bandana: "" } : null;
	const item = getPetCosmetic(id);
	if (!item || !pet.owned.includes(id)) return null;
	if (item.kind === "collar") return pet.collar === id ? null : { ...pet, collar: id };
	if (item.kind === "bandana") return pet.bandana === id ? null : { ...pet, bandana: id };
	if (item.kind === "bedStyle") return pet.bedStyle === id ? null : { ...pet, bedStyle: id };
	return null;
}

export function getPetCatalog(pet: PetState, level: number): PetCatalogEntry[] {
	return petCosmetics.filter((item) => !item.hidden || pet.owned.includes(item.id)).map((item) => ({
		id: item.id,
		kind: item.kind,
		name: item.name,
		price: item.price,
		currency: item.currency,
		owned: pet.owned.includes(item.id),
		equipped:
			(item.kind === "collar" && pet.collar === item.id) ||
			(item.kind === "bandana" && pet.bandana === item.id) ||
			(item.kind === "bedStyle" && pet.bedStyle === item.id) ||
			(item.kind === "bed" && pet.hasBed) ||
			(item.kind === "bowls" && pet.hasBowls),
		locked: level < item.requiredLevel,
		requiredLevel: item.requiredLevel,
	}));
}

export function createPetSnapshot(state: Pick<GameState, "pet" | "era" | "market">, now: number): PetSnapshot {
	const pet = normalizePetState(state.pet);
	return {
		adopted: pet.adopted,
		offer: isPetOfferOpen(pet, state.era.id),
		happyLeftMs: getPetHappyLeftMs(pet, now),
		cooldownLeftMs: getPetCooldownLeftMs(pet, now),
		collar: pet.collar,
		bandana: pet.bandana,
		hasBed: pet.hasBed,
		hasBowls: pet.hasBowls,
		bedStyle: pet.bedStyle && pet.bedStyle !== DEFAULT_PET_BED_STYLE ? pet.bedStyle.replace("bedstyle_", "") : "",
		owned: pet.owned,
		catalog: getPetCatalog(pet, state.market.level),
	};
}
