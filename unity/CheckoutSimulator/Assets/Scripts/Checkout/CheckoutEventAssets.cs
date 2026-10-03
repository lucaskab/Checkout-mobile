using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;
using MarketDay;

namespace Checkout {
 // Event props: Blender-authored FBX models (Resources/EventProps) with the shared painted shader,
 // cloned market characters, and a few primitive helpers. Built once per event and cached.
 public sealed class CheckoutEventAssets {
  public static readonly Color Ink=new Color(.22f,.115f,.055f,1);
  readonly Dictionary<string,Material> materials=new Dictionary<string,Material>();
  readonly Dictionary<string,Material> textured=new Dictionary<string,Material>();
  readonly Dictionary<string,Material> atlases=new Dictionary<string,Material>();
  readonly List<Mesh> meshes=new List<Mesh>();
  static Shader painted;
  static Shader Painted=>painted?painted:(painted=Shader.Find("MarketDay/Soft Painted"));
  public Material Material(string color){if(!materials.TryGetValue(color,out var material)){material=new Material(Painted);material.name="Event "+color;material.color=MarketSimulation.C(color);material.SetFloat("_Outline",.8f);material.SetColor("_OutlineColor",Ink);materials[color]=material;}return material;}
  public Material Textured(string texture){if(!textured.TryGetValue(texture,out var material)){material=new Material(Painted);material.name="Event texture "+texture;material.mainTexture=Resources.Load<Texture2D>("EventProps/Textures/"+texture);material.color=Color.white;material.SetFloat("_Outline",.8f);material.SetColor("_OutlineColor",Ink);textured[texture]=material;}return material;}
  // Baked Blender atlases and the supplied game models share the Standard shader used by the map's Tripo models.
  public Material Atlas(string name){if(!atlases.TryGetValue(name,out var material)){material=new Material(Shader.Find("Standard"));material.name="Event atlas "+name;material.mainTexture=Resources.Load<Texture2D>("EventProps/Tex/"+name);material.color=Color.white;material.SetFloat("_Glossiness",.12f);material.SetFloat("_Metallic",0);atlases[name]=material;}return material;}
  public Transform Group(Transform parent,string name,Vector3 position){var go=new GameObject(name);go.transform.SetParent(parent,false);go.transform.localPosition=position;return go.transform;}

  // Blender material names: C_RRGGBB (painted colour) or T_<texture> (painted texture). See scripts/blender/build_event_props.py.
  Material Remap(Material source){if(!source)return Material("FFFFFF");var name=source.name.Replace(" (Instance)","");int dot=name.IndexOf('.');if(dot>0)name=name.Substring(0,dot);
   if(name.StartsWith("C_")&&name.Length>=8)return Material(name.Substring(2,6));if(name.StartsWith("T_"))return Textured(name.Substring(2));if(name.StartsWith("G_"))return Atlas(name.Substring(2));return source;}
  public Transform Model(Transform parent,string model,Vector3 p,float yaw=0,float scale=1){
   var holder=Group(parent,model,p);holder.gameObject.layer=2;holder.localRotation=Quaternion.Euler(0,yaw,0);holder.localScale=Vector3.one*scale;
   var prefab=Resources.Load<GameObject>("EventProps/"+model);if(!prefab){Debug.LogWarning("CHECKOUT_EVENT_PROP_MISSING "+model);return holder;}
   var go=Object.Instantiate(prefab,holder,false);go.name=model+" model";
   foreach(var t in go.GetComponentsInChildren<Transform>(true))t.gameObject.layer=2;
   foreach(var c in go.GetComponentsInChildren<Collider>(true))Object.Destroy(c);
   foreach(var r in go.GetComponentsInChildren<Renderer>(true)){var shared=r.sharedMaterials;for(int i=0;i<shared.Length;i++)shared[i]=Remap(shared[i]);r.sharedMaterials=shared;r.shadowCastingMode=ShadowCastingMode.On;}
   return holder;}

