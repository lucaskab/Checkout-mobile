import {
	RTNGodot,
	RTNGodotView,
	runOnGodotThread,
} from "@borndotcom/react-native-godot";
import * as FileSystem from "expo-file-system/legacy";
import { useEffect, useMemo, useState } from "react";
import {
	ActivityIndicator,
	Platform,
	StatusBar,
	StyleSheet,
	Text,
	View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Worklets } from "react-native-worklets-core";
import { GameModeToggle } from "@/components/game-mode-toggle";
import { FloatingAction } from "./floating-action";
import { StockDrawer } from "./stock-drawer";
import type { SimulatorCommand, SimulatorState } from "./types";

const PROJECT_NAME = "CheckoutMarket";

type NativeBridge = {
	dispatch_json(command: string): void;
	get_snapshot_json(): string;
};

function findBridge(): NativeBridge | null {
	"worklet";
	if (RTNGodot.getInstance() == null) return null;
	const sceneTree = RTNGodot.API().Engine.get_main_loop();
	return sceneTree
		.get_root()
		.find_child("ReactNativeBridge", true, false) as NativeBridge | null;
}

function initializeGodot() {
	runOnGodotThread(() => {
		"worklet";
		if (RTNGodot.getInstance() != null) return;

		if (Platform.OS === "android") {
			RTNGodot.createInstance([
				"--path",
				`/${PROJECT_NAME}`,
				"--rendering-driver",
				"opengl3",
				"--rendering-method",
				"gl_compatibility",
				"--display-driver",
				"embedded",
			]);
			return;
		}

		RTNGodot.createInstance([
			"--main-pack",
			`${FileSystem.bundleDirectory}${PROJECT_NAME}.pck`,
			"--rendering-driver",
			"opengl3",
			"--rendering-method",
			"gl_compatibility",
			"--display-driver",
			"embedded",
		]);
	});
}

function formatMoney(value: number) {
	return new Intl.NumberFormat("pt-BR", {
		style: "currency",
		currency: "BRL",
		maximumFractionDigits: 0,
	}).format(value);
}

export default function GodotSimulator() {
	const [market, setMarket] = useState<SimulatorState | null>(null);
	const [stockOpen, setStockOpen] = useState(false);
	const applySnapshotOnJS = useMemo(
		() =>
			Worklets.createRunOnJS((snapshotJson: string) => {
				try {
					setMarket(JSON.parse(snapshotJson) as SimulatorState);
				} catch {
					// O próximo poll atualiza quando o Godot terminar de iniciar.
				}
			}),
		[],
	);

	useEffect(() => {
		initializeGodot();
		const interval = setInterval(() => {
			runOnGodotThread(() => {
				"worklet";
				const bridge = findBridge();
				if (bridge) applySnapshotOnJS(bridge.get_snapshot_json());
			});
		}, 350);

		return () => clearInterval(interval);
	}, [applySnapshotOnJS]);

	const lowStock = useMemo(
		() => market?.products.filter((product) => product.low).length ?? 0,
		[market],
	);

	function send(command: SimulatorCommand) {
		const commandJson = JSON.stringify(command);
		runOnGodotThread(() => {
			"worklet";
			findBridge()?.dispatch_json(commandJson);
		});
	}

	function cycleSpeed() {
		const current = market?.gameSpeed ?? 1;
		send({
			action: "set_speed",
			value: current < 1.5 ? 2 : current < 2.5 ? 3 : 1,
		});
	}

	return (
		<SafeAreaView edges={["top", "bottom"]} style={styles.screen}>
			<StatusBar hidden />
			<RTNGodotView style={styles.game} />

			<View style={styles.modeToggle}>
				<GameModeToggle activeMode="simulator" />
			</View>

			<View pointerEvents="none" style={styles.topStatus}>
				<View style={styles.statusHeader}>
					<View style={styles.brandDot} />
					<View style={styles.statusCopy}>
						<Text style={styles.statusEyebrow}>MERCADO GIRASSOL</Text>
						<Text style={styles.statusTitle}>
							{market ? "Simulação conectada" : "Iniciando LibGodot"}
						</Text>
					</View>
					<Text style={styles.clock}>{market?.time ?? "--:--"}</Text>
				</View>
				<View style={styles.valuesRow}>
					<StatusValue label="SALDO" value={formatMoney(market?.cash ?? 0)} />
					<StatusValue label="LUCRO" value={formatMoney(market?.profitToday ?? 0)} />
					<StatusValue
						label={`DIA ${market?.day ?? "--"}`}
						value={`${market?.queueSize ?? 0} na fila`}
					/>
				</View>
			</View>

			<View style={styles.actions}>
				<FloatingAction
					color="#4f7d60"
					icon={market?.paused ? "▶" : "Ⅱ"}
					label={market?.paused ? "Continuar" : "Pausar"}
					onPress={() => send({ action: "toggle_pause" })}
				/>
				<FloatingAction
					color="#60796e"
					icon="×"
					label={`${market?.gameSpeed ?? 1}x ritmo`}
					onPress={cycleSpeed}
				/>
				<FloatingAction
					color={lowStock ? "#d87a5f" : "#d7a950"}
					icon="▦"
					label={`Estoque${lowStock ? ` • ${lowStock}` : ""}`}
					onPress={() => setStockOpen(true)}
				/>
				<FloatingAction
					color="#755f80"
					icon="+"
					label="Contratar"
					onPress={() => send({ action: "hire_employee", role: "cashiers" })}
				/>
			</View>

			{stockOpen && market && (
				<StockDrawer
					onClose={() => setStockOpen(false)}
					onOrder={(product) =>
						send({ action: "order_stock", product, quantity: 20 })
					}
					products={market.products}
				/>
			)}

			{!market && (
				<View pointerEvents="none" style={styles.loader}>
					<ActivityIndicator color="#4f7d60" size="large" />
					<Text style={styles.loaderText}>Carregando o mercado nativo…</Text>
				</View>
			)}
		</SafeAreaView>
	);
}

