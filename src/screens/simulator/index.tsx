import UnityView from "@azesmway/react-native-unity";
import { LegendList } from "@legendapp/list/react-native";
import { StatusBar } from "expo-status-bar";
import { useEffect, useRef, useState } from "react";
import { Pressable, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StyleSheet } from "react-native-unistyles";
import type { ProductionSector } from "@/@types/production";
import type { SimulatorPanel } from "@/@types/simulator";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameIcon } from "@/components/game-icon";
import { GameModeToggle } from "@/components/game-mode-toggle";
import { GameText as Text } from "@/components/game-text";
import type { GameIconId } from "@/data/game-icon-assets";
import { AchievementsScreen } from "@/screens/achievements";
import { CurrencyStoreScreen } from "@/screens/currency-store";
import { ExpansionsScreen } from "@/screens/expansions";
import { MissionsScreen } from "@/screens/missions";
import { ProductsScreen } from "@/screens/products";
import { SectorDetailScreen } from "@/screens/sector-detail";
import { SectorsScreen } from "@/screens/sectors";
import { ShelfManagementScreen } from "@/screens/shelf-management";
import { ShelfListScreen } from "@/screens/shelf-management/shelf-list";
import { ShopScreen } from "@/screens/shop";
import { SuppliersScreen } from "@/screens/suppliers";
import { TeamScreen } from "@/screens/team";
import { useGameStore } from "@/stores/game-store";
import { SimulatorEvent } from "./simulator-event";
import { SimulatorProgress } from "./simulator-progress";
import { useSimulator } from "./use-simulator";

