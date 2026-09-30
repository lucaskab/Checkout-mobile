using System;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using K = Checkout.CheckoutDesktopKit;
namespace Checkout {
 // 3D pressable button: a darker edge under a raised face that sinks while pressed.
 public class CheckoutDesktopButton:MonoBehaviour,IPointerDownHandler,IPointerUpHandler,IPointerExitHandler,IPointerClickHandler {
  const float Lift=4;
  UnityEngine.UI.Image edge,face,icon;TextMeshProUGUI label;RectTransform faceRect;UnityEngine.UI.LayoutElement layout;
  public DesktopButton Data {get;private set;}
  public Action<CheckoutDesktopButton> Clicked;
  bool pressed;

  public static CheckoutDesktopButton Create(Transform parent,float height,float fontSize,int radius=12,bool stacked=false){
   var go=new GameObject("Button",typeof(RectTransform));go.transform.SetParent(parent,false);
   var button=go.AddComponent<CheckoutDesktopButton>();
   button.edge=go.AddComponent<UnityEngine.UI.Image>();button.edge.sprite=K.Rounded(radius);button.edge.type=UnityEngine.UI.Image.Type.Sliced;
   button.layout=go.AddComponent<UnityEngine.UI.LayoutElement>();button.layout.minHeight=button.layout.preferredHeight=height;button.layout.flexibleWidth=1;
   var faceGo=new GameObject("Face",typeof(RectTransform));faceGo.transform.SetParent(go.transform,false);
   button.faceRect=(RectTransform)faceGo.transform;button.faceRect.anchorMin=Vector2.zero;button.faceRect.anchorMax=Vector2.one;
   button.face=faceGo.AddComponent<UnityEngine.UI.Image>();button.face.sprite=K.Rounded(radius);button.face.type=UnityEngine.UI.Image.Type.Sliced;button.face.raycastTarget=false;
   // Toolbar buttons stack the icon over the label; everything else is a single row.
   UnityEngine.UI.HorizontalOrVerticalLayoutGroup row=stacked?faceGo.AddComponent<UnityEngine.UI.VerticalLayoutGroup>():faceGo.AddComponent<UnityEngine.UI.HorizontalLayoutGroup>();
   row.childAlignment=TextAnchor.MiddleCenter;row.spacing=stacked?2:6;row.padding=stacked?new RectOffset(4,4,6,4):new RectOffset(10,10,2,2);
   row.childControlWidth=row.childControlHeight=true;row.childForceExpandWidth=row.childForceExpandHeight=false;
   var iconGo=new GameObject("Icon",typeof(RectTransform));iconGo.transform.SetParent(faceGo.transform,false);
   button.icon=iconGo.AddComponent<UnityEngine.UI.Image>();button.icon.preserveAspect=true;button.icon.raycastTarget=false;
   var iconLayout=iconGo.AddComponent<UnityEngine.UI.LayoutElement>();iconLayout.preferredWidth=iconLayout.preferredHeight=Mathf.Round(height*(stacked?.45f:.5f));
   var labelGo=new GameObject("Label",typeof(RectTransform));labelGo.transform.SetParent(faceGo.transform,false);
   button.label=labelGo.AddComponent<TextMeshProUGUI>();button.label.font=K.Label;button.label.fontSize=fontSize;button.label.alignment=TextAlignmentOptions.Center;
   button.label.textWrappingMode=TextWrappingModes.NoWrap;button.label.overflowMode=TextOverflowModes.Ellipsis;button.label.raycastTarget=false;
   button.Layout();return button;
  }
  public void SetWidth(float width){layout.flexibleWidth=width>0?0:1;layout.preferredWidth=width>0?width:-1;layout.minWidth=width>0?width:-1;}
  public void Apply(DesktopButton data){
   Data=data;var style=K.Variant(data.variant,data.enabled,data.active);
   edge.color=style.edge;face.color=style.face;label.color=style.text;
   var text=K.Clean(data.label);if(label.text!=text)label.text=text;label.gameObject.SetActive(!string.IsNullOrEmpty(text));
   var sprite=K.Icon(data.icon);icon.sprite=sprite;icon.gameObject.SetActive(sprite);
   icon.color=data.enabled?Color.white:new Color(1,1,1,.55f);
  }
  void Layout(){float drop=pressed?Lift-2:0;faceRect.offsetMin=new Vector2(0,Lift-drop);faceRect.offsetMax=new Vector2(0,-drop);}
  public void OnPointerDown(PointerEventData e){if(e.button!=PointerEventData.InputButton.Left||Data==null||!Data.enabled)return;pressed=true;Layout();}
  public void OnPointerUp(PointerEventData e){pressed=false;Layout();}
  public void OnPointerExit(PointerEventData e){pressed=false;Layout();}
  public void OnPointerClick(PointerEventData e){if(e.button==PointerEventData.InputButton.Left&&Data!=null)Clicked?.Invoke(this);}
 }
}
