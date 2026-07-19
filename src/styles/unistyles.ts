import { StyleSheet } from "react-native-unistyles";

const lightTheme = {
	colors: {
		/* ── Blue (primary brand — retail trust, Carrefour/Walmart style) ── */
		"blue-50": "#EFF6FF",
		"blue-100": "#DBEAFE",
		"blue-200": "#BFDBFE",
		"blue-300": "#93C5FD",
		"blue-400": "#60A5FA",
		"blue-500": "#2563EB" /* primary action */,
		"blue-600": "#1D4ED8",
		"blue-700": "#1E40AF",
		"blue-800": "#1E3A8A",

		/* ── Red (sale tags, urgency, promos) ───────────────────────────── */
		"red-50": "#FFF1F2",
		"red-100": "#FFE4E6",
		"red-200": "#FECDD3",
		"red-400": "#F87171",
		"red-500": "#DC2626" /* sale red */,
		"red-600": "#B91C1C",

		/* ── Green (positive outcomes and successful purchases) ─────────── */
		"green-50": "#ECFDF3",
		"green-100": "#D1FADF",
		"green-500": "#12B76A",
		"green-600": "#039855",

		/* ── Amber / Gold (coins, warmth, bakery) ───────────────────────── */
		"amber-50": "#FFFBEB",
		"amber-100": "#FEF3C7",
		"amber-200": "#FDE68A",
		"amber-400": "#FBBF24" /* coin gold */,
		"amber-500": "#D97706",
		"amber-600": "#B45309",

		/* ── Violet (gems, premium) ─────────────────────────────────────── */
		"violet-50": "#F5F3FF",
		"violet-100": "#EDE9FE",
		"violet-400": "#A78BFA",
		"violet-500": "#7C3AED" /* gem violet */,
		"violet-600": "#6D28D9",

		/* ── Neutrals (structure, text, borders) ────────────────────────── */
		"neutral-0": "#FFFFFF",
		"neutral-50": "#F8FAFF" /* page bg — faint blue tint */,
		"neutral-100": "#EEF2FF",
		"neutral-150": "#E0E7FF",
		"neutral-200": "#C7D2FE",
		"neutral-300": "#A5B4FC",
		"neutral-400": "#818CF8",
		"neutral-500": "#6366F1",
		"neutral-600": "#4338CA",
		"neutral-700": "#1E2060" /* deep navy for text */,
		"neutral-800": "#0F1240",

		/* ── Game aliases (shared store and supplier surfaces) ───────────── */
		gameBackground: "#F8FAFF",
		gameText: "#0F1240",
		gameMuted: "#6366F1",
		gameAccentSoft: "#EFF6FF",
		gameBorder: "#E0E7FF",
		gameShelf: "#FEF3C7",
		gameShelfBorder: "#B45309",
		gameLockedShelf: "#F8FAFF",
	},
	fonts: {
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
