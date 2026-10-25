import type { ProductionSectorId } from "@/@types/production";
import { itemCatalog } from "@/data/market-products";
import { getProductionSector, productionRecipes } from "@/data/production-sectors";
import { getSectorBuildStatus } from "@/services/interior-construction";
import type { Routes } from ".";
import { type KitchenItem, type KitchenStep, kstep, page, productIcon, type State } from "../view-kit";

// The hand-made production games (page.layout = "kitchen", drawn by CheckoutDesktopHUD.Kitchen.cs and the
// CheckoutDesktopHUD.Puzzle*.cs files). Lucas 24/10: every sector is a small puzzle that makes the player think, tied to
// the sector's real work — the baker fills the tray, the cheesemaker balances the aging rack, the butcher cuts to weight,
// the fishmonger closes the orders on the scale, the juice bar sorts the jugs, the ice-cream parlour stacks the cone
// from picture clues, the cellar measures the blend. The three recipes of a sector are its three levels. Fewer moves =
// more stars (1–3); 3 stars make one extra unit (store: cookByHand).

const art = (name: string) => `Game/${name}`;
const item = (productId: number): KitchenItem => ({
	icon: productIcon(productId),
	label: itemCatalog.find((entry) => entry.id === productId)?.name ?? "",
});

/** Queijaria: fill the aging rack so every shelf and column has one of each cheese; `givens` wheels already in. */
function maturacao(cheeses: string[], givens: number, hint: string): KitchenStep {
	return kstep("aging", "Encha a câmara de maturação", hint, { pieces: cheeses, singles: givens, done: "Maturação perfeita!" });
}

/** Açougue: knives over an uneven piece, every portion `grams` ± `tolerance`. */
function corte(portions: number, grams: number, tolerance: number, hint: string): KitchenStep {
	return kstep("portions", "Corte na medida", hint, { count: portions, scale: [grams, tolerance], done: "Tudo no peso!" });
}

/** Peixaria: share the pieces among the orders so every scale closes on its weight. */
function pedidos(trays: number, pieces: number, kinds: string[], hint: string): KitchenStep {
	return kstep("orders", "Pedidos na balança", hint, { count: trays, singles: pieces, pieces: kinds, done: "Pedidos fechados!" });
}

/** Sucos: pour the layers until every jug holds one juice (two empty jugs to help). */
function copos(flavors: string[], hint: string): KitchenStep {
	return kstep("sort", "Separe os sucos", hint, { pieces: flavors, singles: 2, done: "Cada suco na sua jarra!" });
}

/** Sorvetes: stack the scoops so every picture clue holds. */
function casquinha(flavors: string[], hint: string): KitchenStep {
	return kstep("scoops", "Monte a casquinha do pedido", hint, { pieces: flavors, done: "Casquinha certinha!" });
}

/** Adega: pour between unmarked vessels until one holds the asked litres (level 1–3). */
function medida(level: number, hint: string): KitchenStep {
	return kstep("decant", "Medida exata", hint, { count: level, done: "Medida certinha!" });
}

/** The bakery puzzle: fill a tray of `grid` cells with the dealt doughs (pieces of the set in
 * CheckoutDesktopHUD.KitchenPuzzle.cs: frances 1×1, forma 1×2, baguete 1×3, tranca 1×4, redondo 2×2). */
function fornada(title: string, grid: [number, number], pieces: string[], singles: number, hint: string): KitchenStep {
	return kstep("tray", title, hint, { grid, pieces, singles, done: "Assadeira cheia!" });
}

/** Into the oven: take it out when it is golden. */
function forno(raw: string, baked: string, title: string, hint: string, minutes: number, done: string): KitchenStep {
	return kstep("stop", title, hint, {
		art: art(raw),
		states: [art(baked)],
		back: art("kt_oven"),
		at: [0.5, 0.36],
		gauge: "oven",
		zone: [0.72, 0.88],
		scale: [0, minutes],
		unit: "min",
		seconds: 7,
		size: 300,
		done,
	});
}

