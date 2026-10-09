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
 // ENTREGA: the supplier truck backs into the stockroom dock with every box waiting at the dock (snapshot.dock)
 // and the player puts them away, box by box, on the racks of the stockroom (src/services/receiving.ts).
 // Art: Blender renders from ArtSource/receiving/receiving_art.py (Resources/CheckoutDesktop/Receiving), drawn
 // in layers like REPOR so the 2D game reads as 3D: rack back < boxes < rack front (beams, uprights).
 //  · Secos (mercearia) on the first rack, Bebidas and Hortifrúti on the two bays of the second, refrigerated
 //    and frozen goods in the walk-in cold room behind the strip curtain.
 //  · What the stockroom already holds (snapshot.stockroom) stands on the racks, so the player sees it fill up.
 //  · The delivery note on the clipboard ticks each box; the last one gets the CONFERIDO stamp and the truck
 //    honks and drives off.
 //  · Every box sends unloadDelivery(id, units): the goods only become stock once they are on a rack.
 // Feel (Unpacking / Supermarket Simulator references): ghost of the place under the pointer, squash and a dust
 // puff on landing, heavier boxes sound lower, a combo for quick boxes, sparkles when a box joins its product.
 public sealed class CheckoutReceivingGame:MonoBehaviour {
  public static CheckoutReceivingGame Instance {get;private set;}
  public bool IsOpen=>window&&window.activeSelf;
  const string Dir="Receiving/";
  const float ComboWindow=2.4f,BoxScale=1.35f;
  static readonly Vector2 Mid=new Vector2(.5f,.5f);

  CheckoutBridge bridge;RectTransform root,stage;GameObject window,hint,toast;TextMeshProUGUI title;Image backdrop;AudioSource sound;
  AudioClip honk,thudLow,thudHigh,stampClip,whoosh;
  readonly List<GameObject> scene=new List<GameObject>();
  // The entries of the truck on the dock now (its delivery note lists them).
  DockEntry[] truckEntries=Array.Empty<DockEntry>();

  // ------------------------------------------------------------------ data from the art
  [Serializable] class JQuad {public int level,bay,index;public float[] fl,fr,bl,br;public float ppm,ppmBack;}
  [Serializable] class JFixture {public string key;public int[] size;public JQuad[] slots;public float[] sign;public float[] display;public float boxHeight;}
  [Serializable] class JTruck {public string key;public int[] size;public JQuad cargo;public float ppm,ppmBack,boxHeight;}
  [Serializable] class JLine {public float x0,x1,y;}
  [Serializable] class JClip {public int[] size;public float[] sheet;public JLine[] lines;}
  static T Load<T>(string name) where T:class{var t=Resources.Load<TextAsset>("CheckoutDesktop/"+Dir+name);return t?JsonUtility.FromJson<T>(t.text):null;}

  // A place for one box on a rack or in the cold room (stage pixels: bottom-centre of the box and its width).
  sealed class Place {public Fixture fixture;public string zone;public int level,bay,index;public Vector2 foot;public float width;public BoxView box;}
  sealed class Fixture {public string key,name;public RectTransform root,boxes;public Image back,front,sign;public TextMeshProUGUI label;public readonly List<Place> places=new List<Place>();public string[] bayZones;}
  sealed class BoxView {public RectTransform rect;public Image art;public int productId,units;public string deliveryId,zone,category;public CheckoutDragToken drag;public bool stored;}
  sealed class NoteLine {public string deliveryId;public int productId,total,done;public TextMeshProUGUI text;public Image check,strike;}

  readonly List<Fixture> fixtures=new List<Fixture>();readonly List<BoxView> truckBoxes=new List<BoxView>();readonly List<NoteLine> notes=new List<NoteLine>();
  RectTransform truckRoot,cargo,clipboard;Image ghost;Place ghostPlace;
  readonly Dictionary<string,int> roomLeft=new Dictionary<string,int>();
  int streak;float lastGood=-99,lastInput;bool finishing;

  public void Initialize(CheckoutBridge owner){
   Instance=this;bridge=owner;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.5f;
   honk=Honk();thudLow=U.Tone(70,.16f,55,.8f);thudHigh=U.Tone(140,.1f,110,.6f);stampClip=U.Tone(95,.12f,60,.9f);whoosh=U.Noise(.22f,.12f);
   root=U.Canvas(transform,"CheckoutReceivingGame",84);
   stage=U.GameWindow(root,"dock_backdrop",out window,out title,out backdrop,Close);
   var art=K.Icon(Dir+"receiving_backdrop");
   if(art&&backdrop){backdrop.sprite=art;var fit=backdrop.GetComponent<AspectRatioFitter>();if(fit)fit.aspectRatio=art.rect.width/Mathf.Max(1,art.rect.height);}
   window.SetActive(false);
  }

  // ------------------------------------------------------------------ public API
  public static bool HasArt=>K.Icon(Dir+"receiving_rack_back")!=null;
  public static void Show(){if(Instance)Instance.Open();}
  bool OtherGameOpen=>(CheckoutCounterGame.Instance&&CheckoutCounterGame.Instance.IsOpen)||(CheckoutIncidents.Instance&&CheckoutIncidents.Instance.IsOpen)||(CheckoutRestockGame.Instance&&CheckoutRestockGame.Instance.IsOpen)||(CheckoutStockroom.Instance&&CheckoutStockroom.Instance.IsOpen)||(CheckoutSupplierShop.Instance&&CheckoutSupplierShop.Instance.IsOpen)||(CheckoutPackingGame.Instance&&CheckoutPackingGame.Instance.IsOpen);

  void Open(){
   var dock=bridge.State?.dock;if(dock==null||dock.Length==0||OtherGameOpen)return;
   window.SetActive(true);window.transform.SetAsLastSibling();StopAllCoroutines();Clear();
   finishing=false;streak=0;lastGood=-99;lastInput=Time.unscaledTime;
   title.text="Receber entrega";Canvas.ForceUpdateCanvases();
   var truck=TruckOf(dock,dock[0]);BuildRoom();FillStockroom();LoadTruck(truck,true);BuildNote();
   StartCoroutine(IdleHints());
  }
  // One truck = one supplier order: the entries sharing the first one's orderId. A legacy entry without an id is a truck alone.
  static DockEntry[] TruckOf(DockEntry[] dock,DockEntry first){
   if(string.IsNullOrEmpty(first.orderId))return new[]{first};
   return dock.Where(d=>d.orderId==first.orderId).ToArray();
  }
  void Close(){StopAllCoroutines();Clear();window.SetActive(false);}
  void Clear(){
   foreach(var o in scene)if(o)Destroy(o);scene.Clear();if(hint)Destroy(hint);hint=null;toast=null;
   fixtures.Clear();truckBoxes.Clear();notes.Clear();roomLeft.Clear();truckRoot=cargo=clipboard=null;ghost=null;ghostPlace=null;
  }
  T Keep<T>(T c) where T:Component{scene.Add(c.gameObject);return c;}
  void Play(AudioClip clip,float pitch=1,float volume=1){if(!clip||!sound)return;sound.pitch=CheckoutRestockSound.Vary(pitch);sound.PlayOneShot(clip,volume);}
  static string Json(string s)=>"\""+(s??"").Replace("\\","\\\\").Replace("\"","\\\"")+"\"";
  float W=>stage.rect.width;float H=>stage.rect.height;

  // ------------------------------------------------------------------ the room: racks and cold room
  static readonly Dictionary<string,string> ZoneNames=new Dictionary<string,string>{{"mercearia","SECOS"},{"bebidas","BEBIDAS"},{"hortifruti","HORTIFRÚTI"},{"refrigerados","CÂMARA FRIA"}};
  static readonly Dictionary<string,string> ZoneColors=new Dictionary<string,string>{{"refrigerados","4FA3D9"},{"bebidas","F28C28"},{"hortifruti","5DA637"},{"mercearia","D9A032"}};

  void BuildRoom(){
   // Truck on the left third; secos, bebidas|hortifrúti and the cold room share the rest of the floor.
   float left=-W*.5f+W*.30f,right=W*.5f-W*.01f,slot=(right-left)/3f;
   AddFixture("rack","Secos",new[]{"mercearia","mercearia"},new Vector2(left+slot*.5f,-H*.03f),slot);
   AddFixture("rack","Bebidas · Hortifrúti",new[]{"bebidas","hortifruti"},new Vector2(left+slot*1.5f,-H*.03f),slot);
   AddFixture("coldroom","Câmara fria",new[]{"refrigerados"},new Vector2(left+slot*2.5f,-H*.03f),slot);
  }
  void AddFixture(string key,string name,string[] bays,Vector2 center,float slotWidth){
   var d=Load<JFixture>("receiving_"+key);
   // The rendered body takes about 60% of the image width: size the image so the body fills its slot.
   float aspect=d!=null&&d.size!=null?d.size[0]/(float)d.size[1]:1.6f;
   float w=slotWidth/.6f,h=w/aspect;if(h>H*.9f){h=H*.9f;w=h*aspect;}
   var f=new Fixture{key=key,name=name,bayZones=bays};
   f.root=Keep(N("Fixture "+key+" "+name,stage));U.At(f.root,Mid,new Vector2(w,h),center);
   U.Shadow(f.root,new Vector2(w*.62f,h*.08f),new Vector2(0,h*.05f));
   f.back=Layer(f.root,"Back",Dir+"receiving_"+key+"_back");
   f.boxes=N("Boxes",f.root);U.Stretch(f.boxes,Vector2.zero,Vector2.one);
   f.front=Layer(f.root,"Front",Dir+"receiving_"+key+"_front");
   // A hit area over the body (drops land on it).
   var hit=U.HitArea(N("Hit",f.root),"Area");((RectTransform)hit.transform.parent).anchorMin=new Vector2(.2f,.04f);((RectTransform)hit.transform.parent).anchorMax=new Vector2(.8f,.97f);
   ((RectTransform)hit.transform.parent).offsetMin=((RectTransform)hit.transform.parent).offsetMax=Vector2.zero;hit.raycastTarget=false;
   if(d?.slots!=null){
    float S=h/Mathf.Max(1,d.size[1]);
    foreach(var q in d.slots.OrderByDescending(q=>q.level).ThenBy(q=>q.bay).ThenBy(q=>q.index)){
     Vector2 P(float[] a)=>a!=null&&a.Length>1?new Vector2((a[0]-.5f)*w,(a[1]-.5f)*h):Vector2.zero;
     var fl=P(q.fl);var fr=P(q.fr);var bl=P(q.bl);var br=P(q.br);
     var foot=Vector2.Lerp((fl+fr)*.5f,(bl+br)*.5f,.42f);float width=Mathf.Lerp((fr-fl).magnitude,(br-bl).magnitude,.42f);
     string zone=bays[Mathf.Clamp(q.bay,0,bays.Length-1)];
     f.places.Add(new Place{fixture=f,zone=zone,level=q.level,bay=q.bay,index=q.index,foot=foot+center,width=width});
    }
   }
   // Sign: the zone names on the board on top (two bays: both names), in the zone colours.
   if(d?.sign!=null&&d.sign.Length>=4){
    var node=N("Sign",f.root);U.Stretch(node,new Vector2(d.sign[0],d.sign[1]),new Vector2(d.sign[2],d.sign[3]),new Vector2(8,2),new Vector2(-8,-2));
    f.label=U.Label(node,"Text",K.Headline,h*.05f,"0F5F59");U.Stretch(f.label.rectTransform,Vector2.zero,Vector2.one);
    f.label.enableAutoSizing=true;f.label.fontSizeMin=10;f.label.fontSizeMax=h*.055f;
    f.label.text=string.Join("  ·  ",bays.Distinct().Select(z=>$"<color=#{ZoneColors[z]}>{ZoneNames[z]}</color>"));
   }
   if(key=="coldroom"&&d?.display!=null&&d.display.Length>=4){
    // The thermometer of the cold room keeps blinking its temperature.
    var node=N("Display",f.root);U.Stretch(node,new Vector2(d.display[0],d.display[1]),new Vector2(d.display[2],d.display[3]));
    var glow=U.GlowAt(node,"Glow",new Color(.3f,1,.5f,.35f),Mid,h*.08f);StartCoroutine(Blink(glow));
   }
   fixtures.Add(f);
  }
  static RectTransform N(string name,Transform parent){var r=(RectTransform)new GameObject(name,typeof(RectTransform)).transform;r.SetParent(parent,false);return r;}
  static Image Layer(RectTransform parent,string name,string sprite){
   var img=new GameObject(name,typeof(RectTransform),typeof(Image)).GetComponent<Image>();img.transform.SetParent(parent,false);
   img.sprite=K.Icon(sprite);img.raycastTarget=false;img.preserveAspect=false;U.Stretch(img.rectTransform,Vector2.zero,Vector2.one);
   if(!img.sprite)img.color=new Color(1,1,1,0);return img;
  }
  IEnumerator Blink(Image img){while(img){img.color=new Color(.3f,1,.5f,.2f+.2f*Mathf.PingPong(Time.unscaledTime,1));yield return null;}}

  // ------------------------------------------------------------------ boxes
  // Which carton a product comes in: crates for produce, shrink-wrapped packs for drinks, frozen cartons for
  // the freezer, trays for bread and eggs, plain cardboard for the rest.
  static string BoxKind(string category){
   switch(category){
    case "hortifruti":case "organicos":return "crate";
    case "bebidas":case "refrigerantes":case "aguas":case "energeticos":case "alcoolicos":return "pack";
    case "congelados":case "sorvetes":return "frozen";
    case "padaria":case "ovos":return "tray";
    default:return "carton";
   }
  }
  // Heavy boxes land with a deeper thud.
  static float Weight(string category){switch(category){case "aguas":case "bebidas":case "refrigerantes":case "alcoolicos":case "limpeza":return .8f;case "padaria":case "doces":case "bolachas":case "chocolates":return 1.25f;default:return 1;}}

  BoxView MakeBox(RectTransform parent,int productId,int units,string category,float width){
   string kind=BoxKind(category);float size=width*BoxScale;
   var holder=new GameObject("Box",typeof(RectTransform),typeof(Image)).GetComponent<Image>();holder.transform.SetParent(parent,false);
   holder.color=new Color(1,1,1,0);holder.raycastTarget=false;var r=holder.rectTransform;r.anchorMin=r.anchorMax=Mid;r.pivot=new Vector2(.5f,.14f);r.sizeDelta=new Vector2(size,size);
   var art=new GameObject("Art",typeof(RectTransform),typeof(Image)).GetComponent<Image>();art.transform.SetParent(r,false);art.sprite=K.Icon(Dir+"box_"+kind);art.raycastTarget=false;U.Stretch(art.rectTransform,Vector2.zero,Vector2.one);
   if(!art.sprite){art.sprite=K.Icon("Game/cardboard_box");}
   // The label: the product and how many units the box holds.
   var label=Mark(kind);var node=N("Label",r);U.Stretch(node,label.min,label.max);
   var icon=new GameObject("Product",typeof(RectTransform),typeof(Image)).GetComponent<Image>();icon.transform.SetParent(node,false);
   icon.sprite=K.Icon($"Products/product-{productId:000}");icon.preserveAspect=true;icon.raycastTarget=false;U.Stretch(icon.rectTransform,new Vector2(0,0),new Vector2(.48f,1),new Vector2(2,2),new Vector2(0,-2));
   var count=U.Label(node,"Units",K.Headline,size*.12f,"4A3624");U.Stretch(count.rectTransform,new Vector2(.48f,0),Vector2.one);count.text=units+"×";
   count.enableAutoSizing=true;count.fontSizeMin=6;count.fontSizeMax=size*.14f;count.overflowMode=TextOverflowModes.Overflow;
   return new BoxView{rect=r,art=art,productId=productId,units=units,category=category};
  }
  static readonly Dictionary<string,Rect> labels=new Dictionary<string,Rect>();
  static Rect Mark(string kind){
   if(labels.TryGetValue(kind,out var r))return r;
   var t=Resources.Load<TextAsset>("CheckoutDesktop/"+Dir+"box_"+kind+"_marks");r=new Rect(.33f,.35f,.32f,.28f);
   if(t){var m=System.Text.RegularExpressions.Regex.Match(t.text,"\\[([^\\]]+)\\]");if(m.Success){var v=m.Groups[1].Value.Split(',').Select(x=>float.Parse(x.Trim(),System.Globalization.CultureInfo.InvariantCulture)).ToArray();if(v.Length>=4)r=Rect.MinMaxRect(v[0],v[1],v[2],v[3]);}}
   labels[kind]=r;return r;
  }

  // What the stockroom already holds stands on its racks, product next to product.
  void FillStockroom(){
   var held=bridge.State?.stockroom;if(held==null)return;
   foreach(var item in held.OrderBy(x=>x.productId)){
    for(int i=0;i<item.boxes;i++){
     var place=FreePlace(item.zone,item.productId,null);if(place==null)break;
     int units=i<item.boxes-1?item.caseSize:Mathf.Max(1,item.units-item.caseSize*(item.boxes-1));
     var box=MakeBox(place.fixture.boxes,item.productId,units,item.category,place.width);box.stored=true;Put(box,place);
     // A box already opened for the shelves shows it (lighter, a bit lower).
     if(units<item.caseSize)box.art.color=new Color(.93f,.9f,.86f,1);
    }
   }
  }
  void Put(BoxView box,Place place){
   place.box=box;box.rect.SetParent(place.fixture.boxes,false);box.rect.anchoredPosition=place.foot-(Vector2)place.fixture.root.anchoredPosition;
   float s=place.width*BoxScale;box.rect.sizeDelta=new Vector2(s,s);
   // Upper levels in front of the lower ones' tops, boxes further right on top of the left ones.
   var ordered=place.fixture.places.Where(p=>p.box!=null&&p.box.rect).OrderByDescending(p=>p.foot.y).ThenBy(p=>p.foot.x).ToList();
   for(int i=0;i<ordered.Count;i++)ordered[i].box.rect.SetSiblingIndex(i);
  }
  // A free place in the zone: next to boxes of the same product first, then the lowest, leftmost one.
  Place FreePlace(string zone,int productId,Vector2? near){
   var free=fixtures.SelectMany(f=>f.places).Where(p=>p.zone==zone&&p.box==null).ToList();if(free.Count==0)return null;
   if(near.HasValue)return free.OrderBy(p=>(p.foot-near.Value).sqrMagnitude).First();
   var friends=fixtures.SelectMany(f=>f.places).Where(p=>p.box!=null&&p.box.productId==productId).ToList();
   if(friends.Count>0)return free.OrderBy(p=>friends.Min(f=>(f.foot-p.foot).sqrMagnitude)).First();
   return free.OrderBy(p=>p.level).ThenBy(p=>p.bay).ThenBy(p=>p.index).First();
  }

  // ------------------------------------------------------------------ the truck
  void LoadTruck(DockEntry[] dock,bool driveIn){
   truckEntries=dock;
   var d=Load<JTruck>("receiving_truck");
   float h=H*.86f,aspect=d!=null&&d.size!=null?d.size[0]/(float)d.size[1]:1.6f,w=h*aspect;
   var home=new Vector2(-W*.5f+W*.155f,-H*.04f);
   truckRoot=Keep(N("Truck",stage));U.At(truckRoot,Mid,new Vector2(w,h),driveIn?home-new Vector2(W*.6f,0):home);truckRoot.SetSiblingIndex(0);
   Layer(truckRoot,"Back",Dir+"receiving_truck_back");
   cargo=N("Cargo",truckRoot);U.Stretch(cargo,Vector2.zero,Vector2.one);
   Layer(truckRoot,"Front",Dir+"receiving_truck_front");
   foreach(var e in dock){roomLeft[e.id]=e.room;}
   // Every box at the dock, mixed like a real load: back rows first, then the front, stacked in layers of 3 × 3.
   var boxes=new List<(DockEntry e,int units)>();
   foreach(var e in dock){int size=Mathf.Max(1,e.boxUnits);for(int left=Mathf.Max(0,e.quantity-e.unloaded);left>0;left-=size)boxes.Add((e,Mathf.Min(size,left)));}
   boxes=boxes.OrderBy(b=>b.e.productId*31%7).ThenBy(b=>b.e.productId).ToList();
   Vector2 P(float[] a)=>a!=null&&a.Length>1?new Vector2((a[0]-.5f)*w,(a[1]-.5f)*h):Vector2.zero;
   var q=d?.cargo;var fl=q!=null?P(q.fl):new Vector2(-w*.18f,-h*.27f);var fr=q!=null?P(q.fr):new Vector2(w*.18f,-h*.27f);
   var bl=q!=null?P(q.bl):new Vector2(-w*.12f,h*.01f);var br=q!=null?P(q.br):new Vector2(w*.12f,h*.01f);
   int shown=Mathf.Min(boxes.Count,27);
   for(int i=0;i<shown;i++){
    int layer=i/9,cell=i%9,row=2-cell/3,col=cell%3;   // fill the back row first
    float u=(col+.5f)/3f,t=(row+.5f)/3.2f;
    var front=Vector2.Lerp(fl,fr,u);var back=Vector2.Lerp(bl,br,u);var foot=Vector2.Lerp(front,back,t);
    float width=Mathf.Lerp((fr-fl).magnitude,(br-bl).magnitude,t)/3.3f;
    var (e,units)=boxes[i];
    var box=MakeBox(cargo,e.productId,units,e.category,width);box.deliveryId=e.id;box.zone=e.zone;
    var spot=foot+new Vector2(0,layer*width*.92f);box.rect.anchoredPosition=spot;
    var drag=U.Drag(box.rect.GetComponent<Image>());box.drag=drag;
    var b=box;var at=spot;drag.SetHome(at);
    drag.Setup(fixtures.Select(f=>f.root).ToArray(),target=>Drop(b,target),()=>{Miss(b);},()=>Grab(b));
    drag.Moved=local=>Hover(b,local);
    truckBoxes.Add(box);
   }
   // Draw order: back rows behind, upper layers on top.
   foreach(var bx in truckBoxes.OrderByDescending(x=>x.rect.anchoredPosition.y-(x.rect.anchoredPosition.y>0?0:0)).ThenBy(x=>x.rect.anchoredPosition.x))bx.rect.SetAsLastSibling();
   if(driveIn){Play(whoosh,.6f);StartCoroutine(Arrive(home));}
   if(boxes.Count>shown)Toast($"Mais {boxes.Count-shown} caixas no fundo do caminhão");
  }
  IEnumerator Arrive(Vector2 home){
   // Backs in, stops with a little bounce and a honk.
   yield return U.Move(truckRoot,home,.8f,true);Play(honk,1,.7f);
   StartCoroutine(U.Pop(truckRoot,1.02f,.25f));
  }

  // ------------------------------------------------------------------ dragging
  void Grab(BoxView box){
   lastInput=Time.unscaledTime;StopHint();Play(CheckoutRestockSound.Grab);
   // While carried the box leaves the truck's clipping and floats over everything.
   box.rect.SetParent(stage,true);box.rect.SetAsLastSibling();
  }
  void Hover(BoxView box,Vector2 local){
   var f=FixtureAt(local);var place=f!=null?FreePlace(box.zone,box.productId,local):null;
   if(place!=null&&place.fixture!=f)place=null;
   if(place==ghostPlace)return;ghostPlace=place;
   if(ghost){Destroy(ghost.gameObject);ghost=null;}
   if(place==null)return;
   // A see-through copy of the box shows where it will go.
   ghost=Keep(new GameObject("Ghost",typeof(RectTransform),typeof(Image)).GetComponent<Image>());ghost.transform.SetParent(place.fixture.boxes,false);
   ghost.sprite=box.art.sprite;ghost.raycastTarget=false;ghost.color=new Color(.75f,1,.75f,.55f);
   var r=ghost.rectTransform;r.anchorMin=r.anchorMax=Mid;r.pivot=new Vector2(.5f,.14f);float s=place.width*BoxScale;r.sizeDelta=new Vector2(s,s);
   r.anchoredPosition=place.foot-(Vector2)place.fixture.root.anchoredPosition;
  }
  Fixture FixtureAt(Vector2 local){
   foreach(var f in fixtures){var rr=f.root;var p=local-rr.anchoredPosition;var size=rr.sizeDelta;if(Mathf.Abs(p.x)<size.x*.3f&&p.y>-size.y*.5f&&p.y<size.y*.47f)return f;}
   return null;
  }
  void Miss(BoxView box){
   lastInput=Time.unscaledTime;if(ghost){Destroy(ghost.gameObject);ghost=null;}ghostPlace=null;
   // Back into the truck (the drag springs it home in stage space; it rejoins the cargo afterwards).
   StartCoroutine(Rejoin(box));Play(CheckoutRestockSound.Back);
  }
  IEnumerator Rejoin(BoxView box){yield return new WaitForSecondsRealtime(.4f);if(box!=null&&box.rect&&!box.stored&&cargo){box.rect.SetParent(cargo,true);}}

  bool Drop(BoxView box,RectTransform target){
   lastInput=Time.unscaledTime;
   var f=fixtures.FirstOrDefault(x=>x.root==target);var local=(Vector2)box.rect.anchoredPosition;
   if(box.rect.parent!=stage)local=U.LocalOf(stage,box.rect);
   if(ghost){Destroy(ghost.gameObject);ghost=null;}var chosen=ghostPlace;ghostPlace=null;
   if(f==null)return false;
   if(!f.bayZones.Contains(box.zone)){
    // Wrong place: the sign shakes red and the right one flashes.
    Play(CheckoutRestockSound.Wrong);streak=0;
    if(f.label)StartCoroutine(U.Shake(f.label.rectTransform,.35f,10));
    var right=fixtures.FirstOrDefault(x=>x.bayZones.Contains(box.zone));if(right?.label!=null)StartCoroutine(U.Pop(right.label.transform,1.25f,.35f));
    Toast(Wrong(box.zone));
    return false;
   }
   if(!roomLeft.TryGetValue(box.deliveryId,out var room)||room<box.units){
    Play(CheckoutRestockSound.Wrong,.85f);StartCoroutine(U.Shake(f.root,.3f,8));
    Toast("Depósito cheio para este produto! Venda um pouco ou amplie o estoque.");return false;
   }
   var place=chosen!=null&&chosen.fixture==f&&chosen.box==null?chosen:FreePlace(box.zone,box.productId,local);
   if(place==null){Play(CheckoutRestockSound.Wrong,.85f);Toast("Essa prateleira está lotada. Use outra parte do rack.");return false;}
   // Accepted: the app moves the units into stock.
   box.drag.Locked=true;box.stored=true;truckBoxes.Remove(box);roomLeft[box.deliveryId]=room-box.units;
   bridge.Command("unloadDelivery","["+Json(box.deliveryId)+","+box.units+"]");
   StartCoroutine(Land(box,place));
   Tick(box);
   if(truckBoxes.Count==0)StartCoroutine(Done());
   return true;
  }
  static string Wrong(string zone){
   switch(zone){
    case "refrigerados":return "Gelados vão para a câmara fria!";
    case "bebidas":return "Bebidas vão no rack de bebidas.";
    case "hortifruti":return "Hortifrúti vai no rack de hortifrúti.";
    default:return "Secos vão no rack de secos.";
   }
  }
  IEnumerator Land(BoxView box,Place place){
   var r=box.rect;place.box=box;
   // Fly to the place (stage space), then become part of the rack's layers.
   var to=place.foot;r.SetParent(stage,true);float s=place.width*BoxScale;
   StartCoroutine(U.Scale(r,new Vector3(s/Mathf.Max(1,r.sizeDelta.x),s/Mathf.Max(1,r.sizeDelta.y),1),.22f));
   yield return U.Move(r,to,.22f);
   if(!r)yield break;
   r.localScale=Vector3.one;Put(box,place);
   // Squash on landing, a puff of dust and a thud that depends on the weight.
   float w=Weight(box.category);Play(w<1?thudLow:thudHigh,w);Play(CheckoutRestockSound.Place(false),1,.6f);
   StartCoroutine(Squash(r));Dust(place);
   bool friend=place.fixture.places.Any(p=>p!=place&&p.box!=null&&p.box.productId==box.productId&&p.level==place.level&&Mathf.Abs(p.index-place.index+(p.bay-place.bay)*3)==1);
   if(friend){U.Sparkles(this,stage,place.foot+new Vector2(0,place.width*.6f),5,place.width*.9f);}
   Combo(place);
  }
  IEnumerator Squash(RectTransform r){
   float[] k={1.18f,.86f,1.06f,1f};float[] y={.82f,1.12f,.96f,1f};
   for(int i=0;i<k.Length;i++){if(!r)yield break;yield return U.Scale(r,new Vector3(k[i],y[i],1),.06f);}
  }
  void Dust(Place place){
   for(int i=0;i<5;i++){
    var p=U.GlowAt(stage,"Dust",new Color(.86f,.78f,.64f,.65f),Mid,place.width*.5f,place.foot+new Vector2((i-2)*place.width*.22f,place.width*.05f));
    Keep(p);StartCoroutine(Puff(p,(i-2)*place.width*.25f));
   }
  }
  IEnumerator Puff(Image p,float dx){
   var r=p.rectTransform;var from=r.anchoredPosition;var c=p.color;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.5f){if(!p)yield break;r.anchoredPosition=from+new Vector2(dx*t,18*t);r.localScale=Vector3.one*(1+t*1.2f);p.color=new Color(c.r,c.g,c.b,c.a*(1-t));yield return null;}
   if(p)Destroy(p.gameObject);
  }
  void Combo(Place place){
   float now=Time.unscaledTime;streak=now-lastGood<ComboWindow?streak+1:1;lastGood=now;
   if(streak<3)return;
   var label=Keep(U.Label(stage,"Combo",K.Headline,30,"FFFFFF"));U.At(label.rectTransform,Mid,new Vector2(260,50),place.foot+new Vector2(0,place.width*1.3f));
   label.text=$"Combo x{streak}!";label.outlineWidth=.25f;label.outlineColor=new Color32(200,90,20,255);
   StartCoroutine(FloatAway(label));
  }
  IEnumerator FloatAway(TextMeshProUGUI t){
   var r=t.rectTransform;var from=r.anchoredPosition;r.localScale=Vector3.zero;yield return U.Scale(r,Vector3.one,.18f,true);
   for(float k=0;k<1;k+=Time.unscaledDeltaTime/.8f){if(!t)yield break;r.anchoredPosition=from+new Vector2(0,50*k);t.alpha=1-k*k;yield return null;}
   if(t)Destroy(t.gameObject);
  }

  // ------------------------------------------------------------------ the delivery note
  void BuildNote(){
   var d=Load<JClip>("receiving_clipboard");var sprite=K.Icon(Dir+"receiving_clipboard");
   float h=H*.42f,w=h*(sprite?sprite.rect.width/sprite.rect.height:.75f);
   var img=Keep(new GameObject("Clipboard",typeof(RectTransform),typeof(Image)).GetComponent<Image>());img.transform.SetParent(stage,false);
   img.sprite=sprite;img.raycastTarget=false;if(!sprite)img.color=K.C("FFF7EC");
   clipboard=img.rectTransform;U.At(clipboard,new Vector2(0,0),new Vector2(w,h),new Vector2(w*.62f,h*.52f));clipboard.localRotation=Quaternion.Euler(0,0,4);
   var sheet=d?.sheet!=null&&d.sheet.Length>=4?Rect.MinMaxRect(d.sheet[0],d.sheet[1],d.sheet[2],d.sheet[3]):new Rect(.1f,.07f,.8f,.78f);
   var head=U.Label(clipboard,"Heading",K.Headline,h*.06f,"FFFFFF");U.Stretch(head.rectTransform,new Vector2(sheet.xMin,sheet.yMax-.08f),new Vector2(sheet.xMax,sheet.yMax-.005f));head.text="NOTA DE ENTREGA";
   head.enableAutoSizing=true;head.fontSizeMin=8;head.fontSizeMax=h*.06f;
   var lines=d?.lines??new JLine[0];
   var groups=truckEntries.Take(Mathf.Max(1,lines.Length)).ToList();
   for(int i=0;i<groups.Count;i++){
    var e=groups[i];float y=lines.Length>i?lines[i].y:sheet.yMax-.14f-i*.075f;float x0=lines.Length>i?lines[i].x0:sheet.xMin+.05f,x1=lines.Length>i?lines[i].x1:sheet.xMax-.05f;
    var row=N("Line "+i,clipboard);U.Stretch(row,new Vector2(x0,y),new Vector2(x1,y+.065f));
    var t=U.Label(row,"Text",K.Body,h*.045f,"4A3624",TextAlignmentOptions.Left);U.Stretch(t.rectTransform,Vector2.zero,new Vector2(.86f,1));t.enableAutoSizing=true;t.fontSizeMin=6;t.fontSizeMax=h*.045f;
    var check=U.Icon(row,"Check","Icons/success",new Vector2(.93f,.5f),new Vector2(h*.05f,h*.05f));check.color=new Color(1,1,1,0);
    var strike=N("Strike",row).gameObject.AddComponent<Image>();strike.color=new Color(.27f,.6f,.2f,0);strike.raycastTarget=false;U.Stretch(strike.rectTransform,new Vector2(0,.45f),new Vector2(0,.55f));
    int total=Mathf.Max(0,Mathf.CeilToInt((e.quantity-e.unloaded)/(float)Mathf.Max(1,e.boxUnits)));
    var line=new NoteLine{deliveryId=e.id,productId=e.productId,total=total,done=0,text=t,check=check,strike=strike};notes.Add(line);NoteText(line,e.productName);
   }
  }
  void NoteText(NoteLine l,string name){if(l.text)l.text.text=$"{name}  <b>{l.done}/{l.total}</b>";}
  void Tick(BoxView box){
   var l=notes.FirstOrDefault(n=>n.deliveryId==box.deliveryId);if(l==null)return;
   l.done=Mathf.Min(l.total,l.done+1);var name=bridge.State?.dock?.FirstOrDefault(d=>d.id==l.deliveryId)?.productName??"";NoteText(l,name);
   Play(CheckoutRestockSound.Place(false),1.6f,.35f);StartCoroutine(U.Pop(l.text.transform,1.12f,.2f));
   if(l.done>=l.total){StartCoroutine(U.Tint(l.check,Color.white,.2f));StartCoroutine(Strike(l));}
  }
  IEnumerator Strike(NoteLine l){
   if(!l.strike)yield break;l.strike.color=new Color(.27f,.6f,.2f,.8f);var r=l.strike.rectTransform;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.25f){if(!r)yield break;r.anchorMax=new Vector2(.86f*t,.55f);yield return null;}
   if(r)r.anchorMax=new Vector2(.86f,.55f);
  }

  // ------------------------------------------------------------------ the end: stamp, honk, drive off
  IEnumerator Done(){
   if(finishing)yield break;finishing=true;
   yield return new WaitForSecondsRealtime(.5f);
   for(float t=0;t<3&&bridge.HasPending("unloadDelivery");t+=.1f)yield return new WaitForSecondsRealtime(.1f);
   // The stamp slams on the delivery note.
   if(clipboard){
    var stamp=Keep(new GameObject("Stamp",typeof(RectTransform),typeof(Image)).GetComponent<Image>());stamp.transform.SetParent(clipboard,false);
    stamp.sprite=K.Icon(Dir+"stamp_conferido");stamp.raycastTarget=false;var r=stamp.rectTransform;U.At(r,new Vector2(.5f,.32f),Vector2.one*clipboard.sizeDelta.x*.85f);
    r.localRotation=Quaternion.Euler(0,0,-14);r.localScale=Vector3.one*2.2f;stamp.color=new Color(1,1,1,0);
    StartCoroutine(U.Tint(stamp,Color.white,.12f));yield return U.Scale(r,Vector3.one,.14f);
    Play(stampClip,1,1);StartCoroutine(U.Shake(clipboard,.2f,6));U.Sparkles(this,stage,U.LocalOf(stage,r),8,140);
   }
   Play(CheckoutRestockSound.Done);
   yield return new WaitForSecondsRealtime(.8f);
   // Whatever did not fit stays on the truck (a full stockroom).
   var left=bridge.State?.dock?.Where(d=>d.quantity-d.unloaded>0).ToArray();
   // The first entry that is new or still fits names the next truck (its order's entries come with it).
   var pick=left?.FirstOrDefault(d=>notes.All(n=>n.deliveryId!=d.id)||d.room>0);
   if(pick!=null){
    // More trucks waited behind (or boxes that did not fit the first trip): the next load comes in.
    Play(honk,1.1f,.6f);yield return Leave();yield return new WaitForSecondsRealtime(.3f);
    if(!window.activeSelf)yield break;Clear();window.SetActive(true);finishing=false;BuildRoom();FillStockroom();LoadTruck(TruckOf(left,pick),true);BuildNote();yield break;
   }
   Play(honk,1,.8f);yield return Leave();
   yield return new WaitForSecondsRealtime(.5f);Close();
  }
  IEnumerator Leave(){if(!truckRoot)yield break;Play(whoosh,.5f);yield return U.Move(truckRoot,truckRoot.anchoredPosition-new Vector2(W*.7f,0),.7f);}

  // ------------------------------------------------------------------ hints and messages
  IEnumerator IdleHints(){
   while(window.activeSelf){
    yield return new WaitForSecondsRealtime(1f);
    if(hint||finishing||Time.unscaledTime-lastInput<5f)continue;
    var box=truckBoxes.LastOrDefault();if(box==null)continue;
    var place=FreePlace(box.zone,box.productId,null);if(place==null)continue;
    var b=box;var p=place;
    hint=U.Hint(this,stage,()=>b.rect&&!b.stored?U.LocalOf(stage,b.rect):throw new Exception(),()=>p.foot);
   }
  }
  void StopHint(){if(hint)Destroy(hint);hint=null;}
  void Toast(string text){
   if(toast)Destroy(toast);
   var plate=Keep(U.Shape(stage,"Toast","4A3624",20,new Vector2(.5f,1),new Vector2(W*.6f,56),new Vector2(0,-44)));toast=plate.gameObject;
   var label=U.Label(plate.transform,"Text",K.Headline,22,"FFFFFF");U.Stretch(label.rectTransform,Vector2.zero,Vector2.one,new Vector2(16,0),new Vector2(-16,0));label.text=text;label.enableAutoSizing=true;label.fontSizeMin=12;label.fontSizeMax=22;
   StartCoroutine(U.Pop(plate.rectTransform,1.06f,.22f));StartCoroutine(DropLater(plate.gameObject,2.4f));
  }
  IEnumerator DropLater(GameObject o,float delay){yield return new WaitForSecondsRealtime(delay);if(o)Destroy(o);}

  // Two-tone truck horn (beep-beep).
  static AudioClip Honk(){
   int rate=22050,count=(int)(rate*.5f);var data=new float[count];
   for(int i=0;i<count;i++){float t=i/(float)rate;bool on=t<.18f||(t>.26f&&t<.46f);float env=on?1:0;
    data[i]=env*.35f*(Mathf.Sign(Mathf.Sin(2*Mathf.PI*392*t))*.5f+Mathf.Sin(2*Mathf.PI*494*t)*.5f)*Mathf.Clamp01(1-Mathf.Abs(t-.23f)*.6f);}
   var clip=AudioClip.Create("honk",count,1,rate,false);clip.SetData(data,0);return clip;
  }

  void Update(){
   if(!IsOpen)return;
   if(Input.GetKeyDown(KeyCode.Escape))Close();
  }
 }
}
