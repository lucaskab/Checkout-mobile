using System;
using System.Collections;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;

namespace Checkout {
 /// <summary>
 /// Cloud saves (Lucas 12/10): the player signs in with Google and the progress (market, coins, diamonds) follows
 /// them to a new phone. The server is server/ (Node on Render, Prisma Postgres); the host owns the save itself
 /// (desktop/cloud.ts: cloud-export / cloud-import) and the "Conta" page.
 /// - Login: Android = "Sign in with Google" (Credential Manager, Plugins/Android/CheckoutGoogleSignIn.java);
 ///   Editor and PC builds = the browser (OAuth with PKCE on a 127.0.0.1 port; the server trades the code).
 ///   iPhone: not yet (needs Google Sign-In for iOS and Sign in with Apple).
 /// - Sync: every few minutes while playing (only when the save changed) and when the app goes to the background.
 ///   Each upload says which cloud revision it builds on; if another phone uploaded in between, the server refuses
 ///   and the player chooses which progress continues (never a silent overwrite). A new phone (fresh game) simply
 ///   takes the cloud's progress.
 /// </summary>
 public class CheckoutCloud:MonoBehaviour {
  public static CheckoutCloud Active {get;private set;}
  // Render service (render.yaml). CHECKOUT_SERVER overrides it (a local server while developing).
  const string DefaultServer="https://checkout-server-babc.onrender.com";
  // Google Cloud project "Checkout Game": the web client is the audience of the phone's login; the desktop client
  // is the PC/Editor's (its secret stays on the server).
  public const string WebClientId="663095472642-8vg9kgj7o3fdfv56k74m0v37leaqb5ni.apps.googleusercontent.com";
  const string DesktopClientId="663095472642-6votj9sh26dh1nrqpnn196hf301jhtqk.apps.googleusercontent.com";
  const float UploadEvery=300f,RetryOffline=60f;
  static string Server{get{var env=Environment.GetEnvironmentVariable("CHECKOUT_SERVER");return string.IsNullOrEmpty(env)?DefaultServer:env.TrimEnd('/');}}

  CheckoutDesktopHost host;
  string token,playerId,email,playerName,deviceId,lastHash;int revision;long lastSyncAt;
  // What the progress held at the last sync (level, day, diamonds), and which account it belongs to.
  Summary synced;string owner;
  string status="unavailable";bool busy,uploadWaiting;float nextUpload=float.MaxValue;
  CloudSave conflictCloud;
  readonly Dictionary<string,Action<string>> waiting=new Dictionary<string,Action<string>>();int sequence;

  // ---- JSON shapes (server and host) ----
  [Serializable] public class Summary{public int level;public string era;public double coins;public double diamonds;public int day;public int version;}
  [Serializable] public class CloudSave{public int revision;public string updatedAt;public Summary summary;public string deviceId;public string data;}
  [Serializable] class Player{public string id;public string email;public string name;}
  [Serializable] class AuthReply{public string token;public Player player;public CloudSave save;}
  [Serializable] class ConflictReply{public string error;public CloudSave current;}
  [Serializable] class Upload{public int baseRevision;public string data;public string deviceId;public bool force;}
  [Serializable] class IdToken{public string idToken;}
  [Serializable] class CodeLogin{public string code;public string codeVerifier;public string redirectUri;}
  [Serializable] class Exported{public string id;public string data;public Summary summary;public bool fresh;}
  [Serializable] class Imported{public string id;public bool ok;}
  [Serializable] class Resolve{public string keep;}
  [Serializable] class Conflict{public Summary cloud;public long cloudAt;public string cloudDevice;public bool otherAccount;}
  [Serializable] class Status{public string kind="cloud";public string status;public string email;public string name;public long lastSyncAt;public string error;public Conflict conflict;}

  public static void Attach(CheckoutDesktopHost owner){
   if(Active||!owner)return;
   // UnitySendMessage (Android login) finds the receiver by name.
   var go=new GameObject("CheckoutCloud");go.transform.SetParent(owner.transform,false);
   Active=go.AddComponent<CheckoutCloud>();Active.host=owner;
  }
  static bool SignInSupported=>Application.isEditor||Application.platform==RuntimePlatform.Android||Application.platform==RuntimePlatform.WindowsPlayer||Application.platform==RuntimePlatform.OSXPlayer;

