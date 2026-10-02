import { copyFileSync, existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import type { StateStorage } from "zustand/middleware";

// Desktop replacement for src/storage/mmkv.ts. The save lives outside the mobile app,
// so testing on desktop never touches the phone's progress.
const path = process.env.CHECKOUT_DESKTOP_SAVE ?? "checkout-desktop-save.json";

const pause = (ms: number) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);

// The save must never be lost: when Unity restarts the game quickly, the previous host may still be
// replacing the file (it is briefly missing, or locked on Windows). Wait for it instead of starting a new
// game, keep a copy of the last save that loaded, and if the file really cannot be read keep it aside
// rather than overwriting it with a fresh game.
function read(): Record<string, string> {
	for (let attempt = 0; attempt < 40; attempt++) {
		try {
			if (!existsSync(path)) {
				if (existsSync(`${path}.tmp`)) {
					pause(100);
					continue;
				}
				return {};
			}
			const values = JSON.parse(readFileSync(path, "utf8"));
			try {
				copyFileSync(path, `${path}.bak`);
			} catch {}
			return values;
		} catch {
			pause(100);
		}
	}
	try {
		copyFileSync(path, `${path}.unreadable-${Date.now()}`);
	} catch {}
	console.error(`CHECKOUT_SAVE could not read ${path}; a copy was kept aside and a new game started`);
	return {};
}

function write(values: Record<string, string>) {
	mkdirSync(dirname(path), { recursive: true });
	writeFileSync(`${path}.tmp`, JSON.stringify(values));
	// Windows refuses the rename while another process has the file open: retry for a moment.
	for (let attempt = 0; attempt < 20; attempt++) {
		try {
			renameSync(`${path}.tmp`, path);
			return;
		} catch {
			pause(50);
		}
	}
	console.error(`CHECKOUT_SAVE could not replace ${path}`);
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
