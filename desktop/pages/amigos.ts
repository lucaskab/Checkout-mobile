import type { Routes } from ".";
import type { SocialLogEntry } from "@/@types/social";
import { getInteriorDecor } from "@/data/interior-decor";
import { itemCatalog } from "@/data/market-products";
import {
	inviteRewardDecorId,
	SOCIAL_HELPS_PER_DAY,
	SOCIAL_INVITE_MILESTONES,
	SOCIAL_REQUEST_MAX,
	SOCIAL_REQUEST_MIN,
	SOCIAL_REQUESTS_OPEN,
} from "@/data/social";
import { normalizeSocialState } from "@/services/social";
import { cloudStore, formatAgo } from "../cloud";
import { qrText } from "../qr";
import {
	avatarIcon,
	formatCode,
	helpableBuilds,
	inviteUrl,
	likesText,
	marketName,
	sendableStock,
	socialHelpsToday,
	socialIcon,
	socialStore,
	stageIcon,
	stageName,
	toastText,
	type SocialFriend,
	type SocialPerson,
	type SocialRequestView,
} from "../social";
import {
	act,
	board,
	type BoardTile,
	button,
	type Button,
	type Card,
	card,
	decorIcon,
	fmt,
	go,
	meter,
	page,
	type Page,
	productIcon,
	stat,
	type State,
	tile,
} from "../view-kit";
import { contractShortfall } from "./day";

// Amigos (social v1, docs/social-api.md) as full-screen game windows (Lucas 02/11: "use a tela inteira, como a Loja"),
// with big header tabs: Amigos (my card, the daily helps meter and a grid of friend cards), Pedidos (product
// requests, mine and the friends'), Convidar (my code, the QR and the reward ladder of the exclusive decorations) and
// Correio (gift boxes to open, the history of what friends did). The friend's Pedidos during a visit, the product
// picker and the profile (market name + face) use the same window.

const NAVY = "1D2B4F";
const DAY_MS = 24 * 3_600_000;
const productName = (id: number) => itemCatalog.find((item) => item.id === id)?.name ?? "";
const hoursLeft = (request: SocialRequestView, now: number) => Math.max(1, Math.ceil((request.expiresAt - now) / 3_600_000));
const online = () => socialStore.signedIn || socialStore.mock;
const busy = (key: string) => socialStore.busy.has(key);
const social = (state: State) => normalizeSocialState(state.social);

type Tab = "amigos" | "pedidos" | "convidar" | "correio";

/** The four big tabs, with red counts like the other windows. */
function sections(state: State, active: Tab): Button[] {
	const now = Date.now();
	const mine = social(state);
	const fulfil = friendRequests(now).filter((request) => sendableStock(request.productId) >= request.qty).length;
	const tabs: { id: Tab; label: string; icon: string; route: string; badge: number }[] = [
		{ id: "amigos", label: "Amigos", icon: socialIcon("friends"), route: "!amigos", badge: socialStore.incoming.length },
		{ id: "pedidos", label: "Pedidos", icon: socialIcon("package"), route: "!amigos-pedidos", badge: fulfil },
		{ id: "convidar", label: "Convidar", icon: socialIcon("invite"), route: "!amigos-convidar", badge: socialStore.offeredCode ? 1 : 0 },
		{ id: "correio", label: "Correio", icon: socialIcon("gift"), route: "!amigos-correio", badge: mine.mailbox.length },
	];
	return tabs.map((tab) =>
		button(tab.label, { icon: tab.icon, route: tab.route, variant: tab.id === active ? "coin" : "secondary", active: tab.id === active, badge: tab.badge > 0 ? String(tab.badge) : "" }),
	);
}

/** One full-screen social window: navy header, the four tabs, big cards over the tiles. */
function boardPage(state: State, route: string, title: string, active: Tab | null, cards: Card[], tiles: BoardTile[], options: Parameters<typeof board>[1] = {}, extra: Partial<Page> = {}) {
	return page(route, title, cards, {
		icon: socialIcon("friends"),
		layout: "board",
		sections: active ? sections(state, active) : [],
		board: board(tiles, { tint: NAVY, columns: 4, ...options }),
		...extra,
	});
}

// ------------------------------------------------------------------------------------------------------------ states

