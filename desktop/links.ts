/**
 * The game's pages on the web (App Store rule 5.1.1(i): the privacy policy must be reachable inside the app).
 * The pages only name them ("privacy" / "support"); Unity opens the address in the browser (CheckoutLinks in
 * CheckoutSettings.cs, which keeps the same two addresses for the Opções window before the game starts).
 */
export const gameLinks = {
	privacy: "https://lucaskab.github.io/privacy.html",
	support: "https://lucaskab.github.io",
	// The game's Discord server (Lucas 06/11): bugs, suggestions, questions, players' markets. A permanent invite.
	discord: "https://discord.gg/xfMgfpYzMu",
	// The game's page in the store of this device (Lucas 10/11, "Versão nova disponível"): Unity picks the App Store
	// on the iPhone and Google Play on Android (CheckoutLinks "store").
	store: "store",
} as const;
export type GameLink = keyof typeof gameLinks;

export function isGameLink(value: unknown): value is GameLink {
	return typeof value === "string" && Object.prototype.hasOwnProperty.call(gameLinks, value);
}
