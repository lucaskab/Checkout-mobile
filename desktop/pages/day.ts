import type { DayContract } from "@/@types/market-day";
import { canOpenAtNight, getPiecesToPlaceBeforeOpening, NIGHT_TURN } from "@/services/market-era";
import type { GameIconId } from "@/data/game-icon-assets";
import {
	DAY_DURATION_MS,
	FREE_DAY_CONTRACT_ID,
	getContractProgress,
} from "@/services/market-day";
import {
	act,
	type Card,
	card,
	fmt,
	gameIcon,
	page,
	type State,
} from "../view-kit";
import type { Routes } from ".";
import { canClaimConsolation, getConsolationOffer } from "@/services/contract-pressure";
import { adsStore, getLastAdEvent, isAdOpening } from "../ads";

// Desktop pages for the market day, mirroring src/components/market-day.
const clock = (ms: number) => {
	const seconds = Math.max(0, Math.ceil(ms / 1_000));
	return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};
const difficulty = { 1: "Fácil", 2: "Médio", 3: "Difícil" } as const;
const contractIcons: GameIconId[] = [
	"coin",
	"receipt",
	"customers",
	"handshake",
	"success",
	"medal",
	"target",
];
const iconOf = (icon: string) =>
	gameIcon(
		contractIcons.includes(icon as GameIconId)
			? (icon as GameIconId)
			: "target",
	);

function contractCard(contract: DayContract, canOpen = true) {
	const rewards = [
		`+${fmt(contract.reward.coins)} moedas`,
		`+${contract.reward.experience} XP`,
		...(contract.reward.diamonds
			? [`+${contract.reward.diamonds} diamante`]
			: []),
	];
	return card(contract.title, {
		eyebrow: contract.challenge ? "CONTRATO · DESAFIO DO DIA" : `CONTRATO · ${difficulty[contract.difficulty]}`,
		subtitle: contract.challenge
			? // two sentences, each translated on its own (the description comes from the contract data)
				[contract.description, "Você está mandando bem: este vale mais!"].join(" ")
			: contract.description,
		icon: iconOf(contract.icon),
		badge: contract.challenge ? "Desafio" : difficulty[contract.difficulty],
		tone: contract.challenge ? "featured" : contract.difficulty === 3 ? "warning" : "",
		lines: [`Recompensa: ${rewards.join(" · ")}`],
		buttons: [
			act("Aceitar e abrir", "startDay", [contract.id], {
				variant: "success",
				icon: gameIcon("key"),
				// furniture still waiting to be placed: the card above says so, the button waits too
				enabled: canOpen,
				after: "back",
				ok: `Dia aberto: ${contract.title}`,
				fail: "Coloque seus móveis no modo Construir antes de abrir.",
			}),
		],
	});
}

function dayStatus(state: State, now: number): Card {
	const { day } = state;
	const progress = getContractProgress(day.contract, day.stats);
	return card(day.contract?.title ?? "Dia livre", {
		eyebrow: `DIA ${day.dayNumber} · ${clock((day.endsAt ?? now) - now)} restantes`,
		subtitle:
			day.contract?.description ??
			"Sem contrato: a nota vem da satisfação dos clientes.",
		icon: gameIcon("clipboard"),
		badge: day.contract ? progress.label : "",
		tone: progress.completed ? "success" : "",
		progress: day.contract ? progress.ratio : -1,
		lines: [
			`${day.stats.customers} clientes · ${fmt(day.stats.revenue)} moedas · lucro ${fmt(day.stats.profit)}`,
		],
		buttons: [
			act("Encerrar o dia", "closeDay", [], {
				variant: "danger",
				icon: gameIcon("lock"),
				ok: "Mercado fechado",
			}),
		],
	});
}

function planning(state: State) {
	const { day } = state;
	const minutes = Math.round(DAY_DURATION_MS / 60_000);
	const waiting = getPiecesToPlaceBeforeOpening(state);
	return page(
		"day",
		`Dia ${day.dayNumber}`,
		[
			...(waiting > 0
				? [
						card("Monte a sua loja primeiro", {
							eyebrow: "MÓVEIS PARA COLOCAR",
							subtitle: `Você tem ${waiting} ${waiting === 1 ? "móvel" : "móveis"} esperando. Toque em Construir e coloque o caixa e as prateleiras onde quiser para poder abrir.`,
							icon: gameIcon("hammer"),
							tone: "warning",
						}),
					]
				: []),
			card("Escolha o contrato de hoje", {
				eyebrow: `PLANEJAMENTO · ${minutes} MIN`,
				subtitle:
					"Cumpra a meta antes de fechar para ganhar a recompensa. Clientes satisfeitos melhoram a nota do dia.",
				icon: gameIcon("clipboard"),
			}),
			...day.offers.map((offer) => contractCard(offer, waiting === 0)),
			// No "Dia livre" card (Lucas 19/10): a contract only adds a prize, so there is no reason to skip one.
			// From the Späti on the shop can also open at night.
			...(canOpenAtNight(state.era.id)
				? [
						card("Turno da noite", {
							eyebrow: "SÓ A PARTIR DO SPÄTI",
							subtitle: "Abre à noite, sem contrato. Vêm menos clientes, mas eles gastam mais e procuram bebidas, doces e congelados.",
							icon: gameIcon("sleepy"),
							lines: [
								`Clientes ×${NIGHT_TURN.arrivalMultiplier.toLocaleString("pt-BR")} · gasto por cliente ×${NIGHT_TURN.budgetMultiplier.toLocaleString("pt-BR")}`,
								"Bebidas, doces, salgadinhos e congelados vendem mais",
							],
							buttons: [
								act("Abrir à noite", "startDay", [FREE_DAY_CONTRACT_ID, "noite"], {
									variant: "primary",
									enabled: waiting === 0,
									after: "back",
									ok: "Turno da noite aberto!",
									fail: waiting > 0 ? "Coloque seus móveis no modo Construir antes de abrir." : "Não foi possível abrir agora.",
								}),
							],
						}),
					]
				: []),
		],
		{ icon: gameIcon("clipboard"), subtitle: "Contrato do dia" },
	);
}

