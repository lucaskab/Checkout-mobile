# Rankings v1 — friends ranking, weekly league, world & country level ranking

Asked by Lucas on 02/11/2026: item 8 of `claude/social-amigos-rankings-proposta.md` (rankings), **plus** a world and a
country ranking **by level** ("para ver quem são os top jogadores no mundo"). Builds on social v1
(`docs/social-api.md`, branch `social-game`): same principles (account needed, device-authoritative save, limits on the
server, new routes only, ids/numbers only — the game localizes, free-plan budget).

This file is the contract between the Worker (`worker/`) and the game (`src/`, `desktop/`, Unity). Both sides build
against it; change it only together, and write down what you settle in "Details settled" at the end.

## The four boards (one full-screen window "Ranking", tabs in this order)
| Tab | Who | Ordered by | Resets |
|---|---|---|---|
| **Amigos** | me + my friends | level, then total XP (switchable: level · semana (league points) · curtidas · nota do mercado) | never (week column resets Monday) |
| **Liga** | my league group (≤ 30 players of similar level) | league points this week | every Monday 00:00 UTC |
| **Mundo** | everyone with a ranking profile | level, then total XP, then who reached that level first | never (live, cached ≤ 10 min) |
| **País** | same, only my country | same as Mundo | never |

Mundo/País show the **top 100** plus **my own row pinned** (my position even when I am #48 213).

## Who is ranked
- A player is in Mundo/País once they have a social profile (`profiles` row; created by the first `/v1/social/*` call —
  opening the Ranking window counts) **and** at least one cloud save. Signed-out players see the boards read-only
  with a "Entre para aparecer no ranking" card (the top lists are public data: names, avatars, levels, countries).
- `hidden` players (see anti-cheat) and players with `ranking_opt_out = 1` are never listed and get `rank: null`.
- Market names follow the social rules (hidden name → `marketName: null`, the game shows "Mercado #<code>").

## Level, XP and "reached first"
- The save summary (`worker/src/save.ts`) gains `xp` = `state.market.totalExperience` (number, ≥ 0). Old summaries
  read back as `xp: 0`.
- On every `PUT /v1/save`, for a player with a profile: update `profiles.level`, `profiles.xp`; when the level goes
  **up**, set `profiles.level_at = now` (ms). `level_at` is the tie-break "who got there first".
- Sort key everywhere for level boards: `level DESC, xp DESC, level_at ASC, player_id ASC`.

## Country
- From Cloudflare: `request.cf.country` (ISO 3166-1 alpha-2, e.g. "BR"). Stored in `profiles.country` on every
  `PUT /v1/save` and every `/v1/social/*` call when it differs (cheap: only write on change). Values "XX", "T1"
  (Tor) and missing → keep the old value (`null` until a real one arrives).
- The player can't type a country (no cheating into a small country's top). Shown as a flag + the code.
- Privacy: the country is coarse, comes from the connection and is shown publicly on the boards → goes into the
  privacy policy text and the Ranking window has a "Aparecer no ranking" switch (`ranking_opt_out`).

## Weekly league
- **Divisions** (ids, the game localizes): `bronze`, `silver`, `gold`, `sapphire`, `ruby`, `emerald`, `diamond`.
  Everyone starts in `bronze`.
- **Week** = Monday 00:00 UTC → next Monday 00:00 UTC. Week id = `YYYY-Www` (ISO week), e.g. `2026-W45`.
- **Joining:** the first time a player sends points in a week, the server puts them in a group of their division:
  the open group (< 30 members, created this week) whose `level_band` matches theirs, else a new group.
  `level_band = floor((level - 1) / 5)` (levels 1–5, 6–10, …). Groups never merge or split during the week.
- **Points** come from the game (the save is device-authoritative). The game keeps this week's points in the save and
  sends the **week total** (not a delta) — see `POST /v1/rankings/league/points`. The server keeps the max it has seen
  (never goes down), capped by `maxPointsPerDay(level) × days elapsed in the week (1–7)`; above the cap → stored at the
  cap and the player gets a `suspicious` strike (anti-cheat).