function signedOutCard(): Card {
	const providers = cloudStore.providers.length ? cloudStore.providers : ["google" as const];
	const canSignIn = cloudStore.status === "signed-out";
	return card("Entre para jogar com amigos", {
		icon: socialIcon("friends"),
		eyebrow: "AMIGOS",
		tone: cloudStore.status === "unavailable" ? "locked" : "info",
		lines: ["Visite o mercado dos amigos, mande presentes, ajude nas obras e peça produtos.", "Sua conta também guarda o seu progresso na nuvem."],
		buttons:
			cloudStore.status === "unavailable"
				? []
				: providers.map((provider) =>
						act(cloudStore.status === "signing-in" ? "Entrando…" : provider === "apple" ? "Iniciar sessão com a Apple" : "Entrar com Google", "cloudSignIn", [provider], {
							variant: provider === "apple" ? "secondary" : "success",
							enabled: canSignIn,
							ok: provider === "apple" ? "Abrindo o login da Apple…" : "Abrindo o login do Google…",
						}),
					),
	});
}

/** Signed out, loading, an error, or the first-time profile: what every tab shows before the real content. */
function gate(state: State, route: string, active: Tab): Page | null {
	if (!online()) return boardPage(state, route, "Amigos", null, [signedOutCard()], [], { empty: "Entre na sua conta para ver os amigos." });
	const me = socialStore.me;
	if (!me) {
		const failed = Boolean(socialStore.error);
		return boardPage(
			state,
			route,
			"Amigos",
			null,
			[
				failed
					? card("Não deu para carregar os amigos", {
							icon: socialIcon("warning"),
							tone: "warning",
							lines: [socialStore.error],
							buttons: [act("Tentar de novo", "socialRefresh", [], { ok: "" })],
						})
					: card("Carregando os amigos…", { icon: socialIcon("friends") }),
			],
			[],
			{ empty: "" },
		);
	}
	// First time (no name yet) or a reported name: the profile comes first.
	if (!me.marketName || me.nameHidden) return profilePage(state, true);
	void active;
	return null;
}

// ------------------------------------------------------------------------------------------------------------ profile

function profilePage(state: State, required: boolean): Page {
	const me = socialStore.me!;
	const hidden = me.nameHidden;
	const first = !me.marketName;
	const chosen = socialStore.draft.avatar || me.avatar || "";
	const ids = Array.from({ length: socialStore.avatars }, (_, i) => `shopper-${i + 1}`);
	const tiles = ids.map((id, index) =>
		tile(id, `Rosto ${index + 1}`, {
			icon: avatarIcon(id),
			frame: "portrait",
			tone: id === chosen ? "gold" : "",
			state: id === chosen ? "done" : "",
			sticker: id === chosen ? "ESCOLHIDO" : "",
			action: act(id === chosen ? "Escolhido" : "Escolher", "socialPickAvatar", [id], { variant: id === chosen ? "coin" : "secondary", ok: "" }),
			detail: "Este é o rosto que os seus amigos veem no seu cartão.",
			actions: [act("Escolher este rosto", "socialPickAvatar", [id], { variant: "success", ok: "" })],
		}),
	);
	const hero = card(first ? "Dê um nome ao seu mercado" : hidden ? "Escolha outro nome" : marketName(me), {
		icon: avatarIcon(chosen),
		eyebrow: first ? "PRIMEIRA VEZ AQUI" : "SEU PERFIL",
		tone: hidden ? "warning" : "",
		// (not the big hero title: on a phone the faces stay above the fold under the card)
		// (first time: the title says it; the faces stay above the fold on a phone)
		lines: [
			first
				? ""
				: hidden
					? "O nome do seu mercado foi denunciado e está escondido. Os amigos veem só o código até você escolher outro."
					: "",
			"De 3 a 20 letras ou números. Nada de palavrões: nomes denunciados ficam escondidos.",
		].filter(Boolean),
		input: { id: "name", placeholder: "Nome do mercado", value: hidden ? "" : (me.marketName ?? ""), max: 20, kind: "name" },
		buttons: [
			act(busy("profile") ? "Salvando…" : "Salvar", "socialSaveProfile", ["$input:name", chosen], {
				icon: socialIcon("success"),
				variant: "success",
				enabled: !busy("profile") && Boolean(chosen),
				fail: "Escolha um rosto primeiro.",
				ok: "",
				after: required ? "" : "back",
			}),
		],
	});
	return boardPage(state, "amigos:perfil", required ? "Seu perfil" : "Perfil", required ? null : "amigos", [hero], tiles, {
		columns: 6,
		focus: chosen,
		empty: "",
		stats: [stat(socialIcon("like"), fmt(me.likes), "curtidas"), stat(socialIcon("friends"), fmt(socialStore.friends.length), "amigos")],
	});
}

// ------------------------------------------------------------------------------------------------------------ amigos

