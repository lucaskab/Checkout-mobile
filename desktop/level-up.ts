import { t } from "@/i18n";
import type { EmployeeRole } from "@/@types/employee";
import { getMarketEra } from "@/data/economy";
import { getAchievementIcon, getMissionIcon, getShopItemIcon } from "@/data/game-icon-assets";
import { type LevelUnlock, type LevelUnlockKind, getLevelUnlocks, getNextLevelUnlocks } from "@/services/level-unlocks";
import { getExperienceToNextLevel } from "@/services/progression";
import { decorIcon, fmt, gameIcon, productIcon, type State } from "./view-kit";
import { tools } from "./view";

// The level-up celebration (like Hay Day's and Township's "Level up!" screens): the new level on a medal with
// rays and confetti, then the complete list of what it opened, grouped and explained (where to find it, what
// to do with it), the things that wait for a bigger market, and what the next level brings. Unity draws it
// over everything (CheckoutDesktopHUD.LevelUp.cs) until the player taps "Continuar" (dismissLevelUp).

export type LevelUpItem = {
	icon: string;
	title: string;
	detail: string;
	/** Small label on the card ("NOVO", "NÍVEL 5", the expansion it waits for). */
	tag: string;
};

export type LevelUpGroup = {
	title: string;
	/** What to do with these, in one line. */
	hint: string;
	icon: string;
	/** Colour of the group header (hex). */
	tint: string;
	items: LevelUpItem[];
	/** Button that closes the celebration and opens where these live. */
	button: string;
	route: string;
};

export type LevelUpView = {
	/** Changes with every new celebration (Unity replays the animation). */
	key: string;
	from: number;
	to: number;
	headline: string;
	subtitle: string;
	/** Things opened now (not counting the ones that wait for an expansion). */
	total: number;
	groups: LevelUpGroup[];
	/** Shown when the level opened nothing new. */
	empty: string;
	xp: number;
	xpGoal: number;
	next: string;
};

type GroupSpec = { title: string; hint: string; icon: string; tint: string; button: string; route: string };

const groups: Record<LevelUnlockKind | "tool", GroupSpec> = {
	product: {
		title: "Produtos novos",
		hint: "Peça aos fornecedores em Entregas e coloque nas prateleiras: mais variedade traz mais clientes.",
		icon: gameIcon("package"),
		tint: "2E8CAE",
		button: "Pedir produtos",
		route: "!suppliers",
	},
	sector: {
		title: "Setores de produção",
		hint: "Construa o setor na Loja › Móveis e obras e produza com as suas receitas.",
		icon: gameIcon("conveyor"),
		tint: "C0612B",
		button: "Ver produção",
		route: "!sectors",
	},
	recipe: {
		title: "Receitas",
		hint: "Produza no setor ou faça à mão, no jogo de cozinha, para ganhar estrelas e um bônus.",
		icon: gameIcon("conveyor"),
		tint: "D9822B",
		button: "Ver receitas",
		route: "!sectors",
	},
	shelf: {
		title: "Prateleiras",
		hint: "Melhore as prateleiras em Prateleiras: mais produtos expostos vendem mais.",
		icon: gameIcon("shelf"),
		tint: "B0603A",
		button: "Ver prateleiras",
		route: "!store",
	},
	employee: {
		title: "Equipe",
		hint: "Contrate na Loja › Equipe: eles trabalham sozinhos enquanto você cuida do resto.",
		icon: gameIcon("manager"),
		tint: "5C7A3A",
		button: "Ver equipe",
		route: "!loja:equipe",
	},
	shop: {
		title: "Melhorias",
		hint: "Compre na Loja › Melhorias: deixam o mercado mais rápido e lucrativo.",
		icon: gameIcon("toolbox"),
		tint: "8B5C9E",
		button: "Ver melhorias",
		route: "!loja:melhorias",
	},
	decor: {
		title: "Decoração",
		hint: "Compre na Loja › Decoração e coloque no modo construir.",
		icon: gameIcon("plant"),
		tint: "3F9E78",
		button: "Ver decoração",
		route: "!loja:decoracao",
	},
	tool: {
		title: "Novos botões",
		hint: "Apareceram na barra de baixo da tela.",
		icon: gameIcon("lightning"),
		tint: "E0A441",
		button: "",
		route: "",
	},
	mission: {
		title: "Missões",
		hint: "Novas metas com prêmio em Missões.",
		icon: gameIcon("trophy"),
		tint: "B5822A",
		button: "Ver missões",
		route: "!missions",
	},
	achievement: {
		title: "Conquistas",
		hint: "Novas medalhas para colecionar em Conquistas.",
		icon: gameIcon("crown"),
		tint: "A0662F",
		button: "Ver conquistas",
		route: "!achievements",
	},
};

const order: (LevelUnlockKind | "tool")[] = [
	"product",
	"sector",
	"recipe",
	"shelf",
	"tool",
	"employee",
	"shop",
	"decor",
	"mission",
	"achievement",
];

