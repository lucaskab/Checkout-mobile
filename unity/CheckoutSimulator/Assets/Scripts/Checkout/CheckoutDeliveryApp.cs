using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // Delivery: the online-order app on the store computer (Delivery tab of CheckoutSupplierShop), built like a
 // mobile game: a rank and streak header, offer tickets, a mission card per order with a road strip, a live city
 // map, and a bouncy notification pill. Cards are built once and updated in place; the store is read 4 times a
 // second. Columns are in CheckoutDeliveryApp.Cards.cs, the mission cards in CheckoutDeliveryApp.Mission.cs, the map
 // in CheckoutDeliveryApp.Map.cs and the juice (buttons, coins, confetti) in CheckoutDeliveryApp.Fx.cs.
 public sealed partial class CheckoutDeliveryApp:MonoBehaviour {
  public static CheckoutDeliveryApp Instance {get;private set;}
  // Opens the store computer on the Delivery tab.
  public static void ShowTab(){CheckoutSupplierShop.ShowDelivery();}

  const string Ink="4A3624",Muted="8A7560",Green="3DAA5C",Red="E15533",Blue="2E8CAE",Gold="F2B03D",EmptyTone="E5D6BC",Paper="FFF6E4";
  const double MoneyDoorWait=60000;
  const float PillHold=6f;
  static readonly CultureInfo Br=CultureInfo.GetCultureInfo("pt-BR");
  static readonly string[] AvatarColors={"2E8CAE","E15533","3DAA5C","8B5C9E","F2B03D","E0884A"};
  static readonly string[] StepNames={"Aceito","Embalar","Moto","Na porta","A caminho"};
  // Ranks by deliveries made: name, colour of the XP bar, and the count each rank starts at.
  static readonly string[] RankNames={"Bronze","Prata","Ouro","Diamante"};
  static readonly string[] RankColors={"C98B4B","9AA8B4","F2B03D","5FD4F0"};
  static readonly int[] RankFrom={0,10,30,80};

  CheckoutBridge bridge;RectTransform host,root,headerRect,pillRoot,pill,offersContent,activeContent,historyContent,mapFrame;
  GameObject lockedNode,offersEmpty,activeEmpty,historyEmpty;
  TextMeshProUGUI offersCount,activeCount,lockSub,pillTitle,pillSub,pillInitials;
  TextMeshProUGUI rankName,rankXp,streakText,ratingText,motosText;
  Image rankFill,streakFlame,ratingStar,motoIcon,pillDisc;
  Image[] streakSegments=new Image[10];Image[] pillStarImgs=new Image[5];
  GameObject pillStars;JuicyButton pillOpen;
  int lastRank=-1,lastSegments=-1,reportedMask;
  bool built,primed,pillBusy,pillHide;string session="";float refreshAt;
  readonly Dictionary<string,OfferView> offers=new Dictionary<string,OfferView>();
  readonly Dictionary<string,ActiveView> actives=new Dictionary<string,ActiveView>();
  readonly Dictionary<string,string> seen=new Dictionary<string,string>();
  readonly Queue<Notice> notices=new Queue<Notice>();

  // A pill announcement. Kind: 0 new offer (chime), 1 motoboy at the door (horn), 2 delivered (coin + a ding per star).
  // Avatar seeds the coloured disc; Name gives the initials.
  sealed class Notice{public int Kind,Stars,Avatar;public string Title,Sub,Name;}

  public void Initialize(CheckoutBridge owner){
   Instance=this;bridge=owner;
   pillRoot=U.Canvas(transform,"CheckoutDeliveryPill",95);
   fxRoot=U.Canvas(transform,"CheckoutDeliveryFx",96);
   BuildPill();
  }

  // ------------------------------------------------------------------ helpers (shared with the column code)
  static string Money(long v)=>v.ToString("N0",Br);
  static string Km(float km)=>km.ToString("0.0",Br)+" km";
  // Countdown: m:ss, or Ns under a minute.
  static string Clock(double seconds){int s=Mathf.Max(0,(int)Math.Ceiling(seconds));return (s/60)+":"+(s%60).ToString("00",CultureInfo.InvariantCulture);}
  static string Short(double seconds){int s=Mathf.Max(0,(int)Math.Ceiling(seconds));return s<60?s+"s":Clock(seconds);}
  static double Secs(double ms,double now)=>(ms-now)/1000.0;
  static string Q(string id)=>"[\""+(id??"").Replace("\\","\\\\").Replace("\"","\\\"")+"\"]";
  static string AvatarHex(int seed)=>AvatarColors[Mathf.Abs(seed)%AvatarColors.Length];
  static int SeedOf(string text){int h=0;foreach(char ch in text??"")h=unchecked(h*31+ch);return Mathf.Abs(h);}
  static string Initials(string name){
   var parts=(name??"").Split(new[]{' '},StringSplitOptions.RemoveEmptyEntries);
   if(parts.Length==0)return "?";
   if(parts.Length==1)return parts[0].Substring(0,1).ToUpperInvariant();
   return (parts[0].Substring(0,1)+parts[parts.Length-1].Substring(0,1)).ToUpperInvariant();
  }
  static string FirstName(string name){
   var parts=(name??"").Split(new[]{' '},StringSplitOptions.RemoveEmptyEntries);
   return parts.Length==0?"":parts[0];
  }
  // A phrase of the courier, stable for one order (the same order always gets the same line).
  static string Pick(string[] list,string seed){
   if(list==null||list.Length==0)return "";
   return list[SeedOf(seed)%list.Length];
  }
  // Step of the timeline a status sits on (0 Aceito .. 4 A caminho), -1 when it is not an active order.
  static int StageOf(string status){
   switch(status){
    case "aceito":return 1;
    case "aguardando-moto":return 2;
    case "moto-na-porta":return 3;
    case "a-caminho":return 4;
    default:return -1;
   }
  }
  // Rank by deliveries: 0 Bronze, 1 Prata, 2 Ouro, 3 Diamante.
  static int RankOf(int delivered){int r=0;for(int i=1;i<RankFrom.Length;i++)if(delivered>=RankFrom[i])r=i;return r;}
  static float Ease(float t)=>1-Mathf.Pow(1-t,3);
  static LayoutElement Pref(GameObject go,float w,float h){
   var le=go.GetComponent<LayoutElement>();if(!le)le=go.AddComponent<LayoutElement>();
   if(w>=0)le.preferredWidth=w;
   if(h>=0)le.preferredHeight=h;
   return le;
  }
  // Takes a node out of its layout group (backgrounds, overlays, anything that must not be re-laid out per frame).
  static void Overlay(GameObject go){go.AddComponent<LayoutElement>().ignoreLayout=true;}
  // An image of a given sprite (a 3D icon or a procedural one), sized by the layout.
  static Image SpriteImg(Transform parent,string name,Sprite sprite,Color tint,float w,float h){
   var img=N.Image(parent,name,tint,0);img.sprite=sprite;img.preserveAspect=true;img.raycastTarget=false;Pref(img.gameObject,w,h);return img;
  }
  static Image LayImg(Transform parent,string name,string path,float w,float h)=>SpriteImg(parent,name,K.Icon(path),Color.white,w,h);
  // A chunky game panel (outline, highlight, shadow) as a sliced image filling its rect.
  static Image Panel(Transform parent,string name,string fillHex,int radius=20){
   var img=N.Image(parent,name,Color.white,0);img.sprite=DeliveryArt.Chunk(fillHex,radius);img.type=Image.Type.Sliced;img.raycastTarget=false;
   return img;
  }
  // A round avatar: a seeded coloured disc with a dark outline and big white initials. Returns the disc.
  static Image Avatar(Transform parent,string name,float size,out TextMeshProUGUI initials){
   var node=N.Node(name,parent);Pref(node.gameObject,size,size);
   var disc=N.Image(node,"Disc",Color.white,0);disc.sprite=DeliveryArt.Disc(AvatarColors[0]);disc.raycastTarget=false;U.Stretch(disc.rectTransform,Vector2.zero,Vector2.one);
   initials=U.Label(node,"Initials",K.Headline,Mathf.Round(size*.4f),"FFFFFF");U.Stretch(initials.rectTransform,Vector2.zero,Vector2.one);
   return disc;
  }
  // Paints an avatar from its seed and its initials (cheap: the disc sprites are cached).
  static void PaintAvatar(Image disc,TextMeshProUGUI initials,int seed,string name){
   if(disc)disc.sprite=DeliveryArt.Disc(AvatarHex(seed));
   if(initials&&initials.text!=Initials(name))initials.text=Initials(name);
  }
  static Image Star(Transform parent,bool on,float size)=>SpriteImg(parent,"Star",on?DeliveryArt.StarOn:DeliveryArt.StarOff,Color.white,size,size);
  static void Fit(RectTransform r){var f=r.gameObject.AddComponent<ContentSizeFitter>();f.verticalFit=ContentSizeFitter.FitMode.PreferredSize;}
  // A clipped scroll view whose content the caller lays out.
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
  // Column head: a saturated title ribbon and a count chip.
  static void SectionHead(RectTransform parent,string title,out TextMeshProUGUI count){
   var head=N.Node("Head",parent);N.Row(head.gameObject,10).childAlignment=TextAnchor.MiddleLeft;Pref(head.gameObject,-1,50);
   var ribbon=Panel(head,"Ribbon",Blue,16);N.Row(ribbon.gameObject,0,new RectOffset(18,18,4,4)).childAlignment=TextAnchor.MiddleLeft;Pref(ribbon.gameObject,-1,50).flexibleWidth=1;
   var label=U.Label(ribbon.transform,"Title",K.Headline,26,"FFFFFF",TextAlignmentOptions.Left);
   label.text=title;
   var chip=Panel(head,"CountBack",Gold,14);N.Row(chip.gameObject,0,new RectOffset(14,14,3,3));Pref(chip.gameObject,-1,40);
   count=U.Label(chip.transform,"Count",K.Number,20,Ink);
  }
  // A friendly empty state: a 3D icon at 120 px, a title and a tip, centred.
  static GameObject Empty(RectTransform parent,Sprite picture,string title,string text,float height){
   var node=N.Node("Empty",parent);N.Column(node.gameObject,10).childAlignment=TextAnchor.MiddleCenter;Pref(node.gameObject,-1,height);
   SpriteImg(node,"Picture",picture,Color.white,120,120);
   U.Label(node,"Title",K.Headline,28,Ink,TextAlignmentOptions.Center).text=title;
   var body=N.Text(node,"Body",K.Body,19,K.C(Muted));body.alignment=TextAlignmentOptions.Center;body.text=text;Pref(body.gameObject,-1,60);
   return node.gameObject;
  }
  static bool Blocked()=>(CheckoutPackingGame.Instance&&CheckoutPackingGame.Instance.IsOpen)||(CheckoutRestockGame.Instance&&CheckoutRestockGame.Instance.IsOpen)||(CheckoutReceivingGame.Instance&&CheckoutReceivingGame.Instance.IsOpen)||(CheckoutCounterGame.Instance&&CheckoutCounterGame.Instance.IsOpen);

  // ------------------------------------------------------------------ build: the Delivery tab body
  void Build(RectTransform body){
   host=body;built=true;
   root=N.Node("Delivery",host);U.Stretch(root,Vector2.zero,Vector2.one,new Vector2(14,12),new Vector2(-14,-12));
   N.Column(root.gameObject,12);
   BuildHeader(root);
   // Three columns share the rest of the screen: offers 38%, orders in progress 34%, map and history 28%.
   var row=N.Node("Panels",root);N.Row(row.gameObject,14).childAlignment=TextAnchor.UpperLeft;Pref(row.gameObject,-1,-1).flexibleHeight=1;
   BuildOffersColumn(row,38);
   BuildActiveColumn(row,34);
   BuildSideColumn(row,28);
   BuildLocked();
  }
  // Header: four chunky chips (rank with XP, streak flame meter, rating star, motoboys).
  void BuildHeader(RectTransform parent){
   headerRect=N.Node("Header",parent);N.Row(headerRect.gameObject,12).childAlignment=TextAnchor.MiddleCenter;Pref(headerRect.gameObject,-1,116);
   // Rank chip: the medal icon, title, XP bar and the delivery count.
   var rank=Chip(headerRect,"Rank",1.7f);
   SpriteImg(rank.transform,"Medal",K.Icon("Icons/medal"),Color.white,72,72);
   var rt=N.Node("Texts",rank.transform);N.Column(rt.gameObject,2);Pref(rt.gameObject,-1,-1).flexibleWidth=1;
   U.Label(rt,"Kicker",K.Body,18,Muted,TextAlignmentOptions.Left).text="Rank de entregador";
   rankName=U.Label(rt,"Name",K.Headline,28,Ink,TextAlignmentOptions.Left);
   var xp=Panel(rt,"XpBack",EmptyTone,8);Pref(xp.gameObject,-1,18);
   rankFill=N.Image(xp.transform,"XpFill",Color.white,0);rankFill.sprite=DeliveryArt.Chunk(RankColors[0],8);rankFill.type=Image.Type.Filled;rankFill.fillMethod=Image.FillMethod.Horizontal;rankFill.fillAmount=0;
   U.Stretch(rankFill.rectTransform,Vector2.zero,Vector2.one,new Vector2(3,3),new Vector2(-3,-3));
   rankXp=U.Label(xp.transform,"XpText",K.Number,15,Ink);U.Stretch(rankXp.rectTransform,Vector2.zero,Vector2.one);
   // Streak chip: a flame that grows with the streak, and a 10-segment meter.
   var streak=Chip(headerRect,"Streak",1.3f);
   streakFlame=SpriteImg(streak.transform,"Flame",K.Icon("Icons/flame"),Color.white,60,60);
   var st=N.Node("Texts",streak.transform);N.Column(st.gameObject,2);Pref(st.gameObject,-1,-1).flexibleWidth=1;
   U.Label(st,"Kicker",K.Body,18,Muted,TextAlignmentOptions.Left).text="Sequência";
   streakText=U.Label(st,"Value",K.Headline,28,Ink,TextAlignmentOptions.Left);
   var meter=N.Node("Meter",st);N.Row(meter.gameObject,3);Pref(meter.gameObject,-1,14);
   for(int i=0;i<streakSegments.Length;i++){var seg=Panel(meter,"Seg",EmptyTone,4);Pref(seg.gameObject,-1,14).flexibleWidth=1;streakSegments[i]=seg;}
   // Rating chip: the star and the number.
   var rate=Chip(headerRect,"Rating",1f);
   ratingStar=SpriteImg(rate.transform,"Star",DeliveryArt.StarOn,Color.white,52,52);
   var rr=N.Node("Texts",rate.transform);N.Column(rr.gameObject,2);Pref(rr.gameObject,-1,-1).flexibleWidth=1;
   U.Label(rr,"Kicker",K.Body,18,Muted,TextAlignmentOptions.Left).text="Nota";
   ratingText=U.Label(rr,"Value",K.Headline,30,Ink,TextAlignmentOptions.Left);
   // Motoboys: the delivery truck icon and x/y.
   var motos=Chip(headerRect,"Motos",1f);
   motoIcon=SpriteImg(motos.transform,"Moto",DeliveryArt.Moto,Color.white,60,60);
   var mt=N.Node("Texts",motos.transform);N.Column(mt.gameObject,2);Pref(mt.gameObject,-1,-1).flexibleWidth=1;
   U.Label(mt,"Kicker",K.Body,18,Muted,TextAlignmentOptions.Left).text="Motoboys ativos";
   motosText=U.Label(mt,"Value",K.Headline,30,Ink,TextAlignmentOptions.Left);
  }
  // A cream chunky panel that lays out its children in a row.
  Image Chip(RectTransform parent,string name,float flex){
   var chip=Panel(parent,name,Paper,20);
   N.Row(chip.gameObject,12,new RectOffset(16,16,8,8)).childAlignment=TextAnchor.MiddleLeft;
   Pref(chip.gameObject,-1,116).flexibleWidth=flex;
   return chip;
  }
  // Locked: the teaser until the market reaches the Minimercado era.
  void BuildLocked(){
   lockedNode=N.Node("Locked",host).gameObject;U.Stretch(lockedNode.transform as RectTransform,Vector2.zero,Vector2.one);
   var card=Panel(lockedNode.transform,"Card",Paper,26);U.At(card.rectTransform,new Vector2(.5f,.5f),new Vector2(780,600),Vector2.zero);
   var col=N.Column(card.gameObject,14,new RectOffset(48,48,34,34));col.childAlignment=TextAnchor.MiddleCenter;
   SpriteImg(card.transform,"Picture",DeliveryArt.Moto,Color.white,160,160);
   U.Label(card.transform,"Title",K.Headline,36,Ink,TextAlignmentOptions.Center).text="Delivery da loja";
   lockSub=U.Label(card.transform,"Sub",K.Headline,26,"B5651D",TextAlignmentOptions.Center);
   string[] bullets={"Vizinhos pedem compras online pelo app","Você embala o pedido e o motoboy leva até a porta","Entregas perfeitas dão estrelas, gorjeta e sequência"};
   foreach(var line in bullets){
    var item=N.Text(card.transform,"Bullet",K.Body,20,K.C(Ink));item.alignment=TextAlignmentOptions.Center;item.text="•  "+line;Pref(item.gameObject,-1,30);
   }
   lockedNode.SetActive(false);
  }

  // ------------------------------------------------------------------ notification pill (game-style, with an avatar)
  void BuildPill(){
   pill=Panel(pillRoot,"Pill","2B2118",26).rectTransform;
   U.At(pill,new Vector2(.5f,1),new Vector2(640,118),new Vector2(0,140));
   N.Row(pill.gameObject,14,new RectOffset(16,18,10,10)).childAlignment=TextAnchor.MiddleLeft;
   pillDisc=Avatar(pill,"Portrait",92,out pillInitials);
   var tx=N.Node("Texts",pill);N.Column(tx.gameObject,0);Pref(tx.gameObject,-1,-1).flexibleWidth=1;
   pillTitle=U.Label(tx,"Title",K.Headline,26,"FFFFFF",TextAlignmentOptions.Left);
   pillSub=U.Label(tx,"Sub",K.Body,19,"E9DCC4",TextAlignmentOptions.Left);
   var right=N.Node("Right",pill);N.Column(right.gameObject,6).childAlignment=TextAnchor.MiddleCenter;Pref(right.gameObject,150,-1);
   var stars=N.Node("Stars",right);N.Row(stars.gameObject,3).childAlignment=TextAnchor.MiddleCenter;Pref(stars.gameObject,-1,26);
   for(int i=0;i<pillStarImgs.Length;i++)pillStarImgs[i]=SpriteImg(stars,"Star",DeliveryArt.StarOff,Color.white,26,26);
   pillStars=stars.gameObject;pillStars.SetActive(false);
   pillOpen=JuicyButton.Create(right,"Abrir",Gold,"B5651D",52,22,null,true,Ink);
   pillOpen.Clicked=()=>{if(!pillBusy)return;pillHide=true;ShowTab();};
   var hit=pill.GetComponent<Image>();
   if(!hit)hit=N.Image(pill,"Hit",new Color(1,1,1,0),0);
   U.Tap(hit,()=>{if(!pillBusy)return;pillHide=true;ShowTab();});
  }
  // Shows one announcement: slides down with an overshoot, plays its sound, holds for 6 s, slides back up.
  IEnumerator ShowPill(Notice n){
   pillBusy=true;pillHide=false;
   pillTitle.text=n.Title;pillSub.text=n.Sub;
   PaintAvatar(pillDisc,pillInitials,n.Avatar,n.Name);
   pillStars.SetActive(n.Kind==2);
   for(int i=0;i<pillStarImgs.Length;i++)DeliveryArt.SetStar(pillStarImgs[i],i<n.Stars);
   if(n.Kind==0)CheckoutDeliverySound.Play(CheckoutDeliverySound.Chime,.5f);
   else if(n.Kind==1)CheckoutDeliverySound.Play(CheckoutDeliverySound.Horn,.45f);
   else CheckoutDeliverySound.Play(CheckoutDeliverySound.Coin,.5f);
   yield return U.Move(pill,new Vector2(0,-18),.55f,true);
   if(n.Kind==2){Coins(pill,10);Confetti(pill,14);}
   if(n.Kind==2)for(int i=0;i<n.Stars;i++){
    yield return new WaitForSecondsRealtime(.16f);
    if(pillHide)break;
    DeliveryArt.SetStar(pillStarImgs[i],true);
    CheckoutDeliverySound.Play(CheckoutDeliverySound.Star(i),.4f);
   }
   for(float t=0;t<PillHold&&!pillHide&&!Blocked();t+=Time.unscaledDeltaTime)yield return null;
   yield return U.Move(pill,new Vector2(0,140),.35f);
   pillBusy=false;pillHide=false;
  }

  // ------------------------------------------------------------------ events: diff the order statuses
  void Detect(DeliveryState d,string sessionNow){
   if(d.orders==null)return;
   if(!primed||sessionNow!=session){
    // The first snapshot of a session is the baseline: nothing is announced for it.
    primed=true;session=sessionNow;seen.Clear();
    foreach(var o in d.orders)if(o!=null&&!string.IsNullOrEmpty(o.id))seen[o.id]=o.status;
    return;
   }
   bool looking=CheckoutSupplierShop.Instance&&CheckoutSupplierShop.Instance.DeliveryShown;
   foreach(var o in d.orders){
    if(o==null||string.IsNullOrEmpty(o.id))continue;
    seen.TryGetValue(o.id,out var prev);
    if(prev==o.status)continue;
    seen[o.id]=o.status;
    // The app is on screen: the cards already show it, with a burst instead of the pill.
    if(looking){
     if(o.status=="entregue"){Confetti(headerRect,22);Coins(headerRect,12);}
     continue;
    }
    string courierName=o.courier!=null&&!string.IsNullOrEmpty(o.courier.name)?o.courier.name:"O entregador";
    if(o.status=="oferta")
     notices.Enqueue(new Notice{Kind=0,Avatar=o.avatar,Name=o.customerName,Title="Novo pedido · "+o.customerName,Sub=o.neighborhood+" · "+Km(o.distanceKm)+" · ganho ~ "+Money(Mathf.RoundToInt(o.itemsValue+o.fee))});
    else if(o.status=="moto-na-porta")
     notices.Enqueue(new Notice{Kind=1,Avatar=SeedOf(o.courier!=null?o.courier.id:o.id),Name=courierName,Title="Motoboy na porta!",Sub=courierName+" chegou · entregue o pedido"});
    else if(o.status=="entregue")
     notices.Enqueue(new Notice{Kind=2,Avatar=o.avatar,Name=o.customerName,Stars=Mathf.Clamp(Mathf.RoundToInt(o.stars),0,5),Title="Pedido entregue · "+o.customerName,Sub="+"+Money(Mathf.RoundToInt(o.paid))+" moedas"});
   }
   // Forget the orders that left the list (the history keeps only a few).
   var ids=new HashSet<string>(d.orders.Where(o=>o!=null).Select(o=>o.id));
   foreach(var key in seen.Keys.ToList())if(!ids.Contains(key))seen.Remove(key);
  }

  // ------------------------------------------------------------------ frame
  // Each step logs its first exception once and keeps going, so one bad element never blanks the tab.
  void Report(Exception e,int where){
   if((reportedMask&(1<<where))!=0)return;
   reportedMask|=1<<where;
   Debug.LogException(e);
  }
  void Update(){
   if(!built){
    var shop=CheckoutSupplierShop.Instance;
    if(!shop||bridge==null)return;
    try{Build(shop.TabBody(CheckoutSupplierShop.TabDelivery));}catch(Exception e){Report(e,0);}
   }
   refreshAt-=Time.unscaledDeltaTime;
   if(refreshAt<=0){refreshAt=.25f;try{Refresh();}catch(Exception e){Report(e,1);}}
   try{Animate(CheckoutBridge.Now);}catch(Exception e){Report(e,2);}
   if(!pillBusy&&notices.Count>0&&!Blocked())StartCoroutine(ShowPill(notices.Dequeue()));
  }
  // Reads the store (4 Hz): events, the locked state, header numbers and the columns.
  void Refresh(){
   var s=bridge?.State;if(s==null||s.delivery==null)return;
   var d=s.delivery;
   Detect(d,s.session??"");
   bool unlocked=d.unlocked;
   root.gameObject.SetActive(unlocked);lockedNode.SetActive(!unlocked);
   if(!unlocked){lockSub.text="Libera no "+(string.IsNullOrEmpty(d.unlockEraName)?"próximo nível da loja":d.unlockEraName);return;}
   double now=CheckoutBridge.Now;
   SyncHeader(d);
   SyncOffers(d,now);
   SyncActives(d,now);
   SyncHistory(d,now);
   SyncMap(d,now);
  }
  // Header numbers. The XP bar and the meter change only when their value changes; nothing here moves layout.
  void SyncHeader(DeliveryState d){
   int rank=RankOf(d.delivered);
   if(rank!=lastRank){
    lastRank=rank;
    rankName.text=RankNames[rank];
    rankFill.sprite=DeliveryArt.Chunk(RankColors[rank],8);
   }
   float frac=1f,start=RankFrom[rank];
   if(rank<RankFrom.Length-1){float to=RankFrom[rank+1];frac=Mathf.Clamp01((d.delivered-start)/(to-start));rankXp.text=d.delivered+" / "+to;}
   else rankXp.text=d.delivered+" entregas";
   rankFill.fillAmount=frac;
   int lit=Mathf.Clamp(d.streak,0,streakSegments.Length);
   if(lit!=lastSegments){
    lastSegments=lit;
    for(int i=0;i<streakSegments.Length;i++)streakSegments[i].color=K.C(i<lit?"EF6A1F":"FFFFFF");
   }
   streakText.text=d.streak.ToString(CultureInfo.InvariantCulture);
   ratingText.text=d.rating.ToString("0.0",Br);
   motosText.text=d.active+"/"+d.slots;
  }
  // Per-frame motion: the flame breathes with the streak, the truck icon bobs by scale, and the cards and map animate.
  void Animate(double now){
   float t=Time.unscaledTime;
   float wave=.5f+.5f*Mathf.Sin(t*5f);
   int streak=Mathf.Clamp(lastSegments,0,10);
   float flameScale=.9f+.03f*streak+.04f*Mathf.Sin(t*9f)*(streak>0?1f:0f);
   if(streakFlame)streakFlame.rectTransform.localScale=Vector3.one*flameScale;
   if(motoIcon)motoIcon.rectTransform.localScale=Vector3.one*(1f+.04f*Mathf.Sin(t*4f));
   if(ratingStar)ratingStar.rectTransform.localScale=Vector3.one*(1f+.05f*wave);
   AnimateCards(now,t);
   AnimateMap(t);
  }
 }
}
