import type { DayGrade } from "@/@types/market-day";
import type { GameIconId } from "@/data/game-icon-assets";

export const gradeMessages: Record<DayGrade, string> = {
	S: "Dia perfeito!",
	A: "Excelente dia!",
	B: "Bom dia de trabalho",
	C: "Dá para melhorar",
	D: "Dia difícil",
};

export function contractIcon(icon: string): GameIconId {
	const known: GameIconId[] = [
		"coin",
		"receipt",
		"customers",
		"handshake",
		"success",
		"medal",
		"target",
	];
	return known.includes(icon as GameIconId) ? (icon as GameIconId) : "target";
}
