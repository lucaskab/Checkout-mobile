using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Rede in the world, part 1 (Lucas 06/11 "Aprovado"): "eventsdc" on the QA copy of the save.
 //   1. the save jumps to the rede and names the chain: the distribution centre replaces the central warehouse;
 //   2. stills of the DC (game camera, south-east, south-west, top) with the brand on its plates;
 //   3. an order through the DC: the truck that comes is one of the chain's (dry), backed onto the DC's dock;
 //   4. the market repainted: the DC and the fleet truck follow the colours.
 // RESULT lines in Logs/autotest_log.txt, stills Logs/dc_*.jpg.
 public sealed partial class CheckoutAutoTest {
  IEnumerator RedeWorld(string request){
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-dc-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT dc {name}: {(ok?"PASS":"FAIL")} {detail}");
   if(!CheckoutStartMenu.QaMode){Note("dc: not on the QA copy, stopping");yield break;}
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   var sim=FindAnyObjectByType<MarketDay.MarketSimulation>();
   var world=sim?sim.world:null;
   yield return new WaitForSecondsRealtime(3f);
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1f);
   Act("setMarketLevel","[55]");yield return new WaitForSecondsRealtime(1f);Act("dismissLevelUp","[]");Act("devAdjustCoins","[9000000]");Act("devAdjustDiamonds","[500]");
   Act("resetMarketPaint","[]");Act("devSetMarketEra","[\"rede\"]");
   Route("");yield return new WaitForSecondsRealtime(8f);Act("dismissLevelUp","[]");if(hud)hud.QaReleaseCelebrations();
   Act("nameChain","[\"Bom Preço\",\"coroa\"]");yield return new WaitForSecondsRealtime(2f);Route("");
   Act("startDay","[\"livre\"]");yield return new WaitForSecondsRealtime(3f);
   Note("dc: "+CheckoutRedeWorld.Report);
   var grand=world?world.Find(CheckoutMarketLayout.GrandWarehouse):null;
   if(grand)Note("dc: Warehouse Large children: "+string.Join(", ",grand.Cast<Transform>().Select(c=>c.name+(c.gameObject.activeSelf?"":"(off)"))));
   var dc=grand?grand.Find("Rede DC"):null;
   Result("the distribution centre replaces the central warehouse",dc&&dc.gameObject.activeInHierarchy&&CheckoutRedeWorld.Report.StartsWith("dc on"),CheckoutRedeWorld.Report);
   var plates=dc?dc.GetComponentsInChildren<TMPro.TextMeshPro>(true).Where(t=>t.gameObject.activeInHierarchy).Select(t=>t.text).ToArray():new string[0];
   Result("the DC's plates carry the chain's name",plates.Length>0&&plates.All(t=>t.ToUpperInvariant()=="BOM PREÇO"),string.Join("|",plates));
   var c=dc?dc.position+new Vector3(1.5f,4,0):new Vector3(-6.5f,4,31.8f);
   if(sim)sim.HomeCamera();yield return new WaitForSecondsRealtime(1f);
   TierShot("dc_gamecam",2048,1152,c,34);
   yield return From("dc_se",c,new Vector3(1.1f,.75f,-1f),36,30);
   yield return From("dc_sw",c,new Vector3(-.9f,.6f,-1f),36,30);
   yield return From("dc_ne_docks",c+new Vector3(6,-1,0),new Vector3(1.2f,.55f,.35f),30,30);
   TopDown(new Vector3(c.x+6,0,c.z),34,"dc_top");
   // the whole lot and its neighbours: where the fleet's diesel island and parked trucks could go
   TopDown(new Vector3(4,0,24),78,"dc_overview");
   yield return From("dc_overview_iso",new Vector3(6,0,30),new Vector3(.9f,1.25f,-.75f),70,40);
   Note("dc: world texts on the depth-tested material: "+CheckoutWorldText.Fixed);
   var facade=world?world.Find("Market Stage Dressing/S4 name"):null;
   if(facade){var fz=facade.position;Note($"dc: facade letters at ({fz.x:0.0},{fz.y:0.0},{fz.z:0.0})");}
   var gate=world?world.Find("Rede gatehouse"):null;var totem=world?world.Find("Rede totem"):null;
   Result("the truck gate and the chain's totem stand",gate&&gate.gameObject.activeInHierarchy&&totem&&totem.gameObject.activeInHierarchy,$"gate {(gate?gate.position.ToString():"-")} totem {(totem?totem.position.ToString():"-")}");
   if(gate)yield return From("dc_gate",gate.position+new Vector3(0,1.5f,-2f),new Vector3(1f,.55f,-.8f),13,30);
   if(totem){yield return From("dc_totem",totem.position+Vector3.up*3.5f,new Vector3(.3f,.35f,-1f),12,32);TierShot("dc_totem_gamecam",2048,1152,totem.position+Vector3.up*2,16);}
   // 3. an order through the DC
   Act("orderFromDistributionCenter","[[{\"productId\":172,\"boxes\":2},{\"productId\":175,\"boxes\":1}]]");
   Transform fleet=null;
   bool gateShot=false;
   for(float t=0;t<90&&!fleet;t+=.5f){
    yield return new WaitForSecondsRealtime(.5f);
    // (the order is packed at the DC first: time is moved on until it leaves on its truck)
    if(Mathf.Repeat(t,2f)<.01f&&bridge.State.orders.Any(o=>!string.IsNullOrEmpty(o.fleetTruckId)&&o.status!="em-transporte"))Act("devAdvanceOrders","[0.5]");
    foreach(var name in new[]{"Anim_Truck_5","Anim_Truck_8","Anim_Truck_11"}){var tr=world?world.Find(name):null;var skin=tr?tr.Find("Fleet skin"):null;if(tr&&tr.gameObject.activeInHierarchy&&skin&&skin.gameObject.activeSelf)fleet=tr;}
   }
   Result("a delivery through the DC comes in a fleet truck",fleet,fleet?fleet.name:string.Join(",",bridge.State.orders.Select(o=>o.id+":"+o.status+":"+o.fleetTruckId)));
   if(fleet){
    var trucks=FindAnyObjectByType<CheckoutMap>()?.Trucks;
    for(float t=0;t<40;t+=.1f){
     yield return new WaitForSecondsRealtime(.1f);
     if(!gateShot&&gate&&(fleet.position-gate.position).sqrMagnitude<5f*5f){gateShot=true;yield return From("dc_gate_open",gate.position+new Vector3(0,1.5f,-2f),new Vector3(1f,.55f,-.8f),14,30);}
     if(trucks&&Vector3.Distance(fleet.position,trucks.Home(fleet))<.3f)break;
    }
    Note("dc: gate shot while the truck passed: "+gateShot);
    yield return new WaitForSecondsRealtime(1.5f);
    var p=fleet.position;Note($"dc: fleet truck {fleet.name} at ({p.x:0.00},{p.z:0.00}) home {(trucks?trucks.Home(fleet).ToString():"?")}");
    yield return From("dc_fleet_dock",p+new Vector3(-1,1,0),new Vector3(1f,.7f,-.9f),14,30);
    TierShot("dc_fleet_gamecam",2048,1152,p,18);
   }
   // 4. repainted
   Act("applyMarketPaint","[\"C2185B\",\"00B8D4\",\"diamonds\"]");yield return new WaitForSecondsRealtime(3f);
   yield return From("dc_paint",c,new Vector3(1.1f,.75f,-1f),36,30);
   Act("resetMarketPaint","[]");yield return new WaitForSecondsRealtime(1f);
   if(sim)sim.HomeCamera();
  }

  // "eventsyard": the fleet's yard (Lucas 06/11 "coloque no jogo"): the chain with 5 trucks, stills of the yard,
  // one truck leaving (mid-way), one coming in → pump → backing into its bay; RESULT lines, stills Logs/yard_*.jpg,
  // video Logs/yard_demo.mjpg.
  IEnumerator RedeYard(string request){
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-yard-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT yard {name}: {(ok?"PASS":"FAIL")} {detail}");
   if(!CheckoutStartMenu.QaMode){Note("yard: not on the QA copy, stopping");yield break;}
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   var sim=FindAnyObjectByType<MarketDay.MarketSimulation>();
   yield return new WaitForSecondsRealtime(3f);
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1f);
   Act("setMarketLevel","[55]");yield return new WaitForSecondsRealtime(1f);Act("dismissLevelUp","[]");Act("devAdjustCoins","[9000000]");
   Act("resetMarketPaint","[]");Act("devSetMarketEra","[\"rede\"]");
   Route("");yield return new WaitForSecondsRealtime(8f);Act("dismissLevelUp","[]");if(hud)hud.QaReleaseCelebrations();
   Act("nameChain","[\"Bom Preço\",\"coroa\"]");yield return new WaitForSecondsRealtime(1f);
   Act("buyFleetTruck","[\"seco\"]");Act("buyFleetTruck","[\"seco\"]");Act("buyFleetTruck","[\"refrigerado\"]");
   yield return new WaitForSecondsRealtime(2.5f);Route("");
   var yard=CheckoutRedeYard.Current;
   Note("yard: "+CheckoutRedeYard.Report+" | "+(yard?yard.Describe():"no yard"));
   var ids=bridge.State.chain?.trucks?.Where(t=>t!=null).Select(t=>t.id).ToArray()??new string[0];
   Result("the yard stands with the fleet parked",yard&&ids.Length>=5&&ids.All(id=>yard.QaMode(id)=="Parked"),yard?yard.Describe():"-");
   var o=CheckoutRedeYard.Origin;
   if(sim)sim.HomeCamera();yield return new WaitForSecondsRealtime(.5f);
   TierShot("yard_gamecam",2048,1152,o+new Vector3(-2,1,0),30);
   yield return From("yard_se",o+new Vector3(-1,1,0),new Vector3(.75f,.8f,-1f),34,34);
   yield return From("yard_pump_close",CheckoutRedeYard.PumpPosition+Vector3.up,new Vector3(.8f,.55f,-.9f),14,34);
   TopDown(o,40,"yard_top");
   // a round trip filmed: one truck leaves, another comes in to the pump and backs into its bay
   if(sim)sim.FocusCinematic(o+new Vector3(3,0,-1),20);yield return new WaitForSecondsRealtime(.5f);
   RecStart("Logs/yard_demo.mjpg");
   bool left=ids.Length>1&&yard.QaLeave(ids[1]);
   yield return Frames(2.2f);
   if(left)yield return From("yard_leaving",o+new Vector3(4,1,-2),new Vector3(.6f,.7f,-1f),24,34);
   bool back=yard.QaRoundTrip(ids[0]);
   Transform m0=yard.TruckModel(ids[0]);
   bool pumpShot=false,parked=false;
   for(float t=0;t<60;t+=.25f){
    yield return Frames(.25f);
    var mode=yard.QaMode(ids[0]);
    if(!pumpShot&&mode=="Refuelling"){pumpShot=true;yield return From("yard_refuel",CheckoutRedeYard.PumpPosition+Vector3.up,new Vector3(.8f,.55f,-.9f),15,34);}
    if(mode=="Backing"&&m0&&t%2f<.26f)Note($"yard: backing at ({m0.position.x:0.0},{m0.position.z:0.0}) yaw {m0.eulerAngles.y:0}");
    if(pumpShot&&mode=="Parked"){parked=true;break;}
   }
   yield return Frames(1.5f);RecStop();
   Result("a truck comes in, refuels and backs into its bay",back&&pumpShot&&parked,m0?$"at ({m0.position.x:0.00},{m0.position.z:0.00}) yaw {m0.eulerAngles.y:0}":"-");
   if(parked)yield return From("yard_parked_again",o+new Vector3(4,1,2),new Vector3(.3f,.8f,-1f),20,34);
   Result("a truck leaves the yard to the street",left&&yard.QaMode(ids[1])=="Away",yard.QaMode(ids[1]));
   yield return new WaitForSecondsRealtime(2f);
   if(sim)sim.HomeCamera();
  }

  // A still from `dir` (towards the camera) at `dist` metres, field of view `fov`, of `target`.
  IEnumerator From(string name,Vector3 target,Vector3 dir,float dist,float fov){
   yield return new WaitForEndOfFrame();
   var main=Camera.main;if(!main){Note("no camera");yield break;}
   var go=new GameObject("QA dc camera");var cam=go.AddComponent<Camera>();cam.CopyFrom(main);cam.orthographic=false;cam.fieldOfView=fov;
   go.transform.position=target+dir.normalized*dist;go.transform.LookAt(target);cam.nearClipPlane=.3f;cam.farClipPlane=dist+300;
   var rt=new RenderTexture(2048,1152,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;
   var image=new Texture2D(2048,1152,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,2048,1152),0,0);image.Apply();RenderTexture.active=active;
   File.WriteAllBytes("Logs/"+name+".jpg",image.EncodeToJPG(86));Destroy(image);cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(go);Note("shot "+name);
  }
 }
}