function friendChips(friend: SocialFriend, now: number) {
	const builds = helpableBuilds(friend, now);
	const requests = (friend.openRequests ?? []).filter((request) => request.expiresAt > now);
	return [
		stat(socialIcon("like"), fmt(friend.likes ?? 0), ""),
		...(builds.length ? [stat(socialIcon("handshake"), builds.length === 1 ? "1 obra para ajudar" : `${builds.length} obras para ajudar`, "", "success")] : []),
		...requests.slice(0, 1).map((request) => stat(productIcon(request.productId), `pede ${request.qty}× ${productName(request.productId)}`, "", "info")),
	];
}

function giftButton(friend: SocialFriend) {
	return act(friend.giftedToday ? "Enviado" : "Presente", "socialGift", [friend.id], {
		icon: friend.giftedToday ? socialIcon("success") : socialIcon("gift"),
		variant: friend.giftedToday ? "secondary" : "success",
		enabled: !friend.giftedToday && !busy(`gift:${friend.id}`),
		ok: "",
		fail: "Você já mandou um presente hoje. Volte amanhã!",
	});
}

function visitButton(friend: SocialFriend) {
	return act(busy(`visit-start:${friend.id}`) || busy(`visit:${friend.id}`) ? "Abrindo…" : "Visitar", "socialVisit", [friend.id], {
		icon: socialIcon("market"),
		variant: "primary",
		enabled: !busy(`visit-start:${friend.id}`),
		ok: "",
	});
}

function friendTile(friend: SocialFriend, now: number): BoardTile {
	const builds = helpableBuilds(friend, now);
	const requests = (friend.openRequests ?? []).filter((request) => request.expiresAt > now);
	const confirming = socialStore.confirmRemove === friend.id;
	return tile(friend.id, marketName(friend), {
		group: "Seus amigos",
		icon: avatarIcon(friend.avatar),
		frame: "portrait",
		corner: stageIcon(friend.era),
		subtitle: friend.lastSeen ? `Visto ${formatAgo(friend.lastSeen, now)}` : stageName(friend.era),
		sticker: `NV ${friend.level}`,
		tone: builds.length + requests.length > 0 ? "success" : "",
		state: builds.length ? "ready" : "",
		chips: friendChips(friend, now),
		action: visitButton(friend),
		alt: giftButton(friend),
		detail: [stageName(friend.era), likesText(friend.likes ?? 0)].filter(Boolean).join(" · "),
		facts: [
			stat(stageIcon(friend.era), String(friend.level), "nível"),
			stat(socialIcon("like"), fmt(friend.likes ?? 0), "curtidas"),
			stat(socialIcon("handshake"), String(builds.length), "obras"),
		],
		lines: [
			...requests.map((request) => `Pede ${request.qty}× ${productName(request.productId)} · ${hoursLeft(request, now)} h`),
			builds.length ? "Visite o mercado e toque em Ajudar em cada obra: −5 min para o amigo, moedas para você." : "",
		].filter(Boolean),
		actions: [
			visitButton(friend),
			giftButton(friend),
			act(friend.likedToday ? "Curtido hoje" : "Curtir", "socialLike", [friend.id], {
				icon: socialIcon("like"),
				variant: friend.likedToday ? "secondary" : "success",
				enabled: !friend.likedToday && !busy(`like:${friend.id}`),
				ok: "",
			}),
			act(confirming ? "Remover mesmo?" : "Remover amigo", "socialRemove", [friend.id], { variant: "danger", enabled: !busy(`remove:${friend.id}`), ok: "" }),
			act("Denunciar nome", "socialReport", [friend.id], { variant: "secondary", enabled: !busy(`report:${friend.id}`), ok: "" }),
		],
	});
}

function personTile(person: SocialPerson, incoming: boolean): BoardTile {
	return tile(`${incoming ? "in" : "out"}-${person.id}`, marketName(person), {
		group: incoming ? "Querem ser seus amigos" : "Esperando resposta",
		icon: avatarIcon(person.avatar),
		frame: "portrait",
		corner: stageIcon(person.era),
		subtitle: `Nível ${person.level} · ${stageName(person.era)}`,
		sticker: incoming ? "NOVO" : "",
		tone: incoming ? "info" : "locked",
		state: incoming ? "ready" : "",
		action: incoming
			? act("Aceitar", "socialAccept", [person.id], { icon: socialIcon("friends"), variant: "success", enabled: !busy(`accept:${person.id}`), ok: "" })
			: button("Esperando…", { variant: "secondary", enabled: false }),
		alt: incoming ? act("Recusar", "socialDecline", [person.id], { variant: "secondary", enabled: !busy(`decline:${person.id}`), ok: "" }) : button("", { enabled: false }),
		// (short: on a phone the side panel shows it whole, with Aceitar and Recusar under it)
		detail: incoming ? "Aceite para visitar, ajudar e trocar presentes." : "Pedido enviado. Falta o amigo aceitar.",
		actions: incoming
			? [
					act("Aceitar", "socialAccept", [person.id], { icon: socialIcon("friends"), variant: "success", enabled: !busy(`accept:${person.id}`), ok: "" }),
					act("Recusar", "socialDecline", [person.id], { variant: "secondary", enabled: !busy(`decline:${person.id}`), ok: "" }),
				]
			: [],
	});
}

