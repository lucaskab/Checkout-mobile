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
 // customer waiting with a cart bubble or the CAIXA button. Everything is rendered art from
 // scripts/blender/build_ui_sprites.py over a textured counter, and every step reacts in the scene:
 //  1. products slide out of the basket onto the running belt; drag each one over the scanner glass
 //     (laser flash, beep) and it drops into the bag while the printer prints its line;
 //  2. key the total on the keypad (the POS screen shows the subtotal); the customer reacts;
 //  3. card: push it into the machine slot (it slides in, processes, approves or declines and pops out);
 //     cash: the drawer rolls open, drop the customer's notes in it and hand back the exact change.
 // The live customer (their 3D model at the till) shows in the portrait with emotes.
 // The keyed amount goes to the app as completeCheckout(id, charged); src/services/checkout-counter.ts
 // decides the money. Nothing here changes coins by itself.
 public sealed class CheckoutCounterGame:MonoBehaviour {
  public static CheckoutCounterGame Instance {get;private set;}
  static readonly int[] Denominations={100,50,20,10,5,2,1};
  static readonly int[] BinValues={50,20,10,5,2};

  CheckoutBridge bridge;RectTransform root,stage,fabRect;GameObject window,fab;
  TextMeshProUGUI title,fabText;Image backdrop;
  AudioSource sound;AudioClip beep,ding,buzz,printSound,slide,cash,thud,click;
  CheckoutEntry entry;int itemsLeft;long charged,total,subtotal;string typed="";bool busy,finished;float closeAt;
  readonly List<GameObject> scene=new List<GameObject>();GameObject hint;
  // Fixtures
  RectTransform beltSurface,glass,bagMouth,posScreen,printerSlot,paper,paperLines,basketRect,portraitRect;
  Image bag,scanner,laser,laserGlow,patience;RawImage beltRaw;TextMeshProUGUI lcd,lcdCaption;Portrait portrait;

  public static void Show(CheckoutBridge owner,string checkoutId){if(Instance)Instance.Open(checkoutId);}
  public bool IsOpen=>window&&window.activeSelf;

  public void Initialize(CheckoutBridge owner){
   Instance=this;bridge=owner;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.4f;
   beep=U.Tone(1500,.08f);ding=U.Tone(990,.22f,1320);buzz=U.Tone(150,.3f,110,.6f);printSound=U.Noise(.18f,.12f);slide=U.Noise(.12f,.08f);cash=U.Tone(1800,.12f,2400,.35f);thud=U.Tone(90,.12f,70,.7f);click=U.Tone(2400,.03f);
   root=U.Canvas(transform,"CheckoutCounterGame",80);
   BuildFab();
   stage=U.GameWindow(root,"reg_backdrop",out window,out title,out backdrop,Close);
   window.SetActive(false);
  }
  void Play(AudioClip clip,float pitch=1){if(!clip)return;sound.pitch=pitch;sound.PlayOneShot(clip);}

  void BuildFab(){
   // Floating register button on the left edge (clear of the app toolbars), with a waiting count.
   var node=CheckoutDesktopCard.Node("CaixaButton",root);node.anchorMin=node.anchorMax=new Vector2(0,.5f);node.pivot=new Vector2(0,.5f);node.anchoredPosition=new Vector2(16,-30);node.sizeDelta=new Vector2(150,124);fabRect=node;
   var edge=node.gameObject.AddComponent<Image>();edge.sprite=K.Rounded(22);edge.type=Image.Type.Sliced;edge.color=K.C("427A24");
   var face=U.Box(node,"Face","5DA637",20,Vector2.zero,Vector2.one);face.rectTransform.offsetMin=new Vector2(0,7);
   U.Art(face.transform,"Icon","pos_terminal",new Vector2(.5f,.62f),70);
   var label=U.Label(face.transform,"Label",K.Headline,20,"FFFFFF");U.Stretch(label.rectTransform,Vector2.zero,new Vector2(1,.3f));label.text="CAIXA";
   var badge=U.Shape(node,"Badge","E15533",16,new Vector2(1,1),new Vector2(42,36),new Vector2(-6,-6));
   fabText=U.Label(badge.transform,"Count",K.Headline,20,"FFFFFF");U.Stretch(fabText.rectTransform,Vector2.zero,Vector2.one);
   U.Tap(edge,()=>Open(null));
   fab=node.gameObject;fab.SetActive(false);
  }

  // ------------------------------------------------------------------ flow
  CheckoutEntry Find(string id){var list=bridge.State?.checkouts;if(list==null)return null;foreach(var c in list)if(c.id==id)return c;return null;}
  IEnumerable<CheckoutEntry> Ready(){var now=CheckoutBridge.Now;return (bridge.State?.checkouts??Array.Empty<CheckoutEntry>()).Where(c=>c.readyAt<=now).OrderBy(c=>c.readyAt);}

  public void Open(string checkoutId){
   var next=string.IsNullOrEmpty(checkoutId)?null:Find(checkoutId);
   if(next==null)next=Ready().FirstOrDefault();
   if(next==null){if(bridge)bridge.OpenPanel("team");return;} // Nobody waiting: the register opens the team page as before.
   entry=next;typed="";charged=0;subtotal=0;busy=false;finished=false;closeAt=0;
   total=(long)Math.Round(entry.total);
   title.text="Caixa · "+entry.customerName;
   window.SetActive(true);window.transform.SetAsLastSibling();Canvas.ForceUpdateCanvases();
   StopAllCoroutines();BuildScene();StartCoroutine(Intro());
  }
  public void Close(){StopAllCoroutines();Clear();portrait?.Release();portrait=null;window.SetActive(false);entry=null;}
  void Clear(){foreach(var o in scene)if(o)Destroy(o);scene.Clear();if(hint)Destroy(hint);machine=null;keypad=null;tray=null;tokens.Clear();}
  T Keep<T>(T c) where T:Component{scene.Add(c.gameObject);return c;}
  // Transparent grab area holding a shadow and the art, so the shadow can sit underneath.
  RectTransform Holder(string name,Vector2 size){var img=Keep(CheckoutDesktopCard.Image(stage,name,new Color(1,1,1,0),0));img.raycastTarget=true;U.At(img.rectTransform,Mid,size);return img.rectTransform;}
  // Stage-local position (for things anchored at the stage centre) of a stage fraction.
  Vector2 P(float x,float y)=>new Vector2((x-.5f)*stage.rect.width,(y-.5f)*stage.rect.height);
  Vector2 At(RectTransform target)=>U.LocalOf(stage,target);
  static Vector2 Mid=>new Vector2(.5f,.5f);
  void Hint(Func<Vector2> from,Func<Vector2> to,bool tap=false){if(hint)Destroy(hint);hint=U.Hint(this,stage,from,to,tap);}
  void StopHint(){if(hint)Destroy(hint);hint=null;}

  void BuildScene(){
   Clear();
   // Customer (live 3D portrait) with a patience ring and a name plate.
   var ring=Keep(U.Shape(stage,"PortraitRing","FFF7EC",120,new Vector2(.11f,.73f),new Vector2(236,236)));
   patience=U.Shape(ring.transform,"Patience","5DA637",0,Mid,new Vector2(236,236));patience.sprite=Ring();patience.type=Image.Type.Filled;patience.fillMethod=Image.FillMethod.Radial360;patience.fillOrigin=(int)Image.Origin360.Top;patience.fillClockwise=false;
   var hole=U.Shape(ring.transform,"Hole","B98E55",100,Mid,new Vector2(196,196));hole.gameObject.AddComponent<Mask>().showMaskGraphic=true;
   portraitRect=hole.rectTransform;
   var raw=new GameObject("Portrait",typeof(RectTransform)).AddComponent<RawImage>();raw.transform.SetParent(hole.transform,false);U.Stretch(raw.rectTransform,Vector2.zero,Vector2.one);raw.raycastTarget=false;
   var fallback=U.Icon(hole.transform,"Fallback","Icons/customers",Mid,new Vector2(150,150));fallback.transform.SetAsFirstSibling();
   portrait=new Portrait(raw,entry.customerId,fallback);
   var plate=U.Art(ring.transform,"NamePlate","panel_board",new Vector2(.5f,0),64,new Vector2(0,-18));plate.sprite=U.Sliced("panel_board",new Vector4(70,60,70,60));plate.type=Image.Type.Sliced;plate.pixelsPerUnitMultiplier=3;plate.rectTransform.sizeDelta=new Vector2(230,62);
   var nameLabel=U.Label(plate.transform,"Name",K.Headline,24,"FFFFFF");U.Stretch(nameLabel.rectTransform,Vector2.zero,Vector2.one,new Vector2(14,4),new Vector2(-14,-2));nameLabel.text=entry.customerName;nameLabel.outlineWidth=.2f;nameLabel.outlineColor=new Color32(110,62,24,255);
   // POS monitor (subtotal / change) and the receipt printer.
   var pos=Keep(U.Art(stage,"POS","pos_terminal",new Vector2(.47f,.8f),230));posScreen=U.Over(pos,"pos_terminal","screen");
   lcdCaption=U.Label(posScreen,"Caption",K.Label,17,"3F5A33",TextAlignmentOptions.TopLeft);U.Stretch(lcdCaption.rectTransform,Vector2.zero,Vector2.one,new Vector2(12,6),new Vector2(-12,-6));lcdCaption.text="SUBTOTAL";
   lcd=U.Label(posScreen,"Value",K.Number,44,"22361A",TextAlignmentOptions.BottomRight);U.Stretch(lcd.rectTransform,Vector2.zero,Vector2.one,new Vector2(12,4),new Vector2(-14,-4));lcd.text="0";
   var printer=Keep(U.Art(stage,"Printer","receipt_printer",new Vector2(.74f,.7f),210));printerSlot=U.Over(printer,"receipt_printer","slot");
   paper=Keep(U.Shape(stage,"Paper","FFFFFF",3,Mid,new Vector2(printerSlot.rect.width*.86f,6))).rectTransform;paper.pivot=new Vector2(.5f,0);paper.anchoredPosition=At(printerSlot);
   paperLines=CheckoutDesktopCard.Node("Lines",paper);U.Stretch(paperLines,Vector2.zero,Vector2.one,new Vector2(8,4),new Vector2(-8,-4));
   var column=CheckoutDesktopCard.Column(paperLines.gameObject,1);column.childAlignment=TextAnchor.LowerLeft;column.childForceExpandHeight=false;
   // Belt (the rubber surface keeps running), scanner and bag.
   var belt=Keep(U.Art(stage,"Belt","belt",new Vector2(.43f,.3f),150));beltSurface=U.Over(belt,"belt","surface");
   beltRaw=new GameObject("Rubber",typeof(RectTransform)).AddComponent<RawImage>();beltRaw.transform.SetParent(beltSurface,false);U.Stretch(beltRaw.rectTransform,Vector2.zero,Vector2.one);beltRaw.raycastTarget=false;
   var tile=Resources.Load<Texture2D>("CheckoutDesktop/Game/belt_tile");if(tile){tile.wrapMode=TextureWrapMode.Repeat;beltRaw.texture=tile;}
   scanner=Keep(U.Art(stage,"Scanner","scanner_bed",new Vector2(.745f,.3f),190));glass=U.Over(scanner,"scanner_bed","glass");
   laserGlow=U.GlowAt(glass,"LaserGlow",new Color(1,.25f,.2f,.55f),Mid,10);laserGlow.rectTransform.anchorMin=new Vector2(0,.5f);laserGlow.rectTransform.anchorMax=new Vector2(1,.5f);laserGlow.rectTransform.sizeDelta=new Vector2(40,70);
   laser=U.Shape(glass,"Laser","FF4A3A",2,Mid,new Vector2(10,5));laser.rectTransform.anchorMin=new Vector2(.03f,.5f);laser.rectTransform.anchorMax=new Vector2(.97f,.5f);laser.rectTransform.sizeDelta=new Vector2(0,5);
   bag=Keep(U.Art(stage,"Bag","shopping_bag",new Vector2(.905f,.33f),220));bagMouth=U.Over(bag,"shopping_bag","mouth");
   basketRect=Keep(U.Icon(stage,"Basket","Icons/basket",new Vector2(.1f,.26f),new Vector2(170,170))).rectTransform;
  }

  IEnumerator Intro(){
   // Products come out of the basket one by one and ride the belt to their spot.
   var items=entry.items??Array.Empty<CheckoutLine>();itemsLeft=items.Length;
   for(int i=0;i<items.Length;i++){SpawnItem(items[i],i,items.Length);Play(slide,1.2f);StartCoroutine(U.Pop(basketRect,1.08f,.2f));yield return new WaitForSecondsRealtime(.16f);}
   yield return new WaitForSecondsRealtime(.6f);
   Hint(()=>tokens.Count>0&&tokens[0]?tokens[0].anchoredPosition:At(beltSurface),()=>At(glass));
  }
  readonly List<RectTransform> tokens=new List<RectTransform>();
  void SpawnItem(CheckoutLine item,int index,int count){
   var token=Holder("Item "+item.name,new Vector2(118,118));
   U.Shadow(token,new Vector2(96,26),new Vector2(0,8));U.Icon(token,"Icon",$"Products/product-{item.productId:000}",Mid,new Vector2(118,118));
   if(item.quantity>1){var q=U.Shape(token,"Qty","2E8CAE",14,new Vector2(1,1),new Vector2(50,36),new Vector2(-8,-8));var qt=U.Label(q.transform,"Q",K.Headline,20,"FFFFFF");U.Stretch(qt.rectTransform,Vector2.zero,Vector2.one);qt.text="x"+item.quantity;}
   tokens.Add(token);
   token.anchoredPosition=At(basketRect);token.localScale=Vector3.one*.3f;
   var spot=BeltSpot(index,count);
   StartCoroutine(U.Scale(token,Vector3.one,.3f,true));StartCoroutine(U.Move(token,spot,.6f,true));
   var drag=U.Drag(token.GetComponent<Image>());drag.SetHome(spot);
   drag.Setup(new[]{glass,scanner.rectTransform},_=>{if(busy)return false;StopHint();StartCoroutine(Scan(token,item));return true;},()=>{Play(thud);StartCoroutine(U.Shake(scanner.rectTransform,.25f,6));},()=>{Play(slide,1.5f);StopHint();});
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
   laser.color=K.C("7DFF6A");laserGlow.color=new Color(.4f,1,.4f,.8f);Play(beep);StartCoroutine(U.Pop(scanner.rectTransform,1.04f,.2f));
   yield return U.Move(token,g+new Vector2(60,10),.2f);
   laser.color=K.C("FF4A3A");laserGlow.color=new Color(1,.25f,.2f,.55f);
   subtotal+=(long)Math.Round(item.quantity*item.unitPrice);lcd.text=subtotal.ToString();StartCoroutine(U.Pop(lcd.transform,1.12f,.2f));
   StartCoroutine(PrintLine($"{item.quantity}x {Short(item.name)}",$"{item.quantity*item.unitPrice:0}"));
   // Arc into the bag.
   var from=token.anchoredPosition;var to=At(bagMouth);
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.38f){var e=1-Mathf.Pow(1-t,2);token.anchoredPosition=Vector2.Lerp(from,to,e)+new Vector2(0,Mathf.Sin(t*Mathf.PI)*120);token.localScale=Vector3.one*Mathf.Lerp(1,.45f,t);yield return null;}
   Destroy(token.gameObject);Play(thud,1.6f);StartCoroutine(U.Pop(bag.rectTransform,1.1f,.25f));
   itemsLeft--;busy=false;
   if(itemsLeft<=0){lcdCaption.text="TOTAL";StartCoroutine(U.Pop(posScreen,1.08f,.3f));yield return new WaitForSecondsRealtime(.5f);ShowKeypad();}
  }
  static string Short(string name)=>name.Length>13?name.Substring(0,12)+".":name;

  // The printer pushes the paper up one line at a time.
  IEnumerator PrintLine(string left,string right,bool bold=false){
   Play(printSound);
   var row=CheckoutDesktopCard.Text(paperLines,"Line",K.Number,bold?15:12,K.Ink);row.textWrappingMode=TextWrappingModes.NoWrap;row.overflowMode=TextOverflowModes.Ellipsis;
   row.text=bold?$"<b>{left}</b><pos=62%><b>{right}</b>":$"{left}<pos=72%>{right}";row.alpha=0;
   var start=paper.sizeDelta;var to=start+new Vector2(0,bold?22:17);
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.25f){paper.sizeDelta=Vector2.Lerp(start,to,t);row.alpha=t;yield return null;}
   paper.sizeDelta=to;row.alpha=1;
  }

  // ------------------------------------------------------------------ step 2: keypad
  Image keypad;TextMeshProUGUI keypadText;RectTransform keypadScreen;
  void ShowKeypad(){
   keypad=Keep(U.Art(stage,"Keypad","keypad_panel",Mid,540));var kr=keypad.rectTransform;
   var home=P(.43f,.46f);kr.anchoredPosition=home-new Vector2(0,900);StartCoroutine(U.Move(kr,home,.45f,true));Play(slide,.8f);
   keypadScreen=U.Over(keypad,"keypad_panel","screen");
   keypadText=U.Label(keypadScreen,"Typed",K.Number,46,"22361A",TextAlignmentOptions.Right);U.Stretch(keypadText.rectTransform,Vector2.zero,Vector2.one,new Vector2(14,0),new Vector2(-16,0));keypadText.text="0";
   foreach(var key in new[]{"7","8","9","4","5","6","1","2","3","C","0","OK"}){
    var spot=U.Over(keypad,"keypad_panel","key_"+key);
    var cap=U.Icon(spot,"Cap","Game/"+(key=="C"?"key_red":key=="OK"?"key_green":"key_light"),Mid,Vector2.zero);U.Stretch(cap.rectTransform,Vector2.zero,Vector2.one,new Vector2(-2,-2),new Vector2(2,2));cap.preserveAspect=false;
    var label=U.Label(cap.transform,"Label",K.Headline,key=="OK"?30:40,key=="C"||key=="OK"?"FFFFFF":"3A4448");U.Stretch(label.rectTransform,Vector2.zero,Vector2.one,Vector2.zero,new Vector2(0,4));label.text=key;
    var k=key;U.Tap(cap,()=>Key(k,cap.rectTransform));
   }
   Hint(()=>U.LocalOf(stage,(RectTransform)keypad.transform.Find("key_"+(total.ToString()[0]))),()=>Vector2.zero,true);
  }
  void Key(string key,RectTransform cap=null){
   if(busy||finished||keypad==null)return;StopHint();
   if(cap)StartCoroutine(Press(cap));
   if(key=="C"){typed=typed.Length>0?typed.Substring(0,typed.Length-1):"";Play(click,.8f);}
   else if(key=="OK"){if(typed.Length==0){Play(buzz);StartCoroutine(U.Shake(keypadScreen,.3f));return;}StartCoroutine(Confirm());return;}
   else if(typed.Length<6){typed+=key;Play(beep,1.1f+key[0]%10*.02f);}
   keypadText.text=typed.Length>0?typed:"0";StartCoroutine(U.Pop(keypadText.transform,1.08f,.14f));
  }
  static IEnumerator Press(RectTransform cap){var img=cap.GetComponent<Image>();if(img)img.color=new Color(.8f,.8f,.8f);yield return U.Scale(cap,Vector3.one*.9f,.05f);yield return U.Scale(cap,Vector3.one,.12f,true);if(img)img.color=Color.white;}
  IEnumerator Confirm(){
   busy=true;long.TryParse(typed,out charged);
   var screen=U.Box(keypadScreen,"Flash","FFFFFF",8,Vector2.zero,Vector2.one);screen.transform.SetAsFirstSibling();
   if(charged==total){Play(ding);screen.color=new Color(.55f,.9f,.45f,.8f);StartCoroutine(Emote("heart"));}
   else if(charged>total){
    // The customer spots the overcharge: red screen, angry emote, the right total is charged.
    Play(buzz);screen.color=new Color(1,.45f,.35f,.85f);StartCoroutine(U.Shake(keypad.rectTransform,.4f));StartCoroutine(Emote("angry"));StartCoroutine(U.Shake(portraitRect,.4f,10));
    yield return new WaitForSecondsRealtime(.9f);keypadText.text=total.ToString();
   }
   else{Play(buzz,1.3f);screen.color=new Color(1,.85f,.4f,.85f);StartCoroutine(Emote("question"));}
   yield return PrintLine("TOTAL",Math.Min(charged,total).ToString(),true);
   yield return new WaitForSecondsRealtime(.6f);
   StartCoroutine(U.Move(keypad.rectTransform,keypad.rectTransform.anchoredPosition-new Vector2(0,900),.35f));yield return new WaitForSecondsRealtime(.35f);
   busy=false;
   if(entry.method=="cartao")StartCoroutine(CardStep(0));else StartCoroutine(CashStep());
  }

  // ------------------------------------------------------------------ step 3a: card machine
  Image machine,led,machineFlash;RectTransform slotRect,machineScreen;TextMeshProUGUI machineText;Image machineIcon;int cardTries;
  static readonly string[] CardArt={"card_blue","card_purple","card_red"};
  IEnumerator CardStep(int attempt){
   cardTries=attempt;
   if(machine==null){
    machine=Keep(U.Art(stage,"Machine","card_machine",Mid,380));var home=P(.55f,.4f);machine.rectTransform.anchoredPosition=home-new Vector2(0,800);StartCoroutine(U.Move(machine.rectTransform,home,.45f,true));Play(slide,.7f);
    machineScreen=U.Over(machine,"card_machine","screen");
    machineFlash=U.Box(machineScreen,"Flash","FFFFFF",6,Vector2.zero,Vector2.one);machineFlash.color=new Color(1,1,1,0);
    machineText=U.Label(machineScreen,"Text",K.Number,30,"1F3B34");U.Stretch(machineText.rectTransform,Vector2.zero,Vector2.one);machineText.text=Math.Min(charged,total).ToString();
    machineIcon=U.Icon(machineScreen,"Icon","Icons/success",Mid,new Vector2(64,64));machineIcon.gameObject.SetActive(false);
    var ledRect=U.Over(machine,"card_machine","led");led=U.GlowAt(ledRect,"Led",new Color(.3f,.3f,.3f,0),Mid,46);
    slotRect=U.Over(machine,"card_machine","slot");
    yield return new WaitForSecondsRealtime(.45f);
   }
   // The customer holds out a card (a different one after a decline).
   var card=Holder("Card",new Vector2(128*U.Aspect(CardArt[attempt%3]),128));U.Shadow(card,new Vector2(170,30),new Vector2(0,6));U.Art(card,"Face",CardArt[attempt%3],Mid,128);
   var hold=P(.25f,.34f);card.anchoredPosition=hold-new Vector2(500,0);card.localRotation=Quaternion.Euler(0,0,-8);StartCoroutine(U.Move(card,hold,.45f,true));Play(slide,1.3f);
   if(attempt>0)StartCoroutine(Emote("sweat"));
   yield return new WaitForSecondsRealtime(.45f);
   var drag=U.Drag(card.GetComponent<Image>());drag.SetHome(hold);
   drag.Setup(new[]{slotRect,machine.rectTransform},_=>{StopHint();StartCoroutine(Insert(card,drag));return true;},()=>Play(thud),StopHint);
   Hint(()=>card?card.anchoredPosition:Vector2.zero,()=>At(slotRect));
  }
  IEnumerator Insert(RectTransform card,CheckoutDragToken drag){
   drag.Locked=true;busy=true;
   // Turn upright over the slot, then slide down into the machine behind a mask at the slot line.
   var slot=At(slotRect);var shadow=card.Find("Shadow");if(shadow)shadow.gameObject.SetActive(false);
   float length=card.rect.width;
   StartCoroutine(U.Rotate(card,90,.2f));yield return U.Move(card,slot+new Vector2(0,length*.5f+14),.22f);
   Play(slide,.8f);
   var clip=CheckoutDesktopCard.Node("Clip",stage);clip.anchorMin=clip.anchorMax=Mid;clip.pivot=new Vector2(.5f,0);clip.sizeDelta=new Vector2(320,700);clip.anchoredPosition=slot;clip.gameObject.AddComponent<RectMask2D>();scene.Add(clip.gameObject);
   card.SetParent(clip,true);
   var outside=card.anchoredPosition;var inside=outside-new Vector2(0,length*.62f);
   yield return U.Move(card,inside,.3f);Play(thud,1.8f);StartCoroutine(U.Shake(machine.rectTransform,.12f,4));
   // Processing: blinking dots and an amber LED.
   for(int i=0;i<6;i++){machineText.text=new string('•',i%3+1);led.color=i%2==0?new Color(1,.75f,.2f,.9f):new Color(.3f,.3f,.3f,0);Play(beep,.6f);yield return new WaitForSecondsRealtime(.24f);}
   // Some cards are declined. After two declines the customer pays cash instead.
   bool approved=cardTries>=1?UnityEngine.Random.value<.9f:UnityEngine.Random.value<.8f;
   machineText.text="";machineIcon.gameObject.SetActive(true);machineIcon.rectTransform.localScale=Vector3.zero;StartCoroutine(U.Scale(machineIcon.rectTransform,Vector3.one,.3f,true));
   if(approved){
    machineIcon.sprite=K.Icon("Icons/success");machineFlash.color=new Color(.55f,.95f,.5f,.9f);led.color=new Color(.35f,1,.35f,1);Play(ding);StartCoroutine(U.Pop(machine.rectTransform,1.06f,.3f));
    yield return new WaitForSecondsRealtime(.35f);
    Play(slide,1.2f);yield return U.Move(card,outside+new Vector2(0,20),.22f);
    card.SetParent(stage,true);StartCoroutine(U.Rotate(card,-10,.3f));StartCoroutine(U.Move(card,P(.12f,.62f),.45f));StartCoroutine(U.Scale(card,Vector3.one*.4f,.45f));
    yield return Finish();
   }
   else{
    machineIcon.sprite=K.Icon("Icons/warning");machineFlash.color=new Color(1,.4f,.3f,.9f);led.color=new Color(1,.25f,.2f,1);Play(buzz);StartCoroutine(U.Shake(machine.rectTransform,.5f,12));
    yield return new WaitForSecondsRealtime(.25f);
    yield return U.Move(card,outside+new Vector2(0,60),.18f);Play(thud,1.2f);
    card.SetParent(stage,true);StartCoroutine(Emote("sweat"));
    yield return new WaitForSecondsRealtime(.35f);StartCoroutine(U.Rotate(card,-30,.3f));yield return U.Move(card,P(-.1f,.3f),.4f);
    machineIcon.gameObject.SetActive(false);machineFlash.color=new Color(1,1,1,0);led.color=new Color(.3f,.3f,.3f,0);machineText.text=Math.Min(charged,total).ToString();busy=false;
    if(cardTries>=1){StartCoroutine(U.Move(machine.rectTransform,machine.rectTransform.anchoredPosition-new Vector2(0,800),.35f));yield return new WaitForSecondsRealtime(.35f);machine=null;StartCoroutine(CashStep());}
    else StartCoroutine(CardStep(cardTries+1));
   }
  }

  // ------------------------------------------------------------------ step 3b: cash drawer
  Image tray,dish;readonly List<int> handPile=new List<int>();readonly List<RectTransform> handNotes=new List<RectTransform>();long changeDue,changeGiven;TextMeshProUGUI dishSum;GameObject dishBadge;
  IEnumerator CashStep(){
   long price=Math.Min(charged,total),given=(long)Math.Round(Math.Max(entry.cashGiven,price));
   if(given<price)given=price;
   changeDue=given-price;changeGiven=0;handPile.Clear();handNotes.Clear();
   // The drawer rolls out of the counter; the customer's dish holds the notes they pay with.
   tray=Keep(U.Art(stage,"Drawer","cash_tray",Mid,330));var home=P(.64f,.24f);tray.rectTransform.anchoredPosition=home-new Vector2(0,700);Play(slide,.6f);StartCoroutine(U.Move(tray.rectTransform,home,.5f,true));
   dish=Keep(U.Art(stage,"Dish","change_dish",Mid,170));dish.rectTransform.anchoredPosition=P(.24f,.22f);
   dishBadge=Keep(U.Shape(stage,"DishBadge","FFF7EC",18,Mid,new Vector2(150,52))).gameObject;var br=(RectTransform)dishBadge.transform;br.anchoredPosition=P(.24f,.22f)+new Vector2(0,-110);
   U.Icon(br,"Coin","Icons/coin",new Vector2(0,.5f),new Vector2(44,44),new Vector2(28,0));
   dishSum=U.Label(br,"Sum",K.Headline,28,"4A3624");U.Stretch(dishSum.rectTransform,new Vector2(.32f,0),Vector2.one,Vector2.zero,new Vector2(-10,0));dishSum.text=given.ToString();
   lcdCaption.text=changeDue>0?"TROCO":"TOTAL";lcd.text=changeDue>0?changeDue.ToString():price.ToString();StartCoroutine(U.Pop(posScreen,1.08f,.3f));
   yield return new WaitForSecondsRealtime(.55f);
   var notes=Split(given);int placed=0;var first=default(RectTransform);
   for(int i=0;i<notes.Count;i++){
    int value=notes[i];var note=Money(stage,value,P(.24f,.22f)+new Vector2(-30+i*14,20+i*8),1f);note.localRotation=Quaternion.Euler(0,0,UnityEngine.Random.Range(-14,14));if(first==null)first=note;
    note.localScale=Vector3.zero;StartCoroutine(U.Scale(note,Vector3.one,.25f,true));Play(printSound,1.6f);
    var drag=U.Drag(note.GetComponent<Image>());drag.SetHome(note.anchoredPosition);
    drag.Setup(new[]{tray.rectTransform},_=>{drag.Locked=true;placed++;StopHint();StartCoroutine(DropNote(note,value,placed==notes.Count));return true;},()=>Play(thud),StopHint);
    yield return new WaitForSecondsRealtime(.1f);
   }
   Hint(()=>first?first.anchoredPosition:Vector2.zero,()=>At(tray.rectTransform));
  }
  RectTransform Bin(int value){int i=Array.IndexOf(BinValues,value);return i>=0?U.Over(tray,"cash_tray","bin"+i,"BinSpot"):U.Over(tray,"cash_tray","cup0","CupSpot");}
  IEnumerator DropNote(RectTransform note,int value,bool last){
   // Each note goes to its own slot in the drawer.
   var spot=Bin(value);note.SetParent(tray.rectTransform,true);var to=(Vector2)tray.rectTransform.InverseTransformPoint(spot.TransformPoint(spot.rect.center))+new Vector2(UnityEngine.Random.Range(-6,6),UnityEngine.Random.Range(-10,10));Destroy(spot.gameObject);
   note.anchorMin=note.anchorMax=Mid;
   StartCoroutine(U.Rotate(note,value<=1?0:90,.2f));StartCoroutine(U.Scale(note,Vector3.one*(value<=1?.6f:.62f),.2f));yield return U.Move(note,to,.24f);Play(cash,.8f);
   dishSum.text=Math.Max(0,long.Parse(dishSum.text)-value).ToString();
   if(last){
    dishSum.text="0";yield return new WaitForSecondsRealtime(.3f);
    if(changeDue<=0){yield return CloseDrawer();yield return Finish();}
    else{BuildChange();StartCoroutine(Emote("question"));}
   }
  }
  // Piles of change in the drawer: drag notes and coins to the customer's dish.
  void BuildChange(){
   var values=BinValues.Where(v=>v<=Math.Max(changeDue,1)*2).ToList();values.Add(1);
   foreach(var value in values)for(int n=0;n<3;n++)ChangePiece(value,n);
   var firstValue=Denominations.First(v=>v<=changeDue);
   Hint(()=>PileSpot(firstValue),()=>dish?dish.rectTransform.anchoredPosition:Vector2.zero);
  }
  Vector2 PileSpot(int value){var spot=Bin(value);var p=At(spot);Destroy(spot.gameObject);return p;}
  void ChangePiece(int value,int layer){
   var note=Money(stage,value,PileSpot(value)+new Vector2(0,-6+layer*6),value<=1?.6f:.62f);if(value>1)note.localRotation=Quaternion.Euler(0,0,90);
   var drag=U.Drag(note.GetComponent<Image>());drag.SetHome(note.anchoredPosition);
   drag.Setup(new[]{dish.rectTransform},_=>{GiveChange(note,value);return true;},()=>Play(thud),StopHint);
  }
  void GiveChange(RectTransform note,int value){
   if(finished)return;StopHint();
   note.GetComponent<CheckoutDragToken>().Locked=true;
   var spot=dish.rectTransform.anchoredPosition+new Vector2(UnityEngine.Random.Range(-40,40),UnityEngine.Random.Range(0,24));
   StartCoroutine(U.Rotate(note,UnityEngine.Random.Range(-15,15),.2f));StartCoroutine(U.Scale(note,Vector3.one*(value<=1?.55f:.7f),.2f));StartCoroutine(U.Move(note,spot,.2f));
   changeGiven+=value;handPile.Add(value);handNotes.Add(note);dishSum.text=changeGiven.ToString();StartCoroutine(U.Pop(dishSum.transform,1.15f,.2f));Play(cash,.9f+handPile.Count*.05f);
   ChangePiece(value,2); // Refill the pile so there is always enough change.
   if(changeGiven==changeDue){StartCoroutine(Emote("heart"));StartCoroutine(ChangeDone());}
   else if(changeGiven>changeDue){
    // Too much: the customer pushes the extra back into the drawer.
    StartCoroutine(Emote("sweat"));Play(buzz,1.2f);handPile.RemoveAt(handPile.Count-1);handNotes.RemoveAt(handNotes.Count-1);changeGiven-=value;dishSum.text=changeGiven.ToString();
    StartCoroutine(Return(note,value));StartCoroutine(U.Shake(dish.rectTransform,.3f,10));
   }
  }
  IEnumerator Return(RectTransform note,int value){yield return new WaitForSecondsRealtime(.35f);if(!note)yield break;yield return U.Move(note,PileSpot(value),.35f);if(note)Destroy(note.gameObject);}
  IEnumerator ChangeDone(){finished=true;yield return new WaitForSecondsRealtime(.4f);yield return CloseDrawer();finished=false;yield return Finish();}
  IEnumerator CloseDrawer(){
   Play(slide,.6f);foreach(var o in scene.ToList())if(o&&o.name.StartsWith("Money")&&o.transform.parent==stage&&!handNotes.Contains((RectTransform)o.transform)){var r=(RectTransform)o.transform;StartCoroutine(U.Move(r,r.anchoredPosition-new Vector2(0,700),.3f));}
   yield return U.Move(tray.rectTransform,tray.rectTransform.anchoredPosition-new Vector2(0,700),.3f);Play(thud,.8f);StartCoroutine(U.Shake(stage,.15f,4));
  }
  static List<int> Split(long amount){var notes=new List<int>();foreach(var v in Denominations)while(amount>=v&&notes.Count<6){notes.Add(v);amount-=v;}if(amount>0)notes.Add((int)amount);return notes;}
  RectTransform Money(RectTransform parent,int value,Vector2 at,float scale){
   var art=value<=1?"coin_1":"note_"+value;var img=Keep(U.Art(parent,"Money "+value,art,Mid,value<=1?64:92,at));img.rectTransform.localScale=Vector3.one*scale;return img.rectTransform;
  }

  // ------------------------------------------------------------------ done
  IEnumerator Finish(){
   if(finished&&closeAt>0)yield break;finished=true;StopHint();
   bridge.Command("completeCheckout","[\""+entry.id+"\","+Math.Max(1,charged)+"]");
   Play(ding,1.2f);StartCoroutine(Emote(charged<=total?"heart":"angry"));
   // The bag goes to the customer, coins fly to the POS and sparkles pop.
   StartCoroutine(U.Move(bag.rectTransform,At(portraitRect)+new Vector2(90,-140),.6f));StartCoroutine(U.Scale(bag.rectTransform,Vector3.one*.55f,.6f));
   U.Sparkles(this,stage,At(posScreen),10,180);
   yield return U.Coins(this,stage,P(.55f,.35f),At(posScreen),Mathf.Clamp((int)(Math.Min(charged,total)/5)+3,4,14));
   closeAt=Time.unscaledTime+1.2f;
  }
  IEnumerator Emote(string kind){if(!portraitRect)yield break;yield return U.Emote(this,stage,kind,At(portraitRect)+new Vector2(110,95),100);}

  void Update(){
   var ready=Ready().Count();
   fab.SetActive(ready>0&&!IsOpen&&!(CheckoutIncidents.Instance&&CheckoutIncidents.Instance.IsOpen));if(fab.activeSelf){fabText.text=ready.ToString();fabRect.localScale=Vector3.one*(1+Mathf.Sin(Time.unscaledTime*4)*.03f);}
   if(!IsOpen)return;
   // Belt keeps running; the laser breathes.
   if(beltRaw){var r=beltSurface.rect;float tiles=r.height>0?r.width/(r.height*4f):4;beltRaw.uvRect=new Rect(-Time.unscaledTime*.35f,0,tiles,1);}
   if(laser&&!busy){float k=Mathf.PingPong(Time.unscaledTime*2,1);laser.color=Color.Lerp(K.C("FF4A3A"),K.C("B8261A"),k);laserGlow.color=new Color(1,.25f,.2f,.35f+.25f*k);}
   portrait?.Tick();
   if(closeAt>0){if(Time.unscaledTime>closeAt)Close();return;}
   var live=Find(entry.id);
   if(live==null){ // Gave up waiting (or a cashier served them): they walk away annoyed.
    if(!finished){finished=true;StopHint();StartCoroutine(Emote("angry"));Play(buzz,.8f);closeAt=Time.unscaledTime+1.8f;StartCoroutine(U.Shake(portraitRect,.5f,12));}
    return;}
   double now=CheckoutBridge.Now,left=Math.Max(0,live.expiresAt-now),span=Math.Max(1,live.expiresAt-live.readyAt);float ratio=(float)(left/span);
   patience.fillAmount=Mathf.Clamp01(ratio);patience.color=Color.Lerp(K.C("E15533"),K.C("5DA637"),Mathf.InverseLerp(.15f,.5f,ratio));
   if(ratio<.25f&&!finished&&Mathf.Repeat(Time.unscaledTime,4f)<Time.unscaledDeltaTime)StartCoroutine(Emote("sweat"));
   if(Input.GetKeyDown(KeyCode.Escape))Close();
   if(keypad){for(int d=0;d<=9;d++)if(Input.GetKeyDown(KeyCode.Alpha0+d)||Input.GetKeyDown(KeyCode.Keypad0+d))Key(d.ToString());if(Input.GetKeyDown(KeyCode.Backspace))Key("C");if(Input.GetKeyDown(KeyCode.Return)||Input.GetKeyDown(KeyCode.KeypadEnter))Key("OK");}
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
   readonly RawImage image;readonly Image fallback;readonly string customerId;Transform target;Camera cam;RenderTexture texture;float searchAt;bool logged;Transform headBone;
   public Portrait(RawImage raw,string id,Image placeholder){image=raw;customerId=id;fallback=placeholder;image.enabled=false;Tick();}
   void Attach(Transform walker){
    target=walker;texture=new RenderTexture(384,384,24);
    var go=new GameObject("Customer portrait camera");cam=go.AddComponent<Camera>();cam.targetTexture=texture;cam.fieldOfView=30;cam.nearClipPlane=.05f;cam.farClipPlane=80;cam.depth=-20;
    cam.clearFlags=CameraClearFlags.SolidColor;cam.backgroundColor=K.C("EAD9BE");
    image.texture=texture;image.enabled=true;if(fallback)fallback.enabled=false;
   }
   public void Tick(){
    if(!target){
     if(cam){UnityEngine.Object.Destroy(cam.gameObject);cam=null;image.enabled=false;if(fallback)fallback.enabled=true;}
     if(Time.unscaledTime<searchAt)return;searchAt=Time.unscaledTime+.5f;var w=FindWalker(customerId);if(w)Attach(w);else return;
    }
    // Skinned bounds are unreliable off screen, so aim at the head bone (or a child named "head").
    if(!headBone){var animator=target.GetComponentInChildren<Animator>();if(animator&&animator.isHuman)headBone=animator.GetBoneTransform(HumanBodyBones.Head);if(!headBone)headBone=target.GetComponentsInChildren<Transform>().FirstOrDefault(t=>t.name.ToLowerInvariant().Contains("head"));}
    var head=headBone?headBone.position:target.position+Vector3.up*1.55f;float h=Mathf.Clamp(head.y-target.position.y,.6f,2.2f);
    var face=-target.forward;face.y=0;if(face.sqrMagnitude<.01f)face=Vector3.back;face.Normalize();
    cam.transform.position=head+face*h*.55f+Vector3.up*h*.02f;cam.transform.LookAt(head-Vector3.up*h*.06f);
    if(!logged){logged=true;var info=$"CHECKOUT_PORTRAIT target={target.name} head={(headBone?headBone.name:"none")} headPos={head} root={target.position} cam={cam.transform.position}";try{System.IO.File.AppendAllText("Logs/portrait.txt",info+"\n");}catch{}Debug.Log(info);}
   }
   public void Release(){if(cam)UnityEngine.Object.Destroy(cam.gameObject);if(texture){texture.Release();UnityEngine.Object.Destroy(texture);}}
  }
 }
}
