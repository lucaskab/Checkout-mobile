import type { ProductionJob, ProductionRecipe, ProductionSector } from "@/@types/production";
import { describeFixtureProducts } from "@/data/fixture-products";
import { getProductionSectorProductId } from "@/data/game-icon-assets";
import { formatBuildDuration, formatConstructionCountdown } from "@/data/market-expansions";
import { itemCatalog } from "@/data/market-products";
import { getProductionSector, getSectorRecipes, productionSectors } from "@/data/production-sectors";
import { getSectorCounterFor } from "@/data/shelf-types";
import { getActiveGameEventEffects } from "@/services/game-events";
import { getSectorBuildStatus } from "@/services/interior-construction";
import {
	getProductionDiamondCost,
	getProductionEconomy,
	getProductionRemainingTime,
	getRecipeProfitMargin,
} from "@/services/production";
import { getMaxShelfOrderBoxes, getShelfOrderQuote } from "@/services/shelf-order-quote";
import type { Routes } from ".";
import {
	act,
	type BoardStat,
	type BoardTile,
	board,
	type Button,
	button,
	decorIcon,
	fmt,
	gameIcon,
	go,
	meter,
	noButton,
	page,
	productIcon,
	ratio,
	type State,
	stat,
	swap,
	tile,
} from "../view-kit";
import { buildCard } from "./build-cards";
import { hasKitchenGame } from "./kitchen";

// Production as a game board (page.layout = "board"): the sectors are machines on a factory floor (build
// them, see what each one is cooking, open it), and inside a sector the production lines tick down with a
// timer while the recipes show which ingredients are missing — with a one-tap order for each missing one,
// like the production buildings of Hay Day and Township.

const productName = (id: number) => itemCatalog.find((item) => item.id === id)?.name ?? `Produto ${id}`;

function buildButtons(state: State, sectorId: string): Button[] {
	const build = getSectorBuildStatus(state, sectorId);
	if (build.status === "built") return [];
	return buildCard(state, {
		title: productionSectors.find((sector) => sector.id === sectorId)?.name ?? "Setor",
		icon: decorIcon(`sector-${sectorId}`),
		subtitle: "",
		status: build,
		coins: { action: "buildSector", args: [sectorId, "coins"], price: build.coinCost },
		diamonds: { action: "buildSector", args: [sectorId, "diamonds"], price: build.diamondCost },
	}).buttons;
}

// ---------------------------------------------------------------- the sectors
function sectorTile(state: State, sector: ProductionSector, now: number): BoardTile {
	const build = getSectorBuildStatus(state, sector.id, now);
	const jobs = state.production.jobs.filter((job) => job.sectorId === sector.id);
	const counter = getSectorCounterFor(sector.id);
	const sells = describeFixtureProducts(counter?.id ?? "", state.market.unlockedProductIds);
	const open = go("Abrir setor", `sector:${sector.id}`, { icon: gameIcon("conveyor"), variant: "primary" });
	const builds = buildButtons(state, sector.id);
	const next = jobs.sort((a, b) => a.endsAt - b.endsAt)[0];
	const base = {
		group: build.status === "built" ? "SEUS SETORES" : build.status === "locked" ? "AINDA BLOQUEADOS" : "PARA CONSTRUIR",
		icon: productIcon(getProductionSectorProductId(sector.id)),
		subtitle: sector.subtitle,
		detail: sector.description,
		lines: [sells ? `Vende no balcão: ${sells}` : ""].filter(Boolean),
	};
	if (build.status === "built")
		return tile(sector.id, sector.name, {
			...base,
			sticker: jobs.length ? "PRODUZINDO" : "PARADO",
			tone: jobs.length ? "info" : "warning",
			badge: `${jobs.length}/${sector.slotCount}`,
			fill: ratio(jobs.length, sector.slotCount),
			fillText: `${jobs.length}/${sector.slotCount} linhas`,
			timerEnd: next ? next.endsAt : 0,
			timerTotal: next ? next.endsAt - next.startedAt : 0,
			state: jobs.length < sector.slotCount ? "ready" : "",
			action: open,
			facts: [
				stat(gameIcon("conveyor"), `${jobs.length}/${sector.slotCount}`, "Linhas ocupadas"),
				stat(gameIcon("clipboard"), String(getSectorRecipes(sector.id).length), "Receitas"),
			],
			actions: [
				open,
				...(counter ? [go(`Vender no ${counter.name.toLocaleLowerCase("pt-BR")}`, `shelf:${counter.id}`, { icon: gameIcon("shelf") })] : []),
			],
		});
	if (build.status === "building" || build.status === "queued" || build.status === "stored")
		return tile(sector.id, sector.name, {
			...base,
			sticker: build.status === "building" ? "EM OBRA" : build.status === "stored" ? "NO INVENTÁRIO" : "NA FILA",
			tone: "warning",
			fill: build.status === "building" ? build.progress : -1,
			fillText: build.status === "building" ? `Pronto em ${formatConstructionCountdown(build.remainingMs)}` : "",
			timerEnd: build.status === "building" ? now + build.remainingMs : 0,
			timerTotal: build.durationMs,
			state: "busy",
			action: builds[0] ?? noButton(),
			actions: builds,
		});
	if (build.status === "locked")
		return tile(sector.id, sector.name, {
			...base,
			// The reason ("Chega com: ...") is the locked button; it was also the ribbon and the bar text.
			sticker: "",
			tone: "locked",
			state: "locked",
			fill: Math.min(1, state.market.level / Math.max(1, sector.requiredLevel)),
			fillText: "",
			action: button(build.reason, { variant: "secondary", enabled: false, icon: gameIcon("lock") }),
		});
	return tile(sector.id, sector.name, {
		...base,
		sticker: "CONSTRUIR",
		tone: "gold",
		badge: fmt(build.coinCost),
		state: "ready",
		fillText: `Obra de ${formatBuildDuration(build.durationMs)}`,
		action: builds[0] ?? noButton(),
		facts: [
			stat(gameIcon("coin"), fmt(build.coinCost), "Custo da obra"),
			stat(gameIcon("construction"), formatBuildDuration(build.durationMs), "Tempo de obra"),
			stat(gameIcon("conveyor"), String(sector.slotCount), "Linhas de produção"),
		],
		actions: builds,
	});
}

