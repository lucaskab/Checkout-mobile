/**
 * Diamonds to finish something right now ("acelerar"): every timer of the game is priced by the same curve, from the
 * time STILL LEFT, so the price drops as the wait runs down (Lucas 12/10: a 2-hour job with 1 hour left must not cost
 * what it cost at the start).
 *
 * The curve is concave, like the genre's references: the first minutes are the dearest per minute and long waits get
 * a bulk discount, so skipping a short wait is an impulse (1–10 diamonds) and skipping a whole day is a decision
 * (~150 diamonds ≈ € 3 at the packs' rate of ~45–50 diamonds per euro).
 *
 *   ≤ 1 min → 1 · 1 h → 10 · 1 day → 150 · 1 week → 700 (straight lines between, the last slope beyond)
 *
 * Unity draws the same price live on the works boards: CheckoutSkipPrice.cs holds a copy of these points
 * (diamond-skip.test.mjs fails if the two drift apart).
 */
const MINUTE = 60_000;
const HOUR = 60 * MINUTE;
const DAY = 24 * HOUR;

/** [time left in ms, diamonds] — keep in step with CheckoutSkipPrice.Points in Unity. */
export const SKIP_PRICE_POINTS: readonly (readonly [number, number])[] = [
	[MINUTE, 1],
	[HOUR, 10],
	[DAY, 150],
	[7 * DAY, 700],
];

export function getSkipDiamondCost(remainingMs: number) {
	if (!Number.isFinite(remainingMs) || remainingMs <= 0) return 0;
	const points = SKIP_PRICE_POINTS;
	if (remainingMs <= points[0][0]) return points[0][1];
	for (let i = 1; i < points.length; i++) {
		const [t1, d1] = points[i];
		if (remainingMs <= t1) {
			const [t0, d0] = points[i - 1];
			return Math.ceil(d0 + ((d1 - d0) * (remainingMs - t0)) / (t1 - t0));
		}
	}
	const [ta, da] = points[points.length - 2];
	const [tb, db] = points[points.length - 1];
	return Math.ceil(db + ((db - da) * (remainingMs - tb)) / (tb - ta));
}
