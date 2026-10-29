/**
 * Local estimate of the Worker's CPU time per upload/download size (npm run bench). Runs the same JavaScript the Worker
 * runs (V8 here too) on synthetic saves shaped like the game's; the real figure comes from the deployed Worker's logs
 * (cpuTime), see README.md › Limites. Storage calls (D1/R2) are not counted: they wait on the network, not the CPU.
 */
import { readUpload } from "../src/save.ts";

export function syntheticSave(targetBytes: number) {
	const state: Record<string, unknown> = { coins: 12345, era: { id: "mesinha" }, market: { level: 7 }, logistics: { premiumCurrency: 120 }, day: { dayNumber: 30 } };
	const items: unknown[] = [];
	state.items = items;
	let size = 0;
	for (let i = 0; size < targetBytes; i++) {
		const item = { id: `item-${i}`, name: `Produto ${i} pão`, price: i * 1.5, qty: i % 17, pos: { x: i % 40, y: (i * 7) % 30, r: 90 }, tags: ["a", "b"], flags: { sold: i % 2 === 0, locked: false } };
		items.push(item);
		size += JSON.stringify(item).length + 1;
	}
	return JSON.stringify({ state, version: 45 });
}

const cpu = (work: () => void, runs: number) => {
	work();
	const start = process.cpuUsage();
	for (let i = 0; i < runs; i++) work();
	const used = process.cpuUsage(start);
	return (used.user + used.system) / 1000 / runs;
};

const encoder = new TextEncoder();
for (const size of [50_000, 500_000, 2_000_000]) {
	const data = syntheticSave(size);
	const body = encoder.encode(`{"baseRevision":3,"data":${JSON.stringify(data)},"deviceId":"phone-a","force":false}`);
	const put = cpu(() => readUpload(new Uint8Array(body.buffer.slice(0))), 20);
	const literal = encoder.encode(JSON.stringify(data));
	const get = cpu(() => new Blob(['{"revision":3,"data":', literal, "}"]), 20);
	console.log(`save ${(encoder.encode(data).length / 1000).toFixed(0)} KB (body ${(body.length / 1000).toFixed(0)} KB): PUT ≈ ${put.toFixed(2)} ms CPU, GET ≈ ${get.toFixed(2)} ms CPU`);
}
