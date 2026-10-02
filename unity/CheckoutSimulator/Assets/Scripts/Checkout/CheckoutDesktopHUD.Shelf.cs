using System.Collections;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // The shelf window (page.layout == "shelf", data from desktop/pages/shelf-view.ts): the fixture drawn as it
 // stands in the shop -- crates on the sidewalk table, the styrofoam cooler, the drinks fridge, the freezer,
 // the bakery shelf, the gondola, the sector counter -- with its products sitting in it. Like the shelves of
 // Supermarket Simulator or the stands of Hay Day, the player works on the fixture itself:
 //  - picks a place to see the product up close (stock, price tag and what customers think of it, level);
 //  - drags a product to another place (the top row is at eye level and sells more);
 //  - puts a product in an empty place, swaps or removes it;
 //  - tidies the fixture up by tapping the mess of its own kind (wilted leaves, melted ice, frost, crumbs,
 //    smudges, crooked products): a messy fixture sells less (src/services/shelf-care.ts).
 // Art: Resources/CheckoutDesktop/Fixtures/<art>_back|_front (ArtSource/fixture_art.py), the products are
 // drawn between the two layers. Care sprites: Resources/CheckoutDesktop/Care.
 public partial class CheckoutDesktopHUD {
  public static bool ShelfOpen;

  GameObject shelfWin;RectTransform shelfRail,shelfArt,shelfSlotsLayer,shelfOverlay,shelfSpots,shelfDetail,shelfHeaderIcon;
  Image shelfHeader,shelfBack,shelfFront,shelfCareFill,shelfIcon;TextMeshProUGUI shelfTitle,shelfSubtitle,shelfSign,shelfCareLabel,shelfCareHint,shelfCareEffect,shelfNote,shelfCoins;
  GameObject shelfNoteBar;CheckoutDesktopButton shelfExpand,shelfCapacity;
  readonly List<CheckoutDesktopButton> shelfTabs=new List<CheckoutDesktopButton>();readonly List<GameObject> shelfTabBadges=new List<GameObject>();
  readonly List<ShelfSlotUi> shelfSlots=new List<ShelfSlotUi>();
  readonly List<Image> shelfSpotPool=new List<Image>();
  DesktopShelf shelfData;string shelfShown,shelfDetailKey;int shelfSelected=-1;bool shelfPicking;
  int shelfSpotsLeft;string shelfSpotsKey;

  // ------------------------------------------------------------------ build
  void BuildShelf(){
   var node=N.Node("Shelf window",root);shelfWin=node.gameObject;Stretch(node,Vector2.zero,Vector2.zero);
   var dim=shelfWin.AddComponent<Image>();dim.color=new Color(.10f,.07f,.04f,.58f);Clickable(shelfWin,()=>host.Route(""));
   var window=Stretch(N.Node("Window",node),new Vector2(64,118),new Vector2(-64,-18));
   var edge=window.gameObject.AddComponent<Image>();edge.sprite=K.Rounded(30);edge.type=Image.Type.Sliced;edge.color=K.C("8A5A2B");
   window.gameObject.AddComponent<Button>().transition=Selectable.Transition.None;
   var face=N.Image(window,"Face",K.Paper,28);Stretch(face.rectTransform,new Vector2(4,9),new Vector2(-4,-4));

   // Header: band in the fixture's colour, its picture, name and what it sells now.
   shelfHeader=N.Image(face.transform,"Header",K.C("8A5A2B"),26);var hr=shelfHeader.rectTransform;hr.anchorMin=new Vector2(0,1);hr.anchorMax=Vector2.one;hr.pivot=new Vector2(.5f,1);hr.offsetMin=new Vector2(0,-92);hr.offsetMax=Vector2.zero;
   var row=N.Row(shelfHeader.gameObject,14,new RectOffset(18,18,10,14));row.childAlignment=TextAnchor.MiddleLeft;
   var iconBack=N.Image(shelfHeader.transform,"IconBack",new Color(1,1,1,.92f),18);var ib=iconBack.gameObject.AddComponent<LayoutElement>();ib.preferredWidth=ib.preferredHeight=66;
   shelfIcon=N.Image(iconBack.transform,"Icon",Color.white,0);shelfIcon.preserveAspect=true;Stretch(shelfIcon.rectTransform,new Vector2(5,5),new Vector2(-5,-5));
   var titles=N.Node("Titles",shelfHeader.transform);N.Column(titles.gameObject,0);titles.gameObject.AddComponent<LayoutElement>().flexibleWidth=1;
   shelfTitle=N.Text(titles,"Title",K.Headline,32,Color.white);shelfTitle.textWrappingMode=TextWrappingModes.NoWrap;
   shelfSubtitle=N.Text(titles,"Subtitle",K.Body,16,new Color(1,1,1,.85f));shelfSubtitle.textWrappingMode=TextWrappingModes.NoWrap;shelfSubtitle.overflowMode=TextOverflowModes.Ellipsis;
   shelfCoins=Balance(shelfHeader.transform,"Icons/coin",null);
   var close=CheckoutDesktopButton.Create(shelfHeader.transform,54,22,14);close.SetWidth(58);close.Clicked=_=>host.Route("");
   close.Apply(new DesktopButton{label="X",variant="danger",enabled=true,route="",action="",args="[]",after="",ok="",fail="",badge=""});

   var body=Stretch(N.Node("Body",face.transform),Vector2.zero,new Vector2(0,-98));
   // Rail: the fixtures the player has.
   var rail=N.Image(body,"Rail",K.C("F3DFC0"),22);var rr=rail.rectTransform;rr.anchorMin=Vector2.zero;rr.anchorMax=new Vector2(0,1);rr.pivot=new Vector2(0,.5f);rr.offsetMin=new Vector2(12,12);rr.offsetMax=new Vector2(238,-4);
   var railScroll=Scroll(rail.transform,"Tabs",true,out shelfRail);Stretch((RectTransform)railScroll.transform,new Vector2(8,10),new Vector2(-8,-10));

   // Stage: the fixture on the shop wall.
   var stage=N.Node("Stage",body);stage.anchorMin=Vector2.zero;stage.anchorMax=new Vector2(0,1);stage.pivot=new Vector2(0,1);stage.offsetMin=new Vector2(250,12);stage.offsetMax=new Vector2(250+790,-4);
   var wall=N.Image(stage,"Wall",K.C("EFE2CC"),22);Stretch(wall.rectTransform,Vector2.zero,Vector2.zero);
   var tiles=N.Image(wall.transform,"Tiles",Color.white,0);tiles.sprite=K.Icon("Game/wall_backdrop");tiles.color=new Color(1,1,1,.55f);Stretch(tiles.rectTransform,new Vector2(6,190),new Vector2(-6,-6));
   shelfNoteBar=N.Image(stage,"Note",K.C("FFF1CF"),12).gameObject;var nr=(RectTransform)shelfNoteBar.transform;nr.anchorMin=new Vector2(0,1);nr.anchorMax=Vector2.one;nr.pivot=new Vector2(.5f,1);nr.offsetMin=new Vector2(10,-44);nr.offsetMax=new Vector2(-10,-8);
   shelfNote=N.Text(shelfNoteBar.transform,"Text",K.Body,14,K.Ink);shelfNote.alignment=TextAlignmentOptions.Center;Stretch(shelfNote.rectTransform,new Vector2(10,0),new Vector2(-10,0));
   // Art: 3:2, back layer, products, front layer, labels and the mess on top.
   shelfArt=N.Node("Art",stage);shelfArt.anchorMin=shelfArt.anchorMax=new Vector2(.5f,1);shelfArt.pivot=new Vector2(.5f,1);shelfArt.sizeDelta=new Vector2(744,496);shelfArt.anchoredPosition=new Vector2(0,-48);
   shelfBack=N.Image(shelfArt,"Back",Color.white,0);Stretch(shelfBack.rectTransform,Vector2.zero,Vector2.zero);
   shelfSlotsLayer=Stretch(N.Node("Products",shelfArt),Vector2.zero,Vector2.zero);
   shelfFront=N.Image(shelfArt,"Front",Color.white,0);Stretch(shelfFront.rectTransform,Vector2.zero,Vector2.zero);
   shelfSign=N.Text(shelfArt,"Sign",K.Headline,22,K.Ink);shelfSign.alignment=TextAlignmentOptions.Center;shelfSign.textWrappingMode=TextWrappingModes.NoWrap;
   var sr=shelfSign.rectTransform;sr.anchorMin=new Vector2(.3f,.855f);sr.anchorMax=new Vector2(.7f,.965f);sr.offsetMin=sr.offsetMax=Vector2.zero;
   shelfOverlay=Stretch(N.Node("Labels",shelfArt),Vector2.zero,Vector2.zero);
   shelfSpots=Stretch(N.Node("Mess",shelfArt),Vector2.zero,Vector2.zero);
   for(int i=0;i<7;i++)shelfSlots.Add(ShelfSlotUi.Create(this,i,shelfSlotsLayer,shelfOverlay));

   // Care strip under the fixture.
   var careBox=N.Image(stage,"Care",K.Cream,16);var cr=careBox.rectTransform;cr.anchorMin=Vector2.zero;cr.anchorMax=new Vector2(1,0);cr.pivot=new Vector2(.5f,0);cr.offsetMin=new Vector2(10,76);cr.offsetMax=new Vector2(-10,176);
   shelfCareLabel=N.Text(careBox.transform,"Label",K.Headline,19,K.Ink);var cl=shelfCareLabel.rectTransform;cl.anchorMin=new Vector2(0,1);cl.anchorMax=new Vector2(.5f,1);cl.offsetMin=new Vector2(16,-40);cl.offsetMax=new Vector2(0,-8);shelfCareLabel.textWrappingMode=TextWrappingModes.NoWrap;
   shelfCareEffect=N.Text(careBox.transform,"Effect",K.Label,15,K.Muted);shelfCareEffect.alignment=TextAlignmentOptions.Right;var ce=shelfCareEffect.rectTransform;ce.anchorMin=new Vector2(.5f,1);ce.anchorMax=Vector2.one;ce.offsetMin=new Vector2(0,-40);ce.offsetMax=new Vector2(-16,-8);shelfCareEffect.textWrappingMode=TextWrappingModes.NoWrap;
   var track=N.Image(careBox.transform,"Track",K.C("EADBC4"),7);var tr=track.rectTransform;tr.anchorMin=new Vector2(0,1);tr.anchorMax=Vector2.one;tr.offsetMin=new Vector2(16,-58);tr.offsetMax=new Vector2(-16,-44);
   shelfCareFill=N.Image(track.transform,"Fill",K.C("5DA637"),7);var fr=shelfCareFill.rectTransform;fr.anchorMin=Vector2.zero;fr.anchorMax=new Vector2(1,1);fr.offsetMin=fr.offsetMax=Vector2.zero;
   shelfCareHint=N.Text(careBox.transform,"Hint",K.Body,15,K.Muted);var ch=shelfCareHint.rectTransform;ch.anchorMin=Vector2.zero;ch.anchorMax=new Vector2(1,0);ch.offsetMin=new Vector2(16,8);ch.offsetMax=new Vector2(-16,38);
   // Upgrades of the fixture.
   var ups=N.Node("Upgrades",stage);ups.anchorMin=Vector2.zero;ups.anchorMax=new Vector2(1,0);ups.pivot=new Vector2(.5f,0);ups.offsetMin=new Vector2(10,10);ups.offsetMax=new Vector2(-10,66);
   var ur=N.Row(ups.gameObject,10);ur.childControlHeight=true;ur.childForceExpandHeight=true;ur.childForceExpandWidth=true;
   shelfExpand=CheckoutDesktopButton.Create(ups,52,16,14);shelfExpand.Clicked=Press;
   shelfCapacity=CheckoutDesktopButton.Create(ups,52,16,14);shelfCapacity.Clicked=Press;

   // Detail: the place picked (or the fixture when none is).
   var detail=N.Image(body,"Detail",K.Cream,22);var dr=detail.rectTransform;dr.anchorMin=Vector2.zero;dr.anchorMax=Vector2.one;dr.offsetMin=new Vector2(1052,12);dr.offsetMax=new Vector2(-12,-4);
   shelfDetail=Stretch(N.Node("Content",detail.transform),new Vector2(16,14),new Vector2(-16,-14));
   shelfWin.SetActive(false);
  }

  // ------------------------------------------------------------------ apply
  void ApplyShelf(DesktopView v){
   bool on=v.hasPage&&v.page!=null&&v.page.layout=="shelf"&&v.page.shelf!=null&&!string.IsNullOrEmpty(v.page.shelf.id);
   if(shelfWin.activeSelf!=on)shelfWin.SetActive(on);ShelfOpen=on;
   if(!on){shelfShown=null;return;}
   var p=v.page;var s=p.shelf;shelfData=s;
   if(s.id!=shelfShown){shelfShown=s.id;shelfSelected=FirstProduct(s);shelfPicking=false;shelfDetailKey=null;shelfSpotsKey=null;}
   shelfCoins.text=v.coins;
   var tint=K.C(string.IsNullOrEmpty(s.tint)?"8A5A2B":s.tint);shelfHeader.color=tint;
   shelfTitle.text=K.Clean(s.name);shelfSubtitle.text=K.Clean(s.accepts);shelfSign.text=K.Clean(s.name);
   var icon=K.Icon(p.icon);shelfIcon.sprite=icon;shelfIcon.enabled=icon;
   shelfBack.sprite=K.Icon(s.art+"_back");shelfFront.sprite=K.Icon(s.art+"_front");
   shelfBack.enabled=shelfBack.sprite;shelfFront.enabled=shelfFront.sprite;
   shelfNoteBar.SetActive(!string.IsNullOrEmpty(s.stallNote));shelfNote.text=K.Clean(s.stallNote);
   ApplyShelfTabs(p.tabs??new DesktopButton[0]);
   var slots=s.slots??new DesktopShelfSlot[0];
   for(int i=0;i<shelfSlots.Count;i++)shelfSlots[i].Apply(i<slots.Length?slots[i]:null,i==shelfSelected);
   // Care.
   int c=Mathf.Clamp(s.condition,0,100);
   shelfCareLabel.text=$"{s.careTitle}: {c}%";
   shelfCareFill.rectTransform.anchorMax=new Vector2(Mathf.Max(.02f,c/100f),1);
   shelfCareFill.color=c>=70?K.C("5DA637"):c>=40?K.C("E8B54A"):K.C("E15533");
   float factor=.8f+.25f*c/100f;int pct=Mathf.RoundToInt((factor-1)*100);
   shelfCareEffect.text=pct>=0?$"Vendas +{pct}%":$"Vendas {pct}%";shelfCareEffect.color=pct>=0?K.C("427A24"):K.C("C0401F");
   ApplyShelfSpots(s);
   shelfCareHint.text=c>=100?"Tudo em ordem: este móvel está vendendo o máximo.":$"{s.careVerb}: {s.careHint}";
   // Upgrades.
   shelfExpand.gameObject.SetActive(s.expandCost>0);
   if(s.expandCost>0)shelfExpand.Apply(Btn($"Mais um espaço · {Fmt(s.expandCost)}","expandShelfSlots",Args(s.id),"coin","Icons/coin",
    v.level>=s.expandLevel,$"Novo espaço na {s.name}!",v.level>=s.expandLevel?"Moedas insuficientes.":$"Disponível no nível {s.expandLevel}."));
   shelfCapacity.gameObject.SetActive(s.capacityCost>0);
   if(s.capacityCost>0)shelfCapacity.Apply(Btn($"Cabem {s.capacity} → {s.capacityNext} por espaço · {Fmt(s.capacityCost)}","upgradeShelfCapacity","[\""+s.id+"\",\"coins\"]","coin","Icons/coin",
    v.level>=s.capacityLevel,"Cada espaço agora cabe mais produtos!",v.level>=s.capacityLevel?"Moedas insuficientes.":$"Disponível no nível {s.capacityLevel}."));
   ApplyShelfDetail(v);
   // The build button hides behind the window, as with the shop.
   ShopOpen=true;
  }

  static int FirstProduct(DesktopShelf s){if(s.slots!=null)for(int i=0;i<s.slots.Length;i++)if(s.slots[i].state=="product")return i;return -1;}

  void ApplyShelfTabs(DesktopButton[] tabs){
   while(shelfTabs.Count<tabs.Length){
    var b=CheckoutDesktopButton.Create(shelfRail,66,16,16);b.Clicked=Press;shelfTabs.Add(b);
    var label=b.GetComponentInChildren<TextMeshProUGUI>(true);label.alignment=TextAlignmentOptions.Left;label.textWrappingMode=TextWrappingModes.Normal;
    var faceRow=b.transform.Find("Face").GetComponent<HorizontalLayoutGroup>();faceRow.childAlignment=TextAnchor.MiddleLeft;faceRow.padding=new RectOffset(8,10,2,2);faceRow.spacing=8;
    b.transform.Find("Face/Icon").GetComponent<LayoutElement>().preferredWidth=48;b.transform.Find("Face/Icon").GetComponent<LayoutElement>().preferredHeight=48;
    var pill=N.Image(b.transform,"Badge",K.C("E15533"),12);var pr=pill.rectTransform;pr.anchorMin=pr.anchorMax=new Vector2(1,1);pr.pivot=new Vector2(1,1);pr.anchoredPosition=new Vector2(2,2);pr.sizeDelta=new Vector2(26,26);
    var t=N.Text(pill.transform,"Text",K.Number,15,Color.white);t.alignment=TextAlignmentOptions.Center;Stretch(t.rectTransform,Vector2.zero,Vector2.zero);
    shelfTabBadges.Add(pill.gameObject);
   }
   for(int i=0;i<shelfTabs.Count;i++){
    bool show=i<tabs.Length;shelfTabs[i].gameObject.SetActive(show);if(!show)continue;
    var data=tabs[i];shelfTabs[i].Apply(data);
    shelfTabs[i].transform.Find("Face").GetComponent<Image>().color=data.active?ShopGold:K.C("FFF7EC");
    shelfTabs[i].GetComponent<Image>().color=data.active?K.C("C58A1E"):K.C("D9BE93");
    bool badge=!string.IsNullOrEmpty(data.badge);shelfTabBadges[i].SetActive(badge);if(badge)shelfTabBadges[i].GetComponentInChildren<TextMeshProUGUI>().text=data.badge;
   }
  }

  // ------------------------------------------------------------------ care game
  static readonly float[,] SpotSpots={{.12f,.66f},{.55f,.70f},{.80f,.58f},{.32f,.30f},{.68f,.26f},{.22f,.52f},{.47f,.48f},{.86f,.34f},{.40f,.18f},{.62f,.62f}};
  void ApplyShelfSpots(DesktopShelf s){
   int want=s.condition>=100?0:Mathf.Clamp(Mathf.CeilToInt((100-s.condition)/10f),1,10);
   string key=s.id+"|"+want;
   if(key!=shelfSpotsKey){
    // A new mess (or a new fixture): lay it out again.
    shelfSpotsKey=key;shelfSpotsLeft=want;
    while(shelfSpotPool.Count<10){
     var img=N.Image(shelfSpots,"Spot",Color.white,0);img.preserveAspect=true;img.raycastTarget=true;
     var index=shelfSpotPool.Count;var trigger=img.gameObject.AddComponent<Button>();trigger.transition=Selectable.Transition.None;trigger.onClick.AddListener(()=>CleanSpot(index));
     shelfSpotPool.Add(img);
    }
    var sprite=K.Icon("Care/"+SpotSprite(s.careSpot));
    for(int i=0;i<shelfSpotPool.Count;i++){
     var img=shelfSpotPool[i];bool on=i<want;img.gameObject.SetActive(on);if(!on)continue;
     img.transform.localScale=Vector3.one;img.color=Color.white;
     // Crooked products on the gondola: the products of the fixture, tilted.
     if(s.careSpot=="mess"){var products=new List<DesktopShelfSlot>();foreach(var slot in s.slots)if(slot.state=="product")products.Add(slot);
      img.sprite=products.Count>0?K.Icon(products[i%products.Count].icon):sprite;img.transform.localRotation=Quaternion.Euler(0,0,i%2==0?38:-34);}
     else{img.sprite=sprite;img.transform.localRotation=Quaternion.Euler(0,0,(i*47)%360);}
     var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(SpotSpots[i,0],SpotSpots[i,1]);r.sizeDelta=s.careSpot=="mess"?new Vector2(64,64):new Vector2(124,124);r.anchoredPosition=Vector2.zero;
    }
   }
  }
  static string SpotSprite(string spot)=>spot=="wilted"||spot=="frost"||spot=="crumbs"||spot=="smudge"||spot=="melt"?spot:"smudge";
  void CleanSpot(int index){
   if(index>=shelfSpotPool.Count||!shelfSpotPool[index].gameObject.activeSelf||shelfData==null)return;
   StartCoroutine(Vanish(shelfSpotPool[index]));
   shelfSpotsLeft--;
   if(shelfSpotsLeft<=0)Run("tendShelf",Args(shelfData.id),$"{shelfData.name} arrumada! Vende mais agora.","Não deu para arrumar agora.");
  }
  IEnumerator Vanish(Image img){
   var rect=img.rectTransform;float t=0;var start=rect.localScale;
   // A sparkle where the mess was.
   var spark=N.Image(shelfSpots,"Sparkle",Color.white,0);spark.sprite=K.Icon("Game/sparkle");var sr=spark.rectTransform;sr.anchorMin=sr.anchorMax=rect.anchorMin;sr.sizeDelta=new Vector2(70,70);
   while(t<.28f){t+=Time.unscaledDeltaTime;float k=t/.28f;rect.localScale=start*(1-k*.6f);img.color=new Color(1,1,1,1-k);spark.color=new Color(1,1,1,1-k);sr.localScale=Vector3.one*(1+k);yield return null;}
   img.gameObject.SetActive(false);Destroy(spark.gameObject);
  }

  // ------------------------------------------------------------------ slot events
  public void ShelfSelect(int index){
   if(shelfData==null||shelfData.slots==null||index>=shelfData.slots.Length)return;
   var slot=shelfData.slots[index];if(slot.state=="hidden")return;
   shelfSelected=index;shelfPicking=slot.state=="empty";shelfDetailKey=null;
   for(int i=0;i<shelfSlots.Count;i++)shelfSlots[i].Select(i==index);
   if(view!=null)ApplyShelfDetail(view);
  }
  public void ShelfDrop(int from,int to){
   if(shelfData==null||from==to)return;var a=shelfData.slots[from];var b=shelfData.slots[to];
   if(a.state!="product"||(b.state!="product"&&b.state!="empty"))return;
   shelfSelected=to;shelfDetailKey=null;
   Run("swapShelfSlots","[\""+a.slotId+"\",\""+b.slotId+"\"]",to<4?$"{a.name} agora está {(shelfData.rowTop??"").Split('·')[0].Trim().ToLowerInvariant()}.":$"{a.name} mudou de lugar.","Não deu para trocar de lugar.");
  }

  // ------------------------------------------------------------------ detail panel
  void ApplyShelfDetail(DesktopView v){
   var s=shelfData;if(s==null)return;
   var slot=shelfSelected>=0&&s.slots!=null&&shelfSelected<s.slots.Length?s.slots[shelfSelected]:null;
   if(slot!=null&&slot.state=="hidden"){slot=null;shelfSelected=-1;}
   if(slot!=null&&slot.state=="empty")shelfPicking=true;
   string key=s.id+"|"+shelfSelected+"|"+shelfPicking+"|"+v.coins+"|"+v.level+"|"+(slot==null?"":JsonUtility.ToJson(slot))+"|"+(shelfPicking?(s.picks?.Length??0).ToString():"");
   if(key==shelfDetailKey)return;shelfDetailKey=key;
   for(int i=shelfDetail.childCount-1;i>=0;i--)Destroy(shelfDetail.GetChild(i).gameObject);
   if(slot==null)DetailOverview(s);
   else if(slot.state=="locked")DetailLocked(s,slot,v);
   else if(shelfPicking)DetailPicker(s,slot);
   else DetailProduct(s,slot,v);
  }

  RectTransform Column(RectTransform parent,int spacing){var c=N.Node("Column",parent);Stretch(c,Vector2.zero,Vector2.zero);var col=N.Column(c.gameObject,spacing);col.childControlHeight=true;col.childForceExpandHeight=false;col.childAlignment=TextAnchor.UpperLeft;return c;}
  TextMeshProUGUI Line(Transform parent,string text,TMP_FontAsset font,float size,Color color,float height=-1){
   var t=N.Text(parent,"Line",font,size,color);t.text=K.Clean(text);if(height>0)t.gameObject.AddComponent<LayoutElement>().preferredHeight=height;return t;
  }
  CheckoutDesktopButton DetailButton(Transform parent,DesktopButton data,float height=50){var b=CheckoutDesktopButton.Create(parent,height,16,14);b.Clicked=Press;b.Apply(data);b.GetComponent<LayoutElement>().flexibleHeight=0;return b;}
  RectTransform DetailRow(Transform parent,float height){var r=N.Node("Row",parent);var h=N.Row(r.gameObject,8);h.childControlHeight=true;h.childForceExpandHeight=true;h.childForceExpandWidth=true;
   var le=r.gameObject.AddComponent<LayoutElement>();le.preferredHeight=le.minHeight=height;le.flexibleHeight=0;return r;}

  void DetailOverview(DesktopShelf s){
   var col=Column(shelfDetail,8);
   Line(col,s.name,K.Headline,24,K.Ink);
   Line(col,s.accepts,K.Body,15,K.Muted);
   Line(col," ",K.Body,6,K.Muted);
   Line(col,"Como cuidar deste móvel",K.Label,16,K.Ink);
   Line(col,"• Toque num lugar para ver o produto de perto: estoque, preço e nível.",K.Body,15,K.Ink);
   Line(col,"• Arraste um produto para outro lugar. "+s.rowTop+"; "+s.rowBottom.ToLowerInvariant()+".",K.Body,15,K.Ink);
   Line(col,"• "+s.careVerb+": "+s.careHint,K.Body,15,K.Ink);
   Line(col,"• Um preço justo vende mais; muito caro afasta os clientes.",K.Body,15,K.Ink);
  }

  void DetailLocked(DesktopShelf s,DesktopShelfSlot slot,DesktopView v){
   var col=Column(shelfDetail,10);
   Line(col,"Espaço fechado",K.Headline,24,K.Ink);
   Line(col,$"Abra mais um lugar na {s.name} para vender mais um produto.",K.Body,15,K.Muted);
   var lockRow=N.Node("Lock",col);lockRow.gameObject.AddComponent<LayoutElement>().preferredHeight=120;
   var lockImg=N.Image(lockRow,"Icon",Color.white,0);lockImg.sprite=K.Icon("Icons/lock");lockImg.preserveAspect=true;Stretch(lockImg.rectTransform,new Vector2(0,10),new Vector2(0,-10));
   bool level=v.level>=slot.unlockLevel;
   DetailButton(col,Btn($"Abrir espaço · {Fmt(slot.unlockCost)}","expandShelfSlots",Args(s.id),"coin","Icons/coin",level,"Novo espaço aberto!",level?"Moedas insuficientes.":$"Disponível no nível {slot.unlockLevel}."),56);
   if(!level)Line(col,$"Precisa do nível {slot.unlockLevel}.",K.Label,15,K.C("C0401F"));
  }

  void DetailPicker(DesktopShelf s,DesktopShelfSlot slot){
   var col=Column(shelfDetail,8);
   Line(col,slot.state=="product"?$"Trocar {slot.name} por":"Colocar um produto",K.Headline,22,K.Ink,30);
   Line(col,slot.row=="top"?s.rowTop:s.rowBottom,K.Label,14,slot.row=="top"?K.C("427A24"):K.Muted,20);
   var picks=s.picks??new DesktopShelfPick[0];
   if(picks.Length==0){
    Line(col,"Nenhum outro produto deste tipo liberado agora. Novos produtos chegam com as expansões e os níveis.",K.Body,15,K.Muted);
   }else{
    var scroll=Scroll(col,"Picks",true,out var content);scroll.gameObject.AddComponent<LayoutElement>().flexibleHeight=1;
    DestroyImmediate(content.GetComponent<VerticalLayoutGroup>());
    var grid=content.gameObject.AddComponent<GridLayoutGroup>();grid.cellSize=new Vector2(132,160);grid.spacing=new Vector2(10,10);grid.padding=new RectOffset(2,8,4,8);
    grid.constraint=GridLayoutGroup.Constraint.FixedColumnCount;grid.constraintCount=2;
    foreach(var pick in picks){
     var tile=N.Image(content,"Pick",K.C("F3DFC0"),14);tile.raycastTarget=true;
     var img=N.Image(tile.transform,"Icon",Color.white,0);img.sprite=K.Icon(pick.icon);img.preserveAspect=true;var ir=img.rectTransform;ir.anchorMin=new Vector2(.5f,1);ir.anchorMax=new Vector2(.5f,1);ir.pivot=new Vector2(.5f,1);ir.sizeDelta=new Vector2(64,64);ir.anchoredPosition=new Vector2(0,-6);
     var name=N.Text(tile.transform,"Name",K.Label,15,K.Ink);name.text=K.Clean(pick.name);name.alignment=TextAlignmentOptions.Center;name.textWrappingMode=TextWrappingModes.NoWrap;name.overflowMode=TextOverflowModes.Ellipsis;var nr=name.rectTransform;nr.anchorMin=new Vector2(0,0);nr.anchorMax=new Vector2(1,0);nr.offsetMin=new Vector2(4,58);nr.offsetMax=new Vector2(-4,80);
     var info=N.Text(tile.transform,"Info",K.Body,12,K.Muted);info.text=$"Depósito: {pick.reserve}\nVenda {pick.price}";info.alignment=TextAlignmentOptions.Center;var inf=info.rectTransform;inf.anchorMin=Vector2.zero;inf.anchorMax=new Vector2(1,0);inf.offsetMin=new Vector2(4,22);inf.offsetMax=new Vector2(-4,58);
     var profit=N.Text(tile.transform,"Profit",K.Label,12,K.C("427A24"));profit.text=$"Lucro {pick.profit}/un.";profit.alignment=TextAlignmentOptions.Center;profit.textWrappingMode=TextWrappingModes.NoWrap;var pf=profit.rectTransform;pf.anchorMin=Vector2.zero;pf.anchorMax=new Vector2(1,0);pf.offsetMin=new Vector2(4,6);pf.offsetMax=new Vector2(-4,22);
     var id=pick.productId;var pickName=pick.name;var slotId=slot.slotId;
     Clickable(tile.gameObject,()=>{shelfPicking=false;shelfDetailKey=null;Run("assignProductToShelf","[\""+slotId+"\","+id+",true]",$"{pickName} na prateleira. Reponha para vender.","Não deu para colocar este produto.");});
    }
   }
   if(slot.state=="product")DetailButton(col,new DesktopButton{label="Cancelar",variant="secondary",enabled=true,action="",args="[]",route="",after="",ok="",fail="",badge="",icon=""},46).Clicked=_=>{shelfPicking=false;shelfDetailKey=null;ApplyShelfDetail(view);};
  }

  void DetailProduct(DesktopShelf s,DesktopShelfSlot slot,DesktopView v){
   var col=Column(shelfDetail,8);
   // Product header.
   var head=N.Node("Head",col);var hl=N.Row(head.gameObject,12);hl.childAlignment=TextAnchor.MiddleLeft;head.gameObject.AddComponent<LayoutElement>().preferredHeight=86;
   var art=N.Image(head,"Art",K.C("F7E6C8"),18);var al=art.gameObject.AddComponent<LayoutElement>();al.preferredWidth=al.preferredHeight=84;
   var icon=N.Image(art.transform,"Icon",Color.white,0);icon.sprite=K.Icon(slot.icon);icon.preserveAspect=true;Stretch(icon.rectTransform,new Vector2(6,6),new Vector2(-6,-6));
   var texts=N.Node("Texts",head);N.Column(texts.gameObject,0);texts.gameObject.AddComponent<LayoutElement>().flexibleWidth=1;
   var title=Line(texts,slot.name,K.Headline,24,K.Ink);title.textWrappingMode=TextWrappingModes.NoWrap;title.overflowMode=TextOverflowModes.Ellipsis;
   Line(texts,slot.row=="top"?s.rowTop:s.rowBottom,K.Label,14,slot.row=="top"?K.C("427A24"):K.C("B26A2E"));
   Line(texts,slot.level>0?$"Nível {slot.level}/{slot.maxLevel} · +{Mathf.RoundToInt((Mathf.Pow(1.1f,slot.level)-1)*100)}% de lucro":$"Nível 0/{slot.maxLevel}",K.Body,14,K.Muted);

   // Stock.
   Line(col,"ESTOQUE",K.Label,13,K.Muted,18).characterSpacing=3;
   var bar=N.Image(col,"Stock",K.C("EADBC4"),8);bar.gameObject.AddComponent<LayoutElement>().preferredHeight=18;
   var fill=N.Image(bar.transform,"Fill",slot.stock==0?K.C("E15533"):slot.stock*3<slot.capacity?K.C("E8B54A"):K.C("5DA637"),8);var fr=fill.rectTransform;fr.anchorMin=Vector2.zero;fr.anchorMax=new Vector2(Mathf.Max(.03f,(float)slot.stock/Mathf.Max(1,slot.capacity)),1);fr.offsetMin=fr.offsetMax=Vector2.zero;
   Line(col,slot.stock==0?$"Esgotado na prateleira · {slot.reserve} no depósito":$"{slot.stock} de {slot.capacity} na prateleira · {slot.reserve} no depósito",K.Body,15,slot.stock==0?K.C("C0401F"):K.Ink);
   var stockRow=DetailRow(col,50);
   if(slot.restockAmount>0)DetailButton(stockRow,Btn($"Repor +{slot.restockAmount}","restockShelf","[{\"shelfId\":\""+slot.slotId+"\",\"productId\":"+slot.productId+",\"amount\":"+slot.restockAmount+"}]","success","Icons/basket",true,$"{slot.name} reposto!","Não deu para repor."));
   else if(!string.IsNullOrEmpty(slot.incoming))DetailButton(stockRow,new DesktopButton{label=slot.incoming,variant="secondary",enabled=false,icon="Icons/delivery-truck",action="",args="[]",route="",after="",ok="",fail="",badge=""});
   else if(slot.reserve==0)DetailButton(stockRow,new DesktopButton{label="Pedir ao fornecedor",variant="coin",enabled=true,icon="Icons/delivery-truck",action="",args="[]",route="shelforder:"+slot.productId+":1",after="",ok="",fail="",badge=""});
   else DetailButton(stockRow,new DesktopButton{label="Prateleira cheia",variant="secondary",enabled=false,icon="",action="",args="[]",route="",after="",ok="",fail="",badge=""});

   // Price tag.
   Line(col,"PREÇO NA ETIQUETA",K.Label,13,K.Muted,18).characterSpacing=3;
   var priceRow=N.Node("Price",col);priceRow.gameObject.AddComponent<LayoutElement>().preferredHeight=64;var prl=N.Row(priceRow.gameObject,8);prl.childAlignment=TextAnchor.MiddleLeft;prl.childControlHeight=true;prl.childForceExpandHeight=false;
   var minus=DetailButton(priceRow,Btn("−","setShelfPrice","[\""+slot.slotId+"\","+(slot.price-1)+"]","secondary","",slot.price>slot.minPrice,"",$"O mínimo é {slot.minPrice}."),52);minus.SetWidth(56);
   var tag=N.Image(priceRow,"Tag",K.C("F2B03D"),12);var tl=tag.gameObject.AddComponent<LayoutElement>();tl.preferredWidth=128;tl.preferredHeight=58;
   var coin=N.Image(tag.transform,"Coin",Color.white,0);coin.sprite=K.Icon("Icons/coin");coin.preserveAspect=true;var cr=coin.rectTransform;cr.anchorMin=new Vector2(0,.5f);cr.anchorMax=new Vector2(0,.5f);cr.pivot=new Vector2(0,.5f);cr.sizeDelta=new Vector2(30,30);cr.anchoredPosition=new Vector2(10,0);
   var price=N.Text(tag.transform,"Value",K.Number,30,K.Ink);price.text=slot.price.ToString();price.alignment=TextAlignmentOptions.Center;price.textWrappingMode=TextWrappingModes.NoWrap;price.enableAutoSizing=true;price.fontSizeMin=16;price.fontSizeMax=30;Stretch(price.rectTransform,new Vector2(36,0),new Vector2(-6,0));
   var plus=DetailButton(priceRow,Btn("+","setShelfPrice","[\""+slot.slotId+"\","+(slot.price+1)+"]","secondary","",slot.price<slot.maxPrice,"",$"O máximo é {slot.maxPrice}."),52);plus.SetWidth(56);
   var mood=N.Image(priceRow,"Mood",K.Tone(slot.moodTone).edge,12);var ml=mood.gameObject.AddComponent<LayoutElement>();ml.preferredWidth=118;ml.preferredHeight=40;
   var moodText=N.Text(mood.transform,"Text",K.Label,16,Color.white);moodText.text=slot.mood;moodText.alignment=TextAlignmentOptions.Center;Stretch(moodText.rectTransform,Vector2.zero,Vector2.zero);
   int profit=slot.price-slot.cost;
   Line(col,$"Lucro por unidade: {profit} · Sugerido: {slot.suggested} (de {slot.minPrice} a {slot.maxPrice})",K.Body,14,profit>0?K.Ink:K.C("C0401F"));
   if(slot.price!=slot.suggested)DetailButton(col,Btn($"Voltar ao preço sugerido ({slot.suggested})","setShelfPrice","[\""+slot.slotId+"\","+slot.suggested+"]","secondary","Icons/price-tag",true,"Preço ajustado.",""),44);

   // Level and the place.
   if(slot.upgradeCost>0)DetailButton(col,Btn($"Subir de nível (+10% de lucro) · {Fmt(slot.upgradeCost)}","upgradeProduct","["+slot.productId+"]","coin","Icons/coin",true,$"{slot.name} subiu de nível: +10% de lucro!","Moedas insuficientes."),48);
   var actions=DetailRow(col,48);
   var swap=DetailButton(actions,new DesktopButton{label="Trocar",variant="primary",enabled=true,icon="",action="",args="[]",route="",after="",ok="",fail="",badge=""});
   swap.Clicked=_=>{shelfPicking=true;shelfDetailKey=null;ApplyShelfDetail(view);};
   DetailButton(actions,Btn("Tirar","clearShelf","[\""+slot.slotId+"\"]","danger","",true,$"{slot.name} voltou para o depósito.","Libere espaço no depósito antes de tirar."));
   Line(col,"Dica: arraste o produto para outro lugar do móvel.",K.Body,13,K.Muted);
  }

  // ------------------------------------------------------------------ helpers
  static string Fmt(int value)=>value.ToString("N0",System.Globalization.CultureInfo.GetCultureInfo("pt-BR"));
  static string Args(string text)=>"[\""+text+"\"]";
  static DesktopButton Btn(string label,string action,string args,string variant,string icon,bool enabled,string ok,string fail)=>
   new DesktopButton{label=label,action=action,args=args,variant=variant,icon=icon,enabled=enabled,ok=ok,fail=fail,route="",after="",badge=""};
  void Run(string action,string args,string ok,string fail){
   pending[host.Action(action,args,"")]=new DesktopButton{label="",action=action,args=args,variant="primary",enabled=true,ok=ok,fail=fail,route="",after="",badge="",icon=""};
  }
 }

 // One place of the fixture: the products piled in it (between the back and the front of the art) and, on top,
 // its price tag, its stock and the hit area to pick it or drag it.
 public class ShelfSlotUi:MonoBehaviour,IPointerClickHandler,IBeginDragHandler,IDragHandler,IEndDragHandler,IDropHandler {
  CheckoutDesktopHUD hud;int index;RectTransform pile,labels;Image glow,emptyMark,lockBack;TextMeshProUGUI emptyText,lockText,stockText,levelText;
  GameObject tag,stockChip,levelChip,empty,locked;TextMeshProUGUI tagText;Image tagBack;
  readonly List<Image> icons=new List<Image>();DesktopShelfSlot data;
  static RectTransform dragGhost;static int dragFrom=-1;

  public static ShelfSlotUi Create(CheckoutDesktopHUD hud,int index,RectTransform productsLayer,RectTransform labelsLayer){
   float x0=CheckoutDesktopHUDShelfMath.X0(index),x1=CheckoutDesktopHUDShelfMath.X1(index),y0=CheckoutDesktopHUDShelfMath.Y0(index),y1=CheckoutDesktopHUDShelfMath.Y1(index);
   // Products layer: glow + pile.
   var pile=N.Node("Slot"+index,productsLayer);pile.anchorMin=new Vector2(x0,y0);pile.anchorMax=new Vector2(x1,y1);pile.offsetMin=pile.offsetMax=Vector2.zero;
   var glow=N.Image(pile,"Glow",new Color(1f,.82f,.35f,.0f),16);Stretch(glow.rectTransform,new Vector2(-6,-4),new Vector2(6,6));
   // Labels layer: hit area, tag, chips.
   var hit=N.Node("Hit"+index,labelsLayer);hit.anchorMin=new Vector2(x0,y0);hit.anchorMax=new Vector2(x1,y1);hit.offsetMin=hit.offsetMax=Vector2.zero;
   var area=hit.gameObject.AddComponent<Image>();area.color=new Color(0,0,0,0);area.raycastTarget=true;
   var ui=hit.gameObject.AddComponent<ShelfSlotUi>();ui.hud=hud;ui.index=index;ui.pile=pile;ui.labels=hit;ui.glow=glow;
   // Empty place: a dashed "+" to put something in.
   ui.empty=N.Node("Empty",hit).gameObject;Stretch((RectTransform)ui.empty.transform,new Vector2(10,14),new Vector2(-10,-8));
   ui.emptyMark=N.Image(ui.empty.transform,"Mark",new Color(1,1,1,.55f),18);Stretch(ui.emptyMark.rectTransform,Vector2.zero,Vector2.zero);
   ui.emptyText=N.Text(ui.empty.transform,"Text",K.Label,16,K.Muted);ui.emptyText.text="+\nColocar";ui.emptyText.alignment=TextAlignmentOptions.Center;Stretch(ui.emptyText.rectTransform,Vector2.zero,Vector2.zero);
   // Locked place: the next one to open.
   ui.locked=N.Node("Locked",hit).gameObject;Stretch((RectTransform)ui.locked.transform,new Vector2(10,14),new Vector2(-10,-8));
   ui.lockBack=N.Image(ui.locked.transform,"Back",new Color(.18f,.14f,.10f,.55f),18);Stretch(ui.lockBack.rectTransform,Vector2.zero,Vector2.zero);
   var lockIcon=N.Image(ui.locked.transform,"Lock",Color.white,0);lockIcon.sprite=K.Icon("Icons/lock");lockIcon.preserveAspect=true;var lr=lockIcon.rectTransform;lr.anchorMin=new Vector2(.5f,.45f);lr.anchorMax=new Vector2(.5f,.45f);lr.sizeDelta=new Vector2(44,44);
   ui.lockText=N.Text(ui.locked.transform,"Text",K.Label,14,Color.white);ui.lockText.alignment=TextAlignmentOptions.Center;var lt=ui.lockText.rectTransform;lt.anchorMin=Vector2.zero;lt.anchorMax=new Vector2(1,.3f);lt.offsetMin=lt.offsetMax=Vector2.zero;
   // Price tag under the place.
   ui.tagBack=N.Image(hit,"Tag",K.C("FFE08A"),8);ui.tag=ui.tagBack.gameObject;var tr=ui.tagBack.rectTransform;tr.anchorMin=tr.anchorMax=new Vector2(.5f,0);tr.pivot=new Vector2(.5f,1);tr.sizeDelta=new Vector2(74,28);tr.anchoredPosition=new Vector2(0,2);
   ui.tagText=N.Text(ui.tagBack.transform,"Price",K.Number,18,K.Ink);ui.tagText.alignment=TextAlignmentOptions.Center;ui.tagText.textWrappingMode=TextWrappingModes.NoWrap;ui.tagText.enableAutoSizing=true;ui.tagText.fontSizeMin=11;ui.tagText.fontSizeMax=18;Stretch(ui.tagText.rectTransform,Vector2.zero,Vector2.zero);
   // Stock and level chips.
   var stock=N.Image(hit,"Stock",new Color(.17f,.13f,.09f,.82f),10);ui.stockChip=stock.gameObject;var sr=stock.rectTransform;sr.anchorMin=sr.anchorMax=new Vector2(1,1);sr.pivot=new Vector2(1,1);sr.sizeDelta=new Vector2(54,24);sr.anchoredPosition=new Vector2(4,6);
   ui.stockText=N.Text(stock.transform,"Text",K.Number,14,Color.white);ui.stockText.alignment=TextAlignmentOptions.Center;Stretch(ui.stockText.rectTransform,Vector2.zero,Vector2.zero);
   var level=N.Image(hit,"Level",K.C("8B5C9E"),10);ui.levelChip=level.gameObject;var lv=level.rectTransform;lv.anchorMin=lv.anchorMax=new Vector2(0,1);lv.pivot=new Vector2(0,1);lv.sizeDelta=new Vector2(46,24);lv.anchoredPosition=new Vector2(-4,6);
   ui.levelText=N.Text(level.transform,"Text",K.Number,13,Color.white);ui.levelText.alignment=TextAlignmentOptions.Center;Stretch(ui.levelText.rectTransform,Vector2.zero,Vector2.zero);
   return ui;
  }
  static RectTransform Stretch(RectTransform r,Vector2 min,Vector2 max){r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=min;r.offsetMax=max;return r;}

  public void Apply(DesktopShelfSlot slot,bool selected){
   data=slot;bool hidden=slot==null||slot.state=="hidden";
   gameObject.SetActive(!hidden);pile.gameObject.SetActive(!hidden);if(hidden)return;
   bool product=slot.state=="product";
   empty.SetActive(slot.state=="empty");locked.SetActive(slot.state=="locked");
   if(slot.state=="locked")lockText.text="Abrir · "+slot.unlockCost.ToString("N0",System.Globalization.CultureInfo.GetCultureInfo("pt-BR"));
   tag.SetActive(product);stockChip.SetActive(product);levelChip.SetActive(product&&slot.level>0);
   if(product){
    tagText.text=slot.price.ToString();
    // The tag is tinted by what customers think of the price.
    tagBack.color=slot.moodTone=="success"?K.C("B9E39B"):slot.moodTone=="warning"?K.C("FFC98A"):slot.moodTone=="danger"?K.C("F7A08C"):K.C("FFE08A");
    stockText.text=slot.stock==0?"0!":$"{slot.stock}/{slot.capacity}";stockChip.GetComponent<Image>().color=slot.stock==0?K.C("E15533"):new Color(.17f,.13f,.09f,.82f);
    levelText.text="Nv"+slot.level;
   }
   // The pile: one icon per unit on the shelf (up to 12), back row higher, a little crooked.
   int count=product?Mathf.Min(slot.stock,12):0;
   var sprite=product?K.Icon(slot.icon):null;
   while(icons.Count<count){var img=N.Image(pile,"Unit",Color.white,0);img.preserveAspect=true;icons.Add(img);}
   var size=pile.rect.size;if(size.x<1)size=new Vector2(140,140);
   float unit=Mathf.Min(size.x*.5f,size.y*.72f);
   // Rows of up to 4, centred; the front row (row 0) is drawn last, the rows behind a bit higher and darker.
   for(int i=0;i<icons.Count;i++){
    bool on=i<count;icons[i].gameObject.SetActive(on);if(!on)continue;
    int place=count-1-i;int row=place/4,col=place%4;int inRow=Mathf.Min(4,count-row*4);
    float spacing=size.x*.2f;float x=size.x*.5f+(col-(inRow-1)*.5f)*spacing+(row%2==1?size.x*.06f:0);
    float y=size.y*(.06f+.15f*row);
    var r=icons[i].rectTransform;r.anchorMin=r.anchorMax=Vector2.zero;r.pivot=new Vector2(.5f,0);r.sizeDelta=new Vector2(unit,unit);
    r.anchoredPosition=new Vector2(x,y);r.localRotation=Quaternion.Euler(0,0,((i*37)%11)-5);
    icons[i].sprite=sprite;float shade=1-.1f*row;icons[i].color=new Color(shade,shade,shade,1);
    icons[i].transform.SetSiblingIndex(1+i);
   }
   Select(selected);
  }
  public void Select(bool on){if(glow)glow.color=new Color(1f,.82f,.35f,on?.55f:0);}

  public void OnPointerClick(PointerEventData e){if(e.dragging)return;hud.ShelfSelect(index);}
  public void OnBeginDrag(PointerEventData e){
   if(data==null||data.state!="product")return;
   dragFrom=index;var canvas=GetComponentInParent<Canvas>().rootCanvas;
   var ghost=N.Image(canvas.transform,"Drag",Color.white,0);ghost.sprite=K.Icon(data.icon);ghost.preserveAspect=true;ghost.raycastTarget=false;
   dragGhost=ghost.rectTransform;dragGhost.sizeDelta=new Vector2(96,96);Move(e);
  }
  public void OnDrag(PointerEventData e){if(dragGhost)Move(e);}
  void Move(PointerEventData e){var canvas=(RectTransform)dragGhost.parent;RectTransformUtility.ScreenPointToLocalPointInRectangle(canvas,e.position,null,out var p);dragGhost.anchorMin=dragGhost.anchorMax=new Vector2(.5f,.5f);dragGhost.anchoredPosition=p;}
  public void OnEndDrag(PointerEventData e){if(dragGhost)Destroy(dragGhost.gameObject);dragGhost=null;dragFrom=-1;}
  public void OnDrop(PointerEventData e){if(dragFrom>=0&&dragFrom!=index)hud.ShelfDrop(dragFrom,index);}
 }

 // Product places on the art (normalised, origin bottom-left): keep in sync with ArtSource/fixture_art.py.
 static class CheckoutDesktopHUDShelfMath {
  static readonly float[] X={.17f,.39f,.61f,.83f,.28f,.50f,.72f};
  const float W=.19f;
  public static float X0(int i)=>X[i]-W/2;public static float X1(int i)=>X[i]+W/2;
  public static float Y0(int i)=>i<4?.50f:.14f;public static float Y1(int i)=>i<4?.78f:.42f;
 }
}
