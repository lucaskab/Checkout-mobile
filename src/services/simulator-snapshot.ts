import type { GameState } from "@/@types/game";
import type { SimulatorSnapshot } from "@/@types/simulator";
import { getGameEvent } from "@/data/game-events";
import { marketExpansions } from "@/data/market-expansions";
import { itemCatalog, shelves } from "@/data/market-products";
import {
	productionRecipes,
	productionSectors,
} from "@/data/production-sectors";
import {
	getShelfCapacity,
	initialUnlockedShelfSlots,
	shelfSlotUpgrades,
} from "@/data/shelf-capacity";
import { getPhysicalShelfId, getShelfSlotIds } from "@/data/shelf-slots";
import { getActiveGameEventEffects } from "@/services/game-events";
import { getClaimableMissionCount } from "@/services/missions";
import { getExperienceToNextLevel } from "@/services/progression";
export function createSimulatorSnapshot(
	state: GameState,
	session: string,
	revision: number,
	now = Date.now(),
): SimulatorSnapshot {
	const active =
		state.events.activeEvent && state.events.activeEvent.endsAt > now
			? state.events.activeEvent
			: null;
	const event = getGameEvent(active?.eventId),
		effects = getActiveGameEventEffects(state.events, now);
	return {
		kind: "snapshot",
		protocol: 1,
		session,
		revision,
		sentAt: now,
		coins: state.coins,
		diamonds: state.logistics.premiumCurrency,
		experience: state.market.experience,
		experienceToNextLevel: getExperienceToNextLevel(state.market.level),
		level: state.market.level,
		isOpen: state.market.isOpen,
		satisfaction: state.market.customerSatisfaction,
		served: state.market.customersServed,
		dailyRevenue: state.daily.revenue,
		dailyGoal: state.daily.goal,
		dailyClaimable: state.daily.goalReached && !state.daily.claimed,
		claimableMissions: getClaimableMissionCount(state),
		shelves: shelves.map((s, index) => {
			const slots = getShelfSlotIds(s.id);
			const firstSlot = slots.find((id) => state.shelfAssignments[id]) ?? s.id;
			const id = state.shelfAssignments[firstSlot] ?? 0;
			const product = itemCatalog.find((p) => p.id === id);
			const requiredLevel =
				index < initialUnlockedShelfSlots
					? 1
					: (shelfSlotUpgrades.find(
							(upgrade) => upgrade.unlockedSlots === index + 1,
						)?.playerLevel ?? 1);
			return {
				id: s.id,
				name: s.name ?? s.id,
				productId: id,
				productName: product?.name ?? "Prateleira vazia",
				category: product?.category ?? "",
				stock: slots.reduce(
					(total, id) => total + (state.shelfStock[id] ?? 0),
					0,
				),
				reserve: state.inventory[id] ?? 0,
				price: state.shelfPrices[firstSlot] ?? product?.sellingPrice ?? 0,
				capacity: getShelfCapacity(state.shelfUpgradeLevels[s.id] ?? 0),
				unlocked: index < state.unlockedShelfSlots,
				requiredLevel,
				expiresAt: Math.min(
					...(state.shelfLots[s.id] ?? []).map(
						(l) => l.expiresAt ?? Number.MAX_SAFE_INTEGER,
					),
					Number.MAX_SAFE_INTEGER,
				),
			};
		}),
		sectors: productionSectors.map((s) => ({
			id: s.id,
			name: s.name,
			unlocked: state.market.level >= s.requiredLevel,
			requiredLevel: s.requiredLevel,
			jobs: state.production.jobs.filter((j) => j.sectorId === s.id).length,
		})),
		employees: state.employees.employees,
		orders: state.logistics.orders.map((order) => ({
			...order,
			productCategory:
				itemCatalog.find((product) => product.id === order.productId)
					?.category ?? "",
		})),
		jobs: state.production.jobs,
		customers: state.market.recentCustomers.map((customer) => ({
			...customer,
			purchases: customer.purchases?.map((purchase) => {
				const recipe = productionRecipes.find(
					(r) => r.outputProductId === purchase.productId,
				);
				const sector = productionSectors.find((s) => s.id === recipe?.sectorId);
				return {
					...purchase,
					shelfId:
						sector && state.market.level >= sector.requiredLevel
							? `sector-${sector.id}`
							: getPhysicalShelfId(purchase.shelfId),
				};
			}),
		})),
		expansions: state.unlockedMarketExpansionIds,
		ownedItems: state.shop.ownedItemIds,
		expansionStates: marketExpansions.map((expansion) => ({
			id: expansion.id,
			name: expansion.name,
			requiredLevel: expansion.requiredLevel,
			unlocked: state.unlockedMarketExpansionIds.includes(expansion.id),
		})),
		event: {
			id: event?.id ?? "",
			name: event?.name ?? "",
			description: event?.description ?? "",
			effectLabel: event?.effectLabel ?? "",
			kind: event?.kind ?? "",
			endsAt: active?.endsAt ?? 0,
			arrivalMultiplier: effects.customerArrivalMultiplier,
			productionMultiplier: effects.productionDurationMultiplier,
		},
	};
}
