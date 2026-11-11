import { getMarketEra } from "@/data/economy";
import {
	getNextTruckDiamondPrice,
	getNextTruckUnlock,
	getSupplierTrucks,
	MAX_SUPPLIER_TRUCKS,
	type TruckUnlock,
} from "@/data/supplier-capacity";
import { act, type BoardTile, gameIcon, type State, tile } from "../view-kit";

// Supplier trucks and the cart, shared by the Entregas board and the Central logística page (Lucas 11/11):
// one truck at the start, more with the level and the expansions (free) or with diamonds.

/** Boxes waiting in the supplier cart. */
export const cartBoxes = (state: State) => (state.logistics.cart ?? []).reduce((total, line) => total + line.boxes, 0);

/** "Você tem 1 caminhão." / "Você tem 3 caminhões." (whole sentences, so they translate). */
export const trucksText = (trucks: number) => (trucks === 1 ? "Você tem 1 caminhão." : `Você tem ${trucks} caminhões.`);

/** "Nível 9" or "Quitanda". */
export function truckUnlockLabel(unlock: TruckUnlock) {
	return unlock.kind === "level" ? `Nível ${unlock.level}` : getMarketEra(unlock.eraId).name;
}

/** The next free truck in words ("Próximo caminhão grátis: Nível 9" / "…: Quitanda"). */
export function nextTruckText(state: State) {
	const next = getNextTruckUnlock(state);
	return next ? `Próximo caminhão grátis: ${truckUnlockLabel(next)}` : "";
}

/** The button that buys one more truck with diamonds (null when no more can be bought). */
export function buyTruckButton(state: State) {
	const price = getNextTruckDiamondPrice(state);
	if (price === null) return null;
	const after = getSupplierTrucks(state) + 1;
	return act(`Comprar caminhão · ${price}`, "upgradeSupplierOrderSlots", ["diamonds"], {
		variant: "gem",
		icon: gameIcon("diamond"),
		ok: `Agora você tem ${after} caminhões!`,
		fail: "Diamantes insuficientes.",
	});
}

/** The lane after the trucks: the next free one and the diamond purchase (null at the maximum). */
export function truckLane(state: State): BoardTile | null {
	const trucks = getSupplierTrucks(state);
	if (trucks >= MAX_SUPPLIER_TRUCKS) return null;
	const next = getNextTruckUnlock(state);
	const buy = buyTruckButton(state);
	if (!next && !buy) return null;
	return tile("slotnext", "Mais um caminhão", {
		group: "CAMINHÕES NA ESTRADA",
		icon: gameIcon("deliveryTruck"),
		subtitle: next ? nextTruckText(state) : "Mais caminhões = mais pedidos ao mesmo tempo",
		sticker: next ? (next.kind === "level" ? `NV ${next.level}` : getMarketEra(next.eraId).name) : "NOVA PISTA",
		tone: buy ? "gold" : "locked",
		state: buy ? "" : "locked",
		detail: `${trucksText(trucks)} Cada caminhão leva um pedido com vários produtos. ${
			buy
				? "Caminhões novos chegam de graça com o nível e as expansões do mercado, ou na hora com diamantes."
				: "Caminhões novos chegam de graça com o nível e as expansões do mercado."
		}`,
		...(buy ? { action: buy, actions: [buy] } : {}),
		vehicle: "Game/lane_truck",
		lane: "locked",
	});
}
