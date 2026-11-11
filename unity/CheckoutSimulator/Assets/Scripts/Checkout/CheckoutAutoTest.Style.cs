using System.Collections;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout {
 // "Estilo do mercado" (CheckoutMarketStyle + CheckoutMarketStylePanel), on the QA copy of the save (the word "events"):
 //  - "eventsstyle[-stage.stage…]": looks previewed on each stage, shot inside the shop and close on the back sign:
 //    Logs/st_<stage>_<look>_<view>.jpg, STYLE lines with what was dressed.
 //  - "eventsstylesign": one sign look, frames 0.15 s apart for each effect (Logs/ss_<effect>_<frame>.jpg).
 //  - "eventsstyleui": the picker as a player uses it, bought with coins and diamonds (Logs/at_style_ui_*.png).
 public sealed partial class CheckoutAutoTest {
  static StyleChoice Look(string floor,string floorColor,string wall,string wallColor,string uniform,string um,string ud,string font,string look,string effect,string main,string second,string palette="arco-iris",int speed=1)=>
   new StyleChoice{floor=floor,floorColor=floorColor,wall=wall,wallColor=wallColor,uniform=uniform,uniformMain=um,uniformDetail=ud,sign=new StyleSign{font=font,look=look,effect=effect,main=main,second=second,palette=palette,speed=speed}};
  static readonly (string id,StyleChoice c)[] StyleLooks={
   ("classico",new StyleChoice()),
   ("a",Look("taco","","tijolinho","","vermelho","C0392B","F4F6F8","redonda","neon","pulsar","FF4FD8","4FF5FF")),
   ("b",Look("xadrez","1D2B4F","metro","F4F6F8","personalizado","2F6FA8","F2C230","pesada","caixa","onda","FFD54F","C0392B")),
   ("c",Look("marmore-escuro","","ripado","","preto","1E2024","D9A93E","fina","neon-placa","falhando","4FF5FF","FF4FD8")),
   ("d",Look("ladrilho","","floral","E86A9E","verde","1F7A4D","F0E2B6","esportiva","lampadas","letra","FFB300","8A1C2B")),
   ("e",Look("granilite","","pastilha","2F8FA0","turquesa","1E9A96","F27D5E","redonda","colorido","arco-iris","FFD54F","E53935","tropical")),
   ("f",Look("cimento","","lousa","","laranja","E3762C","1D2B4F","elegante","contorno","piscar","FFFFFF","1D2B4F")),
   ("g",Look("vinil","E86A9E","listrado","4A90D0","ceu","4A90D0","F4F6F8","digital","degrade","brilho","4FF5FF","9D7CFF")),
   ("h",Look("madeira-clara","","pedra","","mostarda","D9A520","5A3A24","moderna","liso","alternar","F2C230","1D2B4F")),
  };

  IEnumerator Style(string request){
   if(request.StartsWith("eventsstylesign"))return StyleSign(request);
   if(request.StartsWith("eventsstyleui"))return StyleUi(request);
   if(request.StartsWith("eventsstyleuniform"))return StyleUniform(request);
   return StyleCompare(request);
  }

  Bounds StyleSignBounds(){
   var dressing=GameObject.Find("Market Stage Dressing");var b=new Bounds(Vector3.zero,Vector3.zero);
   if(!dressing)return b;
   foreach(var name in new[]{"S4 name","S2 name","S1 rear sign","S0 name board"}){
    var t=dressing.transform.Find(name);if(!t||!t.gameObject.activeInHierarchy)continue;
    bool any=false;foreach(var r in t.GetComponentsInChildren<Renderer>(false)){if(!r.enabled)continue;if(!any){b=r.bounds;any=true;}else b.Encapsulate(r.bounds);}
    if(any)return b;
   }
   return b;
  }

  IEnumerator StyleCompare(string request){
   var parts=request.Split('-');
   var stages=parts.Length>1?parts[1].Split('.'):new[]{"spati","quitanda","minimercado","mercadinho","supermercado","hipermercado"};
   foreach(var f in Directory.GetFiles("Logs","st_*.jpg"))File.Delete(f);
   var style=CheckoutMarketStyle.Active;if(!style){Note("STYLE no CheckoutMarketStyle");yield break;}
   foreach(var stage in stages){
    yield return GoToStage(stage);
    // staff in the shop for the uniform
    bool small=CheckoutStall.Small;var shell=FindAnyObjectByType<CheckoutMarketShell>();
    var fp=small?CheckoutStall.Footprint:shell?shell.Footprint:new Bounds(Vector3.zero,Vector3.one*20);
    Note($"STYLE {stage}: era={bridge.State?.era?.id} small={small} inside={CheckoutStall.ShopInside} floor={CheckoutStall.InteriorFloor} y={CheckoutStall.FloorY} unlocked={bridge.State?.style?.insideUnlocked}/{bridge.State?.style?.signUnlocked}");
    foreach(var (id,c) in StyleLooks){
     if(small&&(id=="e"||id=="g"||id=="h"))continue;
     style.Preview(c);yield return new WaitForSecondsRealtime(.8f);
     Note($"STYLE {stage} {id}: {style.QaReport()}");
     float size=Mathf.Max(fp.size.x,fp.size.z)*(small?1.25f:.8f)+1;
     CaptureSized($"st_{stage}_{id}_inside",2000,1100,new Vector3(fp.center.x,small?.6f:.8f,fp.center.z),size);
     if(!small){var sb=StyleSignBounds();if(sb.size.x>0)CaptureSized($"st_{stage}_{id}_sign",2000,1100,sb.center,Mathf.Max(6,sb.size.x*1.25f));}
    }
    style.EndPreview();yield return new WaitForSecondsRealtime(.4f);
   }
  }

  IEnumerator StyleSign(string request){
   foreach(var f in Directory.GetFiles("Logs","ss_*.jpg"))File.Delete(f);
   yield return GoToStage(request.Contains("-")?request.Split('-')[1]:"supermercado");
   var style=CheckoutMarketStyle.Active;if(!style){Note("STYLE no CheckoutMarketStyle");yield break;}
   var looks=new[]{("neon","pulsar","FF4FD8"),("neon-placa","letra","4FF5FF"),("neon","falhando","B6FF4F"),("caixa","onda","FFD54F"),("colorido","arco-iris","FFD54F"),("lampadas","piscar","FFB300"),("liso","brilho","E53935"),("contorno","alternar","FFFFFF")};
   foreach(var (look,effect,main) in looks){
    var c=Look(Classic(),"",Classic(),"",Classic(),"","","redonda",look,effect,main,"1D2B4F");
    style.Preview(c);yield return new WaitForSecondsRealtime(.6f);
    var sb=StyleSignBounds();
    for(int i=0;i<24;i++){CaptureSized($"ss_{look}_{effect}_{i:00}",1280,640,sb.center+Vector3.up*.3f,Mathf.Max(5,sb.size.x*.8f));yield return new WaitForSecondsRealtime(.08f);}
    Note($"STYLE sign {look}/{effect}: {style.QaReport()}");
   }
   style.EndPreview();
  }
  static string Classic()=>CheckoutMarketStyle.Classic;

  // The staff in each uniform: the shop opens (staff at work) and each worker is shot close (Logs/su_<look>_<worker>.jpg).
  IEnumerator StyleUniform(string request){
   foreach(var f in Directory.GetFiles("Logs","su_*.jpg"))File.Delete(f);
   yield return GoToStage(request.Contains("-")?request.Split('-')[1]:"supermercado");
   var style=CheckoutMarketStyle.Active;if(!style){Note("STYLE no CheckoutMarketStyle");yield break;}
   CheckoutBridge.Emit("{\"kind\":\"hud\",\"id\":\"qa-style-open\",\"action\":\"setMarketOpen\",\"args\":[true]}");
   yield return new WaitForSecondsRealtime(10);
   var world=GameObject.Find("Supermarket World");
   var staff=new System.Collections.Generic.List<Transform>();
   // the QA copy's shop stays closed (nobody works inside): the staff are shown where they stand for the shots
   var shown=new System.Collections.Generic.List<GameObject>();
   if(world)foreach(Transform w in world.transform)if(w.name.StartsWith("Worker_")&&!w.name.StartsWith("Worker_Delivery")){if(!w.gameObject.activeSelf){w.gameObject.SetActive(true);shown.Add(w.gameObject);}staff.Add(w);}
   var holder=GameObject.Find("Market Staff");if(holder)foreach(Transform w in holder.transform)if(w.gameObject.activeInHierarchy&&w.GetComponent<MarketDay.MarketCharacterAnimator>())staff.Add(w);
   Note("STYLE uniform staff: "+string.Join(", ",staff.Select(w=>w.name)));
   foreach(var id in new[]{"classico","a","b","c","d","e"}){
    var c=StyleLooks.First(l=>l.id==id).c;style.Preview(c);yield return new WaitForSecondsRealtime(1f);
    Note($"STYLE uniform {id}: {style.QaReport()}");
    foreach(var g in shown)if(g)g.SetActive(true);
    yield return new WaitForSecondsRealtime(.6f);
    int i=0;foreach(var w in staff.Take(8)){if(!w)continue;CaptureSized($"su_{id}_{i++}_{w.name.Replace(' ','_')}",700,900,w.position+Vector3.up*.9f,2.6f);}
   }
   style.EndPreview();foreach(var g in shown)if(g)g.SetActive(false);
  }

  IEnumerator StyleUi(string request){
   var parts=request.Split('-');string stage=parts.Length>1?parts[1]:"supermercado";int n=0;
   Note("STYLEUI "+CheckoutQaGameView.Set(2778,1284)+" handheld="+CheckoutScreen.Handheld);
   void Route(string r)=>CheckoutBridge.Emit("{\"kind\":\"route\",\"route\":\""+r+"\"}");
   yield return GoToStage(stage);
   yield return Dev("devAdjustCoins","[3000000]",()=>bridge.State.coins>=1000000);
   yield return Dev("devAdjustDiamonds","[500]",()=>bridge.State.diamonds>=300);
   string Wallet()=>$"coins {bridge.State.coins:0} diamonds {bridge.State.diamonds:0} owned [{string.Join(",",bridge.State.style?.owned??new string[0])}] floor={bridge.State.style?.floor} sign={bridge.State.style?.sign?.look}/{bridge.State.style?.sign?.effect}";
   IEnumerator Step(string name){yield return new WaitForSecondsRealtime(.8f);yield return Shot($"style_ui_{++n:00}_{name}");Note($"STYLEUI {name}: {CheckoutMarketStylePanel.QaStatus} · {Wallet()}");}
   IEnumerator Press(string which){var b=CheckoutMarketStylePanel.QaButton(which);if(!b){Note("STYLEUI missing button "+which);yield break;}Note($"STYLEUI press {which}: '{b.Data?.label}' enabled={b.Data?.enabled}");b.Clicked?.Invoke(b);for(float t=0;t<4&&CheckoutMarketStylePanel.QaBusy;t+=.2f)yield return new WaitForSecondsRealtime(.2f);yield return new WaitForSecondsRealtime(.8f);}
   Route("~loja:decoracao");yield return new WaitForSecondsRealtime(2f);yield return Shot($"style_ui_{++n:00}_loja_card");
   var entry=FindObjectsByType<CheckoutDesktopButton>(FindObjectsSortMode.None).FirstOrDefault(b=>b.isActiveAndEnabled&&b.Data!=null&&b.Data.route=="@style");
   Note("STYLEUI loja card button: "+(entry?entry.Data.label:"MISSING"));
   if(entry)entry.Clicked?.Invoke(entry);else{Route("");CheckoutMarketStylePanel.Show();}
   yield return new WaitForSecondsRealtime(1.5f);
   if(!CheckoutMarketStylePanel.Open){Note("STYLEUI the picker did not open");yield break;}
   yield return Step("open_floor");
   CheckoutMarketStylePanel.QaPick("floor","taco");yield return Step("floor_taco");
   CheckoutMarketStylePanel.QaPick("floor","xadrez");CheckoutMarketStylePanel.QaColour(0,"8A1C2B");yield return Step("floor_xadrez");
   CheckoutMarketStylePanel.QaTab(1);CheckoutMarketStylePanel.QaPick("wall","metro");CheckoutMarketStylePanel.QaColour(0,"1E8C7A");yield return Step("wall_metro");
   CheckoutMarketStylePanel.QaTab(2);CheckoutMarketStylePanel.QaPick("uniform","personalizado");CheckoutMarketStylePanel.QaColour(0,"5E4F8C");CheckoutMarketStylePanel.QaColour(1,"F2C230");yield return Step("uniform_custom");
   double coins0=bridge.State.coins;
   yield return Press("coins");yield return Step("bought_coins");
   Note($"STYLEUI coins paid {coins0-bridge.State.coins:0}");
   CheckoutMarketStylePanel.QaTab(3);yield return Step("sign_tab");
   CheckoutMarketStylePanel.QaPick("font","fina");CheckoutMarketStylePanel.QaPick("look","neon");CheckoutMarketStylePanel.QaPick("effect","pulsar");CheckoutMarketStylePanel.QaColour(0,"FF4FD8");yield return Step("sign_neon");
   CheckoutMarketStylePanel.QaPick("look","colorido");CheckoutMarketStylePanel.QaPalette("tropical");CheckoutMarketStylePanel.QaPick("effect","onda");CheckoutMarketStylePanel.QaSpeed(2);yield return Step("sign_colorido");
   double gems0=bridge.State.diamonds;
   yield return Press("diamonds");yield return Step("bought_diamonds");
   Note($"STYLEUI diamonds paid {gems0-bridge.State.diamonds:0}");
   // back to an owned floor: free
   CheckoutMarketStylePanel.QaTab(0);CheckoutMarketStylePanel.QaPick("floor","taco");yield return Step("owned_taco");
   CheckoutMarketStylePanel.QaPick("floor","xadrez");yield return Step("back_xadrez");
   yield return Press("cancel");yield return Step("closed");
  }
 }
}
