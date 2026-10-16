// Smoke test for play-kit: a fresh game, the first tutorial steps, 10 minutes with the shop open.
import { startGame } from "./play-kit.ts";
const out = (...a: unknown[]) => process.stderr.write(a.map((x) => (typeof x === "string" ? x : JSON.stringify(x))).join(" ") + "\n");
const g = await startGame({ name: "smoke" });
out("start", g.summary());
out("coach", g.hudView().coach, "goal", g.hudView().goal);
out("quick", g.hudView().quick, "tools", g.hudView().tools);
await g.route("!shelves");
out("shelves page title", g.page()?.title, "buttons", g.buttons().slice(0, 8));
await g.route("");
out("open", await g.hud("setMarketOpen", [true]));
await g.run(600);
out("after 10 min", g.summary(), "customers", g.snapshot()?.customers?.length);
out("coach", g.hudView().coach);
out("problems", g.problems.slice(0, 15));
process.exit(0);
