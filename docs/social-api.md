# Social features v1 — friends, invites, visits, help, gifts, product requests

Approved by Lucas on 01/11/2026: items 1–6 of `claude/social-amigos-rankings-proposta.md`. Ranking, album trading,
teams and partner events are NOT part of v1.

This file is the contract between the Worker (`worker/`) and the game (`src/`, `desktop/`, Unity). Both sides
build against it; change it only together.

## Principles
- **Social needs an account** (Google / Apple, already in the game). Signed-out players see a "Entre para jogar com
  amigos" card with the login buttons.
- **The save stays device-authoritative.** Nobody writes another player's save. Everything a friend does to you
  (help, gift, like, delivery, reward) becomes an **inbox item** on the server; your game applies it to your own save.
- **Inbox is at-least-once, applied exactly once:** the game fetches unacked items, applies them, remembers the
  applied ids in the save (`social.appliedInbox`, last 300 ids), saves, then acks. An item already in
  `appliedInbox` is acked without applying again. Never lose a delivery because of a crash between apply and ack.
- **Limits live on the server** (UTC day). The helper's own reward is granted by the helper's game only after the
  server answers OK.
- **New routes only.** Old builds keep working unchanged. Free plan budget: the game adds at most one social call
  per 5 minutes in the background (inbox + friends refresh), plus calls on user actions.
- **No free-text chat in v1.** The only user text is the market name (filtered, reportable).
- **Multilingual:** the server never sends display text except the invite landing page (pt-BR, en, es, fr, de by
  Accept-Language). Everything else is ids/numbers; the game localizes.

## Numbers (defaults, tune in one place on each side)
| What | Value |
|---|---|
| Friends per player | 50 |
| Pending outgoing friend requests | 20 |
| Gift | 1 per friend per day; receiver claims at most 25 gifts per day (extra ones wait for the next day) |
| Like | 1 per friend per day; both get coins (liker locally, owner via inbox) |
| Help on a build | 1 per helper per build; max 10 helps per build; max 30 helps given per helper per day; each help = 5 min off |
| Product requests | max 2 open per player; qty 1–20 units of one product; expire after 24 h; one friend fulfils a whole request |
| Invite redeem | only accounts created less than 7 days ago, once per account, not your own code |
| Invite reward | when the invited player reaches **level 8 (Späti)**: 30 💎 to each. Inviter milestones at 1 / 3 / 5 rewarded invites: exclusive decorations (`invite-reward-1`, `-3`, `-5`) |
| Market name | 3–20 chars, letters (any script), digits, space, `'`, `-`, `&`, `.`; profanity list (pt, en, es, fr, de); after 3 distinct reports the name is hidden ("Mercado #<code>") until changed |

## Data (D1) — `worker/schema.sql` additions
- `profiles(player_id PK, code UNIQUE, market_name, avatar, level, era, likes_total, public_json, invited_by,
  invite_rewarded, invites_rewarded, name_hidden, created_at, updated_at)`
  - `code`: 8 chars from `23456789ABCDEFGHJKMNPQRSTUVWXYZ`, shown as `XXXX-XXXX`, created on first `/v1/social/me`.
  - `level`/`era` refreshed from the save summary on every `PUT /v1/save`.
  - `public_json`: the small public block the game sends with the save (below), ≤ 4 KB.
- `friends(player_id, friend_id, created_at, PK(player_id, friend_id))` — two rows per friendship.
- `friend_requests(from_id, to_id, created_at, PK(from_id, to_id))`
- `inbox(id INTEGER PK AUTOINCREMENT, player_id, kind, from_id, payload, created_at, acked_at)` — payload is JSON text.
- `daily_actions(player_id, day, kind, target, PK(player_id, day, kind, target))` — gift/like limits (`day` = UTC day number).
- `build_helps(owner_id, build_id, helper_id, created_at, PK(owner_id, build_id, helper_id))` — also counts the helps
  given per helper per UTC day.
