import type { MarketEraId } from "@/@types/economy";
import type {
	MarketSignChoice,
	MarketSignPalette,
	MarketStyleChoice,
	MarketStyleItem,
	MarketStyleKind,
	MarketStyleSnapshot,
	MarketStyleState,
} from "@/@types/market-style";
import { roundPrice } from "@/data/economy";
import { getMarketPaintCoinPrice, MARKET_PAINT_SWATCHES, normalizeHex } from "@/data/market-paint";

// "Estilo do mercado" (Lucas 08/11): the player dresses the shop — the floor, the walls, the staff uniform and the big
// letters on the back wall of the market (font, look, colours, neon, blinking). Each item is bought once (coins or
// diamonds) and then used freely; colours are free. Unity draws it (CheckoutMarketStyle.cs) and the picker
// (CheckoutMarketStylePanel.cs); the rules and prices live here.

export const CLASSIC_STYLE_ID = "classico";
export const STATIC_EFFECT_ID = "fixo";

const item = (
	kind: MarketStyleKind,
	id: string,
	name: string,
	coinFactor: number,
	diamondPrice: number,
	extra: Partial<MarketStyleItem> = {},
): MarketStyleItem => ({ id, kind, name, coinFactor, diamondPrice, ...extra });

const FLOOR = (id: string, name: string, extra: Partial<MarketStyleItem> = {}) => item("floor", id, name, 1, 20, extra);
const WALL = (id: string, name: string, extra: Partial<MarketStyleItem> = {}) => item("wall", id, name, 0.8, 15, extra);
const UNIFORM = (id: string, name: string, main: string, detail: string) =>
	item("uniform", id, name, 0.6, 10, { main, detail });

