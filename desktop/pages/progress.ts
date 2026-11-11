import type { AchievementCategory, AchievementRarity } from "@/@types/achievement";
import type { MissionCategory } from "@/@types/mission";
import { achievementRarityOrder, achievements } from "@/data/achievements";
import {
	currencyPackSections,
	currencyPacks,
	getCurrencyPackCoins,
	isCurrencyPackAvailable,
} from "@/data/currency-packs";
import { getPackEvent, getPackPrice, iapStore, storePlatform } from "../iap";
import { adStatusLine, adsStore, getLastAdEvent, isAdOpening } from "../ads";
import { AD_DAILY_COIN_VIDEOS, AD_DAILY_DIAMONDS, AD_REWARD_DIAMONDS, formatAdWait, getRewardedAdOffer, getRewardedCoinAdOffer } from "@/services/rewarded-ads";
import { getAchievementIcon, getMissionIcon } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import { missions } from "@/data/missions";
import {
	getAchievementProgress,
	getAchievementStars,
	getAchievementTotals,
} from "@/services/achievements";
import { describeMissionReward, getMissionProgress, getMissionStatus } from "@/services/missions";
import { cloudStore } from "../cloud";
import {
	canClaimDailyLogin,
	canDoubleDailyLogin,
	getLoginReward,
	getNextLoginDay,
	getStreakRecovery,
	LOGIN_STREAK_DAYS,
} from "@/services/daily-login";
import type { Routes } from ".";
import { getStarterOfferEnd, isStarterOfferOpen, STARTER_PACK_ID } from "@/services/perks";
import { petCosmetics } from "@/data/pet";
import { getWeekEnd, getWeeklyProgress, getWeeklyReward } from "@/services/weekly-event";
import {
	albumCollections,
	getCollectionProgress,
	isProductCollected,
	SALES_TO_COLLECT,
} from "@/data/product-album";
import {
	type Button,
	couponPlus,
	act,
	type Card,
	card,
	fmt,
	gameIcon,
	go,
	page,
	productIcon,
	ratio,
	swap,
} from "../view-kit";

type MissionFilter = "active" | "claimed" | "locked";

const missionFilters: { id: MissionFilter; label: string }[] = [
	{ id: "active", label: "Em andamento" },
	{ id: "claimed", label: "Concluídas" },
	{ id: "locked", label: "Próximas" },
];

const missionCategoryLabels: Record<MissionCategory, string> = {
	customers: "CLIENTES",
	inventory: "ESTOQUE",
	management: "GESTÃO",
	production: "PRODUÇÃO",
	progression: "PROGRESSÃO",
	sales: "VENDAS",
};

type AchievementFilter = "all" | AchievementCategory;

const achievementFilters: { id: AchievementFilter; label: string }[] = [
	{ id: "all", label: "Todas" },
	{ id: "progression", label: "Evolução" },
	{ id: "sales", label: "Vendas" },
	{ id: "customers", label: "Clientes" },
	{ id: "production", label: "Produção" },
	{ id: "management", label: "Gestão" },
	{ id: "logistics", label: "Logística" },
	{ id: "collection", label: "Coleção" },
	{ id: "specialist", label: "Especialistas" },
];

const achievementCategoryLabels: Record<AchievementCategory, string> = {
	collection: "COLEÇÃO",
	customers: "CLIENTES",
	logistics: "LOGÍSTICA",
	management: "GESTÃO",
	production: "PRODUÇÃO",
	progression: "EVOLUÇÃO",
	sales: "VENDAS",
	specialist: "ESPECIALISTA",
};

const rarityLabels: Record<AchievementRarity, string> = {
	common: "Comum",
	uncommon: "Incomum",
	rare: "Rara",
	epic: "Épica",
	legendary: "Lendária",
};

// Same as formatCompactNumber in src/screens/achievements/index.tsx.
function formatCompactNumber(value: number) {
	if (value >= 1_000_000) return `${value / 1_000_000}M`;
	if (value >= 1_000) return `${value / 1_000}k`;
	return value.toString();
}

