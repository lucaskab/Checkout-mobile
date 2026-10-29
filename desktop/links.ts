/**
 * The game's pages on the web (App Store rule 5.1.1(i): the privacy policy must be reachable inside the app).
 * The pages only name them ("privacy" / "support"); Unity opens the address in the browser (CheckoutLinks in
 * CheckoutSettings.cs, which keeps the same two addresses for the Opções window before the game starts).
 */
export const gameLinks = {
	privacy: "https://lucaskab.github.io/privacy.html",
	support: "https://lucaskab.github.io",
} as const;
export type GameLink = keyof typeof gameLinks;

export function isGameLink(value: unknown): value is GameLink {
	return typeof value === "string" && Object.prototype.hasOwnProperty.call(gameLinks, value);
}
