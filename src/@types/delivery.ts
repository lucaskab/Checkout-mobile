/** Delivery (the market's online orders, src/services/delivery.ts). Times are epoch milliseconds. */
export type DeliveryOrderStatus =
	| "oferta"
	| "aceito"
	| "aguardando-moto"
	| "moto-na-porta"
	| "a-caminho"
	| "entregue"
	| "expirado"
	| "recusado"
	| "cancelado";

export type DeliveryCustomer = {
	name: string;
	neighborhood: string;
	/** Seed of the customer's avatar picture (1–999). */
	avatar: number;
};

export type DeliveryItem = {
	productId: number;
	quantity: number;
};

export type DeliveryCourier = {
	/** Id of the motoboy in src/data/delivery-data.ts. */
	id: string;
	name: string;
	color: string;
	/** The motoboy reaches the store front. */
	arriveAt: number;
	/** When the motoboy started waiting at the door ("moto-na-porta"). */
	doorSince?: number;
	/** When the bag leaves the store ("a-caminho") plus the trip time. */
	deliverAt?: number;
};

export type DeliveryOrder = {
	id: string;
	status: DeliveryOrderStatus;
	customer: DeliveryCustomer;
	/** Customer's note; "" when there is none. */
	note: string;
	/** What the customer ordered. */
	items: DeliveryItem[];
	/** What went into the bag (set when packed; missing units are allowed). */
	packed?: DeliveryItem[];
	distanceKm: number;
	fee: number;
	/** Shelf value of the ordered units (priced again when packed). */
	itemsValue: number;
	createdAt: number;
	expiresAt: number;
	acceptedAt?: number;
	/** Last moment the bag can be packed; later the customer cancels. */
	packBy?: number;
	packedAt?: number;
	courier?: DeliveryCourier;
	/** Packing quality 0–1 (the mini-game). */
	quality?: number;
	/** Packed units / ordered units. */
	fillRatio?: number;
	/** Stars 1–5 in half steps. */
	stars?: number;
	/** Tip paid on arrival. */
	tip?: number;
	/** Streak bonus paid on arrival. */
	bonus?: number;
	/** Coins paid on arrival (goods + fee + tip + bonus). */
	paid?: number;
};

export type DeliveryState = {
	orders: DeliveryOrder[];
	/** When the next offer wave may arrive (null until the market opens for the first time). */
	nextOfferAt: number | null;
	/** Running average of the stars (starts at 4.6, 1–5). */
	rating: number;
	/** Stars of the last deliveries (up to 20, oldest first). */
	ratings: number[];
	streak: number;
	bestStreak: number;
	delivered: number;
	earnings: number;
	/** Seed of the random draws (offers, customers, motoboys). */
	seed: number;
};

/** What the packing mini-game reports (packDeliveryOrder). */
export type DeliveryPackResult = {
	items: DeliveryItem[];
	/** Packing quality 0–1. */
	quality: number;
	/** Seconds the packing took. */
	seconds: number;
};
