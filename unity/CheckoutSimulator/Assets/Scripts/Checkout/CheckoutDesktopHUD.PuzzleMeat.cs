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
 // Açougue — "Corte na medida" (step kind "portions"): a cut of beef (Blender art: contra-filé, picanha or fraldinha)
 // that is thick in some places and thin in others lies on the block; the knife marks above it split it into portions and the scale under each one shows its weight.
 // Every portion must weigh the target (± tolerance): the thick end needs narrow cuts, the thin end wide ones. Drag the
 // knives until every scale is green. Moves = knife drags; the ideal is one drag per knife.
 public partial class CheckoutDesktopHUD {
  IEnumerator StepPortions(DesktopKitchenStep s){
   int portions=Mathf.Clamp(s.count,2,7);
   float target=s.scale!=null&&s.scale.Length>0?s.scale[0]:150,tolerance=s.scale!=null&&s.scale.Length>1?s.scale[1]:15;
   // The piece: one of the Blender cuts (CheckoutPuzzleArt.Meats: its thickness per slice was measured from the
   // picture, so the weights match what the player sees), or a random code-drawn profile without the art.
   var cuts0=CheckoutPuzzleArt.Meats.Where(m=>K.Icon("Game/pz_meat_"+m.id)!=null).ToArray();
   bool useArt=cuts0.Length>0;var meatArt=useArt?cuts0[Random.Range(0,cuts0.Length)]:default;
   int slices=useArt?meatArt.profile.Length:60;var thick=new float[slices];
   // Flipped half of the time, so the thick end is not always on the same side.
   bool flipped=useArt&&Random.value<.5f;
   if(useArt)for(int i=0;i<slices;i++)thick[i]=Mathf.Max(.02f,meatArt.profile[flipped?slices-1-i:i]);
   else{
    float a1=Random.Range(.25f,.6f),p1=Random.Range(0,6.28f),a2=Random.Range(.1f,.3f),tilt=Random.Range(-.45f,.45f);
    for(int i=0;i<slices;i++){float x=i/(slices-1f);thick[i]=Mathf.Max(.35f,1+a1*Mathf.Sin(x*3.4f+p1)+a2*Mathf.Sin(x*9+p1*2)+tilt*(x-.5f));}
   }
   float total=thick.Sum();var grams=thick.Select(t=>t/total*target*portions).ToArray();

   float W=StageW,H=StageH;float width=W-140,height=Mathf.Min(170,H*.36f);var center=new Vector2(0,10);
   float left=center.x-width/2;
   var columns=new List<Image>();var fats=new List<Image>();
   RawImage meatImage=null;float pxScale=0;
   if(useArt){
    // The cut lies on the end-grain block of the bench art; the picture spans exactly the measured x range.
    // As wide as the block allows, but never taller than the knives reach.
    var sprite=K.Icon("Game/pz_meat_"+meatArt.id);pxScale=Mathf.Min(width/(meatArt.x1-meatArt.x0),height*1.05f/(meatArt.profile.Max()*meatArt.size.y));
    width=(meatArt.x1-meatArt.x0)*pxScale;left=center.x-width/2;
    float floorY=center.y-height*.55f;var size=meatArt.size*pxScale;
    // With the picture flipped, its measured range sits at the other end of the texture.
    float x0=flipped?meatArt.size.x-meatArt.x1:meatArt.x0;
    var mid=new Vector2(left-x0*pxScale+size.x/2,floorY-meatArt.y0*pxScale+size.y/2);
    var holder=PNode(kitchenStage,"Meat",mid,size);meatImage=holder.gameObject.AddComponent<RawImage>();meatImage.texture=sprite.texture;meatImage.raycastTarget=false;
    if(flipped)meatImage.uvRect=new Rect(1,0,-1,1);
   }
   else{
    // The butcher's block and the meat: one column per slice, its height = the thickness.
    var block=PImage(kitchenStage,"Block",K.C("9C6B3E"),24,center,new Vector2(width+60,height*1.25f+40));
    PImage(block.transform,"Top",K.C("C99662"),20,Vector2.zero,new Vector2(width+40,height*1.25f+20));
    float sliceW=width/slices;
    for(int i=0;i<slices;i++){
     // The piece lies on the block: its height is how thick it is there (fat cap on top).
     float h=height*thick[i]/1.7f;var x=left+(i+.5f)*sliceW;float floorY=center.y-height*.55f;
     var meat=PImage(kitchenStage,"Meat",Color.Lerp(K.C("C8423C"),K.C("A8302E"),Noise(i,3)),4,new Vector2(x,floorY+h/2),new Vector2(sliceW+1,h));
     var fat=PImage(kitchenStage,"Fat",K.C("F3E3CF"),4,new Vector2(x,floorY+h-3),new Vector2(sliceW+1,10));
     if(Noise(i,7)>.6f){var marble=N.Image(meat.transform,"Marble",new Color(1,.9f,.85f,.5f),3);marble.rectTransform.sizeDelta=new Vector2(sliceW*.9f,4);marble.rectTransform.anchoredPosition=new Vector2(0,(Noise(i,9)-.5f)*h*.6f);}
     columns.Add(meat);fats.Add(fat);
    }
   }
   // Knives start evenly spaced (which is wrong: the meat is not even).
   var knives=new List<RectTransform>();var cuts=new List<float>();
   for(int k=1;k<portions;k++)cuts.Add(k/(float)portions);
   var scales=new List<(Image back,TextMeshProUGUI text)>();
   for(int k=0;k<portions;k++){
    var back=PImage(kitchenStage,"Scale",K.C("2E3A4A"),12,Vector2.zero,new Vector2(110,44));
    var t=PText(back.transform,"",20,Color.white,Vector2.zero,new Vector2(108,40),K.Number);
    scales.Add((back,t));
   }
   int moves=0;int par=portions-1;
   float knifeY=center.y+height*.62f+40;
   for(int k=0;k<cuts.Count;k++){
    int index=k;
    var knife=PNode(kitchenStage,"Knife",new Vector2(left+cuts[k]*width,center.y+10),new Vector2(60,height*1.25f+120));
    var line=N.Image(knife,"Line",new Color(1,1,1,.85f),2);var lr=line.rectTransform;lr.anchorMin=lr.anchorMax=lr.pivot=new Vector2(.5f,.5f);lr.sizeDelta=new Vector2(5,height*1.4f);lr.anchoredPosition=new Vector2(0,-30);
    var dash=N.Image(knife,"Edge",new Color(.2f,.12f,.08f,.6f),2);var dr=dash.rectTransform;dr.anchorMin=dr.anchorMax=dr.pivot=new Vector2(.5f,.5f);dr.sizeDelta=new Vector2(2,height*1.4f);dr.anchoredPosition=new Vector2(0,-30);
    var grip=N.Image(knife,"Handle",K.C("3B2A1E"),14);var gr=grip.rectTransform;gr.anchorMin=gr.anchorMax=gr.pivot=new Vector2(.5f,.5f);gr.sizeDelta=new Vector2(44,64);gr.anchoredPosition=new Vector2(0,height*.62f+28);
    var blade=N.Image(knife,"Blade",K.C("C9D2DA"),10);var bl=blade.rectTransform;bl.anchorMin=bl.anchorMax=bl.pivot=new Vector2(.5f,.5f);bl.sizeDelta=new Vector2(30,40);bl.anchoredPosition=new Vector2(0,height*.62f-14);
    PHandle(knife,p=>{kitchenPad.Interacted=true;Sound("pop",1.3f);},p=>{
      float lo=index>0?cuts[index-1]+.03f:.03f,hi=index<cuts.Count-1?cuts[index+1]-.03f:.97f;
      cuts[index]=Mathf.Clamp((p.x-left)/width,lo,hi);knife.anchoredPosition=new Vector2(left+cuts[index]*width,knife.anchoredPosition.y);},
     p=>{moves++;Sound("whoosh",1.4f);},null);
    knives.Add(knife);
   }
   var moveText=PMoves(new Vector2(-W/2+190,-H/2+24),340);
   var goal=PText(kitchenStage,"",19,K.Ink,new Vector2(W/2-210,-H/2+24),new Vector2(400,28));
   goal.text=$"Cada porção: {target:0} g (± {tolerance:0} g)";
   var hand=KHint(()=>knives.Count>0&&knives[0]?knives[0].anchoredPosition+new Vector2(0,height*.62f+20):Vector2.zero,()=>knives.Count>0&&knives[0]?knives[0].anchoredPosition+new Vector2(width*.12f,height*.62f+20):Vector2.zero);
   float Weight(float from,float to){float g=0;for(int i=0;i<slices;i++){float s0=i/(float)slices,s1=(i+1)/(float)slices;float o=Mathf.Max(0,Mathf.Min(to,s1)-Mathf.Max(from,s0));g+=grams[i]*o*slices;}return g;}
   bool done=false;
   while(!done){
    if(kitchenPad.Interacted&&hand)Destroy(hand);
    int good=0;
    for(int k=0;k<portions;k++){
     float from=k==0?0:cuts[k-1],to=k==portions-1?1:cuts[k];float g=Weight(from,to);
     bool ok=Mathf.Abs(g-target)<=tolerance;if(ok)good++;
     scales[k].back.color=ok?K.C("4F9A2E"):Mathf.Abs(g-target)<=tolerance*2.5f?K.C("E8962B"):K.C("2E3A4A");
     scales[k].text.text=$"{g:0} g";
     scales[k].back.rectTransform.anchoredPosition=new Vector2(left+(from+to)/2*width,center.y-height*.62f-44);
     scales[k].back.rectTransform.sizeDelta=new Vector2(Mathf.Clamp((to-from)*width-8,84,130),44);
    }
    PMovesText(moveText,moves,par);KitchenMeter(good/(float)portions);
    done=good==portions&&!Input.GetMouseButton(0)&&Input.touchCount==0;
    yield return null;
   }
   if(hand)Destroy(hand);
   kitchenScore=PuzzleScore(moves,par,false,.06f);
   // Chop: the knives drop and the portions slide apart.
   foreach(var k in knives){StartCoroutine(U.Move(k,k.anchoredPosition-new Vector2(0,60),.12f));}
   Sound("chop");yield return new WaitForSecondsRealtime(.2f);
   if(meatImage){
    // The picture is cut into one piece per portion (same texture, each showing its own stretch) and they slide apart.
    var holder=meatImage.rectTransform;float span=meatArt.x1-meatArt.x0;float x0=flipped?meatArt.size.x-meatArt.x1:meatArt.x0;
    for(int part=0;part<portions;part++){
     float from=part==0?0:cuts[part-1],to=part==portions-1?1:cuts[part];
     // Screen pixels of the (possibly flipped) picture: the first and last portions keep the picture's margins.
     float px0=part==0?0:x0+from*span,px1=part==portions-1?meatArt.size.x:x0+to*span;
     var piece=PNode(kitchenStage,"Portion",holder.anchoredPosition+new Vector2(((px0+px1)/2-meatArt.size.x/2)*pxScale,0),new Vector2((px1-px0)*pxScale,holder.sizeDelta.y));
     var img=piece.gameObject.AddComponent<RawImage>();img.texture=meatImage.texture;img.raycastTarget=false;
     float u0=px0/meatArt.size.x,u1=px1/meatArt.size.x;img.uvRect=flipped?new Rect(1-u0,0,-(u1-u0),1):new Rect(u0,0,u1-u0,1);
     StartCoroutine(U.Move(piece,piece.anchoredPosition+new Vector2((part-(portions-1)/2f)*16,0),.2f));
    }
    meatImage.enabled=false;
   }
   else for(int i=0;i<slices;i++){float x=(i+.5f)/slices;int part=0;while(part<cuts.Count&&x>cuts[part])part++;var shift=new Vector2((part-(portions-1)/2f)*14,0);foreach(var img in new[]{columns[i],fats[i]}){var r=img.rectTransform;StartCoroutine(U.Move(r,r.anchoredPosition+shift,.2f));}}
   yield return PSolved(center,width*.4f);
  }
 }
}
