import { SOCIAL } from "./limits.ts";

/**
 * What a cloud save is and the rules for replacing it — the same rules as server/src/save.ts (Render).
 *
 * The save is the game's whole persisted store: the "checkout.game" value, a JSON text `{"state": {...}, "version": N}`.
 * In R2 it is kept as a JSON *string literal* (the save text in quotes, escaped), exactly as it travels inside the
 * API's JSON: a download then streams it into the answer without re-encoding 2 MB on the Worker's CPU.
 */
export const MAX_SAVE_BYTES = 2 * 1024 * 1024;
export const HISTORY_KEPT = 10;
/** A replaced save becomes a restore point only if it is at least this old (an upload every few minutes would
 * otherwise fill the history with near-copies). */
export const HISTORY_EVERY_MS = 60 * 60_000;

export type SaveSummary = {
	level: number;
	era: string;
	coins: number;
	diamonds: number;
	day: number;
	/** The save's own format version (the game migrates older ones). */
	version: number;
	/** Total experience ever earned (state.market.totalExperience): the level boards' second key. 0 in old summaries. */
	xp: number;
};

/** A cloud save as D1 knows it (the save itself is in R2, at `key`). */
export type SaveMeta = {
	revision: number;
	summary: SaveSummary;
	deviceId: string;
	/** Milliseconds since 1970. */
	updatedAt: number;
	key: string;
	bytes: number;
};

const encoder = new TextEncoder();

/** Is the text at most 2 MB in UTF-8? Counts the bytes only when the length alone cannot tell (saves 0.7–2 MB). */
export function fitsSaveLimit(text: string) {
	if (text.length > MAX_SAVE_BYTES) return false;
	if (text.length * 3 <= MAX_SAVE_BYTES) return true;
	return encoder.encode(text).length <= MAX_SAVE_BYTES;
}

const num = (value: unknown) => (typeof value === "number" && Number.isFinite(value) ? value : 0);

/** Checks the upload is a real game save and reads what the player sees about it. Null = not a save.
 * `knownToFit`: the caller already knows it is at most MAX_SAVE_BYTES (skips counting the bytes). */
export function readSave(data: unknown, knownToFit = false): SaveSummary | null {
	if (typeof data !== "string" || !data || !(knownToFit || fitsSaveLimit(data))) return null;
	let parsed: unknown;
	try {
		parsed = JSON.parse(data);
	} catch {
		return null;
	}
	if (!parsed || typeof parsed !== "object") return null;
	// biome-ignore lint/suspicious/noExplicitAny: the game's state is read defensively, field by field
	const { state, version } = parsed as { state?: Record<string, any>; version?: unknown };
	if (!state || typeof state !== "object" || Array.isArray(state)) return null;
	return summaryOf(state, version);
}

// biome-ignore lint/suspicious/noExplicitAny: see readSave
function summaryOf(state: Record<string, any>, version: unknown): SaveSummary {
	return {
		level: num(state.market?.level) || 1,
		era: typeof state.era?.id === "string" ? state.era.id : "",
		coins: num(state.coins),
		diamonds: num(state.logistics?.premiumCurrency),
		day: num(state.day?.dayNumber),
		version: num(version),
		xp: Math.max(0, Math.floor(num(state.market?.totalExperience))),
	};
}

/** A summary read back from storage (or from the old database), always in the same shape and key order. */
export function cleanSummary(value: unknown): SaveSummary {
	const s = (value && typeof value === "object" ? value : {}) as Record<string, unknown>;
	return { level: num(s.level) || 1, era: typeof s.era === "string" ? s.era : "", coins: num(s.coins), diamonds: num(s.diamonds), day: num(s.day), version: num(s.version), xp: Math.max(0, Math.floor(num(s.xp))) };
}

/**
 * Whether an upload may replace the current save. A device that is behind (another phone uploaded since it last
 * synced) gets a conflict instead, so one phone never silently erases what the other one played. A forced upload
 * (the player chose this device's progress) still names the cloud revision the player was shown.
 */
export function canReplace(current: SaveMeta | null, baseRevision: number) {
	return (current?.revision ?? 0) === baseRevision;
}

export type Upload = {
	/** The revision this device last downloaded or uploaded (0 = it never had one). */
	baseRevision: number;
	/** The save as a JSON string literal (quotes included, UTF-8), ready to be stored. */
	literal: Uint8Array;
	summary: SaveSummary;
	deviceId: string;
	/** The player chose to replace the cloud progress with this device's (after a conflict). */
	force: boolean;
	/**
	 * The social public block (docs/social-api.md), as JSON text to store as is: undefined = not sent (older builds) or
	 * refused by checkPublic (the save itself still goes through), null = sent as null (clears it).
	 */
	public?: string | null;
	/** Set when a public block was sent but refused (why, for the log). */
	publicRefused?: string;
};

