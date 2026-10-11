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
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // Atacado · Pedidos: the supplier market app on the store computer. Browse the catalog by category, put boxes of
 // many products into one cart and buy everything at once. One order = one truck (placeSupplierCart).
 // Feel (Supermarket Simulator's market app): product cards that lift under the pointer, a cart that fills the
 // truck, soft plucks for every click and a truck that drives off after the purchase.
 public sealed class CheckoutSupplierShop:MonoBehaviour {
  public static CheckoutSupplierShop Instance {get;private set;}
  public bool IsOpen=>window!=null&&window.activeSelf;

  public const string TabAtacado="atacado",TabDelivery="delivery";
  public bool DeliveryShown=>IsOpen&&tab==TabDelivery;
  // The body node of a tab; the Delivery app builds its screen into the delivery one.
  public RectTransform TabBody(string name)=>name==TabDelivery?deliveryBody:body;

  const string AllKey="*",LowKey="!low";
  const string Blue="2E8CAE",Dark="2B2B2B",Muted="8A7560",Green="3DAA5C",Red="E15533",Cream="FFF6E6";
  const int CardW=206,CardH=326,CardGap=14,CartWidth=420,SideWidth=232,MaxLines=40;
  static readonly CultureInfo Br=CultureInfo.GetCultureInfo("pt-BR");

  CheckoutBridge bridge;AudioSource sound;
  RectTransform root,frameRect,screenRect,body,deliveryBody,gridView,gridContent,sideContent,cartRect,cartList,cartContent,cartBadge;
  string tab=TabAtacado;TextMeshProUGUI titleText,deliveryBadgeText;Image deliveryBadge;CheckoutDesktopButton tabAtacado,tabDelivery;
  GameObject window,emptyNode,toast;CanvasGroup frameGroup;Image dim,meterImg,truckMover;GridLayoutGroup grid;
  TextMeshProUGUI coinsText,trucksText,cartCount,meterText,totalText,discountText;
  CheckoutDesktopButton couponButton,helperButton,buyButton,clearButton,repeatButton;
  AudioClip clipTick,clipPage,clipAdd,clipPlus,clipMinus,clipRemove,clipError,clipChime;
  readonly List<CheckoutDesktopButton> catButtons=new List<CheckoutDesktopButton>();
  readonly Dictionary<int,ProductCard> cards=new Dictionary<int,ProductCard>();
  readonly List<CartLine> cart=new List<CartLine>();
  readonly List<CartRow> rows=new List<CartRow>();
  string selected=AllKey,catalogSig="";bool useCoupon,busy;int lastRevision=int.MinValue,fade;float refreshAt,meterShown,meterTarget;

  sealed class CartLine {public int productId,boxes;}
  sealed class ProductCard {public int productId;public RectTransform root,slide,lift;public CanvasGroup group;public Image edge,face,icon,lockIcon,ribbon,barFill;public TextMeshProUGUI title,sub,stock,price,unit,ribbonText;public CheckoutDesktopButton button;public float hover;public bool hovered;}
  sealed class CartRow {public int productId;public RectTransform rect,plus,minus;public Image icon;public TextMeshProUGUI title,units,cost,count;}

  public static void Show(int productId=0){if(Instance)Instance.Open(productId,TabAtacado);}
  // Opens the computer on the Delivery tab (the Dynamic Island pill and the HUD "@delivery" route).
  public static void ShowDelivery(){if(Instance)Instance.Open(0,TabDelivery);}

  public void Initialize(CheckoutBridge owner){
   Instance=this;bridge=owner;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.5f;
   // Soft plucks (fast attack, 60-120 ms decay). The purchase also uses the existing coin and whoosh recordings.
   clipTick=Notes(.12f,1320,0,.03f);clipPage=Notes(.3f,587,0,.09f);clipAdd=Notes(.32f,523,0,.09f,784,.07f,.12f);
   clipPlus=Notes(.28f,659,0,.08f,988,.04f,.1f);clipMinus=Notes(.28f,494,0,.08f,392,.04f,.1f);clipRemove=Notes(.26f,523,0,.1f,392,.05f,.12f);
   clipError=Notes(.35f,110,0,.18f,82,0,.18f);clipChime=Notes(.22f,784,0,.14f,988,.09f,.14f,1319,.18f,.3f);
   root=U.Canvas(transform,"CheckoutSupplierShop",85);
   BuildWindow();
   window.SetActive(false);
  }

  // ------------------------------------------------------------------ window and layout
  void BuildWindow(){
   // Everything lives under one node, so hiding the window also hides the dim that catches the clicks.
   var holder=N.Node("Shop",root);U.Stretch(holder,Vector2.zero,Vector2.one);window=holder.gameObject;
   dim=U.Box(holder,"Dim","000000",0,Vector2.zero,Vector2.one);dim.color=new Color(.12f,.08f,.05f,.62f);dim.raycastTarget=true;U.Stretch(dim.rectTransform,Vector2.zero,Vector2.one,new Vector2(-900,-900),new Vector2(900,900)); // past the safe area: the whole screen darkens
   // The monitor: a dark rounded bezel around the app's screen.
   var bezel=N.Image(holder,"Bezel",K.C("2B2420"),34);bezel.raycastTarget=true;
   frameRect=U.Stretch(bezel.rectTransform,new Vector2(.035f,.05f),new Vector2(.965f,.95f));
   frameGroup=bezel.gameObject.AddComponent<CanvasGroup>();
   var screen=N.Image(bezel.transform,"Screen",K.C(Cream),22);screen.raycastTarget=true;
   screenRect=U.Stretch(screen.rectTransform,Vector2.zero,Vector2.one,new Vector2(14,14),new Vector2(-14,-14));
   BuildTopBar(screenRect);
   body=N.Node("Body",screenRect);U.Stretch(body,Vector2.zero,Vector2.one,Vector2.zero,new Vector2(0,-84));
   BuildSidebar();BuildGrid();BuildCart();
   deliveryBody=N.Node("DeliveryBody",screenRect);U.Stretch(deliveryBody,Vector2.zero,Vector2.one,Vector2.zero,new Vector2(0,-84));deliveryBody.gameObject.SetActive(false);
   SelectTab(TabAtacado,false);
  }

  // Shows one tab's body (Atacado catalog or the Delivery app) and styles the tab buttons.
  void SelectTab(string next,bool sound){
   tab=next;bool delivery=next==TabDelivery;
   if(body)body.gameObject.SetActive(!delivery);
   if(deliveryBody)deliveryBody.gameObject.SetActive(delivery);
   if(tabAtacado)tabAtacado.Apply(Btn("Atacado",delivery?"secondary":"primary",true,"Icons/delivery-truck",!delivery));
   if(tabDelivery)tabDelivery.Apply(Btn("Delivery",delivery?"primary":"secondary",true,"Icons/smartphone",delivery));
   if(titleText)titleText.text=delivery?"Delivery · Pedidos online":"Atacado · Pedidos";
   if(sound)Sfx(clipPage,.5f);
  }
  // Red badge on the Delivery tab: offers waiting for an answer.
  void SyncBadge(){
   int waiting=0;var d=bridge?.State?.delivery;
   if(d?.orders!=null)foreach(var o in d.orders)if(o!=null&&o.status=="oferta")waiting++;
   if(deliveryBadge){deliveryBadge.gameObject.SetActive(waiting>0);deliveryBadgeText.text=waiting.ToString(CultureInfo.InvariantCulture);}
  }

  void BuildTopBar(RectTransform screen){
   var top=N.Image(screen,"TopBar",K.C(Blue),22);top.raycastTarget=true;
   U.Stretch(top.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(0,-84),Vector2.zero);
   U.Icon(top.transform,"Logo","Icons/delivery-truck",new Vector2(0,.5f),new Vector2(56,56),new Vector2(44,0));
   var title=U.Label(top.transform,"Title",K.Headline,30,"FFFFFF",TextAlignmentOptions.Left);
   U.Stretch(title.rectTransform,new Vector2(0,0),new Vector2(.3f,1),new Vector2(84,6),new Vector2(-10,-6));
   title.text="Atacado · Pedidos";title.enableAutoSizing=true;title.fontSizeMin=18;title.fontSizeMax=30;titleText=title;
   // Tabs between the title and the chips: Atacado (supplier orders) and Delivery (online orders to pack).
   var tabs=N.Node("Tabs",top.transform);U.Stretch(tabs,new Vector2(.3f,0),new Vector2(.58f,1),new Vector2(6,14),new Vector2(-6,-14));
   N.Row(tabs.gameObject,8).childAlignment=TextAnchor.MiddleCenter;
   tabAtacado=CheckoutDesktopButton.Create(tabs,52,17,14);tabAtacado.Clicked=_=>SelectTab(TabAtacado,true);
   tabDelivery=CheckoutDesktopButton.Create(tabs,52,17,14);tabDelivery.Clicked=_=>SelectTab(TabDelivery,true);
   // Red badge on the Delivery tab: how many offers wait for an answer.
   deliveryBadge=U.Shape(tabDelivery.transform,"Badge",Red,12,new Vector2(1,1),new Vector2(40,28),new Vector2(-4,6));
   deliveryBadgeText=U.Label(deliveryBadge.transform,"Text",K.Headline,16,"FFFFFF");U.Stretch(deliveryBadgeText.rectTransform,Vector2.zero,Vector2.one);
   deliveryBadge.gameObject.SetActive(false);
   var chips=N.Node("Chips",top.transform);U.Stretch(chips,new Vector2(.58f,0),Vector2.one,new Vector2(0,8),new Vector2(-84,-8));
   N.Row(chips.gameObject,10).childAlignment=TextAnchor.MiddleRight;
   Image back;
   coinsText=Chip(chips,"Coins","FFF7EC","Icons/coin",out back);
   trucksText=Chip(chips,"Trucks","FFF7EC","Icons/delivery-truck",out back);
   var close=U.Button(top.transform,"X","danger",Close,56,22);
   U.At((RectTransform)close.transform,new Vector2(1,.5f),new Vector2(56,56),new Vector2(-42,0));
  }

  void BuildSidebar(){
   var side=N.Image(body,"Sidebar",K.C("F4E2BA"),0);
   U.Stretch(side.rectTransform,Vector2.zero,new Vector2(0,1),Vector2.zero,new Vector2(SideWidth,0));
   var view=ScrollArea(side.transform,"Categories",out sideContent);
   U.Stretch(view,Vector2.zero,Vector2.one,new Vector2(10,10),new Vector2(-10,-10));
   N.Column(sideContent.gameObject,8,new RectOffset(2,2,4,4));Fit(sideContent);
  }

  void BuildGrid(){
   gridView=ScrollArea(body,"Grid",out gridContent);
   U.Stretch(gridView,Vector2.zero,Vector2.one,new Vector2(SideWidth+12,12),new Vector2(-CartWidth-12,-12));
   grid=gridContent.gameObject.AddComponent<GridLayoutGroup>();
   grid.cellSize=new Vector2(CardW,CardH);grid.spacing=new Vector2(CardGap,CardGap);grid.padding=new RectOffset(4,4,4,4);
   grid.childAlignment=TextAnchor.UpperCenter;grid.constraint=GridLayoutGroup.Constraint.FixedColumnCount;grid.constraintCount=3;
   Fit(gridContent);
  }

  void BuildCart(){
   var panel=N.Image(body,"Cart",K.C("FBEFD6"),0);
   cartRect=U.Stretch(panel.rectTransform,new Vector2(1,0),Vector2.one,new Vector2(-CartWidth,0),Vector2.zero);
   var col=N.Node("Column",cartRect);U.Stretch(col,Vector2.zero,Vector2.one,new Vector2(16,16),new Vector2(-16,-16));
   N.Column(col.gameObject,10);
   // Header: title and the boxes in the truck.
   var head=N.Node("Header",col);N.Row(head.gameObject,8);Pref(head.gameObject,-1,44);
   var title=U.Label(head,"Title",K.Headline,26,Dark,TextAlignmentOptions.Left);title.text="Carrinho";Pref(title.gameObject,-1,-1).flexibleWidth=1;
   cartCount=Chip(head,"Count","F2B03D",null,out var countBack);cartBadge=countBack.rectTransform;
   // The lines of the cart (scrolls), with an empty state.
   var listView=ScrollArea(col.transform,"CartList",out cartContent);
   cartList=listView;
   var listLayout=Pref(listView.gameObject,-1,-1);listLayout.flexibleHeight=1;listLayout.minHeight=120;
   N.Column(cartContent.gameObject,8,new RectOffset(0,0,4,4));Fit(cartContent);
   var empty=N.Node("Empty",listView);U.Stretch(empty,Vector2.zero,Vector2.one);emptyNode=empty.gameObject;
   U.Icon(empty,"Icon","Icons/basket",new Vector2(.5f,.5f),new Vector2(96,96),new Vector2(0,60));
   var et=U.Label(empty,"Text",K.Headline,22,Dark);U.At(et.rectTransform,new Vector2(.5f,.5f),new Vector2(340,30),Vector2.zero);et.text="Seu carrinho está vazio";
   var es=U.Label(empty,"Sub",K.Body,16,Muted);U.At(es.rectTransform,new Vector2(.5f,.5f),new Vector2(340,24),new Vector2(0,-34));es.text="Escolha as caixas no catálogo";
   // One click puts the previous order back in the cart (what was bought last time, as much as fits now).
   repeatButton=CheckoutDesktopButton.Create(empty,44,15,14);repeatButton.Clicked=_=>RepeatLast();
   U.At((RectTransform)repeatButton.transform,new Vector2(.5f,.5f),new Vector2(320,44),new Vector2(0,-86));
   // The truck's load: boxes out of the most the truck takes.
   var meter=N.Node("Meter",col);N.Column(meter.gameObject,4);Pref(meter.gameObject,-1,58);
   var mhead=N.Node("MeterHead",meter);N.Row(mhead.gameObject,6);Pref(mhead.gameObject,-1,22);
   var mlabel=U.Label(mhead,"Label",K.Body,15,Muted,TextAlignmentOptions.Left);mlabel.text="Caminhão";Pref(mlabel.gameObject,-1,-1).flexibleWidth=1;
   meterText=U.Label(mhead,"Value",K.Body,15,Dark,TextAlignmentOptions.Right);
   var track=N.Image(meter,"Track",K.C("EADBC4"),8);Pref(track.gameObject,-1,16);
   meterImg=N.Image(track.transform,"Fill",K.C(Green),8);U.Stretch(meterImg.rectTransform,Vector2.zero,new Vector2(0,1));
   // Total, with the freight coupon when there is one.
   var tot=N.Node("Total",col);N.Row(tot.gameObject,6);Pref(tot.gameObject,-1,40);
   var tl=U.Label(tot,"Label",K.Body,18,Muted,TextAlignmentOptions.Left);tl.text="Total";Pref(tl.gameObject,-1,-1).flexibleWidth=1;
   discountText=U.Label(tot,"Discount",K.Body,14,Green,TextAlignmentOptions.Right);
   LayImg(tot,"Coin","Icons/coin",28,28);
   totalText=U.Label(tot,"Value",K.Headline,28,Dark,TextAlignmentOptions.Right);
   couponButton=CheckoutDesktopButton.Create(col,40,15,14);couponButton.Clicked=_=>ToggleCoupon();
   helperButton=CheckoutDesktopButton.Create(col,46,16,14);helperButton.Clicked=_=>FillLow();
   buyButton=CheckoutDesktopButton.Create(col,64,22,18);buyButton.Clicked=_=>Buy();
   clearButton=CheckoutDesktopButton.Create(col,34,14,12);clearButton.Clicked=_=>ClearCart();
   // The truck that takes the order away; hidden until a purchase.
   truckMover=N.Image(cartRect,"TruckMover",Color.white,0);truckMover.sprite=K.Icon("Icons/delivery-truck");truckMover.preserveAspect=true;truckMover.raycastTarget=false;
   U.At(truckMover.rectTransform,new Vector2(.5f,.5f),new Vector2(150,150),Vector2.zero);truckMover.gameObject.SetActive(false);
  }

  // ------------------------------------------------------------------ helpers
  // A clipped scroll view (mouse wheel, touch drag) whose content the caller lays out.
  static RectTransform ScrollArea(Transform parent,string name,out RectTransform content){
   var view=N.Image(parent,name,new Color(1,1,1,0),0);view.raycastTarget=true;
   view.gameObject.AddComponent<RectMask2D>();
   content=N.Node("Content",view.transform);
   content.anchorMin=new Vector2(0,1);content.anchorMax=Vector2.one;content.pivot=new Vector2(.5f,1);content.sizeDelta=Vector2.zero;content.anchoredPosition=Vector2.zero;
   var scroll=view.gameObject.AddComponent<ScrollRect>();
   scroll.viewport=view.rectTransform;scroll.content=content;scroll.horizontal=false;scroll.vertical=true;
   scroll.movementType=ScrollRect.MovementType.Elastic;scroll.scrollSensitivity=36;
   return view.rectTransform;
  }
  static void Fit(RectTransform r){var f=r.gameObject.AddComponent<UnityEngine.UI.ContentSizeFitter>();f.verticalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;}
  static UnityEngine.UI.LayoutElement Pref(GameObject go,float w,float h){
   var le=go.GetComponent<UnityEngine.UI.LayoutElement>();if(!le)le=go.AddComponent<UnityEngine.UI.LayoutElement>();
   if(w>=0)le.preferredWidth=w;
   if(h>=0)le.preferredHeight=h;
   return le;
  }
  // Takes a node out of its layout group (ribbons, lock badges).
  static void Overlay(GameObject go){go.AddComponent<UnityEngine.UI.LayoutElement>().ignoreLayout=true;}
  static Image LayImg(Transform parent,string name,string path,float w,float h){
   var img=N.Image(parent,name,Color.white,0);img.sprite=K.Icon(path);img.preserveAspect=true;img.raycastTarget=false;Pref(img.gameObject,w,h);return img;
  }
  // A rounded chip with an optional icon and a short text, sized by its content.
  static TextMeshProUGUI Chip(Transform parent,string name,string color,string icon,out Image back){
   back=N.Image(parent,name,K.C(color),18);
   var row=N.Row(back.gameObject,6,new RectOffset(12,12,4,4));row.childAlignment=TextAnchor.MiddleCenter;
   if(!string.IsNullOrEmpty(icon))LayImg(back.transform,"Icon",icon,26,26);
   return U.Label(back.transform,"Text",K.Headline,20,Dark);
  }
  // A small rounded button with one symbol (stepper, remove); the tap runs onTap.
  static Image Mini(Transform parent,string name,string text,string color,float w,float h,Action onTap){
   var img=N.Image(parent,name,K.C(color),12);Pref(img.gameObject,w,h);
   var label=U.Label(img.transform,"Text",K.Headline,20,Dark);U.Stretch(label.rectTransform,Vector2.zero,Vector2.one);label.text=text;
   U.Tap(img,onTap);return img;
  }
  static string Money(long v)=>v.ToString("N0",Br);
  static float Ease(float t)=>1-Mathf.Pow(1-t,3);
  static DesktopButton Btn(string label,string variant,bool enabled,string icon,bool active=false)=>new DesktopButton{label=label,variant=variant,enabled=enabled,icon=icon,active=active,action="",args="[]",route="",after="",ok="",fail="",badge=""};
  static string Duration(double seconds){int s=(int)Math.Ceiling(seconds);int m=s/60,r=s%60;return m>0?m+" min "+r+" s":s+" s";}
  // Soft pluck notes given as triples (pitch Hz, start s, length s): sine with a faint octave, fast attack, exponential decay.
  static AudioClip Notes(float volume,params float[] notes){
   const int rate=22050;float end=0;
   for(int i=0;i+2<notes.Length;i+=3)end=Mathf.Max(end,notes[i+1]+notes[i+2]);
   int count=Mathf.Max(1,(int)((end+.03f)*rate));var data=new float[count];
   for(int i=0;i+2<notes.Length;i+=3){
    float hz=notes[i],start=notes[i+1],len=Mathf.Max(.02f,notes[i+2]);
    int from=(int)(start*rate),to=Mathf.Min(count,from+(int)((len+.03f)*rate));
    for(int n=from;n<to;n++){
     float t=(n-from)/(float)rate;
     float env=(1-Mathf.Exp(-t*500f))*Mathf.Exp(-t*3f/len);
     data[n]+=volume*env*(Mathf.Sin(2*Mathf.PI*hz*t)+.25f*Mathf.Sin(4*Mathf.PI*hz*t))/1.25f;
    }
   }
   var clip=AudioClip.Create("supplier_"+count,count,1,rate,false);clip.SetData(data,0);return clip;
  }
  void Sfx(AudioClip clip,float volume=.5f){if(!clip||!sound)return;sound.pitch=UnityEngine.Random.Range(.97f,1.03f);sound.PlayOneShot(clip,volume);}

  // ------------------------------------------------------------------ catalog (live from the snapshot)
  SupplierProduct[] Catalog=>bridge?.State?.supplierCatalog??Array.Empty<SupplierProduct>();
  SupplierInfo Info=>bridge?.State?.supplierInfo;
  SupplierProduct Find(int productId){foreach(var p in Catalog)if(p!=null&&p.productId==productId)return p;return null;}
  bool Matches(SupplierProduct p)=>selected==AllKey||(selected==LowKey?p.low:(p.category??"")==selected);

  // ------------------------------------------------------------------ product cards
  ProductCard CardFor(int productId){
   if(cards.TryGetValue(productId,out var known))return known;
   var c=BuildCard(productId);cards[productId]=c;return c;
  }
  ProductCard BuildCard(int productId){
   var c=new ProductCard{productId=productId};
   c.root=N.Node("Card",gridContent);c.group=c.root.gameObject.AddComponent<CanvasGroup>();
   var hover=c.root.gameObject.AddComponent<CheckoutSupplierHover>();
   hover.Changed=on=>{c.hovered=on;if(on)Sfx(clipTick,.1f);};
   c.slide=N.Node("Slide",c.root);U.Stretch(c.slide,Vector2.zero,Vector2.one);
   c.lift=N.Node("Lift",c.slide);U.Stretch(c.lift,Vector2.zero,Vector2.one);
   // Card face: a warm outline and the cream face (outside the column layout).
   c.edge=N.Image(c.lift,"Outline",K.C("E2C98F"),22);Overlay(c.edge.gameObject);U.Stretch(c.edge.rectTransform,Vector2.zero,Vector2.one);
   c.face=N.Image(c.lift,"Face",K.C("FFFDF8"),20);Overlay(c.face.gameObject);c.face.raycastTarget=true;
   U.Stretch(c.face.rectTransform,Vector2.zero,Vector2.one,new Vector2(2,2),new Vector2(-2,-2));
   N.Column(c.lift.gameObject,4,new RectOffset(14,14,14,12));
   // Art: a soft glow behind the product, the lock on locked products.
   var art=N.Node("Art",c.lift);Pref(art.gameObject,-1,96);
   U.GlowAt(art,"Glow",new Color(1,.93f,.7f,.9f),new Vector2(.5f,.5f),110);
   c.icon=U.Icon(art,"Product",$"Products/product-{productId:000}",new Vector2(.5f,.5f),new Vector2(88,88));
   c.lockIcon=U.Icon(art,"Lock","Icons/lock",new Vector2(1,0),new Vector2(38,38),new Vector2(-6,6));c.lockIcon.gameObject.SetActive(false);
   // Ribbon for the products running out, over the top corner.
   c.ribbon=U.Shape(c.lift,"Ribbon",Red,12,new Vector2(1,1),new Vector2(112,26),new Vector2(-62,-18));Overlay(c.ribbon.gameObject);
   c.ribbonText=U.Label(c.ribbon.transform,"Text",K.Headline,13,"FFFFFF");U.Stretch(c.ribbonText.rectTransform,Vector2.zero,Vector2.one,new Vector2(6,0),new Vector2(-6,0));
   c.ribbonText.text="ACABANDO";c.ribbon.gameObject.SetActive(false);
   c.title=U.Label(c.lift,"Name",K.Headline,19,Dark);Pref(c.title.gameObject,-1,24);
   c.sub=U.Label(c.lift,"Sub",K.Body,14,Muted);Pref(c.sub.gameObject,-1,20);c.sub.overflowMode=TextOverflowModes.Overflow;
   c.stock=U.Label(c.lift,"Stock",K.Body,14,Muted);Pref(c.stock.gameObject,-1,20);c.stock.overflowMode=TextOverflowModes.Overflow;
   var bar=N.Image(c.lift,"Bar",K.C("EADBC4"),5);Pref(bar.gameObject,-1,10);
   c.barFill=N.Image(bar.transform,"Fill",K.C(Green),5);U.Stretch(c.barFill.rectTransform,Vector2.zero,Vector2.one);
   // Price per box with the coin.
   var prow=N.Node("Price",c.lift);N.Row(prow.gameObject,6).childAlignment=TextAnchor.MiddleCenter;Pref(prow.gameObject,-1,36);
   LayImg(prow,"Coin","Icons/coin",28,28);
   c.price=U.Label(prow,"Value",K.Headline,26,Dark);
   var per=U.Label(prow,"Per",K.Body,13,Muted);per.text="por caixa";
   c.unit=U.Label(c.lift,"Unit",K.Body,13,Muted);Pref(c.unit.gameObject,-1,20);c.unit.enableAutoSizing=true;c.unit.fontSizeMin=10;c.unit.fontSizeMax=13; // shrinks to fit instead of "..."
   c.button=CheckoutDesktopButton.Create(c.lift,44,16,14);
   c.button.Clicked=_=>OnAdd(c);
   return c;
  }
  void ApplyCard(ProductCard c,SupplierProduct p){
   bool locked=p.locked,low=p.low&&!locked;
   c.edge.color=K.C(low?"F2B03D":"E2C98F");
   c.face.color=K.C(locked?"EFE7DA":"FFFDF8");
   c.title.text=p.name??"";
   int caseSize=Math.Max(1,p.caseSize),capacity=Math.Max(1,p.capacityBoxes);
   int stockBoxes=(p.stockUnits+caseSize-1)/caseSize;
   c.sub.text="Caixa com "+p.caseSize+" un.";
   c.stock.text="No depósito: "+stockBoxes+"/"+p.capacityBoxes+" cx";
   c.barFill.rectTransform.anchorMax=new Vector2(Mathf.Clamp01(stockBoxes/(float)capacity),1);
   c.barFill.color=K.C(low?Red:Green);
   c.price.text=Money(Mathf.RoundToInt(p.boxPrice));
   c.unit.text=p.unitCost.ToString("N2",Br)+" por un. · vende a "+p.salePrice.ToString("N2",Br);
   c.ribbon.gameObject.SetActive(low);
   c.lockIcon.gameObject.SetActive(locked);
   c.icon.color=locked?new Color(1,1,1,.45f):Color.white;
   int inCart=Boxes(p.productId);
   if(locked)c.button.Apply(Btn("Nível "+p.unlockLevel,"secondary",false,"Icons/lock"));
   else if(p.freeBoxes-inCart<=0)c.button.Apply(Btn("Depósito cheio","secondary",false,""));
   else c.button.Apply(Btn("+ Carrinho","coin",true,"Icons/cart"));
  }
  // Cards shown for the selected category, in catalog order, each one sliding in with a short stagger.
  void Relayout(bool animate){
   var list=Catalog.Where(Matches).ToList();
   foreach(var c in cards.Values)c.root.gameObject.SetActive(false);
   for(int i=0;i<list.Count;i++){
    var c=CardFor(list[i].productId);
    c.root.gameObject.SetActive(true);c.root.SetSiblingIndex(i);ApplyCard(c,list[i]);
    if(animate){c.group.alpha=0;c.slide.anchoredPosition=new Vector2(0,-26);StartCoroutine(Appear(c,Mathf.Min(i,12)*.03f));}
    else{c.group.alpha=1;c.slide.anchoredPosition=Vector2.zero;}
   }
  }
  IEnumerator Appear(ProductCard c,float delay){
   yield return new WaitForSecondsRealtime(delay);
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.3f){
    if(!c.root)yield break;float e=Ease(t);c.group.alpha=e;c.slide.anchoredPosition=new Vector2(0,-26*(1-e));yield return null;
   }
   if(c.root){c.group.alpha=1;c.slide.anchoredPosition=Vector2.zero;}
  }

  // ------------------------------------------------------------------ category sidebar
  void SyncSidebar(){
   var keys=new List<string>{AllKey,LowKey};var names=new List<string>{"Todos",""};var pids=new List<int>{0,0};
   int lowCount=0;
   foreach(var p in Catalog){
    if(p.low)lowCount++;
    var cat=p.category??"";
    if(!keys.Contains(cat)){keys.Add(cat);names.Add(p.categoryLabel??cat);pids.Add(p.productId);}
   }
   names[1]="Acabando ("+lowCount+")";
   while(catButtons.Count<keys.Count){
    var b=CheckoutDesktopButton.Create(sideContent,58,15,14);
    b.Clicked=x=>SelectCategory(x.Data.route);
    catButtons.Add(b);
   }
   for(int i=0;i<catButtons.Count;i++){
    bool on=i<keys.Count;catButtons[i].gameObject.SetActive(on);if(!on)continue;
    string icon=i==0?"Icons/basket":i==1?"Icons/warning":"Products/product-"+pids[i].ToString("000");
    catButtons[i].Apply(Btn(names[i],"secondary",true,icon,keys[i]==selected));
    catButtons[i].Data.route=keys[i];
   }
  }
  void SelectCategory(string key){
   if(busy||string.IsNullOrEmpty(key)||key==selected)return;
   selected=key;Sfx(clipPage,.5f);Relayout(true);SyncSidebar();
  }

  // ------------------------------------------------------------------ snapshot sync
  // Numbers follow the snapshot; the cards and the sidebar are only rebuilt when the catalog itself changes.
  void Sync(bool force){
   var s=bridge?.State;if(s==null)return;
   if(!force&&s.revision==lastRevision)return;
   lastRevision=s.revision;
   SyncBadge();
   cart.RemoveAll(l=>Find(l.productId)==null);
   if(Info==null||Info.freightCoupons<=0)useCoupon=false;
   coinsText.text=Money((long)s.coins);
   trucksText.text="Caminhões "+(Info?.active??0)+"/"+(Info?.slots??0);
   grid.constraintCount=Mathf.Max(1,Mathf.FloorToInt((gridView.rect.width-8+CardGap)/(CardW+CardGap)));
   SyncSidebar();
   string sig=string.Join(",",Catalog.Select(p=>p.productId.ToString()).ToArray());
   if(sig!=catalogSig){catalogSig=sig;Relayout(false);}
   else foreach(var p in Catalog){if(cards.TryGetValue(p.productId,out var c)&&c.root.gameObject.activeSelf)ApplyCard(c,p);}
   RefreshCart();
  }

  // ------------------------------------------------------------------ open and close
  void Open(int productId,string openTab){
   if(bridge==null||bridge.State==null)return;
   bool other=(CheckoutCounterGame.Instance&&CheckoutCounterGame.Instance.IsOpen)||(CheckoutIncidents.Instance&&CheckoutIncidents.Instance.IsOpen)||(CheckoutRestockGame.Instance&&CheckoutRestockGame.Instance.IsOpen)||(CheckoutStockroom.Instance&&CheckoutStockroom.Instance.IsOpen)||(CheckoutReceivingGame.Instance&&CheckoutReceivingGame.Instance.IsOpen)||(CheckoutPackingGame.Instance&&CheckoutPackingGame.Instance.IsOpen);
   if(other)return;
   bool wasOpen=IsOpen;
   if(!wasOpen){window.SetActive(true);window.transform.SetAsLastSibling();StartCoroutine(OpenAnim());}
   SelectTab(openTab,false);
   // A product from the HUD opens its category with one box in the cart.
   if(productId>0){
    var pick=Find(productId);
    if(pick!=null)selected=pick.category??AllKey;
   }
   Sync(true);
   if(productId>0)PreAdd(productId);
   Relayout(!wasOpen);
   RefreshCart();
  }
  void PreAdd(int productId){
   var p=Find(productId);
   if(p==null){Toast("Esse produto não está no catálogo agora.","C0401F");return;}
   if(p.locked){Toast("Libera no nível "+p.unlockLevel+".","C0401F");return;}
   int added=AddBoxes(productId,1,out var why);
   if(added==0)Toast(why,"C0401F");else Sfx(clipAdd,.35f);
  }
  void Close(){
   if(!IsOpen||busy)return;
   StartCoroutine(CloseAnim());
  }
  IEnumerator OpenAnim(){
   int my=++fade;
   frameGroup.alpha=0;frameRect.localScale=Vector3.one*.92f;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.25f){
    if(fade!=my||!window)yield break;
    float e=Ease(t);frameGroup.alpha=e;frameRect.localScale=Vector3.one*(.92f+.08f*e);dim.color=new Color(dim.color.r,dim.color.g,dim.color.b,.62f*e);
    yield return null;
   }
   if(fade!=my||!window)yield break;
   frameGroup.alpha=1;frameRect.localScale=Vector3.one;dim.color=new Color(dim.color.r,dim.color.g,dim.color.b,.62f);
  }
  IEnumerator CloseAnim(){
   int my=++fade;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.18f){
    if(fade!=my||!window)yield break;
    float e=1-t;frameGroup.alpha=e;frameRect.localScale=Vector3.one*(1-.08f*t);dim.color=new Color(dim.color.r,dim.color.g,dim.color.b,.62f*e);
    yield return null;
   }
   if(fade!=my||!window)yield break;
   window.SetActive(false);frameGroup.alpha=1;frameRect.localScale=Vector3.one;dim.color=new Color(dim.color.r,dim.color.g,dim.color.b,.62f);
  }

  // ------------------------------------------------------------------ cart: numbers and checks
  int Boxes(int productId){var l=cart.Find(x=>x.productId==productId);return l==null?0:l.boxes;}
  int TotalBoxes(){int t=0;foreach(var l in cart)t+=l.boxes;return t;}
  long Subtotal(){long sum=0;foreach(var l in cart){var p=Find(l.productId);if(p!=null)sum+=(long)Mathf.RoundToInt(p.boxPrice)*l.boxes;}return sum;}
  bool CouponOn=>useCoupon&&(Info?.freightCoupons??0)>0;
  // The freight coupon takes 10% off the whole order, rounded up.
  long Priced(long subtotal)=>CouponOn?(subtotal*9+9)/10:subtotal;
  // Why `add` more boxes of this product cannot go in the cart now ("" when they can).
  string Refusal(int productId,int add){
   if(busy)return "Aguarde o pedido terminar.";
   var p=Find(productId);if(p==null)return "Produto indisponível agora.";
   if(p.locked)return "Libera no nível "+p.unlockLevel+".";
   var info=Info;if(info==null||bridge.State==null)return "Conectando ao fornecedor...";
   if(Boxes(productId)==0&&cart.Count>=MaxLines)return "O carrinho já tem produtos demais.";
   if(Boxes(productId)+add>p.freeBoxes)return "Não cabe mais no depósito";
   if(TotalBoxes()+add>info.maxBoxes)return "O caminhão está cheio ("+info.maxBoxes+" caixas)";
   if(Priced(Subtotal()+(long)Mathf.RoundToInt(p.boxPrice)*add)>bridge.State.coins)return "Moedas insuficientes";
   return "";
  }
  // What stops the order right now ("" when the cart can be sent).
  string Problem(){
   if(cart.Count==0)return "Seu carrinho está vazio.";
   var info=Info;if(info==null||bridge.State==null)return "Conectando ao fornecedor...";
   if(info.active>=info.slots)return "Todos os caminhões estão na estrada";
   foreach(var l in cart){
    var p=Find(l.productId);
    if(p==null||p.locked)return "Um produto do carrinho não está disponível.";
    if(l.boxes>p.freeBoxes)return "Não cabe mais no depósito: "+p.name;
   }
   if(TotalBoxes()>info.maxBoxes)return "O caminhão está cheio ("+info.maxBoxes+" caixas)";
   if(Priced(Subtotal())>bridge.State.coins)return "Moedas insuficientes";
   return "";
  }
  // Adds up to n boxes, one by one while each passes the checks. why = the reason it stopped ("" if it did not).
  int AddBoxes(int productId,int n,out string why){
   why="";int added=0;
   for(int i=0;i<n;i++){
    why=Refusal(productId,1);if(why.Length>0)break;
    var line=cart.Find(x=>x.productId==productId);
    if(line==null){line=new CartLine{productId=productId};cart.Add(line);}
    line.boxes++;added++;
   }
   return added;
  }

  // ------------------------------------------------------------------ cart: rows and totals
  CartRow BuildRow(){
   var r=new CartRow();
   var rowImg=N.Image(cartContent,"Row",K.C("FFFDF8"),16);Pref(rowImg.gameObject,-1,80);
   N.Row(rowImg.gameObject,8,new RectOffset(10,10,8,8)).childAlignment=TextAnchor.MiddleLeft;
   r.rect=rowImg.rectTransform;
   r.icon=LayImg(rowImg.transform,"Icon","Products/product-001",48,48);
   var info=N.Node("Info",rowImg.transform);N.Column(info.gameObject,2);Pref(info.gameObject,-1,-1).flexibleWidth=1;
   r.title=U.Label(info,"Name",K.Headline,17,Dark,TextAlignmentOptions.Left);Pref(r.title.gameObject,-1,22);r.title.enableAutoSizing=true;r.title.fontSizeMin=13;r.title.fontSizeMax=17;
   var sub=N.Node("Cost",info);N.Row(sub.gameObject,4);Pref(sub.gameObject,-1,20);
   r.units=U.Label(sub,"Units",K.Body,14,Muted,TextAlignmentOptions.Left);Pref(r.units.gameObject,-1,-1).flexibleWidth=1;r.units.enableAutoSizing=true;r.units.fontSizeMin=11;r.units.fontSizeMax=14;
   LayImg(sub,"Coin","Icons/coin",16,16);
   r.cost=U.Label(sub,"Value",K.Body,14,Dark,TextAlignmentOptions.Left);
   var step=N.Node("Stepper",rowImg.transform);N.Row(step.gameObject,4).childAlignment=TextAnchor.MiddleCenter;Pref(step.gameObject,100,34);
   r.minus=Mini(step,"Minus","-","EADBC4",28,28,()=>Step(r,-1)).rectTransform;
   r.count=U.Label(step,"Count",K.Headline,18,Dark);Pref(r.count.gameObject,34,30);
   r.plus=Mini(step,"Plus","+","FFE3A8",28,28,()=>Step(r,1)).rectTransform;
   Mini(rowImg.transform,"Remove","X","F7D7CC",24,24,()=>RemoveLine(r));
   return r;
  }
  void ApplyRow(CartRow r,CartLine l){
   var p=Find(l.productId);
   r.productId=l.productId;
   r.icon.sprite=K.Icon($"Products/product-{l.productId:000}");
   r.title.text=p?.name??"";
   int units=l.boxes*Math.Max(1,p?.caseSize??1);
   r.units.text=l.boxes+" cx · "+units+" un.";
   r.cost.text=Money((long)Mathf.RoundToInt(p?.boxPrice??0)*l.boxes);
   r.count.text=l.boxes.ToString(CultureInfo.InvariantCulture);
  }
  void RefreshCart(){
   while(rows.Count<cart.Count)rows.Add(BuildRow());
   for(int i=0;i<rows.Count;i++){
    bool on=i<cart.Count;rows[i].rect.gameObject.SetActive(on);
    if(on)ApplyRow(rows[i],cart[i]);
   }
   var info=Info;int max=Math.Max(1,info?.maxBoxes??10),boxes=TotalBoxes();
   // The truck's load: orange when nearly full, red when full.
   meterTarget=Mathf.Clamp01(boxes/(float)max);
   meterText.text=boxes+"/"+max+" caixas";
   meterImg.color=K.C(boxes>=max?Red:meterTarget>=.8f?"F0A030":Green);
   cartCount.text=boxes+" cx";
   totalText.text=Money(Priced(Subtotal()));
   discountText.text=CouponOn?"-10% frete":"";
   bool coupons=info!=null&&info.freightCoupons>0;
   couponButton.gameObject.SetActive(coupons);
   if(coupons)couponButton.Apply(Btn(CouponOn?"Cupom de frete aplicado (-10%)":"Usar cupom de frete (-10%) · tem "+info.freightCoupons,"secondary",!busy,"Icons/receipt",CouponOn));
   emptyNode.SetActive(cart.Count==0);
   var last=LastOrder();
   repeatButton.gameObject.SetActive(cart.Count==0&&last.Count>0);
   if(last.Count>0)repeatButton.Apply(Btn(last.Count==1?"Repetir último pedido (1 produto)":"Repetir último pedido ("+last.Count+" produtos)","primary",!busy,"Icons/clipboard"));
   string problem=Problem();
   helperButton.Apply(Btn("Adicionar o que está acabando","secondary",!busy,"Icons/warning"));
   buyButton.Apply(Btn(busy?"Enviando pedido...":"Fazer pedido","success",!busy&&problem.Length==0,"Icons/delivery-truck"));
   clearButton.Apply(Btn("Limpar carrinho","secondary",!busy&&cart.Count>0,""));
  }
  void Step(CartRow r,int dir){
   if(busy)return;
   var line=cart.Find(x=>x.productId==r.productId);if(line==null)return;
   if(dir>0){
    var why=Refusal(line.productId,1);
    if(why.Length>0){Fail(r.plus,why);return;}
    line.boxes++;Sfx(clipPlus,.5f);StartCoroutine(U.Pop(r.plus,1.2f,.2f));
   }else{
    if(line.boxes<=1){RemoveLine(r);return;}
    line.boxes--;Sfx(clipMinus,.5f);StartCoroutine(U.Pop(r.minus,1.2f,.2f));
   }
   RefreshCart();
  }
  void RemoveLine(CartRow r){
   if(busy)return;
   cart.RemoveAll(x=>x.productId==r.productId);Sfx(clipRemove,.5f);RefreshCart();
  }
  void ClearCart(){if(busy||cart.Count==0)return;cart.Clear();Sfx(clipRemove,.4f);RefreshCart();}
  void ToggleCoupon(){if(busy||!(Info?.freightCoupons>0))return;useCoupon=!useCoupon;Sfx(clipPage,.5f);RefreshCart();}
  // The last order bought, kept between sessions as "id:boxes,id:boxes".
  const string LastKey="checkout.shop.lastOrder";
  List<CartLine> LastOrder(){
   var list=new List<CartLine>();
   string raw;try{raw=PlayerPrefs.GetString(LastKey,"");}catch{raw="";}
   foreach(var part in raw.Split(new[]{','},StringSplitOptions.RemoveEmptyEntries)){
    var bits=part.Split(':');
    if(bits.Length==2&&int.TryParse(bits[0],NumberStyles.Integer,CultureInfo.InvariantCulture,out var id)&&int.TryParse(bits[1],NumberStyles.Integer,CultureInfo.InvariantCulture,out var n)&&id>0&&n>0)list.Add(new CartLine{productId=id,boxes=n});
   }
   return list;
  }
  void SaveLast(){
   var sb=new StringBuilder();
   foreach(var l in cart){if(sb.Length>0)sb.Append(',');sb.Append(l.productId.ToString(CultureInfo.InvariantCulture)).Append(':').Append(l.boxes.ToString(CultureInfo.InvariantCulture));}
   try{PlayerPrefs.SetString(LastKey,sb.ToString());PlayerPrefs.Save();}catch{}
  }
  void RepeatLast(){
   if(busy)return;
   var last=LastOrder();if(last.Count==0)return;
   int total=0,wanted=0;string why="";
   foreach(var l in last){wanted+=l.boxes;total+=AddBoxes(l.productId,l.boxes,out var w);if(w.Length>0)why=w;}
   if(total==0){Fail(repeatButton.transform as RectTransform,why.Length>0?why:"Nada coube agora.");RefreshCart();return;}
   Sfx(clipAdd,.4f);
   if(total<wanted)Toast("Coube só "+total+" caixa(s): "+why,"F0A030");
   RefreshCart();
  }
  // Fills the cart with what is running out, emptiest product first; each one takes as many boxes as fit.
  void FillLow(){
   if(busy)return;
   var low=Catalog.Where(p=>p.low&&!p.locked).OrderBy(p=>p.stockUnits/(float)Math.Max(1,p.capacityBoxes)).ToList();
   if(low.Count==0){Sfx(clipError,.4f);Toast("Nada está acabando agora.");return;}
   int total=0;string why="";
   foreach(var p in low){total+=AddBoxes(p.productId,Math.Max(1,p.freeBoxes),out var w);if(w.Length>0)why=w;}
   if(total>0){Sfx(clipAdd,.4f);Toast("Coloquei "+total+" caixa(s) do que está acabando no carrinho");}
   else Fail(helperButton.transform as RectTransform,why.Length>0?why:"Nada coube agora.");
   RefreshCart();
  }
  void OnAdd(ProductCard c){
   if(busy)return;
   var p=Find(c.productId);if(p==null)return;
   if(p.locked){Fail(c.lift,"Libera no nível "+p.unlockLevel+".");return;}
   bool shift=Input.GetKey(KeyCode.LeftShift)||Input.GetKey(KeyCode.RightShift);
   int want=shift?5:1;
   int added=AddBoxes(c.productId,want,out var why);
   if(added==0){Fail(c.lift,why);return;}
   Sfx(clipAdd,.35f);
   if(added<want)Toast("Coube só "+added+" caixa(s): "+why,"F0A030");
   StartCoroutine(FlyItem(c.productId,U.LocalOf(root,c.icon.rectTransform),U.LocalOf(root,cartBadge)));
   RefreshCart();
  }
  // A copy of the product's picture flies in an arc from the card to the cart badge.
  IEnumerator FlyItem(int productId,Vector2 from,Vector2 to){
   var img=U.Icon(root,"Flyer",$"Products/product-{productId:000}",new Vector2(.5f,.5f),new Vector2(84,84),from);
   var r=img.rectTransform;var mid=(from+to)*.5f+new Vector2(0,170);
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.6f){
    if(!r)yield break;
    float e=Ease(t);
    r.anchoredPosition=Vector2.Lerp(Vector2.Lerp(from,mid,e),Vector2.Lerp(mid,to,e),e);
    r.localScale=Vector3.one*(1.05f-.6f*e);
    yield return null;
   }
   if(img)Destroy(img.gameObject);
   if(cartBadge)StartCoroutine(U.Pop(cartBadge,1.22f,.25f));
  }

  // ------------------------------------------------------------------ feedback
  void Fail(RectTransform from,string why){
   Sfx(clipError,.6f);
   if(from)StartCoroutine(U.Shake(from,.3f,8));
   Toast(why,"C0401F");
  }
  void Toast(string text,string color="4A3624"){
   if(toast)Destroy(toast);
   var plate=U.Shape(screenRect,"Toast",color,22,new Vector2(.5f,0),new Vector2(Mathf.Min(640,screenRect.rect.width-40),52),new Vector2(0,26));
   toast=plate.gameObject;
   var label=U.Label(plate.transform,"Text",K.Headline,22,"FFFFFF");
   U.Stretch(label.rectTransform,Vector2.zero,Vector2.one,new Vector2(18,0),new Vector2(-18,0));
   label.text=text;label.enableAutoSizing=true;label.fontSizeMin=13;label.fontSizeMax=22;
   StartCoroutine(U.Pop(plate.transform,1.06f,.22f));StartCoroutine(DropToast(toast,2.6f));
  }
  IEnumerator DropToast(GameObject o,float delay){
   yield return new WaitForSecondsRealtime(delay);
   if(o){if(toast==o)toast=null;Destroy(o);}
  }

  // ------------------------------------------------------------------ purchase
  void Buy(){
   if(busy)return;
   var why=Problem();
   if(why.Length>0){Fail(buyButton.transform as RectTransform,why);return;}
   StartCoroutine(PurchaseRoutine());
  }
  IEnumerator PurchaseRoutine(){
   busy=true;RefreshCart();
   var beforeIds=new HashSet<string>((bridge.State?.orders??new Order[0]).Select(o=>o.id));
   double slowest=0;
   foreach(var l in cart){var p=Find(l.productId);if(p!=null&&p.deliverySeconds>slowest)slowest=p.deliverySeconds;}
   // One cart, one order: the lines as the app takes them (the coupon only when it is on).
   var sb=new StringBuilder("[{\"lines\":[");
   for(int i=0;i<cart.Count;i++){
    if(i>0)sb.Append(',');
    sb.Append("{\"productId\":").Append(cart[i].productId.ToString(CultureInfo.InvariantCulture)).Append(",\"boxes\":").Append(cart[i].boxes.ToString(CultureInfo.InvariantCulture)).Append('}');
   }
   sb.Append("]");
   if(CouponOn)sb.Append(",\"useFreightCoupon\":true");
   sb.Append("}]");
   bridge.Command("placeSupplierCart",sb.ToString());
   // The order is taken when one more truck is on the road in the snapshot.
   bool placed=false;
   for(float t=0;t<5f&&!placed;t+=.1f){
    yield return new WaitForSecondsRealtime(.1f);
    placed=(bridge.State?.orders??new Order[0]).Any(o=>o!=null&&!beforeIds.Contains(o.id));
   }
   if(!placed){busy=false;RefreshCart();Toast("O fornecedor não aceitou o pedido. O carrinho foi mantido.","C0401F");yield break;}
   // The cart lines shrink, a truck gets loaded, then it drives off to the right with a whoosh.
   var listAt=U.LocalOf(cartRect,cartList);
   foreach(var r in rows)if(r.rect.gameObject.activeSelf)StartCoroutine(U.Scale(r.rect,Vector3.zero,.25f));
   yield return new WaitForSecondsRealtime(.3f);
   truckMover.gameObject.SetActive(true);truckMover.rectTransform.anchoredPosition=listAt;truckMover.rectTransform.localScale=Vector3.zero;
   yield return U.Scale(truckMover.rectTransform,Vector3.one,.25f,true);
   Sfx(U.Sfx("whoosh"),.35f);Sfx(U.Sfx("coin_0"),.4f);Sfx(clipChime,.5f);
   U.Sparkles(this,cartRect,listAt,8,120);
   float endX=cartRect.rect.width*.5f+200;
   yield return U.Move(truckMover.rectTransform,new Vector2(endX,listAt.y),.9f);
   truckMover.gameObject.SetActive(false);
   SaveLast();cart.Clear();useCoupon=false;busy=false;
   foreach(var r in rows)r.rect.localScale=Vector3.one;
   RefreshCart();
   Toast("Pedido feito! Chega em "+Duration(slowest),Green);
  }

  // ------------------------------------------------------------------ frame
  void Update(){
   if(!IsOpen)return;
   if(Input.GetKeyDown(KeyCode.Escape)){Close();return;}
   float dt=Time.unscaledDeltaTime;
   // The truck's load eases up; the card under the pointer lifts.
   meterShown=Mathf.MoveTowards(meterShown,meterTarget,dt*1.6f);
   meterImg.rectTransform.anchorMax=new Vector2(meterShown,1);
   foreach(var c in cards.Values){
    if(!c.root.gameObject.activeSelf)continue;
    c.hover=Mathf.MoveTowards(c.hover,c.hovered?1f:0f,dt*7f);
    c.lift.localScale=Vector3.one*(1+.03f*c.hover);
    c.lift.anchoredPosition=new Vector2(0,6*c.hover);
   }
   refreshAt-=dt;
   if(refreshAt<=0){refreshAt=.25f;Sync(false);}
  }
 }

 // Reports pointer enter and exit of a product card (the card lifts while the pointer is on it).
 public sealed class CheckoutSupplierHover:MonoBehaviour,IPointerEnterHandler,IPointerExitHandler {
  public Action<bool> Changed;
  public void OnPointerEnter(PointerEventData e){Changed?.Invoke(true);}
  public void OnPointerExit(PointerEventData e){Changed?.Invoke(false);}
 }
}
