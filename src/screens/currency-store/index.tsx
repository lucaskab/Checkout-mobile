import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { router } from "expo-router";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { CurrencyPack } from "@/@types/currency-purchase";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { currencyPackSections, currencyPacks } from "@/data/currency-packs";
import { getCurrencySectionIcon } from "@/data/game-icon-assets";
import { useGameStore } from "@/stores/game-store";
import { CurrencyPackCard } from "./components/currency-pack-card";
import { useCurrencyStore } from "./use-currency-store";

type CurrencyPackSection = (typeof currencyPackSections)[number];

type CurrencyStoreListItem =
	| { id: string; section: CurrencyPackSection; type: "section" }
	| { id: string; pack: CurrencyPack; type: "pack" };

const listItems: CurrencyStoreListItem[] = currencyPackSections.flatMap(
	(section) => [
		{ id: `section-${section.category}`, section, type: "section" },
		...currencyPacks
			.filter((pack) => pack.category === section.category)
			.map((pack) => ({ id: pack.id, pack, type: "pack" }) as const),
	],
);

export function CurrencyStoreScreen() {
	const coins = useGameStore((state) => state.coins);
	const diamonds = useGameStore((state) => state.logistics.premiumCurrency);
	const {
		availableProductCount,
		feedback,
		loadProducts,
		products,
		purchase,
		purchasingProductId,
		status,
		totalProductCount,
	} = useCurrencyStore();

	function renderItem({
		item,
	}: LegendListRenderItemProps<CurrencyStoreListItem>) {
		if (item.type === "section") {
			return (
				<View style={styles.sectionHeader}>
					<GameIcon
						icon={getCurrencySectionIcon(item.section.category)}
						style={styles.sectionEmoji}
					/>
					<View style={styles.sectionCopy}>
						<Text style={styles.sectionTitle}>{item.section.title}</Text>
						<Text style={styles.sectionDescription}>
							{item.section.description}
						</Text>
					</View>
				</View>
			);
		}

		const product = products[item.pack.productId];

		return (
			<CurrencyPackCard
				canPurchase={Boolean(product) && status === "ready"}
				isPurchasing={purchasingProductId === item.pack.productId}
				onPurchase={purchase}
				pack={item.pack}
				price={product?.priceString ?? item.pack.fallbackPrice}
			/>
		);
	}

	return (
		<LegendList
			contentContainerStyle={styles.content}
			data={listItems}
			estimatedItemSize={170}
			extraData={{
				feedback,
				products,
				purchasingProductId,
				status,
			}}
			keyExtractor={(item) => item.id}
			ListFooterComponent={
				<Text style={styles.footerText}>
					Os valores cobrados são os exibidos pela App Store ou Google Play. As
					compras desta tela são consumíveis.
				</Text>
			}
			ListHeaderComponent={
				<View>
					<Pressable onPress={router.back} style={styles.backButton}>
						<Text style={styles.backIcon}>‹</Text>
						<Text style={styles.backText}>Voltar</Text>
					</Pressable>

					<View style={styles.hero}>
						<GameIcon icon="bank" style={styles.heroEmoji} />
						<View style={styles.heroCopy}>
							<Text style={styles.heroTitle}>Banco do Mercado</Text>
							<Text style={styles.heroDescription}>
								Reforce o caixa e acelere as próximas melhorias.
							</Text>
						</View>
					</View>

					<View style={styles.balanceRow}>
						<BalanceCard
							icon="coin"
							label="Moedas atuais"
							value={coins.toLocaleString("pt-BR")}
							variant="coin"
						/>
						<BalanceCard
							icon="diamond"
							label="Diamantes atuais"
							value={diamonds.toLocaleString("pt-BR")}
							variant="gem"
						/>
					</View>

					{status !== "ready" && (
						<View style={styles.storeNotice}>
							<Text style={styles.noticeTitle}>
								{status === "loading"
									? "Carregando produtos..."
									: status === "missing-configuration"
										? "RevenueCat ainda não configurado"
										: "Produtos indisponíveis"}
							</Text>
							<Text style={styles.noticeDescription}>
								{status === "missing-configuration"
									? "Adicione as chaves públicas do RevenueCat para habilitar as compras."
									: status === "unavailable"
										? "Confira se os IDs dos produtos estão ativos nas lojas e no RevenueCat."
										: "Buscando os preços da sua loja..."}
							</Text>
							{status !== "loading" && (
								<GameButton
									label="Tentar novamente"
									onPress={loadProducts}
									size="small"
									variant="secondary"
								/>
							)}
						</View>
					)}

					{status === "ready" && availableProductCount < totalProductCount && (
						<Text style={styles.partialNotice}>
							{availableProductCount}/{totalProductCount} produtos configurados
							na loja.
						</Text>
					)}

					{feedback && (
						<View
							style={[
								styles.feedback,
								feedback.kind === "error" && styles.errorFeedback,
							]}
						>
							<GameIcon
								icon={feedback.kind === "success" ? "success" : "warning"}
								style={styles.feedbackEmoji}
							/>
							<Text style={styles.feedbackText}>{feedback.message}</Text>
						</View>
					)}
				</View>
			}
			renderItem={renderItem}
		/>
	);
}

