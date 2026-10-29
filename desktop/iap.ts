import { currencyPacks, getCurrencyPack, getRegionalPrice, isCurrencyPackAvailable } from "@/data/currency-packs";
import type { GameStore } from "@/@types/game";

/**
 * The diamond store as the host sees it (Lucas 12/10: diamonds are bought with real money). The purchase itself
 * happens in Unity (CheckoutIap.cs, Unity IAP: App Store / Google Play); the host only:
 * - sends Unity the catalog (`iap-catalog`) when it connects;
 * - asks Unity to buy a pack (`purchase`) when the player presses "Comprar";
 * - credits the pack when Unity reports the store's pending order (HUD action grantCurrencyPack, once per
 *   transaction: src/stores/game-store.ts), and Unity confirms the order to the store only after that;
 * - keeps what Unity tells about the store (`iap`: ready or not, local prices, the last purchase) for the pages.
 */
export type IapStoreStatus = "starting" | "ready" | "unavailable";

export type IapNotice = { text: string; ok: boolean; at: number };

export const iapStore = {
	status: "starting" as IapStoreStatus,
	/** Store prices in the player's currency, by product id ("R$ 24,90"). */
	prices: {} as Record<string, string>,
	/** The products the store says can be bought now (null until it gives its list). */
	productIds: null as string[] | null,
	/** A purchase waiting for the App Store sheet / approval (product id). */
	busyProductId: "",
	/** The last thing that happened (shown at the top of the diamond store). */
	notice: null as IapNotice | null,
	/** The device's country ("BR", "US", "DE"…): the currency of the prices until the store answers. */
	region: "",
	/** What just happened to each pack's purchase, shown on its own card (cancelled, failed, waiting, bought). */
	packEvents: {} as Record<string, PackEvent>,
};

export type PackEventKind = "cancelled" | "failed" | "deferred" | "bought";
export type PackEvent = { kind: PackEventKind; at: number; text: string };
/** How long the card keeps showing it. */
const PACK_EVENT_MS: Record<PackEventKind, number> = { cancelled: 8_000, failed: 10_000, deferred: 10 * 60_000, bought: 12_000 };

/** The latest event of a pack, while it is still worth showing. */
export function getPackEvent(productId: string, now = Date.now()) {
	const event = iapStore.packEvents[productId];
	return event && now - event.at < PACK_EVENT_MS[event.kind] ? event : null;
}

export type IapCatalogMessage = {
	kind: "iap-catalog";
	products: { productId: string; packId: string }[];
};

export function createIapCatalogMessage(): IapCatalogMessage {
	return {
		kind: "iap-catalog",
		products: currencyPacks.map((pack) => ({ productId: pack.productId, packId: pack.id })),
	};
}

/** What Unity reports about the store. */
export type IapUnityMessage = {
	kind: "iap";
	status?: string;
	productIds?: unknown;
	prices?: unknown;
	productId?: unknown;
	event?: unknown;
	message?: unknown;
	region?: unknown;
};

export function applyIapMessage(message: IapUnityMessage, now = Date.now()) {
	if (message.status === "ready" || message.status === "unavailable") iapStore.status = message.status;
	if (typeof message.region === "string" && message.region) iapStore.region = message.region;
	// Prices come as two parallel arrays (Unity's JsonUtility has no dictionaries).
	// (Unity's JsonUtility writes empty arrays on the event messages: only a list with prices replaces them.)
	if (Array.isArray(message.productIds) && Array.isArray(message.prices) && message.prices.length > 0) {
		const prices: Record<string, string> = {};
		const ids: string[] = [];
		message.productIds.forEach((id, i) => {
			if (typeof id !== "string" || !id) return;
			ids.push(id);
			const price = (message.prices as unknown[])[i];
			if (typeof price === "string" && price) prices[id] = price;
		});
		iapStore.prices = prices;
		iapStore.productIds = ids;
	}
	const productId = typeof message.productId === "string" ? message.productId : "";
	switch (message.event) {
		case "cancelled":
			iapStore.busyProductId = "";
			if (productId) iapStore.packEvents[productId] = { kind: "cancelled", at: now, text: "Compra cancelada" };
			break;
		case "failed":
			iapStore.busyProductId = "";
			if (productId)
				iapStore.packEvents[productId] = { kind: "failed", at: now, text: "Não concluída · nada foi cobrado" };
			break;
		case "deferred":
			// Waiting for a parent's approval: no second order meanwhile (the welcome combo could be paid twice).
			iapStore.busyProductId = productId || iapStore.busyProductId;
			if (productId)
				iapStore.packEvents[productId] = { kind: "deferred", at: now, text: "Aguardando aprovação" };
			break;
		case "started":
			iapStore.busyProductId = productId;
			break;
	}
}

