/** An answer with a JSON error body, thrown from anywhere in a route (the app turns it into the response). */
export class HttpError extends Error {
	status: number;
	body: Record<string, unknown>;
	constructor(status: number, body: Record<string, unknown>) {
		super(String(body.error));
		this.status = status;
		this.body = body;
	}
}

/**
 * Every JSON answer: never cached, never sniffed as something else, never framed or loaded as a page (a JSON API has
 * nothing to run: CSP "default-src 'none'"), no Referer to elsewhere, HTTPS only from now on (OWASP REST Security).
 */
export const SECURITY_HEADERS = {
	"x-content-type-options": "nosniff",
	"content-security-policy": "default-src 'none'; frame-ancestors 'none'",
	"referrer-policy": "no-referrer",
	"strict-transport-security": "max-age=31536000",
};
export const HEADERS = { "content-type": "application/json", "cache-control": "no-store", ...SECURITY_HEADERS };
/**
 * A request body of at most `max` bytes: refused (413) on a declared Content-Length above it, and also while reading
 * (a chunked body declares nothing), so an oversized body never gets buffered whole on the Worker.
 */
export async function readCapped(request: Request, max: number): Promise<Uint8Array> {
	const declared = Number(request.headers.get("content-length") ?? "0");
	if (declared > max) throw new HttpError(413, { error: "too-large" });
	if (!request.body) return new Uint8Array(0);
	const reader = request.body.getReader();
	const chunks: Uint8Array[] = [];
	let total = 0;
	for (;;) {
		const { done, value } = await reader.read();
		if (done) break;
		total += value.byteLength;
		if (total > max) {
			await reader.cancel().catch(() => {});
			throw new HttpError(413, { error: "too-large" });
		}
		chunks.push(value);
	}
	if (chunks.length === 1) return chunks[0];
	const bytes = new Uint8Array(total);
	let at = 0;
	for (const chunk of chunks) {
		bytes.set(chunk, at);
		at += chunk.byteLength;
	}
	return bytes;
}

export const json =(status: number, body: unknown) => new Response(body === null ? null : JSON.stringify(body), { status, headers: HEADERS });
