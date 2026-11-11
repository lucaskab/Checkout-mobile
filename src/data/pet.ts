import type { MarketEraId } from "@/@types/economy";
import type { PetCosmeticDefinition } from "@/@types/pet";

// "Mascote caramelo" numbers and catalogue (rules: src/services/store-pet.ts).

/** The stray dog shows up at the door from the Späti on. */
export const PET_FIRST_ERA: MarketEraId = "spati";
/** Petting him again needs a 2-minute break. */
export const PET_COOLDOWN_MS = 120_000;
/** A petted dog stays happy for a minute… */
export const PET_HAPPY_MS = 60_000;
/** …and a happy dog at the door brings 5% more customers. */
export const PET_HAPPY_ARRIVAL_MULTIPLIER = 1.05;
export const PET_EXPERIENCE = 2;
/** The collar he wears from day one. */
export const DEFAULT_PET_COLLAR = "collar_navy";
/** The fabric of his beds from day one (the market's navy). */
export const DEFAULT_PET_BED_STYLE = "bedstyle_navy";
/** His beds: build-mode decorations (src/data/interior-decor.ts), placed anywhere inside or outside the shop. He sleeps
 * on the nearest one when the market closes and naps on it now and then (Lucas 08/11). */
export const PET_BED_DECOR_IDS = ["pet-bed-round", "pet-bed-basket", "pet-bed-house", "pet-bed-sofa", "pet-bed-royal"];

export const PET_OFFER_TEXT = "Um vira-lata caramelo apareceu na porta! Adotar?";
export const PET_NAME = "Caramelo";

export const petCosmetics: PetCosmeticDefinition[] = [
	{
		id: "collar_navy",
		kind: "collar",
		name: "Coleira azul-marinho",
		description: "A coleira da casa, nas cores do mercado.",
		price: 0,
		currency: "coins",
		requiredLevel: 0,
	},
	{
		id: "collar_red",
		kind: "collar",
		name: "Coleira vermelha",
		description: "Vermelho vivo, dá para ver de longe.",
		price: 300,
		currency: "coins",
		requiredLevel: 0,
	},
	{
		id: "collar_green",
		kind: "collar",
		name: "Coleira verde",
		description: "Verde como a feira de sábado.",
		price: 300,
		currency: "coins",
		requiredLevel: 0,
	},
	{
		id: "collar_gold",
		kind: "collar",
		name: "Coleira dourada",
		description: "Para o cachorro mais chique do bairro.",
		price: 15,
		currency: "diamonds",
		requiredLevel: 15,
	},
	{
		id: "bandana_navy",
		kind: "bandana",
		name: "Bandana azul-marinho",
		description: "Uniforme de funcionário do mês.",
		price: 500,
		currency: "coins",
		requiredLevel: 0,
	},
	{
		id: "bandana_plaid",
		kind: "bandana",
		name: "Bandana xadrez",
		description: "Xadrez clássico, charme de fazenda.",
		price: 500,
		currency: "coins",
		requiredLevel: 0,
	},
	{
		id: "bandana_flowers",
		kind: "bandana",
		name: "Bandana florida",
		description: "Flores coloridas para alegrar a porta.",
		price: 8,
		currency: "diamonds",
		requiredLevel: 0,
	},
	{
		id: "pet_bed",
		kind: "bed",
		name: "Caminha",
		description: "Uma caminha macia perto da porta: ele tira um cochilo nela.",
		price: 800,
		currency: "coins",
		requiredLevel: 0,
		// the beds are decorations now (PET_BED_DECOR_IDS); old saves keep this one by the checkout
		hidden: true,
	},
	{
		id: "bedstyle_navy",
		kind: "bedStyle",
		name: "Tecido azul-marinho",
		description: "As caminhas nas cores do mercado, com debrum creme.",
		price: 0,
		currency: "coins",
		requiredLevel: 0,
	},
	{
		id: "bedstyle_teal",
		kind: "bedStyle",
		name: "Tecido verde-água",
		description: "Verde-água fresquinho em todas as caminhas.",
		price: 400,
		currency: "coins",
		requiredLevel: 0,
	},
	{
		id: "bedstyle_orange",
		kind: "bedStyle",
		name: "Tecido caramelo",
		description: "Combina com o pelo dele.",
		price: 400,
		currency: "coins",
		requiredLevel: 0,
	},
	{
		id: "bedstyle_rose",
		kind: "bedStyle",
		name: "Tecido rosê",
		description: "Rosa antigo, delicado e chique.",
		price: 10,
		currency: "diamonds",
		requiredLevel: 0,
	},
	{
		id: "pet_bowls",
		kind: "bowls",
		name: "Potes de água e ração",
		description: "Água fresca e ração sempre à mão.",
		price: 400,
		currency: "coins",
		requiredLevel: 0,
	},
];

export function getPetCosmetic(id: string) {
	return petCosmetics.find((item) => item.id === id) ?? null;
}
