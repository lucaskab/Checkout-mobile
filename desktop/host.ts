import "./require-shim";
import { createInterface } from "node:readline";
import type { GameActions } from "@/@types/game";
import type { SimulatorPanel } from "@/@types/simulator";
import { shelves } from "@/data/market-products";
import { createSimulatorCommandHandler } from "@/services/simulator-protocol";
import { getUnlockedSimulatorSectorId } from "@/services/simulator-sector-selection";
import { getRecentEventOutcome } from "@/services/game-events";
import { getPiecesToPlaceBeforeOpening } from "@/services/market-era";
import { createSimulatorSnapshot } from "@/services/simulator-snapshot";
import { useGameStore } from "@/stores/game-store";
import { getCatalog, getLanguage, localizeSnapshot, localizeView, setLanguage, t } from "@/i18n";
import { createDesktopView } from "./view.ts";
import {
	applyIapMessage,
	createIapCatalogMessage,
	type IapUnityMessage,
	noteGrantedPack,
	requestPackPurchase,
} from "./iap.ts";
import {
	applyCloudMessage,
	cloudActions,
	cloudStore,
	type CloudUnityMessage,
	exportSave,
	importSave,
	requestCloudAction,
} from "./cloud.ts";
import { type AdPlacement, adPlacements, type AdsUnityMessage, applyAdsMessage, noteAdReward, requestAdPrivacy, requestRewardedAd, takePendingAd } from "./ads.ts";

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
	"grantCurrencyPack",
	"dismissDiamondShortfall",
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
// grantCurrencyPurchase credits any amount with no store: only the dev build's test buttons may use it. Real
// purchases go through grantCurrencyPack, which Unity sends when the App Store / Google Play reports a payment.
const devOnly = (action: string) =>
	action.startsWith("dev") || action === "resetGame" || action === "setMarketLevel" || action === "grantCurrencyPurchase";

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

// Too few diamonds for what the player pressed (any speed-up or diamond price): the diamond store opens on top of
// the page, saying how many are missing (Lucas 12/10). Closing it goes back to where the player was.
function openStoreOnShortfall() {
	const shortfall = useGameStore.getState().diamondShortfall;
	if (!shortfall) return false;
	useGameStore.getState().dismissDiamondShortfall();
	const route = `currency:diamonds:${Math.max(1, shortfall.missing)}`;
	if (routes.at(-1)?.startsWith("currency")) routes.splice(-1, 1, route);
	else routes.push(route);
	view();
	return true;
}

// Why opening the shop / starting a day was refused, in words the player can act on.
function rejectionReason(action: string) {
	const state = useGameStore.getState();
	if (action !== "setMarketOpen" && action !== "startDay") return null;
	if (getPiecesToPlaceBeforeOpening(state) > 0) return t("Coloque os móveis que estão esperando antes de abrir a loja.");
	if (state.day.phase === "results") return t("Veja o resultado do dia antes de abrir de novo.");
	return null;
}

