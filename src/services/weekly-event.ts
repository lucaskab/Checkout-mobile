import type { MarketEraId } from "@/@types/economy";
import { getMarketEra } from "@/data/economy";
import { itemCatalog } from "@/data/market-products";

// Weekly event ("evento da semana"): every calendar week has a theme. Its products are wanted more by the
// customers all week, and selling enough of them pays a prize once. The themes take turns, so coming back
// every week brings something different.

export type WeeklyTheme = {
	id: string;
	name: string;
	description: string;
	categories: string[];
	/** Units of the theme's products to sell during the week. */
	goal: number;
	/** Customers want the theme's products this much more (necessity ×). */
	boost: number;
};

export const weeklyThemes: WeeklyTheme[] = [
	{
		id: "feira",
		name: "Semana da Feira",
		description: "Frutas, verduras e orgânicos em alta: o bairro quer comer bem.",
		categories: ["hortifruti", "organicos"],
		goal: 120,
		boost: 1.3,
	},
	{
		id: "festa",
		name: "Semana da Festa",
		description: "Aniversários e churrascos: bebidas, doces e chocolates saem rápido.",
		categories: ["bebidas", "refrigerantes", "aguas", "energeticos", "doces", "chocolates", "bolachas"],
		goal: 180,
		boost: 1.3,
	},
	{
		id: "cafe",
		name: "Semana do Café da Manhã",
		description: "Pão, leite, queijos e frios logo cedo.",
		categories: ["padaria", "laticinios", "frios", "queijos"],
		goal: 140,
		boost: 1.3,
	},
	{
		id: "freezer",
		name: "Semana do Freezer",
		description: "Calor na cidade: congelados, carnes e peixes para estocar.",
		categories: ["congelados", "carnes", "peixes"],
		goal: 80,
		boost: 1.3,
	},
];

export type WeeklyEventState = {
	/** Week the progress refers to ("2026-W40"). */
	weekKey: string;
	/** Units of the theme's products already sold when the week started. */
	baseline: number;
	claimed: boolean;
};

const WEEK = 7 * 24 * 60 * 60_000;
// Weeks start on Monday 00:00 local time (5 Jan 1970 was a Monday).
const FIRST_MONDAY = new Date(1970, 0, 5).getTime();

export function getWeekIndex(now: number) {
	return Math.floor((now - FIRST_MONDAY) / WEEK);
}

export function getWeekKey(now: number) {
	return `S${getWeekIndex(now)}`;
}

export function getWeeklyTheme(now: number) {
	return weeklyThemes[((getWeekIndex(now) % weeklyThemes.length) + weeklyThemes.length) % weeklyThemes.length];
}

/** When the current week ends (next Monday 00:00 local). */
export function getWeekEnd(now: number) {
	return FIRST_MONDAY + (getWeekIndex(now) + 1) * WEEK;
}

export function getThemeUnitsSold(theme: WeeklyTheme, soldByProduct: Record<number, number> | undefined) {
	let total = 0;
	for (const product of itemCatalog)
		if (theme.categories.includes(product.category)) total += soldByProduct?.[product.id] ?? 0;
	return total;
}

export function createWeeklyEventState(): WeeklyEventState {
	return { weekKey: "", baseline: 0, claimed: false };
}

export function normalizeWeeklyEventState(value: unknown): WeeklyEventState {
	if (!value || typeof value !== "object") return createWeeklyEventState();
	const item = value as Partial<WeeklyEventState>;
	return {
		weekKey: typeof item.weekKey === "string" ? item.weekKey : "",
		baseline: typeof item.baseline === "number" && Number.isFinite(item.baseline) ? Math.max(0, item.baseline) : 0,
		claimed: item.claimed === true,
	};
}

/** The weekly state for `now`: a new week starts counting from the sales made so far. */
export function syncWeeklyEvent(
	state: WeeklyEventState | undefined,
	soldByProduct: Record<number, number> | undefined,
	now: number,
): WeeklyEventState {
	const key = getWeekKey(now);
	if (state && state.weekKey === key) return state;
	return { weekKey: key, baseline: getThemeUnitsSold(getWeeklyTheme(now), soldByProduct), claimed: false };
}

export function getWeeklyProgress(
	state: WeeklyEventState | undefined,
	soldByProduct: Record<number, number> | undefined,
	now: number,
) {
	const theme = getWeeklyTheme(now);
	const synced = syncWeeklyEvent(state, soldByProduct, now);
	const sold = Math.max(0, getThemeUnitsSold(theme, soldByProduct) - synced.baseline);
	return { theme, sold, done: sold >= theme.goal, claimed: synced.claimed };
}

export function getWeeklyReward(eraId: MarketEraId) {
	return { coins: Math.round((getMarketEra(eraId).itemUpgradeBaseCost * 15) / 10) * 10, diamonds: 5 };
}

export function getWeeklyNecessityMultiplier(category: string, now: number) {
	const theme = getWeeklyTheme(now);
	return theme.categories.includes(category) ? theme.boost : 1;
}
