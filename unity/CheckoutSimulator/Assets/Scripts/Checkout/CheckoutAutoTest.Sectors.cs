using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEngine;

namespace Checkout {
 // The special sectors one expansion earlier (Lucas 04/11) in the Editor ("eventssectors-phone"; "events…" runs on the
 // QA copy of the save, which this scenario starts over with "Reiniciar jogo": the player's own save is never touched).
 // For each expansion that now brings sectors (minimercado: padaria; mercadinho: queijaria, açougue, bebidas;
 // supermercado: peixaria, sorvetes, adega): the sectors are offered (the room check finds a spot for each), bought,
 // placed where the build mode settles them (logged in design coordinates, for CheckoutMapDesign), every counter and the
 // queue still reachable from the door, shot while the works run and once built. Shots Logs/at_ps_*.png at the
 // iPhone's landscape size; RESULT lines in Logs/autotest_log.txt.
 public sealed partial class CheckoutAutoTest {
  IEnumerator Sectors(string request){
   int seq=0;
   void Act(string action,string args)=>CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-sectors-"+(++seq)+"-"+Time.frameCount+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   void Result(string name,bool ok,string detail="")=>Note($"RESULT sectors {name}: {(ok?"PASS":"FAIL")} {detail}");
   var hud=FindAnyObjectByType<CheckoutDesktopHUD>();
   // (the level-up card of the jump to level 40 and the one-off tips would cover the shots: closed on the copy)
   IEnumerator Tips(){Act("dismissLevelUp","[]");for(int i=0;i<4&&hud&&hud.CoachQa().isTip;i++){Act("dismissOnboardingTip","[]");yield return new WaitForSecondsRealtime(.5f);}yield return new WaitForSecondsRealtime(.6f);}
   const BindingFlags F=BindingFlags.NonPublic|BindingFlags.Instance;

   Note("sectors: "+CheckoutQaGameView.Set(2778,1284)+" handheld="+CheckoutScreen.Handheld);
   yield return new WaitForSecondsRealtime(3f);
   // A clean QA copy: a new game, moved to each expansion with the dev tools (the copy only).
   Act("resetGame","[]");yield return new WaitForSecondsRealtime(4f);
   Act("skipOnboarding","[]");Act("claimDayResult","[]");yield return new WaitForSecondsRealtime(1.5f);
   Act("setMarketLevel","[40]");
   Act("grantCurrencyPurchase","[{\"coins\":20000000,\"diamonds\":5000,\"transactionId\":\"qa-sectors-"+System.DateTime.Now.Ticks+"\"}]");
   yield return new WaitForSecondsRealtime(2f);yield return Tips();

   var plan=new (string era,string[] ids)[]{("minimercado",new[]{"padaria"}),("mercadinho",new[]{"queijaria","acougue","bebidas"}),("supermercado",new[]{"peixaria","sorvetes","adega"})};
   var spots=new List<string>();
   foreach(var (era,ids) in plan){
    yield return GoToStage(era);yield return Tips();
    var inside=CheckoutInterior.Active;
    for(float t=0;t<8&&(inside==null||bridge.State?.era?.id!=era);t+=.5f){yield return new WaitForSecondsRealtime(.5f);inside=CheckoutInterior.Active;}
    // wait for the room check of this floor (every 1.5 s)
    yield return new WaitForSecondsRealtime(3.5f);
    var all=ids.Concat(plan.TakeWhile(p=>p.era!=era).SelectMany(p=>p.ids)).ToArray();
    // Furnished like a player's shop of this expansion first: every shelf it sells and the second checkout, placed
    // where the build mode settles them and built. The sectors must still find room after that.
    for(int k=0;k<9;k++){Act("unlockNextShelf","[]");yield return new WaitForSecondsRealtime(.7f);}
    Act("purchaseShopItem","[\"extra-checkout\",\"coins\"]");yield return new WaitForSecondsRealtime(2f);
    inside=CheckoutInterior.Active;
    {
     var fl=inside.FloorRect;int put=0;var missing=new List<string>();
     foreach(var key in inside.waiting.Keys.Where(k=>!k.StartsWith("sector:")).OrderBy(k=>k.StartsWith("checkout")?0:1).ThenBy(k=>k).ToList()){
      CheckoutInterior.Item it=null;
      for(float pz=fl.yMin+1.2f;it==null&&pz<fl.yMax-.6f;pz+=.8f)
       for(float px=fl.xMin+.8f;it==null&&px<fl.xMax-.6f;px+=.8f)
        it=inside.PlaceWaiting(key,new Vector3(px,0,pz));
      if(it!=null&&inside.Reachable(out _))put++;else{if(it!=null){inside.waiting[key]=(it.type,it.template);Destroy(it.root.gameObject);inside.items.Remove(key);}missing.Add(key);}
     }
     inside.MarkPending();FindAnyObjectByType<CheckoutMap>().SaveInterior();yield return new WaitForSecondsRealtime(2.5f);
     Act("devFinishInteriorConstructions","[]");yield return new WaitForSecondsRealtime(3f);
     Note($"sectors {era}: furnished with {put} pieces placed [{string.Join(",",CheckoutInterior.Active.items.Values.Where(i=>i.root&&!i.outside&&i.type!="sector").Select(i=>i.id))}]; not placed [{string.Join(",",missing)}]");
     yield return new WaitForSecondsRealtime(3.5f);
    }
    inside=CheckoutInterior.Active;
    var offered=bridge.State.sectors?.Where(x=>x!=null&&ids.Contains(x.id)).ToList()??new List<Sector>();
    Note($"sectors {era}: stage {inside?.LayoutState?.stage} floor {inside?.FloorRect} small {CheckoutStall.Small}; room blocked {inside?.RoomSent}; layout sectors [{string.Join(",",inside?.LayoutState?.sectorIds??new string[0])}]");
    Result($"{era}: the layout has room for {string.Join(", ",ids)}",ids.All(id=>inside!=null&&inside.LayoutState.sectorIds!=null&&inside.LayoutState.sectorIds.Contains(id))&&ids.All(id=>!(inside.RoomSent??"").Contains("sector:"+id)),$"blocked {inside?.RoomSent}");
    // The Produção page as the player sees it now (the new sectors on sale).
    Route("!sectors");yield return new WaitForSecondsRealtime(2f);yield return Tips();
    yield return ShotJpg("ps_"+era+"_setores");
    Route("");yield return new WaitForSecondsRealtime(1f);
    // Buy each (it waits in the build-mode inventory), then place it where the build mode settles it.
    foreach(var id in ids){Act("buildSector","[\""+id+"\",\"coins\"]");yield return new WaitForSecondsRealtime(1.2f);}
    yield return new WaitForSecondsRealtime(2f);
    inside=CheckoutInterior.Active;var floor=inside.FloorRect;
    var defaults=typeof(CheckoutInterior).GetMethod("DefaultFor",F);
    foreach(var id in ids){
     string key="sector:"+id;
     CheckoutInterior.Item placed=inside.waiting.ContainsKey(key)?null:inside.Get(key);
     // first where the map design / built-in default puts it, then along the floor
     if(placed==null&&defaults!=null){var args=new object[]{key,1f};var d=(Vector3)defaults.Invoke(inside,args);var world=inside.WorldOf(d.x,d.z);if(floor.Contains(new Vector2(world.x,world.z)))placed=inside.PlaceWaiting(key,world);}
     for(float pz=floor.yMax-1.8f;placed==null&&pz>floor.yMin+1.5f;pz-=1f)
      for(float px=floor.xMin+2f;placed==null&&px<floor.xMax-2f;px+=1f)
       placed=inside.PlaceWaiting(key,new Vector3(px,0,pz));
     string fits="";if(placed!=null){inside.Fits(placed,placed.root.position,placed.rot,out var why);fits=why??"ok";}
     var line=placed!=null?$"{era} {key} x={placed.x:0.000} z={placed.z:0.000} rot={placed.rot:0} world={placed.root.position:0.00} template={placed.template} fits={fits}":$"{era} {key} NOT PLACED";
     Note("sectors spot "+line);spots.Add(line);
    }
    bool reach=inside.Reachable(out var blocked);
    Result($"{era}: placed and every counter, shelf and the queue still reachable",ids.All(id=>inside.Get("sector:"+id)!=null)&&reach,reach?"":"blocked by "+blocked?.id);
    inside.MarkPending();FindAnyObjectByType<CheckoutMap>().SaveInterior();yield return new WaitForSecondsRealtime(3f);
    var building=bridge.State.sectors?.Where(x=>x!=null&&ids.Contains(x.id)).Select(x=>x.id+(x.building?":building":x.unlocked?":built":":-")).ToArray()??new string[0];
    Note($"sectors {era}: after placing [{string.Join(",",building)}], builds [{string.Join(",",(bridge.State.builds??new BuildEntry[0]).Select(b=>b.kind+":"+b.targetId+(b.pending?"(pending)":"")+" "+((b.endsAt-b.startedAt)/60000)+"min"))}]");
    var home=FindAnyObjectByType<MarketDay.MarketSimulation>();if(home)home.HomeCamera();yield return new WaitForSecondsRealtime(1.2f);
    CaptureJpg("ps_"+era+"_obras",floor);yield return ShotJpg("ps_"+era+"_obras_hud");
    Act("devFinishInteriorConstructions","[]");yield return new WaitForSecondsRealtime(3.5f);
    var built=ids.Where(id=>bridge.State.sectors?.FirstOrDefault(x=>x?.id==id)?.unlocked==true).ToArray();
    Result($"{era}: built ({string.Join(", ",ids)})",built.Length==ids.Length,$"built [{string.Join(",",built)}]");
    inside=CheckoutInterior.Active;bool reach2=inside.Reachable(out var blocked2);
    Result($"{era}: built, the shop still walkable",reach2,reach2?"":"blocked by "+blocked2?.id);
    yield return new WaitForSecondsRealtime(1.5f);
    CaptureJpg("ps_"+era+"_prontos",inside.FloorRect);
    // the sectors already built from the expansions before stand there too (nothing is lost on the way up)
    Note($"sectors {era}: standing [{string.Join(",",inside.items.Values.Where(i=>i.root&&i.type=="sector").Select(i=>i.id))}] (expected at least {string.Join(",",all)})");
   }
   File.WriteAllLines("Logs/sectors_spots.txt",spots);
   Route("");yield return new WaitForSecondsRealtime(1f);
  }

