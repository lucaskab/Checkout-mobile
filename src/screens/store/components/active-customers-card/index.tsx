import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreActiveCustomer } from "@/@types/store";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";

type ActiveCustomersCardProps = {
	customers: StoreActiveCustomer[];
};

export function ActiveCustomersCard({ customers }: ActiveCustomersCardProps) {
	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<View style={styles.titleRow}>
					<GameIcon icon="customers" style={styles.titleIcon} />
					<Text style={styles.title}>Clientes na loja</Text>
				</View>
				<View style={styles.countBadge}>
					<Text style={styles.countBadgeText}>{customers.length} agora</Text>
				</View>
			</View>
			<View style={styles.list}>
				{customers.length === 0 && (
					<Text style={styles.emptyState}>
						Abra o mercado para receber os primeiros clientes.
					</Text>
				)}
				{customers.map((customer) => (
					<View key={customer.id} style={styles.customer}>
						<GameIcon icon="customers" style={styles.customerEmoji} />
						<View style={styles.customerCopy}>
							<Text style={styles.customerName}>{customer.name}</Text>
							<Text numberOfLines={1} style={styles.customerItem}>
								{customer.item}
							</Text>
						</View>
						<View style={styles.customerValue}>
							<View style={styles.spentRow}>
								<GameIcon icon="coin" style={styles.spentIcon} />
								<Text style={styles.spent}>{customer.spent}</Text>
							</View>
							<Text style={[styles.status, statusStyles[customer.status]]}>
								{customer.status}
							</Text>
							{typeof customer.satisfaction === "number" && (
								<Text
									style={[
										styles.satisfaction,
										customer.satisfaction >= 60
											? styles.happySatisfaction
											: styles.lowSatisfaction,
									]}
								>
									{customer.satisfaction}% satisfação
								</Text>
							)}
						</View>
					</View>
				))}
			</View>
		</View>
	);
}

const statusStyles = StyleSheet.create((theme) => ({
	pagou: { color: theme.colors["green-600"] },
	"saiu sem comprar": { color: theme.colors["neutral-500"] },
}));

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
	header: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
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
	title: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	countBadge: {
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(0.4),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-500"],
	},
	countBadgeText: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-0"],
		fontSize: 11,
		fontWeight: "700",
	},
	list: {
		gap: theme.gap(1),
		marginTop: theme.gap(1.5),
	},
	emptyState: {
		paddingVertical: theme.gap(1.5),
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		textAlign: "center",
	},
	customer: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
		padding: theme.gap(1.25),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-50"],
	},
	customerEmoji: {
		width: 40,
		height: 40,
	},
	customerCopy: {
		flex: 1,
	},
	customerName: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	customerItem: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-600"],
		fontSize: 11,
	},
	customerValue: {
		fontFamily: theme.fonts.family.numberBold,
		alignItems: "flex-end",
	},
	spentRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	spentIcon: {
		width: 16,
		height: 16,
	},
	spent: {
		color: theme.colors["amber-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	status: {
		marginTop: theme.gap(0.25),
		fontSize: 10,
		fontWeight: "700",
	},
	satisfaction: { marginTop: 2, fontSize: 9, fontWeight: "800" },
	happySatisfaction: { color: theme.colors["green-600"] },
	lowSatisfaction: { color: theme.colors["red-500"] },
}));