- `product_requests(id INTEGER PK AUTOINCREMENT, player_id, product_id, qty, status ['open','fulfilled','cancelled','expired'], fulfilled_by, created_at, expires_at)`
- `name_reports(target_id, reporter_id, created_at, PK(target_id, reporter_id))`
- `DELETE /v1/account` removes all of the player's social rows (and their friendships on the other side).

## The public block (sent by the game with the save)
`PUT /v1/save` accepts an optional `public` object next to `data` (old builds don't send it):
```json
{ "builds": [ { "id": "interior:42", "kind": "interior|evolution|era|lot", "item": "shelf-produce", "tier": 3, "endsAt": 1793570000000 } ],
  "stage": "spati", "marketRating": 4.2 }
```
Only builds that are running or queued. The server stores it as-is (validated: object, ≤ 4 KB, ≤ 12 builds).
- **Send it as the last field**, after `force` (Unity: declare the field last in the upload class):
  `{"baseRevision":3,"data":"…","deviceId":"…","force":false,"public":{…}}`. The server then cuts the save out of the
  body without parsing the whole body (the cheap path). Any other position works but parses the whole body.
- No `public` = keep the stored one (old builds). `"public": null` = clear it. A block that fails the checks is
  ignored (logged) and **the save itself is still stored** — a bad public block never blocks a cloud save.
- Only a profile that exists is updated (one is created by the first `/v1/social/*` call, never by an upload).
- **Build ids must be unique per build instance** (never reused by a later build in the same slot), e.g.
  `interior:42:<startedAt>`: helps are counted per (owner, buildId) and kept 30 days.

## Routes (all `Authorization: Bearer <token>`; JSON in and out)
| Route | Body → Answer |
|---|---|
| `GET /v1/social/me` | → `{code, marketName, avatar, level, era, likes, friends, invitedBy: code\|null, invites: {rewarded, milestones:[1,3,5]}}` (creates the profile on first call; default name `null` = the game asks the player to choose) |
| `PUT /v1/social/me` | `{marketName?, avatar?}` → the profile (same shape as GET) \| 400 `{error:"name-not-allowed"}` \| 400 `{error:"bad-avatar"}` |
| `GET /v1/social/friends` | → `{friends:[Friend], incoming:[{id, code, marketName, avatar, level, era}], outgoing:[…same]}` |
| `POST /v1/social/friends/add` | `{code}` → `{status:"requested"\|"friends"}` ("friends" when they had already asked me) \| 404 `not-found` \| 409 `already-friends`\|`self` \| 429 `limit` (my or their list full, or 20 pending) |
| `POST /v1/social/friends/accept` | `{id}` → `{status:"friends"}` \| 404 `not-found` (no pending request from them) \| 429 `limit` |
| `POST /v1/social/friends/decline` | `{id}` → 204 |
| `DELETE /v1/social/friends/{id}` | → 204 (removes both sides; also cancels their pending requests) |
| `POST /v1/social/report` | `{id}` → 204 (market name report; reporting yourself does nothing) \| 404 `not-found` |
| `GET /v1/social/friends/{id}/market` | → `{profile: Friend, public, data}` — `data` is the friend's save exactly as `GET /v1/save` returns it (read-only use: render the visit). 403 `not-friends`, 404 `no-save` |
| `POST /v1/social/gift` | `{to}` → 204 \| 409 `already-today` \| 403 `not-friends` |
| `POST /v1/social/like` | `{to}` → `{likes}` (the friend's new total) \| 409 `already-today` \| 403 `not-friends` |
| `POST /v1/social/help` | `{to, buildId}` → `{helps}` (that build's count) \| 409 `already-helped`\|`build-full` \| 429 `daily-limit` \| 404 `no-build` (not in the friend's public block) \| 403 `not-friends` |
| `GET /v1/social/requests` | → `{mine:[Request], friends:[Request & {owner: id}]}` (open ones only) |
| `POST /v1/social/requests` | `{productId, qty}` → `Request` \| 429 `limit` \| 400 `bad-request` (`productId` 1–64 of `A-Z a-z 0-9 _ . : -`, `qty` integer 1–20) |
| `DELETE /v1/social/requests/{id}` | → 204 (only the owner, only open) \| 404 `not-found` (not an open request of mine) |
| `POST /v1/social/requests/{id}/fulfill` | → 204 \| 409 `taken` (someone else was first / expired / cancelled) \| 403 `not-friends` (also: my own request) \| 404 `not-found` |
| `GET /v1/social/inbox` | → `{items:[{id, kind, from: {id, code, marketName, avatar}\|null, payload, createdAt}]}` (unacked, oldest first, ≤ 100) |
| `POST /v1/social/inbox/ack` | `{ids:[…]}` (≤ 300; ids not mine or already acked are ignored) → 204 \| 400 `bad-request` |
| `POST /v1/social/invite/redeem` | `{code}` → `{status:"friends"\|"invited"}` ("invited": the invite counts but a friend list is full) \| 409 `already-invited`\|`too-late`\|`self` (also: the code of a player I invited) \| 404 `not-found` |
| `GET /i/{code}` (no auth) | HTML landing page: the inviter's market name, store buttons (Play link with `&referrer=invite%3D<code>`, App Store link), "Copiar código", "Abrir no jogo" (`checkout://add/<code>`). Unknown code → same page without the name. A malformed code → no code box, plain store links. |

`Friend = {id, code, marketName, avatar, photo, level, era, likes, lastSeen, giftedToday, likedToday, public, openRequests:[Request]}`
(`photo`: see Photos below)
`Request = {id, productId, qty, createdAt, expiresAt}`

### Details settled while building the server (02/11/2026)
- **Codes** travel as the 8 characters without the dash (`"7KQ2M9XA"`) in every answer and URL
  (`/i/7KQ2M9XA`, `checkout://add/7KQ2M9XA`, `referrer=invite%3D7KQ2M9XA`); the game shows `7KQ2-M9XA`. The server
  accepts typed codes with or without the dash, spaces, lower case.
- **Times** (`lastSeen`, `createdAt`, `expiresAt`) are numbers: milliseconds since 1970, UTC. `lastSeen` = the
  friend's last cloud upload or login, whichever is later.
- **`GET /v1/social/me`** also returns `id` (the player id) and `nameHidden`. `invites.milestones` is the fixed list
  of thresholds `[1,3,5]`; reached = those ≤ `rewarded`.
- **Hidden names:** other players get `marketName: null` (the game shows "Mercado #<code>"); the owner still gets
  their own name plus `nameHidden: true` → ask for a new one. Re-sending the same name in another spelling (case,
  accents, spaces) does not count as a change: 400 `name-not-allowed`. A new name clears the reports.
- **`avatar`**: a string id from the game's avatar list, 1–32 of `A-Z a-z 0-9 _ -`; `null` = default (send `null`
  to reset). `marketName: null` in `PUT /me` = leave the name unchanged.
- **`friend_added`** goes only to the player who did not act (the requester when the other accepts; the inviter when
  a code is redeemed). The actor already knows from the answer.
- **Inbox `from`**: `null` when the sender's account was deleted. For `invite_reward` it is the other player.
  When an account is deleted, what it sent (gifts, deliveries…) stays with the receivers, with `from: null`; players
  it invited stay "already invited" (their own reward still comes at level 8).
- **Invite reward:** granted when the invited player's level in the save summary reaches 8 on `PUT /v1/save`, or
  right away when the code is redeemed by a player already at level 8. Exactly once (checked inside one D1
  transaction). The inviter's item carries `milestone` when their rewarded count becomes 1, 3 or 5.
- **Gifts held back:** the receiver is offered at most 25 `gift` items per UTC day (counted by acks); the rest stay
  unacked on the server and show up on the next days. Other kinds are never held back.
- **Social bodies** are at most 16 KB (413 `too-large`). Every social route answers 401 `signed-out` without a
  valid session and 429 `slow-down` past the rate limit, like the save routes.
- `GET /v1/social/friends`: friends most recently seen first; `incoming` / `outgoing` oldest first.

### Photos — friends see the Google profile photo (settled 04/11/2026, branch `next-photos-sectors`)
Lucas: friends show the photo of their social login. Server: `worker/migrations/0004_photos.sql`; tests
`worker/test/photos.test.ts`.
- **Where it comes from:** the Google ID token's `picture` claim (sent when the login asks for the `profile` scope:
  the iPhone and PC/Editor logins ask for `openid email profile`; Android's Credential Manager "Sign in with Google"
  returns the same Google Identity Services ID token, whose consent covers name, e-mail and profile picture — to
  confirm on the first Android login after the deploy: `SELECT photo_url FROM players WHERE google_sub = …`). Stored as `players.photo_url` on every Google login (a login without
  one keeps the stored one). Only `https://lh3…lh6.googleusercontent.com/…` addresses (≤ 1024 chars) are kept;
  anything else is dropped.
