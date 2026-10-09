using System.Collections.Generic;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // Boosters running now (Melhorias → Boosters, desktop/view.ts boosts): a glowing chip under the top bar for each
 // one and the edges of the screen tinted with its colour. Each booster moves its own way:
 //  · Café Energético: amber, buzzing icon, fast heartbeat glow, sparkle ring spinning quickly.
 //  · Happy Hour: party colours cycling, icon bouncing to a beat, slow disco ring.
 //  · Liquidação Relâmpago: red sale sign, icon swinging like a hanging tag, blinking like a shop light.
 // The chip pops in when a booster starts (with a coloured flash on the screen) and fades out when it ends.
 public partial class CheckoutDesktopHUD {
  class BoostChip {
   public string id;public RectTransform rect,iconRect,fill;public UnityEngine.UI.Image edge,glow,halo,icon,bar;
   public TextMeshProUGUI name,timer,effect;public CanvasGroup group;
   public Color tint;public float secondsAt,receivedAt,total,born,leftAt=-1;
  }
  RectTransform boostColumn;readonly List<BoostChip> boostChips=new List<BoostChip>();
  UnityEngine.UI.Image boostAura;float boostFlashAt=-10;Color boostFlashColor=Color.white;
  static Sprite glowSprite,haloSprite,vignetteSprite;

  static readonly Color[] PartyColors={K.C("E35DB0"),K.C("9B5DE5"),K.C("F7C548"),K.C("3EC1D3")};

  void BuildBoosts(){
   // Screen-edge aura: under every panel (first child of the canvas), never catching clicks.
   boostAura=N.Image(root,"BoostAura",Color.clear,0);boostAura.sprite=Vignette();
   var ar=boostAura.rectTransform;ar.anchorMin=Vector2.zero;ar.anchorMax=Vector2.one;ar.offsetMin=ar.offsetMax=Vector2.zero;
   boostAura.transform.SetAsFirstSibling();boostAura.gameObject.SetActive(false);

   // Chips: a column on the right, under the coins and diamonds (the left side has the REPOR/CONSERTAR buttons).
   boostColumn=N.Node("Boosts",root);boostColumn.anchorMin=boostColumn.anchorMax=boostColumn.pivot=new Vector2(1,1);
   boostColumn.anchoredPosition=new Vector2(-18,-150);
   var col=N.Column(boostColumn.gameObject,10);col.childForceExpandWidth=false;col.childAlignment=TextAnchor.UpperRight;
   var fit=boostColumn.gameObject.AddComponent<UnityEngine.UI.ContentSizeFitter>();
   fit.horizontalFit=fit.verticalFit=UnityEngine.UI.ContentSizeFitter.FitMode.PreferredSize;
  }

  BoostChip CreateBoostChip(DesktopBoost b){
   var chip=new BoostChip{id=b.id,born=Time.unscaledTime};
   var holder=N.Node("Boost "+b.id,boostColumn);chip.rect=holder;
   var le=holder.gameObject.AddComponent<UnityEngine.UI.LayoutElement>();le.preferredWidth=330;le.preferredHeight=72;
   chip.group=holder.gameObject.AddComponent<CanvasGroup>();chip.group.blocksRaycasts=false;chip.group.interactable=false;

   // Soft coloured glow behind the whole chip.
   chip.glow=N.Image(holder,"Glow",Color.clear,0);chip.glow.sprite=Glow();
   var gr=chip.glow.rectTransform;gr.anchorMin=Vector2.zero;gr.anchorMax=Vector2.one;gr.offsetMin=new Vector2(-26,-24);gr.offsetMax=new Vector2(26,24);

   // Raised panel: coloured edge, cream face.
   chip.edge=N.Image(holder,"Edge",Color.white,18);var er=chip.edge.rectTransform;er.anchorMin=Vector2.zero;er.anchorMax=Vector2.one;er.offsetMin=er.offsetMax=Vector2.zero;
   var face=N.Image(chip.edge.transform,"Face",K.Cream,16);var fr=face.rectTransform;fr.anchorMin=Vector2.zero;fr.anchorMax=Vector2.one;fr.offsetMin=new Vector2(3,6);fr.offsetMax=new Vector2(-3,-3);

   // Icon in a round badge with a spinning sparkle ring.
   var badge=N.Node("Badge",face.transform);badge.anchorMin=badge.anchorMax=new Vector2(0,.5f);badge.pivot=new Vector2(.5f,.5f);badge.anchoredPosition=new Vector2(34,0);badge.sizeDelta=new Vector2(52,52);
   chip.halo=N.Image(badge,"Halo",Color.white,0);chip.halo.sprite=Halo();var hr=chip.halo.rectTransform;hr.anchorMin=hr.anchorMax=new Vector2(.5f,.5f);hr.sizeDelta=new Vector2(70,70);
   var disc=N.Image(badge,"Disc",Color.white,26);var dr=disc.rectTransform;dr.anchorMin=Vector2.zero;dr.anchorMax=Vector2.one;dr.offsetMin=dr.offsetMax=Vector2.zero;disc.color=new Color(1,1,1,.92f);
   chip.icon=N.Image(badge,"Icon",Color.white,0);chip.icon.preserveAspect=true;chip.iconRect=chip.icon.rectTransform;
   chip.iconRect.anchorMin=chip.iconRect.anchorMax=new Vector2(.5f,.5f);chip.iconRect.sizeDelta=new Vector2(40,40);

   // Name + timer on top, the effect below, a bar that drains at the bottom.
   chip.name=N.Text(face.transform,"Name",K.Label,14,K.Ink);chip.name.textWrappingMode=TextWrappingModes.NoWrap;chip.name.overflowMode=TextOverflowModes.Ellipsis;
   Place(chip.name.rectTransform,68,-9,-66,22);
   chip.timer=N.Text(face.transform,"Timer",K.Number,16,K.Ink);chip.timer.alignment=TextAlignmentOptions.Right;chip.timer.textWrappingMode=TextWrappingModes.NoWrap;
   var tr=chip.timer.rectTransform;tr.anchorMin=tr.anchorMax=tr.pivot=new Vector2(1,1);tr.anchoredPosition=new Vector2(-10,-8);tr.sizeDelta=new Vector2(64,22);
   chip.effect=N.Text(face.transform,"Effect",K.Body,13,K.Muted);chip.effect.textWrappingMode=TextWrappingModes.NoWrap;chip.effect.overflowMode=TextOverflowModes.Ellipsis;
   Place(chip.effect.rectTransform,68,-30,-10,18);
   chip.bar=N.Image(face.transform,"Track",K.C("EADBC4"),4);var br=chip.bar.rectTransform;br.anchorMin=new Vector2(0,0);br.anchorMax=new Vector2(1,0);br.pivot=new Vector2(.5f,0);br.offsetMin=new Vector2(68,8);br.offsetMax=new Vector2(-10,15);
   var fill=N.Image(chip.bar.transform,"Fill",Color.white,4);chip.fill=fill.rectTransform;chip.fill.anchorMin=Vector2.zero;chip.fill.anchorMax=new Vector2(1,1);chip.fill.offsetMin=chip.fill.offsetMax=Vector2.zero;
   chip.bar=fill;

   holder.localScale=Vector3.one*.2f;
   boostFlashAt=Time.unscaledTime;
   return chip;
  }
  static void Place(RectTransform r,float left,float top,float right,float height){r.anchorMin=new Vector2(0,1);r.anchorMax=new Vector2(1,1);r.pivot=new Vector2(0,1);r.offsetMin=new Vector2(left,top-height);r.offsetMax=new Vector2(right,top);}

  void ApplyBoosts(DesktopView v){
   var list=v.boosts??new DesktopBoost[0];
   foreach(var b in list){
    if(string.IsNullOrEmpty(b.id))continue;
    var chip=boostChips.Find(c=>c.id==b.id&&c.leftAt<0);
    if(chip==null){chip=CreateBoostChip(b);boostChips.Add(chip);boostFlashColor=K.C(b.tint);}
    chip.tint=K.C(b.tint);chip.secondsAt=b.seconds;chip.receivedAt=Time.unscaledTime;chip.total=Mathf.Max(1,b.total);
    var sprite=K.Icon(b.icon);if(sprite)chip.icon.sprite=sprite;
    chip.name.text=b.name;chip.effect.text=K.Clean(b.effect);
   }
   // Ended (or used up): fade out.
   foreach(var chip in boostChips)if(chip.leftAt<0&&System.Array.FindIndex(list,b=>b.id==chip.id)<0)chip.leftAt=Time.unscaledTime;
  }

  void UpdateBoosts(){
   float now=Time.unscaledTime;
   Color auraColor=Color.clear;float auraAlpha=0;int live=0;
   for(int i=boostChips.Count-1;i>=0;i--){
    var c=boostChips[i];
    // Enter: elastic pop. Leave: shrink and fade.
    float age=now-c.born,scale=age<.45f?Mathf.LerpUnclamped(.2f,1,BackOut(age/.45f)):1f,alpha=1;
    if(c.leftAt>=0){float k=(now-c.leftAt)/.35f;if(k>=1){Destroy(c.rect.gameObject);boostChips.RemoveAt(i);continue;}scale*=1-.4f*k;alpha=1-k;}
    c.rect.localScale=Vector3.one*scale;c.group.alpha=alpha;

    float left=Mathf.Max(0,c.secondsAt-(now-c.receivedAt));
    int s=Mathf.CeilToInt(left);c.timer.text=(s/60)+":"+(s%60).ToString("00");
    c.fill.anchorMax=new Vector2(Mathf.Clamp01(left/c.total),1);

    Color tint=c.tint;float glow=.55f;
    switch(c.id){
     case "energy-coffee":{ // buzzing with energy
      float beat=Mathf.Pow(Mathf.Abs(Mathf.Sin(now*Mathf.PI*2.4f)),6);glow=.45f+.5f*beat;
      c.iconRect.localRotation=Quaternion.Euler(0,0,Mathf.Sin(now*55)*4);c.iconRect.anchoredPosition=new Vector2(Mathf.Sin(now*47)*1.2f,Mathf.Cos(now*39)*1.2f);
      c.halo.rectTransform.localRotation=Quaternion.Euler(0,0,-now*240);c.halo.rectTransform.localScale=Vector3.one*(1+.08f*beat);
      break;}
     case "happy-hour":{ // party: colours cycle, icon dances to the beat
      float h=now*.5f%PartyColors.Length;int a=(int)h;tint=Color.Lerp(PartyColors[a],PartyColors[(a+1)%PartyColors.Length],h-a);
      float bounce=Mathf.Abs(Mathf.Sin(now*Mathf.PI*2));glow=.5f+.35f*bounce;
      c.iconRect.anchoredPosition=new Vector2(0,bounce*6-2);c.iconRect.localScale=new Vector3(1+.08f*(1-bounce),1-.06f*(1-bounce),1);
      c.halo.rectTransform.localRotation=Quaternion.Euler(0,0,now*70);c.halo.rectTransform.localScale=Vector3.one;
      break;}
     case "flash-sale":{ // a hanging sale tag that blinks like a shop light
      float blink=Mathf.Sin(now*Mathf.PI*6)>0?1:.25f;glow=.3f+.6f*blink;
      c.iconRect.localRotation=Quaternion.Euler(0,0,Mathf.Sin(now*4.2f)*16);c.iconRect.anchoredPosition=Vector2.zero;
      c.halo.rectTransform.localRotation=Quaternion.Euler(0,0,now*120);c.halo.rectTransform.localScale=Vector3.one*(1+.1f*blink);
      break;}
     default:{glow=.45f+.25f*Mathf.Sin(now*3);c.halo.rectTransform.localRotation=Quaternion.Euler(0,0,now*90);break;}
    }
    // The last ten seconds: the edge blinks.
    bool ending=left<=10&&c.leftAt<0;
    c.edge.color=ending&&Mathf.Sin(now*Mathf.PI*4)>0?K.C("E15533"):tint;
    c.glow.color=new Color(tint.r,tint.g,tint.b,glow*.8f*alpha);
    c.halo.color=new Color(tint.r,tint.g,tint.b,.9f*alpha);c.bar.color=tint;c.timer.color=ending?K.C("C0401F"):K.Ink;

    if(c.leftAt<0){live++;auraColor+=tint;auraAlpha+=.1f+.08f*glow;}
   }

   // Screen edges: the mix of the boosters' colours, breathing; a start flashes stronger for a moment.
   float flash=Mathf.Clamp01(1-(now-boostFlashAt)/.7f);
   bool show=live>0||flash>0;boostAura.gameObject.SetActive(show);
   if(show){
    Color mix=live>0?auraColor/live:boostFlashColor;
    mix=Color.Lerp(mix,boostFlashColor,flash);
    float a=Mathf.Min(.32f,live>0?auraAlpha/live:0)+.45f*flash*flash;
    boostAura.color=new Color(mix.r,mix.g,mix.b,a);
   }
  }

  // Overshoots a little and settles (a pop).
  static float BackOut(float t){t=Mathf.Clamp01(t)-1;const float c1=1.70158f,c3=c1+1;return 1+c3*t*t*t+c1*t*t;}

  // ------------------------------------------------------------------ generated sprites
  static Sprite Glow(){
   if(glowSprite)return glowSprite;const int n=128;var t=new Texture2D(n,n,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp};var px=new Color32[n*n];
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){
    // Rounded-rectangle glow: strongest near the chip's border, fading outwards.
    float dx=Mathf.Max(0,Mathf.Abs((x+.5f)/n*2-1)-.55f)/.45f,dy=Mathf.Max(0,Mathf.Abs((y+.5f)/n*2-1)-.45f)/.55f;
    float d=Mathf.Sqrt(dx*dx+dy*dy);float a=Mathf.Clamp01(1-d);a=a*a*(3-2*a);px[y*n+x]=new Color32(255,255,255,(byte)(a*255));
   }
   t.SetPixels32(px);t.Apply();return glowSprite=Sprite.Create(t,new Rect(0,0,n,n),new Vector2(.5f,.5f));
  }
  static Sprite Halo(){
   if(haloSprite)return haloSprite;const int n=128;var t=new Texture2D(n,n,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp};var px=new Color32[n*n];
   // A ring of twelve little sparks with a faint band between them.
   for(int y=0;y<n;y++)for(int x=0;x<n;x++){
    float dx=(x+.5f)/n*2-1,dy=(y+.5f)/n*2-1,d=Mathf.Sqrt(dx*dx+dy*dy),ang=Mathf.Atan2(dy,dx);
    float band=Mathf.Clamp01(1-Mathf.Abs(d-.84f)/.06f)*.35f;
    float seg=Mathf.Repeat(ang/(Mathf.PI*2)*12,1)-.5f;float spark=Mathf.Clamp01(1-Mathf.Sqrt(seg*seg*3.2f+(d-.84f)*(d-.84f)*90));
    float a=Mathf.Clamp01(band+spark*spark);px[y*n+x]=new Color32(255,255,255,(byte)(a*255));
   }
   t.SetPixels32(px);t.Apply();return haloSprite=Sprite.Create(t,new Rect(0,0,n,n),new Vector2(.5f,.5f));
  }
  static Sprite Vignette(){
   if(vignetteSprite)return vignetteSprite;const int w=160,h=100;var t=new Texture2D(w,h,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp};var px=new Color32[w*h];
   // Clear in the middle, coloured towards the edges and strongest in the corners.
   for(int y=0;y<h;y++)for(int x=0;x<w;x++){
    float dx=Mathf.Abs((x+.5f)/w*2-1),dy=Mathf.Abs((y+.5f)/h*2-1);
    float edge=Mathf.Max(Mathf.Pow(dx,5),Mathf.Pow(dy,4));float corner=Mathf.Pow(dx*dy,2.5f);
    float a=Mathf.Clamp01(edge*.9f+corner*.6f);px[y*w+x]=new Color32(255,255,255,(byte)(a*255));
   }
   t.SetPixels32(px);t.Apply();return vignetteSprite=Sprite.Create(t,new Rect(0,0,w,h),new Vector2(.5f,.5f));
  }
 }
}
