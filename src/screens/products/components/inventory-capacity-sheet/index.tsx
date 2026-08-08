import { useState } from "react";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { ItemDefinition } from "@/@types/item";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import {
	getInventoryCapacity,
	getNextInventoryCapacityUpgrade,
} from "@/data/inventory-capacity";
import { useGameStore } from "@/stores/game-store";

type InventoryCapacitySheetProps = {
	product: ItemDefinition;
};

export function InventoryCapacitySheet({
	product,
}: InventoryCapacitySheetProps) {
	const { closeBottomSheet } = useBottomSheet();
	const coins = useGameStore((state) => state.coins);
	const inventory = useGameStore((state) => state.inventory);
	const inventoryCapacityLevels = useGameStore(
		(state) => state.inventoryCapacityLevels,
	);
	const marketLevel = useGameStore((state) => state.market.level);
	const upgradeInventoryCapacity = useGameStore(
		(state) => state.upgradeInventoryCapacity,
	);
	const [feedback, setFeedback] = useState<string | null>(null);
	const upgradeLevel = inventoryCapacityLevels[product.id] ?? 0;
	const capacity = getInventoryCapacity(product, upgradeLevel);
	const nextUpgrade = getNextInventoryCapacityUpgrade(upgradeLevel);
	const hasRequiredLevel = Boolean(
		nextUpgrade && marketLevel >= nextUpgrade.playerLevel,
	);
	const hasEnoughCoins = Boolean(nextUpgrade && coins >= nextUpgrade.coinCost);

	function upgradeCapacity() {
		if (upgradeInventoryCapacity(product.id) && nextUpgrade) {
			setFeedback(
				`Capacidade ampliada para ${getInventoryCapacity(product, upgradeLevel + 1)} unidades.`,
			);
			return;
		}

		setFeedback(
			nextUpgrade && marketLevel < nextUpgrade.playerLevel
				? `Alcance o nível ${nextUpgrade.playerLevel} para ampliar este estoque.`
				: "Você não tem moedas suficientes para esta ampliação.",
		);
	}

	return (
		<View style={styles.content}>
			<View style={styles.productHeader}>
				<ProductImage productId={product.id} style={styles.productImage} />
				<View style={styles.productCopy}>
					<Text style={styles.title}>Estoque de {product.name}</Text>
					<Text style={styles.description}>
						Escolha quais itens terão mais espaço no seu depósito.
					</Text>
				</View>
			</View>
			<View style={styles.capacityCard}>
				<View>
					<Text style={styles.capacityLabel}>Capacidade atual</Text>
					<Text style={styles.capacityValue}>
						{inventory[product.id] ?? 0} / {capacity} unidades
					</Text>
				</View>
				<GameIcon icon="package" style={styles.capacityIcon} />
			</View>
			{nextUpgrade ? (
				<View style={styles.upgradeCard}>
					<Text style={styles.upgradeTitle}>
						Amplie para {getInventoryCapacity(product, upgradeLevel + 1)}{" "}
						unidades
					</Text>
					<Text style={styles.upgradeDescription}>
						Disponível no nível {nextUpgrade.playerLevel}. Mais espaço para
						pedidos e produção.
					</Text>
					<Pressable
						disabled={!hasRequiredLevel || !hasEnoughCoins}
						onPress={upgradeCapacity}
						style={[
							styles.upgradeButton,
							(!hasRequiredLevel || !hasEnoughCoins) && styles.disabledButton,
						]}
					>
						<View style={styles.upgradeButtonContent}>
							<GameIcon icon="coin" style={styles.upgradeButtonIcon} />
							<Text style={styles.upgradeButtonText}>
								Ampliar por {nextUpgrade.coinCost.toLocaleString("pt-BR")}
							</Text>
						</View>
					</Pressable>
					{!hasRequiredLevel && (
						<Text style={styles.lockedText}>
							Faltam {nextUpgrade.playerLevel - marketLevel} nível
							{nextUpgrade.playerLevel - marketLevel === 1 ? "" : "is"}.
						</Text>
					)}
				</View>
			) : (
				<Text style={styles.maximumText}>
					Este item já está na capacidade máxima.
				</Text>
			)}
			{feedback && <Text style={styles.feedback}>{feedback}</Text>}
			<Pressable onPress={closeBottomSheet} style={styles.closeButton}>
				<Text style={styles.closeButtonText}>Concluir</Text>
			</Pressable>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		paddingHorizontal: theme.gap(2.75),
	},
	productHeader: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
	},
	productImage: {
		width: theme.gap(7),
		height: theme.gap(7),
	},
	productCopy: {
		flex: 1,
	},
	title: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large + 2,
		fontWeight: "700",
	},
	description: {
		marginTop: theme.gap(0.375),
		color: theme.colors["neutral-600"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	capacityCard: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		marginTop: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["blue-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-50"],
	},
	capacityLabel: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	capacityValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["blue-700"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	capacityIcon: {
		width: theme.gap(4),
		height: theme.gap(4),
	},
	upgradeCard: {
		marginTop: theme.gap(1.25),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["violet-100"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["violet-50"],
	},
	upgradeTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	upgradeDescription: {
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-600"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	upgradeButton: {
		alignItems: "center",
		justifyContent: "center",
		minHeight: theme.gap(4.75),
		marginTop: theme.gap(1.25),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["violet-500"],
	},
	disabledButton: {
		opacity: 0.45,
	},
	upgradeButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	upgradeButtonContent: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
	},
	upgradeButtonIcon: {
		width: theme.gap(2.5),
		height: theme.gap(2.5),
	},
	lockedText: {
		marginTop: theme.gap(0.75),
		color: theme.colors["violet-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	maximumText: {
		marginTop: theme.gap(1.25),
		color: theme.colors["green-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
		textAlign: "center",
	},
	feedback: {
		marginTop: theme.gap(1),
		color: theme.colors["green-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
		textAlign: "center",
	},
	closeButton: {
		alignItems: "center",
		justifyContent: "center",
		minHeight: theme.gap(5),
		marginTop: theme.gap(1),
		marginBottom: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(2.5),
	},
	closeButtonText: {
		color: theme.colors["neutral-700"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
}));
