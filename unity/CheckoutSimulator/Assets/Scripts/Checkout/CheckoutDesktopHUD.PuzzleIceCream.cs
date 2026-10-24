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
 // Sorvetes — "Casquinha certa" (step kind "scoops"): a customer's order is a tall cone, and the order slip only says it
 // in pictures (no words, so it works in every language): "this flavour at the bottom", "this one right on top of that
 // one", "this one somewhere above that one", "not this one on top". Drag the scoops into the cone (drag one onto
 // another to swap); every clue ticks green when it holds. All clues green = the cone is right. The clues are chosen so
 // that exactly one stacking fits.
 public partial class CheckoutDesktopHUD {
  static readonly Dictionary<string,(string body,string dots)> ScoopLook=new Dictionary<string,(string,string)>{
   {"chocolate",("7A4A2C","5A3420")},{"morango",("F28CA6","E25578")},{"baunilha",("FFF0C9","E9D49A")},{"menta",("A8E6C9","3E7A55")},{"flocos",("FFF7EE","3B2A1E")},{"limao",("E4F28A","B9CC4A")},
  };
  // Clue kinds: 0 = A at slot i (from the bottom), 1 = A right on top of B, 2 = A somewhere above B, 3 = A not at slot i.
  struct ScoopClue {public int kind,a,b,slot;}

  IEnumerator StepScoops(DesktopKitchenStep s){
   var flavors=(s.pieces??new string[0]).Where(ScoopLook.ContainsKey).ToArray();if(flavors.Length<3)flavors=new[]{"chocolate","morango","baunilha"};
   int n=flavors.Length;
   var answer=Enumerable.Range(0,n).OrderBy(_=>Random.value).ToArray(); // answer[slot] = flavour, slot 0 = bottom
   var clues=MakeScoopClues(answer,n);

   float W=StageW,H=StageH;
   // The cone (centre left): a waffle cone with n slots stacked on it.
   float scoop=Mathf.Min(96,(H-120)/(n+.6f));var coneAt=new Vector2(-W*.14f,-H/2+scoop*.75f+12);scoopMoves=0;
   var cone=PImage(kitchenStage,"Cone",K.C("D9A05B"),10,coneAt,new Vector2(scoop*.95f,scoop*1.3f));
   for(int k=0;k<4;k++){var line=N.Image(cone.transform,"Waffle",new Color(.55f,.33f,.12f,.5f),2);line.rectTransform.sizeDelta=new Vector2(4,scoop*1.4f);line.rectTransform.anchoredPosition=new Vector2((k-1.5f)*scoop*.22f,0);line.rectTransform.localRotation=Quaternion.Euler(0,0,30);}
   var slots=new List<Image>();var slotAt=new List<Vector2>();
   for(int i=0;i<n;i++){var at=coneAt+new Vector2(0,scoop*.7f+i*scoop*.82f);slotAt.Add(at);slots.Add(PImage(kitchenStage,"Slot",new Color(1,1,1,.35f),(int)(scoop/2),at,new Vector2(scoop*.9f,scoop*.9f)));}
   var placed=new int[n];for(int i=0;i<n;i++)placed[i]=-1;
   var scoopRects=new RectTransform[n];var homes=new Vector2[n];
   // The tubs (a column on the left): one scoop of each flavour to take.
   for(int f=0;f<n;f++){
    homes[f]=new Vector2(-W/2+70,H/2-scoop*.62f-f*(H-40)/n);
    var tub=PImage(kitchenStage,"Tub",K.C("C9D8E4"),14,homes[f]-new Vector2(0,scoop*.22f),new Vector2(scoop*1f,scoop*.55f));
    var r=PNode(kitchenStage,"Scoop",homes[f],new Vector2(scoop*.9f,scoop*.9f));DrawScoop(r,flavors[f],scoop*.86f,f);
    scoopRects[f]=r;int flavor=f;Vector2 grab=Vector2.zero;
    PHandle(r,p=>{grab=r.anchoredPosition-p;r.SetAsLastSibling();kitchenPad.Interacted=true;Sound("pop",1.2f);},p=>r.anchoredPosition=p+grab*.5f,p=>ScoopDrop(flavor,placed,slots,slotAt,scoopRects,homes),null);
   }
   // The order slip (right): the clues as little pictures, each with a tick.
   float slipW=Mathf.Min(W*.42f,520);var slipAt=new Vector2(W/2-slipW/2-20,0);
   var slip=PBoard("Order slip",slipAt,new Vector2(slipW,H-40),"C99A5B","FFFDF6");
   float rowH=Mathf.Min(78,(H-80)/clues.Count);var ticks=new List<Image>();
   for(int c=0;c<clues.Count;c++){
    var y=(H-40)/2-30-(c+.5f)*rowH;var row=PNode(slip,"Clue",new Vector2(0,y),new Vector2(slipW-30,rowH-8));
    DrawClue(row,clues[c],flavors,n,rowH-12);
    var tick=N.Image(row,"Tick",new Color(.85f,.85f,.85f,1),14);tick.rectTransform.sizeDelta=new Vector2(28,28);tick.rectTransform.anchoredPosition=new Vector2(slipW/2-40,0);ticks.Add(tick);
   }
   var moveText=PMoves(new Vector2(-W*.2f,-H/2+14),300);moveText.gameObject.SetActive(false);
   var hand=KHint(()=>scoopRects[0]?scoopRects[0].anchoredPosition:Vector2.zero,()=>slotAt[0]);
   while(true){
    if(kitchenPad.Interacted&&hand)Destroy(hand);
    int ok=0;for(int c=0;c<clues.Count;c++){bool good=placed.All(x=>x>=0)?ClueHolds(clues[c],placed):CluePossible(clues[c],placed);bool full=ClueDecided(clues[c],placed);
     ticks[c].color=full&&good?K.C("4F9A2E"):full?K.C("D8462A"):new Color(.85f,.85f,.85f,1);if(full&&good)ok++;}
    KitchenMeter(ok/(float)clues.Count);
    if(placed.All(x=>x>=0)&&ok==clues.Count&&!Input.GetMouseButton(0))break;
    yield return null;
   }
   if(hand)Destroy(hand);KitchenMeter(1);
   kitchenScore=PuzzleScore(scoopMoves,n,false,.07f);scoopMoves=0;
   for(int i=0;i<n;i++){StartCoroutine(U.Pop(scoopRects[placed[i]],1.12f,.25f));yield return new WaitForSecondsRealtime(.08f);}
   yield return PSolved(coneAt+new Vector2(0,scoop*n*.4f),scoop*2);
  }
  int scoopMoves;

  void ScoopDrop(int flavor,int[] placed,List<Image> slots,List<Vector2> slotAt,RectTransform[] rects,Vector2[] homes){
   var r=rects[flavor];int from=System.Array.IndexOf(placed,flavor);
   int target=-1;float best=slots[0].rectTransform.sizeDelta.x*.7f;
   for(int i=0;i<slotAt.Count;i++){float d=Vector2.Distance(r.anchoredPosition,slotAt[i]);if(d<best){best=d;target=i;}}
   scoopMoves++;
   if(target<0){if(from>=0)placed[from]=-1;StartCoroutine(U.Move(r,homes[flavor],.18f,true));return;}
   int other=placed[target];
   if(from>=0)placed[from]=-1;
   if(other>=0&&other!=flavor){if(from>=0){placed[from]=other;StartCoroutine(U.Move(rects[other],slotAt[from],.15f));}else StartCoroutine(U.Move(rects[other],homes[other],.18f));}
   placed[target]=flavor;StartCoroutine(U.Move(r,slotAt[target],.12f));Sound("pop");
   // Higher scoops are drawn over the lower ones.
   for(int i=0;i<placed.Length;i++)if(placed[i]>=0)rects[placed[i]].SetAsLastSibling();
  }

  static bool ClueHolds(ScoopClue c,int[] p){
   int pa=System.Array.IndexOf(p,c.a),pb=c.b>=0?System.Array.IndexOf(p,c.b):-1;
   switch(c.kind){case 0:return pa==c.slot;case 1:return pa>=0&&pb>=0&&pa==pb+1;case 2:return pa>=0&&pb>=0&&pa>pb;default:return pa!=c.slot;}
  }
  // A clue is decided once the scoops it talks about are in the cone (or, for slot clues, the slot is taken).
  static bool ClueDecided(ScoopClue c,int[] p){
   int pa=System.Array.IndexOf(p,c.a);
   if(c.kind==0||c.kind==3)return pa>=0||p[c.slot]>=0;
   return pa>=0&&System.Array.IndexOf(p,c.b)>=0;
  }
  static bool CluePossible(ScoopClue c,int[] p){
   if(!ClueDecided(c,p))return true;
   int pa=System.Array.IndexOf(p,c.a);
   if(c.kind==0)return pa==c.slot;if(c.kind==3)return pa!=c.slot;
   return ClueHolds(c,p);
  }
  // Clues true for the answer, added until only the answer fits, then trimmed of the ones not needed.
  static List<ScoopClue> MakeScoopClues(int[] answer,int n){
   var pos=new int[n];for(int i=0;i<n;i++)pos[answer[i]]=i;
   var pool=new List<ScoopClue>();
   for(int a=0;a<n;a++){
    pool.Add(new ScoopClue{kind=0,a=a,b=-1,slot=pos[a]});
    for(int sl=0;sl<n;sl++)if(sl!=pos[a]&&(sl==0||sl==n-1))pool.Add(new ScoopClue{kind=3,a=a,b=-1,slot=sl});
    for(int b=0;b<n;b++)if(a!=b){if(pos[a]==pos[b]+1)pool.Add(new ScoopClue{kind=1,a=a,b=b});if(pos[a]>pos[b])pool.Add(new ScoopClue{kind=2,a=a,b=b});}
   }
   pool=pool.OrderBy(c=>c.kind==0?Random.value+.6f:Random.value).ToList(); // relational clues first: more thinking
   var perms=Permutations(n).ToList();var chosen=new List<ScoopClue>();
   foreach(var c in pool){if(Count(chosen,perms)==1)break;chosen.Add(c);}
   for(int i=chosen.Count-1;i>=0;i--){var without=chosen.Where((_,k)=>k!=i).ToList();if(Count(without,perms)==1)chosen=without;}
   return chosen.OrderBy(c=>c.kind).ToList();
  }
  static int Count(List<ScoopClue> clues,List<int[]> perms)=>perms.Count(p=>clues.All(c=>ClueHolds(c,p)));
  static IEnumerable<int[]> Permutations(int n){
   var a=Enumerable.Range(0,n).ToArray();
   IEnumerable<int[]> Rec(int k){if(k==n){yield return (int[])a.Clone();yield break;}for(int i=k;i<n;i++){(a[k],a[i])=(a[i],a[k]);foreach(var p in Rec(k+1))yield return p;(a[k],a[i])=(a[i],a[k]);}}
   return Rec(0);
  }

  // A clue in pictures: a mini cone with the flavour at its slot (crossed when "not"), or two scoops stacked
  // (touching = right on top; dots between = somewhere above).
  void DrawClue(RectTransform row,ScoopClue c,string[] flavors,int n,float h){
   var back=N.Image(row,"Back",new Color(.96f,.92f,.84f,1),12);back.rectTransform.sizeDelta=row.sizeDelta;
   float d=Mathf.Min(h/(c.kind==0||c.kind==3?n*.62f+.5f:2.4f),40);
   float x=-row.sizeDelta.x/2+60;
   if(c.kind==0||c.kind==3){
    var mini=N.Node("Mini cone",row);mini.anchoredPosition=new Vector2(x,0);
    var cone=N.Image(mini,"Cone",K.C("D9A05B"),6);cone.rectTransform.sizeDelta=new Vector2(d*.8f,d);cone.rectTransform.anchoredPosition=new Vector2(0,-h/2+d*.5f);
    for(int i=0;i<n;i++){
     var at=new Vector2(0,-h/2+d*1.0f+i*d*.62f);
     if(i==c.slot){var sc=N.Node("Scoop",mini);sc.anchoredPosition=at;sc.sizeDelta=new Vector2(d,d);DrawScoop(sc,flavors[c.a],d,c.a);
      if(c.kind==3){var x1=N.Image(sc,"Cross",K.C("D8462A"),3);x1.rectTransform.sizeDelta=new Vector2(d*1.2f,6);x1.rectTransform.localRotation=Quaternion.Euler(0,0,45);var x2=N.Image(sc,"Cross",K.C("D8462A"),3);x2.rectTransform.sizeDelta=new Vector2(d*1.2f,6);x2.rectTransform.localRotation=Quaternion.Euler(0,0,-45);}}
     else{var ghost=N.Image(mini,"Empty",new Color(.75f,.7f,.62f,.45f),(int)(d/2));ghost.rectTransform.sizeDelta=new Vector2(d*.8f,d*.8f);ghost.rectTransform.anchoredPosition=at;}
    }
   }
   else{
    float big=Mathf.Min(h*.46f,40);
    var low=N.Node("Below",row);low.anchoredPosition=new Vector2(x,-big*.45f);low.sizeDelta=new Vector2(big,big);DrawScoop(low,flavors[c.b],big,c.b);
    var high=N.Node("Above",row);high.anchoredPosition=new Vector2(x,c.kind==1?big*.4f:big*.62f);high.sizeDelta=new Vector2(big,big);DrawScoop(high,flavors[c.a],big,c.a);
    if(c.kind==2){high.anchoredPosition=new Vector2(x+big*1.2f,big*.55f);low.anchoredPosition=new Vector2(x-big*.2f,-big*.45f);
     for(int k=0;k<3;k++){var dot=N.Image(row,"Dot",K.C("8A7560"),4);dot.rectTransform.sizeDelta=new Vector2(7,7);dot.rectTransform.anchoredPosition=new Vector2(x+big*.25f+k*big*.25f,-big*.2f+k*big*.25f);}}
   }
  }

  // A scoop drawn in code until the Blender art (Game/pz_scoop_<flavour>) exists.
  void DrawScoop(RectTransform parent,string flavor,float size,int seed){
   var art=K.Icon("Game/pz_scoop_"+flavor);
   if(art){var i=N.Image(parent,"Art",Color.white,0);i.sprite=art;i.preserveAspect=true;i.rectTransform.sizeDelta=new Vector2(size,size);return;}
   var look=ScoopLook[flavor];
   var drip=N.Image(parent,"Drip",K.C(look.body),(int)(size/4));drip.rectTransform.sizeDelta=new Vector2(size*.92f,size*.32f);drip.rectTransform.anchoredPosition=new Vector2(0,-size*.3f);
   var ball=N.Image(parent,"Ball",K.C(look.body),(int)(size/2));ball.rectTransform.sizeDelta=new Vector2(size*.86f,size*.8f);ball.rectTransform.anchoredPosition=new Vector2(0,size*.04f);
   for(int k=0;k<5;k++){var dot=N.Image(parent,"Bit",K.C(look.dots),4);float d=size*.07f;dot.rectTransform.sizeDelta=new Vector2(d,d);dot.rectTransform.anchoredPosition=new Vector2((Noise(seed,k)-.5f)*size*.5f,(Noise(k,seed+5)-.5f)*size*.4f);}
   var gloss=N.Image(parent,"Gloss",new Color(1,1,1,.4f),10);gloss.rectTransform.sizeDelta=new Vector2(size*.3f,size*.12f);gloss.rectTransform.anchoredPosition=new Vector2(-size*.15f,size*.25f);
  }
 }
}
