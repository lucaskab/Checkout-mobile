using System;
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
 // Juice for the Delivery app: chunky 3D buttons, coin bursts and confetti on an overlay canvas.
 public sealed partial class CheckoutDeliveryApp {
  // Layer for the particles: an overlay above the store computer, so bursts fly over every panel.
  RectTransform fxRoot;
  static readonly string[] Confetti_Colors={"E15533","2E8CAE","3DAA5C","F2B03D","8B5C9E","FF8FB1"};

  // A chunky 3D button: a dark bottom edge, a bright face that presses down 4 px, a little idle wiggle when asked.
  public sealed class JuicyButton:MonoBehaviour,IPointerDownHandler,IPointerUpHandler,IPointerExitHandler,IPointerEnterHandler,IPointerClickHandler {
   const float EdgeH=7f,PressDrop=4f;
   Image edge,face;TextMeshProUGUI label;Image icon;RectTransform faceRect;
   string fillHex="2E8CAE",edgeHex="1F6A86",lastFill="",lastEdge="",textHex="FFFFFF";
   bool enabledNow=true,pressed,hover,wiggle;
   public Action Clicked;

   public static JuicyButton Create(Transform parent,string text,string fillHex,string edgeHex,float height,float fontSize,string iconPath,bool wiggle,string textHex="FFFFFF"){
    var go=new GameObject("JuicyButton",typeof(RectTransform));go.transform.SetParent(parent,false);
    var b=go.AddComponent<JuicyButton>();
    var layout=go.AddComponent<LayoutElement>();layout.minHeight=height;layout.preferredHeight=height;layout.flexibleWidth=1;
    b.edge=go.AddComponent<Image>();b.edge.raycastTarget=true;
    var faceGo=new GameObject("Face",typeof(RectTransform));faceGo.transform.SetParent(go.transform,false);
    b.faceRect=(RectTransform)faceGo.transform;b.faceRect.anchorMin=Vector2.zero;b.faceRect.anchorMax=Vector2.one;
    b.face=faceGo.AddComponent<Image>();b.face.raycastTarget=false;
    var row=faceGo.AddComponent<HorizontalLayoutGroup>();row.childAlignment=TextAnchor.MiddleCenter;row.spacing=10;row.padding=new RectOffset(14,14,4,4);
    row.childControlWidth=true;row.childControlHeight=true;row.childForceExpandWidth=false;row.childForceExpandHeight=false;
    var iconGo=new GameObject("Icon",typeof(RectTransform));iconGo.transform.SetParent(faceGo.transform,false);
    b.icon=iconGo.AddComponent<Image>();b.icon.preserveAspect=true;b.icon.raycastTarget=false;
    var il=iconGo.AddComponent<LayoutElement>();il.preferredWidth=il.preferredHeight=Mathf.Round(height*.55f);
    iconGo.SetActive(!string.IsNullOrEmpty(iconPath));
    if(!string.IsNullOrEmpty(iconPath))b.icon.sprite=K.Icon(iconPath);
    var labelGo=new GameObject("Label",typeof(RectTransform));labelGo.transform.SetParent(faceGo.transform,false);
    b.label=labelGo.AddComponent<TextMeshProUGUI>();b.label.font=K.Headline;b.label.fontSize=fontSize;b.label.alignment=TextAlignmentOptions.Center;
    // Labels never truncate: they shrink (down to 16) to fit the button instead of showing an ellipsis.
    b.label.textWrappingMode=TextWrappingModes.NoWrap;b.label.overflowMode=TextOverflowModes.Overflow;b.label.raycastTarget=false;
    b.label.enableAutoSizing=true;b.label.fontSizeMin=16;b.label.fontSizeMax=fontSize;
    b.label.color=K.C(textHex);
    b.label.text=text??"";
    b.fillHex=fillHex;b.edgeHex=edgeHex;b.wiggle=wiggle;b.textHex=textHex;
    b.Paint();b.Place(false);
    return b;
   }
   public void SetText(string text){if(label&&label.text!=text)label.text=text??"";}
   public void SetFill(string fill,string edgeColor){fillHex=fill;edgeHex=edgeColor;Paint();}
   public void SetEnabled(bool on){enabledNow=on;Paint();}
   void Paint(){
    if(edgeHex!=lastEdge){lastEdge=edgeHex;edge.sprite=DeliveryArt.Chunk(edgeHex,20);}
    if(fillHex!=lastFill){lastFill=fillHex;face.sprite=DeliveryArt.Chunk(fillHex,20);}
    edge.type=Image.Type.Sliced;face.type=Image.Type.Sliced;
    edge.color=Color.white;
    face.color=enabledNow?Color.white:new Color(.62f,.58f,.52f,1f);
    label.color=enabledNow?K.C(textHex):K.C("B9AE9C");
   }
   // Pressed or up: the face sits EdgeH px above the edge; pressed it drops PressDrop px.
   void Place(bool down){
    float drop=down?PressDrop:0f;
    faceRect.offsetMin=new Vector2(0,EdgeH-drop);
    faceRect.offsetMax=new Vector2(0,-drop);
   }
   void Update(){
    if(!pressed&&wiggle&&enabledNow)transform.localScale=Vector3.one*(1f+.022f*Mathf.Sin(Time.unscaledTime*5f));
    else if(transform.localScale.x!=1f)transform.localScale=Vector3.one;
    if(hover&&!pressed&&enabledNow)face.color=new Color(1.08f,1.08f,1.08f,1f);
    else if(enabledNow)face.color=Color.white;
   }
   public void OnPointerDown(PointerEventData e){if(e.button!=PointerEventData.InputButton.Left||!enabledNow)return;pressed=true;Place(true);}
   public void OnPointerUp(PointerEventData e){pressed=false;Place(false);}
   public void OnPointerExit(PointerEventData e){pressed=false;hover=false;Place(false);}
   public void OnPointerEnter(PointerEventData e){hover=true;}
   public void OnPointerClick(PointerEventData e){
    if(e.button!=PointerEventData.InputButton.Left||!enabledNow)return;
    StartCoroutine(U.Pop(transform,1.06f,.18f));
    Clicked?.Invoke();
   }
  }

  // Particles: small pieces fly out of a source, arc, fall and fade. Coins are the same with the coin sprite.
  void Burst(RectTransform source,int count,bool coins){
   if(!fxRoot||!source)return;
   Vector2 at=LocalOf(source);
   for(int i=0;i<count;i++){
    var img=N.Image(fxRoot,"Piece",Color.white,0);img.raycastTarget=false;
    if(coins){img.sprite=K.Icon("Icons/coin");U.At(img.rectTransform,new Vector2(.5f,.5f),new Vector2(34,34),at);}
    else{img.sprite=K.Rounded(3);img.color=K.C(Confetti_Colors[UnityEngine.Random.Range(0,Confetti_Colors.Length)]);U.At(img.rectTransform,new Vector2(.5f,.5f),new Vector2(12,18),at);}
    float angle=UnityEngine.Random.Range(0f,Mathf.PI*2f);float speed=coins?UnityEngine.Random.Range(380f,640f):UnityEngine.Random.Range(260f,520f);
    Vector2 vel=new Vector2(Mathf.Cos(angle),Mathf.Sin(angle))*speed;
    if(vel.y<0)vel.y=-vel.y;
    StartCoroutine(Fly(img,vel,coins?1.1f:1.4f,UnityEngine.Random.Range(-540f,540f)));
   }
  }
  // Public helpers used by the cards and the notification.
  static void Coins(RectTransform source,int count){if(Instance)Instance.Burst(source,count,true);}
  static void Confetti(RectTransform source,int count){if(Instance)Instance.Burst(source,count,false);}
  IEnumerator Fly(Image img,Vector2 vel,float life,float spin){
   float t=0;const float gravity=1100f;
   var rect=img.rectTransform;
   Vector2 pos=rect.anchoredPosition;
   while(t<life){
    if(!img)yield break;
    float dt=Time.unscaledDeltaTime;t+=dt;
    vel.y-=gravity*dt;vel*=Mathf.Pow(.4f,dt);
    pos+=vel*dt;
    rect.anchoredPosition=pos;
    rect.localRotation=Quaternion.Euler(0,0,spin*t);
    img.color=new Color(img.color.r,img.color.g,img.color.b,Mathf.Clamp01((life-t)/.35f));
    yield return null;
   }
   if(img)Destroy(img.gameObject);
  }
  // Local position (fxRoot space) of the centre of a rect.
  Vector2 LocalOf(RectTransform source){
   Vector3 world=source.TransformPoint(source.rect.center);
   return (Vector2)fxRoot.InverseTransformPoint(world);
  }
 }
}
