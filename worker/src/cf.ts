/**
 * The parts of Cloudflare's runtime this Worker uses (D1, R2, sockets), typed here so the Worker needs no npm
 * package at all (no @cloudflare/workers-types, no wrangler at runtime). The tests run the same code in Node with
 * stand-ins (test/fakes.ts: D1 over node:sqlite, R2 in memory, sockets over node:net).
 */
export type D1Meta = { changes: number; last_row_id: number; rows_read?: number; rows_written?: number };
export type D1Result<T = Row> = { results: T[]; success: boolean; meta: D1Meta };
export type Row = Record<string, unknown>;

export interface D1PreparedStatement {
	bind(...values: unknown[]): D1PreparedStatement;
	first<T = Row>(): Promise<T | null>;
	all<T = Row>(): Promise<D1Result<T>>;
	run(): Promise<D1Result>;
}

export interface D1Database {
	prepare(sql: string): D1PreparedStatement;
	/** Runs the statements in order, in one transaction and one round trip. */
	batch<T = Row>(statements: D1PreparedStatement[]): Promise<D1Result<T>[]>;
}

export interface R2Object {
	key: string;
	size: number;
	/** MD5 of the content (hex) for objects uploaded in one piece, which is all this Worker writes. */
	etag: string;
}

export interface R2ObjectBody extends R2Object {
	arrayBuffer(): Promise<ArrayBuffer>;
}

export interface R2Bucket {
	get(key: string): Promise<R2ObjectBody | null>;
	head(key: string): Promise<R2Object | null>;
	put(key: string, value: string | ArrayBuffer | Uint8Array, options?: { httpMetadata?: { contentType?: string } }): Promise<R2Object | null>;
	delete(keys: string | string[]): Promise<void>;
}

/** cloudflare:sockets (TCP), used only by the one-time copy from the old Postgres database. */
export type Socket = {
	readable: ReadableStream<Uint8Array>;
	writable: WritableStream<Uint8Array>;
	opened?: Promise<unknown>;
	startTls(): Socket;
	close(): Promise<void> | void;
};
export type Connect = (address: { hostname: string; port: number }, options: { secureTransport: "off" | "starttls"; allowHalfOpen?: boolean }) => Socket;

/** The Worker's settings (Workers › checkout-server › Settings › Variables and Secrets) and storage. */
export type Env = {
	DB: D1Database;
	SAVES: R2Bucket;
	SESSION_SECRET?: string;
	GOOGLE_CLIENT_IDS?: string;
	GOOGLE_DESKTOP_CLIENT_ID?: string;
	GOOGLE_DESKTOP_CLIENT_SECRET?: string;
	GOOGLE_IOS_CLIENT_ID?: string;
	APPLE_BUNDLE_IDS?: string;
	APPLE_TEAM_ID?: string;
	APPLE_KEY_ID?: string;
	APPLE_PRIVATE_KEY?: string;
	/** Temporary, for the move from Render: the old Prisma Postgres connection string (postgres://…). */
	OLD_DATABASE_URL?: string;
	/** Temporary, public (not a secret): the key that checks the signed tokens of /admin/* (copy, CPU benchmark). */
	ADMIN_PUBLIC_KEY?: string;
};
