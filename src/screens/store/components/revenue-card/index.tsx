import { Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreQuickStat } from "@/@types/store";

type RevenueCardProps = {
	dailyGoal: number;
	quickStats: StoreQuickStat[];
	revenue: number;
};

export function RevenueCard({
	dailyGoal,
	quickStats,
	revenue,
}: RevenueCardProps) {
	const progress = Math.min(Math.round((revenue / dailyGoal) * 100), 100);

	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<View>
					<Text style={styles.title}>💰 Faturamento hoje</Text>
					<Text style={styles.subtitle}>
						Meta diária: 🪙 {dailyGoal.toLocaleString("pt-BR")}
					</Text>
				</View>
				<View style={styles.revenueCopy}>
					<Text style={styles.revenue}>
						🪙 {revenue.toLocaleString("pt-BR")}
					</Text>
					<Text style={styles.progressLabel}>{progress}% da meta</Text>
				</View>
			</View>
			<View style={styles.progressTrack}>
				<View style={[styles.progressFill, { width: `${progress}%` }]} />
			</View>
			<View style={styles.stats}>
				{quickStats.map((stat) => (
					<View key={stat.label} style={styles.stat}>
						<Text style={styles.statValue}>
							{stat.icon} {stat.value}
						</Text>
						<Text style={styles.statLabel}>{stat.label}</Text>
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
	header: {
		flexDirection: "row",
		alignItems: "flex-start",
		justifyContent: "space-between",
	},
	title: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	subtitle: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 11,
	},
	revenueCopy: {
		alignItems: "flex-end",
	},
	revenue: {
		color: theme.colors["amber-600"],
		fontSize: theme.fonts.size.large + 4,
		fontWeight: "700",
	},
	progressLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "700",
	},
	progressTrack: {
		height: theme.gap(1.25),
		overflow: "hidden",
		marginTop: theme.gap(1.5),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-100"],
	},
	progressFill: {
		height: "100%",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-500"],
	},
	stats: {
		flexDirection: "row",
		gap: theme.gap(1),
		marginTop: theme.gap(1.5),
	},
	stat: {
		flex: 1,
		alignItems: "center",
		paddingVertical: theme.gap(1),
		paddingHorizontal: theme.gap(0.5),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-50"],
	},
	statValue: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	statLabel: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 10,
		textAlign: "center",
	},
}));
