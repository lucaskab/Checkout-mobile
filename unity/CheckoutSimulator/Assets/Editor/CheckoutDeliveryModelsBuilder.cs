using System;
using System.Linq;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class CheckoutDeliveryModelsBuilder
{
    const string WorkerFolder = "Assets/Art/Characters/Meshy/Workers/";
    const string CargoRoot = "Supplied Delivery Cargo";
    static readonly string[] Clips = { "Idle", "Walking", "CarryIdle", "CarryWalking", "Pickup", "PutDown" };

    [MenuItem("Supermarket/Apply supplied produce and delivery models")]
    public static void Apply()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode before replacing delivery assets.");
        var world = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        ApplyToWorld(world);
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);
        EditorSceneManager.SaveScene(world.gameObject.scene);
        AssetDatabase.SaveAssets();
        Debug.Log("CHECKOUT_DELIVERY_MODELS_OK");
    }

    public static void ApplyToWorld(Transform world)
    {
        var produce = world.Find("Produce");
        var old = produce.Find("ReplacementVisual");
        if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        foreach (var renderer in produce.GetComponentsInChildren<Renderer>(true)) renderer.enabled = false;
        Fit(produce, "FruitMarketStand", "ReplacementVisual", new Vector3(6.55f,.74f,.45f), new Vector3(2.9f,1.6f,2.2f), 180);
        foreach (Transform stock in world)
            if (stock.name.StartsWith("Stock_produce_"))
                foreach (var renderer in stock.GetComponentsInChildren<Renderer>(true)) renderer.enabled = false;

        old = world.Find(CargoRoot);
        if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var root = new GameObject(CargoRoot).transform;
        root.SetParent(world, false);
        root.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
        foreach (var renderer in world.Find("Delivery").GetComponentsInChildren<Renderer>(true)) renderer.enabled = false;
        Fit(root,"VegetableCrate","Fresh vegetable crate",new Vector3(-4.2f,.15f,16.15f),new Vector3(.9f,.5f,.8f),180);
        Fit(root,"VegetableCrate","Vegetable crate stack",new Vector3(-4.2f,.59f,16.15f),new Vector3(.9f,.5f,.8f),180);
        Fit(root,"CardboardBox","Storage parcel",new Vector3(-3.1f,.15f,16.15f),new Vector3(.75f,.55f,.72f),180);

        var cargo = new GameObject("Carried cardboard box").transform;
        cargo.SetParent(root, false);
        Fit(cargo,"CardboardBox","Visual",Vector3.zero,new Vector3(.82f,.57f,.72f),180);
        // Cargo root is bottom-centred, including when the hands release it on the porch.
        var marker = new GameObject("Warehouse delivery doorstep").transform;
        marker.SetParent(root, false);
        marker.position = new Vector3(-1.65f,.15f,16.72f);
        ConfigureWorker(world, cargo, marker);
    }

    static void ConfigureWorker(Transform world, Transform cargo, Transform doorstep)
    {
        string path = WorkerFolder + "Worker_Delivery.fbx";
        var importer = (ModelImporter)AssetImporter.GetAtPath(path);
        importer.animationType = ModelImporterAnimationType.Legacy;
        importer.importAnimation = true;
        importer.importCameras = importer.importLights = false;
        importer.materialImportMode = ModelImporterMaterialImportMode.None;
        importer.animationCompression = ModelImporterAnimationCompression.Off;
        var clips = importer.defaultClipAnimations;
        foreach (var clip in clips)
        {
            foreach (string name in Clips.OrderByDescending(n=>n.Length)) if (clip.name.EndsWith(name)) { clip.name = name; break; }
            clip.loopTime = clip.name.Contains("Walking") || clip.name.Contains("Idle");
            clip.wrapMode = clip.loopTime ? WrapMode.Loop : WrapMode.ClampForever;
        }
        importer.clipAnimations = clips;
        importer.SaveAndReimport();
        var textureImporter = (TextureImporter)AssetImporter.GetAtPath(WorkerFolder + "Worker_Delivery.png");
        textureImporter.maxTextureSize = 2048;
        textureImporter.sRGBTexture = true;
        textureImporter.mipmapEnabled = true;
        textureImporter.SaveAndReimport();
        var material = AssetDatabase.LoadAssetAtPath<Material>(WorkerFolder + "Worker_Delivery.mat");
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material,WorkerFolder + "Worker_Delivery.mat"); }
        material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(WorkerFolder + "Worker_Delivery.png");
        material.SetFloat("_Glossiness",.1f);
        EditorUtility.SetDirty(material);
        var worker = world.Find("Worker_Delivery");
        var old = worker.Find("Visual");
        if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var genericAnimator = worker.GetComponent<MarketCharacterAnimator>();
        if (genericAnimator) UnityEngine.Object.DestroyImmediate(genericAnimator);
        var visual = UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path),worker);
        visual.name = "Visual";
        visual.transform.localPosition = Vector3.zero;
        visual.transform.localRotation = Quaternion.identity;
        var player = visual.GetComponent<Animation>() ?? visual.AddComponent<Animation>();
        foreach (var clip in AssetDatabase.LoadAllAssetsAtPath(path).OfType<AnimationClip>().Where(c=>!c.name.StartsWith("__preview__"))) player.AddClip(clip,clip.name);
        foreach (string name in Clips) if (!player[name]) throw new InvalidOperationException("Missing delivery animation: " + name);
        player.playAutomatically = false;
        player.cullingType = AnimationCullingType.AlwaysAnimate;
        foreach (var renderer in visual.GetComponentsInChildren<Renderer>()) renderer.sharedMaterial = material;
        foreach (var renderer in visual.GetComponentsInChildren<SkinnedMeshRenderer>()) renderer.updateWhenOffscreen = true;
        var delivery = worker.GetComponent<MarketDeliveryWorker>() ?? worker.gameObject.AddComponent<MarketDeliveryWorker>();
        delivery.animationPlayer = player;
        delivery.leftHand = visual.GetComponentsInChildren<Transform>().Single(t=>t.name=="Hand_L");
        delivery.rightHand = visual.GetComponentsInChildren<Transform>().Single(t=>t.name=="Hand_R");
        delivery.truck = world.Find("Anim_Truck_5");
        delivery.truckHome = delivery.truck.position;
        delivery.cargo = cargo;
        delivery.storageDoor = doorstep;
        delivery.pickupPoint = new Vector3(6.5f,.85f,17.34f);
        delivery.route = new[] { new Vector3(-1.65f,.15f,16.19f),new Vector3(3.7f,.15f,16.19f),new Vector3(4.65f,.15f,16.85f),new Vector3(6.5f,.15f,16.85f) };
        worker.SetPositionAndRotation(delivery.route[0],Quaternion.identity);
        cargo.position = delivery.pickupPoint;
        EditorUtility.SetDirty(delivery);
    }

    static Transform Fit(Transform parent, string model, string name, Vector3 floor, Vector3 size, float yaw)
    {
        var visual = CheckoutMapModelsBuilder.Create(parent,model,name,yaw);
        Bounds BoundsOf() { var rs=visual.GetComponentsInChildren<Renderer>();var b=rs[0].bounds;foreach(var r in rs)b.Encapsulate(r.bounds);return b; }
        var bounds = BoundsOf();
        visual.localScale *= Mathf.Min(size.x/bounds.size.x,size.y/bounds.size.y,size.z/bounds.size.z);
        bounds = BoundsOf();
        visual.position += new Vector3(floor.x-bounds.center.x,floor.y-bounds.min.y,floor.z-bounds.center.z);
        return visual;
    }
}
