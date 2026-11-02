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
- `inbox(id INTEGER PK AUTOINCREMENT, player_id, kind, from_id, payload, created_at, acked_at)`
- `daily_actions(player_id, day, kind, target, PK(player_id, day, kind, target))` — gift/like/help-given limits.
- `build_helps(owner_id, build_id, helper_id, created_at, PK(owner_id, build_id, helper_id))`
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

## Routes (all `Authorization: Bearer <token>`; JSON in and out)
| Route | Body → Answer |
|---|---|
| `GET /v1/social/me` | → `{code, marketName, avatar, level, era, likes, friends, invitedBy: code\|null, invites: {rewarded, milestones:[1,3,5]}}` (creates the profile on first call; default name `null` = the game asks the player to choose) |
| `PUT /v1/social/me` | `{marketName?, avatar?}` → the profile \| 400 `{error:"name-not-allowed"}` \| 400 `{error:"bad-avatar"}` |
| `GET /v1/social/friends` | → `{friends:[Friend], incoming:[{id, code, marketName, avatar, level, era}], outgoing:[…same]}` |
| `POST /v1/social/friends/add` | `{code}` → `{status:"requested"\|"friends"}` \| 404 `not-found` \| 409 `already-friends`\|`self` \| 429 `limit` |
| `POST /v1/social/friends/accept` | `{id}` → `{status:"friends"}` |
| `POST /v1/social/friends/decline` | `{id}` → 204 |
| `DELETE /v1/social/friends/{id}` | → 204 (removes both sides; also cancels their pending requests) |
| `POST /v1/social/report` | `{id}` → 204 (market name report) |
| `GET /v1/social/friends/{id}/market` | → `{profile: Friend, public, data}` — `data` is the friend's save exactly as `GET /v1/save` returns it (read-only use: render the visit). 403 `not-friends`, 404 `no-save` |
| `POST /v1/social/gift` | `{to}` → 204 \| 409 `already-today` \| 403 `not-friends` |
| `POST /v1/social/like` | `{to}` → `{likes}` \| 409 `already-today` |
| `POST /v1/social/help` | `{to, buildId}` → `{helps}` (that build's count) \| 409 `already-helped`\|`build-full` \| 429 `daily-limit` \| 404 `no-build` (not in the friend's public block) |
| `GET /v1/social/requests` | → `{mine:[Request], friends:[Request & {owner: id}]}` (open ones only) |
| `POST /v1/social/requests` | `{productId, qty}` → `Request` \| 429 `limit` \| 400 `bad-request` |
| `DELETE /v1/social/requests/{id}` | → 204 (only the owner, only open) |
| `POST /v1/social/requests/{id}/fulfill` | → 204 \| 409 `taken` (someone else was first / expired / cancelled) \| 403 `not-friends` |
| `GET /v1/social/inbox` | → `{items:[{id, kind, from: {id, code, marketName, avatar}\|null, payload, createdAt}]}` (unacked, oldest first, ≤ 100) |
| `POST /v1/social/inbox/ack` | `{ids:[…]}` → 204 |
| `POST /v1/social/invite/redeem` | `{code}` → `{status:"friends"}` \| 409 `already-invited`\|`too-late`\|`self` \| 404 `not-found` |
| `GET /i/{code}` (no auth) | HTML landing page: the inviter's market name, store buttons (Play link with `&referrer=invite%3D<code>`, App Store link), "Copiar código", "Abrir no jogo" (`checkout://add/<code>`). Unknown code → same page without the name. |

`Friend = {id, code, marketName, avatar, level, era, likes, lastSeen, giftedToday, likedToday, public, openRequests:[Request]}`
`Request = {id, productId, qty, createdAt, expiresAt}`

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
