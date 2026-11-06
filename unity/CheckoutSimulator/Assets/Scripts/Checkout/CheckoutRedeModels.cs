using System;
using System.Collections.Generic;
using UnityEngine;
using MarketDay;

namespace Checkout {
 // Rede de supermercados (Lucas 06/11 "Aprovado"): the chain's Blender models (scripts/blender/rede_export.py →
 // Resources/Rede/<Model>.fbx + <Model>_brand.json). Materials follow the Blender contract: C_RRGGBB a painted colour
 // (the market's "Soft Painted" look; navy / gold are repainted by CheckoutMarketPaint like the rest of the market),
 // E_RRGGBB a lit colour. The blank white plates get the chain's logo and name from the JSON (never baked in the model:
 // the name is the player's own text, the logo follows the emblem and the market's colours).
 public static class CheckoutRedeModels {
  static Shader painted;
  static readonly Dictionary<string,Material> materials=new Dictionary<string,Material>();
  static readonly Dictionary<string,PlateSet> plateSets=new Dictionary<string,PlateSet>();
  static readonly Color Ink=new Color(.22f,.115f,.055f,1);

  [Serializable] public class Plate{public string name,holder,kind,color;public float size,text;public bool upper;public float[] pos,normal,right,up;}
  [Serializable] public class PlateSet{public string model;public int tris;public float[] size;public Plate[] plates;}

  static Shader Painted=>painted?painted:(painted=Shader.Find("MarketDay/Soft Painted"));

  static Material Mat(string name){
   int dot=name.IndexOf('.');if(dot>0)name=name.Substring(0,dot);name=name.Replace(" (Instance)","");
   if(materials.TryGetValue(name,out var m)&&m)return m;
   string hex=name.Length>=8&&(name.StartsWith("C_")||name.StartsWith("E_"))?name.Substring(2,6):"FFFFFF";
   m=new Material(Painted){name="Rede "+name};
   var c=MarketSimulation.C(hex);
   if(name.StartsWith("E_")){c=Color.Lerp(c,Color.white,.25f);m.SetFloat("_Outline",0);}   // lamps: bright, no ink line
   else{m.SetFloat("_Outline",.8f);m.SetColor("_OutlineColor",Ink);}
   m.color=c;materials[name]=m;return m;
  }

  public static PlateSet Plates(string model){
   if(plateSets.TryGetValue(model,out var set))return set;
   var json=Resources.Load<TextAsset>("Rede/"+model+"_brand");
   set=json?JsonUtility.FromJson<PlateSet>(json.text):null;
   plateSets[model]=set;return set;
  }

  /// <summary>The model under a new holder (local origin = the model's origin: footprint centre on the ground).</summary>
  public static Transform Spawn(string model,Transform parent,string name){
   var holder=new GameObject(name).transform;holder.SetParent(parent,false);
   var prefab=Resources.Load<GameObject>("Rede/"+model);
   if(!prefab){Debug.LogWarning("CHECKOUT_REDE_MODEL_MISSING "+model);return holder;}
   var go=UnityEngine.Object.Instantiate(prefab,holder,false);go.name=model+" model";
   foreach(var r in go.GetComponentsInChildren<Renderer>(true)){
    var mats=r.sharedMaterials;
    for(int i=0;i<mats.Length;i++)mats[i]=Mat(mats[i]?mats[i].name:"C_FFFFFF");
    r.sharedMaterials=mats;
   }
   foreach(var c in go.GetComponentsInChildren<Collider>(true))UnityEngine.Object.Destroy(c);
   var set=Plates(model);
   if(set!=null&&set.plates!=null&&set.plates.Length>0)holder.gameObject.AddComponent<CheckoutRedePlates>().Build(set);
   CheckoutMarketPaint.Touch(holder.gameObject);
   return holder;
  }
 }

 // The logo and the name on a model's blank plates; redrawn when the brand changes (name, emblem, colours).
 public sealed class CheckoutRedePlates:MonoBehaviour {
  sealed class Made{public CheckoutRedeModels.Plate plate;public Transform t;public MeshRenderer logo;public TextMesh text;}
  readonly List<Made> made=new List<Made>();
  int version=-1;
  static Material logoMaterial;static Texture logoTexture;
  static Font font;static Material fontMaterial;

  static Vector3 V(float[] a)=>a!=null&&a.Length>=3?new Vector3(a[0],a[1],a[2]):Vector3.zero;