  // Event props v2 (Oct 2026): Blender FBX + one baked BaseColor atlas each, in Resources/EventProps2 (ArtSource/events_v2).
  // Exported with the readable side facing +Z; the same Standard-shader look as the construction machines (CheckoutWorks).
  readonly Dictionary<string,Material> bakedProps=new Dictionary<string,Material>();
  public Transform Prop2(Transform parent,string model,Vector3 p,float yaw=0,float scale=1,string tint=null){
   var holder=Group(parent,model,p);holder.gameObject.layer=2;holder.localRotation=Quaternion.Euler(0,yaw,0);holder.localScale=Vector3.one*scale;
   var prefab=Resources.Load<GameObject>("EventProps2/"+model);if(!prefab){Debug.LogWarning("CHECKOUT_EVENT_PROP_MISSING "+model);return holder;}
   var go=Object.Instantiate(prefab,holder,false);go.name=model+" model";
   var key=model+"|"+tint;
   if(!bakedProps.TryGetValue(key,out var material)||!material){
    material=new Material(Shader.Find("Standard")){name=model+" (baked)"};var tex=Resources.Load<Texture2D>("EventProps2/"+model+"_BaseColor");
    if(tex)material.mainTexture=tex;material.color=string.IsNullOrEmpty(tint)?Color.white:MarketSimulation.C(tint);
    material.SetFloat("_Glossiness",.12f);material.SetFloat("_Metallic",0);bakedProps[key]=material;}
   foreach(var t in go.GetComponentsInChildren<Transform>(true))t.gameObject.layer=2;
   foreach(var c in go.GetComponentsInChildren<Collider>(true))Object.Destroy(c);
   foreach(var r in go.GetComponentsInChildren<Renderer>(true)){var shared=r.sharedMaterials;for(int i=0;i<shared.Length;i++)shared[i]=material;r.sharedMaterials=shared;r.shadowCastingMode=ShadowCastingMode.On;}
   return holder;}

  // A live copy of one of the market's rigged characters, looping one of its Blender clips.
  public Transform Actor(Transform parent,string source,Vector3 p,float yaw,string clip="Idle",float speed=1){
   var holder=Group(parent,"Event actor "+source,p);holder.localRotation=Quaternion.Euler(0,yaw,0);
   var world=Object.FindAnyObjectByType<MarketSimulation>();var root=world&&world.world?world.world.Find(source):null;
   // The simulation renames the stocker to StockWorker_0 when it spawns the stock team.
   if(!root&&world&&world.world&&source=="Worker_Stocker")foreach(var alt in new[]{"StockWorker_0","Worker_Delivery","Worker_Cashier"}){root=world.world.Find(alt);if(root)break;}
   if(!root){foreach(var a in Object.FindObjectsByType<MarketCharacterAnimator>(FindObjectsInactive.Include))if(a.name==source){root=a.transform;break;}}
   if(!root){Debug.LogWarning("CHECKOUT_EVENT_ACTOR_MISSING "+source);return holder;}
   var animator=root.GetComponent<MarketCharacterAnimator>();var player=animator&&animator.animationPlayer?animator.animationPlayer:root.GetComponentInChildren<Animation>(true);
   var visual=player?player.gameObject:root.gameObject;
   bool wasActive=holder.gameObject.activeSelf;holder.gameObject.SetActive(false);
   var clone=Object.Instantiate(visual,holder,false);clone.name="Visual";
   foreach(var b in clone.GetComponentsInChildren<MonoBehaviour>(true))Object.DestroyImmediate(b);
   foreach(var n in clone.GetComponentsInChildren<UnityEngine.AI.NavMeshAgent>(true))Object.DestroyImmediate(n);
   foreach(var c in clone.GetComponentsInChildren<Collider>(true))Object.DestroyImmediate(c);
   foreach(var t in clone.GetComponentsInChildren<Transform>(true)){t.gameObject.layer=2;if(t.name=="Handled purchase")t.gameObject.SetActive(false);}
   clone.transform.localPosition=visual==root.gameObject?Vector3.zero:Quaternion.Inverse(root.rotation)*(visual.transform.position-root.position);
   clone.transform.localRotation=visual==root.gameObject?Quaternion.identity:Quaternion.Inverse(root.rotation)*visual.transform.rotation;
   clone.transform.localScale=visual.transform.lossyScale;clone.SetActive(true);
   foreach(var r in clone.GetComponentsInChildren<Renderer>(true))r.enabled=true;
   var anim=clone.GetComponent<Animation>();if(!anim)anim=clone.GetComponentInChildren<Animation>(true);
   if(anim){anim.enabled=true;anim.cullingType=AnimationCullingType.AlwaysAnimate;var state=anim[clip]??anim["Idle"];if(state){state.wrapMode=WrapMode.Loop;state.speed=speed;state.time=Random.value*state.length;anim.Play(state.name);}}
   holder.gameObject.SetActive(wasActive);return holder;}

