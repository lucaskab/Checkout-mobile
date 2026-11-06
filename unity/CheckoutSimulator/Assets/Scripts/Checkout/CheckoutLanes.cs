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
  // A staffed counter other than the main one only takes customers while its own cashier works (one cashier per
  // checkout, Lucas 05/11); the main checkout is the player's when nobody works it.
  public bool staffed=true;
  public bool Open=>itemId!=null?owned&&staffed&&CheckoutInterior.Active&&CheckoutInterior.Active.Get(itemId)!=null:parts==null||parts.All(p=>p&&p.activeSelf);
  public int Capacity=>itemId!=null&&CheckoutInterior.Active?CheckoutInterior.Active.QueueLength(itemId):places?.Length??5;
 }
 // Checkout lanes bought as upgrades: a second staffed counter and two self-checkout kiosks.
 // Purely visual: customers join the shortest open line; the game rules still come from the snapshot.
 public class CheckoutLanes:MonoBehaviour {
  public const string ExtraItem="extra-checkout",SelfItem="self-checkout";
  // The checkouts and kiosks of src/data/checkout-lanes.ts: piece id → the shop item that builds it (null: comes with
  // the market). Cashier n stands at counter n ("Worker_Cashier", "Worker_Cashier 2", then copies of the first).
  public static readonly (string piece,string item)[] Counters={("checkout:main",null),("checkout:extra",ExtraItem),("checkout:3","checkout-3"),("checkout:4","checkout-4"),("checkout:5","checkout-5")};
  public static readonly (string piece,string item)[] Kiosks={("kiosk:1",SelfItem),("kiosk:2",SelfItem),("kiosk:3","extra-kiosks"),("kiosk:4","extra-kiosks"),("kiosk:5","kiosks-3"),("kiosk:6","kiosks-3")};
  public static string ItemOf(string piece){foreach(var c in Counters)if(c.piece==piece)return c.item;foreach(var k in Kiosks)if(k.piece==piece)return k.item;return null;}
  public static string[] PiecesOf(string item){var list=new List<string>();foreach(var c in Counters)if(c.item==item)list.Add(c.piece);foreach(var k in Kiosks)if(k.item==item)list.Add(k.piece);return list.ToArray();}
  public static string CashierName(int n)=>n<=1?"Worker_Cashier":"Worker_Cashier "+n;
  public static int CounterNumber(string piece){for(int i=0;i<Counters.Length;i++)if(Counters[i].piece==piece)return i+1;return 0;}
  public readonly List<CheckoutLane> lanes=new List<CheckoutLane>();
  CheckoutInterior interior;
  static Vector3 P(float x,float z)=>new Vector3(x,.74f,z);
  public void Initialize(Transform world,List<CheckoutWalker> mainQueue,CheckoutInterior furniture=null){
   interior=furniture&&furniture.Ready?furniture:null;
   if(interior){
    var first=world.Find("Worker_Cashier");
    for(int i=0;i<Counters.Length;i++){
     var worker=world.Find(CashierName(i+1));
     // (cashiers 3–5 are copies of the first one, made once)
     if(!worker&&first){worker=Instantiate(first.gameObject,world).transform;worker.name=CashierName(i+1);worker.gameObject.SetActive(false);}
     lanes.Add(new CheckoutLane{queue=i==0?mainQueue:new List<CheckoutWalker>(),itemId=Counters[i].piece,cashier=worker?worker.GetComponent<CheckoutCashier>():null,owned=i==0});
    }
    foreach(var k in Kiosks)lanes.Add(new CheckoutLane{itemId=k.piece,isKiosk=true,owned=false});
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
    foreach(var lane in lanes.Skip(1)){var item=ItemOf(lane.itemId);bool on=owned!=null&&item!=null&&owned.Contains(item);if(lane.owned==on)continue;changed=true;lane.owned=on;}
    return changed;
   }
   foreach(var lane in lanes.Skip(1)){bool on=owned!=null&&owned.Contains(lane.kiosk?SelfItem:ExtraItem);if(lane.Open==on)continue;changed=true;foreach(var part in lane.parts)part.SetActive(on);}
   return changed;
  }
  /// <summary>Which counters have a cashier now: the first `cashiers` built counters (CheckoutMap shows them).
  /// Returns true when a lane opened or closed.</summary>
  public bool Staff(int cashiers,bool open){
   bool changed=false;int n=0;
   foreach(var lane in lanes){
    if(lane.isKiosk||lane.itemId==null)continue;
    bool built=lane.owned&&interior&&interior.Get(lane.itemId)!=null;
    bool has=built&&n<cashiers;if(built)n++;
    if(lane.cashier)lane.cashier.gameObject.SetActive(open&&has);
    // the main counter always takes customers (the player serves it); the others only with their cashier
    bool staffed=lane.itemId=="checkout:main"||has;
    if(lane.staffed!=staffed){lane.staffed=staffed;changed=true;}
   }
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
