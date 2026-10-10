// node:readline for the embedded build: the host's line handler receives the messages Unity sends through
// __checkoutReceive (one JSON message per call) instead of lines on stdin.
type Handler = (line: string) => void;
export function createInterface(_options?: unknown) {
	return {
		on(event: string, fn: Handler) {
			if (event === "line") (globalThis as Record<string, unknown>).__checkoutReceive = (line: string) => fn(line);
			return this;
		},
	};
}
