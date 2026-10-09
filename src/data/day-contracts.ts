import type {
	DayContractDifficulty,
	DayContractKind,
} from "@/@types/market-day";
import type { DayForecast } from "@/services/day-forecast";

// Contracts offered at the start of each day. Targets come from the day's forecast (what this market,
// with its shelves, level and size, should see in one turn; src/services/day-forecast.ts):
// the easy one is usually done before half of the day, the medium one a little after half, and the hard
// one asks for nearly a whole good day.
export const CONTRACT_SHARE = { easy: 0.4, medium: 0.6, hard: 0.85 } as const;

export type DayContractDefinition = {
	description: (target: number, categoryLabel: string) => string;
	difficulty: DayContractDifficulty;
	icon: string;
	id: string;
	kind: DayContractKind;
	target: (level: number, forecast: DayForecast, category?: string) => number;
	title: (categoryLabel: string) => string;
};

const round = (value: number, step: number) =>
	Math.max(step, Math.round(value / step) * step);
/** Coins rounded to a friendly number (5 by 5 when small, 10 by 10 after). */
const coins = (value: number) => round(value, value < 150 ? 5 : 10);

export const dayContractDefinitions: DayContractDefinition[] = [
	{
		id: "caixa-cheio",
		kind: "revenue",
		difficulty: 1,
		icon: "coin",
		title: () => "Caixa cheio",
		description: (target) =>
			`Fature ${target.toLocaleString("pt-BR")} moedas hoje.`,
		target: (_level, forecast) => Math.max(20, coins(forecast.revenue * CONTRACT_SHARE.easy)),
	},
	{
		id: "margem-boa",
		kind: "profit",
		difficulty: 2,
		icon: "receipt",
		title: () => "Margem saudável",
		description: (target) =>
			`Termine o dia com ${target.toLocaleString("pt-BR")} moedas de lucro nas vendas.`,
		target: (_level, forecast) => Math.max(10, coins(forecast.profit * CONTRACT_SHARE.medium)),
	},
	{
		id: "casa-cheia",
		kind: "customers",
		difficulty: 1,
		icon: "customers",
		title: () => "Casa cheia",
		description: (target) => `Receba ${target} clientes antes de fechar.`,
		target: (_level, forecast) => Math.max(3, Math.round(forecast.customers * CONTRACT_SHARE.easy)),
	},
	{
		id: "atendimento-ouro",
		kind: "requests",
		difficulty: 2,
		icon: "handshake",
		title: () => "Atendimento de ouro",
		description: (target) =>
			`Resolva bem ${target} pedidos especiais de clientes.`,
		// Requests depend on luck and on the player answering them: half of the expected ones.
		target: (_level, forecast) => Math.max(1, Math.round(forecast.requests * 0.5)),
	},
	{
		id: "clientes-sorrindo",
		kind: "satisfaction",
		difficulty: 2,
		icon: "success",
		title: () => "Clientes sorrindo",
		description: (target) =>
			`Feche o dia com satisfação média de pelo menos ${target}%.`,
		target: (level) => Math.min(82, 66 + level),
	},
	{
		id: "ninguem-esperando",
		kind: "no-expired",
		difficulty: 3,
		icon: "medal",
		title: () => "Ninguém fica esperando",
		description: (target) =>
			`Atenda ${target} pedidos especiais sem deixar nenhum cliente ir embora.`,
		target: (_level, forecast) => Math.max(2, Math.round(forecast.requests * 0.7)),
	},
	{
		id: "especialista",
		kind: "category",
		difficulty: 3,
		icon: "target",
		title: (category) => `Especialista em ${category}`,
		description: (target, category) =>
			`Venda ${target} unidades de ${category.toLocaleLowerCase("pt-BR")}.`,
		target: (_level, forecast, category) => {
			const expected =
				(category ? forecast.unitsByCategory[category] : undefined) ??
				forecast.units / Math.max(1, Object.keys(forecast.unitsByCategory).length);
			return Math.max(2, Math.round(expected * CONTRACT_SHARE.hard));
		},
	},
];

export const dayContractRewardMultiplier: Record<
	DayContractDifficulty,
	number
> = { 1: 1, 2: 1.5, 3: 2.2 };
