using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
using Random = UnityEngine.Random;
namespace Checkout {
 // The bakery's batch puzzle (step kind "tray", desktop/pages/kitchen.ts fornada()): Lucas 24/10 wanted the sector games
 // to be real puzzles that make the player think. The doughs of the batch are pieces of different lengths on a grid
 // (pão francês 1×1, pão de forma 1×2, baguete 1×3, trança 1×4, pão redondo 2×2) and they must fill the baking tray
 // with no gap. A tray is dealt fresh every time from a random tiling, so it always has a solution; the player may find
 // any other. Drag a dough onto the tray (it snaps to the cells, a green/red shadow shows where it lands), tap it to turn
 // it, drag a placed one to take it back. Placing each piece once is perfect; extra moves and the hint cost score.
 // When the tray is full the breads bake (they turn golden) and the recipe goes on to the oven.
 public partial class CheckoutDesktopHUD {
  // Piece set: footprint in cells and the dough / baked colours used until the Blender art lands
  // (Resources/CheckoutDesktop/Game/pz_bread_<id>_raw / _baked replace the drawn shapes when they exist).
  static readonly Dictionary<string,(int w,int h,string raw,string baked)> BreadPieces=new Dictionary<string,(int,int,string,string)>{
   {"frances",(1,1,"F3DDB4","D9902F")},{"forma",(1,2,"F6E3C2","C9853A")},{"baguete",(1,3,"EED7AA","CF8A2E")},
   {"tranca",(1,4,"F4D9A0","B8732A")},{"redondo",(2,2,"EBD3A6","B9782F")},
  };

  sealed class TrayPiece {
   public string id;public int w,h;public bool turned;public int col=-1,row=-1;
   public RectTransform rect,body;public Image dough,baked,art,artBaked,gloss;public List<Image> scores=new List<Image>();public Vector2 home;public float homeScale;
   public int W=>turned?h:w;public int H=>turned?w:h;public bool Placed=>col>=0;
  }
  sealed class TrayState {
   public int cols,rows;public float cell;public Vector2 origin; // origin = top-left corner of the tray (stage coords)
   public int[,] owner;public List<TrayPiece> pieces=new List<TrayPiece>();public List<RectInt> solution=new List<RectInt>();
   public int moves,par;public bool hint;public RectTransform ghost;public Image ghostImage;
   public Vector2 CellCenter(int c,int r,int w,int h)=>origin+new Vector2((c+w*.5f)*cell,-(r+h*.5f)*cell);
   public bool Fits(int c,int r,int w,int h,TrayPiece self){
    if(c<0||r<0||c+w>cols||r+h>rows)return false;
    for(int x=c;x<c+w;x++)for(int y=r;y<r+h;y++){int o=owner[x,y];if(o>=0&&(self==null||pieces[o]!=self))return false;}
    return true;
   }
   public void Mark(TrayPiece p,bool on){int i=pieces.IndexOf(p);for(int x=p.col;x<p.col+p.W;x++)for(int y=p.row;y<p.row+p.H;y++)owner[x,y]=on?i:-1;}
   public int Filled(){int n=0;for(int x=0;x<cols;x++)for(int y=0;y<rows;y++)if(owner[x,y]>=0)n++;return n;}
  }
  TrayState tray;

