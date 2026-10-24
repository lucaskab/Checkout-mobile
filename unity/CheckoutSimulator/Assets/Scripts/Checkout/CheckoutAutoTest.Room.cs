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
 }
}
