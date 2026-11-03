import { plugin } from "bun";
import { afterAll, beforeAll, expect, mock, test } from "bun:test";

plugin({
	name: "png-as-id",
	setup(build) {
		build.onLoad({ filter: /\.png$/ }, (args) => ({
			contents: `const path = ${JSON.stringify(args.path)}; export default path; export const toString = () => path;`,
			loader: "js",
		}));
	},
});

// Rankings v1 on the host (desktop/rankings.ts, desktop/pages/ranking.ts) against the fake server
// (desktop/rankings-mock.ts behind desktop/social-mock.ts), with the real store: the four tabs, the podium and my pinned
// row, joining the league by earning points, wrong-week, the league reward applied once across a lost ack, viewing
// never touching the save, the opt-out and the signed-out boards.
globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../src/stores/game-store.ts");
const social = await import("./social.ts");
const ranking = await import("./rankings.ts");
const { pages } = await import("./pages/index.ts");
const { createDesktopView } = await import("./view.ts");
const { isoWeek } = await import("../src/services/rankings.ts");
const { setLanguage } = await import("../src/i18n/index.ts");
const { countryName } = await import("./pages/ranking.ts");

const initial = JSON.stringify(useGameStore.getState());
const sent = [];
const game = () => useGameStore.getState();
const settle = async () => {
	for (let i = 0; i < 8; i++) await Bun.sleep(1);
};
const storedSave = () => JSON.stringify(useGameStore.persist.getOptions().storage.getItem("checkout.game"));

beforeAll(() => {
	useGameStore.setState(JSON.parse(initial));
	social.resetSocial();
	ranking.resetRankings();
	social.initSocial({ send: (m) => sent.push(m), refresh: () => {}, onVisit: () => {}, unity: false });
	ranking.initRankings({ send: (m) => sent.push(m), refresh: () => {} });
	social.applySocialStatus({ mock: true, platform: "editor", canShare: true, avatars: 12 });
});
afterAll(() => {
	social.resetSocial();
	ranking.resetRankings();
	useGameStore.setState(JSON.parse(initial));
});

const open = async (tab) => {
	ranking.onRankingRoute(`ranking:${tab}`);
	await settle();
	return pages(game(), `ranking:${tab}`);
};

