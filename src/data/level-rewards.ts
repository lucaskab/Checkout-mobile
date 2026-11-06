import type { MarketEraId } from "@/@types/economy";
import { getMarketEra } from "@/data/economy";
import { interiorDecor } from "@/data/interior-decor";

// A prize on every level (Lucas 06/11, launch audit: "todo level tem que ter alguma recompensa pro jogador, para
// manter ele motivado... alguma decoração, algum item exclusivo"). On top of what the level unlocks:
//  - every level: coins, two item-level prices of the current expansion (they keep their worth at every stage);
//  - every 5th level a few diamonds, every 10th a few more;
//  - a decoration of the diamond shelf, free, on the levels that unlock nothing else (36, 38) and on the milestones
//    (25, 50, 75, 100), and on every odd level past the last unlock (53+): the cheapest one the player does not own
//    yet; once they own them all, diamonds instead.
// Pure: the store hands it the level, the expansion and the decorations owned (src/stores/game-store.ts).

/** The last level that unlocks something (src/data/level-ladder.test.mjs keeps 2–52 unlocking, but 36 and 38). */
export const LAST_UNLOCK_LEVEL = 52;
const QUIET_LEVELS = [36, 38];
const MILESTONES = [25, 50, 75, 100];
const DECOR_FALLBACK_DIAMONDS = 10;

export type LevelReward = {
	level: number;
	coins: number;
	diamonds: number;
	/** A decoration given for free (its id), when this level gives one. */
	decorId?: string;
};

/** The diamond-priced decorations, cheapest first: the ones a level can give. */
export const levelRewardDecor = interiorDecor
	.filter((decor) => (decor.diamondPrice ?? 0) > 0 && !decor.exclusive)
	.sort((a, b) => (a.diamondPrice ?? 0) - (b.diamondPrice ?? 0) || a.requiredLevel - b.requiredLevel);

export function levelGivesDecor(level: number) {
	return QUIET_LEVELS.includes(level) || MILESTONES.includes(level) || (level > LAST_UNLOCK_LEVEL && level % 2 === 1);
}

export function getLevelReward(level: number, eraId: MarketEraId, owned: Record<string, number> = {}): LevelReward {
	const base = getMarketEra(eraId).itemUpgradeBaseCost;
	const coins = Math.max(50, Math.round((base * 2) / 10) * 10);
	let diamonds = level % 10 === 0 ? 8 : level % 5 === 0 ? 3 : 0;
	let decorId: string | undefined;
	if (levelGivesDecor(level)) {
		const gift = levelRewardDecor.find((decor) => !(owned[decor.id] > 0) && decor.requiredLevel <= level);
		if (gift) decorId = gift.id;
		else diamonds += DECOR_FALLBACK_DIAMONDS;
	}
	return { level, coins, diamonds, ...(decorId ? { decorId } : {}) };
}

/** The prizes of the levels in (from, to], one after the other (a decoration given counts as owned for the next). */
export function getLevelRewards(from: number, to: number, eraId: MarketEraId, owned: Record<string, number> = {}) {
	const have = { ...owned };
	const rewards: LevelReward[] = [];
	for (let level = from + 1; level <= to; level++) {
		const reward = getLevelReward(level, eraId, have);
		if (reward.decorId) have[reward.decorId] = (have[reward.decorId] ?? 0) + 1;
		rewards.push(reward);
	}
	return rewards;
}
