using System;
using System.Linq;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using Checkout;

// Runs against the open scene in Play Mode; never loads a snapshot or writes game state.
public static class CheckoutCustomerRoutePlaytest
{
    static CheckoutCityTraffic traffic;
    static CheckoutWalker[] customers;
    static int next;
    static bool projected;
    static readonly HashSet<CheckoutWalker> arriving=new();
    static readonly List<string> appearances=new();
    static readonly Dictionary<CheckoutWalker,(int phase,float time,Vector3 position)> stages=new();
    static readonly HashSet<CheckoutWalker> picked=new(),scanned=new(),paid=new();
    static float started, oldScale;
    public static string Status { get; private set; } = "Not run";
    public static void Run()
    {
        if(!EditorApplication.isPlaying)throw new InvalidOperationException("Play Mode required");
        traffic=UnityEngine.Object.FindFirstObjectByType<CheckoutCityTraffic>();
        customers=UnityEngine.Object.FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include,FindObjectsSortMode.None).OrderBy(c=>int.Parse(c.name.Substring(9))<6?1:0).ThenBy(c=>c.name).ToArray();
        if(customers.Any(c=>c.Reserved))throw new InvalidOperationException("Wait for active visits before running route QA");
        projected=false;arriving.Clear();appearances.Clear();stages.Clear();picked.Clear();scanned.Clear();paid.Clear();next=0;started=Time.time;oldScale=Time.timeScale;Time.timeScale=8;
        Status="Running";EditorApplication.update-=Tick;EditorApplication.update+=Tick;
    }
    public static void RunProjected()
    {
        Run();projected=true;
        var bridge=UnityEngine.Object.FindAnyObjectByType<CheckoutBridge>();
        // Ephemeral Play Mode fixture; stopping Play restores the user's scene/progress.
        var state=new Snapshot{kind="snapshot",protocol=1,session="customer-behavior-qa",revision=1,level=30,isOpen=true,
            shelves=CheckoutShelfSlots.Ids.Select(id=>new Shelf{id=id,unlocked=true,stock=30,capacity=30}).ToArray(),
            sectors=new[]{"padaria","acougue","peixaria","queijaria"}.Select(id=>new Sector{id=id,unlocked=true}).ToArray(),
            employees=Array.Empty<Employee>(),orders=Array.Empty<Order>(),jobs=Array.Empty<Job>(),customers=Array.Empty<Customer>(),expansions=Array.Empty<string>(),ownedItems=Array.Empty<string>(),@event=new MarketEvent()};
        bridge.Receive(JsonUtility.ToJson(state));state.revision++;
        var destinations=new[]{"sector-padaria","sector-acougue","sector-peixaria","sector-queijaria","produce","dairy","bakery","snacks","drinks","coffee"};
        state.customers=destinations.Select((id,i)=>new Customer{id="projected-"+i,spent=12,purchases=new[]{new Purchase{shelfId=id,quantity=1}}}).Reverse().ToArray();
        bridge.Receive(JsonUtility.ToJson(state));
    }
    static void Tick()
    {
        if(!EditorApplication.isPlaying){Finish("Stopped");return;}
        foreach(var c in customers.Where(c=>c.gameObject.activeInHierarchy))
        {
            var p=c.transform.position;
            int phase=c.VisitPhase;
            if(projected&&arriving.Add(c)){
                var body=c.GetComponent<MarketDay.MarketCharacterAnimator>().animationPlayer.GetComponentsInChildren<SkinnedMeshRenderer>().First(r=>!r.name.EndsWith("_Prop"));
                appearances.Add(body.sharedMaterial.mainTexture.name);
                Debug.Log("CUSTOMER_APPEARANCE "+appearances.Count+" "+appearances.Last());
                if(appearances.Count==5&&appearances.Distinct().Count()!=5){Finish("FAIL: first five appearances repeated");return;}
            }
            if(stages.TryGetValue(c,out var previous)){
                if(previous.phase!=phase){
                    if(previous.phase==1){if(Time.time-previous.time<1.3f){Finish("FAIL: pickup skipped "+c.name);return;}picked.Add(c);}
                    if(phase==4){if(previous.phase!=8||!picked.Contains(c)){Finish("FAIL: payment before scanning "+c.name);return;}scanned.Add(c);}
                    if(c.HasPaid){if(!scanned.Contains(c)){Finish("FAIL: checkout skipped "+c.name);return;}paid.Add(c);}
                    stages[c]=(phase,Time.time,p);
                }else if((phase==1||phase==8||phase==4)&&Vector3.Distance(p,previous.position)>.12f){Finish("FAIL: moving during purchase/payment "+c.name);return;}
            }else stages[c]=(phase,Time.time,p);
            if(p.x> -18.5f&&p.x< -9.5f&&p.z> -10.3f&&!(p.x< -14.4f&&Mathf.Abs(p.z-c.CarDoor.z)<.8f)){Finish("FAIL: parking shortcut "+c.name+" "+p);return;}
            var player=c.GetComponent<MarketDay.MarketCharacterAnimator>().animationPlayer;
            if(c.GetComponentsInChildren<SkinnedMeshRenderer>().Count(r=>r.enabled&&!r.name.EndsWith("_Prop"))!=1){Finish("FAIL: duplicate/missing body "+c.name);return;}
        }
        if(!projected&&next<customers.Length&&traffic.TryBegin(new Customer{id="route-qa-"+next,spent=12,purchases=new[]{new Purchase{shelfId=CheckoutShelfSlots.Ids[next%CheckoutShelfSlots.Ids.Length],quantity=1}}},customers[next]))
        {Debug.Log("CUSTOMER_ROUTE_STARTED "+customers[next].name);next++;}
        if((projected?traffic.CompletedVisits==10:next==customers.Length&&traffic.CompletedVisits==customers.Length)&&!customers.Any(c=>c.Reserved)){Finish("PASS: "+traffic.CompletedVisits+" customers parked, shopped, paid and returned via sidewalks; paid="+traffic.PaidVisits+" pickup="+picked.Count+" scanned="+scanned.Count);return;}
        if(Time.time-started>1500)Finish("FAIL: visit timeout "+string.Join(",",customers.Where(c=>c.Reserved).Select(c=>c.name+" "+c.transform.position)));
    }
    static void Finish(string status){Status=status;Time.timeScale=oldScale;EditorApplication.update-=Tick;Debug.Log("CUSTOMER_ROUTE_QA "+status);}
}
