// Lets Node run the app's TypeScript sources unchanged: resolves the "@/" alias and
// extensionless imports, and swaps the MMKV storage for a JSON file on disk.
import { existsSync, statSync } from "node:fs";
import { dirname, resolve as resolvePath } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const desktop = dirname(fileURLToPath(import.meta.url));
const source = resolvePath(desktop, "../src");
const overrides = { "@/storage/mmkv": resolvePath(desktop, "storage.ts") };

function file(base) {
	for (const candidate of [base, `${base}.ts`, `${base}/index.ts`])
		if (existsSync(candidate) && statSync(candidate).isFile()) return candidate;
	return null;
}

export async function resolve(specifier, context, next) {
	let base = null;
	if (overrides[specifier]) base = overrides[specifier];
	else if (specifier.startsWith("@/"))
		base = resolvePath(source, specifier.slice(2));
	else if (specifier.startsWith(".") && context.parentURL?.startsWith("file:"))
		base = resolvePath(dirname(fileURLToPath(context.parentURL)), specifier);
	const found = base && file(base);
	if (!found) return next(specifier, context);
	return {
		url: pathToFileURL(found).href,
		format: found.endsWith(".ts") ? "module-typescript" : undefined,
		shortCircuit: true,
	};
}
