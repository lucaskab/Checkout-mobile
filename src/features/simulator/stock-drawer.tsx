import { Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import type { SimulatorProduct } from "./types";

type Props = {
	products: SimulatorProduct[];
	onOrder: (id: string) => void;
	onClose: () => void;
};

export function StockDrawer({ onClose, onOrder, products }: Props) {
	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<View>
					<Text style={styles.eyebrow}>GESTÃO RÁPIDA</Text>
					<Text style={styles.title}>Estoque da loja</Text>
				</View>
				<Pressable onPress={onClose} style={styles.close}>
					<Text style={styles.closeText}>×</Text>
				</Pressable>
			</View>
			<ScrollView contentContainerStyle={styles.list} showsVerticalScrollIndicator={false}>
				{products.map((product) => {
					const percentage = Math.min(
						100,
						Math.round((product.quantity / product.capacity) * 100),
					);

					return (
						<View key={product.id} style={styles.product}>
							<View style={styles.productHeader}>
								<Text style={styles.productName}>{product.name}</Text>
								<Text style={[styles.count, product.low && styles.low]}>
									{product.quantity}/{product.capacity}
								</Text>
							</View>
							<View style={styles.track}>
								<View
									style={[
										styles.fill,
										product.low && styles.fillLow,
										{ width: `${percentage}%` },
									]}
								/>
							</View>
							<Pressable onPress={() => onOrder(product.id)} style={styles.order}>
								<Text style={styles.orderText}>Pedir +20</Text>
							</Pressable>
						</View>
					);
				})}
			</ScrollView>
		</View>
	);
}

const styles = StyleSheet.create({
	card: {
		position: "absolute",
		top: 148,
		right: 14,
		bottom: 82,
		left: 14,
		padding: 16,
		borderRadius: 26,
		backgroundColor: "#fff9ed",
		elevation: 12,
		shadowColor: "#1f392d",
		shadowOffset: { width: 0, height: 10 },
		shadowOpacity: 0.25,
		shadowRadius: 18,
	},
	header: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		marginBottom: 12,
	},
	eyebrow: { color: "#5f8569", fontSize: 9, fontWeight: "900", letterSpacing: 1.2 },
	title: { marginTop: 2, color: "#293b32", fontSize: 20, fontWeight: "900" },
	close: {
		width: 34,
		height: 34,
		alignItems: "center",
		justifyContent: "center",
		borderRadius: 13,
		backgroundColor: "#e7efe4",
	},
	closeText: { color: "#42644f", fontSize: 24, lineHeight: 27 },
	list: { gap: 10, paddingBottom: 8 },
	product: { padding: 12, borderRadius: 18, backgroundColor: "#f3eddf" },
	productHeader: { flexDirection: "row", justifyContent: "space-between" },
	productName: { color: "#34483d", fontSize: 13, fontWeight: "800" },
	count: { color: "#557363", fontSize: 12, fontWeight: "900" },
	low: { color: "#c85d4a" },
	track: {
		height: 7,
		overflow: "hidden",
		marginTop: 8,
		borderRadius: 6,
		backgroundColor: "#d9dfd4",
	},
	fill: { height: 7, borderRadius: 6, backgroundColor: "#6f9a76" },
	fillLow: { backgroundColor: "#df795f" },
	order: {
		alignSelf: "flex-end",
		marginTop: 8,
		paddingHorizontal: 11,
		paddingVertical: 6,
		borderRadius: 10,
		backgroundColor: "#466e55",
	},
	orderText: { color: "#fffdf7", fontSize: 10, fontWeight: "900" },
});
