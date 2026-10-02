import type { GameShelfCare } from "@/@types/game";
import { getPhysicalShelfId } from "@/data/shelf-slots";

// Looking after the fixtures (the shelf window of the game): every product a customer takes leaves the
// fixture a little messier (wilted leaves in the crates, melted ice in the cooler, frost in the freezer,
// crumbs in the bread basket, products out of line on the gondola). A messy fixture sells less; the player
// tidies it up in the shelf window (src/data/shelf-types.ts says what tidying means for each one).
//
// Where a product sits matters too, as in a real supermarket: the top row is at eye level ("eye level is
// buy level"), the lower row sells a bit less, so rearranging the slots is worth it.

/** Condition lost per unit sold from a fixture (a full 4-slot shelf sold out twice ≈ −50). */
export const CARE_PER_UNIT = 1.5;
/** Below this the fixture asks for care (badge in the shelf window). */
export const CARE_WARNING = 60;
/** Slots per row of a fixture: the first row is at eye level. */
export const SLOTS_PER_ROW = 4;

export function getShelfCondition(care: GameShelfCare | undefined, physicalShelfId: string) {
	const value = care?.[physicalShelfId];
	return typeof value === "number" && Number.isFinite(value) ? Math.max(0, Math.min(100, value)) : 100;
}

/** Sales wear the fixtures they came from. */
export function wearShelfCare(
	care: GameShelfCare | undefined,
	purchases: { shelfId: string; quantity: number }[],
): GameShelfCare {
	const next: GameShelfCare = { ...(care ?? {}) };
	for (const purchase of purchases) {
		const id = getPhysicalShelfId(purchase.shelfId);
		next[id] = Math.max(0, getShelfCondition(next, id) - CARE_PER_UNIT * purchase.quantity);
	}
	return next;
}

/** How much a fixture's condition helps its products sell: ×0.80 when neglected, ×1.05 when spotless. */
export function getCareFactor(condition: number) {
	return 0.8 + 0.25 * Math.max(0, Math.min(100, condition)) / 100;
}

/** Position of a slot on its fixture: 0 for "produce", 2 for "produce:2". */
export function getSlotIndex(slotId: string) {
	const index = Number(slotId.split(":")[1] ?? 0);
	return Number.isFinite(index) ? index : 0;
}

/** Eye level sells more: the first row ×1.05, the row below ×0.90. */
export function getSlotPositionFactor(slotId: string) {
	return getSlotIndex(slotId) < SLOTS_PER_ROW ? 1.05 : 0.9;
}

export function normalizeShelfCare(value: unknown): GameShelfCare {
	if (!value || typeof value !== "object") return {};
	return Object.fromEntries(
		Object.entries(value as Record<string, unknown>).flatMap(([id, condition]) =>
			typeof condition === "number" && Number.isFinite(condition)
				? [[id, Math.max(0, Math.min(100, condition))]]
				: [],
		),
	);
}
