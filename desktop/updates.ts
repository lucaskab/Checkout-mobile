import { isNewerVersion } from "@/services/app-prompts";

/**
 * A new version in the store (Lucas 10/11: "às vezes a pessoa fica jogando uma versão muito antiga do jogo, não
 * atualiza e aí está perdendo muito conteúdo"). Unity asks the store once a session (CheckoutUpdates.cs: the App
 * Store lookup on the iPhone, Google Play's in-app updates API on Android) and tells the host:
 *   { kind: "update", latest: "1.0.3", current: "1.0.2" }      (iPhone: the store's version name)
 *   { kind: "update", latest: "code 21", current: "1.0.2", available: true }   (Android: only the version code)
 * The host opens the "atualizar" card once a session on the main screen (never over a window, the tutorial or a
 * celebration); "Agora não" waits 2 days for that same version (snoozeAppUpdate, src/services/app-prompts.ts).
 * Nothing is forced: the player always keeps playing.
 */
export const updateStore = {
	latest: "",
	current: "",
	available: false,
	shown: false,
};

export type UpdateUnityMessage = { kind: "update"; latest?: unknown; current?: unknown; available?: unknown };

export function applyUpdateMessage(message: UpdateUnityMessage) {
	const latest = typeof message.latest === "string" ? message.latest.slice(0, 32) : "";
	const current = typeof message.current === "string" ? message.current.slice(0, 32) : "";
	if (!latest) return false;
	updateStore.latest = latest;
	updateStore.current = current;
	// Android only knows the store's version code is higher (Unity compared it); the iPhone compares names here.
	updateStore.available = message.available === true || isNewerVersion(latest, current);
	return updateStore.available;
}

/** The version name to show ("" on Android, where only the code is known). */
export function updateVersionLabel() {
	return /^\d+(\.\d+)*$/.test(updateStore.latest) ? updateStore.latest : "";
}

export function resetUpdateStore() {
	updateStore.latest = "";
	updateStore.current = "";
	updateStore.available = false;
	updateStore.shown = false;
}
