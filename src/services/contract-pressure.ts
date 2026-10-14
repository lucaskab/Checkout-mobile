import type { DayResult, DayReward } from "@/@types/market-day";

/**
 * Contract pacing and the "consolation" video (Lucas 14/10, after the block-puzzle games that earn most from ads).
 *
 * How those games do it (research notes in the project doc anuncios-recompensa-contrato):
 * - The difficulty is not a straight line: a few easy wins make the player feel good at the game, then one harder
 *   step comes; after a miss the next one is easier again, so the player keeps coming back instead of giving up.
 * - The offer to watch a video comes right after the miss, when the player cares most ("you were so close"):
 *   the best-converting moment for a rewarded ad. The prize is shown before the video and is always given, so the
 *   video never feels like a trick, and it is smaller than winning the contract (playing well stays the best way).
 * - Only by choice: no forced ads (the game's rule). The offer appears once per failed contract.
 *
 * Here:
 * - `contractMomentum` counts contracts kept in a row (>0) or missed in a row (<0); free days do not change it.
 * - Each kept contract makes the next day's targets 8 % bigger (up to +32 %); every third one in a row is a
 *   "Desafio" day (+12 % more, and it pays more). A miss resets the climb and the day after is 8 % easier (down
 *   to −16 % after more misses), so a struggling player gets back to winning.
 * - The first days of the game never climb (the player is still learning).
 * - A missed contract offers a video: half of the contract's coins for sure, plus a surprise prize (diamonds, XP or
 *   more coins). The prize is decided only when the video ends.
 */

export const PRESSURE_STEP = 0.08;
export const PRESSURE_MAX_STEPS = 4;
export const CHALLENGE_EXTRA = 0.12;
export const RELIEF_STEP = 0.08;
export const RELIEF_MAX_STEPS = 2;
/** Days before the climb starts (tutorial days stay as they are). */
export const PRESSURE_FROM_DAY = 3;

export type ContractPressure = {
	/** Multiplies the targets (and the rewards) of the day's offers. */
	factor: number;
	/** A "Desafio" day: the third contract in a row, harder and better paid. */
	challenge: boolean;
};

export function getContractPressure(momentum: number | undefined, dayNumber: number): ContractPressure {
	const m = Math.trunc(momentum ?? 0);
	if (m < 0) return { factor: 1 - RELIEF_STEP * Math.min(RELIEF_MAX_STEPS, -m), challenge: false };
	if (dayNumber < PRESSURE_FROM_DAY || m === 0) return { factor: 1, challenge: false };
	const challenge = m % 3 === 2; // after two kept in a row, the third offer is the challenge
	const factor = 1 + PRESSURE_STEP * Math.min(PRESSURE_MAX_STEPS, m) + (challenge ? CHALLENGE_EXTRA : 0);
	return { factor: Math.round(factor * 100) / 100, challenge };
}

/** The momentum after a day: kept contract climbs, missed one drops, a free day keeps it. */
export function nextContractMomentum(momentum: number | undefined, hadContract: boolean, completed: boolean) {
	const m = Math.trunc(momentum ?? 0);
	if (!hadContract) return m;
	if (completed) return m > 0 ? m + 1 : 1;
	return m < 0 ? m - 1 : -1;
}

// ---------------------------------------------------------------- consolation video

/** Share of the contract's coins the video always gives. */
export const CONSOLATION_COIN_SHARE = 0.5;
export const CONSOLATION_DIAMONDS = 3;

export type ConsolationPrize = DayReward & { label: string };

/** A missed contract whose consolation video was not watched yet. */
export function canClaimConsolation(result: DayResult | null | undefined) {
	return Boolean(result?.contract && !result.contractCompleted && !result.consolation);
}

/** What the offer shows before the video: the sure part and the possible surprises. */
export function getConsolationOffer(result: DayResult | null | undefined) {
	if (!result?.contract || result.contractCompleted) return null;
	const sure = Math.max(5, Math.round((result.contract.reward.coins * CONSOLATION_COIN_SHARE) / 5) * 5);
	return {
		coins: sure,
		surprises: [
			`+${CONSOLATION_DIAMONDS} diamantes`,
			`+${Math.max(1, Math.round(result.contract.reward.experience * 0.5))} XP`,
			`+${sure} moedas extras`,
		],
	};
}

/** The prize after the video: the sure coins and one surprise (roll in [0,1)). */
export function rollConsolation(result: DayResult, roll: number): ConsolationPrize | null {
	const offer = getConsolationOffer(result);
	if (!offer || !result.contract) return null;
	const xp = Math.max(1, Math.round(result.contract.reward.experience * 0.5));
	if (roll < 0.4) return { coins: offer.coins, diamonds: CONSOLATION_DIAMONDS, experience: 0, label: `+${offer.coins} moedas e +${CONSOLATION_DIAMONDS} diamantes` };
	if (roll < 0.8) return { coins: offer.coins, diamonds: 0, experience: xp, label: `+${offer.coins} moedas e +${xp} XP` };
	return { coins: offer.coins * 2, diamonds: 0, experience: 0, label: `+${offer.coins * 2} moedas` };
}
