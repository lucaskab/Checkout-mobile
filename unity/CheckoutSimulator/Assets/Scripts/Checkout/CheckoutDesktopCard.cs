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
  // Social v1: a text field (friend code, market name) and a QR code on the card.
  GameObject inputRow,qrRow;TMP_InputField field;UnityEngine.UI.RawImage qrImage;string inputId,inputValue,qrShown;
  /// <summary>What was typed in each card field (by input id): buttons send it with "$input:&lt;id&gt;" in their args.</summary>
  public static readonly Dictionary<string,string> Typed=new Dictionary<string,string>();

  public static RectTransform Node(string name,Transform parent){var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);return (RectTransform)go.transform;}
  public static UnityEngine.UI.VerticalLayoutGroup Column(GameObject go,int spacing,RectOffset padding=null){var v=go.AddComponent<UnityEngine.UI.VerticalLayoutGroup>();v.spacing=spacing;v.padding=padding??new RectOffset();v.childControlWidth=v.childControlHeight=true;v.childForceExpandWidth=true;v.childForceExpandHeight=false;return v;}
  public static UnityEngine.UI.HorizontalLayoutGroup Row(GameObject go,int spacing,RectOffset padding=null){var h=go.AddComponent<UnityEngine.UI.HorizontalLayoutGroup>();h.spacing=spacing;h.padding=padding??new RectOffset();h.childControlWidth=h.childControlHeight=true;h.childForceExpandWidth=false;h.childForceExpandHeight=false;h.childAlignment=TextAnchor.MiddleLeft;return h;}
  public static TextMeshProUGUI Text(Transform parent,string name,TMP_FontAsset font,float size,Color color){
   var t=Node(name,parent).gameObject.AddComponent<TextMeshProUGUI>();t.font=font;t.fontSize=size;t.color=color;t.raycastTarget=false;t.textWrappingMode=TextWrappingModes.Normal;CheckoutI18nText.Register(t);CheckoutHandheldText.Register(t);return t;
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
   ApplyInput(data.input);ApplyQr(data.qr);
   var actions=data.buttons??Array.Empty<DesktopButton>();
   while(buttonPool.Count<actions.Length){var b=CheckoutDesktopButton.Create(buttons,44,15);b.Clicked=x=>Clicked?.Invoke(x);buttonPool.Add(b);}
   // The avatar picker: big faces instead of small icons.
   bool faces=actions.Length>0&&Array.TrueForAll(actions,a=>(a.icon??"").StartsWith("avatar:",StringComparison.Ordinal)&&string.IsNullOrEmpty(a.label));
   for(int i=0;i<buttonPool.Count;i++){bool on=i<actions.Length;buttonPool[i].gameObject.SetActive(on);if(on){buttonPool[i].Apply(actions[i]);buttonPool[i].SetSize(faces?92:44,faces?78:22);}}
   buttons.gameObject.SetActive(actions.Length>0);
  }

  void ApplyInput(DesktopInput input){
   bool has=input!=null&&!string.IsNullOrEmpty(input.id);
   if(!has){if(inputRow)inputRow.SetActive(false);return;}
   if(!field)BuildInput();
   inputRow.SetActive(true);
   if(inputId!=input.id){
    inputId=input.id;inputValue=input.value??"";
    field.SetTextWithoutNotify(Typed.TryGetValue(input.id,out var typed)?typed:inputValue);Typed[input.id]=field.text;
   }else if(!field.isFocused&&field.text==inputValue&&(input.value??"")!=inputValue){
    // The page got the saved value later (the profile loaded): shown while the player has not typed.
    inputValue=input.value??"";field.SetTextWithoutNotify(inputValue);Typed[input.id]=inputValue;
   }
   field.characterLimit=input.max>0?input.max:0;
   ((TextMeshProUGUI)field.placeholder).text=input.placeholder??"";
   // Friend codes: capital letters and digits (a dash is fine, the host removes it).
   if(input.kind=="code")field.onValidateInput=(text,index,c)=>char.IsLetterOrDigit(c)&&c<128?char.ToUpperInvariant(c):c=='-'?c:'\0';
   else field.onValidateInput=null;
   inputRow.transform.SetSiblingIndex(buttons.GetSiblingIndex());
  }
  void BuildInput(){
   var edgeImage=Image(face.transform,"Input",K.Border,12);inputRow=edgeImage.gameObject;inputRow.SetActive(false);
   inputRow.AddComponent<UnityEngine.UI.LayoutElement>().preferredHeight=CheckoutScreen.Handheld?60:52;
   var inner=Image(inputRow.transform,"Face",K.White,10);var ir=inner.rectTransform;ir.anchorMin=Vector2.zero;ir.anchorMax=Vector2.one;ir.offsetMin=new Vector2(2,2);ir.offsetMax=new Vector2(-2,-2);
   inner.raycastTarget=true;
   var area=Node("Text Area",inner.transform);area.anchorMin=Vector2.zero;area.anchorMax=Vector2.one;area.offsetMin=new Vector2(14,4);area.offsetMax=new Vector2(-14,-4);
   area.gameObject.AddComponent<UnityEngine.UI.RectMask2D>();
   // Not registered with the translators: the player's own text (and the placeholder comes translated by the host).
   TextMeshProUGUI Field(string name,Color color){
    var t=Node(name,area).gameObject.AddComponent<TextMeshProUGUI>();t.font=K.Body;t.fontSize=CheckoutScreen.Handheld?24:20;t.color=color;
    t.textWrappingMode=TextWrappingModes.NoWrap;t.alignment=TextAlignmentOptions.MidlineLeft;t.raycastTarget=false;
    var r=t.rectTransform;r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;return t;
   }
   var placeholder=Field("Placeholder",K.Muted);placeholder.fontStyle=FontStyles.Italic;
   var text=Field("Text",K.Ink);
   inner.gameObject.SetActive(false);
   field=inner.gameObject.AddComponent<TMP_InputField>();
   field.textViewport=area;field.textComponent=text;field.placeholder=placeholder;field.fontAsset=K.Body;field.pointSize=text.fontSize;
   field.lineType=TMP_InputField.LineType.SingleLine;field.caretWidth=3;field.customCaretColor=true;field.caretColor=K.Ink;
   field.selectionColor=new Color(.95f,.69f,.24f,.45f);
   field.onValueChanged.AddListener(v=>{if(!string.IsNullOrEmpty(inputId))Typed[inputId]=v;});
   inner.gameObject.SetActive(true);
  }
  void ApplyQr(string qr){
   bool has=!string.IsNullOrEmpty(qr);
   if(!has){if(qrRow)qrRow.SetActive(false);return;}
   if(!qrRow){
    qrRow=Node("QR",face.transform).gameObject;qrRow.AddComponent<UnityEngine.UI.LayoutElement>().preferredHeight=250;
    var raw=Node("Code",qrRow.transform).gameObject.AddComponent<UnityEngine.UI.RawImage>();qrImage=raw;raw.raycastTarget=false;
    var r=raw.rectTransform;r.anchorMin=r.anchorMax=r.pivot=new Vector2(.5f,.5f);r.sizeDelta=new Vector2(240,240);
   }
   qrRow.SetActive(true);qrRow.transform.SetSiblingIndex(buttons.GetSiblingIndex());
   if(qrShown!=qr){qrShown=qr;if(qrImage.texture)Destroy(qrImage.texture);qrImage.texture=QrTexture(qr);}
  }
  /// <summary>"&lt;size&gt;:" + rows of 1/0 (desktop/qr.ts) as a black-on-white texture with a quiet zone.</summary>
  static Texture2D QrTexture(string text){
   int colon=text.IndexOf(':');if(colon<1||!int.TryParse(text.Substring(0,colon),out int size)||text.Length<colon+1+size*size)return null;
   const int quiet=3;int n=size+quiet*2;
   var pixels=new Color32[n*n];for(int i=0;i<pixels.Length;i++)pixels[i]=new Color32(255,255,255,255);
   for(int y=0;y<size;y++)for(int x=0;x<size;x++)if(text[colon+1+y*size+x]=='1')pixels[(n-1-(y+quiet))*n+x+quiet]=new Color32(29,43,79,255);
   var texture=new Texture2D(n,n,TextureFormat.RGBA32,false){filterMode=FilterMode.Point,wrapMode=TextureWrapMode.Clamp};
   texture.SetPixels32(pixels);texture.Apply();return texture;
  }
 }
}
