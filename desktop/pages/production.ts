import type {
	ProductionJob,
	ProductionRecipe,
	ProductionSector,
} from "@/@types/production";
import { getProductionSectorProductId } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import {
	getProductionSector,
	getSectorRecipes,
	productionSectors,
} from "@/data/production-sectors";
import { getActiveGameEventEffects } from "@/services/game-events";
import {
	getProductionDiamondCost,
	getProductionEconomy,
	getProductionProgress,
	getProductionRemainingTime,
	getRecipeProfitMargin,
} from "@/services/production";
import {
	act,
	type Card,
	card,
	fmt,
	gameIcon,
	go,
	page,
	productIcon,
	type State,
	swap,
} from "../view-kit";
import type { Routes } from ".";

// Mirrors src/screens/sectors (list) and src/screens/sector-detail (recipes + slots).

const productName = (id: number) =>
	itemCatalog.find((item) => item.id === id)?.name ?? `Produto ${id}`;

// Same copy as getAmbientCopy in sector-detail/index.tsx.
function getAmbientCopy(sectorId: ProductionSector["id"]) {
	switch (sectorId) {
		case "padaria":
			return "Fornos aquecidos · farinha fresca";
		case "queijaria":
			return "Câmara maturando · leite selecionado";
		case "acougue":
			return "Bancada preparada · defumador ativo";
		case "peixaria":
			return "Balcão a 2°C · frescor garantido";
		case "bebidas":
			return "Refrigerador ligado · bebidas fresquinhas";
		case "sorvetes":
			return "Freezer a -18°C · sobremesas geladas";
	}
}

function sectorsPage(state: State) {
	const level = state.market.level;
	const jobs = state.production.jobs;
	const unlocked = productionSectors.filter(
		(sector) => level >= sector.requiredLevel,
	).length;

	const hero = card("Setores especiais", {
		eyebrow: "CENTRAL DE PRODUÇÃO",
		icon: gameIcon("conveyor"),
		subtitle:
			"Transforme produtos básicos em itens exclusivos, mais lucrativos e valiosos.",
		lines: [
			`${unlocked}/${productionSectors.length} setores liberados`,
			`${jobs.length} em produção`,
			`${fmt(state.production.totalCrafted)} itens fabricados`,
		],
		tone: "info",
	});

	const sectorCards = productionSectors.map((sector) => {
		const isLocked = level < sector.requiredLevel;
		const activeJobs = jobs.filter((job) => job.sectorId === sector.id).length;
		return card(sector.name, {
			eyebrow: sector.subtitle,
			subtitle: sector.description,
			icon: productIcon(getProductionSectorProductId(sector.id)),
			badge: isLocked ? `Nível ${sector.requiredLevel}` : `${sector.slotCount} slots`,
			tone: isLocked ? "locked" : activeJobs > 0 ? "success" : "",
			lines: [
				`${
					isLocked
						? "Setor bloqueado"
						: activeJobs > 0
							? `${activeJobs} produção(ões) ativa(s)`
							: "Pronto para produzir"
				} · ${sector.slotCount} slots`,
			],
			buttons: [
				go("Abrir", `sector:${sector.id}`, {
					enabled: !isLocked,
					variant: "primary",
					fail: isLocked ? `Nível ${sector.requiredLevel}` : "",
				}),
			],
		});
	});

	return page("sectors", "Produção", [hero, ...sectorCards], {
		subtitle: "Seu mercado, suas receitas",
		icon: gameIcon("market"),
	});
}

function slotCard(
	state: State,
	slotIndex: number,
	job: ProductionJob | undefined,
	now: number,
): Card {
	if (!job) {
		return card(`Slot ${slotIndex + 1}`, {
			eyebrow: "LINHA DE PRODUÇÃO",
			subtitle: "Escolha uma receita abaixo",
			icon: gameIcon("conveyor"),
			badge: "Livre",
		});
	}
	const progress = getProductionProgress(job, now);
	const diamondCost = getProductionDiamondCost(job.endsAt - now);
	const canAfford = state.logistics.premiumCurrency >= diamondCost;
	return card(productName(job.outputProductId), {
		eyebrow: `SLOT ${slotIndex + 1}`,
		icon: productIcon(job.outputProductId),
		badge: `${Math.round(progress * 100)}%`,
		tone: progress >= 1 ? "success" : "info",
		lines: [
			`Pronto em ${getProductionRemainingTime(job.endsAt, now)}`,
			`Rende ${job.outputQuantity} unid.`,
		],
		progress,
		buttons: [
			act(`Finalizar agora · ${diamondCost}`, "finishProductionNow", [job.id], {
				variant: "gem",
				icon: gameIcon("diamond"),
				enabled: canAfford,
				ok: `Produção concluída agora por ${diamondCost} diamantes.`,
				fail: "Você não possui diamantes suficientes.",
			}),
		],
	});
}

