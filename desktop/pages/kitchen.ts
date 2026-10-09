import type { ProductionSectorId } from "@/@types/production";
import { itemCatalog } from "@/data/market-products";
import { getProductionSector, productionRecipes } from "@/data/production-sectors";
import { getSectorBuildStatus } from "@/services/interior-construction";
import type { Routes } from ".";
import { type KitchenItem, type KitchenStep, kstep, page, productIcon, type State } from "../view-kit";

// The hand-made production games (page.layout = "kitchen", drawn by CheckoutDesktopHUD.Kitchen.cs): each recipe
// is cooked step by step the way it is done for real, from the guides of SEBRAE/ABNT (pão francês), Embrapa
// (queijo minas frescal) and the butcher's and fishmonger's routines. Each step is one gesture (drag the
// ingredients in, knead, wait for the dough to double, cut along the guides, take it out of the oven at the
// right moment…); how well it went gives 1–3 stars, and 3 stars make one extra unit (store: cookByHand).

const art = (name: string) => `Game/${name}`;
const item = (productId: number): KitchenItem => ({
	icon: productIcon(productId),
	label: itemCatalog.find((entry) => entry.id === productId)?.name ?? "",
});
const extra = (name: string, label: string): KitchenItem => ({ icon: art(name), label });

// Products used as ingredients.
const FARINHA = 43;
const MANTEIGA = 7;
const LEITE = 5;
const OVOS = 50;
const CHOCOLATE = 24;

const QUEIJO_PRATO = 6;
const VINHO = 31;
const BRIE = 105;
const MINAS = 104;

const CARNE = 27;
const TOMATE = 1;
const FRANGO = 57;
const CERVEJA = 60;
const ARROZ = 51;
const PEIXE = 44;
const BANANA = 46;
const AGUA_MINERAL = 21;
const REFRIGERANTE = 14;
const MACA = 49;
const UVA = 62;
const IOGURTE = 8;
const ACUCAR = 53;
const CHA = 16;
const TRUFA = 32;
const SORVETE = 116;
const VINHO_CASA = 119;
const TABUA = 106;

const SAL_GROSSO = extra("kt_salt", "Sal");
const VINAGRE = extra("kt_vinegar", "Vinagre de arroz");

const FERMENTO_LACTEO = extra("kt_culture", "Fermento lácteo");
const CLORETO = extra("kt_calcium", "Cloreto de cálcio");
const COALHO = extra("kt_rennet", "Coalho");
const MOFO = extra("kt_penicillium", "Mofo branco");
const FERMENTO = extra("kt_yeast", "Fermento");
const AGUA = extra("kt_water", "Água gelada");
const SAL = extra("kt_salt", "Sal");

/** Four slanted cuts along a loaf that fills the art from side to side. */
const pestanas = [0.2, 0.4, 0.6, 0.8].flatMap((x) => [x - 0.07, 0.36, x + 0.07, 0.64]);

/** Cut lines over the vat: four down, three across (cubes of about 1.5 cm). */
const lira = [
	...[0.32, 0.44, 0.56, 0.68].flatMap((x) => [x, 0.6, x, 0.92]),
	...[0.66, 0.76, 0.86].flatMap((y) => [0.2, y, 0.8, y]),
];

