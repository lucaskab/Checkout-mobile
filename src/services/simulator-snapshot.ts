import { getMarketEra, getNextMarketEra, marketEras } from "@/data/economy";
import { ERA_LOTS, LOT_GRID, MARKET_LOTS, PLAZA_LOTS } from "@/data/market-lots";
import type { GameState } from "@/@types/game";
import type {
	SimulatorDelivery,
	SimulatorDeliveryOrder,
	SimulatorSnapshot,
	SimulatorSupplierProduct,
} from "@/@types/simulator";
import {
	DELIVERY_UNLOCK_ERA_ID,
	getCourierProfile,
	getDeliverySlots,
	isActiveDeliveryOrder,
	isDeliveryUnlocked,
} from "@/services/delivery";
import { getGameEvent } from "@/data/game-events";
import { interiorDecor } from "@/data/interior-decor";
import {
	getMarketExpansionSkipCost,
	marketExpansions,
} from "@/data/market-expansions";
import { getInventoryBoxCapacity, getInventoryCapacity } from "@/data/inventory-capacity";
import { itemCatalog, itemCategories, shelves, starterShelfIds } from "@/data/market-products";
import { shelfProductSlots } from "@/data/shelf-slots";
import { getFixtureName } from "@/data/shelf-types";
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
import { getActiveGameEventEffects, getTurnEventKey } from "@/services/game-events";
import { getContractProgress } from "@/services/market-day";
import { getIncidentShelves } from "@/services/store-incidents-context";
import { getClaimableMissionCount } from "@/services/missions";
import { isMarketBuilding } from "@/services/market-era";
import { getLotClearCost, getLotClearDuration, getLotStatus } from "@/services/market-lots";
import { getExperienceToNextLevel } from "@/services/progression";
import { getActiveBoosts } from "@/services/shop-effects";
import { getBoxCount, getCaseSize } from "@/data/case-sizes";
import { getMaxBoxesPerOrder } from "@/data/supplier-capacity";
import { getFreeBoxPlaces, getStockroomRoom } from "@/services/stockroom";
import {
	getActiveSupplierOrders,
	getOrderBoxes,
	getOrderLines,
	getSupplierCost,
	getSupplierDurationMs,
	getSupplierIncoming,
	LOW_STOCK_SHARE,
} from "@/services/supplier-cart";
import { getDeliveryBoxUnits, getRemainingBoxes, getWarehouseZone } from "@/services/receiving";
import { getSimulatorLayout } from "@/services/simulator-layout";
import {
	findInteriorConstruction,
	getInteriorBuildName,
	getInteriorSkipCost,
} from "@/data/interior-construction";
/** The shop's catalog: unlocked products first, then the locked ones of this and the next expansion. */
function createSupplierCatalog(state: GameState, now: number): SimulatorSupplierProduct[] {
	const unlocked = new Set(state.market.unlockedProductIds);
	const nextEraId = getNextMarketEra(state.era.id)?.id;
	return itemCatalog
		.filter(
			(product) =>
				product.acquisition === "supplier" &&
				(unlocked.has(product.id) || product.unlockEra === state.era.id || product.unlockEra === nextEraId),
		)
		.sort(
			(a, b) =>
				Number(!unlocked.has(a.id)) - Number(!unlocked.has(b.id)) ||
				a.unlockLevel - b.unlockLevel ||
				a.id - b.id,
		)
		.map((product) => {
			const caseSize = getCaseSize(product);
			const level = state.inventoryCapacityLevels[product.id];
			const stockUnits = state.inventory[product.id] ?? 0;
			const incoming = getSupplierIncoming(state, product.id, now);
			const slots = Object.entries(state.shelfAssignments)
				.filter(([, productId]) => productId === product.id)
				.map(([slotId]) => slotId);
			const boxPrice = getSupplierCost(state, product.id, caseSize, now);
			return {
				productId: product.id,
				name: product.name,
				category: product.category,
				categoryLabel:
					itemCategories.find((category) => category.id === product.category)?.label ?? product.category,
				caseSize,
				boxPrice,
				unitCost: Math.round((boxPrice / caseSize) * 100) / 100,
				salePrice:
					slots.map((slotId) => state.shelfPrices[slotId]).find((price) => price !== undefined) ??
					product.sellingPrice,
				stockUnits,
				shelfUnits: slots.reduce((total, slotId) => total + (state.shelfStock[slotId] ?? 0), 0),
				capacityBoxes: getInventoryBoxCapacity(level),
				freeBoxes: getFreeBoxPlaces(product, stockUnits, level, incoming.units),
				incomingBoxes: incoming.boxes,
				low: stockUnits / Math.max(1, getInventoryCapacity(product, level)) < LOW_STOCK_SHARE,
				locked: !unlocked.has(product.id),
				unlockLevel: product.unlockLevel,
				deliverySeconds: Math.round(getSupplierDurationMs(state, product.supplierTime, now) / 1000),
			};
		});
}

