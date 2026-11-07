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
   // "eventsvideo-<stage>-furnished": a player's shop first (shelves placed and built, two checkouts, a cashier and a
   // stock clerk, market open with customers), then only the events that happen at or in the shop.
   bool furnished=only=="furnished";if(furnished)only=null;
   // "...-furnished-<id>-close": the furnished shop, then the close stills of one event.
   if(only!=null&&only.StartsWith("furnished-")){furnished=true;only=only.Substring(10);}
   // "...-<id>-close": no video, three close stills of the scene (Logs/evc_<id>_<n>.jpg), to look at the assets.
   bool close=only!=null&&only.EndsWith("-close");if(close)only=only.Substring(0,only.Length-6);
   string[] shopEvents={"quinto-dia-util","cafe-com-a-equipe","fim-do-mes","maquininha-fora-do-ar","queda-de-energia","turno-puxado","vigilancia-sanitaria"};
   if(!close)foreach(var f in Directory.GetFiles("Logs",furnished?"evv_*_loja.mjpg":"evv_*.mjpg"))File.Delete(f);
   int seq=0;void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-evv-"+(++seq)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   if(furnished){
    Act("resetGame","[]");yield return new WaitForSecondsRealtime(4f);
    Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1.5f);
    Act("setMarketLevel","[40]");
    Act("grantCurrencyPurchase","[{\"coins\":20000000,\"diamonds\":5000,\"transactionId\":\"qa-evv-"+DateTime.Now.Ticks+"\"}]");
    yield return new WaitForSecondsRealtime(2f);Act("dismissLevelUp","[]");
   }
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
   yield return new WaitForSecondsRealtime(6);
   if(furnished){
    var inside0=CheckoutInterior.Active;
    for(float t=0;t<8&&(inside0==null||bridge.State?.era?.id!=stage);t+=.5f){yield return new WaitForSecondsRealtime(.5f);inside0=CheckoutInterior.Active;}
    yield return new WaitForSecondsRealtime(3.5f);
    for(int k=0;k<9;k++){Act("unlockNextShelf","[]");yield return new WaitForSecondsRealtime(.7f);}
    Act("purchaseShopItem","[\"extra-checkout\",\"coins\"]");yield return new WaitForSecondsRealtime(2f);
    var inside=CheckoutInterior.Active;var fl=inside.FloorRect;int put=0;
    foreach(var key in new System.Collections.Generic.List<string>(inside.waiting.Keys)){
     if(key.StartsWith("sector:"))continue;
     CheckoutInterior.Item it=null;
     for(float pz=fl.yMin+1.2f;it==null&&pz<fl.yMax-.6f;pz+=.8f)
      for(float px=fl.xMin+.8f;it==null&&px<fl.xMax-.6f;px+=.8f)
       it=inside.PlaceWaiting(key,new Vector3(px,0,pz));
     if(it!=null&&inside.Reachable(out _))put++;else if(it!=null){inside.waiting[key]=(it.type,it.template);Destroy(it.root.gameObject);inside.items.Remove(key);}
    }
    inside.MarkPending();FindAnyObjectByType<CheckoutMap>().SaveInterior();yield return new WaitForSecondsRealtime(2.5f);
    Act("devFinishInteriorConstructions","[]");yield return new WaitForSecondsRealtime(3f);
    Act("hireEmployee","[\"cashier\"]");Act("hireEmployee","[\"cashier\"]");Act("hireEmployee","[\"stock_clerk\"]");yield return new WaitForSecondsRealtime(1.5f);
    Note($"furnished: {put} pieces placed");
   }
   // open, so customers walk in and out as in the game
   if(!bridge.State.isOpen){CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-open\",\"action\":\"setMarketOpen\",\"args\":[true]}");for(float t=0;t<6&&!bridge.State.isOpen;t+=.5f)yield return new WaitForSecondsRealtime(.5f);}
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();
   if(furnished)yield return new WaitForSecondsRealtime(20f);   // customers come in
   yield return CloseCardsSettled();
   Note($"stage {stage}: era={bridge.State?.era?.id} open={bridge.State.isOpen}");
   int n=0;
   foreach(var id in CheckoutEventVisuals.EventIds){
    n++;
    if(only!=null&&id!=only)continue;
    if(furnished&&Array.IndexOf(shopEvents,id)<0)continue;
    yield return CloseCardsSettled();
    fx.Preview(id);yield return new WaitForSecondsRealtime(1.5f);
    var focus=fx.FocusOf(id);
    if(close&&home){
     for(int k=0;k<3;k++){home.FocusCinematic(new Vector3(focus.x+(k-1)*.8f,0,focus.z),k==1?3.2f:4.5f);yield return new WaitForSecondsRealtime(2.5f);yield return new WaitForEndOfFrame();File.WriteAllBytes($"Logs/evc_{id}_{k}.jpg",RecJpg(2400,88));}
     Note($"event {n:00} {id}: close stills");fx.Preview("");yield return new WaitForSecondsRealtime(.8f);continue;
    }
    if(home)home.Focus(new Vector3(focus.x,0,focus.z),12);
    yield return new WaitForSecondsRealtime(.6f);
    RecStart($"Logs/evv_{n:00}_{id}{(furnished?"_loja":"")}.mjpg");
    yield return Frames(9f);
    if(home)home.Focus(new Vector3(focus.x,0,focus.z-1.5f),20);
    yield return Frames(6f);
    RecStop();
    Note($"event {n:00} {id}: focus {focus}");
    fx.Preview("");yield return new WaitForSecondsRealtime(.8f);
   }
   if(home)home.HomeCamera();
  }

  // The celebration cards ("Móvel pronto!" for each shelf built, level-ups) one after another, so none covers the video.
  IEnumerator CloseCardsSettled(){
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();if(!hud)yield break;
   int quiet=0;
   for(int i=0;i<60&&quiet<4;i++){
    yield return new WaitForSecondsRealtime(.6f);
    if(!hud.LevelUpOpen&&!hud.ConquestOpen){quiet++;continue;}
    quiet=0;hud.QaCloseCelebrations();
   }
  }
 }
}