export const marketStyleItems: MarketStyleItem[] = [
	// Floors (Unity: Resources/CheckoutStyle/Floor_<id>).
	FLOOR(CLASSIC_STYLE_ID, "Mármore clássico", { free: true }),
	FLOOR("madeira-clara", "Madeira clara"),
	FLOOR("taco", "Taco espinha de peixe"),
	FLOOR("porcelanato", "Porcelanato cinza"),
	FLOOR("xadrez", "Xadrez", { tintable: true, color: "2E3236" }),
	FLOOR("cimento", "Cimento queimado"),
	FLOOR("ladrilho", "Ladrilho hidráulico"),
	FLOOR("granilite", "Granilite"),
	FLOOR("terracota", "Terracota"),
	FLOOR("vinil", "Vinil colorido", { tintable: true, color: "4FA3A5" }),
	FLOOR("marmore-escuro", "Mármore escuro", { coinFactor: 1.4, diamondPrice: 30 }),
	// Walls (the inside of the market; Resources/CheckoutStyle/Wall_<id>).
	WALL(CLASSIC_STYLE_ID, "Reboco clássico", { free: true }),
	WALL("tinta", "Tinta lisa", { tintable: true, color: "F2C230" }),
	WALL("metro", "Azulejo de metrô", { tintable: true, color: "F4F6F8" }),
	WALL("tijolinho", "Tijolinho"),
	WALL("ripado", "Madeira ripada"),
	WALL("pastilha", "Pastilhas", { tintable: true, color: "2F8FA0" }),
	WALL("listrado", "Papel listrado", { tintable: true, color: "E86A9E" }),
	WALL("floral", "Papel floral", { tintable: true, color: "7CB342" }),
	WALL("concreto", "Concreto"),
	WALL("lousa", "Lousa"),
	WALL("pedra", "Pedra", { coinFactor: 1.2, diamondPrice: 25 }),
	// Staff uniform: the original outfits, ready-made colour pairs, or any two colours.
	item("uniform", CLASSIC_STYLE_ID, "Uniformes originais", 0, 0, { free: true }),
	UNIFORM("marinho", "Marinho e dourado", "1D2B4F", "D3A53D"),
	UNIFORM("vermelho", "Vermelho e branco", "C0392B", "F4F6F8"),
	UNIFORM("verde", "Verde e creme", "1F7A4D", "F0E2B6"),
	UNIFORM("laranja", "Laranja e marinho", "E3762C", "1D2B4F"),
	UNIFORM("preto", "Preto e dourado", "1E2024", "D9A93E"),
	UNIFORM("ceu", "Céu e branco", "4A90D0", "F4F6F8"),
	UNIFORM("vinho", "Vinho e rosa", "7A1F35", "F2A7C0"),
	UNIFORM("roxo", "Roxo e amarelo", "5B3A8C", "F2C230"),
	UNIFORM("turquesa", "Turquesa e coral", "1E9A96", "F27D5E"),
	UNIFORM("mostarda", "Mostarda e marrom", "D9A520", "5A3A24"),
	item("uniform", "personalizado", "Cores livres", 1.5, 30, { tintable: true, main: "2F6FA8", detail: "F2C230" }),
	// Sign fonts (Resources/CheckoutStyle/Fonts).
	item("font", CLASSIC_STYLE_ID, "Clássica", 0, 0, { free: true }),
	item("font", "redonda", "Redonda", 0.5, 10),
	item("font", "esportiva", "Esportiva", 0.5, 10),
	item("font", "elegante", "Elegante", 0.5, 10),
	item("font", "moderna", "Moderna", 0.5, 10),
	item("font", "digital", "Digital", 0.5, 10),
	item("font", "pesada", "Pesada", 0.5, 10),
	item("font", "fina", "Fina", 0.5, 10),
	// Sign looks.
	item("look", CLASSIC_STYLE_ID, "Dourado clássico", 0, 0, { free: true }),
	item("look", "liso", "Letra pintada", 0.6, 10, { note: "Uma cor, sem relevo" }),
	item("look", "caixa", "Letra caixa 3D", 0.8, 15, { note: "Frente e lateral em duas cores" }),
	item("look", "contorno", "Contorno", 0.8, 15, { note: "Letra com borda grossa" }),
	item("look", "degrade", "Degradê", 0.8, 15, { note: "Uma cor em cima, outra embaixo" }),
	item("look", "colorido", "Letras coloridas", 1, 20, { note: "Cada letra de uma cor" }),
	item("look", "neon", "Neon", 1.5, 25, { note: "Tubo que brilha, de dia e de noite" }),
	item("look", "neon-placa", "Neon na placa", 1.8, 30, { note: "Neon sobre uma placa escura" }),
	item("look", "lampadas", "Letreiro de lâmpadas", 1.8, 30, { note: "Moldura de lâmpadas de teatro" }),
	// Sign effects (all loop forever; "speed" picks how fast).
	item("effect", STATIC_EFFECT_ID, "Fixo", 0, 0, { free: true }),
	item("effect", "pulsar", "Pulsar", 0.6, 15, { note: "Acende e apaga devagar" }),
	item("effect", "piscar", "Piscar", 0.6, 15, { note: "Liga e desliga" }),
	item("effect", "falhando", "Neon falhando", 0.8, 15, { note: "Uma letra pisca de vez em quando" }),
	item("effect", "letra", "Letra por letra", 0.8, 15, { note: "Acende uma letra de cada vez" }),
	item("effect", "onda", "Onda", 0.8, 15, { note: "As letras pulam em sequência" }),
	item("effect", "alternar", "Alternar cores", 0.8, 15, { note: "Troca entre as duas cores" }),
	item("effect", "arco-iris", "Arco-íris", 1, 20, { note: "Passa por todas as cores" }),
	item("effect", "brilho", "Brilho passando", 0.8, 15, { note: "Um reflexo corre pelas letras" }),
];

export const marketSignPalettes: MarketSignPalette[] = [
	{ id: "arco-iris", name: "Arco-íris", colors: ["E53935", "FB8C00", "FDD835", "43A047", "1E88E5", "8E24AA"] },
	{ id: "pastel", name: "Pastel", colors: ["F8B4C4", "FFD59E", "FFF3A3", "B8E6C1", "A9D4F5", "D2B8F0"] },
	{ id: "mercado", name: "Cores do mercado", colors: ["1D2B4F", "D3A53D", "C0392B", "1F7A4D"] },
	{ id: "tropical", name: "Tropical", colors: ["FF6F61", "FFC93C", "2EC4B6", "7BD389", "FF9F1C"] },
	{ id: "infantil", name: "Brinquedo", colors: ["E53935", "1E88E5", "FDD835", "43A047"] },
	{ id: "por-do-sol", name: "Pôr do sol", colors: ["FF5E62", "FF9966", "FFC371", "C06C84", "6C5B7B"] },
];

