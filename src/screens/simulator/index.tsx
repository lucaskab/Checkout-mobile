import { LegendList } from "@legendapp/list/react-native";
import { router } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StyleSheet } from "react-native-unistyles";
import type { SimulatorPanel } from "@/@types/simulator";
import { GameHeader } from "@/components/game-header";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import type { GameIconId } from "@/data/game-icon-assets";
import { AchievementsScreen } from "@/screens/achievements";
import { CurrencyStoreScreen } from "@/screens/currency-store";
import { ExpansionsScreen } from "@/screens/expansions";
import { MissionsScreen } from "@/screens/missions";
import { ProductsScreen } from "@/screens/products";
import { SectorsScreen } from "@/screens/sectors";
import { ShopScreen } from "@/screens/shop";
import { StoreScreen } from "@/screens/store";
import { SuppliersScreen } from "@/screens/suppliers";
import { TeamScreen } from "@/screens/team";
import { useGameStore } from "@/stores/game-store";
import UnityView from "@azesmway/react-native-unity";
import { useSimulator } from "./use-simulator";

const entries: { id: SimulatorPanel; label: string; icon: GameIconId }[] = [
	{ id: "store", label: "Prateleiras", icon: "shelf" },
	{ id: "products", label: "Estoque", icon: "basket" },
	{ id: "suppliers", label: "Entregas", icon: "deliveryTruck" },
	{ id: "sectors", label: "Produção", icon: "market" },
	{ id: "team", label: "Equipe", icon: "computer" },
	{ id: "shop", label: "Melhorias", icon: "toolbox" },
	{ id: "expansions", label: "Expansões", icon: "market" },
	{ id: "missions", label: "Missões", icon: "computer" },
	{ id: "achievements", label: "Conquistas", icon: "computer" },
	{ id: "currency", label: "Diamantes", icon: "diamond" },
];
const screens = {
	store: StoreScreen,
	products: ProductsScreen,
	suppliers: SuppliersScreen,
	sectors: SectorsScreen,
	team: TeamScreen,
	shop: ShopScreen,
	expansions: ExpansionsScreen,
	missions: MissionsScreen,
	achievements: AchievementsScreen,
	currency: CurrencyStoreScreen,
};
export function SimulatorScreen() {
	const [panel, setPanel] = useState<SimulatorPanel | null>(null);
	const unityRef = useRef<UnityView>(null);
	const openPanel = useCallback((next: SimulatorPanel) => setPanel(next), []);
	const { status, onUnityMessage } = useSimulator(unityRef, openPanel);
	const opened = useGameStore((s) => s.market.isOpen);
	const setOpen = useGameStore((s) => s.setMarketOpen);
	const insets = useSafeAreaInsets();
	const Panel = panel ? screens[panel] : null;
	return (
		<View style={styles.root}>
			<UnityView
				androidKeepPlayerMounted
				fullScreen={false}
				onUnityMessage={onUnityMessage}
				ref={unityRef}
				style={styles.world}
			/>
			<View pointerEvents="box-none" style={styles.overlay}>
				<GameHeader />
				<View style={styles.controls}>
					<Pressable
						accessibilityRole="button"
						accessibilityLabel="Voltar ao modo sistema"
						onPress={() => router.replace("/")}
						style={styles.button}
					>
						<GameIcon icon="computer" style={styles.icon} />
						<Text style={styles.buttonText}>Sistema</Text>
					</Pressable>
					<Pressable
						accessibilityRole="button"
						onPress={() => setOpen(!opened)}
						style={[styles.button, styles.openButton]}
					>
						<Text style={styles.buttonText}>
							{opened ? "Fechar mercado" : "Abrir mercado"}
						</Text>
					</Pressable>
				</View>
				{status !== "ready" && (
					<View style={styles.notice}>
						<Text style={styles.noticeTitle}>
							{status === "loading"
								? "Preparando seu mercado…"
								: "Não foi possível iniciar o simulador"}
						</Text>
						<Text style={styles.noticeBody}>
							{status === "loading"
								? "Seu progresso está sendo carregado."
								: "Tente abrir o modo novamente. Se persistir, reinstale a versão atualizada do app."}
						</Text>
					</View>
				)}
				<View pointerEvents="none" style={styles.spacer} />
				<View
					style={[
						styles.toolbar,
						{ paddingBottom: Math.max(insets.bottom, 8) },
					]}
				>
					<LegendList
						horizontal
						data={entries}
						keyExtractor={(e) => e.id}
						renderItem={({ item }) => (
							<Pressable
								accessibilityRole="button"
								onPress={() => setPanel(item.id)}
								style={styles.tool}
							>
								<GameIcon icon={item.icon} style={styles.toolIcon} />
								<Text style={styles.toolText}>{item.label}</Text>
							</Pressable>
						)}
					/>
				</View>
			</View>
			{Panel && (
				<View
					style={[
						styles.panel,
						{ top: insets.top + 8, paddingBottom: insets.bottom },
					]}
				>
					<View style={styles.panelHeader}>
						<Text style={styles.panelTitle}>
							{entries.find((e) => e.id === panel)?.label}
						</Text>
						<Pressable
							accessibilityRole="button"
							accessibilityLabel="Voltar ao mapa"
							onPress={() => setPanel(null)}
							style={styles.button}
						>
							<Text style={styles.buttonText}>Voltar ao mapa</Text>
						</Pressable>
					</View>
					<View style={styles.spacer}>
						<Panel />
					</View>
				</View>
			)}
		</View>
	);
}
const styles = StyleSheet.create((theme) => ({
	root: { flex: 1, backgroundColor: theme.colors.gameBackground },
	world: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
	overlay: { flex: 1 },
	spacer: { flex: 1 },
	controls: {
		flexDirection: "row",
		justifyContent: "space-between",
		padding: theme.gap(1),
		gap: theme.gap(1),
	},
	button: {
		flexDirection: "row",
		gap: 6,
		alignItems: "center",
		paddingHorizontal: 14,
		paddingVertical: 10,
		borderRadius: 14,
		borderWidth: 2,
		borderBottomWidth: 4,
		borderColor: theme.colors["neutral-300"],
		backgroundColor: theme.colors["neutral-100"],
	},
	openButton: { backgroundColor: theme.colors["green-100"] },
	buttonText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 13,
		color: theme.colors["neutral-700"],
	},
	icon: { width: 22, height: 22 },
	toolbar: {
		height: 110,
		backgroundColor: theme.colors["neutral-100"],
		borderTopWidth: 3,
		borderColor: theme.colors["neutral-300"],
	},
	tool: {
		width: 94,
		alignItems: "center",
		justifyContent: "center",
		padding: 8,
		gap: 5,
	},
	toolIcon: { width: 36, height: 36 },
	toolText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 11,
		color: theme.colors["neutral-700"],
	},
	notice: {
		margin: 24,
		padding: 20,
		borderRadius: 20,
		backgroundColor: theme.colors["neutral-100"],
		borderWidth: 2,
		borderColor: theme.colors["neutral-300"],
	},
	noticeTitle: {
		fontFamily: theme.fonts.family.headline,
		fontSize: 20,
		color: theme.colors["neutral-700"],
	},
	noticeBody: {
		fontSize: 14,
		color: theme.colors["neutral-600"],
		marginTop: 8,
	},
	panel: {
		position: "absolute",
		left: 0,
		right: 0,
		bottom: 0,
		backgroundColor: theme.colors.gameBackground,
		borderTopLeftRadius: 22,
		borderTopRightRadius: 22,
		borderWidth: 2,
		borderColor: theme.colors["neutral-300"],
	},
	panelHeader: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		padding: 12,
	},
	panelTitle: {
		fontFamily: theme.fonts.family.headline,
		fontSize: 22,
		color: theme.colors["neutral-700"],
	},
}));