function sectorsBoard(state: State) {
	const now = Date.now();
	const jobs = state.production.jobs;
	const built = state.builtSectorIds.length;
	const slots = productionSectors
		.filter((sector) => state.builtSectorIds.includes(sector.id))
		.reduce((total, sector) => total + sector.slotCount, 0);
	const idle = productionSectors.filter(
		(sector) => state.builtSectorIds.includes(sector.id) && jobs.filter((job) => job.sectorId === sector.id).length === 0,
	).length;
	const tiles = productionSectors.map((sector) => sectorTile(state, sector, now));
	return page("sectors", "Produção", [], {
		layout: "board",
		icon: gameIcon("conveyor"),
		subtitle: "Fabrique produtos exclusivos e mais lucrativos",
		board: board(tiles, {
			tint: "B26A2E",
			backdrop: "Game/floor_backdrop",
			columns: 4,
			stats: [
				stat(gameIcon("market"), `${built}/${productionSectors.length}`, "Setores"),
				stat(gameIcon("conveyor"), `${jobs.length}/${slots}`, "Linhas"),
				stat(gameIcon("package"), fmt(state.production.totalCrafted), "Fabricados"),
			],
			meter: meter("Linhas trabalhando", jobs.length, Math.max(slots, 1), {
				icon: gameIcon("conveyor"),
				text: slots ? `${jobs.length} de ${slots} linhas de produção ocupadas` : "Construa um setor para começar a produzir",
				tone: "info",
			}),
			tip: idle
				? `${idle} setor${idle === 1 ? " está parado" : "es estão parados"}. Abra e coloque uma receita para fabricar!`
				: built
					? "Todos os setores trabalhando. Produtos fabricados custam menos que os do fornecedor."
					: "Construa o primeiro setor: produtos fabricados dão mais lucro.",
		}),
	});
}