  IEnumerator Start(){
   token=PlayerPrefs.GetString("checkout.cloud.token","");playerId=PlayerPrefs.GetString("checkout.cloud.player","");
   email=PlayerPrefs.GetString("checkout.cloud.email","");playerName=PlayerPrefs.GetString("checkout.cloud.name","");
   deviceId=PlayerPrefs.GetString("checkout.cloud.device","");owner=PlayerPrefs.GetString("checkout.cloud.owner","");
   if(string.IsNullOrEmpty(deviceId)){deviceId=SystemInfo.deviceModel+"-"+Guid.NewGuid().ToString("N").Substring(0,8);PlayerPrefs.SetString("checkout.cloud.device",deviceId);PlayerPrefs.Save();}
   LoadPlayerState();
   // Let the host start and load the save first.
   yield return new WaitForSecondsRealtime(2f);
   if(!SignInSupported){Report("unavailable");yield break;}
   if(string.IsNullOrEmpty(token)){Report("signed-out");yield break;}
   yield return Run(Reconcile());
  }
  void LoadPlayerState(){
   revision=string.IsNullOrEmpty(playerId)?0:PlayerPrefs.GetInt("checkout.cloud.rev."+playerId,0);
   lastHash=string.IsNullOrEmpty(playerId)?"":PlayerPrefs.GetString("checkout.cloud.hash."+playerId,"");
   lastSyncAt=string.IsNullOrEmpty(playerId)?0:long.TryParse(PlayerPrefs.GetString("checkout.cloud.at."+playerId,"0"),out var at)?at:0;
   var json=string.IsNullOrEmpty(playerId)?"":PlayerPrefs.GetString("checkout.cloud.summary."+playerId,"");
   synced=string.IsNullOrEmpty(json)?null:JsonUtility.FromJson<Summary>(json);
  }
  void SavePlayerState(){
   if(string.IsNullOrEmpty(playerId))return;
   PlayerPrefs.SetInt("checkout.cloud.rev."+playerId,revision);PlayerPrefs.SetString("checkout.cloud.hash."+playerId,lastHash??"");
   PlayerPrefs.SetString("checkout.cloud.at."+playerId,lastSyncAt.ToString());
   if(synced!=null)PlayerPrefs.SetString("checkout.cloud.summary."+playerId,JsonUtility.ToJson(synced));
   // The progress on this device now belongs to this account.
   owner=playerId;PlayerPrefs.SetString("checkout.cloud.owner",owner);PlayerPrefs.Save();
  }
  bool SignedIn=>!string.IsNullOrEmpty(token);

  void Report(string next,string error="",Conflict conflict=null){
   status=next;
   host.Send(JsonUtility.ToJson(new Status{status=next,email=SignedIn?email:"",name=SignedIn?playerName:"",lastSyncAt=lastSyncAt,error=error,conflict=conflict}));
  }

  void Update(){
   if(!SignedIn||busy||status=="conflict")return;
   if(!uploadWaiting&&Time.unscaledTime<nextUpload)return;
   uploadWaiting=false;nextUpload=Time.unscaledTime+UploadEvery;StartCoroutine(Run(UploadSave(false)));
  }
  // Leaving the game (phone home button, closing the window): send what changed now (or right after the current call).
  void OnApplicationPause(bool paused){
   if(!paused||!SignedIn||status=="conflict")return;
   if(busy)uploadWaiting=true;else StartCoroutine(Run(UploadSave(false)));
  }
  void OnApplicationFocus(bool focused){if(!focused)OnApplicationPause(true);}
  void OnDestroy(){if(Active==this)Active=null;}

  IEnumerator Run(IEnumerator work){if(busy)yield break;busy=true;try{yield return work;}finally{busy=false;}}

  // ---- host lines ----
  public void OnHost(string kind,string line){
   switch(kind){
    case "cloud-signin":if(!busy&&!SignedIn)StartCoroutine(Run(SignIn()));break;
    case "cloud-sync":if(!busy&&SignedIn)StartCoroutine(Run(status=="conflict"?Reconcile():UploadSave(false)));break;
    case "cloud-signout":SignOut();break;
    case "cloud-delete":if(!busy&&SignedIn)StartCoroutine(Run(DeleteAccount()));break;
    case "cloud-resolve":{var keep=JsonUtility.FromJson<Resolve>(line)?.keep;if(!busy&&SignedIn&&status=="conflict")StartCoroutine(Run(keep=="cloud"?TakeCloud():UploadSave(true)));break;}
    case "cloud-save":{var m=JsonUtility.FromJson<Exported>(line);if(m!=null&&waiting.TryGetValue(m.id??"",out var done)){waiting.Remove(m.id);done(line);}break;}
    case "cloud-imported":{var m=JsonUtility.FromJson<Imported>(line);if(m!=null&&waiting.TryGetValue(m.id??"",out var done)){waiting.Remove(m.id);done(line);}break;}
   }
  }
  IEnumerator AskHost(string kind,string extra,Action<string> answer){
   string id="cloud-"+(++sequence);string reply=null;waiting[id]=r=>reply=r;
   host.Send("{\"kind\":\""+kind+"\",\"id\":\""+id+"\""+extra+"}");
   float until=Time.unscaledTime+30f;
   while(reply==null&&Time.unscaledTime<until)yield return null;
   waiting.Remove(id);answer(reply);
  }
  IEnumerator ExportSave(Action<Exported> answer){
   Exported result=null;yield return AskHost("cloud-export","",r=>{if(r!=null)result=JsonUtility.FromJson<Exported>(r);});answer(result);
  }
  IEnumerator ImportSave(string data,Action<bool> answer){
   var wrapped=JsonUtility.ToJson(new Wrap{v=data});
   bool ok=false;yield return AskHost("cloud-import",",\"data\":"+wrapped.Substring(5,wrapped.Length-6),r=>{ok=r!=null&&(JsonUtility.FromJson<Imported>(r)?.ok??false);});answer(ok);
  }
  [Serializable] class Wrap{public string v;}

