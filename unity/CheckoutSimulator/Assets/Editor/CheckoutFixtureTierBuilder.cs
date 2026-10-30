using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Checkout;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

// "Evoluções dos móveis" (docs-drafts/evolucoes-moveis.md): one prefab per approved tier model, built from the FBX
// exports (ArtSource/fixture_tiers/export -> Assets/Art/Interior/Models/Tiers) with the kit's materials (KitRemap:
// "Cores do mercado" paints the navy and gold, never the products), the stock groups ("Anim Fill n") and the
// footprint / service points the furniture code reads (CheckoutInteriorPiece). The prefabs live in
// Resources/CheckoutFixtureTiers/<kind>_T<n> and CheckoutInterior loads them by name when the Interior Kit has no
// template of that name, so the scene does not change. Also renders the build tray's pictures
// (Resources/CheckoutDesktop/Decor/<template>.png) inside Unity.
public static partial class CheckoutMarketStagesBuilder
{
    const string TierModels = "Assets/Art/Interior/Models/Tiers/";
    const string TierPrefabs = "Assets/Resources/CheckoutFixtureTiers/";
    const string DecorSprites = "Assets/Resources/CheckoutDesktop/Decor/";

    // Footprints in metres (width x depth), from ArtSource/fixture_tiers/export/README.md and src/data/fixture-tiers.ts.
    static readonly Dictionary<string, Vector2> TierFootprints = new Dictionary<string, Vector2>
    {
        { "shelf_T1", new Vector2(1f, .5f) }, { "shelf_T2", new Vector2(1.5f, .5f) }, { "shelf_T3", new Vector2(2f, .75f) }, { "shelf_T4", new Vector2(2.5f, 1f) },
        { "produce_T1", new Vector2(1f, .75f) }, { "produce_T2", new Vector2(1.5f, .75f) }, { "produce_T3", new Vector2(2f, 1f) }, { "produce_T4", new Vector2(2.5f, 1.25f) },
        { "drinks_T1", new Vector2(.75f, .75f) }, { "drinks_T2", new Vector2(1.25f, .75f) }, { "drinks_T3", new Vector2(2f, .75f) }, { "drinks_T4", new Vector2(2.5f, 1f) },
        { "dairy_T1", new Vector2(1f, .75f) }, { "dairy_T2", new Vector2(1.5f, .75f) }, { "dairy_T3", new Vector2(2f, 1f) }, { "dairy_T4", new Vector2(2.5f, 1f) },
        { "bakery_T1", new Vector2(1f, .5f) }, { "bakery_T2", new Vector2(1.5f, .5f) }, { "bakery_T3", new Vector2(2f, .75f) }, { "bakery_T4", new Vector2(2f, 1f) },
        { "freezer_T1", new Vector2(1f, .75f) }, { "freezer_T2", new Vector2(1.5f, .75f) }, { "freezer_T3", new Vector2(1.5f, .9f) }, { "freezer_T4", new Vector2(2.5f, 1.25f) },
        { "icecream_T1", new Vector2(1f, .75f) }, { "icecream_T2", new Vector2(1.5f, .75f) }, { "icecream_T3", new Vector2(2f, 1f) }, { "icecream_T4", new Vector2(2.5f, 1f) },
        { "checkout_T1", new Vector2(1.25f, 1.25f) }, { "checkout_T2", new Vector2(1.75f, 1.5f) }, { "checkout_T3", new Vector2(2.5f, 1.75f) }, { "checkout_T4", new Vector2(3f, 1.75f) },
        { "coldroom_T1", new Vector2(1.25f, .75f) }, { "coldroom_T2", new Vector2(2f, 2f) }, { "coldroom_T3", new Vector2(3f, 2.5f) }, { "coldroom_T4", new Vector2(5f, 4f) },
        { "carts_T1", new Vector2(.75f, .6f) }, { "carts_T2", new Vector2(1.75f, .75f) }, { "carts_T3", new Vector2(2.25f, 1f) },
        { "atm_T1", new Vector2(.75f, .85f) }, { "atm_T2", new Vector2(1.5f, .85f) }, { "atm_T3", new Vector2(2.25f, 1.5f) },
        { "gumball_T1", new Vector2(.5f, .5f) }, { "gumball_T2", new Vector2(1f, .5f) },
        { "claw_T1", new Vector2(.75f, .75f) }, { "claw_T2", new Vector2(1.5f, .85f) }, { "claw_T3", new Vector2(1.5f, 1.5f) },
    };
    // Kinds that hold products customers take from the front (-Z).
    static readonly string[] ServingKinds = { "shelf", "produce", "drinks", "dairy", "bakery", "freezer", "icecream" };
    // Pictures also saved under the decoration's own id (the Loja cards show the decoration as bought: tier 1).
    static readonly Dictionary<string, string> StationSprites = new Dictionary<string, string>
    {
        { "carts_T1", "basket-station" }, { "carts_T2", "cart-corral" }, { "carts_T3", "big-cart-corral" },
        { "atm_T1", "atm" }, { "gumball_T1", "gumball" }, { "claw_T1", "claw-machine" },
    };

