import { useWindowDimensions, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreShelf } from "@/@types/store";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { itemCatalog } from "@/data/market-products";
import {
	getNextShelfUnlockUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import {
	getShelfSlotCount,
	getShelfSlotIds,
	getUnlockedPhysicalShelfCount,
	resolveShelfSlotCounts,
} from "@/data/shelf-slots";
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
	const shelfSlotCounts = useGameStore((state) => state.shelfSlotCounts);
	const unlockedShelfSlots = useGameStore((state) => state.unlockedShelfSlots);
	const shelfUpgradeLevels = useGameStore((state) => state.shelfUpgradeLevels);
	const shelfItemSize = Math.min((width - 96) / SHELF_COLUMNS, 84);
	const resolvedShelfSlotCounts = resolveShelfSlotCounts(
		shelfSlotCounts,
		unlockedShelfSlots,
	);
	const unlockedShelves = shelves.slice(
		0,
		getUnlockedPhysicalShelfCount(resolvedShelfSlotCounts),
	);
	const nextShelfUpgrade = getNextShelfUnlockUpgrade(unlockedShelves.length);
	const occupiedShelves = unlockedShelves.filter((shelf) =>
		getShelfSlotIds(
			shelf.id,
			getShelfSlotCount(shelf.id, resolvedShelfSlotCounts),
		).some((slotId) => shelfAssignments[slotId]),
	).length;

	function renderSlot(shelf: StoreShelf, slotId: string) {
		const product = itemCatalog.find(
			(item) => item.id === shelfAssignments[slotId],
		);
		const slot: StoreShelf = {
			...shelf,
			id: slotId,
			productId: product?.id,
		};

		return (
			<ShelfItem
				availableQuantity={product ? (inventory[product.id] ?? 0) : 0}
				capacity={getShelfCapacity(shelfUpgradeLevels[shelf.id])}
				key={slotId}
				onPress={() => onPressShelf(shelf)}
				price={shelfPrices[slotId] ?? product?.sellingPrice}
				shelf={slot}
				shelfQuantity={shelfStock[slotId] ?? 0}
				size={shelfItemSize}
			/>
		);
	}

	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<View style={styles.headerCopy}>
					<View style={styles.titleRow}>
						<GameIcon icon="shelf" style={styles.titleIcon} />
						<Text style={styles.title}>Minhas Gôndolas</Text>
					</View>
					<Text style={styles.subtitle}>
						Cada prateleira começa com 4 espaços. Toque para gerenciar.
					</Text>
				</View>
				<View style={styles.occupancyBadge}>
					<Text style={styles.occupancyText}>
						{occupiedShelves}/{unlockedShelves.length}
					</Text>
				</View>
			</View>
			<View style={styles.unit}>
				{unlockedShelves.map((shelf) => (
					<View key={shelf.id} style={styles.shelfSection}>
						<Text style={styles.shelfTitle}>{shelf.name}</Text>
						<View style={styles.grid}>
							{getShelfSlotIds(
								shelf.id,
								getShelfSlotCount(shelf.id, resolvedShelfSlotCounts),
							).map((slotId) => renderSlot(shelf, slotId))}
						</View>
					</View>
				))}
				{nextShelfUpgrade && (
					<View style={styles.nextSlot}>
						<ShelfItem
							availableQuantity={0}
							capacity={0}
							key="next-shelf-slot"
							onPress={onPressShelf}
							shelf={{
								id: "next-shelf-slot",
								locked: true,
								nextShelfUpgrade,
							}}
							shelfQuantity={0}
							size={shelfItemSize}
						/>
					</View>
				)}
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
	shelfSection: { gap: theme.gap(0.375) },
	shelfTitle: {
		color: theme.colors["neutral-600"],
		fontSize: 10,
		fontWeight: "800",
	},
	grid: {
		flexDirection: "row",
		flexWrap: "wrap",
		columnGap: theme.gap(0.75),
	},
	nextSlot: { marginTop: theme.gap(0.75) },
}));