const games: Record<string, () => KitchenStep[]> = {
	// ------------------------------------------------------------ padaria
	// The bakery is a packing puzzle (Lucas 24/10: "algo mais puzzle, que faça a pessoa pensar"): the doughs of the
	// batch, each its own shape on the grid, must fill the baking tray with no gap — then into the oven. The three
	// recipes are three levels: a bigger tray, longer loaves and fewer little rolls to plug the holes.
	"baguete-rustica": () => [
		fornada("Monte a fornada", [4, 3], ["frances", "forma", "baguete"], 3,
			"Arraste as massas para a assadeira até não sobrar nenhum buraco. Toque numa massa para girar."),
		forno("kt_baguette_raw", "kt_baguette_baked", "Asse com vapor", "Forno a 220 °C com vapor, uns 18 minutos. Tire quando a casca estiver bem dourada: cedo fica pálida, tarde queima.", 18, "Casquinha crocante!"),
	],
	"croissant-premium": () => [
		fornada("Monte a fornada", [5, 4], ["frances", "forma", "baguete", "redondo"], 2,
			"Encaixe todas as massas na assadeira, sem buracos. Toque para girar; arraste uma massa já posta para tirá-la."),
		forno("kt_croissant_raw", "kt_croissant_baked", "Asse", "Forno a 200 °C. Tire quando as camadas estiverem douradas e estufadas.", 16, "Folhado perfeito!"),
	],
	"bolo-de-vitrine": () => [
		fornada("Monte a fornada", [6, 4], ["frances", "forma", "baguete", "tranca", "redondo"], 1,
			"A fornada grande do dia: as massas compridas primeiro, os pãezinhos fecham os buracos. Toque para girar."),
		forno("kt_cake_batter", "kt_cake_baked", "Asse", "Forno a 180 °C. Tire quando o palito sair limpo: nem cru no meio, nem ressecado.", 40, "Palito limpo!"),
	],
	// ------------------------------------------------------------ queijaria: the aging rack (a small Latin square)
	"queijo-minas": () => [maturacao(["minas", "prato", "azul"], 3, "Arraste os queijos para a câmara: cada prateleira e cada coluna com um queijo de cada tipo.")],
	"brie-maturado": () => [maturacao(["minas", "prato", "brie", "azul"], 7, "Quatro queijos agora: nenhum tipo pode se repetir na mesma prateleira nem na mesma coluna.")],
	"tabua-de-queijos": () => [maturacao(["minas", "prato", "brie", "azul"], 5, "A câmara cheia da tábua, com poucas pistas: pense em cada fileira e cada coluna.")],
	// ------------------------------------------------------------ açougue: cut to weight
	"hamburguer-artesanal": () => [corte(4, 150, 15, "Arraste as facas: cada porção tem que dar 150 g. Onde a carne é mais grossa, a fatia fica mais estreita.")],
	"corte-dry-aged": () => [corte(5, 300, 20, "Bifes de 300 g cada. A peça é irregular: olhe a altura da carne antes de mover as facas.")],
	"kit-churrasco": () => [corte(6, 250, 12, "Seis peças de 250 g para o kit, com pouca folga na balança.")],
	// ------------------------------------------------------------ peixaria: orders on the scale
	"file-de-peixe": () => [pedidos(2, 5, ["peixe", "file"], "Monte os pedidos: arraste cada peixe para uma bandeja até cada balança fechar o peso pedido. Use todos.")],
	"sushi-especial": () => [pedidos(3, 7, ["file", "salmao", "camarao"], "Três pedidos, sete peças: todas têm que ir para alguma bandeja e cada uma fecha o peso exato.")],
	"barco-de-frutos-do-mar": () => [pedidos(3, 9, ["peixe", "salmao", "file", "camarao"], "O pedido grande do dia: nove peças em três bandejas, cada uma no peso certinho.")],
	// ------------------------------------------------------------ sucos: sort the layered jugs
	"suco-gelado": () => [copos(["laranja", "morango", "limao"], "Toque numa jarra e depois em outra para despejar. O suco só cai sobre o mesmo sabor ou numa jarra vazia.")],
	"cha-gelado": () => [copos(["laranja", "morango", "limao", "uva"], "Quatro sabores misturados: deixe cada jarra com um sabor só.")],
	"vitamina-cremosa": () => [copos(["laranja", "morango", "limao", "uva", "abacaxi"], "Cinco sabores e só duas jarras vazias: planeje antes de despejar.")],
	// ------------------------------------------------------------ sorvetes: the right cone, from picture clues
	"sorvete-creme": () => [casquinha(["chocolate", "morango", "baunilha"], "Monte a casquinha seguindo o pedido em desenhos: cada pista fica verde quando está certa.")],
	"sundae-chocolate": () => [casquinha(["chocolate", "morango", "baunilha", "menta"], "Quatro bolas: os sabores encostados ficam um em cima do outro; com pontinhos, é em algum lugar acima.")],
	"pote-sorvete-familia": () => [casquinha(["chocolate", "morango", "baunilha", "menta", "flocos"], "A casquinha gigante: cinco bolas e todas as pistas verdes.")],
	// ------------------------------------------------------------ adega: measure the blend exactly
	"vinho-da-casa": () => [medida(1, "Toque num recipiente e depois em outro para despejar até um esvaziar ou o outro encher. Consiga a medida pedida.")],
	"sangria-da-casa": () => [medida(2, "Os recipientes não têm marcas: só dá para medir enchendo e esvaziando. Chegue na medida exata.")],
	"kit-harmonizacao": () => [medida(3, "A medida mais difícil da adega: pense alguns passos à frente.")],
};

