using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // REPOR: restock a store fixture. Open the cart boxes (swipe the tape), then drag each unit onto the
 // price-tagged lane of its product. Fridges and chests have covers that must stay closed while the
 // round runs. Units are sent to the app as restockShelf commands, batched per lane.
 public sealed class CheckoutRestockGame:MonoBehaviour {
  public static CheckoutRestockGame Instance {get;private set;}
  public bool IsOpen=>window&&window.activeSelf;
  public string QaFixture;

  static readonly Vector2 Mid=new Vector2(.5f,.5f);
  const int MaxLanes=7,MaxUnitsPerBox=12;
  const float PourStep=.07f,ComboWindow=2.5f,IdleHint=5f,ColdSeconds=12f,ColdRefillSeconds=30f;

  CheckoutBridge bridge;RectTransform root,stage;GameObject window,hint,toast;TextMeshProUGUI title;Image backdrop;
  AudioSource sound;
  readonly List<GameObject> scene=new List<GameObject>();
  readonly List<Group> groups=new List<Group>();int groupIndex;

  // Current fixture
  FixtureView view;bool coldKind;float cold=1;bool coldRan;RectTransform coldBar;Image coldFill;
  readonly List<Lane> lanes=new List<Lane>();readonly List<Cart> carts=new List<Cart>();
  readonly Dictionary<int,int> reserveLeft=new Dictionary<int,int>();
  readonly Dictionary<string,Pending> pending=new Dictionary<string,Pending>();
  TextMeshProUGUI comboLabel;RectTransform comboBadge;
  int placed,mistakes,streak,bestStreak,totalBoxes;float startedAt,lastGood,lastInput,coverDoneAt;bool finished;

  sealed class Group {public string shelfId,name;public List<RestockSlot> slots;public float urgency;}
  sealed class Lane {public RestockSlot slot;public int number,productId,cap,next;public RectTransform rect;public FixtureLane geo;public Image tag;public TextMeshProUGUI count;public readonly List<Image> icons=new List<Image>();public readonly List<Image> shadows=new List<Image>();public readonly List<int> rows=new List<int>();}
  sealed class Cart {public int productId,units;public RectTransform box;public Image carton,flap,front,tape,curl;public RectTransform icon,badgeRect;public float peel,tapeU0,tapeU1;public int peelDir;public Vector2 tapeL,tapeR;public TextMeshProUGUI badge;public RectTransform handle;public Vector2 home;public float size;public bool open,done;public int flying;public CheckoutDragToken drag;public readonly List<Unit> pile=new List<Unit>();}
  sealed class Unit {public RectTransform rect;public int productId;public Cart cart;}
  sealed class Pending {public string slotId;public int productId,amount;public float lastAt;}

  public void Initialize(CheckoutBridge owner){
   Instance=this;bridge=owner;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.5f;
   root=U.Canvas(transform,"CheckoutRestockGame",83);
   stage=U.GameWindow(root,"wall_backdrop",out window,out title,out backdrop,Close);
   // The store corner rendered for REPOR (wall, wainscot and tiled floor) replaces the generic wall.
   var corner=K.Icon("Restock/restock_backdrop");
   if(corner&&backdrop){
    backdrop.sprite=corner;var fit=backdrop.GetComponent<AspectRatioFitter>();
    if(fit)fit.aspectRatio=corner.rect.width/Mathf.Max(1,corner.rect.height);
   }
   window.SetActive(false);
  }

  // ------------------------------------------------------------------ public API
  public static void Show(){if(Instance)Instance.OpenMostUrgent();}
  public static void ShowFixture(string shelfId){if(Instance)Instance.OpenFixtureById(shelfId);}
  public static bool AnyNeeds(Snapshot s){return s?.restockSlots?.Any(x=>Needs(x))??false;}
  static bool Needs(RestockSlot s){return s!=null&&s.reserve>0&&s.stock<s.capacity;}
  bool OtherGameOpen=>(CheckoutSupplierShop.Instance&&CheckoutSupplierShop.Instance.IsOpen)||(CheckoutCounterGame.Instance&&CheckoutCounterGame.Instance.IsOpen)||(CheckoutIncidents.Instance&&CheckoutIncidents.Instance.IsOpen)||(CheckoutStockroom.Instance&&CheckoutStockroom.Instance.IsOpen)||(CheckoutReceivingGame.Instance&&CheckoutReceivingGame.Instance.IsOpen)||(CheckoutPackingGame.Instance&&CheckoutPackingGame.Instance.IsOpen);

  // ------------------------------------------------------------------ fixtures and lanes
  // Lane number from the slot id: "<shelfId>" is lane 0, "<shelfId>:n" is lane n (max 6).
  static int LaneNumber(RestockSlot s){
   var id=s.slotId??"";int colon=id.LastIndexOf(':');if(colon<0||colon==id.Length-1)return 0;
   return int.TryParse(id.Substring(colon+1),out var n)?Mathf.Clamp(n,0,MaxLanes-1):0;
  }
  void BuildGroups(){
   groups.Clear();var all=bridge.State?.restockSlots;if(all==null)return;
   foreach(var g in all.Where(s=>s!=null).GroupBy(s=>s.shelfId)){
    var slots=g.OrderBy(s=>LaneNumber(s)).ToList();var needing=slots.Where(s=>Needs(s)).ToList();
    if(needing.Count==0)continue;
    groups.Add(new Group{shelfId=g.Key,name=slots[0].shelfName,slots=slots,urgency=needing.Min(s=>s.stock/(float)Mathf.Max(1,s.capacity))});
   }
   groups.Sort((a,b)=>a.urgency.CompareTo(b.urgency));
  }
  void OpenMostUrgent(){
   if(OtherGameOpen)return;BuildGroups();if(groups.Count==0)return;
   groupIndex=0;OpenGroup();
  }
  void OpenFixtureById(string shelfId){
   if(OtherGameOpen||string.IsNullOrEmpty(shelfId))return;BuildGroups();
   int at=groups.FindIndex(g=>g.shelfId==shelfId);
   if(at<0){
    // Asked for a fixture that needs nothing: open it anyway, all its slots, as the first tab.
    var slots=(bridge.State?.restockSlots??Array.Empty<RestockSlot>()).Where(s=>s!=null&&s.shelfId==shelfId).OrderBy(s=>LaneNumber(s)).ToList();
    if(slots.Count==0)return;
    groups.Insert(0,new Group{shelfId=shelfId,name=slots[0].shelfName,slots=slots,urgency=1});at=0;
   }
   groupIndex=at;OpenGroup();
  }
  // Switching fixtures (or reopening) sends what is pending, then rebuilds the scene.
  void OpenGroup(){
   if(groupIndex<0||groupIndex>=groups.Count||OtherGameOpen)return;
   FlushAll();StopAllCoroutines();Clear();
   window.SetActive(true);window.transform.SetAsLastSibling();
   finished=false;placed=mistakes=streak=bestStreak=totalBoxes=0;startedAt=lastInput=Time.unscaledTime;lastGood=-99;
   promptAt=0;coverDoneAt=0;
   var g=groups[groupIndex];title.text="Repor · "+g.name;
   BuildFixture(g);
   BuildTabs();
   // First box: a hand shows the swipe across its tape.
   if(carts.Count>0&&carts[0].handle!=null){
    var first=carts[0].handle;float w=carts[0].size*.4f;
    ShowHint(()=>U.LocalOf(stage,first)+new Vector2(-w,0),()=>U.LocalOf(stage,first)+new Vector2(w,0),false);
   }
  }
  void Close(){
   StopAllCoroutines();FlushAll();Clear();window.SetActive(false);finished=false;
  }
  void Clear(){
   foreach(var o in scene)if(o)Destroy(o);
   scene.Clear();if(hint)Destroy(hint);hint=null;toast=null;
   view=null;coldKind=false;coldRan=false;coldBar=null;coldFill=null;cold=1;
   lanes.Clear();carts.Clear();reserveLeft.Clear();pending.Clear();boxQueue.Clear();
   comboLabel=null;comboBadge=null;QaFixture=null;
  }
  T Keep<T>(T c) where T:Component{scene.Add(c.gameObject);return c;}
  void Play(AudioClip clip,float pitch=1,float volume=1){if(!clip||!sound)return;sound.pitch=CheckoutRestockSound.Vary(pitch);sound.PlayOneShot(clip,volume);}
  AudioClip back=>CheckoutRestockSound.Back;AudioClip grab=>CheckoutRestockSound.Grab;AudioClip wrong=>CheckoutRestockSound.Wrong;
  bool Glassy=>view!=null&&(view.key=="fridge"||view.key=="cooler");
  static string Json(string s)=>"\""+(s??"").Replace("\\","\\\\").Replace("\"","\\\"")+"\"";
  void Touch(){lastInput=Time.unscaledTime;StopHint();}
  void StopHint(){if(hint)Destroy(hint);hint=null;}

  // Short message across the top of the stage (one at a time).
  void Toast(string text){
   if(toast)Destroy(toast);
   var plate=Keep(U.Shape(stage,"Toast","4A3624",20,new Vector2(.5f,1),new Vector2(stage.rect.width*.62f,58),new Vector2(0,-40)));
   var label=U.Label(plate.transform,"Text",K.Headline,24,"FFFFFF");U.Stretch(label.rectTransform,Vector2.zero,Vector2.one,new Vector2(16,0),new Vector2(-16,0));
   label.text=text;label.enableAutoSizing=true;label.fontSizeMin=14;label.fontSizeMax=24;
   toast=plate.gameObject;StartCoroutine(U.Pop(plate.transform,1.08f,.25f));StartCoroutine(DropLater(plate.gameObject,2.4f));
  }
  IEnumerator DropLater(GameObject o,float delay){yield return new WaitForSecondsRealtime(delay);if(o){if(toast==o)toast=null;Destroy(o);}}

  // Round tabs at the top-left of the stage, one per fixture that needs restock.
  void BuildTabs(){
   if(groups.Count<2)return;
   for(int i=0;i<groups.Count;i++){
    var g=groups[i];var emptiest=g.slots.Where(s=>Needs(s)).OrderBy(s=>s.stock/(float)Mathf.Max(1,s.capacity)).FirstOrDefault()??g.slots[0];
    var tab=Keep(U.Shape(stage,"Tab "+i,i==groupIndex?"FFE3A8":"FFF7EC",30,new Vector2(0,1),new Vector2(60,60),new Vector2(46+i*70,-44)));
    U.Icon(tab.transform,"Product",$"Products/product-{emptiest.productId:000}",Mid,new Vector2(42,42));
    int need=g.slots.Count(s=>Needs(s));
    var dot=U.Shape(tab.rectTransform,"Dot","E15533",12,new Vector2(1,1),new Vector2(24,22),new Vector2(-2,-2));
    var count=U.Label(dot.transform,"Count",K.Headline,13,"FFFFFF");U.Stretch(count.rectTransform,Vector2.zero,Vector2.one);count.text=need.ToString();
    int index=i;U.Tap(tab,()=>{Touch();groupIndex=index;OpenGroup();});
   }
  }


  // Live value of a slot from the snapshot (customers keep buying while the player works).
  RestockSlot Live(string slotId)=>bridge.State?.restockSlots?.FirstOrDefault(s=>s!=null&&s.slotId==slotId);
  int Unflushed(string slotId){return pending.TryGetValue(slotId,out var p)?p.amount:0;}
  int UnflushedProduct(int productId){return pending.Values.Where(p=>p.productId==productId).Sum(p=>p.amount);}
  // Room left on a lane: live stock, unsent units and the lane's own empty places.
  int RoomFor(Lane lane){
   var live=Live(lane.slot.slotId);int stock=live?.stock??lane.slot.stock;
   return Mathf.Min(lane.cap-stock-Unflushed(lane.slot.slotId),lane.cap-lane.next);
  }
  // Stockroom units of a product left for this round (never more than the live reserve).
  int ReserveLeft(int productId){
   int local=reserveLeft.TryGetValue(productId,out var r)?r:0;
   var live=bridge.State?.restockSlots?.FirstOrDefault(s=>s!=null&&s.productId==productId);
   if(live!=null)local=Mathf.Min(local,live.reserve-UnflushedProduct(productId));
   return local;
  }
  // The lane under a dragged thing (its pivot follows the pointer while dragging).
  Lane LaneUnder(RectTransform dragged){
   if(view==null||!dragged)return null;
   Vector2 p=view.root.InverseTransformPoint(dragged.position);
   var geo=CheckoutFixtureArt.Pick(view,p);
   return geo==null?null:lanes.FirstOrDefault(l=>l.geo==geo);
  }
  Lane FirstFreeLane(int productId){return lanes.FirstOrDefault(l=>l.productId==productId&&RoomFor(l)>0);}

  // ------------------------------------------------------------------ commands (batched per lane)
  void AddPending(string slotId,int productId,int amount){
   if(amount<=0||string.IsNullOrEmpty(slotId))return;
   if(!pending.TryGetValue(slotId,out var p)){p=new Pending{slotId=slotId,productId=productId};pending[slotId]=p;}
   p.amount+=amount;p.lastAt=Time.unscaledTime;
  }
  void Send(Pending p){
   if(p==null||p.amount<=0)return;
   bridge.Command("restockShelf","[{\"shelfId\":"+Json(p.slotId)+",\"productId\":"+p.productId+",\"amount\":"+p.amount+"}]");
  }
  void FlushSlot(string slotId){
   if(pending.TryGetValue(slotId,out var p)){pending.Remove(slotId);Send(p);}
  }
  void FlushAll(){
   if(pending.Count==0)return;
   var all=pending.Values.ToList();pending.Clear();
   foreach(var p in all)Send(p);
  }

  // ------------------------------------------------------------------ scene: fixture, lanes, cover, cart
  static int Seed(string s){int h=17;foreach(char c in s??"")h=h*31+c;return h;}
  void BuildFixture(Group g){
   QaFixture=g.shelfId;
   float W=stage.rect.width,H=stage.rect.height;
   // Fixture on the left, standing on the floor; the cart on the right (CartWidth); tabs on top.
   float cw=Mathf.Min(CartWidth,W*.4f);
   float top=H*.5f-(groups.Count>1?84:16),bottom=-H*.5f+8,left=-W*.5f+16,right=W*.5f-cw-30;
   var box=new Vector2(right-left,top-bottom);
   var center=new Vector2((left+right)*.5f,(top+bottom)*.5f);
   int era=bridge.State?.era?.index??0;
   view=CheckoutFixtureArt.Build(stage,CheckoutFixtureArt.ArtKey(g.shelfId,era),g.name,center,box);
   Keep(view.root);
   Canvas.ForceUpdateCanvases();
   var byLane=new Dictionary<int,RestockSlot>();
   foreach(var s in g.slots)if(!byLane.ContainsKey(LaneNumber(s)))byLane[LaneNumber(s)]=s;
   for(int l=0;l<view.lanes.Length;l++){
    var geo=view.lanes[l];if(geo==null)continue;
    if(!byLane.TryGetValue(l,out var slot)){geo.rect.gameObject.SetActive(false);continue;}
    BuildLane(geo,l,slot);
   }
   SortProducts();
   // Doors and lids: a tap opens or closes each one (they start closed).
   coldKind=view.doors.Length>0;
   for(int d=0;d<view.doors.Length;d++){int door=d;U.Tap(view.doorHits[d],()=>ToggleDoor(door));}
   if(coldKind)BuildColdMeter(H);
   BuildCarts(g,W,H);
   comboBadge=Keep(U.Shape(stage,"Combo","EC862E",22,Mid,new Vector2(120,44),new Vector2(W*.5f-cw*.5f-18,-H*.5f+cw*.76f+40))).rectTransform;
   comboBadge.gameObject.SetActive(false);
   comboLabel=U.Label(comboBadge.transform,"Text",K.Headline,22,"FFFFFF");U.Stretch(comboLabel.rectTransform,Vector2.zero,Vector2.one);
   comboLabel.text="";
   Canvas.ForceUpdateCanvases();
  }

  // One lane inside the 3D fixture: the units stand on the shelf floor in facings (left to right) and
  // rows (front to back). Units in stock are solid with a contact shadow, empty places are faint ghosts.
  // A price tag ("etiqueta") hangs on the front edge.
  static readonly Color Ghost=new Color(1,1,1,.36f);
  static Color RowShade(int row)=>new Color(1-.12f*row,1-.12f*row,1-.1f*row,1);
  void BuildLane(FixtureLane geo,int number,RestockSlot slot){
   var lv=new Lane{slot=slot,number=number,productId=slot.productId,rect=geo.rect,geo=geo,cap=Mathf.Max(0,slot.capacity)};
   int stock=Mathf.Max(0,slot.stock);lv.next=Mathf.Min(stock,lv.cap);
   if(!reserveLeft.ContainsKey(slot.productId))reserveLeft[slot.productId]=Mathf.Max(0,slot.reserve);
   var sprite=CheckoutFixtureArt.Product(slot.productId);float aspect=CheckoutFixtureArt.ProductAspect(slot.productId);
   int n=Mathf.Max(1,lv.cap);
   for(int i=0;i<n;i++){
    var p=CheckoutFixtureArt.Slot(geo,i,n,aspect,out float h,out int row);
    float w=h/Mathf.Max(.05f,aspect);
    var sh=Keep(U.GlowAt(view.shadows,"Shadow",new Color(.12f,.07f,.03f,.55f),new Vector2(.5f,.5f),1,p));
    sh.rectTransform.sizeDelta=new Vector2(w*1.05f,h*.16f);sh.enabled=i<stock;
    var icon=new GameObject("Unit "+number+"."+i,typeof(RectTransform),typeof(Image)).GetComponent<Image>();
    icon.transform.SetParent(view.products,false);icon.sprite=sprite;icon.raycastTarget=false;icon.preserveAspect=false;
    var r=icon.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);r.pivot=new Vector2(.5f,0);r.sizeDelta=new Vector2(w,h);r.anchoredPosition=p;
    icon.color=i<stock?RowShade(row):Ghost;
    lv.icons.Add(icon);lv.shadows.Add(sh);lv.rows.Add(row);
   }
   // Price tag ("etiqueta") on the lane's front edge: the product and how full the lane is.
   float laneW=(geo.fr-geo.fl).magnitude,tagW=Mathf.Clamp(laneW*.42f,46,96),tagH=tagW*.4f;
   lv.tag=Keep(U.Shape(view.root,"Tag "+number,"FFF1D1",8,new Vector2(.5f,.5f),new Vector2(tagW,tagH),geo.FrontMid+new Vector2(0,-tagH*.45f)));
   var outline=lv.tag.gameObject.AddComponent<Outline>();outline.effectColor=K.C("EC862E");outline.effectDistance=new Vector2(1.5f,-1.5f);
   var tagIcon=U.Icon(lv.tag.transform,"Product",$"Products/product-{slot.productId:000}",new Vector2(0,.5f),Vector2.one*tagH*.85f,new Vector2(tagH*.5f,0));tagIcon.raycastTarget=false;
   lv.count=U.Label(lv.tag.transform,"Count",K.Headline,tagH*.5f,"4A3624");
   U.Stretch(lv.count.rectTransform,Vector2.zero,Vector2.one,new Vector2(tagH*.9f,0),new Vector2(-2,0));
   lv.count.enableAutoSizing=true;lv.count.fontSizeMin=7;lv.count.fontSizeMax=tagH*.55f;lv.count.text=lv.next+"/"+lv.cap;
   lv.tag.raycastTarget=false;
   lanes.Add(lv);
  }
  // Products further back (higher on screen, same shelf) are drawn first.
  void SortProducts(){
   if(view==null)return;
   var all=new List<RectTransform>();foreach(Transform t in view.products)all.Add((RectTransform)t);
   all.Sort((a,b)=>b.anchoredPosition.y.CompareTo(a.anchoredPosition.y));
   for(int i=0;i<all.Count;i++)all[i].SetSiblingIndex(i);
  }

  void BuildColdMeter(float H){
   var bar=U.Shape(stage,"Cold","FFF7EC",10,new Vector2(1,1),new Vector2(26,H*.34f),new Vector2(-31,-(18+H*.17f)));
   Keep(bar);coldBar=bar.rectTransform;
   coldFill=U.Box(bar.transform,"Fill","3B8FD6",8,Vector2.zero,Vector2.one);
   cold=1;coldRan=false;RefreshCold();
  }
  void RefreshCold(){
   if(!coldFill)return;
   coldFill.rectTransform.anchorMax=new Vector2(1,Mathf.Clamp01(cold));
   coldFill.color=Color.Lerp(K.C("E15533"),K.C("3B8FD6"),Mathf.Clamp01(cold));
  }

  // ------------------------------------------------------------------ the stock cart (pre-rendered 3D)
  // restock_cart.json (ArtSource/restock/cart_art.py): the deck quad in the cart image and, for the box
  // images (same camera, same pixel scale), the anchor (bottom centre), label, tape ends and mouth points.
  [Serializable] class JCartDeck {public float[] fl,fr,bl,br;}
  [Serializable] class JCartFill {public float[] fl,fr,bl,br;public float ppm,height;}
  [Serializable] class JCartBox {public float[] anchor,label,labelTop,tapeL,tapeR,mouth;public JCartFill fill;}
  [Serializable] class JCart {public int[] cartSize,boxSize;public JCartDeck deck;public JCartBox box;}
  static JCart cartData;
  static JCart CartData(){
   if(cartData!=null)return cartData;
   var t=Resources.Load<TextAsset>("CheckoutDesktop/Restock/restock_cart");
   cartData=t?JsonUtility.FromJson<JCart>(t.text):null;return cartData;
  }
  static Vector2 V(float[] a)=>a!=null&&a.Length>1?new Vector2(a[0],a[1]):new Vector2(.5f,.5f);
  static Image Layer(Transform parent,string name,string path){
   var img=new GameObject(name,typeof(RectTransform),typeof(Image)).GetComponent<Image>();img.transform.SetParent(parent,false);
   img.sprite=K.Icon(path);img.raycastTarget=false;U.Stretch(img.rectTransform,Vector2.zero,Vector2.one);return img;
  }
  float cartScale=1;Vector2 cartBoxPx;

  // The cart stands at the bottom right, in front of the wall; one closed box per product that needs
  // restock on this fixture (units = min(stockroom reserve, units missing here, 12)).
  void BuildCarts(Group g,float W,float H){
   var items=g.slots.Where(s=>Needs(s)).GroupBy(s=>s.productId).Select(grp=>new{pid=grp.Key,units=Mathf.Min(reserveLeft.TryGetValue(grp.Key,out var r)?r:0,Mathf.Min(grp.Sum(s=>Mathf.Max(0,s.capacity-s.stock)),grp.First().caseSize>0?grp.First().caseSize:MaxUnitsPerBox))}).Where(x=>x.units>0).ToList();
   var d=CartData();
   Vector2 cartPx=d!=null?new Vector2(d.cartSize[0],d.cartSize[1]):new Vector2(1079,819);
   cartBoxPx=d!=null?new Vector2(d.boxSize[0],d.boxSize[1]):new Vector2(527,302);
   float cw=Mathf.Min(CartWidth,W*.4f),ch=cw*cartPx.y/cartPx.x;cartScale=cw/cartPx.x;
   var cart=Keep(Layer(stage,"Cart","Restock/restock_cart")).rectTransform;
   U.At(cart,Mid,new Vector2(cw,ch),new Vector2(W*.5f-cw*.5f-18,-H*.5f+ch*.5f+6));
   int n=items.Count;if(n==0)return;
   totalBoxes=n;
   // Deck points (stage space) from the normalised deck quad.
   Vector2 Deck(float u,float v){
    var q=d?.deck;Vector2 fl=V(q?.fl),fr=V(q?.fr),bl=V(q?.bl),br=V(q?.br);
    var p=Vector2.Lerp(Vector2.Lerp(fl,fr,u),Vector2.Lerp(bl,br,u),v);
    return cart.anchoredPosition+new Vector2((p.x-.5f)*cw,(p.y-.5f)*ch);
   }
   // At most three boxes in a row on the deck; the others wait and roll in when a box is emptied.
   int shown=Mathf.Min(3,n);
   // Size the boxes so their bodies sit side by side on the deck without overlapping.
   float deckPx=(V(d?.deck?.fr).x-V(d?.deck?.fl).x)*cartPx.x;
   float scale=Mathf.Min(1f,deckPx*.86f/shown*.9f/(cartBoxPx.x*.56f));
   boxQueue.Clear();boxSlots.Clear();boxScale=scale;
   for(int i=0;i<shown;i++)boxSlots.Add(Deck(.06f+(i+.5f)/shown*.84f,.45f));
   for(int i=0;i<n;i++){
    if(i<shown)BuildBox(items[i].pid,items[i].units,scale,boxSlots[i]);
    else boxQueue.Enqueue((items[i].pid,items[i].units));
   }
  }
  const float CartWidth=540;
  readonly Queue<(int pid,int units)> boxQueue=new Queue<(int pid,int units)>();readonly List<Vector2> boxSlots=new List<Vector2>();float boxScale=1;

  // A closed carton: rendered box + tape layer + the product on its printed label + a unit count badge.
  // An invisible handle over the tape takes the swipe that cuts it.
  Cart BuildBox(int productId,int units,float scale,Vector2 home){
   var d=CartData();
   Vector2 size=cartBoxPx*cartScale*scale;
   var holder=Keep(CheckoutDesktopCard.Image(stage,"Box",new Color(1,1,1,0),0));
   var box=holder.rectTransform;
   U.At(box,Mid,size,home);var anchor=V(d?.box?.anchor);box.pivot=new Vector2(anchor.x,anchor.y);box.anchoredPosition=home;
   Vector2 P(float[] a){var p=V(a);return new Vector2((p.x-.5f)*size.x,(p.y-.5f)*size.y);}
   float bodyW=size.x*.56f;
   var sh=U.GlowAt(box,"Shadow",new Color(.1f,.06f,.03f,.45f),Mid,1,P(d?.box?.anchor));sh.rectTransform.sizeDelta=new Vector2(bodyW*1.25f,size.y*.16f);
   // Layers: closed carton | open carton (back, flaps) < units < open front wall | tape on top.
   var closed=Layer(box,"Closed","Restock/restock_box_closed");
   var open=Layer(box,"Open","Restock/restock_box_open");open.gameObject.SetActive(false);
   var unitsNode=(RectTransform)new GameObject("Units",typeof(RectTransform)).transform;unitsNode.SetParent(box,false);U.Stretch(unitsNode,Vector2.zero,Vector2.one);
   var front=Layer(box,"OpenFront","Restock/restock_box_open_front");front.gameObject.SetActive(false);
   var tape=Layer(box,"Tape","Restock/restock_box_tape");tape.type=Image.Type.Filled;tape.fillMethod=Image.FillMethod.Horizontal;tape.fillAmount=1;
   var label=P(d?.box?.label);float ls=bodyW*.3f;
   var icon=U.Icon(box,"Product",$"Products/product-{productId:000}",Mid,Vector2.one*ls,label);icon.raycastTarget=false;
   var badge=U.Shape(box,"Count","4A3624",14,Mid,new Vector2(ls*1.05f,ls*.6f),label+new Vector2(bodyW*.36f,ls*.55f));badge.raycastTarget=false;
   var count=U.Label(badge.transform,"Units",K.Headline,ls*.42f,"FFFFFF");U.Stretch(count.rectTransform,Vector2.zero,Vector2.one);count.text="x"+units;
   // Swipe handle over the tape (from one tape end to the other).
   var tl=P(d?.box?.tapeL);var tr=P(d?.box?.tapeR);
   var handle=U.Shape(box,"TapeHandle","FFFFFF",0,Mid,new Vector2(Mathf.Abs(tr.x-tl.x)*1.15f,size.y*.4f),(tl+tr)*.5f);
   handle.color=new Color(1,1,1,0);handle.raycastTarget=true;
   var c=new Cart{productId=productId,units=units,box=box,carton=closed,flap=open,front=front,tape=tape,handle=handle.rectTransform,home=home,size=bodyW,badge=count,
                  icon=icon.rectTransform,badgeRect=badge.rectTransform,tapeL=tl,tapeR=tr,tapeU0=V(d?.box?.tapeL).x,tapeU1=V(d?.box?.tapeR).x};
   handle.gameObject.AddComponent<CheckoutRestockTape>().Init(handle.rectTransform,(p,dir)=>PeelTape(c,p,dir),()=>OpenBox(c));
   carts.Add(c);
   return c;
  }

  // ------------------------------------------------------------------ boxes: peel the tape, open, units out
  float promptAt;
  RectTransform[] LaneRects(){return view!=null&&view.dropArea?new[]{view.dropArea}:Array.Empty<RectTransform>();}
  // The finger pulls the tape off from the side it started on: the strip shortens behind it and the free
  // end curls up under the finger.
  void PeelTape(Cart c,float p,int dir){
   if(c==null||c.open||!c.tape)return;
   if(c.peel<=0){Touch();Play(CheckoutRestockSound.Tape,1,.45f);}
   c.peel=Mathf.Max(c.peel,p);c.peelDir=dir;
   // The fill runs over the whole image; the tape spans [tapeU0, tapeU1] of it.
   float edge=dir>0?Mathf.Lerp(c.tapeU0,c.tapeU1,c.peel):Mathf.Lerp(c.tapeU1,c.tapeU0,c.peel);
   c.tape.fillOrigin=dir>0?1:0;c.tape.fillAmount=dir>0?1-edge:edge;
   float x=dir>0?Mathf.Lerp(c.tapeL.x,c.tapeR.x,c.peel):Mathf.Lerp(c.tapeR.x,c.tapeL.x,c.peel);
   float th=c.box.rect.height*.06f;
   if(!c.curl){
    c.curl=U.Shape(c.box,"Curl","D9C6A2",3,Mid,new Vector2(th*2.2f,th*.8f),Vector2.zero);c.curl.raycastTarget=false;var co=c.curl.gameObject.AddComponent<Shadow>();co.effectColor=new Color(.3f,.2f,.1f,.35f);co.effectDistance=new Vector2(1,-2);
    c.curl.rectTransform.pivot=new Vector2(dir>0?1:0,.5f);
   }
   var cr=c.curl.rectTransform;cr.anchoredPosition=new Vector2(x,c.tapeL.y+th*.2f+th*c.peel);
   cr.localRotation=Quaternion.Euler(0,0,dir>0?-28-20*c.peel:28+20*c.peel);
  }
  void OpenBox(Cart c){
   if(c==null||c.open||c.done||!c.box)return;
   Touch();c.open=true;
   if(c.handle)c.handle.gameObject.SetActive(false);
   if(c.peelDir==0)c.peelDir=1;
   StartCoroutine(OpenRoutine(c));
  }
  IEnumerator OpenRoutine(Cart c){
   // The rest of the tape comes off in one pull; the strip flies away and fades.
   Play(CheckoutRestockSound.Tape,1.05f,.7f);
   float from=c.tape?c.tape.fillAmount:0;
   if(c.tape)c.tape.fillOrigin=c.peelDir>0?1:0;
   if(!c.curl){PeelTape(c,.02f,c.peelDir);}
   var curl=c.curl;Vector2 cp=curl?curl.rectTransform.anchoredPosition:Vector2.zero;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.22f){
    if(!c.box)yield break;
    if(c.tape)c.tape.fillAmount=Mathf.Lerp(from,0,t);
    if(curl){var r=curl.rectTransform;float x=c.peelDir>0?Mathf.Lerp(cp.x,c.tapeR.x,t):Mathf.Lerp(cp.x,c.tapeL.x,t);r.anchoredPosition=new Vector2(x,cp.y+t*8);}
    yield return null;
   }
   if(c.tape)c.tape.gameObject.SetActive(false);
   if(curl){
    var r=curl.rectTransform;var p0=r.anchoredPosition;
    for(float t=0;t<1;t+=Time.unscaledDeltaTime/.45f){
     if(!curl)break;r.anchoredPosition=p0+new Vector2(c.peelDir*c.size*.5f*t,c.size*.35f*Mathf.Sin(t*Mathf.PI*.6f));
     r.localRotation=Quaternion.Euler(0,0,-c.peelDir*(40+120*t));var col=curl.color;col.a=1-t;curl.color=col;yield return null;
    }
    if(curl)Destroy(curl.gameObject);
   }
   // The flaps spring open: swap to the open carton with a soft squash of the whole box.
   if(c.carton)c.carton.gameObject.SetActive(false);
   if(c.flap)c.flap.gameObject.SetActive(true);
   if(c.front)c.front.gameObject.SetActive(true);
   if(c.icon)c.icon.SetAsLastSibling();if(c.badgeRect)c.badgeRect.SetAsLastSibling();
   Play(back,.8f,.5f);
   if(c.box){c.box.localScale=new Vector3(1.04f,.94f,1);StartCoroutine(U.Scale(c.box,Vector3.one,.25f,true));}
   // The units stand inside the box in rows, back row first, rising a little as they appear.
   var d=CartData();var f=d?.box?.fill;var size=c.box.rect.size;
   Vector2 Q(float[] a){var p=V(a);return new Vector2((p.x-.5f)*size.x,(p.y-.5f)*size.y);}
   Vector2 fl=Q(f?.fl),fr=Q(f?.fr),bl=Q(f?.bl),br=Q(f?.br);
   float pxScale=size.x/Mathf.Max(1,cartBoxPx.x);
   float aspect=CheckoutFixtureArt.ProductAspect(c.productId);var sprite=CheckoutFixtureArt.Product(c.productId);
   int n=c.units,rows=n<=4?1:2,cols=Mathf.Max(1,Mathf.CeilToInt(n/(float)rows));
   var parent=c.box.Find("Units");
   var list=new List<(Vector2 pos,float h,int row)>();
   for(int i=0;i<n;i++){
    int row=rows-1-i/cols,col=i%cols;   // fill the back row first so the front row is drawn on top
    float u=(col+.5f)/cols,v=rows==1?.45f:(row==1?.78f:.25f);
    var p=Vector2.Lerp(Vector2.Lerp(fl,fr,u),Vector2.Lerp(bl,br,u),v);
    float laneW=Vector2.Distance(Vector2.Lerp(fl,bl,v),Vector2.Lerp(fr,br,v));
    float h=Mathf.Min((f?.ppm??600)*.30f*pxScale*(1-.08f*row),laneW/cols*1.3f*aspect);
    list.Add((p,h,row));
   }
   for(int i=0;i<n;i++){
    var (pos,h,row)=list[i];
    var img=new GameObject("Unit",typeof(RectTransform),typeof(Image)).GetComponent<Image>();
    img.transform.SetParent(parent??c.box,false);img.sprite=sprite;img.preserveAspect=false;
    var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);r.pivot=new Vector2(.5f,0);r.sizeDelta=new Vector2(h/Mathf.Max(.05f,aspect),h);
    r.anchoredPosition=pos-new Vector2(0,h*.5f);img.color=row>0?new Color(.9f,.9f,.92f,1):Color.white;
    StartCoroutine(RiseIn(r,pos,.08f+i*.05f));
    var unit=new Unit{rect=r,productId=c.productId,cart=c};
    c.pile.Add(unit);
    AddUnitToken(unit,pos);
   }
   // The box itself can be dragged onto a lane to pour all its units.
   var holder=c.box.GetComponent<Image>();
   c.drag=U.Drag(holder);c.drag.SetHome(c.home);
   c.drag.Setup(LaneRects(),t=>DropBox(c,t),()=>Play(back,1,.6f),()=>{Touch();Play(grab,.9f,.6f);});
  }
  // A unit rises from inside the box to its place.
  IEnumerator RiseIn(RectTransform r,Vector2 to,float delay){
   if(!r)yield break;var from=r.anchoredPosition;
   yield return new WaitForSecondsRealtime(delay);
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.28f){
    if(!r)yield break;var tk=r.GetComponent<CheckoutDragToken>();if(tk&&tk.Dragging)yield break;
    float e=1-(1-t)*(1-t);r.anchoredPosition=Vector2.Lerp(from,to,e);yield return null;
   }
   if(r&&!(r.GetComponent<CheckoutDragToken>()?.Dragging??false))r.anchoredPosition=to;
  }
  IEnumerator PopIn(Transform t,float delay){
   yield return new WaitForSecondsRealtime(delay);
   if(t)yield return U.Scale(t,Vector3.one,.3f,true);
  }
  void AddUnitToken(Unit u,Vector2 home){
   var d=U.Drag(u.rect.GetComponent<Image>());d.SetHome(home);
   d.Setup(LaneRects(),t=>DropUnit(u,t),()=>Play(back,1,.6f),()=>{Touch();Play(grab,1,.6f);});
  }

  // ------------------------------------------------------------------ drops
  // One unit onto a lane. True keeps it where the flight puts it; false sends it back home.
  bool DropUnit(Unit u,RectTransform target){
   Touch();
   if(u==null||!u.rect||u.cart==null)return false;
   var lane=LaneUnder(u.rect);if(lane==null)return false;
   if(!view.Reachable(lane.geo)){BlockedByCover(u.rect,lane);return false;}
   if(lane.productId!=u.productId){WrongLane(lane,u.productId);return false;}
   if(RoomFor(lane)<=0){Play(wrong,1,.7f);StartCoroutine(U.Shake(lane.tag.rectTransform,.3f,8));Toast("Essa vaga está cheia");return false;}
   if(ReserveLeft(u.productId)<=0){Play(wrong,1,.7f);Toast("Sem mais "+lane.slot.productName+" no depósito");return false;}
   Place(u,lane,0);
   return true;
  }
  // The whole open box onto a lane: pours every unit that fits, one by one. The rest stay in the box.
  bool DropBox(Cart c,RectTransform target){
   Touch();
   if(c==null||!c.open||c.done)return false;
   var lane=LaneUnder(c.box);if(lane==null)return false;
   if(!view.Reachable(lane.geo)){BlockedByCover(c.box,lane);return false;}
   if(lane.productId!=c.productId){WrongLane(lane,c.productId);return false;}
   int room=RoomFor(lane),reserve=ReserveLeft(c.productId);
   int n=Mathf.Min(c.pile.Count,Mathf.Min(room,reserve));
   if(n<=0){
    Play(wrong,1,.7f);StartCoroutine(U.Shake(lane.tag.rectTransform,.3f,8));
    Toast(room<=0?"Essa vaga está cheia":"Sem mais "+lane.slot.productName+" no depósito");
    return false;
   }
   for(int i=0;i<n;i++){
    var u=c.pile[c.pile.Count-1];
    Place(u,lane,i*PourStep);
   }
   if(c.pile.Count>0&&c.box)StartCoroutine(U.Move(c.box,c.home,.3f,true));
   return true;
  }
  // Books one unit on the lane's next empty place and starts its flight. State changes now; the
  // animation (and the ghost turning solid) follows after the optional delay.
  void Place(Unit u,Lane lane,float delay){
   int index=lane.next;lane.next++;
   reserveLeft[u.productId]=(reserveLeft.TryGetValue(u.productId,out var r)?r:0)-1;
   u.cart.pile.Remove(u);u.cart.units--;u.cart.flying++;if(u.cart.badge)u.cart.badge.text="x"+u.cart.units;
   placed++;
   AddPending(lane.slot.slotId,u.productId,1);
   if(lane.next>=lane.cap)FlushSlot(lane.slot.slotId);
   var tk=u.rect?u.rect.GetComponent<CheckoutDragToken>():null;if(tk)tk.Locked=true;
   Combo(true);
   StartCoroutine(Land(u,lane,index,delay));
  }
  // Flight to the ghost place, which turns solid with a squash pop.
  IEnumerator Land(Unit u,Lane lane,int index,float delay){
   if(delay>0)yield return new WaitForSecondsRealtime(delay);
   var ghost=index<lane.icons.Count?lane.icons[index]:null;
   Vector2 at=ghost?U.LocalOf(stage,ghost.rectTransform):Vector2.zero;
   if(u.rect){
    u.rect.SetParent(stage,true);u.rect.SetAsLastSibling();Keep(u.rect);
    yield return U.Move(u.rect,at,.22f,true);
    Destroy(u.rect.gameObject);
   }
   if(ghost){
    ghost.color=RowShade(index<lane.rows.Count?lane.rows[index]:0);StartCoroutine(U.Pop(ghost.transform,1.1f,.22f));
    if(lane.count)lane.count.text=Mathf.Min(lane.cap,index+1)+"/"+lane.cap;
    if(index<lane.shadows.Count&&lane.shadows[index])lane.shadows[index].enabled=true;
   }
   // Each unit in a streak plays the next note of the scale: a combo becomes a little melody.
   Play(CheckoutRestockSound.Place(Glassy),1+Mathf.Min(streak,6)*.02f,.7f);
   if(ghost)Puff(at,new Color(1,.97f,.85f,.55f),ghost.rectTransform.rect.height*1.3f,.45f);
   u.cart.flying--;
   if(u.cart.open&&!u.cart.done&&u.cart.pile.Count==0&&u.cart.flying==0)StartCoroutine(FlattenBox(u.cart));
  }
  // An empty box flattens and disappears.
  IEnumerator FlattenBox(Cart c){
   c.done=true;if(c.drag)c.drag.Locked=true;
   Play(CheckoutRestockSound.Flatten,1,.6f);
   if(c.box){
    var at=U.LocalOf(stage,c.box);
    for(int i=0;i<4;i++)Puff(at+new Vector2((i-1.5f)*c.size*.3f,-c.size*.15f),new Color(.86f,.74f,.56f,.45f),c.size*.5f,.6f,new Vector2((i-1.5f)*c.size*.25f,c.size*.12f));
    yield return U.Scale(c.box,new Vector3(1,.1f,1),.25f);
    if(c.box)Destroy(c.box.gameObject);
   }
   carts.Remove(c);
   // The next waiting box slides onto the free spot.
   if(boxQueue.Count>0&&!finished){
    var (pid,units)=boxQueue.Dequeue();
    var slot=boxSlots.OrderBy(p=>carts.Any(k=>k.box&&(k.home-p).sqrMagnitude<1)?1:0).ThenBy(p=>(p-c.home).sqrMagnitude).First();
    var nb=BuildBox(pid,units,boxScale,slot);
    nb.box.anchoredPosition=slot+new Vector2(stage.rect.width*.25f,0);
    StartCoroutine(U.Move(nb.box,slot,.4f,true));Play(back,.9f,.5f);
   }
  }

  void Combo(bool good){
   if(good){
    streak=(Time.unscaledTime-lastGood<=ComboWindow&&streak>0)?streak+1:1;
    lastGood=Time.unscaledTime;bestStreak=Mathf.Max(bestStreak,streak);
   }
   if(comboBadge){
    bool on=good&&streak>=2;comboBadge.gameObject.SetActive(on);
    if(on&&comboLabel)comboLabel.text="x"+streak;
   }
  }
  // A soft glow that swells and fades (no sparks): the feedback stays calm.
  void Puff(Vector2 at,Color color,float size,float seconds,Vector2 drift=default){
   if(!stage)return;
   var g=Keep(U.GlowAt(stage,"Puff",color,Mid,size*.5f,at));
   StartCoroutine(PuffRun(g,size,seconds,drift));
  }
  IEnumerator PuffRun(Image g,float size,float seconds,Vector2 drift){
   if(!g)yield break;var r=g.rectTransform;var from=r.anchoredPosition;float a=g.color.a;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/seconds){
    if(!g)yield break;float e=1-(1-t)*(1-t);
    r.sizeDelta=Vector2.one*Mathf.Lerp(size*.5f,size,e);r.anchoredPosition=from+drift*e;
    var c=g.color;c.a=a*(1-t)*(t<.15f?t/.15f:1);g.color=c;yield return null;
   }
   if(g)Destroy(g.gameObject);
  }
  void Mistake(){mistakes++;streak=0;if(comboBadge)comboBadge.gameObject.SetActive(false);}
  void WrongLane(Lane lane,int productId){
   Play(wrong,1,.7f);StartCoroutine(U.Shake(lane.tag.rectTransform,.35f,6));
   Mistake();
   // The lane that does sell this product glows briefly.
   var right=FirstFreeLane(productId);
   if(right!=null)StartCoroutine(Glow(right.tag));
  }
  IEnumerator Glow(Image tag){
   if(!tag)yield break;var home=tag.color;
   yield return U.Tint(tag,K.C("FFD35C"),.2f);
   yield return new WaitForSecondsRealtime(.5f);
   if(tag)yield return U.Tint(tag,home,.3f);
  }
  // Drop on a lane behind a closed door: the door shakes, buzz, the unit returns.
  RectTransform DoorHit(int d)=>view!=null&&d>=0&&d<view.doorHits.Length&&view.doorHits[d]?view.doorHits[d].rectTransform:null;
  int ClosedDoorOf(Lane lane){if(lane?.geo==null)return -1;foreach(int d in lane.geo.doors)if(!view.doorOpen[d])return d;return -1;}
  void BlockedByCover(RectTransform from,Lane lane){
   Play(wrong,1,.7f);Mistake();
   int d=ClosedDoorOf(lane);var door=d>=0?view.doors[d]:null;var hit=DoorHit(d);
   if(door)StartCoroutine(U.Shake(door,.35f,12));
   Toast(view.kind=="door"?"Abra a porta primeiro":"Abra a tampa primeiro");
   if(hit&&from)ShowHint(()=>U.LocalOf(stage,from),()=>U.LocalOf(stage,hit),false);
  }
  void ToggleDoor(int d){
   if(view==null||d<0||d>=view.doors.Length||finished)return;
   Touch();
   bool open=!view.doorOpen[d];
   // Sliding lids share one track: opening one side closes the other.
   if(open&&view.kind=="lid")for(int o=0;o<view.doors.Length;o++)if(o!=d&&view.doorOpen[o])StartCoroutine(CheckoutFixtureArt.OpenDoor(view,o,false,.3f));
   StartCoroutine(DoorRoutine(d,open));
  }
  IEnumerator DoorRoutine(int d,bool open){
   if(open)Play(CheckoutRestockSound.DoorOpen,1,.7f);
   yield return CheckoutFixtureArt.OpenDoor(view,d,open,open?.45f:.32f);
   if(!open)Play(CheckoutRestockSound.DoorClose,1,.7f);
  }
  IEnumerator AllDoors(bool open){
   if(view==null)yield break;
   // Lids: one side at a time is enough for the QA run (it opens the left, then the right when needed).
   for(int d=0;d<view.doors.Length;d++)if(view.doorOpen[d]!=open){yield return DoorRoutine(d,open);if(open&&view.kind=="lid")break;}
  }
  IEnumerator Pulse(RectTransform r){
   if(!r)yield break;
   var s0=r.localScale;
   yield return U.Scale(r,s0*1.04f,.15f);
   if(r)yield return U.Scale(r,s0,.2f,true);
  }
  void ShowHint(Func<Vector2> from,Func<Vector2> to,bool tap){
   StopHint();hint=U.Hint(this,stage,from,to,tap);
  }

  // ------------------------------------------------------------------ frame: cold meter, round end, hints
  void Update(){
   if(!IsOpen)return;
   if(Input.GetKeyDown(KeyCode.Escape)){Close();return;}
   float dt=Time.unscaledDeltaTime;
   if(coldKind&&view!=null){
    // A door open: the cold drains; all closed: it refills slowly. Empty costs a star (once).
    if(view.AnyOpen){
     cold=Mathf.Max(0,cold-dt/ColdSeconds);
     if(cold<=0&&!coldRan){coldRan=true;Play(wrong,1,.7f);Toast("Feche a porta! Os produtos estão esquentando");}
    }else cold=Mathf.Min(1,cold+dt/ColdRefillSeconds);
    RefreshCold();
   }
   if(streak>0&&Time.unscaledTime-lastGood>ComboWindow){streak=0;if(comboBadge)comboBadge.gameObject.SetActive(false);}
   if(pending.Count>0){foreach(var p in pending.Values.ToList())if(Time.unscaledTime-p.lastAt>.5f)FlushSlot(p.slotId);}
   if(finished)return;
   // Round end: every box is flat. The cover must be closed to finish.
   if(totalBoxes>0&&carts.Count==0&&boxQueue.Count==0){
    if(coldKind&&view!=null&&view.AnyOpen){
     coverDoneAt=0;
     if(Time.unscaledTime>promptAt){
      promptAt=Time.unscaledTime+3f;Toast(view.kind=="door"?"Feche a porta para terminar":"Feche a tampa para terminar");
      for(int d=0;d<view.doors.Length;d++)if(view.doorOpen[d]){var hit=DoorHit(d);if(hit)ShowHint(()=>U.LocalOf(stage,hit),()=>U.LocalOf(stage,hit),true);break;}
     }
    }else{
     if(coverDoneAt<=0)coverDoneAt=Time.unscaledTime+.6f;
     else if(Time.unscaledTime>=coverDoneAt){Finish();return;}
    }
   }else coverDoneAt=0;
   if(hint==null&&Time.unscaledTime-lastInput>IdleHint)ShowIdleHint();
  }

  // Idle for 5 s: point at the next thing to do (a tape, a unit's lane, or the cover).
  void ShowIdleHint(){
   if(view==null||stage==null)return;
   var closed=carts.FirstOrDefault(c=>!c.open&&!c.done);
   if(closed!=null&&closed.handle!=null){
    var handle=closed.handle;float w=closed.size*.4f;
    ShowHint(()=>U.LocalOf(stage,handle)+new Vector2(-w,0),()=>U.LocalOf(stage,handle)+new Vector2(w,0),false);
    return;
   }
   var unit=carts.Where(c=>c.open&&!c.done).SelectMany(c=>c.pile).FirstOrDefault(u=>u.rect!=null);
   if(unit!=null){
    var lane=FirstFreeLane(unit.productId);
    var closedHit=lane!=null&&!view.Reachable(lane.geo)?DoorHit(ClosedDoorOf(lane)):null;
    if(closedHit){
     var from=unit.rect;
     ShowHint(()=>U.LocalOf(stage,from),()=>U.LocalOf(stage,closedHit),false);
     return;
    }
    if(lane!=null){
     var from=unit.rect;var target=lane.rect;
     ShowHint(()=>U.LocalOf(stage,from),()=>U.LocalOf(stage,target),false);
     return;
    }
   }
   if(coldKind&&view.AnyOpen&&carts.Count==0){
    for(int d=0;d<view.doors.Length;d++)if(view.doorOpen[d]){
     var hit=DoorHit(d);if(hit)ShowHint(()=>U.LocalOf(stage,hit),()=>U.LocalOf(stage,hit),true);break;
    }
   }
  }

  // ------------------------------------------------------------------ result card
  // Stars: start at 3, -1 per 3 mistakes, -1 if the cold ran out, -1 if over 8 s per box (min 1).
  // Everything placed (and the doors closed): a soft chime, then after a moment the next fixture that
  // needs restock opens by itself, or the window closes. No result card.
  void Finish(){
   if(finished)return;
   finished=true;FlushAll();StopHint();
   if(comboBadge)comboBadge.gameObject.SetActive(false);
   var marker=(RectTransform)new GameObject("Result",typeof(RectTransform)).transform;marker.SetParent(stage,false);Keep(marker);
   BuildGroups();
   int next=groups.FindIndex(g=>g.shelfId!=QaFixture);
   Play(next>=0?CheckoutRestockSound.Next:CheckoutRestockSound.Done,1,.8f);
   if(view!=null)Puff(U.LocalOf(stage,view.root),new Color(1,.95f,.8f,.3f),view.root.rect.height*1.1f,1.2f);
   StartCoroutine(AfterFinish(next));
  }
  IEnumerator AfterFinish(int next){
   yield return new WaitForSecondsRealtime(next>=0?2f:1.6f);
   if(!IsOpen)yield break;
   if(next>=0&&next<groups.Count){groupIndex=next;OpenGroup();}else Close();
  }

  // ------------------------------------------------------------------ QA helper (automated test)
  // Opens the cover, opens every box and places each unit on its right lane through the normal drop
  // code (no real input), then closes the cover so the round can finish.
  public IEnumerator QaPlayAll(){
   if(!IsOpen||view==null)yield break;
   if(coldKind)yield return AllDoors(true);
   for(int guard=0;guard<40&&IsOpen;guard++){
    var c=carts.FirstOrDefault(k=>!k.done&&!k.open);
    if(c==null){if(boxQueue.Count>0||carts.Any(k=>!k.done)){yield return new WaitForSecondsRealtime(.6f);continue;}break;}
    // Pull the tape the way a finger would, then let the box open.
    for(float pp=.1f;pp<.7f;pp+=.15f){PeelTape(c,pp,1);yield return new WaitForSecondsRealtime(.05f);}
    OpenBox(c);
    yield return new WaitForSecondsRealtime(1.3f);
    foreach(var u in c.pile.ToList()){
     var lane=FirstFreeLane(u.productId);
     if(lane==null||!IsOpen)break;
     if(!view.Reachable(lane.geo)){int dd=ClosedDoorOf(lane);ToggleDoor(dd);yield return new WaitForSecondsRealtime(.5f);}
     // Put the unit over its lane, as a drag would, then drop it.
     if(u.rect&&lane.rect)u.rect.position=lane.rect.position;
     DropUnit(u,view.dropArea);
     yield return new WaitForSecondsRealtime(.25f);
    }
   }
   yield return new WaitForSecondsRealtime(1f);
   if(coldKind&&view!=null)yield return AllDoors(false);
  }
 }

 // Tape on a cart box: the swipe pulls it off from the end where it started; at 70% the rest comes off.
 public sealed class CheckoutRestockTape:MonoBehaviour,IBeginDragHandler,IDragHandler,IEndDragHandler {
  RectTransform rect;Action<float,int> progress;Action done;bool active;int dir;float peeled;
  public void Init(RectTransform rect,Action<float,int> progress,Action done){this.rect=rect;this.progress=progress;this.done=done;}
  Vector2 Local(PointerEventData e){RectTransformUtility.ScreenPointToLocalPointInRectangle(rect,e.position,e.pressEventCamera,out var p);return p;}
  public void OnBeginDrag(PointerEventData e){if(!rect||done==null)return;active=true;if(dir==0)dir=Local(e).x<0?1:-1;}
  public void OnDrag(PointerEventData e){
   if(!active||!rect||done==null)return;
   float w=Mathf.Max(1,rect.rect.width),x=Local(e).x;
   float p=Mathf.Clamp01(dir>0?(x+w*.5f)/w:(w*.5f-x)/w);
   if(p<=peeled)return;peeled=p;progress?.Invoke(p,dir);
   if(peeled>=.7f){active=false;var d=done;done=null;d?.Invoke();}
  }
  public void OnEndDrag(PointerEventData e){active=false;}
 }
}
