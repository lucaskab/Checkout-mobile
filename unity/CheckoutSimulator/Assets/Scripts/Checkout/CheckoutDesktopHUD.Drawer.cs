using System.Collections.Generic;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 public partial class CheckoutDesktopHUD {
  GameObject drawer;TextMeshProUGUI pageTitle,pageSubtitle;UnityEngine.UI.Image pageIcon;
  CheckoutDesktopButton backButton,closeButton;GameObject chipBar;RectTransform chipContent,cardContent;
  UnityEngine.UI.ScrollRect cardScroll,chipScroll;string shownPage;
  readonly List<CheckoutDesktopButton> chips=new List<CheckoutDesktopButton>();readonly List<CheckoutDesktopCard> cards=new List<CheckoutDesktopCard>();

  // Viewport + content for a ScrollRect; content grows with its layout along the scroll axis.
  static UnityEngine.UI.ScrollRect Scroll(Transform parent,string name,bool vertical,out RectTransform content){
   var node=N.Node(name,parent);var scroll=node.gameObject.AddComponent<UnityEngine.UI.ScrollRect>();
   var viewport=N.Node("Viewport",node);viewport.anchorMin=Vector2.zero;viewport.anchorMax=Vector2.one;viewport.offsetMin=viewport.offsetMax=Vector2.zero;
   var hit=viewport.gameObject.AddComponent<UnityEngine.UI.Image>();hit.color=new Color(0,0,0,0);viewport.gameObject.AddComponent<UnityEngine.UI.RectMask2D>();
   content=N.Node("Content",viewport);
   if(vertical){content.anchorMin=new Vector2(0,1);content.anchorMax=Vector2.one;content.pivot=new Vector2(.5f,1);N.Column(content.gameObject,10,new RectOffset(2,8,2,12));}
   else{content.anchorMin=Vector2.zero;content.anchorMax=new Vector2(0,1);content.pivot=new Vector2(0,.5f);var row=N.Row(content.gameObject,6,new RectOffset(0,0,0,4));row.childControlHeight=true;row.childForceExpandHeight=true;}
   content.offsetMin=content.offsetMax=Vector2.zero;
   var fitter=content.gameObject.AddComponent<UnityEngine.UI.ContentSizeFitter>();
   if(vertical)fitter.verticalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;else fitter.horizontalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;
   scroll.viewport=viewport;scroll.content=content;scroll.horizontal=!vertical;scroll.vertical=vertical;scroll.scrollSensitivity=40;scroll.movementType=UnityEngine.UI.ScrollRect.MovementType.Clamped;
   return scroll;
  }

  void BuildDrawer(){
   var face=Panel(root,"Drawer",0,0,out var edge,out var faceImage,22);drawer=edge.gameObject;faceImage.color=K.Paper;
   Destroy(drawer.GetComponent<UnityEngine.UI.LayoutElement>());edge.raycastTarget=true;
   var rect=(RectTransform)drawer.transform;rect.anchorMin=new Vector2(1,0);rect.anchorMax=Vector2.one;rect.pivot=new Vector2(1,.5f);rect.offsetMin=new Vector2(-600,128);rect.offsetMax=new Vector2(-16,-128);
   N.Column(face.gameObject,10,new RectOffset(14,14,12,10));
   var header=N.Node("Header",face);N.Row(header.gameObject,10);
   backButton=CheckoutDesktopButton.Create(header,46,15,12);backButton.SetWidth(92);backButton.Clicked=Press;
   pageIcon=N.Image(header,"Icon",Color.white,0);pageIcon.preserveAspect=true;var il=pageIcon.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();il.preferredWidth=il.preferredHeight=44;
   var texts=N.Node("Texts",header);N.Column(texts.gameObject,0);texts.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   pageTitle=N.Text(texts,"Title",K.Headline,26,K.Ink);pageTitle.textWrappingMode=TextWrappingModes.NoWrap;pageTitle.overflowMode=TextOverflowModes.Ellipsis;
   pageSubtitle=N.Text(texts,"Subtitle",K.Body,14,K.Muted);
   closeButton=CheckoutDesktopButton.Create(header,46,20,12);closeButton.SetWidth(52);closeButton.Clicked=_=>host.Route("");
   chipScroll=Scroll(face,"Chips",false,out chipContent);chipBar=chipScroll.gameObject;chipBar.AddComponent<UnityEngine.UI.LayoutElement>().preferredHeight=48;
   cardScroll=Scroll(face,"Cards",true,out cardContent);cardScroll.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleHeight=1;
   drawer.SetActive(false);
  }

  void ApplyDrawer(DesktopView v){
   // The shop has its own full-screen window (CheckoutDesktopHUD.Shop).
   bool open=v.hasPage&&(v.page==null||v.page.layout!="shop");
   drawer.SetActive(open);if(!open){shownPage=null;return;}
   var p=v.page;
   pageTitle.text=p.title;pageSubtitle.text=p.subtitle;pageSubtitle.gameObject.SetActive(!string.IsNullOrEmpty(p.subtitle));
   var icon=K.Icon(p.icon);pageIcon.sprite=icon;pageIcon.gameObject.SetActive(icon);
   backButton.gameObject.SetActive(v.canBack);
   backButton.Apply(new DesktopButton{label="Voltar",variant="secondary",enabled=true,route="back",action="",args="[]",after="",ok="",fail=""});
   closeButton.Apply(new DesktopButton{label="X",variant="danger",enabled=true,route="",action="",args="[]",after="",ok="",fail=""});
   var chipData=p.chips??new DesktopButton[0];
   while(chips.Count<chipData.Length){var b=CheckoutDesktopButton.Create(chipContent,40,14,14);b.SetWidth(0);b.Clicked=Press;var l=b.GetComponent<UnityEngine.UI.LayoutElement>();l.flexibleWidth=0;chips.Add(b);}
   for(int i=0;i<chips.Count;i++){bool on=i<chipData.Length;chips[i].gameObject.SetActive(on);if(on){chips[i].Apply(chipData[i]);FitChip(chips[i]);}}
   chipBar.SetActive(chipData.Length>0);
   var cardData=p.cards??new DesktopCard[0];
   while(cards.Count<cardData.Length){var c=N.Create(cardContent);c.Clicked=Press;cards.Add(c);}
   for(int i=0;i<cards.Count;i++){bool on=i<cardData.Length;cards[i].gameObject.SetActive(on);if(on)cards[i].Apply(cardData[i]);}
   // New page (not a filter/stepper swap on the same page): start at the top.
   string key=(p.route??"").Split(':')[0]+"/"+v.canBack;
   if(key!=shownPage){shownPage=key;Canvas.ForceUpdateCanvases();cardScroll.verticalNormalizedPosition=1;chipScroll.horizontalNormalizedPosition=0;}
  }
  // Chips size to their label so long category lists stay compact.
  static void FitChip(CheckoutDesktopButton chip){
   var label=chip.GetComponentInChildren<TextMeshProUGUI>(true);var icon=chip.transform.Find("Face/Icon");
   float width=(label&&label.gameObject.activeSelf?label.GetPreferredValues(chip.Data.label).x:0)+(icon&&icon.gameObject.activeSelf?26:0)+30;
   chip.SetWidth(Mathf.Max(56,width));
  }
 }
}
