import { formatBuildDuration, formatConstructionCountdown, getMarketExpansionSkipCost } from "@/data/market-expansions";
import { ERA_LOTS, MARKET_LOTS } from "@/data/market-lots";
import { getMarketEra, marketEras } from "@/data/economy";
import {
	getLotClearCost,
	getLotClearDuration,
	getLotClearExperience,
	getLotStatus,
} from "@/services/market-lots";
import { act, button, type Card, card, fmt, gameIcon, type State } from "../view-kit";

// Land (Loja → Terrenos): buy the lots around the market and clear what stands on them. Each lot says which
// expansion needs it, so the player knows what he is saving for.

/** First expansion that stands on (or needs) each lot. */
function neededBy(lotId: string) {
	const era = marketEras.find((item) => (ERA_LOTS[item.id] ?? []).includes(lotId));
	return era ? era.name : "";
}

export function lotCards(state: State): Card[] {
	const now = Date.now();
	const cards: Card[] = [];
	for (const lot of MARKET_LOTS) {
		const status = getLotStatus(state.lots, lot.id);
		if (status === "praca") continue;
		const needs = neededBy(lot.id);
		const forWhat = needs ? `Necessário para: ${needs}` : "";
		const clearCost = getLotClearCost(lot);
		const clearTime = formatBuildDuration(getLotClearDuration(lot));
		if (status === "seu") {
			cards.push(
				card(lot.label, {
					eyebrow: "SEU TERRENO",
					icon: gameIcon("success"),
					tone: "success",
					badge: "Limpo",
					subtitle: (ERA_LOTS[state.era.id] ?? []).includes(lot.id)
						? "O seu mercado está aqui."
						: "Livre para decorar enquanto o mercado não chega aqui.",
					lines: forWhat ? [forWhat] : [],
					buttons: [],
				}),
			);
		} else if (status === "limpando" && state.lots.clearing) {
			const total = Math.max(1, state.lots.clearing.endsAt - state.lots.clearing.startedAt);
			const remaining = Math.max(0, state.lots.clearing.endsAt - now);
			const cost = getMarketExpansionSkipCost(remaining);
			cards.push(
				card(lot.label, {
					eyebrow: "LIMPANDO",
					icon: gameIcon("construction"),
					tone: "warning",
					badge: formatConstructionCountdown(remaining),
					progress: 1 - remaining / total,
					subtitle: `A equipe está tirando: ${lot.ruinName}.`,
					lines: [forWhat, `+${getLotClearExperience(lot)} XP quando terminar`].filter(Boolean),
					buttons: [
						act(`Acelerar · ${cost}`, "finishLotClearingNow", [], {
							variant: "gem",
							icon: gameIcon("diamond"),
							enabled: state.logistics.premiumCurrency >= cost,
							ok: `${lot.label} limpo!`,
							fail: "Diamantes insuficientes",
						}),
					],
				}),
			);
		} else if (status === "comprado") {
			const busy = Boolean(state.lots.clearing);
			cards.push(
				card(lot.label, {
					eyebrow: "COMPRADO · FALTA LIMPAR",
					icon: gameIcon("broom"),
					tone: "featured",
					badge: clearTime,
					subtitle: `Ainda tem: ${lot.ruinName}. Contrate a equipe de limpeza para o terreno ficar pronto.`,
					lines: [forWhat, `Limpeza: ${fmt(clearCost)} moedas · ${clearTime} · +${getLotClearExperience(lot)} XP`].filter(Boolean),
					buttons: [
						act(busy ? "Equipe ocupada" : `Limpar · ${fmt(clearCost)}`, "clearLot", [lot.id], {
							variant: "coin",
							icon: gameIcon("coin"),
							enabled: !busy && state.coins >= clearCost,
							ok: `A limpeza do ${lot.label} começou!`,
							fail: busy ? "A equipe já está limpando outro terreno." : "Moedas insuficientes",
						}),
					],
				}),
			);
		} else {
			const locked = status === "bloqueado";
			cards.push(
				card(lot.label, {
					eyebrow: locked ? "AINDA LONGE" : "À VENDA",
					icon: gameIcon(locked ? "lock" : "key"),
					tone: locked ? "locked" : state.coins >= lot.price ? "featured" : "",
					badge: fmt(lot.price),
					subtitle: locked
						? "Compre antes um terreno vizinho (o Lote A1, na esquina, vem primeiro)."
						: `Tem ${lot.ruinName.toLocaleLowerCase("pt-BR")}: depois de comprar, é preciso limpar (${fmt(clearCost)} moedas · ${clearTime}).`,
					lines: forWhat ? [forWhat] : [],
					buttons: [
						act(fmt(lot.price), "buyLot", [lot.id], {
							variant: "coin",
							icon: gameIcon("coin"),
							enabled: !locked && state.coins >= lot.price,
							ok: `${lot.label} é seu! Agora é só limpar.`,
							fail: locked ? "Compre antes um terreno vizinho." : "Moedas insuficientes",
						}),
					],
				}),
			);
		}
	}
	return cards;
}

/** Short line for the expansion card: which lots the next expansion still needs. */
export function missingLotsLine(state: State, eraId: string) {
	const missing = (ERA_LOTS[eraId as keyof typeof ERA_LOTS] ?? []).filter((id) => !(state.lots?.cleared ?? []).includes(id));
	if (!missing.length) return "";
	const labels = missing.map((id) => MARKET_LOTS.find((lot) => lot.id === id)?.label ?? id);
	return `Precisa ${missing.length === 1 ? "do terreno" : "dos terrenos"} ${labels.join(", ")} comprado${missing.length === 1 ? "" : "s"} e limpo${missing.length === 1 ? "" : "s"} (Loja → Terrenos) para ${getMarketEra(eraId as never).name}.`;
}
