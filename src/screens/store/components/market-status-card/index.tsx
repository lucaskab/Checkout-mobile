import { Pressable, Text, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";

type MarketStatusCardProps = {
	experience: number;
	experienceToNextLevel: number;
	isOpen: boolean;
	lastExperienceGain: number;
	level: number;
	onToggle: () => void;
	recentUnlocks: string[];
	unlockedProductCount: number;
};

export function MarketStatusCard({
	experience,
	experienceToNextLevel,
	isOpen,
	lastExperienceGain,
	level,
	onToggle,
	recentUnlocks,
	unlockedProductCount,
}: MarketStatusCardProps) {
	const experienceProgress = Math.min(
		Math.round((experience / experienceToNextLevel) * 100),
		100,
	);

	return (
		<View style={[styles.card, isOpen && styles.openCard]}>
			<View style={styles.copy}>
				<View style={[styles.status, isOpen && styles.openStatus]}>
					<View style={[styles.statusDot, isOpen && styles.openStatusDot]} />
					<Text style={[styles.statusText, isOpen && styles.openStatusText]}>
						{isOpen ? "Mercado aberto" : "Mercado fechado"}
					</Text>
				</View>
				<Text style={styles.title}>
					{isOpen
						? "Clientes estão chegando para comprar."
						: "Abra para começar a receber clientes."}
				</Text>
				<Text style={styles.detail}>
					Nível {level} · {unlockedProductCount} produtos desbloqueados
				</Text>
				<View style={styles.experienceRow}>
					<View style={styles.experienceTrack}>
						<View
							style={[
								styles.experienceFill,
								{ width: `${experienceProgress}%` },
							]}
						/>
					</View>
					<Text style={styles.experienceText}>
						{experience}/{experienceToNextLevel} XP
					</Text>
				</View>
				{lastExperienceGain > 0 && (
					<Text style={styles.experienceGain}>
						+{lastExperienceGain} XP na última venda
					</Text>
				)}
				{recentUnlocks.length > 0 && (
					<View style={styles.unlockNotice}>
						<Text style={styles.unlockTitle}>✨ Novos produtos liberados</Text>
						<Text style={styles.unlockCopy}>{recentUnlocks.join(" · ")}</Text>
					</View>
				)}
			</View>
			<Pressable
				onPress={onToggle}
				style={[styles.button, isOpen && styles.closeButton]}
			>
				<Text style={styles.buttonText}>{isOpen ? "Fechar" : "Abrir"}</Text>
			</Pressable>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	card: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1.5),
		padding: theme.gap(1.75),
		borderWidth: 1,
		borderColor: theme.colors["neutral-150"],
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["neutral-0"],
		shadowColor: theme.colors["neutral-800"],
		shadowOffset: { width: 0, height: 3 },
		shadowOpacity: 0.08,
		shadowRadius: 8,
		elevation: 2,
	},
	openCard: {
		borderColor: theme.colors["green-100"],
		backgroundColor: theme.colors["green-50"],
	},
	copy: {
		flex: 1,
	},
	status: {
		alignSelf: "flex-start",
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.5),
		paddingHorizontal: theme.gap(0.875),
		paddingVertical: theme.gap(0.4),
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["neutral-100"],
	},
	openStatus: {
		backgroundColor: theme.colors["green-100"],
	},
	statusDot: {
		width: theme.gap(0.75),
		height: theme.gap(0.75),
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["neutral-500"],
	},
	openStatusDot: {
		backgroundColor: theme.colors["green-500"],
	},
	statusText: {
		color: theme.colors["neutral-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	openStatusText: {
		color: theme.colors["green-600"],
	},
	title: {
		marginTop: theme.gap(0.75),
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
	detail: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-600"],
		fontSize: 11,
	},
	experienceRow: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginTop: theme.gap(1),
	},
	experienceTrack: {
		flex: 1,
		height: theme.gap(0.75),
		overflow: "hidden",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-100"],
	},
	experienceFill: {
		height: "100%",
		borderRadius: theme.gap(1),
		backgroundColor: theme.colors["blue-500"],
	},
	experienceText: {
		color: theme.colors["blue-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	experienceGain: {
		marginTop: theme.gap(0.5),
		color: theme.colors["green-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	unlockNotice: {
		marginTop: theme.gap(1),
		padding: theme.gap(1),
		borderRadius: theme.gap(1.5),
		backgroundColor: theme.colors["amber-50"],
	},
	unlockTitle: {
		color: theme.colors["amber-600"],
		fontSize: 10,
		fontWeight: "700",
	},
	unlockCopy: {
		marginTop: theme.gap(0.25),
		color: theme.colors["neutral-700"],
		fontSize: 11,
		fontWeight: "700",
	},
	button: {
		alignItems: "center",
		justifyContent: "center",
		minWidth: theme.gap(8),
		minHeight: theme.gap(4.5),
		paddingHorizontal: theme.gap(1.25),
		borderRadius: theme.gap(2.5),
		backgroundColor: theme.colors["blue-500"],
	},
	closeButton: {
		backgroundColor: theme.colors["red-500"],
	},
	buttonText: {
		color: theme.colors["neutral-0"],
		fontSize: theme.fonts.size.small,
		fontWeight: "700",
	},
}));
