import { Pressable, Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreShelf } from "@/@types/store";

export const ShelfItem = ({
	availableQuantity,
	capacity,
	onPress,
	shelf,
	shelfQuantity,
	size,
}: {
	availableQuantity: number;
	capacity: number;
	onPress: (shelf: StoreShelf) => void;
	shelf: StoreShelf;
	shelfQuantity: number;
	size: number;
}) => {
	return (
		<Pressable
			disabled={shelf.locked}
			onPress={() => onPress(shelf)}
			style={[
				styles.shelf,
				{ width: size, height: size },
				shelf.locked && styles.lockedShelf,
				shelfQuantity === 0 && !shelf.locked && styles.emptyShelf,
			]}
		>
			{!shelf.locked && (
				<View style={styles.quantityBadge}>
					<Text style={styles.quantityText}>
						x{shelfQuantity}/{capacity}
					</Text>
				</View>
			)}
			<Text style={styles.shelfProduct}>
				{shelf.locked ? "🏪" : shelf.product}
			</Text>
			{!shelf.locked && (
				<Text style={styles.shelfStatus}>
					{availableQuantity > 0
						? `${availableQuantity} no estoque`
						: "Estoque vazio"}
				</Text>
			)}
		</Pressable>
	);
};

const styles = StyleSheet.create((theme) => ({
	shelf: {
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 3,
		borderStyle: "dashed",
		borderColor: theme.colors.gameShelfBorder,
		borderRadius: 21,
		backgroundColor: theme.colors.gameShelf,
	},
	lockedShelf: {
		borderColor: theme.colors.gameBorder,
		backgroundColor: theme.colors.gameLockedShelf,
	},
	emptyShelf: {
		borderColor: theme.colors["red-400"],
		backgroundColor: theme.colors["red-50"],
	},
	quantityBadge: {
		position: "absolute",
		top: theme.gap(0.5),
		right: theme.gap(0.5),
		minWidth: theme.gap(2.5),
		alignItems: "center",
		paddingHorizontal: theme.gap(0.5),
		paddingVertical: 2,
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-500"],
	},
	quantityText: {
		color: theme.colors["neutral-0"],
		fontSize: 10,
		fontWeight: "700",
	},
	shelfProduct: {
		fontSize: 30,
	},
	shelfStatus: {
		position: "absolute",
		bottom: theme.gap(0.5),
		color: theme.colors["neutral-600"],
		fontSize: 8,
		fontWeight: "700",
	},
}));