- **What gives points** (game side, one place in `src/data/rankings.ts`):
  | Action | Points |
  |---|---|
  | each customer who bought | 1 |
  | each contract delivered | 25 |
  | end of a day: the day's rating stars (0–5) | stars × 10 |
  | an evolution / interior build / era / lot finished | 50 |
  | helping a friend's build (social) | 5 |
  `maxPointsPerDay(level) = 2000 + 300 × level` (server; generous, only catches impossible numbers).
- **End of week** (cron, Monday 00:05 UTC; also lazily on the first league call of a new week if the cron did not run):
  for every group of the finished week, final order = points DESC, then who reached that total first (`points_at` ASC).
  - top **5** move up one division (not above `diamond`), bottom **5** move down (not below `bronze`), but only players
    with ≥ 1 point count for promotion; players with 0 points always move down (except in bronze).
  - rewards go out as inbox items (kind `league_reward`, below) — exactly once per (player, week).
  - next week's division is stored on the profile (`league_division`); the player joins a new group when they first
    send points in the new week.
- **Rewards** (defaults, one table in the Worker `limits.ts` and mirrored for display in `src/data/rankings.ts`;
  Lucas may tune):
  | Final place | Diamonds (× division multiplier) |
  |---|---|
  | 1st | 20 |
  | 2nd | 15 |
  | 3rd | 10 |
  | 4th–10th | 5 |
  | promoted (top 5) | + a "baú" of coins = 3 × the receiver's gift value (the game computes it, payload says `chest: true`) |
  Division multiplier: bronze 1, silver 1, gold 1.5, sapphire 1.5, ruby 2, emerald 2, diamond 3 (rounded down).

## Data (D1) — `worker/migrations/0003_rankings.sql` + end of `schema.sql`
- `profiles` gains: `xp INTEGER NOT NULL DEFAULT 0`, `level_at INTEGER NOT NULL DEFAULT 0`, `country TEXT`,
  `ranking_opt_out INTEGER NOT NULL DEFAULT 0`, `ranking_hidden INTEGER NOT NULL DEFAULT 0`,
  `strikes INTEGER NOT NULL DEFAULT 0`, `league_division TEXT NOT NULL DEFAULT 'bronze'`, `has_save INTEGER NOT NULL DEFAULT 0`.
  (`ALTER TABLE … ADD COLUMN`; D1 has no `IF NOT EXISTS` for columns → the migration file says to run it once; the Worker
  checks the columns at startup only in tests.)
- Index for the boards: `CREATE INDEX profiles_rank ON profiles (level DESC, xp DESC, level_at, player_id) WHERE ranking_hidden = 0 AND ranking_opt_out = 0 AND has_save = 1;`
  and `profiles_rank_country ON profiles (country, level DESC, xp DESC, level_at, player_id) WHERE …same…`.
- `league_groups(id INTEGER PK AUTOINCREMENT, week TEXT, division TEXT, level_band INTEGER, members INTEGER, closed INTEGER DEFAULT 0)`,
  index `(week, division, level_band, members)`.
- `league_members(week TEXT, player_id TEXT, group_id INTEGER, points INTEGER, points_at INTEGER, final_place INTEGER,
  PK(week, player_id))`, index `(group_id, points DESC, points_at)`.
- `DELETE /v1/account` also removes the player's league rows (their group keeps one member less).

