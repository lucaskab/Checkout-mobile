using System;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Procedural sprites of the Delivery app: chunky game panels, avatar discs with a dark outline, the rating star,
 // the countdown ring, the map pin and the route dash. Everything is baked once from a per-sample colour function
 // (supersampled, antialiased) and cached by key. Icons (medal, flame, trucks, coins) come from Resources instead.
 public static class DeliveryArt {
  const int Size=128,Samples=4;
  static readonly Dictionary<string,Sprite> cache=new Dictionary<string,Sprite>();
  static Vector2[] starPoly;
  public const string Outline="2A1B10";

  // ------------------------------------------------------------------ simple shapes (white, tinted by Image.color)
  public static Sprite Star{get{
   if(starPoly==null){
    starPoly=new Vector2[10];
    for(int i=0;i<10;i++){
     float angle=Mathf.PI*.5f+i*Mathf.PI/5f;float r=i%2==0?.5f:.21f;
     starPoly[i]=new Vector2(.5f+r*Mathf.Cos(angle),.52f+r*Mathf.Sin(angle));
    }
   }
   var poly=starPoly;
   return Bake("star",p=>InPoly(p,poly));
  }}
  public static Sprite Ring{get{return Bake("ring",p=>{float d=Vector2.Distance(p,new Vector2(.5f,.5f));return d<=.5f&&d>=.39f;});}}
  public static Sprite Circle{get{return Bake("circle",p=>Vector2.Distance(p,new Vector2(.5f,.5f))<=.5f);}}
  // Map marker: a round head over a pointed tail (tail at the bottom).
  public static Sprite Pin{get{return Bake("pin",p=>Vector2.Distance(p,new Vector2(.5f,.64f))<=.3f||InTri(p,new Vector2(.5f,.04f),new Vector2(.22f,.6f),new Vector2(.78f,.6f)));}}
  // Rendered art (Blender, Resources/CheckoutDesktop/Delivery and Icons): glossy star (lit / unlit), the two map pins
  // and the delivery moto. Each falls back to the flat procedural shape if its texture is missing. Use them untinted.
  public static Sprite StarOn=>CheckoutDesktopKit.Icon("Delivery/star_on")??Star;
  public static Sprite StarOff=>CheckoutDesktopKit.Icon("Delivery/star_off")??Star;
  public static Sprite PinCustomer=>CheckoutDesktopKit.Icon("Delivery/map_pin_red")??Pin;
  public static Sprite PinStore=>CheckoutDesktopKit.Icon("Delivery/map_pin_teal")??Pin;
  public static Sprite Moto=>CheckoutDesktopKit.Icon("Icons/delivery-moto")??CheckoutDesktopKit.Icon("Icons/delivery-truck");
  public static void SetStar(UnityEngine.UI.Image img,bool on){if(!img)return;img.sprite=on?StarOn:StarOff;img.color=Color.white;}
  // Rounded dash for dotted routes (a short horizontal capsule).
  public static Sprite Dash{get{return Bake("dash",p=>DistSeg(p,new Vector2(.2f,.5f),new Vector2(.8f,.5f))<=.3f);}}

  // ------------------------------------------------------------------ chunky game panel
  // A rounded panel with a dark outline (3 texels), a light top highlight and a darker bottom shadow, baked in the fill
  // colour. Sliced with border R+4, so it stretches to any size with crisp corners and edges.
  public static Sprite Chunk(string fillHex,int radius=20){
   string key="chunk-"+fillHex+"-"+radius;
   if(cache.TryGetValue(key,out var got))return got;
   Color fill=K_C(fillHex),outline=K_C(Outline),white=Color.white,dark=new Color(.1f,.06f,.03f);
   float W=2*radius+16f,T=3f;
   // Pixel p runs top-down (p.y = 0 at the top of the panel).
   return PaintSliced(key,(int)W,(int)W,radius+4,p=>{
    float x=p.x*W,y=p.y*W;
    float cx=Mathf.Clamp(x,radius,W-radius),cy=Mathf.Clamp(y,radius,W-radius);
    float edge=radius-Vector2.Distance(new Vector2(x,y),new Vector2(cx,cy));
    if(edge<0)return Color.clear;
    if(edge<T)return outline;
    Color c=fill;
    if(y<T+5f)c=Color.Lerp(c,white,.42f*(1f-(y-T)/5f));
    if(y>W-T-6f)c=Color.Lerp(c,dark,.26f*Mathf.Clamp01((y-(W-T-6f))/6f));
    return c;
   });
  }
  // ------------------------------------------------------------------ flat app card (the delivery app's look)
  // A modern app surface: rounded, no outline, a hairline border a shade darker than the fill and a soft shadow under
  // it (a few texels below the body). Sliced like Chunk, so it stretches to any size.
  public static Sprite Flat(string fillHex,int radius=18){
   string key="flat-"+fillHex+"-"+radius;
   if(cache.TryGetValue(key,out var got))return got;
   Color fill=K_C(fillHex),line=Color.Lerp(fill,Color.black,.07f);
   float S=4f,W=2*radius+16f+S;
   return PaintSliced(key,(int)W,(int)W,radius+6,p=>{
    float x=p.x*W,y=p.y*W;
    // body: the square minus the shadow band at the bottom
    float cx=Mathf.Clamp(x,radius+1,W-radius-1),cy=Mathf.Clamp(y,radius+1,W-S-radius-1);
    float edge=radius-Vector2.Distance(new Vector2(x,y),new Vector2(cx,cy));
    if(edge>=0){var c=edge<1.2f?line:fill;c.a=Mathf.Clamp01(edge+.5f)*fill.a;return c;}
    // soft shadow: the same shape S texels lower, fading out over 4 texels
    float sy=Mathf.Clamp(y,radius+1+S,W-radius-1);float se=radius-Vector2.Distance(new Vector2(x,y),new Vector2(cx,sy));
    if(se>-4f){float a=.16f*Mathf.Clamp01((se+4f)/4f);return new Color(0,0,0,a);}
    return Color.clear;
   });
  }
  // An app avatar: the seeded colour in a clean circle with a thin white ring (no cartoon outline).
  public static Sprite FlatDisc(string fillHex){
   string key="fdisc-"+fillHex;
   if(cache.TryGetValue(key,out var got))return got;
   Color fill=K_C(fillHex);
   return Paint(key,96,96,p=>{
    float d=Vector2.Distance(p,new Vector2(.5f,.5f));
    if(d>.5f)return Color.clear;
    if(d>.465f)return new Color(1,1,1,Mathf.Clamp01((.5f-d)*60f));
    return fill;
   });
  }
  static Color K_C(string hex){ColorUtility.TryParseHtmlString("#"+hex,out var c);return c;}

  // A round avatar disc: a dark outline, the seeded colour, a soft top highlight. Initials are drawn over it by the app.
  public static Sprite Disc(string fillHex){
   string key="disc-"+fillHex;
   if(cache.TryGetValue(key,out var got))return got;
   Color fill=K_C(fillHex),outline=K_C(Outline),white=Color.white;
   return Paint(key,96,96,p=>{
    float d=Vector2.Distance(p,new Vector2(.5f,.5f));
    if(d>.5f)return Color.clear;
    if(d>.46f)return outline;
    Color c=fill;
    if(p.y<.3f)c=Color.Lerp(c,white,.28f*(1f-p.y/.3f));
    return c;
   });
  }

  // Starburst sticker (for "NOVO!" stamps), in the given colour.
  public static Sprite Burst(string hex){
   string key="burst-"+hex;
   if(cache.TryGetValue(key,out var got))return got;
   Color col=K_C(hex);
   return Paint(key,128,128,p=>{
    Vector2 d=p-new Vector2(.5f,.5f);float r=d.magnitude;float a=Mathf.Atan2(d.y,d.x);
    float lim=.36f+.12f*Mathf.Cos(a*12f);
    return r<=lim?col:Color.clear;
   });
  }

  // ------------------------------------------------------------------ bake helpers
  static bool Inside(Vector2 p,float x0,float x1,float y0,float y1)=>p.x>=x0&&p.x<=x1&&p.y>=y0&&p.y<=y1;
  static float DistSeg(Vector2 p,Vector2 a,Vector2 b){
   var ab=b-a;float t=Mathf.Clamp01(Vector2.Dot(p-a,ab)/Mathf.Max(1e-6f,ab.sqrMagnitude));
   return Vector2.Distance(p,a+ab*t);
  }
  static bool InTri(Vector2 p,Vector2 a,Vector2 b,Vector2 c){
   float d1=Side(p,a,b),d2=Side(p,b,c),d3=Side(p,c,a);
   bool neg=d1<0||d2<0||d3<0,pos=d1>0||d2>0||d3>0;
   return !(neg&&pos);
  }
  static float Side(Vector2 p,Vector2 a,Vector2 b)=>(p.x-b.x)*(a.y-b.y)-(a.x-b.x)*(p.y-b.y);
  static bool InPoly(Vector2 p,Vector2[] poly){
   bool inside=false;
   for(int i=0,j=poly.Length-1;i<poly.Length;j=i++){
    if((poly[i].y>p.y)!=(poly[j].y>p.y)&&p.x<(poly[j].x-poly[i].x)*(p.y-poly[i].y)/(poly[j].y-poly[i].y)+poly[i].x)inside=!inside;
   }
   return inside;
  }

  // Bakes a white shape: alpha = coverage.
  // The shape helpers are written bottom-up (y = 0 at the bottom of the sprite), so the top-down sample is flipped.
  static Sprite Bake(string key,Func<Vector2,bool> inside)=>Paint(key,Size,Size,p=>inside(new Vector2(p.x,1f-p.y))?Color.white:Color.clear);

  // Bakes a colour per sample (p in 0..1 across the texture, top-down); the colour's alpha is the coverage.
  static Sprite Paint(string key,int w,int h,Func<Vector2,Color> color){
   if(cache.TryGetValue(key,out var made))return made;
   var tex=new Texture2D(w,h,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
   tex.SetPixels32(Pixels(w,h,color));tex.Apply();
   var sprite=Sprite.Create(tex,new Rect(0,0,w,h),new Vector2(.5f,.5f),100f);
   cache[key]=sprite;return sprite;
  }
  // Same, but 9-sliced with a border in texels (the panels).
  static Sprite PaintSliced(string key,int w,int h,int border,Func<Vector2,Color> color){
   var tex=new Texture2D(w,h,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
   tex.SetPixels32(Pixels(w,h,color));tex.Apply();
   var sprite=Sprite.Create(tex,new Rect(0,0,w,h),new Vector2(.5f,.5f),100f,0,SpriteMeshType.FullRect,new Vector4(border,border,border,border));
   cache[key]=sprite;return sprite;
  }
  // Supersampled average: colour is averaged over the samples that hit (premultiplied), alpha is the hit ratio.
  static Color32[] Pixels(int w,int h,Func<Vector2,Color> color){
   var px=new Color32[w*h];
   float total=Samples*Samples;
   for(int y=0;y<h;y++)for(int x=0;x<w;x++){
    float r=0,g=0,b=0,a=0;
    for(int sy=0;sy<Samples;sy++)for(int sx=0;sx<Samples;sx++){
     // Texture row 0 is the bottom, so p.y runs top-down: 0 at the top row, 1 at the bottom row.
     var p=new Vector2((x+(sx+.5f)/Samples)/w,1f-(y+(sy+.5f)/Samples)/h);
     Color c=color(p);
     if(c.a<=0)continue;
     r+=c.r*c.a;g+=c.g*c.a;b+=c.b*c.a;a+=c.a;
    }
    if(a<=0){px[y*w+x]=new Color32(0,0,0,0);continue;}
    px[y*w+x]=new Color32((byte)Mathf.RoundToInt(Mathf.Clamp01(r/a)*255f),(byte)Mathf.RoundToInt(Mathf.Clamp01(g/a)*255f),(byte)Mathf.RoundToInt(Mathf.Clamp01(b/a)*255f),(byte)Mathf.RoundToInt(255f*a/total));
   }
   return px;
  }
 }
}
