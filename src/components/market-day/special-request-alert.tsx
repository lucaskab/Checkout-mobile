import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useBottomSheet } from "@/components/bottom-sheet";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getPendingRequests } from "@/services/market-day";
import { useGameStore } from "@/stores/game-store";
import { requestKindIcons, requestKindLabels } from "./labels";
import { SpecialRequestsSheet } from "./special-requests-sheet";
import { formatClock, useNow } from "./use-now";

// Alert for the most urgent customer waiting with a special request.
export function SpecialRequestAlert() {
	const { openBottomSheet } = useBottomSheet();
	const day = useGameStore((state) => state.day);
	const pending = getPendingRequests(day).sort(
		(a, b) => a.expiresAt - b.expiresAt,
	);
	const now = useNow(pending.length > 0);
	const next = pending[0];
	if (!next || day.phase !== "open") return null;
	const remaining = next.expiresAt - now;
	const urgent = remaining < 15_000;

	return (
		<Pressable
			accessibilityLabel={`${next.customerName}: ${next.message}. Atender`}
			accessibilityRole="button"
			onPress={() =>
				openBottomSheet(<SpecialRequestsSheet focusId={next.id} />)
			}
			style={({ pressed }) => [
				styles.alert,
				urgent && styles.urgent,
				pressed && styles.pressed,
			]}
		>
			<GameIcon icon={requestKindIcons[next.kind]} style={styles.icon} />
			<View style={styles.copy}>
				<Text numberOfLines={1} style={styles.title}>
					{next.customerName} · {requestKindLabels[next.kind]}
					{pending.length > 1 ? ` (+${pending.length - 1})` : ""}
				</Text>
				<Text numberOfLines={1} style={styles.message}>
					{next.message}
				</Text>
			</View>
			<View style={styles.action}>
				<Text style={styles.timer}>{formatClock(remaining)}</Text>
				<Text style={styles.actionText}>ATENDER</Text>
			</View>
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	alert: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(1),
		marginHorizontal: theme.gap(1),
		marginTop: theme.gap(0.75),
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.75),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderRadius: theme.gap(1.5),
		borderColor: theme.colors["amber-400"],
		backgroundColor: theme.colors["amber-50"],
	},
	urgent: {
		borderColor: theme.colors["red-400"],
		backgroundColor: theme.colors["red-50"],
	},
	pressed: { borderBottomWidth: 2, transform: [{ translateY: 2 }] },
	icon: { width: theme.gap(3.5), height: theme.gap(3.5) },
	copy: { flex: 1 },
	title: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 13,
	},
	message: { color: theme.colors["neutral-600"], fontSize: 11 },
	action: { alignItems: "flex-end" },
	timer: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 14,
	},
	actionText: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 10,
	},
}));
