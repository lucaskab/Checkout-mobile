using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using U = Checkout.CheckoutUiKit;

namespace Checkout {
 // Store mishaps in the 3D world (src/services/store-incidents.ts): a spill with a wet-floor sign, a
 // cooler (ice cream freezer / drinks fridge) sparking and smoking, a big wrong price tag, a dead bulb. Each has a clickable warning
 // bubble; the click opens a short hands-on task drawn with rendered art (scripts/blender/
 // build_ui_sprites.py) and, once done, sends fixIncident(id) to the app.
 public sealed class CheckoutIncidents:MonoBehaviour {
  public static CheckoutIncidents Instance {get;private set;}
  public bool IsOpen=>window&&window.activeSelf;
  bool markerErrorLogged;
  CheckoutBridge bridge;CheckoutMap map;readonly CheckoutEventAssets art=new CheckoutEventAssets();
  readonly Dictionary<string,Transform> markers=new Dictionary<string,Transform>();
  RectTransform root,stage;GameObject window,fab,hint;TextMeshProUGUI title,fabText;Image backdrop;AudioSource sound;AudioClip scrub,clank,ding,buzz,click,hum,thud;
  IncidentEntry current;bool done;float closeAt;readonly List<GameObject> scene=new List<GameObject>();

  public void Initialize(CheckoutBridge owner,CheckoutMap projection){
   Instance=this;bridge=owner;map=projection;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.45f;
   scrub=U.Noise(.1f,.1f);clank=U.Tone(420,.09f,300,.6f);ding=U.Tone(990,.22f,1480);buzz=U.Tone(150,.3f,110,.6f);click=U.Tone(2200,.03f);hum=U.Tone(120,.6f,122,.25f);thud=U.Tone(90,.12f,70,.7f);
   root=U.Canvas(transform,"CheckoutIncidentGame",81);
   BuildFab();
   stage=U.GameWindow(root,"floor_backdrop",out window,out title,out backdrop,Close);
   window.SetActive(false);
  }
  void Play(AudioClip clip,float pitch=1){if(!clip)return;sound.pitch=pitch;sound.PlayOneShot(clip);}

  void BuildFab(){
   var node=CheckoutDesktopCard.Node("ImprevistoButton",root);node.anchorMin=node.anchorMax=new Vector2(0,.5f);node.pivot=new Vector2(0,.5f);node.anchoredPosition=new Vector2(16,-176);node.sizeDelta=new Vector2(150,124);
   var edge=node.gameObject.AddComponent<Image>();edge.sprite=K.Rounded(22);edge.type=Image.Type.Sliced;edge.color=K.C("A9651C");
   var face=U.Box(node,"Face","F2B03D",20,Vector2.zero,Vector2.one);face.rectTransform.offsetMin=new Vector2(0,7);
   U.Art(face.transform,"Icon","bucket",new Vector2(.5f,.62f),68);
   var label=U.Label(face.transform,"Label",K.Headline,17,"4A3624");U.Stretch(label.rectTransform,Vector2.zero,new Vector2(1,.3f));label.text="CONSERTAR";
   var badge=U.Shape(node,"Badge","E15533",16,new Vector2(1,1),new Vector2(42,36),new Vector2(-6,-6));
   fabText=U.Label(badge.transform,"Count",K.Headline,20,"FFFFFF");U.Stretch(fabText.rectTransform,Vector2.zero,Vector2.one);
   U.Tap(edge,()=>Open(null));
   fab=node.gameObject;fab.SetActive(false);
  }

  static string IconFor(string kind)=>kind=="derramado"?"broom":kind=="freezer_sorvete"?"freezer":kind=="geladeira_bebidas"?"refrigerator":kind=="etiqueta"?"price-tag":"light";
  static string TitleFor(string kind)=>kind=="derramado"?"Limpar o chão":kind=="freezer_sorvete"?"Freezer de sorvete em curto":kind=="geladeira_bebidas"?"Geladeira de bebidas em curto":kind=="etiqueta"?"Trocar a etiqueta":"Trocar a lâmpada";

