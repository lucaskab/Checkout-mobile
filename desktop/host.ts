import "./require-shim";
import { createInterface } from "node:readline";
import type { GameActions } from "@/@types/game";
import type { SimulatorPanel } from "@/@types/simulator";
import { shelves } from "@/data/market-products";
import { createSimulatorCommandHandler } from "@/services/simulator-protocol";
import { getUnlockedSimulatorSectorId } from "@/services/simulator-sector-selection";
import { createSimulatorSnapshot } from "@/services/simulator-snapshot";
import { useGameStore } from "@/stores/game-store";
import { createDesktopView } from "./view.ts";

// Desktop stand-in for the React Native app: owns the same zustand store, runs the same
// timers as src/app/_layout.tsx and speaks the Unity bridge protocol over stdin/stdout.
// stdout carries one JSON message per line, so logs from the game code go to stderr.
console.log = console.info = console.warn = console.error;

const panels: SimulatorPanel[] = [
	"store",
	"storage",
	"products",
	"suppliers",
	"sectors",
	"team",
	"shop",
	"expansions",
	"missions",
	"achievements",
	"currency",
];
// Everything the app's screens call on the store. Timers stay owned by this host.
const hudActions: (keyof GameActions)[] = [
	"activateLogisticsBoost",
	"assignProductToShelf",
	"buildSector",
	"claimDailyGoal",
	"claimDayResult",
	"claimMission",
	"clearShelf",
	"completeCheckout",
	"closeDay",
	"completeOrderFinalStage",
	"deliverOrderInstantly",
	"devActivateGameEvent",
	"devAdjustCoins",
	"devAdjustDiamonds",
	"devAdjustInventory",
	"devArriveDelivery",
	"devPassTime",
	"devSetMarketEra",
	"devClearDock",
	"devFinishMarketExpansion",
	"devFinishInteriorConstructions",
	"devTriggerIncident",
	"devWearShelf",
	"dismissOfflineSummary",
	"evolveMarketEra",
	"upgradeProduct",
	"claimDailyLogin",
	"claimAlbumCollection",
	"claimWeeklyEvent",
	"buyLot",
	"clearLot",
	"finishLotClearingNow",
	"expandShelfSlots",
	"finishMarketEraNow",
	"finishMarketExpansionNow",
	"finishInteriorConstructionNow",
	"finishProductionNow",
	"fixIncident",
	"grantCurrencyPurchase",
	"hireEmployee",
	"placeSupplierOrder",
	"purchaseDecor",
	"purchaseShopItem",
	"resetGame",
	"resolveSpecialRequest",
	"restockShelf",
	"setEmployeeWorking",
	"setMarketLevel",
	"setMarketOpen",
	"setShelfPrice",
	"swapShelfSlots",
	"tendShelf",
	"startDay",
	"startProduction",
	"trainEmployee",
	"unlockMarketExpansion",
	"unlockNextShelf",
	"unlockNextShelfSlot",
	"unloadAllDeliveries",
	"unloadDelivery",
	"unlockProduct",
	"upgradeInventoryCapacity",
	"upgradeShelfCapacity",
	"upgradeSupplierOrderSlots",
];

const session = `desktop-${Date.now()}-${Math.random().toString(36).slice(2)}`;
let revision = 0,
	ready = false,
	dirty = true,
	viewDirty = true,
	viewSentAt = 0;
// Open HUD pages, innermost last. Unity renders only the top one.
const routes: string[] = [];

function send(message: unknown) {
	process.stdout.write(`${JSON.stringify(message)}\n`);
}
function snapshot() {
	if (!ready) return;
	dirty = false;
	send(createSimulatorSnapshot(useGameStore.getState(), session, revision));
}
function view() {
	viewDirty = false;
	viewSentAt = Date.now();
	send(createDesktopView(useGameStore.getState(), revision, routes));
}
// "" closes every page, "back" pops one, "~route" replaces the top one, "!route" starts a
// fresh stack (toolbar), anything else pushes.
function navigate(route: string) {
	if (!route) routes.length = 0;
	else if (route.startsWith("!")) routes.splice(0, routes.length, route.slice(1));
	else if (route === "back") routes.pop();
	else if (route.startsWith("~")) routes.splice(-1, 1, route.slice(1));
	else if (routes.at(-1) !== route) routes.push(route);
	view();
}

