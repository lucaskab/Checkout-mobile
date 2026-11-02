import type { Routes } from ".";
import { itemCatalog } from "@/data/market-products";
import { SOCIAL_REQUEST_MAX, SOCIAL_REQUEST_MIN } from "@/data/social";
import { t } from "@/i18n";
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
	socialIcon,
	socialStore,
	stageName,
	type SocialFriend,
	type SocialPerson,
	type SocialRequestView,
} from "../social";
import { act, button, type Card, card, fmt, go, noInput, page, productIcon, type State } from "../view-kit";

// Amigos (social v1, docs/social-api.md): my code (copy, share, QR), add a friend by code, the invite code, friend
// requests, the friends (level, stage, likes, Presente, Visitar, badges for builds to help and open requests), the
// player's own product requests, and the first-time profile (market name + one of the game's shoppers as the face).

const productName = (id: number) => itemCatalog.find((item) => item.id === id)?.name ?? "";
const hoursLeft = (request: SocialRequestView, now: number) => Math.max(1, Math.ceil((request.expiresAt - now) / 3_600_000));
const online = () => socialStore.signedIn || socialStore.mock;
const busy = (key: string) => socialStore.busy.has(key);

function signedOutCards(): Card[] {
	const providers = cloudStore.providers.length ? cloudStore.providers : ["google" as const];
	const canSignIn = cloudStore.status === "signed-out";
	return [
		card("Entre para jogar com amigos", {
			icon: socialIcon("friends"),
			eyebrow: "AMIGOS",
			tone: cloudStore.status === "unavailable" ? "locked" : "info",
			lines: [
				"Visite o mercado dos amigos, mande presentes, ajude nas obras e peça produtos.",
				"Sua conta também guarda o seu progresso na nuvem.",
			],
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
		}),
	];
}

/** Profile: the market's name and a face (first time the page opens, and "Editar perfil"). */
function profileCards(first: boolean, hidden = false): Card[] {
	const me = socialStore.me;
	const chosen = socialStore.draft.avatar || me?.avatar || "";
	const ids = Array.from({ length: socialStore.avatars }, (_, i) => `shopper-${i + 1}`);
	const rows: Card[] = [];
	for (let i = 0; i < ids.length; i += 4)
		rows.push(
			card("", {
				eyebrow: i === 0 ? "ESCOLHA UM ROSTO" : "",
				buttons: ids.slice(i, i + 4).map((id) =>
					act("", "socialPickAvatar", [id], { icon: avatarIcon(id), variant: id === chosen ? "coin" : "secondary", active: id === chosen, ok: "" }),
				),
			}),
		);
	return [
		card(first ? "Dê um nome ao seu mercado" : hidden ? "Escolha outro nome" : "Seu perfil", {
			icon: avatarIcon(chosen),
			eyebrow: first ? "PRIMEIRA VEZ AQUI" : "PERFIL",
			tone: hidden ? "warning" : "",
			lines: [
				first
					? "É assim que os seus amigos vão ver o seu mercado."
					: hidden
						? "O nome do seu mercado foi denunciado e está escondido. Os amigos veem só o código até você escolher outro."
						: "O nome e o rosto que os seus amigos veem.",
				"De 3 a 20 letras ou números. Nada de palavrões: nomes denunciados ficam escondidos.",
			],
			input: { id: "name", placeholder: "Nome do mercado", value: hidden ? "" : (me?.marketName ?? ""), max: 20, kind: "name" },
			buttons: [
				act(busy("profile") ? "Salvando…" : "Salvar", "socialSaveProfile", ["$input:name", chosen], {
					variant: "success",
					enabled: !busy("profile") && Boolean(chosen),
					fail: "Escolha um rosto primeiro.",
					ok: "",
					after: first || hidden ? "" : "back",
				}),
			],
		}),
		...rows,
	];
}

