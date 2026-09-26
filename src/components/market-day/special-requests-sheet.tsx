import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameButton } from "@/components/game-button";
import { GameText as Text } from "@/components/game-text";
import { useGameStore } from "@/stores/game-store";
import { SpecialRequestCard } from "./special-request-card";

// Pending requests first, then the last answers of the day so the player sees the outcome.
export function SpecialRequestsSheet({ focusId }: { focusId?: string }) {
	const { closeBottomSheet } = useBottomSheet();
	const requests = useGameStore((state) => state.day.requests);
	const pending = requests.filter((request) => request.status === "pending");
	const focused = focusId
		? pending.filter((request) => request.id === focusId)
		: [];
	const ordered = [
		...focused,
		...pending.filter((request) => request.id !== focusId),
	];
	const answered = requests
		.filter((request) => request.status !== "pending")
		.slice(0, 2);

	return (
		<View style={styles.container}>
			<View>
				<Text style={styles.title}>Pedidos especiais</Text>
				<Text style={styles.subtitle}>
					Atenda antes do tempo acabar. Quem espera demais vai embora e a
					reputação cai.
				</Text>
			</View>
			{ordered.length === 0 && (
				<Text style={styles.empty}>Nenhum cliente esperando agora.</Text>
			)}
			{ordered.map((request) => (
				<SpecialRequestCard key={request.id} request={request} />
			))}
			{answered.map((request) => (
				<SpecialRequestCard key={request.id} request={request} />
			))}
			<GameButton
				fullWidth
				label="Voltar à loja"
				onPress={closeBottomSheet}
				variant="secondary"
			/>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	container: { gap: theme.gap(1), paddingHorizontal: theme.gap(1.5) },
	title: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 21,
	},
	subtitle: { marginTop: 2, color: theme.colors["neutral-500"], fontSize: 12 },
	empty: {
		paddingVertical: theme.gap(2),
		textAlign: "center",
		color: theme.colors["neutral-500"],
	},
}));
