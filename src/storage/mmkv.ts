import { createMMKV } from "react-native-mmkv";
import type { StateStorage } from "zustand/middleware";

const storage = createMMKV({ id: "checkout-game" });

export const mmkvStorage: StateStorage = {
	getItem: (key) => storage.getString(key) ?? null,
	removeItem: (key) => storage.remove(key),
	setItem: (key, value) => storage.set(key, value),
};
