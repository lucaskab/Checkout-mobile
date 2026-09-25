import "./require-shim";
import { useGameStore } from "@/stores/game-store";
import { pages } from "./pages";

// Prints the page for a route: node --import ./desktop/register.mjs desktop/try-page.ts shelf:dairy
console.log = console.info = console.warn = console.error;
for (const route of process.argv.slice(2))
	process.stdout.write(`${JSON.stringify(pages(useGameStore.getState(), route), null, 1)}\n`);
