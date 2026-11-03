import "../../desktop/require-shim.ts";
// QA: the game's host side of rankings v1 (desktop/rankings.ts, desktop/pages/ranking.ts, the league_reward in
// src/services/social.ts) against the REAL Worker (worker/, branch rank-server merged), with node:sqlite + in-memory R2
// like the Worker's own tests. Unity's role (CheckoutSocial: the HTTP call, with the session token unless the call is an
// open board and the player is signed out) is played by `send` below. Run from the repo root:
//   rm -f /tmp/rankings-qa.json; CHECKOUT_DESKTOP_SAVE=/tmp/rankings-qa.json node --no-warnings --import ./desktop/register.mjs scripts/rankings/server-qa.mts
import assert from "node:assert/strict";
import { createApp } from "../../worker/src/app.ts";
import { Store } from "../../worker/src/store.ts";
import { fakeD1, fakeR2 } from "../../worker/test/fakes.ts";
import { useGameStore } from "@/stores/game-store";
import * as social from "../../desktop/social.ts";
import * as ranking from "../../desktop/rankings.ts";
import { pages } from "../../desktop/pages/index.ts";
import { createDesktopView } from "../../desktop/view.ts";
import { createMockFriendSave } from "../../desktop/social-mock.ts";
import { isoWeek } from "@/services/rankings";
import { getSocialRewards } from "@/data/social";

