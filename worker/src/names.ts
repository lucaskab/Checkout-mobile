import { SOCIAL } from "./limits.ts";

/**
 * Market names (the only text players write in social v1): 3–20 characters — letters of any script, digits, space,
 * `'`, `-`, `&`, `.` — and not on the profanity list (pt, en, es, fr, de).
 *
 * The filter compares a normalised copy: lower case, accents stripped, ß → ss, digit and Cyrillic/Greek look-alikes
 * mapped to Latin letters (0→o, 1→i, 3→e, 4→a, 5→s, 7→t, @→a, $→s, а→a…). A word's letters may be repeated
 * ("puuuta") and the spelling may be split letter by letter ("f u c k", "p.u.t.a"). WORDS match whole words only
 * (so "computador", "Barcelona" or "Scunthorpe" pass); WORST also match inside other words ("MercadoDoCaralho").
 * Words whose letters are doubled keep at least the double ("faggot" needs "gg", so the German "Fagott" passes;
 * "nigger" needs "gg", so "Niger" passes). Runs a few small regexes on ≤ 20 characters: microseconds.
 */
const WORDS = [
	// pt
	"puta", "puto", "putinha", "putona", "putaria", "puteiro", "cu", "cuzao", "cuzinho", "caralho", "karalho", "krl", "porra", "merda",
	"bosta", "foda", "fodase", "foder", "fodido", "fodida", "buceta", "boceta", "xoxota", "xereca", "xota", "piroca", "punheta",
	"punheteiro", "boquete", "siririca", "arrombado", "arrombada", "viado", "sapatao", "traveco", "corno", "otario", "babaca",
	"retardado", "crioulo", "vagabunda", "quenga", "vadia", "prostituta", "estupro", "estuprador", "pedofilo", "nazista", "escroto",
	"pqp", "vsf", "tnc", "fdp", "filhodaputa", "filhadaputa",
	// en
	"fuck", "fucker", "fucking", "fucked", "fuk", "fck", "motherfucker", "shit", "shitty", "bullshit", "shithead", "cunt", "dickhead",
	"cocksucker", "pussy", "bitch", "bastard", "asshole", "arsehole", "arse", "whore", "slut", "nigger", "nigga", "faggot", "fag",
	"retard", "retarded", "wanker", "twat", "bollocks", "porn", "porno", "sex", "rape", "rapist", "pedo", "pedophile", "paedophile",
	"nazi", "hitler", "chink", "spic", "kike", "coon", "paki", "tranny", "dyke", "jizz", "cum", "dildo", "tits", "boobs", "penis",
	"vagina", "anal", "milf", "wtf", "stfu",
	// es
	"mierda", "joder", "jodido", "jodida", "cono", "cabron", "cabrona", "pendejo", "pendeja", "gilipollas", "maricon", "marica",
	"polla", "verga", "chingar", "chingada", "chingado", "chinga", "culero", "culo", "mamon", "zorra", "hijoputa", "hijodeputa",
	"follar", "ojete", "panocha", "carajo", "cojones", "malparido", "malparida", "gonorrea", "sudaca", "negrata", "putita", "puton",
	"putero", "pajero",
	// fr
	"merde", "putain", "pute", "salope", "connard", "connasse", "conne", "encule", "enculer", "nique", "niquer", "ntm", "batard",
	"chier", "foutre", "pd", "pede", "tapette", "bougnoule", "negre", "branleur", "branlette", "trouduc", "couille", "enfoire",
	"petasse", "poufiasse",
	// de
	"scheisse", "scheiss", "arschloch", "arsch", "arschgeige", "fotze", "votze", "ficken", "ficker", "fick", "hurensohn", "hure",
	"wichser", "wixer", "schlampe", "missgeburt", "spast", "spasti", "schwuchtel", "mongo", "kanake", "neger", "nutte", "pimmel",
	"titten", "drecksau", "judensau",
];

