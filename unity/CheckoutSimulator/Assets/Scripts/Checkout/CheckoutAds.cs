using System;
using System.Collections.Concurrent;
using UnityEngine;
using UnityEngine.UI;
#if CHECKOUT_ADMOB
using GoogleMobileAds.Api;
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
  string showingId;bool earned;

  [Serializable] class ShowMessage{public string id;}
  [Serializable] class StatusMessage{public string kind="ad",status="",@event="",id="";}

  public static void Attach(CheckoutDesktopHost owner){
   if(Active||!owner)return;
   var ads=owner.gameObject.AddComponent<CheckoutAds>();ads.host=owner;Active=ads;
   ads.Begin();
  }

  void Report(string status,string evt="",string id="")=>host.Send(JsonUtility.ToJson(new StatusMessage{status=status,@event=evt,id=id??""}));

  /// <summary>Host line <c>ad-show</c>: play a video for this id.</summary>
  public void Show(string json){
   var id=JsonUtility.FromJson<ShowMessage>(json)?.id;
   if(string.IsNullOrEmpty(id)||!string.IsNullOrEmpty(showingId))return;
   showingId=id;earned=false;
   if(!ShowVideo()){Report(Ready?"ready":"unavailable","failed",id);showingId=null;}
  }

  // The video ended: watched to the end pays (through the host), otherwise nothing.
  void Finished(){
   var id=showingId;showingId=null;if(string.IsNullOrEmpty(id))return;
   if(earned)host.Action("claimRewardedAd","["+CheckoutIapFlow.Quote(id)+"]","",(ok,reason)=>{if(!ok)Debug.LogWarning("CHECKOUT_ADS reward refused: "+reason);});
   else Report(Ready?"ready":"loading","closed",id);
   Load();
  }

  void Update(){while(main.TryDequeue(out var action))action();}
  void OnDestroy(){if(Active==this)Active=null;}

#if CHECKOUT_ADMOB && (UNITY_IOS || UNITY_ANDROID) && !UNITY_EDITOR
  // Google's test units until the real ones exist in AdMob (Assets › Google Mobile Ads › Settings holds the app id).
#if UNITY_IOS
  const string Unit="ca-app-pub-3940256099942544/1712485313";
#else
  const string Unit="ca-app-pub-3940256099942544/5224354917";
#endif
  RewardedAd ad;bool loading;
  bool Ready=>ad!=null&&ad.CanShowAd();
  void Begin(){
   Report("loading");
   MobileAds.Initialize(_=>main.Enqueue(Load));
  }
  void Load(){
   if(loading||Ready)return;loading=true;
   RewardedAd.Load(Unit,new AdRequest(),(loaded,error)=>main.Enqueue(()=>{
    loading=false;
    if(error!=null||loaded==null){Debug.LogWarning("CHECKOUT_ADS no video: "+error?.GetMessage());Report("unavailable");Invoke(nameof(Load),60);return;}
    ad?.Destroy();ad=loaded;
    ad.OnAdFullScreenContentClosed+=()=>main.Enqueue(Finished);
    ad.OnAdFullScreenContentFailed+=e=>main.Enqueue(()=>{Debug.LogWarning("CHECKOUT_ADS video failed: "+e?.GetMessage());earned=false;Finished();});
    Report("ready");
   }));
  }
  bool ShowVideo(){
   if(!Ready)return false;
   var current=ad;ad=null;
   current.Show(_=>main.Enqueue(()=>earned=true));
   return true;
  }
#else
  // Editor: a test video. Elsewhere (desktop builds, phones without the AdMob plugin): none.
  bool Ready=>Application.isEditor;
  void Begin(){Report(Ready?"ready":"unavailable");}
  void Load(){}
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
