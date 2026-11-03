import type { Routes } from ".";
import type { LeagueDivision } from "@/@types/rankings";
import { COUNTRY_NAMES } from "@/data/countries";
import {
	LEAGUE_DIVISION_NAMES,
	LEAGUE_DIVISION_TINTS,
	LEAGUE_POINTS,
	leagueBadgeFile,
	leagueRewardDiamonds,
	LEAGUE_PLACE_DIAMONDS,
	RANKING_TOP,
} from "@/data/rankings";
import { getLanguage } from "@/i18n";
import { type FriendsColumn, rankTrend, sortFriendsBoard, timeLeftText, weekEndsAt } from "@/services/rankings";
import { cloudStore } from "../cloud";
import {
	type FriendRank,
	type LeagueBoard,
	type LeagueRow,
	type LevelBoard,
	type RankingTab,
	type RankRow,
	friendsRows,
	rankingsOnline,
	rankingsStore,
	viewRankings,
} from "../rankings";
import { avatarIcon, formatCode, socialIcon, socialStore, stageIcon, stageName } from "../social";
import { act, board, type BoardStat, type BoardTile, button, type Button, type Card, card, fmt, meter, page, type Page, stat, type State, tile } from "../view-kit";

// The "Ranking" window (rankings v1, docs/rankings-api.md): full-screen like the Loja and the Amigos windows (Lucas
// 02/11: "tela inteira e bem gamificado"), with the four boards as big header tabs. Mundo / País: the top three on a
// podium (big round framed faces, gold/silver/bronze plinths, a crown on #1), then ranked rows (round face, name, level
// ribbon, stage badge, flag) and my own row pinned under them. Liga: the division badge big in the bar with the time
// left, the prizes strip, the promotion zone in green and the demotion zone in red. Amigos: a column switch and an
// invite row at the end. Signed out: Mundo and País read-only with a card to sign in.

const NAVY = "1D2B4F";
const langIndex = () => ({ pt: 0, en: 1, es: 2, fr: 3, de: 4 })[getLanguage()] ?? 0;
/** The country's name in the player's language (from its ISO code; the code itself when unknown). */
export const countryName = (code: string | null | undefined) => (code ? (COUNTRY_NAMES[code.toUpperCase()]?.[langIndex()] ?? code.toUpperCase()) : "");
export const flagIcon = (code: string | null | undefined) => (code && COUNTRY_NAMES[code.toUpperCase()] ? `Flags/${code.toLowerCase()}` : "Flags/xx");
export const divisionIcon = (division: LeagueDivision) => `Icons/${leagueBadgeFile(division)}`;
export const divisionName = (division: LeagueDivision) => `Liga ${LEAGUE_DIVISION_NAMES[division]}`;
const nameOf = (row: { marketName: string | null; code: string }) => row.marketName?.trim() || `Mercado #${formatCode(row.code)}`;
const myId = () => socialStore.me?.id ?? "";
/** A face id this phone can draw: "shopper-N" past the shoppers Unity has (fewer looks on some builds) wraps around. */
export function faceOf(avatar: string | null | undefined) {
	const match = /^shopper-(\d+)$/.exec(avatar ?? "");
	const count = Math.max(1, socialStore.avatars || 12);
	return avatarIcon(match ? `shopper-${((Number(match[1]) - 1) % count) + 1}` : avatar);
}
const busy = (key: string) => rankingsStore.busy.has(key);

// ------------------------------------------------------------------------------------------------------------ frame

function tabs(state: State, active: RankingTab): Button[] {
	const week = viewRankings();
	const me = rankingsStore.world.data?.me ?? rankingsStore.country.data?.me;
	const country = rankingsStore.country.data?.country ?? me?.country ?? null;
	const league = rankingsStore.league.data;
	const list: { id: RankingTab; label: string; icon: string; badge: string }[] = [
		{ id: "amigos", label: "Amigos", icon: socialIcon("friends"), badge: "" },
		{ id: "liga", label: "Liga", icon: divisionIcon(league?.division ?? "bronze"), badge: week.cards.length ? String(week.cards.length) : "" },
		{ id: "mundo", label: "Mundo", icon: "Icons/globe", badge: "" },
		{ id: "pais", label: "País", icon: flagIcon(country), badge: "" },
	];
	void state;
	return list.map((tab) =>
		button(tab.label, { icon: tab.icon, route: `~ranking:${tab.id}`, variant: tab.id === active ? "coin" : "secondary", active: tab.id === active, badge: tab.badge }),
	);
}