function BalanceCard({
	icon,
	label,
	value,
	variant,
}: {
	icon: "coin" | "diamond";
	label: string;
	value: string;
	variant: "coin" | "gem";
}) {
	return (
		<View style={[styles.balanceCard, styles.balanceCardVariant(variant)]}>
			<GameIcon icon={icon} style={styles.balanceEmoji} />
			<View style={styles.balanceCopy}>
				<Text style={styles.balanceValue}>{value}</Text>
				<Text style={styles.balanceLabel}>{label}</Text>
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	content: {
		paddingBottom: theme.gap(4),
		backgroundColor: theme.colors["neutral-50"],
	},
	backButton: {
		flexDirection: "row",
		alignItems: "center",
		alignSelf: "flex-start",
		gap: theme.gap(0.5),
		marginHorizontal: theme.gap(1.5),
		marginTop: theme.gap(1.25),
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-100"],
	},
	backIcon: {
		color: theme.colors["neutral-700"],
		fontSize: 23,
		lineHeight: 20,
	},
	backText: {
		color: theme.colors["neutral-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	hero: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.25),
		margin: theme.gap(1.5),
		marginBottom: theme.gap(1),
		padding: theme.gap(1.5),
		borderWidth: 2,
		borderBottomWidth: 5,
		borderColor: theme.colors["green-500"],
		borderBottomColor: theme.colors["green-600"],
		borderRadius: theme.gap(2.25),
		backgroundColor: theme.colors["green-50"],
	},
	heroEmoji: { width: 52, height: 52 },
	heroCopy: { flex: 1 },
	heroTitle: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 22,
		fontWeight: "700",
	},
	heroDescription: {
		marginTop: 2,
		color: theme.colors["neutral-600"],
		fontSize: theme.fonts.size.small,
	},
	balanceRow: {
		flexDirection: "row",
		gap: theme.gap(0.75),
		marginHorizontal: theme.gap(1.5),
		marginBottom: theme.gap(1),
	},
	balanceCard: {
		flex: 1,
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		padding: theme.gap(1),
		borderWidth: 1,
		borderRadius: theme.gap(1.5),
	},
	balanceCardVariant: (variant: "coin" | "gem") => ({
		borderColor:
			variant === "coin"
				? theme.colors["amber-200"]
				: theme.colors["violet-400"],
		backgroundColor:
			variant === "coin" ? theme.colors["amber-50"] : theme.colors["violet-50"],
	}),
	balanceEmoji: { width: 28, height: 28 },
	balanceCopy: { flex: 1 },
	balanceValue: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	balanceLabel: {
		marginTop: 1,
		color: theme.colors["neutral-500"],
		fontSize: 9,
		fontWeight: "600",
	},
	storeNotice: {
		gap: theme.gap(0.75),
		marginHorizontal: theme.gap(1.5),
		marginBottom: theme.gap(1),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-50"],
	},
	noticeTitle: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	noticeDescription: {
		color: theme.colors["neutral-600"],
		fontSize: 11,
		lineHeight: theme.gap(1.75),
	},
	partialNotice: {
		marginHorizontal: theme.gap(1.5),
		marginBottom: theme.gap(1),
		padding: theme.gap(1),
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["amber-50"],
		color: theme.colors["amber-600"],
		fontSize: 11,
		fontWeight: "700",
	},
	feedback: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginHorizontal: theme.gap(1.5),
		marginBottom: theme.gap(1),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["green-100"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["green-50"],
	},
	errorFeedback: {
		borderColor: theme.colors["red-200"],
		backgroundColor: theme.colors["red-50"],
	},
	feedbackEmoji: { width: 22, height: 22 },
	feedbackText: {
		flex: 1,
		color: theme.colors["neutral-700"],
		fontSize: 11,
		fontWeight: "600",
	},
	sectionHeader: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginHorizontal: theme.gap(1.5),
		paddingTop: theme.gap(1.5),
		paddingBottom: theme.gap(0.75),
	},
	sectionEmoji: { width: 32, height: 32 },
	sectionCopy: { flex: 1 },
	sectionTitle: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	sectionDescription: {
		marginTop: 1,
		color: theme.colors["neutral-500"],
		fontSize: 11,
	},
	footerText: {
		marginHorizontal: theme.gap(2),
		marginTop: theme.gap(1),
		color: theme.colors["neutral-500"],
		fontSize: 10,
		lineHeight: theme.gap(1.5),
		textAlign: "center",
	},
}));