const WORST = [
	"fuck", "nigger", "nigga", "faggot", "cocksuck", "asshole", "whore", "caralho", "buceta", "xoxota", "arrombad", "fodase",
	"punhet", "filhodaput", "filhadaput", "filhodeput", "hijoput", "hijodeput", "gilipoll", "pendej", "chingad", "maricon",
	"connard", "connasse", "encule", "putain", "hurensohn", "wichser", "arschloch", "missgeburt", "schlampe", "schwuchtel",
	"scheiss", "hitler", "pedofil", "pedophil", "estupr",
];

// "faggot" → "f+a+g{2,}o+t+": every letter may repeat, doubled letters stay at least doubled.
const pattern = (word: string) => word.replace(/(.)\1*/g, (run, letter: string) => (run.length === 1 ? `${letter}+` : `${letter}{${run.length},}`));
const WORD_RE = new RegExp(`^(?:${WORDS.map((w) => pattern(w) + (w.length >= 3 ? "s?" : "")).join("|")})$`);
const WORST_RE = new RegExp(WORST.map(pattern).join("|"));

const LOOKALIKES: Record<string, string> = {
	"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", $: "s",
	// Cyrillic and Greek letters that look Latin
	а: "a", в: "b", е: "e", ё: "e", і: "i", к: "k", м: "m", н: "h", о: "o", р: "p", с: "c", т: "t", у: "y", х: "x",
	α: "a", ε: "e", ι: "i", κ: "k", ν: "v", ο: "o", ρ: "p", τ: "t", υ: "u", χ: "x",
	// Latin letters NFD does not split
	æ: "ae", œ: "oe", ø: "o", ł: "l", đ: "d", ð: "d", þ: "th", ı: "i",
};
const LOOKALIKE_RE = new RegExp(`[${Object.keys(LOOKALIKES).join("").replace(/[$]/g, "\\$")}]`, "g");

/** The copy the filter compares: lower case, no accents, look-alikes mapped. */
export function normalizeForFilter(text: string) {
	return text
		.toLowerCase()
		.replace(/ß/g, "ss")
		.normalize("NFD")
		.replace(/\p{M}+/gu, "")
		.replace(LOOKALIKE_RE, (c) => LOOKALIKES[c]);
}

/** Whether the name contains a word of the profanity list (see the top of the file). */
export function isProfane(name: string) {
	const tokens = normalizeForFilter(name)
		.split(/[^\p{L}\p{N}]+/u)
		.filter(Boolean);
	// "f u c k" / "p.u.t.a": runs of single characters are read as one word too.
	const words = [...tokens];
	let run = "";
	for (const token of [...tokens, ""]) {
		if (token.length === 1) run += token;
		else {
			if (run.length > 1) words.push(run);
			run = "";
		}
	}
	const squashed = tokens.join("");
	words.push(squashed);
	return words.some((w) => WORD_RE.test(w)) || WORST_RE.test(squashed);
}

const ALLOWED = /^[\p{L}\p{M}\p{Nd} '\-&.]+$/u;
const HAS_LETTER_OR_DIGIT = /[\p{L}\p{Nd}]/u;

/** The name as stored: NFC, trimmed, inner spaces collapsed. Null when it is not a string. */
export function cleanName(value: unknown): string | null {
	if (typeof value !== "string" || value.length > 200) return null;
	return value.normalize("NFC").replace(/\s+/g, " ").trim();
}

/** Whether a cleaned name may be a market name. */
export function isNameAllowed(name: string) {
	const chars = [...name].length;
	if (chars < SOCIAL.nameMinChars || chars > SOCIAL.nameMaxChars) return false;
	if (!ALLOWED.test(name) || !HAS_LETTER_OR_DIGIT.test(name)) return false;
	return !isProfane(name);
}

/** Two spellings of the same name ("Zé Mercado" / "ze  mercado"): a hidden name is not "changed" by them. */
export const sameName = (a: string, b: string) => normalizeForFilter(a).replace(/[^\p{L}\p{N}]+/gu, "") === normalizeForFilter(b).replace(/[^\p{L}\p{N}]+/gu, "");
