import { useWindowDimensions, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreShelf } from "@/@types/store";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { itemCatalog } from "@/data/market-products";
import {
	getNextShelfSlotUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import { useGameStore } from "@/stores/game-store";
import { ShelfItem } from "../shelf-item";

type ShelfGridProps = {
	onPressShelf: (shelf: StoreShelf) => void;
	shelves: StoreShelf[];
};

const SHELF_COLUMNS = 4;

export function ShelfGrid({ onPressShelf, shelves }: ShelfGridProps) {
	const { width } = useWindowDimensions();
	const inventory = useGameStore((state) => state.inventory);
	const shelfAssignments = useGameStore((state) => state.shelfAssignments);
	const shelfStock = useGameStore((state) => state.shelfStock);
	const shelfPrices = useGameStore((state) => state.shelfPrices);
	const unlockedShelfSlots = useGameStore((state) => state.unlockedShelfSlots);
	const shelfUpgradeLevels = useGameStore((state) => state.shelfUpgradeLevels);
	const shelfItemSize = Math.min((width - 96) / SHELF_COLUMNS, 84);
	const unlockedShelves = shelves.slice(0, unlockedShelfSlots).map((shelf) => {
		const product = itemCatalog.find(
			(item) => item.id === shelfAssignments[shelf.id],
		);

		return {
			...shelf,
			name: product?.name ?? shelf.name,
			productId: product?.id,
		};
	});
	const nextSlotUpgrade = getNextShelfSlotUpgrade(unlockedShelfSlots);
	const visibleShelves: StoreShelf[] = [
		...unlockedShelves,
		...(nextSlotUpgrade
			? [
					{
						id: "next-shelf-slot",
						locked: true,
						nextSlotUpgrade,
					},
				]
			: []),
	];
	const occupiedShelves = unlockedShelves.filter((shelf) =>
		Boolean(shelf.productId),
	).length;

	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<View style={styles.headerCopy}>
					<View style={styles.titleRow}>
						<GameIcon icon="shelf" style={styles.titleIcon} />
						<Text style={styles.title}>Minhas Gôndolas</Text>
					</View>
					<Text style={styles.subtitle}>
						Toque numa vaga para abastecer ou trocar o produto.
					</Text>
				</View>
				<View style={styles.occupancyBadge}>
					<Text style={styles.occupancyText}>
						{occupiedShelves}/{unlockedShelves.length}
					</Text>
				</View>
			</View>
			<View style={styles.unit}>
				<View style={styles.grid}>
					{visibleShelves.map((shelf) => (
						<ShelfItem
							availableQuantity={
								shelf.productId ? (inventory[shelf.productId] ?? 0) : 0
							}
							capacity={getShelfCapacity(shelfUpgradeLevels[shelf.id])}
							key={shelf.id}
							onPress={onPressShelf}
							price={shelfPrices[shelf.id]}
							shelf={shelf}
							shelfQuantity={shelfStock[shelf.id] ?? 0}
							size={shelfItemSize}
						/>
					))}
				</View>
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	card: {
		padding: theme.gap(1.5),
		borderWidth: 3,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-100"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 3 },
		shadowOpacity: 0.12,
		shadowRadius: 8,
		elevation: 3,
	},
	header: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(1),
	},
	headerCopy: {
		flex: 1,
	},
	title: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "800",
	},
	titleRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
	},
	titleIcon: { width: 24, height: 24 },
	subtitle: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	occupancyBadge: {
		minWidth: theme.gap(5),
		alignItems: "center",
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.5),
		borderWidth: 2,
		borderColor: theme.colors["green-500"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["green-50"],
	},
	occupancyText: {
		color: theme.colors["green-600"],
		fontSize: 12,
		fontWeight: "800",
	},
	unit: {
		marginTop: theme.gap(1.25),
		padding: theme.gap(1),
		borderWidth: 2,
		borderColor: theme.colors.gameShelfBorder,
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["neutral-200"],
	},
	grid: {
		flexDirection: "row",
		flexWrap: "wrap",
		columnGap: theme.gap(0.75),
	},
}));
