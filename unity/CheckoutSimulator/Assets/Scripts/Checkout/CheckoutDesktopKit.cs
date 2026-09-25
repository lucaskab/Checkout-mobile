using System.Collections.Generic;
using TMPro;
using UnityEngine;
namespace Checkout {
 // Cozy cream look shared with the React Native theme: rounded cards, 3D pressable buttons.
 public static class CheckoutDesktopKit {
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

  static readonly Dictionary<string,Sprite> icons=new Dictionary<string,Sprite>();
  public static Sprite Icon(string path){
   if(string.IsNullOrEmpty(path))return null;
   if(icons.TryGetValue(path,out var cached))return cached;
   var texture=Resources.Load<Texture2D>("CheckoutDesktop/"+path);
   var sprite=texture?Sprite.Create(texture,new Rect(0,0,texture.width,texture.height),new Vector2(.5f,.5f)):null;
   icons[path]=sprite;return sprite;
  }
 }
}
