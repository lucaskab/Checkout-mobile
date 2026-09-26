using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Checkout;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using Debug = UnityEngine.Debug;

// Unity <-> Blender bridge for the event props.
// 1) Runs Blender headless with scripts/blender/build_event_props.py (FBX -> Assets/Resources/EventProps).
// 2) Opens the market scene and enters Play mode. 3-5) Preview / capture the events while playing.
public static class CheckoutEventTools {
 const string Menu="Checkout/Eventos/";
 const string BlenderPref="Checkout.BlenderPath";
 static Process blender;static string blenderLog;static double started;static readonly object gate=new object();

 static string Repo=>Path.GetFullPath(Path.Combine(Application.dataPath,"..","..",".."));
 static string Script=>Path.Combine(Repo,"scripts","blender","build_event_props.py");
 public static string LogPath=>Path.GetFullPath(Path.Combine(Application.dataPath,"..","ArtSource","EventProps","blender.log"));

 static string FindBlender(){
  var saved=EditorPrefs.GetString(BlenderPref,"");if(File.Exists(saved))return saved;
  foreach(var root in new[]{Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),@"C:\Program Files"}){
   var foundation=Path.Combine(root,"Blender Foundation");if(!Directory.Exists(foundation))continue;
   var exe=Directory.GetDirectories(foundation).OrderByDescending(d=>d).Select(d=>Path.Combine(d,"blender.exe")).FirstOrDefault(File.Exists);if(exe!=null)return exe;}
  foreach(var mac in new[]{"/Applications/Blender.app/Contents/MacOS/Blender"})if(File.Exists(mac))return mac;
  return null;}

 [MenuItem(Menu+"1. Gerar props no Blender",false,1)]
 public static void BuildProps()=>RunBlender("");
 public static void RunBlender(string props){
  if(blender!=null&&!blender.HasExited){Debug.LogWarning("CHECKOUT_BLENDER_BUSY");return;}
  var exe=FindBlender();if(exe==null){exe=EditorUtility.OpenFilePanel("Localize o blender.exe","C:/Program Files","exe");if(string.IsNullOrEmpty(exe))return;EditorPrefs.SetString(BlenderPref,exe);}
  Directory.CreateDirectory(Path.GetDirectoryName(LogPath));blenderLog="";
  var info=new ProcessStartInfo(exe,$"-b --factory-startup --python \"{Script}\" -- {props}"){UseShellExecute=false,RedirectStandardOutput=true,RedirectStandardError=true,CreateNoWindow=true,WorkingDirectory=Repo};
  blender=new Process{StartInfo=info,EnableRaisingEvents=true};
  blender.OutputDataReceived+=(_,e)=>{if(e.Data!=null)lock(gate)blenderLog+=e.Data+"\n";};
  blender.ErrorDataReceived+=(_,e)=>{if(e.Data!=null)lock(gate)blenderLog+="ERR "+e.Data+"\n";};
  blender.Start();blender.BeginOutputReadLine();blender.BeginErrorReadLine();started=EditorApplication.timeSinceStartup;
  Debug.Log("CHECKOUT_BLENDER_START "+exe+" "+Script);EditorApplication.update+=WatchBlender;}
 static void WatchBlender(){
  if(blender==null){EditorApplication.update-=WatchBlender;return;}
  string log;lock(gate)log=blenderLog;int built=log.Split('\n').Count(l=>l.StartsWith("EVENT_PROP_BUILT"));
  if(!blender.HasExited){if(EditorUtility.DisplayCancelableProgressBar("Blender · props dos eventos",$"{built} props exportados…",Mathf.Repeat((float)(EditorApplication.timeSinceStartup-started)/60f,1))){blender.Kill();}return;}
  EditorApplication.update-=WatchBlender;EditorUtility.ClearProgressBar();File.WriteAllText(LogPath,log);
  var failed=log.Split('\n').Where(l=>l.StartsWith("EVENT_PROP_FAILED")||l.Contains("Traceback")||l.StartsWith("ERR Error")).ToArray();
  Debug.Log($"CHECKOUT_BLENDER_DONE exit={blender.ExitCode} built={built} failed={failed.Length} log={LogPath}");foreach(var f in failed)Debug.LogWarning(f);
  blender=null;AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);}

 [MenuItem(Menu+"2. Abrir mercado e dar Play",false,2)]
 public static void OpenAndPlay(){if(EditorApplication.isPlaying)return;if(!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo())return;EditorSceneManager.OpenScene(MarketBuilder.ScenePath);EditorApplication.isPlaying=true;}

 [MenuItem(Menu+"3. Próximo evento  ]",false,20)] static void Next(){if(CheckoutEventPreview.Instance)CheckoutEventPreview.Instance.Next();}
 [MenuItem(Menu+"4. Evento anterior  [",false,21)] static void Previous(){if(CheckoutEventPreview.Instance)CheckoutEventPreview.Instance.Previous();}
 [MenuItem(Menu+"5. Limpar evento",false,22)] static void Clear(){if(CheckoutEventPreview.Instance)CheckoutEventPreview.Instance.Clear();}
 [MenuItem(Menu+"6. Capturar todos os eventos (F9)",false,40)] static void Capture(){if(CheckoutEventPreview.Instance)CheckoutEventPreview.Instance.CaptureAll();}
 [MenuItem(Menu+"3. Próximo evento  ]",true)][MenuItem(Menu+"4. Evento anterior  [",true)][MenuItem(Menu+"5. Limpar evento",true)][MenuItem(Menu+"6. Capturar todos os eventos (F9)",true)]
 static bool Playing()=>EditorApplication.isPlaying&&CheckoutEventPreview.Instance;

 [MenuItem(Menu+"Abrir pasta de capturas",false,60)] static void Reveal(){Directory.CreateDirectory(CheckoutEventPreview.CaptureFolder);EditorUtility.RevealInFinder(CheckoutEventPreview.CaptureFolder);}
}