/** The cheese-making steps (milk to fresh cheese in molds); `warm` is the temperature for the rennet. */
function cheeseMaking(molds: number, milk: KitchenItem[], warm: number, extraCulture?: KitchenItem): KitchenStep[] {
	const from = 65;
	const to = 25;
	const at = (temperature: number) => (from - temperature) / (from - to);
	return [
		kstep("add", "Coloque o leite no tacho", "Leite fresco e coado no tacho de inox.", {
			art: art("kt_pot_milk"),
			items: milk,
			size: 380,
			done: "Tacho cheio!",
		}),
		kstep("heat", "Pasteurize o leite", "Segure para aquecer e mantenha entre 63 e 67 °C. Na fábrica são 30 minutos a 65 °C: mata os micróbios sem estragar o leite.", {
			art: art("kt_pot_milk"),
			zone: [(63 - 20) / 60, (67 - 20) / 60],
			scale: [20, 80],
			unit: "°C",
			seconds: 4,
			size: 380,
			done: "Leite pasteurizado!",
		}),
		kstep("stop", `Esfrie até ${warm} °C`, `Deixe esfriar e toque em AGORA quando chegar a ${warm} °C: é a temperatura em que o coalho trabalha.`, {
			art: art("kt_pot_milk"),
			zone: [at(warm + 2), at(warm - 2)],
			scale: [from, to],
			unit: "°C",
			seconds: 6,
			size: 380,
			done: `${warm} °C certinho!`,
		}),
		kstep("add", "Fermento, cloreto e coalho", "Primeiro o fermento lácteo, depois o cloreto de cálcio e por último o coalho, mexendo bem.", {
			art: art("kt_pot_milk"),
			items: [FERMENTO_LACTEO, ...(extraCulture ? [extraCulture] : []), CLORETO, COALHO],
			size: 380,
			done: "Agora é esperar!",
		}),
		kstep("stop", "Espere coalhar", "Em uns 40 minutos o leite vira um gel. Toque em PRONTO quando a coalhada estiver firme e der um corte limpo.", {
			art: art("kt_pot_milk"),
			states: [art("kt_pot_gel")],
			gauge: "grow",
			zone: [0.66, 0.86],
			scale: [0, 50],
			unit: "min",
			seconds: 6,
			size: 340,
			done: "Corte limpo!",
		}),
		kstep("cut", "Corte a coalhada", "Passe a lira de ponta a ponta: primeiro as linhas de cima para baixo, depois as de lado. Cubos de 1,5 cm soltam o soro.", {
			art: art("kt_pot_gel"),
			states: [art("kt_pot_curd")],
			lines: lira,
			tool: art("kt_lira"),
			size: 420,
			done: "Cubinhos perfeitos!",
		}),
		kstep("rub", "Mexa devagar", "Mexa bem devagar com a concha. Rápido demais quebra os grãos e o queijo fica seco!", {
			art: art("kt_pot_curd"),
			tool: art("kt_ladle"),
			count: 8,
			slow: 900,
			size: 420,
			done: "Grãos firmes!",
		}),
		kstep("place", "Enforme", "Pegue a massa com a concha e encha cada forma furada: o soro escorre pelos furinhos.", {
			art: art("kt_molds"),
			states: [art("kt_molds_full")],
			items: [extra("kt_curd_scoop", "Massa")],
			spots: [0.27, 0.68, 0.73, 0.68, 0.27, 0.38, 0.73, 0.38].slice(0, Math.max(2, Math.min(4, molds)) * 2),
			size: 520,
			done: "Formas cheias!",
		}),
		kstep("tap", "Vire e salgue", "Vire cada queijo na forma e salgue o outro lado (15 g por lado).", {
			art: art("kt_molds_full"),
			states: [art("kt_cheese_minas")],
			spots: [0.27, 0.62, 0.73, 0.62, 0.27, 0.36, 0.73, 0.36],
			size: 520,
			done: "Queijos prontos!",
		}),
	];
}

/** The butcher's "toalete": the thick fat cap and the silver skin are cut off. */
const toalete = () =>
	kstep("tap", "Faça a toalete", "Tire a capa de gordura grossa e os nervos (a pele prateada): toque em cada pedaço para cortar fora.", {
		art: art("kt_meat_raw"),
		states: [art("kt_meat_clean")],
		spots: [0.3, 0.74, 0.5, 0.78, 0.7, 0.74, 0.22, 0.46, 0.58, 0.44, 0.78, 0.42],
		size: 440,
		done: "Carne limpinha!",
	});

/** Scale, gut, wash, fillet and debone a fish. */
const cleanFish = (): KitchenStep[] => [
	kstep("add", "Pegue o peixe", "Peixe fresco: olho brilhante, guelra vermelha e carne firme.", {
		art: art("kt_ice_tray"),
		items: [item(PEIXE)],
		size: 460,
		done: "Peixe fresquinho!",
	}),
	kstep("swipe", "Escame", "Raspe da cauda para a cabeça (da direita para a esquerda), contra as escamas.", {
		art: art("kt_fish_whole"),
		states: [art("kt_fish_scaled")],
		dir: 180,
		count: 7,
		size: 560,
		done: "Sem escamas!",
	}),
	kstep("cut", "Abra a barriga", "Um corte raso pela barriga, da cabeça até o rabo, sem furar as vísceras.", {
		art: art("kt_fish_scaled"),
		states: [art("kt_fish_open")],
		lines: [0.22, 0.32, 0.62, 0.32],
		tool: art("kt_fish_knife"),
		size: 560,
		done: "Corte limpo!",
	}),
	kstep("rub", "Limpe e lave", "Tire as vísceras e lave bem por dentro, em água corrente.", {
		art: art("kt_fish_open"),
		count: 6,
		size: 560,
		done: "Limpinho!",
	}),
	kstep("cut", "Filete", "Faca rente à espinha, da cabeça até o rabo: um filé de cada lado.", {
		art: art("kt_fish_open"),
		states: [art("kt_fillets")],
		lines: [0.14, 0.52, 0.8, 0.52],
		tool: art("kt_fish_knife"),
		size: 560,
		done: "Dois filés!",
	}),
	kstep("tap", "Tire as espinhas", "Com a pinça, puxe cada espinha no sentido da cabeça.", {
		art: art("kt_fillet_bones"),
		states: [art("kt_fillets")],
		spots: [0.27, 0.72, 0.34, 0.72, 0.41, 0.72, 0.48, 0.72, 0.55, 0.72, 0.62, 0.72, 0.69, 0.72],
		size: 460,
		done: "Sem espinhas!",
	}),
];

