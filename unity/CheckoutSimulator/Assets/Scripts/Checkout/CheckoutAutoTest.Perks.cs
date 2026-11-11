using System.Collections;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "eventsperks" (QA copy; Lucas 11/11): the starter pack's page opens on its own after the tutorial, the HUD shows
 // "Oferta"; the card of 8 h away offers Coletar / 2× vídeo / 3× diamantes / a longer time away; the daily gift offers
 // to get a streak broken by one day back.
 public sealed partial class CheckoutAutoTest {
  IEnumerator Perks(string request){
   int seq=0;
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT perks {name}: {(ok?"PASS":"FAIL")} {detail}");
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-pk-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   CheckoutDesktopButton[] Buttons(string action)=>FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Where(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.action==action).ToArray();
   CheckoutDesktopButton[] Routed(string route)=>FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Where(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.route==route).ToArray();
   // The starter pack's page opens on its own (once) when nothing else is on screen.
   yield return new WaitForSecondsRealtime(4f);
   yield return ShotJpg("perks_offer_page");
   Result("the starter pack opens on its own",Buttons("buyCurrencyPack").Length>0,Buttons("buyCurrencyPack").Length.ToString());
   Route("");yield return new WaitForSecondsRealtime(2.5f);
   yield return ShotJpg("perks_hud");
   Result("Oferta on the HUD",Routed("!oferta").Length>0,Routed("!oferta").Length.ToString());
   // The way back after 8 h, and a streak broken by one day.
   Act("devPreviewPerks","[]");yield return new WaitForSecondsRealtime(2.5f);
   yield return ShotJpg("perks_offline");
   bool video=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Any(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.action=="watchRewardedAd");
   Result("offline: 2x video, 3x diamonds, longer time",video&&Buttons("tripleOfflineCoins").Length>0&&Buttons("buyOfflineCap").Length>0);
   Act("dismissOfflineSummary","[]");yield return new WaitForSecondsRealtime(1.5f);
   Route("!gratis");yield return new WaitForSecondsRealtime(3f);
   yield return ShotJpg("perks_streak");
   Result("streak recovery on the daily gift",Buttons("recoverLoginStreak").Length>0,Buttons("recoverLoginStreak").Length.ToString());
   Route("!missions:presentes");yield return new WaitForSecondsRealtime(3f);
   yield return ShotJpg("perks_streak_board");
   Route("!currency:all");yield return new WaitForSecondsRealtime(3f);
   yield return ShotJpg("perks_store");
   Route("");
  }
 }
}
