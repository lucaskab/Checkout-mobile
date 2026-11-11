using System;
using System.Collections;
using UnityEngine;
using UnityEngine.Networking;

namespace Checkout {
 // The game and its store page (Lucas 10/11):
 //  - Rating: host line {"kind":"store-review"} (the arrival of an expansion, desktop/host.ts + src/services/app-prompts.ts)
 //    opens the system's own review sheet: SKStoreReviewController on the iPhone (Unity's Device.RequestStoreReview),
 //    Google Play's In-App Review on Android (Plugins/Android/CheckoutAppStore.java). The system decides whether it
 //    actually shows (Apple at most 3 times a year, Google its own quota); nothing is reported back, by design.
 //  - New version: once a session, 20 s after the game starts, the store is asked whether a newer version is out —
 //    the App Store lookup on the iPhone, Play's in-app updates API on Android — and the answer goes to the host
 //    ({"kind":"update"}, desktop/updates.ts), which offers "Atualizar agora" / "Agora não". "Atualizar agora" opens
 //    the store page (CheckoutLinks "store").
 // Editor and desktop builds: the review is only logged; the update check is skipped unless Logs/fake_update.txt
 // holds a version (QA).
 public class CheckoutAppStore:MonoBehaviour {
  public const string AppleId="6826304188";
  public const string AndroidPackage="com.lucasfurini.checkout";
  public static CheckoutAppStore Active {get;private set;}
  CheckoutDesktopHost host;

  [Serializable] class UpdateMessage{public string kind="update",latest="",current="";public bool available;}
  [Serializable] class LookupResult{public string version;}
  [Serializable] class Lookup{public int resultCount;public LookupResult[] results;}

  public static void Attach(CheckoutDesktopHost owner){
   if(Active||!owner)return;
   var store=owner.gameObject.AddComponent<CheckoutAppStore>();store.host=owner;Active=store;
   store.StartCoroutine(store.CheckLater());
  }
  void OnDestroy(){if(Active==this)Active=null;}

  /// <summary>Host line store-review: the system's review sheet.</summary>
  public void RequestReview(){
#if UNITY_IOS && !UNITY_EDITOR
   try{UnityEngine.iOS.Device.RequestStoreReview();}catch(Exception ex){Debug.LogWarning("CHECKOUT_REVIEW "+ex.Message);}
#elif UNITY_ANDROID && !UNITY_EDITOR
   try{
    using var player=new AndroidJavaClass("com.unity3d.player.UnityPlayer");
    using var activity=player.GetStatic<AndroidJavaObject>("currentActivity");
    using var plugin=new AndroidJavaClass("com.checkout.store.CheckoutAppStore");
    plugin.CallStatic("requestReview",activity);
   }catch(Exception ex){Debug.LogWarning("CHECKOUT_REVIEW "+ex.Message);}
#endif
   Debug.Log("CHECKOUT_REVIEW requested");
  }

  /// <summary>The game's page in this device's store.</summary>
  public static string StoreUrl(){
#if UNITY_IOS && !UNITY_EDITOR
   return "itms-apps://apps.apple.com/app/id"+AppleId;
#elif UNITY_ANDROID && !UNITY_EDITOR
   return "market://details?id="+AndroidPackage;
#else
   return Application.platform==RuntimePlatform.OSXEditor||Application.platform==RuntimePlatform.OSXPlayer
    ?"https://apps.apple.com/app/id"+AppleId:"https://play.google.com/store/apps/details?id="+AndroidPackage;
#endif
  }

  public static void OpenStore(){
   var url=StoreUrl();Debug.Log("CHECKOUT_UPDATE open "+url);
   Application.OpenURL(url);
  }

  IEnumerator CheckLater(){
   yield return new WaitForSecondsRealtime(20f);
   if(Application.isEditor||!(Application.platform==RuntimePlatform.IPhonePlayer||Application.platform==RuntimePlatform.Android)){
    // QA: Logs/fake_update.txt = "1.0.9" pretends the store has that version.
    string fake=null;try{if(System.IO.File.Exists("Logs/fake_update.txt"))fake=System.IO.File.ReadAllText("Logs/fake_update.txt").Trim();}catch{}
    if(!string.IsNullOrEmpty(fake))Report(fake,false);
    yield break;
   }
#if UNITY_IOS
   // The App Store's public lookup (the store's own version name; refreshed by Apple within hours of a release).
   var url="https://itunes.apple.com/lookup?bundleId="+Application.identifier+"&t="+DateTime.UtcNow.Ticks;
   using var req=UnityWebRequest.Get(url);req.timeout=15;
   yield return req.SendWebRequest();
   if(req.result!=UnityWebRequest.Result.Success){Debug.Log("CHECKOUT_UPDATE lookup failed: "+req.error);yield break;}
   Lookup data=null;try{data=JsonUtility.FromJson<Lookup>(req.downloadHandler.text);}catch{}
   var latest=data!=null&&data.resultCount>0&&data.results!=null&&data.results.Length>0?data.results[0].version:null;
   Debug.Log("CHECKOUT_UPDATE store "+latest+" here "+Application.version);
   if(!string.IsNullOrEmpty(latest))Report(latest,false);
#elif UNITY_ANDROID
   try{
    using var player=new AndroidJavaClass("com.unity3d.player.UnityPlayer");
    using var activity=player.GetStatic<AndroidJavaObject>("currentActivity");
    using var plugin=new AndroidJavaClass("com.checkout.store.CheckoutAppStore");
    plugin.CallStatic("checkUpdate",activity,gameObject.name);
   }catch(Exception ex){Debug.LogWarning("CHECKOUT_UPDATE "+ex.Message);}
#endif
  }

  /// <summary>Called by CheckoutAppStore.java (UnitySendMessage): the store's version code when an update is available, "" when not.</summary>
  public void OnUpdateInfo(string code){
   Debug.Log("CHECKOUT_UPDATE play code '"+code+"'");
   if(!string.IsNullOrEmpty(code))Report("code "+code,true);
  }

  /// <summary>QA: pretend the store has `version` now.</summary>
  public void QaReport(string version)=>Report(version,false);

  void Report(string latest,bool available){
   Debug.Log("CHECKOUT_UPDATE report "+latest+" (here "+Application.version+")");
   host?.Send(JsonUtility.ToJson(new UpdateMessage{latest=latest,current=Application.version,available=available}));
  }
 }
}
