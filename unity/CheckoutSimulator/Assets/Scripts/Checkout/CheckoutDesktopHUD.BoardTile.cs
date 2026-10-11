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

   public static BoardTileUi Create(CheckoutDesktopHUD hud,Transform parent){
    var root=N.Node("Tile",parent);var ui=root.gameObject.AddComponent<BoardTileUi>();ui.hud=hud;ui.rect=root;
    ui.glow=N.Image(root,"Glow",new Color(1,.85f,.3f,0),0);ui.glow.sprite=U.Glow();Stretch(ui.glow.rectTransform,new Vector2(-26,-26),new Vector2(26,26));
    ui.edge=N.Image(root,"Edge",K.Border,18);ui.edge.raycastTarget=true;Stretch(ui.edge.rectTransform,Vector2.zero,Vector2.zero);
    ui.face=N.Image(root,"Face",K.Cream,16);Stretch(ui.face.rectTransform,new Vector2(3,7),new Vector2(-3,-3));
    var f=ui.face.transform;
    ui.circleImage=N.Image(f,"Circle",Color.white,0);ui.circleImage.sprite=K.Rounded(56);ui.circleImage.type=Image.Type.Sliced;ui.circle=ui.circleImage.rectTransform;
    ui.icon=N.Image(ui.circle,"Icon",Color.white,0);ui.icon.preserveAspect=true;Stretch(ui.icon.rectTransform,new Vector2(10,10),new Vector2(-10,-10));
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
    ui.ribbon=Pill(root,"Ribbon",K.C("E15533"),out ui.ribbonText,13,K.Label);ui.ribbonText.characterSpacing=2;ui.ribbonRect=ui.ribbon.rectTransform;
    ui.badge=Pill(root,"Badge",new Color(.29f,.21f,.14f,.92f),out ui.badgeText,15,K.Number);ui.badgeRect=ui.badge.rectTransform;
    return ui;
   }

   void Layout(bool asRows){
    string mode=asRows?"row":"card";if(mode==layoutMode)return;layoutMode=mode;
    if(!asRows){
     Place(circle,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-12),new Vector2(112,112));
     Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-128),new Vector2(-16,38));title.alignment=TextAlignmentOptions.Center;
     Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-166),new Vector2(-16,18));subtitle.alignment=TextAlignmentOptions.Center;
     // Face is 258 tall (tile 268 minus the edge): pips, bar and button stack without touching.
     Place(pips.Rect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-181),new Vector2(120,14));
     Place(barRect,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-197),new Vector2(-24,15));
     Place(buttonRect,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,4),new Vector2(-14,40)); // top at 214 from the face top: clear of the bar (ends at 212)
     Place(timerRect,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,-122),new Vector2(96,26));
     Place(ribbonRect,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(-8,10),new Vector2(100,26));ribbonRect.localRotation=Quaternion.Euler(0,0,6);
     Place(badgeRect,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(8,10),new Vector2(48,28));
     title.fontSizeMax=17;
    } else {
     Place(circle,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(12,2),new Vector2(84,84));
     Place(titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(110,-12),new Vector2(-430,30));title.alignment=TextAlignmentOptions.MidlineLeft;
     Place(subtitleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(110,-42),new Vector2(-430,20));subtitle.alignment=TextAlignmentOptions.MidlineLeft;
     Place(pips.Rect,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(-232,-16),new Vector2(90,14));
     Place(barRect,new Vector2(0,0),new Vector2(1,0),new Vector2(0,0),new Vector2(110,18),new Vector2(-430,20));
     Place(buttonRect,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-12,-2),new Vector2(200,52));
     Place(timerRect,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-222,-20),new Vector2(96,26));
     Place(ribbonRect,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(-8,10),new Vector2(100,26));ribbonRect.localRotation=Quaternion.Euler(0,0,4);
     Place(badgeRect,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(-224,-34),new Vector2(48,28));
     title.fontSizeMax=20;
    }
   }

   public void Apply(DesktopTile t,bool asRows,bool isSelected){
    bool changed=data==null||data.id!=t.id;data=t;Id=t.id;rows=asRows;Layout(asRows);
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
    Select(isSelected);
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
    icon.rectTransform.anchoredPosition=new Vector2(0,ready?Mathf.Abs(Mathf.Sin(t*3.2f))*5:0);
   }

   public void OnPointerClick(PointerEventData e){if(e.button!=PointerEventData.InputButton.Left||data==null)return;hud.BoardSelect(data.id);StartCoroutine(U.Pop(transform,1.05f,.18f));}
  }

  // The side panel: the picked tile up close with every action.
  class BoardDetailUi:MonoBehaviour {
   CheckoutDesktopHUD hud;DesktopTile data;
   Image hero,heroGlow,circleImage,icon,lockIcon,stamp,ribbon,barFill,timer;TextMeshProUGUI title,subtitle,ribbonText,barText,timerText,detail;
   RectTransform ribbonRect,barRect,factsGrid,linesBox,actionsBox;GameObject timerRow;BoardPips pips;
   readonly List<BoardChip> facts=new List<BoardChip>();readonly List<TextMeshProUGUI> lines=new List<TextMeshProUGUI>();readonly List<CheckoutDesktopButton> actions=new List<CheckoutDesktopButton>();
   float fillShown=-1,fillTarget;string shownId;

   public static BoardDetailUi Create(CheckoutDesktopHUD hud,RectTransform content){
    var ui=content.gameObject.AddComponent<BoardDetailUi>();ui.hud=hud;
    var col=content.GetComponent<VerticalLayoutGroup>();col.spacing=10;col.padding=new RectOffset(6,10,6,14);col.childAlignment=TextAnchor.UpperCenter;
    // Hero: the icon big on a soft glow, its ribbon.
    ui.hero=N.Image(content,"Hero",K.C("FFF3C8"),20);ui.hero.gameObject.AddComponent<LayoutElement>().preferredHeight=190;
    ui.heroGlow=N.Image(ui.hero.transform,"Glow",new Color(1,1,1,.7f),0);ui.heroGlow.sprite=U.Glow();Place(ui.heroGlow.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(300,240));
    ui.circleImage=N.Image(ui.hero.transform,"Circle",Color.white,0);ui.circleImage.sprite=K.Rounded(80);ui.circleImage.type=Image.Type.Sliced;Place(ui.circleImage.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(160,160));
    ui.icon=N.Image(ui.circleImage.transform,"Icon",Color.white,0);ui.icon.preserveAspect=true;Stretch(ui.icon.rectTransform,new Vector2(14,14),new Vector2(-14,-14));
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
    circleImage.color=locked?K.C("D8CDBB"):Color.white;
    var sprite=K.Icon(t.icon);icon.sprite=sprite;icon.enabled=sprite;icon.color=locked?new Color(.25f,.19f,.13f,.82f):Color.white;
    lockIcon.gameObject.SetActive(locked);stamp.gameObject.SetActive(done);
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
    while(facts.Count<f.Length)facts.Add(BoardChip.Create(factsGrid,false));
    for(int i=0;i<facts.Count;i++){bool on=i<f.Length;facts[i].gameObject.SetActive(on);if(on)facts[i].Apply(f[i]);}
    factsGrid.gameObject.SetActive(f.Length>0);
    var l=t.lines??new string[0];
    while(lines.Count<l.Length){var x=N.Text(linesBox,"Line",K.Body,14,K.Muted);x.alignment=TextAlignmentOptions.Center;lines.Add(x);}
    for(int i=0;i<lines.Count;i++){bool on=i<l.Length;lines[i].gameObject.SetActive(on);if(on)lines[i].text=K.Clean(l[i]);}
    linesBox.gameObject.SetActive(l.Length>0);
    var a=t.actions??new DesktopButton[0];
    while(actions.Count<a.Length){var b=CheckoutDesktopButton.Create(actionsBox,52,17,14);b.Clicked=hud.BoardPress;actions.Add(b);}
    for(int i=0;i<actions.Count;i++){bool on=i<a.Length;actions[i].gameObject.SetActive(on);if(on)actions[i].Apply(a[i]);}
    actionsBox.gameObject.SetActive(a.Length>0);
   }

   public void Tick(double now,float t){
    if(data==null||!gameObject.activeInHierarchy)return;
    if(data.timerEnd>0){double left=data.timerEnd-now;timerText.text=left>0?Clock(left):"Pronto!";
     if(data.state=="busy"&&data.timerTotal>0)fillTarget=Mathf.Clamp01(1f-(float)(left/data.timerTotal));}
    if(fillShown>=0){fillShown=Mathf.MoveTowards(fillShown,fillTarget,Time.unscaledDeltaTime*.9f);barFill.rectTransform.anchorMax=new Vector2(Mathf.Max(fillShown>0?.03f:0,fillShown),1);}
    bool ready=data.state=="ready";
    icon.rectTransform.anchoredPosition=new Vector2(0,ready?Mathf.Abs(Mathf.Sin(t*3f))*8:Mathf.Sin(t*1.6f)*2);
    heroGlow.rectTransform.localScale=Vector3.one*(1+.05f*Mathf.Sin(t*2.2f));
   }
  }
 }
}