  // A random tiling of the tray with the allowed pieces (backtracking from the top-left free cell): the deal.
  static List<(string id,RectInt at)> DealTray(int cols,int rows,string[] allowed,int maxSingles){
   var kinds=allowed.Where(BreadPieces.ContainsKey).ToList();if(kinds.Count==0)kinds.Add("frances");
   List<(string,RectInt)> best=null;int bestScore=int.MinValue;
   for(int attempt=0;attempt<60;attempt++){
    var grid=new bool[cols,rows];var placed=new List<(string,RectInt)>();int singles=0,steps=0;
    bool Fill(){
     if(++steps>4000)return false;
     int fc=-1,fr=-1;for(int r=0;r<rows&&fc<0;r++)for(int c=0;c<cols;c++)if(!grid[c,r]){fc=c;fr=r;break;}
     if(fc<0)return true;
     var options=new List<(string id,int w,int h,float weight)>();
     foreach(var k in kinds){var d=BreadPieces[k];
      foreach(var (w,h) in d.w==d.h?new[]{(d.w,d.h)}:new[]{(d.w,d.h),(d.h,d.w)}){
       if(k=="frances"&&singles>=maxSingles)continue;
       if(fc+w>cols||fr+h>rows)continue;bool ok=true;for(int x=fc;x<fc+w&&ok;x++)for(int y=fr;y<fr+h&&ok;y++)if(grid[x,y])ok=false;
       if(ok)options.Add((k,w,h,Mathf.Pow(w*h,1.4f)*Random.Range(.5f,1.5f)));
      }}
     foreach(var o in options.OrderByDescending(o=>o.weight)){
      for(int x=fc;x<fc+o.w;x++)for(int y=fr;y<fr+o.h;y++)grid[x,y]=true;
      placed.Add((o.id,new RectInt(fc,fr,o.w,o.h)));if(o.id=="frances")singles++;
      if(Fill())return true;
      placed.RemoveAt(placed.Count-1);if(o.id=="frances")singles--;
      for(int x=fc;x<fc+o.w;x++)for(int y=fr;y<fr+o.h;y++)grid[x,y]=false;
     }
     return false;
    }
    if(!Fill())continue;
    // Interesting deals: several kinds of dough, long ones, few little rolls.
    int score=placed.Select(p=>p.Item1).Distinct().Count()*10-placed.Count(p=>p.Item1=="frances")*4+placed.Count(p=>p.Item2.width*p.Item2.height>=3)*3;
    if(score>bestScore){bestScore=score;best=placed;}
    if(attempt>=12&&best!=null)break;
   }
   return best??new List<(string,RectInt)>();
  }

  IEnumerator StepTray(DesktopKitchenStep s){
   int cols=s.grid!=null&&s.grid.Length>=2?Mathf.Clamp((int)s.grid[0],2,8):4,rows=s.grid!=null&&s.grid.Length>=2?Mathf.Clamp((int)s.grid[1],2,6):3;
   var deal=DealTray(cols,rows,s.pieces??new[]{"frances","forma","baguete"},Mathf.Max(0,s.singles));
   var t=tray=new TrayState{cols=cols,rows=rows,owner=new int[cols,rows],par=deal.Count};
   for(int x=0;x<cols;x++)for(int y=0;y<rows;y++)t.owner[x,y]=-1;
   foreach(var d in deal)t.solution.Add(d.at);

   // Layout: the tray on the left of the bench, the doughs to its right.
   float W=kitchenStage.rect.width,H=kitchenStage.rect.height;
   float trayArea=W*.56f;t.cell=Mathf.Floor(Mathf.Min((trayArea-70)/cols,(H-70)/rows));
   float tw=t.cell*cols,th=t.cell*rows;var center=new Vector2(-W/2+30+trayArea/2,0);
   t.origin=center+new Vector2(-tw/2,th/2);
   var rim=KKeep(N.Image(kitchenStage,"Tray rim",K.C("3B3F46"),18));Place(rim.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),center,new Vector2(tw+34,th+34));
   var shade=KKeep(N.Image(kitchenStage,"Tray shadow",new Color(.15f,.08f,.03f,.35f),0));shade.sprite=U.Glow();Place(shade.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),center-new Vector2(0,14),new Vector2(tw+120,th+90));shade.transform.SetSiblingIndex(rim.transform.GetSiblingIndex());
   var traySprite=K.Icon("Game/pz_tray");
   var bed=N.Image(rim.transform,"Bed",traySprite?Color.white:K.C("2A2D33"),traySprite?0:10);if(traySprite)bed.sprite=traySprite;Stretch(bed.rectTransform,new Vector2(17,17),new Vector2(-17,-17));
   for(int x=0;x<cols;x++)for(int y=0;y<rows;y++){
    var cellImg=N.Image(bed.transform,"Cell",new Color(1,1,1,.06f),8);Place(cellImg.rectTransform,new Vector2(0,1),new Vector2(0,1),new Vector2(0,1),new Vector2(x*t.cell+3,-y*t.cell-3),new Vector2(t.cell-6,t.cell-6));
   }
   var ghost=KKeep(N.Image(kitchenStage,"Landing",new Color(.4f,.85f,.35f,.35f),12));t.ghost=ghost.rectTransform;t.ghostImage=ghost;ghost.gameObject.SetActive(false);

