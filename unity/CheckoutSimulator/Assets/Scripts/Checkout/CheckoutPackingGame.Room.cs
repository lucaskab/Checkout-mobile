using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // The stockroom the order is packed from: the same racks, cold room and boxes as CheckoutReceivingGame (the art
 // comes from Resources/CheckoutDesktop/Receiving). Every box on the racks is a source of units: a press on it takes
 // one unit out (the box count goes down); the units go back to their box when they are not put in a bag.
 public sealed partial class CheckoutPackingGame:MonoBehaviour {
  const string RoomDir="Receiving/";
  const float RoomBoxScale=1.35f;
  static readonly Dictionary<string,string> ZoneNames=new Dictionary<string,string>{{"mercearia","SECOS"},{"bebidas","BEBIDAS"},{"hortifruti","HORTIFRÚTI"},{"refrigerados","CÂMARA FRIA"}};
  static readonly Dictionary<string,string> ZoneColors=new Dictionary<string,string>{{"refrigerados","4FA3D9"},{"bebidas","F28C28"},{"hortifruti","5DA637"},{"mercearia","D9A032"}};
  static readonly Dictionary<string,Rect> boxMarks=new Dictionary<string,Rect>();

  // ------------------------------------------------------------------ data from the art (Receiving json)
  [Serializable] class RoomQuad {public int level,bay,index;public float[] fl,fr,bl,br;public float ppm,ppmBack;}
  [Serializable] class RoomFixtureJson {public string key;public int[] size;public RoomQuad[] slots;public float[] sign;public float[] display;public float boxHeight;}
  [Serializable] class RoomClipLine {public float x0,x1,y;}
  [Serializable] class RoomClipJson {public int[] size;public float[] sheet;public RoomClipLine[] lines;}
  static T RoomLoad<T>(string name) where T:class{var t=Resources.Load<TextAsset>("CheckoutDesktop/"+RoomDir+name);return t?JsonUtility.FromJson<T>(t.text):null;}

  // A place for one box on a rack or in the cold room (stage pixels: bottom-centre of the box and its width).
  sealed class RoomPlace {public RoomFixture fixture;public string zone;public int level,bay,index;public Vector2 foot;public float width;public PackBox box;}
  sealed class RoomFixture {public string name;public RectTransform root,boxes;public string[] bayZones;public readonly List<RoomPlace> places=new List<RoomPlace>();public TextMeshProUGUI label;}
  // One box on the racks: its product, the units still inside and the label that counts them.
  sealed class PackBox {public RectTransform rect;public Image holder,art,glow;public TextMeshProUGUI count;public int productId,units,caseUnits;public string name,category,zone;public RoomPlace place;public Vector2 basePos;public float lift;public bool opened;}

  readonly List<RoomFixture> roomFixtures=new List<RoomFixture>();readonly List<PackBox> roomBoxes=new List<PackBox>();
  RectTransform rackLayer;Image pillBack;TextMeshProUGUI pillText;RoomPlace ghostPlace;

  // Forwards the press and the drag of a box to the packing game: a drag from a box takes one unit out of it.
  sealed class BoxInput:MonoBehaviour,IPointerDownHandler,IBeginDragHandler,IDragHandler,IEndDragHandler,IPointerEnterHandler,IPointerExitHandler{
   public CheckoutPackingGame Game;public PackBox Box;Token carried;
   public void OnPointerDown(PointerEventData e){Game.BoxPressed(Box);}
   public void OnBeginDrag(PointerEventData e){carried=Game.BoxDragStart(Box,e);}
   public void OnDrag(PointerEventData e){if(carried!=null)Game.UnitDragged(carried,e);}
   public void OnEndDrag(PointerEventData e){if(carried!=null){var t=carried;carried=null;Game.UnitDragEnded(t,e);}}
   public void OnPointerEnter(PointerEventData e){Game.BoxHovered(Box,true);}
   public void OnPointerExit(PointerEventData e){Game.BoxHovered(Box,false);}
  }

  // ------------------------------------------------------------------ the room
  void BuildRoom(){
   // The packing station takes the left 30%; the racks fill the rest. Unlike the receiving room (fixed 3 fixtures),
   // the room grows with the stock: every zone gets as many rack bays as its boxes need (9 boxes a bay, 2 bays a
   // rack) and the cold room repeats every 6 boxes, so EVERYTHING the stockroom holds stands on a shelf.
   rackLayer=Node("Racks",board);U.Stretch(rackLayer,Vector2.zero,Vector2.one);
   var held=bridge.State?.stockroom??new StockroomEntry[0];
   int Boxes(string zone)=>held.Where(x=>x!=null&&x.zone==zone).Sum(x=>Mathf.Max(0,x.boxes));
   var bays=new List<string>();
   foreach(var z in new[]{"hortifruti","bebidas","mercearia"}){int n=Mathf.CeilToInt(Boxes(z)/9f);for(int i=0;i<n;i++)bays.Add(z);}
   int colds=Mathf.CeilToInt(Boxes("refrigerados")/6f);
   if(bays.Count==0&&colds==0){bays.Add("hortifruti");bays.Add("mercearia");}
   var racks=new List<string[]>();
   for(int i=0;i<bays.Count;i+=2)racks.Add(new[]{bays[i],i+1<bays.Count?bays[i+1]:bays[i]});
   int count=racks.Count+colds;
   float left=-W*.5f+W*.30f,right=W*.5f-W*.01f,slot=(right-left)/Mathf.Max(1,count);
   int k=0;
   foreach(var r in racks){string name=string.Join(" · ",r.Distinct().Select(z=>ZoneNames[z]));AddFixture("rack",name,r,left+slot*(k+.5f),slot);k++;}
   for(int i=0;i<colds;i++){AddFixture("coldroom","Câmara fria",new[]{"refrigerados"},left+slot*(k+.5f),slot);k++;}
  }
  void AddFixture(string key,string name,string[] bays,float centerX,float slotWidth){
   var d=RoomLoad<RoomFixtureJson>("receiving_"+key);
   // The rendered body takes about 60% of the image width: size the image so the body fills its slot, as tall as
   // the room allows; the foot of the rack (about 8% up the image) stands on the floor line of the backdrop.
   float aspect=d!=null&&d.size!=null?d.size[0]/(float)d.size[1]:1.6f;
   float w=slotWidth/.6f,h=w/aspect;float maxH=H*.76f;if(h>maxH){h=maxH;w=h*aspect;}
   var center=new Vector2(centerX,-H*.21f+h*.42f);
   var f=new RoomFixture{name=name,bayZones=bays};
   f.root=Node("Fixture "+key+" "+name,rackLayer);U.At(f.root,Mid,new Vector2(w,h),center);
   U.Shadow(f.root,new Vector2(w*.62f,h*.08f),new Vector2(0,h*.05f));
   RackLayer(f.root,"Back",RoomDir+"receiving_"+key+"_back");
   f.boxes=Node("Boxes",f.root);U.Stretch(f.boxes,Vector2.zero,Vector2.one);
   RackLayer(f.root,"Front",RoomDir+"receiving_"+key+"_front");
   if(d?.slots!=null){
    foreach(var q in d.slots.OrderByDescending(q=>q.level).ThenBy(q=>q.bay).ThenBy(q=>q.index)){
     Vector2 P(float[] a)=>a!=null&&a.Length>1?new Vector2((a[0]-.5f)*w,(a[1]-.5f)*h):Vector2.zero;
     var fl=P(q.fl);var fr=P(q.fr);var bl=P(q.bl);var br=P(q.br);
     var foot=Vector2.Lerp((fl+fr)*.5f,(bl+br)*.5f,.22f);float width=Mathf.Lerp((fr-fl).magnitude,(br-bl).magnitude,.22f);
     string zone=bays[Mathf.Clamp(q.bay,0,bays.Length-1)];
     f.places.Add(new RoomPlace{fixture=f,zone=zone,level=q.level,bay=q.bay,index=q.index,foot=foot+center,width=width});
    }
   }
   // The zone names on the sign of the rack, in the zone colours.
   if(d?.sign!=null&&d.sign.Length>=4){
    var node=Node("Sign",f.root);U.Stretch(node,new Vector2(d.sign[0],d.sign[1]),new Vector2(d.sign[2],d.sign[3]),new Vector2(8,2),new Vector2(-8,-2));
    f.label=U.Label(node,"Text",K.Headline,h*.05f,"0F5F59");U.Stretch(f.label.rectTransform,Vector2.zero,Vector2.one);
    f.label.enableAutoSizing=true;f.label.fontSizeMin=10;f.label.fontSizeMax=h*.055f;
    f.label.text=string.Join("  ·  ",bays.Distinct().Select(z=>"<color=#"+ZoneColors[z]+">"+ZoneNames[z]+"</color>"));
   }
   if(key=="coldroom"&&d?.display!=null&&d.display.Length>=4){
    // The thermometer of the cold room keeps blinking its temperature.
    var node=Node("Display",f.root);U.Stretch(node,new Vector2(d.display[0],d.display[1]),new Vector2(d.display[2],d.display[3]));
    var glow=U.GlowAt(node,"Glow",new Color(.3f,1,.5f,.35f),Mid,h*.08f);StartCoroutine(BlinkGlow(glow));
   }
   roomFixtures.Add(f);
  }
  Image RackLayer(RectTransform parent,string name,string sprite){
   var img=new GameObject(name,typeof(RectTransform),typeof(Image)).GetComponent<Image>();img.transform.SetParent(parent,false);
   img.sprite=K.Icon(sprite);img.raycastTarget=false;img.preserveAspect=false;U.Stretch(img.rectTransform,Vector2.zero,Vector2.one);
   if(!img.sprite)img.color=new Color(1,1,1,0);return img;
  }
  IEnumerator BlinkGlow(Image img){while(img){img.color=new Color(.3f,1,.5f,.2f+.2f*Mathf.PingPong(Time.unscaledTime,1));yield return null;}}

  // ------------------------------------------------------------------ boxes
  // Which carton a product comes in (same rule as the receiving room).
  static string BoxKind(string category){
   switch(category){
    case "hortifruti":case "organicos":return "crate";
    case "bebidas":case "refrigerantes":case "aguas":case "energeticos":case "alcoolicos":return "pack";
    case "congelados":case "sorvetes":return "frozen";
    case "padaria":case "ovos":return "tray";
    default:return "carton";
   }
  }
  // Where the printed "N×" mark sits on the carton art.
  static Rect BoxMark(string kind){
   if(boxMarks.TryGetValue(kind,out var r))return r;
   var t=Resources.Load<TextAsset>("CheckoutDesktop/"+RoomDir+"box_"+kind+"_marks");r=new Rect(.33f,.35f,.32f,.28f);
   if(t){var m=Regex.Match(t.text,"\\[([^\\]]+)\\]");if(m.Success){var v=m.Groups[1].Value.Split(',').Select(x=>float.Parse(x.Trim(),System.Globalization.CultureInfo.InvariantCulture)).ToArray();if(v.Length>=4)r=Rect.MinMaxRect(v[0],v[1],v[2],v[3]);}}
   boxMarks[kind]=r;return r;
  }
  PackBox MakeBox(RectTransform parent,int productId,int units,string name,string category,float width){
   string kind=BoxKind(category);float size=width*RoomBoxScale;
   var holder=new GameObject("Box",typeof(RectTransform),typeof(Image)).GetComponent<Image>();holder.transform.SetParent(parent,false);
   holder.color=new Color(1,1,1,0);holder.raycastTarget=true;var r=holder.rectTransform;r.anchorMin=r.anchorMax=Mid;r.pivot=new Vector2(.5f,.14f);r.sizeDelta=new Vector2(size,size);
   var glow=U.GlowAt(r,"Hint",new Color(1,.9f,.45f,0),Mid,size*1.25f);
   var art=new GameObject("Art",typeof(RectTransform),typeof(Image)).GetComponent<Image>();art.transform.SetParent(r,false);art.sprite=K.Icon(RoomDir+"box_"+kind);art.raycastTarget=false;U.Stretch(art.rectTransform,Vector2.zero,Vector2.one);
   if(!art.sprite)art.sprite=K.Icon("Game/cardboard_box");
   // The product itself peeks out of the box, big, so the player can find it at a glance; the count sits on a
   // small dark tag at the front corner.
   var peek=new GameObject("Product",typeof(RectTransform),typeof(Image)).GetComponent<Image>();peek.transform.SetParent(r,false);
   peek.sprite=K.Icon("Products/product-"+productId.ToString("000",System.Globalization.CultureInfo.InvariantCulture));peek.preserveAspect=true;peek.raycastTarget=false;
   var pr=peek.rectTransform;pr.anchorMin=pr.anchorMax=new Vector2(.5f,kind=="tray"?.6f:.7f);pr.pivot=new Vector2(.5f,.5f);pr.sizeDelta=new Vector2(size*.56f,size*.56f);
   var tag=new GameObject("Tag",typeof(RectTransform),typeof(Image)).GetComponent<Image>();tag.transform.SetParent(r,false);
   tag.sprite=K.Rounded(10);tag.type=Image.Type.Sliced;tag.color=new Color(.18f,.12f,.07f,.88f);tag.raycastTarget=false;
   var tr=tag.rectTransform;tr.anchorMin=tr.anchorMax=new Vector2(.8f,.24f);tr.pivot=new Vector2(.5f,.5f);tr.sizeDelta=new Vector2(size*.34f,size*.17f);
   var count=U.Label(tr,"Units",K.Headline,size*.12f,"FFFFFF");U.Stretch(count.rectTransform,Vector2.zero,Vector2.one);
   count.enableAutoSizing=true;count.fontSizeMin=8;count.fontSizeMax=size*.13f;count.overflowMode=TextOverflowModes.Overflow;
   var box=new PackBox{rect=r,holder=holder,art=art,glow=glow,count=count,productId=productId,units=units,caseUnits=units,name=name,category=category};
   box.zone=ZoneOfCategory(category);
   count.text=units+"×";
   var input=holder.gameObject.AddComponent<BoxInput>();input.Game=this;input.Box=box;
   roomBoxes.Add(box);
   return box;
  }
  static string ZoneOfCategory(string category){
   switch(category){
    case "refrigerados":case "congelados":case "sorvetes":case "carnes":case "peixes":case "frios":case "laticinios":return "refrigerados";
    case "bebidas":case "aguas":case "refrigerantes":case "alcoolicos":case "energeticos":return "bebidas";
    case "hortifruti":case "organicos":return "hortifruti";
    default:return "mercearia";
   }
  }
  void RefreshBoxCount(PackBox b){
   if(b==null||!b.count)return;
   b.count.text=b.units+"×";
   bool empty=b.units<=0;b.art.color=empty?new Color(.55f,.55f,.55f,.85f):(b.opened?new Color(.93f,.9f,.86f,1):Color.white);
  }

  // What the stockroom holds stands on its racks, product next to product (the same placing as the receiving room).
  // Returns the units that really fit on the racks per product: only those can be packed.
  Dictionary<int,int> FillStockroom(){
   var shown=new Dictionary<int,int>();
   var held=bridge.State?.stockroom;if(held==null)return shown;
   foreach(var item in held.OrderBy(x=>x.productId)){
    for(int i=0;i<item.boxes;i++){
     var place=FreePlace(item.zone,item.productId,null);if(place==null)break;
     int units=i<item.boxes-1?item.caseSize:Mathf.Max(1,item.units-item.caseSize*(item.boxes-1));
     var box=MakeBox(place.fixture.boxes,item.productId,units,item.productName??"Produto",item.category??"",place.width);
     box.opened=units<item.caseSize;Put(box,place);RefreshBoxCount(box);
     shown[item.productId]=(shown.TryGetValue(item.productId,out var s)?s:0)+units;
    }
   }
   return shown;
  }
  void Put(PackBox box,RoomPlace place){
   place.box=box;box.place=place;box.rect.SetParent(place.fixture.boxes,false);
   box.basePos=place.foot-(Vector2)place.fixture.root.anchoredPosition;box.rect.anchoredPosition=box.basePos;
   float s=place.width*RoomBoxScale;box.rect.sizeDelta=new Vector2(s,s);
   // Upper levels in front of the lower ones' tops, boxes further right on top of the left ones.
   var ordered=place.fixture.places.Where(p=>p.box!=null&&p.box.rect).OrderByDescending(p=>p.foot.y).ThenBy(p=>p.foot.x).ToList();
   for(int i=0;i<ordered.Count;i++)ordered[i].box.rect.SetSiblingIndex(i);
  }
  // A free place in the zone: next to boxes of the same product first, then the lowest, leftmost one.
  RoomPlace FreePlace(string zone,int productId,Vector2? near){
   var free=roomFixtures.SelectMany(f=>f.places).Where(p=>p.zone==zone&&p.box==null).ToList();if(free.Count==0)return null;
   if(near.HasValue)return free.OrderBy(p=>(p.foot-near.Value).sqrMagnitude).First();
   var friends=roomFixtures.SelectMany(f=>f.places).Where(p=>p.box!=null&&p.box.productId==productId).ToList();
   if(friends.Count>0)return free.OrderBy(p=>friends.Min(f=>(f.foot-p.foot).sqrMagnitude)).First();
   return free.OrderBy(p=>p.level).ThenBy(p=>p.bay).ThenBy(p=>p.index).First();
  }
 }
}
