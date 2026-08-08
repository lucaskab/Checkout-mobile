import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { Pressable, View } from "react-native";
import Animated, {
	FadeInDown,
	useAnimatedStyle,
	useSharedValue,
	withTiming,
} from "react-native-reanimated";
import { StyleSheet } from "react-native-unistyles";
import type {
	ProductionJob,
	ProductionRecipe,
	ProductionSector,
} from "@/@types/production";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { getProductionSectorProductId } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import {
	getProductionSector,
	getSectorRecipes,
} from "@/data/production-sectors";
import { getActiveGameEventEffects } from "@/services/game-events";
import {
	getProductionDiamondCost,
	getProductionEconomy,
	getProductionProgress,
	getProductionRemainingTime,
	getRecipeProfitMargin,
} from "@/services/production";
import { useGameStore } from "@/stores/game-store";

type SectorDetailScreenProps = {
	sectorId: string;
};

export function SectorDetailScreen({ sectorId }: SectorDetailScreenProps) {
	const sector = getProductionSector(sectorId);

	if (!sector) {
		return (
			<View style={styles.notFound}>
				<GameIcon icon="construction" style={styles.notFoundEmoji} />
				<Text style={styles.notFoundTitle}>Setor não encontrado</Text>
				<Pressable onPress={() => router.back()} style={styles.backButton}>
					<Text style={styles.backButtonText}>Voltar aos setores</Text>
				</Pressable>
			</View>
		);
	}

	return <UnlockedSectorScreen sector={sector} />;
}

