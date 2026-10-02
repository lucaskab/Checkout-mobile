using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using MarketDay;
namespace Checkout {
 public class CheckoutMap:MonoBehaviour {
  Transform world;CheckoutBridge bridge;readonly Dictionary<string,CheckoutStatusMarker> markers=new Dictionary<string,CheckoutStatusMarker>();readonly CheckoutEventAssets markerArt=new CheckoutEventAssets();readonly Dictionary<string,Transform> staff=new Dictionary<string,Transform>();readonly Dictionary<string,GameObject> decorations=new Dictionary<string,GameObject>();readonly Dictionary<string,Vector3> homes=new Dictionary<string,Vector3>();readonly Dictionary<string,Quaternion> truckRotations=new Dictionary<string,Quaternion>();readonly HashSet<string> dispatchedDeliveryOrders=new HashSet<string>();MarketDeliveryWorker deliveryWorker;
  readonly Dictionary<string,Vector3> fixtures=new Dictionary<string,Vector3>{{"produce",P(6.55f,.45f)},{"dairy",P(-6.4f,-1.6f)},{"bakery",P(-6.45f,1.05f)},{"snacks",P(-1.6f,.3f)},{"drinks",P(2,-1.18f)},{"coffee",P(-2.2f,6.37f)},{"pizza",P(4.85f,-5.36f)},{"home",P(-6.4f,4.2f)},{"icecream",P(6.4f,-4.2f)}};
  readonly Dictionary<string,Vector3> approaches=new Dictionary<string,Vector3>{{"produce",P(5.1f,-1.2f)},{"dairy",P(-4,-1.6f)},{"bakery",P(-3.8f,2.55f)},{"snacks",P(-.18f,.5f)},{"drinks",P(3.3f,-1.2f)},{"coffee",P(-2f,5.1f)},{"pizza",P(4.85f,-3.85f)},{"home",P(-4.9f,4.2f)},{"icecream",P(4.9f,-4.2f)}};
  CheckoutMarketLayout layout;readonly Dictionary<Transform,Vector3> targets=new Dictionary<Transform,Vector3>();
  public Vector3 Point(Vector3 point)=>layout?layout.Point(point):point;
  // Furniture placed in build mode; when the scene has the Interior Kit it replaces the fixed fixtures.
  public CheckoutInterior Interior {get;private set;}
  bool Furnished=>Interior&&Interior.Ready;
  CheckoutInterior.Item Piece(string id)=>Furnished&&id!=null?Interior.Get(Special(id)?CheckoutInterior.SectorKey(id.Substring(7)):CheckoutInterior.ShelfKey(id)):null;
  public Vector3 QueueSpot(CheckoutLane lane,int i)=>CheckoutStall.Small?CheckoutStall.QueueSpot(i):Furnished&&lane?.itemId!=null?Interior.QueueSpot(lane.itemId,i):Register;
  public Vector3 HelpSpot(int i)=>CheckoutStall.Small?CheckoutStall.HelpSpot(i):Furnished?Interior.FreeSpotNear(Point(P(.9f,-5.9f)),i):Point(new Vector3(.9f+i*.85f,.74f,-5.9f));
  Vector3 MarkerPoint(string id,float fallback){var it=Piece(id);return it!=null?it.root.position+Vector3.up*it.piece.markerHeight:Fixture(id)+Vector3.up*fallback;}
  readonly Dictionary<string,Vector3> axes=new Dictionary<string,Vector3>();readonly Dictionary<string,Vector3> staffSpots=new Dictionary<string,Vector3>();
  public Vector3 Entrance=>CheckoutStall.Small?CheckoutStall.Entrance:Point(P(-1.75f,-8.7f));
  public Vector3 CheckoutPoint(Vector3 point)=>layout?CheckoutMarketLayout.CheckoutPoint(point,layout.State):point;
  public Vector3 Register=>CheckoutStall.Small?CheckoutStall.Register:CheckoutPoint(MarketSimulation.Register);
  public CheckoutLanes Lanes {get;private set;}
  public Vector3 LaneRegister(CheckoutLane lane)=>CheckoutStall.Small?CheckoutStall.Register:lane!=null&&lane.itemId!=null&&Furnished?Interior.Register(lane.itemId):lane==null||lane.places==null?Register:Point(lane.register);
  public bool HasParking=>!CheckoutStall.Small&&layout&&layout.State.parking;
  // Eras 0-4: the stall in front of the lots replaces the building (see CheckoutStall).
  public CheckoutStall Stall {get;private set;}
  CheckoutEventVisuals events;float workClock;Snapshot state;Material teal;
  static Vector3 P(float x,float z)=>new Vector3(x,.74f,z);
  Bounds SectorBounds(string id){var root=world.Find("Sector_"+id.Substring(7));var renderers=root?root.GetComponentsInChildren<Renderer>(true).Where(r=>r.enabled).ToArray():Array.Empty<Renderer>();if(renderers.Length==0)return new Bounds(P(0,4.3f),Vector3.one);var bounds=renderers[0].bounds;foreach(var renderer in renderers.Skip(1))bounds.Encapsulate(renderer.bounds);return bounds;}
  Vector3 SectorPosition(string id){var it=Piece(id);if(it!=null)return it.root.position;var bounds=SectorBounds(id);return P(bounds.center.x,bounds.center.z);}
  Vector3 SectorApproach(string id){var it=Piece(id);if(it!=null)return Interior.Approach(it);var bounds=SectorBounds(id);return P(bounds.center.x,bounds.min.z-.65f);}
  // In the shop expansions the shelves the player placed inside are used; otherwise the stall crates.
  bool StallCrate(string id)=>CheckoutStall.Small&&!(CheckoutStall.ShopInside&&Piece(id) is CheckoutInterior.Item it&&it.root&&it.root.gameObject.activeInHierarchy&&!it.building);
  public Vector3 Fixture(string id)=>StallCrate(id)?CheckoutStall.Crate(id):Piece(id) is CheckoutInterior.Item it?it.root.position:Special(id)?SectorPosition(id):world&&world.GetComponentInChildren<CheckoutShelfSlots>()?Point(CheckoutShelfSlots.Position(id)):fixtures.TryGetValue(id,out var p)?Point(p):Point(P(0,0));
  public Vector3 Approach(string id)=>StallCrate(id)?CheckoutStall.Approach(id):Piece(id) is CheckoutInterior.Item it?Interior.Approach(it):Special(id)?SectorApproach(id):world&&world.GetComponentInChildren<CheckoutShelfSlots>()?Point(CheckoutShelfSlots.Position(id))+Vector3.back*(.7f*layout.State.depthScale+.55f):approaches.TryGetValue(id,out var p)?Point(p):Point(P(0,0));
  public bool Special(string id)=>id!=null&&id.StartsWith("sector-");
  // Hired stock clerks and cleaners (CheckoutStaff) and the Staff Kit templates they and the incidents use.
  public CheckoutStaff Staff {get;private set;}
  public Transform StaffTemplate(string name)=>world?world.Find("Staff Kit/"+name):null;
  public void SaveInterior(){if(bridge&&Interior)bridge.Command("saveInteriorLayout","["+Interior.ExportJson()+"]");}
  // The map design ("Modo edição"): moved/hidden/added scene objects and the painted ground.
  public CheckoutDesignWorld Design {get;private set;}
  public CheckoutMarketLayout Layout=>layout;
  // Applies the last snapshot again (the map editor switched the stage it previews).
  public void Reapply(){if(state!=null)Apply(state);}
  public void Initialize(Transform root,CheckoutBridge owner){world=root;bridge=owner;Design=gameObject.AddComponent<CheckoutDesignWorld>();Design.Initialize(world);layout=gameObject.AddComponent<CheckoutMarketLayout>();layout.Initialize(world);Interior=gameObject.AddComponent<CheckoutInterior>();Interior.Initialize(world,layout,this);Lanes=gameObject.AddComponent<CheckoutLanes>();Lanes.Initialize(world,bridge.Queue,Interior);Stall=gameObject.AddComponent<CheckoutStall>();Stall.Initialize(world,this);
   if(Furnished){var sim=FindAnyObjectByType<MarketSimulation>();if(sim)sim.Furniture=()=>Interior.Obstacles().Concat(Design.Obstacles());}
   foreach(var old in world.GetComponentsInChildren<DepartmentTarget>())old.gameObject.SetActive(false);
   teal=Mat("2E8CAE");
   foreach(var pair in fixtures){markers[pair.Key]=Marker(pair.Key,Fixture(pair.Key)+Vector3.up*1.35f);Target(Fixture(pair.Key),new Vector3(1.4f,2,1.1f),"store",pair.Key);}
   events=gameObject.AddComponent<CheckoutEventVisuals>();events.Initialize();
   Staff=gameObject.AddComponent<CheckoutStaff>();Staff.Initialize(world,this);
   foreach(Transform t in world)if(t.name.StartsWith("Anim_Truck")){homes[t.name]=t.position;truckRotations[t.name]=t.rotation;t.gameObject.SetActive(false);}deliveryWorker=world.GetComponentInChildren<MarketDeliveryWorker>(true);
   Target(P(3,18),new Vector3(8,5,4),"suppliers");Target(P(-3.9f,-4.7f),new Vector3(3,2,1.7f),"checkout"); // The register opens the playable checkout.
  }
  // Timelapse building site when a paid expansion grows the shop or builds the central warehouse.
  void PlayConstruction(bool grow){var show=world.GetComponentInChildren<CheckoutStageConstruction>(true);if(!show)return;var dressing=world.GetComponentInChildren<CheckoutStageDressing>(true);
   var shell=world.GetComponentInChildren<CheckoutMarketShell>(true);var root=grow?(shell?shell.Walls:world.Find("Building")):world.Find(CheckoutMarketLayout.GrandWarehouse);if(!root)return;var shells=new List<Transform>();foreach(Transform child in root)if(child.GetComponentInChildren<Renderer>())shells.Add(child);
   var renderers=root.GetComponentsInChildren<Renderer>();if(renderers.Length==0)return;var bounds=renderers[0].bounds;foreach(var r in renderers)bounds.Encapsulate(r.bounds);
   if(grow)show.Play(shells,bounds,.74f,dressing?dressing.Title(layout.State.stage):"",dressing);else show.Play(shells,bounds,bounds.min.y,"ARMAZÉM CENTRAL",null);}
  // Live building site while a bought expansion is still under construction.
  CheckoutConstructionSite site;
  void UpdateConstructionSite(Snapshot next){var show=world.GetComponentInChildren<CheckoutStageConstruction>(true);if(!show)return;if(!site)site=show.GetComponent<CheckoutConstructionSite>();if(!site)site=show.gameObject.AddComponent<CheckoutConstructionSite>();
   var works=next.construction;if(works==null||string.IsNullOrEmpty(works.expansionId)||CheckoutMapEditor.Open){site.Hide();return;}
   // The ground inside the hoardings is cleared already: plaza pieces the finished expansion replaces go now.
   if(works.targetLayout!=null&&works.targetLayout.widthScale>0){var lots=world.GetComponentInChildren<CheckoutExpansionNeighborhood>(true);if(lots)lots.Apply(works.targetLayout);var dress=world.GetComponentInChildren<CheckoutStageDressing>(true);if(dress&&works.targetLayout.stage>layout.State.stage)dress.ClearForWorks(works.targetLayout.stage);}
   var plan=new CheckoutConstructionSite.Plan{startedAt=works.startedAt,endsAt=works.endsAt,skipCost=works.skipCost};
   Vector3 F(float x,float z)=>new Vector3(x,0,z);
   if(works.expansionId=="grand-warehouse"){
    // The central warehouse goes up on the old lot at the back of the block; trucks come in from the east street.
    var building=new Bounds(F(-8.15f,34.2f),F(15.6f,13));var min=building.min;var max=building.max;
    float x0=min.x-2.4f,x1=max.x+8f,z0=min.z-3.2f,z1=max.z+2.4f,zc=building.center.z;
    plan.id=works.expansionId;plan.groundY=plan.floorY=.13f;plan.walls=building;plan.wallHeights=new[]{6f,6f,6f,6f};plan.scaffold=new[]{true,true,false,false};
    plan.fences.AddRange(new[]{F(x0,z0),F(x1,z0),F(x1,z0),F(x1,zc-2.2f),F(x1,zc+2.2f),F(x1,z1),F(x1,z1),F(x0,z1),F(x0,z1),F(x0,z0)});
    plan.gateA=F(x1,zc-2.2f);plan.gateB=F(x1,zc+2.2f);plan.truckFrom=F(x1+12f,zc);plan.truckPark=F(x1+3.7f,zc);
    plan.site=new Bounds(F((x0+x1)*.5f,(z0+z1)*.5f),F(x1-x0,z1-z0));plan.work=new Bounds(F((max.x+x1)*.5f,zc),F(x1-max.x-1f,z1-z0-1f));plan.crewArea=new Bounds(building.center,F(building.size.x-2f,building.size.z-2f));plan.cranesInside=true;
    var derelict=world.Find(CheckoutMarketLayout.GrandWarehouseSite);if(derelict)derelict.gameObject.SetActive(false); // cleared for the works
    site.Show(plan);return;}
   // Shop growth: new walls go up east towards the street and north to the yard, around the open shop.
   var shell=world.GetComponentInChildren<CheckoutMarketShell>(true);var wallsRoot=shell?shell.Walls:world.Find("Building");var renderers=wallsRoot?wallsRoot.GetComponentsInChildren<Renderer>().Where(r=>r.enabled).ToArray():Array.Empty<Renderer>();if(renderers.Length==0){site.Hide();return;}
   var walls=renderers[0].bounds;foreach(var r in renderers)walls.Encapsulate(r.bounds);
   var target=works.targetLayout!=null&&works.targetLayout.widthScale>0?works.targetLayout:layout.State;
   Vector3 To(Vector3 p)=>CheckoutMarketLayout.Project(CheckoutMarketLayout.Unproject(p,layout.State),target);
   var grown=new Bounds(To(walls.min),Vector3.zero);grown.Encapsulate(To(walls.max));grown.Encapsulate(walls.min);grown.Encapsulate(walls.max);
   float front=walls.min.z,east=Mathf.Max(grown.max.x+1.8f,walls.max.x+3.4f),north=Mathf.Max(grown.max.z,walls.max.z)+2.8f,west=walls.min.x-.8f,runStart=walls.max.x+.6f;
   float gateMid=(runStart+east)*.5f,gateHalf=Mathf.Min(2.1f,(east-runStart)*.5f-.3f);
   plan.id=works.expansionId+":"+target.stage;plan.groundY=.15f;plan.floorY=.74f;
   plan.walls=new Bounds(F((grown.min.x+grown.max.x)*.5f,(grown.min.z+grown.max.z)*.5f),F(grown.size.x,grown.size.z));
   float tall=Mathf.Max(3f,walls.max.y-.74f);plan.wallHeights=new[]{0f,.75f,tall,0f};plan.scaffold=new[]{false,false,true,false};
   plan.fences.AddRange(new[]{F(runStart,front),F(gateMid-gateHalf,front),F(gateMid+gateHalf,front),F(east,front),F(east,front),F(east,north),F(east,north),F(west,north),F(west,north),F(west,walls.max.z+.6f)});
   plan.gateA=F(gateMid-gateHalf,front);plan.gateB=F(gateMid+gateHalf,front);plan.truckFrom=F(gateMid,front-13f);plan.truckPark=F(gateMid,front-3.6f);
   plan.site=new Bounds(F((west+east)*.5f,(front+north)*.5f),F(east-west,north-front));
   plan.work=new Bounds(F((walls.max.x+east)*.5f+.2f,(front+north)*.5f),F(Mathf.Max(1.6f,east-walls.max.x-.8f),north-front-1f));
   float cx0=walls.max.x+.5f,cx1=grown.max.x-.4f;if(cx1-cx0<1.2f){cx0=walls.max.x+.5f;cx1=east-.6f;}
   plan.crewArea=new Bounds(F((cx0+cx1)*.5f,(front+1f+grown.max.z-.6f)*.5f),F(cx1-cx0,grown.max.z-.6f-front-1f));
   site.Show(plan);}
  public void Apply(Snapshot next){bool editor=CheckoutMapEditor.Open;if(editor)next.layout=CheckoutMapDesign.LayoutFor(CheckoutMapEditor.Stage,CheckoutMapEditor.Warehouse);bool newSession=state==null||state.session!=next.session;bool animateSectors=!newSession; if(newSession)dispatchedDeliveryOrders.Clear();bool navigationChanged=state==null||!next.shelves.Select(s=>s.unlocked).SequenceEqual(state.shelves.Select(s=>s.unlocked))||!next.sectors.Select(s=>s.unlocked).SequenceEqual(state.sectors.Select(s=>s.unlocked));state=next;var previousLayout=layout.State;bool grow=!editor&&!newSession&&next.layout!=null&&next.layout.stage>previousLayout.stage;bool warehouseBuilt=!editor&&!newSession&&next.layout!=null&&next.layout.storageLarge&&!previousLayout.storageLarge;layout.holdNewDressing=grow;bool resized=layout.Apply(next.layout);if(layout.State.storageLarge!=grandBays){grandBays=layout.State.storageLarge;SwitchTruckBays(grandBays);}if(grow||warehouseBuilt)PlayConstruction(grow);
   if(resized)foreach(var actor in staff.Values){var home=homes[actor.name];var original=CheckoutMarketLayout.Unproject(home,previousLayout);homes[actor.name]=Point(original);actor.position=homes[actor.name];}world.GetComponentInChildren<CheckoutShelfSlots>()?.Apply(next.shelves);
   bool furnitureMoved=Furnished&&Interior.Apply(next);
   // A wing bought in this session: the pieces move to the map design made for the bigger shop.
   if(grow&&Furnished&&Interior.AdoptDesign())furnitureMoved=true;
   if(Furnished){foreach(var shelf in next.shelves)Interior.SetFill(Interior.Get(CheckoutInterior.ShelfKey(shelf.id)),shelf.unlocked&&shelf.capacity>0?(float)shelf.stock/shelf.capacity:0);foreach(var it in Interior.items.Values)if(it.type=="sector")Interior.SetFill(it,1);}
   foreach(var shelf in next.shelves){if(!markers.TryGetValue(shelf.id,out var marker))continue;
    marker.transform.position=MarkerPoint(shelf.id,1.35f);if(Furnished)marker.gameObject.SetActive(Piece(shelf.id)!=null&&!shelf.building);
    marker.Apply(shelf.unlocked,shelf.stock,shelf.capacity,false,shelf.requiredLevel);
    var pieces=world.Cast<Transform>().Where(t=>t.name.StartsWith("Stock_"+shelf.id+"_")).OrderBy(t=>t.name).ToArray();int visible=shelf.unlocked&&shelf.stock>0?Mathf.Max(1,Mathf.CeilToInt(pieces.Length*(float)shelf.stock/Mathf.Max(1,shelf.capacity))):0;
    for(int i=0;i<pieces.Length;i++)pieces[i].gameObject.SetActive(i<visible);
   }
   foreach(var sector in next.sectors){var root=world.Find("Sector_"+sector.id);var progress=world.Find("Sector Construction/"+sector.id)?.GetComponent<CheckoutSectorProgress>();bool present=layout.HasSector(sector.id);bool available=present&&sector.unlocked;if(root&&!progress)root.gameObject.SetActive(available);
    var position=SectorPosition("sector-"+sector.id);
    string key="sector-"+sector.id;if(!markers.ContainsKey(key)){markers[key]=Marker(key,position+Vector3.up*1.65f);Target(position,new Vector3(1.3f,2,1.1f),"sectors","",sector.id);}
    markers[key].gameObject.SetActive(present&&!sector.building&&(!Furnished||Piece(key)!=null));markers[key].transform.position=MarkerPoint(key,1.65f);markers[key].Apply(available,sector.jobs,1,true,sector.requiredLevel);
    if(sector.id=="queijaria"&&available&&!world.Find("Worker_Cheesemaker")){var template=world.Find("Worker_Baker");if(template){var cheesemaker=Instantiate(template,world);cheesemaker.name="Worker_Cheesemaker";var display=root?root.GetComponentsInChildren<Renderer>().FirstOrDefault(r=>r.enabled):null;cheesemaker.position=display?P(display.bounds.center.x,display.bounds.center.z+display.bounds.size.z*.12f):P(-3.8f,4.5f);cheesemaker.rotation=Quaternion.identity;}}
    string worker=sector.id=="padaria"?"Worker_Baker":sector.id=="queijaria"?"Worker_Cheesemaker":sector.id=="acougue"?"Worker_Butcher":sector.id=="peixaria"?"Worker_Fishmonger":"";var actor=string.IsNullOrEmpty(worker)?null:world.Find(worker);
    if(Furnished){ // Counters are furniture now: the worker stands behind wherever it was placed.
     if(progress)progress.gameObject.SetActive(false);if(root)root.gameObject.SetActive(available);
     var counter=Piece(key);if(actor){actor.gameObject.SetActive(available&&counter!=null);
      if(counter!=null&&counter.piece.staffed){var spot=Interior.StaffPoint(counter);if(!staffSpots.TryGetValue(actor.name,out var last)||(last-spot).sqrMagnitude>.0001f){staffSpots[actor.name]=spot;actor.SetPositionAndRotation(spot,counter.root.rotation);}
       var walk=actor.GetComponent<CheckoutSectorWorker>();if(!walk)walk=actor.gameObject.AddComponent<CheckoutSectorWorker>();walk.span=.8f;walk.frame=counter.root;}}
     continue;}if(actor&&!actor.GetComponent<CheckoutSectorWorker>())actor.gameObject.AddComponent<CheckoutSectorWorker>().span=sector.id=="padaria"?.3f:sector.id=="peixaria"?.6f:sector.id=="acougue"?.4f:.5f;if(progress){progress.gameObject.SetActive(true);progress.Apply(available,animateSectors&&!resized);if(!present){/* Sectors from expansions not bought yet still show their building site. */if(progress.construction)progress.construction.gameObject.SetActive(true);progress.finished.gameObject.SetActive(false);if(progress.worker)progress.worker.gameObject.SetActive(false);}}else if(actor)actor.gameObject.SetActive(available);
   }
   // Stock clerks and cleaners are played by CheckoutStaff from the app's task timeline.
   Staff.Apply(next);
   foreach(string id in next.ownedItems)if(id!=CheckoutLanes.ExtraItem&&id!=CheckoutLanes.SelfItem&&!decorations.ContainsKey("shop-"+id)){int i=decorations.Keys.Count(k=>k.StartsWith("shop-"));var item=Box("Upgrade "+id,new Vector3(-8.2f,1.25f,3.6f-i*.45f),new Vector3(.32f,.6f,.32f),teal);decorations["shop-"+id]=item;}
   foreach(var pair in decorations.Where(p=>p.Key.StartsWith("shop-")))pair.Value.SetActive(next.ownedItems.Contains(pair.Key.Substring(5)));
   foreach(var pair in targets){var target=pair.Key.GetComponent<CheckoutTarget>();if(Furnished&&(target.panel=="store"||target.panel=="sectors"||target.panel=="checkout")){pair.Key.gameObject.SetActive(false);continue;}if(!string.IsNullOrEmpty(target.sectorId)){pair.Key.gameObject.SetActive(layout.HasSector(target.sectorId));pair.Key.position=SectorPosition("sector-"+target.sectorId);}else if(pair.Value.z<8&&Mathf.Abs(pair.Value.x)<10)pair.Key.position=target.panel=="checkout"?CheckoutPoint(pair.Value):Point(pair.Value);}
   if(Lanes.Apply(next.ownedItems))navigationChanged=true;Lanes.Rebase(layout.State);
   // The register is the player's until a cashier is hired: the operator only stands there while one works
   // (the second checkout needs a second cashier).
   int cashiers=next.employees?.Count(e=>e.role=="cashier"&&e.isWorking)??0;
   var mainCashier=world.Find("Worker_Cashier");if(mainCashier)mainCashier.gameObject.SetActive(next.isOpen&&cashiers>0);
   var extraCashier=world.Find("Worker_Cashier 2");if(extraCashier)extraCashier.gameObject.SetActive(next.isOpen&&cashiers>1&&next.ownedItems!=null&&next.ownedItems.Contains(CheckoutLanes.ExtraItem));
   if(Furnished&&(furnitureMoved||resized||newSession||staff.Count!=placedClerks))PlaceClerks();
   if(resized||navigationChanged||furnitureMoved){FindAnyObjectByType<MarketSimulation>().RebuildLayoutNavigation(layout.State);foreach(var walker in FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include)){walker.RebaseLayout(previousLayout,layout.State);if(furnitureMoved)walker.FurnitureMoved();}}
   events.Apply(next.@event);
   // Night turn (Späti on): the city goes dark and the street lights come on while it is open.
   events.SetNight(next.day!=null&&next.day.shift=="noite"&&next.day.phase=="open");
   // Closed shop: nobody works inside (the unloader outside keeps his own shift).
   if(!next.isOpen)foreach(Transform t in world)if((t.name.StartsWith("Worker_")&&t.name!="Worker_Delivery")||t.name.StartsWith("Employee_"))t.gameObject.SetActive(false);
   UpdateConstructionSite(next);
   // Moved, hidden and added scene objects plus the painted ground of this stage (the editor drives its own).
   if(!editor&&Design.Sync(layout.State.stage)&&Furnished)FurnitureChanged();
   // Eras 0-4 sell from a stall: the building and everything inside it hide (last, so nothing above turns it back on).
   Stall.Apply(next);
  }
  // Stock clerks and cleaners work in front of the shelves wherever those stand.
  // Build mode moved furniture: staff follow at once; `navigation` also rebuilds the walkable floor.
  public void FurnitureChanged(bool navigation=true){if(!Furnished)return;staffSpots.Clear();Lanes.Rebase(layout.State);PlaceClerks();
   if(state!=null)foreach(var sector in state.sectors){var actor=world.Find(sector.id=="padaria"?"Worker_Baker":sector.id=="queijaria"?"Worker_Cheesemaker":sector.id=="acougue"?"Worker_Butcher":sector.id=="peixaria"?"Worker_Fishmonger":"-");var counter=Piece("sector-"+sector.id);
    if(actor&&counter!=null&&counter.piece.staffed){var spot=Interior.StaffPoint(counter);staffSpots[actor.name]=spot;actor.SetPositionAndRotation(spot,counter.root.rotation);}}
   if(!navigation)return;FindAnyObjectByType<MarketSimulation>().RebuildLayoutNavigation(layout.State);foreach(var walker in FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include)){walker.RebaseLayout(layout.State,layout.State);walker.FurnitureMoved();}}
  int placedClerks=-1;
  void PlaceClerks(){placedClerks=staff.Count;int n=0;foreach(var pair in staff.OrderBy(p=>p.Key)){var actor=pair.Value;if(!Interior.ClerkSpot(n++,out var spot,out var axis))continue;homes[actor.name]=spot;axes[actor.name]=axis;actor.position=spot;}}
  public float ScanCustomer(Customer customer,CheckoutLane lane=null){int items=customer.purchases?.Sum(p=>p.quantity)??1;if(lane!=null&&lane.kiosk)return lane.kiosk.Serve(items);
   var cashier=lane!=null&&lane.cashier?lane.cashier:world.Find("Worker_Cashier").GetComponent<CheckoutCashier>();if(!cashier)return 2f;cashier.Serve(items);return cashier.ScanDuration;}
  public float PaymentDuration=>world.Find("Worker_Cashier").GetComponent<CheckoutCashier>()?.PaymentDuration??2f;
  public float ServeCustomer(Customer customer){var cashier=world.Find("Worker_Cashier").GetComponent<CheckoutCashier>();return cashier?cashier.Serve(customer.purchases?.Sum(p=>p.quantity)??1):2f;}
  void Update(){if(state==null)return;workClock+=Time.deltaTime;
   foreach(var sector in state.sectors)if(sector.unlocked&&sector.jobs>0&&Mathf.FloorToInt(workClock)!=Mathf.FloorToInt(workClock-Time.deltaTime)&&Mathf.FloorToInt(workClock)%3==0){string name=sector.id=="padaria"?"Worker_Baker":sector.id=="queijaria"?"Worker_Cheesemaker":sector.id=="acougue"?"Worker_Butcher":sector.id=="peixaria"?"Worker_Fishmonger":"";var worker=string.IsNullOrEmpty(name)?null:world.Find(name);if(worker&&worker.gameObject.activeSelf)worker.GetComponent<MarketCharacterAnimator>()?.Perform("BuyAtSpecialSector");}
   if(!CheckoutStall.Small)UpdateSupplierDeliveries();
  }
  void UpdateSupplierDeliveries(){var claimed=new HashSet<Transform>();var docked=new HashSet<string>((state.dock??System.Array.Empty<DockEntry>()).Select(d=>d.id));foreach(var order in state.orders.Where(order=>order.status=="em-transporte"||docked.Contains("entrega-"+order.id)).OrderBy(order=>order.createdAt)){var truck=TruckFor(order,claimed);if(!truck||!homes.TryGetValue(truck.name,out var home))continue;claimed.Add(truck);if(!truck.gameObject.activeSelf){truck.position=home+truck.forward*9f;truck.rotation=truckRotations[truck.name];truck.gameObject.SetActive(true);}
   truck.rotation=Quaternion.RotateTowards(truck.rotation,truckRotations[truck.name],Time.deltaTime*180);truck.position=Vector3.MoveTowards(truck.position,home,Time.deltaTime*3.25f);
   if(Vector3.Distance(truck.position,home)<.04f&&dispatchedDeliveryOrders.Add(order.id))deliveryWorker?.QueueDelivery(truck,home,order.createdAt+order.deliveryDurationMs);
   DockClick(truck,docked.Contains("entrega-"+order.id)&&Vector3.Distance(truck.position,home)<.1f);
  }
   foreach(var pair in homes){var truck=world.Find(pair.Key);if(!truck||claimed.Contains(truck)||(deliveryWorker&&deliveryWorker.HasDeliveryFor(truck)))continue;truck.gameObject.SetActive(false);}
  }
  // A truck parked with goods still to unload can be clicked to open the unloading mini-game.
  static void DockClick(Transform truck,bool on){
   var click=truck.Find("DockClick");
   if(on&&!click){var go=new GameObject("DockClick");go.transform.SetParent(truck,false);var box=go.AddComponent<BoxCollider>();var s=truck.lossyScale;box.size=new Vector3(3.2f/Mathf.Max(.01f,s.x),3.4f/Mathf.Max(.01f,s.y),7f/Mathf.Max(.01f,s.z));box.center=new Vector3(0,box.size.y*.5f,0);go.AddComponent<CheckoutTarget>().panel="dock";click=go.transform;}
   if(click)click.gameObject.SetActive(on);
  }
  // With the central warehouse bought the trucks park in its yard (bays placed by the Central Park builder).
  bool grandBays;readonly Dictionary<string,Vector3> baseTruckHomes=new Dictionary<string,Vector3>();readonly Dictionary<string,Quaternion> baseTruckRotations=new Dictionary<string,Quaternion>();
  void SwitchTruckBays(bool grand){foreach(var name in truckRotations.Keys.ToArray()){if(!baseTruckHomes.ContainsKey(name)){baseTruckHomes[name]=homes[name];baseTruckRotations[name]=truckRotations[name];}var bay=grand?world.Find(CheckoutMarketLayout.GrandYard+"/Bays/"+name):null;
   // The bay markers were saved with the truck's pivot height doubled (trucks floated 1.4 m up): keep the truck's own
   // height on the yard and back it up to a hand's width from the dock shelter.
   homes[name]=bay?new Vector3(bay.position.x+.2f,baseTruckHomes[name].y,bay.position.z):baseTruckHomes[name];truckRotations[name]=bay?bay.rotation:baseTruckRotations[name];var truck=world.Find(name);if(truck&&!truck.gameObject.activeSelf){truck.position=homes[name];truck.rotation=truckRotations[name];}}}
  Transform TruckFor(Order order,HashSet<Transform> claimed){string name=order.productCategory=="peixes"?"Anim_Truck_8":order.productCategory=="congelados"?"Anim_Truck_11":"Anim_Truck_5";var truck=world.Find(name);return truck&&!claimed.Contains(truck)?truck:null;}
  void OnDestroy(){markerArt.Dispose();if(teal)Destroy(teal);}
  Material Mat(string hex){var mat=new Material(Shader.Find("Standard"));mat.color=MarketSimulation.C(hex);mat.SetFloat("_Glossiness",0);return mat;}
  GameObject Box(string name,Vector3 p,Vector3 size,Material mat){var o=GameObject.CreatePrimitive(PrimitiveType.Cube);o.name=name;o.transform.SetParent(transform);o.transform.position=p;o.transform.localScale=size;o.GetComponent<Renderer>().material=mat;return o;}
  CheckoutStatusMarker Marker(string id,Vector3 p){var go=new GameObject("Status "+id);go.transform.SetParent(transform);go.transform.position=p;var marker=go.AddComponent<CheckoutStatusMarker>();marker.Initialize(markerArt);return marker;}
  void Target(Vector3 p,Vector3 size,string panel,string shelfId="",string sectorId=""){var go=new GameObject("Open "+panel);go.transform.SetParent(transform);go.transform.position=p;go.AddComponent<BoxCollider>().size=size;var target=go.AddComponent<CheckoutTarget>();target.panel=panel;target.shelfId=shelfId;target.sectorId=sectorId;targets[go.transform]=p;}
 }
}
