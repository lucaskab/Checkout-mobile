using System;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Rede: the fleet's yard on the plaza north of the distribution centre and the fleet's trucks on the map.
 // Lucas 06/11: "eu gostei da localização do 1", "coloque no jogo"; v2: "aumente o estacionamento ... quase até o final do
 // mapa", "uma entrada e uma saída", "apareçam ali do final do mapa e não simplesmente da calçada"; v3: "os caminhões
 // têm que andar por toda a cidade ... integração com o centro de distribuição ... uma animação ali também de carregando
 // os caminhões", and the parked trucks must not vanish.
 // The model (Resources/Rede/RedeFleetYard, scripts/blender/rede_yard.py) stands at Origin with the diesel island; it is a
 // one-way loop (entrance at the north end, bays in the middle, exit at the south end). What each truck does follows its
 // job (snapshot chain.trucks: job, phase indo / voltando / patio, departAt / returnAt):
 //  * at the depot ("patio") it waits in its bay; parked trucks stay put whatever the others do;
 //  * contract / branch run: out of the exit, down the east street to the distribution centre, through the gate, backs
 //    onto a free dock, the loaders carry boxes into it (CheckoutRedeLoading), then out of the gate, down the street and
 //    east along the avenue across the city into the fog; it comes back along the avenue from the east, up the east
 //    street to the yard's entrance, refuels and parks (it sets off ReturnLead before its trip ends);
 //  * supplying the centre ("abastecer"): out of the exit and north to the supplier; the goods come back in the same
 //    truck, which backs onto a dock and is unloaded (CheckoutDeliveryTrucks + the delivery worker); once unloaded it
 //    drives from the dock up the street into the yard (TakeOver), refuels and parks;
 //  * if the game missed a part (the app was closed), the truck simply comes home from the north end of the map.
 // A truck on the move finishes what it is doing before it obeys a new phase; it waits for cars, people, other trucks
 // (registered with CheckoutEventTraffic, so the city's cars and the suppliers' trucks wait for it too) and junctions.
 // With the yard the map grows north (the edge fog, the camera's pan, the cars' turning points) and whatever stood on
 // its footprint (the plaza's planters, the horizon's houses) hides.
 public sealed class CheckoutRedeYard:MonoBehaviour {
  public static readonly Vector3 Origin=new Vector3(2f,0f,55.6f);
  /// <summary>The chain's trucks in the game (yard and docks): in proportion to the streets and the yard.</summary>
  public const float FleetScale=.75f;
  /// <summary>Centre to tail of a fleet truck at FleetScale (the Blender truck runs from −3.3 to +3.2, nose at −).</summary>
  public const float TailOffset=3.2f*FleetScale,NoseOffset=3.3f*FleetScale;
  const float Top=.17f,Road=.15f;
  // model space (rede_yard.py)
  static readonly float[] Bays={-15f,-11.7f,-8.4f,-5.1f,-1.8f,1.5f,4.8f};
  const float TruckY=4.4f,LaneIn=11.2f,LaneOut=-2.3f;
  // the truck at the pump stops with its side tank (behind the cab) by the pumps
  static readonly Vector2 PumpStop=new Vector2(11.2f,LaneIn),Pump=new Vector2(9.5f,13.9f);
  // streets (world, CheckoutStreetLayout / CheckoutNeighborhoodTraffic): the east street's lanes, the avenue's lanes,
  // how far out a truck comes from / goes to (deep in the edge fog)
  const float EastSouth=22.4f,EastNorth=24.6f,AvenueWest=-17f,AvenueEast=-20f,FarEast=64f,FarNorth=95.6f;
  // the distribution centre's yard: its driveway from the east street (CheckoutDeliveryTrucks' grand yard)
  const float GateZ=33.4f,PastGateZ=29.2f;
  const float RefuelSeconds=9f,LoadSeconds=24f,ReturnLead=30000;

  Transform world,yard,fuel;
  readonly List<Renderer> hidden=new List<Renderer>();
  /// <summary>QA: what the yard did last.</summary>
  public static string Report{get;private set;}="";
  public static CheckoutRedeYard Current{get;private set;}

  enum Mode{Away,Parked,Driving,Refuelling,Loading}
  sealed class Truck{
   public string id,kind,phase,job,lastJob;public double departAt,arriveAt,returnAt,doneDepart=-1;
   public Transform model;public Bounds box;public Mode mode;public int bay,dock=-1;
   public readonly List<CheckoutVehiclePath> runs=new List<CheckoutVehiclePath>();public readonly List<bool> runBack=new List<bool>();
   public int runCount,run;public float s,speed,since,timer;public bool hiddenStart,held,qaStay;
   public Action done;public string route="";
  }
  readonly Dictionary<string,Truck> trucks=new Dictionary<string,Truck>();
  readonly CheckoutRedeLoading loading=new CheckoutRedeLoading();

  static Vector3 W(float x,float y)=>Origin+new Vector3(x,Top,y);
  static Vector3 V(float x,float z)=>new Vector3(x,Road,z);

  public static CheckoutRedeYard Show(Transform world){
   if(!Current)Current=new GameObject("Rede Fleet Yard").AddComponent<CheckoutRedeYard>();
   Current.world=world;Current.Build();return Current;
  }
  public static void HideYard(){if(Current)Current.Off();}

  void Build(){
   if(!Resources.Load<GameObject>("Rede/RedeFleetYard")){Report="yard model missing";return;}
   if(!yard){
    yard=CheckoutRedeModels.Spawn("RedeFleetYard",transform,"Yard");
    fuel=CheckoutRedeModels.Spawn("RedeFuelIsland",transform,"Diesel island");
   }
   yard.gameObject.SetActive(true);fuel.gameObject.SetActive(true);
   yard.SetPositionAndRotation(Origin,Quaternion.identity);
   // the Blender island turned 90° about Z: the long side along the entrance aisle
   fuel.SetPositionAndRotation(W(Pump.x,Pump.y),Quaternion.Euler(0,-90,0));
   ClearPlaza();
   Grow(true);
   Report=$"yard on, hid {hidden.Count} renderers, map north edge {(fog?fog.PlayableRect.yMax:0):0.0}";
  }

  void Off(){
   foreach(var r in hidden)if(r)r.enabled=true;hidden.Clear();
   if(yard)yard.gameObject.SetActive(false);if(fuel)fuel.gameObject.SetActive(false);
   foreach(var t in trucks.Values){Release(t);if(t.model)Destroy(t.model.gameObject);}
   trucks.Clear();loading.StopAll();Grow(false);Report="yard off";
  }

  // The yard lies past the map's old north edge (z 49.5) and reaches z 73.5 with its hedges: with it the map grows
  // north, the edge fog moves back past the hedges, the camera can pan up to it and the street's cars turn round
  // deep in the fog instead of at the old edge ("Quando a gente expande para rede, o mapa aumenta um pouco também").
  public const float NorthEdge=75f;
  CheckoutEdgeFog fog;Rect fogBefore;bool grown;
  void Grow(bool on){
   if(!fog&&Camera.main)fog=Camera.main.GetComponent<CheckoutEdgeFog>();
   if(on&&!grown){
    grown=true;MarketDay.MarketSimulation.ExtraNorth=24f;
    if(fog){fogBefore=fog.PlayableRect;var r=fogBefore;if(r.width>0&&r.yMax<NorthEdge)fog.PlayableRect=Rect.MinMaxRect(r.xMin,r.yMin,r.xMax,NorthEdge);}
    CheckoutNeighborhoodTraffic.NorthTurn=NorthEdge+14f;
   }else if(!on&&grown){
    grown=false;MarketDay.MarketSimulation.ExtraNorth=0;
    if(fog&&fogBefore.width>0)fog.PlayableRect=fogBefore;
    CheckoutNeighborhoodTraffic.NorthTurn=0;
   }
  }

  // Whatever stands wholly on the yard's footprint (the plaza's planters, a bench or a lamp) hides, and any of the
  // horizon's houses touching it; the ground, the roads and the trees' row south of it stay.
  void ClearPlaza(){
   foreach(var r in hidden)if(r)r.enabled=true;hidden.Clear();
   if(!world)return;
   var min=Origin+new Vector3(-18.2f,0,-6.9f);var max=Origin+new Vector3(19.3f,0,18.8f);
   var horizon=world.Find("City Horizon");
   foreach(var r in world.GetComponentsInChildren<Renderer>(false)){
    if(!r.enabled||r.transform.IsChildOf(transform))continue;
    var b=r.bounds;
    bool house=horizon&&r.transform.IsChildOf(horizon)&&!r.name.StartsWith("Ground");
    bool touches=b.max.x>min.x&&b.min.x<max.x&&b.max.z>min.z&&b.min.z<max.z;
    bool inside=b.min.x>=min.x&&b.max.x<=max.x&&b.min.z>=min.z&&b.max.z<=max.z;
    if(house?!touches:(!inside||b.size.y<.3f))continue;
    if(r.GetComponentInParent<CheckoutWalker>()||r.name.Contains("Customer")||r.name.Contains("Worker")||r.GetComponentInParent<Animator>())continue;
    r.enabled=false;hidden.Add(r);
   }
  }

  // ------------------------------------------------------------------ the snapshot
  public void Sync(Snapshot s){
   if(!yard||!yard.gameObject.activeInHierarchy||s?.chain?.trucks==null)return;
   var seen=new HashSet<string>();
   for(int i=0;i<s.chain.trucks.Length;i++){
    var f=s.chain.trucks[i];if(f==null||string.IsNullOrEmpty(f.id))continue;seen.Add(f.id);
    bool fresh=!trucks.TryGetValue(f.id,out var t);
    if(fresh){
     // bays fill from the east end (by the pump)
     t=new Truck{id=f.id,kind=f.kind=="refrigerado"?"refrigerado":"seco",bay=Bays.Length-1-Mathf.Min(i,Bays.Length-1)};
     t.model=CheckoutRedeModels.Spawn(t.kind=="refrigerado"?"FleetTruck_Reefer":"FleetTruck_Dry",transform,"Fleet truck "+f.id);
     t.model.localScale=Vector3.one*FleetScale;
     t.box=LocalBox(t.model);
     trucks[f.id]=t;
    }
    t.phase=f.phase;t.departAt=f.departAt;t.arriveAt=f.arriveAt;t.returnAt=f.returnAt;
    if(!string.IsNullOrEmpty(f.job)){t.job=f.job;t.lastJob=f.job;}else t.job=null;
    if(fresh){
     // first sight (a new session, a new truck): it is where its job says, no parade
     t.doneDepart=f.departAt;
     if(f.phase=="patio")Park(t);else Away(t);
    }
   }
   foreach(var id in new List<string>(trucks.Keys))if(!seen.Contains(id)){var t=trucks[id];Release(t);if(t.model)Destroy(t.model.gameObject);trucks.Remove(id);}
  }

  // A truck at rest follows its job (called every half second): a parked one sent out leaves (to the dock when one is
  // free, or north to a supplier), one away comes home when its trip is (nearly) over. One on the move finishes first.
  // the phase now (the snapshot's phase was worked out when it was sent; the trip's times tell the rest)
  string Phase(Truck t,double now){
   if(string.IsNullOrEmpty(t.job)||t.phase=="patio")return "patio";
   return now<t.arriveAt?"indo":now<t.returnAt?"voltando":"patio";
  }
  void Settle(Truck t){
   if(!t.model)return;
   double now=CheckoutBridge.Now;string phase=Phase(t,now);
   if(t.mode==Mode.Parked){
    if(phase=="indo"&&t.departAt!=t.doneDepart&&!t.qaStay){
     if(t.job=="abastecer"){t.doneDepart=t.departAt;LeaveNorth(t);}
     else{int d=FreeDock();if(d>=0){t.doneDepart=t.departAt;ToDock(t,d);}}
    }
   }else if(t.mode==Mode.Away&&!t.qaStay){
    if(phase=="indo"&&t.departAt!=t.doneDepart)t.doneDepart=t.departAt;   // a new trip while it was out: it stays out
    bool cityJob=t.lastJob=="contrato"||t.lastJob=="filial";
    if(phase=="patio")ComeHome(t,cityJob);
    else if(phase=="voltando"&&cityJob&&now>=t.returnAt-ReturnLead)ComeHome(t,true);
   }
  }

  void Park(Truck t){
   t.mode=Mode.Parked;t.model.gameObject.SetActive(true);t.held=false;
   t.model.SetPositionAndRotation(W(Bays[t.bay],TruckY),Quaternion.identity);   // the Blender truck faces −Z: nose south
   CheckoutEventTraffic.Unregister(t.model);
  }
  void Away(Truck t){t.mode=Mode.Away;t.model.gameObject.SetActive(false);t.held=false;CheckoutEventTraffic.Unregister(t.model);}
  void Release(Truck t){if(t.model)CheckoutEventTraffic.Unregister(t.model);if(t.dock>=0){CheckoutDeliveryTrucks.Unreserve(t.model);t.dock=-1;}}

  // ------------------------------------------------------------------ journeys
  // Points along the way; `back` marks the legs driven in reverse (onto a dock). Each run (legs driven one way) becomes
  // one smooth path (CheckoutVehiclePath: corners rounded, right turns tight), the truck stops between runs.
  readonly List<Vector3> pts=new List<Vector3>();readonly List<bool> legBack=new List<bool>();
  void Begin(Vector3 p){pts.Clear();legBack.Clear();pts.Add(p);legBack.Add(false);}
  void To(Vector3 p,bool back=false){pts.Add(p);legBack.Add(back);}
  void Go(Truck t,string route,bool hiddenStart,Action done){
   t.runCount=0;t.runBack.Clear();
   Vector3? body=t.model.gameObject.activeSelf&&!hiddenStart?-t.model.forward:(Vector3?)null;
   int i=1;
   while(i<pts.Count){
    bool reverse=legBack[i];int j=i;while(j+1<pts.Count&&legBack[j+1]==reverse)j++;
    runPts.Clear();for(int k=i-1;k<=j;k++)runPts.Add(pts[k]);
    if(t.runs.Count<=t.runCount)t.runs.Add(new CheckoutVehiclePath());
    Vector3? prev=t.runCount>0?(t.runBack[t.runCount-1]?-t.runs[t.runCount-1].EndTangent:t.runs[t.runCount-1].EndTangent):body;
    Vector3? facing=prev.HasValue?(reverse?-prev.Value:prev.Value):(Vector3?)null;
    t.runs[t.runCount++].Build(runPts,reverse?2.6f:3.6f,facing,false);
    t.runBack.Add(reverse);i=j+1;
   }
   t.run=0;t.s=0;t.speed=0;t.since=Time.time;t.mode=Mode.Driving;t.done=done;t.route=route;t.hiddenStart=hiddenStart;t.held=false;
   if(!hiddenStart){t.model.gameObject.SetActive(true);CheckoutEventTraffic.Register(t.model,t.box);}
   else t.model.gameObject.SetActive(false);
  }
  readonly List<Vector3> runPts=new List<Vector3>();

  // out of its bay into the exit aisle and out to the street (the last point is on the driveway)
  void OutOfBay(Truck t){float x=Bays[t.bay];Begin(W(x,TruckY));To(W(x,LaneOut));To(W(16.6f,LaneOut));}
  // from the pump on along the entrance aisle and forwards into its bay
  void ToBay(Truck t){
   float x=Bays[t.bay];Begin(t.model.position);To(W(x,LaneIn));To(W(x,TruckY));
   Go(t,"bay",false,()=>Park(t));
  }
  void Refuel(Truck t){t.mode=Mode.Refuelling;t.timer=RefuelSeconds;t.held=false;}
  // in at the entrance from the street (a point on the street's lane north of the entrance or level with it)
  void IntoEntrance(){To(W(15.6f,LaneIn));To(W(PumpStop.x,PumpStop.y));}

  // contract / branch run: down the east street, past the centre's driveway, back onto the dock; load; away east
  void ToDock(Truck t,int dock){
   if(!CheckoutRedeWorld.DockPose(dock,out var tail,out var facing)){t.doneDepart=-1;return;}
   t.dock=dock;CheckoutDeliveryTrucks.Reserve(t.model,tail);
   var centre=tail+facing*TailOffset;centre.y=Road;
   OutOfBay(t);To(V(EastSouth,Origin.z+LaneOut));To(V(EastSouth,PastGateZ));
   To(V(18.4f,GateZ),true);To(V(12f,centre.z),true);To(centre+facing*4f,true);To(centre,true);
   Go(t,"to dock",false,()=>Load(t));
  }
  void Load(Truck t){
   t.mode=Mode.Loading;t.timer=LoadSeconds;t.held=false;
   CheckoutRedeWorld.DockPose(t.dock,out var tail,out var facing);
   loading.Start(t.dock,t.model,tail,facing,LoadSeconds);
  }
  void FromDockToCity(Truck t){
   CheckoutRedeWorld.DockPose(t.dock,out var tail,out var facing);
   Begin(t.model.position);To(V(12f,tail.z));To(V(18.6f,GateZ));To(V(EastSouth,PastGateZ-.6f));To(V(EastSouth,AvenueEast));To(V(FarEast,AvenueEast));
   loading.Stop(t.dock);CheckoutDeliveryTrucks.Unreserve(t.model);t.dock=-1;
   Go(t,"to the city",false,()=>{Away(t);Settle(t);});
  }
  // home: from the city (along the avenue from the east, up the east street) or from the north end of the map
  void ComeHome(Truck t,bool fromCity){
   if(fromCity){Begin(V(FarEast,AvenueWest));To(V(EastNorth,AvenueWest));To(V(EastNorth,Origin.z+LaneIn));}
   else{Begin(V(EastSouth,FarNorth));To(V(EastSouth,Origin.z+LaneIn));}
   IntoEntrance();
   Go(t,fromCity?"home from the city":"home from the north",true,()=>Refuel(t));
  }
  // supplying the centre: north to the supplier (the goods come back in it to the docks: TakeOver)
  void LeaveNorth(Truck t){
   OutOfBay(t);To(V(EastNorth,Origin.z+LaneOut));To(V(EastNorth,FarNorth));
   Go(t,"to the supplier",false,()=>{Away(t);Settle(t);});
  }

  /// <summary>The supplier truck dressed as fleet truck `id` has been unloaded at the centre's dock: the yard's truck
  /// takes its place there (same model, same pose) and drives home. False: the truck is busy elsewhere.</summary>
  public bool TakeOver(string id,Transform skin){
   if(string.IsNullOrEmpty(id)||!skin||!trucks.TryGetValue(id,out var t)||t.mode!=Mode.Away||!t.model)return false;
   t.model.SetPositionAndRotation(skin.position,skin.rotation);t.model.gameObject.SetActive(true);
   var p=skin.position;p.y=Road;
   Begin(p);To(V(12f,p.z));To(V(18.6f,GateZ));To(V(EastNorth,GateZ));To(V(EastNorth,Origin.z+LaneIn));IntoEntrance();
   t.doneDepart=t.departAt;
   Go(t,"home from the dock",false,()=>Refuel(t));
   return true;
  }

  // a dock no truck stands on or is headed for (the suppliers' trucks included)
  int FreeDock(){
   for(int d=0;d<CheckoutRedeWorld.DockCount;d++){
    if(!CheckoutRedeWorld.DockPose(d,out var tail,out _))continue;
    if(CheckoutDeliveryTrucks.BayTaken(tail))continue;
    bool mine=false;foreach(var o in trucks.Values)if(o.dock==d)mine=true;
    if(!mine)return d;
   }
   return -1;
  }
  /// <summary>Whether a fleet truck is backing onto / standing at / loading at dock `d` (the dock's door opens).</summary>
  public bool DockBusy(int d){
   foreach(var t in trucks.Values)if(t.dock==d&&t.model&&(t.mode==Mode.Loading||(t.mode==Mode.Driving&&t.run>0)))return true;
   return false;
  }
  /// <summary>The trucks out on the map (the centre's gate opens for them).</summary>
  public IEnumerable<Transform> Moving(){foreach(var t in trucks.Values)if(t.model&&t.model.gameObject.activeInHierarchy&&t.mode!=Mode.Parked)yield return t.model;}

  // ------------------------------------------------------------------ driving
  float nextSettle,nextPaint;
  void Update(){
   if(Time.unscaledTime>nextSettle){nextSettle=Time.unscaledTime+.5f;foreach(var t in trucks.Values)Settle(t);}
   foreach(var t in trucks.Values){
    if(!t.model)continue;
    switch(t.mode){
     case Mode.Driving:Drive(t);break;
     case Mode.Refuelling:t.timer-=Time.deltaTime;if(t.timer<=0)ToBay(t);break;
     case Mode.Loading:
      t.timer-=Time.deltaTime;
      if(t.timer<=0&&loading.Done(t.dock))FromDockToCity(t);
      break;
    }
   }
   loading.Update(Time.deltaTime);
   if(Time.unscaledTime>nextPaint){nextPaint=Time.unscaledTime+1f;foreach(var t in trucks.Values)if(t.model&&t.model.gameObject.activeInHierarchy)CheckoutMarketPaint.Touch(t.model.gameObject);}
  }

  void Drive(Truck t){
   float dt=Time.deltaTime;if(dt<=0)return;
   var m=t.model;
   if(t.hiddenStart){
    // it comes out of the fog once its start is clear
    var start=t.runs[0].Sample(0,out var first);
    if(Covered(t,start,6f))return;
    t.hiddenStart=false;m.SetPositionAndRotation(start,Quaternion.LookRotation(-first,Vector3.up));m.gameObject.SetActive(true);
    CheckoutEventTraffic.Register(m,t.box);
   }
   while(t.run<t.runCount&&t.s>=t.runs[t.run].Length-.02f){t.run++;t.s=0;t.speed=0;}
   if(t.run>=t.runCount){var done=t.done;t.done=null;t.mode=Mode.Parked;CheckoutEventTraffic.Unregister(m);done?.Invoke();if(t.mode==Mode.Refuelling||t.mode==Mode.Loading)CheckoutEventTraffic.Register(m,t.box);return;}
   var path=t.runs[t.run];bool reverse=t.runBack[t.run];
   path.Sample(t.s,out var dir);
   const float accel=2f,brake=2.6f;
   bool yardOrDock=InYard(m.position)||m.position.x<EastSouth-1.5f&&m.position.z>26f&&m.position.z<41f;
   float cruise=reverse?1.5f:yardOrDock?2.6f:4.5f;
   float top=Mathf.Min(cruise,Mathf.Max(.35f,path.StopSpeed(t.s,brake)),path.Allowed(t.s,cruise,brake,1.8f));
   // whatever is ahead (behind, backing up): cars, people, the suppliers' and the other fleet trucks, junctions
   var nose=m.position+dir*(reverse?TailOffset:NoseOffset);
   float look=1.2f+t.speed*t.speed/(2*brake);
   bool blocked=CheckoutEventTraffic.CityAhead(nose,dir,look,1.0f)||CheckoutEventTraffic.Blocks(nose-dir*.3f,dir,look,1.0f,m);
   bool held=false;
   if(!reverse&&!yardOrDock&&CheckoutTrafficJunctions.Hold(m,dir,blocked,t.speed*t.speed/(2*brake*1.8f)))held=true;
   else if(blocked&&Time.time-t.since<25f)held=true;   // never stuck for ever
   if(held)top=0;t.held=held&&t.speed<.2f;
   t.speed=t.speed<top?Mathf.Min(top,t.speed+accel*dt):Mathf.Max(top,t.speed-brake*1.8f*dt);
   t.s=Mathf.Min(path.Length,t.s+t.speed*dt);
   var p=path.Sample(t.s,out var heading);
   // the model's nose is −Z: it faces where it goes, or away from it backing up
   m.SetPositionAndRotation(p,Quaternion.LookRotation(reverse?heading:-heading,Vector3.up));
   if(t.speed>.3f)t.since=Time.time;
  }
  static bool InYard(Vector3 p)=>p.x>Origin.x-18f&&p.x<Origin.x+16.6f&&p.z>Origin.z-6.5f&&p.z<Origin.z+17f;

  // another fleet truck, a supplier's truck or a car within `radius` of a point
  bool Covered(Truck self,Vector3 at,float radius){
   foreach(var o in trucks.Values){
    if(o==self||!o.model||!o.model.gameObject.activeSelf||o.mode==Mode.Parked)continue;
    var d=o.model.position-at;d.y=0;if(d.sqrMagnitude<radius*radius)return true;
   }
   return CheckoutEventTraffic.Covered(at,radius*.5f,self.model)||CheckoutEventTraffic.CityAhead(at,Vector3.forward,0f,radius*.5f);
  }

  static Bounds LocalBox(Transform t){
   bool first=true;var box=new Bounds(Vector3.zero,new Vector3(2.4f,3,7));
   foreach(var mf in t.GetComponentsInChildren<MeshFilter>(true)){
    if(!mf.sharedMesh)continue;var b=mf.sharedMesh.bounds;
    for(int i=0;i<8;i++){
     var c=new Vector3((i&1)==0?b.min.x:b.max.x,(i&2)==0?b.min.y:b.max.y,(i&4)==0?b.min.z:b.max.z);
     var l=t.InverseTransformPoint(mf.transform.TransformPoint(c));
     if(first){box=new Bounds(l,Vector3.zero);first=false;}else box.Encapsulate(l);
    }
   }
   return box;
  }

  // ------------------------------------------------------------------ QA
  public string QaMode(string id)=>trucks.TryGetValue(id,out var t)?t.mode.ToString():"-";
  public string QaRoute(string id)=>trucks.TryGetValue(id,out var t)?t.route:"-";
  public bool QaHeld(string id)=>trucks.TryGetValue(id,out var t)&&t.held;
  public int QaDock(string id)=>trucks.TryGetValue(id,out var t)?t.dock:-1;
  /// <summary>QA: each truck's id, mode, route and bay.</summary>
  public string Describe(){var parts=new List<string>();foreach(var t in trucks.Values)parts.Add($"{t.id}:{t.mode}{(t.mode==Mode.Driving?"("+t.route+")":"")}@{t.bay}{(t.dock>=0?" dock "+t.dock:"")}");return string.Join(" ",parts);}
  public Transform TruckModel(string id)=>trucks.TryGetValue(id,out var t)?t.model:null;
  public IEnumerable<string> Ids=>trucks.Keys;
  public Vector3 BayPosition(int i)=>W(Bays[Mathf.Clamp(i,0,Bays.Length-1)],TruckY);
  public static Vector3 PumpPosition=>W(PumpStop.x,PumpStop.y);
  /// <summary>QA: the entrance and exit driveways at the street (world).</summary>
  public static Vector3 EntranceAt=>W(17.5f,LaneIn);
  public static Vector3 ExitAt=>W(17.5f,LaneOut);
  /// <summary>QA: the yard's slab (world x/z), driveways excluded.</summary>
  public static Rect Slab=>Rect.MinMaxRect(Origin.x-17.5f,Origin.z-6.3f,Origin.x+14.6f,Origin.z+16.9f);
  public int QaLoaders=>loading.Active;

  void OnDestroy(){if(Current==this)Current=null;loading.StopAll();}
 }
}
