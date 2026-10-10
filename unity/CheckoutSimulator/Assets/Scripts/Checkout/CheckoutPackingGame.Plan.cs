using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // Order planning for the packing game: the lines the stockroom can fill (what is really on the racks), the weight of
 // each product, the par time, one seeded twist per order (fragile or plastic-free bag), and the substitution picker
 // that only opens when a line is really short.
 public sealed partial class CheckoutPackingGame:MonoBehaviour {
  sealed class PackOpt {public int productId;public string name,category;public bool ok;}

  System.Random rng=new System.Random(1);
  readonly List<Line> substQueue=new List<Line>();
  Line substLine;List<PackOpt> substOpts;
  Dictionary<int,int> shownStock=new Dictionary<int,int>();
  bool twistFragile,twistEco;
  string twistTitle="",twistBody="";

  // Stable across runs and platforms (string.GetHashCode is randomised per process).
  static int Hash(string s){unchecked{uint h=2166136261;foreach(char c in s??""){h^=c;h*=16777619;}return (int)(h&0x7fffffff);}}

  // Weight by category (kg): drinks 1.2–2, pantry 1, produce .5, bread .4, dairy 1, cleaning 1.5, the rest .6.
  static float WeightOf(string category,int productId){
   switch(category){
    case "bebidas":case "aguas":case "refrigerantes":case "alcoolicos":case "energeticos":return 1.2f+(Mathf.Abs(productId*37)%9)/8f*.8f;
    case "mercearia":return 1f;
    case "hortifruti":return .5f;
    case "padaria":return .4f;
    case "laticinios":return 1f;
    case "limpeza":return 1.5f;
    default:return .6f;
   }
  }

  // One ticket line per order line. A line can only get the units the racks really show (shown); the line's need is
  // the number of units that can be packed. Par: 20 s + 7 s per ordered unit.
  void PrepareLines(Dictionary<int,int> shown){
   lines.Clear();shownStock=shown??new Dictionary<int,int>();
   foreach(var it in order.items??new DeliveryItem[0]){
    if(it==null)continue;
    int have=shownStock.TryGetValue(it.productId,out var s)?s:0;
    int need=Mathf.Clamp(have,0,Mathf.Max(0,it.quantity));
    lines.Add(new Line{productId=it.productId,quantity=it.quantity,need=need,name=it.productName??"Produto",category=it.category??"",done=0});
   }
   requiredTotal=lines.Sum(x=>x.need);requiredPlaced=0;
   parSec=30f+9f*lines.Sum(x=>x.quantity); // the whole stockroom is open: finding the boxes takes time
  }

  // No twist card when the storage opens (author asked for no alert there), so no hidden twist rules either: only the
  // normal rules apply (cold in the thermal bag, nothing heavy on top of fragile food).
  void PlanOrder(){
   rng=new System.Random(Hash(orderId));
   twistFragile=false;twistEco=false;twistTitle="";twistBody="";substMistakes=0;
   // Every line the racks cannot fill gets the substitution picker before packing starts.
   substQueue.Clear();substQueue.AddRange(lines.Where(l=>l.need<l.quantity));
   pendingSubst=substQueue.Count>0;
  }

  // Three in-stock products for a short line: one of the same section (the right substitute), two from elsewhere.
  List<PackOpt> SubstOptions(Line line){
   var inOrder=new HashSet<int>(lines.Select(x=>x.productId));
   var held=bridge.State?.stockroom;
   var pool=new List<PackOpt>();var seen=new HashSet<int>();
   if(held!=null)foreach(var e in held){
    if(e==null||e.productId<=0||inOrder.Contains(e.productId)||!seen.Add(e.productId))continue;
    if(!shownStock.TryGetValue(e.productId,out var units)||units<=0)continue;
    pool.Add(new PackOpt{productId=e.productId,name=e.productName??"Produto",category=e.category??""});
   }
   var same=pool.Where(p=>p.category==line.category).OrderBy(p=>rng.Next()).ToList();
   var other=pool.Where(p=>p.category!=line.category).OrderBy(p=>rng.Next()).ToList();
   var list=new List<PackOpt>();
   if(same.Count>0){same[0].ok=true;list.Add(same[0]);}
   list.AddRange(other.Take(3-list.Count));
   if(same.Count==0)foreach(var p in list)p.ok=true;
   return list.OrderBy(p=>rng.Next()).ToList();
  }

  // The substitution picker: a card with three in-stock products. A wrong pick is refused and counted for the grade.
  void OpenSubst(){
   if(!board||modal!=null)return;
   while(substQueue.Count>0){
    var line=substQueue[0];substQueue.RemoveAt(0);
    var opts=SubstOptions(line);
    if(opts.Count==0)continue;
    substLine=line;substOpts=opts;
    BuildSubstModal();
    return;
   }
   pendingSubst=false;CheckDone();
  }
  void BuildSubstModal(){
   running=false;
   float cardW=Mathf.Min(W*.84f,920f),cardH=Mathf.Min(H*.66f,470f);
   var dim=U.Box(board,"SubstDim","000000",0,Vector2.zero,Vector2.one);dim.color=new Color(.12f,.08f,.04f,.62f);dim.raycastTarget=true;
   modal=dim.gameObject;
   var card=U.Shape(dim.transform,"SubstCard","FFF7EC",28,Mid,new Vector2(cardW,cardH));
   var head=U.Label(card.transform,"Title",K.Headline,36,"4A3624");
   U.Stretch(head.rectTransform,new Vector2(0,.8f),new Vector2(1,.96f),new Vector2(20,0),new Vector2(-20,0));
   head.text="“"+substLine.name+"” acabou!";head.enableAutoSizing=true;head.fontSizeMin=18;head.fontSizeMax=36;
   var sub=U.Label(card.transform,"Sub",K.Body,22,"8A7560");
   U.Stretch(sub.rectTransform,new Vector2(0,.7f),new Vector2(1,.79f),new Vector2(20,0),new Vector2(-20,0));
   sub.text="Escolha o substituto certo para o cliente";sub.enableAutoSizing=true;sub.fontSizeMin=14;sub.fontSizeMax=22;
   float optW=cardW*.3f,optH=cardH*.56f;
   for(int i=0;i<substOpts.Count;i++){
    var opt=substOpts[i];
    var option=U.Shape(card.transform,"Opt"+i,"FBEEDA",22,Mid,new Vector2(optW,optH),new Vector2((i-1)*(optW+cardW*.03f),-cardH*.06f));
    U.Icon(option.transform,"Icon","Products/product-"+opt.productId.ToString("000",CultureInfo.InvariantCulture),new Vector2(.5f,.7f),new Vector2(optW*.6f,optW*.6f));
    var name=U.Label(option.transform,"Name",K.Body,22,"4A3624");
    U.Stretch(name.rectTransform,new Vector2(0,0),new Vector2(1,.3f),new Vector2(8,6),new Vector2(-8,0));
    name.textWrappingMode=TextWrappingModes.Normal;name.text=opt.name;name.enableAutoSizing=true;name.fontSizeMin=14;name.fontSizeMax=22;
    var optRect=option.rectTransform;
    U.Tap(option,()=>PickSubst(opt,optRect));
   }
  }
  void PickSubst(PackOpt opt,RectTransform optRect){
   if(modal==null||substLine==null)return;
   Touch();
   if(!opt.ok){
    substMistakes++;PlayClip(CheckoutRestockSound.Wrong,.6f);
    if(optRect)StartCoroutine(U.Shake(optRect,.3f,10));
    Toast("Esse não substitui "+substLine.name+".");
    return;
   }
   PlayClip(CheckoutRestockSound.Next,.6f);
   Destroy(modal);modal=null;
   ApplySubstitution(opt);
   running=true;
   OpenSubst();
  }
  // The substitute takes the short line: its units are taken from its own box like any other.
  void ApplySubstitution(PackOpt opt){
   var line=substLine;if(line==null)return;
   line.productId=opt.productId;line.name=opt.name;line.category=opt.category;line.substituted=true;line.done=0;
   line.need=Mathf.Min(line.quantity,shownStock.TryGetValue(opt.productId,out var u)?u:0);
   requiredTotal=lines.Sum(x=>x.need);
   RefreshLine(line);
   Toast("Substituto: "+opt.name+".");
   substLine=null;
   CheckDone();
  }
 }
}