export const MAX_PUBLIC_BYTES = SOCIAL.maxPublicBytes;
export const MAX_PUBLIC_BUILDS = SOCIAL.maxPublicBuilds;

/** Checks a public block's JSON text (at most 4 KB, an object, at most 12 builds). Null = fine, else why not. */
export function checkPublic(text: string): string | null {
	if (text.length > MAX_PUBLIC_BYTES || (text.length * 3 > MAX_PUBLIC_BYTES && encoder.encode(text).length > MAX_PUBLIC_BYTES)) return "too-large";
	let value: unknown;
	try {
		value = JSON.parse(text);
	} catch {
		return "bad-json";
	}
	if (!value || typeof value !== "object" || Array.isArray(value)) return "not-an-object";
	const builds = (value as { builds?: unknown }).builds;
	if (builds !== undefined && builds !== null && (!Array.isArray(builds) || builds.length > MAX_PUBLIC_BUILDS)) return "bad-builds";
	return null;
}

/** Applies checkPublic to what was sent: the fields of Upload. */
function publicFields(text: string | null | undefined): Pick<Upload, "public" | "publicRefused"> {
	if (text === undefined) return {};
	if (text === null || text === "null") return { public: null };
	const refused = checkPublic(text);
	return refused ? { publicRefused: refused } : { public: text };
}

export class BadRequest extends Error {
	code: string;
	constructor(code: string) {
		super(code);
		this.code = code;
	}
}

// What the game sends (Unity's JsonUtility: fields in declaration order, no spaces):
// {"baseRevision":3,"data":"{\"state\":…}","deviceId":"…","force":false}
// and, from the social builds on, the public block as the last field: …,"force":false,"public":{…}}
const HEAD = /^\{"baseRevision":(0|[1-9]\d{0,8}),"data":/;
const TAIL = /,"deviceId":("(?:[^"\\\u0000-\u001f]|\\.){0,400}"),"force":(true|false)(?:,"public":(\{[^]*\}|null))?\}$/;
// How far from the end the tail can start: deviceId (≤ 400 characters, escaped) and the public block (≤ 4 KB).
const TAIL_WINDOW = 1024 + 6 * 400 + MAX_PUBLIC_BYTES;
const decoder = new TextDecoder();

/**
 * Reads PUT /v1/save's body (its bytes). The save travels as a 2 MB string inside the JSON, and the Worker's CPU time
 * is the budget: in the game's own format the save's string literal is cut straight out of the body's bytes, decoded
 * and parsed once (which also proves it is one single, well-formed string), and those same bytes are what gets stored
 * — nothing is re-encoded. Any other shape (another client, other key order) takes the general path: parse the whole
 * body, re-encode the save. Same answers either way: 400 bad-json / not-a-save / bad-upload, like the Render server.
 * The optional public block (≤ 4 KB) is checked on its own; a refused one never refuses the save.
 */
export function readUpload(bytes: Uint8Array): Upload {
	const head = HEAD.exec(decoder.decode(bytes.subarray(0, 48)));
	const tail = head ? TAIL.exec(decoder.decode(bytes.subarray(Math.max(0, bytes.length - TAIL_WINDOW)))) : null;
	if (head && tail) {
		const start = head[0].length;
		const end = bytes.length - encoder.encode(tail[0]).length;
		if (end - start >= 2 && bytes[start] === 34 && bytes[end - 1] === 34) {
			const literal = bytes.subarray(start, end);
			let data: unknown;
			try {
				data = JSON.parse(decoder.decode(literal));
			} catch {
				data = undefined;
			}
			if (typeof data === "string") {
				// The save's UTF-8 size is at most the literal's minus its quotes (escapes only make it longer).
				const summary = readSave(data, literal.length - 2 <= MAX_SAVE_BYTES);
				if (!summary) throw new BadRequest("not-a-save");
				const deviceId = (JSON.parse(tail[1]) as string).slice(0, 100);
				if (!deviceId) throw new BadRequest("bad-upload");
				return { baseRevision: Number(head[1]), literal, summary, deviceId, force: tail[2] === "true", ...publicFields(tail[3]) };
			}
		}
	}
	let body: Record<string, unknown>;
	try {
		body = JSON.parse(decoder.decode(bytes) || "{}");
		if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error();
	} catch {
		throw new BadRequest("bad-json");
	}
	const summary = readSave(body.data);
	if (!summary) throw new BadRequest("not-a-save");
	const baseRevision = typeof body.baseRevision === "number" && Number.isInteger(body.baseRevision) ? body.baseRevision : -1;
	const deviceId = typeof body.deviceId === "string" ? body.deviceId.slice(0, 100) : "";
	if (baseRevision < 0 || !deviceId) throw new BadRequest("bad-upload");
	const sent = body.public === undefined ? undefined : body.public === null ? null : JSON.stringify(body.public);
	return { baseRevision, literal: encoder.encode(JSON.stringify(body.data)), summary, deviceId, force: body.force === true, ...publicFields(sent) };
}
