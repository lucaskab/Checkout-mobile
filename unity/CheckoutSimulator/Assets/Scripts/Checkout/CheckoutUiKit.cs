using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Text.RegularExpressions;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;

namespace Checkout {
 // Shared building blocks for the simulator mini-games (register, store mishaps): a full-screen
 // canvas, cream windows, simple shapes, tweens and drag tokens. Works with mouse and touch.
 public static class CheckoutUiKit {
  public static RectTransform Canvas(Transform parent,string name,int order){
   var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);
   var canvas=go.AddComponent<UnityEngine.Canvas>();canvas.renderMode=RenderMode.ScreenSpaceOverlay;canvas.sortingOrder=order;
   var scaler=go.AddComponent<CanvasScaler>();scaler.uiScaleMode=CanvasScaler.ScaleMode.ScaleWithScreenSize;scaler.referenceResolution=new Vector2(1600,1000);scaler.matchWidthOrHeight=.5f;
   go.AddComponent<GraphicRaycaster>();
   if(!UnityEngine.Object.FindAnyObjectByType<EventSystem>()){var events=new GameObject("EventSystem");events.AddComponent<EventSystem>();events.AddComponent<StandaloneInputModule>();}
   return (RectTransform)go.transform;
  }
  public static RectTransform Stretch(RectTransform rect,Vector2 min,Vector2 max,Vector2 offMin=default,Vector2 offMax=default){rect.anchorMin=min;rect.anchorMax=max;rect.offsetMin=offMin;rect.offsetMax=offMax;return rect;}
  // A node anchored at a point with a fixed size (pixels in the 1600x1000 reference).
  public static RectTransform At(RectTransform rect,Vector2 anchor,Vector2 size,Vector2 offset=default){rect.anchorMin=rect.anchorMax=anchor;rect.pivot=new Vector2(.5f,.5f);rect.sizeDelta=size;rect.anchoredPosition=offset;return rect;}
  public static Image Box(Transform parent,string name,string color,int radius,Vector2 min,Vector2 max){var image=N.Image(parent,name,K.C(color),radius);Stretch(image.rectTransform,min,max);return image;}
  public static Image Shape(Transform parent,string name,string color,int radius,Vector2 anchor,Vector2 size,Vector2 offset=default){var image=N.Image(parent,name,K.C(color),radius);At(image.rectTransform,anchor,size,offset);return image;}
  public static Image Icon(Transform parent,string name,string path,Vector2 anchor,Vector2 size,Vector2 offset=default){var image=N.Image(parent,name,Color.white,0);image.sprite=K.Icon(path);image.preserveAspect=true;At(image.rectTransform,anchor,size,offset);return image;}
  public static TextMeshProUGUI Label(Transform parent,string name,TMP_FontAsset font,float size,string color,TextAlignmentOptions align=TextAlignmentOptions.Center){var t=N.Text(parent,name,font,size,K.C(color));t.alignment=align;t.textWrappingMode=TextWrappingModes.NoWrap;t.overflowMode=TextOverflowModes.Ellipsis;return t;}
  public static CheckoutDesktopButton Button(Transform parent,string label,string variant,Action onClick,float height=56,float font=20){
   var b=CheckoutDesktopButton.Create(parent,height,font,14);b.Apply(new DesktopButton{label=label,variant=variant,enabled=true,icon="",action="",args="[]",route="",after="",ok="",fail=""});b.Clicked=_=>onClick();return b;
  }
  // Cream window with a darker edge filling most of the screen; returns the face.
  public static RectTransform Window(RectTransform root,out GameObject dim){
   var back=Box(root,"Dim","000000",0,Vector2.zero,Vector2.one);back.color=new Color(.14f,.09f,.05f,.62f);back.raycastTarget=true;dim=back.gameObject;
   var edge=Box(back.transform,"Edge","D4B482",26,new Vector2(.05f,.07f),new Vector2(.95f,.93f));
   var face=Box(edge.transform,"Face","FFF7EC",24,Vector2.zero,Vector2.one);face.rectTransform.offsetMin=new Vector2(3,8);face.rectTransform.offsetMax=new Vector2(-3,-3);
   return face.rectTransform;
  }

