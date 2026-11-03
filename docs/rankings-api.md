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
### Server (branch `rank-server`, 03/11/2026)
- **Times** (`updatedAt`, `endsAt`) are milliseconds since 1970, UTC. `endsAt` = next Monday 00:00 UTC.
- **Profiles:** every signed-in `/v1/rankings/*` call creates the profile when missing (like `/v1/social/*`) and keeps
  the country. A profile made from an existing cloud save starts ranked (`has_save = 1`, `level_at` = now).
- **`xp`** is the last field of the save summary (`{level, era, coins, diamonds, day, version, xp}`), a whole number ≥ 0.
- **`level_at`**: set when the level goes up, and on the first upload of a profile that never had one; a level going
  down (a restored save) keeps it. The migration sets `level_at` = the profile's last change for profiles that already
  had a save.
- **Boards (`world`, `country`):**
  - `limit`: an integer clamped to 1–100; missing or not a number → 100.
  - `?country=` is case-insensitive, two letters; `XX`, `T1` or anything else → 400 `bad-request`. Without it: my
    profile's country, then the connection's. No country at all → 200 `{country: null, top: [], me: null, total: 0, updatedAt}`.
  - `me` is null when signed out and on another country's board. My own row always carries my own market name (even
    when hidden by reports); other hidden names are `null`, as in social.
  - `total` = ranked players on that board (cached with the top list).
  - The top list and `total` are cached 10 min (isolate memory + Cache API); `me.rank` is always live. Opting out,
    being hidden or levelling up shows in `me` at once and in the cached top within 10 min.
  - Signing in is optional: a missing, invalid or expired token is answered as signed out (no 401 on these two routes).
  - Headers: signed in `cache-control: private, no-store`; signed out `public, max-age=60`. `x-board-cache:
    memory|cache|d1|none` says where the top list came from (debug only).
- **Friends board:** `rows` = me (first) + friends. Hidden friends (anti-cheat) are left out; opted-out friends stay
  (this board is only seen by friends, who already see each other in Amigos). `rank` is always `null` there (the game
  ranks by the chosen column). `weekPoints` = this ISO week's league points (0 when not joined); `likes` = the profile's
  likes total; `marketRating` = the public block's `marketRating` (number) or `null`.
- **League:**
  - A player joins this week's group with the first send of **≥ 1 point**; sending 0 before joining answers
    `{points: 0, place: null, groupSize: 0}` and joins nothing (so nobody is relegated for opening the app).
  - `group`: best first (points DESC, then `points_at` ASC, then player id); `place` is the 1-based position. Hidden
    players are not listed (a hidden player still sees their own row). `groupSize` (points answer) = the same count.
  - `promote` = `demote` = the zone of my group: **min(5, ⌊n/2⌋)** for n listed players (n 30 → 5, 10 → 5, 6 → 3, 2 → 1,
    1 → 0), so in a small group nobody is both promoted and relegated. Before joining: 5 / 5.
  - `rewards`: 10 entries, places 1–10, diamonds already × my division's multiplier.
  - `lastWeek`: from my group of the previous ISO week once it is closed: `{division: that week's, place (null when I
    was hidden), movedTo}`; `null` when I did not play that week.
  - `POST …/points`: 400 `bad-request` unless `week` matches `YYYY-Www` and `points` is an integer 0–1 000 000 000;
    409 `{error: "wrong-week", week: "<the server's week>"}`; 413 `too-large` over 16 KB. A hidden player gets 200
    `{points: <stored or 0>, place: null, groupSize: 0}` and nothing is written.
  - The cap uses the profile's level (from the last upload) × the ISO weekday (Monday 1 … Sunday 7). Above it: stored
    at the cap and **one strike per crossing** — a strike only when the stored total was still below the cap (the game
    resends its week total every 10 min; the same over-cap total again is not another strike until the next day's cap).
  - Points never go down; `points_at` moves only when the stored total grows.
- **End of week** (per group, all in SQL in one D1 batch):
  - Places by points DESC, `points_at` ASC, player id; hidden members get no place, no reward, keep their division.
  - With n placed players and zone = min(5, ⌊n/2⌋): place ≤ zone with ≥ 1 point → up one division (diamond stays
    diamond) + `chest: true` (also in diamond); place > n − zone, or 0 points → down one (bronze stays bronze); the rest
    stay. Diamonds = base(place) × multiplier rounded down, only with ≥ 1 point.
  - **Every placed member** gets one `league_reward` item (`diamonds` may be 0, `chest` false) so the game can show the
    end-of-week card to all; `from` is `null`. Exactly once per (player, week): the group's `closed` flag is written in
    the same transaction, and the insert also checks for an earlier item of that week.
  - Players who did not play keep their division. League rows older than 8 weeks are deleted by the cron.
  - Cron `5 0 * * 1` closes everything in batches of 100 groups. Lazy close: `GET league` / `POST …/points` first close
    my own group of a past week (it decides my division before I join a new group), then up to 100 other open groups.
- **Anti-cheat on uploads:** one strike per upload when the level is above `MAX_LEVEL`, or when it jumped more than
  +5 over the stored level **and** the new level is above 12 (the first 12 levels cost minutes: `EARLY_LEVELS` in
  `src/services/progression.ts`) **and** the profile already had a save (a profile's first save is not a jump).
- **`MAX_LEVEL` = 200.** The game has no top level: `applyExperience` levels up forever and the unlock ladder ends at
  52 (~531 k XP, the designed month of play). Level 200 needs ~14.5 M XP (years), so it only catches impossible numbers.
- **Data, besides the contract:** `league_members` also keeps `moved_to`, `diamonds`, `chest` (the close's outcome,
  read by `lastWeek`); indexes `league_members (player_id)` and `league_groups (week) WHERE closed = 0`.
- **Before `0003_rankings.sql` runs** the new Worker keeps saves, social and account deletion working as before (it
  notices the missing columns); only `/v1/rankings/*` answers 500.