  public void Build(CheckoutRedeModels.PlateSet set){
   foreach(var p in set.plates){
    var n=V(p.normal).normalized;var up=V(p.up).normalized;if(n==Vector3.zero||up==Vector3.zero)continue;
    var go=new GameObject("Brand "+p.name);go.transform.SetParent(transform,false);
    go.transform.localPosition=V(p.pos)+n*.012f;
    go.transform.localRotation=Quaternion.LookRotation(-n,up);   // quad / text readable from the plate's front
    var m=new Made{plate=p,t=go.transform};
    if(p.kind=="logo"){
     var mf=go.AddComponent<MeshFilter>();mf.sharedMesh=Quad();
     m.logo=go.AddComponent<MeshRenderer>();m.logo.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;
     go.transform.localScale=new Vector3(p.size,p.size,1);
    }else{
     m.text=go.AddComponent<TextMesh>();
     EnsureFont();if(font){m.text.font=font;go.GetComponent<MeshRenderer>().sharedMaterial=fontMaterial?fontMaterial:font.material;}
     m.text.fontSize=64;m.text.anchor=TextAnchor.MiddleCenter;m.text.alignment=TextAlignment.Center;m.text.fontStyle=FontStyle.Bold;
     m.text.characterSize=p.text*10f/64f*1.35f;
    }
    made.Add(m);
   }
   Refresh(true);
  }

  static Mesh quad;
  static Mesh Quad(){
   if(quad)return quad;
   quad=new Mesh{name="Rede plate"};
   quad.vertices=new[]{new Vector3(-.5f,-.5f,0),new Vector3(.5f,-.5f,0),new Vector3(-.5f,.5f,0),new Vector3(.5f,.5f,0)};
   quad.uv=new[]{new Vector2(0,0),new Vector2(1,0),new Vector2(0,1),new Vector2(1,1)};
   quad.triangles=new[]{0,2,1,2,3,1};quad.RecalculateNormals();quad.RecalculateBounds();
   return quad;
  }

  // The facade's own letters (the hipermercado dressing) set the look of the chain's lettering.
  static void EnsureFont(){
   if(font)return;
   var dressing=GameObject.Find("Market Stage Dressing");
   var sample=dressing?dressing.GetComponentInChildren<TextMesh>(true):null;
   if(sample&&sample.font){font=sample.font;fontMaterial=sample.GetComponent<MeshRenderer>()?.sharedMaterial;return;}
   var stage=FindAnyObjectByType<CheckoutStageConstruction>(FindObjectsInactive.Include);
   if(stage&&stage.titleFont){font=stage.titleFont;fontMaterial=stage.titleMaterial;}
  }

  void Update(){Refresh(false);}

  void Refresh(bool force){
   if(!force&&version==CheckoutBrand.Version)return;
   version=CheckoutBrand.Version;
   bool on=CheckoutBrand.Named&&!string.IsNullOrEmpty(CheckoutBrand.Name);
   var tex=CheckoutBrand.Logo;
   if(!logoMaterial){logoMaterial=new Material(Shader.Find("Sprites/Default")){name="Rede plate logo"};}
   if(logoTexture!=tex){logoMaterial.mainTexture=tex;logoTexture=tex;}
   foreach(var m in made){
    if(m.logo){m.logo.sharedMaterial=logoMaterial;m.logo.enabled=on&&tex;}
    if(m.text){
     m.text.gameObject.SetActive(on);if(!on)continue;
     var name=m.plate.upper?CheckoutBrand.Name.ToUpperInvariant():CheckoutBrand.Name;
     m.text.text=name;
     m.text.color=m.plate.color=="F0C75A"?Color.Lerp(CheckoutBrand.Accent,Color.white,.2f):CheckoutBrand.Primary;
     Fit(m);
    }
   }
  }

  // Long names shrink to the plate (a plate is about as wide as the text was planned for 9 letters).
  static void Fit(Made m){
   float baseSize=m.plate.text*10f/64f*1.35f;m.text.characterSize=baseSize;
   var r=m.text.GetComponent<MeshRenderer>();if(!r)return;
   float planned=m.plate.text*9f*.62f,width=0;
   var b=r.localBounds;width=b.size.x;
   if(width>planned&&width>0)m.text.characterSize=baseSize*planned/width;
  }
 }
}