/** Where each part exists: floor and walls need an inside (Späti and up), the big sign the market building. */
const INSIDE_ERAS: MarketEraId[] = ["spati", "quitanda", "minimercado", "mercadinho", "supermercado", "hipermercado", "rede"];
const SIGN_ERAS: MarketEraId[] = ["mercadinho", "supermercado", "hipermercado", "rede"];
export const isMarketStyleUnlocked = (eraId: MarketEraId | undefined) => INSIDE_ERAS.includes(eraId ?? "mesinha");
export const isMarketSignStyleUnlocked = (eraId: MarketEraId | undefined) => SIGN_ERAS.includes(eraId ?? "mesinha");

export const SIGN_SPEEDS = [0, 1, 2] as const;

export function getMarketStyleItem(kind: MarketStyleKind, id: string) {
	return marketStyleItems.find((entry) => entry.kind === kind && entry.id === id) ?? null;
}

export const styleKey = (kind: MarketStyleKind, id: string) => `${kind}:${id}`;

export function getMarketStyleCoinPrice(entry: MarketStyleItem, eraId: MarketEraId | undefined) {
	if (entry.free) return 0;
	return roundPrice(getMarketPaintCoinPrice(eraId) * entry.coinFactor);
}

export function createMarketSignChoice(): MarketSignChoice {
	return { font: CLASSIC_STYLE_ID, look: CLASSIC_STYLE_ID, effect: STATIC_EFFECT_ID, main: "", second: "", palette: "arco-iris", speed: 1 };
}

export function createMarketStyleState(): MarketStyleState {
	return {
		floor: CLASSIC_STYLE_ID,
		floorColor: "",
		wall: CLASSIC_STYLE_ID,
		wallColor: "",
		uniform: CLASSIC_STYLE_ID,
		uniformMain: "",
		uniformDetail: "",
		sign: createMarketSignChoice(),
		owned: [],
		purchases: 0,
	};
}

const pickId = (kind: MarketStyleKind, value: unknown, fallback: string) =>
	typeof value === "string" && getMarketStyleItem(kind, value) ? value : fallback;
const hexOr = (value: unknown, fallback = "") => normalizeHex(value) ?? fallback;

/**
 * A choice cleaned up: unknown ids fall back to `base`, colours only stay where they mean something (a tintable floor
 * or wall, the free-colour uniform, a non-classic sign) and preset uniforms always wear their own pair.
 */
export function normalizeMarketStyleChoice(value: unknown, base: MarketStyleChoice = createMarketStyleState()): MarketStyleChoice {
	const raw = (value ?? {}) as Partial<MarketStyleChoice>;
	const rawSign = (raw.sign ?? {}) as Partial<MarketSignChoice>;
	const floor = pickId("floor", raw.floor, base.floor);
	const wall = pickId("wall", raw.wall, base.wall);
	const uniform = pickId("uniform", raw.uniform, base.uniform);
	const floorItem = getMarketStyleItem("floor", floor);
	const wallItem = getMarketStyleItem("wall", wall);
	const uniformItem = getMarketStyleItem("uniform", uniform);
	const look = pickId("look", rawSign.look, base.sign.look);
	const classicSign = look === CLASSIC_STYLE_ID;
	const speed = Math.round(Number(rawSign.speed));
	return {
		floor,
		floorColor: floorItem?.tintable ? hexOr(raw.floorColor, floorItem.color) : "",
		wall,
		wallColor: wallItem?.tintable ? hexOr(raw.wallColor, wallItem.color) : "",
		uniform,
		uniformMain: uniformItem?.tintable ? hexOr(raw.uniformMain, uniformItem.main) : (uniformItem?.main ?? ""),
		uniformDetail: uniformItem?.tintable ? hexOr(raw.uniformDetail, uniformItem.detail) : (uniformItem?.detail ?? ""),
		sign: {
			font: pickId("font", rawSign.font, base.sign.font),
			look,
			effect: pickId("effect", rawSign.effect, base.sign.effect),
			main: classicSign ? "" : hexOr(rawSign.main, "FFD54F"),
			second: classicSign ? "" : hexOr(rawSign.second, "E53935"),
			palette: marketSignPalettes.some((entry) => entry.id === rawSign.palette) ? (rawSign.palette as string) : "arco-iris",
			speed: speed >= 0 && speed <= 2 ? speed : 1,
		},
	};
}

