import { Pressable, Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreAlert } from "@/@types/store";

type AttentionCardProps = {
	alerts: StoreAlert[];
	onPressAlert: (alert: StoreAlert) => void;
};

export function AttentionCard({ alerts, onPressAlert }: AttentionCardProps) {
	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<Text style={styles.title}>⚠️ Requer atenção</Text>
			</View>
			<View style={styles.list}>
				{alerts.map((alert) => (
					<View
						key={alert.id}
						style={[styles.alert, alert.type === "low" && styles.lowAlert]}
					>
						<Text style={styles.alertEmoji}>{alert.emoji}</Text>
						<View style={styles.alertCopy}>
							<Text style={styles.alertName}>{alert.name}</Text>
							<Text style={styles.alertIssue}>{alert.issue}</Text>
						</View>
						<Pressable
							onPress={() => onPressAlert(alert)}
							style={[
								styles.actionButton,
								alert.type === "low" && styles.lowActionButton,
							]}
						>
							<Text style={styles.actionButtonText}>{alert.actionLabel}</Text>
						</Pressable>
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
		borderColor: theme.colors["red-200"],
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
		alignItems: "center",
	},
	title: {
		color: theme.colors["red-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	list: {
		gap: theme.gap(0.875),
		marginTop: theme.gap(1.25),
	},
	alert: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-50"],
	},
	lowAlert: {
		borderColor: theme.colors["red-200"],
		backgroundColor: theme.colors["red-50"],
	},
	alertEmoji: {
		fontSize: 21,
	},
	alertCopy: {
		flex: 1,
	},
	alertName: {
		color: theme.colors["neutral-800"],
		fontSize: 12,
		fontWeight: "700",
	},
	alertIssue: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-600"],
		fontSize: 11,
	},
	actionButton: {
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(0.75),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-500"],
	},
	lowActionButton: {
		backgroundColor: theme.colors["red-500"],
	},
	actionButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: 11,
		fontWeight: "700",
	},
}));
