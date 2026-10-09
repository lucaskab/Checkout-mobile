using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.IO;
using UnityEngine;
using Debug = UnityEngine.Debug;
namespace Checkout {
 // Desktop stand-in for the React Native app: spawns desktop/host.ts (the real game store under
 // Node) and exchanges the same bridge messages over stdin/stdout. Mobile builds never create it.
 [DefaultExecutionOrder(-600)]
 public class CheckoutDesktopHost:MonoBehaviour {
  public static CheckoutDesktopHost Active {get;private set;}
  Process process;StreamWriter input;readonly ConcurrentQueue<string> lines=new ConcurrentQueue<string>();
  CheckoutBridge bridge;CheckoutDesktopHUD hud;
  [Serializable] class Kind{public string kind;}
  [Serializable] class I18nMessage{public string lang;public string[] keys;public string[] values;}

#if UNITY_EDITOR || (UNITY_STANDALONE && !UNITY_IOS && !UNITY_ANDROID)
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Boot(){
   // QA runs feed a fixed snapshot file and must stay offline.
   if(Array.IndexOf(Environment.GetCommandLineArgs(),"--checkout-snapshot")>=0||Environment.GetEnvironmentVariable("CHECKOUT_DESKTOP")=="0")return;
   var bridge=FindAnyObjectByType<CheckoutBridge>();if(!bridge)return;
   // The start screen asks "Jogar" or "Modo edição" before the game (and its save) starts.
   CheckoutStartMenu.Show(bridge.gameObject);
  }
#endif

  // Release builds (Checkout/Build Release) ship the game host compiled with Bun in StreamingAssets, so
  // testers need neither Node nor the repository. Returns null when the player has no bundled host.
  public static string BundledHost(){
   if(Application.isEditor)return null;
   string name;
   if(Application.platform==RuntimePlatform.WindowsPlayer)name="checkout-host-win-x64.exe";
   else if(Application.platform==RuntimePlatform.OSXPlayer)name=System.Runtime.InteropServices.RuntimeInformation.ProcessArchitecture==System.Runtime.InteropServices.Architecture.Arm64?"checkout-host-mac-arm64":"checkout-host-mac-x64";
   else return null;
   var path=Path.Combine(Application.streamingAssetsPath,name);
   return File.Exists(path)?path:null;
  }
  public static bool IsRelease=>BundledHost()!=null;

  static string Node(){
   foreach(var path in new[]{Environment.GetEnvironmentVariable("CHECKOUT_NODE"),"/opt/homebrew/bin/node","/usr/local/bin/node","/usr/bin/node"})if(!string.IsNullOrEmpty(path)&&File.Exists(path))return path;
   return "node";
  }
  static string Repo(){
   var configured=Environment.GetEnvironmentVariable("CHECKOUT_REPO");
   if(!string.IsNullOrEmpty(configured)&&HasHost(configured))return Path.GetFullPath(configured);
   foreach(var start in new[]{Application.dataPath,Environment.CurrentDirectory}){
    var root=FindRepoRoot(start);if(!string.IsNullOrEmpty(root))return root;
   }
   return Path.GetFullPath(Path.Combine(Application.dataPath,"..","..",".."));
  }
  static string FindRepoRoot(string start){
   if(string.IsNullOrEmpty(start))return null;
   var path=Path.GetFullPath(start);
   while(!string.IsNullOrEmpty(path)){
    if(HasHost(path))return path;
    var parent=Directory.GetParent(path);if(parent==null)break;path=parent.FullName;
   }
   return null;
  }
  static bool HasHost(string root)=>Directory.Exists(root)&&File.Exists(Path.Combine(root,"desktop","host.ts"));