const entries: {
	id: SimulatorPanel;
	label: string;
	icon: GameIconId;
	requiredLevel: number;
}[] = [
	{ id: "store", label: "Prateleiras", icon: "shelf", requiredLevel: 1 },
	{ id: "products", label: "Estoque", icon: "basket", requiredLevel: 1 },
	{
		id: "suppliers",
		label: "Entregas",
		icon: "deliveryTruck",
		requiredLevel: 1,
	},
	{ id: "sectors", label: "Produção", icon: "market", requiredLevel: 2 },
	{ id: "team", label: "Equipe", icon: "computer", requiredLevel: 2 },
	{ id: "shop", label: "Melhorias", icon: "toolbox", requiredLevel: 2 },
	{ id: "expansions", label: "Expansões", icon: "market", requiredLevel: 4 },
	{ id: "missions", label: "Missões", icon: "trophy", requiredLevel: 1 },
	{
		id: "achievements",
		label: "Conquistas",
		icon: "crown",
		requiredLevel: 1,
	},
	{ id: "currency", label: "Diamantes", icon: "diamond", requiredLevel: 1 },
];
export function SimulatorScreen() {
	const [shelfId, setShelfId] = useState<string | null>(null);
	const [sectorId, setSectorId] = useState<ProductionSector["id"] | null>(null);
	const { openBottomSheet, closeBottomSheet } = useBottomSheet();
	useEffect(() => {
		if (!shelfId) return;
		openBottomSheet(
			<ShelfManagementScreen
				key={shelfId}
				shelfId={shelfId}
				onClose={closeBottomSheet}
			/>,
		);
		setShelfId(null);
	}, [shelfId, openBottomSheet, closeBottomSheet]);
	useEffect(() => {
		if (!sectorId) return;

		openBottomSheet(
			<SectorDetailScreen
				key={sectorId}
				onBack={closeBottomSheet}
				sectorId={sectorId}
			/>,
		);
		setSectorId(null);
	}, [sectorId, openBottomSheet, closeBottomSheet]);
	const [menuOpen, setMenuOpen] = useState(false);
	const [panel, setPanel] = useState<SimulatorPanel | null>(null);
	const unityRef = useRef<UnityView>(null);
	const { status, onUnityMessage } = useSimulator(
		unityRef,
		setPanel,
		setShelfId,
		setSectorId,
	);
	const opened = useGameStore((s) => s.market.isOpen);
	const level = useGameStore((s) => s.market.level);
	const coins = useGameStore((s) => s.coins);
	const diamonds = useGameStore((s) => s.logistics.premiumCurrency);
	const setOpen = useGameStore((s) => s.setMarketOpen);
	const insets = useSafeAreaInsets();

	function closePanel() {
		setPanel(null);
	}

	function openPanel(nextPanel: SimulatorPanel) {
		setPanel(nextPanel);
		setMenuOpen(false);
	}

	function renderPanel() {
		switch (panel) {
			case "store":
				return <ShelfListScreen />;
			case "products":
				return <ProductsScreen />;
			case "suppliers":
				return <SuppliersScreen />;
			case "sectors":
				return <SectorsScreen />;
			case "team":
				return <TeamScreen onBack={closePanel} />;
			case "shop":
				return <ShopScreen />;
			case "expansions":
				return <ExpansionsScreen onBack={closePanel} />;
			case "missions":
				return <MissionsScreen onBack={closePanel} />;
			case "achievements":
				return <AchievementsScreen onBack={closePanel} />;
			case "currency":
				return <CurrencyStoreScreen onBack={closePanel} />;
			default:
				return null;
		}
	}

	const panelContent = renderPanel();
	return (
		<View style={styles.root}>
			<StatusBar animated hidden />
			<UnityView
				androidKeepPlayerMounted
				fullScreen
				keepPlayerMounted
				onUnityMessage={onUnityMessage}
				ref={unityRef}
				style={styles.world}
			/>
			<View pointerEvents="box-none" style={styles.overlay}>
				<View
					accessibilityElementsHidden={Boolean(panelContent)}
					importantForAccessibility={
						panelContent ? "no-hide-descendants" : "auto"
					}
					pointerEvents={panelContent ? "none" : "box-none"}
					style={styles.controls}
				>
					<View style={[styles.topHud, { top: insets.top + 8 }]}>
						<GameModeToggle />
						<View style={styles.playerStats}>
							<CurrencyChip icon="coin" value={coins} />
							<CurrencyChip icon="diamond" value={diamonds} />
						</View>
					</View>
					<View style={[styles.progressHud, { top: insets.top + 62 }]}>
						<SimulatorProgress onOpenPanel={openPanel} />
					</View>
					<View
						pointerEvents="box-none"
						style={[styles.eventHud, { top: insets.top + 124 }]}
					>
						<SimulatorEvent />
					</View>
					<Pressable
						accessibilityRole="button"
						accessibilityLabel={opened ? "Fechar mercado" : "Abrir mercado"}
						onPress={() => setOpen(!opened)}
						style={({ pressed }) => [
							styles.marketButton,
							{ top: insets.top + 124 },
							opened && styles.openMarketButton,
							pressed && styles.pressedMarketButton,
						]}
					>
						<GameIcon icon="market" style={styles.marketButtonIcon} />
						<Text style={styles.marketButtonText}>
							{opened ? "Fechar" : "Abrir"}
						</Text>
					</Pressable>
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
					<View
						style={[styles.toolbar, { bottom: Math.max(insets.bottom, 12) }]}
					>
						<LegendList
							contentContainerStyle={styles.toolbarContent}
							horizontal
							recycleItems
							data={menuOpen ? entries : entries.slice(0, 5)}
							keyExtractor={(e) => e.id}
							renderItem={({ item }) => {
								const locked = level < item.requiredLevel;

								return (
									<Pressable
										accessibilityRole="button"
										disabled={locked}
										accessibilityLabel={
											locked
												? `${item.label}. Disponível no nível ${item.requiredLevel}`
												: item.label
										}
										onPress={() => openPanel(item.id)}
										style={[styles.tool, locked && styles.lockedTool]}
									>
										<GameIcon icon={item.icon} style={styles.toolIcon} />
										<Text style={styles.toolText}>{item.label}</Text>
										{locked && (
											<View style={styles.toolLock}>
												<GameIcon icon="lock" style={styles.toolLockIcon} />
												<Text style={styles.toolLockText}>
													{item.requiredLevel}
												</Text>
											</View>
										)}
									</Pressable>
								);
							}}
							showsHorizontalScrollIndicator={false}
							style={styles.toolbarList}
						/>
						<Pressable
							accessibilityRole="button"
							accessibilityLabel={menuOpen ? "Recolher ações" : "Mais ações"}
							accessibilityState={{ expanded: menuOpen }}
							onPress={() => setMenuOpen(!menuOpen)}
							style={styles.tool}
						>
							<GameIcon
								icon={menuOpen ? "controller" : "toolbox"}
								style={styles.toolIcon}
							/>
							<Text style={styles.toolText}>{menuOpen ? "Menos" : "Mais"}</Text>
						</Pressable>
					</View>
				</View>
			</View>
			{panelContent && (
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
							onPress={closePanel}
							style={styles.panelButton}
						>
							<Text style={styles.buttonText}>Voltar ao mapa</Text>
						</Pressable>
					</View>
					<View style={styles.spacer}>{panelContent}</View>
				</View>
			)}
		</View>
	);
}

