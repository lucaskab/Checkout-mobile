using System;
using System.Collections;
using System.IO;
using UnityEngine;

namespace Checkout {
 // Every event recorded for Lucas's review (06/11: "grava todos os eventos acontecendo para eu ver um por um e te indicar
 // o que você precisa melhorar"). "eventsvideo-<stage>" (default mercadinho, where all 19 can happen; "eventsvideo-<stage>-<id>"
 // for one): the market switches to the stage on the QA copy of the save and each event's scene runs (the visuals'
 // preview, the same scene the game shows), the game camera on the scene's focus: 9 s close, then 6 s wider.
 // One video per event, 30 fps: Logs/evv_<nn>_<id>.mjpg (JPEG frames back to back, ffmpeg reads them).
 public partial class CheckoutAutoTest {
  IEnumerator EventVideos(string request){
   var fx=FindAnyObjectByType<CheckoutEventVisuals>();if(!fx){Note("no CheckoutEventVisuals");yield break;}
   var parts=request.Split('-');var stage=parts.Length>1&&parts[1]!=""?parts[1]:"mercadinho";
   string only=parts.Length>2?string.Join("-",parts,2,parts.Length-2):null;
   foreach(var f in Directory.GetFiles("Logs","evv_*.mjpg"))File.Delete(f);
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
   yield return new WaitForSecondsRealtime(6);
   // open, so customers walk in and out as in the game
   if(!bridge.State.isOpen){CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-open\",\"action\":\"setMarketOpen\",\"args\":[true]}");for(float t=0;t<6&&!bridge.State.isOpen;t+=.5f)yield return new WaitForSecondsRealtime(.5f);}
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();
   Note($"stage {stage}: era={bridge.State?.era?.id} open={bridge.State.isOpen}");
   int n=0;
   foreach(var id in CheckoutEventVisuals.EventIds){
    n++;
    if(only!=null&&id!=only)continue;
    fx.Preview(id);yield return new WaitForSecondsRealtime(1.5f);
    var focus=fx.FocusOf(id);
    if(home)home.Focus(new Vector3(focus.x,0,focus.z),12);
    yield return new WaitForSecondsRealtime(.6f);
    RecStart($"Logs/evv_{n:00}_{id}.mjpg");
    yield return Frames(9f);
    if(home)home.Focus(new Vector3(focus.x,0,focus.z-1.5f),20);
    yield return Frames(6f);
    RecStop();
    Note($"event {n:00} {id}: focus {focus}");
    fx.Preview("");yield return new WaitForSecondsRealtime(.8f);
   }
   if(home)home.HomeCamera();
  }
 }
}