## Routes (all `Authorization: Bearer <token>` unless noted; JSON in and out; 16 KB bodies like social)
| Route | Body → Answer |
|---|---|
| `GET /v1/rankings/world?limit=100` (auth optional) | → `{top:[Row], me: Row\|null, total, updatedAt}` |
| `GET /v1/rankings/country?country=BR&limit=100` (auth optional; `country` defaults to mine, then to the request's) | → `{country, top:[Row], me: Row\|null, total, updatedAt}` |
| `GET /v1/rankings/friends` | → `{rows:[Row & {weekPoints, likes, marketRating}]}` — me + friends, unsorted (the game sorts by the chosen column) |
| `GET /v1/rankings/league` | → `{week, endsAt, division, group:[LeagueRow], me: LeagueRow\|null, promote: 5, demote: 5, rewards:[{place, diamonds}], lastWeek: {division, place, movedTo}\|null}` — `me: null` and `group: []` until I send points this week |
| `POST /v1/rankings/league/points` | `{week, points}` → `{points, place, groupSize}` (stored value after the cap) \| 409 `wrong-week` (the game's clock is in another week: it resets its counter and sends again) \| 400 `bad-request` |
| `PUT /v1/rankings/settings` | `{optOut: bool}` → 204 |

`Row = {rank, id, code, marketName, avatar, level, xp, era, country}` — `rank` is 1-based; for `me` it is my real
position (count of players ahead + 1), `null` if I am not ranked (opt-out, hidden, no save yet).
`LeagueRow = {place, id, code, marketName, avatar, level, points, isFriend}`.

- **Caching / free plan:** world/country `top` lists are cached with the Cache API for 10 min per (board, country,
  limit); `updatedAt` says when. `me.rank` is one indexed `COUNT(*)` per call. League group reads are one query.
  The game calls the boards **only while the Ranking window is open** (each tab at most every 60 s) and sends league
  points at most every 10 min plus on day end and on app pause/quit — never in the background otherwise.

### Inbox kind added
| kind | payload | The receiving game does |
|---|---|---|
| `league_reward` | `{week, division, place, diamonds, chest: bool, movedTo: division}` | Shows the end-of-week card (podium, place, new division with a badge animation), + diamonds, + coin chest if `chest` |

## Anti-cheat (the save stays device-authoritative; the server only refuses the impossible)
- League points above the daily cap → stored at the cap + 1 strike.
- Level jumping more than **+5 in one upload** or above the game's max level (`MAX_LEVEL` in limits, = the last level
  in the game's level table) → the level is still stored for social, the player gets 1 strike.
- `strikes ≥ 3` → `ranking_hidden = 1` (off every board, league points ignored, no league rewards). An admin route can
  clear it later (not in v1). Strikes never block the save or social.

## The game side
- **HUD:** a "Ranking" button (trophy icon) next to Amigos; also a "Ranking" tab/shortcut from the Amigos window header.
- **Window:** full-screen board like the Loja/Amigos (Lucas 02/11: full-screen and very gamified). Tabs Amigos · Liga ·
  Mundo · País with badges.
  - **Mundo / País:** podium for the top 3 (big framed round portraits, gold/silver/bronze plinths, crown on #1), then
    ranked cards/rows with round portrait, name, level ribbon, stage badge, flag; **my row pinned** at the bottom
    ("Você · #48.213"), "Ver minha posição" scrolls to me when I'm in the top 100. País header: my flag + country name
    (localized from the ISO code).
  - **Liga:** division badge big in the header + "termina em 2d 14h"; promotion zone (top 5) green, demotion zone
    (bottom 5) red, my row highlighted; rewards strip (1st/2nd/3rd diamonds, chest); before joining this week: "Faça
    pontos para entrar na liga desta semana" with how points are earned.
  - **Amigos:** column switch (Nível · Semana · Curtidas · Nota), invite card at the end ("Chame amigos para disputar").
  - **End of week:** the `league_reward` card: podium, place, division up/down animation, rewards with confetti.
- **Save:** `rankings: {week, points, pointsAt, lastSent, optOut}` with defaults on load (no version bump). Points are
  added where the actions happen (one helper `addLeaguePoints(state, n, now)` in `src/services/rankings.ts`) and reset
  when the ISO week changes (by the device clock; the server's 409 `wrong-week` wins).
- **Art:** reuse `trophy`, `medal`, `crown` icons; new 2D icons in the existing painted style (Codex imagegen, sheet on
  #00FF00, approved by Lucas before use): 7 division badges + a globe. Flags: an open-source flag set (MIT, e.g.
  `flag-icons`) rendered to small PNGs for the countries in the list. NEVER bake text into art.

## Details settled
(empty — add here what the server and the game settle while building)
