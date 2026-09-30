using UnityEngine;
namespace Checkout {
 // Self-checkout kiosk: the customer passes each item over the scanner into the bag. Purely visual.
 public class CheckoutKiosk:MonoBehaviour {
  // Path of one item, relative to the kiosk at its scene size (front faces -Z): hand, scanner, bag.
  static readonly Vector3[] path={new Vector3(-.56f,1.47f,-.63f),new Vector3(-.14f,1.33f,-.08f),new Vector3(.84f,1.43f,0)};
  public const float ItemSeconds=.9f;
  Vector3[] local;Transform item;float elapsed,duration;
  void Awake(){
   local=new Vector3[path.Length];bool placed=GetComponent<CheckoutInteriorPiece>();for(int i=0;i<path.Length;i++)local[i]=placed?path[i]:transform.InverseTransformPoint(transform.position+path[i]); // Interior Kit kiosks are authored at unit scale facing -Z.
   var source=FindAnyObjectByType<CheckoutCashier>(FindObjectsInactive.Include);
   if(source&&source.item){item=Instantiate(source.item,transform.parent);item.name="Self checkout scanned item";item.gameObject.SetActive(false);}
  }
  public float Serve(int quantity){elapsed=0;duration=Mathf.Clamp(quantity,1,6)*ItemSeconds;if(item)item.gameObject.SetActive(true);return duration;}
  void OnDisable(){duration=0;if(item)item.gameObject.SetActive(false);}
  void Update(){
   if(duration<=0||!item)return;
   elapsed+=Time.deltaTime;
   if(elapsed>=duration){duration=0;item.gameObject.SetActive(false);return;}
   float t=Mathf.Repeat(elapsed,ItemSeconds)/ItemSeconds;
   // Over the scanner in the first half (a short pause on the glass), then into the bag.
   var a=transform.TransformPoint(local[0]);var b=transform.TransformPoint(local[1]);var c=transform.TransformPoint(local[2]);
   item.position=t<.5f?Vector3.Lerp(a,b,Mathf.SmoothStep(0,1,Mathf.Clamp01(t/.4f))):Vector3.Lerp(b,c,Mathf.SmoothStep(0,1,(t-.5f)/.5f))+Vector3.up*Mathf.Sin((t-.5f)/.5f*Mathf.PI)*.12f;
  }
 }
}
