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
export type Page = {
	route: string;
	title: string;
	subtitle: string;
	icon: string;
	chips: Button[];
	cards: Card[];
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
	return { route, title, subtitle: "", icon: "", chips: [], cards, ...options };
}
export const ratio = (value: number, total: number) =>
	Math.max(0, Math.min(1, value / Math.max(total, 1)));
