import { Image } from "expo-image";
import type { ImageStyle, StyleProp } from "react-native";
import { getProductAsset } from "@/data/product-assets";

type ProductImageProps = {
	productId: number;
	style?: StyleProp<ImageStyle>;
};

export function ProductImage({ productId, style }: ProductImageProps) {
	return (
		<Image
			accessibilityIgnoresInvertColors
			cachePolicy="memory-disk"
			contentFit="contain"
			source={getProductAsset(productId)}
			style={style}
			transition={0}
		/>
	);
}
