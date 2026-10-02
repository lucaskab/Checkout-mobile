import type { MarketEraId } from "@/@types/economy";
import type { MissionDefinition } from "@/@types/mission";
import { getMarketEra, getNextMarketEra } from "@/data/economy";

export const missions: MissionDefinition[] = [
	{
		category: "progression",
		description: "Alcance o nível 2 e libere sua primeira expansão.",

		goal: 2,
		id: "level-2",
		metric: "level",
		requiredLevel: 1,
		reward: { coins: 250, items: [{ productId: 48, quantity: 4 }] },
		title: "Primeiros passos",
	},
	{
		category: "progression",
		description: "Chegue ao nível 5 dominando a rotina do mercado.",

		goal: 5,
		id: "level-5",
		metric: "level",
		requiredLevel: 2,
		reward: { coins: 800, items: [{ productId: 50, quantity: 3 }] },
		title: "Mercado em crescimento",
	},
	{
		category: "progression",
		description: "Alcance o nível 10 e torne-se referência no bairro.",

		goal: 10,
		id: "level-10",
		metric: "level",
		requiredLevel: 5,
		reward: { coins: 2_500, items: [{ productId: 51, quantity: 3 }] },
		title: "Dono do bairro",
	},
	{
		category: "progression",
		description: "Chegue ao nível 16 para comandar operações avançadas.",

		goal: 16,
		id: "level-16",
		metric: "level",
		requiredLevel: 10,
		reward: { coins: 7_500, items: [{ productId: 17, quantity: 4 }] },
		title: "Rede regional",
	},
	{
		category: "progression",
		description: "Alcance o nível 22 e domine todos os setores especiais.",

		goal: 22,
		id: "level-22",
		metric: "level",
		requiredLevel: 16,
		reward: { coins: 20_000, items: [{ productId: 31, quantity: 2 }] },
		title: "Império varejista",
	},
	{
		category: "customers",
		description: "Receba seus primeiros clientes no mercado.",

		goal: 5,
		id: "customers-5",
		metric: "customersServed",
		requiredLevel: 1,
		reward: { coins: 120, items: [{ productId: 1, quantity: 3 }] },
		title: "Portas abertas",
	},
	{
		category: "customers",
		description: "Atenda 25 clientes e mantenha o fluxo da loja.",

		goal: 25,
		id: "customers-25",
		metric: "customersServed",
		requiredLevel: 2,
		reward: { coins: 500, items: [{ productId: 46, quantity: 4 }] },
		title: "Movimento constante",
	},
	{
		category: "customers",
		description: "Atenda 100 clientes ao longo da sua jornada.",

		goal: 100,
		id: "customers-100",
		metric: "customersServed",
		requiredLevel: 4,
		reward: { coins: 1_500, items: [{ productId: 13, quantity: 8 }] },
		title: "Casa cheia",
	},
	{
		category: "customers",
		description: "Atenda 350 clientes com consistência.",

		goal: 350,
		id: "customers-350",
		metric: "customersServed",
		requiredLevel: 8,
		reward: { coins: 4_000, items: [{ productId: 14, quantity: 6 }] },
		title: "Fila no caixa",
	},
	{
		category: "customers",
		description: "Atenda 1.000 clientes e prove sua escala.",

		goal: 1_000,
		id: "customers-1000",
		metric: "customersServed",
		requiredLevel: 15,
		reward: { coins: 12_000, items: [{ productId: 55, quantity: 4 }] },
		title: "Mil clientes felizes",
	},
	{
		category: "customers",
		description: "Faça seus primeiros 10 clientes saírem com compras.",

		goal: 10,
		id: "buyers-10",
		metric: "customersWhoBought",
		requiredLevel: 1,
		reward: { coins: 200 },
		title: "Compra garantida",
	},
	{
		category: "customers",
		description: "Converta 75 visitas em compras.",

		goal: 75,
		id: "buyers-75",
		metric: "customersWhoBought",
		requiredLevel: 4,
		reward: { coins: 1_100, items: [{ productId: 49, quantity: 6 }] },
		title: "Bom atendimento",
	},
	{
		category: "customers",
		description: "Faça 300 clientes concluírem uma compra.",

		goal: 300,
		id: "buyers-300",
		metric: "customersWhoBought",
		requiredLevel: 9,
		reward: { coins: 4_500, items: [{ productId: 22, quantity: 3 }] },
		title: "Clientes fiéis",
	},
	{
		category: "sales",
		description: "Venda 10 unidades de qualquer produto.",

		goal: 10,
		id: "units-10",
		metric: "unitsSold",
		requiredLevel: 1,
		reward: { coins: 180, items: [{ productId: 46, quantity: 5 }] },
		title: "Primeiras vendas",
	},
	{
		category: "sales",
		description: "Venda 50 unidades no total.",

		goal: 50,
		id: "units-50",
		metric: "unitsSold",
		requiredLevel: 2,
		reward: { coins: 650 },
		title: "Giro de estoque",
	},
	{
		category: "sales",
		description: "Venda 200 unidades para seus clientes.",

		goal: 200,
		id: "units-200",
		metric: "unitsSold",
		requiredLevel: 5,
		reward: { coins: 2_000, items: [{ productId: 9, quantity: 5 }] },
		title: "Ritmo acelerado",
	},
	{
		category: "sales",
		description: "Venda 750 unidades no total.",

		goal: 750,
		id: "units-750",
		metric: "unitsSold",
		requiredLevel: 10,
		reward: { coins: 6_000, items: [{ productId: 26, quantity: 8 }] },
		title: "Máquina de vendas",
	},
	{
		category: "sales",
		description: "Supere a marca de 2.500 unidades vendidas.",

		goal: 2_500,
		id: "units-2500",
		metric: "unitsSold",
		requiredLevel: 18,
		reward: { coins: 18_000, items: [{ productId: 20, quantity: 4 }] },
		title: "Volume lendário",
	},
	{
		category: "sales",
		description: "Fature suas primeiras 1.000 moedas em vendas.",

		goal: 1_000,
		id: "revenue-1000",
		metric: "revenue",
		requiredLevel: 1,
		reward: { coins: 250 },
		title: "Caixa positivo",
	},
	{
		category: "sales",
		description: "Acumule 5.000 moedas de faturamento.",

		goal: 5_000,
		id: "revenue-5000",
		metric: "revenue",
		requiredLevel: 3,
		reward: { coins: 900, items: [{ productId: 50, quantity: 6 }] },
		title: "Boa margem",
	},
	{
		category: "sales",
		description: "Fature 25.000 moedas com o mercado.",

		goal: 25_000,
		id: "revenue-25000",
		metric: "revenue",
		requiredLevel: 7,
		reward: { coins: 3_500, items: [{ productId: 6, quantity: 4 }] },
		title: "Resultado expressivo",
	},
	{
		category: "sales",
		description: "Alcance 100.000 moedas de faturamento.",

		goal: 100_000,
		id: "revenue-100000",
		metric: "revenue",
		requiredLevel: 13,
		reward: { coins: 10_000, items: [{ productId: 24, quantity: 2 }] },
		title: "Seis dígitos",
	},
	{
		category: "sales",
		description: "Venda 20 tomates ao longo do jogo.",

		goal: 20,
		id: "tomato-sales-20",
		metric: "soldProduct",
		requiredLevel: 1,
		reward: { coins: 220, items: [{ productId: 1, quantity: 5 }] },
		targetProductId: 1,
		title: "Rei do hortifruti",
	},
	{
		category: "sales",
		description: "Venda 40 pães franceses.",

		goal: 40,
		id: "bread-sales-40",
		metric: "soldProduct",
		requiredLevel: 3,
		reward: { coins: 500, items: [{ productId: 56, quantity: 5 }] },
		targetProductId: 9,
		title: "Pão quentinho",
	},
	{
		category: "sales",
		description: "Venda 25 cafés especiais.",

		goal: 25,
		id: "coffee-sales-25",
		metric: "soldProduct",
		requiredLevel: 9,
		reward: { coins: 600, items: [{ productId: 15, quantity: 5 }] },
		targetProductId: 15,
		title: "Hora do café",
	},
	{
		category: "sales",
		description: "Venda ao menos uma unidade de 8 produtos diferentes.",

		goal: 8,
		id: "variety-8",
		metric: "uniqueProductsSold",
		requiredLevel: 4,
		reward: { coins: 1_000 },
		title: "Variedade na gôndola",
	},
	{
		category: "sales",
		description: "Venda ao menos uma unidade de 20 produtos diferentes.",

		goal: 20,
		id: "variety-20",
		metric: "uniqueProductsSold",
		requiredLevel: 10,
		reward: { coins: 4_000, items: [{ productId: 54, quantity: 5 }] },
		title: "Catálogo completo",
	},
	{
		category: "production",
		description: "Fabrique seu primeiro item em um setor especial.",

		goal: 1,
		id: "crafted-1",
		metric: "productionCrafted",
		requiredLevel: 19,
		reward: { coins: 300, items: [{ productId: 43, quantity: 4 }] },
		title: "Produção inaugurada",
	},
	{
		category: "production",
		description: "Produza 10 itens dentro do mercado.",

		goal: 10,
		id: "crafted-10",
		metric: "productionCrafted",
		requiredLevel: 20,
		reward: { coins: 900, items: [{ productId: 7, quantity: 4 }] },
		title: "Linha aquecida",
	},
	{
		category: "production",
		description: "Produza 50 itens em setores especiais.",

		goal: 50,
		id: "crafted-50",
		metric: "productionCrafted",
		requiredLevel: 22,
		reward: { coins: 2_500, items: [{ productId: 5, quantity: 8 }] },
		title: "Produção eficiente",
	},
	{
		category: "production",
		description: "Fabrique 200 itens de alto valor.",

		goal: 200,
		id: "crafted-200",
		metric: "productionCrafted",
		requiredLevel: 27,
		reward: { coins: 7_500, items: [{ productId: 27, quantity: 5 }] },
		title: "Turno industrial",
	},
	{
		category: "production",
		description: "Fabrique 750 itens nos setores do mercado.",

		goal: 750,
		id: "crafted-750",
		metric: "productionCrafted",
		requiredLevel: 35,
		reward: { coins: 22_000, items: [{ productId: 45, quantity: 8 }] },
		title: "Mestre artesão",
	},
	{
		category: "inventory",
		description: "Mantenha 25 unidades guardadas no estoque.",

		goal: 25,
		id: "inventory-25",
		metric: "inventoryUnits",
		requiredLevel: 1,
		reward: { coins: 220 },
		title: "Despensa organizada",
	},
	{
		category: "inventory",
		description: "Acumule 75 unidades no estoque do mercado.",

		goal: 75,
		id: "inventory-75",
		metric: "inventoryUnits",
		requiredLevel: 3,
		reward: { coins: 800, items: [{ productId: 47, quantity: 6 }] },
		title: "Estoque seguro",
	},
	{
		category: "inventory",
		description: "Mantenha 200 unidades prontas para uso.",

		goal: 200,
		id: "inventory-200",
		metric: "inventoryUnits",
		requiredLevel: 8,
		reward: { coins: 3_000, items: [{ productId: 52, quantity: 8 }] },
		title: "Centro de distribuição",
	},
	{
		category: "inventory",
		description: "Guarde 20 unidades de farinha para a padaria.",

		goal: 20,
		id: "flour-stock-20",
		metric: "inventoryProduct",
		requiredLevel: 9,
		reward: { coins: 350, items: [{ productId: 5, quantity: 3 }] },
		targetProductId: 43,
		title: "Reserva da padaria",
	},
	{
		category: "inventory",
		description: "Mantenha 15 unidades de leite para a queijaria.",

		goal: 15,
		id: "milk-stock-15",
		metric: "inventoryProduct",
		requiredLevel: 6,
		reward: { coins: 900, items: [{ productId: 6, quantity: 3 }] },
		targetProductId: 5,
		title: "Leite selecionado",
	},
	{
		category: "management",
		description: "Faça sua primeira melhoria de capacidade.",

		goal: 1,
		id: "upgrades-1",
		metric: "shelfUpgrades",
		requiredLevel: 2,
		reward: { coins: 400 },
		title: "Primeira melhoria",
	},
	{
		category: "management",
		description: "Realize 5 melhorias nas prateleiras.",

		goal: 5,
		id: "upgrades-5",
		metric: "shelfUpgrades",
		requiredLevel: 6,
		reward: { coins: 1_800, items: [{ productId: 23, quantity: 5 }] },
		title: "Loja otimizada",
	},
	{
		category: "management",
		description: "Some 12 níveis de melhoria nas prateleiras.",

		goal: 12,
		id: "upgrades-12",
		metric: "shelfUpgrades",
		requiredLevel: 12,
		reward: { coins: 6_000, items: [{ productId: 18, quantity: 5 }] },
		title: "Estrutura premium",
	},
	...expansionMissions(),
];

