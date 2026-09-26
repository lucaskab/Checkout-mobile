using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using UnityEditor;

// Dev helper: runs the project's own tools while the editor is open, so art, tests and play-mode
// checks can run without anyone clicking in Unity. Drop a request file in Logs/ and the result
// lands next to it:
//   Logs/tool_request.txt  first line:
//     "sprites [names]"   Blender renders scripts/blender/build_ui_sprites.py, then the art is reimported
//     "tests [paths]"     bun test in the repo root        "tsc"   TypeScript check
//     "editorlog"         copies the end of the editor log to Logs/editor_log.txt
//     "play a,b,c"        compiles if needed, enters play mode and runs CheckoutAutoTest scenarios
//     "stop" / "refresh"
//   Logs/tool_result.txt   exit code and output.
// A background thread watches for requests (the editor barely ticks while it is in the
// background); work that needs the editor's main thread brings the editor window to the front.
// Only these fixed commands run; the request only picks one and passes plain names.
[InitializeOnLoad]
public static class CheckoutToolRunner {
 const string Request="Logs/tool_request.txt",Result="Logs/tool_result.txt";
 const string Blender=@"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe";
 static readonly string Project=Directory.GetCurrentDirectory();
 static string P(string relative)=>Path.Combine(Project,relative);
 static Thread watcher;static volatile bool stopping;static volatile string mainThreadWork;static DateTime lastNudge;const string PlayPending="Logs/play_pending.txt";
 [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr hWnd);
 [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr hWnd,int nCmdShow);
 [DllImport("user32.dll")] static extern bool IsIconic(IntPtr hWnd);
 [DllImport("user32.dll")] static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,UIntPtr dwExtraInfo);

 static CheckoutToolRunner(){
  EditorApplication.update+=Tick;
  AssemblyReloadEvents.beforeAssemblyReload+=()=>{stopping=true;};
  stopping=false;watcher=new Thread(Watch){IsBackground=true,Name="CheckoutToolRunner"};watcher.Start();
 }

 // ------------------------------------------------------------------ background thread
 static void Watch(){
  while(!stopping){
   try{
    // A pending play survives the domain reload of a recompile; keep nudging the editor until it starts.
    if(File.Exists(P(PlayPending))&&(DateTime.Now-lastNudge).TotalSeconds>6){lastNudge=DateTime.Now;Wake(null);}
    if(mainThreadWork==null&&File.Exists(P(Request))){
     var lines=File.ReadAllLines(P(Request));File.Delete(P(Request));
     if(lines.Length>0)Handle(lines[0].Trim());
    }
   }catch(Exception e){Write($"runner error\n{e}");}
   Thread.Sleep(1000);
  }
 }
 static void Handle(string line){
  var words=line.Split(new[]{' '},StringSplitOptions.RemoveEmptyEntries);if(words.Length==0)return;
  var kind=words[0];var rest=string.Join(" ",words,1,words.Length-1);
  foreach(var c in rest)if(!(char.IsLetterOrDigit(c)||c=='_'||c=='-'||c=='.'||c=='/'||c==' '||c==','))return; // plain names only
  var root=Path.GetFullPath(Path.Combine(Project,"..",".."));
  switch(kind){
   case "sprites":Run(kind,Blender,$"-b --factory-startup --python \"{Path.Combine(root,"scripts","blender","build_ui_sprites.py")}\" -- {rest}",root);Wake("refresh");return;
   case "tests":Run(kind,"cmd.exe",$"/c bun test {rest}",root);return;
   case "tsc":Run(kind,"cmd.exe","/c node node_modules/typescript/bin/tsc --noEmit -p .",root);return;
   case "editorlog":WriteEditorLog();return;
   case "play":File.WriteAllText(P("Logs/autotest.txt"),rest);File.WriteAllText(P(PlayPending),rest);Write($"kind=play\nscenario={rest}\nwaiting for the editor");Wake(null);return;
   case "stop":Wake("stop");return;
   case "refresh":Wake("refresh");return;
  }
 }
 static void Run(string kind,string exe,string args,string cwd){
  Write($"kind={kind}\nrunning");
  var info=new ProcessStartInfo(exe,args){WorkingDirectory=cwd,UseShellExecute=false,CreateNoWindow=true,RedirectStandardOutput=true,RedirectStandardError=true};
  var output=new System.Text.StringBuilder();
  using var process=new Process{StartInfo=info};
  process.OutputDataReceived+=(_,e)=>{if(e.Data!=null)lock(output)output.AppendLine(e.Data);};
  process.ErrorDataReceived+=(_,e)=>{if(e.Data!=null)lock(output)output.AppendLine(e.Data);};
  try{process.Start();process.BeginOutputReadLine();process.BeginErrorReadLine();process.WaitForExit();}
  catch(Exception e){Write($"kind={kind}\nexit=-1\n{e}");return;}
  lock(output)Write($"kind={kind}\nexit={process.ExitCode}\n{output}");
 }
 static void Write(string text){try{File.WriteAllText(P(Result),text);}catch{}}
 // Main-thread work: bring the editor forward so it runs its update loop.
 static void Wake(string work){
  if(work!=null)mainThreadWork=work;
  try{
   var handle=Process.GetCurrentProcess().MainWindowHandle;
   if(handle!=IntPtr.Zero){if(IsIconic(handle))ShowWindow(handle,9);keybd_event(0x12,0,0,UIntPtr.Zero);keybd_event(0x12,0,2,UIntPtr.Zero);SetForegroundWindow(handle);}
  }catch{}
 }

 // Copies the end of the editor log (compile errors, exceptions).
 static void WriteEditorLog(){
  var path=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Unity","Editor","Editor.log");
  try{
   using var stream=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite);long start=Math.Max(0,stream.Length-400_000);stream.Seek(start,SeekOrigin.Begin);
   using var reader=new StreamReader(stream);File.WriteAllText(P("Logs/editor_log.txt"),reader.ReadToEnd());
   Write("kind=editorlog\nok");
  }catch(Exception e){Write("kind=editorlog\n"+e);}
 }

 // ------------------------------------------------------------------ editor main thread
 static void Tick(){
  if(EditorApplication.isPlaying&&File.Exists(P("Logs/autotest_done.txt"))){File.Delete(P("Logs/autotest_done.txt"));EditorApplication.isPlaying=false;Write("kind=play\nfinished");return;}
  if(EditorApplication.isCompiling||EditorApplication.isUpdating)return;
  if(File.Exists(P(PlayPending))&&!EditorApplication.isPlayingOrWillChangePlaymode){
   AssetDatabase.Refresh();if(EditorApplication.isCompiling)return; // compiles first; the file outlives the reload
   File.Delete(P(PlayPending));PlayerSettings.runInBackground=true;EditorApplication.isPlaying=true;Write("kind=play\nstarted");return;
  }
  var work=mainThreadWork;if(work==null)return;
  mainThreadWork=null;
  switch(work){
   case "refresh":AssetDatabase.Refresh(ImportAssetOptions.ForceUpdate);break;
   case "stop":EditorApplication.isPlaying=false;Write("kind=stop");break;
  }
 }
}
