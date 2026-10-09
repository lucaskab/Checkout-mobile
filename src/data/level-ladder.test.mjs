import { expect, test } from "bun:test";
import { achievements } from "./achievements.ts";
import { itemCatalog } from "./market-products.ts";
import { missions } from "./missions.ts";
import { productionRecipes, productionSectors } from "./production-sectors.ts";
import { getLevelUnlocks } from "../services/level-unlocks.ts";

// Every level is a reward (scripts/economy/catalog.py SCHEDULE): something to sell, build, buy or place.
const LAST_LADDER_LEVEL = 52;
const content = ["product", "recipe", "sector", "shelf", "employee", "shop", "decor"];
const productLevel = (id) => itemCatalog.find((product) => product.id === id).unlockLevel;

test("every level up to the end of the ladder opens something new", () => {
	for (let level = 2; level <= LAST_LADDER_LEVEL; level++) {
		const opened = getLevelUnlocks(level - 1, level, "rede").filter((unlock) => content.includes(unlock.kind));
		expect({ level, opened: opened.length > 0 }).toEqual({ level, opened: true });
	}
});

test("on the sidewalk table the first levels open things that can be used right away", () => {
	for (let level = 2; level <= 8; level++) {
		const now = getLevelUnlocks(level - 1, level, "mesinha").filter(
			(unlock) => !unlock.waitingEra && content.includes(unlock.kind),
		);
		expect({ level, usable: now.length > 0 }).toEqual({ level, usable: true });
	}
	// Potato, carrot, apple and eggs fit the crates: they open by level, not with the tent.
	const atThree = getLevelUnlocks(1, 3, "mesinha").filter((unlock) => unlock.kind === "product" && !unlock.waitingEra);
	expect(atThree.map((unlock) => unlock.name).sort()).toEqual(["Batata", "Cenoura", "Maçã", "Ovos"]);
});

test("products open one to three per level, not in heaps", () => {
	const perLevel = {};
	for (const product of itemCatalog)
		if (product.acquisition !== "production" && product.unlockLevel > 1)
			perLevel[product.unlockLevel] = (perLevel[product.unlockLevel] ?? 0) + 1;
	expect(Math.max(...Object.values(perLevel))).toBeLessThanOrEqual(3);
});

test("recipes only use what is already open, and a sector is there by its first recipe", () => {
	for (const recipe of productionRecipes) {
		expect(productLevel(recipe.outputProductId)).toBe(recipe.requiredLevel);
		for (const ingredient of recipe.ingredients)
			expect({ recipe: recipe.id, early: productLevel(ingredient.productId) <= recipe.requiredLevel }).toEqual({
				recipe: recipe.id,
				early: true,
			});
	}
	for (const sector of productionSectors) {
		const first = Math.min(...productionRecipes.filter((r) => r.sectorId === sector.id).map((r) => r.requiredLevel));
		// The butcher's and the fishmonger's open with the fresh meat and fish they alone sell, a little earlier.
		expect({ sector: sector.id, ok: sector.requiredLevel <= first && sector.requiredLevel >= first - 3 }).toEqual({
			sector: sector.id,
			ok: true,
		});
	}
});

test("missions and achievements never ask for or give a product before its level", () => {
	for (const mission of missions) {
		const reachable = mission.metric === "level" ? mission.goal : mission.requiredLevel;
		if (mission.targetProductId)
			expect({ id: mission.id, ok: productLevel(mission.targetProductId) <= mission.requiredLevel }).toEqual({
				id: mission.id,
				ok: true,
			});
		for (const item of mission.reward.items ?? [])
			expect({ id: mission.id, ok: productLevel(item.productId) <= reachable }).toEqual({ id: mission.id, ok: true });
	}
	for (const achievement of achievements)
		if (achievement.targetProductId)
			expect({ id: achievement.id, ok: productLevel(achievement.targetProductId) <= achievement.requiredLevel }).toEqual({
				id: achievement.id,
				ok: true,
			});
});
