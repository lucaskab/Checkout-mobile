import { describeFixtureProducts } from "@/data/fixture-products";
import { getFixtureName, getShelfType } from "@/data/shelf-types";
import { interiorDecor } from "@/data/interior-decor";
import { shopItemBuildDurations } from "@/data/interior-construction";
import { productionSectors } from "@/data/production-sectors";
import { shopCategories, shopItems } from "@/data/shop-items";
import { getShopCategoryIcon } from "@/data/game-icon-assets";
import {
	getNextShelfBuildStatus,
	getSectorBuildStatus,
	getShopItemBuildStatus,
	getStoredInteriorBuilds,
} from "@/services/interior-construction";
import { getInteriorBuildName } from "@/data/interior-construction";
import type { Routes } from ".";
import {
	act,
	button,
	type Button,
	type Card,
	card,
	decorIcon,
	fmt,
	gameIcon,
	page,
	type State,
} from "../view-kit";
import { buildCard, placeButton, shelfThumb } from "./build-cards";
import { eraCards } from "./eras";
import { lotCards } from "./lots";
import { getMarketEra, getNextMarketEra } from "@/data/economy";
import { routes as progress } from "./progress";
import { routes as upgrades } from "./upgrades";

// The market's shop: everything the player can buy, in one full-screen place split by category
// (like the shops of Township, Hay Day or Supermarket Simulator's computer). Unity draws it as a
// category rail + a grid of tiles (page.layout = "shop").

type Tab = { id: string; label: string; icon: string; hint: string };
const tabs: Tab[] = [
	{ id: "destaques", label: "Destaques", icon: gameIcon("gift"), hint: "O melhor da loja para o seu mercado agora" },
	{ id: "moveis", label: "Móveis e obras", icon: gameIcon("construction"), hint: "Prateleiras, setores e caixas · vão para o inventário e você escolhe o lugar" },
	{ id: "melhorias", label: "Melhorias", icon: gameIcon("toolbox"), hint: "Equipamentos e tecnologia que deixam o mercado mais rápido e lucrativo" },
	{ id: "equipe", label: "Equipe", icon: gameIcon("manager"), hint: "Contrate e treine funcionários" },
	{ id: "terrenos", label: "Terrenos", icon: gameIcon("key"), hint: "Compre os terrenos em volta do mercado e limpe o que tem neles · cada expansão precisa dos seus" },
	{ id: "expansoes", label: "Expansões", icon: gameIcon("market"), hint: "Da mesinha na calçada à rede de hipermercados · cada expansão traz mais lugares, clientes e vendas" },
	{ id: "decoracao", label: "Decoração", icon: gameIcon("plant"), hint: "Enfeites para dentro da loja e para a praça · vão para o inventário" },
	{ id: "moedas", label: "Moedas e diamantes", icon: gameIcon("diamond"), hint: "Reforce o caixa" },
];

const route = (tab: string, sub = "") => `~loja:${tab}${sub ? `:${sub}` : ""}`;
const chip = (label: string, tab: string, sub: string, active: boolean, icon = "") =>
	button(label, { route: route(tab, sub), variant: "secondary", active, icon });

// ------------------------------------------------------------------ furniture and works
const builtItems = Object.keys(shopItemBuildDurations);

function shelfCard(state: State) {
	const build = getNextShelfBuildStatus(state);
	if (!build.shelf) return null;
	return buildCard(state, {
		title: getFixtureName(build.shelf.id, state.era.id),
		icon: shelfThumb(build.shelf.id),
		subtitle: describeFixtureProducts(build.shelf.id, state.market.unlockedProductIds)
			? `Aceita: ${describeFixtureProducts(build.shelf.id, state.market.unlockedProductIds)}. Começa com quatro espaços de produto.`
			: `Os produtos dele chegam com: ${getMarketEra(getShelfType(build.shelf.id)?.eraId ?? state.era.id).name}.`,
		status: build,
		coins: { action: "unlockNextShelf", args: [], price: build.coinCost },
	});
}

function sectorCards(state: State) {
	return productionSectors.map((sector) => {
		const status = getSectorBuildStatus(state, sector.id);
		return buildCard(state, {
			title: sector.name,
			icon: decorIcon(`sector-${sector.id}`),
			subtitle: sector.description,
			status,
			coins: { action: "buildSector", args: [sector.id, "coins"], price: status.coinCost },
			diamonds: { action: "buildSector", args: [sector.id, "diamonds"], price: status.diamondCost },
			builtLine: "Produza em Produção.",
		});
	});
}