// Missions of each expansion: one to grow into the next expansion and one about the shop itself. Rewards
// follow the price of the next expansion (about a tenth of it), so they matter at every stage.
function expansionMissions(): MissionDefinition[] {
	const steps: {
		era: MarketEraId;
		goal: { metric: MissionDefinition["metric"]; goal: number; title: string; description: string };
	}[] = [
		{ era: "mesinha", goal: { metric: "productLevels", goal: 1, title: "Produto caprichado", description: "Suba um produto para o nível 1 na tela Prateleiras." } },
		{ era: "tenda", goal: { metric: "unitsSold", goal: 60, title: "A tenda pegou", description: "Venda 60 unidades no total." } },
		{ era: "banca", goal: { metric: "productLevels", goal: 5, title: "Banca afinada", description: "Some 5 níveis de produto." } },
		{ era: "conteiner", goal: { metric: "customersServed", goal: 300, title: "Clientela fiel", description: "Atenda 300 clientes no total." } },
		{ era: "spati", goal: { metric: "productLevels", goal: 12, title: "O Späti da esquina", description: "Some 12 níveis de produto." } },
		{ era: "quitanda", goal: { metric: "unitsSold", goal: 1_500, title: "Freguesia do bairro", description: "Venda 1.500 unidades no total." } },
		{ era: "minimercado", goal: { metric: "revenue", goal: 150_000, title: "Caixa cheio", description: "Fature 150.000 moedas no total." } },
		{ era: "mercadinho", goal: { metric: "productLevels", goal: 30, title: "Mercadinho de respeito", description: "Some 30 níveis de produto." } },
		{ era: "supermercado", goal: { metric: "customersServed", goal: 3_000, title: "Super movimento", description: "Atenda 3.000 clientes no total." } },
		{ era: "hipermercado", goal: { metric: "revenue", goal: 2_000_000, title: "Gigante do varejo", description: "Fature 2 milhões de moedas no total." } },
	];
	return steps.flatMap(({ era, goal }) => {
		const current = getMarketEra(era);
		const next = getNextMarketEra(era);
		const reward = Math.max(100, Math.round(((next ?? current).coinCost * 0.1) / 50) * 50);
		const list: MissionDefinition[] = [
			{
				category: "progression",
				description: `Missão da expansão ${current.name}. ${goal.description}`,
				goal: goal.goal,
				id: `exp-${era}-shop`,
				metric: goal.metric,
				requiredLevel: 1,
				requiredEra: era,
				reward: { coins: Math.round(reward / 2 / 10) * 10 },
				title: goal.title,
			},
		];
		if (next)
			list.push({
				category: "progression",
				description: `Missão da expansão ${current.name}: evolua para ${next.name} na Loja, aba Expansões.`,
				goal: next.index,
				id: `exp-${era}-next`,
				metric: "expansion",
				requiredLevel: 1,
				requiredEra: era,
				reward: { coins: reward },
				title: `Próxima expansão: ${next.name}`,
			});
		return list;
	});
}

export function getMission(missionId: string) {
	return missions.find((mission) => mission.id === missionId);
}
