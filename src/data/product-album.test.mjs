import { expect, test } from "bun:test";
import { albumCollections, getCollectionProgress, SALES_TO_COLLECT } from "./product-album";
import { itemCatalog } from "./market-products";

test("every product belongs to exactly one album collection", () => {
	const ids = albumCollections.flatMap((collection) => collection.productIds);
	expect(new Set(ids).size).toBe(ids.length);
	expect(ids.length).toBe(itemCatalog.length);
});

test("a collection is complete when each of its products sold enough", () => {
	const collection = albumCollections[0];
	const sold = Object.fromEntries(collection.productIds.map((id) => [id, SALES_TO_COLLECT]));
	expect(getCollectionProgress(collection, sold).complete).toBe(true);
	sold[collection.productIds[0]] = SALES_TO_COLLECT - 1;
	expect(getCollectionProgress(collection, sold).complete).toBe(false);
});
