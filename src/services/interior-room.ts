// Room on the shop floor for the pieces the player could buy next (Lucas 24/10: a player bought a freezer and had
// nowhere to put it). Unity measures it on the real floor (CheckoutInterior.Room.cs): with the pieces already
// standing and the ones still in the inventory put in first, it tries to fit each next piece (the next shelf, every
// sector not built yet, the second checkout, the self-checkout kiosks) and sends the ones that do not fit:
//   { kind: "room", blocked: ["shelf:pizza", "sector:padaria"] }   (desktop/host.ts)
// Those cannot be bought until the player makes room (moves or stores furniture and decorations) or the market
// grows. Nothing is blocked until Unity has measured (the app, tests), and nothing of this is saved.

/** Shown on the buy button of a piece that does not fit. */
export const NO_ROOM_REASON = "Sem espaço na loja";
/** Shown under it: what the player can do. */
export const NO_ROOM_HINT = "Mova ou guarde móveis e decorações no modo construir, ou cresça o mercado.";

let blocked = new Set<string>();

/** Unity's measurement. Returns true when it changed (the pages then redraw). */
export function setInteriorNoRoom(ids: unknown): boolean {
	const next = new Set(
		Array.isArray(ids) ? ids.filter((id): id is string => typeof id === "string" && id.length < 64).slice(0, 64) : [],
	);
	if (next.size === blocked.size && [...next].every((id) => blocked.has(id))) return false;
	blocked = next;
	return true;
}

/** Piece ids as Unity names them: "shelf:pizza", "sector:padaria", "checkout:extra", "kiosk:1". */
export function hasInteriorRoom(pieceId: string) {
	return !blocked.has(pieceId);
}

/** The piece a shop item puts on the floor (the builders install it), if any. */
export function getShopItemPieceId(itemId: string) {
	if (itemId === "extra-checkout") return "checkout:extra";
	if (itemId === "self-checkout") return "kiosk:1";
	return null;
}
