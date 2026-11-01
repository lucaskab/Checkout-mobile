import type { EvolutionKind, FixtureEvolution } from "@/@types/fixture-evolution";
import {
	fixtureTierAttraction,
	fixtureTierPlaces,
	fixtureTierRestock,
	getSectorBatchOutput,
	getSectorTierDefinition,
} from "@/data/fixture-tiers";
import { findEvolution, getEvolutionDurationMs, getEvolutionProgress } from "@/data/fixture-evolution";
import { formatBuildDuration, formatConstructionCountdown } from "@/data/market-expansions";
import { getExclusiveProductFor } from "@/services/tier-rewards";
import { act, gameIcon, type State } from "../view-kit";

// The evolution crew on the HUD pages (claude/evolucoes-recompensas.md): what an evolution gives, how long it takes,
// where it stands and the diamond button that finishes it. Unity draws the ring and the builder on the fixture itself.

export type EvolutionStatus = {
	evolution: FixtureEvolution;
	queued: boolean;
	remainingMs: number;
	progress: number;
	skipCost: number;
	/** "Evoluindo · 1:42" / "Na fila da equipe · 10min". */
	line: string;
};

export function evolutionStatus(state: State, kind: EvolutionKind, targetId: string, now = Date.now()): EvolutionStatus | null {
	const evolution = findEvolution(state.evolutions, kind, targetId);
	if (!evolution) return null;
	const progress = getEvolutionProgress(evolution, now);
	return {
		evolution,
		...progress,
		line: progress.queued
			? `Na fila da equipe de evolução · ${formatBuildDuration(progress.remainingMs)}`
			: `Evoluindo · faltam ${formatConstructionCountdown(progress.remainingMs)}`,
	};
}

/** "Terminar já · 12" (diamonds), the one way to skip the wait. */
export function evolutionSkipButton(state: State, status: EvolutionStatus) {
	return act(`Terminar já · ${status.skipCost}`, "finishEvolutionNow", [status.evolution.id], {
		variant: "gem",
		icon: gameIcon("diamond"),
		enabled: state.logistics.premiumCurrency >= status.skipCost,
		ok: "Evolução concluída!",
		fail: "Diamantes insuficientes.",
	});
}

/** How long the next evolution takes ("2min", "1h"). */
export function evolutionTimeText(kind: EvolutionKind, targetId: string, toTier: number) {
	const ms = getEvolutionDurationMs(kind, targetId, toTier);
	return ms > 0 ? formatBuildDuration(ms) : "";
}

const pct = (value: number) => Math.round(value * 100);

/** What a product fixture gains going to `toTier` (lines for the "Evoluir" card and the chips of the reveal). */
export function shelfRewardLines(shelfId: string, fromTier: number, toTier: number, capacityFrom: number, capacityTo: number) {
	const lines = [`${capacityFrom} → ${capacityTo} por produto`];
	const placesFrom = fixtureTierPlaces[Math.max(1, fromTier)] ?? 4;
	const placesTo = fixtureTierPlaces[toTier] ?? placesFrom;
	if (placesTo > placesFrom) lines.push(`+${placesTo - placesFrom} lugar para produto`);
	const attraction = pct(fixtureTierAttraction[toTier] ?? 0);
	if (attraction > 0) lines.push(`+${attraction}% de clientes neste móvel`);
	const restock = pct(fixtureTierRestock[toTier] ?? 0);
	if (restock > 0) lines.push(`Reposição ${restock}% mais rápida`);
	const exclusive = getExclusiveProductFor(shelfId, toTier);
	if (exclusive) lines.push(`NOVO: ${exclusive.name}`);
	return lines;
}

/** What a special sector gains going to `toTier`. */
export function sectorRewardLines(sectorId: string, fromTier: number, toTier: number) {
	const from = getSectorTierDefinition(fromTier);
	const to = getSectorTierDefinition(toTier);
	const lines: string[] = [];
	if (to.extraSlots > from.extraSlots) lines.push(`+${to.extraSlots - from.extraSlots} linha de produção`);
	if (to.durationMultiplier < from.durationMultiplier) lines.push(`Produção ${pct(1 - to.durationMultiplier)}% mais rápida`);
	if (to.outputMultiplier > from.outputMultiplier) lines.push(`Rende +${pct(to.outputMultiplier - 1)}% por lote`);
	if (to.priceMultiplier > from.priceMultiplier) lines.push(`+${pct(to.priceMultiplier - 1)}% no preço`);
	if (to.counterPlaces > from.counterPlaces) lines.push(`Balcão com ${to.counterPlaces} produtos (+${to.counterUnits} unid.)`);
	const exclusive = getExclusiveProductFor(sectorId, toTier);
	if (exclusive) lines.push(`NOVO: ${exclusive.name}`);
	return lines;
}

/** A batch at this tier ("10 → 13"), for the sector's stat. */
export function sectorBatchText(outputQuantity: number, fromTier: number, toTier: number) {
	return `${getSectorBatchOutput(outputQuantity, fromTier)} → ${getSectorBatchOutput(outputQuantity, toTier)}`;
}