function checkoutCards(state: State) {
	return builtItems.flatMap((id) => {
		const item = shopItems.find((entry) => entry.id === id);
		const status = getShopItemBuildStatus(state, id);
		if (!item || !status) return [];
		const locked = state.market.level < item.level;
		const isDiamond = Boolean(item.diamondPrice);
		const price = item.diamondPrice ?? item.coinPrice ?? 0;
		return [
			buildCard(state, {
				title: item.name,
				icon: decorIcon(id === "self-checkout" ? "kiosk" : "checkout"),
				subtitle: item.description,
				status: locked && status.status === "available" ? { ...status, status: "locked", reason: `Nível ${item.level}` } : status,
				...(isDiamond
					? { diamonds: { action: "purchaseShopItem", args: [id, "diamonds"], price } }
					: { coins: { action: "purchaseShopItem", args: [id, "coins"], price } }),
			}),
		];
	});
}

function inventoryCard(state: State): Card | null {
	const stored = getStoredInteriorBuilds(state);
	if (stored.length === 0) return null;
	return card(`${stored.length} ${stored.length === 1 ? "item no inventário" : "itens no inventário"}`, {
		eyebrow: "PRONTO PARA COLOCAR",
		icon: gameIcon("package"),
		tone: "featured",
		subtitle: "Você comprou e ainda não colocou. Escolha o lugar no modo construir para os construtores começarem.",
		lines: stored.map((item) => `• ${getInteriorBuildName(item.kind, item.targetId)}`),
		buttons: [placeButton("Colocar agora")],
	});
}

function moveis(state: State, sub: string) {
	const cards: Card[] = [];
	const inventory = inventoryCard(state);
	if (inventory) cards.push(inventory);
	if (sub === "" || sub === "prateleiras") {
		const shelf = shelfCard(state);
		if (shelf) cards.push(shelf);
	}
	if (sub === "" || sub === "setores") cards.push(...sectorCards(state));
	if (sub === "" || sub === "caixas") cards.push(...checkoutCards(state));
	// Things to buy first, then the inventory/works, then what is already in the shop.
	const order = (c: Card) => (c.tone === "featured" ? -1 : c.tone === "" ? 0 : c.tone === "info" ? 1 : c.tone === "warning" ? 2 : c.tone === "locked" ? 3 : 4);
	cards.sort((a, b) => order(a) - order(b));
	return {
		cards,
		chips: [
			chip("Tudo", "moveis", "", sub === ""),
			chip("Prateleiras", "moveis", "prateleiras", sub === "prateleiras", gameIcon("shelf")),
			chip("Setores", "moveis", "setores", sub === "setores", gameIcon("conveyor")),
			chip("Caixas", "moveis", "caixas", sub === "caixas", gameIcon("calculator")),
		],
	};
}

// ------------------------------------------------------------------ decorations
function decoracao(state: State, sub: string) {
	const zone = sub === "fora" ? "outside" : "inside";
	const coins = state.coins;
	const diamonds = state.logistics.premiumCurrency;
	const cards = interiorDecor
		.filter((decor) => decor.zone === zone)
		.map((decor) => {
			const locked = state.market.level < decor.requiredLevel;
			const owned = state.interior.owned[decor.id] ?? 0;
			const useDiamonds = !decor.coinPrice;
			const price = (useDiamonds ? decor.diamondPrice : decor.coinPrice) ?? 0;
			return card(decor.name, {
				eyebrow: locked ? `NÍVEL ${decor.requiredLevel}` : zone === "outside" ? "PRAÇA" : "DENTRO DA LOJA",
				icon: decorIcon(decor.id),
				tone: locked ? "locked" : owned > 0 ? "success" : "",
				badge: owned > 0 ? `x${owned}` : "",
				subtitle: decor.description,
				buttons: [
					act(locked ? `Nível ${decor.requiredLevel}` : fmt(price), "purchaseDecor", [decor.id, useDiamonds ? "diamonds" : "coins"], {
						variant: useDiamonds ? "gem" : "coin",
						icon: locked ? "" : gameIcon(useDiamonds ? "diamond" : "coin"),
						enabled: !locked && (useDiamonds ? diamonds >= price : coins >= price),
						ok: `${decor.name} comprado! Coloque no modo construir.`,
						fail: locked ? `Nível ${decor.requiredLevel}` : useDiamonds ? "Diamantes insuficientes" : "Moedas insuficientes",
					}),
					...(owned > 0 ? [placeButton("Colocar")] : []),
				],
			});
		});
	return {
		cards,
		chips: [
			chip("Dentro da loja", "decoracao", "dentro", zone === "inside", gameIcon("market")),
			chip("Praça", "decoracao", "fora", zone === "outside", gameIcon("garden")),
		],
	};
}

