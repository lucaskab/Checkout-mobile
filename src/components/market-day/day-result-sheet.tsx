import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { DayResult } from "@/@types/market-day";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import type { GameIconId } from "@/data/game-icon-assets";
import { useGameStore } from "@/stores/game-store";
import { gradeMessages } from "./labels";

// End of the turn: grade, profit and the rewards earned by the day's decisions.
export function DayResultSheet() {
	const { closeBottomSheet } = useBottomSheet();
	const day = useGameStore((state) => state.day);
	const claim = useGameStore((state) => state.claimDayResult);
	const result = day.result;

	if (day.phase !== "results" || !result) {
		return (
			<View style={styles.container}>
				<Text style={styles.title}>Nenhum resultado pendente</Text>
				<GameButton fullWidth label="Voltar" onPress={closeBottomSheet} />
			</View>
		);
	}

	function collect() {
		if (claim()) closeBottomSheet();
	}

	return <ResultContent onCollect={collect} result={result} />;
}

function ResultContent({
	onCollect,
	result,
}: {
	onCollect: () => void;
	result: DayResult;
}) {
	styles.useVariants({ grade: result.grade });
	const { stats } = result;
	const requests =
		stats.requestsServed +
		stats.requestsPartial +
		stats.requestsFailed +
		stats.requestsExpired;
	const minutes = Math.max(1, Math.round(result.durationMs / 60_000));

	return (
		<View style={styles.container}>
			<View style={styles.header}>
				<View style={styles.gradeBadge}>
					<Text style={styles.gradeText}>{result.grade}</Text>
				</View>
				<View style={styles.headerCopy}>
					<Text style={styles.eyebrow}>
						DIA {result.dayNumber} ENCERRADO · {minutes} MIN
					</Text>
					<Text style={styles.title}>{gradeMessages[result.grade]}</Text>
					<Text style={styles.subtitle}>Nota {result.score} de 100</Text>
				</View>
			</View>

			{result.contract && (
				<View
					style={[
						styles.contract,
						!result.contractCompleted && styles.contractFailed,
					]}
				>
					<GameIcon
						icon={result.contractCompleted ? "success" : "warning"}
						style={styles.contractIcon}
					/>
					<View style={styles.contractCopy}>
						<Text style={styles.contractTitle}>{result.contract.title}</Text>
						<Text style={styles.contractText}>
							{result.contractCompleted
								? "Contrato cumprido! Recompensa garantida."
								: `Faltou pouco: ${Math.round(result.contractProgress * 100)}% da meta.`}
						</Text>
					</View>
				</View>
			)}

			<View style={styles.grid}>
				<Stat
					icon="coin"
					label="Faturamento"
					value={stats.revenue.toLocaleString("pt-BR")}
				/>
				<Stat
					icon="receipt"
					label="Lucro nas vendas"
					value={stats.profit.toLocaleString("pt-BR")}
				/>
				<Stat
					icon="customers"
					label="Clientes"
					value={String(stats.customers)}
				/>
				<Stat
					icon="success"
					label="Satisfação média"
					value={`${result.averageSatisfaction}%`}
				/>
				<Stat
					icon="handshake"
					label="Pedidos atendidos"
					value={`${stats.requestsServed + stats.requestsPartial}/${requests}`}
				/>
				<Stat
					icon="medal"
					label="Fidelidade"
					value={`${stats.loyaltyChange >= 0 ? "+" : ""}${stats.loyaltyChange}`}
				/>
			</View>

			{result.highlights.length > 0 && (
				<View style={styles.highlights}>
					{result.highlights.map((line) => (
						<Text key={line} style={styles.highlight}>
							• {line}
						</Text>
					))}
				</View>
			)}

			<View style={styles.rewards}>
				<Text style={styles.rewardsTitle}>Recompensas do dia</Text>
				<View style={styles.rewardRow}>
					<Reward icon="coin" value={`+${result.total.coins}`} />
					<Reward icon="trophy" value={`+${result.total.experience} XP`} />
					{result.total.diamonds > 0 && (
						<Reward icon="diamond" value={`+${result.total.diamonds}`} />
					)}
				</View>
				<Text style={styles.rewardsNote}>
					Inclui bônus de desempenho pela nota {result.grade}.
					{stats.tips > 0 ? ` Gorjetas (${stats.tips}) já estão no caixa.` : ""}
				</Text>
			</View>

			<GameButton
				fullWidth
				icon="coin"
				label={`Coletar e planejar o dia ${result.dayNumber + 1}`}
				onPress={onCollect}
				variant="coin"
			/>
		</View>
	);
}

