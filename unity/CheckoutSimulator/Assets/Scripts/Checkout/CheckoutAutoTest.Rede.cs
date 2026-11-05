using System.Collections;
using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Checkout {
 // Rede de supermercados (Lucas 05/11, ideas 2 + 5): on the QA copy of the save at the iPhone's landscape size, recorded
 // into Logs/rede_demo.mjpg (30 fps JPEG frames) with stills Logs/ff_rede_*.jpg:
 //  "eventsrede-phone"
 //   1. the save jumps to the rede (dev): the card to name the chain opens by itself; a logo is tapped, a name typed,
 //      "Batizar a rede";
 //   2. the facade's big letters and logo turn into the chain's name and logo;
 //   3. the Rede window: Frota (an order through the distribution centre), Contratos, Filiais (a branch bought and
 //      finished, a cargo sent, coins collected);
 //   4. the market repainted (Cores do mercado): the logo, the own-brand products and the facade follow the colours.
 // RESULT lines in Logs/autotest_log.txt.
 public sealed partial class CheckoutAutoTest {
  IEnumerator Rede(string request){
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-rede-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
   void Result(string name,bool ok,string detail="")=>Note($"RESULT rede {name}: {(ok?"PASS":"FAIL")} {detail}");
   IEnumerator Shot(string name){yield return new WaitForEndOfFrame();System.IO.File.WriteAllBytes("Logs/ff_rede_"+name+".jpg",RecJpg(4000,86));Note($"still ff_rede_{name}.jpg at {RecAt:0.0}s");}
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   if(!hud){Note("rede: no HUD");yield break;}
   if(request.EndsWith("-phone"))Note("rede: "+CheckoutQaGameView.Set(2778,1284));
   if(!CheckoutStartMenu.QaMode){Note("rede: not on the QA copy, stopping");yield break;}
   var langBefore=CheckoutI18n.Language;Lang(request.Contains("-en")?"en":"pt");
   var sim=FindAnyObjectByType<MarketDay.MarketSimulation>();
   yield return new WaitForSecondsRealtime(3f);
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1f);
   for(int i=0;i<3&&hud.CoachQa().isTip;i++){Act("dismissOnboardingTip","[]");yield return new WaitForSecondsRealtime(.5f);}
   Act("setMarketLevel","[55]");yield return new WaitForSecondsRealtime(1f);Act("dismissLevelUp","[]");Act("devAdjustCoins","[9000000]");Act("devAdjustDiamonds","[500]");
   Act("resetMarketPaint","[]");
   Act("devSetMarketEra","[\"rede\"]");
   Route("");yield return new WaitForSecondsRealtime(2f);Act("dismissLevelUp","[]");hud.QaReleaseCelebrations();yield return new WaitForSecondsRealtime(2f);
   Act("startDay","[\"livre\"]");yield return new WaitForSecondsRealtime(2f);
   if(sim)sim.HomeCamera();
   string Top()=>hud.QaPageCard?.title??"";
   RecStart("Logs/rede_demo.mjpg");
   try{
    // 1. naming
    for(int i=0;i<30*6&&!(hud.QaPageCard?.input!=null&&hud.QaPageCard.input.id=="rede-nome");i++)yield return null;
    bool opened=hud.QaPageCard?.input?.id=="rede-nome";
    if(!opened){Route("!rede:marca");yield return Frames(1.5f);}
    Result("the naming card opens by itself when the rede is ready",opened,Top());
    yield return Frames(1.2f);yield return Shot("1_batizar");
    var tile=hud.GetComponentsInChildren<MonoBehaviour>(false).FirstOrDefault(m=>m.GetType().Name=="BoardTileUi"&&(m.GetType().GetField("Id")?.GetValue(m) as string)=="coroa");
    if(tile)ExecuteEvents.Execute(tile.gameObject,new PointerEventData(EventSystem.current){button=PointerEventData.InputButton.Left},ExecuteEvents.pointerClickHandler);
    else Act("chainPickEmblem","[\"coroa\"]");
    yield return Frames(1f);
    var field=hud.GetComponentsInChildren<TMPro.TMP_InputField>(false).FirstOrDefault();
    if(field){field.text="";foreach(var ch in "Bom Preço"){field.text+=ch;yield return Frames(.06f);}}
    yield return Frames(.6f);yield return Shot("2_nome_logo");
    var save=hud.GetComponentsInChildren<CheckoutDesktopButton>(false).FirstOrDefault(b=>b.Data!=null&&b.Data.action=="nameChain");
    if(save&&field)save.Clicked?.Invoke(save);else Act("nameChain","[\"Bom Preço\",\"coroa\"]");
    yield return Frames(2f);
    Result("the chain is named",CheckoutBrand.Named&&CheckoutBrand.Name=="Bom Preço"&&CheckoutBrand.Emblem=="coroa",$"{CheckoutBrand.Name} / {CheckoutBrand.Emblem}");
    // 2. the facade
    Route("");yield return Frames(1f);
    var letters=GameObject.Find("S4 name");
    if(sim&&letters){sim.FocusCinematic(letters.transform.position+new Vector3(0,0,-6),14);}
    yield return Frames(2.5f);
    Result("the facade shows the chain's name and logo",CheckoutBrandWorld.Report.StartsWith("brand BOM PREÇO"),CheckoutBrandWorld.Report);
    yield return Shot("3_fachada");
    if(sim)sim.HomeCamera();yield return Frames(1.5f);yield return Shot("3b_mercado");
    // 3. the Rede window
    Route("!rede:cd");yield return Frames(2f);yield return Shot("4_frota");
    Act("orderFromDistributionCenter","[[{\"productId\":172,\"boxes\":2},{\"productId\":175,\"boxes\":1}]]");yield return Frames(2f);
    Result("an order through the distribution centre leaves on a fleet truck",bridge.State.orders.Any(o=>!string.IsNullOrEmpty(o.fleetTruckId)),string.Join(",",bridge.State.orders.Select(o=>o.fleetTruckId)));
    yield return Shot("4b_frota_rua");
    Route("!rede:contratos");yield return Frames(2.2f);yield return Shot("5_contratos");
    Route("!rede:filiais");yield return Frames(2f);yield return Shot("6_filiais");
    Act("buyChainBranch","[\"centro\"]");yield return Frames(1.2f);Act("finishChainBranchNow","[\"centro\"]");yield return Frames(1.5f);
    Act("buyChainBranch","[\"praia\"]");yield return Frames(1.5f);
    Result("a branch is bought and opened",bridge.State.chain!=null&&bridge.State.chain.branches.Any(b=>b.id=="centro"&&b.level==1),string.Join(",",bridge.State.chain?.branches?.Select(b=>b.id+b.level)??new string[0]));
    yield return Shot("6b_filial_aberta");
    // 4. repainted
    Act("applyMarketPaint","[\"C2185B\",\"00B8D4\",\"diamonds\"]");yield return Frames(2f);
    Route("!rede:marca");yield return Frames(2f);yield return Shot("7_marca_cores");
    Route("!rede:cd");yield return Frames(1.5f);hud.QaBoardScroll(.9f);yield return Frames(1.5f);yield return Shot("7b_produtos_cores");hud.QaBoardScroll(0);
    Route("");if(letters&&sim)sim.FocusCinematic(letters.transform.position+new Vector3(0,0,-6),14);yield return Frames(2.5f);yield return Shot("8_fachada_cores");
    Result("the brand follows the market's colours",CheckoutBrand.Primary!=CheckoutBrand.ClassicPrimary,ColorUtility.ToHtmlStringRGB(CheckoutBrand.Primary));
    if(sim)sim.HomeCamera();yield return Frames(1f);
   } finally {RecStop();}
   Act("resetMarketPaint","[]");Lang(langBefore);Route("");
   yield return new WaitForSecondsRealtime(1f);
  }
 }
}