  // ------------------------------------------------------------------ world markers
  void Update(){
   var list=bridge.State?.incidents??Array.Empty<IncidentEntry>();
   fab.SetActive(list.Length>0&&!window.activeSelf&&!(CheckoutCounterGame.Instance&&CheckoutCounterGame.Instance.IsOpen));if(fab.activeSelf)fabText.text=list.Length.ToString();
   try{
    foreach(var incident in list)if(!markers.ContainsKey(incident.id))markers[incident.id]=Marker(incident);
    foreach(var id in markers.Keys.ToList())if(list.All(i=>i.id!=id)){var m=markers[id];markers.Remove(id);if(m)StartCoroutine(Vanish(m));}
    foreach(var pair in markers)Animate(pair.Value,list.FirstOrDefault(i=>i.id==pair.Key));
   }catch(Exception e){if(!markerErrorLogged){markerErrorLogged=true;Debug.LogException(e);}}
   if(!window.activeSelf)return;
   DrawWires();
   if(closeAt>0){if(Time.unscaledTime>closeAt)Close();return;}
   if(current!=null&&list.All(i=>i.id!=current.id)&&!done){done=true;closeAt=Time.unscaledTime+.8f;} // Fixed by staff meanwhile.
   if(Input.GetKeyDown(KeyCode.Escape))Close();
  }
  Vector3 Spot(string shelfId){var p=map.Fixture(shelfId);var front=new Vector3(p.x,.76f,p.z-.95f);return front;}
  Transform Marker(IncidentEntry incident){
   var rootT=new GameObject("Incident · "+incident.kind).transform;rootT.SetParent(transform);rootT.position=Spot(incident.shelfId);
   switch(incident.kind){
    case "derramado":
     foreach(var (x,z,s) in new[]{(0f,0f,1f),(.35f,.2f,.55f),(-.3f,-.18f,.45f)}){var puddle=art.Part(rootT,"Puddle",new Vector3(x,.01f,z),new Vector3(.9f*s,.01f,.65f*s),"86C6E6",PrimitiveType.Cylinder);}
     var sign=art.Group(rootT,"Wet floor sign",new Vector3(.75f,0,.1f));
     art.Part(sign,"Front",new Vector3(0,.32f,-.08f),new Vector3(.34f,.6f,.03f),"F4BA42").localRotation=Quaternion.Euler(-12,0,0);
     art.Part(sign,"Back",new Vector3(0,.32f,.08f),new Vector3(.34f,.6f,.03f),"F4BA42").localRotation=Quaternion.Euler(12,0,0);
     art.Part(sign,"Mark",new Vector3(0,.36f,-.12f),new Vector3(.06f,.24f,.02f),"2F3A40").localRotation=Quaternion.Euler(-12,0,0);
     break;
    case "freezer_sorvete":
    case "geladeira_bebidas":
     art.Part(rootT,"Warning light",new Vector3(0,2.05f,.8f),new Vector3(.22f,.12f,.22f),"E15533",PrimitiveType.Cylinder);
     for(int i=0;i<3;i++)art.Part(rootT,"Smoke",new Vector3(0,1.9f,.8f),Vector3.one*.18f,"C9D6D2",PrimitiveType.Sphere);
     art.Part(rootT,"Water",new Vector3(0,.01f,.1f),new Vector3(.8f,.01f,.4f),"B4EBE2",PrimitiveType.Cylinder);
     break;
    case "etiqueta":
     var tag=art.Group(rootT,"Wrong tag",new Vector3(0,1.55f,.3f));
     art.Part(tag,"Tag",Vector3.zero,new Vector3(.6f,.32f,.04f),"E15533");art.Part(tag,"Hole",new Vector3(-.22f,.06f,-.03f),new Vector3(.06f,.06f,.02f),"FFF1D1");
     art.Part(tag,"Cross A",new Vector3(.05f,0,-.03f),new Vector3(.3f,.05f,.02f),"FFF1D1").localRotation=Quaternion.Euler(0,0,35);
     art.Part(tag,"Cross B",new Vector3(.05f,0,-.03f),new Vector3(.3f,.05f,.02f),"FFF1D1").localRotation=Quaternion.Euler(0,0,-35);
     break;
    default:
     art.Bar(rootT,new Vector3(0,3.1f,.6f),new Vector3(0,2.5f,.6f),.03f,"2F3A40");
     art.Part(rootT,"Shade",new Vector3(0,2.45f,.6f),new Vector3(.5f,.16f,.5f),"384444",PrimitiveType.Cylinder);
     art.Part(rootT,"Bulb",new Vector3(0,2.32f,.6f),Vector3.one*.18f,"555555",PrimitiveType.Sphere);
     break;
   }
   // Clickable warning bubble over the mishap.
   var bubble=art.Group(rootT,"Bubble",new Vector3(0,2.7f,0));
   art.Part(bubble,"Edge",new Vector3(0,0,.012f),new Vector3(.66f,.56f,.03f),"4A3624");art.Part(bubble,"Face",Vector3.zero,new Vector3(.6f,.5f,.04f),"FFF1CF");
   var iconGo=new GameObject("Icon");iconGo.transform.SetParent(bubble,false);iconGo.transform.localPosition=new Vector3(0,0,-.05f);
   var sr=iconGo.AddComponent<SpriteRenderer>();sr.sprite=K.Icon("Icons/"+IconFor(incident.kind));if(sr.sprite){var size=Mathf.Max(sr.sprite.bounds.size.x,sr.sprite.bounds.size.y);iconGo.transform.localScale=Vector3.one*(.36f/Mathf.Max(.001f,size));}
   var hit=bubble.gameObject.AddComponent<BoxCollider>();hit.size=new Vector3(.9f,.8f,.3f);bubble.gameObject.layer=0;
   var target=bubble.gameObject.AddComponent<CheckoutTarget>();target.panel="incident";target.requestId=incident.id;
   rootT.localScale=Vector3.zero;StartCoroutine(Grow(rootT));
   return rootT;
  }
  IEnumerator Grow(Transform t){for(float s=0;s<1;s+=Time.deltaTime/.4f){if(!t)yield break;t.localScale=Vector3.one*Mathf.Sin(s*Mathf.PI*.6f)/Mathf.Sin(Mathf.PI*.6f);yield return null;}if(t)t.localScale=Vector3.one;}
  IEnumerator Vanish(Transform t){Play(ding,1.3f);for(float s=1;s>0;s-=Time.deltaTime/.35f){if(!t)yield break;t.localScale=Vector3.one*s;yield return null;}if(t)Destroy(t.gameObject);}
  void Animate(Transform marker,IncidentEntry incident){
   if(!marker||incident==null)return;
   var bubble=marker.Find("Bubble");if(bubble){bubble.localPosition=new Vector3(0,2.7f+Mathf.Sin(Time.time*3)*.06f,0);if(Camera.main)bubble.rotation=Camera.main.transform.rotation;}
   if(IsCooler(incident.kind)){
    var light=marker.Find("Warning light");if(light)light.GetComponent<Renderer>().material.color=Mathf.Repeat(Time.time,1)<.5f?K.C("FF4A3A"):K.C("5A1A12");
    int i=0;foreach(Transform smoke in marker)if(smoke.name=="Smoke"){float t=Mathf.Repeat(Time.time*.5f+i*.33f,1);smoke.localPosition=new Vector3(Mathf.Sin(t*6+i)*.1f,1.9f+t*.9f,.8f);smoke.localScale=Vector3.one*(.12f+t*.25f);i++;}
   }
   if(incident.kind=="etiqueta"){var tag=marker.Find("Wrong tag");if(tag){tag.localRotation=Quaternion.Euler(0,0,Mathf.Sin(Time.time*2.5f)*12);if(Camera.main)tag.rotation=Camera.main.transform.rotation*Quaternion.Euler(0,0,Mathf.Sin(Time.time*2.5f)*12);}}
   if(incident.kind=="lampada"){var bulb=marker.Find("Bulb");if(bulb)bulb.GetComponent<Renderer>().material.color=UnityEngine.Random.value<.06f?K.C("FFF3B0"):K.C("555555");}
  }

