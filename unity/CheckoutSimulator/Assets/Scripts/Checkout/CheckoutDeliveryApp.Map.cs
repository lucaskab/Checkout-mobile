using System;
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
 // The GPS map: the real city (CheckoutCityViews.MapTexture) in a rounded frame. With no active order it shows the
 // neighbourhood around the store (about 70 m wide); with orders it eases to frame the store and the drop-offs.
 // Overlays (pins with labels, the dashed route from CheckoutCourier.RouteOf and the live bike from
 // CheckoutCourier.TryGetBike) are placed in the texture's uv space, so they stay on the streets as the view moves.
 public sealed partial class CheckoutDeliveryApp {
  const int RouteDots=36;
  const float NeighbourhoodMeters=70f,MinOrderView=.2f;
  const float PinW=40f,PinH=52f;
  RawImage mapRaw;GameObject mapPlaceholder;TextMeshProUGUI mapPlaceholderText;
  RectTransform storePin;TextMeshProUGUI storeLabel;CheckoutMap mapRef;
  Rect mapView=new Rect(0,0,1,1);
  Vector2 storeUv;bool storeKnown;
  readonly Dictionary<string,MapOrder> mapOrders=new Dictionary<string,MapOrder>();

  // One order on the map: its customer pin with a label, its dashed route (resampled), and its bike marker.
  sealed class MapOrder{
   public string id;public RectTransform pin,bike;public TextMeshProUGUI label;
   public List<RectTransform> dots=new List<RectTransform>();public List<Vector2> route=new List<Vector2>();
   public Vector2 door,bikeUv,bikeShown;public bool hasDoor,hasRoute,hasBike,bikeSeen;public int stage=-1;
   public string routeSig="",labelText="";
  }

  // The frame: a chunky rounded panel with a masked texture, a GPS ribbon and the overlay layer. Tall: at least 300 px.
  void BuildMap(RectTransform parent){
   mapFrame=Panel(parent,"MapFrame","F5EBD6",26).rectTransform;
   var sized=Pref(mapFrame.gameObject,-1,360);sized.minHeight=300;sized.flexibleHeight=1;
   var mask=N.Image(mapFrame,"Mask",Color.white,0);mask.sprite=K.Rounded(18);mask.type=Image.Type.Sliced;mask.raycastTarget=false;
   U.Stretch(mask.rectTransform,Vector2.zero,Vector2.one,new Vector2(10,10),new Vector2(-10,-10));
   mask.gameObject.AddComponent<Mask>().showMaskGraphic=true;
   var rawNode=N.Node("City",mask.transform);U.Stretch(rawNode,Vector2.zero,Vector2.one);
   mapRaw=rawNode.gameObject.AddComponent<RawImage>();mapRaw.raycastTarget=false;mapRaw.color=Color.white;
   // Placeholder while the city view is not rendered yet.
   var ph=N.Node("Placeholder",mask.transform);U.Stretch(ph,Vector2.zero,Vector2.one);
   var phBack=N.Image(ph,"Back",K.C("E9DCC2"),0);U.Stretch(phBack.rectTransform,Vector2.zero,Vector2.one);
   var phIcon=SpriteImg(ph,"Icon",K.Icon("Icons/market"),Color.white,96,96);U.At(phIcon.rectTransform,new Vector2(.5f,.6f),new Vector2(96,96),Vector2.zero);
   mapPlaceholderText=U.Label(ph,"Text",K.Headline,24,Ink);U.At(mapPlaceholderText.rectTransform,new Vector2(.5f,.22f),new Vector2(300,40),Vector2.zero);
   mapPlaceholderText.text="Carregando mapa…";
   mapPlaceholder=ph.gameObject;
   // Overlay layer: pins, route and bike live here, clipped by the mask.
   mapLayer=N.Node("Layer",mask.transform);U.Stretch(mapLayer,Vector2.zero,Vector2.one);
   storePin=BuildPin(mapLayer,Blue,"Loja",out storeLabel);
   storePin.gameObject.SetActive(false);
   // GPS ribbon, tilted, over the top-left corner.
   var gps=Panel(mapFrame,"Gps",Blue,14);U.At(gps.rectTransform,new Vector2(0,1),new Vector2(212,42),new Vector2(96,-26));
   gps.rectTransform.localRotation=Quaternion.Euler(0,0,-4f);
   var gpsText=U.Label(gps.transform,"Text",K.Headline,20,"FFFFFF");U.Stretch(gpsText.rectTransform,Vector2.zero,Vector2.one);gpsText.text="GPS · ao vivo";
  }
  // A map pin: a red (or blue) head with a white outline, 40 x 52 px, its tip at the anchor, and a small label above.
  static RectTransform BuildPin(RectTransform layer,string fillHex,string text,out TextMeshProUGUI label){
   var pin=N.Node("Pin",layer);pin.pivot=new Vector2(.5f,0);pin.sizeDelta=new Vector2(PinW,PinH);
   var outline=N.Image(pin,"Outline",Color.white,0);outline.sprite=DeliveryArt.Pin;outline.raycastTarget=false;
   U.Stretch(outline.rectTransform,Vector2.zero,Vector2.one,new Vector2(-4,-4),new Vector2(4,4));
   var fill=N.Image(pin,"Fill",K.C(fillHex),0);fill.sprite=DeliveryArt.Pin;fill.raycastTarget=false;U.Stretch(fill.rectTransform,Vector2.zero,Vector2.one);
   var chip=Panel(pin,"Label","FFFDF8",12);
   U.At(chip.rectTransform,new Vector2(.5f,1),new Vector2(128,30),Vector2.zero);
   chip.rectTransform.pivot=new Vector2(.5f,0);chip.rectTransform.anchoredPosition=new Vector2(0,8);
   label=U.Label(chip.transform,"Text",K.Body,18,Ink);U.Stretch(label.rectTransform,Vector2.zero,Vector2.one);label.text=text;
   return pin;
  }

  // Reads the store: the map texture, the store pin, and one entry per mission order (pin, route, bike).
  void SyncMap(DeliveryState d,double now){
   if(mapFrame==null)return;
   var tex=CheckoutCityViews.MapTexture;
   bool ready=tex!=null;
   if(mapRaw.texture!=tex)mapRaw.texture=tex;
   mapPlaceholder.SetActive(!ready);
   if(!ready){mapPlaceholderText.text="Carregando mapa…";return;}
   if(!mapRef)mapRef=FindAnyObjectByType<CheckoutMap>();
   if(mapRef&&!storeKnown){storeUv=CheckoutCityViews.WorldToMap(mapRef.Entrance);storeKnown=true;}
   storePin.gameObject.SetActive(storeKnown);
   var list=(d.orders??new DeliveryOrder[0]).Where(o=>o!=null&&StageOf(o.status)>0).ToList();
   var keep=new HashSet<string>(list.Select(o=>o.id));
   foreach(var key in mapOrders.Keys.ToList())if(!keep.Contains(key)){
    var gone=mapOrders[key];mapOrders.Remove(key);
    if(gone.pin)Destroy(gone.pin.gameObject);
    if(gone.bike)Destroy(gone.bike.gameObject);
    foreach(var dot in gone.dots)if(dot)Destroy(dot.gameObject);
   }
   foreach(var o in list){
    if(!mapOrders.TryGetValue(o.id,out var m)){m=BuildMapOrder(o.id);mapOrders[o.id]=m;}
    m.stage=StageOf(o.status);
    string first=FirstName(o.customerName);
    if(m.labelText!=first){m.labelText=first;m.label.text=first;}
    if(!m.hasDoor){m.door=CheckoutCityViews.WorldToMap(CheckoutCityViews.CustomerDoor(o.id));m.hasDoor=true;}
    // The route is read when the order is on the road or about to be; its dots are rebuilt only when it changes.
    if(m.stage>=2){
     var pts=CheckoutCourier.RouteOf(o.id);
     string sig=pts==null?"":pts.Count+":"+(pts.Count>0?pts[0].ToString("F1")+pts[pts.Count-1].ToString("F1"):"");
     if(sig!=m.routeSig){
      m.routeSig=sig;
      m.route.Clear();
      if(pts!=null)foreach(var p in pts)m.route.Add(CheckoutCityViews.WorldToMap(p));
      m.route=Resample(m.route,RouteDots);
      m.hasRoute=m.route.Count>1;
     }
    }
    m.pin.gameObject.SetActive(true);
   }
   // Dots are shown only on the active route of each order.
   foreach(var m in mapOrders.Values)foreach(var dot in m.dots)if(dot)dot.gameObject.SetActive(m.hasRoute&&m.stage>=2);
  }
  MapOrder BuildMapOrder(string id){
   var m=new MapOrder{id=id};
   m.pin=BuildPin(mapLayer,Red,"",out m.label);
   // The bike: a blue badge with the delivery truck icon, made once.
   m.bike=N.Node("Bike",mapLayer);m.bike.sizeDelta=new Vector2(44,44);
   var badge=N.Image(m.bike,"Badge",K.C(Blue),0);badge.sprite=DeliveryArt.Circle;U.Stretch(badge.rectTransform,Vector2.zero,Vector2.one);
   var glyph=N.Image(m.bike,"Glyph",Color.white,0);glyph.sprite=K.Icon("Icons/delivery-truck");glyph.preserveAspect=true;U.Stretch(glyph.rectTransform,new Vector2(.14f,.14f),new Vector2(.86f,.86f));
   m.bike.gameObject.SetActive(false);
   // Route dots, created once per order.
   for(int i=0;i<RouteDots;i++){
    var dot=N.Image(mapLayer,"Dot",K.C("5FA8C6"),0);dot.sprite=DeliveryArt.Dash;dot.raycastTarget=false;
    dot.rectTransform.sizeDelta=new Vector2(16,8);dot.rectTransform.pivot=new Vector2(.5f,.5f);
    m.dots.Add(dot.rectTransform);dot.gameObject.SetActive(false);
   }
   return m;
  }
  // Normalised position in the map layer for a uv point in the texture, given the current view.
  Vector2 Norm(Vector2 uv)=>new Vector2((uv.x-mapView.x)/Mathf.Max(1e-4f,mapView.width),(uv.y-mapView.y)/Mathf.Max(1e-4f,mapView.height));
  static void Place(RectTransform r,Vector2 norm){r.anchorMin=r.anchorMax=norm;}

  // Evenly spaced points along a polyline (by arc length), so the dots keep their spacing.
  static List<Vector2> Resample(List<Vector2> pts,int count){
   var result=new List<Vector2>();
   if(pts==null||pts.Count<2)return result;
   float total=0;for(int i=1;i<pts.Count;i++)total+=Vector2.Distance(pts[i-1],pts[i]);
   if(total<=1e-6f)return result;
   for(int k=0;k<count;k++){
    float want=total*(k+.5f)/count,acc=0;
    for(int i=1;i<pts.Count;i++){
     float seg=Vector2.Distance(pts[i-1],pts[i]);
     if(acc+seg>=want||i==pts.Count-1){
      float t=seg>1e-6f?Mathf.Clamp01((want-acc)/seg):0f;
      result.Add(Vector2.Lerp(pts[i-1],pts[i],t));
      break;
     }
     acc+=seg;
    }
   }
   return result;
  }

  // Per frame: frame the view (eased), place every overlay in it, and follow the live bike smoothly.
  void AnimateMap(float t){
   if(mapFrame==null||CheckoutCityViews.MapTexture==null)return;
   float dt=Time.unscaledDeltaTime;
   var r=mapFrame.rect;
   float aspect=r.width>1f?r.height/r.width:.75f;
   // Targets: the store and every drop-off, and the bikes that are on the road.
   var pts=new List<Vector2>();
   if(storeKnown)pts.Add(storeUv);
   foreach(var m in mapOrders.Values){
    if(!m.hasDoor)continue;
    pts.Add(m.door);
    if(m.stage==4&&CheckoutCourier.TryGetBike(m.id,out var bikePos,out var prog)){
     m.bikeUv=CheckoutCityViews.WorldToMap(bikePos);
     if(!m.bikeSeen){m.bikeShown=m.bikeUv;m.bikeSeen=true;}
     m.hasBike=true;
     pts.Add(m.bikeUv);
    }else m.hasBike=false;
   }
   // Width of the neighbourhood view in uv: about 70 m of the map (the map's world rect is in metres).
   float metersUv=Mathf.Clamp(NeighbourhoodMeters/Mathf.Max(1f,CheckoutCityViews.MapWorldRect.width),.04f,1f);
   Rect want=pts.Count==0?ViewAround(storeKnown?storeUv:new Vector2(.5f,.5f),metersUv,aspect):ViewFor(pts,aspect,Mathf.Max(MinOrderView,metersUv));
   float ease=1f-Mathf.Exp(-dt*2.6f);
   mapView=new Rect(Mathf.Lerp(mapView.x,want.x,ease),Mathf.Lerp(mapView.y,want.y,ease),Mathf.Lerp(mapView.width,want.width,ease),Mathf.Lerp(mapView.height,want.height,ease));
   mapRaw.uvRect=mapView;
   if(storeKnown){storePin.gameObject.SetActive(true);Place(storePin,Norm(storeUv));storePin.anchoredPosition=Vector2.zero;}
   foreach(var m in mapOrders.Values){
    if(m.pin==null)continue;
    Place(m.pin,Norm(m.door));m.pin.anchoredPosition=Vector2.zero;
    m.pin.localScale=Vector3.one*(1f+.05f*Mathf.Sin(t*4f+m.door.x*10f));
    // Route dots: resampled points along the real road, each rotated along its direction.
    for(int i=0;i<m.dots.Count;i++){
     var dot=m.dots[i];if(!dot)continue;
     if(i>=m.route.Count)continue;
     Place(dot,Norm(m.route[i]));dot.anchoredPosition=Vector2.zero;
     int a=Mathf.Max(0,i-1),b=Mathf.Min(m.route.Count-1,i+1);
     Vector2 dir=Norm(m.route[b])-Norm(m.route[a]);
     dot.localRotation=Quaternion.Euler(0,0,Mathf.Atan2(dir.y,dir.x)*Mathf.Rad2Deg);
    }
    // The live bike follows its real position smoothly and bobs in place.
    if(m.hasBike){
     m.bikeShown=Vector2.Lerp(m.bikeShown,m.bikeUv,1f-Mathf.Exp(-dt*6f));
     if(!m.bike.gameObject.activeSelf)m.bike.gameObject.SetActive(true);
     Place(m.bike,Norm(m.bikeShown));m.bike.anchoredPosition=new Vector2(0,6f*Mathf.Sin(t*5f));
    }else if(m.bike.gameObject.activeSelf){
     m.bike.gameObject.SetActive(false);m.bikeSeen=false;
    }
   }
   // The placeholder text blinks while the map loads (if it is still shown).
   if(mapPlaceholder.activeSelf)mapPlaceholderText.color=K.C(Ink)*new Color(1,1,1,.55f+.45f*Mathf.Sin(t*4f));
  }
  // A view of the given uv width (height from the frame's aspect), centred on a point and kept inside the texture.
  static Rect ViewAround(Vector2 c,float w,float aspect){
   float h=w*aspect;
   if(h>1f){h=1f;w=h/aspect;}
   if(w>1f){w=1f;h=w*aspect;}
   float x=Mathf.Clamp(c.x-w*.5f,0,1-w),y=Mathf.Clamp(c.y-h*.5f,0,1-h);
   return new Rect(x,y,w,h);
  }
  // The view (uv rect) with the frame's aspect that covers the points with a margin, kept inside the texture.
  static Rect ViewFor(List<Vector2> pts,float aspect,float minW){
   if(pts.Count==0)return new Rect(0,0,1,1);
   float minX=pts.Min(p=>p.x),maxX=pts.Max(p=>p.x),minY=pts.Min(p=>p.y),maxY=pts.Max(p=>p.y)+.07f; // room above the top pin for its label and the GPS ribbon
   float cx=(minX+maxX)*.5f,cy=(minY+maxY)*.5f;
   float w=Mathf.Max((maxX-minX)*1.6f+.12f,((maxY-minY)*1.6f+.12f)/aspect,minW);
   return ViewAround(new Vector2(cx,cy),w,aspect);
  }
 }
}
