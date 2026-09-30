using System;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

// Adds the wine cellar (adega) department: the Tripo wine rack against the east wall of the market,
// with a building site shown until the sector is unlocked (like the other production sectors).
public static class CheckoutWineSectorBuilder
{
    const string Folder = "Assets/Art/Models/MapModels/WineRack/";
    public const string Id = "adega";
    // Floor point (market floor height .74) and the direction the rack faces (into the shop).
    static readonly Vector3 Floor = new Vector3(8.45f, .74f, -2.3f);
    const float Width = 2.3f, Height = 1.75f, FacingYaw = 270f;

    [MenuItem("Supermarket/Add wine cellar sector")]
    public static void Apply()
    {
        var market = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!market || !market.world) throw new InvalidOperationException("Open the Supermarket scene first.");
        var world = market.world;
        var constructionRoot = world.Find("Sector Construction");
        if (!constructionRoot) throw new InvalidOperationException("Existing sector construction root is missing.");

        var old = world.Find("Sector_" + Id); if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var oldHolder = constructionRoot.Find(Id); if (oldHolder) UnityEngine.Object.DestroyImmediate(oldHolder.gameObject);

        var finished = new GameObject("Sector_" + Id).transform;
        finished.SetParent(world, false);
        finished.position = Floor; finished.rotation = Quaternion.identity;
        var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Folder + "WineRack.fbx"), finished);
        model.name = "Display";
        foreach (var r in model.GetComponentsInChildren<Renderer>()) r.sharedMaterial = RackMaterial();
        // Stand the rack upright with its front (the side the bottles face) looking into the shop.
        FaceFront(model.transform);
        Fit(model.transform, Floor, Width, Height);
        finished.gameObject.SetActive(false);

        var holder = new GameObject(Id).transform;
        holder.SetParent(constructionRoot, false);
        holder.position = Floor;
        var construction = new GameObject("Construction visual").transform;
        construction.SetParent(holder, false);
        var placeholder = CheckoutMapModelsBuilder.Create(construction, "ConstructionPlatform", "ConstructionPlatform", 180f);
        placeholder.rotation = Quaternion.Euler(0, FacingYaw, 0) * placeholder.rotation;
        Fit(placeholder, Floor, Width, 1.5f);
        var progress = holder.gameObject.AddComponent<CheckoutSectorProgress>();
        progress.construction = construction;
        progress.finished = finished;
        progress.worker = null;
        construction.gameObject.SetActive(true);

        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);
        EditorSceneManager.SaveScene(world.gameObject.scene);
        AssetDatabase.SaveAssets();
        Debug.Log("CHECKOUT_WINE_SECTOR_ADDED at " + Floor.ToString("F2") + " size=" + BoundsOf(model.transform).size.ToString("F2"));
    }

    // The wine rack is widest along its face; turn it so that face points along FacingYaw.
    static void FaceFront(Transform model)
    {
        var b = BoundsOf(model);
        // Thin axis = depth. Model forward (face) is the model's -depth side after import; rotate so the
        // wide side runs along the wall (world Z) and the face looks west.
        float yaw = b.size.x >= b.size.z ? FacingYaw : FacingYaw - 90f;
        model.rotation = Quaternion.Euler(0, yaw, 0) * model.rotation;
    }

    static Material RackMaterial()
    {
        string path = Folder + "WineRack.mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("Standard");
        material.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(Folder + "WineRack_Albedo.jpg"));
        var normalPath = Folder + "WineRack_Normal.png";
        var importer = AssetImporter.GetAtPath(normalPath) as TextureImporter;
        if (importer && importer.textureType != TextureImporterType.NormalMap) { importer.textureType = TextureImporterType.NormalMap; importer.SaveAndReimport(); }
        material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(normalPath));
        material.EnableKeyword("_NORMALMAP");
        material.SetFloat("_Glossiness", .35f);
        material.color = Color.white;
        EditorUtility.SetDirty(material);
        return material;
    }

    static void Fit(Transform model, Vector3 floor, float width, float maxHeight)
    {
        var bounds = BoundsOf(model);
        float along = Mathf.Max(bounds.size.x, bounds.size.z);
        model.localScale *= Mathf.Min(width / along, maxHeight / bounds.size.y);
        bounds = BoundsOf(model);
        model.position += new Vector3(floor.x - bounds.center.x, floor.y - bounds.min.y, floor.z - bounds.center.z);
    }

    static Bounds BoundsOf(Transform root)
    {
        var renderers = root.GetComponentsInChildren<Renderer>(true);
        var bounds = renderers[0].bounds;
        foreach (var renderer in renderers.Skip(1)) bounds.Encapsulate(renderer.bounds);
        return bounds;
    }
}
