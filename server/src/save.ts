/**
 * What a cloud save is and the rules for replacing it (no database here, so it is easy to test).
 *
 * The save is the game's whole persisted store: the "checkout.game" value, a JSON text
 * `{"state": {...}, "version": N}` (src/stores/game-store.ts, zustand persist).
 */
export const MAX_SAVE_BYTES = 2 * 1024 * 1024;
export const HISTORY_KEPT = 10;
/** A replaced save becomes a restore point only if it is at least this old (an upload every few minutes
 * would otherwise fill the history with near-copies and double the database work). */
export const HISTORY_EVERY_MS = 60 * 60_000;

export type SaveSummary = {
	level: number;
	era: string;
	coins: number;
	diamonds: number;
	day: number;
	/** The save's own format version (the game migrates older ones). */
	version: number;
};

export type SaveRecord = {
	revision: number;
	data: string;
	summary: SaveSummary;
	deviceId: string;
	updatedAt: Date;
};

const num = (value: unknown) => (typeof value === "number" && Number.isFinite(value) ? value : 0);

/** Checks the upload is a real game save and reads what the player sees about it. Null = not a save. */
export function readSave(data: unknown): SaveSummary | null {
	if (typeof data !== "string" || !data || Buffer.byteLength(data, "utf8") > MAX_SAVE_BYTES) return null;
	let parsed: unknown;
	try {
		parsed = JSON.parse(data);
	} catch {
		return null;
	}
	if (!parsed || typeof parsed !== "object") return null;
	const { state, version } = parsed as { state?: Record<string, any>; version?: unknown };
	if (!state || typeof state !== "object" || Array.isArray(state)) return null;
	return {
		level: num(state.market?.level) || 1,
		era: typeof state.era?.id === "string" ? state.era.id : "",
		coins: num(state.coins),
		diamonds: num(state.logistics?.premiumCurrency),
		day: num(state.day?.dayNumber),
		version: num(version),
	};
}

export type UploadRequest = {
	/** The revision this device last downloaded or uploaded (0 = it never had one). */
	baseRevision: number;
	data: string;
	deviceId: string;
	/** The player chose to replace the cloud progress with this device's (after a conflict): `baseRevision` is then
	 * the cloud revision they were shown, and the replaced save is always kept as a restore point. */
	force?: boolean;
};

/**
 * Whether an upload may replace the current save. A device that is behind (another phone uploaded since it
 * last synced) gets a conflict instead, so one phone never silently erases what the other one played.
 */
export function canReplace(current: SaveRecord | null, upload: UploadRequest) {
	// A forced upload (the player chose this device's progress) still names the cloud revision the player was shown:
	// if yet another phone uploaded since, the choice is asked again with the newer progress.
	return (current?.revision ?? 0) === upload.baseRevision;
}
