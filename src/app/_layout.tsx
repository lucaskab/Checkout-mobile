import { Fredoka_600SemiBold } from "@expo-google-fonts/fredoka/600SemiBold";
import { Fredoka_700Bold } from "@expo-google-fonts/fredoka/700Bold";
import { JetBrainsMono_500Medium } from "@expo-google-fonts/jetbrains-mono/500Medium";
import { JetBrainsMono_700Bold } from "@expo-google-fonts/jetbrains-mono/700Bold";
import { Nunito_400Regular } from "@expo-google-fonts/nunito/400Regular";
import { Nunito_600SemiBold } from "@expo-google-fonts/nunito/600SemiBold";
import { Nunito_700Bold } from "@expo-google-fonts/nunito/700Bold";
import { Nunito_800ExtraBold } from "@expo-google-fonts/nunito/800ExtraBold";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { useEffect } from "react";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { BackgroundMusic } from "@/components/background-music";
import { BottomSheetProvider } from "@/components/bottom-sheet";
import { EmployeeSimulation } from "@/components/employee-simulation";
import { GameEventSimulation } from "@/components/game-event-simulation";
import { GameSessionLifecycle } from "@/components/game-session-lifecycle";
import { InventorySpoilageSimulation } from "@/components/inventory-spoilage-simulation";
import { MarketSimulation } from "@/components/market-simulation";
import { ProductionSimulation } from "@/components/production-simulation";
import { RevenueCatInitializer } from "@/components/revenue-cat-initializer";
import { SupplierLogisticsSimulation } from "@/components/supplier-logistics-simulation";

const queryClient = new QueryClient();

SplashScreen.preventAutoHideAsync();

export default function RootLayout() {
	const [fontsLoaded, fontError] = useFonts({
		Fredoka_600SemiBold,
		Fredoka_700Bold,
		JetBrainsMono_500Medium,
		JetBrainsMono_700Bold,
		Nunito_400Regular,
		Nunito_600SemiBold,
		Nunito_700Bold,
		Nunito_800ExtraBold,
	});

	useEffect(() => {
		if (fontsLoaded || fontError) {
			SplashScreen.hideAsync();
		}
	}, [fontError, fontsLoaded]);

	if (!fontsLoaded && !fontError) {
		return null;
	}

	return (
		<QueryClientProvider client={queryClient}>
			<GestureHandlerRootView style={{ flex: 1 }}>
				<BottomSheetProvider>
					<BackgroundMusic />
					<GameEventSimulation />
					<GameSessionLifecycle />
					<EmployeeSimulation />
					<InventorySpoilageSimulation />
					<MarketSimulation />
					<ProductionSimulation />
					<RevenueCatInitializer />
					<SupplierLogisticsSimulation />
					<Stack screenOptions={{ headerShown: false }}>
						<Stack.Screen name="(tabs)" />
						<Stack.Screen
							name="simulator"
							options={{ animation: "fade", gestureEnabled: false }}
						/>
					</Stack>
				</BottomSheetProvider>
			</GestureHandlerRootView>
		</QueryClientProvider>
	);
}
