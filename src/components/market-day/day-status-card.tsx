import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getContractProgress, getPendingRequests } from "@/services/market-day";
import { useGameStore } from "@/stores/game-store";
import { DayPlanningSheet } from "./day-planning-sheet";
import { DayResultSheet } from "./day-result-sheet";
import { SpecialRequestsSheet } from "./special-requests-sheet";
import { formatClock, useNow } from "./use-now";

// The turn at a glance: day number, clock, contract progress and the next action.
export function DayStatusCard({ compact = false }: { compact?: boolean }) {
	const { openBottomSheet } = useBottomSheet();
	const day = useGameStore((state) => state.day);
	const closeDay = useGameStore((state) => state.closeDay);
	const now = useNow(day.phase === "open");
	const progress = getContractProgress(day.contract, day.stats);
	const pending = getPendingRequests(day).length;
	styles.useVariants({ compact });

	function openRequests() {
		openBottomSheet(<SpecialRequestsSheet />);
	}

	// The results sheet opens on its own (MarketDayPrompts) once the day closes.
	function endDay() {
		closeDay();
	}

	if (day.phase === "planning") {
		return (
			<View style={styles.card}>
				<GameIcon icon="clipboard" style={styles.icon} />
				<View style={styles.copy}>
					<Text style={styles.eyebrow}>DIA {day.dayNumber}</Text>
					<Text numberOfLines={1} style={styles.title}>
						Escolha o contrato do dia
					</Text>
				</View>
				<GameButton
					icon="key"
					label="Planejar"
					onPress={() => openBottomSheet(<DayPlanningSheet />)}
					size={compact ? "small" : "medium"}
					variant="success"
				/>
			</View>
		);
	}

	if (day.phase === "results") {
		return (
			<View style={styles.card}>
				<GameIcon icon="trophy" style={styles.icon} />
				<View style={styles.copy}>
					<Text style={styles.eyebrow}>DIA {day.dayNumber} ENCERRADO</Text>
					<Text numberOfLines={1} style={styles.title}>
						Nota {day.result?.grade ?? "-"} · recompensas prontas
					</Text>
				</View>
				<GameButton
					icon="coin"
					label="Resultado"
					onPress={() => openBottomSheet(<DayResultSheet />)}
					size={compact ? "small" : "medium"}
					variant="coin"
				/>
			</View>
		);
	}

	return (
		<View style={styles.card}>
			<View style={styles.clock}>
				<Text style={styles.clockDay}>DIA {day.dayNumber}</Text>
				<Text style={styles.clockTime}>
					{formatClock((day.endsAt ?? now) - now)}
				</Text>
			</View>
			<View style={styles.copy}>
				<Text numberOfLines={1} style={styles.title}>
					{day.contract?.title ?? "Dia livre"}
				</Text>
				{day.contract && (
					<>
						<View style={styles.track}>
							<View
								style={[
									styles.fill,
									progress.completed && styles.fillDone,
									{ width: `${progress.ratio * 100}%` },
								]}
							/>
						</View>
						<Text numberOfLines={1} style={styles.progressLabel}>
							{progress.completed ? "Contrato cumprido!" : progress.label}
						</Text>
					</>
				)}
			</View>
			{pending > 0 && (
				<Pressable
					accessibilityLabel={`${pending} pedidos especiais esperando`}
					accessibilityRole="button"
					onPress={openRequests}
					style={styles.requests}
				>
					<GameIcon icon="customers" style={styles.requestsIcon} />
					<Text style={styles.requestsText}>{pending}</Text>
				</Pressable>
			)}
			<GameButton
				icon="lock"
				label={compact ? "Fechar" : "Encerrar"}
				onPress={endDay}
				size="small"
				variant="danger"
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	card: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderRadius: theme.gap(1.75),
		borderColor: theme.colors["neutral-200"],
		backgroundColor: theme.colors["neutral-0"],
		variants: {
			compact: {
				true: { padding: theme.gap(0.75), borderRadius: theme.gap(1.5) },
				false: { marginBottom: theme.gap(1.5) },
			},
		},
	},
	icon: { width: theme.gap(4), height: theme.gap(4) },
	copy: { flex: 1, gap: 2 },
	eyebrow: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 9,
		letterSpacing: 1,
	},
	title: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 15,
	},
	clock: {
		alignItems: "center",
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["blue-50"],
	},
	clockDay: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 9,
	},
	clockTime: {
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 16,
	},
	track: {
		height: 6,
		overflow: "hidden",
		borderRadius: 999,
		backgroundColor: theme.colors["neutral-100"],
	},
	fill: {
		height: "100%",
		borderRadius: 999,
		backgroundColor: theme.colors["amber-400"],
	},
	fillDone: { backgroundColor: theme.colors["green-500"] },
	progressLabel: { color: theme.colors["neutral-500"], fontSize: 10 },
	requests: {
		flexDirection: "row",
		alignItems: "center",
		gap: 2,
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: 999,
		backgroundColor: theme.colors["red-500"],
	},
	requestsIcon: { width: 18, height: 18 },
	requestsText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 13,
	},
}));
