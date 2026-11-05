using System.Collections.Generic;
using TMPro;
using UnityEngine;
namespace Checkout {
 // Cozy cream look shared with the React Native theme: rounded cards, 3D pressable buttons.
 public static class CheckoutDesktopKit {
  // The UI fonts have no emoji: coin/diamond/clock/lock pictographs from the shared page texts are dropped
  // (the icons next to them say the same).
  public static string Clean(string text){
   if(string.IsNullOrEmpty(text))return text;
   var sb=new System.Text.StringBuilder(text.Length);
   for(int i=0;i<text.Length;i++){
    char c=text[i];
    if(char.IsHighSurrogate(c)&&i+1<text.Length){i++;continue;} // 🪙 💎 🔒 🏗 …
    if(c=='\uFE0F'||c=='\u23F1'||c=='\u2714'||c=='\u26A0'||c=='\u2605'||c=='\u2606')continue; // variation selector, ⏱ ✔ ⚠ ★ ☆ (not in the game font: boxes)
    sb.Append(c);
   }
   return sb.ToString().Replace("  "," ").Trim();
  }
  public static Color C(string hex){ColorUtility.TryParseHtmlString("#"+hex,out var c);return c;}
  public static readonly Color Cream=C("FFF7EC"),Paper=C("FBEEDA"),Border=C("D4B482"),Ink=C("4A3624"),Muted=C("8A7560"),White=Color.white;

  public struct Style{public Color face,edge,text;public Style(string f,string e,string t){face=C(f);edge=C(e);text=C(t);}}
  public static Style Variant(string variant,bool enabled,bool active){
   if(!enabled)return new Style("E7DCCB","CDBFA8","9A8B78");
   if(active)return new Style("FFE3A8","E0A441","4A3624");
   switch(variant){
    case "success":return new Style("5DA637","427A24","FFFFFF");
    case "danger":return new Style("E15533","C0401F","FFFFFF");
    case "coin":return new Style("F2B03D","C58A1E","4A3624");
    case "gem":return new Style("8B5C9E","6A4279","FFFFFF");
    // "Iniciar sessão com a Apple": black with white text, as Apple asks for its button.
    case "apple":return new Style("111111","000000","FFFFFF");
    case "secondary":return new Style("FBEEDA","D4B482","4A3624");
    default:return new Style("2E8CAE","1F6A86","FFFFFF");
   }
  }
  public static Style Tone(string tone){
   switch(tone){
    case "success":return new Style("EAF6DF","8CC063","4A3624");
    case "danger":return new Style("FCE4DC","E59A84","4A3624");
    case "warning":return new Style("FFF1CF","E8B54A","4A3624");
    case "locked":return new Style("EFE7DA","C9BBA5","8A7560");
    case "info":return new Style("E2F1F7","86C0D6","4A3624");
    default:return new Style("FFF7EC","D4B482","4A3624");
   }
  }

  static readonly Dictionary<int,Sprite> rounded=new Dictionary<int,Sprite>();
  // White rounded rectangle, 9-sliced so any size keeps crisp corners.
  public static Sprite Rounded(int radius){
   if(rounded.TryGetValue(radius,out var cached))return cached;
   int size=radius*2+4;var texture=new Texture2D(size,size,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
   var pixels=new Color32[size*size];
   for(int y=0;y<size;y++)for(int x=0;x<size;x++){
    float cx=Mathf.Clamp(x+.5f,radius,size-radius),cy=Mathf.Clamp(y+.5f,radius,size-radius);
    float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(cx,cy));
    pixels[y*size+x]=new Color32(255,255,255,(byte)(Mathf.Clamp01(radius-d+.5f)*255));
   }
   texture.SetPixels32(pixels);texture.Apply();
   var sprite=Sprite.Create(texture,new Rect(0,0,size,size),new Vector2(.5f,.5f),100,0,SpriteMeshType.FullRect,new Vector4(radius+1,radius+1,radius+1,radius+1));
   rounded[radius]=sprite;return sprite;
  }