function CurrencyChip({ icon, value }: { icon: GameIconId; value: number }) {
	return (
		<View
			accessible
			accessibilityLabel={`${icon === "coin" ? "Moedas" : "Diamantes"}: ${value.toLocaleString("pt-BR")}`}
			style={styles.currencyChip}
		>
			<GameIcon icon={icon} style={styles.currencyIcon} />
			<Text numberOfLines={1} style={styles.currencyValue}>
				{value.toLocaleString("pt-BR", {
					notation: "compact",
					maximumFractionDigits: 1,
				})}
			</Text>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	root: { flex: 1, backgroundColor: theme.colors.gameBackground },
	world: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
	overlay: { flex: 1 },
	controls: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
	spacer: { flex: 1 },
	topHud: {
		position: "absolute",
		top: 0,
		left: 0,
		right: 0,
		paddingHorizontal: theme.gap(1),
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(0.5),
	},
	eventHud: { position: "absolute", left: theme.gap(1), right: theme.gap(10) },
	progressHud: {
		position: "absolute",
		left: theme.gap(1),
		right: theme.gap(1),
	},
	buttonText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 11,
		color: theme.colors["neutral-700"],
	},
	playerStats: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.375),
	},
	currencyChip: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.375),
		maxWidth: 110,
		paddingHorizontal: theme.gap(0.625),
		paddingVertical: theme.gap(0.25),
		borderWidth: 2,
		borderBottomWidth: 3,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	currencyIcon: { width: 19, height: 19 },
	currencyValue: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 12,
		color: theme.colors["neutral-700"],
	},
	marketButton: {
		position: "absolute",
		right: theme.gap(1),
		top: 112,
		alignItems: "center",
		gap: theme.gap(0.25),
		paddingHorizontal: theme.gap(0.875),
		paddingVertical: theme.gap(0.625),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderColor: theme.colors["green-600"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["green-500"],
	},
	openMarketButton: {
		borderColor: theme.colors["red-600"],
		backgroundColor: theme.colors["red-500"],
	},
	pressedMarketButton: {
		borderBottomWidth: 2,
		transform: [{ translateY: 2 }],
	},
	marketButtonIcon: { width: 28, height: 28 },
	marketButtonText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		color: theme.colors["neutral-0"],
	},
	panelButton: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.625),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-100"],
	},
	toolbar: {
		position: "absolute",
		left: 0,
		right: 0,
		height: 64,
		flexDirection: "row",
		alignItems: "center",
		paddingRight: theme.gap(1),
	},
	toolbarList: {
		flex: 1,
	},
	toolbarContent: {
		alignItems: "center",
		gap: theme.gap(0.5),
		paddingHorizontal: theme.gap(1),
	},
	tool: {
		width: 62,
		height: 60,
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.25),
		padding: theme.gap(0.5),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["neutral-100"],
	},
	toolIcon: { width: 27, height: 27 },
	toolText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 9,
		color: theme.colors["neutral-700"],
		textAlign: "center",
	},
	lockedTool: { opacity: 0.82 },
	toolLock: {
		position: "absolute",
		top: -5,
		right: -5,
		minWidth: 24,
		height: 22,
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: 1,
		paddingHorizontal: 3,
		borderWidth: 2,
		borderColor: theme.colors["neutral-0"],
		borderRadius: 11,
		backgroundColor: theme.colors["amber-500"],
	},
	toolLockIcon: { width: 11, height: 11 },
	toolLockText: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 8,
		color: theme.colors["neutral-800"],
	},
	notice: {
		position: "absolute",
		top: 170,
		left: 24,
		right: 24,
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
