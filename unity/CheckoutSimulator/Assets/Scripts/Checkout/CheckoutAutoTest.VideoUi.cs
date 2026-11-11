using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "eventsvideoui" (QA copy of the save; Lucas 10/11): the always-visible "Grátis" (videos) and "Amigos" buttons above
 // "Bônus", the page where the player picks diamonds or coins, the store-review request after an expansion's
 // celebration and the "Versão nova disponível" card (Logs/fake_update.txt pretends the store has a newer version).
 public sealed partial class CheckoutAutoTest {
  IEnumerator VideoUi(string request){
   int seq=0;var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-vui-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT video {name}: {(ok?"PASS":"FAIL")} {detail}");
   IEnumerator Tips(){for(int i=0;i<3&&hud&&hud.CoachQa().isTip;i++){Act("dismissOnboardingTip","[]");yield return new WaitForSecondsRealtime(.5f);}}
   Route("");yield return new WaitForSecondsRealtime(3f);yield return Tips();
   // the rail: the fixed buttons above "Bônus"
   var buttons=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Where(b=>b.isActiveAndEnabled&&b.Data!=null).ToList();
   var free=buttons.FirstOrDefault(b=>b.Data.route=="!video");
   var friends=buttons.FirstOrDefault(b=>b.Data.route=="!amigos"&&b.transform.parent&&b.transform.parent.name=="QuickRail");
   Note($"VUI rail: free={(free?free.Data.label+" badge "+free.Data.badge+" variant "+free.Data.variant:"MISSING")} friends={(friends?"present":"missing")} breathe={(free&&free.GetComponent<CheckoutBreathe>()!=null)}");
   Result("the free video button is on screen",free!=null,free?free.Data.label:"missing");
   yield return ShotJpg("vui_home");
   // the page where the player picks the prize
   if(free)free.Clicked?.Invoke(free);else Route("!video");
   yield return new WaitForSecondsRealtime(2f);yield return ShotJpg("vui_video_page");
   var page=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Where(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.action=="watchRewardedAd").Select(b=>b.Data.label+" "+b.Data.args).ToArray();
   Note("VUI page buttons: "+string.Join(" | ",page));
   Result("the page offers diamonds and coins",page.Any(p=>p.Contains("diamonds"))&&page.Any(p=>p.Contains("coins")),string.Join(" | ",page));
   Route("");yield return new WaitForSecondsRealtime(1.5f);
   // English
   CheckoutI18n.SetLanguage("en");CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\"en\"}");yield return new WaitForSecondsRealtime(2f);
   Route("!video");yield return new WaitForSecondsRealtime(2f);yield return ShotJpg("vui_video_page_en");
   Route("");CheckoutI18n.SetLanguage("pt");CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\"pt\"}");yield return new WaitForSecondsRealtime(2f);
   // the update card: the store "has" 1.0.9 (once a session, on the main screen)
   yield return new WaitForSecondsRealtime(1f);
   CheckoutAppStore.Active?.QaReport("1.0.9");
   for(float t=0;t<15&&!(hud&&hud.CurrentRoute=="atualizar");t+=1f)yield return new WaitForSecondsRealtime(1f);
   Note("VUI update route: "+(hud?hud.CurrentRoute:"?"));
   Result("the new-version card opens on its own",hud&&hud.CurrentRoute=="atualizar",hud?hud.CurrentRoute:"");
   yield return ShotJpg("vui_update");
   Route("");yield return new WaitForSecondsRealtime(1f);
  }
 }
}
