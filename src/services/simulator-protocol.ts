import type { GameActions } from "../@types/game";
import type {
	SimulatorAction,
	SimulatorCommand,
	SimulatorReceipt,
} from "../@types/simulator";

const text = (v: unknown): boolean =>
	typeof v === "string" && v.length > 0 && v.length < 120;
const positive = (v: unknown): boolean =>
	typeof v === "number" && Number.isFinite(v) && v > 0;
const integer = (v: unknown): boolean => positive(v) && Number.isSafeInteger(v);
const boolean = (v: unknown): boolean => typeof v === "boolean";
const currency = (v: unknown): boolean => v === "coins" || v === "diamonds";
const object = (v: unknown): v is Record<string, unknown> =>
	!!v && typeof v === "object" && !Array.isArray(v);
const schemas: Record<SimulatorAction, ((v: unknown) => boolean)[]> = {
	activateLogisticsBoost: [],
	claimDailyGoal: [],
	claimDayResult: [],
	closeDay: [],
	completeCheckout: [text, positive],
	completeOrderFinalStage: [text],
	claimMission: [text],
	deliverOrderInstantly: [text],
	finishProductionNow: [text],
	finishMarketExpansionNow: [],
	finishInteriorConstructionNow: [text],
	buildSector: [
		(v) =>
			[
				"padaria",
				"queijaria",
				"acougue",
				"peixaria",
				"bebidas",
				"sorvetes",
				"adega",
			].includes(String(v)),
		currency,
	],
	saveInteriorLayout: [(v) => Array.isArray(v) && v.length <= 300],
	purchaseDecor: [text, currency],
	fixIncident: [text],
	unloadDelivery: [text, integer],
	unloadAllDeliveries: [],
	hireEmployee: [
		(v) => ["cashier", "stock_clerk", "cleaner"].includes(String(v)),
	],
	placeSupplierOrder: [
		(v) =>
			object(v) &&
			integer(v.productId) &&
			integer(v.quantity) &&
			(v.useFreightCoupon === undefined || boolean(v.useFreightCoupon)),
	],
	purchaseShopItem: [text, currency],
	assignProductToShelf: [text, integer],
	clearShelf: [text],
	tendShelf: [text],
	swapShelfSlots: [text, text],
	restockShelf: [
		(v) =>
			object(v) &&
			text(v.shelfId) &&
			integer(v.productId) &&
			(v.amount === undefined || integer(v.amount)),
	],
	setEmployeeWorking: [text, boolean],
	trainEmployee: [text],
	resolveSpecialRequest: [text, text],
	setMarketOpen: [boolean],
	startDay: [text],
	setShelfPrice: [text, positive],
	startProduction: [
		(v) =>
			object(v) &&
			text(v.recipeId) &&
			[
				"padaria",
				"queijaria",
				"acougue",
				"peixaria",
				"bebidas",
				"sorvetes",
				"adega",
			].includes(String(v.sectorId)),
	],
	upgradeSupplierOrderSlots: [currency],
	upgradeInventoryCapacity: [integer],
	expandShelfSlots: [text],
	unlockNextShelf: [],
	unlockNextShelfSlot: [],
	unlockMarketExpansion: [
		(v) =>
			[
				"fresh-wing",
				"service-wing",
				"stock-annex",
				"premium-hall",
				"grand-warehouse",
			].includes(String(v)),
	],
	upgradeShelfCapacity: [text, currency],
};
export const simulatorActions = Object.keys(schemas) as SimulatorAction[];
// A session changes whenever the renderer reconnects. Old commands never cross sessions.
export function createSimulatorCommandHandler(
	session: string,
	actions: () => GameActions,
	revision: () => number,
) {
	const receipts = new Map<string, SimulatorReceipt>();
	return (value: unknown): SimulatorReceipt => {
		const input = object(value) ? value : {};
		const id = typeof input.id === "string" ? input.id : "invalid";
		const fail = (reason: string): SimulatorReceipt => ({
			kind: "receipt",
			protocol: 1,
			session,
			id,
			ok: false,
			reason,
			revision: revision(),
		});
		if (input.protocol !== 1 || input.session !== session)
			return fail("session-mismatch");
		if (
			!text(id) ||
			!Number.isSafeInteger(input.revision) ||
			Number(input.revision) < 0 ||
			Number(input.revision) > revision()
		)
			return fail("invalid-command");
		const cached = receipts.get(id);
		if (cached) return cached;
		const schema =
			typeof input.action === "string" && Object.hasOwn(schemas, input.action)
				? schemas[input.action as SimulatorAction]
				: undefined;
		if (
			!schema ||
			!Array.isArray(input.args) ||
			input.args.length !== schema.length ||
			!schema.every((check, i) => check((input.args as unknown[])[i]))
		)
			return fail("invalid-action");
		// Stale UI decisions must be reviewed against a fresh snapshot, especially currency spends.
		if (Number(input.revision) !== revision()) return fail("stale-revision");
		if (receipts.size >= 10000) return fail("session-capacity");
		const command = input as unknown as SimulatorCommand;
		let result: SimulatorReceipt;
		try {
			const action = actions()[command.action] as (
				...args: unknown[]
			) => boolean | undefined;
			result = {
				...fail("game-rule-rejected"),
				ok: action(...command.args) !== false,
			};
			if (result.ok) delete result.reason;
			result.revision = revision();
		} catch {
			result = fail("action-failed");
		}
		receipts.set(id, result);
		return result;
	};
}
