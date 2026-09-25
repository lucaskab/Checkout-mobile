import { Image } from "expo-image";
import { ScrollView, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type {
	MarketExpansionCurrency,
	MarketExpansionId,
} from "@/@types/market-expansion";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { marketExpansionAssets } from "@/data/market-expansion-assets";
import { marketExpansions } from "@/data/market-expansions";
import { useGameStore } from "@/stores/game-store";

export function MarketExpansionsSheet() {
	const { closeBottomSheet } = useBottomSheet();
	const coins = useGameStore((state) => state.coins);
	const diamonds = useGameStore((state) => state.logistics.premiumCurrency);
	const level = useGameStore((state) => state.market.level);
	const unlockedIds = useGameStore((state) => state.unlockedMarketExpansionIds);
	const unlockMarketExpansion = useGameStore(
		(state) => state.unlockMarketExpansion,
	);

	function unlock(
		expansionId: MarketExpansionId,
		currency: MarketExpansionCurrency,
	) {
		unlockMarketExpansion(expansionId, currency);
	}

	return (
		<ScrollView contentContainerStyle={styles.content}>
			<View style={styles.header}>
				<View style={styles.headerIcon}>
					<GameIcon icon="construction" style={styles.headerIconImage} />
				</View>
				<View style={styles.headerCopy}>
					<Text style={styles.eyebrow}>CHECKOUT MARKET</Text>
					<Text style={styles.title}>Expansões</Text>
					<Text style={styles.description}>
						Desbloqueie novas alas e faça seu mercado crescer.
					</Text>
				</View>
			</View>

			<View style={styles.balanceRow}>
				<Text style={styles.balance}>🪙 {coins.toLocaleString("pt-BR")}</Text>
				<Text style={styles.balance}>
					💎 {diamonds.toLocaleString("pt-BR")}
				</Text>
				<Text style={styles.balance}>NÍVEL {level}</Text>
			</View>

			{marketExpansions.map((expansion) => {
				const unlocked = unlockedIds.includes(expansion.id);
				const levelLocked = level < expansion.requiredLevel;
				const hasCoins = coins >= expansion.coinCost;
				const hasDiamonds = diamonds >= expansion.diamondCost;

				return (
					<View key={expansion.id} style={styles.card}>
						<Image
							cachePolicy="memory-disk"
							contentFit="contain"
							source={marketExpansionAssets[expansion.id]}
							style={styles.image}
							transition={0}
						/>
						<View style={styles.cardCopy}>
							<View style={styles.cardTitleRow}>
								<Text style={styles.cardTitle}>{expansion.name}</Text>
								<Text
									style={[styles.status, unlocked && styles.statusUnlocked]}
								>
									{unlocked ? "LIBERADA" : `NÍVEL ${expansion.requiredLevel}`}
								</Text>
							</View>
							<Text style={styles.cardDescription}>
								{expansion.description}
							</Text>
							{unlocked ? (
								<Text style={styles.unlockedText}>
									Área pronta para o mercado.
								</Text>
							) : levelLocked ? (
								<Text style={styles.lockedText}>
									Alcance o nível {expansion.requiredLevel} para desbloquear.
								</Text>
							) : (
								<View style={styles.actions}>
									<GameButton
										disabled={!hasCoins}
										icon="coin"
										label={expansion.coinCost.toLocaleString("pt-BR")}
										onPress={() => unlock(expansion.id, "coins")}
										size="small"
										style={styles.actionButton}
										variant="coin"
									/>
									<GameButton
										disabled={!hasDiamonds}
										icon="diamond"
										label={expansion.diamondCost.toLocaleString("pt-BR")}
										onPress={() => unlock(expansion.id, "diamonds")}
										size="small"
										style={styles.actionButton}
										variant="gem"
									/>
								</View>
							)}
						</View>
					</View>
				);
			})}

			<GameButton
				fullWidth
				label="Concluir"
				onPress={closeBottomSheet}
				variant="secondary"
			/>
		</ScrollView>
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		gap: theme.gap(1),
		paddingHorizontal: theme.gap(1.5),
		paddingBottom: theme.gap(1),
	},
	header: { flexDirection: "row", alignItems: "center", gap: theme.gap(1) },
	headerIcon: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-100"],
	},
	headerIconImage: { width: theme.gap(3), height: theme.gap(3) },
	headerCopy: { flex: 1 },
	eyebrow: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1,
	},
	title: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 24,
		fontWeight: "800",
	},
	description: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		lineHeight: 16,
	},
	balanceRow: {
		flexDirection: "row",
		justifyContent: "space-between",
		padding: theme.gap(0.875),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	balance: {
		color: theme.colors["neutral-700"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 10,
		fontWeight: "800",
	},
	card: {
		flexDirection: "row",
		gap: theme.gap(1),
		padding: theme.gap(0.875),
		borderWidth: 2,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	image: { width: theme.gap(8), height: theme.gap(8) },
	cardCopy: { flex: 1, gap: theme.gap(0.375) },
	cardTitleRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
	},
	cardTitle: {
		flex: 1,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 14,
		fontWeight: "800",
	},
	status: {
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "800",
	},
	statusUnlocked: { color: theme.colors["green-600"] },
	cardDescription: {
		color: theme.colors["neutral-600"],
		fontSize: 10,
		lineHeight: 14,
	},
	actions: {
		flexDirection: "row",
		gap: theme.gap(0.5),
		marginTop: theme.gap(0.25),
	},
	actionButton: { flex: 1 },
	lockedText: {
		color: theme.colors["amber-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	unlockedText: {
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "700",
	},
}));
