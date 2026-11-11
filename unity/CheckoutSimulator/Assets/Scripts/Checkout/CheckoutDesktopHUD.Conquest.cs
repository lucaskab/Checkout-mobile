using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // Conquest celebration (view.celebration from desktop/celebration.ts): a lot cleared, a new expansion, a sector,
 // a fixture or an installation finished. Like Township's "new area" and Hay Day's "building ready": for a lot the
 // camera first flies over it for the dust, the light column and the confetti (CheckoutConquestFx), then a medal
 // with the thing conquered pops up with rays, a ribbon, what it changes (chips) and a button to use it. One at a
 // time; it waits while the level-up celebration is open (and the level-up waits for it). Continuar/Esc closes it
 // (dismissCelebration) and the camera glides back.
 public partial class CheckoutDesktopHUD {
  RectTransform conquestRoot,conquestStage,conquestMedal,conquestRibbon,conquestChips,conquestButtons,conquestConfetti;
  Image conquestDim,conquestRays,conquestGlow,conquestRim,conquestIcon,conquestBand,conquestBandShade;readonly List<Image> conquestTails=new List<Image>();
  TextMeshProUGUI conquestHeadline,conquestTitle,conquestSubtitle;CanvasGroup conquestText,conquestCardGroup;RectTransform conquestCard;
  // Evolutions: the new look (a picture of the piece), the numbers counting up and the products opened (NOVO).
  RectTransform conquestStats,conquestProducts,conquestPips;Image conquestPipsBack;RawImage conquestPortrait;Texture2D conquestPortraitTex;
  readonly List<(TextMeshProUGUI text,DesktopCelebrationStat stat)> conquestCounters=new List<(TextMeshProUGUI,DesktopCelebrationStat)>();
  CheckoutDesktopButton conquestContinue,conquestGo;
  string conquestShownKey,conquestClosedKey,conquestId,conquestRoute;Coroutine conquestRun;bool conquestPlaying,conquestEvolution;
  AudioSource conquestAudio;
  // The card's confetti: the same pieces as the 3D burst at the reveal (CheckoutConfettiArt), turning as they fall.
  sealed class CardConfetto{public RectTransform rect;public Image image;public Vector2 velocity;public float spin,life,flip,flipSpeed,frame,frameSpeed,sway;public int row,col;public Color accent;}
  readonly List<CardConfetto> conquestPieces=new List<CardConfetto>();
  public bool ConquestOpen=>conquestPlaying||(conquestRoot&&conquestRoot.gameObject.activeSelf);
  /// <summary>QA: the view the HUD shows now.</summary>
  public DesktopView QaView=>view;
  /// <summary>QA: the card itself is up (after the reveal).</summary>
  public bool QaCardShown=>conquestRoot&&conquestRoot.gameObject.activeSelf;
  /// <summary>A celebration is due and has not been shown yet (the level-up waits for it).</summary>
  bool ConquestWaiting(DesktopView v)=>v!=null&&v.celebration!=null&&!string.IsNullOrEmpty(v.celebration.key)&&v.celebration.key!=conquestClosedKey;

  void BuildConquest(){
   var canvasGo=new GameObject("CheckoutConquest",typeof(RectTransform));canvasGo.transform.SetParent(transform,false);
   var canvas=canvasGo.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=96;
   var scaler=canvasGo.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;CheckoutScreen.Fit(scaler,1,fixedLayout:true);
   canvasGo.AddComponent<GraphicRaycaster>();
   conquestRoot=CheckoutScreen.SafeArea(canvasGo.transform);
   conquestAudio=gameObject.AddComponent<AudioSource>();conquestAudio.playOnAwake=false;conquestAudio.volume=.5f;

   // (the layer only catches taps: no dark backdrop, U.TapCatcher; Lucas 05/11)
   conquestDim=N.Image(conquestRoot,"Dim",U.TapCatcher,0);conquestDim.raycastTarget=true;U.Stretch(conquestDim.rectTransform,Vector2.zero,Vector2.one,new Vector2(-900,-900),new Vector2(900,900));
   conquestStage=N.Node("Stage",conquestRoot);U.Stretch(conquestStage,new Vector2(.5f,.5f),new Vector2(.5f,.5f));conquestStage.sizeDelta=new Vector2(1000,700);

   // Rays and glow behind the medal.
   conquestRays=N.Image(conquestStage,"Rays",new Color(1f,.9f,.55f,.5f),0);conquestRays.sprite=LevelRaysSprite();U.At(conquestRays.rectTransform,new Vector2(.5f,.5f),new Vector2(700,700),new Vector2(0,170));
   conquestGlow=U.GlowAt(conquestStage,"Glow",new Color(1f,.85f,.4f,.8f),new Vector2(.5f,.5f),380,new Vector2(0,170));
   // Medal: tinted rim, cream ring and face, the conquered thing in the middle.
   conquestMedal=N.Node("Medal",conquestStage);U.At(conquestMedal,new Vector2(.5f,.5f),new Vector2(230,230),new Vector2(0,170));
   conquestRim=N.Image(conquestMedal,"Rim",K.C("3F9E52"),0);conquestRim.sprite=LevelDisc();U.Stretch(conquestRim.rectTransform,Vector2.zero,Vector2.one);
   var ring=N.Image(conquestMedal,"Ring",K.C("FFE9A8"),0);ring.sprite=LevelDisc();U.Stretch(ring.rectTransform,Vector2.zero,Vector2.one,new Vector2(12,12),new Vector2(-12,-12));
   var face=N.Image(conquestMedal,"Face",K.C("FFF7EA"),0);face.sprite=LevelDisc();U.Stretch(face.rectTransform,Vector2.zero,Vector2.one,new Vector2(22,22),new Vector2(-22,-22));
   var shine=N.Image(conquestMedal,"Shine",new Color(1,1,1,.35f),0);shine.sprite=LevelDisc();U.At(shine.rectTransform,new Vector2(.5f,.5f),new Vector2(110,40),new Vector2(-4,62));
   conquestIcon=U.Icon(conquestMedal,"Icon","Icons/key",new Vector2(.5f,.5f),new Vector2(138,138));conquestIcon.raycastTarget=false;
   var portrait=new GameObject("Portrait",typeof(RectTransform),typeof(RawImage));portrait.transform.SetParent(conquestMedal,false);
   conquestPortrait=portrait.GetComponent<RawImage>();conquestPortrait.raycastTarget=false;U.At(conquestPortrait.rectTransform,new Vector2(.5f,.5f),new Vector2(184,184),Vector2.zero);conquestPortrait.enabled=false;

   // Ribbon with the headline.
   conquestRibbon=N.Node("Ribbon",conquestStage);U.At(conquestRibbon,new Vector2(.5f,.5f),new Vector2(560,80),new Vector2(0,26));
   foreach(var side in new[]{-1,1}){
    var tail=N.Image(conquestRibbon,"Tail",Color.white,0);tail.sprite=LevelTailSprite();var tr=tail.rectTransform;
    tr.anchorMin=tr.anchorMax=new Vector2(side<0?0:1,.5f);tr.pivot=new Vector2(.5f,.5f);tr.sizeDelta=new Vector2(126,60);tr.anchoredPosition=new Vector2(side*24,-28);tr.localScale=new Vector3(side<0?1:-1,1,1);conquestTails.Add(tail);
    var fold=N.Image(conquestRibbon,"Fold",Color.white,0);fold.sprite=LevelFoldSprite();var fr=fold.rectTransform;
    fr.anchorMin=fr.anchorMax=new Vector2(side<0?0:1,.5f);fr.pivot=new Vector2(.5f,1);fr.sizeDelta=new Vector2(38,18);fr.anchoredPosition=new Vector2(-side*19,-40);fr.localScale=new Vector3(side<0?1:-1,1,1);conquestTails.Add(fold);
   }
   conquestBand=N.Image(conquestRibbon,"Band",K.C("3F9E52"),14);U.Stretch(conquestBand.rectTransform,Vector2.zero,Vector2.one);
   conquestBandShade=N.Image(conquestBand.transform,"Shade",Color.black,14);conquestBandShade.color=new Color(0,0,0,.14f);U.Stretch(conquestBandShade.rectTransform,Vector2.zero,new Vector2(1,.32f));
   conquestHeadline=U.Label(conquestBand.transform,"Text",K.Headline,38,"FFFFFF");U.Stretch(conquestHeadline.rectTransform,Vector2.zero,Vector2.one,new Vector2(10,4),new Vector2(-10,-2));
   conquestHeadline.overflowMode=TextOverflowModes.Overflow;conquestHeadline.characterSpacing=2;conquestHeadline.outlineWidth=.15f;conquestHeadline.outlineColor=new Color32(20,40,30,200);

   // Title, explanation, chips and buttons.
   var textNode=N.Node("Text",conquestStage);U.Stretch(textNode,new Vector2(.5f,.5f),new Vector2(.5f,.5f));textNode.sizeDelta=new Vector2(900,300);textNode.anchoredPosition=new Vector2(0,-150);
   conquestText=textNode.gameObject.AddComponent<CanvasGroup>();
   // The words, numbers and buttons stand on their own navy card (gold trim) now that nothing dims the world behind:
   // under the ribbon (its tails stay in front), sized to the rows when the card shows (PlayConquest).
   var cardEdge=N.Image(conquestStage,"Card",RankGoldTrim,30);cardEdge.raycastTarget=false;conquestCard=cardEdge.rectTransform;
   conquestCard.anchorMin=conquestCard.anchorMax=new Vector2(.5f,.5f);conquestCard.pivot=new Vector2(.5f,1);conquestCard.sizeDelta=new Vector2(940,320);
   var cardFace=N.Image(cardEdge.transform,"Face",RankNavy,28);cardFace.raycastTarget=false;U.Stretch(cardFace.rectTransform,Vector2.zero,Vector2.one,new Vector2(3,3),new Vector2(-3,-3));
   conquestCardGroup=cardEdge.gameObject.AddComponent<CanvasGroup>();conquestCardGroup.blocksRaycasts=false;
   conquestCard.SetSiblingIndex(conquestRibbon.GetSiblingIndex());
   conquestTitle=U.Label(textNode,"Title",K.Headline,46,"FFFFFF");U.At(conquestTitle.rectTransform,new Vector2(.5f,1),new Vector2(900,58),new Vector2(0,-30));
   conquestTitle.outlineWidth=.18f;conquestTitle.outlineColor=new Color32(15,20,40,220);conquestTitle.overflowMode=TextOverflowModes.Overflow;
   conquestTitle.textWrappingMode=TextWrappingModes.NoWrap;conquestTitle.enableAutoSizing=true;conquestTitle.fontSizeMin=26;conquestTitle.fontSizeMax=46;
   conquestSubtitle=U.Label(textNode,"Subtitle",K.Label,22,"FFF1D6");U.At(conquestSubtitle.rectTransform,new Vector2(.5f,1),new Vector2(820,60),new Vector2(0,-92));
   conquestSubtitle.textWrappingMode=TextWrappingModes.Normal;conquestSubtitle.overflowMode=TextOverflowModes.Overflow;
   conquestChips=N.Node("Chips",textNode);U.At(conquestChips,new Vector2(.5f,1),new Vector2(900,48),new Vector2(0,-152));
   var row=N.Row(conquestChips.gameObject,12,new RectOffset(0,0,0,0));row.childAlignment=TextAnchor.MiddleCenter;row.childControlWidth=row.childControlHeight=true;row.childForceExpandWidth=false;
   // (evolutions) before → after numbers and the new products, between the chips and the buttons
   conquestStats=N.Node("Stats",textNode);U.At(conquestStats,new Vector2(.5f,1),new Vector2(900,116),new Vector2(0,-140));
   var statsRow=N.Row(conquestStats.gameObject,14,new RectOffset(0,0,0,0));statsRow.childAlignment=TextAnchor.MiddleCenter;statsRow.childControlWidth=statsRow.childControlHeight=true;statsRow.childForceExpandWidth=false;
   conquestProducts=N.Node("Products",textNode);U.At(conquestProducts,new Vector2(.5f,1),new Vector2(900,108),new Vector2(0,-222));
   var productsRow=N.Row(conquestProducts.gameObject,14,new RectOffset(0,0,0,0));productsRow.childAlignment=TextAnchor.MiddleCenter;productsRow.childControlWidth=productsRow.childControlHeight=true;productsRow.childForceExpandWidth=false;
   conquestPipsBack=N.Image(textNode,"Pips back",new Color(.07f,.11f,.22f,.8f),24);conquestPipsBack.raycastTarget=false;U.At(conquestPipsBack.rectTransform,new Vector2(.5f,1),new Vector2(220,46),new Vector2(0,-74));
   conquestPips=N.Node("Pips",textNode);U.At(conquestPips,new Vector2(.5f,1),new Vector2(400,34),new Vector2(0,-74));
   var pipsRow=N.Row(conquestPips.gameObject,6,new RectOffset(0,0,0,0));pipsRow.childAlignment=TextAnchor.MiddleCenter;pipsRow.childControlWidth=pipsRow.childControlHeight=true;pipsRow.childForceExpandWidth=false;
   conquestButtons=N.Node("Buttons",textNode);U.At(conquestButtons,new Vector2(.5f,1),new Vector2(600,64),new Vector2(0,-226));
   var buttons=N.Row(conquestButtons.gameObject,16,new RectOffset(0,0,0,0));buttons.childAlignment=TextAnchor.MiddleCenter;buttons.childControlWidth=buttons.childControlHeight=true;buttons.childForceExpandWidth=false;
   conquestGo=U.Button(conquestButtons,"Ver","secondary",()=>CloseConquest(conquestRoute),62,22);Size(conquestGo,240);
   conquestContinue=U.Button(conquestButtons,"Continuar","success",()=>CloseConquest(""),62,24);Size(conquestContinue,250);

   conquestConfetti=N.Node("Confetti",conquestRoot);U.Stretch(conquestConfetti,Vector2.zero,Vector2.one);
   conquestRoot.gameObject.SetActive(false);
  }
  static void Size(CheckoutDesktopButton button,float width){var le=button.gameObject.GetComponent<LayoutElement>();if(!le)le=button.gameObject.AddComponent<LayoutElement>();le.preferredWidth=width;le.preferredHeight=62;}

  void ApplyConquest(DesktopView v){
   if(qaCelebrationHold)return;
   var data=v.celebration;
   bool has=data!=null&&!string.IsNullOrEmpty(data.key)&&data.key!=conquestClosedKey;
   if(!has){
    if(ConquestOpen&&(data==null||string.IsNullOrEmpty(data.key))){
     // dismissed elsewhere: an evolution's close-up still flies back to the player's own view (and gives the input back)
     bool evolution=conquestEvolution;HideConquest();if(evolution)CheckoutConquestFx.Instance.RestoreCamera();
    }
    return;
   }
   if(data.key==conquestShownKey&&ConquestOpen)return;
   if(LevelUpOpen)return; // after the level-up is closed (the next view brings it back)
   // An evolution's reveal plays on the piece itself: it waits until the player is back on the map (no window open).
   if(data.reveal!=null&&!string.IsNullOrEmpty(data.reveal.kind)&&v.hasPage)return;
   conquestShownKey=data.key;
   if(conquestRun!=null)StopCoroutine(conquestRun);
   conquestRun=StartCoroutine(PlayConquest(data,v.hasPage));
  }

  void CloseConquest(string route){
   if(string.IsNullOrEmpty(conquestShownKey)||conquestPlaying&&!conquestRoot.gameObject.activeSelf)return;
   conquestClosedKey=conquestShownKey;
   Silent.Add(host.Action("dismissCelebration","[\""+conquestId+"\"]",route??""));
   Sound("tap");bool evolution=conquestEvolution;HideConquest();
   // (an evolution's close-up always goes back to the player's own view, even when the card opens a page)
   if(string.IsNullOrEmpty(route)||evolution)CheckoutConquestFx.Instance.RestoreCamera();
  }

  // ------------------------------------------------------------------ cinematic HUD (the evolution reveal)
  // The side HUD fades out while a reveal plays (REPOR, the objective, the day and goal cards, Bônus, the hammer, the
  // toolbar...); the coins and diamonds stay. Every overlay canvas but the celebrations' own is faded as a whole; in the
  // HUD's own canvas, everything but the wallet.
  readonly List<(CanvasGroup group,float alpha,bool raycasts)> cinematic=new List<(CanvasGroup,float,bool)>();Coroutine cinematicRun;bool cinematicOn;
  public void Cinematic(bool on){
   if(on==cinematicOn)return;cinematicOn=on;
   if(on){
    cinematic.Clear();
    // (inactive ones too: the goal card comes back on the same view the page closes on, after this ran)
    void Add(GameObject go){if(!go)return;var g=go.GetComponent<CanvasGroup>();if(!g)g=go.AddComponent<CanvasGroup>();cinematic.Add((g,g.alpha,g.blocksRaycasts));}
    var top=root?root.Find("TopBar"):null;
    if(root)foreach(Transform child in root){if(child==top)continue;Add(child.gameObject);}
    if(top)foreach(Transform child in top){if(child.name=="Wallet")continue;Add(child.gameObject);}
    var hudCanvas=root?root.GetComponentInParent<Canvas>():null;
    foreach(var c in FindObjectsByType<Canvas>(FindObjectsSortMode.None)){
     if(!c||!c.isRootCanvas||c.renderMode!=RenderMode.ScreenSpaceOverlay||c==hudCanvas)continue;
     var n=c.gameObject.name;if(n=="CheckoutConquest"||n=="CheckoutLevelUp"||n=="Evolution chips")continue;
     Add(c.gameObject);
    }
   }
   if(cinematicRun!=null)StopCoroutine(cinematicRun);
   cinematicRun=StartCoroutine(CinematicFade(on));
  }
  IEnumerator CinematicFade(bool on){
   var from=new List<float>();foreach(var c in cinematic)from.Add(c.group?c.group.alpha:0);
   for(float t=0;t<1;t+=CheckoutUiKit.Dt/.3f){
    for(int i=0;i<cinematic.Count;i++){var c=cinematic[i];if(!c.group)continue;c.group.alpha=Mathf.Lerp(from[i],on?0:c.alpha,t);c.group.blocksRaycasts=!on&&c.raycasts;}
    yield return null;
   }
   foreach(var c in cinematic)if(c.group){c.group.alpha=on?0:c.alpha;c.group.blocksRaycasts=on?false:c.raycasts;}
   if(!on)cinematic.Clear();
   cinematicRun=null;
  }
  void HideConquest(){
   if(conquestRun!=null){StopCoroutine(conquestRun);conquestRun=null;}
   if(conquestEvolution){conquestEvolution=false;Cinematic(false);}
   conquestPlaying=false;
   foreach(var piece in conquestPieces)if(piece.rect)Destroy(piece.rect.gameObject);conquestPieces.Clear();
   if(conquestRoot)conquestRoot.gameObject.SetActive(false);
  }

  IEnumerator PlayConquest(DesktopCelebration data,bool pageOpen){
   conquestPlaying=true;conquestId=data.id;conquestRoute=data.route;QaCountDone=false;
   // A lot: first the show on the map (the camera flies there unless a window is open).
   if(data.kind=="lot"&&!string.IsNullOrEmpty(data.lotId)){
    var sites=FindAnyObjectByType<CheckoutLotSites>();
    if(sites){Sound("whoosh");float wait=sites.CelebrateLot(data.lotId,!pageOpen);if(wait>0)yield return CheckoutUiKit.Wait(wait);}
   }
   // An evolution: first the reveal on the piece (camera, cloth, pop, confetti, chips), then the card.
   bool evolution=data.reveal!=null&&!string.IsNullOrEmpty(data.reveal.kind);
   conquestEvolution=evolution;
   if(!evolution&&cinematicOn)Cinematic(false);   // (an evolution cut short by another celebration: the HUD comes back)
   if(evolution){
    Cinematic(true);
    float wait=CheckoutEvolutionReveal.Instance.Play(data.reveal,data.id,!pageOpen);
    if(wait>0)yield return CheckoutUiKit.Wait(wait);
   }
   // The new look: a live 3/4 snapshot of the new tier's own model (taken as its reveal began); the build-mode sprite
   // of the tier only when that picture could not be taken, and a picture of the piece as it stands as the last resort.
   if(conquestPortraitTex){Destroy(conquestPortraitTex);conquestPortraitTex=null;}
   if(evolution)conquestPortraitTex=CheckoutEvolutionReveal.Instance.TakeSnapshot(data.id);bool snap=conquestPortraitTex;
   var tierSprite=evolution&&!conquestPortraitTex?CheckoutEvolutionReveal.TierSprite(data.reveal.template):null;
   if(evolution&&!conquestPortraitTex&&!tierSprite)conquestPortraitTex=CheckoutEvolutionReveal.Portrait(data.reveal.kind,data.reveal.targetId);
   QaCardPicture=!evolution?"":snap?"snapshot":tierSprite?"sprite":conquestPortraitTex?"portrait":"none";
   conquestPortrait.texture=conquestPortraitTex;conquestPortrait.enabled=conquestPortraitTex;
   var tint=K.C(string.IsNullOrEmpty(data.tint)?"3F9E52":data.tint);
   conquestRim.color=Color.Lerp(tint,Color.black,.15f);conquestBand.color=tint;
   foreach(var t in conquestTails)t.color=Color.Lerp(tint,Color.black,t.name=="Fold"?.45f:.25f);
   conquestIcon.sprite=tierSprite?tierSprite:K.Icon(data.icon);conquestIcon.enabled=conquestIcon.sprite&&!conquestPortraitTex;
   conquestIcon.rectTransform.sizeDelta=tierSprite?new Vector2(176,176):new Vector2(138,138);
   conquestHeadline.text=K.Clean(data.headline);conquestTitle.text=K.Clean(data.title);conquestSubtitle.text=K.Clean(data.subtitle);
   foreach(Transform child in conquestChips){child.gameObject.SetActive(false);Destroy(child.gameObject);}
   foreach(var chip in data.chips??new DesktopCelebrationChip[0])ConquestChip(chip);
   foreach(Transform child in conquestStats){child.gameObject.SetActive(false);Destroy(child.gameObject);}
   foreach(Transform child in conquestProducts){child.gameObject.SetActive(false);Destroy(child.gameObject);}
   conquestCounters.Clear();
   foreach(var stat in data.stats??new DesktopCelebrationStat[0])ConquestStat(stat);
   foreach(var product in data.products??new DesktopCelebrationProduct[0])ConquestProduct(product);
   bool hasStats=conquestStats.childCount>0,hasProducts=conquestProducts.childCount>0;
   // An evolution with numbers (shelves, sectors): medal, ribbon, the name with the tier as pips, the numbers, the NOVO
   // product and the buttons, with even room between them (no description line, Lucas 01/11). The rest: as before.
   bool tierCard=evolution&&hasStats;
   foreach(Transform child in conquestPips){child.gameObject.SetActive(false);Destroy(child.gameObject);}
   int pips=tierCard&&data.reveal.maxTier>1?Mathf.Min(data.reveal.maxTier,6):0;
   for(int i=0;i<pips;i++){
    var pip=N.Image(conquestPips,"Pip",Color.white,0);pip.sprite=CheckoutConfettiArt.StarSprite(i<data.reveal.tier);pip.preserveAspect=true;pip.raycastTarget=false;
    var pl=pip.gameObject.AddComponent<LayoutElement>();pl.preferredWidth=pl.preferredHeight=i<data.reveal.tier?44:34;
   }
   conquestPips.gameObject.SetActive(pips>0);conquestPipsBack.gameObject.SetActive(pips>0);
   int filled=Mathf.Min(pips,tierCard?data.reveal.tier:0);conquestPipsBack.rectTransform.sizeDelta=new Vector2(filled*44+(pips-filled)*34+(pips-1)*6+32,52);
   conquestSubtitle.gameObject.SetActive(!tierCard);
   if(tierCard){
    const float medalY=200,ribbonY=52,titleY=-22;
    float y=titleY-28;                                              // the title's bottom, then each row's top and centre
    if(pips>0){y-=10;conquestPips.anchoredPosition=conquestPipsBack.rectTransform.anchoredPosition=new Vector2(0,y-26);y-=52;}
    y-=18;conquestStats.anchoredPosition=new Vector2(0,y-58);y-=116;
    if(hasProducts){y-=26;conquestProducts.anchoredPosition=new Vector2(0,y-54);y-=108;}
    y-=28;conquestButtons.anchoredPosition=new Vector2(0,y-31);y-=62;
    float top=medalY+115;
    conquestStage.anchoredPosition=new Vector2(0,-(top+y)*.5f);      // the whole block centred on the screen
    StageAt(medalY,ribbonY,titleY);
   }else{
    conquestStage.anchoredPosition=Vector2.zero;StageAt(170,26,-30);
    // the rows stack under the subtitle: chips (if any), numbers, products, then the buttons
    float y=-152;if(conquestChips.childCount>0)y-=58;
    conquestStats.anchoredPosition=new Vector2(0,y);if(hasStats)y-=84;
    conquestProducts.anchoredPosition=new Vector2(0,y);if(hasProducts)y-=104;
    conquestButtons.anchoredPosition=new Vector2(0,Mathf.Min(-226,y-10));
   }
   // the card: from just over the title to just under the buttons (the text block's top is the stage's centre)
   {float cardTop=conquestTitle.rectTransform.anchoredPosition.y+29+12,cardBottom=conquestButtons.anchoredPosition.y-31-22;
    conquestCard.anchoredPosition=new Vector2(0,cardTop);conquestCard.sizeDelta=new Vector2(940,cardTop-cardBottom);}
   LayoutRebuilder.ForceRebuildLayoutImmediate(conquestStats);LayoutRebuilder.ForceRebuildLayoutImmediate(conquestProducts);LayoutRebuilder.ForceRebuildLayoutImmediate(conquestPips);
   conquestGo.gameObject.SetActive(!string.IsNullOrEmpty(data.button));
   if(!string.IsNullOrEmpty(data.button))conquestGo.Apply(new DesktopButton{label=K.Clean(data.button),variant="secondary",enabled=true,icon="",action="",args="[]",route="",after="",ok="",fail="",badge=""});
   LayoutRebuilder.ForceRebuildLayoutImmediate(conquestChips);LayoutRebuilder.ForceRebuildLayoutImmediate(conquestButtons);

   // Reset and play.
   conquestRoot.gameObject.SetActive(true);conquestRoot.SetAsLastSibling();
   conquestDim.color=U.TapCatcher;conquestCardGroup.alpha=0;
   conquestMedal.localScale=Vector3.zero;conquestRibbon.localScale=new Vector3(0,1,1);conquestRays.transform.localScale=Vector3.zero;conquestGlow.transform.localScale=Vector3.zero;
   conquestText.alpha=0;foreach(Transform chip in conquestChips)chip.localScale=Vector3.zero;
   StartCoroutine(U.Scale(conquestRays.transform,Vector3.one,.5f,true));StartCoroutine(U.Scale(conquestGlow.transform,Vector3.one,.45f));
   // (brisk: the numbers stand at their new values about 0.8 s after the card shows)
   yield return U.Scale(conquestMedal,Vector3.one,.36f,true);
   var fanfare=U.Sfx("conquest");if(fanfare&&conquestAudio)conquestAudio.PlayOneShot(fanfare,.9f);else Sound("success");
   StartCoroutine(U.Pop(conquestMedal,1.18f,.3f));
   U.Sparkles(this,conquestStage,conquestMedal.anchoredPosition,12,220);
   ConquestConfettiBurst(84,evolution?CheckoutConfettiArt.AccentFor(data.reveal.kind,data.reveal.targetId):CheckoutConfettiArt.Gold);
   StartCoroutine(U.Scale(conquestRibbon,Vector3.one,.26f,true));
   float delay=0;foreach(Transform chip in conquestChips){StartCoroutine(LevelPopIn(chip,delay));delay+=.05f;}
   foreach(Transform tile in conquestStats){StartCoroutine(LevelPopIn(tile,delay));delay+=.05f;}
   if(conquestCounters.Count>0)StartCoroutine(CountUp(.42f));
   foreach(Transform pip in conquestPips){pip.localScale=Vector3.zero;StartCoroutine(LevelPopIn(pip,delay*.5f));}
   if(conquestPipsBack.gameObject.activeSelf){conquestPipsBack.transform.localScale=new Vector3(0,1,1);StartCoroutine(U.Scale(conquestPipsBack.transform,Vector3.one,.25f,true));}
   foreach(Transform tile in conquestProducts){StartCoroutine(LevelPopIn(tile,delay));delay+=.08f;}
   for(float t=0;t<1;t+=CheckoutUiKit.Dt/.22f){conquestText.alpha=conquestCardGroup.alpha=t;yield return null;}
   conquestText.alpha=conquestCardGroup.alpha=1;
   conquestRun=null;
  }

  void ConquestChip(DesktopCelebrationChip chip){
   var pill=N.Image(conquestChips,"Chip",new Color(1,.97f,.9f,.95f),20);
   var row=N.Row(pill.gameObject,8,new RectOffset(12,16,6,6));row.childAlignment=TextAnchor.MiddleLeft;row.childControlWidth=row.childControlHeight=true;row.childForceExpandWidth=false;
   pill.gameObject.AddComponent<ContentSizeFitter>().horizontalFit=ContentSizeFitter.FitMode.PreferredSize;
   var le=pill.gameObject.AddComponent<LayoutElement>();le.preferredHeight=46;
   var icon=N.Image(pill.transform,"Icon",Color.white,0);icon.sprite=K.Icon(chip.icon);icon.preserveAspect=true;var il=icon.gameObject.AddComponent<LayoutElement>();il.preferredWidth=il.preferredHeight=30;
   if(!icon.sprite)icon.gameObject.SetActive(false);
   var text=N.Text(pill.transform,"Text",K.Label,19,K.Ink);text.textWrappingMode=TextWrappingModes.NoWrap;text.alignment=TextAlignmentOptions.MidlineLeft;text.text=K.Clean(chip.text);
  }

  // A number of the evolution: the icon and a short label on top, a big "before → after" under them (counts up).
  void ConquestStat(DesktopCelebrationStat stat){
   var tile=N.Image(conquestStats,"Stat",new Color(.11f,.17f,.31f,.94f),18);
   var le=tile.gameObject.AddComponent<LayoutElement>();le.preferredWidth=214;le.preferredHeight=116;
   var rim=tile.gameObject.AddComponent<Outline>();rim.effectColor=K.C("E0B040");rim.effectDistance=new Vector2(2,-2);
   var icon=N.Image(tile.transform,"Icon",Color.white,0);icon.sprite=K.Icon(stat.icon);icon.preserveAspect=true;U.At(icon.rectTransform,new Vector2(0,1),new Vector2(38,38),new Vector2(32,-30));
   if(!icon.sprite)icon.gameObject.SetActive(false);
   var label=N.Text(tile.transform,"Label",K.Label,19,K.C("C9D7EE"));label.alignment=TextAlignmentOptions.MidlineLeft;label.textWrappingMode=TextWrappingModes.NoWrap;
   label.enableAutoSizing=true;label.fontSizeMin=13;label.fontSizeMax=19;label.overflowMode=TextOverflowModes.Ellipsis;label.text=K.Clean(stat.label);
   U.Stretch(label.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(58,-50),new Vector2(-10,-10));
   var value=N.Text(tile.transform,"Value",K.Headline,38,K.C("FFE08A"));value.alignment=TextAlignmentOptions.Center;value.textWrappingMode=TextWrappingModes.NoWrap;value.richText=true;
   value.enableAutoSizing=true;value.fontSizeMin=20;value.fontSizeMax=38;
   U.Stretch(value.rectTransform,Vector2.zero,new Vector2(1,0),new Vector2(10,8),new Vector2(-10,64));
   value.text=StatText(stat,0);conquestCounters.Add((value,stat));
  }
  static string StatText(DesktopCelebrationStat s,float k){
   float now=Mathf.Lerp(s.from,s.to,k);string suffix=s.suffix??"";
   return "<color=#AFC2E0><size=74%>"+Mathf.RoundToInt(s.from)+suffix+"</size></color> <color=#E0B040><size=70%>→</size></color> "+Mathf.RoundToInt(now)+suffix;
  }
  public bool QaCountDone{get;private set;}public string QaCardPicture{get;private set;}="";
  public Texture QaPortrait=>conquestPortrait&&conquestPortrait.enabled?conquestPortrait.texture:null;
  public string[] QaStatTexts=>conquestCounters.Select(c=>c.text?c.text.text:"").ToArray();
  IEnumerator CountUp(float seconds){
   QaCountDone=false;
   var tick=U.Sfx("coin_0");int last=-1;
   for(float k=0;k<1;k+=CheckoutUiKit.Dt/seconds){
    float e=1-(1-k)*(1-k);
    foreach(var (text,stat) in conquestCounters)if(text)text.text=StatText(stat,e);
    int step=Mathf.FloorToInt(e*8);if(step!=last&&tick&&conquestAudio){last=step;conquestAudio.PlayOneShot(tick,.12f);}
    yield return null;
   }
   foreach(var (text,stat) in conquestCounters)if(text)text.text=StatText(stat,1);
   QaCountDone=true;
  }
  // A product the evolution opened: its icon with a NOVO badge and its name.
  // (the icon big on the left, the name beside it, the NOVO badge inside the tile's top right corner)
  void ConquestProduct(DesktopCelebrationProduct product){
   var tile=N.Image(conquestProducts,"Product",new Color(1,.97f,.9f,.97f),20);
   var le=tile.gameObject.AddComponent<LayoutElement>();le.preferredWidth=340;le.preferredHeight=108;
   var rim=tile.gameObject.AddComponent<Outline>();rim.effectColor=K.C("E0B040");rim.effectDistance=new Vector2(2,-2);
   var icon=N.Image(tile.transform,"Icon",Color.white,0);icon.sprite=K.Icon(product.icon);icon.preserveAspect=true;U.At(icon.rectTransform,new Vector2(0,.5f),new Vector2(88,88),new Vector2(58,0));
   var name=N.Text(tile.transform,"Name",K.Label,24,K.Ink);name.alignment=TextAlignmentOptions.MidlineLeft;name.textWrappingMode=TextWrappingModes.Normal;
   name.enableAutoSizing=true;name.fontSizeMin=15;name.fontSizeMax=24;name.text=K.Clean(product.name);
   U.Stretch(name.rectTransform,Vector2.zero,Vector2.one,new Vector2(112,8),new Vector2(-14,-36));
   var badge=N.Image(tile.transform,"Novo",K.C("E8452C"),12);U.At(badge.rectTransform,new Vector2(1,1),new Vector2(104,28),new Vector2(-62,-22));badge.transform.localRotation=Quaternion.Euler(0,0,4);
   var text=N.Text(badge.transform,"Text",K.Headline,16,Color.white);text.alignment=TextAlignmentOptions.Center;text.textWrappingMode=TextWrappingModes.NoWrap;
   text.enableAutoSizing=true;text.fontSizeMin=10;text.fontSizeMax=16;text.text=CheckoutI18n.T("NOVO");U.Stretch(text.rectTransform,Vector2.zero,Vector2.one,new Vector2(6,0),new Vector2(-6,0));
  }
  void StageAt(float medalY,float ribbonY,float titleY){
   conquestMedal.anchoredPosition=new Vector2(0,medalY);conquestRays.rectTransform.anchoredPosition=new Vector2(0,medalY);conquestGlow.rectTransform.anchoredPosition=new Vector2(0,medalY);
   conquestRibbon.anchoredPosition=new Vector2(0,ribbonY);conquestTitle.rectTransform.anchoredPosition=new Vector2(0,titleY);
  }
  /// <summary>QA: the card's gaps in canvas units (title → pips/numbers, numbers → NOVO tile, NOVO tile → buttons) and
  /// whether every NOVO badge sits inside its tile; NaN where a row is missing.</summary>
  public float[] QaCardGaps(){
   Rect R(RectTransform r){var c=new Vector3[4];r.GetWorldCorners(c);var a=conquestRoot.InverseTransformPoint(c[0]);var b=conquestRoot.InverseTransformPoint(c[2]);return Rect.MinMaxRect(a.x,a.y,b.x,b.y);}
   Rect Union(Transform row){Rect u=default;bool any=false;foreach(Transform t in row){if(!t.gameObject.activeSelf)continue;var r=R((RectTransform)t);foreach(Transform k in t)if(k.name=="Novo"){var b=R((RectTransform)k);r=Rect.MinMaxRect(Mathf.Min(r.xMin,b.xMin),Mathf.Min(r.yMin,b.yMin),Mathf.Max(r.xMax,b.xMax),Mathf.Max(r.yMax,b.yMax));}u=any?Rect.MinMaxRect(Mathf.Min(u.xMin,r.xMin),Mathf.Min(u.yMin,r.yMin),Mathf.Max(u.xMax,r.xMax),Mathf.Max(u.yMax,r.yMax)):r;any=true;}return any?u:new Rect(float.NaN,float.NaN,0,0);}
   var title=R(conquestTitle.rectTransform);var stats=Union(conquestStats);var products=Union(conquestProducts);var buttons=Union(conquestButtons);
   float inside=1;foreach(Transform t in conquestProducts){var tr=R((RectTransform)t);foreach(Transform k in t)if(k.name=="Novo"){var b=R((RectTransform)k);if(b.xMin<tr.xMin-.5f||b.xMax>tr.xMax+.5f||b.yMin<tr.yMin-.5f||b.yMax>tr.yMax+.5f)inside=0;}}
   float statsTop=stats.yMax,belowTitle=title.yMin-(conquestPips.gameObject.activeSelf?R(conquestPips).yMax:statsTop);
   return new[]{belowTitle,stats.yMin-products.yMax,(float.IsNaN(products.y)?stats.yMin:products.yMin)-buttons.yMax,inside};
  }

  void ConquestConfettiBurst(int count,Color accent){
   Vector2 from=conquestConfetti.InverseTransformPoint(conquestMedal.position);
   for(int i=0;i<count;i++){
    int row=Random.Range(0,CheckoutConfettiArt.RowCount),col=Random.Range(0,CheckoutConfettiArt.Cols);
    var go=new GameObject("Piece",typeof(RectTransform),typeof(Image));go.transform.SetParent(conquestConfetti,false);
    var img=go.GetComponent<Image>();img.sprite=CheckoutConfettiArt.Sprite(accent,row,col);img.raycastTarget=false;
    var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);
    float size=CheckoutConfettiArt.IsStar(row)?Random.Range(20f,28f):Random.Range(26f,40f);r.sizeDelta=new Vector2(size,size);
    r.anchoredPosition=from+Random.insideUnitCircle*30;r.localRotation=Quaternion.Euler(0,0,Random.Range(0f,360f));
    var angle=Random.Range(15f,165f)*Mathf.Deg2Rad;var speed=Random.Range(480f,1050f);
    conquestPieces.Add(new CardConfetto{rect=r,image=img,row=row,col=col,accent=accent,velocity=new Vector2(Mathf.Cos(angle)*speed*1.25f,Mathf.Sin(angle)*speed),
     spin=Random.Range(-300f,300f),flip=Random.Range(0f,6.28f),flipSpeed=Random.Range(4f,10f),frame=col,frameSpeed=Random.Range(7f,15f),sway=Random.Range(0f,6.28f),life=Random.Range(2.2f,3.2f)});
   }
  }

  void UpdateConquest(){
   if(!conquestRoot||!conquestRoot.gameObject.activeSelf)return;
   if(Input.GetKeyDown(KeyCode.Escape)){CloseConquest("");return;}
   float dt=CheckoutUiKit.Dt;
   if(conquestRays)conquestRays.transform.Rotate(0,0,-16*dt);
   if(conquestGlow){var c=conquestGlow.color;c.a=.7f+.15f*Mathf.Sin(Time.unscaledTime*2.4f);conquestGlow.color=c;}
   if(conquestContinue&&conquestRun==null){var s=1+.03f*Mathf.Sin(Time.unscaledTime*4);conquestContinue.transform.localScale=new Vector3(s,s,1);}
   // each piece flutters down: air drag, a slow fall, a sway; it spins and turns over (its width through zero) while
   // its picture steps through the piece turning in the light (the gold ones flash)
   for(int i=conquestPieces.Count-1;i>=0;i--){
    var p=conquestPieces[i];
    if(!p.rect){conquestPieces.RemoveAt(i);continue;}
    p.velocity+=new Vector2(-p.velocity.x*1.1f*dt,-820*dt);p.velocity.y=Mathf.Max(p.velocity.y,-300);
    p.sway+=dt*3.2f;p.rect.anchoredPosition+=p.velocity*dt+new Vector2(Mathf.Sin(p.sway)*46*dt,0);
    p.rect.Rotate(0,0,p.spin*dt);p.flip+=p.flipSpeed*dt;var sc=p.rect.localScale;sc.x=Mathf.Cos(p.flip);p.rect.localScale=sc;
    p.frame+=p.frameSpeed*dt;int col=(int)p.frame%CheckoutConfettiArt.Cols;
    if(col!=p.col){p.col=col;p.image.sprite=CheckoutConfettiArt.Sprite(p.accent,p.row,col);}
    p.life-=dt;
    if(p.life<.5f){var c=p.image.color;c.a=Mathf.Clamp01(p.life/.5f);p.image.color=c;}
    if(p.life<=0){Destroy(p.rect.gameObject);conquestPieces.RemoveAt(i);}
   }
  }
 }
}