/** Sushi rice: seasoned and cooled with the spatula, then the fish sliced. */
const sushiRice = (): KitchenStep[] => [
	kstep("add", "Tempere o arroz", "Arroz cozido no ponto, vinagre de arroz e uma pitada de sal e açúcar.", {
		art: art("kt_rice_tub"),
		states: [art("kt_rice_seasoned")],
		items: [item(ARROZ), VINAGRE, SAL_GROSSO],
		size: 440,
		done: "Temperado!",
	}),
	kstep("rub", "Misture e abane", "Corte o arroz com a espátula, sem amassar: devagar, para os grãos ficarem inteiros e brilhando.", {
		art: art("kt_rice_seasoned"),
		tool: art("kt_ladle"),
		count: 8,
		slow: 1300,
		size: 440,
		done: "Grãos soltinhos!",
	}),
];
const sliceSalmon = (): KitchenStep[] => [
	kstep("cut", "Fatie o peixe", "Fatias na diagonal, num movimento só da faca, sem serrar.", {
		art: art("kt_salmon_block"),
		states: [art("kt_salmon_slices")],
		lines: [0.25, 0.12, 0.2, 0.88, 0.4, 0.12, 0.35, 0.88, 0.55, 0.12, 0.5, 0.88, 0.7, 0.12, 0.65, 0.88],
		tool: art("kt_fish_knife"),
		size: 440,
		done: "Fatias perfeitas!",
	}),
];

/** Blend: hold to run the blender and stop in the smooth zone (too long heats and foams). */
const blend = (from: string, to: string) =>
	kstep("heat", "Bata", "Segure para bater e mantenha na faixa verde até ficar lisinho. Demais esquenta e espuma.", {
		art: art(from),
		states: [art(to)],
		zone: [0.55, 0.8],
		scale: [0, 100],
		unit: "%",
		seconds: 3,
		size: 380,
		done: "Lisinho!",
	});
/** Pour into the glass with ice. */
const serve = (full: string) =>
	kstep("place", "Sirva com gelo", "Três cubos de gelo no copo.", {
		art: art(full),
		items: [extra("kt_ice_cube", "Gelo")],
		spots: [0.4, 0.8, 0.6, 0.82, 0.5, 0.72],
		size: 320,
		done: "Geladinho!",
	});

