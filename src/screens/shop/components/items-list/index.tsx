import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { useState } from "react";
import { Pressable, ScrollView, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { ShopCategory, ShopItemDefinition } from "@/@types/shop";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getShopCategoryIcon } from "@/data/game-icon-assets";
import { shopCategories, shopItems } from "@/data/shop-items";
import { ItemCard } from "../item-card";

type ItemsListProps = {
	coins: number;
	consumableAmounts: Record<string, number>;
	diamonds: number;
	level: number;
	onPurchase: (item: ShopItemDefinition) => boolean;
	ownedItemIds: string[];
};

export function ItemsList({
	coins,
	consumableAmounts,
	diamonds,
	level,
	onPurchase,
	ownedItemIds,
}: ItemsListProps) {
	const [category, setCategory] = useState<ShopCategory>("equipamentos");
	const [feedback, setFeedback] = useState<string | null>(null);
	const items = shopItems.filter((item) => item.category === category);

	function purchase(item: ShopItemDefinition) {
		if (onPurchase(item)) {
			setFeedback(
				item.isConsumable
					? `${item.name} foi adicionado aos boosters.`
					: `${item.name} foi instalado no mercado.`,
			);
			return;
		}

		setFeedback("Você ainda não atende aos requisitos desta compra.");
	}

	function renderItem({ item }: LegendListRenderItemProps<ShopItemDefinition>) {
		const isOwned = ownedItemIds.includes(item.id);
		const isLocked = level < item.level;
		const consumableAmount = consumableAmounts[item.id] ?? 0;
		const price = item.diamondPrice ?? item.coinPrice ?? 0;
		const canAfford = item.diamondPrice ? diamonds >= price : coins >= price;

		return (
			<ItemCard
				canAfford={canAfford}
				consumableAmount={consumableAmount}
				isLocked={isLocked}
				isOwned={isOwned}
				item={item}
				onPurchase={purchase}
			/>
		);
	}

	return (
		<LegendList
			contentContainerStyle={styles.content}
			data={items}
			estimatedItemSize={288}
			extraData={{
				coins,
				consumableAmounts,
				diamonds,
				level,
				ownedItemIds,
			}}
			keyExtractor={(item) => item.id}
			ListHeaderComponent={
				<View>
					<View style={styles.sectionTitleRow}>
						<View style={styles.titleAccent} />
						<Text style={styles.sectionTitle}>LOJA DO MERCADO</Text>
					</View>
					<ScrollView
						horizontal
						contentContainerStyle={styles.categories}
						showsHorizontalScrollIndicator={false}
					>
						{shopCategories.map((itemCategory) => {
							const isActive = itemCategory.id === category;

							return (
								<Pressable
									key={itemCategory.id}
									onPress={() => {
										setCategory(itemCategory.id);
										setFeedback(null);
									}}
									style={[styles.category, isActive && styles.activeCategory]}
								>
									<View
										style={[
											styles.categoryVisual,
											isActive && styles.activeCategoryVisual,
										]}
									>
										<GameIcon
											icon={getShopCategoryIcon(itemCategory.id)}
											style={styles.categoryEmoji}
										/>
									</View>
									<Text
										numberOfLines={1}
										style={[
											styles.categoryText,
											isActive && styles.activeCategoryText,
										]}
									>
										{itemCategory.label}
									</Text>
								</Pressable>
							);
						})}
					</ScrollView>
					<View style={styles.listHeader}>
						<Text style={styles.listTitle}>
							{
								shopCategories.find(
									(itemCategory) => itemCategory.id === category,
								)?.label
							}
						</Text>
						<Text style={styles.listCount}>{items.length} melhorias</Text>
					</View>
					{feedback && (
						<View style={styles.feedback}>
							<Text style={styles.feedbackIcon}>✓</Text>
							<Text style={styles.feedbackText}>{feedback}</Text>
						</View>
					)}
				</View>
			}
			numColumns={2}
			renderItem={renderItem}
		/>
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		paddingHorizontal: theme.gap(1.25),
		paddingBottom: theme.gap(3),
		backgroundColor: theme.colors["neutral-50"],
	},
	sectionTitleRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		paddingHorizontal: theme.gap(0.5),
		paddingTop: theme.gap(1.5),
	},
	titleAccent: {
		width: theme.gap(0.5),
		height: theme.gap(3.5),
		borderRadius: theme.gap(0.5),
		backgroundColor: theme.colors["blue-500"],
	},
	sectionTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
		letterSpacing: 0.3,
	},
	categories: {
		gap: theme.gap(0.5),
		paddingTop: theme.gap(1.25),
		paddingBottom: theme.gap(1.5),
	},
	category: {
		width: theme.gap(9.5),
		alignItems: "center",
		padding: theme.gap(0.75),
		borderWidth: 1,
		borderColor: "transparent",
		borderRadius: theme.gap(2),
	},
	activeCategory: {
		borderColor: theme.colors["blue-300"],
		backgroundColor: theme.colors["blue-500"],
		shadowColor: theme.colors["blue-700"],
		shadowOffset: { width: 0, height: 4 },
		shadowOpacity: 0.22,
		shadowRadius: 8,
		elevation: 5,
	},
	categoryVisual: {
		width: theme.gap(5.75),
		height: theme.gap(5.75),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	activeCategoryVisual: {
		backgroundColor: theme.colors["blue-600"],
	},
	categoryEmoji: {
		width: 40,
		height: 40,
	},
	categoryText: {
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		fontWeight: "700",
		textAlign: "center",
	},
	activeCategoryText: {
		color: theme.colors["neutral-0"],
	},
	listHeader: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		paddingHorizontal: theme.gap(0.625),
		marginBottom: theme.gap(0.5),
	},
	listTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	listCount: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	feedback: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginHorizontal: theme.gap(0.625),
		marginBottom: theme.gap(0.75),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["green-100"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["green-50"],
	},
	feedbackIcon: {
		color: theme.colors["green-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	feedbackText: {
		flex: 1,
		color: theme.colors["green-600"],
		fontSize: 11,
		fontWeight: "700",
	},
}));
