using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
using Random = UnityEngine.Random;
namespace Checkout {
 // Sucos — "Copos misturados" (step kind "sort"): the juices got layered in the wrong jugs. Tap a jug, then another, to
 // pour its top layer over: it only goes onto the same juice or into an empty jug, and only as much as fits. Done when
 // every jug holds a single juice (full) or nothing. The deal is checked by a solver, which also gives the ideal number of
 // pours; Desfazer takes the last pour back (it still counts as a move).
 public partial class CheckoutDesktopHUD {
  static readonly Dictionary<string,string> JuiceColor=new Dictionary<string,string>{
   {"laranja","F59A23"},{"morango","E5484D"},{"limao","8CCB3C"},{"uva","7E4AA8"},{"abacaxi","F6D44A"},{"melancia","F2667E"},{"maracuja","F3B532"},{"acai","4A2A5E"},
  };
  const int JugCap=4;

  IEnumerator StepSort(DesktopKitchenStep s){
   var flavors=(s.pieces??new string[0]).Where(JuiceColor.ContainsKey).ToArray();if(flavors.Length<2)flavors=new[]{"laranja","morango","limao"};
   int empty=Mathf.Clamp(s.singles,1,3);int n=flavors.Length;
   List<List<int>> jugs=null;int par=0;
   for(int attempt=0;attempt<10;attempt++){
    var units=new List<int>();for(int f=0;f<n;f++)for(int k=0;k<JugCap;k++)units.Add(f);
    units=units.OrderBy(_=>Random.value).ToList();
    var deal=new List<List<int>>();for(int j=0;j<n;j++)deal.Add(units.GetRange(j*JugCap,JugCap));for(int j=0;j<empty;j++)deal.Add(new List<int>());
    if(deal.Any(j=>j.Count==JugCap&&j.All(x=>x==j[0])))continue; // no jug already done
    int steps=SolveSort(deal,50000);if(steps<0||steps<n)continue;
    jugs=deal;par=steps;break;
   }
   if(jugs==null){jugs=new List<List<int>>();for(int f=0;f<n;f++)jugs.Add(new List<int>{f,(f+1)%n,f,(f+1)%n});for(int j=0;j<empty;j++)jugs.Add(new List<int>());par=SolveSort(jugs,50000);if(par<0)par=n*3;}

   float W=StageW,H=StageH;int count=jugs.Count;
   float jugW=Mathf.Min(120,(W-100)/count-24),unitH=Mathf.Min(62,(H-130)/JugCap),jugH=unitH*JugCap+26;
   var bases=new List<Vector2>();var jugRects=new List<RectTransform>();
   var layers=new List<List<Image>>();
   for(int j=0;j<count;j++){
    var at=new Vector2((j-(count-1)/2f)*(jugW+24),10);bases.Add(at);
    var jug=PNode(kitchenStage,"Jug",at,new Vector2(jugW,jugH));
    PShadow(jug,new Vector2(jugW,jugH*.3f));
    var glass=N.Image(jug,"Glass",new Color(.85f,.95f,1f,.35f),18);glass.rectTransform.sizeDelta=new Vector2(jugW,jugH);
    var rim=N.Image(jug,"Rim",new Color(1,1,1,.7f),6);rim.rectTransform.sizeDelta=new Vector2(jugW+8,10);rim.rectTransform.anchoredPosition=new Vector2(0,jugH/2);
    jugRects.Add(jug);layers.Add(new List<Image>());
    int index=j;PHandle(jug,null,null,null,()=>JugTap(index));
   }
   var shine=new List<Image>();
   for(int j=0;j<count;j++){var g=N.Image(jugRects[j],"Shine",new Color(1,1,1,.28f),6);g.rectTransform.sizeDelta=new Vector2(8,jugH*.75f);g.rectTransform.anchoredPosition=new Vector2(-jugW*.32f,0);shine.Add(g);}
   void Redraw(){
    for(int j=0;j<count;j++){
     foreach(var l in layers[j])if(l)Destroy(l.gameObject);layers[j].Clear();
     for(int k=0;k<jugs[j].Count;k++){
      var c=K.C(JuiceColor[flavors[jugs[j][k]]]);
      var layer=N.Image(jugRects[j],"Juice",c,k==0?14:4);layer.rectTransform.sizeDelta=new Vector2(jugW-14,unitH-2);
      layer.rectTransform.anchoredPosition=new Vector2(0,-jugH/2+13+(k+.5f)*unitH);layer.transform.SetSiblingIndex(2+k);
      var top=N.Image(layer.transform,"Top",new Color(1,1,1,.18f),3);top.rectTransform.sizeDelta=new Vector2(jugW-20,6);top.rectTransform.anchoredPosition=new Vector2(0,unitH/2-5);
      layers[j].Add(layer);
     }
    }
    for(int j=0;j<count;j++)shine[j].transform.SetAsLastSibling();
   }
   Redraw();
   var history=new Stack<List<List<int>>>();int moves=0;int selected=-1;
   jugTap=j=>{
    kitchenPad.Interacted=true;
    if(selected<0){if(jugs[j].Count==0){Sound("bonk");return;}selected=j;StartCoroutine(U.Move(jugRects[j],bases[j]+new Vector2(0,28),.1f));Sound("pop",1.2f);return;}
    if(selected==j){StartCoroutine(U.Move(jugRects[j],bases[j],.1f));selected=-1;return;}
    var from=jugs[selected];var to=jugs[j];int top=from[from.Count-1];
    if(to.Count>=JugCap||(to.Count>0&&to[to.Count-1]!=top)){Sound("bonk");StartCoroutine(U.Pop(jugRects[j],1.06f,.15f));return;}
    history.Push(jugs.Select(x=>x.ToList()).ToList());
    while(from.Count>0&&from[from.Count-1]==top&&to.Count<JugCap){from.RemoveAt(from.Count-1);to.Add(top);}
    moves++;Sound("whoosh",1.1f);StartCoroutine(U.Move(jugRects[selected],bases[selected],.12f));selected=-1;Redraw();
   };
   var undo=PButton("Desfazer","secondary",new Vector2(W/2-20-85,-H/2+30),new Vector2(160,48),()=>{if(history.Count==0)return;jugs=history.Pop();moves++;if(selected>=0){jugRects[selected].anchoredPosition=bases[selected];selected=-1;}Redraw();Sound("pop",.8f);});
   var moveText=PMoves(new Vector2(-W/2+190,-H/2+30),340);
   var hand=KHint(()=>jugRects[0].anchoredPosition,()=>jugRects[count-1].anchoredPosition,true);
   bool Sorted()=>jugs.All(j=>j.Count==0||(j.Count==JugCap&&j.All(x=>x==j[0])));
   while(!Sorted()){
    if(kitchenPad.Interacted&&hand)Destroy(hand);
    PMovesText(moveText,moves,par);
    KitchenMeter(jugs.Count(j=>j.Count==JugCap&&j.All(x=>x==j[0]))/(float)n);
    yield return null;
   }
   if(hand)Destroy(hand);PMovesText(moveText,moves,par);KitchenMeter(1);
   jugTap=null;
   kitchenScore=PuzzleScore(moves,par+1,false,.06f);
   for(int j=0;j<count;j++)if(jugs[j].Count>0){StartCoroutine(U.Pop(jugRects[j],1.1f,.3f));yield return new WaitForSecondsRealtime(.06f);}
   yield return PSolved(new Vector2(0,10),W*.3f);
  }
  System.Action<int> jugTap;
  void JugTap(int j)=>jugTap?.Invoke(j);

