import type {
	AchievementDefinition,
	AchievementRarity,
} from "@/@types/achievement";

type AchievementInput = Omit<AchievementDefinition, "thresholds"> & {
	thresholds: number[];
};

function defineAchievement(input: AchievementInput): AchievementDefinition {
	if (input.thresholds.length !== 5) {
		throw new Error(`Achievement ${input.id} precisa ter exatamente 5 níveis.`);
	}

	return {
		...input,
		thresholds: input.thresholds as AchievementDefinition["thresholds"],
	};
}

const salesMilestones = [10, 100, 1_000, 10_000, 100_000];
const specialistMilestones = [5, 25, 100, 500, 2_500];
const rareSpecialistMilestones = [1, 10, 50, 250, 1_000];

export const achievements: AchievementDefinition[] = [
	defineAchievement({
		category: "progression",
		description:
			"Evolua o mercado e transforme uma pequena loja em um império.",

		id: "market-level",
		metric: "level",
		rarity: "legendary",
		requiredLevel: 1,
		thresholds: [2, 5, 10, 20, 35],
		title: "Império varejista",
	}),
	defineAchievement({
		category: "progression",
		description: "Acumule experiência administrando cada detalhe da operação.",

		id: "total-experience",
		metric: "experience",
		rarity: "epic",
		requiredLevel: 1,
		thresholds: [100, 1_000, 5_000, 25_000, 100_000],
		title: "Administrador experiente",
	}),
	defineAchievement({
		category: "collection",
		description: "Desbloqueie novos produtos e complete o catálogo do mercado.",

		id: "products-unlocked",
		metric: "productsUnlocked",
		rarity: "epic",
		requiredLevel: 1,
		thresholds: [5, 15, 30, 50, 70],
		title: "Catálogo sem fim",
	}),
	defineAchievement({
		category: "progression",
		description: "Conclua missões e prove que nenhum objetivo fica para trás.",

		id: "missions-claimed",
		metric: "missionsClaimed",
		rarity: "rare",
		requiredLevel: 1,
		thresholds: [3, 10, 25, 50, 80],
		title: "Incansável",
	}),
	defineAchievement({
		category: "management",
		description:
			"Melhore as gôndolas para comportar operações cada vez maiores.",

		id: "shelf-upgrades",
		metric: "shelfUpgrades",
		rarity: "rare",
		requiredLevel: 2,
		thresholds: [1, 5, 12, 25, 50],
		title: "Mestre das gôndolas",
	}),
	defineAchievement({
		category: "sales",
		description: "Venda unidades de qualquer produto aos clientes do mercado.",

		id: "units-sold",
		metric: "unitsSold",
		rarity: "legendary",
		requiredLevel: 1,
		thresholds: salesMilestones,
		title: "Máquina de vendas",
	}),
	defineAchievement({
		category: "sales",
		description: "Faça o caixa crescer com faturamento acumulado em vendas.",

		id: "total-revenue",
		metric: "revenue",
		rarity: "legendary",
		requiredLevel: 1,
		thresholds: [1_000, 10_000, 100_000, 1_000_000, 10_000_000],
		title: "Cofres cheios",
	}),
	defineAchievement({
		category: "collection",
		description: "Venda produtos diferentes e mostre a força do seu catálogo.",

		id: "unique-products-sold",
		metric: "uniqueProductsSold",
		rarity: "epic",
		requiredLevel: 2,
		thresholds: [3, 10, 25, 50, 75],
		title: "Tem de tudo",
	}),
	defineAchievement({
		category: "customers",
		description:
			"Receba visitantes e faça o mercado virar referência no bairro.",

		id: "customers-served",
		metric: "customersServed",
		rarity: "legendary",
		requiredLevel: 1,
		thresholds: [10, 100, 1_000, 10_000, 100_000],
		title: "Casa cheia",
	}),
	defineAchievement({
		category: "customers",
		description:
			"Faça clientes encontrarem o que precisam e concluírem a compra.",

		id: "customers-converted",
		metric: "customersWhoBought",
		rarity: "legendary",
		requiredLevel: 1,
		thresholds: [5, 75, 750, 7_500, 75_000],
		title: "Clientes fiéis",
	}),
	defineAchievement({
		category: "production",
		description: "Fabrique produtos especiais dentro dos setores do mercado.",

		id: "items-crafted",
		metric: "productionCrafted",
		rarity: "legendary",
		requiredLevel: 3,
		thresholds: [1, 25, 250, 2_500, 25_000],
		title: "Produção imparável",
	}),
	defineAchievement({
		category: "production",
		description:
			"Inicie ciclos de fabricação e mantenha todos os setores ocupados.",

		id: "production-jobs",
		metric: "productionJobsStarted",
		rarity: "epic",
		requiredLevel: 3,
		thresholds: [1, 20, 150, 1_000, 10_000],
		title: "Turno completo",
	}),
	defineAchievement({
		category: "logistics",
		description: "Faça pedidos aos fornecedores para sustentar o crescimento.",

		id: "supplier-orders",
		metric: "supplierOrdersPlaced",
		rarity: "epic",
		requiredLevel: 1,
		thresholds: [1, 10, 50, 250, 1_000],
		title: "Rei da logística",
	}),
	defineAchievement({
		category: "management",
		description:
			"Reponha produtos nas gôndolas antes que os clientes percebam.",

		id: "restocked-units",
		metric: "restockedUnits",
		rarity: "legendary",
		requiredLevel: 1,
		thresholds: [10, 100, 1_000, 10_000, 100_000],
		title: "Nunca falta",
	}),
	defineAchievement({
		category: "management",
		description: "Ajuste preços para equilibrar margem, demanda e experiência.",

		id: "price-changes",
		metric: "priceChanges",
		rarity: "rare",
		requiredLevel: 2,
		thresholds: [1, 10, 50, 250, 1_000],
		title: "Estrategista de preços",
	}),
	defineAchievement({
		category: "management",
		description:
			"Abra o mercado em novos turnos e mantenha a operação constante.",

		id: "market-openings",
		metric: "marketOpenings",
		rarity: "rare",
		requiredLevel: 1,
		thresholds: [1, 10, 50, 250, 1_000],
		title: "Primeiro a chegar",
	}),
	defineAchievement({
		category: "collection",
		description: "Adquira melhorias e itens especiais na loja premium.",

		id: "shop-purchases",
		metric: "shopPurchases",
		rarity: "epic",
		requiredLevel: 2,
		thresholds: [1, 5, 15, 50, 150],
		title: "Colecionador de melhorias",
	}),
	defineAchievement({
		category: "logistics",
		description:
			"Use recursos de emergência para receber entregas imediatamente.",

		id: "instant-deliveries",
		metric: "instantDeliveries",
		rarity: "rare",
		requiredLevel: 2,
		thresholds: [1, 5, 25, 100, 500],
		title: "Sem tempo a perder",
	}),
	defineAchievement({
		category: "production",
		description: "Finalize fabricações na hora quando cada segundo importa.",

		id: "instant-production",
		metric: "instantProductionFinishes",
		rarity: "rare",
		requiredLevel: 3,
		thresholds: [1, 5, 25, 100, 500],
		title: "Produção relâmpago",
	}),
	defineAchievement({
		category: "specialist",
		description: "Venda tomates frescos e domine o começo de toda boa feira.",

		id: "tomato-specialist",
		metric: "soldProduct",
		rarity: "common",
		requiredLevel: 1,
		targetProductId: 1,
		thresholds: specialistMilestones,
		title: "Rei do tomate",
	}),
	defineAchievement({
		category: "specialist",
		description: "Faça do leite integral um clássico indispensável do mercado.",

		id: "milk-specialist",
		metric: "soldProduct",
		rarity: "common",
		requiredLevel: 1,
		targetProductId: 5,
		thresholds: specialistMilestones,
		title: "Rota do leite",
	}),
	defineAchievement({
		category: "specialist",
		description: "Espalhe o cheiro de pão francês por todos os corredores.",

		id: "bread-specialist",
		metric: "soldProduct",
		rarity: "uncommon",
		requiredLevel: 1,
		targetProductId: 9,
		thresholds: specialistMilestones,
		title: "Pão de cada dia",
	}),
	defineAchievement({
		category: "specialist",
		description: "Venda sucos naturais e refresque uma multidão de clientes.",

		id: "juice-specialist",
		metric: "soldProduct",
		rarity: "uncommon",
		requiredLevel: 2,
		targetProductId: 13,
		thresholds: specialistMilestones,
		title: "Refresco da casa",
	}),
	defineAchievement({
		category: "specialist",
		description: "Transforme café especial no combustível oficial do bairro.",

		id: "coffee-specialist",
		metric: "soldProduct",
		rarity: "rare",
		requiredLevel: 4,
		targetProductId: 15,
		thresholds: specialistMilestones,
		title: "Barista do bairro",
	}),
	defineAchievement({
		category: "specialist",
		description:
			"Venda pizzas congeladas suficientes para alimentar uma cidade.",

		id: "pizza-specialist",
		metric: "soldProduct",
		rarity: "uncommon",
		requiredLevel: 4,
		targetProductId: 17,
		thresholds: specialistMilestones,
		title: "Noite da pizza",
	}),
	defineAchievement({
		category: "specialist",
		description: "Abasteça clientes que precisam de energia para seguir o dia.",

		id: "energy-specialist",
		metric: "soldProduct",
		rarity: "rare",
		requiredLevel: 5,
		targetProductId: 22,
		thresholds: specialistMilestones,
		title: "Carga máxima",
	}),
	defineAchievement({
		category: "specialist",
		description:
			"Venda chocolates premium e conquiste os clientes mais exigentes.",

		id: "chocolate-specialist",
		metric: "soldProduct",
		rarity: "rare",
		requiredLevel: 6,
		targetProductId: 24,
		thresholds: specialistMilestones,
		title: "Mestre chocolatier",
	}),
	defineAchievement({
		category: "specialist",
		description: "Leve macarrão italiano para mesas em toda a vizinhança.",

		id: "pasta-specialist",
		metric: "soldProduct",
		rarity: "rare",
		requiredLevel: 7,
		targetProductId: 26,
		thresholds: specialistMilestones,
		title: "La dolce venda",
	}),
	defineAchievement({
		category: "specialist",
		description: "Venda cortes nobres e seja reconhecido pelo melhor açougue.",

		id: "meat-specialist",
		metric: "soldProduct",
		rarity: "epic",
		requiredLevel: 8,
		targetProductId: 27,
		thresholds: rareSpecialistMilestones,
		title: "Corte perfeito",
	}),
	defineAchievement({
		category: "specialist",
		description:
			"Venda cestas orgânicas para clientes que valorizam qualidade.",

		id: "organic-specialist",
		metric: "soldProduct",
		rarity: "epic",
		requiredLevel: 9,
		targetProductId: 29,
		thresholds: rareSpecialistMilestones,
		title: "Mercado sustentável",
	}),
	defineAchievement({
		category: "specialist",
		description: "Monte uma adega respeitada vendendo vinhos importados.",

		id: "wine-specialist",
		metric: "soldProduct",
		rarity: "epic",
		requiredLevel: 12,
		targetProductId: 31,
		thresholds: rareSpecialistMilestones,
		title: "Sommelier do varejo",
	}),
	defineAchievement({
		category: "specialist",
		description:
			"Venda champanhes reserva para as celebrações mais exclusivas.",

		id: "champagne-specialist",
		metric: "soldProduct",
		rarity: "legendary",
		requiredLevel: 18,
		targetProductId: 33,
		thresholds: [1, 5, 20, 75, 250],
		title: "Brinde lendário",
	}),
	defineAchievement({
		category: "specialist",
		description: "Faça a peixaria ganhar fama vendendo peixe sempre fresco.",

		id: "fish-specialist",
		metric: "soldProduct",
		rarity: "epic",
		requiredLevel: 10,
		targetProductId: 44,
		thresholds: rareSpecialistMilestones,
		title: "Tesouro do mar",
	}),
	defineAchievement({
		category: "specialist",
		description:
			"Fabrique e venda baguetes rústicas dignas de uma grande padaria.",

		id: "baguette-specialist",
		metric: "soldProduct",
		rarity: "legendary",
		requiredLevel: 6,
		targetProductId: 101,
		thresholds: [1, 10, 50, 200, 750],
		title: "Forno lendário",
	}),
	defineAchievement({
		category: "specialist",
		description: "Venda tábuas de queijo que nenhum cliente consegue esquecer.",

		id: "cheese-specialist",
		metric: "soldProduct",
		rarity: "legendary",
		requiredLevel: 10,
		targetProductId: 106,
		thresholds: [1, 10, 50, 200, 750],
		title: "Afinador de queijos",
	}),
	defineAchievement({
		category: "specialist",
		description: "Produza e venda sushi especial em escala de restaurante.",

		id: "sushi-specialist",
		metric: "soldProduct",
		rarity: "legendary",
		requiredLevel: 16,
		targetProductId: 111,
		thresholds: [1, 5, 25, 100, 500],
		title: "Sushiman secreto",
	}),
];

export const achievementRarityOrder: Record<AchievementRarity, number> = {
	common: 1,
	uncommon: 2,
	rare: 3,
	epic: 4,
	legendary: 5,
};
