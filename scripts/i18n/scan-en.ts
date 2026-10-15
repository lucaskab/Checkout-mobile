import "../../desktop/require-shim";
import { writeFileSync } from "node:fs";
import { localizeSnapshot, localizeView, setLanguage } from "@/i18n";
import { createSimulatorSnapshot } from "@/services/simulator-snapshot";
import { useGameStore } from "@/stores/game-store";
import { createDesktopView } from "../../desktop/view";

// Walks every HUD page the game links to (in English) and lists the texts that came out in Portuguese.
//   node --import ./desktop/register.mjs scripts/i18n/scan-en.ts [lang]   → scripts/i18n/scan-<lang>.json
console.log = console.info = console.warn = console.error = () => {};
const lang = process.argv[2] ?? "en";
setLanguage(lang);
const PT = /[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔ]|\b(de|da|dos|das|para|com|não|você|seu|sua|seus|suas|uma|um|em|que|na|nas|nos|pela|pelo|ao|aos|ou|mais|hoje|dia|dias|loja|caixa|moedas|clientes|produtos|prateleiras?|mercado|pedidos?|vender|comprar|toque|faltam|falta|grátis|vídeo|obra|estoque|entrega|ganhe|abrir|fechar|voltar|melhorias|equipe|nível)\b/i;
const IGNORE = /^(Icons|Products|Ui|Fixtures|Art)\/|^[\w-]+(:[\w.-]*)*$|^\[.*\]$|^#?[0-9a-f]{6}$/i;
const found = new Map<string, Set<string>>();
function collect(value: unknown, where: string, routes: Set<string>) {
	if (typeof value === "string") {
		if (/^[!~][a-z][\w-]*(:\S*)?$/.test(value)) {
			routes.add(value.slice(1));
			return;
		}
		if (!IGNORE.test(value) && PT.test(value)) {
			if (!found.has(value)) found.set(value, new Set());
			found.get(value)!.add(where);
		}
		return;
	}
	if (Array.isArray(value)) return value.forEach((v) => collect(v, where, routes));
	if (value && typeof value === "object")
		for (const [key, v] of Object.entries(value)) {
			if (key === "args" && typeof v === "string") continue;
			if ((key === "route" || key === "after") && typeof v === "string") {
				if (v && v !== "back") routes.add(v.replace(/^[!~]/, ""));
				continue;
			}
			collect(v, where, routes);
		}
}
function crawl(label: string) {
	const state = () => useGameStore.getState();
	const queue = [""];
	const seen = new Set<string>();
	const extra = new Set<string>();
	collect(localizeSnapshot(createSimulatorSnapshot(state(), "scan", 1)), `${label}:snapshot`, extra);
	while (queue.length && seen.size < 2000) {
		const route = queue.shift()!;
		if (seen.has(route)) continue;
		seen.add(route);
		const routes = new Set<string>();
		collect(localizeView(createDesktopView(state(), 1, route ? [route] : [])), `${label}:${route || "hud"}`, routes);
		for (const r of routes) if (!seen.has(r) && r !== "back" && !r.startsWith("dev")) queue.push(r);
	}
	return seen.size;
}
const counts: string[] = [];
counts.push(`fresh ${crawl("fresh")}`);
const store = useGameStore.getState() as any;
store.devAdjustCoins?.(500_000);
store.devAdjustDiamonds?.(1_000);
for (const era of ["banca", "quitanda", "minimercado", "mercadinho", "supermercado"]) {
	try { (useGameStore.getState() as any).devSetMarketEra(era); } catch {}
	counts.push(`${era} ${crawl(era)}`);
}
const out = [...found.entries()].map(([text, where]) => ({ text, where: [...where].slice(0, 4) }));
writeFileSync(`scripts/i18n/scan-${lang}.json`, JSON.stringify(out, null, "\t"));
process.stdout.write(`${counts.join(", ")} → ${out.length} texts in Portuguese (scripts/i18n/scan-${lang}.json)\n`);
