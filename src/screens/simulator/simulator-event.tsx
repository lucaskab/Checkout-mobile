import { useEffect, useState } from "react";
import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { getGameEvent } from "@/data/game-events";
import { getGameEventIcon } from "@/data/game-icon-assets";
import { useGameStore } from "@/stores/game-store";

export function SimulatorEvent() {
	const active = useGameStore((state) => state.events.activeEvent);
	const [now, setNow] = useState(Date.now());
	const [expanded, setExpanded] = useState(false);
	const event = getGameEvent(active?.eventId);
	useEffect(() => {
		setExpanded(false);
		setNow(Date.now());
		if (!active) return;
		const timer = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(timer);
	}, [active]);
	if (!event || !active || active.endsAt <= now) return null;
	const seconds = Math.ceil((active.endsAt - now) / 1000);
	return (
		<Pressable
			accessibilityRole="button"
			accessibilityLabel={`${event.name}. ${event.effectLabel}. Ver detalhes do evento`}
			accessibilityState={{ expanded }}
			onPress={() => setExpanded(!expanded)}
			style={[styles.chip, event.kind === "negative" && styles.negative]}
		>
			<View style={styles.row}>
				<GameIcon icon={getGameEventIcon(event.id)} style={styles.icon} />
				<Text numberOfLines={1} style={styles.name}>
					{event.name}
				</Text>
				<Text style={styles.timer}>
					{Math.floor(seconds / 60)}:{String(seconds % 60).padStart(2, "0")}
				</Text>
			</View>
			{expanded && <Text style={styles.detail}>{event.effectLabel}</Text>}
		</Pressable>
	);
}
const styles = StyleSheet.create((theme) => ({
	chip: {
		alignSelf: "flex-start",
		maxWidth: "100%",
		minHeight: 44,
		justifyContent: "center",
		paddingHorizontal: theme.gap(1),
		paddingVertical: theme.gap(0.625),
		borderRadius: theme.gap(1.5),
		borderWidth: 1,
		borderColor: theme.colors["green-100"],
		backgroundColor: theme.colors["green-50"],
	},
	negative: {
		borderColor: theme.colors["red-200"],
		backgroundColor: theme.colors["red-50"],
	},
	row: { flexDirection: "row", alignItems: "center", gap: theme.gap(0.75) },
	icon: { width: 24, height: 24 },
	name: {
		flexShrink: 1,
		fontFamily: theme.fonts.family.badge,
		fontSize: 12,
		color: theme.colors["neutral-800"],
	},
	timer: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 11,
		color: theme.colors["neutral-600"],
	},
	detail: {
		marginTop: theme.gap(0.5),
		fontSize: 12,
		color: theme.colors["neutral-700"],
	},
}));
