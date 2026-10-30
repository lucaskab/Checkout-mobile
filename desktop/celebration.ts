import type { GameCelebration } from "@/@types/game";
import { getMarketEra, getNextMarketEra } from "@/data/economy";
import { getShopItemIcon } from "@/data/game-icon-assets";
import { getMarketLot } from "@/data/market-lots";
import { itemCatalog } from "@/data/market-products";
import { productionRecipes, productionSectors } from "@/data/production-sectors";
import { getFixtureName, shelfTypes } from "@/data/shelf-types";
import { shopItems } from "@/data/shop-items";
import { getLotClearExperience, getMissingLots } from "@/services/market-lots";
import { decorIcon, fmt, gameIcon, type State } from "./view-kit";
import { decorTiers, getFixtureTierDefinition } from "@/data/fixture-tiers";
import { getShelfCapacity } from "@/data/shelf-capacity";
import { getShelfFixtureKind } from "@/services/fixture-tiers";

// The conquest celebration (Township's "new area!", Hay Day's "building ready!"): a medal with the thing
// conquered, a ribbon, what it changes for the player in two or three chips and a button to use it. One at a
// time from state.celebrations (src/services/celebrations.ts); Unity draws it (CheckoutDesktopHUD.Conquest.cs)
// and, for a lot, first flies the camera over it for the dust, the light and the confetti (CheckoutLotSites).

export type CelebrationChip = { icon: string; text: string };

export type CelebrationView = {
	/** Changes with every celebration (Unity replays the animation). */
	key: string;
	/** Id given back to dismissCelebration. */
	id: string;
	kind: GameCelebration["kind"];
	headline: string;
	title: string;
	subtitle: string;
	icon: string;
	/** Colour of the medal ring and the ribbon (hex). */
	tint: string;
	chips: CelebrationChip[];
	/** Optional second button that closes the celebration and opens a page. */
	button: string;
	route: string;
	/** Lot to fly over and light up (lot celebrations only). */
	lotId: string;
};

function view(celebration: GameCelebration, fields: Omit<CelebrationView, "key" | "id" | "kind" | "lotId"> & { lotId?: string }) {
	return { key: celebration.id, id: celebration.id, kind: celebration.kind, lotId: "", ...fields } satisfies CelebrationView;
}

function lotView(state: State, celebration: GameCelebration): CelebrationView | null {
	const lot = getMarketLot(celebration.targetId);
	if (!lot) return null;
	const next = getNextMarketEra(state.era.id);
	const missing = next ? getMissingLots(state.lots, next.id) : [];
	const owned = state.lots?.cleared.length ?? 0;
	const xp = getLotClearExperience(lot);
	const chips: CelebrationChip[] = [
		{ icon: gameIcon("key"), text: `${fmt(owned)} ${owned === 1 ? "terreno seu" : "terrenos seus"}` },
		...(xp > 0 ? [{ icon: gameIcon("crown"), text: `+${fmt(xp)} XP da limpeza` }] : []),
	];
	if (next) chips.push({ icon: gameIcon("market"), text: missing.length ? missing.length === 1 ? `${next.name}: falta 1` : `${next.name}: faltam ${missing.length}` : `Pronto para ${next.name}` });
	return view(celebration, {
		headline: "TERRENO LIBERADO!",
		title: `Lote ${lot.id} é seu`,
		subtitle: `${lot.ruinName} virou chão limpo: mais espaço para o mercado crescer.`,
		icon: "Game/lot_lock_open",
		tint: "3F9E52",
		chips,
		button: next ? "Ver expansões" : "",
		route: next ? "!loja:expansoes" : "",
		lotId: lot.id,
	});
}

function eraView(state: State, celebration: GameCelebration): CelebrationView | null {
	const era = getMarketEra(celebration.targetId as never);
	if (!era) return null;
	const fixtures = shelfTypes.filter((shelf) => shelf.eraId === era.id);
	const products = itemCatalog.filter(
		(product) => product.unlockEra === era.id && product.unlockLevel <= state.market.level && product.acquisition !== "production",
	);
	const chips: CelebrationChip[] = [
		{ icon: gameIcon("customers"), text: `Até ${fmt(era.maxCustomersPerTurn)} clientes por dia` },
		...(fixtures.length ? [{ icon: gameIcon("shelf"), text: `Novo móvel: ${fixtures.map((shelf) => getFixtureName(shelf.id, era.id)).join(", ")}` }] : []),
		...(products.length ? [{ icon: gameIcon("package"), text: products.length === 1 ? "1 produto para vender" : `${fmt(products.length)} produtos para vender` }] : []),
	];
	return view(celebration, {
		headline: "NOVA EXPANSÃO!",
		title: era.name,
		subtitle: "Seu mercado cresceu: mais clientes, mais espaço e coisas novas para vender.",
		icon: gameIcon("market"),
		tint: "E0A441",
		chips: chips.slice(0, 3),
		button: fixtures.length ? "Comprar móveis" : "Ver produtos",
		route: fixtures.length ? "!loja:moveis" : "!products",
	});
}

