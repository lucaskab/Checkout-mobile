import type { D1Database } from "./cf.ts";
import { b64url } from "./tokens.ts";

/**
 * Push notifications (Lucas 06/11: "Tanto locais quanto push notification"), through Firebase Cloud Messaging
 * (HTTP v1, project checkout-game). The game (CheckoutFirebase + CheckoutSocial) sends its device token, language and
 * the push kinds the player left on in Opções › Avisos (PUT /v1/push). Whatever lands in a player's social inbox
 * (a friend request, a gift, a help, a delivery, the week's league result...) becomes one notification per player
 * per flush: the inbox rows are claimed (inbox.pushed_at) right after the social call that wrote them, and after the
 * weekly league close. The inbox stays the truth; a push is only the nudge to open the game.
 * Secret FCM_SERVICE_ACCOUNT: the JSON key of a service account of the project with the role "Firebase Cloud
 * Messaging API Admin" (Lucas pastes it in Workers › checkout-server › Settings › Variables and Secrets).
 * Before migration 0005 (push_devices, inbox.pushed_at) every push call quietly does nothing.
 */

export type PushCategory = "amigos" | "eventos";
export const PUSH_CATEGORIES: PushCategory[] = ["amigos", "eventos"];
const LANGS = ["pt", "en", "es", "fr", "de"] as const;
type Lang = (typeof LANGS)[number];

/** How many inbox rows one flush claims (and the age past which a row is never pushed: it was read in the game). */
// Workers Free: at most 50 outgoing fetches per invocation (the OAuth token + one per device), so one flush sends to
// at most MAX_SENDS devices; what is left goes out with the next flush (the next social call, or the 10-min cron).
const FLUSH_ROWS = 20;
export const MAX_SENDS = 30;
const MAX_AGE_MS = 60 * 60_000;
/** The week's league result can wait longer (thousands land at once on Monday; the cron sends them in batches). */
const LEAGUE_MAX_AGE_MS = 24 * 3600_000;
const MAX_DEVICES_PER_PLAYER = 5;

export type ServiceAccount = { projectId: string; clientEmail: string; privateKey: string };

export function readServiceAccount(json: string | undefined): ServiceAccount | null {
	if (!json) return null;
	try {
		const key = JSON.parse(json);
		if (typeof key.project_id !== "string" || typeof key.client_email !== "string" || typeof key.private_key !== "string") return null;
		return { projectId: key.project_id, clientEmail: key.client_email, privateKey: key.private_key.replace(/\\n/g, "\n") };
	} catch {
		return null;
	}
}

export type PushMessage = { title: string; body: string; data?: Record<string, string> };
export type SendResult = "ok" | "gone" | "error";
export type Sender = (token: string, message: PushMessage) => Promise<SendResult>;

/** FCM HTTP v1 with a service account: an OAuth token (RS256 JWT, kept until 5 min before it expires). */
export function fcmSender(account: ServiceAccount, fetcher: typeof fetch = fetch, now: () => number = Date.now, log: (line: string) => void = () => {}): Sender {
	let access: { token: string; until: number } | null = null;
	let key: CryptoKey | null = null;

	const accessToken = async () => {
		if (access && access.until > now()) return access.token;
		if (!key) {
			const pem = account.privateKey.replace(/-----[^-]+-----/g, "").replace(/\s+/g, "");
			const der = Uint8Array.from(atob(pem), (c) => c.charCodeAt(0));
			key = await crypto.subtle.importKey("pkcs8", der, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["sign"]);
		}
		const iat = Math.floor(now() / 1000);
		const head = b64url(JSON.stringify({ alg: "RS256", typ: "JWT" }));
		const claims = b64url(
			JSON.stringify({ iss: account.clientEmail, scope: "https://www.googleapis.com/auth/firebase.messaging", aud: "https://oauth2.googleapis.com/token", iat, exp: iat + 3600 }),
		);
		const signature = await crypto.subtle.sign("RSASSA-PKCS1-v1_5", key, new TextEncoder().encode(`${head}.${claims}`));
		const response = await fetcher("https://oauth2.googleapis.com/token", {
			method: "POST",
			headers: { "content-type": "application/x-www-form-urlencoded" },
			body: `grant_type=${encodeURIComponent("urn:ietf:params:oauth:grant-type:jwt-bearer")}&assertion=${head}.${claims}.${b64url(signature)}`,
		});
		const answer = (await response.json().catch(() => ({}))) as { access_token?: string; expires_in?: number };
		if (!response.ok || !answer.access_token) {
			log(`push: oauth refused (${response.status})`);
			return null;
		}
		access = { token: answer.access_token, until: now() + Math.max(60, (answer.expires_in ?? 3600) - 300) * 1000 };
		return access.token;
	};

	return async (token, message) => {
		const bearer = await accessToken();
		if (!bearer) return "error";
		const response = await fetcher(`https://fcm.googleapis.com/v1/projects/${account.projectId}/messages:send`, {
			method: "POST",
			headers: { "content-type": "application/json", authorization: `Bearer ${bearer}` },
			body: JSON.stringify({
				message: {
					token,
					notification: { title: message.title, body: message.body },
					data: message.data ?? {},
					android: { priority: "high", notification: { channel_id: "checkout" } },
					apns: { payload: { aps: { sound: "default" } } },
				},
			}),
		});
		if (response.ok) return "ok";
		const text = await response.text().catch(() => "");
		// The app was uninstalled or the token was replaced: forget the device.
		if (response.status === 404 || /UNREGISTERED|registration-token-not-registered|INVALID_ARGUMENT.*token/i.test(text)) return "gone";
		if (response.status === 401) access = null;
		log(`push: send failed (${response.status})`);
		return "error";
	};
}

