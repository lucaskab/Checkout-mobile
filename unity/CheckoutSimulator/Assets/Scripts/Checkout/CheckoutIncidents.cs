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
  RectTransform root,stage;GameObject window,fab,hint;TextMeshProUGUI title,fabText;Image backdrop;AudioSource sound;
  IncidentEntry current;bool done;float closeAt;readonly List<GameObject> scene=new List<GameObject>();

  public void Initialize(CheckoutBridge owner,CheckoutMap projection){
   Instance=this;bridge=owner;map=projection;
   sound=gameObject.AddComponent<AudioSource>();sound.playOnAwake=false;sound.volume=.55f;
   root=U.Canvas(transform,"CheckoutIncidentGame",81);
   BuildFab();
   stage=U.GameWindow(root,"floor_backdrop",out window,out title,out backdrop,Close);
   window.SetActive(false);
  }
  void Play(string clip,float pitch=1,float volume=1){var c=U.Sfx(clip);if(!c)return;sound.pitch=pitch;sound.PlayOneShot(c,volume);}

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

  static string IconFor(string kind)=>kind=="derramado"||kind=="sujeira"?"broom":kind=="freezer_sorvete"?"freezer":kind=="geladeira_bebidas"?"refrigerator":kind=="etiqueta"?"price-tag":"light";
  static string TitleFor(string kind)=>kind=="derramado"?"Limpar o chão":kind=="sujeira"?"Varrer o chão sujo":kind=="freezer_sorvete"?"Freezer de sorvete em curto":kind=="geladeira_bebidas"?"Geladeira de bebidas em curto":kind=="etiqueta"?"Trocar a etiqueta":"Trocar a lâmpada";

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
  Vector3 Spot(string shelfId){var p=map.Approach(shelfId);return new Vector3(p.x,.76f,p.z);} // In front of the shelf, wherever it was placed.
  Transform Marker(IncidentEntry incident){
   var rootT=new GameObject("Incident · "+incident.kind).transform;rootT.SetParent(transform);rootT.position=Spot(incident.shelfId);
   // Modelled props from the Staff Kit (spill with a tipped bottle, wet-floor sign, dirt and litter).
   Transform Prop(string template,Vector3 at,float yaw){var t=map.StaffTemplate(template);if(!t)return null;var go=Instantiate(t.gameObject,rootT,false);go.name=template;go.SetActive(true);go.transform.localPosition=at;go.transform.localRotation=Quaternion.Euler(0,yaw,0);return go.transform;}
   float spin=Mathf.Abs(incident.id.GetHashCode()%360);
   if(incident.kind=="derramado"&&Prop("staff-puddle",new Vector3(0,-.015f,0),spin)){Prop("staff-wetsign",new Vector3(.95f,-.02f,.15f),spin*.3f+20);}
   else if(incident.kind=="sujeira"){
    // Saves from before floor messes were kept apart: step aside from a spill in front of the same shelf.
    bool spill=(bridge.State?.incidents??Array.Empty<IncidentEntry>()).Any(i=>i.id!=incident.id&&i.shelfId==incident.shelfId&&i.kind=="derramado");
    var dirt=Prop(spin>180?"staff-dirt-a":"staff-dirt-b",new Vector3(spill?1.1f:0,-.015f,spill?.4f:0),spin);if(dirt)dirt.localScale=Vector3.one*1.45f;}
   else switch(incident.kind){
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
  IEnumerator Vanish(Transform t){Play("success",1.3f);for(float s=1;s>0;s-=Time.deltaTime/.35f){if(!t)yield break;t.localScale=Vector3.one*s;yield return null;}if(t)Destroy(t.gameObject);}
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
   U.SetArt(backdrop,current.kind=="derramado"||current.kind=="sujeira"?"floor_backdrop":current.kind=="lampada"?"ceiling_backdrop":"wall_backdrop");
   Canvas.ForceUpdateCanvases();
   switch(current.kind){case "derramado":BuildCleaning(false);break;case "sujeira":BuildCleaning(true);break;case "freezer_sorvete":case "geladeira_bebidas":BuildWiring(current.kind);break;case "etiqueta":BuildTag();break;default:BuildBulb();break;}
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
   if(done)return;done=true;StopHint();Play("success");
   if(taskText){taskText.text="Pronto! Tudo certo.";TaskProgress(1);}
   bridge.Command("fixIncident","[\""+current.id+"\"]");
   U.Sparkles(this,stage,at,12,220);
   var star=Keep(U.Icon(stage,"Done","Icons/success",Mid,new Vector2(200,200)));star.rectTransform.anchoredPosition=at+new Vector2(0,40);star.rectTransform.localScale=Vector3.zero;StartCoroutine(U.Scale(star.rectTransform,Vector3.one,.45f,true));
   closeAt=Time.unscaledTime+1.6f;
  }

  // ------------------------------------------------------------------ cleaning (spills and dirt)
  // Every mess is one of a few different jobs, picked from the incident id so it changes each time:
  //  spill:  a puddle in several blobs to mop, or a broken bottle (pick up every shard into the dustpan, then mop);
  //  dirt:   muddy footprints to mop one by one, litter to throw in the bin, or dust piles to sweep into the dustpan.
  // The floor is the market's own cream tiles with the navy kick plate; a navy banner says what to do and counts.
  TextMeshProUGUI taskText;Image taskBar;int taskDone,taskTotal;
  sealed class MessSpot {public Image img;public float dirt=1,baseAlpha=1;public Vector3 baseScale=Vector3.one;public float radius;}
  GameObject bannerGo;
  void Banner(string text,int total){
   taskDone=0;taskTotal=total;if(bannerGo)Destroy(bannerGo);
   var edge=Keep(U.Shape(stage,"Task",Gold,26,new Vector2(.5f,1),new Vector2(640,78),new Vector2(0,-96)));
   bannerGo=edge.gameObject;
   var face=U.Box(edge.transform,"Face",Navy,24,Vector2.zero,Vector2.one);face.rectTransform.offsetMin=new Vector2(3,3);face.rectTransform.offsetMax=new Vector2(-3,-3);
   taskText=U.Label(face.transform,"Text",K.Label,24,"FFFFFF");U.Stretch(taskText.rectTransform,new Vector2(0,.3f),Vector2.one,new Vector2(18,0),new Vector2(-18,-4));
   var track=U.Box(face.transform,"Track","0B1322",8,Vector2.zero,new Vector2(1,0));track.rectTransform.offsetMin=new Vector2(22,10);track.rectTransform.offsetMax=new Vector2(-22,24);
   taskBar=U.Box(track.transform,"Fill",Gold,8,Vector2.zero,new Vector2(0,1));
   SetTask(text);
  }
  void SetTask(string text){if(taskText)taskText.text=taskTotal>1?$"{text}  <color=#E8B04A>{taskDone}/{taskTotal}</color>":text;}
  void TaskProgress(float k){if(!taskBar)return;taskBar.rectTransform.anchorMax=new Vector2(Mathf.Clamp01(k),1);taskBar.color=k>=1?K.C("5DA637"):K.C(Gold);}
  const string Navy="22345E",Gold="E8B04A";
  static int Variant(string id,int count){unchecked{int h=17;foreach(var c in id??"")h=h*31+c;return Mathf.Abs(h)%count;}}

  void BuildCleaning(bool dirt){
   if(!dirt){if(Variant(current.id,2)==0)BuildPuddle();else BuildBrokenBottle();}
   else switch(Variant(current.id,3)){case 0:BuildFootprints();break;case 1:BuildLitter();break;default:BuildDust();break;}
  }

  // A mop the player drags; scrubbing over dirty spots cleans them. Smooth: the head lags the pointer a little,
  // foam and sounds are rate limited, spots fade gradually.
  Image mop;RectTransform mopRect;Vector2 mopHome;CheckoutDragToken mopDrag;float nextFoam,nextScrub;int foamAlive;
  void Mop(Vector2 at,List<MessSpot> spots,Action done,string doneText){
   Place("Bucket","bucket",170,P(.9f,.18f));
   mop=Place("Mop","mop",360,at);mopRect=mop.rectTransform;mopRect.pivot=new Vector2(.5f,.12f);mopRect.anchoredPosition=at;mopHome=at;
   mopDrag=U.Drag(mop);mopDrag.SetHome(mopHome);
   Vector2 last=at;float lean=0;
   mopDrag.Setup(spots.Select(s=>s.img.rectTransform).ToArray(),_=>false,null,()=>{StopHint();last=mopRect.anchoredPosition;Play("pickup",.8f,.5f);});
   mopDrag.Moved=_=>{
    if(done==null)return;var head=mopRect.anchoredPosition;float moved=(head-last).magnitude;var dir=head-last;last=head;
    lean=Mathf.Lerp(lean,Mathf.Clamp(-dir.x*.6f,-16,16),.25f);mopRect.localRotation=Quaternion.Euler(0,0,lean);
    if(moved<1.5f)return;
    bool any=false;
    foreach(var s in spots){
     if(s.dirt<=0||!s.img)continue;
     var c=s.img.rectTransform.anchoredPosition;if((head-c).magnitude>s.radius)continue;
     any=true;s.dirt=Mathf.Max(0,s.dirt-moved/2600f);
     float k=s.dirt;s.img.color=new Color(s.img.color.r,s.img.color.g,s.img.color.b,s.baseAlpha*(.12f+.88f*k));s.img.rectTransform.localScale=s.baseScale*(.55f+.45f*k);
     if(s.dirt<=0){taskDone++;Play("bubble_"+taskDone%3,1.1f);StartCoroutine(Shine(c));StartCoroutine(U.Fade(s.img,0,.35f));}
    }
    if(any){
     if(Time.unscaledTime>nextScrub){nextScrub=Time.unscaledTime+.16f;Play("scrub_"+UnityEngine.Random.Range(0,3),UnityEngine.Random.Range(.9f,1.1f),.8f);}
     if(Time.unscaledTime>nextFoam&&foamAlive<10){nextFoam=Time.unscaledTime+.07f;StartCoroutine(Foam(head+UnityEngine.Random.insideUnitCircle*40));}
    }
    float left=spots.Sum(s=>s.dirt)/Mathf.Max(1,spots.Count);TaskProgress(1-left);SetTask(doneText);
    if(spots.All(s=>s.dirt<=0)){var d=done;done=null;mopDrag.Locked=true;StartCoroutine(PutMopBack());d();}
   };
   var first=spots.FirstOrDefault(s=>s.dirt>0);
   Hint(()=>mopRect.anchoredPosition,()=>first!=null&&first.img?first.img.rectTransform.anchoredPosition:Vector2.zero);
  }
  IEnumerator PutMopBack(){yield return new WaitForSecondsRealtime(.2f);if(!mopRect)yield break;StartCoroutine(U.Rotate(mopRect,0,.3f));yield return U.Move(mopRect,mopHome,.4f,true);}
  IEnumerator Foam(Vector2 at){
   foamAlive++;
   var b=Keep(U.Art(stage,"Foam","soap_bubble",Mid,UnityEngine.Random.Range(30,58)));b.raycastTarget=false;b.rectTransform.anchoredPosition=at;b.rectTransform.localScale=Vector3.zero;
   yield return U.Scale(b.rectTransform,Vector3.one,.18f,true);StartCoroutine(U.Move(b.rectTransform,at+new Vector2(UnityEngine.Random.Range(-18,18),40),.7f));yield return U.Fade(b,0,.7f);
   foamAlive--;if(b){scene.Remove(b.gameObject);Destroy(b.gameObject);}
  }
  IEnumerator Shine(Vector2 at){
   var s=Keep(U.Art(stage,"Shine","sparkle",Mid,90));s.raycastTarget=false;s.rectTransform.anchoredPosition=at;s.rectTransform.localScale=Vector3.zero;
   yield return U.Scale(s.rectTransform,Vector3.one,.2f,true);yield return U.Fade(s,0,.4f);if(s)Destroy(s.gameObject);
  }
  MessSpot MakeSpot(string sprite,float height,Vector2 at,float rot,Color tint,float radius){
   var img=Place("Spot",sprite,height,at);img.color=tint;img.rectTransform.localRotation=Quaternion.Euler(0,0,rot);img.raycastTarget=false;
   return new MessSpot{img=img,baseAlpha=tint.a,baseScale=Vector3.one,radius=radius};
  }

  // Spill A: a puddle in several blobs, the fallen product and the wet-floor sign.
  void BuildPuddle(){
   var fallen=Keep(U.Icon(stage,"Fallen product",$"Products/product-{current.productId:000}",Mid,new Vector2(130,130)));fallen.rectTransform.anchoredPosition=P(.6f,.62f);fallen.rectTransform.localRotation=Quaternion.Euler(0,0,78);
   Place("Sign","wet_sign",230,P(.12f,.44f));
   var spots=new List<MessSpot>{
    MakeSpot("puddle",300,P(.42f,.44f),0,Color.white,190),
    MakeSpot("puddle",170,P(.6f,.33f),40,Color.white,110),
    MakeSpot("puddle",130,P(.3f,.28f),-30,Color.white,90),
   };
   Banner("Passe o esfregão na poça",spots.Count);
   Mop(P(.84f,.36f),spots,()=>{StartCoroutine(U.Rotate(fallen.rectTransform,0,.3f));StartCoroutine(U.Move(fallen.rectTransform,fallen.rectTransform.anchoredPosition+new Vector2(0,260),.6f));StartCoroutine(U.Fade(fallen,0,.6f));Complete(P(.45f,.4f));},"Passe o esfregão na poça");
  }

  // Spill B: a broken bottle. Pick up each shard (drag it to the dustpan), then mop the drink.
  void BuildBrokenBottle(){
   var juice=new Color(.85f,1f,.9f,.95f); // spilled soda: clear with a green hint
   var puddle=MakeSpot("puddle",260,P(.42f,.42f),10,juice,170);
   var neck=Place("Neck","bottle_neck",170,P(.52f,.55f));neck.rectTransform.localRotation=Quaternion.Euler(0,0,-25);
   var pan=Place("Dustpan","dustpan",210,P(.88f,.62f));var mouth=U.Over(pan,"dustpan","mouth");
   Place("Sign","wet_sign",210,P(.1f,.46f));
   var pieces=new List<RectTransform>();
   int n=UnityEngine.Random.Range(6,9);
   for(int i=0;i<n+1;i++){
    bool isNeck=i==n;var piece=isNeck?neck:Place("Shard","glass_shard_"+i%3,UnityEngine.Random.Range(70,110),P(.42f,.42f)+UnityEngine.Random.insideUnitCircle*new Vector2(300,150));
    if(!isNeck)piece.rectTransform.localRotation=Quaternion.Euler(0,0,UnityEngine.Random.Range(0,360));
    var r=piece.rectTransform;pieces.Add(r);
    var drag=U.Drag(piece);drag.SetHome(r.anchoredPosition);
    drag.Setup(new[]{mouth,pan.rectTransform},_=>{
     drag.Locked=true;taskDone++;Play("glass_"+taskDone%3,1,.9f);StartCoroutine(U.Pop(pan.rectTransform,1.06f,.2f));
     StartCoroutine(U.Scale(r,Vector3.one*.5f,.2f));StartCoroutine(U.Move(r,At(mouth)+UnityEngine.Random.insideUnitCircle*30,.2f));
     TaskProgress(taskDone/(float)taskTotal*.6f);SetTask("Recolha os cacos de vidro");
     if(taskDone>=taskTotal)StartCoroutine(ShardsDone());
     return true;},()=>Play("glass_1",.8f,.6f),()=>{StopHint();Play("glass_"+UnityEngine.Random.Range(0,3),1.2f,.5f);});
   }
   Banner("Recolha os cacos de vidro",pieces.Count);
   Hint(()=>{var p=pieces.FirstOrDefault(x=>x&&!x.GetComponent<CheckoutDragToken>().Locked);return p?p.anchoredPosition:Vector2.zero;},()=>At(mouth));
   IEnumerator ShardsDone(){
    yield return new WaitForSecondsRealtime(.3f);Play("glass_dump");StartCoroutine(U.Shake(pan.rectTransform,.3f,6));
    foreach(var p in pieces)if(p)StartCoroutine(U.Fade(p.GetComponent<Image>(),0,.4f));
    yield return new WaitForSecondsRealtime(.4f);
    Banner("Agora passe o esfregão no refrigerante",1);TaskProgress(.6f);
    Mop(P(.84f,.3f),new List<MessSpot>{puddle},()=>Complete(P(.42f,.42f)),"Agora passe o esfregão no refrigerante");
   }
  }

  // Dirt A: a trail of muddy footprints, each one mopped away.
  void BuildFootprints(){
   var spots=new List<MessSpot>();int n=UnityEngine.Random.Range(5,8);
   var from=P(.08f,.25f);var to=P(.72f,.7f);var dir=(to-from).normalized;float yaw=Mathf.Atan2(dir.y,dir.x)*Mathf.Rad2Deg-90;
   for(int i=0;i<n;i++){
    var at=Vector2.Lerp(from,to,(i+.5f)/n)+new Vector2(-dir.y,dir.x)*(i%2==0?28:-28);
    spots.Add(MakeSpot("footprint",110,at,yaw+UnityEngine.Random.Range(-8,8),new Color(1,1,1,.92f),80));
   }
   Banner("Limpe as pegadas de lama",spots.Count);
   Mop(P(.86f,.34f),spots,()=>Complete(P(.45f,.45f)),"Limpe as pegadas de lama");
  }

  // Dirt B: litter on the floor; throw every piece in the bin.
  void BuildLitter(){
   var bin=Place("Bin","trash_bin",250,P(.86f,.4f));var mouth=U.Over(bin,"trash_bin","mouth");
   string[] kinds={"litter_paper","litter_wrapper","litter_cup","litter_paper","litter_wrapper","litter_cup"};
   int n=UnityEngine.Random.Range(4,7);var pieces=new List<RectTransform>();
   for(int i=0;i<n;i++){
    var k=kinds[(i+Variant(current.id,6))%kinds.Length];
    var img=Place("Litter",k,k=="litter_cup"?135:k=="litter_wrapper"?100:110,P(UnityEngine.Random.Range(.12f,.66f),UnityEngine.Random.Range(.2f,.7f)));
    img.rectTransform.localRotation=Quaternion.Euler(0,0,UnityEngine.Random.Range(-40,40));
    var r=img.rectTransform;pieces.Add(r);
    var drag=U.Drag(img);drag.SetHome(r.anchoredPosition);
    drag.Setup(new[]{mouth,bin.rectTransform},_=>{
     drag.Locked=true;taskDone++;Play("trash",UnityEngine.Random.Range(.9f,1.1f));StartCoroutine(U.Pop(bin.rectTransform,1.07f,.25f));
     StartCoroutine(Drop(r,At(mouth)));TaskProgress(taskDone/(float)taskTotal);SetTask("Jogue o lixo na lixeira");
     if(taskDone>=taskTotal)Complete(At(bin.rectTransform));
     return true;},()=>Play("bonk",1,.5f),()=>{StopHint();Play("pickup");});
   }
   Banner("Jogue o lixo na lixeira",n);
   Hint(()=>{var p=pieces.FirstOrDefault(x=>x&&!x.GetComponent<CheckoutDragToken>().Locked);return p?p.anchoredPosition:Vector2.zero;},()=>At(mouth));
  }
  IEnumerator Drop(RectTransform r,Vector2 mouth){
   var from=r.anchoredPosition;
   for(float t=0;t<1;t+=Time.unscaledDeltaTime/.3f){if(!r)yield break;r.anchoredPosition=Vector2.Lerp(from,mouth,t)+new Vector2(0,Mathf.Sin(t*Mathf.PI)*60);r.localScale=Vector3.one*Mathf.Lerp(1,.3f,t);yield return null;}
   if(r)r.gameObject.SetActive(false);
  }

  // Dirt C: dust piles; drag the broom over a pile to push it along, into the dustpan.
  void BuildDust(){
   var pan=Place("Dustpan","dustpan",230,P(.86f,.3f));var mouth=U.Over(pan,"dustpan","mouth");
   int n=UnityEngine.Random.Range(2,4);var piles=new List<Image>();
   for(int i=0;i<n;i++){var p=Place("Dust","dust_pile",UnityEngine.Random.Range(120,160),P(UnityEngine.Random.Range(.18f,.55f),UnityEngine.Random.Range(.25f,.65f)));p.raycastTarget=false;piles.Add(p);}
   var broom=Place("Broom","broom",330,P(.62f,.6f));var br=broom.rectTransform;br.pivot=new Vector2(.5f,.08f);var home=P(.66f,.5f);br.anchoredPosition=home;
   Banner("Varra a poeira até a pá",n);
   var drag=U.Drag(broom);drag.SetHome(home);Vector2 last=home;float nextSweep=0;
   drag.Setup(new[]{mouth},_=>false,null,()=>{StopHint();last=br.anchoredPosition;});
   drag.Moved=_=>{
    var head=br.anchoredPosition;var delta=head-last;last=head;if(delta.sqrMagnitude<1)return;
    br.localRotation=Quaternion.Euler(0,0,Mathf.Clamp(-delta.x*.8f,-20,20));
    bool pushing=false;
    foreach(var p in piles){
     if(!p||!p.gameObject.activeSelf)continue;var r=p.rectTransform;
     if((r.anchoredPosition-head).magnitude>r.rect.width*.6f)continue;
     // The pile rides just ahead of the bristles in the direction of the stroke.
     pushing=true;var ahead=head+delta.normalized*r.rect.width*.42f;r.anchoredPosition=Vector2.Lerp(r.anchoredPosition+delta*.6f,ahead,.35f);r.localScale=Vector3.one*Mathf.Max(.75f,r.localScale.x*.998f);
     if((r.anchoredPosition-At(mouth)).magnitude<Mathf.Max(70,mouth.rect.width*.6f)){
      p.gameObject.SetActive(false);taskDone++;Play("trash",1.3f,.7f);StartCoroutine(U.Pop(pan.rectTransform,1.08f,.25f));
      StartCoroutine(Puff(At(mouth)));TaskProgress(taskDone/(float)taskTotal);SetTask("Varra a poeira até a pá");
      if(taskDone>=taskTotal){drag.Locked=true;StartCoroutine(U.Move(br,home,.4f,true));Complete(At(pan.rectTransform));}
     }
    }
    if(pushing&&Time.unscaledTime>nextSweep){nextSweep=Time.unscaledTime+.2f;Play("sweep_"+UnityEngine.Random.Range(0,2),UnityEngine.Random.Range(.9f,1.1f),.8f);StartCoroutine(Puff(head+UnityEngine.Random.insideUnitCircle*30));}
   };
   Hint(()=>{var p=piles.FirstOrDefault(x=>x&&x.gameObject.activeSelf);return p?p.rectTransform.anchoredPosition-new Vector2(60,0):Vector2.zero;},()=>At(mouth));
  }
  IEnumerator Puff(Vector2 at){
   var b=Keep(U.Art(stage,"Dust puff","soap_bubble",Mid,UnityEngine.Random.Range(40,70)));b.raycastTarget=false;b.color=new Color(.75f,.72f,.66f,.7f);b.rectTransform.anchoredPosition=at;
   StartCoroutine(U.Move(b.rectTransform,at+new Vector2(UnityEngine.Random.Range(-30,30),50),.6f));yield return U.Fade(b,0,.6f);if(b){scene.Remove(b.gameObject);Destroy(b.gameObject);}
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

  void BuildWiring(string kind){
   wires.Clear();
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
    if(done)return;StopHint();Play("tap",.8f);StartCoroutine(U.Pop(brk.rectTransform,1.1f,.2f));
    if(power){
     power=false;U.SetArt(brk,"breaker_off");Play("bonk",1.4f);StartCoroutine(U.Fade(grilleGlow,0,.3f));
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
    if(!coinsOk){Play("bonk");StartCoroutine(U.Shake(tag.rectTransform,.4f));return false;}
    if(power){Zap(At(panel.rectTransform),1f);Hint(()=>At(brk.rectTransform),()=>Vector2.zero,true);return false;}
    kitDrag.Locked=true;kitIn=true;StartCoroutine(FitPlugs());return true;},()=>Play("bonk"),StopHint);
   IEnumerator FitPlugs(){
    StartCoroutine(U.Scale(kr,Vector3.one*.3f,.3f));yield return U.Move(kr,At(panel.rectTransform),.3f);kit.gameObject.SetActive(false);Play("tap",1.2f);
    foreach(var w in wires){
     StartCoroutine(U.Fade(w.soot.GetComponent<Image>(),0,.3f));
     w.home=w.stub+new Vector2(UnityEngine.Random.Range(-40f,40f),-UnityEngine.Random.Range(120f,200f));
     w.plug=Plug(w);w.plug.anchoredPosition=w.stub;w.plugged=true;StartCoroutine(U.Move(w.plug,w.home,.4f,true));Play("tap",1+wires.IndexOf(w)*.1f);
     var wire=w;w.drag=U.Drag(w.plug.GetComponent<Image>());w.drag.SetHome(w.home);
     w.drag.Setup(terminals.Values.ToArray(),target=>{
      StopHint();
      if(power){Zap(At(target),1.2f);return false;}
      var letter=terminals.First(p=>p.Value==target).Key;
      if(wires.Any(o=>o!=wire&&o.connected&&o.letter==letter)){Play("bonk");return false;}
      if(letter!=wire.letter){Zap(At(target),.8f);StartCoroutine(U.Shake(target,.3f,8));return false;}
      wire.drag.Locked=true;wire.connected=true;connected++;StartCoroutine(Seat(wire,target));
      if(connected==count)Hint(()=>At(brk.rectTransform),()=>Vector2.zero,true);
      return true;},()=>Play("tap",.6f),StopHint);
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
   yield return U.Move(w.plug,top+new Vector2(0,18),.12f);yield return U.Move(w.plug,top,.08f);Play("tap",1.5f);StartCoroutine(U.Pop(terminal,1.08f,.2f));
   var led=U.GlowAt(terminal,"Ok",new Color(.4f,1,.4f,.9f),new Vector2(.5f,1),50,new Vector2(0,10));led.rectTransform.localScale=Vector3.zero;StartCoroutine(U.Scale(led.rectTransform,Vector3.one,.25f,true));
  }
  IEnumerator TripBack(Image brk){Play("bonk");StartCoroutine(U.Shake(brk.rectTransform,.3f,8));yield return new WaitForSecondsRealtime(.35f);if(brk)U.SetArt(brk,"breaker_off");}
  IEnumerator PowerUp(Image brk,Image cold,RectTransform coldArea){
   Play("bulb_on",1.3f);
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
   Play("zap",UnityEngine.Random.Range(1.4f,1.9f));Play("bonk",1.6f);
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
     if(value!=right){Play("bonk");StartCoroutine(U.Shake(old,.35f,10));StartCoroutine(Flash(tag.GetComponent<Image>()));return false;}
     drag.Locked=true;Play("tap",.8f);StartCoroutine(Replace(old,tag,holder));return true;},()=>Play("tap",.6f),StopHint);
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
   StartCoroutine(U.Rotate(old,80,.5f));StartCoroutine(U.Move(old,old.anchoredPosition+new Vector2(-80,-600),.6f));Play("bonk",1.3f);
   tag.localRotation=Quaternion.identity;yield return U.Move(tag,At(holder)+new Vector2(0,-tag.rect.height*.22f),.18f);Play("tap",1.2f);StartCoroutine(U.Pop(tag,1.15f,.25f));
   yield return new WaitForSecondsRealtime(.35f);Complete(At(holder));
  }

  // Dead bulb. The pendant hangs from the ceiling with the socket right under the shade; the bulb hangs in it.
  // Swipe left/right over the bulb to turn it round its own axis (rendered frames, the thread runs out of the
  // socket as it turns) until it drops; drag a new bulb from the box into the socket; swipe the other way to
  // screw it in; the light comes back.
  const int BulbFrames=8,BulbTurns=14;const float SwipeStep=46,ThreadDrop=34;
  void BuildBulb(){
   var lamp=Place("Lamp","pendant_lamp",560,Vector2.zero);lamp.rectTransform.anchoredPosition=new Vector2(P(.4f,0).x,stage.rect.height*.5f-lamp.rectTransform.rect.height*.5f+10);Canvas.ForceUpdateCanvases();
   var socket=U.Over(lamp,"pendant_lamp","socket");Canvas.ForceUpdateCanvases();
   var dark=Keep(U.Box(stage,"Dark","000000",0,Vector2.zero,Vector2.one));dark.color=new Color(.05f,.04f,.08f,.62f);dark.raycastTarget=false;
   var glow=Keep(U.GlowAt(stage,"Glow",new Color(1,.9f,.55f,0),Mid,40));
   // Where the bulb's base sits when fully screwed in: the thread hidden inside the socket.
   Vector2 Seat()=>At(socket)+new Vector2(0,socket.rect.height*.1f);
   // The bulb hangs upside down (base up) from its thread top.
   Image Bulb(string sprite,Vector2 at){var b=Place("Bulb",sprite,190,at);b.rectTransform.pivot=new Vector2(.5f,.4f);b.rectTransform.localRotation=Quaternion.Euler(0,0,180);b.rectTransform.anchoredPosition=at;b.transform.SetSiblingIndex(lamp.transform.GetSiblingIndex());return b;}
   var old=Bulb("bulb_dead_0",Seat());
   Place("Box","bulb_box",170,P(.84f,.2f));
   var fresh=Place("New bulb","bulb_off_0",150,P(.84f,.44f));var fr=fresh.rectTransform;
   Banner("Gire a lâmpada queimada para soltar",1);
   // Swipe area over the old bulb.
   int frame=0,turns=0;bool removed=false;
   var area=Swipe(old.rectTransform,dx=>{
    if(removed||done)return;StopHint();
    int steps=(int)(dx/SwipeStep);if(steps==0)return;
    for(int i=0;i<Mathf.Abs(steps);i++){
     int dir=steps>0?1:-1;frame=(frame+dir+BulbFrames)%BulbFrames;turns=Mathf.Clamp(turns+dir,0,BulbTurns);
     U.SetArt(old,"bulb_dead_"+frame);old.rectTransform.anchoredPosition=Seat()-new Vector2(0,ThreadDrop*turns/(float)BulbTurns);
     Play("twist_"+(turns%2),1+turns*.02f,.8f);
    }
    TaskProgress(turns/(float)BulbTurns*.5f);
    if(turns>=BulbTurns){removed=true;taskDone=1;StartCoroutine(Fall(old));StartCoroutine(NextStep());}
    return;
   },SwipeStep);
   StartCoroutine(Flicker(old,()=>!removed));
   Hint(()=>At(old.rectTransform)+new Vector2(-70,0),()=>At(old.rectTransform)+new Vector2(70,0));
   IEnumerator NextStep(){
    yield return new WaitForSecondsRealtime(.5f);
    Banner("Coloque a lâmpada nova no bocal",1);TaskProgress(.5f);
    var drag=U.Drag(fresh);drag.SetHome(fr.anchoredPosition);
    drag.Setup(new[]{socket,lamp.rectTransform},_=>{StopHint();drag.Locked=true;StartCoroutine(Mount());return true;},()=>Play("bonk",1,.5f),()=>{StopHint();Play("pickup");});
    Hint(()=>fr.anchoredPosition,Seat);
   }
   IEnumerator Mount(){
    // Loosely in the socket, thread showing; screw it in with swipes the other way.
    Destroy(fresh.gameObject);var bulb=Bulb("bulb_off_0",Seat()-new Vector2(0,ThreadDrop));Play("pickup",.8f);
    yield return U.Scale(bulb.rectTransform,Vector3.one*1.05f,.08f);StartCoroutine(U.Scale(bulb.rectTransform,Vector3.one,.12f,true));
    Banner("Agora gire para rosquear",1);TaskProgress(.5f);
    int f=0,t=0;bool lit=false;
    Swipe(bulb.rectTransform,dx=>{
     if(lit||done)return;StopHint();
     int steps=(int)(-dx/SwipeStep);if(steps==0)return;
     for(int i=0;i<Mathf.Abs(steps);i++){
      int dir=steps>0?1:-1;f=(f-dir+BulbFrames)%BulbFrames;t=Mathf.Clamp(t+dir,0,BulbTurns);
      U.SetArt(bulb,"bulb_off_"+f);bulb.rectTransform.anchoredPosition=Seat()-new Vector2(0,ThreadDrop*(1-t/(float)BulbTurns));
      Play("twist_"+(t%2),1.1f+t*.02f,.8f);
     }
     TaskProgress(.5f+t/(float)BulbTurns*.5f);
     if(t>=BulbTurns){lit=true;StartCoroutine(Light(bulb));}
    },SwipeStep);
    Hint(()=>At(bulb.rectTransform)+new Vector2(70,0),()=>At(bulb.rectTransform)+new Vector2(-70,0));
   }
   IEnumerator Light(Image bulb){
    Play("bulb_on");
    for(int i=0;i<3;i++){U.SetArt(bulb,"bulb_on");yield return new WaitForSecondsRealtime(.07f);U.SetArt(bulb,"bulb_off_0");yield return new WaitForSecondsRealtime(.09f);}
    U.SetArt(bulb,"bulb_on");glow.rectTransform.anchoredPosition=bulb.rectTransform.anchoredPosition-new Vector2(0,60);
    StartCoroutine(U.Scale(glow.rectTransform,Vector3.one*22,.5f));StartCoroutine(U.Fade(glow,.6f,.5f));StartCoroutine(U.Fade(dark,0,.7f));
    yield return new WaitForSecondsRealtime(.5f);Complete(bulb.rectTransform.anchoredPosition-new Vector2(0,80));
   }
  }
  // A transparent area over `target` that reports horizontal drag distance in steps of `step` pixels.
  RectTransform Swipe(RectTransform target,Action<float> onSteps,float step){
   var hit=Keep(CheckoutDesktopCard.Image(stage,"Swipe",new Color(1,1,1,0),0));hit.raycastTarget=true;
   var r=hit.rectTransform;U.At(r,Mid,new Vector2(Mathf.Max(220,target.rect.width*1.6f),Mathf.Max(220,target.rect.height*1.1f)),At(target));
   var s=hit.gameObject.AddComponent<CheckoutSwipe>();s.step=step;s.onSteps=onSteps;return r;
  }
  IEnumerator Fall(Image img){var r=img.rectTransform;Play("whoosh",.8f);StartCoroutine(U.Rotate(r,300,.6f));yield return U.Move(r,r.anchoredPosition+new Vector2(60,-700),.6f);Play("glass_dump",.9f,.6f);}
  IEnumerator Flicker(Image img,Func<bool> on){while(img&&on()){yield return new WaitForSecondsRealtime(UnityEngine.Random.Range(.6f,1.6f));if(!img||!on())yield break;var keep=img.sprite;U.SetArt(img,"bulb_on");Play("tap",.5f,.4f);yield return new WaitForSecondsRealtime(.05f);if(img&&on())img.sprite=keep;}}
 }
 // Horizontal swipes (mouse or finger) in canvas units, reported in whole steps.
 public sealed class CheckoutSwipe:MonoBehaviour,UnityEngine.EventSystems.IBeginDragHandler,UnityEngine.EventSystems.IDragHandler {
  public float step=40;public Action<float> onSteps;float acc;Canvas canvas;
  public void OnBeginDrag(UnityEngine.EventSystems.PointerEventData e){acc=0;}
  public void OnDrag(UnityEngine.EventSystems.PointerEventData e){
   if(!canvas)canvas=GetComponentInParent<Canvas>();
   acc+=e.delta.x/Mathf.Max(.01f,canvas?canvas.scaleFactor:1);
   if(Mathf.Abs(acc)>=step){int n=(int)(acc/step);acc-=n*step;onSteps?.Invoke(n*step);}
  }
 }
}