function rankPage(state: State, tab: RankingTab, cards: Card[], tiles: BoardTile[], options: Parameters<typeof board>[1] = {}, extra: Partial<Page> = {}) {
	const scroll = rankingsStore.scroll ? `${rankingsStore.scroll}#${rankingsStore.scrollCount}` : "";
	return page(`ranking:${tab}`, "Ranking", cards, {
		icon: "Icons/trophy",
		layout: "board",
		sections: tabs(state, tab),
		board: board(tiles, { tint: NAVY, columns: 1, style: "rank", scroll, ...options }),
		...extra,
	});
}

/** Signed out: the boards stay visible (Mundo, País) and this card asks to sign in. */
function signInCard(): Card {
	const providers = cloudStore.providers.length ? cloudStore.providers : ["google" as const];
	const canSignIn = cloudStore.status === "signed-out";
	return card("Entre para aparecer no ranking", {
		icon: "Icons/trophy",
		eyebrow: "RANKING",
		tone: "gold",
		lines: ["Dispute a liga da semana, compare com os amigos e mostre o seu mercado para o mundo."],
		buttons:
			cloudStore.status === "unavailable" && !socialStore.mock
				? []
				: providers.map((provider) =>
						act(cloudStore.status === "signing-in" ? "Entrando…" : provider === "apple" ? "Iniciar sessão com a Apple" : "Entrar com Google", "cloudSignIn", [provider], {
							variant: provider === "apple" ? "secondary" : "success",
							enabled: canSignIn,
							ok: provider === "apple" ? "Abrindo o login da Apple…" : "Abrindo o login do Google…",
						}),
					),
	});
}

function troubleCard(text: string): Card {
	return card("Não deu para carregar o ranking", {
		icon: socialIcon("warning"),
		tone: "warning",
		lines: [text],
		buttons: [act("Tentar de novo", "rankingRefresh", [], { ok: "" })],
	});
}

/** "Aparecer no ranking" (the switch of the opt-out, PUT /v1/rankings/settings). */
function optOutButton(): Button {
	const optOut = viewRankings().optOut;
	return act(optOut ? "No ranking: não" : "No ranking: sim", "rankingOptOut", [!optOut], {
		icon: optOut ? socialIcon("lock") : socialIcon("success"),
		variant: optOut ? "secondary" : "success",
		enabled: rankingsOnline() && !busy("optout"),
		ok: "",
		fail: "Entre na sua conta para aparecer no ranking.",
	});
}

// ------------------------------------------------------------------------------------------------------------ rows

type RowLook = { value: string; valueLabel: string; tone?: string; group?: string; you?: boolean; sticker?: string; actions?: Button[] };

function playerTile(id: string, row: { marketName: string | null; code: string; avatar: string | null; level: number; era?: string; country?: string | null }, rank: number | null, look: RowLook): BoardTile {
	const name = nameOf(row);
	const facts: BoardStat[] = [
		stat(stageIcon(row.era ?? "mesinha"), String(row.level), "nível"),
		...(look.value ? [stat("Icons/trophy", look.value, look.valueLabel === "XP" ? "experiência" : look.valueLabel)] : []),
	];
	return tile(id, look.you ? `${name} (você)` : name, {
		group: look.group ?? "",
		icon: faceOf(row.avatar),
		frame: "rank",
		corner: row.era ? stageIcon(row.era) : "",
		subtitle: row.era ? stageName(row.era) : "",
		sticker: look.sticker ?? `NV ${row.level}`,
		tone: look.tone ?? (look.you ? "gold" : ""),
		rank: rank && rank > 0 ? String(rank) : "-",
		flag: row.country ? flagIcon(row.country) : "",
		value: look.value,
		valueLabel: look.valueLabel,
		// (the side panel fits without a scroll, even under Amigos' column tabs: the country is a line under the
		// stage, two facts, the place is the row's disc)
		detail: row.country ? countryName(row.country) : "",
		facts,
		actions: look.actions ?? [],
	});
}

