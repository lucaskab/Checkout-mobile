// Re-checks the QA sweep's fixes (16/10) on a fresh headless game.
import { startGame } from "./play-kit.ts";
const out = (...a: unknown[]) => process.stderr.write(a.map((x) => (typeof x === "string" ? x : JSON.stringify(x))).join(" ") + "\n");
const g = await startGame({ name: "verify" });
await g.hud("skipOnboarding", []);
// 1. numbers and texts in English
await g.hud("devAdjustCoins", [123456]);
out("shelves subtitle", g.buttons("store").length, JSON.stringify(g.pageOf("store")).match(/Starts with four slots|Começa/g));
out("hud coins text", g.hudView().coins, JSON.stringify(g.pageOf("loja:expansoes")).match(/\d{1,3}([.,]\d{3})+/g)?.slice(0, 4));
// 2. setMarketOpen tells when it did nothing
await g.hud("setMarketOpen", [true]);
await g.run(400);
out("day phase", g.state().day.phase, "reopen ->", await g.hud("setMarketOpen", [true]));
// 3. contract prize text in English
const day = g.pageOf("day");
await g.hud("claimDayResult", []);
const offers = g.state().day.offers ?? [];
if (offers[0]) await g.hud("startDay", [offers[0].id]);
out("dayDetail", g.hudView().dayDetail);
// 4. offline with empty shelves sells nothing
for (const slot of Object.keys(g.state().shelfStock)) g.state().shelfStock[slot] = 0;
const before = g.state().coins;
await g.away(3 * 3600);
out("offline empty shelves coins", g.state().coins - before, g.state().offlineSummary);
// 5. level-up preview names
const { useGameStore } = await import("@/stores/game-store");
out("level-up next", g.hudView().levelUp?.next ?? "(no popup)");
out("problems", g.problems);
process.exit(0);
