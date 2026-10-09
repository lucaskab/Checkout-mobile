// Suppliers sell in boxes (case packs), the way real wholesalers do: a fardo of 6 bottles, a box of 12 milk
// cartons, a crate of vegetables. The player orders and pays per box; the stockroom keeps the boxes and the
// shelves are still filled unit by unit (src/stores/game-store.ts restockShelf).
//
// The sizes follow real case packs, kept small where the game starts (the sidewalk table has 200 coins), so
// the first boxes of fruit and vegetables cost a few turns of sales and never lock the player out:
//   fruit and vegetables: caixote with 5   · eggs: box with 6 trays    · water and soft drinks: fardo of 6
//   juice: 6 · energy drinks and beer: fardo of 12 · milk: box with 12 cartons · yoghurt and butter: 6
//   cheese, cold cuts, meat and fish: 4 (heavy, perishable) · bread: tray with 12, sliced bread and pastries: 8
//   sweets, biscuits, chocolate: display box with 12 · grocery staples: fardo of 10 (rice and coffee 6)
//   pasta: 12 · frozen: 6 (chips and pastries 10) · ice lollies: 12 · hygiene and cleaning: 6 to 12
//   pets, nappies, organic baskets, gourmet kits: 4 · wine and champagne: box of 6
// Sources: case pack conventions (en.wikipedia.org/wiki/Case_(goods)) and Brazilian wholesale listings.

const byCategory: Record<string, number> = {
	hortifruti: 5,
	organicos: 4,
	ovos: 6,
	laticinios: 6,
	queijos: 4,
	frios: 4,
	padaria: 8,
	doces: 12,
	chocolates: 12,
	bolachas: 12,
	sazonais: 6,
	bebidas: 6,
	refrigerantes: 6,
	aguas: 6,
	energeticos: 12,
	alcoolicos: 6,
	mercearia: 10,
	massas: 12,
	congelados: 6,
	sorvetes: 12,
	carnes: 4,
	peixes: 4,
	gourmet: 4,
	higiene: 6,
	limpeza: 6,
	pets: 4,
	bebes: 4,
	eletronicos: 12,
	papelaria: 10,
};

// Products whose real box differs from their category's.
const byProduct: Record<number, number> = {
	5: 12, // leite integral: caixa com 12 litros
	9: 12, // pão francês: bandeja com 12
	27: 4, // carne nobre
	31: 6, // vinho importado
	33: 6, // champanhe
	35: 12, // detergente
	51: 6, // arroz: fardo 6 × 5 kg
	55: 6, // café em pó
	15: 6, // café especial
	30: 6, // granola
	32: 6, // trufa gourmet
	34: 6, // shampoo
	58: 8, // papel higiênico: fardo com 8
	60: 12, // cerveja: fardo de 12 latas
	20: 10, // batata frita congelada
	18: 10, // pastel congelado
	36: 4, // ração premium
	37: 4, // fralda
	61: 12, // picolé
};

/** Units in one supplier box of this product. */
export function getCaseSize(product: { id: number; category: string; caseSize?: number }) {
	if (product.caseSize && product.caseSize > 0) return product.caseSize;
	return byProduct[product.id] ?? byCategory[product.category] ?? 6;
}

/** How many whole boxes `units` fill (a box that is partly used still counts as one). */
export function getBoxCount(units: number, caseSize: number) {
	return units <= 0 ? 0 : Math.ceil(units / Math.max(1, caseSize));
}
