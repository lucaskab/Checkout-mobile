import "../../desktop/require-shim.ts";
// QA: the game's host side (desktop/social.ts) against the REAL Worker (worker/, social routes from branch social-server),
// with node:sqlite + in-memory R2 like the Worker's own tests. Unity's role (CheckoutSocial: the HTTP call with the
// session token) is played by `send` below. Needs the social Worker in worker/ (after social-server is merged):
//   CHECKOUT_DESKTOP_SAVE=/tmp/social-qa.json node --no-warnings --import ./desktop/register.mjs scripts/social/server-qa.mts
import assert from "node:assert/strict";
import { createApp } from "../../worker/src/app.ts";
import { Store } from "../../worker/src/store.ts";
import { DAY_MS, dayOf } from "../../worker/src/limits.ts";
import { fakeD1, fakeR2 } from "../../worker/test/fakes.ts";
import { useGameStore } from "@/stores/game-store";
import * as social from "../../desktop/social.ts";
import { exportSave } from "../../desktop/cloud.ts";
import { createMockFriendSave } from "../../desktop/social-mock.ts";
import { getSocialRewards, getDeliveryReward } from "@/data/social";
import { itemCatalog } from "@/data/market-products";

async function main() {

const T0 = Date.now();
const clock = { now: T0 };
const db = fakeD1();
const store = new Store(db, fakeR2(), { clock: () => clock.now, log: () => {} });
const app = createApp({
	store,
	verifyGoogle: async (t: string) => (t.startsWith("token-") ? { sub: `g-${t.slice(6)}`, email: `${t.slice(6)}@example.com`, name: t.slice(6) } : null),
	sessionSecret: "qa-secret-qa-secret-qa-secret-qa-1234",
	rateLimit: 1_000_000,
	now: () => clock.now,
	log: () => {},
});
const http = async (method: string, path: string, body?: unknown, token?: string) => {
	const response = await app(
		new Request(`https://checkout-server.example${path}`, {
			method,
			headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
			body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
		}),
		"1.2.3.4",
	);
	const text = await response.text();
	return { status: response.status, text, body: text ? JSON.parse(text) : null };
};
const login = async (name: string) => {
	const r = await http("POST", "/v1/auth/google", { idToken: `token-${name}` });
	const me = (await http("GET", "/v1/social/me", undefined, r.body.token)).body;
	return { name, token: r.body.token as string, id: r.body.player.id as string, code: me.code as string, revision: 0 };
};
/** Unity's upload body: the public block as the LAST field, raw JSON. */
const upload = async (user: { token: string; revision: number }, data: string, publicJson: string) => {
	const body = `{"baseRevision":${user.revision},"data":${JSON.stringify(data)},"deviceId":"qa","force":false${publicJson ? `,"public":${publicJson}` : ""}}`;
	const r = await http("PUT", "/v1/save", body, user.token);
	assert.equal(r.status, 200, r.text);
	user.revision = r.body.revision;
};

// --- players
const lucas = await login("lucas");
const ana = await login("ana");
const bruno = await login("bruno");
await http("PUT", "/v1/social/me", { marketName: "Mercado da Ana", avatar: "shopper-3" }, ana.token);
await http("PUT", "/v1/social/me", { marketName: "Banca do Bruno", avatar: "shopper-7" }, bruno.token);
const anaSave = createMockFriendSave({ era: "spati", level: 9, coins: 4000, evolutions: [{ id: "evolucao-shelf-crates-2-1", kind: "shelf", targetId: "crates", toTier: 2, minutesLeft: 40 }], now: T0 });
const anaPublic = JSON.stringify({ builds: [{ id: "evolution:evolucao-shelf-crates-2-1", kind: "evolution", item: "shelf-crates", tier: 2, endsAt: T0 + 40 * 60_000 }], stage: "spati", marketRating: 4.4 });
await upload(ana, anaSave, anaPublic);

// --- the game (host) with Unity's transport
let failAck = 0;
const sent: any[] = [];
const results: string[] = [];
const ok = (name: string) => results.push(`RESULT ${name}: PASS`);
social.initSocial({
	send: (message: any) => {
		sent.push(message);
		if (message.kind !== "social-call") return;
		if (message.path === "/v1/social/inbox/ack" && failAck > 0) {
			failAck--;
			setTimeout(() => social.applySocialReply({ id: message.id, code: 0, body: "", network: true }), 0);
			return;
		}
		http(message.method, message.path, message.body || undefined, lucas.token).then((r) =>
			social.applySocialReply({ id: message.id, code: r.status, body: r.text, network: false }),
		);
	},
	refresh: () => {},
	unity: false,
});
social.applySocialStatus({ signedIn: true, mock: false, platform: "editor", canShare: true });
const settle = async () => {
	for (let i = 0; i < 500 && (i < 3 || social.socialStore.busy.size > 0 || social.socialStore.loading); i++) await new Promise((r) => setTimeout(r, 2));
};
const act = async (action: string, ...args: unknown[]) => {
	social.requestSocialAction(action, args);
	await settle();
};
const toasts = () => sent.filter((m) => m.kind === "social-toast").map((m) => m.text);
const game = () => useGameStore.getState();

// profile
assert.equal(await social.loadSocial(true), true);
assert.equal(social.socialStore.me!.code, lucas.code);
assert.equal(social.socialStore.me!.marketName, null);
await act("socialSaveProfile", "Mercadinho do Lucas", "shopper-4");
assert.equal(social.socialStore.me!.marketName, "Mercadinho do Lucas");
assert.equal(game().social.profile.code, lucas.code);
ok("profile name + avatar (PUT /me)");

// add by code (typed with a dash, lower case) → Ana accepts
await act("socialAddFriend", `${ana.code.slice(0, 4).toLowerCase()}-${ana.code.slice(4)}`);
assert.equal(toasts().at(-1), "Pedido de amizade enviado!");
assert.equal((await http("POST", "/v1/social/friends/accept", { id: lucas.id }, ana.token)).status, 200);
// Bruno asks Lucas; Lucas accepts in the game
await http("POST", "/v1/social/friends/add", { code: lucas.code }, bruno.token);
await social.loadSocial(true);
assert.deepEqual(social.socialStore.incoming.map((p) => p.id), [bruno.id]);
await act("socialAccept", bruno.id);
assert.deepEqual(social.socialStore.friends.map((f) => f.id).sort(), [ana.id, bruno.id].sort());
ok("add by code / accept");

// inbox: friend_added (from Ana accepting) + gifts/likes from friends; applied once, acked
await http("POST", "/v1/social/gift", { to: lucas.id }, ana.token);
await http("POST", "/v1/social/like", { to: lucas.id }, bruno.token);
const coins0 = game().coins;
const first = await social.runInboxCycle("login");
const rewards = getSocialRewards(game().era.id);
// the like pays at once; the gift waits in the Correio until "Abrir"
assert.equal(game().coins, coins0 + rewards.like);
assert.equal(game().social.mailbox.length, 1);
await act("socialOpenMail", "all");
assert.equal(game().coins, coins0 + rewards.like + rewards.gift);
assert.equal(first.acked, first.applied);
assert.equal((await http("GET", "/v1/social/inbox", undefined, lucas.token)).body.items.length, 0);
ok(`inbox applied ${first.applied} and acked (friend_added, gift, like)`);

// crash between save and ack
await http("POST", "/v1/social/gift", { to: lucas.id }, bruno.token);
failAck = 1;
const coins1 = game().coins;
assert.deepEqual(await social.runInboxCycle(), { applied: 1, acked: 0 });
assert.equal(game().social.mailbox.length, 1);
assert.deepEqual(await social.runInboxCycle(), { applied: 0, acked: 1 });
assert.equal(game().social.mailbox.length, 1);
await act("socialOpenMail", "all");
assert.equal(game().coins, coins1 + rewards.gift);
ok("gift box applied exactly once across a lost ack, paid once when opened");

// like + help Ana at home (helper rewards after the server's OK)
const coins2 = game().coins;
await act("socialLike", ana.id);
await act("socialHelp", ana.id, "evolution:evolucao-shelf-crates-2-1");
await act("socialHelp", ana.id, "evolution:evolucao-shelf-crates-2-1");
assert.equal(toasts().at(-1), "Você já ajudou nesta obra.");
assert.equal(game().coins, coins2 + rewards.like + rewards.help);
const anaInbox = (await http("GET", "/v1/social/inbox", undefined, ana.token)).body.items.map((i: any) => i.kind);
assert.deepEqual(anaInbox.slice(-2), ["like", "help"]);
ok("like + help (409 already-helped on the second help)");

// visit Ana: the real market answer (data = the stored save text)
const apple = itemCatalog[0];
useGameStore.setState({ inventory: { ...game().inventory, [apple.id]: 10 } });
await http("POST", "/v1/social/requests", { productId: String(apple.id), qty: 4 }, ana.token);
await social.loadSocial(true);
const before = exportSave().data;
const visit = await social.startVisit(ana.id);
assert.equal(visit.ok, true, visit.reason);
assert.equal(social.visitSnapshot()!.era.id, "spati");
assert.equal(social.visitView()!.builds[0].helped, true);
const request = social.socialStore.visit!.friend.openRequests[0];
await act("socialSend", request.id, ana.id, apple.id, 4);
assert.equal(exportSave().data, before);
const coins3 = game().coins;
social.endVisit();
assert.equal(game().coins, coins3 + getDeliveryReward(apple.purchasePrice, 4));
assert.equal(game().inventory[apple.id], 6);
const delivered = (await http("GET", "/v1/social/inbox", undefined, ana.token)).body.items.filter((i: any) => i.kind === "delivery");
assert.equal(delivered[0].payload.qty, 4);
ok("visit (save frozen) + Enviar a requested product");

// ask friends; Bruno fulfils; the delivery lands in the stock room
const tomato = itemCatalog[1];
await act("socialRequest", tomato.id, 7);
assert.equal(game().social.requests.length, 1);
const mine = (await http("GET", "/v1/social/requests", undefined, bruno.token)).body.friends[0];
assert.equal((await http("POST", `/v1/social/requests/${mine.id}/fulfill`, undefined, bruno.token)).status, 204);
const have = game().inventory[tomato.id] ?? 0;
await social.runInboxCycle();
assert.equal(game().inventory[tomato.id], have + 7);
assert.deepEqual(game().social.requests, []);
ok("Pedir aos amigos → fulfil → delivery in stock");

// the cloud upload with the public block last; friends see the builds
useGameStore.setState({ interiorConstructions: [{ id: "shelf-produce-123", kind: "shelf", targetId: "produce", startedAt: clock.now - 60_000, endsAt: clock.now + 600_000 }] });
const exported = exportSave();
await upload(lucas, exported.data, exported.publicJson);
const seen = (await http("GET", "/v1/social/friends", undefined, ana.token)).body.friends.find((f: any) => f.id === lucas.id);
assert.equal(seen.public.builds[0].id, "interior:shelf-produce-123");
assert.equal((await http("POST", "/v1/social/help", { to: lucas.id, buildId: "interior:shelf-produce-123" }, ana.token)).status, 200);
const end = game().interiorConstructions[0].endsAt;
await social.runInboxCycle();
assert.equal(game().interiorConstructions[0].endsAt, end - 5 * 60_000);
ok("public block in PUT /v1/save (last field) → friend's help takes 5 min off");

// invite: Carla redeems Lucas's code, reaches level 8 → 30 diamonds + invite-reward-1
const carla = await login("carla");
assert.equal((await http("POST", "/v1/social/invite/redeem", { code: lucas.code }, carla.token)).body.status, "friends");
await upload(carla, JSON.stringify({ state: { coins: 1, era: { id: "spati" }, market: { level: 8 }, logistics: { premiumCurrency: 10 }, day: { dayNumber: 9 } }, version: 50 }), "");
const diamonds = game().logistics.premiumCurrency;
await social.runInboxCycle();
assert.equal(game().logistics.premiumCurrency, diamonds + 30);
assert.equal(game().interior.owned["invite-reward-1"], 1);
ok("invite redeem → level 8 → reward + milestone decoration");

// the player redeems Bruno's code? (account < 7 days) — and a second time
await act("socialRedeem", bruno.code);
await act("socialRedeem", bruno.code);
assert.equal(toasts().at(-1), "Você já usou um código de convite.");
ok("redeem once (409 already-invited)");

for (const line of results) console.log(line);
console.log(`RESULT server-qa: ${results.length} checks PASS against the Worker`);
process.exit(0);

}
main().catch((error) => {
	console.error(error);
	process.exit(1);
});
