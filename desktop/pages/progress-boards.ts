import type { AchievementCategory, AchievementRarity } from "@/@types/achievement";
import type { MissionCategory } from "@/@types/mission";
import { achievements } from "@/data/achievements";
import { getAchievementIcon, getMissionIcon } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import { missions } from "@/data/missions";
import {
	albumCollections,
	getCollectionProgress,
	isProductCollected,
	SALES_TO_COLLECT,
} from "@/data/product-album";
import {
	getAchievementProgress,
	getAchievementStars,
	getAchievementTotals,
} from "@/services/achievements";
import {
	canClaimDailyLogin,
	getLoginReward,
	getNextLoginDay,
	LOGIN_STREAK_DAYS,
} from "@/services/daily-login";
import { getMissionProgress, getMissionStatus } from "@/services/missions";
import { getWeekEnd, getWeeklyProgress, getWeeklyReward } from "@/services/weekly-event";
import type { Routes } from ".";
import {
	act,
	type BoardMark,
	type BoardTile,
	board,
	type Button,
	button,
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

// Missions, gifts, the product album and the trophies as game boards (page.layout = "board"): a quest
// board with rows you can claim right there (and a "claim all"), a 7-day gift streak to tap every day, the
// weekly event, sticker collections and a trophy wall with five stars per trophy. Inspired by the daily
// tasks of Township's Gold Pass, the achievement walls of mobile games (tiers, visible progress, a
// celebration on claim) and Hay Day's sticker-style collections.

const missionCategory: Record<MissionCategory, string> = {
	customers: "CLIENTES",
	inventory: "ESTOQUE",
	management: "GESTÃO",
	production: "PRODUÇÃO",
	progression: "PROGRESSÃO",
	sales: "VENDAS",
};
/** Where a mission is played: the button next to it takes the player there. */
const missionRoute: Partial<Record<MissionCategory, [string, string, string]>> = {
	inventory: ["Ir ao estoque", "!products", "basket"],
	production: ["Ir à produção", "!sectors", "conveyor"],
	management: ["Ir à loja", "!loja", "market"],
};

const productName = (id: number) => itemCatalog.find((item) => item.id === id)?.name ?? `#${id}`;

/** Decorative milestones along a progress bar (every `step`), done once reached. */
function milestones(value: number, max: number, count: number, icon: string, label: (at: number) => string): BoardMark[] {
	return Array.from({ length: count }, (_, index) => {
		const at = Math.round((max * (index + 1)) / count);
		return { at, icon, label: label(at), state: value >= at ? "done" : "locked", action: noButton() };
	});
}

// ---------------------------------------------------------------- Missões
type MissionTab = "missoes" | "presentes" | "concluidas" | "proximas";

function missionTile(state: State, mission: (typeof missions)[number]): BoardTile {
	const progress = getMissionProgress(mission, state);
	const status = getMissionStatus(mission, state);
	const shown = Math.min(progress, mission.goal);
	const rewards = [
		`${fmt(mission.reward.coins)} moedas`,
		...(mission.reward.items ?? []).map((item) => `${item.quantity}× ${productName(item.productId)}`),
	];
	const claim = act("Resgatar", "claimMission", [mission.id], {
		variant: "success",
		icon: gameIcon("coin"),
		ok: "Recompensa resgatada!",
		fail: "Não deu para resgatar: veja se há espaço no depósito para os itens do prêmio.",
	});
	const where = missionRoute[mission.category];
	const goThere = where ? go(where[0], where[1], { icon: gameIcon(where[2] as Parameters<typeof gameIcon>[0]) }) : null;
	const action: Button =
		status === "claimable"
			? claim
			: status === "claimed"
				? button("Resgatada", { variant: "secondary", enabled: false, icon: gameIcon("success") })
				: status === "locked"
					? button(`Nível ${mission.requiredLevel}`, { variant: "secondary", enabled: false, icon: gameIcon("lock") })
					: (goThere ?? button("Em andamento", { variant: "secondary", enabled: false }));
	return tile(mission.id, mission.title, {
		group:
			status === "claimable"
				? "PRONTAS PARA RESGATAR"
				: status === "claimed"
					? "CONCLUÍDAS"
					: status === "locked"
						? "PRÓXIMAS"
						: missionCategory[mission.category],
		icon: gameIcon(getMissionIcon(mission.id)),
		subtitle: mission.description,
		sticker: status === "claimable" ? "PRONTA!" : status === "locked" ? `NV ${mission.requiredLevel}` : "",
		tone: status === "claimable" ? "success" : status === "locked" ? "locked" : status === "claimed" ? "info" : "",
		badge: `+${fmt(mission.reward.coins)}`,
		fill: ratio(shown, mission.goal),
		fillText: `${fmt(shown)} / ${fmt(mission.goal)}`,
		state: status === "claimable" ? "ready" : status === "locked" ? "locked" : status === "claimed" ? "done" : "",
		action,
		// The side panel already shows the subtitle (the description): no second copy; the reward is the badge.
		detail: "",
		facts: [
			stat(gameIcon("target"), `${fmt(shown)}/${fmt(mission.goal)}`, "Progresso", status === "claimable" ? "success" : ""),
			stat(gameIcon("coin"), fmt(mission.reward.coins), "Moedas de prêmio", "gold"),
			stat(gameIcon("clipboard"), missionCategory[mission.category], "Categoria"),
			stat(gameIcon("crown"), `Nv ${mission.requiredLevel}`, "Nível mínimo"),
		],
		lines: [`Prêmio: ${rewards.join(", ")}`],
		actions: [status === "claimable" ? claim : null, goThere].filter((item): item is Button => item !== null),
	});
}

function giftTiles(state: State): BoardTile[] {
	const now = Date.now();
	const ready = canClaimDailyLogin(state.dailyLogin, now);
	const next = getNextLoginDay(state.dailyLogin, now);
	const today = ready ? next : (state.dailyLogin?.streak ?? 0);
	const days = Array.from({ length: LOGIN_STREAK_DAYS }, (_, index) => {
		const day = index + 1;
		const gift = getLoginReward(day, state.era.id);
		const done = day < today || (!ready && day === today);
		const isToday = ready && day === today;
		const prize = `${fmt(gift.coins)} moedas${gift.diamonds ? ` + ${gift.diamonds} diamantes` : ""}`;
		const claim = act(`Resgatar ${prize}`, "claimDailyLogin", [], {
			variant: "success",
			icon: gameIcon("gift"),
			ok: "Presente do dia resgatado!",
			fail: "Já resgatado hoje.",
		});
		return tile(`day${day}`, `Dia ${day}`, {
			group: "PRESENTE DO DIA · VOLTE TODO DIA",
			icon: gameIcon(gift.diamonds ? "diamond" : "gift"),
			subtitle: prize,
			sticker: isToday ? "HOJE!" : day === LOGIN_STREAK_DAYS ? "BÔNUS" : "",
			tone: isToday ? "success" : done ? "info" : day === LOGIN_STREAK_DAYS ? "gold" : "",
			badge: gift.diamonds ? `+${gift.diamonds}` : "",
			state: isToday ? "ready" : done ? "done" : "",
			action: isToday ? claim : noButton(),
			detail: "Volte todo dia: o presente cresce a cada dia seguido e o 7º dia dá diamantes. Perder um dia recomeça a sequência.",
			facts: [
				stat(gameIcon("coin"), fmt(gift.coins), "Moedas"),
				stat(gameIcon("diamond"), String(gift.diamonds ?? 0), "Diamantes"),
				stat(gameIcon("flame"), `${Math.min(today, LOGIN_STREAK_DAYS)}/${LOGIN_STREAK_DAYS}`, "Sequência"),
			],
			actions: isToday ? [claim] : [],
		});
	});
	const weekly = getWeeklyProgress(state.weeklyEvent, state.market.soldByProduct, now);
	const reward = getWeeklyReward(state.era.id);
	const prize = `${fmt(reward.coins)} moedas + ${reward.diamonds} diamantes`;
	const claimWeek = act(`Resgatar ${prize}`, "claimWeeklyEvent", [], {
		variant: "success",
		icon: gameIcon("festival"),
		ok: "Prêmio da semana resgatado!",
	});
	const sold = Math.min(weekly.sold, weekly.theme.goal);
	const albumProgress = albumCollections.map((collection) => getCollectionProgress(collection, state.market.soldByProduct));
	const stickers = albumProgress.reduce((total, item) => total + item.collected, 0);
	const stickerTotal = albumProgress.reduce((total, item) => total + item.total, 0);
	const prizes = albumCollections.filter(
		(collection, index) => albumProgress[index].complete && !(state.albumClaimedIds ?? []).includes(collection.id),
	).length;
	return [
		...days,
		tile("weekly", weekly.theme.name, {
			group: "EVENTO DA SEMANA E ÁLBUM",
			icon: gameIcon("festival"),
			subtitle: weekly.theme.description,
			sticker: weekly.claimed ? "RESGATADO" : weekly.done ? "PRONTO!" : "SEMANA",
			tone: weekly.done && !weekly.claimed ? "success" : "gold",
			badge: `${sold}/${weekly.theme.goal}`,
			fill: ratio(sold, weekly.theme.goal),
			fillText: `${sold}/${weekly.theme.goal} vendidos`,
			timerEnd: getWeekEnd(now),
			timerTotal: 7 * 24 * 60 * 60_000,
			state: weekly.done && !weekly.claimed ? "ready" : weekly.claimed ? "done" : "",
			action: weekly.done && !weekly.claimed ? claimWeek : noButton(),
			detail: `${weekly.theme.description} Esses produtos vendem mais a semana toda. Venda ${weekly.theme.goal} unidades deles para ganhar ${prize}.`,
			facts: [
				stat(gameIcon("target"), `${sold}/${weekly.theme.goal}`, "Vendidos"),
				stat(gameIcon("coin"), fmt(reward.coins), "Moedas"),
				stat(gameIcon("diamond"), String(reward.diamonds), "Diamantes"),
			],
			actions: weekly.done && !weekly.claimed ? [claimWeek] : [],
		}),
		tile("album", "Álbum de produtos", {
			group: "EVENTO DA SEMANA E ÁLBUM",
			icon: gameIcon("medal"),
			subtitle: `Venda ${SALES_TO_COLLECT} de um produto para ganhar a figurinha`,
			sticker: prizes > 0 ? `${prizes} PRÊMIO${prizes === 1 ? "" : "S"}!` : "",
			tone: prizes > 0 ? "success" : "info",
			badge: `${stickers}/${stickerTotal}`,
			fill: ratio(stickers, stickerTotal),
			fillText: `${stickers}/${stickerTotal} figurinhas`,
			state: prizes > 0 ? "ready" : "",
			action: go("Abrir álbum", "album", { icon: gameIcon("medal"), variant: prizes > 0 ? "success" : "primary" }),
			detail: "Cada produto vira figurinha quando você vende 10 unidades dele. Complete uma coleção para ganhar moedas e diamantes.",
			actions: [go("Abrir álbum", "album", { icon: gameIcon("medal"), variant: "primary" })],
		}),
	];
}

function missionsBoard(state: State, args: string[]) {
	const entries = missions.map((mission) => ({ mission, status: getMissionStatus(mission, state) }));
	const claimable = entries.filter((entry) => entry.status === "claimable");
	const claimed = entries.filter((entry) => entry.status === "claimed").length;
	const giftReady = canClaimDailyLogin(state.dailyLogin, Date.now());
	const tabs: { id: MissionTab; label: string; icon: string; count: number }[] = [
		{ id: "missoes", label: "Missões", icon: gameIcon("target"), count: claimable.length },
		{ id: "presentes", label: "Presentes", icon: gameIcon("gift"), count: giftReady ? 1 : 0 },
		{ id: "concluidas", label: "Concluídas", icon: gameIcon("success"), count: 0 },
		{ id: "proximas", label: "Próximas", icon: gameIcon("lock"), count: 0 },
	];
	const legacy: Record<string, MissionTab> = { active: "missoes", claimed: "concluidas", locked: "proximas" };
	const active = (tabs.find((tab) => tab.id === args[0])?.id ?? legacy[args[0] ?? ""] ?? "missoes") as MissionTab;
	const order = (status: string) => (status === "claimable" ? 0 : status === "active" ? 1 : 2);
	const tiles =
		active === "presentes"
			? giftTiles(state)
			: entries
					.filter(({ status }) =>
						active === "missoes"
							? status === "active" || status === "claimable"
							: active === "concluidas"
								? status === "claimed"
								: status === "locked",
					)
					.sort(
						(a, b) =>
							order(a.status) - order(b.status) ||
							a.mission.requiredLevel - b.mission.requiredLevel ||
							a.mission.goal - b.mission.goal,
					)
					.map(({ mission }) => missionTile(state, mission));
	const prize = claimable.reduce((total, entry) => total + entry.mission.reward.coins, 0);
	return page(`missions:${active}`, "Missões", [], {
		layout: "board",
		icon: gameIcon("trophy"),
		subtitle: "Complete objetivos, resgate prêmios e volte todo dia",
		tabs: tabs.map((tab) => ({
			...swap(tab.label, `missions:${tab.id}`, tab.id === active, tab.icon),
			badge: tab.count > 0 ? String(tab.count) : "",
		})),
		board: board(tiles, {
			tint: "8B5C9E",
			backdrop: "Game/panel_board",
			style: active === "presentes" ? "card" : "row",
			columns: active === "presentes" ? 4 : 1,
			stats: [
				// Completed count is the meter below; the level is on the HUD's level card.
				stat(gameIcon("target"), String(claimable.length), "Prontas", claimable.length ? "success" : ""),
			],
			meter: meter("Jornada do mercado", claimed, missions.length, {
				icon: gameIcon("trophy"),
				text: `${claimed} de ${missions.length} missões concluídas`,
				tone: "gold",
				marks: milestones(claimed, missions.length, 4, gameIcon("trophy"), (at) => `${at} missões concluídas`),
			}),
			footer: [
				act(claimable.length ? `Resgatar todas (${claimable.length}) · +${fmt(prize)}` : "Nada para resgatar", "claimAllMissions", [], {
					variant: "success",
					icon: gameIcon("coin"),
					enabled: claimable.length > 0,
					ok: "Tudo resgatado!",
					fail: "Algumas não couberam no depósito.",
				}),
				...(giftReady && active !== "presentes"
					? [go("Presente do dia!", "~missions:presentes", { icon: gameIcon("gift"), variant: "coin" })]
					: [go("Ver conquistas", "!achievements", { icon: gameIcon("crown") })]),
			],
			tip: claimable.length
				? `${claimable.length} ${claimable.length === 1 ? "missão pronta" : "missões prontas"}! Resgate para ganhar ${fmt(prize)} moedas.`
				: giftReady
					? "Seu presente do dia está esperando na aba Presentes!"
					: "Cada missão concluída aproxima você do próximo troféu da jornada.",
			empty:
				active === "concluidas"
					? "Nenhuma missão concluída ainda."
					: active === "proximas"
						? "Todas as missões já estão liberadas."
						: "Tudo limpo por aqui! Continue evoluindo para liberar novos objetivos.",
		}),
	});
}

// ---------------------------------------------------------------- Álbum
function albumBoard(state: State) {
	const claimedIds = state.albumClaimedIds ?? [];
	const tiles = albumCollections.map((collection) => {
		const progress = getCollectionProgress(collection, state.market.soldByProduct);
		const claimed = claimedIds.includes(collection.id);
		const ready = progress.complete && !claimed;
		const prize = `${fmt(collection.reward.coins)} moedas + ${collection.reward.diamonds} diamantes`;
		const claim = act(`Resgatar ${prize}`, "claimAlbumCollection", [collection.id], {
			variant: "success",
			icon: gameIcon("gift"),
			ok: "Coleção completa! Prêmio resgatado.",
		});
		return tile(collection.id, collection.name, {
			group: ready ? "COMPLETAS · RESGATE O PRÊMIO" : claimed ? "RESGATADAS" : "COLEÇÕES",
			icon: productIcon(collection.productIds[0]),
			subtitle: prize,
			// Progress shows once, in the bar ("3/10 figurinhas"): no ribbon and badge with the same count.
			sticker: ready ? "COMPLETA!" : "",
			tone: ready ? "success" : claimed ? "info" : "gold",
			badge: "",
			fill: ratio(progress.collected, progress.total),
			fillText: `${progress.collected}/${progress.total} figurinhas`,
			state: ready ? "ready" : claimed ? "done" : "",
			action: ready ? claim : noButton(),
			detail: `Venda ${SALES_TO_COLLECT} unidades de cada produto desta coleção para completá-la.`,
			facts: collection.productIds.slice(0, 12).map((id) => {
				const sold = state.market.soldByProduct[id] ?? 0;
				const done = isProductCollected(state.market.soldByProduct, id);
				return stat(productIcon(id), done ? "OK" : `${Math.min(sold, SALES_TO_COLLECT)}/${SALES_TO_COLLECT}`, productName(id), done ? "success" : "");
			}),
			actions: ready ? [claim] : [],
		});
	});
	const total = albumCollections.length;
	const done = albumCollections.filter((collection) => claimedIds.includes(collection.id)).length;
	return page("album", "Álbum de produtos", [], {
		layout: "board",
		icon: gameIcon("medal"),
		subtitle: `Venda ${SALES_TO_COLLECT} de um produto para ganhar a figurinha`,
		board: board(tiles, {
			tint: "B26A2E",
			backdrop: "Game/panel_board",
			columns: 4,
			stats: [stat(gameIcon("medal"), `${done}/${total}`, "Coleções")],
			meter: meter("Coleções completas", done, total, { icon: gameIcon("medal"), text: `${done} de ${total} coleções resgatadas`, tone: "gold" }),
			footer: [go("Voltar às missões", "!missions:presentes", { icon: gameIcon("trophy") })],
			tip: "Produtos novos dão figurinhas novas: varie o que você vende!",
		}),
	});
}

// ---------------------------------------------------------------- Conquistas
const rarity: Record<AchievementRarity, [string, string]> = {
	common: ["COMUM", ""],
	uncommon: ["INCOMUM", "success"],
	rare: ["RARA", "info"],
	epic: ["ÉPICA", "info"],
	legendary: ["LENDÁRIA", "gold"],
};
const achievementTabs: { id: "all" | AchievementCategory; label: string; icon: string }[] = [
	{ id: "all", label: "Todas", icon: "crown" },
	{ id: "progression", label: "Evolução", icon: "market" },
	{ id: "sales", label: "Vendas", icon: "coin" },
	{ id: "customers", label: "Clientes", icon: "customers" },
	{ id: "production", label: "Produção", icon: "conveyor" },
	{ id: "management", label: "Gestão", icon: "clipboard" },
	{ id: "logistics", label: "Logística", icon: "deliveryTruck" },
	{ id: "collection", label: "Coleção", icon: "medal" },
	{ id: "specialist", label: "Especialistas", icon: "graduation" },
];
const compact = (value: number) =>
	value >= 1_000_000 ? `${value / 1_000_000}M` : value >= 1_000 ? `${value / 1_000}k` : String(value);

function achievementsBoard(state: State, args: string[]) {
	const level = state.market.level;
	const active = achievementTabs.find((tab) => tab.id === args[0])?.id ?? "all";
	const totals = getAchievementTotals(state);
	const entries = achievements
		.filter((achievement) => active === "all" || achievement.category === active)
		.map((achievement) => ({
			achievement,
			progress: getAchievementProgress(achievement, state),
			stars: getAchievementStars(achievement, state),
		}))
		.sort((a, b) => {
			const lockedA = level < a.achievement.requiredLevel ? 1 : 0;
			const lockedB = level < b.achievement.requiredLevel ? 1 : 0;
			const doneA = a.stars === a.achievement.thresholds.length ? 1 : 0;
			const doneB = b.stars === b.achievement.thresholds.length ? 1 : 0;
			return lockedA - lockedB || doneA - doneB || b.stars - a.stars;
		});
	const tiles = entries.map(({ achievement, progress, stars }) => {
		const { thresholds } = achievement;
		const locked = level < achievement.requiredLevel;
		const complete = stars === thresholds.length;
		const previous = stars === 0 ? 0 : thresholds[stars - 1];
		const next = thresholds[stars] ?? thresholds[thresholds.length - 1];
		const [label, tone] = rarity[achievement.rarity];
		return tile(achievement.id, achievement.title, {
			group: locked ? "BLOQUEADAS" : complete ? "NO MÁXIMO" : "EM ANDAMENTO",
			icon: achievement.targetProductId ? productIcon(achievement.targetProductId) : gameIcon(getAchievementIcon(achievement.id)),
			subtitle: achievement.description,
			sticker: locked ? `NV ${achievement.requiredLevel}` : label,
			tone: locked ? "locked" : complete ? "success" : tone,
			badge: `${stars}/${thresholds.length}`,
			stars,
			maxStars: thresholds.length,
			fill: locked ? 0 : complete ? 1 : ratio(progress - previous, Math.max(1, next - previous)),
			fillText: complete ? "Máximo!" : `${compact(Math.min(progress, next))} / ${compact(next)}`,
			state: locked ? "locked" : complete ? "done" : "",
			detail: achievement.rarity === "legendary" ? "O quinto nível pertence aos gerentes mais dedicados." : "", // the description is the subtitle
			facts: thresholds.map((goal, index) =>
				stat(gameIcon(index < stars ? "success" : "medal"), compact(goal), `Estrela ${index + 1}`, index < stars ? "success" : index === stars ? "gold" : ""),
			),
			lines: [complete ? "Todas as estrelas conquistadas!" : `Próxima estrela: ${fmt(Math.min(progress, next))} de ${fmt(next)}`],
		});
	});
	return page(`achievements:${active}`, "Conquistas", [], {
		layout: "board",
		icon: gameIcon("crown"),
		subtitle: "Salão da fama: cada nível vale uma estrela",
		tabs: achievementTabs.map((tab) => swap(tab.label, `achievements:${tab.id}`, tab.id === active, gameIcon(tab.icon as Parameters<typeof gameIcon>[0]))),
		board: board(tiles, {
			tint: "C58A1E",
			backdrop: "Game/panel_board",
			columns: 5,
			stats: [
				stat(gameIcon("medal"), `${totals.stars}/${totals.totalStars}`, "Estrelas"),
				stat(gameIcon("crown"), String(totals.achievementsCompleted), "No máximo"),
			],
			meter: meter("Salão da fama", totals.stars, totals.totalStars, {
				icon: gameIcon("crown"),
				text: `${totals.stars} de ${totals.totalStars} estrelas`,
				tone: "gold",
				marks: milestones(totals.stars, totals.totalStars, 4, gameIcon("crown"), (at) => `${at} estrelas`),
			}),
			footer: [go("Ver missões", "!missions", { icon: gameIcon("trophy") })],
			tip: "As estrelas chegam sozinhas: venda, atenda e evolua o mercado. Toque numa conquista para ver as metas de cada estrela.",
			empty: "Nenhuma conquista nesta categoria.",
		}),
	});
}

export const routes: Routes = {
	missions: missionsBoard,
	album: albumBoard,
	achievements: achievementsBoard,
};
