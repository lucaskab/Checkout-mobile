using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MarketDay;

public static class CheckoutMapModelsBuilder
{
    const string AssetRoot = "Assets/Art/Models/MapModels/";
    const string WorldPath = "Assets/Art/Models/MarketWorld.fbx";
    const string VisualName = "ReplacementVisual";

    [MenuItem("Supermarket/Apply supplied map models")]
    public static void Apply()
    {
        EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
        ApplyToWorld(UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world);
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        AssetDatabase.SaveAssets();
        MarketBuilder.Capture("/tmp/checkout-map-after.png");
        Debug.Log("CHECKOUT_MAP_MODELS_OK");
    }

    public static void ApplyToWorld(Transform world)
    {
        Replace(world, "Anim_Truck_5", "DeliveryTruck");
        Replace(world, "Anim_Truck_8", "FishDeliveryTruck");
        Replace(world, "Anim_Truck_11", "IceCreamTruck");
        Replace(world, "Warehouse", "Warehouse");
        ReplaceShelves(world);
        CheckoutStructureBuilder.ApplyToWorld(world);
        CheckoutSectorModelsBuilder.ApplyToWorld(world);
        CheckoutTerrainBuilder.ApplyToWorld(world);
        CheckoutDeliveryModelsBuilder.ApplyToWorld(world);
    }

    static void Replace(Transform world, string targetName, string modelName)
    {
        var target = world.Find(targetName);
        if (!target) throw new InvalidOperationException("Missing map object: " + targetName);
        var existing = target.Find(VisualName);
        if (existing) UnityEngine.Object.DestroyImmediate(existing.gameObject);
        var legacy = target.GetComponentsInChildren<Renderer>(true);
        var footprint = BoundsOf(legacy);
        foreach (var renderer in legacy) renderer.enabled = false;
        var visual = Create(target, modelName, VisualName, 180f);
        var bounds = BoundsOf(visual.GetComponentsInChildren<Renderer>());
        var scale = Mathf.Min(footprint.size.x / bounds.size.x,
            footprint.size.y / bounds.size.y, footprint.size.z / bounds.size.z);
        visual.localScale *= scale;
        bounds = BoundsOf(visual.GetComponentsInChildren<Renderer>());
        visual.position += new Vector3(footprint.center.x - bounds.center.x,
            footprint.min.y - bounds.min.y, footprint.center.z - bounds.center.z);
        ValidateFit(visual, footprint, footprint.min.y);
    }

    static void ReplaceShelves(Transform world)
    {
        var root = world.Find("Groceries");
        if (!root) throw new InvalidOperationException("Missing Groceries.");
        foreach (var child in root.Cast<Transform>().Where(t => t.name.StartsWith(VisualName)).ToArray())
            UnityEngine.Object.DestroyImmediate(child.gameObject);

        // The original FBX combines both aisle fixtures with the rear coffee rack.
        // Keep the rear fixture and remove only triangles within the two aisle footprints.
        var importer = (ModelImporter)AssetImporter.GetAtPath(WorldPath);
        var readable = importer.isReadable;
        try
        {
            importer.isReadable = true;
            importer.SaveAndReimport();
            var source = AssetDatabase.LoadAssetAtPath<GameObject>(WorldPath).transform.Find("Groceries").GetComponent<MeshFilter>().sharedMesh;
            var mesh = UnityEngine.Object.Instantiate(source);
            mesh.name = "GroceriesWithoutAisleFixtures";
            var vertices = mesh.vertices;
            for (int submesh = 0; submesh < mesh.subMeshCount; submesh++)
            {
                var indices = mesh.GetTriangles(submesh);
                var kept = new System.Collections.Generic.List<int>();
                for (int i = 0; i < indices.Length; i += 3)
                {
                    var center = root.TransformPoint((vertices[indices[i]] + vertices[indices[i + 1]] + vertices[indices[i + 2]]) / 3f);
                    bool snacks = Mathf.Abs(center.x + 1.6f) < .8f && Mathf.Abs(center.z - .3f) < 2.1f;
                    bool drinks = Mathf.Abs(center.x - 2f) < .8f && Mathf.Abs(center.z + 1.18f) < 2.6f;
                    if (!snacks && !drinks) kept.AddRange(new[] { indices[i], indices[i + 1], indices[i + 2] });
                }
                mesh.SetTriangles(kept, submesh);
            }
            string path = AssetRoot + "GroceriesWithoutAisleFixtures.asset";
            var saved = AssetDatabase.LoadAssetAtPath<Mesh>(path);
            if (saved) { EditorUtility.CopySerialized(mesh, saved); UnityEngine.Object.DestroyImmediate(mesh); }
            else { AssetDatabase.CreateAsset(mesh, path); saved = mesh; }
            root.GetComponent<MeshFilter>().sharedMesh = saved;
        }
        finally { importer.isReadable = readable; importer.SaveAndReimport(); }

        Aisle(root, "DisplayShelf", new Vector3(-1.6f, .74f, .3f), new Vector3(1.45f, 1.75f, 3.895f));
        Aisle(root, "WineRack", new Vector3(2f, .74f, -1.18f), new Vector3(1.45f, 1.75f, 4.75f));
        // Supplied meshes already contain products. Keep stock roots for snapshot logic,
        // but prevent the previous product meshes from overlapping the new models.
        foreach (Transform stock in world)
            if (stock.name.StartsWith("Stock_snacks_") || stock.name.StartsWith("Stock_drinks_"))
                foreach (var renderer in stock.GetComponentsInChildren<Renderer>(true)) renderer.enabled = false;
    }

