declare module "@borndotcom/react-native-godot" {
	import type { ComponentType } from "react";
	import type { ViewProps } from "react-native";

	export type GodotModule = {
		createInstance(args: string[]): unknown;
		getInstance(): unknown;
		API(): any;
		runOnGodotThread<T>(worklet: () => T): Promise<T>;
	};

	export const RTNGodot: GodotModule;
	export const RTNGodotView: ComponentType<ViewProps & { windowName?: string }>;
	export function runOnGodotThread<T>(worklet: () => T): Promise<T>;
}
