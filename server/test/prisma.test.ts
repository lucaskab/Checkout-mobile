import assert from "node:assert/strict";
import { after, describe, test } from "node:test";

// Runs against a real Postgres when DATABASE_URL is set (GitHub Actions: .github/workflows/server.yml).
const enabled = !!process.env.DATABASE_URL;
const save = (diamonds: number) =>
	JSON.stringify({ state: { coins: 1, era: { id: "mesinha" }, market: { level: 2 }, logistics: { premiumCurrency: diamonds }, day: { dayNumber: 1 } }, version: 45 });
const summary = (diamonds: number) => ({ level: 2, era: "mesinha", coins: 1, diamonds, day: 1, version: 45 });

describe("Prisma store (Postgres)", { skip: !enabled && "no DATABASE_URL" }, async () => {
	const { prismaStore } = await import("../src/prisma-store.ts");
	const store = prismaStore(undefined, 0);
	after(() => store.close());
	const sub = `g-${Date.now()}`;

	test("sign in creates once and updates the profile", async () => {
		const a = await store.signIn("google", sub, "a@x.com", "A");
		const b = await store.signIn("google", sub, "b@x.com", "B");
		assert.equal(a.id, b.id);
		assert.equal((await store.getPlayer(a.id))?.email, "b@x.com");
	});

	test("Apple accounts: their own id, the name kept from the first login, the refresh token stored", async () => {
		const appleSub = `a-${Date.now()}`;
		const first = await store.signIn("apple", appleSub, "x@privaterelay.appleid.com", "Bia");
		const again = await store.signIn("apple", appleSub, null, null);
		assert.equal(first.id, again.id);
		assert.equal(again.provider, "apple");
		assert.equal(again.name, "Bia");
		assert.equal(again.email, "x@privaterelay.appleid.com");
		await store.setAppleRefresh(first.id, "r-1");
		assert.equal((await store.getPlayer(first.id))?.appleRefresh, "r-1");
		assert.notEqual((await store.signIn("google", appleSub, null, null)).id, first.id, "a Google id never matches an Apple one");
		await store.deletePlayer(first.id);
	});

	test("replace, conflict, history (newest 10), concurrent uploads, delete", async () => {
		const player = await store.signIn("google", sub, null, null);
		const at = (revision: number) => (current: { revision: number } | null) => (current?.revision ?? 0) === revision;
		const first = await store.replaceSave(player.id, { data: save(1), summary: summary(1), deviceId: "a" }, at(0));
		assert.ok(first.ok);
		assert.equal(first.ok && first.save.revision, 1);
		const refused = await store.replaceSave(player.id, { data: save(2), summary: summary(2), deviceId: "b" }, at(0));
		assert.equal(refused.ok, false);
		assert.equal(!refused.ok && refused.current?.revision, 1);
		for (let r = 1; r <= 12; r++) await store.replaceSave(player.id, { data: save(r + 1), summary: summary(r + 1), deviceId: "a" }, at(r));
		const current = await store.getSave(player.id);
		assert.equal(current?.revision, 13);
		assert.equal(current?.summary.diamonds, 13);
		// Two phones upload on top of the same revision at once: exactly one wins.
		const both = await Promise.all([
			store.replaceSave(player.id, { data: save(100), summary: summary(100), deviceId: "a" }, at(13)),
			store.replaceSave(player.id, { data: save(200), summary: summary(200), deviceId: "b" }, at(13)),
		]);
		assert.equal(both.filter((r) => r.ok).length, 1);
		assert.equal((await store.getSave(player.id))?.revision, 14);
		const { PrismaClient } = await import("@prisma/client");
		const prisma = new PrismaClient();
		assert.equal(await prisma.saveHistory.count({ where: { playerId: player.id } }), 10);
		// A forced replace keeps the replaced save even when it is recent.
		const keepStore = prismaStore(prisma, 60 * 60_000);
		const before = await prisma.saveHistory.count({ where: { playerId: player.id } });
		const forced = await keepStore.replaceSave(player.id, { data: save(300), summary: summary(300), deviceId: "a", keepReplaced: true }, at(14));
		assert.ok(forced.ok);
		assert.equal(await prisma.saveHistory.count({ where: { playerId: player.id } }), Math.min(10, before + 1));
		await store.deletePlayer(player.id);
		assert.equal(await store.getSave(player.id), null);
		assert.equal(await prisma.saveHistory.count({ where: { playerId: player.id } }), 0);
		await prisma.$disconnect();
	});
});