/** "Você · #48.213" pinned under the rows: where I am even far from the top 100. */
function pinnedTile(row: RankRow | null, look: RowLook & { inTop: boolean }): BoardTile {
	if (!row) return tile("", "");
	const optOut = viewRankings().optOut;
	const ranked = row.rank !== null && !optOut;
	const pinned = playerTile("pinned-me", row, row.rank, { ...look, you: true, tone: "gold" });
	return {
		...pinned,
		title: ranked ? `Você · #${fmt(row.rank!)}` : "Você",
		subtitle: ranked ? nameOf(row) : optOut ? "Você não aparece no ranking" : "Salve na nuvem para entrar no ranking",
		action: ranked && look.inTop ? act("Ver minha posição", "rankingMyPosition", [row.id], { variant: "primary", ok: "" }) : button("", { enabled: false }),
	};
}

/** Mundo / País rows: the top three on the podium, the rest as rows, me pinned. */
function levelBoardView(board0: LevelBoard, me: RankRow | null) {
	const id = me?.id ?? myId();
	const tiles = board0.top.map((row) =>
		playerTile(row.id, row, row.rank, { value: fmt(row.xp), valueLabel: "XP", you: row.id === id }),
	);
	const inTop = !!me && board0.top.some((row) => row.id === me.id);
	return {
		podium: tiles.slice(0, 3),
		tiles: tiles.slice(3),
		pinned: pinnedTile(me, { value: me ? fmt(me.xp) : "", valueLabel: "XP", inTop }),
	};
}

// ------------------------------------------------------------------------------------------------------------ mundo / país

function levelPage(state: State, tab: "mundo" | "pais"): Page {
	const loaded = tab === "mundo" ? rankingsStore.world : rankingsStore.country;
	const online = rankingsOnline();
	const data = loaded.data;
	const cards: Card[] = [];
	if (!online) cards.push(signInCard());
	if (!data) {
		cards.push(loaded.error ? troubleCard(loaded.error) : card("Carregando o ranking…", { icon: "Icons/trophy" }));
		return rankPage(state, tab, cards, [], { empty: "" });
	}
	const me = online ? data.me : null;
	const view = levelBoardView(data, me);
	const country = data.country ?? me?.country ?? null;
	const ranked = me && me.rank !== null && !viewRankings().optOut;
	const strip = tab === "mundo"
		? meter("Mundo", ranked ? Math.max(1, data.total - me!.rank! + 1) : 0, Math.max(1, data.total), {
				icon: "Icons/globe",
				tone: "gold",
				buttons: online ? [optOutButton()] : [],
				text: ranked ? `Você é #${fmt(me!.rank!)} de ${fmt(data.total)} jogadores` : `Top ${RANKING_TOP} de ${fmt(data.total)} jogadores`,
			})
		: meter(country ? countryName(country) : "País", ranked ? Math.max(1, data.total - me!.rank! + 1) : 0, Math.max(1, data.total), {
				icon: flagIcon(country),
				tone: "gold",
				buttons: online ? [optOutButton()] : [],
				text: ranked ? `Você é #${fmt(me!.rank!)} de ${fmt(data.total)} no seu país` : `Top ${RANKING_TOP} de ${fmt(data.total)} jogadores do país`,
			});
	return rankPage(state, tab, cards, view.tiles, {
		podium: view.podium,
		pinned: view.pinned,
		meter: strip,
		focus: ranked && view.pinned.action.action ? me!.id : "",
		stats: [stat(socialIcon("friends"), fmt(data.total), "jogadores"), ...(ranked ? [stat("Icons/trophy", `#${fmt(me!.rank!)}`, "sua posição")] : [])],
		empty: data.top.length ? "" : "Ninguém no ranking ainda.",
	});
}

