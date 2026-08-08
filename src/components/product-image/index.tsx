import { Image, type ImageStyle, type StyleProp } from "react-native";
import { getProductAsset } from "@/data/product-assets";

type ProductImageProps = {
	productId: number;
	style?: StyleProp<ImageStyle>;
};

export function ProductImage({ productId, style }: ProductImageProps) {
	return (
		<Image
			accessibilityIgnoresInvertColors
			resizeMode="contain"
			source={getProductAsset(productId)}
			style={style}
		/>
	);
}
