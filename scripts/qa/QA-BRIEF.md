# Checkout — headless QA playthrough brief

The game: "Checkout - Supermercado Simulator", a mobile supermarket tycoon (Unity draws the world and the
mini-games; ALL game rules, economy, pages and HUD come from the TypeScript game in `src/` driven by
`desktop/host.ts`). The player starts with a little table ("mesinha") and grows through stages:
mesinha → tenda → banca → conteiner → spati → quitanda → minimercado → mercadinho → supermercado →
hipermercado (→ rede/chain). The game is played in ENGLISH (Portuguese is the source language and gets
translated; any Portuguese left on an English screen is a bug).

## How to play it headless (fast)

`scripts/qa/play-kit.ts` runs the real host on a virtual clock from a brand-new save. One game hour takes
~2 s of real time. Write your scenario as a .ts file in `scripts/qa/agents/<your-name>/` and run:

    cd /home/claude/lucaskab/checkout-mobile
    timeout 900 node --no-warnings --import ./desktop/register.mjs scripts/qa/agents/<your-name>/<file>.ts 2>&1 | tail -80

Print with `process.stderr.write(...)` (console.* is redirected to the log file `tmp/qa/<name>.log`).
Always end the script with `process.exit(0)`. Read `scripts/qa/smoke.ts` first: it is a working example.

API (see the header of play-kit.ts):
- `const g = await startGame({ name: "<unique-name>", lang: "en" })` — fresh save each time (use a unique name per script).
- `g.hudView()` — HUD: coins, diamonds, level, xp, day bar, `coach` (the tutorial: title/text/button/buttonAction/target),
  `goal`, `quick`/`tools` buttons (each has `route` and/or `action`+`args` as a JSON string), `offline`, `levelUp`, `celebration`.
- `await g.route(r)` — open a page: "!loja" (fresh stack), "shelf:produce" (push), "back", "" (close all). Then `g.page()`.
- `g.pageOf(route)` — build any page without opening it. `g.buttons()` / `g.buttons(route)` — the buttons on it.
- `await g.hud(action, argsArray, after?)` — press a button: use the button's `action` and `JSON.parse(button.args)`.
  Returns `{ ok, reason }`. Coach buttons: `g.hud(coach.buttonAction, [])`.
- `await g.run(seconds)` — play with the app open. `await g.away(seconds)` — close the app and come back later.
- `g.state()` — the raw store (read only, for checking numbers). `g.summary()` — coins/level/era/day phase.
- `await g.panel("store", { shelfId })` — a click on the world (panels: store, stock, sectors, requests, day...).
- `g.problems` — automatic findings: Portuguese on English screens, pages that failed to build, errors thrown.
- Dev cheats exist (only to SKIP grind when your task says so): `devAdjustCoins [n]`, `devAdjustDiamonds [n]`,
  `devSetMarketEra ["supermercado"]`, `devPassTime [hours]`, `devFinishInteriorConstructions []`,
  `devFinishMarketExpansion []`, `devActivateGameEvent ["quinto-dia-util"]`. Say in the report when you used them.

The day loop: a game "day" is a few minutes with the shop open; at the end the day results open and the player
must collect them and start the next day (look for the buttons on the "day-result" / "day" pages and the HUD day bar).
The mini-games that happen in Unity (working the register, unloading trucks, restocking by hand) are NOT in the
headless game; when the rules expect the player to do them, look for the store action that finishes them
(e.g. receiving / restock / checkout actions) and note it.

## Rules
- Do NOT edit anything under `src/`, `desktop/`, `unity/` or commit to git. Only create files in
  `scripts/qa/agents/<your-name>/` and your report.
- Keep runs short (timeout 900). Prefer many small scripts over one huge one. Don't loop forever.
- When a rule seems odd, compare with real supermarket simulators / tycoon games (Supermarket Simulator,
  Supermarket Together, Idle Supermarket Tycoon, My Supermarket, Hay Day/Township for timers and stages) and
  search the web when unsure. Cite the source in the report.
- Read the relevant source (src/stores/game-store.ts, src/services/*, src/data/*, desktop/pages/*) to confirm a
  bug before reporting it, and point to file:line of the likely cause.

## Report (the deliverable)
Write `tmp/qa/reports/<your-name>.md` (in English), with these sections:
1. What you played (stages, game time, cheats used).
2. FAILED — things that are broken (crash, error page, action that silently does nothing, stuck progress,
   impossible goal, wrong number). For each: steps to reproduce (the script), what happened, what should happen,
   likely cause file:line, severity (high/med/low).
3. BAD — works but makes no sense / confusing / unfair / boring (with reasoning and, when used, sources).
4. IMPROVE — concrete suggestions, smallest first.
5. GOOD — what works well.
6. Portuguese texts found (exact strings and the page/route).
Keep it factual and specific; no padding. Your final answer to the caller: the report path and a 10-line summary.
