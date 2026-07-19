import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { StyleSheet } from "react-native-unistyles";
import type {
	PurchaseDecision,
	SimulationResult,
} from "@/@types/customer-simulation";
import { simulateCustomers } from "@/services/customer-simulation";

const marketPrice = 5;
const customerCount = 50;

export function CustomerSimulatorScreen() {
	const insets = useSafeAreaInsets();
	const [sellingPrice, setSellingPrice] = useState(5.5);
	const [promotionRate, setPromotionRate] = useState(0);
	const [simulation, setSimulation] = useState<SimulationResult | null>(null);
	const [seed, setSeed] = useState(1);

	function updatePrice(amount: number) {
		setSellingPrice((currentPrice) =>
			Math.max(1, Number((currentPrice + amount).toFixed(2))),
		);
	}

	function updatePromotion(amount: number) {
		setPromotionRate((currentRate) =>
			Math.min(Math.max(currentRate + amount, 0), 0.5),
		);
	}

	function runSimulation() {
		setSimulation(
			simulateCustomers({
				customerCount,
				product: {
					category: "laticinios",
					marketPrice,
					name: "Leite",
					necessity: 86,
					promotionRate,
					sellingPrice: sellingPrice * (1 - promotionRate),
				},
				seed,
				storeReputation: 62,
			}),
		);
		setSeed((currentSeed) => currentSeed + 1);
	}

	function renderDecision({
		item,
	}: LegendListRenderItemProps<PurchaseDecision>) {
		return <DecisionRow decision={item} />;
	}

	return (
		<LegendList
			ListHeaderComponent={
				<View style={[styles.header, { paddingTop: insets.top + 12 }]}>
					<Text style={styles.eyebrow}>LABORATÓRIO DE ECONOMIA</Text>
					<Text style={styles.title}>Simulador de clientes</Text>
					<Text style={styles.subtitle}>
						Teste como preço, promoção e perfis de cliente impactam suas vendas.
					</Text>

					<View style={styles.productCard}>
						<View style={styles.productVisual}>
							<Text style={styles.productEmoji}>🥛</Text>
						</View>
						<View>
							<Text style={styles.productName}>Leite integral</Text>
							<Text style={styles.marketPrice}>
								Mercado: R$ {marketPrice.toFixed(2)}
							</Text>
						</View>
					</View>

					<ControlRow
						label="Preço de venda"
						value={`R$ ${sellingPrice.toFixed(2)}`}
						onDecrease={() => updatePrice(-0.5)}
						onIncrease={() => updatePrice(0.5)}
					/>
					<ControlRow
						label="Promoção"
						value={`${Math.round(promotionRate * 100)}%`}
						onDecrease={() => updatePromotion(-0.1)}
						onIncrease={() => updatePromotion(0.1)}
					/>

					<View style={styles.priceInsight}>
						<Text style={styles.priceInsightLabel}>PREÇO EFETIVO</Text>
						<Text style={styles.priceInsightValue}>
							R$ {(sellingPrice * (1 - promotionRate)).toFixed(2)}
						</Text>
						<Text style={styles.priceInsightDescription}>
							{formatDifference(
								sellingPrice * (1 - promotionRate),
								marketPrice,
							)}{" "}
							em relação ao mercado
						</Text>
					</View>

					<Pressable onPress={runSimulation} style={styles.simulateButton}>
						<Text style={styles.simulateButtonText}>
							Simular {customerCount} clientes
						</Text>
					</Pressable>

					{simulation ? (
						<SimulationSummary simulation={simulation} />
					) : (
						<EmptyState />
					)}
					{simulation && (
						<Text style={styles.sectionTitle}>Decisões recentes</Text>
					)}
				</View>
			}
			contentContainerStyle={styles.content}
			data={simulation?.decisions.slice(0, 12) ?? []}
			estimatedItemSize={64}
			keyExtractor={(decision) => decision.customer.id}
			renderItem={renderDecision}
		/>
	);
}

function ControlRow({
	label,
	value,
	onDecrease,
	onIncrease,
}: {
	label: string;
	value: string;
	onDecrease: () => void;
	onIncrease: () => void;
}) {
	return (
		<View style={styles.controlRow}>
			<Text style={styles.controlLabel}>{label}</Text>
			<View style={styles.stepper}>
				<Pressable onPress={onDecrease} style={styles.stepperButton}>
					<Text style={styles.stepperButtonText}>−</Text>
				</Pressable>
				<Text style={styles.stepperValue}>{value}</Text>
				<Pressable onPress={onIncrease} style={styles.stepperButton}>
					<Text style={styles.stepperButtonText}>+</Text>
				</Pressable>
			</View>
		</View>
	);
}

function SimulationSummary({ simulation }: { simulation: SimulationResult }) {
	return (
		<View style={styles.summary}>
			<Text style={styles.summaryTitle}>Resultado da simulação</Text>
			<View style={styles.metricRow}>
				<Metric
					label="Conversão"
					value={`${Math.round(simulation.conversionRate * 100)}%`}
				/>
				<Metric label="Unidades" value={simulation.totalUnits.toString()} />
				<Metric label="Receita" value={`R$ ${simulation.revenue.toFixed(0)}`} />
			</View>
			<Text style={styles.summaryNote}>
				Chance média de compra: {Math.round(simulation.averageChance * 100)}%
			</Text>
		</View>
	);
}

function Metric({ label, value }: { label: string; value: string }) {
	return (
		<View style={styles.metric}>
			<Text style={styles.metricValue}>{value}</Text>
			<Text style={styles.metricLabel}>{label}</Text>
		</View>
	);
}

function EmptyState() {
	return (
		<View style={styles.emptyState}>
			<Text style={styles.emptyStateIcon}>🧠</Text>
			<Text style={styles.emptyStateText}>
				Rode uma simulação para analisar as decisões dos clientes.
			</Text>
		</View>
	);
}