export const hasKitchenGame = (recipeId: string) => recipeId in games;

const tints: Record<string, string> = {
	padaria: "B7682B",
	queijaria: "D3A12A",
	acougue: "B33A32",
	peixaria: "2A7FA8",
	bebidas: "D46A2A",
	sorvetes: "D0679A",
	adega: "7A2E4A",
};

function kitchenPage(state: State, args: string[]) {
	const recipe = productionRecipes.find((entry) => entry.id === args[0]);
	const sector = recipe ? getProductionSector(recipe.sectorId) : undefined;
	const build = sector ? getSectorBuildStatus(state, sector.id) : null;
	const game = recipe ? games[recipe.id] : undefined;
	if (!recipe || !sector || !game) return page("kitchen", "Cozinha", [], { layout: "kitchen" });
	const missing = recipe.ingredients.filter((ingredient) => (state.inventory[ingredient.productId] ?? 0) < ingredient.quantity);
	const reason =
		build?.status !== "built"
			? "O setor ainda não está pronto."
			: state.market.level < recipe.requiredLevel
				? `Libera no nível ${recipe.requiredLevel}.`
				: missing.length
					? `Faltam ingredientes: ${missing.map((ingredient) => item(ingredient.productId).label).join(", ")}.`
					: "";
	const product = itemCatalog.find((entry) => entry.id === recipe.outputProductId);
	return page(`kitchen:${args.join(":")}`, product?.name ?? "Cozinha", [], {
		layout: "kitchen",
		subtitle: sector.name,
		icon: productIcon(recipe.outputProductId),
		kitchen: {
			recipeId: recipe.id,
			sectorId: sector.id as ProductionSectorId,
			title: product?.name ?? recipe.id,
			icon: productIcon(recipe.outputProductId),
			tint: tints[sector.id] ?? "8A5A2B",
			bench: art(`kt_bench_${sector.id}`),
			output: recipe.outputQuantity,
			back: `~sector:${sector.id}`,
			canCook: reason === "",
			reason,
			steps: game(),
			demo: args[1] !== undefined && args[1] !== "" ? Number(args[1]) : -1,
		},
	});
}

export const routes: Routes = {
	kitchen: kitchenPage,
};
