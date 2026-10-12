import { Prisma, PrismaClient } from "@prisma/client";
import { HISTORY_EVERY_MS, HISTORY_KEPT, type SaveRecord, type SaveSummary } from "./save.ts";
import type { Store } from "./store.ts";

const toRecord = (row: { revision: number; data: string; summary: unknown; deviceId: string; updatedAt: Date }): SaveRecord => ({
	revision: row.revision,
	data: row.data,
	summary: row.summary as SaveSummary,
	deviceId: row.deviceId,
	updatedAt: row.updatedAt,
});

/**
 * Players and saves in Postgres (Prisma Postgres in production). Prisma Postgres bills per operation, so a
 * normal upload costs two: read the current save, then replace it only if it is still that revision (a
 * conditional update — two phones uploading at once cannot both win). A restore point adds two more, at most
 * once an hour.
 */
export function prismaStore(prisma = new PrismaClient(), historyEveryMs = HISTORY_EVERY_MS): Store & { close(): Promise<void> } {
	const store: Store & { close(): Promise<void> } = {
		close: () => prisma.$disconnect(),
		async signIn(googleSub, email, name) {
			const player = await prisma.player.upsert({
				where: { googleSub },
				create: { googleSub, email, name },
				update: { email, name, lastSeen: new Date() },
			});
			return { id: player.id, googleSub: player.googleSub, email: player.email, name: player.name };
		},
		async getPlayer(id) {
			const player = await prisma.player.findUnique({ where: { id } });
			return player && { id: player.id, googleSub: player.googleSub, email: player.email, name: player.name };
		},
		async getSave(playerId) {
			const save = await prisma.cloudSave.findUnique({ where: { playerId } });
			return save && toRecord(save);
		},
		async replaceSave(playerId, upload, accept) {
			const current = await store.getSave(playerId);
			if (!accept(current)) return { ok: false, current };
			const updatedAt = new Date();
			const fields = { data: upload.data, summary: upload.summary as Prisma.InputJsonValue, deviceId: upload.deviceId, updatedAt };
			if (!current) {
				try {
					const created = await prisma.cloudSave.create({ data: { ...fields, playerId, revision: 1 } });
					return { ok: true, save: toRecord(created) };
				} catch (error) {
					// Another phone created the first save at the same moment.
					if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002")
						return { ok: false, current: await store.getSave(playerId) };
					throw error;
				}
			}
			const { count } = await prisma.cloudSave.updateMany({
				where: { playerId, revision: current.revision },
				data: { ...fields, revision: current.revision + 1 },
			});
			if (count === 0) return { ok: false, current: await store.getSave(playerId) };
			// The replaced save becomes a restore point (after the update won, so a losing upload leaves no copy).
			if (upload.keepReplaced || updatedAt.getTime() - current.updatedAt.getTime() >= historyEveryMs) {
				await prisma.saveHistory.create({
					data: { playerId, revision: current.revision, data: current.data, summary: current.summary as Prisma.InputJsonValue, deviceId: current.deviceId, savedAt: current.updatedAt },
				});
				const old = await prisma.saveHistory.findMany({ where: { playerId }, orderBy: { savedAt: "desc" }, skip: HISTORY_KEPT, select: { id: true } });
				if (old.length) await prisma.saveHistory.deleteMany({ where: { id: { in: old.map((o) => o.id) } } });
			}
			return { ok: true, save: { data: upload.data, summary: upload.summary, deviceId: upload.deviceId, revision: current.revision + 1, updatedAt } };
		},
		async deletePlayer(id) {
			await prisma.player.deleteMany({ where: { id } });
		},
	};
	return store;
}
