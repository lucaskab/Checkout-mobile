using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using UnityEngine;
using UnityEngine.Networking;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout {
 /// <summary>
 /// Social v1 on the Unity side (docs/social-api.md, desktop/social.ts). Unity owns the network and the session: the
 /// host asks for each call (<c>social-call</c>) and gets the answer back (<c>social-reply</c>) without ever seeing the
 /// token. Also here: the inbox clock (start, after a login, every 5 min), writing the save to disk before an ack,
 /// the toasts, the native share sheet with a picture of the market, the clipboard, checkout://add/&lt;code&gt; links,
 /// Android's Play Install Referrer, the visit flag (the player's market is frozen meanwhile) and the avatars (portraits
 /// of the game's own shoppers). In the Editor (and QA runs) the host answers the calls itself (desktop/social-mock.ts)
 /// until CHECKOUT_SOCIAL_SERVER=1 points the Editor at the real Worker.
 /// </summary>
 public class CheckoutSocial:MonoBehaviour {
  public static CheckoutSocial Active {get;private set;}
  /// <summary>Visiting a friend's market: commands, layout saves and world taps of the player's market wait.</summary>
  public static bool Visiting {get;private set;}
  public static string VisitName {get;private set;}="";
  /// <summary>QA: the picture the last "Chamar amigo" shared (the share sheet itself is the phone's own window).</summary>
  public static string LastSharePicture {get;private set;}="";
  const float TickEvery=300f;
  CheckoutDesktopHost host;bool mock,statusSent,lastSignedIn;float nextTick=float.MaxValue;
  readonly Queue<string> links=new Queue<string>();

  [Serializable] class Status{public string kind="social";public bool signedIn;public bool mock;public string platform;public bool canShare;public int avatars;}
  [Serializable] class Tick{public string kind="social-tick";public string reason;}
  [Serializable] class CallMessage{public string id,method,path,body;}
  [Serializable] class Reply{public string kind="social-reply";public string id;public long code;public string body;public bool network;}
  [Serializable] class Flushed{public string kind="social-flushed";public string id;}
  [Serializable] class Link{public string kind="social-link";public string code;public string source;}
  [Serializable] class ToastMessage{public string text,icon;public bool ok;}
  [Serializable] class FxMessage{public string fx;public int coins;}
  [Serializable] class ShareMessage{public string url,code,text,name,caption,codeLabel,avatar,stage;}
  [Serializable] class CopyMessage{public string text;}
  [Serializable] class VisitMessage{public bool active;public string friendId,name;}

  public static void Attach(CheckoutDesktopHost owner){
   if(!owner||CheckoutStartMenu.EditMode)return;
   var social=owner.GetComponent<CheckoutSocial>()??owner.gameObject.AddComponent<CheckoutSocial>();
   social.host=owner;social.mock=UseMock;Active=social;
  }
  static bool UseMock=>CheckoutStartMenu.QaMode||(Application.isEditor&&Environment.GetEnvironmentVariable("CHECKOUT_SOCIAL_SERVER")!="1");
  static bool SignedIn=>CheckoutCloud.Active&&CheckoutCloud.Active.HasSession;
  static string Platform=>Application.isEditor?"editor":Application.platform==RuntimePlatform.IPhonePlayer?"ios":Application.platform==RuntimePlatform.Android?"android":"desktop";
  static bool CanShare=>!Application.isEditor&&(Application.platform==RuntimePlatform.IPhonePlayer||Application.platform==RuntimePlatform.Android);

  IEnumerator Start(){
   Application.deepLinkActivated+=OnDeepLink;CheckoutCloud.Changed+=OnCloud;
   if(!string.IsNullOrEmpty(Application.absoluteURL))OnDeepLink(Application.absoluteURL);
   // The host loads the save first (and CheckoutCloud compares it with the cloud).
   yield return new WaitForSecondsRealtime(2.5f);
   lastSignedIn=SignedIn;SendStatus();
   yield return new WaitForSecondsRealtime(2f);
   Send(new Tick{reason="start"});nextTick=Time.unscaledTime+TickEvery;
   if(lastSignedIn)MaybeReferrer();
  }
  void OnDestroy(){Application.deepLinkActivated-=OnDeepLink;CheckoutCloud.Changed-=OnCloud;if(Active==this){Active=null;Visiting=false;}}
  void Update(){if(statusSent&&Time.unscaledTime>=nextTick){nextTick=Time.unscaledTime+TickEvery;Send(new Tick{reason="sync"});}}
  // Signed in or out (Google / Apple): the host learns it; a login fetches the inbox at once (and offers an invite code).
  void OnCloud(){
   if(!statusSent)return;
   bool now=SignedIn;if(now==lastSignedIn)return;
   lastSignedIn=now;SendStatus();
   if(now){Send(new Tick{reason="login"});nextTick=Time.unscaledTime+TickEvery;MaybeReferrer();}
  }
  void SendStatus(){
   Send(new Status{signedIn=SignedIn,mock=mock,platform=Platform,canShare=CanShare,avatars=AvatarCount()});statusSent=true;
   while(links.Count>0)host.Send(links.Dequeue());
  }
  void Send(object message){if(host)host.Send(JsonUtility.ToJson(message));}

  // ---- host lines ----
  public void OnHost(string kind,string line){
   switch(kind){
    case "social-call":{var call=JsonUtility.FromJson<CallMessage>(line);if(call!=null)StartCoroutine(Run(call));break;}
    case "social-flush":{
     // The inbox items are in the save: write it to the phone's disk before the server may forget them.
     var id=JsonUtility.FromJson<Flushed>(line)?.id??"";host.Flush();Send(new Flushed{id=id});break;}
    case "social-toast":{var t=JsonUtility.FromJson<ToastMessage>(line);if(t!=null)host.Hud?.SocialToast(t.text,t.icon,t.ok);break;}
    case "social-copy":{var c=JsonUtility.FromJson<CopyMessage>(line);if(c!=null)GUIUtility.systemCopyBuffer=c.text??"";break;}
    case "social-share":{var s=JsonUtility.FromJson<ShareMessage>(line);if(s!=null)StartCoroutine(Share(s));break;}
    case "social-visit":{var v=JsonUtility.FromJson<VisitMessage>(line);if(v!=null)SetVisiting(v.active,v.name);break;}
    case "social-fx":{var f=JsonUtility.FromJson<FxMessage>(line);if(f!=null)host.Hud?.SocialFx(f.fx,f.coins);break;}
   }
  }

  IEnumerator Run(CallMessage call){
   if(!SignedIn){Send(new Reply{id=call.id,code=401,body="{\"error\":\"signed-out\"}"});yield break;}
   using var request=new UnityWebRequest(CheckoutCloud.ServerUrl+call.path,string.IsNullOrEmpty(call.method)?"GET":call.method);
   if(!string.IsNullOrEmpty(call.body)){request.uploadHandler=new UploadHandlerRaw(Encoding.UTF8.GetBytes(call.body));request.SetRequestHeader("Content-Type","application/json");}
   request.downloadHandler=new DownloadHandlerBuffer();
   request.SetRequestHeader("Authorization","Bearer "+CheckoutCloud.Active.SessionToken);
   request.timeout=40;
   yield return request.SendWebRequest();
   bool network=request.result==UnityWebRequest.Result.ConnectionError||request.responseCode==0;
   // Only the route and the status in the log (the answers may carry names; the token never).
   if(network||request.responseCode>=400)Debug.Log("CHECKOUT_SOCIAL "+call.method+" "+call.path+" -> "+request.responseCode);
   Send(new Reply{id=call.id,code=request.responseCode,body=request.downloadHandler?.text??"",network=network});
  }

  // ---- the visit ----
  void SetVisiting(bool on,string name){
   Visiting=on;VisitName=on?name??"":"";
   // Back home: whatever the friend's floor made the interior remember is dropped (the player's own layout comes
   // with the next snapshot, under the player's own session).
   if(!on)CheckoutInterior.Active?.ClearPending();
   Debug.Log("CHECKOUT_SOCIAL visit "+(on?"started":"ended"));
  }

  // ---- share / links ----
  IEnumerator Share(ShareMessage message){
   // A postcard of the player's own market: the camera framed on the shop (a 3/4 view like the reveal camera), a clear
   // day (no rain, no night) for that one picture, no HUD, padlocks or world markers, and the market's name and friend
   // code laid over by the game's UI (runtime text in the player's language). Everything is put back right after.
   var canvases=FindObjectsByType<Canvas>(FindObjectsSortMode.None).Where(c=>c.enabled&&c.isRootCanvas&&c.renderMode==RenderMode.ScreenSpaceOverlay).ToList();
   var sim=FindAnyObjectByType<MarketDay.MarketSimulation>();var camera=sim?sim.CameraState:(focus:Vector3.zero,zoom:0f);
   var visuals=FindAnyObjectByType<CheckoutEventVisuals>();
   var hidden=PostcardHide();
   try{
    foreach(var c in canvases)c.enabled=false;
    if(visuals)visuals.Photo(true);
    if(sim){var (at,size)=PostcardFrame();sim.FocusCinematic(at,size);}
    var card=PostcardOverlay(message);
    yield return null;yield return null;
    yield return new WaitForEndOfFrame();
    Texture2D grabbed=null;try{grabbed=ScreenCapture.CaptureScreenshotAsTexture();}catch(Exception ex){Debug.LogWarning("CHECKOUT_SOCIAL share picture: "+ex.Message);}
    if(card)Destroy(card);
    postcardShot=grabbed;
   }finally{
    foreach(var r in hidden)if(r)r.enabled=true;
    if(visuals)visuals.Photo(false);
    if(sim&&camera.zoom>0)sim.Focus(camera.focus,camera.zoom);
    foreach(var c in canvases)if(c)c.enabled=true;
   }
   var shot=postcardShot;postcardShot=null;
   // (the screen's alpha is not a picture's: opaque RGB, or the share sheet shows a washed-out postcard)
   if(shot){var opaque=new Texture2D(shot.width,shot.height,TextureFormat.RGB24,false);opaque.SetPixels32(shot.GetPixels32());opaque.Apply();Destroy(shot);shot=opaque;}
   string path=Path.Combine(Application.temporaryCachePath,"checkout-invite.png");
   if(shot){try{File.WriteAllBytes(path,Fit(shot,1280).EncodeToPNG());LastSharePicture=path;}catch(Exception ex){Debug.LogWarning("CHECKOUT_SOCIAL share picture: "+ex.Message);path="";}Destroy(shot);}else path="";
   string text=(message.text??"")+"\n"+(message.url??"");
#if UNITY_IOS && !UNITY_EDITOR
   CheckoutShare_Share(message.text??"",message.url??"",path);
#elif UNITY_ANDROID && !UNITY_EDITOR
   try{
    using var player=new AndroidJavaClass("com.unity3d.player.UnityPlayer");
    using var activity=player.GetStatic<AndroidJavaObject>("currentActivity");
    using var plugin=new AndroidJavaClass("com.checkout.social.CheckoutShare");
    plugin.CallStatic("share",activity,text,path);
   }catch(Exception ex){Debug.LogWarning("CHECKOUT_SOCIAL share: "+ex.Message);GUIUtility.systemCopyBuffer=text;host.Hud?.SocialToast(CheckoutI18n.T("Convite copiado! Cole numa conversa."),"Icons/smartphone",true);}
#else
   // Editor and computers: no share sheet; the invite goes to the clipboard.
   GUIUtility.systemCopyBuffer=text;host.Hud?.SocialToast(CheckoutI18n.T("Convite copiado! Cole numa conversa."),"Icons/smartphone",true);
#endif
  }
  Texture2D postcardShot;

  // The shop (stall, small shop or the market building) and the lot it stands on: centre and camera size so it fills
  // about 60 % of the picture.
  static (Vector3 at,float size) PostcardFrame(){
   var ia=CheckoutInterior.Active;
   Bounds b=ia?new Bounds(new Vector3(ia.FloorRect.center.x,0,ia.FloorRect.center.y),new Vector3(ia.FloorRect.width,2,ia.FloorRect.height)):new Bounds(Vector3.zero,new Vector3(10,2,10));
   if(CheckoutStall.Small)b.Encapsulate(CheckoutStall.Footprint);
   float span=b.size.x+b.size.z;float aspect=Screen.width/(float)Mathf.Max(1,Screen.height);
   float size=Mathf.Max(span*.42f/(2*.6f),span*.8f/(2*.6f*aspect));
   return (b.center+new Vector3(0,0,-.6f),Mathf.Clamp(size,3.6f,30f));
  }

  // Padlocks over the lots, request bubbles, markers and icons in the world: hidden for the picture.
  static List<Renderer> PostcardHide(){
   var list=new List<Renderer>();
   string[] words={"Padlock","bubble","Bubble","Marker","Icon","Speed up","Plate","Ring"};
   foreach(var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)){
    if(!r.enabled)continue;var t=r.transform;bool hit=false;
    for(int depth=0;depth<3&&t&&!hit;depth++,t=t.parent)foreach(var w in words)if(t.name.Contains(w)){hit=true;break;}
    if(hit){r.enabled=false;list.Add(r);}
   }
   return list;
  }

  // The postcard's ribbon: the player's face, the market's name and stage, "Vem jogar comigo!" and the friend code.
  GameObject PostcardOverlay(ShareMessage m){
   var go=new GameObject("Postcard",typeof(RectTransform),typeof(Canvas),typeof(UnityEngine.UI.CanvasScaler));
   var canvas=go.GetComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=32000;CheckoutScreen.Fit(go.GetComponent<UnityEngine.UI.CanvasScaler>());
   var root=(RectTransform)go.transform;
   var edge=CheckoutDesktopCard.Image(root,"Ribbon",K.C("E3B54A"),26);var er=edge.rectTransform;er.anchorMin=er.anchorMax=er.pivot=new Vector2(0,0);er.anchoredPosition=new Vector2(28,26);
   var fit=edge.gameObject.AddComponent<UnityEngine.UI.ContentSizeFitter>();fit.horizontalFit=fit.verticalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;
   CheckoutDesktopCard.Column(edge.gameObject,0,new RectOffset(3,3,3,3));
   var face=CheckoutDesktopCard.Image(edge.transform,"Face",K.C("1D2B4F"),24);var row=CheckoutDesktopCard.Row(face.gameObject,16,new RectOffset(16,26,14,14));row.childAlignment=TextAnchor.MiddleLeft;
   var ring=CheckoutDesktopCard.Image(face.transform,"Avatar",K.C("E3B54A"),44);var rl=ring.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();rl.preferredWidth=rl.preferredHeight=96;
   var plate=CheckoutDesktopCard.Image(ring.transform,"Plate",K.C("2A3D6B"),40);var pr=plate.rectTransform;pr.anchorMin=Vector2.zero;pr.anchorMax=Vector2.one;pr.offsetMin=new Vector2(4,4);pr.offsetMax=new Vector2(-4,-4);
   var avatar=CheckoutDesktopCard.Image(plate.transform,"Face",Color.white,0);avatar.preserveAspect=true;avatar.sprite=K.Icon(m.avatar);avatar.enabled=avatar.sprite;var ar=avatar.rectTransform;ar.anchorMin=Vector2.zero;ar.anchorMax=Vector2.one;ar.offsetMin=new Vector2(2,0);ar.offsetMax=new Vector2(-2,-2);
   var texts=CheckoutDesktopCard.Node("Texts",face.transform);CheckoutDesktopCard.Column(texts.gameObject,0);
   var caption=CheckoutDesktopCard.Text(texts,"Caption",K.Label,18,K.C("E3B54A"));caption.text=(m.caption??"").ToUpperInvariant();caption.characterSpacing=3;caption.textWrappingMode=TMPro.TextWrappingModes.NoWrap;
   var name=CheckoutDesktopCard.Text(texts,"Name",K.Headline,38,Color.white);name.text=m.name??"";name.textWrappingMode=TMPro.TextWrappingModes.NoWrap;
   var code=CheckoutDesktopCard.Text(texts,"Code",K.Number,24,K.C("F3E6CC"));code.text=(string.IsNullOrEmpty(m.stage)?"":m.stage+"  ·  ")+(m.codeLabel??"")+"  "+(m.code??"");code.textWrappingMode=TMPro.TextWrappingModes.NoWrap;
   return go;
  }

  static Texture2D Fit(Texture2D source,int maxWidth){
   if(source.width<=maxWidth)return source;
   int w=maxWidth,h=Mathf.RoundToInt(source.height*(maxWidth/(float)source.width));
   var rt=RenderTexture.GetTemporary(w,h,0);Graphics.Blit(source,rt);var prev=RenderTexture.active;RenderTexture.active=rt;
   var result=new Texture2D(w,h,TextureFormat.RGB24,false);result.ReadPixels(new Rect(0,0,w,h),0,0);result.Apply();
   RenderTexture.active=prev;RenderTexture.ReleaseTemporary(rt);return result;
  }
#if UNITY_IOS && !UNITY_EDITOR
  [System.Runtime.InteropServices.DllImport("__Internal")] static extern void CheckoutShare_Share(string text,string url,string imagePath);
#endif

  static readonly Regex CodePattern=new Regex(@"(?:checkout://add/|/i/|invite=)([A-Za-z0-9]{4}-?[A-Za-z0-9]{4})(?![A-Za-z0-9])",RegexOptions.Compiled);
  /// <summary>The friend code in checkout://add/&lt;code&gt;, an invite page link or a Play referrer (invite=&lt;code&gt;).</summary>
  public static string CodeIn(string text){
   if(string.IsNullOrEmpty(text))return null;
   try{text=Uri.UnescapeDataString(text);}catch{}
   var m=CodePattern.Match(text);return m.Success?m.Groups[1].Value.Replace("-","").ToUpperInvariant():null;
  }
  void OnDeepLink(string url){var code=CodeIn(url);if(code!=null)Offer(code,"deeplink");}
  void Offer(string code,string source){
   var json=JsonUtility.ToJson(new Link{code=code,source=source});
   if(statusSent&&host)host.Send(json);else links.Enqueue(json);
  }
  // Android: the Play Store says which link installed the game (…&referrer=invite%3D<code>). Asked once per install,
  // after the first login (social needs an account); the code is offered on the Amigos page.
  void MaybeReferrer(){
#if UNITY_ANDROID && !UNITY_EDITOR
   if(PlayerPrefs.GetInt("checkout.social.referrer",0)==1)return;
   try{
    using var player=new AndroidJavaClass("com.unity3d.player.UnityPlayer");
    using var activity=player.GetStatic<AndroidJavaObject>("currentActivity");
    using var plugin=new AndroidJavaClass("com.checkout.social.CheckoutReferrer");
    plugin.CallStatic("fetch",activity,gameObject.name);
   }catch(Exception ex){Debug.LogWarning("CHECKOUT_SOCIAL referrer: "+ex.Message);}
#endif
  }
  /// <summary>Called by CheckoutReferrer.java (UnitySendMessage) with the install referrer ("" when none).</summary>
  public void OnInstallReferrer(string referrer){
   PlayerPrefs.SetInt("checkout.social.referrer",1);PlayerPrefs.Save();
   var code=CodeIn(referrer);if(code!=null)Offer(code,"referrer");
  }

  // ---- avatars: portraits of the game's own shoppers ("shopper-1" … "shopper-N") ----
  static readonly Dictionary<string,Sprite> avatars=new Dictionary<string,Sprite>();
  static readonly HashSet<string> wanted=new HashSet<string>();
  static List<Animation> faces;static bool rendering;
  /// <summary>The shoppers' different looks, in a fixed order (every phone gets the same face for the same id).</summary>
  static List<Animation> Faces(){
   if(faces!=null&&faces.All(f=>f))return faces;
   var seen=new Dictionary<string,Animation>();
   foreach(var motion in FindObjectsByType<MarketDay.MarketCharacterAnimator>(FindObjectsInactive.Include,FindObjectsSortMode.None)){
    if(!motion||!motion.animationPlayer||!motion.GetComponent<CheckoutWalker>())continue;
    var key=LookOf(motion.animationPlayer.transform);if(key!=null&&!seen.ContainsKey(key))seen[key]=motion.animationPlayer;
   }
   faces=seen.OrderBy(p=>p.Key,StringComparer.Ordinal).Select(p=>p.Value).Take(12).ToList();
   return faces;
  }
  static string LookOf(Transform model){
   foreach(var r in model.GetComponentsInChildren<SkinnedMeshRenderer>(true))if(!r.name.EndsWith("_Prop")&&r.sharedMaterial&&r.sharedMaterial.mainTexture)return r.sharedMaterial.mainTexture.name;
   return null;
  }
  public static int AvatarCount(){try{return Mathf.Clamp(Faces().Count,0,12);}catch{return 0;}}
  /// <summary>The face for an avatar id; a stand-in icon until it is drawn (it is drawn once, then kept).</summary>
  public static Sprite Avatar(string id){
   if(string.IsNullOrEmpty(id))id="shopper-1";
   if(avatars.TryGetValue(id,out var sprite)&&sprite)return sprite;
   wanted.Add(id);
   if(Active&&!rendering)Active.StartCoroutine(Active.RenderAvatars());
   return K.Icon("Icons/customers");
  }
  IEnumerator RenderAvatars(){
   rendering=true;
   try{
    while(wanted.Count>0){
     var id=wanted.First();wanted.Remove(id);
     if(avatars.ContainsKey(id))continue;
     int index=int.TryParse(id.Replace("shopper-",""),out var n)?n-1:-1;
     var list=Faces();
     if(index<0||index>=list.Count){avatars[id]=null;continue;}
     yield return null;
     var sprite=Portrait(list[index]);
     if(sprite)avatars[id]=sprite;
     // The HUD picks the new face up with the next view (every second or so).
    }
   }finally{rendering=false;}
  }
  const int PortraitLayer=31;
  static Sprite Portrait(Animation source){
   GameObject clone=null;Camera cam=null;RenderTexture rt=null;
   try{
    clone=Instantiate(source.gameObject);clone.name="Avatar portrait";
    foreach(var mb in clone.GetComponentsInChildren<MonoBehaviour>(true))DestroyImmediate(mb);
    clone.transform.SetPositionAndRotation(new Vector3(0,-300,0),Quaternion.identity);clone.SetActive(true);
    foreach(var t in clone.GetComponentsInChildren<Transform>(true)){t.gameObject.layer=PortraitLayer;t.gameObject.SetActive(t==clone.transform||t.gameObject.activeSelf);}
    foreach(var r in clone.GetComponentsInChildren<Renderer>(true))if(r.name.EndsWith("_Prop"))r.enabled=false;
    var animation=clone.GetComponent<Animation>();
    if(animation){
     AnimationState idle=null;foreach(AnimationState s in animation)if(idle==null||s.name.ToLowerInvariant().Contains("idle"))idle=s;
     if(idle!=null){animation.Play(idle.name);idle.time=.3f;animation.Sample();}
    }
    // Frame the head (like the till's live portrait): the top of the baked body and the Head joint.
    Transform head=null;foreach(var t in clone.GetComponentsInChildren<Transform>(true))if(t.name=="Head"||t.name.ToLowerInvariant().EndsWith(":head")){head=t;break;}
    SkinnedMeshRenderer body=null;foreach(var r in clone.GetComponentsInChildren<SkinnedMeshRenderer>(true))if(!r.name.EndsWith("_Prop")&&r.sharedMesh&&(!body||r.sharedMesh.vertexCount>body.sharedMesh.vertexCount))body=r;
    float top=float.MinValue;
    if(body){var baked=new Mesh();body.BakeMesh(baked,true);foreach(var v in baked.vertices)top=Mathf.Max(top,body.transform.TransformPoint(v).y);DestroyImmediate(baked);}
    float headSize=head&&top>float.MinValue?Mathf.Clamp(top-head.position.y,.2f,.9f):.4f;
    Vector3 center=head?head.position+Vector3.up*headSize*.35f:clone.transform.position+Vector3.up*(top>float.MinValue?top-clone.transform.position.y-.2f:1.6f);
    var face=clone.transform.forward;face.y=0;if(face.sqrMagnitude<.01f)face=Vector3.forward;face.Normalize();
    rt=new RenderTexture(256,256,24,RenderTextureFormat.ARGB32);
    cam=new GameObject("Avatar camera").AddComponent<Camera>();cam.enabled=false;cam.targetTexture=rt;cam.cullingMask=1<<PortraitLayer;
    cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=K.C("1D2B4F");cam.fieldOfView=30;cam.nearClipPlane=.05f;cam.farClipPlane=10;
    float d=headSize*2.3f/.536f;cam.transform.position=center+face*d+Vector3.up*headSize*.1f;cam.transform.LookAt(center);
    cam.Render();
    var prev=RenderTexture.active;RenderTexture.active=rt;
    var texture=new Texture2D(256,256,TextureFormat.RGBA32,false);texture.ReadPixels(new Rect(0,0,256,256),0,0);texture.Apply();
    RenderTexture.active=prev;
    return Sprite.Create(texture,new Rect(0,0,256,256),new Vector2(.5f,.5f));
   }catch(Exception ex){Debug.LogWarning("CHECKOUT_SOCIAL avatar: "+ex.Message);return null;}
   finally{if(cam)DestroyImmediate(cam.gameObject);if(rt){rt.Release();DestroyImmediate(rt);}if(clone)DestroyImmediate(clone);}
  }
 }
}
