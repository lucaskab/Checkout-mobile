using System;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 // Rede de supermercados: the chain's brand as pictures. The name and the emblem come in the snapshot (chain), the two
 // colours are the market's ("Cores do mercado", paint). Codex painted the art with mask colours and
 // scripts/art/rede_art.py turned it into:
 //  - Rede/Emblems/<id>.png  RGBA mask: R = main colour, G = accent, B = white, A = coverage;
 //  - Products/product-172..179.png and Rede/filial-<id>.png in the classic navy/gold with the basket logo, plus
 //    Rede/Tint/<name>.png (R = band shading, G = band, B = logo circle, A = coverage) and Rede/logo_spots.json.
 // Here they are tinted with the market's colours and the player's emblem, once per change, and handed to the HUD
 // (K.Icon asks Handles/Icon first) and to the world (Logo).
 public static class CheckoutBrand {
  public static readonly Color ClassicPrimary=new Color32(0x1D,0x2B,0x4F,255),ClassicAccent=new Color32(0xD3,0xA5,0x3D,255);
  public static bool Unlocked{get;private set;}
  public static bool Named{get;private set;}
  public static string Name{get;private set;}="";
  public static string Emblem{get;private set;}="cesta";
  public static Color Primary{get;private set;}=ClassicPrimary;
  public static Color Accent{get;private set;}=ClassicAccent;
  /// <summary>Goes up on every change of name, emblem or colours (the world re-dresses itself).</summary>
  public static int Version{get;private set;}
  public static event Action Changed;

  static readonly Dictionary<string,Sprite> sprites=new Dictionary<string,Sprite>();
  static readonly Dictionary<string,Texture2D> textures=new Dictionary<string,Texture2D>();
  static Dictionary<string,Vector3> spots;

  public static void Apply(ChainState chain,PaintState paint){
   var p=Hex(paint?.primary,ClassicPrimary);var a=Hex(paint?.accent,ClassicAccent);
   bool unlocked=chain!=null&&chain.unlocked,named=unlocked&&chain.named;
   string name=named?(chain.brand??""):"";string emblem=string.IsNullOrEmpty(chain?.emblem)?"cesta":chain.emblem;
   if(unlocked==Unlocked&&named==Named&&name==Name&&emblem==Emblem&&p==Primary&&a==Accent)return;
   bool look=emblem!=Emblem||p!=Primary||a!=Accent;
   Unlocked=unlocked;Named=named;Name=name;Emblem=emblem;Primary=p;Accent=a;Version++;
   if(look)Flush();
   Changed?.Invoke();
  }

  static Color Hex(string hex,Color fallback){
   if(string.IsNullOrEmpty(hex))return fallback;
   return ColorUtility.TryParseHtmlString(hex.StartsWith("#")?hex:"#"+hex,out var c)?c:fallback;
  }
  static void Flush(){
   foreach(var t in textures.Values)if(t)UnityEngine.Object.Destroy(t);
   textures.Clear();sprites.Clear();
  }

  // ------------------------------------------------------------------------------------------------ HUD
  /// <summary>Paths the brand draws: the emblems, the chain's own products and the branch stores.</summary>
  public static bool Handles(string path){
   if(path.StartsWith("Rede/Emblems/",StringComparison.Ordinal))return true;
   if(path.StartsWith("Rede/filial-",StringComparison.Ordinal))return true;
   return path.StartsWith("Products/product-17",StringComparison.Ordinal)&&IsOwnProduct(path.Substring(9));
  }
  static bool IsOwnProduct(string name)=>name.Length==11&&int.TryParse(name.Substring(8),out var id)&&id>=172&&id<=179;

  public static Sprite Icon(string path){
   if(sprites.TryGetValue(path,out var cached)&&cached)return cached;
   Texture2D tex=null;
   if(path.StartsWith("Rede/Emblems/",StringComparison.Ordinal))tex=EmblemTexture(path.Substring(13));
   else{var name=path.Substring(path.LastIndexOf('/')+1);tex=Composite(path,name);}
   if(!tex)return null;
   var sprite=Sprite.Create(tex,new Rect(0,0,tex.width,tex.height),new Vector2(.5f,.5f));
   sprites[path]=sprite;return sprite;
  }

  /// <summary>The player's logo (the chosen emblem in the market's colours).</summary>
  public static Texture2D Logo=>EmblemTexture(Emblem);

  static Texture2D EmblemTexture(string id){
   var key="emblem:"+id;
   if(textures.TryGetValue(key,out var t)&&t)return t;
   var mask=Resources.Load<Texture2D>("CheckoutDesktop/Rede/Emblems/"+id);
   if(!mask||!mask.isReadable)return mask;
   var px=mask.GetPixels32();var outPx=new Color32[px.Length];
   Color32 pc=Primary,ac=Accent;
   for(int i=0;i<px.Length;i++){
    var m=px[i];float r=m.r/255f,g=m.g/255f,b=m.b/255f;
    outPx[i]=new Color32((byte)Mathf.Clamp(pc.r*r+ac.r*g+255*b,0,255),(byte)Mathf.Clamp(pc.g*r+ac.g*g+255*b,0,255),(byte)Mathf.Clamp(pc.b*r+ac.b*g+255*b,0,255),m.a);
   }
   t=new Texture2D(mask.width,mask.height,TextureFormat.RGBA32,true){name="Brand "+id,wrapMode=TextureWrapMode.Clamp};
   t.SetPixels32(outPx);t.Apply(true,false);
   textures[key]=t;return t;
  }

  /// <summary>A picture with brand parts (own product, branch store) in the market's colours with the player's logo.</summary>
  static Texture2D Composite(string path,string name){
   var key="art:"+path;
   if(textures.TryGetValue(key,out var t)&&t)return t;
   var src=Resources.Load<Texture2D>("CheckoutDesktop/"+path);
   var tint=Resources.Load<Texture2D>("CheckoutDesktop/Rede/Tint/"+name);
   if(!src)return null;
   bool classic=Primary==ClassicPrimary&&Accent==ClassicAccent&&Emblem=="cesta";
   if(classic||!tint||!src.isReadable||!tint.isReadable)return src;
   int w=src.width,h=src.height;
   var basePx=src.GetPixels();var tintPx=tint.width==w&&tint.height==h?tint.GetPixels():ScaledPixels(tint,w,h);
   var outPx=new Color[basePx.Length];
   for(int i=0;i<basePx.Length;i++){
    var c=basePx[i];var tt=tintPx[i];float band=tt.g;
    if(band>.003f){float shade=Mathf.Clamp01(tt.r/Mathf.Max(band,1e-3f));var col=Primary*(.55f+.75f*shade);col.a=c.a;c=Color.Lerp(c,new Color(Mathf.Clamp01(col.r),Mathf.Clamp01(col.g),Mathf.Clamp01(col.b),c.a),band);}
    outPx[i]=c;
   }
   if(Spots().TryGetValue(name,out var spot))PaintLogo(outPx,w,h,spot);
   t=new Texture2D(w,h,TextureFormat.RGBA32,true){name="Brand "+name,wrapMode=TextureWrapMode.Clamp};
   t.SetPixels(outPx);t.Apply(true,false);
   textures[key]=t;return t;
  }

  static Color[] ScaledPixels(Texture2D tex,int w,int h){
   var o=new Color[w*h];for(int y=0;y<h;y++)for(int x=0;x<w;x++)o[y*w+x]=tex.GetPixelBilinear((x+.5f)/w,(y+.5f)/h);return o;
  }

  // A cream plate on the logo circle with the emblem on it (spot: x, y from the top, radius; all 0..1 of the width).
  static void PaintLogo(Color[] px,int w,int h,Vector3 spot){
   var emblem=EmblemTexture(Emblem);if(!emblem||!emblem.isReadable)return;
   float cx=spot.x*w,cy=(1-spot.y)*h,rad=spot.z*w;var cream=new Color32(0xFB,0xF8,0xF1,255);
   float size=rad*1.5f;
   int x0=Mathf.Max(0,Mathf.FloorToInt(cx-rad-3)),x1=Mathf.Min(w-1,Mathf.CeilToInt(cx+rad+3));
   int y0=Mathf.Max(0,Mathf.FloorToInt(cy-rad-3)),y1=Mathf.Min(h-1,Mathf.CeilToInt(cy+rad+3));
   for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){
    int i=y*w+x;float d=Mathf.Sqrt((x+.5f-cx)*(x+.5f-cx)+(y+.5f-cy)*(y+.5f-cy));
    float plate=Mathf.Clamp01(rad+2.5f*w/128f-d);if(plate<=0)continue;
    var c=px[i];c=Color.Lerp(c,(Color)cream,plate);
    float u=(x+.5f-(cx-size/2))/size,v=(y+.5f-(cy-size/2))/size;
    if(u>=0&&u<=1&&v>=0&&v<=1){var e=emblem.GetPixelBilinear(u,v);c=Color.Lerp(c,new Color(e.r,e.g,e.b,1),e.a);}
    c.a=Mathf.Max(px[i].a,plate);px[i]=c;
   }
  }

  [Serializable] class Spot{public string name;public float x,y,r;}
  [Serializable] class SpotList{public Spot[] items;}
  static Dictionary<string,Vector3> Spots(){
   if(spots!=null)return spots;
   spots=new Dictionary<string,Vector3>();
   var json=Resources.Load<TextAsset>("CheckoutDesktop/Rede/logo_spots");
   if(json){var list=JsonUtility.FromJson<SpotList>(json.text);if(list?.items!=null)foreach(var s in list.items)if(s!=null&&!string.IsNullOrEmpty(s.name))spots[s.name]=new Vector3(s.x,s.y,s.r);}
   return spots;
  }
 }
}