/**
 * Where the purchases happen, by the device the game runs on: the App Store on the iPhone, Google Play on Android,
 * no store on the PC / Mac builds (the embedded host sets process.platform to "ios" or "android": desktop/embedded/env.ts).
 * The pages name only the store of this device (App Store rule 2.3.10: no other platform's store on the iPhone).
 */
export type StorePlatform = "ios" | "android" | "other";
export function storePlatform(): StorePlatform {
	const platform = String((globalThis as { process?: { platform?: unknown } }).process?.platform ?? "");
	return platform === "ios" ? "ios" : platform === "android" ? "android" : "other";
}

/** Can this pack be bought right now (the store answered and lists it)? */
export function isPackPurchasable(productId: string) {
	if (iapStore.status !== "ready") return false;
	return !iapStore.productIds || iapStore.productIds.length === 0 || iapStore.productIds.includes(productId);
}

/**
 * The price shown on a pack: only the store's own (in the player's currency) and only once the store is ready —
 * never a price of our own table as if the pack could be bought (App Store review, 29/10). "" = no price to show.
 * The Editor's test store has no prices: there (not on a phone) the region's table stands in, to see the screens.
 */
export function getPackPrice(productId: string) {
	if (!isPackPurchasable(productId)) return "";
	if (iapStore.prices[productId]) return iapStore.prices[productId];
	if (storePlatform() !== "other") return "";
	const pack = getCurrencyPack(productId);
	return pack ? getRegionalPrice(pack, iapStore.region) : "";
}

export type BuyPackResult =
	| { ok: true; message: { kind: "purchase"; productId: string; packId: string } }
	| { ok: false; reason: string };

/** "Comprar": checks the pack can be bought now and builds the message that asks Unity to buy it. */
export function requestPackPurchase(state: GameStore, packId: unknown): BuyPackResult {
	const pack = typeof packId === "string" ? getCurrencyPack(packId) : undefined;
	if (!pack) return { ok: false, reason: "Pacote desconhecido." };
	if (!isCurrencyPackAvailable(pack, state.currencyPurchases.purchasedPackIds))
		return { ok: false, reason: "Esta oferta já foi comprada." };
	if (iapStore.status !== "ready")
		return {
			ok: false,
			reason:
				iapStore.status === "starting"
					? "A loja ainda está carregando. Tente de novo em instantes."
					: "A loja não está disponível neste aparelho agora.",
		};
	if (!isPackPurchasable(pack.productId)) return { ok: false, reason: "Este pacote não está disponível na loja agora." };
	if (iapStore.busyProductId) return { ok: false, reason: "Já existe uma compra em andamento." };
	iapStore.busyProductId = pack.productId;
	return { ok: true, message: { kind: "purchase", productId: pack.productId, packId: pack.id } };
}

/** After the pack was credited (grantCurrencyPack): the notice at the top of the store. */
export function noteGrantedPack(
	grant: { packId?: string; coins: number; diamonds: number } | null,
	now = Date.now(),
) {
	iapStore.busyProductId = "";
	if (!grant) return;
	const pack = grant.packId ? getCurrencyPack(grant.packId) : undefined;
	if (pack)
		iapStore.packEvents[pack.productId] = {
			kind: "bought",
			at: now,
			text: grant.diamonds > 0 ? `Comprado! +${grant.diamonds.toLocaleString("pt-BR")} diamantes` : `Comprado! +${grant.coins.toLocaleString("pt-BR")} moedas`,
		};
	const parts = [
		grant.diamonds > 0 ? `+${grant.diamonds.toLocaleString("pt-BR")} diamantes` : "",
		grant.coins > 0 ? `+${grant.coins.toLocaleString("pt-BR")} moedas` : "",
	].filter(Boolean);
	iapStore.notice = { text: `Compra concluída: ${parts.join(" e ")}. Obrigado!`, ok: true, at: now };
}

/** Resets the module (tests). */
export function resetIapStore() {
	iapStore.status = "starting";
	iapStore.prices = {};
	iapStore.productIds = null;
	iapStore.busyProductId = "";
	iapStore.notice = null;
	iapStore.region = "";
	iapStore.packEvents = {};
}
