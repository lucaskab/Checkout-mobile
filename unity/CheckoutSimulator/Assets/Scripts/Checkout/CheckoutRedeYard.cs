using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Rede: the fleet's yard on the plaza north of the distribution centre (Lucas 06/11: "eu gostei da localização do 1",
 // "coloque no jogo"; v2 06/11: "aumente o estacionamento ... quase até o final do mapa", "uma entrada e uma saída",
 // "os caminhões ... apareçam ali do final do mapa e não simplesmente da calçada").
 // The model (Resources/Rede/RedeFleetYard, scripts/blender/rede_yard.py) stands at Origin with the approved diesel
 // island (RedeFuelIsland). It is a one-way loop, so a truck coming in and one going out never share a metre of road:
 //  * a truck at the depot ("patio") waits in its drive-through bay in the middle row, nose south to the exit aisle;
 //  * when it leaves (a delivery, a contract, a branch run) it drives forwards into the south aisle, out of the EXIT
 //    driveway, turns left onto the east street's northbound lane and away into the fog at the map's north end; the
 //    delivery itself is shown at the docks (CheckoutRedeWorld.Dress);
 //  * when it comes back it drives down the southbound lane out of the fog, turns into the ENTRANCE driveway at the
 //    north end, stops at the pump to refuel, then turns forwards into its bay.
 // The trucks are the chain's trucks at FleetScale (in proportion to the streets: a lane is 2.25 m), queue behind one
 // another, give way to the street's cars and the cars give way to them (CheckoutNeighborhoodTraffic.Blockers).
 // With the yard the map grows north (the edge fog, the camera's pan, the cars' turning points) and whatever stood on
 // its footprint (the plaza's planters, the horizon's houses) hides.
 public sealed class CheckoutRedeYard:MonoBehaviour {
  public static readonly Vector3 Origin=new Vector3(2f,0f,55.6f);
  /// <summary>The chain's trucks in the game (yard and docks): in proportion to the streets and the yard.</summary>
  public const float FleetScale=.75f;
  const float Top=.17f;
  // model space (rede_yard.py)
  static readonly float[] Bays={-15f,-11.7f,-8.4f,-5.1f,-1.8f,1.5f,4.8f};
  const float TruckY=4.4f,LaneIn=11.2f,LaneOut=-2.3f;
  static readonly Vector2 PumpStop=new Vector2(9.9f,LaneIn),Pump=new Vector2(9.5f,13.9f);
  // the east street (world x 22.4 southbound, 24.6 northbound: CheckoutNeighborhoodTraffic) in model space, and how
  // far north a truck comes from / goes to (world z 95.6: deep in the edge fog of the grown map)
  const float SouthLane=20.4f,NorthLane=22.6f,FarNorth=40f;
  const float Speed=3.6f,RefuelSeconds=9f;

  Transform world,yard,fuel;
  readonly List<Renderer> hidden=new List<Renderer>();
  /// <summary>QA: what the yard did last.</summary>
  public static string Report{get;private set;}="";
  public static CheckoutRedeYard Current{get;private set;}

  enum Mode{Away,Parked,Leaving,Arriving,Refuelling,ToBay}
  sealed class Truck{public string id,kind,phase;public Transform model;public Mode mode;public int bay;public List<Vector3> path;public float along,length,timer,waited;public bool held,started,qaStay;}
  readonly Dictionary<string,Truck> trucks=new Dictionary<string,Truck>();

  static Vector3 W(float x,float y)=>Origin+new Vector3(x,Top,y);

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
   foreach(var t in trucks.Values){CheckoutNeighborhoodTraffic.Blockers.Remove(t.model);if(t.model)Destroy(t.model.gameObject);}
   trucks.Clear();Grow(false);Report="yard off";
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

  public void Sync(Snapshot s){
   if(!yard||!yard.gameObject.activeInHierarchy||s?.chain?.trucks==null)return;
   var seen=new HashSet<string>();
   for(int i=0;i<s.chain.trucks.Length;i++){
    var f=s.chain.trucks[i];if(f==null||string.IsNullOrEmpty(f.id))continue;seen.Add(f.id);
    if(!trucks.TryGetValue(f.id,out var t)){
     // bays fill from the east end (by the pump)
     t=new Truck{id=f.id,kind=f.kind=="refrigerado"?"refrigerado":"seco",bay=Bays.Length-1-Mathf.Min(i,Bays.Length-1),phase=f.phase};
     t.model=CheckoutRedeModels.Spawn(t.kind=="refrigerado"?"FleetTruck_Reefer":"FleetTruck_Dry",transform,"Fleet truck "+f.id);
     t.model.localScale=Vector3.one*FleetScale;
     trucks[f.id]=t;
     if(f.phase=="patio")Park(t);else Away(t);
     continue;
    }
    t.phase=f.phase;Settle(t);
   }
   foreach(var id in new List<string>(trucks.Keys))if(!seen.Contains(id)){var t=trucks[id];CheckoutNeighborhoodTraffic.Blockers.Remove(t.model);if(t.model)Destroy(t.model.gameObject);trucks.Remove(id);}
  }

  // A truck at rest follows its phase: a parked one sent out leaves, one away that is due home comes in. A truck on
  // the move finishes what it is doing first (it never vanishes mid-yard), then settles.
  void Settle(Truck t){
   bool home=t.phase=="patio";
   if(t.mode==Mode.Parked&&!home)Leave(t);
   else if(t.mode==Mode.Away&&home&&!t.qaStay)Arrive(t);
  }

  void Park(Truck t){
   t.mode=Mode.Parked;t.model.gameObject.SetActive(true);
   t.model.SetPositionAndRotation(W(Bays[t.bay],TruckY),Quaternion.identity);   // the Blender truck faces −Z: nose south
  }
  void Away(Truck t){t.mode=Mode.Away;t.model.gameObject.SetActive(false);CheckoutNeighborhoodTraffic.Blockers.Remove(t.model);}

  // Forwards out of the bay into the south aisle, east to the exit driveway, left onto the northbound lane, north.
  void Leave(Truck t){
   float x=Bays[t.bay];
   Go(t,Mode.Leaving,Smooth(new List<Vector3>{W(x,TruckY),W(x,1.2f),W(x+1.6f,-1.5f),W(x+4.5f,LaneOut),W(16.4f,LaneOut),
    W(19.6f,-1.8f),W(21.8f,0f),W(NorthLane,2.8f),W(NorthLane,9f),W(NorthLane,FarNorth)}));
  }
  // Down the southbound lane out of the fog, right into the entrance driveway, along the aisle to the pump.
  void Arrive(Truck t){
   Go(t,Mode.Arriving,Smooth(new List<Vector3>{W(SouthLane,FarNorth),W(SouthLane,20f),W(SouthLane,15f),W(18.6f,11.8f),
    W(15.6f,LaneIn),W(PumpStop.x,PumpStop.y)}));
   t.model.gameObject.SetActive(false);   // shown once its start is clear (Update)
  }
  // From the pump on along the aisle and forwards into its bay, nose south.
  void ToBay(Truck t){
   float x=Bays[t.bay];
   var pts=new List<Vector3>{W(PumpStop.x,PumpStop.y)};
   if(x+5f<PumpStop.x-1f)pts.Add(W(x+5f,LaneIn));
   pts.Add(W(x+1.7f,10.3f));pts.Add(W(x,7.6f));pts.Add(W(x,TruckY));
   Go(t,Mode.ToBay,Smooth(pts));
  }

  void Go(Truck t,Mode mode,List<Vector3> path){t.mode=mode;t.path=path;t.along=0;t.length=Length(path);t.waited=0;t.started=mode!=Mode.Arriving;}

  static float Length(List<Vector3> p){float l=0;for(int i=1;i<p.Count;i++)l+=Vector3.Distance(p[i-1],p[i]);return l;}

  // Catmull-Rom through the points (a dozen steps per span): trucks turn in curves, not corners.
  static List<Vector3> Smooth(List<Vector3> p){
   var o=new List<Vector3>();if(p.Count<3){o.AddRange(p);return o;}
   for(int i=0;i<p.Count-1;i++){
    var p0=p[Mathf.Max(0,i-1)];var p1=p[i];var p2=p[i+1];var p3=p[Mathf.Min(p.Count-1,i+2)];
    int n=Mathf.Clamp(Mathf.CeilToInt(Vector3.Distance(p1,p2)/.6f),2,24);
    for(int k=0;k<n;k++){float u=k/(float)n,u2=u*u,u3=u2*u;o.Add(.5f*((2*p1)+(-p0+p2)*u+(2*p0-5*p1+4*p2-p3)*u2+(-p0+3*p1-3*p2+p3)*u3));}
   }
   o.Add(p[p.Count-1]);return o;
  }

  float nextPaint;
  void Update(){
   foreach(var t in trucks.Values){
    if(!t.model)continue;
    switch(t.mode){
     case Mode.Leaving:case Mode.Arriving:case Mode.ToBay:
      if(!t.started){
       // an arrival waits in the fog until its start is clear (another truck or a car just went by)
       if(Occupied(t,t.path[0],7f))break;
       t.started=true;t.model.gameObject.SetActive(true);t.model.position=t.path[0];
       var first=t.path[1]-t.path[0];first.y=0;t.model.rotation=Quaternion.LookRotation(-first.normalized,Vector3.up);
       if(!CheckoutNeighborhoodTraffic.Blockers.Contains(t.model))CheckoutNeighborhoodTraffic.Blockers.Add(t.model);
      }
      Drive(t,Time.deltaTime);
      if(t.along>=t.length){
       if(t.mode==Mode.Leaving){Away(t);Settle(t);}
       else if(t.mode==Mode.Arriving){t.mode=Mode.Refuelling;t.timer=RefuelSeconds;}
       else{Park(t);CheckoutNeighborhoodTraffic.Blockers.Remove(t.model);Settle(t);}
      }
      break;
     case Mode.Refuelling:
      t.timer-=Time.deltaTime;if(t.timer<=0)ToBay(t);break;
    }
   }
   if(Time.unscaledTime>nextPaint){nextPaint=Time.unscaledTime+1f;foreach(var t in trucks.Values)if(t.model&&t.model.gameObject.activeInHierarchy)CheckoutMarketPaint.Touch(t.model.gameObject);}
  }

  // Another fleet truck on the move (or at the pump) within `radius` of a point.
  bool Occupied(Truck self,Vector3 at,float radius){
   foreach(var o in trucks.Values){
    if(o==self||!o.model||!o.model.gameObject.activeSelf||o.mode==Mode.Parked||o.mode==Mode.Away)continue;
    var d=o.model.position-at;d.y=0;if(d.sqrMagnitude<radius*radius)return true;
   }
   var traffic=Traffic;
   if(traffic&&traffic.cars!=null)foreach(var c in traffic.cars)if(c!=null&&c.vehicle&&c.vehicle.gameObject.activeSelf){var d=c.vehicle.position-at;d.y=0;if(d.sqrMagnitude<radius*radius)return true;}
   return false;
  }

  CheckoutNeighborhoodTraffic traffic;
  CheckoutNeighborhoodTraffic Traffic{get{if(!traffic)traffic=FindAnyObjectByType<CheckoutNeighborhoodTraffic>();return traffic;}}

  // Something in the way ahead: a fleet truck on the move or refuelling (a queue at the pump), a car on the street.
  // Parked trucks are in their bays, off every lane. The loop is one-way, so trucks never face each other: a truck
  // always waits for the one ahead. Only a car that stays in the way long (a jam) is crept past (never a deadlock).
  bool Ahead(Truck t,Vector3 heading){
   var p=t.model.position;
   bool In(Vector3 q,float reach,float half){var d=q-p;d.y=0;float f=Vector3.Dot(d,heading);return f>.2f&&f<reach&&(d-heading*f).sqrMagnitude<half*half;}
   foreach(var o in trucks.Values){
    if(o==t||!o.model||!o.model.gameObject.activeSelf||o.mode==Mode.Parked||o.mode==Mode.Away)continue;
    if(In(o.model.position,6.4f,1.7f))return true;
   }
   var traffic=Traffic;
   if(t.waited<8f&&traffic&&traffic.cars!=null)foreach(var c in traffic.cars)if(c!=null&&c.vehicle&&c.vehicle.gameObject.activeSelf&&In(c.vehicle.position,6f,1.8f))return true;
   return false;
  }

  void Drive(Truck t,float dt){
   var here=Point(t,t.along,out var tangent);tangent.y=0;
   bool wait=tangent.sqrMagnitude>1e-4f&&Ahead(t,tangent.normalized);
   t.held=wait;
   if(wait){t.waited+=dt;return;}
   t.waited=0;
   // slower on the first / last metres and in the turns
   float edge=Mathf.Min(t.along,t.length-t.along);
   var further=Point(t,Mathf.Min(t.length,t.along+3f),out var ahead);ahead.y=0;
   float bend=tangent.sqrMagnitude>1e-4f&&ahead.sqrMagnitude>1e-4f?Vector3.Angle(tangent,ahead):0;
   float v=Speed*Mathf.Lerp(.35f,1f,Mathf.Clamp01(edge/4f))*Mathf.Lerp(1f,.5f,Mathf.Clamp01(bend/60f));
   t.along=Mathf.Min(t.length,t.along+v*dt);
   var p=Point(t,t.along,out var dir);dir.y=0;
   t.model.position=p;
   // the model's nose is −Z
   if(dir.sqrMagnitude>1e-4f)t.model.rotation=Quaternion.Slerp(t.model.rotation,Quaternion.LookRotation(-dir.normalized,Vector3.up),Mathf.Clamp01(dt*8f));
  }
  static Vector3 Point(Truck t,float d,out Vector3 tangent){
   float acc=0;
   for(int i=1;i<t.path.Count;i++){
    float l=Vector3.Distance(t.path[i-1],t.path[i]);
    if(acc+l>=d||i==t.path.Count-1){tangent=(t.path[i]-t.path[i-1]).normalized;return Vector3.Lerp(t.path[i-1],t.path[i],l>0?Mathf.Clamp01((d-acc)/l):1);}
    acc+=l;
   }
   tangent=Vector3.forward;return t.path[0];
  }

  /// <summary>QA: a parked truck goes out of sight and comes straight back (fog → entrance → pump → its bay).</summary>
  public bool QaRoundTrip(string id){
   if(!trucks.TryGetValue(id,out var t)||t.mode!=Mode.Parked)return false;
   t.qaStay=false;Arrive(t);return true;
  }
  /// <summary>QA: a parked truck leaves and stays away (the store still has it at the depot).</summary>
  public bool QaLeave(string id){if(!trucks.TryGetValue(id,out var t)||t.mode!=Mode.Parked)return false;t.qaStay=true;Leave(t);return true;}
  public string QaMode(string id)=>trucks.TryGetValue(id,out var t)?t.mode.ToString():"-";
  public bool QaHeld(string id)=>trucks.TryGetValue(id,out var t)&&t.held;
  /// <summary>QA: each truck's id, mode and bay.</summary>
  public string Describe(){var parts=new List<string>();foreach(var t in trucks.Values)parts.Add($"{t.id}:{t.mode}@{t.bay}");return string.Join(" ",parts);}
  public Transform TruckModel(string id)=>trucks.TryGetValue(id,out var t)?t.model:null;
  public Vector3 BayPosition(int i)=>W(Bays[Mathf.Clamp(i,0,Bays.Length-1)],TruckY);
  public static Vector3 PumpPosition=>W(PumpStop.x,PumpStop.y);
  /// <summary>QA: the entrance and exit driveways at the street (world).</summary>
  public static Vector3 EntranceAt=>W(17.5f,LaneIn);
  public static Vector3 ExitAt=>W(17.5f,LaneOut);
  /// <summary>QA: the yard's slab (world x/z), driveways excluded.</summary>
  public static Rect Slab=>Rect.MinMaxRect(Origin.x-17.5f,Origin.z-6.3f,Origin.x+14.6f,Origin.z+16.9f);

  void OnDestroy(){if(Current==this)Current=null;}
 }
}
