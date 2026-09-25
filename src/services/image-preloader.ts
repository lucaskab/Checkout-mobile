import { Asset } from "expo-asset";
import { gameImageAssets } from "@/data/game-image-assets";

const PRELOAD_BATCH_SIZE = 8;

let preloadPromise: Promise<void> | undefined;

export function preloadGameImages(): Promise<void> {
	if (!preloadPromise) {
		preloadPromise = preloadGameImagesInBatches();
	}

	return preloadPromise;
}

async function preloadGameImagesInBatches() {
	const failedAssets: number[] = [];

	for (
		let index = 0;
		index < gameImageAssets.length;
		index += PRELOAD_BATCH_SIZE
	) {
		const batch = gameImageAssets.slice(index, index + PRELOAD_BATCH_SIZE);
		const results = await Promise.all(
			batch.map(async (source) => {
				try {
					await Asset.loadAsync(source);
					return true;
				} catch {
					try {
						await Asset.loadAsync(source);
						return true;
					} catch {
						return false;
					}
				}
			}),
		);

		results.forEach((loaded, batchIndex) => {
			if (!loaded) {
				failedAssets.push(batch[batchIndex]);
			}
		});
	}

	if (failedAssets.length > 0) {
		console.warn(
			`[ImagePreloader] ${failedAssets.length} game image(s) failed to preload.`,
		);
	}
}
