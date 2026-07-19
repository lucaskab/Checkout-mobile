import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Tabs } from "expo-router";
import { StyleSheet } from "react-native-unistyles";
import { BackgroundMusic } from "@/components/background-music";
import { BottomSheetProvider } from "@/components/bottom-sheet";
import { IapProvider } from "@/components/iap-provider";
import { MarketSimulation } from "@/components/market-simulation";
import { SupplierLogisticsSimulation } from "@/components/supplier-logistics-simulation";

const queryClient = new QueryClient();
export default function RootLayout() {
	return (
		<QueryClientProvider client={queryClient}>
			<IapProvider>
				<BottomSheetProvider>
					<BackgroundMusic />
					<MarketSimulation />
					<SupplierLogisticsSimulation />
					<Tabs
						safeAreaInsets={{ bottom: 0 }}
						screenOptions={{
							headerStatusBarHeight: 0,
							headerStyle: styles.header,
							headerTitleStyle: styles.headerTitle,
							tabBarStyle: styles.tabBar,
							tabBarItemStyle: styles.tabBarItem,
							tabBarLabelStyle: styles.tabBarLabel,
						}}
					>
						<Tabs.Screen name="index" options={{ title: "Loja" }} />
						<Tabs.Screen name="suppliers" options={{ headerShown: false }} />
						<Tabs.Screen
							name="customers"
							options={{ headerShown: false, title: "Clientes" }}
						/>
					</Tabs>
				</BottomSheetProvider>
			</IapProvider>
		</QueryClientProvider>
	);
}

const styles = StyleSheet.create((theme) => ({
	header: {
		backgroundColor: theme.colors["neutral-0"],
	},
	headerTitle: {
		color: theme.colors["neutral-700"],
		fontFamily: theme.fonts.weight.bold,
		fontSize: theme.fonts.size.medium,
	},
	tabBar: {
		paddingTop: theme.gap(0.5),
		paddingBottom: theme.gap(0.5),
		borderTopColor: theme.colors["neutral-100"],
		backgroundColor: theme.colors["neutral-0"],
	},
	tabBarItem: {
		paddingVertical: 0,
	},
	tabBarLabel: {
		fontFamily: theme.fonts.weight.bold,
		fontSize: theme.fonts.size.small,
	},
}));