/** My strip across the top of Amigos (the board's bar): my face (opens the profile), my code, Copiar / Convidar and
 * the helps of the day as a meter in blocks of five. */
function myStrip(helps: number) {
	const me = socialStore.me!;
	return meter(formatCode(me.code), helps, SOCIAL_HELPS_PER_DAY, {
		icon: avatarIcon(me.avatar),
		frame: "portrait",
		route: "amigos:perfil",
		tone: "gold",
		segments: SOCIAL_HELPS_PER_DAY / 5,
		text: `${marketName(me)} · Ajudas hoje ${helps}/${SOCIAL_HELPS_PER_DAY}`,
		buttons: [
			act("Copiar", "socialCopy", [], { variant: "secondary", ok: "" }),
			act("Convidar", "socialShare", [], { icon: socialIcon("share"), variant: "success", ok: "" }),
		],
	});
}

function addFriendCard(invite: boolean): Card {
	return card(invite ? "Tem um código de convite?" : "Adicionar amigo", {
		icon: socialIcon("friends"),
		eyebrow: "CÓDIGO DE UM AMIGO",
		lines: [invite ? "O código de um amigo, ou o convite de quem te chamou (vocês ganham 30 diamantes no Späti)." : "Digite o código de amigo (8 letras e números)."],
		input: { id: "code", placeholder: "Ex.: K7Q2-MX4P", value: "", max: 9, kind: "code" },
		buttons: [
			act(busy("add") ? "Enviando…" : "Adicionar", "socialAddFriend", ["$input:code"], { icon: socialIcon("friends"), variant: "primary", enabled: !busy("add"), ok: "" }),
			// "Tem um código de convite?": the same field, used as the invite (first 7 days, once).
			...(invite ? [act(busy("redeem") ? "Enviando…" : "Usar como convite", "socialRedeem", ["$input:code"], { icon: socialIcon("invite"), variant: "secondary", enabled: !busy("redeem"), ok: "" })] : []),
		],
	});
}

function amigosPage(state: State): Page {
	const gated = gate(state, "amigos", "amigos");
	if (gated) return gated;
	const now = Date.now();
	const friends = [...socialStore.friends].sort(
		(a, b) => helpableBuilds(b, now).length + (b.openRequests?.length ?? 0) - (helpableBuilds(a, now).length + (a.openRequests?.length ?? 0)) || b.lastSeen - a.lastSeen,
	);
	const helps = Math.min(SOCIAL_HELPS_PER_DAY, socialHelpsToday());
	const toGift = friends.filter((friend) => !friend.giftedToday).length;
	const cards: Card[] = friends.length
		? []
		: [
				card("Jogue junto com os amigos!", {
					icon: socialIcon("friends"),
					eyebrow: "NENHUM AMIGO AINDA",
					tone: "gold",
					lines: ["Visitem o mercado um do outro, ajudem nas obras e mandem presentes.", "Quem entrar pelo seu convite e chegar ao Späti ganha 30 diamantes, e você também."],
					buttons: [act("Convidar amigos", "socialShare", [], { icon: socialIcon("share"), variant: "success", ok: "" })],
				}),
			];
	// The friends first (the whole first row on a phone), the requests at the end of the grid: a new one is also the
	// side panel's first pick, with Aceitar and Recusar.
	const tiles = [
		...friends.map((friend) => friendTile(friend, now)),
		...socialStore.incoming.map((person) => personTile(person, true)),
		...socialStore.outgoing.map((person) => personTile(person, false)),
	];
	const firstRequest = socialStore.incoming[0];
	return boardPage(state, "amigos", "Amigos", "amigos", cards, tiles, {
		focus: firstRequest ? `in-${firstRequest.id}` : "",
		stats: [stat(socialIcon("friends"), fmt(friends.length), "amigos"), stat(socialIcon("like"), fmt(socialStore.me!.likes), "curtidas")],
		meter: myStrip(helps),
		footer: [
			...(friends.length
				? [
						act(busy("gift-all") ? "Enviando…" : toGift ? `Mandar presente para todos (${toGift})` : "Presentes de hoje enviados", "socialGiftAll", [], {
							icon: toGift ? socialIcon("gift") : socialIcon("success"),
							variant: toGift ? "success" : "secondary",
							enabled: toGift > 0 && !busy("gift-all"),
							ok: "",
							fail: "Você já mandou presente para todos hoje.",
						}),
					]
				: []),
			go("Adicionar amigo", "!amigos-convidar:codigo", { icon: socialIcon("friends"), variant: "primary" }),
		],
		empty: "",
	});
}

