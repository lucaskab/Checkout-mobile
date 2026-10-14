using System.Collections.Generic;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // Side buttons always on screen (desktop/view.ts quickButtons, Lucas 14/10 "está muito escondido"): the daily
 // gift, the free video (plays at once when one is ready), the diamond store and "Salvar" (Google sign-in) until the
 // player signs in. A column at the bottom-right corner, above the toolbar; a red pill marks what is waiting and it
 // breathes so the eye finds it. Hidden while a window is open.
 public partial class CheckoutDesktopHUD {
  RectTransform quickRail;
  readonly List<CheckoutDesktopButton> quickButtons=new List<CheckoutDesktopButton>();
  readonly List<GameObject> quickBadges=new List<GameObject>();readonly List<TextMeshProUGUI> quickBadgeTexts=new List<TextMeshProUGUI>();

  void BuildQuick(){
   quickRail=N.Node("QuickRail",root);quickRail.anchorMin=quickRail.anchorMax=quickRail.pivot=new Vector2(1,0);
   quickRail.anchoredPosition=Phone?new Vector2(-10,112):new Vector2(-18,132);
   var column=N.Column(quickRail.gameObject,Phone?8:10);column.childAlignment=TextAnchor.LowerRight;
   var fitter=quickRail.gameObject.AddComponent<UnityEngine.UI.ContentSizeFitter>();fitter.horizontalFit=fitter.verticalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;
  }
  void ApplyQuick(DesktopView v){
   var items=v.quick??new DesktopButton[0];
   quickRail.gameObject.SetActive(!v.hasPage&&items.Length>0);
   while(quickButtons.Count<items.Length){
    var b=CheckoutDesktopButton.Create(quickRail,Phone?74:80,13,18,true);b.SetWidth(Phone?92:96);b.Clicked=Press;quickButtons.Add(b);
    var pill=N.Image(b.transform,"Pill",K.C("E15533"),11);var rect=pill.rectTransform;rect.anchorMin=rect.anchorMax=rect.pivot=Vector2.one;rect.anchoredPosition=new Vector2(6,6);rect.sizeDelta=new Vector2(44,24);
    var text=N.Text(pill.transform,"Text",K.Number,13,Color.white);text.alignment=TextAlignmentOptions.Center;var tr=text.rectTransform;tr.anchorMin=Vector2.zero;tr.anchorMax=Vector2.one;tr.offsetMin=tr.offsetMax=Vector2.zero;
    pill.gameObject.AddComponent<CheckoutPulse>();
    quickBadges.Add(pill.gameObject);quickBadgeTexts.Add(text);
   }
   for(int i=0;i<quickButtons.Count;i++){
    bool on=i<items.Length;quickButtons[i].gameObject.SetActive(on);if(!on)continue;
    quickButtons[i].Apply(items[i]);
    var badge=items[i].badge??"";quickBadges[i].SetActive(badge.Length>0);quickBadgeTexts[i].text=badge;
    quickBadges[i].GetComponent<UnityEngine.UI.Image>().color=badge=="Grátis"?K.C("2E9E44"):K.C("E15533");
   }
  }
 }

 /// <summary>A gentle breathing scale for "something is waiting here" pills.</summary>
 public sealed class CheckoutPulse:MonoBehaviour {
  void Update(){float s=1+.08f*Mathf.Sin(Time.unscaledTime*5.5f);transform.localScale=new Vector3(s,s,1);}
 }
}
