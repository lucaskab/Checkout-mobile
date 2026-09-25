import { gameEvents } from "@/data/game-events";
import { getGameEventIcon } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import type { Routes } from ".";
import {
	act,
	type Button,
	type Card,
	card,
	fmt,
	gameIcon,
	type Page,
	page,
	productIcon,
	swap,
	type State,
} from "../view-kit";

// Mirrors src/components/dev-cheat-sheet (DEV Cheats) plus a reset section.
const categories = [
	{ id: "moedas", label: "Moedas" },
	{ id: "nivel", label: "Nível" },
	{ id: "eventos", label: "Eventos" },
	{ id: "estoque", label: "Estoque" },
	{ id: "reset", label: "Reset" },
] as const;
type Category = (typeof categories)[number]["id"];

// Highest level anything unlocks at (products).
const maxLevel = Math.max(...itemCatalog.map((product) => product.unlockLevel));

// Same as formatStep in src/components/dev-cheat-sheet/index.tsx.
function formatStep(step: number) {
	const absoluteStep = Math.abs(step);
	const sign = step > 0 ? "+" : "−";
	if (absoluteStep >= 1_000) return `${sign}${absoluteStep / 1_000}K`;
	return `${sign}${absoluteStep}`;
}

const steps = (action: string, values: number[]): Button[] =>
	values.map((step) =>
		act(formatStep(step), action, [step], {
			variant: step > 0 ? "success" : "danger",
		}),
	);

const warning = card("DEV Cheats", {
	eyebrow: "DEV ONLY",
	icon: gameIcon("warning"),
	tone: "warning",
	subtitle: "Alterações persistidas neste save local.",
});

function devPage(category: Category, cards: Card[], route = `dev:${category}`): Page {
	return page(route, "DEV Cheats", [warning, ...cards], {
		subtitle: "Altere o estado do jogo para validar níveis, economia e estoque.",
		icon: gameIcon("toolbox"),
		chips: categories.map((c) => swap(c.label, `dev:${c.id}`, c.id === category)),
	});
}

