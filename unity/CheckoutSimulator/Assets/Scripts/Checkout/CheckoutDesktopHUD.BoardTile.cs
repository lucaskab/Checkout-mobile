using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 public partial class CheckoutDesktopHUD {
  static RectTransform Place(RectTransform r,Vector2 anchorMin,Vector2 anchorMax,Vector2 pivot,Vector2 position,Vector2 size){
   r.anchorMin=anchorMin;r.anchorMax=anchorMax;r.pivot=pivot;r.anchoredPosition=position;r.sizeDelta=size;return r;
  }
  static Image Pill(Transform parent,string name,Color color,out TextMeshProUGUI text,float fontSize,TMP_FontAsset font){
   var image=N.Image(parent,name,color,12);text=N.Text(image.transform,"Text",font,fontSize,Color.white);text.alignment=TextAlignmentOptions.Center;
   text.textWrappingMode=TextWrappingModes.NoWrap;Stretch(text.rectTransform,new Vector2(8,0),new Vector2(-8,0));return image;
  }
  static float PillWidth(TextMeshProUGUI text,string value,float min){return Mathf.Max(min,text.GetPreferredValues(value).x+20);}
  // Social v1 tiles: up to three chips (icon + text) under the title, in rows of this height.
  const int ChipRows=3;const float ChipH=26;
  // Compact cards (a board with chips): the chips start this far from the face's top; the card is as tall as its rows.
  const float CompactTop=166;
  static readonly Color PortraitNavy=K.C("1D2B4F"),PortraitGold=K.C("E3B54A");
  /// <summary>A player's face ("avatar:…", or a portrait frame): drawn round, clipped inside a gold rim, wherever it shows.</summary>
  static bool IsFace(DesktopTile t)=>t.frame=="portrait"||(t.icon??"").StartsWith("avatar:",System.StringComparison.Ordinal);

  // A small chip of a tile: icon + text on a soft pill (likes, "2 obras para ajudar", "pede 6× Tomate").
  sealed class TileChip {
   public RectTransform rect;Image back,icon;TextMeshProUGUI text;
   public static TileChip Create(Transform parent){
    var c=new TileChip();var img=N.Image(parent,"Chip",K.C("F3E6CC"),11);c.back=img;c.rect=img.rectTransform;
    var le=img.gameObject.AddComponent<LayoutElement>();le.preferredHeight=ChipH-4;
    var row=N.Row(img.gameObject,5,new RectOffset(6,9,2,2));row.childAlignment=TextAnchor.MiddleCenter;
    c.icon=N.Image(img.transform,"Icon",Color.white,0);c.icon.preserveAspect=true;var il=c.icon.gameObject.AddComponent<LayoutElement>();il.preferredWidth=il.preferredHeight=18;
    c.text=N.Text(img.transform,"Text",K.Label,12,K.Ink);c.text.textWrappingMode=TextWrappingModes.NoWrap;c.text.overflowMode=TextOverflowModes.Ellipsis;
    return c;
   }
   public void Apply(DesktopStat s){
    var sprite=K.Icon(s.icon);icon.sprite=sprite;icon.gameObject.SetActive(sprite);text.text=K.Clean(s.value);
    back.color=string.IsNullOrEmpty(s.tone)?K.C("F3E6CC"):ToneFace(s.tone);text.color=string.IsNullOrEmpty(s.tone)?K.Ink:ToneStrong(s.tone);
   }
  }

  // Small diamonds for levels/stars: maxStars above 5 is drawn as 5 diamonds worth 2 points each.
  class BoardPips {
   readonly List<Image> pips=new List<Image>();RectTransform row;
   public GameObject gameObject=>row.gameObject;
   public BoardPips(Transform parent,float size){
    row=N.Node("Pips",parent);var h=N.Row(row.gameObject,(int)(size*.35f));h.childAlignment=TextAnchor.MiddleCenter;
    for(int i=0;i<5;i++){var pip=N.Image(row,"Pip",Color.white,0);pip.sprite=K.Rounded(3);pip.type=Image.Type.Sliced;var le=pip.gameObject.AddComponent<LayoutElement>();le.preferredWidth=le.preferredHeight=size;pip.rectTransform.localRotation=Quaternion.Euler(0,0,45);pips.Add(pip);}
   }
   public RectTransform Rect=>row;
   public void Apply(int stars,int max){
    bool on=max>0;row.gameObject.SetActive(on);if(!on)return;
    int count=Mathf.Min(5,max);float value=max>5?stars*5f/max:stars;
    for(int i=0;i<pips.Count;i++){
     pips[i].gameObject.SetActive(i<count);
     pips[i].color=value>=i+1?K.C("F2B03D"):value>=i+.5f?new Color(.95f,.69f,.24f,.55f):K.C("D9CBB4");
    }
   }
  }

  // One tile of a board (card in the grid or a wide row).
  class BoardTileUi:MonoBehaviour,IPointerClickHandler {
   CheckoutDesktopHUD hud;public string Id;DesktopTile data;bool rows;
   RectTransform rect,circle,titleRect,subtitleRect,barRect,buttonRect,ribbonRect,badgeRect,timerRect;
   Image glow,edge,face,circleImage,icon,lockIcon,stamp,ribbon,badge,timer,barFill;TextMeshProUGUI title,subtitle,ribbonText,badgeText,timerText,barText;
   BoardPips pips;CheckoutDesktopButton button;bool selected;float fillShown=-1,fillTarget;string layoutMode;
   Image ring,cornerBack,cornerIcon;RectTransform chipsBox;readonly List<TileChip> chips=new List<TileChip>();CheckoutDesktopButton alt;
   string frame;float wobblePhase;Image clip,rim;bool isFace;
   // Rankings v1 rows (frame "rank"): the place on a medal disc, the flag and the number at the row's end.
   Image rankDisc,flagImage,flagEdge;TextMeshProUGUI rankText,valueText,valueLabelText;

   public static BoardTileUi Create(CheckoutDesktopHUD hud,Transform parent){
    var root=N.Node("Tile",parent);var ui=root.gameObject.AddComponent<BoardTileUi>();ui.hud=hud;ui.rect=root;
    ui.glow=N.Image(root,"Glow",new Color(1,.85f,.3f,0),0);ui.glow.sprite=U.Glow();Stretch(ui.glow.rectTransform,new Vector2(-26,-26),new Vector2(26,26));
    ui.edge=N.Image(root,"Edge",K.Border,18);ui.edge.raycastTarget=true;Stretch(ui.edge.rectTransform,Vector2.zero,Vector2.zero);
    ui.face=N.Image(root,"Face",K.Cream,16);Stretch(ui.face.rectTransform,new Vector2(3,7),new Vector2(-3,-3));
    var f=ui.face.transform;
    // (a friend's face sits in a gold ring, the plate navy)
    ui.ring=N.Image(f,"Ring",PortraitGold,0);ui.ring.sprite=K.Disc();
    ui.circleImage=N.Image(f,"Circle",Color.white,0);ui.circleImage.sprite=K.Rounded(56);ui.circleImage.type=Image.Type.Sliced;ui.circle=ui.circleImage.rectTransform;
    // (a portrait: the picture clipped to the plate's circle, the gold rim drawn over its edge; the stamp and the stage badge on top)
    ui.clip=K.RoundClip(ui.circle,"Clip");K.SetRound(ui.clip,false);
    ui.icon=N.Image(ui.clip.transform,"Icon",Color.white,0);ui.icon.preserveAspect=true;Stretch(ui.icon.rectTransform,new Vector2(10,10),new Vector2(-10,-10));
    ui.rim=N.Image(ui.circle,"Rim",PortraitGold,0);ui.rim.gameObject.SetActive(false);
    ui.lockIcon=N.Image(ui.circle,"Lock",Color.white,0);ui.lockIcon.sprite=K.Icon("Icons/lock");ui.lockIcon.preserveAspect=true;Place(ui.lockIcon.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(46,46));
    ui.stamp=N.Image(ui.circle,"Stamp",Color.white,0);ui.stamp.sprite=K.Icon("Icons/success");ui.stamp.preserveAspect=true;Place(ui.stamp.rectTransform,new Vector2(1,0),new Vector2(1,0),new Vector2(1,0),new Vector2(10,-6),new Vector2(48,48));
    ui.title=N.Text(f,"Title",K.Headline,17,K.Ink);ui.title.enableAutoSizing=true;ui.title.fontSizeMin=12;ui.title.fontSizeMax=17;ui.title.overflowMode=TextOverflowModes.Ellipsis;ui.titleRect=ui.title.rectTransform;
    ui.subtitle=N.Text(f,"Subtitle",K.Body,12,K.Muted);ui.subtitle.textWrappingMode=TextWrappingModes.NoWrap;ui.subtitle.overflowMode=TextOverflowModes.Ellipsis;ui.subtitleRect=ui.subtitle.rectTransform;
    ui.pips=new BoardPips(f,11);
    var track=N.Image(f,"Bar",K.C("E6D6BC"),8);ui.barRect=track.rectTransform;
    ui.barFill=N.Image(track.transform,"Fill",K.C("5DA637"),8);var fr=ui.barFill.rectTransform;fr.anchorMin=Vector2.zero;fr.anchorMax=new Vector2(0,1);fr.offsetMin=fr.offsetMax=Vector2.zero;
    ui.barText=N.Text(track.transform,"Text",K.Number,12,K.Ink);ui.barText.alignment=TextAlignmentOptions.Center;ui.barText.textWrappingMode=TextWrappingModes.NoWrap;ui.barText.outlineWidth=.18f;ui.barText.outlineColor=new Color32(255,255,255,180);Stretch(ui.barText.rectTransform,Vector2.zero,Vector2.zero);
    ui.timer=Pill(f,"Timer",new Color(.17f,.13f,.09f,.88f),out ui.timerText,14,K.Number);ui.timerRect=ui.timer.rectTransform;
    ui.button=CheckoutDesktopButton.Create(f,42,15,12);ui.button.Clicked=hud.BoardPress;ui.buttonRect=(RectTransform)ui.button.transform;
    Destroy(ui.button.GetComponent<LayoutElement>());
    ui.alt=CheckoutDesktopButton.Create(f,42,15,12);ui.alt.Clicked=hud.BoardPress;Destroy(ui.alt.GetComponent<LayoutElement>());ui.alt.gameObject.SetActive(false);
    ui.chipsBox=N.Node("Chips",f);var cv=N.Column(ui.chipsBox.gameObject,4);cv.childAlignment=TextAnchor.UpperCenter;cv.childForceExpandWidth=false;cv.childControlWidth=true;
    ui.cornerBack=N.Image(f,"Corner",K.Cream,22);var cb=ui.cornerBack.rectTransform;
    var cEdge=N.Image(ui.cornerBack.transform,"Edge",PortraitGold,22);Stretch(cEdge.rectTransform,new Vector2(-3,-3),new Vector2(3,3));cEdge.transform.SetAsFirstSibling();
    var cFace=N.Image(ui.cornerBack.transform,"Face",K.Cream,20);Stretch(cFace.rectTransform,Vector2.zero,Vector2.zero);
    ui.cornerIcon=N.Image(ui.cornerBack.transform,"Icon",Color.white,0);ui.cornerIcon.preserveAspect=true;Stretch(ui.cornerIcon.rectTransform,new Vector2(5,5),new Vector2(-5,-5));
    ui.cornerBack.gameObject.SetActive(false);
    ui.ribbon=Pill(root,"Ribbon",K.C("E15533"),out ui.ribbonText,13,K.Label);ui.ribbonText.characterSpacing=2;ui.ribbonRect=ui.ribbon.rectTransform;
    ui.badge=Pill(root,"Badge",new Color(.29f,.21f,.14f,.92f),out ui.badgeText,15,K.Number);ui.badgeRect=ui.badge.rectTransform;
    // (rankings: the place disc, the flag on a white edge, the value and its label; off unless the row is a "rank")
    ui.rankDisc=N.Image(f,"Rank",K.C("EADBC4"),0);ui.rankDisc.sprite=K.Disc();
    ui.rankText=N.Text(ui.rankDisc.transform,"Text",K.Headline,22,K.Ink);ui.rankText.alignment=TextAlignmentOptions.Center;ui.rankText.textWrappingMode=TextWrappingModes.NoWrap;
    ui.rankText.enableAutoSizing=true;ui.rankText.fontSizeMin=11;ui.rankText.fontSizeMax=24;Stretch(ui.rankText.rectTransform,new Vector2(4,2),new Vector2(-4,-2));
    ui.flagEdge=N.Image(f,"FlagEdge",Color.white,4);
    ui.flagImage=N.Image(ui.flagEdge.transform,"Flag",Color.white,0);ui.flagImage.preserveAspect=true;Stretch(ui.flagImage.rectTransform,new Vector2(2,2),new Vector2(-2,-2));
    ui.valueText=N.Text(f,"Value",K.Number,20,K.Ink);ui.valueText.alignment=TextAlignmentOptions.MidlineRight;ui.valueText.textWrappingMode=TextWrappingModes.NoWrap;
    ui.valueText.enableAutoSizing=true;ui.valueText.fontSizeMin=12;ui.valueText.fontSizeMax=21;
    ui.valueLabelText=N.Text(f,"ValueLabel",K.Label,11,K.Muted);ui.valueLabelText.alignment=TextAlignmentOptions.MidlineRight;ui.valueLabelText.textWrappingMode=TextWrappingModes.NoWrap;ui.valueLabelText.characterSpacing=2;
    ui.rankDisc.gameObject.SetActive(false);ui.flagEdge.gameObject.SetActive(false);ui.valueText.gameObject.SetActive(false);ui.valueLabelText.gameObject.SetActive(false);
    return ui;
   }

   // Modes: card (the usual square tile), compact (a board with chips: the friends, the requests), showcase (a prize,
   // big art), gift (a present to open, big wobbling art), line (a slim row: the Correio's history) and row (wide rows).
   void Layout(string mode,int chipRows){
    string key=mode+chipRows;if(key==layoutMode)return;layoutMode=key;
    ring.gameObject.SetActive(false);
    // (ribbons sit inside the card's corner, clear of the section title above; the number pill too)
    Place(ribbonRect,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(-6,-6),new Vector2(100,26));ribbonRect.localRotation=Quaternion.Euler(0,0,mode=="row"?4:6);
    Place(badgeRect,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(6,2),new Vector2(48,28));
    title.alignment=TextAlignmentOptions.Center;subtitle.alignment=TextAlignmentOptions.Center;title.fontSizeMax=17;
    switch(mode){
     case "row":
      Place(circle,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(12,2),new Vector2(84,84));
      Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(110,-12),new Vector2(-430,30));title.alignment=TextAlignmentOptions.MidlineLeft;
      Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(110,-42),new Vector2(-430,20));subtitle.alignment=TextAlignmentOptions.MidlineLeft;
      Place(pips.Rect,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(-232,-16),new Vector2(90,14));
      Place(barRect,new Vector2(0,0),new Vector2(1,0),new Vector2(0,0),new Vector2(110,18),new Vector2(-430,20));
      Place(buttonRect,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-12,-2),new Vector2(200,52));
      Place(timerRect,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-222,-20),new Vector2(96,26));
      Place(ribbonRect,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(-8,10),new Vector2(100,26));
      Place(badgeRect,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(-224,-34),new Vector2(48,28));
      Place(ring.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(7,2),new Vector2(94,94));
      Place(cornerBack.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(.5f,.5f),new Vector2(86,-26),new Vector2(36,36));
      Place(chipsBox,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(110,-64),new Vector2(-430,ChipH));
      title.fontSizeMax=20;break;
     case "rank":
      // (placed per row in PlaceRank: the place, the button and the ribbon move things)
      title.fontSizeMax=19;ribbonRect.localRotation=Quaternion.identity;break;
     case "line":
      Place(circle,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(10,0),new Vector2(42,42));
      Place(ring.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(7,0),new Vector2(48,48));
      Place(cornerBack.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(.5f,.5f),new Vector2(50,-12),new Vector2(24,24));
      Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(66,-5),new Vector2(-76,24));title.alignment=TextAlignmentOptions.MidlineLeft;
      Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(66,-29),new Vector2(-76,20));subtitle.alignment=TextAlignmentOptions.MidlineLeft;
      title.fontSizeMax=16;break;
     case "compact":{
      // face 96 high in its ring, the timer on its foot, title, subtitle, the chip rows, a bar, the buttons
      Place(circle,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-10),new Vector2(96,96));
      Place(ring.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-5),new Vector2(106,106));
      Place(cornerBack.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(42,-92),new Vector2(40,40));
      Place(timerRect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,-104),new Vector2(92,24));
      Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-118),new Vector2(-16,28));
      Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-146),new Vector2(-16,18));
      Place(chipsBox,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-CompactTop),new Vector2(-16,chipRows*ChipH));
      float below=-CompactTop-chipRows*ChipH-2;
      Place(barRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,below),new Vector2(-24,14));
      Place(pips.Rect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,below),new Vector2(120,14));
      break;}
     case "face":
      // a face on a short card (the profile's faces, a friend request): ring, name, a line, the buttons
      Place(circle,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-8),new Vector2(90,90));
      Place(ring.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-3),new Vector2(100,100));
      Place(cornerBack.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(40,-84),new Vector2(36,36));
      Place(timerRect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,-96),new Vector2(92,24));
      Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-102),new Vector2(-16,26));
      Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-128),new Vector2(-16,18));
      Place(pips.Rect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-148),new Vector2(120,14));
      Place(barRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-148),new Vector2(-24,14));
      Place(chipsBox,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-148),new Vector2(-16,ChipH));
      break;
     case "showcase":
      // the prize big: a 150 plate, then its name, the friends it takes and the bar
      Place(circle,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-8),new Vector2(150,150));
      Place(ring.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-3),new Vector2(160,160));
      Place(cornerBack.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(62,-140),new Vector2(44,44));
      Place(timerRect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,-150),new Vector2(96,26));
      Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-162),new Vector2(-16,30));
      Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-192),new Vector2(-16,18));
      Place(pips.Rect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-212),new Vector2(120,14));
      Place(barRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-216),new Vector2(-24,15));
      Place(chipsBox,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-212),new Vector2(-16,ChipH));
      title.fontSizeMax=19;break;
     case "gift":
      // a present: big art (132), its sender, Abrir
      Place(circle,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-4),new Vector2(132,132));
      Place(ring.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,0),new Vector2(140,140));
      Place(cornerBack.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(54,-118),new Vector2(40,40));
      Place(timerRect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,-130),new Vector2(96,26));
      Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-140),new Vector2(-16,28));
      Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-168),new Vector2(-16,18));
      Place(pips.Rect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-188),new Vector2(120,14));
      Place(barRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-190),new Vector2(-24,15));
      Place(chipsBox,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-186),new Vector2(-16,ChipH));
      break;
     default:
      Place(circle,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-12),new Vector2(112,112));
      Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-128),new Vector2(-16,38));
      Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-166),new Vector2(-16,18));
      // Face is 258 tall (tile 268 minus the edge): pips, bar and button stack without touching.
      Place(pips.Rect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-181),new Vector2(120,14));
      Place(barRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-197),new Vector2(-24,15));
      Place(timerRect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,-122),new Vector2(96,26));
      Place(ring.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-7),new Vector2(122,122));
      Place(cornerBack.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(46,-106),new Vector2(44,44));
      Place(chipsBox,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-186),new Vector2(-16,ChipRows*ChipH));
      break;
    }
   }

   public void Apply(DesktopTile t,bool asRows,bool isSelected){
    bool changed=data==null||data.id!=t.id;data=t;Id=t.id;rows=asRows;frame=t.frame??"";
    int chipRows=hud.boardChipRows;
    string mode=asRows&&frame=="rank"?"rank":asRows?"row":frame=="line"?"line":frame=="showcase"?"showcase":frame=="gift"?"gift":chipRows>0?"compact":frame=="portrait"&&hud.boardFaces?"face":"card";
    Layout(mode,chipRows);if(changed)wobblePhase=(t.id??"").GetHashCode()%100*.07f;
    bool locked=t.state=="locked",done=t.state=="done";
    face.color=ToneFace(t.tone);circleImage.color=locked?K.C("D8CDBB"):Color.Lerp(Color.white,ToneFace(t.tone),.6f);
    var sprite=K.Icon(t.icon);icon.sprite=sprite;icon.enabled=sprite;
    icon.color=locked?new Color(.25f,.19f,.13f,.82f):done?new Color(1,1,1,.75f):Color.white;
    lockIcon.gameObject.SetActive(locked);stamp.gameObject.SetActive(done);
    title.text=K.Clean(t.title);subtitle.text=K.Clean(t.subtitle);subtitle.gameObject.SetActive(!string.IsNullOrEmpty(t.subtitle));
    pips.Apply(t.stars,t.maxStars);
    bool bar=t.fill>=0;barRect.gameObject.SetActive(bar);
    if(bar){fillTarget=Mathf.Clamp01(t.fill);if(changed||fillShown<0)fillShown=fillTarget;barText.text=K.Clean(t.fillText);
     barFill.color=t.tone=="danger"||t.tone=="warning"||t.tone=="info"||t.tone=="gold"||t.tone=="locked"?ToneStrong(t.tone):fillTarget<.34f?ToneStrong("warning"):ToneStrong("success");}
    bool hasRibbon=!string.IsNullOrEmpty(t.sticker);ribbon.gameObject.SetActive(hasRibbon);
    if(hasRibbon){var label=K.Clean(t.sticker);ribbonText.text=label;ribbon.color=ToneStrong(string.IsNullOrEmpty(t.tone)?"danger":t.tone);ribbonRect.sizeDelta=new Vector2(PillWidth(ribbonText,label,60),26);}
    bool hasBadge=!string.IsNullOrEmpty(t.badge);badge.gameObject.SetActive(hasBadge);
    if(hasBadge){var label=K.Clean(t.badge);badgeText.text=label;badgeRect.sizeDelta=new Vector2(PillWidth(badgeText,label,40),28);}
    timer.gameObject.SetActive(t.timerEnd>0);
    bool hasButton=t.action!=null&&!string.IsNullOrEmpty(t.action.label);button.gameObject.SetActive(hasButton);if(hasButton)button.Apply(t.action);
    // Social v1: a framed portrait, the stage badge, the chips and a second big button.
    bool portrait=IsFace(t);isFace=portrait;ring.gameObject.SetActive(portrait);
    K.SetRound(clip,portrait);rim.gameObject.SetActive(portrait);
    if(portrait){
     circleImage.color=locked?K.C("6E7790"):PortraitNavy;circleImage.sprite=K.Disc();circleImage.type=Image.Type.Simple;
     icon.rectTransform.offsetMin=Vector2.zero;icon.rectTransform.offsetMax=Vector2.zero;
     float plate=circle.sizeDelta.x,border=(ring.rectTransform.sizeDelta.x-plate)*.5f;K.FitRim(rim,plate,Mathf.Max(3,border));
    }else{circleImage.sprite=K.Rounded(56);circleImage.type=Image.Type.Sliced;icon.rectTransform.offsetMin=new Vector2(10,10);icon.rectTransform.offsetMax=new Vector2(-10,-10);}
    var corner=K.Icon(t.corner);cornerBack.gameObject.SetActive(corner);if(corner)cornerIcon.sprite=corner;
    var cs=t.chips??new DesktopStat[0];
    while(chips.Count<cs.Length&&chips.Count<ChipRows)chips.Add(TileChip.Create(chipsBox));
    for(int i=0;i<chips.Count;i++){bool on=i<cs.Length;chips[i].rect.gameObject.SetActive(on);if(on)chips[i].Apply(cs[i]);}
    chipsBox.gameObject.SetActive(cs.Length>0);
    bool line=mode=="line";
    // A slim row: the face, who and what; no buttons, bars or ribbons.
    if(line){barRect.gameObject.SetActive(false);pips.gameObject.SetActive(false);timer.gameObject.SetActive(false);ribbon.gameObject.SetActive(false);badge.gameObject.SetActive(false);button.gameObject.SetActive(false);chipsBox.gameObject.SetActive(false);hasButton=false;}
    if(t.frame=="portrait"&&hasRibbon)ribbon.color=PortraitGold;
    bool rank=mode=="rank";
    rankDisc.gameObject.SetActive(false);flagEdge.gameObject.SetActive(false);valueText.gameObject.SetActive(false);valueLabelText.gameObject.SetActive(false);
    if(rank){selected=isSelected;alt.gameObject.SetActive(false);PlaceRank(t,hasButton,hasRibbon);return;}
    // (a present and a prize: big art on a soft plate, no inset)
    if((frame=="gift"||frame=="showcase")&&!portrait){icon.rectTransform.offsetMin=new Vector2(frame=="gift"?2:8,frame=="gift"?2:8);icon.rectTransform.offsetMax=new Vector2(frame=="gift"?-2:-8,frame=="gift"?-2:-8);}
    if(frame=="gift"&&!portrait)circleImage.color=new Color(1,1,1,.55f);
    bool hasAlt=t.alt!=null&&!string.IsNullOrEmpty(t.alt.label);alt.gameObject.SetActive(hasAlt&&hasButton);
    var ar=(RectTransform)alt.transform;
    if(hasAlt&&hasButton){
     if(asRows){Place(buttonRect,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-12,-2),new Vector2(150,52));Place(ar,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-170,-2),new Vector2(150,52));}
     else{Place(buttonRect,new Vector2(0,0),new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(2,4),new Vector2(-12,44));Place(ar,new Vector2(.5f,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(-2,4),new Vector2(-12,44));}
     alt.Apply(t.alt);
     // Two buttons on a narrow card (phones: four friends a row): words without icons, shrinking before any "…".
     bool tight=!asRows&&hud.boardCellWidth>0&&hud.boardCellWidth<300;
     button.Fit(tight);alt.Fit(tight);
    } else if(asRows)Place(buttonRect,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-12,-2),new Vector2(200,52));
    else Place(buttonRect,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,4),new Vector2(-14,mode=="card"?40:44));
    Select(isSelected);
   }
   // A ranking row: [place] [round face + stage badge] name / level ribbon + stage … [flag] [value] [button]. Medal colours
   // for the top three; the face is round, clipped inside its ring (no square corners).
   void PlaceRank(DesktopTile t,bool hasButton,bool hasRibbon){
    string place=t.rank??"";bool hasPlace=place.Length>0;
    barRect.gameObject.SetActive(false);pips.gameObject.SetActive(false);timer.gameObject.SetActive(false);badge.gameObject.SetActive(false);chipsBox.gameObject.SetActive(false);
    float lead=hasPlace?66:0,face=Phone?56:60;
    rankDisc.gameObject.SetActive(hasPlace);
    if(hasPlace){
     Place(rankDisc.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(10,0),new Vector2(50,50));
     rankText.text=K.Clean(place);
     Color disc=place=="1"?K.C("E3B54A"):place=="2"?K.C("AEB8C4"):place=="3"?K.C("C98146"):place=="-"?K.C("D8CDBB"):K.C("F3E6CC");
     rankDisc.color=disc;rankText.color=place=="1"||place=="2"||place=="3"?Color.white:K.Ink;
     rankText.outlineWidth=place=="1"||place=="2"||place=="3"?.2f:0;rankText.outlineColor=new Color32(80,50,20,200);
    }
    Place(circle,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(10+lead+3,0),new Vector2(face,face));
    Place(ring.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(10+lead,0),new Vector2(face+6,face+6));
    if(isFace){float border=3;K.FitRim(rim,face,border);}
    Place(cornerBack.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(.5f,.5f),new Vector2(10+lead+face-2,-face*.36f),new Vector2(26,26));
    float x=10+lead+face+18;
    // the right end: the button, then the value block, then the flag
    float right=12;
    if(hasButton){Place(buttonRect,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-12,-2),new Vector2(Phone?180:200,Phone?46:50));button.Fit(true);right+=(Phone?180:200)+12;}
    bool hasValue=!string.IsNullOrEmpty(t.value);
    if(hasValue){
     valueText.gameObject.SetActive(true);valueText.text=K.Clean(t.value);
     bool label=!string.IsNullOrEmpty(t.valueLabel);valueLabelText.gameObject.SetActive(label);valueLabelText.text=K.Clean(t.valueLabel).ToUpperInvariant();
     float w=Mathf.Clamp(Mathf.Max(valueText.GetPreferredValues(valueText.text).x,label?valueLabelText.GetPreferredValues(valueLabelText.text).x:0)+6,70,170);
     Place(valueText.rectTransform,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-right,label?8:0),new Vector2(w,28));
     Place(valueLabelText.rectTransform,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-right,-15),new Vector2(w,16));
     valueText.color=t.tone=="gold"?K.C("9A6A10"):K.Ink;
     right+=w+14;
    }
    var flag=K.Icon(t.flag);flagEdge.gameObject.SetActive(flag);
    if(flag){flagImage.sprite=flag;Place(flagEdge.rectTransform,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-right,0),new Vector2(44,34));right+=44+14;}
    // the name on top; the level ribbon and the stage under it
    Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(x,-9),new Vector2(-x-right,30));title.alignment=TextAlignmentOptions.MidlineLeft;
    float under=x;
    if(hasRibbon){
     ribbon.color=t.tone=="gold"?K.C("C98A12"):PortraitNavy;ribbonRect.localRotation=Quaternion.identity;
     float rw=PillWidth(ribbonText,ribbonText.text,54);
     Place(ribbonRect,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(x,-42),new Vector2(rw,22));under+=rw+8;
    }
    Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(under,-42),new Vector2(-under-right,22));subtitle.alignment=TextAlignmentOptions.MidlineLeft;
    Select(selected);
   }
   public void Select(bool on){selected=on;edge.color=on?K.C("F2B03D"):ToneEdge(data!=null?data.tone:"");rect.localScale=on?Vector3.one*1.0f:Vector3.one;}

   public void Tick(double now,float t){
    if(data==null)return;
    if(data.timerEnd>0){
     double left=data.timerEnd-now;timerText.text=left>0?Clock(left):"Pronto!";
     if(data.state=="busy"&&data.timerTotal>0)fillTarget=Mathf.Clamp01(1f-(float)(left/data.timerTotal));
    }
    if(fillShown>=0){fillShown=Mathf.MoveTowards(fillShown,fillTarget,Time.unscaledDeltaTime*.9f);barFill.rectTransform.anchorMax=new Vector2(Mathf.Max(fillShown>0?.04f:0,fillShown),1);}
    bool ready=data.state=="ready";
    glow.color=ready?new Color(1,.82f,.3f,.38f+.22f*Mathf.Sin(t*4.5f)):selected?new Color(1,.85f,.4f,.35f):new Color(1,.85f,.3f,0);
    icon.rectTransform.anchoredPosition=new Vector2(0,ready&&!isFace?Mathf.Abs(Mathf.Sin(t*3.2f))*5:0);
    // A present wobbles while it waits, with a little hop now and then (like a box someone shakes).
    if(frame=="gift"){float w=t*2.6f+wobblePhase;float hop=Mathf.Repeat(t+wobblePhase,3.2f);
     icon.rectTransform.localRotation=Quaternion.Euler(0,0,Mathf.Sin(w)*7+(hop<.35f?Mathf.Sin(hop/.35f*Mathf.PI*4)*6:0));
     icon.rectTransform.anchoredPosition=new Vector2(0,hop<.35f?Mathf.Sin(hop/.35f*Mathf.PI)*9:0);}
    else if(icon.rectTransform.localRotation!=Quaternion.identity)icon.rectTransform.localRotation=Quaternion.identity;
   }

   public void OnPointerClick(PointerEventData e){if(e.button!=PointerEventData.InputButton.Left||data==null)return;hud.BoardSelect(data.id);StartCoroutine(U.Pop(transform,1.05f,.18f));}
  }

  // The side panel: the picked tile up close with every action.
  class BoardDetailUi:MonoBehaviour {
   CheckoutDesktopHUD hud;DesktopTile data;
   Image hero,heroGlow,circleImage,icon,lockIcon,stamp,ribbon,barFill,timer,clip,rim;TextMeshProUGUI title,subtitle,ribbonText,barText,timerText,detail;
   RectTransform ribbonRect,barRect,factsGrid,linesBox,actionsBox;GameObject timerRow;BoardPips pips;
   readonly List<BoardChip> facts=new List<BoardChip>();readonly List<TextMeshProUGUI> lines=new List<TextMeshProUGUI>();readonly List<CheckoutDesktopButton> actions=new List<CheckoutDesktopButton>();
   readonly List<RectTransform> stepRows=new List<RectTransform>();
   float fillShown=-1,fillTarget;string shownId;

   public static BoardDetailUi Create(CheckoutDesktopHUD hud,RectTransform content){
    var ui=content.gameObject.AddComponent<BoardDetailUi>();ui.hud=hud;
    // (phones: a little tighter, so a friend request shows whole with both buttons)
    var col=content.GetComponent<VerticalLayoutGroup>();col.spacing=Phone?8:10;col.padding=Phone?new RectOffset(6,10,4,6):new RectOffset(6,10,6,14);col.childAlignment=TextAnchor.UpperCenter;
    // Hero: the icon big on a soft glow, its ribbon.
    // (phones: a shorter hero, so a friend request's text and both its buttons fit without a scroll)
    ui.hero=N.Image(content,"Hero",K.C("FFF3C8"),20);ui.hero.gameObject.AddComponent<LayoutElement>().preferredHeight=Phone?150:190;
    ui.heroGlow=N.Image(ui.hero.transform,"Glow",new Color(1,1,1,.7f),0);ui.heroGlow.sprite=U.Glow();Place(ui.heroGlow.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(300,240));
    ui.circleImage=N.Image(ui.hero.transform,"Circle",Color.white,0);ui.circleImage.sprite=K.Rounded(80);ui.circleImage.type=Image.Type.Sliced;Place(ui.circleImage.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,Phone?new Vector2(128,128):new Vector2(160,160));
    ui.clip=K.RoundClip(ui.circleImage.transform,"Clip");K.SetRound(ui.clip,false);
    ui.icon=N.Image(ui.clip.transform,"Icon",Color.white,0);ui.icon.preserveAspect=true;Stretch(ui.icon.rectTransform,new Vector2(14,14),new Vector2(-14,-14));
    ui.rim=N.Image(ui.circleImage.transform,"Rim",PortraitGold,0);ui.rim.gameObject.SetActive(false);
    ui.lockIcon=N.Image(ui.circleImage.transform,"Lock",Color.white,0);ui.lockIcon.sprite=K.Icon("Icons/lock");ui.lockIcon.preserveAspect=true;Place(ui.lockIcon.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(64,64));
    ui.stamp=N.Image(ui.circleImage.transform,"Stamp",Color.white,0);ui.stamp.sprite=K.Icon("Icons/success");ui.stamp.preserveAspect=true;Place(ui.stamp.rectTransform,new Vector2(1,0),new Vector2(1,0),new Vector2(1,0),new Vector2(14,-8),new Vector2(64,64));
    ui.ribbon=Pill(ui.hero.transform,"Ribbon",K.C("E15533"),out ui.ribbonText,15,K.Label);ui.ribbonText.characterSpacing=2;ui.ribbonRect=ui.ribbon.rectTransform;
    Place(ui.ribbonRect,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(10,-10),new Vector2(120,30));ui.ribbonRect.localRotation=Quaternion.Euler(0,0,4);
    ui.title=N.Text(content,"Title",K.Headline,26,K.Ink);ui.title.alignment=TextAlignmentOptions.Center;
    ui.subtitle=N.Text(content,"Subtitle",K.Body,15,K.Muted);ui.subtitle.alignment=TextAlignmentOptions.Center;
    ui.pips=new BoardPips(content,15);ui.pips.Rect.gameObject.AddComponent<LayoutElement>().preferredHeight=20;
    var track=N.Image(content,"Bar",K.C("E6D6BC"),10);ui.barRect=track.rectTransform;track.gameObject.AddComponent<LayoutElement>().preferredHeight=26;
    ui.barFill=N.Image(track.transform,"Fill",K.C("5DA637"),10);var fr=ui.barFill.rectTransform;fr.anchorMin=Vector2.zero;fr.anchorMax=new Vector2(0,1);fr.offsetMin=fr.offsetMax=Vector2.zero;
    ui.barText=N.Text(track.transform,"Text",K.Number,15,K.Ink);ui.barText.alignment=TextAlignmentOptions.Center;ui.barText.textWrappingMode=TextWrappingModes.NoWrap;ui.barText.outlineWidth=.18f;ui.barText.outlineColor=new Color32(255,255,255,180);Stretch(ui.barText.rectTransform,Vector2.zero,Vector2.zero);
    ui.timerRow=N.Node("Timer row",content).gameObject;ui.timerRow.AddComponent<LayoutElement>().preferredHeight=34;
    ui.timer=Pill(ui.timerRow.transform,"Timer",new Color(.17f,.13f,.09f,.9f),out ui.timerText,18,K.Number);Place(ui.timer.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(150,34));
    ui.detail=N.Text(content,"Detail",K.Body,15,K.Ink);ui.detail.alignment=TextAlignmentOptions.Center;
    ui.factsGrid=N.Node("Facts",content);var grid=ui.factsGrid.gameObject.AddComponent<GridLayoutGroup>();grid.cellSize=new Vector2(186,60);grid.spacing=new Vector2(8,8);grid.constraint=GridLayoutGroup.Constraint.FixedColumnCount;grid.constraintCount=2;grid.childAlignment=TextAnchor.UpperCenter;
    ui.linesBox=N.Node("Lines",content);N.Column(ui.linesBox.gameObject,2);
    ui.actionsBox=N.Node("Actions",content);N.Column(ui.actionsBox.gameObject,10,new RectOffset(0,0,6,0));
    return ui;
   }

   public void Apply(DesktopTile t,bool asRows){
    bool changed=shownId!=t.id;shownId=t.id;data=t;
    bool locked=t.state=="locked",done=t.state=="done";
    hero.color=ToneFace(string.IsNullOrEmpty(t.tone)?"gold":t.tone);heroGlow.color=new Color(1,1,1,.75f);
    bool portrait=IsFace(t);
    circleImage.color=locked?K.C("D8CDBB"):portrait?PortraitNavy:Color.white;
    var sprite=K.Icon(t.icon);icon.sprite=sprite;icon.enabled=sprite;icon.color=locked?new Color(.25f,.19f,.13f,.82f):Color.white;
    lockIcon.gameObject.SetActive(locked);stamp.gameObject.SetActive(done);
    // (a friend's face: round, the picture clipped inside the plate, a gold rim over its edge)
    K.SetRound(clip,portrait);rim.gameObject.SetActive(portrait);
    circleImage.sprite=portrait?K.Disc():K.Rounded(80);circleImage.type=portrait?Image.Type.Simple:Image.Type.Sliced;
    var ir=icon.rectTransform;ir.offsetMin=portrait?Vector2.zero:new Vector2(14,14);ir.offsetMax=portrait?Vector2.zero:new Vector2(-14,-14);
    if(portrait)K.FitRim(rim,circleImage.rectTransform.sizeDelta.x,Phone?5:6);
    bool hasRibbon=!string.IsNullOrEmpty(t.sticker);ribbon.gameObject.SetActive(hasRibbon);
    if(hasRibbon){var label=K.Clean(t.sticker);ribbonText.text=label;ribbon.color=ToneStrong(string.IsNullOrEmpty(t.tone)?"danger":t.tone);ribbonRect.sizeDelta=new Vector2(PillWidth(ribbonText,label,70),30);}
    title.text=K.Clean(t.title);subtitle.text=K.Clean(t.subtitle);subtitle.gameObject.SetActive(!string.IsNullOrEmpty(t.subtitle));
    pips.Apply(t.stars,t.maxStars);
    bool bar=t.fill>=0;barRect.gameObject.SetActive(bar);
    if(bar){fillTarget=Mathf.Clamp01(t.fill);if(changed||fillShown<0)fillShown=fillTarget;barText.text=K.Clean(t.fillText);
     barFill.color=t.tone=="danger"||t.tone=="warning"||t.tone=="info"||t.tone=="gold"||t.tone=="locked"?ToneStrong(t.tone):fillTarget<.34f?ToneStrong("warning"):ToneStrong("success");}
    timerRow.SetActive(t.timerEnd>0);
    detail.text=K.Clean(t.detail);detail.gameObject.SetActive(!string.IsNullOrEmpty(t.detail));
    var f=t.facts??new DesktopStat[0];
    // (two facts a row as wide as the panel: a narrow panel on an iPad cut them at 186 each)
    var fg=factsGrid.GetComponent<GridLayoutGroup>();fg.cellSize=new Vector2(Mathf.Min(186,Mathf.Floor((hud.BoardDetailWidth-40-8)/2)),60);
    while(facts.Count<f.Length)facts.Add(BoardChip.Create(factsGrid,false));
    for(int i=0;i<facts.Count;i++){bool on=i<f.Length;facts[i].gameObject.SetActive(on);if(on)facts[i].Apply(f[i]);}
    factsGrid.gameObject.SetActive(f.Length>0);
    var l=t.lines??new string[0];
    while(lines.Count<l.Length){var x=N.Text(linesBox,"Line",K.Body,14,K.Muted);x.alignment=TextAlignmentOptions.Center;lines.Add(x);}
    for(int i=0;i<lines.Count;i++){bool on=i<l.Length;lines[i].gameObject.SetActive(on);if(on)lines[i].text=K.Clean(l[i]);}
    linesBox.gameObject.SetActive(l.Length>0);
    var a=t.actions??new DesktopButton[0];
    while(actions.Count<a.Length){var b=CheckoutDesktopButton.Create(actionsBox,52,17,14);b.Clicked=hud.BoardPress;actions.Add(b);}
    // Short buttons in a row of four (a quantity stepper: −5 −1 +1 +5), the others one per line.
    int rowIndex=0,inRow=0;
    for(int i=0;i<actions.Count;i++){
     bool on=i<a.Length;actions[i].gameObject.SetActive(on);if(!on)continue;actions[i].Apply(a[i]);
     bool small=K.Clean(a[i].label??"").Length<=3&&string.IsNullOrEmpty(a[i].icon);
     Transform parent=actionsBox;
     if(small){if(inRow==0||inRow==4){while(stepRows.Count<=rowIndex){var r=N.Node("Steps",actionsBox);var h=N.Row(r.gameObject,8);h.childForceExpandWidth=true;h.childControlHeight=true;stepRows.Add(r);}parent=stepRows[rowIndex];rowIndex++;inRow=0;}else parent=stepRows[rowIndex-1];inRow++;}
     else inRow=0;
     if(actions[i].transform.parent!=parent)actions[i].transform.SetParent(parent,false);
     if(parent==actionsBox)actions[i].transform.SetAsLastSibling();else{parent.SetAsLastSibling();actions[i].transform.SetAsLastSibling();}
    }
    for(int r=0;r<stepRows.Count;r++)stepRows[r].gameObject.SetActive(r<rowIndex);
    actionsBox.gameObject.SetActive(a.Length>0);
   }

   public void Tick(double now,float t){
    if(data==null||!gameObject.activeInHierarchy)return;
    if(data.timerEnd>0){double left=data.timerEnd-now;timerText.text=left>0?Clock(left):"Pronto!";
     if(data.state=="busy"&&data.timerTotal>0)fillTarget=Mathf.Clamp01(1f-(float)(left/data.timerTotal));}
    if(fillShown>=0){fillShown=Mathf.MoveTowards(fillShown,fillTarget,Time.unscaledDeltaTime*.9f);barFill.rectTransform.anchorMax=new Vector2(Mathf.Max(fillShown>0?.03f:0,fillShown),1);}
    bool ready=data.state=="ready";
    // (a portrait stays still in its round frame: a moving picture would bare the plate's edge)
    icon.rectTransform.anchoredPosition=IsFace(data)?Vector2.zero:new Vector2(0,ready?Mathf.Abs(Mathf.Sin(t*3f))*8:Mathf.Sin(t*1.6f)*2);
    heroGlow.rectTransform.localScale=Vector3.one*(1+.05f*Mathf.Sin(t*2.2f));
   }
  }
 }
}