// ------------------------------------------------------------------------------------------------------------ liga

/** How league points are earned (before joining this week, and in the side panel). */
function earnTiles(): BoardTile[] {
	const rows: { id: string; icon: string; title: string; value: string }[] = [
		{ id: "earn-customer", icon: socialIcon("customers"), title: "Cada cliente que comprou", value: `+${LEAGUE_POINTS.customer}` },
		{ id: "earn-contract", icon: "Icons/clipboard", title: "Contrato do dia entregue", value: `+${LEAGUE_POINTS.contract}` },
		{ id: "earn-stars", icon: "Icons/success", title: "Fim do dia: cada estrela da nota", value: `+${LEAGUE_POINTS.dayStar}` },
		{ id: "earn-build", icon: "Icons/construction", title: "Evolução, obra, expansão ou terreno pronto", value: `+${LEAGUE_POINTS.build}` },
		{ id: "earn-help", icon: socialIcon("handshake"), title: "Ajudar na obra de um amigo", value: `+${LEAGUE_POINTS.help}` },
	];
	return rows.map((row) =>
		tile(row.id, row.title, { group: "Como ganhar pontos", icon: row.icon, frame: "rank", value: row.value, valueLabel: "pontos", rank: "", detail: "Os pontos contam na liga desta semana (segunda a domingo)." }),
	);
}

function rewardsStrip(league: LeagueBoard | null, division: LeagueDivision): BoardStat[] {
	const rewards = league?.rewards.length ? league.rewards : LEAGUE_PLACE_DIAMONDS.map((row) => ({ place: row.place, diamonds: leagueRewardDiamonds(row.place, division) }));
	const at = (place: number) => rewards.find((row) => row.place === place)?.diamonds ?? 0;
	return [
		stat("Icons/crown", `+${at(1)}`, "#1", "gold"),
		stat("Icons/medal", `+${at(2)}`, "#2", "info"),
		stat("Icons/medal", `+${at(3)}`, "#3", "warning"),
		stat("Icons/diamond", `+${at(4)}`, "#4 – #10", ""),
		stat("Icons/gift", `Top ${league?.promote ?? 5}`, "Baú de moedas", "success"),
	];
}

// Last week on a chip: a short value ("#2 · subiu!") over its label, like the prizes beside it.
function lastChip(last: { place: number; division: LeagueDivision; movedTo: LeagueDivision }): string {
	const moved = rankOf(last.movedTo) - rankOf(last.division);
	if (last.place > 0) return moved > 0 ? `#${last.place} · subiu!` : moved < 0 ? `#${last.place} · desceu` : `#${last.place}`;
	return moved > 0 ? "Subiu!" : moved < 0 ? "Desceu" : "Ficou";
}

