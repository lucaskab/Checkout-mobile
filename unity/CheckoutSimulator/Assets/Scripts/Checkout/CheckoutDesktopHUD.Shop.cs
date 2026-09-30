using System.Collections.Generic;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
namespace Checkout {
 // The market's shop (page.layout == "shop"): a full-screen window in the style of mobile/PC simulator
 // shops (Township, Hay Day, Supermarket Simulator): navy header with the balances, a rail of categories
 // on the left (red counters for things waiting in the inventory), sub-filters as chips and a grid of
 // big tiles (art, ribbon, name, what it does, price buttons). Data comes from desktop/pages/loja.ts.
 public partial class CheckoutDesktopHUD {
  // The build button (its own canvas) hides while the shop window is open.
  public static bool ShopOpen;
  public static readonly Color ShopNavy=K.C("1D2B4F"),ShopNavyLight=K.C("2B3D69"),ShopGold=K.C("F2B03D");
  GameObject shop;RectTransform shopRail,shopChipContent,shopGrid;GameObject shopChipBar;
  TextMeshProUGUI shopSection,shopHint,shopCoins,shopDiamonds;Image shopSectionIcon;ScrollRect shopScroll,shopChipScroll;string shopShown;
  readonly List<CheckoutDesktopButton> shopTabs=new List<CheckoutDesktopButton>();readonly List<GameObject> shopTabBadges=new List<GameObject>();
  readonly List<CheckoutDesktopButton> shopChips=new List<CheckoutDesktopButton>();readonly List<CheckoutShopTile> shopTiles=new List<CheckoutShopTile>();

  static RectTransform Stretch(RectTransform r,Vector2 min,Vector2 max){r.anchorMin=Vector2.zero;r.anchorMax=Vector2.one;r.offsetMin=min;r.offsetMax=max;return r;}

