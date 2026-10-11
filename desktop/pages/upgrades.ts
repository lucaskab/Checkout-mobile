import type { EmployeeRole } from "@/@types/employee";
import type { ShopCategory, ShopItemDefinition, ShopItemQuality } from "@/@types/shop";
import { getMarketEra } from "@/data/economy";
import { employeeDefinitions, isEmployeeEraReached } from "@/data/employees";
import { getShopCategoryIcon, getShopItemIcon } from "@/data/game-icon-assets";
import {
	formatBuildDuration,
	formatConstructionCountdown,
	getMarketExpansionSkipCost,
	getMissingMarketExpansionPrerequisites,
	marketExpansions,
} from "@/data/market-expansions";
import { shopCategories, shopItems } from "@/data/shop-items";
import { AUTO_CASHIER_INTERVAL_MS } from "@/services/checkout-counter";
import { getActiveGameEventEffects } from "@/services/game-events";
import { getShopEffects } from "@/services/shop-effects";
import {
	EMPLOYEE_MAX_LEVEL,
	getEmployeeTrainingCost,
} from "@/services/employee-progression";
import {
	EMPLOYEE_PAYROLL_INTERVAL_MS,
	getEmployeeEffects,
	getEmployeePayrollCost,
	getShiftSalary,
} from "@/services/employees";
import type { Routes } from ".";
import { getShopItemBuildStatus } from "@/services/interior-construction";
import {
	act,
	card,
	expansionIcon,
	fmt,
	gameIcon,
	page,
	ratio,
	type State,
	swap,
} from "../view-kit";

// Same icon mapping as roleIcon() in src/screens/team/index.tsx.
function roleIcon(role: EmployeeRole) {
	switch (role) {
		case "cashier":
			return "calculator" as const;
		case "stock_clerk":
			return "package" as const;
		case "cleaner":
			return "broom" as const;
	}
}

// Copied from src/screens/shop/components/item-card/index.tsx.
function getItemQuality(item: ShopItemDefinition): ShopItemQuality {
	if (item.quality) return item.quality;
	if (item.level >= 50) return "lendario";
	if (item.level >= 24) return "epico";
	if (item.level >= 10) return "raro";
	if (item.level >= 5) return "incomum";
	return "comum";
}

const qualityLabels: Record<ShopItemQuality, string> = {
	comum: "Comum",
	incomum: "Incomum",
	raro: "Raro",
	epico: "Épico",
	lendario: "Lendário",
	mitico: "Mítico",
};