function leaguePage(state: State): Page {
	if (!rankingsOnline()) return rankPage(state, "liga", [signInCard()], earnTiles(), { empty: "", strip: rewardsStrip(null, "bronze") });
	const loaded = rankingsStore.league;
	const league = loaded.data;
	if (!league) return rankPage(state, "liga", [loaded.error ? troubleCard(loaded.error) : card("Carregando a liga…", { icon: divisionIcon("bronze") })], [], { empty: "" });
	const now = Date.now();
	const week = viewRankings(now);
	const division = league.division;
	const ends = league.endsAt || weekEndsAt(league.week);
	const last = league.lastWeek;
	const lastPlace = last && last.place > 0 ? ` #${last.place}` : "";
	const lastText = last ? (last.movedTo !== last.division ? (rankOf(last.movedTo) > rankOf(last.division) ? `Semana passada:${lastPlace} · subiu!` : `Semana passada:${lastPlace} · desceu`) : `Semana passada:${lastPlace}`) : "";
	const strip = rewardsStrip(league, division);
	const bar = (points: number, goal: number, words: string) =>
		meter(divisionName(division), points, Math.max(1, goal), { icon: divisionIcon(division), tone: "gold", text: words, buttons: [optOutButton()] });
	if (!league.me || !league.group.length) {
		// Not in this week's league yet: it opens with the first points that reach the server.
		const hero = card("Faça pontos para entrar na liga desta semana", {
			icon: divisionIcon(division),
			eyebrow: divisionName(division).toUpperCase(),
			tone: "gold",
			lines: [
				week.points > 0 ? `Você já tem ${fmt(week.points)} pontos: a liga abre quando eles chegarem ao servidor.` : "Venda, entregue contratos e termine obras: cada ponto conta.",
				`Termina em ${timeLeftText(ends, now)}`,
				...(lastText ? [lastText] : []),
			],
		});
		return rankPage(state, "liga", [hero], earnTiles(), {
			tint: LEAGUE_DIVISION_TINTS[division],
			meter: bar(week.points, Math.max(week.points, 100), `Termina em ${timeLeftText(ends, now)} · ${fmt(week.points)} pontos esta semana`),
			strip,
			stats: [stat(divisionIcon(division), LEAGUE_DIVISION_NAMES[division], "divisão")],
			empty: "",
		});
	}
	const size = league.group.length;
	// The server's zones (min(5, ⌊n/2⌋) each: never both for one player); clamped for safety.
	const promote = Math.min(league.promote, size);
	const demote = Math.max(0, Math.min(league.demote, size - promote));
	const me = league.me;
	const tiles = league.group.map((row) => {
		const zone = row.place <= promote ? "up" : demote && row.place > size - demote ? "down" : "";
		const you = row.id === me.id;
		return leagueTile(row, you, zone);
	});
	const fifth = league.group[promote - 1]?.points ?? 0;
	const words =
		me.place <= promote
			? `Termina em ${timeLeftText(ends, now)} · zona de subida!`
			: `Termina em ${timeLeftText(ends, now)} · faltam ${fmt(Math.max(1, fifth - me.points + 1))} pontos para subir`;
	return rankPage(state, "liga", [], tiles, {
		tint: LEAGUE_DIVISION_TINTS[division],
		meter: bar(me.points, Math.max(me.points, fifth, 1), words),
		strip: last ? [...strip, stat(divisionIcon(last.movedTo), lastChip(last), "Semana passada", "")] : strip,
		pinned: { ...leagueTile(me, true, ""), id: "pinned-me", title: `Você · #${me.place}`, subtitle: `${fmt(me.points)} pontos`, action: act("Ver minha posição", "rankingMyPosition", [me.id], { variant: "primary", ok: "" }) },
		focus: me.id,
		stats: [stat(divisionIcon(division), `#${me.place}`, "na liga"), stat("Icons/trophy", fmt(me.points), "pontos")],
		empty: "",
	});
}
const rankOf = (division: LeagueDivision) => ["bronze", "silver", "gold", "sapphire", "ruby", "emerald", "diamond"].indexOf(division);

function leagueTile(row: LeagueRow, you: boolean, zone: string): BoardTile {
	const group = zone === "up" ? "Zona de subida" : zone === "down" ? "Zona de descida" : "Na liga";
	return playerTile(row.id, { marketName: row.marketName, code: row.code, avatar: row.avatar, level: row.level }, row.place, {
		value: fmt(row.points),
		valueLabel: "pontos",
		tone: you ? "gold" : zone === "up" ? "success" : zone === "down" ? "danger" : "",
		group,
		you,
		sticker: row.isFriend && !you ? "AMIGO" : `NV ${row.level}`,
	});
}

// ------------------------------------------------------------------------------------------------------------ amigos

const columnLabels: Record<FriendsColumn, string> = { nivel: "Nível", semana: "Semana", curtidas: "Curtidas", nota: "Nota" };
function friendValue(row: FriendRank, column: FriendsColumn) {
	if (column === "semana") return { value: fmt(row.weekPoints), valueLabel: "pontos" };
	if (column === "curtidas") return { value: fmt(row.likes), valueLabel: row.likes === 1 ? "curtida" : "curtidas" };
	if (column === "nota") return { value: row.marketRating === null ? "–" : row.marketRating.toFixed(1).replace(".", ","), valueLabel: "nota" };
	return { value: fmt(row.xp), valueLabel: "XP" };
}