type Builder = (state: State, args: string[]) => Page;
const builders: Record<Category, Builder> = {
	moedas: (state) =>
		devPage("moedas", [
			card("Moedas", {
				eyebrow: "ECONOMIA",
				icon: gameIcon("coin"),
				badge: fmt(state.coins),
				subtitle: "Teste compras, melhorias e acelerações instantâneas.",
				buttons: steps("devAdjustCoins", [-1_000, -10_000, -100_000]),
			}),
			card("Adicionar moedas", {
				icon: gameIcon("coin"),
				badge: fmt(state.coins),
				buttons: steps("devAdjustCoins", [1_000, 10_000, 100_000]),
			}),
			card("Diamantes", {
				eyebrow: "ECONOMIA",
				icon: gameIcon("diamond"),
				badge: fmt(state.logistics.premiumCurrency),
				buttons: steps("devAdjustDiamonds", [-10, -100, -1_000]),
			}),
			card("Adicionar diamantes", {
				icon: gameIcon("diamond"),
				badge: fmt(state.logistics.premiumCurrency),
				buttons: steps("devAdjustDiamonds", [10, 100, 1_000]),
			}),
		]),
	nivel: (state) => {
		const level = state.market.level;
		const levels = Array.from({ length: maxLevel }, (_, index) => index + 1);
		const rows: Card[] = [];
		for (let start = 0; start < levels.length; start += 4)
			rows.push(
				card(`Níveis ${levels[start]}–${levels[Math.min(start + 3, levels.length - 1)]}`, {
					icon: gameIcon("medal"),
					tone: level >= levels[start] && level <= levels[start] + 3 ? "info" : "",
					buttons: levels.slice(start, start + 4).map((preset) =>
						act(`Lv. ${preset}`, "setMarketLevel", [preset], {
							variant: level === preset ? "primary" : "secondary",
							active: level === preset,
						}),
					),
				}),
			);
		return devPage("nivel", [
			card("Nível do jogador", {
				eyebrow: "PROGRESSÃO",
				icon: gameIcon("medal"),
				badge: `Nv ${level}`,
				subtitle: "Mudar o nível recalcula os produtos liberados.",
				lines: [`Máximo com conteúdo: ${maxLevel}`],
				buttons: [
					act("−5", "setMarketLevel", [level - 5], { variant: "danger", enabled: level > 1 }),
					act("−1", "setMarketLevel", [level - 1], { variant: "danger", enabled: level > 1 }),
					act("+1", "setMarketLevel", [level + 1], { variant: "success" }),
					act("+5", "setMarketLevel", [level + 5], { variant: "success" }),
				],
			}),
			...rows,
		]);
	},
	eventos: (state) => {
		const active = state.events.activeEvent;
		const now = Date.now();
		return devPage(
			"eventos",
			gameEvents.map((event) => {
				const isActive = active?.eventId === event.id && active.endsAt > now;
				const isPositive = event.kind === "positive";
				const seconds = isActive && active ? Math.ceil((active.endsAt - now) / 1000) : 0;
				return card(event.name, {
					eyebrow: isPositive ? "POSITIVO" : "NEGATIVO",
					subtitle: event.effectLabel,
					icon: gameIcon(getGameEventIcon(event.id)),
					badge: isActive ? "ATIVO" : `${event.durationMinutes} min`,
					tone: isActive ? "info" : isPositive ? "success" : "danger",
					lines: isActive
						? [`Faltam ${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`]
						: [],
					buttons: [
						act(isActive ? "Reativar" : "Ativar", "devActivateGameEvent", [event.id], {
							variant: isPositive ? "success" : "danger",
							ok: `${event.name} ativado`,
							fail: "Não foi possível ativar o evento",
						}),
					],
				});
			}),
		);
	},
	// "dev:estoque:<liberados|bloqueados>:<pagina>"
	estoque: (state, [filterArg, pageArg]) => {
		const filter = filterArg === "bloqueados" ? "bloqueados" : "liberados";
		const unlocked = new Set(state.market.unlockedProductIds);
		const list = itemCatalog.filter((product) =>
			filter === "liberados" ? unlocked.has(product.id) : !unlocked.has(product.id),
		);
		const size = 40;
		const pages = Math.max(1, Math.ceil(list.length / size));
		const current = Math.min(pages - 1, Math.max(0, Number(pageArg) || 0));
		const lockedCount = itemCatalog.length - unlocked.size;
		const nav: Button[] = [
			swap(`Liberados (${unlocked.size})`, "dev:estoque:liberados:0", filter === "liberados"),
			swap(`Bloqueados (${lockedCount})`, "dev:estoque:bloqueados:0", filter === "bloqueados"),
		];
		if (pages > 1)
			nav.push(
				swap("‹", `dev:estoque:${filter}:${Math.max(0, current - 1)}`, false),
				swap("›", `dev:estoque:${filter}:${Math.min(pages - 1, current + 1)}`, false),
			);
		const cards: Card[] = [
			card("Estoque", {
				eyebrow: "DEV",
				icon: gameIcon("basket"),
				badge: pages > 1 ? `${current + 1}/${pages}` : "",
				subtitle: "Altere a quantidade de um item no estoque.",
				buttons: nav,
			}),
		];
		for (const product of list.slice(current * size, (current + 1) * size)) {
			const stock = state.inventory[product.id] ?? 0;
			const capacity = getInventoryCapacity(
				product,
				state.inventoryCapacityLevels[product.id],
			);
			const isUnlocked = unlocked.has(product.id);
			cards.push(
				card(product.name, {
					eyebrow: `ID ${product.id} · nível ${product.unlockLevel}`,
					icon: productIcon(product.id),
					badge: isUnlocked ? `${fmt(stock)}/${fmt(capacity)}` : "Bloqueado",
					tone: isUnlocked ? "" : "locked",
					buttons: isUnlocked
						? [
								act("−10", "devAdjustInventory", [product.id, -10], { variant: "danger", enabled: stock > 0 }),
								act("+1", "devAdjustInventory", [product.id, 1], { variant: "success", enabled: stock < capacity }),
								act("+10", "devAdjustInventory", [product.id, 10], { variant: "success", enabled: stock < capacity }),
								act("+100", "devAdjustInventory", [product.id, 100], { variant: "success", enabled: stock < capacity }),
							]
						: [
								act("Liberar", "unlockProduct", [product.id], {
									variant: "primary",
									ok: `${product.name} liberado`,
								}),
							],
				}),
			);
		}
		return devPage("estoque", cards, `dev:estoque:${filter}:${current}`);
	},
	reset: () =>
		devPage("reset", [
			card("Reiniciar jogo", {
				eyebrow: "PERIGO",
				icon: gameIcon("warning"),
				tone: "danger",
				subtitle: "Apaga todo o progresso deste save (compras de moeda são mantidas).",
				buttons: [
					act("Reiniciar jogo", "resetGame", [], {
						variant: "danger",
						ok: "Jogo reiniciado",
					}),
				],
			}),
		]),
};

export const routes: Routes = {
	dev: (state, [arg, ...rest]) => {
		const category: Category = categories.some((c) => c.id === arg)
			? (arg as Category)
			: "moedas";
		return builders[category](state, rest);
	},
};
