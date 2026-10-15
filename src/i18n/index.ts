import { type Catalog, Translator } from "./translator";
import de from "./locales/de";
import en from "./locales/en";
import es from "./locales/es";
import fr from "./locales/fr";

// The game is written in Portuguese; the other languages translate its texts on the way out
// (the desktop host translates every page and snapshot before Unity draws them).

export type Language = "pt" | "en" | "es" | "fr" | "de";

/** Languages the player can pick, with their own names (shown in the language menu). */
export const languages: { id: Language; name: string }[] = [
	{ id: "pt", name: "Português" },
	{ id: "en", name: "English" },
	{ id: "es", name: "Español" },
	{ id: "fr", name: "Français" },
	{ id: "de", name: "Deutsch" },
];

/** List conjunction: "tomate, alface e banana" → "tomato, lettuce and banana". */
const conjunctions: Record<Exclude<Language, "pt">, string> = { en: " and ", es: " y ", fr: " et ", de: " und " };

const catalogs: Record<Exclude<Language, "pt">, Catalog> = { en, es, fr, de };
const translators = new Map<Language, Translator>();
let current: Language = "pt";

export function isLanguage(value: unknown): value is Language {
	return typeof value === "string" && languages.some((language) => language.id === value);
}

export function setLanguage(language: string | null | undefined) {
	current = isLanguage(language) ? language : "pt";
}

export function getLanguage(): Language {
	return current;
}

export function getCatalog(language: Language = current): Catalog {
	if (language === "pt") return {};
	return { ...catalogs[language], " e ": conjunctions[language] };
}

function translator(language: Language) {
	let found = translators.get(language);
	if (!found) {
		found = new Translator(getCatalog(language), { keepNounCase: language === "de" });
		translators.set(language, found);
	}
	return found;
}

/** The text in the current language (unchanged in Portuguese or when the catalog does not know it). */
export function t(text: string): string {
	if (current === "pt" || !text) return text;
	return translator(current).translate(text);
}

/** Keys of the desktop page messages that hold ids, routes, icons or colours — never text. */
const viewIdKeys = new Set([
	"kind", "route", "icon", "action", "args", "after", "variant", "tone", "id", "slotId", "state", "row", "art",
	"tint", "careSpot", "category", "backdrop", "style", "focus", "origin", "vehicle", "lane", "moodTone", "layout",
	"goalIcon", "eventIcon", "dayPhase", "progressRoute", "session", "gauge", "unit", "method", "sound", "image",
	"shape", "color", "targetId", "eraId", "sectorId", "shelfId", "requestId", "customerId", "status", "zone", "role",
	"incidentId", "incidentKind", "ruin", "shift", "phase", "coins", "diamonds", "productCategory", "box", "key",
]);
/** Snapshot keys Unity shows as text (names, labels); everything else in a snapshot is data. */
const snapshotTextKeys = new Set([
	"name", "productName", "shelfName", "contractTitle", "contractLabel", "message", "description", "effectLabel",
	"nextName", "label", "ruinName", "neededBy", "title", "text", "categoryLabel",
]);

function localize<T>(value: T, translate: (key: string) => boolean): T {
	const visit = (node: unknown, key: string): unknown => {
		if (typeof node === "string") return translate(key) ? t(node) : node;
		if (Array.isArray(node)) return node.map((item) => visit(item, key));
		if (node && typeof node === "object") {
			const out: Record<string, unknown> = {};
			for (const [k, v] of Object.entries(node)) out[k] = visit(v, k);
			return out;
		}
		return node;
	};
	return visit(value, "") as T;
}

/** A desktop page message in the current language. */
export function localizeView<T>(view: T): T {
	return current === "pt" ? view : localize(view, (key) => !viewIdKeys.has(key));
}

/** A simulator snapshot with its names and labels in the current language. */
export function localizeSnapshot<T>(snapshot: T): T {
	return current === "pt" ? snapshot : localize(snapshot, (key) => snapshotTextKeys.has(key));
}