// ------------------------------------------------------------------------------------------------------------ pedidos

/** The friends' open requests (from the friend list and the requests route), newest first, one per id. */
function friendRequests(now: number) {
	const seen = new Map<number, SocialRequestView & { owner: string }>();
	for (const friend of socialStore.friends) for (const request of friend.openRequests ?? []) seen.set(request.id, { ...request, owner: friend.id });
	for (const request of socialStore.requests.friends) if (request.owner && !seen.has(request.id)) seen.set(request.id, { ...request, owner: request.owner });
	return [...seen.values()].filter((request) => request.expiresAt > now).sort((a, b) => b.createdAt - a.createdAt);
}

function sendTile(request: SocialRequestView, owner: SocialFriend | undefined, now: number, group: string): BoardTile {
	const have = sendableStock(request.productId);
	const enough = have >= request.qty;
	const product = itemCatalog.find((item) => item.id === request.productId);
	const reward = product ? Math.max(1, Math.round(product.purchasePrice * request.qty * 1.25)) : 0;
	const send = act(busy(`send:${request.id}`) ? "Enviando…" : "Enviar", "socialSend", [request.id, owner?.id ?? request.owner ?? "", request.productId, request.qty], {
		icon: socialIcon("package"),
		variant: "success",
		enabled: enough && !busy(`send:${request.id}`),
		fail: `Faltam ${fmt(request.qty - have)} no seu estoque.`,
		ok: "",
	});
	return tile(`send-${request.id}`, `${request.qty}× ${productName(request.productId)}`, {
		group,
		icon: productIcon(request.productId),
		subtitle: owner ? marketName(owner) : "",
		badge: `+${fmt(reward)}`,
		sticker: enough ? "PODE ENVIAR" : "",
		tone: enough ? "success" : "locked",
		state: enough ? "ready" : "",
		chips: [stat(productIcon(request.productId), `você tem ${fmt(have)}`, "", enough ? "success" : "danger"), stat(socialIcon("coin"), `+${fmt(reward)} moedas`, "", "gold")],
		timerEnd: request.expiresAt,
		timerTotal: DAY_MS,
		action: send,
		detail: enough ? "Você recebe o preço do fornecedor de volta e mais 25%." : `Faltam ${fmt(request.qty - have)} no seu estoque.`,
		facts: [stat(productIcon(request.productId), fmt(have), "no estoque"), stat(socialIcon("coin"), `+${fmt(reward)}`, "moedas"), stat(socialIcon("package"), String(request.qty), "pedido")],
		lines: [owner ? `Pedido de ${marketName(owner)}` : "", `Vale por mais ${hoursLeft(request, now)} h`].filter(Boolean),
		actions: [send],
	});
}

function pedidosPage(state: State): Page {
	const gated = gate(state, "amigos-pedidos", "pedidos");
	if (gated) return gated;
	const now = Date.now();
	const mine = socialStore.requests.mine.filter((request) => request.expiresAt > now);
	const mineTiles = mine.map((request) => {
		const cancel = act("Cancelar", "socialCancelRequest", [request.id], { variant: "danger", enabled: !busy(`cancel:${request.id}`), ok: "" });
		return tile(`mine-${request.id}`, `${request.qty}× ${productName(request.productId)}`, {
			// (one group: mine and the friends' side by side, the ribbon says whose)
			group: "Pedidos abertos",
			sticker: "SEU PEDIDO",
			icon: productIcon(request.productId),
			subtitle: `Vale por mais ${hoursLeft(request, now)} h`,
			tone: "info",
			state: "busy",
			timerEnd: request.expiresAt,
			timerTotal: DAY_MS,
			fill: Math.max(0, Math.min(1, (request.expiresAt - now) / DAY_MS)),
			chips: [stat(productIcon(request.productId), `no estoque: ${fmt(state.inventory[request.productId] ?? 0)}`, "")],
			action: cancel,
			detail: "Um amigo manda tudo de uma vez, direto para o seu estoque.",
			actions: [cancel],
		});
	});
	const theirs = friendRequests(now).map((request) =>
		sendTile(
			request,
			socialStore.friends.find((friend) => friend.id === request.owner),
			now,
			"Pedidos abertos",
		),
	);
	const open = mine.length;
	return boardPage(state, "amigos-pedidos", "Pedidos", "pedidos", [], [...mineTiles, ...theirs], {
		stats: [stat(socialIcon("package"), `${open}/${SOCIAL_REQUESTS_OPEN}`, "seus pedidos"), stat(socialIcon("friends"), String(theirs.length), "dos amigos")],
		footer: [
			go(open >= SOCIAL_REQUESTS_OPEN ? "2 pedidos abertos" : "Pedir aos amigos", "amigos-pedir", {
				icon: socialIcon("package"),
				variant: "success",
				enabled: open < SOCIAL_REQUESTS_OPEN,
			}),
		],
		empty: "Nenhum pedido aberto. Falta um produto? Peça aos amigos!",
	});
}

