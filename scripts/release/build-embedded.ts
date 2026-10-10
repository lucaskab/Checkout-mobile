// @ts-nocheck: Bun-only script (the repo's tsc has no Bun types).
// Bundles the game host (store, timers, pages: desktop/host.ts) into one JavaScript file that the Unity player runs
// inside itself on the iPhone (JavaScriptCore, Assets/Plugins/iOS/CheckoutJS.mm), so the iOS build is the whole
// game on its own: no separate program, no React Native app around it.
//   bun scripts/release/build-embedded.ts
// Output: unity/CheckoutSimulator/Assets/Resources/CheckoutGame/game.txt (a TextAsset).
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dir, "../..");
const embedded = resolve(root, "desktop/embedded");
const out = resolve(root, "unity/CheckoutSimulator/Assets/Resources/CheckoutGame");

const iphone: import("bun").BunPlugin = {
	name: "checkout-embedded",
	setup(build) {
		// Node modules the host uses become small stand-ins; the save goes through the native plugin.
		build.onResolve({ filter: /^@\/storage\/mmkv$/ }, () => ({ path: resolve(embedded, "storage.ts") }));
		build.onResolve({ filter: /^(node:)?readline$/ }, () => ({ path: resolve(embedded, "readline.ts") }));
		build.onResolve({ filter: /^(node:)?path$/ }, () => ({ path: resolve(embedded, "path.ts") }));
		build.onResolve({ filter: /^(node:)?(fs|url|module)$/ }, (args) => {
			throw new Error(`the embedded build cannot use ${args.path} (imported by ${args.importer})`);
		});
		// require("…png"): the path itself is the icon id (desktop/view-kit.ts keeps the basename).
		// (resolved by name only, so the build does not need the image files).
		build.onResolve({ filter: /\.(png|jpe?g|webp|gif)$/ }, (args) => ({
			path: resolve(args.resolveDir, args.path).replace(/\\/g, "/"),
			namespace: "image-id",
		}));
		build.onLoad({ filter: /.*/, namespace: "image-id" }, (args) => ({
			contents: `module.exports = ${JSON.stringify(args.path)};`,
			loader: "js",
		}));
	},
};

const result = await Bun.build({
	entrypoints: [resolve(embedded, "entry.ts")],
	target: "browser",
	format: "iife",
	// Like the testers' build: no Dev tab, no dev pages and no dev actions on the phone.
	define: { __DEV__: "false", "process.env.NODE_ENV": '"production"' },
	minify: true,
	plugins: [iphone],
});
if (!result.success) {
	for (const log of result.logs) console.error(log);
	process.exit(1);
}
mkdirSync(out, { recursive: true });
const code = await result.outputs[0].text();
writeFileSync(resolve(out, "game.txt"), code);
console.log(`ok ${(code.length / 1024).toFixed(0)} KB -> ${resolve(out, "game.txt")}`);
