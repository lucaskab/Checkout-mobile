// "Mascote caramelo": a stray caramel dog shows up at the market's door (from the Späti on) and can be adopted for
// free. Petting him makes him happy for a minute (a few more customers come in); collars, bandanas, a bed and
// bowls dress him up. Rules: src/services/store-pet.ts, catalogue: src/data/pet.ts.

/** bed: the old single bed (no longer sold: beds are build-mode decorations, src/data/interior-decor.ts pet-bed-*);
 * bedStyle: the fabric of every bed (Unity swaps the bed's painted texture). */
export type PetCosmeticKind = "collar" | "bandana" | "bed" | "bowls" | "bedStyle";

export type PetCurrency = "coins" | "diamonds";

export type PetCosmeticDefinition = {
	id: string;
	kind: PetCosmeticKind;
	/** Portuguese; translated on the way out. */
	name: string;
	description: string;
	/** 0 = free (the starter collar). */
	price: number;
	currency: PetCurrency;
	requiredLevel: number;
	/** Not sold any more (kept so old saves keep what they bought). */
	hidden?: boolean;
};

export type PetState = {
	adopted: boolean;
	adoptedAt: number;
	/** Last petting (0 = never). */
	lastPetAt: number;
	/** The dog is happy (customer bonus) until this time. */
	happyUntil: number;
	petsToday: number;
	/** The day petsToday belongs to (day.dayNumber). */
	petsDay: number;
	/** Cosmetic ids bought (the starter collar is owned on adoption). */
	owned: string[];
	/** Equipped collar id. */
	collar: string;
	/** Equipped bandana id ("" = none). */
	bandana: string;
	hasBed: boolean;
	hasBowls: boolean;
	/** The fabric of his beds (a bedStyle cosmetic id). */
	bedStyle: string;
};

export type PetCatalogEntry = {
	id: string;
	kind: PetCosmeticKind;
	name: string;
	price: number;
	currency: PetCurrency;
	owned: boolean;
	equipped: boolean;
	locked: boolean;
	requiredLevel: number;
};

/** What Unity gets in every snapshot (pet). Flat and JsonUtility-friendly. */
export type PetSnapshot = {
	adopted: boolean;
	/** The dog waits at the door with the "Adotar?" card (Späti on, not adopted yet). */
	offer: boolean;
	happyLeftMs: number;
	cooldownLeftMs: number;
	collar: string;
	bandana: string;
	hasBed: boolean;
	hasBowls: boolean;
	/** Fabric of the beds: "" (navy, the default) | "teal" | "orange" | "rose" (Unity: IK_D4_<Bed>_albedo_<style>). */
	bedStyle: string;
	owned: string[];
	catalog: PetCatalogEntry[];
};
