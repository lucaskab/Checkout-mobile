using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Rede de supermercados (Lucas 06/11 "Aprovado", part 3): the chain's paper bag (Resources/Rede/RedeBag, its logo on
 // both sides) in the hand of every customer who paid, and the chain's logo on the staff's uniforms once it is named.

 // The bag hangs from the right hand, upright, alongside the leg, from the till to the street.
 public sealed class CheckoutRedeBag:MonoBehaviour {
  Transform bag,hand,head;bool carrying;float size=1;

  public static void Carry(Transform actor,bool on){
   if(!actor)return;
   var b=actor.GetComponent<CheckoutRedeBag>();
   if(!on){if(b)b.Set(false);return;}
   if(!Resources.Load<GameObject>("Rede/RedeBag"))return;
   if(!b)b=actor.gameObject.AddComponent<CheckoutRedeBag>();
   b.Set(true);
  }

  void Set(bool on){
   carrying=on;
   if(on&&!bag){
    var anim=GetComponent<MarketDay.MarketCharacterAnimator>();
    var visual=anim&&anim.animationPlayer?anim.animationPlayer.transform:transform;
    foreach(var t in visual.GetComponentsInChildren<Transform>(true)){if(t.name=="Hand_R")hand=t;else if(t.name=="Head")head=t;}
    bag=CheckoutRedeModels.Spawn("RedeBag",transform,"Rede bag");
    foreach(var r in bag.GetComponentsInChildren<Renderer>(true))r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
   }
   if(bag)bag.gameObject.SetActive(on);
   if(on&&head)size=Mathf.Clamp((head.position.y-transform.position.y)/1.85f,.72f,1.12f);
  }

  void LateUpdate(){
   if(!carrying||!bag||!hand)return;
   var facing=-transform.forward;facing.y=0;if(facing.sqrMagnitude<.01f)facing=Vector3.forward;facing.Normalize();
   var right=Vector3.Cross(Vector3.up,facing).normalized;
   float s=size*1.05f;
   bag.localScale=Vector3.one*s/Mathf.Max(.0001f,transform.lossyScale.y);
   // handles in the hand (the bag is 0.53 m to the top of its handles at scale 1), the bag a little away from the leg
   var side=Mathf.Sign(Vector3.Dot(hand.position-transform.position,right));if(side==0)side=1;
   bag.position=hand.position+Vector3.down*(.5f*s)+right*side*.03f*s;
   bag.rotation=Quaternion.LookRotation(right*side,Vector3.up);
  }
 }

 // The logo on a cream badge on the chest of every member of staff ("Worker_*", not the suppliers' delivery man).
 public sealed class CheckoutRedeUniforms:MonoBehaviour {
  public static CheckoutRedeUniforms Current{get;private set;}
  Transform world,staffRoot;float next;int version=-1;readonly List<Transform> candidates=new List<Transform>();
  readonly Dictionary<Transform,Transform> badges=new Dictionary<Transform,Transform>();
  readonly Dictionary<Transform,(Transform l,Transform r,Transform head)> bones=new Dictionary<Transform,(Transform,Transform,Transform)>();
  static Material badgeMaterial;static Texture2D badge;static int badgeVersion=-1;
  /// <summary>QA: badges shown now.</summary>
  public static int Shown{get;private set;}

  public static void Ensure(Transform world){
   if(!Current)Current=new GameObject("Rede Uniforms").AddComponent<CheckoutRedeUniforms>();
   Current.world=world;
  }

  void Update(){
   if(Time.unscaledTime<next&&version==CheckoutBrand.Version)return;
   next=Time.unscaledTime+2f;version=CheckoutBrand.Version;
   bool on=CheckoutBrand.Named&&world;
   Shown=0;
   candidates.Clear();
   if(world)foreach(Transform w in world)if(w.name.StartsWith("Worker_")&&!w.name.StartsWith("Worker_Delivery"))candidates.Add(w);
   // the stock clerks and cleaners (CheckoutStaff's holder)
   if(!staffRoot){var go=GameObject.Find("Market Staff");staffRoot=go?go.transform:null;}
   if(staffRoot)foreach(Transform w in staffRoot)if(w.GetComponent<MarketDay.MarketCharacterAnimator>())candidates.Add(w);
   foreach(var w in candidates){
    badges.TryGetValue(w,out var b);
    if(!on||!w.gameObject.activeInHierarchy){if(b)b.gameObject.SetActive(false);continue;}
    if(!b){b=Make(w);badges[w]=b;}
    if(!b)continue;
    b.gameObject.SetActive(true);b.GetComponent<MeshRenderer>().sharedMaterial=Material();Shown++;
   }
  }

  Transform Make(Transform worker){
   var anim=worker.GetComponent<MarketDay.MarketCharacterAnimator>();
   var visual=anim&&anim.animationPlayer?anim.animationPlayer.transform:worker;
   Transform l=null,r=null,head=null;
   foreach(var t in visual.GetComponentsInChildren<Transform>(true)){if(t.name=="UpperArm_L")l=t;else if(t.name=="UpperArm_R")r=t;else if(t.name=="Head")head=t;}
   if(!l||!r||!head)return null;
   bones[worker]=(l,r,head);
   var go=GameObject.CreatePrimitive(PrimitiveType.Quad);go.name="Rede uniform badge";
   var col=go.GetComponent<Collider>();if(col)Destroy(col);
   go.transform.SetParent(worker,false);
   var mr=go.GetComponent<MeshRenderer>();mr.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
   return go.transform;
  }

  // On the left of the chest (the wearer's left), in front of the shirt; follows the body every frame.
  void LateUpdate(){
   foreach(var pair in badges){
    var b=pair.Value;if(!b||!b.gameObject.activeSelf||!bones.TryGetValue(pair.Key,out var bn))continue;
    var w=pair.Key;
    var shoulders=(bn.l.position+bn.r.position)*.5f;
    float size=Mathf.Clamp((bn.head.position.y-w.position.y)/1.85f,.6f,1.2f);
    var facing=-w.forward;facing.y=0;if(facing.sqrMagnitude<.01f)continue;facing.Normalize();
    var across=bn.l.position-bn.r.position;across.y=0;
    b.position=shoulders+Vector3.down*.1f*size+facing*.34f*size+across*.1f;
    b.rotation=Quaternion.LookRotation(-facing,Vector3.up);
    b.localScale=Vector3.one*.17f*size/Mathf.Max(.0001f,w.lossyScale.y);
   }
  }

  static Material Material(){
   if(!badgeMaterial)badgeMaterial=new Material(Shader.Find("Sprites/Default")){name="Rede uniform badge"};
   if(badgeVersion!=CheckoutBrand.Version||!badge){badgeVersion=CheckoutBrand.Version;badge=Badge(badge);badgeMaterial.mainTexture=badge;}
   return badgeMaterial;
  }

  // The logo on a round cream plate with a thin gold rim (the uniforms are navy: the emblem would vanish on them).
  static Texture2D Badge(Texture2D into){
   var logo=CheckoutBrand.Logo;const int n=128;
   if(!into)into=new Texture2D(n,n,TextureFormat.RGBA32,true){name="Rede uniform badge",wrapMode=TextureWrapMode.Clamp};
   var px=new Color[n*n];var cream=new Color(.984f,.973f,.945f,1);var rim=Color.Lerp(CheckoutBrand.Accent,Color.white,.1f);
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){
    float dx=x+.5f-n/2f,dy=y+.5f-n/2f,dist=Mathf.Sqrt(dx*dx+dy*dy);
    float a=Mathf.Clamp01(n/2f-1-dist);var c=dist>n/2f-7?rim:cream;c.a=a;
    if(logo&&logo.isReadable){float u=dx/(n*.66f)+.5f,v=dy/(n*.66f)+.5f;if(u>=0&&u<=1&&v>=0&&v<=1){var e=logo.GetPixelBilinear(u,v);c=Color.Lerp(c,new Color(e.r,e.g,e.b,a),e.a);}}
    px[y*n+x]=c;
   }
   into.SetPixels(px);into.Apply(true,false);return into;
  }

  void OnDestroy(){if(Current==this)Current=null;}
 }
}