  // ---- server ----
  class Reply{public long code;public string text;public bool network;}
  IEnumerator Call(string method,string path,string body,Action<Reply> answer,int timeout=75){
   using var request=new UnityWebRequest(Server+path,method);
   if(body!=null){request.uploadHandler=new UploadHandlerRaw(Encoding.UTF8.GetBytes(body));request.SetRequestHeader("Content-Type","application/json");}
   request.downloadHandler=new DownloadHandlerBuffer();
   if(SignedIn)request.SetRequestHeader("Authorization","Bearer "+token);
   // The free server sleeps when nobody plays: the first call can take ~50 s to wake it.
   request.timeout=timeout;
   yield return request.SendWebRequest();
   answer(new Reply{code=request.responseCode,text=request.downloadHandler?.text??"",network=request.result==UnityWebRequest.Result.ConnectionError||request.responseCode==0});
  }
  static long ParseTime(string iso)=>DateTime.TryParse(iso,null,System.Globalization.DateTimeStyles.RoundtripKind,out var t)?new DateTimeOffset(t.ToUniversalTime()).ToUnixTimeMilliseconds():0;
  static long Now()=>DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
  static string Hash(string data){using var sha=SHA256.Create();return Convert.ToBase64String(sha.ComputeHash(Encoding.UTF8.GetBytes(data??"")));}

  bool Trouble(Reply r){
   if(r.code==401){Debug.Log("CHECKOUT_CLOUD session ended");SignOut();return true;}
   if(r.network||r.code>=500||r.code==429){Report("offline");nextUpload=Time.unscaledTime+RetryOffline;return true;}
   return false;
  }