- **Apple:** Sign in with Apple gives no photo — its credential has only `user`, `fullName`, `email` (scopes `.fullName`
  and `.email`) and the identity token none either. Apple accounts (and Google accounts without a picture) keep their
  chosen avatar (`shopper-1…12`).
- **Who gets it:** `Friend.photo` (friend list, `GET …/market` profile) and `GET /v1/rankings/friends` rows' `photo`:
  only accepted friends and myself. Friend requests (`incoming` / `outgoing`), inbox `from`, Mundo / País / Liga
  never carry it (strangers see the avatar: privacy).
- **The switch** "Mostrar minha foto do Google para amigos" (default on): `PUT /v1/social/me {showPhoto: boolean}`
  (400 `bad-request` when not a boolean) → `players.photo_hidden`. Off: friends get `photo: null` (they see the
  avatar), and so does my own row on the friends board. `GET/PUT /v1/social/me` answer `photo` (my own stored URL even
  when hidden, for the profile preview; null for Apple) and `showPhoto`.
- **The game** shows `photo` when it is not null, else the avatar; my own face in the friend screens shows my photo
  when `showPhoto && photo`. It asks Google for a small square (`=s128-c`, Google's image-sizing parameters: `=s<n>`
  size of the longer side, `-c` square crop; the token's `=s96-c` suffix is replaced), downloads it only from
  `https://lh3…lh6.googleusercontent.com`, caches it in memory and on disk (size cap), draws it round inside the gold
  ring and keeps the avatar while it loads or when it fails.
- **Before the migration** the Worker answers as before with `photo: null` / `showPhoto: true` (a "no such column"
  turns photos off for a minute and logs "run worker/migrations/0004_photos.sql").
- **Privacy policy (text for Lucas to approve):** "Se você entrar com o Google, a foto do seu perfil Google é mostrada
  aos seus amigos no jogo. Você pode desligar isso no seu perfil."

### Inbox kinds and payloads
| kind | payload | The receiving game does |
|---|---|---|
| `gift` | `{}` | Opens as a gift box: coins scaled to the receiver's level (or a delivery ticket / album sticker). Max 25 per day (server keeps the rest unacked until the next day — the game acks only what it applied) |
| `like` | `{}` | + coins (small), "X curtiu seu mercado" |
| `help` | `{buildId, minutes: 5}` | −5 min on that build if still running (never below now); if it already finished, a small coin thank-you |
| `delivery` | `{requestId, productId, qty}` | + qty of the product into the stock room (overflow allowed) |
| `friend_request` | `{}` | Shows the request (badge) |
| `friend_added` | `{via: "code"\|"invite"}` | "Agora vocês são amigos" |
| `invite_reward` | `{diamonds: 30, role: "inviter"\|"invited", milestone?: 1\|3\|5}` | + diamonds; milestone → unlocks the exclusive decoration in the inventory |
| `request_fulfilled` | `{requestId}` | Notification only (the goods come as `delivery`) |

## The game side (summary — details in the game's own docs)
- Profile card + choose market name and avatar (first time the Amigos page opens).
- **Amigos** page: my code (copy / share / QR), add by code, incoming requests, friend list with level, stage,
  likes, "Presente" button, "Visitar", badges for friends with builds to help or open requests.
- **Chamar amigo**: native share sheet with the link `https://checkout-server.lucaslfurini.workers.dev/i/<code>`
  and a picture of the player's market. Android reads the Play Install Referrer and offers the code automatically
  after login; iPhone: "Tem um código de convite?" field (paste). `checkout://add/<code>` opens the game and adds
  the friend.
- **Visit**: the friend's market rendered read-only from `GET …/market` (never touching the player's own state or
  save), camera only, top bar with Curtir, Presente, Ajudar (on each running build), and the friend's product
  requests (Enviar). "Voltar ao meu mercado".
