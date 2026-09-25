import type UnityView from "@azesmway/react-native-unity";
import { type Dispatch, type SetStateAction, useEffect, useState } from "react";
import { AppState } from "react-native";
import type { ProductionSector } from "@/@types/production";
import type { SimulatorPanel } from "@/@types/simulator";
import { shelves } from "@/data/market-products";
import { createSimulatorCommandHandler } from "@/services/simulator-protocol";
import { getUnlockedSimulatorSectorId } from "@/services/simulator-sector-selection";
import { createSimulatorSnapshot } from "@/services/simulator-snapshot";
import { useGameStore } from "@/stores/game-store";

type UnityMessageHandler = (message: string) => void;
type CheckoutGlobal = typeof globalThis & {
	__checkoutUnityMessage?: UnityMessageHandler;
};
const checkoutGlobal = globalThis as CheckoutGlobal;

const panels: SimulatorPanel[] = [
	"store",
	"storage",
	"products",
	"suppliers",
	"sectors",
	"team",
	"shop",
	"expansions",
	"missions",
	"achievements",
	"currency",
];
export function useSimulator(
	unityRef: React.RefObject<UnityView | null>,
	setPanel: Dispatch<SetStateAction<SimulatorPanel | null>>,
	setShelfId: Dispatch<SetStateAction<string | null>>,
	setSectorId: Dispatch<SetStateAction<ProductionSector["id"] | null>>,
) {
	const [status, setStatus] = useState<"loading" | "ready" | "error">(
		"loading",
	);
	useEffect(() => {
		const session = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
		let revision = 0,
			ready = false,
			dirty = true,
			active = true;
		const send = (message: unknown) => {
			try {
				unityRef.current?.postMessage(
					"CheckoutBridge",
					"Receive",
					JSON.stringify(message),
				);
			} catch {
				if (active) setStatus("error");
			}
		};
		const snapshot = () => {
			if (!ready || !active) return;
			dirty = false;
			void send(
				createSimulatorSnapshot(useGameStore.getState(), session, revision),
			);
		};
		const command = createSimulatorCommandHandler(
			session,
			() => useGameStore.getState(),
			() => revision,
		);
		const unsubscribe = useGameStore.subscribe(() => {
			revision++;
			dirty = true;
		});
		const receive = (raw: string) => {
			try {
				const message = JSON.parse(raw);
				if (message.kind === "ready") {
					ready = true;
					setStatus("ready");
					snapshot();
				} else if (message.kind === "panel" && panels.includes(message.panel)) {
					const unlockedSectorId =
						message.panel === "sectors"
							? getUnlockedSimulatorSectorId(
									message.sectorId,
									useGameStore.getState().market.level,
								)
							: null;

					if (
						message.panel === "store" &&
						shelves.some((shelf) => shelf.id === message.shelfId)
					) {
						setSectorId(null);
						setShelfId(message.shelfId);
					} else if (unlockedSectorId) {
						setPanel(null);
						setShelfId(null);
						setSectorId(unlockedSectorId);
					} else {
						setSectorId(null);
						setShelfId(null);
						setPanel(message.panel);
					}
				} else if (message.kind === "command") {
					void send(command(message));
					snapshot();
				} else if (message.kind === "error") {
					setStatus("error");
				}
			} catch {
				setStatus("error");
			}
		};
		checkoutGlobal.__checkoutUnityMessage = receive;
		const timer = setInterval(() => {
			if (dirty) snapshot();
		}, 100);
		const resume = AppState.addEventListener("change", (state) => {
			if (state === "active") {
				dirty = true;
				snapshot();
			}
		});
		const timeout = setTimeout(() => {
			if (!ready) setStatus("error");
		}, 45000);
		return () => {
			active = false;
			unsubscribe();
			delete checkoutGlobal.__checkoutUnityMessage;
			resume.remove();
			clearInterval(timer);
			clearTimeout(timeout);
		};
	}, [setPanel, setSectorId, setShelfId, unityRef]);
	function onUnityMessage(event: { nativeEvent: { message: string } }) {
		checkoutGlobal.__checkoutUnityMessage?.(event.nativeEvent.message);
	}
	return { status, onUnityMessage };
}
