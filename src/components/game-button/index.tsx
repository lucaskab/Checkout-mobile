import { Pressable, type PressableProps, type ViewStyle } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { GameIcon } from "@/components/game-icon";
import { GameText as Text } from "@/components/game-text";
import type { GameIconId } from "@/data/game-icon-assets";

export type GameButtonVariant =
	| "primary"
	| "secondary"
	| "success"
	| "danger"
	| "coin"
	| "gem";

export type GameButtonSize = "small" | "medium" | "large";

type GameButtonProps = {
	/** Texto do botão. */
	label: string;
	/** Ícone PNG opcional exibido antes do texto. */
	icon?: GameIconId;
	/** Estilo visual do botão. */
	variant?: GameButtonVariant;
	/** Tamanho do botão. */
	size?: GameButtonSize;
	/** Ocupa toda a largura disponível. */
	fullWidth?: boolean;
	/** Estilo extra aplicado ao container (ex.: flex, margens). */
	style?: ViewStyle;
} & Omit<PressableProps, "style" | "children">;

/**
 * Botão reutilizável com profundidade 3D. A "aresta" inferior encolhe e o
 * botão afunda ao ser pressionado, imitando uma tecla física.
 */
export function GameButton({
	disabled,
	icon,
	fullWidth = false,
	label,
	size = "medium",
	style,
	variant = "primary",
	...pressableProps
}: GameButtonProps) {
	styles.useVariants({ disabled: Boolean(disabled), fullWidth, size, variant });

	return (
		<Pressable
			accessibilityRole="button"
			accessibilityState={{ disabled: Boolean(disabled) }}
			disabled={disabled}
			style={({ pressed }) => [
				styles.button,
				pressed && !disabled && styles.pressed,
				style,
			]}
			{...pressableProps}
		>
			{icon && <GameIcon icon={icon} style={styles.icon} />}
			<Text numberOfLines={1} style={styles.label}>
				{label}
			</Text>
		</Pressable>
	);
}

const styles = StyleSheet.create((theme) => ({
	button: {
		flexDirection: "row",
		alignItems: "center",
		justifyContent: "center",
		gap: theme.gap(0.5),
		borderWidth: 2,
		borderBottomWidth: 5,
		variants: {
			size: {
				small: {
					minHeight: theme.gap(4),
					paddingHorizontal: theme.gap(1.25),
					borderRadius: theme.gap(1.25),
				},
				medium: {
					minHeight: theme.gap(5),
					paddingHorizontal: theme.gap(1.75),
					borderRadius: theme.gap(1.5),
				},
				large: {
					minHeight: theme.gap(6),
					paddingHorizontal: theme.gap(2.25),
					borderRadius: theme.gap(2),
				},
			},
			variant: {
				primary: {
					borderColor: theme.colors["blue-400"],
					borderBottomColor: theme.colors["blue-600"],
					backgroundColor: theme.colors["blue-500"],
				},
				secondary: {
					borderColor: theme.colors["neutral-200"],
					borderBottomColor: theme.colors["neutral-300"],
					backgroundColor: theme.colors["neutral-0"],
				},
				success: {
					borderColor: theme.colors["green-500"],
					borderBottomColor: theme.colors["green-600"],
					backgroundColor: theme.colors["green-500"],
				},
				danger: {
					borderColor: theme.colors["red-400"],
					borderBottomColor: theme.colors["red-600"],
					backgroundColor: theme.colors["red-500"],
				},
				coin: {
					borderColor: theme.colors["amber-400"],
					borderBottomColor: theme.colors["amber-600"],
					backgroundColor: theme.colors["amber-400"],
				},
				gem: {
					borderColor: theme.colors["violet-400"],
					borderBottomColor: theme.colors["violet-600"],
					backgroundColor: theme.colors["violet-500"],
				},
			},
			fullWidth: {
				true: {
					alignSelf: "stretch",
				},
			},
			disabled: {
				true: {
					borderColor: theme.colors["neutral-200"],
					borderBottomColor: theme.colors["neutral-300"],
					backgroundColor: theme.colors["neutral-100"],
				},
			},
		},
	},
	pressed: {
		borderBottomWidth: 2,
		transform: [{ translateY: 3 }],
	},
	icon: {
		variants: {
			size: {
				small: { width: 16, height: 16 },
				medium: { width: 20, height: 20 },
				large: { width: 24, height: 24 },
			},
		},
	},
	label: {
		fontFamily: theme.fonts.family.badge,
		fontWeight: "800",
		variants: {
			size: {
				small: { fontSize: 11 },
				medium: { fontSize: theme.fonts.size.small },
				large: { fontSize: theme.fonts.size.medium },
			},
			variant: {
				primary: { color: theme.colors["neutral-0"] },
				secondary: { color: theme.colors["neutral-700"] },
				success: { color: theme.colors["neutral-0"] },
				danger: { color: theme.colors["neutral-0"] },
				coin: { color: theme.colors["neutral-800"] },
				gem: { color: theme.colors["neutral-0"] },
			},
			disabled: {
				true: { color: theme.colors["neutral-500"] },
			},
		},
	},
}));
