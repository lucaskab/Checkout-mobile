import { getMarketEra, getNextMarketEra } from "@/data/economy";
import { ERA_LOTS, LOT_GRID, PLAZA_LOTS } from "@/data/market-lots";
import type { GameState } from "@/@types/game";
import type { SimulatorSnapshot } from "@/@types/simulator";
import { getGameEvent } from "@/data/game-events";
import { interiorDecor } from "@/data/interior-decor";
import {
	getMarketExpansionSkipCost,
	marketExpansions,
} from "@/data/market-expansions";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import { itemCatalog, shelves, starterShelfIds } from "@/data/market-products";
import {
	productionRecipes,
	productionSectors,
} from "@/data/production-sectors";
import {
	getNextShelfUnlockUpgrade,
	getShelfCapacity,
} from "@/data/shelf-capacity";
import {
	getPhysicalShelfId,
	getShelfSlotCount,
	getShelfSlotIds,
	productsPerShelf,
	resolveShelfSlotCounts,
} from "@/data/shelf-slots";
import { getActiveGameEventEffects } from "@/services/game-events";
import { getContractProgress } from "@/services/market-day";
import { getIncidentShelves } from "@/services/store-incidents-context";
import { getClaimableMissionCount } from "@/services/missions";
import { getExperienceToNextLevel } from "@/services/progression";
import { getBoxUnits, getWarehouseZone } from "@/services/receiving";
import { getSimulatorLayout } from "@/services/simulator-layout";
import {
	findInteriorConstruction,
	getInteriorBuildName,
	getInteriorSkipCost,
} from "@/data/interior-construction";
export function createSimulatorSnapshot(
	state: GameState,
	session: string,
	revision: number,
	now = Date.now(),
): SimulatorSnapshot {
	const layout = getSimulatorLayout(state.unlockedMarketExpansionIds);
	const shelfSlotCounts = resolveShelfSlotCounts(
		state.shelfSlotCounts,
		state.unlockedShelfSlots,
	);
	const active =
		state.events.activeEvent && state.events.activeEvent.endsAt > now
			? state.events.activeEvent
			: null;
	const event = getGameEvent(active?.eventId),
		effects = getActiveGameEventEffects(state.events, now);
	const dayProgress = getContractProgress(state.day.contract, state.day.stats);
	return {
		layout,
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
			const slotCount = getShelfSlotCount(s.id, shelfSlotCounts);
			const slots = getShelfSlotIds(
				s.id,
				slotCount > 0 ? slotCount : productsPerShelf,
			);
			const firstSlot =
				slots.find((id) => state.shelfAssignments[id]) ?? slots[0];
			const id = firstSlot ? (state.shelfAssignments[firstSlot] ?? 0) : 0;
			const product = itemCatalog.find((p) => p.id === id);
			const requiredLevel =
				index < starterShelfIds.length
					? 1
					: (getNextShelfUnlockUpgrade(index)?.playerLevel ?? 1);
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
				price:
					(firstSlot ? state.shelfPrices[firstSlot] : undefined) ??
					product?.sellingPrice ??
					0,
				capacity: getShelfCapacity(state.shelfUpgradeLevels[s.id] ?? 0),
				unlocked: slotCount > 0,
				// Paid for and still being built: Unity shows the works where it will stand.
				building: !!findInteriorConstruction(state.interiorConstructions, "shelf", s.id),
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
			// A sector serves only once it has been built (the level lets the player build it).
			unlocked: state.builtSectorIds.includes(s.id),
			building: !!findInteriorConstruction(state.interiorConstructions, "sector", s.id),
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
						sector &&
						layout.sectorIds.includes(sector.id) &&
						state.builtSectorIds.includes(sector.id)
							? `sector-${sector.id}`
							: getPhysicalShelfId(purchase.shelfId),
				};
			}),
		})),
		expansions: state.unlockedMarketExpansionIds,
		// Stage of the market (0 mesinha … 8 rede) and its evolution obra, if any.
		era: {
			id: state.era.id,
			index: getMarketEra(state.era.id).index,
			name: getMarketEra(state.era.id).name,
			// Lots of the block (see src/data/market-lots.ts): owned now, taken by the next era, square.
			grid: LOT_GRID,
			lots: ERA_LOTS[state.era.id],
			nextLots: ERA_LOTS[(state.era.construction?.eraId ?? getNextMarketEra(state.era.id)?.id) ?? state.era.id],
			nextName: getMarketEra(state.era.construction?.eraId ?? getNextMarketEra(state.era.id)?.id ?? state.era.id).name,
			plazaLots: PLAZA_LOTS,
			construction: state.era.construction
				? {
						eraId: state.era.construction.eraId,
						index: getMarketEra(state.era.construction.eraId).index,
						name: getMarketEra(state.era.construction.eraId).name,
						startedAt: state.era.construction.startedAt,
						endsAt: state.era.construction.endsAt,
						skipCost: getMarketExpansionSkipCost(state.era.construction.endsAt - now),
					}
				: null,
		},
		// Shelves, sectors and fixtures under construction inside the market.
		// `pending`: bought, waiting in the build-mode inventory for a spot; `queued`: placed, waiting
		// for the works before it.
		builds: state.interiorConstructions.map((item) => {
			const duration = Math.max(0, item.durationMs ?? item.endsAt - item.startedAt);
			const queued = !item.pending && item.startedAt > now;
			return {
				id: item.id,
				kind: item.kind,
				targetId: item.targetId,
				name: getInteriorBuildName(item.kind, item.targetId),
				startedAt: item.startedAt,
				endsAt: item.endsAt,
				durationMs: duration,
				pending: !!item.pending,
				queued,
				skipCost: getInteriorSkipCost(item.pending || queued ? duration : item.endsAt - now),
			};
		}),
		ownedItems: state.shop.ownedItemIds,
		expansionStates: marketExpansions.map((expansion) => ({
			id: expansion.id,
			name: expansion.name,
			requiredLevel: expansion.requiredLevel,
			unlocked: state.unlockedMarketExpansionIds.includes(expansion.id),
			building: state.marketExpansionConstruction?.expansionId === expansion.id,
		})),
		// Works in progress: Unity shows the building site (cranes, scaffolding, countdown) around the
		// layout the market will have once this expansion opens.
		construction: state.marketExpansionConstruction
			? {
					expansionId: state.marketExpansionConstruction.expansionId,
					startedAt: state.marketExpansionConstruction.startedAt,
					endsAt: state.marketExpansionConstruction.endsAt,
					skipCost: getMarketExpansionSkipCost(
						state.marketExpansionConstruction.endsAt - Date.now(),
					),
					targetLayout: getSimulatorLayout([
						...state.unlockedMarketExpansionIds,
						state.marketExpansionConstruction.expansionId,
					]),
				}
			: null,
		interior: {
			items: (state.interior?.items ?? []).map((item) => ({
				id: item.id,
				type: item.type,
				x: item.x,
				z: item.z,
				rot: item.rot,
				stored: !!item.stored,
				outside: !!item.outside,
			})),
			owned: Object.entries(state.interior?.owned ?? {}).map(([type, count]) => ({ type, count })),
		},
		decorCatalog: interiorDecor.map((decor) => ({
			id: decor.id,
			name: decor.name,
			description: decor.description,
			coinPrice: decor.coinPrice ?? 0,
			diamondPrice: decor.diamondPrice ?? 0,
			requiredLevel: decor.requiredLevel,
			zone: decor.zone,
		})),
		// The register line: Unity keeps these customers waiting at the till until they are paid.
		checkouts: state.checkout.queue.map((checkout) => ({
			id: checkout.id,
			customerId: checkout.customerId,
			customerName: checkout.customerName,
			mood: checkout.mood,
			method: checkout.method,
			total: checkout.total,
			cashGiven: checkout.cashGiven,
			readyAt: checkout.readyAt,
			expiresAt: checkout.expiresAt,
			items: checkout.items.map((item) => ({
				productId: item.productId,
				name: item.name,
				quantity: item.quantity,
				unitPrice: item.unitPrice,
			})),
		})),
		dock: state.receiving.dock.map((delivery) => ({
			id: delivery.id,
			productId: delivery.productId,
			productName: delivery.productName,
			category: delivery.category,
			zone: delivery.zone,
			quantity: delivery.quantity,
			unloaded: delivery.unloaded,
			boxUnits: getBoxUnits(delivery.quantity),
			// Free space for this product in the stockroom (a full stockroom refuses the boxes).
			room: Math.max(
				0,
				getInventoryCapacity(
					{ id: delivery.productId },
					state.inventoryCapacityLevels[delivery.productId],
				) - (state.inventory[delivery.productId] ?? 0),
			),
			arrivedAt: delivery.arrivedAt,
		})),
		restockSlots: shelves.flatMap((shelf) => {
			const count = getShelfSlotCount(shelf.id, shelfSlotCounts);
			if (count <= 0) return [];
			const capacity = getShelfCapacity(state.shelfUpgradeLevels[shelf.id] ?? 0);
			return getShelfSlotIds(shelf.id, count).flatMap((slotId) => {
				const productId = state.shelfAssignments[slotId];
				const product = productId
					? itemCatalog.find((item) => item.id === productId)
					: undefined;
				if (!product) return [];
				return [
					{
						slotId,
						shelfId: shelf.id,
						shelfName: shelf.name ?? shelf.id,
						productId: product.id,
						productName: product.name,
						zone: getWarehouseZone(product.category),
						stock: state.shelfStock[slotId] ?? 0,
						capacity,
						reserve: state.inventory[product.id] ?? 0,
					},
				];
			});
		}),
		// Store mishaps, shown at their shelf; clicking one opens its small task in Unity.
		incidents: state.incidents.active.map((incident) => ({
			id: incident.id,
			kind: incident.kind,
			shelfId: incident.shelfId,
			shelfName: incident.shelfName,
			productId: incident.productId,
			productName: incident.productName,
			createdAt: incident.createdAt,
			fixCost: incident.fixCost,
			tagPrice: incident.tagPrice,
			price:
				getIncidentShelves(state).find((shelf) => shelf.shelfId === incident.shelfId)
					?.price ?? 0,
		})),
		// What the stock clerks and cleaners are doing (src/services/staff-work.ts). A restock trip goes
		// to the sector counter when the product is made by a sector on the floor.
		staffTasks: (state.employees.tasks ?? []).map((task) => {
			const employee = state.employees.employees.find((item) => item.id === task.employeeId);
			if (task.kind === "restock") {
				const recipe = productionRecipes.find((r) => r.outputProductId === task.productId);
				const sector = productionSectors.find((item) => item.id === recipe?.sectorId);
				const atSector =
					sector &&
					layout.sectorIds.includes(sector.id) &&
					state.builtSectorIds.includes(sector.id);
				return {
					id: task.id,
					employeeId: task.employeeId,
					role: employee?.role ?? "stock_clerk",
					kind: task.kind,
					startedAt: task.startedAt,
					endsAt: task.endsAt,
					shelfId: atSector ? `sector-${sector.id}` : task.shelfId,
					slotId: task.slotId,
					productId: task.productId,
					productName: task.productName,
					units: task.units,
					box: task.box,
					incidentId: "",
					incidentKind: "",
				};
			}
			return {
				id: task.id,
				employeeId: task.employeeId,
				role: employee?.role ?? "cleaner",
				kind: task.kind,
				startedAt: task.startedAt,
				endsAt: task.endsAt,
				shelfId: task.shelfId,
				slotId: "",
				productId: 0,
				productName: "",
				units: 0,
				box: "",
				incidentId: task.incidentId,
				incidentKind: task.incidentKind,
			};
		}),
		checkoutResults: state.checkout.recent.map((outcome) => ({
			id: outcome.id,
			customerId: outcome.customerId,
			status: outcome.status,
			mistake: outcome.mistake,
			charged: outcome.charged,
			tip: outcome.tip,
		})),
		day: {
			phase: state.day.phase,
			dayNumber: state.day.dayNumber,
			startedAt: state.day.startedAt ?? 0,
			endsAt: state.day.endsAt ?? 0,
			loyalty: state.day.loyalty,
			contractTitle: state.day.contract?.title ?? "Dia livre",
			contractLabel: dayProgress.label,
			contractProgress: dayProgress.ratio,
			contractCompleted: dayProgress.completed,
			grade: state.day.result?.grade ?? "",
			// Pending requests plus the ones answered in the last seconds, so Unity can react.
			requests: state.day.requests
				.filter(
					(request) =>
						request.status === "pending" ||
						now - (request.resolvedAt ?? 0) < 8_000,
				)
				.map((request) => ({
					id: request.id,
					customerId: request.customerId,
					customerName: request.customerName,
					kind: request.kind,
					message: request.message,
					productId: request.productId,
					productName: request.productName,
					createdAt: request.createdAt,
					expiresAt: request.expiresAt,
					status: request.status,
				})),
		},
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
