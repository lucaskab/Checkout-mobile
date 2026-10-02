import { expect, test } from "bun:test";
import { canShelfHold, getShelfKind } from "./shelf-categories";
import { initialShelfAssignments, itemCatalog, shelves } from "./market-products";
import { getFixtureName, getFixturesForCategory, sectorCounters, shelfTypes } from "./shelf-types";
import { getEraOrder, getUnlockedProductIds, starterShelfIds } from "./market-products";
import { productionSectors } from "./production-sectors";

test("each fixture only holds its own kind of goods", () => {
	expect(getShelfKind("drinks")).toBe("fridge");
	expect(getShelfKind("pizza")).toBe("freezer");
	expect(getShelfKind("icecream")).toBe("freezer");
	expect(getShelfKind("produce")).toBe("shelf");
	expect(getShelfKind("sector-acougue")).toBe("counter");
	// Produce stand: fruit and vegetables only.
	expect(canShelfHold("produce", "hortifruti").ok).toBe(true);
	expect(canShelfHold("produce", "laticinios").ok).toBe(false);
	// Upright cooler: drinks only.
	expect(canShelfHold("drinks", "bebidas").ok).toBe(true);
	expect(canShelfHold("drinks", "alcoolicos").ok).toBe(true);
	expect(canShelfHold("drinks", "laticinios").ok).toBe(false);
	// Chest freezer: ice cream only; the frozen-food freezer: frozen food only.
	expect(canShelfHold("icecream", "sorvetes").ok).toBe(true);
	expect(canShelfHold("icecream", "congelados").ok).toBe(false);
	expect(canShelfHold("pizza", "congelados").ok).toBe(true);
	expect(canShelfHold("pizza", "sorvetes").ok).toBe(false);
	// Meat and fish only at their counters.
	expect(canShelfHold("sector-acougue", "carnes").ok).toBe(true);
	expect(canShelfHold("dairy", "carnes").ok).toBe(false);
	expect(canShelfHold("drinks", "hortifruti").reason).toContain("Geladeira de bebidas");
	expect(shelves.find((shelf) => shelf.id === "pizza")?.name).toBe("Freezer de congelados");
});

test("every product has somewhere to be sold, and every sector counter sells what its sector makes", () => {
	for (const product of itemCatalog) expect(getFixturesForCategory(product.category).length).toBeGreaterThan(0);
	for (const counter of sectorCounters) expect(counter.categories.length).toBeGreaterThan(0);
});

test("a new game's products already sit on shelves that can hold them", () => {
	for (const [shelfId, productId] of Object.entries(initialShelfAssignments)) {
		if (productId == null) continue;
		const product = itemCatalog.find((item) => item.id === productId);
		expect(canShelfHold(shelfId, product.category).ok).toBe(true);
	}
});

test("the sidewalk table starts with the crates and the styrofoam cooler only", () => {
	expect(starterShelfIds).toEqual(["produce", "drinks"]);
	expect(getFixtureName("drinks", "mesinha")).toBe("Isopor com gelo");
	expect(getFixtureName("drinks", "conteiner")).toBe("Geladeira de bebidas");
	expect(getFixtureName("produce", "tenda")).toBe("Caixotes de hortifrúti");
	const names = getUnlockedProductIds(99, "mesinha").map((id) => itemCatalog.find((p) => p.id === id).name);
	expect(names.sort()).toEqual(["Alface", "Banana", "Refrigerante", "Tomate", "Água mineral"].sort());
});

test("no product opens before a fixture of its expansion can hold it", () => {
	for (const product of itemCatalog) {
		const era = getEraOrder(product.unlockEra);
		const shelf = shelfTypes.some(
			(item) => item.categories.includes(product.category) && getEraOrder(item.eraId) <= era,
		);
		const counter = sectorCounters.some(
			(item) =>
				item.categories.includes(product.category) &&
				getEraOrder(productionSectors.find((sector) => sector.id === item.sectorId).eraId) <= era,
		);
		expect({ product: product.name, sellable: shelf || counter }).toEqual({ product: product.name, sellable: true });
	}
});
