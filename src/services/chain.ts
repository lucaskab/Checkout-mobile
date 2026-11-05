import type {
	ChainBranch,
	ChainBranchId,
	ChainContract,
	ChainContractLine,
	ChainEmblemId,
	ChainSnapshot,
	ChainState,
	FleetJob,
	FleetTruck,
	FleetTruckKind,
} from "@/@types/chain";
import type { ItemDefinition } from "@/@types/item";
import type { MarketEraId } from "@/@types/economy";
import {
	BRANCH_CARGO_UNITS,
	BRANCH_FAVORITE_SHARE,
	BRANCH_INCOME_PER_MIN,
	BRANCH_LEVEL_INCOME,
	BRANCH_PARTIAL_SUPPLY,
	BRANCH_PENDING_HOURS,
	BRANCH_SUPPLY_HOURS,
	BRANCH_TRIP_MS,
	BRANCH_UPGRADES,
	CHAIN_NAME_MAX,
	CHAIN_NAME_MIN,
	COLD_CATEGORIES,
	CONTRACT_DIAMOND_EVERY,
	CONTRACT_LIFETIME_MS,
	CONTRACT_OFFERS,
	CONTRACT_PREMIUM,
	CONTRACT_REFRESH_MS,
	CONTRACT_TRIP_MS,
	FLEET_SPEED_FACTORS,
	FLEET_SPEED_PRICES,
	FLEET_START,
	FLEET_TRUCK_PRICES,
	chainBranches,
	chainClients,
	chainEmblems,
} from "@/data/chain";
import { marketEras } from "@/data/economy";

// Rede de supermercados: the brand, the fleet of the distribution centre, the city contracts and the branches.
// Pure functions over ChainState; the store (src/stores/game-store.ts) calls them and keeps the coins.

const MIN = 60_000;
const HOUR = 3_600_000;
const branchIds = chainBranches.map((branch) => branch.id);

export function isChainUnlocked(eraId: MarketEraId | undefined) {
	const index = marketEras.findIndex((era) => era.id === eraId);
	const rede = marketEras.findIndex((era) => era.id === "rede");
	return index >= 0 && rede >= 0 && index >= rede;
}

function newBranch(id: ChainBranchId): ChainBranch {
	return { id, level: 0, works: null, supply: 0, supplyAt: 0, pending: 0, cargo: null, earned: 0 };
}

function newTruck(kind: FleetTruckKind, index: number): FleetTruck {
	return { id: `truck-${index + 1}`, kind, job: null, trips: 0 };
}

export function createChainState(): ChainState {
	return {
		brand: { name: "", emblem: "cesta", namedAt: null, renames: 0 },
		fleet: { trucks: FLEET_START.map(newTruck), speedLevel: 0 },
		autoOrder: { enabled: false, lastAt: 0 },
		contracts: { offers: [], refreshAt: 0, completed: 0, earned: 0, serial: 0 },
		branches: Object.fromEntries(branchIds.map((id) => [id, newBranch(id)])) as Record<ChainBranchId, ChainBranch>,
	};
}

const num = (value: unknown, fallback = 0) => (typeof value === "number" && Number.isFinite(value) ? value : fallback);

