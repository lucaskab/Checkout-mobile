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
  // Started by CheckoutBoot once the game scene is loaded (the Boot scene comes first on Android).
  internal static void Boot(){if(Application.isEditor&&File.Exists("Logs/autotest.txt"))new GameObject("CheckoutAutoTest").AddComponent<CheckoutAutoTest>();}

  readonly List<string> log=new List<string>();CheckoutBridge bridge;
  DockEntry fakeDock;RestockSlot[] fakeSlots;IncidentEntry fakeIncident;bool lowShelves;

  void Awake(){DontDestroyOnLoad(gameObject);Application.logMessageReceived+=OnLog;CheckoutBridge.TestPatch=Patch;}
  void OnDestroy(){Application.logMessageReceived-=OnLog;CheckoutBridge.TestPatch=null;}
  void OnLog(string message,string stack,LogType type){if(type==LogType.Exception||type==LogType.Error)log.Add($"[{type}] {message}\n{stack}");else if(message.StartsWith("CHECKOUT_RECEIPT")||message.StartsWith("CHECKOUT_PORTRAIT"))log.Add(message);}
  void Note(string s){log.Add($"{Time.realtimeSinceStartup:0.0}s {s}");Flush();}
  void Flush(){try{File.WriteAllLines("Logs/autotest_log.txt",log);}catch{}}

  IEnumerator Start(){
   var scenarios=File.ReadAllText("Logs/autotest.txt").Split(new[]{',',' '},StringSplitOptions.RemoveEmptyEntries);File.Delete("Logs/autotest.txt");
   foreach(var f in Directory.GetFiles("Logs","at_*.png"))File.Delete(f);
   Note("scenarios: "+string.Join(",",scenarios));
   // the start menu waits for a click: play
   for(float t=0;t<5;t+=.5f){var menu=FindAnyObjectByType<CheckoutStartMenu>();if(menu){menu.SendMessage("Choose",false,SendMessageOptions.DontRequireReceiver);break;}yield return new WaitForSecondsRealtime(.5f);}
   for(float t=0;t<90&&(bridge==null||bridge.State==null||bridge.State.shelves==null);t+=.5f){bridge=FindAnyObjectByType<CheckoutBridge>();yield return new WaitForSecondsRealtime(.5f);}
   if(scenarios.All(x=>x=="lamps")){foreach(var x in scenarios){Note("== "+x);yield return Lamps();}Finish();yield break;}// visual check, no host needed
   if(bridge==null||bridge.State==null){Note("no snapshot from the host");Finish();yield break;}
   Note($"snapshot ok: coins={bridge.State.coins} shelves={bridge.State.shelves.Length} dock={(bridge.State.dock?.Length??-1)} slots={(bridge.State.restockSlots?.Length??-1)}");
   yield return new WaitForSecondsRealtime(3);
   foreach(var s in scenarios){
    Note("== "+s);
    IEnumerator run=s=="eventsrigs"?RigTest():s.StartsWith("eventslayout")?LayoutReview(s):s.StartsWith("eventshorizon")?HorizonReview(s):s.StartsWith("eventsaudit")?AuditReview(s):s.StartsWith("eventshud")?HudReview(s):s.StartsWith("events")?Events(s):s.StartsWith("interactive")?InteractiveEvents(s):s=="register"?RegisterCash():s=="dock"?Dock():s=="restock"?Restock():s.StartsWith("fixtures")?Fixtures(s):s=="freezer"?Wires("freezer_sorvete"):s=="geladeira"?Wires("geladeira_bebidas"):null;
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
   // "fixtures": every slot a third full with stock in the stockroom (visual check of the REPOR game)
   if(lowShelves&&s.restockSlots!=null)foreach(var r in s.restockSlots){r.stock=Mathf.Min(r.stock,r.capacity/3);r.reserve=Mathf.Max(r.reserve,8);}
   if(fakeIncident!=null&&(s.incidents==null||s.incidents.All(d=>d.id!=fakeIncident.id))){s.incidents=(s.incidents??Array.Empty<IncidentEntry>()).Append(fakeIncident).ToArray();if(s.coins<fakeIncident.fixCost+1)s.coins=fakeIncident.fixCost+100;}
  }

  // Register, cash step ("register"): a made-up customer pays R$ 37 with a 50 note; the test scans, taps the money
  // into the drawer and gives R$ 13 of change (10 + 2 + 1), with a shot of each step.
  IEnumerator RegisterCash(){
   var game=CheckoutCounterGame.Instance;if(!game){Note("no register");yield break;}
   var fake=new CheckoutEntry{id="qa-cash",customerId="",customerName="Cliente teste",mood="",method="dinheiro",total=37,cashGiven=50,readyAt=0,expiresAt=double.MaxValue,
    items=new[]{new CheckoutLine{productId=1,quantity=2,name="Tomate",unitPrice=10},new CheckoutLine{productId=14,quantity=1,name="Refrigerante",unitPrice=17}}};
   game.OpenPreview(fake);
   yield return new WaitForSecondsRealtime(2f);
   yield return Shot("register_scan");
   yield return game.QaScanAll();
   yield return new WaitForSecondsRealtime(2.4f);
   yield return Shot("register_pay");
   game.QaPayAll();yield return new WaitForSecondsRealtime(2.4f);
   yield return Shot("register_change");
   game.QaGive(10);yield return new WaitForSecondsRealtime(.5f);
   game.QaGive(50);yield return new WaitForSecondsRealtime(.5f); // too much: refused
   game.QaGive(2);yield return new WaitForSecondsRealtime(.6f);
   yield return Shot("register_change2");
   game.QaGive(1);yield return new WaitForSecondsRealtime(1.6f);
   yield return Shot("register_done");
   game.Close();
  }

  // Interactive events ("interactive"), played for real through the host: the health inspector's round at the
  // mercadinho (each of her stops is fixed through the app once she stands at it, so she approves and hangs the seal),
  // then the jam's window sales (every request is clicked at once). Step log + shots Logs/ia_*.jpg.
  IEnumerator InteractiveEvents(string request){
   var fx=FindAnyObjectByType<CheckoutEventVisuals>();var map=FindAnyObjectByType<CheckoutMap>();
   if(!fx||!map){Note("no CheckoutEventVisuals / CheckoutMap");yield break;}
   foreach(var f in Directory.GetFiles("Logs","ia_*.jpg"))File.Delete(f);
   void Hud(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+action+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   Vector3 Flat(Vector3 v)=>new Vector3(v.x,0,v.z);
   Hud("devSetMarketEra","[\"mercadinho\"]");yield return new WaitForSecondsRealtime(6);
   Hud("setMarketOpen","[true]");yield return new WaitForSecondsRealtime(1);
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();
   // ---- vigilância sanitária
   int shot=0;float start=0;
   if(request!="interactive-window"){
   Hud("devActivateGameEvent","[\"vigilancia-sanitaria\"]");
   shot=0;var fixing=new HashSet<string>();start=Time.realtimeSinceStartup;float resolved=-1;
   while(Time.realtimeSinceStartup-start<420){
    yield return new WaitForSecondsRealtime(2.5f);
    var ev=bridge.State?.@event;var ins=GameObject.Find("Inspector");
    Note($"t={Time.realtimeSinceStartup-start:0} ev={ev?.id} ia={ev?.interaction} seal={ev?.seal} stops={(ev?.stops==null?"-":string.Join(",",ev.stops.Select(x=>x.status+":"+x.shelfId+":"+x.kind)))} inspector={(ins?ins.transform.position.ToString("F1")+" s="+ins.transform.localScale.x.ToString("0.00"):"none")}");
    if(ins&&ins.transform.localScale.x>.01f&&shot<70)CaptureAt(ins.transform.position+Vector3.up,7,$"ia_ins_{shot++:00}");
    var open=ev?.stops?.FirstOrDefault(x=>x.status=="open");
    if(open!=null&&!fixing.Contains(open.id)&&ins&&Vector3.Distance(Flat(ins.transform.position),Flat(map.Approach(open.shelfId)))<2.2f){
     fixing.Add(open.id);yield return new WaitForSecondsRealtime(4);CaptureAt(map.Approach(open.shelfId)+Vector3.up,9,$"ia_ins_{shot++:00}_stop");
     Hud("fixIncident","[\""+open.incidentId+"\"]");Note("fixed "+open.incidentId);
    }
    if(ev?.stops!=null&&ev.stops.Length>0&&ev.stops.All(x=>x.status=="fixed"||x.status=="failed")&&resolved<0)resolved=Time.realtimeSinceStartup;
    if(ev?.id!="vigilancia-sanitaria"&&shot>0&&resolved<0)resolved=Time.realtimeSinceStartup;
    if(resolved>0&&Time.realtimeSinceStartup-resolved>28)break;
   }
   var door=map.Entrance;CaptureAt(door+Vector3.up*1.2f,6,"ia_ins_door");if(home){home.Focus(new Vector3(door.x,0,door.z-4),20);yield return new WaitForSecondsRealtime(1);Capture("ia_ins_front");}
   }
   if(request=="interactive-inspect")yield break;
   var entrance=map.Entrance;
   // ---- engarrafamento: venda pela janela
   Hud("devAdjustInventory","[21,40]");Hud("devAdjustInventory","[14,40]");   // water and soda in the storeroom
   Hud("devActivateGameEvent","[\"engarrafamento\"]");yield return new WaitForSecondsRealtime(2);
   if(home){home.Focus(new Vector3(entrance.x+2,0,entrance.z-6),24);yield return new WaitForSecondsRealtime(1);}
   var served=new HashSet<string>();shot=0;start=Time.realtimeSinceStartup;
   while(Time.realtimeSinceStartup-start<150){
    yield return new WaitForSecondsRealtime(2f);
    var ev=bridge.State?.@event;
    Note($"t={Time.realtimeSinceStartup-start:0} ev={ev?.id} ia={ev?.interaction} served={ev?.windowServed}/{ev?.windowGoal} requests={(ev?.windowRequests==null?"-":string.Join(",",ev.windowRequests.Select(x=>x.id+":"+x.status+":"+x.lane+"/"+x.slot+":"+x.productName+":"+(x.inStock?"stock":"none"))))}");
    var waiting=ev?.windowRequests?.FirstOrDefault(x=>x.status=="waiting"&&!served.Contains(x.id));
    var bubble=waiting!=null?GameObject.Find("Window request "+waiting.id):null;
    if(bubble){
     yield return new WaitForSecondsRealtime(1.5f);CaptureAt(bubble.transform.position+Vector3.down*1.4f,7,$"ia_win_{shot++:00}_ask");Note(fx.QaWindowCar(waiting.id));
     CaptureAt(bubble.transform.position+Vector3.down*1.8f,2.5f,$"ia_win_{shot++:00}_window");
     served.Add(waiting.id);fx.ServeWindow(waiting.id);Note("serve "+waiting.id+" inStock="+waiting.inStock);
    }
    var root=GameObject.Find("Event interactions");
    var vendor=root?root.GetComponentsInChildren<Transform>().FirstOrDefault(t=>t.name.StartsWith("Event actor")):null;
    if(vendor&&vendor.localScale.x>.01f&&shot<70)CaptureAt(vendor.position+Vector3.up,6,$"ia_win_{shot++:00}");
   }
   if(home)home.HomeCamera();
  }

  // REPOR, the fixture itself ("fixtures-mesinha.conteiner.spati"): at each stage every fixture of the market, a third full,
  // played by CheckoutRestockGame.QaPlayAll; shots Logs/fx_<stage>_<fixture>_{0,1,2}.jpg (closed, half way, result).
  IEnumerator Fixtures(string request){
   var parts=request.Split('-');var stages=parts.Length>1?parts[1].Split('.'):new[]{"mesinha","tenda","banca","conteiner","spati","quitanda","supermercado"};
   foreach(var f in Directory.GetFiles("Logs","fx_*.jpg"))File.Delete(f);
   lowShelves=true;
   foreach(var stage in stages){
    // "atual" keeps the save's own stage (no era change)
    if(stage!="atual"){
     CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
     yield return new WaitForSecondsRealtime(6);
    }
    // fixtures this save does not own yet are added as test slots (the look only; their commands are refused)
    var extra=new List<RestockSlot>();
    foreach(var (fid,name,pids) in QaFixtures){
     if(bridge.State?.restockSlots!=null&&bridge.State.restockSlots.Any(r=>r.shelfId==fid))continue;
     for(int i=0;i<pids.Length;i++)extra.Add(new RestockSlot{slotId=i==0?fid:fid+":"+i,shelfId=fid,shelfName=name,productId=pids[i],productName="Produto "+pids[i],zone="mercearia",stock=2,capacity=8,reserve=8});
    }
    fakeSlots=extra.Count>0?extra.ToArray():null;yield return new WaitForSecondsRealtime(.6f);
    var ids=(bridge.State?.restockSlots??Array.Empty<RestockSlot>()).Select(r=>r.shelfId).Distinct().ToList();
    Note($"stage {stage}: era={bridge.State?.era?.id}/{bridge.State?.era?.index} fixtures={string.Join(",",ids)}");
    foreach(var id in ids){
     CheckoutRestockGame.ShowFixture(id);yield return new WaitForSecondsRealtime(1.2f);
     var game=CheckoutRestockGame.Instance;if(!game||!game.IsOpen){Note("not open: "+id);continue;}
     yield return Shot($"fx_{stage}_{id}_0");
     var run=StartCoroutine(game.QaPlayAll());
     yield return new WaitForSecondsRealtime(3.5f);yield return Shot($"fx_{stage}_{id}_1");
     for(float t=0;t<25&&game.IsOpen&&!Visible("CheckoutRestockGame","Result");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
     yield return new WaitForSecondsRealtime(1.2f);yield return Shot($"fx_{stage}_{id}_2");
     StopCoroutine(run);CloseRestock();yield return new WaitForSecondsRealtime(.5f);
    }
   }
   lowShelves=false;fakeSlots=null;
  }
  static readonly (string,string,int[])[] QaFixtures={("bakery","Prateleira da padaria",new[]{9,56,10,101,102}),("dairy","Geladeira de laticínios",new[]{5,8,7,6,28}),("snacks","Gôndola de doces",new[]{23,12,24,32,25}),("coffee","Gôndola de mercearia",new[]{51,52,55,53,54,26}),("pizza","Freezer de congelados",new[]{17,20,18,40,19}),("home","Gôndola de casa",new[]{34,58,35,59}),("icecream","Freezer de sorvetes",new[]{61,116,117,118})};
  static void CloseRestock(){var g=CheckoutRestockGame.Instance;if(g&&g.IsOpen)g.SendMessage("Close",SendMessageOptions.DontRequireReceiver);}

  // ------------------------------------------------------------------ helpers
  static void CloseAll(){
   foreach(var name in new[]{"CheckoutStockroom","CheckoutIncidentGame","CheckoutCounterGame"}){var c=GameObject.Find(name);if(!c)continue;var dim=c.transform.Find("Dim");if(dim&&dim.gameObject.activeSelf)dim.gameObject.SetActive(false);}
  }
  // ------------------------------------------------------------------ event scenes, stage by stage
  // "events-mesinha.banca" (or "events" for every stage): switches the market to each stage with the dev tool (on the QA
  // copy of the save) and photographs every event that can happen there: Logs/ev_<stage>_<event>.jpg.
  static readonly string[] Stages={"mesinha","tenda","banca","conteiner","spati","quitanda","minimercado","mercadinho","supermercado","hipermercado"};
  static readonly Dictionary<string,string> FirstStage=new Dictionary<string,string>{
   {"hora-do-rush","mesinha"},{"quinto-dia-util","mesinha"},{"feira-de-rua","mesinha"},{"onda-de-calor","mesinha"},{"chuva-forte","mesinha"},
   {"rua-em-obras","mesinha"},{"engarrafamento","mesinha"},{"fim-do-mes","mesinha"},{"sorteio-na-porta","tenda"},{"maquininha-fora-do-ar","tenda"},
   {"caminhao-de-ofertas","banca"},{"queda-de-energia","banca"},{"vigilancia-sanitaria","banca"},{"dia-de-jogo","conteiner"},{"cafe-com-a-equipe","conteiner"},
   {"excursao-da-escola","conteiner"},{"turno-puxado","conteiner"},{"viralizou","spati"},{"carro-de-som","spati"}};
  IEnumerator Events(string request){
   var fx=FindAnyObjectByType<CheckoutEventVisuals>();if(!fx){Note("no CheckoutEventVisuals");yield break;}
   var parts=request.Split('-');var stages=parts.Length>1?parts[1].Split('.'):Stages;
   string only=parts.Length>2?string.Join("-",parts.Skip(2)):null; // event ids hold dashes (fim-do-mes)
   foreach(var f in Directory.GetFiles("Logs","ev_*.jpg"))File.Delete(f);
   foreach(var stage in stages){
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
    yield return new WaitForSecondsRealtime(5);
    var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();yield return new WaitForSecondsRealtime(1.5f);
    var map=FindAnyObjectByType<CheckoutMap>();
    Note($"stage {stage}: era={bridge.State?.era?.id} door={(map?map.Entrance:Vector3.zero)} small={CheckoutStall.Small}");
    if(stage==stages[0])DumpAvenue();
    fx.Preview("");yield return new WaitForSecondsRealtime(.5f);Capture($"ev_{stage}_00-clean");
    if(map){var e=map.Entrance;home?.Focus(new Vector3(e.x,0,e.z-5),20);yield return new WaitForSecondsRealtime(1.2f);Capture($"ev_{stage}_01-front");home?.HomeCamera();yield return new WaitForSecondsRealtime(1f);}
    int at=Array.IndexOf(Stages,stage);
    foreach(var id in CheckoutEventVisuals.EventIds){
     if(only!=null&&id!=only)continue;
     if(FirstStage.TryGetValue(id,out var first)&&Array.IndexOf(Stages,first)>at)continue;
     fx.Preview(id);yield return new WaitForSecondsRealtime(.5f);
     // the scene's own focus (where its story happens), a wide shot and a close one; the stories run 4x faster
     // in between so the shots catch them under way (the bus at its stop, people walking in)
     var focus=fx.FocusOf(id);
     if(home)home.Focus(new Vector3(focus.x,0,focus.z),22);
     Time.timeScale=4;yield return new WaitForSecondsRealtime(2.5f);Time.timeScale=1;yield return new WaitForSecondsRealtime(.3f);
     Capture($"ev_{stage}_{id}");CaptureAt(focus+Vector3.up,10,$"ev_{stage}_{id}_close");
     Time.timeScale=4;yield return new WaitForSecondsRealtime(2.5f);Time.timeScale=1;yield return new WaitForSecondsRealtime(.3f);
     CaptureAt(focus+Vector3.up,10,$"ev_{stage}_{id}_later");
     if(home)home.HomeCamera();
    }
    fx.Preview("");
   }
  }
  // Block layout per stage ("eventslayout-supermercado.hipermercado"): where the shop, the parking lot, the depot,
  // the loading yard and the delivery trucks are. Logs/layout_<stage>.txt + shots Logs/lay_<stage>_*.jpg.
  IEnumerator LayoutReview(string request){
   var parts=request.Split('-');var stages=parts.Length>1?parts[1].Split('.'):new[]{"minimercado","mercadinho","supermercado","hipermercado"};
   foreach(var f in Directory.GetFiles("Logs","lay_*.jpg"))File.Delete(f);
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();
   foreach(var stage in stages){
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
    yield return new WaitForSecondsRealtime(7);
    var lines=new List<string>();var map=FindAnyObjectByType<CheckoutMap>();var world=home?home.world:null;
    lines.Add($"stage {stage} era={bridge.State?.era?.id} layout={JsonUtility.ToJson(bridge.State?.layout)} door={(map?map.Entrance:Vector3.zero)} lot={CheckoutCityTraffic.Lot}");
    void B(string label,Transform t){if(!t){lines.Add($"{label}: missing");return;}var rs=t.GetComponentsInChildren<Renderer>().Where(r=>r.enabled&&!(r is ParticleSystemRenderer)).ToArray();
     if(!t.gameObject.activeInHierarchy||rs.Length==0){lines.Add($"{label}: inactive/hidden at {t.position}");return;}var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
     lines.Add($"{label}: x[{b.min.x:0.0},{b.max.x:0.0}] z[{b.min.z:0.0},{b.max.z:0.0}] y[{b.min.y:0.0},{b.max.y:0.0}] pivot {t.position.x:0.0},{t.position.z:0.0} rot {t.eulerAngles.y:0}");}
    if(world){
     var shell=world.GetComponentInChildren<CheckoutMarketShell>(true);B("shell",shell?shell.transform:null);
     foreach(var n in new[]{"Warehouse",CheckoutMarketLayout.GrandWarehouse,CheckoutMarketLayout.GrandYard,"Loading Yard Details","Market parking lot","Expansion Park","Market Stage Dressing","Supplied Delivery Cargo","Worker_Delivery","Anim_Truck_5","Anim_Truck_8","Anim_Truck_11"})B(n,world.Find(n));
     foreach(Transform c in world)if(c.name.StartsWith("Lot site"))B(c.name,c);
     var yard=world.Find(CheckoutMarketLayout.GrandYard+"/Bays");if(yard)foreach(Transform bay in yard)lines.Add($"grand bay {bay.name} at {bay.position.x:0.0},{bay.position.z:0.0} rot {bay.eulerAngles.y:0}");
     var worker=world.GetComponentInChildren<MarketDay.MarketDeliveryWorker>(true);
     if(worker){lines.Add("delivery door "+worker.storageDoor.position+" route "+string.Join(" ",worker.route.Select(p=>$"({p.x:0.0},{p.z:0.0})")));}
    }
    for(int i=0;i<CheckoutCityTraffic.Bays;i++)lines.Add($"parking bay {i}: {CheckoutCityTraffic.Bay(i)} door {CheckoutCityTraffic.Door(i)}");
    // The trucks parked on their bays for the shots, then one driving in from the street.
    var trucks=map?map.Trucks:null;
    if(trucks){trucks.DockAllForReview();lines.Add(trucks.Describe());}
    if(world){var worker=world.GetComponentInChildren<MarketDay.MarketDeliveryWorker>(true);if(worker)lines.Add("worker route "+string.Join(" ",worker.route.Select(p=>$"({p.x:0.0},{p.y:0.00},{p.z:0.0})")));}
    var layoutNow=map?map.Layout:null;if(layoutNow)lines.Add($"storage door {layoutNow.StorageDoor} facing {layoutNow.StorageFacing} beside {CheckoutMarketLayout.StorageBeside}");
    File.WriteAllLines($"Logs/layout_{stage}.txt",lines);Note($"layout {stage}: {lines.Count} lines");
    yield return new WaitForSecondsRealtime(.5f);
    TopDown(new Vector3(0,0,18),64,$"lay_{stage}_top");
    CaptureAt(new Vector3(0,0,14),46,$"lay_{stage}_iso");
    CaptureAt(new Vector3(8,0,26),26,$"lay_{stage}_back");
    if(trucks){
     var yardAt=trucks.Kind==CheckoutDeliveryTrucks.Yard.Grand?new Vector3(10,0,31):trucks.Kind==CheckoutDeliveryTrucks.Yard.Depot?new Vector3(12,0,6):new Vector3(4,0,-11);
     CaptureAt(yardAt,20,$"lay_{stage}_yard");
     var t=trucks.DriveInForReview();float started=Time.realtimeSinceStartup;
     foreach(var at in new[]{5f,11f,17f,24f}){while(Time.realtimeSinceStartup-started<at)yield return null;CaptureAt(yardAt,30,$"lay_{stage}_drive{at:0}");Note($"drive {stage} {at}s truck at {(t?t.position:Vector3.zero)} docked={trucks.Docked(t)}");}
     trucks.EndReview();
    }
   }
  }
  // Shop audit per stage ("eventsaudit-supermercado.hipermercado"): doors, stage dressing, the street furniture
  // around the front of the shop and the checkout area inside. Logs/audit_<stage>.txt + shots Logs/au_<stage>_*.jpg.
  IEnumerator AuditReview(string request){
   var parts=request.Split('-');var stages=parts.Length>1?parts[1].Split('.'):new[]{"minimercado","mercadinho","supermercado","hipermercado"};
   foreach(var f in Directory.GetFiles("Logs","au_*.jpg"))File.Delete(f);
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();
   foreach(var stage in stages){
    CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
    // Long enough for the growth timelapse (the old walls stand in the new shop while it plays).
    yield return new WaitForSecondsRealtime(18);
    var lines=new List<string>();var map=FindAnyObjectByType<CheckoutMap>();var world=home?home.world:null;
    lines.Add($"stage {stage} layout={JsonUtility.ToJson(bridge.State?.layout)} entrance={(map?map.Entrance:Vector3.zero)} lot={CheckoutCityTraffic.Lot}");
    // The furniture still waiting to be placed (the QA save starts with it) goes in, as the build mode would put it.
    var inside=CheckoutInterior.Active;
    if(inside){var zone0=inside.CheckoutZone;var floor0=inside.FloorRect;
     foreach(var w in inside.waiting.ToList()){bool counter=w.Value.type=="checkout"||w.Value.type=="kiosk";
      var at=counter?new Vector3(zone0.center.x,CheckoutInterior.Floor,floor0.yMin+2):new Vector3(floor0.center.x-2,CheckoutInterior.Floor,floor0.center.y);
      var placed=inside.PlaceWaiting(w.Key,at);lines.Add($"placed {w.Key} ({w.Value.type}): {(placed!=null?placed.root.position+" rot "+placed.rot:"no room")}");}
     map?.FurnitureChanged(false);
     yield return new WaitForSecondsRealtime(1);}
    string Path(Transform t){var p=t.name;for(int i=0;i<3&&t.parent;i++){t=t.parent;p=t.name+"/"+p;}return p;}
    void B(string label,Transform t){if(!t){lines.Add($"{label}: missing");return;}var rs=t.GetComponentsInChildren<Renderer>().Where(r=>r.enabled&&!(r is ParticleSystemRenderer)).ToArray();
     if(!t.gameObject.activeInHierarchy||rs.Length==0){lines.Add($"{label}: inactive/hidden at {t.position}");return;}var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
     lines.Add($"{label}: x[{b.min.x:0.00},{b.max.x:0.00}] z[{b.min.z:0.00},{b.max.z:0.00}] y[{b.min.y:0.00},{b.max.y:0.00}] pivot {t.position.x:0.00},{t.position.z:0.00} rot {t.eulerAngles.y:0} scale {t.localScale}");}
    var shell=world?world.GetComponentInChildren<CheckoutMarketShell>(true):null;
    if(shell){B("shell",shell.transform);foreach(var n in new[]{"Sidelight L","Sidelight R","Mullion L","Mullion R","Portal jamb L","Portal jamb R","Portal header","Portal sign","Rear jamb L","Rear jamb R","Rear lintel"})B("shell "+n,shell.Walls.Find(n));lines.Add($"rear door {shell.RearDoor} ramp {shell.RampTop}->{shell.RampEnd}");}
    if(world)foreach(var t in world.GetComponentsInChildren<Transform>(true))if(t.name.StartsWith("Anim_Door")||(t.parent&&t.parent.name=="Clean entrance frame"))B("door "+Path(t),t);
    var roller=GameObject.Find("Rear roller door");B("roller door",roller?roller.transform:null);
    foreach(var item in FindObjectsByType<CheckoutStageItem>(FindObjectsInactive.Include,FindObjectsSortMode.None))B($"item {item.name} [{item.minStage}-{item.maxStage}]",item.transform);
    // Street furniture and props on the front of the block (the shop forecourt, the parking lot, the sidewalk).
    var seen=new HashSet<Transform>();
    foreach(var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)){
     if(!r.enabled||!r.gameObject.activeInHierarchy||r is ParticleSystemRenderer)continue;var b=r.bounds;
     if(b.center.x<-20||b.center.x>22||b.center.z<-16||b.center.z>8||b.size.x>14||b.size.z>14)continue;
     var t=r.transform;while(t.parent&&t.parent!=world&&t.parent.parent!=world&&t.parent.GetComponent<Renderer>()==null&&t.parent.childCount<12)t=t.parent;
     if(shell&&t.IsChildOf(shell.transform))continue;if(t.name.StartsWith("Customer")||t.name.StartsWith("Worker")||t.GetComponentInParent<CheckoutWalker>())continue;
     if(!seen.Add(t))continue;B("prop "+Path(t),t);}
    var it=CheckoutInterior.Active;
    if(it){lines.Add($"floor {it.FloorRect} checkout zone {it.CheckoutZone}");foreach(var id in new[]{"checkout:main","checkout:extra","kiosk:1","kiosk:2"}){var x=it.Get(id);if(x==null||!x.root){lines.Add($"{id}: none");continue;}string why;bool fits=it.Fits(x,x.root.position,x.rot,out why);lines.Add($"{id}: at {x.root.position} rot {x.rot} queue0 {it.QueueSpot(id,0)} fits {fits} {why}");}}
    lines.Sort((a,b)=>string.CompareOrdinal(a.StartsWith("prop")?"z"+a:a,b.StartsWith("prop")?"z"+b:b));
    File.WriteAllLines($"Logs/audit_{stage}.txt",lines);Note($"audit {stage}: {lines.Count} lines");
    yield return new WaitForSecondsRealtime(.5f);
    var door=map?map.Entrance:new Vector3(-1.75f,0,-6);
    CaptureAt(door+new Vector3(0,1.5f,0),9,$"au_{stage}_front");
    CaptureAt(new Vector3(2,0,-6),26,$"au_{stage}_facade");
    if(shell)CaptureAt(shell.RearDoor+new Vector3(0,1,0),9,$"au_{stage}_rear");
    CaptureAt(new Vector3(11,0,-6),22,$"au_{stage}_lot");
    TopDown(new Vector3(0,0,-4),44,$"au_{stage}_plan");
    if(it){var f=it.FloorRect;TopDown(new Vector3(f.center.x,0,f.center.y),Mathf.Max(f.width,f.height)+3,$"au_{stage}_floor");var zc=it.CheckoutZone.center;CaptureAt(new Vector3(zc.x-2,.8f,zc.y),Mathf.Max(12,it.FloorRect.height*.8f),$"au_{stage}_checkouts");}
   }
  }
  // HUD screens ("eventshud-products.storage.suppliers"): opens each route like the toolbar does and takes a
  // full-screen shot with the HUD (Logs/hud_<route>.png). "+" in a route stands for ":" (products+todos).
  IEnumerator HudReview(string request){
   var dash=request.IndexOf('-');var routes=dash>=0?request.Substring(dash+1).Split('.'):new[]{"products","storage","suppliers","sectors","missions","achievements"}; // routes may hold '-' (kitchen+baguete-rustica)
   foreach(var f in Directory.GetFiles("Logs","at_hud_*.png"))File.Delete(f);
   var host=CheckoutDesktopHost.Active;if(!host){Note("no desktop host");yield break;}
   yield return new WaitForSecondsRealtime(2);
   foreach(var raw in routes){
    // "@action~1~2" runs a store action on the QA save first (orderLowStock, devArriveDelivery~12…).
    if(raw.StartsWith("@")){var bits=raw.Substring(1).Split('~');
     CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+bits[0]+"\",\"action\":\""+bits[0]+"\",\"args\":["+string.Join(",",bits.Skip(1))+"]}");
     yield return new WaitForSecondsRealtime(1.5f);continue;}
    var route=raw.Replace('+',':');host.Route("!"+route);
    yield return new WaitForSecondsRealtime(1.6f);
    yield return Shot("hud_"+raw.Replace('+','_'));
   }
   host.Route("");
  }
  // Map edge ("eventshorizon"): what the player sees past the city at the widest zoom, from the corners of the pan
  // limits (MarketSimulation: focus x ±26, z -16..34, zoom up to 38). Logs/horizon.txt + Logs/hz_*.jpg.
  IEnumerator HorizonReview(string request){
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-hz\",\"action\":\"devSetMarketEra\",\"args\":[\"hipermercado\"]}");
   yield return new WaitForSecondsRealtime(7);
   foreach(var f in Directory.GetFiles("Logs","hz_*.jpg"))File.Delete(f);
   var lines=new List<string>();var home=FindAnyObjectByType<MarketDay.MarketSimulation>();var world=home?home.world:null;
   foreach(var tiles in FindObjectsByType<UnityEngine.Tilemaps.TilemapRenderer>(FindObjectsSortMode.None))lines.Add($"tilemap {tiles.transform.parent?.name}/{tiles.name} active {tiles.gameObject.activeInHierarchy} shader {tiles.sharedMaterial?.shader.name} bounds {tiles.bounds.min} {tiles.bounds.max} order {tiles.sortingOrder} y {tiles.transform.position.y}");
   foreach(var r in FindObjectsByType<MeshRenderer>(FindObjectsSortMode.None)){var b=r.bounds;if(b.size.x>90||b.size.z>90)lines.Add($"big renderer {r.transform.parent?.name}/{r.name} bounds {b.min} {b.max} mat {r.sharedMaterial?.name} shader {r.sharedMaterial?.shader.name}");}
   var main=Camera.main;if(main)lines.Add($"camera ortho {main.orthographic} size {main.orthographicSize} rot {main.transform.eulerAngles} bg {main.backgroundColor} fog {RenderSettings.fog} far {main.farClipPlane}");
   if(world)foreach(Transform group in world){var rs=group.GetComponentsInChildren<Renderer>(true);if(rs.Length==0)continue;var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
    lines.Add($"group {group.name}: {group.childCount} children, x[{b.min.x:0},{b.max.x:0}] z[{b.min.z:0},{b.max.z:0}] y[{b.min.y:0.0},{b.max.y:0.0}]");}
   var est=world?world.Find("City Establishments"):null;
   if(est)foreach(Transform c in est){var rs=c.GetComponentsInChildren<MeshRenderer>(true);if(rs.Length==0)continue;var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);
    lines.Add($"  building {c.name}: centre ({b.center.x:0.0},{b.center.z:0.0}) size ({b.size.x:0.0},{b.size.y:0.0},{b.size.z:0.0}) yaw {c.eulerAngles.y:0} renderers {rs.Length} mats {string.Join(",",rs.SelectMany(r=>r.sharedMaterials).Where(m=>m).Select(m=>m.name).Distinct().Take(6))}");}
   var hz=FindAnyObjectByType<CheckoutMap>()?.Horizon;if(hz){lines.Add(hz.Describe());var pr=hz.Playable;var hroot=GameObject.Find("City Horizon")?.transform;
    foreach(var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)){if((hroot&&r.transform.IsChildOf(hroot))||r.name.StartsWith("Ground"))continue;var b=r.bounds;if(b.size.sqrMagnitude<.01f)continue;
     if(b.center.x<pr.xMin||b.center.x>pr.xMax||b.center.z<pr.yMin||b.center.z>pr.yMax)lines.Add($"outside: {r.transform.parent?.name}/{r.name} centre ({b.center.x:0},{b.center.y:0.0},{b.center.z:0}) size ({b.size.x:0},{b.size.y:0.0},{b.size.z:0}) {r.sharedMaterial?.name}");}}
   File.WriteAllLines("Logs/horizon.txt",lines);
   foreach(var v in new[]{(new Vector3(0,0,9),38f,"wide"),(new Vector3(-26,0,-16),38f,"sw"),(new Vector3(26,0,-16),38f,"se"),(new Vector3(-26,0,34),38f,"nw"),(new Vector3(26,0,34),38f,"ne"),(new Vector3(0,0,9),24f,"mid")})
    CaptureAt(v.Item1,v.Item2*2,"hz_"+v.Item3);
   TopDown(new Vector3(0,0,6),220,"hz_plan");
  }
  // Straight down over the block (orthographic), so lots, parking lot and depot read like a plan.
  void TopDown(Vector3 center,float size,string name){
   var go=new GameObject("QA plan camera");var cam=go.AddComponent<Camera>();if(Camera.main)cam.CopyFrom(Camera.main);
   cam.orthographic=true;cam.orthographicSize=size*.5f;go.transform.SetPositionAndRotation(center+Vector3.up*120,Quaternion.Euler(90,0,0));cam.nearClipPlane=1;cam.farClipPlane=300;
   var rt=new RenderTexture(1280,1280,24){antiAliasing=4};cam.targetTexture=rt;cam.aspect=1;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;
   var image=new Texture2D(1280,1280,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1280,1280),0,0);image.Apply();RenderTexture.active=active;
   File.WriteAllBytes("Logs/"+name+".jpg",image.EncodeToJPG(85));Destroy(image);cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(go);Note("shot "+name);
  }
  // Rig check: every event rig and a row of characters playing event moves, at known spots on the avenue.
  // Logs/rigtest.txt lists each rig's clips, parts and where its bones are; shots Logs/ev_rigs_*.jpg.
  IEnumerator RigTest(){
   var art=new CheckoutEventAssets();var root=new GameObject("Rig test").transform;var lines=new List<string>();
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();
   void Info(Transform rig){var anim=CheckoutEventAssets.RigAnimation(rig);var clips=new List<string>();if(anim)foreach(AnimationState s in anim)clips.Add(s.name+"("+s.length.ToString("0.00")+")");
    lines.Add($"## {rig.name} at {rig.position} yaw {rig.eulerAngles.y:0}: clips {string.Join(",",clips)}");
    foreach(var t in rig.GetComponentsInChildren<Transform>(true)){var r=t.GetComponent<Renderer>();if(r){var b=r.bounds;lines.Add($"  part {t.name} [{r.GetType().Name}] x[{b.min.x:0.00},{b.max.x:0.00}] y[{b.min.y:0.00},{b.max.y:0.00}] z[{b.min.z:0.00},{b.max.z:0.00}]");}
     else if(t!=rig&&t.childCount<=8)lines.Add($"  bone {t.name} at {t.position.x:0.00},{t.position.y:0.00},{t.position.z:0.00} fwd {t.forward.x:0.0},{t.forward.y:0.0},{t.forward.z:0.0} up {t.up.x:0.0},{t.up.y:0.0},{t.up.z:0.0}");}}
   var y=.15f;
   var bus=art.Rig(root,"Rig_CityBus",new Vector3(4,y,-14),180);CheckoutEventAssets.PlayClip(CheckoutEventAssets.RigAnimation(bus),"DoorsOpen",WrapMode.ClampForever);
   art.Rig(root,"Rig_BoxTruck",new Vector3(4,y,-20),180);
   var wheel=art.Rig(root,"Rig_PrizeWheel",new Vector3(0,y,-10),0,1,"Spin");
   var hoe=art.Rig(root,"Rig_Backhoe",new Vector3(16,y,-20),0,1,"Dig");
   var bucket=art.Rig(root,"Rig_BucketTruck",new Vector3(16,y,-14),180,1,"Work");
   var flag=art.Rig(root,"Rig_FlagPole",new Vector3(-4,y,-11),0,1,"Wind");
   var car=art.Rig(root,"Rig_Car",new Vector3(-6,y,-17),0,1,"Idle");
   string[] moves={"Cheer","Clap","Wave","FilmPhone","WorkOverhead","Fan","PullWheel","HoldHandle","TypeATM","Clipboard","SitSip","Tired"};
   for(int i=0;i<moves.Length;i++)art.Actor(root,i%2==0?"Customer_06":"Customer_08",new Vector3(1.5f+i*1.1f,y,-9.6f),180,"Idle",1,moves[i],0);
   var plain=art.Actor(root,"Customer_06",new Vector3(1.5f+moves.Length*1.1f,y,-9.6f),180,"Idle");
   yield return new WaitForSecondsRealtime(1.2f);
   foreach(var r in new[]{bus,wheel,hoe,bucket,flag,car})Info(r);
   foreach(var m in root.GetComponentsInChildren<CheckoutEventMoves>())lines.Add($"move {m.Clip} on {m.transform.parent?.parent?.name}: enabled {m.enabled}");
   File.WriteAllLines("Logs/rigtest.txt",lines);Note("rigtest lines "+lines.Count);
   if(home){home.Focus(new Vector3(6,0,-15),26);yield return new WaitForSecondsRealtime(1.5f);Capture("ev_rigs_avenue");
    for(int k=0;k<4;k++){yield return new WaitForSecondsRealtime(.45f);CaptureAt(new Vector3(4.5f+k*0f,1.2f,-9.6f),7.5f,"ev_rigs_moves_"+k);}
    CaptureAt(new Vector3(11f,1.2f,-9.6f),7.5f,"ev_rigs_moves_b");
    home.Focus(new Vector3(4,0,-14),12);yield return new WaitForSecondsRealtime(.6f);Capture("ev_rigs_bus");home.HomeCamera();}
   Destroy(root.gameObject);art.Dispose();
  }
  // Everything along the avenue in front of the block (sidewalks, crossings, lamps, trees, the roundabout): Logs/avenue.txt.
  void DumpAvenue(){
   var lines=new List<string>();
   foreach(var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)){
    if(!r.enabled||!r.gameObject.activeInHierarchy)continue;var b=r.bounds;
    if(b.center.z<-32||b.center.z>-4||b.center.x<-40||b.center.x>40)continue;if(b.size.x>60||b.size.z>60)continue;
    var t=r.transform;var path=t.name;for(int i=0;i<3&&t.parent;i++){t=t.parent;path=t.name+"/"+path;}
    lines.Add($"{path}\tx[{b.min.x:0.0},{b.max.x:0.0}] z[{b.min.z:0.0},{b.max.z:0.0}] y[{b.min.y:0.0},{b.max.y:0.0}]");
   }
   lines.Sort();File.WriteAllLines("Logs/avenue.txt",lines);Note("avenue objects: "+lines.Count);
  }
  // A close shot with the game camera's angle, aimed at `target` (a second camera, so the game's own stays put).
  void CaptureAt(Vector3 target,float size,string name){
   var main=Camera.main;if(!main){Note("no camera");return;}
   var go=new GameObject("QA close camera");var cam=go.AddComponent<Camera>();cam.CopyFrom(main);
   if(main.GetComponent<CheckoutEdgeFog>())go.AddComponent<CheckoutEdgeFog>();
   float dist=size*2.2f;go.transform.rotation=main.transform.rotation;go.transform.position=target-main.transform.forward*dist;
   if(cam.orthographic)cam.orthographicSize=size*.5f;else cam.fieldOfView=2*Mathf.Atan(size*.5f/dist)*Mathf.Rad2Deg;
   cam.nearClipPlane=.3f;cam.farClipPlane=dist+200;
   var rt=new RenderTexture(1280,800,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;
   var image=new Texture2D(1280,800,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1280,800),0,0);image.Apply();RenderTexture.active=active;
   File.WriteAllBytes("Logs/"+name+".jpg",image.EncodeToJPG(82));Destroy(image);cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(go);Note("shot "+name);
  }
  void Capture(string name){
   var camera=Camera.main;if(!camera){Note("no camera");return;}
   var old=camera.targetTexture;var active=RenderTexture.active;var rt=new RenderTexture(1280,800,24){antiAliasing=4};
   camera.targetTexture=rt;camera.Render();RenderTexture.active=rt;var image=new Texture2D(1280,800,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1280,800),0,0);image.Apply();
   camera.targetTexture=old;RenderTexture.active=active;File.WriteAllBytes("Logs/"+name+".jpg",image.EncodeToJPG(82));Destroy(image);rt.Release();Destroy(rt);Note("shot "+name);
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
   yield return null;CheckoutStockroom.ShowLegacyDock();yield return new WaitForSecondsRealtime(1.5f);
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
     CheckoutStockroom.ShowLegacyDock();yield return new WaitForSecondsRealtime(1.5f);
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
