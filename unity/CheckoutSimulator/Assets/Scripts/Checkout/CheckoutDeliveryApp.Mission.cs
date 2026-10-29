using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // The orders in progress as mission cards. The card itself is the list item (so the column gives it its full width)
 // and is at least 360 px tall: a ribbon with the step, the courier avatar with the info line, the road strip with
 // the moto driving from the store to the door (driven by the real progress from CheckoutCourier), and one big
 // action button. The moto is created once and moved in AnimateCards; no layout group touches it, so it cannot flicker.
 public sealed partial class CheckoutDeliveryApp {
  // Road strip geometry (fractions of the road): the store is on the left, the door on the right.
  const float RoadStore=.07f,RoadDoor=.93f,RoadY=.5f;
  const float MissionMinHeight=360f;

  sealed class ActiveView{
   public string id;public RectTransform root,roadNode,moto;public CanvasGroup group;public Image card,ribbonBack,roadFill,courierDisc;
   public TextMeshProUGUI status,courierName,courierInitials,info,meta;public Image[] nodes;public TextMeshProUGUI[] nodeLabels;
   public JuicyButton action;public DeliveryOrder order;public int stage=-1,lastStage=-2;public float motoX=RoadStore,progress;public bool hasBike;
   public string cardFill="";
  }

  // ------------------------------------------------------------------ list
  void SyncActives(DeliveryState d,double now){
   var list=(d.orders??new DeliveryOrder[0]).Where(o=>o!=null&&StageOf(o.status)>0).ToList();
   var keep=new HashSet<string>(list.Select(o=>o.id));
   foreach(var key in actives.Keys.ToList())if(!keep.Contains(key)){
    var gone=actives[key];actives.Remove(key);Retire(gone.root,gone.group,0f);
   }
   for(int i=0;i<list.Count;i++){
    var o=list[i];
    if(!actives.TryGetValue(o.id,out var v)){v=BuildActiveCard(o.id);actives[o.id]=v;StartCoroutine(PopIn(v.root));}
    if(v.root.GetSiblingIndex()!=i)v.root.SetSiblingIndex(i);
    ApplyActive(v,o,now);
   }
   activeEmpty.SetActive(list.Count==0);
   activeCount.text=list.Count.ToString(CultureInfo.InvariantCulture);
  }
  IEnumerator PopIn(RectTransform r){
   if(!r)yield break;
   r.localScale=Vector3.one*.88f;
   yield return U.Scale(r,Vector3.one,.35f,true);
  }

  // ------------------------------------------------------------------ build (once per order)
  ActiveView BuildActiveCard(string id){
   var v=new ActiveView{id=id};
   // The card is the list item: a Panel with a column layout, so the scroll content gives it the full width.
   var card=Panel(activeContent,"Mission",Paper,24);
   v.card=card;v.root=card.rectTransform;
   v.group=v.root.gameObject.AddComponent<CanvasGroup>();
   N.Column(v.root.gameObject,10,new RectOffset(16,16,14,14));
   var sized=Pref(v.root.gameObject,-1,MissionMinHeight);sized.minHeight=MissionMinHeight;
   // Ribbon with the step name.
   v.ribbonBack=Panel(v.root,"Ribbon",Blue,16);Pref(v.ribbonBack.gameObject,-1,46);
   N.Row(v.ribbonBack.gameObject,0,new RectOffset(18,18,4,4)).childAlignment=TextAnchor.MiddleLeft;
   v.status=U.Label(v.ribbonBack.transform,"Status",K.Headline,24,"FFFFFF",TextAlignmentOptions.Left);
   // Head: the courier's avatar, and the order's text.
   var head=N.Node("Head",v.root);N.Row(head.gameObject,14).childAlignment=TextAnchor.MiddleLeft;Pref(head.gameObject,-1,100);
   v.courierDisc=Avatar(head,"Courier",96,out v.courierInitials);
   var tx=N.Node("Texts",head);N.Column(tx.gameObject,2);Pref(tx.gameObject,-1,-1).flexibleWidth=1;
   v.courierName=U.Label(tx,"Courier",K.Headline,26,Ink,TextAlignmentOptions.Left);
   v.info=N.Text(tx,"Info",K.Body,19,K.C(Ink));v.info.alignment=TextAlignmentOptions.Left;Pref(v.info.gameObject,-1,50);
   v.meta=U.Label(tx,"Meta",K.Body,18,Muted,TextAlignmentOptions.Left);
   // Road strip: a fixed area with no layout group, so the moto inside it is only moved by code.
   v.roadNode=N.Node("Road",v.root);Pref(v.roadNode.gameObject,-1,120);
   var bg=Panel(v.roadNode,"Asphalt","9AA6AE",12);U.Stretch(bg.rectTransform,new Vector2(0,RoadY-.12f),new Vector2(1,RoadY+.12f));
   v.roadFill=Panel(v.roadNode,"Done",Green,12);U.Stretch(v.roadFill.rectTransform,new Vector2(0,RoadY-.12f),new Vector2(RoadStore,RoadY+.12f));
   // Dashes down the middle of the road (the road paint), drawn once.
   for(int i=0;i<7;i++){
    float x=RoadStore+(RoadDoor-RoadStore)*(i+.5f)/7f;
    var dash=N.Image(v.roadNode,"Dash",K.C("F4EBDD"),0);dash.sprite=DeliveryArt.Dash;U.At(dash.rectTransform,new Vector2(x,RoadY),new Vector2(26,6),Vector2.zero);
   }
   // Five step names under the road. The step dots on the road are not drawn (author: no dots on the line).
   v.nodes=new Image[StepNames.Length];v.nodeLabels=new TextMeshProUGUI[StepNames.Length];
   for(int i=0;i<StepNames.Length;i++){
    float x=RoadStore+(RoadDoor-RoadStore)*i/(StepNames.Length-1);
    var nd=N.Image(v.roadNode,"Node",K.C(EmptyTone),0);nd.sprite=DeliveryArt.Circle;U.At(nd.rectTransform,new Vector2(x,RoadY),new Vector2(30,30),Vector2.zero);nd.enabled=false;v.nodes[i]=nd;
    var lb=U.Label(v.roadNode,"Label",K.Body,18,Muted,TextAlignmentOptions.Center);U.At(lb.rectTransform,new Vector2(x,.02f),new Vector2(120,24),Vector2.zero);lb.text=StepNames[i];v.nodeLabels[i]=lb;
   }
   // The moto (delivery truck icon), created once; it sits steady over the road and only slides along it.
   var motoImg=N.Image(v.roadNode,"Moto",Color.white,0);motoImg.sprite=DeliveryArt.Moto;motoImg.preserveAspect=true;motoImg.raycastTarget=false;
   U.At(motoImg.rectTransform,new Vector2(RoadStore,RoadY),new Vector2(78,78),new Vector2(0,34));
   v.moto=motoImg.rectTransform;
   // The icon art faces left; the moto rides left to right, so it is mirrored to face where it goes.
   v.moto.localScale=new Vector3(-1,1,1);
   // The one big button of the step: full card width, 70 px.
   v.action=JuicyButton.Create(v.root,"",Blue,"1F6A86",70,24,"Icons/clipboard",false);
   v.action.Clicked=()=>ActionFor(v);
   return v;
  }

  // ------------------------------------------------------------------ apply (4 Hz; no layout churn)
  void ApplyActive(ActiveView v,DeliveryOrder o,double now){
   v.order=o;
   int stage=StageOf(o.status);v.stage=stage;
   string courierName=o.courier!=null&&!string.IsNullOrEmpty(o.courier.name)?o.courier.name:"Motoboy";
   string courierColor=o.courier!=null&&!string.IsNullOrEmpty(o.courier.color)?o.courier.color:Blue;
   int courierSeed=SeedOf(o.courier!=null?o.courier.id:o.id);
   // Courier and customer text.
   v.courierName.text=courierName;
   v.info.text=InfoText(o,now);
   v.meta.text=string.Format("Cliente {0} · {1} · {2}",o.customerName??"",o.neighborhood??"",Km(o.distanceKm));
   v.status.text=StatusText(o.status);
   PaintAvatar(v.courierDisc,v.courierInitials,courierSeed,courierName);
   if(stage!=v.lastStage){
    v.lastStage=stage;
    v.ribbonBack.sprite=DeliveryArt.Flat(stage==3?Green:stage==4?Red:Blue,16);
    string fill=stage==3?"FFF4D6":Paper;   // white card; warm when the motoboy waits at the door
    if(fill!=v.cardFill){v.cardFill=fill;v.card.sprite=DeliveryArt.Flat(fill,24);}
    for(int i=0;i<v.nodes.Length;i++){
     bool done=i<stage,cur=i==stage;
     v.nodes[i].color=K.C(done?Green:cur?Gold:EmptyTone);
     v.nodeLabels[i].color=K.C(cur?Ink:Muted);
     v.nodes[i].rectTransform.localScale=Vector3.one;
    }
    v.roadFill.color=K.C(Green);
   }
   // The one button: pack, or hand over. The rest is a timer, shown but not pressable.
   bool live=stage==1||stage==3;
   v.action.SetText(ActionLabel(o,now));
   v.action.SetFill(stage==3?Green:stage==1?Blue:"9AA0A8",stage==3?"2C7A40":stage==1?"B83A1E":"7B818A");
   v.action.SetEnabled(live);
  }

  // ------------------------------------------------------------------ actions
  void ActionFor(ActiveView v){
   if(v==null||v.order==null||bridge==null)return;
   if(v.order.status=="aceito"){CheckoutPackingGame.Show(v.id);return;}
   if(v.order.status=="moto-na-porta"){
    bridge.Command("handOverDelivery",Q(v.id));
    CheckoutDeliverySound.Play(CheckoutDeliverySound.Sticker,.5f);
    Confetti(v.action.GetComponent<RectTransform>(),10);
    StartCoroutine(U.Pop(v.root,1.03f,.2f));
   }
  }

  // ------------------------------------------------------------------ per-frame motion
  // The moto follows the real progress of its trip (CheckoutCourier) and eases toward it (no bob);
  // the current step pulses by scale. Nothing here touches a layout group.
  void AnimateCards(double now,float t){
   float ease=1f-Mathf.Exp(-Time.unscaledDeltaTime*5f);
   foreach(var v in actives.Values){
    if(v==null||v.order==null||!v.root)continue;
    int stage=v.stage;
    // Real progress from the courier when the bike is on its way; otherwise the store's own estimate.
    float progress=RouteProgress(v.order,now);
    if(stage==4){
     if(CheckoutCourier.TryGetBike(v.id,out var pos,out var p01)){progress=p01;v.hasBike=true;}
     else v.hasBike=false;
    }else v.hasBike=false;
    v.progress=progress;
    float target=stage==4?Mathf.Lerp(RoadStore,RoadDoor,progress):RoadStore;
    v.motoX=Mathf.Lerp(v.motoX,target,ease);
    v.moto.anchorMin=v.moto.anchorMax=new Vector2(v.motoX,RoadY);
    v.moto.anchoredPosition=new Vector2(0,34);
    v.roadFill.rectTransform.anchorMax=new Vector2(v.motoX,RoadY+.12f);
   }
  }
  // The trip's progress by time when the courier's own position is not known: 40 s + 25 s per km, ending at deliverAt.
  static float RouteProgress(DeliveryOrder o,double now){
   if(o==null||o.status!="a-caminho"||o.deliverAt<=0)return 0f;
   double total=(40+25*Math.Max(.6,o.distanceKm))*1000.0;
   return Mathf.Clamp01((float)(1-(o.deliverAt-now)/total));
  }
  static int ItemCount(DeliveryOrder o)=>(o.items??new DeliveryItem[0]).Where(i=>i!=null).Sum(i=>i.quantity);
  static string StatusText(string status){
   switch(status){
    case "aceito":return "Embalando";
    case "aguardando-moto":return "Moto a caminho da loja";
    case "moto-na-porta":return "Motoboy na porta";
    case "a-caminho":return "Saiu para entrega";
    default:return "";
   }
  }
  static bool AtDoor(DeliveryOrder o)=>CheckoutCourier.TryGetBike(o.id,out _,out var p)&&p>=.98f;
  static string InfoText(DeliveryOrder o,double now){
   string who=o.courier!=null&&!string.IsNullOrEmpty(o.courier.name)?o.courier.name:"O motoboy";
   switch(o.status){
    case "aceito":return o.packBy>0?string.Format("Embale em {0} · o embalo vale estrelas",Clock(Secs(o.packBy,now))):"Embale o pedido";
    case "aguardando-moto":return o.arriveAt>0?string.Format("{0} chega em {1}",who,Clock(Secs(o.arriveAt,now))):string.Format("{0} a caminho da loja",who);
    case "moto-na-porta":
     string phrase=Pick(o.courier!=null&&o.courier.phrases!=null?o.courier.phrases.arrive:null,o.id);
     string auto=o.doorSince>0?" · "+string.Format("automática em {0}",Clock(Secs(o.doorSince+MoneyDoorWait,now))):"";
     return "\""+CheckoutI18n.T(phrase)+"\""+auto;
    case "a-caminho":
     // The bike got to the door ahead of time: it is ringing the bell, the customer is coming down.
     if(AtDoor(o))return string.Format("{0} tocou a campainha · {1}",who,Clock(Secs(o.deliverAt,now)));
     return o.deliverAt>0?string.Format("Entrega em {0} · {1}",Clock(Secs(o.deliverAt,now)),Km(o.distanceKm)):string.Format("Saiu para entrega · {0}",Km(o.distanceKm));
    default:return "";
   }
  }
  // The big button of the step: pack, wait for the moto, hand over, or on the way.
  static string ActionLabel(DeliveryOrder o,double now){
   switch(o.status){
    case "aceito":return "Montar pedido";
    case "aguardando-moto":return o.arriveAt>0?"Motoboy chegando · "+Clock(Secs(o.arriveAt,now)):"Motoboy chegando…";
    case "moto-na-porta":return "Entregar ao motoboy";
    case "a-caminho":if(AtDoor(o))return "Na porta do cliente";return o.deliverAt>0?"A caminho · "+Clock(Secs(o.deliverAt,now)):"A caminho";
    default:return "";
   }
  }
 }
}
