import { HEADERS, HttpError, json, readCapped } from "./http.ts";
import { readCode } from "./codes.ts";
import { invitePage, pageResponse, pickLanguage } from "./landing.ts";
import { SOCIAL } from "./limits.ts";
import { cleanName, isNameAllowed, sameName } from "./names.ts";
import type { FriendRow, InboxRow, OwnPhoto, Profile, RequestRow, Store } from "./store.ts";

/**
 * Social v1 routes (docs/social-api.md — the contract with the game). All under /v1/social/ with the game's session
 * (`Authorization: Bearer <token>`), plus the public invite page GET /i/<code>. Answers are ids and numbers only (the
 * game localizes); times are milliseconds since 1970. The stored public block and inbox payloads are JSON text
 * spliced into the answers as they are (no parse / re-encode), and a visit streams the friend's stored save like
 * GET /v1/save does.
 */
export type SocialOptions = {
	store: Store;
	now: () => number;
	log: (line: string) => void;
	/** The signed-in player's id (session checked, rate limited) or HttpError 401/429. */
	sessionOf: (request: Request) => Promise<string>;
};

const JSON_HEADERS = HEADERS;
const raw = (status: number, text: string) => new Response(text, { status, headers: JSON_HEADERS });
const fail = (status: number, error: string): never => {
	throw new HttpError(status, { error });
};

const PLAYER_ID = /^[A-Za-z0-9_-]{1,64}$/;
const AVATAR = /^[A-Za-z0-9_-]{1,32}$/;
const PRODUCT_ID = /^[A-Za-z0-9_.:-]{1,64}$/;
const MAX_SOCIAL_BODY = 16 * 1024;
const VERBS = new Set(["add", "accept", "decline", "ack", "redeem"]);
const ROUTES = new Set(
	[
		"GET me", "PUT me", "GET friends", "POST friends/add", "POST friends/accept", "POST friends/decline", "DELETE friends/:id",
		"GET friends/:id/market", "POST report", "POST gift", "POST like", "POST help", "GET requests", "POST requests",
		"DELETE requests/:id", "POST requests/:id/fulfill", "GET inbox", "POST inbox/ack", "POST invite/redeem",
	],
);

/** Social bodies are small: refuse anything bigger than 16 KB before reading it. */
export async function readBody(request: Request): Promise<Record<string, unknown>> {
	const text = new TextDecoder().decode(await readCapped(request, MAX_SOCIAL_BODY));
	try {
		const body = JSON.parse(text || "{}");
		if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error();
		return body;
	} catch {
		return fail(400, "bad-json");
	}
}

const playerId = (value: unknown) => (typeof value === "string" && PLAYER_ID.test(value) ? value : null);

// ── Answer shapes ─────────────────────────────────────────────────────────────────────────────────────────────

/** Someone else's name: null when unnamed or hidden by reports (the game shows "Mercado #<code>"). */
const shownName = (p: Profile) => (p.nameHidden ? null : p.marketName);

const request = (r: RequestRow) => ({ id: r.id, productId: r.productId, qty: r.qty, createdAt: r.createdAt, expiresAt: r.expiresAt });

const card = (p: Profile) => ({ id: p.id, code: p.code, marketName: shownName(p), avatar: p.avatar, level: p.level, era: p.era });

/** Friend = {id, code, marketName, avatar, photo, level, era, likes, lastSeen, giftedToday, likedToday, openRequests,
 * public}. `photo`: the friend's Google photo (null: none, or they turned it off). Only friends get it: strangers
 * (friend requests, the inbox, Mundo / País / Liga) see the avatar only. */
function friendJson(f: FriendRow, requests: RequestRow[]) {
	const head = JSON.stringify({
		...card(f),
		photo: f.photo,
		likes: f.likes,
		lastSeen: f.lastSeen,
		giftedToday: f.giftedToday,
		likedToday: f.likedToday,
		openRequests: requests.filter((r) => r.owner === f.id).map(request),
	});
	return `${head.slice(0, -1)},"public":${f.publicJson ?? "null"}}`;
}

