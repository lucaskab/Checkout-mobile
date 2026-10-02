using System;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;

namespace Checkout {
 public sealed class CheckoutEventVisuals:MonoBehaviour {
  public static readonly string[] EventIds={"hora-do-pico","pagamento-caiu","influenciadora-local","feira-do-bairro","desconto-atacadista","rota-livre","equipe-inspirada","treinamento-expresso","caixa-da-sorte","dia-perfeito","chuva-forte","obras-na-rua","concorrente-em-promocao","clientes-economicos","instabilidade-nos-caixas","alta-do-combustivel","transito-pesado","manutencao-de-equipamentos","equipe-cansada","fiscalizacao-surpresa"};
 class Motion {public Transform root;public Vector3 home,dir,scale;public Quaternion rot;public string kind;public float phase,range,speed;}
  class StreetlightState {public Light light;public bool enabled;public float intensity,range,spotAngle;}
  class GlowState {public Renderer renderer;public Material[] original,glowing;}
  readonly Dictionary<string,GameObject> scenes=new Dictionary<string,GameObject>();
  readonly Dictionary<string,List<Motion>> motions=new Dictionary<string,List<Motion>>();
  readonly List<StreetlightState> streetlights=new List<StreetlightState>();
  readonly List<GlowState> streetlightGlow=new List<GlowState>();
  readonly CheckoutEventAssets art=new CheckoutEventAssets();
  CheckoutRainPuddles rainPuddles;GameObject umbrellaPrefab;
  Light sun;Color sunColor,ambient,background;float sunIntensity;Camera view;Material particleMaterial;
  string building,active="";float clock,umbrellaRefresh;double expiresAt;
  public string ActiveId=>active;
  public static bool RoadWorks{get;private set;}
  public void Initialize(){sun=FindObjectsByType<Light>().FirstOrDefault(l=>l.type==LightType.Directional);if(sun){sunColor=sun.color;sunIntensity=sun.intensity;}ambient=RenderSettings.ambientLight;view=Camera.main;if(view)background=view.backgroundColor;particleMaterial=new Material(Shader.Find("Sprites/Default"));rainPuddles=gameObject.AddComponent<CheckoutRainPuddles>();rainPuddles.Initialize();umbrellaPrefab=Resources.Load<GameObject>("Rain/StreetUmbrella");EnsureOriginalStreetlights();CacheStreetlights();CacheStreetlightGlow();}
  MarketEvent lastSnapshot;bool previewing;
  public bool Previewing=>previewing;
  public void Apply(MarketEvent value){lastSnapshot=value;if(previewing)return;string id=value!=null&&value.endsAt>DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()?value.id:"";expiresAt=value?.endsAt??0;SetEvent(id??"");}
  // Editor/dev preview: shows an event regardless of the game store; an empty id hands control back to the snapshots.
  public void Preview(string id){if(string.IsNullOrEmpty(id)){previewing=false;Apply(lastSnapshot);return;}previewing=true;expiresAt=DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()+3600000;SetEvent(id);}
  void SetEvent(string id){if(active==id)return;if(scenes.TryGetValue(active,out var previous)){previous.SetActive(false);foreach(var particles in previous.GetComponentsInChildren<ParticleSystem>(true))particles.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);}active=id;RoadWorks=id=="obras-na-rua";clock=0;umbrellaRefresh=0;rainPuddles.SetRaining(id=="chuva-forte");SetCustomerUmbrellas(id=="chuva-forte");
   RestoreLight();SetStreetlights(id=="chuva-forte"||night);if(string.IsNullOrEmpty(id)){if(night)NightLight();return;}
   if(scenes.TryGetValue(id,out var stale)&&builtFor.TryGetValue(id,out var key)&&key!=LayoutKey()){Destroy(stale);scenes.Remove(id);}
   if(!scenes.TryGetValue(id,out var scene)){building=id;builtFor[id]=LayoutKey();scene=new GameObject("Event · "+id);scene.transform.SetParent(transform,false);scene.SetActive(false);scenes[id]=scene;motions[id]=new List<Motion>();Build(id,scene.transform);}
   foreach(var motion in motions[id]){motion.root.localPosition=motion.home;motion.root.localRotation=motion.rot;motion.root.localScale=motion.scale;}scene.SetActive(true);foreach(var particles in scene.GetComponentsInChildren<ParticleSystem>())particles.Play();
   if(id=="chuva-forte"){if(sun){sun.color=new Color(.66f,.77f,.94f);sun.intensity=sunIntensity*.68f;}RenderSettings.ambientLight=new Color(.39f,.46f,.55f);if(view)view.backgroundColor=new Color(.52f,.63f,.66f);}
   if(id=="dia-perfeito"&&sun){sun.color=new Color(1,.94f,.75f);sun.intensity=sunIntensity*1.08f;}
   if(night)NightLight();
  }
  // Night turn: a dark blue sky over whatever the event set, with the street lights on.
  bool night;
  public void SetNight(bool value){if(night==value)return;night=value;var id=active;active="\u0000";SetEvent(id);}
  void NightLight(){if(sun){sun.color=new Color(.55f,.64f,.98f);sun.intensity=(sun.intensity>0?sun.intensity:sunIntensity)*.28f;}RenderSettings.ambientLight=new Color(.16f,.19f,.31f);if(view)view.backgroundColor=new Color(.07f,.09f,.17f);}
  void SetCustomerUmbrellas(bool enabled){foreach(var customer in FindObjectsByType<MarketCharacterAnimator>(FindObjectsInactive.Include).Where(c=>c.GetComponent<CheckoutCityPedestrian>()||c.GetComponent<CheckoutCityAppearance>())){var pedestrian=customer.GetComponent<CheckoutCityPedestrian>();var rig=customer.GetComponent<MarketRainUmbrellaRig>();if(enabled&&!rig)rig=customer.gameObject.AddComponent<MarketRainUmbrellaRig>();if(!rig)continue;rig.Initialize(customer.animationPlayer,umbrellaPrefab);rig.SetRainShelter(enabled&&!(pedestrian&&pedestrian.IsSheltered));}}
  void Update(){if(active=="chuva-forte"&&(umbrellaRefresh+=Time.deltaTime)>.5f){umbrellaRefresh=0;SetCustomerUmbrellas(true);}if(string.IsNullOrEmpty(active))return;if(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()>=expiresAt){SetEvent("");return;}clock+=Time.deltaTime;
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
    case "sway":m.root.localRotation=m.rot*Quaternion.Euler(Mathf.Sin(t*2.3f)*7,0,Mathf.Sin(t*1.7f)*14);break;
   }}
  }
  void RestoreLight(){if(sun){sun.color=sunColor;sun.intensity=sunIntensity;}RenderSettings.ambientLight=ambient;if(view)view.backgroundColor=background;}
  void EnsureOriginalStreetlights(){var world=FindAnyObjectByType<MarketSimulation>();if(!world||world.world.Find("City Circulation Repairs/Original street lights"))return;var group=new GameObject("Original street lights").transform;group.SetParent(world.world,false);var positions=new[]{new Vector3(-27.7f,.13f,-10),new Vector3(-27.7f,.13f,8),new Vector3(-27.7f,.13f,26),new Vector3(27.7f,.13f,-9),new Vector3(27.7f,.13f,9),new Vector3(27.7f,.13f,27),new Vector3(-12,.13f,34.3f),new Vector3(12,.13f,34.3f)};foreach(var position in positions){var direction=position.z>33?Vector3.back:Vector3.left*Mathf.Sign(position.x);var light=new GameObject("Original street spotlight").AddComponent<Light>();light.transform.SetParent(group,false);light.transform.position=position+direction*.73f+Vector3.up*3.79f;light.transform.rotation=Quaternion.LookRotation(Vector3.down+direction*.3f);light.type=LightType.Spot;light.color=new Color(1,.82f,.53f);light.intensity=3;light.range=8;light.spotAngle=90;light.shadows=LightShadows.None;light.enabled=false;}}
  void CacheStreetlights(){foreach(var light in FindObjectsByType<Light>(FindObjectsInactive.Include).Where(l=>l.type==LightType.Spot&&l.name.ToLowerInvariant().Contains("spotlight")))streetlights.Add(new StreetlightState{light=light,enabled=light.enabled,intensity=light.intensity,range=light.range,spotAngle=light.spotAngle});}
  void CacheStreetlightGlow(){foreach(var renderer in FindObjectsByType<Renderer>(FindObjectsInactive.Include).Where(r=>r.name=="Luminous lens"||r.sharedMaterials.Any(m=>m&&m.name.Contains("CityLamp")))){var original=renderer.sharedMaterials;var glowing=original.Select(m=>{if(!m||!m.HasProperty("_EmissionColor")||(renderer.name!="Luminous lens"&&!m.name.Contains("CityLamp")))return m;var copy=new Material(m){name=m.name+" (Rain glow)"};copy.EnableKeyword("_EMISSION");copy.SetColor("_EmissionColor",Color.black);return copy;}).ToArray();renderer.sharedMaterials=glowing;streetlightGlow.Add(new GlowState{renderer=renderer,original=original,glowing=glowing});}}
  void SetStreetlights(bool enabled){foreach(var state in streetlights){if(!state.light)continue;state.light.enabled=enabled||state.enabled;state.light.intensity=enabled?Mathf.Max(state.intensity*1.7f,5):state.intensity;state.light.range=enabled?Mathf.Max(state.range*1.4f,11):state.range;state.light.spotAngle=enabled?Mathf.Max(state.spotAngle,100):state.spotAngle;}foreach(var state in streetlightGlow)foreach(var material in state.glowing)if(material)material.SetColor("_EmissionColor",enabled?new Color(1,.62f,.28f)*3.5f:Color.black);}
  void RestoreStreetlightMaterials(){foreach(var state in streetlightGlow){if(state.renderer)state.renderer.sharedMaterials=state.original;foreach(var material in state.glowing)if(material&& !state.original.Contains(material))Destroy(material);}streetlightGlow.Clear();}
  void OnDestroy(){RoadWorks=false;RestoreLight();SetStreetlights(false);RestoreStreetlightMaterials();art.Dispose();if(particleMaterial)Destroy(particleMaterial);}
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
  string LayoutKey(){var layout=GetComponent<CheckoutMarketLayout>();return layout&&layout.State!=null?layout.State.widthScale.ToString("0.00")+"x"+layout.State.depthScale.ToString("0.00"):"";}
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
  void Build(string id,Transform root){var door=Door;var till=Till;switch(id){
   case "hora-do-pico":{
    // Rush hour: a stanchion queue along the storefront to the door, shoppers with carts waiting and more arriving.
    M(root,"QueueStanchions",door+new Vector3(-2.9f,0,-1.9f),0);
    string[] people={"Customer_01","Customer_03","Customer_04","Customer_06"};
    for(int i=0;i<4;i++){var spot=Group(root,"Waiting shopper",door+new Vector3(-1.2f-i*1.25f,0,-1.9f));art.Actor(spot,people[i],Vector3.zero,90,"Idle");if(i%2==1)M(spot,"CartFull",new Vector3(-.62f,0,.05f),-90,.9f);Queue(spot,Vector3.right,i*.9f);}
    for(int i=0;i<3;i++){var walker=Group(root,"Arriving shopper",door+new Vector3(-9,0,-3.3f));art.Actor(walker,people[(i+1)%4],Vector3.zero,90,"Walking");Lane(walker,Vector3.right,7,1.1f,i*2.3f);}
    Icon(root,"UpArrow",door+new Vector3(-3.2f,3.3f,-1.9f),1.2f,"float");break;}
   case "pagamento-caiu":{
    // Payday: shoppers with loaded carts heading to the till, coins over the counter and a bulging money bag.
    string[] shoppers={"Customer_02","Customer_05","Customer_07"};
    for(int i=0;i<3;i++){var spot=Group(root,"Payday shopper",till+new Vector3(2.2f+i*1.3f,0,.6f+i*.5f));art.Actor(spot,shoppers[i],Vector3.zero,ActorFace,"Idle");M(spot,"CartFull",new Vector3(.2f,0,-.7f),Face,.9f);}
    Icon(root,"MoneyBag",till+new Vector3(.2f,2.8f,.3f),1.5f);
    for(int i=0;i<5;i++)Icon(root,"GoldCoin",till+new Vector3(-1.4f+i*.95f,2.1f+(i%2)*.5f,-.4f),1.1f,"coin");
    M(root,"CoinStack",till+new Vector3(-1.3f,.5f,-.2f),Face,.9f);break;}
   case "influenciadora-local":{
    // Creator corner on the sidewalk right of the door: pastel backdrop, ring light and floating hearts.
    var corner=Group(root,"Creator filming corner",door+new Vector3(4.6f,0,-2.5f));M(corner,"CreatorBackdrop",Vector3.zero,0);
    art.Actor(corner,"Customer_03",new Vector3(-.2f,.05f,.1f),170,"Idle");M(corner,"RingLight",new Vector3(.5f,.05f,-1.2f),200);
    for(int i=0;i<4;i++)Icon(root,"Heart",door+new Vector3(3.9f+i*.55f,2.8f,-2.4f),1.1f+(i%2)*.3f,"rise");break;}
   case "feira-do-bairro":{
    // Street fair on the front sidewalk: striped tents, the market's own produce stands and crates, bunting, neighbours.
    M(root,"FairStallRed",door+new Vector3(-5.4f,0,-2.3f),0);M(root,"FairStallTeal",door+new Vector3(5.2f,0,-2.3f),0);
    M(root,"GameFruitStand",door+new Vector3(-8.6f,0,-2.3f),Face+36,1);M(root,"GameFruitStand",door+new Vector3(8.4f,0,-2.3f),Face+36,1);
    foreach(var x in new[]{-3.2f,3f})M(root,"GameVegetableCrate",door+new Vector3(x,0,-3.3f),Face+20,1.1f);
    M(root,"FairBunting",door+new Vector3(0,0,-3.6f),0);
    art.Actor(Group(root,"Fair shopper",door+new Vector3(-5.8f,0,-3.9f)),"Customer_04",Vector3.zero,10,"Idle");
    art.Actor(Group(root,"Fair shopper",door+new Vector3(4.6f,0,-3.9f)),"Customer_06",Vector3.zero,-15,"Idle");
    Icon(root,"BalloonBunch",door+new Vector3(-7f,0,-3.4f),1,"float");Icon(root,"BalloonBunch",door+new Vector3(7f,0,-3.4f),1,"float");break;}
   case "desconto-atacadista":{
    // Wholesale drop at the warehouse doorstep: stacks of the market's cardboard boxes, pallet jack, stocker and price board.
    // At the warehouse doorstep once the storage is bought; before that, on the sidewalk right of the entrance.
    var house=WorldBounds(Storage,new Bounds(W(3,.34f,19),new Vector3(8,4,6)));bool storage=Has(Storage);
    var dock=storage?new Vector3(house.center.x+1.2f,.34f,house.min.z-2.2f):door+new Vector3(5.6f,0,-2.4f);
    var yard=Group(root,"Wholesale pallet offer",dock);
    for(int p=0;p<2;p++){var pallet=Group(yard,"Wholesale pallet",new Vector3(-1.1f+p*2.2f,0,p*.3f));M(pallet,"Pallet",Vector3.zero,0);
     for(int layer=0;layer<3-p;layer++)for(int k=0;k<4;k++)M(pallet,"GameCardboardBox",new Vector3(-.32f+(k%2)*.64f,.18f+layer*.44f,-.28f+(k/2)*.56f),(k+layer)%2*180+layer*4,1);}
    M(yard,"PalletJack",new Vector3(-2.6f,0,-1.1f),Face+70);M(yard,"WholesaleBoard",new Vector3(2.9f,0,-.8f));
    art.Actor(yard,"Worker_Stocker",new Vector3(-.2f,0,-1.5f),ActorFace,"Idle");
    Icon(root,"PriceTag",dock+Vector3.up*3.9f,1.5f);break;}
   case "rota-livre":{
    // Free route: the delivery truck cruises the front street over green lane arrows, green light at the corner.
    var van=M(root,"GameDeliveryTruck",W(2,.15f,-14),90);Lane(van,Vector3.left,30,3.4f);
    for(int i=0;i<7;i++)M(root,"LaneArrow",W(-10+i*3.6f,.16f,-14),-90,1.1f);
    M(root,"GameTrafficLight",W(14.2f,.34f,-12.3f),-90,1);var star=M(van,"StarBadge",new Vector3(0,3.4f,0),0,1.1f);Animated(star,"coin");break;}
   case "equipe-inspirada":{
    // Inspired team: gold stars above every counter worker, fresh bread racks and a team banner.
    foreach(var worker in new[]{"Worker_Baker","Worker_Butcher","Worker_Fishmonger","Worker_Cashier"}){var at=WorldPoint(worker,Vector3.zero);if(at!=Vector3.zero)Icon(root,"StarBadge",at+Vector3.up*2.6f,1.15f);}
    var baker=WorldPoint("Worker_Baker",W(-6,.74f,5));M(root,"BreadRack",baker+new Vector3(1.6f,0,-1.1f),Face+20);M(root,"BreadRack",baker+new Vector3(2.7f,0,-1.5f),Face+20);
    M(root,"TeamBanner",In(1.5f,.34f,7.9f),0);
    for(int i=0;i<3;i++)Icon(root,"EnergyBolt",In(-3.5f+i*4.2f,3.3f,1.5f),1.3f,"float");break;}
   case "treinamento-expresso":{
    // Express training in the free floor area: whiteboard, trainee chairs and the instructor.
    var training=Group(root,"Staff training station",In(5.4f,.74f,-1.8f));
    M(training,"TrainingBoard",new Vector3(0,0,.9f),Face);M(training,"TrainingChairs",new Vector3(-.4f,0,-.8f),Face+180);
    art.Actor(training,"Worker_Stocker",new Vector3(1.2f,0,.7f),ActorFace-20,"Idle");
    art.Actor(training,"Worker_Cashier",new Vector3(-1.1f,0,-1.5f),30,"Idle");art.Actor(training,"Worker_Baker",new Vector3(.2f,0,-1.7f),10,"Idle");
    Icon(root,"GraduationCap",In(5.4f,3.4f,-1.2f),1.4f);break;}
   case "caixa-da-sorte":{
    // Lucky checkout: a giant gift beside the till, a sign, confetti cannons, confetti and coins.
    M(root,"GiftBox",till+new Vector3(3.1f,0,1.3f),Face,1.2f);M(root,"LuckySign",till+new Vector3(4.4f,0,.7f));
    M(root,"ConfettiCannon",till+new Vector3(2.1f,0,2.1f),Face+40);M(root,"ConfettiCannon",till+new Vector3(4.2f,0,2.2f),Face-40);Confetti(root,till+new Vector3(.4f,2.2f,-.3f));
    for(int i=0;i<3;i++)Icon(root,"GoldCoin",till+new Vector3(-.6f+i*.8f,2.4f+(i%2)*.3f,-.2f),1.1f,"coin");break;}
   case "dia-perfeito":{
    // Perfect day: flower arch over the entrance path, the market's flower planters, balloons and a smiling sun.
    M(root,"FlowerArch",door+new Vector3(0,0,-1.7f),0,1.25f);
    foreach(var x in new[]{-3.1f,3.1f})M(root,"GameFlowerPlanter",door+new Vector3(x,0,-2.7f),0,1);
    Icon(root,"BalloonBunch",door+new Vector3(-4.4f,0,-2.2f),1,"float");Icon(root,"BalloonBunch",door+new Vector3(4.4f,0,-2.2f),1,"float");
    Icon(root,"SunBadge",door+new Vector3(-4.5f,5.2f,2),1.8f);Confetti(root,door+new Vector3(0,3.2f,-1.7f));break;}
   case "chuva-forte":BuildRain(root);break;
   case "obras-na-rua":{
    // Curbside trench in the westbound lane between the entrance crossing and the car drop-off; the neighborhood cars detour around it.
    var works=Group(root,"Street road works",P(2.55f,.15f,-13.05f));var prefab=Resources.Load<GameObject>("RoadWorks/StreetRoadWorks");
    if(prefab){var model=Instantiate(prefab,works,false);model.transform.localRotation=Quaternion.Euler(0,180,0);foreach(var part in model.GetComponentsInChildren<Transform>(true))part.gameObject.layer=2;PaintNamed(model.transform);}break;}
   case "concorrente-em-promocao":{
    // Rival pop-up on the opposite sidewalk: magenta tent, huge promo board and a dancing tube man.
    var rival=Group(root,"Competitor promotional stand",W(7.5f,.34f,-26.4f));
    M(rival,"RivalTent",Vector3.zero,0);M(rival,"RivalBoard",new Vector3(-2.6f,0,.4f),0);
    var tube=M(rival,"TubeMan",new Vector3(2.5f,0,-.3f),Face);Animated(tube,"sway");
    for(int i=0;i<2;i++){var w=Group(root,"Tempted shopper",W(1.5f,.34f,-25.2f));art.Actor(w,i==0?"Customer_05":"Customer_08",Vector3.zero,90,"Walking");Lane(w,Vector3.right,5,.9f,i*2.6f);}
    Icon(root,"PriceTag",W(7.5f,4.4f,-26.4f),1.6f);break;}
   case "clientes-economicos":{
    // Thrifty shoppers comparing prices: shopping lists, calculators and bargain tags over their heads.
    for(int i=0;i<2;i++){var shopper=Group(root,"Comparing prices",In(-.2f+i*3.2f,.74f,-3.2f));art.Actor(shopper,i==0?"Customer_04":"Customer_09",Vector3.zero,ActorFace,"Idle");M(shopper,i==0?"CartEmpty":"CartFull",new Vector3(.7f,0,.1f),Face+60,.9f);
     Icon(root,i==0?"Calculator":"ShoppingList",In(-.2f+i*3.2f,2.9f,-3.2f),1.4f);}
    M(root,"CouponStand",door+new Vector3(1.9f,.4f,1.6f));Icon(root,"PriceTag",In(1.4f,3.5f,-2.6f),1.1f);break;}
   case "instabilidade-nos-caixas":{
    // Unstable tills: error screen on the POS, sparks, a pulsing warning, an out-of-order sign and a technician.
    M(root,"BrokenTerminal",till+new Vector3(-.2f,.45f,-.7f),Face,1.1f);Icon(root,"WarningBadge",till+new Vector3(0,2.7f,-.4f),1.2f,"pulse");
    M(root,"OutOfOrderSign",till+new Vector3(1.5f,0,-1.6f));M(root,"Toolbox",till+new Vector3(2.4f,0,-.7f),Face+25);
    M(root,"GameWorker",till+new Vector3(2.7f,0,.3f),Face-70,1);
    Sparks(root,till+new Vector3(-.2f,1.3f,-.8f));break;}
   case "alta-do-combustivel":{
    // Fuel price spike at the delivery bays: pump with a climbing price next to the trucks, barrels, red arrow.
    // Beside the delivery trucks once the loading yard exists; before that, a delivery truck refuelling at the curb.
    bool yardOpen=Has("Anim_Truck_5");var bay=WorldBounds("Anim_Truck_5",new Bounds(W(9,.34f,13),new Vector3(2,2,4)));
    if(!yardOpen){M(root,"GameDeliveryTruck",W(9.6f,.15f,-14.1f),90);bay=new Bounds(W(9.6f,1.2f,-14.1f),new Vector3(4.6f,2.6f,2));}
    var fuel=Group(root,"Fuel price increase",yardOpen?new Vector3(bay.min.x-1.3f,.34f,bay.center.z-.6f):W(9.8f,.34f,-11.9f));M(fuel,"FuelPump",Vector3.zero,Face+36);M(fuel,"OilBarrels",new Vector3(-.3f,0,1.6f),Face);M(fuel,"JerryCan",new Vector3(.6f,0,-.9f),Face+30);
    art.Actor(fuel,"Worker_Delivery",new Vector3(-.9f,0,-.6f),ActorFace,"Idle");
    Icon(root,"UpArrow",new Vector3(bay.center.x,bay.max.y+1.6f,bay.center.z),1.5f,"float");break;}
   case "transito-pesado":{
    // Heavy traffic: a bumper-to-bumper line of the city's cars on the east street, exhaust, a slow sign and a grumpy cloud.
    string[] cars={"GameCartoonCar","GameStylizedCar","GameToyVan","GameCartoonCar","GameStylizedCar","GameToyVan"};
    for(int i=0;i<6;i++){var car=M(root,cars[i],W(22,.15f,-9+i*4.4f),0);Queue(car,Vector3.back,i*.6f);Exhaust(car);}
    M(root,"SlowSign",W(20,.34f,-11),-90);Icon(root,"AngryCloud",W(22,4.2f,1),1.5f,"float");break;}
   case "manutencao-de-equipamentos":{
    // Equipment maintenance at the bakery: taped-off repair zone in front of the oven counter, technician, ladder, gears, steam.
    var oven=WorldPoint("Worker_Baker",W(-6,.74f,5));
    var zone=Group(root,"Production repair station",oven+new Vector3(1.6f,0,-2.2f));M(zone,"RepairStation",Vector3.zero,0);M(zone,"StepLadder",new Vector3(.9f,0,.5f),Face+20);M(zone,"Toolbox",new Vector3(-.8f,0,-.4f),Face+10);M(zone,"MaintenanceSign",new Vector3(1.6f,0,-1.3f));
    M(zone,"GameWorker",new Vector3(-.3f,0,.3f),Face+150,1);
    Icon(root,"Gear",oven+new Vector3(.6f,2.8f,.2f),1.2f,"spin");Icon(root,"Gear",oven+new Vector3(1.7f,2.4f,.2f),.8f,"spin");
    Particles(root,"Steam leak",oven+new Vector3(.4f,1.6f,.4f),P(.4f,.3f,.4f),new Color(.9f,.93f,.9f,.45f),14,1.8f,.6f,.35f,false);break;}
   case "equipe-cansada":{
    // Tired team: break corner beside the warehouse, coffee, drowsy workers swaying and floating Zzz.
    // Beside the warehouse once it exists; before that, outside the store's east wall by the service door.
    var house=WorldBounds(Storage,new Bounds(W(3,.34f,19),new Vector3(8,4,6)));var shell=WorldBounds("Building",new Bounds(W(0,.74f,-2),new Vector3(18,3,14)));
    var spot=Has(Storage)?new Vector3(house.min.x-2.2f,.34f,house.center.z-.5f):new Vector3(shell.max.x+2f,.34f,shell.max.z-2.6f);
    var rest=Group(root,"Staff break corner",spot);M(rest,"BreakCorner",Vector3.zero,Face);
    var a=art.Actor(rest,"Worker_Cashier",new Vector3(-.9f,0,-1.5f),ActorFace,"Idle",.45f);Animated(a,"rock");
    var b=art.Actor(rest,"Worker_Baker",new Vector3(.4f,0,-1.7f),ActorFace-20,"Idle",.4f);Animated(b,"rock");
    Icon(root,"Zzz",spot+new Vector3(-.7f,2.6f,-.6f),1.3f,"float");Icon(root,"Zzz",spot+new Vector3(.3f,2.8f,-.9f),1f,"float");Icon(root,"CoffeeCup",spot+new Vector3(1.2f,2.7f,-.2f),1.3f);
    Particles(root,"Coffee steam",spot+new Vector3(.8f,1.2f,.3f),P(.1f,.05f,.1f),new Color(.95f,.92f,.86f,.4f),6,1.6f,.35f,.18f,false);break;}
   case "fiscalizacao-surpresa":{
    // Surprise inspection just inside the door: inspector, folding table, forms, badge and a magnifying glass.
    var visit=Group(root,"Inspection visit",door+new Vector3(4.4f,.4f,1.9f));M(visit,"InspectionKit",new Vector3(.9f,0,.2f),Face+10);
    art.Actor(visit,"Customer_08",Vector3.zero,ActorFace,"Idle");
    Icon(root,"ClipboardIcon",door+new Vector3(4.4f,3.1f,1.9f),1.2f);Icon(root,"Magnifier",door+new Vector3(5.5f,3.3f,2.1f),1.2f);M(visit,"IdBadge",new Vector3(-.3f,1.3f,-.25f),Face,.35f);break;}
   default:Debug.LogWarning("CHECKOUT_EVENT_VISUAL_MISSING "+id);break;
  }}
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