  // Fewest pours to sort the jugs (breadth-first over the states; -1 when not found within `limit` states).
  static int SolveSort(List<List<int>> start,int limit){
   string Key(List<List<int>> s)=>string.Join("|",s.Select(j=>string.Concat(j.Select(x=>(char)('a'+x)))).OrderBy(x=>x));
   bool Done(List<List<int>> s)=>s.All(j=>j.Count==0||(j.Count==JugCap&&j.All(x=>x==j[0])));
   var seen=new HashSet<string>{Key(start)};var frontier=new List<List<List<int>>>{start};int depth=0;
   while(frontier.Count>0&&seen.Count<limit){
    var next=new List<List<List<int>>>();
    foreach(var s in frontier){
     if(Done(s))return depth;
     for(int a=0;a<s.Count;a++){if(s[a].Count==0)continue;int top=s[a][s[a].Count-1];
      // (pouring a single-juice jug into an empty one changes nothing: skipped below)
      for(int b=0;b<s.Count;b++){if(a==b)continue;var to=s[b];if(to.Count>=JugCap||(to.Count>0&&to[to.Count-1]!=top))continue;if(to.Count==0&&s[a].All(x=>x==top))continue;
       var c=s.Select(x=>x.ToList()).ToList();var f=c[a];var t=c[b];while(f.Count>0&&f[f.Count-1]==top&&t.Count<JugCap){f.RemoveAt(f.Count-1);t.Add(top);}
       if(seen.Add(Key(c)))next.Add(c);}
     }
    }
    frontier=next;depth++;
   }
   return -1;
  }
 }
}
