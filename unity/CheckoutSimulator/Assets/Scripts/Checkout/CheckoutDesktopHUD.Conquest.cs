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
  TextMeshProUGUI conquestHeadline,conquestTitle,conquestSubtitle;CanvasGroup conquestText;
  // Evolutions: the new look (a picture of the piece), the numbers counting up and the products opened (NOVO).
  RectTransform conquestStats,conquestProducts;RawImage conquestPortrait;Texture2D conquestPortraitTex;
  readonly List<(TextMeshProUGUI text,DesktopCelebrationStat stat)> conquestCounters=new List<(TextMeshProUGUI,DesktopCelebrationStat)>();
  CheckoutDesktopButton conquestContinue,conquestGo;
  string conquestShownKey,conquestClosedKey,conquestId,conquestRoute;Coroutine conquestRun;bool conquestPlaying,conquestEvolution;
  AudioSource conquestAudio;
  readonly List<LevelConfetto> conquestPieces=new List<LevelConfetto>();
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

   conquestDim=N.Image(conquestRoot,"Dim",new Color(.06f,.08f,.15f,.6f),0);conquestDim.raycastTarget=true;U.Stretch(conquestDim.rectTransform,Vector2.zero,Vector2.one,new Vector2(-900,-900),new Vector2(900,900));
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
   conquestTitle=U.Label(textNode,"Title",K.Headline,46,"FFFFFF");U.At(conquestTitle.rectTransform,new Vector2(.5f,1),new Vector2(900,58),new Vector2(0,-30));
   conquestTitle.outlineWidth=.18f;conquestTitle.outlineColor=new Color32(15,20,40,220);conquestTitle.overflowMode=TextOverflowModes.Overflow;
   conquestSubtitle=U.Label(textNode,"Subtitle",K.Label,22,"FFF1D6");U.At(conquestSubtitle.rectTransform,new Vector2(.5f,1),new Vector2(820,60),new Vector2(0,-92));
   conquestSubtitle.textWrappingMode=TextWrappingModes.Normal;conquestSubtitle.overflowMode=TextOverflowModes.Overflow;
   conquestChips=N.Node("Chips",textNode);U.At(conquestChips,new Vector2(.5f,1),new Vector2(900,48),new Vector2(0,-152));
   var row=N.Row(conquestChips.gameObject,12,new RectOffset(0,0,0,0));row.childAlignment=TextAnchor.MiddleCenter;row.childControlWidth=row.childControlHeight=true;row.childForceExpandWidth=false;
   // (evolutions) before → after numbers and the new products, between the chips and the buttons
   conquestStats=N.Node("Stats",textNode);U.At(conquestStats,new Vector2(.5f,1),new Vector2(900,74),new Vector2(0,-140));
   var statsRow=N.Row(conquestStats.gameObject,12,new RectOffset(0,0,0,0));statsRow.childAlignment=TextAnchor.MiddleCenter;statsRow.childControlWidth=statsRow.childControlHeight=true;statsRow.childForceExpandWidth=false;
   conquestProducts=N.Node("Products",textNode);U.At(conquestProducts,new Vector2(.5f,1),new Vector2(900,96),new Vector2(0,-222));
   var productsRow=N.Row(conquestProducts.gameObject,14,new RectOffset(0,0,0,0));productsRow.childAlignment=TextAnchor.MiddleCenter;productsRow.childControlWidth=productsRow.childControlHeight=true;productsRow.childForceExpandWidth=false;
   conquestButtons=N.Node("Buttons",textNode);U.At(conquestButtons,new Vector2(.5f,1),new Vector2(600,64),new Vector2(0,-226));
   var buttons=N.Row(conquestButtons.gameObject,16,new RectOffset(0,0,0,0));buttons.childAlignment=TextAnchor.MiddleCenter;buttons.childControlWidth=buttons.childControlHeight=true;buttons.childForceExpandWidth=false;
   conquestGo=U.Button(conquestButtons,"Ver","secondary",()=>CloseConquest(conquestRoute),62,22);Size(conquestGo,240);
   conquestContinue=U.Button(conquestButtons,"Continuar","success",()=>CloseConquest(""),62,24);Size(conquestContinue,250);

   conquestConfetti=N.Node("Confetti",conquestRoot);U.Stretch(conquestConfetti,Vector2.zero,Vector2.one);
   conquestRoot.gameObject.SetActive(false);
  }
  static void Size(CheckoutDesktopButton button,float width){var le=button.gameObject.GetComponent<LayoutElement>();if(!le)le=button.gameObject.AddComponent<LayoutElement>();le.preferredWidth=width;le.preferredHeight=62;}

  void ApplyConquest(DesktopView v){
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
   // the rows stack under the subtitle: chips (if any), numbers, products, then the buttons
   float y=-152;if(conquestChips.childCount>0)y-=58;
   conquestStats.anchoredPosition=new Vector2(0,y);if(hasStats)y-=84;
   conquestProducts.anchoredPosition=new Vector2(0,y);if(hasProducts)y-=104;
   conquestButtons.anchoredPosition=new Vector2(0,Mathf.Min(-226,y-10));
   conquestGo.gameObject.SetActive(!string.IsNullOrEmpty(data.button));
   if(!string.IsNullOrEmpty(data.button))conquestGo.Apply(new DesktopButton{label=K.Clean(data.button),variant="secondary",enabled=true,icon="",action="",args="[]",route="",after="",ok="",fail="",badge=""});
   LayoutRebuilder.ForceRebuildLayoutImmediate(conquestChips);LayoutRebuilder.ForceRebuildLayoutImmediate(conquestButtons);

   // Reset and play.
   conquestRoot.gameObject.SetActive(true);conquestRoot.SetAsLastSibling();
   conquestDim.color=new Color(.06f,.08f,.15f,0);
   conquestMedal.localScale=Vector3.zero;conquestRibbon.localScale=new Vector3(0,1,1);conquestRays.transform.localScale=Vector3.zero;conquestGlow.transform.localScale=Vector3.zero;
   conquestText.alpha=0;foreach(Transform chip in conquestChips)chip.localScale=Vector3.zero;
   StartCoroutine(U.Fade(conquestDim,.58f,.3f));
   StartCoroutine(U.Scale(conquestRays.transform,Vector3.one,.5f,true));StartCoroutine(U.Scale(conquestGlow.transform,Vector3.one,.45f));
   // (brisk: the numbers stand at their new values about 0.8 s after the card shows)
   yield return U.Scale(conquestMedal,Vector3.one,.36f,true);
   var fanfare=U.Sfx("conquest");if(fanfare&&conquestAudio)conquestAudio.PlayOneShot(fanfare,.9f);else Sound("success");
   StartCoroutine(U.Pop(conquestMedal,1.18f,.3f));
   U.Sparkles(this,conquestStage,new Vector2(0,170),12,220);
   ConquestConfettiBurst(70);
   StartCoroutine(U.Scale(conquestRibbon,Vector3.one,.26f,true));
   float delay=0;foreach(Transform chip in conquestChips){StartCoroutine(LevelPopIn(chip,delay));delay+=.05f;}
   foreach(Transform tile in conquestStats){StartCoroutine(LevelPopIn(tile,delay));delay+=.05f;}
   if(conquestCounters.Count>0)StartCoroutine(CountUp(.42f));
   foreach(Transform tile in conquestProducts){StartCoroutine(LevelPopIn(tile,delay));delay+=.08f;}
   for(float t=0;t<1;t+=CheckoutUiKit.Dt/.22f){conquestText.alpha=t;yield return null;}
   conquestText.alpha=1;
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

  // A number of the evolution: "Por produto 10 → 15" (counts up from the old value to the new one).
  void ConquestStat(DesktopCelebrationStat stat){
   var tile=N.Image(conquestStats,"Stat",new Color(.11f,.17f,.31f,.92f),16);
   var le=tile.gameObject.AddComponent<LayoutElement>();le.preferredWidth=196;le.preferredHeight=72;
   var rim=tile.gameObject.AddComponent<Outline>();rim.effectColor=K.C("E0B040");rim.effectDistance=new Vector2(2,-2);
   var icon=N.Image(tile.transform,"Icon",Color.white,0);icon.sprite=K.Icon(stat.icon);icon.preserveAspect=true;U.At(icon.rectTransform,new Vector2(0,.5f),new Vector2(34,34),new Vector2(26,0));
   if(!icon.sprite)icon.gameObject.SetActive(false);
   var label=N.Text(tile.transform,"Label",K.Label,15,K.C("BFD0E8"));label.alignment=TextAlignmentOptions.MidlineLeft;label.text=K.Clean(stat.label);U.Stretch(label.rectTransform,new Vector2(0,.52f),Vector2.one,new Vector2(50,0),new Vector2(-8,-4));
   var value=N.Text(tile.transform,"Value",K.Headline,24,K.C("FFE08A"));value.alignment=TextAlignmentOptions.MidlineLeft;value.textWrappingMode=TextWrappingModes.NoWrap;
   U.Stretch(value.rectTransform,Vector2.zero,new Vector2(1,.56f),new Vector2(50,4),new Vector2(-8,0));
   value.text=StatText(stat,0);conquestCounters.Add((value,stat));
  }
  static string StatText(DesktopCelebrationStat s,float k){
   float now=Mathf.Lerp(s.from,s.to,k);string suffix=s.suffix??"";
   return Mathf.RoundToInt(s.from)+suffix+"  →  "+Mathf.RoundToInt(now)+suffix;
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
  void ConquestProduct(DesktopCelebrationProduct product){
   var tile=N.Image(conquestProducts,"Product",new Color(1,.97f,.9f,.96f),18);
   var le=tile.gameObject.AddComponent<LayoutElement>();le.preferredWidth=260;le.preferredHeight=92;
   var icon=N.Image(tile.transform,"Icon",Color.white,0);icon.sprite=K.Icon(product.icon);icon.preserveAspect=true;U.At(icon.rectTransform,new Vector2(0,.5f),new Vector2(76,76),new Vector2(48,0));
   var name=N.Text(tile.transform,"Name",K.Label,19,K.Ink);name.alignment=TextAlignmentOptions.MidlineLeft;name.textWrappingMode=TextWrappingModes.Normal;name.text=K.Clean(product.name);
   U.Stretch(name.rectTransform,Vector2.zero,Vector2.one,new Vector2(94,6),new Vector2(-10,-6));
   var badge=N.Image(tile.transform,"Novo",K.C("E8452C"),12);U.At(badge.rectTransform,new Vector2(0,1),new Vector2(70,28),new Vector2(36,-4));badge.transform.localRotation=Quaternion.Euler(0,0,8);
   var text=N.Text(badge.transform,"Text",K.Headline,15,Color.white);text.alignment=TextAlignmentOptions.Center;text.text="NOVO";U.Stretch(text.rectTransform,Vector2.zero,Vector2.one);
  }

  void ConquestConfettiBurst(int count){
   for(int i=0;i<count;i++){
    var piece=N.Image(conquestConfetti,"Piece",K.C(ConfettiColors[i%ConfettiColors.Length]),i%3==0?4:0);
    var r=piece.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);
    r.sizeDelta=i%4==0?new Vector2(12,12):new Vector2(Random.Range(8,13),Random.Range(16,24));
    r.anchoredPosition=new Vector2(0,170);
    var angle=Random.Range(20f,160f)*Mathf.Deg2Rad;var speed=Random.Range(420f,900f);
    conquestPieces.Add(new LevelConfetto{rect=r,velocity=new Vector2(Mathf.Cos(angle)*speed*1.2f,Mathf.Sin(angle)*speed),spin=Random.Range(-540f,540f),life=Random.Range(2f,3f)});
   }
  }

  void UpdateConquest(){
   if(!conquestRoot||!conquestRoot.gameObject.activeSelf)return;
   if(Input.GetKeyDown(KeyCode.Escape)){CloseConquest("");return;}
   float dt=CheckoutUiKit.Dt;
   if(conquestRays)conquestRays.transform.Rotate(0,0,-16*dt);
   if(conquestGlow){var c=conquestGlow.color;c.a=.7f+.15f*Mathf.Sin(Time.unscaledTime*2.4f);conquestGlow.color=c;}
   if(conquestContinue&&conquestRun==null){var s=1+.03f*Mathf.Sin(Time.unscaledTime*4);conquestContinue.transform.localScale=new Vector3(s,s,1);}
   for(int i=conquestPieces.Count-1;i>=0;i--){
    var p=conquestPieces[i];
    if(!p.rect){conquestPieces.RemoveAt(i);continue;}
    p.velocity+=new Vector2(-p.velocity.x*.9f*dt,-900*dt);p.velocity.y=Mathf.Max(p.velocity.y,-520);
    p.rect.anchoredPosition+=p.velocity*dt+new Vector2(Mathf.Sin(Time.unscaledTime*6+i)*30*dt,0);
    p.rect.Rotate(0,0,p.spin*dt);p.life-=dt;
    if(p.life<.5f){var img=p.rect.GetComponent<Image>();if(img){var c=img.color;c.a=Mathf.Clamp01(p.life/.5f);img.color=c;}}
    if(p.life<=0){Destroy(p.rect.gameObject);conquestPieces.RemoveAt(i);}
   }
  }
 }
}