  // ------------------------------------------------------------------ hands-on tasks
  public static void Show(string id){if(Instance)Instance.Open(id);}
  void Open(string id){
   var list=bridge.State?.incidents??Array.Empty<IncidentEntry>();
   current=list.FirstOrDefault(i=>i.id==id)??list.FirstOrDefault();if(current==null)return;
   done=false;closeAt=0;title.text=TitleFor(current.kind)+" · "+current.shelfName;
   window.SetActive(true);window.transform.SetAsLastSibling();StopAllCoroutines();Clear();
   U.SetArt(backdrop,current.kind=="derramado"?"floor_backdrop":current.kind=="lampada"?"ceiling_backdrop":"wall_backdrop");
   Canvas.ForceUpdateCanvases();
   switch(current.kind){case "derramado":BuildMop();break;case "freezer_sorvete":case "geladeira_bebidas":BuildWiring(current.kind);break;case "etiqueta":BuildTag();break;default:BuildBulb();break;}
  }
  void Close(){StopAllCoroutines();Clear();window.SetActive(false);current=null;}
  void Clear(){foreach(var o in scene)if(o)Destroy(o);scene.Clear();wires.Clear();wireLayer=null;if(hint)Destroy(hint);hint=null;}
  T Keep<T>(T c) where T:Component{scene.Add(c.gameObject);return c;}
  static Vector2 Mid=>new Vector2(.5f,.5f);
  Vector2 P(float x,float y)=>new Vector2((x-.5f)*stage.rect.width,(y-.5f)*stage.rect.height);
  Vector2 At(RectTransform target)=>U.LocalOf(stage,target);
  Image Place(string name,string sprite,float height,Vector2 at){var img=Keep(U.Art(stage,name,sprite,Mid,height));img.rectTransform.anchoredPosition=at;return img;}
  void Hint(Func<Vector2> from,Func<Vector2> to,bool tap=false){if(hint)Destroy(hint);hint=U.Hint(this,stage,from,to,tap);}
  void StopHint(){if(hint)Destroy(hint);hint=null;}
  void Complete(Vector2 at){
   if(done)return;done=true;StopHint();Play(ding);
   bridge.Command("fixIncident","[\""+current.id+"\"]");
   U.Sparkles(this,stage,at,12,220);
   var star=Keep(U.Icon(stage,"Done","Icons/success",Mid,new Vector2(200,200)));star.rectTransform.anchoredPosition=at+new Vector2(0,40);star.rectTransform.localScale=Vector3.zero;StartCoroutine(U.Scale(star.rectTransform,Vector3.one,.45f,true));
   closeAt=Time.unscaledTime+1.6f;
  }

  // Spill: scrub the puddle with the mop (drag the mop head back and forth over it) until it is dry.
  void BuildMop(){
   var fallen=Keep(U.Icon(stage,"Fallen product",$"Products/product-{current.productId:000}",Mid,new Vector2(130,130)));fallen.rectTransform.anchoredPosition=P(.62f,.6f);fallen.rectTransform.localRotation=Quaternion.Euler(0,0,78);
   var puddle=Place("Puddle","puddle",340,P(.47f,.42f));
   Place("Sign","wet_sign",230,P(.13f,.44f));
   Place("Bucket","bucket",180,P(.87f,.2f));
   var mop=Place("Mop","mop",380,P(.84f,.52f));var mr=mop.rectTransform;mr.pivot=new Vector2(.5f,.12f);mr.anchoredPosition=P(.84f,.36f);
   float dirt=1;var drag=U.Drag(mop);var home=mr.anchoredPosition;drag.SetHome(home);Vector2 last=home;
   drag.Setup(new[]{puddle.rectTransform},_=>false,null,()=>{StopHint();last=mr.anchoredPosition;});
   drag.Moved=_=>{
    if(done)return;var head=mr.anchoredPosition;var c=puddle.rectTransform.anchoredPosition;var size=puddle.rectTransform.sizeDelta*puddle.rectTransform.localScale.x*.5f;
    var d=new Vector2((head.x-c.x)/Mathf.Max(1,size.x),(head.y-c.y)/Mathf.Max(1,size.y));float moved=(head-last).magnitude;last=head;
    mr.localRotation=Quaternion.Euler(0,0,Mathf.Clamp((head.x-c.x)*-.03f,-14,14));
    if(d.sqrMagnitude>1.3f||moved<2)return;
    dirt-=moved/4200f;if(UnityEngine.Random.value<.4f)Play(scrub,UnityEngine.Random.Range(.8f,1.3f));
    float k=Mathf.Clamp01(dirt);puddle.rectTransform.localScale=Vector3.one*(.3f+.7f*k);puddle.color=new Color(1,1,1,.25f+.75f*k);
    if(UnityEngine.Random.value<.3f)StartCoroutine(Bubble(head+UnityEngine.Random.insideUnitCircle*50));
    if(dirt<=0){drag.Locked=true;StartCoroutine(Dry(puddle,fallen,mr,home));}
   };
   Hint(()=>mr.anchoredPosition,()=>puddle.rectTransform.anchoredPosition);
  }
  IEnumerator Bubble(Vector2 at){
   var b=Keep(U.Art(stage,"Foam","soap_bubble",Mid,UnityEngine.Random.Range(34,64)));b.rectTransform.anchoredPosition=at;b.rectTransform.localScale=Vector3.zero;
   yield return U.Scale(b.rectTransform,Vector3.one,.2f,true);StartCoroutine(U.Move(b.rectTransform,at+new Vector2(UnityEngine.Random.Range(-20,20),50),.8f));yield return U.Fade(b,0,.8f);if(b)Destroy(b.gameObject);
  }
  IEnumerator Dry(Image puddle,Image fallen,RectTransform mop,Vector2 home){
   yield return U.Fade(puddle,0,.4f);StartCoroutine(U.Move(mop,home,.4f,true));mop.localRotation=Quaternion.identity;
   // The fallen product is put back on its feet and floats away to the shelf.
   StartCoroutine(U.Rotate(fallen.rectTransform,0,.3f));StartCoroutine(U.Move(fallen.rectTransform,fallen.rectTransform.anchoredPosition+new Vector2(0,260),.6f));StartCoroutine(U.Fade(fallen,0,.6f));
   Complete(puddle.rectTransform.anchoredPosition);
  }

