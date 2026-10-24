import type { StateStorage } from "zustand/middleware";
import { blocksWrite, lockSave } from "@/storage/save-guard";

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
		if (values && typeof values === "object") return values;
		lockSave("the save file is not an object");
		return {};
	} catch (error) {
		// A save that exists but cannot be read is never overwritten by the new game (save-guard.ts).
		lockSave(error);
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
		if (blocksWrite(key)) return;
		delete values[key];
		later();
	},
	setItem: (key, value) => {
		if (blocksWrite(key)) return;
		values[key] = value;
		later();
	},
};