    static void Aisle(Transform root, string name, Vector3 floorCenter, Vector3 size)
    {
        var footprint = new Bounds(floorCenter + Vector3.up * size.y * .5f, size);
        for (int side = 0; side < 2; side++)
            for (int section = 0; section < 2; section++)
            {
                var visual = Create(root, name, VisualName + name + side + section, side == 0 ? 90f : -90f);
                var bounds = BoundsOf(visual.GetComponentsInChildren<Renderer>());
                visual.localScale *= Mathf.Min(size.x * .5f / bounds.size.x, size.y / bounds.size.y, size.z * .5f / bounds.size.z);
                bounds = BoundsOf(visual.GetComponentsInChildren<Renderer>());
                var center = floorCenter + new Vector3((side == 0 ? 1 : -1) * bounds.size.x * .5f, 0, (section == 0 ? -1 : 1) * bounds.size.z * .5f);
                visual.position += new Vector3(center.x - bounds.center.x, center.y - bounds.min.y, center.z - bounds.center.z);
                ValidateFit(visual, footprint, floorCenter.y);
            }
    }

    internal static Transform Create(Transform parent, string name, string instanceName, float yaw)
    {
        string folder = AssetRoot + name + "/";
        string path = folder + name + ".fbx";
        var importer = (ModelImporter)AssetImporter.GetAtPath(path);
        if (!importer) throw new InvalidOperationException("Missing supplied model: " + path);
        importer.importCameras = false;
        importer.importLights = false;
        importer.importAnimation = false;
        importer.materialImportMode = ModelImporterMaterialImportMode.None;
        if (AssetDatabase.WriteImportSettingsIfDirty(path)) AssetDatabase.ImportAsset(path);
        string texturePath = folder + name + "_BaseColor.png";
        var textureImporter = (TextureImporter)AssetImporter.GetAtPath(texturePath);
        textureImporter.maxTextureSize = 2048;
        textureImporter.sRGBTexture = true;
        textureImporter.mipmapEnabled = true;
        if (AssetDatabase.WriteImportSettingsIfDirty(texturePath)) AssetDatabase.ImportAsset(texturePath);
        string materialPath = folder + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(materialPath);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, materialPath); }
        material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
        material.SetFloat("_Glossiness", .15f);
        var model = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        var instance = (GameObject)PrefabUtility.InstantiatePrefab(model);
        instance.name = instanceName;
        instance.transform.SetParent(parent, false);
        instance.transform.rotation = Quaternion.Euler(-90f, yaw, 0f);
        foreach (var renderer in instance.GetComponentsInChildren<Renderer>()) renderer.sharedMaterial = material;
        return instance.transform;
    }

    static Bounds BoundsOf(Renderer[] renderers)
    {
        if (renderers.Length == 0) throw new InvalidOperationException("Model has no renderers.");
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers) bounds.Encapsulate(renderer.bounds);
        return bounds;
    }

    static void ValidateFit(Transform visual, Bounds footprint, float floor)
    {
        var bounds = BoundsOf(visual.GetComponentsInChildren<Renderer>());
        if (Mathf.Abs(bounds.min.y - floor) > .01f || bounds.min.x < footprint.min.x - .01f || bounds.max.x > footprint.max.x + .01f || bounds.min.z < footprint.min.z - .01f || bounds.max.z > footprint.max.z + .01f)
            throw new InvalidOperationException("Replacement exceeds its original footprint: " + visual.name);
        Debug.Log("MAP_MODEL_FIT " + visual.parent.name + "/" + visual.name + " center=" + bounds.center.ToString("F3") + " size=" + bounds.size.ToString("F3"));
    }
}
