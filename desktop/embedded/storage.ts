import type { StateStorage } from "zustand/middleware";

// The save of the embedded build (iPhone): one JSON file in the app's documents, read and written by the native
// plugin (Assets/Plugins/iOS/CheckoutJS.mm). Writes are gathered and flushed at most every 2 s, and right away
// when Unity calls __checkoutFlush (the app goes to the background or quits).
type Native = { save(text: string): void; load(): string };
const native = (globalThis as unknown as { __native: Native }).__native;

function read(): Record<string, string> {
	try {
		const text = native.load();
		if (!text) return {};
		const values = JSON.parse(text);
		return values && typeof values === "object" ? values : {};
	} catch (error) {
		console.error("CHECKOUT_SAVE could not read the save; a new game starts", error);
		return {};
	}
}

const values = read();
let dirty = false,
	timer: ReturnType<typeof setTimeout> | null = null;

function flush() {
	if (timer !== null) clearTimeout(timer);
	timer = null;
	if (!dirty) return;
	dirty = false;
	native.save(JSON.stringify(values));
}
function later() {
	dirty = true;
	if (timer === null) timer = setTimeout(flush, 2_000);
}
(globalThis as Record<string, unknown>).__checkoutFlush = flush;

export const mmkvStorage: StateStorage = {
	getItem: (key) => values[key] ?? null,
	removeItem: (key) => {
		delete values[key];
		later();
	},
	setItem: (key, value) => {
		values[key] = value;
		later();
	},
};
