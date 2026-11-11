using System;
using System.Collections.Concurrent;
using UnityEngine;
using UnityEngine.UI;
#if CHECKOUT_ADMOB
using GoogleMobileAds.Api;
using GoogleMobileAds.Ump.Api;
#endif

namespace Checkout {
 /// <summary>
 /// Rewarded videos (Lucas 12/10): the player chooses to watch a short video for a few diamonds (rules and amounts in
 /// src/services/rewarded-ads.ts; never forced, no interstitials).
 /// - Phone builds with the Google Mobile Ads plugin (define CHECKOUT_ADMOB, set by CheckoutAdsDefine when the plugin is
 ///   installed): Google AdMob rewarded ads.
 /// - The Editor: a 5-second test video drawn here, to try the whole flow without an ad network.
 /// - Desktop builds (and phones without the plugin): no videos; the store says so.
 /// The host asks for a video with an id (<c>ad-show</c>); a video watched to the end is reported with that id
 /// (HUD action claimRewardedAd, which the host pays once); closed early or failed → <c>{kind:"ad",event}</c>.
 /// </summary>
 public class CheckoutAds:MonoBehaviour {
  public static CheckoutAds Active {get;private set;}
  CheckoutDesktopHost host;
  // Ad SDK callbacks may come from another thread: they are run on the next Update.
  readonly ConcurrentQueue<Action> main=new ConcurrentQueue<Action>();
  string showingId;bool earned;float showingAt;

  [Serializable] class ShowMessage{public string id;}
  [Serializable] class StatusMessage{public string kind="ad",status="",@event="",id="";public bool privacy;}

  public static void Attach(CheckoutDesktopHost owner){
   if(Active||!owner)return;
   var ads=owner.gameObject.AddComponent<CheckoutAds>();ads.host=owner;Active=ads;
   ads.Begin();
  }

  void Report(string status,string evt="",string id="")=>host.Send(JsonUtility.ToJson(new StatusMessage{status=status,@event=evt,id=id??"",privacy=PrivacyRequired}));

  /// <summary>Host line <c>ad-show</c>: play a video for this id.</summary>
  public void Show(string json){
   var id=JsonUtility.FromJson<ShowMessage>(json)?.id;
   // One at a time; a video that never reported its end is given up after 150 s (the host gives up at 120 s).
   if(string.IsNullOrEmpty(id)||(!string.IsNullOrEmpty(showingId)&&Time.realtimeSinceStartup-showingAt<150f))return;
   showingId=id;showingAt=Time.realtimeSinceStartup;earned=false;
   if(ShowVideo())CheckoutAudio.HoldMusic(true); // the game's music waits while the video plays
   // None loaded yet (phones): QueueShow loads one and opens it as soon as it arrives, or reports "failed".
   else if(!QueueShow()){Report(Ready?"ready":"unavailable","failed",id);showingId=null;}
  }

  // The video ended: watched to the end pays (through the host), otherwise nothing.
  void Finished(){
   CheckoutAudio.HoldMusic(false);
   var id=showingId;showingId=null;if(string.IsNullOrEmpty(id))return;
   if(earned)CheckoutFirebase.AdWatched(id);
   if(earned){
    host.Action("claimRewardedAd","["+CheckoutIapFlow.Quote(id)+"]","",(ok,reason)=>{if(!ok)Debug.LogWarning("CHECKOUT_ADS reward refused: "+reason);});
    Report(Ready?"ready":"loading"); // the shown video is used up: the host must not think one is still ready
   }
   else Report(Ready?"ready":"loading","closed",id);
   Load();
  }