function friendCard(friend: SocialFriend, now: number): Card {
	const builds = helpableBuilds(friend, now);
	const requests = friend.openRequests ?? [];
	const stage = stageName(friend.era);
	const badges = [
		builds.length === 1 ? "1 obra para ajudar" : builds.length > 1 ? `${builds.length} obras para ajudar` : "",
		requests.length ? "Pediu produtos" : "",
	].filter(Boolean);
	return card(marketName(friend), {
		icon: avatarIcon(friend.avatar),
		eyebrow: badges.join(" · ").toUpperCase(),
		badge: builds.length + requests.length > 0 ? String(builds.length + requests.length) : "",
		tone: builds.length + requests.length > 0 ? "success" : "",
		// Each piece in the player's language before they are joined (stage names would match other patterns whole).
		subtitle: [t(`Nível ${friend.level}`), t(stage), likesText(friend.likes)].filter(Boolean).join(" · "),
		lines: [
			friend.lastSeen ? `Visto ${formatAgo(friend.lastSeen, now)}` : "",
			...requests.slice(0, 2).map((request) => `Pede ${request.qty}× ${productName(request.productId)} · ${hoursLeft(request, now)} h`),
		].filter(Boolean),
		buttons: [
			act(busy(`visit-start:${friend.id}`) || busy(`visit:${friend.id}`) ? "Abrindo…" : "Visitar", "socialVisit", [friend.id], {
				icon: socialIcon("market"),
				variant: "primary",
				enabled: !busy(`visit-start:${friend.id}`),
				ok: "",
			}),
			act(friend.giftedToday ? "Enviado hoje" : "Presente", "socialGift", [friend.id], {
				icon: socialIcon("gift"),
				variant: friend.giftedToday ? "secondary" : "success",
				enabled: !friend.giftedToday && !busy(`gift:${friend.id}`),
				ok: "",
				fail: "Você já mandou um presente hoje. Volte amanhã!",
			}),
			go("Mais", `amigos:amigo:${friend.id}`),
		],
	});
}

function requestCard(person: SocialPerson): Card {
	return card(marketName(person), {
		icon: avatarIcon(person.avatar),
		eyebrow: "QUER SER SEU AMIGO",
		subtitle: [t(`Nível ${person.level}`), t(stageName(person.era))].filter(Boolean).join(" · "),
		tone: "info",
		buttons: [
			act("Aceitar", "socialAccept", [person.id], { icon: socialIcon("friends"), variant: "success", enabled: !busy(`accept:${person.id}`), ok: "" }),
			act("Recusar", "socialDecline", [person.id], { variant: "secondary", enabled: !busy(`decline:${person.id}`), ok: "" }),
		],
	});
}

function mainPage(state: State) {
	const now = Date.now();
	const title = "Amigos";
	const icon = socialIcon("friends");
	if (!online()) return page("amigos", title, signedOutCards(), { icon, subtitle: "Jogue junto com os seus amigos" });
	const me = socialStore.me;
	if (!me)
		return page(
			"amigos",
			title,
			[
				socialStore.error
					? card("Não deu para carregar os amigos", {
							icon: socialIcon("warning"),
							tone: "warning",
							lines: [socialStore.error],
							buttons: [act("Tentar de novo", "socialRefresh", [], { ok: "" })],
						})
					: card("Carregando os amigos…", { icon }),
			],
			{ icon },
		);
	if (!me.marketName) return page("amigos", title, profileCards(true), { icon, subtitle: "Seu perfil" });
	// The name was reported and is hidden ("Mercado #code" for the others): ask for a new one.
	if (me.nameHidden) return page("amigos", title, profileCards(false, true), { icon, subtitle: "Seu perfil" });

	const cards: Card[] = [];
	cards.push(
		card(marketName(me), {
			icon: avatarIcon(me.avatar),
			eyebrow: "MEU CÓDIGO DE AMIGO",
			subtitle: formatCode(me.code),
			lines: [[t(`Nível ${state.market.level}`), t(stageName(state.era.id)), likesText(me.likes)].join(" · "), "Mande o código ou chame pelo link: quem entrar pelo seu convite e chegar ao Späti ganha 30 diamantes, e você também."],
			qr: socialStore.showQr ? qrText(inviteUrl(me.code)) : "",
			buttons: [
				act("Convidar", "socialShare", [], { icon: socialIcon("share"), variant: "success", ok: "" }),
				act("Copiar", "socialCopy", [], { variant: "secondary", ok: "" }),
				act(socialStore.showQr ? "Fechar QR" : "QR", "socialQr", [], { variant: "secondary", ok: "" }),
				go("Perfil", "amigos:perfil"),
			],
		}),
	);
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
	}
	for (const person of socialStore.incoming) cards.push(requestCard(person));
	cards.push(
		card("Adicionar amigo", {
			icon: socialIcon("friends"),
			lines: ["Digite o código de amigo (8 letras e números)."],
			input: { id: "code", placeholder: "Ex.: K7Q2-MX4P", value: "", max: 9, kind: "code" },
			buttons: [act(busy("add") ? "Enviando…" : "Adicionar", "socialAddFriend", ["$input:code"], { variant: "primary", enabled: !busy("add"), ok: "" })],
		}),
	);
	if (socialStore.news.length)
		cards.push(
			card("Novidades", {
				icon: socialIcon("like"),
				lines: socialStore.news.slice(0, 5).map((item) => `${item.text} · ${formatAgo(item.at, now)}`),
			}),
		);
	if (socialStore.requests.mine.length)
		cards.push(
			card("Seus pedidos aos amigos", {
				icon: socialIcon("package"),
				lines: socialStore.requests.mine.map((request) => `${request.qty}× ${productName(request.productId)} · ${hoursLeft(request, now)} h restantes`),
				buttons: socialStore.requests.mine.map((request) =>
					act(`Cancelar ${productName(request.productId)}`, "socialCancelRequest", [request.id], { variant: "secondary", enabled: !busy(`cancel:${request.id}`), ok: "" }),
				),
			}),
		);
	const friends = [...socialStore.friends].sort(
		(a, b) => helpableBuilds(b, now).length + (b.openRequests?.length ?? 0) - (helpableBuilds(a, now).length + (a.openRequests?.length ?? 0)) || b.lastSeen - a.lastSeen,
	);
	if (!friends.length)
		cards.push(
			card("Nenhum amigo ainda", {
				icon: socialIcon("friends"),
				lines: ["Chame alguém com o seu código ou o link do convite."],
				buttons: [act("Chamar amigo", "socialShare", [], { icon: socialIcon("share"), variant: "success", ok: "" })],
			}),
		);
	for (const friend of friends) cards.push(friendCard(friend, now));
	if (socialStore.outgoing.length)
		cards.push(
			card("Esperando resposta", {
				icon: socialIcon("friends"),
				lines: socialStore.outgoing.map((person) => marketName(person)),
			}),
		);
	if (!me.invitedBy && !socialStore.offeredCode)
		cards.push(
			card("Tem um código de convite?", {
				icon: socialIcon("invite"),
				lines: ["Nos primeiros 7 dias de jogo: use o código de quem te chamou e os dois ganham 30 diamantes quando você chegar ao Späti."],
				input: { id: "invite", placeholder: "Código do convite", value: "", max: 9, kind: "code" },
				buttons: [act(busy("redeem") ? "Enviando…" : "Usar código", "socialRedeem", ["$input:invite"], { variant: "secondary", enabled: !busy("redeem"), ok: "" })],
			}),
		);
	return page("amigos", title, cards, {
		icon,
		subtitle: friends.length === 1 ? "1 amigo" : `${friends.length} amigos`,
	});
}