// Weekly event: this week's theme, its goal and the prize.
function weeklyEventCard(state: Parameters<Routes[string]>[0]): Card {
	const now = Date.now();
	const progress = getWeeklyProgress(state.weeklyEvent, state.market.soldByProduct, now);
	const reward = getWeeklyReward(state.era.id);
	const daysLeft = Math.max(1, Math.ceil((getWeekEnd(now) - now) / (24 * 60 * 60_000)));
	const prize = `${fmt(reward.coins)} moedas + ${reward.diamonds} diamantes${couponPlus(reward.coupons)}`;
	return card(progress.theme.name, {
		eyebrow: `EVENTO DA SEMANA · ${daysLeft === 1 ? "ÚLTIMO DIA" : `${daysLeft} DIAS`}`,
		subtitle: `${progress.theme.description} Esses produtos vendem mais a semana toda.`,
		icon: gameIcon("festival"),
		tone: progress.done && !progress.claimed ? "featured" : "",
		badge: progress.claimed ? "Resgatado" : progress.done ? "Pronto" : `${Math.min(progress.sold, progress.theme.goal)}/${progress.theme.goal}`,
		progress: ratio(Math.min(progress.sold, progress.theme.goal), progress.theme.goal),
		lines: [`Meta: vender ${progress.theme.goal} unidades desses produtos`, `Prêmio: ${prize}`],
		buttons:
			progress.done && !progress.claimed
				? [act(`Resgatar ${prize}`, "claimWeeklyEvent", [], { variant: "success", ok: "Prêmio da semana resgatado!" })]
				: [],
	});
}

// Product album: one line on the missions page, the whole album on its own page.
function albumSummaryCard(state: Parameters<Routes[string]>[0]): Card {
	const progress = albumCollections.map((c) => getCollectionProgress(c, state.market.soldByProduct));
	const collected = progress.reduce((total, p) => total + p.collected, 0);
	const total = progress.reduce((sum, p) => sum + p.total, 0);
	const ready = albumCollections.filter(
		(c, i) => progress[i].complete && !(state.albumClaimedIds ?? []).includes(c.id),
	).length;
	return card("Álbum de produtos", {
		eyebrow: "COLEÇÕES",
		subtitle: `Cada produto vira figurinha quando você vende ${SALES_TO_COLLECT} unidades dele. Complete uma coleção para ganhar o prêmio.`,
		icon: gameIcon("medal"),
		badge: ready > 0 ? `${ready} prêmio(s)` : `${collected}/${total}`,
		tone: ready > 0 ? "featured" : "",
		progress: ratio(collected, total),
		buttons: [go("Abrir álbum", "album", { variant: "primary" })],
	});
}

// "Recuperar sequência" (Lucas 11/11): a streak broken by 1–3 days comes back for diamonds (or a video for 1 day).
export function streakRecoveryButtons(state: Parameters<Routes[string]>[0], now = Date.now()): Button[] {
	const offer = getStreakRecovery(state.dailyLogin, now);
	if (!offer) return [];
	const waiting = isAdOpening("streak");
	return [
		act(`Recuperar · ${offer.diamonds}`, "recoverLoginStreak", [], {
			variant: "gem",
			icon: gameIcon("diamond"),
			ok: "Sequência recuperada! Resgate o presente de hoje.",
		}),
		...(offer.video
			? [act(waiting ? "Abrindo…" : "Com vídeo", "watchRewardedAd", ["streak"], { variant: "coin", icon: gameIcon("television"), enabled: !waiting, ok: "" })]
			: []),
	];
}
export function streakRecoveryText(state: Parameters<Routes[string]>[0], now = Date.now()) {
	const offer = getStreakRecovery(state.dailyLogin, now);
	if (!offer) return "";
	return offer.missed === 1
		? `Você perdeu 1 dia e a sequência ia voltar ao dia 1. Recupere e continue do dia ${offer.streak + 1}.`
		: `Você perdeu ${offer.missed} dias e a sequência ia voltar ao dia 1. Recupere e continue do dia ${offer.streak + 1}.`;
}

