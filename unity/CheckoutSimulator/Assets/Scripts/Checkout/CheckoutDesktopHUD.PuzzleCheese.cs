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
 // Queijaria — "Câmara de maturação" (step kind "aging"): the aging rack is an n×n grid and every shelf (row) and every
 // column must hold one wheel of each cheese, so they ripen evenly (a small Latin-square / sudoku). Some wheels are
 // already there; drag cheeses from the crates on the right onto the free spots, drag one off to take it back. Two of a
 // kind on the same shelf or column glow red. Full rack with no clash = done.
 public partial class CheckoutDesktopHUD {
  static readonly Dictionary<string,(string body,string rind,string spot)> CheeseLook=new Dictionary<string,(string,string,string)>{
   {"minas",("FBF7EC","E9DDC2","")},{"prato",("F4C34A","E3A72B","")},{"brie",("FFF9EF","D9D3C6","EFE6D3")},{"azul",("E7EEF1","C9D3D8","4F79A6")},{"parmesao",("F1D58A","C99A3D","")},
  };

  sealed class AgingState {public int n;public int[,] cell;public bool[,] given;public int[,] answer;public Image[,] slot;public RectTransform[,] wheel;public int moves,par;public string[] kinds;public bool hint;}
  AgingState aging;

  IEnumerator StepAging(DesktopKitchenStep s){
   var kinds=(s.pieces??new string[0]).Where(CheeseLook.ContainsKey).ToArray();if(kinds.Length<3)kinds=new[]{"minas","prato","brie"};
   int n=kinds.Length;var a=aging=new AgingState{n=n,kinds=kinds};
   a.answer=LatinSquare(n);
   a.given=GivenCells(a.answer,Mathf.Clamp(s.singles,1,n*n-1));
   a.cell=new int[n,n];for(int r=0;r<n;r++)for(int c=0;c<n;c++)a.cell[r,c]=a.given[r,c]?a.answer[r,c]:-1;
   a.par=0;for(int r=0;r<n;r++)for(int c=0;c<n;c++)if(!a.given[r,c])a.par++;
   a.slot=new Image[n,n];a.wheel=new RectTransform[n,n];

   // The rack (left): dark wood frame, a shelf board under each row.
   float W=StageW,H=StageH;float cell=Mathf.Floor(Mathf.Min((W*.56f-80)/n,(H-60)/n));
   var center=new Vector2(-W/2+30+W*.28f,0);float side=cell*n;
   var frame=PImage(kitchenStage,"Rack",K.C("6B4524"),20,center,new Vector2(side+40,side+40));
   PImage(frame.transform,"Back",K.C("3E2A1A"),14,Vector2.zero,new Vector2(side+14,side+14));
   for(int r=0;r<n;r++){
    var plank=PImage(frame.transform,"Shelf",K.C("A8743F"),6,new Vector2(0,side/2-(r+1)*cell+6),new Vector2(side+10,12));
    for(int c=0;c<n;c++){
     var at=new Vector2(-side/2+(c+.5f)*cell,side/2-(r+.5f)*cell+4);
     a.slot[r,c]=PImage(frame.transform,"Spot",new Color(1,1,1,.07f),40,at,new Vector2(cell-14,cell-14));
    }
   }
   for(int r=0;r<n;r++)for(int c=0;c<n;c++)if(a.cell[r,c]>=0)PutWheel(r,c,a.cell[r,c],cell,frame,true);

   // The crates (right): one per cheese, endless supply.
   float x0=center.x+side/2+60,width=W/2-20-x0;
   var board=PBoard("Cheese crates",new Vector2(x0+width/2,20),new Vector2(width+20,H-80));
   float crate=Mathf.Min(cell*1.05f,(width-20)/Mathf.Min(n,2)-20);
   for(int k=0;k<n;k++){
    int kind=k;int col=k%2,row=k/2;int rows=(n+1)/2;
    var at=new Vector2(x0+width*(col==0?.27f:.73f),20+((rows-1)/2f-row)*(crate+16));
    var box=PImage(kitchenStage,"Crate",K.C("C8955A"),14,at,new Vector2(crate,crate));
    PImage(box.transform,"Inner",K.C("E8C891"),12,Vector2.zero,new Vector2(crate-14,crate-14));
    DrawCheese(box.transform,kinds[k],crate*.72f,k);
    RectTransform drag=null;
    PHandle(box.rectTransform,p=>{drag=NewCheese(kind,cell,p);},p=>{if(drag)drag.anchoredPosition=p;},p=>{if(drag){DropCheese(drag,kind,cell,frame);drag=null;}},()=>Toast("Arraste o queijo até um lugar vazio da câmara.",true));
   }
   var moves=PMoves(new Vector2(x0+width*.3f,-H/2+30),width*.6f);
   PButton("Dica","secondary",new Vector2(W/2-20-80,-H/2+30),new Vector2(150,48),()=>AgingHint(cell,frame));
   while(!AgingDone()){PMovesText(moves,a.moves,a.par);KitchenMeter(AgingFilled()/(float)(n*n));yield return null;}
   PMovesText(moves,a.moves,a.par);KitchenMeter(1);
   kitchenScore=PuzzleScore(a.moves,a.par,a.hint);
   for(int r=0;r<n;r++)for(int c=0;c<n;c++)if(a.wheel[r,c]){StartCoroutine(U.Pop(a.wheel[r,c],1.12f,.3f));yield return new WaitForSecondsRealtime(.04f);}
   yield return PSolved(center,side*.6f);
   aging=null;
  }

  // Cheese drawn in code until the Blender art (Game/pz_cheese_<kind>) exists: wheel with rind, holes or blue veins.
  void DrawCheese(Transform parent,string kind,float size,int seed){
   var art=K.Icon("Game/pz_cheese_"+kind);
   PShadow(parent,new Vector2(size,size*.9f));
   if(art){var i=N.Image(parent,"Art",Color.white,0);i.sprite=art;i.preserveAspect=true;var r=i.rectTransform;r.anchorMin=r.anchorMax=r.pivot=new Vector2(.5f,.5f);r.sizeDelta=new Vector2(size,size);return;}
   var look=CheeseLook[kind];
   N.Image(parent,"Rind",K.C(look.rind),(int)(size/2)).rectTransform.sizeDelta=new Vector2(size,size);
   var body=N.Image(parent,"Body",K.C(look.body),(int)(size/2));body.rectTransform.sizeDelta=new Vector2(size*.84f,size*.84f);
   if(kind=="prato"||kind=="parmesao"||kind=="minas")
    for(int h=0;h<5;h++){var hole=N.Image(parent,"Hole",new Color(0,0,0,kind=="minas"?.06f:.12f),8);float d=size*(.08f+Noise(seed,h)*.06f);hole.rectTransform.sizeDelta=new Vector2(d,d);hole.rectTransform.anchoredPosition=new Vector2((Noise(h,seed+3)-.5f)*size*.5f,(Noise(h+9,seed)-.5f)*size*.5f);}
   if(!string.IsNullOrEmpty(look.spot))
    for(int h=0;h<7;h++){var v=N.Image(parent,"Vein",K.C(look.spot),6);v.color=new Color(v.color.r,v.color.g,v.color.b,kind=="brie"?.9f:.8f);float d=size*(kind=="brie"?.18f:.07f);v.rectTransform.sizeDelta=new Vector2(d,d*(kind=="brie"?.6f:1));v.rectTransform.anchoredPosition=new Vector2((Noise(h,seed+11)-.5f)*size*.55f,(Noise(h+4,seed+2)-.5f)*size*.55f);}
   var gloss=N.Image(parent,"Gloss",new Color(1,1,1,.35f),20);gloss.rectTransform.sizeDelta=new Vector2(size*.45f,size*.16f);gloss.rectTransform.anchoredPosition=new Vector2(-size*.12f,size*.24f);
  }
  RectTransform NewCheese(int kind,float cell,Vector2 at){
   var r=PNode(kitchenStage,"Cheese",at,new Vector2(cell,cell));DrawCheese(r,aging.kinds[kind],cell*.78f,kind);r.SetAsLastSibling();Sound("pop",1.2f);kitchenPad.Interacted=true;return r;
  }
  void PutWheel(int row,int col,int kind,float cell,Image frame,bool given){
   var a=aging;var spot=a.slot[row,col].rectTransform;
   var r=PNode(frame.transform,given?"Given":"Wheel",spot.anchoredPosition,new Vector2(cell,cell));DrawCheese(r,a.kinds[kind],cell*.78f,row*7+col);
   if(given){var pin=N.Image(r,"Pin",K.C("8A5A2B"),6);pin.rectTransform.sizeDelta=new Vector2(14,14);pin.rectTransform.anchoredPosition=new Vector2(cell*.3f,-cell*.3f);}
   a.wheel[row,col]=r;a.cell[row,col]=kind;
   if(!given){
    // Dragging a placed wheel lifts a copy; the wheel itself only fades (destroying it would end the drag).
    int rr=row,cc=col,mine=kind;RectTransform drag=null;var fade=r.gameObject.AddComponent<CanvasGroup>();
    PHandle(r,p=>{if(a.wheel[rr,cc]!=r)return;drag=NewCheese(mine,cell,p);fade.alpha=0;a.cell[rr,cc]=-1;a.wheel[rr,cc]=null;AgingConflicts();},
     p=>{if(drag)drag.anchoredPosition=p;},
     p=>{if(drag){DropCheese(drag,mine,cell,frame);drag=null;Destroy(r.gameObject);}},null);
   }
   AgingConflicts();
  }
  void ClearWheel(int row,int col){var a=aging;if(a.wheel[row,col])Destroy(a.wheel[row,col].gameObject);a.wheel[row,col]=null;a.cell[row,col]=-1;AgingConflicts();}
  void DropCheese(RectTransform drag,int kind,float cell,Image frame){
   var a=aging;if(a==null){Destroy(drag.gameObject);return;}
   // The spot under the finger.
   int best=-1,br=0,bc=0;float bestD=cell*.6f;
   var local=(Vector2)frame.rectTransform.InverseTransformPoint(drag.position);
   for(int r=0;r<a.n;r++)for(int c=0;c<a.n;c++){float d=Vector2.Distance(local,a.slot[r,c].rectTransform.anchoredPosition);if(d<bestD){bestD=d;best=1;br=r;bc=c;}}
   Destroy(drag.gameObject);
   if(best<0)return;
   if(a.given[br,bc]){Sound("bonk");StartCoroutine(U.Pop(a.wheel[br,bc],1.1f,.2f));return;}
   if(a.wheel[br,bc])ClearWheel(br,bc);
   a.moves++;Sound("pop");PutWheel(br,bc,kind,cell,frame,false);StartCoroutine(U.Pop(a.wheel[br,bc],1.12f,.2f));
  }
  // Red glow under every wheel that shares its shelf or column with one of the same kind.
  void AgingConflicts(){
   var a=aging;if(a==null)return;
   for(int r=0;r<a.n;r++)for(int c=0;c<a.n;c++){
    bool clash=false;int k=a.cell[r,c];
    if(k>=0)for(int i=0;i<a.n&&!clash;i++)if((i!=c&&a.cell[r,i]==k)||(i!=r&&a.cell[i,c]==k))clash=true;
    a.slot[r,c].color=clash?new Color(.95f,.25f,.2f,.55f):new Color(1,1,1,.07f);
   }
  }
  int AgingFilled(){var a=aging;int f=0;for(int r=0;r<a.n;r++)for(int c=0;c<a.n;c++)if(a.cell[r,c]>=0)f++;return f;}
  bool AgingDone(){
   var a=aging;if(AgingFilled()<a.n*a.n)return false;
   for(int r=0;r<a.n;r++)for(int c=0;c<a.n;c++)for(int i=0;i<a.n;i++)if((i!=c&&a.cell[r,i]==a.cell[r,c])||(i!=r&&a.cell[i,c]==a.cell[r,c]))return false;
   return true;
  }
  void AgingHint(float cell,Image frame){
   var a=aging;if(a==null)return;a.hint=true;
   // A wrong wheel first, else an empty spot with the cheese it takes.
   for(int r=0;r<a.n;r++)for(int c=0;c<a.n;c++)if(!a.given[r,c]&&a.cell[r,c]>=0&&a.cell[r,c]!=a.answer[r,c]){StartCoroutine(PFlash(a.slot[r,c],new Color(.95f,.25f,.2f,.8f),1.2f));Toast("Este queijo não fica aqui: tire e pense na fileira e na coluna.",false);return;}
   for(int r=0;r<a.n;r++)for(int c=0;c<a.n;c++)if(a.cell[r,c]<0){PutWheel(r,c,a.answer[r,c],cell,frame,false);a.moves++;StartCoroutine(U.Pop(a.wheel[r,c],1.2f,.3f));Toast("Um queijo no lugar certo!",true);return;}
  }

  // A random Latin square: the cyclic one with rows, columns and symbols shuffled.
  static int[,] LatinSquare(int n){
   var rows=Enumerable.Range(0,n).OrderBy(_=>Random.value).ToArray();var cols=Enumerable.Range(0,n).OrderBy(_=>Random.value).ToArray();var sym=Enumerable.Range(0,n).OrderBy(_=>Random.value).ToArray();
   var g=new int[n,n];for(int r=0;r<n;r++)for(int c=0;c<n;c++)g[r,c]=sym[(rows[r]+cols[c])%n];return g;
  }
  // Keeps `givens` cells shown so that the square still has a single solution (removes cells while it stays unique).
  static bool[,] GivenCells(int[,] answer,int givens){
   int n=answer.GetLength(0);var shown=new bool[n,n];for(int r=0;r<n;r++)for(int c=0;c<n;c++)shown[r,c]=true;int count=n*n;
   foreach(var i in Enumerable.Range(0,n*n).OrderBy(_=>Random.value)){
    if(count<=givens)break;int r=i/n,c=i%n;shown[r,c]=false;
    if(CountLatin(answer,shown,n,2)!=1)shown[r,c]=true;else count--;
   }
   return shown;
  }
  static int CountLatin(int[,] answer,bool[,] shown,int n,int limit){
   var g=new int[n,n];for(int r=0;r<n;r++)for(int c=0;c<n;c++)g[r,c]=shown[r,c]?answer[r,c]:-1;
   int found=0;
   void Solve(int i){
    if(found>=limit)return;if(i==n*n){found++;return;}
    int r=i/n,c=i%n;if(g[r,c]>=0){Solve(i+1);return;}
    for(int k=0;k<n;k++){bool ok=true;for(int j=0;j<n&&ok;j++)if(g[r,j]==k||g[j,c]==k)ok=false;if(!ok)continue;g[r,c]=k;Solve(i+1);g[r,c]=-1;}
   }
   Solve(0);return found;
  }
 }
}
