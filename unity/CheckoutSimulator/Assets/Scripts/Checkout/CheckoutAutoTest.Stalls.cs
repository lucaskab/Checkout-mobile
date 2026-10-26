using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // The first stages' stall models ("eventsstalls" or "eventsstalls-mesinha.tenda.banca.conteiner"; the word "events"
 // puts it on the QA copy of the save). Per stage: the model the game shows and its parts (CUT_* hidden, the glass
 // swapped for the see-through one), the footprint, the crate / register / queue / entrance points against the model,
 // whether a tap on the register reaches the stall's checkout, and shots from the player's camera, close up and with a
 // shopper at the stall (the market is opened): Logs/st_<stage>_{home,close,shopper}.jpg, STALL lines in the log.
 public sealed partial class CheckoutAutoTest {
  static readonly string[] StallModels={"Era0_Mesinha","Era1_Tenda","Era2_Banca","Era3_Conteiner","Era4_Spati","Era5_Quitanda","Era6_Minimercado"};
  IEnumerator Stalls(string request){
   var parts=request.Split('-');var stages=parts.Length>1?parts[1].Split('.'):new[]{"mesinha","tenda","banca","conteiner"};
   foreach(var f in Directory.GetFiles("Logs","st_*.jpg"))File.Delete(f);
   var fx=FindAnyObjectByType<CheckoutEventVisuals>();if(fx&&fx.Previewing)fx.Preview("");
   foreach(var stage in stages){
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
    yield return new WaitForSecondsRealtime(6);
    // open for customers: a finished day is claimed first, then a free day starts (or the market just opens)
    if(!bridge.State.isOpen){
     CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-claim\",\"action\":\"claimDayResult\",\"args\":[]}");yield return new WaitForSecondsRealtime(1);
     CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-day\",\"action\":\"startDay\",\"args\":[\"livre\"]}");for(float t=0;t<4&&!bridge.State.isOpen;t+=.5f)yield return new WaitForSecondsRealtime(.5f);
     if(!bridge.State.isOpen){CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-open\",\"action\":\"setMarketOpen\",\"args\":[true]}");for(float t=0;t<6&&!bridge.State.isOpen;t+=.5f)yield return new WaitForSecondsRealtime(.5f);}
     Note($"STALL {stage}: day phase {bridge.State.day?.phase} open={bridge.State.isOpen}");
    }
    var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();yield return new WaitForSecondsRealtime(1.5f);
    var fp=CheckoutStall.Footprint;
    Note($"STALL {stage}: era={bridge.State?.era?.id}/{bridge.State?.era?.index} open={bridge.State.isOpen} small={CheckoutStall.Small} yard={CheckoutStall.Yard} shop={CheckoutStall.ShopInside} footprint center={fp.center} size={fp.size}");
    GameObject model=null;foreach(var n in StallModels){var go=GameObject.Find(n);if(go){model=go;break;}}
    if(!model){Note($"STALL {stage}: NO MODEL SHOWN");continue;}
    var rs=model.GetComponentsInChildren<Renderer>(true);
    Note($"STALL {stage}: model {model.name} scale {model.transform.localScale.x:0.00} at {model.transform.position}; parts "+string.Join(", ",rs.Select(r=>$"{r.name}{(r.gameObject.activeInHierarchy?"":" (hidden)")}[{string.Join("/",r.sharedMaterials.Select(m=>m?m.name:"-"))}]")));
    var cut=rs.Where(r=>r.name.StartsWith("CUT_")&&r.gameObject.activeInHierarchy).Select(r=>r.name).ToList();
    var glass=rs.Where(r=>r.name.Contains("Glass")&&!r.sharedMaterials.All(m=>m&&m.name=="Era glass")).Select(r=>r.name).ToList();
    var tris=model.GetComponentsInChildren<MeshFilter>(false).Sum(m=>{var me=m.sharedMesh;if(!me)return 0;long n=0;for(int i=0;i<me.subMeshCount;i++)n+=me.GetIndexCount(i);return (int)(n/3);});
    Note($"STALL {stage}: visible triangles {tris}; CUT_ parts still shown: {cut.Count} {string.Join(",",cut)}; glass not swapped: {glass.Count} {string.Join(",",glass)}");
    // the points the customers use, against the model's visible bounds
    var vis=model.GetComponentsInChildren<Renderer>(false);var b=vis[0].bounds;foreach(var r in vis)b.Encapsulate(r.bounds);
    var ids=(bridge.State?.shelves??Array.Empty<Shelf>()).Where(s=>s.unlocked).Select(s=>s.id).ToList();
    var crates=ids.Select(id=>(id,CheckoutStall.Crate(id))).ToList();
    Note($"STALL {stage}: bounds {b.min:F2}..{b.max:F2}; crates "+string.Join(" ",crates.Select(c=>$"{c.id}@({c.Item2.x:0.00},{c.Item2.y:0.00},{c.Item2.z:0.00}){(InXZ(b,c.Item2)?"":" OUTSIDE")}")));
    var reg=CheckoutStall.Register;var map=FindAnyObjectByType<CheckoutMap>();
    Note($"STALL {stage}: register ({reg.x:0.00},{reg.y:0.00},{reg.z:0.00}){(InXZ(b,reg)?"":" OUTSIDE")}; entrance {(map?map.Entrance:Vector3.zero)}; queue "+string.Join(" ",Enumerable.Range(0,4).Select(i=>{var q=CheckoutStall.QueueSpot(i);return $"({q.x:0.00},{q.z:0.00}){(InXZ(b,q)?" INSIDE THE STALL":"")}";}))+"; approach "+string.Join(" ",ids.Take(5).Select(id=>{var a=CheckoutStall.Approach(id);return $"({a.x:0.00},{a.z:0.00}){(InXZ(b,a)?" INSIDE THE STALL":"")}";})));
    // a tap on the register: what the player's ray hits first
    var click=model.transform.Find("Stall checkout");var cam=Camera.main;
    if(cam){var sp=cam.WorldToScreenPoint(reg);var ray=cam.ScreenPointToRay(sp);var hits=Physics.RaycastAll(ray,500).OrderBy(h=>h.distance).ToList();
     var first=hits.FirstOrDefault();var target=first.collider?first.collider.GetComponentInParent<CheckoutTarget>():null;
     Note($"STALL {stage}: click box {(click?"present":"MISSING")}; tap on the register hits {(first.collider?first.collider.name:"nothing")} -> {(target?target.panel:"no target")}");}
    Capture($"st_{stage}_home");
    float size=Mathf.Max(fp.size.x,fp.size.z)*1.7f+1;CaptureAt(new Vector3(fp.center.x,.6f,fp.center.z-.4f),size,$"st_{stage}_close");
    // a shopper at the stall (picking from the crates or paying)
    var front=CheckoutStall.StallFront;bool shot=false;
    for(float t=0;t<45&&!shot;t+=.5f){
     foreach(var w in FindObjectsByType<CheckoutWalker>(FindObjectsSortMode.None)){
      var p=w.transform.position;var r=new Rect(front.xMin-.3f,front.yMin-.3f,front.width+.6f,front.height+.6f);
      if(ShopInsideNow()?CheckoutStall.InteriorFloor.Contains(new Vector2(p.x,p.z)):r.Contains(new Vector2(p.x,p.z))){yield return new WaitForSecondsRealtime(1f);CaptureAt(new Vector3(fp.center.x,.6f,fp.center.z-.6f),size,$"st_{stage}_shopper");Note($"STALL {stage}: shopper {w.name} at ({p.x:0.00},{p.z:0.00}) after {t:0}s");shot=true;break;}
     }
     if(!shot)yield return new WaitForSecondsRealtime(.5f);
    }
    if(!shot)Note($"STALL {stage}: no shopper reached the stall in 45 s (customers in the snapshot: {bridge.State.customers?.Length??0})");
   }
  }
  static bool ShopInsideNow()=>CheckoutStall.ShopInside;
  static bool InXZ(Bounds b,Vector3 p)=>p.x>=b.min.x-.05f&&p.x<=b.max.x+.05f&&p.z>=b.min.z-.05f&&p.z<=b.max.z+.05f;
 }
}
