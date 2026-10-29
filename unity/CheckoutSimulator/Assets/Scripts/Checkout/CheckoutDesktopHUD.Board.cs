using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // The game windows of the toolbar (page.layout == "board", data from desktop/pages/*-boards.ts): stock,
 // depot, deliveries, production, missions and trophies drawn as boards of tiles the player acts on, in the
 // spirit of Hay Day's barn and roadside shop, Township's order boards and the ordering tablet of Supermarket
 // Simulator: a coloured header with the numbers that matter, chunky tabs with red counters, a progress bar
 // with milestones, tiles with big art, warning ribbons, gauges, ticking timers and one-tap buttons, a side
 // panel with every action of the picked tile and big "do it all" buttons at the bottom. Tiles that want
 // attention glow and bob; successful actions burst into sparkles with a coin sound.
 public partial class CheckoutDesktopHUD {
  public static bool BoardOpen;

  SectionBar boardGroupTabs;GameObject boardIconBack;
  GameObject boardWin;Image boardHeader,boardIcon,boardBackdrop,boardMeterFill;RectTransform boardStats,boardTabsRow,boardMeter,boardMeterTrack,boardMeterMarks,boardBody,boardGridArea,boardContent,boardFooter,boardDetail,boardTipBar;
  TextMeshProUGUI boardTitle,boardSubtitle,boardCoins,boardDiamonds,boardMeterTitle,boardMeterText,boardTip,boardEmpty;Image boardMeterIcon;ScrollRect boardScroll,boardDetailScroll;
  readonly List<CheckoutDesktopButton> boardTabs=new List<CheckoutDesktopButton>();readonly List<GameObject> boardTabBadges=new List<GameObject>();
  readonly List<BoardChip> boardStatChips=new List<BoardChip>();readonly List<BoardMarkUi> boardMarks=new List<BoardMarkUi>();
  readonly List<BoardSection> boardSections=new List<BoardSection>();readonly List<BoardTileUi> boardTiles=new List<BoardTileUi>();
  readonly List<CheckoutDesktopButton> boardFooterButtons=new List<CheckoutDesktopButton>();
  BoardDetailUi boardDetailUi;DesktopBoard boardData;string boardShown,boardSelected;float boardReceivedAt;float boardMeterShown=-1;
  AudioSource boardSound;RectTransform boardPressed;string boardPressedVariant;GameObject boardDetailPanel;

  // Tile colours by tone: face, edge, ribbon.
  static Color ToneFace(string tone)=>tone=="success"?K.C("EFF8E6"):tone=="warning"?K.C("FFF4D6"):tone=="danger"?K.C("FDE9E2"):tone=="info"?K.C("E6F3F8"):tone=="gold"?K.C("FFF3C8"):tone=="locked"?K.C("EAE2D5"):K.Cream;
  static Color ToneEdge(string tone)=>tone=="success"?K.C("7DB357"):tone=="warning"?K.C("E0A93C"):tone=="danger"?K.C("D9694A"):tone=="info"?K.C("6FB0CA"):tone=="gold"?K.C("E0A441"):tone=="locked"?K.C("BCAE97"):K.Border;
  static Color ToneStrong(string tone)=>tone=="success"?K.C("4F9A2E"):tone=="warning"?K.C("E8962B"):tone=="danger"?K.C("D8462A"):tone=="info"?K.C("2E8CAE"):tone=="gold"?K.C("E0A021"):tone=="locked"?K.C("8A7560"):K.C("8A5A2B");

  // Phones: shorter header (no subtitle), slimmer meter, no clerk tip bar and a narrower side panel, so the tiles
  // get the height (one full row instead of a cut one).
  static float BoardHeaderH=>Phone?70:96;
  static float BoardDetailW=>Phone?330:424;

  // ------------------------------------------------------------------ build
  void BuildBoard(){
   var node=N.Node("Board window",root);boardWin=node.gameObject;Stretch(node,Vector2.zero,Vector2.zero);
   var dim=boardWin.AddComponent<Image>();dim.color=new Color(.10f,.07f,.04f,.58f);Clickable(boardWin,()=>host.Route(""));
   var window=Stretch(N.Node("Window",node),CheckoutScreen.Handheld?new Vector2(8,8):new Vector2(40,118),CheckoutScreen.Handheld?new Vector2(-8,-6):new Vector2(-40,-16));
   var edge=window.gameObject.AddComponent<Image>();edge.sprite=K.Rounded(30);edge.type=Image.Type.Sliced;edge.color=K.C("8A5A2B");
   window.gameObject.AddComponent<Button>().transition=Selectable.Transition.None;
   var face=N.Image(window,"Face",K.Paper,28);Stretch(face.rectTransform,new Vector2(4,9),new Vector2(-4,-4));
   boardSound=gameObject.AddComponent<AudioSource>();boardSound.playOnAwake=false;boardSound.volume=.5f;

   // Header band: icon, title, the numbers that matter, balances, close.
   boardHeader=N.Image(face.transform,"Header",K.C("2E8CAE"),26);var hr=boardHeader.rectTransform;hr.anchorMin=new Vector2(0,1);hr.anchorMax=Vector2.one;hr.pivot=new Vector2(.5f,1);hr.offsetMin=new Vector2(0,-BoardHeaderH);hr.offsetMax=Vector2.zero;
   var shine=N.Image(boardHeader.transform,"Shine",new Color(1,1,1,.12f),24);var shr=shine.rectTransform;shr.anchorMin=new Vector2(0,.55f);shr.anchorMax=Vector2.one;shr.offsetMin=new Vector2(6,0);shr.offsetMax=new Vector2(-6,-4);
   shine.gameObject.AddComponent<LayoutElement>().ignoreLayout=true;
   var row=N.Row(boardHeader.gameObject,12,Phone?new RectOffset(14,12,6,10):new RectOffset(18,16,10,14));row.childAlignment=TextAnchor.MiddleLeft;
   var iconBack=N.Image(boardHeader.transform,"IconBack",new Color(1,1,1,.95f),20);boardIconBack=iconBack.gameObject;var ib=iconBack.gameObject.AddComponent<LayoutElement>();ib.preferredWidth=ib.preferredHeight=Phone?48:68;
   boardIcon=N.Image(iconBack.transform,"Icon",Color.white,0);boardIcon.preserveAspect=true;Stretch(boardIcon.rectTransform,new Vector2(6,6),new Vector2(-6,-6));
   var titles=N.Node("Titles",boardHeader.transform);N.Column(titles.gameObject,0);var tl=titles.gameObject.AddComponent<LayoutElement>();tl.flexibleWidth=1;tl.minWidth=240;
   boardTitle=N.Text(titles,"Title",K.Headline,Phone?28:34,Color.white);boardTitle.textWrappingMode=TextWrappingModes.NoWrap;boardTitle.characterSpacing=1;
   boardSubtitle=N.Text(titles,"Subtitle",K.Body,15,new Color(1,1,1,.88f));boardSubtitle.textWrappingMode=TextWrappingModes.NoWrap;boardSubtitle.overflowMode=TextOverflowModes.Ellipsis;boardSubtitle.gameObject.SetActive(!Phone); // the title and tabs say it
   boardGroupTabs=MakeSections(titles);
   boardStats=N.Node("Stats",boardHeader.transform);var sr=N.Row(boardStats.gameObject,8);sr.childAlignment=TextAnchor.MiddleRight;
   boardCoins=Balance(boardHeader.transform,"Icons/coin",null);
   boardDiamonds=Balance(boardHeader.transform,"Icons/diamond",()=>host.Route("~loja:moedas"));
   var close=CheckoutDesktopButton.Create(boardHeader.transform,54,22,14);close.SetWidth(58);close.Clicked=_=>host.Route("");
   close.Apply(new DesktopButton{label="X",variant="danger",enabled=true,route="",action="",args="[]",after="",ok="",fail="",badge=""});

   // Tabs: chunky buttons with red counters.
   boardTabsRow=N.Node("Tabs",face.transform);var tr=boardTabsRow;tr.anchorMin=new Vector2(0,1);tr.anchorMax=Vector2.one;tr.pivot=new Vector2(.5f,1);tr.offsetMin=new Vector2(16,-BoardHeaderH-58);tr.offsetMax=new Vector2(-16,-BoardHeaderH-6);
   var trow=N.Row(boardTabsRow.gameObject,10);trow.childControlHeight=true;trow.childForceExpandHeight=true;

   // Meter: a long bar with milestones.
   var meter=N.Image(face.transform,"Meter",K.Cream,18);boardMeter=meter.rectTransform;boardMeter.anchorMin=new Vector2(0,1);boardMeter.anchorMax=Vector2.one;boardMeter.pivot=new Vector2(.5f,1);boardMeter.offsetMin=new Vector2(16,-222);boardMeter.offsetMax=new Vector2(-16,-160);
   var mEdge=N.Image(meter.transform,"Edge",K.Border,18);Stretch(mEdge.rectTransform,new Vector2(0,-3),Vector2.zero);mEdge.transform.SetAsFirstSibling();
   boardMeterIcon=N.Image(meter.transform,"Icon",Color.white,0);boardMeterIcon.preserveAspect=true;var mi=boardMeterIcon.rectTransform;mi.anchorMin=mi.anchorMax=new Vector2(0,.5f);mi.pivot=new Vector2(0,.5f);mi.sizeDelta=Phone?new Vector2(38,38):new Vector2(46,46);mi.anchoredPosition=new Vector2(12,0);
   boardMeterTitle=N.Text(meter.transform,"Title",K.Headline,19,K.Ink);boardMeterTitle.textWrappingMode=TextWrappingModes.NoWrap;var mt=boardMeterTitle.rectTransform;mt.anchorMin=new Vector2(0,.5f);mt.anchorMax=new Vector2(0,1);mt.pivot=new Vector2(0,1);mt.offsetMin=new Vector2(66,0);mt.offsetMax=new Vector2(330,-6);
   boardMeterText=N.Text(meter.transform,"Text",K.Body,14,K.Muted);boardMeterText.textWrappingMode=TextWrappingModes.NoWrap;boardMeterText.overflowMode=TextOverflowModes.Ellipsis;var mx=boardMeterText.rectTransform;mx.anchorMin=new Vector2(0,0);mx.anchorMax=new Vector2(0,.5f);mx.pivot=new Vector2(0,0);mx.offsetMin=new Vector2(66,6);mx.offsetMax=new Vector2(430,0);
   var track=N.Image(meter.transform,"Track",K.C("EADBC4"),11);boardMeterTrack=track.rectTransform;boardMeterTrack.anchorMin=new Vector2(0,.5f);boardMeterTrack.anchorMax=new Vector2(1,.5f);boardMeterTrack.offsetMin=new Vector2(450,-11);boardMeterTrack.offsetMax=new Vector2(-30,11);
   boardMeterFill=N.Image(track.transform,"Fill",K.C("5DA637"),11);var mf=boardMeterFill.rectTransform;mf.anchorMin=Vector2.zero;mf.anchorMax=new Vector2(0,1);mf.offsetMin=mf.offsetMax=Vector2.zero;
   var gloss=N.Image(boardMeterFill.transform,"Gloss",new Color(1,1,1,.28f),8);var gr=gloss.rectTransform;gr.anchorMin=new Vector2(0,.55f);gr.anchorMax=Vector2.one;gr.offsetMin=new Vector2(3,0);gr.offsetMax=new Vector2(-3,-2);
   boardMeterMarks=Stretch(N.Node("Marks",track.transform),Vector2.zero,Vector2.zero);

   // Body: tiles on the left, the picked tile on the right.
   boardBody=Stretch(N.Node("Body",face.transform),new Vector2(0,0),new Vector2(0,-228));
   var area=N.Image(boardBody,"Tiles area",K.C("F3E3C8"),22);boardGridArea=area.rectTransform;boardGridArea.anchorMin=Vector2.zero;boardGridArea.anchorMax=Vector2.one;boardGridArea.offsetMin=new Vector2(16,14);boardGridArea.offsetMax=new Vector2(-BoardDetailW-12,0);
   boardBackdrop=N.Image(area.transform,"Backdrop",new Color(1,1,1,.22f),0);boardBackdrop.preserveAspect=false;Stretch(boardBackdrop.rectTransform,new Vector2(4,4),new Vector2(-4,-4));
   boardScroll=Scroll(area.transform,"Tiles",true,out boardContent);Stretch((RectTransform)boardScroll.transform,new Vector2(10,124),new Vector2(-6,-8));
   var col=boardContent.GetComponent<VerticalLayoutGroup>();col.spacing=6;col.padding=new RectOffset(8,14,6,16);
   boardEmpty=N.Text(area.transform,"Empty",K.Headline,22,K.Muted);boardEmpty.alignment=TextAlignmentOptions.Center;Stretch(boardEmpty.rectTransform,new Vector2(40,140),new Vector2(-40,-40));
   // Tip bar (the clerk's advice) and the big buttons.
   var tip=N.Image(area.transform,"Tip",K.C("FFF8E8"),16);boardTipBar=tip.rectTransform;boardTipBar.anchorMin=Vector2.zero;boardTipBar.anchorMax=new Vector2(1,0);boardTipBar.pivot=new Vector2(.5f,0);boardTipBar.offsetMin=new Vector2(10,70);boardTipBar.offsetMax=new Vector2(-10,116);
   var clerk=N.Image(tip.transform,"Clerk",Color.white,0);clerk.sprite=K.Icon("Icons/manager");clerk.preserveAspect=true;var cr=clerk.rectTransform;cr.anchorMin=cr.anchorMax=new Vector2(0,.5f);cr.pivot=new Vector2(0,.5f);cr.sizeDelta=new Vector2(40,40);cr.anchoredPosition=new Vector2(8,0);
   boardTip=N.Text(tip.transform,"Text",K.Body,15,K.Ink);boardTip.textWrappingMode=TextWrappingModes.Normal;boardTip.overflowMode=TextOverflowModes.Ellipsis;boardTip.alignment=TextAlignmentOptions.MidlineLeft;Stretch(boardTip.rectTransform,new Vector2(56,2),new Vector2(-12,-2));
   boardFooter=N.Node("Footer",area.transform);boardFooter.anchorMin=Vector2.zero;boardFooter.anchorMax=new Vector2(1,0);boardFooter.pivot=new Vector2(.5f,0);boardFooter.offsetMin=new Vector2(10,10);boardFooter.offsetMax=new Vector2(-10,64);
   var fr=N.Row(boardFooter.gameObject,10);fr.childControlHeight=true;fr.childForceExpandHeight=true;fr.childForceExpandWidth=true;

   var detail=N.Image(boardBody,"Detail",K.Cream,22);boardDetailPanel=detail.gameObject;var dr=detail.rectTransform;dr.anchorMin=new Vector2(1,0);dr.anchorMax=Vector2.one;dr.pivot=new Vector2(1,.5f);dr.offsetMin=new Vector2(-BoardDetailW,14);dr.offsetMax=new Vector2(-16,0);
   var dEdge=N.Image(detail.transform,"Edge",K.Border,22);Stretch(dEdge.rectTransform,new Vector2(0,-4),Vector2.zero);dEdge.transform.SetAsFirstSibling();
   boardDetailScroll=Scroll(detail.transform,"Content",true,out boardDetail);Stretch((RectTransform)boardDetailScroll.transform,new Vector2(10,10),new Vector2(-6,-10));
   boardDetailUi=BoardDetailUi.Create(this,boardDetail);
   boardWin.SetActive(false);
  }

  // ------------------------------------------------------------------ apply
  void ApplyBoard(DesktopView v){
   bool on=v.hasPage&&v.page!=null&&v.page.layout=="board"&&v.page.board!=null&&v.page.board.tiles!=null;
   if(boardWin.activeSelf!=on)boardWin.SetActive(on);BoardOpen=on;
   if(!on){boardShown=null;return;}
   var p=v.page;var b=p.board;boardData=b;boardReceivedAt=Time.realtimeSinceStartup;
   string page=(p.route??"").Split(':')[0];bool fresh=page!=boardShown;
   // A header tab switch (Produtos, Missões) swaps the window in place: no opening pop.
   if(fresh){boardShown=page;boardLaneStates.Clear();boardSelected=string.IsNullOrEmpty(b.focus)?null:b.focus;boardMeterShown=-1;if(!TakeSectionHop())StartCoroutine(U.Pop(boardWin.transform.Find("Window"),1.02f,.22f));}
   boardCoins.text=v.coins;boardDiamonds.text=v.diamonds;
   boardHeader.color=K.C(string.IsNullOrEmpty(b.tint)?"2E8CAE":b.tint);
   boardTitle.text=K.Clean(p.title);boardSubtitle.text=K.Clean(p.subtitle);
   var icon=K.Icon(p.icon);boardIcon.sprite=icon;boardIcon.enabled=icon;
   // Windows of a toolbar group: the sibling windows as big tabs instead of the title (the tabs have icons).
   bool grouped=ApplySections(boardGroupTabs,p.sections,boardTitle,boardSubtitle,!Phone);
   if(boardIconBack)boardIconBack.SetActive(!grouped);
   var back=K.Icon(b.backdrop);boardBackdrop.sprite=back;boardBackdrop.enabled=back;
   ApplyBoardStats(b.stats??new DesktopStat[0]);
   ApplyBoardTabs(p.tabs??new DesktopButton[0]);
   bool hasTabs=p.tabs!=null&&p.tabs.Length>0;boardTabsRow.gameObject.SetActive(hasTabs);
   bool hasMeter=b.meter!=null&&b.meter.max>0;boardMeter.gameObject.SetActive(hasMeter);
   // Everything below the header moves up when there are no tabs or no meter.
   float top=BoardHeaderH+(hasTabs?58:0),meterH=62;
   boardMeter.offsetMin=new Vector2(16,-top-6-meterH);boardMeter.offsetMax=new Vector2(-16,-top-6);
   boardBody.offsetMax=new Vector2(0,-(top+(hasMeter?meterH+12:4)));
   if(hasMeter)ApplyBoardMeter(b.meter,fresh);
   // Delivery lanes take the whole width: no side panel.
   bool road=b.style=="road";
   boardGridArea.offsetMax=new Vector2(road?-16:-BoardDetailW-12,0);
   ApplyBoardTiles(b);
   ApplyBoardFooter(b);
   if(fresh){Canvas.ForceUpdateCanvases();boardScroll.verticalNormalizedPosition=1;}
   ShopOpen=true;
  }

  void ApplyBoardStats(DesktopStat[] stats){
   while(boardStatChips.Count<stats.Length)boardStatChips.Add(BoardChip.Create(boardStats,true));
   // A narrow screen (iPad, 4:3) has no room for the numbers next to the tabs and the balances: they pushed the X off the
   // screen and covered the Entregas tab (onboarding QA 29/10). There the header keeps one number, or none.
   float width=boardHeader.rectTransform.rect.width;int room=width<1000?0:width<1200?1:stats.Length;
   for(int i=0;i<boardStatChips.Count;i++){bool on=i<stats.Length&&i<room;boardStatChips[i].gameObject.SetActive(on);if(on)boardStatChips[i].Apply(stats[i]);}
  }

  void ApplyBoardTabs(DesktopButton[] tabs){
   while(boardTabs.Count<tabs.Length){
    var b=CheckoutDesktopButton.Create(boardTabsRow,48,17,16);b.Clicked=x=>{Sound("tap",1.1f);Press(x);};boardTabs.Add(b);
    var pill=N.Image(b.transform,"Badge",K.C("E15533"),11);var pr=pill.rectTransform;pr.anchorMin=pr.anchorMax=pr.pivot=Vector2.one;pr.anchoredPosition=new Vector2(6,8);pr.sizeDelta=new Vector2(30,24);
    var t=N.Text(pill.transform,"Text",K.Number,14,Color.white);t.alignment=TextAlignmentOptions.Center;Stretch(t.rectTransform,Vector2.zero,Vector2.zero);
    boardTabBadges.Add(pill.gameObject);
   }
   for(int i=0;i<boardTabs.Count;i++){
    bool on=i<tabs.Length;boardTabs[i].gameObject.SetActive(on);if(!on)continue;
    var tab=tabs[i];boardTabs[i].Apply(tab);
    var label=boardTabs[i].GetComponentInChildren<TextMeshProUGUI>(true);
    float width=(label?label.GetPreferredValues(K.Clean(tab.label)).x:80)+(string.IsNullOrEmpty(tab.icon)?0:30)+44;
    boardTabs[i].SetWidth(Mathf.Max(Phone?96:110,width));
    bool badge=!string.IsNullOrEmpty(tab.badge);boardTabBadges[i].SetActive(badge);
    if(badge)boardTabBadges[i].GetComponentInChildren<TextMeshProUGUI>().text=tab.badge;
   }
   // Phones: a row wider than the window (8 trophy categories) shrinks to fit; the labels shrink with it.
   float room=boardTabsRow.rect.width>100?boardTabsRow.rect.width:1240,total=0;int shown=0;
   for(int i=0;i<tabs.Length&&i<boardTabs.Count;i++){total+=boardTabs[i].GetComponent<LayoutElement>().preferredWidth;shown++;}
   total+=Mathf.Max(0,shown-1)*10;
   if(Phone&&total>room){float k=(room-Mathf.Max(0,shown-1)*10)/(total-Mathf.Max(0,shown-1)*10);for(int i=0;i<shown;i++)boardTabs[i].SetWidth(Mathf.Floor(boardTabs[i].GetComponent<LayoutElement>().preferredWidth*k));}
  }

  void ApplyBoardMeter(DesktopMeter m,bool fresh){
   boardMeterTitle.text=K.Clean(m.title);boardMeterText.text=K.Clean(m.text);
   var icon=K.Icon(m.icon);boardMeterIcon.sprite=icon;boardMeterIcon.enabled=icon;
   boardMeterFill.color=ToneStrong(string.IsNullOrEmpty(m.tone)?"success":m.tone);
   float target=Mathf.Clamp01(m.value/Mathf.Max(.0001f,m.max));
   if(fresh||boardMeterShown<0)boardMeterShown=0;
   boardMeterTarget=target;
   var marks=m.marks??new DesktopMark[0];
   while(boardMarks.Count<marks.Length)boardMarks.Add(BoardMarkUi.Create(this,boardMeterMarks));
   for(int i=0;i<boardMarks.Count;i++){bool on=i<marks.Length;boardMarks[i].gameObject.SetActive(on);if(on)boardMarks[i].Apply(marks[i],m.max);}
  }
  float boardMeterTarget;

  void ApplyBoardTiles(DesktopBoard b){
   var tiles=b.tiles;bool road=b.style=="road";bool rows=b.style=="row"||road;
   int columns=Mathf.Max(1,b.columns);if(Phone)columns=Mathf.Min(columns,4); // phones: wider cards, ribbons clear of the badges
   // The window has a fixed size on the 1600×1000 canvas: before its first layout use that width.
   float width=boardGridArea.rect.width>100?boardGridArea.rect.width-40:(road?1440:1020);
   var cell=road?new Vector2(width-10,LaneHeight):rows?new Vector2(width-10,108):new Vector2(Mathf.Floor((width-(columns-1)*14f)/columns),268);
   // Sections: a title each time the group changes.
   int section=-1;string group=null;
   if(road)while(boardLanes.Count<tiles.Length)boardLanes.Add(BoardLaneUi.Create(this,boardContent));
   else while(boardTiles.Count<tiles.Length)boardTiles.Add(BoardTileUi.Create(this,boardContent));
   for(int i=0;i<tiles.Length;i++){
    var t=tiles[i];string g=t.group??"";
    if(section<0||g!=group){section++;group=g;
     if(boardSections.Count<=section)boardSections.Add(BoardSection.Create(boardContent));
     var s=boardSections[section];s.gameObject.SetActive(true);s.transform.SetSiblingIndex(section);s.Apply(g,cell,rows,columns);}
    Component ui=road?(Component)boardLanes[i]:boardTiles[i];ui.gameObject.SetActive(true);
    if(ui.transform.parent!=boardSections[section].grid)ui.transform.SetParent(boardSections[section].grid,false);
    ui.transform.SetAsLastSibling();
    if(road){
     var laneUi=boardLanes[i];laneUi.Apply(t);
     // A truck that reaches the dock while the window is open honks.
     string key=t.id.StartsWith("d")?t.id:null;
     if(key!=null&&!boardLaneStates.ContainsKey(key)&&boardLaneStates.Count>0)LaneArrived(laneUi);
    }
    else boardTiles[i].Apply(t,rows,t.id==SelectedId(tiles));
   }
   if(road){
    boardLaneStates.Clear();boardLaneStates["_"]="";
    foreach(var t in tiles)boardLaneStates[t.id]=t.lane;
   } else boardLaneStates.Clear();
   for(int i=section+1;i<boardSections.Count;i++)boardSections[i].gameObject.SetActive(false);
   for(int i=road?0:tiles.Length;i<boardTiles.Count;i++)boardTiles[i].gameObject.SetActive(false);
   for(int i=road?tiles.Length:0;i<boardLanes.Count;i++)boardLanes[i].gameObject.SetActive(false);
   boardEmpty.gameObject.SetActive(tiles.Length==0);boardEmpty.text=K.Clean(b.empty);
   if(road){boardDetailPanel.SetActive(false);return;}
   boardDetailPanel.SetActive(true);
   var picked=FindTile(tiles,SelectedId(tiles));
   boardDetailUi.gameObject.SetActive(picked!=null);if(picked!=null)boardDetailUi.Apply(picked,rows);
  }
  string SelectedId(DesktopTile[] tiles){
   if(!string.IsNullOrEmpty(boardSelected)&&FindTile(tiles,boardSelected)!=null)return boardSelected;
   return tiles.Length>0?tiles[0].id:null;
  }
  static DesktopTile FindTile(DesktopTile[] tiles,string id){if(id==null)return null;foreach(var t in tiles)if(t.id==id)return t;return null;}

  void ApplyBoardFooter(DesktopBoard b){
   var buttons=b.footer??new DesktopButton[0];
   while(boardFooterButtons.Count<buttons.Length){var x=CheckoutDesktopButton.Create(boardFooter,54,18,16);x.Clicked=BoardPress;boardFooterButtons.Add(x);}
   for(int i=0;i<boardFooterButtons.Count;i++){bool on=i<buttons.Length;boardFooterButtons[i].gameObject.SetActive(on);if(on)boardFooterButtons[i].Apply(buttons[i]);}
   boardFooter.gameObject.SetActive(buttons.Length>0);
   // Phones skip the clerk's tip: the tabs' red counters and the footer buttons already say it.
   bool tip=!Phone&&!string.IsNullOrEmpty(b.tip);
   boardTip.text=K.Clean(b.tip);boardTipBar.gameObject.SetActive(tip);
   // Without big buttons or tip the tiles take the room.
   float bottom=(buttons.Length>0?64:6)+(tip?52:0)+6;
   boardTipBar.offsetMin=new Vector2(10,(buttons.Length>0?70:10));boardTipBar.offsetMax=new Vector2(-10,(buttons.Length>0?116:56));
   ((RectTransform)boardScroll.transform).offsetMin=new Vector2(10,bottom);
  }

  // ------------------------------------------------------------------ interaction
  public void BoardSelect(string id){
   if(boardData==null||id==boardSelected)return;
   boardSelected=id;Sound("tap");
   foreach(var t in boardTiles)if(t.gameObject.activeSelf)t.Select(t.Id==id);
   var picked=FindTile(boardData.tiles,id);
   if(picked!=null){boardDetailUi.gameObject.SetActive(true);boardDetailUi.Apply(picked,boardData.style=="row");boardDetailScroll.verticalNormalizedPosition=1;StartCoroutine(U.Pop(boardDetailUi.transform,1.03f,.2f));}
  }
  public void BoardPress(CheckoutDesktopButton button){
   if(button==null||button.Data==null)return;
   boardPressed=(RectTransform)button.transform;boardPressedVariant=button.Data.variant;
   if(!button.Data.enabled){Sound("bonk",1.1f);StartCoroutine(U.Shake(boardPressed,.25f,8));}
   else Sound("tap");
   Press(button);
  }
  // Called by Result(): a successful board action bursts into sparkles where it was pressed.
  void BoardFeedback(bool ok){
   if(!BoardOpen||!boardPressed)return;
   var space=(RectTransform)boardWin.transform;
   if(ok){
    var at=U.PointIn(space,boardPressed);
    U.Sparkles(this,space,at,10,150);
    Sound(boardPressedVariant=="success"?"success":boardPressedVariant=="coin"||boardPressedVariant=="gem"?"coin_"+Random.Range(0,3):"pop");
   }
   else{Sound("card_no");StartCoroutine(U.Shake(boardPressed,.3f,10));}
   boardPressed=null;
  }
  /// <summary>The HUD's tap sound, for panels drawn elsewhere (the build tray).</summary>
  public void Tap()=>Sound("tap",1.05f);
  void Sound(string name,float pitch=1){var clip=U.Sfx(name);if(!clip||!boardSound)return;boardSound.pitch=pitch;boardSound.PlayOneShot(clip);}

  // Timers tick, gauges slide, ready tiles glow (called from Update).
  void UpdateBoard(){
   if(!BoardOpen||boardData==null)return;
   double now=boardData.now+(Time.realtimeSinceStartup-boardReceivedAt)*1000.0;
   float t=Time.unscaledTime;
   foreach(var tile in boardTiles)if(tile.gameObject.activeInHierarchy)tile.Tick(now,t);
   foreach(var lane in boardLanes)if(lane.gameObject.activeInHierarchy)lane.Tick(now,t);
   boardDetailUi.Tick(now,t);
   foreach(var mark in boardMarks)if(mark.gameObject.activeSelf)mark.Tick(t);
   if(boardMeter.gameObject.activeSelf){
    boardMeterShown=Mathf.MoveTowards(boardMeterShown,boardMeterTarget,Time.unscaledDeltaTime*.8f);
    boardMeterFill.rectTransform.anchorMax=new Vector2(Mathf.Max(.015f,boardMeterShown),1);
   }
  }

  public static string Clock(double ms){
   long s=(long)System.Math.Ceiling(System.Math.Max(0,ms)/1000.0);long m=s/60;
   return m>=60?$"{m/60}h{m%60:00}":$"{m}:{s%60:00}";
  }

  // ------------------------------------------------------------------ pieces
  // A number in the header (or a fact in the side panel): icon, value, label.
  class BoardChip:MonoBehaviour {
   Image back,icon;TextMeshProUGUI value,label;bool header;
   public static BoardChip Create(Transform parent,bool header){
    var root=N.Node("Stat",parent);var chip=root.gameObject.AddComponent<BoardChip>();chip.header=header;
    chip.back=root.gameObject.AddComponent<Image>();chip.back.sprite=K.Rounded(16);chip.back.type=Image.Type.Sliced;chip.back.color=header?new Color(0,0,0,.22f):K.C("FBEEDA");
    var le=root.gameObject.AddComponent<LayoutElement>();le.preferredHeight=header?(Phone?52:58):60;le.minWidth=header?118:0;
    var row=N.Row(root.gameObject,8,header&&Phone?new RectOffset(10,12,2,2):new RectOffset(10,12,6,6));row.childAlignment=TextAnchor.MiddleLeft;
    chip.icon=N.Image(root,"Icon",Color.white,0);chip.icon.preserveAspect=true;var il=chip.icon.gameObject.AddComponent<LayoutElement>();il.preferredWidth=il.preferredHeight=header?34:32;
    var texts=N.Node("Texts",root);N.Column(texts.gameObject,-2);
    chip.value=N.Text(texts,"Value",K.Number,header?22:19,header?Color.white:K.Ink);chip.value.textWrappingMode=TextWrappingModes.NoWrap;
    chip.label=N.Text(texts,"Label",K.Label,header&&Phone?11:12,header?new Color(1,1,1,.82f):K.Muted);chip.label.textWrappingMode=TextWrappingModes.NoWrap;
    return chip;
   }
   public void Apply(DesktopStat s){
    var sprite=K.Icon(s.icon);icon.sprite=sprite;icon.gameObject.SetActive(sprite);
    value.text=K.Clean(s.value);label.text=K.Clean(s.label).ToUpperInvariant();
    if(header)back.color=string.IsNullOrEmpty(s.tone)?new Color(0,0,0,.22f):Color.Lerp(ToneStrong(s.tone),Color.black,.15f);
    else{back.color=string.IsNullOrEmpty(s.tone)?K.C("FBEEDA"):ToneFace(s.tone);value.color=string.IsNullOrEmpty(s.tone)?K.Ink:ToneStrong(s.tone);}
   }
  }

  // A milestone on the meter: chest/trophy icon on the bar; ready ones bounce and can be clicked.
  class BoardMarkUi:MonoBehaviour,IPointerClickHandler {
   CheckoutDesktopHUD hud;Image glow,icon,check;DesktopMark data;
   public static BoardMarkUi Create(CheckoutDesktopHUD hud,RectTransform parent){
    var root=N.Node("Mark",parent);var m=root.gameObject.AddComponent<BoardMarkUi>();m.hud=hud;root.sizeDelta=new Vector2(56,56);
    m.glow=N.Image(root,"Glow",new Color(1,.85f,.3f,.0f),0);m.glow.sprite=U.Glow();Stretch(m.glow.rectTransform,new Vector2(-22,-22),new Vector2(22,22));
    var hit=root.gameObject.AddComponent<Image>();hit.color=new Color(0,0,0,0);
    m.icon=N.Image(root,"Icon",Color.white,0);m.icon.preserveAspect=true;Stretch(m.icon.rectTransform,Vector2.zero,Vector2.zero);
    m.check=N.Image(root,"Check",Color.white,0);m.check.sprite=K.Icon("Icons/success");m.check.preserveAspect=true;var cr=m.check.rectTransform;cr.anchorMin=cr.anchorMax=new Vector2(1,0);cr.sizeDelta=new Vector2(24,24);cr.anchoredPosition=new Vector2(-4,6);
    return m;
   }
   public void Apply(DesktopMark mark,float max){
    data=mark;var r=(RectTransform)transform;r.anchorMin=r.anchorMax=new Vector2(Mathf.Clamp01(mark.at/Mathf.Max(.0001f,max)),.5f);r.anchoredPosition=Vector2.zero;
    icon.sprite=K.Icon(mark.icon);icon.color=mark.state=="locked"?new Color(.55f,.5f,.45f,.85f):Color.white;
    check.gameObject.SetActive(mark.state=="done");
   }
   public void Tick(float t){
    bool ready=data!=null&&data.state=="ready";
    glow.color=new Color(1,.85f,.3f,ready?.45f+.25f*Mathf.Sin(t*5):0);
    icon.rectTransform.anchoredPosition=new Vector2(0,ready?Mathf.Abs(Mathf.Sin(t*4))*6:0);
   }
   public void OnPointerClick(PointerEventData e){
    if(data==null||data.action==null)return;
    if(data.state=="ready"&&!string.IsNullOrEmpty(data.action.action))hud.PressMark(this,data.action);
    else if(!string.IsNullOrEmpty(data.label))hud.Toast(K.Clean(data.label),data.state!="locked");
   }
  }
  void PressMark(BoardMarkUi mark,DesktopButton action){
   boardPressed=(RectTransform)mark.transform;boardPressedVariant="success";Sound("tap");
   pending[host.Action(action.action,action.args,action.after)]=action;
  }

  // A title over a group of tiles plus the grid they sit in.
  class BoardSection:MonoBehaviour {
   public RectTransform grid;TextMeshProUGUI title;GameObject header;GridLayoutGroup layout;
   public static BoardSection Create(Transform parent){
    var root=N.Node("Section",parent);var s=root.gameObject.AddComponent<BoardSection>();N.Column(root.gameObject,6);
    s.header=N.Node("Header",root).gameObject;var hl=s.header.AddComponent<LayoutElement>();hl.preferredHeight=30;
    var line=N.Image(s.header.transform,"Line",new Color(.55f,.4f,.25f,.25f),2);var lr=line.rectTransform;lr.anchorMin=new Vector2(0,.5f);lr.anchorMax=new Vector2(1,.5f);lr.offsetMin=new Vector2(0,-1);lr.offsetMax=new Vector2(0,1);
    var pill=N.Image(s.header.transform,"Pill",K.C("8A5A2B"),12);var pr=pill.rectTransform;pr.anchorMin=new Vector2(0,0);pr.anchorMax=new Vector2(0,1);pr.pivot=new Vector2(0,.5f);pr.offsetMin=new Vector2(0,1);pr.offsetMax=new Vector2(0,-1);
    var fit=pill.gameObject.AddComponent<HorizontalLayoutGroup>();fit.padding=new RectOffset(14,14,2,2);fit.childControlWidth=fit.childControlHeight=true;fit.childForceExpandWidth=false;
    var csf=pill.gameObject.AddComponent<ContentSizeFitter>();csf.horizontalFit=ContentSizeFitter.FitMode.PreferredSize;
    s.title=N.Text(pill.transform,"Title",K.Label,14,Color.white);s.title.characterSpacing=4;s.title.textWrappingMode=TextWrappingModes.NoWrap;s.title.alignment=TextAlignmentOptions.MidlineLeft;
    s.grid=N.Node("Grid",root);s.layout=s.grid.gameObject.AddComponent<GridLayoutGroup>();s.layout.spacing=new Vector2(14,14);s.layout.padding=new RectOffset(2,2,4,10);
    s.layout.startCorner=GridLayoutGroup.Corner.UpperLeft;s.layout.childAlignment=TextAnchor.UpperLeft;s.layout.constraint=GridLayoutGroup.Constraint.FixedColumnCount;
    return s;
   }
   public void Apply(string group,Vector2 cell,bool rows,int columns){
    header.SetActive(!string.IsNullOrEmpty(group));title.text=K.Clean(group);
    layout.cellSize=cell;layout.spacing=new Vector2(14,rows?10:14);layout.constraintCount=rows?1:columns;
   }
  }
 }
}
