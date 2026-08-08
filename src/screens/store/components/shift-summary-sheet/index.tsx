import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { GameShiftSummary } from "@/@types/game";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";

export function ShiftSummarySheet({ summary }: { summary: GameShiftSummary }) {
	const { closeBottomSheet } = useBottomSheet();
	const durationMinutes = Math.max(1, Math.round(summary.durationMs / 60_000));
	const satisfactionSign = summary.satisfactionChange > 0 ? "+" : "";

	return (
		<View style={styles.container}>
			<View style={styles.header}>
				<View style={styles.headerIcon}>
					<GameIcon icon="market" style={styles.headerImage} />
				</View>
				<View style={styles.headerCopy}>
					<Text style={styles.eyebrow}>TURNO ENCERRADO</Text>
					<Text style={styles.title}>O mercado rendeu bem!</Text>
					<Text style={styles.subtitle}>{durationMinutes} min de operação</Text>
				</View>
			</View>

			<View style={styles.statsGrid}>
				<SummaryStat
					icon="coin"
					label="Faturamento"
					value={`+${summary.revenue.toLocaleString("pt-BR")}`}
				/>
				<SummaryStat
					icon="customers"
					label="Clientes"
					value={`+${summary.customersServed}`}
				/>
				<SummaryStat
					icon="basket"
					label="Unidades"
					value={`+${summary.unitsSold}`}
				/>
				<SummaryStat
					icon="trophy"
					label="Experiência"
					value={`+${summary.experienceGained} XP`}
				/>
			</View>

			<View style={styles.satisfactionRow}>
				<View>
					<Text style={styles.satisfactionLabel}>Reputação do mercado</Text>
					<Text style={styles.satisfactionValue}>
						{Math.round(summary.satisfaction)}% satisfação
					</Text>
				</View>
				<Text
					style={[
						styles.satisfactionChange,
						summary.satisfactionChange < 0 && styles.negative,
					]}
				>
					{satisfactionSign}
					{summary.satisfactionChange.toFixed(1)}%
				</Text>
			</View>

			<GameButton
				label="Continuar crescendo"
				onPress={closeBottomSheet}
				fullWidth
			/>
		</View>
	);
}

function SummaryStat({
	icon,
	label,
	value,
}: {
	icon: "basket" | "coin" | "customers" | "trophy";
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

const styles = StyleSheet.create((theme) => ({
	container: { gap: theme.gap(1.25), paddingHorizontal: theme.gap(1.5) },
	header: { flexDirection: "row", alignItems: "center", gap: theme.gap(1) },
	headerIcon: {
		width: theme.gap(6),
		height: theme.gap(6),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["green-100"],
	},
	headerImage: { width: theme.gap(3.5), height: theme.gap(3.5) },
	headerCopy: { flex: 1 },
	eyebrow: {
		color: theme.colors["green-600"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1.2,
	},
	title: {
		marginTop: 2,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 21,
		fontWeight: "700",
	},
	subtitle: { marginTop: 2, color: theme.colors["neutral-500"], fontSize: 11 },
	statsGrid: { flexDirection: "row", flexWrap: "wrap", gap: theme.gap(0.75) },
	stat: {
		width: "48%",
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
	satisfactionRow: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-50"],
	},
	satisfactionLabel: { color: theme.colors["neutral-600"], fontSize: 11 },
	satisfactionValue: {
		marginTop: 2,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.bodyBold,
		fontSize: 14,
	},
	satisfactionChange: {
		color: theme.colors["green-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 16,
	},
	negative: { color: theme.colors["red-600"] },
}));