  void BuildShop(){
   var node=N.Node("Shop",root);shop=node.gameObject;Stretch(node,Vector2.zero,Vector2.zero);
   // Dimmed world behind; clicking it closes the shop.
   var dim=shop.AddComponent<Image>();dim.color=new Color(.10f,.07f,.04f,.58f);Clickable(shop,()=>host.Route(""));
   var window=Stretch(N.Node("Window",node),new Vector2(64,118),new Vector2(-64,-18));
   var edge=window.gameObject.AddComponent<Image>();edge.sprite=K.Rounded(30);edge.type=Image.Type.Sliced;edge.color=K.C("B98642");
   window.gameObject.AddComponent<Button>().transition=Selectable.Transition.None; // clicks inside do not close it
   var face=N.Image(window,"Face",K.Paper,28);Stretch(face.rectTransform,new Vector2(4,9),new Vector2(-4,-4));

   // Header: navy band, gold title, balances and close.
   var header=N.Image(face.transform,"Header",ShopNavy,26);var hr=header.rectTransform;hr.anchorMin=new Vector2(0,1);hr.anchorMax=Vector2.one;hr.pivot=new Vector2(.5f,1);hr.offsetMin=new Vector2(0,-98);hr.offsetMax=Vector2.zero;
   var stripe=N.Image(header.transform,"Gold stripe",ShopGold,3);var sr=stripe.rectTransform;sr.anchorMin=Vector2.zero;sr.anchorMax=new Vector2(1,0);sr.offsetMin=new Vector2(18,4);sr.offsetMax=new Vector2(-18,9);stripe.gameObject.AddComponent<LayoutElement>().ignoreLayout=true;
   var row=N.Row(header.gameObject,16,new RectOffset(24,18,10,18));row.childAlignment=TextAnchor.MiddleLeft;
   var logo=N.Image(header.transform,"Logo",Color.white,0);logo.sprite=K.Icon("Icons/market");logo.preserveAspect=true;var ll=logo.gameObject.AddComponent<LayoutElement>();ll.preferredWidth=ll.preferredHeight=66;
   var titles=N.Node("Titles",header.transform);N.Column(titles.gameObject,0);titles.gameObject.AddComponent<LayoutElement>().flexibleWidth=1;
   var title=N.Text(titles,"Title",K.Headline,36,ShopGold);title.text="LOJA DO MERCADO";title.characterSpacing=3;title.textWrappingMode=TextWrappingModes.NoWrap;
   var tagline=N.Text(titles,"Tagline",K.Body,15,K.C("C9D6EE"));tagline.text="Tudo o que você pode comprar, separado por categoria";
   shopCoins=Balance(header.transform,"Icons/coin",null);
   shopDiamonds=Balance(header.transform,"Icons/diamond",()=>host.Route("~loja:moedas"));
   var close=CheckoutDesktopButton.Create(header.transform,54,22,14);close.SetWidth(58);close.Clicked=_=>host.Route("");
   close.Apply(new DesktopButton{label="X",variant="danger",enabled=true,route="",action="",args="[]",after="",ok="",fail="",badge=""});

   // Body: category rail + content.
   var body=Stretch(N.Node("Body",face.transform),new Vector2(0,0),new Vector2(0,-104));
   var rail=N.Image(body,"Rail",K.C("F3DFC0"),22);var rr=rail.rectTransform;rr.anchorMin=Vector2.zero;rr.anchorMax=new Vector2(0,1);rr.pivot=new Vector2(0,.5f);rr.offsetMin=new Vector2(14,14);rr.offsetMax=new Vector2(270,-6);
   shopRail=rail.rectTransform;var rl=N.Column(rail.gameObject,8,new RectOffset(10,10,12,12));rl.childForceExpandHeight=false;

   var content=Stretch(N.Node("Content",body),new Vector2(286,12),new Vector2(-18,-6));
   N.Column(content.gameObject,8,new RectOffset(0,0,0,0));
   var section=N.Node("Section",content);N.Row(section.gameObject,12);section.gameObject.AddComponent<LayoutElement>().preferredHeight=58;
   shopSectionIcon=N.Image(section,"Icon",Color.white,0);shopSectionIcon.preserveAspect=true;var il=shopSectionIcon.gameObject.AddComponent<LayoutElement>();il.preferredWidth=il.preferredHeight=48;
   var texts=N.Node("Texts",section);N.Column(texts.gameObject,0);texts.gameObject.AddComponent<LayoutElement>().flexibleWidth=1;
   shopSection=N.Text(texts,"Title",K.Headline,28,K.Ink);shopSection.textWrappingMode=TextWrappingModes.NoWrap;
   shopHint=N.Text(texts,"Hint",K.Body,15,K.Muted);shopHint.textWrappingMode=TextWrappingModes.NoWrap;shopHint.overflowMode=TextOverflowModes.Ellipsis;
   shopChipScroll=Scroll(content,"Chips",false,out shopChipContent);shopChipBar=shopChipScroll.gameObject;shopChipBar.AddComponent<LayoutElement>().preferredHeight=48;
   shopScroll=Scroll(content,"Tiles",true,out shopGrid);shopScroll.gameObject.AddComponent<LayoutElement>().flexibleHeight=1;
   // The scroll helper sets up a column; the tiles use a grid instead.
   DestroyImmediate(shopGrid.GetComponent<VerticalLayoutGroup>());
   var grid=shopGrid.gameObject.AddComponent<GridLayoutGroup>();grid.cellSize=new Vector2(290,378);grid.spacing=new Vector2(18,18);grid.padding=new RectOffset(4,12,6,18);
   grid.startCorner=GridLayoutGroup.Corner.UpperLeft;grid.childAlignment=TextAnchor.UpperLeft;grid.constraint=GridLayoutGroup.Constraint.Flexible;
   shop.SetActive(false);
  }

  // Balance pill (coins, diamonds); the diamond one opens the coins & diamonds category.
  TextMeshProUGUI Balance(Transform parent,string icon,System.Action onClick){
   var pill=N.Image(parent,"Balance",ShopNavyLight,20);var row=N.Row(pill.gameObject,8,new RectOffset(10,14,6,6));row.childAlignment=TextAnchor.MiddleLeft;
   var le=pill.gameObject.AddComponent<LayoutElement>();le.preferredHeight=52;le.minWidth=150;
   var i=N.Image(pill.transform,"Icon",Color.white,0);i.sprite=K.Icon(icon);i.preserveAspect=true;var l=i.gameObject.AddComponent<LayoutElement>();l.preferredWidth=l.preferredHeight=34;
   var text=N.Text(pill.transform,"Value",K.Number,22,Color.white);text.textWrappingMode=TextWrappingModes.NoWrap;
   if(onClick!=null){pill.raycastTarget=true;var plus=N.Image(pill.transform,"Plus",K.C("5DA637"),12);var pl=plus.gameObject.AddComponent<LayoutElement>();pl.preferredWidth=pl.preferredHeight=28;
    var pt=N.Text(plus.transform,"+",K.Headline,22,Color.white);pt.text="+";pt.alignment=TextAlignmentOptions.Center;Stretch(pt.rectTransform,Vector2.zero,Vector2.zero);Clickable(pill.gameObject,onClick);}
   return text;
  }