// Daily login gift: a 7-day streak shown as a row of days, the next one ready to claim once a day.
function dailyGiftCard(state: Parameters<Routes[string]>[0]): Card {
	const now = Date.now();
	const ready = canClaimDailyLogin(state.dailyLogin, now);
	const next = getNextLoginDay(state.dailyLogin, now);
	const today = ready ? next : state.dailyLogin?.streak ?? 0;
	const reward = getLoginReward(next, state.era.id);
	const days = Array.from({ length: LOGIN_STREAK_DAYS }, (_, index) => {
		const day = index + 1;
		const gift = getLoginReward(day, state.era.id);
		const mark = day < today || (!ready && day === today) ? "ok" : day === today ? "hoje" : "";
		return `Dia ${day}: ${gift.coins} moedas${gift.diamonds ? ` + ${gift.diamonds} diamantes` : ""}${couponPlus(gift.coupons)}${mark ? ` · ${mark}` : ""}`;
	});
	// After claiming, a video gives today's gift again (once a day).
	const canDouble = canDoubleDailyLogin(state.dailyLogin, now);
	const todays = getLoginReward(Math.max(1, state.dailyLogin?.streak ?? 1), state.era.id);
	const waiting = isAdOpening("gift");
	const recovery = streakRecoveryButtons(state, now);
	if (recovery.length)
		return card("Presente do dia", {
			eyebrow: "SEQUÊNCIA PERDIDA",
			subtitle: streakRecoveryText(state, now),
			icon: gameIcon("flame"),
			tone: "featured",
			lines: days,
			buttons: [
				...recovery,
				act("Recomeçar", "claimDailyLogin", [], { variant: "secondary", ok: "Presente resgatado!", fail: "Já resgatado hoje." }),
			],
		});
	return card("Presente do dia", {
		eyebrow: `SEQUÊNCIA ${Math.min(today, LOGIN_STREAK_DAYS)}/${LOGIN_STREAK_DAYS}`,
		subtitle: ready
			? "Volte todo dia: o presente cresce a cada dia seguido e o 7º dia dá diamantes. Perder um dia recomeça a sequência."
			: canDouble
				? "Presente resgatado! Assista um vídeo curto e ganhe o presente de hoje de novo."
				: "Presente de hoje resgatado. Volte amanhã para continuar a sequência.",
		icon: gameIcon("gift"),
		tone: ready || canDouble ? "featured" : "",
		badge: ready ? "Novo" : canDouble ? "Dobre" : "Resgatado",
		lines: days,
		buttons: ready
			? [
					act(
						`Resgatar ${reward.coins} moedas${reward.diamonds ? ` + ${reward.diamonds} diamantes` : ""}${couponPlus(reward.coupons)}`,
						"claimDailyLogin",
						[],
						{ variant: "success", ok: "Presente resgatado! Assista um vídeo para dobrar.", fail: "Já resgatado hoje." },
					),
				]
			: canDouble
				? [
						act(
							waiting ? "Abrindo o vídeo…" : `Dobrar com vídeo · +${todays.coins} moedas${todays.diamonds ? ` + ${todays.diamonds} diamantes` : ""}`,
							"watchRewardedAd",
							["gift"],
							{ variant: "gem", icon: gameIcon("television"), enabled: !waiting, ok: "" },
						),
					]
				: [],
	});
}

// The rewarded videos (Lucas 06/11 diamonds, 10/11 coins): the player picks the prize, 7 videos a day for each.
// "diamonds" pays AD_REWARD_DIAMONDS; "coins" pays by the player's level (src/services/rewarded-ads.ts).
function videoCard(state: Parameters<Routes[string]>[0], placement: "diamonds" | "coins", missing = 0): Card {
	const coins = placement === "coins";
	const offer = coins ? getRewardedCoinAdOffer(state.rewardedAds, state.market.level) : getRewardedAdOffer(state.rewardedAds);
	const perDay = coins ? AD_DAILY_COIN_VIDEOS : Math.floor(AD_DAILY_DIAMONDS / AD_REWARD_DIAMONDS);
	const prize = coins ? `+${fmt(offer.reward)} moedas` : `+${offer.reward} diamantes`;
	const lastAny = getLastAdEvent();
	const last = lastAny && (lastAny.placement ?? "diamonds") === placement ? lastAny : null;
	const waiting = isAdOpening(placement);
	const status = last?.kind === "rewarded"
		? last.label || `Você ganhou +${last.diamonds} diamantes!`
		: last?.kind === "failed"
			? "O vídeo não carregou. Tente de novo."
			: last?.kind === "closed"
				? "Vídeo fechado antes do fim · sem prêmio"
				: waiting
					? "Abrindo o vídeo…"
					: offer.available
						? adStatusLine()
						: "";
	return card(coins ? "Moedas" : "Diamantes", {
		eyebrow: "VÍDEO GRÁTIS",
		subtitle: offer.available
			? `Assista um vídeo curto e ganhe ${prize}`
			: `Você já ganhou ${coins ? "as moedas" : "os diamantes"} de vídeo de hoje · volta em ${formatAdWait(offer.waitMs)}`,
		icon: gameIcon(coins ? "coin" : "diamond"),
		badge: missing > 0 && offer.available ? "Grátis" : "",
		tone: last?.kind === "rewarded" ? "success" : last ? "danger" : waiting ? "warning" : "info",
		lines: [
			`Hoje: ${offer.watchedToday} de ${perDay} vídeos`,
			...(status ? [status] : [offer.available ? (coins ? "O prêmio cresce a cada nível" : "Some os diamantes e acelere o que quiser") : "Novos vídeos à meia-noite"]),
		],
		buttons: [
			act(waiting ? "Aguardando…" : `Assistir · ${coins ? `+${fmt(offer.reward)}` : `+${offer.reward}`}`, "watchRewardedAd", [placement], {
				variant: coins ? "coin" : "gem",
				icon: gameIcon("television"),
				// Pressable while the video loads or after a failed load: Unity loads one and opens it (Lucas 08/11).
				enabled: offer.available && !waiting,
				ok: "",
			}),
		],
	});
}

