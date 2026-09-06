using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using MarketDay;
namespace Checkout {
 public class CheckoutMap:MonoBehaviour {
  Transform world;CheckoutBridge bridge;readonly Dictionary<string,TextMesh> labels=new Dictionary<string,TextMesh>();readonly Dictionary<string,Transform> staff=new Dictionary<string,Transform>();readonly Dictionary<string,GameObject> decorations=new Dictionary<string,GameObject>();readonly Dictionary<string,Vector3> homes=new Dictionary<string,Vector3>();
  readonly Dictionary<string,Vector3> fixtures=new Dictionary<string,Vector3>{{"produce",P(6.55f,.45f)},{"dairy",P(-6.4f,-1.6f)},{"bakery",P(-6.45f,1.05f)},{"snacks",P(-1.6f,.3f)},{"drinks",P(2,-1.18f)},{"coffee",P(-2.2f,6.37f)},{"pizza",P(4.85f,-5.36f)}};
  readonly Dictionary<string,Vector3> approaches=new Dictionary<string,Vector3>{{"produce",P(5.1f,-1.2f)},{"dairy",P(-4,-1.6f)},{"bakery",P(-3.8f,2.55f)},{"snacks",P(-.18f,.5f)},{"drinks",P(3.3f,-1.2f)},{"coffee",P(-2.2f,5.1f)},{"pizza",P(4.85f,-3.85f)}};
  ParticleSystem rain;GameObject roadworks;Light sunlight;Color sunlightColor;TextMesh eventSign;float workClock;Snapshot state;Font font;Material white,teal,gold;
  static Vector3 P(float x,float z)=>new Vector3(x,.74f,z);
  public Vector3 Fixture(string id)=>fixtures.TryGetValue(id,out var p)?p:P(0,0);
  public Vector3 Approach(string id)=>approaches.TryGetValue(id,out var p)?p:P(0,0);
  public bool Special(string id)=>id=="bakery";
  public void Initialize(Transform root,CheckoutBridge owner){world=root;bridge=owner;font=Resources.Load<Font>("CheckoutFredoka");if(!font)font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
   white=Mat("FFF7EC");teal=Mat("2E8CAE");gold=Mat("F2B03D");
   foreach(var pair in fixtures){labels[pair.Key]=Label(pair.Key,Fixture(pair.Key)+Vector3.up*1.75f,"",.115f);Target(Fixture(pair.Key),new Vector3(1.4f,2,1.1f),"store");}
   eventSign=Label("Event",new Vector3(0,4.8f,5.5f),"",.22f);
   sunlight=FindObjectsByType<Light>(FindObjectsSortMode.None).FirstOrDefault(l=>l.type==LightType.Directional);if(sunlight)sunlightColor=sunlight.color;
   foreach(Transform t in world)if(t.name.StartsWith("Anim_Truck"))homes[t.name]=t.position;
   Target(P(3,10),new Vector3(8,5,4),"suppliers");Target(P(-3.9f,-4.7f),new Vector3(3,2,1.7f),"team");
   roadworks=new GameObject("Road works event");roadworks.transform.SetParent(transform);for(int i=0;i<6;i++){var cone=GameObject.CreatePrimitive(PrimitiveType.Cylinder);cone.name="Road safety marker";cone.transform.SetParent(roadworks.transform);cone.transform.position=new Vector3(10+i*.65f,.4f,9);cone.transform.localScale=new Vector3(.25f,.4f,.25f);cone.GetComponent<Renderer>().material=gold;Destroy(cone.GetComponent<Collider>());}roadworks.SetActive(false);
   var weather=new GameObject("Rain event");weather.transform.SetParent(transform);weather.transform.position=new Vector3(0,9,2);weather.transform.rotation=Quaternion.Euler(90,0,0);rain=weather.AddComponent<ParticleSystem>();rain.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);var main=rain.main;main.startLifetime=1.3f;main.startSpeed=10;main.startSize=.025f;main.startColor=new Color(.6f,.8f,1,.55f);main.maxParticles=700;var shape=rain.shape;shape.shapeType=ParticleSystemShapeType.Box;shape.scale=new Vector3(26,23,.1f);var emission=rain.emission;emission.rateOverTime=450;rain.GetComponent<ParticleSystemRenderer>().material=new Material(Shader.Find("Sprites/Default"));
  }
  public void Apply(Snapshot next){state=next;
   foreach(var shelf in next.shelves){if(!labels.TryGetValue(shelf.id,out var text))continue;
    text.text=shelf.unlocked?shelf.productName+"\n"+shelf.stock+" / "+shelf.capacity+"  ·  $"+shelf.price.ToString("0.##")+"\nEstoque: "+shelf.reserve:"Prateleira bloqueada";
    text.color=MarketSimulation.C(shelf.unlocked?(shelf.stock==0?"C0401F":"4A3624"):"977552");
    var pieces=world.Cast<Transform>().Where(t=>t.name.StartsWith("Stock_"+shelf.id+"_")).OrderBy(t=>t.name).ToArray();int visible=shelf.unlocked&&shelf.stock>0?Mathf.Max(1,Mathf.CeilToInt(pieces.Length*(float)shelf.stock/Mathf.Max(1,shelf.capacity))):0;
    for(int i=0;i<pieces.Length;i++)pieces[i].gameObject.SetActive(i<visible);
   }
   foreach(var sector in next.sectors){var root=world.Find("Sector_"+sector.id);if(root)root.gameObject.SetActive(sector.unlocked);
    var position=sector.id=="padaria"?P(-5.5f,4.5f):sector.id=="acougue"?P(6.5f,4.3f):sector.id=="peixaria"?P(1.5f,4.3f):P(-.1f,5.3f);
    string key="sector-"+sector.id;if(!labels.ContainsKey(key)){labels[key]=Label(key,position+Vector3.up*2.7f,"",.13f);Target(position,new Vector3(1.3f,2,1.1f),"sectors");}
    labels[key].text=sector.name+(sector.unlocked?(sector.jobs>0?"\nProduzindo · "+sector.jobs:"\nPronto para produzir"):"\nBloqueado");
    string worker=sector.id=="padaria"?"Worker_Baker":sector.id=="acougue"?"Worker_Butcher":sector.id=="peixaria"?"Worker_Fishmonger":"";var actor=world.Find(worker);if(actor)actor.gameObject.SetActive(sector.unlocked);
   }
   var baseCashier=world.Find("Worker_Cashier");if(baseCashier)baseCashier.gameObject.SetActive(true); // The player runs checkout before hiring.
   foreach(var employee in next.employees){if(!staff.TryGetValue(employee.id,out var actor)){
     Transform template=world.Find(employee.role=="cashier"?"Worker_Cashier":"StockWorker_0");if(!template)continue;actor=Instantiate(template,world);actor.name="Employee_"+employee.id;var oldAgent=actor.GetComponent<UnityEngine.AI.NavMeshAgent>();if(oldAgent)Destroy(oldAgent);staff[employee.id]=actor;
     float n=staff.Count;actor.position=employee.role=="cashier"?P(-5.5f,-4):P(3.8f,2.3f+n*.65f);homes[actor.name]=actor.position;Target(actor.position,new Vector3(.7f,2,.7f),"team");
    }actor.gameObject.SetActive(employee.isWorking);
   }
   foreach(var pair in staff)if(!next.employees.Any(e=>e.id==pair.Key&&e.isWorking))pair.Value.gameObject.SetActive(false);
   string[] expansionNames={"fresh-wing","service-wing","stock-annex","premium-hall"};for(int i=0;i<expansionNames.Length;i++){string id=expansionNames[i];if(!decorations.ContainsKey(id)){var tile=Box(id,new Vector3(12,.15f,-5+i*4),new Vector3(4,.3f,3.5f),white);decorations[id]=tile;Label(id,tile.transform.position+Vector3.up*.6f,id.Replace('-',' '),.18f);Target(tile.transform.position,new Vector3(4,1,3.5f),"expansions");}decorations[id].SetActive(next.expansions.Contains(id));}
   foreach(string id in next.ownedItems)if(!decorations.ContainsKey("shop-"+id)){int i=decorations.Keys.Count(k=>k.StartsWith("shop-"));var item=Box("Upgrade "+id,new Vector3(-8.2f,1.25f,3.6f-i*.45f),new Vector3(.32f,.6f,.32f),teal);decorations["shop-"+id]=item;Label(id,item.transform.position+Vector3.up*.65f,id.Replace('-',' '),.075f);}
   foreach(var pair in decorations.Where(p=>p.Key.StartsWith("shop-")))pair.Value.SetActive(next.ownedItems.Contains(pair.Key.Substring(5)));
   eventSign.text=next.@event.name+(string.IsNullOrEmpty(next.@event.name)?"":"\n"+next.@event.effectLabel);eventSign.color=MarketSimulation.C(next.@event.kind=="negative"?"C0401F":"427A24");
   bool raining=next.@event.id=="chuva-forte";if(raining&&!rain.isPlaying)rain.Play();if(!raining&&rain.isPlaying)rain.Stop(true,ParticleSystemStopBehavior.StopEmittingAndClear);roadworks.SetActive(next.@event.id=="obras-na-rua");if(sunlight)sunlight.color=raining?new Color(.65f,.76f,.9f):sunlightColor;
  }
  void Update(){if(state==null)return;workClock+=Time.deltaTime;
   foreach(var employee in state.employees)if(employee.isWorking&&staff.TryGetValue(employee.id,out var actor)&&employee.role!="cashier"){
    var home=homes[actor.name];float u=Mathf.Sin(workClock*.45f*employee.efficiency);var target=home+Vector3.forward*u*.55f;var direction=target-actor.position;if(direction.sqrMagnitude>.000001f)actor.rotation=Quaternion.RotateTowards(actor.rotation,Quaternion.LookRotation(-direction),Time.deltaTime*180);actor.position=target;
   }
   foreach(var sector in state.sectors)if(sector.unlocked&&sector.jobs>0&&Mathf.FloorToInt(workClock)!=Mathf.FloorToInt(workClock-Time.deltaTime)&&Mathf.FloorToInt(workClock)%3==0){string name=sector.id=="padaria"?"Worker_Baker":sector.id=="acougue"?"Worker_Butcher":"Worker_Fishmonger";var worker=world.Find(name);if(worker&&worker.gameObject.activeSelf)worker.GetComponent<MarketCharacterAnimator>()?.Perform("BuyAtSpecialSector");}
   int index=0;foreach(Transform truck in world)if(truck.name.StartsWith("Anim_Truck")&&homes.TryGetValue(truck.name,out var home)){var incoming=state.orders.Where(o=>o.status!="entregue").ToArray();float offset=index<incoming.Length?(incoming[index].status=="em-transporte"?Mathf.PingPong(workClock,4):5):0;truck.position=Vector3.MoveTowards(truck.position,home+Vector3.forward*offset,Time.deltaTime*2);index++;}
  }
  void LateUpdate(){var camera=Camera.main;if(camera)foreach(var label in labels.Values)if(label)label.transform.rotation=camera.transform.rotation;if(eventSign&&camera)eventSign.transform.rotation=camera.transform.rotation;}
  Material Mat(string hex){var mat=new Material(Shader.Find("Standard"));mat.color=MarketSimulation.C(hex);mat.SetFloat("_Glossiness",0);return mat;}
  GameObject Box(string name,Vector3 p,Vector3 size,Material mat){var o=GameObject.CreatePrimitive(PrimitiveType.Cube);o.name=name;o.transform.SetParent(transform);o.transform.position=p;o.transform.localScale=size;o.GetComponent<Renderer>().material=mat;return o;}
  TextMesh Label(string name,Vector3 p,string value,float size){var go=new GameObject("Label "+name);go.transform.SetParent(transform);go.transform.position=p;var text=go.AddComponent<TextMesh>();text.font=font;text.fontSize=48;text.characterSize=size;text.anchor=TextAnchor.MiddleCenter;text.alignment=TextAlignment.Center;text.text=value;text.color=MarketSimulation.C("4A3624");go.GetComponent<MeshRenderer>().material=font.material;return text;}
  void Target(Vector3 p,Vector3 size,string panel){var go=new GameObject("Open "+panel);go.transform.SetParent(transform);go.transform.position=p;go.AddComponent<BoxCollider>().size=size;go.AddComponent<CheckoutTarget>().panel=panel;}
 }
}