  void ApplyShop(DesktopView v){
   bool on=v.hasPage&&v.page!=null&&v.page.layout=="shop";
   if(shop.activeSelf!=on)shop.SetActive(on);ShopOpen=on;
   if(!on){shopShown=null;return;}
   var p=v.page;
   shopCoins.text=v.coins;shopDiamonds.text=v.diamonds;
   shopSection.text=p.title;shopHint.text=p.subtitle;var icon=K.Icon(p.icon);shopSectionIcon.sprite=icon;shopSectionIcon.gameObject.SetActive(icon);
   // Category rail.
   var tabs=p.tabs??new DesktopButton[0];
   while(shopTabs.Count<tabs.Length){
    var b=CheckoutDesktopButton.Create(shopRail,62,17,16);b.Clicked=Press;shopTabs.Add(b);
    var label=b.GetComponentInChildren<TextMeshProUGUI>(true);label.alignment=TextAlignmentOptions.Left;label.textWrappingMode=TextWrappingModes.Normal;
    var faceRow=b.transform.Find("Face").GetComponent<HorizontalLayoutGroup>();faceRow.childAlignment=TextAnchor.MiddleLeft;faceRow.padding=new RectOffset(12,10,2,2);faceRow.spacing=10;
    var pill=N.Image(b.transform,"Badge",K.C("E15533"),13);var pr=pill.rectTransform;pr.anchorMin=pr.anchorMax=new Vector2(1,.5f);pr.pivot=new Vector2(1,.5f);pr.anchoredPosition=new Vector2(-10,2);pr.sizeDelta=new Vector2(30,28);
    var t=N.Text(pill.transform,"Count",K.Number,15,Color.white);t.alignment=TextAlignmentOptions.Center;Stretch(t.rectTransform,Vector2.zero,Vector2.zero);
    shopTabBadges.Add(pill.gameObject);
   }
   for(int i=0;i<shopTabs.Count;i++){
    bool show=i<tabs.Length;shopTabs[i].gameObject.SetActive(show);if(!show)continue;
    var data=tabs[i];shopTabs[i].Apply(data);
    // The open category is a gold tab; the others are plain.
    shopTabs[i].transform.Find("Face").GetComponent<Image>().color=data.active?ShopGold:K.C("FFF7EC");
    shopTabs[i].GetComponent<Image>().color=data.active?K.C("C58A1E"):K.C("D9BE93");
    bool badge=!string.IsNullOrEmpty(data.badge);shopTabBadges[i].SetActive(badge);if(badge)shopTabBadges[i].GetComponentInChildren<TextMeshProUGUI>().text=data.badge;
   }
   // Sub-filters.
   var chipData=p.chips??new DesktopButton[0];
   while(shopChips.Count<chipData.Length){var b=CheckoutDesktopButton.Create(shopChipContent,40,14,14);b.SetWidth(0);b.Clicked=Press;b.GetComponent<LayoutElement>().flexibleWidth=0;shopChips.Add(b);}
   for(int i=0;i<shopChips.Count;i++){bool show=i<chipData.Length;shopChips[i].gameObject.SetActive(show);if(show){shopChips[i].Apply(chipData[i]);FitChip(shopChips[i]);}}
   shopChipBar.SetActive(chipData.Length>0);
   // Tiles.
   var cardData=p.cards??new DesktopCard[0];
   while(shopTiles.Count<cardData.Length){var t=CheckoutShopTile.Create(shopGrid);t.Clicked=Press;shopTiles.Add(t);}
   for(int i=0;i<shopTiles.Count;i++){bool show=i<cardData.Length;shopTiles[i].gameObject.SetActive(show);if(show)shopTiles[i].Apply(cardData[i]);}
   string key=p.route??"";
   if(key!=shopShown){shopShown=key;Canvas.ForceUpdateCanvases();shopScroll.verticalNormalizedPosition=1;shopChipScroll.horizontalNormalizedPosition=0;}
  }
 }

 // One product tile of the shop grid: big art on a soft glow, ribbon, name, description, price buttons.
 public class CheckoutShopTile:MonoBehaviour {
  Image edge,face,art,glow,icon,ribbonBack,eyebrowBack,lockIcon,fill;TextMeshProUGUI ribbon,eyebrow,title,subtitle;
  RectTransform lines,buttons,fillRect;GameObject progress;
  readonly List<TextMeshProUGUI> linePool=new List<TextMeshProUGUI>();readonly List<CheckoutDesktopButton> buttonPool=new List<CheckoutDesktopButton>();
  public System.Action<CheckoutDesktopButton> Clicked;
  static Sprite glowSprite;

