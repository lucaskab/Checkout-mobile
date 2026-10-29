import type { Connect, Socket } from "./cf.ts";

/**
 * A tiny Postgres client (wire protocol v3: TLS via STARTTLS, SCRAM-SHA-256 or cleartext password, simple queries),
 * just enough for the one-time copy of the Render database (Prisma Postgres). Written here because the Worker has no
 * npm dependencies; columns come back as raw bytes, so a 2 MB save is moved without being decoded.
 */
export type PgResult = { fields: string[]; rows: (Uint8Array | null)[][] };

const encoder = new TextEncoder();
const decoder = new TextDecoder();

class Reader {
	chunks: Uint8Array[] = [];
	size = 0;
	reader: ReadableStreamDefaultReader<Uint8Array>;
	constructor(stream: ReadableStream<Uint8Array>) {
		this.reader = stream.getReader();
	}
	async fill(n: number) {
		while (this.size < n) {
			const { value, done } = await this.reader.read();
			if (done) throw new Error("postgres closed the connection");
			if (value?.length) {
				this.chunks.push(value);
				this.size += value.length;
			}
		}
	}
	take(n: number): Uint8Array {
		const first = this.chunks[0];
		let out: Uint8Array;
		if (first.length >= n) {
			out = first.subarray(0, n);
			if (first.length === n) this.chunks.shift();
			else this.chunks[0] = first.subarray(n);
		} else {
			out = new Uint8Array(n);
			let at = 0;
			while (at < n) {
				const chunk = this.chunks[0];
				const part = Math.min(chunk.length, n - at);
				out.set(chunk.subarray(0, part), at);
				at += part;
				if (part === chunk.length) this.chunks.shift();
				else this.chunks[0] = chunk.subarray(part);
			}
		}
		this.size -= n;
		return out;
	}
	async message(): Promise<{ type: string; body: Uint8Array }> {
		await this.fill(5);
		const head = this.take(5);
		const length = new DataView(head.buffer, head.byteOffset, 5).getInt32(1);
		await this.fill(length - 4);
		return { type: String.fromCharCode(head[0]), body: this.take(length - 4) };
	}
	release() {
		this.reader.releaseLock();
	}
}

function message(type: string, ...parts: (Uint8Array | string | number)[]) {
	const bytes = parts.map((p) => (typeof p === "string" ? encoder.encode(p) : typeof p === "number" ? int32(p) : p));
	const length = 4 + bytes.reduce((n, b) => n + b.length, 0);
	const out = new Uint8Array((type ? 1 : 0) + length);
	let at = 0;
	if (type) out[at++] = type.charCodeAt(0);
	new DataView(out.buffer).setInt32(at, length);
	at += 4;
	for (const b of bytes) {
		out.set(b, at);
		at += b.length;
	}
	return out;
}
const int32 = (n: number) => {
	const b = new Uint8Array(4);
	new DataView(b.buffer).setInt32(0, n);
	return b;
};
const cstr = (s: string) => `${s}\0`;

function errorText(body: Uint8Array) {
	const fields: Record<string, string> = {};
	let at = 0;
	while (at < body.length && body[at] !== 0) {
		const code = String.fromCharCode(body[at]);
		const end = body.indexOf(0, at + 1);
		fields[code] = decoder.decode(body.subarray(at + 1, end));
		at = end + 1;
	}
	return `postgres ${fields.C ?? ""}: ${fields.M ?? "error"}`;
}

const b64 = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes));
const unb64 = (text: string) => Uint8Array.from(atob(text), (c) => c.charCodeAt(0));

