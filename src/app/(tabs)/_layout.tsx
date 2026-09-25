import { Tabs } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StyleSheet, useUnistyles } from "react-native-unistyles";
import { GameHeader } from "@/components/game-header";
import { TabBarIcon } from "@/components/tab-bar-icon";

export default function TabsLayout() {
	const { theme } = useUnistyles();
	const insets = useSafeAreaInsets();

	return (
		<Tabs
			safeAreaInsets={{ bottom: insets.bottom }}
			screenOptions={{
				header: () => <GameHeader />,
				tabBarStyle: styles.tabBar,
				tabBarItemStyle: styles.tabBarItem,
				tabBarLabelStyle: styles.tabBarLabel,
				tabBarActiveTintColor: theme.colors["blue-700"],
				tabBarInactiveTintColor: theme.colors["neutral-500"],
			}}
		>
			<Tabs.Screen
				name="index"
				options={{
					title: "Loja",
					tabBarIcon: ({ focused }) => (
						<TabBarIcon icon="market" focused={focused} />
					),
				}}
			/>
			<Tabs.Screen
				name="products"
				options={{
					title: "Produtos",
					tabBarIcon: ({ focused }) => (
						<TabBarIcon icon="basket" focused={focused} />
					),
				}}
			/>
			<Tabs.Screen
				name="storage"
				options={{
					title: "Depósito",
					tabBarIcon: ({ focused }) => (
						<TabBarIcon icon="warehouse" focused={focused} />
					),
				}}
			/>
			<Tabs.Screen
				name="sectors"
				options={{
					title: "Setores",
					tabBarIcon: ({ focused }) => (
						<TabBarIcon icon="shelf" focused={focused} />
					),
				}}
			/>
			<Tabs.Screen
				name="shop"
				options={{
					title: "Shop",
					tabBarIcon: ({ focused }) => (
						<TabBarIcon icon="diamond" focused={focused} />
					),
				}}
			/>
			<Tabs.Screen
				name="suppliers"
				options={{
					title: "Fornecedores",
					tabBarIcon: ({ focused }) => (
						<TabBarIcon icon="deliveryTruck" focused={focused} />
					),
				}}
			/>
			<Tabs.Screen
				name="currency-store"
				options={{ href: null, tabBarStyle: { display: "none" } }}
			/>
			<Tabs.Screen
				name="missions"
				options={{ href: null, tabBarStyle: { display: "none" } }}
			/>
			<Tabs.Screen
				name="achievements"
				options={{ href: null, tabBarStyle: { display: "none" } }}
			/>
			<Tabs.Screen
				name="expansions"
				options={{ href: null, tabBarStyle: { display: "none" } }}
			/>
			<Tabs.Screen
				name="team"
				options={{ href: null, tabBarStyle: { display: "none" } }}
			/>
		</Tabs>
	);
}

const styles = StyleSheet.create((theme) => ({
	tabBar: {
		height: theme.gap(9),
		paddingTop: theme.gap(0.75),
		paddingBottom: theme.gap(0.75),
	},
	tabBarItem: {
		paddingVertical: theme.gap(0.25),
	},
	tabBarLabel: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		marginTop: theme.gap(0.25),
	},
}));