function UnlockedSectorScreen({ sector }: { sector: ProductionSector }) {
	const [currentTime, setCurrentTime] = useState(Date.now());
	const [feedback, setFeedback] = useState<string | null>(null);
	const diamonds = useGameStore((state) => state.logistics.premiumCurrency);
	const events = useGameStore((state) => state.events);
	const inventory = useGameStore((state) => state.inventory);
	const level = useGameStore((state) => state.market.level);
	const jobs = useGameStore((state) => state.production.jobs);
	const finishProductionNow = useGameStore(
		(state) => state.finishProductionNow,
	);
	const startProduction = useGameStore((state) => state.startProduction);
	const eventEffects = getActiveGameEventEffects(events);
	const recipes = getSectorRecipes(sector.id);
	const sectorJobs = jobs.filter((job) => job.sectorId === sector.id);
	const hasFreeSlot = sectorJobs.length < sector.slotCount;

	useEffect(() => {
		if (sectorJobs.length === 0) {
			return;
		}

		const interval = setInterval(() => setCurrentTime(Date.now()), 1_000);

		return () => clearInterval(interval);
	}, [sectorJobs.length]);

	function produce(recipe: ProductionRecipe) {
		const product = itemCatalog.find(
			(item) => item.id === recipe.outputProductId,
		);

		if (startProduction({ recipeId: recipe.id, sectorId: sector.id })) {
			setFeedback(`${product?.name} entrou na linha de produção.`);
			return;
		}

		setFeedback(
			hasFreeSlot
				? "Faltam ingredientes ou nível para iniciar esta receita."
				: "Todos os slots deste setor estão ocupados.",
		);
	}

	function finishNow(job: ProductionJob) {
		const cost = getProductionDiamondCost(job.endsAt - currentTime);

		if (finishProductionNow(job.id)) {
			setFeedback(`Produção concluída agora por ${cost} diamantes.`);
			return;
		}

		setFeedback("Você não possui diamantes suficientes.");
	}

	function renderRecipe({
		index,
		item: recipe,
	}: LegendListRenderItemProps<ProductionRecipe>) {
		const product = itemCatalog.find(
			(item) => item.id === recipe.outputProductId,
		);
		const isLocked = level < recipe.requiredLevel;
		const hasIngredients = recipe.ingredients.every(
			(ingredient) =>
				(inventory[ingredient.productId] ?? 0) >= ingredient.quantity,
		);
		const margin = getRecipeProfitMargin(recipe);
		const economy = getProductionEconomy(recipe);

		return (
			<Animated.View entering={FadeInDown.delay(index * 70).duration(300)}>
				<View style={[styles.recipeCard, getRecipeAccentStyle(sector.id)]}>
					<View style={styles.recipeHeader}>
						<View style={[styles.productEmojiFrame, getHeroStyle(sector.id)]}>
							{product && (
								<ProductImage
									productId={product.id}
									style={styles.productImage}
								/>
							)}
						</View>
						<View style={styles.recipeCopy}>
							<Text style={styles.recipeName}>{product?.name}</Text>
							<Text style={styles.recipeYield}>
								Rende {recipe.outputQuantity} unid. ·{" "}
								{getProductionRemainingTime(
									Date.now() +
										recipe.durationMs *
											eventEffects.productionDurationMultiplier,
									Date.now(),
								)}
							</Text>
						</View>
						{isLocked && (
							<View style={styles.recipeLock}>
								<Text style={styles.recipeLockText}>
									Nível {recipe.requiredLevel}
								</Text>
							</View>
						)}
					</View>

					<View style={styles.rewardsRow}>
						<View style={styles.rewardChip}>
							<Text style={styles.rewardLabel}>MARGEM</Text>
							<Text style={styles.profitValue}>+{margin}%</Text>
						</View>
						<View style={styles.rewardChip}>
							<Text style={styles.rewardLabel}>XP / VENDA</Text>
							<Text style={styles.xpValue}>{product?.xpPerSale} XP</Text>
						</View>
						<View style={styles.rewardChip}>
							<Text style={styles.rewardLabel}>VENDA</Text>
							<View style={styles.inlineValueRow}>
								<GameIcon icon="coin" style={styles.inlineIcon} />
								<Text style={styles.saleValue}>{product?.sellingPrice}</Text>
							</View>
						</View>
					</View>

					<View style={styles.planningCard}>
						<View>
							<Text style={styles.planningLabel}>CUSTO POR UNIDADE</Text>
							<View style={styles.inlineValueRow}>
								<GameIcon icon="warehouse" style={styles.inlineIcon} />
								<Text style={styles.planningValue}>
									{Math.ceil(economy.productionUnitCost)} fabricando
								</Text>
							</View>
						</View>
						<Text style={styles.planningArrow}>→</Text>
						<View style={styles.planningSupplier}>
							<Text style={styles.planningLabel}>FORNECEDOR</Text>
							<View style={styles.inlineValueRow}>
								<GameIcon icon="deliveryTruck" style={styles.inlineIcon} />
								<Text style={styles.planningSupplierValue}>
									{economy.supplierUnitPrice}
								</Text>
							</View>
						</View>
						<View style={styles.savingsBadge}>
							<Text style={styles.savingsBadgeText}>
								−{economy.savingsPercent}%
							</Text>
						</View>
					</View>

					<Text style={styles.ingredientsTitle}>INGREDIENTES</Text>
					<View style={styles.ingredients}>
						{recipe.ingredients.map((ingredient) => {
							const ingredientProduct = itemCatalog.find(
								(item) => item.id === ingredient.productId,
							);
							const owned = inventory[ingredient.productId] ?? 0;
							const enough = owned >= ingredient.quantity;

							return (
								<View
									key={ingredient.productId}
									style={[
										styles.ingredient,
										!enough && styles.missingIngredient,
									]}
								>
									{ingredientProduct && (
										<ProductImage
											productId={ingredientProduct.id}
											style={styles.ingredientImage}
										/>
									)}
									<Text style={styles.ingredientText}>
										{ingredient.quantity}× {ingredientProduct?.name}
									</Text>
									<Text
										style={[
											styles.ownedAmount,
											!enough && styles.missingAmount,
										]}
									>
										{owned}
									</Text>
								</View>
							);
						})}
					</View>

					<Pressable
						disabled={isLocked || !hasIngredients || !hasFreeSlot}
						onPress={() => produce(recipe)}
						style={({ pressed }) => [
							styles.produceButton,
							getButtonStyle(sector.id),
							(isLocked || !hasIngredients || !hasFreeSlot) &&
								styles.disabledButton,
							pressed && styles.pressedButton,
						]}
					>
						<Text style={styles.produceButtonText}>
							{isLocked
								? `Libera no nível ${recipe.requiredLevel}`
								: !hasFreeSlot
									? "Slots ocupados"
									: !hasIngredients
										? "Ingredientes insuficientes"
										: `Fabricar ${recipe.outputQuantity} agora`}
						</Text>
					</Pressable>
				</View>
			</Animated.View>
		);
	}

	return (
		<LegendList
			contentContainerStyle={styles.content}
			data={recipes}
			estimatedItemSize={390}
			keyExtractor={(recipe) => recipe.id}
			ListHeaderComponent={
				<View>
					<View style={[styles.detailHero, getHeroStyle(sector.id)]}>
						<View style={styles.detailTopBar}>
							<Pressable onPress={() => router.back()} style={styles.heroBack}>
								<Text style={styles.heroBackText}>‹</Text>
							</Pressable>
							<Text style={styles.heroEyebrow}>SETOR ESPECIAL</Text>
							<View style={styles.heroLevel}>
								<Text style={styles.heroLevelText}>
									Nível {sector.requiredLevel}+
								</Text>
							</View>
						</View>
						<ProductImage
							productId={getProductionSectorProductId(sector.id)}
							style={styles.detailEmoji}
						/>
						<Text style={styles.detailTitle}>{sector.name}</Text>
						<Text style={styles.detailSubtitle}>{sector.description}</Text>
						<View style={styles.ambientRow}>
							<Text style={styles.ambientText}>
								{getAmbientCopy(sector.id)}
							</Text>
						</View>
					</View>

					<View style={styles.productionSection}>
						<View style={styles.sectionTitleRow}>
							<View>
								<Text style={styles.sectionTitle}>Linha de produção</Text>
								<Text style={styles.sectionDescription}>
									Produções continuam mesmo fora desta tela.
								</Text>
							</View>
							<Text style={styles.activeSlots}>
								{sectorJobs.length}/{sector.slotCount} ativos
							</Text>
						</View>

						<View style={styles.slots}>
							{Array.from({ length: sector.slotCount }, (_, slotIndex) => {
								const job = sectorJobs.find(
									(item) => item.slotIndex === slotIndex,
								);

								return (
									<ProductionSlot
										currentTime={currentTime}
										diamonds={diamonds}
										job={job}
										// biome-ignore lint/suspicious/noArrayIndexKey: slotIndex is the stable identity of this fixed production slot.
										key={slotIndex}
										onFinishNow={finishNow}
										slotIndex={slotIndex}
									/>
								);
							})}
						</View>
					</View>

					{feedback && (
						<Pressable
							onPress={() => setFeedback(null)}
							style={styles.feedback}
						>
							<Text style={styles.feedbackText}>{feedback}</Text>
							<Text style={styles.feedbackClose}>×</Text>
						</Pressable>
					)}

					<View style={styles.recipesHeader}>
						<View>
							<Text style={styles.sectionTitle}>Receitas do setor</Text>
							<Text style={styles.sectionDescription}>
								Mais XP significa uma margem percentual mais estratégica.
							</Text>
						</View>
						<Text style={styles.recipeCount}>{recipes.length}</Text>
					</View>
				</View>
			}
			renderItem={renderRecipe}
		/>
	);
}

