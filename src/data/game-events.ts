import type { GameEventDefinition } from "@/@types/game-event";

// Market events (Oct 2026 redesign). Ids match CheckoutEventVisuals in Unity.
//
// crowdShare: the share of the turn's customers, while the event runs, who come *through* its scene (withdraw at the
// ATM, get off the bus, leave the street fair…) before walking in and shopping for real (getEventCustomerOrigin).
//
// Each event changes what a real neighbourhood market would feel on that day, and only happens once the
// market has what the event is about: a power cut needs a fridge, a coffee break needs a team, a crowd
// filming the shop needs a real shop front (requirements.minEra, in the order of the expansions).

/** Drinks that sell cold. */
const drinks = ["bebidas", "refrigerantes", "aguas", "energeticos"];
/** What spoils without power: dairy and cold cuts, drinks in the fridge, freezers and the meat/fish counters. */
const refrigerated = ["laticinios", "queijos", "frios", "congelados", "sorvetes", "carnes", "peixes", ...drinks, "alcoolicos"];

export const gameEvents: GameEventDefinition[] = [
	// Positive
	{
		description: "Um ônibus parou no ponto e desceu uma leva de trabalhadores.",
		durationMinutes: 4,
		effectLabel: "+45% de clientes",
		effects: { customerArrivalMultiplier: 1.45 },
		crowdShare: 0.7,
		id: "hora-do-rush",
		kind: "positive",
		name: "Hora do rush",
		requirements: { minEra: "mesinha" },
	},
	{
		description: "O salário caiu e tem fila no caixa eletrônico da calçada.",
		durationMinutes: 4,
		effectLabel: "+15% de clientes e +40% no orçamento",
		// Payday brings people out to spend (Lucas 15/10: whoever withdraws at the ATM must really go in and buy):
		// a modest +15% of visits on top of the bigger budgets, and most of them queue at the ATM first.
		effects: { customerArrivalMultiplier: 1.15, customerBudgetMultiplier: 1.4 },
		crowdShare: 0.6,
		id: "quinto-dia-util",
		kind: "positive",
		name: "Quinto dia útil",
		requirements: { minEra: "mesinha" },
	},
	{
		description: "A feira livre fechou a rua e trouxe famílias para o bairro. As barracas também vendem fruta.",
		durationMinutes: 5,
		effectLabel: "+25% de clientes e +15% no orçamento; hortifrúti vende um pouco menos",
		effects: {
			customerArrivalMultiplier: 1.25,
			customerBudgetMultiplier: 1.15,
			categoryDemand: { hortifruti: 0.85, organicos: 0.85 },
		},
		crowdShare: 0.5,
		id: "feira-de-rua",
		kind: "positive",
		name: "Feira de rua",
		requirements: { minEra: "mesinha" },
	},
	{
		description: "38°C na rua: todo mundo quer bebida gelada e sorvete.",
		durationMinutes: 4,
		effectLabel: "Procura 2× por bebida gelada e sorvete",
		effects: {
			categoryDemand: { ...Object.fromEntries(drinks.map((category) => [category, 2])), sorvetes: 2 },
		},
		crowdShare: 0.4,
		id: "onda-de-calor",
		kind: "positive",
		name: "Onda de calor",
		requirements: { minEra: "mesinha" },
	},
	{
		description: "A roleta de prêmios na porta anima os clientes a levar mais um item.",
		durationMinutes: 4,
		effectLabel: "+10% de clientes; cada cliente leva +1 item",
		// The wheel at the door pulls in a few passers-by (+10%) who spin it and then go in to shop.
		effects: { customerArrivalMultiplier: 1.1, extraBasketItems: 1 },
		crowdShare: 0.5,
		id: "sorteio-na-porta",
		kind: "positive",
		name: "Sorteio na porta",
		requirements: { minEra: "tenda" },
	},
	{
		description: "O fornecedor estacionou com ofertas direto do caminhão.",
		durationMinutes: 4,
		effectLabel: "-25% no custo dos pedidos",
		effects: { supplierCostMultiplier: 0.75 },
		crowdShare: 0.35,
		id: "caminhao-de-ofertas",
		kind: "positive",
		name: "Caminhão de ofertas",
		requirements: { minEra: "banca" },
	},
	{
		description: "Tem jogo do Brasil no telão: o bairro inteiro vem buscar cerveja, refri e carne para o churrasco.",
		durationMinutes: 5,
		effectLabel: "+15% de clientes; procura 2,5× por cerveja e refri, 2× por bebidas e carnes",
		effects: {
			customerArrivalMultiplier: 1.15,
			categoryDemand: {
				alcoolicos: 2.5,
				refrigerantes: 2.5,
				bebidas: 2,
				aguas: 1.5,
				energeticos: 1.5,
				carnes: 2,
				bolachas: 1.5,
			},
		},
		crowdShare: 0.5,
		id: "dia-de-jogo",
		kind: "positive",
		name: "Dia de jogo do Brasil",
		requirements: { minEra: "conteiner" },
	},
	{
		description: "Uma pausa para o café nos fundos deixou a equipe animada.",
		durationMinutes: 4,
		effectLabel: "Equipe 40% mais rápida e +30% de XP",
		effects: { staffSpeedMultiplier: 1.4, experienceMultiplier: 1.3 },
		id: "cafe-com-a-equipe",
		kind: "positive",
		name: "Café com a equipe",
		requirements: { minEra: "conteiner", needsStaff: true },
	},
	{
		description: "Uma influenciadora está filmando um dos seus produtos na frente do mercado.",
		durationMinutes: 4,
		effectLabel: "+20% de clientes; procura 2× pelo produto do vídeo",
		effects: { customerArrivalMultiplier: 1.2, featuredProductBoost: 2 },
		crowdShare: 0.5,
		id: "viralizou",
		kind: "positive",
		name: "Viralizou!",
		requirements: { minEra: "spati" },
	},
	// Negative / mixed
	{
		description: "A chuva forte deixou as ruas vazias.",
		durationMinutes: 5,
		effectLabel: "-35% de clientes",
		effects: { customerArrivalMultiplier: 0.65 },
		id: "chuva-forte",
		kind: "negative",
		name: "Chuva forte",
		requirements: { minEra: "mesinha" },
	},
	{
		description: "A rua foi aberta para obras e o trânsito foi desviado.",
		durationMinutes: 5,
		effectLabel: "-45% de clientes",
		effects: { customerArrivalMultiplier: 0.55 },
		id: "rua-em-obras",
		kind: "negative",
		name: "Rua em obras",
		requirements: { minEra: "mesinha" },
	},
	{
		description: "O trânsito parou: as entregas atrasam e quem está preso no carro desce para comprar água.",
		durationMinutes: 4,
		effectLabel: "Entregas 70% mais lentas; motoristas buzinam pedindo água e refri: venda pela janela!",
		effects: {
			interaction: "window-sales",
			supplierDurationMultiplier: 1.7,
			categoryDemand: { aguas: 1.3, refrigerantes: 1.3 },
		},
		id: "engarrafamento",
		kind: "negative",
		name: "Engarrafamento",
		requirements: { minEra: "mesinha" },
	},
	{
		description: "O dinheiro acabou e o vizinho está em liquidação: o bairro procura o mais barato.",
		durationMinutes: 4,
		effectLabel: "-35% no orçamento; clientes preferem os produtos baratos",
		effects: { customerBudgetMultiplier: 0.65, cheapPreference: 1 },
		crowdShare: 0.35,
		id: "fim-do-mes",
		kind: "negative",
		name: "Fim do mês",
		requirements: { minEra: "mesinha" },
	},
	{
		description: "A operadora caiu: só dá para pagar em dinheiro, e quem ia passar o cartão gasta só o que tem na carteira.",
		durationMinutes: 4,
		effectLabel: "Só dinheiro no caixa; clientes gastam 20% menos",
		effects: { cashOnly: true, customerBudgetMultiplier: 0.8 },
		id: "maquininha-fora-do-ar",
		kind: "negative",
		name: "Maquininha fora do ar",
		requirements: { minEra: "tenda" },
	},
	{
		description: "Uma turma de escola invadiu o mercado: doces e sorvetes voam das prateleiras.",
		durationMinutes: 4,
		effectLabel: "+15% de clientes e procura 2× por doces",
		effects: {
			customerArrivalMultiplier: 1.15,
			categoryDemand: { doces: 2, chocolates: 2, bolachas: 2, sorvetes: 2 },
		},
		crowdShare: 0.6,
		id: "excursao-da-escola",
		kind: "positive",
		name: "Excursão da escola",
		requirements: { minEra: "conteiner" },
	},
	{
		description: "O transformador da rua estourou: geladeiras e freezers desligaram e a produção parou.",
		durationMinutes: 4,
		effectLabel: "Produção 65% mais lenta; menos procura por gelados",
		effects: {
			productionDurationMultiplier: 1.65,
			categoryDemand: Object.fromEntries(refrigerated.map((category) => [category, 0.7])),
			powerOutage: true,
		},
		id: "queda-de-energia",
		kind: "negative",
		name: "Queda de energia",
		requirements: { minEra: "banca", needsRefrigeration: true },
	},
	{
		description: "A equipe está exausta depois de um turno puxado.",
		durationMinutes: 4,
		effectLabel: "Equipe 25% mais lenta e -20% de XP",
		effects: { staffSpeedMultiplier: 0.75, experienceMultiplier: 0.8 },
		id: "turno-puxado",
		kind: "negative",
		name: "Turno puxado",
		requirements: { minEra: "conteiner", needsStaff: true },
	},
	{
		description: "Um fiscal da vigilância sanitária vai checar três pontos do mercado. Resolva cada problema que ele encontrar antes que ele anote!",
		durationMinutes: 5,
		effectLabel: "Checklist do fiscal: tudo resolvido dá bônus e reputação; dois problemas ou mais, multa",
		effects: { interaction: "inspection" },
		id: "vigilancia-sanitaria",
		kind: "negative",
		name: "Vigilância sanitária",
		// The inspector checks real mishaps (price tags, lamps, floor, coolers): only the market building has them.
		requirements: { minEra: "mercadinho" },
	},
	{
		description: "O carro de som do concorrente anuncia ofertas pelo bairro.",
		durationMinutes: 4,
		effectLabel: "-30% de clientes e -20% no orçamento",
		effects: { customerArrivalMultiplier: 0.7, customerBudgetMultiplier: 0.8 },
		id: "carro-de-som",
		kind: "negative",
		name: "Carro de som do concorrente",
		requirements: { minEra: "spati" },
	},
];

export function getGameEvent(eventId: string | null | undefined) {
	return gameEvents.find((event) => event.id === eventId) ?? null;
}
