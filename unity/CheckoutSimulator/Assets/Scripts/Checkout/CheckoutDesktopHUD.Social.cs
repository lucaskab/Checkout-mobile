using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;
using U = Checkout.CheckoutUiKit;
namespace Checkout {
 // Social v1 in the HUD (desktop/social.ts): the visit bar over a friend's market (their face and name, Curtir, Presente,
 // Pedidos, "Voltar ao meu mercado"), an "Ajudar" button floating over each of their running builds, and the small
 // queue of social toasts ("Ana te ajudou na obra: −5 min"). Navy with a thin gold trim, like the market's own colours.
 public partial class CheckoutDesktopHUD {
  static readonly Color SocialNavy=K.C("1D2B4F"),SocialGold=K.C("E3B54A"),SocialCream=K.C("F3E6CC");
  RectTransform visitBar,visitButtonRow,visitBuildRow,visitNote,socialToastBox,helpLayer;
  Image visitAvatar,socialToastIcon;TextMeshProUGUI visitName,visitSubtitle,visitNoteText,socialToastText;
  readonly List<CheckoutDesktopButton> visitButtons=new List<CheckoutDesktopButton>(),visitBuildButtons=new List<CheckoutDesktopButton>(),helpButtons=new List<CheckoutDesktopButton>();
  readonly Queue<(string text,string icon,bool ok)> socialToasts=new Queue<(string text,string icon,bool ok)>();
  readonly List<Transform> helpAnchors=new List<Transform>();
  float socialToastUntil,siteCheckAt;bool visiting;
  /// <summary>The last HUD button pressed (a sparkle bursts there when a like or a help lands).</summary>
  RectTransform lastPressed;
  RectTransform socialFxLayer;
  sealed class SocialConfetto{public RectTransform rect;public Image image;public Vector2 velocity;public float spin,life,age;}
  readonly List<SocialConfetto> socialConfetti=new List<SocialConfetto>();
  readonly List<DesktopVisitBuild> looseBuilds=new List<DesktopVisitBuild>();
  /// <summary>Visiting a friend (the HUD shows the visit bar instead of the player's own).</summary>
  public bool VisitShown=>visiting;

  /// <summary>A social celebration (desktop/social.ts fx): confetti and coins flying to the counter, or a sparkle.</summary>
  public void SocialFx(string kind,int coins){
   if(!socialFxLayer){socialFxLayer=N.Node("SocialFx",root);Stretch(socialFxLayer,Vector2.zero,Vector2.zero);}
   socialFxLayer.SetAsLastSibling();
   var from=lastPressed&&lastPressed.gameObject.activeInHierarchy?U.PointIn(socialFxLayer,lastPressed):socialFxLayer.rect.center;
   if(kind=="sparkle"){U.Sparkles(this,socialFxLayer,from,12,170);Sound("success",1.1f);return;}
   if(kind!="confetti")return;
   Sound("coin_"+Random.Range(0,3));Sound("success");
   var accent=CheckoutConfettiArt.Gold;
   for(int i=0;i<46;i++){
    int row=Random.Range(0,CheckoutConfettiArt.RowCount),col=Random.Range(0,CheckoutConfettiArt.Cols);
    var go=new GameObject("Piece",typeof(RectTransform),typeof(Image));go.transform.SetParent(socialFxLayer,false);
    var img=go.GetComponent<Image>();img.sprite=CheckoutConfettiArt.Sprite(accent,row,col);img.raycastTarget=false;
    var r=img.rectTransform;r.anchorMin=r.anchorMax=new Vector2(.5f,.5f);float size=Random.Range(18f,30f);r.sizeDelta=new Vector2(size,size);
    r.anchoredPosition=from+Random.insideUnitCircle*24;r.localRotation=Quaternion.Euler(0,0,Random.Range(0f,360f));
    float angle=Random.Range(30f,150f)*Mathf.Deg2Rad,speed=Random.Range(380f,820f);
    socialConfetti.Add(new SocialConfetto{rect=r,image=img,velocity=new Vector2(Mathf.Cos(angle)*speed,Mathf.Sin(angle)*speed),spin=Random.Range(-360f,360f),life=Random.Range(1.2f,1.9f)});
   }
   // the coins fly to the counter (the board window's balance, else the top bar's)
   var counter=BoardOpen&&boardCoins?boardCoins.rectTransform:null;
   if(counter)StartCoroutine(U.Coins(this,socialFxLayer,from,U.PointIn(socialFxLayer,counter),Mathf.Clamp(coins/5,4,10)));
  }
  void UpdateSocialFx(){
   float dt=U.Dt;
   for(int i=socialConfetti.Count-1;i>=0;i--){
    var p=socialConfetti[i];if(!p.rect){socialConfetti.RemoveAt(i);continue;}
    p.age+=dt;p.velocity+=new Vector2(-p.velocity.x*1.6f*dt,-900f*dt);p.rect.anchoredPosition+=p.velocity*dt;p.rect.Rotate(0,0,p.spin*dt);
    var c=p.image.color;c.a=Mathf.Clamp01((p.life-p.age)/.4f);p.image.color=c;
    if(p.age>=p.life){Destroy(p.rect.gameObject);socialConfetti.RemoveAt(i);}
   }
  }

