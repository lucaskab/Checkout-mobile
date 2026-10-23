import type {
	InteriorDecorDefinition,
	InteriorItem,
	InteriorState,
} from "@/@types/interior";

// Decorations for the build mode shop. Ids match the templates in Unity's Interior Kit.
export const interiorDecor: InteriorDecorDefinition[] = [
	{ id: "basket-stack", name: "Cestinhas", description: "Pilha de cestinhas na entrada.", coinPrice: 600, requiredLevel: 1, zone: "inside" },
	{ id: "plant-small", name: "Vaso de planta", description: "Um verdinho para alegrar o corredor.", coinPrice: 800, requiredLevel: 1, zone: "inside" },
	{ id: "balloons", name: "Arco de balões", description: "Festa de inauguração todo dia.", diamondPrice: 15, requiredLevel: 1, zone: "inside" },
	{ id: "floor-lamp", name: "Luminária", description: "Luz dourada e aconchegante.", coinPrice: 1_200, requiredLevel: 4, zone: "inside" },
	{ id: "bench", name: "Banco de descanso", description: "Para quem espera na fila do caixa.", coinPrice: 1_500, requiredLevel: 5, zone: "inside" },
	{ id: "cart-corral", name: "Carrinhos de Compras", description: "Melhoria: com os carrinhos no mapa, cada cliente pode levar +1 produto.", coinPrice: 4_000, requiredLevel: 7, zone: "inside", effect: { basketItems: 1 } },
	{ id: "plant-palm", name: "Palmeira", description: "Planta grande em vaso dourado.", coinPrice: 2_500, requiredLevel: 8, zone: "inside" },
	{ id: "promo-stand", name: "Expositor de ofertas", description: "Pilha de promoção com placa.", coinPrice: 3_000, requiredLevel: 10, zone: "inside" },
	{ id: "water-cooler", name: "Bebedouro", description: "Água fresca para os clientes.", coinPrice: 1_800, requiredLevel: 12, zone: "inside" },
	{ id: "gumball", name: "Máquina de chiclete", description: "Melhoria: 1 em cada 4 clientes compra um chiclete (+2 moedas cada, mais nos níveis altos; quase tudo lucro). Até 3 máquinas.", coinPrice: 2_200, requiredLevel: 13, zone: "inside", effect: { play: { chance: 0.25, coins: 2, maxPlaced: 3 } } },
	{ id: "flower-stand", name: "Banca de flores", description: "Baldes de flores coloridas.", coinPrice: 4_000, requiredLevel: 14, zone: "inside" },
	{ id: "watermelon-pile", name: "Ilha de melancias", description: "Montanha de melancias da estação.", coinPrice: 3_500, requiredLevel: 16, zone: "inside" },
	{ id: "claw-machine", name: "Máquina de pelúcia", description: "Melhoria: 1 em cada 5 clientes joga (+6 moedas por jogada, mais nos níveis altos; quase tudo lucro). Dentro ou fora do mercado. Até 3 máquinas.", diamondPrice: 25, requiredLevel: 23, zone: "both", effect: { play: { chance: 0.2, coins: 6, maxPlaced: 3 } } },
	{ id: "atm", name: "Caixa eletrônico", description: "Melhoria: os clientes sacam dinheiro e gastam +15% no mercado.", coinPrice: 15_000, requiredLevel: 19, zone: "inside", effect: { budget: 0.15 } },
	{ id: "vending-machine", name: "Máquina de bebidas", description: "Melhoria: 1 em cada 5 clientes compra uma bebida gelada (+4 moedas cada, mais nos níveis altos). Dentro ou fora do mercado. Até 3 máquinas.", coinPrice: 7_500, requiredLevel: 11, zone: "both", effect: { play: { chance: 0.2, coins: 4, maxPlaced: 3 } } },
	{ id: "photo-booth", name: "Cabine de fotos", description: "Melhoria: 1 em cada 8 clientes tira fotos na cabine (+9 moedas cada, mais nos níveis altos). Dentro ou fora do mercado. Até 2 cabines.", diamondPrice: 30, requiredLevel: 18, zone: "both", effect: { play: { chance: 0.125, coins: 9, maxPlaced: 2 } } },
	{ id: "digital-totem", name: "Totem digital", description: "Tela de ofertas animada.", diamondPrice: 30, requiredLevel: 26, zone: "inside" },
	// Decor v4 (22/10/2026): new inside decorations (coins and diamonds).
	{ id: "umbrella-stand", name: "Porta-guarda-chuvas", description: "Balde de latão com guarda-chuvas coloridos.", coinPrice: 900, requiredLevel: 2, zone: "inside" },
	{ id: "monstera", name: "Costela-de-adão", description: "Folhonas recortadas num vaso de cerâmica.", coinPrice: 1_400, requiredLevel: 3, zone: "inside" },
	{ id: "can-pyramid", name: "Pirâmide de latas", description: "Latas empilhadas em promoção, com faixa colorida.", coinPrice: 2_400, requiredLevel: 7, zone: "inside" },
	{ id: "fruit-pyramid", name: "Pirâmide de frutas", description: "Caixotes de maçãs, laranjas e limões em degraus.", coinPrice: 3_200, requiredLevel: 9, zone: "inside" },
	{ id: "tasting-table", name: "Mesa de degustação", description: "Queijos, pães e uvas para provar.", coinPrice: 3_600, requiredLevel: 14, zone: "inside" },
	{ id: "wine-barrel", name: "Barril de vinhos", description: "Barril de carvalho com garrafas e taças.", coinPrice: 4_500, requiredLevel: 18, zone: "inside" },
	{ id: "neon-cart", name: "Neon de carrinho", description: "Carrinho de compras em neon que pisca.", diamondPrice: 20, requiredLevel: 10, zone: "inside" },
	{ id: "giant-teddy", name: "Ursão de pelúcia", description: "Ursão gigante de laço, a alegria da criançada.", diamondPrice: 25, requiredLevel: 12, zone: "inside" },
	{ id: "party-tree", name: "Árvore de festa", description: "Árvore enfeitada com bolas e luzinhas piscando.", diamondPrice: 30, requiredLevel: 15, zone: "inside" },
	{ id: "aquarium", name: "Aquário", description: "Peixinhos coloridos nadando entre plantas.", diamondPrice: 40, requiredLevel: 20, zone: "inside" },
	// Outside the market: the plaza and footways of the city block.
	{ id: "flower-bed", name: "Canteiro de flores", description: "Floreira comprida para a calçada.", coinPrice: 1_500, requiredLevel: 1, zone: "outside" },
	{ id: "bike-rack", name: "Bicicletário", description: "Vagas para as bicicletas dos clientes.", coinPrice: 1_200, requiredLevel: 3, zone: "outside" },
	{ id: "park-bench", name: "Banco de praça", description: "Madeira e ferro fundido, clássico.", coinPrice: 1_800, requiredLevel: 2, zone: "outside" },
	{ id: "tree-planter", name: "Árvore com canteiro", description: "Sombra fresquinha na praça.", coinPrice: 2_600, requiredLevel: 4, zone: "outside" },
	{ id: "street-lamp", name: "Poste de luz", description: "Luz dourada com bandeirolas.", coinPrice: 2_200, requiredLevel: 6, zone: "outside" },
	{ id: "recycle-bins", name: "Lixeiras de reciclagem", description: "Quatro cores para separar o lixo.", coinPrice: 1_400, requiredLevel: 9, zone: "outside" },
	{ id: "parasol-table", name: "Mesa com guarda-sol", description: "Para um lanche ao ar livre.", coinPrice: 3_200, requiredLevel: 11, zone: "outside" },
	{ id: "ice-cream-cart", name: "Carrinho de sorvete", description: "Sorvete geladinho na praça.", diamondPrice: 20, requiredLevel: 20, zone: "outside" },
	{ id: "billboard", name: "Placa de ofertas", description: "Anuncie as promoções da semana.", coinPrice: 4_500, requiredLevel: 15, zone: "outside" },
	{ id: "fountain", name: "Fonte", description: "Fonte de dois andares com água corrente.", diamondPrice: 45, requiredLevel: 21, zone: "outside" },
	{ id: "popcorn-cart", name: "Carrinho de pipoca", description: "Cheirinho de pipoca na entrada.", coinPrice: 5_000, requiredLevel: 17, zone: "outside" },
	{ id: "coffee-kiosk", name: "Quiosque de café", description: "Melhoria: 1 em cada 4 clientes leva um café e um docinho (+5 moedas cada, mais nos níveis altos). Até 2 quiosques.", coinPrice: 12_000, requiredLevel: 15, zone: "outside", effect: { play: { chance: 0.25, coins: 5, maxPlaced: 2 } } },
	{ id: "festoon-pergola", name: "Pérgola com luzes", description: "Varal de lâmpadas sobre a praça.", coinPrice: 6_500, requiredLevel: 12, zone: "outside" },
	{ id: "kiddie-ride", name: "Carrinho de mola", description: "Brinquedo para a criançada.", diamondPrice: 35, requiredLevel: 25, zone: "outside" },
	// Decor v4 (22/10/2026): new plaza decorations.
	{ id: "picket-fence", name: "Cerquinha florida", description: "Cerca de madeira branca com flores.", coinPrice: 900, requiredLevel: 1, zone: "outside" },
	{ id: "hedge-planter", name: "Jardineira com cerca viva", description: "Arbusto podadinho numa jardineira de madeira.", coinPrice: 1_600, requiredLevel: 2, zone: "outside" },
	{ id: "bird-bath", name: "Bebedouro de passarinhos", description: "Pedra entalhada com passarinhos.", coinPrice: 1_300, requiredLevel: 4, zone: "outside" },
	{ id: "picnic-table", name: "Mesa de piquenique", description: "Mesa de madeira com toalha xadrez.", coinPrice: 2_400, requiredLevel: 5, zone: "outside" },
	{ id: "veggie-garden", name: "Horta", description: "Canteiros com alface, cenoura e tomate.", coinPrice: 2_800, requiredLevel: 8, zone: "outside" },
	{ id: "swing-set", name: "Balanço", description: "Balanço de madeira para a criançada.", coinPrice: 6_000, requiredLevel: 13, zone: "outside" },
	{ id: "hotdog-cart", name: "Carrinho de cachorro-quente", description: "Salsichas na chapa e guarda-sol listrado.", coinPrice: 5_500, requiredLevel: 16, zone: "outside" },
	{ id: "topiary-animal", name: "Arbusto em forma de bicho", description: "Um elefantinho podado com capricho.", diamondPrice: 30, requiredLevel: 16, zone: "outside" },
	{ id: "gazebo", name: "Coreto", description: "Coreto de ferro e madeira com luzinhas.", diamondPrice: 50, requiredLevel: 22, zone: "outside" },
	{ id: "carousel", name: "Mini carrossel", description: "Carrossel de cavalinhos que gira.", diamondPrice: 60, requiredLevel: 24, zone: "outside" },
];

