import { plugin } from "bun";
import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

// Toolbar groups (desktop/sections.ts, Lucas 19/10): Produtos = Prateleiras · Estoque · Entregas and Missões =
// Missões · Conquistas, one toolbar button each, the windows switching through big header tabs (Page.sections).
plugin({
	name: "png-as-id",
	setup(build) {
		build.onLoad({ filter: /\.png$/ }, (args) => ({
			contents: `const path = ${JSON.stringify(args.path)}; export default path; export const toString = () => path;`,
			loader: "js",
		}));
	},
});
globalThis.__DEV__ = false;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../src/stores/game-store.ts");
const { pages } = await import("./pages/index.ts");
const { createDesktopView } = await import("./view.ts");

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();
const labels = (buttons) => buttons.map((b) => b.label);

describe("toolbar groups", () => {
	test("the toolbar has one button per group instead of one per window", () => {
		const tools = labels(createDesktopView(store(), 1, []).tools);
		expect(tools).toEqual(["Loja", "Produtos", "Produção", "Missões"]);
	});

	test("Produtos opens Prateleiras, or Estoque when trucks wait at the dock", () => {
		const tool = () => createDesktopView(store(), 1, []).tools.find((b) => b.label === "Produtos");
		expect(tool().route).toBe("!store");
		useGameStore.setState({
			receiving: { ...store().receiving, dock: [{ id: "d1", productId: "arroz", quantity: 10, unloaded: 0, arrivedAt: Date.now() }] },
		});
		expect(tool().route).toBe("!products");
		expect(tool().badge).toBe("1");
	});

	test("the group button lights up on any of its windows", () => {
		for (const route of ["store", "products:doca", "storage", "suppliers:estrada"]) {
			const tool = createDesktopView(store(), 1, [route]).tools.find((b) => b.label === "Produtos");
			expect(tool.active).toBe(true);
		}
		const missions = createDesktopView(store(), 1, ["achievements"]).tools.find((b) => b.label === "Missões");
		expect(missions.active).toBe(true);
	});

	test("each window of a group carries its siblings as header tabs, the open one marked", () => {
		for (const [route, active] of [
			["store", "Prateleiras"],
			["products", "Estoque"],
			["suppliers", "Entregas"],
		]) {
			const sections = pages(store(), route).sections;
			expect(labels(sections)).toEqual(["Prateleiras", "Estoque", "Entregas"]);
			expect(sections.find((s) => s.active).label).toBe(active);
			expect(sections.map((s) => s.route)).toEqual(["!store", "!products", "!suppliers"]);
		}
		expect(labels(pages(store(), "missions").sections)).toEqual(["Missões", "Conquistas"]);
		expect(labels(pages(store(), "achievements").sections)).toEqual(["Missões", "Conquistas"]);
	});

	test("windows outside the groups and the side drawers have no header tabs", () => {
		expect(pages(store(), "loja").sections).toEqual([]);
		expect(pages(store(), "shelves").sections).toEqual([]);
	});

	test("the corner buttons fold into one Bônus button with a count of what is waiting", () => {
		const view = createDesktopView(store(), 1, []);
		const waiting = view.quick.filter((b) => b.badge !== "").length;
		expect(view.quickMain.label).toBe("Bônus");
		expect(view.quickMain.badge).toBe(waiting > 0 ? String(waiting) : "");
		expect(view.quick.map((b) => b.label)).toContain("Presente");
	});
});