function StatusValue({ label, value }: { label: string; value: string }) {
	return (
		<View style={styles.statusValue}>
			<Text numberOfLines={1} style={styles.value}>{value}</Text>
			<Text style={styles.caption}>{label}</Text>
		</View>
	);
}

const styles = StyleSheet.create({
	screen: { flex: 1, backgroundColor: "#cadfc9" },
	game: { flex: 1, backgroundColor: "#cadfc9" },
	modeToggle: {
		position: "absolute",
		top: 12,
		left: 0,
		right: 0,
		alignItems: "center",
	},
	topStatus: {
		position: "absolute",
		top: 82,
		left: 14,
		right: 14,
		padding: 14,
		borderRadius: 22,
		backgroundColor: "rgba(255,250,239,0.96)",
		elevation: 8,
		shadowColor: "#21392e",
		shadowOffset: { width: 0, height: 8 },
		shadowOpacity: 0.18,
		shadowRadius: 14,
	},
	statusHeader: { flexDirection: "row", alignItems: "center" },
	brandDot: { width: 9, height: 34, marginRight: 10, borderRadius: 7, backgroundColor: "#e6b75d" },
	statusCopy: { flex: 1 },
	statusEyebrow: { color: "#66816f", fontSize: 8, fontWeight: "900", letterSpacing: 1 },
	statusTitle: { marginTop: 2, color: "#2d4136", fontSize: 14, fontWeight: "900" },
	clock: { color: "#426b51", fontSize: 18, fontWeight: "900" },
	valuesRow: { flexDirection: "row", gap: 8, marginTop: 12 },
	statusValue: { flex: 1, padding: 8, borderRadius: 12, backgroundColor: "#f3eddf" },
	value: { color: "#426b51", fontSize: 12, fontWeight: "900" },
	caption: { marginTop: 2, color: "#7b897f", fontSize: 8, fontWeight: "800" },
	actions: {
		position: "absolute",
		left: 14,
		bottom: 14,
		flexDirection: "row",
		flexWrap: "wrap",
		gap: 9,
		maxWidth: 242,
	},
	loader: {
		position: "absolute",
		top: 0,
		right: 0,
		bottom: 0,
		left: 0,
		alignItems: "center",
		justifyContent: "center",
		gap: 12,
		backgroundColor: "#dcebd9",
	},
	loaderText: { color: "#42614f", fontWeight: "800" },
});