const games: Record<string, () => KitchenStep[]> = {
	// ------------------------------------------------------------ padaria
	"baguete-rustica": () => [
		kstep("add", "Misture os ingredientes", "Na ordem da padaria: farinha e fermento, a água gelada (segura a massa em 27 °C), o sal e por último a gordura.", {
			art: art("kt_bowl"),
			states: [art("kt_dough_rough")],
			items: [item(FARINHA), FERMENTO, AGUA, SAL, item(MANTEIGA)],
			size: 330,
			done: "Massa misturada!",
		}),
		kstep("rub", "Sove a massa", "Esfregue a massa para os lados até ela ficar lisa e elástica: o ponto de véu, quando estica fininha sem rasgar.", {
			art: art("kt_dough_rough"),
			states: [art("kt_dough_smooth")],
			count: 14,
			size: 300,
			done: "Ponto de véu!",
		}),
		kstep("stop", "Deixe crescer", "A massa descansa coberta, num lugar morno (~32 °C). Toque em PRONTO quando ela dobrar de tamanho: nem antes, nem depois.", {
			art: art("kt_dough_smooth"),
			states: [art("kt_dough_risen")],
			gauge: "grow",
			zone: [0.62, 0.8],
			scale: [1, 2.4],
			unit: "x",
			seconds: 7,
			size: 280,
			done: "Dobrou de tamanho!",
		}),
		kstep("swipe", "Modele as baguetes", "Abra, enrole e alongue: arraste para os lados sobre a massa para esticá-la num bastão comprido.", {
			art: art("kt_dough_risen"),
			states: [art("kt_baguette_raw")],
			dir: -1,
			count: 6,
			size: 300,
			done: "Bem modelada!",
		}),
		kstep("cut", "Faça as pestanas", "Com a lâmina, corte rápido e inclinado sobre cada guia, de ponta a ponta. É esse corte que abre e vira a pestana crocante.", {
			art: art("kt_baguette_raw"),
			states: [art("kt_baguette_scored")],
			lines: pestanas,
			tool: art("kt_blade"),
			size: 760,
			done: "Pestanas perfeitas!",
		}),
		kstep("stop", "Asse com vapor", "Forno a 220 °C com vapor, uns 18 minutos. Tire quando a casca estiver bem dourada: cedo fica pálida, tarde queima.", {
			art: art("kt_baguette_scored"),
			states: [art("kt_baguette_baked")],
			back: art("kt_oven"),
			at: [0.5, 0.36],
			gauge: "oven",
			zone: [0.72, 0.88],
			scale: [0, 18],
			unit: "min",
			seconds: 8,
			size: 300,
			done: "Casquinha crocante!",
		}),
	],
	"croissant-premium": () => [
		kstep("add", "Faça a massa", "Farinha, fermento, leite e uma pitada de sal na tigela.", {
			art: art("kt_bowl"),
			states: [art("kt_dough_rough")],
			items: [item(FARINHA), FERMENTO, item(LEITE), SAL],
			size: 330,
			done: "Massa pronta para sovar!",
		}),
		kstep("rub", "Sove", "Sove até a massa ficar lisa.", {
			art: art("kt_dough_rough"),
			states: [art("kt_dough_smooth")],
			count: 10,
			size: 300,
			done: "Lisinha!",
		}),
		kstep("add", "Coloque a manteiga", "Abra a massa e coloque a manteiga gelada no meio: ela vai virar as camadas folhadas.", {
			art: art("kt_dough_sheet"),
			items: [item(MANTEIGA)],
			size: 420,
			done: "Manteiga envelopada!",
		}),
		kstep("swipe", "Lamine em 3 dobras", "Estique a massa para cima e para baixo e dobre em três, três vezes. Cada dobra multiplica as camadas.", {
			art: art("kt_dough_sheet"),
			dir: 90,
			count: 6,
			size: 420,
			done: "27 camadas de manteiga!",
		}),
		kstep("cut", "Corte os triângulos", "Corte a massa laminada em triângulos compridos seguindo as guias.", {
			art: art("kt_dough_sheet"),
			states: [art("kt_croissant_raw")],
			lines: [0.08, 0.15, 0.3, 0.85, 0.3, 0.85, 0.52, 0.15, 0.52, 0.15, 0.74, 0.85, 0.74, 0.85, 0.92, 0.15],
			tool: art("kt_blade"),
			size: 420,
			done: "Agora é só enrolar!",
		}),
		kstep("stop", "Asse", "Forno a 200 °C. Tire quando estiverem bem dourados e folhados.", {
			art: art("kt_croissant_raw"),
			states: [art("kt_croissant_baked")],
			back: art("kt_oven"),
			at: [0.5, 0.36],
			gauge: "oven",
			zone: [0.7, 0.86],
			scale: [0, 20],
			unit: "min",
			seconds: 8,
			size: 220,
			done: "Folhados e dourados!",
		}),
	],
	"bolo-de-vitrine": () => [
		kstep("add", "Misture a massa", "Ovos, leite, farinha e o chocolate derretido na tigela.", {
			art: art("kt_bowl"),
			states: [art("kt_cake_batter")],
			items: [item(OVOS), item(LEITE), item(FARINHA), item(CHOCOLATE)],
			size: 330,
			done: "Tudo na tigela!",
		}),
		kstep("rub", "Bata a massa", "Bata com o batedor até a massa ficar lisa e aerada, sem pelotas.", {
			art: art("kt_cake_batter"),
			tool: art("kt_whisk"),
			count: 12,
			size: 330,
			done: "Massa fofinha!",
		}),
		kstep("stop", "Asse", "Forno a 180 °C. Tire quando o palito sair limpo: nem cru no meio, nem ressecado.", {
			art: art("kt_cake_batter"),
			states: [art("kt_cake_baked")],
			back: art("kt_oven"),
			at: [0.5, 0.36],
			gauge: "oven",
			zone: [0.66, 0.84],
			scale: [0, 40],
			unit: "min",
			seconds: 9,
			size: 230,
			done: "Palito limpo!",
		}),
		kstep("tap", "Decore", "Toque em cada marca para pôr o chantilly e as cerejas.", {
			art: art("kt_cake_baked"),
			states: [art("kt_cake_done")],
			spots: [0.5, 0.86, 0.79, 0.76, 0.88, 0.55, 0.74, 0.38, 0.5, 0.33, 0.26, 0.38, 0.12, 0.55, 0.21, 0.76],
			size: 360,
			done: "Pronto para a vitrine!",
		}),
	],
	// ------------------------------------------------------------ queijaria (Embrapa: queijo minas frescal)
	"queijo-minas": () => cheeseMaking(4, [item(LEITE)], 38),
	"brie-maturado": () => [
		...cheeseMaking(4, [item(LEITE), item(QUEIJO_PRATO)], 32, MOFO),
		kstep("stop", "Deixe maturar", "Na câmara a 12 °C e bem úmida, o mofo branco cobre a casca. Toque quando ela estiver aveludada e branquinha.", {
			art: art("kt_cheese_fresh"),
			states: [art("kt_cheese_brie")],
			zone: [0.66, 0.86],
			scale: [0, 30],
			unit: "dias",
			seconds: 7,
			size: 300,
			done: "Casca aveludada!",
		}),
	],
	"tabua-de-queijos": () => [
		kstep("cut", "Corte o brie em fatias", "Corte do centro para fora, como uma pizza, seguindo as guias.", {
			art: art("kt_cheese_brie"),
			lines: [0.5, 0.55, 0.5, 0.95, 0.5, 0.55, 0.88, 0.62, 0.5, 0.55, 0.78, 0.18, 0.5, 0.55, 0.22, 0.18, 0.5, 0.55, 0.12, 0.62],
			tool: art("kt_blade"),
			size: 340,
			done: "Fatias iguais!",
		}),
		kstep("place", "Monte a tábua", "Arrume as fatias de queijo nos lugares marcados da tábua.", {
			art: art("kt_board"),
			states: [art("kt_cheese_board")],
			items: [extra("kt_cheese_wedge", "Fatia de queijo")],
			spots: [0.22, 0.68, 0.76, 0.68, 0.3, 0.32, 0.5, 0.3, 0.7, 0.32],
			size: 520,
			done: "Tábua montada!",
		}),
		kstep("add", "Harmonize", "Coloque o queijo minas e o vinho para acompanhar.", {
			art: art("kt_cheese_board"),
			items: [item(MINAS), item(BRIE), item(VINHO)],
			size: 520,
			done: "Pronta para servir!",
		}),
	],
	// ------------------------------------------------------------ açougue
	"hamburguer-artesanal": () => [
		toalete(),
		kstep("rub", "Moa a carne", "Gire a manivela: a carne passa pelo disco e sai moída.", {
			art: art("kt_grinder"),
			states: [art("kt_grinder_full")],
			count: 10,
			size: 420,
			done: "Carne moída na hora!",
		}),
		kstep("add", "Tempere", "Tomate picadinho e sal, só na hora de modelar.", {
			art: art("kt_grinder_full"),
			items: [item(TOMATE), SAL_GROSSO],
			size: 420,
			done: "Temperado!",
		}),
		kstep("stop", "Pese 150 g", "A carne vai caindo na balança: toque quando der 150 g. Todo hambúrguer igual!", {
			art: art("kt_scale"),
			zone: [145 / 200, 155 / 200],
			scale: [0, 200],
			unit: "g",
			seconds: 5,
			size: 340,
			done: "150 g na mosca!",
		}),
		kstep("swipe", "Prense", "Aperte para baixo no aro até virar um disco de uns 2 cm.", {
			art: art("kt_patty_ball"),
			states: [art("kt_patty")],
			dir: -90,
			count: 4,
			size: 260,
			done: "Disco perfeito!",
		}),
		kstep("place", "Embale", "Coloque os hambúrgueres na bandeja: o filme e a etiqueta com o peso vão por cima.", {
			art: art("kt_tray_foam"),
			states: [art("kt_tray_patties")],
			items: [extra("kt_patty", "Hambúrguer")],
			spots: [0.28, 0.68, 0.72, 0.68, 0.28, 0.34, 0.72, 0.34],
			size: 480,
			done: "Pronto para a vitrine!",
		}),
	],
	"corte-dry-aged": () => [
		toalete(),
		kstep("stop", "Câmara de maturação", "A 1–3 °C e 80% de umidade a carne fica macia e ganha sabor de castanhas. Tire entre 21 e 30 dias.", {
			art: art("kt_meat_clean"),
			states: [art("kt_meat_aged")],
			back: art("kt_aging_cabinet"),
			at: [0.5, 0.52],
			zone: [21 / 45, 30 / 45],
			scale: [0, 45],
			unit: "dias",
			seconds: 8,
			size: 200,
			done: "Maturado no ponto!",
		}),
		kstep("cut", "Tire a casca seca", "Corte fora a crosta escura de cada borda: por dentro está a carne macia.", {
			art: art("kt_meat_aged"),
			states: [art("kt_meat_clean")],
			lines: [0.1, 0.25, 0.9, 0.25, 0.1, 0.8, 0.9, 0.8, 0.12, 0.25, 0.12, 0.8, 0.88, 0.25, 0.88, 0.8],
			tool: art("kt_cleaver"),
			size: 440,
			done: "Casca aparada!",
		}),
		kstep("cut", "Corte os bifes", "Contra a fibra, bifes de dois dedos de altura.", {
			art: art("kt_meat_clean"),
			states: [art("kt_steaks")],
			lines: [0.36, 0.15, 0.36, 0.9, 0.64, 0.15, 0.64, 0.9],
			tool: art("kt_cleaver"),
			size: 440,
			done: "Bifes alto!",
		}),
		kstep("place", "Embale a vácuo", "Os bifes vão para a bandeja e a máquina tira o ar.", {
			art: art("kt_tray_foam"),
			states: [art("kt_tray_steaks")],
			items: [extra("kt_steak", "Bife")],
			spots: [0.22, 0.52, 0.5, 0.52, 0.78, 0.52],
			size: 480,
			done: "Embalado!",
		}),
	],
	"kit-churrasco": () => [
		kstep("cut", "Corte a picanha", "Contra a fibra, em bifes grossos, sempre com a capa de gordura.", {
			art: art("kt_picanha"),
			lines: [0.3, 0.12, 0.3, 0.9, 0.5, 0.12, 0.5, 0.9, 0.7, 0.12, 0.7, 0.9],
			tool: art("kt_cleaver"),
			size: 460,
			done: "Bifes de picanha!",
		}),
		kstep("tap", "Sal grosso", "Só sal grosso, bem espalhado, na hora de ir para a brasa.", {
			art: art("kt_picanha"),
			spots: [0.18, 0.4, 0.38, 0.58, 0.58, 0.42, 0.78, 0.58, 0.3, 0.3, 0.7, 0.32],
			size: 460,
			done: "Bem salgadinha!",
		}),
		kstep("place", "Monte os espetos", "Espete os pedaços com a gordura toda do mesmo lado.", {
			art: art("kt_skewer"),
			states: [art("kt_skewer_full")],
			items: [extra("kt_picanha_piece", "Picanha")],
			spots: [0.3, 0.5, 0.44, 0.5, 0.58, 0.5, 0.72, 0.5, 0.86, 0.5],
			size: 560,
			done: "Espetos prontos!",
		}),
		kstep("add", "Monte o kit", "Os espetos, o frango e as cervejas geladas na caixa.", {
			art: art("kt_bbq_box"),
			states: [art("kt_bbq_box_full")],
			items: [extra("kt_skewer_full", "Espetos"), item(FRANGO), item(CERVEJA)],
			size: 480,
			done: "Churrasco garantido!",
		}),
	],
	// ------------------------------------------------------------ peixaria
	"file-de-peixe": () => [
		...cleanFish(),
		kstep("place", "Para o gelo", "Peixe fresco fica entre 0 e 4 °C: direto para a cama de gelo.", {
			art: art("kt_ice_tray"),
			states: [art("kt_ice_tray_full")],
			items: [extra("kt_fillet", "Filé")],
			spots: [0.5, 0.78, 0.5, 0.6, 0.5, 0.42, 0.5, 0.24],
			size: 500,
			done: "Fresquinho no gelo!",
		}),
	],
	"sushi-especial": () => [
		...sushiRice(),
		...sliceSalmon(),
		kstep("swipe", "Enrole", "Enrole com a esteira de bambu, apertando de leve, de baixo para cima.", {
			art: art("kt_makisu"),
			states: [art("kt_sushi_roll")],
			dir: 90,
			count: 3,
			size: 420,
			done: "Rolinho firme!",
		}),
		kstep("cut", "Corte o rolo", "Faca molhada, um corte só em cada guia: peças iguais.", {
			art: art("kt_sushi_roll"),
			lines: [0.25, 0.2, 0.25, 0.8, 0.42, 0.2, 0.42, 0.8, 0.58, 0.2, 0.58, 0.8, 0.75, 0.2, 0.75, 0.8],
			tool: art("kt_fish_knife"),
			size: 480,
			done: "Peças iguais!",
		}),
		kstep("place", "Monte o prato", "Arrume as peças no prato.", {
			art: art("kt_sushi_plate"),
			states: [art("kt_sushi_plate_full")],
			items: [extra("kt_sushi_piece", "Sushi")],
			spots: [0.12, 0.5, 0.31, 0.5, 0.5, 0.5, 0.69, 0.5, 0.88, 0.5],
			size: 520,
			done: "Lindo!",
		}),
	],
	"barco-de-frutos-do-mar": () => [
		...sushiRice(),
		...sliceSalmon(),
		kstep("place", "Monte o barco", "Os sushis enfileirados no barco de madeira.", {
			art: art("kt_sushi_boat"),
			items: [extra("kt_sushi_piece", "Sushi")],
			spots: [0.18, 0.55, 0.3, 0.55, 0.42, 0.55, 0.54, 0.55, 0.66, 0.55, 0.78, 0.55],
			size: 560,
			done: "Sushis a bordo!",
		}),
		kstep("place", "Camarões", "Por último os camarões, do outro lado do barco.", {
			art: art("kt_sushi_boat"),
			states: [art("kt_sushi_boat_full")],
			items: [extra("kt_shrimp", "Camarão")],
			spots: [0.24, 0.7, 0.42, 0.7, 0.6, 0.7, 0.78, 0.7],
			size: 560,
			done: "Barco completo!",
		}),
	],
	// ------------------------------------------------------------ bebidas
	"suco-gelado": () => [
		kstep("rub", "Lave as frutas", "Esfregue as frutas na água: casca limpa, suco seguro.", {
			art: art("kt_fruit_bowl"),
			states: [art("kt_fruit_washed")],
			count: 6,
			size: 400,
			done: "Frutas limpinhas!",
		}),
		kstep("cut", "Corte a maçã", "Em quatro, tirando o miolo e as sementes.", {
			art: art("kt_apple"),
			states: [art("kt_apple_sliced")],
			lines: [0.5, 0.22, 0.5, 0.95, 0.24, 0.6, 0.76, 0.6],
			tool: art("kt_fish_knife"),
			size: 380,
			done: "Maçã em quartos!",
		}),
		kstep("add", "Para o liquidificador", "Maçã, banana e água gelada no copo do liquidificador.", {
			art: art("kt_blender"),
			states: [art("kt_blender_fruit")],
			items: [item(MACA), item(BANANA), item(AGUA_MINERAL)],
			size: 380,
			done: "Tampa e vamos lá!",
		}),
		blend("kt_blender_fruit", "kt_blender_juice"),
		serve("kt_glass_juice"),
	],
	"cha-gelado": () => [
		kstep("heat", "Aqueça a água", "Para o chá, a água vai a 90–95 °C, sem ferver demais: segure e mantenha na faixa.", {
			art: art("kt_kettle"),
			zone: [(90 - 20) / 80, (95 - 20) / 80],
			scale: [20, 100],
			unit: "°C",
			seconds: 3,
			size: 340,
			done: "Água no ponto!",
		}),
		kstep("add", "Infusão", "O chá e o açúcar na água quente.", {
			art: art("kt_glass"),
			states: [art("kt_glass_tea")],
			items: [item(CHA), item(ACUCAR), item(AGUA_MINERAL)],
			size: 320,
			done: "Agora a infusão!",
		}),
		kstep("stop", "Deixe em infusão", "De 3 a 5 minutos: menos fica fraco, mais fica amargo.", {
			art: art("kt_glass_tea"),
			zone: [3 / 8, 5 / 8],
			scale: [0, 8],
			unit: "min",
			seconds: 6,
			size: 320,
			done: "Sabor no ponto!",
		}),
		serve("kt_glass_tea"),
	],
	"vitamina-cremosa": () => [
		kstep("add", "Para o liquidificador", "Leite gelado, iogurte e banana.", {
			art: art("kt_blender"),
			states: [art("kt_blender_fruit")],
			items: [item(LEITE), item(IOGURTE), item(BANANA)],
			size: 380,
			done: "Tudo dentro!",
		}),
		blend("kt_blender_fruit", "kt_blender_smoothie"),
		kstep("stop", "Encha o copo", "Toque para parar quando chegar perto da borda, sem derramar.", {
			art: art("kt_glass"),
			states: [art("kt_glass_smoothie")],
			zone: [0.78, 0.92],
			scale: [0, 400],
			unit: "ml",
			seconds: 5,
			size: 320,
			done: "Copo cheio!",
		}),
	],
	// ------------------------------------------------------------ sorvetes
	"sorvete-creme": () => [
		kstep("add", "Faça a base", "Leite, iogurte e açúcar na produtora.", {
			art: art("kt_churner"),
			items: [item(LEITE), item(IOGURTE), item(ACUCAR)],
			size: 400,
			done: "Base pronta!",
		}),
		kstep("heat", "Pasteurize a base", "Aqueça e segure entre 72 e 76 °C: a base fica segura e mais cremosa.", {
			art: art("kt_churner"),
			zone: [(72 - 20) / 70, (76 - 20) / 70],
			scale: [20, 90],
			unit: "°C",
			seconds: 3,
			size: 400,
			done: "Pasteurizada!",
		}),
		kstep("stop", "Matura na geladeira", "A base descansa na geladeira: toque quando estiver entre 4 e 8 °C.", {
			art: art("kt_churner"),
			zone: [(76 - 8) / 74, (76 - 4) / 74],
			scale: [76, 2],
			unit: "°C",
			seconds: 6,
			size: 400,
			done: "Fria e maturada!",
		}),
		kstep("rub", "Bata congelando", "A pá bate e congela ao mesmo tempo, colocando ar: é isso que deixa o sorvete leve.", {
			art: art("kt_churner"),
			states: [art("kt_churner_full")],
			count: 12,
			size: 400,
			done: "Cremoso!",
		}),
		kstep("place", "Encha os potes", "Uma bola em cada pote.", {
			art: art("kt_ice_pot"),
			states: [art("kt_ice_pot_full")],
			items: [extra("kt_scoop", "Bola de sorvete")],
			spots: [0.5, 0.72],
			size: 320,
			done: "Pote cheio!",
		}),
		kstep("stop", "Endureça no freezer", "No freezer abaixo de -18 °C: toque quando estiver firme.", {
			art: art("kt_ice_pot_full"),
			zone: [(4 + 18) / 30, 0.97],
			scale: [4, -26],
			unit: "°C",
			seconds: 6,
			size: 320,
			done: "Firme e cremoso!",
		}),
	],
	"sundae-chocolate": () => [
		kstep("place", "Duas bolas na taça", "Sorvete de creme bem firme.", {
			art: art("kt_sundae"),
			items: [extra("kt_scoop", "Bola de sorvete")],
			spots: [0.38, 0.78, 0.62, 0.78],
			size: 360,
			done: "Duas bolas!",
		}),
		kstep("tap", "Calda de chocolate", "Toque em cada ponto para fazer a calda escorrer.", {
			art: art("kt_sundae"),
			states: [art("kt_sundae_full")],
			spots: [0.3, 0.84, 0.45, 0.88, 0.6, 0.86, 0.72, 0.8, 0.5, 0.76],
			size: 360,
			done: "Calda por cima!",
		}),
		kstep("add", "Cereja", "E a cereja no topo, com o chocolate.", {
			art: art("kt_sundae_full"),
			items: [item(SORVETE), item(CHOCOLATE)],
			size: 360,
			done: "Sundae perfeito!",
		}),
	],
	"pote-sorvete-familia": () => [
		kstep("place", "Três bolas no pote", "Bolas grandes, uma ao lado da outra.", {
			art: art("kt_family_pot"),
			states: [art("kt_family_pot_full")],
			items: [extra("kt_scoop", "Bola de sorvete")],
			spots: [0.32, 0.75, 0.68, 0.75, 0.5, 0.86],
			size: 380,
			done: "Pote cheio!",
		}),
		kstep("add", "Cobertura", "Sorvete de creme e maçã picadinha por cima.", {
			art: art("kt_family_pot_full"),
			items: [item(SORVETE), item(MACA)],
			size: 380,
			done: "Pote família!",
		}),
	],
	// ------------------------------------------------------------ adega
	"vinho-da-casa": () => [
		kstep("add", "As uvas na tina", "Uvas maduras, sem os cabinhos.", {
			art: art("kt_grape_tub"),
			items: [item(UVA)],
			size: 420,
			done: "Tina cheia!",
		}),
		kstep("rub", "Esmague as uvas", "Pise as uvas para soltar o mosto: casca, polpa e suco.", {
			art: art("kt_grape_tub"),
			states: [art("kt_grape_crushed")],
			count: 12,
			size: 420,
			done: "Mosto pronto!",
		}),
		kstep("add", "Açúcar e fermentação", "Um pouco de açúcar para as leveduras transformarem em álcool.", {
			art: art("kt_grape_crushed"),
			items: [item(ACUCAR)],
			size: 420,
			done: "Fermentando!",
		}),
		kstep("stop", "Fermente", "De 7 a 10 dias a uns 25 °C. Toque quando a fervura das bolhas acalmar.", {
			art: art("kt_grape_crushed"),
			zone: [7 / 14, 10 / 14],
			scale: [0, 14],
			unit: "dias",
			seconds: 7,
			size: 420,
			done: "Fermentou!",
		}),
		kstep("swipe", "Prense", "Gire o fuso para baixo e aperte as cascas: o vinho escorre pela bica.", {
			art: art("kt_press"),
			states: [art("kt_press_full")],
			dir: -90,
			count: 5,
			size: 420,
			done: "Prensado!",
		}),
		kstep("stop", "Encha a garrafa", "Toque para fechar a torneira quando chegar no gargalo.", {
			art: art("kt_bottle_empty"),
			states: [art("kt_bottle_full")],
			zone: [0.8, 0.92],
			scale: [0, 750],
			unit: "ml",
			seconds: 5,
			size: 360,
			done: "750 ml!",
		}),
		kstep("tap", "Arrolhe", "Toque na garrafa para pôr a rolha.", {
			art: art("kt_bottle_full"),
			states: [art("kt_bottle_corked")],
			spots: [0.5, 0.96],
			size: 360,
			done: "Vinho da casa!",
		}),
	],
	"sangria-da-casa": () => [
		kstep("cut", "Corte a maçã", "Em cubinhos, com casca.", {
			art: art("kt_apple"),
			states: [art("kt_apple_sliced")],
			lines: [0.5, 0.22, 0.5, 0.95, 0.24, 0.6, 0.76, 0.6],
			tool: art("kt_fish_knife"),
			size: 380,
			done: "Maçã picada!",
		}),
		kstep("add", "Na jarra", "Vinho da casa, a maçã e o refrigerante para dar gás.", {
			art: art("kt_pitcher"),
			states: [art("kt_pitcher_full")],
			items: [item(VINHO_CASA), item(MACA), item(REFRIGERANTE)],
			size: 360,
			done: "Que cor!",
		}),
		kstep("rub", "Misture devagar", "Mexa devagar para não perder o gás.", {
			art: art("kt_pitcher_full"),
			count: 6,
			slow: 1400,
			size: 360,
			done: "Misturada!",
		}),
		kstep("place", "Gelo", "Cubos de gelo na jarra.", {
			art: art("kt_pitcher_full"),
			items: [extra("kt_ice_cube", "Gelo")],
			spots: [0.4, 0.82, 0.55, 0.86, 0.48, 0.74],
			size: 360,
			done: "Bem gelada!",
		}),
	],
	"kit-harmonizacao": () => [
		kstep("add", "Monte a caixa", "O vinho, a tábua de queijos e as trufas, cada um no seu lugar.", {
			art: art("kt_gift_box"),
			states: [art("kt_gift_box_full")],
			items: [item(VINHO), item(TABUA), item(TRUFA)],
			size: 480,
			done: "Caixa montada!",
		}),
		kstep("swipe", "Feche com o laço", "Passe a fita de um lado ao outro.", {
			art: art("kt_gift_box_full"),
			dir: -1,
			count: 3,
			size: 480,
			done: "Presente perfeito!",
		}),
	],
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
