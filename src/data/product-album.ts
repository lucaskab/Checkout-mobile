import { itemCatalog } from "@/data/market-products";

// Product album ("Álbum de produtos"): every product of the catalogue is a sticker. A product is collected once
// the market has sold SALES_TO_COLLECT units of it; completing a collection (a family of categories) pays a
// reward once. It rewards trying new products instead of selling the same few forever.

export const SALES_TO_COLLECT = 10;

type CollectionSeed = { id: string; name: string; categories: string[] };

const seeds: CollectionSeed[] = [
	{ id: "hortifruti", name: "Hortifruti", categories: ["hortifruti", "organicos"] },
	{ id: "bebidas", name: "Bebidas", categories: ["bebidas", "refrigerantes", "aguas", "energeticos"] },
	{ id: "doces", name: "Doces e lanches", categories: ["doces", "chocolates", "bolachas"] },
	{ id: "frios", name: "Laticínios e frios", categories: ["laticinios", "frios", "queijos"] },
	{ id: "padaria", name: "Padaria e massas", categories: ["padaria", "massas"] },
	{ id: "congelados", name: "Congelados", categories: ["congelados"] },
	{ id: "acougue", name: "Açougue e peixaria", categories: ["carnes", "peixes"] },
	{ id: "gourmet", name: "Gourmet e importados", categories: ["gourmet", "premium", "importados", "luxo"] },
];

export type AlbumCollection = {
	id: string;
	name: string;
	productIds: number[];
	reward: { coins: number; diamonds: number };
};

const grouped = new Set(seeds.flatMap((seed) => seed.categories));

export const albumCollections: AlbumCollection[] = [
	...seeds.map((seed) => ({ id: seed.id, name: seed.name, categories: seed.categories })),
	// Everything else (cleaning, pets, babies, seasonal…) is the "variedades" page.
	{ id: "variedades", name: "Variedades", categories: [] as string[] },
]
	.map((collection) => {
		const productIds = itemCatalog
			.filter((product) =>
				collection.id === "variedades"
					? !grouped.has(product.category)
					: collection.categories.includes(product.category),
			)
			.map((product) => product.id);
		return {
			id: collection.id,
			name: collection.name,
			productIds,
			reward: { coins: 200 * productIds.length, diamonds: productIds.length >= 6 ? 3 : 2 },
		};
	})
	.filter((collection) => collection.productIds.length > 0);

export function isProductCollected(soldByProduct: Record<number, number> | undefined, productId: number) {
	return (soldByProduct?.[productId] ?? 0) >= SALES_TO_COLLECT;
}

export function getCollectionProgress(
	collection: AlbumCollection,
	soldByProduct: Record<number, number> | undefined,
) {
	const collected = collection.productIds.filter((id) => isProductCollected(soldByProduct, id)).length;
	return { collected, total: collection.productIds.length, complete: collected === collection.productIds.length };
}
