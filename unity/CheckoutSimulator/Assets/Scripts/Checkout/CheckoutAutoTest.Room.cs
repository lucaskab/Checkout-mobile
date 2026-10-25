using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // Room audit ("eventsroom-spati.quitanda..."): for each expansion, every piece of shop furniture the player can own
 // there (the shelves of that expansion, its sectors, the extra checkout and the kiosks) starts in the inventory and
 // goes in one by one, each tried along the walls first, the way a tidy player would furnish the shop. Logs which
 // pieces find no room (Logs/room_<stage>.txt) and a plan shot (Logs/room_<stage>.jpg). Runs on the QA copy of the save.
 public sealed partial class CheckoutAutoTest {
  // Expansion index from which each piece can be bought (src/data/shelf-types.ts, src/data/production-sectors.ts).
  static readonly Dictionary<string,int> ShelfEra=new Dictionary<string,int>{{"produce",0},{"drinks",0},{"bakery",1},{"dairy",2},{"snacks",3},{"coffee",4},{"pizza",5},{"home",6},{"icecream",8}};
  static readonly Dictionary<string,int> SectorEra=new Dictionary<string,int>{{"padaria",7},{"queijaria",8},{"acougue",8},{"bebidas",8},{"peixaria",9},{"sorvetes",9},{"adega",9}};
  static readonly string[] EraIds={"mesinha","tenda","banca","conteiner","spati","quitanda","minimercado","mercadinho","supermercado","hipermercado","rede"};
  string summaryGate="";int roomEra=-1;bool roomExtras,roomKeepInterior;

  void PatchRoom(Snapshot s){
   if(roomEra<0)return;
   if(s.shelves!=null)foreach(var x in s.shelves){x.unlocked=ShelfEra.TryGetValue(x.id,out var e)&&e<=roomEra;x.building=false;}
   if(s.sectors!=null)foreach(var x in s.sectors){x.unlocked=SectorEra.TryGetValue(x.id,out var e)&&e<=roomEra;x.building=false;}
   s.builds=System.Array.Empty<BuildEntry>();
   var owned=(s.ownedItems??System.Array.Empty<string>()).Where(i=>i!=CheckoutLanes.ExtraItem&&i!=CheckoutLanes.SelfItem).ToList();
   if(roomExtras){owned.Add(CheckoutLanes.ExtraItem);if(roomEra>=8)owned.Add(CheckoutLanes.SelfItem);}
   s.ownedItems=owned.ToArray();
   var ids=new List<string>{"checkout:main"};
   if(roomExtras){ids.Add("checkout:extra");if(roomEra>=8){ids.Add("kiosk:1");ids.Add("kiosk:2");}}
   if(s.shelves!=null)ids.AddRange(s.shelves.Where(x=>x.unlocked).Select(x=>"shelf:"+x.id));
   if(s.sectors!=null)ids.AddRange(s.sectors.Where(x=>x.unlocked).Select(x=>"sector:"+x.id));
   if(roomKeepInterior)return;
   s.interior=new InteriorState{items=ids.Select(i=>new InteriorItem{id=i,type=i.Split(':')[0],stored=true}).ToArray(),owned=System.Array.Empty<DecorOwned>()};
  }

  IEnumerator RoomAudit(string request){
   var parts=request.Split('-');var stages=parts.Length>1?parts[1].Split('.'):new[]{"spati","quitanda","minimercado","mercadinho","supermercado","hipermercado","rede"};
   var summary=new List<string>();
   foreach(var stage in stages){
    int era=System.Array.IndexOf(EraIds,stage);if(era<0){Note("unknown stage "+stage);continue;}
    foreach(var extras in new[]{false,true}){
     var inside=CheckoutInterior.Active;if(inside)inside.editing=false;
     roomEra=era;roomExtras=extras;
     CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-room-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
     yield return new WaitForSecondsRealtime(extras?6:18);
     inside=CheckoutInterior.Active;if(!inside){Note("no interior");continue;}
     inside.editing=true;yield return new WaitForSecondsRealtime(.5f);
     var lines=new List<string>();var floor=inside.FloorRect;
     lines.Add($"stage {stage} extras={extras} small={CheckoutStall.Small} shopInside={CheckoutStall.ShopInside} yard={CheckoutStall.Yard} floor {floor} ({floor.width:0.0}x{floor.height:0.0} m) checkout zone {inside.CheckoutZone}");
     lines.Add("waiting: "+string.Join(", ",inside.waiting.Keys));
     // Counters first (as the build mode orders them), then shelves in buying order, then sectors.
     var order=inside.waiting.Keys.OrderBy(k=>k.StartsWith("checkout")||k.StartsWith("kiosk")?0:k.StartsWith("shelf")?1:2)
      .ThenBy(k=>k.StartsWith("shelf:")&&ShelfEra.TryGetValue(k.Substring(6),out var e)?e:0).ThenBy(k=>k).ToList();
     // Start points: along the walls first (back wall, then the sides), then the middle of the shop.
     var starts=new List<Vector3>();
     for(float z=floor.yMax-1;z>floor.yMin;z-=.75f)for(float x=floor.xMin+1;x<floor.xMax;x+=.75f)starts.Add(new Vector3(x,CheckoutInterior.Floor,z));
     float Wall(Vector3 p)=>Mathf.Min(Mathf.Min(p.x-floor.xMin,floor.xMax-p.x),floor.yMax-p.z);
     starts=starts.OrderBy(p=>Mathf.Round(Wall(p)*2)/2).ThenBy(p=>-p.z).ThenBy(p=>p.x).ToList();
     int ok=0;var missing=new List<string>();
     foreach(var id in order){
      if(!inside.waiting.ContainsKey(id))continue;
      bool counter=id.StartsWith("checkout")||id.StartsWith("kiosk");
      CheckoutInterior.Item placed=null;string why="no fitting spot";int tries=0;
      var points=counter?new List<Vector3>{new Vector3(inside.CheckoutZone.center.x,CheckoutInterior.Floor,floor.yMin+2)}.Concat(starts.Take(12)).ToList():starts;
      foreach(var p in points){
       if(++tries>36)break;
       var it=inside.PlaceWaiting(id,p);
       if(it==null){why="no fitting spot";break;}// Settle already searched the whole shop
       if(inside.Reachable(out var blocked)){placed=it;break;}
       why="blocks the way to "+(blocked!=null?blocked.id:"?");inside.Unplace(it);
      }
      if(placed!=null){ok++;lines.Add($"placed {id} at ({placed.root.position.x:0.00},{placed.root.position.z:0.00}) rot {placed.rot:0} after {tries} tries");}
      else{missing.Add(id);lines.Add($"NO ROOM {id}: {why}");}
     }
     var roomMap=FindAnyObjectByType<CheckoutMap>();if(roomMap){roomMap.FurnitureChanged(false);roomMap.SaveInterior();}
     yield return new WaitForSecondsRealtime(1);
     // The buy gate (CheckoutInterior.Room.cs): with this floor, which next pieces have no room?
     roomKeepInterior=true;inside.MarkPending();inside.editing=false;
     for(float t=0;t<6;t+=.5f)yield return new WaitForSecondsRealtime(.5f);
     lines.Add("room gate: "+inside.RoomSent);summaryGate=inside.RoomSent;
     if(!extras)yield return Shot("room_hud_"+stage);
     inside.editing=true;
     var c=floor.center;TopDown(new Vector3(c.x,0,c.y),Mathf.Max(floor.width,floor.height)+3,$"room_{stage}{(extras?"_x":"")}");
     File.WriteAllLines($"Logs/room_{stage}{(extras?"_x":"")}.txt",lines);
     summary.Add($"{stage}{(extras?" +extras":"")}: {ok}/{order.Count} placed{(missing.Count>0?"; NO ROOM: "+string.Join(", ",missing):"")}; gate {summaryGate}");roomKeepInterior=false;
     Note(summary[summary.Count-1]);
    }
   }
   File.WriteAllLines("Logs/room_summary.txt",summary);
   roomEra=-1;var last=CheckoutInterior.Active;if(last)last.editing=false;
  }
 // The bakery puzzle ("trayplay-<recipe>"): opens the recipe's tray step, shows it, places half the doughs the way the
 // deal solves it, then the rest, and shoots each moment (Logs/at_tray_*.png).
 IEnumerator TrayPlay(string request){
  var recipe=request.Contains("-")?request.Substring(request.IndexOf('-')+1):"croissant-premium";
  CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\"kitchen:"+recipe+":0\"}");
  yield return new WaitForSecondsRealtime(3);
  yield return Shot("tray_"+recipe+"_0");
  var hud=FindAnyObjectByType<CheckoutDesktopHUD>();if(!hud){Note("no HUD");yield break;}
  int placed=0;for(int i=0;i<3&&hud.QaTrayPlace();i++){placed++;yield return new WaitForSecondsRealtime(.5f);}
  yield return Shot("tray_"+recipe+"_1");
  while(hud.QaTrayPlace()){placed++;yield return new WaitForSecondsRealtime(.35f);}
  yield return new WaitForSecondsRealtime(.6f);
  yield return Shot("tray_"+recipe+"_2");
  Note("tray "+recipe+" placed "+placed);
  yield return new WaitForSecondsRealtime(2.5f);
  yield return Shot("tray_"+recipe+"_3");
  CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\"\"}");
 }
 // The sector puzzles ("kitchenshot-<recipe>.<recipe>…"): opens each recipe's first step and shoots it (Logs/at_kitchen_*.png).
 IEnumerator KitchenShots(string request){
  var recipes=request.Contains("-")?request.Substring(request.IndexOf('-')+1).Split('.'):new string[0];
  foreach(var recipe in recipes){
   CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\"kitchen:"+recipe+":0\"}");
   yield return new WaitForSecondsRealtime(3.5f);
   yield return Shot("kitchen_"+recipe);
   CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\"\"}");
   yield return new WaitForSecondsRealtime(1);
  }
 }
 // The checkout after an expansion ("eventscounter-spati.quitanda.minimercado.mercadinho", QA save): with the checkout and the
 // shelves in the inventory (as a new game has them), logs whether the build mode would ask for the checkout and, where
 // the player places it, whether it finds a spot (a tester got stuck at an expansion, 24/10).
 IEnumerator CounterCheck(string request){
  var stages=request.Contains("-")?request.Substring(request.IndexOf('-')+1).Split('.'):new[]{"spati","quitanda","minimercado","mercadinho"};
  foreach(var stage in stages){
   int era=System.Array.IndexOf(EraIds,stage);if(era<0)continue;
   var inside=CheckoutInterior.Active;if(inside)inside.editing=false;
   roomEra=era;roomExtras=false;
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-counter-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
   yield return new WaitForSecondsRealtime(18);
   inside=CheckoutInterior.Active;if(!inside){Note("no interior");continue;}
   bool ownCounter=CheckoutStall.Small&&!CheckoutStall.PlacedCounter;
   bool waits=inside.waiting.Values.Any(w=>w.type=="checkout");
   string placed="-";
   if(waits&&!ownCounter){inside.editing=true;var z=inside.CheckoutZone;var it=inside.PlaceWaiting("checkout:main",new Vector3(z.center.x,CheckoutInterior.Floor,z.center.y));placed=it!=null?"placed at "+it.root.position:"NO ROOM";inside.editing=false;}
   Note($"counter {stage}: own counter={ownCounter} checkout waiting={waits} -> {placed}; waiting: {string.Join(",",inside.waiting.Keys)}");
  }
  roomEra=-1;
 }
  // Build-mode grid on every stage ("eventsgrid-mesinha.tenda...", QA save): opens the build mode with a piece selected and
 // logs the grid height against the floor under it and the feet of the shop's pieces, with a close and a low shot, so
 // the grid and the green/red footprint can be checked lying on the floor, under the furniture.
 IEnumerator GridCheck(string request){
  var stages=request.Contains("-")?request.Substring(request.IndexOf('-')+1).Split('.'):EraIds;
  foreach(var stage in stages){
   int era=System.Array.IndexOf(EraIds,stage);if(era<0)continue;
   var inside=CheckoutInterior.Active;if(inside)inside.editing=false;
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-grid-"+stage+"\",\"action\":\"devSetMarketEra\",\"args\":[\""+stage+"\"]}");
   yield return new WaitForSecondsRealtime(18);
   inside=CheckoutInterior.Active;if(!inside){Note("no interior");continue;}
   // A shop with every piece still waiting (the QA save): place one, so the footprint and the feet can be checked.
   if(!inside.items.Values.Any(i=>i.root&&i.functional&&!i.outside)&&inside.waiting.Count>0){
    var key=inside.waiting.Keys.FirstOrDefault(k=>k.StartsWith("shelf:"))??inside.waiting.Keys.First();var fr=inside.FloorRect;
    inside.editing=true;var put=inside.PlaceWaiting(key,new Vector3(fr.center.x,CheckoutInterior.FloorHere,fr.center.y));inside.editing=false;
    Note($"grid {stage}: placed {key} for the check -> {(put!=null?put.root.position.ToString("F3"):"no room")}");
   }
   bool open=CheckoutBuildMode.QaOpenAndSelect();yield return new WaitForSecondsRealtime(1.5f);
   float gy=CheckoutInterior.FloorHere;var floor=inside.FloorRect;
   // Highest surface under a few floor points that is not a piece of furniture (the floor itself).
   var pieces=new HashSet<Transform>(inside.items.Values.Where(i=>i.root).Select(i=>i.root));
   bool OfPiece(Transform t){for(;t;t=t.parent)if(pieces.Contains(t))return true;return false;}
   var floorHits=new List<string>();
   foreach(var f in new[]{new Vector2(.3f,.3f),new Vector2(.5f,.5f),new Vector2(.7f,.6f)}){
    var o=new Vector3(Mathf.Lerp(floor.xMin,floor.xMax,f.x),gy+3,Mathf.Lerp(floor.yMin,floor.yMax,f.y));
    var hits=Physics.RaycastAll(o,Vector3.down,6).Where(h=>!OfPiece(h.transform)).OrderBy(h=>h.distance).ToArray();
    floorHits.Add(hits.Length>0?$"{hits[0].point.y:0.000}({hits[0].collider.name})":"none");
   }
   // The shop model has no colliders: give its meshes temporary ones and drop rays on the floor (slab top).
   if(CheckoutStall.ShopInside){
    var model=FindObjectsByType<MeshFilter>(FindObjectsSortMode.None).Where(m=>m.gameObject.activeInHierarchy&&m.sharedMesh&&m.GetComponentsInParent<Transform>().Any(t=>t.name.StartsWith("Era"+CheckoutStall.Era+"_"))).ToList();
    var temp=new List<MeshCollider>();foreach(var m in model){var mc=m.gameObject.AddComponent<MeshCollider>();mc.sharedMesh=m.sharedMesh;temp.Add(mc);}
    Physics.SyncTransforms();var tops=new List<string>();
    foreach(var f in new[]{new Vector2(.25f,.3f),new Vector2(.5f,.5f),new Vector2(.75f,.7f),new Vector2(.4f,.8f)}){
     var o=new Vector3(Mathf.Lerp(floor.xMin,floor.xMax,f.x),gy+2.5f,Mathf.Lerp(floor.yMin,floor.yMax,f.y));
     var hit=temp.Select(c=>c.Raycast(new Ray(o,Vector3.down),out var h,6)?h:(RaycastHit?)null).Where(h=>h.HasValue).Select(h=>h.Value).OrderBy(h=>h.distance).ToList();
     tops.Add(hit.Count>0?string.Join(">",hit.Take(3).Select(h=>$"{h.point.y:0.000}({h.collider.name})")):"none");
    }
    foreach(var mc in temp)Destroy(mc);
    Note($"grid {stage} model meshes {model.Count}, floor surface: {string.Join(" ",tops)}");
   }
   var feet=inside.items.Values.Where(i=>i.root&&!i.outside).Select(i=>{var rs=i.root.GetComponentsInChildren<Renderer>();return rs.Length>0?rs.Min(r=>r.bounds.min.y):i.root.position.y;}).ToList();
   string feetText=feet.Count>0?$"min {feet.Min():0.000} max {feet.Max():0.000} roots {inside.items.Values.Where(i=>i.root&&!i.outside).Select(i=>i.root.position.y).DefaultIfEmpty(0).Min():0.000}":"no pieces";
   Note($"grid {stage}: open={open} small={CheckoutStall.Small} grid y={gy+.012f:0.000} floor hits {string.Join(" ",floorHits)}; feet {feetText}");
   var c=floor.center;var at=new Vector3(c.x,gy,c.y);
   CaptureAt(at,Mathf.Max(floor.width,floor.height)+1.5f,$"grid_{stage}");
   var sel=inside.items.Values.FirstOrDefault(i=>i.root&&i.functional&&!i.outside);
   LowShot(sel!=null?sel.root.position:at,sel!=null?4.5f:Mathf.Min(floor.width,floor.height),$"grid_{stage}_low");
   CheckoutBuildMode.QaClose();yield return new WaitForSecondsRealtime(1);
  }
 }
 // A low camera (about 20 degrees above the floor) looking at a point: shows whether a flat overlay lies on the floor.
 void LowShot(Vector3 target,float size,string name){
  var main=Camera.main;if(!main){Note("no camera");return;}
  var go=new GameObject("QA low camera");var cam=go.AddComponent<Camera>();cam.CopyFrom(main);cam.orthographic=false;
  var flat=Vector3.ProjectOnPlane(main.transform.forward,Vector3.up).normalized;if(flat.sqrMagnitude<.1f)flat=Vector3.forward;
  float dist=size*1.8f;var dir=(flat*Mathf.Cos(20*Mathf.Deg2Rad)-Vector3.up*Mathf.Sin(20*Mathf.Deg2Rad)).normalized;
  go.transform.position=target+Vector3.up*.4f-dir*dist;go.transform.rotation=Quaternion.LookRotation(dir);
  cam.fieldOfView=2*Mathf.Atan(size*.5f/dist)*Mathf.Rad2Deg;cam.nearClipPlane=.05f;cam.farClipPlane=dist+80;
  var rt=new RenderTexture(1280,800,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;
  var image=new Texture2D(1280,800,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1280,800),0,0);image.Apply();RenderTexture.active=active;
  File.WriteAllBytes("Logs/"+name+".jpg",image.EncodeToJPG(82));Destroy(image);cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(go);Note("shot "+name);
 }
  // A look at what Lucas asked about on 25/10 ("eventslook", QA save): every ruin on the locked lots, the mercadinho's
 // entrance (which parts are see-through) and any renderer whose transform is sheared (a skewed car).
 IEnumerator LookAround(string request){
  yield return new WaitForSecondsRealtime(6);
  int n=0;
  foreach(var b in CheckoutLotSites.Obstacles.ToList()){
   CaptureAt(b.center,Mathf.Max(b.size.x,b.size.z)*1.5f+2,$"look_lot_{n}");
   LowShot(new Vector3(b.center.x,b.min.y,b.center.z),Mathf.Max(b.size.x,b.size.z)*1.2f,$"look_lot_{n}_low");n++;
  }
  Note($"look: {n} ruins");
  var awning=GameObject.Find("S0 door awning");
  if(awning){
   var at=awning.transform.position;CaptureAt(at,9,"look_front");CaptureAt(at,5,"look_front_close");
   foreach(var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)){
    if(!r.enabled||!r.gameObject.activeInHierarchy||Vector3.Distance(r.bounds.center,at)>6)continue;
    var shaders=string.Join("/",r.sharedMaterials.Where(m=>m).Select(m=>m.shader.name+(m.HasProperty("_Fade")?"("+m.GetFloat("_Fade").ToString("0.0")+")":"")));
    Note($"front {TPath(r.transform)}: {shaders}");
   }
  }else Note("look: no S0 door awning");
  // Sheared transforms: the world axes of the object are not at right angles (a rotated child under a parent
  // scaled unevenly). Logged once per top object.
  var seen=new HashSet<Transform>();
  foreach(var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None)){
   if(!r.gameObject.activeInHierarchy)continue;var m=r.transform.localToWorldMatrix;
   Vector3 x=((Vector3)m.GetColumn(0)).normalized,y=((Vector3)m.GetColumn(1)).normalized,z=((Vector3)m.GetColumn(2)).normalized;
   float shear=Mathf.Max(Mathf.Abs(Vector3.Dot(x,y)),Mathf.Abs(Vector3.Dot(y,z)),Mathf.Abs(Vector3.Dot(x,z)));
   if(shear<.02f)continue;var top=r.transform;while(top.parent&&top.parent.parent)top=top.parent;
   if(!seen.Add(top)&&seen.Count>60)continue;
   Note($"shear {shear:0.000} {TPath(r.transform)}");
  }
  // The city's cars: a close shot of each one that is out on the road.
  int c=0;
  foreach(var traffic in FindObjectsByType<CheckoutCityTraffic>(FindObjectsSortMode.None))
   foreach(var v in traffic.vehicles)if(v&&v.gameObject.activeInHierarchy&&c<8){CaptureAt(v.position+Vector3.up*.6f,4,$"look_car_{c++}");Note($"car {c-1}: {TPath(v)} rot {v.eulerAngles} scale {v.lossyScale}");}
  // The neighbourhood cars (the yellow van among them), each seen from straight above too: the body must line up
  // with its driving direction (Lucas 25/10: the van looked "italic").
  foreach(var hood in FindObjectsByType<CheckoutNeighborhoodTraffic>(FindObjectsSortMode.None))
   foreach(var car in hood.cars){var v=car?.vehicle;if(!v||!v.gameObject.activeInHierarchy)continue;
    CaptureAt(v.position+Vector3.up*.6f,5,$"look_hood_{c}");ShotFrom(v.position+Vector3.up*9,v.position,$"look_hood_{c}_top",v.forward);
    Note($"hood car {c}: {TPath(v)} visual {(v.childCount>0?v.GetChild(0).name+" "+v.GetChild(0).localEulerAngles:"-")}");c++;}
  // The lot clearing scene with the new Casa (the same scene the game builds), far from the map.
  var lots=FindAnyObjectByType<CheckoutLotSites>();
  if(lots){
   // "eventslook-casa,loja,oficina": one clearing scene after the other.
   var ruins=(request.Contains("-")?request.Substring(request.IndexOf('-')+1):"casa").Split(',');
   foreach(var ruin in ruins){
   var origin=new Vector3(900,0,900);var root=lots.PreviewClearing(ruin,origin,24f);
   var eye=origin+new Vector3(-9f,9.5f,-13.5f);var look=origin+Vector3.up*1.2f;
   float t0=Time.realtimeSinceStartup;
   foreach(var at in new[]{.5f,6f,12f,18f,23.5f}){while(Time.realtimeSinceStartup-t0<at)yield return null;ShotFrom(eye,look,$"look_clear_{ruin}_{at:0}",Vector3.up);}
   // Close-ups of what is carried away: the skip and a rubble heap (bits of the ruin itself on them).
   if(root){
    var skipLoad=root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t=>t.name.StartsWith("Skip rubble"));
    if(skipLoad){var at2=skipLoad.parent?skipLoad.position:skipLoad.position;ShotFrom(at2+new Vector3(-1.6f,2.2f,-2.2f),at2,$"look_clear_{ruin}_skip",Vector3.up);}
    int dressedCount=root.GetComponentsInChildren<Transform>(true).Count(t=>t.name=="Ruin rubble");Note($"clear {ruin}: ruin rubble bits {dressedCount}");
    var heapBit=root.GetComponentsInChildren<Transform>(false).FirstOrDefault(t=>t.name=="Ruin rubble"&&t.parent&&!t.parent.name.StartsWith("Skip rubble"));
    if(heapBit){var hp=heapBit.parent.position;ShotFrom(hp+new Vector3(-1.4f,1.8f,-2f),hp,$"look_clear_{ruin}_heap",Vector3.up);}
    Destroy(root);
   }
   yield return null;
   }
  }else Note("look: no CheckoutLotSites");
 }
 // A picture from `eye` towards `look` with its own camera (away from the map: no fog, no main-camera framing).
 void ShotFrom(Vector3 eye,Vector3 look,string name,Vector3 up){
  var go=new GameObject("QA free camera");var cam=go.AddComponent<Camera>();
  go.transform.position=eye;go.transform.rotation=Quaternion.LookRotation(look-eye,up);
  cam.fieldOfView=42;cam.nearClipPlane=.2f;cam.farClipPlane=200;cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=new Color(.93f,.92f,.88f);
  var rt=new RenderTexture(1280,800,24){antiAliasing=4};cam.targetTexture=rt;cam.Render();var active=RenderTexture.active;RenderTexture.active=rt;
  var image=new Texture2D(1280,800,TextureFormat.RGB24,false);image.ReadPixels(new Rect(0,0,1280,800),0,0);image.Apply();RenderTexture.active=active;
  File.WriteAllBytes("Logs/"+name+".jpg",image.EncodeToJPG(82));Destroy(image);cam.targetTexture=null;rt.Release();Destroy(rt);Destroy(go);Note("shot "+name);
 }
 static string TPath(Transform t){var s=t.name;for(var p=t.parent;p;p=p.parent)s=p.name+"/"+s;return s;}
 }
}
