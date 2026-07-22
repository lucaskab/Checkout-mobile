import { Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { ItemDefinition } from "@/@types/item";

export const LockedProductCard = ({
	playerLevel,
	product,
}: {
	playerLevel: number;
	product: ItemDefinition;
}) => {
	const levelsLeft = product.unlockLevel - playerLevel;
	const progress = Math.min(
		100,
		Math.round((playerLevel / product.unlockLevel) * 100),
	);

	return (
		<View style={styles.lockedCard}>
			<View style={styles.cardTopRow}>
				<View style={styles.productIdentity}>
					<View style={styles.lockedVisual}>
						<Text style={styles.lockedEmoji}>{product.emoji}</Text>
						<Text style={styles.lockIcon}>🔒</Text>
					</View>
					<View style={styles.productCopy}>
						<Text numberOfLines={1} style={styles.lockedName}>
							{product.name}
						</Text>
						<Text style={styles.lockedCategory}>{product.category}</Text>
					</View>
				</View>
				<View style={styles.unlockLevelChip}>
					<Text style={styles.unlockLevelText}>Nv {product.unlockLevel}</Text>
				</View>
			</View>
			<View style={styles.lockedRewards}>
				<Text style={styles.lockedRewardText}>
					🪙 {product.sellingPrice} por venda
				</Text>
				<Text style={styles.lockedRewardText}>+{product.xpPerSale} XP</Text>
			</View>
			<View style={styles.unlockProgressTrack}>
				<View style={[styles.unlockProgressFill, { width: `${progress}%` }]} />
			</View>
			<Text style={styles.unlockProgressText}>
				{levelsLeft > 0
					? `Faltam ${levelsLeft} nível${levelsLeft === 1 ? "" : "is"} para desbloquear`
					: "Pronto para desbloquear"}
			</Text>
		</View>
	);
};

const styles = StyleSheet.create((theme) => ({
	lockedCard: {
		marginTop: theme.gap(1),
		padding: theme.gap(1.5),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-100"],
	},
	cardTopRow: {
		flexDirection: "row",
		alignItems: "flex-start",
		justifyContent: "space-between",
	},
	productIdentity: {
		flex: 1,
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		paddingRight: theme.gap(1),
	},
	productCopy: {
		flex: 1,
	},
	lockedVisual: {
		position: "relative",
		width: theme.gap(5.5),
		height: theme.gap(5.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-150"],
	},
	lockedEmoji: {
		opacity: 0.35,
		fontSize: 25,
	},
	lockIcon: {
		position: "absolute",
		fontSize: 13,
	},
	lockedName: {
		color: theme.colors["neutral-600"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	lockedCategory: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	unlockLevelChip: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.375),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-150"],
	},
	unlockLevelText: {
		color: theme.colors["neutral-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	lockedRewards: {
		flexDirection: "row",
		gap: theme.gap(1.5),
		marginTop: theme.gap(1.25),
	},
	lockedRewardText: {
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	unlockProgressTrack: {
		height: theme.gap(0.625),
		overflow: "hidden",
		marginTop: theme.gap(1.25),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-200"],
	},
	unlockProgressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-400"],
	},
	unlockProgressText: {
		marginTop: theme.gap(0.75),
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "600",
	},
}));