// ---------------------------------------------------------------- inside a sector
function lineTile(state: State, sector: ProductionSector, index: number, job: ProductionJob | undefined, now: number): BoardTile {
	if (!job)
		return tile(`line${index}`, `Linha ${index + 1}`, {
			group: "LINHAS DE PRODUÇÃO",
			icon: gameIcon("conveyor"),
			subtitle: "Livre: escolha uma receita",
			sticker: "LIVRE",
			tone: "warning",
			state: "ready",
			detail: "Linha parada! Escolha uma receita nas receitas abaixo e toque em Fabricar.",
		});
	const cost = getProductionDiamondCost(job.endsAt - now);
	const finish = act(`Terminar já · ${cost}`, "finishProductionNow", [job.id], {
		variant: "gem",
		icon: gameIcon("diamond"),
		enabled: state.logistics.premiumCurrency >= cost,
		ok: `${productName(job.outputProductId)} pronto!`,
		fail: "Diamantes insuficientes.",
	});
	return tile(`line${index}`, productName(job.outputProductId), {
		group: "LINHAS DE PRODUÇÃO",
		icon: productIcon(job.outputProductId),
		subtitle: `Linha ${index + 1} · rende ${job.outputQuantity}`,
		sticker: "FABRICANDO",
		tone: "info",
		badge: `x${job.outputQuantity}`,
		fill: ratio(now - job.startedAt, job.endsAt - job.startedAt),
		fillText: `Pronto em ${getProductionRemainingTime(job.endsAt, now)}`,
		timerEnd: job.endsAt,
		timerTotal: job.endsAt - job.startedAt,
		state: "busy",
		action: finish,
		detail: "A produção continua mesmo com a janela fechada. Quando termina, vai direto para o depósito.",
		facts: [
			stat(gameIcon("package"), `x${job.outputQuantity}`, "Rende"),
			stat(gameIcon("diamond"), String(cost), "Terminar já"),
		],
		actions: [finish],
	});
}

function recipeTile(state: State, sector: ProductionSector, recipe: ProductionRecipe, freeSlot: boolean, multiplier: number, now: number): BoardTile {
	const product = itemCatalog.find((item) => item.id === recipe.outputProductId);
	const name = productName(recipe.outputProductId);
	const locked = state.market.level < recipe.requiredLevel;
	const owned = (id: number) => state.inventory[id] ?? 0;
	const missing = recipe.ingredients.filter((ingredient) => owned(ingredient.productId) < ingredient.quantity);
	const have = recipe.ingredients.length - missing.length;
	const canMake = !locked && missing.length === 0 && freeSlot;
	const duration = getProductionRemainingTime(now + recipe.durationMs * multiplier, now);
	const economy = getProductionEconomy(recipe);
	const make = act(`Fabricar ${recipe.outputQuantity}`, "startProduction", [{ recipeId: recipe.id, sectorId: sector.id }], {
		variant: "success",
		icon: gameIcon("conveyor"),
		enabled: canMake,
		ok: `${name} entrou na linha de produção!`,
		fail: locked
			? `Libera no nível ${recipe.requiredLevel}.`
			: !freeSlot
				? "Todas as linhas estão ocupadas."
				: "Faltam ingredientes.",
	});
	// Made by hand in the kitchen game: no line needed, no wait, 3 stars give one more.
	const built = getSectorBuildStatus(state, sector.id).status === "built";
	const byHand = hasKitchenGame(recipe.id) && built && !locked
		? go(missing.length ? "Fazer à mão (falta ingrediente)" : "Fazer à mão", `kitchen:${recipe.id}`, {
				icon: gameIcon("target"),
				variant: missing.length ? "secondary" : "primary",
				enabled: missing.length === 0,
				fail: "Faltam ingredientes.",
			})
		: null;
	// One tap to order each missing ingredient from the supplier (full load).
	const orders = missing
		.map((ingredient) => {
			const item = itemCatalog.find((entry) => entry.id === ingredient.productId);
			if (!item || item.acquisition !== "supplier") return null;
			// Whole supplier boxes, as many as the racks, coins and delivery slots allow.
			const boxes = getMaxShelfOrderBoxes(state, item.id);
			const quote = boxes > 0 ? getShelfOrderQuote(state, item.id, boxes, now) : null;
			const boxLabel = boxes === 1 ? "1 caixa" : `${boxes} caixas`;
			return quote
				? act(`Pedir ${item.name} · ${boxLabel} · ${fmt(quote.total)}`, "placeSupplierOrder", [{ productId: item.id, boxes }], {
						variant: "coin",
						icon: gameIcon("deliveryTruck"),
						ok: `${item.name} a caminho!`,
						fail: "Não deu para pedir agora.",
					})
				: null;
		})
		.filter((item): item is Button => item !== null);
	const facts: BoardStat[] = [
		...recipe.ingredients.map((ingredient) =>
			stat(
				productIcon(ingredient.productId),
				`${fmt(owned(ingredient.productId))}/${ingredient.quantity}`,
				productName(ingredient.productId),
				owned(ingredient.productId) >= ingredient.quantity ? "success" : "danger",
			),
		),
		stat(gameIcon("coin"), `+${getRecipeProfitMargin(recipe)}%`, "Margem"),
		stat(gameIcon("priceTag"), `−${economy.savingsPercent}%`, "Mais barato que comprar"),
	];
	return tile(recipe.id, name, {
		group: "RECEITAS",
		icon: productIcon(recipe.outputProductId),
		subtitle: `Rende ${recipe.outputQuantity} · ${duration}`,
		sticker: locked ? `NV ${recipe.requiredLevel}` : canMake || (byHand?.enabled ?? false) ? "PODE FAZER" : missing.length ? "FALTA INGREDIENTE" : "LINHAS CHEIAS",
		tone: locked ? "locked" : canMake ? "success" : missing.length ? "warning" : "",
		badge: `x${recipe.outputQuantity}`,
		fill: locked ? -1 : ratio(have, recipe.ingredients.length),
		fillText: `Ingredientes ${have}/${recipe.ingredients.length}`,
		state: locked ? "locked" : canMake ? "ready" : "",
		action: !locked && missing.length && orders.length ? orders[0] : byHand?.enabled ? byHand : make,
		detail: `Vende por ${product?.sellingPrice ?? 0} e dá ${product?.xpPerSale ?? 0} XP por venda. Fabricar custa ${Math.ceil(economy.productionUnitCost)} por unidade, comprar custaria ${economy.supplierUnitPrice}.`,
		facts,
		actions: [...(byHand ? [byHand] : []), make, ...orders],
	});
}

