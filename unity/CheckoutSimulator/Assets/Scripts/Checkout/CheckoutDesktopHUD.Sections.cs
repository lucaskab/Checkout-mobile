using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // Big header tabs for the windows of a toolbar group (page.sections, desktop/sections.ts; Lucas 19/10 "a HUD está
 // muito lotada"): one toolbar button "Produtos" opens Prateleiras · Estoque · Entregas, "Missões" opens Missões ·
 // Conquistas. The tabs take the place of the window title, in the header band; the open one is gold. Switching
 // tabs swaps the window without the opening pop, so it reads as one window.
 public partial class CheckoutDesktopHUD {
  sealed class SectionBar {
   public RectTransform row;public readonly List<CheckoutDesktopButton> buttons=new List<CheckoutDesktopButton>();
   public readonly List<GameObject> badges=new List<GameObject>();public readonly List<TextMeshProUGUI> badgeTexts=new List<TextMeshProUGUI>();
   public readonly List<bool> open=new List<bool>();
  }
  // Set when a header tab was pressed: the next window to open is a sibling, so it skips the pop.
  bool sectionHop;

  SectionBar MakeSections(Transform titles){
   var bar=new SectionBar();bar.row=N.Node("Sections",titles);
   var h=N.Row(bar.row.gameObject,Phone?8:10);h.childAlignment=TextAnchor.MiddleLeft;
   var le=bar.row.gameObject.AddComponent<LayoutElement>();le.preferredHeight=SectionH+8;
   bar.row.gameObject.SetActive(false);
   return bar;
  }
  static float SectionH=>Phone?44:52;

  /// <summary>Shows the tabs (and hides the title) when the page has sections; returns whether it does.</summary>
  bool ApplySections(SectionBar bar,DesktopButton[] sections,TextMeshProUGUI title,TextMeshProUGUI subtitle,bool subtitleShown){
   bool on=sections!=null&&sections.Length>0;
   bar.row.gameObject.SetActive(on);
   title.gameObject.SetActive(!on);subtitle.gameObject.SetActive(!on&&subtitleShown);
   if(!on)return false;
   while(bar.buttons.Count<sections.Length){
    var b=CheckoutDesktopButton.Create(bar.row,SectionH,Phone?18:20,16);
    int index=bar.buttons.Count;
    b.Clicked=x=>{if(bar.open[index])return;Sound("tap",1.1f);sectionHop=true;Press(x);};
    var pill=N.Image(b.transform,"Badge",K.C("E15533"),11);var pr=pill.rectTransform;pr.anchorMin=pr.anchorMax=pr.pivot=Vector2.one;pr.anchoredPosition=new Vector2(6,8);pr.sizeDelta=new Vector2(30,24);
    var t=N.Text(pill.transform,"Text",K.Number,14,Color.white);t.alignment=TextAlignmentOptions.Center;Stretch(t.rectTransform,Vector2.zero,Vector2.zero);
    pill.gameObject.AddComponent<CheckoutPulse>();
    bar.buttons.Add(b);bar.badges.Add(pill.gameObject);bar.badgeTexts.Add(t);bar.open.Add(false);
   }
   for(int i=0;i<bar.buttons.Count;i++){
    bool shown=i<sections.Length;bar.buttons[i].gameObject.SetActive(shown);if(!shown)continue;
    var s=sections[i];bar.open[i]=s.active;
    // The open tab in full gold (the "active" style is the pale one of the small tabs below it).
    bar.buttons[i].Apply(new DesktopButton{label=s.label,icon=s.icon,variant=s.active?"coin":"secondary",enabled=true,active=false,action=s.action,args=s.args,route=s.route,after=s.after,ok=s.ok,fail=s.fail,badge=s.badge});
    var label=bar.buttons[i].GetComponentInChildren<TextMeshProUGUI>(true);
    float width=(label?label.GetPreferredValues(K.Clean(s.label)).x:90)+(string.IsNullOrEmpty(s.icon)?0:SectionH*.5f+6)+30;
    bar.buttons[i].SetWidth(Mathf.Max(Phone?110:140,width));
    // The open tab sits a little higher, like a pulled folder tab.
    bar.buttons[i].transform.localScale=s.active?Vector3.one*1.04f:Vector3.one;
    bool badge=!string.IsNullOrEmpty(s.badge)&&!s.active;bar.badges[i].SetActive(badge);
    if(badge)bar.badgeTexts[i].text=s.badge;
   }
   return true;
  }

  /// <summary>True once per tab switch: the window that opens skips its pop (it is the same window).</summary>
  bool TakeSectionHop(){bool hop=sectionHop;sectionHop=false;return hop;}
 }
}