export const functionalInteriorTypes = ["shelf", "sector", "checkout", "kiosk"] as const;

export function getInteriorDecor(id: string) {
	return interiorDecor.find((item) => item.id === id) ?? null;
}

export const initialInteriorState: InteriorState = { items: [], owned: {} };

/**
 * What the shop comes with: the checkout, the produce crates and the drinks cooler (the fixtures of the
 * sidewalk table, src/data/shelf-types.ts). Nothing stands inside yet: once the market has a floor, the
 * player places these pieces in build mode.
 */
export const starterInteriorPieces: { id: string; type: string }[] = [
	{ id: "checkout:main", type: "checkout" },
	{ id: "shelf:produce", type: "shelf" },
	{ id: "shelf:drinks", type: "shelf" },
];

export function createStarterInteriorState(): InteriorState {
	return {
		items: starterInteriorPieces.map((piece) => ({ ...piece, x: 0, z: 0, rot: 0, stored: true })),
		owned: {},
	};
}

/** Shop furniture the player owns but has not placed yet (the market cannot open meanwhile). */
export function getWaitingInteriorPieces(interior: InteriorState | undefined) {
	return (interior?.items ?? []).filter(
		(item) =>
			item.stored && (functionalInteriorTypes as readonly string[]).includes(item.type),
	);
}

