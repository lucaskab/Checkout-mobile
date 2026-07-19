import { Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { StoreActiveCustomer } from "@/@types/store";

type ActiveCustomersCardProps = {
	customers: StoreActiveCustomer[];
};

export function ActiveCustomersCard({ customers }: ActiveCustomersCardProps) {
	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<Text style={styles.title}>👥 Clientes na loja</Text>
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
						<Text style={styles.customerEmoji}>{customer.emoji}</Text>
						<View style={styles.customerCopy}>
							<Text style={styles.customerName}>{customer.name}</Text>
							<Text numberOfLines={1} style={styles.customerItem}>
								{customer.item}
							</Text>
						</View>
						<View style={styles.customerValue}>
							<Text style={styles.spent}>🪙 {customer.spent}</Text>
							<Text style={[styles.status, statusStyles[customer.status]]}>
								{customer.status}
							</Text>
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
		alignItems: "center",
		justifyContent: "space-between",
	},
	title: {
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
		fontSize: 25,
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
		alignItems: "flex-end",
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
}));
