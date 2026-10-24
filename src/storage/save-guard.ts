// The player's progress must survive every update (Lucas 24/10: "todo update ... eles não percam de onde eles
// pararam"). If a save cannot be read or migrated, the store starts from a fresh game — and without this guard its
// next write would replace the real progress on disk. Once locked, the game keeps running but nothing is written
// over "checkout.game" this session, so a fixed update (or a cloud restore) still finds the save intact.
export const SAVE_KEY = "checkout.game";

let locked = false;

export function lockSave(reason: unknown) {
	if (!locked) console.error(`CHECKOUT_SAVE locked: the save could not be loaded, it is kept as it is (${String(reason)})`);
	locked = true;
}

export function unlockSave() {
	locked = false;
}

export function isSaveLocked() {
	return locked;
}

/** True when a write to `key` must be skipped to protect the save on disk. */
export function blocksWrite(key: string) {
	return locked && key === SAVE_KEY;
}
