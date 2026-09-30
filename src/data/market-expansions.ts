import type {
	MarketExpansionConstruction,
	MarketExpansionDefinition,
	MarketExpansionId,
} from "@/@types/market-expansion";

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;

export const marketExpansions: MarketExpansionDefinition[] = [
	{
		buildDurationMs: 5 * MINUTE,
		coinCost: 4_000,
		diamondCost: 8,
		description:
			"Aumenta o mercado, constrói o depósito e abre espaço para a queijaria.",
		id: "fresh-wing",
		name: "Ala de produtos frescos",
		requiredLevel: 4,
	},
	{
		buildDurationMs: 2 * HOUR,
		coinCost: 18_000,
		diamondCost: 24,
		description:
			"Amplia o salão, adiciona estacionamento e abre espaço para o açougue.",
		id: "service-wing",
		name: "Ala de atendimento",
		requiredLevel: 9,
	},
	{
		buildDurationMs: 12 * HOUR,
		coinCost: 65_000,
		diamondCost: 60,
		description:
			"Expande o mercado com peixaria e um pátio de carga para entregas de maior porte.",
		id: "stock-annex",
		name: "Anexo de estoque",
		requiredLevel: 16,
	},
	{
		buildDurationMs: 24 * HOUR,
		coinCost: 240_000,
		diamondCost: 140,
		description:
			"Cria o maior salão e uma praça de convivência com jardim e playground para os clientes.",
		id: "premium-hall",
		name: "Galeria premium",
		requiredLevel: 24,
	},
	{
		buildDurationMs: 36 * HOUR,
		coinCost: 150_000,
		diamondCost: 110,
		description:
			"Troca o depósito por um armazém central nos fundos, com novo pátio de caminhões e espaço para a adega.",
		id: "grand-warehouse",
		name: "Armazém central",
		requiredLevel: 20,
		requiresExpansionIds: ["fresh-wing", "stock-annex"],
	},
];

/** Expansions that grow the shop building itself (the warehouse lives out back). */
export const marketBuildingExpansionIds: MarketExpansionId[] = [
	"fresh-wing",
	"service-wing",
	"stock-annex",
	"premium-hall",
];

export function getMarketExpansion(id: MarketExpansionId) {
	return marketExpansions.find((expansion) => expansion.id === id) ?? null;
}

export function getMissingMarketExpansionPrerequisites(
	expansion: MarketExpansionDefinition,
	unlockedIds: readonly MarketExpansionId[],
) {
	return (expansion.requiresExpansionIds ?? [])
		.filter((id) => !unlockedIds.includes(id))
		.map((id) => getMarketExpansion(id))
		.filter((item): item is MarketExpansionDefinition => item !== null);
}

export function normalizeMarketExpansionIds(
	value: unknown,
): MarketExpansionId[] {
	if (!Array.isArray(value)) {
		return [];
	}

	const validIds = new Set(marketExpansions.map((expansion) => expansion.id));
	return Array.from(
		new Set(value.filter((id): id is MarketExpansionId => validIds.has(id))),
	);
}

/** Diamonds to finish a construction right now: 1 per started 10 minutes still left. */
export function getMarketExpansionSkipCost(remainingMs: number) {
	return remainingMs <= 0 ? 0 : Math.max(1, Math.ceil(remainingMs / 600_000));
}

export function formatBuildDuration(ms: number) {
	const totalMinutes = Math.max(0, Math.ceil(ms / 60_000));
	const days = Math.floor(totalMinutes / 1440);
	const hours = Math.floor((totalMinutes % 1440) / 60);
	const minutes = totalMinutes % 60;
	if (days > 0) return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
	if (hours > 0) return minutes > 0 ? `${hours}h ${minutes}min` : `${hours}h`;
	return `${Math.max(1, minutes)}min`;
}

export function normalizeMarketExpansionConstruction(
	value: unknown,
): MarketExpansionConstruction | null {
	if (!value || typeof value !== "object") return null;
	const item = value as Partial<MarketExpansionConstruction>;
	const [expansionId] = normalizeMarketExpansionIds([item.expansionId]);
	if (
		!expansionId ||
		typeof item.startedAt !== "number" ||
		typeof item.endsAt !== "number" ||
		!Number.isFinite(item.endsAt)
	) {
		return null;
	}
	return { expansionId, startedAt: item.startedAt, endsAt: item.endsAt };
}

/** Live countdown label: "4:05" under an hour, then "1h 59min" / "1d 3h". */
export function formatConstructionCountdown(remainingMs: number) {
	const ms = Math.max(0, remainingMs);
	if (ms >= 60 * 60_000) return formatBuildDuration(ms);
	const totalSeconds = Math.ceil(ms / 1000);
	const minutes = Math.floor(totalSeconds / 60);
	const seconds = totalSeconds % 60;
	return `${minutes}:${String(seconds).padStart(2, "0")}`;
}
