import type { GameState } from "@/@types/game";
import { getInteriorDecor } from "@/data/interior-decor";
import { getPetCosmetic, PET_BED_DECOR_IDS, PET_FIRST_ERA, PET_OFFER_TEXT, petCosmetics } from "@/data/pet";
import { THIEF_GONE_MESSAGE, THIEF_NOT_YET_MESSAGE } from "@/data/security";
import { normalizeStoreSecurityState } from "@/services/store-security";
import {
	getPetCooldownLeftMs,
	getPetHappyLeftMs,
	isPetEraReached,
	normalizePetState,
} from "@/services/store-pet";
import { getMarketEra } from "@/data/economy";
import { act, type Card, card, decorIcon, fmt, gameIcon, productIcon, type State } from "../view-kit";
import { placeButton } from "./build-cards";

// "Mascote caramelo" in the shop (Decoração › Caramelo): adopt the dog, pet him, buy and wear his cosmetics.
// The same actions Unity sends from the world (the dog at the door): src/services/store-pet.ts.

/** The dog's picture until he has art of his own: the premium pet food bag. */
const PET_ICON = productIcon(36);
export const petChipIcon = PET_ICON;

const kindLabels: Record<string, string> = {
	collar: "COLEIRA",
	bandana: "BANDANA",
	bed: "CAMINHA",
	bowls: "POTES",
	bedStyle: "TECIDO DAS CAMINHAS",
};

const seconds = (ms: number) => Math.max(1, Math.ceil(ms / 1000));

function dogCard(state: State): Card {
	const pet = normalizePetState(state.pet);
	const now = Date.now();
	if (!pet.adopted) {
		const reached = isPetEraReached(state.era.id);
		return card("Mascote caramelo", {
			eyebrow: reached ? "NA PORTA" : "BLOQUEADO",
			icon: PET_ICON,
			tone: reached ? "featured" : "locked",
			subtitle: reached ? PET_OFFER_TEXT : "Um vira-lata caramelo vai aparecer na porta do mercado.",
			lines: ["Adotar é de graça.", "Um cachorro feliz na porta traz mais clientes."],
			buttons: [
				act(reached ? "Adotar" : `Chega com: ${getMarketEra(PET_FIRST_ERA).name}`, "adoptPet", [], {
					variant: "success",
					enabled: reached,
					ok: "Você adotou um vira-lata caramelo!",
					fail: reached ? "Não foi possível agora." : `Chega com: ${getMarketEra(PET_FIRST_ERA).name}`,
				}),
			],
		});
	}
	const happy = getPetHappyLeftMs(pet, now);
	const cooldown = getPetCooldownLeftMs(pet, now);
	return card("Mascote caramelo", {
		eyebrow: happy > 0 ? "FELIZ" : "NA PORTA",
		icon: PET_ICON,
		tone: happy > 0 ? "success" : "featured",
		subtitle: "Faça carinho para ele ficar feliz: por um minuto, mais clientes entram no mercado.",
		lines: [
			happy > 0 ? `Feliz por mais ${seconds(happy)} s · +5% de clientes` : "Esperando um carinho",
			`Carinhos hoje: ${pet.petsDay === state.day.dayNumber ? pet.petsToday : 0}`,
		],
		buttons: [
			act(cooldown > 0 ? `Carinho em ${seconds(cooldown)} s` : "Fazer carinho", "petDog", [], {
				variant: "success",
				enabled: cooldown <= 0,
				ok: "Ele adorou o carinho!",
				fail: "Ele quer descansar um pouco.",
			}),
		],
	});
}

