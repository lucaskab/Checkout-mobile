using System;
using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // Shared pieces of the sector puzzles (CheckoutDesktopHUD.KitchenPuzzle*.cs): nodes on the bench in stage coordinates
 // (centre = 0,0), boards, labels, drag handles, the score rule and the little celebrations. Every puzzle builds its
 // board from these, so they all look and feel like the bakery tray Lucas liked (24/10).
 public partial class CheckoutDesktopHUD {
  float StageW=>kitchenStage.rect.width;
  float StageH=>kitchenStage.rect.height;

  RectTransform PNode(Transform parent,string name,Vector2 at,Vector2 size){
   var r=N.Node(name,parent);r.anchorMin=r.anchorMax=r.pivot=new Vector2(.5f,.5f);r.anchoredPosition=at;r.sizeDelta=size;
   if(parent==kitchenStage)kitchenScene.Add(r.gameObject);return r;
  }
  Image PImage(Transform parent,string name,Color color,int radius,Vector2 at,Vector2 size){
   var i=N.Image(parent,name,color,radius);var r=i.rectTransform;r.anchorMin=r.anchorMax=r.pivot=new Vector2(.5f,.5f);r.anchoredPosition=at;r.sizeDelta=size;
   if(parent==kitchenStage)kitchenScene.Add(i.gameObject);return i;
  }
  TextMeshProUGUI PText(Transform parent,string text,float size,Color color,Vector2 at,Vector2 box,TMP_FontAsset font=null){
   var t=N.Text(parent,"Text",font??K.Label,size,color);t.alignment=TextAlignmentOptions.Center;t.textWrappingMode=TextWrappingModes.NoWrap;t.text=text;
   var r=t.rectTransform;r.anchorMin=r.anchorMax=r.pivot=new Vector2(.5f,.5f);r.anchoredPosition=at;r.sizeDelta=box;
   if(parent==kitchenStage)kitchenScene.Add(t.gameObject);return t;
  }
  // A framed board (wood edge, cream face) the puzzle's pieces sit on.
  RectTransform PBoard(string name,Vector2 at,Vector2 size,string edge="8A5A2B",string face="FFF3DF"){
   var b=PImage(kitchenStage,name,K.C(edge),22,at,size);
   var f=N.Image(b.transform,"Face",K.C(face),20);Stretch(f.rectTransform,new Vector2(4,7),new Vector2(-4,-4));
   return f.rectTransform;
  }
  // Soft shadow under a piece.
  void PShadow(Transform parent,Vector2 size){var s=N.Image(parent,"Shadow",new Color(.2f,.1f,.03f,.28f),0);s.sprite=U.Glow();var r=s.rectTransform;r.anchorMin=r.anchorMax=r.pivot=new Vector2(.5f,.5f);r.anchoredPosition=new Vector2(0,-size.y*.08f);r.sizeDelta=size*1.15f;}
  // Pointer handle (drag / tap) in stage coordinates.
  TrayHandle PHandle(RectTransform r,Action<Vector2> began,Action<Vector2> moved,Action<Vector2> ended,Action tapped){
   var img=r.GetComponent<Image>();if(!img){img=r.gameObject.AddComponent<Image>();img.color=new Color(1,1,1,.001f);}else if(img.color.a<=0)img.color=new Color(1,1,1,.001f);img.raycastTarget=true;
   var h=r.gameObject.AddComponent<TrayHandle>();h.Space=kitchenStage;h.Began=began;h.Moved=moved;h.Ended=ended;h.Tapped=tapped;return h;
  }
  // A small button on the bench (Dica, Desfazer, Recomeçar).
  CheckoutDesktopButton PButton(string label,string variant,Vector2 at,Vector2 size,Action click){
   var b=U.Button(kitchenStage,label,variant,click,size.y,18);Destroy(b.GetComponent<LayoutElement>());
   var r=(RectTransform)b.transform;r.anchorMin=r.anchorMax=r.pivot=new Vector2(.5f,.5f);r.anchoredPosition=at;r.sizeDelta=size;kitchenScene.Add(b.gameObject);return b;
  }
  // Stage point of a pointer / rect (the stage is centred).
  bool PInside(Vector2 p,RectTransform r,float margin=0){var a=r.anchoredPosition;var s=r.sizeDelta*.5f;return Mathf.Abs(p.x-a.x)<=s.x+margin&&Mathf.Abs(p.y-a.y)<=s.y+margin;}
  // Moves against the ideal: at the ideal = 1, each extra move costs a bit; a hint caps it (2 stars at best overall).
  static float PuzzleScore(int moves,int par,bool hint,float perMove=.08f){
   float s=moves<=par?1f:Mathf.Max(.45f,1f-perMove*(moves-par));return hint?Mathf.Min(s,.7f):s;
  }
  // Moves counter on the bench.
  TextMeshProUGUI PMoves(Vector2 at,float width){
   var t=PText(kitchenStage,"",17,K.Ink,at,new Vector2(width,28));t.outlineWidth=.2f;t.outlineColor=new Color32(255,255,255,200);return t;
  }
  void PMovesText(TextMeshProUGUI t,int moves,int par){if(t)t.text=$"Movimentos: {moves}  ·  ideal: {par}";}
  IEnumerator PSolved(Vector2 at,float radius){Sound("success");U.Sparkles(this,kitchenStage,at,14,radius);yield return new WaitForSecondsRealtime(.9f);}
  IEnumerator PFlash(Image img,Color color,float seconds=.5f){
   if(!img)yield break;var home=img.color;for(float k=0;k<seconds&&img;k+=Time.unscaledDeltaTime){img.color=Color.Lerp(color,home,k/seconds);yield return null;}if(img)img.color=home;
  }
  // A rough 1:1 hash for deterministic little patterns (cheese spots, marbling).
  static float Noise(int a,int b){unchecked{int h=a*73856093^b*19349663;h=(h<<13)^h;return ((h*(h*h*15731+789221)+1376312589)&0x7fffffff)/2147483647f;}}
 }
}
