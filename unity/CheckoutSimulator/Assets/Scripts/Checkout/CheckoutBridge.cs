using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.AI;
using UnityEngine.UI;
using MarketDay;
namespace Checkout {
 [DefaultExecutionOrder(-500)]
 public class CheckoutBridge : MonoBehaviour {
  // Dev play-mode checks (CheckoutAutoTest) add their test data to each snapshot as it arrives.
  public static System.Action<Snapshot> TestPatch;
  public Snapshot State {get;private set;}
  MarketSimulation simulation;CheckoutMap map;CheckoutCityTraffic traffic;float hello;int commandSequence;Vector2 pointerStart;bool pointerDragged;
  readonly Queue<Customer> visits=new Queue<Customer>();readonly HashSet<string> seen=new HashSet<string>();readonly List<CheckoutWalker> walkers=new List<CheckoutWalker>();readonly List<string> appearanceBag=new List<string>();string lastAppearance;
  public readonly List<CheckoutWalker> Queue=new List<CheckoutWalker>();
#if UNITY_IOS && !UNITY_EDITOR
  [DllImport("__Internal")] static extern void sendMessageToMobileApp(string message);
#endif
  void Awake(){name="CheckoutBridge";simulation=FindAnyObjectByType<MarketSimulation>();simulation.quietCapture=true;simulation.enabled=false;var qa=simulation.GetComponent<MarketPlaytest>();if(qa)qa.enabled=false;}
  void Start(){simulation.Initialize(false);simulation.hud.gameObject.SetActive(false);map=gameObject.AddComponent<CheckoutMap>();gameObject.AddComponent<CheckoutCounterGame>().Initialize(this);gameObject.AddComponent<CheckoutIncidents>().Initialize(this,map);gameObject.AddComponent<CheckoutStockroom>().Initialize(this);map.Initialize(simulation.world,this);gameObject.AddComponent<CheckoutBuildMode>().Initialize(this,map);gameObject.AddComponent<CheckoutLotView>().Initialize(this);traffic=FindAnyObjectByType<CheckoutCityTraffic>();
   foreach(Transform t in simulation.world)if(t.name.StartsWith("Customer_")){var w=t.gameObject.AddComponent<CheckoutWalker>();w.Initialize(this,t.GetComponent<NavMeshAgent>(),map);walkers.Add(w);t.gameObject.SetActive(false);}
   // Integration is read-only until the React Native authority supplies a snapshot.
   foreach(Transform t in simulation.world)if(t.name.StartsWith("StockWorker_"))t.gameObject.SetActive(false);
   Emit("{\"kind\":\"ready\",\"protocol\":1}");
   var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"--checkout-snapshot");if(at>=0&&at+1<args.Length){Receive(File.ReadAllText(args[at+1]));int eventQa=Array.IndexOf(args,"--checkout-event-qa"),parityQa=Array.IndexOf(args,"--checkout-parity-qa");if(eventQa>=0&&eventQa+1<args.Length)StartCoroutine(gameObject.AddComponent<CheckoutEventPlaytest>().Run(this,args[eventQa+1]));else if(parityQa>=0&&parityQa+1<args.Length)StartCoroutine(gameObject.AddComponent<CheckoutParityPlaytest>().Run(this,args[parityQa+1]));else if(Array.IndexOf(args,"--checkout-qa")>=0)StartCoroutine(CaptureQA());}
  }
  public void Receive(string json){if(json.StartsWith("{\"kind\":\"receipt\"")){Receipt(json);return;}try {var next=JsonUtility.FromJson<Snapshot>(json);if(next.kind!="snapshot"||next.protocol!=1||next.shelves==null||next.@event==null)return;
   bool newSession=State==null||State.session!=next.session;if(!newSession&&next.revision<State.revision)return;
   if(newSession){seen.Clear();visits.Clear();if(traffic)traffic.ResetVisits();foreach(var w in walkers)w.CancelVisit();Queue.Clear();}
   bool parkingOpened=next.layout!=null&&next.layout.parking&&(State?.layout==null||!State.layout.parking);
   if(next.customers!=null)foreach(var customer in next.customers.Reverse())if(seen.Add(customer.id)&&!newSession)visits.Enqueue(customer);
   // Recent customers are already paid by the app. Replay a short visual arrival when
   // opening the simulator or unlocking parking; never generate another transaction.
   if((newSession||parkingOpened)&&next.isOpen&&visits.Count==0&&next.customers!=null)
    foreach(var customer in next.customers.Take(3).Reverse())visits.Enqueue(customer);
   // A closed market takes no one new; pending arrivals stay seen so reopening never replays them.
   if(!next.isOpen)visits.Clear();
   bool closing=State!=null&&State.isOpen&&!next.isOpen;
   TestPatch?.Invoke(next);State=next;map.Apply(next);
   if(closing)foreach(var w in walkers)w.MarketClosed();if(seen.Count>2000){seen.Clear();foreach(var c in next.customers??Array.Empty<Customer>())seen.Add(c.id);}
  }catch(Exception ex){Debug.LogError("CHECKOUT_SNAPSHOT_ERROR "+ex.Message);}}
  void Update(){simulation.ExternalCamera();if(State==null){hello+=Time.unscaledDeltaTime;if(hello>1){hello=0;Emit("{\"kind\":\"ready\",\"protocol\":1}");}return;}
   simulation.speed=1;
   // New customers wait outside while the player rearranges the shop in build mode.
   if(visits.Count>0&&State.isOpen&&!CheckoutBuildMode.Open&&!CheckoutMapEditor.Open){var walker=NextAvailableWalker();if(walker){if(traffic&&map.HasParking){if(traffic.TryBegin(visits.Peek(),walker)){visits.Dequeue();AppearanceStarted(walker);}}else if(walkers.All(w=>!w.gameObject.activeSelf||Vector3.Distance(w.transform.position,map.Entrance)>1.5f)){walker.Begin(visits.Dequeue());AppearanceStarted(walker);}}}
   if(Input.GetMouseButtonDown(0)){pointerStart=Input.mousePosition;pointerDragged=false;}
   if(Input.touchCount>1||(Input.GetMouseButton(0)&&Vector2.Distance(pointerStart,Input.mousePosition)>10))pointerDragged=true;
   if(Input.GetMouseButtonUp(0)&&!pointerDragged&&!CheckoutBuildMode.Open&&!CheckoutMapEditor.Open&&UnityEngine.EventSystems.EventSystem.current&&!UnityEngine.EventSystems.EventSystem.current.IsPointerOverGameObject()){
    if(Physics.Raycast(simulation.view.ScreenPointToRay(Input.mousePosition),out var hit,150)){var action=hit.collider.GetComponent<CheckoutTarget>();if(action){if(action.panel=="checkout")CheckoutCounterGame.Show(this,action.requestId);
     // Works boards: finish a build inside the market (or the expansion) right now for diamonds.
     else if(action.panel=="finishBuild"&&!string.IsNullOrEmpty(action.requestId))Command("finishInteriorConstructionNow","[\""+action.requestId+"\"]");
     else if(action.panel=="finishWorks")Command("finishMarketExpansionNow","[]");else if(action.panel=="incident")CheckoutIncidents.Show(action.requestId);else if(action.panel=="dock")CheckoutStockroom.ShowDock();else OpenPanel(action.panel,action.shelfId,action.sectorId,action.requestId);}}
   }
  }
  string AppearanceKey(CheckoutWalker walker){var motion=walker.GetComponent<MarketCharacterAnimator>();var body=motion.animationPlayer.GetComponentsInChildren<SkinnedMeshRenderer>(true).FirstOrDefault(r=>!r.name.EndsWith("_Prop"));return body&&body.sharedMaterial&&body.sharedMaterial.mainTexture?body.sharedMaterial.mainTexture.name:walker.name;}
  CheckoutWalker NextAvailableWalker(){
   // Several pooled actors share the same GLB; randomize appearances, not actor IDs.
   if(appearanceBag.Count==0){appearanceBag.AddRange(walkers.Select(AppearanceKey).Distinct());for(int i=appearanceBag.Count-1;i>0;i--){int j=UnityEngine.Random.Range(0,i+1);var t=appearanceBag[i];appearanceBag[i]=appearanceBag[j];appearanceBag[j]=t;}if(appearanceBag.Count>1&&appearanceBag[0]==lastAppearance){var t=appearanceBag[0];appearanceBag[0]=appearanceBag[1];appearanceBag[1]=t;}}
   foreach(var key in appearanceBag){var available=walkers.Where(w=>!w.Reserved&&!w.gameObject.activeSelf&&AppearanceKey(w)==key).ToArray();if(available.Length>0)return available[UnityEngine.Random.Range(0,available.Length)];}return null;
  }
  void AppearanceStarted(CheckoutWalker walker){lastAppearance=AppearanceKey(walker);appearanceBag.Remove(lastAppearance);}
  public void OpenPanel(string panel,string shelfId="",string sectorId="",string requestId="")=>Emit(JsonUtility.ToJson(new PanelMessage{kind="panel",panel=panel,shelfId=shelfId,sectorId=sectorId,requestId=requestId}));
  [Serializable] class PanelMessage{public string kind,panel,shelfId,sectorId,requestId;}
  // The special request of a customer, pending or just answered (see CheckoutRequestBubble).
  public DayRequest RequestFor(string customerId){if(string.IsNullOrEmpty(customerId)||State?.day?.requests==null)return null;foreach(var r in State.day.requests)if(r.customerId==customerId)return r;return null;}
  public static double Now=>DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
  public CheckoutEntry CheckoutFor(string customerId){if(string.IsNullOrEmpty(customerId)||State?.checkouts==null)return null;foreach(var c in State.checkouts)if(c.customerId==customerId)return c;return null;}
  public CheckoutResult CheckoutResultFor(string customerId){if(string.IsNullOrEmpty(customerId)||State?.checkoutResults==null)return null;foreach(var r in State.checkoutResults)if(r.customerId==customerId)return r;return null;}
  // Mini-game results. The app rejects a command made against an older revision ("stale-revision");
  // the store changes every second while the market runs, so those are sent again at the newer
  // revision the receipt reports (the mini-game already happened, it only has to be recorded).
  public void Command(string action,string args)=>SendCommand(action,args,State?.revision??0,0);
  void SendCommand(string action,string args,int revision,int tries){
   if(State==null)return;var id="unity-"+(++commandSequence);
   if(pending.Count>100)pending.Clear();pending[id]=new PendingCommand{action=action,args=args,tries=tries};
   Emit("{\"kind\":\"command\",\"protocol\":1,\"session\":\""+State.session+"\",\"revision\":"+Mathf.Max(revision,State.revision)+",\"id\":\""+id+"\",\"action\":\""+action+"\",\"args\":"+args+"}");
  }
  sealed class PendingCommand{public string action,args;public int tries;}
  [Serializable] class ReceiptMessage{public string kind,id,reason;public bool ok;public int revision;}
  readonly Dictionary<string,PendingCommand> pending=new Dictionary<string,PendingCommand>();
  public bool HasPending(string action)=>pending.Values.Any(p=>p.action==action);
  public void Receipt(string json){
   ReceiptMessage receipt;try {receipt=JsonUtility.FromJson<ReceiptMessage>(json);}catch {return;}
   if(receipt?.id==null||!pending.TryGetValue(receipt.id,out var command))return;
   pending.Remove(receipt.id);if(receipt.ok)return;
   if(receipt.reason=="stale-revision"&&command.tries<6){SendCommand(command.action,command.args,receipt.revision,command.tries+1);return;}
   Debug.LogWarning("CHECKOUT_RECEIPT "+command.action+" "+command.args+" -> "+receipt.reason);
  }
  public static void Emit(string json){
#if UNITY_ANDROID && !UNITY_EDITOR
   using(var module=new AndroidJavaClass("com.azesmwayreactnativeunity.ReactNativeUnityViewManager"))module.CallStatic("sendMessageToMobileApp",json);
#elif UNITY_IOS && !UNITY_EDITOR
   sendMessageToMobileApp(json);
#else
   if(CheckoutDesktopHost.Active&&CheckoutDesktopHost.Active.Send(json))return;
   Debug.Log("CHECKOUT_EVENT "+json);
#endif
  }
  IEnumerator CaptureQA(){yield return new WaitForSeconds(2);foreach(var c in State.customers??Array.Empty<Customer>())visits.Enqueue(c);yield return new WaitForSeconds(10);var path=Path.GetFullPath("checkout-projection.png");ScreenCapture.CaptureScreenshot(path);yield return new WaitForSeconds(1);Debug.Log("CHECKOUT_PROJECTION_OK "+State.session+" "+State.revision+" shelves="+State.shelves.Length+" coins="+State.coins+" "+path);Application.Quit();}
 }
 public class CheckoutTarget:MonoBehaviour {public string panel;public string shelfId,sectorId,requestId;}
}
