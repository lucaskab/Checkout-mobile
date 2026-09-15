using UnityEngine;

namespace Checkout {
 // A small world-space status pill replaces multi-line labels over every fixture.
 public sealed class CheckoutStatusMarker:MonoBehaviour {
  Transform fill;GameObject warning,lockIcon,lockLevelBadge;TextMesh lockLevel;float ratio;bool working,locked;
  public void Initialize(CheckoutEventAssets art){
   art.Part(transform,"Status background",Vector3.zero,new Vector3(.82f,.17f,.035f),"FFF1D8");
   fill=art.Part(transform,"Stock level",new Vector3(-.34f,0,-.026f),new Vector3(.68f,.075f,.018f),"65A593");
   warning=art.Part(transform,"Attention",new Vector3(0,.06f,-.06f),new Vector3(.06f,.2f,.02f),"C36C52").gameObject;
   art.Part(warning.transform,"Dot",new Vector3(0,-.8f,0),new Vector3(1,.24f,1),"C36C52");warning.SetActive(false);
   var icon=art.Group(transform,"Level lock",new Vector3(0,.06f,-.07f));lockIcon=icon.gameObject;
   art.Part(icon,"Lock body",new Vector3(0,-.05f,0),new Vector3(.28f,.2f,.035f),"E9A52E");
   art.Bar(icon,new Vector3(-.105f,.02f,0),new Vector3(-.105f,.22f,0),.045f,"E9A52E");
   art.Bar(icon,new Vector3(.105f,.02f,0),new Vector3(.105f,.22f,0),.045f,"E9A52E");
   art.Bar(icon,new Vector3(-.105f,.22f,0),new Vector3(.105f,.22f,0),.045f,"E9A52E");
   lockIcon.SetActive(false);
   var badge=art.Group(transform,"Level requirement",new Vector3(0,-.24f,-.065f));lockLevelBadge=badge.gameObject;
   art.Part(badge,"Level badge background",Vector3.zero,new Vector3(.62f,.16f,.025f),"FFF1D8");
   var label=new GameObject("Level label",typeof(TextMesh));label.transform.SetParent(badge,false);label.transform.localPosition=new Vector3(0,-.015f,-.025f);lockLevel=label.GetComponent<TextMesh>();lockLevel.anchor=TextAnchor.MiddleCenter;lockLevel.alignment=TextAlignment.Center;lockLevel.characterSize=.045f;lockLevel.fontSize=48;lockLevel.color=MarketDay.MarketSimulation.C("7A4A22");
   lockLevelBadge.SetActive(false);
  }
  public void Apply(bool unlocked,int stock,int capacity,bool production=false,int requiredLevel=0){locked=!unlocked;ratio=Mathf.Clamp01((float)stock/Mathf.Max(1,capacity));working=unlocked&&production&&stock>0;gameObject.SetActive(locked||(production?working:ratio<.999f));lockIcon.SetActive(locked);lockLevelBadge.SetActive(locked&&requiredLevel>0);if(requiredLevel>0)lockLevel.text="NV. "+requiredLevel;warning.SetActive(unlocked&&!production&&stock==0);fill.gameObject.SetActive(unlocked&&stock>0);SetFill(working ? .65f : ratio);}
  void SetFill(float amount){fill.localScale=new Vector3(.68f*amount,.075f,.018f);fill.localPosition=new Vector3(-.34f+.34f*amount,0,-.026f);}
  void LateUpdate(){if(Camera.main)transform.rotation=Camera.main.transform.rotation;if(working)SetFill(.35f+Mathf.PingPong(Time.time*.35f,.65f));if(locked)lockIcon.transform.localScale=Vector3.one*(.94f+Mathf.Sin(Time.time*2.2f)*.06f);}
 }
}