type ProductionSlotProps = {
	currentTime: number;
	diamonds: number;
	job?: ProductionJob;
	onFinishNow: (job: ProductionJob) => void;
	slotIndex: number;
};

function ProductionSlot({
	currentTime,
	diamonds,
	job,
	onFinishNow,
	slotIndex,
}: ProductionSlotProps) {
	if (!job) {
		return (
			<View style={styles.emptySlot}>
				<View style={styles.emptySlotIcon}>
					<Text style={styles.emptySlotIconText}>＋</Text>
				</View>
				<View>
					<Text style={styles.emptySlotTitle}>Slot {slotIndex + 1}</Text>
					<Text style={styles.emptySlotText}>Escolha uma receita abaixo</Text>
				</View>
			</View>
		);
	}

	const product = itemCatalog.find((item) => item.id === job.outputProductId);
	const progress = getProductionProgress(job, currentTime);
	const diamondCost = getProductionDiamondCost(job.endsAt - currentTime);

	return (
		<View style={styles.activeSlot}>
			<View style={styles.activeSlotHeader}>
				{product && (
					<ProductImage productId={product.id} style={styles.activeSlotImage} />
				)}
				<View style={styles.activeSlotCopy}>
					<Text style={styles.activeSlotTitle}>{product?.name}</Text>
					<Text style={styles.activeSlotTime}>
						Pronto em {getProductionRemainingTime(job.endsAt, currentTime)}
					</Text>
				</View>
				<Text style={styles.progressLabel}>{Math.round(progress * 100)}%</Text>
			</View>
			<View style={styles.progressTrack}>
				<ProductionProgress progress={progress} />
			</View>
			<Pressable
				disabled={diamonds < diamondCost}
				onPress={() => onFinishNow(job)}
				style={[
					styles.instantButton,
					diamonds < diamondCost && styles.disabledInstantButton,
				]}
			>
				<View style={styles.instantButtonRow}>
					<GameIcon icon="lightning" style={styles.instantIcon} />
					<Text style={styles.instantButtonText}>Finalizar agora ·</Text>
					<GameIcon icon="diamond" style={styles.instantIcon} />
					<Text style={styles.instantButtonText}>{diamondCost}</Text>
				</View>
			</Pressable>
		</View>
	);
}

