import type { GameEventDefinition } from "@/@types/game-event";

export const gameEvents: GameEventDefinition[] = [
	{
		description: "O bairro ficou movimentado e mais clientes estão chegando.",
		durationMinutes: 5,
		effectLabel: "+45% de chegada de clientes",
		effects: { customerArrivalMultiplier: 1.45 },

		id: "hora-do-pico",
		kind: "positive",
		name: "Hora do pico",
	},
	{
		description:
			"O pagamento caiu e os clientes estão dispostos a gastar mais.",
		durationMinutes: 6,
		effectLabel: "+40% no orçamento dos clientes",
		effects: { customerBudgetMultiplier: 1.4 },

		id: "pagamento-caiu",
		kind: "positive",
		name: "Dia de pagamento",
	},
	{
		description:
			"Uma influenciadora recomendou o mercado para seus seguidores.",
		durationMinutes: 5,
		effectLabel: "+20% de clientes e +25% de receita",
		effects: {
			customerArrivalMultiplier: 1.2,
			revenueMultiplier: 1.25,
		},

		id: "influenciadora-local",
		kind: "positive",
		name: "Recomendação viral",
	},
	{
		description: "A feira da região trouxe famílias e compradores animados.",
		durationMinutes: 7,
		effectLabel: "+25% de clientes e +15% no orçamento",
		effects: {
			customerArrivalMultiplier: 1.25,
			customerBudgetMultiplier: 1.15,
		},

		id: "feira-do-bairro",
		kind: "positive",
		name: "Feira do bairro",
	},
	{
		description:
			"Os fornecedores ofereceram uma condição especial por tempo limitado.",
		durationMinutes: 6,
		effectLabel: "-25% no custo de novos pedidos",
		effects: { supplierCostMultiplier: 0.75 },

		id: "desconto-atacadista",
		kind: "positive",
		name: "Desconto atacadista",
	},
	{
		description: "As rotas estão livres e os novos pedidos chegam mais rápido.",
		durationMinutes: 5,
		effectLabel: "-40% no tempo de novas entregas",
		effects: { supplierDurationMultiplier: 0.6 },

		id: "rota-livre",
		kind: "positive",
		name: "Rota livre",
	},
	{
		description: "A equipe de produção está trabalhando com energia total.",
		durationMinutes: 6,
		effectLabel: "-40% no tempo de novas produções",
		effects: { productionDurationMultiplier: 0.6 },

		id: "equipe-inspirada",
		kind: "positive",
		name: "Equipe inspirada",
	},
	{
		description: "Um treinamento rápido melhorou o aprendizado com cada venda.",
		durationMinutes: 7,
		effectLabel: "+60% de experiência nas vendas",
		effects: { experienceMultiplier: 1.6 },

		id: "treinamento-expresso",
		kind: "positive",
		name: "Treinamento expresso",
	},
	{
		description:
			"Os caixas estão oferecendo produtos extras com muita eficiência.",
		durationMinutes: 5,
		effectLabel: "+18% de receita nas vendas",
		effects: { revenueMultiplier: 1.18 },

		id: "caixa-da-sorte",
		kind: "positive",
		name: "Caixa da sorte",
	},
	{
		description: "Tudo está funcionando em perfeita sintonia no mercado.",
		durationMinutes: 5,
		effectLabel: "+15% de clientes e receita, +20% de XP",
		effects: {
			customerArrivalMultiplier: 1.15,
			experienceMultiplier: 1.2,
			revenueMultiplier: 1.15,
		},

		id: "dia-perfeito",
		kind: "positive",
		name: "Dia perfeito",
	},
	{
		description: "A chuva afastou parte dos clientes das ruas.",
		durationMinutes: 5,
		effectLabel: "-35% na chegada de clientes",
		effects: { customerArrivalMultiplier: 0.65 },

		id: "chuva-forte",
		kind: "negative",
		name: "Chuva forte",
	},
	{
		description: "Obras próximas dificultaram o acesso ao estacionamento.",
		durationMinutes: 7,
		effectLabel: "-45% na chegada de clientes",
		effects: { customerArrivalMultiplier: 0.55 },

		id: "obras-na-rua",
		kind: "negative",
		name: "Obras na rua",
	},
	{
		description: "Um concorrente iniciou uma promoção agressiva na região.",
		durationMinutes: 6,
		effectLabel: "-30% de clientes e -20% no orçamento",
		effects: {
			customerArrivalMultiplier: 0.7,
			customerBudgetMultiplier: 0.8,
		},

		id: "concorrente-em-promocao",
		kind: "negative",
		name: "Concorrente em promoção",
	},
	{
		description: "Os clientes estão comparando cada preço antes de comprar.",
		durationMinutes: 5,
		effectLabel: "-35% no orçamento dos clientes",
		effects: { customerBudgetMultiplier: 0.65 },

		id: "clientes-economicos",
		kind: "negative",
		name: "Clientes econômicos",
	},
	{
		description: "Falhas nos caixas estão reduzindo o faturamento das vendas.",
		durationMinutes: 5,
		effectLabel: "-22% de receita nas vendas",
		effects: { revenueMultiplier: 0.78 },

		id: "instabilidade-nos-caixas",
		kind: "negative",
		name: "Instabilidade nos caixas",
	},
	{
		description: "O preço do combustível encareceu temporariamente as compras.",
		durationMinutes: 7,
		effectLabel: "+35% no custo de novos pedidos",
		effects: { supplierCostMultiplier: 1.35 },

		id: "alta-do-combustivel",
		kind: "negative",
		name: "Alta do combustível",
	},
	{
		description: "O trânsito pesado está atrasando as novas entregas.",
		durationMinutes: 6,
		effectLabel: "+70% no tempo de novas entregas",
		effects: { supplierDurationMultiplier: 1.7 },

		id: "transito-pesado",
		kind: "negative",
		name: "Trânsito pesado",
	},
	{
		description: "Alguns equipamentos precisam de manutenção emergencial.",
		durationMinutes: 6,
		effectLabel: "+65% no tempo de novas produções",
		effects: { productionDurationMultiplier: 1.65 },

		id: "manutencao-de-equipamentos",
		kind: "negative",
		name: "Equipamentos em manutenção",
	},
	{
		description: "O ritmo da equipe caiu depois de um turno muito puxado.",
		durationMinutes: 5,
		effectLabel: "+35% no tempo de produção e -20% de XP",
		effects: {
			experienceMultiplier: 0.8,
			productionDurationMultiplier: 1.35,
		},

		id: "equipe-cansada",
		kind: "negative",
		name: "Equipe cansada",
	},
	{
		description:
			"Uma fiscalização deixou o atendimento mais lento e cauteloso.",
		durationMinutes: 4,
		effectLabel: "-15% de clientes e receita",
		effects: {
			customerArrivalMultiplier: 0.85,
			revenueMultiplier: 0.85,
		},

		id: "fiscalizacao-surpresa",
		kind: "negative",
		name: "Fiscalização surpresa",
	},
];

export function getGameEvent(eventId: string | null | undefined) {
	return gameEvents.find((event) => event.id === eventId) ?? null;
}