// ------------------------------------------------------------------ highlights
function destaques(state: State) {
	const picks: Card[] = [];
	const inventory = inventoryCard(state);
	if (inventory) picks.push(inventory);
	// The next expansion (or its obra) is the biggest thing to buy.
	const era = eraCards(state, { roadmap: false })[1];
	if (era && (era.tone === "featured" || era.tone === "warning")) picks.push({ ...era, eyebrow: "EXPANSÃO" });
	// The land the next expansion needs (to buy, to clear or being cleared) comes right after.
	const land = lotCards(state).find((c) => c.eyebrow === "LIMPANDO" || c.eyebrow.startsWith("COMPRADO") || (c.eyebrow === "À VENDA" && c.lines.some((l) => l.includes(getNextMarketEra(state.era.id)?.name ?? "—"))));
	if (land) picks.push({ ...land, eyebrow: `TERRENO · ${land.eyebrow}` });
	const shelf = shelfCard(state);
	if (shelf && shelf.tone === "") picks.push({ ...shelf, eyebrow: "RECOMENDADO" });
	const sector = sectorCards(state).find((c) => c.tone === "");
	if (sector) picks.push({ ...sector, eyebrow: "NOVO SETOR" });
	// Cheapest upgrade the player can afford now.
	const upgrade = shopItems
		.filter(
			(item) =>
				!item.isConsumable &&
				!builtItems.includes(item.id) &&
				!state.shop.ownedItemIds.includes(item.id) &&
				state.market.level >= item.level &&
				(item.coinPrice ?? 0) > 0 &&
				(item.coinPrice ?? 0) <= Math.max(state.coins * 1.5, 500),
		)
		.sort((a, b) => (a.coinPrice ?? 0) - (b.coinPrice ?? 0))[0];
	if (upgrade) {
		const cards = upgrades.shop(state, [upgrade.category]).cards;
		const match = cards.find((c) => c.title === upgrade.name);
		if (match) picks.push({ ...match, eyebrow: "MELHORIA" });
	}
	const hire = upgrades.team(state, []).cards.find((c) => c.eyebrow === "DISPONÍVEL");
	if (hire) picks.push({ ...hire, eyebrow: "CONTRATE" });
	const decor = interiorDecor.find((d) => state.market.level >= d.requiredLevel && !(state.interior.owned[d.id] ?? 0) && d.coinPrice && state.coins >= d.coinPrice);
	if (decor) {
		const c = decoracao(state, decor.zone === "outside" ? "fora" : "dentro").cards.find((x) => x.title === decor.name);
		if (c) picks.push({ ...c, eyebrow: "DECORAÇÃO" });
	}
	const best = progress.currency(state, ["bundle"]).cards.slice(1).find((c) => /^(mais popular|melhor valor)$/i.test(c.subtitle));
	if (best) picks.push({ ...best, eyebrow: "OFERTA", tone: "featured" });
	return { cards: picks, chips: [] as Button[] };
}

// ------------------------------------------------------------------ the page
function content(state: State, tab: string, sub: string): { cards: Card[]; chips: Button[] } {
	switch (tab) {
		case "moveis":
			return moveis(state, sub);
		case "melhorias": {
			const category = shopCategories.find((c) => c.id === sub)?.id ?? "equipamentos";
			const built = upgrades.shop(state, [category]);
			const names = new Set(builtItems.map((id) => shopItems.find((item) => item.id === id)?.name));
			return {
				cards: built.cards.filter((c) => !names.has(c.title)),
				chips: shopCategories.map((c) => chip(c.label, "melhorias", c.id, c.id === category, gameIcon(getShopCategoryIcon(c.id)))),
			};
		}
		case "equipe":
			return { cards: upgrades.team(state, []).cards, chips: [] };
		case "terrenos":
			return { cards: lotCards(state), chips: [] };
		case "expansoes":
			// Da mesinha na calçada à rede: cada expansão traz mais lugares, clientes e vendas. The wings of the
			// market building come with the supermercado and the hipermercado (ERA_BUILDING_EXPANSIONS).
			return {
				cards: eraCards(state),
				chips: [],
			};
		case "decoracao":
			return decoracao(state, sub);
		case "moedas": {
			const currency = progress.currency(state, [sub || "all"]);
			return {
				cards: currency.cards.slice(1),
				chips: currency.chips.map((c) => ({ ...c, route: c.route.replace("~currency:", "~loja:moedas:") })),
			};
		}
		default:
			return destaques(state);
	}
}

export function shopPage(state: State, [tabArg, sub = ""]: string[]) {
	const tab = tabs.find((t) => t.id === tabArg) ?? tabs[0];
	const { cards, chips } = content(state, tab.id, sub === "all" ? "" : sub);
	const stored = getStoredInteriorBuilds(state).length;
	return page(`loja:${tab.id}${sub ? `:${sub}` : ""}`, tab.label, cards, {
		subtitle: tab.hint,
		icon: tab.icon,
		layout: "shop",
		tabs: tabs.map((t) =>
			button(t.label, {
				route: route(t.id),
				variant: "secondary",
				icon: t.icon,
				active: t.id === tab.id,
				badge: t.id === "moveis" && stored > 0 ? String(stored) : "",
			}),
		),
		chips,
	});
}

export const routes: Routes = {
	loja: shopPage,
};
