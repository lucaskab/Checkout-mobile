import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreTopSeller } from "@/@types/store";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";

type TopSellersCardProps = {
	items: StoreTopSeller[];
};

export function TopSellersCard({ items }: TopSellersCardProps) {
	const highestSold = items[0]?.sold ?? 1;

	return (
		<View style={styles.card}>
			<View style={styles.titleRow}>
				<GameIcon icon="trophy" style={styles.titleIcon} />
				<Text style={styles.title}>Mais vendidos hoje</Text>
			</View>
			<View style={styles.list}>
				{items.map((item, index) => (
					<View key={item.id} style={styles.item}>
						<View style={[styles.rank, index === 0 && styles.firstRank]}>
							<GameIcon icon="medal" style={styles.rankText} />
						</View>
						<ProductImage
							productId={item.productId ?? Number(item.id)}
							style={styles.itemImage}
						/>
						<View style={styles.itemCopy}>
							<View style={styles.itemHeader}>
								<Text style={styles.itemName}>{item.name}</Text>
								<View style={styles.revenueRow}>
									<GameIcon icon="coin" style={styles.revenueIcon} />
									<Text style={styles.itemRevenue}>{item.revenue}</Text>
								</View>
							</View>
							<View style={styles.progressTrack}>
								<View
									style={[
										styles.progressFill,
										index === 0 && styles.firstProgressFill,
										{ width: `${(item.sold / highestSold) * 100}%` },
									]}
								/>
							</View>
							<Text style={styles.unitsSold}>
								{item.sold} unidades vendidas
							</Text>
						</View>
					</View>
				))}
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	card: {
		padding: theme.gap(2),
		borderWidth: 2,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-0"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 3 },
		shadowOpacity: 0.08,
		shadowRadius: 8,
		elevation: 2,
	},
	title: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	titleRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
	},
	titleIcon: {
		width: 22,
		height: 22,
	},
	list: {
		gap: theme.gap(1.25),
		marginTop: theme.gap(1.5),
	},
	item: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
	},
	rank: {
		width: theme.gap(3.5),
		height: theme.gap(3.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	firstRank: {
		backgroundColor: theme.colors["amber-100"],
	},
	rankText: {
		width: 24,
		height: 24,
	},
	itemImage: {
		width: theme.gap(4.5),
		height: theme.gap(4.5),
	},
	itemCopy: {
		flex: 1,
	},
	revenueRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.2),
	},
	revenueIcon: {
		width: 16,
		height: 16,
	},
	itemHeader: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	itemName: {
		color: theme.colors["neutral-800"],
		fontSize: 12,
		fontWeight: "700",
	},
	itemRevenue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["amber-600"],
		fontSize: 12,
		fontWeight: "700",
	},
	progressTrack: {
		height: theme.gap(0.625),
		overflow: "hidden",
		marginTop: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	progressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-500"],
	},
	firstProgressFill: {
		backgroundColor: theme.colors["amber-400"],
	},
	unitsSold: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 10,
	},
}));