function friendPage(id: string) {
	const friend = socialStore.friends.find((item) => item.id === id);
	if (!friend) return page(`amigos:amigo:${id}`, "Amigo", [card("Esse amigo não está mais na lista.", { icon: socialIcon("friends") })]);
	const now = Date.now();
	const confirming = socialStore.confirmRemove === id;
	const builds = helpableBuilds(friend, now);
	return page(
		`amigos:amigo:${id}`,
		marketName(friend),
		[
			friendCard(friend, now),
			card("Curtir o mercado", {
				icon: socialIcon("like"),
				lines: ["Uma curtida por dia: vocês dois ganham moedas."],
				buttons: [
					act(friend.likedToday ? "Curtido hoje" : "Curtir", "socialLike", [id], {
						icon: socialIcon("like"),
						variant: friend.likedToday ? "secondary" : "success",
						enabled: !friend.likedToday && !busy(`like:${id}`),
						ok: "",
					}),
				],
			}),
			...(builds.length
				? [
						card("Obras para ajudar", {
							icon: socialIcon("handshake"),
							lines: ["Visite o mercado e toque em Ajudar em cada obra: −5 min para o amigo, moedas para você."],
						}),
					]
				: []),
			card(confirming ? "Remover mesmo?" : "Remover amigo", {
				icon: socialIcon("warning"),
				tone: confirming ? "danger" : "",
				lines: [confirming ? "Toque de novo para remover. Vocês deixam de ver o mercado um do outro." : "Tira esse amigo da sua lista (e você da lista dele)."],
				buttons: [act(confirming ? "Remover" : "Remover amigo", "socialRemove", [id], { variant: "danger", enabled: !busy(`remove:${id}`), ok: "", after: confirming ? "back" : "" })],
			}),
			card("Denunciar o nome", {
				icon: socialIcon("warning"),
				lines: ["O nome deste mercado é ofensivo? Depois de algumas denúncias ele fica escondido até ser trocado."],
				buttons: [act("Denunciar nome", "socialReport", [id], { variant: "secondary", enabled: !busy(`report:${id}`), ok: "" })],
			}),
		],
		{ icon: avatarIcon(friend.avatar), subtitle: [t(`Nível ${friend.level}`), t(stageName(friend.era))].filter(Boolean).join(" · ") },
	);
}

