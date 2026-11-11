import type { ChainBranchId, ChainContract, FleetTruck } from "@/@types/chain";
import {
	AUTO_ORDER_RESERVE,
	CHAIN_NAME_MAX,
	CHAIN_RENAME_DIAMONDS,
	chainBranches,
	chainClients,
	chainEmblems,
	FLEET_SPEED_FACTORS,
	privateLabelProducts,
} from "@/data/chain";
import { getSkipDiamondCost } from "@/data/diamond-skip";
import { formatBuildDuration } from "@/data/market-expansions";
import { itemCatalog, itemCategories } from "@/data/market-products";
import {
	chooseBranchCargo,
	getBranchDefinition,
	getBranchIncomePerMin,
	getBranchNextStep,
	getContractShortfall,
	getNextSpeedPrice,
	getNextTruckPrice,
	getTripFactor,
	isChainUnlocked,
	isTruckFree,
	pickTruck,
	updateBranch,
} from "@/services/chain";
import type { Routes } from ".";
import {
	act,
	type BoardTile,
	board,
	button,
	type Button,
	type Card,
	card,
	fmt,
	gameIcon,
	go,
	meter,
	page,
	productIcon,
	type State,
	stat,
	tile,
} from "../view-kit";

// Rede de supermercados (claude/rede-supermercados-proposta.md, ideas 2 + 5): the chain's brand (name, logo, own
// products), its distribution centre with the player's own truck fleet (restocking the market, city contracts) and the
// branch stores on the city map. Four tabs of one window, like Produtos / Missões.

const NAVY = "1D2B4F";
const MIN = 60_000;
type Tab = "marca" | "cd" | "contratos" | "filiais";
const tabs: { id: Tab; label: string; icon: string }[] = [
	{ id: "marca", label: "Marca", icon: "ui-marca" },
	{ id: "cd", label: "Frota", icon: "ui-frota" },
	{ id: "contratos", label: "Contratos", icon: "ui-contratos" },
	{ id: "filiais", label: "Filiais", icon: "ui-filiais" },
];

/** Art of the Rede window (Resources/CheckoutDesktop/Rede/...). Emblems are tinted with the market's colours by Unity. */
export const redeIcon = (name: string) => `Rede/${name}`;
export const emblemIcon = (id: string) => `Rede/Emblems/${id}`;
/** The logos' names, under each one on the Marca tab. */
const emblemNames: Record<string, string> = {
	cesta: "Cesta",
	carrinho: "Carrinho",
	folha: "Folha",
	estrela: "Estrela",
	coroa: "Coroa",
	sol: "Sol",
	coracao: "Coração",
	sacola: "Sacola",
	maca: "Maçã",
	trigo: "Trigo",
	toldo: "Toldo",
	diamante: "Diamante",
};
const productName = (id: number) => itemCatalog.find((item) => item.id === id)?.name ?? `#${id}`;
const minutes = (ms: number) => formatBuildDuration(Math.max(MIN, ms));
const categoryLabel = (id: string) => (itemCategories.find((category) => category.id === id)?.label ?? id).toLocaleLowerCase("pt-BR");
const favoritesText = (ids: string[]) => ids.map(categoryLabel).join(", ");

function sections(state: State, active: Tab): Button[] {
	const waiting = branchesWaiting(state);
	const ready = contractsReady(state);
	return tabs.map((tab) =>
		button(tab.label, {
			icon: redeIcon(tab.icon),
			route: `!rede:${tab.id}`,
			variant: tab.id === active ? "coin" : "secondary",
			active: tab.id === active,
			badge: tab.id === "filiais" && waiting > 0 ? "!" : tab.id === "contratos" && ready > 0 ? String(ready) : "",
		}),
	);
}

/** Offers on the board that the stockroom can already fill. */
function contractsReady(state: State) {
	return state.chain.contracts.offers.filter((offer) => offer.acceptedAt === null && getContractShortfall(offer, state.inventory).length === 0).length;
}

/** Branches with coins to collect (over a minute of income) or empty shelves. */
function branchesWaiting(state: State) {
	const now = Date.now();
	return chainBranches.filter((def) => {
		const b = updateBranch(state.chain.branches[def.id], now);
		return b.level > 0 && (b.pending >= getBranchIncomePerMin(def.id, b.level) * 30 || (b.supply < 0.25 && !b.cargo));
	}).length;
}