  // Cooler short circuit (ice cream chest freezer or upright drinks fridge): a small wiring puzzle,
  // shuffled every time.
  //  1. The breaker is on and the cut wires spark: switch it off.
  //  2. Drag the wire kit (it costs coins) into the box: each cut wire gets a new plug.
  //  3. The taped diagram says which colour goes to which terminal (A–E); terminals, wire order and
  //     colours are random. A wrong terminal sparks and the plug jumps back.
  //  4. Switch the breaker back on: the cooler starts, frost and cold light come back.
  static bool IsCooler(string kind)=>kind=="freezer_sorvete"||kind=="geladeira_bebidas";
  static readonly string[] WireHex={"E53935","1E88E5","FDD835","43A047","FB8C00","8E24AA"};
  sealed class Wire {
   public Color color;public string letter;public Vector2 anchor,stub;public RectTransform plug,soot;public Image[] segments;public bool plugged,connected;public CheckoutDragToken drag;public Vector2 home;
  }
  readonly List<Wire> wires=new List<Wire>();RectTransform wireLayer;
  AudioClip zap;

  void BuildWiring(string kind){
   zap??=U.Noise(.16f,.4f);wires.Clear();
   bool freezer=kind=="freezer_sorvete";int count=freezer?4:5;
   // The appliance on the left, its service grille smoking and sparking.
   var unit=freezer?Place("Unit","chest_freezer",340,P(.17f,.46f)):Place("Unit","drinks_cooler",640,P(.15f,.5f));
   Canvas.ForceUpdateCanvases();
   var grille=U.Over(unit,freezer?"chest_freezer":"drinks_cooler","panel");
   var grilleGlow=U.GlowAt(grille,"Short",new Color(1,.55f,.15f,.6f),Mid,120);
   var coldArea=U.Over(unit,freezer?"chest_freezer":"drinks_cooler",freezer?"lid":"door");
   var cold=U.GlowAt(coldArea,"Cold",new Color(.6f,.9f,1,0),Mid,40);cold.rectTransform.anchorMin=Vector2.zero;cold.rectTransform.anchorMax=Vector2.one;cold.rectTransform.sizeDelta=new Vector2(80,80);
   // The open electrical box.
   var panel=Place("Panel","electric_panel",740,P(.555f,.5f));Canvas.ForceUpdateCanvases();
   var duct=U.Over(panel,"electric_panel","duct");var rail=U.Over(panel,"electric_panel","terminals");var switchSpot=U.Over(panel,"electric_panel","switch");
   Canvas.ForceUpdateCanvases();
   // Random colours, random wire order along the duct, random letters on the terminals, random map.
   var colors=WireHex.OrderBy(_=>UnityEngine.Random.value).Take(count).Select(h=>K.C(h)).ToList();
   var letters=new[]{"A","B","C","D","E"}.Take(count).ToList();
   var mapLetters=letters.OrderBy(_=>UnityEngine.Random.value).ToList();
   var railLetters=letters.OrderBy(_=>UnityEngine.Random.value).ToList();
   var terminals=new Dictionary<string,RectTransform>();
   var railCenter=At(rail);float railWidth=rail.rect.width;
   for(int i=0;i<count;i++){
    float x=railCenter.x-railWidth*.42f+railWidth*.84f*i/Mathf.Max(1,count-1);
    var t=Keep(U.Art(stage,"Terminal "+railLetters[i],"terminal",Mid,92));t.rectTransform.anchoredPosition=new Vector2(x,railCenter.y+30);
    var label=U.Shape(t.rectTransform,"Label","FFF7EC",10,new Vector2(.5f,0),new Vector2(44,36),new Vector2(0,-24));
    var l=U.Label(label.transform,"Letter",K.Headline,26,"2F3A40");U.Stretch(l.rectTransform,Vector2.zero,Vector2.one);l.text=railLetters[i];
    terminals[railLetters[i]]=t.rectTransform;
   }
   wireLayer=CheckoutDesktopCard.Node("Wires",stage);wireLayer.anchorMin=wireLayer.anchorMax=Mid;wireLayer.sizeDelta=Vector2.zero;scene.Add(wireLayer.gameObject);
   var ductCenter=At(duct);float ductWidth=duct.rect.width;
   for(int i=0;i<count;i++){
    var w=new Wire{color=colors[i],letter=mapLetters[i]};
    w.anchor=new Vector2(ductCenter.x-ductWidth*.4f+ductWidth*.8f*i/Mathf.Max(1,count-1),ductCenter.y-duct.rect.height*.35f);
    w.stub=w.anchor+new Vector2(UnityEngine.Random.Range(-18f,18f),-UnityEngine.Random.Range(60f,95f));
    w.segments=new Image[18];
    for(int s=0;s<w.segments.Length;s++){var seg=CheckoutDesktopCard.Image(wireLayer,"Cable",w.color,0);seg.sprite=U.ArtSprite("cable_tile");seg.type=Image.Type.Simple;seg.raycastTarget=false;seg.rectTransform.anchorMin=seg.rectTransform.anchorMax=Mid;w.segments[s]=seg;}
    var soot=U.Art(wireLayer,"Burnt","soot",Mid,46);soot.rectTransform.anchoredPosition=w.stub;w.soot=soot.rectTransform;
    wires.Add(w);
   }
   // The wiring diagram taped to the right, listing each colour and its terminal.
   var card=Place("Diagram","diagram_card",300,P(.9f,.66f));card.rectTransform.localRotation=Quaternion.Euler(0,0,-3);
   var rows=U.Over(card,"diagram_card","rows");
   var ordered=wires.OrderBy(w=>w.letter).ToList();
   for(int i=0;i<ordered.Count;i++){
    float y=1-(i+.5f)/ordered.Count;
    var sw=CheckoutDesktopCard.Image(rows,"Swatch",ordered[i].color,0);sw.sprite=U.ArtSprite("cable_tile");sw.raycastTarget=false;U.At(sw.rectTransform,new Vector2(.32f,y),new Vector2(110,20));
    var badge=U.Shape(rows,"Badge","2F3A40",16,new Vector2(.8f,y),new Vector2(38,34));
    var bl=U.Label(badge.transform,"Letter",K.Headline,24,"FFFFFF");U.Stretch(bl.rectTransform,Vector2.zero,Vector2.one);bl.text=ordered[i].letter;
   }
   // Wire kit with its price.
   bool coinsOk=bridge.State!=null&&bridge.State.coins>=current.fixCost;
   var kit=Place("Kit","wire_kit",150,P(.9f,.22f));var kr=kit.rectTransform;
   var tag=U.Shape(kr,"Price",coinsOk?"FFF7EC":"FCE4DC",18,new Vector2(.5f,0),new Vector2(140,48),new Vector2(0,-6));
   U.Icon(tag.transform,"Coin","Icons/coin",new Vector2(0,.5f),new Vector2(40,40),new Vector2(26,0));
   var price=U.Label(tag.transform,"Value",K.Headline,26,coinsOk?"4A3624":"C0401F");U.Stretch(price.rectTransform,new Vector2(.32f,0),Vector2.one,Vector2.zero,new Vector2(-10,0));price.text=current.fixCost.ToString("0");
   // Breaker: starts on, with the short sparking.
   bool power=true,kitIn=false;int connected=0;
   // On the stage (not inside the panel) so it sits over the cables instead of under them.
   var brk=Keep(U.Art(stage,"Breaker","breaker_on",Mid,Mathf.Max(80,switchSpot.rect.height*.95f)));brk.rectTransform.anchoredPosition=At(switchSpot);
   StartCoroutine(ShortCircuit(grille,()=>power&&!done));
   Hint(()=>At(brk.rectTransform),()=>Vector2.zero,true);
   U.Tap(brk,()=>{
    if(done)return;StopHint();Play(click,.8f);StartCoroutine(U.Pop(brk.rectTransform,1.1f,.2f));
    if(power){
     power=false;U.SetArt(brk,"breaker_off");Play(thud,1.4f);StartCoroutine(U.Fade(grilleGlow,0,.3f));
     if(!kitIn)Hint(()=>kr.anchoredPosition,()=>At(panel.rectTransform));
     return;
    }
    if(connected<count){ // Not ready: it trips right back.
     U.SetArt(brk,"breaker_on");Zap(At(brk.rectTransform),1.2f);StartCoroutine(TripBack(brk));return;
    }
    power=true;U.SetArt(brk,"breaker_on");StartCoroutine(PowerUp(brk,cold,coldArea));
   });
   var kitDrag=U.Drag(kit);kitDrag.SetHome(kr.anchoredPosition);
   kitDrag.Setup(new[]{panel.rectTransform},_=>{
    StopHint();
    if(!coinsOk){Play(buzz);StartCoroutine(U.Shake(tag.rectTransform,.4f));return false;}
    if(power){Zap(At(panel.rectTransform),1f);Hint(()=>At(brk.rectTransform),()=>Vector2.zero,true);return false;}
    kitDrag.Locked=true;kitIn=true;StartCoroutine(FitPlugs());return true;},()=>Play(thud),StopHint);
   IEnumerator FitPlugs(){
    StartCoroutine(U.Scale(kr,Vector3.one*.3f,.3f));yield return U.Move(kr,At(panel.rectTransform),.3f);kit.gameObject.SetActive(false);Play(clank,1.2f);
    foreach(var w in wires){
     StartCoroutine(U.Fade(w.soot.GetComponent<Image>(),0,.3f));
     w.home=w.stub+new Vector2(UnityEngine.Random.Range(-40f,40f),-UnityEngine.Random.Range(120f,200f));
     w.plug=Plug(w);w.plug.anchoredPosition=w.stub;w.plugged=true;StartCoroutine(U.Move(w.plug,w.home,.4f,true));Play(click,1+wires.IndexOf(w)*.1f);
     var wire=w;w.drag=U.Drag(w.plug.GetComponent<Image>());w.drag.SetHome(w.home);
     w.drag.Setup(terminals.Values.ToArray(),target=>{
      StopHint();
      if(power){Zap(At(target),1.2f);return false;}
      var letter=terminals.First(p=>p.Value==target).Key;
      if(wires.Any(o=>o!=wire&&o.connected&&o.letter==letter)){Play(buzz);return false;}
      if(letter!=wire.letter){Zap(At(target),.8f);StartCoroutine(U.Shake(target,.3f,8));return false;}
      wire.drag.Locked=true;wire.connected=true;connected++;StartCoroutine(Seat(wire,target));
      if(connected==count)Hint(()=>At(brk.rectTransform),()=>Vector2.zero,true);
      return true;},()=>Play(click,.6f),StopHint);
     yield return new WaitForSecondsRealtime(.08f);
    }
    Hint(()=>{var next=wires.FirstOrDefault(x=>!x.connected);return next!=null&&next.plug?At(next.plug):railCenter;},()=>railCenter);
   }
  }
  RectTransform Plug(Wire w){
   var holder=Keep(CheckoutDesktopCard.Image(stage,"Plug",new Color(1,1,1,0),0));holder.raycastTarget=true;U.At(holder.rectTransform,Mid,new Vector2(50,100));
   var pin=U.Art(holder.transform,"Pin","plug_pin",Mid,100);
   var sleeve=U.Art(holder.transform,"Sleeve","plug_sleeve",Mid,100);sleeve.color=Color.Lerp(w.color,Color.white,.15f);
   return holder.rectTransform;
  }
  IEnumerator Seat(Wire w,RectTransform terminal){
   // The pin drops into the terminal, the screw turns and a green light comes on.
   var top=At(terminal)+new Vector2(0,terminal.rect.height*.42f+w.plug.rect.height*.36f);
   yield return U.Move(w.plug,top+new Vector2(0,18),.12f);yield return U.Move(w.plug,top,.08f);Play(clank,1.5f);StartCoroutine(U.Pop(terminal,1.08f,.2f));
   var led=U.GlowAt(terminal,"Ok",new Color(.4f,1,.4f,.9f),new Vector2(.5f,1),50,new Vector2(0,10));led.rectTransform.localScale=Vector3.zero;StartCoroutine(U.Scale(led.rectTransform,Vector3.one,.25f,true));
  }
  IEnumerator TripBack(Image brk){Play(buzz);StartCoroutine(U.Shake(brk.rectTransform,.3f,8));yield return new WaitForSecondsRealtime(.35f);if(brk)U.SetArt(brk,"breaker_off");}
  IEnumerator PowerUp(Image brk,Image cold,RectTransform coldArea){
   Play(hum,1.3f);
   foreach(var w in wires)if(w.plug)StartCoroutine(U.Pop(w.plug,1.12f,.2f));
   yield return new WaitForSecondsRealtime(.25f);
   StartCoroutine(U.Fade(cold,.75f,.6f));
   for(int i=0;i<6;i++){StartCoroutine(Frost(At(coldArea)+new Vector2(UnityEngine.Random.Range(-100f,100f),UnityEngine.Random.Range(-40f,40f))));yield return new WaitForSecondsRealtime(.1f);}
   Complete(At(coldArea));
  }
  IEnumerator Frost(Vector2 at){
   var puff=Keep(U.Art(stage,"Frost","soap_bubble",Mid,UnityEngine.Random.Range(50,90)));puff.color=new Color(.85f,.95f,1,.9f);puff.rectTransform.anchoredPosition=at;
   StartCoroutine(U.Move(puff.rectTransform,at+new Vector2(UnityEngine.Random.Range(-30,30),150),1.2f));yield return U.Fade(puff,0,1.2f);if(puff)Destroy(puff.gameObject);
  }
  // A spark burst with a crackle.
  void Zap(Vector2 at,float strength){
   Play(zap,UnityEngine.Random.Range(1.4f,1.9f));Play(buzz,1.6f);
   var flash=Keep(U.GlowAt(stage,"Flash",new Color(.7f,.9f,1,.9f),Mid,160*strength,at));StartCoroutine(U.Fade(flash,0,.25f));Destroy(flash.gameObject,.3f);
   for(int i=0;i<5;i++){var s=Keep(U.Art(stage,"Spark","sparkle",Mid,UnityEngine.Random.Range(30,60)*strength));s.color=new Color(1,.9f,.45f);s.rectTransform.anchoredPosition=at;StartCoroutine(U.Move(s.rectTransform,at+UnityEngine.Random.insideUnitCircle*90*strength,.25f));StartCoroutine(U.Fade(s,0,.3f));Destroy(s.gameObject,.35f);}
  }
  // While the power is on, the cut wire ends and the appliance grille keep sparking.
  IEnumerator ShortCircuit(RectTransform grille,Func<bool> on){
   while(on()){
    yield return new WaitForSecondsRealtime(UnityEngine.Random.Range(.35f,.9f));if(!on())yield break;
    var w=wires.Count>0?wires[UnityEngine.Random.Range(0,wires.Count)]:null;
    if(w!=null&&!w.plugged)Zap(w.stub,.55f);
    if(grille&&UnityEngine.Random.value<.5f)Zap(At(grille),.45f);
   }
  }
  // Cables follow a soft S from the duct to the plug (or to the burnt stub before the kit).
  void DrawWires(){
   if(wireLayer==null||!window.activeSelf)return;
   foreach(var w in wires){
    Vector2 p0=w.anchor,p1,p2,p3;
    if(!w.plugged||!w.plug){p3=w.stub;p1=p0+new Vector2(0,-25);p2=p3+new Vector2(0,25);}
    else{p3=w.plug.anchoredPosition+new Vector2(0,w.plug.rect.height*.45f*w.plug.localScale.y);p1=p0+new Vector2(0,-150);p2=p3+new Vector2(0,170);}
    var prev=p0;int n=w.segments.Length;
    for(int i=1;i<=n;i++){
     float t=i/(float)n,u=1-t;var pt=u*u*u*p0+3*u*u*t*p1+3*u*t*t*p2+t*t*t*p3;
     var seg=w.segments[i-1].rectTransform;var d=pt-prev;seg.anchoredPosition=(prev+pt)*.5f;seg.sizeDelta=new Vector2(d.magnitude+4,15);seg.localRotation=Quaternion.Euler(0,0,Mathf.Atan2(d.y,d.x)*Mathf.Rad2Deg);prev=pt;
    }
   }
  }