function inboxJson(item: InboxRow) {
	const head = JSON.stringify({ id: item.id, kind: item.kind, from: item.from, createdAt: item.createdAt });
	return `${head.slice(0, -1)},"payload":${item.payload}}`;
}

const meJson = (me: { profile: Profile; friends: number; inviterCode: string | null; photo: OwnPhoto }) => ({
	id: me.profile.id,
	code: me.profile.code,
	// The owner always sees their own name; nameHidden tells the game to ask for a new one.
	marketName: me.profile.marketName,
	avatar: me.profile.avatar,
	level: me.profile.level,
	era: me.profile.era,
	likes: me.profile.likes,
	friends: me.friends,
	invitedBy: me.inviterCode,
	invites: { rewarded: me.profile.invitesRewarded, milestones: SOCIAL.inviteMilestones },
	nameHidden: me.profile.nameHidden,
	// My own Google photo (null: none, Apple, or before migrations/0004_photos.sql) even when I hide it from friends,
	// and the switch "Mostrar minha foto do Google para amigos".
	photo: me.photo.url,
	showPhoto: me.photo.shown,
});

/** The build ids in a stored public block (validated as an object with ≤ 12 builds when it was stored). */
function buildIds(publicJson: string | null): string[] {
	if (!publicJson) return [];
	try {
		const builds = (JSON.parse(publicJson) as { builds?: unknown }).builds;
		return Array.isArray(builds) ? builds.map((b) => (b && typeof b === "object" ? (b as { id?: unknown }).id : null)).filter((id): id is string => typeof id === "string") : [];
	} catch {
		return [];
	}
}