/** The Delivery app: every order flattened for Unity (src/services/delivery.ts has the rules). */
function createDeliverySnapshot(state: GameState): SimulatorDelivery {
	const { delivery } = state;
	const orders = delivery.orders.map((order): SimulatorDeliveryOrder => {
		const courier = getCourierProfile(order.courier?.id);
		return {
			id: order.id,
			status: order.status,
			customerName: order.customer.name,
			neighborhood: order.customer.neighborhood,
			avatar: order.customer.avatar,
			note: order.note,
			items: order.items.map((item) => {
				const product = itemCatalog.find((entry) => entry.id === item.productId);
				return {
					productId: item.productId,
					productName: product?.name ?? "",
					category: product?.category ?? "",
					quantity: item.quantity,
					packed: order.packed?.find((line) => line.productId === item.productId)?.quantity ?? 0,
				};
			}),
			distanceKm: order.distanceKm,
			fee: order.fee,
			itemsValue: order.itemsValue,
			fillRatio: order.fillRatio ?? 0,
			quality: order.quality ?? 0,
			stars: order.stars ?? 0,
			tip: order.tip ?? 0,
			bonus: order.bonus ?? 0,
			paid: order.paid ?? 0,
			courier:
				order.courier && courier
					? {
							id: order.courier.id,
							name: courier.name,
							color: courier.color,
							phrases: courier.phrases,
						}
					: null,
			createdAt: order.createdAt,
			expiresAt: order.expiresAt,
			acceptedAt: order.acceptedAt ?? 0,
			packBy: order.packBy ?? 0,
			packedAt: order.packedAt ?? 0,
			arriveAt: order.courier?.arriveAt ?? 0,
			doorSince: order.courier?.doorSince ?? 0,
			deliverAt: order.courier?.deliverAt ?? 0,
		};
	});
	return {
		unlocked: isDeliveryUnlocked(state.era.id),
		unlockEraName: getMarketEra(DELIVERY_UNLOCK_ERA_ID).name,
		slots: getDeliverySlots(state.era.id),
		active: delivery.orders.filter(isActiveDeliveryOrder).length,
		rating: delivery.rating,
		streak: delivery.streak,
		bestStreak: delivery.bestStreak,
		delivered: delivery.delivered,
		orders,
	};
}

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
				// The styrofoam cooler on the sidewalk is the drinks fridge from the container on.
				name: getFixtureName(s.id, state.era.id),
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
			// One truck, one row per product on it (orders from before carts have one).
			boxes: getOrderBoxes(order),
			lines: getOrderLines(order).map((line) => ({
				productId: line.productId,
				productName:
					itemCatalog.find((product) => product.id === line.productId)?.name ??
					"Produto",
				boxes: line.boxes,
			})),
		})),
		supplierCatalog: createSupplierCatalog(state, now),
		supplierInfo: {
			slots: state.logistics.supplierOrderSlots,
			active: getActiveSupplierOrders(state, now).length,
			maxBoxes: getMaxBoxesPerOrder(state.logistics.supplierOrderSlots),
			freightCoupons: state.logistics.freightCoupons,
		},
		jobs: state.production.jobs,
		delivery: createDeliverySnapshot(state),
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
		// Stage of the market (0 mesinha … 10 rede) and its evolution obra, if any.
		era: {
			id: state.era.id,
			index: getMarketEra(state.era.id).index,
			name: getMarketEra(state.era.id).name,
			building: isMarketBuilding(state.era.id),
			// Lots of the block (see src/data/market-lots.ts): owned now, taken by the next era, square.
			grid: LOT_GRID,
			// Each lot with its land status: "venda" (for sale), "bloqueado" (not next to your land yet),
			// "comprado" (bought, still with its ruin), "limpando" (crew at work), "seu", "praca".
			lotRects: MARKET_LOTS.map((lot) => {
				const status = getLotStatus(state.lots, lot.id);
				const clearing = state.lots?.clearing?.lotId === lot.id ? state.lots.clearing : null;
				return {
					...lot,
					status,
					clearCost: getLotClearCost(lot),
					clearDurationMs: getLotClearDuration(lot),
					clearStartedAt: clearing?.startedAt ?? 0,
					clearEndsAt: clearing?.endsAt ?? 0,
					skipCost: clearing ? getMarketExpansionSkipCost(clearing.endsAt - now) : 0,
					// The market building (or the stall) stands on it now: no ruin, no sign.
					occupied: (ERA_LOTS[state.era.id] ?? []).includes(lot.id),
					// First expansion that needs it ("Supermercado"), for the lot's tap panel in the world.
					neededBy: marketEras.find((era) => (ERA_LOTS[era.id] ?? []).includes(lot.id))?.name ?? "",
				};
			}),
			lots: state.lots?.cleared ?? [],
			nextLots: (ERA_LOTS[(state.era.construction?.eraId ?? getNextMarketEra(state.era.id)?.id) ?? state.era.id] ?? []).filter(
				(id) => !(state.lots?.cleared ?? []).includes(id),
			),
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
				name: getInteriorBuildName(item.kind, item.targetId, state.era.id),
				startedAt: item.startedAt,
				endsAt: item.endsAt,
				durationMs: duration,
				pending: !!item.pending,
				queued,
				skipCost: getInteriorSkipCost(item.pending || queued ? duration : item.endsAt - now),
			};
		}),
		ownedItems: state.shop.ownedItemIds,
		...(() => {
			const running = getActiveBoosts(state.shop, now);
			return {
				boosts: running.map((boost) => boost.id),
				boostSeconds: running.map((boost) => Math.ceil(boost.remainingMs / 1000)),
			};
		})(),
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
			upgrade: Boolean(decor.effect),
		})),
		decorPlays: state.market.decorPlays ?? [],
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
			orderId: delivery.orderId ?? "",
			productId: delivery.productId,
			productName: delivery.productName,
			category: delivery.category,
			zone: delivery.zone,
			quantity: delivery.quantity,
			unloaded: delivery.unloaded,
			boxUnits: getDeliveryBoxUnits(delivery),
			boxes: getRemainingBoxes(delivery).length,
			// Free space for this product in the stockroom (a full stockroom refuses the boxes).
			room: (() => {
				const product = itemCatalog.find((item) => item.id === delivery.productId);
				if (!product) return 0;
				const units = state.inventory[delivery.productId] ?? 0;
				const level = state.inventoryCapacityLevels[delivery.productId];
				return delivery.caseSize
					? getStockroomRoom(product, units, level)
					: Math.max(0, getInventoryCapacity(product, level) - units);
			})(),
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
						shelfName: getFixtureName(shelf.id, state.era.id),
						productId: product.id,
						productName: product.name,
						zone: getWarehouseZone(product.category),
						stock: state.shelfStock[slotId] ?? 0,
						capacity,
						reserve: state.inventory[product.id] ?? 0,
						caseSize: product.caseSize,
					},
				];
			});
		}),
		// The stockroom racks: every product with stock, in its boxes.
		stockroom: itemCatalog.flatMap((product) => {
			const units = state.inventory[product.id] ?? 0;
			if (units <= 0) return [];
			const level = state.inventoryCapacityLevels[product.id];
			return [
				{
					productId: product.id,
					productName: product.name,
					category: product.category,
					zone: getWarehouseZone(product.category),
					units,
					caseSize: product.caseSize,
					boxes: getBoxCount(units, product.caseSize),
					capacityBoxes: getInventoryBoxCapacity(level),
				},
			];
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
			// "noite": night turn (Unity darkens the city).
			shift: state.day.shift ?? "dia",
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
			interaction: effects.interaction ?? "",
			stops: (active ? (state.events.inspection?.stops ?? []) : []).map((stop) => ({
				id: stop.id,
				status: stop.status,
				shelfId: stop.shelfId ?? "",
				incidentId: stop.incidentId ?? "",
				kind: stop.kind ?? "",
				at: stop.at,
				deadline: stop.deadline,
			})),
			seal:
				Boolean(state.events.sealTurnKey) &&
				state.day.phase === "open" &&
				state.events.sealTurnKey === getTurnEventKey(state.day),
			windowRequests: (active ? (state.events.windowSales?.requests ?? []) : []).map((request) => ({
				id: request.id,
				lane: request.lane,
				slot: request.slot,
				productId: request.productId,
				productName: itemCatalog.find((item) => item.id === request.productId)?.name ?? "",
				status: request.status,
				expiresAt: request.expiresAt,
				inStock:
					(state.inventory[request.productId] ?? 0) > 0 ||
					shelfProductSlots.some(
						(slot) =>
							state.shelfAssignments[slot.id] === request.productId && (state.shelfStock[slot.id] ?? 0) > 0,
					),
			})),
			windowServed: active ? (state.events.windowSales?.served ?? 0) : 0,
			windowGoal: active ? (state.events.windowSales?.goal ?? 0) : 0,
		},
	};
}
