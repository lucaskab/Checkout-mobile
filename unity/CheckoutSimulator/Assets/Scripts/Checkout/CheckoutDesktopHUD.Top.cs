using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 public partial class CheckoutDesktopHUD {
  TextMeshProUGUI levelText,progressText,xpText,dailyText,eventName,eventTimer,eventEffect,coinsText,gemsText;
  RectTransform xpFill,dailyFill;GameObject eventPanel;UnityEngine.UI.Image eventEdge,eventFace,eventIcon,dailyEdge;
  CheckoutDesktopButton marketButton,claimButton;

  TextMeshProUGUI Chip(Transform parent,string icon,System.Action onClick){
   var face=Panel(parent,"Chip",150,58,out var edge,out _,18);Clickable(edge.gameObject,onClick);
   N.Row(face.gameObject,8,new RectOffset(10,12,4,4)).childAlignment=TextAnchor.MiddleLeft;
   var image=N.Image(face,"Icon",Color.white,0);image.sprite=K.Icon("Icons/"+icon);image.preserveAspect=true;
   var il=image.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();il.preferredWidth=il.preferredHeight=32;
   var text=N.Text(face,"Value",K.Number,20,K.Ink);text.textWrappingMode=TextWrappingModes.NoWrap;text.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   return text;
  }

  void BuildTop(){
   var bar=N.Node("TopBar",root);bar.anchorMin=new Vector2(0,1);bar.anchorMax=Vector2.one;bar.pivot=new Vector2(.5f,1);bar.offsetMin=new Vector2(16,-112);bar.offsetMax=new Vector2(-16,-14);
   var row=N.Row(bar.gameObject,12);row.childAlignment=TextAnchor.UpperLeft;

   // Level + XP + next unlock. Clicking opens the panel of the next unlock, like the app.
   var level=Panel(bar,"Level",330,96,out var levelEdge,out _);Clickable(levelEdge.gameObject,()=>{if(view!=null)host.Route("!"+view.progressRoute);});
   N.Column(level.gameObject,4,new RectOffset(14,14,8,8));
   var head=N.Node("Head",level);N.Row(head.gameObject,8);
   var crown=N.Image(head,"Crown",Color.white,0);crown.sprite=K.Icon("Icons/crown");crown.preserveAspect=true;var cl=crown.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();cl.preferredWidth=cl.preferredHeight=26;
   levelText=N.Text(head,"Level",K.Headline,20,K.Ink);levelText.textWrappingMode=TextWrappingModes.NoWrap;
   xpText=N.Text(head,"XP",K.Number,14,K.Muted);xpText.alignment=TextAlignmentOptions.Right;xpText.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   Bar(level,12,K.C("8B5C9E"),out xpFill);
   progressText=N.Text(level,"Next",K.Body,14,K.Muted);progressText.textWrappingMode=TextWrappingModes.NoWrap;progressText.overflowMode=TextOverflowModes.Ellipsis;

   BuildDayPanel(bar);

   // Daily goal, with the claim button once it is reached.
   var daily=Panel(bar,"Daily",250,96,out dailyEdge,out _);Clickable(dailyEdge.gameObject,()=>host.Route("!store"));
   N.Column(daily.gameObject,4,new RectOffset(14,14,8,8));
   var dhead=N.Node("Head",daily);N.Row(dhead.gameObject,8);
   var coin=N.Image(dhead,"Coin",Color.white,0);coin.sprite=K.Icon("Icons/coin");coin.preserveAspect=true;var dl=coin.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();dl.preferredWidth=dl.preferredHeight=24;
   var dtitle=N.Text(dhead,"Title",K.Label,15,K.Ink);dtitle.text="META DO DIA";dtitle.textWrappingMode=TextWrappingModes.NoWrap;
   dailyText=N.Text(dhead,"Value",K.Number,14,K.Muted);dailyText.alignment=TextAlignmentOptions.Right;dailyText.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   Bar(daily,12,K.C("F2B03D"),out dailyFill);
   claimButton=CheckoutDesktopButton.Create(daily,30,13,10);claimButton.Clicked=Press;

   // Active event chip, only while an event runs.
   var ev=Panel(bar,"Event",270,96,out eventEdge,out eventFace);eventPanel=eventEdge.gameObject;
   N.Row(ev.gameObject,10,new RectOffset(12,12,8,8));
   eventIcon=N.Image(ev,"Icon",Color.white,0);eventIcon.preserveAspect=true;var el=eventIcon.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();el.preferredWidth=el.preferredHeight=44;
   var etexts=N.Node("Texts",ev);N.Column(etexts.gameObject,1);etexts.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   var ehead=N.Node("Head",etexts);N.Row(ehead.gameObject,6);
   eventName=N.Text(ehead,"Name",K.Label,15,K.Ink);eventName.textWrappingMode=TextWrappingModes.NoWrap;eventName.overflowMode=TextOverflowModes.Ellipsis;eventName.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   eventTimer=N.Text(ehead,"Timer",K.Number,15,K.Ink);eventTimer.textWrappingMode=TextWrappingModes.NoWrap;
   eventEffect=N.Text(etexts,"Effect",K.Body,13,K.Muted);eventEffect.overflowMode=TextOverflowModes.Ellipsis;

   N.Node("Spacer",bar).gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=1;
   var wallet=N.Node("Wallet",bar);N.Column(wallet.gameObject,6);wallet.gameObject.AddComponent<UnityEngine.UI.LayoutElement>().flexibleWidth=0;
   coinsText=Chip(wallet,"coin",()=>host.Route("!dev:moedas"));
   gemsText=Chip(wallet,"diamond",()=>host.Route("!currency"));
   marketButton=CheckoutDesktopButton.Create(bar,96,17,18,true);marketButton.SetWidth(132);marketButton.Clicked=Press;
  }

  void ApplyTop(DesktopView v){
   levelText.text="NÍVEL "+v.level;xpText.text=v.xp+" / "+v.xpGoal+" XP";progressText.text=v.progressLabel;
   xpFill.anchorMax=new Vector2(Mathf.Clamp01(v.xp/(float)Mathf.Max(1,v.xpGoal)),1);
   dailyText.text=v.daily;dailyFill.anchorMax=new Vector2(Mathf.Clamp01(v.dailyProgress),1);
   dailyEdge.color=v.dailyClaimable?K.C("5DA637"):K.Border;
   claimButton.gameObject.SetActive(v.dailyClaimable);
   if(v.dailyClaimable)claimButton.Apply(new DesktopButton{label="Coletar meta",variant="success",enabled=true,action="claimDailyGoal",args="[]",ok="Meta do dia coletada!",route="",after="",fail=""});
   eventPanel.SetActive(v.hasEvent);
   if(v.hasEvent){var tone=K.Tone(v.eventNegative?"danger":"success");eventEdge.color=tone.edge;eventFace.color=tone.face;eventName.text=v.eventName;eventTimer.text=v.eventTimer;eventEffect.text=v.eventEffect;eventIcon.sprite=K.Icon(v.eventIcon);}
   coinsText.text=v.coins;gemsText.text=v.diamonds;
   marketButton.Apply(MarketButton(v));
   ApplyDay(v);
  }
 }
}
