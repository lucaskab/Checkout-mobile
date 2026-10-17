using System;
using System.Globalization;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // The Delivery app looks like an app (Lucas 17/10: "quero que pareça mais como um app, porque atualmente não parece"):
 // a tablet held in landscape, with a status bar (clock, signal, battery), the app bar (the app's logo and name, the
 // store online/closed, the rating and the player's rank avatar), one page at a time and a bottom tab bar with badges:
 //  - Pedidos: the new orders in a sheet on the left, the live city map on the right (like a courier app);
 //  - Entregas: the orders in progress, same map;
 //  - Perfil: rank, streak, rating and motoboys, then the last deliveries.
 public sealed partial class CheckoutDeliveryApp {
  const string Bezel="17191C";
  static readonly string[] TabTitles={"Pedidos","Entregas","Perfil"};
  RectTransform pagesHost,offersPage,activePage,profilePage,mapColumn;
  TextMeshProUGUI clockText,statusText,barRating;
  Image barAvatarRing,statusDot;
  readonly Image[] tabIcons=new Image[3],tabPills=new Image[3];
  readonly TextMeshProUGUI[] tabLabels=new TextMeshProUGUI[3],tabBadges=new TextMeshProUGUI[3];
  readonly GameObject[] tabBadgeNodes=new GameObject[3];
  int tab=-1;bool wasShown;

  void BuildShell(RectTransform parent){
   // the device: a dark bezel with rounded corners and the screen inside it
   var device=Panel(parent,"Device",Bezel,18);U.Stretch(device.rectTransform,Vector2.zero,Vector2.one);
   var screen=Panel(device.transform,"Screen",ScreenTone,14);U.Stretch(screen.rectTransform,Vector2.zero,Vector2.one,new Vector2(12,14),new Vector2(-12,-12));
   screen.gameObject.AddComponent<RectMask2D>();
   var col=N.Column(screen.gameObject,0);col.childAlignment=TextAnchor.UpperCenter;
   BuildStatusBar(screen.rectTransform);
   BuildAppBar(screen.rectTransform);
   // landscape phone: the tabs are a navigation rail on the left (a bottom bar ate the height the cards need)
   var body=N.Node("Body",screen.rectTransform);N.Row(body.gameObject,0);var bodySize=Pref(body.gameObject,-1,-1);bodySize.flexibleHeight=1;
   BuildTabBar(body);
   // pages: a sheet on the left (orders / in progress) and the map on the right; the profile covers both
   pagesHost=N.Node("Pages",body);var pagesSize=Pref(pagesHost.gameObject,-1,-1);pagesSize.flexibleHeight=1;pagesSize.flexibleWidth=1;
   var row=N.Node("Split",pagesHost);U.Stretch(row,Vector2.zero,Vector2.one,new Vector2(14,10),new Vector2(-14,-8));
   N.Row(row.gameObject,14).childAlignment=TextAnchor.UpperLeft;
   var sheet=N.Node("Sheet",row);N.Row(sheet.gameObject,0);Pref(sheet.gameObject,-1,-1).flexibleWidth=46;
   BuildOffersColumn(sheet,1);offersPage=(RectTransform)sheet.GetChild(sheet.childCount-1);
   BuildActiveColumn(sheet,1);activePage=(RectTransform)sheet.GetChild(sheet.childCount-1);
   mapColumn=N.Node("MapColumn",row);N.Column(mapColumn.gameObject,0);Pref(mapColumn.gameObject,-1,-1).flexibleWidth=54;
   BuildMap(mapColumn);
   profilePage=N.Node("Profile",pagesHost);U.Stretch(profilePage,Vector2.zero,Vector2.one,new Vector2(14,10),new Vector2(-14,-8));
   N.Column(profilePage.gameObject,12);
   BuildHeader(profilePage);
   BuildHistory(profilePage);
   SelectTab(0);
  }

  // ------------------------------------------------------------------ status bar: time, signal, wifi, battery
  void BuildStatusBar(RectTransform screen){
   var bar=N.Node("StatusBar",screen);N.Row(bar.gameObject,8,new RectOffset(26,24,4,0)).childAlignment=TextAnchor.MiddleLeft;Pref(bar.gameObject,-1,30);
   clockText=U.Label(bar,"Clock",K.Number,17,Ink,TextAlignmentOptions.Left);Pref(clockText.gameObject,90,-1);
   var gap=N.Node("Gap",bar);Pref(gap.gameObject,-1,-1).flexibleWidth=1;
   // signal: four bars of growing height
   var signal=N.Node("Signal",bar);Pref(signal.gameObject,26,16);
   for(int i=0;i<4;i++){var b=N.Image(signal,"Bar",K.C(Ink),0);b.sprite=K.Rounded(2);b.type=Image.Type.Sliced;b.raycastTarget=false;
    U.At(b.rectTransform,new Vector2(0,0),new Vector2(4.5f,5+i*3.5f),new Vector2(2.5f+i*6.5f,(5+i*3.5f)*.5f));}
   // wifi: three stacked arcs drawn as shrinking rings clipped to a wedge would be overkill: three dots of growing width
   var wifi=N.Node("Wifi",bar);Pref(wifi.gameObject,22,16);
   for(int i=0;i<3;i++){var w=N.Image(wifi,"Arc",K.C(Ink),0);w.sprite=K.Rounded(2);w.type=Image.Type.Sliced;w.raycastTarget=false;
    U.At(w.rectTransform,new Vector2(.5f,0),new Vector2(6+i*7,3),new Vector2(0,2+i*5));}
   // battery: outline, fill, cap
   var bat=N.Node("Battery",bar);Pref(bat.gameObject,34,16);
   var shell=N.Image(bat,"Shell",K.C(Muted),0);shell.sprite=K.Rounded(4);shell.type=Image.Type.Sliced;shell.raycastTarget=false;U.At(shell.rectTransform,new Vector2(0,.5f),new Vector2(28,15),new Vector2(14,0));
   var inner=N.Image(shell.transform,"Inside",K.C(ScreenTone),0);inner.sprite=K.Rounded(3);inner.type=Image.Type.Sliced;inner.raycastTarget=false;U.Stretch(inner.rectTransform,Vector2.zero,Vector2.one,new Vector2(2,2),new Vector2(-2,-2));
   var level=N.Image(shell.transform,"Level",K.C(Green),0);level.sprite=K.Rounded(2);level.type=Image.Type.Sliced;level.raycastTarget=false;U.Stretch(level.rectTransform,Vector2.zero,new Vector2(.82f,1),new Vector2(3,3),new Vector2(0,-3));
   var cap=N.Image(bat,"Cap",K.C(Muted),0);cap.raycastTarget=false;U.At(cap.rectTransform,new Vector2(0,.5f),new Vector2(3,7),new Vector2(30,0));
  }

  // ------------------------------------------------------------------ app bar: logo, name, online, rating, avatar
  void BuildAppBar(RectTransform screen){
   var bar=N.Image(screen,"AppBar",K.C(Paper),0);N.Row(bar.gameObject,14,new RectOffset(20,20,6,6)).childAlignment=TextAnchor.MiddleLeft;Pref(bar.gameObject,-1,66);
   // logo: the brand disc with the moto
   var logo=N.Node("Logo",bar.transform);Pref(logo.gameObject,50,50);
   var disc=N.Image(logo,"Disc",Color.white,0);disc.sprite=DeliveryArt.FlatDisc(Blue);disc.raycastTarget=false;U.Stretch(disc.rectTransform,Vector2.zero,Vector2.one);
   var moto=N.Image(logo,"Moto",Color.white,0);moto.sprite=DeliveryArt.Moto;moto.preserveAspect=true;moto.raycastTarget=false;U.Stretch(moto.rectTransform,Vector2.zero,Vector2.one,new Vector2(8,8),new Vector2(-8,-8));
   var names=N.Node("Names",bar.transform);N.Column(names.gameObject,0);Pref(names.gameObject,-1,-1).flexibleWidth=1;
   U.Label(names,"App",K.Headline,24,Ink,TextAlignmentOptions.Left).text="Entregas da loja";
   var status=N.Node("Status",names);N.Row(status.gameObject,6).childAlignment=TextAnchor.MiddleLeft;Pref(status.gameObject,-1,24);
   statusDot=N.Image(status,"Dot",K.C(Green),0);statusDot.sprite=DeliveryArt.Circle;statusDot.raycastTarget=false;Pref(statusDot.gameObject,12,12);
   statusText=U.Label(status,"Text",K.Body,17,Muted,TextAlignmentOptions.Left);statusText.overflowMode=TextOverflowModes.Overflow;   // an ellipsis drops the whole line when it is a hair too shortPref(statusText.gameObject,-1,-1).flexibleWidth=1;
   // rating chip and the player's avatar with the rank colour around it
   var rate=Panel(bar.transform,"Rating",ScreenTone,14);N.Row(rate.gameObject,6,new RectOffset(12,14,4,4)).childAlignment=TextAnchor.MiddleCenter;Pref(rate.gameObject,-1,42);
   SpriteImg(rate.transform,"Star",DeliveryArt.StarOn,Color.white,26,26);
   barRating=U.Label(rate.transform,"Value",K.Number,20,Ink);
   var me=N.Node("Me",bar.transform);Pref(me.gameObject,48,48);
   barAvatarRing=N.Image(me,"Ring",K.C(RankColors[0]),0);barAvatarRing.sprite=DeliveryArt.Circle;barAvatarRing.raycastTarget=false;U.Stretch(barAvatarRing.rectTransform,Vector2.zero,Vector2.one);
   var face=N.Image(me,"Face",Color.white,0);face.sprite=DeliveryArt.FlatDisc("2B3540");face.raycastTarget=false;U.Stretch(face.rectTransform,Vector2.zero,Vector2.one,new Vector2(4,4),new Vector2(-4,-4));
   var medal=N.Image(me,"Medal",Color.white,0);medal.sprite=K.Icon("Icons/medal");medal.preserveAspect=true;medal.raycastTarget=false;U.Stretch(medal.rectTransform,Vector2.zero,Vector2.one,new Vector2(11,11),new Vector2(-11,-11));
   var tap=me.gameObject.AddComponent<Image>();tap.color=new Color(1,1,1,0);U.Tap(tap,()=>SelectTab(2));
   // a hairline under the bar
   var line=N.Image(screen,"BarLine",K.C(EmptyTone),0);line.raycastTarget=false;Pref(line.gameObject,-1,2);
  }

  // ------------------------------------------------------------------ tab bar
  void BuildTabBar(RectTransform body){
   var rail=N.Image(body,"TabRail",K.C(Paper),0);var col=N.Column(rail.gameObject,6,new RectOffset(6,6,14,14));col.childAlignment=TextAnchor.UpperCenter;
   var railSize=Pref(rail.gameObject,104,-1);railSize.minWidth=104;railSize.flexibleWidth=0;railSize.flexibleHeight=1;   // fixed: the column would otherwise share the width with the pages
   var line=N.Image(body,"TabLine",K.C(EmptyTone),0);line.raycastTarget=false;var lineSize=Pref(line.gameObject,2,-1);lineSize.flexibleWidth=0;lineSize.flexibleHeight=1;
   Sprite[] icons={K.Icon("Icons/smartphone"),DeliveryArt.Moto,K.Icon("Icons/medal")};
   for(int i=0;i<3;i++){
    int index=i;
    var cell=N.Node("Tab"+i,rail.transform);Pref(cell.gameObject,-1,86);
    var hit=cell.gameObject.AddComponent<Image>();hit.color=new Color(1,1,1,0);U.Tap(hit,()=>{SelectTab(index);CheckoutDeliverySound.Play(CheckoutDeliverySound.Accept,.15f);});
    var pillImg=N.Image(cell,"Pill",K.C(Blue),0);pillImg.sprite=K.Rounded(16);pillImg.type=Image.Type.Sliced;pillImg.raycastTarget=false;
    U.At(pillImg.rectTransform,new Vector2(.5f,1),new Vector2(68,36),new Vector2(0,-24));tabPills[i]=pillImg;
    var icon=N.Image(cell,"Icon",Color.white,0);icon.sprite=icons[i];icon.preserveAspect=true;icon.raycastTarget=false;
    U.At(icon.rectTransform,new Vector2(.5f,1),new Vector2(30,30),new Vector2(0,-24));tabIcons[i]=icon;
    var label=U.Label(cell,"Label",K.Headline,16,Muted);U.At(label.rectTransform,new Vector2(.5f,0),new Vector2(96,24),new Vector2(0,16));label.text=TabTitles[i];tabLabels[i]=label;
    var badge=Panel(cell,"Badge",Red,11);U.At(badge.rectTransform,new Vector2(.5f,1),new Vector2(30,24),new Vector2(28,-10));
    var count=U.Label(badge.transform,"Count",K.Number,15,"FFFFFF");U.Stretch(count.rectTransform,Vector2.zero,Vector2.one);
    tabBadges[i]=count;tabBadgeNodes[i]=badge.gameObject;badge.gameObject.SetActive(false);
   }
  }

  /// <summary>QA: shows one page of the app (0 orders, 1 in progress, 2 profile).</summary>
  public void QaTab(int index)=>SelectTab(index);
  /// <summary>QA: the status line under the app's name, with its drawn size.</summary>
  public string QaStatus=>statusText?$"'{statusText.text}' {statusText.rectTransform.rect.width:0}x{statusText.rectTransform.rect.height:0} active={statusText.gameObject.activeInHierarchy} alpha={statusText.color.a:0.00}":"none";

  void SelectTab(int index){
   if(index==tab)return;
   tab=index;
   bool profile=index==2;
   if(offersPage)offersPage.gameObject.SetActive(index==0);
   if(activePage)activePage.gameObject.SetActive(index==1);
   var split=pagesHost?pagesHost.Find("Split"):null;if(split)split.gameObject.SetActive(!profile);
   if(profilePage)profilePage.gameObject.SetActive(profile);
   for(int i=0;i<3;i++){
    bool on=i==index;
    if(tabPills[i])tabPills[i].color=on?K.C("FDE3DB"):new Color(1,1,1,0);
    if(tabIcons[i])tabIcons[i].color=on?Color.white:new Color(1,1,1,.55f);
    if(tabLabels[i]){tabLabels[i].color=K.C(on?Blue:Muted);}
   }
  }

  // ------------------------------------------------------------------ the last deliveries (profile page)
  void BuildHistory(RectTransform parent){
   var histHead=N.Node("HistoryHead",parent);N.Row(histHead.gameObject,10,new RectOffset(6,6,0,0)).childAlignment=TextAnchor.MiddleLeft;Pref(histHead.gameObject,-1,40);
   U.Label(histHead,"Title",K.Headline,24,Ink,TextAlignmentOptions.Left).text="Últimas entregas";
   var histView=ScrollArea(parent,"HistoryView",out historyContent);
   Pref(histView.gameObject,-1,-1).flexibleHeight=1;
   N.Column(historyContent.gameObject,8,new RectOffset(0,6,2,6));Fit(historyContent);
   historyEmpty=Empty(historyContent,K.Icon("Icons/medal"),"Sem entregas ainda","As entregas feitas aparecem aqui, com estrelas e gorjeta.",200);
  }

  // ------------------------------------------------------------------ per refresh: clock, status, badges, the open tab
  void SyncShell(DeliveryState d){
   var now=DateTime.Now;
   if(clockText){var t=now.ToString("HH:mm",CultureInfo.InvariantCulture);if(clockText.text!=t)clockText.text=t;}
   var s=bridge?.State;bool open=s!=null&&s.isOpen;
   if(statusText){string want=CheckoutI18n.T(open?"Loja aberta · recebendo pedidos":"Loja fechada · sem pedidos novos");if(statusText.text!=want)statusText.text=want;}
   if(statusDot)statusDot.color=K.C(open?Green:"A0A6AE");
   if(barRating)barRating.text=d.rating.ToString("0.0",Br);
   if(barAvatarRing)barAvatarRing.color=K.C(RankColors[RankOf(d.delivered)]);
   int offersN=0,activeN=0;
   if(d.orders!=null)foreach(var o in d.orders){if(o==null)continue;if(o.status=="oferta")offersN++;else if(StageOf(o.status)>0)activeN++;}
   Badge(0,offersN);Badge(1,activeN);Badge(2,0);
   // opening the app lands on the page with something to do
   bool shown=CheckoutSupplierShop.Instance&&CheckoutSupplierShop.Instance.DeliveryShown;
   if(shown&&!wasShown)SelectTab(offersN>0||activeN==0?0:1);
   wasShown=shown;
  }
  void Badge(int i,int n){
   if(tabBadgeNodes[i]==null)return;
   bool on=n>0;if(tabBadgeNodes[i].activeSelf!=on)tabBadgeNodes[i].SetActive(on);
   if(on){var t=n>9?"9+":n.ToString(CultureInfo.InvariantCulture);if(tabBadges[i].text!=t)tabBadges[i].text=t;}
  }
 }
}
