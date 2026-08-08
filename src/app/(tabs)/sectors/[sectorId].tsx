import { useLocalSearchParams } from "expo-router";
import { SectorDetailScreen } from "@/screens/sector-detail";

export default function SectorDetail() {
	const { sectorId } = useLocalSearchParams<{ sectorId: string }>();

	return <SectorDetailScreen sectorId={sectorId} />;
}
