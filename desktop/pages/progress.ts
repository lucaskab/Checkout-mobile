import type { AchievementCategory, AchievementRarity } from "@/@types/achievement";
import type { MissionCategory } from "@/@types/mission";
import { achievementRarityOrder, achievements } from "@/data/achievements";
import {
	currencyPackSections,
	currencyPacks,
	getCurrencyPackCoins,
	isCurrencyPackAvailable,
} from "@/data/currency-packs";
import { getPackEvent, getPackPrice, iapStore } from "../iap";
import { adsStore, getLastAdEvent, isAdOpening } from "../ads";
import { AD_DAILY_CAP, formatAdWait, getRewardedAdOffer } from "@/services/rewarded-ads";
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
	LOGIN_STREAK_DAYS,
} from "@/services/daily-login";
import type { Routes } from ".";
import { getWeekEnd, getWeeklyProgress, getWeeklyReward } from "@/services/weekly-event";
import {
	albumCollections,
	getCollectionProgress,
	isProductCollected,
	SALES_TO_COLLECT,
} from "@/data/product-album";
import {
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
	const prize = `${fmt(reward.coins)} moedas + ${reward.diamonds} diamantes`;
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
		return `Dia ${day}: ${gift.coins} moedas${gift.diamonds ? ` + ${gift.diamonds} diamantes` : ""}${mark ? ` · ${mark}` : ""}`;
	});
	// After claiming, a video gives today's gift again (once a day).
	const canDouble = canDoubleDailyLogin(state.dailyLogin, now);
	const todays = getLoginReward(Math.max(1, state.dailyLogin?.streak ?? 1), state.era.id);
	const waiting = isAdOpening("gift");
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
						`Resgatar ${reward.coins} moedas${reward.diamonds ? ` + ${reward.diamonds} diamantes` : ""}`,
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
							{ variant: "gem", icon: gameIcon("television"), enabled: !waiting && adsStore.status !== "unavailable", ok: "" },
						),
					]
				: [],
	});
}

// "Diamantes grátis": watch a short video for a few diamonds (max AD_DAILY_CAP a day, a few minutes apart).
function adCard(state: State, missing: number): Card {
	const offer = getRewardedAdOffer(state.rewardedAds);
	const last = getLastAdEvent();
	const waiting = isAdOpening("diamonds");
	const status = last?.kind === "rewarded"
		? last.label || `Você ganhou +${last.diamonds} diamantes!`
		: last?.kind === "failed"
			? "O vídeo não carregou. Tente de novo."
			: last?.kind === "closed"
				? "Vídeo fechado antes do fim · sem prêmio"
				: waiting
					? "Abrindo o vídeo…"
					: "";
	const label = offer.available
		? `Assistir · +${offer.reward}`
		: offer.reason === "daily-cap"
			? "Volte amanhã"
			: `Próximo em ${formatAdWait(offer.waitMs)}`;
	return card("Diamantes grátis", {
		eyebrow: "VÍDEO",
		subtitle: `Assista um vídeo curto e ganhe diamantes · hoje: ${offer.watchedToday} de ${AD_DAILY_CAP}`,
		icon: gameIcon("television"),
		badge: missing > 0 && offer.available ? "Grátis" : "",
		tone: last?.kind === "rewarded" ? "success" : last && last.kind !== "rewarded" ? "danger" : waiting ? "warning" : "info",
		lines: status ? [status] : [offer.watchedToday + 1 >= AD_DAILY_CAP && offer.available ? "O último do dia vale mais!" : "Some os diamantes e acelere o que quiser"],
		buttons: [
			act(waiting ? "Aguardando…" : label, "watchRewardedAd", [], {
				variant: "gem",
				enabled: offer.available && !waiting && adsStore.status !== "unavailable",
				ok: "",
			}),
			// GDPR: where Google's consent tool asks for it, the player can change their ads choice at any time.
			...(adsStore.privacyOptions
				? [act("Privacidade dos anúncios", "openAdPrivacy", [], { variant: "secondary", ok: "" })]
				: []),
		],
	});
}

// "Prêmios grátis": everything free in one place, opened from the HUD's side buttons — the daily gift (and its
// video to double it), the diamond videos, and a nudge to save the progress with Google.
function accountNudgeCard(): Card | null {
	const signedIn = !["unavailable", "signed-out", "signing-in"].includes(cloudStore.status);
	if (signedIn || cloudStore.status === "unavailable") return null;
	return card("Salve seu progresso", {
		eyebrow: "CONTA",
		subtitle: "Entre com Google e seus diamantes e o mercado continuam em qualquer celular.",
		icon: gameIcon("smartphone"),
		tone: "info",
		buttons: [go("Entrar com Google", "conta", { variant: "primary" })],
	});
}

export const routes: Routes = {
	gratis: (state) =>
		page(
			"gratis",
			"Prêmios grátis",
			[
				dailyGiftCard(state),
				adCard(state, 1),
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
		// Free diamonds for a rewarded video (src/services/rewarded-ads.ts): by choice, a few a day.
		if (filter === "all" || filter === "diamonds") cards.push(adCard(state, missing));
		if (iapStore.status === "unavailable")
			cards.push(
				card("Loja indisponível", {
					subtitle: "As compras não estão disponíveis neste aparelho agora (sem conexão com a App Store / Google Play).",
					icon: gameIcon("bank"),
					tone: "locked",
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
				if (!isCurrencyPackAvailable(pack, purchased)) continue;
				const coins = getCurrencyPackCoins(pack, state.era.id);
				const rewards = [
					coins > 0 ? `${fmt(coins)} moedas` : "",
					pack.diamonds > 0 ? `${fmt(pack.diamonds)} diamantes` : "",
				].filter(Boolean);
				// Just the price on the button (Lucas 12/10), in the player's currency.
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
							act(busy ? "Aguardando…" : price, "buyCurrencyPack", [pack.id], {
								variant: pack.category === "coins" ? "coin" : pack.category === "diamonds" ? "gem" : "primary",
								enabled: !busy,
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