/** The column's icon on the tabs, the rows' values and the rivalry card. */
const columnIcons: Record<FriendsColumn, string> = { nivel: "Icons/medal", semana: "Icons/flame", curtidas: "Icons/like", nota: "shape:star" };
/** The number a column ranks by, for the rows' bars (relative to the leader). */
function columnNumber(row: FriendRank, column: FriendsColumn) {
	if (column === "semana") return row.weekPoints;
	if (column === "curtidas") return row.likes;
	if (column === "nota") return row.marketRating ?? 0;
	return row.xp;
}

/** "Faltam 3 níveis para passar a Banca do Bruno" (or "Você lidera! Ana está a 2 níveis") in the chosen column. */
function rivalText(me: FriendRank, other: FriendRank, column: FriendsColumn, lead: boolean): string {
	const name = nameOf(other);
	const plural = (n: number, one: string, many: string) => (n === 1 ? one : many);
	if (column === "nivel") {
		const levels = Math.abs(other.level - me.level);
		const xp = Math.abs(other.xp - me.xp);
		if (lead) return levels > 0 ? `Você lidera! ${name} está a ${levels} ${plural(levels, "nível", "níveis")}` : `Você lidera! ${name} está a ${fmt(xp)} XP`;
		return levels > 0 ? `${plural(levels, "Falta", "Faltam")} ${levels} ${plural(levels, "nível", "níveis")} para passar ${name}` : `Faltam ${fmt(xp + 1)} XP para passar ${name}`;
	}
	if (column === "semana") {
		const gap = Math.abs(other.weekPoints - me.weekPoints);
		return lead ? `Você lidera! ${name} está a ${fmt(gap)} ${plural(gap, "ponto", "pontos")}` : `Faltam ${fmt(gap + 1)} pontos para passar ${name}`;
	}
	if (column === "curtidas") {
		const gap = Math.abs(other.likes - me.likes);
		return lead ? `Você lidera! ${name} está a ${gap} ${plural(gap, "curtida", "curtidas")}` : `${plural(gap + 1, "Falta", "Faltam")} ${gap + 1} ${plural(gap + 1, "curtida", "curtidas")} para passar ${name}`;
	}
	const gap = Math.abs((other.marketRating ?? 0) - (me.marketRating ?? 0));
	const words = gap.toFixed(1).replace(".", ",");
	if (gap < 0.05) return lead ? `Você lidera! ${name} está colado em você` : `Empatados na nota com ${name}`;
	return lead ? `Você lidera! ${name} está a ${words} de nota` : `Falta ${words} de nota para passar ${name}`;
}

