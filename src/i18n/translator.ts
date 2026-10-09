// Runtime translator for the game's texts. The game is written in Portuguese; a catalog maps each
// Portuguese text (or pattern, with {0}, {1}… where the code inserts numbers and names) to its translation.
//
// Lookup order for a text: exact entry → pattern ("Faltam {0} itens") → the text split at its separators
// (" · ", line breaks, ": "…) with each piece looked up on its own. Whatever is not in the catalog stays
// in Portuguese, so a missing entry never breaks a screen.

export type Catalog = Record<string, string>;

type Pattern = {
	source: string;
	target: string;
	regex: RegExp;
	/** Longest literal piece: a cheap test before running the regex. */
	probe: string;
	weight: number;
};

const escape = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const letters = (text: string) => (text.match(/\p{L}/gu) ?? []).length;
const SEPARATORS = /(\s+·\s+|\s*\n\s*|\s+•\s+|\s+—\s+|\s+\|\s+|:\s+|;\s+|\s+›\s+|\s{2,})/;
/** Sentences first: "Chega no nível 5. Vende por 18." */
const SENTENCES = /((?<=[.!?…])\s+)/;
/** Last resort inside a piece: a list ("tomate, alface e banana"). */
const LIST = /(,\s+|\s+e\s+)/;
const MAX_CACHE = 20_000;

export class Translator {
	private exact = new Map<string, string>();
	private upper = new Map<string, string>();
	/** "tomate" inside a list → "tomato" (German keeps its capital nouns). */
	private lower = new Map<string, string>();
	private patterns: Pattern[] = [];
	private cache = new Map<string, string>();

	constructor(catalog: Catalog, options: { keepNounCase?: boolean } = {}) {
		// A text of several sentences also teaches each sentence on its own: the game often glues a
		// sentence of its own to one from the data ("{0} Esses produtos vendem mais…").
		const entries = Object.entries(catalog);
		for (const [source, target] of Object.entries(catalog)) {
			const from = source.split(SENTENCES).filter((_, i) => i % 2 === 0);
			const to = (target ?? "").split(SENTENCES).filter((_, i) => i % 2 === 0);
			if (from.length < 2 || from.length !== to.length) continue;
			from.forEach((piece, i) => {
				// "{0} Esses produtos…": the leading value is a sentence of its own.
				const lead = /^\{\d+\}\s+/.exec(piece);
				if (lead && to[i].startsWith(lead[0])) {
					piece = piece.slice(lead[0].length);
					to[i] = to[i].slice(lead[0].length);
				}
				const slots = (text: string) => (text.match(/\{\d+\}/g) ?? []).sort().join();
				if (!(piece in catalog) && slots(piece) === slots(to[i])) entries.push([piece, to[i]]);
			});
		}
		for (let [source, target] of entries) {
			if (!target) continue;
			// "{0}{1}" (a name and its suffix glued together) is one value for matching.
			for (let glued = /\{(\d+)\}\{(\d+)\}/.exec(source); glued; glued = /\{(\d+)\}\{(\d+)\}/.exec(source)) {
				const pair = glued[0];
				if (!target.includes(pair)) break;
				source = source.replace(pair, `{${glued[1]}}`);
				target = target.replace(pair, `{${glued[1]}}`);
			}
			if (/\{\d+\}/.test(source)) {
				const literal = source.replace(/\{\d+\}/g, "");
				// "{0} {1}" or "{0} de {1}" would match almost anything: patterns need real words.
				if (letters(literal) < 3) continue;
				const order: number[] = [];
				const body = source
					.split(/(\{\d+\})/)
					.map((piece) => {
						const slot = /^\{(\d+)\}$/.exec(piece);
						if (!slot) return escape(piece);
						order.push(Number(slot[1]));
						// A value never spans two sentences.
						return "((?:(?![.!?…]\\s)[\\s\\S])+?)";
					})
					.join("");
				const probe = source
					.split(/\{\d+\}/)
					.reduce((a, b) => (b.length > a.length ? b : a), "");
				// Captures are numbered in the order they appear; map them back to {n}.
				const target2 = target.replace(/\{(\d+)\}/g, (_, n) => `{#${order.indexOf(Number(n))}}`);
				this.patterns.push({ source, target: target2, regex: new RegExp(`^${body}$`), probe, weight: literal.length });
			} else {
				this.exact.set(source, target);
				const up = source.toLocaleUpperCase("pt-BR");
				if (up !== source && !this.exact.has(up)) this.upper.set(up, target.toLocaleUpperCase());
				const first = source.charAt(0);
				if (first !== first.toLowerCase()) {
					const low = first.toLowerCase() + source.slice(1);
					if (!(low in catalog))
						this.lower.set(low, options.keepNounCase ? target : target.charAt(0).toLowerCase() + target.slice(1));
				}
			}
		}
		// The most specific pattern wins.
		this.patterns.sort((a, b) => b.weight - a.weight);
	}

	translate(text: string): string {
		if (!text || !/\p{L}/u.test(text)) return text;
		const hit = this.cache.get(text);
		if (hit !== undefined) return hit;
		const result = this.find(text, 0) ?? text;
		if (this.cache.size > MAX_CACHE) this.cache.clear();
		this.cache.set(text, result);
		return result;
	}

	/** Whether the catalog knows the whole text (exact, pattern or every piece). */
	has(text: string) {
		return this.find(text, 0) !== null;
	}

	private word(text: string) {
		return this.exact.get(text) ?? this.upper.get(text) ?? this.lower.get(text);
	}

	private find(text: string, depth: number): string | null {
		const exact = this.word(text);
		if (exact !== undefined) return exact;
		// Numbers, signs and emoji around a known text ("Batata +2", "🪙 Moedas", "Nível 3!").
		const trimmed = /^([^\p{L}]*)([\s\S]*?\p{L})([^\p{L}]*)$/u.exec(text);
		if (trimmed && (trimmed[1] || trimmed[3])) {
			const inner = this.word(trimmed[2]);
			if (inner !== undefined) return trimmed[1] + inner + trimmed[3];
		}
		if (depth > 3) return null;
		for (const pattern of this.patterns) {
			if (pattern.probe && !text.includes(pattern.probe)) continue;
			const match = pattern.regex.exec(text);
			if (!match) continue;
			const values = match.slice(1).map((value) => this.find(value, depth + 1) ?? value);
			return pattern.target.replace(/\{#(-?\d+)\}/g, (_, n) => values[Number(n)] ?? "");
		}
		for (const separators of [SENTENCES, SEPARATORS, LIST]) {
			const pieces = text.split(separators);
			if (pieces.length < 2) continue;
			let changed = false;
			const out = pieces.map((piece, index) => {
				// Separators that are words (" e " → " and ") have their own catalog entry.
				if (index % 2 === 1) return this.exact.get(piece) ?? piece;
				if (!/\p{L}/u.test(piece)) return piece;
				const found = this.find(piece, depth + 1);
				if (found === null) return piece;
				changed = true;
				return found;
			});
			if (changed) return out.join("");
		}
		return null;
	}
}