/** "Pedir aos amigos": a grid of products (the contract's missing one first) and a big quantity stepper. */
function pickerPage(state: State, productArg: string | undefined, qtyArg: string | undefined): Page {
	const gated = gate(state, "amigos-pedir", "pedidos");
	if (gated) return gated;
	const short = contractShortfall(state);
	const unlocked = itemCatalog.filter((item) => state.market.unlockedProductIds.includes(item.id));
	const products = [...(short ? [short] : []), ...unlocked.filter((item) => item.id !== short?.id).sort((a, b) => (state.inventory[a.id] ?? 0) - (state.inventory[b.id] ?? 0))];
	const picked = Number(productArg) || products[0]?.id || 0;
	const amount = Math.max(SOCIAL_REQUEST_MIN, Math.min(SOCIAL_REQUEST_MAX, Math.floor(Number(qtyArg)) || 10));
	const open = socialStore.requests.mine.length;
	const tiles = products.map((product) => {
		const qty = product.id === picked ? amount : 10;
		const step = (label: string, to: number) => {
			const value = Math.max(SOCIAL_REQUEST_MIN, Math.min(SOCIAL_REQUEST_MAX, to));
			return button(label, { route: `~amigos-pedir:${product.id}:${value}`, variant: value === qty ? "coin" : "secondary", active: value === qty });
		};
		const have = state.inventory[product.id] ?? 0;
		const missing = short?.id === product.id;
		return tile(String(product.id), product.name, {
			group: missing ? "Falta no contrato" : "Seus produtos",
			icon: productIcon(product.id),
			subtitle: `${qty} unidades`,
			badge: fmt(have),
			sticker: missing ? "FALTANDO" : have <= 0 ? "ACABOU" : "",
			tone: missing ? "warning" : have <= 0 ? "danger" : "",
			action: go("Escolher", `~amigos-pedir:${product.id}:${qty}`, { variant: product.id === picked ? "coin" : "secondary" }),
			facts: [stat(productIcon(product.id), fmt(have), "no estoque"), stat(socialIcon("package"), String(qty), "unidades")],
			actions: [
				step("−5", qty - 5),
				step("−1", qty - 1),
				step("+1", qty + 1),
				step("+5", qty + 5),
				step("5", 5),
				step("10", 10),
				step("20", 20),
				act(busy(`request:${product.id}`) ? "Enviando…" : `Pedir ${qty}× ${product.name}`, "socialRequest", [product.id, qty], {
					icon: socialIcon("package"),
					variant: "success",
					enabled: open < SOCIAL_REQUESTS_OPEN && !busy(`request:${product.id}`),
					fail: "Você já tem 2 pedidos abertos.",
					ok: "",
					after: "back",
				}),
			],
		});
	});
	return boardPage(state, `amigos-pedir:${picked}:${amount}`, "Pedir aos amigos", "pedidos", [], tiles, {
		columns: 5,
		focus: String(picked),
		stats: [stat(socialIcon("package"), `${open}/${SOCIAL_REQUESTS_OPEN}`, "pedidos abertos")],
		empty: "Nenhum produto liberado ainda.",
	});
}

// ------------------------------------------------------------------------------------------------------------ convidar

/** Convidar: my invite code as the bar (Convidar / Copiar / QR, the friends who reached the Späti in blocks with the
 * three prizes on it) and the reward ladder as the hero, big pictures above the fold. "Tem um código?" opens the field
 * (route "amigos-convidar:codigo"), the QR its own card; both only when asked for. */
