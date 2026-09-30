import { page, type Page, type State } from "../view-kit";
import { routes as day } from "./day";
import { routes as dev } from "./dev";
import { routes as loja, shopPage } from "./loja";
import { routes as progress } from "./progress";
import { routes as production } from "./production";
import { routes as shelves } from "./shelves";
import { routes as stock } from "./stock";
import { routes as suppliers } from "./suppliers";
import { routes as upgrades } from "./upgrades";

export type Routes = Record<string, (state: State, args: string[]) => Page>;

// A route is "<page>:<arg>:<arg>", e.g. "shelf:dairy" or "order:12:10".
const all: Routes = {
	...shelves,
	...stock,
	...suppliers,
	...production,
	...upgrades,
	...progress,
	...dev,
	...day,
	...loja,
	// Everything that is bought lives in the shop now: the old pages open their shop category.
	team: (state) => shopPage(state, ["equipe"]),
	shop: (state, [category]) => shopPage(state, ["melhorias", category ?? ""]),
	expansions: (state) => shopPage(state, ["expansoes"]),
	currency: (state, [filter]) => shopPage(state, ["moedas", filter ?? ""]),
};

export function pages(state: State, route: string): Page {
	const [name, ...args] = route.split(":");
	const build = all[name];
	if (!build) return page(route, "Em breve", []);
	try {
		return build(state, args);
	} catch (error) {
		return page(route, "Erro ao montar a tela", [], { subtitle: String(error) });
	}
}
