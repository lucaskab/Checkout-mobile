// Headless player for QA: runs the real desktop host (desktop/host.ts, the same game the testers play through
// Unity) on a virtual clock, from a brand-new save, and lets a script press the same buttons Unity would.
//
//   node --import ./desktop/register.mjs scripts/qa/<scenario>.ts
//
//   import { startGame } from "./play-kit.ts";
//   const g = await startGame({ name: "early", lang: "en" });   // fresh save in tmp/qa/early-save.json
//   await g.route("!shelves");          // open a page like the toolbar does (see desktop/host.ts navigate)
//   g.page();                           // the page Unity would draw now (already translated), or g.pageOf("stock")
//   g.buttons();                        // every button on the current page: { label, action, args, route, disabled }
//   await g.hud("setMarketOpen", [true]);  // a HUD action (any store action in hudActions), returns { ok, reason }
//   await g.run(120);                   // play 120 s of game time (timers tick every virtual second)
//   await g.away(3 * 3600);             // close the app for 3 h and come back (offline income, timers)
//   g.state();                          // the zustand store state (read only!)
//   g.snapshot();                       // the last snapshot sent to Unity (customers, shelves, HUD numbers)
//   g.log("anything");                  // goes to tmp/qa/<name>.log with the game time
//   g.problems                          // texts left in Portuguese, errors thrown, "Erro ao montar a tela" pages
//
// Time runs only when the script calls run()/away(): one run(3600) takes a few seconds of real time.
import { mkdirSync, rmSync, appendFileSync, writeFileSync } from "node:fs";
import { PassThrough } from "node:stream";

type Timer = { id: number; fn: () => void; every: number; due: number; repeat: boolean };
type Message = Record<string, any>;

export type Game = Awaited<ReturnType<typeof startGame>>;

