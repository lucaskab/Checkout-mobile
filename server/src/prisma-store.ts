import { Prisma, PrismaClient } from "@prisma/client";
import { HISTORY_KEPT, type SaveRecord, type SaveSummary } from "./save.ts";
import type { Store } from "./store.ts";

const toRecord = (row: { revision: number; data: string; summary: unknown; deviceId: string; updatedAt: Date }): SaveRecord => ({
	revision: row.revision,
	data: row.data,
	summary: row.summary as SaveSummary,
	deviceId: row.deviceId,
	updatedAt: row.updatedAt,
});

/** Players and saves in Postgres (Prisma Postgres in production). */
export function prismaStore(prisma = new PrismaClient()): Store & { close(): Promise<void> } {
	return {
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
			try {
				return await prisma.$transaction(
					async (tx) => {
						// Lock the player's row so two uploads for the same player run one after the other.
						await tx.$queryRaw`SELECT id FROM players WHERE id = ${playerId} FOR UPDATE`;
						const row = await tx.cloudSave.findUnique({ where: { playerId } });
						const current = row && toRecord(row);
						if (!accept(current)) return { ok: false as const, current };
						const fields = { data: upload.data, summary: upload.summary as Prisma.InputJsonValue, deviceId: upload.deviceId, updatedAt: new Date() };
						let saved;
						if (row) {
							await tx.saveHistory.create({
								data: { playerId, revision: row.revision, data: row.data, summary: row.summary as Prisma.InputJsonValue, deviceId: row.deviceId, savedAt: row.updatedAt },
							});
							const old = await tx.saveHistory.findMany({ where: { playerId }, orderBy: { savedAt: "desc" }, skip: HISTORY_KEPT, select: { id: true } });
							if (old.length) await tx.saveHistory.deleteMany({ where: { id: { in: old.map((o) => o.id) } } });
							saved = await tx.cloudSave.update({ where: { playerId }, data: { ...fields, revision: row.revision + 1 } });
						} else saved = await tx.cloudSave.create({ data: { ...fields, playerId, revision: 1 } });
						return { ok: true as const, save: toRecord(saved) };
					},
					{ timeout: 15_000 },
				);
			} catch (error) {
				// Two first uploads at once: the other one created the save; report it as the current one.
				if (error instanceof Prisma.PrismaClientKnownRequestError && error.code === "P2002")
					return { ok: false, current: await this.getSave(playerId) };
				throw error;
			}
		},
		async deletePlayer(id) {
			await prisma.player.deleteMany({ where: { id } });
		},
	};
}
