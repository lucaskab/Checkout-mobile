using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Purchasing;
// The game's snapshot has its own Order (a supplier truck): this one is the store's.
using StoreOrder = UnityEngine.Purchasing.Order;

namespace Checkout {
 /// <summary>
 /// Real-money purchases of diamonds and coins (Lucas 12/10) through Unity IAP 5: the App Store on the iPhone,
 /// Google Play on Android, Unity's fake store in the Editor. Desktop builds (the testers' Windows / Mac builds) get no
 /// store at all: Unity IAP would fall back to its FakeStore there, which "sells" for free, so the diamond store says it
 /// is unavailable instead.
 ///
 /// Flow (rules in <see cref="CheckoutIapFlow"/>):
 /// 1. The host sends the catalog (<c>iap-catalog</c>, src/data/currency-packs.ts) → connect, fetch the products,
 ///    report the local prices to the host (the diamond store shows them).
 /// 2. "Comprar" in the diamond store → host → <c>purchase</c> → <see cref="StoreController.PurchaseProduct(string)"/>.
 /// 3. The store reports the paid order (<c>OnPurchasePending</c>, also on the next launch when it was never confirmed)
 ///    → the game credits the pack once per transaction (grantCurrencyPack), the save is written, then the order is
 ///    confirmed (<c>ConfirmPurchase</c>).
 /// All products are consumables: diamonds and coins are spent; the welcome combo's "once" is the game's rule.
 /// Apple validates the purchase on the device (StoreKit 2); server-side validation of the JWS is a later step.
 /// </summary>
 [DefaultExecutionOrder(-550)]
 public class CheckoutIap:MonoBehaviour {
  public static CheckoutIap Active {get;private set;}
  CheckoutDesktopHost host;CheckoutIapFlow flow;
  StoreController store;bool connecting,connected,subscribed;
  const float RetrySeconds=30;

  public static void Attach(CheckoutDesktopHost owner){
   if(Active||!owner)return;
   var iap=owner.gameObject.AddComponent<CheckoutIap>();iap.host=owner;
   iap.flow=new CheckoutIapFlow(
    (action,args,answered)=>owner.Action(action,args,"",answered),
    json=>owner.Send(json),
    owner.Flush);
   Active=iap;
  }

  /// <summary>Host line <c>iap-catalog</c>: the packs to sell.</summary>
  public void Catalog(string json){
   bool changed=flow.ReadCatalog(json);
   flow.ReportRegion();
   if(!StoreSupported){flow.ReportStatus(false,null,null,"no store on this platform");return;}
   if(!connected){Connect();return;}
   if(changed)Fetch();else ReportPrices();
  }

  /// <summary>Host line <c>purchase</c>: the player pressed "Comprar".</summary>
  [Serializable] class PurchaseMessage{public string productId,packId;}
  public void Purchase(string json){
   var m=JsonUtility.FromJson<PurchaseMessage>(json);var id=m?.productId;
   if(string.IsNullOrEmpty(id))return;
   var product=connected?store.GetProductById(id):null;
   if(product==null||!product.availableToPurchase){flow.ReportEvent("failed",id,"product not available");return;}
   flow.ReportEvent("started",id);
   try {store.PurchaseProduct(product);}
   catch(Exception ex){Debug.LogWarning("CHECKOUT_IAP purchase not started: "+ex.Message);flow.ReportEvent("failed",id,ex.Message);}
  }

  /// <summary>Host line <c>iap-retry</c>: "Tentar de novo" on the diamond store when the store did not answer.</summary>
  public void RetryNow(){
   if(!StoreSupported){flow.ReportStatus(false,null,null,"no store on this platform");return;}
   if(!connected){CancelInvoke(nameof(Reconnect));Connect();}
   else if(flow.HasCatalog)Fetch();
   else ReportPrices();
  }

  // A real store (or the Editor's fake one for testing): never the FakeStore of a desktop build.
  static bool StoreSupported=>Application.isEditor||Application.platform==RuntimePlatform.IPhonePlayer||Application.platform==RuntimePlatform.Android;