function recipeCard(
	state: State,
	sector: ProductionSector,
	recipe: ProductionRecipe,
	hasFreeSlot: boolean,
	durationMultiplier: number,
): Card {
	const inventory = state.inventory;
	const name = productName(recipe.outputProductId);
	const product = itemCatalog.find((item) => item.id === recipe.outputProductId);
	const isLocked = state.market.level < recipe.requiredLevel;
	const hasIngredients = recipe.ingredients.every(
		(ingredient) => (inventory[ingredient.productId] ?? 0) >= ingredient.quantity,
	);
	const margin = getRecipeProfitMargin(recipe);
	const economy = getProductionEconomy(recipe);
	const now = Date.now();
	const duration = getProductionRemainingTime(
		now + recipe.durationMs * durationMultiplier,
		now,
	);
	const canProduce = !isLocked && hasIngredients && hasFreeSlot;
	const label = isLocked
		? `Libera no nível ${recipe.requiredLevel}`
		: !hasFreeSlot
			? "Slots ocupados"
			: !hasIngredients
				? "Ingredientes insuficientes"
				: `Fabricar ${recipe.outputQuantity} agora`;

	return card(name, {
		eyebrow: "RECEITA",
		subtitle: `Rende ${recipe.outputQuantity} unid. · ${duration}`,
		icon: productIcon(recipe.outputProductId),
		badge: isLocked ? `Nível ${recipe.requiredLevel}` : `x${recipe.outputQuantity}`,
		tone: isLocked ? "locked" : canProduce ? "success" : hasIngredients ? "" : "warning",
		lines: [
			`Margem +${margin}% · ${product?.xpPerSale ?? 0} XP/venda · Venda ${product?.sellingPrice ?? 0}`,
			`Custo/unid. ${Math.ceil(economy.productionUnitCost)} fabricando → fornecedor ${economy.supplierUnitPrice} (−${economy.savingsPercent}%)`,
			"INGREDIENTES",
			...recipe.ingredients.map((ingredient) => {
				const owned = inventory[ingredient.productId] ?? 0;
				const enough = owned >= ingredient.quantity;
				return `${enough ? "✓" : "✗"} ${ingredient.quantity}× ${productName(ingredient.productId)} · tem ${fmt(owned)}`;
			}),
		],
		buttons: [
			act(label, "startProduction", [{ recipeId: recipe.id, sectorId: sector.id }], {
				variant: "success",
				enabled: canProduce,
				ok: `${name} entrou na linha de produção.`,
				fail: hasFreeSlot
					? "Faltam ingredientes ou nível para iniciar esta receita."
					: "Todos os slots deste setor estão ocupados.",
			}),
		],
	});
}

function sectorPage(state: State, sectorId: string) {
	const route = `sector:${sectorId}`;
	const sector = getProductionSector(sectorId);
	if (!sector) {
		return page(route, "Setor não encontrado", [
			card("Setor não encontrado", {
				icon: gameIcon("construction"),
				buttons: [go("Voltar aos setores", "sectors")],
			}),
		]);
	}

	const now = Date.now();
	const level = state.market.level;
	const eventEffects = getActiveGameEventEffects(state.events);
	const recipes = getSectorRecipes(sector.id);
	const sectorJobs = state.production.jobs.filter((job) => job.sectorId === sector.id);
	const hasFreeSlot = sectorJobs.length < sector.slotCount;

	const hero = card(sector.name, {
		eyebrow: "SETOR ESPECIAL",
		subtitle: sector.description,
		icon: productIcon(getProductionSectorProductId(sector.id)),
		badge: `Nível ${sector.requiredLevel}+`,
		tone: level < sector.requiredLevel ? "locked" : "info",
		lines: [
			getAmbientCopy(sector.id),
			`Linha de produção: ${sectorJobs.length}/${sector.slotCount} ativos`,
			"Produções continuam mesmo fora desta tela.",
			`Diamantes: ${fmt(state.logistics.premiumCurrency)}`,
		],
	});

	const slots = Array.from({ length: sector.slotCount }, (_, slotIndex) =>
		slotCard(
			state,
			slotIndex,
			sectorJobs.find((job) => job.slotIndex === slotIndex),
			now,
		),
	);

	const recipeCards = recipes.map((recipe) =>
		recipeCard(
			state,
			sector,
			recipe,
			hasFreeSlot,
			eventEffects.productionDurationMultiplier,
		),
	);

	// Quick switch between sectors (the RN list only opens unlocked ones).
	const chips = productionSectors.map((item) => {
		const locked = level < item.requiredLevel;
		return {
			...swap(item.name, `sector:${item.id}`, item.id === sector.id),
			enabled: !locked,
			fail: locked ? `Nível ${item.requiredLevel}` : "",
		};
	});

	return page(route, sector.name, [hero, ...slots, ...recipeCards], {
		subtitle: `Receitas do setor · ${recipes.length}`,
		icon: productIcon(getProductionSectorProductId(sector.id)),
		chips,
	});
}

export const routes: Routes = {
	sectors: (state) => sectorsPage(state),
	sector: (state, [sectorId = ""]) => sectorPage(state, sectorId),
};