  // ---- round portraits (social v1): a picture clipped to a circle under a ring ----
  const int DiscSize=256;
  static Sprite disc;static readonly Dictionary<int,Sprite> rims=new Dictionary<int,Sprite>();
  static Sprite DiscSprite(float inner){
   var texture=new Texture2D(DiscSize,DiscSize,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
   var pixels=new Color32[DiscSize*DiscSize];float r=DiscSize*.5f;
   for(int y=0;y<DiscSize;y++)for(int x=0;x<DiscSize;x++){
    float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(r,r));
    float a=Mathf.Clamp01(r-.5f-d+.5f);if(inner>0)a*=Mathf.Clamp01(d-inner+.5f);
    pixels[y*DiscSize+x]=new Color32(255,255,255,(byte)(a*255));
   }
   texture.SetPixels32(pixels);texture.Apply();
   return Sprite.Create(texture,new Rect(0,0,DiscSize,DiscSize),new Vector2(.5f,.5f),100,0,SpriteMeshType.FullRect);
  }
  /// <summary>A white disc, not sliced: any square rect draws a clean circle (a portrait's plate and its round mask).</summary>
  public static Sprite Disc()=>disc?disc:(disc=DiscSprite(0));
  /// <summary>A white ring that fills a square of <paramref name="outer"/> units and leaves a hole of
  /// <paramref name="hole"/> units: the frame drawn over a masked picture.</summary>
  public static Sprite Rim(float outer,float hole){
   int inner=Mathf.Clamp(Mathf.RoundToInt(DiscSize*.5f*hole/Mathf.Max(1,outer)),8,DiscSize/2-2);
   if(rims.TryGetValue(inner,out var cached)&&cached)return cached;
   return rims[inner]=DiscSprite(inner);
  }
  /// <summary>A round holder: its children are clipped to the circle (the mask itself is not drawn). Off, it clips nothing.</summary>
  public static UnityEngine.UI.Image RoundClip(Transform parent,string name){
   var go=new GameObject(name,typeof(RectTransform));go.transform.SetParent(parent,false);
   var image=go.AddComponent<UnityEngine.UI.Image>();image.sprite=Disc();image.raycastTarget=false;
   go.AddComponent<UnityEngine.UI.Mask>().showMaskGraphic=false;
   var r=(RectTransform)go.transform;r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=r.offsetMax=Vector2.zero;
   return image;
  }
  public static void SetRound(UnityEngine.UI.Image clip,bool on){if(!clip)return;clip.enabled=on;var m=clip.GetComponent<UnityEngine.UI.Mask>();if(m)m.enabled=on;}
  /// <summary>A gold ring over a portrait: an image laid on <paramref name="plate"/> grown by <paramref name="border"/> on each
  /// side, its hole 1.5 units smaller than the plate so it hides the mask's hard edge.</summary>
  public static void FitRim(UnityEngine.UI.Image rim,float plate,float border){
   var r=rim.rectTransform;r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=new Vector2(-border,-border);r.offsetMax=new Vector2(border,border);
   rim.sprite=Rim(plate+border*2,plate-3);rim.type=UnityEngine.UI.Image.Type.Simple;rim.preserveAspect=false;
  }

  static readonly Dictionary<string,TMP_FontAsset> fonts=new Dictionary<string,TMP_FontAsset>();
  public static TMP_FontAsset Font(string name){
   if(fonts.TryGetValue(name,out var cached))return cached;
   var source=Resources.Load<Font>("CheckoutDesktop/Fonts/"+name);
   var asset=source?TMP_FontAsset.CreateFontAsset(source):TMP_Settings.defaultFontAsset;
   fonts[name]=asset;return asset;
  }
  public static TMP_FontAsset Headline=>Font("Fredoka_700Bold");
  public static TMP_FontAsset Label=>Font("Nunito_800ExtraBold");
  public static TMP_FontAsset Body=>Font("Nunito_700Bold");
  public static TMP_FontAsset Number=>Font("JetBrainsMono_700Bold");

  static readonly Dictionary<string,Sprite> icons=new Dictionary<string,Sprite>();static readonly Dictionary<string,float> misses=new Dictionary<string,float>();
  public static Sprite Icon(string path){
   if(string.IsNullOrEmpty(path))return null;
   // Social v1: "avatar:shopper-3" = a portrait of one of the game's own shoppers (drawn once by CheckoutSocial).
   if(path.StartsWith("avatar:",System.StringComparison.Ordinal))return CheckoutSocial.Avatar(path.Substring(7));
   // Rankings v1: "shape:star" = a shape drawn in code (CheckoutRankArt), white, painted by the Image's colour.
   if(path.StartsWith("shape:",System.StringComparison.Ordinal))return CheckoutRankArt.Shape(path.Substring(6));
   // Rede: the emblems, the chain's own products and the branch stores in the market's colours with the player's logo.
   if(CheckoutBrand.Handles(path))return CheckoutBrand.Icon(path);
   if(icons.TryGetValue(path,out var cached))return cached;
   // Misses are retried after a moment: a texture that was still importing loads next time.
   if(misses.TryGetValue(path,out var missedAt)&&Time.realtimeSinceStartup-missedAt<2)return null;
   var texture=Resources.Load<Texture2D>("CheckoutDesktop/"+path);
   var sprite=texture?Sprite.Create(texture,new Rect(0,0,texture.width,texture.height),new Vector2(.5f,.5f)):null;
   if(sprite){icons[path]=sprite;misses.Remove(path);}else misses[path]=Time.realtimeSinceStartup;
   return sprite;
  }
 }
}
