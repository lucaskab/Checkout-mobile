using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Street lamps at night and in heavy rain.
 // Real spot lights only light a handful of objects per mesh (pixel light count is 1–4 on phone/PC), so most lamps
 // stayed dark or cast a tiny half-moon on the road. Every lamp head on the map (city street lights, park globes,
 // modern square/quay lamps, yard lamps) now gets the same fake light: a warm pool on the ground under it and a
 // halo on the lens, both additive and unlit, faded in and out.
 public sealed class CheckoutStreetLightPools:MonoBehaviour {
  static readonly string[] EmitterNames={"luminous lens","lamp globe","lamp light","lamp head glow"};
  static readonly string[] EmitterMaterials={"citylamp","lampglobe","modernlampglow","yardlamp","streetlampglow"};
  class Lamp {public Vector3 head;public float groundY,radius;public bool beam;}
  readonly List<Lamp> lamps=new List<Lamp>();
  readonly List<Renderer> pieces=new List<Renderer>();
  Material poolMat,beamMat,haloMat;Transform root;float level,target,strength=.6f;
  public int Count=>lamps.Count;

  public void Initialize(){Discover();Build();SetLevel(0);}

  // Fully lit at night, a bit softer over a rainy afternoon.
  public void SetOn(bool on,float power){target=on?1:0;if(on)strength=power;enabled=true;}

  void Update(){level=Mathf.MoveTowards(level,target,Time.deltaTime*1.4f);SetLevel(level);if(Mathf.Approximately(level,target))enabled=target>0;}

  void SetLevel(float k){if(!root)return;root.gameObject.SetActive(k>.001f);var warm=new Color(1f,.74f,.44f);
   if(poolMat)poolMat.SetColor("_Color",new Color(warm.r,warm.g,warm.b,.72f*strength*k));
   if(beamMat)beamMat.SetColor("_Color",new Color(warm.r,warm.g*.96f,warm.b*.9f,.12f*strength*k));
   if(haloMat)haloMat.SetColor("_Color",new Color(1f,.82f,.56f,.9f*k));}

  void Discover(){
   var heads=new List<(Vector3 p,Transform owner)>();
   foreach(var r in FindObjectsByType<Renderer>(FindObjectsInactive.Exclude)){
    if(r is ParticleSystemRenderer)continue;var n=r.name.ToLowerInvariant();
    bool match=EmitterNames.Contains(n)||r.sharedMaterials.Any(m=>m&&EmitterMaterials.Any(e=>m.name.ToLowerInvariant().StartsWith(e)));
    if(!match)continue;var c=r.bounds.center;if(c.y<2.2f||c.y>9)continue;// floor lamps, signs and interior fixtures stay out
    heads.Add((new Vector3(c.x,r.bounds.min.y,c.z),r.transform.root));}
   foreach(var l in FindObjectsByType<Light>(FindObjectsInactive.Include))if(l.type==LightType.Spot&&l.name.ToLowerInvariant().Contains("spotlight"))heads.Add((l.transform.position,l.transform.root));
   foreach(var h in heads){if(lamps.Any(o=>Flat(o.head-h.p).sqrMagnitude<1.4f*1.4f))continue;
    float ground=Ground(h.p);float height=Mathf.Max(1.5f,h.p.y-ground);
    lamps.Add(new Lamp{head=h.p,groundY=ground,radius=Mathf.Clamp(height*1.25f,3.2f,6f),beam=false});}// no beam: a cone reads as a lit triangle from the iso camera
  }

  static Vector3 Flat(Vector3 v)=>new Vector3(v.x,0,v.z);

  // The ground right under the lamp head (sidewalk, road, park path); the pole, cars and people are skipped.
  static float Ground(Vector3 head){float best=float.NegativeInfinity;
   foreach(var hit in Physics.RaycastAll(head+Vector3.down*.25f,Vector3.down,12,~0,QueryTriggerInteraction.Ignore)){if(head.y-hit.point.y<1.4f||hit.point.y>.6f||hit.rigidbody)continue;/* skip the pole, cars and people */if(hit.point.y>best)best=hit.point.y;}
   return float.IsNegativeInfinity(best)?(head.y>4?.13f:0):best;}

  void Build(){var shader=Resources.Load<Shader>("CheckoutLighting/StreetLightAdditive");if(!shader)shader=Shader.Find("Sprites/Default");
   var falloff=Falloff(128);poolMat=new Material(shader){name="Street light pool",mainTexture=falloff,renderQueue=3005};
   beamMat=new Material(shader){name="Street light beam",mainTexture=Texture2D.whiteTexture,renderQueue=3006};
   haloMat=new Material(shader){name="Street light halo",mainTexture=falloff,renderQueue=3007};
   root=new GameObject("Street light pools").transform;root.SetParent(transform,false);
   var quad=Quad();Mesh cone=Cone(18);
   foreach(var lamp in lamps){
    var pool=Piece("Pool",quad,poolMat);pool.position=new Vector3(lamp.head.x,lamp.groundY+.035f,lamp.head.z);pool.localScale=Vector3.one*lamp.radius*2;
    var halo=Piece("Halo",quad,haloMat);halo.gameObject.AddComponent<CheckoutBillboard>();halo.position=lamp.head+Vector3.down*.05f;halo.localScale=Vector3.one*.9f;
    if(lamp.beam){var beam=Piece("Beam",cone,beamMat);beam.position=lamp.head;float h=lamp.head.y-lamp.groundY;beam.localScale=new Vector3(lamp.radius*.8f,h,lamp.radius*.8f);}}
  }

  Transform Piece(string name,Mesh mesh,Material mat){var go=new GameObject(name,typeof(MeshFilter),typeof(MeshRenderer));go.transform.SetParent(root,false);go.GetComponent<MeshFilter>().sharedMesh=mesh;var mr=go.GetComponent<MeshRenderer>();mr.sharedMaterial=mat;mr.shadowCastingMode=UnityEngine.Rendering.ShadowCastingMode.Off;mr.receiveShadows=false;mr.lightProbeUsage=UnityEngine.Rendering.LightProbeUsage.Off;mr.reflectionProbeUsage=UnityEngine.Rendering.ReflectionProbeUsage.Off;pieces.Add(mr);return go.transform;}

  // Flat 1×1 quad lying on the ground (the halo re-aims it at the camera).
  static Mesh Quad(){var m=new Mesh{name="Light quad"};m.vertices=new[]{new Vector3(-.5f,0,-.5f),new Vector3(.5f,0,-.5f),new Vector3(.5f,0,.5f),new Vector3(-.5f,0,.5f)};m.uv=new[]{new Vector2(0,0),new Vector2(1,0),new Vector2(1,1),new Vector2(0,1)};m.colors=Enumerable.Repeat(Color.white,4).ToArray();m.triangles=new[]{0,2,1,0,3,2};m.RecalculateBounds();return m;}

  // Open cone from the lamp head (apex, bright) down to the ground (base radius 1, fades out).
  static Mesh Cone(int sides){var v=new List<Vector3>();var c=new List<Color>();var uv=new List<Vector2>();var t=new List<int>();
   for(int i=0;i<=sides;i++){float a=i*Mathf.PI*2/sides;v.Add(new Vector3(Mathf.Cos(a)*.06f,0,Mathf.Sin(a)*.06f));c.Add(new Color(1,1,1,1));uv.Add(new Vector2(.5f,.5f));v.Add(new Vector3(Mathf.Cos(a),-1,Mathf.Sin(a)));c.Add(new Color(1,1,1,0));uv.Add(new Vector2(.5f,.5f));}
   for(int i=0;i<sides;i++){int a=i*2;t.AddRange(new[]{a,a+1,a+2,a+2,a+1,a+3});}
   var m=new Mesh{name="Light beam"};m.SetVertices(v);m.SetColors(c);m.SetUVs(0,uv);m.SetTriangles(t,0);m.RecalculateBounds();return m;}

  // Smooth round falloff: bright centre, long soft edge, exactly zero at the rim.
  static Texture2D Falloff(int size){var tex=new Texture2D(size,size,TextureFormat.R8,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear,name="Street light falloff"};var px=new Color32[size*size];
   for(int y=0;y<size;y++)for(int x=0;x<size;x++){float dx=(x+.5f)/size*2-1,dy=(y+.5f)/size*2-1;float r=Mathf.Clamp01(Mathf.Sqrt(dx*dx+dy*dy));float k=Mathf.Pow(1-r*r,2.2f);byte b=(byte)Mathf.RoundToInt(k*255);px[y*size+x]=new Color32(b,b,b,255);}
   tex.SetPixels32(px);tex.Apply(false,true);return tex;}

  void OnDestroy(){foreach(var m in new[]{poolMat,beamMat,haloMat})if(m)Destroy(m);}
 }

 // Keeps the lamp halo facing the camera.
 public sealed class CheckoutBillboard:MonoBehaviour {Camera cam;void LateUpdate(){if(!cam)cam=Camera.main;if(!cam)return;transform.rotation=Quaternion.LookRotation(cam.transform.forward,cam.transform.up)*Quaternion.Euler(-90,0,0);}}
}