// ── Devices ────────────────────────────────────────────────────────────────────────────────────────────────────

const missing = (error: unknown) => /no such (table|column): (push_devices|pushed_at)/i.test(String((error as Error)?.message ?? error));

export function readDevice(body: Record<string, unknown>) {
	const token = typeof body.token === "string" ? body.token.trim() : "";
	if (!token || token.length > 4096 || /\s/.test(token)) return null;
	const platform = body.platform === "ios" || body.platform === "android" ? body.platform : null;
	if (!platform) return null;
	const lang: Lang = (LANGS as readonly string[]).includes(String(body.lang)) ? (body.lang as Lang) : "en";
	const wanted = Array.isArray(body.categories) ? body.categories : typeof body.categories === "string" ? body.categories.split(",") : [];
	const categories = PUSH_CATEGORIES.filter((c) => wanted.includes(c));
	return { token, platform, lang, categories };
}

/** Saves (or moves to this player) a device; a player keeps at most a few (the newest). */
export async function registerDevice(db: D1Database, playerId: string, device: NonNullable<ReturnType<typeof readDevice>>, now: number) {
	try {
		await db.batch([
			db
				.prepare(
					`INSERT INTO push_devices (token, player_id, platform, lang, categories, updated_at) VALUES (?, ?, ?, ?, ?, ?)
					 ON CONFLICT (token) DO UPDATE SET player_id = excluded.player_id, platform = excluded.platform, lang = excluded.lang,
					   categories = excluded.categories, updated_at = excluded.updated_at`,
				)
				.bind(device.token, playerId, device.platform, device.lang, device.categories.join(","), now),
			db
				.prepare(
					`DELETE FROM push_devices WHERE player_id = ? AND token NOT IN
					   (SELECT token FROM push_devices WHERE player_id = ? ORDER BY updated_at DESC LIMIT ${MAX_DEVICES_PER_PLAYER})`,
				)
				.bind(playerId, playerId),
		]);
		return true;
	} catch (error) {
		if (missing(error)) return false;
		throw error;
	}
}

export async function removeDevice(db: D1Database, playerId: string, token: string) {
	try {
		await db.prepare("DELETE FROM push_devices WHERE token = ? AND player_id = ?").bind(token, playerId).run();
	} catch (error) {
		if (!missing(error)) throw error;
	}
}

export async function removePlayerDevices(db: D1Database, playerId: string) {
	try {
		await db.prepare("DELETE FROM push_devices WHERE player_id = ?").bind(playerId).run();
	} catch (error) {
		if (!missing(error)) throw error;
	}
}

// ── Texts ──────────────────────────────────────────────────────────────────────────────────────────────────────

