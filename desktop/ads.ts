import type { GameStore } from "@/@types/game";
import { getRewardedAdOffer } from "@/services/rewarded-ads";

/**
 * Rewarded videos as the host sees them (rules: src/services/rewarded-ads.ts). The video itself plays in Unity
 * (CheckoutAds.cs: Google AdMob on the phone, a test video in the Editor); the host:
 * - asks Unity to show one (`ad-show` with a fresh id) when the player presses "Assistir vídeo";
 * - credits it (claimRewardedAd) only when Unity reports that same id was watched to the end — a video it did not
 *   ask for, or the same one twice, gives nothing;
 * - keeps what Unity tells about the videos (ready, loading, none available) and the last result for the pages;
 * - shows "Privacidade dos anúncios" when Google's consent tool says the player must be able to change their choice
 *   (GDPR: Europe, UK, Switzerland) and asks Unity to open that form (`ad-privacy`).
 */
export type AdsStatus = "starting" | "ready" | "loading" | "unavailable";
export type AdEvent = { kind: "rewarded" | "closed" | "failed"; at: number; diamonds: number };

export const adsStore = {
	status: "starting" as AdsStatus,
	/** The video the game asked for and has not credited yet. */
	pendingId: "",
	pendingAt: 0,
	last: null as AdEvent | null,
	/** The player must be able to reopen the ads consent form (Unity reports it after asking Google). */
	privacyOptions: false,
};

let sequence = 0;

export type ShowAdResult =
	| { ok: true; message: { kind: "ad-show"; id: string } }
	| { ok: false; reason: string };

/** "Assistir vídeo": checks the player may watch one now and builds the message for Unity. */
export function requestRewardedAd(state: GameStore, now = Date.now()): ShowAdResult {
	const offer = getRewardedAdOffer(state.rewardedAds, now);
	if (!offer.available)
		return {
			ok: false,
			reason: offer.reason === "daily-cap" ? "Você já assistiu os vídeos de hoje. Volte amanhã!" : "Espere um pouco para o próximo vídeo.",
		};
	if (adsStore.status === "unavailable") return { ok: false, reason: "Nenhum vídeo disponível agora. Tente mais tarde." };
	// One at a time (a video left open more than 2 minutes is given up).
	if (adsStore.pendingId && now - adsStore.pendingAt < 120_000) return { ok: false, reason: "O vídeo já está abrindo." };
	adsStore.pendingId = `ad-${now.toString(36)}-${(++sequence).toString(36)}`;
	adsStore.pendingAt = now;
	return { ok: true, message: { kind: "ad-show", id: adsStore.pendingId } };
}

/** Unity says the video `id` was watched to the end: whether it is the one the game is waiting for. */
export function takePendingAd(id: unknown) {
	if (typeof id !== "string" || !id || id !== adsStore.pendingId) return false;
	adsStore.pendingId = "";
	return true;
}

export type AdsUnityMessage = { kind: "ad"; status?: unknown; event?: unknown; id?: unknown; privacy?: unknown };

export function applyAdsMessage(message: AdsUnityMessage, now = Date.now()) {
	if (message.status === "ready" || message.status === "loading" || message.status === "unavailable")
		adsStore.status = message.status;
	if (typeof message.privacy === "boolean") adsStore.privacyOptions = message.privacy;
	if ((message.event === "closed" || message.event === "failed") && message.id === adsStore.pendingId) {
		adsStore.pendingId = "";
		adsStore.last = { kind: message.event, at: now, diamonds: 0 };
	}
}

export function noteAdReward(diamonds: number | null, now = Date.now()) {
	if (diamonds && diamonds > 0) adsStore.last = { kind: "rewarded", at: now, diamonds };
}

/** "Privacidade dos anúncios": the message for Unity to reopen the consent form (only when Google asks for it). */
export function requestAdPrivacy(): { ok: true; message: { kind: "ad-privacy" } } | { ok: false; reason: string } {
	if (!adsStore.privacyOptions) return { ok: false, reason: "Nada para ajustar neste aparelho." };
	return { ok: true, message: { kind: "ad-privacy" } };
}

/** The last result while it is worth showing (a few seconds). */
export function getLastAdEvent(now = Date.now()) {
	return adsStore.last && now - adsStore.last.at < 8_000 ? adsStore.last : null;
}

export function resetAdsStore() {
	adsStore.status = "starting";
	adsStore.pendingId = "";
	adsStore.pendingAt = 0;
	adsStore.last = null;
	adsStore.privacyOptions = false;
}
