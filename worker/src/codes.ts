/**
 * Invite / friend codes: 8 characters from an alphabet without look-alikes (no 0/O, 1/I/L), stored and sent by the
 * API as the 8 characters ("7KQ2M9XA"); the game shows them as "7KQ2-M9XA". Typed codes are read case-insensitively,
 * with or without the dash or spaces.
 */
export const CODE_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ";
export const CODE_LENGTH = 8;
const VALID = new RegExp(`^[${CODE_ALPHABET}]{${CODE_LENGTH}}$`);

/** A new random code (uniform: bytes ≥ 248 are drawn again). */
export function newCode() {
	let code = "";
	while (code.length < CODE_LENGTH) {
		for (const byte of crypto.getRandomValues(new Uint8Array(16))) {
			if (byte < 248 && code.length < CODE_LENGTH) code += CODE_ALPHABET[byte % CODE_ALPHABET.length];
		}
	}
	return code;
}

/** A typed or linked code in its stored form, or null when it cannot be one. */
export function readCode(value: unknown): string | null {
	if (typeof value !== "string" || value.length > 40) return null;
	const code = value.toUpperCase().replace(/[\s-]+/g, "");
	return VALID.test(code) ? code : null;
}

/** "7KQ2M9XA" → "7KQ2-M9XA" (the landing page; the game formats its own). */
export const showCode = (code: string) => `${code.slice(0, 4)}-${code.slice(4)}`;