  void BuildSocial(){
   // Under everything else of the HUD: the "Ajudar" buttons that follow the builds of the friend's market.
   helpLayer=N.Node("VisitHelp",root);Stretch(helpLayer,Vector2.zero,Vector2.zero);helpLayer.SetAsFirstSibling();

   var edge=N.Image(root,"VisitBar",SocialGold,22);visitBar=edge.rectTransform;
   visitBar.anchorMin=visitBar.anchorMax=visitBar.pivot=new Vector2(.5f,1);visitBar.anchoredPosition=new Vector2(0,Phone?-8:-14);
   var fit=edge.gameObject.AddComponent<ContentSizeFitter>();fit.horizontalFit=fit.verticalFit=ContentSizeFitter.FitMode.PreferredSize;
   N.Column(edge.gameObject,0,new RectOffset(2,2,2,2));
   var face=N.Image(edge.transform,"Face",SocialNavy,20);var row=N.Row(face.gameObject,Phone?12:14,new RectOffset(12,12,10,10));row.childAlignment=TextAnchor.MiddleLeft;
   var ring=N.Image(face.transform,"Avatar",SocialGold,36);var rl=ring.gameObject.AddComponent<LayoutElement>();rl.preferredWidth=rl.preferredHeight=Phone?72:66;
   var clip=N.Image(ring.transform,"Clip",SocialNavy,34);Stretch(clip.rectTransform,new Vector2(3,3),new Vector2(-3,-3));clip.gameObject.AddComponent<Mask>().showMaskGraphic=true;
   visitAvatar=N.Image(clip.transform,"Face",Color.white,0);visitAvatar.preserveAspect=true;Stretch(visitAvatar.rectTransform,Vector2.zero,Vector2.zero);
   var texts=N.Node("Texts",face.transform);N.Column(texts.gameObject,0);var tl=texts.gameObject.AddComponent<LayoutElement>();tl.minWidth=Phone?230:250;tl.preferredWidth=Phone?260:280;
   var eyebrow=N.Text(texts,"Eyebrow",K.Label,12,SocialGold);eyebrow.text="VISITANDO";eyebrow.characterSpacing=4;
   visitName=N.Text(texts,"Name",K.Headline,Phone?24:22,Color.white);visitName.textWrappingMode=TextWrappingModes.NoWrap;visitName.overflowMode=TextOverflowModes.Ellipsis;
   visitSubtitle=N.Text(texts,"Subtitle",K.Body,Phone?15:14,SocialCream);visitSubtitle.textWrappingMode=TextWrappingModes.NoWrap;visitSubtitle.overflowMode=TextOverflowModes.Ellipsis;
   visitButtonRow=N.Node("Buttons",face.transform);N.Row(visitButtonRow.gameObject,8).childForceExpandHeight=false;
   edge.gameObject.SetActive(false);

   // Builds with no spot found on the map (the expansion works, a lot, a stall's own crates, a piece still in the
   // friend's inventory): their "Ajudar" goes in a row under the bar.
   visitBuildRow=N.Node("VisitBuilds",root);visitBuildRow.anchorMin=visitBuildRow.anchorMax=visitBuildRow.pivot=new Vector2(.5f,1);
   var bf=visitBuildRow.gameObject.AddComponent<ContentSizeFitter>();bf.horizontalFit=bf.verticalFit=ContentSizeFitter.FitMode.PreferredSize;N.Row(visitBuildRow.gameObject,8);
   visitBuildRow.gameObject.SetActive(false);

   // The hint at the bottom ("Toque em Ajudar…").
   var note=N.Image(root,"VisitNote",SocialGold,18);visitNote=note.rectTransform;visitNote.anchorMin=visitNote.anchorMax=visitNote.pivot=new Vector2(.5f,0);visitNote.anchoredPosition=new Vector2(0,Phone?14:20);
   var nf=note.gameObject.AddComponent<ContentSizeFitter>();nf.horizontalFit=nf.verticalFit=ContentSizeFitter.FitMode.PreferredSize;N.Column(note.gameObject,0,new RectOffset(2,2,2,2));
   var nface=N.Image(note.transform,"Face",SocialNavy,16);N.Row(nface.gameObject,0,new RectOffset(20,20,10,10));
   visitNoteText=N.Text(nface.transform,"Text",K.Label,Phone?18:16,SocialCream);visitNoteText.textWrappingMode=TextWrappingModes.NoWrap;
   note.gameObject.SetActive(false);

   // Social toasts: one at a time, under the top bar, with the icon of what happened.
   var tedge=N.Image(root,"SocialToast",SocialGold,20);socialToastBox=tedge.rectTransform;socialToastBox.anchorMin=socialToastBox.anchorMax=socialToastBox.pivot=new Vector2(.5f,1);
   var tf=tedge.gameObject.AddComponent<ContentSizeFitter>();tf.horizontalFit=tf.verticalFit=ContentSizeFitter.FitMode.PreferredSize;N.Column(tedge.gameObject,0,new RectOffset(2,2,2,2));
   var tface=N.Image(tedge.transform,"Face",SocialNavy,18);var trow=N.Row(tface.gameObject,12,new RectOffset(14,22,10,10));trow.childAlignment=TextAnchor.MiddleLeft;
   socialToastIcon=N.Image(tface.transform,"Icon",Color.white,0);socialToastIcon.preserveAspect=true;var il=socialToastIcon.gameObject.AddComponent<LayoutElement>();il.preferredWidth=il.preferredHeight=Phone?44:40;
   socialToastText=N.Text(tface.transform,"Text",K.Label,Phone?20:18,Color.white);socialToastText.textWrappingMode=TextWrappingModes.Normal;
   var stl=socialToastText.gameObject.AddComponent<LayoutElement>();stl.preferredWidth=-1;
   tedge.gameObject.SetActive(false);
  }

