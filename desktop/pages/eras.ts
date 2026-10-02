import { formatBuildDuration, formatConstructionCountdown, getMarketExpansionSkipCost } from "@/data/market-expansions";
import { getMarketEra, getNextMarketEra, marketEras } from "@/data/economy";
import { act, button, type Card, card, fmt, gameIcon, type State } from "../view-kit";
import { missingLotsLine } from "./lots";

// Evolution of the market, era by era: from the table on the sidewalk to the chain of hypermarkets.
// The player only sees "expansões": shown in the Loja ("Expansões") and in the DEV cheats.

const perks = (id: string) => {
	const era = getMarketEra(id as never);
	const parts = [
		`${era.productSlots} lugares de produto`,
		era.arrivalMultiplier !== 1 ? `clientes ×${era.arrivalMultiplier.toLocaleString("pt-BR")}` : "",
		era.ticketMultiplier > 1 ? `cesta ×${era.ticketMultiplier.toLocaleString("pt-BR")}` : "",
		era.offlineTurnsPerHour > 0
			? `vende sozinho ${Math.round(era.offlineTurnsPerHour * 100)}% de um turno por hora fora`
			: "não vende sem você",
		era.nightTurn ? "abre à noite" : "",
	];
	return parts.filter(Boolean).join(" · ");
};

/** The current era, the next one (buy / obra / accelerate) and the road ahead. */
export function eraCards(state: State, { roadmap = true } = {}): Card[] {
	const now = Date.now();
	const current = getMarketEra(state.era.id);
	const next = getNextMarketEra(state.era.id);
	const cards: Card[] = [
		card(current.name, {
			eyebrow: `EXPANSÃO ${current.index} · SEU MERCADO`,
			icon: gameIcon("market"),
			tone: "success",
			badge: "Atual",
			subtitle: perks(current.id),
		}),
	];
	const obra = state.era.construction;
	if (obra) {
		const target = getMarketEra(obra.eraId);
		const total = Math.max(1, obra.endsAt - obra.startedAt);
		const remaining = Math.max(0, obra.endsAt - now);
		const cost = getMarketExpansionSkipCost(remaining);
		cards.push(
			card(target.name, {
				eyebrow: `EXPANSÃO ${target.index} · EM OBRA`,
				icon: gameIcon("construction"),
				tone: "warning",
				badge: formatConstructionCountdown(remaining),
				progress: 1 - remaining / total,
				subtitle: "Os construtores estão montando a próxima expansão.",
				lines: [`Pronto em ${formatConstructionCountdown(remaining)}`, perks(target.id)],
				buttons: [
					act(`Acelerar · ${cost}`, "finishMarketEraNow", [], {
						variant: "gem",
						icon: gameIcon("diamond"),
						enabled: state.logistics.premiumCurrency >= cost,
						ok: `${target.name} pronto!`,
						fail: "Diamantes insuficientes",
					}),
				],
			}),
		);
	} else if (next) {
		const lotsMissing = missingLotsLine(state, next.id);
		const affordable = state.coins >= next.coinCost && !lotsMissing;
		cards.push(
			card(next.name, {
				eyebrow: `EXPANSÃO ${next.index} · PRÓXIMA`,
				icon: gameIcon("market"),
				tone: affordable ? "featured" : "",
				badge: next.buildDurationMs > 0 ? `obra ${formatBuildDuration(next.buildDurationMs)}` : "na hora",
				subtitle: perks(next.id),
				lines: [
					lotsMissing
						? lotsMissing
						: affordable
							? "Evolua agora: a obra começa na hora."
							: `Faltam ${fmt(next.coinCost - state.coins)} moedas.`,
				],
				buttons: [
					act(fmt(next.coinCost), "evolveMarketEra", [], {
						variant: "coin",
						icon: gameIcon("coin"),
						enabled: affordable,
						ok: `Obra de ${next.name} começou!`,
						fail: lotsMissing ? "Compre e limpe os terrenos antes." : "Moedas insuficientes",
					}),
					...(lotsMissing ? [button("Terrenos", { route: "~loja:terrenos", variant: "secondary", icon: gameIcon("key") })] : []),
				],
			}),
		);
	}
	if (roadmap) {
		for (const era of marketEras.slice((obra ? getMarketEra(obra.eraId) : (next ?? current)).index + 1)) {
			cards.push(
				card(era.name, {
					eyebrow: `EXPANSÃO ${era.index} · MAIS À FRENTE`,
					icon: gameIcon("lock"),
					tone: "locked",
					badge: fmt(era.coinCost),
					subtitle: perks(era.id),
					lines: [`Obra de ${formatBuildDuration(era.buildDurationMs)} · por volta do dia ${era.targetDay}`],
				}),
			);
		}
	}
	return cards;
}

const shortName = (name: string) => {
	const short = name.replace(" na calçada", "").replace(" de feira", "").replace(" de filiais", "").replace("Mini-", "");
	return short.charAt(0).toLocaleUpperCase("pt-BR") + short.slice(1);
};

/** DEV: jump to any era and pass time away from the game. */
export function devEraCards(state: State): Card[] {
	return [
		...[0, 3, 6, 9].map((start) =>
			card(`Pular para a expansão ${start} a ${Math.min(start + 2, marketEras.length - 1)}`, {
				eyebrow: "EXPANSÕES",
				icon: gameIcon("market"),
				badge: start === 0 ? getMarketEra(state.era.id).name : "",
				subtitle: start === 0 ? "Muda a expansão na hora, sem custo e sem obra." : "",
				buttons: marketEras.slice(start, start + 3).map((era) =>
					act(shortName(era.name), "devSetMarketEra", [era.id], {
						variant: era.id === state.era.id ? "success" : "secondary",
						ok: `Agora: ${era.name}`,
					}),
				),
			}),
		),
		card("Passar tempo fora do jogo", {
			eyebrow: "TEMPO",
			icon: gameIcon("sleepy"),
			subtitle:
				"Como se você tivesse saído: a obra da expansão anda e o mercado aberto vende sozinho (até 8 h por vez).",
			lines: [
				state.era.averageTurnProfit > 0
					? `Um turno seu rende em média ${fmt(state.era.averageTurnProfit)} moedas.`
					: "Termine um turno para o jogo saber quanto vale uma hora fora.",
			],
			buttons: [1, 4, 8].map((hours) =>
				act(`+${hours} h`, "devPassTime", [hours], { variant: "success", ok: `Passaram ${hours} h` }),
			),
		}),
	];
}
