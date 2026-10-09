// Which game texts have no translation yet.
//   node scripts/i18n/missing.cjs        → writes scripts/i18n/missing.json ({ text, where } for each new text)
// Translate those entries and add them to every file in src/i18n/locales (same key, the Portuguese text).
// Unity's own texts (C#) are scanned too: plain "literals" and $"interpolated {x}" strings.
const fs = require("fs"), path = require("path");
const root = path.resolve(__dirname, "../..");
const found = require("./extract-ts.cjs").map((o) => ({ text: o.text, where: `${o.file}:${o.line}` }));
const csRoot = path.join(root, "unity/CheckoutSimulator/Assets/Scripts");
const PT = /[ãõçáéíóúâêôàÃÕÇÁÉÍÓÚÂÊÔ]|\b(de|da|do|para|com|sem|não|seu|sua|um|uma|no|na|em|por|mais|menos|agora|moedas|loja|estoque|caixa|clientes?|produtos?|prateleiras?|mercado|pedido|entrega|obras?|lote|terreno|limpar|voltar|jogar|pronto|toque|clique|arraste|coloque)\b/i;
(function walk(dir) {
	for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
		const file = path.join(dir, entry.name);
		if (entry.isDirectory()) { if (entry.name !== "Editor") walk(file); continue; }
		if (!entry.name.endsWith(".cs") || /AutoTest|Playtest|Preview/.test(entry.name)) continue;
		const code = fs.readFileSync(file, "utf8").replace(/\/\/[^\n]*/g, "");
		for (const m of code.matchAll(/(\$?)"((?:[^"\\\n]|\\.)*)"/g)) {
			if (/(==|!=)\s*$/.test(code.slice(Math.max(0, m.index - 4), m.index))) continue;
			let i = 0;
			const text = (m[1] ? m[2].replace(/\{[^{}]*\}/g, () => `{${i++}}`) : m[2]).replace(/\\n/g, "\n").replace(/\\"/g, '"');
			if (/\p{L}{2}/u.test(text.replace(/\{\d+\}/g, "")) && PT.test(text) && !/^[\w\-./]+$/.test(text))
				found.push({ text, where: `${path.relative(root, file)}:${code.slice(0, m.index).split("\n").length}` });
		}
	}
})(csRoot);
// A text is known when any catalog has it (texts that read the same in a language are left out of that file).
const keys = new Set();
for (const file of fs.readdirSync(path.join(root, "src/i18n/locales"))) {
	const catalog = fs.readFileSync(path.join(root, "src/i18n/locales", file), "utf8");
	for (const m of catalog.matchAll(/^\t("(?:[^"\\]|\\.)*"):/gm)) keys.add(JSON.parse(m[1]));
}
const seen = new Set();
const missing = found.filter((o) => !keys.has(o.text) && !seen.has(o.text) && seen.add(o.text));
fs.writeFileSync(path.join(__dirname, "missing.json"), JSON.stringify(missing, null, "\t"));
console.log(`${missing.length} texts without translation → scripts/i18n/missing.json`);
