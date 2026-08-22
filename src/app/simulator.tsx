import * as Device from "expo-device";
import { lazy, Suspense } from "react";
import { ActivityIndicator, Platform, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { GameModeToggle } from "@/components/game-mode-toggle";

const GodotSimulator = lazy(() => import("@/features/simulator/godot-simulator"));

const supportsGodot =
	Device.isDevice &&
	(Device.supportedCpuArchitectures?.some((architecture) =>
		/arm|armeabi/i.test(architecture),
	) ?? false);

export default function SimulatorRoute() {
	if (!supportsGodot) {
		const compatibilityMessage =
			Platform.OS === "ios"
				? "A integração LibGodot está preparada para um iPhone físico. Conecte o aparelho ao Mac e execute o development build para jogar."
				: "A LibGodot possui binários Android ARM. Este emulador x86_64 não carrega o motor nativo; conecte um aparelho Android para jogar.";

		return (
			<SafeAreaView style={styles.fallback}>
				<GameModeToggle activeMode="simulator" />
				<View style={styles.fallbackCard}>
					<Text style={styles.fallbackTitle}>Simulador disponível no celular</Text>
					<Text style={styles.fallbackText}>
						{compatibilityMessage}
					</Text>
				</View>
			</SafeAreaView>
		);
	}

	return (
		<Suspense
			fallback={
				<View style={styles.loading}>
					<ActivityIndicator color="#426b51" size="large" />
					<Text style={styles.loadingText}>Preparando LibGodot…</Text>
				</View>
			}
		>
			<GodotSimulator />
		</Suspense>
	);
}

const styles = StyleSheet.create({
	fallback: {
		flex: 1,
		alignItems: "center",
		gap: 28,
		paddingHorizontal: 20,
		paddingTop: 18,
		backgroundColor: "#dcebd9",
	},
	fallbackCard: {
		width: "100%",
		padding: 22,
		borderRadius: 24,
		backgroundColor: "#fff9ed",
		elevation: 6,
	},
	fallbackTitle: { color: "#293b32", fontSize: 20, fontWeight: "900" },
	fallbackText: {
		marginTop: 10,
		color: "#557363",
		fontSize: 14,
		fontWeight: "600",
		lineHeight: 21,
	},
	loading: {
		flex: 1,
		alignItems: "center",
		justifyContent: "center",
		gap: 12,
		backgroundColor: "#dcebd9",
	},
	loadingText: { color: "#42614f", fontWeight: "800" },
});
