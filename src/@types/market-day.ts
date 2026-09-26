import type { CustomerArchetype, CustomerMood } from "./customer-simulation";

// A market day is a turn: pick a contract, open, serve special requests, close and review.
export type MarketDayPhase = "planning" | "open" | "results";

export type DayContractKind =
	| "revenue"
	| "profit"
	| "customers"
	| "requests"
	| "satisfaction"
	| "category"
	| "no-expired";

export type DayContractDifficulty = 1 | 2 | 3;

export type DayReward = {
	coins: number;
	diamonds: number;
	experience: number;
};

export type DayContract = {
	category?: string;
	categoryLabel?: string;
	description: string;
	difficulty: DayContractDifficulty;
	icon: string;
	id: string;
	kind: DayContractKind;
	reward: DayReward;
	target: number;
	title: string;
};

export type SpecialRequestKind = "produto" | "alternativa" | "ajuda";

export type SpecialRequestQuality = "best" | "good" | "bad";

export type SpecialRequestOption = {
	id: string;
	label: string;
	detail: string;
	productId?: number;
	quality: SpecialRequestQuality;
	// "stock" sells one unit straight from the storage room.
	source?: "stock" | "shelf" | "none";
};

export type SpecialRequestStatus =
	| "pending"
	| "served"
	| "partial"
	| "failed"
	| "expired";

export type SpecialRequest = {
	archetype: CustomerArchetype;
	createdAt: number;
	customerId: string;
	customerName: string;
	expiresAt: number;
	id: string;
	kind: SpecialRequestKind;
	message: string;
	mood: CustomerMood;
	options: SpecialRequestOption[];
	outcome: string;
	productId: number;
	productName: string;
	resolvedAt: number | null;
	status: SpecialRequestStatus;
	tip: number;
};

export type DayStats = {
	incidentsFixed: number;
	checkoutsLost: number;
	customers: number;
	loyaltyChange: number;
	profit: number;
	reputationChange: number;
	requestsExpired: number;
	requestsFailed: number;
	requestsPartial: number;
	requestsServed: number;
	revenue: number;
	satisfactionSamples: number;
	satisfactionTotal: number;
	soldByCategory: Record<string, number>;
	tips: number;
	unitsSold: number;
};

export type DayGrade = "S" | "A" | "B" | "C" | "D";

export type DayResult = {
	averageSatisfaction: number;
	bonus: DayReward;
	closedAt: number;
	contract: DayContract | null;
	contractCompleted: boolean;
	contractProgress: number;
	dayNumber: number;
	durationMs: number;
	grade: DayGrade;
	highlights: string[];
	score: number;
	stats: DayStats;
	total: DayReward;
};

export type GameDayState = {
	contract: DayContract | null;
	dayNumber: number;
	endsAt: number | null;
	// Customer loyalty (0-100) carries over between days and brings more visits.
	loyalty: number;
	offers: DayContract[];
	phase: MarketDayPhase;
	requests: SpecialRequest[];
	result: DayResult | null;
	startedAt: number | null;
	stats: DayStats;
};

export type DayCustomerInput = {
	archetype: CustomerArchetype;
	customerId: string;
	customerName: string;
	mood: CustomerMood;
	seed: number;
};

export type DayCatalogProduct = {
	category: string;
	categoryLabel: string;
	id: number;
	name: string;
	purchasePrice: number;
	sellingPrice: number;
};

// What the store can offer right now: products on shelves (with stock) and in storage.
export type DayStoreContext = {
	catalog: DayCatalogProduct[];
	shelfProductIds: number[];
	storageProductIds: number[];
	unlockedProductIds: number[];
};
