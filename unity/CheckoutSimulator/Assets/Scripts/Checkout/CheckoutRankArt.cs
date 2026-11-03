using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 /// <summary>
 /// Rankings v1 (03/11 redesign): the shapes the ranking screens draw themselves, white with soft edges so an Image's
 /// colour paints them: a star (the Nota column), ▲/▼ triangles (rank changes), a pennant (the bunting over the
 /// podium), a spotlight cone, a chevron (the division arrow), a stamp frame, a marble-veined plinth face, a soft dotted
 /// backdrop texture and the parts of a treasure chest (body and lid; a PLACEHOLDER until the painted chest exists).
 /// Never text: every word on these screens is a UI label. <c>K.Icon("shape:star")</c> hands these out by name.
 /// </summary>
 public static class CheckoutRankArt {
  static readonly Dictionary<string,Sprite> cache=new Dictionary<string,Sprite>();

  /// <summary>A shape by name ("star", "up", "pennant", "spot", "chevron", "stamp", "plinth", "dots", "chest", "lid", "vs").</summary>
  public static Sprite Shape(string name){
   switch(name){
    case "star":return Star();
    case "up":return Triangle();
    case "pennant":return Pennant();
    case "spot":return Spotlight();
    case "chevron":return Chevron();
    case "stamp":return Stamp();
    case "plinth":return Plinth();
    case "dots":return Dots();
    case "chest":return ChestBody();
    case "lid":return ChestLid();
    case "vs":return Burst();
    default:return null;
   }
  }

  delegate float Coverage(float x,float y);
  /// <summary>A white sprite whose alpha is <paramref name="cover"/> (0–1) over [0,1]² with 3×3 supersampling.</summary>
  static Sprite Make(string key,int w,int h,Coverage cover,System.Func<float,float,float> shade=null,Vector4 border=default,Color? tint=null){
   if(cache.TryGetValue(key,out var cached)&&cached)return cached;
   var t=new Texture2D(w,h,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
   var px=new Color32[w*h];
   for(int y=0;y<h;y++)for(int x=0;x<w;x++){
    float a=0;
    for(int sy=0;sy<3;sy++)for(int sx=0;sx<3;sx++)a+=Mathf.Clamp01(cover((x+(sx+.5f)/3f)/w,(y+(sy+.5f)/3f)/h));
    a/=9f;
    float v=shade==null?1:Mathf.Clamp01(shade((x+.5f)/w,(y+.5f)/h));
    var col=tint??Color.white;
    px[y*w+x]=new Color32((byte)(col.r*v*255),(byte)(col.g*v*255),(byte)(col.b*v*255),(byte)(a*255));
   }
   t.SetPixels32(px);t.Apply();
   var s=border==default?Sprite.Create(t,new Rect(0,0,w,h),new Vector2(.5f,.5f)):Sprite.Create(t,new Rect(0,0,w,h),new Vector2(.5f,.5f),100,0,SpriteMeshType.FullRect,border);
   cache[key]=s;return s;
  }

  static bool InPolygon(Vector2 p,Vector2[] poly){
   bool inside=false;
   for(int i=0,j=poly.Length-1;i<poly.Length;j=i++){
    if(((poly[i].y>p.y)!=(poly[j].y>p.y))&&(p.x<(poly[j].x-poly[i].x)*(p.y-poly[i].y)/(poly[j].y-poly[i].y)+poly[i].x))inside=!inside;
   }
   return inside;
  }

  /// <summary>A five-point star, a touch lighter in the middle (the Nota column).</summary>
  public static Sprite Star(){
   // (painted gold, a darker rim: it reads on cream and on navy alike)
   var outer=new Vector2[10];var inner=new Vector2[10];
   for(int i=0;i<10;i++){float a=Mathf.PI/2+i*Mathf.PI/5;float r=i%2==0?.48f:.2f;float r2=i%2==0?.4f:.165f;outer[i]=new Vector2(.5f+Mathf.Cos(a)*r,.47f+Mathf.Sin(a)*r);inner[i]=new Vector2(.5f+Mathf.Cos(a)*r2,.47f+Mathf.Sin(a)*r2);}
   return Make("star",96,96,(x,y)=>InPolygon(new Vector2(x,y),outer)?1:0,(x,y)=>InPolygon(new Vector2(x,y),inner)?1-.16f*Vector2.Distance(new Vector2(x,y),new Vector2(.5f,.62f)):.68f,default,new Color(.98f,.74f,.22f));
  }
  /// <summary>An upward triangle with rounded feel (▲; rotated 180° for ▼).</summary>
  public static Sprite Triangle(){
   var pts=new[]{new Vector2(.5f,.92f),new Vector2(.94f,.14f),new Vector2(.06f,.14f)};
   return Make("up",48,48,(x,y)=>InPolygon(new Vector2(x,y),pts)?1:0);
  }
  /// <summary>A bunting pennant: a triangle hanging from its top edge, a darker band along the top.</summary>
  public static Sprite Pennant(){
   var pts=new[]{new Vector2(.02f,1),new Vector2(.98f,1),new Vector2(.5f,.04f)};
   return Make("pennant",64,80,(x,y)=>InPolygon(new Vector2(x,y),pts)?1:0,(x,y)=>y>.86f?.82f:1-.12f*Mathf.Abs(x-.5f));
  }
  /// <summary>A light cone from the top: narrow there, wide and faded at the bottom.</summary>
  public static Sprite Spotlight(){
   return Make("spot",128,256,(x,y)=>{
    float half=.08f+.42f*(1-y);float edge=Mathf.Clamp01((half-Mathf.Abs(x-.5f))/.08f);
    return edge*Mathf.Pow(y,.6f)*Mathf.Clamp01((1-y)*6);
   });
  }
  /// <summary>A thick chevron pointing right (the division arrow, three of them in a row).</summary>
  public static Sprite Chevron(){
   var pts=new[]{new Vector2(.08f,.92f),new Vector2(.42f,.92f),new Vector2(.92f,.5f),new Vector2(.42f,.08f),new Vector2(.08f,.08f),new Vector2(.56f,.5f)};
   return Make("chevron",64,64,(x,y)=>InPolygon(new Vector2(x,y),pts)?1:0);
  }
  /// <summary>A stamp's frame: a rounded ring with a thin inner line (9-sliced).</summary>
  public static Sprite Stamp(){
   const int n=96;const float r=.22f;
   return Make("stamp",n,n,(x,y)=>{
    float cx=Mathf.Clamp(x,r,1-r),cy=Mathf.Clamp(y,r,1-r);float d=Vector2.Distance(new Vector2(x,y),new Vector2(cx,cy))/r; // 0 inside … 1 at the edge
    float outer=d<1?1:0;
    float inset=Mathf.Min(Mathf.Min(x,1-x),Mathf.Min(y,1-y));
    float ring=inset<.09f?1:0;float line=inset>.13f&&inset<.16f?1:0;
    return outer*Mathf.Max(ring,line);
   },null,new Vector4(30,30,30,30));
  }
  /// <summary>A plinth face: light at the top, a little darker at the base, faint marble veins (tinted per place).</summary>
  public static Sprite Plinth(){
   // a soft marble: light at the top, a gentle diagonal sheen, two faint wandering veins
   return Make("plinth2",128,128,(x,y)=>1,(x,y)=>{
    float v=.84f+.16f*y;
    v+=.035f*Mathf.Sin((x*1.4f+y*.9f)*Mathf.PI);
    float vein1=Mathf.Abs(y-(.35f+.18f*Mathf.Sin(x*3.1f+.6f)));float vein2=Mathf.Abs(y-(.72f+.12f*Mathf.Sin(x*2.3f+2.1f)));
    v-=.05f*Mathf.Clamp01(1-vein1/.018f)+.04f*Mathf.Clamp01(1-vein2/.014f);
    return v;
   },new Vector4(10,10,10,10));
  }

  /// <summary>Faint dots for the podium's backdrop (tiled; alpha is low on purpose).</summary>
  public static Sprite Dots(){
   return Make("dots",64,64,(x,y)=>{
    float a=Vector2.Distance(new Vector2(x,y),new Vector2(.25f,.25f))<.06f?1:0;
    float b=Vector2.Distance(new Vector2(x,y),new Vector2(.75f,.7f))<.045f?1:0;
    return Mathf.Max(a,b);
   });
  }
  /// <summary>PLACEHOLDER chest body: a wooden box with planks and two metal bands (tinted wood; bands drawn lighter).</summary>
  public static Sprite ChestBody(){
   return Make("chest",160,112,(x,y)=>{
    float r=.08f;float cx=Mathf.Clamp(x,r,1-r),cy=Mathf.Clamp(y,r*1.4f,1-r*1.4f);
    return Vector2.Distance(new Vector2(x,y*1.43f/1.43f),new Vector2(cx,cy))<r?1:0;
   },(x,y)=>{
    bool band=(x>.18f&&x<.26f)||(x>.74f&&x<.82f);
    bool plate=x>.43f&&x<.57f&&y>.5f&&y<.86f;
    float plank=Mathf.Abs(Mathf.Sin(y*Mathf.PI*3))<.08f?.78f:1;
    return band||plate?1:.72f*plank*(.9f+.1f*y);
   });
  }
  /// <summary>PLACEHOLDER chest lid: the rounded top of the chest (same palette as the body).</summary>
  public static Sprite ChestLid(){
   return Make("lid",160,72,(x,y)=>{
    float dx=(x-.5f)/.5f,dy=y/1f;
    float dome=1-dx*dx*.35f;return y<dome&&x>.01f&&x<.99f?1:0;
   },(x,y)=>{
    bool band=(x>.18f&&x<.26f)||(x>.74f&&x<.82f);
    return band?1:.66f*(.85f+.15f*y);
   });
  }
  /// <summary>The VS emblem's burst: a 12-point star behind the letters.</summary>
  public static Sprite Burst(){
   var pts=new Vector2[24];
   for(int i=0;i<24;i++){float r=i%2==0?.5f:.38f;float a=i*Mathf.PI/12;pts[i]=new Vector2(.5f+Mathf.Cos(a)*r,.5f+Mathf.Sin(a)*r);}
   return Make("vs",128,128,(x,y)=>InPolygon(new Vector2(x,y),pts)?1:0,(x,y)=>1-.25f*Vector2.Distance(new Vector2(x,y),new Vector2(.5f,.62f)));
  }
 }
}
