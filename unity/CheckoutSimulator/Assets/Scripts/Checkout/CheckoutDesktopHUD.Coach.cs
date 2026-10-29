using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // Dona Neide's tutorial and one-off tips (desktop/view.ts "coach", rules in src/services/onboarding.ts).
 // The host says WHAT to explain and WHERE to point (a target string); this file finds that thing on screen
 // and draws the guide: a dimmed screen with a hole over the target (spotlight), a speech bubble with her
 // portrait, a tapping hand, the step counter, and a little celebration when a step pays a prize.
 // Targets: world:<panel>[:<shelfId>] | tool:<route> | market | action:<name> | route:<prefix> | fab:caixa|repor|entrega | goal | help |
 // settings | close (the open page's X), several separated by "|" (the first one found wins). A target only counts when a finger
 // on it would reach it: scrolled out of its list, or under the page window or another window, it is not on screen (under the
 // page window the guide points at the page's X instead, QA 29/10). The hole lets taps through, so the player plays the real
 // game; while a game window (register, shop, dock…) or the Opções window is open the guide shrinks to a corner note or hides.
 // Also here: the "next objective" card under the top bar (view.goal).
 public partial class CheckoutDesktopHUD {
  RectTransform coachRoot,coachCard,coachHand,coachRing,coachReward,coachPath,coachCompact;
  readonly Image[] coachDims=new Image[4];Image coachFull,coachPortrait,coachCompactPortrait;CanvasGroup coachGroup,coachRewardGroup;
  TextMeshProUGUI coachName,coachTitle,coachText,coachStep,coachCompactText,coachRewardText;
  CheckoutDesktopButton coachButton;GameObject coachSkip;LayoutElement coachCardWidth;
  DesktopCoach coach;string coachKey="",coachRewardSeen=null;float coachMissingSince=-1,coachShownAt;
  AudioSource coachSound;
  // Next-objective card (HUD canvas).
  GameObject goalCard;TextMeshProUGUI goalCardText,goalCardDetail;Image goalCardIcon,goalCardEdge;RectTransform goalCardFill;string goalRoute="";

  void BuildCoach(){
   coachSound=gameObject.AddComponent<AudioSource>();coachSound.playOnAwake=false;coachSound.volume=.5f;
   // Own canvas above the game windows (80–86) and below the level-up celebration (95).
   var go=new GameObject("CheckoutCoach",typeof(RectTransform));go.transform.SetParent(transform,false);
   var canvas=go.AddComponent<Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=88;
   CheckoutScreen.Fit(go.AddComponent<CanvasScaler>());go.AddComponent<GraphicRaycaster>();
   coachRoot=CheckoutScreen.SafeArea(go.transform);coachGroup=coachRoot.gameObject.AddComponent<CanvasGroup>();
   var shade=new Color(.12f,.08f,.04f,.62f);
   // Full dim for the welcome card; four dims around the hole for a spotlight (taps inside the hole go through).
   // The dims reach past the safe area to the screen's edges (on the iPhone the strip by the island stayed bright).
   coachFull=N.Image(coachRoot,"Dim",shade,0);coachFull.raycastTarget=true;U.Stretch(coachFull.rectTransform,Vector2.zero,Vector2.one,-Vector2.one*DimBleed,Vector2.one*DimBleed);
   for(int i=0;i<4;i++){var d=N.Image(coachRoot,"Dim"+i,shade,0);d.raycastTarget=true;var r=d.rectTransform;r.anchorMin=r.anchorMax=r.pivot=Vector2.zero;coachDims[i]=d;}
   // Pulsing gold frame around the target.
   var ring=N.Image(coachRoot,"Ring",K.C("F2B03D"),0);ring.sprite=RingSprite();ring.type=Image.Type.Sliced;coachRing=ring.rectTransform;coachRing.anchorMin=coachRing.anchorMax=Vector2.zero;coachRing.pivot=new Vector2(.5f,.5f);
   // Tapping hand (same art and fingertip pivot as the mini-games' hint).
   var hand=U.Art(coachRoot,"Hand","hand_pointer",Vector2.zero,120);coachHand=hand.rectTransform;coachHand.anchorMin=coachHand.anchorMax=Vector2.zero;coachHand.pivot=HandTip;coachHand.localRotation=Quaternion.Euler(0,0,160);

   // Speech card: portrait + name tag on the left, title / text / buttons on the right.
   coachCard=N.Node("Card",coachRoot);coachCard.anchorMin=coachCard.anchorMax=Vector2.zero;coachCard.pivot=new Vector2(.5f,.5f);
   var fit=coachCard.gameObject.AddComponent<ContentSizeFitter>();fit.verticalFit=fit.horizontalFit=ContentSizeFitter.FitMode.PreferredSize;
   var edge=coachCard.gameObject.AddComponent<Image>();edge.sprite=K.Rounded(22);edge.type=Image.Type.Sliced;edge.color=K.C("C58A1E");edge.raycastTarget=true;
   N.Column(coachCard.gameObject,0,new RectOffset(3,3,3,7));
   var face=N.Image(coachCard,"Face",K.Cream,20);N.Row(face.gameObject,14,new RectOffset(16,18,14,14)).childAlignment=TextAnchor.UpperLeft;
   coachCardWidth=face.gameObject.AddComponent<LayoutElement>();coachCardWidth.preferredWidth=560;
   var who=N.Node("Who",face.transform);N.Column(who.gameObject,4).childAlignment=TextAnchor.UpperCenter;var wl=who.gameObject.AddComponent<LayoutElement>();wl.preferredWidth=wl.minWidth=104;
   var frame=N.Image(who,"Frame",K.C("F2B03D"),48);var fl=frame.gameObject.AddComponent<LayoutElement>();fl.preferredWidth=fl.preferredHeight=104;fl.minHeight=104;
   coachPortrait=N.Image(frame.transform,"Portrait",Color.white,0);coachPortrait.preserveAspect=true;U.Stretch(coachPortrait.rectTransform,Vector2.zero,Vector2.one,new Vector2(6,6),new Vector2(-6,-6));
   var tag=N.Image(who,"Tag",K.C("2E8CAE"),10);var tagl=tag.gameObject.AddComponent<LayoutElement>();tagl.preferredHeight=28;
   coachName=N.Text(tag.transform,"Name",K.Label,14,Color.white);coachName.alignment=TextAlignmentOptions.Center;coachName.textWrappingMode=TextWrappingModes.NoWrap;U.Stretch(coachName.rectTransform,Vector2.zero,Vector2.one);
   var body=N.Node("Body",face.transform);N.Column(body.gameObject,6);body.gameObject.AddComponent<LayoutElement>().flexibleWidth=1;
   var head=N.Node("Head",body);N.Row(head.gameObject,8);
   coachTitle=N.Text(head,"Title",K.Headline,24,K.Ink);coachTitle.gameObject.AddComponent<LayoutElement>().flexibleWidth=1;
   coachStep=N.Text(head,"Step",K.Number,14,K.Muted);coachStep.textWrappingMode=TextWrappingModes.NoWrap;coachStep.alignment=TextAlignmentOptions.TopRight;
   coachText=N.Text(body,"Text",K.Body,18,K.Ink);coachText.lineSpacing=4;
   // The road ahead (welcome card only): Mesinha › Tenda › … › Rede.
   var pathBox=N.Image(body,"Path",K.C("FBEEDA"),10);N.Column(pathBox.gameObject,0,new RectOffset(10,10,6,6));coachPath=pathBox.rectTransform;
   coachPathText=N.Text(pathBox.transform,"Stages",K.Label,14,K.Ink);coachPathText.lineSpacing=6;
   var buttons=N.Node("Buttons",body);var br=N.Row(buttons.gameObject,14,new RectOffset(0,0,6,0));br.childAlignment=TextAnchor.MiddleRight;
   var skip=N.Text(buttons,"Skip",K.Label,15,K.Muted);skip.text="Já sei jogar";skip.textWrappingMode=TextWrappingModes.NoWrap;skip.raycastTarget=true;
   U.Tap(skip,()=>CoachAction("skipOnboarding"));coachSkip=skip.gameObject;
   coachButton=CheckoutDesktopButton.Create(buttons,54,20,14);coachButton.SetWidth(220);coachButton.Clicked=_=>{if(coach!=null)CoachAction(coach.buttonAction);};

   // Corner note while a game window is open (does not block the game).
   coachCompact=N.Node("Compact",coachRoot);coachCompact.anchorMin=coachCompact.anchorMax=coachCompact.pivot=new Vector2(0,1);coachCompact.anchoredPosition=new Vector2(16,-16);
   var cfit=coachCompact.gameObject.AddComponent<ContentSizeFitter>();cfit.verticalFit=cfit.horizontalFit=ContentSizeFitter.FitMode.PreferredSize;
   var cedge=coachCompact.gameObject.AddComponent<Image>();cedge.sprite=K.Rounded(18);cedge.type=Image.Type.Sliced;cedge.color=K.C("C58A1E");cedge.raycastTarget=false;
   N.Column(coachCompact.gameObject,0,new RectOffset(2,2,2,5));
   var cface=N.Image(coachCompact,"Face",K.Cream,16);N.Row(cface.gameObject,10,new RectOffset(10,14,8,8)).childAlignment=TextAnchor.MiddleLeft;
   var cframe=N.Image(cface.transform,"Frame",K.C("F2B03D"),30);var cfl=cframe.gameObject.AddComponent<LayoutElement>();cfl.preferredWidth=cfl.preferredHeight=cfl.minHeight=64;
   // After a few seconds the note folds to her portrait (it sat over the register's customer and the windows' headers);
   // a tap on the portrait shows the text again.
   cframe.raycastTarget=true;U.Tap(cframe,()=>coachCompactAt=Time.unscaledTime);
   coachCompactPortrait=N.Image(cframe.transform,"Portrait",Color.white,0);coachCompactPortrait.preserveAspect=true;U.Stretch(coachCompactPortrait.rectTransform,Vector2.zero,Vector2.one,new Vector2(4,4),new Vector2(-4,-4));
   coachCompactText=N.Text(cface.transform,"Text",K.Body,16,K.Ink);var ctl=coachCompactText.gameObject.AddComponent<LayoutElement>();ctl.preferredWidth=380;

   // Prize banner ("Primeira venda! +20 moedas").
   coachReward=N.Node("Reward",coachRoot);coachReward.anchorMin=coachReward.anchorMax=coachReward.pivot=new Vector2(.5f,.72f);
   var rfit=coachReward.gameObject.AddComponent<ContentSizeFitter>();rfit.verticalFit=rfit.horizontalFit=ContentSizeFitter.FitMode.PreferredSize;
   var redge=coachReward.gameObject.AddComponent<Image>();redge.sprite=K.Rounded(22);redge.type=Image.Type.Sliced;redge.color=K.C("C58A1E");redge.raycastTarget=false;
   N.Column(coachReward.gameObject,0,new RectOffset(3,3,3,7));
   var rface=N.Image(coachReward,"Face",K.C("F2B03D"),20);N.Row(rface.gameObject,10,new RectOffset(18,22,10,10)).childAlignment=TextAnchor.MiddleCenter;
   var ricon=N.Image(rface.transform,"Icon",Color.white,0);ricon.sprite=K.Icon("Icons/trophy");ricon.preserveAspect=true;var ril=ricon.gameObject.AddComponent<LayoutElement>();ril.preferredWidth=ril.preferredHeight=40;
   coachRewardText=N.Text(rface.transform,"Text",K.Headline,24,K.Ink);coachRewardText.textWrappingMode=TextWrappingModes.NoWrap;
   coachRewardGroup=coachReward.gameObject.AddComponent<CanvasGroup>();coachRewardGroup.blocksRaycasts=false;coachReward.gameObject.SetActive(false);

   HideCoach();
   BuildGoalCard();
  }

  // "Próximo objetivo" under the top bar: what to do next to grow (buy the lot, save coins, evolve…).
  void BuildGoalCard(){
   // Top right, under the wallet: the left edge belongs to the floating CAIXA / REPOR / ENTREGA buttons.
   var node=N.Node("Goal",root);node.anchorMin=node.anchorMax=node.pivot=new Vector2(1,1);node.anchoredPosition=Phone?new Vector2(-8,-98):new Vector2(-16,-120);node.sizeDelta=Phone?new Vector2(330,82):new Vector2(360,96);
   goalCardEdge=node.gameObject.AddComponent<Image>();goalCardEdge.sprite=K.Rounded(16);goalCardEdge.type=Image.Type.Sliced;goalCardEdge.color=K.Border;
   Clickable(node.gameObject,GoalPressed);
   var face=N.Image(node,"Face",K.Cream,14);U.Stretch(face.rectTransform,Vector2.zero,Vector2.one,new Vector2(2,5),new Vector2(-2,-2));
   N.Row(face.gameObject,10,new RectOffset(10,12,6,6)).childAlignment=TextAnchor.MiddleLeft;
   goalCardIcon=N.Image(face.transform,"Icon",Color.white,0);goalCardIcon.preserveAspect=true;var il=goalCardIcon.gameObject.AddComponent<LayoutElement>();il.preferredWidth=il.preferredHeight=38;
   var texts=N.Node("Texts",face.transform);N.Column(texts.gameObject,2);texts.gameObject.AddComponent<LayoutElement>().flexibleWidth=1;
   var eyebrow=N.Text(texts,"Eyebrow",K.Label,11,K.C("C58A1E"));eyebrow.text="PRÓXIMO OBJETIVO";eyebrow.textWrappingMode=TextWrappingModes.NoWrap;
   goalCardText=N.Text(texts,"Text",K.Label,15,K.Ink);goalCardText.textWrappingMode=TextWrappingModes.NoWrap;goalCardText.overflowMode=TextOverflowModes.Ellipsis;
   goalCardDetail=N.Text(texts,"Detail",K.Body,12,K.Muted);goalCardDetail.textWrappingMode=TextWrappingModes.NoWrap;goalCardDetail.overflowMode=TextOverflowModes.Ellipsis;
   Bar(texts,6,K.C("F2B03D"),out goalCardFill);
   goalCard=node.gameObject;goalCard.SetActive(false);
  }
  // "@lots" shows the block from above (like the HUD's Press); anything else is a page route.
  void GoalPressed(){if(goalRoute=="@lots"){host.Route("");CheckoutLotView.Show();}else if(goalRoute.Length>0)host.Route("!"+goalRoute);}

  void ApplyCoach(DesktopView v){
   // Next objective card.
   var g=v.goal;bool showGoal=g!=null&&!string.IsNullOrEmpty(g.text)&&!v.hasPage;
   goalCard.SetActive(showGoal);
   if(showGoal){
    goalRoute=g.route??"";goalCardText.text=g.text;goalCardDetail.text=g.detail;var icon=K.Icon(g.icon);if(icon)goalCardIcon.sprite=icon;
    goalCardFill.parent.gameObject.SetActive(g.progress>=0);goalCardFill.anchorMax=new Vector2(Mathf.Clamp01(g.progress),1);
    goalCardEdge.color=g.progress>=1?K.C("5DA637"):K.Border;
   }
   coach=v.coach;
   // Prizes: celebrate each one once (the first view after loading only remembers the last one).
   string rewardKey=coach?.rewardKey??"";
   if(coachRewardSeen==null)coachRewardSeen=rewardKey;
   else if(rewardKey.Length>0&&rewardKey!=coachRewardSeen){coachRewardSeen=rewardKey;StartCoroutine(CoachRewardPop(coach.rewardText));}
   string key=coach?.key??"";
   if(key!=coachKey){coachKey=key;coachShownAt=Time.unscaledTime;coachMissingSince=-1;coachScrolledTarget=null;if(key.Length>0)PlayCoach("pop");}
   if(key.Length==0){HideCoach();return;}
   coachName.text=coach.speaker;coachTitle.text=coach.title;coachText.text=K.Clean(coach.text);
   var portrait=K.Icon("Game/"+coach.art);if(!portrait)portrait=K.Icon("Icons/customers");coachPortrait.sprite=coachCompactPortrait.sprite=portrait;
   coachStep.text=coach.isTip?"DICA":coach.total>0&&coach.mode!="modal"?$"{coach.step}/{coach.total}":"";
   bool hasButton=!string.IsNullOrEmpty(coach.button);
   coachButton.gameObject.SetActive(hasButton);
   if(hasButton)coachButton.Apply(new DesktopButton{label=coach.button,icon="",variant=coach.mode=="modal"?"success":"primary",enabled=true,action="",args="[]",route="",after="",ok="",fail=""});
   coachSkip.SetActive(coach.canSkip);
   coachButton.transform.parent.gameObject.SetActive(hasButton||coach.canSkip);
   BuildCoachPath(coach.path);
   coachCardWidth.preferredWidth=coach.mode=="modal"?680:540;
  }
  TextMeshProUGUI coachPathText;
  // The road ahead in one wrapped line: the first stage in green (you are here), the last in gold.
  void BuildCoachPath(string[] path){
   bool on=path!=null&&path.Length>0;coachPath.gameObject.SetActive(on);if(!on)return;
   var sb=new System.Text.StringBuilder();
   for(int i=0;i<path.Length;i++){
    if(i>0)sb.Append(" <color=#C58A1E>›</color> ");
    sb.Append(i==0?"<color=#427A24>"+path[i]+"</color>":i==path.Length-1?"<color=#B9740F>"+path[i]+"</color>":path[i]);
   }
   coachPathText.text=sb.ToString();
  }

  void CoachAction(string action){if(!string.IsNullOrEmpty(action)){PlayCoach("tap");host.Action(action,"[]","");}}
  void PlayCoach(string clip,float volume=1){var c=U.Sfx(clip);if(c)coachSound.PlayOneShot(c,volume);}

  // Null-safe: after a scene reload some coach pieces can be gone before the HUD rebuilds (it spammed NREs every frame).
  void HideCoach(){
   if(coachFull)coachFull.gameObject.SetActive(false);if(coachDims!=null)foreach(var d in coachDims)if(d)d.gameObject.SetActive(false);
   if(coachRing)coachRing.gameObject.SetActive(false);if(coachHand)coachHand.gameObject.SetActive(false);if(coachCard)coachCard.gameObject.SetActive(false);if(coachCompact)coachCompact.gameObject.SetActive(false);
  }

  // A game window covers the screen: the guide only leaves a note in the corner.
  static bool GameWindowOpen()=>
   (CheckoutCounterGame.Instance&&CheckoutCounterGame.Instance.IsOpen)||(CheckoutSupplierShop.Instance&&CheckoutSupplierShop.Instance.IsOpen)||
   (CheckoutRestockGame.Instance&&CheckoutRestockGame.Instance.IsOpen)||(CheckoutReceivingGame.Instance&&CheckoutReceivingGame.Instance.IsOpen)||
   (CheckoutStockroom.Instance&&CheckoutStockroom.Instance.IsOpen)||(CheckoutPackingGame.Instance&&CheckoutPackingGame.Instance.IsOpen)||
   (CheckoutIncidents.Instance&&CheckoutIncidents.Instance.IsOpen);

  float coachSearchAt;string coachSearchSpec,coachLayoutKey;bool coachFoundCache;Rect coachHoleCache;
  string coachCompactShown;float coachCompactAt;const float CompactReadSeconds=8;
  void UpdateCoach(){
   if(coachRoot==null)return;
   if(Input.GetMouseButton(0)||Input.touchCount>0||Input.mouseScrollDelta.sqrMagnitude>0)coachPointerAt=Time.unscaledTime;
   if(coachReward.gameObject.activeSelf)coachReward.SetAsLastSibling();
   if(coach==null||string.IsNullOrEmpty(coach.key)){HideCoach();return;}
   // Other moments come first: the level-up and conquest celebrations, the offline earnings, loading, building.
   // The Opções window (gear) too: the card sat over its Conta tab and the diamond store (QA 29/10).
   if(LevelUpOpen||ConquestOpen||modal.activeSelf||status.activeSelf||CheckoutBuildMode.Open||CheckoutLotView.Open||CheckoutSettings.Open){HideCoach();return;}
   // A game window, or a page window with nothing to point at: a note in the corner instead of a card over the window.
   bool game=GameWindowOpen();
   if(game||(view!=null&&view.hasPage&&coach.mode=="bubble"&&string.IsNullOrEmpty(coach.target))){
    HideCoach();var note=K.Clean(game&&!string.IsNullOrEmpty(coach.gameText)?coach.gameText:coach.text);
    if(note!=coachCompactShown||!coachCompact.gameObject.activeSelf){coachCompactShown=note;coachCompactAt=Time.unscaledTime;coachCompactText.text=note;}
    coachCompactText.gameObject.SetActive(Time.unscaledTime-coachCompactAt<CompactReadSeconds);
    coachCompact.gameObject.SetActive(true);return;
   }
   coachCompact.gameObject.SetActive(false);
   float pulse=Mathf.Sin(Time.unscaledTime*5f);
   bool modalMode=coach.mode=="modal";
   coachFull.gameObject.SetActive(modalMode);
   coachCard.gameObject.SetActive(true);
   var size=coachRoot.rect.size;
   if(modalMode){
    foreach(var d in coachDims)d.gameObject.SetActive(false);coachRing.gameObject.SetActive(false);coachHand.gameObject.SetActive(false);
    coachCard.anchoredPosition=new Vector2(size.x*.5f,size.y*.5f);
    coachCard.localScale=Vector3.one*Mathf.Min(1,.9f+(Time.unscaledTime-coachShownAt)*.5f);
    return;
   }
   coachCard.localScale=Vector3.one;
   // The target search walks the scene: ~6 times a second is enough (it ran every frame and cost the iPhone).
   if(Time.unscaledTime>=coachSearchAt||coach.target!=coachSearchSpec){
    coachSearchAt=Time.unscaledTime+.16f;coachSearchSpec=coach.target;coachFoundCache=FindCoachTarget(coach.target,out coachHoleCache);
   }
   bool found=coachFoundCache;var hole=coachHoleCache;
   // Wait a moment for a target that is still appearing (a page opening); after that never lock the screen.
   if(!found){if(coachMissingSince<0)coachMissingSince=Time.unscaledTime;}else coachMissingSince=-1;
   bool spotlight=coach.mode=="spotlight"&&found;
   bool waiting=!found&&!string.IsNullOrEmpty(coach.target)&&Time.unscaledTime-coachMissingSince<1.2f;
   // Dims around the hole.
   for(int i=0;i<4;i++)coachDims[i].gameObject.SetActive(spotlight&&!waiting);
   if(spotlight){
    var h=hole;h.xMin=Mathf.Max(0,h.xMin);h.yMin=Mathf.Max(0,h.yMin);h.xMax=Mathf.Min(size.x,h.xMax);h.yMax=Mathf.Min(size.y,h.yMax);
    const float b=DimBleed;
    CoachPlace(coachDims[0].rectTransform,-b,-b,size.x+2*b,h.yMin+b);
    CoachPlace(coachDims[1].rectTransform,-b,h.yMax,size.x+2*b,size.y-h.yMax+b);
    CoachPlace(coachDims[2].rectTransform,-b,h.yMin,h.xMin+b,h.height);
    CoachPlace(coachDims[3].rectTransform,h.xMax,h.yMin,size.x-h.xMax+b,h.height);
   }
   coachRing.gameObject.SetActive(found);coachHand.gameObject.SetActive(found);
   bool nearTop=found&&hole.center.y>size.y*.72f;
   if(found){
    coachRing.anchoredPosition=hole.center;float grow=10+pulse*5;coachRing.sizeDelta=hole.size+new Vector2(grow,grow)*2;
    coachFull.transform.SetAsFirstSibling();coachRing.SetAsLastSibling();
    // The fingertip taps the middle of the target (a small target: its centre); near the top edge the hand comes from
    // below so it stays on screen.
    coachHand.localRotation=Quaternion.Euler(0,0,nearTop?-20:160);
    var nudge=new Vector2(Mathf.Min(10,hole.width*.15f),Mathf.Min(10,hole.height*.15f)*(nearTop?1:-1));
    coachHand.anchoredPosition=hole.center+nudge*(1+Mathf.Max(0,pulse));
    coachHand.localScale=Vector3.one*(1-.08f*Mathf.Max(0,pulse));coachHand.SetAsLastSibling();
   }
   if(coachLayoutKey!=coach.key+coach.text){coachLayoutKey=coach.key+coach.text;LayoutRebuilder.ForceRebuildLayoutImmediate(coachCard);}
   coachCard.anchoredPosition=CoachCardSpot(size,coachCard.rect.size,found,hole,nearTop);coachCard.SetAsLastSibling();if(found)coachHand.SetAsLastSibling();
  }
  // Fingertip of Game/hand_pointer.png (the top of the index finger, measured on the art).
  static readonly Vector2 HandTip=new Vector2(.34f,.92f);
  // Where the card goes: next to the target, never over it or the hand, and off the open page window when it can
  // (it covered the Conta page and the diamond store, QA 29/10). Candidates around the hole, then free spots; the one
  // that covers the least of what matters wins.
  Vector2 CoachCardSpot(Vector2 size,Vector2 card,bool found,Rect hole,bool nearTop){
   Rect page=default;var open=OpenPage();bool hasPage=open&&CoachRectOf(PageFrame(open),out page);
   float left=hasPage?Mathf.Max(card.x*.5f+12,(page.xMin-12)*.5f):size.x*.5f; // the middle of the free side
   if(hasPage&&page.xMin<card.x+24)left=size.x*.5f;
   var spots=coachSpots;spots.Clear();
   const float gap=26;
   if(found){
    spots.Add(new Vector2(hole.center.x,hole.yMin-gap-card.y*.5f));
    spots.Add(new Vector2(hole.center.x,hole.yMax+gap+card.y*.5f));
    spots.Add(new Vector2(hole.xMin-gap-card.x*.5f,hole.center.y));
    spots.Add(new Vector2(hole.xMax+gap+card.x*.5f,hole.center.y));
   }
   spots.Add(new Vector2(left,size.y-130-card.y*.5f)); // under the top bar, clear of the windows' buttons
   spots.Add(new Vector2(left,size.y*.5f));
   spots.Add(new Vector2(left,card.y*.5f+110));         // above the toolbar
   // The hand: about 160 wide and 155 tall from the fingertip, above it (or below it near the top edge).
   var tip=coachHand.anchoredPosition;var hand=nearTop?Rect.MinMaxRect(tip.x-80,tip.y-135,tip.x+80,tip.y+25):Rect.MinMaxRect(tip.x-80,tip.y-25,tip.x+80,tip.y+135);
   Vector2 best=spots[0];float bestScore=float.MaxValue;
   foreach(var raw in spots){
    var at=new Vector2(Mathf.Clamp(raw.x,card.x*.5f+12,size.x-card.x*.5f-12),Mathf.Clamp(raw.y,card.y*.5f+12,size.y-card.y*.5f-12));
    var r=new Rect(at-card*.5f,card);
    float score=0;
    if(found){score+=1000*Overlap(r,CoachPad(hole,8));score+=400*Overlap(r,hand);score+=.02f*Vector2.Distance(at,hole.center);}
    // Off the page window, and above all off its header (title, tabs, X) when the window fills the screen.
    if(hasPage){score+=3*Overlap(r,page);score+=6*Overlap(r,Rect.MinMaxRect(page.xMin,page.yMax-110,page.xMax,page.yMax));}
    if(score<bestScore-.01f){bestScore=score;best=at;}
   }
   return best;
  }
  readonly List<Vector2> coachSpots=new List<Vector2>();static readonly Vector3[] coachCorners=new Vector3[4];
  static float Overlap(Rect a,Rect b){float w=Mathf.Min(a.xMax,b.xMax)-Mathf.Max(a.xMin,b.xMin),h=Mathf.Min(a.yMax,b.yMax)-Mathf.Max(a.yMin,b.yMin);return w>0&&h>0?w*h:0;}
  bool CoachRectOf(RectTransform r,out Rect local){
   local=default;if(!r)return false;var c=coachCorners;r.GetWorldCorners(c);
   var canvas=r.GetComponentInParent<Canvas>();var cam=canvas&&canvas.renderMode!=RenderMode.ScreenSpaceOverlay?canvas.worldCamera:null;
   Vector2 min=new Vector2(float.MaxValue,float.MaxValue),max=new Vector2(float.MinValue,float.MinValue);
   foreach(var w in c){var s=RectTransformUtility.WorldToScreenPoint(cam,w);min=Vector2.Min(min,s);max=Vector2.Max(max,s);}
   return ScreenRect(min,max,out local);
  }
  // Rounded outline, 9-sliced: a frame of any size around the target.
  static Sprite ringSprite;
  static Sprite RingSprite(){
   if(ringSprite)return ringSprite;const int n=64,r=22,stroke=7;var t=new Texture2D(n,n,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp};var px=new Color32[n*n];
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){
    float cx=Mathf.Clamp(x+.5f,r,n-r),cy=Mathf.Clamp(y+.5f,r,n-r);float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(cx,cy));
    float outer=Mathf.Clamp01(r-d+.5f),inner=Mathf.Clamp01(d-(r-stroke)+.5f);px[y*n+x]=new Color32(255,255,255,(byte)(outer*inner*255));
   }
   t.SetPixels32(px);t.Apply();return ringSprite=Sprite.Create(t,new Rect(0,0,n,n),new Vector2(.5f,.5f),100,0,SpriteMeshType.FullRect,new Vector4(r+1,r+1,r+1,r+1));
  }
  const float DimBleed=600;
  static void CoachPlace(RectTransform r,float x,float y,float w,float h){r.anchoredPosition=new Vector2(x,y);r.sizeDelta=new Vector2(Mathf.Max(0,w),Mathf.Max(0,h));}

  // ------------------------------------------------------------------ targets
  bool FindCoachTarget(string spec,out Rect hole){
   hole=default;coachTargetUi=null;coachTargetWorld=null;coachTargetPart="";coachUnderPage=false;if(string.IsNullOrEmpty(spec))return false;
   // The floating buttons pulse and move in their rail (REPOR / ENTREGA come and go above CAIXA): a wider frame keeps them inside.
   foreach(var raw in spec.Split('|')){
    var part=raw.Trim();coachScrollTarget=null;coachScrollAway=float.MaxValue;
    if(FindOne(part,out hole)){hole=CoachPad(hole,part.StartsWith("fab:")?18:10);coachTargetPart=part;return true;}
    // The button is there but scrolled out of its list (the results' COLETAR, a contract, a mission…): the guide scrolls
    // the list until it is wholly in view and then points at it. It never jumps to another target meanwhile (Lucas
    // 29/10: it fell back to the pressed "Resultado" button and the player was stuck).
    if(coachScrollTarget){coachTargetPart=part;CoachScrollTo(coachScrollRect,coachScrollTarget);return false;}
   }
   // The target is there but the page window covers it (the toolbar on an iPad, the top bar…): close the page first.
   if(coachUnderPage&&FindOne("close",out hole)){hole=CoachPad(hole,10);coachTargetPart="close";return true;}
   coachTargetUi=null;coachTargetWorld=null;
   return false;
  }
  static Rect CoachPad(Rect r,float p)=>new Rect(r.xMin-p,r.yMin-p,r.width+p*2,r.height+p*2);
  bool FindOne(string spec,out Rect hole){
   hole=default;
   if(spec=="market")return Visible(marketButton?(RectTransform)marketButton.transform:null,out hole);
   if(spec=="goal")return goalCard&&goalCard.activeInHierarchy&&Visible((RectTransform)goalCard.transform,out hole);
   if(spec=="help")return helpButton&&Visible(helpButton,out hole);
   // The gear (Opções): the tutorial's "Guarde o seu progresso" step points at it.
   if(spec=="settings")return settingsButton&&Visible(settingsButton,out hole);
   // The X of the page window ("feche a janela").
   if(spec=="close"){var x=PageClose();return x&&Visible(x,out hole);}
   if(spec.StartsWith("tool:")){var route=spec.Substring(5);foreach(var t in tools)if(t&&t.gameObject.activeInHierarchy&&t.Data!=null&&t.Data.route==route)return Visible((RectTransform)t.transform,out hole);return false;}
   if(spec.StartsWith("fab:")){
    string name=spec=="fab:caixa"?"CaixaButton":spec=="fab:repor"?"ReporButton":spec=="fab:entrega"?"EntregaButton":"";
    var go=name.Length>0?GameObject.Find(name):null;return go&&Visible(go.transform as RectTransform,out hole);
   }
   if(spec.StartsWith("action:")||spec.StartsWith("route:")){
    bool byAction=spec.StartsWith("action:");string want=spec.Substring(byAction?7:6);
    // Several buttons can match (three contracts, a "Pedir caixas" per product): the most visible one, then the
    // highest, so the hand does not jump between them.
    RectTransform pick=null;Rect pickHole=default;float pickScore=float.MinValue;
    foreach(var b in FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None)){
     if(!b.isActiveAndEnabled||b.Data==null||!b.Data.enabled)continue;
     bool match=byAction?b.Data.action==want:(b.Data.route??"").StartsWith(want);
     if(!match||!Visible((RectTransform)b.transform,out var h))continue;
     float score=Mathf.Round(h.width*h.height/400f)*10000+h.center.y;
     if(score>pickScore){pickScore=score;pick=(RectTransform)b.transform;pickHole=h;}
    }
    coachTargetUi=pick;hole=pickHole;return pick!=null;
   }
   if(spec.StartsWith("world:"))return WorldTarget(spec.Substring(6),out hole);
   return false;
  }
  // A UI element on screen, in the coach's coordinates (origin at the bottom left of the safe area).
  bool Visible(RectTransform target,out Rect hole){
   hole=default;coachTargetUi=target;if(!target||!target.gameObject.activeInHierarchy)return false;
   // In a scrolling list the button must be wholly in view; if it is not, the nearest one is remembered and the list is
   // scrolled to it (after one scroll, half in view is enough: a list may not go further).
   var scroll=target.GetComponentInParent<UnityEngine.UI.ScrollRect>();
   if(scroll&&scroll.content&&target.IsChildOf(scroll.content)&&target!=coachScrolledTarget){
    var vr=ScreenRectOf(scroll.viewport?scroll.viewport:(RectTransform)scroll.transform);var tr=ScreenRectOf(target);
    float away=Mathf.Max(0,vr.yMin-tr.yMin)+Mathf.Max(0,tr.yMax-vr.yMax)+Mathf.Max(0,vr.xMin-tr.xMin)+Mathf.Max(0,tr.xMax-vr.xMax);
    if(away>2){if(away<coachScrollAway){coachScrollAway=away;coachScrollRect=scroll;coachScrollTarget=target;}return false;}
   }
   var r=ScreenRectOf(target);
   // Inside a scrolling list only what the viewport shows counts: the part outside it is cut off, and a button mostly
   // scrolled away is not a target (the hole and the hand sat over the page header).
   var clip=target.GetComponentInParent<UnityEngine.UI.RectMask2D>();
   if(clip&&!Clip(ref r,ScreenRectOf(clip.rectTransform)))return false;
   var mask=target.GetComponentInParent<UnityEngine.UI.Mask>();
   if(mask&&!Clip(ref r,ScreenRectOf((RectTransform)mask.transform)))return false;
   if(!Clip(ref r,new Rect(0,0,Screen.width,Screen.height)))return false;
   var full=ScreenRectOf(target);if(r.width*r.height<full.width*full.height*.5f)return false;
   // A finger on it must reach it: another window, the page or a popup on top means it is not on screen now.
   if(!Reachable(target,r.center))return false;
   return ScreenRect(r.min,r.max,out hole);
  }
  static bool Clip(ref Rect r,Rect by){
   var x0=Mathf.Max(r.xMin,by.xMin);var y0=Mathf.Max(r.yMin,by.yMin);var x1=Mathf.Min(r.xMax,by.xMax);var y1=Mathf.Min(r.yMax,by.yMax);
   if(x1-x0<2||y1-y0<2)return false;r=Rect.MinMaxRect(x0,y0,x1,y1);return true;
  }
  // The page window on screen: the side drawer, or one of the full-screen windows (shelf, board, kitchen, shop).
  GameObject OpenPage(){
   if(drawer&&drawer.activeInHierarchy)return drawer;if(shelfWin&&shelfWin.activeInHierarchy)return shelfWin;if(boardWin&&boardWin.activeInHierarchy)return boardWin;
   if(kitchenWin&&kitchenWin.activeInHierarchy)return kitchenWin;if(shop&&shop.activeInHierarchy)return shop;return null;
  }
  // Its visible frame (the full-screen windows dim the whole screen around a "Window" panel).
  static RectTransform PageFrame(GameObject page){var w=page.transform.Find("Window");return (RectTransform)(w?w:page.transform);}
  // Its X: the window's own close button (label "X", no route).
  RectTransform PageClose(){
   var page=OpenPage();if(!page)return null;
   if(page==drawer)return closeButton&&closeButton.isActiveAndEnabled?(RectTransform)closeButton.transform:null;
   foreach(var b in page.GetComponentsInChildren<CheckoutDesktopButton>())if(b.isActiveAndEnabled&&b.Data!=null&&b.Data.label=="X"&&string.IsNullOrEmpty(b.Data.route))return (RectTransform)b.transform;
   return null;
  }
  // ---- auto-scroll: brings a target that sits further down (or across) a scrolling list into view.
  UnityEngine.UI.ScrollRect coachScrollRect;RectTransform coachScrollTarget,coachScrolledTarget;float coachScrollAway,coachScrollAt,coachPointerAt=-10;bool coachScrolling;int coachScrollCount;
  void CoachScrollTo(UnityEngine.UI.ScrollRect scroll,RectTransform target){
   // Not while the player is touching or has just scrolled the list: after a moment it comes back to the button.
   if(coachScrolling&&Time.unscaledTime-coachScrollAt>2)coachScrolling=false; // a scroll cut short (window closed mid-way)
   if(coachScrolling||!scroll||Time.unscaledTime-coachPointerAt<1.5f)return;
   coachScrollAt=Time.unscaledTime;
   StartCoroutine(CoachScrollRoutine(scroll,target));
  }
  IEnumerator CoachScrollRoutine(UnityEngine.UI.ScrollRect scroll,RectTransform target){
   coachScrolling=true;coachScrollCount++;
   scroll.StopMovement();Canvas.ForceUpdateCanvases();
   var view=scroll.viewport?scroll.viewport:(RectTransform)scroll.transform;var content=scroll.content;
   var b=RectTransformUtility.CalculateRelativeRectTransformBounds(view,target);var cb=RectTransformUtility.CalculateRelativeRectTransformBounds(view,content);var vr=view.rect;
   Vector2 d=Vector2.zero;
   if(scroll.vertical){
    float m=Mathf.Min(18,vr.height*.05f);
    if(b.max.y>vr.yMax-m||b.size.y>vr.height-2*m)d.y=vr.yMax-m-b.max.y;else if(b.min.y<vr.yMin+m)d.y=vr.yMin+m-b.min.y;
    float lo=vr.yMax-cb.max.y,hi=vr.yMin-cb.min.y;d.y=lo<=hi?Mathf.Clamp(d.y,lo,hi):0;
   }
   if(scroll.horizontal){
    float m=Mathf.Min(18,vr.width*.05f);
    if(b.min.x<vr.xMin+m||b.size.x>vr.width-2*m)d.x=vr.xMin+m-b.min.x;else if(b.max.x>vr.xMax-m)d.x=vr.xMax-m-b.max.x;
    float lo=vr.xMax-cb.max.x,hi=vr.xMin-cb.min.x;d.x=lo<=hi?Mathf.Clamp(d.x,lo,hi):0;
   }
   var parent=content.parent?content.parent:view;
   Vector2 step=parent.InverseTransformVector(view.TransformVector(d));var from=content.anchoredPosition;var to=from+step;
   for(float t=0;t<1&&scroll&&content;t+=Time.unscaledDeltaTime/.35f){
    if(Time.unscaledTime-coachPointerAt<.1f)break; // the player took the list: let go
    content.anchoredPosition=Vector2.Lerp(from,to,Mathf.SmoothStep(0,1,t));yield return null;
   }
   if(scroll&&content&&Time.unscaledTime-coachPointerAt>=.1f){content.anchoredPosition=to;scroll.StopMovement();}
   coachScrolledTarget=target;coachScrolling=false;coachSearchAt=0; // look again right away
  }
  bool coachUnderPage;readonly List<UnityEngine.EventSystems.RaycastResult> coachHits=new List<UnityEngine.EventSystems.RaycastResult>();
  // The first UI element under the point that is not the guide itself must belong to the target.
  bool Reachable(RectTransform target,Vector2 at){
   var es=UnityEngine.EventSystems.EventSystem.current;if(!es)return true;
   coachHits.Clear();es.RaycastAll(new UnityEngine.EventSystems.PointerEventData(es){position=at},coachHits);
   foreach(var hit in coachHits){
    var t=hit.gameObject?hit.gameObject.transform:null;if(!t||t.IsChildOf(coachRoot))continue;
    if(t.IsChildOf(target))return true;
    var page=OpenPage();if(page&&t.IsChildOf(page.transform)&&!target.IsChildOf(page.transform))coachUnderPage=true;
    return false;
   }
   return true;
  }
  // A clickable thing of the map (CheckoutTarget panel and optional shelf id), projected with the main camera.
  bool WorldTarget(string spec,out Rect hole){
   hole=default;var parts=spec.Split(':');string panel=parts[0],shelf=parts.Length>1?parts[1]:"";
   var cam=Camera.main;if(!cam)return false;
   foreach(var t in FindObjectsByType<CheckoutTarget>(FindObjectsSortMode.None)){
    if(!t.isActiveAndEnabled||t.panel!=panel||(shelf.Length>0&&t.shelfId!=shelf))continue;
    var col=t.GetComponent<Collider>();var b=col?col.bounds:new Bounds(t.transform.position,Vector3.one);
    Vector2 min=new Vector2(float.MaxValue,float.MaxValue),max=new Vector2(float.MinValue,float.MinValue);bool behind=false;
    for(int i=0;i<8;i++){
     var p=b.center+Vector3.Scale(b.extents,new Vector3((i&1)==0?-1:1,(i&2)==0?-1:1,(i&4)==0?-1:1));
     var s=cam.WorldToScreenPoint(p);if(s.z<0){behind=true;break;}min=Vector2.Min(min,s);max=Vector2.Max(max,s);
    }
    if(behind)continue;
    coachTargetWorld=t;coachTargetUi=null;coachWorldScreen=Rect.MinMaxRect(min.x,min.y,max.x,max.y);
    if(!ScreenRect(min,max,out hole)||hole.center.x<=0||hole.center.y<=0||hole.center.x>=coachRoot.rect.width||hole.center.y>=coachRoot.rect.height)continue;
    // A map tap under a button or a window never reaches the map (CheckoutPointer.OverUi).
    if(UiOver((min+max)*.5f))continue;
    return true;
   }
   return false;
  }
  bool UiOver(Vector2 at){
   var es=UnityEngine.EventSystems.EventSystem.current;if(!es)return false;
   coachHits.Clear();es.RaycastAll(new UnityEngine.EventSystems.PointerEventData(es){position=at},coachHits);
   foreach(var hit in coachHits)if(hit.gameObject&&!hit.gameObject.transform.IsChildOf(coachRoot))return true;
   return false;
  }
  bool ScreenRect(Vector2 min,Vector2 max,out Rect hole){
   hole=default;
   if(!RectTransformUtility.ScreenPointToLocalPointInRectangle(coachRoot,min,null,out var a))return false;
   if(!RectTransformUtility.ScreenPointToLocalPointInRectangle(coachRoot,max,null,out var b))return false;
   // Local points are around the pivot (center): move the origin to the bottom left.
   var offset=coachRoot.rect.size*coachRoot.pivot;a+=offset;b+=offset;
   hole=Rect.MinMaxRect(Mathf.Min(a.x,b.x),Mathf.Min(a.y,b.y),Mathf.Max(a.x,b.x),Mathf.Max(a.y,b.y));
   return hole.width>2&&hole.height>2;
  }

  // ------------------------------------------------------------------ QA (CheckoutAutoTest "onboarding")
  // What the guide shows right now, in screen pixels, so the test can tap where the hand points and check that the
  // hole, the hand and the card sit on the real button.
  RectTransform coachTargetUi;CheckoutTarget coachTargetWorld;string coachTargetPart="";Rect coachWorldScreen;
  public sealed class CoachQaInfo {
   public string key="",mode="",target="",part="",title="",text="",button="";public bool isTip,card,compact,found,dims,hand,page;
   public Rect hole,targetRect,cardRect,buttonRect,compactRect,drawerRect;public Vector2 tip;public int scrolls;public bool scrolling;
   public RectTransform targetUi,buttonUi;public CheckoutTarget targetWorld;
  }
  Vector2 CoachToScreen(Vector2 p)=>RectTransformUtility.WorldToScreenPoint(null,coachRoot.TransformPoint(p-coachRoot.rect.size*coachRoot.pivot));
  static Rect ScreenRectOf(RectTransform r){
   if(!r)return default;var c=coachCorners;r.GetWorldCorners(c);var canvas=r.GetComponentInParent<Canvas>();var cam=canvas&&canvas.renderMode!=RenderMode.ScreenSpaceOverlay?canvas.worldCamera:null;
   Vector2 min=new Vector2(float.MaxValue,float.MaxValue),max=new Vector2(float.MinValue,float.MinValue);
   foreach(var w in c){var s=RectTransformUtility.WorldToScreenPoint(cam,w);min=Vector2.Min(min,s);max=Vector2.Max(max,s);}
   return Rect.MinMaxRect(min.x,min.y,max.x,max.y);
  }
  public CoachQaInfo CoachQa(){
   var q=new CoachQaInfo();if(coachRoot==null)return q;
   q.page=view!=null&&view.hasPage;var open=OpenPage();q.drawerRect=open?ScreenRectOf(PageFrame(open)):default;
   if(coach==null||string.IsNullOrEmpty(coach.key))return q;
   q.scrolls=coachScrollCount;q.scrolling=coachScrolling;
   q.key=coach.key;q.mode=coach.mode;q.target=coach.target??"";q.title=coach.title;q.text=coach.text;q.button=coach.button??"";q.isTip=coach.isTip;
   q.card=coachCard.gameObject.activeInHierarchy;q.compact=coachCompact.gameObject.activeInHierarchy;
   q.dims=coachDims[0].gameObject.activeInHierarchy;q.hand=coachHand.gameObject.activeInHierarchy;q.found=q.hand&&coachFoundCache;
   if(q.card)q.cardRect=ScreenRectOf(coachCard);if(q.compact)q.compactRect=ScreenRectOf(coachCompact);
   if(q.card&&coachButton.gameObject.activeInHierarchy){q.buttonUi=(RectTransform)coachButton.transform;q.buttonRect=ScreenRectOf(q.buttonUi);}
   if(q.found){
    var a=CoachToScreen(coachHoleCache.min);var b=CoachToScreen(coachHoleCache.max);q.hole=Rect.MinMaxRect(a.x,a.y,b.x,b.y);
    q.tip=RectTransformUtility.WorldToScreenPoint(null,coachHand.position);q.part=coachTargetPart;
    q.targetUi=coachTargetUi;q.targetWorld=coachTargetWorld;q.targetRect=coachTargetUi?ScreenRectOf(coachTargetUi):coachTargetWorld?coachWorldScreen:default;
   }
   return q;
  }
  /// <summary>QA: closes a level-up or trophy celebration (they hide the guide).</summary>
  public void QaCloseCelebrations(){if(LevelUpOpen)CloseLevelUp("");if(ConquestOpen)CloseConquest("");}
  /// <summary>QA: the page window's close (X) button, when a page is open.</summary>
  public RectTransform QaPageClose=>PageClose();

  IEnumerator CoachRewardPop(string text){
   if(string.IsNullOrEmpty(text))yield break;
   coachRewardText.text=text;coachReward.gameObject.SetActive(true);coachReward.SetAsLastSibling();coachRewardGroup.alpha=1;coachReward.localScale=Vector3.zero;
   PlayCoach("success",.8f);PlayCoach("coin_1",.7f);
   yield return U.Scale(coachReward,Vector3.one,.35f,true);
   U.Sparkles(this,coachRoot,coachReward.anchoredPosition+new Vector2(0,coachRoot.rect.height*.22f),12,220);
   yield return new WaitForSecondsRealtime(2.2f);
   for(float t=1;t>0;t-=Time.unscaledDeltaTime/.4f){coachRewardGroup.alpha=t;yield return null;}
   coachReward.gameObject.SetActive(false);
  }
 }
}
