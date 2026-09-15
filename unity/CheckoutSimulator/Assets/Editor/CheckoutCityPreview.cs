using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using Checkout;
public static class CheckoutCityPreview
{
    static string session;
    static int sequence;
    static float nextBatch;
    [MenuItem("Supermarket/Run continuous city preview")]
    public static void Run()
    {
        if(!EditorApplication.isPlaying)throw new InvalidOperationException("Start Play Mode first");
        var bridge=UnityEngine.Object.FindAnyObjectByType<CheckoutBridge>();
        if(bridge.State==null)throw new InvalidOperationException("Load a preview snapshot first");
        session=bridge.State.session;sequence=0;nextBatch=0;
        EditorApplication.update-=Tick;EditorApplication.update+=Tick;
        Time.timeScale=1;EditorApplication.ExecuteMenuItem("Window/General/Game");
    }
    static void Tick()
    {
        if(!EditorApplication.isPlaying){EditorApplication.update-=Tick;return;}
        var bridge=UnityEngine.Object.FindAnyObjectByType<CheckoutBridge>();
        if(!bridge||bridge.State==null||bridge.State.session!=session){EditorApplication.update-=Tick;return;}
        if(Time.time<nextBatch)return;
        if(UnityEngine.Object.FindObjectsByType<CheckoutWalker>(FindObjectsInactive.Include).Any(w=>w.Reserved))return;
        var snapshot=JsonUtility.FromJson<Snapshot>(JsonUtility.ToJson(bridge.State));
        var shelves=snapshot.shelves.Where(s=>s.unlocked&&s.stock>0).ToArray();if(shelves.Length==0)return;
        snapshot.revision++;
        string batch="editor-preview-"+DateTime.UtcNow.Ticks+"-"+(sequence++);
        snapshot.customers=Enumerable.Range(0,3).Select(i=>new Customer{id=batch+"-"+i,spent=12,purchases=shelves.OrderBy(s=>UnityEngine.Random.value).Take(UnityEngine.Random.Range(1,Math.Min(3,shelves.Length)+1)).Select(s=>new Purchase{shelfId=s.id,quantity=1}).ToArray()}).ToArray();
        bridge.Receive(JsonUtility.ToJson(snapshot));nextBatch=Time.time+20;
    }
}