// GDPR: where Google's consent tool asks for it, the player can change their ads choice at any time.
function adPrivacyCard(): Card[] {
	return adsStore.privacyOptions
		? [card("Privacidade dos anúncios", {
				subtitle: "Mude a sua escolha sobre os anúncios a qualquer momento.",
				icon: gameIcon("television"),
				buttons: [act("Privacidade dos anúncios", "openAdPrivacy", [], { variant: "secondary", ok: "" })],
			})]
		: [];
}

// "Prêmios grátis": everything free in one place, opened from the HUD's side buttons — the daily gift (and its
// video to double it), the diamond videos, and a nudge to save the progress with Google.
function accountNudgeCard(): Card | null {
	const signedIn = !["unavailable", "signed-out", "signing-in"].includes(cloudStore.status);
	if (signedIn || cloudStore.status === "unavailable") return null;
	// Names only the logins this device offers (the iPhone has just Apple for now).
	const providers = cloudStore.providers.length ? cloudStore.providers : ["google"];
	const apple = providers.includes("apple"), google = providers.includes("google");
	return card("Salve seu progresso", {
		eyebrow: "CONTA",
		subtitle:
			apple && google
				? "Entre com a Apple ou com o Google e seus diamantes e o mercado continuam em qualquer celular."
				: apple
					? "Entre com a Apple e seus diamantes e o mercado continuam em qualquer celular."
					: "Entre com Google e seus diamantes e o mercado continuam em qualquer celular.",
		icon: gameIcon("smartphone"),
		tone: "info",
		buttons: [go(google && !apple ? "Entrar com Google" : "Entrar", "conta", { variant: "primary" })],
	});
}

// Pacote inicial (Lucas 11/11): once, in the first 48 h after the tutorial; the best value of the store.
function leftText(ms: number) {
	const minutes = Math.max(1, Math.ceil(ms / 60_000));
	return minutes >= 60 ? `${Math.floor(minutes / 60)} h ${minutes % 60} min` : `${minutes} min`;
}
export function starterOfferCard(state: Parameters<Routes[string]>[0], now = Date.now()): Card | null {
	const purchased = state.currencyPurchases.purchasedPackIds;
	if (!isStarterOfferOpen(state.perks, purchased, now)) return null;
	const pack = currencyPacks.find((item) => item.id === STARTER_PACK_ID);
	if (!pack) return null;
	const coins = getCurrencyPackCoins(pack, state.era.id);
	const bandana = petCosmetics.find((item) => item.id === pack.extras?.petCosmeticId);
	const price = getPackPrice(pack.productId);
	const busy = iapStore.busyProductId === pack.productId;
	const event = getPackEvent(pack.productId);
	const coupons = pack.extras?.freightCoupons ?? 0;
	return card(pack.name, {
		eyebrow: "OFERTA",
		subtitle: [
			`${fmt(pack.diamonds)} diamantes`,
			`${fmt(coins)} moedas`,
			"+1 caminhão",
			coupons === 1 ? "1 cupom de frete" : `${coupons} cupons de frete`,
			...(bandana ? [`${bandana.name} para o Caramelo`] : []),
		].join(" + "),
		icon: gameIcon("gift"),
		badge: `${Math.max(1, Math.ceil((getStarterOfferEnd(state.perks) - now) / 3_600_000))}h`,
		tone: "featured",
		lines: [
			`Termina em ${leftText(getStarterOfferEnd(state.perks) - now)}`,
			"Só uma vez: o melhor valor da loja.",
			...(event?.text ? [event.text] : []),
		],
		buttons: [
			act(busy ? "Aguardando…" : price ? `Comprar · ${price}` : "—", "buyCurrencyPack", [pack.id], {
				variant: "primary",
				enabled: !busy && !!price,
				ok: "Abrindo a loja…",
			}),
		],
	});
}