function redePage(state: State, active: Tab, title: string, cards: Card[], tiles: BoardTile[], options: Parameters<typeof board>[1] = {}) {
	return page(`rede:${active}`, title, cards, {
		icon: redeIcon("ui-filiais"),
		layout: "board",
		sections: sections(state, active),
		board: board(tiles, { tint: NAVY, columns: 4, ...options }),
	});
}

function lockedPage(state: State) {
	return page("rede", "Rede de supermercados", [
		card("Ainda não é uma rede", {
			icon: redeIcon("ui-filiais"),
			eyebrow: "ÚLTIMA EXPANSÃO",
			tone: "locked",
			lines: ["Quando a obra da Rede de supermercados terminar, você dá um nome e um logo à sua rede, ganha o centro de distribuição com caminhões próprios e abre filiais pela cidade."],
			buttons: [go("Ver expansões", "!loja:expansoes", { icon: gameIcon("construction") })],
		}),
	]);
	void state;
}

// ------------------------------------------------------------------------------------------------ Marca
// The logo picked on the Marca tab before saving (a tap on a logo tile picks it, like the faces of Amigos).
let pickedEmblem: string | null = null;
export const redeActions = ["chainPickEmblem"];
export function requestRedeAction(action: string, args: unknown[]): { ok: boolean; reason?: string } {
	if (action === "chainPickEmblem" && chainEmblems.includes(args[0] as never)) {
		pickedEmblem = args[0] as string;
		return { ok: true };
	}
	return { ok: false };
}

function brandPage(state: State, pickedArg?: string): ReturnType<typeof page> {
	const brand = state.chain.brand;
	const first = brand.namedAt === null;
	const choice = pickedArg ?? pickedEmblem;
	const picked = chainEmblems.includes(choice as never) ? (choice as string) : brand.emblem;
	const hero = card(first ? "Dê um nome à sua rede" : brand.name, {
		icon: emblemIcon(picked),
		eyebrow: first ? "VOCÊ AGORA É UMA REDE!" : "SUA MARCA",
		hero: !first,
		lines: [
			first
				? "O nome e o logo vão para a fachada, os produtos da marca própria e as filiais, nas cores do mercado."
				: `Trocar só o logo é grátis. Um nome novo custa ${CHAIN_RENAME_DIAMONDS} diamantes.`,
		],
		input: { id: "rede-nome", placeholder: "Nome da rede", value: brand.name, max: CHAIN_NAME_MAX, kind: "name" },
		buttons: [
			act(first ? "Batizar a rede" : `Salvar`, "nameChain", ["$input:rede-nome", picked], {
				icon: gameIcon("success"),
				variant: "success",
				ok: first ? "Sua rede nasceu!" : "Marca atualizada!",
				fail: "Escolha um nome de 2 a 18 letras.",
			}),
		],
	});
	const emblems = chainEmblems.map((id) =>
		tile(id, emblemNames[id] ?? "", {
			icon: emblemIcon(id),
			state: id === picked ? "done" : "",
			action: act(id === picked ? "Escolhido" : "Escolher", "chainPickEmblem", [id], { variant: id === picked ? "coin" : "secondary", ok: "" }),
		}),
	);
	return redePage(state, "marca", first ? "Batize a sua rede" : "Marca da rede", [hero], emblems, {
		columns: 12,
		style: "faces",
		focus: picked,
		empty: "",
		stats: [stat(redeIcon("ui-frota"), fmt(state.chain.fleet.trucks.length), "caminhões"), stat(redeIcon("ui-filiais"), fmt(chainBranches.filter((b) => state.chain.branches[b.id].level > 0).length), "filiais")],
	});
}

