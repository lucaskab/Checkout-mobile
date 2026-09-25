import type { EmployeeRole } from "@/@types/employee";
import type { ShopCategory, ShopItemDefinition, ShopItemQuality } from "@/@types/shop";
import { employeeDefinitions } from "@/data/employees";
import { getShopCategoryIcon, getShopItemIcon } from "@/data/game-icon-assets";
import { marketExpansions } from "@/data/market-expansions";
import { shopCategories, shopItems } from "@/data/shop-items";
import {
	EMPLOYEE_MAX_LEVEL,
	getEmployeeTrainingCost,
} from "@/services/employee-progression";
import {
	EMPLOYEE_PAYROLL_INTERVAL_MS,
	getEmployeeEffects,
	getEmployeePayrollCost,
} from "@/services/employees";
import type { Routes } from ".";
import {
	act,
	card,
	expansionIcon,
	fmt,
	gameIcon,
	page,
	ratio,
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

const qualityStars: Record<ShopItemQuality, number> = {
	comum: 1,
	incomum: 2,
	raro: 3,
	epico: 4,
	lendario: 5,
	mitico: 6,
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
			eyebrow: "GESTÃO DE PESSOAS",
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
				`Fila ${Math.round((1 - effects.customerArrivalMultiplier) * 100)}% mais rápida · +${effects.restockAmount} reposição`,
				`Reputação +${effects.storeReputationBonus}`,
			],
			progress: 1 - ratio(remaining, EMPLOYEE_PAYROLL_INTERVAL_MS),
		});

		const roleCards = employeeDefinitions.map((definition) => {
			const employee = employees.employees.find(
				(item) => item.role === definition.id,
			);
			const levelLocked = level < definition.level;
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
						`🪙 ${employee.salary}/turno`,
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
				eyebrow: levelLocked ? `NÍVEL ${definition.level}` : "DISPONÍVEL",
				icon: gameIcon(roleIcon(definition.id)),
				tone: levelLocked ? "locked" : "",
				subtitle: definition.description,
				lines: [
					`${definition.efficiency} eficiência · 🪙 ${definition.salary}/turno`,
				],
				buttons: [
					act(
						levelLocked
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
		const items = shopItems.filter((item) => item.category === category);

		const cards = items.map((item) => {
			const isOwned = ownedItemIds.includes(item.id);
			const isLocked = level < item.level;
			const consumableAmount = consumableAmounts[item.id] ?? 0;
			const isDiamond = Boolean(item.diamondPrice);
			const price = item.diamondPrice ?? item.coinPrice ?? 0;
			const canAfford = isDiamond ? diamonds >= price : coins >= price;
			const quality = getItemQuality(item);
			const isLegendary = quality === "lendario" || quality === "mitico";
			const verb = item.isConsumable
				? "Comprar"
				: isLegendary
					? "Desbloquear"
					: "Comprar";
			const label = isOwned
				? "Instalado"
				: isLocked
					? `Nível ${item.level}`
					: `${verb} · ${formatPrice(price)}`;

			return card(item.name, {
				eyebrow: `${qualityLabels[quality]} ${"★".repeat(qualityStars[quality])}`,
				icon: gameIcon(getShopItemIcon(item.id)),
				badge:
					item.isConsumable && consumableAmount > 0
						? `x${consumableAmount}`
						: `Nv ${item.level}`,
				tone: isOwned
					? "success"
					: isLocked
						? "locked"
						: isLegendary
							? "warning"
							: "",
				subtitle: item.description,
				lines: [
					`Nível ${item.level} · ${isDiamond ? "💎" : "🪙"} ${formatPrice(price)}`,
					...(item.isConsumable && consumableAmount > 0
						? [`No inventário: ${consumableAmount}`]
						: []),
				],
				buttons: [
					act(
						label,
						"purchaseShopItem",
						[item.id, isDiamond ? "diamonds" : "coins"],
						{
							variant: isOwned ? "success" : isDiamond ? "gem" : "coin",
							icon: gameIcon(isDiamond ? "diamond" : "coin"),
							enabled: !isOwned && !isLocked && canAfford,
							ok: item.isConsumable
								? `${item.name} foi adicionado aos boosters.`
								: `${item.name} foi instalado no mercado.`,
							fail: "Você ainda não atende aos requisitos desta compra.",
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

		const cards = marketExpansions.map((expansion) => {
			const unlocked = unlockedIds.includes(expansion.id);
			const levelLocked = level < expansion.requiredLevel;
			const hasCoins = coins >= expansion.coinCost;
			const hasDiamonds = diamonds >= expansion.diamondCost;

			return card(expansion.name, {
				eyebrow: unlocked ? "LIBERADA" : `NÍVEL ${expansion.requiredLevel}`,
				icon: expansionIcon(expansion.id),
				tone: unlocked ? "success" : levelLocked ? "locked" : "",
				subtitle: expansion.description,
				lines: [
					unlocked
						? "Área pronta para o mercado."
						: levelLocked
							? `Alcance o nível ${expansion.requiredLevel} para desbloquear.`
							: `🪙 ${fmt(expansion.coinCost)} ou 💎 ${fmt(expansion.diamondCost)}`,
				],
				buttons:
					unlocked || levelLocked
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
										ok: `${expansion.name} liberada`,
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
										ok: `${expansion.name} liberada`,
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