function convidarPage(state: State, codeField: boolean): Page {
	const gated = gate(state, codeField ? "amigos-convidar:codigo" : "amigos-convidar", "convidar");
	if (gated) return gated;
	const me = socialStore.me!;
	const rewarded = Math.max(0, me.invites?.rewarded ?? 0);
	const top = SOCIAL_INVITE_MILESTONES[SOCIAL_INVITE_MILESTONES.length - 1];
	const next = SOCIAL_INVITE_MILESTONES.find((milestone) => milestone > rewarded);
	const cards: Card[] = [];
	if (socialStore.offeredCode) {
		const code = socialStore.offeredCode;
		cards.push(
			card("Convite de um amigo", {
				icon: socialIcon("invite"),
				eyebrow: "CÓDIGO RECEBIDO",
				subtitle: formatCode(code),
				tone: "success",
				lines: [me.invitedBy ? "Adicione esse amigo à sua lista." : "Use o convite: vocês viram amigos e, quando você chegar ao Späti, os dois ganham 30 diamantes."],
				buttons: [
					me.invitedBy
						? act("Adicionar amigo", "socialAddFriend", [code], { variant: "success", enabled: !busy("add"), ok: "" })
						: act("Usar convite", "socialRedeem", [code], { variant: "success", enabled: !busy("redeem"), ok: "" }),
				],
			}),
		);
	} else if (codeField) cards.push(addFriendCard(!me.invitedBy));
	if (socialStore.showQr)
		cards.push(
			card(formatCode(me.code), {
				icon: socialIcon("invite"),
				eyebrow: "QR DO CONVITE",
				subtitle: "Aponte a câmera do celular do amigo.",
				// (closed from the bar's "Fechar QR": the card stays short enough to show whole on a phone)
				qr: qrText(inviteUrl(me.code)),
			}),
		);
	const ladder = SOCIAL_INVITE_MILESTONES.map((milestone) => {
		const id = inviteRewardDecorId(milestone);
		const decor = getInteriorDecor(id);
		const reached = rewarded >= milestone;
		const left = milestone - rewarded;
		return tile(id, decor?.name ?? id, {
			group: "Prêmios do convite",
			icon: decorIcon(id),
			frame: "showcase",
			subtitle: milestone === 1 ? "1 amigo no Späti" : `${milestone} amigos no Späti`,
			sticker: reached ? "GANHOU!" : left === 1 ? "FALTA 1" : `FALTAM ${left}`,
			tone: reached ? "gold" : "locked",
			state: reached ? "done" : milestone === next ? "" : "locked",
			fill: Math.min(1, rewarded / milestone),
			fillText: `${Math.min(rewarded, milestone)}/${milestone}`,
			action: reached ? button("Na sua decoração", { variant: "secondary", enabled: false, icon: socialIcon("success") }) : button(`Faltam ${left}`, { variant: "secondary", enabled: false }),
			detail: decor?.description ?? "",
			facts: [stat(socialIcon("friends"), `${Math.min(rewarded, milestone)}/${milestone}`, "amigos"), stat(socialIcon("diamond"), fmt(30 * milestone), "diamantes")],
			lines: [reached ? "Está no seu inventário: coloque no mercado pelo modo construir." : "Exclusivo: não se compra na loja."],
		});
	});
	const asking = codeField || Boolean(socialStore.offeredCode);
	return boardPage(state, codeField ? "amigos-convidar:codigo" : "amigos-convidar", "Convidar", "convidar", cards, ladder, {
		columns: 3,
		focus: inviteRewardDecorId(next ?? top),
		stats: [stat(socialIcon("friends"), String(rewarded), "convites premiados"), stat(socialIcon("diamond"), fmt(rewarded * 30), "diamantes")],
		meter: meter(formatCode(me.code), Math.min(rewarded, top), top, {
			icon: socialIcon("invite"),
			tone: "gold",
			segments: top,
			text: `${Math.min(rewarded, top)}/${top} no Späti · +30 diamantes por amigo`,
			buttons: [
				act("Convidar", "socialShare", [], { icon: socialIcon("share"), variant: "success", ok: "" }),
				act("Copiar", "socialCopy", [], { variant: "secondary", ok: "" }),
				act(socialStore.showQr ? "Fechar QR" : "QR", "socialQr", [], { variant: "secondary", ok: "" }),
			],
			marks: SOCIAL_INVITE_MILESTONES.map((milestone) => ({
				at: milestone,
				icon: decorIcon(inviteRewardDecorId(milestone)),
				label: getInteriorDecor(inviteRewardDecorId(milestone))?.name ?? "",
				state: rewarded >= milestone ? "done" : "locked",
				action: button("", { enabled: false }),
			})),
		}),
		footer: socialStore.offeredCode
			? []
			: [
					asking
						? go("Fechar o código", "~amigos-convidar", { variant: "secondary" })
						: go(me.invitedBy ? "Adicionar por código" : "Tem um código de convite?", "~amigos-convidar:codigo", { icon: socialIcon("friends"), variant: "primary" }),
				],
		empty: "",
	});
}

// ------------------------------------------------------------------------------------------------------------ correio