// ------------------------------------------------------------------------------------------------ Frota / CD
function privateLabelTiles(state: State): BoardTile[] {
	// The chain's own products (ordered only from the distribution centre).
	return privateLabelProducts.map(({ id, baseId }) => {
		const item = itemCatalog.find((product) => product.id === id);
		const base = itemCatalog.find((product) => product.id === baseId);
		const stock = state.inventory[id] ?? 0;
		return tile(`pl-${id}`, base?.name ?? productName(id), {
			group: "MARCA PRÓPRIA",
			icon: productIcon(id),
			badge: stock > 0 ? fmt(stock) : "",
			subtitle: item && base ? `Lucro ${fmt(item.sellingPrice - item.purchasePrice)} · comum ${fmt(base.sellingPrice - base.purchasePrice)}` : "",
			detail: "Produto da sua rede: vem do centro de distribuição, custa quase metade e dá mais lucro por unidade. Clientes econômicos e famílias adoram.",
			action: act("Pedir 1 caixa", "orderFromDistributionCenter", [[{ productId: id, boxes: 1 }]], {
				icon: redeIcon("ui-cd"),
				variant: "primary",
				ok: "O caminhão da rede saiu do centro de distribuição!",
				fail: "Nenhum caminhão livre ou sem espaço no estoque.",
			}),
		});
	});
}

const jobLabel: Record<string, string> = { abastecer: "Levando estoque ao mercado", contrato: "Entregando um contrato", filial: "Levando carga à filial" };

function truckTile(state: State, truck: FleetTruck, index: number, now: number): BoardTile {
	const free = isTruckFree(truck, now);
	const job = truck.job;
	const cold = truck.kind === "refrigerado";
	const going = job && now < job.arriveAt;
	return tile(truck.id, `${cold ? "Refrigerado" : "Caminhão"} ${index + 1}`, {
		group: "SUA FROTA",
		icon: redeIcon(cold ? "ui-refrigerado" : "ui-frota"),
		tone: free ? "success" : "info",
		sticker: free ? "NO PÁTIO" : going ? "NA ESTRADA" : "VOLTANDO",
		subtitle: free ? "Pronto para sair" : jobLabel[job?.kind ?? ""] ?? "",
		timerEnd: free || !job ? 0 : going ? job.arriveAt : job.returnAt,
		timerTotal: free || !job ? 0 : going ? job.arriveAt - job.departAt : job.returnAt - job.arriveAt,
		state: free ? "" : "busy",
		chips: [stat(gameIcon("deliveryTruck"), fmt(truck.trips), "viagens")],
		detail: `${cold ? "Leva de tudo, inclusive carnes, peixes, laticínios, congelados e sorvetes." : "Leva tudo o que não precisa de frio. Os produtos gelados vão no refrigerado."} Pelo centro de distribuição as caixas saem 10% mais baratas e chegam na metade do tempo.`,
	});
	void state;
}

