import type { AchievementCategory, AchievementRarity } from "@/@types/achievement";
import type { MissionCategory } from "@/@types/mission";
import { achievementRarityOrder, achievements } from "@/data/achievements";
import { currencyPackSections, currencyPacks } from "@/data/currency-packs";
import { getAchievementIcon, getMissionIcon } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import { missions } from "@/data/missions";
import {
	getAchievementProgress,
	getAchievementStars,
	getAchievementTotals,
} from "@/services/achievements";
import { getMissionProgress, getMissionStatus } from "@/services/missions";
import {
	canClaimDailyLogin,
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

const productName = (id: number) =>
	itemCatalog.find((item) => item.id === id)?.name ?? `#${id}`;

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
	return card("Presente do dia", {
		eyebrow: `SEQUÊNCIA ${Math.min(today, LOGIN_STREAK_DAYS)}/${LOGIN_STREAK_DAYS}`,
		subtitle: ready
			? "Volte todo dia: o presente cresce a cada dia seguido e o 7º dia dá diamantes. Perder um dia recomeça a sequência."
			: "Presente de hoje resgatado. Volte amanhã para continuar a sequência.",
		icon: gameIcon("gift"),
		tone: ready ? "featured" : "",
		badge: ready ? "Novo" : "Resgatado",
		lines: days,
		buttons: ready
			? [
					act(
						`Resgatar ${reward.coins} moedas${reward.diamonds ? ` + ${reward.diamonds} diamantes` : ""}`,
						"claimDailyLogin",
						[],
						{ variant: "success", ok: "Presente resgatado!", fail: "Já resgatado hoje." },
					),
				]
			: [],
	});
}

export const routes: Routes = {
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
			const rewards = [
				`${fmt(mission.reward.coins)} moedas`,
				...(mission.reward.items ?? []).map(
					(item) => `${item.quantity}× ${productName(item.productId)}`,
				),
			];
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
										ok: "Recompensa resgatada e adicionada ao mercado.",
										fail: "Não foi possível resgatar. Verifique o espaço disponível no estoque.",
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
				`${"★".repeat(stars)}${"☆".repeat(thresholds.length - stars)}  ${thresholds.map(formatCompactNumber).join(" · ")}`,
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
					badge: `★ ${stars}/${thresholds.length}`,
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
	// No App Store / Google Play on desktop: each pack credits directly with the
	// same input the RN store hook passes after a successful purchase.
	currency: (state, [arg]) => {
		const filter = currencyPackSections.some((s) => s.category === arg) ? arg : "all";
		const cards: Card[] = [
			card("Banco do Mercado", {
				subtitle: "Reforce o caixa e acelere as próximas melhorias.",
				icon: gameIcon("bank"),
				lines: [
					`Moedas atuais: ${fmt(state.coins)}`,
					`Diamantes atuais: ${fmt(state.logistics.premiumCurrency)}`,
					"Desktop: compras creditadas sem loja (teste).",
				],
			}),
		];
		for (const section of currencyPackSections) {
			if (filter !== "all" && section.category !== filter) continue;
			for (const pack of currencyPacks.filter((p) => p.category === section.category)) {
				const rewards = [
					pack.coins > 0 ? `${fmt(pack.coins)} moedas` : "",
					pack.diamonds > 0 ? `${fmt(pack.diamonds)} diamantes` : "",
				].filter(Boolean);
				cards.push(
					card(pack.name, {
						eyebrow: section.title.toUpperCase(),
						subtitle: pack.badge,
						icon: gameIcon(
							pack.category === "bundle"
								? "gift"
								: pack.category === "coins"
									? "coin"
									: "diamond",
						),
						badge: pack.fallbackPrice,
						tone: pack.category === "bundle" ? "info" : "",
						lines: [rewards.join(" + ")],
						buttons: [
							act(
								`Comprar · ${pack.fallbackPrice}`,
								"grantCurrencyPurchase",
								[
									{
										coins: pack.coins,
										diamonds: pack.diamonds,
										transactionId: `desktop-${Date.now()}-${pack.id}`,
									},
								],
								{
									variant:
										pack.category === "coins"
											? "coin"
											: pack.category === "diamonds"
												? "gem"
												: "primary",
									ok: `${pack.name} foi creditado na sua conta.`,
									fail: "Esta compra já havia sido creditada.",
								},
							),
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
