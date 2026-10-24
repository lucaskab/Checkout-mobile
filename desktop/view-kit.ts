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
/** A number on a board: header chips and the facts of the picked tile. */
export type BoardStat = { icon: string; value: string; label: string; tone: string };
/** A milestone on the board's meter (a chest at 25 %, a trophy at the end…). state: locked | ready | done. */
export type BoardMark = { at: number; icon: string; label: string; state: string; action: Button };
/** The bar across the top of a board (warehouse space, collection, points to the next chest…). max 0 = none. */
export type BoardMeter = {
	title: string;
	icon: string;
	value: number;
	max: number;
	text: string;
	/** success | warning | danger | info | gold */
	tone: string;
	marks: BoardMark[];
};
/** One tile of a board: a product, a delivery, a machine, a mission, a trophy… */
export type BoardTile = {
	id: string;
	/** Section the tile belongs to (a title is drawn when it changes). */
	group: string;
	icon: string;
	title: string;
	subtitle: string;
	/** Ribbon on the corner ("ACABANDO", "NOVO", "PRONTO!"). */
	sticker: string;
	/** Colour of the tile and its ribbon: success | warning | danger | info | gold | locked | "". */
	tone: string;
	/** Number pill on the top right (stock, quantity…). */
	badge: string;
	stars: number;
	maxStars: number;
	/** 0–1 bar on the tile, below 0 = none. */
	fill: number;
	fillText: string;
	/** Countdown (epoch ms, 0 = none) and its full length, drawn as a ticking clock on the tile. */
	timerEnd: number;
	timerTotal: number;
	/** "" | locked (silhouette) | ready (glows and bounces) | busy | done (stamped). */
	state: string;
	/** The big button of the tile (label "" = none). */
	action: Button;
	/** Side panel of the picked tile: a short text, facts, lines and every action. */
	detail: string;
	facts: BoardStat[];
	lines: string[];
	actions: Button[];
	/** Delivery lanes (board style "road"): where the truck comes from (art + name), which truck it is and
	 * the lane's state: road (driving, progress from the timer) | dock (arrived) | free | locked. */
	origin: string;
	originLabel: string;
	vehicle: string;
	lane: string;
};
/** A game window built from tiles (layout "board"): stock, deposit, deliveries, production, missions, trophies. */
export type BoardView = {
	/** Colour of the header band (hex without #). */
	tint: string;
	/** Picture behind the tiles (Resources/CheckoutDesktop/<path>). */
	backdrop: string;
	/** Tip shown by the clerk at the bottom ("3 produtos acabando: peça agora!"). */
	tip: string;
	stats: BoardStat[];
	meter: BoardMeter;
	tiles: BoardTile[];
	/** Big actions under the tiles (order everything that is running out, collect all…). */
	footer: Button[];
	/** "card" = square tiles in a grid, "row" = wide rows (missions, trophies), "road" = delivery lanes. */
	style: string;
	columns: number;
	/** Epoch ms when the view was made (Unity keeps the timers ticking from it). */
	now: number;
	empty: string;
	/** Tile picked when the board opens (id); "" = the first one. */
	focus: string;
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
	/**
	 * Sibling windows shown as big tabs in the header (Lucas 19/10, "a HUD está lotada"): one toolbar button opens a
	 * group (Produtos: Prateleiras · Estoque · Entregas; Missões: Missões · Conquistas) and these switch inside it.
	 */
	sections: Button[];
	cards: Card[];
	/** Layout "shelf" only. */
	shelf: ShelfView | null;
	/** Layout "board" only. */
	board: BoardView | null;
	/** Layout "kitchen" only: the hand-made production game. */
	kitchen: KitchenView | null;
};
/** One thing the player drags in a kitchen step (an ingredient, a tool, a piece). */
export type KitchenItem = { icon: string; label: string };
/**
 * One step of a kitchen game (CheckoutDesktopHUD.Kitchen.cs). Kinds:
 *  add    drag the items onto the art (in order; out of order costs quality)
 *  rub    rub/stir over the art until the bar fills (count = strokes); slow > 0 = too fast spoils it
 *  heat   hold to heat, let go to cool: keep the gauge inside the zone for `seconds`
 *  stop   the gauge runs by itself (oven, fermentation, cooling): tap when it is inside the zone
 *  cut    drag the knife along each guide (lines = x0,y0,x1,y1 over the art, 0–1)
 *  tap    tap every spot (spots = x,y over the art)
 *  place  drag a copy of items[0] onto every spot
 *  swipe  strokes in one direction over the art (dir in degrees, -1 = sideways either way)
 */
