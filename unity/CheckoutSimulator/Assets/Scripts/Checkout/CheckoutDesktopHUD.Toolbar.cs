using System.Collections.Generic;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 public partial class CheckoutDesktopHUD {
  RectTransform toolbar;
  readonly List<CheckoutDesktopButton> tools=new List<CheckoutDesktopButton>();
  readonly List<GameObject> toolBadges=new List<GameObject>();readonly List<TextMeshProUGUI> toolBadgeTexts=new List<TextMeshProUGUI>();

  void BuildToolbar(){
   toolbar=N.Node("Toolbar",root);toolbar.anchorMin=toolbar.anchorMax=new Vector2(.5f,0);toolbar.pivot=new Vector2(.5f,0);toolbar.anchoredPosition=new Vector2(0,14);
   var row=N.Row(toolbar.gameObject,8,new RectOffset(10,10,10,10));row.childAlignment=TextAnchor.MiddleCenter;
   var fitter=toolbar.gameObject.AddComponent<UnityEngine.UI.ContentSizeFitter>();fitter.horizontalFit=fitter.verticalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;
   var back=toolbar.gameObject.AddComponent<UnityEngine.UI.Image>();back.sprite=K.Rounded(22);back.type=UnityEngine.UI.Image.Type.Sliced;back.color=new Color(.29f,.21f,.14f,.35f);
  }
  void ApplyToolbar(DesktopView v){
   var items=v.tools??new DesktopButton[0];
   while(tools.Count<items.Length){
    var b=CheckoutDesktopButton.Create(toolbar,84,13,16,true);b.SetWidth(94);b.Clicked=ToolPressed;tools.Add(b);
    // Small pill in the corner: lock level or claimable count.
    var pill=N.Image(b.transform,"Pill",K.C("F2B03D"),11);var rect=pill.rectTransform;rect.anchorMin=rect.anchorMax=rect.pivot=Vector2.one;rect.anchoredPosition=new Vector2(4,4);rect.sizeDelta=new Vector2(38,22);
    var text=N.Text(pill.transform,"Text",K.Number,12,K.Ink);text.alignment=TextAlignmentOptions.Center;var tr=text.rectTransform;tr.anchorMin=Vector2.zero;tr.anchorMax=Vector2.one;tr.offsetMin=tr.offsetMax=Vector2.zero;
    toolBadges.Add(pill.gameObject);toolBadgeTexts.Add(text);
   }
   for(int i=0;i<tools.Count;i++){
    bool on=i<items.Length;tools[i].gameObject.SetActive(on);if(!on)continue;tools[i].Apply(items[i]);
    string pill=!items[i].enabled?LockLevel(items[i].fail):!string.IsNullOrEmpty(items[i].badge)?items[i].badge:items[i].route=="!missions"&&v.claimableMissions>0?v.claimableMissions.ToString():"";
    toolBadges[i].SetActive(pill.Length>0);toolBadgeTexts[i].text=pill;
    toolBadges[i].GetComponent<UnityEngine.UI.Image>().color=items[i].enabled?K.C("E15533"):K.C("F2B03D");toolBadgeTexts[i].color=items[i].enabled?Color.white:K.Ink;
   }
  }
  static string LockLevel(string fail){var digits=new System.Text.StringBuilder();foreach(char c in fail??"")if(char.IsDigit(c))digits.Append(c);return digits.Length>0?"Nv"+digits:"";}
  // Clicking the open tool again closes the drawer.
  void ToolPressed(CheckoutDesktopButton button){if(button.Data!=null&&button.Data.active&&button.Data.enabled)host.Route("");else Press(button);}
 }
}
