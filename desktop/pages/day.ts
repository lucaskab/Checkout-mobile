import type { DayContract, SpecialRequest } from "@/@types/market-day";
import { getWaitingInteriorPieces } from "@/data/interior-decor";
import type { GameIconId } from "@/data/game-icon-assets";
import {
	DAY_DURATION_MS,
	FREE_DAY_CONTRACT_ID,
	getContractProgress,
	getPendingRequests,
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

// Desktop pages for the market day, mirroring src/components/market-day.
const clock = (ms: number) => {
	const seconds = Math.max(0, Math.ceil(ms / 1_000));
	return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
};
const difficulty = { 1: "Fácil", 2: "Médio", 3: "Difícil" } as const;
const moods = {
	calmo: "calmo",
	"com-pressa": "com pressa",
	estressado: "estressado",
	feliz: "feliz",
} as const;
const kinds = {
	ajuda: "Precisa de ajuda",
	alternativa: "Quer uma alternativa",
	produto: "Procura um produto",
} as const;
const kindIcons: Record<SpecialRequest["kind"], GameIconId> = {
	ajuda: "customers",
	alternativa: "handshake",
	produto: "basket",
};
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

function contractCard(contract: DayContract) {
	const rewards = [
		`+${fmt(contract.reward.coins)} moedas`,
		`+${contract.reward.experience} XP`,
		...(contract.reward.diamonds
			? [`+${contract.reward.diamonds} diamante`]
			: []),
	];
	return card(contract.title, {
		eyebrow: `CONTRATO · ${difficulty[contract.difficulty]}`,
		subtitle: contract.description,
		icon: iconOf(contract.icon),
		badge: difficulty[contract.difficulty],
		tone: contract.difficulty === 3 ? "warning" : "",
		lines: [`Recompensa: ${rewards.join(" · ")}`],
		buttons: [
			act("Aceitar e abrir", "startDay", [contract.id], {
				variant: "success",
				icon: gameIcon("key"),
				after: "back",
				ok: `Dia aberto: ${contract.title}`,
				fail: "Coloque seus móveis no modo Construir antes de abrir.",
			}),
		],
	});
}

function requestCard(request: SpecialRequest, now: number): Card {
	const remaining = request.expiresAt - now;
	const total = Math.max(1, request.expiresAt - request.createdAt);
	if (request.status !== "pending")
		return card(request.customerName, {
			eyebrow: kinds[request.kind],
			subtitle: request.outcome,
			icon: gameIcon(kindIcons[request.kind]),
			tone:
				request.status === "served"
					? "success"
					: request.status === "partial"
						? "warning"
						: "danger",
			badge: request.tip ? `+${request.tip}` : "",
		});
	return card(request.customerName, {
		eyebrow: `${kinds[request.kind]} · ${moods[request.mood]}`,
		subtitle: `“${request.message}”`,
		icon: gameIcon(kindIcons[request.kind]),
		badge: clock(remaining),
		tone: remaining < 15_000 ? "danger" : "info",
		progress: Math.max(0, remaining / total),
		buttons: request.options.map((option) =>
			act(option.label, "resolveSpecialRequest", [request.id, option.id], {
				variant: "secondary",
				ok: "Cliente atendido",
				fail: "Esse pedido já expirou.",
			}),
		),
	});
}

function dayStatus(state: State, now: number): Card {
	const { day } = state;
	const progress = getContractProgress(day.contract, day.stats);
	return card(day.contract?.title ?? "Dia livre", {
		eyebrow: `DIA ${day.dayNumber} · ${clock((day.endsAt ?? now) - now)} restantes`,
		subtitle:
			day.contract?.description ??
			"Sem contrato: a nota vem da satisfação e dos pedidos.",
		icon: gameIcon("clipboard"),
		badge: day.contract ? progress.label : "",
		tone: progress.completed ? "success" : "",
		progress: day.contract ? progress.ratio : -1,
		lines: [
			`${day.stats.customers} clientes · ${fmt(day.stats.revenue)} moedas · lucro ${fmt(day.stats.profit)}`,
			`Pedidos: ${day.stats.requestsServed + day.stats.requestsPartial} atendidos · ${day.stats.requestsExpired} perdidos · fidelidade ${day.loyalty}`,
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
	const waiting = getWaitingInteriorPieces(state.interior).length;
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
					"Cumpra a meta antes de fechar para ganhar a recompensa. Pedidos especiais bem atendidos melhoram a nota do dia.",
				icon: gameIcon("clipboard"),
				lines: [
					`Fidelidade dos clientes: ${day.loyalty}/100 (mais fidelidade, mais visitas)`,
				],
			}),
			...day.offers.map(contractCard),
			card("Dia livre", {
				subtitle: "Abrir sem contrato. A nota do dia ainda conta.",
				icon: gameIcon("key"),
				buttons: [
					act("Abrir sem contrato", "startDay", [FREE_DAY_CONTRACT_ID], {
						variant: "secondary",
						after: "back",
						ok: "Mercado aberto!",
						fail: "Coloque seus móveis no modo Construir antes de abrir.",
					}),
				],
			}),
		],
		{ icon: gameIcon("clipboard"), subtitle: "Contrato do dia" },
	);
}

function openDay(state: State, focusId?: string) {
	const now = Date.now();
	const pending = getPendingRequests(state.day).sort((a, b) =>
		a.id === focusId ? -1 : b.id === focusId ? 1 : a.expiresAt - b.expiresAt,
	);
	const answered = state.day.requests
		.filter((r) => r.status !== "pending")
		.slice(0, 3);
	return page(
		focusId ? `request:${focusId}` : "requests",
		"Pedidos especiais",
		[
			dayStatus(state, now),
			...(pending.length
				? pending.map((request) => requestCard(request, now))
				: [
						card("Nenhum cliente esperando", {
							subtitle:
								"Os pedidos aparecem aqui e com um balão sobre o cliente.",
							tone: "locked",
						}),
					]),
			...answered.map((request) => requestCard(request, now)),
		],
		{ icon: gameIcon("customers"), subtitle: `${pending.length} esperando` },
	);
}

function results(state: State) {
	const result = state.day.result;
	if (!result) return planning(state);
	const { stats } = result;
	const requests =
		stats.requestsServed +
		stats.requestsPartial +
		stats.requestsFailed +
		stats.requestsExpired;
	return page(
		"day-result",
		`Dia ${result.dayNumber} encerrado`,
		[
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
					`Pedidos atendidos ${stats.requestsServed + stats.requestsPartial}/${requests} · fidelidade ${stats.loyaltyChange >= 0 ? "+" : ""}${stats.loyaltyChange}`,
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
	requests: (state) =>
		state.day.phase === "open" ? openDay(state) : routes.day(state, []),
	request: (state, [id]) =>
		state.day.phase === "open" ? openDay(state, id) : routes.day(state, []),
	"day-result": (state) =>
		state.day.phase === "results" ? results(state) : routes.day(state, []),
};