const historyIcon: Record<string, string> = { gift: "gift", like: "like", help: "handshake", delivery: "package", friend_request: "friends", friend_added: "friends", invite_reward: "diamond", request_fulfilled: "package" };
const historyLine: Record<string, string> = {
	gift: "mandou um presente",
	like: "curtiu seu mercado",
	help: "ajudou na obra: −{2} min",
	delivery: "mandou {3}× {4}",
	friend_request: "quer ser seu amigo",
	friend_added: "virou seu amigo",
	invite_reward: "convite premiado: +{5} diamantes",
	request_fulfilled: "atendeu o seu pedido",
};

/** One line of the history: the friend's face, who, what and when, as a slim row (two per line). */
function historyTile(entry: SocialLogEntry, index: number, now: number): BoardTile {
	const values = { name: entry.name, coins: entry.coins, minutes: entry.minutes, qty: entry.qty, product: productName(entry.productId), diamonds: entry.diamonds };
	const line = toastText(historyLine[entry.kind] ?? entry.text, values);
	const icon = socialIcon((historyIcon[entry.kind] ?? "friends") as never);
	return tile(`log-${index}`, entry.name || "Um amigo", {
		group: "Histórico",
		icon: entry.avatar ? avatarIcon(entry.avatar) : icon,
		frame: "line",
		corner: icon,
		subtitle: `${line} · ${formatAgo(entry.at, now)}`,
		// (the side panel: who, when, and the whole message once)
		detail: toastText(entry.text, values),
	});
}

function correioPage(state: State): Page {
	const gated = gate(state, "amigos-correio", "correio");
	if (gated) return gated;
	const now = Date.now();
	const mine = social(state);
	const boxes = [...mine.mailbox].reverse().map((mail) =>
		tile(`mail-${mail.id}`, "Presente", {
			group: "Para abrir",
			icon: socialIcon("gift"),
			frame: "gift",
			subtitle: mail.name || "Um amigo",
			badge: `+${fmt(mail.coins)}`,
			tone: "gold",
			state: "ready",
			action: act("Abrir", "socialOpenMail", [mail.id], { icon: socialIcon("gift"), variant: "success", ok: "" }),
			detail: "Um presente de um amigo: abra para ganhar as moedas.",
			facts: [stat(socialIcon("coin"), `+${fmt(mail.coins)}`, "moedas")],
			lines: [formatAgo(mail.at, now)],
			actions: [act("Abrir", "socialOpenMail", [mail.id], { icon: socialIcon("gift"), variant: "success", ok: "" })],
		}),
	);
	const total = mine.mailbox.reduce((sum, mail) => sum + mail.coins, 0);
	const history = mine.history.map((entry, index) => historyTile(entry, index, now));
	return boardPage(state, "amigos-correio", "Correio", "correio", [], [...boxes, ...history], {
		stats: [stat(socialIcon("gift"), String(mine.mailbox.length), "para abrir"), stat(socialIcon("coin"), `+${fmt(total)}`, "moedas")],
		footer: mine.mailbox.length
			? [act(mine.mailbox.length === 1 ? "Abrir o presente" : `Abrir tudo (${mine.mailbox.length})`, "socialOpenMail", ["all"], { icon: socialIcon("gift"), variant: "success", ok: "" })]
			: [],
		empty: "Nada no correio ainda. Os presentes dos amigos chegam aqui.",
	});
}

// ------------------------------------------------------------------------------------------------------------ visit

/** During a visit: the friend's open product requests, each with "Enviar" (checks the stock room first). */
function visitRequestsPage(state: State): Page {
	const visit = socialStore.visit;
	if (!visit) return boardPage(state, "visita", "Pedidos", null, [], [], { empty: "Você está no seu mercado." });
	const now = Date.now();
	const requests = (visit.friend.openRequests ?? []).filter((request) => request.expiresAt > now);
	const tiles = requests.map((request) => sendTile({ ...request, owner: visit.friend.id }, visit.friend, now, "Pedidos de ajuda"));
	return boardPage(state, "visita", `Pedidos de ${marketName(visit.friend)}`, null, [], tiles, {
		columns: 4,
		stats: [stat(socialIcon("package"), String(requests.length), "pedidos")],
		empty: "Este amigo não está pedindo produtos agora.",
	});
}

export const routes: Routes = {
	amigos: (state, [section, id, qty]) => {
		if (section === "perfil") return online() && socialStore.me ? profilePage(state, false) : amigosPage(state);
		// Old links ("amigos:pedir:<product>:<qty>") open the product picker.
		if (section === "pedir") return pickerPage(state, id, qty);
		return amigosPage(state);
	},
	"amigos-pedidos": (state) => pedidosPage(state),
	"amigos-pedir": (state, [id, qty]) => pickerPage(state, id, qty),
	"amigos-convidar": (state, [arg]) => convidarPage(state, arg === "codigo"),
	"amigos-correio": (state) => correioPage(state),
	visita: (state) => visitRequestsPage(state),
};