  IEnumerator Smoke(RectTransform bay,Func<bool> on){
   while(bay&&on()){
    var puff=Keep(U.Art(stage,"Smoke","soap_bubble",Mid,UnityEngine.Random.Range(60,110)));puff.color=new Color(.72f,.74f,.76f,.8f);var at=At(bay)+new Vector2(UnityEngine.Random.Range(-120,120),20);puff.rectTransform.anchoredPosition=at;
    StartCoroutine(U.Move(puff.rectTransform,at+new Vector2(UnityEngine.Random.Range(-40,40),260),1.6f));StartCoroutine(U.Fade(puff,0,1.6f));Destroy(puff.gameObject,1.7f);
    yield return new WaitForSecondsRealtime(.35f);
   }
  }
  IEnumerator Blink(Image led,Func<bool> on){while(led&&on()){led.color=new Color(1,.2f,.15f,Mathf.Repeat(Time.unscaledTime,.8f)<.4f?1:.15f);yield return null;}}

  // Wrong tag: drag the tag with the price the system has onto the shelf holder (wrong ones bounce off).
  void BuildTag(){
   var shelf=Place("Shelf","shelf_unit",600,P(.37f,.5f));Canvas.ForceUpdateCanvases();
   var spot=U.Over(shelf,"shelf_unit","spot");var holder=U.Over(shelf,"shelf_unit","holder");Canvas.ForceUpdateCanvases();
   float ps=Mathf.Min(spot.rect.height*.8f,spot.rect.width/3.1f);foreach(var x in new[]{.17f,.5f,.83f})U.Icon(spot,"Product",$"Products/product-{current.productId:000}",new Vector2(x,.42f),Vector2.one*ps);
   long right=(long)Math.Round(current.price);
   // The price the system has, on a POS screen, so the player knows what to pick.
   var pos=Place("System","pos_terminal",200,P(.84f,.78f));var screen=U.Over(pos,"pos_terminal","screen");
   var cap=U.Label(screen,"Caption",K.Label,14,"3F5A33",TextAlignmentOptions.TopLeft);U.Stretch(cap.rectTransform,Vector2.zero,Vector2.one,new Vector2(8,4),new Vector2(-8,-4));cap.text="PREÇO";
   var pt=U.Label(screen,"Price",K.Number,38,"22361A",TextAlignmentOptions.BottomRight);U.Stretch(pt.rectTransform,Vector2.zero,Vector2.one,new Vector2(8,2),new Vector2(-10,-2));pt.text=right.ToString();
   // The wrong red tag hangs loose from the holder.
   var old=Tag(stage,"tag_red",current.tagPrice,78);old.pivot=new Vector2(.5f,1);old.anchoredPosition=At(holder)+new Vector2(0,holder.rect.height*.5f);
   StartCoroutine(Loose(old));
   var prices=new List<long>{right,Math.Max(1,right+UnityEngine.Random.Range(3,9)),Math.Max(1,right-UnityEngine.Random.Range(2,Math.Max(3,(int)right/2)))}.Distinct().OrderBy(_=>UnityEngine.Random.value).ToList();
   var target=CheckoutDesktopCard.Node("Target",holder);U.Stretch(target,Vector2.zero,Vector2.one,new Vector2(-60,-60),new Vector2(60,60));
   RectTransform rightTag=null;
   for(int i=0;i<prices.Count;i++){
    long value=prices[i];var tag=Tag(stage,"tag_yellow",value,88);tag.anchoredPosition=P(.84f,.5f-i*.17f);if(value==right)rightTag=tag;
    var drag=U.Drag(tag.GetComponent<Image>());drag.SetHome(tag.anchoredPosition);
    drag.Setup(new[]{target},_=>{
     StopHint();
     if(value!=right){Play(buzz);StartCoroutine(U.Shake(old,.35f,10));StartCoroutine(Flash(tag.GetComponent<Image>()));return false;}
     drag.Locked=true;Play(click,.8f);StartCoroutine(Replace(old,tag,holder));return true;},()=>Play(click,.6f),StopHint);
   }
   Hint(()=>rightTag?rightTag.anchoredPosition:Vector2.zero,()=>At(holder));
  }
  RectTransform Tag(RectTransform parent,string sprite,double value,float height){
   var img=Keep(U.Art(parent,"Tag "+value,sprite,Mid,height));var area=U.Over(img,sprite,"value");
   var t=U.Label(area,"Price",K.Headline,height*.42f,"2F3A40");U.Stretch(t.rectTransform,Vector2.zero,Vector2.one);t.text=value.ToString("0");t.enableAutoSizing=true;t.fontSizeMin=12;t.fontSizeMax=height*.42f;
   return img.rectTransform;
  }
  IEnumerator Flash(Image img){if(!img)yield break;img.color=new Color(1,.55f,.5f);yield return new WaitForSecondsRealtime(.25f);if(img)img.color=Color.white;}
  IEnumerator Loose(RectTransform tag){while(tag&&!done){tag.localRotation=Quaternion.Euler(0,0,12+Mathf.Sin(Time.unscaledTime*3)*14);yield return null;}}
  IEnumerator Replace(RectTransform old,RectTransform tag,RectTransform holder){
   // The old tag falls off, the new one clicks into the holder.
   StartCoroutine(U.Rotate(old,80,.5f));StartCoroutine(U.Move(old,old.anchoredPosition+new Vector2(-80,-600),.6f));Play(thud,1.3f);
   tag.localRotation=Quaternion.identity;yield return U.Move(tag,At(holder)+new Vector2(0,-tag.rect.height*.22f),.18f);Play(click,1.2f);StartCoroutine(U.Pop(tag,1.15f,.25f));
   yield return new WaitForSecondsRealtime(.35f);Complete(At(holder));
  }