  // Soft white radial spot, tinted per tile.
  static Sprite Glow(){
   if(glowSprite)return glowSprite;
   const int size=128;var tex=new Texture2D(size,size,TextureFormat.RGBA32,false){wrapMode=TextureWrapMode.Clamp};
   var px=new Color32[size*size];
   for(int y=0;y<size;y++)for(int x=0;x<size;x++){float d=Vector2.Distance(new Vector2(x,y),new Vector2(size*.5f,size*.5f))/(size*.5f);px[y*size+x]=new Color32(255,255,255,(byte)(Mathf.Clamp01(1-d*d)*255));}
   tex.SetPixels32(px);tex.Apply();glowSprite=Sprite.Create(tex,new Rect(0,0,size,size),new Vector2(.5f,.5f));return glowSprite;
  }
  static RectTransform Anchor(RectTransform r,Vector2 min,Vector2 max,Vector2 offMin,Vector2 offMax){r.anchorMin=min;r.anchorMax=max;r.offsetMin=offMin;r.offsetMax=offMax;return r;}

  public static CheckoutShopTile Create(Transform parent){
   var root=N.Node("Tile",parent);var t=root.gameObject.AddComponent<CheckoutShopTile>();
   t.edge=root.gameObject.AddComponent<Image>();t.edge.sprite=K.Rounded(22);t.edge.type=Image.Type.Sliced;t.edge.raycastTarget=false;
   t.face=N.Image(root,"Face",K.Cream,20);Anchor(t.face.rectTransform,Vector2.zero,Vector2.one,new Vector2(3,7),new Vector2(-3,-3));
   var f=t.face.rectTransform;
   // Art: tinted panel with a glow and the big picture.
   t.art=N.Image(f,"Art",K.C("F7E6C8"),18);Anchor(t.art.rectTransform,new Vector2(0,1),Vector2.one,new Vector2(8,-168),new Vector2(-8,-8));
   t.glow=N.Image(t.art.transform,"Glow",Color.white,0);t.glow.sprite=Glow();Anchor(t.glow.rectTransform,Vector2.zero,Vector2.one,new Vector2(20,-6),new Vector2(-20,6));
   t.icon=N.Image(t.art.transform,"Icon",Color.white,0);t.icon.preserveAspect=true;Anchor(t.icon.rectTransform,Vector2.zero,Vector2.one,new Vector2(28,10),new Vector2(-28,-10));
   t.lockIcon=N.Image(t.art.transform,"Lock",Color.white,0);t.lockIcon.sprite=K.Icon("Icons/lock");t.lockIcon.preserveAspect=true;var lr=t.lockIcon.rectTransform;lr.anchorMin=lr.anchorMax=new Vector2(1,0);lr.pivot=new Vector2(1,0);lr.anchoredPosition=new Vector2(-8,8);lr.sizeDelta=new Vector2(40,40);
   // Eyebrow (top-left) and ribbon (top-right) over the art.
   t.eyebrowBack=N.Image(t.art.transform,"Eyebrow",new Color(.11f,.17f,.31f,.85f),10);var er=t.eyebrowBack.rectTransform;er.anchorMin=er.anchorMax=er.pivot=new Vector2(0,1);er.anchoredPosition=new Vector2(8,-8);
   N.Row(t.eyebrowBack.gameObject,0,new RectOffset(9,9,3,3));var ef=t.eyebrowBack.gameObject.AddComponent<ContentSizeFitter>();ef.horizontalFit=ef.verticalFit=ContentSizeFitter.FitMode.PreferredSize;
   t.eyebrow=N.Text(t.eyebrowBack.transform,"Text",K.Label,11,Color.white);t.eyebrow.textWrappingMode=TextWrappingModes.NoWrap;t.eyebrow.characterSpacing=3;
   t.ribbonBack=N.Image(t.art.transform,"Ribbon",CheckoutDesktopHUD.ShopGold,10);var rr=t.ribbonBack.rectTransform;rr.anchorMin=rr.anchorMax=rr.pivot=Vector2.one;rr.anchoredPosition=new Vector2(-8,-8);
   N.Row(t.ribbonBack.gameObject,0,new RectOffset(9,9,3,3));var rf=t.ribbonBack.gameObject.AddComponent<ContentSizeFitter>();rf.horizontalFit=rf.verticalFit=ContentSizeFitter.FitMode.PreferredSize;
   t.ribbon=N.Text(t.ribbonBack.transform,"Text",K.Number,13,K.Ink);t.ribbon.textWrappingMode=TextWrappingModes.NoWrap;
   // Texts.
   var text=Anchor(N.Node("Texts",f),Vector2.zero,Vector2.one,new Vector2(14,70),new Vector2(-14,-176));
   var col=N.Column(text.gameObject,3);col.childForceExpandHeight=false;
   t.title=N.Text(text,"Title",K.Headline,20,K.Ink);t.title.textWrappingMode=TextWrappingModes.NoWrap;t.title.overflowMode=TextOverflowModes.Ellipsis;
   t.subtitle=N.Text(text,"Subtitle",K.Body,13,K.Muted);t.subtitle.overflowMode=TextOverflowModes.Ellipsis;t.subtitle.maxVisibleLines=3;
   t.lines=N.Node("Lines",text);N.Column(t.lines.gameObject,1);
   // Progress + buttons at the bottom.
   var track=N.Image(f,"Progress",K.C("EADBC4"),5);Anchor(track.rectTransform,new Vector2(0,0),new Vector2(1,0),new Vector2(14,62),new Vector2(-14,72));t.progress=track.gameObject;
   t.fill=N.Image(track.transform,"Fill",K.C("5DA637"),5);t.fillRect=t.fill.rectTransform;t.fillRect.anchorMin=Vector2.zero;t.fillRect.offsetMin=t.fillRect.offsetMax=Vector2.zero;
   t.buttons=Anchor(N.Node("Buttons",f),Vector2.zero,new Vector2(1,0),new Vector2(12,10),new Vector2(-12,58));var br=N.Row(t.buttons.gameObject,8);br.childForceExpandWidth=true;br.childControlHeight=true;br.childForceExpandHeight=true;
   return t;
  }

