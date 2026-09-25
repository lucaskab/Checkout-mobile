using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using MarketDay;
namespace Checkout {
 public class CheckoutMap:MonoBehaviour {
  Transform world;CheckoutBridge bridge;readonly Dictionary<string,CheckoutStatusMarker> markers=new Dictionary<string,CheckoutStatusMarker>();readonly CheckoutEventAssets markerArt=new CheckoutEventAssets();readonly Dictionary<string,Transform> staff=new Dictionary<string,Transform>();readonly Dictionary<string,GameObject> decorations=new Dictionary<string,GameObject>();readonly Dictionary<string,Vector3> homes=new Dictionary<string,Vector3>();readonly Dictionary<string,Quaternion> truckRotations=new Dictionary<string,Quaternion>();readonly HashSet<string> dispatchedDeliveryOrders=new HashSet<string>();MarketDeliveryWorker deliveryWorker;
  readonly Dictionary<string,Vector3> fixtures=new Dictionary<string,Vector3>{{"produce",P(6.55f,.45f)},{"dairy",P(-6.4f,-1.6f)},{"bakery",P(-6.45f,1.05f)},{"snacks",P(-1.6f,.3f)},{"drinks",P(2,-1.18f)},{"coffee",P(-2.2f,6.37f)},{"pizza",P(4.85f,-5.36f)}};
  readonly Dictionary<string,Vector3> approaches=new Dictionary<string,Vector3>{{"produce",P(5.1f,-1.2f)},{"dairy",P(-4,-1.6f)},{"bakery",P(-3.8f,2.55f)},{"snacks",P(-.18f,.5f)},{"drinks",P(3.3f,-1.2f)},{"coffee",P(-2f,5.1f)},{"pizza",P(4.85f,-3.85f)}};
  CheckoutMarketLayout layout;readonly Dictionary<Transform,Vector3> targets=new Dictionary<Transform,Vector3>();
  public Vector3 Point(Vector3 point)=>layout?layout.Point(point):point;
  public Vector3 Entrance=>Point(P(-1.75f,-8.7f));
  public Vector3 CheckoutPoint(Vector3 point)=>layout?CheckoutMarketLayout.CheckoutPoint(point,layout.State):point;
  public Vector3 Register=>CheckoutPoint(MarketSimulation.Register);
  public CheckoutLanes Lanes {get;private set;}
  public Vector3 LaneRegister(CheckoutLane lane)=>lane==null||lane.places==null?Register:Point(lane.register);
  public bool HasParking=>layout&&layout.State.parking;
  CheckoutEventVisuals events;float workClock;Snapshot state;Material teal;
  static Vector3 P(float x,float z)=>new Vector3(x,.74f,z);
  Bounds SectorBounds(string id){var root=world.Find("Sector_"+id.Substring(7));var renderers=root?root.GetComponentsInChildren<Renderer>(true).Where(r=>r.enabled).ToArray():Array.Empty<Renderer>();if(renderers.Length==0)return new Bounds(P(0,4.3f),Vector3.one);var bounds=renderers[0].bounds;foreach(var renderer in renderers.Skip(1))bounds.Encapsulate(renderer.bounds);return bounds;}
  Vector3 SectorPosition(string id){var bounds=SectorBounds(id);return P(bounds.center.x,bounds.center.z);}
  Vector3 SectorApproach(string id){var bounds=SectorBounds(id);return P(bounds.center.x,bounds.min.z-.65f);}
  public Vector3 Fixture(string id)=>Special(id)?SectorPosition(id):world&&world.GetComponentInChildren<CheckoutShelfSlots>()?Point(CheckoutShelfSlots.Position(id)):fixtures.TryGetValue(id,out var p)?Point(p):Point(P(0,0));
  public Vector3 Approach(string id)=>Special(id)?SectorApproach(id):world&&world.GetComponentInChildren<CheckoutShelfSlots>()?Point(CheckoutShelfSlots.Position(id))+Vector3.back*(.7f*layout.State.depthScale+.55f):approaches.TryGetValue(id,out var p)?Point(p):Point(P(0,0));
  public bool Special(string id)=>id!=null&&id.StartsWith("sector-");
  public void Initialize(Transform root,CheckoutBridge owner){world=root;bridge=owner;layout=gameObject.AddComponent<CheckoutMarketLayout>();layout.Initialize(world);Lanes=gameObject.AddComponent<CheckoutLanes>();Lanes.Initialize(world,bridge.Queue);
   foreach(var old in world.GetComponentsInChildren<DepartmentTarget>())old.gameObject.SetActive(false);
   teal=Mat("2E8CAE");
   foreach(var pair in fixtures){markers[pair.Key]=Marker(pair.Key,Fixture(pair.Key)+Vector3.up*1.35f);Target(Fixture(pair.Key),new Vector3(1.4f,2,1.1f),"store",pair.Key);}
   events=gameObject.AddComponent<CheckoutEventVisuals>();events.Initialize();
   foreach(Transform t in world)if(t.name.StartsWith("Anim_Truck")){homes[t.name]=t.position;truckRotations[t.name]=t.rotation;t.gameObject.SetActive(false);}deliveryWorker=world.GetComponentInChildren<MarketDeliveryWorker>(true);
   Target(P(3,18),new Vector3(8,5,4),"suppliers");Target(P(-3.9f,-4.7f),new Vector3(3,2,1.7f),"team");
  }
  public void Apply(Snapshot next){bool newSession=state==null||state.session!=next.session;bool animateSectors=!newSession; if(newSession)dispatchedDeliveryOrders.Clear();bool navigationChanged=state==null||!next.shelves.Select(s=>s.unlocked).SequenceEqual(state.shelves.Select(s=>s.unlocked))||!next.sectors.Select(s=>s.unlocked).SequenceEqual(state.sectors.Select(s=>s.unlocked));state=next;var previousLayout=layout.State;bool resized=layout.Apply(next.layout);
   if(resized)foreach(var actor in staff.Values){var home=homes[actor.name];var original=CheckoutMarketLayout.Anchor+Vector3.Scale(home-CheckoutMarketLayout.Anchor,new Vector3(1/previousLayout.widthScale,1,1/previousLayout.depthScale));homes[actor.name]=Point(original);actor.position=homes[actor.name];}world.GetComponentInChildren<CheckoutShelfSlots>()?.Apply(next.shelves);
   foreach(var shelf in next.shelves){if(!markers.TryGetValue(shelf.id,out var marker))continue;
    marker.transform.position=Fixture(shelf.id)+Vector3.up*1.35f;
    marker.Apply(shelf.unlocked,shelf.stock,shelf.capacity,false,shelf.requiredLevel);
    var pieces=world.Cast<Transform>().Where(t=>t.name.StartsWith("Stock_"+shelf.id+"_")).OrderBy(t=>t.name).ToArray();int visible=shelf.unlocked&&shelf.stock>0?Mathf.Max(1,Mathf.CeilToInt(pieces.Length*(float)shelf.stock/Mathf.Max(1,shelf.capacity))):0;
    for(int i=0;i<pieces.Length;i++)pieces[i].gameObject.SetActive(i<visible);
   }
   foreach(var sector in next.sectors){var root=world.Find("Sector_"+sector.id);var progress=world.Find("Sector Construction/"+sector.id)?.GetComponent<CheckoutSectorProgress>();bool present=layout.HasSector(sector.id);bool available=present&&sector.unlocked;if(root&&!progress)root.gameObject.SetActive(available);
    var position=SectorPosition("sector-"+sector.id);
    string key="sector-"+sector.id;if(!markers.ContainsKey(key)){markers[key]=Marker(key,position+Vector3.up*1.65f);Target(position,new Vector3(1.3f,2,1.1f),"sectors","",sector.id);}
    markers[key].gameObject.SetActive(present);markers[key].transform.position=SectorPosition(key)+Vector3.up*1.65f;markers[key].Apply(available,sector.jobs,1,true,sector.requiredLevel);
    if(sector.id=="queijaria"&&available&&!world.Find("Worker_Cheesemaker")){var template=world.Find("Worker_Baker");if(template){var cheesemaker=Instantiate(template,world);cheesemaker.name="Worker_Cheesemaker";var display=root?root.GetComponentsInChildren<Renderer>().FirstOrDefault(r=>r.enabled):null;cheesemaker.position=display?P(display.bounds.center.x,display.bounds.center.z+display.bounds.size.z*.12f):P(-3.8f,4.5f);cheesemaker.rotation=Quaternion.identity;}}
    string worker=sector.id=="padaria"?"Worker_Baker":sector.id=="queijaria"?"Worker_Cheesemaker":sector.id=="acougue"?"Worker_Butcher":sector.id=="peixaria"?"Worker_Fishmonger":"";var actor=string.IsNullOrEmpty(worker)?null:world.Find(worker);if(actor&&!actor.GetComponent<CheckoutSectorWorker>())actor.gameObject.AddComponent<CheckoutSectorWorker>().span=sector.id=="padaria"?.3f:sector.id=="peixaria"?.6f:sector.id=="acougue"?.4f:.5f;if(progress){progress.gameObject.SetActive(present);progress.Apply(available,animateSectors&&!resized);if(!present){progress.construction.gameObject.SetActive(false);progress.finished.gameObject.SetActive(false);if(progress.worker)progress.worker.gameObject.SetActive(false);}}else if(actor)actor.gameObject.SetActive(available);
   }
   var baseCashier=world.Find("Worker_Cashier");if(baseCashier)baseCashier.gameObject.SetActive(true); // The player runs checkout before hiring.
   foreach(var employee in next.employees){if(employee.role=="cashier")continue;if(!staff.TryGetValue(employee.id,out var actor)){
     Transform template=world.Find(employee.role=="cashier"?"Worker_Cashier":"StockWorker_0");if(!template)continue;actor=Instantiate(template,world);actor.name="Employee_"+employee.id;var oldAgent=actor.GetComponent<UnityEngine.AI.NavMeshAgent>();if(oldAgent)Destroy(oldAgent);staff[employee.id]=actor;
     float n=staff.Count;actor.position=Point(employee.role=="cashier"?P(-5.5f,-4):P(3.8f,2.3f+n*.65f));if(employee.role=="cleaner"){var broom=markerArt.Group(actor,"Cleaner broom",new Vector3(.48f,.12f,-.08f));markerArt.Bar(broom,new Vector3(0,0,0),new Vector3(0,1.15f,0),.055f,"936545");markerArt.Part(broom,"Broom head",new Vector3(0,.02f,0),new Vector3(.42f,.16f,.18f),"E9A52E");}homes[actor.name]=actor.position;Target(actor.position,new Vector3(.7f,2,.7f),"team");
    }actor.gameObject.SetActive(employee.isWorking);
   }
   foreach(var pair in staff)if(!next.employees.Any(e=>e.id==pair.Key&&e.isWorking))pair.Value.gameObject.SetActive(false);
   foreach(string id in next.ownedItems)if(id!=CheckoutLanes.ExtraItem&&id!=CheckoutLanes.SelfItem&&!decorations.ContainsKey("shop-"+id)){int i=decorations.Keys.Count(k=>k.StartsWith("shop-"));var item=Box("Upgrade "+id,new Vector3(-8.2f,1.25f,3.6f-i*.45f),new Vector3(.32f,.6f,.32f),teal);decorations["shop-"+id]=item;}
   foreach(var pair in decorations.Where(p=>p.Key.StartsWith("shop-")))pair.Value.SetActive(next.ownedItems.Contains(pair.Key.Substring(5)));
   foreach(var pair in targets){var target=pair.Key.GetComponent<CheckoutTarget>();if(!string.IsNullOrEmpty(target.sectorId)){pair.Key.gameObject.SetActive(layout.HasSector(target.sectorId));pair.Key.position=SectorPosition("sector-"+target.sectorId);}else if(pair.Value.z<8&&Mathf.Abs(pair.Value.x)<10)pair.Key.position=target.panel=="team"&&pair.Value==P(-3.9f,-4.7f)?CheckoutPoint(pair.Value):Point(pair.Value);}
   if(Lanes.Apply(next.ownedItems))navigationChanged=true;Lanes.Rebase(layout.State);
   if(resized||navigationChanged){FindAnyObjectByType<MarketSimulation>().RebuildLayoutNavigation(layout.State);foreach(var walker in FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include))walker.RebaseLayout(previousLayout,layout.State);}
   events.Apply(next.@event);
  }
  public float ScanCustomer(Customer customer,CheckoutLane lane=null){int items=customer.purchases?.Sum(p=>p.quantity)??1;if(lane!=null&&lane.kiosk)return lane.kiosk.Serve(items);
   var cashier=lane!=null&&lane.cashier?lane.cashier:world.Find("Worker_Cashier").GetComponent<CheckoutCashier>();if(!cashier)return 2f;cashier.Serve(items);return cashier.ScanDuration;}
  public float PaymentDuration=>world.Find("Worker_Cashier").GetComponent<CheckoutCashier>()?.PaymentDuration??2f;
  public float ServeCustomer(Customer customer){var cashier=world.Find("Worker_Cashier").GetComponent<CheckoutCashier>();return cashier?cashier.Serve(customer.purchases?.Sum(p=>p.quantity)??1):2f;}
  void Update(){if(state==null)return;workClock+=Time.deltaTime;
   foreach(var employee in state.employees)if(employee.isWorking&&staff.TryGetValue(employee.id,out var actor)&&employee.role!="cashier"){
    // Walk to one end, stop and work for a moment, turn in place, then walk back. All staff share
    // the clock so the stacked helpers keep their spacing.
    var home=homes[actor.name];float walk=2.4f/Mathf.Max(.3f,employee.efficiency),pause=1.6f,t=Mathf.Repeat(workClock,2*(walk+pause));
    float side=t<walk+pause?1:-1,local=t<walk+pause?t:t-walk-pause,s=local<walk?Mathf.SmoothStep(-1,1,local/walk)*side:side;
    var target=home+Vector3.forward*s*.55f;var direction=target-actor.position;
    var heading=direction.sqrMagnitude>.000001f?direction:local>walk+pause-.6f?Vector3.forward*-side:Vector3.zero;
    if(heading!=Vector3.zero)actor.rotation=Quaternion.RotateTowards(actor.rotation,Quaternion.LookRotation(-heading),Time.deltaTime*320);actor.position=target;
   }
   foreach(var sector in state.sectors)if(sector.unlocked&&sector.jobs>0&&Mathf.FloorToInt(workClock)!=Mathf.FloorToInt(workClock-Time.deltaTime)&&Mathf.FloorToInt(workClock)%3==0){string name=sector.id=="padaria"?"Worker_Baker":sector.id=="queijaria"?"Worker_Cheesemaker":sector.id=="acougue"?"Worker_Butcher":sector.id=="peixaria"?"Worker_Fishmonger":"";var worker=string.IsNullOrEmpty(name)?null:world.Find(name);if(worker&&worker.gameObject.activeSelf)worker.GetComponent<MarketCharacterAnimator>()?.Perform("BuyAtSpecialSector");}
   UpdateSupplierDeliveries();
  }
  void UpdateSupplierDeliveries(){var claimed=new HashSet<Transform>();foreach(var order in state.orders.Where(order=>order.status=="em-transporte").OrderBy(order=>order.createdAt)){var truck=TruckFor(order,claimed);if(!truck||!homes.TryGetValue(truck.name,out var home))continue;claimed.Add(truck);if(!truck.gameObject.activeSelf){truck.position=home+truck.forward*9f;truck.rotation=truckRotations[truck.name];truck.gameObject.SetActive(true);}
   truck.rotation=Quaternion.RotateTowards(truck.rotation,truckRotations[truck.name],Time.deltaTime*180);truck.position=Vector3.MoveTowards(truck.position,home,Time.deltaTime*3.25f);
   if(Vector3.Distance(truck.position,home)<.04f&&dispatchedDeliveryOrders.Add(order.id))deliveryWorker?.QueueDelivery(truck,home,order.createdAt+order.deliveryDurationMs);
  }
   foreach(var pair in homes){var truck=world.Find(pair.Key);if(!truck||claimed.Contains(truck)||(deliveryWorker&&deliveryWorker.HasDeliveryFor(truck)))continue;truck.gameObject.SetActive(false);}
  }
  Transform TruckFor(Order order,HashSet<Transform> claimed){string name=order.productCategory=="peixes"?"Anim_Truck_8":order.productCategory=="congelados"?"Anim_Truck_11":"Anim_Truck_5";var truck=world.Find(name);return truck&&!claimed.Contains(truck)?truck:null;}
  void OnDestroy(){markerArt.Dispose();if(teal)Destroy(teal);}
  Material Mat(string hex){var mat=new Material(Shader.Find("Standard"));mat.color=MarketSimulation.C(hex);mat.SetFloat("_Glossiness",0);return mat;}
  GameObject Box(string name,Vector3 p,Vector3 size,Material mat){var o=GameObject.CreatePrimitive(PrimitiveType.Cube);o.name=name;o.transform.SetParent(transform);o.transform.position=p;o.transform.localScale=size;o.GetComponent<Renderer>().material=mat;return o;}
  CheckoutStatusMarker Marker(string id,Vector3 p){var go=new GameObject("Status "+id);go.transform.SetParent(transform);go.transform.position=p;var marker=go.AddComponent<CheckoutStatusMarker>();marker.Initialize(markerArt);return marker;}
  void Target(Vector3 p,Vector3 size,string panel,string shelfId="",string sectorId=""){var go=new GameObject("Open "+panel);go.transform.SetParent(transform);go.transform.position=p;go.AddComponent<BoxCollider>().size=size;var target=go.AddComponent<CheckoutTarget>();target.panel=panel;target.shelfId=shelfId;target.sectorId=sectorId;targets[go.transform]=p;}
 }
}
