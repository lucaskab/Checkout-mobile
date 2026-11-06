using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Rede: the fleet's yard on the plaza north of the distribution centre (Lucas 06/11: "eu gostei da localização do 1",
 // "coloque no jogo"). The model (Resources/Rede/RedeFleetYard, scripts/blender/rede_yard.py) stands at Origin with the
 // approved diesel island (RedeFuelIsland) by its entrance, and the chain's own trucks live in it:
 //  * a truck at the depot ("patio") waits backed into its bay, nose to the aisle;
 //  * when it leaves (a delivery, a contract, a branch run) it pulls out of the bay, drives down the aisle and out to the
 //    east street; the delivery itself is shown at the docks (CheckoutRedeWorld.Dress);
 //  * when it comes back it drives in from the street, stops by the pump to refuel, then backs into its bay.
 // The plaza's own furniture standing on the yard (two planters) hides while the yard is shown.
 public sealed class CheckoutRedeYard:MonoBehaviour {
  public static readonly Vector3 Origin=new Vector3(2f,0f,55.6f);
  const float Top=.17f;
  // model space (rede_yard.py): bays along the north kerb, a parked truck's origin, the pump stop, the aisle lanes
  static readonly float[] Bays={-15f,-11.7f,-8.4f,-5.1f,-1.8f,1.5f,4.8f};
  const float TruckY=2.4f,LaneIn=-2.1f,LaneOut=-2.6f,StreetX=20.5f;
  static readonly Vector2 PumpStop=new Vector2(9.9f,-2.1f),Pump=new Vector2(9.5f,-4.7f);
  const float Speed=4.2f,RefuelSeconds=18f;

  Transform world,yard,fuel;
  readonly List<Renderer> hidden=new List<Renderer>();
  /// <summary>QA: what the yard did last.</summary>
  public static string Report{get;private set;}="";
  public static CheckoutRedeYard Current{get;private set;}

  enum Mode{Away,Parked,Leaving,Arriving,Refuelling,Backing}
  sealed class Truck{public string id,kind;public Transform model;public Mode mode;public int bay;public List<Vector3> path;public List<bool> reverse;public float along,length,timer;public string phase;}
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
   // the Blender island turned 90° about Z: the long side along the aisle
   fuel.SetPositionAndRotation(W(Pump.x,Pump.y),Quaternion.Euler(0,-90,0));
   ClearPlaza();
   Grow(true);
   Report=$"yard on, hid {hidden.Count} plaza renderers, map north edge {(fog?fog.Playable.yMax:0):0.0}";
  }

  void Off(){
   foreach(var r in hidden)if(r)r.enabled=true;hidden.Clear();
   if(yard)yard.gameObject.SetActive(false);if(fuel)fuel.gameObject.SetActive(false);
   foreach(var t in trucks.Values)if(t.model)Destroy(t.model.gameObject);
   trucks.Clear();Grow(false);Report="yard off";
  }

  // The yard lies just past the map's north edge (z 49.5): with it the map grows north, the edge fog moves back past
  // the hedges and the camera can pan up to it ("Quando a gente expande para rede, o mapa aumenta um pouco também").
  const float NorthEdge=65f;
  CheckoutEdgeFog fog;Rect fogBefore;bool grown;
  void Grow(bool on){
   if(!fog&&Camera.main)fog=Camera.main.GetComponent<CheckoutEdgeFog>();
   if(on&&!grown){
    grown=true;MarketDay.MarketSimulation.ExtraNorth=14f;
    if(fog){fogBefore=fog.Playable;var r=fogBefore;if(r.width>0&&r.yMax<NorthEdge)fog.Playable=Rect.MinMaxRect(r.xMin,r.yMin,r.xMax,NorthEdge);}
   }else if(!on&&grown){
    grown=false;MarketDay.MarketSimulation.ExtraNorth=0;
    if(fog&&fogBefore.width>0)fog.Playable=fogBefore;
   }
  }

  // Whatever stands wholly on the yard's footprint (the plaza's planters, a bench or a lamp) hides; the ground under it,
  // the roads and the trees' row south of it are larger than the footprint or outside it and stay.
  void ClearPlaza(){
   foreach(var r in hidden)if(r)r.enabled=true;hidden.Clear();
   if(!world)return;
   var min=Origin+new Vector3(-18.2f,0,-6.9f);var max=Origin+new Vector3(18.2f,0,7.6f);
   foreach(var r in world.GetComponentsInChildren<Renderer>(false)){
    if(!r.enabled||r.transform.IsChildOf(transform))continue;
    var b=r.bounds;
    if(b.min.x<min.x||b.max.x>max.x||b.min.z<min.z||b.max.z>max.z||b.size.y<.3f)continue;
    var root=r.transform.root;if(root==transform)continue;
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
     // bays fill from the east end (by the pump): the first trucks back in with room to spare
     t=new Truck{id=f.id,kind=f.kind=="refrigerado"?"refrigerado":"seco",bay=Bays.Length-1-Mathf.Min(i,Bays.Length-1),phase=f.phase};
     t.model=CheckoutRedeModels.Spawn(t.kind=="refrigerado"?"FleetTruck_Reefer":"FleetTruck_Dry",transform,"Fleet truck "+f.id);
     trucks[f.id]=t;
     if(f.phase=="patio")Park(t);else Away(t);
    }
    if(t.phase==f.phase)continue;
    bool home=f.phase=="patio",wasHome=t.phase=="patio";t.phase=f.phase;
    if(wasHome&&!home)Leave(t);
    else if(!wasHome&&home)Arrive(t);
   }
   foreach(var id in new List<string>(trucks.Keys))if(!seen.Contains(id)){if(trucks[id].model)Destroy(trucks[id].model.gameObject);trucks.Remove(id);}
  }

  void Park(Truck t){
   t.mode=Mode.Parked;t.model.gameObject.SetActive(true);
   t.model.SetPositionAndRotation(W(Bays[t.bay],TruckY),Quaternion.identity);   // the Blender truck faces −Z: nose to the aisle
  }
  void Away(Truck t){t.mode=Mode.Away;t.model.gameObject.SetActive(false);}

  // Out of the bay forwards, a curve onto the out lane, down the aisle past the pump and out to the street.
  void Leave(Truck t){
   if(t.mode!=Mode.Parked){Away(t);return;}
   float x=Bays[t.bay];
   var pts=new List<Vector3>{W(x,TruckY),W(x,.2f),W(x+1.2f,-1.6f),W(x+4f,LaneOut),W(StreetX,LaneOut),W(StreetX+6,LaneOut)};
   Go(t,Mode.Leaving,Smooth(pts),false);
  }
  // In from the street on the in lane to the pump.
  void Arrive(Truck t){
   var pts=new List<Vector3>{W(StreetX+6,LaneIn),W(StreetX,LaneIn),W(PumpStop.x,PumpStop.y)};
   t.model.gameObject.SetActive(true);
   Go(t,Mode.Arriving,Smooth(pts),false);
  }
  // From the pump forwards past its bay, then backwards into it (nose ends to the aisle).
  void Back(Truck t){
   float x=Bays[t.bay];
   // past the bay (as far as the yard's west kerb allows), then back in
   float over=Mathf.Min(5.5f,x+16.9f);
   var fwd=Smooth(new List<Vector3>{W(PumpStop.x,PumpStop.y),W(x-over*.55f,LaneIn),W(x-over,LaneIn+.3f)});
   var rev=Smooth(new List<Vector3>{W(x-over,LaneIn+.3f),W(x-over*.3f,-.9f),W(x,1.0f),W(x,TruckY)});
   var all=new List<Vector3>(fwd);var dir=new List<bool>();for(int i=0;i<fwd.Count;i++)dir.Add(false);
   for(int i=1;i<rev.Count;i++){all.Add(rev[i]);dir.Add(true);}
   t.mode=Mode.Backing;t.path=all;t.reverse=dir;t.along=0;t.length=Length(all);
  }

  void Go(Truck t,Mode mode,List<Vector3> path,bool reverse){
   t.mode=mode;t.path=path;t.reverse=new List<bool>();for(int i=0;i<path.Count;i++)t.reverse.Add(reverse);
   t.along=0;t.length=Length(path);
  }

  static float Length(List<Vector3> p){float l=0;for(int i=1;i<p.Count;i++)l+=Vector3.Distance(p[i-1],p[i]);return l;}

  // Catmull-Rom through the points (a dozen steps per span): trucks turn in curves, not corners.
  static List<Vector3> Smooth(List<Vector3> p){
   var o=new List<Vector3>();if(p.Count<3){o.AddRange(p);return o;}
   for(int i=0;i<p.Count-1;i++){
    var p0=p[Mathf.Max(0,i-1)];var p1=p[i];var p2=p[i+1];var p3=p[Mathf.Min(p.Count-1,i+2)];
    for(int k=0;k<12;k++){float u=k/12f,u2=u*u,u3=u2*u;o.Add(.5f*((2*p1)+(-p0+p2)*u+(2*p0-5*p1+4*p2-p3)*u2+(-p0+3*p1-3*p2+p3)*u3));}
   }
   o.Add(p[p.Count-1]);return o;
  }

  float nextPaint;
  void Update(){
   foreach(var t in trucks.Values){
    if(!t.model)continue;
    switch(t.mode){
     case Mode.Leaving:case Mode.Arriving:case Mode.Backing:
      Drive(t,Time.deltaTime);
      if(t.along>=t.length){
       if(t.mode==Mode.Leaving)Away(t);
       else if(t.mode==Mode.Arriving){t.mode=Mode.Refuelling;t.timer=RefuelSeconds;}
       else Park(t);
      }
      break;
     case Mode.Refuelling:
      t.timer-=Time.deltaTime;if(t.timer<=0)Back(t);break;
    }
   }
   if(Time.unscaledTime>nextPaint){nextPaint=Time.unscaledTime+1f;foreach(var t in trucks.Values)if(t.model&&t.model.gameObject.activeInHierarchy)CheckoutMarketPaint.Touch(t.model.gameObject);}
  }

  void Drive(Truck t,float dt){
   // slower when reversing and on the first / last metres
   float edge=Mathf.Min(t.along,t.length-t.along);
   float v=Speed*Mathf.Lerp(.35f,1f,Mathf.Clamp01(edge/4f));
   int seg=Segment(t,t.along);if(t.reverse[Mathf.Min(seg+1,t.reverse.Count-1)])v*=.55f;
   t.along=Mathf.Min(t.length,t.along+v*dt);
   var p=Point(t,t.along,out int s,out Vector3 tangent);
   bool rev=t.reverse[Mathf.Min(s+1,t.reverse.Count-1)];
   var nose=rev?tangent:-tangent;   // the model's nose is −Z: it looks back along its way when reversing
   nose.y=0;
   t.model.position=p;
   if(nose.sqrMagnitude>1e-4f)t.model.rotation=Quaternion.Slerp(t.model.rotation,Quaternion.LookRotation(nose,Vector3.up),Mathf.Clamp01(dt*10f));
  }
  static int Segment(Truck t,float d){float acc=0;for(int i=1;i<t.path.Count;i++){float l=Vector3.Distance(t.path[i-1],t.path[i]);if(acc+l>=d)return i-1;acc+=l;}return t.path.Count-2;}
  static Vector3 Point(Truck t,float d,out int seg,out Vector3 tangent){
   float acc=0;
   for(int i=1;i<t.path.Count;i++){
    float l=Vector3.Distance(t.path[i-1],t.path[i]);
    if(acc+l>=d||i==t.path.Count-1){seg=i-1;tangent=(t.path[i]-t.path[i-1]).normalized;return Vector3.Lerp(t.path[i-1],t.path[i],l>0?Mathf.Clamp01((d-acc)/l):1);}
    acc+=l;
   }
   seg=0;tangent=Vector3.forward;return t.path[0];
  }

  /// <summary>QA: a parked truck goes out and comes straight back (street → pump → its bay), to film the yard.</summary>
  public bool QaRoundTrip(string id){
   if(!trucks.TryGetValue(id,out var t)||t.mode!=Mode.Parked)return false;
   Arrive(t);t.model.position=W(StreetX+6,LaneIn);return true;
  }
  public bool QaLeave(string id){if(!trucks.TryGetValue(id,out var t)||t.mode!=Mode.Parked)return false;Leave(t);return true;}
  public string QaMode(string id)=>trucks.TryGetValue(id,out var t)?t.mode.ToString():"-";
  /// <summary>QA: each truck's id, mode and bay.</summary>
  public string Describe(){var parts=new List<string>();foreach(var t in trucks.Values)parts.Add($"{t.id}:{t.mode}@{t.bay}");return string.Join(" ",parts);}
  public Transform TruckModel(string id)=>trucks.TryGetValue(id,out var t)?t.model:null;
  public Vector3 BayPosition(int i)=>W(Bays[Mathf.Clamp(i,0,Bays.Length-1)],TruckY);
  public static Vector3 PumpPosition=>W(PumpStop.x,PumpStop.y);

  void OnDestroy(){if(Current==this)Current=null;}
 }
}