  void Awake(){
   bridge=GetComponent<CheckoutBridge>();
   ProcessStartInfo start;var bundled=BundledHost();
   if(bundled!=null)start=new ProcessStartInfo(bundled,""){WorkingDirectory=Application.persistentDataPath};
   else{
    var repo=Repo();
    if(!File.Exists(Path.Combine(repo,"desktop","host.ts"))){Debug.LogWarning("CHECKOUT_DESKTOP host.ts not found under "+repo);Destroy(this);return;}
    start=new ProcessStartInfo(Node(),"--no-warnings --import ./desktop/register.mjs desktop/host.ts"){WorkingDirectory=repo};
   }
   start.UseShellExecute=false;start.RedirectStandardInput=true;start.RedirectStandardOutput=true;start.RedirectStandardError=true;start.CreateNoWindow=true;start.StandardOutputEncoding=System.Text.Encoding.UTF8;
   // "Modo edição" plays on its own sandbox save (infinite money, everything unlocked): the real game is untouched.
   // The release build (sent to testers) keeps its own save, so trying it on the dev machine never touches the real game.
   var save=Path.Combine(Application.persistentDataPath,CheckoutStartMenu.EditMode?"checkout-editor-save.json":bundled!=null?"checkout-release-save.json":"checkout-desktop-save.json");
   // QA runs play a fresh copy of the player's save (they switch stages with the dev tools).
   if(CheckoutStartMenu.QaMode){var qa=Path.Combine(Application.persistentDataPath,"checkout-qa-save.json");try{if(File.Exists(save))File.Copy(save,qa,true);}catch{}save=qa;}
   start.EnvironmentVariables["CHECKOUT_DESKTOP_SAVE"]=save;
   // The language picked on the start screen: the host translates every page before sending it.
   start.EnvironmentVariables["CHECKOUT_LANG"]=CheckoutI18n.Language;
   try {process=Process.Start(start);}catch(Exception ex){Debug.LogError("CHECKOUT_DESKTOP could not start node: "+ex.Message);Destroy(this);return;}
   input=new StreamWriter(process.StandardInput.BaseStream,new System.Text.UTF8Encoding(false)){AutoFlush=true,NewLine="\n"};
   process.OutputDataReceived+=(_,e)=>{if(e.Data!=null)lines.Enqueue(e.Data);};
   process.ErrorDataReceived+=(_,e)=>{if(!string.IsNullOrEmpty(e.Data))Debug.Log("CHECKOUT_HOST "+e.Data);};
   process.BeginOutputReadLine();process.BeginErrorReadLine();
   Active=this;hud=gameObject.AddComponent<CheckoutDesktopHUD>();hud.Initialize(this);
   if(CheckoutStartMenu.EditMode)gameObject.AddComponent<CheckoutMapEditor>().Initialize(this);
  }

  public bool Send(string json){
   if(process==null||process.HasExited)return false;
   try {input.WriteLine(json);return true;}catch(Exception ex){Debug.LogWarning("CHECKOUT_DESKTOP send failed: "+ex.Message);return false;}
  }
  public void Route(string route)=>Send("{\"kind\":\"route\",\"route\":"+Quote(route)+"}");
  int sequence;
  public string Action(string action,string args,string after){
   string id="hud-"+(++sequence);
   Send("{\"kind\":\"hud\",\"id\":\""+id+"\",\"action\":"+Quote(action)+",\"args\":"+(string.IsNullOrEmpty(args)?"[]":args)+",\"after\":"+Quote(after??"")+"}");
   return id;
  }
  static string Quote(string value)=>"\""+(value??"").Replace("\\","\\\\").Replace("\"","\\\"")+"\"";

  // The game page stack is shown again (the map editor hides it while editing).
  public CheckoutDesktopHUD Hud=>hud;
  void Update(){
   // Only the newest view matters; snapshots and results are applied in order.
   string latestView=null;
   while(lines.TryDequeue(out var line)){
    string kind;try {kind=JsonUtility.FromJson<Kind>(line)?.kind;}catch {continue;}
    if(kind=="view")latestView=line;
    else if(kind=="snapshot")bridge.Receive(line);
    else if(kind=="result")hud.Result(line);
    else if(kind=="receipt")bridge.Receipt(line); // retries stale commands, logs other rejections
    else if(kind=="i18n"){var m=JsonUtility.FromJson<I18nMessage>(line);if(m!=null)CheckoutI18n.Load(m.lang,m.keys,m.values);}
   }
   if(latestView!=null)hud.Apply(latestView);
   if(process!=null&&process.HasExited&&Active==this){Active=null;hud.Offline(CheckoutI18n.T(IsRelease?"O jogo parou de responder. Feche e abra de novo.":"O processo do jogo (node) parou. Veja o Console."));}
  }

  void OnDestroy(){
   if(Active==this)Active=null;
   try {input?.Close();}catch {}
   try {if(process!=null&&!process.HasExited&&!process.WaitForExit(500))process.Kill();}catch {}
   process?.Dispose();
  }
 }
}
