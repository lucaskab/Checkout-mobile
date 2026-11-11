using System.Collections;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "eventsrankvisit" (QA copy, the Editor's fake server; Lucas 10/11): Ranking › Mundo, "Visitar" on a player of the
 // top 100 who is not a friend → their market, only to look (the visit bar has just "Voltar ao meu mercado"); back home.
 public sealed partial class CheckoutAutoTest {
  IEnumerator RankVisit(string request){
   int seq=0;
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT rankvisit {name}: {(ok?"PASS":"FAIL")} {detail}");
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-rv-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   Route("");yield return new WaitForSecondsRealtime(3f);
   Route("!ranking:mundo");yield return new WaitForSecondsRealtime(4f);
   yield return ShotJpg("rv_mundo");
   var visit=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Where(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.action=="socialVisitPlayer").ToList();
   Note($"RV visit buttons on screen: {visit.Count}");
   Result("Visitar on the Mundo rows",visit.Count>0,visit.Count.ToString());
   if(visit.Count==0)yield break;
   visit[0].Clicked?.Invoke(visit[0]);
   yield return new WaitForSecondsRealtime(8f);
   yield return ShotJpg("rv_visit");
   var bar=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).Where(b=>b.isActiveAndEnabled&&b.Data!=null&&(b.Data.action=="socialLike"||b.Data.action=="socialGift"||b.Data.action=="socialLeave")).Select(b=>b.Data.action).ToArray();
   Note("RV visit bar: "+string.Join(",",bar));
   Result("only to look: no like or gift, a way back",bar.Contains("socialLeave")&&!bar.Contains("socialLike")&&!bar.Contains("socialGift"),string.Join(",",bar));
   Act("socialLeave","[]");yield return new WaitForSecondsRealtime(5f);
   yield return ShotJpg("rv_home");
  }
 }
}