  // The screen as the player sees it (HUD included) at the game view's size, as JPG (the Mac's disk is nearly full: a
  // PNG of this size is ~4 MB, the JPG ~0.5 MB; the QA converts it to PNG off the Mac).
  IEnumerator ShotJpg(string name){
   yield return new WaitForEndOfFrame();
   var tex=ScreenCapture.CaptureScreenshotAsTexture();
   try{File.WriteAllBytes("Logs/at_"+name+".jpg",tex.EncodeToJPG(90));Note("shot "+name);}finally{Destroy(tex);}
   yield return new WaitForSecondsRealtime(.3f);
  }
  // A view of the shop floor from the game's camera angle, at the iPhone's landscape size (2778 x 1284), as JPG.
  void CaptureJpg(string name,Rect floor){
   var main=Camera.main;if(!main){Note("no camera");return;}
   const int w=2778,h=1284;
   var go=new GameObject("QA sectors camera");var cam=go.AddComponent<Camera>();cam.CopyFrom(main);
   if(main.GetComponent<CheckoutEdgeFog>())go.AddComponent<CheckoutEdgeFog>();
   cam.aspect=(float)w/h;
   float size=Mathf.Max(floor.width*.6f,floor.height)*(CheckoutStall.Small?1.2f:1.0f)+1;
   var target=new Vector3(floor.center.x,CheckoutInterior.FloorHere,floor.center.y);
   float dist=size*2.2f;go.transform.rotation=main.transform.rotation;go.transform.position=target-main.transform.forward*dist;
   if(cam.orthographic)cam.orthographicSize=size*.5f;else cam.fieldOfView=2*Mathf.Atan(size*.5f/dist)*Mathf.Rad2Deg;cam.nearClipPlane=.3f;cam.farClipPlane=dist+200;
   var dressing=GameObject.Find("Supermarket World/Market Stage Dressing");var hidden=new List<GameObject>();
   if(dressing)foreach(Transform c in dressing.transform)if(c.gameObject.activeSelf&&(c.name.StartsWith("Bunting")||c.name.StartsWith("Pendant"))){c.gameObject.SetActive(false);hidden.Add(c.gameObject);}
   try{
    var rt=new RenderTexture(w,h,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;
    var image=new Texture2D(w,h,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,w,h),0,0);image.Apply();RenderTexture.active=active;
    File.WriteAllBytes("Logs/at_"+name+".jpg",image.EncodeToJPG(90));Destroy(image);cam.targetTexture=null;rt.Release();Destroy(rt);
    Note("shot "+name);
   }finally{Destroy(go);foreach(var g in hidden)if(g)g.SetActive(true);}
  }
 }
}