export function socialRoutes(options: SocialOptions) {
	const { store, sessionOf } = options;

	/** The signed-in player's profile (created on first use); the session was checked before the body was read. */
	const profileOf = async (id: string, counts = false, country: string | null = null) => {
		const found = await store.socialMe(id, counts, country);
		if (!found) fail(401, "signed-out");
		return found as NonNullable<typeof found>;
	};

	/** `country`: the connection's country (checked; null = unknown), kept on the profile when it changed. */
	return async (req: Request, path: string, method: string, country: string | null = null): Promise<Response | null> => {
		// The invite landing page (no session).
		if (path.startsWith("/i/") && (method === "GET" || method === "HEAD")) {
			const segment = path.slice(3).split("/")[0];
			let code: string | null = null;
			try {
				code = readCode(decodeURIComponent(segment));
			} catch {}
			const name = code ? await store.marketNameByCode(code) : null;
			const iphone = /iPhone|iPad|iPod/.test(req.headers.get("user-agent") ?? "");
			return pageResponse(invitePage(code, name, pickLanguage(req.headers.get("accept-language")), iphone));
		}
		if (!path.startsWith("/v1/social/")) return null;
		const parts = path.slice("/v1/social/".length).split("/");
		// "friends/<id>/market" → "friends/:id/market"; the second segment is an id unless it is one of the verbs.
		const route = `${method} ${parts.map((part, i) => (i === 1 && !VERBS.has(part) ? ":id" : part)).join("/")}`;
		if (!ROUTES.has(route)) return null;
		const id = await sessionOf(req);
		const me = (counts = false) => profileOf(id, counts, country);

		switch (route) {
			case "GET me":
				return json(200, meJson(await me(true)));

			case "PUT me": {
				const body = await readBody(req);
				const { profile } = await me();
				const changes: { marketName?: string; avatar?: string | null; clearReports?: boolean } = {};
				if (body.marketName !== undefined && body.marketName !== null) {
					const name = cleanName(body.marketName);
					if (name === null || !isNameAllowed(name)) fail(400, "name-not-allowed");
					const same = profile.marketName !== null && sameName(name as string, profile.marketName);
					// A hidden name comes back only as another name, not as a new spelling of the same one.
					if (same && profile.nameHidden) fail(400, "name-not-allowed");
					if (name !== profile.marketName) changes.marketName = name as string;
					if (!same && profile.marketName !== null) changes.clearReports = true;
				}
				if (body.avatar !== undefined) {
					if (body.avatar !== null && (typeof body.avatar !== "string" || !AVATAR.test(body.avatar))) fail(400, "bad-avatar");
					changes.avatar = body.avatar as string | null;
				}
				if (body.showPhoto !== undefined && typeof body.showPhoto !== "boolean") fail(400, "bad-request");
				if (Object.keys(changes).length) await store.updateProfile(profile.id, changes);
				if (typeof body.showPhoto === "boolean") await store.setPhotoShown(profile.id, body.showPhoto);
				return json(200, meJson(await me(true)));
			}

			case "GET friends": {
				const { profile } = await me();
				const list = await store.friendsOf(profile.id);
				const friends = list.friends.map((f) => friendJson(f, list.requests)).join(",");
				return raw(200, `{"friends":[${friends}],"incoming":${JSON.stringify(list.incoming.map(card))},"outgoing":${JSON.stringify(list.outgoing.map(card))}}`);
			}

			case "POST friends/add": {
				const body = await readBody(req);
				const code = readCode(body.code);
				if (!code) fail(404, "not-found");
				const { profile } = await me();
				if (code === profile.code) fail(409, "self");
				const other = await store.relation(profile.id, { code: code as string });
				if (!other) return fail(404, "not-found");
				if (other.areFriends) fail(409, "already-friends");
				const full = other.myFriends >= SOCIAL.maxFriends || other.theirFriends >= SOCIAL.maxFriends;
				if (other.incoming) {
					// They asked first: adding their code accepts.
					if (full || !(await store.befriend(profile.id, other.id, "code", other.id)).friends) fail(429, "limit");
					return json(200, { status: "friends" });
				}
				if (other.outgoing) return json(200, { status: "requested" });
				if (full || other.myOutgoing >= SOCIAL.maxOutgoingRequests || !(await store.requestFriend(profile.id, other.id))) fail(429, "limit");
				return json(200, { status: "requested" });
			}

			case "POST friends/accept": {
				const body = await readBody(req);
				const from = playerId(body.id);
				if (!from) return fail(404, "not-found");
				const { profile } = await me();
				const other = await store.relation(profile.id, { id: from });
				if (other?.areFriends) return json(200, { status: "friends" });
				if (!other?.incoming) return fail(404, "not-found");
				if (other.myFriends >= SOCIAL.maxFriends || other.theirFriends >= SOCIAL.maxFriends) fail(429, "limit");
				if (!(await store.befriend(profile.id, other.id, "code", other.id)).friends) fail(429, "limit");
				return json(200, { status: "friends" });
			}

			case "POST friends/decline": {
				const body = await readBody(req);
				const from = playerId(body.id);
				const { profile } = await me();
				if (from) await store.declineFriend(profile.id, from);
				return json(204, null);
			}

			case "DELETE friends/:id": {
				const other = playerId(parts[1]);
				const { profile } = await me();
				if (other) await store.removeFriend(profile.id, other);
				return json(204, null);
			}

			case "GET friends/:id/market": {
				const friendId = playerId(parts[1]);
				const { profile } = await me();
				const visit = friendId ? await store.friendMarket(profile.id, friendId) : null;
				if (!visit) return fail(403, "not-friends");
				const found = visit.save ? await store.readSave(visit.friend.id, visit.save) : null;
				if (!found) return fail(404, "no-save");
				// {"profile":Friend,"public":…,"data":<the stored string literal>} — the save is not re-encoded.
				const head = `{"profile":${friendJson(visit.friend, visit.requests)},"public":${visit.friend.publicJson ?? "null"},"data":`;
				return new Response(new Blob([head, found.body, "}"]), { status: 200, headers: JSON_HEADERS });
			}

			case "POST report": {
				const body = await readBody(req);
				const target = playerId(body.id);
				if (!target) return fail(404, "not-found");
				const { profile } = await me();
				if (target !== profile.id && !(await store.reportName(profile.id, target))) fail(404, "not-found");
				return json(204, null);
			}

			case "POST gift":
			case "POST like": {
				const body = await readBody(req);
				const to = playerId(body.to);
				const { profile } = await me();
				if (!to || to === profile.id) return fail(403, "not-friends");
				const done = await store.daily(parts[0] as "gift" | "like", profile.id, to);
				if (done.result === "not-friends") fail(403, "not-friends");
				if (done.result === "already-today") fail(409, "already-today");
				return parts[0] === "gift" ? json(204, null) : json(200, { likes: done.likes });
			}

			case "POST help": {
				const body = await readBody(req);
				const to = playerId(body.to);
				const buildId = typeof body.buildId === "string" && body.buildId.length > 0 && body.buildId.length <= 100 ? body.buildId : null;
				const { profile } = await me();
				if (!to || to === profile.id) return fail(403, "not-friends");
				const target = await store.helpTarget(profile.id, to);
				if (!target.friends) fail(403, "not-friends");
				if (!buildId || !buildIds(target.publicJson).includes(buildId)) fail(404, "no-build");
				const done = await store.help(profile.id, to, buildId as string);
				if (done.ok) return json(200, { helps: done.helps });
				return fail(done.error === "not-friends" ? 403 : done.error === "daily-limit" ? 429 : 409, done.error);
			}

			case "GET requests": {
				const { profile } = await me();
				const lists = await store.requestsFor(profile.id);
				return json(200, { mine: lists.mine.map(request), friends: lists.friends.map((r) => ({ ...request(r), owner: r.owner })) });
			}

			case "POST requests": {
				const body = await readBody(req);
				const { productId, qty } = body;
				if (typeof productId !== "string" || !PRODUCT_ID.test(productId)) fail(400, "bad-request");
				if (typeof qty !== "number" || !Number.isInteger(qty) || qty < SOCIAL.minRequestQty || qty > SOCIAL.maxRequestQty) fail(400, "bad-request");
				const { profile } = await me();
				const created = await store.createRequest(profile.id, productId as string, qty as number);
				if (!created) return fail(429, "limit");
				return json(200, request(created));
			}

			case "DELETE requests/:id":
			case "POST requests/:id/fulfill": {
				const id = /^[1-9]\d{0,15}$/.test(parts[1]) ? Number(parts[1]) : 0;
				const { profile } = await me();
				if (!id) return fail(404, "not-found");
				if (method === "DELETE") {
					if (!(await store.cancelRequest(profile.id, id))) fail(404, "not-found");
					return json(204, null);
				}
				const result = await store.fulfillRequest(profile.id, id);
				if (result === "ok") return json(204, null);
				return fail(result === "not-found" ? 404 : result === "not-friends" ? 403 : 409, result);
			}

			case "GET inbox": {
				const { profile } = await me();
				const items = await store.inbox(profile.id);
				return raw(200, `{"items":[${items.map(inboxJson).join(",")}]}`);
			}

			case "POST inbox/ack": {
				const body = await readBody(req);
				const ids = body.ids;
				if (!Array.isArray(ids) || ids.length > SOCIAL.maxAckIds || !ids.every((id) => Number.isSafeInteger(id) && id > 0)) fail(400, "bad-request");
				const { profile } = await me();
				if ((ids as number[]).length) await store.ackInbox(profile.id, ids as number[]);
				return json(204, null);
			}

			case "POST invite/redeem": {
				const body = await readBody(req);
				const code = readCode(body.code);
				if (!code) return fail(404, "not-found");
				const mine = await me();
				const { profile } = mine;
				if (code === profile.code) fail(409, "self");
				if (profile.invitedBy !== null) fail(409, "already-invited");
				if (options.now() - mine.accountCreatedAt >= SOCIAL.inviteRedeemWindowMs) fail(409, "too-late");
				const inviter = await store.relation(profile.id, { code });
				if (!inviter) return fail(404, "not-found");
				// Two new accounts inviting each other would both be rewarded twice: a code of someone I invited is "self".
				if (inviter.invitedBy === profile.id) fail(409, "self");
				const redeemed = await store.redeemInvite(profile.id, inviter.id);
				if (!redeemed.claimed) fail(409, "already-invited");
				options.log(`invite ${profile.id} <- ${inviter.id}`);
				return json(200, { status: redeemed.friends ? "friends" : "invited" });
			}
		}
		return null;
	};
}