  /// <summary>QA: a social toast is on screen or waiting (the shots wait for them to fade).</summary>
  public bool SocialToastShowing=>socialToastBox&&(socialToastBox.gameObject.activeSelf||socialToasts.Count>0);
  /// <summary>Queues a social toast (CheckoutSocial: inbox results, answers of the friends' server).</summary>
  public void SocialToast(string text,string icon,bool ok){
   if(string.IsNullOrEmpty(text))return;
   if(socialToasts.Count<8)socialToasts.Enqueue((text,icon,ok));
   if(!socialToastBox.gameObject.activeSelf)NextSocialToast();
  }
  void NextSocialToast(){
   if(socialToasts.Count==0){socialToastBox.gameObject.SetActive(false);return;}
   var (text,icon,ok)=socialToasts.Dequeue();
   socialToastText.text=K.Clean(text);
   var size=socialToastText.GetPreferredValues(socialToastText.text);socialToastText.GetComponent<LayoutElement>().preferredWidth=Mathf.Min(size.x+4,Phone?820:760);
   var sprite=K.Icon(icon);socialToastIcon.sprite=sprite;socialToastIcon.gameObject.SetActive(sprite);
   socialToastBox.GetComponent<Image>().color=ok?SocialGold:K.C("E15533");
   // Visiting: under the bar (and its row of "Ajudar" buttons). At home: just above the toolbar, clear of the top bar,
   // the tutorial card and the open window.
   // With a window open, over the free part of the screen left of it (never over the window's cards).
   var at=visiting?new Vector2(.5f,1):new Vector2(.5f,0);socialToastBox.anchorMin=socialToastBox.anchorMax=socialToastBox.pivot=at;
   socialToastBox.anchoredPosition=visiting?new Vector2(ToastShift(),Phone?-178:-170):new Vector2(ToastShift(),Phone?124:142);
   socialToastBox.gameObject.SetActive(true);socialToastBox.SetAsLastSibling();socialToastUntil=Time.unscaledTime+2.8f;
   StartCoroutine(CheckoutUiKit.Pop(socialToastBox,1.06f,.18f));
  }