function sectorBoard(state: State, sectorId: string) {
	const sector = getProductionSector(sectorId);
	if (!sector) return sectorsBoard(state);
	const now = Date.now();
	const build = getSectorBuildStatus(state, sector.id, now);
	const jobs = state.production.jobs.filter((job) => job.sectorId === sector.id);
	const freeSlot = jobs.length < sector.slotCount && build.status === "built";
	const multiplier = getActiveGameEventEffects(state.events).productionDurationMultiplier;
	const recipes = getSectorRecipes(sector.id);
	const tiles = [
		...(build.status === "built"
			? Array.from({ length: sector.slotCount }, (_, index) =>
					lineTile(state, sector, index, jobs.find((job) => job.slotIndex === index), now),
				)
			: [sectorTile(state, sector, now)]),
		...recipes
			.map((recipe) => recipeTile(state, sector, recipe, freeSlot, multiplier, now))
			.sort((a, b) => Number(b.state === "ready") - Number(a.state === "ready")),
	];
	const counter = getSectorCounterFor(sector.id);
	return page(`sector:${sector.id}`, sector.name, [], {
		layout: "board",
		icon: productIcon(getProductionSectorProductId(sector.id)),
		subtitle: sector.description,
		tabs: [
			go("Todos", "~sectors", { icon: gameIcon("conveyor") }),
			...productionSectors.map((item) => {
				const status = getSectorBuildStatus(state, item.id, now).status;
				return {
					...swap(item.name, `sector:${item.id}`, item.id === sector.id, productIcon(getProductionSectorProductId(item.id))),
					enabled: status !== "locked",
					fail: status === "locked" ? `Nível ${item.requiredLevel}` : "",
				};
			}),
		],
		board: board(tiles, {
			tint: "B26A2E",
			backdrop: "Game/floor_backdrop",
			columns: 4,
			stats: [
				stat(gameIcon("conveyor"), `${jobs.length}/${sector.slotCount}`, "Linhas"),
			],
			meter: meter("Linhas de produção", jobs.length, sector.slotCount, {
				icon: gameIcon("conveyor"),
				text: freeSlot ? "Tem linha livre: escolha uma receita!" : "Todas as linhas trabalhando",
				tone: freeSlot ? "warning" : "success",
			}),
			footer: [
				...(counter && build.status === "built"
					? [go(`Vender no ${counter.name.toLocaleLowerCase("pt-BR")}`, `shelf:${counter.id}`, { icon: gameIcon("shelf"), variant: "primary" })]
					: []),
				go("Todos os setores", "~sectors", { icon: gameIcon("conveyor") }),
			],
			tip: freeSlot
				? "Linha livre! As receitas com brilho já têm todos os ingredientes."
				: build.status === "built"
					? "Tudo produzindo. Enquanto isso, peça os ingredientes que faltam."
					: "Construa este setor para começar a fabricar.",
		}),
	});
}

export const routes: Routes = {
	sectors: (state) => sectorsBoard(state),
	sector: (state, [sectorId = ""]) => sectorBoard(state, sectorId),
};
