using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // Rede · Filiais (board style "street", Lucas 05/11: the cards on the city map were ugly, the texts small and everything
 // too close). The branches stand side by side as big shop cards across the whole window, like the shops of one avenue:
 // the store's art on a panel in its neighbourhood's colour (tile.look = "scene:RRGGBB") over a strip of pavement, its
 // state ribbon, the coins waiting and the timer on the panel; then the name, one line, the favourite goods, the level,
 // the shelves and the buttons (tile.actions, or tile.action). Spacing: 18 between cards, 16 inside, 12 between blocks.
 public partial class CheckoutDesktopHUD {
  const float StreetGap=18,StreetPad=16;
  RectTransform streetRoot;readonly List<StreetCard> streetCards=new List<StreetCard>();

  bool ApplyBoardStreet(DesktopBoard b){
   if(b.style!="street"){
    if(streetRoot&&streetRoot.gameObject.activeSelf){streetRoot.gameObject.SetActive(false);boardScroll.gameObject.SetActive(true);}
    return false;
   }
   boardScroll.gameObject.SetActive(false);
   if(boardMapPins)boardMapPins.gameObject.SetActive(false);
   boardBackdrop.enabled=false;
   if(!streetRoot)streetRoot=Stretch(N.Node("Street",boardGridArea),Vector2.zero,Vector2.zero);
   streetRoot.gameObject.SetActive(true);streetRoot.SetAsLastSibling();
   var tiles=b.tiles??new DesktopTile[0];
   while(streetCards.Count<tiles.Length)streetCards.Add(StreetCard.Create(this,streetRoot));
   var area=boardGridArea.rect;float aw=area.width>100?area.width:1500,ah=area.height>100?area.height:600;
   int n=Mathf.Max(1,tiles.Length);
   float cw=Mathf.Floor((aw-2*StreetPad-(n-1)*StreetGap)/n),ch=ah-2*StreetPad;
   // Every shop's panel has the same height: what the busiest card leaves (the words never run into the buttons).
   float sceneH=cw*.95f;foreach(var t in tiles)sceneH=Mathf.Min(sceneH,ch-StreetCard.Needs(t));sceneH=Mathf.Max(110,sceneH);
   for(int i=0;i<streetCards.Count;i++){
    var c=streetCards[i];bool on=i<tiles.Length;c.gameObject.SetActive(on);if(!on)continue;
    var r=(RectTransform)c.transform;r.anchorMin=r.anchorMax=r.pivot=new Vector2(0,1);r.sizeDelta=new Vector2(cw,ch);
    r.anchoredPosition=new Vector2(StreetPad+i*(cw+StreetGap),-StreetPad);
    c.Apply(tiles[i],cw,sceneH);
   }
   foreach(var sec in boardSections)sec.gameObject.SetActive(false);
   boardEmpty.gameObject.SetActive(false);boardMore.gameObject.SetActive(false);
   boardDetailPanel.SetActive(false);
   return true;
  }
  void TickStreet(double now,float t){
   if(!streetRoot||!streetRoot.gameObject.activeInHierarchy)return;
   foreach(var c in streetCards)if(c.gameObject.activeSelf)c.Tick(now,t);
  }

  sealed class StreetCard:MonoBehaviour {
   CheckoutDesktopHUD hud;DesktopTile data;
   RectTransform scene,art,ground,glow,ribbon,coins,timer,bar,barFill,buttons;
   Image edge,face,sceneImage,ribbonImage,groundImage,curb;
   TextMeshProUGUI ribbonText,coinsText,timerText,title,subtitle,likes,barText;
   BoardPips pips;readonly List<CheckoutDesktopButton> list=new List<CheckoutDesktopButton>();
   float fillShown=-1,fillTarget,coinsRow=-12;

   public static StreetCard Create(CheckoutDesktopHUD hud,Transform parent){
    var root=N.Node("Shop",parent);var c=root.gameObject.AddComponent<StreetCard>();c.hud=hud;
    c.edge=N.Image(root,"Edge",K.Border,24);Stretch(c.edge.rectTransform,new Vector2(0,-5),Vector2.zero);
    c.face=N.Image(root,"Face",K.C("FFF9EE"),24);Stretch(c.face.rectTransform,Vector2.zero,Vector2.zero);
    // The scene: a rounded panel (a mask) with the neighbourhood's colour, a soft light, the pavement and the store.
    c.sceneImage=N.Image(root,"Scene",Color.white,20);c.scene=c.sceneImage.rectTransform;
    c.scene.gameObject.AddComponent<Mask>().showMaskGraphic=true;
    var g=N.Image(c.scene,"Light",new Color(1,1,1,.75f),0);g.sprite=U.Glow();c.glow=g.rectTransform;
    c.groundImage=N.Image(c.scene,"Pavement",new Color(1,1,1,.55f),0);c.ground=c.groundImage.rectTransform;
    c.curb=N.Image(c.ground,"Curb",new Color(0,0,0,.08f),0);var cr=c.curb.rectTransform;cr.anchorMin=new Vector2(0,1);cr.anchorMax=Vector2.one;cr.pivot=new Vector2(.5f,1);cr.sizeDelta=new Vector2(0,5);cr.anchoredPosition=Vector2.zero;
    var a=N.Image(c.scene,"Store",Color.white,0);a.preserveAspect=true;c.art=a.rectTransform;
    c.ribbonImage=Pill(c.scene,"Ribbon",K.C("8A5A2B"),out c.ribbonText,15,K.Label);c.ribbon=c.ribbonImage.rectTransform;c.ribbonText.characterSpacing=2;
    c.ribbon.anchorMin=c.ribbon.anchorMax=c.ribbon.pivot=new Vector2(0,1);c.ribbon.anchoredPosition=new Vector2(12,-12);
    // Coins waiting: a gold pill with a coin, top right.
    var coin=N.Image(c.scene,"Coins",K.C("F2B03D"),16);c.coins=coin.rectTransform;c.coins.anchorMin=c.coins.anchorMax=c.coins.pivot=Vector2.one;c.coins.anchoredPosition=new Vector2(-12,-12);
    var ci=N.Image(coin.transform,"Coin",Color.white,0);ci.sprite=K.Icon("Icons/coin");ci.preserveAspect=true;var cir=ci.rectTransform;cir.anchorMin=cir.anchorMax=cir.pivot=new Vector2(0,.5f);cir.sizeDelta=new Vector2(24,24);cir.anchoredPosition=new Vector2(8,0);
    c.coinsText=N.Text(coin.transform,"Text",K.Number,18,K.Ink);c.coinsText.textWrappingMode=TextWrappingModes.NoWrap;c.coinsText.alignment=TextAlignmentOptions.MidlineLeft;Stretch(c.coinsText.rectTransform,new Vector2(38,0),new Vector2(-10,0));
    // The timer of a works or of a cargo on the road, at the foot of the scene.
    var tm=N.Image(c.scene,"Timer",new Color(.11f,.17f,.31f,.92f),14);c.timer=tm.rectTransform;c.timer.anchorMin=c.timer.anchorMax=c.timer.pivot=new Vector2(.5f,0);c.timer.anchoredPosition=new Vector2(0,12);
    c.timerText=N.Text(tm.transform,"Text",K.Number,18,Color.white);c.timerText.alignment=TextAlignmentOptions.Center;c.timerText.textWrappingMode=TextWrappingModes.NoWrap;Stretch(c.timerText.rectTransform,new Vector2(10,0),new Vector2(-10,0));
    c.title=N.Text(root,"Title",K.Headline,24,K.Ink);c.title.alignment=TextAlignmentOptions.Center;c.title.textWrappingMode=TextWrappingModes.NoWrap;c.title.enableAutoSizing=true;c.title.fontSizeMin=16;c.title.fontSizeMax=24;
    c.subtitle=N.Text(root,"Line",K.Body,17,K.Muted);c.subtitle.alignment=TextAlignmentOptions.Center;c.subtitle.textWrappingMode=TextWrappingModes.NoWrap;c.subtitle.enableAutoSizing=true;c.subtitle.fontSizeMin=12;c.subtitle.fontSizeMax=17;
    c.likes=N.Text(root,"Likes",K.Body,15,K.C("A0805E"));c.likes.alignment=TextAlignmentOptions.Center;c.likes.textWrappingMode=TextWrappingModes.NoWrap;c.likes.enableAutoSizing=true;c.likes.fontSizeMin=11;c.likes.fontSizeMax=15;
    c.pips=new BoardPips(root,15);
    var track=N.Image(root,"Shelves",K.C("EADBC4"),13);c.bar=track.rectTransform;
    var fill=N.Image(track.transform,"Fill",K.C("4F9A2E"),13);c.barFill=fill.rectTransform;c.barFill.anchorMin=Vector2.zero;c.barFill.anchorMax=new Vector2(0,1);c.barFill.offsetMin=c.barFill.offsetMax=Vector2.zero;
    var gloss=N.Image(fill.transform,"Gloss",new Color(1,1,1,.28f),9);var gr=gloss.rectTransform;gr.anchorMin=new Vector2(0,.55f);gr.anchorMax=Vector2.one;gr.offsetMin=new Vector2(3,0);gr.offsetMax=new Vector2(-3,-2);
    c.barText=N.Text(track.transform,"Text",K.Label,14,Color.white);c.barText.alignment=TextAlignmentOptions.Center;c.barText.textWrappingMode=TextWrappingModes.NoWrap;Stretch(c.barText.rectTransform,Vector2.zero,Vector2.zero);
    c.barText.outlineWidth=.18f;c.barText.outlineColor=new Color32(60,40,20,140);
    c.buttons=N.Node("Buttons",root);var col=N.Column(c.buttons.gameObject,10);col.childControlHeight=true;col.childForceExpandHeight=false;
    return c;
   }

   static Color Scene(string look){
    if(!string.IsNullOrEmpty(look)&&look.StartsWith("scene:")&&ColorUtility.TryParseHtmlString("#"+look.Substring(6),out var c))return c;
    return K.C("E6EEF4");
   }

   const float ButtonH=46,ButtonGap=10,TitleH=30,LineH=26,LikesH=22,BarH=26,Gap=10;
   static DesktopButton[] Actions(DesktopTile t)=>t.actions!=null&&t.actions.Length>0?t.actions:t.action!=null&&!string.IsNullOrEmpty(t.action.label)?new[]{t.action}:new DesktopButton[0];
   static bool HasLikes(DesktopTile t)=>t.lines!=null&&t.lines.Length>0&&!string.IsNullOrEmpty(t.lines[0]);
   /// <summary>The card's height without its scene: margins, the words, the shelves and the buttons.</summary>
   public static float Needs(DesktopTile t){
    int n=Actions(t).Length;
    return 12+18+TitleH+Gap+LineH+(HasLikes(t)?Gap+LikesH:0)+20+n*ButtonH+Mathf.Max(0,n-1)*ButtonGap+StreetPad+4;
   }

   public void Apply(DesktopTile t,float cw,float sceneH){
    bool changed=data==null||data.id!=t.id;data=t;
    var actions=Actions(t);
    float buttonsH=actions.Length*ButtonH+Mathf.Max(0,actions.Length-1)*ButtonGap;
    bool hasBar=t.fill>=0,hasLikes=HasLikes(t);
    // From the foot up: the buttons and the shelves; from the top down: the scene, the name, the line, the likes.
    float y=StreetPad+4;
    Place(buttons,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,y),new Vector2(-2*StreetPad,buttonsH));y+=buttonsH+(actions.Length>0?14:0);
    // (the shelves sit on the scene's pavement, so the card keeps room for its words)
    bar.gameObject.SetActive(hasBar);
    if(hasBar){if(bar.parent!=scene)bar.SetParent(scene,false);bar.SetAsLastSibling();Place(bar,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,12),new Vector2(-24,BarH));}
    // (the level is the ribbon's NÍVEL n: no diamonds under the name, they ran into the words)
    pips.gameObject.SetActive(false);
    Place(scene,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-12),new Vector2(-24,sceneH));
    sceneImage.color=Scene(t.look);
    float top=-12-sceneH-18;
    Place((RectTransform)title.transform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,top),new Vector2(-2*StreetPad,TitleH));top-=TitleH+Gap;
    Place((RectTransform)subtitle.transform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,top),new Vector2(-2*StreetPad,LineH));top-=LineH+Gap;
    Place((RectTransform)likes.transform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,top),new Vector2(-2*StreetPad,LikesH));
    // The scene's pieces scale with it: pavement a third, the store as big as it fits over it.
    float sw=cw-24;
    Place(ground,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),Vector2.zero,new Vector2(0,sceneH*.3f));
    // (the store stands on the pavement; with the shelves bar there it stands just above the bar)
    float foot=t.fill>=0?12+BarH+2:sceneH*.06f;
    float artSize=Mathf.Min((sceneH-foot)*.96f,sw*.86f);
    Place(art,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(0,foot),new Vector2(artSize,artSize));
    Place(glow,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(0,sceneH*.08f),new Vector2(sw*1.05f,sceneH*1.05f));
    bool locked=t.state=="locked";
    var sprite=K.Icon(t.icon);art.GetComponent<Image>().sprite=sprite;art.gameObject.SetActive(sprite);
    title.text=K.Clean(t.title);subtitle.text=K.Clean(t.subtitle);subtitle.gameObject.SetActive(!string.IsNullOrEmpty(t.subtitle));
    likes.gameObject.SetActive(hasLikes);if(hasLikes)likes.text=K.Clean(t.lines[0]);
    bool hasRibbon=!string.IsNullOrEmpty(t.sticker);ribbon.gameObject.SetActive(hasRibbon);
    if(hasRibbon){var label=K.Clean(t.sticker);ribbonText.text=label;ribbonImage.color=ToneStrong(string.IsNullOrEmpty(t.tone)?"":t.tone);ribbon.sizeDelta=new Vector2(PillWidth(ribbonText,label,70)+8,32);}
    bool hasCoins=!string.IsNullOrEmpty(t.badge);coins.gameObject.SetActive(hasCoins);
    if(hasCoins){var label=K.Clean(t.badge);coinsText.text=label;coins.sizeDelta=new Vector2(coinsText.GetPreferredValues(label).x+52,36);}
    timer.gameObject.SetActive(t.timerEnd>0);
    // (the timer at the foot's middle; with coins waiting on the right it moves to the left corner)
    timer.anchorMin=timer.anchorMax=timer.pivot=new Vector2(.5f,0);timer.anchoredPosition=new Vector2(0,hasBar?12+BarH+8:12);
    // coins top right; under the ribbon's row when a long ribbon (PRATELEIRAS VAZIAS) leaves no room beside it
    coinsRow=hasRibbon&&hasCoins&&ribbon.sizeDelta.x+coins.sizeDelta.x+36>cw-24?-12-32-8:-12;
    if(hasBar){fillTarget=Mathf.Clamp01(t.fill);if(changed||fillShown<0)fillShown=fillTarget;barText.text=K.Clean(t.fillText);
     barFill.GetComponent<Image>().color=fillTarget<.25f?ToneStrong("danger"):fillTarget<.5f?ToneStrong("warning"):ToneStrong("success");}
    face.color=t.tone=="danger"?K.C("FFF1EB"):K.C("FFF9EE");edge.color=t.tone=="danger"?K.C("E9A48F"):K.Border;
    while(list.Count<actions.Length){var x=CheckoutDesktopButton.Create(buttons,ButtonH,15,14);x.Clicked=hud.BoardPress;list.Add(x);}
    for(int i=0;i<list.Count;i++){bool on=i<actions.Length;list[i].gameObject.SetActive(on);if(on){list[i].Apply(actions[i]);list[i].Shrink(11);}}
    art.GetComponent<Image>().color=locked?new Color(1,1,1,.6f):Color.white;
   }

   public void Tick(double now,float t){
    if(data==null)return;
    if(data.timerEnd>0){double left=data.timerEnd-now;var text=left>0?Clock(left):"Pronto!";timerText.text=text;timer.sizeDelta=new Vector2(Mathf.Max(92,timerText.GetPreferredValues(text).x+28),32);}
    if(fillShown>=0){fillShown=Mathf.MoveTowards(fillShown,fillTarget,Time.unscaledDeltaTime*.9f);barFill.anchorMax=new Vector2(Mathf.Max(fillShown>0?.05f:0,fillShown),1);}
    // coins waiting bob a little, so the eye goes to them
    if(coins.gameObject.activeSelf)coins.anchoredPosition=new Vector2(-12,coinsRow-Mathf.Abs(Mathf.Sin(t*3f+transform.GetSiblingIndex()))*3);
   }
  }
 }
}
