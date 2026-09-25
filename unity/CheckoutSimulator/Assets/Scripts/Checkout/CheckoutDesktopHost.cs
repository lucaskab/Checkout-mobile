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

#if UNITY_EDITOR || (UNITY_STANDALONE && !UNITY_IOS && !UNITY_ANDROID)
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Boot(){
   // QA runs feed a fixed snapshot file and must stay offline.
   if(Array.IndexOf(Environment.GetCommandLineArgs(),"--checkout-snapshot")>=0||Environment.GetEnvironmentVariable("CHECKOUT_DESKTOP")=="0")return;
   var bridge=FindAnyObjectByType<CheckoutBridge>();if(!bridge)return;
   bridge.gameObject.AddComponent<CheckoutDesktopHost>();
  }
#endif

  static string Node(){
   foreach(var path in new[]{Environment.GetEnvironmentVariable("CHECKOUT_NODE"),"/opt/homebrew/bin/node","/usr/local/bin/node","/usr/bin/node"})if(!string.IsNullOrEmpty(path)&&File.Exists(path))return path;
   return "node";
  }
  static string Repo(){
   var root=Environment.GetEnvironmentVariable("CHECKOUT_REPO");if(!string.IsNullOrEmpty(root))return root;
   // Assets → CheckoutSimulator → unity → repository.
   return Path.GetFullPath(Path.Combine(Application.dataPath,"..","..",".."));
  }

  void Awake(){
   bridge=GetComponent<CheckoutBridge>();var repo=Repo();
   if(!File.Exists(Path.Combine(repo,"desktop","host.ts"))){Debug.LogWarning("CHECKOUT_DESKTOP host.ts not found under "+repo);Destroy(this);return;}
   var start=new ProcessStartInfo(Node(),"--no-warnings --import ./desktop/register.mjs desktop/host.ts"){WorkingDirectory=repo,UseShellExecute=false,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true,StandardOutputEncoding=System.Text.Encoding.UTF8};
   start.EnvironmentVariables["CHECKOUT_DESKTOP_SAVE"]=Path.Combine(Application.persistentDataPath,"checkout-desktop-save.json");
   try {process=Process.Start(start);}catch(Exception ex){Debug.LogError("CHECKOUT_DESKTOP could not start node: "+ex.Message);Destroy(this);return;}
   input=new StreamWriter(process.StandardInput.BaseStream,new System.Text.UTF8Encoding(false)){AutoFlush=true,NewLine="\n"};
   process.OutputDataReceived+=(_,e)=>{if(e.Data!=null)lines.Enqueue(e.Data);};
   process.ErrorDataReceived+=(_,e)=>{if(!string.IsNullOrEmpty(e.Data))Debug.Log("CHECKOUT_HOST "+e.Data);};
   process.BeginOutputReadLine();process.BeginErrorReadLine();
   Active=this;hud=gameObject.AddComponent<CheckoutDesktopHUD>();hud.Initialize(this);
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

  void Update(){
   // Only the newest view matters; snapshots and results are applied in order.
   string latestView=null;
   while(lines.TryDequeue(out var line)){
    string kind;try {kind=JsonUtility.FromJson<Kind>(line)?.kind;}catch {continue;}
    if(kind=="view")latestView=line;
    else if(kind=="snapshot")bridge.Receive(line);
    else if(kind=="result")hud.Result(line);
    else if(kind=="receipt"){}
   }
   if(latestView!=null)hud.Apply(latestView);
   if(process!=null&&process.HasExited&&Active==this){Active=null;hud.Offline("O processo do jogo (node) parou. Veja o Console.");}
  }

  void OnDestroy(){
   if(Active==this)Active=null;
   try {input?.Close();}catch {}
   try {if(process!=null&&!process.HasExited&&!process.WaitForExit(500))process.Kill();}catch {}
   process?.Dispose();
  }
 }
}