test("Mundo: a full-screen board with the top three on the podium, ranked rows, flags and my row pinned", async () => {
	const world = await open("mundo");
	expect(world.layout).toBe("board");
	expect(world.board.style).toBe("rank");
	expect(world.sections.map((s) => s.label)).toEqual(["Amigos", "Liga", "Mundo", "País"]);
	expect(world.sections[2].active).toBe(true);
	expect(world.board.podium).toHaveLength(3);
	expect(world.board.podium.map((t) => t.rank)).toEqual(["1", "2", "3"]);
	expect(world.board.podium.every((t) => t.icon.startsWith("avatar:") && t.flag.startsWith("Flags/"))).toBe(true);
	expect(world.board.tiles[0].rank).toBe("4");
	expect(world.board.tiles.length).toBe(97);
	const pinned = world.board.pinned;
	expect(pinned.id).toBe("pinned-me");
	expect(pinned.title).toMatch(/^Você · #\d/);
	// opening Ranking created the social profile (the first call), so the inbox is polled from now on
	expect(social.socialTouched()).toBe(true);
	expect(social.socialMock().log.slice(0, 2)).toEqual(["GET /v1/social/me", "GET /v1/rankings/world?limit=100"]);
});

test("País: the player's flag and the country's name from the ISO code, in every language", async () => {
	const country = await open("pais");
	expect(country.board.meter.icon).toBe("Flags/br");
	expect(country.board.meter.title).toBe("Brasil");
	expect(country.board.tiles.concat(country.board.podium).every((t) => t.flag === "Flags/br")).toBe(true);
	const names = ["pt", "en", "es", "fr", "de"].map((lang) => {
		setLanguage(lang);
		return countryName("DE");
	});
	setLanguage("pt");
	expect(names).toEqual(["Alemanha", "Germany", "Alemania", "Allemagne", "Deutschland"]);
	// "Ver minha posição" when I am in the top 100 of my country
	const me = country.board.pinned;
	if (me.action.action) {
		expect(ranking.requestRankingAction("rankingMyPosition", [JSON.parse(me.action.args)[0]]).ok).toBe(true);
		expect(pages(game(), "ranking:pais").board.scroll).toMatch(/#1$/);
	}
});

// The save without the Amigos board's last-seen places (the one thing opening it remembers, for the ▲/▼).
const saveSansSeen = () => {
	let saved = JSON.parse(storedSave());
	if (typeof saved === "string") saved = JSON.parse(saved);
	delete saved.state.rankings.seenRanks;
	return JSON.stringify(saved);
};

test("viewing the boards changes nothing in the save but the Amigos places it remembers for the ▲/▼", async () => {
	await settle();
	const before = saveSansSeen();
	for (const tab of ["mundo", "pais", "amigos", "liga"]) await open(tab);
	createDesktopView(game(), 1, ["ranking:liga"]);
	expect(saveSansSeen()).toBe(before);
	expect(Object.keys(game().rankings.seenRanks.nivel ?? {}).length).toBeGreaterThanOrEqual(3);
});

test("Liga: before joining, how to earn points; points earned and sent join the league", async () => {
	const before = await open("liga");
	expect(before.cards[0].title).toBe("Faça pontos para entrar na liga desta semana");
	expect(before.board.tiles.map((t) => t.id)).toContain("earn-customer");
	expect(before.board.strip.length).toBeGreaterThanOrEqual(5);
	expect(before.board.meter.icon).toBe("Icons/league-silver");
	game().claimSocialHelperReward("help");
	expect(game().rankings.points).toBeGreaterThan(0);
	const result = await ranking.sendLeaguePoints("test", true);
	expect(result.sent).toBe(true);
	expect(game().rankings.sentPoints).toBe(game().rankings.points);
	// nothing new: nothing sent
	expect((await ranking.sendLeaguePoints("again", true)).sent).toBe(false);
	ranking.rankingsStore.league.loadedAt = 0;
	const joined = await open("liga");
	const tiles = joined.board.tiles;
	expect(tiles.length).toBeGreaterThanOrEqual(29);
	expect(tiles.slice(0, 5).every((t) => t.tone === "success" || t.tone === "gold")).toBe(true);
	expect(tiles.slice(-5).every((t) => t.tone === "danger" || t.tone === "gold")).toBe(true);
	expect(tiles.some((t) => t.tone === "gold" && t.title.endsWith("(você)"))).toBe(true);
	expect(joined.board.pinned.title).toMatch(/^Você · #\d+/);
	expect(joined.board.meter.text).toMatch(/^Termina em /);
});

test("409 wrong-week: the server's week wins and the points go again", async () => {
	const server = social.socialMock().rankings;
	game().applyLeagueWrongWeek("2020-W01");
	useGameStore.setState({ rankings: { ...game().rankings, week: isoWeek(Date.now() - 7 * 86_400_000), skew: null } });
	game().claimSocialHelperReward("help");
	// the device clock says another week than the fake server's
	useGameStore.setState({ rankings: { ...game().rankings, skew: { week: "2030-W10", deviceWeek: isoWeek(Date.now()) }, week: "2030-W10", points: 7, sentPoints: 0 } });
	const result = await ranking.sendLeaguePoints("test", true);
	expect(social.socialMock().log.filter((l) => l.startsWith("POST /v1/rankings/league/points")).length).toBeGreaterThanOrEqual(2);
	expect(game().rankings.week).toBe(server.league.week);
	expect(result.reason === "nothing" || result.sent === true).toBe(true);
});

test("the league reward is applied once (diamonds up exactly once across a lost ack) and shows the end-of-week card", async () => {
	const diamonds = game().logistics.premiumCurrency;
	social.socialMock().control("league-reward");
	social.socialMock().control("fail", "/v1/social/inbox/ack");
	await social.runInboxCycle("test");
	expect(game().logistics.premiumCurrency).toBe(diamonds + 15);
	await social.runInboxCycle("test");
	expect(game().logistics.premiumCurrency).toBe(diamonds + 15);
	expect(social.socialMock().inbox.filter((row) => row.kind === "league_reward" && !row.acked)).toHaveLength(0);
	const view = createDesktopView(game(), 1, []);
	expect(view.leagueCard).toMatchObject({ place: 2, division: "bronze", movedTo: "silver", moved: "up", diamonds: 15, stamp: "SUBIU!" });
	// the real podium of that week's group (from the item's top): faces and names, me on my plinth
	expect(view.leagueCard.podiumNames.every((name) => name.length > 0)).toBe(true);
	expect(view.leagueCard.podiumAvatars.every((icon) => icon.startsWith("avatar:"))).toBe(true);
	expect(view.leagueCard.podiumNames[1]).toBe(view.leagueCard.meName);
	expect(view.leagueCard.stats.map((s) => s.label)).toEqual(["de 30 jogadores", "pontos na semana", "jogadores que você passou"]);
	expect(view.leagueCard.coins).toBeGreaterThan(0);
	expect(view.quick.find((b) => b.label === "Ranking").badge).toBe("1");
	expect(ranking.requestRankingAction("rankingDismissCard", [view.leagueCard.key]).ok).toBe(true);
	expect(createDesktopView(game(), 2, []).leagueCard).toBe(null);
});

test("Amigos: a rival card (me VS the friend above), bars against the leader, ▲/▼ since the board was last opened", async () => {
	ranking.requestRankingAction("rankingColumn", ["nivel"]);
	const first = await open("amigos");
	expect(first.board.rival.text).toMatch(/^(Faltam?|Você lidera!)/);
	expect(first.board.rival.meName).toBe("Você");
	expect(first.board.rival.button.label).toMatch(/^No ranking/);
	expect([...first.board.podium, ...first.board.tiles.filter((t) => t.id !== "invite")].every((t) => t.fill > 0 && t.fill <= 1 && t.valueIcon === "Icons/medal")).toBe(true);
	expect(first.board.tiles.at(-1).look).toBe("invite");
	// close the window, a friend climbs past the others, open again: ▲ for them, ▼ for who they passed
	ranking.onRankingRoute("home");
	social.socialMock().control("friend-up");
	ranking.rankingsStore.friends.loadedAt = 0;
	const again = await open("amigos");
	const all = [...again.board.podium, ...again.board.tiles];
	expect(all.some((t) => t.trend > 0)).toBe(true);
	expect(all.some((t) => t.trend < 0)).toBe(true);
	// staying in the window keeps the arrows (the baseline is this opening's)
	ranking.rankingsStore.friends.loadedAt = 0;
	const still = await open("amigos");
	expect([...still.board.podium, ...still.board.tiles].some((t) => t.trend > 0)).toBe(true);
});

test("Amigos: the column switch sorts the friends, an invite row closes the list", async () => {
	const friends = await open("amigos");
	expect(friends.tabs.map((b) => b.label)).toEqual(["Nível", "Semana", "Curtidas", "Nota"]);
	expect(friends.board.tiles.at(-1).id).toBe("invite");
	expect(friends.board.podium).toHaveLength(3);
	ranking.requestRankingAction("rankingColumn", ["curtidas"]);
	const byLikes = pages(game(), "ranking:amigos");
	const values = [...byLikes.board.podium, ...byLikes.board.tiles.filter((t) => t.id !== "invite")].map((t) => Number(t.value.replace(/\./g, "")));
	expect(values).toEqual([...values].sort((a, b) => b - a));
	expect(byLikes.tabs.find((b) => b.active).label).toBe("Curtidas");
});

test("Aparecer no ranking: off hides me from the boards (rank null), on brings me back", async () => {
	ranking.requestRankingAction("rankingOptOut", [true]);
	await settle();
	expect(game().rankings.optOut).toBe(true);
	const hidden = await open("mundo");
	expect(hidden.board.pinned.title).toBe("Você");
	expect(ranking.rankingsStore.world.data.me.rank).toBe(null);
	expect(hidden.board.meter.buttons[0].label).toBe("No ranking: não");
	// opted out: no points go to the league
	game().claimSocialHelperReward("help");
	expect((await ranking.sendLeaguePoints("test", true)).sent).toBe(false);
	ranking.requestRankingAction("rankingOptOut", [false]);
	await settle();
	expect(game().rankings.optOut).toBe(false);
	expect((await open("mundo")).board.pinned.title).toMatch(/^Você · #/);
});

test("signed out: Mundo and País stay readable with a sign-in card; Amigos and Liga ask to sign in", async () => {
	social.socialMock().control("signed-out");
	ranking.rankingsStore.world.loadedAt = 0;
	const world = await open("mundo");
	expect(world.cards[0].title).toBe("Entre para aparecer no ranking");
	// (the top three as rows under the card: the podium would not fit with it)
	expect(world.board.podium).toHaveLength(0);
	expect(world.board.tiles.slice(0, 3).map((tile) => tile.rank)).toEqual(["1", "2", "3"]);
	expect(world.board.pinned.id).toBe("");
	const league = await open("liga");
	expect(league.cards[0].title).toBe("Entre para aparecer no ranking");
	expect((await open("amigos")).cards[0].title).toBe("Entre para aparecer no ranking");
	expect((await ranking.sendLeaguePoints("test", true)).sent).toBe(false);
	social.socialMock().control("signed-out", "off");
});
