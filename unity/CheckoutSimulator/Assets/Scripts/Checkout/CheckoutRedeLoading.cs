using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Rede (Lucas 06/11: "eu quero que tenha uma animação ali também de carregando os caminhões"): a fleet truck backed
 // onto one of the distribution centre's docks is loaded before it leaves on a contract or a branch run. A loader (a copy
 // of the delivery worker: same clothes, the chain's badge, the same carry clips) comes out of the dock's open door
 // with a box, puts it into the truck's tail, goes back in for the next one, and so on for the loading time; then
 // goes back in and the truck can go. Presentation only.
 public sealed class CheckoutRedeLoading {
  sealed class Loader {
   public int dock;public Transform body,cargo,left,right;public Animation anim;
   public Vector3 inside,outside,facing;public float until,clock,clock2,wait;public int step;public string clip;public bool carrying,leaving,done;
   public Vector3 cargoScale;public Transform cargoParent;
  }
  readonly List<Loader> loaders=new List<Loader>();
  public int Active{get{int n=0;foreach(var l in loaders)if(!l.done)n++;return n;}}

  /// <summary>Starts loading the truck at dock `dock`: `tail` is the middle of its tail, `facing` points from the wall
  /// to the truck.</summary>
  public void Start(int dock,Transform truck,Vector3 tail,Vector3 facing,float seconds){
   Stop(dock);
   var template=Object.FindAnyObjectByType<MarketDay.MarketDeliveryWorker>(FindObjectsInactive.Include);
   var l=new Loader{dock=dock,facing=facing,until=seconds};
   // inside the dock's door (the dark loading bay) and just behind the truck's tail, in the gap to the wall
   l.inside=tail-facing*(.8f+1.2f);l.outside=tail-facing*.42f;
   l.inside.y=l.outside.y=.15f;
   if(template){
    var go=Object.Instantiate(template.gameObject,template.transform.parent);
    go.name="Worker_Loader "+dock;
    var w=go.GetComponent<MarketDay.MarketDeliveryWorker>();
    l.anim=w?w.animationPlayer:go.GetComponentInChildren<Animation>();l.cargo=w?w.cargo:null;l.left=w?w.leftHand:null;l.right=w?w.rightHand:null;
    // The delivery worker's parcel lives outside its body between trips: the copy's reference would still point at the
    // worker's own parcel (moving it, and destroying it with the copy). The loader carries a parcel of its own.
    if(l.cargo&&!l.cargo.IsChildOf(go.transform)){var own=Object.Instantiate(l.cargo.gameObject,go.transform);own.name="Loader parcel";l.cargo=own.transform;}
    if(l.left&&!l.left.IsChildOf(go.transform))l.left=null;
    if(l.right&&!l.right.IsChildOf(go.transform))l.right=null;
    if(!l.left||!l.right)foreach(var b in go.GetComponentsInChildren<Transform>(true)){if(b.name=="Hand_L")l.left=b;else if(b.name=="Hand_R")l.right=b;}
    foreach(var mb in go.GetComponentsInChildren<MonoBehaviour>(true))Object.DestroyImmediate(mb);
    foreach(var b in go.GetComponentsInChildren<UnityEngine.AI.NavMeshAgent>(true))b.enabled=false;
    foreach(var r in go.GetComponentsInChildren<Renderer>(true))if(!l.cargo||!r.transform.IsChildOf(l.cargo))r.enabled=true;
    l.body=go.transform;
    if(l.cargo){l.cargoParent=l.cargo.parent;l.cargoScale=l.cargo.localScale;l.cargo.gameObject.SetActive(false);}
    l.body.position=l.inside;l.body.rotation=Quaternion.LookRotation(facing,Vector3.up);
    go.SetActive(true);
    l.wait=1.0f;   // the door rolls up first
    Pick(l);
   }else l.done=false;
   loaders.Add(l);
  }

  /// <summary>Whether the loading at dock `dock` is over (the loader is back inside).</summary>
  public bool Done(int dock){foreach(var l in loaders)if(l.dock==dock)return l.done||!l.body&&l.clock>=l.until;return true;}

  public void Stop(int dock){for(int i=loaders.Count-1;i>=0;i--)if(loaders[i].dock==dock){Kill(loaders[i]);loaders.RemoveAt(i);}}
  public void StopAll(){foreach(var l in loaders)Kill(l);loaders.Clear();}
  static void Kill(Loader l){if(l.body)Object.Destroy(l.body.gameObject);}

  public void Update(float dt){
   for(int i=loaders.Count-1;i>=0;i--){
    var l=loaders[i];
    l.clock+=dt;
    if(!l.body){continue;}
    if(l.done)continue;
    if(l.wait>0){l.wait-=dt;Play(l,"CarryIdle");continue;}
    switch(l.step){
     case 0:   // out of the door with a box
      if(Walk(l,l.outside,dt,true)){l.step=1;l.clock2=0;Play(l,"PutDown");}
      break;
     case 1:   // into the truck
      Face(l,l.facing,dt);l.clock2+=dt;
      if(l.carrying&&l.clock2>=Length(l,"PutDown")*.65f)Drop(l);
      if(l.clock2>=Length(l,"PutDown")){l.step=2;}
      break;
     case 2:   // back in for the next one (or for good)
      if(Walk(l,l.inside,dt,false)){
       if(l.clock>=l.until){l.done=true;l.body.gameObject.SetActive(false);break;}
       l.step=3;l.clock2=0;Play(l,"Pickup");
      }
      break;
     case 3:   // the next box off the pallet
      Face(l,-l.facing,dt);l.clock2+=dt;
      if(!l.carrying&&l.clock2>=Length(l,"Pickup")*.55f)Pick(l);
      if(l.clock2>=Length(l,"Pickup"))l.step=0;
      break;
    }
    if(l.carrying&&l.cargo&&l.left&&l.right){
     l.cargo.position=(l.left.position+l.right.position)*.5f+Vector3.down*.5f+l.body.forward*.08f;
     l.cargo.rotation=l.body.rotation;
    }
   }
  }

  static bool Walk(Loader l,Vector3 to,float dt,bool loaded){
   var d=to-l.body.position;d.y=0;
   if(d.magnitude<.03f){Play(l,loaded?"CarryIdle":"Idle");return true;}
   Face(l,d,dt);
   float speed=1.15f*(loaded?.85f:1f);
   var p=Vector3.MoveTowards(l.body.position,new Vector3(to.x,l.body.position.y,to.z),speed*dt);p.y=Mathf.MoveTowards(p.y,to.y,dt);
   l.body.position=p;Play(l,loaded?"CarryWalking":"Walking");
   return false;
  }
  static void Face(Loader l,Vector3 dir,float dt){dir.y=0;if(dir.sqrMagnitude<1e-4f)return;l.body.rotation=Quaternion.Slerp(l.body.rotation,Quaternion.LookRotation(dir.normalized,Vector3.up),Mathf.Clamp01(dt*8f));}
  static void Pick(Loader l){if(!l.cargo)return;l.carrying=true;l.cargo.gameObject.SetActive(true);l.cargo.SetParent(l.body,true);}
  static void Drop(Loader l){if(!l.cargo)return;l.carrying=false;l.cargo.SetParent(l.cargoParent,true);l.cargo.localScale=l.cargoScale;l.cargo.gameObject.SetActive(false);}
  static float Length(Loader l,string clip)=>l.anim&&l.anim[clip]?l.anim[clip].length:1f;
  static void Play(Loader l,string clip){
   if(!l.anim||l.clip==clip||!l.anim[clip])return;
   l.clip=clip;l.anim[clip].time=0;l.anim.CrossFade(clip,.12f);
  }
 }
}
