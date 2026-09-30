import {
	LegendList,
	type LegendListRenderItemProps,
} from "@legendapp/list/react-native";
import { type ReactNode, useState } from "react";
import { Pressable, TextInput, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { ProductImage } from "@/components/product-image";
import { gameEvents } from "@/data/game-events";
import { type GameIconId, getGameEventIcon } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import { useGameStore } from "@/stores/game-store";

export function DevCheatSheet() {
	const [search, setSearch] = useState("");
	const { closeBottomSheet } = useBottomSheet();
	const coins = useGameStore((state) => state.coins);
	const diamonds = useGameStore((state) => state.logistics.premiumCurrency);
	const activeEvent = useGameStore((state) => state.events.activeEvent);
	const inventory = useGameStore((state) => state.inventory);
	const level = useGameStore((state) => state.market.level);
	const devAdjustCoins = useGameStore((state) => state.devAdjustCoins);
	const devAdjustDiamonds = useGameStore((state) => state.devAdjustDiamonds);
	const devAdjustInventory = useGameStore((state) => state.devAdjustInventory);
	const devActivateGameEvent = useGameStore(
		(state) => state.devActivateGameEvent,
	);
	const setMarketLevel = useGameStore((state) => state.setMarketLevel);
	const construction = useGameStore(
		(state) => state.marketExpansionConstruction,
	);
	const devFinishMarketExpansion = useGameStore(
		(state) => state.devFinishMarketExpansion,
	);
	const interiorBuilds = useGameStore((state) => state.interiorConstructions.length);
	const devFinishInteriorConstructions = useGameStore(
		(state) => state.devFinishInteriorConstructions,
	);
	const normalizedSearch = search.trim().toLocaleLowerCase("pt-BR");
	const products = normalizedSearch
		? itemCatalog.filter((product) =>
				product.name.toLocaleLowerCase("pt-BR").includes(normalizedSearch),
			)
		: itemCatalog;

	function renderEvent({
		item: event,
	}: LegendListRenderItemProps<(typeof gameEvents)[number]>) {
		const isActive =
			activeEvent?.eventId === event.id && activeEvent.endsAt > Date.now();
		const isPositive = event.kind === "positive";

		return (
			<Pressable
				accessibilityLabel={`Ativar evento ${event.name}`}
				onPress={() => devActivateGameEvent(event.id)}
				style={({ pressed }) => [
					styles.eventCard,
					isPositive ? styles.positiveEventCard : styles.negativeEventCard,
					isActive && styles.activeEventCard,
					pressed && styles.pressedEventCard,
				]}
			>
				<View style={styles.eventHeading}>
					<View style={styles.eventKind}>
						<GameIcon
							icon={getGameEventIcon(event.id)}
							style={styles.eventEmoji}
						/>
						<Text
							style={[
								styles.eventKindText,
								isPositive
									? styles.positiveEventText
									: styles.negativeEventText,
							]}
						>
							{isPositive ? "POSITIVO" : "NEGATIVO"}
						</Text>
					</View>
					{isActive && (
						<View style={styles.activeEventBadge}>
							<Text style={styles.activeEventBadgeText}>ATIVO</Text>
						</View>
					)}
				</View>
				<Text numberOfLines={1} style={styles.eventName}>
					{event.name}
				</Text>
				<Text numberOfLines={2} style={styles.eventEffect}>
					{event.effectLabel}
				</Text>
				<View style={styles.eventFooter}>
					<Text style={styles.eventDuration}>{event.durationMinutes} min</Text>
					<Text
						style={[
							styles.eventAction,
							isPositive ? styles.positiveEventText : styles.negativeEventText,
						]}
					>
						{isActive ? "Reativar" : "Ativar"}
					</Text>
				</View>
			</Pressable>
		);
	}

	function renderProduct({
		item: product,
	}: LegendListRenderItemProps<(typeof itemCatalog)[number]>) {
		return (
			<View style={styles.productRow}>
				<View style={styles.productEmojiFrame}>
					<ProductImage productId={product.id} style={styles.productImage} />
				</View>
				<View style={styles.productCopy}>
					<Text numberOfLines={1} style={styles.productName}>
						{product.name}
					</Text>
					<Text style={styles.productMeta}>
						ID {product.id} · nível {product.unlockLevel}
					</Text>
				</View>
				<CompactButton
					label="−10"
					onPress={() => devAdjustInventory(product.id, -10)}
				/>
				<CompactButton
					label="−1"
					onPress={() => devAdjustInventory(product.id, -1)}
				/>
				<Text style={styles.stockValue}>{inventory[product.id] ?? 0}</Text>
				<CompactButton
					label="+1"
					onPress={() => devAdjustInventory(product.id, 1)}
					positive
				/>
				<CompactButton
					label="+10"
					onPress={() => devAdjustInventory(product.id, 10)}
					positive
				/>
			</View>
		);
	}

	return (
		<View style={styles.sheet}>
			<View style={styles.header}>
				<View style={styles.headerIcon}>
					<GameIcon icon="toolbox" style={styles.headerEmoji} />
				</View>
				<View style={styles.headerCopy}>
					<View style={styles.titleRow}>
						<Text style={styles.title}>DEV Cheats</Text>
						<View style={styles.devBadge}>
							<Text style={styles.devBadgeText}>DEV ONLY</Text>
						</View>
					</View>
					<Text style={styles.description}>
						Altere o estado do jogo para validar níveis, economia e estoque.
					</Text>
				</View>
				<Pressable
					accessibilityLabel="Fechar menu de desenvolvimento"
					onPress={closeBottomSheet}
					style={styles.closeButton}
				>
					<Text style={styles.closeButtonText}>×</Text>
				</Pressable>
			</View>

			<LegendList
				contentContainerStyle={styles.content}
				data={products}
				estimatedItemSize={58}
				extraData={inventory}
				keyExtractor={(product) => product.id.toString()}
				keyboardShouldPersistTaps="handled"
				ListEmptyComponent={
					<View style={styles.emptyState}>
						<Text style={styles.emptyStateText}>
							Nenhum item encontrado para “{search}”.
						</Text>
					</View>
				}
				ListHeaderComponent={
					<View style={styles.headerContent}>
						<View style={styles.warning}>
							<GameIcon icon="warning" style={styles.warningIcon} />
							<Text style={styles.warningText}>
								Estas alterações são persistidas neste save local e não aparecem
								em builds de produção.
							</Text>
						</View>

						<CheatSection
							description="Toque em um evento para ativá-lo imediatamente. Isso substitui o evento atual e reinicia sua duração."
							title="Eventos"
						>
							<LegendList
								data={gameEvents}
								estimatedItemSize={184}
								extraData={activeEvent}
								horizontal
								keyExtractor={(event) => event.id}
								renderItem={renderEvent}
								showsHorizontalScrollIndicator={false}
								style={styles.eventsList}
							/>
						</CheatSection>

						<CheatSection
							description="Mudar o nível também recalcula exatamente os produtos liberados."
							title="Progressão"
						>
							<ValueControl
								icon="medal"
								label="Nível do jogador"
								onChange={(amount) => setMarketLevel(level + amount)}
								steps={[-5, -1, 1, 5]}
								value={level.toLocaleString("pt-BR")}
							/>
							<View style={styles.presetRow}>
								{[1, 5, 10, 16, 22].map((preset) => (
									<Pressable
										key={preset}
										onPress={() => setMarketLevel(preset)}
										style={[
											styles.presetButton,
											level === preset && styles.activePresetButton,
										]}
									>
										<Text
											style={[
												styles.presetText,
												level === preset && styles.activePresetText,
											]}
										>
											Lv. {preset}
										</Text>
									</Pressable>
								))}
							</View>
						</CheatSection>

						<CheatSection
							description="Termina na hora a obra da expansão em andamento, sem gastar diamantes."
							title="Obras"
						>
							<CompactButton
								label={
									construction
										? "Terminar obra agora"
										: "Nenhuma obra em andamento"
								}
								onPress={() => devFinishMarketExpansion()}
								positive={!!construction}
							/>
							<CompactButton
								label={
									interiorBuilds > 0
										? "Terminar obras internas"
										: "Nenhuma obra interna"
								}
								onPress={() => devFinishInteriorConstructions()}
								positive={interiorBuilds > 0}
							/>
						</CheatSection>

						<CheatSection
							description="Teste compras, melhorias e acelerações instantâneas."
							title="Economia"
						>
							<ValueControl
								icon="coin"
								label="Moedas"
								onChange={devAdjustCoins}
								steps={[-100_000, -1_000, 1_000, 100_000]}
								value={coins.toLocaleString("pt-BR")}
							/>
							<ValueControl
								icon="diamond"
								label="Diamantes"
								onChange={devAdjustDiamonds}
								steps={[-100, -10, 10, 100]}
								value={diamonds.toLocaleString("pt-BR")}
							/>
						</CheatSection>

						<CheatSection
							description="Procure um item e altere sua quantidade no estoque."
							title="Estoque"
						>
							<View style={styles.searchField}>
								<Text style={styles.searchIcon}>⌕</Text>
								<TextInput
									autoCapitalize="none"
									autoCorrect={false}
									onChangeText={setSearch}
									placeholder="Buscar item..."
									style={styles.searchInput}
									value={search}
								/>
								{search.length > 0 && (
									<Pressable onPress={() => setSearch("")}>
										<Text style={styles.clearSearch}>×</Text>
									</Pressable>
								)}
							</View>
						</CheatSection>
					</View>
				}
				renderItem={renderProduct}
				showsVerticalScrollIndicator={false}
				style={styles.scroll}
			/>
		</View>
	);
}

type CheatSectionProps = {
	children: ReactNode;
	description: string;
	title: string;
};

function CheatSection({ children, description, title }: CheatSectionProps) {
	return (
		<View style={styles.section}>
			<Text style={styles.sectionTitle}>{title}</Text>
			<Text style={styles.sectionDescription}>{description}</Text>
			<View style={styles.sectionContent}>{children}</View>
		</View>
	);
}

type ValueControlProps = {
	icon: GameIconId;
	label: string;
	onChange: (amount: number) => void;
	steps: number[];
	value: string;
};

function ValueControl({
	icon,
	label,
	onChange,
	steps,
	value,
}: ValueControlProps) {
	return (
		<View style={styles.valueCard}>
			<View style={styles.valueHeading}>
				<GameIcon icon={icon} style={styles.valueEmoji} />
				<View>
					<Text style={styles.valueLabel}>{label}</Text>
					<Text style={styles.value}>{value}</Text>
				</View>
			</View>
			<View style={styles.valueActions}>
				{steps.map((step) => (
					<Pressable
						key={step}
						onPress={() => onChange(step)}
						style={[
							styles.valueButton,
							step > 0 ? styles.addButton : styles.removeButton,
						]}
					>
						<Text
							style={[
								styles.valueButtonText,
								step > 0 ? styles.addButtonText : styles.removeButtonText,
							]}
						>
							{formatStep(step)}
						</Text>
					</Pressable>
				))}
			</View>
		</View>
	);
}

function CompactButton({
	label,
	onPress,
	positive = false,
}: {
	label: string;
	onPress: () => void;
	positive?: boolean;
}) {
	return (
		<Pressable
			onPress={onPress}
			style={[
				styles.compactButton,
				positive ? styles.compactAddButton : styles.compactRemoveButton,
			]}
		>
			<Text
				style={[
					styles.compactButtonText,
					positive ? styles.compactAddText : styles.compactRemoveText,
				]}
			>
				{label}
			</Text>
		</Pressable>
	);
}

function formatStep(step: number) {
	const absoluteStep = Math.abs(step);
	const sign = step > 0 ? "+" : "−";

	if (absoluteStep >= 1_000) {
		return `${sign}${absoluteStep / 1_000}K`;
	}

	return `${sign}${absoluteStep}`;
}

const styles = StyleSheet.create((theme) => ({
	sheet: {
		backgroundColor: theme.colors["neutral-0"],
	},
	header: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		paddingHorizontal: theme.gap(1.5),
		paddingBottom: theme.gap(1.25),
		borderBottomWidth: 1,
		borderBottomColor: theme.colors["neutral-150"],
	},
	headerIcon: {
		width: theme.gap(5),
		height: theme.gap(5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["violet-100"],
	},
	headerEmoji: { width: 34, height: 34 },
	headerCopy: { flex: 1 },
	titleRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
	},
	title: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	devBadge: {
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: 3,
		borderRadius: theme.gap(0.75),
		backgroundColor: theme.colors["violet-500"],
	},
	devBadgeText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "700",
		letterSpacing: 0.5,
	},
	description: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
		lineHeight: 14,
	},
	closeButton: {
		width: theme.gap(4),
		height: theme.gap(4),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-100"],
	},
	closeButtonText: {
		marginTop: -2,
		color: theme.colors["neutral-600"],
		fontSize: 24,
	},
	scroll: { maxHeight: 620 },
	content: {
		padding: theme.gap(1.5),
		paddingBottom: theme.gap(3),
	},
	headerContent: {
		gap: theme.gap(1.25),
		marginBottom: theme.gap(0.75),
	},
	warning: {
		flexDirection: "row",
		gap: theme.gap(0.75),
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["amber-50"],
	},
	warningIcon: { width: 24, height: 24 },
	warningText: {
		flex: 1,
		color: theme.colors["amber-600"],
		fontSize: 10,
		fontWeight: "600",
		lineHeight: 14,
	},
	section: {
		padding: theme.gap(1.25),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.75),
		backgroundColor: theme.colors["neutral-50"],
	},
	sectionTitle: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	sectionDescription: {
		marginTop: 2,
		color: theme.colors["neutral-500"],
		fontSize: 10,
		lineHeight: 14,
	},
	sectionContent: { gap: theme.gap(0.75), marginTop: theme.gap(1) },
	eventsList: {
		height: theme.gap(15),
	},
	eventCard: {
		width: theme.gap(22),
		height: theme.gap(14.5),
		marginRight: theme.gap(0.75),
		padding: theme.gap(1),
		borderWidth: 1,
		borderRadius: theme.gap(1.25),
	},
	positiveEventCard: {
		borderColor: theme.colors["green-100"],
		backgroundColor: theme.colors["green-50"],
	},
	negativeEventCard: {
		borderColor: theme.colors["red-200"],
		backgroundColor: theme.colors["red-50"],
	},
	activeEventCard: {
		borderWidth: 2,
		borderColor: theme.colors["violet-500"],
	},
	pressedEventCard: {
		opacity: 0.65,
	},
	eventHeading: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	eventKind: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
	},
	eventEmoji: {
		width: 28,
		height: 28,
	},
	eventKindText: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 7,
		fontWeight: "800",
		letterSpacing: 0.4,
	},
	positiveEventText: {
		color: theme.colors["green-600"],
	},
	negativeEventText: {
		color: theme.colors["red-600"],
	},
	activeEventBadge: {
		paddingHorizontal: theme.gap(0.5),
		paddingVertical: 2,
		borderRadius: theme.gap(0.5),
		backgroundColor: theme.colors["violet-500"],
	},
	activeEventBadgeText: {
		color: theme.colors["neutral-0"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 7,
		fontWeight: "800",
	},
	eventName: {
		marginTop: theme.gap(0.5),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 11,
		fontWeight: "800",
	},
	eventEffect: {
		flex: 1,
		marginTop: 2,
		color: theme.colors["neutral-600"],
		fontSize: 9,
		fontWeight: "600",
		lineHeight: 12,
	},
	eventFooter: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
	},
	eventDuration: {
		color: theme.colors["neutral-500"],
		fontFamily: theme.fonts.family.number,
		fontSize: 8,
		fontWeight: "700",
	},
	eventAction: {
		fontSize: 9,
		fontWeight: "800",
	},
	valueCard: {
		padding: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
	},
	valueHeading: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
	},
	valueEmoji: { width: 34, height: 34 },
	valueLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 9,
		fontWeight: "700",
		letterSpacing: 0.4,
		textTransform: "uppercase",
	},
	value: {
		marginTop: 1,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: theme.fonts.size.large,
		fontWeight: "700",
	},
	valueActions: {
		flexDirection: "row",
		gap: theme.gap(0.5),
		marginTop: theme.gap(0.75),
	},
	valueButton: {
		flex: 1,
		alignItems: "center",
		paddingVertical: theme.gap(0.75),
		borderWidth: 1,
		borderRadius: theme.gap(1),
	},
	removeButton: {
		borderColor: theme.colors["red-200"],
		backgroundColor: theme.colors["red-50"],
	},
	addButton: {
		borderColor: theme.colors["green-100"],
		backgroundColor: theme.colors["green-50"],
	},
	valueButtonText: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 10,
		fontWeight: "700",
	},
	removeButtonText: { color: theme.colors["red-500"] },
	addButtonText: { color: theme.colors["green-600"] },
	presetRow: { flexDirection: "row", gap: theme.gap(0.5) },
	presetButton: {
		flex: 1,
		alignItems: "center",
		paddingVertical: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-0"],
	},
	activePresetButton: {
		borderColor: theme.colors["violet-500"],
		backgroundColor: theme.colors["violet-500"],
	},
	presetText: {
		color: theme.colors["neutral-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 9,
		fontWeight: "700",
	},
	activePresetText: { color: theme.colors["neutral-0"] },
	searchField: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		paddingHorizontal: theme.gap(1),
		borderWidth: 1,
		borderColor: theme.colors["neutral-200"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
	},
	searchIcon: {
		color: theme.colors["neutral-500"],
		fontSize: 20,
	},
	searchInput: {
		flex: 1,
		height: theme.gap(5),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.body,
		fontSize: theme.fonts.size.small,
	},
	clearSearch: {
		color: theme.colors["neutral-500"],
		fontSize: 20,
	},
	productRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		marginBottom: theme.gap(0.5),
		paddingHorizontal: theme.gap(0.75),
		paddingVertical: theme.gap(0.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
	},
	emptyState: {
		alignItems: "center",
		padding: theme.gap(2),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["neutral-0"],
	},
	emptyStateText: {
		color: theme.colors["neutral-500"],
		fontSize: theme.fonts.size.small,
		textAlign: "center",
	},
	productEmojiFrame: {
		width: theme.gap(3.75),
		height: theme.gap(3.75),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-100"],
	},
	productImage: {
		width: theme.gap(3.25),
		height: theme.gap(3.25),
	},
	productCopy: { flex: 1, minWidth: 60 },
	productName: {
		color: theme.colors["neutral-800"],
		fontSize: 10,
		fontWeight: "700",
	},
	productMeta: {
		marginTop: 1,
		color: theme.colors["neutral-500"],
		fontSize: 8,
	},
	stockValue: {
		minWidth: theme.gap(3),
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 10,
		fontWeight: "700",
		textAlign: "center",
	},
	compactButton: {
		minWidth: theme.gap(3.5),
		alignItems: "center",
		paddingHorizontal: theme.gap(0.5),
		paddingVertical: theme.gap(0.5),
		borderWidth: 1,
		borderRadius: theme.gap(0.75),
	},
	compactRemoveButton: {
		borderColor: theme.colors["red-200"],
		backgroundColor: theme.colors["red-50"],
	},
	compactAddButton: {
		borderColor: theme.colors["green-100"],
		backgroundColor: theme.colors["green-50"],
	},
	compactButtonText: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 8,
		fontWeight: "700",
	},
	compactRemoveText: { color: theme.colors["red-500"] },
	compactAddText: { color: theme.colors["green-600"] },
}));
