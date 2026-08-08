import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";

const STRIPES = Array.from({ length: 12 }, (_, index) => index);

export function SupermarketAwning() {
	return (
		<View accessibilityElementsHidden style={styles.awning}>
			{STRIPES.map((stripe) => (
				<View
					key={stripe}
					style={stripe % 2 === 0 ? styles.blueStripe : styles.redStripe}
				/>
			))}
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	awning: {
		height: theme.gap(0.75),
		flexDirection: "row",
		overflow: "hidden",
	},
	blueStripe: {
		flex: 1,
		backgroundColor: theme.colors["blue-500"],
	},
	redStripe: {
		flex: 1,
		backgroundColor: theme.colors["red-500"],
	},
}));
