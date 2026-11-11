// "Ladrão e segurança": now and then a thief walks into the market (from the quitanda on), hangs around for a
// few seconds, grabs the cash from the till and runs for the door (until Nov 2026 he stole goods from a shelf; old
// saves can still hold one of those). The player taps him to catch him (the money goes back and pays a small
// reward); a hired security guard catches him alone, and the store dog barks and slows him down. Rules: src/services/store-security.ts, numbers: src/data/security.ts.

/**
 * entering: walking in and browsing (nothing taken yet, tapping him does nothing);
 * fleeing: has the goods and runs for the door until fleeDeadline;
 * caught: stopped (by the player or the guard), the goods went back; leaves the scene at removeAt;
 * escaped: got away with the goods; leaves the scene at removeAt.
 */
export type StoreThiefPhase = "entering" | "fleeing" | "caught" | "escaped";

export type StoreThiefCatcher = "" | "player" | "guard";

export type StoreThief = {
	id: string;
	phase: StoreThiefPhase;
	/** Game clock (ms, Date.now()) when he appeared at the door. */
	spawnedAt: number;
	/** When he grabs the goods (spawnedAt + THIEF_GRAB_DELAY_MS). */
	grabAt: number;
	/** He is out of the door at this time (0 until he grabs). */
	fleeDeadline: number;
	/** The security guard stops him at this time (0 = no guard on duty when he grabbed). */
	guardCatchAt: number;
	/** He leaves the scene at this time (0 while active). */
	removeAt: number;
	/** What he is after: 0 / "Dinheiro do caixa" for the till; a product for an old shelf thief. */
	productId: number;
	productName: string;
	/** "till" for the cash; an old shelf thief: the shelf slot the units came from (and go back to). */
	slotId: string;
	/** Where he goes: THIEF_TILL_ID (the main checkout) or an old thief's fixture. */
	shelfId: string;
	/** Units taken (old shelf thieves; 0 for the till). */
	quantity: number;
	/** The cash taken from the till (old shelf thieves: quantity × the shelf price). */
	value: number;
	/** The store dog barked at the grab: he runs slower (Unity plays the bark). */
	dogBarked: boolean;
	caughtBy: StoreThiefCatcher;
	/** Coins paid for catching him (0 otherwise). */
	coins: number;
};

export type StoreSecurityOutcomeKind = "caught" | "escaped" | "guard";

/** The last thief's ending, for a short HUD toast. */
export type StoreSecurityOutcome = {
	kind: StoreSecurityOutcomeKind;
	coins: number;
	productName: string;
	quantity: number;
	at: number;
};

export type StoreSecurityState = {
	/** At most one thief at a time. */
	thief: StoreThief | null;
	/** Next spawn (null = not scheduled: the market is closed or the era has no thieves yet). */
	nextAt: number | null;
	seed: number;
	/** The day the *Today counters belong to (day.dayNumber). */
	statsDay: number;
	caughtToday: number;
	escapedToday: number;
	lostValueToday: number;
	totalCaught: number;
	totalEscaped: number;
	lastOutcome: StoreSecurityOutcome | null;
	/** Last tick: a long gap (the game was closed) sends an active thief away and gives the goods back. */
	tickAt: number;
};

/** One shelf slot a thief can steal from (a product with stock). */
export type SecurityShelfSlot = {
	slotId: string;
	shelfId: string;
	productId: number;
	productName: string;
	price: number;
	stock: number;
};

/** What the store must apply after a security step. */
export type SecurityEffect =
	| { kind: "take"; slotId: string; productId: number; quantity: number }
	| { kind: "return"; slotId: string; productId: number; quantity: number }
	/** Cash out of the till (negative) or back into it (positive). */
	| { kind: "cash"; coins: number }
	| { kind: "reward"; coins: number; experience: number; reputation: number };

/** What Unity gets in every snapshot (security). Flat and JsonUtility-friendly: no missing fields. */
export type StoreThiefSnapshot = {
	id: string;
	phase: StoreThiefPhase;
	productId: number;
	productName: string;
	slotId: string;
	shelfId: string;
	quantity: number;
	value: number;
	spawnedAt: number;
	grabAt: number;
	fleeDeadline: number;
	guardCatchAt: number;
	removeAt: number;
	/** Relative to the snapshot's sentAt (0 when passed / not applicable). */
	grabInMs: number;
	fleeLeftMs: number;
	guardInMs: number;
	dogBarked: boolean;
	caughtBy: StoreThiefCatcher;
	coins: number;
};

export type StoreSecuritySnapshot = {
	/** null when there is no thief (Unity: JsonUtility leaves it with an empty id). */
	thief: StoreThiefSnapshot | null;
	guardHired: boolean;
	caughtToday: number;
	escapedToday: number;
	lostValueToday: number;
	lastOutcome: {
		kind: StoreSecurityOutcomeKind;
		coins: number;
		productName: string;
		quantity: number;
		ageMs: number;
	} | null;
};
