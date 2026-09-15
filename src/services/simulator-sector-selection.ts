import type { ProductionSector } from "@/@types/production";
import { productionSectors } from "@/data/production-sectors";

export function getUnlockedSimulatorSectorId(
	sectorId: unknown,
	level: number,
): ProductionSector["id"] | null {
	const sector = productionSectors.find((item) => item.id === sectorId);

	return sector && level >= sector.requiredLevel ? sector.id : null;
}
