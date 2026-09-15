using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using MarketDay;

public static class CheckoutBakeryDisplayBuilder
{
    const string ModelPath = "Assets/Art/Models/BakeryDisplay/BakeryDisplay.fbx";
    const float DisplayScale = 4f;

    [MenuItem("Supermarket/Apply bakery display to current scene")]
    public static void Apply()
    {
        EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation) throw new InvalidOperationException("Missing MarketSimulation.");

        ApplyToWorld(simulation.world);
        EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene());
        AssetDatabase.SaveAssets();
        Debug.Log("CHECKOUT_BAKERY_DISPLAY_OK");
    }

    public static void ApplyToWorld(Transform world)
    {
        ConfigureImports();
        var legacyParts = world.Cast<Transform>()
            .Where(child => child.name == "Bakery" || child.name.StartsWith("Stock_bakery_"))
            .ToArray();
        if (legacyParts.Length == 0) throw new InvalidOperationException("Missing Bakery in market world.");

        var sector = world.Find("Sector_padaria");
        if (!sector) throw new InvalidOperationException("Missing bakery sector root.");

        var existingDisplays = world.GetComponentsInChildren<Transform>(true)
            .Where(child => child.name == "BakeryDisplay")
            .ToArray();
        foreach (var existingDisplay in existingDisplays) UnityEngine.Object.DestroyImmediate(existingDisplay.gameObject);
        var groundY = GetBounds(sector).min.y;
        foreach (var renderer in sector.GetComponentsInChildren<Renderer>(true)) renderer.enabled = false;

        var model = AssetDatabase.LoadAssetAtPath<GameObject>(ModelPath);
        if (!model) throw new InvalidOperationException("Missing bakery display model: " + ModelPath);

        var display = (GameObject)PrefabUtility.InstantiatePrefab(model);
        display.name = "BakeryDisplay";
        display.transform.SetParent(sector, true);
        display.transform.localScale = Vector3.one * DisplayScale;
        display.transform.rotation = Quaternion.Euler(-90f, 180f, 0f);
        display.transform.position = MarketSimulation.P(-7.05f, 4.25f);

        var displayBounds = GetBounds(display.transform);
        display.transform.position += Vector3.up * (groundY - displayBounds.min.y);
        foreach (var legacyPart in legacyParts) legacyPart.gameObject.SetActive(false);

        var baker = world.Find("Worker_Baker");
        if (baker)
        {
            var bakerPosition = display.transform.TransformPoint(Vector3.zero);
            bakerPosition.y = MarketSimulation.P(0f, 0f).y;
            baker.position = bakerPosition;
            baker.rotation = Quaternion.identity;
        }
    }

    [MenuItem("Supermarket/Capture bakery display preview")]
    public static void CapturePreview()
    {
        EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
        MarketBuilder.Capture("/tmp/checkout-bakery-display.png");
        Debug.Log("CHECKOUT_BAKERY_DISPLAY_CAPTURE_OK");
    }

    public static void Validate()
    {
        EditorSceneManager.OpenScene(MarketBuilder.ScenePath);
        var world = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
        var displays = world.GetComponentsInChildren<Transform>(true)
            .Where(child => child.name == "BakeryDisplay")
            .ToArray();
        if (displays.Length != 1) throw new InvalidOperationException("Expected exactly one bakery display, found " + displays.Length + ".");
        var display = displays[0];
        var baker = world.Find("Worker_Baker");
        if (!display || !baker) throw new InvalidOperationException("Missing bakery display or baker.");

        var bounds = GetBounds(display);
        var floorY = MarketSimulation.P(0f, 0f).y;
        if (Mathf.Abs(bounds.min.y - floorY) > 0.05f) throw new InvalidOperationException("Bakery display is not grounded.");
        if (Mathf.Abs(baker.position.y - floorY) > 0.01f) throw new InvalidOperationException("Baker is not grounded.");

        var bakerLocal = display.InverseTransformPoint(baker.position);
        if (Mathf.Abs(bakerLocal.z) > 0.03f || Mathf.Abs(bakerLocal.x) > 0.49f || Mathf.Abs(bakerLocal.y) > 0.45f)
            throw new InvalidOperationException("Baker is outside the bakery footprint.");

        var vertices = display.GetComponentsInChildren<MeshFilter>().Sum(filter => filter.sharedMesh.vertexCount);
        if (vertices > 100000) throw new InvalidOperationException("Bakery display exceeds the mobile vertex budget.");
        Debug.Log("CHECKOUT_BAKERY_VALIDATION_OK vertices=" + vertices + " floor=" + bounds.min.y + " bakerLocal=" + bakerLocal);
    }

    static void ConfigureImports()
    {
        var modelImporter = (ModelImporter)AssetImporter.GetAtPath(ModelPath);
        if (!modelImporter) throw new InvalidOperationException("Missing bakery display importer.");
        modelImporter.importCameras = false;
        modelImporter.importLights = false;
        modelImporter.importAnimation = false;
        modelImporter.globalScale = 100f;
        modelImporter.isReadable = false;
        modelImporter.meshCompression = ModelImporterMeshCompression.Medium;
        modelImporter.optimizeMeshPolygons = true;
        modelImporter.optimizeMeshVertices = true;
        if (AssetDatabase.WriteImportSettingsIfDirty(ModelPath)) AssetDatabase.ImportAsset(ModelPath);

        ConfigureTexture("bakery+display+3d+model_basecolor.jpg", true, TextureImporterType.Default);
        ConfigureTexture("bakery+display+3d+model_normal.jpg", false, TextureImporterType.NormalMap);
        ConfigureTexture("bakery+display+3d+model_rm.jpg", false, TextureImporterType.Default);
    }

    static void ConfigureTexture(string name, bool sRgb, TextureImporterType type)
    {
        var path = "Assets/Art/Models/BakeryDisplay/" + name;
        var importer = (TextureImporter)AssetImporter.GetAtPath(path);
        if (!importer) return;
        importer.sRGBTexture = sRgb;
        importer.textureType = type;
        importer.maxTextureSize = 2048;
        importer.mipmapEnabled = true;
        importer.textureCompression = TextureImporterCompression.CompressedHQ;
        if (AssetDatabase.WriteImportSettingsIfDirty(path)) AssetDatabase.ImportAsset(path);
    }

    static Bounds GetBounds(Transform root)
    {
        var renderers = root.GetComponentsInChildren<Renderer>(true);
        if (renderers.Length == 0) throw new InvalidOperationException("No renderers found for " + root.name);

        var bounds = renderers[0].bounds;
        for (var index = 1; index < renderers.Length; index++) bounds.Encapsulate(renderers[index].bounds);
        return bounds;
    }

    static Bounds GetBounds(Transform[] roots)
    {
        var renderers = roots.SelectMany(root => root.GetComponentsInChildren<Renderer>(true)).ToArray();
        if (renderers.Length == 0) throw new InvalidOperationException("No bakery renderers found.");

        var bounds = renderers[0].bounds;
        for (var index = 1; index < renderers.Length; index++) bounds.Encapsulate(renderers[index].bounds);
        return bounds;
    }
}