/** Any save (older, partial or hand-edited) becomes a valid chain state; nothing the player had is dropped. */
export function normalizeChainState(raw: unknown): ChainState {
	const base = createChainState();
	if (!raw || typeof raw !== "object") return base;
	const value = raw as Partial<ChainState>;
	const brand = value.brand ?? base.brand;
	const trucks = Array.isArray(value.fleet?.trucks)
		? value.fleet.trucks
				.filter((truck): truck is FleetTruck => !!truck && (truck.kind === "seco" || truck.kind === "refrigerado"))
				.map((truck, index) => ({
					id: typeof truck.id === "string" ? truck.id : `truck-${index + 1}`,
					kind: truck.kind,
					job: truck.job && typeof truck.job === "object" ? truck.job : null,
					trips: num(truck.trips),
				}))
		: base.fleet.trucks;
	const branches = { ...base.branches };
	for (const id of branchIds) {
		const b = value.branches?.[id];
		if (b && typeof b === "object")
			branches[id] = {
				...newBranch(id),
				...b,
				id,
				level: Math.max(0, Math.min(3, Math.floor(num(b.level)))),
				supply: Math.max(0, Math.min(1, num(b.supply))),
				pending: Math.max(0, num(b.pending)),
				earned: Math.max(0, num(b.earned)),
			};
	}
	return {
		brand: {
			name: typeof brand.name === "string" ? brand.name.slice(0, CHAIN_NAME_MAX) : "",
			emblem: chainEmblems.includes(brand.emblem as ChainEmblemId) ? (brand.emblem as ChainEmblemId) : "cesta",
			namedAt: typeof brand.namedAt === "number" ? brand.namedAt : null,
			renames: num(brand.renames),
		},
		fleet: {
			trucks: trucks.length ? trucks : base.fleet.trucks,
			speedLevel: Math.max(0, Math.min(FLEET_SPEED_PRICES.length, Math.floor(num(value.fleet?.speedLevel)))),
		},
		autoOrder: { enabled: value.autoOrder?.enabled === true, lastAt: num(value.autoOrder?.lastAt) },
		contracts: {
			offers: Array.isArray(value.contracts?.offers) ? value.contracts.offers : [],
			refreshAt: num(value.contracts?.refreshAt),
			completed: num(value.contracts?.completed),
			earned: num(value.contracts?.earned),
			serial: num(value.contracts?.serial),
		},
		branches,
	};
}

