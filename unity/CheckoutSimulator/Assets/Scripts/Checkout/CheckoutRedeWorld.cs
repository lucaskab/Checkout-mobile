using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Rede de supermercados in the world (Lucas 06/11 "Aprovado", part 1):
 //  * the distribution centre (Resources/Rede/RedeDC) stands where the hipermercado's central warehouse was, once the
 //    chain is unlocked: the old building's renderers hide (its colliders stay: tapping it still opens the storage),
 //    the DC's docks face the yard's three bays (y −1.45 / +1.55 / +4.55 of its centre) and the supplier trucks back
 //    onto its dock bumpers (CheckoutDeliveryTrucks.GrandShift);
 //  * the fleet: a delivery that comes through the distribution centre (order.fleetTruckId) arrives in one of the
 //    chain's own trucks (dry or refrigerated) instead of a supplier's, and a truck leaving on a contract or a branch run
 //    comes to the dock first and drives off loaded (CheckoutMap.UpdateSupplierDeliveries).
 // Everything goes back to the old warehouse when the chain goes away (dev jumps).
 public sealed class CheckoutRedeWorld:MonoBehaviour {
  public static CheckoutRedeWorld Current{get;private set;}
  // The DC's half width and its dock face (bumpers) east of its centre, metres (scripts/blender/rede_dc.py W2 + .2).
  const float HalfWidth=9.2f,DockFace=9.45f;
  // The supplier trucks' tails at the old warehouse (the hipermercado yard's bays): x −0.39.
  const float OldRearX=-.39f;
  Transform world,dc;
  readonly List<Renderer> hidden=new List<Renderer>();
  bool on;
  Bounds oldBounds;bool measured;
  /// <summary>QA: what the last change did.</summary>
  public static string Report{get;private set;}="";

  public static void Ensure(Transform world,Snapshot s){
   if(!Current)Current=new GameObject("Rede World").AddComponent<CheckoutRedeWorld>();
   Current.world=world;Current.Apply(s);
  }

  void Apply(Snapshot s){
   var grand=world?world.Find(CheckoutMarketLayout.GrandWarehouse):null;
   bool want=s!=null&&s.chain!=null&&s.chain.unlocked&&s.layout!=null&&s.layout.storageLarge&&grand&&grand.gameObject.activeInHierarchy&&Resources.Load<GameObject>("Rede/RedeDC");
   if(want==on)return;
   on=want;
   if(on)Show(grand);else Hide();
  }

  void Show(Transform grand){
   if(!measured){
    bool any=false;
    foreach(var r in grand.GetComponentsInChildren<Renderer>(true)){
     if(r is ParticleSystemRenderer)continue;
     if(!any){oldBounds=r.bounds;any=true;}else oldBounds.Encapsulate(r.bounds);
    }
    measured=any;
    if(!any)oldBounds=new Bounds(new Vector3(-6.85f,4,31.85f),new Vector3(18.4f,8,18));
   }
   hidden.Clear();
   foreach(var r in grand.GetComponentsInChildren<Renderer>(false)){if(!r.enabled||r is ParticleSystemRenderer)continue;r.enabled=false;hidden.Add(r);}
   if(!dc)dc=CheckoutRedeModels.Spawn("RedeDC",grand,"Rede DC");
   dc.gameObject.SetActive(true);
   // The old building's west edge + the DC's half width + .45 (its fire stair stays on the lot, off the sidewalk).
   var c=new Vector3(oldBounds.min.x+HalfWidth+.45f,oldBounds.min.y,oldBounds.center.z);
   dc.position=c;dc.rotation=Quaternion.identity;
   CheckoutDeliveryTrucks.GrandShift=c.x+DockFace+.1f-OldRearX;
   CheckoutDeliveryTrucks.Current?.Reconfigure();
   ShowGate();Totem(true);
   Report=$"dc on at ({c.x:0.00},{c.z:0.00}) old warehouse x[{oldBounds.min.x:0.0},{oldBounds.max.x:0.0}] z[{oldBounds.min.z:0.0},{oldBounds.max.z:0.0}] hid {hidden.Count} renderers, truck shift {CheckoutDeliveryTrucks.GrandShift:0.00}";
  }

  void Hide(){
   foreach(var r in hidden)if(r)r.enabled=true;
   hidden.Clear();
   if(dc)dc.gameObject.SetActive(false);
   if(gate)gate.gameObject.SetActive(false);
   Totem(false);
   CheckoutDeliveryTrucks.GrandShift=0;
   CheckoutDeliveryTrucks.Current?.Reconfigure();
   Report="dc off";
  }

  // ------------------------------------------------------------------ the truck gate and the totem
  // The guard booth with its barrier stands on the north side of the yard's driveway from the east street (z 31.3–35.6):
  // the arm closes the driveway southwards and lifts for every truck that comes near.
  static readonly Vector3 GatePosition=new Vector3(18.8f,.13f,36.9f);
  Transform gate,arm;float armAngle;
  void ShowGate(){
   if(!gate){
    gate=CheckoutRedeModels.Spawn("RedeGatehouse",world,"Rede gatehouse");
    // the arm was exported in the model's space: a pivot at its hinge (Blender (1.3, −1.2, 1.08))
    var mesh=gate.GetComponentsInChildren<MeshFilter>(true);
    foreach(var mf in mesh)if(mf.name.Contains("Arm")){
     var pivot=new GameObject("Arm pivot").transform;pivot.SetParent(gate,false);pivot.localPosition=new Vector3(1.3f,1.08f,-1.2f);
     mf.transform.SetParent(pivot,true);arm=pivot;break;
    }
   }
   gate.gameObject.SetActive(true);
   gate.SetPositionAndRotation(GatePosition,Quaternion.Euler(0,90,0));
  }
  void UpdateGate(){
   if(!gate||!gate.gameObject.activeInHierarchy||!arm)return;
   bool open=false;var trucks=CheckoutDeliveryTrucks.Current;
   if(trucks)foreach(var t in trucks.All)if(t&&t.gameObject.activeInHierarchy&&(t.position-GatePosition).sqrMagnitude<11f*11f)open=true;
   armAngle=Mathf.MoveTowards(armAngle,open?82:0,Time.deltaTime*70);
   arm.localRotation=Quaternion.Euler(0,0,armAngle);
  }

  // The hipermercado's lit totem by the car park becomes the chain's (Resources/Rede/RedeTotem) where it stood.
  Transform totem,oldTotem;readonly List<Renderer> totemHidden=new List<Renderer>();float nextTotem;
  void Totem(bool show){
   var dressing=world?world.Find("Market Stage Dressing"):null;
   var t=dressing?dressing.Find("S4 totem"):null;
   if(!show||!t||!t.gameObject.activeInHierarchy){
    foreach(var r in totemHidden)if(r)r.enabled=true;totemHidden.Clear();
    if(totem)totem.gameObject.SetActive(false);return;
   }
   if(oldTotem!=t){foreach(var r in totemHidden)if(r)r.enabled=true;totemHidden.Clear();oldTotem=t;}
   foreach(var r in t.GetComponentsInChildren<Renderer>(false))if(r.enabled){r.enabled=false;totemHidden.Add(r);}
   if(!totem)totem=CheckoutRedeModels.Spawn("RedeTotem",world,"Rede totem");
   totem.gameObject.SetActive(true);
   var p=t.position;p.y=.13f;
   totem.SetPositionAndRotation(p,Quaternion.Euler(0,t.eulerAngles.y,0));
  }

  // ------------------------------------------------------------------ the fleet's trucks
  sealed class Skin{public Transform model;public string kind;public readonly List<Renderer> own=new List<Renderer>();}
  readonly Dictionary<Transform,Skin> skins=new Dictionary<Transform,Skin>();

  /// <summary>Dress a supplier truck as one of the chain's trucks ("seco" / "refrigerado"), or back as itself (null).</summary>
  public void Dress(Transform truck,string kind){
   if(!truck)return;
   skins.TryGetValue(truck,out var skin);
   string current=skin!=null&&skin.model&&skin.model.gameObject.activeSelf?skin.kind:null;
   if(current==kind)return;
   if(skin==null){skin=new Skin();skins[truck]=skin;}
   if(skin.model&&skin.kind!=kind){Destroy(skin.model.gameObject);skin.model=null;}
   if(kind!=null&&!skin.model){
    skin.kind=kind;
    skin.model=CheckoutRedeModels.Spawn(kind=="refrigerado"?"FleetTruck_Reefer":"FleetTruck_Dry",truck,"Fleet skin");
    Fit(truck,skin.model);
   }
   if(skin.own.Count==0)foreach(var r in truck.GetComponentsInChildren<Renderer>(true))if(!skin.model||!r.transform.IsChildOf(skin.model))skin.own.Add(r);
   bool fleet=kind!=null;
   foreach(var r in skin.own)if(r)r.enabled=!fleet;
   if(skin.model)skin.model.gameObject.SetActive(fleet);
  }
  public static string KindOf(Snapshot s,string truckId){
   if(s?.chain?.trucks==null||string.IsNullOrEmpty(truckId))return null;
   foreach(var t in s.chain.trucks)if(t!=null&&t.id==truckId)return t.kind=="refrigerado"?"refrigerado":"seco";
   return "seco";
  }

  // The chain's truck in real metres on the supplier truck's footprint: tail on its tail, wheels on its wheels, facing
  // the way it drives (+Z); the Blender truck faces −Z, so it turns round.
  static void Fit(Transform truck,Transform model){
   var ls=truck.lossyScale;
   model.localScale=new Vector3(1/Mathf.Max(.0001f,ls.x),1/Mathf.Max(.0001f,ls.y),1/Mathf.Max(.0001f,ls.z));
   model.localRotation=Quaternion.Euler(0,180,0);model.localPosition=Vector3.zero;
   var own=Box(truck,truck,model,false);var fleet=Box(truck,model,null,true);
   model.localPosition+=new Vector3(own.center.x-fleet.center.x,own.min.y-fleet.min.y,own.min.z-fleet.min.z);
  }
  static Bounds Box(Transform space,Transform root,Transform skip,bool only){
   bool first=true;var box=new Bounds();
   void Add(Mesh mesh,Transform part){
    if(!mesh||(!only&&skip&&part.IsChildOf(skip)))return;var b=mesh.bounds;
    for(int i=0;i<8;i++){
     var c=new Vector3((i&1)==0?b.min.x:b.max.x,(i&2)==0?b.min.y:b.max.y,(i&4)==0?b.min.z:b.max.z);
     var l=space.InverseTransformPoint(part.TransformPoint(c));
     if(first){box=new Bounds(l,Vector3.zero);first=false;}else box.Encapsulate(l);
    }
   }
   foreach(var mf in root.GetComponentsInChildren<MeshFilter>(true))Add(mf.sharedMesh,mf.transform);
   foreach(var sm in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))Add(sm.sharedMesh,sm.transform);
   return box;
  }

  // The chain's trucks drive outside the market roots the paint watches: they follow the colours from here.
  float nextPaint;
  void Update(){
   UpdateGate();
   // the dressing is shown again by stage changes: the old totem stays hidden
   if(on&&Time.unscaledTime>nextTotem){nextTotem=Time.unscaledTime+2f;Totem(true);}
   if(Time.unscaledTime<nextPaint)return;nextPaint=Time.unscaledTime+1f;
   foreach(var s in skins.Values)if(s.model&&s.model.gameObject.activeInHierarchy)CheckoutMarketPaint.Touch(s.model.gameObject);
  }

  void OnDestroy(){if(Current==this)Current=null;}
 }
}
