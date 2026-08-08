import { Image, type ImageStyle, type StyleProp } from "react-native";
import { type GameIconId, getGameIconAsset } from "@/data/game-icon-assets";

type GameIconProps = {
	accessibilityLabel?: string;
	icon: GameIconId;
	style?: StyleProp<ImageStyle>;
};

export function GameIcon({ accessibilityLabel, icon, style }: GameIconProps) {
	return (
		<Image
			accessibilityLabel={accessibilityLabel}
			accessibilityIgnoresInvertColors
			resizeMode="contain"
			source={getGameIconAsset(icon)}
			style={style}
		/>
	);
}
