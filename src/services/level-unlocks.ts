import type { MarketEraId } from "@/@types/economy";
import type { ItemDefinition } from "@/@types/item";
import { achievements } from "@/data/achievements";
import { getMarketEra } from "@/data/economy";
import { employeeDefinitions, isEmployeeEraReached } from "@/data/employees";
import { interiorDecor } from "@/data/interior-decor";
import { getEraOrder, itemCatalog, itemCategories } from "@/data/market-products";
import { missions } from "@/data/missions";
import { productionRecipes, productionSectors } from "@/data/production-sectors";
import { shelfCapacityUpgrades, shelfSlotUpgrades } from "@/data/shelf-capacity";
import { shopItems } from "@/data/shop-items";

// Everything a level opens, for the level-up celebration: levels in (from, to], read from the same tables
// that lock them in the game. Things that also need a bigger market come apart ("waiting"), so the player
// knows what they unlocked now and what is already theirs as soon as the market grows.

export type LevelUnlockKind =
	| "product"
	| "sector"
	| "recipe"
	| "shelf"
	| "employee"
	| "shop"
	| "decor"
	| "mission"
	| "achievement";

export type LevelUnlock = {
	kind: LevelUnlockKind;
	id: string;
	name: string;
	detail: string;
	level: number;
	/** Product shown as the picture (products, recipes, sectors). */
	productId?: number;
	/** Opens only with this expansion (not reached yet). */
	waitingEra?: MarketEraId;
};

const categoryLabel = (id: string) => itemCategories.find((category) => category.id === id)?.label ?? id;
const coins = (value: number) => Math.round(value).toLocaleString("pt-BR");

export function getLevelUnlocks(from: number, to: number, eraId: MarketEraId): LevelUnlock[] {
	const inRange = (level: number) => level > from && level <= to;
	const era = getEraOrder(eraId);
	const reached = (id: MarketEraId | undefined) => !id || getEraOrder(id) <= era;
	const unlocks: LevelUnlock[] = [];

	for (const product of itemCatalog) {
		if (!inRange(product.unlockLevel) || product.acquisition === "production") continue;
		unlocks.push({
			kind: "product",
			id: String(product.id),
			name: product.name,
			detail: `${categoryLabel(product.category)} · compra ${coins(product.purchasePrice)}, vende ${coins(product.sellingPrice)}`,
			level: product.unlockLevel,
			productId: product.id,
			waitingEra: reached(product.unlockEra) ? undefined : product.unlockEra,
		});
	}
	for (const sector of productionSectors) {
		if (!inRange(sector.requiredLevel)) continue;
		unlocks.push({
			kind: "sector",
			id: sector.id,
			name: sector.name,
			detail: sector.subtitle,
			level: sector.requiredLevel,
			waitingEra: reached(sector.eraId) ? undefined : sector.eraId,
		});
	}
	for (const recipe of productionRecipes) {
		if (!inRange(recipe.requiredLevel)) continue;
		const output = itemCatalog.find((item) => item.id === recipe.outputProductId);
		const sector = productionSectors.find((item) => item.id === recipe.sectorId);
		unlocks.push({
			kind: "recipe",
			id: recipe.id,
			name: output?.name ?? recipe.id,
			detail: `Receita da ${sector?.name ?? "produção"} · rende ${recipe.outputQuantity} · dá para fazer à mão`,
			level: recipe.requiredLevel,
			productId: recipe.outputProductId,
			waitingEra: sector && !reached(sector.eraId) ? sector.eraId : undefined,
		});
	}
	// Shelf upgrades bought in Prateleiras: more products per shelf, more units per product.
	for (const upgrade of shelfSlotUpgrades) {
		if (!inRange(upgrade.playerLevel)) continue;
		unlocks.push({
			kind: "shelf",
			id: `slots-${upgrade.unlockedSlots}`,
			name: `Prateleira com ${upgrade.unlockedSlots} espaços`,
			detail: `Cada prateleira pode expor ${upgrade.unlockedSlots} produtos · ${coins(upgrade.coinCost)} moedas`,
			level: upgrade.playerLevel,
		});
	}
	for (const upgrade of shelfCapacityUpgrades) {
		if (upgrade.playerLevel <= 1 || !inRange(upgrade.playerLevel)) continue;
		unlocks.push({
			kind: "shelf",
			id: `capacity-${upgrade.capacity}`,
			name: `Prateleira para ${upgrade.capacity} unidades`,
			detail: `Cada produto da prateleira cabe até ${upgrade.capacity} unidades · ${coins(upgrade.coinCost)} moedas`,
			level: upgrade.playerLevel,
		});
	}
	for (const employee of employeeDefinitions) {
		if (!inRange(employee.level)) continue;
		unlocks.push({
			kind: "employee",
			id: employee.id,
			name: employee.name,
			detail: employee.description,
			level: employee.level,
			waitingEra: isEmployeeEraReached(employee, eraId) ? undefined : employee.requiredEra,
		});
	}
	for (const item of shopItems) {
		if (!inRange(item.level)) continue;
		unlocks.push({ kind: "shop", id: item.id, name: item.name, detail: item.description, level: item.level });
	}
	for (const decor of interiorDecor) {
		if (!inRange(decor.requiredLevel)) continue;
		unlocks.push({
			kind: "decor",
			id: decor.id,
			name: decor.name,
			detail: `${decor.zone === "outside" ? "Praça" : "Dentro da loja"} · ${decor.description}`,
			level: decor.requiredLevel,
		});
	}
	for (const mission of missions) {
		if (!inRange(mission.requiredLevel) || !reached(mission.requiredEra)) continue;
		unlocks.push({ kind: "mission", id: mission.id, name: mission.title, detail: mission.description, level: mission.requiredLevel });
	}
	for (const achievement of achievements) {
		if (!inRange(achievement.requiredLevel)) continue;
		unlocks.push({
			kind: "achievement",
			id: achievement.id,
			name: achievement.title,
			detail: achievement.description,
			level: achievement.requiredLevel,
		});
	}
	return unlocks;
}

