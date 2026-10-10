import "./require-shim";
import { createInterface } from "node:readline";
import type { GameActions } from "@/@types/game";
import type { SimulatorPanel } from "@/@types/simulator";
import { shelves } from "@/data/market-products";
import { createSimulatorCommandHandler } from "@/services/simulator-protocol";
import { getUnlockedSimulatorSectorId } from "@/services/simulator-sector-selection";
import { getRecentEventOutcome } from "@/services/game-events";
import { createSimulatorSnapshot } from "@/services/simulator-snapshot";
import { useGameStore } from "@/stores/game-store";
import { getCatalog, getLanguage, localizeSnapshot, localizeView, setLanguage } from "@/i18n";
import { createDesktopView } from "./view.ts";

// Desktop stand-in for the React Native app: owns the same zustand store, runs the same
// timers as src/app/_layout.tsx and speaks the Unity bridge protocol over stdin/stdout.
// stdout carries one JSON message per line, so logs from the game code go to stderr.
console.log = console.info = console.warn = console.error;
// The language picked on Unity's start screen ("pt", "en", "es", "fr", "de"). The game's texts are
// Portuguese; pages and snapshots are translated on the way out, so Unity only draws them.
setLanguage(process.env.CHECKOUT_LANG);

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
	"activateShopBooster",
	"assignProductToShelf",
	"buildSector",
	"claimDailyGoal",
	"claimDayResult",
	"acceptDeliveryOrder",
	"declineDeliveryOrder",
	"packDeliveryOrder",
	"handOverDelivery",
	"claimMission",
	"claimAllMissions",
	"clearShelf",
	"completeCheckout",
	"checkoutArrived",
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
	"devSpawnDeliveryOffer",
	"devFinishMarketExpansion",
	"devFinishInteriorConstructions",
	"devTriggerIncident",
	"devWearShelf",
	"dismissOfflineSummary",
	"dismissLevelUp",
	"dismissCelebration",
	"onboardingNext",
	"skipOnboarding",
	"restartOnboarding",
	"dismissOnboardingTip",
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
	"placeSupplierCart",
	"orderLowStock",
	"purchaseDecor",
	"purchaseShopItem",
	"resetGame",
	"resolveSpecialRequest",
	"restockShelf",
	"serveWindowSale",
	"setEmployeeWorking",
	"setMarketLevel",
	"setMarketOpen",
	"setShelfPrice",
	"swapShelfSlots",
	"tendShelf",
	"startDay",
	"startProduction",
	"cookByHand",
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

// Release builds (the testers' build and the iPhone) refuse the dev cheats even if a page still asked for one.
const devOnly = (action: string) => action.startsWith("dev") || action === "resetGame" || action === "setMarketLevel";

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
	send(localizeSnapshot(createSimulatorSnapshot(useGameStore.getState(), session, revision)));
}
function view() {
	viewDirty = false;
	viewSentAt = Date.now();
	send(localizeView(createDesktopView(useGameStore.getState(), revision, routes)));
}
// "" closes every page, "back" pops one, "~route" replaces the top one, "!route" starts a
// fresh stack (toolbar), anything else pushes.
function navigate(route: string) {
	if (!route) routes.length = 0;
	else if (route.startsWith("!")) routes.splice(0, routes.length, route.slice(1));
	else if (route === "back") routes.pop();
	else if (route.startsWith("~")) routes.splice(-1, 1, route.slice(1));
	else if (routes.at(-1) !== route) routes.push(route);
	// Opening a page can finish a tutorial step ("toque no caixote"), so the coach moves on right away.
	useGameStore.getState().processOnboarding(routes.at(-1) ?? "");
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
	if (!hudActions.includes(action) || (!__DEV__ && devOnly(action)) || !Array.isArray(message.args))
		return send({ kind: "result", id, action, ok: false, reason: "invalid-action" });
	try {
		const run = useGameStore.getState()[action] as (...args: unknown[]) => unknown;
		const ok = run(...message.args) !== false;
		send({ kind: "result", id, action, ok, reason: ok ? "" : "game-rule-rejected" });
		if (ok && message.after === "back") routes.pop();
		// "!route" / "~route": the action then opens a page (the level-up celebration's group buttons).
		else if (ok && typeof message.after === "string" && /^[!~]/.test(message.after)) navigate(message.after);
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
		// Unity's own texts (counter game, map popups, HUD labels) use the same catalog.
		const catalog = getCatalog();
		send({ kind: "i18n", lang: getLanguage(), keys: Object.keys(catalog), values: Object.values(catalog) });
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
// Every second, so an event ends exactly at 0:00 and the market closing ends it at once.
setInterval(() => store().processGameEvents(), 1_000);
setInterval(() => store().processEmployeePayroll(), 5_000);
setInterval(() => store().processInventorySpoilage(), 60_000);
setInterval(() => store().market.isOpen && store().processNextCustomer(), 1_000);
setInterval(() => store().processProductionJobs(), 1_000);
setInterval(() => store().processSupplierOrders(), 1_000);
setInterval(() => {
	store().processCheckoutCounter();
	store().processStoreIncidents();
	store().processReceiving();
	store().processDelivery();
	store().processOnboarding(routes.at(-1) ?? "");
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
	// Pages, the day clock and the event badge carry live timers, so they refresh every second even when idle.
	const stale =
		(routes.length > 0 ||
			phase === "open" ||
			store().events.activeEvent !== null ||
			getRecentEventOutcome(store().events, Date.now() - 1_500) !== null) &&
		Date.now() - viewSentAt > 1_000;
	if ((viewDirty || stale) && Date.now() - viewSentAt > 250) view();
}, 100);
