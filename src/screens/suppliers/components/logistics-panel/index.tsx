import { useEffect, useState } from "react";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getNextSupplierOrderSlotUpgrade } from "@/data/supplier-capacity";
import { getSupplierOrderStatus } from "@/services/logistics";
import { useGameStore } from "@/stores/game-store";

export function LogisticsPanel() {
	const { openBottomSheet } = useBottomSheet();
	const logistics = useGameStore((state) => state.logistics);
	const [currentTime, setCurrentTime] = useState(Date.now());
	const activeOrders = logistics.orders.filter(
		(order) => getSupplierOrderStatus(order, currentTime) !== "entregue",
	);

	useEffect(() => {
		if (activeOrders.length === 0) {
			return;
		}

		const interval = setInterval(() => setCurrentTime(Date.now()), 1_000);

		return () => clearInterval(interval);
	}, [activeOrders.length]);

	return (
		<Pressable
			onPress={() => openBottomSheet(<LogisticsSheet />)}
			style={styles.trigger}
		>
			<View style={styles.triggerIcon}>
				<GameIcon icon="deliveryTruck" style={styles.triggerEmoji} />
			</View>
			<View style={styles.triggerCopy}>
				<Text style={styles.triggerTitle}>Central logística</Text>
				<Text style={styles.triggerSubtitle}>
					{activeOrders.length}/{logistics.supplierOrderSlots} pedidos em
					andamento
				</Text>
			</View>
			<View style={styles.valueRow}>
				<GameIcon icon="diamond" style={styles.valueIcon} />
				<Text style={styles.triggerValue}>{logistics.premiumCurrency}</Text>
			</View>
		</Pressable>
	);
}

function LogisticsSheet() {
	const coins = useGameStore((state) => state.coins);
	const activateLogisticsBoost = useGameStore(
		(state) => state.activateLogisticsBoost,
	);
	const logistics = useGameStore((state) => state.logistics);
	const marketLevel = useGameStore((state) => state.market.level);
	const upgradeSupplierOrderSlots = useGameStore(
		(state) => state.upgradeSupplierOrderSlots,
	);
	const [feedback, setFeedback] = useState<string | null>(null);
	const nextUpgrade = getNextSupplierOrderSlotUpgrade(
		logistics.supplierOrderSlots,
	);

	function activateBoost() {
		activateLogisticsBoost();
	}

	function upgradeSlots(currency: "coins" | "diamonds") {
		if (!nextUpgrade) {
			return;
		}

		if (upgradeSupplierOrderSlots(currency)) {
			setFeedback(
				`Agora você pode manter ${nextUpgrade.slots} pedidos ativos.`,
			);
			return;
		}

		setFeedback(
			marketLevel < nextUpgrade.playerLevel
				? `Alcance o nível ${nextUpgrade.playerLevel} para liberar mais um pedido.`
				: currency === "coins"
					? "Você não tem moedas suficientes para este upgrade."
					: "Você não tem diamantes suficientes para este upgrade.",
		);
	}

	return (
		<View style={styles.sheet}>
			<Text style={styles.sheetTitle}>Central logística</Text>
			<Text style={styles.sheetSubtitle}>
				Acelere entregas sem remover a importância do planejamento.
			</Text>
			<View style={styles.balanceRow}>
				<View style={styles.valueRow}>
					<GameIcon icon="diamond" style={styles.valueIcon} />
					<Text style={styles.balanceText}>{logistics.premiumCurrency}</Text>
				</View>
				<View style={styles.valueRow}>
					<GameIcon icon="ticket" style={styles.valueIcon} />
					<Text style={styles.balanceText}>{logistics.emergencyTokens}</Text>
				</View>
			</View>
			<LogisticsOption
				description="Pedidos novos chegam 30% mais rápido por 15 minutos."
				onPress={activateBoost}
				title="Turbo logística · 3 diamantes"
			/>
			<View style={styles.capacityCard}>
				<View style={styles.capacityCopy}>
					<Text style={styles.optionTitle}>Pedidos simultâneos</Text>
					<Text style={styles.optionDescription}>
						Você pode manter {logistics.supplierOrderSlots} pedidos ativos ao
						mesmo tempo.
					</Text>
				</View>
				<Text style={styles.capacityValue}>{logistics.supplierOrderSlots}</Text>
			</View>
			{nextUpgrade && (
				<>
					<Text style={styles.upgradeDescription}>
						Próximo slot: {nextUpgrade.slots} pedidos · requer nível{" "}
						{nextUpgrade.playerLevel}
					</Text>
					<View style={styles.upgradeActions}>
						<GameButton
							disabled={
								marketLevel < nextUpgrade.playerLevel ||
								coins < nextUpgrade.coinCost
							}
							icon="coin"
							label={nextUpgrade.coinCost.toLocaleString("pt-BR")}
							onPress={() => upgradeSlots("coins")}
							size="small"
							style={styles.upgradeButton}
							variant="coin"
						/>
						<GameButton
							disabled={
								marketLevel < nextUpgrade.playerLevel ||
								logistics.premiumCurrency < nextUpgrade.diamondCost
							}
							icon="diamond"
							label={nextUpgrade.diamondCost.toString()}
							onPress={() => upgradeSlots("diamonds")}
							size="small"
							style={styles.upgradeButton}
							variant="gem"
						/>
					</View>
				</>
			)}
			{feedback && <Text style={styles.feedback}>{feedback}</Text>}
		</View>
	);
}

type LogisticsOptionProps = {
	description: string;
	onPress: () => void;
	title: string;
};

function LogisticsOption({
	description,
	onPress,
	title,
}: LogisticsOptionProps) {
	return (
		<Pressable onPress={onPress} style={styles.option}>
			<View style={styles.optionCopy}>
				<Text style={styles.optionTitle}>{title}</Text>
				<Text style={styles.optionDescription}>{description}</Text>
			</View>
			<Text style={styles.optionArrow}>›</Text>
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	trigger: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginTop: theme.gap(1.25),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["blue-50"],
	},
	triggerIcon: {
		width: theme.gap(4.5),
		height: theme.gap(4.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	triggerEmoji: {
		width: 32,
		height: 32,
	},
	triggerCopy: {
		flex: 1,
	},
	triggerTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	triggerSubtitle: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 11,
		fontWeight: "600",
	},
	triggerValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	valueRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	valueIcon: {
		width: 18,
		height: 18,
	},
	sheet: {
		gap: theme.gap(1),
		paddingHorizontal: theme.gap(2),
		paddingBottom: theme.gap(3),
	},
	sheetTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	sheetSubtitle: {
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		lineHeight: theme.gap(2),
	},
	balanceRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginBottom: theme.gap(0.5),
	},
	balanceText: {
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	option: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	optionCopy: {
		flex: 1,
	},
	optionTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	optionDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	capacityCard: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	capacityCopy: {
		flex: 1,
	},
	capacityValue: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.large,
		fontWeight: "800",
	},
	upgradeDescription: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	upgradeActions: {
		flexDirection: "row",
		gap: theme.gap(0.75),
	},
	upgradeButton: {
		flex: 1,
	},
	feedback: {
		color: theme.colors["green-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	optionArrow: {
		color: theme.colors["blue-500"],
		fontSize: 26,
		fontWeight: "400",
	},
}));
