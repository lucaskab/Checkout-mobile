using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
namespace Checkout {
 // One pooled card of a HUD page. Apply() updates it in place so scrolling survives refreshes.
 public class CheckoutDesktopCard:MonoBehaviour {
  UnityEngine.UI.Image edge,face,icon,badgeBack,fill;TextMeshProUGUI eyebrow,title,subtitle,badge;
  Transform lines,buttons;GameObject header,texts,progress;RectTransform fillRect;
  readonly List<TextMeshProUGUI> linePool=new List<TextMeshProUGUI>();readonly List<CheckoutDesktopButton> buttonPool=new List<CheckoutDesktopButton>();
  public Action<CheckoutDesktopButton> Clicked;

  public static RectTransform Node(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
  public static UnityEngine.UI.VerticalLayoutGroup Column(GameObject go,int spacing,RectOffset padding=null){var v=go.AddComponent<UnityEngine.UI.VerticalLayoutGroup>();v.spacing=spacing;v.padding=padding??new RectOffset();v.childControlWidth=v.childControlHeight=true;v.childForceExpandWidth=true;v.childForceExpandHeight=false;return v;}
  public static UnityEngine.UI.HorizontalLayoutGroup Row(GameObject go,int spacing,RectOffset padding=null){var h=go.AddComponent<UnityEngine.UI.HorizontalLayoutGroup>();h.spacing=spacing;h.padding=padding??new RectOffset();h.childControlWidth=h.childControlHeight=true;h.childForceExpandWidth=false;h.childForceExpandHeight=false;h.childAlignment=TextAnchor.MiddleLeft;return h;}
  public static TextMeshProUGUI Text(Transform parent,string name,TMP_FontAsset font,float size,Color color){
   var t=Node(name,parent).gameObject.AddComponent<TextMeshProUGUI>();t.font=font;t.fontSize=size;t.color=color;t.raycastTarget=false;t.textWrappingMode=TextWrappingModes.Normal;return t;
  }
  public static UnityEngine.UI.Image Image(Transform parent,string name,Color color,int radius){
   var image=Node(name,parent).gameObject.AddComponent<UnityEngine.UI.Image>();image.color=color;image.raycastTarget=false;
   if(radius>0){image.sprite=K.Rounded(radius);image.type=UnityEngine.UI.Image.Type.Sliced;}return image;
  }

  public static CheckoutDesktopCard Create(Transform parent){
   var root=Node("Card",parent);var card=root.gameObject.AddComponent<CheckoutDesktopCard>();
   card.edge=root.gameObject.AddComponent<UnityEngine.UI.Image>();card.edge.sprite=K.Rounded(16);card.edge.type=UnityEngine.UI.Image.Type.Sliced;card.edge.raycastTarget=false;
   Column(root.gameObject,0,new RectOffset(2,2,2,5));
   card.face=Image(root,"Face",K.Cream,14);Column(card.face.gameObject,8,new RectOffset(14,14,12,12));
   card.header=Node("Header",card.face.transform).gameObject;Row(card.header,12);
   card.icon=Image(card.header.transform,"Icon",Color.white,0);card.icon.preserveAspect=true;
   var iconLayout=card.icon.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();iconLayout.preferredWidth=iconLayout.preferredHeight=52;
   card.texts=Node("Texts",card.header.transform).gameObject;Column(card.texts,1);card.texts.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   card.eyebrow=Text(card.texts.transform,"Eyebrow",K.Label,12,K.Muted);card.eyebrow.characterSpacing=4;
   card.title=Text(card.texts.transform,"Title",K.Headline,21,K.Ink);
   card.subtitle=Text(card.texts.transform,"Subtitle",K.Body,15,K.Muted);
   card.badgeBack=Image(card.header.transform,"Badge",K.C("F2B03D"),12);Row(card.badgeBack.gameObject,0,new RectOffset(10,10,4,4));
   card.badge=Text(card.badgeBack.transform,"Text",K.Number,14,K.Ink);card.badge.textWrappingMode=TextWrappingModes.NoWrap;
   card.lines=Node("Lines",card.face.transform);Column(card.lines.gameObject,2);
   var track=Image(card.face.transform,"Progress",K.C("EADBC4"),6);card.progress=track.gameObject;track.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().preferredHeight=12;
   card.fill=Image(track.transform,"Fill",K.C("5DA637"),6);card.fillRect=card.fill.rectTransform;card.fillRect.anchorMin=Vector2.zero;card.fillRect.offsetMin=card.fillRect.offsetMax=Vector2.zero;
   card.buttons=Node("Buttons",card.face.transform);var row=Row(card.buttons.gameObject,8,new RectOffset(0,0,4,0));row.childForceExpandWidth=true;
   return card;
  }

  static void Set(TextMeshProUGUI text,string value){bool has=!string.IsNullOrEmpty(value);text.gameObject.SetActive(has);if(has&&text.text!=value)text.text=value;}
  public void Apply(DesktopCard data){
   var tone=K.Tone(data.tone);edge.color=tone.edge;face.color=tone.face;
   Set(eyebrow,data.eyebrow?.ToUpperInvariant());Set(title,data.title);Set(subtitle,data.subtitle);title.color=tone.text;
   Set(badge,data.badge);badgeBack.gameObject.SetActive(!string.IsNullOrEmpty(data.badge));
   var sprite=K.Icon(data.icon);icon.sprite=sprite;icon.gameObject.SetActive(sprite);icon.color=data.tone=="locked"?new Color(1,1,1,.5f):Color.white;
   header.SetActive(sprite||!string.IsNullOrEmpty(data.title)||!string.IsNullOrEmpty(data.eyebrow)||!string.IsNullOrEmpty(data.badge));
   var values=data.lines??Array.Empty<string>();
   while(linePool.Count<values.Length)linePool.Add(Text(lines,"Line",K.Body,16,K.Ink));
   for(int i=0;i<linePool.Count;i++){bool on=i<values.Length;linePool[i].gameObject.SetActive(on);if(on&&linePool[i].text!=values[i])linePool[i].text=values[i];}
   lines.gameObject.SetActive(values.Length>0);
   progress.SetActive(data.progress>=0);fillRect.anchorMax=new Vector2(Mathf.Clamp01(data.progress),1);
   var actions=data.buttons??Array.Empty<DesktopButton>();
   while(buttonPool.Count<actions.Length){var b=CheckoutDesktopButton.Create(buttons,44,15);b.Clicked=x=>Clicked?.Invoke(x);buttonPool.Add(b);}
   for(int i=0;i<buttonPool.Count;i++){bool on=i<actions.Length;buttonPool[i].gameObject.SetActive(on);if(on)buttonPool[i].Apply(actions[i]);}
   buttons.gameObject.SetActive(actions.Length>0);
  }
 }
}
