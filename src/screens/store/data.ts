import type { StoreAlert } from "@/@types/store";

export { shelves } from "@/data/market-products";

export const dashboardMetrics = {
	dailyGoal: 1500,
};

export const lowStockAlerts: StoreAlert[] = [
	{
		actionLabel: "Reabastecer",
		emoji: "🥛",
		id: "dairy",
		issue: "Restam 2 unidades na prateleira.",
		name: "Leite integral",
		type: "low",
	},
	{
		actionLabel: "Ver",
		emoji: "🥖",
		id: "bakery",
		issue: "A produção fica pronta em 4 minutos.",
		name: "Pão francês",
		type: "notice",
	},
];
