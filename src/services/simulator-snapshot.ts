import type { GameState } from "@/@types/game";
import type { SimulatorSnapshot } from "@/@types/simulator";
import { itemCatalog, shelves } from "@/data/market-products";
import { productionSectors } from "@/data/production-sectors";
import { getShelfCapacity } from "@/data/shelf-capacity";
import { getGameEvent } from "@/data/game-events";
import { getActiveGameEventEffects } from "@/services/game-events";
export function createSimulatorSnapshot(state: GameState, session: string, revision: number, now=Date.now()): SimulatorSnapshot {
 const active=state.events.activeEvent && state.events.activeEvent.endsAt>now ? state.events.activeEvent : null;
 const event=getGameEvent(active?.eventId),effects=getActiveGameEventEffects(state.events,now);
 return {kind:"snapshot",protocol:1,session,revision,sentAt:now,coins:state.coins,diamonds:state.logistics.premiumCurrency,level:state.market.level,isOpen:state.market.isOpen,satisfaction:state.market.customerSatisfaction,served:state.market.customersServed,
 shelves:shelves.map((s,index)=>{const id=state.shelfAssignments[s.id]??0;const product=itemCatalog.find(p=>p.id===id);return {id:s.id,name:s.name??s.id,productId:id,productName:product?.name??"Prateleira vazia",category:product?.category??"",stock:state.shelfStock[s.id]??0,reserve:state.inventory[id]??0,price:state.shelfPrices[s.id]??product?.sellingPrice??0,capacity:getShelfCapacity(state.shelfUpgradeLevels[s.id]??0),unlocked:index<state.unlockedShelfSlots,expiresAt:Math.min(...(state.shelfLots[s.id]??[]).map(l=>l.expiresAt??Number.MAX_SAFE_INTEGER),Number.MAX_SAFE_INTEGER)};}),
 sectors:productionSectors.map(s=>({id:s.id,name:s.name,unlocked:state.market.level>=s.requiredLevel,jobs:state.production.jobs.filter(j=>j.sectorId===s.id).length})),
 employees:state.employees.employees,orders:state.logistics.orders,jobs:state.production.jobs,customers:state.market.recentCustomers,expansions:state.unlockedMarketExpansionIds,ownedItems:state.shop.ownedItemIds,
 event:{id:event?.id??"",name:event?.name??"",description:event?.description??"",effectLabel:event?.effectLabel??"",kind:event?.kind??"",endsAt:active?.endsAt??0,arrivalMultiplier:effects.customerArrivalMultiplier,productionMultiplier:effects.productionDurationMultiplier}};
}