  static void Set(TextMeshProUGUI text,string value){value=K.Clean(value);bool has=!string.IsNullOrEmpty(value);text.gameObject.SetActive(has);if(has&&text.text!=value)text.text=value;}

  public void Apply(DesktopCard data){
   bool featured=data.tone=="featured",locked=data.tone=="locked";
   var tone=featured?new K.Style("FFF3D6","E0A441","4A3624"):K.Tone(data.tone);
   edge.color=tone.edge;face.color=tone.face;
   // Art tint follows the state: gold offer, green owned, amber works, blue inventory, grey locked.
   art.color=featured?K.C("FFE2A0"):data.tone=="success"?K.C("D9EFC6"):data.tone=="warning"?K.C("FBE3AE"):data.tone=="info"?K.C("CFE7F1"):locked?K.C("E4DACB"):K.C("F7E6C8");
   glow.color=new Color(1,1,1,locked?.35f:.85f);
   var sprite=K.Icon(data.icon);icon.sprite=sprite;icon.gameObject.SetActive(sprite);icon.color=locked?new Color(.55f,.55f,.55f,.75f):Color.white;
   lockIcon.gameObject.SetActive(locked&&lockIcon.sprite);
   Set(eyebrow,data.eyebrow?.ToUpperInvariant());eyebrowBack.gameObject.SetActive(!string.IsNullOrEmpty(data.eyebrow));
   Set(ribbon,data.badge);ribbonBack.gameObject.SetActive(!string.IsNullOrEmpty(data.badge));
   ribbonBack.color=data.tone=="warning"?K.C("E8B54A"):data.tone=="info"?K.C("86C0D6"):data.tone=="success"?K.C("8CC063"):CheckoutDesktopHUD.ShopGold;
   Set(title,data.title);title.color=tone.text;Set(subtitle,data.subtitle);
   var values=data.lines??System.Array.Empty<string>();
   while(linePool.Count<values.Length){var l=N.Text(lines,"Line",K.Body,13,K.Ink);l.textWrappingMode=TextWrappingModes.NoWrap;l.overflowMode=TextOverflowModes.Ellipsis;linePool.Add(l);}
   for(int i=0;i<linePool.Count;i++){bool on=i<values.Length&&i<4;linePool[i].gameObject.SetActive(on);if(on)Set(linePool[i],values[i]);}
   progress.SetActive(data.progress>=0);fillRect.anchorMax=new Vector2(Mathf.Clamp01(data.progress),1);
   var actions=data.buttons??System.Array.Empty<DesktopButton>();
   while(buttonPool.Count<actions.Length){var b=CheckoutDesktopButton.Create(buttons,48,16,14);b.Clicked=x=>Clicked?.Invoke(x);buttonPool.Add(b);}
   for(int i=0;i<buttonPool.Count;i++){bool on=i<actions.Length;buttonPool[i].gameObject.SetActive(on);if(on)buttonPool[i].Apply(actions[i]);}
  }
 }
}
