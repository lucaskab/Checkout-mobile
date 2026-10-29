using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Checkout {
 // Dona Neide's tutorial played like a new player ("onboarding-<lang>-<device>[-<label>]", e.g. "onboarding-en-ipad"; one run
 // per play session, "-desk" runs the desktop UI). Runs on a brand-new QA save (CheckoutStartMenu.QaFresh, never the player's
 // save) at the device's resolution (phone 2778x1284, mini 1792x828, ipad 2048x1536, desk 1600x900; the Game view goes back to
 // its size at the end).
 // Every step: the test taps exactly where the guide's hand points (a real UI raycast at the fingertip, or a map tap there),
 // plays the mini-games the step opens (register, supplier shop, unloading), and logs per step the target, its rect, the
 // spotlight hole, the fingertip, what a finger would hit there, whether the card covers the target or the open page, and
 // the time the step took. STEP / PROBLEM / STUCK lines in Logs/autotest_log.txt; shots Logs/ob_<lang>_<device>_<nn>_<step>.jpg
 // (cyan = the real button, yellow = the hole, red ring = where the fingertip taps).
 public sealed partial class CheckoutAutoTest {
  int onboardingRuns;
  readonly List<string> obProblems=new List<string>();

  IEnumerator Onboarding(string request){
   var parts=request.Split('-');string lang=parts.Length>1?parts[1]:"pt",device=parts.Length>2?parts[2]:"phone";
   string tag=lang+"_"+device+(parts.Length>3?"_"+parts[3]:""); // an optional label keeps earlier shots ("onboarding-pt-phone-fixed")
   var host=CheckoutDesktopHost.Active;var hud=host?host.Hud:null;
   if(!hud){Note("onboarding: no HUD");yield break;}
   foreach(var f in Directory.GetFiles("Logs","ob_"+tag+"_*.jpg"))File.Delete(f);
   var size=device=="ipad"?new Vector2Int(2048,1536):device=="desk"?new Vector2Int(1600,900):device=="mini"?new Vector2Int(1792,828):new Vector2Int(2778,1284);
   Note("onboarding "+tag+": "+CheckoutQaGameView.Set(size.x,size.y));
   yield return new WaitForSecondsRealtime(1.5f);
   Note($"onboarding {tag}: screen {Screen.width}x{Screen.height} safe {Screen.safeArea} handheld {CheckoutScreen.Handheld} qaFresh {CheckoutStartMenu.QaFresh}");
   if(!CheckoutStartMenu.QaFresh){Note("onboarding: not on a fresh QA save, stopping (the player's save is never played)");yield break;}
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
   var languageBefore=CheckoutI18n.Language;Lang(lang);
   // One run per play session: after a reset the map keeps the old session's customers as "seen", so nobody walks in.
   if(onboardingRuns++>0){Note("onboarding "+tag+": skipped, one onboarding run per play session (send another play request)");Lang(languageBefore);yield break;}
   Route("");var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();
   yield return new WaitForSecondsRealtime(2.5f);
   // "-results": like Lucas's save (29/10), a day already ended with its results waiting when the tutorial goes on.
   string label=parts.Length>3?parts[3]:"";
   Note($"onboarding {tag}: guide before the run '{hud.CoachQa().key}'");
   if(label.StartsWith("results")){
    void Hud(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+action+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
    // With a contract that is then missed, like Lucas's day: the results page also shows the consolation card, so
    // COLETAR starts further down the list.
    Route("!day");yield return new WaitForSecondsRealtime(2f);
    var accept=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).FirstOrDefault(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.action=="startDay"&&b.Data.enabled);
    if(accept)accept.Clicked?.Invoke(accept);else Hud("startDay","[\"livre\"]");
    yield return new WaitForSecondsRealtime(2f);Note($"  after startDay ({(accept?"a contract":"free day")}): guide '{hud.CoachQa().key}'");
    Hud("closeDay","[]");yield return new WaitForSecondsRealtime(2.5f);Note($"  after closeDay: guide '{hud.CoachQa().key}'");
    Note("onboarding "+tag+": a day was opened and closed, its results wait to be collected");
   }
   obProblems.Clear();bool scrollChecked=false;int repeats=0,stucks=0,scrollsAt=Scrolls(hud.CoachQa());
   string last=null;float runAt=Time.realtimeSinceStartup,stepAt=runAt;int shot=0,acts=0;bool stuckNoted=false;var order=new List<string>();
   while(Time.realtimeSinceStartup-runAt<900){
    yield return new WaitForSecondsRealtime(.5f);
    if(hud.LevelUpOpen||hud.ConquestOpen){Note("celebration on screen: closed by the test");yield return Mark($"ob_{tag}_{++shot:00}_celebration",hud.CoachQa());hud.QaCloseCelebrations();yield return new WaitForSecondsRealtime(1);continue;}
    var q=hud.CoachQa();
    if(q.key!=last){
     if(last!=null)Note($"STEP_DONE {last} in {Time.realtimeSinceStartup-stepAt:0.0}s, {acts} taps");
     last=q.key;stepAt=Time.realtimeSinceStartup;acts=0;stuckNoted=false;
     if(q.key.Length==0&&order.Contains("objetivo")){yield return new WaitForSecondsRealtime(2.5f);yield return Mark($"ob_{tag}_{++shot:00}_end",hud.CoachQa());break;}
     // The guide must only move forward: a step or tip that comes back after another one is a loop (Lucas 29/10:
     // "fica meio que se repetindo"). The step that the day's results interrupted coming back is a resume.
     if(q.key.Length>0&&(order.Count==0||order[order.Count-1]!=q.key)){
      if(order.Contains(q.key)){
       bool resume=order.Count>=2&&order[order.Count-1]=="fim-do-dia"&&order[order.Count-2]==q.key;
       if(resume)Note($"RESUMED '{q.key}' after the day's results");
       else{repeats++;Problem($"REPEAT '{q.key}' shown again after {string.Join(" > ",order.Skip(Math.Max(0,order.Count-3)))}");}
      }
      order.Add(q.key);
     }
     yield return new WaitForSecondsRealtime(1.4f); // the page opening, the card's layout, the hand settling
     q=hud.CoachQa();
     if(q.key!=last)continue;
     yield return Mark($"ob_{tag}_{++shot:00}_{(q.key.Length>0?q.key:"none")}",q);Report(q);
     // Once per run, a target in a scrolling list is scrolled out of view (as a player would): the guide must bring it
     // back on its own and point at it again.
     var list=q.found&&q.targetUi&&!scrollChecked?q.targetUi.GetComponentInParent<UnityEngine.UI.ScrollRect>():null;
     if(list&&list.vertical&&list.content&&list.content.rect.height>((RectTransform)list.transform).rect.height+40){
      scrollChecked=true;int before=Scrolls(q);var far=list.verticalNormalizedPosition>.5f?0f:1f;
      list.StopMovement();list.verticalNormalizedPosition=far;yield return new WaitForSecondsRealtime(.3f);
      var gone=hud.CoachQa();Note($"SCROLL_CHECK '{q.key}': list moved away, target in view now: {gone.found}");
      yield return Mark($"ob_{tag}_{++shot:00}_{q.key}_scrolled_away",gone);
      yield return new WaitForSecondsRealtime(2.2f);
      var back=hud.CoachQa();bool ok=back.found&&Scrolls(back)>before&&back.targetRect.Overlaps(back.hole);
      Note($"SCROLL_CHECK '{q.key}': the guide scrolled the list back: {ok} (scrolls {before} -> {Scrolls(back)}, found {back.found})");
      yield return Mark($"ob_{tag}_{++shot:00}_{q.key}_scrolled_back",back);
      if(!ok)Problem($"'{q.key}': the guide did not bring its target back after the list was scrolled away");
      q=back;
     }
    }
    if(q.key.Length==0){if(Time.realtimeSinceStartup-stepAt>20){Note("STUCK: no guide on screen for 20 s");break;}continue;}
    float limit=q.key=="primeiro-cliente"||q.key=="caixa"?120:q.key=="caminhao"?75:45;
    if(Time.realtimeSinceStartup-stepAt>limit&&!stuckNoted){stuckNoted=true;stucks++;Problem($"STUCK on '{q.key}' for {limit:0}s ({acts} taps)");yield return Mark($"ob_{tag}_{++shot:00}_{q.key}_stuck",q);Report(q);}
    if(Time.realtimeSinceStartup-stepAt>limit*2){Note("GIVE UP on "+q.key);break;}
    bool acted=false;yield return Act(q,tag,acts,()=>{acted=true;acts++;},n=>shot+=n,()=>shot);
    if(acted)yield return new WaitForSecondsRealtime(1.2f);
   }
   bool finished=order.Contains("objetivo");int scrolled=Scrolls(hud.CoachQa())-scrollsAt;
   Note($"onboarding {tag}: steps seen {string.Join(" > ",order)}; {obProblems.Count} problems; total {Time.realtimeSinceStartup-runAt:0}s; the guide scrolled a list {scrolled} times");
   Note($"ONBOARDING_RESULT {tag} {(finished&&stucks==0&&repeats==0?"PASS":"FAIL")} finished={finished} stuck={stucks} repeats={repeats} problems={obProblems.Count}");
   foreach(var p in obProblems)Note("  PROBLEM "+p);
   Lang(languageBefore);Route("");yield return new WaitForSecondsRealtime(1.5f);
  }

  // One move of a player following the guide.
  IEnumerator Act(CheckoutDesktopHUD.CoachQaInfo q,string tag,int taps,Action acted,Action<int> shots,Func<int> shotNow){
   // A mini-game the step opened: play it like the player (the guide only leaves a corner note meanwhile).
   var counter=CheckoutCounterGame.Instance;var shop=CheckoutSupplierShop.Instance;var recv=CheckoutReceivingGame.Instance;
   if(counter&&counter.IsOpen){acted();shots(1);yield return Mark($"ob_{tag}_{shotNow():00}_{q.key}_register",q);yield return PlayRegister(counter);yield break;}
   if(shop&&shop.IsOpen){acted();shots(1);yield return Mark($"ob_{tag}_{shotNow():00}_{q.key}_shop",q);yield return PlayShop(shop,tag,q,shots,shotNow);yield break;}
   if(recv&&recv.IsOpen){acted();shots(1);yield return Mark($"ob_{tag}_{shotNow():00}_{q.key}_unload",q);yield return PlayUnload(recv);yield break;}
   foreach(var other in new MonoBehaviour[]{CheckoutStockroom.Instance,CheckoutRestockGame.Instance,CheckoutIncidents.Instance,CheckoutPackingGame.Instance}){
    bool open=other&&(bool)(other.GetType().GetProperty("IsOpen")?.GetValue(other)??false);
    if(open){acted();var what=$"'{q.key}': a window the step does not need is open ({other.GetType().Name}), closed by the test";if(q.isTip)Note(what);else Problem(what);other.SendMessage("Close",SendMessageOptions.DontRequireReceiver);yield break;}
   }
   if(CheckoutSettings.Open){acted();shots(1);yield return Mark($"ob_{tag}_{shotNow():00}_{q.key}_settings",q);
    if(q.card&&q.cardRect.Overlaps(SettingsRect()))Problem($"'{q.key}': the guide's card covers the Opções window");
    CheckoutSettings.Hide();yield break;}
   // A step that can also be finished with its card's button ("Depois"): after following the hand twice, the button.
   if(q.found&&q.buttonUi&&taps>=2){acted();yield return TapUi(q.buttonUi,$"'{q.key}' card button");yield break;}
   // The hand points at something: tap exactly at the fingertip.
   if(q.found){acted();yield return TapAtHand(q);yield break;}
   // A card with a button (welcome, "Entendi", "Depois", the end card).
   if(q.card&&q.buttonUi){acted();yield return TapUi(q.buttonUi,$"'{q.key}' card button");yield break;}
   // A page open and the guide asks to close it (vitrine / deposito): read a moment, then the X.
   var close=PageX();
   if(q.page&&close&&(q.key=="vitrine"||q.key=="deposito")&&Time.realtimeSinceStartup-lastObTap>2.5f){acted();yield return TapUi(close,$"'{q.key}' page X");yield break;}
   // A spotlight / pointing step whose target cannot be found.
   if(!string.IsNullOrEmpty(q.target)&&!q.found&&Time.realtimeSinceStartup-lastNotFound>8){lastNotFound=Time.realtimeSinceStartup;Problem($"'{q.key}': target '{q.target}' not on screen (page open: {q.page}, card: {q.card}, compact: {q.compact})");}
  }
  float lastObTap,lastNotFound;
  // How many times the guide scrolled a list to its target (read by name, so the test also runs on a coach without it).
  static int Scrolls(CheckoutDesktopHUD.CoachQaInfo q){var f=q.GetType().GetField("scrolls");return f!=null?(int)f.GetValue(q):0;}
  // The X of the page window on screen (the side drawer or a full-screen window: shelf, board, kitchen, shop).
  static RectTransform PageX(){
   foreach(var b in FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None))
    if(b.isActiveAndEnabled&&b.Data!=null&&b.Data.label=="X"&&string.IsNullOrEmpty(b.Data.route)&&string.IsNullOrEmpty(b.Data.action)&&b.GetComponentInParent<CheckoutDesktopHUD>())return (RectTransform)b.transform;
   return null;
  }
  static Rect SettingsRect(){var go=GameObject.Find("CheckoutSettings");if(!go)return default;var r=go.GetComponentsInChildren<RectTransform>().Where(t=>t.name=="Window"||t.name=="Frame"||t.name=="Panel").FirstOrDefault();return r?ScreenRect(r):default;}

  // ---------------------------------------------------------------- taps
  static List<RaycastResult> UiHits(Vector2 at){var hits=new List<RaycastResult>();var es=EventSystem.current;if(es)es.RaycastAll(new PointerEventData(es){position=at},hits);return hits;}
  static string ObPath(Transform t){if(!t)return "(nothing)";var s=t.name;for(int i=0;i<3&&t.parent;i++){t=t.parent;s=t.name+"/"+s;}return s;}
  static bool UnderCoach(Transform t)=>t&&t.GetComponentsInParent<Canvas>(true).Any(c=>c.name=="CheckoutCoach");
  static void Click(GameObject go,Vector2 at){
   var data=new PointerEventData(EventSystem.current){position=at,pressPosition=at,button=PointerEventData.InputButton.Left,clickCount=1,eligibleForClick=true};
   var down=ExecuteEvents.ExecuteHierarchy(go,data,ExecuteEvents.pointerDownHandler);
   var up=down??ExecuteEvents.GetEventHandler<IPointerUpHandler>(go);if(up)ExecuteEvents.Execute(up,data,ExecuteEvents.pointerUpHandler);
   var click=ExecuteEvents.GetEventHandler<IPointerClickHandler>(go);if(click)ExecuteEvents.Execute(click,data,ExecuteEvents.pointerClickHandler);
  }
  static Rect ScreenRect(RectTransform r){var c=new Vector3[4];r.GetWorldCorners(c);var canvas=r.GetComponentInParent<Canvas>();var cam=canvas&&canvas.renderMode!=RenderMode.ScreenSpaceOverlay?canvas.worldCamera:null;
   Vector2 a=new Vector2(float.MaxValue,float.MaxValue),b=new Vector2(float.MinValue,float.MinValue);foreach(var w in c){var s=RectTransformUtility.WorldToScreenPoint(cam,w);a=Vector2.Min(a,s);b=Vector2.Max(b,s);}return Rect.MinMaxRect(a.x,a.y,b.x,b.y);}
  // A finger on a UI element's centre: whatever is on top there gets the tap (a cover over it is reported).
  IEnumerator TapUi(RectTransform target,string what){
   lastObTap=Time.realtimeSinceStartup;
   if(!target){Note("tap: missing "+what);yield break;}
   var at=ScreenRect(target).center;var hits=UiHits(at);var top=hits.Count>0?hits[0].gameObject:null;
   bool ok=top&&top.transform.IsChildOf(target);
   Note($"tap {what} at {at.x:0},{at.y:0}: top={ObPath(top?top.transform:null)} {(ok?"ok":"COVERED")}");
   if(!ok){Problem($"{what}: covered by {ObPath(top?top.transform:null)}");top=target.gameObject;}
   Click(top,at);yield return null;
  }
  // The guide's tap: at the fingertip. UI: the top element there must be the target; map: no UI may be on top and the
  // ray must hit the target object.
  IEnumerator TapAtHand(CheckoutDesktopHUD.CoachQaInfo q){
   lastObTap=Time.realtimeSinceStartup;
   var tip=q.tip;var hits=UiHits(tip);var top=hits.Count>0?hits[0].gameObject:null;
   if(q.targetUi){
    bool ok=top&&top.transform.IsChildOf(q.targetUi);
    Note($"tap '{q.key}' at the fingertip {tip.x:0},{tip.y:0} ({q.part}): top={ObPath(top?top.transform:null)} {(ok?"ok":"MISSES the target")}");
    if(!ok){Problem($"'{q.key}': the fingertip ({tip.x:0},{tip.y:0}) is not on '{q.part}' {Fmt(q.targetRect)}; a tap there hits {ObPath(top?top.transform:null)}");Click(q.targetUi.gameObject,q.targetRect.center);}
    else Click(top,tip);
   }else if(q.targetWorld){
    var hit=hits.Count>0&&!UnderCoach(top.transform)?top:null;
    if(hit){Problem($"'{q.key}': the map target '{q.part}' is under UI at the fingertip ({ObPath(hit.transform)})");}
    var t=bridge.WorldTap(tip);
    Note($"tap '{q.key}' on the map at the fingertip {tip.x:0},{tip.y:0}: hit {(t?t.panel+"/"+t.name:"nothing")}");
    if(!t||t.panel!=q.targetWorld.panel){Problem($"'{q.key}': the fingertip on the map hits {(t?t.panel:"nothing")}, not {q.targetWorld.panel}");bridge.WorldTap(q.targetRect.center);}
   }
   yield return null;
  }

  // ---------------------------------------------------------------- mini-games
  IEnumerator PlayRegister(CheckoutCounterGame g){
   yield return new WaitForSecondsRealtime(1.2f);
   int servedBefore=bridge.State?.served??-1;string id=g.QaEntryId,phase="";float start=Time.realtimeSinceStartup;
   void Track(){var p=g.QaPhase;if(p!=phase){phase=p;Note($"register {id}: {p} at {Time.realtimeSinceStartup-start:0.0}s, patience {g.QaPatience:0.00}");}}
   Track();
   yield return g.QaScanAll();
   for(float t=0;t<45&&g.IsOpen;t+=.4f){
    Track();
    // Done: the register closes by itself after the receipt (forcing it shut earlier cancels the sale).
    if(g.QaFinished){yield return new WaitForSecondsRealtime(.4f);continue;}
    if(g.QaPaying){g.QaPayAll();yield return new WaitForSecondsRealtime(1.6f);continue;}
    if(g.QaChanging){g.QaGive(g.QaNextChange);yield return new WaitForSecondsRealtime(.6f);continue;}
    var card=g.QaCard();var slot=g.QaCardSlot;
    if(card&&slot){yield return Drag(card.gameObject,ScreenOf(slot));yield return new WaitForSecondsRealtime(2.4f);continue;}
    yield return new WaitForSecondsRealtime(.4f);
   }
   Track();
   yield return new WaitForSecondsRealtime(1.5f);
   int servedAfter=bridge.State?.served??-1;
   Note($"register {id}: {(g.IsOpen?"STILL OPEN":"closed")} after {Time.realtimeSinceStartup-start:0.0}s, served {servedBefore} -> {servedAfter}");
   if(g.IsOpen){Problem("register did not close by itself");g.Close();}
  }
  IEnumerator PlayShop(CheckoutSupplierShop shop,string tag,CheckoutDesktopHUD.CoachQaInfo q,Action<int> shots,Func<int> shotNow){
   yield return new WaitForSecondsRealtime(1.5f);
   var add=shop.QaAddButton();
   if(add){yield return TapUi((RectTransform)add.transform,"shop '"+add.Data?.label+"'");yield return new WaitForSecondsRealtime(1);}
   else Problem("shop: no product to add");
   shots(1);yield return Mark($"ob_{tag}_{shotNow():00}_{q.key}_cart",CheckoutDesktopHost.Active.Hud.CoachQa());
   if(shop.QaCartBoxes>0)yield return TapUi((RectTransform)shop.QaBuyButton.transform,"shop '"+shop.QaBuyButton.Data?.label+"'");
   for(float t=0;t<6&&shop.QaBusy;t+=.3f)yield return new WaitForSecondsRealtime(.3f);
   yield return new WaitForSecondsRealtime(1.5f);
   if(shop.IsOpen)shop.QaClose();
   yield return new WaitForSecondsRealtime(1);
  }
  IEnumerator PlayUnload(CheckoutReceivingGame g){
   yield return new WaitForSecondsRealtime(3f);
   int moved=0;
   for(int i=0;i<16&&g.IsOpen;i++){if(!g.QaNextDrop(out var box,out var rack))break;yield return Drag(box.gameObject,ScreenOf(rack));moved++;}
   Note($"unload: {moved} boxes dragged");
   yield return new WaitForSecondsRealtime(3f);
   if(g.IsOpen)g.QaClose();
  }

  // ---------------------------------------------------------------- log and shots
  void Problem(string text){obProblems.Add(text);Note("PROBLEM "+text);}
  static string Fmt(Rect r)=>r.width<=0?"-":$"[{r.xMin:0},{r.yMin:0} {r.width:0}x{r.height:0}]";
  static float OverlapArea(Rect a,Rect b){if(a.width<=0||b.width<=0)return 0;float w=Mathf.Min(a.xMax,b.xMax)-Mathf.Max(a.xMin,b.xMin),h=Mathf.Min(a.yMax,b.yMax)-Mathf.Max(a.yMin,b.yMin);return w>0&&h>0?w*h:0;}
  void Report(CheckoutDesktopHUD.CoachQaInfo q){
   Note($"STEP '{q.key}' mode={q.mode}{(q.isTip?" (tip)":"")} target='{q.target}' found={q.found} part='{q.part}' dims={q.dims} card={q.card} compact={q.compact} page={q.page} title='{q.title}'");
   if(q.found){
    var top=UiHits(q.tip).Select(h=>h.gameObject).FirstOrDefault();
    bool tipIn=q.targetRect.Contains(q.tip),covers=q.hole.Contains(q.targetRect.min)&&q.hole.Contains(q.targetRect.max);
    Note($"  target {Fmt(q.targetRect)} hole {Fmt(q.hole)} fingertip {q.tip.x:0},{q.tip.y:0} tipInTarget={tipIn} holeCoversTarget={covers} card {Fmt(q.cardRect)} top@tip={ObPath(top?top.transform:null)}");
    if(!tipIn)Problem($"'{q.key}': fingertip {q.tip.x:0},{q.tip.y:0} outside the target {Fmt(q.targetRect)} ({q.part})");
    // The floating buttons pulse (their scale is rewritten every frame by their game and their rail), so at the end of the
    // frame they measure up to ~20% bigger than what is drawn: for them the fingertip check above is the one that counts.
    if(!covers&&!q.part.StartsWith("fab:"))Problem($"'{q.key}': the hole {Fmt(q.hole)} does not cover the target {Fmt(q.targetRect)} ({q.part})");
    if(q.card&&OverlapArea(q.cardRect,q.targetRect)>0)Problem($"'{q.key}': the guide's card {Fmt(q.cardRect)} covers the target {Fmt(q.targetRect)}");
    if(q.mode=="spotlight"&&!q.dims)Problem($"'{q.key}': spotlight without the dimmed screen");
    if(q.targetUi){var center=UiHits(q.targetRect.center).Select(h=>h.gameObject).FirstOrDefault(g=>!UnderCoach(g.transform));if(center&&!center.transform.IsChildOf(q.targetUi))Problem($"'{q.key}': the target {q.part} is covered by {ObPath(center.transform)}");}
   }
   // A side window (the drawer) leaves room for the card; a full-screen window cannot be avoided, only its target.
   if(q.mode!="modal"&&q.page&&q.card&&q.drawerRect.width>0&&q.drawerRect.width<Screen.width*.7f){
    float o=OverlapArea(q.cardRect,q.drawerRect);
    bool targetInDrawer=q.found&&OverlapArea(q.targetRect,q.drawerRect)>0;
    if(o>q.cardRect.width*q.cardRect.height*.15f)Problem($"'{q.key}': the guide's card {Fmt(q.cardRect)} covers the open page {Fmt(q.drawerRect)} ({o/(q.cardRect.width*q.cardRect.height):P0} of the card){(targetInDrawer?"":" while pointing outside it")}");
   }
  }
  IEnumerator Mark(string name,CheckoutDesktopHUD.CoachQaInfo q){
   yield return new WaitForEndOfFrame();
   var tex=ScreenCapture.CaptureScreenshotAsTexture();
   if(q!=null&&q.found){float s=Mathf.Max(1,Screen.height/700f);Outline(tex,q.targetRect,Color.cyan,(int)(3*s));Outline(tex,q.hole,Color.yellow,(int)(2*s));Ring(tex,q.tip,12*s,3*s,Color.red);}
   tex.Apply();File.WriteAllBytes("Logs/"+name+".jpg",tex.EncodeToJPG(80));Destroy(tex);Note("shot "+name);
  }
  static void Outline(Texture2D t,Rect r,Color c,int w){
   if(r.width<=0)return;int x0=Mathf.Clamp((int)r.xMin,0,t.width-1),x1=Mathf.Clamp((int)r.xMax,0,t.width-1),y0=Mathf.Clamp((int)r.yMin,0,t.height-1),y1=Mathf.Clamp((int)r.yMax,0,t.height-1);
   for(int k=0;k<w;k++){for(int x=x0;x<=x1;x++){Px(t,x,y0+k,c);Px(t,x,y1-k,c);}for(int y=y0;y<=y1;y++){Px(t,x0+k,y,c);Px(t,x1-k,y,c);}}
  }
  static void Ring(Texture2D t,Vector2 p,float radius,float width,Color c){
   int r=(int)(radius+width);for(int y=-r;y<=r;y++)for(int x=-r;x<=r;x++){float d=Mathf.Sqrt(x*x+y*y);if(d<=radius+width&&d>=radius-width||d<2.5f)Px(t,(int)p.x+x,(int)p.y+y,c);}
  }
  static void Px(Texture2D t,int x,int y,Color c){if(x>=0&&y>=0&&x<t.width&&y<t.height)t.SetPixel(x,y,c);}
 }
}