type Text = { title: string; one: string; many: string; anon?: string };
const T: Record<string, Record<Lang, Text>> = {
	friend_request: {
		pt: { title: "Pedido de amizade", one: "{name} quer ser seu amigo no Checkout.", anon: "Alguém quer ser seu amigo no Checkout.", many: "Você tem {n} pedidos de amizade." },
		en: { title: "Friend request", one: "{name} wants to be your friend on Checkout.", anon: "Someone wants to be your friend on Checkout.", many: "You have {n} friend requests." },
		es: { title: "Solicitud de amistad", one: "{name} quiere ser tu amigo en Checkout.", anon: "Alguien quiere ser tu amigo en Checkout.", many: "Tienes {n} solicitudes de amistad." },
		fr: { title: "Demande d'ami", one: "{name} veut être ton ami sur Checkout.", anon: "Quelqu'un veut être ton ami sur Checkout.", many: "Tu as {n} demandes d'ami." },
		de: { title: "Freundschaftsanfrage", one: "{name} möchte dein Freund bei Checkout sein.", anon: "Jemand möchte dein Freund bei Checkout sein.", many: "Du hast {n} Freundschaftsanfragen." },
	},
	friend_added: {
		pt: { title: "Novo amigo!", one: "{name} agora é seu amigo. Vá visitar o mercado!", anon: "Você tem um novo amigo. Vá visitar o mercado!", many: "Você tem {n} novos amigos." },
		en: { title: "New friend!", one: "{name} is now your friend. Go visit their market!", anon: "You have a new friend. Go visit their market!", many: "You have {n} new friends." },
		es: { title: "¡Nuevo amigo!", one: "{name} ahora es tu amigo. ¡Visita su mercado!", anon: "Tienes un nuevo amigo. ¡Visita su mercado!", many: "Tienes {n} amigos nuevos." },
		fr: { title: "Nouvel ami !", one: "{name} est maintenant ton ami. Va visiter son magasin !", anon: "Tu as un nouvel ami. Va visiter son magasin !", many: "Tu as {n} nouveaux amis." },
		de: { title: "Neuer Freund!", one: "{name} ist jetzt dein Freund. Besuch den Markt!", anon: "Du hast einen neuen Freund. Besuch den Markt!", many: "Du hast {n} neue Freunde." },
	},
	gift: {
		pt: { title: "Presente de amigo", one: "{name} te mandou um presente. Venha abrir!", anon: "Um amigo te mandou um presente. Venha abrir!", many: "Seus amigos te mandaram {n} presentes." },
		en: { title: "Gift from a friend", one: "{name} sent you a gift. Come open it!", anon: "A friend sent you a gift. Come open it!", many: "Your friends sent you {n} gifts." },
		es: { title: "Regalo de un amigo", one: "{name} te envió un regalo. ¡Ven a abrirlo!", anon: "Un amigo te envió un regalo. ¡Ven a abrirlo!", many: "Tus amigos te enviaron {n} regalos." },
		fr: { title: "Cadeau d'un ami", one: "{name} t'a envoyé un cadeau. Viens l'ouvrir !", anon: "Un ami t'a envoyé un cadeau. Viens l'ouvrir !", many: "Tes amis t'ont envoyé {n} cadeaux." },
		de: { title: "Geschenk von einem Freund", one: "{name} hat dir ein Geschenk geschickt. Mach es auf!", anon: "Ein Freund hat dir ein Geschenk geschickt. Mach es auf!", many: "Deine Freunde haben dir {n} Geschenke geschickt." },
	},
	like: {
		pt: { title: "Curtiram seu mercado", one: "{name} curtiu o seu mercado!", anon: "Um amigo curtiu o seu mercado!", many: "Seu mercado ganhou {n} curtidas." },
		en: { title: "Your market got a like", one: "{name} liked your market!", anon: "A friend liked your market!", many: "Your market got {n} likes." },
		es: { title: "Le gustó tu mercado", one: "¡A {name} le gustó tu mercado!", anon: "¡A un amigo le gustó tu mercado!", many: "Tu mercado recibió {n} me gusta." },
		fr: { title: "On aime ton magasin", one: "{name} a aimé ton magasin !", anon: "Un ami a aimé ton magasin !", many: "Ton magasin a reçu {n} j'aime." },
		de: { title: "Dein Markt gefällt", one: "{name} gefällt dein Markt!", anon: "Einem Freund gefällt dein Markt!", many: "Dein Markt hat {n} Likes bekommen." },
	},
	help: {
		pt: { title: "Ajuda na obra", one: "{name} ajudou a acelerar a sua obra!", anon: "Um amigo ajudou a acelerar a sua obra!", many: "Seus amigos ajudaram {n} vezes nas suas obras." },
		en: { title: "Help with construction", one: "{name} helped speed up your construction!", anon: "A friend helped speed up your construction!", many: "Your friends helped {n} times with your construction." },
		es: { title: "Ayuda en la obra", one: "¡{name} ayudó a acelerar tu obra!", anon: "¡Un amigo ayudó a acelerar tu obra!", many: "Tus amigos ayudaron {n} veces en tus obras." },
		fr: { title: "Aide au chantier", one: "{name} a aidé à accélérer ton chantier !", anon: "Un ami a aidé à accélérer ton chantier !", many: "Tes amis ont aidé {n} fois sur tes chantiers." },
		de: { title: "Hilfe beim Bau", one: "{name} hat deinen Bau beschleunigt!", anon: "Ein Freund hat deinen Bau beschleunigt!", many: "Deine Freunde haben {n}-mal beim Bau geholfen." },
	},
	delivery: {
		pt: { title: "Pedido atendido", one: "{name} mandou o produto que você pediu!", anon: "Um amigo mandou o produto que você pediu!", many: "Seus amigos mandaram {n} produtos que você pediu." },
		en: { title: "Request filled", one: "{name} sent the product you asked for!", anon: "A friend sent the product you asked for!", many: "Your friends sent {n} products you asked for." },
		es: { title: "Pedido atendido", one: "¡{name} envió el producto que pediste!", anon: "¡Un amigo envió el producto que pediste!", many: "Tus amigos enviaron {n} productos que pediste." },
		fr: { title: "Demande remplie", one: "{name} a envoyé le produit que tu as demandé !", anon: "Un ami a envoyé le produit que tu as demandé !", many: "Tes amis ont envoyé {n} produits demandés." },
		de: { title: "Anfrage erfüllt", one: "{name} hat das gewünschte Produkt geschickt!", anon: "Ein Freund hat das gewünschte Produkt geschickt!", many: "Deine Freunde haben {n} gewünschte Produkte geschickt." },
	},
	invite_reward: {
		pt: { title: "Prêmio de convite", one: "O seu convite deu prêmio! Venha pegar.", many: "Você ganhou {n} prêmios de convite. Venha pegar." },
		en: { title: "Invite reward", one: "Your invite earned a reward! Come and claim it.", many: "You earned {n} invite rewards. Come and claim them." },
		es: { title: "Premio por invitación", one: "¡Tu invitación dio premio! Ven a recogerlo.", many: "Ganaste {n} premios por invitación. Ven a recogerlos." },
		fr: { title: "Récompense d'invitation", one: "Ton invitation t'a rapporté une récompense ! Viens la récupérer.", many: "Tu as gagné {n} récompenses d'invitation. Viens les récupérer." },
		de: { title: "Einladungsbelohnung", one: "Deine Einladung hat sich gelohnt! Hol dir die Belohnung.", many: "Du hast {n} Einladungsbelohnungen bekommen. Hol sie dir." },
	},
	league_reward: {
		pt: { title: "A liga da semana fechou", one: "Veja a sua colocação e pegue o seu prêmio!", many: "Veja a sua colocação e pegue o seu prêmio!" },
		en: { title: "This week's league is over", one: "See where you placed and claim your reward!", many: "See where you placed and claim your reward!" },
		es: { title: "La liga de la semana cerró", one: "¡Mira tu puesto y recoge tu premio!", many: "¡Mira tu puesto y recoge tu premio!" },
		fr: { title: "La ligue de la semaine est terminée", one: "Regarde ton classement et récupère ta récompense !", many: "Regarde ton classement et récupère ta récompense !" },
		de: { title: "Die Wochenliga ist vorbei", one: "Sieh dir deinen Platz an und hol deine Belohnung!", many: "Sieh dir deinen Platz an und hol deine Belohnung!" },
	},
};
const MIXED: Record<Lang, Text> = {
	pt: { title: "Novidades dos amigos", one: "", many: "Você tem {n} novidades dos seus amigos no Checkout." },
	en: { title: "News from friends", one: "", many: "You have {n} updates from your friends on Checkout." },
	es: { title: "Novedades de amigos", one: "", many: "Tienes {n} novedades de tus amigos en Checkout." },
	fr: { title: "Nouvelles des amis", one: "", many: "Tu as {n} nouvelles de tes amis sur Checkout." },
	de: { title: "Neues von Freunden", one: "", many: "Du hast {n} Neuigkeiten von deinen Freunden bei Checkout." },
};
/** The inbox kinds that become a push, and their category in Opções › Avisos. */
const KIND_CATEGORY: Record<string, PushCategory> = {
	friend_request: "amigos",
	friend_added: "amigos",
	gift: "amigos",
	like: "amigos",
	help: "amigos",
	delivery: "amigos",
	invite_reward: "amigos",
	league_reward: "amigos",
};

