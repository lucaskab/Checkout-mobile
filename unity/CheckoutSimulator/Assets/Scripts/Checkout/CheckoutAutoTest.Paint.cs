using System.Collections;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Unity.Profiling;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Checkout {
 // "Cores do mercado" (CheckoutMarketPaint), on the QA copy of the save (the word "events"):
 //  - "eventspaintcompare[-mesinha.banca…]": every stage from the player's camera and close on the shop, in Clássico,
 //    Floresta, Cereja, Grafite and a custom pair, rendered at the iPhone's 2778x1284: Logs/pc_<stage>_<view>_<palette>.jpg.
 //    PAINT lines: renderers and materials painted, the time a full paint pass takes, and the materials left alone.
 //  - "eventspaintperf[-hipermercado]": frame time, main thread, batches and SetPass for 10 s in Clássico, then 10 s painted.
 //  - "eventspaintui-<lang>-<phone|mini>": the picker as a player uses it (CheckoutAutoTest.PaintUi below).
 public sealed partial class CheckoutAutoTest {
  static readonly (string id,string p,string a)[] ComparePalettes={("classico","1D2B4F","D3A53D"),("floresta","1F4D36","E3C77A"),("cereja","8A1C2B","D9A93E"),("grafite","2E3236","BFC5CC"),("custom","C2185B","00B8D4")};

  IEnumerator Paint(string request){
   if(request.StartsWith("eventspaintui"))return PaintUi(request);
   if(request.StartsWith("eventspaintperf"))return PaintPerf(request);
   if(request.StartsWith("eventspaintkit"))return PaintKit(request);
   return PaintCompare(request);
  }

  IEnumerator GoToStage(string stage){
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
   yield return new WaitForSecondsRealtime(6);
   var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();
   yield return new WaitForSecondsRealtime(2f);
  }

  IEnumerator PaintCompare(string request){
   var parts=request.Split('-');
   var stages=parts.Length>1?parts[1].Split('.'):new[]{"mesinha","banca","conteiner","spati","mercadinho","supermercado","hipermercado"};
   foreach(var st in stages)foreach(var f in Directory.GetFiles("Logs","pc_"+st+"_*.jpg"))File.Delete(f);
   var paint=CheckoutMarketPaint.Active;if(!paint){Note("PAINT no CheckoutMarketPaint");yield break;}
   var fx=FindAnyObjectByType<CheckoutEventVisuals>();if(fx&&fx.Previewing)fx.Preview("");
   foreach(var stage in stages){
    yield return GoToStage(stage);
    bool small=CheckoutStall.Small;var shell=FindAnyObjectByType<CheckoutMarketShell>();
    var fp=small?CheckoutStall.Footprint:shell?shell.Footprint:new Bounds(Vector3.zero,Vector3.one*20);
    Note($"PAINT {stage}: era={bridge.State?.era?.id} small={small} footprint {fp.center} {fp.size}");
    foreach(var (id,p,a) in ComparePalettes){
     var watch=Stopwatch.StartNew();paint.Preview(p,a);watch.Stop();
     yield return new WaitForSecondsRealtime(.6f);
     if(id!="classico")Note($"PAINT {stage} {id}: {paint.PaintedRenderers} renderers, {paint.PaintedMaterials} painted materials, first pass {watch.Elapsed.TotalMilliseconds:0.0} ms");
     CaptureSized($"pc_{stage}_home_{id}",2778,1284,null,0);
     float size=Mathf.Max(fp.size.x,fp.size.z)*(small?1.7f:1.05f)+1;
     CaptureSized($"pc_{stage}_close_{id}",2778,1284,new Vector3(fp.center.x,small?.6f:.8f,fp.center.z-(small?.4f:0)),size);
     // The storage building of the stage (stock room or central warehouse), when there is one.
     if(paint.StorageBounds(out var depot)){CaptureSized($"pc_{stage}_storage_{id}",2778,1284,new Vector3(depot.center.x,.8f,depot.center.z),Mathf.Max(depot.size.x,depot.size.z)*1.3f);if(id=="classico")Note($"PAINT {stage}: storage at {depot.center} size {depot.size}");}
    }
    if(stage==stages[0])LogUnpainted();
    paint.EndPreview();yield return new WaitForSecondsRealtime(.5f);
   }
   LogUnpainted();
  }

  // Every Interior Kit piece (fixtures, sectors, checkouts, decor) laid out on the supermarket floor, shot from above in
  // each palette ("eventspaintkit"): the QA copy of the save has no furniture, so this is where the fixtures are checked.
  // Shots Logs/pk_<part>_<palette>.jpg; the pieces are removed after.
  IEnumerator PaintKit(string request){
   foreach(var f in Directory.GetFiles("Logs","pk_*.jpg"))File.Delete(f);
   var paint=CheckoutMarketPaint.Active;var world=GameObject.Find("Supermarket World");
   if(!paint||!world){Note("PAINT kit: no paint or world");yield break;}
   yield return GoToStage("supermercado");
   var kit=world.transform.Find("Interior Kit");var holderT=GameObject.Find("Market Interior")?.transform;
   var layout=FindAnyObjectByType<CheckoutMarketLayout>();
   if(!kit||!holderT||!layout){Note($"PAINT kit: kit={kit} holder={holderT} layout={layout}");yield break;}
   var floor=CheckoutMarketShell.ClearRect(layout.State);
   var show=new GameObject("QA paint kit").transform;show.SetParent(holderT,false);
   var templates=kit.Cast<Transform>().Where(t=>!t.name.StartsWith("staff")).OrderBy(t=>t.name).ToList();
   int cols=Mathf.CeilToInt(Mathf.Sqrt(templates.Count*floor.width/Mathf.Max(1,floor.height)));int rows=Mathf.CeilToInt(templates.Count/(float)cols);
   float dx=floor.width/cols,dz=floor.height/rows;
   for(int i=0;i<templates.Count;i++){
    var go=Instantiate(templates[i].gameObject,show);go.name="QA "+templates[i].name;go.SetActive(true);
    var piece=go.GetComponent<CheckoutInteriorPiece>();float w=piece?Mathf.Max(piece.max.x-piece.min.x,piece.max.y-piece.min.y):1.8f;
    float k=Mathf.Min(1f,Mathf.Min(dx,dz)*.9f/Mathf.Max(.5f,w));go.transform.localScale*=k;
    go.transform.position=new Vector3(floor.xMin+dx*(i%cols+.5f),.74f,floor.yMax-dz*(i/cols+.5f));
   }
   Note($"PAINT kit: {templates.Count} pieces on a {cols}x{rows} grid over {floor}: {string.Join(",",templates.Select(t=>t.name))}");
   var cam=Camera.main;var center=new Vector3(floor.center.x,.8f,floor.center.y);
   foreach(var (id,p,a) in ComparePalettes){
    paint.Preview(p,a);yield return new WaitForSecondsRealtime(.4f);paint.Scan();yield return new WaitForSecondsRealtime(.4f);
    CaptureSized($"pk_all_{id}",2778,1284,center,Mathf.Max(floor.width,floor.height)*1.05f);
    CaptureSized($"pk_left_{id}",2778,1284,new Vector3(floor.xMin+floor.width*.27f,.8f,floor.center.y),floor.width*.55f);
    CaptureSized($"pk_right_{id}",2778,1284,new Vector3(floor.xMin+floor.width*.73f,.8f,floor.center.y),floor.width*.55f);
    if(id=="floresta"){var lines=new List<string>();foreach(var r in show.GetComponentsInChildren<MeshRenderer>())foreach(var m in r.sharedMaterials)if(m&&m.name.EndsWith("(paint)"))lines.Add(r.transform.root==null?"":(r.GetComponentInParent<CheckoutInteriorPiece>()?.name??r.name)+": "+m.name);
     Note("PAINT kit painted ("+lines.Distinct().Count()+"):\n  "+string.Join("\n  ",lines.Distinct().OrderBy(x=>x)));}
   }
   paint.EndPreview();Destroy(show.gameObject);yield return new WaitForSecondsRealtime(.5f);
  }

  // The market's materials the paint leaves alone that still look navy or gold (to review false negatives).
  void LogUnpainted(){
   var world=GameObject.Find("Supermarket World");if(!world)return;
   var seen=new HashSet<string>();var lines=new List<string>();
   foreach(var root in new[]{"Market Shell","Market Stage Dressing","Market Interior"}){
    var t=world.transform.Find(root);if(!t)continue;
    foreach(var r in t.GetComponentsInChildren<MeshRenderer>(false))foreach(var m in r.sharedMaterials){
     if(!m||!seen.Add(m.name))continue;
     int kind=CheckoutMarketPaint.Classify(m,out _);bool isCopy=m.name.EndsWith("(paint)");
     var key=m.HasProperty("_Color")?CheckoutMarketPaint.Key(m.color.linear):Vector2.zero;
     lines.Add($"{(isCopy?"P":kind==0?"-":"?")} {m.name} [{m.shader.name}] tex={(m.HasProperty("_MainTex")&&m.mainTexture?m.mainTexture.name:"none")} navy={key.x:0.00} gold={key.y:0.00}");
    }
   }
   foreach(Transform child in world.transform)if(child.name.StartsWith("Era"))foreach(var r in child.GetComponentsInChildren<MeshRenderer>(false))foreach(var m in r.sharedMaterials)if(m&&seen.Add(m.name))lines.Add($"{(m.name.EndsWith("(paint)")?"P":"-")} {m.name} [{m.shader.name}] (stall)");
   Note("PAINT materials in the market ("+lines.Count+"):\n  "+string.Join("\n  ",lines.OrderBy(l=>l)));
  }

  IEnumerator PaintPerf(string request){
   var parts=request.Split('-');var stage=parts.Length>1?parts[1]:"hipermercado";
   var paint=CheckoutMarketPaint.Active;if(!paint){Note("PAINT no CheckoutMarketPaint");yield break;}
   yield return GoToStage(stage);
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-open\",\"action\":\"setMarketOpen\",\"args\":[true]}");
   yield return new WaitForSecondsRealtime(4);
   int quality=QualitySettings.GetQualityLevel();QualitySettings.SetQualityLevel(2,true);
   for(int round=0;round<2;round++){
    foreach(var (label,p,a) in new[]{("classico","1D2B4F","D3A53D"),("floresta","1F4D36","E3C77A")}){
     paint.Preview(p,a);yield return new WaitForSecondsRealtime(1.5f);
     yield return Measure($"PERF {stage} {label} (round {round+1})",10);
    }
   }
   double full=0,worst=0,sum=0;for(int i=0;i<5;i++)full+=paint.Scan();for(int i=0;i<20;i++){var ms=paint.QaStep();sum+=ms;worst=System.Math.Max(worst,ms);}
   Note($"PERF {stage}: a full paint pass {full/5:0.00} ms (first paint only); the periodic step (one root every 0.5 s while painted) avg {sum/20:0.00} ms, worst {worst:0.00} ms; {paint.PaintedRenderers} renderers, {paint.PaintedMaterials} painted materials");
   paint.EndPreview();QualitySettings.SetQualityLevel(quality,true);
  }

  IEnumerator Measure(string label,float seconds){
   var main=ProfilerRecorder.StartNew(ProfilerCategory.Internal,"Main Thread",1);var render=ProfilerRecorder.StartNew(ProfilerCategory.Render,"Camera.Render",1);
   var batches=ProfilerRecorder.StartNew(ProfilerCategory.Render,"Batches Count",1);var setpass=ProfilerRecorder.StartNew(ProfilerCategory.Render,"SetPass Calls Count",1);
   var frames=new List<double>();var mains=new List<double>();var renders=new List<double>();long b=0,s=0;int n=0;
   float end=Time.realtimeSinceStartup+seconds;
   while(Time.realtimeSinceStartup<end){yield return null;frames.Add(Time.unscaledDeltaTime*1000.0);if(main.Valid)mains.Add(main.LastValue*1e-6);if(render.Valid)renders.Add(render.LastValue*1e-6);b+=batches.LastValue;s+=setpass.LastValue;n++;}
   main.Dispose();render.Dispose();batches.Dispose();setpass.Dispose();
   double P(List<double> v,double q){if(v.Count==0)return 0;var o=v.OrderBy(x=>x).ToList();return o[Mathf.Clamp((int)(q*o.Count),0,o.Count-1)];}
   Note($"{label}: {n} frames · frame avg {frames.Average():0.00} ms p95 {P(frames,.95):0.00} · main thread avg {(mains.Count>0?mains.Average():0):0.00} ms · Camera.Render avg {(renders.Count>0?renders.Average():0):0.00} ms · batches {b/(double)Mathf.Max(1,n):0} · SetPass {s/(double)Mathf.Max(1,n):0}");
  }

  // The picker as a player uses it ("eventspaintui-<lang>-<phone|mini>[-<stage>]", QA copy of the save): from Loja ›
  // Decoração, a palette, a custom colour (swatch + hue bar), apply with coins, another palette applied with diamonds,
  // back to the classic look for free, a preview cancelled, the price with too few coins, and the build mode's "Cores".
  // Shots Logs/at_paint_<lang>_<device>_<nn>_<step>.png; PAINTUI lines with the wallet before and after each step.
  IEnumerator PaintUi(string request){
   var parts=request.Split('-');string lang=parts.Length>1?parts[1]:"pt",device=parts.Length>2?parts[2]:"phone",stage=parts.Length>3?parts[3]:"supermercado";
   string tag=lang+"_"+device;int n=0;
   var size=device=="mini"?new Vector2Int(1792,828):device=="desk"?new Vector2Int(1600,900):new Vector2Int(2778,1284);
   Note("PAINTUI "+tag+": "+CheckoutQaGameView.Set(size.x,size.y)+" handheld="+CheckoutScreen.Handheld);
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Lang(string l){CheckoutI18n.SetLanguage(l);CheckoutBridge.Emit("{\"kind\":\"language\",\"lang\":\""+l+"\"}");}
   var before=CheckoutI18n.Language;Lang(lang);
   yield return GoToStage(stage);
   var paint=CheckoutMarketPaint.Active;if(!paint){Note("PAINTUI no CheckoutMarketPaint");yield break;}
   // Money on the QA copy for the purchases (dev cheats, never the player's save).
   yield return Dev("devAdjustCoins","[200000]",()=>bridge.State.coins>=50000);
   yield return Dev("devAdjustDiamonds","[200]",()=>bridge.State.diamonds>=100);
   // Start from the classic look.
   if(!CheckoutMarketPaint.IsClassic(paint.SavedPrimary,paint.SavedAccent))yield return Dev("resetMarketPaint","[]",()=>CheckoutMarketPaint.IsClassic(paint.SavedPrimary,paint.SavedAccent));
   string Wallet()=>$"coins {bridge.State.coins:0} diamonds {bridge.State.diamonds:0} paint {bridge.State.paint?.primary}/{bridge.State.paint?.accent} ({bridge.State.paint?.palette}) prices {bridge.State.paint?.coinPrice}/{bridge.State.paint?.diamondPrice} recent {bridge.State.paint?.recent?.Length}";
   IEnumerator Step(string name){yield return new WaitForSecondsRealtime(.7f);yield return Shot($"paint_{tag}_{++n:00}_{name}");Note($"PAINTUI {tag} {name}: {CheckoutMarketPaintPanel.QaStatus} · {Wallet()}");}
   IEnumerator Press(string which){var b=CheckoutMarketPaintPanel.QaButton(which);if(!b){Note("PAINTUI missing button "+which);yield break;}Note($"PAINTUI press {which}: '{b.Data?.label}' enabled={b.Data?.enabled}");b.Clicked?.Invoke(b);for(float t=0;t<4&&CheckoutMarketPaintPanel.QaBusy;t+=.2f)yield return new WaitForSecondsRealtime(.2f);yield return new WaitForSecondsRealtime(.8f);}
   // 1. Loja › Decoração: the card, and its button.
   Route("~loja:decoracao");yield return new WaitForSecondsRealtime(2f);yield return Shot($"paint_{tag}_{++n:00}_loja_card");
   var entry=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).FirstOrDefault(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.route=="@paint");
   Note("PAINTUI loja card button: "+(entry?entry.Data.label:"MISSING"));
   if(entry)entry.Clicked?.Invoke(entry);else{Route("");CheckoutMarketPaintPanel.Show();}
   yield return new WaitForSecondsRealtime(1.5f);
   if(!CheckoutMarketPaintPanel.Open){Note("PAINTUI the picker did not open");Lang(before);yield break;}
   yield return Step("open");
   // 2. A curated palette.
   yield return Tap(CheckoutMarketPaintPanel.QaChip("floresta"));yield return Step("floresta");
   // 3. A custom colour: the accent slot, a swatch, then the hue bar.
   yield return Press("accent");yield return Tap(CheckoutMarketPaintPanel.QaSwatch(9));yield return Step("accent_swatch");
   var hueBar=CheckoutMarketPaintPanel.QaBar(true);
   if(hueBar){var r=hueBar;var from=RectTransformUtility.WorldToScreenPoint(null,r.TransformPoint(new Vector3(r.rect.xMin+r.rect.width*.1f,r.rect.center.y)));var to=RectTransformUtility.WorldToScreenPoint(null,r.TransformPoint(new Vector3(r.rect.xMin+r.rect.width*.55f,r.rect.center.y)));
    var data=new PointerEventData(EventSystem.current){position=from,pressPosition=from,button=PointerEventData.InputButton.Left};
    ExecuteEvents.Execute(r.gameObject,data,ExecuteEvents.pointerDownHandler);for(int i=1;i<=10;i++){data.position=Vector2.Lerp(from,to,i/10f);ExecuteEvents.Execute(r.gameObject,data,ExecuteEvents.dragHandler);yield return null;}
    ExecuteEvents.Execute(r.gameObject,data,ExecuteEvents.pointerUpHandler);}
   yield return Press("primary");yield return Step("custom");
   yield return Press("inside");yield return Step("custom_inside");
   if(CheckoutMarketPaintPanel.QaButton("storage")&&CheckoutMarketPaintPanel.QaButton("storage").gameObject.activeInHierarchy){yield return Press("storage");yield return Step("custom_storage");}
   yield return Press("front");
   // 4. Apply with coins.
   double coins0=bridge.State.coins,gems0=bridge.State.diamonds;
   yield return Press("coins");yield return Step("applied_coins");
   Note($"PAINTUI coins paid {coins0-bridge.State.coins:0} (price {bridge.State.paint?.coinPrice}), diamonds paid {gems0-bridge.State.diamonds:0}");
   // 5. Another palette with diamonds.
   coins0=bridge.State.coins;gems0=bridge.State.diamonds;
   yield return Tap(CheckoutMarketPaintPanel.QaChip("cereja"));yield return Step("cereja_preview");
   yield return Press("diamonds");yield return Step("applied_diamonds");
   Note($"PAINTUI diamonds paid {gems0-bridge.State.diamonds:0} (price {bridge.State.paint?.diamondPrice}), coins paid {coins0-bridge.State.coins:0}");
   // 6. Back to the classic look, free.
   coins0=bridge.State.coins;gems0=bridge.State.diamonds;
   yield return Press("classic");yield return Step("classic_free");
   Note($"PAINTUI back to classic paid coins {coins0-bridge.State.coins:0} diamonds {gems0-bridge.State.diamonds:0}; saved {paint.SavedPrimary}/{paint.SavedAccent}");
   // 7. A preview cancelled: the market goes back.
   yield return Tap(CheckoutMarketPaintPanel.QaChip("grafite"));yield return Step("grafite_preview");
   yield return Press("cancel");yield return new WaitForSecondsRealtime(1f);yield return Shot($"paint_{tag}_{++n:00}_cancelled");
   Note($"PAINTUI after cancel: open={CheckoutMarketPaintPanel.Open} shown {paint.ShownPrimary}/{paint.ShownAccent} saved {paint.SavedPrimary}/{paint.SavedAccent}");
   // 8. Too few coins: the coin button says what is missing (the wallet goes back after).
   double had=bridge.State.coins;yield return Dev("devAdjustCoins","["+(-(long)had+50)+"]",()=>bridge.State.coins<=60);
   CheckoutMarketPaintPanel.Show();yield return new WaitForSecondsRealtime(1f);yield return Tap(CheckoutMarketPaintPanel.QaChip("oceano"));yield return Step("short_of_coins");
   yield return Press("coins");yield return Step("short_of_coins_tapped");
   yield return Press("cancel");yield return Dev("devAdjustCoins","["+((long)had-50)+"]",()=>bridge.State.coins>=had-1);
   // 9. The build mode's tray has "Cores".
   CheckoutBuildMode.OpenFromHud();yield return new WaitForSecondsRealtime(2f);yield return Shot($"paint_{tag}_{++n:00}_build_tray");
   var cores=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).FirstOrDefault(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.label=="Cores"&&b.GetComponentInParent<CheckoutBuildMode>());
   Note("PAINTUI build tray Cores: "+(cores?"present":"MISSING"));
   if(cores){cores.Clicked?.Invoke(cores);yield return new WaitForSecondsRealtime(1.5f);yield return Step("from_build_mode");yield return Press("cancel");yield return new WaitForSecondsRealtime(.8f);yield return Shot($"paint_{tag}_{++n:00}_back_in_build_mode");}
   CheckoutBuildMode.QaClose();
   Route("");Lang(before);yield return new WaitForSecondsRealtime(1.5f);
   Note("PAINTUI done; language back to "+CheckoutI18n.Language);
  }

  // A shot of the player's camera (target null) or of a close camera on `target`, at w x h.
  void CaptureSized(string name,int w,int h,Vector3? target,float size){
   var main=Camera.main;if(!main){Note("no camera");return;}
   var go=new GameObject("QA paint camera");var cam=go.AddComponent<Camera>();cam.CopyFrom(main);
   if(main.GetComponent<CheckoutEdgeFog>())go.AddComponent<CheckoutEdgeFog>();
   cam.aspect=(float)w/h;
   if(target.HasValue){float dist=size*2.2f;go.transform.rotation=main.transform.rotation;go.transform.position=target.Value-main.transform.forward*dist;
    if(cam.orthographic)cam.orthographicSize=size*.5f;else cam.fieldOfView=2*Mathf.Atan(size*.5f/dist)*Mathf.Rad2Deg;cam.nearClipPlane=.3f;cam.farClipPlane=dist+200;}
   var rt=new RenderTexture(w,h,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;
   var image=new Texture2D(w,h,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,w,h),0,0);image.Apply();RenderTexture.active=active;
   File.WriteAllBytes("Logs/"+name+".jpg",image.EncodeToJPG(85));Destroy(image);cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(go);
  }
 }
}
