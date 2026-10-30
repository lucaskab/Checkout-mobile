import { describeFixtureProducts } from "@/data/fixture-products";
import { getFixtureName, getShelfType } from "@/data/shelf-types";
import { interiorDecor } from "@/data/interior-decor";
import { shopItemBuildDurations } from "@/data/interior-construction";
import { productionSectors } from "@/data/production-sectors";
import { shopCategories, shopItems } from "@/data/shop-items";
import { getShopCategoryIcon } from "@/data/game-icon-assets";
import { formatBuildDuration } from "@/data/market-expansions";
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
import {
	checkoutTierItemIds,
	coldRoomTierItemIds,
	decorTiers,
	getDecorTier,
	getNextDecorTier,
} from "@/data/fixture-tiers";
import { getCheckoutTierInfo, getColdRoomInfo } from "@/services/fixture-tiers";
import { getShopItemPlaceEra } from "@/data/interior-construction";
import { getEraOrder } from "@/data/market-products";
import { getMarketExpansion } from "@/data/market-expansions";
import { eraCards } from "./eras";
import { lotCards } from "./lots";
import { getMarketEra, getNextMarketEra } from "@/data/economy";
import { getMarketPaintCoinPrice, getMarketPalette, isClassicPaint, MARKET_PAINT_DIAMONDS } from "@/data/market-paint";
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
/** "Evoluções dos móveis": the checkout's steps and the cold room live in Móveis e obras, not among the upgrades. */
const coldRoomItems = Object.values(coldRoomTierItemIds);
const tierItems: string[] = [...checkoutTierItemIds, ...coldRoomItems];

/** Why a shop item cannot be bought yet ("" = it can). */
function shopItemLock(state: State, itemId: string) {
	const item = shopItems.find((entry) => entry.id === itemId);
	if (!item) return "—";
	const era = getShopItemPlaceEra(itemId);
	if (era && getEraOrder(state.era.id) < getEraOrder(era)) return `Chega com: ${getMarketEra(era).name}`;
	if (state.market.level < item.level) return `Nível ${item.level}`;
	if (item.requiresExpansionId && !state.unlockedMarketExpansionIds.includes(item.requiresExpansionId))
		return `Precisa de: ${getMarketExpansion(item.requiresExpansionId)?.name ?? ""}`;
	return "";
}

function priceButtons(state: State, itemId: string, lock: string, ok: string): Button[] {
	const item = shopItems.find((entry) => entry.id === itemId);
	if (!item) return [];
	const buttons: Button[] = [];
	if (item.coinPrice)
		buttons.push(
			act(lock || `Evoluir · ${fmt(item.coinPrice)}`, "purchaseShopItem", [itemId, "coins"], {
				variant: "coin",
				icon: lock ? "" : gameIcon("coin"),
				enabled: !lock && state.coins >= item.coinPrice,
				ok,
				fail: lock || "Moedas insuficientes",
			}),
		);
	if (item.diamondPrice && !lock)
		buttons.push(
			act(`Evoluir · ${fmt(item.diamondPrice)}`, "purchaseShopItem", [itemId, "diamonds"], {
				variant: "gem",
				icon: gameIcon("diamond"),
				enabled: true, // too few diamonds opens the diamond store (desktop/host.ts)
				ok,
				fail: "Diamantes insuficientes",
			}),
		);
	return buttons;
}

/** The checkout evolves in steps: every checkout of the market (the extra one too) wears the same one. */
function checkoutEvolutionCard(state: State): Card {
	const info = getCheckoutTierInfo(state);
	const nextId = checkoutTierItemIds.find((id) => !state.shop.ownedItemIds.includes(id));
	const next = nextId ? shopItems.find((item) => item.id === nextId) : undefined;
	const current = info.scanner && info.visualTier === 3 ? `${info.name} e leitor` : info.name;
	if (!next)
		return card("Caixa", { eyebrow: "NO MÁXIMO", icon: decorIcon("checkout"), tone: "success", subtitle: `Seus caixas: ${current}.` });
	const lock = shopItemLock(state, next.id);
	return card(`Evoluir o caixa: ${next.name}`, {
		eyebrow: lock ? "BLOQUEADO" : "EVOLUÇÃO",
		icon: decorIcon("checkout"),
		tone: lock ? "locked" : "featured",
		badge: `Nv ${next.level}`,
		subtitle: next.description,
		lines: [`Agora: ${current}`],
		buttons: priceButtons(state, next.id, lock, "Seu caixa evoluiu!"),
	});
}