  // ------------------------------------------------------------------ rendered art (Resources/CheckoutDesktop/Game)
  // Blender renders from scripts/blender/build_ui_sprites.py. Art() keeps the sprite's aspect so the
  // normalized marks exported with it (screens, slots, sockets) line up with Over().
  public static Sprite ArtSprite(string name)=>K.Icon("Game/"+name);
  public static float Aspect(string name){var s=ArtSprite(name);return s?s.rect.width/Mathf.Max(1,s.rect.height):1;}
  public static Image Art(Transform parent,string name,string sprite,Vector2 anchor,float height,Vector2 offset=default){
   var img=N.Image(parent,name,Color.white,0);img.sprite=ArtSprite(sprite);img.type=Image.Type.Simple;img.preserveAspect=false;img.raycastTarget=false;
   At(img.rectTransform,anchor,new Vector2(height*Aspect(sprite),height),offset);return img;
  }
  public static void SetArt(Image img,string sprite){if(img)img.sprite=ArtSprite(sprite);}
  // Full-bleed backdrop that covers its parent without stretching.
  public static Image Backdrop(Transform parent,string sprite){
   var img=N.Image(parent,"Backdrop",Color.white,0);img.sprite=ArtSprite(sprite);img.raycastTarget=false;
   Stretch(img.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f));
   var fit=img.gameObject.AddComponent<AspectRatioFitter>();fit.aspectMode=AspectRatioFitter.AspectMode.EnvelopeParent;fit.aspectRatio=Aspect(sprite);
   return img;
  }
  static readonly Dictionary<string,Dictionary<string,Rect>> marks=new Dictionary<string,Dictionary<string,Rect>>();
  public static Rect Mark(string sprite,string label){
   if(!marks.TryGetValue(sprite,out var table)){
    table=new Dictionary<string,Rect>();var asset=Resources.Load<TextAsset>("CheckoutDesktop/Game/"+sprite+"_marks");
    if(asset)foreach(Match m in Regex.Matches(asset.text,"\"(\\w+)\":\\s*\\[([^\\]]+)\\]")){
     var v=m.Groups[2].Value.Split(',');if(v.Length<4)continue;float F(int i)=>float.Parse(v[i].Trim(),CultureInfo.InvariantCulture);
     table[m.Groups[1].Value]=Rect.MinMaxRect(F(0),F(1),F(2),F(3));
    }
    marks[sprite]=table;
   }
   return table.TryGetValue(label,out var r)?r:new Rect(0,0,1,1);
  }
  // A node covering a marked part of an Art() image (e.g. the POS screen), for live content on top.
  public static RectTransform Over(Image art,string sprite,string label,string name=null){
   var node=N.Node(name??label,art.transform);var r=Mark(sprite,label);node.anchorMin=r.min;node.anchorMax=r.max;node.offsetMin=node.offsetMax=Vector2.zero;node.pivot=new Vector2(.5f,.5f);return node;
  }
  // Center of a marked part in the coordinates of another rect (for tweening things onto it).
  public static Vector2 PointIn(RectTransform space,RectTransform target){return (Vector2)space.InverseTransformPoint(target.TransformPoint(target.rect.center));}
  // Anchored position (for a child anchored at .5,.5 of space) that puts it over target.
  public static Vector2 LocalOf(RectTransform space,RectTransform target){var p=PointIn(space,target);return p-space.rect.center;}

  // Taps: enables raycasts on the graphic (decor images are non-raycast by default) and adds a button.
  public static UnityEngine.UI.Button Tap(Graphic g,Action onTap){
   g.raycastTarget=true;var b=g.GetComponent<UnityEngine.UI.Button>();if(!b)b=g.gameObject.AddComponent<UnityEngine.UI.Button>();
   b.transition=Selectable.Transition.None;b.onClick.AddListener(()=>onTap());return b;
  }
  // Invisible hit area (for parts baked into a rendered sprite).
  public static Image HitArea(RectTransform parent,string name){var img=N.Image(parent,name,new Color(1,1,1,0),0);Stretch(img.rectTransform,Vector2.zero,Vector2.one);img.raycastTarget=true;return img;}
  public static CheckoutDragToken Drag(Graphic g){g.raycastTarget=true;var d=g.GetComponent<CheckoutDragToken>();if(!d)d=g.gameObject.AddComponent<CheckoutDragToken>();return d;}

  // Soft round glow and screen vignette, generated once.
  static Sprite glow,vignette;
  public static Sprite Glow(){
   if(glow)return glow;const int n=128;var t=new Texture2D(n,n,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp};var px=new Color32[n*n];
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(n/2f,n/2f))/(n/2f);float a=Mathf.Clamp01(1-d);a=a*a*(3-2*a);px[y*n+x]=new Color32(255,255,255,(byte)(a*255));}
   t.SetPixels32(px);t.Apply();return glow=Sprite.Create(t,new Rect(0,0,n,n),new Vector2(.5f,.5f));
  }
  public static Sprite Vignette(){
   if(vignette)return vignette;const int w=160,h=90;var t=new Texture2D(w,h,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp};var px=new Color32[w*h];
   for(int y=0;y<h;y++)for(int x=0;x<w;x++){float dx=(x+.5f)/w*2-1,dy=(y+.5f)/h*2-1;float d=Mathf.Sqrt(dx*dx*.8f+dy*dy);float a=Mathf.Clamp01((d-.55f)/.75f);px[y*w+x]=new Color32(40,24,12,(byte)(a*a*150));}
   t.SetPixels32(px);t.Apply();return vignette=Sprite.Create(t,new Rect(0,0,w,h),new Vector2(.5f,.5f));
  }
  public static Image GlowAt(Transform parent,string name,Color color,Vector2 anchor,float size,Vector2 offset=default){var img=N.Image(parent,name,color,0);img.sprite=Glow();img.raycastTarget=false;At(img.rectTransform,anchor,new Vector2(size,size),offset);return img;}
  // Drop shadow under a floating item (dark soft ellipse).
  public static Image Shadow(Transform parent,Vector2 size,Vector2 offset){var img=N.Image(parent,"Shadow",new Color(.18f,.1f,.04f,.35f),0);img.sprite=Glow();img.raycastTarget=false;At(img.rectTransform,new Vector2(.5f,0),size,offset);img.transform.SetAsFirstSibling();return img;}

  // Mini-game window in the HUD style: cream card with a wooden title plaque and a textured stage.
  public static RectTransform GameWindow(RectTransform root,string backdrop,out GameObject dim,out TextMeshProUGUI title,out Image backdropImage,Action onClose){
   var back=Box(root,"Dim","000000",0,Vector2.zero,Vector2.one);back.color=new Color(.12f,.08f,.04f,.66f);back.raycastTarget=true;dim=back.gameObject;
   var edge=Box(back.transform,"Edge","B98E55",30,new Vector2(.04f,.05f),new Vector2(.96f,.93f));
   var face=Box(edge.transform,"Face","FFF7EC",28,Vector2.zero,Vector2.one);face.rectTransform.offsetMin=new Vector2(4,10);face.rectTransform.offsetMax=new Vector2(-4,-4);
   // Stage: rounded mask with the rendered backdrop and a soft vignette.
   var frame=Box(face.transform,"StageFrame","D4B482",22,Vector2.zero,Vector2.one);frame.rectTransform.offsetMin=new Vector2(16,16);frame.rectTransform.offsetMax=new Vector2(-16,-16);
   var maskImg=Box(frame.transform,"StageMask","FFFFFF",20,Vector2.zero,Vector2.one);maskImg.rectTransform.offsetMin=new Vector2(5,5);maskImg.rectTransform.offsetMax=new Vector2(-5,-5);
   maskImg.gameObject.AddComponent<Mask>().showMaskGraphic=true;
   backdropImage=Backdrop(maskImg.transform,backdrop);
   var stage=N.Node("Stage",maskImg.transform);Stretch(stage,Vector2.zero,Vector2.one);
   var vig=N.Image(maskImg.transform,"Vignette",Color.white,0);vig.sprite=Vignette();vig.raycastTarget=false;Stretch(vig.rectTransform,Vector2.zero,Vector2.one);
   // Wooden plaque with the title, overlapping the top edge.
   var plaque=N.Image(back.transform,"Plaque",Color.white,0);plaque.sprite=Sliced("panel_board",new Vector4(70,60,70,60));plaque.type=Image.Type.Sliced;plaque.raycastTarget=false;
   plaque.pixelsPerUnitMultiplier=1.6f;At(plaque.rectTransform,new Vector2(.5f,.93f),new Vector2(640,96));
   title=Label(plaque.transform,"Title",K.Headline,34,"FFFFFF");Stretch(title.rectTransform,Vector2.zero,Vector2.one,new Vector2(30,6),new Vector2(-30,-4));
   title.fontSizeMin=20;title.enableAutoSizing=true;title.fontSizeMax=34;title.outlineWidth=.18f;title.outlineColor=new Color32(110,62,24,255);
   var close=Button(back.transform,"X","danger",onClose,64,26);At((RectTransform)close.transform,new Vector2(.96f,.93f),new Vector2(72,72),new Vector2(-18,-18));
   return stage;
  }
  static readonly Dictionary<string,Sprite> sliced=new Dictionary<string,Sprite>();
  public static Sprite Sliced(string name,Vector4 border){
   if(sliced.TryGetValue(name,out var cached))return cached;var tex=Resources.Load<Texture2D>("CheckoutDesktop/Game/"+name);
   var s=tex?Sprite.Create(tex,new Rect(0,0,tex.width,tex.height),new Vector2(.5f,.5f),100,0,SpriteMeshType.FullRect,border):null;sliced[name]=s;return s;
  }

  // Ghost hand that shows the gesture (drag from -> to, or tap) until Stop() or the object dies.
  public static GameObject Hint(MonoBehaviour runner,RectTransform space,Func<Vector2> from,Func<Vector2> to,bool tap=false){
   var hand=Art(space,"Hint","hand_pointer",new Vector2(.5f,.5f),120);hand.rectTransform.pivot=new Vector2(.3f,.95f);hand.rectTransform.localRotation=Quaternion.Euler(0,0,160);
   var group=hand.gameObject.AddComponent<CanvasGroup>();group.blocksRaycasts=false;group.interactable=false;group.alpha=0;
   runner.StartCoroutine(HintLoop(hand.rectTransform,group,from,to,tap));return hand.gameObject;
  }
  static bool HintPoints(Func<Vector2> from,Func<Vector2> to,out Vector2 a,out Vector2 b){
   try {a=from();b=to();return true;}catch(Exception){a=b=Vector2.zero;return false;}
  }
  static IEnumerator HintLoop(RectTransform hand,CanvasGroup group,Func<Vector2> from,Func<Vector2> to,bool tap){
   yield return new WaitForSecondsRealtime(1.2f);
   while(hand){
    // The targets may be gone (a box already shelved): then the hint just ends.
    if(!HintPoints(from,to,out var a,out var b))yield break;
    hand.SetAsLastSibling();hand.anchoredPosition=a;
    for(float t=0;t<1;t+=Time.unscaledDeltaTime/.25f){if(!hand)yield break;group.alpha=t;yield return null;}
    if(!hand)yield break;
    if(tap){for(int i=0;i<2;i++){for(float t=0;t<1;t+=Time.unscaledDeltaTime/.18f){if(!hand)yield break;hand.localScale=Vector3.one*(1-.15f*Mathf.Sin(t*Mathf.PI));yield return null;}}}
    else{hand.localScale=Vector3.one*.9f;for(float t=0;t<1;t+=Time.unscaledDeltaTime/1.1f){if(!hand)yield break;hand.anchoredPosition=Vector2.Lerp(a,b,Ease(t));yield return null;}if(!hand)yield break;hand.localScale=Vector3.one;}
    for(float t=1;t>0;t-=Time.unscaledDeltaTime/.3f){if(!hand)yield break;group.alpha=t;yield return null;}
    yield return new WaitForSecondsRealtime(.9f);
   }
  }
  // A rendered emote that pops above a point, floats up and fades.
  public static IEnumerator Emote(MonoBehaviour runner,RectTransform parent,string kind,Vector2 at,float size=110){
   var e=Art(parent,"Emote","emote_"+kind,new Vector2(.5f,.5f),size,at);e.rectTransform.localScale=Vector3.zero;
   yield return Scale(e.rectTransform,Vector3.one,.3f,true);runner.StartCoroutine(Move(e.rectTransform,at+new Vector2(0,60),1.2f));
   yield return new WaitForSecondsRealtime(.7f);yield return Fade(e,0,.5f);if(e)UnityEngine.Object.Destroy(e.gameObject);
  }
  // Sparkles bursting around a point (success).
  public static void Sparkles(MonoBehaviour runner,RectTransform parent,Vector2 at,int count=8,float radius=160){
   for(int i=0;i<count;i++){var s=Art(parent,"Sparkle","sparkle",new Vector2(.5f,.5f),UnityEngine.Random.Range(40,80),at);s.rectTransform.localScale=Vector3.zero;runner.StartCoroutine(Burst(s,at+UnityEngine.Random.insideUnitCircle.normalized*radius*UnityEngine.Random.Range(.5f,1f),i*.03f));}
  }
  static IEnumerator Burst(Image s,Vector2 to,float delay){
   yield return new WaitForSecondsRealtime(delay);if(!s)yield break;var r=s.rectTransform;var from=r.anchoredPosition;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.7f){if(!s)yield break;r.anchoredPosition=Vector2.Lerp(from,to,Ease(t));r.localScale=Vector3.one*Mathf.Sin(t*Mathf.PI);r.localRotation=Quaternion.Euler(0,0,t*180);yield return null;}
   if(s)UnityEngine.Object.Destroy(s.gameObject);
  }

  // Recorded-style effects from scripts/make_sounds.py (Resources/CheckoutDesktop/Sounds/<name>.wav).
  static readonly Dictionary<string,AudioClip> sfx=new Dictionary<string,AudioClip>();
  public static AudioClip Sfx(string name){
   if(string.IsNullOrEmpty(name))return null;
   if(sfx.TryGetValue(name,out var clip))return clip;
   clip=Resources.Load<AudioClip>("CheckoutDesktop/Sounds/"+name);sfx[name]=clip;return clip;
  }
  public static AudioClip Tone(float hz,float seconds,float hz2=0,float volume=.5f){
   int rate=22050,count=Mathf.Max(1,(int)(rate*seconds));var data=new float[count];
   for(int i=0;i<count;i++){float t=i/(float)rate,f=hz2>0&&i>count/2?hz2:hz,env=Mathf.Clamp01(1-t/seconds)*Mathf.Clamp01(t*80);data[i]=Mathf.Sin(2*Mathf.PI*f*t)*volume*env;}
   var clip=AudioClip.Create("tone"+hz,count,1,rate,false);clip.SetData(data,0);return clip;
  }
  // Short burst of noise (paper tearing, drawer rolling, scrubbing).
  public static AudioClip Noise(float seconds,float volume=.25f){
   int rate=22050,count=Mathf.Max(1,(int)(rate*seconds));var data=new float[count];var random=new System.Random(7);
   for(int i=0;i<count;i++){float t=i/(float)rate;data[i]=((float)random.NextDouble()*2-1)*volume*Mathf.Clamp01(1-t/seconds);}
   var clip=AudioClip.Create("noise",count,1,rate,false);clip.SetData(data,0);return clip;
  }

  // ------------------------------------------------------------------ tweens (unscaled time)
  static float Ease(float t)=>1-Mathf.Pow(1-t,3);
  static float Back(float t){const float c=1.7f;t-=1;return 1+(c+1)*t*t*t+c*t*t;}
  public static IEnumerator Move(RectTransform rect,Vector2 to,float seconds,bool overshoot=false){
   if(!rect)yield break;Vector2 from=rect.anchoredPosition;for(float t=0;t<1;t+=Time.unscaledDeltaTime/Mathf.Max(.01f,seconds)){if(!rect)yield break;rect.anchoredPosition=Vector2.LerpUnclamped(from,to,overshoot?Back(t):Ease(t));yield return null;}if(rect)rect.anchoredPosition=to;
  }
  public static IEnumerator Scale(Transform target,Vector3 to,float seconds,bool overshoot=false){
   if(!target)yield break;var from=target.localScale;for(float t=0;t<1;t+=Time.unscaledDeltaTime/Mathf.Max(.01f,seconds)){if(!target)yield break;target.localScale=Vector3.LerpUnclamped(from,to,overshoot?Back(t):Ease(t));yield return null;}if(target)target.localScale=to;
  }
  public static IEnumerator Rotate(Transform target,float toZ,float seconds){
   if(!target)yield break;float from=target.localEulerAngles.z;if(from>180)from-=360;for(float t=0;t<1;t+=Time.unscaledDeltaTime/Mathf.Max(.01f,seconds)){if(!target)yield break;target.localRotation=Quaternion.Euler(0,0,Mathf.Lerp(from,toZ,Ease(t)));yield return null;}if(target)target.localRotation=Quaternion.Euler(0,0,toZ);
  }
  public static IEnumerator Fade(Graphic graphic,float toAlpha,float seconds){
   if(!graphic)yield break;var from=graphic.color;var to=new Color(from.r,from.g,from.b,toAlpha);for(float t=0;t<1;t+=Time.unscaledDeltaTime/Mathf.Max(.01f,seconds)){if(!graphic)yield break;graphic.color=Color.Lerp(from,to,t);yield return null;}if(graphic)graphic.color=to;
  }
  public static IEnumerator Tint(Graphic graphic,Color to,float seconds){
   if(!graphic)yield break;var from=graphic.color;for(float t=0;t<1;t+=Time.unscaledDeltaTime/Mathf.Max(.01f,seconds)){if(!graphic)yield break;graphic.color=Color.Lerp(from,to,t);yield return null;}if(graphic)graphic.color=to;
  }
  public static IEnumerator Shake(RectTransform rect,float seconds,float strength=14){
   if(!rect)yield break;var home=rect.anchoredPosition;for(float t=0;t<seconds;t+=Time.unscaledDeltaTime){if(!rect)yield break;rect.anchoredPosition=home+new Vector2(Mathf.Sin(t*70)*strength*(1-t/seconds),0);yield return null;}if(rect)rect.anchoredPosition=home;
  }
  public static IEnumerator Pop(Transform target,float peak=1.18f,float seconds=.28f){
   if(!target)yield break;var home=target.localScale;yield return Scale(target,home*peak,seconds*.4f);yield return Scale(target,home,seconds*.6f,true);
  }
  // Flying coin icons from a point to another, for a satisfying payout.
  public static IEnumerator Coins(MonoBehaviour runner,RectTransform parent,Vector2 from,Vector2 to,int count){
   for(int i=0;i<count;i++){
    var coin=Icon(parent,"Coin","Icons/coin",new Vector2(.5f,.5f),new Vector2(54,54),from+UnityEngine.Random.insideUnitCircle*30);
    runner.StartCoroutine(Fly(coin.rectTransform,to));yield return new WaitForSecondsRealtime(.06f);
   }
  }
  static IEnumerator Fly(RectTransform coin,Vector2 to){
   var from=coin.anchoredPosition;var mid=(from+to)*.5f+new Vector2(0,220);
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.65f){if(!coin)yield break;float e=Ease(t);coin.anchoredPosition=Vector2.Lerp(Vector2.Lerp(from,mid,e),Vector2.Lerp(mid,to,e),e);coin.localScale=Vector3.one*(1-.4f*e);yield return null;}
   if(coin)UnityEngine.Object.Destroy(coin.gameObject);
  }
 }

 // Drag with mouse or finger. While dragging the token follows the pointer; dropping over the target
 // calls onDrop(target) (true keeps it where the handler put it), anywhere else it springs back home.
 public sealed class CheckoutDragToken:MonoBehaviour,IBeginDragHandler,IDragHandler,IEndDragHandler,IPointerDownHandler {
  RectTransform rect;RectTransform[] targets;Vector2 home;Func<RectTransform,bool> onDrop;Action onMiss;Action onGrab;public bool Locked;
  public void Setup(RectTransform[] dropTargets,Func<RectTransform,bool> drop,Action miss=null,Action grab=null){rect=(RectTransform)transform;var g=GetComponent<Graphic>();if(!g){var hit=gameObject.AddComponent<Image>();hit.color=new Color(1,1,1,0);g=hit;}g.raycastTarget=true;targets=dropTargets;onDrop=drop;onMiss=miss;onGrab=grab;if(!homeSet)home=rect.anchoredPosition;}
  public void Setup(RectTransform dropTarget,Func<bool> hit,Action miss=null){Setup(new[]{dropTarget},_=>hit(),miss);}
  public void SetHome(Vector2 position){home=position;homeSet=true;}bool homeSet;
  public bool Dragging{get;private set;}
  public Action<Vector2> Moved;
  public void OnPointerDown(PointerEventData e){}
  public void OnBeginDrag(PointerEventData e){if(Locked)return;Dragging=true;StopAllCoroutines();transform.SetAsLastSibling();rect.localScale=Vector3.one*1.1f;onGrab?.Invoke();}
  public void OnDrag(PointerEventData e){if(Locked)return;if(RectTransformUtility.ScreenPointToLocalPointInRectangle((RectTransform)rect.parent,e.position,e.pressEventCamera,out var local)){rect.localPosition=local;Moved?.Invoke(local);}}
  public void OnEndDrag(PointerEventData e){
   Dragging=false;if(Locked)return;rect.localScale=Vector3.one;
   foreach(var target in targets)if(target&&RectTransformUtility.RectangleContainsScreenPoint(target,e.position,e.pressEventCamera)&&onDrop(target))return;
   StartCoroutine(CheckoutUiKit.Move(rect,home,.35f,true));onMiss?.Invoke();
  }
 }
}
