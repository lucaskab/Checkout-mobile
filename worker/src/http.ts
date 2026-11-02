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

export const HEADERS = { "content-type": "application/json", "cache-control": "no-store" };
export const json = (status: number, body: unknown) => new Response(body === null ? null : JSON.stringify(body), { status, headers: HEADERS });
