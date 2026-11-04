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

// Friends show the photo of their Google login (docs/social-api.md › Photos) against the fake server: the Amigos list,
// the friends board (podium, rows, rival), the visit bar and my own face carry "avatar:<id>|<photo>"; strangers'
// requests and Mundo / País / Liga keep the avatar; the profile switch hides my photo from friends.
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
const { MOCK_PHOTOS } = await import("./social-mock.ts");
const { pages } = await import("./pages/index.ts");

const initial = JSON.stringify(useGameStore.getState());
const sent = [];
const game = () => useGameStore.getState();
const settle = async () => {
	for (let i = 0; i < 8; i++) await Bun.sleep(1);
};
const act = async (action, ...args) => {
	const result = social.requestSocialAction(action, args);
	await settle();
	return result;
};
const openRanking = async (tab) => {
	ranking.onRankingRoute(`ranking:${tab}`);
	await settle();
	return pages(game(), `ranking:${tab}`);
};
const face = (avatar, photo) => `avatar:${avatar}|${photo}`;

beforeAll(async () => {
	useGameStore.setState(JSON.parse(initial));
	social.resetSocial();
	ranking.resetRankings();
	social.initSocial({ send: (m) => sent.push(m), refresh: () => {}, onVisit: () => {}, unity: false });
	ranking.initRankings({ send: (m) => sent.push(m), refresh: () => {} });
	social.applySocialStatus({ mock: true, platform: "editor", canShare: true, avatars: 12 });
	social.onSocialRoute("amigos");
	await settle();
	await act("socialSaveProfile", "Mercado da Lia", "shopper-4");
	social.socialMock().control("photos");
	await social.loadSocial(true);
});
afterAll(() => {
	social.resetSocial();
	ranking.resetRankings();
	useGameStore.setState(JSON.parse(initial));
});

test("photoOf / avatarIcon: only https photos on Google's image hosts ride along with the avatar", () => {
	expect(social.avatarIcon("shopper-3", MOCK_PHOTOS.ana)).toBe(face("shopper-3", MOCK_PHOTOS.ana));
	expect(social.avatarIcon("shopper-3", null)).toBe("avatar:shopper-3");
	expect(social.avatarIcon(null, MOCK_PHOTOS.ana)).toBe(face("shopper-1", MOCK_PHOTOS.ana));
	for (const bad of ["http://lh3.googleusercontent.com/a/x", "https://lh3.googleusercontent.com.evil.example/a", "https://evil.example/a.png", "https://lh3.googleusercontent.com/a/x|y", "file:///etc/passwd", 7])
		expect(social.avatarIcon("shopper-3", bad)).toBe("avatar:shopper-3");
});

test("Amigos list: friends with a photo show it; switch off, Apple, unreachable → as sent; a stranger's request never", () => {
	const page = pages(game(), "amigos");
	const tile = (name) => page.board.tiles.find((t) => t.title === name);
	expect(tile("Mercado da Ana").icon).toBe(face("shopper-3", MOCK_PHOTOS.ana));
	// my own strip across the top (opens the profile)
	expect(page.board.meter?.icon ?? page.meter?.icon).toBe(face("shopper-4", MOCK_PHOTOS.me));
	// Gabi's photo is sent (Unity shows the avatar while it cannot download it).
	expect(tile("Supermercado da Gabi").icon).toBe(face("shopper-6", MOCK_PHOTOS.gabi));
	// Bruno turned the switch off, Carla signs in with Apple: their avatars.
	expect(tile("Banca do Bruno").icon).toBe("avatar:shopper-7");
	expect(tile("Tenda da Carla").icon).toBe("avatar:shopper-5");
	// Duda's request (not a friend yet): the avatar, and the server sent no photo at all.
	expect(tile("Quitanda da Duda").icon).toBe("avatar:shopper-9");
	expect(JSON.stringify(social.socialStore.incoming)).not.toContain("googleusercontent");
});

test("my profile: my photo on the card, the switch hides it from friends (and brings it back)", async () => {
	const profile = () => pages(game(), "amigos:perfil");
	let hero = profile().cards[0];
	expect(hero.icon).toBe(face("shopper-4", MOCK_PHOTOS.me));
	expect(hero.lines).toContain("Mostrar minha foto do Google para amigos");
	const toggle = () => profile().cards[0].buttons.find((b) => b.action === "socialShowPhoto");
	expect(toggle().label).toBe("Foto do Google: sim");
	await act("socialShowPhoto", false);
	expect(social.socialStore.me.showPhoto).toBe(false);
	hero = profile().cards[0];
	expect(hero.icon).toBe("avatar:shopper-4");
	expect(toggle().label).toBe("Foto do Google: não");
	expect(social.myPhoto()).toBe(null);
	// the friends board: my own row as friends see it
	ranking.rankingsStore.friends.loadedAt = 0;
	const board = await openRanking("amigos");
	const mine = [...board.board.podium, ...board.board.tiles].find((t) => t.title.endsWith("(você)"));
	expect(mine.icon).toBe("avatar:shopper-4");
	await act("socialShowPhoto", true);
	expect(social.myPhoto()).toBe(MOCK_PHOTOS.me);
});

test("a Google account without a photo (or Apple) has no switch on the profile", async () => {
	const saved = social.socialStore.me.photo;
	social.socialStore.me.photo = null;
	const hero = pages(game(), "amigos:perfil").cards[0];
	expect(hero.buttons.some((b) => b.action === "socialShowPhoto")).toBe(false);
	expect(hero.icon).toBe("avatar:shopper-4");
	social.socialStore.me.photo = saved;
});

test("friends board: podium, rows, rival and my row carry the photos; Mundo, País and Liga never", async () => {
	ranking.requestRankingAction("rankingColumn", ["nivel"]);
	ranking.rankingsStore.friends.loadedAt = 0;
	const page = await openRanking("amigos");
	const all = [...page.board.podium, ...page.board.tiles];
	const icon = (name) => all.find((t) => t.title.startsWith(name))?.icon;
	expect(icon("Mercado da Ana")).toBe(face("shopper-3", MOCK_PHOTOS.ana));
	expect(icon("Banca do Bruno")).toBe("avatar:shopper-7");
	expect(icon("Tenda da Carla")).toBe("avatar:shopper-5");
	expect(icon("Mercado da Lia")).toBe(face("shopper-4", MOCK_PHOTOS.me));
	expect(page.board.rival.meIcon).toBe(face("shopper-4", MOCK_PHOTOS.me));
	expect(page.board.rival.otherIcon).toMatch(/^avatar:shopper-\d+/);
	for (const tab of ["mundo", "pais", "liga"]) {
		const other = await openRanking(tab);
		expect(JSON.stringify(other)).not.toContain("googleusercontent");
	}
});

test("the visit bar shows the friend's photo", async () => {
	await act("socialVisit", "u-ana");
	for (let i = 0; i < 20 && !social.socialStore.visit; i++) await settle();
	const view = social.visitView();
	expect(view?.avatar).toBe(face("shopper-3", MOCK_PHOTOS.ana));
	expect(social.endVisit()).toBe(true);
	expect(social.socialStore.visit).toBe(null);
});