// ------------------------------------------------------------------------------------------------ brand
/** The name as it will be kept, or why it cannot be used. */
export function checkChainName(input: unknown): { ok: true; name: string } | { ok: false; reason: string } {
	const name = typeof input === "string" ? input.replace(/\s+/g, " ").trim() : "";
	if (name.length < CHAIN_NAME_MIN) return { ok: false, reason: `O nome precisa de pelo menos ${CHAIN_NAME_MIN} letras.` };
	if (name.length > CHAIN_NAME_MAX) return { ok: false, reason: `O nome pode ter no máximo ${CHAIN_NAME_MAX} letras.` };
	if (!/^[\p{L}\p{N}][\p{L}\p{N} '&.\-!]*$/u.test(name)) return { ok: false, reason: "Use só letras, números e espaços." };
	return { ok: true, name };
}

export function isChainEmblem(value: unknown): value is ChainEmblemId {
	return chainEmblems.includes(value as ChainEmblemId);
}

// ------------------------------------------------------------------------------------------------ fleet
export function getTripFactor(chain: ChainState) {
	return FLEET_SPEED_FACTORS[Math.min(chain.fleet.speedLevel, FLEET_SPEED_FACTORS.length - 1)];
}

export function isTruckFree(truck: FleetTruck, now: number) {
	return !truck.job || now >= truck.job.returnAt;
}

/** Trucks back at the centre lose their finished job (and count the trip). */
export function releaseTrucks(chain: ChainState, now: number): ChainState {
	let changed = false;
	const trucks = chain.fleet.trucks.map((truck) => {
		if (truck.job && now >= truck.job.returnAt) {
			changed = true;
			return { ...truck, job: null, trips: truck.trips + 1 };
		}
		return truck;
	});
	return changed ? { ...chain, fleet: { ...chain.fleet, trucks } } : chain;
}

/** A free truck for a trip: a refrigerated one when the load is cold, otherwise a dry one first. */
export function pickTruck(chain: ChainState, cold: boolean, now: number): FleetTruck | null {
	const free = chain.fleet.trucks.filter((truck) => isTruckFree(truck, now));
	if (cold) return free.find((truck) => truck.kind === "refrigerado") ?? null;
	return free.find((truck) => truck.kind === "seco") ?? free.find((truck) => truck.kind === "refrigerado") ?? null;
}

export function withTruckJob(chain: ChainState, truckId: string, job: FleetJob): ChainState {
	return {
		...chain,
		fleet: {
			...chain.fleet,
			trucks: chain.fleet.trucks.map((truck) => (truck.id === truckId ? { ...truck, job } : truck)),
		},
	};
}

export function getNextTruckPrice(chain: ChainState, kind: FleetTruckKind): number | null {
	const start = FLEET_START.filter((k) => k === kind).length;
	const owned = chain.fleet.trucks.filter((truck) => truck.kind === kind).length;
	return FLEET_TRUCK_PRICES[kind][owned - start] ?? null;
}

export function getNextSpeedPrice(chain: ChainState): number | null {
	return FLEET_SPEED_PRICES[chain.fleet.speedLevel] ?? null;
}

export function addTruck(chain: ChainState, kind: FleetTruckKind): ChainState {
	const next = chain.fleet.trucks.reduce((most, truck) => Math.max(most, Number(truck.id.replace(/\D/g, "")) || 0), 0);
	return {
		...chain,
		fleet: { ...chain.fleet, trucks: [...chain.fleet.trucks, { id: `truck-${next + 1}`, kind, job: null, trips: 0 }] },
	};
}

export function isColdCategory(category: string) {
	return COLD_CATEGORIES.includes(category);
}

// ------------------------------------------------------------------------------------------------ contracts
/** Small deterministic dice (the offers of a save do not change when the game reloads). */
function dice(seed: number) {
	let s = (seed * 2654435761) >>> 0 || 1;
	return () => {
		s ^= s << 13;
		s >>>= 0;
		s ^= s >>> 17;
		s ^= s << 5;
		s >>>= 0;
		return s / 4294967296;
	};
}

type OfferContext = {
	catalog: ItemDefinition[];
	unlockedProductIds: number[];
	eraIndex: number;
	now: number;
};

/** One new offer from a client, with 2-3 products the player can sell (by the client's categories first). */
export function createContractOffer(serial: number, ctx: OfferContext): ChainContract | null {
	const roll = dice(serial + 1);
	const client = chainClients[Math.floor(roll() * chainClients.length)];
	const sellable = ctx.catalog.filter((item) => ctx.unlockedProductIds.includes(item.id));
	if (sellable.length === 0) return null;
	const preferred = sellable.filter((item) => client.categories.includes(item.category));
	const pool = preferred.length >= 2 ? preferred : sellable;
	const count = Math.min(pool.length, 2 + (roll() < 0.4 ? 1 : 0));
	const chosen: ItemDefinition[] = [];
	const left = [...pool];
	while (chosen.length < count && left.length) chosen.push(left.splice(Math.floor(roll() * left.length), 1)[0]);
	const scale = 1 + Math.max(0, ctx.eraIndex - 9) * 0.25;
	const lines: ChainContractLine[] = chosen.map((item) => ({
		productId: item.id,
		// fewer of the expensive things, more of the everyday ones
		units: Math.max(8, Math.round(((40 + roll() * 60) * scale * 20) / Math.max(20, item.sellingPrice) / 2) * 2),
	}));
	const value = lines.reduce((sum, line) => {
		const item = chosen.find((product) => product.id === line.productId);
		return sum + (item?.sellingPrice ?? 0) * line.units;
	}, 0);
	const tripMs = Math.round(CONTRACT_TRIP_MS[0] + roll() * (CONTRACT_TRIP_MS[1] - CONTRACT_TRIP_MS[0]));
	return {
		id: `contract-${serial}`,
		client: client.id,
		lines,
		cold: chosen.some((item) => isColdCategory(item.category)),
		reward: Math.max(100, Math.round((value * CONTRACT_PREMIUM) / 50) * 50),
		xp: lines.reduce((sum, line) => sum + line.units, 0),
		diamonds: serial % CONTRACT_DIAMOND_EVERY === CONTRACT_DIAMOND_EVERY - 1 ? 5 : 0,
		tripMs,
		expiresAt: ctx.now + CONTRACT_LIFETIME_MS,
		acceptedAt: null,
		truckId: null,
	};
}

/** Expired offers leave; at the refresh time the board is filled up to CONTRACT_OFFERS again. */
export function refreshContracts(chain: ChainState, ctx: OfferContext): ChainState {
	const { now } = ctx;
	const contracts = chain.contracts;
	const offers = contracts.offers.filter((offer) => offer.acceptedAt !== null || offer.expiresAt > now);
	let serial = contracts.serial;
	let refreshAt = contracts.refreshAt;
	const waiting = offers.filter((offer) => offer.acceptedAt === null).length;
	if (now >= refreshAt || waiting === 0) {
		const fresh: ChainContract[] = [];
		for (let k = waiting; k < CONTRACT_OFFERS; k++) {
			const offer = createContractOffer(serial, ctx);
			serial++;
			if (offer) fresh.push(offer);
		}
		refreshAt = now + CONTRACT_REFRESH_MS;
		if (fresh.length || offers.length !== contracts.offers.length)
			return { ...chain, contracts: { ...contracts, offers: [...offers, ...fresh], serial, refreshAt } };
		return { ...chain, contracts: { ...contracts, refreshAt } };
	}
	if (offers.length !== contracts.offers.length) return { ...chain, contracts: { ...contracts, offers } };
	return chain;
}

/** What is missing in the stockroom for a contract (empty when it can go). */
export function getContractShortfall(contract: ChainContract, inventory: Record<number, number>) {
	return contract.lines
		.map((line) => ({ productId: line.productId, missing: Math.max(0, line.units - (inventory[line.productId] ?? 0)) }))
		.filter((line) => line.missing > 0);
}

// ------------------------------------------------------------------------------------------------ branches
export function getBranchDefinition(id: ChainBranchId) {
	return chainBranches.find((branch) => branch.id === id) ?? chainBranches[0];
}

export function getBranchIncomePerMin(id: ChainBranchId, level: number) {
	return BRANCH_INCOME_PER_MIN * (BRANCH_LEVEL_INCOME[level] ?? 0) * getBranchDefinition(id).income;
}

/** Price and works time of the next step of a branch (buy = level 1, then levels 2 and 3), or null at the top. */
export function getBranchNextStep(branch: ChainBranch): { level: number; price: number; buildMs: number } | null {
	const def = getBranchDefinition(branch.id);
	if (branch.works) return null;
	if (branch.level === 0) return { level: 1, price: def.price, buildMs: def.buildMs };
	const up = BRANCH_UPGRADES[branch.level - 1];
	if (!up) return null;
	return { level: branch.level + 1, price: Math.round((def.price * up.priceShare) / 1000) * 1000, buildMs: up.buildMs };
}

/** Coins a branch earns between `from` and `to` while its shelves fall from `supply` (and the shelves after). */
function accrue(id: ChainBranchId, level: number, supply: number, from: number, to: number) {
	const minutes = Math.max(0, (to - from) / MIN);
	const perMin = getBranchIncomePerMin(id, level);
	const rate = 1 / (BRANCH_SUPPLY_HOURS * 60);
	if (minutes <= 0 || level <= 0) return { coins: 0, supply };
	const end = supply - rate * minutes;
	const area = end >= 0 ? (supply + end) / 2 * minutes : (supply * (supply / rate)) / 2;
	return { coins: perMin * area, supply: Math.max(0, end) };
}

/** Brings one branch up to `now`: income, shelves going down, the works ending and a cargo arriving. */
export function updateBranch(branch: ChainBranch, now: number): ChainBranch {
	let b = { ...branch };
	const steps: { at: number; apply: () => void }[] = [];
	if (b.works && now >= b.works.endsAt) {
		const works = b.works;
		steps.push({
			at: works.endsAt,
			apply: () => {
				const opening = b.level === 0;
				b.level = works.level;
				b.works = null;
				// a new store opens with full shelves
				if (opening) b.supply = 1;
			},
		});
	}
	if (b.cargo && now >= b.cargo.arriveAt) {
		const cargo = b.cargo;
		steps.push({
			at: cargo.arriveAt,
			apply: () => {
				b.supply = Math.max(b.supply, cargo.supply);
				b.cargo = null;
			},
		});
	}
	steps.sort((x, y) => x.at - y.at);
	const cap = (level: number) => getBranchIncomePerMin(b.id, level) * 60 * BRANCH_PENDING_HOURS;
	let at = Math.max(b.supplyAt, 0) || now;
	for (const step of [...steps, { at: now, apply: () => {} }]) {
		const t = Math.max(at, Math.min(step.at, now));
		const got = accrue(b.id, b.level, b.supply, at, t);
		b.pending = Math.min(cap(b.level), b.pending + got.coins);
		b.supply = got.supply;
		at = t;
		step.apply();
	}
	b.supplyAt = now;
	return b;
}

export function updateBranches(chain: ChainState, now: number): ChainState {
	const branches = { ...chain.branches };
	for (const id of branchIds) branches[id] = updateBranch(branches[id], now);
	return { ...chain, branches };
}

/**
 * Units a cargo for `branchId` takes from the stockroom: favourites first (fullest first), then the rest, never
 * more than half of what the stockroom holds of a product. `favoriteShare` decides how full the shelves get.
 */
export function chooseBranchCargo(
	branchId: ChainBranchId,
	level: number,
	inventory: Record<number, number>,
	catalog: ItemDefinition[],
	unlockedProductIds: number[],
) {
	const def = getBranchDefinition(branchId);
	const want = BRANCH_CARGO_UNITS * Math.max(1, level);
	const stocked = catalog
		.filter((item) => unlockedProductIds.includes(item.id) && (inventory[item.id] ?? 0) >= 2)
		.map((item) => ({ item, take: Math.floor((inventory[item.id] ?? 0) / 2), fav: def.favorites.includes(item.category) }))
		.sort((a, b) => Number(b.fav) - Number(a.fav) || b.take - a.take);
	const lines: { productId: number; units: number; favorite: boolean }[] = [];
	let total = 0;
	for (const { item, take, fav } of stocked) {
		if (total >= want) break;
		const units = Math.min(take, want - total);
		if (units <= 0) continue;
		lines.push({ productId: item.id, units, favorite: fav });
		total += units;
	}
	const favorites = lines.filter((line) => line.favorite).reduce((sum, line) => sum + line.units, 0);
	const favoriteShare = total > 0 ? favorites / total : 0;
	const cold = lines.some((line) => isColdCategory(catalog.find((item) => item.id === line.productId)?.category ?? ""));
	return {
		lines,
		total,
		want,
		favoriteShare,
		cold,
		supply: favoriteShare >= BRANCH_FAVORITE_SHARE ? 1 : BRANCH_PARTIAL_SUPPLY,
		enough: total >= want / 2,
	};
}

export function getBranchTripMs(chain: ChainState) {
	return Math.round(BRANCH_TRIP_MS * getTripFactor(chain));
}

// ------------------------------------------------------------------------------------------------ snapshot
export function createChainSnapshot(chain: ChainState, eraId: MarketEraId | undefined, now: number): ChainSnapshot {
	const unlocked = isChainUnlocked(eraId);
	return {
		unlocked,
		named: chain.brand.namedAt !== null,
		name: chain.brand.name,
		emblem: chain.brand.emblem,
		trucks: unlocked
			? chain.fleet.trucks.map((truck) => {
					const job = truck.job && now < truck.job.returnAt ? truck.job : null;
					return {
						id: truck.id,
						kind: truck.kind,
						job: job?.kind ?? null,
						phase: !job ? "patio" : now < job.arriveAt ? "indo" : "voltando",
						departAt: job?.departAt ?? 0,
						arriveAt: job?.arriveAt ?? 0,
						returnAt: job?.returnAt ?? 0,
					};
				})
			: [],
		branches: chainBranches.map((def) => ({
			id: def.id,
			level: chain.branches[def.id]?.level ?? 0,
			building: !!chain.branches[def.id]?.works,
		})),
	};
}

export { HOUR as CHAIN_HOUR };
