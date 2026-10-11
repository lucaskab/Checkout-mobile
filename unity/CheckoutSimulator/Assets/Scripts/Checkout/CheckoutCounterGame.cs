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
 // The playable register (simulator mode, mobile and desktop). Open it by clicking the register, a
 // customer waiting with a cart bubble or the CAIXA button. Rendered art from scripts/blender/build_ui_sprites.py
 // (market colours: navy granite counter, gold trims, the store behind) and three clear steps:
 //  1. Passar: products ride the belt; drag each one over the scanner (beep) and it drops into the bag. The POS
 //     screen lists every item and adds the total by itself (the register does the maths, no calculator);
 //  2. Pagar: card: push it into the machine slot (it processes, approves or declines and pops out);
 //     cash: the register comes up with its drawer open; tap the customer's notes and they fly into it;
 //  3. Troco: the POS shows the change; tap a compartment of the drawer and one of its notes (or a coin) flies to
 //     the customer's dish, tap one on the dish to take it back (a panel keeps count).
 // The live customer (their 3D model at the till) shows in the portrait with emotes.
 // completeCheckout(id, total) goes to the app; src/services/checkout-counter.ts decides the money.
 public sealed class CheckoutCounterGame:MonoBehaviour {
  public static CheckoutCounterGame Instance {get;private set;}
  static readonly int[] Denominations={100,50,20,10,5,2,1};
  const string Navy="22345E",NavyDark="16233F",Gold="E8B04A",Cream="FFF7EC",Green="5DA637",Red="E15533";

  CheckoutBridge bridge;RectTransform root,stage,fabRect;GameObject window,fab;
  TextMeshProUGUI title,fabText;Image backdrop;
  AudioSource sound;
  CheckoutEntry entry;int itemsLeft;long charged,total,subtotal;bool busy,finished;float closeAt;int fabCount=-1;
  readonly List<GameObject> scene=new List<GameObject>();GameObject hint;
  // Fixtures
  RectTransform beltSurface,glass,bagMouth,posScreen,receipt,basketRect,portraitRect;
  Image bag,scanner,laser,laserGlow,patience;RawImage beltRaw;TextMeshProUGUI screenTotal,screenCaption,screenExtra,payChip;Portrait portrait;
  readonly Image[] steps=new Image[3];readonly TextMeshProUGUI[] stepLabels=new TextMeshProUGUI[3];

  public static void Show(CheckoutBridge owner,string checkoutId){if(Instance)Instance.Open(checkoutId);}
  public bool IsOpen=>window&&window.activeSelf;

  public void Initialize(CheckoutBridge owner){
   Instance=this;bridge=owner;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.55f;
   root=U.Canvas(transform,"CheckoutCounterGame",80);
   BuildFab();
   stage=U.GameWindow(root,"reg_backdrop",out window,out title,out backdrop,Close);
   window.SetActive(false);
  }
  void Play(string clip,float pitch=1,float volume=1){var c=U.Sfx(clip);if(!c)return;sound.pitch=pitch;sound.PlayOneShot(c,volume);}

  void BuildFab(){
   // Floating register button on the left edge (clear of the app toolbars), with a waiting count.
   var node=CheckoutDesktopCard.Node("CaixaButton",root);node.anchorMin=node.anchorMax=new Vector2(0,.5f);node.pivot=new Vector2(0,.5f);node.anchoredPosition=new Vector2(16,-30);node.sizeDelta=new Vector2(150,124);fabRect=node;
   var edge=node.gameObject.AddComponent<Image>();edge.sprite=K.Rounded(22);edge.type=Image.Type.Sliced;edge.color=K.C("427A24");
   var face=U.Box(node,"Face","5DA637",20,Vector2.zero,Vector2.one);face.rectTransform.offsetMin=new Vector2(0,7);
   U.Art(face.transform,"Icon","pos_display",new Vector2(.5f,.62f),62);
   var label=U.Label(face.transform,"Label",K.Headline,20,"FFFFFF");U.Stretch(label.rectTransform,Vector2.zero,new Vector2(1,.3f));label.text="CAIXA";
   var badge=U.Shape(node,"Badge","E15533",16,new Vector2(1,1),new Vector2(42,36),new Vector2(-6,-6));
   fabText=U.Label(badge.transform,"Count",K.Headline,20,"FFFFFF");U.Stretch(fabText.rectTransform,Vector2.zero,Vector2.one);
   U.Tap(edge,()=>Open(null));CheckoutFabRail.Add(node,2);
   fab=node.gameObject;fab.SetActive(false);
  }

  // ------------------------------------------------------------------ flow
  CheckoutEntry Find(string id){var list=bridge.State?.checkouts;if(list==null)return null;foreach(var c in list)if(c.id==id)return c;return null;}
  IEnumerable<CheckoutEntry> Ready(){var now=CheckoutBridge.Now;return (bridge.State?.checkouts??Array.Empty<CheckoutEntry>()).Where(c=>c.readyAt<=now&&CheckoutWalker.AtRegister(c.customerId)).OrderBy(c=>c.readyAt);} // only customers standing at the till
  // The same count as Ready().Count() without the sort or the enumerators (Update runs every frame).
  int CountReady(){var list=bridge.State?.checkouts;if(list==null)return 0;var now=CheckoutBridge.Now;int n=0;foreach(var c in list)if(c.readyAt<=now&&CheckoutWalker.AtRegister(c.customerId))n++;return n;}

  public void Open(string checkoutId){
   var next=string.IsNullOrEmpty(checkoutId)?null:Find(checkoutId);
   if(next!=null&&(next.readyAt>CheckoutBridge.Now||!CheckoutWalker.AtRegister(next.customerId)))next=null; // still on the way to the till
   if(next==null)next=Ready().FirstOrDefault();
   if(next==null){if(bridge)bridge.OpenPanel("team");return;} // Nobody waiting: the register opens the team page as before.
   entry=next;charged=0;subtotal=0;busy=false;finished=false;closeAt=0;
   total=(long)Math.Round(entry.total);
   title.text="Caixa · "+entry.customerName;
   window.SetActive(true);window.transform.SetAsLastSibling();Canvas.ForceUpdateCanvases();
   StopAllCoroutines();BuildScene();StartCoroutine(Intro());
  }
  public void Close(){StopAllCoroutines();Clear();portrait?.Release();portrait=null;window.SetActive(false);entry=null;preview=false;}
  // ------------------------------------------------------------------ QA (CheckoutAutoTest "register"): a made-up
  // customer that never leaves, played by the test with the same taps as the player.
  bool preview;readonly Dictionary<RectTransform,CheckoutLine> tokenItems=new Dictionary<RectTransform,CheckoutLine>();
  public void OpenPreview(CheckoutEntry fake){
   entry=fake;preview=true;charged=0;subtotal=0;busy=false;finished=false;closeAt=0;total=(long)Math.Round(fake.total);
   title.text="Caixa · "+fake.customerName;window.SetActive(true);window.transform.SetAsLastSibling();Canvas.ForceUpdateCanvases();
   StopAllCoroutines();BuildScene();StartCoroutine(Intro());
  }
  public IEnumerator QaScanAll(){foreach(var token in tokens.ToList()){while(busy)yield return null;if(token&&tokenItems.TryGetValue(token,out var item))StartCoroutine(Scan(token,item));yield return new WaitForSecondsRealtime(.15f);}while(busy)yield return null;}
  public void QaPayAll()=>PayAll();
  public void QaGive(int value)=>GiveChange(value);
  void Clear(){foreach(var o in scene)if(o)Destroy(o);scene.Clear();tokenItems.Clear();if(hint)Destroy(hint);machine=null;register=null;tokens.Clear();changePanel=null;bins.Clear();binShade.Clear();customerNotes.Clear();handNotes.Clear();paying=changing=false;counterCleared=false;}
  T Keep<T>(T c) where T:Component{scene.Add(c.gameObject);return c;}
  // Transparent grab area holding a shadow and the art, so the shadow can sit underneath.
  RectTransform Holder(string name,Vector2 size){var img=Keep(CheckoutDesktopCard.Image(stage,name,new Color(1,1,1,0),0));img.raycastTarget=true;U.At(img.rectTransform,Mid,size);return img.rectTransform;}
  // Stage-local position (for things anchored at the stage centre) of a stage fraction.
  Vector2 P(float x,float y)=>new Vector2((x-.5f)*stage.rect.width,(y-.5f)*stage.rect.height);
  Vector2 At(RectTransform target)=>U.LocalOf(stage,target);
  static Vector2 Mid=>new Vector2(.5f,.5f);
  void Hint(Func<Vector2> from,Func<Vector2> to,bool tap=false){if(hint)Destroy(hint);hint=U.Hint(this,stage,from,to,tap);}
  void StopHint(){if(hint)Destroy(hint);hint=null;}
  static string Money(double v)=>"R$ "+v.ToString("0");

  // A navy card with a soft shadow and a thin gold edge (customer, steps, change).
  Image Card(string name,Vector2 at,Vector2 size){
   var shadow=Keep(U.Shape(stage,name+" shadow","000000",26,Mid,size+new Vector2(10,10),at+new Vector2(0,-8)));shadow.color=new Color(0,0,0,.28f);
   var edge=Keep(U.Shape(stage,name,Gold,24,Mid,size,at));
   var face=U.Box(edge.transform,"Face",Navy,22,Vector2.zero,Vector2.one);face.rectTransform.offsetMin=new Vector2(3,3);face.rectTransform.offsetMax=new Vector2(-3,-3);
   return face;
  }

  // Phones: the stage is wide and short (about 1290 x 585 against 1430 x 800 on the desktop), so the pieces get
  // their own spots: customer top-left, dish and change on the left, the register or card machine in the middle,
  // the POS and the change counter on the right.
  static bool Phone=>CheckoutScreen.Handheld;
  void BuildScene(){
   Clear();
   // Customer card: live portrait with a patience ring, name, how they pay.
   var card=Card("Customer",P(.155f,.83f),new Vector2(430,168));
   var ring=U.Shape(card.transform,"PortraitRing",Cream,70,new Vector2(0,.5f),new Vector2(140,140),new Vector2(84,0));
   patience=U.Shape(ring.transform,"Patience",Green,0,Mid,new Vector2(140,140));patience.sprite=Ring();patience.type=Image.Type.Filled;patience.fillMethod=Image.FillMethod.Radial360;patience.fillOrigin=(int)Image.Origin360.Top;patience.fillClockwise=false;
   var hole=U.Shape(ring.transform,"Hole","B98E55",60,Mid,new Vector2(116,116));hole.gameObject.AddComponent<Mask>().showMaskGraphic=true;
   portraitRect=hole.rectTransform;
   var raw=new GameObject("Portrait",typeof(RectTransform)).AddComponent<RawImage>();raw.transform.SetParent(hole.transform,false);U.Stretch(raw.rectTransform,Vector2.zero,Vector2.one);raw.raycastTarget=false;
   var fallback=U.Icon(hole.transform,"Fallback","Icons/customers",Mid,new Vector2(96,96));fallback.transform.SetAsFirstSibling();
   portrait=new Portrait(raw,entry.customerId,fallback);
   var name=U.Label(card.transform,"Name",K.Headline,32,"FFFFFF",TextAlignmentOptions.Left);U.Stretch(name.rectTransform,new Vector2(0,.5f),new Vector2(1,1),new Vector2(168,0),new Vector2(-16,-12));name.text=entry.customerName;
   var chip=U.Shape(card.transform,"Pay",entry.method=="cartao"?"2E8CAE":"5DA637",16,new Vector2(0,0),new Vector2(190,46),new Vector2(168+95,40));
   U.Icon(chip.transform,"Icon",entry.method=="cartao"?"Game/card_blue":"Game/note_10",new Vector2(0,.5f),new Vector2(44,30),new Vector2(30,0));
   payChip=U.Label(chip.transform,"Label",K.Label,20,"FFFFFF",TextAlignmentOptions.Left);U.Stretch(payChip.rectTransform,Vector2.zero,Vector2.one,new Vector2(58,0),new Vector2(-8,0));payChip.text=entry.method=="cartao"?"Cartão":"Dinheiro";
   // No step tracker (Lucas, 11/10: it added nothing and ate the top of the stage); the POS screen says what is next.
   // POS monitor: the receipt fills up by itself as items are scanned.
   var pos=Keep(U.Art(stage,"POS","pos_display",new Vector2(Phone?.82f:.8f,Phone?.72f:.74f),330));posScreen=U.Over(pos,"pos_display","screen");
   var head=U.Label(posScreen,"Head",K.Label,15,"8FA7CF",TextAlignmentOptions.TopLeft);U.Stretch(head.rectTransform,Vector2.zero,Vector2.one,new Vector2(16,8),new Vector2(-16,-8));head.text="MERCADINHO · CAIXA 01";if(CheckoutScreen.Handheld)head.rectTransform.offsetMax=new Vector2(-64,-8); // clear of the close button
   receipt=CheckoutDesktopCard.Node("Receipt",posScreen);U.Stretch(receipt,new Vector2(0,.36f),new Vector2(1,.86f),new Vector2(16,0),new Vector2(-16,0));
   var column=CheckoutDesktopCard.Column(receipt.gameObject,2);column.childAlignment=TextAnchor.LowerLeft;column.childForceExpandHeight=false;
   var line=U.Box(posScreen,"Rule","E8B04A",0,new Vector2(0,.34f),new Vector2(1,.34f));line.rectTransform.offsetMin=new Vector2(16,-1);line.rectTransform.offsetMax=new Vector2(-16,1);
   screenCaption=U.Label(posScreen,"Caption",K.Label,18,"E8B04A",TextAlignmentOptions.BottomLeft);U.Stretch(screenCaption.rectTransform,new Vector2(0,0),new Vector2(.45f,.2f),new Vector2(16,8),Vector2.zero);screenCaption.text="SUBTOTAL";
   screenTotal=U.Label(posScreen,"Total",K.Number,46,"FFFFFF",TextAlignmentOptions.BottomRight);U.Stretch(screenTotal.rectTransform,new Vector2(.4f,0),new Vector2(1,.21f),Vector2.zero,new Vector2(-16,2));screenTotal.enableAutoSizing=true;screenTotal.fontSizeMin=26;screenTotal.fontSizeMax=46;screenTotal.text=Money(0);
   screenExtra=U.Label(posScreen,"Extra",K.Label,16,"B9C7E0",TextAlignmentOptions.TopLeft);U.Stretch(screenExtra.rectTransform,new Vector2(0,.2f),new Vector2(1,.33f),new Vector2(16,0),new Vector2(-16,0));screenExtra.textWrappingMode=TextWrappingModes.NoWrap;screenExtra.overflowMode=TextOverflowModes.Overflow;screenExtra.fontSize=16;screenExtra.enableAutoSizing=true;screenExtra.fontSizeMin=10;screenExtra.fontSizeMax=16; // one line, shrinks to fit (it wrapped onto the caption)screenExtra.text=entry.items.Length==1?"1 item":entry.items.Length+" itens";
   // Belt (the rubber surface keeps running), scanner and bag.
   var belt=Keep(U.Art(stage,"Belt","belt",new Vector2(.4f,.3f),160));beltSurface=U.Over(belt,"belt","surface");
   beltRaw=new GameObject("Rubber",typeof(RectTransform)).AddComponent<RawImage>();beltRaw.transform.SetParent(beltSurface,false);U.Stretch(beltRaw.rectTransform,Vector2.zero,Vector2.one);beltRaw.raycastTarget=false;
   var tile=Resources.Load<Texture2D>("CheckoutDesktop/Game/belt_tile");if(tile){tile.wrapMode=TextureWrapMode.Repeat;beltRaw.texture=tile;}
   scanner=Keep(U.Art(stage,"Scanner","scanner_bed",new Vector2(.72f,.3f),200));glass=U.Over(scanner,"scanner_bed","glass");
   laserGlow=U.GlowAt(glass,"LaserGlow",new Color(1,.25f,.2f,.55f),Mid,10);laserGlow.rectTransform.anchorMin=new Vector2(0,.5f);laserGlow.rectTransform.anchorMax=new Vector2(1,.5f);laserGlow.rectTransform.sizeDelta=new Vector2(40,70);
   laser=U.Shape(glass,"Laser","FF4A3A",2,Mid,new Vector2(10,5));laser.rectTransform.anchorMin=new Vector2(.03f,.5f);laser.rectTransform.anchorMax=new Vector2(.97f,.5f);laser.rectTransform.sizeDelta=new Vector2(0,5);
   var scanTag=U.Shape(scanner.transform,"Tag",NavyDark,12,new Vector2(.5f,0),new Vector2(130,34),new Vector2(0,-8));var st=U.Label(scanTag.transform,"L",K.Label,16,"FFFFFF");U.Stretch(st.rectTransform,Vector2.zero,Vector2.one);st.text="LEITOR";
   bag=Keep(U.Art(stage,"Bag","shopping_bag",new Vector2(.9f,.33f),230));bagMouth=U.Over(bag,"shopping_bag","mouth");
   basketRect=Keep(U.Icon(stage,"Basket","Icons/basket",new Vector2(.08f,.3f),new Vector2(170,170))).rectTransform;
  }

  // Highlights the current step in the tracker.
  void Step(int index){
   for(int i=0;i<3;i++){
    if(!stepLabels[i])continue;
    if(!steps[i])continue;
    bool on=i==index,done=i<index;
    steps[i].color=on?K.C(Gold):done?new Color(.36f,.65f,.22f,.95f):new Color(.09f,.14f,.25f,.78f);
    stepLabels[i].color=on?K.C(NavyDark):Color.white;
    if(on)StartCoroutine(U.Pop(steps[i].transform,1.08f,.25f));
   }
  }

  IEnumerator Intro(){
   // Products come out of the basket one by one and ride the belt to their spot.
   var items=entry.items??Array.Empty<CheckoutLine>();itemsLeft=items.Length;
   for(int i=0;i<items.Length;i++){SpawnItem(items[i],i,items.Length);Play("whoosh",1.2f,.5f);StartCoroutine(U.Pop(basketRect,1.08f,.2f));yield return new WaitForSecondsRealtime(.16f);}
   yield return new WaitForSecondsRealtime(.6f);
   // The empty basket goes back under the counter.
   StartCoroutine(U.Move(basketRect,basketRect.anchoredPosition-new Vector2(0,420),.4f));
   Hint(()=>tokens.Count>0&&tokens[0]?tokens[0].anchoredPosition:At(beltSurface),()=>At(glass));
  }
  readonly List<RectTransform> tokens=new List<RectTransform>();
  void SpawnItem(CheckoutLine item,int index,int count){
   var token=Holder("Item "+item.name,new Vector2(124,124));
   U.Shadow(token,new Vector2(100,26),new Vector2(0,8));U.Icon(token,"Icon",$"Products/product-{item.productId:000}",Mid,new Vector2(124,124));
   if(item.quantity>1){var q=U.Shape(token,"Qty",Navy,14,new Vector2(1,1),new Vector2(52,36),new Vector2(-8,-8));var qt=U.Label(q.transform,"Q",K.Headline,20,"FFFFFF");U.Stretch(qt.rectTransform,Vector2.zero,Vector2.one);qt.text="x"+item.quantity;}
   tokens.Add(token);tokenItems[token]=item;
   token.anchoredPosition=At(basketRect);token.localScale=Vector3.one*.3f;
   var spot=BeltSpot(index,count);
   StartCoroutine(U.Scale(token,Vector3.one,.3f,true));StartCoroutine(U.Move(token,spot,.6f,true));
   var drag=U.Drag(token.GetComponent<Image>());drag.SetHome(spot);
   drag.Setup(new[]{glass,scanner.rectTransform},_=>{if(busy)return false;StopHint();StartCoroutine(Scan(token,item));return true;},()=>{Play("bonk",1,.6f);StartCoroutine(U.Shake(scanner.rectTransform,.25f,6));},()=>{Play("tap",1.2f,.5f);StopHint();});
  }
  Vector2 BeltSpot(int index,int count){
   var c=At(beltSurface);float w=beltSurface.rect.width,h=beltSurface.rect.height;int perRow=Mathf.Min(5,Mathf.Max(1,count));int row=index/5,col=index%5;
   float step=(w-150)/Mathf.Max(1,perRow-1);return c+new Vector2(-w/2+75+col*step+(row%2)*30,(row%2==0?8:-18)+h*.05f);
  }

  IEnumerator Scan(RectTransform token,CheckoutLine item){
   busy=true;token.GetComponent<CheckoutDragToken>().Locked=true;tokens.Remove(token);
   // Slide across the glass: the laser flashes green with a beep, then the item hops into the bag.
   var g=At(glass);
   yield return U.Move(token,g+new Vector2(-70,10),.12f);
   laser.color=K.C("7DFF6A");laserGlow.color=new Color(.4f,1,.4f,.8f);Play("scan_beep");StartCoroutine(U.Pop(scanner.rectTransform,1.04f,.2f));
   yield return U.Move(token,g+new Vector2(60,10),.2f);
   laser.color=K.C("FF4A3A");laserGlow.color=new Color(1,.25f,.2f,.55f);
   double price=item.quantity*item.unitPrice;subtotal+=(long)Math.Round(price);
   AddLine($"{item.quantity}x {Short(item.name)}",Money(price));
   screenTotal.text=Money(subtotal);StartCoroutine(U.Pop(screenTotal.transform,1.1f,.2f));
   // Arc into the bag.
   var from=token.anchoredPosition;var to=At(bagMouth);
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.38f){var e=1-Mathf.Pow(1-t,2);token.anchoredPosition=Vector2.Lerp(from,to,e)+new Vector2(0,Mathf.Sin(t*Mathf.PI)*120);token.localScale=Vector3.one*Mathf.Lerp(1,.45f,t);yield return null;}
   Destroy(token.gameObject);Play("pop",.9f,.6f);StartCoroutine(U.Pop(bag.rectTransform,1.1f,.25f));
   itemsLeft--;busy=false;
   if(itemsLeft<=0)StartCoroutine(Totals());
  }
  static string Short(string name)=>name.Length>16?name.Substring(0,15)+".":name;

  // One receipt line on the POS screen (the newest at the bottom; old ones scroll off the top).
  void AddLine(string left,string right){
   var row=CheckoutDesktopCard.Text(receipt,"Line",K.Number,17,Color.white);row.textWrappingMode=TextWrappingModes.NoWrap;row.overflowMode=TextOverflowModes.Ellipsis;
   row.text=$"<color=#DCE6F5>{left}</color><pos=68%>{right}";row.alpha=0;StartCoroutine(FadeIn(row));
   while(receipt.childCount>6)DestroyImmediate(receipt.GetChild(0).gameObject);
  }
  static IEnumerator FadeIn(TextMeshProUGUI t){for(float a=0;a<1;a+=Time.unscaledDeltaTime/.2f){if(!t)yield break;t.alpha=a;yield return null;}if(t)t.alpha=1;}

  // Everything scanned: the register shows the total and payment starts (no typing: the POS adds it up).
  IEnumerator Totals(){
   charged=total;
   screenCaption.text="TOTAL";screenTotal.text=Money(total);screenTotal.color=K.C(Gold);StartCoroutine(U.Pop(posScreen,1.06f,.3f));
   screenExtra.text=entry.method=="cartao"?"Pagamento no cartão":"Pagamento em dinheiro";
   Play("cash_register",1,.7f);StartCoroutine(Emote("heart"));
   yield return new WaitForSecondsRealtime(.7f);
   Step(1);
   if(entry.method=="cartao")StartCoroutine(CardStep(0));else StartCoroutine(CashStep());
  }

  // ------------------------------------------------------------------ step 2a: card machine
  Image machine,led,machineFlash;RectTransform slotRect,machineScreen;TextMeshProUGUI machineText;Image machineIcon;int cardTries;
  static readonly string[] CardArt={"card_blue","card_purple","card_red"};
  IEnumerator CardStep(int attempt){
   cardTries=attempt;
   if(machine==null){
    ClearCounter();
    machine=Keep(U.Art(stage,"Machine","card_machine",Mid,Phone?Mathf.Min(470,stage.rect.height*.82f):380));var home=Phone?P(.5f,.47f):P(.55f,.42f);machine.rectTransform.anchoredPosition=home-new Vector2(0,800);StartCoroutine(U.Move(machine.rectTransform,home,.45f,true));Play("whoosh",.8f,.6f);
    machineScreen=U.Over(machine,"card_machine","screen");
    machineFlash=U.Box(machineScreen,"Flash","FFFFFF",6,Vector2.zero,Vector2.one);machineFlash.color=new Color(1,1,1,0);
    machineText=U.Label(machineScreen,"Text",K.Number,28,"1F3B34");U.Stretch(machineText.rectTransform,Vector2.zero,Vector2.one);machineText.text=Money(total);
    machineIcon=U.Icon(machineScreen,"Icon","Icons/success",Mid,new Vector2(64,64));machineIcon.gameObject.SetActive(false);
    var ledRect=U.Over(machine,"card_machine","led");led=U.GlowAt(ledRect,"Led",new Color(.3f,.3f,.3f,0),Mid,46);
    slotRect=U.Over(machine,"card_machine","slot");
    yield return new WaitForSecondsRealtime(.45f);
   }
   // The customer holds out a card (a different one after a decline).
   var card=Holder("Card",new Vector2(128*U.Aspect(CardArt[attempt%3]),128));U.Shadow(card,new Vector2(170,30),new Vector2(0,6));U.Art(card,"Face",CardArt[attempt%3],Mid,128);
   var hold=P(.25f,.36f);card.anchoredPosition=hold-new Vector2(500,0);card.localRotation=Quaternion.Euler(0,0,-8);StartCoroutine(U.Move(card,hold,.45f,true));Play("card_slide",1.2f,.6f);
   if(attempt>0)StartCoroutine(Emote("sweat"));
   yield return new WaitForSecondsRealtime(.45f);
   var drag=U.Drag(card.GetComponent<Image>());drag.SetHome(hold);
   drag.Setup(new[]{slotRect,machine.rectTransform},_=>{StopHint();StartCoroutine(Insert(card,drag));return true;},()=>Play("bonk",1,.6f),StopHint);
   Hint(()=>card?card.anchoredPosition:Vector2.zero,()=>At(slotRect));
  }
  IEnumerator Insert(RectTransform card,CheckoutDragToken drag){
   drag.Locked=true;busy=true;
   // Turn upright over the slot, then slide down into the machine behind a mask at the slot line.
   var slot=At(slotRect);var shadow=card.Find("Shadow");if(shadow)shadow.gameObject.SetActive(false);
   float length=card.rect.width;
   StartCoroutine(U.Rotate(card,90,.2f));yield return U.Move(card,slot+new Vector2(0,length*.5f+14),.22f);
   Play("card_slide",.9f);
   var clip=CheckoutDesktopCard.Node("Clip",stage);clip.anchorMin=clip.anchorMax=Mid;clip.pivot=new Vector2(.5f,0);clip.sizeDelta=new Vector2(320,700);clip.anchoredPosition=slot;clip.gameObject.AddComponent<RectMask2D>();scene.Add(clip.gameObject);
   card.SetParent(clip,true);
   var outside=card.anchoredPosition;var inside=outside-new Vector2(0,length*.62f);
   yield return U.Move(card,inside,.3f);Play("tap",.7f);StartCoroutine(U.Shake(machine.rectTransform,.12f,4));
   // Processing: blinking dots and an amber LED.
   for(int i=0;i<6;i++){machineText.text=new string('•',i%3+1);led.color=i%2==0?new Color(1,.75f,.2f,.9f):new Color(.3f,.3f,.3f,0);Play("tap",1.6f,.4f);yield return new WaitForSecondsRealtime(.24f);}
   // Some cards are declined. After two declines the customer pays cash instead.
   bool approved=cardTries>=1?UnityEngine.Random.value<.9f:UnityEngine.Random.value<.8f;
   machineText.text="";machineIcon.gameObject.SetActive(true);machineIcon.rectTransform.localScale=Vector3.zero;StartCoroutine(U.Scale(machineIcon.rectTransform,Vector3.one,.3f,true));
   if(approved){
    machineIcon.sprite=K.Icon("Icons/success");machineFlash.color=new Color(.55f,.95f,.5f,.9f);led.color=new Color(.35f,1,.35f,1);Play("card_ok");StartCoroutine(U.Pop(machine.rectTransform,1.06f,.3f));
    screenExtra.text="Cartão aprovado";
    yield return new WaitForSecondsRealtime(.35f);
    Play("card_slide",1.3f,.6f);yield return U.Move(card,outside+new Vector2(0,20),.22f);
    card.SetParent(stage,true);StartCoroutine(U.Rotate(card,-10,.3f));StartCoroutine(U.Move(card,P(.12f,.7f),.45f));StartCoroutine(U.Scale(card,Vector3.one*.4f,.45f));
    Step(2);
    yield return Finish();
   }
   else{
    machineIcon.sprite=K.Icon("Icons/warning");machineFlash.color=new Color(1,.4f,.3f,.9f);led.color=new Color(1,.25f,.2f,1);Play("card_no");StartCoroutine(U.Shake(machine.rectTransform,.5f,12));
    screenExtra.text="Cartão recusado";
    yield return new WaitForSecondsRealtime(.25f);
    yield return U.Move(card,outside+new Vector2(0,60),.18f);Play("card_slide",1.4f,.5f);
    card.SetParent(stage,true);StartCoroutine(Emote("sweat"));
    yield return new WaitForSecondsRealtime(.35f);StartCoroutine(U.Rotate(card,-30,.3f));yield return U.Move(card,P(-.1f,.3f),.4f);
    machineIcon.gameObject.SetActive(false);machineFlash.color=new Color(1,1,1,0);led.color=new Color(.3f,.3f,.3f,0);machineText.text=Money(total);busy=false;
    if(cardTries>=1){
     StartCoroutine(U.Move(machine.rectTransform,machine.rectTransform.anchoredPosition-new Vector2(0,800),.35f));yield return new WaitForSecondsRealtime(.35f);machine=null;
     payChip.text="Dinheiro";screenExtra.text="Vai pagar em dinheiro";
     StartCoroutine(CashStep());
    }
    else StartCoroutine(CardStep(cardTries+1));
   }
  }

  // ------------------------------------------------------------------ step 2b / 3: the cash register and the change
  // The register (Game/register_open, scripts/blender/build_ui_sprites.py) comes up with its drawer open: one
  // compartment per note (100 → 2, marks bin0..bin5) and a cup of R$ 1 coins (mark coins); its customer display
  // shows the money. No dragging: paying, tap each note on the customer's dish (or the dish, for all of them) and it
  // flies into its compartment; change, tap a compartment and one of its notes flies to the dish, tap a note on the
  // dish to take it back. Compartments worth more than what is still due are dimmed.
  static readonly int[] DrawerValues={100,50,20,10,5,2};
  Image register,dish;TextMeshProUGUI registerDisplay;
  readonly Dictionary<int,RectTransform> bins=new Dictionary<int,RectTransform>();
  readonly Dictionary<int,Image> binShade=new Dictionary<int,Image>();
  readonly List<RectTransform> customerNotes=new List<RectTransform>();
  readonly List<RectTransform> handNotes=new List<RectTransform>();
  long changeDue,changeGiven,given,received;bool paying,changing;
  RectTransform changePanel;TextMeshProUGUI changeTitle,changeCount,dishLabel;Image changeBar;
  Vector2 DishCenter=>dish?dish.rectTransform.anchoredPosition:Phone?P(.16f,.42f):P(.19f,.25f);
  // The belt and the scanner slide away under the counter so the register or the card machine has the middle.
  bool counterCleared;
  void ClearCounter(){
   if(counterCleared)return;counterCleared=true;
   foreach(var part in new[]{beltSurface?(RectTransform)beltSurface.parent:null,scanner?scanner.rectTransform:null})
    if(part)StartCoroutine(U.Move(part,part.anchoredPosition-new Vector2(0,700),.35f));
  }

  IEnumerator CashStep(){
   long price=total;given=(long)Math.Round(Math.Max(entry.cashGiven,price));
   changeDue=given-price;changeGiven=0;received=0;paying=true;changing=false;
   customerNotes.Clear();handNotes.Clear();bins.Clear();binShade.Clear();
   // The belt and the scanner make room; the register rises with its drawer open.
   ClearCounter();
   // Phones: the bag leaves too (the change counter takes its corner); it comes back to the customer at the end.
   if(Phone&&bag)StartCoroutine(U.Move(bag.rectTransform,bag.rectTransform.anchoredPosition-new Vector2(0,700),.35f));
   register=Keep(U.Art(stage,"Register","register_open",Mid,Phone?Mathf.Min(560,stage.rect.height*.9f):440));var home=Phone?P(.5f,.48f):P(.54f,.29f);
   register.rectTransform.anchoredPosition=home-new Vector2(0,760);Play("drawer_open");StartCoroutine(U.Move(register.rectTransform,home,.5f,true));
   var display=U.Over(register,"register_open","display");
   registerDisplay=U.Label(display,"Text",K.Number,26,"8CFFB0");U.Stretch(registerDisplay.rectTransform,Vector2.zero,Vector2.one,new Vector2(6,2),new Vector2(-6,-2));registerDisplay.text=Money(0);registerDisplay.enableAutoSizing=true;registerDisplay.fontSizeMin=12;registerDisplay.fontSizeMax=26; // "TROCO R$ 27" fits the little display
   for(int i=0;i<DrawerValues.Length;i++)bins[DrawerValues[i]]=U.Over(register,"register_open","bin"+i,"Bin "+DrawerValues[i]);
   bins[1]=U.Over(register,"register_open","coins","Bin 1");
   // The customer's dish with the money they pay with.
   dish=Keep(U.Art(stage,"Dish","change_dish3",Mid,Phone?230:220));dish.rectTransform.anchoredPosition=Phone?P(.16f,.42f):P(.19f,.25f);
   U.Tap(dish,PayAll);
   var badge=Keep(U.Shape(stage,"DishLabel",NavyDark,18,Mid,new Vector2(330,50),DishCenter+new Vector2(0,-138)));badge.color=new Color(.09f,.14f,.25f,.92f);
   dishLabel=U.Label(badge.transform,"L",K.Label,20,"FFFFFF");U.Stretch(dishLabel.rectTransform,Vector2.zero,Vector2.one,new Vector2(10,0),new Vector2(-10,0));dishLabel.text="Cliente pagou "+Money(given);
   screenCaption.text="RECEBER";screenTotal.text=Money(given);screenTotal.color=Color.white;screenExtra.text="Total "+Money(price)+" · "+(changeDue>0?"Troco "+Money(changeDue):"Sem troco");
   StartCoroutine(U.Pop(posScreen,1.06f,.3f));
   yield return new WaitForSecondsRealtime(.5f);
   var notes=Split(given);
   for(int i=0;i<notes.Count;i++){
    int value=notes[i];var note=MoneyArt(stage,value,DishCenter+new Vector2(-46+i*22,6+i*10),1f);note.localRotation=Quaternion.Euler(0,0,UnityEngine.Random.Range(-12,12));
    note.localScale=Vector3.zero;StartCoroutine(U.Scale(note,Vector3.one,.25f,true));Play(value<=1?"coin_"+i%3:"note_"+i%2,1,.7f);
    var n=note;U.Tap(note.GetComponent<Image>(),()=>PayNote(n,value));customerNotes.Add(note);
    yield return new WaitForSecondsRealtime(.09f);
   }
   dishLabel.text="Toque no dinheiro para guardar";
   Hint(()=>customerNotes.Count>0&&customerNotes[customerNotes.Count-1]?customerNotes[customerNotes.Count-1].anchoredPosition:DishCenter,()=>DishCenter,true);
  }
  Vector2 BinPoint(int value)=>bins.TryGetValue(value,out var bin)&&bin?At(bin):register?At(register.rectTransform):Vector2.zero;
  void PayAll(){if(!paying)return;StartCoroutine(PayAllRoutine());}
  IEnumerator PayAllRoutine(){foreach(var note in customerNotes.ToList()){if(!paying)yield break;if(note)PayNote(note,ValueOf(note));yield return new WaitForSecondsRealtime(.12f);}}
  static int ValueOf(RectTransform note){var name=note.name;int.TryParse(name.Substring(name.LastIndexOf(' ')+1),out var v);return Math.Max(1,v);}
  void PayNote(RectTransform note,int value){
   if(!paying||!note||!customerNotes.Contains(note))return;
   customerNotes.Remove(note);StopHint();
   var button=note.GetComponent<UnityEngine.UI.Button>();if(button)button.interactable=false;
   StartCoroutine(IntoDrawer(note,value,customerNotes.Count==0));
  }
  // Arcs from the dish into its compartment and vanishes into the stack; the register display counts it.
  IEnumerator IntoDrawer(RectTransform note,int value,bool last){
   yield return Arc(note,BinPoint(value),value<=1?0:90,value<=1?.5f:.42f,.36f,90);
   if(note)Destroy(note.gameObject);
   Play(value<=1?"coin_1":"note_0",.95f);PopBin(value);
   received+=value;if(registerDisplay){registerDisplay.text=Money(received);StartCoroutine(U.Pop(registerDisplay.transform,1.15f,.2f));}
   if(!last)yield break;
   paying=false;
   yield return new WaitForSecondsRealtime(.3f);
   if(changeDue<=0){dishLabel.text="Pagou certinho!";registerDisplay.text="OK";Step(2);yield return CloseDrawer();yield return Finish();}
   else{Step(2);BuildChange();StartCoroutine(Emote("question"));}
  }
  // A thrown curve with a turn and a change of size (money flying between the dish and the drawer).
  IEnumerator Arc(RectTransform rect,Vector2 to,float angle,float scale,float seconds,float lift){
   if(!rect)yield break;var from=rect.anchoredPosition;var r0=rect.localEulerAngles.z;var s0=rect.localScale.x;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/seconds){if(!rect)yield break;var e=1-Mathf.Pow(1-t,2);rect.anchoredPosition=Vector2.Lerp(from,to,e)+new Vector2(0,Mathf.Sin(t*Mathf.PI)*lift);rect.localRotation=Quaternion.Euler(0,0,Mathf.LerpAngle(r0,angle,e));rect.localScale=Vector3.one*Mathf.Lerp(s0,scale,e);yield return null;}
   if(rect){rect.anchoredPosition=to;rect.localRotation=Quaternion.Euler(0,0,angle);rect.localScale=Vector3.one*scale;}
  }
  void PopBin(int value){if(!bins.TryGetValue(value,out var bin)||!bin)return;var glow=U.GlowAt(bin,"Flash",new Color(1,.9f,.5f,.8f),Mid,Mathf.Max(bin.rect.width,bin.rect.height)*1.4f);StartCoroutine(FlashOut(glow));}
  static IEnumerator FlashOut(Image glow){for(float t=0;t<1;t+=Time.unscaledDeltaTime/.35f){if(!glow)yield break;var c=glow.color;c.a=.8f*(1-t);glow.color=c;glow.rectTransform.localScale=Vector3.one*(1+t*.3f);yield return null;}if(glow)Destroy(glow.gameObject);}

  // Change: every compartment is a button; the panel keeps count.
  void BuildChange(){
   changing=true;
   screenCaption.text="TROCO";screenTotal.text=Money(changeDue);screenTotal.color=K.C(Gold);StartCoroutine(U.Pop(posScreen,1.08f,.3f));
   dishLabel.text="Toque na gaveta para dar o troco";
   var face=Card("Change",Phone?P(.84f,.28f):P(.19f,.56f),new Vector2(330,150));changePanel=(RectTransform)face.transform.parent;
   changeTitle=U.Label(face.transform,"Title",K.Label,20,"B9C7E0",TextAlignmentOptions.Top);U.Stretch(changeTitle.rectTransform,new Vector2(0,.62f),Vector2.one,new Vector2(12,0),new Vector2(-12,-10));changeTitle.text="DÊ O TROCO";
   changeCount=U.Label(face.transform,"Count",K.Headline,38,"FFFFFF");U.Stretch(changeCount.rectTransform,new Vector2(0,.28f),new Vector2(1,.7f));
   var track=U.Box(face.transform,"Track","0B1322",10,new Vector2(0,0),new Vector2(1,0));track.rectTransform.offsetMin=new Vector2(18,18);track.rectTransform.offsetMax=new Vector2(-18,38);
   changeBar=U.Box(track.transform,"Fill",Gold,10,Vector2.zero,new Vector2(0,1));
   foreach(var pair in bins){
    int value=pair.Key;var bin=pair.Value;if(!bin)continue;
    var shade=U.Box(bin,"Shade","000000",10,Vector2.zero,Vector2.one);shade.color=new Color(.05f,.08f,.15f,0);shade.raycastTarget=false;binShade[value]=shade;
    U.Tap(U.HitArea(bin,"Tap"),()=>GiveChange(value));
   }
   UpdateChange();
   Hint(()=>BinPoint(NextChangeValue()),()=>BinPoint(NextChangeValue()),true);
  }
  long ChangeLeft=>changeDue-changeGiven;
  int NextChangeValue(){foreach(var v in Denominations)if(v<=ChangeLeft)return v;return 1;}
  void UpdateChange(){
   if(!changeCount)return;
   changeCount.text=Money(changeGiven)+" <size=70%><color=#B9C7E0>de "+Money(changeDue)+"</color></size>";
   float k=changeDue>0?Mathf.Clamp01((float)changeGiven/changeDue):1;
   changeBar.rectTransform.anchorMax=new Vector2(k,1);changeBar.color=k>=1?K.C(Green):K.C(Gold);
   foreach(var pair in binShade)if(pair.Value)pair.Value.color=new Color(.05f,.08f,.15f,pair.Key>ChangeLeft&&ChangeLeft>0?.62f:0);
   if(registerDisplay)registerDisplay.text=ChangeLeft>0?"TROCO "+Money(ChangeLeft):"OK";
  }
  void GiveChange(int value){
   if(!changing||finished)return;StopHint();
   if(value>ChangeLeft){
    // Too much: the drawer keeps it.
    Play("bonk",1.1f);StartCoroutine(Emote("sweat"));
    changeTitle.text="MUITO! FALTA "+Money(ChangeLeft);StartCoroutine(U.Shake(changePanel,.3f,10));
    if(bins.TryGetValue(value,out var b)&&b)StartCoroutine(U.Shake(b,.25f,6));
    return;
   }
   PopBin(value);
   var note=MoneyArt(stage,value,BinPoint(value),value<=1?.5f:.42f);note.localRotation=Quaternion.Euler(0,0,value<=1?0:90);
   var spot=DishCenter+new Vector2(UnityEngine.Random.Range(-70,70),UnityEngine.Random.Range(-10,40));
   StartCoroutine(Arc(note,spot,UnityEngine.Random.Range(-15,15),value<=1?.55f:.72f,.34f,110));
   changeGiven+=value;handNotes.Add(note);Play(value<=1?"coin_"+handNotes.Count%3:"note_"+handNotes.Count%2);
   var n=note;U.Tap(note.GetComponent<Image>(),()=>TakeBack(n,value));
   if(changeGiven==changeDue){UpdateChange();StartCoroutine(U.Pop(changePanel,1.08f,.3f));changeTitle.text="TROCO CERTO!";StartCoroutine(Emote("heart"));StartCoroutine(ChangeDone());}
   else{changeTitle.text="FALTA "+Money(ChangeLeft);StartCoroutine(U.Pop(changeCount.transform,1.12f,.2f));UpdateChange();}
  }
  // A note on the dish goes back into the drawer.
  void TakeBack(RectTransform note,int value){
   if(!changing||finished||!note||!handNotes.Contains(note))return;
   handNotes.Remove(note);changeGiven-=value;Play("tap",1.1f);
   var button=note.GetComponent<UnityEngine.UI.Button>();if(button)button.interactable=false;
   StartCoroutine(BackToDrawer(note,value));
   changeTitle.text="FALTA "+Money(ChangeLeft);UpdateChange();
  }
  IEnumerator BackToDrawer(RectTransform note,int value){yield return Arc(note,BinPoint(value),value<=1?0:90,value<=1?.5f:.42f,.3f,80);if(note)Destroy(note.gameObject);PopBin(value);}
  IEnumerator ChangeDone(){finished=true;changing=false;yield return new WaitForSecondsRealtime(.5f);yield return CloseDrawer();finished=false;yield return Finish();}
  IEnumerator CloseDrawer(){
   Play("drawer_open",1.25f,.8f);
   if(register)yield return U.Move(register.rectTransform,register.rectTransform.anchoredPosition-new Vector2(0,760),.32f);
   StartCoroutine(U.Shake(stage,.15f,4));
  }
  // Notes and coins that add up to the amount (largest first).
  static List<int> Split(long amount){var notes=new List<int>();foreach(var v in Denominations)while(amount>=v&&notes.Count<12){notes.Add(v);amount-=v;}return notes;}
  RectTransform MoneyArt(RectTransform parent,int value,Vector2 at,float scale){
   var art=value<=1?"coin3_1":"note3_"+value;var img=Keep(U.Art(parent,"Money "+value,art,Mid,value<=1?70:92,at));img.rectTransform.localScale=Vector3.one*scale;return img.rectTransform;
  }

  // ------------------------------------------------------------------ done
  IEnumerator Finish(){
   if(finished&&closeAt>0)yield break;finished=true;StopHint();
   if(!preview)bridge.Command("completeCheckout","[\""+entry.id+"\","+Math.Max(1,charged)+"]");
   Play("success");StartCoroutine(Emote("heart"));
   screenCaption.text="PAGO";screenTotal.text=Money(total);screenTotal.color=K.C(Green);screenExtra.text="Obrigado, volte sempre!";
   // The bag goes to the customer, coins fly to the POS and sparkles pop.
   StartCoroutine(U.Move(bag.rectTransform,At(portraitRect)+new Vector2(90,-140),.6f));StartCoroutine(U.Scale(bag.rectTransform,Vector3.one*.55f,.6f));
   U.Sparkles(this,stage,At(posScreen),10,180);
   yield return U.Coins(this,stage,P(.55f,.35f),At(posScreen),Mathf.Clamp((int)(total/5)+3,4,14));
   closeAt=Time.unscaledTime+1.2f;
  }
  IEnumerator Emote(string kind){if(!portraitRect)yield break;yield return U.Emote(this,stage,kind,At(portraitRect)+new Vector2(90,70),90);}

  void Update(){
   int ready=CountReady();
   fab.SetActive(ready>0&&!IsOpen&&!(CheckoutIncidents.Instance&&CheckoutIncidents.Instance.IsOpen));if(fab.activeSelf){if(ready!=fabCount){fabCount=ready;fabText.text=ready.ToString();}fabRect.localScale=Vector3.one*(1+Mathf.Sin(Time.unscaledTime*4)*.03f);}
   if(!IsOpen)return;
   // Belt keeps running; the laser breathes.
   if(beltRaw){var r=beltSurface.rect;float tiles=r.height>0?r.width/(r.height*4f):4;beltRaw.uvRect=new Rect(-Time.unscaledTime*.35f,0,tiles,1);}
   if(laser&&!busy){float k=Mathf.PingPong(Time.unscaledTime*2,1);laser.color=Color.Lerp(K.C("FF4A3A"),K.C("B8261A"),k);laserGlow.color=new Color(1,.25f,.2f,.35f+.25f*k);}
   portrait?.Tick();
   if(closeAt>0){if(Time.unscaledTime>closeAt)Close();return;}
   if(preview){if(Input.GetKeyDown(KeyCode.Escape))Close();return;}
   var live=Find(entry.id);
   if(live==null){ // Gave up waiting (or a cashier served them): they walk away annoyed.
    if(!finished){finished=true;StopHint();StartCoroutine(Emote("angry"));Play("card_no",.8f);closeAt=Time.unscaledTime+1.8f;StartCoroutine(U.Shake(portraitRect,.5f,12));}
    return;}
   double now=CheckoutBridge.Now,left=Math.Max(0,live.expiresAt-now),span=Math.Max(1,live.expiresAt-live.readyAt);float ratio=(float)(left/span);
   patience.fillAmount=Mathf.Clamp01(ratio);patience.color=Color.Lerp(K.C(Red),K.C(Green),Mathf.InverseLerp(.15f,.5f,ratio));
   if(ratio<.25f&&!finished&&Mathf.Repeat(Time.unscaledTime,4f)<Time.unscaledDeltaTime)StartCoroutine(Emote("sweat"));
   if(Input.GetKeyDown(KeyCode.Escape))Close();
  }

  // The customer's 3D walker, once it is actually in the register line or at the till (the store
  // rings the basket up before the walker gets there).
  static Transform FindWalker(string customerId){
   if(string.IsNullOrEmpty(customerId))return null;
   foreach(var w in FindObjectsByType<CheckoutWalker>(FindObjectsSortMode.None))
    if(w&&w.gameObject.activeInHierarchy&&w.CustomerId==customerId&&(w.VisitPhase==3||w.VisitPhase==30||w.VisitPhase==8||w.VisitPhase==4))return w.transform;
   return null;
  }
  static Sprite ring;
  static Sprite Ring(){
   if(ring)return ring;const int n=256;var t=new Texture2D(n,n,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp};var px=new Color32[n*n];
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(n/2f,n/2f));float a=Mathf.Clamp01(n/2f-d)*Mathf.Clamp01(d-(n/2f-20));px[y*n+x]=new Color32(255,255,255,(byte)(a*255));}
   t.SetPixels32(px);t.Apply();return ring=Sprite.Create(t,new Rect(0,0,n,n),new Vector2(.5f,.5f));
  }

  // Live head-and-shoulders view of the customer's 3D model at the till, rendered into the portrait.
  sealed class Portrait {
   readonly RawImage image;readonly Image fallback;readonly string customerId;Transform target;Camera cam;RenderTexture texture;float searchAt;Transform headBone;
   public Portrait(RawImage raw,string id,Image placeholder){image=raw;customerId=id;fallback=placeholder;image.enabled=false;Tick();}
   void Attach(Transform walker){
    target=walker;headBone=null;headAbove=-1;texture=new RenderTexture(384,384,24);
    var go=new GameObject("Customer portrait camera");cam=go.AddComponent<Camera>();cam.targetTexture=texture;cam.fieldOfView=30;cam.nearClipPlane=.05f;cam.farClipPlane=7;cam.depth=-20;cam.enabled=false;renderAt=0;
    cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=K.C("EAD9BE");
    image.texture=texture;image.enabled=true;if(fallback)fallback.enabled=false;
   }
   public void Tick(){
    if(!target){
     if(cam){UnityEngine.Object.Destroy(cam.gameObject);cam=null;image.enabled=false;if(fallback)fallback.enabled=true;}
     if(Time.unscaledTime<searchAt)return;searchAt=Time.unscaledTime+.5f;var w=FindWalker(customerId);if(w)Attach(w);else return;
    }
    // The rigs' Head joint sits at the NECK and the heads (hair, caps) are big: aiming at the joint showed the chest.
    // So the height from the joint to the top of the head is measured once on the baked skinned mesh (like
    // CheckoutRequestBubble.HeadTop) and the camera frames the middle of the head, with a little of the shoulders.
    if(!headBone)FindHead();
    Vector3 center;float headSize;
    if(headBone){headSize=headAbove>0?headAbove:.4f;center=headBone.position+Vector3.up*headSize*.35f;}
    else{float s=Mathf.Max(.5f,target.lossyScale.y);headSize=.35f*s;center=target.position+Vector3.up*1.7f*s;}
    var face=-target.forward;face.y=0;if(face.sqrMagnitude<.01f)face=Vector3.back;face.Normalize();
    // FOV 30: the visible height is ~0.54 x distance; about 2.2 head heights fit (the head and the shoulders).
    float d=headSize*2.2f/.536f;
    cam.transform.position=center+face*d+Vector3.up*headSize*.08f;cam.transform.LookAt(center);
    // Rendered by hand ~15 times a second and only as deep as the customer: it drew the whole city every frame.
    if(Time.unscaledTime>=renderAt){renderAt=Time.unscaledTime+1f/15f;cam.Render();}
   }
   float renderAt;
   float headAbove=-1;
   void FindHead(){
    var animator=target.GetComponentInChildren<Animator>();if(animator&&animator.isHuman)headBone=animator.GetBoneTransform(HumanBodyBones.Head);
    if(!headBone)foreach(var t in target.GetComponentsInChildren<Transform>(true))if(t.name=="Head"){headBone=t;break;}
    if(!headBone)headBone=target.GetComponentsInChildren<Transform>().FirstOrDefault(t=>t.name.ToLowerInvariant()=="head"||t.name.ToLowerInvariant().EndsWith(":head"));
    if(!headBone)return;
    SkinnedMeshRenderer body=null;
    foreach(var r in target.GetComponentsInChildren<SkinnedMeshRenderer>(true))if(r.enabled&&!r.name.EndsWith("_Prop")&&r.sharedMesh&&(!body||r.sharedMesh.vertexCount>body.sharedMesh.vertexCount))body=r;
    if(!body){headAbove=.4f;return;}
    var baked=new Mesh();body.BakeMesh(baked,true);float top=float.MinValue;
    foreach(var v in baked.vertices)top=Mathf.Max(top,body.transform.TransformPoint(v).y);
    UnityEngine.Object.Destroy(baked);
    headAbove=top>float.MinValue?Mathf.Clamp(top-headBone.position.y,.2f,.9f):.4f;
   }
   public void Release(){if(cam)UnityEngine.Object.Destroy(cam.gameObject);if(texture){texture.Release();UnityEngine.Object.Destroy(texture);}}
  }
 }
}
