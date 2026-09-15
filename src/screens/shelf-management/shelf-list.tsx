import { LegendList } from "@legendapp/list/react-native";
import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { shelves } from "@/data/market-products";
import { getShelfSlotIds } from "@/data/shelf-slots";
import { getNextShelfSlotUpgrade } from "@/data/shelf-capacity";
import { useGameStore } from "@/stores/game-store";
import { ShelfManagementScreen } from ".";

export function ShelfListScreen() {
	const state = useGameStore();
	const { openBottomSheet, closeBottomSheet } = useBottomSheet();
	const upgrade = getNextShelfSlotUpgrade(state.unlockedShelfSlots);
	return (
		<LegendList
			recycleItems={false}
			data={shelves.slice(0, state.unlockedShelfSlots)}
			keyExtractor={(shelf) => shelf.id}
			contentContainerStyle={styles.list}
			ListHeaderComponent={
				<Text style={styles.subtitle}>
					Seu mix de produtos, do seu jeito. Cada prateleira tem quatro espaços.
				</Text>
			}
			ListFooterComponent={
				upgrade ? (
					<GameButton
						fullWidth
						label={`Nova prateleira · Nv. ${upgrade.playerLevel} · ${upgrade.coinCost} moedas`}
						variant="coin"
						disabled={
							state.market.level < upgrade.playerLevel ||
							state.coins < upgrade.coinCost
						}
						onPress={() => state.unlockNextShelfSlot()}
					/>
				) : null
			}
			renderItem={({ item }) => (
				<View style={styles.card}>
					<Text style={styles.title}>{item.name}</Text>
					<View style={styles.row}>
						{getShelfSlotIds(item.id).map((slotId) => (
							<View key={slotId} style={styles.slot}>
								{state.shelfAssignments[slotId] ? (
									<ProductImage
										productId={state.shelfAssignments[slotId]!}
										style={styles.image}
									/>
								) : (
									<GameIcon icon="basket" style={styles.image} />
								)}
								<Text style={styles.subtitle}>
									{state.shelfAssignments[slotId]
										? `${state.shelfStock[slotId] ?? 0} unid.`
										: "Livre"}
								</Text>
							</View>
						))}
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
				</View>
			)}
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
