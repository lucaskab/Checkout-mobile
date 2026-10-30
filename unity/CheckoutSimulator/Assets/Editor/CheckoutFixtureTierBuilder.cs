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
        // The Supermercado's cold room as a wing of the depot (pivot = the depot mesh's pivot, depot-local; no build cells:
        // it is parented to the depot, CheckoutColdRoom.PlaceDepotWing).
        { "coldroom_depotwing_T2", Vector2.zero }, { "coldroom_depotwing_T3", Vector2.zero },
        { "carts_T1", new Vector2(.75f, .6f) }, { "carts_T2", new Vector2(1.75f, .75f) }, { "carts_T3", new Vector2(2.25f, 1f) },
        { "atm_T1", new Vector2(.75f, .85f) }, { "atm_T2", new Vector2(1.5f, .85f) }, { "atm_T3", new Vector2(2.25f, 1.5f) },
        { "gumball_T1", new Vector2(.5f, .5f) }, { "gumball_T2", new Vector2(1f, .5f) },
        { "claw_T1", new Vector2(.75f, .75f) }, { "claw_T2", new Vector2(1.5f, .85f) }, { "claw_T3", new Vector2(1.5f, 1.5f) },
        // The seven special sectors (Lucas 30/10), T1 2.5 × 2.0, T2 3.25 × 2.5, T3 4.0 × 3.25; the prefabs take the game's
        // sector ids (the juices' FBX is "sector-sucos", the game's sector "bebidas").
        { "sector-padaria_T1", new Vector2(2.5f, 2f) }, { "sector-padaria_T2", new Vector2(3.25f, 2.5f) }, { "sector-padaria_T3", new Vector2(4f, 3.25f) },
        { "sector-queijaria_T1", new Vector2(2.5f, 2f) }, { "sector-queijaria_T2", new Vector2(3.25f, 2.5f) }, { "sector-queijaria_T3", new Vector2(4f, 3.25f) },
        { "sector-acougue_T1", new Vector2(2.5f, 2f) }, { "sector-acougue_T2", new Vector2(3.25f, 2.5f) }, { "sector-acougue_T3", new Vector2(4f, 3.25f) },
        { "sector-peixaria_T1", new Vector2(2.5f, 2f) }, { "sector-peixaria_T2", new Vector2(3.25f, 2.5f) }, { "sector-peixaria_T3", new Vector2(4f, 3.25f) },
        { "sector-sorvetes_T1", new Vector2(2.5f, 2f) }, { "sector-sorvetes_T2", new Vector2(3.25f, 2.5f) }, { "sector-sorvetes_T3", new Vector2(4f, 3.25f) },
        { "sector-adega_T1", new Vector2(2.5f, 2f) }, { "sector-adega_T2", new Vector2(3.25f, 2.5f) }, { "sector-adega_T3", new Vector2(4f, 3.25f) },
        { "sector-bebidas_T1", new Vector2(2.5f, 2f) }, { "sector-bebidas_T2", new Vector2(3.25f, 2.5f) }, { "sector-bebidas_T3", new Vector2(4f, 3.25f) },
    };
    static string FbxName(string name) => name.Replace("sector-bebidas_", "sector-sucos_");
    // Sectors with an attendant behind the counter (as the kit's counters).
    static readonly string[] StaffedSectors = { "sector-padaria", "sector-queijaria", "sector-acougue", "sector-peixaria" };
    // The blank slots the game writes into (CheckoutSectorScreens): never parsed as "E_<hex>" glow colours.
    const string PriceSlot = "E_PriceScreen", TicketSlot = "E_TicketScreen", NameSlot = "E_NamePanel";
    // Kinds that hold products customers take from the front (-Z).
    static readonly string[] ServingKinds = { "shelf", "produce", "drinks", "dairy", "bakery", "freezer", "icecream" };
    // Pictures also saved under the decoration's own id (the Loja cards show the decoration as bought: tier 1).
    static readonly Dictionary<string, string> StationSprites = new Dictionary<string, string>
    {
        { "carts_T1", "basket-station" }, { "carts_T2", "cart-corral" }, { "carts_T3", "big-cart-corral" },
        { "atm_T1", "atm" }, { "gumball_T1", "gumball" }, { "claw_T1", "claw-machine" },
        // the build-mode cards of the sectors (the old pictures had the names written on the boards)
        { "sector-padaria_T1", "sector-padaria" }, { "sector-queijaria_T1", "sector-queijaria" }, { "sector-acougue_T1", "sector-acougue" },
        { "sector-peixaria_T1", "sector-peixaria" }, { "sector-sorvetes_T1", "sector-sorvetes" }, { "sector-adega_T1", "sector-adega" },
        { "sector-bebidas_T1", "sector-bebidas" },
    };

    // Packs everything "Build fixture tiers" generated (prefabs, merged meshes, palette, materials, sprites, the
    // FBX import settings) into Logs/fixture_tiers_assets.zip, keeping the paths under Assets/: to carry them to
    // another clone of the repo in one file.
    [MenuItem("Supermarket/Pack fixture tiers (zip)")]
    public static void PackFixtureTiers()
    {
        var since = DateTime.UtcNow.AddHours(-36);
        var files = new List<string>();
        void Dir(string dir, Func<string, bool> keep)
        {
            if (!Directory.Exists(dir)) return;
            files.AddRange(Directory.GetFiles(dir).Where(f => !f.EndsWith(".DS_Store") && keep(Path.GetFileName(f))));
        }
        Dir("Assets/Resources/CheckoutFixtureTiers", f => true);
        Dir("Assets/Art/Interior/Meshes/FT", f => true);
        Dir("Assets/Art/Interior/Models/Tiers", f => f.EndsWith(".meta"));
        Dir("Assets/Art/Interior/Textures", f => f.StartsWith("FT_"));
        Dir("Assets/Art/Interior/Materials", f => File.GetLastWriteTimeUtc("Assets/Art/Interior/Materials/" + f) > since);
        Dir("Assets/Resources/CheckoutDesktop/Decor", f => File.GetLastWriteTimeUtc("Assets/Resources/CheckoutDesktop/Decor/" + f) > since);
        if (File.Exists("Assets/Art/Interior/Meshes/FT.meta")) files.Add("Assets/Art/Interior/Meshes/FT.meta");
        if (File.Exists("Assets/Resources/CheckoutFixtureTiers.meta")) files.Add("Assets/Resources/CheckoutFixtureTiers.meta");
        Directory.CreateDirectory("Logs");
        var zip = "Logs/fixture_tiers_assets.zip";
        if (File.Exists(zip)) File.Delete(zip);
        using (var stream = File.Create(zip))
        using (var archive = new System.IO.Compression.ZipArchive(stream, System.IO.Compression.ZipArchiveMode.Create))
            foreach (var f in files.Distinct())
            {
                var entry = archive.CreateEntry(f.Replace('\\', '/'), System.IO.Compression.CompressionLevel.Optimal);
                using (var to = entry.Open()) using (var from = File.OpenRead(f)) from.CopyTo(to);
            }
        Debug.Log($"FIXTURE_TIERS packed {files.Distinct().Count()} files into {zip} ({new FileInfo(zip).Length / 1024} KB)");
    }

    [MenuItem("Supermarket/Build fixture tiers")]
    public static void BuildFixtureTiers()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        materials.Clear(); paletteSlots.Clear();
        if (!AssetDatabase.IsValidFolder("Assets/Resources/CheckoutFixtureTiers")) AssetDatabase.CreateFolder("Assets/Resources", "CheckoutFixtureTiers");
        if (!AssetDatabase.IsValidFolder("Assets/Art/Interior/Meshes/FT")) AssetDatabase.CreateFolder("Assets/Art/Interior/Meshes", "FT");
        paletteStruct = Painted("IK_PPalette_FT", "FFFFFF", null, Vector2.one);
        paletteProducts = Painted("IK_PProducts_PaletteFT", "FFFFFF", null, Vector2.one, .35f);
        int built = 0; var report = new List<string>();
        foreach (var pair in TierFootprints)
        {
            var prefab = BuildTierPrefab(pair.Key, pair.Value, report);
            if (prefab) built++;
        }
        WritePalette(report);
        AssetDatabase.SaveAssets();
        RenderTierSprites(report);
        AssetDatabase.SaveAssets(); AssetDatabase.Refresh();
        Debug.Log("FIXTURE_TIERS built " + built + "/" + TierFootprints.Count + "\n" + string.Join("\n", report));
    }

    static GameObject BuildTierPrefab(string name, Vector2 size, List<string> report)
    {
        string path = TierModels + FbxName(name) + ".fbx";
        var importer = AssetImporter.GetAtPath(path) as ModelImporter;
        if (!importer) { report.Add(name + ": missing " + path); return null; }
        if (importer.importNormals != ModelImporterNormals.Import || importer.addCollider || importer.importAnimation || importer.materialLocation != ModelImporterMaterialLocation.InPrefab || importer.bakeAxisConversion || importer.importCameras || importer.importLights || !importer.isReadable)
        {
            importer.importNormals = ModelImporterNormals.Import; importer.addCollider = false; importer.importAnimation = false; importer.importCameras = false; importer.importLights = false;
            importer.isReadable = true; // read by the merge below (the game uses the merged meshes, not the FBX)
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
            // The sectors' screens and name boards: turned to the customers (-Z), then where they are, before the
            // materials are swapped.
            int turned = FaceSlotsForward(root.transform, model);
            if (turned > 0) report.Add($"{name}: {turned} slot triangles faced +Z, turned to the customer side");
            var slots = SlotQuads(root.transform, model);
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
            if (size == Vector2.zero) { min = new Vector2(bounds.min.x, bounds.min.z); max = new Vector2(bounds.max.x, bounds.max.z); }
            // (the cart handles, the cold room's condensers and dock included: nothing may stand under them)
            min = Vector2.Min(min, new Vector2(bounds.min.x, bounds.min.z)); max = Vector2.Max(max, new Vector2(bounds.max.x, bounds.max.z));
            var piece = root.AddComponent<CheckoutInteriorPiece>();
            piece.min = min; piece.max = max; piece.markerHeight = Mathf.Max(1.2f, bounds.max.y + .25f);
            string kind = name.Substring(0, name.IndexOf("_T", StringComparison.Ordinal));
            if (ServingKinds.Contains(kind)) { piece.serves = true; piece.approach = new Vector3(0, 0, min.y - .47f); }
            if (kind == "checkout") CheckoutPoints(piece, name, min, max);
            if (kind.StartsWith("sector-"))
            {
                piece.serves = true; piece.approach = new Vector3(0, 0, min.y - .47f);
                piece.staffed = StaffedSectors.Contains(kind); piece.staff = new Vector3(0, 0, (min.y + max.y) * .5f + (max.y - min.y) * .25f);
                var screens = root.AddComponent<CheckoutSectorScreens>();
                screens.prices = slots.Where(q => q.slot == PriceSlot).OrderBy(q => q.center.x).Select(q => q.quad).ToArray();
                screens.tickets = slots.Where(q => q.slot == TicketSlot).Select(q => q.quad).ToArray();
                screens.names = slots.Where(q => q.slot == NameSlot).Select(q => q.quad).ToArray();
                report.Add($"{name}: screens {screens.prices.Length} price, {screens.tickets.Length} ticket, {screens.names.Length} name");
            }
            // iPhone: one renderer for the body and one per stock group, the flat colours that never repaint in one palette
            // material (drinks T3 went from ~27 materials to a handful). Stock groups in order (Anim Fill 0..3): the shelf
            // empties and refills group by group.
            int before = model.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Distinct().Count();
            var fillRoots = model.GetComponentsInChildren<Transform>(true).Where(t => t.name.StartsWith("Anim Fill")).OrderBy(t => t.name).ToList();
            var bodyParts = model.GetComponentsInChildren<MeshRenderer>(true).Where(r => !InFill(r.transform)).ToList();
            Merge(root.transform, "Body", bodyParts, name + "_body", true);
            var fills = new List<GameObject>();
            for (int i = 0; i < fillRoots.Count; i++)
            {
                var go = Merge(root.transform, fillRoots[i].name, fillRoots[i].GetComponentsInChildren<MeshRenderer>(true).ToList(), name + "_fill" + i, false);
                if (go) fills.Add(go);
            }
            UnityEngine.Object.DestroyImmediate(model);
            model = root.gameObject;
            piece.fill = fills.ToArray();
            report.Add($"{name}: materials {before} -> {root.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Distinct().Count()}");
            var prefab = PrefabUtility.SaveAsPrefabAsset(root, TierPrefabs + name + ".prefab");
            int tris = model.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh).Sum(f => f.sharedMesh.triangles.Length / 3);
            int mats2 = model.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Distinct().Count();
            report.Add($"{name}: {size.x}x{size.y} m, piece {min}..{max}, h {bounds.max.y:0.00}, {tris} tris, {mats2} materials, {fills.Count} fills");
            return prefab;
        }
        finally { UnityEngine.Object.DestroyImmediate(root); }
    }

    struct SlotQuad { public string slot; public Vector3 center; public CheckoutSectorScreens.Quad quad; }

    // A slot quad must face the customers (-Z): one exported facing the wall is invisible from the shop floor (back-face
    // culled, the board behind it shows), so its triangles are turned round (winding and normals) on a copy of the mesh.
    static int FaceSlotsForward(Transform root, GameObject model)
    {
        int turned = 0;
        foreach (var r in model.GetComponentsInChildren<MeshRenderer>(true))
        {
            var mf = r.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null; if (!mesh) continue;
            var mats = r.sharedMaterials; Mesh copy = null; Vector3[] verts = mesh.vertices, normals = null;
            for (int sub = 0; sub < mesh.subMeshCount && sub < mats.Length; sub++)
            {
                string n = mats[sub] ? mats[sub].name : ""; int dot = n.IndexOf('.'); if (dot > 0) n = n.Substring(0, dot);
                if (n != PriceSlot && n != TicketSlot && n != NameSlot) continue;
                var tris = mesh.GetTriangles(sub); bool changed = false;
                for (int i = 0; i + 2 < tris.Length; i += 3)
                {
                    Vector3 a = root.InverseTransformPoint(r.transform.TransformPoint(verts[tris[i]])), b = root.InverseTransformPoint(r.transform.TransformPoint(verts[tris[i + 1]])), c = root.InverseTransformPoint(r.transform.TransformPoint(verts[tris[i + 2]]));
                    if (Vector3.Cross(b - a, c - a).z <= 0) continue; // Unity's front face is clockwise: facing -Z
                    if (copy == null) { copy = UnityEngine.Object.Instantiate(mesh); copy.name = mesh.name; normals = copy.normals; }
                    int t = tris[i + 1]; tris[i + 1] = tris[i + 2]; tris[i + 2] = t; changed = true; turned++;
                    if (normals != null && normals.Length == verts.Length) foreach (var k in new[] { tris[i], tris[i + 1], tris[i + 2] }) if (normals[k].z > 0) normals[k] = -normals[k];
                }
                if (changed) copy.SetTriangles(tris, sub);
            }
            if (copy != null) { if (normals != null && normals.Length == copy.vertexCount) copy.normals = normals; mf.sharedMesh = copy; }
        }
        return turned;
    }

    // Every flat quad drawn with one of the slot materials, in the prefab root's space (the triangles of a slot
    // submesh grouped by touching bounds: one group per screen or board).
    static List<SlotQuad> SlotQuads(Transform root, GameObject model)
    {
        var list = new List<SlotQuad>();
        foreach (var r in model.GetComponentsInChildren<MeshRenderer>(true))
        {
            var mf = r.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null; if (!mesh) continue;
            var mats = r.sharedMaterials; var verts = mesh.vertices;
            for (int sub = 0; sub < mesh.subMeshCount && sub < mats.Length; sub++)
            {
                string n = mats[sub] ? mats[sub].name : ""; int dot = n.IndexOf('.'); if (dot > 0) n = n.Substring(0, dot);
                if (n != PriceSlot && n != TicketSlot && n != NameSlot) continue;
                var tris = mesh.GetTriangles(sub); var groups = new List<Bounds>();
                for (int i = 0; i + 2 < tris.Length; i += 3)
                {
                    var b = new Bounds(root.InverseTransformPoint(r.transform.TransformPoint(verts[tris[i]])), Vector3.zero);
                    b.Encapsulate(root.InverseTransformPoint(r.transform.TransformPoint(verts[tris[i + 1]])));
                    b.Encapsulate(root.InverseTransformPoint(r.transform.TransformPoint(verts[tris[i + 2]])));
                    groups.Add(b);
                }
                for (bool merged = true; merged;)
                {
                    merged = false;
                    for (int a = 0; a < groups.Count && !merged; a++)
                        for (int c = a + 1; c < groups.Count; c++)
                        {
                            var ga = groups[a]; ga.Expand(.004f);
                            if (!ga.Intersects(groups[c])) continue;
                            var u = groups[a]; u.Encapsulate(groups[c]); groups[a] = u; groups.RemoveAt(c); merged = true; break;
                        }
                }
                foreach (var g in groups)
                    list.Add(new SlotQuad { slot = n, center = g.center, quad = new CheckoutSectorScreens.Quad { center = new Vector3(g.center.x, g.center.y, g.min.z), size = new Vector2(g.size.x, g.size.y) } });
            }
        }
        return list;
    }

    static bool InFill(Transform t) { for (; t; t = t.parent) if (t.name.StartsWith("Anim Fill")) return true; return false; }

    // ------------------------------------------------------------------ merge + palette
    const int PaletteSize = 32; // 32 x 32 colours
    static readonly Dictionary<string, int> paletteSlots = new Dictionary<string, int>();
    static Material paletteStruct, paletteProducts;

    // A flat colour that never follows "Cores do mercado" (cream, white, metal, dark, wood, products): it can share the
    // palette material. Navy and gold (repainted) and every textured, glass or glowing material keep their own.
    static bool PaletteColour(Material m) =>
        m && m.shader && m.shader.name == "MarketDay/Soft Painted" && !m.mainTexture && CheckoutMarketPaint.Classify(m, out _) == 0;

    static Vector2 Slot(Color c)
    {
        var key = ColorUtility.ToHtmlStringRGB(c);
        if (!paletteSlots.TryGetValue(key, out int k)) { k = paletteSlots.Count; if (k >= PaletteSize * PaletteSize) k = 0; paletteSlots[key] = k; }
        return new Vector2((k % PaletteSize + .5f) / PaletteSize, (k / PaletteSize + .5f) / PaletteSize);
    }

    // One mesh for these renderers (in `parent`'s space), one submesh per material; saved as an asset.
    static GameObject Merge(Transform parent, string name, List<MeshRenderer> parts, string asset, bool shadows)
    {
        var byMaterial = new Dictionary<Material, List<CombineInstance>>();
        var toParent = parent.worldToLocalMatrix;
        foreach (var r in parts)
        {
            var mf = r.GetComponent<MeshFilter>(); var mesh = mf ? mf.sharedMesh : null; if (!mesh) continue;
            var mats = r.sharedMaterials;
            for (int sub = 0; sub < mesh.subMeshCount && sub < mats.Length; sub++)
            {
                var m = mats[sub]; if (!m) continue;
                var piece = Extract(mesh, sub);
                if (PaletteColour(m))
                {
                    var uv = Slot(m.color); piece.uv = Enumerable.Repeat(uv, piece.vertexCount).ToArray();
                    m = m.name.Contains("Products") ? paletteProducts : paletteStruct;
                }
                if (!byMaterial.TryGetValue(m, out var list)) byMaterial[m] = list = new List<CombineInstance>();
                list.Add(new CombineInstance { mesh = piece, transform = toParent * r.transform.localToWorldMatrix });
            }
        }
        if (byMaterial.Count == 0) return null;
        var merged = new List<CombineInstance>(); var order = new List<Material>(); var temps = new List<Mesh>();
        foreach (var pair in byMaterial)
        {
            var one = new Mesh { indexFormat = UnityEngine.Rendering.IndexFormat.UInt32 };
            one.CombineMeshes(pair.Value.ToArray(), true, true);
            merged.Add(new CombineInstance { mesh = one, transform = Matrix4x4.identity }); order.Add(pair.Key); temps.Add(one);
            foreach (var c in pair.Value) UnityEngine.Object.DestroyImmediate(c.mesh);
        }
        var result = new Mesh { name = "FT_" + asset };
        int verts = merged.Sum(c => c.mesh.vertexCount);
        result.indexFormat = verts > 65000 ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16;
        result.CombineMeshes(merged.ToArray(), false, false);
        result.RecalculateBounds();
        foreach (var t in temps) UnityEngine.Object.DestroyImmediate(t);
        string path = "Assets/Art/Interior/Meshes/FT/" + asset + ".asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (existing) { existing.Clear(); EditorUtility.CopySerialized(result, existing); UnityEngine.Object.DestroyImmediate(result); result = existing; }
        else AssetDatabase.CreateAsset(result, path);
        // Not kept readable in memory on the phone.
        var so = new SerializedObject(result); var readable = so.FindProperty("m_IsReadable"); if (readable != null) { readable.boolValue = false; so.ApplyModifiedPropertiesWithoutUndo(); }
        var go = new GameObject(name); go.transform.SetParent(parent, false);
        go.AddComponent<MeshFilter>().sharedMesh = result;
        var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = order.ToArray();
        mr.shadowCastingMode = shadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
        mr.lightProbeUsage = LightProbeUsage.Off; mr.reflectionProbeUsage = ReflectionProbeUsage.Off;
        return go;
    }

    static Mesh Extract(Mesh mesh, int sub)
    {
        var tris = mesh.GetTriangles(sub); var map = new Dictionary<int, int>();
        var v = mesh.vertices; var n = mesh.normals; var uv = mesh.uv;
        var nv = new List<Vector3>(); var nn = new List<Vector3>(); var nu = new List<Vector2>(); var nt = new int[tris.Length];
        for (int i = 0; i < tris.Length; i++)
        {
            int k = tris[i];
            if (!map.TryGetValue(k, out int j)) { j = nv.Count; map[k] = j; nv.Add(v[k]); if (n.Length > k) nn.Add(n[k]); nu.Add(uv.Length > k ? uv[k] : Vector2.zero); }
            nt[i] = j;
        }
        var m = new Mesh { indexFormat = nv.Count > 65000 ? UnityEngine.Rendering.IndexFormat.UInt32 : UnityEngine.Rendering.IndexFormat.UInt16 };
        m.SetVertices(nv); if (nn.Count == nv.Count) m.SetNormals(nn); m.SetUVs(0, nu); m.SetTriangles(nt, 0);
        return m;
    }

    // The palette texture of every flat colour used (point-sampled, no mips: each texel is one exact colour).
    static void WritePalette(List<string> report)
    {
        const string path = "Assets/Art/Interior/Textures/FT_Palette_albedo.png";
        var tex = new Texture2D(PaletteSize, PaletteSize, TextureFormat.RGBA32, false);
        var fill = Enumerable.Repeat(Color.white, PaletteSize * PaletteSize).ToArray(); tex.SetPixels(fill);
        foreach (var pair in paletteSlots)
        {
            ColorUtility.TryParseHtmlString("#" + pair.Key, out var c);
            tex.SetPixel(pair.Value % PaletteSize, pair.Value / PaletteSize, c);
        }
        tex.Apply();
        File.WriteAllBytes(path, tex.EncodeToPNG()); UnityEngine.Object.DestroyImmediate(tex);
        AssetDatabase.ImportAsset(path);
        var importer = (TextureImporter)AssetImporter.GetAtPath(path);
        importer.textureType = TextureImporterType.Default; importer.mipmapEnabled = false; importer.filterMode = FilterMode.Point;
        importer.textureCompression = TextureImporterCompression.Uncompressed; importer.sRGBTexture = true; importer.wrapMode = TextureWrapMode.Clamp; importer.maxTextureSize = 32;
        importer.SaveAndReimport();
        var palette = AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        foreach (var m in new[] { paletteStruct, paletteProducts }) { m.mainTexture = palette; m.mainTextureScale = Vector2.one; m.color = Color.white; EditorUtility.SetDirty(m); }
        report.Add($"palette: {paletteSlots.Count} flat colours in {path}");
    }

    static Material TierRemap(Material source, bool stock)
    {
        string n = source ? source.name : "C_FFFFFF";
        int dot = n.IndexOf('.'); if (dot > 0) n = n.Substring(0, dot);
        // A colour that belongs to a product (or wood, cream: never the market's paint): its own "Products" material
        // (CheckoutMarketPaint.NotPaint), so navy or gold packaging keeps its colour after a repaint.
        if (n.StartsWith("C_") && n.Length >= 8 && (stock || n.EndsWith("_Product") || n.EndsWith("_Wood") || n.EndsWith("_Cream")))
            return Painted("IK_PProducts_" + n.Substring(2, 6), n.Substring(2, 6), null, Vector2.one, .35f);
        // The sectors' blank slots (before the "E_<hex>" glow rule, which would read "PriceS" as a colour): screens
        // "off" in a dark glass, the name boards cream. The game writes on them (CheckoutSectorScreens).
        if (n == PriceSlot || n == TicketSlot) return Painted("IK_PProducts_161B22", "161B22", null, Vector2.one, .2f);
        if (n == NameSlot) return Painted("IK_PProducts_F4EBD8", "F4EBD8", null, Vector2.one, .35f);
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
                if (TierFootprints[name] == Vector2.zero) continue; // parts of a building (the depot wing): no card picture
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
