#if UNITY_EDITOR
using System.Collections;
using System.IO;
using UnityEngine;

namespace Checkout {
 // Editor QA of the market day pages (Lucas 29/10, special requests removed): the day side panel while the day runs
 // and the end-of-day results, in Portuguese and English. It runs only when Logs/day_qa.txt exists, next to an
 // "eventshud-@dismissDiamondShortfall..." autotest that keeps play mode up on the QA copy of the save (the "events"
 // prefix), so the player's own save is never touched. Shots: Logs/dayqa_*.jpg; notes: Logs/dayqa_log.txt.
 public sealed class CheckoutDayQa:MonoBehaviour {
  const string Flag="Logs/day_qa.txt",LogFile="Logs/dayqa_log.txt";
  [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
  static void Boot(){
   if(!File.Exists(Flag))return;
   File.Delete(Flag);
   var go=new GameObject("CheckoutDayQa");DontDestroyOnLoad(go);go.AddComponent<CheckoutDayQa>();
  }

  CheckoutBridge bridge;
  void Note(string s){try{File.AppendAllText(LogFile,$"{Time.realtimeSinceStartup:0.0}s {s}\n");}catch{}}
  static void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
  static void Hud(string id,string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"dayqa-"+id+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
  static void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
  string Phase()=>bridge?.State?.day?.phase??"";

  IEnumerator Shot(string name){
   yield return new WaitForEndOfFrame();
   var shot=ScreenCapture.CaptureScreenshotAsTexture();
   try{File.WriteAllBytes("Logs/dayqa_"+name+".jpg",shot.EncodeToJPG(82));}finally{Destroy(shot);}
   Note("shot "+name);
  }
  IEnumerator Both(string name,string route){
   foreach(var l in new[]{"pt","en"}){Lang(l);yield return new WaitForSecondsRealtime(2f);Route(route);yield return new WaitForSecondsRealtime(1.6f);yield return Shot(name+"_"+l);}
  }

  IEnumerator Start(){
   try{File.WriteAllText(LogFile,"");}catch{}
   for(float t=0;t<120&&(bridge==null||bridge.State?.shelves==null);t+=.5f){bridge=FindAnyObjectByType<CheckoutBridge>();yield return new WaitForSecondsRealtime(.5f);}
   if(bridge?.State==null){Note("no snapshot");yield break;}
   yield return new WaitForSecondsRealtime(6f);
   var before=CheckoutI18n.Language;
   Note($"phase {Phase()} day {bridge.State.day?.dayNumber} qa {CheckoutStartMenu.QaMode} language {before}");
   if(!CheckoutStartMenu.QaMode){Note("not on the QA save copy: stop");yield break;}
   if(Phase()=="results"){yield return Both("results_before","!day-result");Hud("claim","claimDayResult","[]");yield return new WaitForSecondsRealtime(2f);}
   if(Phase()=="planning"){
    yield return Both("planning","!day");
    foreach(var id in new[]{"caixa-cheio","casa-cheia","margem-boa","clientes-sorrindo"}){if(Phase()!="planning")break;Hud("start-"+id,"startDay","[\""+id+"\"]");yield return new WaitForSecondsRealtime(1.5f);}
    if(Phase()=="planning"){Hud("open","setMarketOpen","[true]");yield return new WaitForSecondsRealtime(1.5f);}
   }
   Note($"phase now {Phase()} contract '{bridge.State.day?.contractTitle}'");
   Route("");yield return new WaitForSecondsRealtime(15f); // a few customers come in
   yield return Shot("hud_open");
   yield return Both("open","!day");
   Hud("close","closeDay","[]");
   for(float t=0;t<60&&Phase()!="results";t+=1)yield return new WaitForSecondsRealtime(1);
   Note($"phase after closing {Phase()} grade {bridge.State.day?.grade}");
   yield return Both("results","!day-result");
   Route("");Lang(before);yield return new WaitForSecondsRealtime(1f);
   Note("done, language back to "+CheckoutI18n.Language);
  }
 }
}
#endif