const command = createSimulatorCommandHandler(
	session,
	() => useGameStore.getState(),
	() => revision,
);
useGameStore.subscribe(() => {
	revision++;
	dirty = viewDirty = true;
});

// World clicks open the same pages the toolbar does, starting a fresh stack.
function openPanel(panel: SimulatorPanel, shelfId?: string, sectorId?: string) {
	const level = useGameStore.getState().market.level;
	const unlockedSectorId =
		panel === "sectors" ? getUnlockedSimulatorSectorId(sectorId, level) : null;
	routes.length = 0;
	if (panel === "store" && shelves.some((shelf) => shelf.id === shelfId))
		navigate(`shelf:${shelfId}`);
	else if (unlockedSectorId) navigate(`sector:${unlockedSectorId}`);
	else navigate(panel);
}

function runHudAction(message: {
	id?: unknown;
	action?: unknown;
	args?: unknown;
	after?: unknown;
}) {
	const id = typeof message.id === "string" ? message.id : "invalid";
	const action = message.action as keyof GameActions;
	if (!hudActions.includes(action) || !Array.isArray(message.args))
		return send({ kind: "result", id, action, ok: false, reason: "invalid-action" });
	try {
		const run = useGameStore.getState()[action] as (...args: unknown[]) => unknown;
		const ok = run(...message.args) !== false;
		send({ kind: "result", id, action, ok, reason: ok ? "" : "game-rule-rejected" });
		if (ok && message.after === "back") routes.pop();
	} catch (error) {
		send({ kind: "result", id, action, ok: false, reason: String(error) });
	}
	view();
	snapshot();
}

createInterface({ input: process.stdin }).on("line", (raw) => {
	let message: Record<string, unknown>;
	try {
		message = JSON.parse(raw);
	} catch {
		return;
	}
	if (message.kind === "ready") {
		ready = true;
		snapshot();
		view();
	} else if (message.kind === "panel" && message.panel === "requests") {
		// A click on a customer waiting with a special request in the Unity world.
		navigate(
			typeof message.requestId === "string" && message.requestId
				? `!request:${message.requestId}`
				: "!requests",
		);
	} else if (message.kind === "panel" && message.panel === "day") {
		navigate("!day");
	} else if (
		message.kind === "panel" &&
		panels.includes(message.panel as SimulatorPanel)
	)
		openPanel(
			message.panel as SimulatorPanel,
			message.shelfId as string,
			message.sectorId as string,
		);
	else if (message.kind === "command") {
		send(command(message));
		snapshot();
	} else if (message.kind === "hud") runHudAction(message);
	else if (message.kind === "route" && typeof message.route === "string")
		navigate(message.route);
});
// Unity closing its end of the pipe is the only shutdown signal.
process.stdin.on("end", () => process.exit(0));

// Same cadence as the simulation components mounted in src/app/_layout.tsx.
const store = () => useGameStore.getState();
store().processSessionResume();
store().processInventorySpoilage();
setInterval(() => store().processGameEvents(), 5_000);
setInterval(() => store().processEmployeePayroll(), 5_000);
setInterval(() => store().processInventorySpoilage(), 60_000);
setInterval(() => store().market.isOpen && store().processNextCustomer(), 1_000);
setInterval(() => store().processProductionJobs(), 1_000);
setInterval(() => store().processSupplierOrders(), 1_000);
setInterval(() => {
	store().processCheckoutCounter();
	store().processStoreIncidents();
	store().processReceiving();
	store().processEmployeeWork();
	store().processMarketDay();
	// Paid expansions open when their works end (the app runs this in ProductionSimulation).
	store().processMarketExpansionConstruction();
	store().processMarketEraConstruction();
	store().processLotClearing();
	// Shelves, sectors and fixtures being built inside the market open on the same clock.
	store().processInteriorConstructions();
}, 1_000);
// When a day ends (timer or button) its results open on their own, like the app's sheet.
let dayPhase = store().day.phase;
setInterval(() => {
	const phase = store().day.phase;
	if (phase !== dayPhase && phase === "results") navigate("!day-result");
	dayPhase = phase;
	if (dirty) snapshot();
	// Pages and the day clock carry live timers, so they refresh every second even when idle.
	const stale =
		(routes.length > 0 || phase === "open") && Date.now() - viewSentAt > 1_000;
	if ((viewDirty || stale) && Date.now() - viewSentAt > 250) view();
}, 100);
