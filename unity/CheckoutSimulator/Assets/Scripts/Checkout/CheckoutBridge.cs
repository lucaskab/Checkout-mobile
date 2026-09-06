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
  public Snapshot State {get;private set;}
  MarketSimulation simulation;CheckoutMap map;float hello;int commandSequence;
  readonly Queue<Customer> visits=new Queue<Customer>();readonly HashSet<string> seen=new HashSet<string>();readonly List<CheckoutWalker> walkers=new List<CheckoutWalker>();
  public readonly List<CheckoutWalker> Queue=new List<CheckoutWalker>();
#if UNITY_IOS && !UNITY_EDITOR
  [DllImport("__Internal")] static extern void sendMessageToMobileApp(string message);
#endif
  void Awake(){name="CheckoutBridge";simulation=FindAnyObjectByType<MarketSimulation>();simulation.quietCapture=true;simulation.enabled=false;var qa=simulation.GetComponent<MarketPlaytest>();if(qa)qa.enabled=false;}
  void Start(){simulation.Initialize(false);simulation.hud.gameObject.SetActive(false);map=gameObject.AddComponent<CheckoutMap>();map.Initialize(simulation.world,this);
   foreach(Transform t in simulation.world)if(t.name.StartsWith("Customer_")){var w=t.gameObject.AddComponent<CheckoutWalker>();w.Initialize(this,t.GetComponent<NavMeshAgent>(),map);walkers.Add(w);t.gameObject.SetActive(false);}
   // Integration is read-only until the React Native authority supplies a snapshot.
   foreach(Transform t in simulation.world)if(t.name.StartsWith("StockWorker_"))t.gameObject.SetActive(false);
   Emit("{\"kind\":\"ready\",\"protocol\":1}");
   var args=Environment.GetCommandLineArgs();int at=Array.IndexOf(args,"--checkout-snapshot");if(at>=0&&at+1<args.Length){Receive(File.ReadAllText(args[at+1]));if(Array.IndexOf(args,"--checkout-qa")>=0)StartCoroutine(CaptureQA());}
  }
  public void Receive(string json){try {var next=JsonUtility.FromJson<Snapshot>(json);if(next.kind!="snapshot"||next.protocol!=1||next.shelves==null||next.@event==null)return;
   bool newSession=State==null||State.session!=next.session;if(!newSession&&next.revision<State.revision)return;
   if(newSession){seen.Clear();visits.Clear();foreach(var w in walkers)w.gameObject.SetActive(false);Queue.Clear();}
   if(next.customers!=null)foreach(var customer in next.customers.Reverse())if(seen.Add(customer.id)&&!newSession)visits.Enqueue(customer);
   State=next;map.Apply(next);if(seen.Count>2000){seen.Clear();foreach(var c in next.customers??Array.Empty<Customer>())seen.Add(c.id);}
  }catch(Exception ex){Debug.LogError("CHECKOUT_SNAPSHOT_ERROR "+ex.Message);}}
  void Update(){simulation.ExternalCamera();if(State==null){hello+=Time.unscaledDeltaTime;if(hello>1){hello=0;Emit("{\"kind\":\"ready\",\"protocol\":1}");}return;}
   simulation.speed=1;
   if(visits.Count>0){var walker=walkers.FirstOrDefault(w=>!w.gameObject.activeSelf);if(walker&&walkers.All(w=>!w.gameObject.activeSelf||Vector3.Distance(w.transform.position,new Vector3(-1.75f,.3f,-8.7f))>1.5f))walker.Begin(visits.Dequeue());}
   if(Input.GetMouseButtonUp(0)&&UnityEngine.EventSystems.EventSystem.current&&!UnityEngine.EventSystems.EventSystem.current.IsPointerOverGameObject()){
    if(Physics.Raycast(simulation.view.ScreenPointToRay(Input.mousePosition),out var hit,150)){var action=hit.collider.GetComponent<CheckoutTarget>();if(action)OpenPanel(action.panel);}
   }
  }
  public void OpenPanel(string panel)=>Emit("{\"kind\":\"panel\",\"panel\":\""+panel+"\"}");
  public void Command(string action,string args){if(State==null)return;Emit("{\"kind\":\"command\",\"protocol\":1,\"session\":\""+State.session+"\",\"revision\":"+State.revision+",\"id\":\"unity-"+(++commandSequence)+"\",\"action\":\""+action+"\",\"args\":"+args+"}");}
  public static void Emit(string json){
#if UNITY_ANDROID && !UNITY_EDITOR
   using(var module=new AndroidJavaClass("com.azesmwayreactnativeunity.ReactNativeUnityViewManager"))module.CallStatic("sendMessageToMobileApp",json);
#elif UNITY_IOS && !UNITY_EDITOR
   sendMessageToMobileApp(json);
#else
   Debug.Log("CHECKOUT_EVENT "+json);
#endif
  }
  IEnumerator CaptureQA(){yield return new WaitForSeconds(2);foreach(var c in State.customers??Array.Empty<Customer>())visits.Enqueue(c);yield return new WaitForSeconds(10);var path=Path.GetFullPath("checkout-projection.png");ScreenCapture.CaptureScreenshot(path);yield return new WaitForSeconds(1);Debug.Log("CHECKOUT_PROJECTION_OK "+State.session+" "+State.revision+" shelves="+State.shelves.Length+" coins="+State.coins+" "+path);Application.Quit();}
 }
 public class CheckoutTarget:MonoBehaviour {public string panel;}
}
