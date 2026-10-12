import { HISTORY_EVERY_MS, HISTORY_KEPT, type SaveRecord, type SaveSummary } from "./save.ts";

export type PlayerRecord = { id: string; googleSub: string; email: string | null; name: string | null };

/** Where players and saves live: Postgres through Prisma in production (prisma-store.ts), memory in tests. */
export interface Store {
	signIn(googleSub: string, email: string | null, name: string | null): Promise<PlayerRecord>;
	getPlayer(id: string): Promise<PlayerRecord | null>;
	getSave(playerId: string): Promise<SaveRecord | null>;
	/**
	 * Replaces the save when `accept(current)` says so — atomically, so two phones uploading at the same time
	 * cannot both win. The replaced save becomes a restore point when it is old enough (HISTORY_EVERY_MS).
	 * Returns the new save, or the current one on a refusal.
	 */
	replaceSave(
		playerId: string,
		upload: { data: string; summary: SaveSummary; deviceId: string; keepReplaced?: boolean },
		accept: (current: SaveRecord | null) => boolean,
	): Promise<{ ok: true; save: SaveRecord } | { ok: false; current: SaveRecord | null }>;
	deletePlayer(id: string): Promise<void>;
}

export function memoryStore(clock = () => new Date(), historyEveryMs = HISTORY_EVERY_MS): Store & { history: Map<string, SaveRecord[]> } {
	const players = new Map<string, PlayerRecord>();
	const saves = new Map<string, SaveRecord>();
	const history = new Map<string, SaveRecord[]>();
	let next = 0;
	return {
		history,
		async signIn(googleSub, email, name) {
			let player = [...players.values()].find((p) => p.googleSub === googleSub);
			if (!player) {
				player = { id: `player-${++next}`, googleSub, email, name };
				players.set(player.id, player);
			} else Object.assign(player, { email, name });
			return { ...player };
		},
		async getPlayer(id) {
			const player = players.get(id);
			return player ? { ...player } : null;
		},
		async getSave(playerId) {
			const save = saves.get(playerId);
			return save ? { ...save } : null;
		},
		async replaceSave(playerId, upload, accept) {
			const current = saves.get(playerId) ?? null;
			if (!accept(current)) return { ok: false, current };
			if (current && (upload.keepReplaced || clock().getTime() - current.updatedAt.getTime() >= historyEveryMs))
				history.set(playerId, [current, ...(history.get(playerId) ?? [])].slice(0, HISTORY_KEPT));
			const save: SaveRecord = { data: upload.data, summary: upload.summary, deviceId: upload.deviceId, revision: (current?.revision ?? 0) + 1, updatedAt: clock() };
			saves.set(playerId, save);
			return { ok: true, save: { ...save } };
		},
		async deletePlayer(id) {
			players.delete(id);
			saves.delete(id);
			history.delete(id);
		},
	};
}
