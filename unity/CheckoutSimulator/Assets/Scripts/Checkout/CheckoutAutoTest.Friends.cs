using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Checkout {
 // The TestFlight 1.0 (11) fixes (Lucas 05/11), on the QA copy of the save against the host's fake server
 // (desktop/social-mock.ts), at the iPhone's landscape size, recorded at 30 fps into Logs/ff_demo.mjpg (JPEG frames back
 // to back, ffmpeg reads them as a video) with stills Logs/ff_*.jpg:
 //  "eventsfriends-phone"
 //   a. Amigos opened signed out ("Entre para jogar com amigos" with the Apple and Google buttons), then the sign-in
 //      completes while the window stays open (simulated: the fake account signs in, slow answers): the window goes from
 //      "Carregando os amigos…" to the first-time setup (name + faces) by itself, never reopened.
 //   b. The face list: every face above the fold, and the list scrolled with the market running (views arriving):
 //      the tile view never ends above the footer while scrolled (the band of TestFlight 1.0 (11)), next to a still of
 //      the old behaviour (CheckoutDesktopHUD.QaLegacySnap) for comparison.
 //   c. Windows with no dark backdrop: Loja, Amigos, Ranking, Opções, a level-up and a conquest card.
 //   d. (unrecorded) a profile call that never answers: the error card with "Tentar de novo" in at most 20 s, and the
 //      retry loads.
 //  "onboardingspot-pt-phone" (a brand-new QA save): a few seconds of the tutorial's spotlight, still dimmed, into
 //  Logs/ff_spot.mjpg.
 // RESULT lines in Logs/autotest_log.txt. The player's own save and account are never touched (cloud status messages here
 // only reach this QA session's host).
 public sealed partial class CheckoutAutoTest {
  FileStream recFile;int recFrames;bool recOn;

  // ------------------------------------------------------------------ recording (30 fps, a fixed game step)
  IEnumerator RecLoop(){
   while(recOn){
    yield return new WaitForEndOfFrame();
    if(!recOn||recFile==null)break;
    var jpg=RecJpg(recW,recQ);recFile.Write(jpg,0,jpg.Length);recFrames++;
   }
  }
  void RecStart(string path){recFile=File.Create(path);recFrames=0;recOn=true;Time.captureFramerate=30;StartCoroutine(RecLoop());Note("rec start "+path);}
  void RecStop(){recOn=false;Time.captureFramerate=0;recFile?.Close();recFile=null;Note($"rec stop: {recFrames} frames ({recFrames/30f:0.0}s of video)");}
  float RecAt=>recFrames/30f;
  // While recording every frame is 1/30 s of video: waits count frames.
  static IEnumerator Frames(float seconds){int n=Mathf.Max(1,Mathf.RoundToInt(seconds*30));for(int i=0;i<n;i++)yield return null;}
  // Frames rendered at recSuper times the Game view's size and averaged down (the trailer: no crawling edges).
  static int recSuper=1;
  static byte[] RecJpg(int width,int quality){
   var tex=ScreenCapture.CaptureScreenshotAsTexture(recSuper);tex.filterMode=FilterMode.Bilinear;
   float k=Mathf.Min(1,width/(float)tex.width);
   int w=Mathf.RoundToInt(tex.width*k)/2*2,h=Mathf.RoundToInt(tex.height*k)/2*2;
   var rt=RenderTexture.GetTemporary(w,h,0,RenderTextureFormat.ARGB32,RenderTextureReadWrite.Linear);
   Graphics.Blit(tex,rt);
   var prev=RenderTexture.active;RenderTexture.active=rt;
   var small=new Texture2D(w,h,TextureFormat.RGB24,false);small.ReadPixels(new Rect(0,0,w,h),0,0);small.Apply();
   RenderTexture.active=prev;RenderTexture.ReleaseTemporary(rt);
   var bytes=small.EncodeToJPG(quality);Destroy(small);Destroy(tex);
   return bytes;
  }
  IEnumerator Still(string name){yield return new WaitForEndOfFrame();File.WriteAllBytes("Logs/ff_"+name+".jpg",RecJpg(4000,86));Note($"still ff_{name}.jpg at {RecAt:0.0}s of video");}

  // ------------------------------------------------------------------ the scenario
  IEnumerator Friends(string request){
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-friends-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Mock(string cmd,string arg="")=>Act("socialMock",arg==""?"[\""+cmd+"\"]":"[\""+cmd+"\",\""+arg+"\"]");
   // The host's view of the account (desktop/cloud.ts): the Amigos sign-in card shows its buttons from it. Only this QA
   // session's host hears it: no CheckoutCloud runs on the QA copy.
   void Cloud(string status,string provider="")=>CheckoutBridge.Emit("{\"kind\":\"cloud\",\"status\":\""+status+"\",\"email\":\"\",\"name\":\"\",\"provider\":\""+provider+"\",\"providers\":[\"apple\",\"google\"],\"lastSyncAt\":0,\"error\":\"\"}");
   void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
   void Result(string name,bool ok,string detail="")=>Note($"RESULT friends {name}: {(ok?"PASS":"FAIL")} {detail}");
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   if(!hud){Note("friends: no HUD");yield break;}
   // What the Amigos window shows, from its first card.
   string Phase(){
    // (JsonUtility fills absent fields: an "empty" input has no id, "no buttons" is an empty list)
    var c=hud.QaPageCard;if(c==null)return CheckoutDesktopHUD.BoardOpen?"content":"none";
    if(c.input!=null&&c.input.id=="name")return "profile";
    var buttons=(c.buttons??new DesktopButton[0]).Where(b=>b!=null&&!string.IsNullOrEmpty(b.label)).ToArray();
    if(buttons.Any(b=>b.action=="cloudSignIn"))return "signed-out";
    if(buttons.Any(b=>b.action=="socialRefresh"))return "error";
    return buttons.Length==0&&string.IsNullOrEmpty(c.input?.id)?"loading":"content";
   }

   Note("friends: "+CheckoutQaGameView.Set(2778,1284)+" handheld="+CheckoutScreen.Handheld+" qa="+CheckoutStartMenu.QaMode);
   if(!CheckoutStartMenu.QaMode){Note("friends: not on the QA copy, stopping");yield break;}
   for(float t=0;t<15&&!CheckoutSocial.Active;t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   var langBefore=CheckoutI18n.Language;Lang("pt");
   yield return new WaitForSecondsRealtime(4f);
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();
   // The QA copy: tutorial skipped, a day's result collected and a free day running (views arrive all the time, like
   // a phone mid-game).
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1.5f);
   Act("startDay","[\"livre\"]");yield return new WaitForSecondsRealtime(3f);
   for(int i=0;i<3&&hud.CoachQa().isTip;i++){Act("dismissOnboardingTip","[]");yield return new WaitForSecondsRealtime(.5f);}
   // Signed out, with Apple and Google offered; the fake server answers 1.5 s late (a phone network).
   Cloud("signed-out");Mock("signed-out");Mock("latency","2600");
   Route("");yield return new WaitForSecondsRealtime(2f);

   RecStart("Logs/ff_demo.mjpg");
   var marks=new List<string>();void Mark(string what){marks.Add($"{RecAt:0.0}s {what}");Note($"mark {RecAt:0.0}s {what}");}
   try{
    // a. Amigos signed out
    yield return Frames(1f);
    Mark("open Amigos signed out");Route("!amigos");yield return Frames(2.2f);
    Result("Amigos signed out shows the sign-in card",Phase()=="signed-out",Phase());
    yield return Still("1_signed_out");
    Mark("sign in with Apple (simulated)");Cloud("signing-in","apple");yield return Frames(1.2f);
    // The login completes with the window still open: CheckoutCloud has the session, CheckoutSocial sends the status;
    // on the fake server the account signs in. Nobody touches the window from here.
    Cloud("synced","apple");Mock("signed-out","off");
    float t0=Time.realtimeSinceStartup;bool sawLoading=false;string last="";
    for(int i=0;i<30*12;i++){
     var p=Phase();if(p!=last){Mark("Amigos: "+p);last=p;}
     if(p=="loading"&&!sawLoading){sawLoading=true;yield return Still("2_loading");}
     if(p=="profile"||p=="error")break;
     yield return null;
    }
    Result("sign-in with Amigos open loads the friends screen by itself (no reopen)",Phase()=="profile",$"loading shown {sawLoading}, then '{Phase()}' {Time.realtimeSinceStartup-t0:0.0}s after the login");
    yield return Frames(1.5f);
    yield return Still("3_first_time_setup");
    string fold=Fold();Note("friends: profile fold "+fold);
    // (every face Unity can draw: CheckoutSocial.AvatarCount, 8 shopper portraits in this project today, at most 12)
    Result("every face of the picker sits whole above the fold on the phone",fold.Contains("cut 0, below 0")&&!fold.StartsWith("whole 0"),fold+$", faces {CheckoutSocial.AvatarCount()}");

    // b. the face list scrolled (if it scrolls at all) with views arriving: no cut while scrolled
    var (cut0,_)=hud.QaBoardCut();Note($"friends: profile view cut at the top {cut0:0}");
    Mark("scroll the face list");
    float worst=0;int seen=0;
    for(int i=0;i<=40;i++){hud.QaBoardScroll(Mathf.Sin(i/40f*Mathf.PI)*.9f);yield return null;var (c,s)=hud.QaBoardCut();if(s>1){seen++;worst=Mathf.Max(worst,c);}}
    yield return Frames(.5f);
    hud.QaBoardScroll(0);yield return Frames(.8f);
    Note($"friends: profile scroll frames {seen} scrolled, worst cut {worst:0}");
    // Pick a face with a tap on its tile (a face picker: the tap picks), type the name, Salvar: the Amigos window proper.
    Mark("tap a face, type the name, Salvar");
    var faceTile=hud.GetComponentsInChildren<MonoBehaviour>(false).FirstOrDefault(m=>m.GetType().Name=="BoardTileUi"&&(m.GetType().GetField("Id")?.GetValue(m) as string)=="shopper-4");
    if(faceTile)ExecuteEvents.Execute(faceTile.gameObject,new PointerEventData(EventSystem.current){button=PointerEventData.InputButton.Left},ExecuteEvents.pointerClickHandler);
    else Act("socialPickAvatar","[\"shopper-4\"]");
    yield return Frames(1.2f);
    Note($"friends: face tile tapped {(bool)faceTile}");
    var field=hud.GetComponentsInChildren<TMPro.TMP_InputField>(false).FirstOrDefault();
    if(field){foreach(var ch in "Mercadinho do Lucas"){field.text+=ch;yield return Frames(.05f);}}
    yield return Frames(.6f);
    yield return Still("3b_face_picked_name_typed");
    var save=hud.GetComponentsInChildren<CheckoutDesktopButton>(false).FirstOrDefault(b=>b.Data!=null&&b.Data.action=="socialSaveProfile");
    if(save&&field)save.Clicked?.Invoke(save);else Act("socialSaveProfile","[\"Mercadinho do Lucas\",\"shopper-4\"]");
    yield return Frames(2.4f);
    Result("profile saved, Amigos shows the friends",Phase()=="content",Phase());

    // c. windows over the world with no dark backdrop
    Mark("Loja");Route("!loja");yield return Frames(2.4f);yield return Still("4_loja");
    // a long board (Missões) scrolled with views arriving (the band could show on any board): no cut while scrolled
    Mark("Missões, scrolled");Route("!missions");yield return Frames(1.6f);
    {var (c0,_)=hud.QaBoardCut();Note($"friends: missions view cut at the top {c0:0}");
     float w2=0;int s2=0;for(int i=0;i<=75;i++){hud.QaBoardScroll(Mathf.Sin(i/75f*Mathf.PI)*.85f);yield return null;var (c,s)=hud.QaBoardCut();if(s>1){s2++;w2=Mathf.Max(w2,c);}if(i==37)yield return Still("4b_missions_scrolled");}
     hud.QaBoardScroll(0);yield return Frames(.6f);
     worst=Mathf.Max(worst,w2);seen+=s2;Note($"friends: missions scroll frames {s2} scrolled, worst cut {w2:0}");}
    Result("no band while a board is scrolled (the tile view keeps its full height)",seen>0&&worst<.5f,$"{seen} scrolled frames, worst cut {worst:0}");
    Mark("Amigos");Route("!amigos");yield return Frames(2.4f);yield return Still("5_amigos");
    Mark("Ranking");Route("!ranking");yield return Frames(2.6f);yield return Still("6_ranking");
    Route("");yield return Frames(.8f);
    Mark("Opções (a dialog)");CheckoutSettings.Show();yield return Frames(2.2f);yield return Still("7_opcoes");
    CheckoutSettings.Hide();yield return Frames(.8f);
    Mark("level-up card");
    hud.QaCelebrate(new DesktopLevelUp{key="qa-level",headline="SUBIU DE NÍVEL!",subtitle=CheckoutI18n.T("Novos produtos e melhorias liberados"),empty=CheckoutI18n.T("Nada novo neste nível."),next="",from=4,to=5,total=0,xp=120,xpGoal=900,groups=new DesktopLevelUpGroup[0]},null);
    yield return Frames(3.4f);yield return Still("8_level_up");
    hud.QaReleaseCelebrations();yield return Frames(.6f);
    Mark("conquest card");
    hud.QaCelebrate(null,new DesktopCelebration{key="qa-conquest",id="qa-conquest",kind="sector",headline=CheckoutI18n.T("NOVO SETOR!"),title=CheckoutI18n.T("Padaria"),subtitle=CheckoutI18n.T("Pães frescos todo dia: os clientes compram mais."),icon="Icons/shelf",tint="3F9E52",button="",route="",lotId="",chips=new DesktopCelebrationChip[0],stats=new DesktopCelebrationStat[0],products=new DesktopCelebrationProduct[0],reveal=null});
    yield return Frames(3f);yield return Still("9_conquest");
    hud.QaReleaseCelebrations();yield return Frames(1f);
   } finally {RecStop();}
   Note("friends: video marks | "+string.Join(" | ",marks));

   // b'. The old behaviour next to the fix, on the profile page (four columns of faces, the cut at any scroll position).
   Route("!amigos:perfil");yield return new WaitForSecondsRealtime(2f);
   CheckoutDesktopHUD.QaLegacySnap=true;yield return new WaitForSecondsRealtime(1.5f);
   hud.QaBoardScroll(.45f);yield return new WaitForSecondsRealtime(2.5f);
   var (oldCut,oldScroll)=hud.QaBoardCut();Note($"friends: TestFlight 1.0 (11) behaviour, scrolled {oldScroll:0}: view cut {oldCut:0} above the footer ({Fold()})");
   yield return Still("b_band_before");
   CheckoutDesktopHUD.QaLegacySnap=false;hud.QaBoardScroll(0);yield return new WaitForSecondsRealtime(2f);
   hud.QaBoardScroll(.45f);yield return new WaitForSecondsRealtime(2.5f);
   var (newCut,newScroll)=hud.QaBoardCut();Note($"friends: fixed, scrolled {newScroll:0}: view cut {newCut:0} ({Fold()})");
   yield return Still("b_band_after");
   Result("the band of 1.0 (11) reproduced with the old rule and gone with the fix",oldCut>.5f&&newCut<.5f,$"old cut {oldCut:0} at scroll {oldScroll:0}, new cut {newCut:0} at scroll {newScroll:0}");
   Route("");yield return new WaitForSecondsRealtime(1f);

   // d. A profile call that never answers: the error card with "Tentar de novo" within the 20 s limit, then the retry.
   Mock("latency","0");Mock("signed-out");yield return new WaitForSecondsRealtime(.6f);
   Route("!amigos");yield return new WaitForSecondsRealtime(1f);
   Mock("hang","/v1/social/me");Mock("signed-out","off");
   float h0=Time.realtimeSinceStartup;yield return new WaitForSecondsRealtime(1f);
   string mid=Phase();
   for(float t=0;t<30&&Phase()!="error";t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   float took=Time.realtimeSinceStartup-h0;
   Result("a call that never answers ends in the error card (Tentar de novo), not endless loading",mid=="loading"&&Phase()=="error"&&took<24,$"'{mid}' then '{Phase()}' after {took:0.0}s");
   yield return Still("d_error_retry");
   Act("socialRefresh","[]");
   for(float t=0;t<8&&Phase()!="content"&&Phase()!="profile";t+=.5f)yield return new WaitForSecondsRealtime(.5f);
   Result("Tentar de novo loads the friends",Phase()=="content"||Phase()=="profile",Phase());
   Route("");Cloud("unavailable");Lang(langBefore);
   yield return new WaitForSecondsRealtime(1f);
  }

  // The tutorial's spotlight on a brand-new QA save: still dimmed around the highlight.
  IEnumerator OnboardingSpot(string request){
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   Note("spot: "+CheckoutQaGameView.Set(2778,1284)+" fresh="+CheckoutStartMenu.QaFresh);
   if(!CheckoutStartMenu.QaFresh||!hud){Note("spot: not on a fresh QA save, stopping");yield break;}
   void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
   void Result(string name,bool ok,string detail="")=>Note($"RESULT spot {name}: {(ok?"PASS":"FAIL")} {detail}");
   var langBefore=CheckoutI18n.Language;Lang("pt");
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();
   // until the guide points at something (a hole in the dim)
   CheckoutDesktopHUD.CoachQaInfo q=null;
   for(float t=0;t<40;t+=.5f){q=hud.CoachQa();if(q.dims&&q.hole.width>0)break;
    // the guide's first cards only ask for "Continuar": tap it like a finger (onboardingNext)
    if(q.card&&!q.found&&!string.IsNullOrEmpty(q.button)&&t>3)CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-spot-"+t+"\",\"action\":\"onboardingNext\",\"args\":[]}");
    yield return new WaitForSecondsRealtime(.5f);}
   Note($"spot: step '{q?.key}' dims {q?.dims} hole {q?.hole}");
   RecStart("Logs/ff_spot.mjpg");
   try{yield return Frames(4.5f);yield return Still("s_spotlight");}finally{RecStop();}
   q=hud.CoachQa();
   Result("the tutorial's spotlight still dims around the highlight",q.dims&&q.hole.width>0,$"step '{q.key}' dims {q.dims} hole {q.hole}");
   Lang(langBefore);
  }
 }
}