  // Dead bulb: unscrew it (tap), drag a new one into the socket, screw it (tap) and the lights come back.
  void BuildBulb(){
   var lamp=Place("Lamp","pendant_lamp",520,Vector2.zero);lamp.rectTransform.anchoredPosition=new Vector2(P(.42f,0).x,stage.rect.height*.5f-230);Canvas.ForceUpdateCanvases();
   var socket=U.Over(lamp,"pendant_lamp","socket");Canvas.ForceUpdateCanvases();
   var dark=Keep(U.Box(stage,"Dark","000000",0,Vector2.zero,Vector2.one));dark.color=new Color(.05f,.04f,.08f,.72f);
   var glow=Keep(U.GlowAt(stage,"Glow",new Color(1,.9f,.55f,0),Mid,40));
   Vector2 SocketBottom()=>At(socket)-new Vector2(0,socket.rect.height*.4f);
   var old=Place("Old bulb","bulb_dead",150,Vector2.zero);old.rectTransform.pivot=new Vector2(.5f,.03f);old.rectTransform.localRotation=Quaternion.Euler(0,0,180);old.rectTransform.anchoredPosition=SocketBottom();
   Place("Box","bulb_box",170,P(.84f,.2f));
   var bulb=Place("New bulb","bulb_off",130,P(.84f,.42f));var br=bulb.rectTransform;
   bool removed=false;int oldTurns=0;
   U.Tap(old,()=>{
    if(removed||done)return;StopHint();oldTurns++;Play(click,1+oldTurns*.1f);StartCoroutine(U.Rotate(old.rectTransform,180+oldTurns*55,.15f));
    if(oldTurns==3){removed=true;StartCoroutine(Fall(old));Hint(()=>br.anchoredPosition,SocketBottom);}
   });
   StartCoroutine(Flicker(old,()=>!removed));
   var drag=U.Drag(bulb);drag.SetHome(br.anchoredPosition);
   drag.Setup(new[]{socket,lamp.rectTransform},_=>{
    StopHint();
    if(!removed){Play(buzz);StartCoroutine(U.Shake(old.rectTransform,.3f,8));return false;}
    drag.Locked=true;StartCoroutine(Mount());return true;},()=>Play(click,.6f),StopHint);
   Hint(()=>At(old.rectTransform),()=>Vector2.zero,true);
   IEnumerator Mount(){
    br.pivot=new Vector2(.5f,.03f);br.localRotation=Quaternion.Euler(0,0,180);yield return U.Move(br,SocketBottom(),.2f);Play(click,1.1f);
    int turns=0;
    Hint(()=>br.anchoredPosition-new Vector2(0,60),()=>Vector2.zero,true);
    U.Tap(bulb,()=>{if(turns>=3||done)return;StopHint();turns++;Play(click,1.2f+turns*.1f);StartCoroutine(U.Rotate(br,180-turns*70,.15f));if(turns==3)StartCoroutine(Light());});
   }
   IEnumerator Light(){
    Play(hum,1.6f);br.localRotation=Quaternion.Euler(0,0,180);
    for(int i=0;i<3;i++){U.SetArt(bulb,"bulb_on");yield return new WaitForSecondsRealtime(.07f);U.SetArt(bulb,"bulb_off");yield return new WaitForSecondsRealtime(.09f);}
    U.SetArt(bulb,"bulb_on");glow.rectTransform.anchoredPosition=br.anchoredPosition-new Vector2(0,70);
    StartCoroutine(U.Scale(glow.rectTransform,Vector3.one*22,.5f));StartCoroutine(U.Fade(glow,.6f,.5f));StartCoroutine(U.Fade(dark,0,.7f));
    yield return new WaitForSecondsRealtime(.5f);Complete(br.anchoredPosition-new Vector2(0,80));
   }
  }
  IEnumerator Fall(Image img){var r=img.rectTransform;StartCoroutine(U.Rotate(r,300,.6f));yield return U.Move(r,r.anchoredPosition+new Vector2(60,-700),.6f);Play(thud,1.8f);}
  IEnumerator Flicker(Image img,Func<bool> on){while(img&&on()){yield return new WaitForSecondsRealtime(UnityEngine.Random.Range(.6f,1.6f));if(!img||!on())yield break;U.SetArt(img,"bulb_on");Play(click,.5f);yield return new WaitForSecondsRealtime(.05f);if(img)U.SetArt(img,"bulb_dead");}}
 }
}
