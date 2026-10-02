import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { DayContract } from "@/@types/market-day";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getPiecesToPlaceBeforeOpening } from "@/services/market-era";
import { DAY_DURATION_MS, FREE_DAY_CONTRACT_ID } from "@/services/market-day";
import { useGameStore } from "@/stores/game-store";
import { contractIcon } from "./labels";

const difficultyLabels = { 1: "Fácil", 2: "Médio", 3: "Difícil" } as const;

// Start of a turn: pick one of today's contracts (or a free day) and open the market.
export function DayPlanningSheet() {
	const { closeBottomSheet } = useBottomSheet();
	const day = useGameStore((state) => state.day);
	const startDay = useGameStore((state) => state.startDay);
	const waiting = useGameStore(
		(state) => getPiecesToPlaceBeforeOpening(state),
	);
	const minutes = Math.round(DAY_DURATION_MS / 60_000);

	function start(contractId: string) {
		if (startDay(contractId)) closeBottomSheet();
	}

	if (day.phase !== "planning") {
		return (
			<View style={styles.container}>
				<Text style={styles.title}>O dia {day.dayNumber} já começou</Text>
				<GameButton fullWidth label="Voltar" onPress={closeBottomSheet} />
			</View>
		);
	}

	return (
		<View style={styles.container}>
			<View>
				<Text style={styles.eyebrow}>
					DIA {day.dayNumber} · {minutes} MIN
				</Text>
				<Text style={styles.title}>Escolha o contrato de hoje</Text>
				<Text style={styles.subtitle}>
					Cumpra a meta antes de fechar para ganhar a recompensa. Pedidos
					especiais bem atendidos melhoram a nota do dia.
				</Text>
			</View>
			{waiting > 0 && (
				<View style={styles.notice}>
					<GameIcon icon="hammer" style={styles.noticeIcon} />
					<Text style={styles.noticeText}>
						Monte a sua loja primeiro: você tem {waiting}{" "}
						{waiting === 1 ? "móvel" : "móveis"} para colocar. Toque em
						Construir e posicione o caixa e as prateleiras onde quiser.
					</Text>
				</View>
			)}
			{day.offers.map((offer) => (
				<ContractCard
					contract={offer}
					key={offer.id}
					onChoose={() => start(offer.id)}
				/>
			))}
			<GameButton
				fullWidth
				icon="key"
				label="Abrir sem contrato"
				onPress={() => start(FREE_DAY_CONTRACT_ID)}
				variant="secondary"
			/>
		</View>
	);
}

function ContractCard({
	contract,
	onChoose,
}: {
	contract: DayContract;
	onChoose: () => void;
}) {
	styles.useVariants({ difficulty: contract.difficulty });

	return (
		<View style={styles.card}>
			<View style={styles.cardHeader}>
				<View style={styles.iconPlate}>
					<GameIcon icon={contractIcon(contract.icon)} style={styles.icon} />
				</View>
				<View style={styles.cardCopy}>
					<View style={styles.titleRow}>
						<Text numberOfLines={1} style={styles.cardTitle}>
							{contract.title}
						</Text>
						<View style={styles.difficulty}>
							<Text style={styles.difficultyText}>
								{difficultyLabels[contract.difficulty]}
							</Text>
						</View>
					</View>
					<Text style={styles.cardDescription}>{contract.description}</Text>
				</View>
			</View>
			<View style={styles.cardFooter}>
				<View style={styles.rewards}>
					<Reward icon="coin" value={`+${contract.reward.coins}`} />
					<Reward icon="trophy" value={`+${contract.reward.experience} XP`} />
					{contract.reward.diamonds > 0 && (
						<Reward icon="diamond" value={`+${contract.reward.diamonds}`} />
					)}
				</View>
				<GameButton
					label="Aceitar"
					onPress={onChoose}
					size="small"
					variant="success"
				/>
			</View>
		</View>
	);
}

function Reward({
	icon,
	value,
}: {
	icon: "coin" | "trophy" | "diamond";
	value: string;
}) {
	return (
		<View style={styles.reward}>
			<GameIcon icon={icon} style={styles.rewardIcon} />
			<Text style={styles.rewardText}>{value}</Text>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	container: { gap: theme.gap(1.25), paddingHorizontal: theme.gap(1.5) },
	notice: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["amber-50"],
	},
	noticeIcon: { width: 36, height: 36 },
	noticeText: {
		flex: 1,
		color: theme.colors["neutral-700"],
		fontSize: 12,
		fontWeight: "600",
	},
	eyebrow: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		letterSpacing: 1.2,
	},
	title: {
		marginTop: 2,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 21,
	},
	subtitle: { marginTop: 4, color: theme.colors["neutral-500"], fontSize: 12 },
	card: {
		gap: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderRadius: theme.gap(1.75),
		borderColor: theme.colors["neutral-150"],
		backgroundColor: theme.colors["neutral-0"],
	},
	cardHeader: { flexDirection: "row", gap: theme.gap(1) },
	iconPlate: {
		width: theme.gap(5.5),
		height: theme.gap(5.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		variants: {
			difficulty: {
				1: { backgroundColor: theme.colors["green-50"] },
				2: { backgroundColor: theme.colors["amber-50"] },
				3: { backgroundColor: theme.colors["violet-50"] },
			},
		},
	},
	icon: { width: theme.gap(3.5), height: theme.gap(3.5) },
	cardCopy: { flex: 1, gap: 2 },
	titleRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
	},
	cardTitle: {
		flexShrink: 1,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 16,
	},
	difficulty: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: 2,
		borderRadius: 999,
		variants: {
			difficulty: {
				1: { backgroundColor: theme.colors["green-100"] },
				2: { backgroundColor: theme.colors["amber-100"] },
				3: { backgroundColor: theme.colors["violet-100"] },
			},
		},
	},
	difficultyText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
		variants: {
			difficulty: {
				1: { color: theme.colors["green-600"] },
				2: { color: theme.colors["amber-600"] },
				3: { color: theme.colors["violet-600"] },
			},
		},
	},
	cardDescription: { color: theme.colors["neutral-600"], fontSize: 12 },
	cardFooter: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(1),
	},
	rewards: {
		flexDirection: "row",
		flexWrap: "wrap",
		gap: theme.gap(0.75),
		flex: 1,
	},
	reward: { flexDirection: "row", alignItems: "center", gap: 3 },
	rewardIcon: { width: 16, height: 16 },
	rewardText: {
		color: theme.colors["neutral-700"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 12,
	},
}));