  void Update(){while(main.TryDequeue(out var action))action();}
  void OnDestroy(){if(Active==this)Active=null;}

#if CHECKOUT_ADMOB && (UNITY_IOS || UNITY_ANDROID) && !UNITY_EDITOR
  // The game's rewarded unit in AdMob (app id: Assets › Google Mobile Ads › Settings). Development builds keep Google's
  // test unit: real ads clicked by the developer count as invalid traffic and can get the AdMob account suspended.
#if UNITY_IOS
  // AdMob app "Checkout (iOS)" ca-app-pub-6635161191872845~9063259268 (23/10), rewarded unit "Diamantes gratis".
  static string Unit=>Debug.isDebugBuild?"ca-app-pub-3940256099942544/1712485313":"ca-app-pub-6635161191872845/9135411459";
#else
  static string Unit=>Debug.isDebugBuild?"ca-app-pub-3940256099942544/5224354917":"ca-app-pub-6635161191872845/4528327896";
#endif
  RewardedAd ad;bool loading,started,consenting,waitingToShow;
  float loadAt;int loadFailures,consentFailures;
  // "Assistir" pressed with no video loaded: how long to wait for one before answering "failed".
  const float WaitForVideoSeconds=12f;
  bool Ready=>ad!=null&&ad.CanShowAd();
  static bool PrivacyRequired=>ConsentInformation.PrivacyOptionsRequirementStatus==PrivacyOptionsRequirementStatus.Required;
  void Begin(){
   if(consenting)return;consenting=true;
   Report(Ready?"ready":"loading");
   // Last session's answer may already allow ads: start right away while the consent info refreshes.
   if(ConsentInformation.CanRequestAds())StartAds();
   ConsentInformation.Update(new ConsentRequestParameters(),updateError=>main.Enqueue(()=>{
    if(updateError!=null)Debug.LogWarning("CHECKOUT_ADS consent info: "+updateError.Message);
    ConsentForm.LoadAndShowConsentFormIfRequired(formError=>main.Enqueue(()=>{
     consenting=false;
     if(formError!=null)Debug.LogWarning("CHECKOUT_ADS consent form: "+formError.Message);
     if(ConsentInformation.CanRequestAds()){consentFailures=0;StartAds();return;}
     if(started)return;
     // No answer that allows ads yet (offline at launch, the form did not load...): ask again later (30 s, 1 min…
     // up to 5 min, and whenever the player presses "Assistir") instead of leaving the videos off for the session.
     consentFailures++;
     var wait=Mathf.Min(300f,30f*Mathf.Pow(2,Mathf.Min(consentFailures,5)-1));
     Debug.LogWarning("CHECKOUT_ADS ads not allowed yet (consent "+ConsentInformation.ConsentStatus+"), asking again in "+wait+" s");
     Report("unavailable");
     if(waitingToShow)GiveUpWaiting();
     CancelInvoke(nameof(Begin));Invoke(nameof(Begin),wait);
    }));
   }));
  }
  void StartAds(){
   if(started){Report(Ready?"ready":"loading");Load();return;}
   started=true;
   MobileAds.Initialize(_=>main.Enqueue(Load));
  }
  /// <summary>Host line <c>ad-privacy</c>: Google's form to change the ads consent.</summary>
  public void ShowPrivacy()=>ConsentForm.ShowPrivacyOptionsForm(error=>main.Enqueue(()=>{
   if(error!=null)Debug.LogWarning("CHECKOUT_ADS privacy form: "+error.Message);
   if(ConsentInformation.CanRequestAds())StartAds();else Report("unavailable");
  }));
  void Load(){
   // A load that never answered (60 s) does not block the next one.
   if(!started||Ready||(loading&&Time.realtimeSinceStartup-loadAt<60f))return;
   loading=true;loadAt=Time.realtimeSinceStartup;
   RewardedAd.Load(Unit,new AdRequest(),(loaded,error)=>main.Enqueue(()=>{
    loading=false;
    if(error!=null||loaded==null){
     // Keep trying (5 s, 10 s, 20 s… up to 2 min, and right away when the player presses "Assistir"): one failed
     // load (no fill, no network) must never leave the videos off.
     loadFailures++;
     var wait=Mathf.Min(120f,5f*Mathf.Pow(2,Mathf.Min(loadFailures,6)-1));
     Debug.LogWarning("CHECKOUT_ADS no video (code "+error?.GetCode()+", "+error?.GetDomain()+"): "+error?.GetMessage()+" · failure "+loadFailures+", next try in "+wait+" s");
     if(loadFailures<=3)CheckoutFirebase.Log("ad_load_failed",("code",error?.GetCode()??-1),("domain",error?.GetDomain()??""),("failure",loadFailures));
     Report("unavailable");
     if(waitingToShow)GiveUpWaiting();
     CancelInvoke(nameof(Load));Invoke(nameof(Load),wait);
     return;
    }
    loadFailures=0;
    ad?.Destroy();ad=loaded;
    ad.OnAdFullScreenContentClosed+=()=>main.Enqueue(Finished);
    ad.OnAdFullScreenContentFailed+=e=>main.Enqueue(()=>{Debug.LogWarning("CHECKOUT_ADS video failed: "+e?.GetMessage());earned=false;Finished();});
    Report("ready");
    // The player pressed "Assistir" while it loaded: open it now.
    if(waitingToShow){
     if(ShowVideo()){waitingToShow=false;CancelInvoke(nameof(WaitTimedOut));CheckoutAudio.HoldMusic(true);}
     else GiveUpWaiting();
    }
   }));
  }
  // "Assistir" with no video loaded yet: load one now (skipping the back-off wait) and open it as soon as it
  // arrives, or answer "failed" after a few seconds, instead of a dead button (Lucas 08/11).
  bool QueueShow(){
   waitingToShow=true;
   CancelInvoke(nameof(WaitTimedOut));Invoke(nameof(WaitTimedOut),WaitForVideoSeconds);
   if(!started)Begin(); // ads not allowed yet (no consent answer, offline at launch): ask again now
   else{CancelInvoke(nameof(Load));Load();}
   Report(Ready?"ready":"loading");
   return true;
  }
  void WaitTimedOut(){if(!waitingToShow)return;Debug.LogWarning("CHECKOUT_ADS no video arrived in "+WaitForVideoSeconds+" s");GiveUpWaiting();}
  void GiveUpWaiting(){
   waitingToShow=false;CancelInvoke(nameof(WaitTimedOut));
   var id=showingId;showingId=null;if(string.IsNullOrEmpty(id))return;
   Report(Ready?"ready":loading?"loading":"unavailable","failed",id);
  }
  // Back in the game (after a call, another app...): try again at once if no video is loaded.
  void OnApplicationPause(bool paused){if(!paused&&started&&!Ready&&string.IsNullOrEmpty(showingId)){CancelInvoke(nameof(Load));Load();}}
  bool ShowVideo(){
   if(!Ready)return false;
   var current=ad;ad=null;
   current.Show(_=>main.Enqueue(()=>earned=true));
   return true;
  }
#else
  // Editor: a test video. Elsewhere (desktop builds, phones without the AdMob plugin): none.
  bool Ready=>Application.isEditor;
  static bool PrivacyRequired=>false;
  public void ShowPrivacy(){}
  void Begin(){Report(Ready?"ready":"unavailable");}
  void Load(){}
  bool QueueShow()=>false;
  bool ShowVideo(){if(!Ready)return false;TestVideo();return true;}

