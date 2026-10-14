import type { GameStore } from "@/@types/game";
import { getRewardedAdOffer } from "@/services/rewarded-ads";
import { canClaimConsolation } from "@/services/contract-pressure";
import { canDoubleDailyLogin } from "@/services/daily-login";

/**
 * What a video is for: the diamonds of "Diamantes grátis" (5 a day), the missed contract's consolation, or the
 * daily gift doubled. Unity only plays the video; the host remembers the placement and credits it when the video
 * the host asked for ends.
 */
export type AdPlacement = "diamonds" | "consolation" | "gift";
export const adPlacements: AdPlacement[] = ["diamonds", "consolation", "gift"];

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
export type AdEvent = { kind: "rewarded" | "closed" | "failed"; at: number; diamonds: number; label?: string };

export const adsStore = {
	status: "starting" as AdsStatus,
	/** The video the game asked for and has not credited yet. */
	pendingId: "",
	pendingAt: 0,
	pendingPlacement: "diamonds" as AdPlacement,
	last: null as AdEvent | null,
	/** The player must be able to reopen the ads consent form (Unity reports it after asking Google). */
	privacyOptions: false,
};

let sequence = 0;

export type ShowAdResult =
	| { ok: true; message: { kind: "ad-show"; id: string } }
	| { ok: false; reason: string };

/** Why a video of this placement cannot be watched now ("" = it can). */
export function adPlacementBlock(state: GameStore, placement: AdPlacement, now = Date.now()) {
	if (placement === "consolation")
		return state.day.phase === "results" && canClaimConsolation(state.day.result) ? "" : "Este prêmio já foi resgatado.";
	if (placement === "gift")
		return canDoubleDailyLogin(state.dailyLogin, now) ? "" : "Resgate o presente de hoje primeiro (ou ele já foi dobrado).";
	return getRewardedAdOffer(state.rewardedAds, now).available ? "" : "Espere um pouco para o próximo vídeo.";
}

/** "Assistir vídeo": checks the player may watch one now and builds the message for Unity. */
export function requestRewardedAd(state: GameStore, now = Date.now(), placement: AdPlacement = "diamonds"): ShowAdResult {
	const blocked = adPlacementBlock(state, placement, now);
	if (blocked) return { ok: false, reason: blocked };
	if (adsStore.status === "unavailable") return { ok: false, reason: "Nenhum vídeo disponível agora. Tente mais tarde." };
	// One at a time (a video left open more than 2 minutes is given up).
	if (adsStore.pendingId && now - adsStore.pendingAt < 120_000) return { ok: false, reason: "O vídeo já está abrindo." };
	adsStore.pendingId = `ad-${now.toString(36)}-${(++sequence).toString(36)}`;
	adsStore.pendingAt = now;
	adsStore.pendingPlacement = placement;
	return { ok: true, message: { kind: "ad-show", id: adsStore.pendingId } };
}

/** A video is opening for this placement (any when omitted); one left open over 2 minutes is given up. */
export function isAdOpening(placement?: AdPlacement, now = Date.now()) {
	return !!adsStore.pendingId && now - adsStore.pendingAt < 120_000 && (!placement || adsStore.pendingPlacement === placement);
}

/** Unity says the video `id` was watched to the end: its placement when it is the one the game is waiting for. */
export function takePendingAd(id: unknown): AdPlacement | null {
	if (typeof id !== "string" || !id || id !== adsStore.pendingId) return null;
	adsStore.pendingId = "";
	return adsStore.pendingPlacement;
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

export function noteAdReward(diamonds: number | null, now = Date.now(), label = "") {
	if ((diamonds && diamonds > 0) || label) adsStore.last = { kind: "rewarded", at: now, diamonds: diamonds ?? 0, label };
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
	adsStore.pendingPlacement = "diamonds";
	adsStore.last = null;
	adsStore.privacyOptions = false;
}
