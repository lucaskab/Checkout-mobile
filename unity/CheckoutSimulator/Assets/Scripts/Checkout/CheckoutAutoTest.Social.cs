using System.Collections;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace Checkout {
 // Social v1 in the Editor ("eventssocial-phone"): on the QA copy of the save, against the host's fake server
 // (desktop/social-mock.ts). First-time profile, the Amigos page, inbox toasts, a gift applied exactly once across a
 // lost ack, a visit to a friend (Curtir, Ajudar on a build, the friend's product requests) with the save file
 // byte-identical during the whole visit, "Pedir aos amigos", the invite reward, the QR code and "Chamar amigo".
 // Shots Logs/at_social_*.png at the iPhone's landscape size; RESULT lines in Logs/autotest_log.txt.
 public sealed partial class CheckoutAutoTest {
  IEnumerator Social(string request){
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-social-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Tick()=>CheckoutBridge.Emit("{\"kind\":\"social-tick\",\"reason\":\"qa\"}");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT social {name}: {(ok?"PASS":"FAIL")} {detail}");
   string savePath=Path.Combine(Application.persistentDataPath,"checkout-qa-save.json");
   byte[] Save(){try{return File.ReadAllBytes(savePath);}catch{return new byte[0];}}
   Note("social: "+CheckoutQaGameView.Set(2778,1284)+" handheld="+CheckoutScreen.Handheld);
   for(float t=0;t<15&&!CheckoutSocial.Active;t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   Note("social: component "+(CheckoutSocial.Active?"on":"missing")+", avatars "+CheckoutSocial.AvatarCount());
   yield return new WaitForSecondsRealtime(4f);
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();
   // The QA copy may wait on a day's result: collect it and open a free day, so the market runs (customers, timers, the
   // save written every second) while everything below happens.
   // (and the QA copy's tutorial card would cover the shots: the tutorial is skipped on the copy only)
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1.5f);
   Act("startDay","[\"livre\"]");yield return new WaitForSecondsRealtime(3f);
   // (and its one-off tips, "A mesinha está esvaziando!", would cover the shots: dismissed on the copy)
   IEnumerator Tips(){for(int i=0;i<3;i++){Act("dismissOnboardingTip","[]");yield return new WaitForSecondsRealtime(.4f);}}
   yield return Tips();
   Note($"social: market open {bridge.State.isOpen}, day {bridge.State.day?.phase}");

   // 1. First time on Amigos: name + face.
   Route("!amigos");yield return new WaitForSecondsRealtime(2.5f);
   // the faces are drawn once (one per frame), then the page shows them
   yield return Tips();Route("~amigos");yield return new WaitForSecondsRealtime(1.5f);
   yield return Shot("social_profile");
   Act("socialSaveProfile","[\"Mercadinho do Lucas\",\"shopper-4\"]");yield return new WaitForSecondsRealtime(2f);
   Route("~amigos");yield return new WaitForSecondsRealtime(1.5f);
   yield return Shot("social_amigos");
   ScrollDrawer(.45f);yield return new WaitForSecondsRealtime(.6f);yield return Shot("social_amigos_friends");
   ScrollDrawer(0);yield return new WaitForSecondsRealtime(.6f);yield return Shot("social_amigos_end");
   ScrollDrawer(1);

   // 2. The inbox (gift from Ana, like from Bruno, Duda's request): toasts and the badge.
   Route("");yield return new WaitForSecondsRealtime(1f);yield return Tips();
   double coins0=bridge.State.coins;
   Tick();yield return new WaitForSecondsRealtime(.9f);yield return Shot("social_toast");
   yield return new WaitForSecondsRealtime(6f);
   Result("inbox applied",bridge.State.coins>coins0,$"coins {coins0} -> {bridge.State.coins}");
   yield return Shot("social_badge");

   // 3. A gift whose ack is lost (the app "died"): applied once, acked the next time without paying again.
   Act("socialMock","[\"gift\"]");Act("socialMock","[\"fail\",\"/v1/social/inbox/ack\"]");yield return new WaitForSecondsRealtime(.5f);
   double coins1=bridge.State.coins;Tick();yield return new WaitForSecondsRealtime(3f);
   double coins2=bridge.State.coins;Tick();yield return new WaitForSecondsRealtime(3f);
   double coins3=bridge.State.coins;
   Result("gift exactly once across a lost ack",coins2>coins1&&coins3==coins2,$"coins {coins1} -> {coins2} -> {coins3}");

   // 4. The visit. First the market opens (a free day: customers, timers, the save written every second), then how
   // much the save moves at home in 8 s, then the same save frozen for the whole visit.
   var a=Save();yield return new WaitForSecondsRealtime(8f);var b=Save();
   Note($"social: at home the save {(a.SequenceEqual(b)?"did not change":"changed")} in 8 s ({a.Length} -> {b.Length} bytes)");
   string homeSession=bridge.State.session;int homeItems=CheckoutInterior.Active?CheckoutInterior.Active.items.Count:-1;double homeCoins=bridge.State.coins;
   var before=Save();
   Act("socialVisit","[\"u-ana\"]");
   for(float t=0;t<15&&!(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(5f);
   if(home)home.HomeCamera();yield return new WaitForSecondsRealtime(1.5f);
   Result("visit shows the friend's market",(bridge.State?.session??"").StartsWith("visit-")&&bridge.State.era?.id=="spati"&&CheckoutSocial.Visiting,$"session {bridge.State?.session} era {bridge.State?.era?.id}");
   yield return Shot("social_visit");
   FocusEvolution();yield return new WaitForSecondsRealtime(1.5f);yield return Shot("social_visit_build");
   Act("socialLike","[\"u-ana\"]");yield return new WaitForSecondsRealtime(1.2f);yield return Shot("social_visit_liked");
   Act("socialHelp","[\"u-ana\",\"evolution:evolucao-shelf-produce-2-ana\"]");yield return new WaitForSecondsRealtime(1.2f);yield return Shot("social_visit_helped");
   Route("!visita");yield return new WaitForSecondsRealtime(1.5f);yield return Shot("social_visit_requests");
   Route("");yield return new WaitForSecondsRealtime(4f);
   var during=Save();
   Result("save byte-identical during the visit",before.Length>0&&before.SequenceEqual(during),$"{before.Length} bytes, {Time.realtimeSinceStartup:0}s");
   Act("socialLeave","[]");
   for(float t=0;t<10&&(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(3f);
   int backItems=CheckoutInterior.Active?CheckoutInterior.Active.items.Count:-1;
   Result("back home exactly",bridge.State.session==homeSession&&!CheckoutSocial.Visiting&&backItems==homeItems,$"session {bridge.State.session} items {homeItems} -> {backItems}");
   Result("like + help + delivery booked on the way back",bridge.State.coins>homeCoins,$"coins {homeCoins} -> {bridge.State.coins}");
   yield return Shot("social_back_home");

   // 5. A visit where the player only looks: the save stays the same bytes up to "Voltar".
   var look=Save();Act("socialVisit","[\"u-carla\"]");
   for(float t=0;t<15&&!(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(4f);yield return Shot("social_visit_carla");
   var looked=Save();Act("socialLeave","[]");yield return new WaitForSecondsRealtime(3f);
   Result("look-only visit save-identical",look.SequenceEqual(looked),$"{look.Length} bytes");

   // 6. "Pedir aos amigos" (the stock page and a contract short of a product open it).
   yield return Tips();
   int product=bridge.State.supplierCatalog!=null&&bridge.State.supplierCatalog.Length>0?bridge.State.supplierCatalog[0].productId:1;
   Route("!amigos:pedir:"+product+":10");yield return new WaitForSecondsRealtime(1.5f);yield return Shot("social_request");
   Route("");yield return new WaitForSecondsRealtime(1f);

   // 7. Eva (invited by the player) reached the Späti: 30 diamonds and the first exclusive decoration.
   double gems=bridge.State.diamonds;Act("socialMock","[\"invite-reward\"]");yield return new WaitForSecondsRealtime(.5f);
   Tick();yield return new WaitForSecondsRealtime(.9f);yield return Shot("social_invite_toast");
   yield return new WaitForSecondsRealtime(3f);
   Result("invite reward",bridge.State.diamonds>=gems+30,$"diamonds {gems} -> {bridge.State.diamonds}");

   // 7b. The reward decoration in the market: the build mode places it from the inventory and the layout is saved.
   var interior=CheckoutInterior.Active;var mode=FindAnyObjectByType<CheckoutBuildMode>();
   Note($"social decor: owned {(interior?interior.Owned("invite-reward-1"):-1)}, template {(interior&&interior.HasTemplate(interior.DecorTemplate("invite-reward-1")))}");
   if(interior&&mode){
    CheckoutBuildMode.QaOpenAndSelect();yield return new WaitForSecondsRealtime(1.5f);
    // Outside, on the block (the bench may stand inside or out): the piece lands where the camera looks.
    typeof(CheckoutBuildMode).GetMethod("Focus",BindingFlags.NonPublic|BindingFlags.Instance,null,new[]{typeof(string)},null)?.Invoke(mode,new object[]{"outside"});
    yield return new WaitForSecondsRealtime(1.2f);
    var simulation=FindAnyObjectByType<MarketDay.MarketSimulation>();
    var stall=CheckoutStall.Centre;if(simulation)simulation.Focus(new Vector3(stall.x+4,0,CheckoutInterior.BlockRect.yMin+1.5f),6f);
    yield return new WaitForSecondsRealtime(1.2f);
    typeof(CheckoutBuildMode).GetMethod("PlaceFromStock",BindingFlags.NonPublic|BindingFlags.Instance)?.Invoke(mode,new object[]{"invite-reward-1"});
    yield return new WaitForSecondsRealtime(.5f);
    // Then slid (as a drag would) to the free spot nearest the camera, beside the stall: the camera looks from the
    // south-east, so the block's south edge is never behind a building or the stall's umbrella.
    var piece=interior.items.Values.FirstOrDefault(i=>i.type=="invite-reward-1"&&i.root);
    if(piece!=null){
     var block=CheckoutInterior.BlockRect;Vector3? best=null;float bestScore=float.MaxValue;
     for(float z=block.yMin+.8f;z<block.yMin+12;z+=.5f)for(float x=block.xMin+.8f;x<block.xMax-.8f;x+=.5f){
      float score=(z-block.yMin)+Mathf.Abs(x-(stall.x+4))*.35f;if(score>=bestScore)continue;
      var p=new Vector3(x,piece.root.position.y,z);if(interior.Fits(piece,p,piece.rot,out _)){best=p;bestScore=score;}
     }
     if(best!=null){interior.MoveTo(piece,best.Value);typeof(CheckoutBuildMode).GetMethod("ShowFootprint",BindingFlags.NonPublic|BindingFlags.Instance,null,System.Type.EmptyTypes,null)?.Invoke(mode,null);}
     Note($"social decor: spot {(best?.ToString()??"none free")}, piece at {piece.root.position}");
     if(simulation)simulation.Focus(piece.root.position+new Vector3(0,0,-1.2f),6f);
    }
    yield return new WaitForSecondsRealtime(1.5f);yield return Shot("social_decor_place");
    typeof(CheckoutBuildMode).GetMethod("Finish",BindingFlags.NonPublic|BindingFlags.Instance,null,System.Type.EmptyTypes,null)?.Invoke(mode,null);
    yield return new WaitForSecondsRealtime(3f);
    if(CheckoutBuildMode.Open)CheckoutBuildMode.QaClose();
    var placed=interior.items.Values.FirstOrDefault(i=>i.type=="invite-reward-1"&&i.root);
    Result("invite decoration placed",placed!=null,placed!=null?placed.id+" at "+placed.root.position:"not in the layout");
    // (the QA copy's one-off tips, "A mesinha está esvaziando!", would cover the market)
    if(placed!=null){
     yield return Tips();
     if(simulation)simulation.Focus(placed.root.position+new Vector3(0,0,-.6f),6f);yield return new WaitForSecondsRealtime(1.8f);yield return Shot("social_decor_placed");
    }
   }

   // 8. QR code and "Chamar amigo" (the Editor copies the invite; the phones open the system's share sheet).
   Route("!amigos");yield return new WaitForSecondsRealtime(1.5f);
   Act("socialQr","[]");yield return new WaitForSecondsRealtime(1.2f);yield return Shot("social_qr");
   Act("socialShare","[]");yield return new WaitForSecondsRealtime(1.5f);yield return Shot("social_share");
   if(File.Exists(CheckoutSocial.LastSharePicture)){File.Copy(CheckoutSocial.LastSharePicture,"Logs/at_social_share_picture.png",true);Note("shot social_share_picture");}
   Result("share picture",File.Exists(CheckoutSocial.LastSharePicture),CheckoutSocial.LastSharePicture);
   Act("socialQr","[]");Route("");yield return new WaitForSecondsRealtime(1f);

   // 9. The Amigos page in English (Lucas tests in English: no Portuguese may leak).
   var langBefore=CheckoutI18n.Language;
   void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
   Lang("en");yield return new WaitForSecondsRealtime(1.5f);
   Route("!amigos");yield return new WaitForSecondsRealtime(1.8f);yield return Shot("social_amigos_en");
   Route("");Lang(langBefore);yield return new WaitForSecondsRealtime(1.5f);
  }

  // The drawer's card list (0 = bottom, 1 = top).
  static void ScrollDrawer(float position){
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();if(!hud)return;
   var field=typeof(CheckoutDesktopHUD).GetField("cardScroll",BindingFlags.NonPublic|BindingFlags.Instance);
   if(field?.GetValue(hud) is UnityEngine.UI.ScrollRect scroll)scroll.verticalNormalizedPosition=position;
  }
  // The camera on a build of the friend's market (the works of a piece, or an evolution ring) for the "Ajudar" over it.
  void FocusEvolution(){
   var works=FindObjectsByType<CheckoutInteriorWorks>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault();
   var site=FindObjectsByType<CheckoutEvolutionSite>(FindObjectsInactive.Include,FindObjectsSortMode.None).FirstOrDefault();
   if(works)CheckoutCameraFocus(works.transform.position);else if(site)CheckoutCameraFocus(site.transform.position);
   var ia=CheckoutInterior.Active;var s=bridge?bridge.State:null;
   Note("social: works "+(works?works.BuildId:"none")+", evolution site "+(site?site.EvolutionId:"none")
    +$", pieces [{(ia?string.Join(",",ia.items.Keys.Take(14)):"no interior")}]"
    +$", evolutions [{(s?.evolutions==null?"":string.Join(",",s.evolutions.Select(e=>e.kind+":"+e.targetId)))}]");
  }
 }
}
