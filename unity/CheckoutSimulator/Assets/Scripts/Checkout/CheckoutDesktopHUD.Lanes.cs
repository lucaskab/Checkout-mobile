using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // The delivery lanes of the Entregas window (board style "road", data from desktop/pages/stock-boards.ts):
 // one lane per truck slot, a road from the supplier of the product (frigorífico, fazenda, porto…) to the
 // supermarket, with the truck driving along it like a loading bar. While the supplier loads it, boxes hop
 // into the truck; on the road it bobs, puffs smoke and paints the road behind it; at the dock the boxes hop
 // into the market. Free lanes have the truck parked and waiting; the next slot is a locked lane to buy.
 public partial class CheckoutDesktopHUD {
  readonly List<BoardLaneUi> boardLanes=new List<BoardLaneUi>();
  readonly Dictionary<string,string> boardLaneStates=new Dictionary<string,string>();
  const float LaneHeight=190;

  class BoardLaneUi:MonoBehaviour {
   CheckoutDesktopHUD hud;public string Id;DesktopTile data;
   RectTransform rect,road,roadArea,truck,bubble,box,ribbonRect,timerRect,titleRect,dashes,trail,lockRect;
   Image edge,face,origin,market,truckImage,bubbleIcon,asphalt,trailImage,ribbon,timer,lockIcon,shade,glow,boxImage,originSign;
   TextMeshProUGUI title,subtitle,originLabel,marketLabel,ribbonText,timerText,status,lockText;
   readonly List<Image> puffs=new List<Image>();readonly List<float> puffAge=new List<float>();
   readonly List<CheckoutDesktopButton> buttons=new List<CheckoutDesktopButton>();
   float progressShown=-1,progress,nextPuff,boxAt;string lane="";

   static readonly Color Asphalt=K.C("4B4F58"),Grass=K.C("8CC65A"),GrassDark=K.C("6DAA3F"),Dash=K.C("F6D45B");

   public static BoardLaneUi Create(CheckoutDesktopHUD hud,Transform parent){
    var root=N.Node("Lane",parent);var ui=root.gameObject.AddComponent<BoardLaneUi>();ui.hud=hud;ui.rect=root;
    ui.glow=N.Image(root,"Glow",new Color(1,.85f,.3f,0),0);ui.glow.sprite=U.Glow();Stretch(ui.glow.rectTransform,new Vector2(-24,-24),new Vector2(24,24));
    ui.edge=N.Image(root,"Edge",K.Border,20);Stretch(ui.edge.rectTransform,Vector2.zero,Vector2.zero);
    ui.face=N.Image(root,"Face",K.Cream,18);Stretch(ui.face.rectTransform,new Vector2(3,7),new Vector2(-3,-3));
    var f=ui.face.transform;

    // The supplier on the left, the market before the buttons.
    ui.origin=N.Image(f,"Origin",Color.white,0);ui.origin.preserveAspect=true;Place(ui.origin.rectTransform,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(6,-6),new Vector2(184,128));
    ui.originSign=N.Image(f,"Origin sign",new Color(1,1,1,.55f),0);ui.originSign.preserveAspect=true;Place(ui.originSign.rectTransform,new Vector2(0,1),new Vector2(0,1),new Vector2(.5f,.5f),new Vector2(98,-66),new Vector2(70,70));
    ui.originLabel=N.Text(f,"Origin label",K.Label,13,K.Ink);ui.originLabel.alignment=TextAlignmentOptions.Center;ui.originLabel.textWrappingMode=TextWrappingModes.NoWrap;ui.originLabel.overflowMode=TextOverflowModes.Ellipsis;
    Place(ui.originLabel.rectTransform,new Vector2(0,0),new Vector2(0,0),new Vector2(0,0),new Vector2(6,10),new Vector2(184,22));
    ui.market=N.Image(f,"Market",Color.white,0);ui.market.preserveAspect=true;ui.market.sprite=K.Icon("Game/lane_mercado");
    Place(ui.market.rectTransform,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(-244,-6),new Vector2(170,120));
    ui.marketLabel=N.Text(f,"Market label",K.Label,13,K.Ink);ui.marketLabel.alignment=TextAlignmentOptions.Center;ui.marketLabel.text="SEU MERCADO";ui.marketLabel.characterSpacing=2;
    Place(ui.marketLabel.rectTransform,new Vector2(1,0),new Vector2(1,0),new Vector2(1,0),new Vector2(-244,10),new Vector2(170,22));

    // Road: grass verges, asphalt, dashed centre line, the painted trail behind the truck.
    ui.roadArea=N.Node("Road area",f);var ra=ui.roadArea;ra.anchorMin=new Vector2(0,0);ra.anchorMax=new Vector2(1,1);ra.offsetMin=new Vector2(196,0);ra.offsetMax=new Vector2(-420,0);
    var verge=N.Image(ra,"Verge",Grass,14);Place(verge.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,24),new Vector2(0,82));
    for(int i=0;i<9;i++){
     var bush=N.Image(verge.transform,"Bush",i%2==0?GrassDark:K.C("A2D46B"),10);var br=bush.rectTransform;
     float x=.04f+i*.115f;br.anchorMin=br.anchorMax=new Vector2(x,i%3==0?.9f:.08f);br.sizeDelta=new Vector2(i%2==0?22:16,i%2==0?14:11);
    }
    ui.asphalt=N.Image(ra,"Asphalt",Asphalt,12);ui.road=ui.asphalt.rectTransform;Place(ui.road,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,36),new Vector2(0,58));
    var kerbTop=N.Image(ui.road,"Kerb",new Color(1,1,1,.85f),2);Place(kerbTop.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-4),new Vector2(-16,3));
    var kerbBottom=N.Image(ui.road,"Kerb",new Color(1,1,1,.85f),2);Place(kerbBottom.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,4),new Vector2(-16,3));
    ui.trailImage=N.Image(ui.road,"Trail",new Color(.36f,.75f,.24f,.9f),5);ui.trail=ui.trailImage.rectTransform;ui.trail.anchorMin=new Vector2(0,.5f);ui.trail.anchorMax=new Vector2(0,.5f);ui.trail.pivot=new Vector2(0,.5f);ui.trail.anchoredPosition=new Vector2(8,0);ui.trail.sizeDelta=new Vector2(0,10);
    ui.dashes=N.Node("Dashes",ui.road);Stretch(ui.dashes,new Vector2(10,0),new Vector2(-10,0));
    for(int i=0;i<22;i++){var d=N.Image(ui.dashes,"Dash",Dash,2);var dr=d.rectTransform;dr.anchorMin=dr.anchorMax=new Vector2((i+.5f)/22f,.5f);dr.sizeDelta=new Vector2(16,4);}
    ui.trail.SetAsLastSibling();

    // Truck with the cargo bubble, the box that hops, smoke puffs.
    for(int i=0;i<5;i++){var p=N.Image(ra,"Puff",new Color(1,1,1,0),0);p.sprite=U.Glow();p.rectTransform.sizeDelta=new Vector2(26,26);ui.puffs.Add(p);ui.puffAge.Add(99);}
    ui.truckImage=N.Image(ra,"Truck",Color.white,0);ui.truckImage.preserveAspect=true;ui.truck=ui.truckImage.rectTransform;ui.truck.anchorMin=ui.truck.anchorMax=new Vector2(0,0);ui.truck.pivot=new Vector2(.5f,0);ui.truck.sizeDelta=new Vector2(118,78);
    var shadow=N.Image(ui.truck,"Shadow",new Color(0,0,0,.28f),0);shadow.sprite=U.Glow();Place(shadow.rectTransform,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(.5f,.5f),new Vector2(0,6),new Vector2(130,20));shadow.transform.SetAsFirstSibling();
    // The cargo: the product on a round sticker on the side of the truck's box.
    var bubble=N.Image(ui.truck,"Cargo",new Color(1,1,1,.96f),20);ui.bubble=bubble.rectTransform;Place(ui.bubble,new Vector2(.3f,.56f),new Vector2(.3f,.56f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(40,40));
    var ring=N.Image(ui.bubble,"Ring",K.C("F2B03D"),20);Stretch(ring.rectTransform,new Vector2(-3,-3),new Vector2(3,3));ring.transform.SetAsFirstSibling();
    ui.bubbleIcon=N.Image(ui.bubble,"Icon",Color.white,0);ui.bubbleIcon.preserveAspect=true;Stretch(ui.bubbleIcon.rectTransform,new Vector2(4,4),new Vector2(-4,-4));
    ui.boxImage=N.Image(ra,"Box",Color.white,0);ui.boxImage.sprite=K.Icon("Game/cardboard_box");ui.boxImage.preserveAspect=true;ui.box=ui.boxImage.rectTransform;ui.box.anchorMin=ui.box.anchorMax=Vector2.zero;ui.box.sizeDelta=new Vector2(30,30);

    // Locked lane: a shade and a padlock over the road.
    ui.shade=N.Image(ra,"Shade",new Color(.42f,.36f,.3f,.55f),12);Place(ui.shade.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,24),new Vector2(0,82));
    ui.lockIcon=N.Image(ra,"Lock",Color.white,0);ui.lockIcon.sprite=K.Icon("Icons/lock");ui.lockIcon.preserveAspect=true;ui.lockRect=ui.lockIcon.rectTransform;Place(ui.lockRect,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(.5f,.5f),new Vector2(0,70),new Vector2(56,56));

    // Header over the road: product, name, status ribbon, the clock.
    var head=N.Node("Head",ra);Place(head,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-6),new Vector2(0,44));
    ui.title=N.Text(head,"Title",K.Headline,20,K.Ink);ui.title.textWrappingMode=TextWrappingModes.NoWrap;ui.title.overflowMode=TextOverflowModes.Ellipsis;ui.titleRect=ui.title.rectTransform;
    Place(ui.titleRect,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(0,0),new Vector2(-250,26));
    ui.subtitle=N.Text(head,"Subtitle",K.Body,13,K.Muted);ui.subtitle.textWrappingMode=TextWrappingModes.NoWrap;ui.subtitle.overflowMode=TextOverflowModes.Ellipsis;
    Place(ui.subtitle.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(0,-26),new Vector2(-250,18));
    ui.ribbon=Pill(head,"Ribbon",K.C("E15533"),out ui.ribbonText,13,K.Label);ui.ribbonText.characterSpacing=2;ui.ribbonRect=ui.ribbon.rectTransform;Place(ui.ribbonRect,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(-108,-2),new Vector2(110,26));
    ui.timer=Pill(head,"Timer",new Color(.17f,.13f,.09f,.88f),out ui.timerText,15,K.Number);ui.timerRect=ui.timer.rectTransform;Place(ui.timerRect,new Vector2(1,1),new Vector2(1,1),new Vector2(1,1),new Vector2(0,-2),new Vector2(98,26));
    ui.status=N.Text(ra,"Status",K.Number,13,K.Ink);ui.status.alignment=TextAlignmentOptions.Center;ui.status.textWrappingMode=TextWrappingModes.NoWrap;
    Place(ui.status.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,3),new Vector2(0,20));
    ui.lockText=N.Text(ra,"Lock text",K.Headline,16,Color.white);ui.lockText.alignment=TextAlignmentOptions.Center;ui.lockText.outlineWidth=.2f;ui.lockText.outlineColor=new Color32(60,40,20,200);
    Place(ui.lockText.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(.5f,0),new Vector2(0,28),new Vector2(0,22));

    // Buttons on the right.
    var col=N.Node("Buttons",f);Place(col,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-12,-2),new Vector2(222,150));
    var v=N.Column(col.gameObject,8);v.childAlignment=TextAnchor.MiddleCenter;v.childForceExpandHeight=false;
    for(int i=0;i<2;i++){var b=CheckoutDesktopButton.Create(col,52,16,14);b.Clicked=hud.BoardPress;ui.buttons.Add(b);}
    return ui;
   }

   public void Apply(DesktopTile t){
    bool changed=data==null||data.id!=t.id;data=t;Id=t.id;lane=t.lane??"";
    bool locked=lane=="locked",free=lane=="free",dock=lane=="dock";
    face.color=locked?K.C("EFE6D8"):dock?ToneFace("success"):K.Cream;
    edge.color=dock?K.C("7DB357"):locked?K.C("BCAE97"):K.Border;
    var o=K.Icon(t.origin);origin.sprite=o;origin.enabled=o;
    originSign.sprite=K.Icon(locked?"Icons/lock":"Icons/cart");originSign.gameObject.SetActive(!o);
    originLabel.text=o?K.Clean(t.originLabel).ToUpperInvariant():locked?"NOVA ROTA":"ESCOLHA O FORNECEDOR";
    var v=K.Icon(string.IsNullOrEmpty(t.vehicle)?"Game/lane_truck":t.vehicle);truckImage.sprite=v;truckImage.enabled=v;
    truckImage.color=locked?new Color(.45f,.4f,.35f,.55f):Color.white;
    var icon=K.Icon(t.icon);bubbleIcon.sprite=icon;bubble.gameObject.SetActive(icon&&!free&&!locked);
    title.text=K.Clean(t.title);subtitle.text=K.Clean(t.subtitle);
    bool hasRibbon=!string.IsNullOrEmpty(t.sticker);ribbon.gameObject.SetActive(hasRibbon);
    bool hasTimer=lane=="road"&&t.timerEnd>0;timer.gameObject.SetActive(hasTimer);
    if(hasRibbon){var label=K.Clean(t.sticker);ribbonText.text=label;ribbon.color=ToneStrong(string.IsNullOrEmpty(t.tone)?"info":t.tone);ribbonRect.sizeDelta=new Vector2(PillWidth(ribbonText,label,70),26);
     ribbonRect.anchoredPosition=new Vector2(hasTimer?-106:0,-2);}
    titleRect.sizeDelta=new Vector2(-(hasRibbon?ribbonRect.sizeDelta.x:0)-(hasTimer?110:0)-12,26);
    shade.gameObject.SetActive(locked);lockIcon.gameObject.SetActive(locked);lockText.gameObject.SetActive(locked);
    lockText.text=locked?(t.state=="locked"?K.Clean(t.subtitle):"Compre mais um caminhão"):"";
    dashes.gameObject.SetActive(!locked);
    trailImage.color=dock?new Color(.36f,.75f,.24f,.95f):new Color(.98f,.74f,.2f,.95f);
    progress=dock?1:free?1:locked?.5f:Mathf.Clamp01(t.fill<0?0:t.fill);
    if(changed||progressShown<0)progressShown=progress;
    boxImage.gameObject.SetActive(false);
    var a=t.actions!=null&&t.actions.Length>0?t.actions:(t.action!=null&&!string.IsNullOrEmpty(t.action.label)?new[]{t.action}:new DesktopButton[0]);
    for(int i=0;i<buttons.Count;i++){bool on=i<a.Length;buttons[i].gameObject.SetActive(on);if(on)buttons[i].Apply(a[i]);}
   }

   public void Tick(double now,float t){
    if(data==null)return;
    float w=roadArea.rect.width;if(w<50)return;
    bool locked=lane=="locked",free=lane=="free",dock=lane=="dock",road=lane=="road";
    if(road&&data.timerTotal>0){
     double left=data.timerEnd-now;progress=Mathf.Clamp01(1f-(float)(left/data.timerTotal));
     timerText.text=left>0?Clock(left):"Chegando!";
    }
    progressShown=Mathf.MoveTowards(progressShown,progress,Time.unscaledDeltaTime*.6f);
    // Where the truck stands: loading at the supplier for the first quarter, then along the road.
    float start=70,end=w-70;
    float drive=road?Mathf.InverseLerp(.25f,1f,progressShown):dock||free?1:.5f;
    float x=Mathf.Lerp(start,end,drive);
    bool moving=road&&progressShown>=.25f&&progressShown<1;
    float bob=moving?Mathf.Abs(Mathf.Sin(t*9f))*2.5f:free?Mathf.Sin(t*1.5f)*.8f:0;
    truck.anchoredPosition=new Vector2(x,44+bob);
    truck.localRotation=Quaternion.Euler(0,0,moving?Mathf.Sin(t*9f)*.8f:0);
    bubble.localScale=Vector3.one*(1+.05f*Mathf.Sin(t*3f));
    // The road behind the truck is painted: the loading bar.
    trail.sizeDelta=new Vector2(Mathf.Max(0,(road?x:dock?end:0)-18),10);
    trailImage.gameObject.SetActive(road||dock);
    float pct=road?progressShown:dock?(data.fill<0?0:data.fill):0;
    status.text=road?(progressShown<.25f?$"Carregando no fornecedor · {Mathf.RoundToInt(progressShown*100)}%":$"{Mathf.RoundToInt(progressShown*100)}% do caminho")
     :dock?$"Descarregando · {Mathf.RoundToInt(pct*100)}% guardado":free?"Livre · faça um pedido":"";
    // Smoke puffs behind a moving truck.
    if(moving&&t>=nextPuff){nextPuff=t+.28f;for(int i=0;i<puffs.Count;i++)if(puffAge[i]>1){puffAge[i]=0;puffs[i].rectTransform.anchoredPosition=new Vector2(x-66,58);break;}}
    for(int i=0;i<puffs.Count;i++){
     puffAge[i]+=Time.unscaledDeltaTime;float age=puffAge[i];var p=puffs[i].rectTransform;
     if(age>1){puffs[i].color=new Color(1,1,1,0);continue;}
     p.anchoredPosition+=new Vector2(-28,16)*Time.unscaledDeltaTime;p.localScale=Vector3.one*(.6f+age*1.2f);puffs[i].color=new Color(.92f,.92f,.92f,.55f*(1-age));
    }
    // Boxes hop from the supplier into the truck while loading, from the truck into the market at the dock.
    bool hop=(road&&progressShown<.25f)||dock;
    boxImage.gameObject.SetActive(hop);
    if(hop){
     boxAt=(boxAt+Time.unscaledDeltaTime*1.4f)%1f;
     float from=road?-40:x+40,to=road?x-40:w+40;
     box.anchoredPosition=new Vector2(Mathf.Lerp(from,to,boxAt),62+Mathf.Sin(boxAt*Mathf.PI)*36);
     box.localRotation=Quaternion.Euler(0,0,boxAt*-200);
    }
    if(locked)lockRect.anchoredPosition=new Vector2(0,72+Mathf.Sin(t*2f)*3);
    glow.color=dock?new Color(.5f,.95f,.4f,.3f+.2f*Mathf.Sin(t*4f)):new Color(1,.85f,.3f,0);
    market.rectTransform.localScale=Vector3.one*(dock?1+.03f*Mathf.Sin(t*4f):1);
   }
  }

  // A lane that just turned into "dock" (the truck arrived while the window is open) honks and sparkles.
  void LaneArrived(BoardLaneUi lane){
   Sound("success");
   var space=(RectTransform)boardWin.transform;
   U.Sparkles(this,space,U.PointIn(space,(RectTransform)lane.transform),12,180);
   StartCoroutine(U.Pop(lane.transform,1.03f,.25f));
  }
 }
}