/** The first level above `level` that opens something, and what it opens (for "next up"). */
export function getNextLevelUnlocks(level: number, eraId: MarketEraId, lookahead = 30) {
	for (let next = level + 1; next <= level + lookahead; next++) {
		const unlocks = getLevelUnlocks(next - 1, next, eraId).filter((unlock) => !unlock.waitingEra);
		if (unlocks.length) return { level: next, unlocks };
	}
	return null;
}

export const eraName = (id: MarketEraId) => getMarketEra(id).name;

/**
 * Why a product is still locked, for the "Próximos" lists: the level it opens at and, when the market does
 * not have the fixture that holds it yet, the expansion that brings it.
 */
export function describeProductLock(product: ItemDefinition, level: number, eraId: MarketEraId) {
	const levelsLeft = Math.max(0, product.unlockLevel - level);
	const eraMissing = getEraOrder(product.unlockEra) > getEraOrder(eraId);
	const era = getMarketEra(product.unlockEra).name;
	const where = product.acquisition === "production" ? " Feito na produção do mercado." : "";
	return {
		levelsLeft,
		/** Expansion still to open (null when the market already has it). */
		eraMissing: eraMissing ? era : null,
		progress: levelsLeft === 0 && eraMissing ? "Falta a expansão" : levelsLeft > 0 ? levelsLeft === 1 ? "Falta 1 nível" : `Faltam ${levelsLeft} níveis` : "Quase lá",
		detail:
			(levelsLeft === 0 && eraMissing
				? `O nível já liberou. Chega quando você abrir ${era} (Loja › Expansões), que traz o móvel para vender.`
				: eraMissing
					? `Chega no nível ${product.unlockLevel}, depois de abrir ${era} (Loja › Expansões).`
					: `Chega no nível ${product.unlockLevel}.`) + where,
	};
}
