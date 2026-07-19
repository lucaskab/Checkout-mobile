import {
	ModalBottomSheet,
	BottomSheetProvider as NativeBottomSheetProvider,
} from "@swmansion/react-native-bottom-sheet";
import { createContext, type ReactNode, useContext, useState } from "react";
import { View } from "react-native";
import { StyleSheet } from "react-native-unistyles";

type BottomSheetContextValue = {
	closeBottomSheet: () => void;
	openBottomSheet: (content: ReactNode) => void;
};

const BottomSheetContext = createContext<BottomSheetContextValue | null>(null);

type BottomSheetProviderProps = {
	children: ReactNode;
};

export function BottomSheetProvider({ children }: BottomSheetProviderProps) {
	const [content, setContent] = useState<ReactNode>(null);
	const [index, setIndex] = useState(0);

	function openBottomSheet(bottomSheetContent: ReactNode) {
		setContent(bottomSheetContent);
		setIndex(1);
	}

	function closeBottomSheet() {
		setIndex(0);
	}

	function handleIndexChange(nextIndex: number) {
		setIndex(nextIndex);
	}

	function handleSettle(settledIndex: number) {
		if (settledIndex === 0) {
			setContent(null);
		}
	}

	return (
		<BottomSheetContext.Provider value={{ closeBottomSheet, openBottomSheet }}>
			<NativeBottomSheetProvider>
				{children}
				<ModalBottomSheet
					detents={[0, "content"]}
					index={index}
					onIndexChange={handleIndexChange}
					onSettle={handleSettle}
					scrimColor="rgba(0, 0, 0, 0.32)"
					surface={<View style={[StyleSheet.absoluteFill, styles.surface]} />}
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
		backgroundColor: "#FFFFFF",
	},
});
