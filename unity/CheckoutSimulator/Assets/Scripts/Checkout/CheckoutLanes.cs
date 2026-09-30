using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using MarketDay;
namespace Checkout {
 // One checkout line: where its customers wait and who scans their items.
 public class CheckoutLane {
  public List<CheckoutWalker> queue=new List<CheckoutWalker>();
  public Vector3[] places; // Legacy unprojected spots, [0] is where the customer pays. Null for the original checkout.
  public Vector3 register;public CheckoutCashier cashier;public CheckoutKiosk kiosk;public GameObject[] parts;
  // With the Interior Kit the lane belongs to a placed piece of furniture (checkout:main, kiosk:1...).
  public string itemId;public bool owned=true;public bool isKiosk;
  public bool Open=>itemId!=null?owned&&CheckoutInterior.Active&&CheckoutInterior.Active.Get(itemId)!=null:parts==null||parts.All(p=>p&&p.activeSelf);
  public int Capacity=>itemId!=null&&CheckoutInterior.Active?CheckoutInterior.Active.QueueLength(itemId):places?.Length??5;
 }
 // Checkout lanes bought as upgrades: a second staffed counter and two self-checkout kiosks.
 // Purely visual: customers join the shortest open line; the game rules still come from the snapshot.
 public class CheckoutLanes:MonoBehaviour {
  public const string ExtraItem="extra-checkout",SelfItem="self-checkout";
  public readonly List<CheckoutLane> lanes=new List<CheckoutLane>();
  CheckoutInterior interior;
  static Vector3 P(float x,float z)=>new Vector3(x,.74f,z);
  public void Initialize(Transform world,List<CheckoutWalker> mainQueue,CheckoutInterior furniture=null){
   interior=furniture&&furniture.Ready?furniture:null;
   if(interior){
    lanes.Add(new CheckoutLane{queue=mainQueue,itemId="checkout:main",cashier=world.Find("Worker_Cashier")?.GetComponent<CheckoutCashier>()});
    var second=world.Find("Worker_Cashier 2");
    lanes.Add(new CheckoutLane{itemId="checkout:extra",cashier=second?second.GetComponent<CheckoutCashier>():null,owned=false});
    lanes.Add(new CheckoutLane{itemId="kiosk:1",isKiosk=true,owned=false});
    lanes.Add(new CheckoutLane{itemId="kiosk:2",isKiosk=true,owned=false});
    return;
   }
   lanes.Add(new CheckoutLane{queue=mainQueue,register=MarketSimulation.Register,cashier=world.Find("Worker_Cashier")?.GetComponent<CheckoutCashier>()});
   var counter=world.Find("ReplacementVisual Checkout 2");var cashier=world.Find("Worker_Cashier 2");
   if(counter&&cashier)lanes.Add(new CheckoutLane{places=new[]{P(3.35f,-6.15f),P(2f,-6.15f),P(.65f,-6.15f)},register=P(3.35f,-4.7f),cashier=cashier.GetComponent<CheckoutCashier>(),parts=new[]{counter.gameObject,cashier.gameObject}});
   // Kiosks stand at x 5.6 and 7.5 (scene baseline); customers face the scanner, just left of the kiosk centre.
   float[] kioskX={5.46f,7.36f};
   for(int i=1;i<=2;i++){var kiosk=world.Find("ReplacementVisual SelfCheckout "+i);if(!kiosk)continue;float x=kioskX[i-1];
    var station=kiosk.GetComponent<CheckoutKiosk>();if(!station)station=kiosk.gameObject.AddComponent<CheckoutKiosk>();
    lanes.Add(new CheckoutLane{places=new[]{P(x,-5.45f),P(x,-6.45f)},register=P(x,-4.4f),kiosk=station,parts=new[]{kiosk.gameObject}});}
  }
  // Shows the lanes of the owned upgrades. Returns true when the set of open lanes changed.
  public bool Apply(string[] owned){
   bool changed=false;
   if(interior){
    foreach(var lane in lanes.Skip(1)){bool on=owned!=null&&owned.Contains(lane.isKiosk?SelfItem:ExtraItem);if(lane.owned==on)continue;changed=true;lane.owned=on;}
    var second=lanes[1].cashier;if(second)second.gameObject.SetActive(lanes[1].owned);
    return changed;
   }
   foreach(var lane in lanes.Skip(1)){bool on=owned!=null&&owned.Contains(lane.kiosk?SelfItem:ExtraItem);if(lane.Open==on)continue;changed=true;foreach(var part in lane.parts)part.SetActive(on);}
   return changed;
  }
  // A random open lane among those with the fewest customers; the original checkout takes the overflow.
  public CheckoutLane Pick(){
   var free=lanes.Where((lane,i)=>i==0||lane.Open&&lane.queue.Count<lane.Capacity).ToList();int fewest=free.Min(lane=>lane.queue.Count);
   var best=free.Where(lane=>lane.queue.Count==fewest).ToList();return best[Random.Range(0,best.Count)];
  }
  // Cashiers stand behind their counters and scan along the belt wherever the counter was placed.
  public void Rebase(MarketLayout layout){
   if(interior){
    foreach(var lane in lanes){var item=interior.Get(lane.itemId);
     if(lane.isKiosk){lane.kiosk=item!=null?item.root.GetComponent<CheckoutKiosk>():null;continue;}
     if(!lane.cashier||item==null)continue;
     var t=lane.cashier.transform;var spot=interior.StaffPoint(item);
     if((t.position-spot).sqrMagnitude>.0001f||Quaternion.Angle(t.rotation,item.root.rotation)>.5f)t.SetPositionAndRotation(spot,item.root.rotation);
     lane.cashier.beltStart=item.root.TransformPoint(item.piece.beltStart);lane.cashier.beltEnd=item.root.TransformPoint(item.piece.beltEnd);}
    return;
   }
   foreach(var lane in lanes.Skip(1))if(lane.cashier){lane.cashier.beltStart=CheckoutMarketLayout.Project(new Vector3(1.85f,1.57f,-4.7f),layout);lane.cashier.beltEnd=CheckoutMarketLayout.Project(new Vector3(3.25f,1.57f,-4.7f),layout);}
  }
  public void Remove(CheckoutWalker walker){foreach(var lane in lanes)lane.queue.Remove(walker);}
 }
}