/** "Pedir aos amigos": one product, 1–20 units (the stock page and a contract short of a product open it). */
function requestPage(state: State, productId: number, qty: number) {
	const product = itemCatalog.find((item) => item.id === productId);
	const route = `amigos:pedir:${productId}`;
	if (!product) return page(route, "Pedir aos amigos", [card("Produto não encontrado.")]);
	const amount = Math.max(SOCIAL_REQUEST_MIN, Math.min(SOCIAL_REQUEST_MAX, Math.floor(qty) || 10));
	const open = socialStore.requests.mine.length;
	const step = (label: string, to: number) =>
		button(label, { route: `~${route}:${Math.max(SOCIAL_REQUEST_MIN, Math.min(SOCIAL_REQUEST_MAX, to))}`, variant: to === amount ? "coin" : "secondary", active: to === amount });
	const cards: Card[] = [];
	if (!online()) cards.push(...signedOutCards());
	else
		cards.push(
			card(product.name, {
				icon: productIcon(product.id),
				eyebrow: "PEDIR AOS AMIGOS",
				subtitle: `${amount} unidades`,
				lines: [
					`No seu estoque: ${fmt(state.inventory[product.id] ?? 0)}`,
					"Um amigo manda tudo de uma vez, direto para o seu estoque. O pedido vale 24 horas.",
					open >= 2 ? "Você já tem 2 pedidos abertos: cancele um na página Amigos." : `Pedidos abertos: ${open} de 2`,
				],
				buttons: [step("−5", amount - 5), step("−1", amount - 1), step("+1", amount + 1), step("+5", amount + 5)],
			}),
			card("", {
				buttons: [step("5", 5), step("10", 10), step("20", 20)],
			}),
			card("", {
				buttons: [
					act(busy(`request:${product.id}`) ? "Enviando…" : `Pedir ${amount}× ${product.name}`, "socialRequest", [product.id, amount], {
						icon: socialIcon("package"),
						variant: "success",
						enabled: open < 2 && !busy(`request:${product.id}`),
						fail: "Você já tem 2 pedidos abertos.",
						ok: "",
						after: "back",
					}),
				],
			}),
		);
	return page(route, "Pedir aos amigos", cards, { icon: socialIcon("package"), subtitle: product.name });
}

/** During a visit: the friend's open product requests, each with "Enviar" (checks the stock room first). */
function visitRequestsPage() {
	const visit = socialStore.visit;
	if (!visit) return page("visita", "Pedidos", [card("Você está no seu mercado.")]);
	const now = Date.now();
	const requests = (visit.friend.openRequests ?? []).filter((request) => request.expiresAt > now);
	const cards: Card[] = requests.map((request) => {
		const have = sendableStock(request.productId);
		const enough = have >= request.qty;
		return card(`${request.qty}× ${productName(request.productId)}`, {
			icon: productIcon(request.productId),
			eyebrow: "PEDIDO DE AJUDA",
			subtitle: `No seu estoque: ${fmt(have)}`,
			lines: [enough ? "Você recebe o preço do fornecedor de volta e mais 25%." : `Faltam ${fmt(request.qty - have)} no seu estoque.`, `Vale por mais ${hoursLeft(request, now)} h`],
			tone: enough ? "success" : "locked",
			buttons: [
				act(busy(`send:${request.id}`) ? "Enviando…" : "Enviar", "socialSend", [request.id, visit.friend.id, request.productId, request.qty], {
					icon: socialIcon("package"),
					variant: "success",
					enabled: enough && !busy(`send:${request.id}`),
					fail: `Faltam ${fmt(request.qty - have)} no seu estoque.`,
					ok: "",
				}),
			],
		});
	});
	if (!cards.length) cards.push(card("Nenhum pedido aberto", { icon: socialIcon("package"), lines: ["Este amigo não está pedindo produtos agora."] }));
	return page("visita", `Pedidos de ${marketName(visit.friend)}`, cards, { icon: socialIcon("package") });
}

export const routes: Routes = {
	amigos: (state, [section, id, qty]) => {
		if (section === "perfil") return online() && socialStore.me ? page("amigos:perfil", "Perfil", profileCards(false), { icon: avatarIcon(socialStore.me.avatar) }) : mainPage(state);
		if (section === "amigo" && id) return friendPage(id);
		if (section === "pedir" && id) return requestPage(state, Number(id), Number(qty ?? 10));
		return mainPage(state);
	},
	visita: () => visitRequestsPage(),
};

// The view-kit's empty input, for pages that build cards by hand.
export const emptyInput = noInput;
