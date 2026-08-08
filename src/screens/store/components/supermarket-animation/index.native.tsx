import { useEffect } from "react";
import { View } from "react-native";
import Animated, {
	Easing,
	useAnimatedStyle,
	useSharedValue,
	withDelay,
	withRepeat,
	withSequence,
	withTiming,
} from "react-native-reanimated";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";
import { ProductImage } from "@/components/product-image";

type SupermarketAnimationProps = {
	isOpen: boolean;
};

/** Tiny cozy scene: a shopper strolls past the storefront window. */
export function SupermarketAnimation({ isOpen }: SupermarketAnimationProps) {
	const walk = useSharedValue(0);
	const bob = useSharedValue(0);

	useEffect(() => {
		const duration = isOpen ? 5200 : 11000;
		walk.value = 0;
		walk.value = withRepeat(
			withTiming(1, { duration, easing: Easing.linear }),
			-1,
			false,
		);
		bob.value = withRepeat(
			withSequence(
				withTiming(-2, { duration: 320, easing: Easing.inOut(Easing.quad) }),
				withTiming(0, { duration: 320, easing: Easing.inOut(Easing.quad) }),
			),
			-1,
			false,
		);
	}, [isOpen, walk, bob]);

	const shopperStyle = useAnimatedStyle(() => ({
		transform: [
			{ translateX: -40 + walk.value * 320 },
			{ translateY: bob.value },
		],
	}));

	return (
		<View style={styles.scene}>
			<View style={styles.sky} />
			<View style={styles.stripeRow}>
				<Awning />
			</View>
			<View style={styles.windowRow}>
				<Window productId={2} />
				<Window productId={9} />
				<Window productId={6} />
				<Window productId={1} />
			</View>
			<View style={styles.shopper}>
				<Animated.View style={shopperStyle}>
					<GameIcon
						icon={isOpen ? "customers" : "broom"}
						style={styles.shopperEmoji}
					/>
				</Animated.View>
			</View>
			<View style={styles.sidewalk} />
			<Sparkle delay={0} left="18%" active={isOpen} />
			<Sparkle delay={900} left="62%" active={isOpen} />
			<Sparkle delay={1800} left="84%" active={isOpen} />
		</View>
	);
}

const AWNING_STRIPES = Array.from({ length: 10 }, (_, index) => index);

function Awning() {
	return (
		<View style={styles.awning}>
			{AWNING_STRIPES.map((stripe) => (
				<View
					key={stripe}
					style={stripe % 2 === 0 ? styles.awningRed : styles.awningCream}
				/>
			))}
		</View>
	);
}

function Window({ productId }: { productId: number }) {
	return (
		<View style={styles.window}>
			<ProductImage productId={productId} style={styles.windowEmoji} />
		</View>
	);
}

function Sparkle({
	active,
	delay,
	left,
}: {
	active: boolean;
	delay: number;
	left: `${number}%`;
}) {
	const glow = useSharedValue(0);

	useEffect(() => {
		if (!active) {
			glow.value = withTiming(0, { duration: 300 });
			return;
		}
		glow.value = withDelay(
			delay,
			withRepeat(
				withSequence(
					withTiming(1, { duration: 700 }),
					withTiming(0, { duration: 700 }),
				),
				-1,
				false,
			),
		);
	}, [active, delay, glow]);

	const animatedStyle = useAnimatedStyle(() => ({ opacity: glow.value }));

	return (
		<View style={[styles.sparkle, { left }]}>
			<Animated.View style={animatedStyle}>
				<GameIcon icon="light" style={styles.sparkleIcon} />
			</Animated.View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	scene: {
		position: "relative",
		height: 76,
		overflow: "hidden",
	},
	sky: {
		...StyleSheet.absoluteFillObject,
		backgroundColor: theme.colors["blue-50"],
	},
	stripeRow: {
		height: theme.gap(1.5),
	},
	awning: {
		flex: 1,
		flexDirection: "row",
		overflow: "hidden",
	},
	awningRed: {
		flex: 1,
		backgroundColor: theme.colors["red-500"],
	},
	awningCream: {
		flex: 1,
		backgroundColor: theme.colors["neutral-50"],
	},
	windowRow: {
		flex: 1,
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-around",
		paddingHorizontal: theme.gap(1),
	},
	window: {
		width: theme.gap(4),
		height: theme.gap(4),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 2,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-0"],
	},
	windowEmoji: {
		width: 30,
		height: 30,
	},
	shopper: {
		position: "absolute",
		bottom: theme.gap(0.5),
	},
	shopperEmoji: {
		width: 36,
		height: 36,
	},
	sidewalk: {
		position: "absolute",
		right: 0,
		bottom: 0,
		left: 0,
		height: theme.gap(0.75),
		backgroundColor: theme.colors["neutral-200"],
	},
	sparkle: {
		position: "absolute",
		top: theme.gap(2),
	},
	sparkleIcon: {
		width: 18,
		height: 18,
	},
}));