function friendsPage(state: State): Page {
	const column = rankingsStore.column;
	const columns = (Object.keys(columnLabels) as FriendsColumn[]).map((id) =>
		act(columnLabels[id], "rankingColumn", [id], { icon: columnIcons[id], variant: id === column ? "coin" : "secondary", active: id === column, ok: "" }),
	);
	if (!rankingsOnline()) return rankPage(state, "amigos", [signInCard()], [], { empty: "Entre na sua conta para ver os amigos." });
	const loaded = rankingsStore.friends;
	if (!loaded.data) return rankPage(state, "amigos", [loaded.error ? troubleCard(loaded.error) : card("Carregando os amigos…", { icon: socialIcon("friends") })], [], { empty: "" });
	const id = myId();
	const sorted = sortFriendsBoard(friendsRows(), column);
	const leader = Math.max(0.0001, ...sorted.map((row) => columnNumber(row, column)));
	const before = rankingsStore.friendsBefore?.[column];
	const tiles = sorted.map((row, index) => ({
		...playerTile(row.id, row, index + 1, {
			...friendValue(row, column),
			you: row.id === id,
			// (the row has its own "Visitar": the side panel stays short enough to never scroll)
			actions: [],
		}),
		// a small "Visitar" on each friend's row, the value's icon, a bar against the leader and ▲/▼ since last time
		action: row.id === id ? button("", { enabled: false }) : act("Visitar", "socialVisit", [row.id], { icon: socialIcon("market"), variant: "primary", ok: "" }),
		valueIcon: columnIcons[column],
		fill: Math.max(0.04, Math.min(1, columnNumber(row, column) / leader)),
		trend: rankTrend(before, row.id, index + 1),
	}));
	const invite = tile("invite", "Chame amigos para disputar", {
		group: "",
		icon: socialIcon("friends"),
		frame: "rank",
		look: "invite",
		subtitle: "Quem entrar pelo seu convite e chegar ao Späti ganha 30 diamantes, e você também.",
		rank: "",
		action: act("Convidar", "socialShare", [], { icon: socialIcon("share"), variant: "success", ok: "" }),
		detail: "Mande o seu código para os amigos e disputem o ranking juntos.",
		actions: [act("Convidar amigos", "socialShare", [], { icon: socialIcon("share"), variant: "success", ok: "" })],
	});
	const meRow = sorted.find((row) => row.id === id);
	const place = meRow ? sorted.indexOf(meRow) + 1 : 0;
	const cards: Card[] = sorted.length <= 1 ? [card("Jogue junto com os amigos!", { icon: socialIcon("friends"), eyebrow: "NENHUM AMIGO AINDA", tone: "gold", lines: ["Adicione amigos em Amigos e vejam quem vai mais longe."], buttons: [act("Convidar amigos", "socialShare", [], { icon: socialIcon("share"), variant: "success", ok: "" })] })] : [];
	const podium = sorted.length >= 3 ? tiles.slice(0, 3) : [];
	// the rival: the friend just above me, or the one just below when I lead
	const other = meRow && sorted.length > 1 ? sorted[place === 1 ? 1 : place - 2] : null;
	const rival =
		meRow && other
			? {
					meIcon: faceOf(meRow.avatar),
					meName: "Você",
					meValue: friendValue(meRow, column).value,
					otherIcon: faceOf(other.avatar),
					otherName: nameOf(other),
					otherValue: friendValue(other, column).value,
					text: rivalText(meRow, other, column, place === 1),
					lead: place === 1,
					icon: columnIcons[column],
					button: optOutButton(),
				}
			: null;
	return rankPage(state, "amigos", cards, [...(podium.length ? tiles.slice(3) : tiles), invite], {
		podium,
		pinned: meRow ? { ...tiles[place - 1], id: "pinned-me", title: `Você · #${place}`, subtitle: nameOf(meRow), trend: 0, action: act("Ver minha posição", "rankingMyPosition", [meRow.id], { variant: "primary", ok: "" }) } : tile("", ""),
		stats: [stat(socialIcon("friends"), String(Math.max(0, sorted.length - 1)), "amigos"), ...(place ? [stat("Icons/trophy", `#${place}`, "entre os amigos")] : [])],
		meter: meter("Amigos", place ? sorted.length - place + 1 : 0, Math.max(1, sorted.length), {
			icon: socialIcon("friends"),
			tone: "gold",
			text: place ? `Você é #${place} de ${sorted.length} entre os amigos` : "Seus amigos",
			buttons: [optOutButton()],
		}),
		rival,
		empty: "",
	}, { tabs: columns });
}

export const routes: Routes = {
	ranking: (state, [tab]) => {
		const which = (["amigos", "liga", "mundo", "pais"].includes(tab ?? "") ? tab : rankingsStore.tab) as RankingTab;
		if (which === "liga") return leaguePage(state);
		if (which === "amigos") return friendsPage(state);
		return levelPage(state, which);
	},
};

// ------------------------------------------------------------------------------------------------------------ end of week

