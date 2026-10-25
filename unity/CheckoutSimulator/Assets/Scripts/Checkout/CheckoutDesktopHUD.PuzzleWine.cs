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
 // Adega — "Medida exata" (step kind "decant"): the blend needs exactly so many litres, but the cellar only has unmarked
 // vessels of fixed sizes (a barrel, a demijohn, a jug…). Tap one, then another, to pour from it until the first is empty
 // or the second is full. Get the asked amount into any vessel. The classic decanting puzzle; a solver picks a deal with a
 // fitting number of pours for the level and gives the ideal. Desfazer / Recomeçar help (both count as moves).
 public partial class CheckoutDesktopHUD {
  const string WineColor="5A0E1E";   // deep bordeaux (Lucas 24/10: the old red read too light for wine)
  IEnumerator StepDecant(DesktopKitchenStep s){
   int level=Mathf.Clamp(s.count,1,3);
   (int[] caps,int[] start,int target,int par) deal=default;
   int minPar=level==1?3:level==2?5:7,maxPar=level==1?5:level==2?7:10;
   for(int attempt=0;attempt<400;attempt++){
    int vcount=level==3&&Random.value<.5f?4:3;
    var caps=new int[vcount];caps[0]=Random.Range(7,level==1?10:13);
    for(int v=1;v<vcount;v++)caps[v]=Random.Range(2,caps[v-1]);
    if(caps.Distinct().Count()!=vcount)continue;
    var start=new int[vcount];start[0]=caps[0];
    int target=Random.Range(1,caps[0]);if(caps.Contains(target))continue;
    int par=SolveDecant(caps,start,target);
    if(par>=minPar&&par<=maxPar){deal=(caps,start,target,par);break;}
   }
   if(deal.caps==null)deal=(new[]{8,5,3},new[]{8,0,0},4,7);
   var cap=deal.caps;var amount=(int[])deal.start.Clone();int count=cap.Length;

   float W=StageW,H=StageH;float maxCap=cap.Max();
   float colW=Mathf.Min(170,(W-120)/count-30),fullH=H-150;
   var bases=new List<Vector2>();var vessels=new List<RectTransform>();var wines=new List<Image>();var labels=new List<TextMeshProUGUI>();
   // The Blender glass vessels (demijohn, carafe, mug + masks): the wine is clipped to the inside of each glass.
   var arts=CheckoutPuzzleArt.Vessels;bool useArt=arts.All(a=>K.Icon("Game/"+a.id)!=null&&K.Icon("Game/"+a.id+"_mask")!=null);
   var glasses=new PGlassParts[count];var pours=new List<Image>[count];
   if(useArt){
    // Bigger vessels, bigger glass (by rank: the caps go down); everything scaled to fit left of the goal card.
    var hs=new float[count];var ws=new float[count];
    for(int v=0;v<count;v++){var a=arts[Mathf.Min(v,2)];hs[v]=(H-110)*(.5f+.5f*cap[v]/maxCap)*(v>=3?.85f:1);ws[v]=hs[v]*a.size.x/a.size.y;}
    float room=W-330,need=ws.Sum()*.82f+18*(count-1),fit=Mathf.Min(1,room/need);
    float x=-W/2+20+(room-need*fit)/2;
    for(int v=0;v<count;v++){
     var a=arts[Mathf.Min(v,2)];float h=hs[v]*fit,w=ws[v]*fit;x+=w*.41f;
     var at=new Vector2(x,-H/2+18+h/2);x+=w*.41f+18*fit;bases.Add(at);
     var g=PGlass(kitchenStage,a,at,h);glasses[v]=g;pours[v]=new List<Image>();vessels.Add(g.root);wines.Add(null);
     float glassTop=(a.inside.yMax-a.size.y/2)*g.scale;
     var tag=PImage(g.root,"Tag",K.C("FFF7EC"),10,new Vector2((a.inside.center.x-a.size.x/2)*g.scale,Mathf.Min(h/2-10,glassTop+30)),new Vector2(96,34));
     labels.Add(PText(tag.transform,"",17,K.Ink,Vector2.zero,new Vector2(94,32),K.Number));
     int index=v;PHandle(g.root,null,null,null,()=>VesselTap(index));
    }
   }
   else for(int v=0;v<count;v++){
    float h=Mathf.Max(70,fullH*cap[v]/maxCap),w=colW*(.7f+.3f*cap[v]/maxCap);
    var at=new Vector2((v-(count-1)/2f)*(colW+30)-W*.08f,-H/2+50+h/2);bases.Add(at);
    var vessel=PNode(kitchenStage,"Vessel",at,new Vector2(w,h));PShadow(vessel,new Vector2(w,h*.25f));
    var body=N.Image(vessel,"Body",v==0?K.C("8A5A2B"):new Color(.8f,.92f,.88f,.45f),18);body.rectTransform.sizeDelta=new Vector2(w,h);
    if(v==0)for(int k=1;k<4;k++){var hoop=N.Image(vessel,"Hoop",K.C("4A3624"),4);hoop.rectTransform.sizeDelta=new Vector2(w+6,8);hoop.rectTransform.anchoredPosition=new Vector2(0,-h/2+h*k/4f);}
    var window=N.Image(vessel,"Window",new Color(1,1,1,.18f),14);window.rectTransform.sizeDelta=new Vector2(w-22,h-22);
    var wine=N.Image(vessel,"Wine",K.C(WineColor),12);var wr=wine.rectTransform;wr.anchorMin=wr.anchorMax=new Vector2(.5f,0);wr.pivot=new Vector2(.5f,0);wr.anchoredPosition=new Vector2(0,11);
    wines.Add(wine);
    var tag=PImage(vessel,"Tag",K.C("FFF7EC"),10,new Vector2(0,h/2+24),new Vector2(96,34));
    labels.Add(PText(tag.transform,"",17,K.Ink,Vector2.zero,new Vector2(94,32),K.Number));
    vessels.Add(vessel);int index=v;PHandle(vessel,null,null,null,()=>VesselTap(index));
   }
   // The goal card (right).
   var goal=PBoard("Goal",new Vector2(W/2-150,H/2-110),new Vector2(250,170),WineColor,"FFF7F2");
   var glass=N.Image(goal,"Glass",K.C(WineColor),20);glass.rectTransform.sizeDelta=new Vector2(56,56);glass.rectTransform.anchoredPosition=new Vector2(0,26);
   PText(goal,$"{deal.target} L",34,K.C(WineColor),new Vector2(0,-40),new Vector2(220,46),K.Headline);
   int moves=0,selected=-1;var history=new Stack<int[]>();
   void Redraw(){
    for(int v=0;v<count;v++){
     labels[v].text=$"{amount[v]}/{cap[v]} L";
     if(!useArt){float h=vessels[v].sizeDelta.y-22;wines[v].rectTransform.sizeDelta=new Vector2(vessels[v].sizeDelta.x-22,h*amount[v]/cap[v]);continue;}
     foreach(var l in pours[v])if(l)Destroy(l.gameObject);pours[v].Clear();
     if(amount[v]<=0)continue;
     var a=glasses[v].v;float level=a.inner.yMin+a.inner.height*amount[v]/cap[v];
     pours[v].Add(PLiquid(glasses[v],K.C(WineColor),0,level));
     pours[v].Add(PLiquid(glasses[v],K.C("8C2A3C"),level-4,level));   // the surface catches a little light
    }
   }
   Redraw();
   vesselTap=v=>{
    kitchenPad.Interacted=true;
    if(selected<0){if(amount[v]==0){Sound("bonk");return;}selected=v;StartCoroutine(U.Move(vessels[v],bases[v]+new Vector2(0,24),.1f));Sound("pop",1.2f);return;}
    if(selected==v){StartCoroutine(U.Move(vessels[v],bases[v],.1f));selected=-1;return;}
    int pour=Mathf.Min(amount[selected],cap[v]-amount[v]);
    if(pour<=0){Sound("bonk");StartCoroutine(U.Pop(vessels[v],1.05f,.15f));return;}
    history.Push((int[])amount.Clone());amount[selected]-=pour;amount[v]+=pour;moves++;
    Sound("whoosh",.9f);StartCoroutine(U.Move(vessels[selected],bases[selected],.12f));selected=-1;Redraw();
   };
   PButton("Desfazer","secondary",new Vector2(W/2-150,-H/2+92),new Vector2(200,46),()=>{if(history.Count==0)return;amount=history.Pop();moves++;if(selected>=0){vessels[selected].anchoredPosition=bases[selected];selected=-1;}Redraw();});
   PButton("Recomeçar","secondary",new Vector2(W/2-150,-H/2+36),new Vector2(200,46),()=>{amount=(int[])deal.start.Clone();history.Clear();moves++;if(selected>=0){vessels[selected].anchoredPosition=bases[selected];selected=-1;}Redraw();});
   var moveText=PMoves(new Vector2(W/2-150,H/2-222),280);
   var hand=KHint(()=>vessels[0].anchoredPosition,()=>vessels[1].anchoredPosition,true);
   while(!amount.Contains(deal.target)){
    if(kitchenPad.Interacted&&hand)Destroy(hand);
    PMovesText(moveText,moves,deal.par);KitchenMeter(Mathf.Min(.9f,moves/(float)(deal.par+2)));
    yield return null;
   }
   if(hand)Destroy(hand);PMovesText(moveText,moves,deal.par);KitchenMeter(1);vesselTap=null;
   int hit=System.Array.IndexOf(amount,deal.target);StartCoroutine(U.Pop(vessels[hit],1.12f,.3f));
   kitchenScore=PuzzleScore(moves,deal.par,false,.06f);
   yield return PSolved(bases[hit],200);
  }
  System.Action<int> vesselTap;
  void VesselTap(int v)=>vesselTap?.Invoke(v);

  // Fewest pours from `start` until some vessel holds `target` (-1 = impossible).
  static int SolveDecant(int[] caps,int[] start,int target){
   string Key(int[] a)=>string.Join(",",a);
   var seen=new HashSet<string>{Key(start)};var frontier=new List<int[]>{start};int depth=0;
   while(frontier.Count>0&&depth<20){
    var next=new List<int[]>();
    foreach(var s in frontier){
     if(s.Contains(target))return depth;
     for(int a=0;a<s.Length;a++)for(int b=0;b<s.Length;b++){if(a==b||s[a]==0||s[b]==caps[b])continue;var c=(int[])s.Clone();int p=Mathf.Min(c[a],caps[b]-c[b]);c[a]-=p;c[b]+=p;if(seen.Add(Key(c)))next.Add(c);}
    }
    frontier=next;depth++;
   }
   return -1;
  }
 }
}
