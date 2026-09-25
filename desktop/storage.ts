import { mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type { StateStorage } from "zustand/middleware";

// Desktop replacement for src/storage/mmkv.ts. The save lives outside the mobile app,
// so testing on desktop never touches the phone's progress.
const path = process.env.CHECKOUT_DESKTOP_SAVE ?? "checkout-desktop-save.json";

function read(): Record<string, string> {
	try {
		return JSON.parse(readFileSync(path, "utf8"));
	} catch {
		return {};
	}
}

function write(values: Record<string, string>) {
	mkdirSync(dirname(path), { recursive: true });
	writeFileSync(`${path}.tmp`, JSON.stringify(values));
	renameSync(`${path}.tmp`, path);
}

const values = read();

export const mmkvStorage: StateStorage = {
	getItem: (key) => values[key] ?? null,
	removeItem: (key) => {
		delete values[key];
		write(values);
	},
	setItem: (key, value) => {
		values[key] = value;
		write(values);
	},
};
