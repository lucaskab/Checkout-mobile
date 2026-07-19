import { Text, useWindowDimensions, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreShelf } from "@/@types/store";
import { useGameStore } from "@/stores/game-store";
import { Shelf } from "../shelf-item";

type ShelfGridProps = {
	onPressShelf: (shelf: StoreShelf) => void;
	shelves: StoreShelf[];
};

export function ShelfGrid({ onPressShelf, shelves }: ShelfGridProps) {
	const { width } = useWindowDimensions();
	const inventory = useGameStore((state) => state.inventory);
	const shelfStock = useGameStore((state) => state.shelfStock);
	const shelfSize = Math.min((width - 80) / 4, 92);
	const occupiedShelves = shelves.filter(
		(shelf) => !shelf.locked && (shelfStock[shelf.id] ?? 0) > 0,
	).length;

	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<View>
					<Text style={styles.title}>Prateleiras</Text>
					<Text style={styles.subtitle}>
						Toque em uma prateleira para reabastecer.
					</Text>
				</View>
				<View style={styles.occupancyBadge}>
					<Text style={styles.occupancyText}>
						{occupiedShelves}/{shelves.length} ocupadas
					</Text>
				</View>
			</View>
			<View style={styles.grid}>
				{shelves.map((shelf) => (
					<Shelf
						availableQuantity={
							shelf.productId ? (inventory[shelf.productId] ?? 0) : 0
						}
						key={shelf.id}
						onPress={onPressShelf}
						shelf={shelf}
						shelfQuantity={shelfStock[shelf.id] ?? 0}
						size={shelfSize}
					/>
				))}
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	card: {
		padding: theme.gap(1.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-0"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 3 },
		shadowOpacity: 0.08,
		shadowRadius: 8,
		elevation: 2,
	},
	header: {
		flexDirection: "row",
		alignItems: "flex-start",
		justifyContent: "space-between",
		gap: theme.gap(1),
	},
	title: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	subtitle: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 11,
	},
	occupancyBadge: {
		paddingHorizontal: theme.gap(0.875),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-50"],
	},
	occupancyText: {
		color: theme.colors["blue-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	grid: {
		flexDirection: "row",
		flexWrap: "wrap",
		gap: theme.gap(1),
		marginTop: theme.gap(1.5),
	},
}));
