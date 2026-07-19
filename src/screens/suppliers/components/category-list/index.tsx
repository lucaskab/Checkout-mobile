import {
	FlatList,
	type ListRenderItemInfo,
	Pressable,
	Text,
} from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type {
	SupplierCategory,
	SupplierCategoryOption,
} from "@/@types/supplier";

type CategoryListProps = {
	activeCategory: SupplierCategory;
	categories: SupplierCategoryOption[];
	onSelectCategory: (category: SupplierCategory) => void;
};

export function CategoryList({
	activeCategory,
	categories,
	onSelectCategory,
}: CategoryListProps) {
	const renderItem = ({ item }: ListRenderItemInfo<SupplierCategoryOption>) => {
		const isActive = item.id === activeCategory;

		return (
			<Pressable
				onPress={() => onSelectCategory(item.id)}
				style={[styles.categoryItem, isActive && styles.activeCategoryItem]}
			>
				<Text style={styles.categoryEmoji}>{item.emoji}</Text>
				<Text
					style={[styles.categoryName, isActive && styles.activeCategoryName]}
				>
					{item.label}
				</Text>
			</Pressable>
		);
	};

	return (
		<FlatList
			data={categories}
			renderItem={renderItem}
			horizontal
			contentContainerStyle={styles.categoryList}
			showsHorizontalScrollIndicator={false}
		/>
	);
}

const styles = StyleSheet.create((theme) => ({
	categoryList: {
		paddingHorizontal: theme.gap(1.5),
		alignItems: "center",
		paddingVertical: theme.gap(2.75),
		backgroundColor: theme.colors["neutral-0"],
	},
	categoryItem: {
		flexDirection: "row",
		alignItems: "center",
		minHeight: theme.gap(6.5),
		maxHeight: theme.gap(6.5),
		gap: theme.gap(0.5),
		marginRight: theme.gap(0.75),
		paddingVertical: theme.gap(1),
		paddingHorizontal: theme.gap(1.25),
		borderRadius: theme.gap(3),
	},
	activeCategoryItem: {
		backgroundColor: theme.colors["blue-50"],
	},
	categoryEmoji: {
		fontSize: 16,
	},
	categoryName: {
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		fontWeight: theme.fonts.weight.medium,
		lineHeight: theme.gap(2),
	},
	activeCategoryName: {
		color: theme.colors["blue-600"],
		fontWeight: theme.fonts.weight.bold,
	},
}));
