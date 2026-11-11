using System.Collections;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "eventsbancadairy" (QA copy of the save): the banca's refrigerated display is part of the stall model
 // (CheckoutStall.BuiltIn), so buying it must start the works right away instead of waiting in the build-mode
 // inventory, where nobody could ever place it (a tester's report, Lucas 09/11/2026).
 public sealed partial class CheckoutAutoTest {
  IEnumerator BancaDairy(string request){
   yield return GoToStage("banca");
   yield return Dev("setMarketLevel","[30]",()=>bridge.State.level>=30);
   yield return Dev("devAdjustCoins","[1000000]",()=>bridge.State.coins>=500000);
   string Shelves()=>string.Join(" ",bridge.State.shelves.Select(s=>s.id+(s.unlocked?"+":s.building?"~":"-")));
   string Builds()=>string.Join(" ",(bridge.State.builds??new BuildEntry[0]).Select(b=>JsonUtility.ToJson(b)));
   Note("DAIRY start: shelves "+Shelves()+" builds "+Builds());
   for(int i=0;i<4;i++){
    var dairy=bridge.State.shelves.FirstOrDefault(s=>s.id=="dairy");
    if(dairy==null){Note("DAIRY FAIL no dairy shelf in the snapshot");yield break;}
    if(dairy.unlocked||dairy.building)break;
    var next=bridge.State.shelves.FirstOrDefault(s=>!s.unlocked&&!s.building);
    yield return Dev("unlockNextShelf","[]",()=>bridge.State.shelves.Any(s=>s.id==next.id&&(s.building||s.unlocked)));
    if(next.id!="dairy"){
     // a shelf before it that does go to the inventory: placed where the build mode settles it, as a player would
     Note("DAIRY next shelf was "+next.id+" (not built in); builds "+Builds());
     yield return new WaitForSecondsRealtime(1.5f);
     var inside=CheckoutInterior.Active;var key="shelf:"+next.id;
     if(inside&&inside.waiting.ContainsKey(key)){
      var fl=inside.FloorRect;CheckoutInterior.Item it=null;
      for(float pz=fl.yMin+.6f;it==null&&pz<fl.yMax-.3f;pz+=.4f)
       for(float px=fl.xMin+.4f;it==null&&px<fl.xMax-.3f;px+=.4f)
        it=inside.PlaceWaiting(key,new Vector3(px,0,pz));
      Note("DAIRY placed "+key+": "+(it!=null?it.root.position.ToString("F2"):"no room"));
      inside.MarkPending();FindAnyObjectByType<CheckoutMap>().SaveInterior();yield return new WaitForSecondsRealtime(2.5f);
     }
     yield return Dev("devFinishInteriorConstructions","[]",()=>bridge.State.shelves.Any(s=>s.id==next.id&&s.unlocked));
     if(!bridge.State.shelves.Any(s=>s.id==next.id&&s.unlocked)){Note("DAIRY stopped: "+next.id+" waits in the inventory");yield break;}
    }
   }
   yield return new WaitForSecondsRealtime(1.5f);
   var entry=(bridge.State.builds??new BuildEntry[0]).FirstOrDefault(b=>JsonUtility.ToJson(b).Contains("\"dairy\""));
   string json=entry!=null?JsonUtility.ToJson(entry):"none";
   bool pending=json.Contains("\"pending\":true");
   Note("DAIRY after buying: "+json+" -> "+(entry!=null&&!pending?"PASS works started (not in the inventory)":entry==null?"(no build entry)":"FAIL still in the inventory"));
   Note("DAIRY build-mode inventory: ["+string.Join(",",CheckoutInterior.Active?CheckoutInterior.Active.waiting.Keys.ToArray():new string[0])+"]");
   Note("DAIRY stall built-in: "+CheckoutStall.BuiltIn("shelf:dairy")+" yard="+CheckoutStall.Yard);
   yield return Shot("dairy_banca_works");
   yield return Dev("devFinishInteriorConstructions","[]",()=>bridge.State.shelves.Any(s=>s.id=="dairy"&&s.unlocked));
   bool open=bridge.State.shelves.Any(s=>s.id=="dairy"&&s.unlocked);
   Note("DAIRY after the works: "+(open?"PASS the display is open":"FAIL not open")+"; shelves "+Shelves());
   yield return new WaitForSecondsRealtime(2f);
   yield return Shot("dairy_banca_done");
  }
 }
}