  // A full-screen "ad" with a 5-second countdown: Close at any time = no reward; wait to the end = reward.
  void TestVideo(){
   var go=new GameObject("Test rewarded video",typeof(RectTransform));
   var canvas=go.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=500;
   go.AddComponent<CanvasScaler>().uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;go.AddComponent<GraphicRaycaster>();
   var back=new GameObject("Back",typeof(RectTransform)).AddComponent<Image>();back.transform.SetParent(go.transform,false);back.color=new Color(.05f,.06f,.1f,.96f);
   var br=back.rectTransform;br.anchorMin=Vector2.zero;br.anchorMax=Vector2.one;br.offsetMin=br.offsetMax=Vector2.zero;
   Text Label(string name,Vector2 at,int size){var t=new GameObject(name,typeof(RectTransform)).AddComponent<Text>();t.transform.SetParent(back.transform,false);t.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");t.fontSize=size;t.alignment=TextAnchor.MiddleCenter;t.color=Color.white;var r=t.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);r.sizeDelta=new Vector2(1400,120);r.anchoredPosition=at;return t;}
   Label("Title",new Vector2(0,80),48).text="Anúncio de teste";
   var count=Label("Count",new Vector2(0,-20),36);
   var close=new GameObject("Close",typeof(RectTransform)).AddComponent<Image>();close.transform.SetParent(back.transform,false);close.color=new Color(1,1,1,.15f);
   var cr=close.rectTransform;cr.anchorMin=cr.anchorMax=Vector2.one;cr.pivot=Vector2.one;cr.anchoredPosition=new Vector2(-30,-30);cr.sizeDelta=new Vector2(90,90);
   var x=new GameObject("X",typeof(RectTransform)).AddComponent<Text>();x.transform.SetParent(close.transform,false);x.font=Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");x.fontSize=44;x.alignment=TextAnchor.MiddleCenter;x.color=Color.white;x.text="X";
   var xr=x.rectTransform;xr.anchorMin=Vector2.zero;xr.anchorMax=Vector2.one;xr.offsetMin=xr.offsetMax=Vector2.zero;
   float left=5;
   close.gameObject.AddComponent<Button>().onClick.AddListener(()=>{Destroy(go);Finished();});
   // A big "Fechar" in the middle too (the corner X can sit under other windows on a desktop).
   var done=new GameObject("Done",typeof(RectTransform)).AddComponent<Image>();done.transform.SetParent(back.transform,false);done.color=new Color(.36f,.65f,.22f,1);
   var dr=done.rectTransform;dr.anchorMin=dr.anchorMax=new Vector2(.5f,.5f);dr.sizeDelta=new Vector2(320,90);dr.anchoredPosition=new Vector2(0,-140);
   var dt=Label("DoneLabel",Vector2.zero,36);dt.transform.SetParent(done.transform,false);dt.rectTransform.anchoredPosition=Vector2.zero;dt.rectTransform.sizeDelta=new Vector2(320,90);dt.text="Fechar";
   done.gameObject.AddComponent<Button>().onClick.AddListener(()=>{Destroy(go);Finished();});
   void Tick(){
    if(!go)return;left-=.1f;
    if(left<=0){earned=true;count.text="Recompensa garantida! Feche o vídeo.";return;}
    count.text="Recompensa em "+Mathf.CeilToInt(left)+" s";Invoke(nameof(TickProxy),.1f);
   }
   tick=Tick;tick();
  }
  Action tick;void TickProxy()=>tick?.Invoke();
#endif
 }
}