function ProductionProgress({ progress }: { progress: number }) {
	const animatedProgress = useSharedValue(progress);

	useEffect(() => {
		animatedProgress.value = withTiming(progress, { duration: 900 });
	}, [animatedProgress, progress]);

	const animatedStyle = useAnimatedStyle(() => ({
		height: "100%",
		width: `${animatedProgress.value * 100}%`,
	}));

	return (
		<Animated.View style={animatedStyle}>
			<View style={styles.progressFill} />
		</Animated.View>
	);
}

function getAmbientCopy(sectorId: ProductionSector["id"]) {
	switch (sectorId) {
		case "padaria":
			return "Fornos aquecidos · farinha fresca";
		case "queijaria":
			return "Câmara maturando · leite selecionado";
		case "acougue":
			return "Bancada preparada · defumador ativo";
		case "peixaria":
			return "Balcão a 2°C · frescor garantido";
	}
}

function getHeroStyle(sectorId: ProductionSector["id"]) {
	switch (sectorId) {
		case "padaria":
			return styles.bakeryHero;
		case "queijaria":
			return styles.cheeseHero;
		case "acougue":
			return styles.butcherHero;
		case "peixaria":
			return styles.fishHero;
	}
}

function getRecipeAccentStyle(sectorId: ProductionSector["id"]) {
	switch (sectorId) {
		case "padaria":
			return styles.bakeryRecipe;
		case "queijaria":
			return styles.cheeseRecipe;
		case "acougue":
			return styles.butcherRecipe;
		case "peixaria":
			return styles.fishRecipe;
	}
}

function getButtonStyle(sectorId: ProductionSector["id"]) {
	switch (sectorId) {
		case "padaria":
			return styles.bakeryButton;
		case "queijaria":
			return styles.cheeseButton;
		case "acougue":
			return styles.butcherButton;
		case "peixaria":
			return styles.fishButton;
	}
}