- **Pedir ajuda**: from a contract shortfall or the stock page, "Pedir aos amigos" for one product (1–20 units).
- Inbox fetch on app start, after login and every 5 min with the cloud sync; results celebrated in a small toast
  queue + a badge on the Amigos button.

## The game side as built (branch `social-game`, 02/11/2026)
Where it lives: `src/services/social.ts` (inbox → save, public block, help on builds), `src/data/social.ts` (numbers),
`desktop/social.ts` (calls, inbox cycle, actions, visit), `desktop/pages/amigos.ts` (Amigos, profile, Pedir aos amigos,
the friend's requests during a visit), `desktop/social-mock.ts` (these routes in process, for the Editor),
`unity/…/CheckoutSocial.cs` (HTTP with the session token, inbox clock, flush before ack, share sheet, links, Play Install
Referrer, avatars) and `CheckoutDesktopHUD.Social.cs` (visit bar, "Ajudar" over the builds, toast queue).

How the game uses the contract (read these as the game's half of it):
- **Product ids** go out as the catalog's numeric id written as text (`"47"`, the Worker's rule) and are read back from
  text or number (requests, `delivery` payloads).
- **Avatar ids**: `shopper-1` … `shopper-12`, portraits of the game's own shoppers drawn by Unity (no image upload).
- **Build ids** in the public block: `interior:<constructionId>` and `evolution:<evolutionId>` (both ids already carry
  their creation time), `era:<eraId>:<startedAt>`, `lot:<lotId>:<startedAt>`; `item` = `<kind>-<targetId>`. The old
  market-expansion works (`marketExpansionConstruction`) are not listed (not one of the four kinds).
- **Upload**: `public` is written after `force` as raw JSON (Unity's JsonUtility cannot write a raw object, so the game
  appends it to the class's own JSON: same bytes as a last field). Omitted when empty or over 4096 characters.
- **`GET …/market`**: `data` is read as the save text; a CloudSave object or a bare `{state, version}` also work. The
  friend's save is migrated with the game's own migrations into a separate object (never the player's store).
- **Background calls**: only `GET /inbox`, at start, after a login and every 5 minutes, and only once the player has
  opened Amigos on this save (the save keeps the code; the first social call creates the profile). After a login the
  game also calls `GET /me` once. The friend list loads only while Amigos is open (at most every 20 s).
- **Ack**: after the items are in the save and the save is on disk (`CheckoutDesktopHost.Flush`), in chunks of ≤ 300.
  Gifts over the day's 25 are not acked (they come again the next UTC day).
- **Helper rewards** (like, help) and the sender's delivery refund are booked only after the server's OK; during a
  visit they wait until the player is back home (the player's save is frozen while visiting).
- **Gifts land in the Correio** (02/11): an applied `gift` becomes a box in the save (`social.mailbox`, applied and
  acked exactly once like every item); "Abrir" / "Abrir tudo" pays its coins. The daily cap of 25 still counts at
  receipt. The Correio also keeps the last 30 things friends did (`social.history`); `social.daily` counts the helps
  the player gave today (the "Ajudas hoje" meter, 30 a day like the server).
- **UI**: Amigos · Pedidos · Convidar · Correio are full-screen windows (the Loja's board layout, Lucas 02/11).

Open questions for the server:
1. Should the market-expansion works (`marketExpansionConstruction`) be a fifth build kind (`expansion`) friends can
   help? The game would send `expansion:<id>:<startedAt>`.
2. A friend whose cloud save is very old (before a migration) is still shown; is there a minimum save version the
   server should refuse for `…/market`? The game copes either way.
