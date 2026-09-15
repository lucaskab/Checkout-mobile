import { router } from "expo-router";
import { Pressable, ScrollView, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { EmbeddedNavigationProps } from "@/@types/embedded-navigation";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { employeeDefinitions } from "@/data/employees";
import { getEmployeeTrainingCost } from "@/services/employee-progression";
import { useGameStore } from "@/stores/game-store";

export function TeamScreen({ onBack }: EmbeddedNavigationProps = {}) {
	const coins = useGameStore((state) => state.coins);
	const level = useGameStore((state) => state.market.level);
	const employees = useGameStore((state) => state.employees.employees);
	const hireEmployee = useGameStore((state) => state.hireEmployee);
	const setEmployeeWorking = useGameStore((state) => state.setEmployeeWorking);
	const trainEmployee = useGameStore((state) => state.trainEmployee);

	return (
		<ScrollView contentContainerStyle={styles.content}>
			<View style={styles.hero}>
				<View style={styles.heroRow}>
					<View style={styles.heroIcon}>
						<GameIcon icon="manager" style={styles.heroImage} />
					</View>
					<View style={styles.heroCopy}>
						<Text style={styles.eyebrow}>GESTÃO DE PESSOAS</Text>
						<Text style={styles.title}>Monte seu time</Text>
					</View>
					<Text style={styles.coins}>🪙 {coins.toLocaleString("pt-BR")}</Text>
				</View>
				<Text style={styles.description}>
					Uma boa equipe transforma vendas em rotina: atendimento, reposição e
					reputação evoluem junto com o seu mercado.
				</Text>
			</View>

			{employeeDefinitions.map((definition) => {
				const employee = employees.find((item) => item.role === definition.id);
				const levelLocked = level < definition.level;
				const hireLocked = coins < definition.hireCost;

				return (
					<View key={definition.id} style={styles.card}>
						<View style={styles.avatar}>
							<GameIcon
								icon={roleIcon(definition.id)}
								style={styles.avatarImage}
							/>
						</View>
						<View style={styles.cardCopy}>
							<View style={styles.titleRow}>
								<Text style={styles.cardTitle}>{definition.name}</Text>
								<Text style={employee ? styles.hired : styles.locked}>
									{employee
										? employee.isWorking
											? "ATIVO"
											: "PAUSADO"
										: levelLocked
											? `NÍVEL ${definition.level}`
											: "DISPONÍVEL"}
								</Text>
							</View>
							<Text style={styles.cardDescription}>
								{definition.description}
							</Text>
							{employee ? (
								<View style={styles.employeeActions}>
									<View style={styles.employeeStats}>
										<Text style={styles.statText}>
											Nv. {employee.level} · {employee.efficiency} eficiência
										</Text>
										<Text style={styles.salary}>
											🪙 {employee.salary}/turno
										</Text>
									</View>
									<View style={styles.buttons}>
										<GameButton
											label={employee.isWorking ? "Pausar" : "Ativar"}
											onPress={() =>
												setEmployeeWorking(employee.id, !employee.isWorking)
											}
											size="small"
											variant={employee.isWorking ? "secondary" : "success"}
										/>
										<GameButton
											disabled={coins < getEmployeeTrainingCost(employee)}
											label={`Treinar ${getEmployeeTrainingCost(employee).toLocaleString("pt-BR")}`}
											onPress={() => trainEmployee(employee.id)}
											size="small"
											variant="coin"
										/>
									</View>
								</View>
							) : (
								<GameButton
									disabled={levelLocked || hireLocked}
									label={
										levelLocked
											? `Chegue ao nível ${definition.level}`
											: `Contratar por ${definition.hireCost.toLocaleString("pt-BR")}`
									}
									onPress={() => hireEmployee(definition.id)}
									size="small"
									variant="success"
								/>
							)}
						</View>
					</View>
				);
			})}

			<Pressable onPress={onBack ?? router.back} style={styles.backButton}>
				<Text style={styles.backText}>Voltar para o mercado</Text>
			</Pressable>
		</ScrollView>
	);
}

function roleIcon(role: (typeof employeeDefinitions)[number]["id"]) {
	switch (role) {
		case "cashier":
			return "calculator" as const;
		case "stock_clerk":
			return "package" as const;
		case "cleaner":
			return "broom" as const;
	}
}

const styles = StyleSheet.create((theme) => ({
	content: {
		gap: theme.gap(1.25),
		padding: theme.gap(1.5),
		paddingBottom: theme.gap(4),
		backgroundColor: theme.colors["neutral-50"],
	},
	hero: {
		padding: theme.gap(1.5),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-800"],
	},
	heroRow: { flexDirection: "row", alignItems: "center", gap: theme.gap(1) },
	heroIcon: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-500"],
	},
	heroImage: { width: theme.gap(3), height: theme.gap(3) },
	heroCopy: { flex: 1 },
	eyebrow: {
		color: theme.colors["blue-200"],
		fontSize: 9,
		fontWeight: "800",
		letterSpacing: 1.2,
	},
	title: {
		marginTop: theme.gap(0.35),
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 27,
	},
	coins: {
		color: theme.colors["amber-200"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
	},
	description: {
		marginTop: theme.gap(1),
		color: theme.colors["blue-100"],
		fontSize: 13,
		lineHeight: 19,
	},
	card: {
		flexDirection: "row",
		gap: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 2,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["neutral-0"],
	},
	avatar: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-100"],
	},
	avatarImage: { width: theme.gap(3), height: theme.gap(3) },
	cardCopy: { flex: 1, gap: theme.gap(0.6) },
	titleRow: {
		flexDirection: "row",
		justifyContent: "space-between",
		alignItems: "center",
		gap: theme.gap(0.5),
	},
	cardTitle: {
		flex: 1,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 16,
	},
	hired: { color: theme.colors["green-600"], fontSize: 9, fontWeight: "800" },
	locked: { color: theme.colors["amber-600"], fontSize: 9, fontWeight: "800" },
	cardDescription: {
		color: theme.colors["neutral-600"],
		fontSize: 12,
		lineHeight: 17,
	},
	employeeActions: { gap: theme.gap(0.5) },
	employeeStats: {
		flexDirection: "row",
		justifyContent: "space-between",
		gap: theme.gap(0.5),
	},
	statText: {
		color: theme.colors["blue-700"],
		fontSize: 10,
		fontWeight: "700",
	},
	salary: { color: theme.colors["neutral-500"], fontSize: 10 },
	buttons: { flexDirection: "row", flexWrap: "wrap", gap: theme.gap(0.5) },
	backButton: { alignItems: "center", padding: theme.gap(1) },
	backText: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.bodyBold,
		fontSize: 13,
	},
}));
