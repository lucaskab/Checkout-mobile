import { basename, extname } from "node:path";
import type { GameStore } from "@/@types/game";
import { type GameIconId, gameIconAssets } from "@/data/game-icon-assets";
import { marketExpansionAssets } from "@/data/market-expansion-assets";
import { getProductAsset } from "@/data/product-assets";

// Flat shapes so Unity's JsonUtility can read them without a JSON library.
export type Variant = "primary" | "secondary" | "success" | "danger" | "coin" | "gem";
export type Button = {
	label: string;
	icon: string;
	variant: Variant;
	enabled: boolean;
	active: boolean;
	// A store action and its JSON-encoded argument list, or a navigation route.
	action: string;
	args: string;
	route: string;
	after: string;
	ok: string;
	fail: string;
	// Small red counter on the button (shop tabs: things waiting in the inventory).
	badge: string;
};
export type Card = {
	title: string;
	eyebrow: string;
	subtitle: string;
	icon: string;
	badge: string;
	tone: string;
	lines: string[];
	progress: number;
	buttons: Button[];
};
/** One place of a fixture in the shelf window (layout "shelf"). */
export type ShelfSlotView = {
	slotId: string;
	index: number;
	/** "product" | "empty" | "locked" (can be opened with "Expandir") | "hidden". */
	state: string;
	/** "top" = eye level, "bottom" = the row below. */
	row: string;
	productId: number;
	name: string;
	icon: string;
	stock: number;
	capacity: number;
	reserve: number;
	price: number;
	minPrice: number;
	maxPrice: number;
	suggested: number;
	cost: number;
	/** Customers' feeling about the price: "Barato", "Justo", "Caro", "Muito caro". */
	mood: string;
	/** "success" | "info" | "warning" | "danger". */
	moodTone: string;
	level: number;
	maxLevel: number;
	upgradeCost: number;
	restockAmount: number;
	/** "A caminho · 3 min" when an order is on the way and the depot is empty. */
	incoming: string;
	/** Locked slot: what opening it costs. */
	unlockCost: number;
	unlockLevel: number;
};
/** A product that can go on the fixture (picker of the shelf window). */
export type ShelfPickView = {
	productId: number;
	name: string;
	icon: string;
	category: string;
	reserve: number;
	price: number;
	profit: number;
};
/** The shelf window: the fixture drawn as in the shop, its places, its care and its upgrades. */
export type ShelfView = {
	id: string;
	/** crates, produce, cooler, fridge, basket, bakery, display, gondola, freezer, chest, counter. */
	kind: string;
	/** Picture of the fixture (Resources/CheckoutDesktop/Fixtures/<art>). */
	art: string;
	/** Colour of the fixture's sign (hex without #). */
	tint: string;
	name: string;
	accepts: string;
	condition: number;
	careTitle: string;
	careVerb: string;
	careHint: string;
	/** What the mess looks like: wilted, melt, smudge, crumbs, mess, frost. */
	careSpot: string;
	rowTop: string;
	rowBottom: string;
	slotCount: number;
	expandCost: number;
	expandLevel: number;
	capacity: number;
	capacityNext: number;
	capacityCost: number;
	capacityLevel: number;
	stallNote: string;
	slots: ShelfSlotView[];
	picks: ShelfPickView[];
};
export type Page = {
	route: string;
	title: string;
	subtitle: string;
	icon: string;
	// "" = side drawer with a list of cards; "shop" = the full-screen shop (category rail + tile grid).
	layout: string;
	// Shop categories (left rail). Chips are the sub-filters of the open category.
	tabs: Button[];
	chips: Button[];
	cards: Card[];
	/** Layout "shelf" only. */
	shelf: ShelfView | null;
};
export type State = GameStore;

export const fmt = (value: number) => Math.round(value).toLocaleString("pt-BR");
const file = (path: unknown) => basename(String(path), extname(String(path)));
export const gameIcon = (id: GameIconId) => `Icons/${file(gameIconAssets[id])}`;
export const productIcon = (id: number) => `Products/${file(getProductAsset(id))}`;
export const expansionIcon = (id: keyof typeof marketExpansionAssets) =>
	`Expansions/${file(marketExpansionAssets[id])}`;

export function button(label: string, options: Partial<Button> = {}): Button {
	return {
		label,
		icon: "",
		variant: "primary",
		enabled: true,
		active: false,
		action: "",
		args: "[]",
		route: "",
		after: "",
		ok: "",
		fail: "",
		badge: "",
		...options,
	};
}
export function act(
	label: string,
	action: string,
	args: unknown[],
	options: Partial<Button> = {},
) {
	return button(label, { action, args: JSON.stringify(args), ...options });
}
export const go = (label: string, route: string, options: Partial<Button> = {}) =>
	button(label, { route, variant: "secondary", ...options });
// "~" replaces the current page instead of pushing a new one (filters, steppers).
export const swap = (label: string, route: string, active: boolean, icon = "") =>
	button(label, { route: `~${route}`, variant: "secondary", active, icon });

export function card(title: string, options: Partial<Card> = {}): Card {
	return {
		title,
		eyebrow: "",
		subtitle: "",
		icon: "",
		badge: "",
		tone: "",
		lines: [],
		progress: -1,
		buttons: [],
		...options,
	};
}
export function page(
	route: string,
	title: string,
	cards: Card[],
	options: Partial<Page> = {},
): Page {
	return { route, title, subtitle: "", icon: "", layout: "", tabs: [], chips: [], cards, shelf: null, ...options };
}
export const ratio = (value: number, total: number) =>
	Math.max(0, Math.min(1, value / Math.max(total, 1)));
export const decorIcon = (file: string) => `Decor/${file}`;