  /// <summary>Start, login, "Salvar agora" after a conflict: compares this device with the cloud.</summary>
  IEnumerator Reconcile(){
   Report("syncing");
   Reply r=null;yield return Call("GET","/v1/save",null,x=>r=x);
   if(r.code==404){yield return UploadSave(false,true);yield break;}
   if(Trouble(r))yield break;
   if(r.code!=200){Report("error",CheckoutI18n.T("O servidor respondeu {0}.").Replace("{0}",r.code.ToString()));yield break;}
   var cloud=JsonUtility.FromJson<CloudSave>(r.text);
   if(cloud.revision==revision){lastSyncAt=Math.Max(lastSyncAt,ParseTime(cloud.updatedAt));SavePlayerState();Report("synced");nextUpload=Time.unscaledTime+30f;yield break;}
   Exported local=null;yield return ExportSave(x=>local=x);
   if(local==null){Report("error","O jogo não respondeu.");yield break;}
   // A new phone (nothing played yet) takes the cloud's progress; so does a device of this account that only fell
   // behind (nothing played here since its last sync: same level, day and diamonds). Otherwise the player chooses.
   bool sameAccount=string.IsNullOrEmpty(owner)||owner==playerId;
   bool unchanged=sameAccount&&revision>0&&synced!=null&&local.summary!=null&&local.summary.level==synced.level&&local.summary.day==synced.day&&Math.Abs(local.summary.diamonds-synced.diamonds)<.5;
   if(local.fresh||unchanged){yield return Apply(cloud);yield break;}
   ShowConflict(cloud);
  }
  void ShowConflict(CloudSave cloud){
   conflictCloud=cloud;
   Report("conflict","",new Conflict{cloud=cloud.summary,cloudAt=ParseTime(cloud.updatedAt),cloudDevice=cloud.deviceId,otherAccount=!string.IsNullOrEmpty(owner)&&owner!=playerId});
  }
  IEnumerator Apply(CloudSave cloud){
   bool ok=false;yield return ImportSave(cloud.data,x=>ok=x);
   if(!ok){Report("error","Não deu para carregar o progresso da nuvem.");yield break;}
   revision=cloud.revision;lastSyncAt=ParseTime(cloud.updatedAt);
   Exported now=null;yield return ExportSave(x=>now=x);lastHash=now!=null?Hash(now.data):"";synced=now?.summary??cloud.summary;
   SavePlayerState();conflictCloud=null;Report("synced");nextUpload=Time.unscaledTime+UploadEvery;
   host.Hud?.Notify(CheckoutI18n.T("Progresso da nuvem carregado!"),true);
  }
  IEnumerator TakeCloud(){
   Report("syncing");
   Reply r=null;yield return Call("GET","/v1/save",null,x=>r=x);
   if(Trouble(r))yield break;
   if(r.code!=200){Report("error","Não deu para baixar o progresso.");yield break;}
   yield return Apply(JsonUtility.FromJson<CloudSave>(r.text));
  }
  /// <summary>Sends this device's progress if it changed. force = the player chose it over the cloud's.</summary>
  IEnumerator UploadSave(bool force,bool always=false){
   Exported local=null;yield return ExportSave(x=>local=x);
   if(local==null||string.IsNullOrEmpty(local.data)){Report("error","O jogo não respondeu.");yield break;}
   var hash=Hash(local.data);
   if(!force&&!always&&hash==lastHash&&status!="offline"&&status!="error"){if(status!="synced")Report("synced");yield break;}
   Report("syncing");
   int baseRevision=force&&conflictCloud!=null?conflictCloud.revision:revision;
   Reply r=null;yield return Call("PUT","/v1/save",JsonUtility.ToJson(new Upload{baseRevision=baseRevision,data=local.data,deviceId=deviceId,force=force}),x=>r=x);
   if(r.code==409){
    var reply=JsonUtility.FromJson<ConflictReply>(r.text);conflictCloud=reply?.current;
    if(conflictCloud==null||conflictCloud.revision==0){revision=0;Report("error","Tente de novo.");yield break;}
    ShowConflict(conflictCloud);yield break;
   }
   if(Trouble(r))yield break;
   if(r.code!=200){Report("error",CheckoutI18n.T("O servidor recusou o envio ({0}).").Replace("{0}",r.code.ToString()));yield break;}
   var saved=JsonUtility.FromJson<CloudSave>(r.text);
   revision=saved.revision;lastHash=hash;synced=local.summary;lastSyncAt=ParseTime(saved.updatedAt);if(lastSyncAt==0)lastSyncAt=Now();
   conflictCloud=null;SavePlayerState();Report("synced");nextUpload=Time.unscaledTime+UploadEvery;
  }
  IEnumerator DeleteAccount(){
   Report("syncing");
   Reply r=null;yield return Call("DELETE","/v1/account",null,x=>r=x);
   if(r.code!=204&&r.code!=401){if(!Trouble(r))Report("error","Não deu para apagar a conta agora.");yield break;}
   if(!string.IsNullOrEmpty(playerId)){foreach(var key in new[]{"rev.","hash.","at.","summary."})PlayerPrefs.DeleteKey("checkout.cloud."+key+playerId);}
   // The progress stays on this device but no longer belongs to an account.
   if(owner==playerId){owner="";PlayerPrefs.DeleteKey("checkout.cloud.owner");}
   SignOut();host.Hud?.Notify(CheckoutI18n.T("Conta apagada."),true);
  }
  void SignOut(){
   token="";email=playerName="";conflictCloud=null;
   PlayerPrefs.DeleteKey("checkout.cloud.token");PlayerPrefs.DeleteKey("checkout.cloud.email");PlayerPrefs.DeleteKey("checkout.cloud.name");PlayerPrefs.Save();
   nextUpload=float.MaxValue;Report("signed-out");
  }

