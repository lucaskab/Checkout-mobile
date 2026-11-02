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
   IEnumerator Tips(){var h=FindAnyObjectByType<CheckoutDesktopHUD>();for(int i=0;i<3&&h&&h.CoachQa().isTip;i++){Act("dismissOnboardingTip","[]");yield return new WaitForSecondsRealtime(.5f);}}
   yield return Tips();
   Note($"social: market open {bridge.State.isOpen}, day {bridge.State.day?.phase}");

   var langBefore=CheckoutI18n.Language;
   void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
   void Mock(string cmd,string arg="")=>Act("socialMock",arg==""?"[\""+cmd+"\"]":"[\""+cmd+"\",\""+arg+"\"]");
   bool BoardShown()=>CheckoutDesktopHUD.BoardOpen;
   // Every window shot notes how its tiles stand against the fold (whole / cut / below) and whether the side panel
   // shows whole: QA 02/11 "no card may be sliced by the footer on the first view".
   IEnumerator Shot2(string name){yield return Shot(name);Note($"social: fold {name}: {Fold()}");}
   IEnumerator Quiet(){var h=FindAnyObjectByType<CheckoutDesktopHUD>();for(float t=0;t<25&&h&&h.SocialToastShowing;t+=.5f)yield return new WaitForSecondsRealtime(.5f);yield return new WaitForSecondsRealtime(.4f);}

   // 1. First time on Amigos: the full-screen window asks for a name and a face (the 12 faces as tiles).
   Route("!amigos");yield return new WaitForSecondsRealtime(2.5f);
   yield return Tips();Route("~amigos");yield return new WaitForSecondsRealtime(1.5f);
   Result("Amigos is a full-screen window",BoardShown(),"board open "+BoardShown());
   yield return Shot2("social_profile_v3");
   Act("socialSaveProfile","[\"Mercadinho do Lucas\",\"shopper-4\"]");yield return new WaitForSecondsRealtime(2f);
   Route("~amigos");yield return new WaitForSecondsRealtime(1.8f);
   yield return Shot2("social_amigos_v3");

   // 2. The inbox (gift from Ana, like from Bruno, Duda's request): toasts, the badge, the gift as a box in the Correio.
   Route("");yield return new WaitForSecondsRealtime(1f);yield return Tips();
   double coins0=bridge.State.coins;
   Tick();yield return new WaitForSecondsRealtime(.9f);yield return Shot("social_toast_v3");
   yield return new WaitForSecondsRealtime(6f);
   Result("inbox applied (the like pays, the gift waits in the Correio)",bridge.State.coins>coins0,$"coins {coins0} -> {bridge.State.coins}");
   var hudQ=FindAnyObjectByType<CheckoutDesktopHUD>();var setQuick=typeof(CheckoutDesktopHUD).GetMethod("SetQuickOpen",BindingFlags.NonPublic|BindingFlags.Instance);
   if(hudQ&&setQuick!=null){setQuick.Invoke(hudQ,new object[]{true});yield return new WaitForSecondsRealtime(.8f);yield return Shot("social_badge_menu_v3");setQuick.Invoke(hudQ,new object[]{false});}

   // 3. A gift whose ack is lost (the app "died"): one box, acked the next time without a second box.
   Mock("gift");Mock("fail","/v1/social/inbox/ack");yield return new WaitForSecondsRealtime(.5f);
   Tick();yield return new WaitForSecondsRealtime(3f);Tick();yield return new WaitForSecondsRealtime(3f);
   Route("!amigos-correio");yield return new WaitForSecondsRealtime(1.8f);yield return Shot2("social_correio_v3");
   double coins1=bridge.State.coins;
   Act("socialOpenMail","[\"all\"]");yield return new WaitForSecondsRealtime(.45f);yield return Shot("social_correio_open_v3");
   yield return new WaitForSecondsRealtime(2.2f);double coins2=bridge.State.coins;
   Act("socialOpenMail","[\"all\"]");yield return new WaitForSecondsRealtime(1.2f);double coins3=bridge.State.coins;
   var gift=10.0; // mesinha gift
   Result("gifts opened once (two boxes, one of them across a lost ack)",coins2-coins1==2*gift&&coins3==coins2,$"coins {coins1} -> {coins2} -> {coins3}");
   yield return Shot2("social_correio_after_v3");

   // 4. Pedidos: mine (asked now) and the friends' (Ana asks for 6 apples), then the product picker.
   int product=bridge.State.supplierCatalog!=null&&bridge.State.supplierCatalog.Length>0?bridge.State.supplierCatalog[0].productId:1;
   Act("socialRequest","["+product+",8]");yield return new WaitForSecondsRealtime(1.5f);
   Route("!amigos-pedidos");yield return new WaitForSecondsRealtime(1.8f);yield return Shot2("social_pedidos_v3");
   Route("!amigos-pedir");yield return new WaitForSecondsRealtime(1.8f);yield return Shot2("social_picker_v3");
   Route("!amigos-convidar");yield return new WaitForSecondsRealtime(1.8f);yield return Quiet();yield return Shot2("social_convidar_0_v3");
   // "Tem um código de convite?" opens the field (the prizes stay the hero until it is asked for)
   Route("~amigos-convidar:codigo");yield return new WaitForSecondsRealtime(1.5f);yield return Shot2("social_convidar_code_v3");
   Route("");yield return new WaitForSecondsRealtime(.8f);

   // 5. The visit to Ana's Späti: her shelves, plants and bench, a works site and an evolution ring with a floating
   // "Ajudar" each. The save stays byte-identical for the whole visit.
   var a=Save();yield return new WaitForSecondsRealtime(8f);var b=Save();
   Note($"social: at home the save {(a.SequenceEqual(b)?"did not change":"changed")} in 8 s ({a.Length} -> {b.Length} bytes)");
   string homeSession=bridge.State.session;string homeEra=bridge.State.era?.id;bool homeSmall=CheckoutStall.Small;int homeItems=CheckoutInterior.Active?CheckoutInterior.Active.items.Count:-1;double homeCoins=bridge.State.coins;
   var before=Save();
   Act("socialVisit","[\"u-ana\"]");
   for(float t=0;t<15&&!(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(5f);
   var ia=CheckoutInterior.Active;
   Result("visit shows the friend's Späti",(bridge.State?.session??"").StartsWith("visit-")&&bridge.State.era?.id=="spati"&&CheckoutSocial.Visiting&&ia&&ia.items.ContainsKey("shelf:produce"),$"era {bridge.State?.era?.id} pieces [{(ia?string.Join(",",ia.items.Keys):"")}]");
   FocusEvolution();yield return new WaitForSecondsRealtime(2.5f);
   var helpLayer=hudQ?hudQ.transform.GetComponentsInChildren<RectTransform>(true).FirstOrDefault(r=>r.name=="VisitHelp"):null;
   int floating=helpLayer?helpLayer.GetComponentsInChildren<CheckoutDesktopButton>(false).Length:0;
   Result("floating Ajudar over the works site and the evolution ring",floating>=2,$"{floating} floating");
   yield return Shot("social_visit_v3");
   Act("socialLike","[\"u-ana\"]");yield return new WaitForSecondsRealtime(.5f);yield return Shot("social_visit_liked_v3");
   yield return new WaitForSecondsRealtime(.8f);
   Act("socialHelp","[\"u-ana\",\"evolution:evolucao-shelf-produce-2-ana\"]");yield return new WaitForSecondsRealtime(1.4f);yield return Shot("social_visit_helped_v3");
   Route("!visita");yield return new WaitForSecondsRealtime(1.8f);yield return Quiet();yield return Shot2("social_visit_requests_v3");
   Route("");yield return new WaitForSecondsRealtime(3f);
   var during=Save();
   Result("save byte-identical during the visit",before.Length>0&&before.SequenceEqual(during),$"{before.Length} bytes");
   Act("socialLeave","[]");
   for(float t=0;t<10&&(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(3f);
   Result("back home exactly",bridge.State.session==homeSession&&!CheckoutSocial.Visiting&&bridge.State.era?.id==homeEra,$"session {bridge.State.session} era {bridge.State.era?.id}");
   Result("like + help booked on the way back",bridge.State.coins>homeCoins,$"coins {homeCoins} -> {bridge.State.coins}");

   // 6. A friend far ahead (Gabi's supermercado on six lots with its wings): it renders for the visit, and lots, wings
   // and the stall come back exactly on "Voltar". The save stays the same bytes.
   var look=Save();Act("socialVisit","[\"u-gabi\"]");
   for(float t=0;t<15&&!(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(6f);
   if(home)home.HomeCamera();yield return new WaitForSecondsRealtime(1.5f);
   Result("supermercado friend renders",bridge.State.era?.id=="supermercado"&&!CheckoutStall.Small,$"era {bridge.State.era?.id} small {CheckoutStall.Small}");
   yield return Shot("social_visit_gabi_v3");
   FocusEvolution();yield return new WaitForSecondsRealtime(2.5f);yield return Shot("social_visit_gabi_build_v3");
   var looked=Save();Act("socialLeave","[]");
   for(float t=0;t<10&&(bridge.State?.session??"").StartsWith("visit-");t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   yield return new WaitForSecondsRealtime(4f);
   if(home)home.HomeCamera();yield return new WaitForSecondsRealtime(1.5f);
   Result("look-only visit save-identical",look.SequenceEqual(looked),$"{look.Length} bytes");
   Result("everything restored after the supermercado",bridge.State.era?.id==homeEra&&CheckoutStall.Small==homeSmall&&bridge.State.session==homeSession,$"era {bridge.State.era?.id} small {CheckoutStall.Small}");
   yield return Tips();yield return Shot("social_back_home_v3");

   // 7. Invites: three of the player's friends reached the Späti (30 diamonds each; decorations at 1 and 3).
   double gems=bridge.State.diamonds;
   for(int i=0;i<3;i++){Mock("invite-reward");yield return new WaitForSecondsRealtime(.2f);}
   Tick();yield return new WaitForSecondsRealtime(4f);
   Result("invite rewards",bridge.State.diamonds>=gems+90,$"diamonds {gems} -> {bridge.State.diamonds}");
   Act("socialRefresh","[]");yield return new WaitForSecondsRealtime(1.5f);
   Route("!amigos-convidar");yield return new WaitForSecondsRealtime(1.8f);yield return Quiet();yield return Shot2("social_convidar_3_v3");
   Act("socialQr","[]");yield return new WaitForSecondsRealtime(1.2f);yield return Quiet();yield return Shot2("social_qr_v3");
   Act("socialQr","[]");yield return new WaitForSecondsRealtime(.6f);

   // 8. The share postcard (the Editor copies the invite; the phones open the system's share sheet).
   Act("socialShare","[]");yield return new WaitForSecondsRealtime(2f);yield return Shot("social_share_v3");
   if(File.Exists(CheckoutSocial.LastSharePicture)){File.Copy(CheckoutSocial.LastSharePicture,"Logs/at_social_share_picture_v3.png",true);Note("shot social_share_picture_v3");}
   Result("share postcard",File.Exists(CheckoutSocial.LastSharePicture),CheckoutSocial.LastSharePicture);
   Route("~amigos:perfil");yield return new WaitForSecondsRealtime(1.8f);yield return Shot2("social_perfil_v3");

   // 9. English (Lucas tests in English: no Portuguese may leak).
   Lang("en");yield return new WaitForSecondsRealtime(1.5f);
   foreach(var r in new[]{"amigos","amigos-pedidos","amigos-convidar","amigos-correio"}){Route("!"+r);yield return new WaitForSecondsRealtime(1.8f);yield return Quiet();yield return Shot2("social_"+r.Replace("amigos-","")+"_en_v3");}
   Lang(langBefore);yield return new WaitForSecondsRealtime(1f);

   // 10. iPad (4:3): the same windows must lay out.
   Note("social: "+CheckoutQaGameView.Set(2048,1536));yield return new WaitForSecondsRealtime(2f);
   foreach(var r in new[]{"amigos","amigos-convidar"}){Route("!"+r);yield return new WaitForSecondsRealtime(2f);yield return Quiet();yield return Shot2("social_"+r.Replace("amigos-","")+"_ipad_v3");}
   Note("social: "+CheckoutQaGameView.Set(2778,1284));yield return new WaitForSecondsRealtime(2f);

   // 11. No friends at all: the empty state invites.
   Mock("solo");Act("socialRefresh","[]");yield return new WaitForSecondsRealtime(1.5f);
   Route("!amigos");yield return new WaitForSecondsRealtime(1.8f);yield return Shot2("social_amigos_empty_v3");
   Route("");yield return new WaitForSecondsRealtime(1f);
  }

  // How the open board's tiles stand against the fold: whole, cut (partly hidden) and below (out of view), plus whether
  // the side panel's content fits without a scroll.
  static string Fold(){
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();if(!hud||!CheckoutDesktopHUD.BoardOpen)return "no board";
   const BindingFlags F=BindingFlags.NonPublic|BindingFlags.Instance;
   var scroll=typeof(CheckoutDesktopHUD).GetField("boardScroll",F)?.GetValue(hud) as UnityEngine.UI.ScrollRect;
   var detail=typeof(CheckoutDesktopHUD).GetField("boardDetailScroll",F)?.GetValue(hud) as UnityEngine.UI.ScrollRect;
   var tiles=typeof(CheckoutDesktopHUD).GetField("boardTiles",F)?.GetValue(hud) as System.Collections.IEnumerable;
   if(!scroll||tiles==null)return "?";
   var vp=scroll.viewport?scroll.viewport:(RectTransform)scroll.transform;var c=new Vector3[4];vp.GetWorldCorners(c);float top=c[1].y,bottom=c[0].y;
   int whole=0,cut=0,below=0;
   foreach(var o in tiles){if(o is not Component tile||!tile.gameObject.activeInHierarchy)continue;((RectTransform)tile.transform).GetWorldCorners(c);
    float t=c[1].y,b=c[0].y;if(b>=bottom-1&&t<=top+1)whole++;else if(t<bottom||b>top)below++;else cut++;}
   string panel="";
   if(detail){var dv=detail.viewport?detail.viewport:(RectTransform)detail.transform;panel=$", panel fits {detail.content.rect.height<=dv.rect.height+1} ({detail.content.rect.height:0}/{dv.rect.height:0})";}
   return $"whole {whole}, cut {cut}, below {below}{panel}";
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
   // (a little north of the site, so its floating "Ajudar" sits clear of the visit bar)
   var at=works?works.transform.position:site?site.transform.position:(Vector3?)null;
   if(at!=null)CheckoutCameraFocus(at.Value+new Vector3(0,0,1.4f));
   var ia=CheckoutInterior.Active;var s=bridge?bridge.State:null;
   Note("social: works "+(works?works.BuildId:"none")+", evolution site "+(site?site.EvolutionId:"none")
    +$", pieces [{(ia?string.Join(",",ia.items.Keys.Take(14)):"no interior")}]"
    +$", evolutions [{(s?.evolutions==null?"":string.Join(",",s.evolutions.Select(e=>e.kind+":"+e.targetId)))}]");
  }
 }
}
