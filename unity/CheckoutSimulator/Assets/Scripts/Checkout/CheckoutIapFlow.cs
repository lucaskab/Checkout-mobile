using System;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout {
 /// <summary>
 /// The rules of a real-money purchase, kept apart from the store SDK so they can be tested without a store
 /// (Editor menu Checkout › QA › Test purchases, CheckoutIapTests):
 /// - the catalog comes from the game logic (host message <c>iap-catalog</c>, src/data/currency-packs.ts);
 /// - a pending order is credited by the game logic, once per transaction (HUD action <c>grantCurrencyPack</c>);
 /// - the order is confirmed to the App Store / Google Play only after the game answered and the save was written,
 ///   so a crash in between re-delivers the purchase instead of losing it (the game ignores a transaction it already
 ///   credited, so the re-delivery is credited once);
 /// - the store's state (ready, prices, cancelled, failed, waiting approval) is reported to the host for the pages.
 /// </summary>
 public class CheckoutIapFlow {
  [Serializable] public class CatalogEntry{public string productId,packId;}
  [Serializable] class CatalogMessage{public string kind;public CatalogEntry[] products;}
  [Serializable] class StatusMessage{public string kind="iap",status="",@event="",productId="",message="";public string[] productIds,prices;}

  /// <summary>Sends a HUD action to the host and calls back with (ok, reason) when the host answers.</summary>
  public delegate void ActionSender(string action,string argsJson,Action<bool,string> answered);
  readonly ActionSender sendAction;
  readonly Action<string> sendRaw;
  readonly Action flushSave;
  readonly List<CatalogEntry> catalog=new List<CatalogEntry>();
  // Transactions credited (or being credited) in this run: a second delivery only waits for the first answer.
  readonly Dictionary<string,List<Action>> inFlight=new Dictionary<string,List<Action>>();
  readonly HashSet<string> done=new HashSet<string>();

  public IReadOnlyList<CatalogEntry> Catalog=>catalog;
  public bool HasCatalog=>catalog.Count>0;

  public CheckoutIapFlow(ActionSender sendAction,Action<string> sendRaw,Action flushSave){this.sendAction=sendAction;this.sendRaw=sendRaw;this.flushSave=flushSave;}

  /// <summary>The host's <c>iap-catalog</c> line. Returns true when the catalog changed.</summary>
  public bool ReadCatalog(string json){
   CatalogMessage m;try {m=JsonUtility.FromJson<CatalogMessage>(json);}catch {return false;}
   if(m?.products==null||m.products.Length==0)return false;
   bool changed=m.products.Length!=catalog.Count;
   for(int i=0;!changed&&i<catalog.Count;i++)changed=catalog[i].productId!=m.products[i].productId;
   catalog.Clear();foreach(var p in m.products)if(p!=null&&!string.IsNullOrEmpty(p.productId))catalog.Add(p);
   return changed;
  }

  /// <summary>
  /// The store reports a paid order (now, or again after a restart). <paramref name="confirm"/> tells the store the
  /// purchase was delivered; it runs once the game answered (credited now or already before).
  /// </summary>
  public void Pending(string productId,string transactionId,Action confirm){
   if(string.IsNullOrEmpty(productId)){Debug.LogError("CHECKOUT_IAP pending order without a product");return;}
   // StoreKit and Google Play always give one; a missing id must still be credited only once per order.
   if(string.IsNullOrEmpty(transactionId))transactionId="noid-"+productId;
   if(done.Contains(transactionId)){confirm?.Invoke();return;}
   if(inFlight.TryGetValue(transactionId,out var waiting)){if(confirm!=null)waiting.Add(confirm);return;}
   inFlight[transactionId]=new List<Action>{confirm};
   sendAction("grantCurrencyPack","["+Quote(productId)+","+Quote(transactionId)+"]",(ok,reason)=>{
    // Refused = already credited (repeated transaction) or not creditable (unknown pack): either way the game will
    // never credit it, so it is confirmed to stop the store re-delivering it forever. Logged for support.
    if(!ok)Debug.LogWarning("CHECKOUT_IAP grant refused for "+productId+" ("+transactionId+"): "+reason);
    flushSave?.Invoke();
    done.Add(transactionId);
    var callbacks=inFlight[transactionId];inFlight.Remove(transactionId);
    foreach(var c in callbacks)c?.Invoke();
   });
  }

  /// <summary>Store ready or not, with the local prices of the products it knows.</summary>
  public void ReportStatus(bool ready,IList<string> productIds=null,IList<string> prices=null,string message=""){
   var m=new StatusMessage{status=ready?"ready":"unavailable",message=message??""};
   if(productIds!=null&&prices!=null&&productIds.Count==prices.Count){m.productIds=new string[productIds.Count];m.prices=new string[prices.Count];productIds.CopyTo(m.productIds,0);prices.CopyTo(m.prices,0);}
   sendRaw(JsonUtility.ToJson(m));
  }
  /// <summary>Something happened to the purchase the player started: started, cancelled, failed, deferred.</summary>
  public void ReportEvent(string evt,string productId,string message=""){
   sendRaw(JsonUtility.ToJson(new StatusMessage{@event=evt,productId=productId??"",message=message??""}));
  }

  public static string Quote(string value)=>"\""+(value??"").Replace("\\","\\\\").Replace("\"","\\\"")+"\"";
 }
}