async function main() {
	// Wednesday of an ISO week, mid-day UTC (the cap allows 3 days of points)
	const T0 = Date.UTC(2026, 10, 4, 12, 0, 0);
	const clock = { now: T0 };
	const realNow = Date.now;
	Date.now = () => clock.now;
	const store = new Store(fakeD1(), fakeR2(), { clock: () => clock.now, log: () => {} });
	const app = createApp({
		store,
		verifyGoogle: async (t: string) => (t.startsWith("token-") ? { sub: `g-${t.slice(6)}`, email: `${t.slice(6)}@example.com`, name: t.slice(6) } : null),
		sessionSecret: "qa-secret-qa-secret-qa-secret-qa-1234",
		rateLimit: 1_000_000,
		now: () => clock.now,
		log: () => {},
	});
	const http = async (method: string, path: string, body?: unknown, token?: string, country = "BR") => {
		const response = await app(
			new Request(`https://checkout-server.example${path}`, {
				method,
				headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
				body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
			}),
			"1.2.3.4",
			country,
		);
		const text = await response.text();
		return { status: response.status, text, body: text ? JSON.parse(text) : null };
	};
	type User = { name: string; token: string; id: string; code: string; revision: number; country: string };
	const login = async (name: string, country: string): Promise<User> => {
		const r = await http("POST", "/v1/auth/google", { idToken: `token-${name}` }, undefined, country);
		const me = (await http("GET", "/v1/social/me", undefined, r.body.token, country)).body;
		await http("PUT", "/v1/social/me", { marketName: `Mercado ${name}`, avatar: `shopper-${1 + (name.length % 12)}` }, r.body.token, country);
		return { name, token: r.body.token, id: r.body.player.id, code: me.code, revision: 0, country };
	};
	const upload = async (user: User, level: number, xp: number) => {
		const save = JSON.parse(createMockFriendSave({ era: level >= 8 ? "spati" : "banca", level, coins: 1000, now: clock.now }));
		save.state.market.totalExperience = xp;
		const body = `{"baseRevision":${user.revision},"data":${JSON.stringify(JSON.stringify(save))},"deviceId":"qa","force":false}`;
		const r = await http("PUT", "/v1/save", body, user.token, user.country);
		assert.equal(r.status, 200, r.text);
		user.revision = r.body.revision;
	};

	// --- a small world: Lucas (BR) and 24 others in four countries, levels around his
	const lucas = await login("lucas", "BR");
	const others: User[] = [];
	const countries = ["BR", "DE", "US", "PT"];
	for (let i = 0; i < 24; i++) {
		const user = await login(`p${i}`, countries[i % 4]);
		await upload(user, 3 + (i % 5), 400 + i * 37);
		others.push(user);
	}
	await upload(lucas, 5, 900);
	await http("POST", "/v1/social/friends/add", { code: others[0].code }, lucas.token);
	await http("POST", "/v1/social/friends/accept", { id: lucas.id }, others[0].token, others[0].country);

	// --- the game (host) with Unity's transport
	let failAck = 0;
	let signedIn = true;
	const sent: any[] = [];
	const results: string[] = [];
	const ok = (name: string) => results.push(`RESULT ${name}: PASS`);
	const transport = (message: any) => {
		sent.push(message);
		if (message.kind !== "social-call") return;
		if (message.path === "/v1/social/inbox/ack" && failAck > 0) {
			failAck--;
			setTimeout(() => social.applySocialReply({ id: message.id, code: 0, body: "", network: true }), 0);
			return;
		}
		// Unity: signed in → with the session; signed out → only an open board, without it
		if (!signedIn && !message.open) return setTimeout(() => social.applySocialReply({ id: message.id, code: 401, body: '{"error":"signed-out"}', network: false }), 0);
		http(message.method, message.path, message.body || undefined, signedIn ? lucas.token : undefined, "BR").then((r) =>
			social.applySocialReply({ id: message.id, code: r.status, body: r.text, network: false }),
		);
	};
	social.initSocial({ send: transport, refresh: () => {}, unity: false });
	ranking.initRankings({ send: transport, refresh: () => {} });
	social.applySocialStatus({ signedIn: true, mock: false, platform: "editor", canShare: true });
	const game = () => useGameStore.getState();
	useGameStore.setState({ market: { ...game().market, level: 5, totalExperience: 900 } });
	const load = async (tab: ranking.RankingTab) => {
		// (a reload the game started itself, after the opt-out, finishes first)
		for (let i = 0; i < 500 && ranking.rankingsStore.loading.size; i++) await new Promise((r) => setTimeout(r, 2));
		ranking.rankingsStore[tab === "mundo" ? "world" : tab === "pais" ? "country" : tab === "amigos" ? "friends" : "league"].loadedAt = 0;
		assert.equal(await ranking.loadRankingTab(tab, true), true, `load ${tab}`);
		return pages(game(), `ranking:${tab}`);
	};

	// Mundo / País
	const world = await load("mundo");
	assert.equal(world.board.podium.length, 3);
	assert.ok(world.board.tiles.length >= 20);
	assert.match(world.board.pinned.title, /^Você · #\d+$/);
	assert.equal(ranking.rankingsStore.world.data!.total, 25);
	ok(`Mundo: podium, ${world.board.tiles.length} rows, pinned "${world.board.pinned.title}"`);
	const country = await load("pais");
	assert.equal(ranking.rankingsStore.country.data!.country, "BR");
	assert.equal(country.board.meter.title, "Brasil");
	assert.ok([...country.board.podium, ...country.board.tiles].every((tile) => tile.flag === "Flags/br"));
	ok(`País BR: ${ranking.rankingsStore.country.data!.total} players, flag and name`);
	// Amigos: rank null from the server, the game ranks by the column
	const friends = await load("amigos");
	assert.ok(ranking.rankingsStore.friends.data!.every((row) => row.rank === null));
	assert.equal(ranking.rankingsStore.friends.data!.length, 2);
	assert.equal(friends.board.tiles.at(-1)!.id, "invite");
	ok("Amigos: me + friend, rank null, sorted by the game, invite row");

	// Liga: before joining, then points earned and sent
	const before = await load("liga");
	assert.equal(before.cards[0].title, "Faça pontos para entrar na liga desta semana");
	assert.equal(ranking.rankingsStore.league.data!.promote, 5);
	game().claimSocialHelperReward("help");
	game().claimSocialHelperReward("help");
	const sentNow = await ranking.sendLeaguePoints("qa", true);
	assert.equal(sentNow.sent, true, JSON.stringify(sentNow));
	assert.equal(game().rankings.sentPoints, 10);
	// the others of his level band join too (≥ 1 point)
	for (const [i, user] of others.entries()) await http("POST", "/v1/rankings/league/points", { week: isoWeek(clock.now), points: 5 + i * 3 }, user.token, user.country);
	const joined = await load("liga");
	const league = ranking.rankingsStore.league.data!;
	const n = league.group.length;
	assert.equal(league.promote, Math.min(5, Math.floor(n / 2)));
	assert.ok(league.me && league.me.points === 10);
	assert.match(joined.board.pinned.title, /^Você · #\d+$/);
	ok(`Liga: joined with 10 points, group of ${n}, zones ${league.promote}/${league.demote}`);

	// 409 wrong-week: the device clock one week behind → the server's week wins, sent again
	useGameStore.setState({ rankings: { ...game().rankings, week: isoWeek(clock.now - 7 * 86_400_000), skew: { week: isoWeek(clock.now - 7 * 86_400_000), deviceWeek: isoWeek(clock.now) }, points: 3, sentPoints: 0 } });
	const retried = await ranking.sendLeaguePoints("qa", true);
	const posts = sent.filter((m) => m.kind === "social-call" && m.path === "/v1/rankings/league/points");
	assert.equal(game().rankings.week, isoWeek(clock.now));
	assert.ok(posts.length >= 2);
	assert.equal(game().rankings.points, 0);
	ok(`409 wrong-week → server week ${game().rankings.week} (${retried.reason})`);
	// put the real total back for the end of the week
	game().claimSocialHelperReward("help");
	await ranking.sendLeaguePoints("qa", true);

	// end of the week: the lazy close on the next league call, one league_reward, applied once across a lost ack
	clock.now = T0 + 6 * 86_400_000;
	assert.equal((await http("GET", "/v1/rankings/league", undefined, lucas.token)).status, 200);
	const inbox = (await http("GET", "/v1/social/inbox", undefined, lucas.token)).body.items.filter((item: any) => item.kind === "league_reward");
	assert.equal(inbox.length, 1, JSON.stringify(inbox));
	const payload = inbox[0].payload;
	const diamonds0 = game().logistics.premiumCurrency;
	const coins0 = game().coins;
	failAck = 1;
	await social.runInboxCycle("qa");
	await social.runInboxCycle("qa");
	assert.equal(game().logistics.premiumCurrency, diamonds0 + payload.diamonds);
	assert.equal(game().coins, coins0 + (payload.chest ? 3 * getSocialRewards(game().era.id).gift : 0));
	assert.equal((await http("GET", "/v1/social/inbox", undefined, lucas.token)).body.items.length, 0);
	const card = createDesktopView(game(), 1, []).leagueCard!;
	assert.equal(card.place, payload.place);
	ok(`end of week: place ${payload.place}, +${payload.diamonds} diamonds${payload.chest ? " + chest" : ""}, once across a lost ack; card ${card.moved}`);

	// opt-out: off the boards (rank null), back on
	ranking.requestRankingAction("rankingOptOut", [true]);
	for (let i = 0; i < 200 && ranking.rankingsStore.busy.size; i++) await new Promise((r) => setTimeout(r, 2));
	await load("mundo");
	assert.equal(ranking.rankingsStore.world.data!.me!.rank, null);
	assert.equal(game().rankings.optOut, true);
	ranking.requestRankingAction("rankingOptOut", [false]);
	for (let i = 0; i < 200 && ranking.rankingsStore.busy.size; i++) await new Promise((r) => setTimeout(r, 2));
	await load("mundo");
	assert.ok((ranking.rankingsStore.world.data!.me!.rank ?? 0) > 0);
	ok("opt-out: rank null on the boards, then back");

	// signed out: Mundo still loads (open call, no token), me null; Liga asks to sign in
	signedIn = false;
	social.applySocialStatus({ signedIn: false, mock: false, platform: "editor", canShare: true });
	const open = await load("mundo");
	assert.equal(ranking.rankingsStore.world.data!.me, null);
	assert.equal(open.cards[0].title, "Entre para aparecer no ranking");
	assert.equal(pages(game(), "ranking:liga").cards[0].title, "Entre para aparecer no ranking");
	ok("signed out: Mundo read-only (no token), Liga asks to sign in");

	Date.now = realNow;
	for (const line of results) console.log(line);
	console.log(`RESULT rankings server-qa: ${results.length} checks PASS against the Worker`);
	process.exit(0);
}
main().catch((error) => {
	console.error(error);
	process.exit(1);
});
