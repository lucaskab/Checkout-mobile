import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { connect as netConnect, type Socket as NetSocket } from "node:net";
import { DatabaseSync } from "node:sqlite";
import { Duplex } from "node:stream";
import { connect as tlsConnect } from "node:tls";
import type { Connect, D1Database, D1PreparedStatement, D1Result, R2Bucket, R2Object, R2ObjectBody, Socket } from "../src/cf.ts";

/**
 * Stand-ins for Cloudflare's D1, R2 and sockets, so the Worker's own code runs in Node's test runner (no npm
 * packages: wrangler/miniflare cannot be installed here). D1 is SQLite too, so the real schema.sql and the real SQL run.
 */
export function fakeD1(): D1Database & { sqlite: DatabaseSync; writes: number } {
	const sqlite = new DatabaseSync(":memory:");
	sqlite.exec(readFileSync(new URL("../schema.sql", import.meta.url), "utf8"));
	const run = (sql: string, values: unknown[]): D1Result => {
		const statement = sqlite.prepare(sql);
		const args = values.map((v) => (v === undefined ? null : typeof v === "boolean" ? Number(v) : v)) as (string | number | null)[];
		if (statement.columns().length) {
			const results = statement.all(...args) as Record<string, unknown>[];
			const changes = Number((sqlite.prepare("SELECT changes() AS c").get() as { c: number }).c);
			const isWrite = /^\s*(INSERT|UPDATE|DELETE)/i.test(sql);
			return { results: results.map((r) => ({ ...r })), success: true, meta: { changes: isWrite ? changes : 0, last_row_id: 0 } };
		}
		const info = statement.run(...args);
		db.writes++;
		return { results: [], success: true, meta: { changes: Number(info.changes), last_row_id: Number(info.lastInsertRowid) } };
	};
	const statement = (sql: string, values: unknown[] = []): D1PreparedStatement & { sql: string; values: unknown[] } => ({
		sql,
		values,
		bind: (...more: unknown[]) => statement(sql, more),
		first: async <T>() => (run(sql, values).results[0] as T) ?? null,
		all: async <T>() => run(sql, values) as D1Result<T>,
		run: async () => run(sql, values),
	});
	const db = {
		sqlite,
		writes: 0,
		prepare: (sql: string) => statement(sql),
		async batch<T>(statements: D1PreparedStatement[]) {
			sqlite.exec("BEGIN");
			try {
				const results = (statements as unknown as { sql: string; values: unknown[] }[]).map((s) => run(s.sql, s.values) as D1Result<T>);
				sqlite.exec("COMMIT");
				return results;
			} catch (error) {
				sqlite.exec("ROLLBACK");
				throw error;
			}
		},
	};
	return db;
}

export function fakeR2(): R2Bucket & { objects: Map<string, Uint8Array>; puts: number } {
	const objects = new Map<string, Uint8Array>();
	const describe = (key: string, bytes: Uint8Array): R2Object => ({ key, size: bytes.length, etag: createHash("md5").update(bytes).digest("hex") });
	return {
		objects,
		puts: 0,
		async put(key, value) {
			this.puts++;
			const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value instanceof Uint8Array ? value.slice() : new Uint8Array(value.slice(0));
			objects.set(key, bytes);
			return describe(key, bytes);
		},
		async get(key) {
			const bytes = objects.get(key);
			if (!bytes) return null;
			return { ...describe(key, bytes), arrayBuffer: async () => bytes.slice().buffer } as R2ObjectBody;
		},
		async head(key) {
			const bytes = objects.get(key);
			return bytes ? describe(key, bytes) : null;
		},
		async delete(keys) {
			for (const key of Array.isArray(keys) ? keys : [keys]) objects.delete(key);
		},
	};
}

/** cloudflare:sockets' connect() over Node's net/tls (STARTTLS included, any certificate: local tests only). */
export const nodeConnect: Connect = (address) => wrap(netConnect(address.port, address.hostname));

function wrap(socket: NetSocket | Duplex): Socket {
	const readable = new ReadableStream<Uint8Array>({
		start(controller) {
			socket.on("data", (chunk: Buffer) => controller.enqueue(new Uint8Array(chunk)));
			socket.on("end", () => {
				try {
					controller.close();
				} catch {}
			});
			socket.on("error", (error) => {
				try {
					controller.error(error);
				} catch {}
			});
		},
	});
	const writable = new WritableStream<Uint8Array>({
		write: (chunk) => new Promise<void>((done, fail) => socket.write(chunk, (error) => (error ? fail(error) : done()))),
	});
	return {
		readable,
		writable,
		startTls() {
			socket.removeAllListeners("data");
			socket.removeAllListeners("end");
			return wrap(tlsConnect({ socket: socket as NetSocket, rejectUnauthorized: false }));
		},
		close() {
			socket.destroy();
		},
	};
}
