import { createMMKV } from "react-native-mmkv";
import type { StateStorage } from "zustand/middleware";
import { blocksWrite } from "./save-guard";

const storage = createMMKV({ id: "checkout-game" });

export const mmkvStorage: StateStorage = {
	getItem: (key) => storage.getString(key) ?? null,
	removeItem: (key) => {
		if (!blocksWrite(key)) storage.remove(key);
	},
	setItem: (key, value) => {
		if (!blocksWrite(key)) storage.set(key, value);
	},
};
