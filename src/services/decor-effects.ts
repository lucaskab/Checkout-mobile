import type { DecorEffect, InteriorState } from "@/@types/interior";
import { getInteriorDecor } from "@/data/interior-decor";

// Decorations that work (Lucas 18/10: "melhorias que você coloca no mapa"): the shopping carts, the ATM and the
// coin machines do something only while they stand placed in the market or on its block.

export type DecorPlayMachine = {
	decorId: string;
	/** The placed pieces of this machine that count (Unity shows the coins over one of them). */
	itemIds: string[];
	chance: number;
	coins: number;
};

export type DecorEffects = {
	/** Extra products per customer. */
	basketItems: number;
	/** Customers' money multiplier. */
	budgetMultiplier: number;
	machines: DecorPlayMachine[];
};

export function getDecorEffects(interior: InteriorState | undefined): DecorEffects {
	const placed: Record<string, string[]> = {};
	for (const item of interior?.items ?? []) {
		if (item.stored) continue;
		const decor = getInteriorDecor(item.type);
		if (!decor?.effect) continue;
		(placed[item.type] ??= []).push(item.id);
	}
	let basketItems = 0;
	let budget = 0;
	const machines: DecorPlayMachine[] = [];
	for (const [decorId, itemIds] of Object.entries(placed)) {
		const effect = getInteriorDecor(decorId)?.effect as DecorEffect;
		basketItems += effect.basketItems ?? 0;
		budget += effect.budget ?? 0;
		if (effect.play)
			machines.push({
				decorId,
				itemIds: itemIds.slice(0, effect.play.maxPlaced),
				chance: effect.play.chance,
				coins: effect.play.coins,
			});
	}
	return { basketItems, budgetMultiplier: 1 + budget, machines };
}

export type DecorPlay = { decorId: string; itemId: string; coins: number };

/**
 * The plays of one customer: every counted machine gets its own roll. Coins grow with the market like the
 * customers' money does (level and era), so the machines stay worth it in bigger markets.
 */
export function rollDecorPlays(
	effects: DecorEffects,
	random: () => number,
	moneyScale: number,
): DecorPlay[] {
	const plays: DecorPlay[] = [];
	for (const machine of effects.machines)
		for (const itemId of machine.itemIds)
			if (random() < machine.chance)
				plays.push({
					decorId: machine.decorId,
					itemId,
					coins: Math.max(1, Math.round(machine.coins * moneyScale)),
				});
	return plays;
}
