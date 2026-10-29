using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // DELIVERY packing challenge, played INSIDE the stockroom: the order's bags stand on the restock cart on the left,
 // the order slip is the receiving clipboard, and the units come straight out of the boxes on the racks (the same
 // racks as the receiving room). A press-and-drag on a box takes one unit out; a unit dropped on the right bag goes
 // in, anything else flies back into its box. Kraft bags rip over 8 kg (a spare slides in). One twist per order
 // (seeded by the order id), a par time, a combo, and a substitution only when the stockroom really lacks a product.
 // Sealing sends packDeliveryOrder with only the correct ordered units and quality = score (0..1).
 // Partial files: Room (racks, boxes, stock on the shelves), Plan (twist, par, substitution), Score (sealing, result).
 public sealed partial class CheckoutPackingGame:MonoBehaviour {
  public static CheckoutPackingGame Instance {get;private set;}
  public bool IsOpen=>window&&window.activeSelf;
  const float ComboWindow=2.4f,IdleAfter=8f,BagLimit=8f;
  const int KindOrdered=0,KindExtra=1,KindWrong=2;
  static readonly Vector2 Mid=new Vector2(.5f,.5f);
  static readonly HashSet<string> ColdCats=new HashSet<string>{"congelados","sorvetes","carnes","peixes","frios","laticinios"};
  static readonly HashSet<string> FragileCats=new HashSet<string>{"ovos","padaria","hortifruti"};
  static readonly Color[] Stickers={K.C("2E8CAE"),K.C("F28C28"),K.C("5DA637"),K.C("D9A032"),K.C("E15533"),K.C("8E6BBF")};
  static readonly Dictionary<string,Sprite> generated=new Dictionary<string,Sprite>();

  CheckoutBridge bridge;RectTransform root,stage,board,clipboard,bagLayer,fx,cartNode;GameObject window,modal,toast;
  TextMeshProUGUI title,timerLabel;Image backdropImage,timerFill;CanvasGroup banner;CheckoutDesktopButton sealButton;AudioSource sound;
  Bag kraft,thermal;Bag hoveredBagRef;PackBox hoveredBox,hintBox;
  readonly List<Bag> allBags=new List<Bag>();readonly List<Bag> bags=new List<Bag>();
  readonly List<Token> tokens=new List<Token>();readonly List<Line> lines=new List<Line>();
  RectTransform[] dropTargets=new RectTransform[0];
  string orderId;DeliveryOrder order;
  float tokenSize,lastInput,lastDrop=-99,elapsed,parSec,cartX0,cartY0,cartW,cartH;
  int streak,requiredTotal,requiredPlaced,substMistakes;
  bool sealing,ended,ready,bannerGone,running,pendingSubst;

  // ------------------------------------------------------------------ data
  sealed class Bag {public string kind;public bool cold,active,spare;public RectTransform node,inside,drop;public Image back,front,glow,closed;
   public float[] mouth,floor,sticker;public float kg,limit=BagLimit;public Vector2 rest;public readonly List<Token> items=new List<Token>();}
  sealed class Token {public RectTransform root,body;public Image glow,icon;public CheckoutDragToken drag;
   public int productId,lineIndex,kind;public string name,category;public bool cold,fragile,placed;public float size,kg;public PackBox source;public Bag bag;
   public bool required=>kind==KindOrdered;}
  sealed class Line {public int productId,quantity,need,done;public string name,category;public TextMeshProUGUI text;public Image check,strike;public bool substituted;public float strikeFrom;}
  // Bag art layout (Resources/CheckoutDesktop/Delivery/bag_solo.json): the sprite-normalised mouth and floor.
  [Serializable] class BagJson {public int[] size;public float[] mouth,floor;}
  [Serializable] class BagsJson {public BagJson kraft,thermal;}
  [Serializable] class DeckJson {public float[] fl,fr,bl,br;}
  [Serializable] class CartJson {public int[] cartSize;public DeckJson deck;}

  public void Initialize(CheckoutBridge owner){
   Instance=this;bridge=owner;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.5f;
   root=U.Canvas(transform,"CheckoutPackingGame",86);
   stage=U.GameWindow(root,"dock_backdrop",out window,out title,out backdropImage,Dismiss);
   // The receiving room's backdrop: the same stockroom as the receiving game.
   var art=K.Icon(RoomDir+"receiving_backdrop");
   if(art&&backdropImage){backdropImage.sprite=art;var fit=backdropImage.GetComponent<AspectRatioFitter>();if(fit)fit.aspectRatio=art.rect.width/Mathf.Max(1,art.rect.height);}
   window.SetActive(false);
  }

  // ------------------------------------------------------------------ public API
  public static void Show(string orderId){if(Instance)Instance.Open(orderId);}
  bool OtherGameOpen=>(CheckoutCounterGame.Instance&&CheckoutCounterGame.Instance.IsOpen)||(CheckoutIncidents.Instance&&CheckoutIncidents.Instance.IsOpen)||(CheckoutRestockGame.Instance&&CheckoutRestockGame.Instance.IsOpen)||(CheckoutReceivingGame.Instance&&CheckoutReceivingGame.Instance.IsOpen)||(CheckoutStockroom.Instance&&CheckoutStockroom.Instance.IsOpen);
  float W=>stage.rect.width;float H=>stage.rect.height;

  static string Json(string s)=>"\""+(s??"").Replace("\\","\\\\").Replace("\"","\\\"")+"\"";
  static RectTransform Node(string name,Transform parent)=>CheckoutDesktopCard.Node(name,parent);
  void PlayClip(AudioClip clip,float volume=.5f){if(!clip||!sound)return;sound.pitch=CheckoutRestockSound.Vary(1);sound.PlayOneShot(clip,volume);}
  static float Ease(float t)=>1-Mathf.Pow(1-t,3);
  static string Initials(string name){
   var parts=(name??"").Split(new[]{' '},StringSplitOptions.RemoveEmptyEntries);
   if(parts.Length==0)return "?";
   return new string(parts.Take(2).Select(p=>char.ToUpperInvariant(p[0])).ToArray());
  }
  static string Clock(float seconds){int s=Mathf.Max(0,Mathf.RoundToInt(seconds));return string.Format(CultureInfo.InvariantCulture,"{0}:{1:00}",s/60,s%60);}
  static T LoadJson<T>(string path) where T:class{var t=Resources.Load<TextAsset>("CheckoutDesktop/"+path);if(!t)return null;try{return JsonUtility.FromJson<T>(t.text);}catch(Exception){return null;}}

  DeliveryOrder Find(string id){
   var orders=bridge.State?.delivery?.orders;if(orders==null||string.IsNullOrEmpty(id))return null;
   foreach(var o in orders)if(o!=null&&o.id==id)return o;return null;
  }

  void Open(string id){
   var o=Find(id);if(o==null||o.status!="aceito"||OtherGameOpen||window.activeSelf)return;
   order=o;orderId=id;sealing=false;ended=false;ready=false;streak=0;lastDrop=-99;bannerGone=false;running=false;elapsed=0;
   lastInput=Time.unscaledTime;hoveredBox=null;hoveredBagRef=null;hintBox=null;substMistakes=0;pendingSubst=false;
   window.SetActive(true);window.transform.SetAsLastSibling();StopAllCoroutines();Clear();
   title.text=string.IsNullOrEmpty(o.customerName)?"Montar pedido · Cliente":string.Format("Montar pedido · {0}",o.customerName);
   Canvas.ForceUpdateCanvases();
   board=Node("Board",stage);U.Stretch(board,Vector2.zero,Vector2.one);
   fx=Node("Fx",board);U.Stretch(fx,Vector2.zero,Vector2.one);
   tokenSize=Mathf.Max(90f,H*.11f);
   BuildRoom();
   var shown=FillStockroom();
   BuildCart();
   BuildBags();
   PrepareLines(shown);
   PlanOrder();
   BuildClipboard();
   BuildBanner();BuildButton();BuildPill();
   if(lines.Count==0||lines.All(l=>l.need<=0))Toast("Nada disponível no estoque para este pedido.");
   CheckDone();
   StartCoroutine(Intro());
  }

  void Close(){StopAllCoroutines();Clear();if(window)window.SetActive(false);sealing=false;ended=false;ready=false;running=false;}
  void Clear(){
   if(board)Destroy(board.gameObject);
   board=null;fx=null;clipboard=null;bagLayer=null;cartNode=null;sealButton=null;timerFill=null;timerLabel=null;toast=null;banner=null;
   kraft=null;thermal=null;hoveredBox=null;hoveredBagRef=null;hintBox=null;modal=null;
   allBags.Clear();bags.Clear();tokens.Clear();lines.Clear();roomFixtures.Clear();roomBoxes.Clear();dropTargets=new RectTransform[0];
   pillBack=null;pillText=null;rackLayer=null;pill=null;
  }
  void Dismiss(){if(sealing||!window.activeSelf)return;Close();}

  // ------------------------------------------------------------------ geometry (stage pixels, origin bottom-left)
  Vector2 StagePos(float x,float y)=>new Vector2(x-W*.5f,y-H*.5f);
  // The cart is the bottom-left of the packing station; its deck quad is read from restock_cart.json.
  void BuildCart(){
   var d=LoadJson<CartJson>("Restock/restock_cart");
   Vector2 cartPx=d!=null&&d.cartSize!=null&&d.cartSize.Length>=2?new Vector2(d.cartSize[0],d.cartSize[1]):new Vector2(1079,819);
   float margin=Mathf.Max(10f,W*.012f),leftW=W*.30f;
   cartH=Mathf.Min(H*.40f,(leftW-2*margin)*cartPx.y/cartPx.x);cartW=cartH*cartPx.x/cartPx.y;
   cartX0=margin;cartY0=margin;
   cartNode=Node("Cart",board);U.At(cartNode,Mid,new Vector2(cartW,cartH),StagePos(cartX0+cartW*.5f,cartY0+cartH*.5f));
   var img=new GameObject("Art",typeof(RectTransform),typeof(Image)).GetComponent<Image>();img.transform.SetParent(cartNode,false);
   img.sprite=K.Icon("Restock/restock_cart");img.raycastTarget=false;img.preserveAspect=false;U.Stretch(img.rectTransform,Vector2.zero,Vector2.one);
   bagLayer=Node("Bags",board);U.Stretch(bagLayer,Vector2.zero,Vector2.one);
  }
  // A point on the cart deck in stage pixels (u across, v from the front edge to the back edge).
  Vector2 DeckPoint(float u,float v){
   var d=LoadJson<CartJson>("Restock/restock_cart");var q=d?.deck;
   Vector2 fl=V2(q?.fl,new Vector2(.085f,.23f)),fr=V2(q?.fr,new Vector2(.82f,.23f)),bl=V2(q?.bl,new Vector2(.15f,.40f)),br=V2(q?.br,new Vector2(.77f,.40f));
   var p=Vector2.Lerp(Vector2.Lerp(fl,fr,u),Vector2.Lerp(bl,br,u),v);
   return new Vector2(cartX0+p.x*cartW,cartY0+p.y*cartH);
  }
  float DeckWidth()=>(V2(null,new Vector2(.82f,0)).x-V2(null,new Vector2(.085f,0)).x)*cartW;
  static Vector2 V2(float[] a,Vector2 fallback)=>a!=null&&a.Length>=2?new Vector2(a[0],a[1]):fallback;

  // ------------------------------------------------------------------ bags (kraft and thermal, spares for the rip)
  void BuildBags(){
   var items=order.items??new DeliveryItem[0];
   bool needKraft=items.Any(i=>i!=null&&!ColdCats.Contains(i.category??""));
   bool needThermal=items.Any(i=>i!=null&&ColdCats.Contains(i.category??""));
   var d=LoadJson<BagsJson>("Delivery/bag_solo");
   // Both bags on the deck: the body height is the same for both, shrunk so the two fit side by side.
   float bagH=H*.30f;
   float kAsp=AspectOf(d?.kraft,537f/759f),tAsp=AspectOf(d?.thermal,855f/912f);
   if(needKraft&&needThermal){float total=bagH*(kAsp+tAsp);float deck=DeckWidth()*.95f;if(total>deck)bagH*=deck/total;}
   // The thermal bag goes first (behind); the kraft bag stands in front of it.
   float uKraft=needThermal?.30f:.5f;
   if(needThermal)thermal=MakeBag("thermal",true,d?.thermal,bagH,.72f,true);
   if(needKraft){
    kraft=MakeBag("kraft",false,d?.kraft,bagH,uKraft,true);
    // Two spares wait beside the kraft bag, hidden until a bag rips.
    allBags.Add(MakeBag("kraft",false,d?.kraft,bagH,Mathf.Clamp(uKraft+.24f,.08f,.92f),false));
    allBags.Add(MakeBag("kraft",false,d?.kraft,bagH,Mathf.Clamp(uKraft-.24f,.08f,.92f),false));
   }
   if(kraft!=null)allBags.Insert(0,kraft);
   if(thermal!=null)allBags.Insert(0,thermal);
   foreach(var b in allBags)if(!b.spare)bags.Add(b);
   dropTargets=allBags.Select(b=>b.drop).ToArray();
   fx.SetAsLastSibling();
  }
  static float AspectOf(BagJson j,float fallback)=>j!=null&&j.size!=null&&j.size.Length>=2?j.size[0]/(float)j.size[1]:fallback;
  Bag MakeBag(string kind,bool cold,BagJson j,float bagH,float u,bool active){
   float[] mouth=j!=null&&j.mouth!=null&&j.mouth.Length>=4?j.mouth:(kind=="kraft"?new[]{.174f,.8301f,.9345f,.886f}:new[]{.3349f,.5789f,.824f,.6386f});
   float[] floor=j!=null&&j.floor!=null&&j.floor.Length>=4?j.floor:(kind=="kraft"?new[]{.233f,.273f,.9335f,.3451f}:new[]{.3349f,.2553f,.8173f,.3306f});
   float aspect=AspectOf(j,kind=="kraft"?537f/759f:855f/912f);
   var b=new Bag{kind=kind,cold=cold,active=active,spare=!active,mouth=mouth,floor=floor,sticker=kind=="kraft"?new[]{.3481f,.5346f}:new[]{.5383f,.4928f}};
   float bw=bagH*aspect,bh=bagH;
   var deck=DeckPoint(u,.5f);
   // The sprite's floor edge stands on the deck; the node is centred on the sprite.
   b.rest=StagePos(deck.x,deck.y+(.5f-floor[1])*bh);
   b.node=Node("Bag "+kind,bagLayer);b.node.anchorMin=b.node.anchorMax=Mid;b.node.pivot=Mid;b.node.sizeDelta=new Vector2(bw,bh);b.node.anchoredPosition=b.rest;
   string tag=kind+"_";
   string key="Delivery/bag_"+(cold?"thermal":"kraft")+"_";
   b.back=BagLayer(b.node,"Back",key+"back_solo",cold?K.C("5FA8C9"):K.C("C49A5C"));
   b.inside=Node("Inside",b.node);U.Stretch(b.inside,Vector2.zero,Vector2.one);
   b.front=BagLayer(b.node,"Front",key+"front_solo",cold?K.C("8CC4DC"):K.C("D9B27A"));
   b.glow=U.Box(b.node,"Glow","FFFFFF",0,Vector2.zero,Vector2.one);b.glow.sprite=U.Glow();b.glow.color=new Color(1,1,1,0);
   b.closed=BagLayer(b.node,"Closed",key+"closed_solo",cold?K.C("5FA8C9"):K.C("C49A5C"));b.closed.gameObject.SetActive(false);
   // The drop area: the whole bag body plus a margin above the mouth (forgiving, not just the thin mouth strip).
   b.drop=Node("Drop "+tag,b.node);
   b.drop.anchorMin=new Vector2(Mathf.Clamp01(mouth[0]-.03f),Mathf.Clamp01(floor[1]));
   b.drop.anchorMax=new Vector2(Mathf.Clamp01(mouth[2]+.03f),Mathf.Clamp01(mouth[3]+.10f));
   b.drop.offsetMin=b.drop.offsetMax=Vector2.zero;
   b.node.gameObject.SetActive(active);
   return b;
  }
  Image BagLayer(RectTransform parent,string name,string sprite,Color fallback){
   var img=new GameObject(name,typeof(RectTransform),typeof(Image)).GetComponent<Image>();img.transform.SetParent(parent,false);
   img.sprite=K.Icon(sprite);img.raycastTarget=false;img.preserveAspect=false;U.Stretch(img.rectTransform,Vector2.zero,Vector2.one);
   if(!img.sprite)img.color=fallback;return img;
  }
  // The spare bag slides in from the right, then joins the bags that take units.
  void ActivateSpare(Bag b){
   b.active=true;b.spare=false;bags.Add(b);b.node.gameObject.SetActive(true);
   StartCoroutine(SlideIn(b));
  }
  IEnumerator SlideIn(Bag b){
   if(!b.node)yield break;b.node.anchoredPosition=b.rest+new Vector2(W*.35f,0);
   yield return U.Move(b.node,b.rest,.45f,true);
   if(b.node)yield return Squash(b.node);
  }
  Bag NextSpare(string kind){return allBags.FirstOrDefault(b=>b.spare&&!b.active&&b.kind==kind);}

  // ------------------------------------------------------------------ the order slip (receiving clipboard)
  void BuildClipboard(){
   var d=RoomLoad<RoomClipJson>("receiving_clipboard");var sprite=K.Icon(RoomDir+"receiving_clipboard");
   float margin=Mathf.Max(10f,W*.012f),leftW=W*.30f;
   float h=Mathf.Min(H*.52f,(leftW-2*margin)/(sprite?sprite.rect.width/sprite.rect.height:.75f));
   float w=h*(sprite?sprite.rect.width/sprite.rect.height:.75f);
   var img=Node("Clipboard",board).gameObject.AddComponent<Image>();
   img.sprite=sprite;img.raycastTarget=false;if(!sprite)img.color=K.C("FFF7EC");
   clipboard=img.rectTransform;U.At(clipboard,Mid,new Vector2(w,h),StagePos(margin+w*.5f,H-margin-h*.5f));clipboard.localRotation=Quaternion.Euler(0,0,2);
   var sheet=d?.sheet!=null&&d.sheet.Length>=4?Rect.MinMaxRect(d.sheet[0],d.sheet[1],d.sheet[2],d.sheet[3]):new Rect(.1f,.07f,.8f,.78f);
   var head=U.Label(clipboard,"Heading",K.Headline,h*.06f,"FFFFFF");U.Stretch(head.rectTransform,new Vector2(sheet.xMin,sheet.yMax-.08f),new Vector2(sheet.xMax,sheet.yMax-.005f));
   head.text=string.IsNullOrEmpty(order.customerName)?"PEDIDO · Cliente":string.Format("PEDIDO · {0}",order.customerName);
   head.enableAutoSizing=true;head.fontSizeMin=11;head.fontSizeMax=h*.065f;
   var slots=d?.lines??new RoomClipLine[0];
   bool hasNote=!string.IsNullOrEmpty(order.note);
   int rowSlots=Mathf.Max(1,slots.Length-1-(hasNote?1:0));
   for(int i=0;i<lines.Count&&i<rowSlots;i++){
    var line=lines[i];int si=i+1;
    float y=slots.Length>si?slots[si].y:sheet.yMax-.14f-i*.075f;float x0=slots.Length>si?slots[si].x0:sheet.xMin+.05f,x1=slots.Length>si?slots[si].x1:sheet.xMax-.05f;
    var row=Node("Line "+i,clipboard);U.Stretch(row,new Vector2(x0,y),new Vector2(x1,y+.065f));
    var t=U.Label(row,"Text",K.Body,h*.055f,"4A3624",TextAlignmentOptions.Left);U.Stretch(t.rectTransform,Vector2.zero,new Vector2(.86f,1));
    t.enableAutoSizing=true;t.fontSizeMin=11;t.fontSizeMax=h*.055f;t.overflowMode=TextOverflowModes.Overflow;
    var check=U.Icon(row,"Check","Icons/success",new Vector2(.93f,.5f),new Vector2(h*.05f,h*.05f));check.color=new Color(1,1,1,0);check.gameObject.SetActive(false);
    var strike=Node("Strike",row).gameObject.AddComponent<Image>();strike.color=new Color(.27f,.6f,.2f,0);strike.raycastTarget=false;
    U.Stretch(strike.rectTransform,new Vector2(0,.45f),new Vector2(0,.55f));
    line.text=t;line.check=check;line.strike=strike;RefreshLine(line);
   }
   if(hasNote&&slots.Length>0){
    var last=slots[slots.Length-1];var note=Node("Note",clipboard);U.Stretch(note,new Vector2(last.x0,last.y),new Vector2(last.x1,last.y+.065f));
    var t=U.Label(note,"Text",K.Body,h*.04f,"8A7560",TextAlignmentOptions.Left);U.Stretch(t.rectTransform,Vector2.zero,Vector2.one);
    t.enableAutoSizing=true;t.fontSizeMin=10;t.fontSizeMax=h*.045f;t.text="“"+order.note+"”";
   }
   // The par timer: a bar under the sheet that empties towards the par time.
   var timer=Node("Timer",board);U.At(timer,Mid,new Vector2(w*.9f,22),StagePos(margin+w*.5f,H-margin-h-22));
   var bg=CheckoutDesktopCard.Image(timer,"Bg",K.C("DDCBB0"),9);U.Stretch(bg.rectTransform,Vector2.zero,Vector2.one);
   timerFill=CheckoutDesktopCard.Image(timer,"Fill",K.C("5DA637"),9);U.Stretch(timerFill.rectTransform,Vector2.zero,Vector2.one);
   timerLabel=U.Label(timer,"Label",K.Body,14,"FFFFFF");timerLabel.enableAutoSizing=true;timerLabel.fontSizeMin=10;timerLabel.fontSizeMax=14;U.Stretch(timerLabel.rectTransform,Vector2.zero,Vector2.one);timerLabel.text="";
  }
  void RefreshLine(Line line){
   if(!line.text)return;
   int missing=line.quantity-line.need;
   string s=line.name+"  <b>"+line.done+"/"+line.need+"</b>";
   if(line.substituted)s+="  <color=#2E8CAE>(subst.)</color>";
   else if(missing>0)s+="  <color=#B03A2E>-"+missing+"</color>";
   line.text.text=s;
  }
  void CompleteLine(Line line){
   if(line.check){line.check.gameObject.SetActive(true);var cr=line.check.rectTransform;cr.localScale=Vector3.zero;StartCoroutine(U.Scale(cr,Vector3.one,.25f,true));}
   if(line.strike)StartCoroutine(StrikeRoutine(line.strike));
  }
  void UncompleteLine(Line line){
   if(line.check)line.check.gameObject.SetActive(false);
   if(line.strike)line.strike.rectTransform.anchorMax=new Vector2(0,.55f);
  }
  static IEnumerator StrikeRoutine(Image strike){
   if(!strike)yield break;strike.color=new Color(.3f,.6f,.2f,.8f);var r=strike.rectTransform;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.3f){if(!r)yield break;r.anchorMax=new Vector2(Ease(t)*.86f,.55f);yield return null;}
   if(r)r.anchorMax=new Vector2(.86f,.55f);
  }

  // ------------------------------------------------------------------ banner, seal button, hover pill
  void BuildBanner(){
   float bw=Mathf.Min(W*.5f,700f);
   var plate=U.Shape(board,"Banner","4A3624",22,new Vector2(.5f,0),new Vector2(bw,56),new Vector2(0,20));
   banner=plate.gameObject.AddComponent<CanvasGroup>();
   var lbl=U.Label(plate.transform,"Text",K.Headline,24,"FFFFFF");
   U.Stretch(lbl.rectTransform,Vector2.zero,Vector2.one,new Vector2(18,0),new Vector2(-18,0));
   lbl.text="Tire unidades das caixas e leve para a sacola certa";
   lbl.enableAutoSizing=true;lbl.fontSizeMin=12;lbl.fontSizeMax=24;
  }
  static IEnumerator FadeGroup(CanvasGroup g,float to,float seconds){
   if(!g)yield break;float from=g.alpha;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/Mathf.Max(.01f,seconds)){if(!g)yield break;g.alpha=Mathf.Lerp(from,to,t);yield return null;}
   if(g)g.alpha=to;
  }
  void BuildButton(){
   sealButton=U.Button(board,"Fechar pedido","success",()=>Seal(),64,26);
   var rt=(RectTransform)sealButton.transform;
   U.At(rt,new Vector2(1,0),new Vector2(260,64),new Vector2(-18,18));
   rt.pivot=new Vector2(1,0);rt.anchoredPosition=new Vector2(-18,18); // fully inside the bottom-right corner
   sealButton.gameObject.SetActive(false);
   ready=false;
  }
  void SetReady(bool on){
   ready=on;if(!sealButton)return;
   sealButton.Apply(new DesktopButton{label="Fechar pedido",variant="success",enabled=on,icon="",action="",args="[]",route="",after="",ok="",fail=""});
   sealButton.gameObject.SetActive(on);
   if(on){var rt=(RectTransform)sealButton.transform;rt.localScale=Vector3.zero;StartCoroutine(U.Scale(rt,Vector3.one,.42f,true));}
  }
  void CheckDone(){
   if(sealing||!sealButton)return;
   bool all=!pendingSubst&&requiredPlaced>=requiredTotal;
   if(all!=ready)SetReady(all);
  }
  // The product name pill that shows above the box under the pointer.
  RectTransform pill;
  void BuildPill(){
   pill=Node("Pill",board);pill.anchorMin=pill.anchorMax=Mid;pill.pivot=new Vector2(.5f,0);pill.sizeDelta=new Vector2(240,36);
   var bgImg=CheckoutDesktopCard.Image(pill,"Bg",K.C("4A3624"),14);U.Stretch(bgImg.rectTransform,Vector2.zero,Vector2.one);
   var lbl=U.Label(pill,"Text",K.Headline,18,"FFFFFF");U.Stretch(lbl.rectTransform,Vector2.zero,Vector2.one,new Vector2(12,0),new Vector2(-12,0));
   lbl.enableAutoSizing=true;lbl.fontSizeMin=10;lbl.fontSizeMax=18;
   pillBack=bgImg;pillText=lbl;pill.gameObject.SetActive(false);
  }

  // ------------------------------------------------------------------ opening: the slip, the card, the substitution
  IEnumerator Intro(){
   if(!clipboard)yield break;
   PlayClip(CheckoutRestockSound.Tape,.6f);
   clipboard.localScale=new Vector3(.2f,.2f,1);
   yield return U.Scale(clipboard,Vector3.one,.45f,true);
   running=true;lastInput=Time.unscaledTime;
   if(pendingSubst)OpenSubst();
  }
  // The twist card: a big banner that pops in, holds, then slides up and fades.
  IEnumerator TwistCard(){
   if(!board||string.IsNullOrEmpty(twistTitle))yield break;
   var card=U.Shape(board,"Twist","FFF7EC",30,Mid,new Vector2(Mathf.Min(W*.6f,780f),Mathf.Min(H*.4f,280f)),Vector2.zero);
   var group=card.gameObject.AddComponent<CanvasGroup>();
   var accent=U.Box(card.transform,"Accent","F2B03D",26,new Vector2(0,.8f),new Vector2(1,1));accent.rectTransform.offsetMin=new Vector2(0,-14);
   var eyebrow=U.Label(card.transform,"Eyebrow",K.Label,18,"8A7560");U.Stretch(eyebrow.rectTransform,new Vector2(0,.7f),new Vector2(1,.8f),new Vector2(20,0),new Vector2(-20,0));
   eyebrow.text="DESAFIO DO PEDIDO";eyebrow.characterSpacing=4;
   var head=U.Label(card.transform,"Title",K.Headline,46,"4A3624");U.Stretch(head.rectTransform,new Vector2(0,.42f),new Vector2(1,.7f),new Vector2(24,0),new Vector2(-24,0));
   head.text=twistTitle;head.enableAutoSizing=true;head.fontSizeMin=24;head.fontSizeMax=46;
   var body=U.Label(card.transform,"Body",K.Body,24,"4A3624");U.Stretch(body.rectTransform,new Vector2(0,.12f),new Vector2(1,.4f),new Vector2(30,0),new Vector2(-30,0));
   body.textWrappingMode=TextWrappingModes.Normal;body.text=twistBody;body.enableAutoSizing=true;body.fontSizeMin=16;body.fontSizeMax=24;
   var rt=card.rectTransform;rt.localScale=Vector3.zero;rt.localRotation=Quaternion.Euler(0,0,-3);
   PlayClip(CheckoutRestockSound.Next,.6f);
   yield return U.Scale(rt,Vector3.one,.4f,true);
   U.Sparkles(this,card.rectTransform,Vector2.zero,8,260);
   yield return new WaitForSecondsRealtime(2.4f);
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.45f){if(!card)yield break;group.alpha=1-t;rt.anchoredPosition=new Vector2(0,120*t);yield return null;}
   if(card)Destroy(card.gameObject);
  }

  // ------------------------------------------------------------------ toast, arc, squash
  void Toast(string text){
   if(!board)return;
   if(toast)Destroy(toast);
   var plate=U.Shape(board,"Toast","4A3624",20,new Vector2(.5f,1),new Vector2(Mathf.Min(W*.6f,700f),56),new Vector2(0,-44));
   toast=plate.gameObject;
   var label=U.Label(plate.transform,"Text",K.Headline,24,"FFFFFF");
   U.Stretch(label.rectTransform,Vector2.zero,Vector2.one,new Vector2(16,0),new Vector2(-16,0));
   label.text=text;label.enableAutoSizing=true;label.fontSizeMin=14;label.fontSizeMax=24;
   StartCoroutine(U.Pop(plate.rectTransform,1.06f,.22f));StartCoroutine(DropLater(toast,2.4f));
  }
  static IEnumerator DropLater(GameObject o,float delay){yield return new WaitForSecondsRealtime(delay);if(o)Destroy(o);}
  // A quadratic arc (lifted in the middle) between two anchored positions, in unscaled time.
  static IEnumerator Arc(RectTransform r,Vector2 to,float seconds,float lift=120f){
   if(!r)yield break;Vector2 from=r.anchoredPosition;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/Mathf.Max(.01f,seconds)){
    if(!r)yield break;float e=Mathf.SmoothStep(0,1,t);
    r.anchoredPosition=Vector2.Lerp(from,to,e)+new Vector2(0,Mathf.Sin(e*Mathf.PI)*lift);
    yield return null;
   }
   if(r)r.anchoredPosition=to;
  }
  static IEnumerator Squash(RectTransform r){
   float[] kx={1.06f,.95f,1.02f,1f};float[] ky={.94f,1.05f,.99f,1f};
   for(int i=0;i<kx.Length;i++){if(!r)yield break;yield return U.Scale(r,new Vector3(kx[i],ky[i],1),.06f);}
  }
  void Combo(){
   float now=Time.unscaledTime;streak=now-lastDrop<ComboWindow?streak+1:1;lastDrop=now;
   if(streak<3||!fx)return;
   var label=U.Label(fx,"Combo",K.Headline,30,"FFFFFF");U.At(label.rectTransform,Mid,new Vector2(320,50),new Vector2(0,H*.1f));
   label.text="Combo x"+streak;
   StartCoroutine(FloatAway(label));
  }
  IEnumerator FloatAway(TextMeshProUGUI t){
   var r=t.rectTransform;var from=r.anchoredPosition;r.localScale=Vector3.zero;
   yield return U.Scale(r,Vector3.one,.18f,true);
   for(float k=0;k<1;k+=Time.unscaledDeltaTime/.8f){if(!t)yield break;r.anchoredPosition=from+new Vector2(0,50*k);t.alpha=1-k*k;yield return null;}
   if(t)Destroy(t.gameObject);
  }
  void CheckOrder(){
   if(sealing||ended||bridge.State?.delivery?.orders==null)return;
   var cur=Find(orderId);
   if(cur!=null&&cur.status=="aceito")return;
   ended=true;
   Toast(cur==null?"Pedido não encontrado.":"Pedido cancelado ou expirado.");
   StartCoroutine(EndSoon());
  }
  IEnumerator EndSoon(){yield return new WaitForSecondsRealtime(1.6f);Close();}
  void UpdateTimer(){
   if(!timerFill)return;
   float f=Mathf.Clamp01(1f-elapsed/Mathf.Max(1f,parSec));
   timerFill.rectTransform.anchorMax=new Vector2(f,1);
   float red=Mathf.PingPong(Time.unscaledTime*3f,1f);
   var green=K.C("5DA637");var alarm=K.C("E15533");
   if(elapsed>parSec)timerFill.color=Color.Lerp(alarm,K.C("F2B03D"),red);
   else if(elapsed>parSec*.8f)timerFill.color=Color.Lerp(green,alarm,red*(elapsed-parSec*.8f)/(parSec*.2f+.01f));
   else timerFill.color=green;
   if(timerLabel)timerLabel.text=elapsed>parSec?string.Format("Passou da meta · {0}",Clock(elapsed)):string.Format("Meta {0} · {1}",Clock(parSec),Clock(elapsed));
  }
  // ------------------------------------------------------------------ frame update
  void Update(){
   if(!window||!window.activeSelf)return;
   if(Input.GetKeyDown(KeyCode.Escape))Dismiss();
   if(!board)return;
   float now=Time.unscaledTime;
   if(running&&!ended&&!sealing&&!modal)elapsed+=Time.unscaledDeltaTime;
   if(now-lastCheckT>.5f){lastCheckT=now;CheckOrder();UpdateTimer();}
   UpdateBoxes(now);
   UpdateHover(now);
  }
  float lastCheckT;

  // ------------------------------------------------------------------ taking units out of the boxes
  void Touch(){lastInput=Time.unscaledTime;hintBox=null;}
  void BoxHovered(PackBox b,bool on){
   if(on)hoveredBox=b;else if(hoveredBox==b)hoveredBox=null;
  }
  void BoxPressed(PackBox b){
   if(sealing||modal!=null||!running)return;
   Touch();
   if(b.units<=0){PlayClip(CheckoutRestockSound.Wrong,.5f);Toast("Essa caixa já está vazia.");}
  }
  // A drag that starts on a box takes one unit out of it: the unit is spawned under the pointer and the drag goes on
  // with the unit's own CheckoutDragToken (its drop and miss handlers decide where the unit ends up).
  Token BoxDragStart(PackBox b,PointerEventData e){
   if(!running||sealing||modal!=null||b==null||b.units<=0)return null;
   Touch();
   b.units--;RefreshBoxCount(b);
   var t=SpawnUnit(b);
   if(RectTransformUtility.ScreenPointToLocalPointInRectangle(fx,e.position,e.pressEventCamera,out var local))t.root.localPosition=local;
   else t.root.localPosition=U.LocalOf(fx,b.rect);
   t.drag.OnBeginDrag(e);
   return t;
  }
  void UnitDragged(Token t,PointerEventData e){if(t!=null&&t.drag)t.drag.OnDrag(e);}
  void UnitDragEnded(Token t,PointerEventData e){if(t!=null&&t.drag)t.drag.OnEndDrag(e);}

  Token SpawnUnit(PackBox b){
   int li=lines.FindIndex(l=>l.productId==b.productId);
   var t=new Token{productId=b.productId,name=b.name??"Produto",category=b.category??"",lineIndex=li,kind=li>=0?KindOrdered:KindWrong,size=tokenSize,source=b};
   t.cold=ColdCats.Contains(t.category);t.fragile=FragileCats.Contains(t.category);t.kg=WeightOf(t.category,t.productId);
   // The root is the drag target itself (transparent, raycast), so the whole unit moves with the pointer.
   var rootImage=new GameObject("Unit",typeof(RectTransform),typeof(Image)).GetComponent<Image>();
   rootImage.transform.SetParent(fx,false);rootImage.color=new Color(1,1,1,0);rootImage.raycastTarget=true;
   var rt=(RectTransform)rootImage.transform;U.At(rt,Mid,new Vector2(tokenSize,tokenSize),Vector2.zero);
   t.root=rt;
   U.Shadow(rt,new Vector2(tokenSize*.8f,tokenSize*.22f),new Vector2(0,-tokenSize*.42f));
   t.glow=U.GlowAt(rt,"Glow",new Color(1,.9f,.45f,0),Mid,tokenSize*1.35f);
   t.body=Node("Body",rt);U.Stretch(t.body,Vector2.zero,Vector2.one);
   t.icon=new GameObject("Icon",typeof(RectTransform),typeof(Image)).GetComponent<Image>();t.icon.transform.SetParent(t.body,false);
   U.Stretch(t.icon.rectTransform,Vector2.zero,Vector2.one);t.icon.raycastTarget=false;t.icon.preserveAspect=true;
   var spr=K.Icon("Products/product-"+b.productId.ToString("000",CultureInfo.InvariantCulture));
   if(spr)t.icon.sprite=spr;
   else{
    t.icon.sprite=Disc();t.icon.color=Stickers[Mathf.Abs(b.productId)%Stickers.Length];
    var lbl=U.Label(t.body,"Name",K.Headline,tokenSize*.28f,"FFFFFF");U.Stretch(lbl.rectTransform,Vector2.zero,Vector2.one);lbl.text=Initials(t.name);
   }
   t.drag=U.Drag(rootImage);
   t.drag.Setup(dropTargets,target=>Drop(t,target),()=>Miss(t),()=>Grab(t));
   tokens.Add(t);
   return t;
  }

  // Pulling a unit out of a bag (or starting the drag of a new one) lifts it above everything.
  void Grab(Token t){
   Touch();PlayClip(CheckoutRestockSound.Grab,.5f);
   if(t.bag!=null)RemoveFromBag(t);
   if(t.root&&fx)t.root.SetParent(fx,true);
  }
  // Dropped anywhere but a bag that takes it: the unit flies back into its own box (the count is restored on arrival).
  void Miss(Token t){
   Touch();ClearBagGlow();
   if(t.placed)return;
   // The drag's spring-back (toward its home) is stopped; the unit flies to its box instead.
   t.drag.StopAllCoroutines();
   StartCoroutine(FlyBack(t));
  }
  IEnumerator FlyBack(Token t){
   var src=t.source;
   if(t.root&&fx){t.root.SetParent(fx,true);t.root.localScale=Vector3.one;}
   if(src!=null&&src.rect&&t.root&&fx)yield return Arc(t.root,U.LocalOf(fx,src.rect),.3f,60f);
   PlayClip(CheckoutRestockSound.Back,.7f);
   if(src!=null){src.units++;RefreshBoxCount(src);}
   tokens.Remove(t);
   if(t.root)Destroy(t.root.gameObject);
   CheckDone();
  }

  // The drop: a bag that takes the unit (right kind of bag: cold goes in the thermal one). Anything else is refused.
  bool Drop(Token t,RectTransform target){
   Touch();ClearBagGlow();
   var bag=allBags.FirstOrDefault(b=>b.drop==target);
   if(bag==null||!bag.active||t.placed)return false;
   if(bag.cold!=t.cold){
    PlayClip(CheckoutRestockSound.Wrong,.7f);
    Toast(t.cold?"Gelado vai na bolsa térmica!":"Esse vai na sacola de papel.");
    return false;
   }
   Accept(t,bag);
   return true;
  }
  void Accept(Token t,Bag bag){
   t.drag.Locked=true;
   // The weight check: a bag over 8 kg rips. The unit that tore it bounces out.
   bool rip=bag.items.Count>0&&bag.kg+t.kg>bag.limit+.001f;
   t.placed=true;t.bag=bag;bag.items.Add(t);bag.kg+=t.kg;
   // Identical units are interchangeable: a unit of an ordered product counts as ordered while its line still needs
   // units, and only the ones beyond that are extras.
   ResolveKind(t);
   if(t.required)requiredPlaced++;
   t.root.SetParent(bag.inside,true);
   Vector2 spot=StackSpot(bag,bag.items.Count-1,t.size);
   StartCoroutine(Land(t,spot));
   StartCoroutine(Squash(bag.node));
   PlayClip(CheckoutRestockSound.Place(t.fragile),.8f);
   if(!bannerGone){bannerGone=true;StartCoroutine(FadeGroup(banner,0,.5f));}
   RefreshTops(bag);
   if(rip){Rip(t,bag);return;}
   if(t.kind==KindWrong)FeedbackWrong(t);
   else if(t.kind==KindExtra)Toast(string.Format("{0} já está completo: devolva a sobra para a caixa.",t.name));
   else Tick(t);
   Combo();
   if(t.kind==KindOrdered){
    // Fragile goods stay last in the bag; a heavy item on top of them crushes them.
    bool fragileRule=twistFragile&&!t.fragile&&bag.items.Take(bag.items.Count-1).Any(x=>x.fragile);
    bool crush=!fragileRule&&bag.items.Count>1&&bag.items[bag.items.Count-2].fragile&&t.kg>=1.2f&&!t.fragile;
    if(fragileRule||crush){PlayClip(CheckoutRestockSound.Wrong,.35f);Wobble(bag);Toast(fragileRule?"Frágil por último! Ovos ficam no topo.":"Cuidado! Pesado por cima.");}
   }
   CheckDone();
  }
  void ResolveKind(Token t){
   if(t.kind==KindWrong||t.lineIndex<0||t.lineIndex>=lines.Count)return;
   var line=lines[t.lineIndex];
   int inBag=tokens.Count(x=>x!=t&&x.placed&&x.kind==KindOrdered&&x.lineIndex==t.lineIndex);
   t.kind=inBag<line.need?KindOrdered:KindExtra;
  }
  void FeedbackWrong(Token t){
   PlayClip(CheckoutRestockSound.Wrong,.35f);
   if(t.body)StartCoroutine(U.Pop(t.body,1.1f,.2f));
   Toast("Não é do pedido: devolva para a caixa.");
  }
  void Tick(Token t){
   var line=lines[t.lineIndex];line.done=Mathf.Min(line.need,line.done+1);RefreshLine(line);
   if(line.text)StartCoroutine(U.Pop(line.text.transform,1.08f,.2f));
   if(line.done>=line.need&&line.need>0)CompleteLine(line);
   if(fx&&t.root)U.Sparkles(this,fx,U.LocalOf(fx,t.root),4,70);
  }
  // Weight over the limit: the unit bounces out of the bag, a spare bag slides in, and the unit goes back to its box.
  void Rip(Token t,Bag bag){
   PlayClip(CheckoutRestockSound.Wrong,.7f);
   if(bag.node)StartCoroutine(U.Shake(bag.node,.35f,10));
   StartCoroutine(RipRoutine(t,bag));
  }
  IEnumerator RipRoutine(Token t,Bag bag){
   yield return new WaitForSecondsRealtime(.35f);
   RemoveFromBag(t);
   Toast("Sacola rasgou! Abrimos outra.");
   var spare=NextSpare(bag.kind);
   if(spare!=null)ActivateSpare(spare);
   else Toast("Sem mais sacolas! Tire algo da sacola.");
   yield return FlyBack(t);
  }
  // Pulls a unit out of its bag (bookkeeping only; the caller moves it).
  void RemoveFromBag(Token t){
   var bag=t.bag;if(bag==null)return;
   bag.items.Remove(t);bag.kg=Mathf.Max(0,bag.kg-t.kg);t.bag=null;t.placed=false;
   if(t.required){
    requiredPlaced--;
    if(t.lineIndex>=0&&t.lineIndex<lines.Count){
     var line=lines[t.lineIndex];bool wasDone=line.done>=line.need&&line.need>0;
     line.done=Mathf.Max(0,line.done-1);
     // An extra unit of the same product still in a bag takes its place on the line.
     var spare=tokens.FirstOrDefault(x=>x!=t&&x.placed&&x.kind==KindExtra&&x.lineIndex==t.lineIndex);
     if(spare!=null){spare.kind=KindOrdered;requiredPlaced++;line.done=Mathf.Min(line.need,line.done+1);}
     RefreshLine(line);
     if(wasDone&&line.done<line.need)UncompleteLine(line);
    }
   }
   RefreshTops(bag);
   CheckDone();
  }
  // Only the top unit of a bag can be dragged out of it.
  void RefreshTops(Bag bag){
   for(int i=0;i<bag.items.Count;i++)bag.items[i].drag.Locked=i!=bag.items.Count-1;
  }
  // Where the n-th unit of a bag lands: column stacking from the floor up, in the bag's inside space.
  Vector2 StackSpot(Bag bag,int index,float size){
   var rect=bag.node.rect;float bw=rect.width,bh=rect.height;
   var f=bag.floor;float s=size*.62f;
   float x0=(f[0]-.5f)*bw,x1=(f[2]-.5f)*bw,y0=(f[1]-.5f)*bh,top=(bag.mouth[3]-.5f)*bh;
   // Units fill the middle of the bag (never against the side walls, which are drawn by the back layer), three
   // per layer, layer over layer: the top ones peek out of the mouth.
   float cx=(x0+x1)*.5f,half=Mathf.Max(0,(x1-x0)*.5f-s*.55f)*.6f;
   int layer=index/3,slot=index%3;
   float x=cx+(slot-1)*half+((layer%2)==1?half*.35f:0f);
   float y=Mathf.Min(y0+s*.45f+layer*s*.42f,top-s*.05f);
   return new Vector2(x,y);
  }
  IEnumerator Land(Token t,Vector2 spot){
   var r=t.root;if(!r)yield break;
   r.localRotation=Quaternion.Euler(0,0,UnityEngine.Random.Range(-8f,8f));
   yield return Arc(r,spot,.28f,110f);
   if(r&&t.placed)r.localScale=Vector3.one*.62f;
  }
  void Wobble(Bag b){StartCoroutine(WobbleRoutine(b));}
  static IEnumerator WobbleRoutine(Bag b){
   float[] angles={3f,-3f,2f,0f};
   foreach(var z in angles){if(!b.node)yield break;yield return U.Rotate(b.node,z,.07f);}
  }

  // ------------------------------------------------------------------ hover: the bag under a dragged unit glows,
  // the box under the pointer lifts and shows its product name; the idle hint bobs the box of the next missing product.
  void UpdateHover(float now){
   Token drag=tokens.FirstOrDefault(x=>x.drag!=null&&x.drag.Dragging);
   Bag hit=null;
   if(drag!=null&&drag.root){
    var sp=RectTransformUtility.WorldToScreenPoint(null,drag.root.position);
    foreach(var b in allBags)if(b.active&&RectTransformUtility.RectangleContainsScreenPoint(b.drop,sp,null)){hit=b;break;}
   }
   if(hit!=hoveredBagRef){ClearBagGlow();hoveredBagRef=hit;}
   if(hit!=null&&hit.glow){hit.glow.color=drag.cold==hit.cold?new Color(.55f,.9f,.4f,.45f):new Color(.92f,.3f,.25f,.45f);}
   if(hoveredBox!=null&&hoveredBox.rect&&board&&pill){
    pill.gameObject.SetActive(true);pill.SetAsLastSibling();
    pill.anchoredPosition=U.LocalOf(board,hoveredBox.rect)+new Vector2(0,hoveredBox.rect.sizeDelta.y*.85f);
    if(pillText)pillText.text=hoveredBox.name+(hoveredBox.units<=0?" (vazia)":"");
   }else if(pill)pill.gameObject.SetActive(false);
  }
  void ClearBagGlow(){if(hoveredBagRef!=null&&hoveredBagRef.glow)hoveredBagRef.glow.color=new Color(1,1,1,0);hoveredBagRef=null;}
  void UpdateBoxes(float now){
   if(running&&!sealing&&modal==null&&now-lastInput>IdleAfter&&(hintBox==null||hintBox.units<=0)){
    var line=lines.FirstOrDefault(l=>l.done<l.need);
    hintBox=line==null?null:roomBoxes.FirstOrDefault(b=>b.productId==line.productId&&b.units>0);
   }
   foreach(var b in roomBoxes){
    if(b.rect==null)continue;
    bool hinted=hintBox!=null&&b==hintBox;
    float lift=(b==hoveredBox&&b.units>0)?4f:0f;
    float bob=hinted?Mathf.Sin(now*5f)*6f:0f;
    b.rect.anchoredPosition=b.basePos+new Vector2(0,lift+bob);
    if(b.glow){float a=hinted?.45f+.25f*Mathf.Sin(now*5f):0f;if(Mathf.Abs(b.glow.color.a-a)>.01f)b.glow.color=new Color(1,.9f,.45f,a);}
   }
  }
 }
}
