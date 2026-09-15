using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout {
 public sealed class CheckoutEventVisuals:MonoBehaviour {
  public static readonly string[] EventIds={"hora-do-pico","pagamento-caiu","influenciadora-local","feira-do-bairro","desconto-atacadista","rota-livre","equipe-inspirada","treinamento-expresso","caixa-da-sorte","dia-perfeito","chuva-forte","obras-na-rua","concorrente-em-promocao","clientes-economicos","instabilidade-nos-caixas","alta-do-combustivel","transito-pesado","manutencao-de-equipamentos","equipe-cansada","fiscalizacao-surpresa"};
  class Motion {public Transform root;public Vector3 home;public string kind;public float phase;}
  readonly Dictionary<string,GameObject> scenes=new Dictionary<string,GameObject>();
  readonly Dictionary<string,List<Motion>> motions=new Dictionary<string,List<Motion>>();
  readonly CheckoutEventAssets art=new CheckoutEventAssets();
  Light sun;Color sunColor,ambient,background;float sunIntensity;Camera view;Material particleMaterial;
  string building,active="";float clock;double expiresAt;
  public string ActiveId=>active;
  public void Initialize(){sun=FindObjectsByType<Light>().FirstOrDefault(l=>l.type==LightType.Directional);if(sun){sunColor=sun.color;sunIntensity=sun.intensity;}ambient=RenderSettings.ambientLight;view=Camera.main;if(view)background=view.backgroundColor;particleMaterial=new Material(Shader.Find("Sprites/Default"));}
  public void Apply(MarketEvent value){string id=value!=null&&value.endsAt>DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()?value.id:"";expiresAt=value?.endsAt??0;SetEvent(id??"");}
  void SetEvent(string id){if(active==id)return;if(scenes.TryGetValue(active,out var previous)){previous.SetActive(false);foreach(var particles in previous.GetComponentsInChildren<ParticleSystem>(true))particles.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);}active=id;clock=0;
   RestoreLight();if(string.IsNullOrEmpty(id))return;
   if(!scenes.TryGetValue(id,out var scene)){building=id;scene=new GameObject("Event · "+id);scene.transform.SetParent(transform,false);scene.SetActive(false);scenes[id]=scene;motions[id]=new List<Motion>();Build(id,scene.transform);}
   foreach(var motion in motions[id]){motion.root.localPosition=motion.home;motion.root.localRotation=Quaternion.identity;}scene.SetActive(true);foreach(var particles in scene.GetComponentsInChildren<ParticleSystem>())particles.Play();
   if(id=="chuva-forte"){if(sun){sun.color=new Color(.66f,.77f,.94f);sun.intensity=sunIntensity*.68f;}RenderSettings.ambientLight=new Color(.39f,.46f,.55f);if(view)view.backgroundColor=new Color(.52f,.63f,.66f);}
   if(id=="dia-perfeito"&&sun){sun.color=new Color(1,.94f,.75f);sun.intensity=sunIntensity*1.08f;}
  }
  void Update(){if(string.IsNullOrEmpty(active))return;if(DateTimeOffset.UtcNow.ToUnixTimeMilliseconds()>=expiresAt){SetEvent("");return;}clock+=Time.deltaTime;
   foreach(var m in motions[active]){float t=clock+m.phase;switch(m.kind){
    case "float":m.root.localPosition=m.home+Vector3.up*Mathf.Sin(t*1.5f)*.14f;break;
    case "coin":m.root.localPosition=m.home+Vector3.up*Mathf.Sin(t*1.8f)*.13f;m.root.localRotation=Quaternion.Euler(0,t*45,0);break;
    case "drive":m.root.localPosition=m.home+Vector3.forward*(Mathf.PingPong(t*1.25f,6)-3);break;
    case "queue":m.root.localPosition=m.home+Vector3.forward*Mathf.Sin(t*.45f)*.12f;break;
    case "pulse":m.root.localScale=Vector3.one*(1+Mathf.Sin(t*2)*.06f);break;
    case "rock":m.root.localRotation=Quaternion.Euler(0,0,Mathf.Sin(t)*4);break;
   }}
  }
  void RestoreLight(){if(sun){sun.color=sunColor;sun.intensity=sunIntensity;}RenderSettings.ambientLight=ambient;if(view)view.backgroundColor=background;}
  void OnDestroy(){RestoreLight();art.Dispose();if(particleMaterial)Destroy(particleMaterial);}
  static Vector3 P(float x,float y,float z)=>new Vector3(x,y,z);
  void Animated(Transform prop,string kind){art.Batch(prop);motions[building].Add(new Motion{root=prop,home=prop.localPosition,kind=kind,phase=motions[building].Count*.7f});}
  void Prop(Transform prop)=>art.Batch(prop);
  Transform Group(Transform root,string name,Vector3 p)=>art.Group(root,name,p);
  void Build(string id,Transform root){switch(id){
   case "hora-do-pico":
    for(int i=0;i<4;i++){var arrival=Group(root,"Busy entrance group",P(-4.6f+i*1.2f,.34f,-10.4f));art.Person(arrival,Vector3.zero,i%2==0?"ECA663":"64A8A1");art.Cart(arrival,P(.55f,0,-.7f));Animated(arrival,"queue");}break;
   case "pagamento-caiu":
    for(int i=0;i<3;i++){var cart=art.Cart(root,P(-4.9f+i*1.5f,.74f,-6.1f));Prop(cart);Animated(art.Coin(root,P(-4.9f+i*1.5f,2.65f,-6.1f)),"coin");}break;
   case "influenciadora-local":{
    var stage=Group(root,"Creator filming corner",P(-5,.35f,-10.2f));art.Part(stage,"Photo mat",P(0,.03f,0),P(2.4f,.06f,1.7f),"D99BAC");art.Person(stage,P(-.5f,0,0),"B984AD");art.Bar(stage,P(.65f,0,-.5f),P(.65f,1.7f,-.5f),.06f,"3E5365");for(int i=-1;i<=1;i++)art.Bar(stage,P(.65f,.55f,-.5f),P(.65f+i*.38f,0,-.7f+Mathf.Abs(i)*.35f),.045f,"3E5365");for(int i=0;i<16;i++){float a=i*Mathf.PI/8;art.Part(stage,"Ring light",P(.65f+Mathf.Cos(a)*.35f,1.9f+Mathf.Sin(a)*.35f,-.5f),Vector3.one*.1f,"FFF2CC",PrimitiveType.Sphere);}art.Part(stage,"Phone",P(.65f,1.9f,-.48f),P(.2f,.34f,.06f),"3E5365");Prop(stage);for(int i=0;i<3;i++)Animated(Heart(root,P(-5.6f+i*.5f,2.6f+i*.28f,-10.2f)),"float");break;}
   case "feira-do-bairro":{
    var stalls=Group(root,"Street fair stalls",P(0,.34f,-11.3f));art.Stall(stalls,P(-5,0,0),"EC9471");art.Stall(stalls,P(3,0,0),"65ADA2");Prop(stalls);for(int i=0;i<7;i++)Animated(art.Balloon(root,P(-6+i*1.5f,3.4f,-11.3f),i%2==0?"EFA877":"89BEB2"),"float");break;}
   case "desconto-atacadista":{
    var delivery=Group(root,"Wholesale pallet offer",P(8.7f,.34f,7));art.Part(delivery,"Pallet",P(0,.1f,0),P(2.3f,.2f,1.7f),"906B4E");for(int i=0;i<6;i++)art.Crate(delivery,P((i%3-1)*.72f,.55f+(i/3)*.66f,0));var board=art.Board(delivery,P(1.8f,0,0),"69A69A");art.Percent(board,P(0,1.65f,-.16f));Prop(delivery);break;}
   case "rota-livre":{
    Animated(art.Vehicle(root,P(10.7f,.3f,1),"67B6A5",true),"drive");var route=Group(root,"Clear delivery lane",P(10.7f,.34f,-3));for(int i=0;i<4;i++){art.Bar(route,P(-.4f,.02f,i*1.3f+.4f),P(0,.02f,i*1.3f),.11f,"DAF1C4");art.Bar(route,P(0,.02f,i*1.3f),P(.4f,.02f,i*1.3f+.4f),.11f,"DAF1C4");}Prop(route);break;}
   case "equipe-inspirada":
    foreach(var p in new[]{P(-5.5f,2.8f,4),P(1.5f,2.8f,4.3f),P(6.5f,2.8f,4.3f)})Animated(Bolt(root,p,"F6CD67"),"float");for(int i=0;i<3;i++){var tray=Group(root,"Freshly finished production",P(-5.6f+i*1.05f,1.8f,3.8f));art.Part(tray,"Tray",Vector3.zero,P(.7f,.07f,.5f),"9DBBB7");for(int j=0;j<3;j++)art.Part(tray,"Bread",P((j-1)*.2f,.12f,0),P(.16f,.18f,.33f),"EEC276",PrimitiveType.Sphere);Prop(tray);}break;
   case "treinamento-expresso":{
    var training=Group(root,"Staff training station",P(-6.2f,.74f,6));var board=art.Board(training,Vector3.zero,"598E83");for(int i=0;i<3;i++){art.Bar(board,P(-.6f,1.85f-i*.23f,-.17f),P(-.49f,1.75f-i*.23f,-.17f),.045f,"FFE3A4");art.Bar(board,P(-.49f,1.75f-i*.23f,-.17f),P(-.31f,1.95f-i*.23f,-.17f),.045f,"FFE3A4");art.Part(board,"Lesson",P(.21f,1.83f-i*.23f,-.17f),P(.6f,.045f,.03f),"E3EED8");}art.Person(training,P(1.3f,0,-.1f),"5E8BA6",true);Prop(training);break;}
   case "caixa-da-sorte":{
    var till=Group(root,"Lucky checkout gift",P(-4.7f,1.3f,-5));art.Part(till,"Gift box",Vector3.zero,P(.65f,.5f,.6f),"83BCA5");art.Part(till,"Ribbon",P(0,.02f,-.31f),P(.13f,.54f,.02f),"FFE2A1");Prop(till);for(int i=0;i<3;i++)Animated(art.Coin(root,P(-5+i*.65f,2.6f,-4.8f)),"coin");break;}
   case "dia-perfeito":{
    var garden=Group(root,"Celebration entrance",P(-1.7f,.34f,-9.2f));for(int side=-1;side<=1;side+=2){art.Part(garden,"Planter",P(side*2.1f,.4f,0),P(.7f,.8f,.7f),"D69F74");for(int i=0;i<3;i++){art.Bar(garden,P(side*2.1f,.75f,0),P(side*2.1f+(i-1)*.22f,1.3f,0),.04f,"6B9B72");art.Part(garden,"Flower",P(side*2.1f+(i-1)*.22f,1.35f,0),Vector3.one*.24f,"F3CA7D",PrimitiveType.Sphere);}}Prop(garden);for(int i=0;i<5;i++)Animated(art.Balloon(root,P(-4+i*1.1f,3.1f,-9.3f),i%2==0?"F2CD7C":"A2C9AF"),"float");break;}
   case "chuva-forte":BuildRain(root);break;
   case "obras-na-rua":{
    var works=Group(root,"Street excavation",P(10.6f,.34f,-3));art.Part(works,"Excavated road",P(0,.02f,0),P(2.6f,.05f,3),"755E51");for(int i=0;i<4;i++)art.Cone(works,P(i%2==0?-1.4f:1.4f,0,-1.2f+(i/2)*2.4f));art.Barrier(works,P(0,0,-1.7f));for(int i=0;i<6;i++)art.Part(works,"Rubble",P(Mathf.Sin(i*3)*.7f,.16f,Mathf.Cos(i*4)),P(.5f,.3f,.4f),"AE9782",PrimitiveType.Sphere);art.Toolbox(works,P(.4f,.1f,.4f));Prop(works);break;}
   case "concorrente-em-promocao":{
    var rival=Group(root,"Competitor promotional stand",P(9.9f,.34f,-8));var board=art.Board(rival,Vector3.zero,"D37669");art.Percent(board,P(0,1.65f,-.17f));art.Stall(rival,P(0,0,2.1f),"BA809D");Prop(rival);Animated(art.Balloon(root,P(11.1f,3.3f,-8),"C58DA6"),"float");break;}
   case "clientes-economicos":{
    for(int i=0;i<2;i++){var shopper=Group(root,"Comparing prices",P(-.6f+i*3,.74f,-2.8f));art.Person(shopper,Vector3.zero,"ABAA81",true);art.Part(shopper,"Calculator",P(-.3f,1.1f,-.34f),P(.32f,.5f,.08f),"485F67");art.Part(shopper,"Display",P(-.3f,1.23f,-.39f),P(.24f,.12f,.02f),"AAD3B9");for(int key=0;key<6;key++)art.Part(shopper,"Key",P(-.38f+(key%3)*.08f,1.06f-(key/3)*.08f,-.4f),P(.045f,.045f,.02f),"F2E5C6");Prop(shopper);}break;}
   case "instabilidade-nos-caixas":{
    var repair=Group(root,"Checkout terminal fault",P(-4.7f,1.5f,-4.9f));art.Part(repair,"Terminal",P(0,.3f,0),P(.8f,.65f,.18f),"435866");art.Part(repair,"Error screen",P(0,.3f,-.1f),P(.67f,.5f,.03f),"C97162");art.Bar(repair,P(-.16f,.14f,-.13f),P(.16f,.46f,-.13f),.07f,"FFE5C6");art.Bar(repair,P(.16f,.14f,-.13f),P(-.16f,.46f,-.13f),.07f,"FFE5C6");Animated(repair,"pulse");var tool=art.Toolbox(root,P(-5.6f,.74f,-4.4f));Prop(tool);break;}
   case "alta-do-combustivel":{
    var pump=Group(root,"Fuel price increase",P(10.4f,.34f,5.5f));art.Part(pump,"Pump base",P(0,.7f,0),P(.95f,1.4f,.65f),"D98661");art.Part(pump,"Pump top",P(0,1.68f,0),P(1.1f,.66f,.75f),"F3E7CF");art.Part(pump,"Display",P(0,1.75f,-.39f),P(.76f,.34f,.03f),"435865");art.Bar(pump,P(0,1.63f,-.42f),P(0,1.89f,-.42f),.05f,"F4C173");art.Bar(pump,P(-.13f,1.77f,-.42f),P(0,1.9f,-.42f),.05f,"F4C173");art.Bar(pump,P(0,1.9f,-.42f),P(.13f,1.77f,-.42f),.05f,"F4C173");art.Bar(pump,P(.57f,1.65f,0),P(.9f,.5f,0),.09f,"3C4B52");art.Bar(pump,P(.9f,.5f,0),P(.65f,1.15f,-.1f),.09f,"3C4B52");Prop(pump);break;}
   case "transito-pesado":
    for(int i=0;i<4;i++)Animated(art.Vehicle(root,P(10.6f,.34f,-7+i*3),i%2==0?"CA8766":"85A4B7"),"queue");break;
   case "manutencao-de-equipamentos":{
    var maintenance=Group(root,"Production repair station",P(1.5f,.74f,3.1f));art.Barrier(maintenance,Vector3.zero);art.Toolbox(maintenance,P(.4f,.1f,-.5f));art.Person(maintenance,P(1.3f,0,.2f),"D8A056",true);Prop(maintenance);Particles(root,"Steam leak",P(1.5f,2.3f,4.3f),P(.5f,.3f,.5f),new Color(.83f,.87f,.84f,.35f),12,1.8f,.5f,.3f,false);break;}
   case "equipe-cansada":{
    var rest=Group(root,"Staff break corner",P(-6.5f,.74f,5.8f));art.Part(rest,"Bench",P(0,.5f,0),P(1.9f,.15f,.65f),"A47755");for(int side=-1;side<=1;side+=2)art.Part(rest,"Bench leg",P(side*.7f,.25f,0),P(.14f,.5f,.5f),"4D6769");art.Cup(rest,P(-.5f,.8f,0));art.Cup(rest,P(.5f,.8f,0));Prop(rest);var person=art.Person(root,P(-5.2f,.74f,5.8f),"A6A38A");Animated(person,"rock");Particles(root,"Coffee steam",P(-7,1.75f,5.8f),P(.08f,.05f,.08f),new Color(.9f,.88f,.81f,.3f),4,1.5f,.3f,.12f,false);break;}
   case "fiscalizacao-surpresa":{
    var inspection=Group(root,"Inspection visit",P(-3.2f,.74f,-6.5f));art.Person(inspection,Vector3.zero,"5D809B",true);art.Part(inspection,"ID badge",P(-.15f,1.17f,-.18f),P(.13f,.19f,.02f),"E6C885");art.Part(inspection,"Document case",P(.6f,.35f,0),P(.55f,.48f,.18f),"4A5863");Prop(inspection);break;}
   default:Debug.LogWarning("CHECKOUT_EVENT_VISUAL_MISSING "+id);break;
  }}
  Transform Heart(Transform root,Vector3 p){var t=Group(root,"Floating heart",p);art.Part(t,"Heart left",P(-.12f,.1f,0),Vector3.one*.32f,"D98B9E",PrimitiveType.Sphere);art.Part(t,"Heart right",P(.12f,.1f,0),Vector3.one*.32f,"D98B9E",PrimitiveType.Sphere);art.Part(t,"Heart tip",P(0,-.06f,0),P(.29f,.29f,.2f),"D98B9E").localRotation=Quaternion.Euler(0,0,45);return t;}
  Transform Bolt(Transform root,Vector3 p,string color){var t=Group(root,"Energy bolt",p);art.Bar(t,P(.15f,.4f,0),P(-.15f,0,0),.16f,color);art.Bar(t,P(-.15f,0,0),P(.15f,0,0),.16f,color);art.Bar(t,P(.15f,0,0),P(-.15f,-.4f,0),.16f,color);return t;}
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
   var puddles=Group(root,"Wet pavement",Vector3.zero);for(int i=0;i<9;i++){float x=i<5?-6+i*2.3f:10.2f;float z=i<5?-10.5f:-6+(i-5)*4;art.Part(puddles,"Puddle",P(x,.355f,z),P(1.4f,.012f,.8f),"759CA8",PrimitiveType.Sphere);art.Part(puddles,"Water reflection",P(x+.15f,.365f,z),P(.6f,.01f,.3f),"ACC5C9",PrimitiveType.Sphere);}Prop(puddles);
   for(int i=0;i<2;i++){var umbrella=Group(root,"Umbrella visitor",P(-3.5f+i*3,.34f,-10));art.Person(umbrella,Vector3.zero,i==0?"CF956B":"6E9EAD");art.Bar(umbrella,P(.28f,.9f,0),P(.28f,2.25f,0),.045f,"536E78");art.Part(umbrella,"Umbrella canopy",P(.28f,2.2f,0),P(1.65f,.4f,1.65f),i==0?"DDA06E":"779FC0",PrimitiveType.Sphere);Animated(umbrella,"queue");}
  }
  void Particles(Transform parent,string name,Vector3 p,Vector3 size,Color color,float rate,float lifetime,float speed,float scale,bool rain){var go=Group(parent,name,p).gameObject;go.layer=2;if(rain)go.transform.localRotation=Quaternion.Euler(90,0,0);else go.transform.localRotation=Quaternion.Euler(-90,0,0);var system=go.AddComponent<ParticleSystem>();system.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);var main=system.main;main.playOnAwake=false;main.startLifetime=lifetime;main.startSpeed=speed;main.startSize=scale;main.startColor=color;main.maxParticles=Mathf.CeilToInt(rate*lifetime)+16;main.simulationSpace=ParticleSystemSimulationSpace.World;main.cullingMode=ParticleSystemCullingMode.AlwaysSimulate;var shape=system.shape;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=size;var emission=system.emission;emission.rateOverTime=rate;var renderer=system.GetComponent<ParticleSystemRenderer>();renderer.sharedMaterial=particleMaterial;if(rain){renderer.renderMode=ParticleSystemRenderMode.Stretch;renderer.lengthScale=8;renderer.velocityScale=.025f;}else{var fade=system.colorOverLifetime;fade.enabled=true;var gradient=new Gradient();gradient.SetKeys(new[]{new GradientColorKey(Color.white,0),new GradientColorKey(Color.white,1)},new[]{new GradientAlphaKey(0,0),new GradientAlphaKey(.6f,.2f),new GradientAlphaKey(0,1)});fade.color=gradient;}}
 }
}
