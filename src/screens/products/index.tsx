import { Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { getExperienceToNextLevel } from "@/services/progression";
import { useGameStore } from "@/stores/game-store";
import { ProductList } from "./components/product-list";

export function ProductsScreen() {
	const coins = useGameStore((state) => state.coins);
	const inventory = useGameStore((state) => state.inventory);
	const premiumCurrency = useGameStore(
		(state) => state.logistics.premiumCurrency,
	);
	const market = useGameStore((state) => state.market);
	const experienceToNextLevel = getExperienceToNextLevel(market.level);
	const experienceProgress = Math.min(
		100,
		Math.round((market.experience / experienceToNextLevel) * 100),
	);

	return (
		<View style={styles.screen}>
			<View style={styles.header}>
				<View style={styles.headerTopRow}>
					<View>
						<Text style={styles.eyebrow}>Nível {market.level}</Text>
						<Text style={styles.title}>Meus produtos</Text>
					</View>
					<View style={styles.currencyRow}>
						<View style={styles.gemChip}>
							<Text style={styles.gemChipText}>💎 {premiumCurrency}</Text>
						</View>
						<View style={styles.coinChip}>
							<Text style={styles.coinChipText}>
								🪙 {coins.toLocaleString("pt-BR")}
							</Text>
						</View>
					</View>
				</View>
				<View style={styles.experienceRow}>
					<View style={styles.experienceTrack}>
						<View
							style={[
								styles.experienceFill,
								{ width: `${experienceProgress}%` },
							]}
						/>
					</View>
					<Text style={styles.experienceText}>
						{market.experience} / {experienceToNextLevel} XP
					</Text>
				</View>
			</View>
			<ProductList
				inventory={inventory}
				level={market.level}
				unlockedProductIds={market.unlockedProductIds}
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	screen: {
		flex: 1,
		backgroundColor: theme.colors["neutral-50"],
	},
	header: {
		paddingHorizontal: theme.gap(1.75),
		paddingBottom: theme.gap(1.5),
		borderBottomWidth: 1,
		borderBottomColor: theme.colors["neutral-150"],
		backgroundColor: theme.colors["neutral-0"],
	},
	headerTopRow: {
		flexDirection: "row",
		alignItems: "flex-start",
		justifyContent: "space-between",
	},
	eyebrow: {
		color: theme.colors["blue-600"],
		fontSize: 10,
		fontWeight: "700",
		textTransform: "uppercase",
	},
	title: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large + 4,
		fontWeight: "700",
	},
	currencyRow: {
		flexDirection: "row",
		gap: theme.gap(0.5),
	},
	gemChip: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.625),
		borderWidth: 1,
		borderColor: theme.colors["violet-100"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["violet-50"],
	},
	gemChipText: {
		color: theme.colors["violet-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	coinChip: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.625),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["amber-50"],
	},
	coinChipText: {
		color: theme.colors["amber-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	experienceRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginTop: theme.gap(1.5),
	},
	experienceTrack: {
		flex: 1,
		height: theme.gap(0.75),
		overflow: "hidden",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-150"],
	},
	experienceFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["amber-400"],
	},
	experienceText: {
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "700",
	},
}));