async function hmac(key: Uint8Array<ArrayBuffer>, data: string) {
	const k = await crypto.subtle.importKey("raw", key, { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
	return new Uint8Array(await crypto.subtle.sign("HMAC", k, encoder.encode(data)));
}

export class PgClient {
	socket: Socket;
	reader: Reader;
	writer: WritableStreamDefaultWriter<Uint8Array>;
	constructor(socket: Socket) {
		this.socket = socket;
		this.reader = new Reader(socket.readable);
		this.writer = socket.writable.getWriter();
	}

	static async connect(url: string, connect: Connect): Promise<PgClient> {
		const u = new URL(url);
		if (u.protocol !== "postgres:" && u.protocol !== "postgresql:") throw new Error("OLD_DATABASE_URL must be the direct connection string (postgres://…)");
		const user = decodeURIComponent(u.username);
		const password = decodeURIComponent(u.password);
		const database = decodeURIComponent(u.pathname.replace(/^\//, "")) || user;
		const sslmode = u.searchParams.get("sslmode") ?? "require";
		const address = { hostname: u.hostname, port: Number(u.port || 5432) };
		let socket = connect(address, { secureTransport: sslmode === "disable" ? "off" : "starttls", allowHalfOpen: false });
		if (sslmode !== "disable") {
			// SSLRequest; "S" = the server speaks TLS from here on.
			const writer = socket.writable.getWriter();
			await writer.write(message("", 80877103));
			const reader = socket.readable.getReader();
			const { value } = await reader.read();
			reader.releaseLock();
			writer.releaseLock();
			if (value?.[0] === 83) socket = socket.startTls();
			else if (sslmode !== "prefer" && sslmode !== "allow") throw new Error("postgres refused TLS");
		}
		const client = new PgClient(socket);
		await client.startup(user, password, database);
		return client;
	}

	async send(bytes: Uint8Array) {
		await this.writer.write(bytes);
	}

	async startup(user: string, password: string, database: string) {
		await this.send(message("", 196608, cstr("user"), cstr(user), cstr("database"), cstr(database), cstr("application_name"), cstr("checkout-worker-copy"), "\0"));
		let scram: { clientFirstBare: string; nonce: string; password: string } | null = null;
		let expectedServerSignature = "";
		for (;;) {
			const { type, body } = await this.reader.message();
			if (type === "E") throw new Error(errorText(body));
			if (type === "R") {
				const view = new DataView(body.buffer, body.byteOffset, body.length);
				const kind = view.getInt32(0);
				if (kind === 0) continue;
				if (kind === 3) await this.send(message("p", cstr(password)));
				else if (kind === 10) {
					const mechanisms = decoder.decode(body.subarray(4)).split("\0");
					if (!mechanisms.includes("SCRAM-SHA-256")) throw new Error(`postgres wants ${mechanisms.join(",")}`);
					const nonce = b64(crypto.getRandomValues(new Uint8Array(18)));
					const clientFirstBare = `n=,r=${nonce}`;
					scram = { clientFirstBare, nonce, password };
					const first = encoder.encode(`n,,${clientFirstBare}`);
					await this.send(message("p", cstr("SCRAM-SHA-256"), first.length, first));
				} else if (kind === 11 && scram) {
					const serverFirst = decoder.decode(body.subarray(4));
					const attrs = Object.fromEntries(serverFirst.split(",").map((kv) => [kv[0], kv.slice(2)]));
					if (!attrs.r?.startsWith(scram.nonce)) throw new Error("postgres SCRAM nonce mismatch");
					const pbkdf = await crypto.subtle.importKey("raw", encoder.encode(scram.password), "PBKDF2", false, ["deriveBits"]);
					const salted = new Uint8Array(
						await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: unb64(attrs.s), iterations: Number(attrs.i) }, pbkdf, 256),
					);
					const clientKey = await hmac(salted, "Client Key");
					const storedKey = new Uint8Array(await crypto.subtle.digest("SHA-256", clientKey));
					const finalWithoutProof = `c=biws,r=${attrs.r}`;
					const authMessage = `${scram.clientFirstBare},${serverFirst},${finalWithoutProof}`;
					const signature = await hmac(storedKey, authMessage);
					const proof = clientKey.map((b, i) => b ^ signature[i]);
					expectedServerSignature = b64(await hmac(await hmac(salted, "Server Key"), authMessage));
					await this.send(message("p", encoder.encode(`${finalWithoutProof},p=${b64(proof)}`)));
				} else if (kind === 12) {
					const final = decoder.decode(body.subarray(4));
					if (final !== `v=${expectedServerSignature}`) throw new Error("postgres SCRAM server signature mismatch");
				} else throw new Error(`postgres auth method ${kind} not supported`);
			} else if (type === "Z") return;
			// S (parameters), K (key data), N (notices): nothing to do.
		}
	}

	/** One statement with the simple query protocol (no parameters: values must be checked by the caller). */
	async query(sql: string): Promise<PgResult> {
		await this.send(message("Q", cstr(sql)));
		const result: PgResult = { fields: [], rows: [] };
		let error: string | null = null;
		for (;;) {
			const { type, body } = await this.reader.message();
			if (type === "T") {
				const view = new DataView(body.buffer, body.byteOffset, body.length);
				const count = view.getInt16(0);
				let at = 2;
				result.fields = [];
				for (let i = 0; i < count; i++) {
					const end = body.indexOf(0, at);
					result.fields.push(decoder.decode(body.subarray(at, end)));
					at = end + 1 + 18;
				}
			} else if (type === "D") {
				const view = new DataView(body.buffer, body.byteOffset, body.length);
				const count = view.getInt16(0);
				let at = 2;
				const row: (Uint8Array | null)[] = [];
				for (let i = 0; i < count; i++) {
					const length = view.getInt32(at);
					at += 4;
					if (length < 0) row.push(null);
					else {
						row.push(body.subarray(at, at + length));
						at += length;
					}
				}
				result.rows.push(row);
			} else if (type === "E") error = errorText(body);
			else if (type === "Z") {
				if (error) throw new Error(error);
				return result;
			}
		}
	}

	/** Rows as objects of text (null stays null); `raw` columns stay bytes. */
	async objects(sql: string, raw: string[] = []): Promise<Record<string, string | Uint8Array | null>[]> {
		const { fields, rows } = await this.query(sql);
		return rows.map((row) => Object.fromEntries(fields.map((f, i) => [f, row[i] === null ? null : raw.includes(f) ? row[i] : decoder.decode(row[i] as Uint8Array)])));
	}

	async close() {
		try {
			await this.send(message("X"));
		} catch {}
		try {
			this.reader.release();
			this.writer.releaseLock();
			await this.socket.close();
		} catch {}
	}
}

/** A value for a simple query: a quoted string literal. */
export const sqlText = (value: string) => `'${value.replace(/'/g, "''")}'`;
