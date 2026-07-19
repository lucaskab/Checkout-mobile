import { Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreTopSeller } from "@/@types/store";

type TopSellersCardProps = {
	items: StoreTopSeller[];
};

const medals = ["🥇", "🥈", "🥉"];

export function TopSellersCard({ items }: TopSellersCardProps) {
	const highestSold = items[0]?.sold ?? 1;

	return (
		<View style={styles.card}>
			<Text style={styles.title}>🏆 Mais vendidos hoje</Text>
			<View style={styles.list}>
				{items.map((item, index) => (
					<View key={item.id} style={styles.item}>
						<View style={[styles.rank, index === 0 && styles.firstRank]}>
							<Text style={styles.rankText}>{medals[index]}</Text>
						</View>
						<Text style={styles.itemEmoji}>{item.emoji}</Text>
						<View style={styles.itemCopy}>
							<View style={styles.itemHeader}>
								<Text style={styles.itemName}>{item.name}</Text>
								<Text style={styles.itemRevenue}>🪙 {item.revenue}</Text>
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
	title: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
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
		fontSize: 15,
	},
	itemEmoji: {
		fontSize: 21,
	},
	itemCopy: {
		flex: 1,
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
