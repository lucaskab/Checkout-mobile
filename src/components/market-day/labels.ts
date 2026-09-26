import type { CustomerMood } from "@/@types/customer-simulation";
import type { DayGrade, SpecialRequestKind } from "@/@types/market-day";
import type { GameIconId } from "@/data/game-icon-assets";

export const moodLabels: Record<CustomerMood, string> = {
	calmo: "Calmo",
	"com-pressa": "Com pressa",
	estressado: "Estressado",
	feliz: "Feliz",
};

export const requestKindLabels: Record<SpecialRequestKind, string> = {
	ajuda: "Precisa de ajuda",
	alternativa: "Quer uma alternativa",
	produto: "Procura um produto",
};

export const requestKindIcons: Record<SpecialRequestKind, GameIconId> = {
	ajuda: "customers",
	alternativa: "handshake",
	produto: "basket",
};

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
