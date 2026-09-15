using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.AI;
using Checkout;
public static class CheckoutShopUpgradePlaytest
{
    [MenuItem("Supermarket/Validate purchased shelf slots")]
    public static void Validate()
    {
        if(!EditorApplication.isPlaying)throw new InvalidOperationException("Run in Play Mode after CheckoutBridge starts");
        var slots=UnityEngine.Object.FindAnyObjectByType<CheckoutShelfSlots>();
        var bridge=UnityEngine.Object.FindAnyObjectByType<CheckoutBridge>();
        var all=CheckoutShelfSlots.Ids.Select(id=>new Shelf{id=id,unlocked=true,category="mercearia"}).ToArray();
        try
        {
            foreach(int count in new[]{4,5,6,7,4})
            {
                for(int i=0;i<all.Length;i++)all[i].unlocked=i<count;
                slots.Apply(all);
                if(slots.transform.Cast<Transform>().Count(t=>t.gameObject.activeSelf)!=count)throw new Exception("Wrong visible shelf count: "+count);
            }
            all[0].category="bebidas";slots.Apply(all);if(!slots.transform.Find("produce/BeverageShelf").gameObject.activeSelf)throw new Exception("Drink assignment did not select beverage shelf");
            all[0].category="limpeza";slots.Apply(all);if(!slots.transform.Find("produce/GroceryDisplay").gameObject.activeSelf)throw new Exception("Household assignment did not select display");
            all[0].category="mercearia";slots.Apply(all);if(!slots.transform.Find("produce/GroceryShelf").gameObject.activeSelf)throw new Exception("Grocery assignment did not select shelf");
            foreach(var p in CheckoutShelfSlots.Positions)
            {
                var path=new NavMeshPath();var approach=p+Vector3.back*1.05f;
                if(!NavMesh.SamplePosition(approach,out var hit,.25f,NavMesh.AllAreas)||!NavMesh.CalculatePath(new Vector3(-1.75f,.74f,-6),hit.position,NavMesh.AllAreas,path)||path.status!=NavMeshPathStatus.PathComplete)throw new Exception("Shelf is unreachable: "+p);
            }
            var cashier=UnityEngine.Object.FindAnyObjectByType<CheckoutCashier>();
            foreach(string name in new[]{"Idle","ScanItems","ReceivePayment"})if(!cashier.player[name])throw new Exception("Missing cashier animation "+name);
            Debug.Log("SHOP_UPGRADE_TEST_OK counts=4,5,6,7,4 categories=3 reachableShelves=7 cashierClips=3");
        }
        finally{slots.Apply(bridge.State?.shelves??all);}
    }
}
