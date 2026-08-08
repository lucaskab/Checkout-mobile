import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { CurrencyPack } from "@/@types/currency-purchase";
import { GameButton, type GameButtonVariant } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";

type CurrencyPackCardProps = {
	canPurchase: boolean;
	isPurchasing: boolean;
	onPurchase: (pack: CurrencyPack) => void;
	pack: CurrencyPack;
	price: string;
};

export function CurrencyPackCard({
	canPurchase,
	isPurchasing,
	onPurchase,
	pack,
	price,
}: CurrencyPackCardProps) {
	const buttonVariant: GameButtonVariant =
		pack.category === "coins"
			? "coin"
			: pack.category === "diamonds"
				? "gem"
				: "primary";

	return (
		<View style={[styles.card, styles.cardCategory(pack.category)]}>
			<View style={styles.cardHeader}>
				<View style={[styles.visual, styles.visualCategory(pack.category)]}>
					<GameIcon
						icon={
							pack.category === "bundle"
								? "gift"
								: pack.category === "coins"
									? "coin"
									: "diamond"
						}
						style={styles.visualEmoji}
					/>
				</View>
				<View style={styles.titleCopy}>
					<Text style={styles.name}>{pack.name}</Text>
					<Text style={styles.badge}>{pack.badge}</Text>
				</View>
				<Text style={styles.price}>{price}</Text>
			</View>

			<View style={styles.rewardRow}>
				{pack.coins > 0 && (
					<View style={styles.rewardPill}>
						<GameIcon icon="coin" style={styles.rewardEmoji} />
						<Text style={styles.rewardValue}>
							{pack.coins.toLocaleString("pt-BR")}
						</Text>
					</View>
				)}
				{pack.diamonds > 0 && (
					<View style={[styles.rewardPill, styles.diamondRewardPill]}>
						<GameIcon icon="diamond" style={styles.rewardEmoji} />
						<Text style={styles.rewardValue}>
							{pack.diamonds.toLocaleString("pt-BR")}
						</Text>
					</View>
				)}
			</View>

			<GameButton
				disabled={!canPurchase || isPurchasing}
				fullWidth
				label={
					isPurchasing
						? "Processando..."
						: canPurchase
							? `Comprar · ${price}`
							: "Produto indisponível"
				}
				onPress={() => onPurchase(pack)}
				size="small"
				variant={buttonVariant}
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	card: {
		gap: theme.gap(1),
		marginHorizontal: theme.gap(1.5),
		marginBottom: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 2,
		borderBottomWidth: 5,
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	cardCategory: (category: CurrencyPack["category"]) => ({
		borderColor:
			category === "bundle"
				? theme.colors["blue-300"]
				: category === "coins"
					? theme.colors["amber-400"]
					: theme.colors["violet-400"],
		borderBottomColor:
			category === "bundle"
				? theme.colors["blue-600"]
				: category === "coins"
					? theme.colors["amber-600"]
					: theme.colors["violet-600"],
	}),
	cardHeader: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
	},
	visual: {
		width: theme.gap(5.5),
		height: theme.gap(5.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
	},
	visualCategory: (category: CurrencyPack["category"]) => ({
		backgroundColor:
			category === "bundle"
				? theme.colors["blue-100"]
				: category === "coins"
					? theme.colors["amber-100"]
					: theme.colors["violet-100"],
	}),
	visualEmoji: { width: 38, height: 38 },
	titleCopy: { flex: 1 },
	name: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	badge: {
		alignSelf: "flex-start",
		marginTop: 2,
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
	},
	price: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	rewardRow: {
		flexDirection: "row",
		gap: theme.gap(0.75),
	},
	rewardPill: {
		flex: 1,
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.5),
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.75),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-50"],
	},
	diamondRewardPill: { backgroundColor: theme.colors["violet-50"] },
	rewardEmoji: { width: 20, height: 20 },
	rewardValue: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
}));