/** The one notification for a player's new inbox rows (same kind: that kind's text; mixed: a count). */
export function pushText(rows: { kind: string; name: string | null }[], lang: string): PushMessage | null {
	const l: Lang = (LANGS as readonly string[]).includes(lang) ? (lang as Lang) : "en";
	const kinds = [...new Set(rows.map((r) => r.kind))];
	if (!rows.length) return null;
	if (kinds.length > 1) return { title: MIXED[l].title, body: MIXED[l].many.replace("{n}", String(rows.length)), data: { kind: "mixed" } };
	const text = T[kinds[0]]?.[l];
	if (!text) return null;
	if (rows.length > 1) return { title: text.title, body: text.many.replace("{n}", String(rows.length)), data: { kind: kinds[0] } };
	const name = rows[0].name?.trim();
	return { title: text.title, body: name ? text.one.replace("{name}", name) : (text.anon ?? text.one), data: { kind: kinds[0] } };
}

// ── Flush ──────────────────────────────────────────────────────────────────────────────────────────────────────

/**
 * Claims the inbox rows not pushed yet (at most FLUSH_ROWS, younger than an hour — a day for the league —, not read
 * in the game, of players with a device) and sends one
 * notification per player to each of their devices that has the category on. Returns how many rows it claimed.
 */
