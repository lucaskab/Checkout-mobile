using System;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;

namespace Checkout {
 public sealed partial class CheckoutEventVisuals:MonoBehaviour {
  public static readonly string[] EventIds={"hora-do-rush","quinto-dia-util","feira-de-rua","onda-de-calor","sorteio-na-porta","caminhao-de-ofertas","dia-de-jogo","cafe-com-a-equipe","viralizou","chuva-forte","rua-em-obras","engarrafamento","fim-do-mes","maquininha-fora-do-ar","excursao-da-escola","queda-de-energia","turno-puxado","vigilancia-sanitaria","carro-de-som"};
 class Motion {public Transform root,target;public Vector3 home,dir,scale,offset;public Quaternion rot;public string kind;public float phase,range,speed;}
  class StreetlightState {public Light light;public bool enabled;public float intensity,range,spotAngle;}
  class GlowState {public Renderer renderer;public Material[] original,glowing;}
  readonly Dictionary<string,GameObject> scenes=new Dictionary<string,GameObject>();
  readonly Dictionary<string,List<Motion>> motions=new Dictionary<string,List<Motion>>();
  readonly List<StreetlightState> streetlights=new List<StreetlightState>();
  readonly List<GlowState> streetlightGlow=new List<GlowState>();
  readonly CheckoutEventAssets art=new CheckoutEventAssets();
  CheckoutRainPuddles rainPuddles;CheckoutStreetLightPools lampPools;GameObject umbrellaPrefab;
  Light sun;Color sunColor,ambient,background;float sunIntensity;Camera view;Material particleMaterial;
  string building,active="";float clock,umbrellaRefresh;double expiresAt;
  public string ActiveId=>active;
  public static bool RoadWorks{get;private set;}
  public void Initialize(){sun=FindObjectsByType<Light>().FirstOrDefault(l=>l.type==LightType.Directional);if(sun){sunColor=sun.color;sunIntensity=sun.intensity;}ambient=RenderSettings.ambientLight;view=Camera.main;if(view)background=view.backgroundColor;particleMaterial=new Material(Shader.Find("Sprites/Default"));rainPuddles=gameObject.AddComponent<CheckoutRainPuddles>();rainPuddles.Initialize();umbrellaPrefab=Resources.Load<GameObject>("Rain/StreetUmbrella");EnsureOriginalStreetlights();CacheStreetlights();CacheStreetlightGlow();lampPools=gameObject.AddComponent<CheckoutStreetLightPools>();lampPools.Initialize();}
  MarketEvent lastSnapshot;bool previewing;
  public bool Previewing=>previewing;
  public void Apply(MarketEvent value){lastSnapshot=value;if(previewing)return;string id=value!=null&&value.endsAt>DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()?value.id:"";expiresAt=value?.endsAt??0;SetEvent(id??"");}
  // Editor/dev preview: shows an event regardless of the game store; an empty id hands control back to the snapshots.
  public void Preview(string id){if(string.IsNullOrEmpty(id)){previewing=false;Apply(lastSnapshot);return;}previewing=true;expiresAt=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()+3600000;SetEvent(id);}
  void SetEvent(string id){if(active==id){if(string.IsNullOrEmpty(id)||!builtFor.TryGetValue(id,out var builtKey)||builtKey==LayoutKey())return;active="\u0000";} // same event, but the shop grew (stage, entrance): its scene is rebuilt for the new layout
   ReleaseCrowd();if(scenes.TryGetValue(active,out var previous)){previous.SetActive(false);foreach(var particles in previous.GetComponentsInChildren<ParticleSystem>(true))particles.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);}active=id;RoadWorks=id=="rua-em-obras";ApplyTraffic(id);clock=0;umbrellaRefresh=0;rainPuddles.SetRaining(id=="chuva-forte");SetCustomerUmbrellas(id=="chuva-forte");
   RestoreLight();SetStreetlights((id=="chuva-forte"||night)&&id!="queda-de-energia");if(string.IsNullOrEmpty(id)){if(night)NightLight();return;}
   if(scenes.TryGetValue(id,out var stale)&&builtFor.TryGetValue(id,out var key)&&key!=LayoutKey()){Destroy(stale);scenes.Remove(id);}
   if(!scenes.TryGetValue(id,out var scene)){building=id;builtFor[id]=LayoutKey();scene=new GameObject("Event · "+id);scene.transform.SetParent(transform,false);WorldAligned(scene.transform);scene.SetActive(false);scenes[id]=scene;motions[id]=new List<Motion>();try{Build(id,scene.transform);}catch(Exception e){Debug.LogException(e);ForgetCrowd(id);}}
   foreach(var motion in motions[id]){motion.root.localPosition=motion.home;motion.root.localRotation=motion.rot;motion.root.localScale=motion.scale;}scene.SetActive(true);ApplyTraffic(id);foreach(var particles in scene.GetComponentsInChildren<ParticleSystem>())particles.Play();
   if(id=="chuva-forte"){if(sun){sun.color=new Color(.66f,.77f,.94f);sun.intensity=sunIntensity*.68f;}RenderSettings.ambientLight=new Color(.39f,.46f,.55f);if(view)view.backgroundColor=new Color(.52f,.63f,.66f);}
   if(night)NightLight();
  }
  // Night turn: a dark blue sky over whatever the event set, with the street lights on.
  bool night;
  public void SetNight(bool value){if(night==value)return;night=value;var id=active;active="\u0000";SetEvent(id);}
  void NightLight(){if(sun){sun.color=new Color(.55f,.64f,.98f);sun.intensity=(sun.intensity>0?sun.intensity:sunIntensity)*.28f;}RenderSettings.ambientLight=new Color(.16f,.19f,.31f);if(view)view.backgroundColor=new Color(.07f,.09f,.17f);}
  // Rain: the city's people and the market's own customers (CheckoutWalker) open an umbrella out on the street; a
  // customer closes it on stepping into the market and opens it again on the way out (CheckoutWalker.OutdoorWalk).
  void SetCustomerUmbrellas(bool enabled){foreach(var customer in FindObjectsByType<MarketCharacterAnimator>(FindObjectsInactive.Include).Where(c=>c.GetComponent<CheckoutCityPedestrian>()||c.GetComponent<CheckoutCityAppearance>()||c.GetComponent<CheckoutWalker>())){var pedestrian=customer.GetComponent<CheckoutCityPedestrian>();var walker=customer.GetComponent<CheckoutWalker>();var rig=customer.GetComponent<MarketRainUmbrellaRig>();if(enabled&&!rig&&(!walker||walker.OutdoorWalk))rig=customer.gameObject.AddComponent<MarketRainUmbrellaRig>();if(!rig)continue;rig.Initialize(customer.animationPlayer,umbrellaPrefab);rig.SetRainShelter(enabled&&!(pedestrian&&pedestrian.IsSheltered)&&(!walker||walker.OutdoorWalk));}}
  void Update(){Interactive();MarketTick();if(active=="chuva-forte"&&(umbrellaRefresh+=Time.deltaTime)>.5f){umbrellaRefresh=0;SetCustomerUmbrellas(true);}if(string.IsNullOrEmpty(active))return;if(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()>=expiresAt){SetEvent("");return;}clock+=Time.deltaTime;
   if(!motions.TryGetValue(active,out var activeMotions))return;
   foreach(var m in activeMotions){float t=clock+m.phase;switch(m.kind){
    case "float":m.root.localPosition=m.home+Vector3.up*Mathf.Sin(t*1.5f)*.14f;break;
    case "hover":m.root.localPosition=m.home+Vector3.up*Mathf.Sin(t*1.6f)*.16f;m.root.localRotation=m.rot*Quaternion.Euler(0,Mathf.Sin(t*.9f)*22,0);break;
    case "rise":{float k=Mathf.Repeat(t*.35f,1);m.root.localPosition=m.home+Vector3.up*k*1.6f+Vector3.right*Mathf.Sin(t*2.2f)*.12f;m.root.localScale=m.scale*Mathf.Sin(k*Mathf.PI);break;}
    case "coin":m.root.localPosition=m.home+Vector3.up*Mathf.Sin(t*1.8f)*.13f;m.root.localRotation=m.rot*Quaternion.Euler(0,t*90,0);break;
    case "spin":m.root.localRotation=m.rot*Quaternion.Euler(0,0,t*60);break;
    case "drive":m.root.localPosition=m.home+Vector3.forward*(Mathf.PingPong(t*1.25f,6)-3);break;
    case "lane":m.root.localPosition=m.home+m.dir*(Mathf.Repeat(t*m.speed,m.range)-m.range*.5f);break;
    case "queue":m.root.localPosition=m.home+m.dir*(Mathf.Max(0,Mathf.Sin(t*.8f))*.35f)+Vector3.up*Mathf.Abs(Mathf.Sin(t*9))*.015f;break;
    case "pulse":m.root.localScale=m.scale*(1+Mathf.Sin(t*3)*.08f);break;
    case "rock":m.root.localRotation=m.rot*Quaternion.Euler(0,0,Mathf.Sin(t)*4);break;
    case "spinfast":m.root.localRotation=m.rot*Quaternion.Euler(0,0,t*140);break;
    case "dig":m.root.localRotation=m.rot*Quaternion.Euler(0,0,Mathf.Sin(t*1.1f)*13);break;
    case "flicker":{bool on=Mathf.PerlinNoise(t*9,m.phase)>.42f;m.root.localScale=on?m.scale*(.7f+Mathf.PerlinNoise(t*23,1)*.7f):Vector3.zero;m.root.localRotation=m.rot*Quaternion.Euler(0,0,t*300);break;}
    case "blink":m.root.localScale=Mathf.Repeat(t,1)<.5f?m.scale:Vector3.zero;break;
    case "bunting":m.root.localRotation=m.rot*Quaternion.Euler(Mathf.Sin(t*1.7f)*3,0,0);break;
    case "sway":m.root.localRotation=m.rot*Quaternion.Euler(Mathf.Sin(t*2.3f)*7,0,Mathf.Sin(t*1.7f)*14);break;
    case "ride":if(m.target)m.root.position=m.target.position+m.offset;break;
    case "follow":{bool on=m.target&&m.target.gameObject.activeInHierarchy;m.root.localScale=on?m.scale:Vector3.zero;if(on)m.root.position=m.target.position+m.offset+Vector3.up*Mathf.Sin(t*1.5f)*.1f;break;}
   }}
  }
  void RestoreLight(){if(sun){sun.color=sunColor;sun.intensity=sunIntensity;}RenderSettings.ambientLight=ambient;if(view)view.backgroundColor=background;}
  void EnsureOriginalStreetlights(){var world=FindAnyObjectByType<MarketSimulation>();if(!world||world.world.Find("City Circulation Repairs/Original street lights"))return;var group=new GameObject("Original street lights").transform;group.SetParent(world.world,false);var positions=new[]{new Vector3(-27.7f,.13f,-10),new Vector3(-27.7f,.13f,8),new Vector3(-27.7f,.13f,26),new Vector3(27.7f,.13f,-9),new Vector3(27.7f,.13f,9),new Vector3(27.7f,.13f,27),new Vector3(-12,.13f,34.3f),new Vector3(12,.13f,34.3f)};foreach(var position in positions){var direction=position.z>33?Vector3.back:Vector3.left*Mathf.Sign(position.x);var light=new GameObject("Original street spotlight").AddComponent<Light>();light.transform.SetParent(group,false);light.transform.position=position+direction*.73f+Vector3.up*3.79f;light.transform.rotation=Quaternion.LookRotation(Vector3.down+direction*.3f);light.type=LightType.Spot;light.color=new Color(1,.82f,.53f);light.intensity=3;light.range=8;light.spotAngle=90;light.shadows=LightShadows.None;light.enabled=false;}}
  void CacheStreetlights(){foreach(var light in FindObjectsByType<Light>(FindObjectsInactive.Include).Where(l=>l.type==LightType.Spot&&l.name.ToLowerInvariant().Contains("spotlight")))streetlights.Add(new StreetlightState{light=light,enabled=light.enabled,intensity=light.intensity,range=light.range,spotAngle=light.spotAngle});}
  void CacheStreetlightGlow(){foreach(var renderer in FindObjectsByType<Renderer>(FindObjectsInactive.Include).Where(r=>r.name=="Luminous lens"||r.sharedMaterials.Any(m=>m&&m.name.Contains("CityLamp")))){var original=renderer.sharedMaterials;var glowing=original.Select(m=>{if(!m||!m.HasProperty("_EmissionColor")||(renderer.name!="Luminous lens"&&!m.name.Contains("CityLamp")))return m;var copy=new Material(m){name=m.name+" (Rain glow)"};copy.EnableKeyword("_EMISSION");copy.SetColor("_EmissionColor",Color.black);return copy;}).ToArray();renderer.sharedMaterials=glowing;streetlightGlow.Add(new GlowState{renderer=renderer,original=original,glowing=glowing});}}
  // Street lamps: the real spot lights stay off (with 1–4 pixel lights per mesh most of them showed nothing or a small
  // half-moon); every lamp head gets the same warm pool and halo from CheckoutStreetLightPools instead.
  void SetStreetlights(bool enabled){foreach(var state in streetlights){if(!state.light)continue;state.light.enabled=false;state.light.intensity=state.intensity;state.light.range=state.range;state.light.spotAngle=state.spotAngle;}if(lampPools)lampPools.SetOn(enabled,night?1f:.85f);foreach(var state in streetlightGlow)foreach(var material in state.glowing)if(material)material.SetColor("_EmissionColor",enabled?new Color(1,.62f,.28f)*3.5f:Color.black);}
  void RestoreStreetlightMaterials(){foreach(var state in streetlightGlow){if(state.renderer)state.renderer.sharedMaterials=state.original;foreach(var material in state.glowing)if(material&& !state.original.Contains(material))Destroy(material);}streetlightGlow.Clear();}
  void OnDestroy(){ClearInteractive();RoadWorks=false;CheckoutEventTraffic.ClearCurbBlock();CheckoutEventTraffic.AvenueJammed=false;RestoreLight();SetStreetlights(false);RestoreStreetlightMaterials();art.Dispose();if(particleMaterial)Destroy(particleMaterial);}
  static Vector3 P(float x,float y,float z)=>new Vector3(x,y,z);
  void Animated(Transform prop,string kind){art.Batch(prop);motions[building].Add(new Motion{root=prop,home=prop.localPosition,rot=prop.localRotation,scale=prop.localScale,kind=kind,phase=motions[building].Count*.7f});}
  void Lane(Transform prop,Vector3 dir,float range,float speed,float phase=0){motions[building].Add(new Motion{root=prop,home=prop.localPosition,rot=prop.localRotation,scale=prop.localScale,dir=dir,range=range,speed=speed,kind="lane",phase=phase});}
  void Queue(Transform prop,Vector3 dir,float phase){motions[building].Add(new Motion{root=prop,home=prop.localPosition,rot=prop.localRotation,scale=prop.localScale,dir=dir,kind="queue",phase=phase});}
  void Prop(Transform prop)=>art.Batch(prop);
  Transform Group(Transform root,string name,Vector3 p)=>art.Group(root,name,p);
  // Blender props face -Z at yaw 0 (ModelYaw corrects the FBX axis). Face turns a prop towards the isometric
  // camera, which looks from +X/-Z. Rigged market characters walk along +Z, so ActorFace turns them to the camera.
  const float Face=-36,ActorFace=144,ModelYaw=180;
  Transform M(Transform root,string model,Vector3 p,float yaw=Face,float scale=1)=>art.Model(root,model,p,yaw+ModelYaw,scale);
  Transform Icon(Transform root,string model,Vector3 p,float scale=1,string kind="hover"){var t=M(root,model,p,Face,scale);Animated(t,kind);return t;}
  // World-space anchors (street lanes, the entrance, the counter workers) converted into this component's space.
  Vector3 W(float x,float y,float z)=>transform.InverseTransformPoint(new Vector3(x,y,z));
  // Interior points follow the purchased store size (CheckoutMarketLayout scales the shell around its anchor).
  Vector3 In(float x,float y,float z){var layout=GetComponent<CheckoutMarketLayout>();var p=new Vector3(x,y,z);return transform.InverseTransformPoint(layout?layout.Point(p):p);}
  // A scene is rebuilt when the market changes shape or stage (the door moves, the stall becomes a shop).
  string LayoutKey(){var layout=GetComponent<CheckoutMarketLayout>();var map=GetComponent<CheckoutMap>()??FindAnyObjectByType<CheckoutMap>();return (layout&&layout.State!=null?layout.State.widthScale.ToString("0.00")+"x"+layout.State.depthScale.ToString("0.00"):"")+"|"+(map?map.Entrance.ToString("F1"):"")+"|"+CheckoutStall.Small+"|"+(map&&map.HasParking);}
  readonly Dictionary<string,string> builtFor=new Dictionary<string,string>();
  Vector3 WorldPoint(string name,Vector3 fallback){var sim=FindAnyObjectByType<MarketSimulation>();var t=sim&&sim.world?sim.world.Find(name):null;return t?transform.InverseTransformPoint(t.position):fallback;}
  Vector3 Door{get{var map=GetComponent<CheckoutMap>();var d=map?transform.InverseTransformPoint(map.Entrance):W(-1.75f,.74f,-8.7f);return new Vector3(d.x,.34f,d.z);}}
  Vector3 Till=>WorldPoint("Worker_Cashier",W(-.4f,.74f,-6.9f));
  static readonly Dictionary<string,string> NamedColors=new Dictionary<string,string>{{"Teal","188F86"},{"Cream","F4DFA4"},{"Orange","EC862E"},{"Dark","384444"},{"Metal","A3B9AD"},{"Screen","93DBDF"},{"Lamp","83B749"},{"Red","D74A3C"},{"White","FFF1D1"},{"Asphalt","4A4D4A"},{"Dirt","805035"},{"Sand","D69C53"},{"Yellow","F4BA42"},{"Stone","B8B2A2"}};
  // The original Blender props (road works, umbrellas) carry colour names only; give them the painted palette.
  void PaintNamed(Transform prop){foreach(var r in prop.GetComponentsInChildren<Renderer>(true)){var shared=r.sharedMaterials;for(int i=0;i<shared.Length;i++){if(!shared[i])continue;var name=shared[i].name.Replace(" (Instance)","");int cut=name.LastIndexOf('_');if(cut>=0)name=name.Substring(cut+1);if(NamedColors.TryGetValue(name,out var hex))shared[i]=art.Material(hex);}r.sharedMaterials=shared;}}
  // Renderer bounds of a map object (warehouse, delivery trucks…) in this component's space.
  Bounds WorldBounds(string name,Bounds fallback){var sim=FindAnyObjectByType<MarketSimulation>();var t=sim&&sim.world?sim.world.Find(name):null;var rs=t&&t.gameObject.activeInHierarchy?t.GetComponentsInChildren<Renderer>().Where(r=>r.enabled).ToArray():new Renderer[0];if(rs.Length==0)return fallback;var b=rs[0].bounds;foreach(var r in rs.Skip(1))b.Encapsulate(r.bounds);b.center=transform.InverseTransformPoint(b.center);return b;}
  // The central warehouse (when bought) takes over from the small storage building.
  string Storage=>Has("Warehouse Large")?"Warehouse Large":"Warehouse";
  bool Has(string name){var sim=FindAnyObjectByType<MarketSimulation>();var t=sim&&sim.world?sim.world.Find(name):null;return t&&t.gameObject.activeInHierarchy&&t.GetComponentsInChildren<Renderer>().Any(r=>r.enabled);}
  // Event scenes: CheckoutEventVisuals.Scenes.cs (built in world space on the avenue in front of the market).
  void Confetti(Transform root,Vector3 p){var go=Group(root,"Confetti",p).gameObject;go.layer=2;go.transform.localRotation=Quaternion.Euler(-90,0,0);var system=go.AddComponent<ParticleSystem>();system.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);var main=system.main;main.playOnAwake=false;main.startLifetime=2.2f;main.startSpeed=new ParticleSystem.MinMaxCurve(2.5f,4.5f);main.startSize=new ParticleSystem.MinMaxCurve(.08f,.15f);main.gravityModifier=.45f;main.startRotation=new ParticleSystem.MinMaxCurve(0,6.28f);var colors=new Gradient();colors.SetKeys(new[]{new GradientColorKey(new Color(.84f,.29f,.24f),0),new GradientColorKey(new Color(.96f,.73f,.26f),.33f),new GradientColorKey(new Color(.09f,.56f,.53f),.66f),new GradientColorKey(new Color(.9f,.49f,.6f),1)},new[]{new GradientAlphaKey(1,0),new GradientAlphaKey(1,1)});main.startColor=new ParticleSystem.MinMaxGradient(colors){mode=ParticleSystemGradientMode.RandomColor};main.maxParticles=200;main.simulationSpace=ParticleSystemSimulationSpace.World;var shape=system.shape;shape.shapeType=ParticleSystemShapeType.Cone;shape.angle=35;shape.radius=.3f;var emission=system.emission;emission.rateOverTime=0;emission.SetBursts(new[]{new ParticleSystem.Burst(0,40,40,999,1.4f)});var renderer=system.GetComponent<ParticleSystemRenderer>();renderer.sharedMaterial=particleMaterial;}
  void Sparks(Transform root,Vector3 p){var go=Group(root,"Sparks",p).gameObject;go.layer=2;go.transform.localRotation=Quaternion.Euler(-90,0,0);var system=go.AddComponent<ParticleSystem>();system.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);var main=system.main;main.playOnAwake=false;main.startLifetime=.45f;main.startSpeed=new ParticleSystem.MinMaxCurve(1.5f,3.2f);main.startSize=new ParticleSystem.MinMaxCurve(.05f,.1f);main.gravityModifier=1.2f;main.startColor=new ParticleSystem.MinMaxGradient(new Color(1,.85f,.35f),new Color(1,.55f,.2f));main.maxParticles=80;main.simulationSpace=ParticleSystemSimulationSpace.World;var shape=system.shape;shape.shapeType=ParticleSystemShapeType.Cone;shape.angle=50;shape.radius=.05f;var emission=system.emission;emission.rateOverTime=0;emission.SetBursts(new[]{new ParticleSystem.Burst(0,14,20,999,.9f)});var renderer=system.GetComponent<ParticleSystemRenderer>();renderer.sharedMaterial=particleMaterial;renderer.renderMode=ParticleSystemRenderMode.Stretch;renderer.lengthScale=2.5f;}
  void Exhaust(Transform car){Particles(car,"Exhaust",new Vector3(.5f,.45f,-2f),new Vector3(.1f,.1f,.1f),new Color(.78f,.8f,.8f,.5f),5,1.4f,.4f,.3f,false);}
  void BuildRain(Transform root){
   var terrain=FindObjectsByType<UnityEngine.Tilemaps.TilemapRenderer>().FirstOrDefault(t=>t.name=="Painted Terrain");
   var area=terrain?terrain.bounds:new Bounds(P(0,0,0),P(90,1,90));
   // Cover the whole city while keeping the cutaway store interior dry.
   void Strip(string name,float minX,float maxX,float minZ,float maxZ){
    float width=maxX-minX,depth=maxZ-minZ;if(width<=0||depth<=0)return;
    Particles(root,name,P((minX+maxX)*.5f,12,(minZ+maxZ)*.5f),P(width,depth,.1f),new Color(.65f,.82f,.96f,.6f),width*depth*.4f,.88f,14,.035f,true);
   }
   Strip("Rain south city",area.min.x,area.max.x,area.min.z,-9.5f);
   Strip("Rain north city",area.min.x,area.max.x,9.5f,area.max.z);
   Strip("Rain west city",area.min.x,-9.5f,-9.5f,9.5f);
   Strip("Rain east city",9.5f,area.max.x,-9.5f,9.5f);
  }
  void Particles(Transform parent,string name,Vector3 p,Vector3 size,Color color,float rate,float lifetime,float speed,float scale,bool rain){var go=Group(parent,name,p).gameObject;go.layer=2;if(rain)go.transform.localRotation=Quaternion.Euler(90,0,0);else go.transform.localRotation=Quaternion.Euler(-90,0,0);var system=go.AddComponent<ParticleSystem>();system.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);var main=system.main;main.playOnAwake=false;main.startLifetime=lifetime;main.startSpeed=speed;main.startSize=scale;main.startColor=color;main.maxParticles=Mathf.CeilToInt(rate*lifetime)+16;main.simulationSpace=ParticleSystemSimulationSpace.World;main.cullingMode=ParticleSystemCullingMode.AlwaysSimulate;var shape=system.shape;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=size;var emission=system.emission;emission.rateOverTime=rate;var renderer=system.GetComponent<ParticleSystemRenderer>();renderer.sharedMaterial=particleMaterial;if(rain){renderer.renderMode=ParticleSystemRenderMode.Stretch;renderer.lengthScale=8;renderer.velocityScale=.025f;}else{var fade=system.colorOverLifetime;fade.enabled=true;var gradient=new Gradient();gradient.SetKeys(new[]{new GradientColorKey(Color.white,0),new GradientColorKey(Color.white,1)},new[]{new GradientAlphaKey(0,0),new GradientAlphaKey(.6f,.2f),new GradientAlphaKey(0,1)});fade.color=gradient;}}
 }
}