function cosmeticCard(state: State, id: string): Card | null {
	const item = getPetCosmetic(id);
	if (!item) return null;
	const pet = normalizePetState(state.pet);
	const owned = pet.owned.includes(id);
	const locked = state.market.level < item.requiredLevel;
	const wearable = item.kind === "collar" || item.kind === "bandana" || item.kind === "bedStyle";
	const equipped =
		(item.kind === "collar" && pet.collar === id) ||
		(item.kind === "bandana" && pet.bandana === id) ||
		(item.kind === "bedStyle" && pet.bedStyle === id) ||
		(item.kind === "bed" && pet.hasBed) ||
		(item.kind === "bowls" && pet.hasBowls);
	const diamonds = item.currency === "diamonds";
	const affordable = diamonds || state.coins >= item.price;
	const buttons = owned
		? wearable
			? [
					equipped
						? item.kind === "bandana"
							? act("Tirar", "equipPetCosmetic", [""], { variant: "secondary", ok: "Bandana guardada." })
							: act("Usando", "equipPetCosmetic", [id], { variant: "secondary", enabled: false })
						: act("Usar", "equipPetCosmetic", [id], { variant: "primary", ok: item.kind === "bedStyle" ? `${item.name} nas caminhas!` : `${item.name} no Caramelo!` }),
				]
			: []
		: [
				act(locked ? `Nível ${item.requiredLevel}` : fmt(item.price), "buyPetCosmetic", [id], {
					variant: diamonds ? "gem" : "coin",
					icon: locked ? "" : gameIcon(diamonds ? "diamond" : "coin"),
					// too few diamonds opens the diamond store (desktop/host.ts)
					enabled: pet.adopted && !locked && affordable,
					ok: `Comprado: ${item.name}!`,
					fail: !pet.adopted ? "Adote o cachorro primeiro." : locked ? `Nível ${item.requiredLevel}` : diamonds ? "Diamantes insuficientes" : "Moedas insuficientes",
				}),
			];
	return card(item.name, {
		eyebrow: locked ? `NÍVEL ${item.requiredLevel}` : kindLabels[item.kind] ?? "",
		icon: PET_ICON,
		tone: locked || !pet.adopted ? "locked" : equipped ? "success" : "",
		badge: equipped ? (wearable ? "Usando" : "No mercado") : owned ? "Seu" : "",
		subtitle: item.description,
		buttons,
	});
}

/** One of his beds: a decoration bought here (or in Decoração) and placed in the build mode, inside or outside. */
function bedCard(state: State, id: string): Card | null {
	const decor = getInteriorDecor(id);
	if (!decor) return null;
	const pet = normalizePetState(state.pet);
	const locked = state.market.level < decor.requiredLevel;
	const owned = state.interior.owned[id] ?? 0;
	const placed = state.interior.items.some((item) => item.type === id && !item.stored);
	const diamonds = !decor.coinPrice;
	const price = (diamonds ? decor.diamondPrice : decor.coinPrice) ?? 0;
	return card(decor.name, {
		eyebrow: locked ? `NÍVEL ${decor.requiredLevel}` : "CAMINHA",
		icon: decorIcon(id),
		tone: locked || !pet.adopted ? "locked" : placed ? "success" : "",
		badge: placed ? "No mercado" : owned > 0 ? `x${owned}` : "",
		subtitle: decor.description,
		buttons: [
			...(owned > 0
				? [placeButton(placed ? "Mudar de lugar" : "Colocar")]
				: [
						act(locked ? `Nível ${decor.requiredLevel}` : fmt(price), "purchaseDecor", [id, diamonds ? "diamonds" : "coins"], {
							variant: diamonds ? "gem" : "coin",
							icon: locked ? "" : gameIcon(diamonds ? "diamond" : "coin"),
							enabled: pet.adopted && !locked && (diamonds || state.coins >= price),
							ok: `${decor.name} comprada! Coloque onde quiser no modo construir.`,
							fail: !pet.adopted ? "Adote o cachorro primeiro." : locked ? `Nível ${decor.requiredLevel}` : diamonds ? "Diamantes insuficientes" : "Moedas insuficientes",
						}),
					]),
		],
	});
}

/** Decoração › Caramelo: the dog, his beds (build-mode decorations) and the beds' fabrics, then his cosmetics. */
export function petCards(state: State): Card[] {
	const pet = normalizePetState(state.pet);
	const shown = petCosmetics.filter((item) => !item.hidden || pet.owned.includes(item.id));
	return [
		dogCard(state),
		...PET_BED_DECOR_IDS.flatMap((id) => bedCard(state, id) ?? []),
		...shown.filter((item) => item.kind === "bedStyle").flatMap((item) => cosmeticCard(state, item.id) ?? []),
		...shown.filter((item) => item.kind !== "bedStyle").flatMap((item) => cosmeticCard(state, item.id) ?? []),
	];
}

/** Why the thief or the dog refused (desktop/host.ts rejectionReason); null = not theirs to explain. */
export function getSecurityPetRejection(state: GameState, action: string, now: number): string | null {
	if (action === "catchThief") {
		const thief = normalizeStoreSecurityState(state.security).thief;
		return thief?.phase === "entering" ? THIEF_NOT_YET_MESSAGE : THIEF_GONE_MESSAGE;
	}
	const pet = normalizePetState(state.pet);
	if (action === "petDog") {
		if (!pet.adopted) return "Adote o cachorro primeiro.";
		const cooldown = getPetCooldownLeftMs(pet, now);
		if (cooldown > 0) return `Ele quer descansar um pouco. Faça carinho de novo em ${seconds(cooldown)} s.`;
	}
	if (action === "buyPetCosmetic" || action === "equipPetCosmetic") {
		if (!pet.adopted) return "Adote o cachorro primeiro.";
	}
	return null;
}