function Stat({
	icon,
	label,
	value,
}: {
	icon: GameIconId;
	label: string;
	value: string;
}) {
	return (
		<View style={styles.stat}>
			<GameIcon icon={icon} style={styles.statIcon} />
			<Text style={styles.statValue}>{value}</Text>
			<Text style={styles.statLabel}>{label}</Text>
		</View>
	);
}

function Reward({ icon, value }: { icon: GameIconId; value: string }) {
	return (
		<View style={styles.reward}>
			<GameIcon icon={icon} style={styles.rewardIcon} />
			<Text style={styles.rewardValue}>{value}</Text>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	container: { gap: theme.gap(1.25), paddingHorizontal: theme.gap(1.5) },
	header: { flexDirection: "row", alignItems: "center", gap: theme.gap(1.25) },
	gradeBadge: {
		width: theme.gap(8),
		height: theme.gap(8),
		alignItems: "center",
		justifyContent: "center",
		borderWidth: 3,
		borderBottomWidth: 6,
		borderRadius: theme.gap(2.5),
		variants: {
			grade: {
				S: {
					backgroundColor: theme.colors["violet-500"],
					borderColor: theme.colors["violet-600"],
				},
				A: {
					backgroundColor: theme.colors["green-500"],
					borderColor: theme.colors["green-600"],
				},
				B: {
					backgroundColor: theme.colors["blue-500"],
					borderColor: theme.colors["blue-600"],
				},
				C: {
					backgroundColor: theme.colors["amber-400"],
					borderColor: theme.colors["amber-600"],
				},
				D: {
					backgroundColor: theme.colors["red-500"],
					borderColor: theme.colors["red-600"],
				},
			},
		},
	},
	gradeText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 40,
	},
	headerCopy: { flex: 1 },
	eyebrow: {
		color: theme.colors["neutral-500"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		letterSpacing: 1.1,
	},
	title: {
		marginTop: 2,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 22,
	},
	subtitle: { marginTop: 2, color: theme.colors["neutral-500"], fontSize: 12 },
	contract: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["green-50"],
	},
	contractFailed: { backgroundColor: theme.colors["red-50"] },
	contractIcon: { width: theme.gap(3.5), height: theme.gap(3.5) },
	contractCopy: { flex: 1 },
	contractTitle: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.bodyBold,
		fontSize: 14,
	},
	contractText: { color: theme.colors["neutral-600"], fontSize: 12 },
	grid: { flexDirection: "row", flexWrap: "wrap", gap: theme.gap(0.75) },
	stat: {
		width: "31%",
		flexGrow: 1,
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	statIcon: { width: theme.gap(2.5), height: theme.gap(2.5) },
	statValue: {
		marginTop: theme.gap(0.35),
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 15,
	},
	statLabel: { marginTop: 1, color: theme.colors["neutral-500"], fontSize: 10 },
	highlights: {
		gap: 4,
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-50"],
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
	},
	highlight: { color: theme.colors["neutral-700"], fontSize: 12 },
	rewards: {
		gap: theme.gap(0.5),
		padding: theme.gap(1.25),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-50"],
	},
	rewardsTitle: {
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 12,
	},
	rewardRow: { flexDirection: "row", gap: theme.gap(1.5) },
	reward: { flexDirection: "row", alignItems: "center", gap: 4 },
	rewardIcon: { width: 22, height: 22 },
	rewardValue: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 16,
	},
	rewardsNote: { color: theme.colors["neutral-500"], fontSize: 11 },
}));