export async function startGame(options: { name: string; lang?: string; keepSave?: boolean; start?: number }) {
	const dir = "tmp/qa";
	mkdirSync(dir, { recursive: true });
	const save = `${dir}/${options.name}-save.json`;
	if (!options.keepSave) for (const f of [save, `${save}.bak`, `${save}.tmp`]) rmSync(f, { force: true });
	const logPath = `${dir}/${options.name}.log`;
	writeFileSync(logPath, "");
	process.env.CHECKOUT_DESKTOP_SAVE = save;
	process.env.CHECKOUT_LANG = options.lang ?? "en";

	// ---- virtual clock
	let now = options.start ?? Date.UTC(2026, 9, 12, 8, 0, 0);
	const RealDate = Date;
	class VirtualDate extends RealDate {
		constructor(...args: any[]) {
			if (args.length === 0) super(now);
			else super(...(args as [any]));
		}
		static now() {
			return now;
		}
	}
	(globalThis as any).Date = VirtualDate;
	const timers = new Map<number, Timer>();
	let nextId = 1;
	const add = (fn: () => void, ms: number, repeat: boolean) => {
		const id = nextId++;
		const every = Math.max(1, Number(ms) || 0);
		timers.set(id, { id, fn, every, due: now + every, repeat });
		return { id, unref() { return this; }, ref() { return this; }, hasRef: () => false, [Symbol.toPrimitive]: () => id } as any;
	};
	const clear = (handle: any) => { if (handle != null) timers.delete(typeof handle === "number" ? handle : handle.id); };
	(globalThis as any).setInterval = (fn: () => void, ms: number) => add(fn, ms, true);
	(globalThis as any).setTimeout = (fn: () => void, ms: number) => add(fn, ms, false);
	(globalThis as any).clearInterval = clear;
	(globalThis as any).clearTimeout = clear;

	// ---- the host's pipes
	const stdin = new PassThrough();
	Object.defineProperty(process, "stdin", { value: stdin, configurable: true });
	const problems: string[] = [];
	const results: Message[] = [];
	let lastView: Message | null = null;
	let lastSnapshot: Message | null = null;
	let catalog: Message | null = null;
	const realWrite = process.stdout.write.bind(process.stdout);
	let pending = "";
	(process.stdout as any).write = (chunk: any, ...rest: any[]) => {
		pending += String(chunk);
		let at: number;
		while ((at = pending.indexOf("\n")) >= 0) {
			const line = pending.slice(0, at);
			pending = pending.slice(at + 1);
			if (!line.trim()) continue;
			try {
				const message = JSON.parse(line);
				if (message.kind === "view") lastView = message;
				else if (message.kind === "snapshot" || message.type === "snapshot" || message.customers) lastSnapshot = message;
				else if (message.kind === "result") results.push(message);
				else if (message.kind === "i18n") catalog = message;
			} catch {
				realWrite(`${line}\n`, ...rest);
			}
		}
		return true;
	};
	const elapsed = () => {
		const s = Math.round((now - (options.start ?? Date.UTC(2026, 9, 12, 8, 0, 0))) / 1000);
		return `${Math.floor(s / 86400)}d ${String(Math.floor((s % 86400) / 3600)).padStart(2, "0")}:${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
	};
	const log = (text: string) => appendFileSync(logPath, `[${elapsed()}] ${text}\n`);
	// The game code's console output goes to stderr in the host; keep errors as problems.
	const realError = console.error;
	console.error = console.warn = (...args: unknown[]) => {
		const text = args.map(String).join(" ");
		if (/error|exception|undefined is not|cannot read/i.test(text)) problems.push(`console: ${text.slice(0, 300)}`);
		appendFileSync(logPath, `[${elapsed()}] (game) ${text.slice(0, 500)}\n`);
	};
	void realError;

	await import("../../desktop/host.ts");
	const { useGameStore } = await import("@/stores/game-store");
	const { pages } = await import("../../desktop/pages/index.ts");
	const { localizeView } = await import("@/i18n");
	const settle = async () => { for (let i = 0; i < 4; i++) await new Promise((r) => setImmediate(r)); };
	const send = async (message: Message) => { stdin.write(`${JSON.stringify(message)}\n`); await settle(); };
	await send({ kind: "ready" });

	function tick(stepMs: number) {
		now += stepMs;
		const due = [...timers.values()].filter((t) => t.due <= now).sort((a, b) => a.due - b.due);
		for (const t of due) {
			if (!timers.has(t.id)) continue;
			// timers faster than the step run once per step; slower ones keep their own cadence
			if (t.repeat) t.due = t.every < stepMs ? now + 1 : t.due + t.every > now ? t.due + t.every : now + t.every;
			else timers.delete(t.id);
			try { t.fn(); } catch (error) { problems.push(`timer threw at ${elapsed()}: ${String((error as Error)?.stack ?? error).slice(0, 400)}`); }
		}
	}

	// Portuguese left in English pages: common Portuguese words / accents.
	const PT = /[ãõçáéíóúâêô]|\b(você|para|com|não|loja|dia|estoque|clientes?|prateleira|moedas|comprar|abrir|fechar|nível|caixa|entrega|mercado|produto|vender|pedido)\b/i;
	function scanTexts(value: unknown, where: string, out: Set<string>) {
		if (typeof value === "string") { if (value.length > 1 && PT.test(value) && !/^https?:/.test(value)) out.add(value); return; }
		if (Array.isArray(value)) { for (const v of value) scanTexts(v, where, out); return; }
		if (value && typeof value === "object") for (const [k, v] of Object.entries(value)) if (!/^(id|action|route|icon|image|key|args|after|art|model|kind|tint|color|target|progressRoute|goalIcon|eventIcon|category|backdrop|variant|tone|layout|status|zone|role|state|phase|shift|sound)$/i.test(k)) scanTexts(v, where, out);
	}
	const seenPt = new Set<string>();
	function check(pageValue: Message, route: string) {
		if (pageValue?.title === "Erro ao montar a tela" || pageValue?.title === "Error building the screen") problems.push(`page ${route} failed: ${pageValue?.subtitle}`);
		if ((process.env.CHECKOUT_LANG ?? "en") !== "pt") {
			const found = new Set<string>();
			scanTexts(pageValue, route, found);
			for (const text of found) if (!seenPt.has(text)) { seenPt.add(text); problems.push(`pt text on ${route}: ${text.slice(0, 160)}`); }
		}
	}
	function buttonsOf(value: unknown, out: Message[] = []): Message[] {
		if (Array.isArray(value)) for (const v of value) buttonsOf(v, out);
		else if (value && typeof value === "object") {
			const o = value as Message;
			if (typeof o.action === "string" || typeof o.route === "string") out.push({ label: o.label ?? o.title ?? o.text ?? "", action: o.action, args: o.args, route: o.route, after: o.after, disabled: o.enabled === false || !!o.disabled });
			for (const [k, v] of Object.entries(o)) if (k !== "args") buttonsOf(v, out);
		}
		return out;
	}

	const game = {
		problems,
		log,
		now: () => now,
		elapsed,
		state: () => useGameStore.getState() as any,
		snapshot: () => lastSnapshot,
		catalog: () => catalog,
		/** The top page Unity would draw now (translated), or null when no page is open. */
		page(): Message | null {
			const v = lastView as Message | null;
			if (!v?.hasPage || !v.page) return null;
			check(v.page, String(v.page.route ?? "page"));
			return v.page;
		},
		/** Everything on screen besides the page: HUD numbers, the day bar, the tutorial coach, goal, offline popup,
		 *  level-up and celebration popups, quick buttons (view.quick / view.tools). */
		hudView() { const v: Message = { ...(lastView ?? {}) }; delete v.page; check(v, "hud"); return v; },
		view: () => lastView,
		/** Any page by route, built from the current state and translated, without opening it. */
		pageOf(route: string) {
			const built = pages(useGameStore.getState() as any, route);
			const localized = (localizeView as any)({ kind: "view", revision: 0, hasPage: true, page: built })?.page ?? built;
			check(localized, route);
			return localized;
		},
		buttons(route?: string) { return buttonsOf(route ? game.pageOf(route) : game.page()); },
		async route(route: string) { await send({ kind: "route", route }); return game.page(); },
		async panel(panel: string, extra: Message = {}) { await send({ kind: "panel", panel, ...extra }); return game.page(); },
		async hud(action: string, args: unknown[] = [], after?: string) {
			const id = `qa-${nextId++}`;
			await send({ kind: "hud", id, action, args, after });
			const result = [...results].reverse().find((r) => r.id === id) ?? { ok: false, reason: "no-result" };
			log(`hud ${action}(${JSON.stringify(args).slice(0, 120)}) -> ${result.ok ? "ok" : `NO ${result.reason}`}`);
			return result;
		},
		async command(message: Message) { await send({ kind: "command", ...message }); },
		/** Plays `seconds` of game time with the app open. */
		async run(seconds: number, stepMs = 1000) {
			const steps = Math.ceil((seconds * 1000) / stepMs);
			for (let i = 0; i < steps; i++) { tick(stepMs); if (i % 20 === 0) await settle(); }
			await settle();
		},
		/** The app closed for `seconds` and opened again (the offline catch-up runs like on a real phone). */
		async away(seconds: number) {
			now += seconds * 1000;
			for (const t of timers.values()) t.due = now + Math.min(t.every, 1000);
			try { (useGameStore.getState() as any).processSessionResume(); } catch (error) { problems.push(`resume threw: ${error}`); }
			await game.run(2);
		},
		summary() {
			const s: any = useGameStore.getState();
			return { time: elapsed(), coins: s.coins, diamonds: s.diamonds, level: s.market?.level, xp: s.market?.experience, era: s.era?.id ?? s.era?.current ?? s.era, open: s.market?.isOpen, day: s.day?.phase };
		},
	};
	return game;
}
