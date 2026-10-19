using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // The money makers and the account (desktop/view.ts quickButtons: daily gift, free video, diamond store, "Salvar"
 // until the player signs in) used to stand as a column at the bottom-right. Lucas 19/10 ("a tela está muito
 // lotada"): one corner button, "Bônus" (view.quickMain), with a red count of what is waiting; a tap opens them as a
 // small menu next to it (each with its own pill), a tap outside or on an item closes it. Hidden while a window is
 // open.
 public partial class CheckoutDesktopHUD {
  RectTransform quickRail,quickMenu,quickList;GameObject quickBlocker;CheckoutDesktopButton quickMain;GameObject quickMainBadge;TextMeshProUGUI quickMainBadgeText;
  readonly List<CheckoutDesktopButton> quickButtons=new List<CheckoutDesktopButton>();
  readonly List<GameObject> quickBadges=new List<GameObject>();readonly List<TextMeshProUGUI> quickBadgeTexts=new List<TextMeshProUGUI>();
  bool quickOpen;

  void BuildQuick(){
   quickRail=N.Node("QuickRail",root);quickRail.anchorMin=quickRail.anchorMax=quickRail.pivot=new Vector2(1,0);
   quickRail.anchoredPosition=Phone?new Vector2(-10,112):new Vector2(-18,132);
   var column=N.Column(quickRail.gameObject,Phone?8:10);column.childAlignment=TextAnchor.LowerRight;
   var fitter=quickRail.gameObject.AddComponent<ContentSizeFitter>();fitter.horizontalFit=fitter.verticalFit=ContentSizeFitter.FitMode.PreferredSize;
   quickMain=CheckoutDesktopButton.Create(quickRail,Phone?74:80,13,18,true);quickMain.SetWidth(Phone?92:96);quickMain.Clicked=_=>{Sound("tap",1.05f);SetQuickOpen(!quickOpen);};
   quickMainBadge=QuickPill(quickMain.transform,44,24,13,out quickMainBadgeText);quickMainBadge.AddComponent<CheckoutPulse>();

   // A full-screen catcher under the menu: a tap anywhere else closes it.
   quickBlocker=N.Node("QuickBlocker",root).gameObject;Stretch((RectTransform)quickBlocker.transform,new Vector2(-2000,-2000),new Vector2(2000,2000));
   var catcher=quickBlocker.AddComponent<Image>();catcher.color=new Color(0,0,0,0);Clickable(quickBlocker,()=>SetQuickOpen(false));
   // The menu: a cream card to the left of the corner button, bottom-aligned with it.
   var edge=N.Image(root,"QuickMenu",K.Border,20);quickMenu=edge.rectTransform;quickMenu.anchorMin=quickMenu.anchorMax=quickMenu.pivot=new Vector2(1,0);
   var face=N.Image(edge.transform,"Face",K.Cream,18);Stretch(face.rectTransform,new Vector2(3,6),new Vector2(-3,-3));
   quickList=N.Node("Items",face.transform);Stretch(quickList,new Vector2(10,10),new Vector2(-10,-10));
   var list=N.Column(quickList.gameObject,Phone?8:10);list.childAlignment=TextAnchor.UpperCenter;
   SetQuickOpen(false);
  }

  GameObject QuickPill(Transform parent,float w,float h,float font,out TextMeshProUGUI text){
   var pill=N.Image(parent,"Pill",K.C("E15533"),11);var rect=pill.rectTransform;rect.anchorMin=rect.anchorMax=rect.pivot=Vector2.one;rect.anchoredPosition=new Vector2(6,6);rect.sizeDelta=new Vector2(w,h);
   text=N.Text(pill.transform,"Text",K.Number,font,Color.white);text.alignment=TextAlignmentOptions.Center;var tr=text.rectTransform;tr.anchorMin=Vector2.zero;tr.anchorMax=Vector2.one;tr.offsetMin=tr.offsetMax=Vector2.zero;
   return pill.gameObject;
  }

  void SetQuickOpen(bool open){
   quickOpen=open;quickBlocker.SetActive(open);quickMenu.gameObject.SetActive(open);
   // The count rides on the corner button only while the menu is closed (open, each item shows its own).
   if(quickMainBadge)quickMainBadge.SetActive(!open&&quickMain.Data!=null&&!string.IsNullOrEmpty(quickMain.Data.badge));
   if(!open)return;
   // On top of the HUD (toolbar, top bar), right next to the corner button.
   quickBlocker.transform.SetAsLastSibling();quickMenu.SetAsLastSibling();
   float w=Phone?250:270,itemH=Phone?62:66,gap=Phone?8:10;int n=0;foreach(var b in quickButtons)if(b.gameObject.activeSelf)n++;
   quickMenu.sizeDelta=new Vector2(w,20+n*itemH+Mathf.Max(0,n-1)*gap+9);
   quickMenu.anchoredPosition=quickRail.anchoredPosition+new Vector2(-((RectTransform)quickMain.transform).rect.width-(Phone?10:14),0);
   StartCoroutine(CheckoutUiKit.Pop(quickMenu,1.05f,.16f));
  }

  void ApplyQuick(DesktopView v){
   var items=v.quick??new DesktopButton[0];
   bool shown=!v.hasPage&&items.Length>0;
   quickRail.gameObject.SetActive(shown);
   if(!shown&&quickOpen)SetQuickOpen(false);
   if(v.quickMain!=null){
    quickMain.Apply(v.quickMain);
    var badge=v.quickMain.badge??"";quickMainBadge.SetActive(badge.Length>0&&!quickOpen);quickMainBadgeText.text=badge;
   }
   while(quickButtons.Count<items.Length){
    var b=CheckoutDesktopButton.Create(quickList,Phone?62:66,Phone?19:20,16);
    b.Clicked=x=>{SetQuickOpen(false);Press(x);};quickButtons.Add(b);
    var pill=QuickPill(b.transform,70,24,13,out var text);pill.AddComponent<CheckoutPulse>();
    quickBadges.Add(pill);quickBadgeTexts.Add(text);
   }
   for(int i=0;i<quickButtons.Count;i++){
    bool on=i<items.Length;quickButtons[i].gameObject.SetActive(on);if(!on)continue;
    quickButtons[i].Apply(items[i]);
    var badge=items[i].badge??"";quickBadges[i].SetActive(badge.Length>0);quickBadgeTexts[i].text=badge;
    quickBadges[i].GetComponent<Image>().color=badge=="Grátis"?K.C("2E9E44"):K.C("E15533");
   }
  }
 }

 /// <summary>A gentle breathing scale for "something is waiting here" pills.</summary>
 public sealed class CheckoutPulse:MonoBehaviour {
  void Update(){float s=1+.08f*Mathf.Sin(Time.unscaledTime*5.5f);transform.localScale=new Vector3(s,s,1);}
 }
}