/** The cold room: T1 free, then built against the depot and at the central warehouse (works over time). */
function coldRoomCard(state: State): Card {
	const cold = getColdRoomInfo(state);
	const nextId = coldRoomTierItemIds[cold.tier + 1];
	const next = nextId ? shopItems.find((item) => item.id === nextId) : undefined;
	const lines = [`Agora: ${cold.name} · até ${cold.upgradeCap === 1 ? "3" : cold.upgradeCap === 2 ? "5" : cold.upgradeCap === 3 ? "8" : "12"} caixas por produto gelado`];
	if (!next)
		return card("Câmara fria", { eyebrow: "NO MÁXIMO", icon: gameIcon("warehouse"), tone: "success", subtitle: "Laticínios, frios, carnes, peixes, congelados e sorvetes ficam na câmara fria.", lines });
	const status = getShopItemBuildStatus(state, next.id);
	if (status && (status.status === "building" || status.status === "queued"))
		return buildCard(state, { title: next.name, icon: gameIcon("warehouse"), subtitle: next.description, status });
	const lock = shopItemLock(state, next.id) || (next.requiresItemId && !state.shop.ownedItemIds.includes(next.requiresItemId) ? "—" : "");
	return card(`Evoluir a câmara fria: ${next.name}`, {
		eyebrow: lock ? "BLOQUEADO" : "EVOLUÇÃO",
		icon: gameIcon("warehouse"),
		tone: lock ? "locked" : "featured",
		badge: formatBuildDuration(shopItemBuildDurations[next.id] ?? 0),
		subtitle: next.description,
		lines,
		buttons: priceButtons(state, next.id, lock, "Os construtores começaram a obra da câmara fria."),
	});
}