  void ApplySocial(DesktopView v){
   bool on=v.visit!=null&&v.visit.active;
   if(on!=visiting){
    visiting=on;
    // The player's own top bar and toolbar wait at home (the rest of the HUD already hides from the view).
    foreach(var name in new[]{"TopBar","Toolbar"}){var t=root.Find(name);if(t)t.gameObject.SetActive(!on);}
    if(!on){foreach(var b in helpButtons)b.gameObject.SetActive(false);helpAnchors.Clear();}
   }
   if(on)foreach(var name in new[]{"TopBar","Toolbar"}){var t=root.Find(name);if(t&&t.gameObject.activeSelf)t.gameObject.SetActive(false);}
   visitBar.gameObject.SetActive(on&&!v.hasPage);visitNote.gameObject.SetActive(on&&!v.hasPage&&!string.IsNullOrEmpty(v.visit.note));
   if(!on){visitBuildRow.gameObject.SetActive(false);return;}
   var visit=v.visit;
   visitName.text=visit.friendName;visitSubtitle.text=visit.subtitle;visitNoteText.text=visit.note;
   var face=K.Icon(visit.avatar);visitAvatar.sprite=face;visitAvatar.enabled=face;
   var buttons=visit.buttons??new DesktopButton[0];
   while(visitButtons.Count<buttons.Length){var b=CheckoutDesktopButton.Create(visitButtonRow,Phone?62:56,Phone?18:16,14);b.Clicked=x=>{Sound("tap",1.05f);Press(x);};visitButtons.Add(b);}
   for(int i=0;i<visitButtons.Count;i++){
    bool shown=i<buttons.Length;visitButtons[i].gameObject.SetActive(shown);if(!shown)continue;
    visitButtons[i].Apply(buttons[i]);FitVisitButton(visitButtons[i]);
   }
   // "Ajudar" over each build of the friend's market (or in the row under the bar when its site is not on the map).
   var builds=visit.builds??new DesktopVisitBuild[0];
   helpAnchors.Clear();var loose=looseBuilds;loose.Clear();
   for(int i=0;i<builds.Length;i++){
    var anchor=SiteOf(builds[i]);
    if(anchor){helpAnchors.Add(anchor);while(helpButtons.Count<helpAnchors.Count){var b=CheckoutDesktopButton.Create(helpLayer,Phone?64:56,Phone?20:18,16);b.Clicked=x=>{Sound("tap",1.1f);Press(x);};helpButtons.Add(b);
      // a gold pin from the button down to the site, so it reads as "this build"
      var pin=N.Image(b.transform,"Pin",SocialGold,0);var pr=pin.rectTransform;pr.anchorMin=pr.anchorMax=new Vector2(.5f,0);pr.pivot=new Vector2(.5f,1);pr.sizeDelta=new Vector2(4,30);pr.anchoredPosition=new Vector2(0,2);pin.transform.SetAsFirstSibling();
      var dot=N.Image(pin.transform,"Dot",SocialNavy,8);var dr=dot.rectTransform;dr.anchorMin=dr.anchorMax=new Vector2(.5f,0);dr.sizeDelta=new Vector2(16,16);dr.anchoredPosition=Vector2.zero;
      var ring=N.Image(dot.transform,"Ring",SocialGold,8);Stretch(ring.rectTransform,new Vector2(-3,-3),new Vector2(3,3));ring.transform.SetAsFirstSibling();}
     var hb=helpButtons[helpAnchors.Count-1];hb.Apply(builds[i].button);FitVisitButton(hb);}
    else loose.Add(builds[i]);
   }
   for(int i=helpAnchors.Count;i<helpButtons.Count;i++)helpButtons[i].gameObject.SetActive(false);
   while(visitBuildButtons.Count<loose.Count){var b=CheckoutDesktopButton.Create(visitBuildRow,Phone?58:52,Phone?17:15,14);b.Clicked=x=>{Sound("tap",1.1f);Press(x);};visitBuildButtons.Add(b);}
   for(int i=0;i<visitBuildButtons.Count;i++){
    bool shown=i<loose.Count;visitBuildButtons[i].gameObject.SetActive(shown);if(!shown)continue;
    var data=loose[i].button;var labelled=JsonUtility.FromJson<DesktopButton>(JsonUtility.ToJson(data));labelled.label=loose[i].label+" · "+data.label;
    visitBuildButtons[i].Apply(labelled);FitVisitButton(visitBuildButtons[i]);
   }
   visitBuildRow.gameObject.SetActive(loose.Count>0&&!v.hasPage);
   visitBuildRow.anchoredPosition=new Vector2(0,visitBar.anchoredPosition.y-(Phone?104:96));
  }
  static void FitVisitButton(CheckoutDesktopButton b){
   var label=b.GetComponentInChildren<TextMeshProUGUI>(true);var icon=b.transform.Find("Face/Icon");
   float w=(label&&label.gameObject.activeSelf?label.GetPreferredValues(label.text).x:0)+(icon&&icon.gameObject.activeSelf?(Phone?40:34):0)+(Phone?34:30);
   b.SetWidth(Mathf.Clamp(w,Phone?96:88,Phone?360:320));
  }
  /// <summary>Where a build of the friend's market stands: its works board or evolution ring (null = not on the map).</summary>
  static Transform SiteOf(DesktopVisitBuild build){
   if(build==null||string.IsNullOrEmpty(build.targetId))return null;
   // (also under a roof that hides the shop's inside: the button floats over the building)
   if(build.kind=="interior")foreach(var w in FindObjectsByType<CheckoutInteriorWorks>(FindObjectsInactive.Include,FindObjectsSortMode.None))if(w&&w.BuildId==build.targetId)return w.Board?w.Board:w.transform;
   if(build.kind=="evolution")foreach(var e in FindObjectsByType<CheckoutEvolutionSite>(FindObjectsInactive.Include,FindObjectsSortMode.None))if(e&&e.EvolutionId==build.targetId)return e.Ring?e.Ring:e.transform;
   return null;
  }

