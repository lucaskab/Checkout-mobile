using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Checkout {
 // Dev-only play-mode check of the mini-games. Runs only when Logs/autotest.txt exists (the editor
 // tool runner writes it): it feeds a test delivery / low shelves / broken coolers into the local
 // snapshot, plays each mini-game with simulated drags and taps (the same pointer events a finger
 // sends), saves screenshots to Logs/at_*.png and a step log with any exception to
 // Logs/autotest_log.txt, then asks the editor to leave play mode.
 public sealed class CheckoutAutoTest:MonoBehaviour {
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Boot(){if(Application.isEditor&&File.Exists("Logs/autotest.txt"))new GameObject("CheckoutAutoTest").AddComponent<CheckoutAutoTest>();}

  readonly List<string> log=new List<string>();CheckoutBridge bridge;
  DockEntry fakeDock;RestockSlot[] fakeSlots;IncidentEntry fakeIncident;

  void Awake(){DontDestroyOnLoad(gameObject);Application.logMessageReceived+=OnLog;CheckoutBridge.TestPatch=Patch;}
  void OnDestroy(){Application.logMessageReceived-=OnLog;CheckoutBridge.TestPatch=null;}
  void OnLog(string message,string stack,LogType type){if(type==LogType.Exception||type==LogType.Error)log.Add($"[{type}] {message}\n{stack}");else if(message.StartsWith("CHECKOUT_RECEIPT")||message.StartsWith("CHECKOUT_PORTRAIT"))log.Add(message);}
  void Note(string s){log.Add($"{Time.realtimeSinceStartup:0.0}s {s}");Flush();}
  void Flush(){try{File.WriteAllLines("Logs/autotest_log.txt",log);}catch{}}

  IEnumerator Start(){
   var scenarios=File.ReadAllText("Logs/autotest.txt").Split(new[]{',',' '},StringSplitOptions.RemoveEmptyEntries);File.Delete("Logs/autotest.txt");
   foreach(var f in Directory.GetFiles("Logs","at_*.png"))File.Delete(f);
   Note("scenarios: "+string.Join(",",scenarios));
   for(float t=0;t<90&&(bridge==null||bridge.State==null||bridge.State.shelves==null);t+=.5f){bridge=FindAnyObjectByType<CheckoutBridge>();yield return new WaitForSecondsRealtime(.5f);}
   if(scenarios.All(x=>x=="lamps")){foreach(var x in scenarios){Note("== "+x);yield return Lamps();}Finish();yield break;}// visual check, no host needed
   if(bridge==null||bridge.State==null){Note("no snapshot from the host");Finish();yield break;}
   Note($"snapshot ok: coins={bridge.State.coins} shelves={bridge.State.shelves.Length} dock={(bridge.State.dock?.Length??-1)} slots={(bridge.State.restockSlots?.Length??-1)}");
   yield return new WaitForSecondsRealtime(3);
   foreach(var s in scenarios){
    Note("== "+s);
    IEnumerator run=s=="dock"?Dock():s=="restock"?Restock():s=="freezer"?Wires("freezer_sorvete"):s=="geladeira"?Wires("geladeira_bebidas"):null;
    if(run==null){Note("unknown scenario");continue;}
    yield return run;
    CloseAll();fakeDock=null;fakeSlots=null;fakeIncident=null;yield return new WaitForSecondsRealtime(1);
   }
   Finish();
  }
  void Finish(){Note("done");Flush();File.WriteAllText("Logs/autotest_done.txt","ok");}

  // Keeps the test data in the snapshot (the host replaces it on every update).
  void LateUpdate(){Patch(bridge?.State);}
  void Patch(Snapshot s){
   if(s==null)return;
   if(fakeDock!=null&&(s.dock==null||s.dock.All(d=>d.id!=fakeDock.id)))s.dock=(s.dock??Array.Empty<DockEntry>()).Append(fakeDock).ToArray();
   if(fakeSlots!=null&&(s.restockSlots==null||s.restockSlots.All(d=>d.slotId!=fakeSlots[0].slotId)))s.restockSlots=(s.restockSlots??Array.Empty<RestockSlot>()).Concat(fakeSlots).ToArray();
   if(fakeIncident!=null&&(s.incidents==null||s.incidents.All(d=>d.id!=fakeIncident.id))){s.incidents=(s.incidents??Array.Empty<IncidentEntry>()).Append(fakeIncident).ToArray();if(s.coins<fakeIncident.fixCost+1)s.coins=fakeIncident.fixCost+100;}
  }

  // ------------------------------------------------------------------ helpers
  static void CloseAll(){
   foreach(var name in new[]{"CheckoutStockroom","CheckoutIncidentGame","CheckoutCounterGame"}){var c=GameObject.Find(name);if(!c)continue;var dim=c.transform.Find("Dim");if(dim&&dim.gameObject.activeSelf)dim.gameObject.SetActive(false);}
  }
  // Street lamps: night turn and heavy rain, every lamp head with its warm pool.
  IEnumerator Lamps(){var fx=FindAnyObjectByType<CheckoutEventVisuals>();if(!fx){Note("no CheckoutEventVisuals");yield break;}
   var pools=fx.GetComponent<CheckoutStreetLightPools>();Note("lamp pools: "+(pools?pools.Count:-1));
   fx.SetNight(true);yield return new WaitForSecondsRealtime(2.5f);yield return Shot("lamps_night");
   fx.SetNight(false);fx.Preview("chuva-forte");yield return new WaitForSecondsRealtime(2.5f);yield return Shot("lamps_rain");
   fx.Preview("");yield return new WaitForSecondsRealtime(2f);yield return Shot("lamps_day");}
  IEnumerator Shot(string name){yield return new WaitForEndOfFrame();ScreenCapture.CaptureScreenshot("Logs/at_"+name+".png");Note("shot "+name);yield return new WaitForSecondsRealtime(.3f);}
  static Vector2 ScreenOf(Transform t){var r=(RectTransform)t;return RectTransformUtility.WorldToScreenPoint(null,r.TransformPoint(r.rect.center));}
  static GameObject Find(string canvas,Func<Transform,bool> match){var c=GameObject.Find(canvas);if(!c)return null;return c.GetComponentsInChildren<Transform>(false).FirstOrDefault(match)?.gameObject;}
  IEnumerator Drag(GameObject go,Vector2 to){
   if(!go){Note("drag: missing object");yield break;}
   var from=ScreenOf(go.transform);var data=new PointerEventData(EventSystem.current){position=from,pressPosition=from,button=PointerEventData.InputButton.Left};
   ExecuteEvents.Execute(go,data,ExecuteEvents.pointerDownHandler);ExecuteEvents.Execute(go,data,ExecuteEvents.beginDragHandler);
   for(int i=1;i<=12;i++){data.position=Vector2.Lerp(from,to,i/12f);ExecuteEvents.Execute(go,data,ExecuteEvents.dragHandler);yield return null;}
   ExecuteEvents.Execute(go,data,ExecuteEvents.endDragHandler);ExecuteEvents.Execute(go,data,ExecuteEvents.pointerUpHandler);
   yield return new WaitForSecondsRealtime(.6f);
  }
  IEnumerator Tap(GameObject go){
   if(!go){Note("tap: missing object");yield break;}
   var data=new PointerEventData(EventSystem.current){position=ScreenOf(go.transform),button=PointerEventData.InputButton.Left};
   ExecuteEvents.Execute(go,data,ExecuteEvents.pointerClickHandler);yield return new WaitForSecondsRealtime(.5f);
  }
  bool Visible(string canvas,string child){var c=GameObject.Find(canvas);var dim=c?c.transform.Find("Dim"):null;return dim&&dim.gameObject.activeInHierarchy&&(child==null||Find(canvas,t=>t.name==child));}
  Shelf AnyShelf(Func<Shelf,bool> match=null)=>bridge.State.shelves.FirstOrDefault(s=>s.unlocked&&s.productId>0&&(match==null||match(s)))??bridge.State.shelves[0];

  // ------------------------------------------------------------------ scenarios
  // Asks the game (dev cheats) for real data; waits for it to show up in the snapshot.
  IEnumerator Dev(string action,string args,Func<bool> arrived){
   if(!CheckoutDesktopHost.Active){Note("no desktop host for "+action);yield break;}
   CheckoutDesktopHost.Active.Action(action,args,"");
   for(float t=0;t<6&&!arrived();t+=.2f)yield return new WaitForSecondsRealtime(.2f);
   Note(action+" "+args+" -> "+(arrived()?"ok":"not in the snapshot"));
  }
  IEnumerator Dock(){
   // A product with room left in the stockroom (base capacity is small), so the boxes fit.
   var shelf=AnyShelf(s=>Reserve(s.productId)>=0&&Reserve(s.productId)<=2);
   // Leftover test trucks from earlier runs go first.
   if(bridge.State.dock!=null&&bridge.State.dock.Any(d=>d.id.StartsWith("entrega-dev-")))yield return Dev("devClearDock","[]",()=>bridge.State.dock.All(d=>!d.id.StartsWith("entrega-dev-")));
   // The stockroom holds only a few units per product: make room first (put back by the unload).
   int had=Reserve(shelf.productId);
   if(had>=4)yield return Dev("devAdjustInventory","["+shelf.productId+",-4]",()=>Reserve(shelf.productId)==had-4);
   if(bridge.State.dock==null||bridge.State.dock.Length==0)yield return Dev("devArriveDelivery","["+shelf.productId+",30]",()=>bridge.State.dock!=null&&bridge.State.dock.Length>0);
   var real=bridge.State.dock?.FirstOrDefault();
   if(real!=null)Note($"using the real delivery {real.id}: {real.quantity-real.unloaded}x {real.productName} zone={real.zone} boxUnits={real.boxUnits}");
   else fakeDock=new DockEntry{id="entrega-autotest",productId=shelf.productId,productName=shelf.productName,category="laticinios",zone="refrigerados",quantity=20,unloaded=0,boxUnits=6,arrivedAt=CheckoutBridge.Now};
   int reserveBefore=Reserve(real?.productId??0);
   yield return null;CheckoutStockroom.ShowDock();yield return new WaitForSecondsRealtime(1.5f);
   Note("window open: "+Visible("CheckoutStockroom",null));yield return Shot("dock_open");
   GameObject Box()=>Find("CheckoutStockroom",t=>t.name=="Box"&&t.GetComponent<CheckoutDragToken>()&&!t.GetComponent<CheckoutDragToken>().Locked);
   var zone=(real??fakeDock).zone;
   var wrong=Find("CheckoutStockroom",t=>t.name.StartsWith("Rack ")&&t.name!="Rack "+zone);var right=Find("CheckoutStockroom",t=>t.name=="Rack "+zone);
   Note($"boxes={GameObject.Find("CheckoutStockroom")?.GetComponentsInChildren<CheckoutDragToken>().Length} wrongRack={(bool)wrong} rightRack={(bool)right}");
   var first=Box();var home=first?ScreenOf(first.transform):Vector2.zero;
   if(wrong)yield return Drag(first,ScreenOf(wrong.transform));
   Note("after wrong drop, box back home: "+(first&&Vector2.Distance(ScreenOf(first.transform),home)<30));yield return Shot("dock_wrong");
   for(int i=0;i<14;i++){var b=Box();if(!b)break;yield return Drag(b,ScreenOf(right.transform));if(i==1)yield return Shot("dock_two");}
   Note("boxes left in truck: "+(GameObject.Find("CheckoutStockroom")?.GetComponentsInChildren<CheckoutDragToken>().Count(d=>!d.Locked)));
   yield return new WaitForSecondsRealtime(1.5f);yield return Shot("dock_done");
   if(real!=null){
    yield return new WaitForSecondsRealtime(2);var after=bridge.State.dock?.FirstOrDefault(d=>d.id==real.id);
    Note("real delivery after unloading: "+(after==null?"gone from the dock (all unloaded)":$"{after.unloaded}/{after.quantity} unloaded"));
    Note($"stockroom reserve of {real.productName}: {reserveBefore} -> {Reserve(real.productId)}");
    Note("window closed by itself: "+!Visible("CheckoutStockroom",null));
   }
   // A second truck that does not fit (the product's stockroom is full now): boxes must bounce.
   if(real!=null){
    CloseAll();yield return new WaitForSecondsRealtime(.5f);
    // (test data only, so no stuck truck is left in the save)
    var full=fakeDock=new DockEntry{id="entrega-autotest-cheio",productId=real.productId,productName=real.productName,category=real.category,zone=real.zone,quantity=12,unloaded=0,boxUnits=2,room=0,arrivedAt=CheckoutBridge.Now};
    yield return null;yield return null;
    if(bridge.State.dock!=null&&bridge.State.dock.Length==1){
     Note($"full truck: {full.quantity}x {full.productName} room={full.room}");
     CheckoutStockroom.ShowDock();yield return new WaitForSecondsRealtime(1.5f);
     var fb=Box();var fh=fb?ScreenOf(fb.transform):Vector2.zero;var rr=Find("CheckoutStockroom",t=>t.name=="Rack "+full.zone);
     if(fb&&rr)yield return Drag(fb,ScreenOf(rr.transform));
     Note("full stockroom: box back on the truck: "+(fb&&Vector2.Distance(ScreenOf(fb.transform),fh)<30));yield return Shot("dock_full");
     CloseAll();
    }else Note("full-truck check skipped: the real delivery is still at the dock");
   }
  }
  int Reserve(int productId)=>bridge.State.restockSlots?.FirstOrDefault(s=>s.productId==productId)?.reserve??-1;

  IEnumerator Restock(){
   // Real low shelves when the stockroom has their product; test ones otherwise.
   var real=(bridge.State.restockSlots??Array.Empty<RestockSlot>()).Where(s=>s.reserve>0&&s.stock<s.capacity).OrderBy(s=>s.stock/(float)Mathf.Max(1,s.capacity)).Take(4).ToList();
   RestockSlot one,two;
   if(real.Count>0){one=real[0];two=real.Skip(1).FirstOrDefault(s=>s.productId!=one.productId);Note($"real slots: {string.Join(", ",real.Select(s=>$"{s.productName} {s.stock}/{s.capacity} res={s.reserve} zone={s.zone}"))}");}
   else{
    var a=AnyShelf();var b=AnyShelf(s=>s.productId!=a.productId)??a;
    fakeSlots=new[]{
     new RestockSlot{slotId="autotest-1",shelfId=a.id,shelfName=a.name,productId=a.productId,productName=a.productName,zone="refrigerados",stock=2,capacity=20,reserve=30},
     new RestockSlot{slotId="autotest-2",shelfId=b.id,shelfName=b.name,productId=b.productId==a.productId?a.productId+1:b.productId,productName=b.productName,zone="mercearia",stock=5,capacity=20,reserve=8},
    };one=fakeSlots[0];two=fakeSlots[1];Note("no real low shelf with stock; using test slots");
   }
   yield return null;CheckoutStockroom.ShowRestock();yield return new WaitForSecondsRealtime(1.5f);
   Note("window open: "+Visible("CheckoutStockroom",null));yield return Shot("restock_open");
   GameObject BoxFor(int pid)=>Find("CheckoutStockroom",t=>t.name=="Box"&&t.TryGetComponent<CheckoutStockBox>(out var tag)&&tag.productId==pid&&!t.GetComponent<CheckoutDragToken>().Locked);
   var card1=Find("CheckoutStockroom",t=>t.name=="Shelf "+one.slotId);var card2=two!=null?Find("CheckoutStockroom",t=>t.name=="Shelf "+two.slotId):null;
   Note($"cards={(bool)card1},{(bool)card2} box1={(bool)BoxFor(one.productId)} box2={(two!=null&&BoxFor(two.productId))}");
   if(card2){yield return Drag(BoxFor(one.productId),ScreenOf(card2.transform));Note("wrong shelf tried");}
   yield return Drag(BoxFor(one.productId),ScreenOf(card1.transform));yield return Shot("restock_one");
   if(card2)yield return Drag(BoxFor(two.productId),ScreenOf(card2.transform));
   yield return new WaitForSecondsRealtime(1f);yield return Shot("restock_two");
   if(real.Count>0){yield return new WaitForSecondsRealtime(1.5f);var live=bridge.State.restockSlots?.FirstOrDefault(s=>s.slotId==one.slotId);Note($"shelf {one.productName}: {one.stock} -> {live?.stock} (reserve {one.reserve} -> {live?.reserve})");}
  }

  IEnumerator Wires(string kind){
   var shelf=AnyShelf();
   IncidentEntry Live()=>bridge.State.incidents?.FirstOrDefault(i=>i.kind==kind);
   if(Live()==null)yield return Dev("devTriggerIncident","[\""+kind+"\"]",()=>Live()!=null);
   var real=Live();
   if(real!=null)Note($"using the real incident {real.id} on {real.shelfName} ({real.productName}) cost={real.fixCost} coins={bridge.State.coins}");
   else fakeIncident=new IncidentEntry{id="imprevisto-autotest-"+kind,kind=kind,shelfId=shelf.id,shelfName=shelf.name,productId=shelf.productId,productName=shelf.productName,createdAt=CheckoutBridge.Now,fixCost=10};
   var id=(real??fakeIncident).id;
   yield return null;yield return null;CheckoutIncidents.Show(id);yield return new WaitForSecondsRealtime(1.5f);
   Note("window open: "+Visible("CheckoutIncidentGame",null));yield return Shot(kind+"_open");
   const string c="CheckoutIncidentGame";
   var kit=Find(c,t=>t.name=="Kit");var panel=Find(c,t=>t.name=="Panel");
   yield return Drag(kit,ScreenOf(panel.transform));Note("kit with power on (should zap back): kit active="+(kit&&kit.activeSelf));
   yield return Tap(Find(c,t=>t.name=="Breaker"));Note("breaker off");yield return Shot(kind+"_off");
   yield return Drag(Find(c,t=>t.name=="Kit"),ScreenOf(panel.transform));yield return new WaitForSecondsRealtime(1.2f);
   var game=FindAnyObjectByType<CheckoutIncidents>();
   var wiresField=typeof(CheckoutIncidents).GetField("wires",BindingFlags.NonPublic|BindingFlags.Instance);
   var wires=((IEnumerable)wiresField.GetValue(game)).Cast<object>().ToList();
   Note("wires="+wires.Count);yield return Shot(kind+"_plugs");
   bool wrongDone=false;
   foreach(var w in wires){
    var type=w.GetType();var letter=(string)type.GetField("letter").GetValue(w);var plug=(RectTransform)type.GetField("plug").GetValue(w);
    var term=Find(c,t=>t.name=="Terminal "+letter);
    if(!wrongDone){var other=Find(c,t=>t.name.StartsWith("Terminal ")&&t.name!="Terminal "+letter);yield return Drag(plug?plug.gameObject:null,ScreenOf(other.transform));wrongDone=true;Note("wrong terminal tried");yield return Shot(kind+"_wrong");}
    yield return Drag(plug?plug.gameObject:null,ScreenOf(term.transform));
    Note($"wire {letter} connected="+type.GetField("connected").GetValue(w));
   }
   yield return Shot(kind+"_wired");
   yield return Tap(Find(c,t=>t.name=="Breaker"));Note("breaker on");yield return new WaitForSecondsRealtime(1.2f);yield return Shot(kind+"_done");
   if(real!=null){yield return new WaitForSecondsRealtime(2.5f);Note("real incident fixed in the game: "+(bridge.State.incidents?.All(i=>i.id!=id)??true)+" coins now "+bridge.State.coins);}
  }
 }
}