    [MenuItem("Supermarket/Build fixture tiers")]
    public static void BuildFixtureTiers()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        materials.Clear();
        if (!AssetDatabase.IsValidFolder("Assets/Resources/CheckoutFixtureTiers")) AssetDatabase.CreateFolder("Assets/Resources", "CheckoutFixtureTiers");
        int built = 0; var report = new List<string>();
        foreach (var pair in TierFootprints)
        {
            var prefab = BuildTierPrefab(pair.Key, pair.Value, report);
            if (prefab) built++;
        }
        AssetDatabase.SaveAssets();
        RenderTierSprites(report);
        AssetDatabase.SaveAssets(); AssetDatabase.Refresh();
        Debug.Log("FIXTURE_TIERS built " + built + "/" + TierFootprints.Count + "\n" + string.Join("\n", report));
    }

    static GameObject BuildTierPrefab(string name, Vector2 size, List<string> report)
    {
        string path = TierModels + name + ".fbx";
        var importer = AssetImporter.GetAtPath(path) as ModelImporter;
        if (!importer) { report.Add(name + ": missing " + path); return null; }
        if (importer.importNormals != ModelImporterNormals.Import || importer.addCollider || importer.importAnimation || importer.materialLocation != ModelImporterMaterialLocation.InPrefab || importer.bakeAxisConversion || importer.importCameras || importer.importLights)
        {
            importer.importNormals = ModelImporterNormals.Import; importer.addCollider = false; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
            importer.materialLocation = ModelImporterMaterialLocation.InPrefab; importer.bakeAxisConversion = false; importer.SaveAndReimport();
        }
        var source = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (!source) { report.Add(name + ": FBX did not load"); return null; }
        var root = new GameObject(name);
        try
        {
            var model = (GameObject)PrefabUtility.InstantiatePrefab(source);
            PrefabUtility.UnpackPrefabInstance(model, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            model.name = "Model"; model.transform.SetParent(root.transform, false); model.transform.localPosition = Vector3.zero;
            // Products never follow the market's colours (packaging can be navy or gold).
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
            {
                bool stock = InFill(r.transform);
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = TierRemap(mats[i], stock);
                r.sharedMaterials = mats;
                if (stock) r.shadowCastingMode = ShadowCastingMode.Off; // iPhone: stock casts no shadows (as the kit's fills)
                r.lightProbeUsage = LightProbeUsage.Off; r.reflectionProbeUsage = ReflectionProbeUsage.Off;
            }
            // Footprint: the build cells, grown to any part that really sticks out (the kit rounds to 6 cm).
            var bounds = new Bounds(Vector3.zero, Vector3.zero); bool any = false;
            foreach (var r in model.GetComponentsInChildren<Renderer>(true)) { if (!any) { bounds = r.bounds; any = true; } else bounds.Encapsulate(r.bounds); }
            var min = new Vector2(-size.x / 2, -size.y / 2); var max = new Vector2(size.x / 2, size.y / 2);
            if (!name.StartsWith("coldroom"))
            {
                min = Vector2.Min(min, new Vector2(bounds.min.x, bounds.min.z)); max = Vector2.Max(max, new Vector2(bounds.max.x, bounds.max.z));
            }
            var piece = root.AddComponent<CheckoutInteriorPiece>();
            piece.min = min; piece.max = max; piece.markerHeight = Mathf.Max(1.2f, bounds.max.y + .25f);
            string kind = name.Substring(0, name.IndexOf("_T", StringComparison.Ordinal));
            if (ServingKinds.Contains(kind)) { piece.serves = true; piece.approach = new Vector3(0, 0, min.y - .47f); }
            if (kind == "checkout") CheckoutPoints(piece, name, min, max);
            // Stock groups, in order (Anim Fill 0..3): the shelf empties and refills group by group.
            var fills = model.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("Anim Fill")).OrderBy(t => t.name).Select(t => t.gameObject).ToArray();
            piece.fill = fills;
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, TierPrefabs + name + ".prefab");
            int tris = model.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh).Sum(f => f.sharedMesh.triangles.Length / 3);
            int mats2 = model.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Distinct().Count();
            report.Add($"{name}: {size.x}x{size.y} m, piece {min}..{max}, h {bounds.max.y:0.00}, {tris} tris, {mats2} materials, {fills.Length} fills");
            return prefab;
        }
        finally { UnityEngine.Object.DestroyImmediate(root); }
    }

    static bool InFill(Transform t) { for (; t; t = t.parent) if (t.name.StartsWith("Anim Fill")) return true; return false; }

    static Material TierRemap(Material source, bool stock)
    {
        string n = source ? source.name : "C_FFFFFF";
        int dot = n.IndexOf('.'); if (dot > 0) n = n.Substring(0, dot);
        // A colour that belongs to a product: its own "Products" material (CheckoutMarketPaint.NotPaint).
        if (n.StartsWith("C_") && n.Length >= 8 && (stock || n.EndsWith("_Product")))
            return Painted("IK_PProducts_" + n.Substring(2, 6), n.Substring(2, 6), null, Vector2.one, .35f);
        // The blank label atlas of the tiers ("IK_PT_Labels" is the old atlas with printed words).
        if (n.StartsWith("T_FT_")) return Painted("IK_PT_" + n.Substring(2), "FFFFFF", n.Substring(2), Vector2.one, .35f);
        return KitRemap(source);
    }

    // Where the cashier works (+Z), the customers queue (-Z, right to left towards the door side) and pay.
    static void CheckoutPoints(CheckoutInteriorPiece piece, string name, Vector2 min, Vector2 max)
    {
        float w = max.x - min.x, z = min.y - .55f, pay = Mathf.Min(max.x - .55f, .55f);
        piece.staffed = true; piece.staff = new Vector3(pay * .4f, 0, max.y - .32f);
        piece.queue = new[] { new Vector3(pay, 0, z), new Vector3(pay - .85f, 0, z), new Vector3(pay - 1.7f, 0, z), new Vector3(pay - 2.55f, 0, z) };
        piece.register = new Vector3(pay, 0, 0);
        piece.beltStart = new Vector3(min.x + .25f, .86f, -.05f); piece.beltEnd = new Vector3(Mathf.Max(min.x + .5f, pay - .3f), .86f, -.05f);
    }

    // ------------------------------------------------------------------ build tray pictures
    // 256 px, transparent, the same three-quarter view as the other furniture pictures.
    static void RenderTierSprites(List<string> report)
    {
        var rig = new GameObject("FT sprite rig"); rig.transform.position = new Vector3(0, -300, 0);
        try
        {
            var light = new GameObject("Key").AddComponent<Light>(); light.type = LightType.Directional; light.intensity = 1.15f;
            light.transform.SetParent(rig.transform, false); light.transform.rotation = Quaternion.Euler(42, -35, 0);
            var fill = new GameObject("Fill").AddComponent<Light>(); fill.type = LightType.Directional; fill.intensity = .45f;
            fill.transform.SetParent(rig.transform, false); fill.transform.rotation = Quaternion.Euler(20, 150, 0);
            var cam = new GameObject("Camera").AddComponent<Camera>(); cam.transform.SetParent(rig.transform, false);
            cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0, 0, 0, 0); cam.fieldOfView = 24; cam.nearClipPlane = .1f; cam.farClipPlane = 60;
            var rt = new RenderTexture(512, 512, 24, RenderTextureFormat.ARGB32) { antiAliasing = 4 };
            cam.targetTexture = rt;
            foreach (var name in TierFootprints.Keys)
            {
                var prefab = AssetDatabase.LoadAssetAtPath<GameObject>(TierPrefabs + name + ".prefab");
                if (!prefab) continue;
                var go = (GameObject)PrefabUtility.InstantiatePrefab(prefab); go.transform.SetParent(rig.transform, false);
                var b = new Bounds(go.transform.position, Vector3.zero);
                foreach (var r in go.GetComponentsInChildren<Renderer>()) b.Encapsulate(r.bounds);
                float radius = b.extents.magnitude;
                var dir = Quaternion.Euler(24, -32, 0) * Vector3.back;
                cam.transform.position = b.center + dir * (radius / Mathf.Sin(cam.fieldOfView * .5f * Mathf.Deg2Rad) * 1.02f);
                cam.transform.LookAt(b.center);
                cam.Render();
                var tex = new Texture2D(512, 512, TextureFormat.RGBA32, false);
                RenderTexture.active = rt; tex.ReadPixels(new Rect(0, 0, 512, 512), 0, 0); tex.Apply(); RenderTexture.active = null;
                var small = Downsample(tex, 256);
                var png = small.EncodeToPNG();
                File.WriteAllBytes(DecorSprites + name + ".png", png);
                if (StationSprites.TryGetValue(name, out var station)) File.WriteAllBytes(DecorSprites + station + ".png", png);
                UnityEngine.Object.DestroyImmediate(tex); UnityEngine.Object.DestroyImmediate(small); UnityEngine.Object.DestroyImmediate(go);
            }
            cam.targetTexture = null; UnityEngine.Object.DestroyImmediate(rt);
            report.Add("sprites rendered to " + DecorSprites);
        }
        finally { UnityEngine.Object.DestroyImmediate(rig); }
        AssetDatabase.Refresh();
        // Same import as the other furniture pictures (a plain 2D texture, loaded as a sprite by the HUD kit).
        foreach (var name in TierFootprints.Keys.Concat(StationSprites.Values))
        {
            var importer = AssetImporter.GetAtPath(DecorSprites + name + ".png") as TextureImporter;
            if (!importer) continue;
            importer.textureType = TextureImporterType.Default; importer.alphaIsTransparency = true; importer.mipmapEnabled = false; importer.maxTextureSize = 256;
            importer.SaveAndReimport();
        }
    }

    static Texture2D Downsample(Texture2D src, int size)
    {
        var dst = new Texture2D(size, size, TextureFormat.RGBA32, false);
        int k = src.width / size;
        for (int y = 0; y < size; y++)
            for (int x = 0; x < size; x++)
            {
                Color c = Color.clear; float a = 0;
                for (int j = 0; j < k; j++) for (int i = 0; i < k; i++) { var p = src.GetPixel(x * k + i, y * k + j); c += new Color(p.r * p.a, p.g * p.a, p.b * p.a, p.a); a += p.a; }
                dst.SetPixel(x, y, a > 0 ? new Color(c.r / a, c.g / a, c.b / a, a / (k * k)) : Color.clear);
            }
        dst.Apply();
        return dst;
    }
}
