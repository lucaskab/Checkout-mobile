// @ts-nocheck: Bun-only script (the repo's tsc has no Bun types).
// Compiles desktop/host.ts (the game store and HUD views) into stand-alone executables, so the
// release builds of the Unity player run without Node, Bun or the repository on the tester's machine.
//   bun scripts/release/build-host.ts [outDir]     (default: release/hosts)
// Output: checkout-host-win-x64.exe, checkout-host-mac-arm64, checkout-host-mac-x64.
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(import.meta.dir, "../..");
const out = resolve(root, process.argv[2] ?? "release/hosts");
mkdirSync(out, { recursive: true });

const desktopAssets: import("bun").BunPlugin = {
	name: "checkout-desktop",
	setup(build) {
		// The mobile app's MMKV storage becomes a JSON file next to the player's save.
		build.onResolve({ filter: /^@\/storage\/mmkv$/ }, () => ({ path: resolve(root, "desktop/storage.ts") }));
		// require("…png"): on desktop the path itself is the icon id (desktop/view-kit.ts keeps the basename).
		build.onLoad({ filter: /\.(png|jpe?g|webp|gif)$/ }, (args) => ({
			contents: `module.exports = ${JSON.stringify(args.path.replace(/\\/g, "/"))};`,
			loader: "js",
		}));
	},
};

const targets: [Bun.Build.Target, string][] = [
	["bun-windows-x64", "checkout-host-win-x64.exe"],
	["bun-darwin-arm64", "checkout-host-mac-arm64"],
	["bun-darwin-x64", "checkout-host-mac-x64"],
];
// CHECKOUT_HOST_TARGET=bun-linux-x64 builds just that one (to try the host on another machine).
const only = process.env.CHECKOUT_HOST_TARGET;
if (only && !targets.some(([target]) => target === only)) targets.push([only as Bun.Build.Target, `checkout-host-${only.replace("bun-", "")}`]);
let failed = false;
for (const [target, name] of targets) {
	if (only && target !== only) continue;
	const result = await Bun.build({
		entrypoints: [resolve(root, "desktop/host.ts")],
		// Testers get the game without the Dev tab and dev-only actions.
		define: { __DEV__: "false" },
		compile: { target, outfile: resolve(out, name) },
		minify: true,
		plugins: [desktopAssets],
	});
	if (!result.success) {
		failed = true;
		console.error(`FAILED ${target}`);
		for (const log of result.logs) console.error(log);
	} else console.log(`ok ${target} -> ${resolve(out, name)}`);
}
process.exit(failed ? 1 : 0);