export const routes: Routes = {
	// "Grátis" (the HUD's diamond button, Lucas 10/11): watch a video and pick the prize.
	video: (state) =>
		page("video", "Vídeo grátis", [videoCard(state, "diamonds"), videoCard(state, "coins"), ...adPrivacyCard()], {
			icon: gameIcon("television"),
			subtitle: "Assista um vídeo curto e escolha o seu prêmio",
		}),
	// "oferta": the starter pack alone (the HUD button and the one-time popup after the tutorial).
	oferta: (state) => {
		const starter = starterOfferCard(state);
		return page("oferta", "Oferta especial", starter ? [starter] : [card("Oferta encerrada", { icon: gameIcon("gift"), tone: "locked", subtitle: "Esta oferta já acabou ou já foi comprada." })], {
			icon: gameIcon("gift"),
			subtitle: "Pacote Inicial",
		});
	},
	gratis: (state) =>
		page(
			"gratis",
			"Prêmios grátis",
			[
				dailyGiftCard(state),
				videoCard(state, "diamonds", 1),
				videoCard(state, "coins", 1),
				...adPrivacyCard(),
				...[accountNudgeCard()].filter((c): c is Card => !!c),
				card("Loja de diamantes", {
					eyebrow: "OFERTAS",
					subtitle: "Pacotes de diamantes e moedas para acelerar o mercado.",
					icon: gameIcon("diamond"),
					buttons: [go("Abrir a loja", "currency", { variant: "gem" })],
				}),
			],
			{ icon: gameIcon("gift"), subtitle: "Presente do dia, vídeos e ofertas" },
		),
	missions: (state, [arg]) => {
		const filter: MissionFilter = missionFilters.some((f) => f.id === arg)
			? (arg as MissionFilter)
			: "active";
		const entries = missions.map((mission) => ({
			mission,
			progress: getMissionProgress(mission, state),
			status: getMissionStatus(mission, state),
		}));
		const claimable = entries.filter((e) => e.status === "claimable").length;
		const claimed = entries.filter((e) => e.status === "claimed").length;
		const filtered = entries
			.filter((entry) =>
				filter === "active"
					? entry.status === "active" || entry.status === "claimable"
					: entry.status === filter,
			)
			.sort((first, second) => {
				if (first.status === "claimable" && second.status !== "claimable") return -1;
				if (second.status === "claimable" && first.status !== "claimable") return 1;
				return (
					first.mission.requiredLevel - second.mission.requiredLevel ||
					first.mission.goal - second.mission.goal
				);
			});
		const cards: Card[] = [
			card("Central de missões", {
				eyebrow: "JORNADA DO MERCADO",
				subtitle: "Complete objetivos e resgate recompensas.",
				icon: gameIcon("target"),
				badge: `Nível ${state.market.level}`,
				lines: [
					`Progresso total: ${claimed}/${missions.length}`,
					`${claimable} para resgatar · ${claimed} concluídas · ${missions.length - claimed} restantes`,
				],
				progress: ratio(claimed, missions.length),
			}),
			weeklyEventCard(state),
			dailyGiftCard(state),
			albumSummaryCard(state),
		];
		if (!filtered.length)
			cards.push(
				card("Tudo limpo por aqui", {
					icon: gameIcon("success"),
					subtitle: "Continue evoluindo para desbloquear novos objetivos.",
				}),
			);
		for (const { mission, progress, status } of filtered) {
			const shown = Math.min(progress, mission.goal);
			const tag =
				status === "locked"
					? ` · Nível ${mission.requiredLevel}`
					: status === "claimed"
						? " · ✓ RESGATADA"
						: "";
			const rewards = describeMissionReward(mission, state);
			cards.push(
				card(mission.title, {
					eyebrow: `${missionCategoryLabels[mission.category]}${tag}`,
					subtitle: mission.description,
					icon: gameIcon(getMissionIcon(mission.id)),
					badge: `${fmt(shown)}/${fmt(mission.goal)}`,
					tone:
						status === "claimable"
							? "success"
							: status === "locked"
								? "locked"
								: status === "claimed"
									? "info"
									: "",
					lines: [
						`${status === "locked" ? "BLOQUEADA" : "PROGRESSO"}: ${fmt(shown)} / ${fmt(mission.goal)}`,
						`Recompensas: ${rewards.join(", ")}`,
					],
					progress: ratio(shown, mission.goal),
					buttons:
						status === "claimable"
							? [
									act("Resgatar", "claimMission", [mission.id], {
										variant: "success",
										ok: `Recompensa resgatada: ${rewards.join(", ")}`,
										fail: "Não foi possível resgatar.",
									}),
								]
							: [],
				}),
			);
		}
		return page(`missions:${filter}`, "Missões", cards, {
			subtitle: claimable > 0 ? `${claimable} pronta(s)` : "Seus objetivos",
			icon: gameIcon("trophy"),
			chips: missionFilters.map((f) =>
				swap(f.label, `missions:${f.id}`, f.id === filter),
			),
		});
	},
	album: (state) => {
		const claimedIds = state.albumClaimedIds ?? [];
		const cards = albumCollections.map((collection) => {
			const progress = getCollectionProgress(collection, state.market.soldByProduct);
			const claimed = claimedIds.includes(collection.id);
			const names = collection.productIds.map((id) => {
				const product = itemCatalog.find((item) => item.id === id);
				const sold = state.market.soldByProduct[id] ?? 0;
				return `${isProductCollected(state.market.soldByProduct, id) ? "ok" : `${Math.min(sold, SALES_TO_COLLECT)}/${SALES_TO_COLLECT}`} · ${product?.name ?? `#${id}`}`;
			});
			const prize = `${fmt(collection.reward.coins)} moedas + ${collection.reward.diamonds} diamantes`;
			return card(collection.name, {
				eyebrow: claimed ? "COMPLETA" : `${progress.collected}/${progress.total} FIGURINHAS`,
				icon: productIcon(collection.productIds[0]),
				tone: claimed ? "" : progress.complete ? "featured" : "",
				badge: claimed ? "Resgatado" : prize,
				progress: ratio(progress.collected, progress.total),
				lines: names,
				buttons:
					progress.complete && !claimed
						? [act(`Resgatar ${prize}`, "claimAlbumCollection", [collection.id], { variant: "success", ok: "Coleção completa! Prêmio resgatado." })]
						: [],
			});
		});
		return page("album", "Álbum de produtos", cards, {
			subtitle: `Venda ${SALES_TO_COLLECT} unidades de um produto para ganhar a figurinha`,
			icon: gameIcon("medal"),
		});
	},
	achievements: (state, [arg]) => {
		const filter: AchievementFilter = achievementFilters.some((f) => f.id === arg)
			? (arg as AchievementFilter)
			: "all";
		const level = state.market.level;
		const totals = getAchievementTotals(state);
		const legendaryStars = achievements
			.filter((a) => a.rarity === "legendary")
			.reduce((total, a) => total + getAchievementStars(a, state), 0);
		const entries = achievements
			.filter((a) => filter === "all" || a.category === filter)
			.map((achievement) => ({
				achievement,
				progress: getAchievementProgress(achievement, state),
				stars: getAchievementStars(achievement, state),
			}))
			.sort((first, second) => {
				const firstLocked = level < first.achievement.requiredLevel ? 1 : 0;
				const secondLocked = level < second.achievement.requiredLevel ? 1 : 0;
				const firstComplete =
					first.stars === first.achievement.thresholds.length ? 1 : 0;
				const secondComplete =
					second.stars === second.achievement.thresholds.length ? 1 : 0;
				return (
					firstLocked - secondLocked ||
					firstComplete - secondComplete ||
					second.stars - first.stars ||
					achievementRarityOrder[second.achievement.rarity] -
						achievementRarityOrder[first.achievement.rarity]
				);
			});
		const cards: Card[] = [
			card("Conquistas", {
				eyebrow: "SALÃO DA FAMA",
				subtitle: "Cada nível concluído vale uma estrela.",
				icon: gameIcon("medal"),
				badge: `${Math.round((totals.stars / totals.totalStars) * 100)}%`,
				lines: [
					`${totals.stars}/${totals.totalStars} estrelas conquistadas`,
					`${totals.achievementsCompleted} máximas · ${legendaryStars} lendárias · ${achievements.length} desafios`,
				],
				progress: ratio(totals.stars, totals.totalStars),
			}),
		];
		for (const { achievement, progress, stars } of entries) {
			const { thresholds } = achievement;
			const isLocked = level < achievement.requiredLevel;
			const isComplete = stars === thresholds.length;
			const previousGoal = stars === 0 ? 0 : thresholds[stars - 1];
			const nextGoal = thresholds[stars] ?? thresholds[thresholds.length - 1];
			const levelProgress = isComplete
				? 1
				: ratio(progress - previousGoal, Math.max(1, nextGoal - previousGoal));
			const lines = [
				`Metas: ${thresholds.map(formatCompactNumber).join(" · ")}`, // stars are in the badge (the font has no ★)
				`${
					isLocked
						? "CONQUISTA BLOQUEADA"
						: isComplete
							? "NÍVEL MÁXIMO ALCANÇADO"
							: `PRÓXIMA ESTRELA · NÍVEL ${stars + 1}`
				}: ${fmt(Math.min(progress, nextGoal))} / ${fmt(nextGoal)}`,
			];
			if (achievement.rarity === "legendary")
				lines.push("O quinto nível pertence aos gerentes mais dedicados.");
			cards.push(
				card(achievement.title, {
					eyebrow: `${achievementCategoryLabels[achievement.category]} · ${rarityLabels[achievement.rarity]}${isLocked ? ` · Nível ${achievement.requiredLevel}` : ""}`,
					subtitle: achievement.description,
					icon: achievement.targetProductId
						? productIcon(achievement.targetProductId)
						: gameIcon(getAchievementIcon(achievement.id)),
					badge: `${stars}/${thresholds.length}`,
					tone: isLocked ? "locked" : isComplete ? "success" : "",
					lines,
					progress: isLocked ? 0 : levelProgress,
				}),
			);
		}
		return page(`achievements:${filter}`, "Conquistas", cards, {
			subtitle: `${achievements.length} conquistas · 5 níveis em cada uma`,
			icon: gameIcon("crown"),
			chips: achievementFilters.map((f) =>
				swap(f.label, `achievements:${f.id}`, f.id === filter),
			),
		});
	},
	// The diamond store (Lucas 12/10): real-money packs bought through the App Store / Google Play (Unity IAP,
	// CheckoutIap.cs). "currency:<filter>:<missing>" opens it after the player tried to spend diamonds they do not
	// have, saying how many are missing and pointing at the smallest pack that covers it.
	currency: (state, [arg, missingArg]) => {
		const filter = currencyPackSections.some((s) => s.category === arg) ? arg : "all";
		const missing = Math.max(0, Number.parseInt(missingArg ?? "", 10) || 0);
		const diamonds = state.logistics.premiumCurrency;
		const purchased = state.currencyPurchases.purchasedPackIds;
		const cards: Card[] = [
			card("Banco do Mercado", {
				subtitle: "Reforce o caixa e acelere as próximas melhorias.",
				icon: gameIcon("bank"),
				lines: [
					`Moedas atuais: ${fmt(state.coins)}`,
					`Diamantes atuais: ${fmt(diamonds)}`,
				],
			}),
		];
		if (missing > 0)
			cards.push(
				card(missing === 1 ? "Falta 1 diamante" : `Faltam ${fmt(missing)} diamantes`, {
					subtitle: "Diamantes terminam qualquer obra, produção ou entrega na hora. Escolha um pacote:",
					icon: gameIcon("diamond"),
					tone: "featured",
					lines: [`Você tem ${fmt(diamonds)} diamantes.`],
				}),
			);
		// Pacote inicial first while it lasts (Lucas 11/11).
		const starter = filter === "all" || filter === "bundle" ? starterOfferCard(state) : null;
		if (starter) cards.push(starter);
		// Free diamonds for a rewarded video (src/services/rewarded-ads.ts): by choice, a few a day.
		if (filter === "all" || filter === "diamonds") cards.push(videoCard(state, "diamonds", missing));
		if (filter === "all" || filter === "coins") cards.push(videoCard(state, "coins"));
		// The packs can only be bought once the store answered: until then no price and no "Comprar" (a price of our
		// own table must never look purchasable, App Store review 29/10). Each device names only its own store.
		const platform = storePlatform();
		if (iapStore.status === "unavailable")
			cards.push(
				card("Loja indisponível", {
					subtitle:
						platform === "ios"
							? "As compras não estão disponíveis neste aparelho agora (sem conexão com a App Store)."
							: platform === "android"
								? "As compras não estão disponíveis neste aparelho agora (sem conexão com o Google Play)."
								: "As compras não estão disponíveis nesta versão do jogo.",
					icon: gameIcon("bank"),
					tone: "locked",
					lines: platform === "other" ? [] : ["Confira a internet e tente de novo."],
					buttons:
						platform === "other"
							? []
							: [act("Tentar de novo", "retryIapStore", [], { variant: "primary", ok: "Conectando à loja…" })],
				}),
			);
		else if (iapStore.status === "starting")
			cards.push(
				card("Conectando à loja…", {
					subtitle:
						platform === "ios"
							? "Os preços aparecem assim que a App Store responder."
							: platform === "android"
								? "Os preços aparecem assim que o Google Play responder."
								: "Os preços aparecem assim que a loja responder.",
					icon: gameIcon("bank"),
					tone: "info",
				}),
			);
		// The smallest diamond pack that covers what is missing.
		const recommended = missing
			? currencyPacks
					.filter((p) => p.category === "diamonds" && p.diamonds >= missing)
					.sort((x, y) => x.diamonds - y.diamonds)[0]?.id
			: undefined;
		for (const section of currencyPackSections) {
			if (filter !== "all" && section.category !== filter) continue;
			for (const pack of currencyPacks.filter((p) => p.category === section.category)) {
				// The starter pack has its own card at the top.
				if (pack.limitedTime || !isCurrencyPackAvailable(pack, purchased)) continue;
				const coins = getCurrencyPackCoins(pack, state.era.id);
				const rewards = [
					coins > 0 ? `${fmt(coins)} moedas` : "",
					pack.diamonds > 0 ? `${fmt(pack.diamonds)} diamantes` : "",
				].filter(Boolean);
				// Just the price on the button (Lucas 12/10), in the player's currency; "—" while the store has none.
				const price = getPackPrice(pack.productId);
				const busy = iapStore.busyProductId === pack.productId;
				// What just happened to this pack's purchase shows on its own card.
				const event = getPackEvent(pack.productId);
				const status = busy && !event ? "Aguardando a loja…" : (event?.text ?? "");
				const tone = event?.kind === "bought"
					? "success"
					: event?.kind === "cancelled" || event?.kind === "failed"
						? "danger"
						: busy
							? "warning"
							: pack.id === recommended
								? "featured"
								: pack.category === "bundle"
									? "info"
									: "";
				cards.push(
					card(pack.name, {
						eyebrow: section.title.toUpperCase(),
						subtitle: rewards.join(" + "),
						icon: gameIcon(
							pack.category === "bundle"
								? "gift"
								: pack.category === "coins"
									? "coin"
									: "diamond",
						),
						badge: pack.id === recommended ? "Recomendado" : pack.badge,
						tone,
						lines: status ? [status] : pack.coinTurns ? ["Cresce com a sua expansão"] : [],
						buttons: [
							act(busy ? "Aguardando…" : price || "—", "buyCurrencyPack", [pack.id], {
								variant: pack.category === "coins" ? "coin" : pack.category === "diamonds" ? "gem" : "primary",
								enabled: !busy && !!price,
								ok: "Abrindo a loja…",
							}),
						],
					}),
				);
			}
		}
		return page(`currency:${filter}`, "Diamantes", cards, {
			subtitle: "Banco do Mercado",
			icon: gameIcon("diamond"),
			chips: [
				swap("Todos", "currency:all", filter === "all"),
				...currencyPackSections.map((s) =>
					swap(s.title, `currency:${s.category}`, s.category === filter),
				),
			],
		});
	},
};