function fleetPage(state: State) {
	const now = Date.now();
	const chain = state.chain;
	const trucks = chain.fleet.trucks;
	const free = trucks.filter((truck) => isTruckFree(truck, now)).length;
	const tiles = trucks.map((truck, index) => truckTile(state, truck, index, now));
	for (const kind of ["seco", "refrigerado"] as const) {
		const price = getNextTruckPrice(chain, kind);
		if (price === null) continue;
		tiles.push(
			tile(`buy-${kind}`, kind === "seco" ? "Novo caminhão" : "Novo refrigerado", {
				group: "SUA FROTA",
				icon: redeIcon(kind === "seco" ? "ui-frota" : "ui-refrigerado"),
				tone: state.coins >= price ? "gold" : "",
				badge: fmt(price),
				subtitle: "Mais um na sua frota",
				action: act(fmt(price), "buyFleetTruck", [kind], { variant: "coin", icon: gameIcon("coin"), enabled: state.coins >= price, ok: "Caminhão novo no pátio!", fail: "Moedas insuficientes" }),
			}),
		);
	}
	const speedPrice = getNextSpeedPrice(chain);
	const level = chain.fleet.speedLevel;
	tiles.push(
		tile("speed", "Motor turbinado", {
			group: "SUA FROTA",
			icon: gameIcon("deliveryTruck"),
			stars: level,
			maxStars: FLEET_SPEED_FACTORS.length - 1,
			badge: speedPrice === null ? "MÁX" : fmt(speedPrice),
			subtitle:
				speedPrice === null
					? `Viagens ${Math.round((1 - getTripFactor(chain)) * 100)}% mais rápidas`
					: `Próximo nível: viagens ${Math.round((1 - FLEET_SPEED_FACTORS[level + 1]) * 100)}% mais rápidas`,
			tone: speedPrice !== null && state.coins >= speedPrice ? "gold" : "",
			action:
				speedPrice === null
					? button("No máximo", { variant: "secondary", enabled: false })
					: act(fmt(speedPrice), "upgradeFleetSpeed", [], { variant: "coin", icon: gameIcon("coin"), enabled: state.coins >= speedPrice, ok: "A frota ficou mais rápida!", fail: "Moedas insuficientes" }),
		}),
	);
	tiles.push(...privateLabelTiles(state));
	const auto = chain.autoOrder.enabled;
	// (the two orders sit on the yard's bar: the trucks show up on the first view instead of under a big card, Lucas 05/11)
	const orders = [
		act("Pedir o que está acabando", "orderLowStock", ["frota"], {
			icon: redeIcon("ui-pedido-automatico"),
			variant: "primary",
			enabled: free > 0,
			ok: "O caminhão da rede saiu do CD!",
			fail: free > 0 ? "Nada acabando ou sem espaço no estoque." : "Todos os caminhões estão na rua.",
		}),
		act(auto ? "Automático: ligado" : "Automático: desligado", "setChainAutoOrder", [!auto], {
			icon: redeIcon("ui-pedido-automatico"),
			variant: auto ? "success" : "secondary",
			ok: auto ? "Pedido automático desligado" : "Pedido automático ligado",
		}),
	];
	return redePage(state, "cd", "Centro de distribuição", [], tiles, {
		style: "card",
		columns: 4,
		meter: meter("Centro de distribuição", free, trucks.length, { icon: redeIcon("ui-cd"), text: `${free} de ${trucks.length} caminhões no pátio`, tone: free > 0 ? "success" : "warning", buttons: orders }),
		stats: [stat(redeIcon("ui-frota"), fmt(trucks.length), "caminhões"), stat(gameIcon("deliveryTruck"), `${chain.fleet.speedLevel}/${FLEET_SPEED_FACTORS.length - 1}`, "motor")],
		tip:
			free === 0
				? "Toda a frota está na rua. Mais caminhões = mais entregas ao mesmo tempo."
				: auto
					? `Pedido automático ligado: quando algo acaba, um caminhão sai sozinho (mantendo pelo menos ${fmt(AUTO_ORDER_RESERVE)} moedas).`
					: "Ligue o pedido automático e a frota repõe o estoque sozinha.",
	});
}

// ------------------------------------------------------------------------------------------------ Contratos
function contractTile(state: State, offer: ChainContract, now: number): BoardTile {
	const client = chainClients.find((item) => item.id === offer.client);
	const taken = offer.acceptedAt !== null;
	const short = getContractShortfall(offer, state.inventory);
	const truck = pickTruck(state.chain, offer.cold, now);
	const job = taken ? state.chain.fleet.trucks.find((t) => t.id === offer.truckId)?.job : null;
	return tile(offer.id, client?.name ?? "Cliente", {
		group: taken ? "NA ESTRADA" : "PEDIDOS DA CIDADE",
		icon: redeIcon(`cliente-${offer.client}`),
		tone: taken ? "info" : short.length === 0 && truck ? "success" : "",
		sticker: taken ? "A CAMINHO" : offer.cold ? "REFRIGERADO" : "",
		badge: fmt(offer.reward),
		subtitle: offer.lines.map((line) => `${fmt(line.units)}× ${productName(line.productId)}`).join(" · "),
		chips: [stat(gameIcon("success"), `+${fmt(offer.xp)} XP`, ""), ...(offer.diamonds ? [stat(gameIcon("diamond"), `+${offer.diamonds}`, "")] : [])],
		timerEnd: taken && job ? job.arriveAt : offer.expiresAt,
		timerTotal: taken && job ? job.arriveAt - job.departAt : offer.expiresAt - now,
		state: taken ? "busy" : "",
		detail: taken
			? "O cliente paga quando o caminhão chegar."
			: `Entregue do seu estoque e receba ${fmt(offer.reward)} moedas. Viagem: ${minutes(Math.round(offer.tripMs * getTripFactor(state.chain)))}.`,
		lines: short.map((line) => `Falta no estoque: ${fmt(line.missing)}× ${productName(line.productId)}`),
		action: taken
			? button("A caminho", { variant: "secondary", enabled: false })
			: act("Entregar", "acceptChainContract", [offer.id], {
					icon: redeIcon(offer.cold ? "ui-refrigerado" : "ui-frota"),
					variant: "success",
					enabled: short.length === 0 && !!truck,
					ok: `O caminhão saiu para o ${client?.name ?? "cliente"}!`,
					fail: short.length ? "Falta produto no estoque." : offer.cold ? "Nenhum refrigerado livre." : "Todos os caminhões estão na rua.",
				}),
	});
}

