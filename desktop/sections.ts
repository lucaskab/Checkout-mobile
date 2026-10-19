import type { GameIconId } from "@/data/game-icon-assets";
import { getClaimableMissionCount } from "@/services/missions";
import { button, type Button, gameIcon, type State } from "./view-kit";

// Toolbar groups (Lucas 19/10: "a HUD está muito lotada de botões"). One button in the toolbar opens the group and
// the windows of the group become big tabs in the window's header (Page.sections): Produtos holds the shelves, the
// stock and the deliveries; Missões holds the missions and the trophies.

type Section = {
	/** The window's route ("!<id>" opens it on a fresh stack). */
	id: string;
	label: string;
	icon: GameIconId;
	/** Route names that belong to this section (the shelf window of one fixture is "shelf:<id>"). */
	roots: string[];
};

export type ToolGroup = {
	id: "produtos" | "missoes";
	label: string;
	icon: GameIconId;
	requiredLevel: number;
	sections: Section[];
};

export const toolGroups: ToolGroup[] = [
	{
		id: "produtos",
		label: "Produtos",
		icon: "warehouse",
		requiredLevel: 1,
		sections: [
			{ id: "store", label: "Prateleiras", icon: "shelf", roots: ["store", "shelf"] },
			// Estoque is also the depot (route "storage" opens it on the dock).
			{ id: "products", label: "Estoque", icon: "warehouse", roots: ["products", "storage"] },
			{ id: "suppliers", label: "Entregas", icon: "deliveryTruck", roots: ["suppliers"] },
		],
	},
	{
		id: "missoes",
		label: "Missões",
		icon: "trophy",
		requiredLevel: 1,
		sections: [
			{ id: "missions", label: "Missões", icon: "trophy", roots: ["missions"] },
			{ id: "achievements", label: "Conquistas", icon: "crown", roots: ["achievements"] },
		],
	},
];

const routeRoot = (route: string) => route.split(":")[0] ?? "";

/** The group a route belongs to (by its first name), or null. */
export function groupOf(route: string): ToolGroup | null {
	const root = routeRoot(route);
	return toolGroups.find((group) => group.sections.some((section) => section.roots.includes(root))) ?? null;
}

/** Trucks waiting at the dock to be unloaded (the Estoque tab lights up). */
const trucksAtDock = (state: State) => state.receiving.dock.filter((delivery) => delivery.quantity > delivery.unloaded).length;

function sectionBadge(state: State, id: string, now: number): string {
	if (id === "products") {
		const dock = trucksAtDock(state);
		return dock > 0 ? String(dock) : "";
	}
	if (id === "missions") {
		const claimable = getClaimableMissionCount(state);
		return claimable > 0 ? String(claimable) : "";
	}
	void now;
	return "";
}

/** Where the group's toolbar button goes: the tab with something waiting (trucks at the dock), else the first. */
export function groupRoute(state: State, group: ToolGroup): string {
	if (group.id === "produtos" && trucksAtDock(state) > 0) return "!products";
	return `!${group.sections[0].id}`;
}

/** The big tabs for a window of a group ([] when the route is not in one). */
export function sectionsFor(state: State, route: string, now = Date.now()): Button[] {
	const group = groupOf(route);
	if (!group) return [];
	const root = routeRoot(route);
	return group.sections.map((section) => {
		const active = section.roots.includes(root);
		return button(section.label, {
			icon: gameIcon(section.icon),
			route: `!${section.id}`,
			variant: active ? "coin" : "secondary",
			active,
			badge: sectionBadge(state, section.id, now),
		});
	});
}