  // Primitive helpers (still used for tiny accents and fallbacks).
  public Transform Part(Transform parent,string name,Vector3 p,Vector3 size,string color,PrimitiveType shape=PrimitiveType.Cube){var go=GameObject.CreatePrimitive(shape);go.name=name;go.layer=2;go.transform.SetParent(parent,false);go.transform.localPosition=p;go.transform.localScale=size;Object.Destroy(go.GetComponent<Collider>());go.GetComponent<Renderer>().sharedMaterial=Material(color);return go.transform;}
  public void Bar(Transform parent,Vector3 a,Vector3 b,float width,string color){var t=Part(parent,"Frame",(a+b)*.5f,new Vector3(width,(a-b).magnitude,width),color);t.up=b-a;}

  // Primitive safety cone kept for the expansion plots.
  public void Cone(Transform parent,Vector3 p){Part(parent,"Cone foot",p+Vector3.up*.05f,new Vector3(.55f,.1f,.55f),"354451");for(int i=0;i<4;i++){float width=.4f-i*.085f;Part(parent,"Safety cone",p+Vector3.up*(.18f+i*.17f),new Vector3(width,.17f,width),i==2?"FFF3DC":"EF8B40");}}
  // Static single-material parts become one mesh per material; multi-material models are already single meshes.
  public void Batch(Transform root){var groups=new Dictionary<Material,List<CombineInstance>>();var parts=root.GetComponentsInChildren<MeshFilter>();foreach(var part in parts){var renderer=part.GetComponent<MeshRenderer>();if(!renderer||renderer.sharedMaterials.Length!=1||!part.sharedMesh||!part.sharedMesh.isReadable||part.GetComponentInParent<Animation>())continue;var material=renderer.sharedMaterial;if(!groups.ContainsKey(material))groups[material]=new List<CombineInstance>();groups[material].Add(new CombineInstance{mesh=part.sharedMesh,transform=root.worldToLocalMatrix*part.transform.localToWorldMatrix});Object.Destroy(renderer);Object.Destroy(part);}
   foreach(var pair in groups){var mesh=new Mesh{name=root.name+" geometry",indexFormat=IndexFormat.UInt32};mesh.CombineMeshes(pair.Value.ToArray());meshes.Add(mesh);var go=new GameObject("Batched "+pair.Key.name);go.layer=2;go.transform.SetParent(root,false);go.AddComponent<MeshFilter>().sharedMesh=mesh;var renderer=go.AddComponent<MeshRenderer>();renderer.sharedMaterial=pair.Key;renderer.shadowCastingMode=ShadowCastingMode.On;}}
  public void Dispose(){foreach(var mat in materials.Values)Object.Destroy(mat);foreach(var mat in textured.Values)Object.Destroy(mat);foreach(var mat in atlases.Values)Object.Destroy(mat);foreach(var mesh in meshes)Object.Destroy(mesh);}
 }
}