// The day running: its contract, clock and numbers so far.
function openDay(state: State) {
	return page(
		"day",
		`Dia ${state.day.dayNumber}`,
		[dayStatus(state, Date.now())],
		{ icon: gameIcon("clipboard"), subtitle: state.day.shift === "noite" ? "Turno da noite" : "Contrato do dia" },
	);
}

// A missed contract: right away, a prize for watching a video (always given, shown before the video).
function consolationCards(state: State): Card[] {
	const result = state.day.result;
	if (!result?.contract || result.contractCompleted) return [];
	if (result.consolation)
		return [
			card("Prêmio de consolação", {
				eyebrow: "VÍDEO ASSISTIDO",
				subtitle: `Você ganhou ${result.consolation.label}. Amanhã tem outro contrato!`,
				icon: gameIcon("gift"),
				tone: "success",
				badge: "Recebido",
			}),
		];
	const offer = getConsolationOffer(result);
	if (!offer) return [];
	const missing = Math.max(0, 100 - Math.round(result.contractProgress * 100));
	const waiting = isAdOpening("consolation");
	const last = getLastAdEvent();
	return [
		card(missing <= 25 ? `Quase! Faltaram só ${missing}%` : "Não foi dessa vez", {
			eyebrow: "PRÊMIO DE CONSOLAÇÃO",
			subtitle: `Assista um vídeo curto e leve ${offer.coins} moedas na hora, mais um prêmio surpresa.`,
			icon: gameIcon("gift"),
			tone: "featured",
			badge: "Grátis",
			lines: [
				`Garantido: +${fmt(offer.coins)} moedas`,
				`Surpresa (um deles): ${offer.surprises.join(" · ")}`,
				...(last && last.kind !== "rewarded" && !waiting
					? [last.kind === "closed" ? "Vídeo fechado antes do fim · sem prêmio" : "O vídeo não carregou. Tente de novo."]
					: []),
			],
			buttons: [
				act(waiting ? "Abrindo o vídeo…" : "Assistir e ganhar", "watchRewardedAd", ["consolation"], {
					variant: "gem",
					icon: gameIcon("television"),
					enabled: canClaimConsolation(result) && !waiting && adsStore.status !== "unavailable",
					ok: "",
					fail: adsStore.status === "unavailable" ? "Nenhum vídeo disponível agora." : "",
				}),
			],
		}),
	];
}

function results(state: State) {
	const result = state.day.result;
	if (!result) return planning(state);
	const { stats } = result;
	return page(
		"day-result",
		`Dia ${result.dayNumber} encerrado`,
		[
			...consolationCards(state),
			card(`Nota ${result.grade}`, {
				eyebrow: `${result.score} DE 100 PONTOS`,
				subtitle: result.contract
					? `${result.contract.title}: ${result.contractCompleted ? "contrato cumprido!" : `${Math.round(result.contractProgress * 100)}% da meta`}`
					: "Dia livre",
				icon: gameIcon(result.contractCompleted ? "trophy" : "medal"),
				tone:
					result.grade === "S" || result.grade === "A"
						? "success"
						: result.grade === "D"
							? "danger"
							: "warning",
				badge: result.grade,
				lines: [
					`Faturamento ${fmt(stats.revenue)} · lucro nas vendas ${fmt(stats.profit)}`,
					`${stats.customers} clientes · satisfação média ${result.averageSatisfaction}%`,
					...result.highlights,
				],
			}),
			card("Recompensas do dia", {
				icon: gameIcon("coin"),
				tone: "warning",
				lines: [
					`+${fmt(result.total.coins)} moedas · +${result.total.experience} XP${result.total.diamonds ? ` · +${result.total.diamonds} diamante` : ""}`,
					`Inclui bônus de desempenho pela nota ${result.grade}.`,
				],
				buttons: [
					act(
						`Coletar e planejar o dia ${result.dayNumber + 1}`,
						"claimDayResult",
						[],
						{
							variant: "coin",
							icon: gameIcon("coin"),
							after: "back",
							ok: "Recompensas coletadas!",
						},
					),
				],
			}),
		],
		{ icon: gameIcon("trophy"), subtitle: "Resultado do turno" },
	);
}

export const routes: Routes = {
	day: (state) =>
		state.day.phase === "planning"
			? planning(state)
			: state.day.phase === "results"
				? results(state)
				: openDay(state),
	"day-result": (state) =>
		state.day.phase === "results" ? results(state) : routes.day(state, []),
};