export type KitchenStep = {
	kind: string;
	title: string;
	hint: string;
	/** Art on the bench when the step starts and what it turns into as the step goes (last = done). */
	art: string;
	states: string[];
	/** Art drawn behind it (the oven, the pot on the stove) and where the art sits over it (x, y, 0–1). */
	back: string;
	at: number[];
	size: number;
	items: KitchenItem[];
	lines: number[];
	spots: number[];
	/** Gauge: the good zone (0–1), its scale labels ([from, to]) and unit; how it moves. */
	zone: number[];
	scale: number[];
	unit: string;
	gauge: string;
	seconds: number;
	count: number;
	dir: number;
	slow: number;
	/** Art that follows the finger (knife, whisk, tweezers…). */
	tool: string;
	/** Short fact shown when the step is done ("Ponto de véu!"). */
	done: string;
	/** Puzzle steps (kind "tray", CheckoutDesktopHUD.KitchenPuzzle.cs): the board in cells [columns, rows], the
	 * pieces that may be dealt (ids of the puzzle's piece set) and how many 1×1 pieces at most (fewer = harder). */
	grid: number[];
	pieces: string[];
	singles: number;
};
export type KitchenView = {
	recipeId: string;
	sectorId: string;
	title: string;
	icon: string;
	tint: string;
	bench: string;
	output: number;
	/** Where to go back to (the sector board). */
	back: string;
	canCook: boolean;
	reason: string;
	steps: KitchenStep[];
	/** QA only ("kitchen:<recipe>:<step>"): opens straight on that step, no scoring. -1 = normal game. */
	demo: number;
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
	return { route, title, subtitle: "", icon: "", layout: "", tabs: [], chips: [], sections: [], cards, shelf: null, board: null, kitchen: null, ...options };
}
export const ratio = (value: number, total: number) =>
	Math.max(0, Math.min(1, value / Math.max(total, 1)));
export const decorIcon = (file: string) => `Decor/${file}`;

export const stat = (icon: string, value: string, label: string, tone = ""): BoardStat => ({ icon, value, label, tone });
export const noButton = () => button("", { variant: "secondary", enabled: false });
export function tile(id: string, title: string, options: Partial<BoardTile> = {}): BoardTile {
	return {
		id,
		group: "",
		icon: "",
		title,
		subtitle: "",
		sticker: "",
		tone: "",
		badge: "",
		stars: 0,
		maxStars: 0,
		fill: -1,
		fillText: "",
		timerEnd: 0,
		timerTotal: 0,
		state: "",
		action: noButton(),
		detail: "",
		facts: [],
		lines: [],
		actions: [],
		origin: "",
		originLabel: "",
		vehicle: "",
		lane: "",
		...options,
	};
}
export function meter(title: string, value: number, max: number, options: Partial<BoardMeter> = {}): BoardMeter {
	return { title, icon: "", value, max, text: "", tone: "success", marks: [], ...options };
}
export const noMeter = () => meter("", 0, 0);
export function board(tiles: BoardTile[], options: Partial<BoardView> = {}): BoardView {
	return {
		tint: "2E8CAE",
		backdrop: "",
		tip: "",
		stats: [],
		meter: noMeter(),
		tiles,
		footer: [],
		style: "card",
		columns: 4,
		now: Date.now(),
		empty: "Nada por aqui ainda.",
		focus: "",
		...options,
	};
}
export function kstep(kind: string, title: string, hint: string, options: Partial<KitchenStep> = {}): KitchenStep {
	return {
		kind,
		title,
		hint,
		art: "",
		states: [],
		back: "",
		at: [0.5, 0.5],
		size: 300,
		items: [],
		lines: [],
		spots: [],
		zone: [0.7, 0.85],
		scale: [0, 100],
		unit: "",
		gauge: "",
		seconds: 6,
		count: 8,
		dir: 0,
		slow: 0,
		tool: "",
		done: "",
		grid: [],
		pieces: [],
		singles: 0,
		...options,
	};
}