function roleIcon(role: string) {
	switch (role as EmployeeRole) {
		case "cashier":
			return gameIcon("calculator");
		case "stock_clerk":
			return gameIcon("package");
		case "cleaner":
			return gameIcon("broom");
	}
	return gameIcon("manager");
}

function iconOf(unlock: LevelUnlock) {
	switch (unlock.kind) {
		case "product":
		case "recipe":
			return unlock.productId ? productIcon(unlock.productId) : gameIcon("package");
		case "sector":
			return decorIcon(`sector-${unlock.id}`);
		case "shelf":
			return gameIcon("shelf");
		case "employee":
			return roleIcon(unlock.id);
		case "shop":
			return gameIcon(getShopItemIcon(unlock.id));
		case "decor":
			return decorIcon(unlock.id);
		case "mission":
			return gameIcon(getMissionIcon(unlock.id));
		case "achievement":
			return gameIcon(getAchievementIcon(unlock.id));
	}
}

const kindLabel: Record<LevelUnlockKind, string> = {
	product: "produto",
	sector: "setor",
	recipe: "receita",
	shelf: "prateleira",
	employee: "funcionário",
	shop: "melhoria",
	decor: "decoração",
	mission: "missão",
	achievement: "conquista",
};

export function levelUpView(state: State): LevelUpView | null {
	const levelUp = state.market.levelUp;
	if (!levelUp || levelUp.to <= levelUp.from) return null;
	const { from, to } = levelUp;
	const eraId = state.era.id;
	const unlocks = getLevelUnlocks(from, to, eraId);
	const now = unlocks.filter((unlock) => !unlock.waitingEra);
	const waiting = unlocks.filter((unlock) => unlock.waitingEra);
	const multi = to - from > 1;
	const tag = (level: number) => (multi ? `NÍVEL ${level}` : "NOVO");

	const result: LevelUpGroup[] = [];
	for (const kind of order) {
		const spec = groups[kind];
		const items: LevelUpItem[] =
			kind === "tool"
				? tools
						.filter((tool) => tool.requiredLevel > from && tool.requiredLevel <= to)
						.map((tool) => ({
							icon: gameIcon(tool.icon),
							title: tool.label,
							detail: "Novo botão na barra de baixo",
							tag: tag(tool.requiredLevel),
						}))
				: now
						.filter((unlock) => unlock.kind === kind)
						.map((unlock) => ({
							icon: iconOf(unlock),
							title: unlock.name,
							detail: unlock.detail,
							tag: tag(unlock.level),
						}));
		if (!items.length) continue;
		result.push({ ...spec, items });
	}
	if (waiting.length) {
		const eras = Array.from(new Set(waiting.map((unlock) => unlock.waitingEra!)));
		result.push({
			title: "Esperando o mercado crescer",
			// One expansion is named; several are told by the tag on each card.
			hint:
				eras.length === 1
					? `Já são seus: chegam quando você abrir ${getMarketEra(eras[0]).name} (Loja › Expansões).`
					: "Já são seus: chegam com as próximas expansões (Loja › Expansões). Cada card mostra qual.",
			icon: gameIcon("lock"),
			tint: "8A7560",
			button: "Ver expansões",
			route: "!loja:expansoes",
			items: waiting.map((unlock) => ({
				icon: iconOf(unlock),
				title: unlock.name,
				detail: `${kindLabel[unlock.kind][0].toLocaleUpperCase("pt-BR")}${kindLabel[unlock.kind].slice(1)} · chega com ${getMarketEra(unlock.waitingEra!).name}`,
				tag: getMarketEra(unlock.waitingEra!).name.toLocaleUpperCase("pt-BR"),
			})),
		});
	}
	const total = result.filter((group) => group.icon !== gameIcon("lock")).reduce((sum, group) => sum + group.items.length, 0);
	const next = getNextLevelUnlocks(to, eraId);
	// translated one by one: the list's sentence is translated as a whole later and would leave the names as they are
	const nextNames = next?.unlocks.map((unlock) => t(unlock.name)) ?? [];
	return {
		key: `${from}:${to}:${levelUp.at}`,
		from,
		to,
		headline: `NÍVEL ${to}!`,
		subtitle: multi
			? `Você subiu ${to - from} níveis de uma vez! Seu mercado está crescendo.`
			: "Seu mercado está crescendo. Veja tudo o que você liberou:",
		total,
		groups: result,
		empty: "Este nível não trouxe itens novos, mas o próximo está chegando. Continue vendendo!",
		xp: state.market.experience,
		xpGoal: getExperienceToNextLevel(state.market.level),
		next: next
			? `No nível ${next.level}: ${nextNames.slice(0, 3).join(", ")}${nextNames.length > 3 ? ` e mais ${fmt(nextNames.length - 3)}` : ""}`
			: "Você já liberou tudo o que os níveis trazem!",
	};
}
