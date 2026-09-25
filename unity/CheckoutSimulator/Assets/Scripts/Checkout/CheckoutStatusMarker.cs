using UnityEngine;

namespace Checkout {
 // A small world-space status pill replaces multi-line labels over every fixture.
 public sealed class CheckoutStatusMarker:MonoBehaviour {
  Transform fill;GameObject warning;float ratio;bool working;
  public void Initialize(CheckoutEventAssets art){
   art.Part(transform,"Status background",Vector3.zero,new Vector3(.82f,.17f,.035f),"FFF1D8");
   fill=art.Part(transform,"Stock level",new Vector3(-.34f,0,-.026f),new Vector3(.68f,.075f,.018f),"65A593");
   warning=art.Part(transform,"Attention",new Vector3(0,.06f,-.06f),new Vector3(.06f,.2f,.02f),"C36C52").gameObject;
   art.Part(warning.transform,"Dot",new Vector3(0,-.8f,0),new Vector3(1,.24f,1),"C36C52");warning.SetActive(false);
  }
  // Locked fixtures show nothing: unlocks are presented by the app, not over the floor.
  public void Apply(bool unlocked,int stock,int capacity,bool production=false,int requiredLevel=0){ratio=Mathf.Clamp01((float)stock/Mathf.Max(1,capacity));working=unlocked&&production&&stock>0;gameObject.SetActive(unlocked&&(production?working:ratio<.999f));warning.SetActive(unlocked&&!production&&stock==0);fill.gameObject.SetActive(unlocked&&stock>0);SetFill(working ? .65f : ratio);}
  void SetFill(float amount){fill.localScale=new Vector3(.68f*amount,.075f,.018f);fill.localPosition=new Vector3(-.34f+.34f*amount,0,-.026f);}
  void LateUpdate(){if(Camera.main)transform.rotation=Camera.main.transform.rotation;if(working)SetFill(.35f+Mathf.PingPong(Time.time*.35f,.65f));}
 }
}
