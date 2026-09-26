using UnityEngine;

namespace Checkout {
 // Speech bubble over a customer who needs the player: a special request (what they want) or a
 // full basket waiting at the register. Icon, patience bar and, once handled, how it went.
 // Clicking it opens the request (app/HUD) or the register mini-game.
 public sealed class CheckoutRequestBubble:MonoBehaviour {
  const float Height=2.45f;
  static CheckoutEventAssets art;
  Transform owner,fill,track,pulse;SpriteRenderer icon;Renderer fillRenderer;CheckoutTarget target;Collider hit;
  string shownKey;float hideAt;double start,end;bool pending;

  public static CheckoutRequestBubble For(Transform walker){
   foreach(var existing in FindObjectsByType<CheckoutRequestBubble>(FindObjectsInactive.Include))if(existing.owner==walker)return existing;
   var go=new GameObject("Request bubble · "+walker.name);var bubble=go.AddComponent<CheckoutRequestBubble>();bubble.owner=walker;bubble.Build();go.SetActive(false);return bubble;
  }

  void Build(){
   art??=new CheckoutEventAssets();
   pulse=new GameObject("Pulse").transform;pulse.SetParent(transform,false);
   art.Part(pulse,"Bubble edge",new Vector3(0,0,.012f),new Vector3(.74f,.6f,.03f),"4A3624");
   art.Part(pulse,"Bubble",Vector3.zero,new Vector3(.68f,.54f,.04f),"FFF7EC");
   var tail=art.Part(pulse,"Tail",new Vector3(0,-.3f,.004f),new Vector3(.16f,.16f,.035f),"FFF7EC");tail.localRotation=Quaternion.Euler(0,0,45);
   track=art.Part(pulse,"Timer track",new Vector3(0,-.19f,-.03f),new Vector3(.5f,.06f,.02f),"EADBC4");
   fill=art.Part(pulse,"Timer",new Vector3(0,-.19f,-.042f),new Vector3(.5f,.06f,.02f),"5DA637");fillRenderer=fill.GetComponent<Renderer>();
   var iconGo=new GameObject("Icon");iconGo.transform.SetParent(pulse,false);iconGo.transform.localPosition=new Vector3(0,.05f,-.05f);
   icon=iconGo.AddComponent<SpriteRenderer>();icon.sortingOrder=5;
   // A generous click area; the bridge raycasts CheckoutTarget colliders on world clicks.
   var box=gameObject.AddComponent<BoxCollider>();box.size=new Vector3(.95f,.9f,.3f);hit=box;
   target=gameObject.AddComponent<CheckoutTarget>();
  }

  void SetIcon(string name){
   var sprite=CheckoutDesktopKit.Icon("Icons/"+name);icon.sprite=sprite;
   if(sprite){var size=Mathf.Max(sprite.bounds.size.x,sprite.bounds.size.y);icon.transform.localScale=Vector3.one*(.34f/Mathf.Max(.001f,size));}
  }

  // Waiting: icon plus a patience bar running from start to end (epoch ms). panel/id go to the click.
  public void Show(string key,string iconName,double from,double until,string panel,string id){
   if(shownKey!=key||!pending){shownKey=key;pending=true;SetIcon(iconName);target.panel=panel;target.requestId=id;track.gameObject.SetActive(true);fill.gameObject.SetActive(true);hit.enabled=true;}
   start=from;end=until;hideAt=float.MaxValue;gameObject.SetActive(true);
  }
  // Handled: a short success or warning icon, then the bubble goes away.
  public void Resolve(string key,bool good){
   if(!pending||shownKey!=key)return;
   pending=false;SetIcon(good?"success":"warning");track.gameObject.SetActive(false);fill.gameObject.SetActive(false);hit.enabled=false;hideAt=Time.time+2.5f;
  }
  public void Hide(){if(pending){pending=false;gameObject.SetActive(false);}}

  static string KindIcon(string kind)=>kind=="produto"?"basket":kind=="alternativa"?"handshake":"customers";
  // Special request of this customer, from the snapshot (null when there is none).
  public void Apply(DayRequest request){
   if(request==null)return;
   if(request.status=="pending")Show(request.id,KindIcon(request.kind),request.createdAt,request.expiresAt,"requests",request.id);
   else Resolve(request.id,request.status=="served"||request.status=="partial");
  }

  void Update(){
   if(!pending){if(gameObject.activeSelf&&Time.time>hideAt)gameObject.SetActive(false);return;}
   float total=(float)System.Math.Max(1,end-start),left=(float)System.Math.Max(0,end-CheckoutBridge.Now),ratio=Mathf.Clamp01(left/total);
   fill.localScale=new Vector3(.5f*ratio,.06f,.02f);fill.localPosition=new Vector3(-.25f+.25f*ratio,-.19f,-.042f);
   fillRenderer.material.color=Color.Lerp(CheckoutDesktopKit.C("E15533"),CheckoutDesktopKit.C("5DA637"),Mathf.InverseLerp(.15f,.5f,ratio));
  }

  void LateUpdate(){
   if(!owner||!owner.gameObject.activeInHierarchy){gameObject.SetActive(false);pending=false;return;}
   transform.position=owner.position+Vector3.up*Height;
   if(Camera.main)transform.rotation=Camera.main.transform.rotation;
   // A gentle bob; nearly-out-of-patience customers pulse faster.
   bool urgent=pending&&fill.localScale.x<.5f*.3f;
   pulse.localPosition=new Vector3(0,Mathf.Sin(Time.time*(urgent?9:3))*.04f,0);
   pulse.localScale=Vector3.one*(urgent?1+Mathf.Sin(Time.time*9)*.05f:1);
  }
 }
}
