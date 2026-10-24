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
 // Peixaria — "Pedidos na balança" (step kind "orders"): customers' orders hang over the ice counter, each one a tray
 // on a scale with the weight asked for. Fish, fillets and shrimp of different weights lie on the ice; every piece must
 // go to some order and every order must close on exactly its weight. Drag a piece onto a tray (or back onto the ice).
 // The deal is made from real splits, so it always has a solution.
 public partial class CheckoutDesktopHUD {
  static readonly Dictionary<string,(string body,string belly,float w,float h,int[] grams)> FishLook=new Dictionary<string,(string,string,float,float,int[])>{
   {"peixe",("7F96A8","D9E2E8",1.9f,.8f,new[]{400,500,600,700,800})},
   {"file",("F3A68A","FBD3C2",1.3f,.62f,new[]{150,200,250,300})},
   {"camarao",("F08C5C","F7C39E",.9f,.72f,new[]{100,150,200})},
   {"salmao",("F07F4E","FFD0B5",1.4f,.62f,new[]{200,250,300,350})},
  };
  sealed class FishPiece {public string kind;public int grams;public RectTransform rect;public Vector2 home;public int tray=-1;}

  IEnumerator StepOrders(DesktopKitchenStep s){
   int trays=Mathf.Clamp(s.count,2,4),pieceCount=Mathf.Clamp(s.singles,trays*2,12);
   var kinds=(s.pieces??new string[0]).Where(FishLook.ContainsKey).ToArray();if(kinds.Length==0)kinds=new[]{"peixe","file"};
   // Deal: share the pieces among the trays (at least 2 each), the targets are their sums.
   var pieces=new List<FishPiece>();var targets=new int[trays];
   for(int i=0;i<pieceCount;i++){var k=kinds[Random.Range(0,kinds.Length)];var g=FishLook[k].grams[Random.Range(0,FishLook[k].grams.Length)];pieces.Add(new FishPiece{kind=k,grams=g});}
   var owner=Enumerable.Range(0,pieceCount).Select(i=>i<trays*2?i/2:Random.Range(0,trays)).ToArray();
   for(int i=0;i<pieceCount;i++)targets[owner[i]]+=pieces[i].grams;
   pieces=pieces.OrderBy(_=>Random.value).ToList();

   float W=StageW,H=StageH;
   // Orders on top: a tray on a scale each.
   // The Blender scale (steel body, weighing plate, display window) and crushed-ice bed, when present.
   var scaleArt=K.Icon("Game/pz_scale");var iceArt=K.Icon("Game/pz_icebed");
   float trayW=Mathf.Min(260,(W-80)/trays-30),trayH=scaleArt!=null?trayW*CheckoutPuzzleArt.ScaleSize.y/CheckoutPuzzleArt.ScaleSize.x:Mathf.Min(150,H*.38f);
   var trayRects=new List<RectTransform>();var readouts=new List<(Image back,TextMeshProUGUI text)>();
   for(int t=0;t<trays;t++){
    var at=new Vector2((t-(trays-1)/2f)*(trayW+30),H/2-trayH/2-14);
    if(scaleArt!=null){
     var scaleImg=PImage(kitchenStage,"Scale",Color.white,0,at,new Vector2(trayW,trayH));scaleImg.sprite=scaleArt;
     float k=trayW/CheckoutPuzzleArt.ScaleSize.x;var d=CheckoutPuzzleArt.ScaleDisplay;
     var window=new Vector2((d.center.x-CheckoutPuzzleArt.ScaleSize.x/2)*k,(d.center.y-CheckoutPuzzleArt.ScaleSize.y/2)*k);
     var glow=PImage(scaleImg.transform,"Readout",new Color(0,0,0,0),6,window,new Vector2(d.width*k,d.height*k));
     var text2=PText(glow.transform,"",Mathf.Clamp(d.height*k*.62f,13,18),K.C("9BE7A0"),Vector2.zero,new Vector2(d.width*k-6,d.height*k),K.Number);
     trayRects.Add(scaleImg.rectTransform);readouts.Add((glow,text2));continue;
    }
    var scale=PImage(kitchenStage,"Scale",K.C("D9DEE3"),18,at,new Vector2(trayW,trayH));
    PImage(scale.transform,"Plate",K.C("F7FAFC"),16,new Vector2(0,10),new Vector2(trayW-24,trayH-56));
    var back=PImage(scale.transform,"Readout",K.C("2E3A4A"),10,new Vector2(0,-trayH/2+22),new Vector2(trayW-40,34));
    var text=PText(back.transform,"",18,Color.white,Vector2.zero,new Vector2(trayW-44,32),K.Number);
    trayRects.Add(scale.rectTransform);readouts.Add((back,text));
   }
   // Ice bed below with the pieces.
   float iceH=H-trayH-60;var iceAt=new Vector2(0,-H/2+iceH/2+8);
   if(iceArt!=null){var bed=PImage(kitchenStage,"Ice",Color.white,0,iceAt,new Vector2(W-40,iceH+10));bed.sprite=iceArt;}
   else{
    var ice=PImage(kitchenStage,"Ice",K.C("CFE8F3"),22,iceAt,new Vector2(W-60,iceH));
    for(int i=0;i<40;i++){var cube=N.Image(ice.transform,"Cube",new Color(1,1,1,.45f),6);float d=10+Noise(i,1)*14;cube.rectTransform.sizeDelta=new Vector2(d,d);cube.rectTransform.anchoredPosition=new Vector2((Noise(i,2)-.5f)*(W-90),(Noise(i,5)-.5f)*(iceH-30));cube.rectTransform.localRotation=Quaternion.Euler(0,0,Noise(i,8)*90);}
   }
   bool lcd=scaleArt!=null;
   float unit=Mathf.Min(82,(W-100)/(pieceCount*1.1f+1));
   int perRow=Mathf.CeilToInt(pieceCount/(iceH>unit*2.4f?2f:1f));
   for(int i=0;i<pieces.Count;i++){
    var p=pieces[i];var look=FishLook[p.kind];var size=new Vector2(look.w*unit,look.h*unit);
    int row=i/perRow,col=i%perRow;int inRow=Mathf.Min(perRow,pieces.Count-row*perRow);
    p.home=iceAt+new Vector2((col-(inRow-1)/2f)*(W-120)/Mathf.Max(1,perRow),(row==0?1:-1)*(perRow<pieceCount?iceH*.22f:0));
    p.rect=PNode(kitchenStage,"Fish",p.home,size);DrawFish(p.rect,p.kind,size,i);
    var tag=PImage(p.rect,"Tag",K.C("FFF7EC"),10,new Vector2(0,-size.y/2-4),new Vector2(78,28));
    PText(tag.transform,$"{p.grams} g",15,K.Ink,Vector2.zero,new Vector2(76,26),K.Number);
    var piece=p;Vector2 grab=Vector2.zero;
    PHandle(p.rect,pos=>{grab=piece.rect.anchoredPosition-pos;piece.rect.SetAsLastSibling();kitchenPad.Interacted=true;Sound("pop",1.2f);},pos=>piece.rect.anchoredPosition=pos+grab*.5f,pos=>FishDrop(piece,pieces,trayRects),null);
   }
   int moves=0;int par=pieceCount;
   var moveText=PMoves(new Vector2(-W/2+190,-H/2+20),340);
   var hand=KHint(()=>pieces[0].rect.anchoredPosition,()=>trayRects[0].anchoredPosition);
   bool Solved(){if(pieces.Any(q=>q.tray<0))return false;for(int t=0;t<trays;t++)if(pieces.Where(q=>q.tray==t).Sum(q=>q.grams)!=targets[t])return false;return true;}
   fishMoves=0;
   while(!Solved()||Input.GetMouseButton(0)){
    if(kitchenPad.Interacted&&hand)Destroy(hand);
    for(int t=0;t<trays;t++){
     int sum=pieces.Where(q=>q.tray==t).Sum(q=>q.grams);
     readouts[t].text.text=$"{Kg(sum)} / {Kg(targets[t])}";
     if(lcd)readouts[t].text.color=sum==targets[t]?K.C("7CF08A"):sum>targets[t]?K.C("FF7A66"):K.C("CFE9FF");
     else readouts[t].back.color=sum==targets[t]?K.C("4F9A2E"):sum>targets[t]?K.C("D8462A"):K.C("2E3A4A");
    }
    moves=fishMoves;PMovesText(moveText,moves,par);
    KitchenMeter(pieces.Count(q=>q.tray>=0)/(float)pieceCount*.9f);
    yield return null;
   }
   for(int t=0;t<trays;t++){readouts[t].text.text=$"{Kg(targets[t])} / {Kg(targets[t])}";if(lcd)readouts[t].text.color=K.C("7CF08A");else readouts[t].back.color=K.C("4F9A2E");StartCoroutine(U.Pop(trayRects[t],1.06f,.25f));}
   if(hand)Destroy(hand);
   kitchenScore=PuzzleScore(fishMoves,par,false);
   yield return PSolved(new Vector2(0,H/2-trayH/2),W*.35f);
  }
  int fishMoves;
  static string Kg(int grams)=>grams>=1000?(grams/1000f).ToString("0.00",System.Globalization.CultureInfo.GetCultureInfo("pt-BR"))+" kg":grams+" g";

  void FishDrop(FishPiece p,List<FishPiece> all,List<RectTransform> trays){
   int target=-1;for(int t=0;t<trays.Count;t++)if(PInside(p.rect.anchoredPosition,trays[t],10)){target=t;break;}
   fishMoves++;
   if(target<0){p.tray=-1;StartCoroutine(U.Move(p.rect,p.home,.18f,true));return;}
   p.tray=target;Sound("pop");
   // Lay the tray's pieces side by side on its plate.
   var on=all.Where(q=>q.tray==target).ToList();var tr=trays[target];
   for(int i=0;i<on.Count;i++){
    float span=tr.sizeDelta.x-70;float x=on.Count==1?0:(i/(on.Count-1f)-.5f)*span;
    var to=tr.anchoredPosition+new Vector2(x,14+(i%2)*10);StartCoroutine(U.Move(on[i].rect,to,.15f));
    on[i].rect.localScale=Vector3.one*(on.Count>3?.75f:.9f);
   }
   foreach(var q in all.Where(q=>q.tray<0))q.rect.localScale=Vector3.one;
  }

  // Fish drawn in code until the Blender art (Game/pz_fish_<kind>) exists.
  void DrawFish(RectTransform parent,string kind,Vector2 size,int seed){
   var art=K.Icon("Game/pz_fish_"+kind);
   if(art){var i=N.Image(parent,"Art",Color.white,0);i.sprite=art;i.preserveAspect=true;i.rectTransform.sizeDelta=size*1.15f;return;}   // the art has its own soft shadow
   PShadow(parent,size);
   var look=FishLook[kind];
   if(kind=="peixe"){
    var body=N.Image(parent,"Body",K.C(look.body),(int)(size.y/2));body.rectTransform.sizeDelta=new Vector2(size.x*.8f,size.y*.8f);body.rectTransform.anchoredPosition=new Vector2(size.x*.06f,0);
    var belly=N.Image(parent,"Belly",K.C(look.belly),(int)(size.y/3));belly.rectTransform.sizeDelta=new Vector2(size.x*.6f,size.y*.3f);belly.rectTransform.anchoredPosition=new Vector2(size.x*.06f,-size.y*.14f);
    var tail=N.Image(parent,"Tail",K.C(look.body),6);tail.rectTransform.sizeDelta=new Vector2(size.y*.5f,size.y*.5f);tail.rectTransform.anchoredPosition=new Vector2(-size.x*.4f,0);tail.rectTransform.localRotation=Quaternion.Euler(0,0,45);
    var eye=N.Image(parent,"Eye",Color.white,8);eye.rectTransform.sizeDelta=new Vector2(size.y*.18f,size.y*.18f);eye.rectTransform.anchoredPosition=new Vector2(size.x*.33f,size.y*.08f);
    var pupil=N.Image(eye.transform,"Pupil",K.C("1D2B4F"),6);pupil.rectTransform.sizeDelta=new Vector2(size.y*.09f,size.y*.09f);
   }
   else if(kind=="camarao"){
    for(int k=0;k<3;k++){var seg=N.Image(parent,"Seg",Color.Lerp(K.C(look.body),K.C(look.belly),k*.3f),(int)(size.y/3));seg.rectTransform.sizeDelta=new Vector2(size.x*.5f,size.y*.5f);seg.rectTransform.anchoredPosition=new Vector2((k-1)*size.x*.22f,Mathf.Abs(k-1)*-size.y*.12f);}
   }
   else{
    var body=N.Image(parent,"Fillet",K.C(look.body),(int)(size.y/2.2f));body.rectTransform.sizeDelta=new Vector2(size.x*.9f,size.y*.8f);
    for(int k=0;k<4;k++){var line=N.Image(parent,"Line",new Color(1,1,1,.5f),3);line.rectTransform.sizeDelta=new Vector2(4,size.y*.6f);line.rectTransform.anchoredPosition=new Vector2((k-1.5f)*size.x*.18f,0);line.rectTransform.localRotation=Quaternion.Euler(0,0,25);}
   }
   var gloss=N.Image(parent,"Gloss",new Color(1,1,1,.3f),10);gloss.rectTransform.sizeDelta=new Vector2(size.x*.4f,size.y*.14f);gloss.rectTransform.anchoredPosition=new Vector2(0,size.y*.22f);
  }
 }
}
