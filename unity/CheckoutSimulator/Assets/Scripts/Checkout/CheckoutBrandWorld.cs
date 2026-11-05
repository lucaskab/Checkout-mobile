using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Rede de supermercados: the chain's name and logo on the building once the player named it. The hipermercado's
 // dressing (CheckoutMarketStagesBuilder Stage4) already carries the big gold letters on the back facade with a round
 // cart logo, the glass canopy's fascia and the lit totem: their words become the chain's name and the cart becomes
 // the player's logo on a cream badge. Everything goes back to how it was when the brand goes away (dev jumps).
 // The chain's name is the player's own text: it is never translated (CheckoutSignText only touches "Portal label").
 public sealed class CheckoutBrandWorld : MonoBehaviour {
  static CheckoutBrandWorld instance;
  Transform world;
  int applied=-1;
  readonly Dictionary<TextMesh,(string text,float size)> original=new Dictionary<TextMesh,(string,float)>();
  readonly Dictionary<Transform,Vector3> logoPositions=new Dictionary<Transform,Vector3>();
  Material badgeMaterial;
  Texture2D badge;

  public static void Ensure(Transform world){
   if(!instance)instance=new GameObject("Brand World").AddComponent<CheckoutBrandWorld>();
   instance.world=world;instance.Refresh();
  }
  /// <summary>QA: what the last dressing did.</summary>
  public static string Report{get;private set;}="";

  void Update(){Refresh();}
  void Refresh(){
   // the dressing is rebuilt / re-enabled by stage changes: look again now and then even without a brand change
   if(applied==CheckoutBrand.Version&&Time.frameCount%120!=0)return;
   applied=CheckoutBrand.Version;Dress();
  }

  Transform Dressing()=>world?world.Find("Market Stage Dressing"):null;

  void Dress(){
   var root=Dressing();if(!root)return;
   bool on=CheckoutBrand.Named&&!string.IsNullOrEmpty(CheckoutBrand.Name);
   string name=CheckoutBrand.Name.ToUpperInvariant();
   int changed=0;
   // the big letters and the round logo on the back facade
   var letters=root.Find("S4 name");
   if(letters){
    string before=null;
    foreach(var t in letters.GetComponentsInChildren<TextMesh>(true)){before??=Remember(t).text;changed+=Set(t,on?name:Remember(t).text,Remember(t).size);}
    Logo(letters,on,before??"HIPERMERCADO",name);
   }
   // the glass canopy's fascia over the entrance
   var canopy=root.Find("S4 glass canopy");
   if(canopy)foreach(var t in canopy.GetComponentsInChildren<TextMesh>(true))changed+=Set(t,on?name:Remember(t).text,Remember(t).size);
   // the lit totem by the car park: short words only (it is narrow)
   var totem=root.Find("S4 totem");
   if(totem)foreach(var t in totem.GetComponentsInChildren<TextMesh>(true)){var o=Remember(t);changed+=Set(t,on?name:o.text,on?o.size*Mathf.Min(1f,5f/Mathf.Max(5,name.Length)):o.size);}
   Report=$"brand {(on?name:"-")} texts {changed}";
  }

  (string text,float size) Remember(TextMesh t){
   if(!original.TryGetValue(t,out var o)){o=(t.text,t.characterSize);original[t]=o;}
   return o;
  }
  static int Set(TextMesh t,string text,float size){
   if(t.text==text&&Mathf.Approximately(t.characterSize,size))return 0;
   t.text=text;t.characterSize=size;return 1;
  }

  // The cart logo sits left of the letters (x = -(letters·h·.19 + h·.45), h = 2.4 m, as the builder placed it): it follows
  // the name's length and turns into the player's logo on a cream badge.
  void Logo(Transform letters,bool on,string oldText,string name){
   const float h=2.4f;
   float oldX=-(oldText.Length*h*.19f+h*.45f),newX=-(name.Length*h*.19f+h*.45f);
   Transform face=null;
   foreach(Transform c in letters){
    if(!c.name.StartsWith("Logo")&&!c.name.StartsWith("Cart"))continue;
    if(!logoPositions.ContainsKey(c))logoPositions[c]=c.localPosition;
    var p=logoPositions[c];c.localPosition=on?new Vector3(p.x+newX-oldX,p.y,p.z):p;
    if(c.name.StartsWith("Cart"))c.gameObject.SetActive(!on);
    if(c.name=="Logo face")face=c;
   }
   var badgeQuad=letters.Find("Brand badge");
   if(!on){if(badgeQuad)badgeQuad.gameObject.SetActive(false);return;}
   if(!face)return;
   if(!badgeQuad){
    var go=GameObject.CreatePrimitive(PrimitiveType.Quad);go.name="Brand badge";
    var col=go.GetComponent<Collider>();if(col)Destroy(col);
    go.transform.SetParent(letters,false);badgeQuad=go.transform;
    var r=go.GetComponent<MeshRenderer>();r.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
   }
   badgeQuad.gameObject.SetActive(true);
   badgeQuad.localPosition=face.localPosition+new Vector3(0,0,-.03f);
   badgeQuad.localRotation=Quaternion.identity;
   float d=h*.58f;badgeQuad.localScale=new Vector3(d,d,1);
   var mr=badgeQuad.GetComponent<MeshRenderer>();
   if(!badgeMaterial){var shader=Shader.Find("Sprites/Default");badgeMaterial=new Material(shader){name="Brand badge"};}
   badgeMaterial.mainTexture=Badge();mr.sharedMaterial=badgeMaterial;
  }

  // The logo on a round cream plate (the facade's logo disc is navy: the emblem's main colour would vanish on it).
  int badgeVersion=-1;
  Texture2D Badge(){
   if(badge&&badgeVersion==CheckoutBrand.Version)return badge;
   badgeVersion=CheckoutBrand.Version;
   var logo=CheckoutBrand.Logo;const int n=256;
   if(!badge)badge=new Texture2D(n,n,TextureFormat.RGBA32,true){name="Brand badge",wrapMode=TextureWrapMode.Clamp};
   var px=new Color[n*n];var cream=new Color(.984f,.973f,.945f,1);
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){
    float dx=x+.5f-n/2f,dy=y+.5f-n/2f,dist=Mathf.Sqrt(dx*dx+dy*dy);
    float a=Mathf.Clamp01(n/2f-1-dist);var c=cream;c.a=a;
    if(logo&&logo.isReadable){float u=(dx/(n*.72f))+.5f,v=(dy/(n*.72f))+.5f;if(u>=0&&u<=1&&v>=0&&v<=1){var e=logo.GetPixelBilinear(u,v);c=Color.Lerp(c,new Color(e.r,e.g,e.b,a),e.a);}}
    px[y*n+x]=c;
   }
   badge.SetPixels(px);badge.Apply(true,false);return badge;
  }

  void OnDestroy(){if(badge)Destroy(badge);if(badgeMaterial)Destroy(badgeMaterial);}
 }
}
