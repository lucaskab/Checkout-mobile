import type { CustomerArchetype, CustomerSex } from "@/@types/customer-simulation";

// Names of the market's walk-in customers, split by sex so the name always matches the body Unity shows
// (CheckoutBridge picks a walker of the customer's sex). A name belongs to one sex only: sexOfCustomerName
// reads old saves (customers saved without a sex) back from the name.
// Before 11/2026 every archetype had names of a single sex and Unity drew the body at random, so the
// checkout card often said "Ana" over a man (Lucas, 08/11).
export const customerNames: Record<CustomerArchetype, Record<CustomerSex, readonly string[]>> = {
	economico: { f: ["Ana", "Paula", "Rita"], m: ["José", "Antônio", "Raul"] },
	familia: { f: ["Juliana", "Carla", "Patrícia"], m: ["Marcos", "Davi", "Lucas"] },
	impulsivo: { f: ["Bia", "Nina", "Lara"], m: ["Léo", "Theo", "Gui"] },
	normal: { f: ["Júlia", "Camila", "Luana"], m: ["Caio", "Igor", "Pedro"] },
	premium: { f: ["Helena", "Clara", "Sofia"], m: ["Henrique", "Otávio", "Eduardo"] },
};

const sexByName = new Map<string, CustomerSex>(
	Object.values(customerNames).flatMap((names) =>
		(Object.keys(names) as CustomerSex[]).flatMap((sex) => names[sex].map((name) => [name, sex] as const)),
	),
);

/** The sex a customer name belongs to; undefined for a name not in the lists (Unity then takes any body). */
export function sexOfCustomerName(name: string): CustomerSex | undefined {
	return sexByName.get(name);
}

// Scrambles the market's running seed (consecutive customers have consecutive seeds) into an even spread.
function mixSeed(seed: number) {
	let h = (Math.trunc(seed) ^ 0x9e3779b9) >>> 0;
	h = Math.imul(h ^ (h >>> 16), 0x85ebca6b) >>> 0;
	h = Math.imul(h ^ (h >>> 13), 0xc2b2ae35) >>> 0;
	return (h ^ (h >>> 16)) >>> 0;
}

/** A new customer's sex (half women, half men) and a name of that sex from their archetype's list. */
export function pickCustomerIdentity(archetype: CustomerArchetype, seed: number): { name: string; sex: CustomerSex } {
	const mixed = mixSeed(seed);
	const sex: CustomerSex = mixed % 2 === 0 ? "f" : "m";
	const names = (customerNames[archetype] ?? customerNames.normal)[sex];
	return { name: names[Math.floor(mixed / 2) % names.length], sex };
}