const styles = StyleSheet.create((theme) => ({
	content: {
		gap: theme.gap(1.25),
		paddingBottom: theme.gap(4),
		backgroundColor: theme.colors["neutral-50"],
	},
	notFound: {
		flex: 1,
		alignItems: "center",
		justifyContent: "center",
		padding: theme.gap(3),
		backgroundColor: theme.colors["neutral-50"],
	},
	notFoundEmoji: { width: 72, height: 72 },
	notFoundTitle: {
		fontFamily: theme.fonts.family.headline,
		marginTop: theme.gap(1),
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	backButton: {
		marginTop: theme.gap(2),
		paddingHorizontal: theme.gap(2),
		paddingVertical: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-500"],
	},
	backButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	detailHero: {
		paddingHorizontal: theme.gap(2),
		paddingTop: theme.gap(1.25),
		paddingBottom: theme.gap(2),
	},
	bakeryHero: { backgroundColor: theme.colors["amber-100"] },
	cheeseHero: { backgroundColor: theme.colors["violet-100"] },
	butcherHero: { backgroundColor: theme.colors["red-100"] },
	fishHero: { backgroundColor: theme.colors["blue-100"] },
	detailTopBar: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	heroBack: {
		width: theme.gap(4),
		height: theme.gap(4),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	heroBackText: {
		marginTop: -3,
		color: theme.colors["neutral-800"],
		fontSize: 30,
	},
	heroEyebrow: {
		color: theme.colors["neutral-600"],
		fontSize: 10,
		fontWeight: "700",
		letterSpacing: 1.2,
	},
	heroLevel: {
		fontFamily: theme.fonts.family.badge,
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-0"],
	},
	heroLevelText: {
		color: theme.colors["neutral-700"],
		fontSize: 9,
		fontWeight: "700",
	},
	detailEmoji: {
		alignSelf: "center",
		width: 82,
		height: 82,
		marginTop: theme.gap(1),
	},
	detailTitle: {
		fontFamily: theme.fonts.family.headline,
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-800"],
		fontSize: 27,
		fontWeight: "700",
		textAlign: "center",
	},
	detailSubtitle: {
		alignSelf: "center",
		maxWidth: 330,
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-700"],
		fontSize: theme.fonts.size.small,
		lineHeight: 18,
		textAlign: "center",
	},
	ambientRow: {
		alignSelf: "center",
		marginTop: theme.gap(1.25),
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(0.75),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	ambientText: {
		color: theme.colors["neutral-700"],
		fontSize: 10,
		fontWeight: "600",
	},
	productionSection: {
		paddingHorizontal: theme.gap(1.5),
		paddingTop: theme.gap(1.75),
	},
	sectionTitleRow: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	sectionTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	sectionDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
	},
	activeSlots: {
		color: theme.colors["blue-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	slots: { gap: theme.gap(0.75), marginTop: theme.gap(1) },
	emptySlot: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		padding: theme.gap(1),
		borderWidth: 1,
		borderStyle: "dashed",
		borderColor: theme.colors["neutral-300"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["neutral-0"],
	},
	emptySlotIcon: {
		width: theme.gap(4.5),
		height: theme.gap(4.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-100"],
	},
	emptySlotIconText: {
		color: theme.colors["neutral-500"],
		fontSize: 22,
	},
	emptySlotTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-700"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	emptySlotText: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
	},
	activeSlot: {
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["green-100"],
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["green-50"],
	},
	activeSlotHeader: { flexDirection: "row", alignItems: "center" },
	activeSlotImage: {
		width: theme.gap(6),
		height: theme.gap(6),
	},
	activeSlotCopy: { flex: 1, marginLeft: theme.gap(0.75) },
	activeSlotTitle: {
		fontFamily: theme.fonts.family.headline,
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	activeSlotTime: {
		marginTop: 2,
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "600",
	},
	progressLabel: {
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	progressTrack: {
		height: 7,
		overflow: "hidden",
		marginTop: theme.gap(0.75),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["green-100"],
	},
	progressFill: {
		height: "100%",
		width: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["green-500"],
	},
	instantButton: {
		alignSelf: "flex-start",
		marginTop: theme.gap(0.75),
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["violet-500"],
	},
	disabledInstantButton: { opacity: 0.4 },
	instantButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: 10,
		fontWeight: "700",
	},
	instantButtonRow: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.25),
	},
	instantIcon: {
		width: 18,
		height: 18,
	},
	feedback: {
		flexDirection: "row",
		alignItems: "center",
		marginHorizontal: theme.gap(1.5),
		marginTop: theme.gap(1.25),
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-600"],
	},
	feedbackText: {
		flex: 1,
		color: theme.colors["neutral-0"],
		fontSize: 11,
		fontWeight: "600",
	},
	feedbackClose: { color: theme.colors["blue-100"], fontSize: 18 },
	recipesHeader: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		paddingHorizontal: theme.gap(1.5),
		paddingTop: theme.gap(2),
		paddingBottom: theme.gap(0.75),
	},
	recipeCount: {
		fontFamily: theme.fonts.family.numberBold,
		minWidth: theme.gap(3),
		height: theme.gap(3),
		color: theme.colors["blue-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
		textAlign: "center",
		textAlignVertical: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["blue-100"],
	},
	recipeCard: {
		marginHorizontal: theme.gap(1.5),
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-0"],
	},
	bakeryRecipe: { borderColor: theme.colors["amber-200"] },
	cheeseRecipe: { borderColor: theme.colors["violet-100"] },
	butcherRecipe: { borderColor: theme.colors["red-200"] },
	fishRecipe: { borderColor: theme.colors["blue-200"] },
	recipeHeader: { flexDirection: "row", alignItems: "center" },
	productEmojiFrame: {
		width: theme.gap(5.5),
		height: theme.gap(5.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
	},
	productImage: {
		width: theme.gap(5),
		height: theme.gap(5),
	},
	recipeCopy: { flex: 1, marginLeft: theme.gap(1) },
	recipeName: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	recipeYield: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
		fontWeight: "600",
	},
	recipeLock: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	recipeLockText: {
		color: theme.colors["neutral-600"],
		fontSize: 9,
		fontWeight: "700",
	},
	rewardsRow: {
		flexDirection: "row",
		gap: theme.gap(0.5),
		marginTop: theme.gap(1),
	},
	rewardChip: {
		flex: 1,
		padding: theme.gap(0.75),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-50"],
	},
	planningCard: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["violet-100"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["violet-50"],
	},
	planningLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "700",
		letterSpacing: 0.4,
	},
	planningValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	inlineValueRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.25),
	},
	inlineIcon: {
		width: 17,
		height: 17,
	},
	planningArrow: {
		color: theme.colors["neutral-400"],
		fontSize: 16,
	},
	planningSupplier: {
		flex: 1,
	},
	planningSupplierValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["neutral-700"],
		fontSize: 10,
		fontWeight: "700",
	},
	savingsBadge: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["green-100"],
	},
	savingsBadgeText: {
		fontFamily: theme.fonts.family.badge,
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "800",
	},
	rewardLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 8,
		fontWeight: "700",
		letterSpacing: 0.4,
	},
	profitValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["green-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	xpValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["violet-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	saleValue: {
		fontFamily: theme.fonts.family.numberBold,
		marginTop: 2,
		color: theme.colors["amber-600"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	ingredientsTitle: {
		fontFamily: theme.fonts.family.headline,
		marginTop: theme.gap(1.25),
		color: theme.colors["neutral-500"],
		fontSize: 9,
		fontWeight: "700",
		letterSpacing: 0.8,
	},
	ingredients: { gap: theme.gap(0.5), marginTop: theme.gap(0.5) },
	ingredient: {
		flexDirection: "row",
		alignItems: "center",
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.5),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["green-50"],
	},
	missingIngredient: { backgroundColor: theme.colors["red-50"] },
	ingredientImage: {
		width: theme.gap(3.5),
		height: theme.gap(3.5),
	},
	ingredientText: {
		flex: 1,
		marginLeft: theme.gap(0.5),
		color: theme.colors["neutral-700"],
		fontSize: 10,
		fontWeight: "600",
	},
	ownedAmount: {
		fontFamily: theme.fonts.family.numberBold,
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	missingAmount: { color: theme.colors["red-500"] },
	produceButton: {
		alignItems: "center",
		marginTop: theme.gap(1.25),
		paddingVertical: theme.gap(1),
		borderRadius: theme.gap(1.25),
	},
	bakeryButton: { backgroundColor: theme.colors["amber-500"] },
	cheeseButton: { backgroundColor: theme.colors["violet-500"] },
	butcherButton: { backgroundColor: theme.colors["red-500"] },
	fishButton: { backgroundColor: theme.colors["blue-500"] },
	disabledButton: { backgroundColor: theme.colors["neutral-300"] },
	pressedButton: { opacity: 0.75 },
	produceButtonText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
}));