function runHudAction(message: {
	id?: unknown;
	action?: unknown;
	args?: unknown;
	after?: unknown;
}) {
	const id = typeof message.id === "string" ? message.id : "invalid";
	// "Conta e nuvem" buttons: Unity signs in with Google and talks to the save server (CheckoutCloud.cs).
	if (typeof message.action === "string" && cloudActions.includes(message.action)) {
		const request = requestCloudAction(message.action, Array.isArray(message.args) ? message.args : []);
		if (request.ok) send(request.message);
		send({
			kind: "result",
			id,
			action: message.action,
			ok: request.ok,
			reason: request.ok ? "" : t(request.reason),
		});
		view();
		return;
	}
	// "Comprar" in the diamond store: Unity opens the App Store / Google Play sheet (CheckoutIap.cs).
	if (message.action === "buyCurrencyPack") {
		const request = requestPackPurchase(useGameStore.getState(), Array.isArray(message.args) ? message.args[0] : "");
		if (request.ok) send(request.message);
		send({ kind: "result", id, action: message.action, ok: request.ok, reason: request.ok ? "" : t(request.reason) });
		view();
		return;
	}
	// "Assistir vídeo": Unity plays a rewarded video (CheckoutAds.cs) for the id the host hands out.
	if (message.action === "watchRewardedAd") {
		const wanted = Array.isArray(message.args) ? message.args[0] : "";
		const placement = adPlacements.includes(wanted as AdPlacement) ? (wanted as AdPlacement) : "diamonds";
		const request = requestRewardedAd(useGameStore.getState(), Date.now(), placement);
		if (request.ok) send(request.message);
		send({ kind: "result", id, action: message.action, ok: request.ok, reason: request.ok ? "" : t(request.reason) });
		view();
		return;
	}
	// "Privacidade dos anúncios": Unity reopens Google's consent form (GDPR).
	if (message.action === "openAdPrivacy") {
		const request = requestAdPrivacy();
		if (request.ok) send(request.message);
		send({ kind: "result", id, action: message.action, ok: request.ok, reason: request.ok ? "" : t(request.reason) });
		return;
	}
	// Unity: that video was watched to the end. Only the one the host asked for pays (once).
	if (message.action === "claimRewardedAd") {
		const adId = Array.isArray(message.args) ? message.args[0] : "";
		const placement = takePendingAd(adId);
		const store = useGameStore.getState();
		let ok = false;
		if (placement === "diamonds") {
			const diamonds = store.claimRewardedAd(String(adId));
			noteAdReward(diamonds);
			ok = !!diamonds;
		} else if (placement === "consolation") {
			const prize = store.claimContractConsolation(String(adId));
			noteAdReward(prize?.diamonds ?? 0, Date.now(), prize ? `Prêmio de consolação: ${prize.label}!` : "");
			ok = !!prize;
		} else if (placement === "gift") {
			const gift = store.claimDailyLoginBonus(String(adId));
			noteAdReward(gift?.diamonds ?? 0, Date.now(), !gift ? "" : gift.diamonds ? `Presente dobrado: +${gift.coins} moedas e +${gift.diamonds} diamantes!` : `Presente dobrado: +${gift.coins} moedas!`);
			ok = !!gift;
		}
		send({ kind: "result", id, action: message.action, ok, reason: ok ? "" : "not-requested" });
		view();
		snapshot();
		return;
	}
	const action = message.action as keyof GameActions;
	if (!hudActions.includes(action) || (!__DEV__ && devOnly(action)) || !Array.isArray(message.args))
		return send({ kind: "result", id, action, ok: false, reason: "invalid-action" });
	try {
		const run = useGameStore.getState()[action] as (...args: unknown[]) => unknown;
		const value = run(...message.args);
		const ok = value !== false && value !== null;
		if (action === "grantCurrencyPack") noteGrantedPack(value as { coins: number; diamonds: number } | null);
		const short = !ok ? useGameStore.getState().diamondShortfall : null;
		const reason = ok
			? ""
			: short
				? t(short.missing === 1 ? "Falta 1 diamante." : `Faltam ${short.missing} diamantes.`)
				: rejectionReason(action) ?? "game-rule-rejected";
		send({ kind: "result", id, action, ok, reason });
		if (ok && message.after === "back") routes.pop();
		// "!route" / "~route": the action then opens a page (the level-up celebration's group buttons).
		else if (ok && typeof message.after === "string" && /^[!~]/.test(message.after)) navigate(message.after);
	} catch (error) {
		send({ kind: "result", id, action, ok: false, reason: String(error) });
	}
	if (!openStoreOnShortfall()) view();
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
		// The packs Unity asks the App Store / Google Play for (CheckoutIap.cs).
		send(createIapCatalogMessage());
		snapshot();
		view();
	} else if (message.kind === "language" && typeof message.lang === "string") {
		// Opções › Idioma during the game (CheckoutSettings): from now on pages, names and Unity's own texts go out in
		// the new language.
		setLanguage(message.lang);
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
		// The world's "Acelerar" boards too: too few diamonds opens the store.
		openStoreOnShortfall();
		snapshot();
	} else if (message.kind === "cloud") {
		const before = cloudStore.status;
		applyCloudMessage(message as CloudUnityMessage);
		// Two phones went separate ways: the choice opens by itself (once).
		if (cloudStore.status === "conflict" && before !== "conflict") navigate("!conta");
		else view();
	} else if (message.kind === "cloud-export") {
		send({ kind: "cloud-save", id: message.id ?? "", ...exportSave() });
	} else if (message.kind === "cloud-import") {
		importSave(message.data).then(
			(ok) => {
				send({ kind: "cloud-imported", id: message.id ?? "", ok });
				snapshot();
				view();
			},
			() => send({ kind: "cloud-imported", id: message.id ?? "", ok: false }),
		);
	} else if (message.kind === "ad") {
		applyAdsMessage(message as AdsUnityMessage);
		view();
	} else if (message.kind === "iap") {
		applyIapMessage(message as IapUnityMessage);
		view();
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
	openStoreOnShortfall();
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