   // The doughs, in a loose row to the right (smaller until picked up), on a floured board so they stand out.
   var shuffled=deal.OrderBy(_=>Random.value).ToList();
   float paletteX0=center.x+tw/2+60,paletteW=W/2-20-paletteX0;
   var board=KKeep(N.Image(kitchenStage,"Dough board",K.C("8A5A2B"),22));
   Place(board.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(paletteX0+paletteW/2,0),new Vector2(paletteW+30,H-24));
   var boardFace=N.Image(board.transform,"Face",K.C("FFF3DF"),20);Stretch(boardFace.rectTransform,new Vector2(4,7),new Vector2(-4,-4));
   float scale=.8f;List<Vector2> homes=null;
   for(;scale>.3f;scale-=.05f){homes=FlowHomes(shuffled.Select(d=>BreadPieces[d.id]).Select(d=>new Vector2(d.w,d.h)*t.cell*scale).ToList(),paletteX0,paletteW,H/2-28,H-128);if(homes!=null)break;}
   homes??=shuffled.Select((_,i)=>new Vector2(paletteX0+paletteW/2,H/2-60-i*30)).ToList();
   for(int i=0;i<shuffled.Count;i++){
    var d=BreadPieces[shuffled[i].id];var p=new TrayPiece{id=shuffled[i].id,w=d.w,h=d.h,home=homes[i],homeScale=scale};
    p.rect=KKeep(N.Image(kitchenStage,"Dough "+p.id,new Color(1,1,1,0),0)).rectTransform;p.rect.GetComponent<Image>().raycastTarget=true;
    Place(p.rect,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),p.home,new Vector2(d.w*t.cell,d.h*t.cell));p.rect.localScale=Vector3.one*scale;
    p.body=N.Node("Body",p.rect);p.body.anchorMin=p.body.anchorMax=p.body.pivot=new Vector2(.5f,.5f);p.body.sizeDelta=new Vector2(d.w*t.cell,d.h*t.cell);
    DrawDough(p,t.cell);
    var handle=p.rect.gameObject.AddComponent<TrayHandle>();handle.Space=kitchenStage;
    var piece=p;handle.Began=pos=>TrayPick(piece,pos);handle.Moved=pos=>TrayDrag(piece,pos);handle.Ended=pos=>TrayDrop(piece,pos);handle.Tapped=()=>TrayTurn(piece);
    t.pieces.Add(p);
   }

   // Hint (one per tray): shows where one dough goes, or which placed one is in the way.
   var hintButton=U.Button(kitchenStage,"Dica","secondary",()=>TrayHint(),50,18);Destroy(hintButton.GetComponent<LayoutElement>());
   Place((RectTransform)hintButton.transform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(W/2-20-80,-H/2+46),new Vector2(150,50));kitchenScene.Add(hintButton.gameObject);
   var counter=KKeep(N.Text(kitchenStage,"Moves",K.Label,17,K.Ink));counter.alignment=TextAlignmentOptions.Left;counter.textWrappingMode=TextWrappingModes.NoWrap;
   Place(counter.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(0,.5f),new Vector2(paletteX0,-H/2+46),new Vector2(paletteW-170,30));

   var first=t.pieces.OrderByDescending(p=>p.w*p.h).First();
   var hand=KHint(()=>first.rect?first.rect.anchoredPosition:Vector2.zero,()=>t.origin+new Vector2(first.W*t.cell*.5f,-first.H*t.cell*.5f));
   int total=cols*rows;
   while(t.Filled()<total){
    if(kitchenPad.Interacted&&hand)Destroy(hand);
    counter.text=$"Movimentos: {t.moves}  ·  ideal: {t.par}";
    KitchenMeter((float)t.Filled()/total);
    yield return null;
   }
   if(hand)Destroy(hand);
   counter.text=$"Movimentos: {t.moves}  ·  ideal: {t.par}";KitchenMeter(1);
   foreach(var p in t.pieces){var h=p.rect.GetComponent<TrayHandle>();if(h)h.enabled=false;}
   kitchenScore=t.moves<=t.par?1f:Mathf.Max(.45f,1f-.08f*(t.moves-t.par));if(t.hint)kitchenScore=Mathf.Min(kitchenScore,.7f);
   // Into the oven: the doughs turn golden one after the other.
   Sound("success");
   foreach(var p in t.pieces.OrderBy(p=>p.row*100+p.col)){StartCoroutine(Bake(p));yield return new WaitForSecondsRealtime(.07f);}
   U.Sparkles(this,kitchenStage,center,14,Mathf.Max(tw,th)*.6f);
   yield return new WaitForSecondsRealtime(.9f);
   tray=null;
  }

  // Homes of the doughs in rows (largest first is not needed: the deal order is shuffled); null when they do not fit.
  static List<Vector2> FlowHomes(List<Vector2> sizes,float x0,float width,float top,float height){
   var homes=new List<Vector2>();float x=x0,y=top,rowH=0;const float gap=18;
   foreach(var s in sizes){
    if(s.x>width)return null;
    if(x+s.x>x0+width){x=x0;y-=rowH+gap;rowH=0;}
    homes.Add(new Vector2(x+s.x/2,y-s.y/2));x+=s.x+gap;rowH=Mathf.Max(rowH,s.y);
   }
   return top-y+rowH<=height?homes:null;
  }

  void DrawDough(TrayPiece p,float cell){
   var d=BreadPieces[p.id];var size=new Vector2(d.w*cell,d.h*cell);
   var rawArt=K.Icon("Game/pz_bread_"+p.id+"_raw");var bakedArt=K.Icon("Game/pz_bread_"+p.id+"_baked");
   var shadow=N.Image(p.body,"Shadow",new Color(.2f,.1f,.03f,.28f),0);shadow.sprite=U.Glow();Stretch(shadow.rectTransform,new Vector2(-10,-18),new Vector2(10,0));
   if(rawArt){
    p.art=N.Image(p.body,"Art",Color.white,0);p.art.sprite=rawArt;Stretch(p.art.rectTransform,Vector2.zero,Vector2.zero);
    if(bakedArt){p.artBaked=N.Image(p.body,"Baked",new Color(1,1,1,0),0);p.artBaked.sprite=bakedArt;Stretch(p.artBaked.rectTransform,Vector2.zero,Vector2.zero);}
    return;
   }
   // Drawn dough until the art exists: a soft rounded loaf with a crust layer that fades in when baked, and scores.
   float inset=Mathf.Max(6,cell*.07f);int radius=Mathf.RoundToInt(Mathf.Min(size.x,size.y)*.42f);
   var edge=N.Image(p.body,"Edge",K.C("C99A5B"),Mathf.Clamp(radius+2,8,62));Stretch(edge.rectTransform,new Vector2(inset-3,inset-4),new Vector2(-inset+3,-inset+2));
   p.dough=N.Image(p.body,"Dough",K.C(d.raw),Mathf.Clamp(radius,8,60));Stretch(p.dough.rectTransform,new Vector2(inset,inset),new Vector2(-inset,-inset));
   p.baked=N.Image(p.body,"Crust",new Color(1,1,1,0),Mathf.Clamp(radius,8,60));var bc=K.C(d.baked);p.baked.color=new Color(bc.r,bc.g,bc.b,0);Stretch(p.baked.rectTransform,new Vector2(inset,inset),new Vector2(-inset,-inset));
   var gloss=p.gloss=N.Image(p.body,"Gloss",new Color(1,1,1,.35f),Mathf.Clamp(radius,6,40));Stretch(gloss.rectTransform,new Vector2(inset*2.2f,size.y*.45f),new Vector2(-inset*2.2f,-inset*1.6f));
   bool tall=d.h>d.w;int scores=p.id=="frances"?1:p.id=="redondo"?2:Mathf.Max(d.w,d.h);
   for(int i=0;i<scores;i++){
    var line=N.Image(p.body,"Score",new Color(1,1,1,.55f),3);p.scores.Add(line);var r=line.rectTransform;
    float f=(i+.5f)/scores;r.anchorMin=r.anchorMax=new Vector2(tall?.5f:f,tall?f:.5f);r.pivot=new Vector2(.5f,.5f);
    r.sizeDelta=p.id=="redondo"?new Vector2(size.x*.55f,8):tall?new Vector2(size.x*.42f,7):new Vector2(7,size.y*.42f);
    r.localRotation=Quaternion.Euler(0,0,p.id=="redondo"?(i==0?45:-45):tall?20:-20);r.anchoredPosition=Vector2.zero;
   }
  }

  IEnumerator Bake(TrayPiece p){
   StartCoroutine(U.Pop(p.rect,1.08f,.22f));
   for(float k=0;k<1;k+=Time.unscaledDeltaTime/.45f){
    if(p.baked){var c=p.baked.color;c.a=k;p.baked.color=c;}
    // The crust takes the shine; the scores open up pale like the crumb.
    if(p.gloss)p.gloss.color=new Color(1,.95f,.8f,Mathf.Lerp(.35f,.18f,k));
    foreach(var sc in p.scores)if(sc)sc.color=Color.Lerp(new Color(1,1,1,.55f),K.C("F7E3B5"),k);
    if(p.artBaked)p.artBaked.color=new Color(1,1,1,k);
    yield return null;
   }
   if(p.baked){var c=p.baked.color;c.a=1;p.baked.color=c;}
   if(p.artBaked)p.artBaked.color=Color.white;
  }

  // ------------------------------------------------------------------ gestures
  Vector2 trayGrab;
  void TrayPick(TrayPiece p,Vector2 pos){
   var t=tray;if(t==null)return;kitchenPad.Interacted=true;
   if(p.Placed){t.Mark(p,false);p.col=p.row=-1;}
   p.rect.SetAsLastSibling();trayGrab=p.rect.anchoredPosition-pos;
   StartCoroutine(U.Scale(p.rect,Vector3.one*1.04f,.12f));Sound("pop",1.2f);
  }
  void TrayDrag(TrayPiece p,Vector2 pos){
   var t=tray;if(t==null)return;
   p.rect.anchoredPosition=pos+trayGrab*.6f;
   var (c,r)=TrayCell(p);bool over=OverTray(p);
   t.ghost.gameObject.SetActive(over);
   if(over){bool ok=t.Fits(c,r,p.W,p.H,p);t.ghost.anchoredPosition=t.CellCenter(c,r,p.W,p.H);t.ghost.sizeDelta=new Vector2(p.W*t.cell-6,p.H*t.cell-6);
    t.ghostImage.color=ok?new Color(.42f,.86f,.36f,.4f):new Color(.9f,.3f,.25f,.35f);t.ghost.SetSiblingIndex(Mathf.Max(0,p.rect.GetSiblingIndex()-1));}
  }
  void TrayDrop(TrayPiece p,Vector2 pos){
   var t=tray;if(t==null)return;t.ghost.gameObject.SetActive(false);
   var (c,r)=TrayCell(p);
   if(OverTray(p)&&t.Fits(c,r,p.W,p.H,null)){
    p.col=c;p.row=r;t.Mark(p,true);t.moves++;Sound("pop");
    StartCoroutine(U.Move(p.rect,t.CellCenter(c,r,p.W,p.H),.1f));StartCoroutine(U.Scale(p.rect,Vector3.one,.12f));
    StartCoroutine(U.Pop(p.body,1.06f,.18f));
   }
   else{if(OverTray(p))Sound("bonk");Home(p);}
  }
  void TrayTurn(TrayPiece p){
   var t=tray;if(t==null||p.w==p.h)return;kitchenPad.Interacted=true;
   if(p.Placed){
    t.Mark(p,false);p.turned=!p.turned;
    if(!t.Fits(p.col,p.row,p.W,p.H,null)){p.turned=!p.turned;t.Mark(p,true);Sound("bonk");StartCoroutine(U.Pop(p.body,1.05f,.15f));return;}
    t.Mark(p,true);t.moves++;p.rect.anchoredPosition=t.CellCenter(p.col,p.row,p.W,p.H);
   }
   else p.turned=!p.turned;
   p.rect.sizeDelta=new Vector2(p.W*t.cell,p.H*t.cell);
   p.body.localRotation=Quaternion.Euler(0,0,p.turned?90:0);
   Sound("whoosh",1.3f);StartCoroutine(U.Pop(p.body,1.06f,.15f));
  }
  void Home(TrayPiece p){StartCoroutine(U.Move(p.rect,p.home,.18f,true));StartCoroutine(U.Scale(p.rect,Vector3.one*p.homeScale,.15f));}
  // The cell under the piece's top-left corner (rounded to the nearest cell).
  (int,int) TrayCell(TrayPiece p){
   var t=tray;var tl=p.rect.anchoredPosition+new Vector2(-p.W*t.cell*.5f,p.H*t.cell*.5f)-t.origin;
   return (Mathf.RoundToInt(tl.x/t.cell),Mathf.RoundToInt(-tl.y/t.cell));
  }
  bool OverTray(TrayPiece p){
   var t=tray;var a=p.rect.anchoredPosition;
   return a.x>t.origin.x-t.cell*.5f&&a.x<t.origin.x+t.cols*t.cell+t.cell*.5f&&a.y<t.origin.y+t.cell*.5f&&a.y>t.origin.y-t.rows*t.cell-t.cell*.5f;
  }

  void TrayHint(){
   var t=tray;if(t==null)return;t.hint=true;kitchenPad.Interacted=true;Sound("pop",.9f);
   // A spot of the deal's own solution that is still free, and a loose dough of that size.
   foreach(var at in t.solution){
    bool free=true;for(int x=at.x;x<at.xMax&&free;x++)for(int y=at.y;y<at.yMax&&free;y++)if(t.owner[x,y]>=0)free=false;
    if(!free)continue;
    var p=t.pieces.FirstOrDefault(q=>!q.Placed&&((q.w==at.width&&q.h==at.height)||(q.h==at.width&&q.w==at.height)));
    if(p==null)continue;
    StartCoroutine(Flash(t.CellCenter(at.x,at.y,at.width,at.height),new Vector2(at.width,at.height)*t.cell,new Color(1f,.82f,.25f,.55f)));
    StartCoroutine(U.Pop(p.body,1.15f,.35f));
    Toast(p.turned==(p.w==at.width&&p.h==at.height)&&p.w!=p.h?"Gire esta massa e encaixe no lugar marcado.":"Esta massa vai no lugar marcado.",true);
    return;
   }
   // Nothing of the solution left free: a placed dough blocks it.
   var wrong=t.pieces.FirstOrDefault(q=>q.Placed&&!t.solution.Any(s=>s.x==q.col&&s.y==q.row&&s.width==q.W&&s.height==q.H));
   if(wrong!=null){StartCoroutine(Flash(wrong.rect.anchoredPosition,wrong.rect.sizeDelta,new Color(.95f,.3f,.25f,.5f)));Toast("Esta massa está atrapalhando: tire e tente outro lugar.",false);}
  }
  IEnumerator Flash(Vector2 at,Vector2 size,Color color){
   var f=KKeep(N.Image(kitchenStage,"Hint spot",color,12));Place(f.rectTransform,new Vector2(.5f,.5f),new Vector2(.5f,.5f),new Vector2(.5f,.5f),at,size);
   for(float k=0;k<2.4f&&f;k+=Time.unscaledDeltaTime){f.color=new Color(color.r,color.g,color.b,color.a*(.55f+.45f*Mathf.Sin(k*8)));yield return null;}
   if(f)Destroy(f.gameObject);
  }

  // QA (autotest "trayplay"): puts one dough where the deal's solution has it, as a drag would. False when done.
  public bool QaTrayPlace(){
   var t=tray;if(t==null)return false;
   foreach(var at in t.solution){
    bool free=true;for(int x=at.x;x<at.xMax&&free;x++)for(int y=at.y;y<at.yMax&&free;y++)if(t.owner[x,y]>=0)free=false;
    if(!free)continue;
    var p=t.pieces.FirstOrDefault(q=>!q.Placed&&((q.w==at.width&&q.h==at.height)||(q.h==at.width&&q.w==at.height)));
    if(p==null)continue;
    if(p.W!=at.width)TrayTurn(p);
    TrayPick(p,p.rect.anchoredPosition);p.rect.anchoredPosition=t.CellCenter(at.x,at.y,at.width,at.height);trayGrab=Vector2.zero;TrayDrop(p,p.rect.anchoredPosition);
    return true;
   }
   return false;
  }

  // Pointer on one dough: press/drag/release in stage coordinates, or a tap (no drag) to turn it.
  sealed class TrayHandle:MonoBehaviour,IBeginDragHandler,IDragHandler,IEndDragHandler,IPointerClickHandler {
   public RectTransform Space;public Action<Vector2> Began,Moved,Ended;public Action Tapped;bool dragging;
   Vector2 Local(PointerEventData e){RectTransformUtility.ScreenPointToLocalPointInRectangle(Space,e.position,e.pressEventCamera,out var p);return p-Space.rect.center;}
   public void OnBeginDrag(PointerEventData e){if(!enabled)return;dragging=true;Began?.Invoke(Local(e));}
   public void OnDrag(PointerEventData e){if(!enabled||!dragging)return;Moved?.Invoke(Local(e));}
   public void OnEndDrag(PointerEventData e){if(!enabled||!dragging)return;dragging=false;Ended?.Invoke(Local(e));}
   public void OnPointerClick(PointerEventData e){if(!enabled||dragging||e.dragging)return;Tapped?.Invoke();}
  }
 }
}
