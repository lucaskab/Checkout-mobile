using System;
using System.Linq;
using Checkout;
using UnityEditor;
using UnityEngine;
using UnityEngine.AI;

public static class CheckoutCityTrafficPlaytest
{
    const string Pending="CheckoutCityTrafficPlaytest.Pending";
    static bool seeded;
    static float started;
    static bool captured;
    static readonly System.Collections.Generic.HashSet<CheckoutWalker> entered=new System.Collections.Generic.HashSet<CheckoutWalker>();
    [MenuItem("Supermarket/Preview city customer traffic")]
    public static void Run()
    {
        seeded=captured=false;entered.Clear();
        SessionState.SetBool(Pending,true);
        EditorApplication.update-=Tick;EditorApplication.update+=Tick;
        EditorApplication.isPlaying=true;
    }
    [InitializeOnLoadMethod] static void Initialize()
    {
        if(SessionState.GetBool(Pending,false))EditorApplication.update+=Tick;
        EditorApplication.playModeStateChanged-=OnPlayModeChanged;
        EditorApplication.playModeStateChanged+=OnPlayModeChanged;
    }
    static void OnPlayModeChanged(PlayModeStateChange state){if(state==PlayModeStateChange.ExitingPlayMode)Finish();}
    static void Tick()
    {
        if(!EditorApplication.isPlaying||EditorApplication.isCompiling)return;
        try
        {
            var bridge=UnityEngine.Object.FindAnyObjectByType<CheckoutBridge>();
            var traffic=UnityEngine.Object.FindAnyObjectByType<CheckoutCityTraffic>();
            if(!bridge||!traffic||!UnityEngine.Object.FindAnyObjectByType<CheckoutMap>())return;
            if(!seeded)
            {
                var snapshot=new Snapshot{kind="snapshot",protocol=1,session="city-traffic-preview",revision=1,isOpen=true,
                    shelves=new[]{"produce","dairy","bakery","snacks","drinks","coffee","pizza"}.Select(id=>new Shelf{id=id,unlocked=true,stock=15,capacity=20}).ToArray(),
                    sectors=new[]{"padaria","acougue","peixaria","queijaria"}.Select(id=>new Sector{id=id,unlocked=true}).ToArray(),
                    employees=Array.Empty<Employee>(),jobs=Array.Empty<Job>(),customers=Array.Empty<Customer>(),orders=Array.Empty<Order>(),expansions=Array.Empty<string>(),ownedItems=Array.Empty<string>(),@event=new MarketEvent()};
                bridge.Receive(JsonUtility.ToJson(snapshot));
                snapshot.revision=2;
                snapshot.customers=Enumerable.Range(0,6).Select(i=>new Customer{id="city-visitor-"+i,spent=12,purchases=new[]{new Purchase{shelfId=i%2==0?"snacks":"drinks",quantity=1}}}).ToArray();
                bridge.Receive(JsonUtility.ToJson(snapshot));
                for(int i=0;i<3;i++)
                {
                    var path=new NavMeshPath();
                    if(!NavMesh.SamplePosition(new Vector3(-14.35f,.15f,CheckoutCityTraffic.BayZ(i)-1.1f),out var start,.8f,NavMesh.AllAreas)||
                        !NavMesh.CalculatePath(start.position,new Vector3(-1.75f,.74f,-6),NavMesh.AllAreas,path)||path.status!=NavMeshPathStatus.PathComplete)
                        throw new Exception("Parking bay "+i+" has no path into the supermarket");
                }
                seeded=true;started=Time.time;Time.timeScale=3;
                Debug.Log("CITY_TRAFFIC_ROUTES_OK bays=3 visitors=6");return;
            }
            foreach(var pedestrian in UnityEngine.Object.FindObjectsByType<CheckoutCityPedestrian>())
                if(pedestrian.GetComponentsInChildren<Renderer>().Any(r=>r.name.EndsWith("_Prop")&&r.enabled))throw new Exception("City pedestrian is carrying a shopping basket");
            foreach(var walker in UnityEngine.Object.FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include))
            {
                if(walker.gameObject.activeSelf&&walker.transform.position.z> -6.8f&&walker.transform.position.x> -9f)entered.Add(walker);
                if(walker.HasPaid&&!walker.gameObject.activeSelf&&walker.GetComponentsInChildren<Renderer>(true).Any(r=>r.name.EndsWith("_Prop")&&r.enabled))throw new Exception("Shopping basket remained visible after returning to the car");
            }
            if(traffic.ParkedVisits>=3&&!captured){MarketBuilder.Capture("ArtSource/TerrainTiles/CityTrafficPreview.png");captured=true;}
            if(traffic.CompletedVisits>=6)
            {
                if(entered.Count<3)throw new Exception("Customers did not physically cross the supermarket entrance");
                if(traffic.PaidVisits!=6)throw new Exception("Not every visitor completed payment");
                Debug.Log("CITY_TRAFFIC_PLAYTEST_OK parked="+traffic.ParkedVisits+" paid="+traffic.PaidVisits+" departed="+traffic.CompletedVisits+" enteredActors="+entered.Count);
                Finish();
            }
            else if(Time.time-started>600)throw new Exception("Traffic timed out: parked="+traffic.ParkedVisits+" paid="+traffic.PaidVisits+" departed="+traffic.CompletedVisits+" enteredActors="+entered.Count);
        }
        catch(Exception error){Debug.LogException(error);Finish();}
    }
    static void Finish(){Time.timeScale=1;SessionState.SetBool(Pending,false);EditorApplication.update-=Tick;}
}