export type LeagueCardView = {
	key: string;
	headline: string;
	title: string;
	subtitle: string;
	place: number;
	division: string;
	movedTo: string;
	/** "up" | "down" | "same" */
	moved: string;
	movedText: string;
	/** The stamp over the new badge: "SUBIU!" | "CAIU" | "MANTEVE". */
	stamp: string;
	badgeFrom: string;
	badgeTo: string;
	diamonds: number;
	coins: number;
	avatar: string;
	/** My name and the tag over my face when I am on the podium. */
	meName: string;
	meTag: string;
	/** The podium of that week's group (names, faces and points, 1st to 3rd): from the item's `top`, else what this
	 * phone saw in the Liga tab; me on mine. An unknown place: "" (Unity shows the division medal). */
	podiumNames: string[];
	podiumAvatars: string[];
	podiumPoints: string[];
	/** The stats row: "#2 de 30 jogadores", "1.452 pontos na semana", "28 jogadores que você passou". */
	stats: BoardStat[];
	button: string;
	/** The new division's colour (confetti, glow). */
	tint: string;
};

/** The first end-of-week card waiting in the save (null = none). The diamonds and coins are already in the save. */
export function leagueCardView(state: State): LeagueCardView | null {
	const card0 = viewRankings().cards[0];
	if (!card0) return null;
	const moved = rankOf(card0.movedTo) > rankOf(card0.division) ? "up" : rankOf(card0.movedTo) < rankOf(card0.division) ? "down" : "same";
	const me = socialStore.me;
	const myFace = avatarIcon(me?.avatar ?? state.social?.profile?.avatar ?? null);
	const myName = me?.marketName?.trim() || (me?.code ? `Mercado #${formatCode(me.code)}` : "Você");
	const seen = rankingsStore.podiums.get(card0.week) ?? [];
	const names: string[] = [];
	const avatars: string[] = [];
	const points: string[] = [];
	for (let place = 1; place <= 3; place++) {
		const top = card0.top[place - 1];
		const row = seen.find((entry) => entry.place === place);
		if (place === card0.place) {
			names.push(myName);
			avatars.push(myFace);
			points.push(top ? fmt(top.points) : card0.points ? fmt(card0.points) : "");
		} else if (top) {
			names.push(nameOf(top));
			avatars.push(faceOf(top.avatar));
			points.push(fmt(top.points));
		} else {
			names.push(row ? nameOf(row) : "");
			avatars.push(row ? faceOf(row.avatar) : "");
			points.push(row ? fmt(row.points) : "");
		}
	}
	const stats: BoardStat[] = [];
	if (card0.place > 0 && card0.size > 0) stats.push(stat("Icons/trophy", `#${card0.place}`, `de ${card0.size} jogadores`));
	if (card0.points > 0) stats.push(stat("Icons/flame", fmt(card0.points), "pontos na semana"));
	if (card0.place > 0 && card0.size > 0) stats.push(stat("Icons/friends", fmt(Math.max(0, card0.size - card0.place)), "jogadores que você passou"));
	return {
		key: card0.id,
		headline: "FIM DA LIGA",
		title: card0.place > 0 ? `Você terminou em #${card0.place}!` : "A liga da semana terminou",
		subtitle: divisionName(card0.division),
		place: card0.place,
		division: card0.division,
		movedTo: card0.movedTo,
		moved,
		movedText:
			moved === "up"
				? `Subiu para a ${divisionName(card0.movedTo)}!`
				: moved === "down"
					? `${divisionName(card0.movedTo)} na próxima semana: bora voltar!`
					: `Continua na ${divisionName(card0.movedTo)}`,
		stamp: moved === "up" ? "SUBIU!" : moved === "down" ? "CAIU" : "MANTEVE",
		badgeFrom: divisionIcon(card0.division),
		badgeTo: divisionIcon(card0.movedTo),
		diamonds: card0.diamonds,
		coins: card0.coins,
		avatar: myFace,
		meName: myName,
		meTag: "VOCÊ",
		podiumNames: names,
		podiumAvatars: avatars,
		podiumPoints: points,
		stats,
		button: "Pegar prêmios",
		tint: LEAGUE_DIVISION_TINTS[card0.movedTo],
	};
}