/** Saves from before the feature and anything malformed: the classic look, nothing owned. */
export function normalizeMarketStyleState(value: unknown): MarketStyleState {
	const raw = (value ?? {}) as Partial<MarketStyleState>;
	const owned = (Array.isArray(raw.owned) ? raw.owned : [])
		.filter((key): key is string => typeof key === "string")
		.filter((key) => {
			const [kind, id] = key.split(":");
			const entry = getMarketStyleItem(kind as MarketStyleKind, id ?? "");
			return entry !== null && !entry.free;
		})
		.filter((key, index, list) => list.indexOf(key) === index);
	const choice = normalizeMarketStyleChoice(raw);
	// Something worn that is not owned (a broken save): back to the free one of that kind.
	const has = (kind: MarketStyleKind, id: string) => getMarketStyleItem(kind, id)?.free || owned.includes(styleKey(kind, id));
	const fixed = normalizeMarketStyleChoice(
		{
			...choice,
			floor: has("floor", choice.floor) ? choice.floor : CLASSIC_STYLE_ID,
			wall: has("wall", choice.wall) ? choice.wall : CLASSIC_STYLE_ID,
			uniform: has("uniform", choice.uniform) ? choice.uniform : CLASSIC_STYLE_ID,
			sign: {
				...choice.sign,
				font: has("font", choice.sign.font) ? choice.sign.font : CLASSIC_STYLE_ID,
				look: has("look", choice.sign.look) ? choice.sign.look : CLASSIC_STYLE_ID,
				effect: has("effect", choice.sign.effect) ? choice.sign.effect : STATIC_EFFECT_ID,
			},
		},
		createMarketStyleState(),
	);
	return { ...fixed, owned, purchases: Math.max(0, Math.floor(Number(raw.purchases) || 0)) };
}

/** The items of `choice` the player still has to buy (free and owned ones are left out). */
export function getUnownedStyleItems(state: MarketStyleState, choice: MarketStyleChoice) {
	const wanted: [MarketStyleKind, string][] = [
		["floor", choice.floor],
		["wall", choice.wall],
		["uniform", choice.uniform],
		["font", choice.sign.font],
		["look", choice.sign.look],
		["effect", choice.sign.effect],
	];
	return wanted
		.map(([kind, id]) => getMarketStyleItem(kind, id))
		.filter((entry): entry is MarketStyleItem => entry !== null && !entry.free && !state.owned.includes(styleKey(entry.kind, entry.id)));
}

export function getMarketStylePrice(state: MarketStyleState, choice: MarketStyleChoice, eraId: MarketEraId | undefined) {
	const items = getUnownedStyleItems(state, choice);
	return {
		items,
		coins: items.reduce((sum, entry) => sum + getMarketStyleCoinPrice(entry, eraId), 0),
		diamonds: items.reduce((sum, entry) => sum + entry.diamondPrice, 0),
	};
}

const sameChoice = (a: MarketStyleChoice, b: MarketStyleChoice) =>
	JSON.stringify(normalizeMarketStyleChoice(a)) === JSON.stringify(normalizeMarketStyleChoice(b));
export const isSameMarketStyle = sameChoice;

/** What Unity gets in every snapshot (style: CheckoutMarketStyle + CheckoutMarketStylePanel). */
export function createMarketStyleSnapshot(state: MarketStyleState | undefined, eraId: MarketEraId | undefined): MarketStyleSnapshot {
	const style = normalizeMarketStyleState(state);
	const { owned, purchases: _purchases, ...choice } = style;
	return {
		...choice,
		owned,
		insideUnlocked: isMarketStyleUnlocked(eraId),
		signUnlocked: isMarketSignStyleUnlocked(eraId),
		coinBase: getMarketPaintCoinPrice(eraId),
		items: marketStyleItems.map((entry) => ({ ...entry, coinPrice: getMarketStyleCoinPrice(entry, eraId) })),
		palettes: marketSignPalettes,
		swatches: MARKET_PAINT_SWATCHES,
	};
}
