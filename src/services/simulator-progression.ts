import type { SimulatorUnlock } from "@/@types/simulator";
import { employeeDefinitions } from "@/data/employees";
import { itemCatalog } from "@/data/market-products";
import { productionSectors } from "@/data/production-sectors";
import { shopItems } from "@/data/shop-items";

const priority: Record<SimulatorUnlock["type"], number> = {
	sector: 0,
	expansion: 1,
	employee: 2,
	shelf: 3,
	product: 4,
	shop: 5,
};

export function getNextSimulatorUnlocks(
	level: number,
	unlockedShelfCount: number,
) {
	// Shelves come with the expansions (src/data/shelf-types.ts), not with levels: not in this roadmap.
	void unlockedShelfCount;
	const candidates: SimulatorUnlock[] = [
		...productionSectors.map((sector) => ({
			id: sector.id,
			label: sector.name,
			panel: "sectors" as const,
			requiredLevel: sector.requiredLevel,
			type: "sector" as const,
		})),
		...employeeDefinitions.map((employee) => ({
			id: employee.id,
			label: employee.name,
			panel: "team" as const,
			requiredLevel: employee.level,
			type: "employee" as const,
		})),
		...itemCatalog.map((product) => ({
			id: String(product.id),
			label: product.name,
			panel: "products" as const,
			requiredLevel: product.unlockLevel,
			type: "product" as const,
		})),
		...shopItems.map((item) => ({
			id: item.id,
			label: item.name,
			panel: "shop" as const,
			requiredLevel: item.level,
			type: "shop" as const,
		})),
	]
		.filter((unlock) => unlock.requiredLevel > level)
		.sort(
			(first, second) =>
				first.requiredLevel - second.requiredLevel ||
				priority[first.type] - priority[second.type] ||
				first.label.localeCompare(second.label, "pt-BR"),
		);

	const nextLevel = candidates[0]?.requiredLevel;
	return candidates.filter((unlock) => unlock.requiredLevel === nextLevel);
}
