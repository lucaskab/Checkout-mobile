import { useCallback, useEffect, useState } from "react";
import { AppState } from "react-native";
import UnityView from "@azesmway/react-native-unity";
import type { SimulatorPanel } from "@/@types/simulator";
import { createSimulatorCommandHandler } from "@/services/simulator-protocol";
import { createSimulatorSnapshot } from "@/services/simulator-snapshot";
import { useGameStore } from "@/stores/game-store";

type UnityMessageHandler = (message: string) => void;
type CheckoutGlobal = typeof globalThis & {
	__checkoutUnityMessage?: UnityMessageHandler;
};
const checkoutGlobal = globalThis as CheckoutGlobal;

const panels: SimulatorPanel[] = [
	"store",
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
	openPanel: (panel: SimulatorPanel) => void,
) {
	const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
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
					openPanel(message.panel);
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
	}, [openPanel, unityRef]);
	const onUnityMessage = useCallback(
		(event: { nativeEvent: { message: string } }) => {
			checkoutGlobal.__checkoutUnityMessage?.(event.nativeEvent.message);
		},
		[],
	);
	return { status, onUnityMessage };
}
