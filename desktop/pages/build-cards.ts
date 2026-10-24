import { getEraOrder, shelves } from "@/data/market-products";
import type { MarketEraId } from "@/@types/economy";
import {
	formatBuildDuration,
	formatConstructionCountdown,
} from "@/data/market-expansions";
import type { InteriorBuildStatus } from "@/services/interior-construction";
import { NO_ROOM_HINT } from "@/services/interior-room";
import { act, button, type Button, type Card, card, decorIcon, fmt, gameIcon, type State } from "../view-kit";

// Things the builders put up inside the market (shelves, sectors, checkouts). Buying one does not
// build it: it goes to the inventory, the player places it in the build mode ("@build") and the
// works start there, one at a time in the builders' queue.

/** Opens the build mode with the inventory ("Para colocar"). */
export const placeButton = (label = "Colocar na loja") =>
	button(label, { route: "@build", variant: "success", icon: gameIcon("hammer") });

/** Thumbnail of a shelf model (same templates as CheckoutInterior.ShelfTemplate); with `eraId`, the look it has in
 * that expansion (up to the contêiner the bakery is the bread basket, "Cesto de pães"). */
export function shelfThumb(shelfId: string, eraId?: MarketEraId) {
	if (shelfId === "bakery" && eraId && getEraOrder(eraId) < getEraOrder("spati")) return decorIcon("bread-basket");
	const template: Record<string, string> = {
		produce: "shelf-produce",
		dairy: "shelf-dairy",
		bakery: "shelf-bakery",
		snacks: "shelf-snacks",
		drinks: "shelf-cooler",
		coffee: "shelf-grocery",
		pizza: "shelf-freezer",
		home: "shelf-cleaning",
		icecream: "shelf-freezer",
	};
	return decorIcon(template[shelfId] ?? "shelf-grocery");
}
export const shelfName = (shelfId: string) => shelves.find((shelf) => shelf.id === shelfId)?.name ?? "Prateleira";

export type BuildOffer = {
	title: string;
	icon: string;
	subtitle: string;
	status: InteriorBuildStatus;
	/** Store action + args to buy with coins / diamonds (omitted when that currency is not offered). */
	coins?: { action: string; args: unknown[]; price: number };
	diamonds?: { action: string; args: unknown[]; price: number };
	/** Shown on the finished item. */
	builtLine?: string;
};

const bought = "Comprado! Está no inventário: toque em Colocar e escolha o lugar.";

/** One buildable in any state: to buy, in the inventory, queued, under construction or ready. */
export function buildCard(state: State, offer: BuildOffer): Card {
	const { status } = offer;
	const diamonds = state.logistics.premiumCurrency;
	const speedUp = (label: string): Button[] =>
		status.construction
			? [
					act(`${label} · ${status.skipCost}`, "finishInteriorConstructionNow", [status.construction.id], {
						variant: "gem",
						icon: gameIcon("diamond"),
						enabled: true, // too few diamonds opens the diamond store (desktop/host.ts)
						ok: `${offer.title} pronto!`,
						fail: "Diamantes insuficientes",
					}),
				]
			: [];
	switch (status.status) {
		case "built":
			return card(offer.title, {
				eyebrow: "NA SUA LOJA",
				icon: offer.icon,
				tone: "success",
				badge: "Pronto",
				subtitle: offer.subtitle,
				lines: offer.builtLine ? [offer.builtLine] : [],
			});
		case "stored":
			return card(offer.title, {
				eyebrow: "NO INVENTÁRIO",
				icon: offer.icon,
				tone: "info",
				badge: "Guardado",
				subtitle: "Escolha o lugar no modo construir: a obra começa quando você concluir.",
				lines: [`Obra de ${formatBuildDuration(status.durationMs)}`],
				buttons: [placeButton()],
			});
		case "queued":
			return card(offer.title, {
				eyebrow: "NA FILA DA OBRA",
				icon: gameIcon("construction"),
				tone: "warning",
				badge: "Na fila",
				subtitle: "Os construtores começam logo depois da obra atual.",
				lines: [
					`Começa em ${formatConstructionCountdown(Math.max(0, (status.construction?.startedAt ?? 0) - Date.now()))}`,
					`Obra de ${formatBuildDuration(status.durationMs)}`,
				],
				buttons: speedUp("Pronto já"),
			});
		case "building":
			return card(offer.title, {
				eyebrow: "EM OBRA",
				icon: gameIcon("construction"),
				tone: "warning",
				badge: formatConstructionCountdown(status.remainingMs),
				progress: status.progress,
				subtitle: "Os construtores estão trabalhando no mercado.",
				lines: [`Pronto em ${formatConstructionCountdown(status.remainingMs)}`],
				buttons: speedUp("Acelerar"),
			});
		default: {
			const locked = status.status === "locked";
			const buttons: Button[] = [];
			if (offer.coins)
				buttons.push(
					act(locked ? status.reason : fmt(offer.coins.price), offer.coins.action, offer.coins.args, {
						variant: "coin",
						icon: locked ? "" : gameIcon("coin"),
						enabled: !locked && state.coins >= offer.coins.price,
						ok: bought,
						fail: locked ? status.reason : "Moedas insuficientes",
					}),
				);
			if (offer.diamonds && !locked)
				buttons.push(
					act(fmt(offer.diamonds.price), offer.diamonds.action, offer.diamonds.args, {
						variant: "gem",
						icon: gameIcon("diamond"),
						enabled: true,
						ok: bought,
						fail: "Diamantes insuficientes",
					}),
				);
			return card(offer.title, {
				eyebrow: locked ? "BLOQUEADO" : "À VENDA",
				icon: offer.icon,
				tone: locked ? "locked" : "",
				badge: formatBuildDuration(status.durationMs),
				subtitle: offer.subtitle,
				// locked: the button already says why; with no room on the floor, what to do about it.
				lines: status.noRoom ? [NO_ROOM_HINT] : locked ? [] : ["Vai para o inventário: você escolhe onde construir."],
				buttons: status.noRoom ? [...buttons, placeButton("Organizar a loja")] : buttons,
			});
		}
	}
}
