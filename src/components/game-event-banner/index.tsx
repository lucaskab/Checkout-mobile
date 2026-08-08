import { useEffect, useState } from "react";
import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getGameEvent } from "@/data/game-events";
import { getGameEventIcon } from "@/data/game-icon-assets";
import { useGameStore } from "@/stores/game-store";

export function GameEventBanner() {
	const activeEvent = useGameStore((state) => state.events.activeEvent);
	const [currentTime, setCurrentTime] = useState(Date.now());
	const event = getGameEvent(activeEvent?.eventId);

	useEffect(() => {
		if (!activeEvent) {
			return;
		}

		setCurrentTime(Date.now());
		const interval = setInterval(() => setCurrentTime(Date.now()), 1_000);

		return () => clearInterval(interval);
	}, [activeEvent]);

	if (!activeEvent || !event || activeEvent.endsAt <= currentTime) {
		return null;
	}

	const remainingSeconds = Math.max(
		0,
		Math.ceil((activeEvent.endsAt - currentTime) / 1_000),
	);
	const minutes = Math.floor(remainingSeconds / 60);
	const seconds = remainingSeconds % 60;
	const isPositive = event.kind === "positive";

	return (
		<View
			style={[
				styles.banner,
				isPositive ? styles.positiveBanner : styles.negativeBanner,
			]}
		>
			<View
				style={[
					styles.icon,
					isPositive ? styles.positiveIcon : styles.negativeIcon,
				]}
			>
				<GameIcon icon={getGameEventIcon(event.id)} style={styles.iconImage} />
			</View>
			<View style={styles.copy}>
				<View style={styles.titleRow}>
					<Text
						style={[
							styles.kind,
							isPositive ? styles.positiveText : styles.negativeText,
						]}
					>
						{isPositive ? "EVENTO POSITIVO" : "EVENTO NEGATIVO"}
					</Text>
					<Text style={styles.title}> · {event.name}</Text>
				</View>
				<Text numberOfLines={1} style={styles.effect}>
					{event.effectLabel}
				</Text>
			</View>
			<View style={styles.timer}>
				<Text style={styles.timerLabel}>Termina em</Text>
				<Text style={styles.timerValue}>
					{minutes}:{seconds.toString().padStart(2, "0")}
				</Text>
			</View>
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	banner: {
		flexDirection: "row",
		alignItems: "center",
		gap: theme.gap(0.75),
		marginHorizontal: theme.gap(1.5),
		marginBottom: theme.gap(0.75),
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.75),
		borderWidth: 1,
		borderRadius: theme.gap(1.5),
	},
	positiveBanner: {
		borderColor: theme.colors["green-100"],
		backgroundColor: theme.colors["green-50"],
	},
	negativeBanner: {
		borderColor: theme.colors["red-200"],
		backgroundColor: theme.colors["red-50"],
	},
	icon: {
		width: theme.gap(4),
		height: theme.gap(4),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.25),
	},
	positiveIcon: {
		backgroundColor: theme.colors["green-100"],
	},
	negativeIcon: {
		backgroundColor: theme.colors["red-100"],
	},
	iconImage: {
		width: 28,
		height: 28,
	},
	copy: {
		flex: 1,
	},
	titleRow: {
		flexDirection: "row",
		alignItems: "center",
	},
	kind: {
		fontFamily: theme.fonts.family.badge,
		fontSize: 8,
		fontWeight: "800",
		letterSpacing: 0.4,
	},
	positiveText: {
		color: theme.colors["green-600"],
	},
	negativeText: {
		color: theme.colors["red-600"],
	},
	title: {
		flex: 1,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 10,
		fontWeight: "800",
	},
	effect: {
		marginTop: 1,
		color: theme.colors["neutral-600"],
		fontSize: 9,
		fontWeight: "600",
	},
	timer: {
		alignItems: "flex-end",
	},
	timerLabel: {
		color: theme.colors["neutral-500"],
		fontSize: 7,
		fontWeight: "700",
	},
	timerValue: {
		marginTop: 1,
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
		fontWeight: "800",
	},
}));
