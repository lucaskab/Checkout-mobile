import {
	ModalBottomSheet,
	BottomSheetProvider as NativeBottomSheetProvider,
} from "@swmansion/react-native-bottom-sheet";
import {
	cloneElement,
	createContext,
	type Dispatch,
	isValidElement,
	type ReactNode,
	type SetStateAction,
	useContext,
	useEffect,
	useRef,
	useState,
} from "react";
import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";
import { useGameStore } from "@/stores/game-store";

type BottomSheetContextValue = {
	closeBottomSheet: () => void;
	openBottomSheet: (content: ReactNode) => void;
	setHeaderColor: Dispatch<SetStateAction<string>>;
};

const BottomSheetContext = createContext<BottomSheetContextValue | null>(null);
const DEFAULT_HEADER_COLOR = "#FFFFFF";

type BottomSheetProviderProps = {
	children: ReactNode;
};

export function BottomSheetProvider({ children }: BottomSheetProviderProps) {
	const [content, setContent] = useState<ReactNode>(null);
	const [index, setIndex] = useState(0);
	const [headerColor, setHeaderColor] = useState(DEFAULT_HEADER_COLOR);
	const isOpenRef = useRef(false);

	useEffect(
		() =>
			useGameStore.subscribe(() => {
				if (!isOpenRef.current) {
					return;
				}

				setContent((currentContent) =>
					isValidElement(currentContent)
						? cloneElement(currentContent)
						: currentContent,
				);
			}),
		[],
	);

	function openBottomSheet(bottomSheetContent: ReactNode) {
		isOpenRef.current = true;
		setHeaderColor(DEFAULT_HEADER_COLOR);
		setContent(bottomSheetContent);
		setIndex(1);
	}

	function closeBottomSheet() {
		isOpenRef.current = false;
		setHeaderColor(DEFAULT_HEADER_COLOR);
		setIndex(0);
	}

	function handleIndexChange(nextIndex: number) {
		isOpenRef.current = nextIndex > 0;
		if (nextIndex === 0) {
			setHeaderColor(DEFAULT_HEADER_COLOR);
		}
		setIndex(nextIndex);
	}

	function handleSettle(settledIndex: number) {
		if (settledIndex === 0 && !isOpenRef.current) {
			setContent(null);
		}
	}

	return (
		<BottomSheetContext.Provider
			value={{ closeBottomSheet, openBottomSheet, setHeaderColor }}
		>
			<NativeBottomSheetProvider>
				{children}
				<ModalBottomSheet
					detents={[0, "content"]}
					index={index}
					onIndexChange={handleIndexChange}
					onSettle={handleSettle}
					scrimColor="rgba(0, 0, 0, 0.32)"
					surface={
						<View
							style={[
								StyleSheet.absoluteFill,
								styles.surface,
								{ backgroundColor: headerColor },
							]}
						/>
					}
				>
					<View style={styles.content}>
						<View style={styles.indicator} />
						{content}
					</View>
				</ModalBottomSheet>
			</NativeBottomSheetProvider>
		</BottomSheetContext.Provider>
	);
}

export function useBottomSheet() {
	const context = useContext(BottomSheetContext);

	if (context === null) {
		throw new Error("useBottomSheet must be used within BottomSheetProvider.");
	}

	return context;
}

export function useBottomSheetHeaderColor(color: string) {
	const { setHeaderColor } = useBottomSheet();

	useEffect(() => {
		setHeaderColor(color);
	}, [color, setHeaderColor]);
}

const styles = StyleSheet.create({
	content: {
		paddingTop: 12,
		paddingBottom: 24,
	},
	indicator: {
		alignSelf: "center",
		width: 36,
		height: 4,
		marginBottom: 16,
		borderRadius: 999,
		backgroundColor: "#D1D5DB",
	},
	surface: {
		borderTopLeftRadius: 24,
		borderTopRightRadius: 24,
	},
});