  // ---- Google login ----
  string idToken,signInError;bool signInDone;
  IEnumerator SignIn(){
   Report("signing-in");
   Reply r=null;
   if(Application.platform==RuntimePlatform.Android&&!Application.isEditor){
    idToken=signInError=null;signInDone=false;
    try{
     using var player=new AndroidJavaClass("com.unity3d.player.UnityPlayer");
     using var activity=player.GetStatic<AndroidJavaObject>("currentActivity");
     using var plugin=new AndroidJavaClass("com.checkout.signin.CheckoutGoogleSignIn");
     plugin.CallStatic("signIn",activity,WebClientId,gameObject.name);
    }catch(Exception ex){Debug.LogWarning("CHECKOUT_CLOUD sign-in: "+ex.Message);signInDone=true;signInError=ex.Message;}
    float until=Time.unscaledTime+180f;while(!signInDone&&Time.unscaledTime<until)yield return null;
    if(string.IsNullOrEmpty(idToken)){Report("signed-out",signInError=="cancelled"?"":"Não deu para entrar com o Google.");yield break;}
    yield return Call("POST","/v1/auth/google",JsonUtility.ToJson(new IdToken{idToken=idToken}),x=>r=x);
   } else {
    CodeLogin code=null;string error=null;
    yield return DesktopLogin(c=>code=c,e=>error=e);
    if(code==null){Report("signed-out",error??"");yield break;}
    yield return Call("POST","/v1/auth/google-code",JsonUtility.ToJson(code),x=>r=x);
   }
   if(r.network||r.code>=500){Report("signed-out","Sem conexão com o servidor. Tente de novo.");yield break;}
   if(r.code!=200){Report("signed-out",CheckoutI18n.T("O Google não confirmou o login ({0}).").Replace("{0}",r.code.ToString()));yield break;}
   var auth=JsonUtility.FromJson<AuthReply>(r.text);
   token=auth.token;playerId=auth.player.id;email=auth.player.email??"";playerName=auth.player.name??"";
   PlayerPrefs.SetString("checkout.cloud.token",token);PlayerPrefs.SetString("checkout.cloud.player",playerId);
   PlayerPrefs.SetString("checkout.cloud.email",email);PlayerPrefs.SetString("checkout.cloud.name",playerName);PlayerPrefs.Save();
   LoadPlayerState();
   yield return Reconcile();
  }

  // Called by CheckoutGoogleSignIn.java (UnitySendMessage).
  public void OnGoogleIdToken(string value){idToken=value;signInDone=true;}
  public void OnGoogleSignInFailed(string reason){signInError=reason;signInDone=true;Debug.Log("CHECKOUT_CLOUD Google sign-in: "+reason);}

  // PC and Editor: Google's login page opens in the browser and comes back to a one-time local address.
  IEnumerator DesktopLogin(Action<CodeLogin> done,Action<string> failed){
   string verifier=RandomText(48),state=RandomText(16);
   string challenge;using(var sha=SHA256.Create())challenge=Base64Url(sha.ComputeHash(Encoding.ASCII.GetBytes(verifier)));
   int port;var probe=new System.Net.Sockets.TcpListener(System.Net.IPAddress.Loopback,0);probe.Start();port=((System.Net.IPEndPoint)probe.LocalEndpoint).Port;probe.Stop();
   string redirect="http://127.0.0.1:"+port+"/";
   var listener=new System.Net.HttpListener();listener.Prefixes.Add(redirect);
   try{listener.Start();}catch(Exception ex){failed(CheckoutI18n.T("Não deu para entrar com o Google.")+" ("+ex.Message+")");yield break;}
   Application.OpenURL("https://accounts.google.com/o/oauth2/v2/auth?client_id="+DesktopClientId+"&redirect_uri="+Uri.EscapeDataString(redirect)
    +"&response_type=code&scope="+Uri.EscapeDataString("openid email profile")+"&code_challenge="+challenge+"&code_challenge_method=S256&state="+state+"&prompt=select_account");
   var pending=listener.GetContextAsync();float until=Time.unscaledTime+300f;
   while(!pending.IsCompleted&&Time.unscaledTime<until)yield return null;
   if(!pending.IsCompleted||pending.IsFaulted){try{listener.Stop();}catch{}failed("O login demorou demais.");yield break;}
   var context=pending.Result;var query=context.Request.QueryString;
   bool ok=query["state"]==state&&!string.IsNullOrEmpty(query["code"]);
   var page=Encoding.UTF8.GetBytes("<html><meta charset='utf-8'><body style='font-family:sans-serif;text-align:center;padding:60px'><h2>"
    +(ok?"Pronto! Pode voltar ao jogo.":"Login cancelado.")+"</h2></body></html>");
   context.Response.ContentType="text/html; charset=utf-8";context.Response.OutputStream.Write(page,0,page.Length);context.Response.Close();
   try{listener.Stop();}catch{}
   if(!ok){failed("");yield break;}
   done(new CodeLogin{code=query["code"],codeVerifier=verifier,redirectUri=redirect});
  }
  static string RandomText(int bytes){var data=new byte[bytes];using(var rng=RandomNumberGenerator.Create())rng.GetBytes(data);return Base64Url(data);}
  static string Base64Url(byte[] data)=>Convert.ToBase64String(data).TrimEnd('=').Replace('+','-').Replace('/','_');
 }
}
