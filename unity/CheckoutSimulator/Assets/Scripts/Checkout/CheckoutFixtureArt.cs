using System;
using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // One product lane of a fixture, in the fixture root's local pixels (origin at the root's center).
 // The floor quad is where the products stand: front-left, front-right, back-left, back-right.
 public sealed class FixtureLane {
  public int index;public int[] doors=Array.Empty<int>();
  public Vector2 fl,fr,bl,br;public float ppmFront,ppmBack,height;
  public RectTransform rect;   // invisible box over the lane (hints, sparkles); not a raycast target
  public Vector2 FrontMid=>(fl+fr)*.5f;
  public Vector2 Center=>(fl+fr+bl+br)*.25f+Vector2.up*ppmFront*height*.35f;
 }
 // A fixture drawn from pre-rendered 3D layers (Blender, ArtSource/restock/restock_art.py):
 // back (interior and shelves) < shadows < products < front (shelf lips, crate fronts, glass) < doors.
 public sealed class FixtureView {
  public string key,kind;                 // kind: "door" (swing), "lid" (slide) or "open"
  public RectTransform root,shadows,products,front,dropArea;
  public FixtureLane[] lanes=new FixtureLane[7]; // null where the fixture has no lane
  public RectTransform[] doors=Array.Empty<RectTransform>();public bool[] doorOpen=Array.Empty<bool>();
  public Image[] doorHits=Array.Empty<Image>();
  public Sprite[][] doorFrames=Array.Empty<Sprite[]>();   // swing doors: closed, half open, open (pre-rendered)
  public Rect[] doorClosedRects=Array.Empty<Rect>(),doorOpenRects=Array.Empty<Rect>();
  public TextMeshProUGUI title;
  public bool AnyOpen{get{foreach(var o in doorOpen)if(o)return true;return false;}}
  public bool Reachable(FixtureLane l){if(l==null||l.doors.Length==0)return true;foreach(int d in l.doors)if(d<doorOpen.Length&&doorOpen[d])return true;return false;}
 }

 public static class CheckoutFixtureArt {
  [Serializable] class JLane {public float[] fl,fr,bl,br;public float ppmFront,ppmBack,height;public int door=-1;}
  [Serializable] class JDoor {public string layer,hinge,kind;public int dir;}
  [Serializable] class JRect {public float x0,y0,x1,y1;}
  [Serializable] class JFixture {public string key;public int[] size;public JLane[] lanes;public JDoor[] doors;public JRect[] doorRects,doorOpenRects;public JRect signRect;}
  [Serializable] class JBound {public int id;public float x0,y0,x1,y1;}
  [Serializable] class JBounds {public JBound[] items;}

  const string Dir="Restock/";
  static readonly Dictionary<string,JFixture> data=new Dictionary<string,JFixture>();
  static JFixture Data(string key){
   if(data.TryGetValue(key,out var d))return d;
   var text=Resources.Load<TextAsset>("CheckoutDesktop/"+Dir+"fixture_"+key);
   d=text?JsonUtility.FromJson<JFixture>(text.text):null;data[key]=d;return d;
  }

  public static string ArtKey(string shelfTypeId,int era){
   switch(shelfTypeId){
    case "produce":return era<2?"crates":"stand";
    case "drinks":return era<3?"cooler":"fridge";
    case "bakery":return era<4?"basket":"bakery_shelf";
    case "dairy":return era<4?"display":"dairy_open";
    case "snacks":return era<4?"shelf_small":"gondola";
    case "coffee":case "home":return "gondola";
    case "pizza":return "freezer_upright";
    case "icecream":return "chest";
    default:return "counter";
   }
  }
  public static float Aspect(string key){var d=Data(key);return d!=null&&d.size!=null&&d.size.Length>1?d.size[0]/(float)Mathf.Max(1,d.size[1]):1.6f;}

  static Image Layer(RectTransform parent,string name,string key,string layer){
   var img=new GameObject(name,typeof(RectTransform),typeof(Image)).GetComponent<Image>();
   img.transform.SetParent(parent,false);img.sprite=K.Icon(Dir+"fixture_"+key+"_"+layer);img.raycastTarget=false;img.preserveAspect=false;
   U.Stretch(img.rectTransform,Vector2.zero,Vector2.one);return img;
  }
  static RectTransform Node(RectTransform parent,string name){var r=(RectTransform)new GameObject(name,typeof(RectTransform)).transform;r.SetParent(parent,false);U.Stretch(r,Vector2.zero,Vector2.one);return r;}

  // Builds the fixture as big as fits in `box` (stage pixels), centered at `center` (offset from the
  // parent's center).
  public static FixtureView Build(RectTransform parent,string key,string displayName,Vector2 center,Vector2 box){
   var d=Data(key);
   float aspect=Aspect(key);float h=Mathf.Min(box.y,box.x/aspect),w=h*aspect;
   var v=new FixtureView{key=key};
   v.root=(RectTransform)new GameObject("Fixture "+key,typeof(RectTransform)).transform;v.root.SetParent(parent,false);
   U.At(v.root,new Vector2(.5f,.5f),new Vector2(w,h),center);
   U.Shadow(v.root,new Vector2(w*.95f,h*.1f),new Vector2(0,h*.01f));
   Layer(v.root,"Back",key,"back");
   v.shadows=Node(v.root,"Shadows");v.products=Node(v.root,"Products");
   v.front=Layer(v.root,"Front",key,"front").rectTransform;
   v.dropArea=Node(v.root,"Drop");
   if(d==null){v.kind="open";return v;}
   Vector2 P(float[] a)=>a!=null&&a.Length>1?new Vector2((a[0]-.5f)*w,(a[1]-.5f)*h):Vector2.zero;
   float S=h/Mathf.Max(1,d.size[1]); // ppm in json is in source pixels
   // Doors / lids
   int nd=d.doors?.Length??0;
   v.kind=nd==0?"open":(d.doors[0].kind=="swing"?"door":"lid");
   v.doors=new RectTransform[nd];v.doorOpen=new bool[nd];v.doorHits=new Image[nd];
   var frames=new Sprite[nd][];var closedRects=new Rect[nd];var openRects=new Rect[nd];
   v.doorFrames=frames;v.doorClosedRects=closedRects;v.doorOpenRects=openRects;
   for(int i=0;i<nd;i++){
    var img=Layer(v.root,"Door "+i,key,"door"+i);var r=img.rectTransform;
    var dr=d.doorRects!=null&&i<d.doorRects.Length?d.doorRects[i]:new JRect{x0=0,y0=0,x1=1,y1=1};
    // Swing doors open through three pre-rendered frames (closed, half, open) turned on their hinge.
    // Doors and lids with pre-rendered frames (swing on the hinge, slide along the rail): door<i>_1.._N.
    var list=new List<Sprite>{img.sprite};
    for(int k=1;k<=8;k++){var sp=K.Icon(Dir+"fixture_"+key+"_door"+i+"_"+k);if(!sp)break;list.Add(sp);}
    if(list.Count>1){
     var open=d.doorOpenRects!=null&&i<d.doorOpenRects.Length?d.doorOpenRects[i]:dr;
     frames[i]=list.ToArray();
     openRects[i]=Rect.MinMaxRect(open.x0,open.y0,open.x1,open.y1);
    }
    closedRects[i]=Rect.MinMaxRect(dr.x0,dr.y0,dr.x1,dr.y1);
    var hit=new GameObject("Hit",typeof(RectTransform),typeof(Image)).GetComponent<Image>();hit.transform.SetParent(r,false);
    hit.color=new Color(1,1,1,0);hit.raycastTarget=true;U.Stretch(hit.rectTransform,new Vector2(dr.x0,dr.y0),new Vector2(dr.x1,dr.y1));
    v.doors[i]=r;v.doorHits[i]=hit;
   }
   // Lanes
   for(int i=0;i<(d.lanes?.Length??0)&&i<v.lanes.Length;i++){
    var j=d.lanes[i];
    var l=new FixtureLane{index=i,fl=P(j.fl),fr=P(j.fr),bl=P(j.bl),br=P(j.br),ppmFront=j.ppmFront*S,ppmBack=j.ppmBack*S,height=j.height};
    // Doors in front of the lane: every door covering at least a quarter of its width.
    var list=new List<int>();float lx0=Mathf.Min(l.fl.x,l.bl.x),lx1=Mathf.Max(l.fr.x,l.br.x);
    for(int k=0;k<nd&&d.doorRects!=null&&k<d.doorRects.Length;k++){
     float dx0=(d.doorRects[k].x0-.5f)*w,dx1=(d.doorRects[k].x1-.5f)*w;
     if(Mathf.Min(lx1,dx1)-Mathf.Max(lx0,dx0)>(lx1-lx0)*.25f)list.Add(k);
    }
    l.doors=list.ToArray();
    var z=Zone(l);
    l.rect=Node(v.dropArea,"Lane "+i);U.At(l.rect,new Vector2(.5f,.5f),z.size,z.center);
    v.lanes[i]=l;
   }
   // Sign with the fixture name
   if(d.signRect!=null&&d.signRect.x1>d.signRect.x0){
    v.title=U.Label(v.root,"Title",K.Headline,h*.045f,"0F5F59");
    U.Stretch(v.title.rectTransform,new Vector2(d.signRect.x0,d.signRect.y0),new Vector2(d.signRect.x1,d.signRect.y1),new Vector2(10,2),new Vector2(-10,-2));
    v.title.enableAutoSizing=true;v.title.fontSizeMin=10;v.title.fontSizeMax=h*.05f;v.title.text=CheckoutI18n.T(displayName??"").ToUpperInvariant(); // translated first: the catalog has "Gôndola de doces", not the capitals
    v.title.transform.SetSiblingIndex(v.front.GetSiblingIndex()+1);
   }
   return v;
  }

  // The space a lane's products occupy (floor quad plus the product height), root-local pixels.
  public static Rect Zone(FixtureLane l){
   float x0=Mathf.Min(l.fl.x,l.bl.x),x1=Mathf.Max(l.fr.x,l.br.x),y0=Mathf.Min(l.fl.y,l.fr.y);
   float y1=Mathf.Max(l.bl.y,l.br.y)+l.ppmBack*l.height;
   return Rect.MinMaxRect(x0,y0,x1,y1);
  }
  // The lane under a root-local point: the lane whose zone contains it (closest center wins), or the
  // nearest lane within a small margin.
  public static FixtureLane Pick(FixtureView v,Vector2 p){
   FixtureLane best=null;float bestD=float.MaxValue;
   foreach(var l in v.lanes){
    if(l==null||!l.rect||!l.rect.gameObject.activeSelf)continue;
    var z=Zone(l);var c=new Vector2(z.center.x,(l.FrontMid.y+z.yMax)*.5f);
    float margin=z.height*.25f,dist=(p-c).magnitude;
    bool inside=p.x>=z.xMin-margin*.3f&&p.x<=z.xMax+margin*.3f&&p.y>=z.yMin-margin&&p.y<=z.yMax+margin*.5f;
    if(!inside)continue;
    if(dist<bestD){bestD=dist;best=l;}
   }
   return best;
  }

  // Facing layout: capacity -> rows (front to back) and facings (left to right).
  public static void Grid(int cap,out int rows,out int facings){rows=cap<=3?1:cap<=8?2:3;facings=Mathf.Max(1,Mathf.CeilToInt(cap/(float)rows));}
  // Where unit `i` of a lane stands (root-local, bottom-center of the product) and its height. Units fill
  // the front row first, left to right, then the rows behind.
  public static Vector2 Slot(FixtureLane l,int i,int cap,float iconAspect,out float height,out int row){
   Grid(Mathf.Max(1,cap),out int rows,out int facings);
   row=Mathf.Min(rows-1,i/facings);int f=i%facings;
   float u=(f+.5f)/facings,t=(row+.5f)/rows;
   var front=Vector2.Lerp(l.fl,l.fr,u);var back=Vector2.Lerp(l.bl,l.br,u);var p=Vector2.Lerp(front,back,t);
   float ppm=Mathf.Lerp(l.ppmFront,l.ppmBack,t);
   float laneW=(Vector2.Lerp(l.fr,l.br,t)-Vector2.Lerp(l.fl,l.bl,t)).magnitude;
   height=Mathf.Min(ppm*l.height*.95f,laneW/facings*1.15f*iconAspect);
   return p;
  }

  // Product sprites cropped to their visible pixels, pivot at the bottom center.
  static Dictionary<int,Rect> bounds;static readonly Dictionary<int,Sprite> cropped=new Dictionary<int,Sprite>();
  public static Sprite Product(int id){
   if(cropped.TryGetValue(id,out var s)&&s)return s;
   if(bounds==null){
    bounds=new Dictionary<int,Rect>();
    var t=Resources.Load<TextAsset>("CheckoutDesktop/"+Dir+"product_bounds");
    if(t){var b=JsonUtility.FromJson<JBounds>(t.text);if(b?.items!=null)foreach(var x in b.items)bounds[x.id]=Rect.MinMaxRect(x.x0,x.y0,x.x1,x.y1);}
   }
   var tex=Resources.Load<Texture2D>($"CheckoutDesktop/Products/product-{id:000}");
   if(!tex)return null;
   var r=bounds.TryGetValue(id,out var nb)?nb:new Rect(0,0,1,1);
   var px=new Rect(r.x*tex.width,r.y*tex.height,Mathf.Max(1,r.width*tex.width),Mathf.Max(1,r.height*tex.height));
   s=Sprite.Create(tex,px,new Vector2(.5f,0));cropped[id]=s;return s;
  }
  public static float ProductAspect(int id){var s=Product(id);return s?s.rect.height/Mathf.Max(1,s.rect.width):1;}

  // Swing door: steps through the rendered frames (closed -> half -> open, or back), like a real door
  // turning on its hinge toward the viewer. The tap area follows the door.
  static IEnumerator Swing(FixtureView v,int i,bool open,float seconds){
   var img=v.doors[i]?v.doors[i].GetComponent<Image>():null;var f=v.doorFrames[i];if(!img||f==null)yield break;
   int last=f.Length-1;float step=seconds/Mathf.Max(1,last);
   for(int n=1;n<=last;n++){
    int k=open?n:last-n;
    yield return new WaitForSecondsRealtime(step);
    if(!img)yield break;if(f[k])img.sprite=f[k];
   }
   var hit=i<v.doorHits.Length&&v.doorHits[i]?v.doorHits[i].rectTransform:null;
   if(hit){var r=open?v.doorOpenRects[i]:v.doorClosedRects[i];hit.anchorMin=r.min;hit.anchorMax=r.max;}
  }
  // Opens or closes one door (swing: frames on its hinge; slide: moves aside).
  public static IEnumerator OpenDoor(FixtureView v,int i,bool open,float seconds=.35f){
   if(v==null||i<0||i>=v.doors.Length||!v.doors[i])yield break;
   v.doorOpen[i]=open;var r=v.doors[i];var img=r.GetComponent<Image>();
   if(i<v.doorFrames.Length&&v.doorFrames[i]!=null){yield return Swing(v,i,open,seconds);yield break;}
   Vector3 s0=r.localScale;Vector2 p0=r.anchoredPosition;
   Vector3 s1=s0;Vector2 p1=p0;
   if(v.kind=="door"){s1=new Vector3(open?.16f:1,1,1);}
   else{
    var hit=v.doorHits[i].rectTransform;float wd=(hit.anchorMax.x-hit.anchorMin.x)*v.root.rect.width;
    int dir=i==0?1:-1;if(v.doors.Length==1)dir=1;
    float shift=v.doors.Length==1?wd*1.02f:wd*.92f;
    p1=new Vector2(open?dir*shift:0,v.doors.Length==1&&open?wd*.04f:0);
   }
   Color c0=img?img.color:Color.white,c1=open?new Color(.82f,.86f,.9f,1):Color.white;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/Mathf.Max(.01f,seconds)){
    if(!r)yield break;float e=1-(1-t)*(1-t)*(1-t);
    r.localScale=Vector3.LerpUnclamped(s0,s1,e);r.anchoredPosition=Vector2.LerpUnclamped(p0,p1,e);if(img)img.color=Color.Lerp(c0,c1,e);
    yield return null;
   }
   if(!r)yield break;r.localScale=s1;r.anchoredPosition=p1;if(img)img.color=c1;
  }
 }
}
