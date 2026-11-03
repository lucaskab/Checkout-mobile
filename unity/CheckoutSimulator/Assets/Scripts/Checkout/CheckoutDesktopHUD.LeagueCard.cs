using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // The end of a league week (DesktopView.leagueCard, desktop/pages/ranking.ts leagueCardView), redesigned 03/11 as a
 // real celebration (Lucas: "bem minimalista, bem feinha"). A navy stage with a slowly turning golden sunburst and two
 // soft spotlights; a ribbon banner "FIM DA LIGA" (the ribbon drawn by the UI, the words a label); chunky marble
 // plinths with a gold trim and a big numeral, the group's real top three (round faces and names from the item's
 // `top`), me with a glow ring and a "VOCÊ" tag, or my place on a card under the podium; the division change (the old
 // badge greys and shrinks, chevrons run, the new badge pops in with a glow and a stamped SUBIU! / CAIU / MANTEVE; a
 // move down is soft blue and encouraging, never red); big rewards (diamonds, a chest that shakes and bursts open
 // with coins); a stats row (points, place of N, players passed). "Pegar prêmios" flies the diamonds and coins to the
 // counters, which tick up, then the card closes. Confetti and sparkles live in a layer BEHIND every label.
 public partial class CheckoutDesktopHUD {
  const float LeagueW=960,LeagueH=640;
  RectTransform leagueRoot,leaguePanel,leagueStage,leagueFx,leagueFlyLayer,leagueRibbon,leaguePodiumBox,leagueMeBox,leagueDivision,leagueChevrons,leagueStamp,leagueRewards,leagueDiamondBox,leagueChestBox,leagueChestLid,leagueStatsRow;
  Image leagueDim,leagueRays,leagueFrom,leagueTo,leagueToGlow,leagueMeFace,leagueStampFrame,leagueChestGlow;readonly List<Image> leagueSpots=new List<Image>();readonly List<Image> leagueChevronParts=new List<Image>();
  TextMeshProUGUI leagueHeadline,leagueTitle,leagueSubtitle,leagueMoved,leagueDiamonds,leagueCoins,leaguePlaceText,leagueMeName,leagueStampText;
  CheckoutDesktopButton leagueButton;CanvasGroup leaguePanelGroup;
  readonly List<LeaguePlace> leaguePodium=new List<LeaguePlace>();
  readonly List<(RectTransform root,Image icon,TextMeshProUGUI value,TextMeshProUGUI label)> leagueStats=new List<(RectTransform,Image,TextMeshProUGUI,TextMeshProUGUI)>();
  string leagueShownKey,leagueClosedKey;Coroutine leagueRun;DesktopLeagueCard leagueData;bool leagueCollecting;
  public bool LeagueCardOpen=>leagueRoot&&leagueRoot.gameObject.activeSelf;
  static readonly Color LeagueUp=K.C("7FCB5A"),LeagueDown=K.C("8EC3E8"),LeagueSame=K.C("F3C64E");

  sealed class LeaguePlace{public RectTransform col,holder;public Image face,ring,rim,glow;public TextMeshProUGUI name,points;public RectTransform tag;}

  void BuildLeagueCard(){
   leagueRoot=N.Node("League card",root);Stretch(leagueRoot,Vector2.zero,Vector2.zero);
   leagueDim=leagueRoot.gameObject.AddComponent<Image>();leagueDim.color=new Color(.04f,.06f,.13f,.84f);
   leaguePanel=N.Node("Panel",leagueRoot);leaguePanel.anchorMin=leaguePanel.anchorMax=leaguePanel.pivot=new Vector2(.5f,.5f);leaguePanel.sizeDelta=new Vector2(LeagueW,LeagueH);
   leaguePanelGroup=leaguePanel.gameObject.AddComponent<CanvasGroup>();
   // the frame: a thin gold trim around the navy stage
   var edge=N.Image(leaguePanel,"Edge",RankGoldTrim,30);Stretch(edge.rectTransform,Vector2.zero,Vector2.zero);
   var face=N.Image(edge.transform,"Face",RankNavy,28);Stretch(face.rectTransform,new Vector2(3,3),new Vector2(-3,-3));
   face.gameObject.AddComponent<RectMask2D>();
   leagueStage=face.rectTransform;
   // behind everything: the sunburst, two spotlights, a warm glow, then the confetti layer (still under every label)
   leagueRays=N.Image(leagueStage,"Rays",new Color(1f,.84f,.4f,.0f),0);leagueRays.sprite=LevelRaysSprite();U.At(leagueRays.rectTransform,new Vector2(.5f,.6f),new Vector2(1100,1100));
   var warm=N.Image(leagueStage,"Warm",new Color(.4f,.55f,.95f,.22f),0);warm.sprite=U.Glow();U.At(warm.rectTransform,new Vector2(.5f,.55f),new Vector2(900,640));
   foreach(var side in new[]{-1,1}){
    var spot=N.Image(leagueStage,"Spot",new Color(1f,.95f,.78f,.0f),0);spot.sprite=CheckoutRankArt.Spotlight();var r=spot.rectTransform;
    r.anchorMin=r.anchorMax=new Vector2(side<0?.1f:.9f,1);r.pivot=new Vector2(.5f,1);r.sizeDelta=new Vector2(380,560);r.anchoredPosition=new Vector2(0,30);r.localRotation=Quaternion.Euler(0,0,side*-24);
    leagueSpots.Add(spot);
   }
   var vignette=N.Image(leagueStage,"Vignette",new Color(0,0,0,.35f),0);vignette.sprite=U.Vignette();Stretch(vignette.rectTransform,Vector2.zero,Vector2.zero);
   leagueFx=N.Node("Fx",leagueStage);Stretch(leagueFx,Vector2.zero,Vector2.zero);
   // texts
   leagueTitle=N.Text(leagueStage,"Title",K.Headline,42,Color.white);leagueTitle.alignment=TextAlignmentOptions.Center;leagueTitle.textWrappingMode=TextWrappingModes.NoWrap;leagueTitle.enableAutoSizing=true;leagueTitle.fontSizeMin=22;leagueTitle.fontSizeMax=42;
   leagueTitle.outlineWidth=.12f;leagueTitle.outlineColor=new Color32(12,20,45,255);
   U.Stretch(leagueTitle.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(40,-136),new Vector2(-40,-84));
   leagueSubtitle=N.Text(leagueStage,"Subtitle",K.Body,19,RankCream);leagueSubtitle.alignment=TextAlignmentOptions.Center;U.Stretch(leagueSubtitle.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(40,-164),new Vector2(-40,-136));
   BuildLeaguePodium();
   BuildLeagueDivision();
   BuildLeagueRewards();
   // the stats row
   leagueStatsRow=N.Node("Stats",leagueStage);leagueStatsRow.anchorMin=new Vector2(0,0);leagueStatsRow.anchorMax=new Vector2(1,0);leagueStatsRow.pivot=new Vector2(.5f,0);leagueStatsRow.offsetMin=new Vector2(40,84);leagueStatsRow.offsetMax=new Vector2(-40,136);
   var srow=N.Row(leagueStatsRow.gameObject,14);srow.childAlignment=TextAnchor.MiddleCenter;srow.childForceExpandWidth=true;srow.childControlHeight=true;srow.childForceExpandHeight=true;
   for(int i=0;i<3;i++){
    var chipEdge=N.Image(leagueStatsRow,"Stat",new Color(.95f,.78f,.3f,.55f),18);
    var chipFace=N.Image(chipEdge.transform,"Face",K.C("2A3D6B"),16);Stretch(chipFace.rectTransform,new Vector2(2,2),new Vector2(-2,-2));
    var icon=N.Image(chipFace.transform,"Icon",Color.white,0);icon.preserveAspect=true;U.At(icon.rectTransform,new Vector2(0,.5f),new Vector2(34,34),new Vector2(28,0));
    var value=U.Label(chipFace.transform,"Value",K.Number,22,"FFFFFF",TextAlignmentOptions.MidlineLeft);U.Stretch(value.rectTransform,new Vector2(0,.42f),Vector2.one,new Vector2(54,0),new Vector2(-8,2));
    value.overflowMode=TextOverflowModes.Overflow;value.enableAutoSizing=true;value.fontSizeMin=13;value.fontSizeMax=22;
    var label=U.Label(chipFace.transform,"Label",K.Label,12,"F7E8C8",TextAlignmentOptions.MidlineLeft);label.enableAutoSizing=true;label.fontSizeMin=9;label.fontSizeMax=12;label.overflowMode=TextOverflowModes.Overflow;U.Stretch(label.rectTransform,new Vector2(0,0),new Vector2(1,.44f),new Vector2(54,3),new Vector2(-8,0));
    leagueStats.Add((chipEdge.rectTransform,icon,value,label));
   }
   leagueButton=CheckoutDesktopButton.Create(leagueStage,64,24,18);var br=(RectTransform)leagueButton.transform;Destroy(leagueButton.GetComponent<LayoutElement>());
   br.anchorMin=br.anchorMax=br.pivot=new Vector2(.5f,0);br.sizeDelta=new Vector2(360,64);br.anchoredPosition=new Vector2(0,16);
   leagueButton.Clicked=_=>CloseLeagueCard();
   // the ribbon banner on top of the frame (half out of it): drawn by the UI, the words a label
   leagueRibbon=N.Node("Ribbon",leaguePanel);U.At(leagueRibbon,new Vector2(.5f,1),new Vector2(500,74),new Vector2(0,-12));
   foreach(var side in new[]{-1,1}){
    var tail=N.Image(leagueRibbon,"Tail",K.C("B8531F"),0);tail.sprite=LevelTailSprite();var tr=tail.rectTransform;
    tr.anchorMin=tr.anchorMax=new Vector2(side<0?0:1,.5f);tr.pivot=new Vector2(.5f,.5f);tr.sizeDelta=new Vector2(120,58);tr.anchoredPosition=new Vector2(side*30,-24);tr.localScale=new Vector3(side<0?1:-1,1,1);
    var fold=N.Image(leagueRibbon,"Fold",K.C("7A3412"),0);fold.sprite=LevelFoldSprite();var fr=fold.rectTransform;
    fr.anchorMin=fr.anchorMax=new Vector2(side<0?0:1,.5f);fr.pivot=new Vector2(.5f,1);fr.sizeDelta=new Vector2(36,18);fr.anchoredPosition=new Vector2(-side*18,-37);fr.localScale=new Vector3(side<0?1:-1,1,1);
   }
   var bandEdge=N.Image(leagueRibbon,"Trim",RankGoldTrim,14);U.Stretch(bandEdge.rectTransform,Vector2.zero,Vector2.one,new Vector2(-3,-3),new Vector2(3,3));
   var band=N.Image(leagueRibbon,"Band",RankOrange,12);U.Stretch(band.rectTransform,Vector2.zero,Vector2.one);
   var bandShade=N.Image(band.transform,"Shade",K.C("C55E26"),12);U.Stretch(bandShade.rectTransform,Vector2.zero,new Vector2(1,.34f));
   var bandShine=N.Image(band.transform,"Shine",new Color(1,1,1,.22f),8);U.Stretch(bandShine.rectTransform,new Vector2(0,.7f),Vector2.one,new Vector2(10,0),new Vector2(-10,-5));
   leagueHeadline=U.Label(band.transform,"Text",K.Headline,34,"FFF6E2");U.Stretch(leagueHeadline.rectTransform,Vector2.zero,Vector2.one,new Vector2(12,4),new Vector2(-12,-2));
   leagueHeadline.characterSpacing=4;leagueHeadline.outlineWidth=.16f;leagueHeadline.outlineColor=new Color32(120,46,14,255);leagueHeadline.enableAutoSizing=true;leagueHeadline.fontSizeMin=18;leagueHeadline.fontSizeMax=34;
   leagueFlyLayer=N.Node("Fly",leagueRoot);Stretch(leagueFlyLayer,Vector2.zero,Vector2.zero);
   leagueRoot.gameObject.SetActive(false);
  }

  void BuildLeaguePodium(){
   leaguePodiumBox=N.Node("Podium",leagueStage);leaguePodiumBox.anchorMin=new Vector2(0,0);leaguePodiumBox.anchorMax=new Vector2(.52f,0);leaguePodiumBox.pivot=new Vector2(.5f,0);
   leaguePodiumBox.offsetMin=new Vector2(30,154);leaguePodiumBox.offsetMax=new Vector2(0,462);
   var floor=N.Image(leaguePodiumBox,"Floor",new Color(0,0,0,.4f),0);floor.sprite=U.Glow();U.Stretch(floor.rectTransform,new Vector2(.02f,0),new Vector2(.98f,0),new Vector2(0,-16),new Vector2(0,22));
   for(int place=1;place<=3;place++){
    int i=place-1;float x=place==1?.5f:place==2?.17f:.83f,plinthH=place==1?112:place==2?88:76,size=place==1?100:84;
    var p=new LeaguePlace();
    var col=N.Node("Place "+place,leaguePodiumBox);col.anchorMin=new Vector2(x,0);col.anchorMax=new Vector2(x,1);col.pivot=new Vector2(.5f,0);col.sizeDelta=new Vector2(156,0);col.anchoredPosition=Vector2.zero;p.col=col;
    // the chunky plinth: dark edge, marble face, gold trim, a big painted numeral with its shadow
    var plinth=N.Image(col,"Plinth",PlinthEdge[i],14);U.Stretch(plinth.rectTransform,new Vector2(0,0),new Vector2(1,0),Vector2.zero,new Vector2(0,plinthH));
    var pf=N.Image(plinth.transform,"Face",PlinthFace[i],0);pf.sprite=CheckoutRankArt.Plinth();pf.type=Image.Type.Sliced;Stretch(pf.rectTransform,new Vector2(5,7),new Vector2(-5,-9));
    var trim=N.Image(plinth.transform,"Trim",RankGoldTrim,3);U.Stretch(trim.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(2,-9),new Vector2(-2,-1));
    var trimShine=N.Image(trim.transform,"Shine",new Color(1,1,1,.55f),2);U.Stretch(trimShine.rectTransform,new Vector2(0,.55f),Vector2.one,new Vector2(3,0),new Vector2(-3,-1));
    var shadowNum=N.Text(pf.transform,"NumberShadow",K.Headline,place==1?66:place==2?54:46,new Color(.3f,.18f,.06f,.35f));shadowNum.text=place.ToString();shadowNum.alignment=TextAlignmentOptions.Center;U.Stretch(shadowNum.rectTransform,new Vector2(0,.32f),Vector2.one,new Vector2(3,-4),new Vector2(3,-4));
    var num=N.Text(pf.transform,"Number",K.Headline,place==1?66:place==2?54:46,Color.white);num.text=place.ToString();num.alignment=TextAlignmentOptions.Center;num.outlineWidth=.24f;num.outlineColor=new Color32(110,66,22,230);U.Stretch(num.rectTransform,new Vector2(0,.32f),Vector2.one);
    p.points=U.Label(pf.transform,"Points",K.Number,15,"4A3624");U.Stretch(p.points.rectTransform,Vector2.zero,new Vector2(1,.34f),new Vector2(4,1),new Vector2(-4,2));
    p.points.overflowMode=TextOverflowModes.Overflow;p.points.enableAutoSizing=true;p.points.fontSizeMin=10;p.points.fontSizeMax=15;
    // the face (glow ring for me, a crown on #1), then the name over the plinth
    var holder=N.Node("Face",col);holder.anchorMin=holder.anchorMax=new Vector2(.5f,0);holder.pivot=new Vector2(.5f,0);holder.sizeDelta=new Vector2(size,size);holder.anchoredPosition=new Vector2(0,plinthH+30);p.holder=holder;
    p.glow=N.Image(holder,"Glow",new Color(1f,.85f,.35f,0),0);p.glow.sprite=U.Glow();U.At(p.glow.rectTransform,new Vector2(.5f,.5f),new Vector2(size*1.9f,size*1.9f));
    p.ring=N.Image(holder,"Ring",PlinthEdge[i],0);p.ring.sprite=K.Disc();Stretch(p.ring.rectTransform,new Vector2(-6,-6),new Vector2(6,6));
    var plate=N.Image(holder,"Plate",K.C("2A3D6B"),0);plate.sprite=K.Disc();Stretch(plate.rectTransform,Vector2.zero,Vector2.zero);
    var clip=K.RoundClip(holder,"Clip");K.SetRound(clip,true);
    p.face=N.Image(clip.transform,"Icon",Color.white,0);p.face.preserveAspect=true;Stretch(p.face.rectTransform,Vector2.zero,Vector2.zero);
    p.rim=N.Image(holder,"Rim",PlinthFace[i],0);K.FitRim(p.rim,size,5);
    var medal=N.Image(holder,"Medal",place==1?Color.white:place==2?K.C("D7DEE6"):K.C("E9A46A"),0);medal.sprite=K.Icon("Icons/medal");medal.preserveAspect=true;U.At(medal.rectTransform,new Vector2(.1f,.1f),new Vector2(size*.36f,size*.36f));
    if(place==1){var crown=N.Image(holder,"Crown",Color.white,0);crown.sprite=K.Icon("Icons/crown");crown.preserveAspect=true;U.At(crown.rectTransform,new Vector2(.5f,1),new Vector2(58,58),new Vector2(0,12));crown.rectTransform.localRotation=Quaternion.Euler(0,0,-8);}
    // "VOCÊ" on my face: an orange tag with a gold edge
    var tagEdge=N.Image(holder,"Tag",RankGoldTrim,12);p.tag=tagEdge.rectTransform;U.At(p.tag,new Vector2(.5f,1),new Vector2(78,26),new Vector2(0,place==1?36:8));
    var tagFace=N.Image(tagEdge.transform,"Face",RankOrange,10);Stretch(tagFace.rectTransform,new Vector2(2,2),new Vector2(-2,-2));
    var tagText=U.Label(tagFace.transform,"Text",K.Headline,15,"FFFFFF");Stretch(tagText.rectTransform,Vector2.zero,Vector2.zero);tagText.characterSpacing=2;tagText.text="VOCÊ";
    p.name=U.Label(col,"Name",K.Label,15,"F7E8C8");U.Stretch(p.name.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(-2,plinthH+4),new Vector2(2,plinthH+26));
    p.name.enableAutoSizing=true;p.name.fontSizeMin=10;p.name.fontSizeMax=15;
    leaguePodium.Add(p);
   }
   // my place when it is not on the podium: a highlighted card with my face, "#12" and my name
   leagueMeBox=N.Node("Me",leagueStage);leagueMeBox.anchorMin=leagueMeBox.anchorMax=new Vector2(.27f,0);leagueMeBox.pivot=new Vector2(.5f,0);leagueMeBox.sizeDelta=new Vector2(360,58);leagueMeBox.anchoredPosition=new Vector2(10,154);
   var meEdge=N.Image(leagueMeBox,"Edge",RankGoldTrim,26);Stretch(meEdge.rectTransform,Vector2.zero,Vector2.zero);
   var meBack=N.Image(meEdge.transform,"Back",K.C("FFF4D6"),24);Stretch(meBack.rectTransform,new Vector2(3,3),new Vector2(-3,-3));
   var meRing=N.Image(leagueMeBox,"Ring",RankOrange,0);meRing.sprite=K.Disc();U.At(meRing.rectTransform,new Vector2(0,.5f),new Vector2(52,52),new Vector2(34,0));
   var meClip=K.RoundClip(meRing.transform,"Clip");K.SetRound(meClip,true);var mcr=meClip.rectTransform;mcr.offsetMin=new Vector2(3,3);mcr.offsetMax=new Vector2(-3,-3);
   var mePlate=N.Image(meClip.transform,"Plate",K.C("2A3D6B"),0);mePlate.sprite=K.Disc();Stretch(mePlate.rectTransform,Vector2.zero,Vector2.zero);
   leagueMeFace=N.Image(meClip.transform,"Icon",Color.white,0);leagueMeFace.preserveAspect=true;Stretch(leagueMeFace.rectTransform,Vector2.zero,Vector2.zero);
   var meRim=N.Image(meRing.transform,"Rim",RankOrange,0);K.FitRim(meRim,46,3);
   leaguePlaceText=U.Label(leagueMeBox,"Place",K.Headline,30,"1D2B4F",TextAlignmentOptions.MidlineLeft);U.Stretch(leaguePlaceText.rectTransform,Vector2.zero,new Vector2(0,1),new Vector2(68,0),new Vector2(150,0));
   leagueMeName=U.Label(leagueMeBox,"Name",K.Label,15,"4A3624",TextAlignmentOptions.MidlineLeft);U.Stretch(leagueMeName.rectTransform,Vector2.zero,Vector2.one,new Vector2(150,0),new Vector2(-14,0));
  }

  void BuildLeagueDivision(){
   leagueDivision=N.Node("Division",leagueStage);leagueDivision.anchorMin=new Vector2(.52f,0);leagueDivision.anchorMax=new Vector2(1,1);leagueDivision.offsetMin=new Vector2(0,292);leagueDivision.offsetMax=new Vector2(-30,-170);
   leagueFrom=N.Image(leagueDivision,"From",Color.white,0);leagueFrom.preserveAspect=true;U.At(leagueFrom.rectTransform,new Vector2(.17f,.6f),new Vector2(104,104));
   // three chevrons running from the old badge to the new one
   leagueChevrons=N.Node("Chevrons",leagueDivision);U.At(leagueChevrons,new Vector2(.42f,.6f),new Vector2(96,40));
   for(int k=0;k<3;k++){var ch=N.Image(leagueChevrons,"Chevron",LeagueUp,0);ch.sprite=CheckoutRankArt.Chevron();U.At(ch.rectTransform,new Vector2(.5f,.5f),new Vector2(32,36),new Vector2(-28+k*28,0));leagueChevronParts.Add(ch);}
   leagueToGlow=N.Image(leagueDivision,"Glow",new Color(1f,.9f,.5f,0),0);leagueToGlow.sprite=U.Glow();U.At(leagueToGlow.rectTransform,new Vector2(.72f,.6f),new Vector2(280,280));
   leagueTo=N.Image(leagueDivision,"To",Color.white,0);leagueTo.preserveAspect=true;U.At(leagueTo.rectTransform,new Vector2(.72f,.6f),new Vector2(150,150));
   // the stamp over the new badge: a rotated frame with the word as a label
   leagueStamp=N.Node("Stamp",leagueDivision);U.At(leagueStamp,new Vector2(.72f,.28f),new Vector2(170,46));leagueStamp.localRotation=Quaternion.Euler(0,0,-8);
   var stampBack=N.Image(leagueStamp,"Back",new Color(.11f,.17f,.31f,.85f),12);Stretch(stampBack.rectTransform,new Vector2(4,4),new Vector2(-4,-4));
   leagueStampFrame=N.Image(leagueStamp,"Frame",LeagueUp,0);leagueStampFrame.sprite=CheckoutRankArt.Stamp();leagueStampFrame.type=Image.Type.Sliced;Stretch(leagueStampFrame.rectTransform,Vector2.zero,Vector2.zero);
   leagueStampText=U.Label(leagueStamp,"Text",K.Headline,26,"FFFFFF");Stretch(leagueStampText.rectTransform,new Vector2(8,2),new Vector2(-8,-2));leagueStampText.characterSpacing=3;leagueStampText.enableAutoSizing=true;leagueStampText.fontSizeMin=14;leagueStampText.fontSizeMax=26;
   leagueMoved=N.Text(leagueDivision,"Moved",K.Headline,21,Color.white);leagueMoved.alignment=TextAlignmentOptions.Center;leagueMoved.textWrappingMode=TextWrappingModes.NoWrap;leagueMoved.enableAutoSizing=true;leagueMoved.fontSizeMin=13;leagueMoved.fontSizeMax=21;
   U.Stretch(leagueMoved.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(0,-26),new Vector2(0,2));
  }

  void BuildLeagueRewards(){
   leagueRewards=N.Node("Rewards",leagueStage);leagueRewards.anchorMin=new Vector2(.52f,0);leagueRewards.anchorMax=new Vector2(1,0);leagueRewards.pivot=new Vector2(.5f,0);leagueRewards.offsetMin=new Vector2(0,140);leagueRewards.offsetMax=new Vector2(-30,222);
   // diamonds: the painted diamond big, a glow behind it, the number counting up
   leagueDiamondBox=N.Node("Diamonds",leagueRewards);leagueDiamondBox.anchorMin=new Vector2(0,0);leagueDiamondBox.anchorMax=new Vector2(.5f,1);leagueDiamondBox.offsetMin=leagueDiamondBox.offsetMax=Vector2.zero;
   var dGlow=N.Image(leagueDiamondBox,"Glow",new Color(.5f,.8f,1f,.35f),0);dGlow.sprite=U.Glow();U.At(dGlow.rectTransform,new Vector2(.3f,.5f),new Vector2(150,150));
   var dIcon=N.Image(leagueDiamondBox,"Icon",Color.white,0);dIcon.sprite=K.Icon("Icons/diamond");dIcon.preserveAspect=true;U.At(dIcon.rectTransform,new Vector2(.3f,.5f),new Vector2(70,70));
   leagueDiamonds=U.Label(leagueDiamondBox,"Value",K.Number,36,"FFFFFF",TextAlignmentOptions.MidlineLeft);U.Stretch(leagueDiamonds.rectTransform,new Vector2(.3f,0),Vector2.one,new Vector2(46,0),Vector2.zero);
   leagueDiamonds.outlineWidth=.12f;leagueDiamonds.outlineColor=new Color32(12,20,45,255);
   // the chest (PLACEHOLDER parts drawn in code): it shakes, the lid flies open and coins burst out
   leagueChestBox=N.Node("Chest",leagueRewards);leagueChestBox.anchorMin=new Vector2(.5f,0);leagueChestBox.anchorMax=new Vector2(1,1);leagueChestBox.offsetMin=leagueChestBox.offsetMax=Vector2.zero;
   leagueChestGlow=N.Image(leagueChestBox,"Glow",new Color(1f,.82f,.35f,0),0);leagueChestGlow.sprite=U.Glow();U.At(leagueChestGlow.rectTransform,new Vector2(.3f,.55f),new Vector2(170,170));
   var chest=N.Node("Box",leagueChestBox);U.At(chest,new Vector2(.3f,.38f),new Vector2(92,64));
   var body=N.Image(chest,"Body",K.C("A86A37"),0);body.sprite=CheckoutRankArt.ChestBody();Stretch(body.rectTransform,Vector2.zero,Vector2.zero);
   leagueChestLid=N.Node("Lid",chest);leagueChestLid.anchorMin=leagueChestLid.anchorMax=new Vector2(.5f,1);leagueChestLid.pivot=new Vector2(.05f,0);leagueChestLid.sizeDelta=new Vector2(96,40);leagueChestLid.anchoredPosition=new Vector2(-44,-4);
   var lid=N.Image(leagueChestLid,"Lid",K.C("94592B"),0);lid.sprite=CheckoutRankArt.ChestLid();Stretch(lid.rectTransform,Vector2.zero,Vector2.zero);
   var lock_=N.Image(chest,"Lock",RankGoldTrim,4);U.At(lock_.rectTransform,new Vector2(.5f,.72f),new Vector2(16,18));
   leagueCoins=U.Label(leagueChestBox,"Value",K.Number,36,"FFFFFF",TextAlignmentOptions.MidlineLeft);U.Stretch(leagueCoins.rectTransform,new Vector2(.3f,0),Vector2.one,new Vector2(52,0),Vector2.zero);
   leagueCoins.outlineWidth=.12f;leagueCoins.outlineColor=new Color32(12,20,45,255);
   var coinMini=N.Image(leagueChestBox,"Coin",Color.white,0);coinMini.sprite=K.Icon("Icons/coin");coinMini.preserveAspect=true;U.At(coinMini.rectTransform,new Vector2(.3f,.5f),new Vector2(30,30),new Vector2(36,-26));
  }

  void ApplyLeagueCard(DesktopView v){
   var card=v.leagueCard;
   bool has=card!=null&&!string.IsNullOrEmpty(card.key)&&card.key!=leagueClosedKey&&!CheckoutSocial.Visiting;
   if(!has){if(LeagueCardOpen&&!leagueCollecting&&(card==null||string.IsNullOrEmpty(card.key)))HideLeagueCard();return;}
   if(card.key==leagueShownKey&&LeagueCardOpen)return;
   // the level-up and the conquest celebrations go first; the next view brings this back
   if(LevelUpOpen||ConquestOpen)return;
   leagueShownKey=card.key;leagueData=card;
   if(leagueRun!=null)StopCoroutine(leagueRun);
   leagueRun=StartCoroutine(PlayLeagueCard(card));
  }
  void CloseLeagueCard(){
   if(string.IsNullOrEmpty(leagueShownKey)||leagueCollecting)return;
   leagueClosedKey=leagueShownKey;
   Silent.Add(host.Action("rankingDismissCard","[\""+leagueShownKey+"\"]",""));
   if(leagueRun!=null){StopCoroutine(leagueRun);leagueRun=null;}
   StartCoroutine(CollectLeaguePrizes());
  }
  void HideLeagueCard(){
   if(leagueRun!=null){StopCoroutine(leagueRun);leagueRun=null;}
   leagueCollecting=false;
   foreach(var p in rankConfetti)if(p.rect&&(p.rect.parent==leagueFx||p.rect.parent==leagueFlyLayer))Destroy(p.rect.gameObject);
   if(leagueRoot)leagueRoot.gameObject.SetActive(false);
   // the toasts held while it was open come now
   if(socialToastBox&&!socialToastBox.gameObject.activeSelf)NextSocialToast();
  }
  /// <summary>QA: the card on screen (its key, "" = none).</summary>
  public string LeagueCardQa=>LeagueCardOpen?leagueShownKey:"";
  /// <summary>QA: the podium's names ("|"-joined) and how many of its places show a real face (not the medal).</summary>
  public string LeagueCardPodiumQa{get{
   if(!LeagueCardOpen)return "";
   int faces=0;var names=new List<string>();
   foreach(var p in leaguePodium){names.Add(p.name.text);if(p.face.sprite&&p.face.rectTransform.offsetMin==Vector2.zero&&p.face.enabled)faces++;}
   return string.Join("|",names)+";faces="+faces;
  }}

  IEnumerator PlayLeagueCard(DesktopLeagueCard card){
   leagueRoot.gameObject.SetActive(true);leagueRoot.SetAsLastSibling();leagueCollecting=false;
   if(socialToastBox)socialToastBox.gameObject.SetActive(false);
   // fit the panel on any screen (an iPhone's 680-unit height, an iPad's 4:3): never cut (the ribbon stands 26 above)
   var area=root.rect;float k=Mathf.Min(1f,(area.width-32)/LeagueW,(area.height-52)/LeagueH);
   leaguePanelGroup.alpha=1;
   leagueHeadline.text=K.Clean(card.headline);leagueTitle.text=K.Clean(card.title);leagueSubtitle.text=K.Clean(card.subtitle);
   Color tint=string.IsNullOrEmpty(card.tint)?CheckoutConfettiArt.Gold:K.C(card.tint);
   Color moveColor=card.moved=="up"?LeagueUp:card.moved=="down"?LeagueDown:LeagueSame;
   leagueMoved.text=K.Clean(card.movedText);leagueMoved.color=card.moved=="same"?RankCream:moveColor;
   leagueFrom.sprite=K.Icon(card.badgeFrom);leagueTo.sprite=K.Icon(card.badgeTo);leagueFrom.color=Color.white;
   bool moved=card.moved!="same";leagueFrom.gameObject.SetActive(moved);leagueChevrons.gameObject.SetActive(moved);
   foreach(var ch in leagueChevronParts){ch.color=new Color(moveColor.r,moveColor.g,moveColor.b,0);}
   leagueChevrons.localRotation=Quaternion.Euler(0,0,card.moved=="down"?0:0);
   var to=leagueTo.rectTransform;to.anchorMin=to.anchorMax=new Vector2(moved?.72f:.5f,.6f);
   var tg=leagueToGlow.rectTransform;tg.anchorMin=tg.anchorMax=to.anchorMin;leagueToGlow.color=new Color(tint.r,tint.g,tint.b,0);
   var st=leagueStamp;st.anchorMin=st.anchorMax=new Vector2(moved?.72f:.5f,.28f);
   leagueStampText.text=K.Clean(card.stamp);leagueStampFrame.color=moveColor;leagueStampText.color=card.moved=="same"?LeagueSame:Color.white;
   leagueStamp.localScale=Vector3.zero;
   // the podium: the real top three of the group (a medal on the plate for a place nobody knows)
   bool onPodium=card.place>=1&&card.place<=3;
   for(int i=0;i<3;i++){
    var p=leaguePodium[i];
    string avatar=card.podiumAvatars!=null&&i<card.podiumAvatars.Length?card.podiumAvatars[i]:"";
    string who=card.podiumNames!=null&&i<card.podiumNames.Length?card.podiumNames[i]:"";
    string pts=card.podiumPoints!=null&&i<card.podiumPoints.Length?card.podiumPoints[i]:"";
    var sprite=K.Icon(string.IsNullOrEmpty(avatar)?"Icons/medal":avatar);p.face.sprite=sprite;p.face.enabled=sprite;
    p.face.rectTransform.offsetMin=p.face.rectTransform.offsetMax=Vector2.zero;if(string.IsNullOrEmpty(avatar)){p.face.rectTransform.offsetMin=new Vector2(14,14);p.face.rectTransform.offsetMax=new Vector2(-14,-14);}
    p.name.text=K.Clean(who);bool me=card.place==i+1;p.name.color=me?RankGoldTrim:RankCream;
    p.points.text=K.Clean(pts);p.points.gameObject.SetActive(!string.IsNullOrEmpty(pts));
    p.tag.gameObject.SetActive(me);p.tag.GetComponentInChildren<TextMeshProUGUI>().text=K.Clean(string.IsNullOrEmpty(card.meTag)?"VOCÊ":card.meTag);
    p.glow.color=new Color(1f,.85f,.35f,0);p.ring.color=me?RankGoldTrim:PlinthEdge[i];
    p.col.localScale=new Vector3(1,0,1);
   }
   // off the podium: the podium a little smaller, my place on a card under it
   leaguePodiumBox.localScale=Vector3.one*(onPodium||card.place<=0?1f:.86f);
   leaguePodiumBox.offsetMin=new Vector2(30,onPodium||card.place<=0?154:218);leaguePodiumBox.offsetMax=new Vector2(0,onPodium||card.place<=0?462:518);
   leagueMeBox.gameObject.SetActive(!onPodium&&card.place>0);leagueMeBox.localScale=Vector3.zero;
   leagueMeFace.sprite=K.Icon(card.avatar);leaguePlaceText.text="#"+card.place;leagueMeName.text=K.Clean(card.meName);
   // rewards
   leagueDiamonds.text="+0";leagueCoins.text="+0";
   leagueDiamondBox.gameObject.SetActive(card.diamonds>0);leagueChestBox.gameObject.SetActive(card.coins>0);
   var db=leagueDiamondBox;var cb=leagueChestBox;
   if(card.diamonds>0&&card.coins<=0){db.anchorMin=new Vector2(.25f,0);db.anchorMax=new Vector2(.75f,1);}else{db.anchorMin=new Vector2(0,0);db.anchorMax=new Vector2(.5f,1);}
   if(card.coins>0&&card.diamonds<=0){cb.anchorMin=new Vector2(.25f,0);cb.anchorMax=new Vector2(.75f,1);}else{cb.anchorMin=new Vector2(.5f,0);cb.anchorMax=new Vector2(1,1);}
   db.localScale=Vector3.zero;cb.localScale=Vector3.zero;leagueChestLid.localRotation=Quaternion.identity;leagueChestGlow.color=new Color(1f,.82f,.35f,0);
   // the stats row
   var stats=card.stats??new DesktopStat[0];
   for(int i=0;i<leagueStats.Count;i++){
    var (r,icon,value,label)=leagueStats[i];bool on=i<stats.Length;r.gameObject.SetActive(on);if(!on)continue;
    icon.sprite=K.Icon(stats[i].icon);icon.enabled=icon.sprite;value.text=K.Clean(stats[i].value);label.text=K.Clean(stats[i].label).ToUpperInvariant();r.localScale=Vector3.zero;
   }
   leagueStatsRow.gameObject.SetActive(stats.Length>0);
   leagueButton.Apply(new DesktopButton{label=card.button,icon="Icons/diamond",variant="coin",enabled=true,action="",args="[]",route="",after="",ok="",fail="",badge=""});
   leagueButton.transform.localScale=Vector3.zero;
   // ---- the show ----
   leagueDim.color=new Color(.04f,.06f,.13f,0);StartCoroutine(U.Fade(leagueDim,.84f,.3f));
   leagueRays.color=new Color(1f,.84f,.4f,0);foreach(var s in leagueSpots)s.color=new Color(1f,.95f,.78f,0);
   leagueRibbon.localScale=new Vector3(0,1,1);
   leaguePanel.localScale=Vector3.one*k*.6f;Sound("whoosh");
   yield return U.Scale(leaguePanel,Vector3.one*k,.38f,true);
   StartCoroutine(U.Fade(leagueRays,.32f,.6f));foreach(var s in leagueSpots)StartCoroutine(U.Fade(s,.22f,.8f));
   StartCoroutine(U.Scale(leagueRibbon,Vector3.one,.35f,true));Sound("pop",1.1f);
   LeagueConfetti(70,tint);
   yield return CheckoutUiKit.Wait(.2f);
   // the plinths rise (3rd, 2nd, 1st); my place pops with its glow
   foreach(var i in new[]{2,1,0}){StartCoroutine(U.Scale(leaguePodium[i].col,Vector3.one,.3f,true));Sound("pop",1+.08f*(2-i));yield return CheckoutUiKit.Wait(.14f);}
   if(onPodium){var mine=leaguePodium[card.place-1];StartCoroutine(U.Pop(mine.holder,1.16f,.35f));StartCoroutine(U.Fade(mine.glow,.75f,.4f));U.Sparkles(this,leagueFx,U.PointIn(leagueFx,mine.holder),12,170);}
   else if(card.place>0){StartCoroutine(U.Scale(leagueMeBox,Vector3.one,.3f,true));}
   yield return CheckoutUiKit.Wait(.25f);
   // the division: the old badge greys and shrinks, the chevrons run, the new badge pops in big with a glow; the stamp
   if(moved){
    leagueTo.transform.localScale=Vector3.zero;leagueFrom.transform.localScale=Vector3.one;
    yield return CheckoutUiKit.Wait(.15f);
    StartCoroutine(U.Tint(leagueFrom,new Color(.62f,.64f,.7f,.75f),.35f));StartCoroutine(U.Scale(leagueFrom.transform,Vector3.one*.72f,.35f));
    foreach(var ch in leagueChevronParts){StartCoroutine(U.Fade(ch,1,.12f));yield return CheckoutUiKit.Wait(.09f);}
   } else {leagueTo.transform.localScale=Vector3.zero;}
   StartCoroutine(U.Fade(leagueToGlow,card.moved=="down"?.35f:.6f,.4f));
   yield return U.Scale(leagueTo.transform,Vector3.one,.42f,true);
   if(card.moved=="up"){Sound("success");U.Sparkles(this,leagueFx,U.PointIn(leagueFx,leagueTo.rectTransform),16,210);}
   else Sound("pop",card.moved=="down"?.85f:1f);
   // the stamp slams down
   leagueStamp.localScale=Vector3.one*2.2f;yield return U.Scale(leagueStamp,Vector3.one,.18f);Sound("pop",.7f);StartCoroutine(U.Shake(leagueStamp,.18f,5));
   yield return CheckoutUiKit.Wait(.15f);
   // the rewards: the diamonds pop and count; the chest shakes, bursts open, coins fly out
   if(card.diamonds>0){yield return U.Scale(leagueDiamondBox,Vector3.one,.3f,true);StartCoroutine(CountPrize(leagueDiamonds,card.diamonds,.7f));Sound("coin_1");}
   if(card.coins>0){
    yield return U.Scale(leagueChestBox,Vector3.one,.3f,true);
    var box=(RectTransform)leagueChestLid.parent;
    yield return U.Shake(box,.45f,7);
    StartCoroutine(U.Rotate(leagueChestLid,16,.22f));StartCoroutine(U.Fade(leagueChestGlow,.85f,.25f));Sound("success",1.2f);
    ChestCoins(U.PointIn(leagueFx,box),14);
    StartCoroutine(CountPrize(leagueCoins,card.coins,.8f));
   }
   // the stats, one after the other, then the button
   for(int i=0;i<leagueStats.Count;i++){if(!leagueStats[i].root.gameObject.activeSelf)continue;StartCoroutine(U.Scale(leagueStats[i].root,Vector3.one,.26f,true));yield return CheckoutUiKit.Wait(.08f);}
   yield return CheckoutUiKit.Wait(.2f);
   yield return U.Scale(leagueButton.transform,Vector3.one,.3f,true);
   leagueRun=null;
  }
  IEnumerator CountPrize(TextMeshProUGUI label,int amount,float seconds){
   for(float t=0;t<seconds;t+=U.Dt){label.text="+"+Mathf.RoundToInt(amount*Mathf.SmoothStep(0,1,t/seconds));yield return null;}
   label.text="+"+amount;
  }
  void LeagueConfetti(int count,Color accent){
   var from=new Vector2(0,leagueFx.rect.height*.32f);
   for(int i=0;i<count;i++){
    int row=Random.Range(0,CheckoutConfettiArt.RowCount),col=Random.Range(0,CheckoutConfettiArt.Cols);
    var go=new GameObject("Piece",typeof(RectTransform),typeof(Image));go.transform.SetParent(leagueFx,false);
    var img=go.GetComponent<Image>();img.sprite=CheckoutConfettiArt.Sprite(i%3==0?CheckoutConfettiArt.Gold:accent,row,col);img.raycastTarget=false;
    var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);float size=Random.Range(18f,32f);r.sizeDelta=new Vector2(size,size);
    r.anchoredPosition=from+new Vector2(Random.Range(-300f,300f),Random.Range(-30f,30f));r.localRotation=Quaternion.Euler(0,0,Random.Range(0f,360f));
    float angle=Random.Range(40f,140f)*Mathf.Deg2Rad,speed=Random.Range(380f,820f);
    rankConfetti.Add(new SocialConfetto{rect=r,image=img,velocity=new Vector2(Mathf.Cos(angle)*speed,Mathf.Sin(angle)*speed),spin=Random.Range(-420f,420f),life=Random.Range(1.6f,2.6f)});
   }
  }
  /// <summary>Coins bursting up out of the opened chest and falling back (behind the labels).</summary>
  void ChestCoins(Vector2 from,int count){
   for(int i=0;i<count;i++){
    var go=new GameObject("Coin",typeof(RectTransform),typeof(Image));go.transform.SetParent(leagueFx,false);
    var img=go.GetComponent<Image>();img.sprite=K.Icon("Icons/coin");img.preserveAspect=true;img.raycastTarget=false;
    var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);r.sizeDelta=Vector2.one*Random.Range(22f,34f);r.anchoredPosition=from+new Vector2(Random.Range(-14f,14f),20);
    float angle=Random.Range(65f,115f)*Mathf.Deg2Rad,speed=Random.Range(420f,640f);
    rankConfetti.Add(new SocialConfetto{rect=r,image=img,velocity=new Vector2(Mathf.Cos(angle)*speed,Mathf.Sin(angle)*speed),spin=Random.Range(-200f,200f),life=Random.Range(1.1f,1.5f)});
   }
  }
  /// <summary>"Pegar prêmios": the diamonds and coins fly to the counters (the board's, else the top bar's), which tick
  /// up, while the card fades; then it closes.</summary>
  IEnumerator CollectLeaguePrizes(){
   leagueCollecting=true;var card=leagueData;Sound("coin_0");
   var diamondsTo=BoardOpen&&boardDiamonds?boardDiamonds:gemsText;var coinsTo=BoardOpen&&boardCoins?boardCoins:coinsText;
   if(card!=null&&card.diamonds>0&&diamondsTo){StartCoroutine(FlyPrize("Icons/diamond",leagueDiamondBox,diamondsTo.rectTransform,Mathf.Clamp(card.diamonds/3,4,10)));StartCoroutine(TickCounter(diamondsTo,card.diamonds,.45f));}
   if(card!=null&&card.coins>0&&coinsTo){StartCoroutine(FlyPrize("Icons/coin",leagueChestBox,coinsTo.rectTransform,Mathf.Clamp(card.coins/5,4,10)));StartCoroutine(TickCounter(coinsTo,card.coins,.45f));}
   for(float t=0;t<.5f;t+=U.Dt){leaguePanelGroup.alpha=1-t/.5f*.85f;yield return null;}
   yield return CheckoutUiKit.Wait(.45f);
   HideLeagueCard();
  }
  IEnumerator FlyPrize(string icon,RectTransform from,RectTransform to,int count){
   var a=U.PointIn(leagueFlyLayer,from);var b=U.PointIn(leagueFlyLayer,to);
   for(int i=0;i<count;i++){
    var piece=U.Icon(leagueFlyLayer,"Prize",icon,new Vector2(.5f,.5f),new Vector2(48,48),a+Random.insideUnitCircle*24);
    StartCoroutine(FlyOne(piece.rectTransform,b));yield return CheckoutUiKit.Wait(.05f);
   }
  }
  IEnumerator FlyOne(RectTransform piece,Vector2 to){
   var from=piece.anchoredPosition;var mid=(from+to)*.5f+new Vector2(0,160);
   for(float t=0;t<1;t+=U.Dt/.55f){if(!piece)yield break;float e=1-Mathf.Pow(1-t,3);piece.anchoredPosition=Vector2.Lerp(Vector2.Lerp(from,mid,e),Vector2.Lerp(mid,to,e),e);piece.localScale=Vector3.one*(1-.45f*e);yield return null;}
   if(piece)Destroy(piece.gameObject);
  }
  /// <summary>A counter ticks from (its number − amount) up to its number, keeping its own thousands separator.</summary>
  IEnumerator TickCounter(TextMeshProUGUI label,int amount,float delay){
   if(!label)yield break;
   string shown=label.text??"";var digits=new System.Text.StringBuilder();foreach(var ch in shown)if(char.IsDigit(ch))digits.Append(ch);
   if(digits.Length==0||!long.TryParse(digits.ToString(),out long total))yield break;
   string sep=shown.Contains(".")?".":shown.Contains(",")?",":shown.Contains(" ")?" ":shown.Contains(" ")?" ":"";
   long from=System.Math.Max(0,total-amount);
   string Format(long n){var s=n.ToString();if(sep=="")return s;var sb=new System.Text.StringBuilder();for(int i=0;i<s.Length;i++){if(i>0&&(s.Length-i)%3==0)sb.Append(sep);sb.Append(s[i]);}return sb.ToString();}
   label.text=Format(from);
   yield return CheckoutUiKit.Wait(delay);
   for(float t=0;t<.6f;t+=U.Dt){if(!label)yield break;label.text=Format((long)Mathf.Lerp(from,total,t/.6f));yield return null;}
   if(label)label.text=shown;
   if(label)StartCoroutine(U.Pop(label.transform,1.18f,.25f));
  }
  void UpdateLeagueCard(){
   if(!LeagueCardOpen)return;
   if(leagueRoot.GetSiblingIndex()!=leagueRoot.parent.childCount-1)leagueRoot.SetAsLastSibling();
   float t=Time.unscaledTime;
   if(leagueRays)leagueRays.transform.Rotate(0,0,-9*U.Dt);
   if(leagueToGlow&&leagueRun==null){var c=leagueToGlow.color;c.a=(leagueData!=null&&leagueData.moved=="down"?.28f:.5f)+.12f*Mathf.Sin(t*2.4f);leagueToGlow.color=c;}
   if(leagueRun==null&&leagueChevrons&&leagueChevrons.gameObject.activeSelf)for(int i=0;i<leagueChevronParts.Count;i++){var c=leagueChevronParts[i].color;c.a=.45f+.55f*Mathf.Clamp01(Mathf.Sin(t*5-i*.9f));leagueChevronParts[i].color=c;}
   if(leagueRun==null&&!leagueCollecting&&leagueButton){float s=1+.03f*Mathf.Sin(t*4);leagueButton.transform.localScale=new Vector3(s,s,1);}
   // (the confetti of the card falls even while no board is open)
   if(!BoardOpen)UpdateRankBoard(t);
  }
 }
}
