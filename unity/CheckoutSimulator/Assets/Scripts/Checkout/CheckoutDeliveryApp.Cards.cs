using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // The columns of the Delivery app: offer tickets (left), the missions in progress (middle, see
 // CheckoutDeliveryApp.Mission.cs) and the city map with the recent deliveries (right). Cards are pooled by order
 // id and updated in place.
 public sealed partial class CheckoutDeliveryApp {
  const float OfferHeight=300f;
  RectTransform mapLayer;

  sealed class OfferView{
   public string id;public RectTransform root,slide,items;public CanvasGroup group;public Image avatarDisc,ringFill,noteBack,stickerBurst;
   public TextMeshProUGUI avatarInitials,name,meta,payout,note,ring;public GameObject noteStrip,stickerNode;
   public string itemSig="";public JuicyButton accept,decline;public double total;public bool answered;public Tilt tilt;
  }

  // Tilts a ticket a little under the pointer and springs it back when the pointer leaves.
  public sealed class Tilt:MonoBehaviour,IPointerEnterHandler,IPointerExitHandler {
   float target,angle;
   public void OnPointerEnter(PointerEventData e){target=-1.6f;}
   public void OnPointerExit(PointerEventData e){target=0f;}
   void Update(){
    angle=Mathf.Lerp(angle,target,1f-Mathf.Exp(-Time.unscaledDeltaTime*14f));
    transform.localRotation=Quaternion.Euler(0,0,angle);
   }
  }

  // ------------------------------------------------------------------ columns
  void BuildOffersColumn(RectTransform row,float weight){
   var left=N.Node("Offers",row);N.Column(left.gameObject,10);Pref(left.gameObject,-1,-1).flexibleWidth=weight;
   SectionHead(left,"Novos pedidos",out offersCount);
   var view=ScrollArea(left,"OffersView",out offersContent);
   Pref(view.gameObject,-1,-1).flexibleHeight=1;
   N.Column(offersContent.gameObject,14,new RectOffset(4,8,4,8));Fit(offersContent);
   offersEmpty=Empty(offersContent,K.Icon("Icons/smartphone"),"Nenhum pedido agora","Novos pedidos chegam em instantes, enquanto a loja estiver aberta.",220);
  }
  void BuildActiveColumn(RectTransform row,float weight){
   var right=N.Node("Active",row);N.Column(right.gameObject,10);Pref(right.gameObject,-1,-1).flexibleWidth=weight;
   SectionHead(right,"Em andamento",out activeCount);
   var view=ScrollArea(right,"ActiveView",out activeContent);
   Pref(view.gameObject,-1,-1).flexibleHeight=1;
   N.Column(activeContent.gameObject,14,new RectOffset(4,8,4,8));Fit(activeContent);
   activeEmpty=Empty(activeContent,DeliveryArt.Moto,"Aceite um pedido para começar","Monte o pedido, entregue ao motoboy e ganhe estrelas e gorjeta.",220);
  }
  void BuildSideColumn(RectTransform row,float weight){
   var side=N.Node("Side",row);N.Column(side.gameObject,10);Pref(side.gameObject,-1,-1).flexibleWidth=weight;
   var mapHead=N.Node("MapHead",side);N.Row(mapHead.gameObject,10).childAlignment=TextAnchor.MiddleLeft;Pref(mapHead.gameObject,-1,50);
   var ribbon=Panel(mapHead,"Ribbon",Blue,16);N.Row(ribbon.gameObject,0,new RectOffset(18,18,4,4)).childAlignment=TextAnchor.MiddleLeft;Pref(ribbon.gameObject,-1,50).flexibleWidth=1;
   U.Label(ribbon.transform,"Title",K.Headline,26,"FFFFFF",TextAlignmentOptions.Left).text="Mapa da cidade";
   BuildMap(side);
   var histHead=N.Node("HistoryHead",side);N.Row(histHead.gameObject,10).childAlignment=TextAnchor.MiddleLeft;Pref(histHead.gameObject,-1,40);
   U.Label(histHead,"Title",K.Headline,24,Ink,TextAlignmentOptions.Left).text="Últimas entregas";
   var histView=ScrollArea(side,"HistoryView",out historyContent);
   Pref(histView.gameObject,-1,-1).flexibleHeight=1;
   N.Column(historyContent.gameObject,8,new RectOffset(0,6,2,6));Fit(historyContent);
   historyEmpty=Empty(historyContent,K.Icon("Icons/medal"),"Sem entregas ainda","As entregas feitas aparecem aqui, com estrelas e gorjeta.",200);
  }

  // ------------------------------------------------------------------ offers
  void SyncOffers(DeliveryState d,double now){
   var list=(d.orders??new DeliveryOrder[0]).Where(o=>o!=null&&o.status=="oferta").OrderBy(o=>o.expiresAt).ToList();
   var keep=new HashSet<string>(list.Select(o=>o.id));
   foreach(var key in offers.Keys.ToList())if(!keep.Contains(key)){var gone=offers[key];offers.Remove(key);Retire(gone.root,gone.group,-120f);}
   bool looking=CheckoutSupplierShop.Instance&&CheckoutSupplierShop.Instance.DeliveryShown;
   for(int i=0;i<list.Count;i++){
    var o=list[i];
    if(!offers.TryGetValue(o.id,out var v)){
     // A new card while the app is open chimes; the first cards of a visit are just shown.
     if(looking&&offers.Count>0)CheckoutDeliverySound.Play(CheckoutDeliverySound.Chime,.4f);
     v=BuildOfferCard(o.id);offers[o.id]=v;StartCoroutine(Enter(v.slide,v.group));
    }
    if(v.root.GetSiblingIndex()!=i)v.root.SetSiblingIndex(i);
    ApplyOffer(v,o,now);
   }
   offersEmpty.SetActive(list.Count==0);
   offersCount.text=list.Count.ToString(CultureInfo.InvariantCulture);
  }
  // A collectible ticket, 300 px tall, four rows: the customer (avatar, name, bairro and km, countdown ring), the items,
  // the note (only when there is one), and the buttons (gold payout pill, quiet decline, big accept). It stays still
  // under the pointer.
  OfferView BuildOfferCard(string id){
   var v=new OfferView{id=id};
   v.root=N.Node("Offer",offersContent);v.group=v.root.gameObject.AddComponent<CanvasGroup>();Pref(v.root.gameObject,-1,OfferHeight);
   v.slide=Panel(v.root,"Ticket",Paper,18).rectTransform;U.Stretch(v.slide,Vector2.zero,Vector2.one);
   v.slide.GetComponent<Image>().raycastTarget=true;
   N.Column(v.slide.gameObject,10,new RectOffset(14,14,16,12));
   // Row 1: avatar, name and neighbourhood, countdown ring.
   var head=N.Node("Head",v.slide);N.Row(head.gameObject,12,new RectOffset(4,0,0,0)).childAlignment=TextAnchor.MiddleLeft;Pref(head.gameObject,-1,70);
   v.avatarDisc=Avatar(head,"Avatar",70,out v.avatarInitials);
   var tx=N.Node("Texts",head);N.Column(tx.gameObject,0);Pref(tx.gameObject,-1,-1).flexibleWidth=1;
   v.name=U.Label(tx,"Name",K.Headline,24,Ink,TextAlignmentOptions.Left);
   v.meta=U.Label(tx,"Meta",K.Body,18,Muted,TextAlignmentOptions.Left);
   var ring=N.Node("Ring",head);Pref(ring.gameObject,62,62);
   var back=N.Image(ring,"Back",K.C(EmptyTone),0);back.sprite=DeliveryArt.Ring;U.Stretch(back.rectTransform,Vector2.zero,Vector2.one);
   v.ringFill=N.Image(ring,"Fill",K.C(Green),0);v.ringFill.sprite=DeliveryArt.Ring;U.Stretch(v.ringFill.rectTransform,Vector2.zero,Vector2.one);
   v.ringFill.type=Image.Type.Filled;v.ringFill.fillMethod=Image.FillMethod.Radial360;v.ringFill.fillOrigin=2;v.ringFill.fillAmount=1;
   v.ring=U.Label(ring,"Text",K.Number,15,Ink);U.Stretch(v.ring.rectTransform,Vector2.zero,Vector2.one);
   // Row 2: the items, as product pictures with a quantity badge.
   v.items=N.Node("Items",v.slide);N.Row(v.items.gameObject,10).childAlignment=TextAnchor.MiddleLeft;Pref(v.items.gameObject,-1,66);
   // Row 3: the note on a sticky strip (hidden when the customer wrote nothing).
   var noteBack=Panel(v.slide.transform,"NoteBack","FFF1B8",12);N.Row(noteBack.gameObject,0,new RectOffset(12,12,4,4)).childAlignment=TextAnchor.MiddleLeft;Pref(noteBack.gameObject,-1,38);
   v.noteBack=noteBack;v.noteStrip=noteBack.gameObject;
   v.note=U.Label(noteBack.transform,"Note",K.Body,18,Ink,TextAlignmentOptions.Left);Pref(v.note.gameObject,-1,-1).flexibleWidth=1;
   // Row 4: the gold payout pill, the quiet decline, the big accept.
   var btns=N.Node("Buttons",v.slide);N.Row(btns.gameObject,10).childAlignment=TextAnchor.MiddleCenter;Pref(btns.gameObject,-1,64);
   var pay=Panel(btns,"Payout",Gold,20);N.Row(pay.gameObject,8,new RectOffset(14,14,4,4)).childAlignment=TextAnchor.MiddleCenter;Pref(pay.gameObject,176,64);
   U.Label(pay.transform,"Label",K.Body,18,Ink,TextAlignmentOptions.Left).text="Ganho";
   LayImg(pay.transform,"Coin","Icons/coin",28,28);
   v.payout=U.Label(pay.transform,"Value",K.Headline,24,Ink,TextAlignmentOptions.Left);
   v.decline=JuicyButton.Create(btns,"Recusar",ScreenTone,"D9DCE0",64,20,null,false,Ink);v.decline.Clicked=()=>Answer(v,false);
   Pref(v.decline.gameObject,110,-1).flexibleWidth=0;
   v.accept=JuicyButton.Create(btns,"Aceitar",Green,"2C7A40",64,26,"Icons/success",true);v.accept.Clicked=()=>Answer(v,true);
   Pref(v.accept.gameObject,-1,64).minWidth=150;
   v.total=1;
   return v;
  }
  void ApplyOffer(OfferView v,DeliveryOrder o,double now){
   v.total=o.createdAt>0&&o.expiresAt>o.createdAt?o.expiresAt-o.createdAt:90000;
   double left=o.expiresAt-now;double share=Math.Max(0,Math.Min(1,left/Math.Max(1000,v.total)));
   v.ringFill.fillAmount=(float)share;
   v.ringFill.color=K.C(share>.4?Green:share>.15?Gold:Red);
   v.ring.text=Short(left/1000.0);
   PaintAvatar(v.avatarDisc,v.avatarInitials,o.avatar,o.customerName);
   v.name.text=o.customerName??"";
   v.meta.text=(o.neighborhood??"")+" · "+Km(o.distanceKm);
   v.payout.text=Money(Mathf.RoundToInt(o.itemsValue+o.fee));
   bool hasNote=!string.IsNullOrEmpty(o.note);
   v.noteStrip.SetActive(hasNote);
   // Without a note the ticket is shorter (no empty band under the buttons).
   var le=v.root.GetComponent<LayoutElement>();if(le){float h=hasNote?OfferHeight:OfferHeight-48f;le.minHeight=h;le.preferredHeight=h;}
   if(hasNote)v.note.text="\""+o.note+"\"";
   string sig=string.Join(",",(o.items??new DeliveryItem[0]).Where(i=>i!=null).Select(i=>i.productId+"x"+i.quantity).ToArray());
   if(sig!=v.itemSig){v.itemSig=sig;BuildItems(v.items,o.items);}
   v.accept.SetEnabled(!v.answered);v.decline.SetEnabled(!v.answered);
  }
  // Product pictures (56 px) with a quantity badge in the corner; four at most, then "+n".
  void BuildItems(RectTransform row,DeliveryItem[] items){
   for(int i=row.childCount-1;i>=0;i--)Destroy(row.GetChild(i).gameObject);
   var list=items??new DeliveryItem[0];
   for(int i=0;i<list.Length&&i<4;i++){
    var it=list[i];if(it==null)continue;
    var pair=N.Node("Item",row);Pref(pair.gameObject,62,62);
    var pic=SpriteImg(pair,"Product",K.Icon("Products/product-"+it.productId.ToString("000",CultureInfo.InvariantCulture)),Color.white,56,56);
    U.At(pic.rectTransform,new Vector2(.5f,.5f),new Vector2(56,56),Vector2.zero);
    var badge=Panel(pair,"Badge",Blue,10);U.At(badge.rectTransform,new Vector2(1,0),new Vector2(42,24),new Vector2(-2,2));
    var qty=U.Label(badge.transform,"Qty",K.Number,16,"FFFFFF");U.Stretch(qty.rectTransform,Vector2.zero,Vector2.one);
    qty.text="x"+it.quantity.ToString(CultureInfo.InvariantCulture);
   }
   if(list.Length>4)U.Label(row,"More",K.Body,18,Muted,TextAlignmentOptions.Left).text="+"+(list.Length-4).ToString(CultureInfo.InvariantCulture);
  }
  void Answer(OfferView v,bool accept){
   if(v==null||v.answered||bridge==null)return;
   v.answered=true;
   if(accept){
    bridge.Command("acceptDeliveryOrder",Q(v.id));
    CheckoutDeliverySound.Play(CheckoutDeliverySound.Accept,.5f);
    Coins(v.payout.rectTransform,8);
    StartCoroutine(U.Pop(v.root,1.05f,.25f));
   }else{
    bridge.Command("declineDeliveryOrder",Q(v.id));
    CheckoutDeliverySound.Play(CheckoutDeliverySound.Decline,.4f);
   }
   // A command the store refuses leaves the card answerable again.
   StartCoroutine(Unlock(v));
  }
  IEnumerator Unlock(OfferView v){yield return new WaitForSecondsRealtime(4f);if(v!=null)v.answered=false;}
  // Removes a card: it leaves the layout at once and slides/fades out.
  void Retire(RectTransform r,CanvasGroup g,float dx){
   if(!r)return;
   var le=r.GetComponent<LayoutElement>();if(!le)le=r.gameObject.AddComponent<LayoutElement>();le.ignoreLayout=true;
   StartCoroutine(Leave(r,g,dx));
  }
  IEnumerator Leave(RectTransform r,CanvasGroup g,float dx){
   Vector2 from=r.anchoredPosition;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.3f){
    if(!r)yield break;
    float e=t*t;
    if(g)g.alpha=1-e;
    r.anchoredPosition=from+new Vector2(dx*e,0);
    yield return null;
   }
   if(r)Destroy(r.gameObject);
  }
  // A new ticket slides in from the left with a bounce while it fades in.
  IEnumerator Enter(RectTransform slide,CanvasGroup g){
   if(!slide||!g)yield break;
   slide.anchoredPosition=new Vector2(-160,0);g.alpha=0;
   var move=StartCoroutine(U.Move(slide,Vector2.zero,.5f,true));
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.3f){if(!slide||!g)yield break;g.alpha=Ease(t);yield return null;}
   if(g)g.alpha=1;
   yield return move;
  }

  // ------------------------------------------------------------------ history
  void SyncHistory(DeliveryState d,double now){
   var done=(d.orders??new DeliveryOrder[0]).Where(o=>o!=null&&(o.status=="entregue"||o.status=="expirado"||o.status=="cancelado"||o.status=="recusado")).Take(10).ToList();
   string sig=string.Join("|",done.Select(o=>o.id+":"+o.status+":"+o.stars.ToString(CultureInfo.InvariantCulture)+":"+o.paid.ToString(CultureInfo.InvariantCulture)).ToArray());
   if(sig==historySig)return;
   historySig=sig;
   // Rebuilt only when a finished order changes; the empty note stays.
   for(int i=historyContent.childCount-1;i>=0;i--){var child=historyContent.GetChild(i).gameObject;if(child!=historyEmpty)Destroy(child);}
   foreach(var o in done)BuildHistoryRow(o);
   historyEmpty.SetActive(done.Count==0);
  }
  string historySig="";
  static string HistoryText(DeliveryOrder o){
   switch(o.status){
    case "entregue":return (o.tip>0?"Gorjeta "+Money(Mathf.RoundToInt(o.tip)):"Sem gorjeta")+" · "+(o.neighborhood??"");
    case "expirado":return "Expirou sem resposta";
    case "cancelado":return "Cancelado: não embalou a tempo";
    default:return "Recusado";
   }
  }
  // A history row, 72 px: the avatar, the name and the note, the stars and the coins earned (coin icon, "+128").
  void BuildHistoryRow(DeliveryOrder o){
   var row=Panel(historyContent,"Row",Paper,14);Pref(row.gameObject,-1,72);
   N.Row(row.gameObject,10,new RectOffset(10,14,6,6)).childAlignment=TextAnchor.MiddleLeft;
   var disc=Avatar(row.transform,"Avatar",60,out var ini);PaintAvatar(disc,ini,o.avatar,o.customerName);
   var tx=N.Node("Texts",row.transform);N.Column(tx.gameObject,0);Pref(tx.gameObject,-1,-1).flexibleWidth=1;
   U.Label(tx,"Name",K.Headline,20,Ink,TextAlignmentOptions.Left).text=o.customerName??"";
   U.Label(tx,"Sub",K.Body,18,Muted,TextAlignmentOptions.Left).text=HistoryText(o);
   if(o.status=="entregue"){
    var stars=N.Node("Stars",row.transform);N.Row(stars.gameObject,2);
    for(int i=0;i<5;i++)Star(stars,i<Mathf.RoundToInt(o.stars),18);
   }
   var money=N.Node("Money",row.transform);N.Row(money.gameObject,6).childAlignment=TextAnchor.MiddleRight;Pref(money.gameObject,130,-1);
   if(o.status=="entregue"){
    LayImg(money.transform,"Coin","Icons/coin",26,26);
    U.Label(money.transform,"Paid",K.Number,20,Ink,TextAlignmentOptions.Right).text="+"+Money(Mathf.RoundToInt(o.paid));
   }else U.Label(money.transform,"Paid",K.Number,20,Muted,TextAlignmentOptions.Right).text="-";
  }
 }
}
