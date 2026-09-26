using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // Market day (turn) in the desktop HUD: the day panel in the top bar and the special request alert.
 // Texts come ready from desktop/view.ts; clicks only open the day pages.
 public partial class CheckoutDesktopHUD {
  TextMeshProUGUI dayTitle,dayDetail,requestTitle,requestText,requestTimer;RectTransform dayFill;UnityEngine.UI.Image dayEdge,requestEdge,requestFace;GameObject requestAlert;

  void BuildDayPanel(RectTransform bar){
   var day=Panel(bar,"Day",300,96,out dayEdge,out _);Clickable(dayEdge.gameObject,()=>host.Route(view!=null&&view.dayPhase=="results"?"!day-result":"!day"));
   N.Column(day.gameObject,4,new RectOffset(14,14,8,8));
   var head=N.Node("Head",day);N.Row(head.gameObject,8);
   var icon=N.Image(head,"Icon",Color.white,0);icon.sprite=K.Icon("Icons/clipboard");icon.preserveAspect=true;var il=icon.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();il.preferredWidth=il.preferredHeight=24;
   dayTitle=N.Text(head,"Title",K.Label,15,K.Ink);dayTitle.textWrappingMode=TextWrappingModes.NoWrap;
   Bar(day,12,K.C("2E8CAE"),out dayFill);
   dayDetail=N.Text(day,"Detail",K.Body,13,K.Muted);dayDetail.textWrappingMode=TextWrappingModes.NoWrap;dayDetail.overflowMode=TextOverflowModes.Ellipsis;

   // Floating alert under the top bar while a customer waits with a request.
   var alert=N.Node("RequestAlert",root);alert.anchorMin=alert.anchorMax=alert.pivot=new Vector2(.5f,1);alert.anchoredPosition=new Vector2(0,-122);alert.sizeDelta=new Vector2(620,74);
   requestEdge=alert.gameObject.AddComponent<UnityEngine.UI.Image>();requestEdge.sprite=K.Rounded(18);requestEdge.type=UnityEngine.UI.Image.Type.Sliced;
   Clickable(alert.gameObject,()=>host.Route("!requests"));
   requestFace=N.Image(alert,"Face",Color.white,16);var face=requestFace.rectTransform;face.anchorMin=Vector2.zero;face.anchorMax=Vector2.one;face.offsetMin=new Vector2(2,5);face.offsetMax=new Vector2(-2,-2);
   N.Row(requestFace.gameObject,12,new RectOffset(14,16,6,6));
   var ricon=N.Image(face,"Icon",Color.white,0);ricon.sprite=K.Icon("Icons/customers");ricon.preserveAspect=true;var rl=ricon.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();rl.preferredWidth=rl.preferredHeight=44;
   var texts=N.Node("Texts",face);N.Column(texts.gameObject,0);texts.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   requestTitle=N.Text(texts,"Title",K.Label,15,K.Ink);requestTitle.textWrappingMode=TextWrappingModes.NoWrap;
   requestText=N.Text(texts,"Text",K.Body,14,K.Muted);requestText.textWrappingMode=TextWrappingModes.NoWrap;requestText.overflowMode=TextOverflowModes.Ellipsis;
   requestTimer=N.Text(face,"Action",K.Label,15,K.C("2E8CAE"));requestTimer.textWrappingMode=TextWrappingModes.NoWrap;requestTimer.text="ATENDER ›";
   requestAlert=alert.gameObject;requestAlert.SetActive(false);
  }

  void ApplyDay(DesktopView v){
   dayTitle.text=string.IsNullOrEmpty(v.dayTitle)?"DIA":v.dayTitle;dayDetail.text=v.dayDetail;
   dayFill.anchorMax=new Vector2(Mathf.Clamp01(v.dayProgress),1);
   dayEdge.color=v.dayPhase=="results"?K.C("F2B03D"):v.dayPhase=="planning"?K.C("5DA637"):K.Border;
   requestAlert.SetActive(v.requestCount>0);
   if(v.requestCount>0){
    var tone=K.Tone(v.requestUrgent?"danger":"warning");requestEdge.color=tone.edge;requestFace.color=tone.face;
    requestTitle.text=v.requestCount>1?$"{v.requestCount} CLIENTES PRECISAM DE VOCÊ":"CLIENTE PRECISA DE VOCÊ";requestText.text=v.requestLabel;
    requestAlert.transform.SetAsLastSibling();
   }
  }

  // The market button follows the day: plan and open, close the day, or collect the results.
  DesktopButton MarketButton(DesktopView v){
   if(v.dayPhase=="results")return new DesktopButton{label="Resultado",icon="Icons/trophy",variant="coin",enabled=true,action="",args="[]",route="!day-result",after="",ok="",fail=""};
   if(v.isOpen)return new DesktopButton{label="Fechar",icon="Icons/market",variant="danger",enabled=true,action="closeDay",args="[]",ok="Dia encerrado",route="",after="",fail=""};
   return new DesktopButton{label="Abrir",icon="Icons/market",variant="success",enabled=true,action="",args="[]",route="!day",after="",ok="",fail=""};
  }
 }
}
