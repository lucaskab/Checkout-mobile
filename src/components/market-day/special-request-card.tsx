import { Pressable, View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import type { SpecialRequest } from "@/@types/market-day";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import { useGameStore } from "@/stores/game-store";
import { moodLabels, requestKindIcons, requestKindLabels } from "./labels";
import { formatClock, useNow } from "./use-now";

// One customer waiting with a special request: countdown plus the possible answers.
export function SpecialRequestCard({ request }: { request: SpecialRequest }) {
	const resolve = useGameStore((state) => state.resolveSpecialRequest);
	const pending = request.status === "pending";
	const now = useNow(pending);
	const total = Math.max(1, request.expiresAt - request.createdAt);
	const remaining = Math.max(0, request.expiresAt - now);
	const ratio = remaining / total;
	styles.useVariants({
		urgent: pending && ratio < 0.35,
		status: pending ? "pending" : request.status,
	});

	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<View style={styles.iconPlate}>
					<GameIcon icon={requestKindIcons[request.kind]} style={styles.icon} />
				</View>
				<View style={styles.headerCopy}>
					<Text style={styles.eyebrow}>
						{requestKindLabels[request.kind].toUpperCase()} ·{" "}
						{moodLabels[request.mood].toUpperCase()}
					</Text>
					<Text numberOfLines={1} style={styles.name}>
						{request.customerName}
					</Text>
				</View>
				{pending && <Text style={styles.timer}>{formatClock(remaining)}</Text>}
			</View>
			<Text style={styles.message}>“{request.message}”</Text>
			{pending ? (
				<>
					<View style={styles.track}>
						<View style={[styles.fill, { width: `${ratio * 100}%` }]} />
					</View>
					<View style={styles.options}>
						{request.options.map((option) => (
							<Pressable
								accessibilityRole="button"
								accessibilityLabel={`${option.label}. ${option.detail}`}
								key={option.id}
								onPress={() => resolve(request.id, option.id)}
								style={({ pressed }) => [
									styles.option,
									pressed && styles.optionPressed,
								]}
							>
								<Text numberOfLines={1} style={styles.optionLabel}>
									{option.label}
								</Text>
								<Text numberOfLines={1} style={styles.optionDetail}>
									{option.detail}
								</Text>
							</Pressable>
						))}
					</View>
				</>
			) : (
				<View style={styles.outcome}>
					<Text style={styles.outcomeText}>{request.outcome}</Text>
					{request.tip > 0 && (
						<View style={styles.tip}>
							<GameIcon icon="coin" style={styles.tipIcon} />
							<Text style={styles.tipText}>+{request.tip} gorjeta</Text>
						</View>
					)}
				</View>
			)}
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	card: {
		gap: theme.gap(0.75),
		padding: theme.gap(1.25),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderRadius: theme.gap(1.75),
		borderColor: theme.colors["neutral-150"],
		backgroundColor: theme.colors["neutral-0"],
		variants: {
			urgent: { true: { borderColor: theme.colors["red-200"] } },
			status: {
				pending: {},
				served: {
					borderColor: theme.colors["green-100"],
					backgroundColor: theme.colors["green-50"],
				},
				partial: { backgroundColor: theme.colors["amber-50"] },
				failed: { backgroundColor: theme.colors["red-50"] },
				expired: { backgroundColor: theme.colors["red-50"] },
			},
		},
	},
	header: { flexDirection: "row", alignItems: "center", gap: theme.gap(1) },
	iconPlate: {
		width: theme.gap(4.5),
		height: theme.gap(4.5),
		alignItems: "center",
		justifyContent: "center",
		borderRadius: theme.gap(1.25),
		backgroundColor: theme.colors["blue-50"],
	},
	icon: { width: theme.gap(3), height: theme.gap(3) },
	headerCopy: { flex: 1 },
	eyebrow: {
		color: theme.colors["blue-600"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 9,
		letterSpacing: 0.8,
	},
	name: {
		color: theme.colors["neutral-800"],
		fontFamily: theme.fonts.family.headline,
		fontSize: 16,
	},
	timer: {
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 16,
		color: theme.colors["neutral-700"],
		variants: { urgent: { true: { color: theme.colors["red-600"] } } },
	},
	message: {
		color: theme.colors["neutral-700"],
		fontSize: 13,
		fontWeight: "600",
	},
	track: {
		height: 6,
		overflow: "hidden",
		borderRadius: 999,
		backgroundColor: theme.colors["neutral-100"],
	},
	fill: {
		height: "100%",
		borderRadius: 999,
		backgroundColor: theme.colors["green-500"],
		variants: {
			urgent: { true: { backgroundColor: theme.colors["red-500"] } },
		},
	},
	options: { gap: theme.gap(0.5) },
	option: {
		paddingHorizontal: theme.gap(1.25),
		paddingVertical: theme.gap(0.75),
		borderWidth: 2,
		borderBottomWidth: 4,
		borderRadius: theme.gap(1.25),
		borderColor: theme.colors["blue-100"],
		backgroundColor: theme.colors["blue-50"],
	},
	optionPressed: { borderBottomWidth: 2, transform: [{ translateY: 2 }] },
	optionLabel: {
		color: theme.colors["blue-700"],
		fontFamily: theme.fonts.family.badge,
		fontSize: 13,
	},
	optionDetail: { color: theme.colors["neutral-500"], fontSize: 11 },
	outcome: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "space-between",
		gap: theme.gap(1),
	},
	outcomeText: { flex: 1, color: theme.colors["neutral-700"], fontSize: 12 },
	tip: { flexDirection: "row", alignItems: "center", gap: 3 },
	tipIcon: { width: 16, height: 16 },
	tipText: {
		color: theme.colors["amber-600"],
		fontFamily: theme.fonts.family.numberBold,
		fontSize: 12,
	},
}));
