// Runs first in the embedded build (desktop/embedded/entry.ts): the game host normally runs under Node or Bun as a
// separate program next to Unity. On the iPhone it runs inside the Unity player, in the system JavaScript engine
// (JavaScriptCore); on Android, in QuickJS compiled into the player. Both have the language but none of Node's or
// the browser's extras. This file gives the host the
// few it uses: console, timers (driven by Unity calling __checkoutTick every frame), and a `process` whose stdout
// goes to Unity (one JSON message per line) and whose env carries the language picked on the start screen.
type Native = {
	send(line: string): void;
	log(text: string): void;
	save(text: string): void;
	load(): string;
	lang: string;
	/** "android" (QuickJS, Assets/Plugins/Android/QuickJS/CheckoutJS.c); the iPhone plugin does not set it. */
	platform?: string;
};
const g = globalThis as Record<string, unknown> & { __native: Native };
const native = g.__native;

// ------------------------------------------------------------------ numbers and sorting in pt-BR
// The game formats every number with toLocaleString("pt-BR") and sorts names with localeCompare(…, "pt-BR").
// JavaScriptCore (iPhone) has Intl and does it natively; QuickJS (Android) has no Intl, so its toLocaleString
// ignores the locale ("130370" instead of "130.370"). This stands in for the two calls, same output as Intl.
if (typeof g.Intl === "undefined") {
	type Digits = { minimumFractionDigits?: number; maximumFractionDigits?: number };
	Number.prototype.toLocaleString = function (this: number, _locales?: unknown, options?: Digits) {
		return formatPtBr(Number(this), options);
	};
	String.prototype.localeCompare = function (this: string, that: unknown) {
		return comparePtBr(String(this), String(that));
	};
}
export function formatPtBr(value: number, options?: { minimumFractionDigits?: number; maximumFractionDigits?: number }) {
	if (!Number.isFinite(value)) return String(value);
	const min = Math.max(0, Math.min(20, options?.minimumFractionDigits ?? 0));
	const max = Math.max(min, Math.min(20, options?.maximumFractionDigits ?? Math.max(min, 3)));
	const fixed = Math.abs(value).toFixed(max);
	if (fixed.includes("e")) return String(value);
	const [whole, decimals = ""] = fixed.split(".");
	let fraction = decimals.replace(/0+$/, "");
	while (fraction.length < min) fraction += "0";
	const sign = value < 0 && Number(fixed) !== 0 ? "-" : "";
	return sign + whole.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + (fraction ? "," + fraction : "");
}
// Like a collator: letters first (accents and case ignored), then accents (plain first), then case (lowercase first).
export function comparePtBr(a: string, b: string) {
	const base = (s: string) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
	const order = (x: string, y: string) => (x < y ? -1 : x > y ? 1 : 0);
	return (
		order(base(a), base(b)) ||
		order(a.normalize("NFD").toLowerCase(), b.normalize("NFD").toLowerCase()) ||
		-order(a.normalize("NFD"), b.normalize("NFD"))
	);
}

if (typeof g.console === "undefined") {
	const log = (...parts: unknown[]) => native.log(parts.map((p) => (typeof p === "string" ? p : safe(p))).join(" "));
	g.console = { log, info: log, warn: log, error: log, debug: log };
}
function safe(value: unknown) {
	try {
		return value instanceof Error ? `${value.message}\n${value.stack ?? ""}` : JSON.stringify(value);
	} catch {
		return String(value);
	}
}

// ------------------------------------------------------------------ timers
type Timer = { id: number; at: number; every: number; fn: (...args: unknown[]) => void; args: unknown[] };
if (typeof g.setTimeout === "undefined") {
	const timers = new Map<number, Timer>();
	let nextId = 1;
	const add = (fn: Timer["fn"], ms: unknown, args: unknown[], repeat: boolean) => {
		const wait = Math.max(0, Number(ms) || 0);
		const id = nextId++;
		timers.set(id, { id, at: Date.now() + wait, every: repeat ? Math.max(1, wait) : 0, fn, args });
		return id;
	};
	g.setTimeout = (fn: Timer["fn"], ms?: number, ...args: unknown[]) => add(fn, ms, args, false);
	g.setInterval = (fn: Timer["fn"], ms?: number, ...args: unknown[]) => add(fn, ms, args, true);
	g.clearTimeout = g.clearInterval = (id: number) => void timers.delete(id);
	// Unity calls this every frame: due timers run in time order; an interval that fell behind (the app was in
	// the background) runs once and is rescheduled from now, like a browser tab coming back.
	g.__checkoutTick = () => {
		const now = Date.now();
		const due = [...timers.values()].filter((t) => t.at <= now).sort((a, b) => a.at - b.at || a.id - b.id);
		for (const t of due) {
			if (!timers.has(t.id)) continue;
			if (t.every) t.at = t.at + t.every > now ? t.at + t.every : now + t.every;
			else timers.delete(t.id);
			try {
				t.fn(...t.args);
			} catch (error) {
				console.error("CHECKOUT_TIMER", error);
			}
		}
	};
}

// ------------------------------------------------------------------ process
let pending = "";
const handlers: Record<string, (() => void)[]> = {};
g.process = {
	env: { CHECKOUT_LANG: native.lang },
	argv: [],
	platform: native.platform ?? "ios",
	stdout: {
		write(chunk: string) {
			pending += chunk;
			let at = pending.indexOf("\n");
			while (at >= 0) {
				const line = pending.slice(0, at);
				pending = pending.slice(at + 1);
				if (line) native.send(line);
				at = pending.indexOf("\n");
			}
			return true;
		},
	},
	stderr: { write: (chunk: string) => (native.log(chunk), true) },
	stdin: {
		on(event: string, fn: () => void) {
			(handlers[event] ??= []).push(fn);
			return this;
		},
	},
	exit() {},
};