function contractsPage(state: State) {
	const now = Date.now();
	const offers = [...state.chain.contracts.offers].sort((a, b) => Number(a.acceptedAt !== null) - Number(b.acceptedAt !== null));
	return redePage(state, "contratos", "Contratos da cidade", [], offers.map((offer) => contractTile(state, offer, now)), {
		style: "row",
		columns: 1,
		empty: "Novos pedidos chegam a cada meia hora.",
		stats: [stat(redeIcon("ui-contratos"), fmt(state.chain.contracts.completed), "entregues"), stat(gameIcon("coin"), fmt(state.chain.contracts.earned), "ganhos")],
		meter: meter("Próximos pedidos", Math.max(0, state.chain.contracts.refreshAt - now), 30 * MIN, {
			icon: gameIcon("target"),
			text: `Novos pedidos em ${minutes(state.chain.contracts.refreshAt - now)}`,
			tone: "info",
		}),
		tip: "Restaurantes, hotéis e escolas compram do seu estoque e pagam bem acima do preço da prateleira.",
	});
}

// ------------------------------------------------------------------------------------------------ Filiais
// Board style "street" (Unity CheckoutDesktopHUD.Street.cs): the five branches side by side as big shop cards, each on a
// panel in its neighbourhood's colour. Lucas 05/11: the pin cards on the city map were ugly and cramped.
const SCENES: Record<ChainBranchId, string> = {
	centro: "CFE0F2",
	praia: "C4EDEA",
	universitario: "D6EDC8",
	vila: "F7DEC2",
	nobre: "E6DAF3",
};

