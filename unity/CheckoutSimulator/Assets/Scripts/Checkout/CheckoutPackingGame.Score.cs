using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // Sealing and grading. Score 0..1 starts at 1: each wrong product in a bag −.12, each extra unit −.07, each care
 // violation (fragile not last, heavy on fragile, the extra plastic-free bag, a wrong substitute) −.10, over par
 // −.04 per 10 s (max −.25); finishing under par +.05. Grade S ≥ .90, A ≥ .75, B ≥ .55, C ≥ .35, D below.
 // Sounds: the restock set while packing; the delivery coin and stars only in the result card.
 public sealed partial class CheckoutPackingGame:MonoBehaviour {
  sealed class PackScore {public int need,correct,wrong,extra,care,stars;public float secs,par,q;public bool quick;public string grade="D";}

  void Seal(){
   if(sealing||!ready||window==null||!window.activeSelf||pendingSubst)return;
   sealing=true;running=false;SetReady(false);
   var s=Evaluate();
   var placed=tokens.Where(t=>t.placed&&t.required).ToList();
   bridge.Command("packDeliveryOrder",PackArgs(s.q,s.secs,placed));
   StartCoroutine(SealRoutine(s,placed.Count));
  }

  PackScore Evaluate(){
   var s=new PackScore{need=requiredTotal,secs=elapsed,par=parSec};
   s.correct=tokens.Count(t=>t.placed&&t.required);
   s.wrong=tokens.Count(t=>t.placed&&t.kind==KindWrong);
   s.extra=tokens.Count(t=>t.placed&&t.kind==KindExtra);
   // The plastic-free twist: every bag beyond the first kraft one costs a care point.
   int spareBags=twistEco?bags.Count(b=>b.kind=="kraft"&&b!=kraft):0;
   s.care=CareViolations()+substMistakes+spareBags;
   s.quick=s.secs<=s.par;
   if(s.correct<=0){s.q=0f;s.grade="D";s.stars=0;return s;}
   float over=s.quick?0f:Mathf.Min(.35f,.06f*Mathf.Ceil((s.secs-s.par)/10f));
   float q=1f-.12f*s.wrong-.07f*s.extra-.10f*s.care-over+(s.quick?.05f:0f);
   s.q=Mathf.Clamp01(q);
   s.grade=s.q>=.9f?"S":s.q>=.75f?"A":s.q>=.55f?"B":s.q>=.35f?"C":"D";
   // S is only for a clean bag under the par time.
   if(s.grade=="S"&&!s.quick)s.grade="A";
   s.stars=s.grade=="S"?5:s.grade=="A"?4:s.grade=="B"?3:s.grade=="C"?2:1;
   return s;
  }
  // Fragile goods must stay last in their bag (any non-fragile after one is a violation); a heavy item on top of a
  // fragile one crushes it, the normal rule.
  int CareViolations(){
   int care=0;
   foreach(var b in bags){
    bool seen=false;
    foreach(var t in b.items){
     if(seen&&(twistFragile?!t.fragile:t.kg>=1.2f))care++;
     if(t.fragile)seen=true;
    }
   }
   return care;
  }
  // Ordered units only, capped at the order quantities by construction; quality = score.
  string PackArgs(float q,float secs,List<Token> placed){
   var counts=new SortedDictionary<int,int>();
   foreach(var t in placed)counts[t.productId]=(counts.TryGetValue(t.productId,out var c)?c:0)+1;
   var sb=new StringBuilder();
   sb.Append("[").Append(Json(orderId)).Append(",{\"items\":[");
   bool first=true;
   foreach(var kv in counts){
    if(!first)sb.Append(',');first=false;
    sb.Append("{\"productId\":").Append(kv.Key.ToString(CultureInfo.InvariantCulture)).Append(",\"quantity\":").Append(kv.Value.ToString(CultureInfo.InvariantCulture)).Append('}');
   }
   sb.Append("],\"quality\":").Append(q.ToString("0.00",CultureInfo.InvariantCulture));
   sb.Append(",\"seconds\":").Append(secs.ToString("0.0",CultureInfo.InvariantCulture)).Append("}]");
   return sb.ToString();
  }

  IEnumerator SealRoutine(PackScore s,int placed){
   foreach(var b in bags.Where(x=>x.items.Count>0).ToList()){if(!b.node)break;yield return CloseBag(b);}
   Bag sealBag=bags.FirstOrDefault(x=>x.items.Count>0&&x.kind=="kraft")??bags.FirstOrDefault(x=>x.items.Count>0);
   // No result screen and no jingle: the bags close, the sticker goes on, and the window closes.
   if(sealBag!=null)yield return StickerSlap(sealBag);
   yield return new WaitForSecondsRealtime(.7f);
   Close();
  }
  // The bag folds: the open layers swap for the closed one, with a squash.
  IEnumerator CloseBag(Bag b){
   PlayClip(CheckoutRestockSound.Flatten,.5f);
   if(b.back)b.back.gameObject.SetActive(false);
   if(b.front)b.front.gameObject.SetActive(false);
   if(b.glow)b.glow.gameObject.SetActive(false);
   b.inside.gameObject.SetActive(false);
   b.closed.gameObject.SetActive(true);
   yield return U.Scale(b.node,new Vector3(1.06f,.9f,1f),.12f);
   yield return U.Scale(b.node,Vector3.one,.18f,true);
  }
  // The customer's sticker, with their initials, slaps onto the sticker point of the folded bag.
  IEnumerator StickerSlap(Bag b){
   if(!b.node)yield break;
   float s=Mathf.Clamp(b.node.rect.width*.32f,40f,90f);
   var disc=new GameObject("Sticker",typeof(RectTransform),typeof(Image)).GetComponent<Image>();
   disc.transform.SetParent(b.node,false);disc.sprite=Disc();disc.color=Stickers[Mathf.Abs(order.avatar)%Stickers.Length];disc.raycastTarget=false;
   var r=disc.rectTransform;r.anchorMin=r.anchorMax=new Vector2(b.sticker[0],b.sticker[1]);r.pivot=Mid;r.sizeDelta=new Vector2(s,s);r.anchoredPosition=Vector2.zero;
   var lbl=U.Label(disc.transform,"Initials",K.Headline,s*.38f,"FFFFFF");U.Stretch(lbl.rectTransform,Vector2.zero,Vector2.one);
   lbl.text=Initials(order.customerName);
   r.localScale=Vector3.one*2.2f;
   PlayClip(CheckoutRestockSound.Place(false),.7f);
   yield return U.Scale(r,Vector3.one,.22f,true);
  }

  static Color GradeColor(string grade){
   switch(grade){
    case "S":return K.C("F2B03D");
    case "A":return K.C("5DA637");
    case "B":return K.C("2E8CAE");
    case "C":return K.C("F28C28");
    default:return K.C("E15533");
   }
  }
  // Tip share by stars (see src/services/delivery.ts getTipRate); the preview is an estimate.
  static float TipRate(int stars){return stars>=5?.2f:stars>=4?.1f:0f;}

  // The result card: a big grade letter pops in, stars fill one by one, breakdown lines count up, the tip preview.
  void ShowResult(PackScore s,int placed){
   if(!board)return;
   float cw=Mathf.Min(W*.6f,660f),ch=Mathf.Min(H*.84f,540f);
   var card=U.Shape(board,"Result","FFF7EC",30,Mid,new Vector2(cw,ch));
   var rt=card.rectTransform;rt.localScale=Vector3.zero;StartCoroutine(U.Scale(rt,Vector3.one,.45f,true));
   var head=U.Label(card.transform,"Title",K.Headline,36,"4A3624");
   U.Stretch(head.rectTransform,new Vector2(0,.86f),new Vector2(1,.97f),new Vector2(16,0),new Vector2(-16,0));
   head.text="Pedido pronto!";head.enableAutoSizing=true;head.fontSizeMin=20;head.fontSizeMax=36;
   var grade=U.Label(card.transform,"Grade",K.Headline,150,"FFFFFF");
   U.Stretch(grade.rectTransform,new Vector2(0,.6f),new Vector2(1,.85f));
   grade.text=s.grade;grade.color=GradeColor(s.grade);
   grade.textWrappingMode=TextWrappingModes.NoWrap;grade.overflowMode=TextOverflowModes.Overflow;grade.enableAutoSizing=true;grade.fontSizeMin=48;grade.fontSizeMax=150;
   grade.transform.localScale=Vector3.zero;StartCoroutine(U.Scale(grade.transform,Vector3.one,.5f,true));
   for(int i=0;i<5;i++){
    var star=new GameObject("Star"+i,typeof(RectTransform),typeof(Image)).GetComponent<Image>();
    star.transform.SetParent(card.transform,false);star.sprite=StarSprite();star.raycastTarget=false;star.color=K.C("D9CBB8");
    U.At(star.rectTransform,new Vector2(.5f,.55f),new Vector2(78,78),new Vector2((i-2)*88f,0));
    StartCoroutine(StarFill(star,i<s.stars,i));
   }
   string[] labels={"Itens certos","Errados","Sobras","Tempo","Cuidado"};
   for(int i=0;i<labels.Length;i++){
    var row=U.Label(card.transform,"Row"+i,K.Body,22,"4A3624",TextAlignmentOptions.Left);
    float y0=.42f-i*.065f;
    U.Stretch(row.rectTransform,new Vector2(.09f,y0),new Vector2(.91f,y0+.06f));
    row.enableAutoSizing=true;row.fontSizeMin=14;row.fontSizeMax=22;row.text="";
    float delay=.9f+.22f*i;
    if(i==3)StartCoroutine(TimeRow(row,s,delay));
    else StartCoroutine(CountRow(row,labels[i],i==0?s.correct:i==1?s.wrong:i==2?s.extra:s.care,i==0?" / "+s.need:"",delay));
   }
   int tip=Mathf.RoundToInt((order.itemsValue)*TipRate(s.stars));
   var coin=U.Icon(card.transform,"Coin","Icons/coin",new Vector2(.12f,.08f),new Vector2(44,44));
   var tipLbl=U.Label(card.transform,"Tip",K.Body,20,"4A3624",TextAlignmentOptions.Left);
   U.Stretch(tipLbl.rectTransform,new Vector2(.2f,.02f),new Vector2(.96f,.14f));
   tipLbl.enableAutoSizing=true;tipLbl.fontSizeMin=14;tipLbl.fontSizeMax=20;
   int chain=bridge.State?.delivery?.streak??0;
   tipLbl.text=(TipRate(s.stars)>0?string.Format("Gorjeta prevista: ~{0} moedas",tip):"Sem gorjeta nesta nota")+(chain>0?"  ·  "+string.Format("sequência x{0}",chain):"");
   coin.color=new Color(1,1,1,.95f);
   StartCoroutine(U.Pop(coin.transform,1.15f,.4f));
   if(s.grade=="S"){
    U.Sparkles(this,card.rectTransform,Vector2.zero,12,250);
    StartCoroutine(Confetti());
   }else if(s.grade=="A")U.Sparkles(this,card.rectTransform,Vector2.zero,6,200);
   CheckoutDeliverySound.Play(CheckoutDeliverySound.Star(s.grade=="D"?0:4),.6f);
  }
  IEnumerator StarFill(Image star,bool on,int i){
   yield return new WaitForSecondsRealtime(.45f+.22f*i);
   if(!star||!on)yield break;
   star.color=K.C("F2B03D");CheckoutDeliverySound.Play(CheckoutDeliverySound.Star(i),.6f);
   yield return U.Pop(star.transform,1.3f,.3f);
  }
  IEnumerator CountRow(TextMeshProUGUI lbl,string label,int value,string suffix,float delay){
   yield return new WaitForSecondsRealtime(delay);
   for(int k=0;k<=value;k++){
    if(!lbl)yield break;
    lbl.text=label+"  <b>"+k+"</b>"+suffix;
    if(k>0)CheckoutDeliverySound.Play(CheckoutDeliverySound.Star(0),.25f);
    yield return new WaitForSecondsRealtime(.14f);
   }
   if(lbl&&value>0)StartCoroutine(U.Pop(lbl.transform,1.06f,.2f));
  }
  IEnumerator TimeRow(TextMeshProUGUI lbl,PackScore s,float delay){
   yield return new WaitForSecondsRealtime(delay);
   if(!lbl)yield break;
   lbl.text=string.Format(s.quick?"Tempo  <b>{0}</b> · meta {1}  <color=#5DA637><b>Rápido!</b></color>":"Tempo  <b>{0}</b> · meta {1}  <color=#B03A2E>passou da meta</color>",Clock(s.secs),Clock(s.par));
   CheckoutDeliverySound.Play(CheckoutDeliverySound.Coin,.3f);
  }
  // Confetti for an S: small coloured dots fall from the top of the stage, swaying.
  IEnumerator Confetti(){
   if(!board)yield break;
   for(int i=0;i<26;i++){
    float x=UnityEngine.Random.Range(-W*.45f,W*.45f);
    var piece=U.GlowAt(board,"Confetti",Stickers[i%Stickers.Length],new Vector2(.5f,1f),UnityEngine.Random.Range(12f,20f),new Vector2(x,0));
    StartCoroutine(Fall(piece.rectTransform,UnityEngine.Random.Range(60f,160f),UnityEngine.Random.Range(0f,6f)));
    yield return new WaitForSecondsRealtime(.03f);
   }
  }
  static IEnumerator Fall(RectTransform r,float speed,float sway){
   if(!r)yield break;var from=r.anchoredPosition;
   for(float t=0;t<2.8f;t+=Time.unscaledDeltaTime){
    if(!r)yield break;
    r.anchoredPosition=from+new Vector2(Mathf.Sin(t*6f+sway)*30f,-speed*t);
    r.localRotation=Quaternion.Euler(0,0,t*200f*(sway>3?1f:-1f));
    yield return null;
   }
   if(r)Destroy(r.gameObject);
  }

  // ------------------------------------------------------------------ sprites generated once (soft disc, star)
  static Sprite Gen(string key,int w,int h,Func<int,int,Color32> pixel){
   if(generated.TryGetValue(key,out var cached))return cached;
   var tex=new Texture2D(w,h,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp,filterMode=FilterMode.Bilinear};
   var px=new Color32[w*h];
   for(int y=0;y<h;y++)for(int x=0;x<w;x++)px[y*w+x]=pixel(x,y);
   tex.SetPixels32(px);tex.Apply();
   var s=Sprite.Create(tex,new Rect(0,0,w,h),Mid,100f);generated[key]=s;return s;
  }
  static Sprite Disc()=>Gen("disc",128,128,(x,y)=>{float d=Vector2.Distance(new Vector2(x+.5f,y+.5f),new Vector2(64f,64f))/64f;float a=Mathf.Clamp01((1f-d)*64f);return new Color32(255,255,255,(byte)(a*255f));});
  static Sprite StarSprite(){
   var poly=new Vector2[10];
   for(int i=0;i<10;i++){float ang=(-90f+i*36f)*Mathf.Deg2Rad;float rad=i%2==0?.5f:.22f;poly[i]=Mid+new Vector2(Mathf.Cos(ang),Mathf.Sin(ang))*rad;}
   return Gen("star",128,128,(x,y)=>InPolygon(new Vector2((x+.5f)/128f,(y+.5f)/128f),poly)?new Color32(255,255,255,255):new Color32(255,255,255,0));
  }
  static bool InPolygon(Vector2 p,Vector2[] poly){
   bool inside=false;
   for(int i=0,j=poly.Length-1;i<poly.Length;j=i++){
    if((poly[i].y>p.y)!=(poly[j].y>p.y)&&p.x<(poly[j].x-poly[i].x)*(p.y-poly[i].y)/(poly[j].y-poly[i].y)+poly[i].x)inside=!inside;
   }
   return inside;
  }
 }
}
