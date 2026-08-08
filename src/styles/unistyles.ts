import { StyleSheet } from "react-native-unistyles";

export const gameFontFamilies = {
	headline: "Fredoka_700Bold",
	badge: "Fredoka_600SemiBold",
	body: "Nunito_400Regular",
	bodyMedium: "Nunito_600SemiBold",
	bodyBold: "Nunito_700Bold",
	bodyExtraBold: "Nunito_800ExtraBold",
	number: "JetBrainsMono_500Medium",
	numberBold: "JetBrainsMono_700Bold",
} as const;

const lightTheme = {
	colors: {
		/* ── Blue (primary action — friendly cozy sky/teal, shop signage) ─── */
		"blue-50": "#E9F6FA",
		"blue-100": "#CDEBF3",
		"blue-200": "#A3D9E8",
		"blue-300": "#6FC0D6",
		"blue-400": "#3FA3C0",
		"blue-500": "#2E8CAE" /* primary action — cozy teal-blue */,
		"blue-600": "#1F718F",
		"blue-700": "#175A73",
		"blue-800": "#123F52",

		/* ── Red (sale tags, urgency — warm ripe tomato) ─────────────────── */
		"red-50": "#FDF0EB",
		"red-100": "#FBDDD1",
		"red-200": "#F6BFA9",
		"red-400": "#EF8A63",
		"red-500": "#E15533" /* tomato sale red */,
		"red-600": "#C0401F",

		/* ── Green (fresh produce, success, growth) ──────────────────────── */
		"green-50": "#EEF7E4",
		"green-100": "#D6EDBE",
		"green-500": "#5DA637" /* leafy produce green */,
		"green-600": "#427A24",

		/* ── Amber / Gold (coins, bakery warmth, wood glow) ──────────────── */
		"amber-50": "#FEF6E4",
		"amber-100": "#FBE9C2",
		"amber-200": "#F6D68C",
		"amber-400": "#F2B03D" /* coin gold */,
		"amber-500": "#D98A2B",
		"amber-600": "#A9651C",

		/* ── Violet (gems, premium — ripe berry/plum) ────────────────────── */
		"violet-50": "#F4EEF7",
		"violet-100": "#E6D9EE",
		"violet-400": "#B48FCB",
		"violet-500": "#8B5C9E" /* gem plum */,
		"violet-600": "#6D4487",

		/* ── Neutrals (warm parchment surfaces → wood-brown text) ────────── */
		"neutral-0": "#FFFFFF",
		"neutral-50": "#FFF7EC" /* page bg — warm cream */,
		"neutral-100": "#FBEEDA",
		"neutral-150": "#F1E1C6" /* warm wood border */,
		"neutral-200": "#E6CFA6",
		"neutral-300": "#D4B482",
		"neutral-400": "#BC9560",
		"neutral-500": "#977552" /* muted wood text */,
		"neutral-600": "#6E5237",
		"neutral-700": "#4A3624" /* deep wood text */,
		"neutral-800": "#2E2013",

		/* ── Game aliases (shared store and supplier surfaces) ───────────── */
		gameBackground: "#FFF7EC",
		gameText: "#2E2013",
		gameMuted: "#977552",
		gameAccentSoft: "#FFF1DE",
		gameBorder: "#F1E1C6",
		gameShelf: "#F0D39B" /* warm pine shelf */,
		gameShelfBorder: "#A9651C" /* wood edge */,
		gameLockedShelf: "#F5ECDD",
	},
	fonts: {
		family: gameFontFamilies,
		size: {
			/** 13px */
			small: 13,
			/** 16px */
			medium: 16,
			/** 18px */
			large: 18,
		},
		weight: {
			regular: "400" as const,
			medium: "500" as const,
			bold: "700" as const,
		},
	},
	gap: (v: number) => v * 8,
};

const appThemes = {
	light: lightTheme,
};

const breakpoints = {
	xs: 0,
	sm: 300,
	md: 500,
	lg: 800,
	xl: 1200,
};

type AppBreakpoints = typeof breakpoints;
type AppThemes = typeof appThemes;

declare module "react-native-unistyles" {
	export interface UnistylesThemes extends AppThemes {}
	export interface UnistylesBreakpoints extends AppBreakpoints {}
}

StyleSheet.configure({
	settings: {
		initialTheme: "light",
	},
	breakpoints,
	themes: appThemes,
});