const finite = (v: unknown, limit: number) =>
	typeof v === "number" && Number.isFinite(v) && Math.abs(v) <= limit;

/** Keeps only well-formed items; decorations never exceed how many were bought. */
export function sanitizeInteriorItems(
	value: unknown,
	owned: Record<string, number>,
): InteriorItem[] | null {
	if (!Array.isArray(value) || value.length > 300) return null;
	const ids = new Set<string>();
	const placed: Record<string, number> = {};
	const items: InteriorItem[] = [];
	for (const raw of value) {
		if (!raw || typeof raw !== "object") return null;
		const item = raw as Partial<InteriorItem>;
		if (typeof item.id !== "string" || !item.id || item.id.length > 40 || ids.has(item.id)) return null;
		if (typeof item.type !== "string" || !item.type || item.type.length > 40) return null;
		if (!finite(item.x, 80) || !finite(item.z, 80) || !finite(item.rot, 100_000)) return null;
		const functional = (functionalInteriorTypes as readonly string[]).includes(item.type);
		const decor = functional ? null : getInteriorDecor(item.type);
		// Shop furniture stays inside; each decoration only goes where it belongs (some go either way).
		if (decor?.zone !== "both" && !!item.outside !== (decor?.zone === "outside")) return null;
		if (!functional) {
			if (!decor) return null;
			placed[item.type] = (placed[item.type] ?? 0) + 1;
			if (placed[item.type] > (owned[item.type] ?? 0)) return null;
		}
		ids.add(item.id);
		items.push({
			id: item.id,
			type: item.type,
			x: Math.round((item.x as number) * 1000) / 1000,
			z: Math.round((item.z as number) * 1000) / 1000,
			rot: (((item.rot as number) % 360) + 360) % 360,
			// Shop furniture can also wait in the stock (the starter pieces before the first build).
			...(item.stored ? { stored: true } : {}),
			...(item.outside ? { outside: true } : {}),
		});
	}
	return items;
}

export function normalizeInteriorState(value: unknown): InteriorState {
	if (!value || typeof value !== "object") return { items: [], owned: {} };
	const state = value as Partial<InteriorState>;
	const owned: Record<string, number> = {};
	if (state.owned && typeof state.owned === "object")
		for (const [id, count] of Object.entries(state.owned))
			if (getInteriorDecor(id) && typeof count === "number" && count > 0)
				owned[id] = Math.min(99, Math.floor(count));
	return { items: sanitizeInteriorItems(state.items, owned) ?? [], owned };
}
