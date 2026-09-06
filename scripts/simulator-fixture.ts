// Isolated QA fixture: never opens the application MMKV store.
import { mock } from "bun:test";
import { writeFileSync } from "node:fs";
(globalThis as unknown as {__DEV__: boolean}).__DEV__=true;
mock.module("@/storage/mmkv",()=>({mmkvStorage:{getItem:()=>null,setItem:()=>{},removeItem:()=>{}}}));
const {useGameStore}=await import("../src/stores/game-store");
const {createSimulatorSnapshot}=await import("../src/services/simulator-snapshot");
const game=useGameStore.getState();game.setMarketLevel(16);game.devAdjustCoins(100000);game.setMarketOpen(true);game.devActivateGameEvent("chuva-forte");game.hireEmployee("stock_clerk");game.hireEmployee("cleaner");game.unlockMarketExpansion("fresh-wing");game.placeSupplierOrder({productId:1,quantity:2});
for(let i=0;i<3;i++){useGameStore.setState({market:{...useGameStore.getState().market,nextCustomerAt:Date.now()-1}});useGameStore.getState().processNextCustomer();}
const snapshot=createSimulatorSnapshot(useGameStore.getState(),"desktop-integration-qa",1);
writeFileSync(process.argv[2]??"simulator-fixture.json",JSON.stringify(snapshot,null,2));
console.log(JSON.stringify({coins:snapshot.coins,shelves:snapshot.shelves.length,event:snapshot.event.id,customers:snapshot.customers.length}));
