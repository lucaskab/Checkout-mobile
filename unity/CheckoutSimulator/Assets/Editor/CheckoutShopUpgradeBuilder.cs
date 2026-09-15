using System;
using System.Linq;
using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;
using MarketDay;
using Checkout;
public static class CheckoutShopUpgradeBuilder
{
    const string Root="Assets/Art/Models/MapModels/";
    static readonly string[] Clips={"Idle","Walking","GetFromShelf","BuyAtSpecialSector","PayAtCheckout","ScanItems","ReceivePayment"};
    public static void Apply()
    {
        var world=UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        if(world.Find("Owned Shelf Slots"))throw new InvalidOperationException("Shop upgrade already applied");
        foreach(Transform t in world)
            if(t.name.StartsWith("ReplacementVisualWineRack")||t.name.StartsWith("ReplacementVisualDisplayShelf")||t.name=="Produce"||t.name.StartsWith("Stock_"))
                foreach(var r in t.GetComponentsInChildren<Renderer>(true)){Undo.RecordObject(r,"Replace slot shelves");r.enabled=false;}
        var slots=new GameObject("Owned Shelf Slots").transform;slots.SetParent(world);slots.SetPositionAndRotation(Vector3.zero,Quaternion.identity);slots.localScale=Vector3.one;slots.gameObject.AddComponent<CheckoutShelfSlots>();Undo.RegisterCreatedObjectUndo(slots.gameObject,"Create purchased shelf slots");
        for(int i=0;i<CheckoutShelfSlots.Ids.Length;i++)
        {
            var slot=new GameObject(CheckoutShelfSlots.Ids[i]).transform;slot.SetParent(slots,false);
            foreach(string model in new[]{"BeverageShelf","GroceryShelf","GroceryDisplay"})
            {
                var visual=CheckoutMapModelsBuilder.Create(slot,model,model,180);var b=BoundsOf(visual);
                visual.localScale*=Mathf.Min(2/b.size.x,1.85f/b.size.y,1.35f/b.size.z);b=BoundsOf(visual);
                var p=CheckoutShelfSlots.Positions[i];visual.position+=new Vector3(p.x-b.center.x,p.y-b.min.y,p.z-b.center.z);
                visual.gameObject.SetActive(model==(i==0?"GroceryDisplay":i==4?"BeverageShelf":"GroceryShelf"));
            }
            slot.gameObject.SetActive(i<4);
        }
        var counter=world.Find("Checkout/ReplacementVisual");var center=BoundsOf(counter).center;Undo.RecordObject(counter,"Turn checkout towards customer lane");counter.RotateAround(center,Vector3.up,180);
        var cashier=world.Find("Worker_Cashier");var player=Character(cashier,"CheckoutWoman");cashier.SetPositionAndRotation(new Vector3(-3.75f,.74f,-3.85f),Quaternion.Euler(0,270,0));
        var old=cashier.GetComponent<MarketCharacterAnimator>();if(old)UnityEngine.Object.DestroyImmediate(old);
        var service=cashier.gameObject.AddComponent<CheckoutCashier>();service.player=player;
        var item=GameObject.CreatePrimitive(PrimitiveType.Cube);item.name="Checkout scanned item";item.transform.SetParent(cashier,true);item.transform.localScale=new Vector3(.16f,.21f,.13f);UnityEngine.Object.DestroyImmediate(item.GetComponent<Collider>());
        var material=new Material(Shader.Find("Standard")){color=new Color(.94f,.58f,.19f)};AssetDatabase.CreateAsset(material,Root+"CheckoutWoman/ScannedItem.mat");item.GetComponent<Renderer>().sharedMaterial=material;item.SetActive(false);service.item=item.transform;
        var customer=world.Find("Customer_01");player=Character(customer,"GirlCustomer");var motion=customer.GetComponent<MarketCharacterAnimator>();if(!motion)motion=customer.gameObject.AddComponent<MarketCharacterAnimator>();motion.animationPlayer=player;
        // Keep the supplied girl in the established customer pool and its complete visit lifecycle.
        var hand=player.GetComponentsInChildren<Transform>().First(t=>t.name=="Hand_L");
        var basket=new GameObject("Girl shopping basket").transform;basket.SetParent(hand,false);basket.localScale=Vector3.one/hand.lossyScale.x;basket.localPosition=new Vector3(0,-.1f/hand.lossyScale.y,0);
        var basketMat=new Material(Shader.Find("Standard")){color=new Color(.13f,.48f,.4f)};AssetDatabase.CreateAsset(basketMat,Root+"GirlCustomer/Basket.mat");
        void BasketPart(Vector3 p,Vector3 size){var o=GameObject.CreatePrimitive(PrimitiveType.Cube);o.name="GirlBasket_Prop";o.transform.SetParent(basket,false);o.transform.localPosition=p;o.transform.localScale=size;UnityEngine.Object.DestroyImmediate(o.GetComponent<Collider>());o.GetComponent<Renderer>().sharedMaterial=basketMat;o.GetComponent<Renderer>().enabled=false;}
        BasketPart(new Vector3(0,-.25f,0),new Vector3(.42f,.04f,.28f));
        BasketPart(new Vector3(-.2f,-.14f,0),new Vector3(.035f,.22f,.28f));BasketPart(new Vector3(.2f,-.14f,0),new Vector3(.035f,.22f,.28f));
        BasketPart(new Vector3(0,-.14f,-.13f),new Vector3(.42f,.22f,.035f));BasketPart(new Vector3(0,-.14f,.13f),new Vector3(.42f,.22f,.035f));
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);EditorSceneManager.SaveScene(world.gameObject.scene);AssetDatabase.SaveAssets();Debug.Log("SHOP_UPGRADE_APPLIED slots=7 customer=GirlCustomer cashier=CheckoutWoman");
    }
    static Animation Character(Transform actor,string name)
    {
        string folder=Root+name+"/",path=folder+name+"Animated.fbx";
        var importer=(ModelImporter)AssetImporter.GetAtPath(path);importer.animationType=ModelImporterAnimationType.Legacy;importer.importAnimation=true;importer.importCameras=importer.importLights=false;importer.materialImportMode=ModelImporterMaterialImportMode.None;importer.animationCompression=ModelImporterAnimationCompression.Off;
        var clips=importer.defaultClipAnimations;foreach(var c in clips){foreach(string n in Clips)if(c.name.EndsWith(n)){c.name=n;break;}c.loopTime=c.name=="Idle"||c.name=="Walking";c.wrapMode=c.loopTime?WrapMode.Loop:WrapMode.ClampForever;}importer.clipAnimations=clips;importer.SaveAndReimport();
        foreach(var r in actor.GetComponentsInChildren<Renderer>(true))r.enabled=false;
        foreach(var animation in actor.GetComponentsInChildren<Animation>(true))animation.enabled=false;
        foreach(Transform child in actor)child.gameObject.SetActive(false);
        var visual=UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path),actor);visual.name="Supplied animated visual";visual.transform.localPosition=Vector3.zero;visual.transform.localRotation=Quaternion.Euler(0,180,0);visual.transform.localScale=Vector3.one*.85f;
        var mat=new Material(Shader.Find("Standard"));mat.mainTexture=AssetDatabase.LoadAssetAtPath<Texture2D>(folder+name+"_BaseColor.png");mat.SetFloat("_Glossiness",.1f);AssetDatabase.CreateAsset(mat,folder+name+"Animated.mat");
        foreach(var r in visual.GetComponentsInChildren<Renderer>())r.sharedMaterial=mat;
        foreach(var r in visual.GetComponentsInChildren<SkinnedMeshRenderer>())r.updateWhenOffscreen=true;
        var player=visual.GetComponent<Animation>();if(!player)player=visual.AddComponent<Animation>();foreach(var clip in AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(c=>!c.name.StartsWith("__preview__")))player.AddClip(clip,clip.name);
        foreach(string clip in Clips)if(!player[clip])throw new InvalidOperationException("Missing supplied character clip "+clip);
        player.playAutomatically=false;player.cullingType=AnimationCullingType.AlwaysAnimate;return player;
    }
    static Bounds BoundsOf(Transform t){var rs=t.GetComponentsInChildren<Renderer>();var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);return b;}
}