function branchTile(state: State, id: ChainBranchId, now: number): BoardTile {
	const def = getBranchDefinition(id);
	const b = updateBranch(state.chain.branches[id], now);
	const next = getBranchNextStep(b);
	const art = redeIcon(`filial-${id}`);
	const look = `scene:${SCENES[id]}`;
	// (the two favourite goods only: the four of them wrapped into a block of small print)
	const likes = [`Gosta de ${def.favorites.slice(0, 2).map(categoryLabel).join(" e ")}`];
	if (b.works) {
		const cost = getSkipDiamondCost(b.works.endsAt - now);
		return tile(id, def.name, {
			icon: art,
			look,
			tone: "warning",
			sticker: b.level === 0 ? "EM OBRA" : `OBRA DO NÍVEL ${b.works.level}`,
			timerEnd: b.works.endsAt,
			timerTotal: b.level === 0 ? def.buildMs : (getBranchNextStep({ ...b, works: null })?.buildMs ?? def.buildMs),
			state: "busy",
			stars: b.level,
			maxStars: b.level > 0 ? 3 : 0,
			subtitle: b.level === 0 ? "Em construção" : `Subindo para o nível ${b.works.level}`,
			action: act(`Acelerar · ${cost}`, "finishChainBranchNow", [id], { variant: "gem", icon: gameIcon("diamond"), ok: `Filial ${def.name} pronta!`, fail: "Diamantes insuficientes" }),
		});
	}
	if (b.level === 0) {
		const price = next?.price ?? def.price;
		const perHour = getBranchIncomePerMin(id, 1) * 60;
		return tile(id, def.name, {
			icon: art,
			look,
			tone: state.coins >= price ? "gold" : "locked",
			sticker: "À VENDA",
			subtitle: `Até ${fmt(perHour)} por hora`,
			lines: likes,
			action: act(fmt(price), "buyChainBranch", [id], { variant: "coin", icon: gameIcon("coin"), enabled: state.coins >= price, ok: `A obra da filial ${def.name} começou!`, fail: "Moedas insuficientes" }),
		});
	}
	const cargo = chooseBranchCargo(id, b.level, state.inventory, itemCatalog, state.market.unlockedProductIds);
	const truck = pickTruck(state.chain, cargo.cold, now);
	const pending = Math.floor(b.pending);
	const empty = b.supply < 0.25;
	const actions: Button[] = [
		act(b.cargo ? "Carga a caminho" : "Mandar carga", "sendChainBranchCargo", [id], {
			icon: redeIcon("ui-frota"),
			variant: empty && !b.cargo ? "success" : "primary",
			enabled: !b.cargo && cargo.enough && !!truck,
			ok: `O caminhão saiu para a filial ${def.name}!`,
			fail: b.cargo ? "Já tem uma carga a caminho." : !cargo.enough ? "Pouco estoque para uma carga." : "Todos os caminhões estão na rua.",
		}),
	];
	if (next)
		actions.push(
			act(`Nível ${next.level} · ${fmt(next.price)}`, "buyChainBranch", [id], { variant: "coin", icon: gameIcon("coin"), enabled: state.coins >= next.price, ok: `A filial ${def.name} vai crescer!`, fail: "Moedas insuficientes" }),
		);
	return tile(id, def.name, {
		icon: art,
		look,
		tone: empty ? "danger" : "success",
		sticker: empty ? "PRATELEIRAS VAZIAS" : b.cargo ? "CARGA A CAMINHO" : `NÍVEL ${b.level}`,
		stars: b.level,
		maxStars: 3,
		badge: pending > 0 ? fmt(pending) : "",
		fill: b.supply,
		fillText: `Prateleiras ${Math.round(b.supply * 100)}%`,
		timerEnd: b.cargo ? b.cargo.arriveAt : 0,
		timerTotal: b.cargo ? b.cargo.arriveAt - now : 0,
		subtitle: `${fmt(getBranchIncomePerMin(id, b.level) * 60 * b.supply)} por hora`,
		action: actions[0],
		actions,
	});
}

function branchesPage(state: State) {
	const now = Date.now();
	const tiles = chainBranches.map((def) => branchTile(state, def.id, now));
	let pending = 0;
	let owned = 0;
	let supply = 0;
	for (const def of chainBranches) {
		const b = updateBranch(state.chain.branches[def.id], now);
		pending += Math.floor(b.pending);
		if (b.level > 0) {
			owned++;
			supply += b.supply;
		}
	}
	return redePage(state, "filiais", "Filiais pela cidade", [], tiles, {
		style: "street",
		columns: 5,
		meter: meter("Abastecimento da rede", owned ? supply : 0, Math.max(1, owned), {
			icon: redeIcon("ui-abastecimento"),
			text: owned ? `${Math.round((supply / owned) * 100)}% das prateleiras cheias` : "Compre a primeira filial",
			tone: owned && supply / owned < 0.3 ? "danger" : "success",
			buttons: [
				act(pending > 0 ? `Coletar ${fmt(pending)}` : "Nada para coletar", "collectChainBranches", [], {
					icon: gameIcon("coin"),
					variant: "coin",
					enabled: pending > 0,
					ok: `+${fmt(pending)} moedas das filiais!`,
				}),
			],
		}),
		stats: [stat(redeIcon("ui-filiais"), `${owned}/${chainBranches.length}`, "filiais"), stat(gameIcon("coin"), fmt(pending), "para coletar")],
	});
}

export const routes: Routes = {
	rede: (state, [tab, arg]) => {
		if (!isChainUnlocked(state.era.id)) return lockedPage(state);
		// The chain has to be named first (the card opens by itself when the rede is done).
		if (state.chain.brand.namedAt === null) return brandPage(state, tab === "marca" ? arg : undefined);
		switch (tab as Tab) {
			case "cd":
				return fleetPage(state);
			case "contratos":
				return contractsPage(state);
			case "marca":
				return brandPage(state, arg);
			default:
				// the toolbar's Rede button lands on the branches (the brand is one tab away)
				return branchesPage(state);
		}
	},
};