  async void Connect(){
   if(connecting||connected)return;connecting=true;
   try {
    store??=UnityIAPServices.StoreController();
    if(!subscribed)Subscribe();
    await store.Connect();
   } catch(Exception ex){
    Debug.LogWarning("CHECKOUT_IAP store unavailable: "+ex.Message);
    flow.ReportStatus(false,null,null,ex.Message);
    Retry();
   } finally {connecting=false;}
  }
  // Offline at launch, or the connection dropped: try again in a while (the store page says it is unavailable).
  void Retry(){CancelInvoke(nameof(Reconnect));Invoke(nameof(Reconnect),RetrySeconds);}
  void Reconnect(){if(!connected&&!connecting)Connect();}

  void Subscribe(){
   subscribed=true;
    // Every event before Connect: a purchase left unconfirmed by the last run may arrive at once.
    store.OnStoreConnected+=OnConnected;
    store.OnStoreDisconnected+=OnDisconnected;
    store.OnProductsFetched+=OnProductsFetched;
    store.OnProductsFetchFailed+=OnProductsFetchFailed;
    store.OnPurchasesFetched+=OnPurchasesFetched;
    store.OnPurchasesFetchFailed+=OnPurchasesFetchFailed;
    store.OnPurchasePending+=OnPurchasePending;
    store.OnPurchaseConfirmed+=OnPurchaseConfirmed;
    store.OnPurchaseFailed+=OnPurchaseFailed;
    store.OnPurchaseDeferred+=OnPurchaseDeferred;
  }

  void OnConnected(){connected=true;Fetch();store.FetchPurchases();}
  void OnDisconnected(StoreConnectionFailureDescription failure){
   connected=false;Debug.LogWarning("CHECKOUT_IAP store disconnected: "+failure?.Message);
   flow.ReportStatus(false,null,null,failure?.Message);
   Retry();
  }
  void Fetch(){
   if(!flow.HasCatalog)return;
   store.FetchProducts(flow.Catalog.Select(p=>new ProductDefinition(p.productId,ProductType.Consumable)).ToList());
  }
  void OnProductsFetched(List<Product> products){ReportPrices();}
  void OnProductsFetchFailed(ProductFetchFailed failure){
   Debug.LogWarning("CHECKOUT_IAP products not fetched: "+failure?.FailureReason);
   // Some products may still have come: the store is usable for those.
   ReportPrices();
  }
  void ReportPrices(){
   var ids=new List<string>();var prices=new List<string>();
   foreach(var product in store.GetProducts()){
    if(product==null||!product.availableToPurchase)continue;
    // The Editor's fake store prices everything "$0.01": the game's regional table shows instead.
    ids.Add(product.definition.id);prices.Add(Application.isEditor?"":product.metadata.localizedPriceString??"");
   }
   flow.ReportStatus(ids.Count>0,ids,prices,ids.Count>0?"":"no products in the store");
  }
  void OnPurchasesFetched(Orders orders){Debug.Log("CHECKOUT_IAP purchases fetched: "+(orders?.PendingOrders?.Count??0)+" pending");}
  void OnPurchasesFetchFailed(PurchasesFetchFailureDescription failure){Debug.LogWarning("CHECKOUT_IAP purchases not fetched: "+failure?.Message);}

  void OnPurchasePending(PendingOrder order){
   var product=order?.CartOrdered?.Items()?.FirstOrDefault()?.Product;
   var id=product?.definition?.id;
   flow.Pending(id,order?.Info?.TransactionID,()=>store.ConfirmPurchase(order));
  }
  void OnPurchaseConfirmed(StoreOrder order){
   if(!(order is ConfirmedOrder))Debug.LogWarning("CHECKOUT_IAP confirmation not completed: "+order?.GetType().Name);
  }
  void OnPurchaseFailed(FailedOrder failed){
   var id=failed?.CartOrdered?.Items()?.FirstOrDefault()?.Product?.definition?.id??"";
   bool cancelled=failed!=null&&failed.FailureReason==PurchaseFailureReason.UserCancelled;
   if(!cancelled)Debug.LogWarning("CHECKOUT_IAP purchase failed: "+failed?.FailureReason+" "+failed?.Details);
   flow.ReportEvent(cancelled?"cancelled":"failed",id,failed?.Details??"");
  }
  void OnPurchaseDeferred(DeferredOrder deferred){
   var id=deferred?.CartOrdered?.Items()?.FirstOrDefault()?.Product?.definition?.id??"";
   flow.ReportEvent("deferred",id);
  }

  void OnDestroy(){if(Active==this)Active=null;}
 }
}