export async function flushPush(db: D1Database, send: Sender | null, now: number, log: (line: string) => void = () => {}) {
	if (!send) return 0;
	let claimed: { player_id: string; kind: string; name: string | null }[];
	try {
		const kinds = Object.keys(KIND_CATEGORY).map((k) => `'${k}'`).join(",");
		const result = await db
			.prepare(
				`UPDATE inbox SET pushed_at = ?1 WHERE id IN (
				   SELECT id FROM inbox WHERE pushed_at IS NULL AND acked_at IS NULL AND (created_at > ?2 OR (kind = 'league_reward' AND created_at > ?3)) AND kind IN (${kinds})
				   AND player_id IN (SELECT player_id FROM push_devices) ORDER BY id LIMIT ${FLUSH_ROWS})
				 RETURNING player_id, kind, (SELECT CASE WHEN p.name_hidden = 1 THEN NULL ELSE p.market_name END FROM profiles p WHERE p.player_id = inbox.from_id) AS name`,
			)
			.bind(now, now - MAX_AGE_MS, now - LEAGUE_MAX_AGE_MS)
			.all<{ player_id: string; kind: string; name: string | null }>();
		claimed = result.results;
	} catch (error) {
		if (missing(error)) return 0;
		throw error;
	}
	if (!claimed.length) return 0;
	const byPlayer = new Map<string, { kind: string; name: string | null }[]>();
	for (const row of claimed) {
		const list = byPlayer.get(row.player_id) ?? [];
		list.push({ kind: row.kind, name: row.name });
		byPlayer.set(row.player_id, list);
	}
	const devices = await db
		.prepare(`SELECT token, player_id, lang, categories FROM push_devices WHERE player_id IN (SELECT value FROM json_each(?))`)
		.bind(JSON.stringify([...byPlayer.keys()]))
		.all<{ token: string; player_id: string; lang: string; categories: string }>();
	let sent = 0;
	const gone: string[] = [];
	await Promise.all(
		devices.results.slice(0, MAX_SENDS).map(async (device) => {
			const on = new Set(device.categories.split(","));
			const rows = (byPlayer.get(device.player_id) ?? []).filter((r) => on.has(KIND_CATEGORY[r.kind]));
			const message = pushText(rows, device.lang);
			if (!message) return;
			const result = await send(device.token, message).catch(() => "error" as const);
			if (result === "ok") sent++;
			else if (result === "gone") gone.push(device.token);
		}),
	);
	if (gone.length) await db.prepare("DELETE FROM push_devices WHERE token IN (SELECT value FROM json_each(?))").bind(JSON.stringify(gone)).run();
	if (sent || gone.length) log(`push: ${sent} sent, ${gone.length} gone`);
	return claimed.length;
}
