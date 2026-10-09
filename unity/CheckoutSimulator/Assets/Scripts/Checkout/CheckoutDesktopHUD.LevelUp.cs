using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // Level-up celebration (view.levelUp from desktop/level-up.ts), in the spirit of Hay Day's and Township's
 // "Level up!": the screen dims, golden rays turn behind a medal with the new level (counting up when several
 // levels came at once), a red ribbon, confetti and a fanfare; then a panel slides up with the complete list of
 // what the level opened, group by group (each with what to do and a button that takes the player there), what
 // waits for a bigger market, and the way to the next level. "Continuar" (or Esc) closes it (dismissLevelUp).
 // It has its own canvas above every window and mini-game.
 public partial class CheckoutDesktopHUD {
  RectTransform levelRoot,levelStage,levelMedal,levelRibbon,levelPanel,levelContent,levelConfetti,levelXpFill;
  Image levelDim,levelRays,levelRaysBack,levelGlow;
  TextMeshProUGUI levelNumber,levelSubtitle,levelCount,levelNext,levelXpText,levelEmpty,levelRibbonText;
  ScrollRect levelScroll;CheckoutDesktopButton levelContinue;CanvasGroup levelPanelGroup;
  // Its own speaker: the board one changes pitch for the pops, which would bend the fanfare.
  AudioSource levelAudio;
  string levelShownKey,levelClosedKey;Coroutine levelRun;
  sealed class LevelConfetto{public RectTransform rect;public Vector2 velocity;public float spin,life;}
  readonly List<LevelConfetto> levelPieces=new List<LevelConfetto>();
  static readonly string[] ConfettiColors={"F2B03D","E15533","2E8CAE","5DA637","E86FA6","8B5C9E","FFFFFF"};
  public bool LevelUpOpen=>levelRoot&&levelRoot.gameObject.activeSelf;

  void BuildLevelUp(){
   var canvasGo=new GameObject("CheckoutLevelUp",typeof(RectTransform));canvasGo.transform.SetParent(transform,false);
   var canvas=canvasGo.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=95;
   var scaler=canvasGo.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;// Matched on the height: the medal, the ribbon and the list always share the same 1000 units of height,
   // however wide the window is (on a short, wide window the list used to cover the ribbon).
   scaler.referenceResolution=new Vector2(1600,1000);scaler.matchWidthOrHeight=1;
   canvasGo.AddComponent<GraphicRaycaster>();
   levelRoot=(RectTransform)canvasGo.transform;
   levelAudio=gameObject.AddComponent<AudioSource>();levelAudio.playOnAwake=false;levelAudio.volume=.5f;levelAudio.pitch=1;

   levelDim=N.Image(levelRoot,"Dim",new Color(.07f,.09f,.17f,.8f),0);levelDim.raycastTarget=true;U.Stretch(levelDim.rectTransform,Vector2.zero,Vector2.one);
   levelStage=N.Node("Stage",levelRoot);U.Stretch(levelStage,Vector2.zero,Vector2.one);

   // Rays and glow behind the medal.
   levelRaysBack=N.Image(levelStage,"RaysBack",new Color(1f,.86f,.45f,.35f),0);levelRaysBack.sprite=LevelRaysSprite();U.At(levelRaysBack.rectTransform,new Vector2(.5f,1),new Vector2(980,980),new Vector2(0,-205));
   levelRays=N.Image(levelStage,"Rays",new Color(1f,.93f,.6f,.55f),0);levelRays.sprite=LevelRaysSprite();U.At(levelRays.rectTransform,new Vector2(.5f,1),new Vector2(760,760),new Vector2(0,-205));
   levelGlow=U.GlowAt(levelStage,"Glow",new Color(1f,.85f,.4f,.85f),new Vector2(.5f,1),430,new Vector2(0,-205));

   // Medal: dark gold rim, gold face, a shine, the crown on top and the level number.
   levelMedal=N.Node("Medal",levelStage);U.At(levelMedal,new Vector2(.5f,1),new Vector2(250,250),new Vector2(0,-205));
   var rim=N.Image(levelMedal,"Rim",K.C("B37A16"),0);rim.sprite=LevelDisc();U.Stretch(rim.rectTransform,Vector2.zero,Vector2.one);
   var ring=N.Image(levelMedal,"Ring",K.C("FFE9A8"),0);ring.sprite=LevelDisc();U.Stretch(ring.rectTransform,Vector2.zero,Vector2.one,new Vector2(12,12),new Vector2(-12,-12));
   var face=N.Image(levelMedal,"Face",K.C("F2B03D"),0);face.sprite=LevelDisc();U.Stretch(face.rectTransform,Vector2.zero,Vector2.one,new Vector2(20,20),new Vector2(-20,-20));
   var shine=N.Image(levelMedal,"Shine",new Color(1f,.97f,.8f,.32f),0);shine.sprite=LevelDisc();U.At(shine.rectTransform,new Vector2(.5f,.5f),new Vector2(120,46),new Vector2(-4,70));
   var crown=U.Icon(levelMedal,"Crown",gameIconPath("crown"),new Vector2(.5f,1),new Vector2(120,120),new Vector2(0,18));crown.raycastTarget=false;
   var label=U.Label(levelMedal,"Label",K.Label,18,"8A5A12");U.At(label.rectTransform,new Vector2(.5f,.5f),new Vector2(200,26),new Vector2(0,-62));label.text="NÍVEL";label.characterSpacing=6;
   // Overflow, not ellipsis: at this size the line is taller than the box and an ellipsis would hide the number.
   levelNumber=U.Label(levelMedal,"Number",K.Headline,100,"FFFFFF");U.At(levelNumber.rectTransform,new Vector2(.5f,.5f),new Vector2(220,150),new Vector2(0,8));
   levelNumber.overflowMode=TextOverflowModes.Overflow;levelNumber.enableAutoSizing=false;
   levelNumber.outlineWidth=.22f;levelNumber.outlineColor=new Color32(150,96,10,255);

   // Ribbon with two folded tails.
   levelRibbon=N.Node("Ribbon",levelStage);U.At(levelRibbon,new Vector2(.5f,1),new Vector2(560,84),new Vector2(0,-352));
   // Each tail starts under the band, comes out lower and ends in a notch; the fold is a darker triangle.
   foreach(var side in new[]{-1,1}){
    var tail=N.Image(levelRibbon,"Tail",K.C("B23A1C"),0);tail.sprite=LevelTailSprite();var tr=tail.rectTransform;
    tr.anchorMin=tr.anchorMax=new Vector2(side<0?0:1,.5f);tr.pivot=new Vector2(.5f,.5f);tr.sizeDelta=new Vector2(132,64);tr.anchoredPosition=new Vector2(side*26,-30);tr.localScale=new Vector3(side<0?1:-1,1,1);
    var fold=N.Image(levelRibbon,"Fold",K.C("7E2410"),0);fold.sprite=LevelFoldSprite();var fr=fold.rectTransform;
    fr.anchorMin=fr.anchorMax=new Vector2(side<0?0:1,.5f);fr.pivot=new Vector2(.5f,1);fr.sizeDelta=new Vector2(40,20);fr.anchoredPosition=new Vector2(-side*20,-42);fr.localScale=new Vector3(side<0?1:-1,1,1);
   }
   var band=N.Image(levelRibbon,"Band",K.C("E15533"),14);U.Stretch(band.rectTransform,Vector2.zero,Vector2.one);
   var bandShade=N.Image(band.transform,"Shade",K.C("C0401F"),14);U.Stretch(bandShade.rectTransform,Vector2.zero,new Vector2(1,.32f));
   levelRibbonText=U.Label(band.transform,"Text",K.Headline,40,"FFFFFF");U.Stretch(levelRibbonText.rectTransform,Vector2.zero,Vector2.one,new Vector2(10,4),new Vector2(-10,-2));
   levelRibbonText.overflowMode=TextOverflowModes.Overflow;levelRibbonText.text="SUBIU DE NÍVEL!";levelRibbonText.characterSpacing=2;levelRibbonText.outlineWidth=.15f;levelRibbonText.outlineColor=new Color32(140,36,14,255);

   levelSubtitle=U.Label(levelStage,"Subtitle",K.Label,22,"FFF4DA");U.At(levelSubtitle.rectTransform,new Vector2(.5f,1),new Vector2(1000,34),new Vector2(0,-418));

   // Panel with the list.
   levelPanel=N.Node("Panel",levelStage);U.Stretch(levelPanel,new Vector2(.5f,0),new Vector2(.5f,0));levelPanel.pivot=new Vector2(.5f,0);levelPanel.sizeDelta=new Vector2(1120,520);levelPanel.anchoredPosition=new Vector2(0,24);
   levelPanelGroup=levelPanel.gameObject.AddComponent<CanvasGroup>();
   var edge=N.Image(levelPanel,"Edge",K.Border,22);U.Stretch(edge.rectTransform,Vector2.zero,Vector2.one);edge.raycastTarget=true;
   var cream=N.Image(levelPanel,"Face",K.Cream,20);U.Stretch(cream.rectTransform,Vector2.zero,Vector2.one,new Vector2(3,7),new Vector2(-3,-3));
   var head=N.Node("Head",cream.transform);U.Stretch(head,new Vector2(0,1),Vector2.one,new Vector2(24,-58),new Vector2(-24,-12));
   levelCount=U.Label(head,"Count",K.Headline,26,"4A3624",TextAlignmentOptions.MidlineLeft);U.Stretch(levelCount.rectTransform,Vector2.zero,Vector2.one);
   var list=N.Node("List",cream.transform);U.Stretch(list,Vector2.zero,Vector2.one,new Vector2(18,96),new Vector2(-12,-62));
   levelScroll=LevelScroll(list,out levelContent);
   levelEmpty=U.Label(list,"Empty",K.Body,20,"8A7560");levelEmpty.textWrappingMode=TextWrappingModes.Normal;U.Stretch(levelEmpty.rectTransform,Vector2.zero,Vector2.one,new Vector2(40,0),new Vector2(-40,0));
   // Footer: way to the next level and the button.
   var foot=N.Node("Foot",cream.transform);U.Stretch(foot,Vector2.zero,new Vector2(1,0),new Vector2(24,14),new Vector2(-24,84));
   var track=N.Image(foot,"Track",K.C("EADBC4"),9);U.Stretch(track.rectTransform,new Vector2(0,.62f),new Vector2(.66f,.62f),new Vector2(0,-9),new Vector2(0,9));
   var fill=N.Image(track.transform,"Fill",K.C("5DA637"),9);levelXpFill=fill.rectTransform;U.Stretch(levelXpFill,Vector2.zero,new Vector2(0,1));
   levelXpText=U.Label(track.transform,"Xp",K.Number,13,"4A3624");U.Stretch(levelXpText.rectTransform,Vector2.zero,Vector2.one);
   levelNext=U.Label(foot,"Next",K.Body,16,"8A7560",TextAlignmentOptions.MidlineLeft);U.Stretch(levelNext.rectTransform,new Vector2(0,0),new Vector2(.66f,.38f));
   var buttonHolder=N.Node("Continue",foot);U.Stretch(buttonHolder,new Vector2(.7f,0),Vector2.one);
   levelContinue=U.Button(buttonHolder,"Continuar","success",()=>CloseLevelUp(""),64,26);
   U.Stretch((RectTransform)levelContinue.transform,Vector2.zero,Vector2.one);

   levelConfetti=N.Node("Confetti",levelRoot);U.Stretch(levelConfetti,Vector2.zero,Vector2.one);
   levelRoot.gameObject.SetActive(false);
  }

  static string gameIconPath(string id)=>"Icons/"+id;

  // Vertical list (viewport with a mask and a content that grows with its layout).
  static ScrollRect LevelScroll(Transform parent,out RectTransform content){
   var node=N.Node("Scroll",parent);U.Stretch(node,Vector2.zero,Vector2.one);var scroll=node.gameObject.AddComponent<ScrollRect>();
   var viewport=N.Node("Viewport",node);U.Stretch(viewport,Vector2.zero,Vector2.one);
   var hit=viewport.gameObject.AddComponent<Image>();hit.color=new Color(0,0,0,0);viewport.gameObject.AddComponent<RectMask2D>();
   content=N.Node("Content",viewport);content.anchorMin=new Vector2(0,1);content.anchorMax=Vector2.one;content.pivot=new Vector2(.5f,1);content.offsetMin=content.offsetMax=Vector2.zero;
   N.Column(content.gameObject,14,new RectOffset(4,10,4,14));
   content.gameObject.AddComponent<ContentSizeFitter>().verticalFit=ContentSizeFitter.FitMode.PreferredSize;
   scroll.viewport=viewport;scroll.content=content;scroll.horizontal=false;scroll.vertical=true;scroll.scrollSensitivity=40;scroll.movementType=ScrollRect.MovementType.Clamped;
   return scroll;
  }

  void ApplyLevelUp(DesktopView v){
   var data=v.levelUp;
   bool has=data!=null&&!string.IsNullOrEmpty(data.key)&&data.key!=levelClosedKey;
   if(!has){if(LevelUpOpen&&(data==null||string.IsNullOrEmpty(data.key)))HideLevelUp();return;}
   if(data.key==levelShownKey&&LevelUpOpen)return;
   // A conquest celebration goes first (a cleared lot often levels up too): the next view brings this back.
   if(ConquestOpen||ConquestWaiting(v))return;
   levelShownKey=data.key;
   if(levelRun!=null)StopCoroutine(levelRun);
   levelRun=StartCoroutine(PlayLevelUp(data));
  }

  void CloseLevelUp(string route){
   if(string.IsNullOrEmpty(levelShownKey))return;
   levelClosedKey=levelShownKey;
   Silent.Add(host.Action("dismissLevelUp","[]",route??""));
   Sound("tap");HideLevelUp();
  }
  void HideLevelUp(){
   if(levelRun!=null){StopCoroutine(levelRun);levelRun=null;}
   foreach(var piece in levelPieces)if(piece.rect)Destroy(piece.rect.gameObject);levelPieces.Clear();
   if(levelRoot)levelRoot.gameObject.SetActive(false);
  }

  IEnumerator PlayLevelUp(DesktopLevelUp data){
   levelRoot.gameObject.SetActive(true);levelRoot.SetAsLastSibling();
   // Reset the stage.
   levelDim.color=new Color(.07f,.09f,.17f,0);
   levelMedal.localScale=Vector3.zero;levelRibbon.localScale=new Vector3(0,1,1);levelRays.transform.localScale=Vector3.zero;levelRaysBack.transform.localScale=Vector3.zero;levelGlow.transform.localScale=Vector3.zero;
   levelSubtitle.text=K.Clean(data.subtitle);levelSubtitle.alpha=0;
   LevelFitPanel();
   levelPanel.anchoredPosition=new Vector2(0,-levelPanel.sizeDelta.y-40);levelPanelGroup.alpha=0;levelPanelGroup.interactable=false;
   levelNumber.text=Mathf.Max(1,data.from).ToString();
   FillLevelList(data);

   StartCoroutine(U.Fade(levelDim,.8f,.3f));
   Sound("whoosh");
   StartCoroutine(U.Scale(levelRays.transform,Vector3.one,.5f,true));StartCoroutine(U.Scale(levelRaysBack.transform,Vector3.one,.6f,true));StartCoroutine(U.Scale(levelGlow.transform,Vector3.one,.5f));
   yield return U.Scale(levelMedal,Vector3.one,.45f,true);
   // Count up through the levels gained (one beat each, the last one with the fanfare).
   int from=Mathf.Max(1,data.from),to=Mathf.Max(from,data.to);
   // Many levels at once count up faster (about a second and a half in all).
   float beat=Mathf.Min(.22f,1.4f/Mathf.Max(1,to-from));
   for(int level=from+1;level<=to;level++){
    levelNumber.text=level.ToString();
    // A soft rising pop for each level on the way; the last one gets the fanfare alone (major, steady:
    // scripts/make_sounds.py levelup), never on top of another sound.
    if(level<to)Sound("pop",Mathf.Min(1.5f,1+.05f*(level-from)));
    else{var fanfare=U.Sfx("levelup");if(fanfare&&levelAudio)levelAudio.PlayOneShot(fanfare,.9f);else Sound("success");}
    StartCoroutine(U.Pop(levelMedal,level==to?1.25f:1.12f,.3f));
    U.Sparkles(this,levelStage,LevelMedalPoint(),level==to?14:5,level==to?230:140);
    if(level<to)yield return new WaitForSecondsRealtime(beat);
   }
   LevelConfettiBurst(90);
   StartCoroutine(U.Scale(levelRibbon,Vector3.one,.35f,true));
   yield return new WaitForSecondsRealtime(.18f);
   StartCoroutine(LevelFadeText(levelSubtitle,1,.3f));
   // The panel slides up, then its groups and cards pop one after the other.
   levelPanelGroup.interactable=true;
   StartCoroutine(LevelFadeGroup(levelPanelGroup,1,.3f));
   yield return U.Move(levelPanel,new Vector2(0,24),.42f,true);
   LevelListToTop();
   int animated=0;
   foreach(Transform group in levelContent){
    group.localScale=Vector3.one;
    var grid=group.Find("Grid");
    if(grid)foreach(Transform card in grid){
     if(animated++>=28)break;
     card.localScale=Vector3.zero;StartCoroutine(LevelPopIn(card,animated*.035f));
    }
   }
   levelRun=null;
  }

  static IEnumerator LevelFadeText(TextMeshProUGUI text,float to,float seconds){
   float from=text.alpha;for(float t=0;t<1;t+=Time.unscaledDeltaTime/seconds){if(!text)yield break;text.alpha=Mathf.Lerp(from,to,t);yield return null;}if(text)text.alpha=to;
  }
  static IEnumerator LevelFadeGroup(CanvasGroup group,float to,float seconds){
   float from=group.alpha;for(float t=0;t<1;t+=Time.unscaledDeltaTime/seconds){if(!group)yield break;group.alpha=Mathf.Lerp(from,to,t);yield return null;}if(group)group.alpha=to;
  }
  IEnumerator LevelPopIn(Transform card,float delay){
   yield return new WaitForSecondsRealtime(delay);if(!card)yield break;
   yield return U.Scale(card,Vector3.one,.28f,true);
  }

  // The list takes the room left under the subtitle (top stack: crown, medal, ribbon and subtitle end ~440
  // units from the top), never covering them; it keeps 520 units when there is room.
  void LevelFitPanel(){
   float height=levelStage.rect.height;if(height<=0)height=1000;
   levelPanel.sizeDelta=new Vector2(1120,Mathf.Clamp(height-450-24,300,520));
  }

  Vector2 LevelMedalPoint(){var p=levelMedal.anchoredPosition;var stage=levelStage.rect;return new Vector2(p.x,stage.height*.5f+p.y);}

  // ------------------------------------------------------------------ the list
  // The list always opens at its first group (the layout is built right away so the position holds).
  void LevelListToTop(){
   LayoutRebuilder.ForceRebuildLayoutImmediate(levelContent);
   levelScroll.StopMovement();levelContent.anchoredPosition=Vector2.zero;levelScroll.verticalNormalizedPosition=1;
  }

  void FillLevelList(DesktopLevelUp data){
   // Out of the layout at once (Destroy only happens at the end of the frame).
   foreach(Transform child in levelContent){child.gameObject.SetActive(false);Destroy(child.gameObject);}
   var groups=data.groups??new DesktopLevelUpGroup[0];
   int total=data.total;
   levelCount.text=total>0?$"Você liberou {total} {(total==1?"novidade":"novidades")} no nível {data.to}":$"Nível {data.to}";
   levelEmpty.gameObject.SetActive(groups.Length==0);levelEmpty.text=K.Clean(data.empty);
   foreach(var group in groups)LevelGroup(group);
   levelNext.text=K.Clean(data.next);
   float goal=Mathf.Max(1,data.xpGoal);levelXpFill.anchorMax=new Vector2(Mathf.Clamp01(data.xp/goal),1);levelXpFill.offsetMin=levelXpFill.offsetMax=Vector2.zero;
   levelXpText.text=$"{data.xp:N0} / {data.xpGoal:N0} XP para o nível {data.to+1}".Replace(",",".");
   LevelListToTop();
  }

  void LevelGroup(DesktopLevelUpGroup group){
   var tint=K.C(string.IsNullOrEmpty(group.tint)?"8A5A2B":group.tint);
   var root=N.Node("Group",levelContent);N.Column(root.gameObject,8);
   // Header: coloured pill (icon, title, count), the hint and the button to where these live.
   var head=N.Node("Head",root);head.gameObject.AddComponent<LayoutElement>().preferredHeight=46;
   var pill=N.Image(head,"Pill",tint,14);var pr=pill.rectTransform;pr.anchorMin=new Vector2(0,.5f);pr.anchorMax=new Vector2(0,.5f);pr.pivot=new Vector2(0,.5f);pr.anchoredPosition=Vector2.zero;
   var pillRow=N.Row(pill.gameObject,8,new RectOffset(10,16,4,4));pillRow.childControlWidth=pillRow.childControlHeight=true;
   pill.gameObject.AddComponent<ContentSizeFitter>().horizontalFit=ContentSizeFitter.FitMode.PreferredSize;
   pr.sizeDelta=new Vector2(0,40);
   var ico=N.Image(pill.transform,"Icon",Color.white,0);ico.sprite=K.Icon(group.icon);ico.preserveAspect=true;var il=ico.gameObject.AddComponent<LayoutElement>();il.preferredWidth=il.preferredHeight=30;
   var title=N.Text(pill.transform,"Title",K.Headline,21,Color.white);title.textWrappingMode=TextWrappingModes.NoWrap;title.alignment=TextAlignmentOptions.MidlineLeft;
   int count=group.items?.Length??0;title.text=$"{K.Clean(group.title)}  <size=17><color=#FFFFFFCC>{count}</color></size>";
   if(!string.IsNullOrEmpty(group.button)){
    var holder=N.Node("Go",head);holder.anchorMin=new Vector2(1,.5f);holder.anchorMax=new Vector2(1,.5f);holder.pivot=new Vector2(1,.5f);holder.sizeDelta=new Vector2(210,42);holder.anchoredPosition=Vector2.zero;
    var route=group.route;
    var go=U.Button(holder,group.button,"secondary",()=>CloseLevelUp(route),42,17);
    U.Stretch((RectTransform)go.transform,Vector2.zero,Vector2.one);
   }
   var hint=N.Text(root,"Hint",K.Body,16,K.Muted);hint.text=K.Clean(group.hint);hint.gameObject.AddComponent<LayoutElement>().preferredHeight=22;
   // Cards.
   var grid=N.Node("Grid",root);var layout=grid.gameObject.AddComponent<GridLayoutGroup>();
   layout.cellSize=new Vector2(254,104);layout.spacing=new Vector2(10,10);layout.constraint=GridLayoutGroup.Constraint.FixedColumnCount;layout.constraintCount=4;
   foreach(var item in group.items??new DesktopLevelUpItem[0])LevelCard(grid,item,tint);
  }

  void LevelCard(Transform grid,DesktopLevelUpItem item,Color tint){
   var card=N.Node("Card",grid);
   var edge=N.Image(card,"Edge",Color.Lerp(K.Border,tint,.35f),14);U.Stretch(edge.rectTransform,Vector2.zero,Vector2.one);
   var face=N.Image(card,"Face",Color.white,12);U.Stretch(face.rectTransform,Vector2.zero,Vector2.one,new Vector2(2,4),new Vector2(-2,-2));
   var well=N.Image(face.transform,"Well",Color.Lerp(K.Paper,tint,.12f),12);U.At(well.rectTransform,new Vector2(0,.5f),new Vector2(80,80),new Vector2(48,0));
   var icon=N.Image(well.transform,"Icon",Color.white,0);icon.sprite=K.Icon(item.icon);icon.preserveAspect=true;U.Stretch(icon.rectTransform,Vector2.zero,Vector2.one,new Vector2(8,8),new Vector2(-8,-8));
   if(!icon.sprite)icon.enabled=false;
   var title=N.Text(face.transform,"Title",K.Headline,18,K.Ink);title.textWrappingMode=TextWrappingModes.NoWrap;title.overflowMode=TextOverflowModes.Ellipsis;title.alignment=TextAlignmentOptions.TopLeft;
   U.Stretch(title.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(96,-36),new Vector2(-8,-8));title.text=K.Clean(item.title);
   var detail=N.Text(face.transform,"Detail",K.Body,13,K.Muted);detail.alignment=TextAlignmentOptions.TopLeft;detail.overflowMode=TextOverflowModes.Ellipsis;detail.enableAutoSizing=false;
   U.Stretch(detail.rectTransform,Vector2.zero,Vector2.one,new Vector2(96,8),new Vector2(-8,-36));detail.text=K.Clean(item.detail);
   if(!string.IsNullOrEmpty(item.tag)){
    var tag=N.Image(face.transform,"Tag",tint,8);var tr=tag.rectTransform;tr.anchorMin=tr.anchorMax=new Vector2(1,1);tr.pivot=new Vector2(1,.5f);tr.anchoredPosition=new Vector2(-6,-2);
    var tagText=N.Text(tag.transform,"Text",K.Label,10,Color.white);tagText.textWrappingMode=TextWrappingModes.NoWrap;tagText.alignment=TextAlignmentOptions.Center;tagText.characterSpacing=2;tagText.text=K.Clean(item.tag);
    tr.sizeDelta=new Vector2(Mathf.Clamp(tagText.preferredWidth+16,44,150),18);U.Stretch(tagText.rectTransform,Vector2.zero,Vector2.one);
   }
  }

  // ------------------------------------------------------------------ confetti, rays (Update)
  void LevelConfettiBurst(int count){
   for(int i=0;i<count;i++){
    var piece=N.Image(levelConfetti,"Piece",K.C(ConfettiColors[i%ConfettiColors.Length]),i%3==0?4:0);
    var r=piece.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);
    r.sizeDelta=i%4==0?new Vector2(12,12):new Vector2(Random.Range(8,13),Random.Range(16,24));
    r.anchoredPosition=LevelMedalPoint();
    var angle=Random.Range(20f,160f)*Mathf.Deg2Rad;var speed=Random.Range(420f,980f);
    levelPieces.Add(new LevelConfetto{rect=r,velocity=new Vector2(Mathf.Cos(angle)*speed*1.2f,Mathf.Sin(angle)*speed),spin=Random.Range(-540f,540f),life=Random.Range(2.2f,3.4f)});
   }
  }

  void UpdateLevelUp(){
   if(!LevelUpOpen)return;
   if(Input.GetKeyDown(KeyCode.Escape)){CloseLevelUp("");return;}
   float dt=Time.unscaledDeltaTime;
   if(levelRays)levelRays.transform.Rotate(0,0,-14*dt);
   if(levelRaysBack)levelRaysBack.transform.Rotate(0,0,9*dt);
   if(levelGlow){var a=.7f+.15f*Mathf.Sin(Time.unscaledTime*2.4f);var c=levelGlow.color;c.a=a;levelGlow.color=c;}
   if(levelContinue&&levelRun==null){var s=1+.03f*Mathf.Sin(Time.unscaledTime*4);levelContinue.transform.localScale=new Vector3(s,s,1);}
   for(int i=levelPieces.Count-1;i>=0;i--){
    var p=levelPieces[i];
    if(!p.rect){levelPieces.RemoveAt(i);continue;}
    p.velocity+=new Vector2(-p.velocity.x*.9f*dt,-900*dt);p.velocity.y=Mathf.Max(p.velocity.y,-520);
    p.rect.anchoredPosition+=p.velocity*dt+new Vector2(Mathf.Sin(Time.unscaledTime*6+i)*30*dt,0);
    p.rect.Rotate(0,0,p.spin*dt);
    p.life-=dt;
    if(p.life<.5f){var img=p.rect.GetComponent<Image>();if(img){var c=img.color;c.a=Mathf.Clamp01(p.life/.5f);img.color=c;}}
    if(p.life<=0){Destroy(p.rect.gameObject);levelPieces.RemoveAt(i);}
   }
  }

  // Soft rays turning behind the medal (one texture, two copies turning against each other).
  static Sprite levelRaysSprite;
  static Sprite LevelRaysSprite(){
   if(levelRaysSprite)return levelRaysSprite;
   const int n=512;var t=new Texture2D(n,n,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};var px=new Color32[n*n];
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){
    float dx=(x+.5f)/n-.5f,dy=(y+.5f)/n-.5f,d=Mathf.Sqrt(dx*dx+dy*dy)*2,a=Mathf.Atan2(dy,dx);
    float ray=Mathf.SmoothStep(0,1,Mathf.Clamp01((Mathf.Cos(a*14)-.15f)*2.2f));
    float fade=Mathf.Clamp01(1-d)*Mathf.Clamp01(d*3);
    px[y*n+x]=new Color32(255,255,255,(byte)(ray*fade*fade*255));
   }
   t.SetPixels32(px);t.Apply();return levelRaysSprite=Sprite.Create(t,new Rect(0,0,n,n),new Vector2(.5f,.5f));
  }
  // Ribbon tail: a band with a V notch cut into its outer end (left; the right tail is mirrored).
  static Sprite levelTailSprite,levelFoldSprite;
  static Sprite LevelTailSprite(){
   if(levelTailSprite)return levelTailSprite;
   const int w=132,h=64;var t=new Texture2D(w,h,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};var px=new Color32[w*h];
   for(int y=0;y<h;y++)for(int x=0;x<w;x++){float notch=30*(1-Mathf.Abs((y+.5f)-h/2f)/(h/2f));float a=Mathf.Clamp01(x+.5f-notch);px[y*w+x]=new Color32(255,255,255,(byte)(a*255));}
   t.SetPixels32(px);t.Apply();return levelTailSprite=Sprite.Create(t,new Rect(0,0,w,h),new Vector2(.5f,.5f));
  }
  // The fold where the band turns into the tail: a right triangle, its square corner at the top right (inner side).
  static Sprite LevelFoldSprite(){
   if(levelFoldSprite)return levelFoldSprite;
   const int w=40,h=20;var t=new Texture2D(w,h,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};var px=new Color32[w*h];
   for(int y=0;y<h;y++)for(int x=0;x<w;x++){float edge=(y+.5f)/h*w;float a=Mathf.Clamp01(edge-(w-(x+.5f))+.5f);px[y*w+x]=new Color32(255,255,255,(byte)(a*255));}
   t.SetPixels32(px);t.Apply();return levelFoldSprite=Sprite.Create(t,new Rect(0,0,w,h),new Vector2(.5f,.5f));
  }
  static Sprite levelDiscSprite;
  static Sprite LevelDisc(){
   if(levelDiscSprite)return levelDiscSprite;
   const int n=256;var t=new Texture2D(n,n,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};var px=new Color32[n*n];
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(n/2f,n/2f));px[y*n+x]=new Color32(255,255,255,(byte)(Mathf.Clamp01(n/2f-d)*255));}
   t.SetPixels32(px);t.Apply();return levelDiscSprite=Sprite.Create(t,new Rect(0,0,n,n),new Vector2(.5f,.5f));
  }
 }
}
