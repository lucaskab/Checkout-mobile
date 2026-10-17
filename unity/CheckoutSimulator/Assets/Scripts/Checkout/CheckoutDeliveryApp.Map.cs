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
 // Overlays (pins with labels, the route line from CheckoutCourier.RouteOf and the live bike from
 // CheckoutCourier.TryGetBike) are placed in the texture's uv space, so they stay on the streets as the view moves.
 // The map texture renders every frame while the app animates it (CheckoutCityViews.KeepMapLive), so traffic and the
 // bike move smoothly; the route line is erased behind the bike as it rides.
 public sealed partial class CheckoutDeliveryApp {
  const float NeighbourhoodMeters=70f,MinOrderView=.2f;
  const float PinW=44f,PinH=60f; // the rendered pin is 0.73 wide per height
  RawImage mapRaw;GameObject mapPlaceholder;TextMeshProUGUI mapPlaceholderText;
  RectTransform storePin;TextMeshProUGUI storeLabel;CheckoutMap mapRef;
  Rect mapView=new Rect(0,0,1,1);
  Vector2 storeUv;bool storeKnown;
  readonly Dictionary<string,MapOrder> mapOrders=new Dictionary<string,MapOrder>();

  // One order on the map: its customer pin with a label, its route line (smoothed), and its bike marker.
  sealed class MapOrder{
   public string id;public RectTransform pin,bike;public TextMeshProUGUI label;
   public RouteLine line;public List<Vector2> route=new List<Vector2>();public List<float> arc=new List<float>();
   public Vector2 door,bikeUv,bikeShown;public bool hasDoor,hasRoute,hasBike,bikeSeen,facingRight;public int stage=-1;public float travel,progress;
   public string routeSig="",labelText="";
  }

  // The frame: a chunky rounded panel with a masked texture, a GPS ribbon and the overlay layer. Tall: at least 300 px.
  void BuildMap(RectTransform parent){
   mapFrame=Panel(parent,"MapFrame",Paper,18).rectTransform;
   var sized=Pref(mapFrame.gameObject,-1,360);sized.minHeight=300;sized.flexibleHeight=1;
   var mask=N.Image(mapFrame,"Mask",Color.white,0);mask.sprite=K.Rounded(18);mask.type=Image.Type.Sliced;mask.raycastTarget=false;
   U.Stretch(mask.rectTransform,Vector2.zero,Vector2.one,new Vector2(10,10),new Vector2(-10,-10));
   mask.gameObject.AddComponent<Mask>().showMaskGraphic=true;
   var rawNode=N.Node("City",mask.transform);U.Stretch(rawNode,Vector2.zero,Vector2.one);
   mapRaw=rawNode.gameObject.AddComponent<RawImage>();mapRaw.raycastTarget=false;mapRaw.color=Color.white;
   // Placeholder while the city view is not rendered yet.
   var ph=N.Node("Placeholder",mask.transform);U.Stretch(ph,Vector2.zero,Vector2.one);
   var phBack=N.Image(ph,"Back",K.C(EmptyTone),0);U.Stretch(phBack.rectTransform,Vector2.zero,Vector2.one);
   var phIcon=SpriteImg(ph,"Icon",K.Icon("Icons/market"),Color.white,96,96);U.At(phIcon.rectTransform,new Vector2(.5f,.6f),new Vector2(96,96),Vector2.zero);
   mapPlaceholderText=U.Label(ph,"Text",K.Headline,24,Ink);U.At(mapPlaceholderText.rectTransform,new Vector2(.5f,.22f),new Vector2(300,40),Vector2.zero);
   mapPlaceholderText.text="Carregando mapa…";
   mapPlaceholder=ph.gameObject;
   // Overlay layer: pins, route and bike live here, clipped by the mask.
   mapLayer=N.Node("Layer",mask.transform);U.Stretch(mapLayer,Vector2.zero,Vector2.one);
   storePin=BuildPin(mapLayer,Blue,"Loja",out storeLabel);
   storePin.gameObject.SetActive(false);
   // GPS ribbon, tilted, over the top-left corner.
   var gps=Panel(mapFrame,"Gps",Blue,14);U.At(gps.rectTransform,new Vector2(0,1),new Vector2(200,38),new Vector2(118,-34));
   // a live chip like a map app's, straight (no game ribbon tilt)
   var gpsText=U.Label(gps.transform,"Text",K.Headline,20,"FFFFFF");U.Stretch(gpsText.rectTransform,Vector2.zero,Vector2.one);gpsText.text="GPS · ao vivo";
  }
  // A map pin: a red (or blue) head with a white outline, 40 x 52 px, its tip at the anchor, and a small label above.
  static RectTransform BuildPin(RectTransform layer,string fillHex,string text,out TextMeshProUGUI label){
   var pin=N.Node("Pin",layer);pin.pivot=new Vector2(.5f,0);pin.sizeDelta=new Vector2(PinW,PinH);
   // The rendered glossy pin: red for a customer, teal for the store (the art has its own white centre).
   var fill=N.Image(pin,"Fill",Color.white,0);fill.sprite=fillHex==Red?DeliveryArt.PinCustomer:DeliveryArt.PinStore;fill.preserveAspect=true;fill.raycastTarget=false;U.Stretch(fill.rectTransform,Vector2.zero,Vector2.one);
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
    if(gone.line)Destroy(gone.line.gameObject);
   }
   foreach(var o in list){
    if(!mapOrders.TryGetValue(o.id,out var m)){m=BuildMapOrder(o.id);mapOrders[o.id]=m;}
    m.stage=StageOf(o.status);
    string first=FirstName(o.customerName);
    if(m.labelText!=first){m.labelText=first;m.label.text=first;}
    if(!m.hasDoor){m.door=CheckoutCityViews.WorldToMap(CheckoutCityViews.CustomerDoor(o.id));m.hasDoor=true;}
    // The route is read when the order is on the road or about to be; the line is rebuilt only when it changes.
    if(m.stage>=2){
     var pts=CheckoutCourier.RouteOf(o.id);
     string sig=pts==null?"":pts.Count+":"+(pts.Count>0?pts[0].ToString("F1")+pts[pts.Count-1].ToString("F1"):"");
     if(sig!=m.routeSig){
      m.routeSig=sig;
      m.route.Clear();
      if(pts!=null)foreach(var p in pts)m.route.Add(CheckoutCityViews.WorldToMap(p));
      // The courier's path is dense: keep its corners only (Douglas-Peucker), then round them.
      m.route=Smooth(Simplify(m.route,.0012f),3);
      m.arc=ArcOf(m.route);
      m.hasRoute=m.route.Count>1;m.travel=0f;
     }
    }
    m.pin.gameObject.SetActive(true);
   }
   // The line is shown only on the active route of each order.
   foreach(var m in mapOrders.Values)if(m.line)m.line.gameObject.SetActive(m.hasRoute&&m.stage>=2);
  }
  MapOrder BuildMapOrder(string id){
   var m=new MapOrder{id=id};
   // The route line sits under the pins and the bike (first child of the layer).
   var lineNode=N.Node("Route",mapLayer);U.Stretch(lineNode,Vector2.zero,Vector2.one);lineNode.SetAsFirstSibling();
   lineNode.gameObject.AddComponent<CanvasRenderer>();   // RequireComponent alone sometimes left it missing (MissingComponentException on the first order)
   m.line=lineNode.gameObject.AddComponent<RouteLine>();m.line.raycastTarget=false;m.line.gameObject.SetActive(false);
   m.pin=BuildPin(mapLayer,Red,"",out m.label);
   // The bike: just the delivery moto icon (no badge), made once.
   m.bike=N.Node("Bike",mapLayer);m.bike.sizeDelta=new Vector2(58,58);
   var glyph=N.Image(m.bike,"Glyph",Color.white,0);glyph.sprite=DeliveryArt.Moto;glyph.preserveAspect=true;glyph.raycastTarget=false;U.Stretch(glyph.rectTransform,Vector2.zero,Vector2.one);
   m.bike.gameObject.SetActive(false);
   return m;
  }
  // Normalised position in the map layer for a uv point in the texture, given the current view.
  Vector2 Norm(Vector2 uv)=>new Vector2((uv.x-mapView.x)/Mathf.Max(1e-4f,mapView.width),(uv.y-mapView.y)/Mathf.Max(1e-4f,mapView.height));
  static void Place(RectTransform r,Vector2 norm){r.anchorMin=r.anchorMax=norm;}

  // Douglas-Peucker: drops the points that lie within eps of the line between their neighbours.
  static List<Vector2> Simplify(List<Vector2> pts,float eps){
   if(pts==null||pts.Count<3)return pts??new List<Vector2>();
   var keep=new bool[pts.Count];keep[0]=keep[pts.Count-1]=true;
   var stack=new Stack<Vector2Int>();stack.Push(new Vector2Int(0,pts.Count-1));
   while(stack.Count>0){
    var seg=stack.Pop();int a=seg.x,b=seg.y;if(b-a<2)continue;
    Vector2 p=pts[a],q=pts[b],d=q-p;float len=d.magnitude;
    int far=-1;float farD=eps;
    for(int i=a+1;i<b;i++){
     float dist=len>1e-7f?Mathf.Abs(d.x*(pts[i].y-p.y)-d.y*(pts[i].x-p.x))/len:Vector2.Distance(pts[i],p);
     if(dist>farD){farD=dist;far=i;}
    }
    if(far<0)continue;
    keep[far]=true;stack.Push(new Vector2Int(a,far));stack.Push(new Vector2Int(far,b));
   }
   var outPts=new List<Vector2>();for(int i=0;i<pts.Count;i++)if(keep[i])outPts.Add(pts[i]);
   return outPts;
  }
  // Chaikin corner cutting (endpoints kept): street corners become soft curves, like a navigation app's line.
  static List<Vector2> Smooth(List<Vector2> pts,int passes){
   if(pts==null||pts.Count<3)return pts??new List<Vector2>();
   var cur=new List<Vector2>();
   // Drop points that repeat (the courier's route can hold duplicates), they would make zero-length segments.
   foreach(var p in pts)if(cur.Count==0||(p-cur[cur.Count-1]).sqrMagnitude>1e-10f)cur.Add(p);
   for(int k=0;k<passes&&cur.Count>=3;k++){
    var next=new List<Vector2>{cur[0]};
    for(int i=0;i<cur.Count-1;i++){
     Vector2 a=cur[i],b=cur[i+1];
     if(i>0)next.Add(Vector2.Lerp(a,b,.25f));
     if(i<cur.Count-2)next.Add(Vector2.Lerp(a,b,.75f));
    }
    next.Add(cur[cur.Count-1]);cur=next;
   }
   return cur;
  }
  // Cumulative arc length at each point.
  static List<float> ArcOf(List<Vector2> pts){
   var arc=new List<float>();float acc=0;
   for(int i=0;i<pts.Count;i++){if(i>0)acc+=Vector2.Distance(pts[i-1],pts[i]);arc.Add(acc);}
   return arc;
  }
  // How far along the route (arc length) the bike is: the courier's progress gives a first guess, then the bike is
  // projected on the segments near that guess (so a route that passes close to itself cannot make it jump).
  static float TravelOf(MapOrder m,Vector2 bike,float progress01){
   if(m.route.Count<2)return 0f;
   float total=m.arc[m.arc.Count-1],guess=progress01*total,window=Mathf.Max(.02f,total*.15f);
   float best=guess,bestD=float.MaxValue;
   for(int i=1;i<m.route.Count;i++){
    if(m.arc[i]<guess-window||m.arc[i-1]>guess+window)continue;
    Vector2 a=m.route[i-1],b=m.route[i],ab=b-a;float len2=ab.sqrMagnitude;
    float t=len2>1e-12f?Mathf.Clamp01(Vector2.Dot(bike-a,ab)/len2):0f;
    float d=(a+ab*t-bike).sqrMagnitude;
    if(d<bestD){bestD=d;best=m.arc[i-1]+t*Mathf.Sqrt(len2);}
   }
   return Mathf.Clamp(best,0f,total);
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
     m.bikeUv=CheckoutCityViews.WorldToMap(bikePos);m.progress=prog;
     if(!m.bikeSeen){m.bikeShown=m.bikeUv;m.bikeSeen=true;}
     m.hasBike=true;
     pts.Add(m.bikeUv);
    }else m.hasBike=false;
   }
   // Width of the neighbourhood view in uv: about 70 m of the map (the map's world rect is in metres).
   float metersUv=Mathf.Clamp(NeighbourhoodMeters/Mathf.Max(1f,CheckoutCityViews.MapWorldRect.width),.04f,1f);
   Rect want=pts.Count==0?ViewAround(storeKnown?storeUv:new Vector2(.5f,.5f),metersUv,aspect):ViewFor(pts,aspect,Mathf.Max(MinOrderView,metersUv));
   CheckoutCityViews.KeepMapLive();
   float ease=1f-Mathf.Exp(-dt*2.6f);
   mapView=new Rect(Mathf.Lerp(mapView.x,want.x,ease),Mathf.Lerp(mapView.y,want.y,ease),Mathf.Lerp(mapView.width,want.width,ease),Mathf.Lerp(mapView.height,want.height,ease));
   mapRaw.uvRect=mapView;
   if(storeKnown){storePin.gameObject.SetActive(true);Place(storePin,Norm(storeUv));storePin.anchoredPosition=Vector2.zero;}
   foreach(var m in mapOrders.Values){
    if(m.pin==null)continue;
    Place(m.pin,Norm(m.door));m.pin.anchoredPosition=Vector2.zero;
    // The live bike follows its real position (read every frame) with a light smoothing, and does not bob.
    if(m.hasBike){
     m.bikeShown=Vector2.Lerp(m.bikeShown,m.bikeUv,1f-Mathf.Exp(-dt*14f));
     if(!m.bike.gameObject.activeSelf)m.bike.gameObject.SetActive(true);
     Place(m.bike,Norm(m.bikeShown));m.bike.anchoredPosition=Vector2.zero;
     // The icon art faces left: mirror it when the bike rides to the right (with a dead zone so it does not flicker).
     float dx=m.bikeUv.x-m.bikeShown.x;
     if(dx>.0004f)m.facingRight=true;else if(dx<-.0004f)m.facingRight=false;
     m.bike.localScale=new Vector3(m.facingRight?-1:1,1,1);
     // The part of the route already ridden is erased (never grows back).
     if(m.hasRoute)m.travel=Mathf.Max(m.travel,TravelOf(m,m.bikeShown,m.progress));
    }else if(m.bike.gameObject.activeSelf){
     m.bike.gameObject.SetActive(false);m.bikeSeen=false;
    }
    if(m.line&&m.line.gameObject.activeSelf)m.line.Set(m.route,m.arc,m.travel,mapView);
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
 // The route of a delivery as one smooth line: a dark casing under a bright blue core, round joins and caps, a
 // constant width in pixels. Points are in map uv; the current view maps them into this rect. Drawing starts at
 // `from` (arc length), so the part the bike already rode is gone.
 public sealed class RouteLine : MaskableGraphic {
  const float Core=8f,Casing=13f;const int Round=10;
  static readonly Color CoreColor=new Color32(0x2F,0x8B,0xF0,0xFF),CasingColor=new Color32(0x16,0x4E,0x9A,0xFF);
  readonly List<Vector2> pts=new List<Vector2>();
  List<Vector2> uv;List<float> arc;float from;Rect view;
  public void Set(List<Vector2> route,List<float> arcs,float start,Rect v){uv=route;arc=arcs;from=start;view=v;SetVerticesDirty();}
  protected override void OnPopulateMesh(VertexHelper vh){
   vh.Clear();
   if(uv==null||arc==null||uv.Count<2||arc.Count!=uv.Count)return;
   var r=rectTransform.rect;
   Vector2 P(Vector2 u)=>new Vector2(r.xMin+(u.x-view.x)/Mathf.Max(1e-4f,view.width)*r.width,r.yMin+(u.y-view.y)/Mathf.Max(1e-4f,view.height)*r.height);
   // The visible part: the point at `from`, then every later point.
   pts.Clear();
   float total=arc[arc.Count-1];if(from>=total-1e-5f)return;
   for(int i=1;i<uv.Count;i++){
    if(arc[i]<=from)continue;
    if(pts.Count==0){float seg=arc[i]-arc[i-1];float t=seg>1e-7f?Mathf.Clamp01((from-arc[i-1])/seg):0f;pts.Add(P(Vector2.Lerp(uv[i-1],uv[i],t)));}
    pts.Add(P(uv[i]));
   }
   if(pts.Count<2)return;
   Stroke(vh,Casing*.5f,CasingColor);
   Stroke(vh,Core*.5f,CoreColor);
  }
  void Stroke(VertexHelper vh,float half,Color c){
   for(int i=1;i<pts.Count;i++){
    Vector2 a=pts[i-1],b=pts[i],d=b-a;float len=d.magnitude;if(len<1e-3f)continue;
    Vector2 n=new Vector2(-d.y,d.x)/len*half;
    int o=vh.currentVertCount;
    vh.AddVert(a-n,c,Vector2.zero);vh.AddVert(a+n,c,Vector2.zero);vh.AddVert(b+n,c,Vector2.zero);vh.AddVert(b-n,c,Vector2.zero);
    vh.AddTriangle(o,o+1,o+2);vh.AddTriangle(o,o+2,o+3);
   }
   // Round joins and caps: a small disc at both ends and wherever the line turns (straight runs need none).
   for(int i=0;i<pts.Count;i++){
    var p=pts[i];
    if(i>0&&i<pts.Count-1){
     Vector2 u=(pts[i]-pts[i-1]),w=(pts[i+1]-pts[i]);
     if(u.sqrMagnitude>1e-6f&&w.sqrMagnitude>1e-6f&&Vector2.Dot(u.normalized,w.normalized)>.9995f)continue;
    }
    int o=vh.currentVertCount;vh.AddVert(p,c,Vector2.zero);
    for(int k=0;k<=Round;k++){float ang=k*Mathf.PI*2f/Round;vh.AddVert(p+new Vector2(Mathf.Cos(ang),Mathf.Sin(ang))*half,c,Vector2.zero);}
    for(int k=0;k<Round;k++)vh.AddTriangle(o,o+1+k,o+2+k);
   }
  }
 }
}
