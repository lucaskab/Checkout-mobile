import { LegendList } from "@legendapp/list/react-native";
import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { shelves } from "@/data/market-products";
import {
	getNextShelfSlotUpgrade,
	getNextShelfUnlockUpgrade,
} from "@/data/shelf-capacity";
import {
	getShelfSlotCount,
	getShelfSlotIds,
	getUnlockedPhysicalShelfCount,
	resolveShelfSlotCounts,
} from "@/data/shelf-slots";
import { useGameStore } from "@/stores/game-store";
import { ShelfManagementScreen } from ".";

export function ShelfListScreen() {
	const state = useGameStore();
	const { openBottomSheet, closeBottomSheet } = useBottomSheet();
	const shelfSlotCounts = resolveShelfSlotCounts(
		state.shelfSlotCounts,
		state.unlockedShelfSlots,
	);
	const unlockedShelves = getUnlockedPhysicalShelfCount(shelfSlotCounts);
	const nextShelfUpgrade = getNextShelfUnlockUpgrade(unlockedShelves);
	return (
		<LegendList
			recycleItems={false}
			data={shelves.slice(0, unlockedShelves)}
			extraData={state}
			keyExtractor={(shelf) => shelf.id}
			contentContainerStyle={styles.list}
			ListHeaderComponent={
				<Text style={styles.subtitle}>
					Seu mix de produtos, do seu jeito. Cada prateleira começa com quatro
					espaços.
				</Text>
			}
			ListFooterComponent={
				nextShelfUpgrade ? (
					<GameButton
						fullWidth
						label={`Nova prateleira · Nv. ${nextShelfUpgrade.playerLevel} · ${nextShelfUpgrade.coinCost} moedas`}
						variant="coin"
						disabled={
							state.market.level < nextShelfUpgrade.playerLevel ||
							state.coins < nextShelfUpgrade.coinCost
						}
						onPress={() => state.unlockNextShelf()}
					/>
				) : null
			}
			renderItem={({ item }) => {
				const slotCount = getShelfSlotCount(item.id, shelfSlotCounts);
				const slotUpgrade = getNextShelfSlotUpgrade(slotCount);

				return (
					<View style={styles.card}>
						<Text style={styles.title}>{item.name}</Text>
						<View style={styles.row}>
							{getShelfSlotIds(item.id, slotCount).map((slotId) => {
								const productId = state.shelfAssignments[slotId];

								return (
									<View key={slotId} style={styles.slot}>
										{productId ? (
											<ProductImage
												productId={productId}
												style={styles.image}
											/>
										) : (
											<GameIcon icon="basket" style={styles.image} />
										)}
										<Text style={styles.subtitle}>
											{productId
												? `${state.shelfStock[slotId] ?? 0} unid.`
												: "Livre"}
										</Text>
									</View>
								);
							})}
						</View>
						<GameButton
							fullWidth
							label="Gerenciar prateleira"
							onPress={() =>
								openBottomSheet(
									<ShelfManagementScreen
										key={item.id}
										shelfId={item.id}
										onClose={closeBottomSheet}
									/>,
								)
							}
						/>
						{slotUpgrade && (
							<GameButton
								fullWidth
								label={`Expandir slots · Nv. ${slotUpgrade.playerLevel} · ${slotUpgrade.coinCost.toLocaleString("pt-BR")} moedas`}
								variant="coin"
								disabled={
									state.market.level < slotUpgrade.playerLevel ||
									state.coins < slotUpgrade.coinCost
								}
								onPress={() => state.expandShelfSlots(item.id)}
							/>
						)}
					</View>
				);
			}}
		/>
	);
}
const styles = StyleSheet.create((theme) => ({
	list: { padding: 16, gap: 16, paddingBottom: 32 },
	card: {
		padding: 16,
		gap: 14,
		borderRadius: 22,
		backgroundColor: theme.colors["neutral-0"],
		borderColor: theme.colors.gameBorder,
		borderWidth: 1.5,
	},
	title: {
		fontFamily: theme.fonts.family.headline,
		fontSize: 23,
		color: theme.colors.gameText,
	},
	subtitle: { fontSize: 13, color: theme.colors.gameMuted },
	row: { flexDirection: "row", gap: 8 },
	slot: {
		flex: 1,
		alignItems: "center",
		paddingVertical: 12,
		gap: 6,
		borderRadius: 14,
		backgroundColor: theme.colors["blue-50"],
	},
	image: { width: 42, height: 42 },
}));