function DecisionRow({ decision }: { decision: PurchaseDecision }) {
	const priceDifference = `${decision.marketDifference >= 0 ? "+" : ""}${Math.round(decision.marketDifference * 100)}%`;

	return (
		<View style={styles.decisionRow}>
			<View
				style={[
					styles.decisionIcon,
					decision.didBuy ? styles.purchaseIcon : styles.skipIcon,
				]}
			>
				<Text>{decision.didBuy ? "✓" : "×"}</Text>
			</View>
			<View style={styles.decisionCopy}>
				<Text style={styles.decisionTitle}>
					{formatArchetype(decision.customer.archetype)} ·{" "}
					{formatMood(decision.customer.mood)}
				</Text>
				<Text style={styles.decisionDescription}>
					{decision.didBuy
						? `Comprou ${decision.quantity} unid.`
						: `Recusou com score ${Math.round(decision.score)}`}
				</Text>
			</View>
			<Text style={styles.decisionPrice}>{priceDifference}</Text>
		</View>
	);
}

function formatDifference(price: number, market: number) {
	const difference = ((price - market) / market) * 100;
	const prefix = difference >= 0 ? "+" : "";
	return `${prefix}${Math.round(difference)}%`;
}

function formatArchetype(archetype: PurchaseDecision["customer"]["archetype"]) {
	return {
		economico: "Econômico",
		familia: "Família",
		impulsivo: "Impulsivo",
		normal: "Normal",
		premium: "Premium",
	}[archetype];
}

function formatMood(mood: PurchaseDecision["customer"]["mood"]) {
	return {
		calmo: "calmo",
		"com-pressa": "com pressa",
		estressado: "estressado",
		feliz: "feliz",
	}[mood];
}

const styles = StyleSheet.create((theme) => ({
	content: {
		paddingBottom: theme.gap(12),
		backgroundColor: theme.colors["neutral-50"],
	},
	header: {
		paddingHorizontal: theme.gap(2),
		paddingBottom: theme.gap(2.5),
	},
	eyebrow: {
		color: theme.colors["blue-600"],
		fontSize: 11,
		fontWeight: "700",
		letterSpacing: 0.8,
	},
	title: {
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-800"],
		fontSize: 27,
		fontWeight: "700",
	},
	subtitle: {
		marginTop: theme.gap(0.75),
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		lineHeight: theme.gap(2.25),
	},
	productCard: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
		marginTop: theme.gap(2),
		padding: theme.gap(1.5),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	productVisual: {
		width: theme.gap(6.5),
		height: theme.gap(6.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-50"],
	},
	productEmoji: {
		fontSize: 30,
	},
	productName: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	marketPrice: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
	},
	controlRow: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		marginTop: theme.gap(1.25),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	controlLabel: {
		color: theme.colors["neutral-700"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	stepper: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
	},
	stepperButton: {
		width: theme.gap(3.5),
		height: theme.gap(3.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	stepperButtonText: {
		color: theme.colors["blue-600"],
		fontSize: 19,
		fontWeight: "700",
	},
	stepperValue: {
		minWidth: theme.gap(7),
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
		textAlign: "center",
	},
	priceInsight: {
		marginTop: theme.gap(1.25),
		padding: theme.gap(1.5),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-800"],
	},
	priceInsightLabel: {
		color: theme.colors["blue-200"],
		fontSize: 10,
		fontWeight: "700",
		letterSpacing: 0.7,
	},
	priceInsightValue: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-0"],
		fontSize: 24,
		fontWeight: "700",
	},
	priceInsightDescription: {
		marginTop: theme.gap(0.25),
		color: theme.colors["blue-100"],
		fontSize: 12,
	},
	simulateButton: {
		alignItems: "center",
		justifyContent: "center",
		height: theme.gap(5.75),
		marginTop: theme.gap(1.5),
		borderRadius: theme.gap(3),
		backgroundColor: theme.colors["blue-500"],
	},
	simulateButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	summary: {
		marginTop: theme.gap(2),
		padding: theme.gap(1.5),
		borderWidth: 1,
		borderColor: theme.colors["green-100"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["green-50"],
	},
	summaryTitle: {
		color: theme.colors["green-600"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	metricRow: {
		flexDirection: "row",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1.25),
	},
	metric: {
		flex: 1,
		alignItems: "center",
		paddingVertical: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	metricValue: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	metricLabel: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "600",
	},
	summaryNote: {
		marginTop: theme.gap(1.25),
		color: theme.colors["green-600"],
		fontSize: 12,
		textAlign: "center",
	},
	emptyState: {
		alignItems: "center",
		marginTop: theme.gap(2),
		padding: theme.gap(2),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	emptyStateIcon: {
		fontSize: 28,
	},
	emptyStateText: {
		marginTop: theme.gap(0.75),
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		textAlign: "center",
	},
	sectionTitle: {
		marginTop: theme.gap(2.5),
		marginBottom: theme.gap(0.75),
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	decisionRow: {
		flexDirection: "row",
		alignItems: "center",
		marginHorizontal: theme.gap(2),
		marginTop: theme.gap(0.75),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	decisionIcon: {
		width: theme.gap(3.5),
		height: theme.gap(3.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.75),
	},
	purchaseIcon: {
		backgroundColor: theme.colors["green-100"],
	},
	skipIcon: {
		backgroundColor: theme.colors["red-100"],
	},
	decisionCopy: {
		flex: 1,
		marginLeft: theme.gap(1),
	},
	decisionTitle: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	decisionDescription: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-500"],
		fontSize: 11,
	},
	decisionPrice: {
		color: theme.colors["amber-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
}));
