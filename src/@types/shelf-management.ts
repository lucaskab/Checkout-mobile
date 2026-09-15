export type ShelfManagementProps = { shelfId: string; onClose: () => void };
export type ShelfManagementPage =
	| { kind: "slots" }
	| { kind: "picker"; slotId: string }
	| { kind: "order"; productId: number };
