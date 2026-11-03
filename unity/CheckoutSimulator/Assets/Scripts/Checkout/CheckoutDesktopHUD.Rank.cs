using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // Rankings v1 in the board window (desktop/pages/ranking.ts, board style "rank"): the top three on a podium (big round
 // framed faces, gold / silver / bronze plinths, a crown and rays on #1, confetti when it opens), a strip of chips over
 // the rows (the league's prizes), the ranked rows (BoardTileUi "rank" mode) and my own row pinned under them with
 // "Ver minha posição". Plus the end-of-week card of the league (DesktopView.leagueCard): the podium, my place, the
 // division badge moving up or down and the prizes, with confetti. Faces are always round: a navy disc that clips the
 // picture, a ring drawn over its edge (never square corners).
 public partial class CheckoutDesktopHUD {
  static float RankRowH=>Phone?78:84;
  static float PodiumScale=>Phone?.72f:1f;
  static readonly Color[] PlinthEdge={K.C("D79E2C"),K.C("98A3B0"),K.C("B06A32")};
  static readonly Color[] PlinthFace={K.C("F2C552"),K.C("CBD3DC"),K.C("DE9A5E")};
  RectTransform rankStrip,rankPodium,rankFx;readonly List<BoardChip> rankStripChips=new List<BoardChip>();
  PodiumColumn[] podiumColumns;BoardTileUi rankPinned;RectTransform rankPinnedRect;
  string rankPodiumKey,rankScrollShown;float rankSparkleAt;
  readonly List<SocialConfetto> rankConfetti=new List<SocialConfetto>();

  void BuildRankBoard(){
   rankStrip=N.Node("Rank strip",boardContent);var row=N.Row(rankStrip.gameObject,10,new RectOffset(4,4,2,6));row.childAlignment=TextAnchor.MiddleCenter;row.childForceExpandWidth=true;
   rankStrip.gameObject.AddComponent<LayoutElement>().preferredHeight=Phone?62:66;rankStrip.gameObject.SetActive(false);
   rankPodium=N.Node("Podium",boardContent);rankPodium.gameObject.AddComponent<LayoutElement>().preferredHeight=PodiumHeight;
   // (a soft floor under the plinths)
   var floor=N.Image(rankPodium,"Floor",new Color(.55f,.36f,.16f,.22f),0);floor.sprite=U.Glow();U.Stretch(floor.rectTransform,new Vector2(.08f,0),new Vector2(.92f,0),new Vector2(0,-14),new Vector2(0,26));
   podiumColumns=new PodiumColumn[3];
   for(int i=0;i<3;i++)podiumColumns[i]=PodiumColumn.Create(this,rankPodium,i+1);
   rankPodium.gameObject.SetActive(false);
   // My row pinned under the tiles (over the footer), the same look as the rows.
   rankPinned=BoardTileUi.Create(this,boardGridArea);rankPinnedRect=(RectTransform)rankPinned.transform;
   var glowEdge=N.Image(rankPinnedRect,"PinnedGlow",new Color(1,.8f,.25f,.5f),20);U.Stretch(glowEdge.rectTransform,Vector2.zero,Vector2.one,new Vector2(-4,-4),new Vector2(4,4));glowEdge.transform.SetAsFirstSibling();
   rankPinned.gameObject.SetActive(false);
   rankFx=N.Node("Rank fx",(RectTransform)boardWin.transform.Find("Window"));Stretch(rankFx,Vector2.zero,Vector2.zero);
  }
  static float PodiumHeight=>(Phone?252:322);

  DesktopTile RankFind(DesktopBoard b,string id){
   if(b==null||string.IsNullOrEmpty(id))return null;
   if(b.podium!=null)foreach(var t in b.podium)if(t!=null&&t.id==id)return t;
   if(b.pinned!=null&&b.pinned.id==id)return b.pinned;
   return null;
  }

  void ApplyRankBoard(DesktopBoard b,bool fresh){
   bool rank=b.style=="rank";
   var strip=rank&&b.strip!=null?b.strip:new DesktopStat[0];
   while(rankStripChips.Count<strip.Length)rankStripChips.Add(BoardChip.Create(rankStrip,false));
   for(int i=0;i<rankStripChips.Count;i++){bool on=i<strip.Length;rankStripChips[i].gameObject.SetActive(on);if(on)rankStripChips[i].Apply(strip[i]);}
   rankStrip.gameObject.SetActive(strip.Length>0);
   var podium=rank&&b.podium!=null&&b.podium.Length>=3?b.podium:null;
   rankPodium.gameObject.SetActive(podium!=null);
   if(podium!=null){
    rankPodium.GetComponent<LayoutElement>().preferredHeight=PodiumHeight;
    for(int i=0;i<3;i++)podiumColumns[i].Apply(podium[i],podium[i].id==boardSelected);
    string key=(boardRouteShown??"")+"|"+podium[0].id+"|"+podium[1].id+"|"+podium[2].id;
    if(key!=rankPodiumKey){rankPodiumKey=key;StartCoroutine(PodiumEntrance());}
   } else rankPodiumKey=null;
   // the order inside the scroll: the page's cards, the strip, the podium, then the rows
   boardHeroes.SetAsFirstSibling();rankStrip.SetSiblingIndex(1);rankPodium.SetSiblingIndex(2);
   // my row pinned over the footer; the tiles end above it
   bool pinned=rank&&b.pinned!=null&&!string.IsNullOrEmpty(b.pinned.id);
   rankPinned.gameObject.SetActive(pinned);
   if(pinned){
    float h=RankRowH;rankPinnedRect.anchorMin=new Vector2(0,0);rankPinnedRect.anchorMax=new Vector2(1,0);rankPinnedRect.pivot=new Vector2(.5f,0);
    rankPinnedRect.offsetMin=new Vector2(14,boardScrollBottom+2);rankPinnedRect.offsetMax=new Vector2(-14,boardScrollBottom+2+h);
    rankPinned.Apply(b.pinned,true,b.pinned.id==boardSelected);
    boardScrollBottom+=h+12;((RectTransform)boardScroll.transform).offsetMin=new Vector2(10,boardScrollBottom);
   }
  }

  // "Ver minha posição": the row of that id comes into the middle of the list and is picked.
  string rankTopRoute;
  void RankScrollIfAsked(DesktopBoard b){
   // (another tab of the window, Mundo → Liga: its list starts at the top, with its podium or its prizes)
   if(b.style=="rank"&&boardRouteShown!=rankTopRoute){rankTopRoute=boardRouteShown;Canvas.ForceUpdateCanvases();boardScroll.verticalNormalizedPosition=1;}
   else if(b.style!="rank")rankTopRoute=null;
   var ask=b.style=="rank"?b.scroll??"":"";
   if(ask==rankScrollShown)return;rankScrollShown=ask;
   if(string.IsNullOrEmpty(ask))return;
   var id=ask.Split('#')[0];StartCoroutine(ScrollToRow(id));
  }
  IEnumerator ScrollToRow(string id){
   yield return null;
   BoardTileUi target=null;foreach(var t in boardTiles)if(t.gameObject.activeInHierarchy&&t.Id==id){target=t;break;}
   if(target==null)yield break;
   Canvas.ForceUpdateCanvases();
   var vp=boardScroll.viewport?boardScroll.viewport:(RectTransform)boardScroll.transform;
   var c=new Vector3[4];((RectTransform)target.transform).GetWorldCorners(c);
   float rowTop=-boardContent.InverseTransformPoint(c[1]).y,rowBottom=-boardContent.InverseTransformPoint(c[0]).y;
   float max=Mathf.Max(0,boardContent.rect.height-vp.rect.height);
   float goal=Mathf.Clamp((rowTop+rowBottom)*.5f-vp.rect.height*.5f,0,max);
   float from=boardContent.anchoredPosition.y;
   for(float t=0;t<.35f;t+=U.Dt){boardContent.anchoredPosition=new Vector2(boardContent.anchoredPosition.x,Mathf.Lerp(from,goal,Mathf.SmoothStep(0,1,t/.35f)));yield return null;}
   boardContent.anchoredPosition=new Vector2(boardContent.anchoredPosition.x,goal);
   boardSelected=null;BoardSelect(id);
   StartCoroutine(U.Pop(target.transform,1.06f,.3f));
   U.Sparkles(this,rankFx,U.PointIn(rankFx,(RectTransform)target.transform),10,170);
  }

  IEnumerator PodiumEntrance(){
   foreach(var col in podiumColumns)col.transform.localScale=new Vector3(1,0,1);
   // 3rd, 2nd, then the winner rise one after the other
   int[] rise={2,1,0};
   foreach(var i in rise){StartCoroutine(U.Scale(podiumColumns[i].transform,Vector3.one,.32f,true));yield return CheckoutUiKit.Wait(.12f);}
   yield return CheckoutUiKit.Wait(.2f);
   Sound("success",1.05f);
   RankConfetti(U.PointIn(rankFx,podiumColumns[0].Portrait),46);
  }

  void RankConfetti(Vector2 from,int count){
   rankFx.SetAsLastSibling();
   for(int i=0;i<count;i++){
    int row=Random.Range(0,CheckoutConfettiArt.RowCount),col=Random.Range(0,CheckoutConfettiArt.Cols);
    var go=new GameObject("Piece",typeof(RectTransform),typeof(Image));go.transform.SetParent(rankFx,false);
    var img=go.GetComponent<Image>();img.sprite=CheckoutConfettiArt.Sprite(CheckoutConfettiArt.Gold,row,col);img.raycastTarget=false;
    var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);float size=Random.Range(16f,28f);r.sizeDelta=new Vector2(size,size);
    r.anchoredPosition=from+Random.insideUnitCircle*30;r.localRotation=Quaternion.Euler(0,0,Random.Range(0f,360f));
    float angle=Random.Range(35f,145f)*Mathf.Deg2Rad,speed=Random.Range(360f,760f);
    rankConfetti.Add(new SocialConfetto{rect=r,image=img,velocity=new Vector2(Mathf.Cos(angle)*speed,Mathf.Sin(angle)*speed),spin=Random.Range(-360f,360f),life=Random.Range(1.3f,2f)});
   }
  }

  void UpdateRankBoard(float t){
   float dt=U.Dt;
   for(int i=rankConfetti.Count-1;i>=0;i--){
    var p=rankConfetti[i];if(!p.rect){rankConfetti.RemoveAt(i);continue;}
    p.age+=dt;p.velocity+=new Vector2(-p.velocity.x*1.6f*dt,-900f*dt);p.rect.anchoredPosition+=p.velocity*dt;p.rect.Rotate(0,0,p.spin*dt);
    var c=p.image.color;c.a=Mathf.Clamp01((p.life-p.age)/.4f);p.image.color=c;
    if(p.age>=p.life){Destroy(p.rect.gameObject);rankConfetti.RemoveAt(i);}
   }
   if(rankPodium==null||!rankPodium.gameObject.activeInHierarchy)return;
   foreach(var col in podiumColumns)col.Tick(t);
   // a little shine on the winner now and then
   if(t>rankSparkleAt){rankSparkleAt=t+2.8f;U.Sparkles(this,rankFx,U.PointIn(rankFx,podiumColumns[0].Portrait),6,120);}
  }

  // One place of the podium: rays and a crown (#1), the round framed face, the name, the level ribbon and the flag,
  // the plinth with the place.
  sealed class PodiumColumn:MonoBehaviour,IPointerClickHandler {
   CheckoutDesktopHUD hud;int place;string id;RectTransform rect,portrait;Image ring,plate,clip,icon,rim,crown,rays,glow,plinth,plinthFace,flag,ribbon,stage;
   TextMeshProUGUI name,number,value,ribbonText;
   public RectTransform Portrait=>portrait;
   public static PodiumColumn Create(CheckoutDesktopHUD hud,RectTransform parent,int place){
    float s=PodiumScale;
    var root=N.Node("Place "+place,parent);var c=root.gameObject.AddComponent<PodiumColumn>();c.hud=hud;c.place=place;c.rect=root;
    float x=place==1?.5f:place==2?.2f:.8f;root.anchorMin=root.anchorMax=new Vector2(x,0);root.pivot=new Vector2(.5f,0);root.sizeDelta=new Vector2(230*s,PodiumHeight);root.anchoredPosition=new Vector2(0,6);
    var hit=root.gameObject.AddComponent<Image>();hit.color=new Color(0,0,0,0);
    float plinthH=(place==1?96:place==2?72:54)*s,face=(place==1?124:100)*s;
    int i=place-1;
    // the plinth: a darker edge, its lighter face, the place in big numbers and the value under it
    c.plinth=N.Image(root,"Plinth",PlinthEdge[i],14);U.Stretch(c.plinth.rectTransform,new Vector2(.08f,0),new Vector2(.92f,0),Vector2.zero,new Vector2(0,plinthH));
    c.plinthFace=N.Image(c.plinth.transform,"Face",PlinthFace[i],12);Stretch(c.plinthFace.rectTransform,new Vector2(4,6),new Vector2(-4,-4));
    var band=N.Image(c.plinthFace.transform,"Shine",new Color(1,1,1,.28f),10);U.Stretch(band.rectTransform,new Vector2(0,.62f),Vector2.one,new Vector2(5,0),new Vector2(-5,-3));
    c.number=N.Text(c.plinthFace.transform,"Number",K.Headline,(place==1?50:40)*s,Color.white);c.number.alignment=TextAlignmentOptions.Center;c.number.text=place.ToString();
    c.number.outlineWidth=.22f;c.number.outlineColor=new Color32(90,55,20,210);U.Stretch(c.number.rectTransform,new Vector2(0,.3f),Vector2.one);
    c.value=N.Text(c.plinthFace.transform,"Value",K.Number,13*Mathf.Max(.85f,s),new Color(.25f,.16f,.06f,.9f));c.value.alignment=TextAlignmentOptions.Center;c.value.textWrappingMode=TextWrappingModes.NoWrap;
    c.value.enableAutoSizing=true;c.value.fontSizeMin=9;c.value.fontSizeMax=14;U.Stretch(c.value.rectTransform,new Vector2(0,0),new Vector2(1,.34f),new Vector2(6,2),new Vector2(-6,0));
    // level ribbon + flag, then the name, above the plinth
    float y=plinthH+6;
    var info=N.Node("Info",root);info.anchorMin=new Vector2(0,0);info.anchorMax=new Vector2(1,0);info.pivot=new Vector2(.5f,0);info.offsetMin=new Vector2(0,y);info.offsetMax=new Vector2(0,y+24*s);
    var ir=N.Row(info.gameObject,6);ir.childAlignment=TextAnchor.MiddleCenter;
    c.ribbon=Pill(info,"Ribbon",PortraitNavy,out c.ribbonText,12,K.Label);c.ribbonText.characterSpacing=1;var rl=c.ribbon.gameObject.AddComponent<LayoutElement>();rl.preferredHeight=22*s;rl.preferredWidth=60;
    var flagEdge=N.Image(info,"FlagEdge",Color.white,3);var fl=flagEdge.gameObject.AddComponent<LayoutElement>();fl.preferredWidth=30*Mathf.Max(.85f,s);fl.preferredHeight=23*Mathf.Max(.85f,s);
    c.flag=N.Image(flagEdge.transform,"Flag",Color.white,0);c.flag.preserveAspect=true;Stretch(c.flag.rectTransform,new Vector2(2,2),new Vector2(-2,-2));
    y+=26*s+2;
    c.name=N.Text(root,"Name",K.Headline,(place==1?19:17)*Mathf.Max(.82f,s),K.Ink);c.name.alignment=TextAlignmentOptions.Center;c.name.textWrappingMode=TextWrappingModes.NoWrap;c.name.overflowMode=TextOverflowModes.Ellipsis;
    var nr=c.name.rectTransform;nr.anchorMin=new Vector2(0,0);nr.anchorMax=new Vector2(1,0);nr.pivot=new Vector2(.5f,0);nr.offsetMin=new Vector2(-6,y);nr.offsetMax=new Vector2(6,y+26*Mathf.Max(.82f,s));
    y+=28*Mathf.Max(.82f,s)+2;
    // the face: rays and a glow behind #1, the ring, the navy plate, the picture clipped round, the rim, the stage badge
    var holder=N.Node("Face",root);holder.anchorMin=holder.anchorMax=new Vector2(.5f,0);holder.pivot=new Vector2(.5f,0);holder.sizeDelta=new Vector2(face,face);holder.anchoredPosition=new Vector2(0,y);c.portrait=holder;
    if(place==1){
     c.rays=N.Image(holder,"Rays",new Color(1f,.9f,.5f,.5f),0);c.rays.sprite=LevelRaysSprite();U.At(c.rays.rectTransform,new Vector2(.5f,.5f),new Vector2(face*2.3f,face*2.3f));
     c.glow=N.Image(holder,"Glow",new Color(1f,.86f,.4f,.65f),0);c.glow.sprite=U.Glow();U.At(c.glow.rectTransform,new Vector2(.5f,.5f),new Vector2(face*1.7f,face*1.7f));
    }
    c.ring=N.Image(holder,"Ring",PlinthEdge[i],0);c.ring.sprite=K.Disc();Stretch(c.ring.rectTransform,new Vector2(-5,-5),new Vector2(5,5));
    c.plate=N.Image(holder,"Plate",PortraitNavy,0);c.plate.sprite=K.Disc();Stretch(c.plate.rectTransform,Vector2.zero,Vector2.zero);
    c.clip=K.RoundClip(holder,"Clip");K.SetRound(c.clip,true);
    c.icon=N.Image(c.clip.transform,"Icon",Color.white,0);c.icon.preserveAspect=true;Stretch(c.icon.rectTransform,Vector2.zero,Vector2.zero);
    c.rim=N.Image(holder,"Rim",PlinthFace[i],0);K.FitRim(c.rim,face,6*Mathf.Max(.8f,s));
    c.stage=N.Image(holder,"Stage",Color.white,0);c.stage.preserveAspect=true;U.At(c.stage.rectTransform,new Vector2(.86f,.12f),new Vector2(face*.34f,face*.34f));
    if(place==1){c.crown=N.Image(holder,"Crown",Color.white,0);c.crown.sprite=K.Icon("Icons/crown");c.crown.preserveAspect=true;U.At(c.crown.rectTransform,new Vector2(.5f,1),new Vector2(face*.56f,face*.56f),new Vector2(0,face*.04f));c.crown.rectTransform.localRotation=Quaternion.Euler(0,0,-8);}
    return c;
   }
   public void Apply(DesktopTile t,bool picked){
    id=t.id;
    var face=K.Icon(t.icon);icon.sprite=face;icon.enabled=face;
    name.text=K.Clean(t.title);
    value.text=K.Clean(t.value);value.gameObject.SetActive(!string.IsNullOrEmpty(t.value));
    bool hasRibbon=!string.IsNullOrEmpty(t.sticker);ribbon.gameObject.SetActive(hasRibbon);
    if(hasRibbon){ribbonText.text=K.Clean(t.sticker);ribbon.GetComponent<LayoutElement>().preferredWidth=PillWidth(ribbonText,ribbonText.text,48);ribbon.color=t.tone=="gold"?K.C("C98A12"):PortraitNavy;}
    var f=K.Icon(t.flag);flag.transform.parent.gameObject.SetActive(f);if(f)flag.sprite=f;
    var st=K.Icon(t.corner);stage.gameObject.SetActive(st);if(st)stage.sprite=st;
    // me on the podium: a gold name
    name.color=t.tone=="gold"?K.C("9A6A10"):K.Ink;
    rim.color=picked?K.C("FFF3B0"):PlinthFace[place-1];
   }
   public void Tick(float t){
    if(rays)rays.transform.localRotation=Quaternion.Euler(0,0,-t*14);
    if(glow){var c=glow.color;c.a=.5f+.18f*Mathf.Sin(t*2.4f);glow.color=c;}
    if(crown)crown.rectTransform.anchoredPosition=new Vector2(0,portrait.sizeDelta.y*.04f+Mathf.Abs(Mathf.Sin(t*2.2f))*4);
   }
   public void OnPointerClick(PointerEventData e){if(string.IsNullOrEmpty(id))return;hud.BoardSelect(id);StartCoroutine(U.Pop(portrait,1.08f,.22f));}
  }

  // ------------------------------------------------------------------ the end-of-week card
  RectTransform leagueRoot,leaguePanel,leagueStage,leagueFx,leagueArrow;Image leagueDim,leagueRays,leagueFrom,leagueTo,leagueMeFace;readonly List<Image> leagueArrowParts=new List<Image>();
  TextMeshProUGUI leagueHeadline,leagueTitle,leagueSubtitle,leagueMoved,leagueDiamonds,leagueCoins,leaguePlaceText;
  RectTransform leagueDiamondChip,leagueCoinChip,leagueMeBox;CheckoutDesktopButton leagueButton;
  readonly List<(Image face,Image ring,TextMeshProUGUI name,RectTransform col)> leaguePodium=new List<(Image,Image,TextMeshProUGUI,RectTransform)>();
  string leagueShownKey,leagueClosedKey;Coroutine leagueRun;
  public bool LeagueCardOpen=>leagueRoot&&leagueRoot.gameObject.activeSelf;

  void BuildLeagueCard(){
   leagueRoot=N.Node("League card",root);Stretch(leagueRoot,Vector2.zero,Vector2.zero);
   leagueDim=leagueRoot.gameObject.AddComponent<Image>();leagueDim.color=new Color(.05f,.07f,.15f,.82f);
   leaguePanel=N.Node("Panel",leagueRoot);leaguePanel.anchorMin=leaguePanel.anchorMax=leaguePanel.pivot=new Vector2(.5f,.5f);leaguePanel.sizeDelta=new Vector2(920,620);
   leagueRays=N.Image(leaguePanel,"Rays",new Color(1f,.9f,.55f,.35f),0);leagueRays.sprite=LevelRaysSprite();U.At(leagueRays.rectTransform,new Vector2(.5f,.62f),new Vector2(980,980));
   var edge=N.Image(leaguePanel,"Edge",SocialGold,30);Stretch(edge.rectTransform,Vector2.zero,Vector2.zero);
   var face=N.Image(edge.transform,"Face",SocialNavy,27);Stretch(face.rectTransform,new Vector2(4,4),new Vector2(-4,-4));
   leagueStage=face.rectTransform;
   leagueHeadline=N.Text(leagueStage,"Headline",K.Label,18,SocialGold);leagueHeadline.characterSpacing=6;leagueHeadline.alignment=TextAlignmentOptions.Center;U.Stretch(leagueHeadline.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(20,-46),new Vector2(-20,-18));
   leagueTitle=N.Text(leagueStage,"Title",K.Headline,40,Color.white);leagueTitle.alignment=TextAlignmentOptions.Center;leagueTitle.textWrappingMode=TextWrappingModes.NoWrap;leagueTitle.enableAutoSizing=true;leagueTitle.fontSizeMin=22;leagueTitle.fontSizeMax=40;
   U.Stretch(leagueTitle.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(30,-98),new Vector2(-30,-46));
   leagueSubtitle=N.Text(leagueStage,"Subtitle",K.Body,18,SocialCream);leagueSubtitle.alignment=TextAlignmentOptions.Center;U.Stretch(leagueSubtitle.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(30,-126),new Vector2(-30,-98));
   // the mini podium on the left: three plinths with round faces
   var podium=N.Node("Podium",leagueStage);podium.anchorMin=new Vector2(0,0);podium.anchorMax=new Vector2(.55f,1);podium.offsetMin=new Vector2(24,124);podium.offsetMax=new Vector2(0,-140);
   for(int place=1;place<=3;place++){
    int i=place-1;float x=place==1?.5f:place==2?.18f:.82f,plinthH=place==1?96:place==2?70:52,size=place==1?104:84;
    var col=N.Node("Place "+place,podium);col.anchorMin=new Vector2(x,0);col.anchorMax=new Vector2(x,1);col.pivot=new Vector2(.5f,0);col.sizeDelta=new Vector2(150,0);col.anchoredPosition=Vector2.zero;
    var plinth=N.Image(col,"Plinth",PlinthEdge[i],12);U.Stretch(plinth.rectTransform,new Vector2(0,0),new Vector2(1,0),Vector2.zero,new Vector2(0,plinthH));
    var pf=N.Image(plinth.transform,"Face",PlinthFace[i],10);Stretch(pf.rectTransform,new Vector2(4,5),new Vector2(-4,-4));
    var num=N.Text(pf.transform,"Number",K.Headline,place==1?44:36,Color.white);num.text=place.ToString();num.alignment=TextAlignmentOptions.Center;num.outlineWidth=.22f;num.outlineColor=new Color32(90,55,20,210);Stretch(num.rectTransform,Vector2.zero,Vector2.zero);
    var name=N.Text(col,"Name",K.Label,14,SocialCream);name.alignment=TextAlignmentOptions.Center;name.textWrappingMode=TextWrappingModes.NoWrap;name.overflowMode=TextOverflowModes.Ellipsis;U.Stretch(name.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(-8,plinthH+4),new Vector2(8,plinthH+24));
    var holder=N.Node("Face",col);holder.anchorMin=holder.anchorMax=new Vector2(.5f,0);holder.pivot=new Vector2(.5f,0);holder.sizeDelta=new Vector2(size,size);holder.anchoredPosition=new Vector2(0,plinthH+28);
    var ring=N.Image(holder,"Ring",PlinthEdge[i],0);ring.sprite=K.Disc();Stretch(ring.rectTransform,new Vector2(-5,-5),new Vector2(5,5));
    var plate=N.Image(holder,"Plate",K.C("2A3D6B"),0);plate.sprite=K.Disc();Stretch(plate.rectTransform,Vector2.zero,Vector2.zero);
    var clip=K.RoundClip(holder,"Clip");K.SetRound(clip,true);
    var img=N.Image(clip.transform,"Icon",Color.white,0);img.preserveAspect=true;Stretch(img.rectTransform,Vector2.zero,Vector2.zero);
    var rim=N.Image(holder,"Rim",PlinthFace[i],0);K.FitRim(rim,size,5);
    if(place==1){var crown=N.Image(holder,"Crown",Color.white,0);crown.sprite=K.Icon("Icons/crown");crown.preserveAspect=true;U.At(crown.rectTransform,new Vector2(.5f,1),new Vector2(62,62),new Vector2(0,14));crown.rectTransform.localRotation=Quaternion.Euler(0,0,-8);}
    leaguePodium.Add((img,ring,name,col));
   }
   // my place when it is not on the podium: my face and "#12"
   leagueMeBox=N.Node("Me",leagueStage);leagueMeBox.anchorMin=leagueMeBox.anchorMax=new Vector2(.275f,0);leagueMeBox.pivot=new Vector2(.5f,0);leagueMeBox.sizeDelta=new Vector2(320,64);leagueMeBox.anchoredPosition=new Vector2(0,96);
   var meBack=N.Image(leagueMeBox,"Back",new Color(1,1,1,.12f),30);Stretch(meBack.rectTransform,Vector2.zero,Vector2.zero);
   var meRing=N.Image(leagueMeBox,"Ring",SocialGold,0);meRing.sprite=K.Disc();U.At(meRing.rectTransform,new Vector2(0,.5f),new Vector2(56,56),new Vector2(36,0));
   var meClip=K.RoundClip(meRing.transform,"Clip");K.SetRound(meClip,true);var mcr=meClip.rectTransform;mcr.offsetMin=new Vector2(3,3);mcr.offsetMax=new Vector2(-3,-3);
   var mePlate=N.Image(meClip.transform,"Plate",K.C("2A3D6B"),0);mePlate.sprite=K.Disc();Stretch(mePlate.rectTransform,Vector2.zero,Vector2.zero);
   leagueMeFace=N.Image(meClip.transform,"Icon",Color.white,0);leagueMeFace.preserveAspect=true;Stretch(leagueMeFace.rectTransform,Vector2.zero,Vector2.zero);
   var meRim=N.Image(meRing.transform,"Rim",SocialGold,0);K.FitRim(meRim,50,3);
   leaguePlaceText=N.Text(leagueMeBox,"Place",K.Headline,30,Color.white);leaguePlaceText.alignment=TextAlignmentOptions.MidlineLeft;leaguePlaceText.textWrappingMode=TextWrappingModes.NoWrap;U.Stretch(leaguePlaceText.rectTransform,Vector2.zero,Vector2.one,new Vector2(76,0),new Vector2(-10,0));
   // the division: from-badge → arrow → to-badge, and the words under it
   var division=N.Node("Division",leagueStage);division.anchorMin=new Vector2(.55f,0);division.anchorMax=new Vector2(1,1);division.offsetMin=new Vector2(0,170);division.offsetMax=new Vector2(-24,-140);
   leagueFrom=N.Image(division,"From",Color.white,0);leagueFrom.preserveAspect=true;U.At(leagueFrom.rectTransform,new Vector2(.22f,.55f),new Vector2(130,130));
   // (an arrow drawn from three bars: a shaft and its head)
   leagueArrow=N.Node("Arrow",division);U.At(leagueArrow,new Vector2(.5f,.55f),new Vector2(64,40));
   var shaft=N.Image(leagueArrow,"Shaft",SocialGold,4);U.At(shaft.rectTransform,new Vector2(.5f,.5f),new Vector2(46,10),new Vector2(-6,0));leagueArrowParts.Add(shaft);
   foreach(var side in new[]{-1,1}){var head=N.Image(leagueArrow,"Head",SocialGold,4);U.At(head.rectTransform,new Vector2(.5f,.5f),new Vector2(28,10),new Vector2(14,side*8));head.rectTransform.localRotation=Quaternion.Euler(0,0,-side*40);leagueArrowParts.Add(head);}
   leagueTo=N.Image(division,"To",Color.white,0);leagueTo.preserveAspect=true;U.At(leagueTo.rectTransform,new Vector2(.78f,.55f),new Vector2(170,170));
   leagueMoved=N.Text(division,"Moved",K.Headline,24,Color.white);leagueMoved.alignment=TextAlignmentOptions.Center;leagueMoved.enableAutoSizing=true;leagueMoved.fontSizeMin=14;leagueMoved.fontSizeMax=26;U.Stretch(leagueMoved.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(0,-6),new Vector2(0,40));
   // the prizes: diamonds and the coin chest, counting up
   var prizes=N.Node("Prizes",leagueStage);prizes.anchorMin=new Vector2(.55f,0);prizes.anchorMax=new Vector2(1,0);prizes.pivot=new Vector2(.5f,0);prizes.offsetMin=new Vector2(0,96);prizes.offsetMax=new Vector2(-24,160);
   var pr=N.Row(prizes.gameObject,14);pr.childAlignment=TextAnchor.MiddleCenter;pr.childForceExpandWidth=false;
   leagueDiamondChip=Prize(prizes,"Icons/diamond",out leagueDiamonds);leagueCoinChip=Prize(prizes,"Icons/gift",out leagueCoins);
   leagueButton=CheckoutDesktopButton.Create(leagueStage,64,24,18);var br=(RectTransform)leagueButton.transform;Destroy(leagueButton.GetComponent<LayoutElement>());
   br.anchorMin=br.anchorMax=br.pivot=new Vector2(.5f,0);br.sizeDelta=new Vector2(340,66);br.anchoredPosition=new Vector2(0,20);
   leagueButton.Clicked=_=>CloseLeagueCard();
   leagueFx=N.Node("Fx",leagueRoot);Stretch(leagueFx,Vector2.zero,Vector2.zero);
   leagueRoot.gameObject.SetActive(false);
  }
  RectTransform Prize(Transform parent,string iconPath,out TextMeshProUGUI text){
   var chip=N.Image(parent,"Prize",new Color(1,1,1,.14f),26);var le=chip.gameObject.AddComponent<LayoutElement>();le.preferredWidth=190;le.preferredHeight=58;
   var icon=N.Image(chip.transform,"Icon",Color.white,0);icon.sprite=K.Icon(iconPath);icon.preserveAspect=true;U.At(icon.rectTransform,new Vector2(0,.5f),new Vector2(48,48),new Vector2(32,0));
   text=N.Text(chip.transform,"Text",K.Number,26,Color.white);text.alignment=TextAlignmentOptions.MidlineLeft;text.textWrappingMode=TextWrappingModes.NoWrap;text.enableAutoSizing=true;text.fontSizeMin=14;text.fontSizeMax=26;
   U.Stretch(text.rectTransform,Vector2.zero,Vector2.one,new Vector2(62,0),new Vector2(-10,0));
   return chip.rectTransform;
  }

  void ApplyLeagueCard(DesktopView v){
   var card=v.leagueCard;
   bool has=card!=null&&!string.IsNullOrEmpty(card.key)&&card.key!=leagueClosedKey&&!CheckoutSocial.Visiting;
   if(!has){if(LeagueCardOpen&&(card==null||string.IsNullOrEmpty(card.key)))HideLeagueCard();return;}
   if(card.key==leagueShownKey&&LeagueCardOpen)return;
   // the level-up and the conquest celebrations go first; the next view brings this back
   if(LevelUpOpen||ConquestOpen)return;
   leagueShownKey=card.key;
   if(leagueRun!=null)StopCoroutine(leagueRun);
   leagueRun=StartCoroutine(PlayLeagueCard(card));
  }
  void CloseLeagueCard(){
   if(string.IsNullOrEmpty(leagueShownKey))return;
   leagueClosedKey=leagueShownKey;
   Silent.Add(host.Action("rankingDismissCard","[\""+leagueShownKey+"\"]",""));
   Sound("coin_0");HideLeagueCard();
  }
  void HideLeagueCard(){
   if(leagueRun!=null){StopCoroutine(leagueRun);leagueRun=null;}
   foreach(var p in rankConfetti)if(p.rect&&p.rect.parent==leagueFx)Destroy(p.rect.gameObject);
   if(leagueRoot)leagueRoot.gameObject.SetActive(false);
  }
  /// <summary>QA: the card's diamonds and coins and whether it is on screen.</summary>
  public string LeagueCardQa=>LeagueCardOpen?leagueShownKey:"";

  IEnumerator PlayLeagueCard(DesktopLeagueCard card){
   leagueRoot.gameObject.SetActive(true);leagueRoot.SetAsLastSibling();
   // fit the panel on any screen (an iPhone's 680-unit height, an iPad's 4:3): never cut
   var area=root.rect;float k=Mathf.Min(1f,(area.width-32)/920f,(area.height-24)/620f);leaguePanel.localScale=Vector3.one*k;
   leagueHeadline.text=K.Clean(card.headline);leagueTitle.text=K.Clean(card.title);leagueSubtitle.text=K.Clean(card.subtitle);
   leagueMoved.text=K.Clean(card.movedText);leagueMoved.color=card.moved=="up"?K.C("9BE07A"):card.moved=="down"?K.C("FF9A86"):SocialCream;
   leagueFrom.sprite=K.Icon(card.badgeFrom);leagueTo.sprite=K.Icon(card.badgeTo);
   bool moved=card.moved!="same";leagueFrom.gameObject.SetActive(moved);leagueArrow.gameObject.SetActive(moved);
   foreach(var part in leagueArrowParts)part.color=card.moved=="up"?K.C("7FCB5A"):card.moved=="down"?K.C("E86A55"):SocialGold;
   var to=leagueTo.rectTransform;to.anchorMin=to.anchorMax=new Vector2(moved?.78f:.5f,.55f);
   for(int i=0;i<3;i++){
    var (face,ring,name,col)=leaguePodium[i];
    string avatar=card.podiumAvatars!=null&&i<card.podiumAvatars.Length?card.podiumAvatars[i]:"";
    string who=card.podiumNames!=null&&i<card.podiumNames.Length?card.podiumNames[i]:"";
    var sprite=K.Icon(string.IsNullOrEmpty(avatar)?"Icons/medal":avatar);face.sprite=sprite;face.enabled=sprite;
    // (an unknown player of that week: the medal on the navy plate instead of a face)
    face.rectTransform.offsetMin=face.rectTransform.offsetMax=Vector2.zero;if(string.IsNullOrEmpty(avatar)){face.rectTransform.offsetMin=new Vector2(14,14);face.rectTransform.offsetMax=new Vector2(-14,-14);}
    name.text=K.Clean(who);name.color=card.place==i+1?SocialGold:SocialCream;
    col.localScale=new Vector3(1,0,1);
   }
   bool onPodium=card.place>=1&&card.place<=3;leagueMeBox.gameObject.SetActive(!onPodium&&card.place>0);
   leagueMeFace.sprite=K.Icon(card.avatar);leaguePlaceText.text="#"+card.place;
   leagueDiamonds.text="+0";leagueCoins.text="+0";
   leagueDiamondChip.gameObject.SetActive(card.diamonds>0);leagueCoinChip.gameObject.SetActive(card.coins>0);
   leagueButton.Apply(new DesktopButton{label=card.button,icon="Icons/diamond",variant="coin",enabled=true,action="",args="[]",route="",after="",ok="",fail="",badge=""});
   leagueDim.color=new Color(.05f,.07f,.15f,0);StartCoroutine(U.Fade(leagueDim,.82f,.3f));
   leaguePanel.localScale=Vector3.one*k*.6f;Sound("whoosh");
   yield return U.Scale(leaguePanel,Vector3.one*k,.38f,true);
   // the plinths rise (3rd, 2nd, 1st), my place pops
   foreach(var i in new[]{2,1,0}){StartCoroutine(U.Scale(leaguePodium[i].col,Vector3.one,.3f,true));Sound("pop",1+.08f*(2-i));yield return CheckoutUiKit.Wait(.14f);}
   if(onPodium){var mine=leaguePodium[card.place-1].col;StartCoroutine(U.Pop(mine,1.18f,.35f));U.Sparkles(this,leagueFx,U.PointIn(leagueFx,mine),14,200);}
   else if(card.place>0){StartCoroutine(U.Pop(leagueMeBox,1.15f,.3f));}
   yield return CheckoutUiKit.Wait(.25f);
   // the division: the old badge shrinks away, the new one pops in (up: sparkles; down: a softer drop)
   if(moved){
    leagueTo.transform.localScale=Vector3.zero;leagueFrom.transform.localScale=Vector3.one;
    yield return CheckoutUiKit.Wait(.2f);
    StartCoroutine(U.Scale(leagueFrom.transform,Vector3.one*.75f,.25f));
    yield return U.Scale(leagueTo.transform,Vector3.one,.42f,true);
    if(card.moved=="up"){Sound("success");U.Sparkles(this,leagueFx,U.PointIn(leagueFx,leagueTo.rectTransform),16,220);}
    else Sound("pop",.8f);
   } else {leagueTo.transform.localScale=Vector3.zero;yield return U.Scale(leagueTo.transform,Vector3.one,.4f,true);}
   // confetti and the prizes counting up
   LeagueConfetti(90);
   for(float t=0;t<.9f;t+=U.Dt){float f=Mathf.SmoothStep(0,1,t/.9f);leagueDiamonds.text="+"+Mathf.RoundToInt(card.diamonds*f);leagueCoins.text="+"+Mathf.RoundToInt(card.coins*f);yield return null;}
   leagueDiamonds.text="+"+card.diamonds;leagueCoins.text="+"+card.coins;
   if(card.diamonds>0||card.coins>0)Sound("coin_"+Random.Range(0,3));
   leagueRun=null;
  }
  void LeagueConfetti(int count){
   var from=new Vector2(0,leagueFx.rect.height*.18f);
   for(int i=0;i<count;i++){
    int row=Random.Range(0,CheckoutConfettiArt.RowCount),col=Random.Range(0,CheckoutConfettiArt.Cols);
    var go=new GameObject("Piece",typeof(RectTransform),typeof(Image));go.transform.SetParent(leagueFx,false);
    var img=go.GetComponent<Image>();img.sprite=CheckoutConfettiArt.Sprite(CheckoutConfettiArt.Gold,row,col);img.raycastTarget=false;
    var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);float size=Random.Range(18f,32f);r.sizeDelta=new Vector2(size,size);
    r.anchoredPosition=from+new Vector2(Random.Range(-260f,260f),Random.Range(-30f,30f));r.localRotation=Quaternion.Euler(0,0,Random.Range(0f,360f));
    float angle=Random.Range(40f,140f)*Mathf.Deg2Rad,speed=Random.Range(420f,900f);
    rankConfetti.Add(new SocialConfetto{rect=r,image=img,velocity=new Vector2(Mathf.Cos(angle)*speed,Mathf.Sin(angle)*speed),spin=Random.Range(-420f,420f),life=Random.Range(1.6f,2.6f)});
   }
  }
  void UpdateLeagueCard(){
   if(!LeagueCardOpen)return;
   if(leagueRoot.GetSiblingIndex()!=leagueRoot.parent.childCount-1)leagueRoot.SetAsLastSibling();
   if(leagueRays)leagueRays.transform.Rotate(0,0,-12*U.Dt);
   if(leagueRun==null&&leagueButton){float s=1+.03f*Mathf.Sin(Time.unscaledTime*4);leagueButton.transform.localScale=new Vector3(s,s,1);}
   // (the confetti of the card falls even while no board is open)
   if(!BoardOpen)UpdateRankBoard(Time.unscaledTime);
  }
 }
}
