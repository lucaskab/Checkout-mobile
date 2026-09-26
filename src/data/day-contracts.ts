import type {
	DayContractDifficulty,
	DayContractKind,
} from "@/@types/market-day";

// Contracts offered at the start of each day. Targets scale with the market level and are
// sized for one DAY_DURATION_MS turn; see services/market-day.ts.
export type DayContractDefinition = {
	description: (target: number, categoryLabel: string) => string;
	difficulty: DayContractDifficulty;
	icon: string;
	id: string;
	kind: DayContractKind;
	target: (level: number) => number;
	title: (categoryLabel: string) => string;
};

const round = (value: number, step: number) =>
	Math.max(step, Math.round(value / step) * step);

export const dayContractDefinitions: DayContractDefinition[] = [
	{
		id: "caixa-cheio",
		kind: "revenue",
		difficulty: 1,
		icon: "coin",
		title: () => "Caixa cheio",
		description: (target) =>
			`Fature ${target.toLocaleString("pt-BR")} moedas hoje.`,
		target: (level) => round(180 + level * 45, 10),
	},
	{
		id: "margem-boa",
		kind: "profit",
		difficulty: 2,
		icon: "receipt",
		title: () => "Margem saudável",
		description: (target) =>
			`Termine o dia com ${target.toLocaleString("pt-BR")} moedas de lucro nas vendas.`,
		target: (level) => round(70 + level * 20, 10),
	},
	{
		id: "casa-cheia",
		kind: "customers",
		difficulty: 1,
		icon: "customers",
		title: () => "Casa cheia",
		description: (target) => `Receba ${target} clientes antes de fechar.`,
		target: (level) => 7 + Math.min(8, Math.floor(level / 2)),
	},
	{
		id: "atendimento-ouro",
		kind: "requests",
		difficulty: 2,
		icon: "handshake",
		title: () => "Atendimento de ouro",
		description: (target) =>
			`Resolva bem ${target} pedidos especiais de clientes.`,
		target: (level) => 2 + Math.min(3, Math.floor(level / 4)),
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
		target: (level) => 3 + Math.min(3, Math.floor(level / 5)),
	},
	{
		id: "especialista",
		kind: "category",
		difficulty: 3,
		icon: "target",
		title: (category) => `Especialista em ${category}`,
		description: (target, category) =>
			`Venda ${target} unidades de ${category.toLocaleLowerCase("pt-BR")}.`,
		target: (level) => 5 + Math.min(10, Math.floor(level * 0.8)),
	},
];

export const dayContractRewardMultiplier: Record<
	DayContractDifficulty,
	number
> = { 1: 1, 2: 1.5, 3: 2.2 };