  float ToastShift()=>drawer&&drawer.activeSelf?-(Phone?284:308):0;

  void UpdateSocial(){
   UpdateSocialFx();
   if(socialToastBox.gameObject.activeSelf&&Time.unscaledTime>socialToastUntil)NextSocialToast();
   // (a window that opens while a toast shows: the toast steps aside)
   if(socialToastBox.gameObject.activeSelf){var p=socialToastBox.anchoredPosition;float shift=ToastShift();if(Mathf.Abs(p.x-shift)>.5f)socialToastBox.anchoredPosition=new Vector2(shift,p.y);}
   if(!visiting)return;
   // The friend's market is built over a few frames after the view: a build still in the row looks for its spot again.
   if(looseBuilds.Count>0&&view!=null&&Time.unscaledTime>siteCheckAt){siteCheckAt=Time.unscaledTime+1f;bool found=false;foreach(var b in looseBuilds)if(SiteOf(b)){found=true;break;}if(found)ApplySocial(view);}
   var cam=Camera.main;var canvas=root.GetComponentInParent<Canvas>();
   for(int i=0;i<helpAnchors.Count&&i<helpButtons.Count;i++){
    var anchor=helpAnchors[i];var b=helpButtons[i];
    if(!anchor||!cam||view==null||view.hasPage){b.gameObject.SetActive(false);continue;}
    var screen=cam.WorldToScreenPoint(anchor.position+Vector3.up*.9f)+new Vector3(0,34*(root.lossyScale.y>0?1:1),0);
    bool shown=screen.z>0&&screen.x>0&&screen.x<Screen.width&&screen.y>0&&screen.y<Screen.height;
    b.gameObject.SetActive(shown);if(!shown)continue;
    var rect=(RectTransform)b.transform;
    RectTransformUtility.ScreenPointToLocalPointInRectangle(helpLayer,screen,canvas&&canvas.renderMode!=RenderMode.ScreenSpaceOverlay?canvas.worldCamera:null,out var local);
    var le=b.GetComponent<LayoutElement>();rect.sizeDelta=new Vector2(le.preferredWidth>0?le.preferredWidth:140,le.preferredHeight);
    // never under the visit bar (and its row of buttons), never on top of the button before it
    float top=helpLayer.rect.height*.5f-(visitBuildRow.gameObject.activeSelf?(Phone?236:220):(Phone?170:160))-rect.sizeDelta.y;
    local.y=Mathf.Min(local.y,top);
    for(int j=0;j<i&&j<helpButtons.Count;j++){
     var other=(RectTransform)helpButtons[j].transform;if(!other.gameObject.activeSelf)continue;
     var o=other.anchoredPosition;float need=(other.sizeDelta.x+rect.sizeDelta.x)*.5f+10;
     if(Mathf.Abs(local.y-o.y)<rect.sizeDelta.y+6&&Mathf.Abs(local.x-o.x)<need)local.x=o.x+(local.x>=o.x?need:-need);
    }
    rect.anchorMin=rect.anchorMax=new Vector2(.5f,.5f);rect.pivot=new Vector2(.5f,0);rect.anchoredPosition=local;
   }
  }

  // "$input:<id>" in a button's args: what the player typed in that card field (CheckoutDesktopCard.Typed).
  static readonly Regex TypedArg=new Regex("\"\\$input:([A-Za-z0-9_-]+)\"",RegexOptions.Compiled);
  static string WithTyped(string args){
   if(string.IsNullOrEmpty(args)||args.IndexOf("$input:",System.StringComparison.Ordinal)<0)return args;
   return TypedArg.Replace(args,m=>JsonText(N.Typed.TryGetValue(m.Groups[1].Value,out var v)?v:""));
  }
  static string JsonText(string value){
   var b=new StringBuilder("\"");
   foreach(var c in value??""){
    if(c=='"'||c=='\\')b.Append('\\').Append(c);
    else if(c<' ')b.Append("\\u").Append(((int)c).ToString("x4"));
    else b.Append(c);
   }
   return b.Append('"').ToString();
  }
 }
}
