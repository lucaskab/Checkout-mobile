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
 // Rankings v1 in the board window (desktop/pages/ranking.ts, board style "rank"). The top three stand on a festive
 // podium: a warm backdrop with faint dots, bunting swags over 2nd and 3rd, a spotlight on the winner, chunky marble
 // plinths with a gold trim and a big painted numeral, round framed faces (crown, rays and a shimmer on #1, medals on
 // all three), confetti when it opens. Effects live in a layer BEHIND the people: no particle ever crosses a name.
 // Over the rows: the league's prizes strip (Liga) or the rivalry card (Amigos, in the meter's place: me VS the friend
 // just above me). The ranked rows are BoardTileUi "rank" mode; my own row is pinned under them. Faces are always
 // round: a navy disc that clips the picture, a ring drawn over its edge (never square corners). The end-of-week card
 // is CheckoutDesktopHUD.LeagueCard.cs.
 public partial class CheckoutDesktopHUD {
  // One spacing scale for the ranking window and the end-of-league card (QA 03/11, Lucas: "mt coisa super colada"):
  // 4 / 8 / 12 / 16 / 24 canvas units (an iPhone's reference), used instead of per-element nudges.
  const float Sp1=4,Sp2=8,Sp3=12,Sp4=16,Sp5=24;
  static float RankRowH=>Phone?68:80;
  /// <summary>Height of this board's ranking rows (taller with the bar under the name, Amigos).</summary>
  float RankCellH=68;
  static float PodiumScale=>Phone?.72f:1f;
  static float PodiumHeight=>(Phone?252:322);
  static readonly Color[] PlinthEdge={K.C("C98A22"),K.C("8E99A6"),K.C("A35F2C")};
  static readonly Color[] PlinthFace={K.C("F4CE62"),K.C("D8DEE6"),K.C("E6A56B")};
  static readonly Color RankGoldTrim=K.C("F3C64E"),RankTeal=K.C("2E8CAE"),RankOrange=K.C("E07A3A"),RankCream=K.C("F7E8C8"),RankNavy=K.C("1D2B4F");
  readonly RectTransform[] rankStripLines=new RectTransform[2];
  RectTransform rankStrip,rankPodium,rankFx,podiumFx,podiumBunting;Image podiumSpot,podiumBack;readonly List<BoardChip> rankStripChips=new List<BoardChip>();
  readonly List<Image> buntingFlags=new List<Image>();readonly List<Image> buntingStrings=new List<Image>();float buntingWidth=-1;
  PodiumColumn[] podiumColumns;BoardTileUi rankPinned;RectTransform rankPinnedRect;Image rankPinnedGlow;
  string rankPodiumKey,rankScrollShown;float rankSparkleAt,rankPodiumGrow;RectTransform rankPodiumFloor;
  readonly List<SocialConfetto> rankConfetti=new List<SocialConfetto>();
  // the Amigos rivalry card
  RectTransform rivalRoot;Image rivalMeFace,rivalOtherFace,rivalMeIcon,rivalOtherIcon,rivalCrown;TextMeshProUGUI rivalText,rivalMeValue,rivalMeName,rivalOtherValue,rivalOtherName;
  CheckoutDesktopButton rivalButton;RectTransform rivalVs;

  void BuildRankBoard(){
   // (two lines of chips in a narrow window, an iPad: the four diamond prizes, then the chest and last week)
   rankStrip=N.Node("Rank strip",boardContent);N.Column(rankStrip.gameObject,6,new RectOffset(4,4,2,4));
   for(int r=0;r<2;r++){var line=N.Node("Line "+r,rankStrip);var row=N.Row(line.gameObject,10);row.childAlignment=TextAnchor.MiddleCenter;row.childForceExpandWidth=true;line.gameObject.AddComponent<LayoutElement>().preferredHeight=Phone?50:58;rankStripLines[r]=line;}
   rankStrip.gameObject.AddComponent<LayoutElement>().preferredHeight=Phone?56:64;rankStrip.gameObject.SetActive(false);
   BuildPodium();
   // My row pinned under the tiles (over the footer), the same look as the rows, with a soft gold halo.
   rankPinned=BoardTileUi.Create(this,boardGridArea);rankPinnedRect=(RectTransform)rankPinned.transform;
   rankPinnedGlow=N.Image(rankPinnedRect,"PinnedGlow",new Color(1,.8f,.25f,.5f),20);U.Stretch(rankPinnedGlow.rectTransform,Vector2.zero,Vector2.one,new Vector2(-4,-4),new Vector2(4,4));rankPinnedGlow.transform.SetAsFirstSibling();
   rankPinned.gameObject.SetActive(false);
   rankFx=N.Node("Rank fx",(RectTransform)boardWin.transform.Find("Window"));Stretch(rankFx,Vector2.zero,Vector2.zero);
   BuildRival();
  }

  // ------------------------------------------------------------------ podium
  void BuildPodium(){
   rankPodium=N.Node("Podium",boardContent);rankPodium.gameObject.AddComponent<LayoutElement>().preferredHeight=PodiumHeight;
   // the stage: warm cream with faint dots, a soft floor glow (instead of flat cream)
   podiumBack=N.Image(rankPodium,"Backdrop",K.C("F8E7C6"),22);U.Stretch(podiumBack.rectTransform,Vector2.zero,Vector2.one,new Vector2(4,0),new Vector2(-4,0));
   var warm=N.Image(podiumBack.transform,"Warm",new Color(1f,.82f,.5f,.28f),0);warm.sprite=U.Glow();U.Stretch(warm.rectTransform,new Vector2(.15f,-.2f),new Vector2(.85f,1.1f));
   var dots=N.Image(podiumBack.transform,"Dots",new Color(.62f,.42f,.2f,.09f),0);dots.sprite=CheckoutRankArt.Dots();dots.type=Image.Type.Tiled;U.Stretch(dots.rectTransform,Vector2.zero,Vector2.one,new Vector2(6,6),new Vector2(-6,-6));
   // the spotlight on the winner
   podiumSpot=N.Image(rankPodium,"Spot",new Color(1f,.96f,.82f,.55f),0);podiumSpot.sprite=CheckoutRankArt.Spotlight();var sr=podiumSpot.rectTransform;sr.anchorMin=sr.anchorMax=new Vector2(.5f,1);sr.pivot=new Vector2(.5f,1);sr.sizeDelta=new Vector2(PodiumHeight*.95f,PodiumHeight);sr.anchoredPosition=Vector2.zero;
   // bunting swags over 2nd and 3rd (the winner keeps the light)
   podiumBunting=N.Node("Bunting",rankPodium);U.Stretch(podiumBunting,Vector2.zero,Vector2.one);
   // confetti and sparkles: behind the people, clipped to the stage
   podiumFx=N.Node("Fx",rankPodium);U.Stretch(podiumFx,Vector2.zero,Vector2.one);podiumFx.gameObject.AddComponent<RectMask2D>();
   var floor=N.Image(rankPodium,"Floor",new Color(.55f,.36f,.16f,.24f),0);floor.sprite=U.Glow();U.Stretch(floor.rectTransform,new Vector2(.08f,0),new Vector2(.92f,0),new Vector2(0,-14),new Vector2(0,26));rankPodiumFloor=floor.rectTransform;
   podiumColumns=new PodiumColumn[3];
   for(int i=0;i<3;i++)podiumColumns[i]=PodiumColumn.Create(this,rankPodium,i+1);
   rankPodium.gameObject.SetActive(false);
  }
  /// <summary>Two garlands of pennants, each from a top corner swagging over a side place (laid out for the width).</summary>
  void LayoutBunting(){
   float w=rankPodium.rect.width,h=rankPodium.rect.height;if(w<100||Mathf.Abs(w-buntingWidth)<1&&buntingFlags.Count>0)return;buntingWidth=w;
   Color[] palette={RankTeal,RankCream,RankOrange,RankNavy,K.C("F0B43C")};
   float flagW=Phone?20:28,flagH=Phone?24:36,sag=Phone?14:26;int perSwag=Phone?7:8;
   int flag=0,line=0;
   for(int side=0;side<2;side++){
    float x0=side==0?w*.02f:w*.66f,x1=side==0?w*.34f:w*.98f;
    Vector2 P(float t)=>new Vector2(Mathf.Lerp(x0,x1,t),-6-Mathf.Sin(t*Mathf.PI)*sag);
    for(int k=0;k<=perSwag;k++){
     // the string between two pennants: a thin cord
     if(k<perSwag){
      var a=P(k/(float)perSwag);var b=P((k+1)/(float)perSwag);
      while(buntingStrings.Count<=line){var s=N.Image(podiumBunting,"Cord",K.C("7A5530"),0);buntingStrings.Add(s);}
      var cord=buntingStrings[line++].rectTransform;cord.anchorMin=cord.anchorMax=new Vector2(0,1);cord.pivot=new Vector2(0,.5f);
      cord.anchoredPosition=a;cord.sizeDelta=new Vector2(Vector2.Distance(a,b)+1,2.2f);cord.localRotation=Quaternion.Euler(0,0,Mathf.Atan2(b.y-a.y,b.x-a.x)*Mathf.Rad2Deg);
     }
     if(k==0||k==perSwag)continue;
     while(buntingFlags.Count<=flag){var f=N.Image(podiumBunting,"Pennant",Color.white,0);f.sprite=CheckoutRankArt.Pennant();buntingFlags.Add(f);}
     var img=buntingFlags[flag];img.color=palette[(flag+side)%palette.Length];
     var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(0,1);r.pivot=new Vector2(.5f,1);r.sizeDelta=new Vector2(flagW,flagH);
     var p=P(k/(float)perSwag);r.anchoredPosition=p+new Vector2(0,1);
     var tangent=P((k+.5f)/perSwag)-P((k-.5f)/perSwag);r.localRotation=Quaternion.Euler(0,0,Mathf.Atan2(tangent.y,tangent.x)*Mathf.Rad2Deg);
     flag++;
    }
   }
   // (a narrow stage, an iPad: the places slimmer, so names never run into the neighbour's)
   foreach(var col in podiumColumns){var cr=(RectTransform)col.transform;cr.sizeDelta=new Vector2(Mathf.Min(230*PodiumScale,w*.3f),cr.sizeDelta.y);}
   for(int i=0;i<buntingFlags.Count;i++)buntingFlags[i].gameObject.SetActive(i<flag);
   for(int i=0;i<buntingStrings.Count;i++)buntingStrings[i].gameObject.SetActive(i<line);
  }

  DesktopTile RankFind(DesktopBoard b,string id){
   if(b==null||string.IsNullOrEmpty(id))return null;
   if(b.podium!=null)foreach(var t in b.podium)if(t!=null&&t.id==id)return t;
   if(b.pinned!=null&&b.pinned.id==id)return b.pinned;
   return null;
  }

  void ApplyRankBoard(DesktopBoard b,bool fresh){
   bool rank=b.style=="rank";
   var strip=rank&&b.strip!=null?b.strip:new DesktopStat[0];
   while(rankStripChips.Count<strip.Length){
    var chip=BoardChip.Create(rankStripLines[0],false);
    // (a long value shrinks inside its chip, never past its edge)
    foreach(var tmp in chip.GetComponentsInChildren<TextMeshProUGUI>(true)){tmp.enableAutoSizing=true;tmp.fontSizeMax=tmp.fontSize;tmp.fontSizeMin=Mathf.Min(11,tmp.fontSize);tmp.overflowMode=TextOverflowModes.Ellipsis;}
    rankStripChips.Add(chip);
   }
   bool twoLines=BoardNarrow&&strip.Length>4;
   for(int i=0;i<rankStripChips.Count;i++){
    bool on=i<strip.Length;var chip=rankStripChips[i];chip.gameObject.SetActive(on);if(!on)continue;
    var line=rankStripLines[twoLines&&i>=4?1:0];if(chip.transform.parent!=line)chip.transform.SetParent(line,false);
    chip.transform.SetSiblingIndex(twoLines&&i>=4?i-4:i);chip.Apply(strip[i]);
    // (two lines: the chips of a line share it evenly; one line: each as wide as it needs; phones: a slimmer chip)
    var le=chip.GetComponent<LayoutElement>();le.preferredWidth=twoLines?10:-1;le.flexibleWidth=twoLines?1:-1;le.preferredHeight=Phone?50:58;
   }
   rankStripLines[1].gameObject.SetActive(twoLines);
   rankStrip.GetComponent<LayoutElement>().preferredHeight=(Phone?56:64)+(twoLines?(Phone?56:64):0);
   rankStrip.gameObject.SetActive(strip.Length>0);
   var podium=rank&&b.podium!=null&&b.podium.Length>=3?b.podium:null;
   rankPodium.gameObject.SetActive(podium!=null);
   if(podium!=null){
    SetPodiumGrow();
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
    float h=RankCellH;rankPinnedRect.anchorMin=new Vector2(0,0);rankPinnedRect.anchorMax=new Vector2(1,0);rankPinnedRect.pivot=new Vector2(.5f,0);
    rankPinnedRect.offsetMin=new Vector2(14,boardScrollBottom+2);rankPinnedRect.offsetMax=new Vector2(-14,boardScrollBottom+2+h);
    rankPinned.Apply(b.pinned,true,b.pinned.id==boardSelected);
    boardScrollBottom+=h+20;((RectTransform)boardScroll.transform).offsetMin=new Vector2(10,boardScrollBottom);
   }
   // the "more below" chevron: smaller, in the gap over my pinned row (never on its border)
   boardMore.sizeDelta=pinned?new Vector2(36,18):new Vector2(54,28);boardMoreDrop=pinned?10:2;
   // the header's numbers (4 AMIGOS, #5 ENTRE OS AMIGOS) with room inside their chips
   foreach(var chip in boardStatChips)chip.Roomy(rank);
   ApplyRival(rank?b.rival:null,b.meter);
  }

  // The podium fills the fold (QA 03/11): with whole rows only on the first view, the first row that would stand half
  // under the pinned row waits for a scroll, and the room it leaves goes to the podium (centred in it) instead of an
  // empty band. Measured on the content at the top of the list, so the same every refresh; true when it changed.
  bool RankFillFold(float height){
   var c=new Vector3[4];
   rankPodium.GetWorldCorners(c);float podiumBottom=-boardContent.InverseTransformPoint(c[0]).y;
   float first=float.MaxValue;
   foreach(var t in boardTiles){
    if(!t.gameObject.activeSelf)continue;((RectTransform)t.transform).GetWorldCorners(c);
    float top=-boardContent.InverseTransformPoint(c[1]).y,bottom=-boardContent.InverseTransformPoint(c[0]).y;
    if(top>=podiumBottom-1&&bottom>height+.5f&&top<first)first=top;
   }
   float grow=0;
   if(first<float.MaxValue){float g=height-(first-rankPodiumGrow);if(g>0&&g<=(Phone?150:200))grow=g;}
   if(Mathf.Abs(grow-rankPodiumGrow)<1)return false;
   rankPodiumGrow=grow;SetPodiumGrow();return true;
  }
  void SetPodiumGrow(){
   rankPodium.GetComponent<LayoutElement>().preferredHeight=PodiumHeight+rankPodiumGrow;
   float lift=rankPodiumGrow*.5f;
   foreach(var col in podiumColumns)((RectTransform)col.transform).anchoredPosition=new Vector2(0,6+lift);
   rankPodiumFloor.offsetMin=new Vector2(0,-14+lift);rankPodiumFloor.offsetMax=new Vector2(0,26+lift);
   podiumSpot.rectTransform.sizeDelta=new Vector2(PodiumHeight*.95f,PodiumHeight+rankPodiumGrow);
   buntingWidth=-1;
  }

  // "Ver minha posição": the row of that id comes into the middle of the list and is picked (a pop, no particles).
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
  }

  IEnumerator PodiumEntrance(){
   foreach(var col in podiumColumns)col.transform.localScale=new Vector3(1,0,1);
   // 3rd, 2nd, then the winner rise one after the other
   int[] rise={2,1,0};
   foreach(var i in rise){StartCoroutine(U.Scale(podiumColumns[i].transform,Vector3.one,.32f,true));yield return CheckoutUiKit.Wait(.12f);}
   yield return CheckoutUiKit.Wait(.2f);
   Sound("success",1.05f);
   // gentle confetti, behind the people (clipped to the stage)
   RankConfetti(U.PointIn(podiumFx,podiumColumns[0].Portrait)+new Vector2(0,40),34);
  }

  void RankConfetti(Vector2 from,int count){
   for(int i=0;i<count;i++){
    int row=Random.Range(0,CheckoutConfettiArt.RowCount),col=Random.Range(0,CheckoutConfettiArt.Cols);
    var go=new GameObject("Piece",typeof(RectTransform),typeof(Image));go.transform.SetParent(podiumFx,false);
    var img=go.GetComponent<Image>();img.sprite=CheckoutConfettiArt.Sprite(i%3==0?RankTeal:i%3==1?RankOrange:CheckoutConfettiArt.Gold,row,col);img.raycastTarget=false;
    var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);float size=Random.Range(14f,24f);r.sizeDelta=new Vector2(size,size);
    r.anchoredPosition=from+Random.insideUnitCircle*30;r.localRotation=Quaternion.Euler(0,0,Random.Range(0f,360f));
    float angle=Random.Range(25f,155f)*Mathf.Deg2Rad,speed=Random.Range(300f,620f);
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
   if(rankPinnedGlow&&rankPinned.gameObject.activeInHierarchy){var g=rankPinnedGlow.color;g.a=.38f+.16f*Mathf.Sin(t*2.2f);rankPinnedGlow.color=g;}
   if(rankPodium==null||!rankPodium.gameObject.activeInHierarchy)return;
   LayoutBunting();
   foreach(var col in podiumColumns)col.Tick(t);
   // the bunting sways a little; the spotlight breathes
   if(podiumBunting)podiumBunting.localRotation=Quaternion.Euler(0,0,Mathf.Sin(t*1.3f)*.35f);
   if(podiumSpot){var c=podiumSpot.color;c.a=.45f+.1f*Mathf.Sin(t*1.7f);podiumSpot.color=c;}
   // a little shine around the winner now and then (behind the faces and names)
   if(t>rankSparkleAt){rankSparkleAt=t+2.8f;U.Sparkles(this,podiumFx,U.PointIn(podiumFx,podiumColumns[0].Portrait),5,110);}
  }

  // One place of the podium: rays and a crown (#1), the round framed face with its medal, the name, the level ribbon
  // and the flag, the chunky plinth (marble, gold trim, big numeral; a shimmer sweeps the winner's).
  sealed class PodiumColumn:MonoBehaviour,IPointerClickHandler {
   CheckoutDesktopHUD hud;int place;string id;RectTransform rect,portrait,shine;Image ring,plate,clip,icon,rim,crown,rays,glow,plinth,plinthFace,flag,ribbon,stage,medal;
   TextMeshProUGUI name,number,numberShadow,value,ribbonText,trendText;float shineAt;Image trendIcon;
   public RectTransform Portrait=>portrait;
   public static PodiumColumn Create(CheckoutDesktopHUD hud,RectTransform parent,int place){
    float s=PodiumScale;
    var root=N.Node("Place "+place,parent);var c=root.gameObject.AddComponent<PodiumColumn>();c.hud=hud;c.place=place;c.rect=root;
    float x=place==1?.5f:place==2?.2f:.8f;root.anchorMin=root.anchorMax=new Vector2(x,0);root.pivot=new Vector2(.5f,0);root.sizeDelta=new Vector2(230*s,PodiumHeight);root.anchoredPosition=new Vector2(0,6);
    var hit=root.gameObject.AddComponent<Image>();hit.color=new Color(0,0,0,0);
    // (a phone's plinths keep room for the place and its value)
    // (taller 2nd/3rd plinths: the numeral stays big above the value)
    float plinthH=Mathf.Max(place==1?76:place==2?66:60,(place==1?96:place==2?76:62)*s),face=(place==1?106:88)*s;
    int i=place-1;
    // the plinth: a darker edge, the marble face with a gold trim on top, a shadowed big numeral, the value under it
    c.plinth=N.Image(root,"Plinth",PlinthEdge[i],14);U.Stretch(c.plinth.rectTransform,new Vector2(.06f,0),new Vector2(.94f,0),Vector2.zero,new Vector2(0,plinthH));
    c.plinthFace=N.Image(c.plinth.transform,"Face",PlinthFace[i],0);c.plinthFace.sprite=CheckoutRankArt.Plinth();c.plinthFace.type=Image.Type.Sliced;Stretch(c.plinthFace.rectTransform,new Vector2(4,6),new Vector2(-4,-7));
    c.plinthFace.gameObject.AddComponent<RectMask2D>();
    var trim=N.Image(c.plinth.transform,"Trim",RankGoldTrim,3);U.Stretch(trim.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(2,-7),new Vector2(-2,-1));
    var trimShine=N.Image(trim.transform,"Shine",new Color(1,1,1,.55f),2);U.Stretch(trimShine.rectTransform,new Vector2(0,.55f),Vector2.one,new Vector2(3,0),new Vector2(-3,-1));
    var band=N.Image(c.plinthFace.transform,"Shine",new Color(1,1,1,.22f),8);U.Stretch(band.rectTransform,new Vector2(0,.66f),Vector2.one,new Vector2(5,0),new Vector2(-5,-3));
    // (the winner's shimmer: a slanted light band sweeping across, clipped to the plinth)
    if(place==1){var sh=N.Image(c.plinthFace.transform,"Shimmer",new Color(1,1,1,.5f),0);sh.sprite=U.Glow();c.shine=sh.rectTransform;c.shine.anchorMin=new Vector2(0,0);c.shine.anchorMax=new Vector2(0,1);c.shine.pivot=new Vector2(.5f,.5f);c.shine.sizeDelta=new Vector2(36,40);c.shine.localRotation=Quaternion.Euler(0,0,-20);c.shine.anchoredPosition=new Vector2(-60,0);}
    float numSize=(place==1?60:50)*s;
    c.numberShadow=N.Text(c.plinthFace.transform,"NumberShadow",K.Headline,numSize,new Color(.3f,.18f,.06f,.35f));c.numberShadow.alignment=TextAlignmentOptions.Center;c.numberShadow.text=place.ToString();U.Stretch(c.numberShadow.rectTransform,new Vector2(0,.3f),Vector2.one,new Vector2(2,-3),new Vector2(2,-3));
    c.number=N.Text(c.plinthFace.transform,"Number",K.Headline,numSize,Color.white);c.number.alignment=TextAlignmentOptions.Center;c.number.text=place.ToString();
    c.number.outlineWidth=.24f;c.number.outlineColor=new Color32(110,66,22,230);U.Stretch(c.number.rectTransform,new Vector2(0,.3f),Vector2.one);
    // (the numeral fits above the value on the shortest plinth: it never runs into the points)
    foreach(var n in new[]{c.number,c.numberShadow}){n.enableAutoSizing=true;n.fontSizeMin=16;n.fontSizeMax=numSize;n.overflowMode=TextOverflowModes.Overflow;}
    c.value=N.Text(c.plinthFace.transform,"Value",K.Number,13*Mathf.Max(.85f,s),new Color(.25f,.16f,.06f,.9f));c.value.alignment=TextAlignmentOptions.Center;c.value.textWrappingMode=TextWrappingModes.NoWrap;
    c.value.enableAutoSizing=true;c.value.fontSizeMin=9;c.value.fontSizeMax=14;U.Stretch(c.value.rectTransform,new Vector2(0,0),new Vector2(1,.32f),new Vector2(Sp2,2),new Vector2(-Sp2,0));
    // the face first (rays, glow and crown with it), so the name and the ribbon are always drawn over any effect
    // plinth · 8 · level ribbon + flag · 6 · name · 8 · face (the crown sits low on the face, inside the stage)
    float infoH=24*s,nameH=26*Mathf.Max(.82f,s);
    float y=plinthH+Sp2;
    float yName=y+infoH+6,yFace=yName+nameH+Sp2;
    var holder=N.Node("Face",root);holder.anchorMin=holder.anchorMax=new Vector2(.5f,0);holder.pivot=new Vector2(.5f,0);holder.sizeDelta=new Vector2(face,face);holder.anchoredPosition=new Vector2(0,yFace);c.portrait=holder;
    if(place==1){
     c.rays=N.Image(holder,"Rays",new Color(1f,.9f,.5f,.5f),0);c.rays.sprite=LevelRaysSprite();U.At(c.rays.rectTransform,new Vector2(.5f,.5f),new Vector2(face*2.1f,face*2.1f));
     c.glow=N.Image(holder,"Glow",new Color(1f,.86f,.4f,.65f),0);c.glow.sprite=U.Glow();U.At(c.glow.rectTransform,new Vector2(.5f,.5f),new Vector2(face*1.6f,face*1.6f));
    }
    c.ring=N.Image(holder,"Ring",PlinthEdge[i],0);c.ring.sprite=K.Disc();Stretch(c.ring.rectTransform,new Vector2(-5,-5),new Vector2(5,5));
    c.plate=N.Image(holder,"Plate",PortraitNavy,0);c.plate.sprite=K.Disc();Stretch(c.plate.rectTransform,Vector2.zero,Vector2.zero);
    c.clip=K.RoundClip(holder,"Clip");K.SetRound(c.clip,true);
    c.icon=N.Image(c.clip.transform,"Icon",Color.white,0);c.icon.preserveAspect=true;Stretch(c.icon.rectTransform,Vector2.zero,Vector2.zero);
    c.rim=N.Image(holder,"Rim",PlinthFace[i],0);K.FitRim(c.rim,face,6*Mathf.Max(.8f,s));
    c.stage=N.Image(holder,"Stage",Color.white,0);c.stage.preserveAspect=true;U.At(c.stage.rectTransform,new Vector2(.86f,.12f),new Vector2(face*.34f,face*.34f));
    // gold / silver / bronze medal on the face's other corner
    c.medal=N.Image(holder,"Medal",place==1?Color.white:place==2?K.C("D7DEE6"):K.C("E9A46A"),0);c.medal.sprite=K.Icon("Icons/medal");c.medal.preserveAspect=true;U.At(c.medal.rectTransform,new Vector2(.12f,.1f),new Vector2(face*.36f,face*.36f));
    if(place==1){c.crown=N.Image(holder,"Crown",Color.white,0);c.crown.sprite=K.Icon("Icons/crown");c.crown.preserveAspect=true;U.At(c.crown.rectTransform,new Vector2(.5f,1),new Vector2(face*.56f,face*.56f),new Vector2(0,-face*.06f));c.crown.rectTransform.localRotation=Quaternion.Euler(0,0,-8);}
    // level ribbon + flag, then the name, above the plinth
    var info=N.Node("Info",root);info.anchorMin=new Vector2(0,0);info.anchorMax=new Vector2(1,0);info.pivot=new Vector2(.5f,0);info.offsetMin=new Vector2(0,y);info.offsetMax=new Vector2(0,y+infoH);
    var ir=N.Row(info.gameObject,(int)Sp2);ir.childAlignment=TextAnchor.MiddleCenter;
    c.ribbon=Pill(info,"Ribbon",PortraitNavy,out c.ribbonText,12,K.Label);c.ribbonText.characterSpacing=1;var rl=c.ribbon.gameObject.AddComponent<LayoutElement>();rl.preferredHeight=22*s;rl.preferredWidth=60;
    var flagEdge=N.Image(info,"FlagEdge",Color.white,3);var fl=flagEdge.gameObject.AddComponent<LayoutElement>();fl.preferredWidth=30*Mathf.Max(.85f,s);fl.preferredHeight=23*Mathf.Max(.85f,s);
    c.flag=N.Image(flagEdge.transform,"Flag",Color.white,0);c.flag.preserveAspect=true;Stretch(c.flag.rectTransform,new Vector2(2,2),new Vector2(-2,-2));
    // ▲/▼ since the board was last opened (Amigos)
    c.trendIcon=N.Image(info,"Trend",Color.white,0);c.trendIcon.sprite=CheckoutRankArt.Triangle();var tl=c.trendIcon.gameObject.AddComponent<LayoutElement>();tl.preferredWidth=tl.preferredHeight=14;
    c.trendText=N.Text(info,"TrendText",K.Number,13,Color.white);c.trendText.textWrappingMode=TextWrappingModes.NoWrap;var ttl=c.trendText.gameObject.AddComponent<LayoutElement>();ttl.preferredWidth=18;ttl.preferredHeight=16;
    c.trendText.outlineWidth=.25f;c.trendText.outlineColor=new Color32(255,250,240,255);
    c.name=N.Text(root,"Name",K.Headline,(place==1?19:17)*Mathf.Max(.82f,s),K.Ink);c.name.alignment=TextAlignmentOptions.Center;c.name.textWrappingMode=TextWrappingModes.NoWrap;c.name.overflowMode=TextOverflowModes.Ellipsis;
    c.name.outlineWidth=.18f;c.name.outlineColor=new Color32(255,246,226,255);c.name.enableAutoSizing=true;c.name.fontSizeMin=11;c.name.fontSizeMax=(place==1?19:17)*Mathf.Max(.82f,s);
    var nr=c.name.rectTransform;nr.anchorMin=new Vector2(0,0);nr.anchorMax=new Vector2(1,0);nr.pivot=new Vector2(.5f,0);nr.offsetMin=new Vector2(Sp1,yName);nr.offsetMax=new Vector2(-Sp1,yName+nameH); // (inside its own place: never over the neighbour's)
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
    bool trend=t.trend!=0;trendIcon.gameObject.SetActive(trend);trendText.gameObject.SetActive(trend);
    if(trend){bool up=t.trend>0;trendIcon.color=trendText.color=up?K.C("4FA83D"):K.C("D98A5E");trendIcon.rectTransform.localRotation=Quaternion.Euler(0,0,up?0:180);trendText.text=Mathf.Abs(t.trend).ToString();}
    // me on the podium: a gold name
    name.color=t.tone=="gold"?K.C("9A6A10"):K.Ink;
    rim.color=picked?K.C("FFF3B0"):PlinthFace[place-1];
   }
   public void Tick(float t){
    if(rays)rays.transform.localRotation=Quaternion.Euler(0,0,-t*14);
    if(glow){var c=glow.color;c.a=.5f+.18f*Mathf.Sin(t*2.4f);glow.color=c;}
    if(crown)crown.rectTransform.anchoredPosition=new Vector2(0,-portrait.sizeDelta.y*.06f+Mathf.Abs(Mathf.Sin(t*2.2f))*4);
    if(shine){
     // a sweep every 3.5 s
     float w=((RectTransform)shine.parent).rect.width;float k=(t%3.5f)/.9f;
     shine.anchoredPosition=new Vector2(k<1?Mathf.Lerp(-40,w+40,k):-60,0);shine.sizeDelta=new Vector2(36,((RectTransform)shine.parent).rect.height*1.6f);
    }
   }
   public void OnPointerClick(PointerEventData e){if(string.IsNullOrEmpty(id))return;hud.BoardSelect(id);StartCoroutine(U.Pop(portrait,1.08f,.22f));}
  }

  // ------------------------------------------------------------------ the Amigos rivalry card (in the meter's place)
  void BuildRival(){
   var parent=boardMeter.parent;
   var edge=N.Image(parent,"Rival",RankGoldTrim,20);rivalRoot=edge.rectTransform;rivalRoot.anchorMin=boardMeter.anchorMin;rivalRoot.anchorMax=boardMeter.anchorMax;rivalRoot.pivot=boardMeter.pivot;
   var back=N.Image(rivalRoot,"Back",RankNavy,18);Stretch(back.rectTransform,new Vector2(2,2),new Vector2(-2,-2));
   var shade=N.Image(back.transform,"Glow",new Color(.35f,.5f,.85f,.25f),0);shade.sprite=U.Glow();U.Stretch(shade.rectTransform,new Vector2(0,-.5f),new Vector2(.45f,1.5f));
   var dots=N.Image(back.transform,"Dots",new Color(1,1,1,.05f),0);dots.sprite=CheckoutRankArt.Dots();dots.type=Image.Type.Tiled;Stretch(dots.rectTransform,new Vector2(4,4),new Vector2(-4,-4));
   var b=back.transform;
   rivalMeFace=RivalFace(b,"Me",12,RankGoldTrim);
   rivalCrown=N.Image(rivalMeFace.transform.parent.parent,"Crown",Color.white,0);rivalCrown.sprite=K.Icon("Icons/crown");rivalCrown.preserveAspect=true;U.At(rivalCrown.rectTransform,new Vector2(.5f,1),new Vector2(28,28),new Vector2(0,6));rivalCrown.rectTransform.localRotation=Quaternion.Euler(0,0,-10);
   rivalMeName=U.Label(b,"MeName",K.Label,12,"F3C64E",TextAlignmentOptions.MidlineLeft);rivalMeName.characterSpacing=1;rivalMeName.overflowMode=TextOverflowModes.Overflow;
   rivalMeValue=U.Label(b,"MeValue",K.Number,19,"FFFFFF",TextAlignmentOptions.MidlineLeft);rivalMeValue.overflowMode=TextOverflowModes.Overflow;
   rivalMeIcon=N.Image(b,"MeIcon",Color.white,0);rivalMeIcon.preserveAspect=true;
   // the VS emblem: an orange burst with a gold rim, the letters a label
   rivalVs=N.Node("VS",b);
   var burstRim=N.Image(rivalVs,"Rim",RankGoldTrim,0);burstRim.sprite=CheckoutRankArt.Burst();U.Stretch(burstRim.rectTransform,Vector2.zero,Vector2.one,new Vector2(-3,-3),new Vector2(3,3));
   var burst=N.Image(rivalVs,"Burst",RankOrange,0);burst.sprite=CheckoutRankArt.Burst();U.Stretch(burst.rectTransform,Vector2.zero,Vector2.one);
   var vs=U.Label(rivalVs,"Text",K.Headline,20,"FFFFFF");U.Stretch(vs.rectTransform,Vector2.zero,Vector2.one);vs.text="VS";vs.outlineWidth=.25f;vs.outlineColor=new Color32(120,40,10,255);
   rivalOtherFace=RivalFace(b,"Other",0,K.C("C9D2DD"));
   rivalOtherName=U.Label(b,"OtherName",K.Label,12,"C9D2DD",TextAlignmentOptions.MidlineLeft);rivalOtherName.characterSpacing=1;rivalOtherName.enableAutoSizing=true;rivalOtherName.fontSizeMin=9;rivalOtherName.fontSizeMax=12;
   rivalOtherValue=U.Label(b,"OtherValue",K.Number,19,"FFFFFF",TextAlignmentOptions.MidlineLeft);rivalOtherValue.overflowMode=TextOverflowModes.Overflow;
   rivalOtherIcon=N.Image(b,"OtherIcon",Color.white,0);rivalOtherIcon.preserveAspect=true;
   rivalText=U.Label(b,"Text",K.Headline,22,"F7E8C8",TextAlignmentOptions.MidlineLeft);rivalText.enableAutoSizing=true;rivalText.fontSizeMin=12;rivalText.fontSizeMax=22;rivalText.textWrappingMode=TextWrappingModes.Normal;
   rivalButton=CheckoutDesktopButton.Create(b,46,17,14);rivalButton.Clicked=BoardPress;Destroy(rivalButton.GetComponent<LayoutElement>());
   rivalRoot.gameObject.SetActive(false);
  }
  Image RivalFace(Transform parent,string name,float x,Color ringColor){
   var holder=N.Node(name+"Face",parent);holder.anchorMin=holder.anchorMax=new Vector2(0,.5f);holder.pivot=new Vector2(0,.5f);holder.sizeDelta=new Vector2(46,46);holder.anchoredPosition=new Vector2(x,0);
   var ring=N.Image(holder,"Ring",ringColor,0);ring.sprite=K.Disc();Stretch(ring.rectTransform,new Vector2(-3,-3),new Vector2(3,3));
   var plate=N.Image(holder,"Plate",K.C("2A3D6B"),0);plate.sprite=K.Disc();Stretch(plate.rectTransform,Vector2.zero,Vector2.zero);
   var clip=K.RoundClip(holder,"Clip");K.SetRound(clip,true);
   var img=N.Image(clip.transform,"Icon",Color.white,0);img.preserveAspect=true;Stretch(img.rectTransform,Vector2.zero,Vector2.zero);
   var rim=N.Image(holder,"Rim",ringColor,0);K.FitRim(rim,46,3);
   return img;
  }
  /// <summary>The rivalry card over the Amigos board, in the meter's rect (the meter hides while it shows).</summary>
  void ApplyRival(DesktopRival r,DesktopMeter m){
   bool on=r!=null&&!string.IsNullOrEmpty(r.text)&&boardMeter.gameObject.activeSelf;
   rivalRoot.gameObject.SetActive(on);
   if(!on)return;
   boardMeter.gameObject.SetActive(false);
   rivalRoot.offsetMin=boardMeter.offsetMin;rivalRoot.offsetMax=boardMeter.offsetMax;
   float H=Mathf.Abs(boardMeter.offsetMax.y-boardMeter.offsetMin.y),face=Mathf.Min(44,H-Sp4);
   rivalMeFace.sprite=K.Icon(r.meIcon);rivalOtherFace.sprite=K.Icon(r.otherIcon);
   rivalCrown.gameObject.SetActive(r.lead);
   var colIcon=K.Icon(r.icon);Color iconTint=Color.white;
   rivalMeIcon.sprite=colIcon;rivalOtherIcon.sprite=colIcon;rivalMeIcon.color=rivalOtherIcon.color=iconTint;rivalMeIcon.enabled=rivalOtherIcon.enabled=colIcon;
   rivalMeName.text=K.Clean(r.meName).ToUpperInvariant();rivalMeValue.text=K.Clean(r.meValue);
   rivalOtherName.text=K.Clean(r.otherName).ToUpperInvariant();rivalOtherValue.text=K.Clean(r.otherValue);
   rivalText.text=K.Clean(r.text);
   // [me] value | VS | [friend] name + value | the gap in words | the opt-out button (a narrow window, an iPad: the
   // faces, the VS and the words; the values are in the rows)
   bool narrow=BoardNarrow;
   rivalMeName.gameObject.SetActive(!narrow);rivalMeValue.gameObject.SetActive(!narrow);rivalMeIcon.gameObject.SetActive(!narrow&&colIcon);
   rivalOtherName.gameObject.SetActive(!narrow);rivalOtherValue.gameObject.SetActive(!narrow);rivalOtherIcon.gameObject.SetActive(!narrow&&colIcon);
   // (the spacing scale: 16 from the edge, 12 from a face to its words, 8 from an icon to its number, 16 around the VS,
   // 24 before the sentence and before the button)
   float x=Sp4;
   var mf=(RectTransform)rivalMeFace.transform.parent.parent;mf.sizeDelta=new Vector2(face,face);mf.anchoredPosition=new Vector2(x,0);x+=face+Sp3;
   float meNum=rivalMeValue.GetPreferredValues(rivalMeValue.text).x,iconRoom=colIcon?20+Sp2:0;
   float valW=Mathf.Clamp(Mathf.Max(iconRoom+meNum,rivalMeName.GetPreferredValues(rivalMeName.text).x)+4,40,150);
   PlaceLeft(rivalMeName.rectTransform,x,12,valW,20);PlaceLeft(rivalMeIcon.rectTransform,x,-10,20,20);PlaceLeft(rivalMeValue.rectTransform,x+iconRoom,-10,Mathf.Max(20,valW-iconRoom),28);if(!narrow)x+=valW+Sp4;
   rivalVs.anchorMin=rivalVs.anchorMax=new Vector2(0,.5f);rivalVs.pivot=new Vector2(0,.5f);rivalVs.sizeDelta=new Vector2(face+2,face+2);rivalVs.anchoredPosition=new Vector2(x,0);x+=face+2+Sp4;
   var of=(RectTransform)rivalOtherFace.transform.parent.parent;of.sizeDelta=new Vector2(face,face);of.anchoredPosition=new Vector2(x,0);x+=face+Sp3;
   float otherNum=rivalOtherValue.GetPreferredValues(rivalOtherValue.text).x;
   float nameW=Mathf.Clamp(Mathf.Max(rivalOtherName.GetPreferredValues(rivalOtherName.text).x,iconRoom+otherNum)+4,60,Phone?190:220);
   PlaceLeft(rivalOtherName.rectTransform,x,12,nameW,20);PlaceLeft(rivalOtherIcon.rectTransform,x,-10,20,20);PlaceLeft(rivalOtherValue.rectTransform,x+iconRoom,-10,Mathf.Max(20,nameW-iconRoom),28);x+=narrow?Sp3:nameW+Sp5;
   // the button at the right end
   bool hasButton=r.button!=null&&!string.IsNullOrEmpty(r.button.label);rivalButton.gameObject.SetActive(hasButton);
   float right=Sp4;
   if(hasButton){
    rivalButton.Apply(r.button);var label=rivalButton.GetComponentInChildren<TextMeshProUGUI>(true);
    float w=Mathf.Max(Phone?92:84,(label?label.GetPreferredValues(K.Clean(r.button.label)).x*1.15f:60)+(string.IsNullOrEmpty(r.button.icon)?0:30)+34);
    var br=(RectTransform)rivalButton.transform;br.anchorMin=br.anchorMax=br.pivot=new Vector2(1,.5f);br.sizeDelta=new Vector2(w,Mathf.Min(46,H-Sp3));br.anchoredPosition=new Vector2(-right,0);right+=w+Sp5;
   }
   var tr=rivalText.rectTransform;tr.anchorMin=new Vector2(0,0);tr.anchorMax=new Vector2(1,1);tr.pivot=new Vector2(0,.5f);tr.offsetMin=new Vector2(x,Sp1);tr.offsetMax=new Vector2(-right,-Sp1);
  }
  static void PlaceLeft(RectTransform r,float x,float y,float w,float h){r.anchorMin=r.anchorMax=new Vector2(0,.5f);r.pivot=new Vector2(0,.5f);r.sizeDelta=new Vector2(w,h);r.anchoredPosition=new Vector2(x,y);}
 }
}
