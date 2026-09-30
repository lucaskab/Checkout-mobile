import { useEffect, useState } from "react";
import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameButton } from "@/components/game-button";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import {
	formatBuildDuration,
	formatConstructionCountdown,
} from "@/data/market-expansions";
import type { InteriorBuildStatus } from "@/services/interior-construction";

type BuildPanelProps = {
	title: string;
	status: InteriorBuildStatus;
	/** Pays with coins and starts the works. */
	onBuild?: () => void;
	/** Pays with diamonds and starts the works (sectors). */
	onBuildWithDiamonds?: () => void;
	/** Diamonds to finish the running works now. */
	onSpeedUp?: () => void;
	coins: number;
	diamonds: number;
};

/** Build / under construction / speed-up card shared by shelves, sectors and fixtures. */
export function BuildPanel({
	coins,
	diamonds,
	onBuild,
	onBuildWithDiamonds,
	onSpeedUp,
	status,
	title,
}: BuildPanelProps) {
	const [now, setNow] = useState(() => Date.now());
	const building = status.status === "building" && status.construction;
	useEffect(() => {
		if (!building) return;
		const timer = setInterval(() => setNow(Date.now()), 1000);
		return () => clearInterval(timer);
	}, [building]);

	if (status.status === "built") return null;
	// Bought: waits in the inventory (build mode) or in the builders' queue.
	if (status.status === "stored" || status.status === "queued")
		return (
			<View style={styles.card}>
				<View style={styles.header}>
					<GameIcon icon="construction" style={styles.icon} />
					<View style={styles.copy}>
						<Text style={styles.eyebrow}>{status.status === "stored" ? "NO INVENTÁRIO" : "NA FILA DA OBRA"}</Text>
						<Text style={styles.title}>{title}</Text>
						<Text style={styles.detail}>
							{status.status === "stored"
								? `Escolha o lugar no modo construir · obra de ${formatBuildDuration(status.durationMs)}`
								: `Começa depois da obra atual · obra de ${formatBuildDuration(status.durationMs)}`}
						</Text>
					</View>
				</View>
			</View>
		);
	const remaining = building ? Math.max(0, status.construction!.endsAt - now) : 0;
	const total = building
		? Math.max(1, status.construction!.endsAt - status.construction!.startedAt)
		: 1;
	const progress = building ? Math.min(1, 1 - remaining / total) : 0;
	const skipCost = building ? Math.max(1, Math.ceil(remaining / 600_000)) : 0;
	const available = status.status === "available";

	return (
		<View style={styles.card}>
			<View style={styles.header}>
				<GameIcon icon="construction" style={styles.icon} />
				<View style={styles.copy}>
					<Text style={styles.eyebrow}>{building ? "EM OBRA" : "CONSTRUÇÃO"}</Text>
					<Text style={styles.title}>{title}</Text>
					<Text style={styles.detail}>
						{building
							? `Pronto em ${formatConstructionCountdown(remaining)}`
							: `Obra de ${formatBuildDuration(status.durationMs)}${status.reason ? ` · ${status.reason}` : ""}`}
					</Text>
				</View>
			</View>
			{building ? (
				<>
					<View style={styles.track}>
						<View style={[styles.fill, { width: `${Math.round(progress * 100)}%` }]} />
					</View>
					{onSpeedUp && (
						<GameButton
							disabled={diamonds < skipCost}
							fullWidth
							icon="diamond"
							label={`Acelerar · ${skipCost}`}
							onPress={onSpeedUp}
							variant="gem"
						/>
					)}
				</>
			) : (
				<View style={styles.actions}>
					{onBuild && (
						<GameButton
							disabled={!available || coins < status.coinCost}
							icon="coin"
							label={`Comprar · ${status.coinCost.toLocaleString("pt-BR")}`}
							onPress={onBuild}
							style={styles.action}
							variant="coin"
						/>
					)}
					{onBuildWithDiamonds && status.diamondCost > 0 && (
						<GameButton
							disabled={!available || diamonds < status.diamondCost}
							icon="diamond"
							label={`${status.diamondCost}`}
							onPress={onBuildWithDiamonds}
							variant="gem"
						/>
					)}
				</View>
			)}
		</View>
	);
}

const styles = StyleSheet.create((theme) => ({
	card: {
		gap: theme.gap(1),
		padding: theme.gap(1.5),
		borderWidth: 1,
		borderColor: theme.colors["amber-200"],
		borderRadius: theme.gap(2),
		backgroundColor: theme.colors["amber-50"],
	},
	header: { flexDirection: "row", alignItems: "center", gap: theme.gap(1) },
	icon: { width: 40, height: 40 },
	copy: { flex: 1 },
	eyebrow: {
		color: theme.colors["amber-600"],
		fontSize: 10,
		fontWeight: "700",
		letterSpacing: 1.2,
	},
	title: {
		color: theme.colors["neutral-800"],
		fontSize: theme.fonts.size.medium,
		fontWeight: "700",
	},
	detail: {
		marginTop: 2,
		color: theme.colors["neutral-600"],
		fontSize: 11,
		fontWeight: "600",
	},
	track: {
		height: 10,
		overflow: "hidden",
		borderRadius: 5,
		backgroundColor: theme.colors["amber-100"],
	},
	fill: { height: "100%", borderRadius: 5, backgroundColor: theme.colors["amber-500"] },
	actions: { flexDirection: "row", gap: theme.gap(0.75) },
	action: { flex: 1 },
}));
