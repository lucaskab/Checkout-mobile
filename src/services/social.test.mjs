import { afterAll, beforeEach, expect, mock, test } from "bun:test";

globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../stores/game-store.ts");
const { applyBuildHelp, applyInboxItems, canSendProduct, computePublicBlock, getSocialBuilds, normalizeSocialState, utcDay } =
	await import("./social.ts");
const { getDeliveryReward, getSocialRewards, SOCIAL_APPLIED_KEEP, SOCIAL_GIFTS_PER_DAY, isAllowedMarketName } = await import("../data/social.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { interiorDecor } = await import("../data/interior-decor.ts");

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();
const MIN = 60_000;
const NOW = Date.UTC(2026, 10, 2, 15, 0, 0);
const ana = { id: "u_ana", code: "ANA123", marketName: "Mercado da Ana", avatar: "shopper-3" };
let nextId = 1;
const item = (kind, payload = {}, from = ana) => ({ id: nextId++, kind, from, payload, createdAt: NOW - 1000 });

test("old saves get an empty social slice and keep everything else (v49 → v50)", async () => {
	const old = JSON.parse(initial);
	delete old.social;
	old.coins = 4321;
	for (const key of Object.keys(old)) if (typeof old[key] === "function") delete old[key];
	const migrated = await useGameStore.persist.getOptions().migrate(old, 49);
	expect(migrated.coins).toBe(4321);
	expect(migrated.social).toEqual(normalizeSocialState(undefined));
	expect(migrated.social.appliedInbox).toEqual([]);
	expect(useGameStore.persist.getOptions().version).toBe(50);
	// Junk in the field never breaks a load.
	expect(normalizeSocialState({ appliedInbox: [1, "2", null, {}], gifts: { claimed: -3 }, requests: [{ id: "x" }, { id: 4, productId: 1, qty: 3 }] })).toMatchObject({
		appliedInbox: ["1", "2"],
		gifts: { day: "", claimed: 0 },
		requests: [{ id: 4, productId: 1, qty: 3 }],
	});
});

test("a gift pays coins scaled to the stage, once, and acks", () => {
	const gift = item("gift");
	const coins = game().coins;
	const first = game().applySocialInbox([gift], NOW);
	const reward = getSocialRewards(game().era.id).gift;
	expect(first.ack).toEqual([String(gift.id)]);
	expect(first.outcomes[0]).toMatchObject({ applied: true, coins: reward, name: "Mercado da Ana" });
	expect(game().coins).toBe(coins + reward);
	// The server sends it again (the ack was lost): acked, never paid twice.
	const again = game().applySocialInbox([gift], NOW + 1000);
	expect(again.ack).toEqual([String(gift.id)]);
	expect(again.outcomes[0].applied).toBe(false);
	expect(game().coins).toBe(coins + reward);
	expect(game().social.totals.gifts).toBe(1);
});

test("gifts stop at 25 a UTC day; the rest stay on the server until the next day", () => {
	const gifts = Array.from({ length: SOCIAL_GIFTS_PER_DAY + 3 }, () => item("gift"));
	const coins = game().coins;
	const reward = getSocialRewards(game().era.id).gift;
	const today = game().applySocialInbox(gifts, NOW);
	expect(today.ack).toHaveLength(SOCIAL_GIFTS_PER_DAY);
	expect(today.outcomes.filter((entry) => !entry.ack)).toHaveLength(3);
	expect(game().coins).toBe(coins + reward * SOCIAL_GIFTS_PER_DAY);
	expect(game().social.gifts).toEqual({ day: utcDay(NOW), claimed: SOCIAL_GIFTS_PER_DAY });
	// Same day, later: still capped.
	expect(game().applySocialInbox(gifts.slice(-3), NOW + 60 * MIN).ack).toEqual([]);
	// Next UTC day: the three waiting gifts open.
	const tomorrow = Date.UTC(2026, 10, 3, 0, 5);
	expect(game().applySocialInbox(gifts.slice(-3), tomorrow).ack).toHaveLength(3);
	expect(game().coins).toBe(coins + reward * (SOCIAL_GIFTS_PER_DAY + 3));
	expect(game().social.gifts.claimed).toBe(3);
});

test("a like pays a little", () => {
	const coins = game().coins;
	const { outcomes } = game().applySocialInbox([item("like")], NOW);
	expect(outcomes[0].coins).toBe(getSocialRewards(game().era.id).like);
	expect(game().coins).toBe(coins + outcomes[0].coins);
	expect(getSocialRewards("mesinha").like).toBeLessThan(getSocialRewards("mesinha").gift);
});

test("help takes 5 minutes off a running interior build, never ending before now", () => {
	useGameStore.setState({
		interiorConstructions: [
			{ id: "shelf-a", kind: "shelf", targetId: "a", startedAt: NOW - 10 * MIN, endsAt: NOW + 20 * MIN, durationMs: 30 * MIN },
			{ id: "shelf-b", kind: "shelf", targetId: "b", startedAt: NOW + 20 * MIN, endsAt: NOW + 50 * MIN, durationMs: 30 * MIN },
		],
	});
	const { outcomes } = game().applySocialInbox([item("help", { buildId: "interior:shelf-a", minutes: 5 })], NOW);
	expect(outcomes[0]).toMatchObject({ applied: true, minutes: 5, coins: 0 });
	const [a, b] = game().interiorConstructions;
	expect(a.endsAt).toBe(NOW + 15 * MIN);
	// The queued one starts when the running one ends.
	expect(b.startedAt).toBe(NOW + 15 * MIN);
	expect(b.endsAt).toBe(NOW + 45 * MIN);
	// Help on the queued one shortens its own working time.
	game().applySocialInbox([item("help", { buildId: "interior:shelf-b", minutes: 5 })], NOW);
	expect(game().interiorConstructions[1].endsAt).toBe(NOW + 40 * MIN);
	// Almost done: it ends now, not in the past.
	useGameStore.setState({ interiorConstructions: [{ id: "x", kind: "shelf", targetId: "x", startedAt: NOW - 10 * MIN, endsAt: NOW + 2 * MIN }] });
	game().applySocialInbox([item("help", { buildId: "interior:x", minutes: 5 })], NOW);
	expect(game().interiorConstructions[0].endsAt).toBe(NOW);
});

test("help on evolutions, the stage works and the lot clearing", () => {
	const era = game().era;
	useGameStore.setState({
		evolutions: [{ id: "evo-1", kind: "shelf", targetId: "gondola", toTier: 3, durationMs: 60 * MIN, startedAt: NOW - 30 * MIN, endsAt: NOW + 30 * MIN }],
		era: { ...era, construction: { eraId: "spati", startedAt: NOW - MIN, endsAt: NOW + 3 * MIN } },
		lots: { ...game().lots, clearing: { lotId: "lote-1", startedAt: NOW - MIN, endsAt: NOW + 60 * MIN } },
	});
	const builds = getSocialBuilds(game(), NOW).map((build) => build.id);
	expect(builds).toEqual([`era:spati:${NOW - MIN}`, "evolution:evo-1", `lot:lote-1:${NOW - MIN}`]);
	// A help for an older build in the same place (another start time) is not this one.
	expect(applyBuildHelp(game(), `lot:lote-1:${NOW - 99 * MIN}`, 5, NOW)).toBe(null);
	game().applySocialInbox(
		[item("help", { buildId: "evolution:evo-1", minutes: 5 }), item("help", { buildId: builds[0], minutes: 5 }), item("help", { buildId: builds[2], minutes: 5 })],
		NOW,
	);
	expect(game().evolutions[0].endsAt).toBe(NOW + 25 * MIN);
	expect(game().era.construction.endsAt).toBe(NOW);
	expect(game().lots.clearing.endsAt).toBe(NOW + 55 * MIN);
	expect(game().social.totals.helpsReceived).toBe(3);
});

test("help on a build that already finished is a small thank-you in coins", () => {
	const coins = game().coins;
	const { outcomes, ack } = game().applySocialInbox([item("help", { buildId: "interior:gone", minutes: 5 })], NOW);
	expect(ack).toHaveLength(1);
	expect(outcomes[0]).toMatchObject({ applied: true, minutes: 0, coins: getSocialRewards(game().era.id).thanks });
	expect(game().coins).toBe(coins + outcomes[0].coins);
	expect(applyBuildHelp(game(), "interior:gone", 5, NOW)).toBe(null);
});

test("a delivery goes into the stock room even past its room, and closes the request", () => {
	const product = itemCatalog[0];
	useGameStore.setState({
		inventory: { ...game().inventory, [product.id]: 7 },
		social: { ...game().social, requests: [{ id: 41, productId: product.id, qty: 12, createdAt: NOW - MIN, expiresAt: NOW + 1000 * MIN }] },
	});
	const { outcomes } = game().applySocialInbox([item("delivery", { requestId: 41, productId: product.id, qty: 12 })], NOW);
	expect(outcomes[0]).toMatchObject({ applied: true, productId: product.id, qty: 12 });
	expect(game().inventory[product.id]).toBe(19);
	expect(game().inventoryLots[product.id].reduce((sum, lot) => sum + lot.quantity, 0)).toBe(19);
	expect(game().social.requests).toEqual([]);
	// The server sends product ids as text ("47"): the same delivery.
	game().applySocialInbox([item("delivery", { requestId: 99, productId: String(product.id), qty: 2 })], NOW);
	expect(game().inventory[product.id]).toBe(21);
	// An unknown product: acked, nothing added.
	const before = JSON.stringify(game().inventory);
	expect(game().applySocialInbox([item("delivery", { productId: 999_999, qty: 3 })], NOW).ack).toHaveLength(1);
	expect(JSON.stringify(game().inventory)).toBe(before);
});

test("invite rewards: diamonds, and each milestone decoration once (never on sale)", () => {
	const diamonds = game().logistics.premiumCurrency;
	game().applySocialInbox([item("invite_reward", { diamonds: 30, role: "inviter", milestone: 1 })], NOW);
	expect(game().logistics.premiumCurrency).toBe(diamonds + 30);
	expect(game().interior.owned["invite-reward-1"]).toBe(1);
	// A repeated milestone (another item id) pays the diamonds but not a second decoration.
	game().applySocialInbox([item("invite_reward", { diamonds: 30, role: "inviter", milestone: 1 })], NOW);
	expect(game().interior.owned["invite-reward-1"]).toBe(1);
	game().applySocialInbox([item("invite_reward", { diamonds: 30, role: "invited" }), item("invite_reward", { diamonds: 5000, role: "inviter", milestone: 3 })], NOW);
	expect(game().social.invites).toEqual({ milestones: [1, 3], invited: true });
	expect(game().interior.owned["invite-reward-3"]).toBe(1);
	// A bad payload never pays more than the cap.
	expect(game().logistics.premiumCurrency).toBe(diamonds + 30 + 30 + 30 + 100);
	for (const id of ["invite-reward-1", "invite-reward-3", "invite-reward-5"]) {
		const decor = interiorDecor.find((entry) => entry.id === id);
		expect(decor?.exclusive).toBe("invite");
	}
});

test("a crash between the save and the ack: the reloaded save acks without paying again", async () => {
	const items = [item("gift"), item("like"), item("invite_reward", { diamonds: 30, role: "inviter" })];
	const before = { coins: game().coins, diamonds: game().logistics.premiumCurrency };
	game().applySocialInbox(items, NOW);
	const after = { coins: game().coins, diamonds: game().logistics.premiumCurrency };
	expect(after.coins).toBeGreaterThan(before.coins);
	// The save was written, the app died before POST /inbox/ack: the next start reloads it and gets the same items.
	const saved = JSON.parse(JSON.stringify(game()));
	for (const key of Object.keys(saved)) if (typeof saved[key] === "function") delete saved[key];
	// (A fresh store first: setState writes through to the storage, so the save goes in after it. The storage is the
	// store's own: the test files share one mocked storage.)
	useGameStore.setState(JSON.parse(initial));
	await useGameStore.persist.getOptions().storage.setItem("checkout.game", { state: saved, version: 50 });
	await useGameStore.persist.rehydrate();
	const replay = game().applySocialInbox(items, NOW + 5 * MIN);
	expect(replay.ack).toEqual(items.map((entry) => String(entry.id)));
	expect(replay.outcomes.every((entry) => !entry.applied)).toBe(true);
	expect({ coins: game().coins, diamonds: game().logistics.premiumCurrency }).toEqual(after);
});

test("the save remembers the last 300 applied ids", () => {
	const likes = Array.from({ length: SOCIAL_APPLIED_KEEP + 20 }, () => item("like"));
	game().applySocialInbox(likes, NOW);
	expect(game().social.appliedInbox).toHaveLength(SOCIAL_APPLIED_KEEP);
	expect(game().social.appliedInbox.at(-1)).toBe(String(likes.at(-1).id));
});

test("unknown kinds and toast-only kinds are acked and change nothing they should not", () => {
	const coins = game().coins;
	const { ack, outcomes } = game().applySocialInbox([item("friend_request"), item("friend_added", { via: "code" }), item("something_new")], NOW);
	expect(ack).toHaveLength(3);
	expect(outcomes.map((entry) => entry.text)).toEqual(["{0} quer ser seu amigo", "Agora você e {0} são amigos", ""]);
	expect(game().coins).toBe(coins);
	// A reported friend's name is hidden by the server; the toast falls back to the code.
	expect(game().applySocialInbox([item("like", {}, { ...ana, marketName: null })], NOW).outcomes[0].name).toBe("#ANA123");
});

test("the public block lists running builds and the stage", () => {
	useGameStore.setState({
		interiorConstructions: [
			{ id: "shelf-a", kind: "shelf", targetId: "a", startedAt: NOW - MIN, endsAt: NOW + 20 * MIN },
			{ id: "shelf-p", kind: "shelf", targetId: "p", startedAt: 0, endsAt: 0, pending: true, durationMs: 1000 },
			{ id: "shelf-done", kind: "shelf", targetId: "d", startedAt: NOW - 20 * MIN, endsAt: NOW - MIN },
		],
	});
	const block = computePublicBlock(game(), NOW);
	expect(block.builds).toEqual([{ id: "interior:shelf-a", kind: "interior", item: "shelf-a", tier: 0, endsAt: NOW + 20 * MIN }]);
	expect(block.stage).toBe(game().era.id);
	expect(block.marketRating).toBeGreaterThanOrEqual(0);
	expect(block.marketRating).toBeLessThanOrEqual(5);
	expect(JSON.stringify(block).length).toBeLessThan(4096);
});

test("helping a friend pays only through the store action (after the server said OK)", () => {
	const coins = game().coins;
	const reward = game().claimSocialHelperReward("help");
	expect(reward).toBe(getSocialRewards(game().era.id).help);
	expect(game().coins).toBe(coins + reward);
	expect(game().social.totals.helpsGiven).toBe(1);
	expect(game().claimSocialHelperReward("like")).toBe(getSocialRewards(game().era.id).like);
});

test("sending a requested product: checked first, taken out of the stock room after the OK, paid back +25%", () => {
	const product = itemCatalog[0];
	useGameStore.setState({ inventory: { ...game().inventory, [product.id]: 5 } });
	expect(canSendProduct(game(), product.id, 6)).toBe(false);
	expect(canSendProduct(game(), product.id, 5)).toBe(true);
	const coins = game().coins;
	const reward = game().completeSocialDelivery(product.id, 5);
	expect(reward).toBe(getDeliveryReward(product.purchasePrice, 5));
	expect(reward).toBeGreaterThan(product.purchasePrice * 5);
	expect(game().inventory[product.id]).toBe(0);
	expect(game().coins).toBe(coins + reward);
	expect(game().social.totals.sent).toBe(1);
});

test("profile and requests mirrors only change when they differ", () => {
	expect(game().rememberSocialProfile({ code: "K7Q2MX", marketName: "Mercadinho do Lucas", avatar: "shopper-2" })).toBe(true);
	expect(game().rememberSocialProfile({ code: "K7Q2MX", marketName: "Mercadinho do Lucas", avatar: "shopper-2" })).toBe(false);
	expect(game().rememberSocialRequests([{ id: 1, productId: 2, qty: 3, createdAt: NOW, expiresAt: NOW + 1 }])).toBe(true);
	expect(game().rememberSocialRequests([{ id: 1, productId: 2, qty: 3, createdAt: NOW, expiresAt: NOW + 1 }])).toBe(false);
	expect(isAllowedMarketName("Mercado da Ana")).toBe(true);
	expect(isAllowedMarketName("ab")).toBe(false);
	expect(isAllowedMarketName("<script>")).toBe(false);
});
