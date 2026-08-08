import {
	StyleSheet as ReactNativeStyleSheet,
	Text,
	type TextProps,
	type TextStyle,
} from "react-native";
import { gameFontFamilies } from "@/styles/unistyles";

export function GameText({ style, ...props }: TextProps) {
	const flattenedStyle = ReactNativeStyleSheet.flatten(style);
	const fontFamily =
		flattenedStyle?.fontFamily ??
		getBodyFontFamily(flattenedStyle?.fontWeight, gameFontFamilies);

	return <Text {...props} style={[{ fontFamily }, style]} />;
}

function getBodyFontFamily(
	fontWeight: TextStyle["fontWeight"],
	fontFamily: {
		body: string;
		bodyBold: string;
		bodyExtraBold: string;
		bodyMedium: string;
	},
) {
	switch (fontWeight) {
		case "800":
		case "900":
		case 800:
		case 900:
			return fontFamily.bodyExtraBold;
		case "bold":
		case "700":
		case 700:
			return fontFamily.bodyBold;
		case "500":
		case "600":
		case 500:
		case 600:
			return fontFamily.bodyMedium;
		default:
			return fontFamily.body;
	}
}
