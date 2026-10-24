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
 // The hand-made production games (page.layout == "kitchen", data from desktop/pages/kitchen.ts): the recipe
 // is cooked step by step on the sector's work bench, one gesture per step, like the real process — drag the
 // ingredients into the bowl in the baker's order, knead until the dough is smooth, wait for it to double and
 // tap at the right time, shape it, score it along the guides, take it out of the oven when it is golden.
 // Each step scores 0–1; the average gives 1–3 stars and the result card sends cookByHand (3 stars = +1 unit).
 public partial class CheckoutDesktopHUD {
  public static bool KitchenOpen;
  GameObject kitchenWin;Image kitchenHeader,kitchenIcon,kitchenBench;RectTransform kitchenStage,kitchenChips,kitchenBar,kitchenCard;
  TextMeshProUGUI kitchenTitle,kitchenSubtitle,kitchenStepTitle,kitchenHint;Image kitchenMeterFill;
  DesktopKitchen kitchen;string kitchenShown;Coroutine kitchenRun;
  readonly List<GameObject> kitchenScene=new List<GameObject>();
  readonly List<KitchenChip> kitchenChipsUi=new List<KitchenChip>();
  readonly List<float> kitchenScores=new List<float>();
  KitchenPad kitchenPad;

  // ------------------------------------------------------------------ build
  void BuildKitchen(){
   var node=N.Node("Kitchen window",root);kitchenWin=node.gameObject;Stretch(node,Vector2.zero,Vector2.zero);
   var dim=kitchenWin.AddComponent<Image>();dim.color=new Color(.10f,.07f,.04f,.7f);
   var window=Stretch(N.Node("Window",node),CheckoutScreen.Handheld?new Vector2(8,8):new Vector2(40,40),CheckoutScreen.Handheld?new Vector2(-8,-6):new Vector2(-40,-16));
   var edge=window.gameObject.AddComponent<Image>();edge.sprite=K.Rounded(30);edge.type=Image.Type.Sliced;edge.color=K.C("8A5A2B");
   var face=N.Image(window,"Face",K.Paper,28);Stretch(face.rectTransform,new Vector2(4,9),new Vector2(-4,-4));

   // Header: product, title, the steps as chips, close.
   kitchenHeader=N.Image(face.transform,"Header",K.C("B7682B"),26);var hr=kitchenHeader.rectTransform;hr.anchorMin=new Vector2(0,1);hr.anchorMax=Vector2.one;hr.pivot=new Vector2(.5f,1);hr.offsetMin=new Vector2(0,-96);hr.offsetMax=Vector2.zero;
   var shine=N.Image(kitchenHeader.transform,"Shine",new Color(1,1,1,.12f),24);var shr=shine.rectTransform;shr.anchorMin=new Vector2(0,.55f);shr.anchorMax=Vector2.one;shr.offsetMin=new Vector2(6,0);shr.offsetMax=new Vector2(-6,-4);
   var iconBack=N.Image(kitchenHeader.transform,"IconBack",new Color(1,1,1,.95f),20);Place(iconBack.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(18,-2),new Vector2(68,68));
   kitchenIcon=N.Image(iconBack.transform,"Icon",Color.white,0);kitchenIcon.preserveAspect=true;Stretch(kitchenIcon.rectTransform,new Vector2(6,6),new Vector2(-6,-6));
   kitchenTitle=N.Text(kitchenHeader.transform,"Title",K.Headline,32,Color.white);kitchenTitle.textWrappingMode=TextWrappingModes.NoWrap;Place(kitchenTitle.rectTransform,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(100,-10),new Vector2(520,42));
   kitchenSubtitle=N.Text(kitchenHeader.transform,"Subtitle",K.Body,15,new Color(1,1,1,.9f));kitchenSubtitle.textWrappingMode=TextWrappingModes.NoWrap;Place(kitchenSubtitle.rectTransform,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(100,-52),new Vector2(520,22));
   kitchenChips=N.Node("Steps",kitchenHeader.transform);Place(kitchenChips,new Vector2(0,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-90,-2),new Vector2(-720,62));
   var row=N.Row(kitchenChips.gameObject,8);row.childAlignment=TextAnchor.MiddleRight;row.childControlHeight=true;row.childForceExpandHeight=true;
   var close=CheckoutDesktopButton.Create(kitchenHeader.transform,54,22,14);close.SetWidth(58);close.Clicked=_=>host.Route("back");
   Destroy(close.GetComponent<LayoutElement>());Place((RectTransform)close.transform,new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(1,.5f),new Vector2(-16,-2),new Vector2(58,54));
   close.Apply(new DesktopButton{label="X",variant="danger",enabled=true,route="",action="",args="[]",after="",ok="",fail="",badge=""});

   // Stage: the bench, everything happens on it.
   var frame=N.Image(face.transform,"StageFrame",K.C("D4B482"),22);Stretch(frame.rectTransform,new Vector2(16,150),new Vector2(-16,-106));
   var mask=N.Image(frame.transform,"StageMask",Color.white,20);Stretch(mask.rectTransform,new Vector2(5,5),new Vector2(-5,-5));mask.gameObject.AddComponent<Mask>().showMaskGraphic=true;
   kitchenBench=N.Image(mask.transform,"Bench",Color.white,0);Stretch(kitchenBench.rectTransform,Vector2.zero,Vector2.zero);
   var vig=N.Image(mask.transform,"Vignette",Color.white,0);vig.sprite=U.Vignette();Stretch(vig.rectTransform,Vector2.zero,Vector2.zero);
   var pad=N.Image(mask.transform,"Pad",new Color(1,1,1,0),0);pad.raycastTarget=true;Stretch(pad.rectTransform,Vector2.zero,Vector2.zero);kitchenPad=pad.gameObject.AddComponent<KitchenPad>();
   kitchenStage=N.Node("Stage",mask.transform);Stretch(kitchenStage,Vector2.zero,Vector2.zero);kitchenPad.Space=kitchenStage;

   // Bottom bar: the step, how to do it, how far along it is.
   var bar=N.Image(face.transform,"Bar",K.Cream,20);kitchenBar=bar.rectTransform;kitchenBar.anchorMin=Vector2.zero;kitchenBar.anchorMax=new Vector2(1,0);kitchenBar.pivot=new Vector2(.5f,0);kitchenBar.offsetMin=new Vector2(16,14);kitchenBar.offsetMax=new Vector2(-16,140);
   var barEdge=N.Image(bar.transform,"Edge",K.Border,20);Stretch(barEdge.rectTransform,new Vector2(0,-4),Vector2.zero);barEdge.transform.SetAsFirstSibling();
   var clerk=N.Image(bar.transform,"Clerk",Color.white,0);clerk.sprite=K.Icon("Icons/manager");clerk.preserveAspect=true;Place(clerk.rectTransform,new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(0,.5f),new Vector2(14,0),new Vector2(78,78));
   kitchenStepTitle=N.Text(bar.transform,"Step",K.Headline,26,K.Ink);kitchenStepTitle.textWrappingMode=TextWrappingModes.NoWrap;Place(kitchenStepTitle.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(104,-12),new Vector2(-130,34));
   kitchenHint=N.Text(bar.transform,"Hint",K.Body,17,K.Muted);kitchenHint.textWrappingMode=TextWrappingModes.Normal;Place(kitchenHint.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(0,1),new Vector2(104,-48),new Vector2(-130,48));
   var track=N.Image(bar.transform,"Track",K.C("EADBC4"),9);Place(track.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(0,0),new Vector2(104,14),new Vector2(-130,18));
   kitchenMeterFill=N.Image(track.transform,"Fill",K.C("5DA637"),9);var mf=kitchenMeterFill.rectTransform;mf.anchorMin=Vector2.zero;mf.anchorMax=new Vector2(0,1);mf.offsetMin=mf.offsetMax=Vector2.zero;

   kitchenCard=N.Node("Card layer",face.transform);Stretch(kitchenCard,Vector2.zero,Vector2.zero);
   kitchenWin.SetActive(false);
  }

  // ------------------------------------------------------------------ apply
  void ApplyKitchen(DesktopView v){
   bool on=v.hasPage&&v.page!=null&&v.page.layout=="kitchen"&&v.page.kitchen!=null&&v.page.kitchen.steps!=null&&v.page.kitchen.steps.Length>0;
   if(kitchenWin.activeSelf!=on)kitchenWin.SetActive(on);KitchenOpen=on;
   if(!on){if(kitchenShown!=null)StopKitchen();kitchenShown=null;return;}
   ShopOpen=true;
   var k=v.page.kitchen;
   // The same recipe keeps playing while the view refreshes; only its "can cook" may change.
   string key=v.page.route;
   if(kitchenShown==key){kitchen.canCook=k.canCook;kitchen.reason=k.reason;return;}
   StopKitchen();kitchenShown=key;kitchen=k;
   kitchenHeader.color=K.C(string.IsNullOrEmpty(k.tint)?"B7682B":k.tint);
   kitchenIcon.sprite=K.Icon(k.icon);kitchenTitle.text=K.Clean(k.title);kitchenSubtitle.text=$"{K.Clean(v.page.subtitle)} · feito à mão · rende {k.output}";
   // The puzzle benches made in Blender (Game/pz_bench_<sector>) win over the old ones.
   kitchenBench.sprite=K.Icon("Game/pz_bench_"+k.sectorId)??K.Icon(k.bench);kitchenBench.color=kitchenBench.sprite?Color.white:K.C("C9A277");
   while(kitchenChipsUi.Count<k.steps.Length)kitchenChipsUi.Add(KitchenChip.Create(kitchenChips));
   for(int i=0;i<kitchenChipsUi.Count;i++){bool show=i<k.steps.Length;kitchenChipsUi[i].gameObject.SetActive(show);if(show)kitchenChipsUi[i].Apply(i+1,"todo",0);}
   StartCoroutine(U.Pop(kitchenWin.transform.Find("Window"),1.02f,.22f));
   kitchenRun=StartCoroutine(KitchenFlow());
  }
  void StopKitchen(){
   if(kitchenRun!=null)StopCoroutine(kitchenRun);kitchenRun=null;
   ClearKitchenScene();foreach(Transform c in kitchenCard)Destroy(c.gameObject);kitchenScores.Clear();
  }
  void ClearKitchenScene(){foreach(var o in kitchenScene)if(o)Destroy(o);kitchenScene.Clear();kitchenPad.Clear();}
  T KKeep<T>(T c) where T:Component{kitchenScene.Add(c.gameObject);return c;}
  void KitchenBar(string title,string hint,float progress,string tone="success"){
   kitchenStepTitle.text=K.Clean(title);kitchenHint.text=K.Clean(hint);KitchenMeter(progress,tone);
  }
  void KitchenMeter(float progress,string tone="success"){
   kitchenMeterFill.rectTransform.anchorMax=new Vector2(Mathf.Clamp01(progress),1);kitchenMeterFill.color=ToneStrong(tone);
  }

  // ------------------------------------------------------------------ flow
  IEnumerator KitchenFlow(){
   // QA ("kitchen:<recipe>:<step>"): straight to one step.
   if(kitchen.demo>=0&&kitchen.demo<kitchen.steps.Length){
    var d=kitchen.steps[kitchen.demo];kitchenChipsUi[kitchen.demo].Apply(kitchen.demo+1,"now",0);KitchenBar(d.title,d.hint,.35f);
    yield return RunStep(d,kitchen.demo);yield break;
   }
   // Intro card: what is going to be made and the steps.
   bool go=false;
   var card=KitchenCardBox(620,480);
   var icon=N.Image(card,"Icon",Color.white,0);icon.sprite=K.Icon(kitchen.icon);icon.preserveAspect=true;Place(icon.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-20),new Vector2(130,130));
   var t=N.Text(card,"Title",K.Headline,30,K.Ink);t.alignment=TextAlignmentOptions.Center;t.text="Vamos fazer: "+K.Clean(kitchen.title);Place(t.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-156),new Vector2(-40,40));
   var s=N.Text(card,"Sub",K.Body,17,K.Muted);s.alignment=TextAlignmentOptions.Center;
   s.text=kitchen.canCook?$"Rende {kitchen.output}. Faça 3 estrelas e ganhe +1 de brinde!":K.Clean(kitchen.reason);s.color=kitchen.canCook?K.Muted:ToneStrong("danger");
   Place(s.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-198),new Vector2(-40,26));
   var list=N.Text(card,"Steps",K.Body,17,K.Ink);list.alignment=TextAlignmentOptions.TopLeft;
   var lines=new List<string>();for(int i=0;i<kitchen.steps.Length;i++)lines.Add($"<b>{i+1}.</b> {K.Clean(kitchen.steps[i].title)}");
   list.text=string.Join("\n",lines);Place(list.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-236),new Vector2(-160,170));
   var start=U.Button(card,kitchen.canCook?"Começar!":"Voltar",kitchen.canCook?"success":"secondary",()=>{if(kitchen.canCook)go=true;else host.Route("back");},64,24);
   Destroy(start.GetComponent<LayoutElement>());Place((RectTransform)start.transform,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(0,24),new Vector2(300,64));
   KitchenBar("Feito à mão","Cada passo é um gesto, como na cozinha de verdade. Capriche: quanto melhor, mais estrelas.",0);
   while(!go)yield return null;
   Sound("pop");yield return U.Scale(card.parent,Vector3.zero,.2f);Destroy(card.parent.parent.gameObject);
   // The steps.
   for(int i=0;i<kitchen.steps.Length;i++){
    var step=kitchen.steps[i];kitchenChipsUi[i].Apply(i+1,"now",0);
    yield return KitchenBanner($"Passo {i+1} de {kitchen.steps.Length}",step.title);
    kitchenScore=1;KitchenBar(step.title,step.hint,0);
    yield return RunStep(step,i);
    kitchenScore=Mathf.Clamp01(kitchenScore);kitchenScores.Add(kitchenScore);
    kitchenChipsUi[i].Apply(i+1,"done",kitchenScore);
    yield return KitchenBanner(kitchenScore>=.85f?"Perfeito!":kitchenScore>=.6f?"Muito bom!":"Deu certo!",step.done,true);
    ClearKitchenScene();
   }
   yield return KitchenResult();
  }
  float kitchenScore;

  IEnumerator KitchenBanner(string top,string text,bool good=false){
   if(string.IsNullOrEmpty(text)&&!good)yield break;
   var b=KKeep(N.Image(kitchenStage,"Banner",new Color(.17f,.12f,.08f,.86f),24));Place(b.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(0,40),new Vector2(640,130));
   var a=N.Text(b.transform,"Top",K.Label,18,good?K.C("F2B03D"):new Color(1,1,1,.75f));a.alignment=TextAlignmentOptions.Center;a.text=K.Clean(top).ToUpperInvariant();a.characterSpacing=3;Place(a.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-16),new Vector2(0,26));
   var c=N.Text(b.transform,"Text",K.Headline,34,Color.white);c.alignment=TextAlignmentOptions.Center;c.text=K.Clean(text);c.enableAutoSizing=true;c.fontSizeMin=20;c.fontSizeMax=34;Place(c.rectTransform,new Vector2(0,0),new Vector2(1,1),new Vector2(.5f,.5f),new Vector2(0,-14),new Vector2(-30,-50));
   b.transform.localScale=Vector3.zero;Sound(good?"success":"whoosh");
   if(good)U.Sparkles(this,kitchenStage,b.rectTransform.anchoredPosition,12,260);
   yield return U.Scale(b.transform,Vector3.one,.25f,true);
   yield return new WaitForSecondsRealtime(good?.9f:.8f);
   yield return U.Scale(b.transform,Vector3.zero,.18f);
   if(b)Destroy(b.gameObject);
  }

  IEnumerator KitchenResult(){
   float avg=0;foreach(var x in kitchenScores)avg+=x;avg/=Mathf.Max(1,kitchenScores.Count);
   int stars=avg>=.85f?3:avg>=.6f?2:1;
   var card=KitchenCardBox(620,460);
   var glow=N.Image(card,"Glow",new Color(1,.9f,.5f,.8f),0);glow.sprite=U.Glow();Place(glow.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,-100),new Vector2(300,240));
   var icon=N.Image(card,"Icon",Color.white,0);icon.sprite=K.Icon(kitchen.icon);icon.preserveAspect=true;Place(icon.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,-100),new Vector2(150,150));
   var pips=new List<Image>();
   for(int i=0;i<3;i++){var p=N.Image(card,"Star",K.C("D9CBB4"),8);p.rectTransform.localRotation=Quaternion.Euler(0,0,45);Place(p.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2((i-1)*78,-214),new Vector2(50,50));pips.Add(p);}
   var title=N.Text(card,"Title",K.Headline,32,K.Ink);title.alignment=TextAlignmentOptions.Center;title.text=stars==3?"Perfeito!":stars==2?"Muito bom!":"Feito!";Place(title.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-252),new Vector2(-40,40));
   var sub=N.Text(card,"Sub",K.Body,18,K.Muted);sub.alignment=TextAlignmentOptions.Center;
   sub.text=$"+{kitchen.output} {K.Clean(kitchen.title)}"+(stars==3?"  ·  <color=#4F9A2E><b>+1 de brinde!</b></color>":"");Place(sub.rectTransform,new Vector2(0,1),new Vector2(1,1),new Vector2(.5f,1),new Vector2(0,-294),new Vector2(-40,28));
   bool sent=false;
   var keep=U.Button(card,"Guardar no estoque","success",()=>{
    if(sent)return;sent=true;
    var args="[{\"recipeId\":\""+kitchen.recipeId+"\",\"sectorId\":\""+kitchen.sectorId+"\",\"stars\":"+stars+"}]";
    var data=new DesktopButton{label="",variant="success",enabled=true,action="cookByHand",args=args,route="",after="back",ok=$"{K.Clean(kitchen.title)} no estoque!",fail=string.IsNullOrEmpty(kitchen.reason)?"Faltaram ingredientes ou espaço no estoque.":kitchen.reason,badge=""};
    pending[host.Action(data.action,data.args,data.after)]=data;
   },64,24);
   Destroy(keep.GetComponent<LayoutElement>());Place((RectTransform)keep.transform,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(0,26),new Vector2(340,64));
   KitchenBar("Pronto!","Guarde no estoque: o produto vai direto para o balcão do setor.",1);
   for(int i=0;i<3;i++){
    yield return new WaitForSecondsRealtime(.35f);
    if(i<stars){pips[i].color=K.C("F2B03D");Sound("coin_"+i);U.Sparkles(this,(RectTransform)card,pips[i].rectTransform.anchoredPosition+new Vector2(0,((RectTransform)card).rect.height/2),8,120);StartCoroutine(U.Pop(pips[i].transform,1.5f,.3f));}
   }
   if(stars==3)Sound("success");
  }

  RectTransform KitchenCardBox(float w,float h){
   var shade=N.Image(kitchenCard,"Shade",new Color(.1f,.06f,.03f,.45f),0);shade.raycastTarget=true;Stretch(shade.rectTransform,Vector2.zero,Vector2.zero);
   var edge=N.Image(shade.transform,"Edge",K.C("8A5A2B"),26);Place(edge.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(0,30),new Vector2(w,h));
   var face=N.Image(edge.transform,"Face",K.Cream,24);Stretch(face.rectTransform,new Vector2(4,8),new Vector2(-4,-4));
   edge.transform.localScale=Vector3.zero;StartCoroutine(U.Scale(edge.transform,Vector3.one,.28f,true));
   return face.rectTransform;
  }

  // ------------------------------------------------------------------ steps
  // The thing being made: an image on the bench (and the state it turns into on top of it).
  Image kTarget,kNext,kBack;RectTransform kTargetRect;Vector2 kTargetSize;
  void KitchenTarget(DesktopKitchenStep s){
   var center=new Vector2(0,30);
   if(!string.IsNullOrEmpty(s.back)){
    var bs=K.Icon(s.back);kBack=KKeep(N.Image(kitchenStage,"Back",Color.white,0));kBack.sprite=bs;kBack.preserveAspect=true;
    float bh=kitchenStage.rect.height*.86f;Place(kBack.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),center,new Vector2(bh*(bs?bs.rect.width/bs.rect.height:1.3f),bh));
    var at=s.at!=null&&s.at.Length>=2?new Vector2(s.at[0],s.at[1]):new Vector2(.5f,.5f);
    center+=new Vector2((at.x-.5f)*kBack.rectTransform.sizeDelta.x,(at.y-.5f)*bh);
   }
   var sprite=K.Icon(s.art);var shadow=KKeep(N.Image(kitchenStage,"Shadow",new Color(.2f,.1f,.04f,.3f),0));shadow.sprite=U.Glow();
   kTarget=KKeep(N.Image(kitchenStage,"Target",Color.white,0));kTarget.sprite=sprite;kTarget.preserveAspect=true;kTargetRect=kTarget.rectTransform;
   float size=Mathf.Max(80,s.size);float aspect=sprite?sprite.rect.width/sprite.rect.height:1;
   kTargetSize=aspect>=1?new Vector2(size,size/aspect):new Vector2(size*aspect,size);
   Place(kTargetRect,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),center,kTargetSize);
   Place(shadow.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),center-new Vector2(0,kTargetSize.y*.42f),new Vector2(kTargetSize.x*1.05f,kTargetSize.y*.35f));
   shadow.gameObject.SetActive(string.IsNullOrEmpty(s.back));
   kNext=N.Image(kTargetRect,"Next",new Color(1,1,1,0),0);kNext.preserveAspect=true;Stretch(kNext.rectTransform,Vector2.zero,Vector2.zero);
   kNext.sprite=s.states!=null&&s.states.Length>0?K.Icon(s.states[s.states.Length-1]):null;kNext.enabled=kNext.sprite;
  }
  Vector2 KPoint(float nx,float ny)=>kTargetRect.anchoredPosition+new Vector2((nx-.5f)*kTargetSize.x,(ny-.5f)*kTargetSize.y);
  bool KOver(Vector2 p,float margin=40){var c=kTargetRect.anchoredPosition;return Mathf.Abs(p.x-c.x)<kTargetSize.x/2+margin&&Mathf.Abs(p.y-c.y)<kTargetSize.y/2+margin;}
  void KMorph(float t){if(kNext&&kNext.enabled)kNext.color=new Color(1,1,1,Mathf.Clamp01(t));}
  void KFinish(DesktopKitchenStep s){if(kNext&&kNext.enabled){kTarget.sprite=kNext.sprite;kNext.color=new Color(1,1,1,0);}}

  IEnumerator RunStep(DesktopKitchenStep s,int index){
   // Puzzle steps draw their own board (CheckoutDesktopHUD.KitchenPuzzle.cs).
   IEnumerator puzzle=s.kind=="tray"?StepTray(s):s.kind=="aging"?StepAging(s):s.kind=="portions"?StepPortions(s):s.kind=="orders"?StepOrders(s)
    :s.kind=="sort"?StepSort(s):s.kind=="scoops"?StepScoops(s):s.kind=="decant"?StepDecant(s):null;
   if(puzzle!=null){yield return puzzle;KitchenMeter(1);yield break;}
   KitchenTarget(s);
   kTarget.transform.localScale=Vector3.zero;yield return U.Scale(kTarget.transform,Vector3.one,.25f,true);
   switch(s.kind){
    case "add":yield return StepAdd(s);break;
    case "rub":yield return StepRub(s);break;
    case "heat":yield return StepHeat(s);break;
    case "stop":yield return StepStop(s);break;
    case "cut":yield return StepCut(s);break;
    case "tap":yield return StepTap(s,false);break;
    case "place":yield return StepTap(s,true);break;
    case "swipe":yield return StepSwipe(s);break;
    default:yield return new WaitForSecondsRealtime(.5f);break;
   }
   KFinish(s);KitchenMeter(1);
   yield return U.Pop(kTarget.transform,1.08f,.25f);
  }

  // Drag the items onto the bowl, in order.
  IEnumerator StepAdd(DesktopKitchenStep s){
   var items=s.items??new DesktopKitchenItem[0];int added=0,next=0,mistakes=0;
   var drop=KKeep(N.Image(kitchenStage,"Drop",new Color(1,1,1,0),0)).rectTransform;Place(drop,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),kTargetRect.anchoredPosition,kTargetSize+new Vector2(120,120));
   float w=kitchenStage.rect.width;float gap=Mathf.Min(190,(w-120)/Mathf.Max(1,items.Length));
   var tokens=new List<RectTransform>();
   for(int i=0;i<items.Length;i++){
    int index=i;var it=items[i];
    var tok=KKeep(N.Image(kitchenStage,"Item",new Color(1,1,1,.001f),0));var tr=tok.rectTransform;
    var home=new Vector2((i-(items.Length-1)/2f)*gap,-kitchenStage.rect.height/2+86);
    Place(tr,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),home,new Vector2(120,120));
    var plate=N.Image(tr,"Plate",new Color(1,1,1,.85f),60);Stretch(plate.rectTransform,new Vector2(8,8),new Vector2(-8,-8));
    var ic=N.Image(tr,"Icon",Color.white,0);ic.sprite=K.Icon(it.icon);ic.preserveAspect=true;Stretch(ic.rectTransform,new Vector2(14,14),new Vector2(-14,-14));
    var lab=N.Text(tr,"Label",K.Label,14,K.Ink);lab.alignment=TextAlignmentOptions.Center;lab.text=K.Clean(it.label);lab.textWrappingMode=TextWrappingModes.NoWrap;lab.outlineWidth=.2f;lab.outlineColor=new Color32(255,255,255,220);
    Place(lab.rectTransform,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(.5f,1),new Vector2(0,2),new Vector2(170,22));
    var num=N.Image(tr,"Num",K.C("8A5A2B"),12);Place(num.rectTransform,new Vector2(0,1),new Vector2(0,1),new Vector2(.5f,.5f),new Vector2(14,-14),new Vector2(28,28));
    var nt=N.Text(num.transform,"N",K.Number,15,Color.white);nt.alignment=TextAlignmentOptions.Center;nt.text=(i+1).ToString();Stretch(nt.rectTransform,Vector2.zero,Vector2.zero);
    var drag=U.Drag(tok);drag.SetHome(home);
    drag.Setup(new[]{drop},_=>{
     if(index!=next){mistakes++;Sound("bonk");Toast($"Primeiro: {K.Clean(items[next].label)}",false);return false;}
     next++;added++;drag.Locked=true;Sound("pop");StartCoroutine(KDropIn(tr));
     KMorph((float)added/items.Length);KitchenMeter((float)added/items.Length);
     StartCoroutine(U.Pop(kTarget.transform,1.06f,.2f));return true;
    },null,()=>kitchenPad.Interacted=true);
    tokens.Add(tr);
   }
   var hint=KHint(()=>tokens.Count>next?tokens[next].anchoredPosition:Vector2.zero,()=>kTargetRect.anchoredPosition);
   while(added<items.Length){if(kitchenPad.Interacted&&hint)Destroy(hint);yield return null;}
   if(hint)Destroy(hint);
   kitchenScore=Mathf.Max(.4f,1-.2f*mistakes);
  }
  IEnumerator KDropIn(RectTransform tr){
   yield return U.Move(tr,kTargetRect.anchoredPosition+new Vector2(0,20),.18f);
   yield return U.Scale(tr,Vector3.zero,.15f);if(tr)tr.gameObject.SetActive(false);
   U.Sparkles(this,kitchenStage,kTargetRect.anchoredPosition,6,120);
  }

  // Rub back and forth over it (knead, stir, beat).
  IEnumerator StepRub(DesktopKitchenStep s){
   float need=Mathf.Max(1,s.count)*kTargetSize.x*.7f,done=0,fast=0,soundAt=0;
   var tool=KTool(s.tool);
   var hint=KHint(()=>kTargetRect.anchoredPosition-new Vector2(kTargetSize.x*.3f,0),()=>kTargetRect.anchoredPosition+new Vector2(kTargetSize.x*.3f,0));
   while(done<need){
    var pad=kitchenPad;
    if(pad.Down&&KOver(pad.Position)){
     if(hint)Destroy(hint);
     float moved=pad.Delta.magnitude;float speed=moved/Mathf.Max(.001f,Time.unscaledDeltaTime);
     if(s.slow>0&&speed>s.slow){fast+=Time.unscaledDeltaTime;done=Mathf.Max(0,done-moved*.5f);if(Time.unscaledTime-warnAt>1.2f){warnAt=Time.unscaledTime;Toast("Devagar! Assim quebra.",false);}}
     else done+=moved;
     if(done-soundAt>kTargetSize.x*.5f){soundAt=done;Sound("scrub_"+Random.Range(0,3),Random.Range(.9f,1.1f));}
     float wob=Mathf.Clamp(pad.Delta.x*.004f,-.08f,.08f);
     kTargetRect.localScale=new Vector3(1+Mathf.Abs(wob),1-Mathf.Abs(wob)*.6f,1);kTargetRect.localRotation=Quaternion.Euler(0,0,-wob*40);
    } else {kTargetRect.localScale=Vector3.Lerp(kTargetRect.localScale,Vector3.one,Time.unscaledDeltaTime*10);kTargetRect.localRotation=Quaternion.Lerp(kTargetRect.localRotation,Quaternion.identity,Time.unscaledDeltaTime*10);}
    if(tool){tool.gameObject.SetActive(pad.Down);tool.anchoredPosition=pad.Position+new Vector2(20,30);}
    KMorph(done/need);KitchenMeter(done/need);
    pad.Delta=Vector2.zero;
    yield return null;
   }
   kTargetRect.localScale=Vector3.one;kTargetRect.localRotation=Quaternion.identity;
   kitchenScore=1-Mathf.Min(.6f,fast*.25f);
  }
  float warnAt;

  // A gauge beside it (temperature, browning, rising) with its good zone.
  Image kGaugeFill,kGaugeZone;RectTransform kGauge,kNeedle;TextMeshProUGUI kGaugeValue;
  void KGauge(DesktopKitchenStep s){
   var at=kTargetRect.anchoredPosition+new Vector2((kBack?kBack.rectTransform.sizeDelta.x/2:kTargetSize.x/2)+90,0);
   var g=KKeep(N.Image(kitchenStage,"Gauge",K.C("FFF8E8"),18));kGauge=g.rectTransform;Place(kGauge,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),at,new Vector2(86,340));
   var e=N.Image(g.transform,"Edge",K.Border,18);Stretch(e.rectTransform,new Vector2(-4,-4),new Vector2(4,4));e.transform.SetAsFirstSibling();
   var track=N.Image(g.transform,"Track",K.C("EADBC4"),12);Place(track.rectTransform,new Vector2(.5f,0),new Vector2(.5f,1),new Vector2(.5f,.5f),new Vector2(0,6),new Vector2(30,-80));
   float lo=s.zone!=null&&s.zone.Length>1?s.zone[0]:.7f,hi=s.zone!=null&&s.zone.Length>1?s.zone[1]:.85f;
   kGaugeZone=N.Image(track.transform,"Zone",new Color(.36f,.72f,.25f,.75f),6);var zr=kGaugeZone.rectTransform;zr.anchorMin=new Vector2(-.25f,lo);zr.anchorMax=new Vector2(1.25f,hi);zr.offsetMin=zr.offsetMax=Vector2.zero;
   kGaugeFill=N.Image(track.transform,"Fill",K.C("E8962B"),12);var fr=kGaugeFill.rectTransform;fr.anchorMin=Vector2.zero;fr.anchorMax=new Vector2(1,0);fr.offsetMin=new Vector2(6,0);fr.offsetMax=new Vector2(-6,0);
   var nd=N.Image(track.transform,"Needle",K.Ink,3);kNeedle=nd.rectTransform;kNeedle.anchorMin=new Vector2(-.4f,0);kNeedle.anchorMax=new Vector2(1.4f,0);kNeedle.sizeDelta=new Vector2(0,5);
   kGaugeValue=N.Text(g.transform,"Value",K.Number,18,K.Ink);kGaugeValue.alignment=TextAlignmentOptions.Center;kGaugeValue.textWrappingMode=TextWrappingModes.NoWrap;Place(kGaugeValue.rectTransform,new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(.5f,0),new Vector2(0,12),new Vector2(110,26));
   var top=N.Text(g.transform,"Unit",K.Label,13,K.Muted);top.alignment=TextAlignmentOptions.Center;top.text=K.Clean(s.unit).ToUpperInvariant();Place(top.rectTransform,new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(.5f,1),new Vector2(0,-8),new Vector2(90,20));
  }
  void KGaugeSet(DesktopKitchenStep s,float v){
   v=Mathf.Clamp01(v);kGaugeFill.rectTransform.anchorMax=new Vector2(1,v);kNeedle.anchoredPosition=new Vector2(0,0);kNeedle.anchorMin=new Vector2(-.4f,v);kNeedle.anchorMax=new Vector2(1.4f,v);
   float from=s.scale!=null&&s.scale.Length>1?s.scale[0]:0,to=s.scale!=null&&s.scale.Length>1?s.scale[1]:100;float value=Mathf.Lerp(from,to,v);
   kGaugeValue.text=(Mathf.Abs(to-from)<5?value.ToString("0.0"):Mathf.RoundToInt(value).ToString())+(string.IsNullOrEmpty(s.unit)||s.unit=="x"?"":" "+s.unit)+(s.unit=="x"?"x":"");
   float lo=s.zone[0],hi=s.zone[1];bool inZone=v>=lo&&v<=hi;
   kGaugeFill.color=inZone?ToneStrong("success"):v>hi?ToneStrong("danger"):ToneStrong("warning");
   kGaugeZone.color=new Color(.36f,.72f,.25f,inZone?.55f+.3f*Mathf.Sin(Time.unscaledTime*8):.6f);
  }
  RectTransform KBigButton(string label,string variant,System.Action onClick,out CheckoutDesktopButton b){
   b=U.Button(kitchenStage,label,variant,onClick,72,26);Destroy(b.GetComponent<LayoutElement>());var r=(RectTransform)b.transform;
   Place(r,new Vector2(1,0),new Vector2(1,0),new Vector2(1,0),new Vector2(-30,26),new Vector2(300,72));kitchenScene.Add(b.gameObject);return r;
  }

  // Hold to heat, let go to cool: keep it in the zone for a while (pasteurize the milk, temper the chocolate).
  IEnumerator StepHeat(DesktopKitchenStep s){
   KGauge(s);float v=0,inZone=0,over=0,need=Mathf.Max(1,s.seconds);bool holding=false;
   var holdBtn=KKeep(N.Image(kitchenStage,"Hold",ToneStrong("danger"),36));var hr=holdBtn.rectTransform;Place(hr,new Vector2(1,0),new Vector2(1,0),new Vector2(1,0),new Vector2(-30,26),new Vector2(300,72));
   var hl=N.Text(hr,"Label",K.Headline,22,Color.white);hl.alignment=TextAlignmentOptions.Center;hl.text="SEGURE P/ AQUECER";Stretch(hl.rectTransform,Vector2.zero,Vector2.zero);
   var hold=holdBtn.gameObject.AddComponent<KitchenHold>();holdBtn.raycastTarget=true;
   var steam=new List<Image>();
   while(inZone<need){
    holding=hold.Held||(kitchenPad.Down&&KOver(kitchenPad.Position,80));
    v+=(holding?.22f:-.1f)*Time.unscaledDeltaTime;v=Mathf.Clamp01(v);
    float lo=s.zone[0],hi=s.zone[1];
    if(v>=lo&&v<=hi)inZone+=Time.unscaledDeltaTime;
    if(v>hi+.06f){over+=Time.unscaledDeltaTime;if(Time.unscaledTime-warnAt>1.5f){warnAt=Time.unscaledTime;Toast("Quente demais! Solte um pouco.",false);}}
    KGaugeSet(s,v);KMorph(inZone/need);KitchenMeter(inZone/need,"info");
    holdBtn.color=holding?Color.Lerp(ToneStrong("danger"),Color.white,.15f):ToneStrong("danger");hr.localScale=Vector3.one*(holding?.96f:1);
    kTarget.color=Color.Lerp(Color.white,K.C("FFD9B0"),v*.6f);
    if(v>lo*.8f&&Random.value<Time.unscaledDeltaTime*6)StartCoroutine(KSteam());
    yield return null;
   }
   kTarget.color=Color.white;kitchenScore=Mathf.Clamp(1-over*.25f,.3f,1);
  }
  IEnumerator KSteam(){
   var p=KKeep(N.Image(kitchenStage,"Steam",new Color(1,1,1,.5f),0));p.sprite=U.Glow();var r=p.rectTransform;
   var start=kTargetRect.anchoredPosition+new Vector2(Random.Range(-.3f,.3f)*kTargetSize.x,kTargetSize.y*.3f);Place(r,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),start,new Vector2(40,40));
   for(float t=0;t<1&&p;t+=Time.unscaledDeltaTime/1.4f){r.anchoredPosition=start+new Vector2(Mathf.Sin(t*6)*10,t*120);r.localScale=Vector3.one*(1+t*1.5f);p.color=new Color(1,1,1,.45f*(1-t));yield return null;}
   if(p)Destroy(p.gameObject);
  }

  // The gauge runs on its own; tap at the right moment (dough doubled, bread golden, milk cooled to 38 °C).
  IEnumerator StepStop(DesktopKitchenStep s){
   KGauge(s);float v=0,dur=Mathf.Max(2,s.seconds);bool stop=false;
   string label=s.gauge=="oven"?"TIRAR DO FORNO":s.gauge=="grow"?"PRONTO!":"AGORA!";
   KBigButton(label,"success",()=>stop=true,out var btn);
   if(s.gauge=="oven"){Sound("whoosh");}
   while(!stop&&v<1){
    v+=Time.unscaledDeltaTime/dur;KGaugeSet(s,v);
    float lo=s.zone[0],hi=s.zone[1];
    if(s.gauge=="grow"){float g=1+v*.55f;kTargetRect.localScale=new Vector3(g,g,1);KMorph(v/hi);}
    else if(s.gauge=="oven"){KMorph(Mathf.SmoothStep(0,1,v/hi));kTarget.color=v>hi?Color.Lerp(Color.white,K.C("5A3A22"),(v-hi)/(1-hi)):Color.white;kNext.color=new Color(kTarget.color.r,kTarget.color.g,kTarget.color.b,kNext.color.a);
     if(Random.value<Time.unscaledDeltaTime*2.5f)StartCoroutine(KSteam());}
    else KMorph(v);
    KitchenMeter(v,v>=lo&&v<=hi?"success":v>hi?"danger":"warning");
    yield return null;
   }
   float lo2=s.zone[0],hi2=s.zone[1];float mid=(lo2+hi2)/2,half=(hi2-lo2)/2;
   if(!stop){kitchenScore=.25f;Toast("Passou do ponto!",false);}
   else if(v>=lo2&&v<=hi2)kitchenScore=1-.15f*Mathf.Abs(v-mid)/Mathf.Max(.001f,half);
   else{kitchenScore=Mathf.Clamp(1-(Mathf.Abs(v-mid)-half)*3.5f,.25f,.8f);Toast(v<lo2?"Cedo demais!":"Passou um pouco!",false);}
   Sound(kitchenScore>.8f?"success":"pop");
   if(s.gauge=="grow")StartCoroutine(U.Scale(kTargetRect,Vector3.one,.3f));
  }

  // Cut along each guide (score the bread, cut the curd, trim the meat, fillet the fish).
  IEnumerator StepCut(DesktopKitchenStep s){
   var l=s.lines??new float[0];int count=l.Length/4;var cut=new bool[count];var guides=new List<GameObject>();float total=0;int made=0;
   for(int i=0;i<count;i++){guides.Add(KDashed(KPoint(l[i*4],l[i*4+1]),KPoint(l[i*4+2],l[i*4+3])));}
   var tool=KTool(string.IsNullOrEmpty(s.tool)?"Game/kt_blade":s.tool);
   var trail=KKeep(N.Image(kitchenStage,"Trail",new Color(.25f,.15f,.08f,.7f),2));trail.gameObject.SetActive(false);
   var hint=count>0?KHint(()=>KPoint(l[0],l[1]),()=>KPoint(l[2],l[3])):null;
   var pts=new List<Vector2>();bool was=false;
   while(made<count){
    var pad=kitchenPad;
    if(pad.Down){
     if(hint)Destroy(hint);
     if(!was){pts.Clear();}
     pts.Add(pad.Position);
     KLine(trail.rectTransform,pts[0],pad.Position,5);trail.gameObject.SetActive(true);
    } else if(was&&pts.Count>1){
     trail.gameObject.SetActive(false);
     var a=pts[0];var b=pts[pts.Count-1];int best=-1;float bestErr=float.MaxValue;
     for(int i=0;i<count;i++){if(cut[i])continue;var p=KPoint(l[i*4],l[i*4+1]);var q=KPoint(l[i*4+2],l[i*4+3]);
      float e=Mathf.Min(Vector2.Distance(a,p)+Vector2.Distance(b,q),Vector2.Distance(a,q)+Vector2.Distance(b,p));if(e<bestErr){bestErr=e;best=i;}}
     if(best>=0){
      var p=KPoint(l[best*4],l[best*4+1]);var q=KPoint(l[best*4+2],l[best*4+3]);float len=Vector2.Distance(p,q);
      if(bestErr<Mathf.Max(70,len*.6f)){
       float dev=0;foreach(var x in pts)dev+=KDistance(x,p,q);dev/=pts.Count;
       float acc=Mathf.Clamp01(1-dev/40f-Mathf.Max(0,bestErr-30)/200f);total+=Mathf.Max(.35f,acc);made++;cut[best]=true;
       Destroy(guides[best]);var c=KKeep(N.Image(kitchenStage,"Cut",new Color(.3f,.18f,.08f,.85f),2));KLine(c.rectTransform,p,q,6);
       Sound("whoosh",1.2f);U.Sparkles(this,kitchenStage,(p+q)/2,5,90);KMorph((float)made/count);KitchenMeter((float)made/count);
      } else {Sound("bonk");Toast("Siga a guia de ponta a ponta.",false);}
     }
    }
    if(tool){tool.gameObject.SetActive(pad.Down);tool.anchoredPosition=pad.Position+new Vector2(30,20);}
    was=pad.Down;
    yield return null;
   }
   kitchenScore=total/Mathf.Max(1,count);
  }
  static float KDistance(Vector2 x,Vector2 a,Vector2 b){var ab=b-a;float t=Mathf.Clamp01(Vector2.Dot(x-a,ab)/Mathf.Max(.001f,ab.sqrMagnitude));return Vector2.Distance(x,a+ab*t);}
  static void KLine(RectTransform r,Vector2 a,Vector2 b,float width){
   r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);r.pivot=new Vector2(0,.5f);r.anchoredPosition=a;r.sizeDelta=new Vector2(Vector2.Distance(a,b),width);
   r.localRotation=Quaternion.Euler(0,0,Mathf.Atan2(b.y-a.y,b.x-a.x)*Mathf.Rad2Deg);
  }
  GameObject KDashed(Vector2 a,Vector2 b){
   var root=KKeep(N.Node("Guide",kitchenStage));Stretch(root,Vector2.zero,Vector2.zero);
   float len=Vector2.Distance(a,b);int n=Mathf.Max(3,Mathf.RoundToInt(len/22));
   for(int i=0;i<n;i++){float t0=(float)i/n,t1=t0+.55f/n;var d=N.Image(root,"Dash",new Color(1,1,1,.95f),2);KLine(d.rectTransform,Vector2.Lerp(a,b,t0),Vector2.Lerp(a,b,t1),5);
    d.rectTransform.anchorMin=d.rectTransform.anchorMax=new Vector2(.5f,.5f);}
   var dot=N.Image(root,"Start",ToneStrong("gold"),12);Place(dot.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),a,new Vector2(20,20));
   return root.gameObject;
  }

  // Tap every spot (decorate, flip, pull the bones) — or drag a piece onto every spot (molds, tray, ice).
  IEnumerator StepTap(DesktopKitchenStep s,bool place){
   var sp=s.spots??new float[0];int count=sp.Length/2;var spots=new List<Image>();var taken=new bool[count];int done=0,miss=0;
   for(int i=0;i<count;i++){var g=KKeep(N.Image(kitchenStage,"Spot",new Color(1,.85f,.3f,.8f),0));g.sprite=U.Glow();Place(g.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),KPoint(sp[i*2],sp[i*2+1]),new Vector2(70,70));
    var ring=N.Image(g.transform,"Ring",new Color(1,1,1,.9f),20);Place(ring.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),Vector2.zero,new Vector2(34,34));spots.Add(g);}
   RectTransform supply=null;Sprite piece=place&&s.items!=null&&s.items.Length>0?K.Icon(s.items[0].icon):null;
   if(place){
    var tok=KKeep(N.Image(kitchenStage,"Supply",Color.white,0));tok.sprite=piece;tok.preserveAspect=true;supply=tok.rectTransform;
    var home=new Vector2(-kitchenStage.rect.width/2+120,-kitchenStage.rect.height/2+100);Place(supply,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),home,new Vector2(110,110));
    var drag=U.Drag(tok);drag.SetHome(home);
    var zone=KKeep(N.Image(kitchenStage,"Zone",new Color(1,1,1,0),0)).rectTransform;Place(zone,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),kTargetRect.anchoredPosition,kTargetSize+new Vector2(80,80));
    drag.Setup(new[]{zone},_=>{
     var at=supply.anchoredPosition;int best=-1;float bd=80;
     for(int i=0;i<count;i++){if(taken[i])continue;float d=Vector2.Distance(at,spots[i].rectTransform.anchoredPosition);if(d<bd){bd=d;best=i;}}
     if(best<0){miss++;Sound("bonk");return false;}
     taken[best]=true;done++;var put=KKeep(N.Image(kitchenStage,"Piece",Color.white,0));put.sprite=piece;put.preserveAspect=true;
     Place(put.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),spots[best].rectTransform.anchoredPosition,new Vector2(96,96));StartCoroutine(U.Pop(put.transform,1.2f,.2f));
     spots[best].gameObject.SetActive(false);Sound("pop");KMorph((float)done/count);KitchenMeter((float)done/count);
     supply.anchoredPosition=home;return true;
    },()=>{miss++;},()=>kitchenPad.Interacted=true);
   }
   var hint=count>0?(place?KHint(()=>supply.anchoredPosition,()=>spots[System.Array.IndexOf(taken,false)<0?0:System.Array.IndexOf(taken,false)].rectTransform.anchoredPosition):KHint(()=>spots[0].rectTransform.anchoredPosition,()=>spots[0].rectTransform.anchoredPosition,true)):null;
   bool was=false;
   while(done<count){
    float t=Time.unscaledTime;for(int i=0;i<count;i++)if(!taken[i])spots[i].rectTransform.localScale=Vector3.one*(1+.12f*Mathf.Sin(t*5+i));
    var pad=kitchenPad;
    if(!place&&pad.Down&&!was){
     if(hint)Destroy(hint);
     int best=-1;float bd=48;for(int i=0;i<count;i++){if(taken[i])continue;float d=Vector2.Distance(pad.Position,spots[i].rectTransform.anchoredPosition);if(d<bd){bd=d;best=i;}}
     if(best>=0){taken[best]=true;done++;spots[best].gameObject.SetActive(false);Sound("pop",1+done*.04f);U.Sparkles(this,kitchenStage,pad.Position,5,80);KMorph((float)done/count);KitchenMeter((float)done/count);}
     else if(KOver(pad.Position,0)){miss++;}
    }
    if(place&&kitchenPad.Interacted&&hint)Destroy(hint);
    was=pad.Down;yield return null;
   }
   if(hint)Destroy(hint);
   kitchenScore=Mathf.Max(.4f,1-.08f*miss);
  }

  // Strokes in one direction (shape the loaf, scale the fish from tail to head, fold the dough).
  IEnumerator StepSwipe(DesktopKitchenStep s){
   int need=Mathf.Max(1,s.count),done=0,wrong=0;bool was=false;Vector2 start=Vector2.zero;
   var dir=s.dir<0?Vector2.right:new Vector2(Mathf.Cos(s.dir*Mathf.Deg2Rad),Mathf.Sin(s.dir*Mathf.Deg2Rad));
   var hint=KHint(()=>kTargetRect.anchoredPosition-dir*kTargetSize.x*.3f,()=>kTargetRect.anchoredPosition+dir*kTargetSize.x*.3f);
   while(done<need){
    var pad=kitchenPad;
    if(pad.Down&&!was){start=pad.Position;}
    if(!pad.Down&&was){
     var d=pad.Position-start;float len=d.magnitude;
     if(len>Mathf.Min(kTargetSize.x,kTargetSize.y)*.35f&&KOver(start,60)){
      if(hint)Destroy(hint);
      bool ok=s.dir<0?Mathf.Abs(d.x)>Mathf.Abs(d.y)*1.3f:Vector2.Dot(d.normalized,dir)>.7f;
      if(ok){done++;Sound("sweep_"+Random.Range(0,3));KMorph((float)done/need);KitchenMeter((float)done/need);
       StartCoroutine(KStretch(s.dir<0||Mathf.Abs(dir.x)>Mathf.Abs(dir.y)));for(int i=0;i<3;i++)StartCoroutine(KFlake(start+d*Random.value,d.normalized));}
      else{wrong++;Sound("bonk");Toast(s.dir<0?"Arraste para os lados.":"Na outra direção!",false);StartCoroutine(U.Shake(kTargetRect,.2f,8));}
     }
    }
    was=pad.Down;yield return null;
   }
   kitchenScore=Mathf.Max(.4f,1-.1f*wrong);
  }
  IEnumerator KStretch(bool horizontal){
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.3f){float k=Mathf.Sin(t*Mathf.PI)*.1f;kTargetRect.localScale=horizontal?new Vector3(1+k,1-k*.6f,1):new Vector3(1-k*.6f,1+k,1);yield return null;}
   kTargetRect.localScale=Vector3.one;
  }
  IEnumerator KFlake(Vector2 at,Vector2 dir){
   var f=KKeep(N.Image(kitchenStage,"Flake",new Color(1,.97f,.9f,.9f),4));var r=f.rectTransform;Place(r,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),at,new Vector2(10,8));
   var v=dir*Random.Range(120,260)+new Vector2(Random.Range(-60,60),Random.Range(40,160));
   for(float t=0;t<1&&f;t+=Time.unscaledDeltaTime/.6f){r.anchoredPosition+=v*Time.unscaledDeltaTime;v+=Vector2.down*500*Time.unscaledDeltaTime;r.localRotation=Quaternion.Euler(0,0,t*400);f.color=new Color(1,.97f,.9f,.9f*(1-t));yield return null;}
   if(f)Destroy(f.gameObject);
  }

  RectTransform KTool(string sprite){
   if(string.IsNullOrEmpty(sprite))return null;var s=K.Icon(sprite);if(!s)return null;
   var t=KKeep(N.Image(kitchenStage,"Tool",Color.white,0));t.sprite=s;t.preserveAspect=true;var r=t.rectTransform;
   Place(r,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.2f,.2f),Vector2.zero,new Vector2(150,150));t.gameObject.SetActive(false);return r;
  }
  GameObject KHint(System.Func<Vector2> from,System.Func<Vector2> to,bool tap=false){
   var h=U.Hint(this,kitchenStage,from,to,tap);kitchenScene.Add(h);kitchenPad.Interacted=false;return h;
  }

  // ------------------------------------------------------------------ pieces
  // Pointer over the bench, in stage coordinates.
  class KitchenPad:MonoBehaviour,IPointerDownHandler,IPointerUpHandler,IDragHandler {
   public RectTransform Space;public bool Down,Interacted;public Vector2 Position,Delta;
   public void Clear(){Down=false;Delta=Vector2.zero;}
   Vector2 Local(PointerEventData e){RectTransformUtility.ScreenPointToLocalPointInRectangle(Space,e.position,e.pressEventCamera,out var p);return p-Space.rect.center;}
   public void OnPointerDown(PointerEventData e){Down=true;Interacted=true;Position=Local(e);Delta=Vector2.zero;}
   public void OnPointerUp(PointerEventData e){Down=false;Position=Local(e);}
   public void OnDrag(PointerEventData e){var p=Local(e);Delta+=p-Position;Position=p;}
  }
  class KitchenHold:MonoBehaviour,IPointerDownHandler,IPointerUpHandler,IPointerExitHandler {
   public bool Held;
   public void OnPointerDown(PointerEventData e){Held=true;}
   public void OnPointerUp(PointerEventData e){Held=false;}
   public void OnPointerExit(PointerEventData e){Held=false;}
  }
  // A step in the header: number, then a tick and the colour of how it went.
  class KitchenChip:MonoBehaviour {
   Image back;TextMeshProUGUI label;
   public static KitchenChip Create(Transform parent){
    var root=N.Node("Chip",parent);var c=root.gameObject.AddComponent<KitchenChip>();
    c.back=root.gameObject.AddComponent<Image>();c.back.sprite=K.Rounded(18);c.back.type=Image.Type.Sliced;
    var le=root.gameObject.AddComponent<LayoutElement>();le.preferredWidth=le.minWidth=52;le.preferredHeight=52;
    c.label=N.Text(root,"Label",K.Number,20,Color.white);c.label.alignment=TextAlignmentOptions.Center;Stretch(c.label.rectTransform,Vector2.zero,Vector2.zero);
    return c;
   }
   public void Apply(int number,string state,float score){
    label.text=number.ToString();
    back.color=state=="now"?K.C("F2B03D"):state=="done"?(score>=.85f?ToneStrong("success"):score>=.6f?ToneStrong("info"):ToneStrong("warning")):new Color(0,0,0,.25f);
    transform.localScale=Vector3.one*(state=="now"?1.12f:1);
   }
  }
 }
}
