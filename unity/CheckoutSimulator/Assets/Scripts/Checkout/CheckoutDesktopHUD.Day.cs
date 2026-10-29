using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // Market day (turn) in the desktop HUD: the day panel in the top bar.
 // Texts come ready from desktop/view.ts; clicks only open the day pages.
 public partial class CheckoutDesktopHUD {
  TextMeshProUGUI dayTitle,dayDetail;RectTransform dayFill;UnityEngine.UI.Image dayEdge;

  void BuildDayPanel(RectTransform bar){
   var day=Panel(bar,"Day",Phone?230:300,CardHeight,out dayEdge,out _);Clickable(dayEdge.gameObject,()=>host.Route(view!=null&&view.dayPhase=="results"?"!day-result":"!day"));
   N.Column(day.gameObject,Phone?2:4,Phone?new RectOffset(12,12,5,5):new RectOffset(14,14,8,8));
   var head=N.Node("Head",day);N.Row(head.gameObject,8);
   var icon=N.Image(head,"Icon",Color.white,0);icon.sprite=K.Icon("Icons/clipboard");icon.preserveAspect=true;var il=icon.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();il.preferredWidth=il.preferredHeight=24;
   dayTitle=N.Text(head,"Title",K.Label,15,K.Ink);dayTitle.textWrappingMode=TextWrappingModes.NoWrap;
   Bar(day,12,K.C("2E8CAE"),out dayFill);
   dayDetail=N.Text(day,"Detail",K.Body,13,K.Muted);dayDetail.textWrappingMode=TextWrappingModes.NoWrap;dayDetail.overflowMode=TextOverflowModes.Ellipsis;
   dayDetail.gameObject.SetActive(!Phone); // "Resultados prontos..." repeats the Resultados button
  }

  void ApplyDay(DesktopView v){
   dayTitle.text=string.IsNullOrEmpty(v.dayTitle)?"DIA":v.dayTitle;dayDetail.text=v.dayDetail;
   dayFill.anchorMax=new Vector2(Mathf.Clamp01(v.dayProgress),1);
   dayEdge.color=v.dayPhase=="results"?K.C("F2B03D"):v.dayPhase=="planning"?K.C("5DA637"):K.Border;
  }

  // The market button follows the day: plan and open, close the day, or collect the results.
  DesktopButton MarketButton(DesktopView v){
   if(v.dayPhase=="results")return new DesktopButton{label="Resultado",icon="Icons/trophy",variant="coin",enabled=true,action="",args="[]",route="!day-result",after="",ok="",fail=""};
   if(v.isOpen)return new DesktopButton{label="Fechar",icon="Icons/market",variant="danger",enabled=true,action="closeDay",args="[]",ok="Dia encerrado",route="",after="",fail=""};
   return new DesktopButton{label="Abrir",icon="Icons/market",variant="success",enabled=true,action="",args="[]",route="!day",after="",ok="",fail=""};
  }
 }
}
