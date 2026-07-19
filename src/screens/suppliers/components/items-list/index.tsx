import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { SupplierOrder } from "@/@types/logistics";
import type { SupplierCategory, SupplierProduct } from "@/@types/supplier";
import { itemCatalog } from "@/data/market-products";
import {
	getOrderProgress,
	getOrderRemainingTime,
	getSupplierOrderStatus,
} from "@/services/logistics";
import { ProductCard } from "../product-card";

interface ItemsListProps {
	products: SupplierProduct[];
	activeCategory: SupplierCategory;
	coins: number;
	emergencyTokens: number;
	onPlaceOrder: (product: SupplierProduct) => boolean;
	onCompleteOrderFinalStage: (orderId: string) => boolean;
	onDeliverOrderInstantly: (orderId: string) => boolean;
	orders: SupplierOrder[];
}

export const ItemsList = ({
	products,
	activeCategory,
	coins,
	emergencyTokens,
	onPlaceOrder,
	onCompleteOrderFinalStage,
	onDeliverOrderInstantly,
	orders,
}: ItemsListProps) => {
	const [buyingId, setBuyingId] = useState<number | null>(null);
	const [currentTime, setCurrentTime] = useState(Date.now());
	const filteredProducts =
		activeCategory === "todos"
			? products
			: products.filter((product) => product.category === activeCategory);
	const activeOrders = orders.filter(
		(order) => getSupplierOrderStatus(order, currentTime) !== "entregue",
	);

	useEffect(() => {
		if (activeOrders.length === 0) {
			return;
		}

		const interval = setInterval(() => setCurrentTime(Date.now()), 1_000);

		return () => clearInterval(interval);
	}, [activeOrders.length]);

	function placeOrder(product: SupplierProduct) {
		if (coins < product.price) {
			return;
		}

		setBuyingId(product.id);
		setTimeout(() => {
			onPlaceOrder(product);
			setBuyingId(null);
		}, 350);
	}

	const renderProduct = ({
		item,
	}: LegendListRenderItemProps<SupplierProduct>) => {
		return (
			<ProductCard
				canAfford={coins >= item.price}
				isBuying={buyingId === item.id}
				onBuy={placeOrder}
				product={item}
			/>
		);
	};
	return (
		<LegendList
			contentContainerStyle={styles.productsList}
			data={filteredProducts}
			estimatedItemSize={250}
			keyExtractor={(product) => product.id.toString()}
			numColumns={2}
			renderItem={renderProduct}
			ListHeaderComponent={
				<View>
					{activeOrders.length > 0 && (
						<View style={styles.ordersHeader}>
							<Text style={styles.ordersTitle}>Pedidos em andamento</Text>
							<Text style={styles.ordersCount}>
								{activeOrders.length} ativo(s)
							</Text>
						</View>
					)}
					{activeOrders.map((order) => {
						const product = itemCatalog.find(
							(item) => item.id === order.productId,
						);
						const status = getSupplierOrderStatus(order, currentTime);
						const progress = getOrderProgress(order, currentTime);

						return (
							<View key={order.id} style={styles.orderCard}>
								<View style={styles.orderContent}>
									<Text style={styles.orderEmoji}>{product?.emoji}</Text>
									<View style={styles.orderCopy}>
										<Text style={styles.orderTitle}>
											{product?.name} · {order.quantity} unid.
										</Text>
										<Text style={styles.orderStatus}>
											{status === "em-producao"
												? "Em produção"
												: status === "enviado"
													? "Pedido enviado"
													: "Em transporte"}
										</Text>
										<Text style={styles.orderTime}>
											Chega em {getOrderRemainingTime(order, currentTime)}
										</Text>
									</View>
								</View>
								<View style={styles.orderProgressTrack}>
									<View
										style={[
											styles.orderProgressFill,
											{ width: `${Math.round(progress * 100)}%` },
										]}
									/>
								</View>
								<View style={styles.orderActions}>
									<Pressable
										onPress={() => onDeliverOrderInstantly(order.id)}
										style={styles.orderAction}
									>
										<Text style={styles.orderActionText}>
											{emergencyTokens > 0
												? "Entrega agora · 🎫"
												: "Entrega agora · 5 💎"}
										</Text>
									</Pressable>
									{status === "em-transporte" && (
										<Pressable
											onPress={() => onCompleteOrderFinalStage(order.id)}
											style={styles.orderActionSecondary}
										>
											<Text style={styles.orderActionSecondaryText}>
												Finalizar por 2 💎
											</Text>
										</Pressable>
									)}
								</View>
							</View>
						);
					})}
					<View style={styles.listHeader}>
						<Text style={styles.listTitle}>Produtos disponíveis</Text>
						<Text style={styles.listCount}>
							{filteredProducts.length} itens
						</Text>
					</View>
				</View>
			}
		/>
	);
};

const styles = StyleSheet.create((theme) => ({
	productsList: {
		paddingHorizontal: theme.gap(1.25),
		paddingTop: theme.gap(0.75),
		paddingBottom: theme.gap(3),
	},
	listHeader: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		paddingHorizontal: theme.gap(2),
		paddingTop: theme.gap(1.5),
	},
	ordersHeader: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		marginHorizontal: theme.gap(1.25),
		marginTop: theme.gap(1.25),
	},
	ordersTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	ordersCount: {
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	orderCard: {
		marginHorizontal: theme.gap(1.25),
		marginTop: theme.gap(1),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	orderActions: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1),
	},
	orderAction: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["blue-500"],
	},
	orderActionText: {
		color: theme.colors["neutral-0"],
		fontSize: 10,
		fontWeight: "700",
	},
	orderActionSecondary: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
	},
	orderActionSecondaryText: {
		color: theme.colors["blue-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	orderContent: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
	},
	orderEmoji: {
		fontSize: 22,
	},
	orderCopy: {
		flex: 1,
	},
	orderTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	orderStatus: {
		color: theme.colors["blue-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	orderTime: {
		marginTop: 2,
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	orderProgressTrack: {
		height: theme.gap(0.5),
		overflow: "hidden",
		marginTop: theme.gap(1),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-100"],
	},
	orderProgressFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-500"],
	},
	listTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	listCount: {
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		fontWeight: "600",
	},
}));
