import { currencyPacks, getCurrencyPack, isCurrencyPackAvailable } from "@/data/currency-packs";
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
	/** A purchase waiting for the App Store sheet / approval (product id). */
	busyProductId: "",
	/** The last thing that happened (shown at the top of the diamond store). */
	notice: null as IapNotice | null,
};

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
};

export function applyIapMessage(message: IapUnityMessage, now = Date.now()) {
	if (message.status === "ready" || message.status === "unavailable") iapStore.status = message.status;
	// Prices come as two parallel arrays (Unity's JsonUtility has no dictionaries).
	// (Unity's JsonUtility writes empty arrays on the event messages: only a list with prices replaces them.)
	if (Array.isArray(message.productIds) && Array.isArray(message.prices) && message.prices.length > 0) {
		const prices: Record<string, string> = {};
		message.productIds.forEach((id, i) => {
			const price = (message.prices as unknown[])[i];
			if (typeof id === "string" && typeof price === "string" && price) prices[id] = price;
		});
		iapStore.prices = prices;
	}
	const productId = typeof message.productId === "string" ? message.productId : "";
	switch (message.event) {
		case "cancelled":
			iapStore.busyProductId = "";
			iapStore.notice = { text: "Compra cancelada.", ok: false, at: now };
			break;
		case "failed":
			iapStore.busyProductId = "";
			iapStore.notice = {
				text: "A compra não foi concluída. Nada foi cobrado.",
				ok: false,
				at: now,
			};
			break;
		case "deferred":
			// Waiting for a parent's approval: no second order meanwhile (the welcome combo could be paid twice).
			iapStore.busyProductId = productId || iapStore.busyProductId;
			iapStore.notice = {
				text: "Compra aguardando aprovação. Os diamantes chegam assim que ela for aprovada.",
				ok: true,
				at: now,
			};
			break;
		case "started":
			iapStore.busyProductId = productId;
			break;
	}
}

/** The price shown on a pack: the store's own (local currency) once Unity has it, the catalog's until then. */
export function getPackPrice(productId: string) {
	return iapStore.prices[productId] ?? getCurrencyPack(productId)?.fallbackPrice ?? "";
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
	if (iapStore.busyProductId) return { ok: false, reason: "Já existe uma compra em andamento." };
	iapStore.busyProductId = pack.productId;
	return { ok: true, message: { kind: "purchase", productId: pack.productId, packId: pack.id } };
}

/** After the pack was credited (grantCurrencyPack): the notice at the top of the store. */
export function noteGrantedPack(grant: { coins: number; diamonds: number } | null, now = Date.now()) {
	iapStore.busyProductId = "";
	if (!grant) return;
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
	iapStore.busyProductId = "";
	iapStore.notice = null;
}