function formatPrice(price: number) {
	if (price >= 1_000_000_000) return `${(price / 1_000_000_000).toFixed(0)}B`;
	if (price >= 1_000_000) {
		const value = price / 1_000_000;
		return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)}M`;
	}
	if (price >= 1_000) return price.toLocaleString("pt-BR");
	return price.toString();
}

// How fast the line moves without the player: the cashier (sped up by the shop) plus self-checkout.
function checkoutPaceLine(state: State) {
	const shop = getShopEffects(state.shop);
	const cashier = state.employees.employees
		.filter((employee) => employee.isWorking && employee.role === "cashier")
		.reduce((total, employee) => total + employee.efficiency, 0);
	const events = getActiveGameEventEffects(state.events, Date.now());
	const rate = cashier * events.staffSpeedMultiplier * shop.cashierSpeedMultiplier + shop.selfCheckoutRate;
	if (rate <= 0) return "Sem operador: quem passa as compras no caixa é você";
	return `Caixa automático: 1 cliente a cada ${(Math.round((AUTO_CASHIER_INTERVAL_MS / 1000 / rate) * 10) / 10).toLocaleString("pt-BR")} s`;
}

function timer(ms: number) {
	const total = Math.max(0, Math.ceil(ms / 1000));
	const minutes = Math.floor(total / 60);
	const seconds = total % 60;
	return `${minutes}:${String(seconds).padStart(2, "0")}`;
}

export const routes: Routes = {
	team: (state) => {
		const { coins, employees } = state;
		const level = state.market.level;
		const payroll = getEmployeePayrollCost(employees);
		const effects = getEmployeeEffects(employees);
		const remaining = employees.nextPayrollAt - Date.now();
		const working = employees.employees.filter((item) => item.isWorking).length;

		const payrollCard = card("Folha de pagamento", {
			eyebrow: "", // the Equipe category title says it
			icon: gameIcon("manager"),
			badge: `🪙 ${fmt(coins)}`,
			tone: payroll > coins ? "danger" : "info",
			subtitle:
				"Uma boa equipe transforma vendas em rotina: atendimento, reposição e reputação.",
			lines: [
				`Ativos: ${working}/${employees.employees.length}`,
				`Próximo pagamento: 🪙 ${fmt(payroll)} em ${timer(remaining)}`,
				`Total já pago: 🪙 ${fmt(employees.totalSalariesPaid)}`,
				...(payroll > coins
					? ["Sem saldo para a folha: a equipe será pausada"]
					: []),
				checkoutPaceLine(state),
				`Reputação +${effects.storeReputationBonus}`,
			],
			progress: 1 - ratio(remaining, EMPLOYEE_PAYROLL_INTERVAL_MS),
		});

		const roleCards = employeeDefinitions.map((definition) => {
			const employee = employees.employees.find(
				(item) => item.role === definition.id,
			);
			const eraLocked = !isEmployeeEraReached(definition, state.era.id);
			const levelLocked = eraLocked || level < definition.level;
			const hireLocked = coins < definition.hireCost;

			if (employee) {
				const cost = getEmployeeTrainingCost(employee);
				const maxed = employee.level >= EMPLOYEE_MAX_LEVEL;
				return card(definition.name, {
					eyebrow: employee.isWorking ? "ATIVO" : "PAUSADO",
					icon: gameIcon(roleIcon(definition.id)),
					badge: `Nv ${employee.level}`,
					tone: employee.isWorking ? "success" : "warning",
					subtitle: definition.description,
					lines: [
						`Nv. ${employee.level} · ${employee.efficiency} eficiência`,
						`🪙 ${getShiftSalary(employee.salary)}/turno`,
					],
					buttons: [
						act(
							employee.isWorking ? "Pausar" : "Ativar",
							"setEmployeeWorking",
							[employee.id, !employee.isWorking],
							{ variant: employee.isWorking ? "secondary" : "success" },
						),
						act(
							maxed ? "Nível máximo" : `Treinar ${fmt(cost)}`,
							"trainEmployee",
							[employee.id],
							{
								variant: "coin",
								icon: gameIcon("coin"),
								enabled: !maxed && coins >= cost,
								ok: `${employee.name} treinado`,
								fail: "Moedas insuficientes",
							},
						),
					],
				});
			}

			return card(definition.name, {
				// The locked button already says which market is needed: no "A PARTIR DE" eyebrow on top.
				eyebrow: eraLocked
					? ""
					: levelLocked
						? `NÍVEL ${definition.level}`
						: "DISPONÍVEL",
				icon: gameIcon(roleIcon(definition.id)),
				tone: levelLocked ? "locked" : "",
				subtitle: definition.description,
				lines: [
					`${definition.efficiency} eficiência · 🪙 ${getShiftSalary(definition.salary)}/turno`,
				],
				buttons: [
					act(
						eraLocked
							? `Precisa do ${getMarketEra(definition.requiredEra).name}`
							: levelLocked
								? `Chegue ao nível ${definition.level}`
								: `Contratar por ${fmt(definition.hireCost)}`,
						"hireEmployee",
						[definition.id],
						{
							variant: "success",
							enabled: !levelLocked && !hireLocked,
							ok: `${definition.name} contratado`,
							fail: "Moedas insuficientes",
						},
					),
				],
			});
		});

		return page("team", "Equipe", [payrollCard, ...roleCards], {
			subtitle: "Monte seu time",
			icon: gameIcon("manager"),
		});
	},
	shop: (state, [arg]) => {
		const category: ShopCategory =
			shopCategories.find((item) => item.id === arg)?.id ?? "equipamentos";
		const coins = state.coins;
		const diamonds = state.logistics.premiumCurrency;
		const level = state.market.level;
		const { consumableAmounts, ownedItemIds } = state.shop;
		const activeBoosts = state.shop.activeBoosts ?? {};
		const now = Date.now();
		// What can be bought first, then what is still locked by level, then what is installed.
		const items = shopItems
			.filter((item) => item.category === category)
			.sort((a, b) => {
				const rank = (item: ShopItemDefinition) =>
					ownedItemIds.includes(item.id) ? 2 : level < item.level ? 1 : 0;
				return rank(a) - rank(b) || a.level - b.level;
			});

		const cards = items.map((item) => {
			const isOwned = ownedItemIds.includes(item.id);
			const required = item.requiresItemId ? shopItems.find((other) => other.id === item.requiresItemId) : undefined;
			const missingRequired = !!required && !ownedItemIds.includes(required.id);
			const isLocked = level < item.level || missingRequired;
			const consumableAmount = consumableAmounts[item.id] ?? 0;
			const isDiamond = Boolean(item.diamondPrice);
			const price = item.diamondPrice ?? item.coinPrice ?? 0;
			const canAfford = isDiamond ? diamonds >= price : coins >= price;
			const quality = getItemQuality(item);
			const isLegendary = quality === "lendario" || quality === "mitico";
			const label = isOwned
				? "Instalado"
				: level < item.level
					? `Nível ${item.level}`
					: missingRequired && required
						? `Precisa de ${required.name}`
					: `Comprar · ${formatPrice(price)}`;

			// Fixtures (second checkout, self-checkout) are installed by the builders over time.
			const build = getShopItemBuildStatus(state, item.id);
			if (build && build.status === "building" && build.construction)
				return card(item.name, {
					eyebrow: "EM INSTALAÇÃO",
					icon: gameIcon("construction"),
					badge: formatConstructionCountdown(build.remainingMs),
					tone: "warning",
					progress: build.progress,
					subtitle: "Os construtores estão instalando no mercado.",
					lines: [`Pronto em ${formatConstructionCountdown(build.remainingMs)}`],
					buttons: [
						act(`Acelerar · 💎 ${build.skipCost}`, "finishInteriorConstructionNow", [build.construction.id], {
							variant: "gem",
							icon: gameIcon("diamond"),
							enabled: diamonds >= build.skipCost,
							ok: `${item.name} pronto!`,
							fail: "Diamantes insuficientes",
						}),
					],
				});

			// Boosters: buy as many as you like, start one when the market needs it.
			if (item.isConsumable) {
				const endsAt = activeBoosts[item.id] ?? 0;
				const running = endsAt > now;
				return card(item.name, {
					eyebrow: running ? "ATIVO AGORA" : isLocked ? `NÍVEL ${item.level}` : "BOOSTER",
					icon: gameIcon(getShopItemIcon(item.id)),
					badge: running ? timer(endsAt - now) : consumableAmount > 0 ? `x${consumableAmount}` : "",
					tone: running ? "success" : isLocked ? "locked" : "",
					progress: running && item.durationMs ? ratio(endsAt - now, item.durationMs) : -1,
					subtitle: item.description,
					lines: [
						`${isDiamond ? "💎" : "🪙"} ${formatPrice(price)} cada`,
						...(consumableAmount > 0 ? [`Guardados: ${consumableAmount}`] : []),
						...(running ? [`Termina em ${timer(endsAt - now)}`] : []),
					],
					buttons: [
						act(isLocked ? `Nível ${item.level}` : formatPrice(price), "purchaseShopItem", [item.id, isDiamond ? "diamonds" : "coins"], {
							variant: isDiamond ? "gem" : "coin",
							icon: gameIcon(isDiamond ? "diamond" : "coin"),
							enabled: !isLocked && canAfford,
							ok: `${item.name} guardado. Use quando quiser.`,
							fail: isLocked ? `Nível ${item.level}` : "Diamantes insuficientes",
						}),
						...(consumableAmount > 0
							? [
									act(running ? "Usar mais um" : "Usar agora", "activateShopBooster", [item.id], {
										variant: "success",
										ok: `${item.name} ativado!`,
										fail: "Nenhum guardado",
									}),
								]
							: []),
					],
				});
			}

			const busy = !!build && build.status === "busy";
			return card(item.name, {
				eyebrow: isOwned ? "ATIVO" : qualityLabels[quality], // no ★: the game font has no star glyph (drew boxes)
				icon: gameIcon(getShopItemIcon(item.id)),
				badge: `Nv ${item.level}`,
				tone: isOwned
					? "success"
					: isLocked
						? "locked"
						: isLegendary
							? "warning"
							: "",
				subtitle: item.description,
				// Level and price are already the badge and the buy button.
				lines: [
					...(isOwned ? ["Funcionando no mercado"] : []),
					...(missingRequired && required ? [`Instale antes: ${required.name}`] : []),
					...(build && !isOwned ? [`Instalação de ${formatBuildDuration(build.durationMs)}${busy ? " · construtores ocupados" : ""}`] : []),
				],
				buttons: [
					act(
						label,
						"purchaseShopItem",
						[item.id, isDiamond ? "diamonds" : "coins"],
						{
							variant: isOwned ? "success" : isDiamond ? "gem" : "coin",
							icon: gameIcon(isDiamond ? "diamond" : "coin"),
							enabled: !isOwned && !isLocked && canAfford && !busy,
							ok: build
								? `Os construtores começaram a instalar ${item.name}.`
								: `${item.name} foi instalado no mercado.`,
							fail: busy
								? "Construtores ocupados com outra obra."
								: missingRequired && required
									? `Instale antes: ${required.name}`
									: isLocked
										? `Nível ${item.level}`
										: isDiamond
										? "Diamantes insuficientes"
										: "Moedas insuficientes",
						},
					),
				],
			});
		});

		const label = shopCategories.find((item) => item.id === category)?.label;
		return page(`shop:${category}`, "Melhorias", cards, {
			subtitle: `LOJA DO MERCADO · ${label} · ${items.length} melhorias · 🪙 ${fmt(coins)} · 💎 ${fmt(diamonds)}`,
			icon: gameIcon("toolbox"),
			chips: shopCategories.map((item) =>
				swap(
					item.label,
					`shop:${item.id}`,
					item.id === category,
					gameIcon(getShopCategoryIcon(item.id)),
				),
			),
		});
	},
	expansions: (state) => {
		const coins = state.coins;
		const diamonds = state.logistics.premiumCurrency;
		const level = state.market.level;
		const unlockedIds = state.unlockedMarketExpansionIds;
		const construction = state.marketExpansionConstruction;
		const remainingMs = construction ? construction.endsAt - Date.now() : 0;
		const skipCost = getMarketExpansionSkipCost(remainingMs);

		const cards = marketExpansions.map((expansion) => {
			const unlocked = unlockedIds.includes(expansion.id);
			const underConstruction = construction?.expansionId === expansion.id;
			const missing = getMissingMarketExpansionPrerequisites(
				expansion,
				unlockedIds,
			);
			const levelLocked =
				level < expansion.requiredLevel || missing.length > 0;
			const hasCoins = coins >= expansion.coinCost;
			const hasDiamonds = diamonds >= expansion.diamondCost;

			if (underConstruction) {
				return card(expansion.name, {
					eyebrow: "🏗️ EM OBRA",
					icon: expansionIcon(expansion.id),
					badge: formatConstructionCountdown(remainingMs),
					tone: "warning",
					subtitle: expansion.description,
					lines: [
						remainingMs > 0
							? `Fica pronta em ${formatConstructionCountdown(remainingMs)}.`
							: "Finalizando a obra...",
					],
					buttons:
						remainingMs > 0
							? [
									act(
										`Acelerar · ${fmt(skipCost)}`,
										"finishMarketExpansionNow",
										[],
										{
											variant: "gem",
											icon: gameIcon("diamond"),
											enabled: diamonds >= skipCost,
											ok: `${expansion.name} concluída`,
											fail: "Diamantes insuficientes",
										},
									),
								]
							: [],
				});
			}

			return card(expansion.name, {
				eyebrow: unlocked ? "LIBERADA" : `NÍVEL ${expansion.requiredLevel}`,
				icon: expansionIcon(expansion.id),
				tone: unlocked ? "success" : levelLocked ? "locked" : "",
				subtitle: expansion.description,
				lines: [
					unlocked
						? "Área pronta para o mercado."
						: level < expansion.requiredLevel
							? `Alcance o nível ${expansion.requiredLevel} para desbloquear.`
							: missing.length > 0
								? `Construa antes: ${missing.map((item) => item.name).join(" e ")}.`
								: construction
									? "Aguarde a obra atual terminar."
									: `🪙 ${fmt(expansion.coinCost)} ou 💎 ${fmt(expansion.diamondCost)}`,
					...(unlocked
						? []
						: [`⏱ Obra de ${formatBuildDuration(expansion.buildDurationMs)}`]),
				],
				buttons:
					unlocked || levelLocked || construction
						? []
						: [
								act(
									fmt(expansion.coinCost),
									"unlockMarketExpansion",
									[expansion.id, "coins"],
									{
										variant: "coin",
										icon: gameIcon("coin"),
										enabled: hasCoins,
										ok: `Obra de ${expansion.name} iniciada`,
										fail: "Moedas insuficientes",
									},
								),
								act(
									fmt(expansion.diamondCost),
									"unlockMarketExpansion",
									[expansion.id, "diamonds"],
									{
										variant: "gem",
										icon: gameIcon("diamond"),
										enabled: hasDiamonds,
										ok: `Obra de ${expansion.name} iniciada`,
										fail: "Diamantes insuficientes",
									},
								),
							],
			});
		});

		return page("expansions", "Expansões", cards, {
			subtitle: `Desbloqueie novas alas e faça seu mercado crescer. · 🪙 ${fmt(coins)} · 💎 ${fmt(diamonds)} · NÍVEL ${level}`,
			icon: gameIcon("construction"),
		});
	},
};
