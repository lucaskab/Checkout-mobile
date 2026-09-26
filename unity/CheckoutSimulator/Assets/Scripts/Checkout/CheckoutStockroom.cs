using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // Receiving and the stockroom (src/services/receiving.ts), in rendered art like the other mini-games.
 //  - ENTREGA: a supplier truck waits at the dock. Drag each box off the truck onto the stockroom rack
 //    of its zone (refrigerados, bebidas, hortifruti e padaria, mercearia); the wrong rack bounces it.
 //    Every box sends unloadDelivery(id, units); the goods only count as stock once unloaded.
 //  - REPOR: store shelves running low, and boxes of what the stockroom has for them. Drag a box onto
 //    the shelf that sells that product; it sends restockShelf({shelfId, productId, amount}).
 public sealed class CheckoutStockroom:MonoBehaviour {
  public static CheckoutStockroom Instance {get;private set;}
  public bool IsOpen=>window&&window.activeSelf;
  static readonly string[] Zones={"refrigerados","bebidas","hortifruti","mercearia"};
  static readonly Dictionary<string,string> ZoneNames=new Dictionary<string,string>{{"refrigerados","Refrigerados"},{"bebidas","Bebidas"},{"hortifruti","Hortifruti"},{"mercearia","Mercearia"}};
  static readonly Dictionary<string,string> ZoneColors=new Dictionary<string,string>{{"refrigerados","4FA3D9"},{"bebidas","F28C28"},{"hortifruti","5DA637"},{"mercearia","D9A032"}};

  CheckoutBridge bridge;RectTransform root,stage,dockFab,restockFab;GameObject window,hint;TextMeshProUGUI title,dockCount,restockCount;Image backdrop;
  AudioSource sound;AudioClip thud,click,ding,buzz,slide;
  readonly List<GameObject> scene=new List<GameObject>();float closeAt;

  public void Initialize(CheckoutBridge owner){
   Instance=this;bridge=owner;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.45f;
   thud=U.Tone(90,.12f,70,.7f);click=U.Tone(2200,.03f);ding=U.Tone(990,.22f,1480);buzz=U.Tone(150,.3f,110,.6f);slide=U.Noise(.14f,.1f);
   root=U.Canvas(transform,"CheckoutStockroom",82);
   dockFab=Fab("EntregaButton","ENTREGA","truck_back","2E8CAE","1F6A86",116,out dockCount,()=>OpenDock());
   restockFab=Fab("ReporButton","REPOR","cardboard_box","8B5C9E","6A4279",262,out restockCount,()=>OpenRestock());
   stage=U.GameWindow(root,"dock_backdrop",out window,out title,out backdrop,Close);
   window.SetActive(false);
  }
  void Play(AudioClip clip,float pitch=1){if(!clip)return;sound.pitch=pitch;sound.PlayOneShot(clip);}

  RectTransform Fab(string name,string label,string art,string face,string edge,float y,out TextMeshProUGUI count,Action onTap){
   var node=CheckoutDesktopCard.Node(name,root);node.anchorMin=node.anchorMax=new Vector2(0,.5f);node.pivot=new Vector2(0,.5f);node.anchoredPosition=new Vector2(16,y);node.sizeDelta=new Vector2(150,124);
   var e=node.gameObject.AddComponent<Image>();e.sprite=K.Rounded(22);e.type=Image.Type.Sliced;e.color=K.C(edge);
   var f=U.Box(node,"Face",face,20,Vector2.zero,Vector2.one);f.rectTransform.offsetMin=new Vector2(0,7);
   U.Art(f.transform,"Icon",art,new Vector2(.5f,.62f),66);
   var l=U.Label(f.transform,"Label",K.Headline,19,"FFFFFF");U.Stretch(l.rectTransform,Vector2.zero,new Vector2(1,.3f));l.text=label;
   var badge=U.Shape(node,"Badge","E15533",16,new Vector2(1,1),new Vector2(42,36),new Vector2(-6,-6));
   count=U.Label(badge.transform,"Count",K.Headline,20,"FFFFFF");U.Stretch(count.rectTransform,Vector2.zero,Vector2.one);
   U.Tap(e,onTap);node.gameObject.SetActive(false);return node;
  }

  // ------------------------------------------------------------------ common
  static Vector2 Mid=>new Vector2(.5f,.5f);
  Vector2 P(float x,float y)=>new Vector2((x-.5f)*stage.rect.width,(y-.5f)*stage.rect.height);
  Vector2 At(RectTransform t)=>U.LocalOf(stage,t);
  T Keep<T>(T c) where T:Component{scene.Add(c.gameObject);return c;}
  void Clear(){foreach(var o in scene)if(o)Destroy(o);scene.Clear();if(hint)Destroy(hint);hint=null;racks.Clear();roomLabel=null;}
  void Hint(Func<Vector2> from,Func<Vector2> to){if(hint)Destroy(hint);hint=U.Hint(this,stage,from,to);}
  void StopHint(){if(hint)Destroy(hint);hint=null;}
  void Close(){StopAllCoroutines();Clear();window.SetActive(false);closeAt=0;}
  bool OtherGameOpen=>(CheckoutCounterGame.Instance&&CheckoutCounterGame.Instance.IsOpen)||(CheckoutIncidents.Instance&&CheckoutIncidents.Instance.IsOpen);
  void OpenWindow(string backdropArt,string heading){
   window.SetActive(true);window.transform.SetAsLastSibling();StopAllCoroutines();Clear();closeAt=0;
   U.SetArt(backdrop,backdropArt);title.text=heading;Canvas.ForceUpdateCanvases();
  }
  static string Json(string s)=>"\""+s.Replace("\\","\\\\").Replace("\"","\\\"")+"\"";

  // A stockroom rack bay with its zone sign; returns the drop area and remembers where boxes go.
  sealed class Rack {public string zone;public Image image;public RectTransform[] levels;public int used;public Image sign;}
  readonly List<Rack> racks=new List<Rack>();
  Rack AddRack(string zone,Vector2 at,float height){
   var img=Keep(U.Art(stage,"Rack "+zone,"rack_bay",Mid,height));img.rectTransform.anchoredPosition=at;
   var sign=U.Art(img.transform,"Sign","zone_sign",new Vector2(.5f,1),height*.2f,new Vector2(0,height*.06f));sign.color=Color.Lerp(K.C(ZoneColors[zone]),Color.white,.15f);
   var text=U.Over(sign,"zone_sign","text");var label=U.Label(text,"Zone",K.Headline,height*.06f,"FFFFFF");U.Stretch(label.rectTransform,Vector2.zero,Vector2.one);label.text=ZoneNames[zone];label.outlineWidth=.18f;label.outlineColor=new Color32(40,30,20,160);label.enableAutoSizing=true;label.fontSizeMin=10;label.fontSizeMax=height*.06f;
   var rack=new Rack{zone=zone,image=img,sign=sign,levels=new[]{U.Over(img,"rack_bay","level0"),U.Over(img,"rack_bay","level1"),U.Over(img,"rack_bay","level2")}};
   racks.Add(rack);return rack;
  }
  // Next free spot on a rack (two per deck, bottom up); extra boxes stack on the top deck.
  Vector2 RackSpot(Rack rack,float boxHeight){
   int i=rack.used++;var level=rack.levels[Mathf.Min(2,(i/2)%3)];var c=At(level);float w=level.rect.width;
   return new Vector2(c.x+(i%2==0?-w*.24f:w*.24f),c.y-level.rect.height*.5f+boxHeight*.45f+(i>=6?(i-6)*6:0));
  }

  // A cardboard box with the product on its label and the unit count.
  RectTransform Box(int productId,int units,float size){
   var holder=Keep(CheckoutDesktopCard.Image(stage,"Box",new Color(1,1,1,0),0));holder.raycastTarget=true;U.At(holder.rectTransform,Mid,new Vector2(size*1.07f,size));
   U.Shadow(holder.rectTransform,new Vector2(size*.9f,size*.22f),new Vector2(0,size*.06f));
   var art=U.Art(holder.transform,"Carton","cardboard_box",Mid,size);
   var label=U.Over(art,"cardboard_box","label");
   U.Icon(label,"Product",$"Products/product-{productId:000}",new Vector2(.3f,.5f),Vector2.one*size*.3f);
   var count=U.Label(label,"Units",K.Headline,size*.2f,"4A3624");U.Stretch(count.rectTransform,new Vector2(.5f,0),Vector2.one);count.text="x"+units;
   count.overflowMode=TextOverflowModes.Overflow;count.enableAutoSizing=true;count.fontSizeMin=8;count.fontSizeMax=size*.2f;
   return holder.rectTransform;
  }

  // ------------------------------------------------------------------ receiving: unload the truck
  DockEntry delivery;Vector2 truckHome;int roomLeft;TextMeshProUGUI roomLabel;readonly List<RectTransform> boxes=new List<RectTransform>();Image truck;RectTransform cargo;
  public static void ShowDock(){if(Instance)Instance.OpenDock();}
  void OpenDock(){
   var dock=bridge.State?.dock;if(dock==null||dock.Length==0||OtherGameOpen)return;
   OpenWindow("dock_backdrop","Receber entrega");
   // Truck on the left; the four stockroom zones side by side in the rest of the floor.
   float W=stage.rect.width,H=stage.rect.height,truckHeight=H*.6f,truckWidth=truckHeight*U.Aspect("truck_back");
   truckHome=new Vector2(-W*.5f+W*.015f+truckWidth*.5f,-H*.06f);
   float left=truckHome.x+truckWidth*.5f+W*.02f,right=W*.49f,bay=(right-left)/Zones.Length;
   float rackHeight=Mathf.Min(H*.6f,bay*.94f/U.Aspect("rack_bay"));
   for(int i=0;i<Zones.Length;i++)AddRack(Zones[i],new Vector2(left+bay*(i+.5f),-H*.5f+H*.2f+rackHeight*.5f),rackHeight);
   LoadTruck(dock[0],false);
  }
  void LoadTruck(DockEntry next,bool driveIn){
   delivery=next;boxes.Clear();title.text="Receber entrega · "+next.productName;roomLeft=next.room;
   // Free stockroom space for this product: boxes beyond it are refused.
   if(!roomLabel){var plate=Keep(U.Shape(stage,"Room","FFF7EC",16,new Vector2(1,0),new Vector2(300,46),new Vector2(-170,40)));roomLabel=U.Label(plate.transform,"Text",K.Label,19,"4A3624");U.Stretch(roomLabel.rectTransform,Vector2.zero,Vector2.one,new Vector2(12,0),new Vector2(-12,0));}
   RoomText();
   if(truck)Destroy(truck.gameObject);
   truck=Keep(U.Art(stage,"Truck","truck_back",Mid,stage.rect.height*.6f));var home=truckHome;truck.rectTransform.anchoredPosition=driveIn?home-new Vector2(700,0):home;truck.transform.SetSiblingIndex(0);
   if(driveIn){Play(slide,.6f);StartCoroutine(U.Move(truck.rectTransform,home,.6f,true));}
   Canvas.ForceUpdateCanvases();cargo=U.Over(truck,"truck_back","cargo");
   // Boxes still in the truck, stacked from the floor of the cargo bay.
   int left=Mathf.Max(0,next.quantity-next.unloaded),size=Mathf.Max(1,next.boxUnits);var units=new List<int>();for(int l=left;l>0;l-=size)units.Add(Mathf.Min(size,l));
   // Boxes a bit wider than a third of the bay, stacked in rows of three (they overlap like a real load).
   float boxSize=Mathf.Min(cargo.rect.width/2.1f,cargo.rect.height/2.2f);
   var floor=(driveIn?home:truck.rectTransform.anchoredPosition)+(At(cargo)-truck.rectTransform.anchoredPosition)-new Vector2(0,cargo.rect.height*.5f);
   for(int i=0;i<units.Count;i++){
    int col=i%3,row=i/3;var spot=floor+new Vector2((col-1)*boxSize*.8f+(row%2==0?0:boxSize*.12f),boxSize*.42f+row*boxSize*.5f);
    var box=Box(next.productId,units[i],boxSize);box.anchoredPosition=driveIn?spot-new Vector2(700,0):spot;if(driveIn)StartCoroutine(U.Move(box,spot,.6f,true));
    boxes.Add(box);int amount=units[i];var b=box;
    var drag=U.Drag(box.GetComponent<Image>());drag.SetHome(spot);
    drag.Setup(racks.Select(r=>r.image.rectTransform).ToArray(),target=>{StopHint();return DropBox(b,amount,target);},()=>Play(thud),()=>{StopHint();Play(slide,1.4f);});
   }
   var zoneRack=racks.FirstOrDefault(r=>r.zone==next.zone);
   Hint(()=>boxes.Count>0&&boxes[boxes.Count-1]?boxes[boxes.Count-1].anchoredPosition:Vector2.zero,()=>zoneRack!=null?At(zoneRack.image.rectTransform):Vector2.zero);
  }
  bool DropBox(RectTransform box,int units,RectTransform target){
   var rack=racks.First(r=>r.image.rectTransform==target);
   if(rack.zone!=delivery.zone){
    // Wrong zone: the sign flashes red and the box goes back.
    Play(buzz);StartCoroutine(U.Shake(rack.sign.rectTransform,.35f,10));StartCoroutine(Flash(rack.sign,K.C("E15533")));
    var right=racks.FirstOrDefault(r=>r.zone==delivery.zone);if(right!=null)StartCoroutine(Flash(right.sign,Color.white));
    return false;
   }
   if(roomLeft<=0){
    // Stockroom full for this product: the box stays on the truck.
    Play(buzz,.8f);StartCoroutine(U.Shake(rack.sign.rectTransform,.35f,10));Toast("Depósito cheio de "+delivery.productName+"! Venda ou amplie o estoque.");
    return false;
   }
   box.GetComponent<CheckoutDragToken>().Locked=true;boxes.Remove(box);
   bridge.Command("unloadDelivery","["+Json(delivery.id)+","+units+"]");roomLeft-=units;RoomText();
   StartCoroutine(Shelve(box,rack));
   if(boxes.Count==0)StartCoroutine(TruckDone());
   return true;
  }
  IEnumerator Shelve(RectTransform box,Rack rack){
   var spot=RackSpot(rack,box.rect.height*.62f);
   StartCoroutine(U.Scale(box,Vector3.one*.62f,.25f));yield return U.Move(box,spot,.25f);Play(thud,1.2f+UnityEngine.Random.value*.3f);StartCoroutine(U.Pop(rack.image.rectTransform,1.03f,.2f));
   var shadow=box.Find("Shadow");if(shadow)shadow.gameObject.SetActive(false);
  }
  void RoomText(){if(roomLabel)roomLabel.text=roomLeft>0?$"Espaço no depósito: {roomLeft}":"Depósito cheio";if(roomLabel)roomLabel.color=K.C(roomLeft>0?"4A3624":"C0401F");}
  // Short message across the top of the stage.
  void Toast(string text){
   var old=scene.FirstOrDefault(o=>o&&o.name=="Toast");if(old)Destroy(old);
   var plate=Keep(U.Shape(stage,"Toast","4A3624",20,new Vector2(.5f,1),new Vector2(stage.rect.width*.62f,58),new Vector2(0,-40)));
   var label=U.Label(plate.transform,"Text",K.Headline,24,"FFFFFF");U.Stretch(label.rectTransform,Vector2.zero,Vector2.one,new Vector2(16,0),new Vector2(-16,0));label.text=text;label.enableAutoSizing=true;label.fontSizeMin=14;label.fontSizeMax=24;
   StartCoroutine(U.Pop(plate.rectTransform,1.08f,.25f));StartCoroutine(DropLater(plate.gameObject,2.4f));
  }
  IEnumerator DropLater(GameObject o,float delay){yield return new WaitForSecondsRealtime(delay);if(o)Destroy(o);}
  IEnumerator Flash(Image img,Color color){if(!img)yield break;var home=img.color;img.color=color;yield return new WaitForSecondsRealtime(.3f);if(img)img.color=home;}
  IEnumerator TruckDone(){
   yield return new WaitForSecondsRealtime(.6f);
   // Let the last unload commands land (a stale one is re-sent) before reading the live dock.
   for(float t=0;t<3&&bridge.HasPending("unloadDelivery");t+=.1f)yield return new WaitForSecondsRealtime(.1f);
   yield return new WaitForSecondsRealtime(.25f);
   // Room ran out in the stockroom: whatever did not fit stays on the truck.
   var live=bridge.State?.dock?.FirstOrDefault(d=>d.id==delivery.id);
   if(live!=null&&live.quantity-live.unloaded>0){
    // Some units did not fit: the truck waits at the dock with the rest.
    Play(buzz,.8f);Toast("Não coube tudo no depósito. O resto fica no caminhão.");
    yield return new WaitForSecondsRealtime(2.2f);closeAt=Time.unscaledTime;yield break;
   }
   Play(ding);U.Sparkles(this,stage,At(truck.rectTransform),10,200);
   Play(slide,.5f);yield return U.Move(truck.rectTransform,truck.rectTransform.anchoredPosition-new Vector2(900,0),.7f);
   yield return new WaitForSecondsRealtime(.3f);
   var next=bridge.State?.dock?.FirstOrDefault(d=>d.id!=delivery.id&&d.quantity-d.unloaded>0);
   if(next!=null)LoadTruck(next,true);else closeAt=Time.unscaledTime+.6f;
  }

  // ------------------------------------------------------------------ stockroom: refill the shelves
  sealed class ShelfCard {public RestockSlot slot;public Image image;public Image fill;public TextMeshProUGUI count;public int stock;}
  readonly List<ShelfCard> cards=new List<ShelfCard>();readonly Dictionary<int,int> reserve=new Dictionary<int,int>();
  public static void ShowRestock(){if(Instance)Instance.OpenRestock();}
  static bool Needs(RestockSlot s)=>s.reserve>0&&s.stock<s.capacity;
  void OpenRestock(){
   var slots=(bridge.State?.restockSlots??Array.Empty<RestockSlot>()).Where(Needs).OrderBy(s=>s.stock/(float)Mathf.Max(1,s.capacity)).Take(4).ToList();
   if(slots.Count==0||OtherGameOpen)return;
   OpenWindow("wall_backdrop","Repor prateleiras");cards.Clear();reserve.Clear();
   // Store shelves along the top, emptiest first.
   for(int i=0;i<slots.Count;i++){
    var s=slots[i];var card=new ShelfCard{slot=s,stock=s.stock};
    card.image=Keep(U.Art(stage,"Shelf "+s.slotId,"shelf_unit",Mid,stage.rect.height*.3f));card.image.rectTransform.anchoredPosition=P(.5f+(i-(slots.Count-1)/2f)*.235f,.77f);
    var spot=U.Over(card.image,"shelf_unit","spot");U.Icon(spot,"Product",$"Products/product-{s.productId:000}",Mid,Vector2.one*Mathf.Min(spot.rect.height,spot.rect.width)*.8f);
    var plate=U.Shape(card.image.rectTransform,"Plate","FFF7EC",14,new Vector2(.5f,0),new Vector2(card.image.rectTransform.rect.width*.86f,54),new Vector2(0,-24));
    var shelfLabel=U.Label(plate.transform,"Name",K.Label,15,"4A3624",TextAlignmentOptions.TopLeft);U.Stretch(shelfLabel.rectTransform,Vector2.zero,Vector2.one,new Vector2(10,4),new Vector2(-10,-4));shelfLabel.text=s.shelfName;
    var track=U.Box(plate.transform,"Track","EADBC4",8,new Vector2(.04f,.14f),new Vector2(.7f,.44f));
    card.fill=U.Box(track.transform,"Fill","5DA637",8,Vector2.zero,Vector2.one);
    card.count=U.Label(plate.transform,"Count",K.Number,16,"4A3624",TextAlignmentOptions.Right);U.Stretch(card.count.rectTransform,new Vector2(.7f,0),new Vector2(1,.6f),Vector2.zero,new Vector2(-10,0));
    Refresh(card);cards.Add(card);reserve[s.productId]=s.reserve;
   }
   // The stockroom racks below, one per zone that has something to bring out.
   var zones=Zones.Where(z=>slots.Any(s=>s.zone==z)).ToList();
   for(int i=0;i<zones.Count;i++)AddRack(zones[i],P(.5f+(i-(zones.Count-1)/2f)*.2f,.215f),stage.rect.height*.36f);
   foreach(var card in cards)SpawnStockBox(card.slot.productId);
   var first=scene.LastOrDefault(o=>o&&o.name=="Box");
   Hint(()=>first?((RectTransform)first.transform).anchoredPosition:Vector2.zero,()=>At(cards[0].image.rectTransform));
  }
  void Refresh(ShelfCard card){
   float ratio=card.stock/(float)Mathf.Max(1,card.slot.capacity);
   card.fill.rectTransform.anchorMax=new Vector2(Mathf.Clamp01(ratio),1);card.fill.color=Color.Lerp(K.C("E15533"),K.C("5DA637"),Mathf.InverseLerp(.15f,.6f,ratio));
   card.count.text=card.stock+"/"+card.slot.capacity;
  }
  // One box for a product, on the rack of its zone (if the stockroom still has it and a shelf wants it).
  void SpawnStockBox(int productId){
   var card=cards.FirstOrDefault(c=>c.slot.productId==productId&&c.stock<c.slot.capacity);
   if(card==null||!reserve.TryGetValue(productId,out var left)||left<=0)return;
   if(scene.Any(o=>o&&o.name=="Box"&&o.TryGetComponent<CheckoutStockBox>(out var tagged)&&tagged.productId==productId))return;
   var rack=racks.FirstOrDefault(r=>r.zone==card.slot.zone);if(rack==null)return;
   int units=Mathf.Min(6,left);float size=stage.rect.height*.12f;
   var box=Box(productId,units,size);box.anchoredPosition=RackSpot(rack,size*.9f);box.gameObject.AddComponent<CheckoutStockBox>().productId=productId;
   box.localScale=Vector3.zero;StartCoroutine(U.Scale(box,Vector3.one,.3f,true));
   var drag=U.Drag(box.GetComponent<Image>());drag.SetHome(box.anchoredPosition);
   drag.Setup(cards.Select(c=>c.image.rectTransform).ToArray(),target=>{StopHint();return DropStock(box,productId,units,target);},()=>Play(thud),()=>{StopHint();Play(slide,1.4f);});
  }
  bool DropStock(RectTransform box,int productId,int units,RectTransform target){
   var card=cards.First(c=>c.image.rectTransform==target);
   if(card.slot.productId!=productId){Play(buzz);StartCoroutine(U.Shake(target,.3f,8));return false;}
   // Live numbers: customers and clerks may have changed the shelf since the screen opened.
   var live=bridge.State?.restockSlots?.FirstOrDefault(s=>s.slotId==card.slot.slotId);if(live!=null)card.stock=live.stock;
   int amount=Mathf.Min(units,card.slot.capacity-card.stock,reserve[productId]);
   if(amount<=0){Play(buzz);StartCoroutine(U.Shake(target,.3f,8));return false;}
   box.GetComponent<CheckoutDragToken>().Locked=true;
   bridge.Command("restockShelf","[{\"shelfId\":"+Json(card.slot.slotId)+",\"productId\":"+productId+",\"amount\":"+amount+"}]");
   card.stock+=amount;reserve[productId]-=amount;
   StartCoroutine(IntoShelf(box,card));
   return true;
  }
  IEnumerator IntoShelf(RectTransform box,ShelfCard card){
   var to=At(card.image.rectTransform);StartCoroutine(U.Scale(box,Vector3.one*.3f,.3f));yield return U.Move(box,to,.3f);
   Destroy(box.gameObject);Play(click,1.2f);Play(thud,1.5f);StartCoroutine(U.Pop(card.image.rectTransform,1.06f,.25f));Refresh(card);U.Sparkles(this,stage,to,5,90);
   SpawnStockBox(card.slot.productId);
   if(!scene.Any(o=>o&&o.name=="Box")){Play(ding);yield return new WaitForSecondsRealtime(.4f);var ok=Keep(U.Icon(stage,"Done","Icons/success",Mid,new Vector2(180,180)));ok.rectTransform.localScale=Vector3.zero;StartCoroutine(U.Scale(ok.rectTransform,Vector3.one,.4f,true));closeAt=Time.unscaledTime+1.3f;}
  }

  void Update(){
   var s=bridge.State;
   int trucks=s?.dock?.Length??0,low=(s?.restockSlots??Array.Empty<RestockSlot>()).Count(x=>x.reserve>0&&x.stock<x.capacity*.35f);
   bool free=!IsOpen&&!OtherGameOpen;
   dockFab.gameObject.SetActive(free&&trucks>0);if(trucks>0)dockCount.text=trucks.ToString();
   restockFab.gameObject.SetActive(free&&low>0);if(low>0)restockCount.text=low.ToString();
   if(dockFab.gameObject.activeSelf)dockFab.localScale=Vector3.one*(1+Mathf.Sin(Time.unscaledTime*4)*.03f);
   if(!IsOpen)return;
   if(closeAt>0&&Time.unscaledTime>closeAt){Close();return;}
   if(Input.GetKeyDown(KeyCode.Escape))Close();
  }
 }
 // Tags a stockroom box with its product.
 public sealed class CheckoutStockBox:MonoBehaviour {public int productId;}
}
