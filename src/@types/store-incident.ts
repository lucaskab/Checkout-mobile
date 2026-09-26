// Mishaps that pop up in the store while it is open. Each one hurts the business until someone
// fixes it: the player (System: one tap; Simulator: a small task in Unity) or the right employee.
// The two coolers (ice cream chest freezer, upright drinks fridge) short-circuit: in the simulator the
// player rewires them (a small puzzle); in System mode it is one tap. Old saves used "freezer".
export type StoreIncidentKind =
	| "derramado"
	| "freezer_sorvete"
	| "geladeira_bebidas"
	| "etiqueta"
	| "lampada";

export type StoreIncident = {
	createdAt: number;
	// Coins needed to fix it (the coolers need parts); 0 for the others.
	fixCost: number;
	id: string;
	kind: StoreIncidentKind;
	productId: number;
	productName: string;
	// Price the wrong tag shows (etiqueta only).
	tagPrice: number;
	// Physical shelf the incident is at.
	shelfId: string;
	shelfName: string;
};

export type StoreIncidentOutcome = {
	fixedAt: number;
	id: string;
	kind: StoreIncidentKind;
	// "player" fixed it by hand; "staff" an employee did.
	by: "player" | "staff";
};

export type StoreIncidentsState = {
	active: StoreIncident[];
	fixed: number;
	nextAt: number | null;
	nextStaffFixAt: number | null;
	recent: StoreIncidentOutcome[];
	seed: number;
	// Cooler spoilage clock.
	spoilAt: number | null;
};

export type StoreIncidentEffects = {
	// Shelves customers cannot buy from (broken cooler).
	blockedShelfIds: string[];
	// Price the customer pays / price set, per shelf with a wrong tag.
	priceMultipliers: Record<string, number>;
	// Taken from the store reputation used by customers, and from each visit's satisfaction.
	reputationPenalty: number;
};

export type StoreIncidentShelf = {
	category: string;
	price: number;
	productId: number;
	productName: string;
	shelfId: string;
	shelfName: string;
	stock: number;
};
