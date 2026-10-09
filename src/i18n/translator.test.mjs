import { expect, test } from "bun:test";
import { getLanguage, localizeSnapshot, localizeView, setLanguage, t } from "@/i18n";
import { Translator } from "@/i18n/translator";

test("exact texts, patterns and pieces", () => {
	const tr = new Translator({
		Batata: "Potato",
		"Tomate": "Tomato",
		"Aceita: {0}.": "Accepts: {0}.",
		"Pedido de {0} {1} confirmado!": "Order of {0} {1} confirmed!",
		"Próximo: {0}{1} · nível {2}": "Next: {0}{1} · level {2}",
		" e ": " and ",
	});
	expect(tr.translate("Batata")).toBe("Potato");
	expect(tr.translate("BATATA")).toBe("POTATO");
	expect(tr.translate("Pedido de 3 Batata confirmado!")).toBe("Order of 3 Potato confirmed!");
	expect(tr.translate("Aceita: tomate e batata.")).toBe("Accepts: tomato and potato.");
	expect(tr.translate("Próximo: Batata +2 · nível 4")).toBe("Next: Potato +2 · level 4");
	// Unknown texts stay as they are.
	expect(tr.translate("Texto novo")).toBe("Texto novo");
});

test("pages keep their ids and routes", () => {
	setLanguage("en");
	expect(getLanguage()).toBe("en");
	const view = localizeView({ kind: "view", tools: [{ label: "Estoque", route: "!products", icon: "Icons/warehouse" }] });
	expect(view.tools[0]).toEqual({ label: "Stock", route: "!products", icon: "Icons/warehouse" });
	const snapshot = localizeSnapshot({ shelves: [{ id: "produce", name: "Caixotes de hortifrúti", category: "hortifruti" }] });
	expect(snapshot.shelves[0].id).toBe("produce");
	expect(snapshot.shelves[0].category).toBe("hortifruti");
	expect(snapshot.shelves[0].name).not.toBe("Caixotes de hortifrúti");
	setLanguage("pt");
	expect(t("Estoque")).toBe("Estoque");
});