function sectorView(state: State, celebration: GameCelebration): CelebrationView | null {
	const sector = productionSectors.find((item) => item.id === celebration.targetId);
	if (!sector) return null;
	const recipes = productionRecipes.filter((recipe) => recipe.sectorId === sector.id && recipe.requiredLevel <= state.market.level);
	const names = recipes
		.map((recipe) => itemCatalog.find((product) => product.id === recipe.outputProductId)?.name)
		.filter(Boolean)
		.slice(0, 2);
	return view(celebration, {
		headline: "SETOR PRONTO!",
		title: sector.name,
		subtitle: `${sector.subtitle}: produza aqui e venda no balcão do setor.`,
		icon: decorIcon(`sector-${sector.id}`),
		tint: "C0612B",
		chips: [
			...(recipes.length
				? [{ icon: gameIcon("conveyor"), text: recipes.length === 1 ? `1 receita: ${names.join(", ")}` : `${fmt(recipes.length)} receitas: ${names.join(", ")}` }]
				: []),
			{ icon: gameIcon("shelf"), text: "Balcão de vendas com 4 espaços" },
		],
		button: "Produzir",
		route: "!sectors",
	});
}

function shelfView(state: State, celebration: GameCelebration): CelebrationView | null {
	const shelf = shelfTypes.find((item) => item.id === celebration.targetId);
	if (!shelf) return null;
	return view(celebration, {
		headline: "MÓVEL PRONTO!",
		title: getFixtureName(shelf.id, state.era.id),
		subtitle: `Os montadores terminaram. Agora dá para vender ${shelf.holds}.`,
		icon: gameIcon("shelf"),
		tint: "2E8CAE",
		chips: [{ icon: gameIcon("package"), text: "4 espaços para produtos" }],
		button: "Abastecer",
		route: "!store",
	});
}

function shopView(celebration: GameCelebration): CelebrationView | null {
	const item = shopItems.find((entry) => entry.id === celebration.targetId);
	if (!item) return null;
	return view(celebration, {
		headline: "INSTALADO!",
		title: item.name,
		subtitle: item.description,
		icon: gameIcon(getShopItemIcon(item.id)),
		tint: "8B5C9E",
		chips: [],
		button: "",
		route: "",
	});
}

/** "Seu móvel evoluiu!": a fixture or a machine took its next look (targetId "shelf:<id>:<tier>" / "decor:<id>:<tier>"). */
function tierView(state: State, celebration: GameCelebration): CelebrationView | null {
	const [group, id, tierText] = celebration.targetId.split(":");
	const tier = Number(tierText);
	if (group === "shelf") {
		const kind = getShelfFixtureKind(id);
		if (!kind) return null;
		const definition = getFixtureTierDefinition(kind, tier);
		const capacity = getShelfCapacity(Math.max(0, tier - 1));
		return view(celebration, {
			headline: "SEU MÓVEL EVOLUIU!",
			title: definition.name,
			subtitle: `${getFixtureName(id, state.era.id)}: novo visual e mais espaço para os produtos.`,
			icon: gameIcon("shelf"),
			tint: "1D2B4F",
			chips: [
				{ icon: gameIcon("package"), text: `${capacity} por produto` },
				{ icon: gameIcon("shelf"), text: `${fmtMetres(definition.width)} × ${fmtMetres(definition.depth)} m` },
			],
			button: "",
			route: "",
		});
	}
	const tiers = decorTiers[id];
	const definition = tiers?.[tier - 1];
	if (!definition) return null;
	return view(celebration, {
		headline: "SEU MÓVEL EVOLUIU!",
		title: definition.name,
		subtitle: "Todos os que você colocou ganharam o novo visual.",
		icon: decorIcon(id),
		tint: "1D2B4F",
		chips: [{ icon: gameIcon("shelf"), text: `${fmtMetres(definition.width)} × ${fmtMetres(definition.depth)} m` }],
		button: "",
		route: "",
	});
}

const fmtMetres = (value: number) => value.toLocaleString("pt-BR", { maximumFractionDigits: 2 });

/** The next conquest to celebrate (oldest first), or null. */
export function celebrationView(state: State): CelebrationView | null {
	for (const celebration of state.celebrations ?? []) {
		const built =
			celebration.kind === "lot"
				? lotView(state, celebration)
				: celebration.kind === "era"
					? eraView(state, celebration)
					: celebration.kind === "sector"
						? sectorView(state, celebration)
						: celebration.kind === "shelf"
							? shelfView(state, celebration)
							: celebration.kind === "tier"
								? tierView(state, celebration)
								: shopView(celebration);
		if (built) return built;
	}
	return null;
}
