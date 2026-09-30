using System.Collections.Generic;
using MarketDay;
using UnityEngine;

namespace Checkout {
 // Storefront entrance art: a Blender portal (pillars, header with the MERCADO board, striped awning,
 // lanterns, threshold and welcome mat) and a flight of steps from the sidewalk to the shop floor.
 // Both follow the projected door frame, so every market level gets an entrance that meets the floor.
 // The old primitive jambs and the flat concrete slab stay in the scene (layout and navigation still
 // read them) but are no longer drawn. Models: scripts/blender/build_event_props.py (MarketPortal, MarketSteps).
 public sealed class CheckoutEntranceDressing:MonoBehaviour {
  const float Floor=.74f,Sidewalk=.15f,PortalWidth=3.78f,PortalHeight=2.76f,StepsLength=1.5f;
  readonly CheckoutEventAssets art=new CheckoutEventAssets();
  readonly List<Renderer> frame=new List<Renderer>();
  Transform world,root,portal,steps;Bounds last;bool doorwayCleared;

  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Boot(){if(!FindAnyObjectByType<MarketSimulation>()||FindAnyObjectByType<CheckoutEntranceDressing>()||FindAnyObjectByType<CheckoutMarketShell>(FindObjectsInactive.Include))return; // the market shell builds its own entrance
  new GameObject("Checkout Entrance Dressing").AddComponent<CheckoutEntranceDressing>();}

  bool Setup(){
   var simulation=FindAnyObjectByType<MarketSimulation>();world=simulation?simulation.world:null;if(!world)return false;
   var clean=Find(world,"Clean entrance frame");if(!clean)return false;
   foreach(var r in clean.GetComponentsInChildren<Renderer>(true)){frame.Add(r);r.forceRenderingOff=true;}
   var slab=Find(world,"Continuous entrance approach");if(slab)foreach(var r in slab.GetComponentsInChildren<Renderer>(true))r.forceRenderingOff=true;
   root=new GameObject("Market entrance").transform;root.SetParent(world,false);
   portal=art.Model(root,"MarketPortal",Vector3.zero,0);
   steps=art.Model(root,"MarketSteps",Vector3.zero,0);
   return true;}

  static Transform Find(Transform parent,string name){foreach(var t in parent.GetComponentsInChildren<Transform>(true))if(t.name==name)return t;return null;}

  void LateUpdate(){
   if(!root&&!Setup())return;
   var b=FrameBounds();if(b.size.sqrMagnitude<.01f)return;
   if((b.center-last.center).sqrMagnitude<1e-6f&&(b.size-last.size).sqrMagnitude<1e-6f)return;
   last=b;Place(b);}

  Bounds FrameBounds(){var has=false;var b=new Bounds();foreach(var r in frame){if(!r||!r.gameObject.activeInHierarchy)continue;if(!has){b=r.bounds;has=true;}else b.Encapsulate(r.bounds);}return b;}

  void Place(Bounds door){
   float width=door.size.x/PortalWidth,front=door.min.z;
   portal.position=new Vector3(door.center.x,Floor,front);
   portal.localScale=new Vector3(width,Mathf.Max(.6f,(door.max.y-Floor)/PortalHeight),1);
   // The flight always starts at the store anchor on the sidewalk, as the navigation ramp does.
   float length=Mathf.Max(.7f,front-CheckoutMarketLayout.Anchor.z);
   steps.position=new Vector3(door.center.x,Floor,front);
   steps.localScale=new Vector3(width,(Floor-Sidewalk)/.59f,length/StepsLength);
   if(!doorwayCleared)ClearDoorway(door);
   Debug.Log($"CHECKOUT_ENTRANCE_OK door={door.center:F2} size={door.size:F2} steps={length:F2}");}

  // The supplied building mesh keeps a few torn triangles of its old door inside the opening; drop them.
  void ClearDoorway(Bounds door){
   doorwayCleared=true;var building=world.Find("Building");var filter=building?building.GetComponent<MeshFilter>():null;
   if(!filter||!filter.sharedMesh||!filter.sharedMesh.isReadable)return;
   var mesh=Instantiate(filter.sharedMesh);mesh.name=filter.sharedMesh.name+" (open doorway)";
   var vertices=mesh.vertices;var toWorld=building.localToWorldMatrix;
   var cut=new Bounds();cut.SetMinMax(new Vector3(door.min.x+.12f,Floor+.06f,door.min.z-.4f),new Vector3(door.max.x-.12f,door.max.y+.2f,door.max.z+.9f));
   int removed=0;
   for(int s=0;s<mesh.subMeshCount;s++){
    var source=mesh.GetTriangles(s);var kept=new List<int>(source.Length);
    for(int i=0;i<source.Length;i+=3){
     var c=toWorld.MultiplyPoint3x4((vertices[source[i]]+vertices[source[i+1]]+vertices[source[i+2]])/3);
     if(cut.Contains(c)){removed++;continue;}
     kept.Add(source[i]);kept.Add(source[i+1]);kept.Add(source[i+2]);}
    mesh.SetTriangles(kept,s);}
   if(removed>0)filter.sharedMesh=mesh;else Destroy(mesh);
   Debug.Log("CHECKOUT_ENTRANCE_DOORWAY_CLEARED triangles="+removed);}
 }
}
