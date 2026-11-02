using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // QA helper for social v1 ("eventssocialcapture"): turns the QA copy of the save (never the player's save) into a
 // furnished Späti, the way a player would have it: every piece placed on the shop floor by the game itself (free spot
 // nearest the middle), a shelf under construction placed, decorations inside and on the block. The layout is written
 // to Logs/social_capture_spati.json; desktop/social-mock.ts uses it for the friend "Mercado da Ana", so a visit shows a
 // real Späti with its fixtures, a works site and an evolution ring.
 public sealed partial class CheckoutAutoTest {
  IEnumerator SocialCapture(string request){
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-capture-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   Note("capture: "+CheckoutQaGameView.Set(2778,1284));
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1f);
   Act("setMarketLevel","[9]");Act("devAdjustCoins","[300000]");yield return new WaitForSecondsRealtime(1f);
   Act("devSetMarketEra","[\"spati\"]");yield return new WaitForSecondsRealtime(8f);
   var ia=CheckoutInterior.Active;var map=FindAnyObjectByType<CheckoutMap>();
   if(!ia||!map){Note("capture: no interior");yield break;}
   Note($"capture: era {bridge.State.era?.id} small {CheckoutStall.Small} inside {CheckoutStall.ShopInside} floor {ia.FloorRect} waiting [{string.Join(",",ia.waiting.Keys)}] pieces [{string.Join(",",ia.items.Keys)}]");
   var floor=ia.FloorRect;var middle=new Vector3(floor.center.x,CheckoutStall.FloorY,floor.center.y);
   void PlaceAll(){foreach(var id in ia.waiting.Keys.ToList())Note("capture: place "+id+" -> "+(ia.PlaceWaiting(id,middle)!=null));}
   PlaceAll();map.SaveInterior();yield return new WaitForSecondsRealtime(2f);
   // the next shelf, bought and placed: its builders start (a works site in the shop)
   Act("unlockNextShelf","[]");yield return new WaitForSecondsRealtime(2.5f);
   PlaceAll();map.SaveInterior();yield return new WaitForSecondsRealtime(2.5f);
   // decorations: inside the shop and on the block in front of it
   string[] inside={"plant-small","monstera","fruit-pyramid"},outside={"flower-bed","park-bench","tree-planter","street-lamp","bike-rack"};
   foreach(var d in inside.Concat(outside))Act("purchaseDecor","[\""+d+"\",\"coins\"]");
   yield return new WaitForSecondsRealtime(2.5f);
   foreach(var d in inside)Note("capture: decor "+d+" -> "+(ia.AddDecor(d,middle,false)?.id??"no room"));
   var door=ia.EntrancePoint;var front=new Vector3(door.x,CheckoutInterior.Ground,door.z-2.2f);
   foreach(var d in outside)Note("capture: decor "+d+" -> "+(ia.AddDecor(d,front,true)?.id??"no room"));
   map.SaveInterior();yield return new WaitForSecondsRealtime(3f);
   var json=ia.ExportJson();File.WriteAllText("Logs/social_capture_spati.json",json);
   Note("CAPTURE spati "+json);
   Note($"capture: builds [{string.Join(",",(bridge.State.builds??new BuildEntry[0]).Select(b=>b.kind+":"+b.targetId+":"+b.id))}]");
   var sim=FindAnyObjectByType<MarketDay.MarketSimulation>();if(sim)sim.Focus(new Vector3(floor.center.x,0,floor.center.y-1.5f),8f);
   yield return new WaitForSecondsRealtime(2f);yield return Shot("social_capture_spati");

   // The same for a supermercado (the friend "Supermercado da Gabi", far ahead): the stage's own shelves on its floor,
   // as the game lays them out, and the next shelf bought and placed (its works site). Logs/social_capture_supermercado.json.
   Act("setMarketLevel","[30]");Act("devAdjustCoins","[3000000]");yield return new WaitForSecondsRealtime(1f);
   Act("devSetMarketEra","[\"supermercado\"]");yield return new WaitForSecondsRealtime(10f);
   ia=CheckoutInterior.Active;map=FindAnyObjectByType<CheckoutMap>();
   if(!ia||!map){Note("capture: no supermercado interior");yield break;}
   floor=ia.FloorRect;middle=new Vector3(floor.center.x,CheckoutStall.FloorY,floor.center.y);
   Note($"capture: era {bridge.State.era?.id} small {CheckoutStall.Small} floor {ia.FloorRect} waiting [{string.Join(",",ia.waiting.Keys)}] pieces [{string.Join(",",ia.items.Keys)}]");
   PlaceAll();map.SaveInterior();yield return new WaitForSecondsRealtime(2f);
   Act("unlockNextShelf","[]");yield return new WaitForSecondsRealtime(2.5f);
   PlaceAll();map.SaveInterior();yield return new WaitForSecondsRealtime(3f);
   var market=ia.ExportJson();File.WriteAllText("Logs/social_capture_supermercado.json",market);
   Note("CAPTURE supermercado "+market);
   Note($"capture: builds [{string.Join(",",(bridge.State.builds??new BuildEntry[0]).Select(b=>b.kind+":"+b.targetId+":"+b.id))}]");
   if(sim)sim.Focus(new Vector3(floor.center.x,0,floor.center.y-1.5f),12f);
   yield return new WaitForSecondsRealtime(2f);yield return Shot("social_capture_supermercado");
  }
 }
}