function shelfCard(state: State) {
	const build = getNextShelfBuildStatus(state);
	if (!build.shelf) return null;
	return buildCard(state, {
		title: getFixtureName(build.shelf.id, state.era.id),
		icon: shelfThumb(build.shelf.id, state.era.id),
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
	return builtItems.filter((id) => !tierItems.includes(id)).flatMap((id) => {
		const item = shopItems.find((entry) => entry.id === id);
		const status = getShopItemBuildStatus(state, id);
		if (!item || !status) return [];
		const locked = state.market.level < item.level;
		const isDiamond = !item.coinPrice && Boolean(item.diamondPrice);
		const price = (isDiamond ? item.diamondPrice : item.coinPrice) ?? 0;
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
		lines: stored.map((item) => `• ${getInteriorBuildName(item.kind, item.targetId, state.era.id)}`),
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
	if (sub === "" || sub === "caixas") cards.push(checkoutEvolutionCard(state), ...checkoutCards(state));
	if (sub === "" || sub === "camara") cards.push(coldRoomCard(state));
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
			chip("Câmara fria", "moveis", "camara", sub === "camara", gameIcon("warehouse")),
		],
	};
}

// ------------------------------------------------------------------ decorations
// "Cores do mercado": the picker is drawn by Unity over the live market ("@paint", CheckoutMarketPaintPanel).
function paintCard(state: State): Card {
	const paint = state.marketPaint;
	const current = isClassicPaint(paint) ? "Clássico" : (getMarketPalette(paint.paletteId)?.name ?? "Sua cor");
	return card("Cores do mercado", {
		eyebrow: "PINTE O SEU MERCADO",
		icon: gameIcon("paint"),
		tone: "featured",
		subtitle: "Pinte o mercado com as suas cores e veja ao vivo antes de pagar.",
		lines: [`Agora: ${current}`, `${fmt(getMarketPaintCoinPrice(state.era.id))} moedas ou ${MARKET_PAINT_DIAMONDS} diamantes`],
		buttons: [button("Escolher cores", { route: "@paint", variant: "primary", icon: gameIcon("paint") })],
	});
}

function decoracao(state: State, sub: string) {
	const zone = sub === "fora" ? "outside" : "inside";
	const coins = state.coins;
	const diamonds = state.logistics.premiumCurrency;
	const cards = interiorDecor
		.filter((decor) => decor.zone === zone)
		.map((decor) => {
			// The cart bays need the market building's aisles: on sale from the mercadinho.
			const eraLock = decor.placeEra && getEraOrder(state.era.id) < getEraOrder(decor.placeEra) ? `Chega com: ${getMarketEra(decor.placeEra).name}` : "";
			const locked = state.market.level < decor.requiredLevel || !!eraLock;
			const lockLabel = eraLock || `Nível ${decor.requiredLevel}`;
			const owned = state.interior.owned[decor.id] ?? 0;
			const useDiamonds = !decor.coinPrice;
			const price = (useDiamonds ? decor.diamondPrice : decor.coinPrice) ?? 0;
			// Evolving decorations: the next tier upgrades every piece of the kind.
			const tier = decorTiers[decor.id] ? getDecorTier(state.interior.tiers, decor.id) : 0;
			const nextTier = owned > 0 ? getNextDecorTier(state.interior.tiers, decor.id) : null;
			const tierLocked = !!nextTier && state.market.level < nextTier.requiredLevel;
			const tierDiamonds = !!nextTier && !nextTier.coinPrice;
			const tierPrice = (tierDiamonds ? nextTier?.diamondPrice : nextTier?.coinPrice) ?? 0;
			return card(tier > 1 ? decorTiers[decor.id][tier - 1].name : decor.name, {
				eyebrow: locked ? (eraLock ? "BLOQUEADO" : `NÍVEL ${decor.requiredLevel}`) : "", // the zone is the selected chip above
				icon: decorIcon(decor.id),
				tone: locked ? "locked" : owned > 0 ? "success" : "",
				badge: owned > 0 ? `x${owned}` : "",
				subtitle: decor.description,
				lines: nextTier ? [`Próximo visual: ${nextTier.name}`] : [],
				buttons: [
					act(locked ? lockLabel : fmt(price), "purchaseDecor", [decor.id, useDiamonds ? "diamonds" : "coins"], {
						variant: useDiamonds ? "gem" : "coin",
						icon: locked ? "" : gameIcon(useDiamonds ? "diamond" : "coin"),
						enabled: !locked && (useDiamonds || coins >= price),
						ok: `${decor.name} comprado! Coloque no modo construir.`,
						fail: locked ? lockLabel : useDiamonds ? "Diamantes insuficientes" : "Moedas insuficientes",
					}),
					...(nextTier
						? [
								act(tierLocked ? `Nível ${nextTier.requiredLevel}` : `Evoluir · ${fmt(tierPrice)}`, "upgradeDecorTier", [decor.id, tierDiamonds ? "diamonds" : "coins"], {
									variant: tierDiamonds ? "gem" : "coin",
									icon: tierLocked ? "" : gameIcon(tierDiamonds ? "diamond" : "coin"),
									enabled: !tierLocked && (tierDiamonds || coins >= tierPrice),
									ok: "Seu móvel evoluiu!",
									fail: tierLocked ? `Nível ${nextTier.requiredLevel}` : tierDiamonds ? "Diamantes insuficientes" : "Moedas insuficientes",
								}),
							]
						: []),
					...(owned > 0 ? [placeButton("Colocar")] : []),
				],
			});
		});
	return {
		cards: [paintCard(state), ...cards],
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
				!tierItems.includes(item.id) &&
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
function content(state: State, tab: string, sub: string, extra = ""): { cards: Card[]; chips: Button[] } {
	switch (tab) {
		case "moveis":
			return moveis(state, sub);
		case "melhorias": {
			const category = shopCategories.find((c) => c.id === sub)?.id ?? "equipamentos";
			const built = upgrades.shop(state, [category]);
			const names = new Set([...builtItems, ...tierItems].map((id) => shopItems.find((item) => item.id === id)?.name));
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
			const currency = progress.currency(state, [sub || "all", extra]);
			return {
				cards: currency.cards.slice(1),
				chips: currency.chips.map((c) => ({ ...c, route: c.route.replace("~currency:", "~loja:moedas:") })),
			};
		}
		default:
			return destaques(state);
	}
}

export function shopPage(state: State, [tabArg, sub = "", extra = ""]: string[]) {
	const tab = tabs.find((t) => t.id === tabArg) ?? tabs[0];
	const { cards, chips } = content(state, tab.id, sub === "all" ? "" : sub, extra);
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
