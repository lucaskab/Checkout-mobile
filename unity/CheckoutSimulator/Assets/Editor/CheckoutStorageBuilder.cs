using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

// The stock room ("DEPÓSITO"), the central warehouse ("ARMAZÉM CENTRAL") and the construction kit used
// by the live building site, all built from scratch in the shop's look: navy ribbed cladding, limestone
// plinths and pilasters, brushed gold bands, white LED lines, and our own tiling textures.
public static partial class CheckoutMarketStagesBuilder
{
    const string MeshFolder = "Assets/Art/Storage/Meshes/";
    const string KitName = "Construction Kit";

    [MenuItem("Supermarket/Build storages and construction kit")]
    public static void BuildStoragesMenu()
    {
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation || !simulation.world) throw new InvalidOperationException("Open the Supermarket scene first.");
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        materials.Clear();
        font = Resources.Load<Font>("MarketBold") ?? Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        BuildStorages(simulation.world);
        var show = simulation.world.GetComponentInChildren<CheckoutStageConstruction>(true);
        if (show) BuildConstructionKit(show);
        EditorSceneManager.MarkSceneDirty(simulation.world.gameObject.scene);
        EditorSceneManager.SaveScene(simulation.world.gameObject.scene);
        AssetDatabase.SaveAssets();
    }

    // ------------------------------------------------------------------ materials
    static Material TexMat(string name, float tiling, float gloss, float metal = 0) => Tri("MS_" + name, "MS_" + name, tiling, gloss, metal);
    static Material Cladding() => TexMat("Cladding", .55f, .45f, .15f);
    static Material RoofSeam() => TexMat("RoofSeam", .5f, .5f, .35f);
    static Material RollerDoor() => TexMat("RollerDoor", .45f, .4f, .2f);
    static Material CranePaint() => TexMat("CranePaint", .9f, .5f, .15f);
    static Material Hazard() => TexMat("Hazard", 1.4f, .35f);
    static Material Concrete() => TexMat("Concrete", .45f, .1f);
    static Material Planks() => TexMat("Planks", .7f, .15f);
    static Material Galvanized() => TexMat("Galvanized", 1.2f, .6f, .6f);
    static Material Rubber() => TexMat("Rubber", 2f, .15f);
    static Material Solar() => TexMat("Solar", .6f, .85f, .2f);
    static Material Brick() => TexMat("Brick", 1.6f, .1f);
    static Material TruckWhite() => TexMat("TruckWhite", .5f, .75f, .1f);
    static Material WindowGlow() => Mat("MS_WindowGlow", "E9D3A2", .9f, "5A4726");
    static Material Skylight() => Mat("MS_Skylight", "9DB3C6", .92f);
    static Material RackOrange() => Mat("MS_RackOrange", "E0762A", .3f);
    static Material InteriorDark() => Mat("MS_InteriorDark", "2B2F38", .1f, "1E1A14");
    static Material DarkGlass() => Mat("MS_DarkGlass", "27303E", .92f);
    static Material Cardboard() => Mat("MS_Cardboard", "C69C63", .1f);
    static Material RedLamp() => Mat("MS_RedLamp", "FF3B30", .6f, "FF2A1F");
    static Material GreenLamp() => Mat("MS_GreenLamp", "37D067", .6f, "22C455");
    static Material AmberLamp() => Mat("MS_AmberLamp", "FFB02E", .6f, "FF9A1F");
    static Material BulbOff() => Mat("MS_BulbOff", "B9B2A0", .6f);
    static Material HatYellow() => Mat("MS_HardHat", "F2C230", .75f);
    static Material Cable() => Mat("MS_Cable", "2A2C31", .4f);

    static Material Printed(string name, string texture)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Folder + name + ".mat", tex = Folder + "Textures/" + texture + "_albedo.png";
        var importer = AssetImporter.GetAtPath(tex) as TextureImporter;
        if (importer && (importer.wrapMode != TextureWrapMode.Clamp || importer.maxTextureSize != 1024)) { importer.wrapMode = TextureWrapMode.Clamp; importer.maxTextureSize = 1024; importer.SaveAndReimport(); }
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("Standard");
        material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(tex);
        material.color = Color.white; material.SetFloat("_Glossiness", .35f);
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static Material Crew(string name)
    {
        string path = "Assets/Art/Characters/Meshy/Workers/" + name + ".mat", tex = "Assets/Art/Characters/Meshy/Workers/" + name + ".png";
        var source = AssetDatabase.LoadAssetAtPath<Material>("Assets/Art/Characters/Meshy/Workers/Worker_Delivery.mat");
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = source ? new Material(source) : new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(tex);
        EditorUtility.SetDirty(material);
        return material;
    }

    // ------------------------------------------------------------------ geometry helpers
    static Transform Node(Transform parent, string name, Vector3 local, Quaternion? rotation = null)
    {
        var t = new GameObject(name).transform; t.SetParent(parent, false); t.localPosition = local; t.localRotation = rotation ?? Quaternion.identity; return t;
    }

    static GameObject Beam(Transform parent, string name, Vector3 a, Vector3 b, float thick, Material material)
    {
        var d = b - a;
        var go = Box(parent, name, (a + b) * .5f, new Vector3(thick, d.magnitude, thick), material);
        go.transform.localRotation = Quaternion.FromToRotation(Vector3.up, d.normalized);
        return go;
    }

    // Four slabs around a w x d rectangle centred on the parent origin (a band, parapet or fascia).
    static void Ring(Transform parent, string name, float w, float d, float y0, float y1, float thick, float outset, Material material, bool east = true)
    {
        float h = y1 - y0, y = (y0 + y1) * .5f, hw = w * .5f + outset, hd = d * .5f + outset;
        Box(parent, name, new Vector3(0, y, -hd + thick * .5f), new Vector3(w + outset * 2, h, thick), material);
        Box(parent, name, new Vector3(0, y, hd - thick * .5f), new Vector3(w + outset * 2, h, thick), material);
        Box(parent, name, new Vector3(-hw + thick * .5f, y, 0), new Vector3(thick, h, d + outset * 2 - thick * 2), material);
        if (east) Box(parent, name, new Vector3(hw - thick * .5f, y, 0), new Vector3(thick, h, d + outset * 2 - thick * 2), material);
    }

    static void Folders()
    {
        if (!AssetDatabase.IsValidFolder("Assets/Art/Storage")) AssetDatabase.CreateFolder("Assets/Art", "Storage");
        if (!AssetDatabase.IsValidFolder("Assets/Art/Storage/Meshes")) AssetDatabase.CreateFolder("Assets/Art/Storage", "Meshes");
    }

    static bool Animated(Transform t, Transform root)
    {
        for (var p = t; p && p != root; p = p.parent) if (p.name.StartsWith("Anim")) return true;
        return false;
    }

    // Merges every static primitive under `group` into one mesh (one sub-mesh per material), saved as an
    // asset. Pieces under "Anim..." nodes and text stay live.
    static GameObject Bake(Transform group, string asset, string folder = MeshFolder)
    {
        Folders();
        var parts = group.GetComponentsInChildren<MeshFilter>(true).Where(f => f.sharedMesh && !Animated(f.transform, group) && f.GetComponent<MeshRenderer>() && !f.GetComponent<TextMesh>()).ToArray();
        if (parts.Length == 0) return null;
        var byMaterial = new Dictionary<Material, List<CombineInstance>>();
        var toLocal = group.worldToLocalMatrix;
        foreach (var f in parts)
        {
            var r = f.GetComponent<MeshRenderer>();
            for (int s = 0; s < f.sharedMesh.subMeshCount; s++)
            {
                var m = r.sharedMaterials[Mathf.Min(s, r.sharedMaterials.Length - 1)];
                if (!byMaterial.TryGetValue(m, out var list)) byMaterial[m] = list = new List<CombineInstance>();
                list.Add(new CombineInstance { mesh = f.sharedMesh, subMeshIndex = s, transform = toLocal * f.transform.localToWorldMatrix });
            }
        }
        var subs = new List<CombineInstance>(); var mats = new List<Material>();
        foreach (var pair in byMaterial)
        {
            var sub = new Mesh { indexFormat = IndexFormat.UInt32 };
            sub.CombineMeshes(pair.Value.ToArray(), true, true);
            subs.Add(new CombineInstance { mesh = sub, transform = Matrix4x4.identity }); mats.Add(pair.Key);
        }
        var mesh = new Mesh { name = asset, indexFormat = IndexFormat.UInt32 };
        mesh.CombineMeshes(subs.ToArray(), false, false);
        mesh.RecalculateBounds();
        foreach (var s in subs) UnityEngine.Object.DestroyImmediate(s.mesh);
        string path = folder + asset + ".asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (existing) { existing.Clear(); EditorUtility.CopySerialized(mesh, existing); mesh = existing; }
        else AssetDatabase.CreateAsset(mesh, path);
        foreach (var f in parts) if (f) UnityEngine.Object.DestroyImmediate(f.gameObject);
        // Remove empty leftovers.
        foreach (var t in group.GetComponentsInChildren<Transform>(true).Reverse().ToArray())
            if (t && t != group && t.childCount == 0 && t.GetComponents<Component>().Length == 1 && !Animated(t, group) && !t.name.StartsWith("Point")) UnityEngine.Object.DestroyImmediate(t.gameObject);
        var baked = new GameObject("Baked " + asset);
        baked.transform.SetParent(group, false);
        baked.AddComponent<MeshFilter>().sharedMesh = mesh;
        var renderer = baked.AddComponent<MeshRenderer>(); renderer.sharedMaterials = mats.ToArray();
        renderer.shadowCastingMode = ShadowCastingMode.On;
        return baked;
    }

    // ------------------------------------------------------------------ storages
    public static void BuildStorages(Transform world)
    {
        var depot = world.Find("Warehouse");
        if (depot) BuildDepot(depot);
        var grand = world.Find(CheckoutMarketLayout.GrandWarehouse);
        if (grand) BuildCentralWarehouse(world, grand);
        var lot = world.Find(CheckoutMarketLayout.GrandWarehouseSite);
        if (lot) BuildDerelictLot(lot);
    }

    // ------------------------------------------------------------------ empty lot (before the central warehouse)
    static Material Rust() => Mat("MS_Rust", "8A4B2A", .2f);
    static Material Printed2(string name) => Printed(name, name);

    static Material Cutout(string name)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Folder + name + ".mat", tex = Folder + "Textures/" + name + "_albedo.png";
        var importer = AssetImporter.GetAtPath(tex) as TextureImporter;
        if (importer && (!importer.alphaIsTransparency || importer.wrapMode != TextureWrapMode.Clamp)) { importer.alphaIsTransparency = true; importer.wrapMode = TextureWrapMode.Clamp; importer.SaveAndReimport(); }
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("Standard");
        material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(tex);
        material.SetFloat("_Mode", 1); material.SetFloat("_Cutoff", .4f); material.EnableKeyword("_ALPHATEST_ON");
        material.SetOverrideTag("RenderType", "TransparentCutout"); material.renderQueue = (int)RenderQueue.AlphaTest;
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static GameObject Quad(Transform parent, string name, Vector3 local, Vector2 size, float yaw, Material material)
    {
        var q = GameObject.CreatePrimitive(PrimitiveType.Quad); UnityEngine.Object.DestroyImmediate(q.GetComponent<Collider>());
        q.name = name; q.transform.SetParent(parent, false); q.transform.localPosition = local;
        q.transform.localRotation = Quaternion.Euler(0, yaw, 0); q.transform.localScale = new Vector3(size.x, size.y, 1);
        q.GetComponent<Renderer>().sharedMaterial = material;
        return q;
    }

    static void BuildDerelictLot(Transform root)
    {
        foreach (var old in root.Cast<Transform>().Where(t => t.name == "Lot dressing").ToArray()) UnityEngine.Object.DestroyImmediate(old.gameObject);
        // The plain concrete dock block and the skip from the first version of the lot make way for the new clutter.
        foreach (var name in new[] { "WarehouseTrim", "SafetyYellowFaded", "SkipGreen" }) { var t = root.Find(name); if (t) t.gameObject.SetActive(false); }
        const float g = .13f;
        var lot = new GameObject("Lot dressing").transform;
        lot.position = new Vector3(0, g, 0); lot.rotation = Quaternion.identity;
        lot.SetParent(root, true);
        var r = new System.Random(77);
        float Rand(float a, float b) => a + (float)r.NextDouble() * (b - a);
        Material grass = Mat("MS_Grass", "5E8A3C", .1f), grassDry = Mat("MS_GrassDry", "A09A55", .1f), grassDark = Mat("MS_GrassDark", "3F6B2F", .1f);
        Material flowerY = Mat("MS_FlowerYellow", "F2D24B", .2f), flowerW = Mat("MS_FlowerWhite", "F1EFE6", .2f);
        Material teal = Mat("MS_FadedTeal", "5E8C8A", .35f), sofa = Mat("MS_OldSofa", "7A5A6E", .05f), mattress = Mat("MS_Mattress", "D9D0B8", .05f);
        Material puddle = Mat("MS_Puddle", "39434E", .96f), cone = Mat("MS_Cone", "F07A28", .3f), tarp = Mat("MS_Tarp", "2F5F9A", .2f);
        Material pigeon = Mat("MS_Pigeon", "8F939C", .2f), pigeonHead = Mat("MS_PigeonHead", "58606E", .3f), catFur = Mat("MS_CatOrange", "D98B3E", .1f);

        // The old building's cracked foundation slab, with stub columns and rusty rebar.
        var slab = Node(lot, "Foundation", Vector3.zero);
        for (int i = 0; i < 3; i++) for (int k = 0; k < 2; k++)
        {
            if (i == 1 && k == 1) continue; // a missing piece, grown over
            var piece = Box(slab, "Slab", new Vector3(-12.0f + i * 3.4f, .06f + Rand(0, .06f), 32.8f + k * 3.6f), new Vector3(3.2f + Rand(-.2f, .1f), .16f, 3.4f + Rand(-.2f, .1f)), Concrete());
            piece.transform.localRotation = Quaternion.Euler(Rand(-1.5f, 1.5f), Rand(-4f, 4f), Rand(-1.5f, 1.5f));
        }
        foreach (var (x, z, h) in new[] { (-13.4f, 31.3f, 1.3f), (-8.6f, 31.2f, .6f), (-3.9f, 38.0f, 1.5f), (-13.4f, 38.0f, .9f) })
        {
            Box(slab, "Stub column", new Vector3(x, h * .5f, z), new Vector3(.45f, h, .45f), Concrete());
            for (int b = 0; b < 4; b++) Beam(slab, "Rebar", new Vector3(x + (b % 2 - .5f) * .26f, h, z + (b / 2 - .5f) * .26f), new Vector3(x + (b % 2 - .5f) * .4f + Rand(-.1f, .1f), h + Rand(.4f, .8f), z + (b / 2 - .5f) * .4f), .035f, Rust());
        }
        // A surviving brick wall at the back, sprayed with graffiti (faces the square).
        var wall = Node(lot, "Graffiti wall", new Vector3(-12.1f, 0, 39.35f));
        Box(wall, "Wall", new Vector3(0, 1.05f, 0), new Vector3(5.6f, 2.1f, .35f), Brick());
        Box(wall, "Coping", new Vector3(0, 2.14f, 0), new Vector3(5.7f, .1f, .42f), Concrete());
        Quad(wall, "Graffiti", new Vector3(0, 1.02f, -.18f), new Vector2(5.5f, 2.0f), 0, Printed2("MS_GraffitiWall"));
        for (int i = 0; i < 7; i++) Box(wall, "Fallen brick", new Vector3(Rand(-2.6f, 2.6f), .08f, Rand(-.8f, -.3f)), new Vector3(.3f, .12f, .15f), Brick()).transform.localRotation = Quaternion.Euler(0, Rand(0, 180), Rand(-10, 10));

        // A rusty shipping container with one door ajar and a tag on the side.
        var box = Node(lot, "Container", new Vector3(-2.7f, 0, 35.2f));
        Box(box, "Container body", new Vector3(0, 1.32f, 0), new Vector3(2.4f, 2.6f, 6.0f), TexMat("ContainerRust", .6f, .3f, .2f));
        Box(box, "Container frame", new Vector3(0, 2.66f, 0), new Vector3(2.5f, .1f, 6.1f), Rust());
        foreach (int s2 in new[] { -1, 1 }) Box(box, "Corner post", new Vector3(s2 * 1.2f, 1.32f, -3.02f), new Vector3(.14f, 2.64f, .14f), Rust());
        Box(box, "Door left", new Vector3(-.6f, 1.3f, -3.04f), new Vector3(1.15f, 2.4f, .06f), TexMat("ContainerRust", .6f, .3f, .2f));
        var ajar = Node(box, "Door right hinge", new Vector3(1.18f, 0, -3.04f), Quaternion.Euler(0, -38, 0));
        Box(ajar, "Door right", new Vector3(-.58f, 1.3f, 0), new Vector3(1.15f, 2.4f, .06f), TexMat("ContainerRust", .6f, .3f, .2f));
        Box(box, "Inside", new Vector3(.5f, 1.3f, -2.96f), new Vector3(1.1f, 2.3f, .02f), InteriorDark());
        Quad(box, "Tag", new Vector3(-1.215f, 1.3f, .4f), new Vector2(3.2f, 1.6f), 90, Cutout("MS_GraffitiTag"));
        Box(box, "Blocks", new Vector3(0, .02f, 2.6f), new Vector3(2.2f, .04f, .4f), Concrete());

        // A car left on bricks, half under a tarp, with a cat asleep on the bonnet.
        var car = Node(lot, "Old car", new Vector3(-7.0f, 0, 29.4f), Quaternion.Euler(0, 24, 0));
        foreach (int sx in new[] { -1, 1 }) foreach (int sz in new[] { -1, 1 })
            for (int b = 0; b < 2; b++) Box(car, "Brick prop", new Vector3(sx * .7f, .1f + b * .15f, sz * 1.25f), new Vector3(.32f, .14f, .2f), Brick());
        Box(car, "Body", new Vector3(0, .62f, 0), new Vector3(1.75f, .6f, 4.1f), teal);
        Box(car, "Cabin", new Vector3(0, 1.18f, -.25f), new Vector3(1.55f, .55f, 2.1f), teal);
        Box(car, "Windscreen", new Vector3(0, 1.18f, .81f), new Vector3(1.4f, .45f, .03f), DarkGlass());
        foreach (int sx in new[] { -1, 1 }) Box(car, "Side glass", new Vector3(sx * .78f, 1.2f, -.25f), new Vector3(.02f, .38f, 1.8f), DarkGlass());
        Box(car, "Bumper", new Vector3(0, .48f, 2.07f), new Vector3(1.8f, .18f, .08f), Rust());
        Box(car, "Rust patch", new Vector3(.88f, .6f, 1.2f), new Vector3(.02f, .35f, .8f), Rust());
        Box(car, "Rust patch", new Vector3(-.3f, .93f, 1.5f), new Vector3(.7f, .02f, .6f), Rust());
        foreach (int sx in new[] { -1, 1 }) Box(car, "Headlight", new Vector3(sx * .6f, .7f, 2.06f), new Vector3(.3f, .14f, .03f), BulbOff());
        var tarpPivot = Node(car, "Anim tarp", new Vector3(0, 1.48f, -.6f));
        Box(tarpPivot, "Tarp top", new Vector3(0, 0, -.8f), new Vector3(1.9f, .03f, 1.8f), tarp);
        Box(tarpPivot, "Tarp side", new Vector3(.95f, -.45f, -.8f), new Vector3(.03f, .95f, 1.7f), tarp).transform.localRotation = Quaternion.Euler(0, 0, -8);
        Box(tarpPivot, "Tarp back", new Vector3(0, -.5f, -1.68f), new Vector3(1.8f, 1.0f, .03f), tarp).transform.localRotation = Quaternion.Euler(12, 0, 0);
        var cat = Node(car, "Cat", new Vector3(.2f, .95f, 1.3f));
        Box(cat, "Cat body", new Vector3(0, .1f, 0), new Vector3(.34f, .2f, .5f), catFur, PrimitiveType.Sphere);
        Box(cat, "Cat head", new Vector3(0, .14f, .28f), new Vector3(.2f, .18f, .2f), catFur, PrimitiveType.Sphere);
        foreach (int sx in new[] { -1, 1 }) Box(cat, "Cat ear", new Vector3(sx * .06f, .25f, .3f), new Vector3(.05f, .07f, .03f), catFur);
        var tail = Node(cat, "Anim tail", new Vector3(0, .08f, -.24f));
        Box(tail, "Cat tail", new Vector3(.12f, 0, -.12f), new Vector3(.05f, .05f, .32f), catFur).transform.localRotation = Quaternion.Euler(0, 40, 0);

        // Tyres, an old sofa, a mattress, a shopping cart and knocked-over cones.
        void Tyre(Vector3 at, float tilt) { var t = Box(lot, "Tyre", at, new Vector3(.8f, .13f, .8f), Rubber(), PrimitiveType.Cylinder); t.transform.localRotation = Quaternion.Euler(tilt, Rand(0, 180), 0); }
        for (int i = 0; i < 4; i++) Tyre(new Vector3(-1.2f + Rand(-.05f, .05f), .13f + i * .26f, 31.3f), 0);
        for (int i = 0; i < 3; i++) Tyre(new Vector3(-14.8f, .13f + i * .26f, 33.6f), 0);
        Tyre(new Vector3(-10.4f, .42f, 31.2f), 80); Tyre(new Vector3(-5.6f, .13f, 38.6f), 0);
        var couch = Node(lot, "Old sofa", new Vector3(-11.3f, 0, 29.6f), Quaternion.Euler(0, -18, 0));
        Box(couch, "Seat", new Vector3(0, .3f, 0), new Vector3(1.9f, .4f, .8f), sofa);
        Box(couch, "Back", new Vector3(0, .65f, .35f), new Vector3(1.9f, .7f, .2f), sofa).transform.localRotation = Quaternion.Euler(-12, 0, 0);
        foreach (int sx in new[] { -1, 1 }) Box(couch, "Arm", new Vector3(sx * .9f, .5f, 0), new Vector3(.2f, .4f, .8f), sofa);
        Box(couch, "Torn cushion", new Vector3(.4f, .52f, -.05f), new Vector3(.7f, .1f, .6f), mattress).transform.localRotation = Quaternion.Euler(0, 0, 9);
        var bed = Box(lot, "Mattress", new Vector3(-9.2f, .45f, 30.4f), new Vector3(1.4f, .18f, 1.95f), mattress);
        bed.transform.localRotation = Quaternion.Euler(-24, 30, 0);
        var cart = Node(lot, "Shopping cart", new Vector3(-5.3f, 0, 33.9f), Quaternion.Euler(0, 40, 72));
        foreach (float y in new[] { .35f, .8f }) Ring(Node(cart, "Basket", Vector3.zero), "Basket", .55f, .8f, y, y + .03f, .03f, 0, Galvanized());
        foreach (int sx in new[] { -1, 1 }) foreach (int sz in new[] { -1, 1 }) Box(cart, "Upright", new Vector3(sx * .27f, .55f, sz * .39f), new Vector3(.025f, .5f, .025f), Galvanized());
        Box(cart, "Handle", new Vector3(0, .95f, -.45f), new Vector3(.6f, .04f, .04f), Rust());
        foreach (int sx in new[] { -1, 1 }) foreach (int sz in new[] { -1, 1 }) Box(cart, "Castor", new Vector3(sx * .24f, .06f, sz * .34f), new Vector3(.1f, .03f, .1f), Rubber(), PrimitiveType.Cylinder).transform.localRotation = Quaternion.Euler(0, 0, 90);
        foreach (var (x, z, down) in new[] { (-4.4f, 27.2f, false), (-3.6f, 26.9f, true), (-9.6f, 26.6f, false) })
        {
            var c = Node(lot, "Cone", new Vector3(x, down ? .15f : 0, z), Quaternion.Euler(down ? 90 : 0, Rand(0, 180), 0));
            Box(c, "Cone base", new Vector3(0, .02f, 0), new Vector3(.42f, .04f, .42f), cone);
            for (int k = 0; k < 4; k++) Box(c, "Cone ring", new Vector3(0, .12f + k * .12f, 0), new Vector3(.32f - k * .06f, .06f, .32f - k * .06f), k == 2 ? flowerW : cone, PrimitiveType.Cylinder);
        }
        // Rubble heaps and puddles.
        foreach (var (x, z) in new[] { (-3.6f, 30.2f), (-13.0f, 36.1f), (-7.6f, 38.9f) })
        {
            Box(lot, "Sand heap", new Vector3(x, .12f, z), new Vector3(1.8f, .6f, 1.4f), Mat("MS_Sand", "D8C08A", .05f), PrimitiveType.Sphere);
            for (int i = 0; i < 9; i++)
            {
                var chunk = Box(lot, "Rubble", new Vector3(x + Rand(-1f, 1f), Rand(.08f, .3f), z + Rand(-.8f, .8f)), new Vector3(Rand(.2f, .5f), Rand(.15f, .3f), Rand(.2f, .45f)), i % 3 == 0 ? Brick() : Concrete());
                chunk.transform.localRotation = Quaternion.Euler(Rand(-25, 25), Rand(0, 180), Rand(-25, 25));
            }
        }
        foreach (var (x, z, d) in new[] { (-8.4f, 34.5f, 1.9f), (-10.9f, 36.7f, 1.2f), (-5.9f, 36.9f, 1.5f) })
            Box(lot, "Puddle", new Vector3(x, .14f, z), new Vector3(d, .005f, d * .7f), puddle, PrimitiveType.Cylinder);
        // Grass everywhere it can grow: the gaps in the slab, along the fence and round the rubbish.
        var sway = new List<Transform>();
        for (int i = 0; i < 70; i++)
        {
            Vector3 p;
            int zone = i % 5;
            if (zone == 0) p = new Vector3(Rand(-8.6f, -5.6f), 0, Rand(34.6f, 38.0f));              // missing slab piece
            else if (zone == 1) p = new Vector3(Rand(-15.3f, -1.0f), 0, Rand(39.4f, 39.8f));        // back fence
            else if (zone == 2) p = new Vector3(Rand(-15.3f, -14.9f), 0, Rand(29f, 39f));           // west fence
            else if (zone == 3) p = new Vector3(Rand(-15f, -1.2f), 0, Rand(30.8f, 31.0f));          // slab edge
            else p = new Vector3(Rand(-15f, -1.2f), 0, Rand(29f, 39.5f));
            bool tall = i % 9 == 0;
            var clump = Node(lot, tall ? "Anim grass" : "Grass", p, Quaternion.Euler(0, Rand(0, 360), 0));
            int blades = tall ? 7 : 5;
            for (int b = 0; b < blades; b++)
            {
                float h = (tall ? Rand(.6f, 1.1f) : Rand(.25f, .55f));
                var blade = Box(clump, "Blade", new Vector3(Rand(-.12f, .12f), h * .5f, Rand(-.12f, .12f)), new Vector3(.05f, h, .05f), b % 3 == 0 ? grassDry : b % 3 == 1 ? grass : grassDark);
                blade.transform.localRotation = Quaternion.Euler(Rand(-18, 18), 0, Rand(-18, 18));
            }
            if (i % 4 == 0) Box(clump, "Flower", new Vector3(Rand(-.1f, .1f), tall ? .7f : .4f, Rand(-.1f, .1f)), Vector3.one * .09f, i % 8 == 0 ? flowerW : flowerY, PrimitiveType.Sphere);
            if (tall) sway.Add(clump);
        }
        // Signs: a danger board on the fence and a lit "coming soon" billboard for the central warehouse.
        var danger = Node(lot, "Danger sign", new Vector3(-8.3f, 0, 25.72f));
        Box(danger, "Board", new Vector3(0, 1.25f, 0), new Vector3(1.4f, .8f, .04f), Mat("MS_DangerRed", "C0392B", .3f));
        Text(danger, "PERIGO", new Vector3(0, 1.38f, -.03f), 0, Color.white, .04f);
        Text(danger, "NÃO ENTRE", new Vector3(0, 1.1f, -.03f), 0, Color.white, .025f);
        var bill = Node(lot, "Coming soon billboard", new Vector3(-12.2f, 0, 26.35f));
        foreach (float x in new[] { -1.6f, 1.6f }) Box(bill, "Post", new Vector3(x, 1.6f, .05f), new Vector3(.14f, 3.2f, .14f), Navy());
        Box(bill, "Frame", new Vector3(0, 3.35f, .06f), new Vector3(4.5f, 2.3f, .12f), Gold());
        Quad(bill, "Print", new Vector3(0, 3.35f, -.01f), new Vector2(4.3f, 2.1f), 0, Printed2("MS_LotBillboard"));
        foreach (float x in new[] { -1.3f, 1.3f })
        {
            Beam(bill, "Lamp arm", new Vector3(x, 4.5f, .05f), new Vector3(x, 4.8f, -.55f), .04f, Gold());
            Box(bill, "Lamp head", new Vector3(x, 4.78f, -.6f), new Vector3(.3f, .1f, .18f), Navy());
            Box(bill, "Lamp light", new Vector3(x, 4.72f, -.6f), new Vector3(.24f, .02f, .12f), Led());
        }
        // A broken yard lamp that still flickers.
        var lamp = Node(lot, "Broken lamp", new Vector3(-1.3f, 0, 38.9f));
        Cyl(lamp, "Pole", Vector3.zero, .07f, 3.6f, Cable());
        var head = Node(lamp, "Head", new Vector3(0, 3.6f, 0), Quaternion.Euler(0, 0, -24));
        Box(head, "Arm", new Vector3(-.35f, 0, 0), new Vector3(.7f, .06f, .06f), Cable());
        Box(head, "Shade", new Vector3(-.7f, -.08f, 0), new Vector3(.4f, .12f, .25f), Cable());
        var bulb = Node(head, "Anim bulb", new Vector3(-.7f, -.16f, 0));
        Box(bulb, "Bulb", Vector3.zero, new Vector3(.26f, .05f, .16f), Led());
        // Pigeons.
        var birds = new List<Transform>();
        foreach (var (x, z) in new[] { (-8.2f, 33.1f), (-7.4f, 33.6f), (-8.9f, 33.8f), (-10.6f, 31.2f), (-4.4f, 34.8f), (-11.8f, 37.2f) })
        {
            var bird = Node(lot, "Anim pigeon", new Vector3(x, .2f, z), Quaternion.Euler(0, Rand(0, 360), 0));
            Box(bird, "Pigeon body", new Vector3(0, .1f, 0), new Vector3(.17f, .15f, .28f), pigeon, PrimitiveType.Sphere);
            Box(bird, "Pigeon head", new Vector3(0, .2f, .12f), new Vector3(.1f, .1f, .1f), pigeonHead, PrimitiveType.Sphere);
            Box(bird, "Pigeon beak", new Vector3(0, .19f, .18f), new Vector3(.02f, .02f, .05f), cone);
            Box(bird, "Pigeon tail", new Vector3(0, .1f, -.17f), new Vector3(.1f, .03f, .12f), pigeonHead);
            birds.Add(bird);
        }

        Bake(lot, "DerelictLot");
        var life = lot.gameObject.AddComponent<CheckoutLotLife>();
        life.pigeons = birds.ToArray(); life.grass = sway.ToArray();
        life.tarp = tarpPivot; life.cat = tail;
        life.lamp = bulb.GetComponentInChildren<Renderer>(); life.lampOn = Led(); life.lampOff = BulbOff();
        Debug.Log("DERELICT_LOT built pieces=" + lot.childCount);
    }

    static Transform FreshBuilding(Transform root, string name, string hideChild, out Vector3 min, out Vector3 max, Vector3 fallbackMin, Vector3 fallbackMax)
    {
        foreach (var old in root.Cast<Transform>().Where(t => t.name == name || t.name == "Brand sign").ToArray()) UnityEngine.Object.DestroyImmediate(old.gameObject);
        min = fallbackMin; max = fallbackMax;
        var legacy = root.Find(hideChild);
        if (legacy)
        {
            bool was = root.gameObject.activeSelf; root.gameObject.SetActive(true); legacy.gameObject.SetActive(true);
            var rs = legacy.GetComponentsInChildren<Renderer>();
            if (rs.Length > 0) { var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds); min = b.min; max = b.max; }
            legacy.gameObject.SetActive(false); root.gameObject.SetActive(was);
        }
        var own = root.GetComponent<MeshRenderer>(); if (own) own.enabled = false;
        var building = new GameObject(name).transform;
        building.position = new Vector3((min.x + max.x) * .5f, min.y, (min.z + max.z) * .5f);
        building.rotation = Quaternion.identity;
        building.SetParent(root, true);
        return building;
    }

    // Rooftop turbine vent (spins) and a packaged AC unit whose fan turns.
    static Transform Vent(Transform parent, Vector3 at)
    {
        var v = Node(parent, "Vent", at);
        Cyl(v, "Vent neck", Vector3.zero, .16f, .35f, Galvanized());
        var spin = Node(v, "Anim vent", new Vector3(0, .35f, 0));
        Cyl(spin, "Vent drum", Vector3.zero, .26f, .32f, Galvanized());
        for (int i = 0; i < 8; i++)
        {
            float a = i * 45 * Mathf.Deg2Rad;
            var fin = Box(spin, "Vent fin", new Vector3(Mathf.Cos(a) * .26f, .16f, Mathf.Sin(a) * .26f), new Vector3(.03f, .3f, .1f), Galvanized());
            fin.transform.localRotation = Quaternion.Euler(0, -i * 45 + 20, 0);
        }
        Box(spin, "Vent cap", new Vector3(0, .36f, 0), new Vector3(.4f, .06f, .4f), Galvanized(), PrimitiveType.Sphere);
        return spin;
    }

    static Transform AirUnit(Transform parent, Vector3 at, float yaw)
    {
        var u = Node(parent, "AC unit", at, Quaternion.Euler(0, yaw, 0));
        Box(u, "AC body", new Vector3(0, .42f, 0), new Vector3(1.7f, .8f, 1.1f), Galvanized());
        Box(u, "AC louvres", new Vector3(0, .42f, -.56f), new Vector3(1.5f, .6f, .02f), Cable());
        Box(u, "AC stripe", new Vector3(0, .78f, -.555f), new Vector3(1.72f, .06f, .02f), Gold());
        Cyl(u, "AC fan ring", new Vector3(.35f, .82f, .1f), .34f, .05f, Cable());
        var fan = Node(u, "Anim fan", new Vector3(.35f, .88f, .1f));
        for (int i = 0; i < 4; i++)
        {
            var blade = Box(fan, "Fan blade", Vector3.zero, new Vector3(.58f, .02f, .1f), Galvanized());
            blade.transform.localRotation = Quaternion.Euler(12, i * 45, 0);
        }
        Box(u, "AC plinth", new Vector3(0, .04f, 0), new Vector3(1.8f, .08f, 1.2f), Concrete());
        return fan;
    }

    static Transform RollerDoorBay(Transform parent, string name, Vector3 centerBottom, float width, float height, bool eastFacing, out Transform pivot)
    {
        // centerBottom is on the wall face. Local frame: +z out of the wall.
        var g = Node(parent, name, centerBottom, Quaternion.Euler(0, eastFacing ? 90 : 180, 0));
        Box(g, "Opening", new Vector3(0, height * .5f, .015f), new Vector3(width, height, .04f), InteriorDark());
        Box(g, "Jamb L", new Vector3(-width * .5f - .15f, height * .5f, .08f), new Vector3(.3f, height + .1f, .2f), Limestone());
        Box(g, "Jamb R", new Vector3(width * .5f + .15f, height * .5f, .08f), new Vector3(.3f, height + .1f, .2f), Limestone());
        Box(g, "Door housing", new Vector3(0, height + .28f, .2f), new Vector3(width + .6f, .5f, .45f), Navy());
        Box(g, "Housing trim", new Vector3(0, height + .05f, .43f), new Vector3(width + .6f, .06f, .03f), Gold());
        pivot = Node(g, "Anim door", new Vector3(0, height, .06f));
        Box(pivot, "Door curtain", new Vector3(0, -height * .5f, 0), new Vector3(width, height, .06f), RollerDoor());
        Box(pivot, "Bottom rail", new Vector3(0, -height + .05f, .02f), new Vector3(width, .1f, .08f), Rubber());
        return g;
    }

    static void Letters(Transform parent, string text, Vector3 at, float size, float yaw)
    {
        var holder = Node(parent, "Letters " + text, at, Quaternion.Euler(0, yaw, 0));
        Letters3D(holder, text, Vector3.zero, size);
    }

    static void WallLamp(Transform parent, Vector3 at, float yaw)
    {
        var l = Node(parent, "Wall lamp", at, Quaternion.Euler(0, yaw, 0));
        Box(l, "Lamp arm", new Vector3(0, 0, .2f), new Vector3(.05f, .05f, .4f), Gold());
        Box(l, "Lamp shade", new Vector3(0, -.05f, .4f), new Vector3(.3f, .12f, .2f), Navy());
        Box(l, "Lamp light", new Vector3(0, -.12f, .4f), new Vector3(.24f, .02f, .14f), Led());
    }

    static void PalletStack(Transform parent, Vector3 at, float yaw, int count, bool bricks, int seed)
    {
        var p = Node(parent, "Pallets", at, Quaternion.Euler(0, yaw, 0));
        var r = new System.Random(seed);
        for (int i = 0; i < count; i++)
        {
            var o = new Vector3((i % 2) * 1.3f, 0, (i / 2) * 1.05f);
            Box(p, "Pallet", o + new Vector3(0, .07f, 0), new Vector3(1.2f, .14f, .95f), Planks());
            int layers = 1 + r.Next(3);
            for (int k = 0; k < layers; k++)
                Box(p, bricks ? "Bricks" : "Boxes", o + new Vector3(0, .14f + .22f + k * .42f, 0), new Vector3(1.1f - k * .08f, .4f, .85f - k * .06f), bricks ? Brick() : Cardboard());
            if (!bricks) Box(p, "Wrap band", o + new Vector3(0, .14f + .3f, .43f), new Vector3(1.12f, .05f, .01f), Navy());
        }
    }

    // ------------------------------------------------------------------ DEPÓSITO
    static void BuildDepot(Transform root)
    {
        var b = FreshBuilding(root, "Depot building", "ReplacementVisual", out var min, out var max, new Vector3(-5.4f, .03f, 17.1f), new Vector3(2.1f, 5.1f, 24.3f));
        float w = max.x - min.x, d = max.z - min.z, hx = w * .5f, hz = d * .5f;
        float plinth = .6f, wallTop = 4.1f, fasciaTop = 4.45f, parapet = 4.62f;
        var s = Node(b, "Shell", Vector3.zero);
        Box(s, "Plinth", new Vector3(0, plinth * .5f, 0), new Vector3(w + .16f, plinth, d + .16f), Limestone());
        Box(s, "Cladding", new Vector3(0, (plinth + wallTop) * .5f, 0), new Vector3(w, wallTop - plinth, d), Cladding());
        Ring(s, "Belt", w, d, 2.0f, 2.14f, .06f, .04f, Limestone(), false);
        Ring(s, "Fascia", w, d, wallTop, fasciaTop, .08f, .06f, Gold());
        Ring(s, "LED line", w, d, wallTop - .06f, wallTop - .01f, .04f, .08f, Led());
        Ring(s, "Parapet", w, d, fasciaTop, parapet, .28f, .1f, Limestone());
        Box(s, "Roof", new Vector3(0, fasciaTop - .1f, 0), new Vector3(w - .3f, .12f, d - .3f), RoofSeam());
        foreach (int i in new[] { -1, 1 }) foreach (int k in new[] { -1, 1 })
            Box(s, "Pilaster", new Vector3(i * (hx - .12f), parapet * .5f, k * (hz - .12f)), new Vector3(.5f, parapet, .5f), Limestone());
        foreach (float x in new[] { -hx + .2f, hx - .2f }) Cyl(s, "Downpipe", new Vector3(x + (x < 0 ? .3f : -.3f), plinth, hz + .08f), .07f, wallTop - plinth, Gold());

        // South front (faces the shop and the camera): glass door with canopy, a ribbon window and the name.
        float face = -hz;
        var door = Node(s, "Entrance", new Vector3(-hx + 1.55f, 0, face));
        Box(door, "Door frame", new Vector3(0, plinth + 1.2f, -.05f), new Vector3(1.4f, 2.4f, .12f), Navy());
        Box(door, "Door glass", new Vector3(0, plinth + 1.12f, -.1f), new Vector3(1.1f, 2.15f, .04f), WindowGlow());
        Box(door, "Door mullion", new Vector3(0, plinth + 1.12f, -.12f), new Vector3(.06f, 2.15f, .02f), Navy());
        Box(door, "Handle", new Vector3(.12f, plinth + 1.1f, -.14f), new Vector3(.03f, .5f, .03f), Gold());
        for (int i = 0; i < 3; i++) { float sh = plinth * (i + 1) / 3f; Box(door, "Step", new Vector3(0, sh * .5f, -.3f - (2 - i) * .3f), new Vector3(1.8f, sh, .3f), Limestone()); }
        Box(door, "Canopy", new Vector3(0, 3.05f, -.55f), new Vector3(2.0f, .12f, 1.1f), Navy());
        Box(door, "Canopy edge", new Vector3(0, 3.05f, -1.1f), new Vector3(2.0f, .16f, .05f), Gold());
        Box(door, "Canopy light", new Vector3(0, 2.98f, -.55f), new Vector3(1.6f, .02f, .5f), Led());
        foreach (float x in new[] { -.95f, .95f }) Beam(door, "Canopy tie", new Vector3(x, 3.8f, -.02f), new Vector3(x, 3.1f, -1.05f), .03f, Galvanized());
        var ribbon = Node(s, "Ribbon window", new Vector3(.8f, 0, face));
        float rw = w - 3.4f;
        Box(ribbon, "Glass", new Vector3(0, 2.75f, -.03f), new Vector3(rw, .95f, .04f), WindowGlow());
        Box(ribbon, "Sill", new Vector3(0, 2.22f, -.1f), new Vector3(rw + .2f, .1f, .2f), Limestone());
        Box(ribbon, "Head", new Vector3(0, 3.27f, -.07f), new Vector3(rw + .2f, .08f, .12f), Limestone());
        for (float x = -rw * .5f; x <= rw * .5f + .01f; x += rw / 4) Box(ribbon, "Mullion", new Vector3(x, 2.75f, -.07f), new Vector3(.07f, .95f, .06f), Navy());
        Letters(s, "DEPÓSITO", new Vector3(.8f, 3.72f, face - .12f), .06f, 0);
        var bulbs = Node(s, "Anim bulbs", Vector3.zero);
        for (int i = 0; i < 11; i++) Box(bulbs, "Bulb", new Vector3(.8f - rw * .5f + i * rw / 10f, wallTop - .2f, face - .12f), Vector3.one * .1f, Led(), PrimitiveType.Sphere);
        WallLamp(s, new Vector3(-hx + .55f, 2.9f, face), 180);
        WallLamp(s, new Vector3(hx - .55f, 2.9f, face), 180);

        // East side faces the truck yard: roller door, dock bumpers, hazard kerb, canopy and stacked pallets.
        var bay = RollerDoorBay(s, "Loading door", new Vector3(hx, plinth, -.2f), 3.0f, 2.9f, true, out var doorPivot);
        foreach (float z in new[] { -1.8f, 1.4f }) Box(s, "Bumper", new Vector3(hx + .1f, .45f, z), new Vector3(.2f, .35f, .25f), Rubber());
        Box(s, "Hazard kerb", new Vector3(hx + .22f, plinth + .02f, -.2f), new Vector3(.3f, .04f, 3.4f), Hazard());
        Box(s, "Side canopy", new Vector3(hx + .8f, 4.0f, -.2f), new Vector3(1.6f, .14f, 4.0f), Navy());
        Box(s, "Side canopy edge", new Vector3(hx + 1.6f, 4.0f, -.2f), new Vector3(.05f, .18f, 4.0f), Gold());
        Box(s, "Side canopy light", new Vector3(hx + .8f, 3.92f, -.2f), new Vector3(1.2f, .02f, 3.4f), Led());
        PalletStack(s, new Vector3(hx + 1.1f, 0, -hz + .2f), 0, 3, false, 3);
        // North and west: windows so the back is not a blank box.
        foreach (float x in new[] { -hx * .45f, hx * .45f })
        {
            Box(s, "Back window", new Vector3(x, 2.8f, hz + .03f), new Vector3(1.4f, .8f, .04f), WindowGlow());
            Box(s, "Back sill", new Vector3(x, 2.35f, hz + .1f), new Vector3(1.6f, .08f, .18f), Limestone());
        }
        Box(s, "West window", new Vector3(-hx - .03f, 2.8f, 0), new Vector3(.04f, .8f, 2.2f), WindowGlow());
        Box(s, "West sill", new Vector3(-hx - .1f, 2.35f, 0), new Vector3(.18f, .08f, 2.4f), Limestone());

        // Roof: solar panels, an AC unit and turbine vents.
        var roof = Node(s, "Roof kit", new Vector3(0, fasciaTop - .04f, 0));
        for (int i = 0; i < 3; i++)
        {
            var panel = Box(roof, "Solar panel", new Vector3(-hx + 1.6f + i * 1.55f, .45f, -hz + 1.6f), new Vector3(1.45f, .05f, 1.9f), Solar());
            panel.transform.localRotation = Quaternion.Euler(-18, 0, 0);
            Box(roof, "Solar leg", new Vector3(-hx + 1.6f + i * 1.55f, .2f, -hz + 2.3f), new Vector3(1.2f, .4f, .06f), Galvanized());
        }
        var fan = AirUnit(roof, new Vector3(hx - 1.4f, 0, hz - 1.2f), 0);
        var vents = new[] { Vent(roof, new Vector3(-hx + 1.2f, 0, hz - 1.0f)), Vent(roof, new Vector3(.2f, 0, hz - .9f)) };

        Bake(s, "Depot_" + (int)(w * 10) + "x" + (int)(d * 10));
        var life = b.gameObject.AddComponent<CheckoutStorageLife>();
        life.doors = new[] { new CheckoutStorageLife.Door { pivot = doorPivot, period = 16f, offset = 3f } };
        life.fans = new[] { fan }; life.vents = vents;
        life.bulbs = bulbs.GetComponentsInChildren<Renderer>(); life.bulbOn = Led(); life.bulbOff = BulbOff();
        Debug.Log("STORAGE_DEPOT built " + min.ToString("F2") + " " + max.ToString("F2"));
    }

    // ------------------------------------------------------------------ ARMAZÉM CENTRAL
    static void BuildCentralWarehouse(Transform world, Transform root)
    {
        var b = FreshBuilding(root, "Central warehouse", "Warehouse model", out var min, out var max, new Vector3(-15.95f, .13f, 27.7f), new Vector3(-.35f, 6.46f, 40.7f));
        float w = max.x - min.x, d = max.z - min.z, hx = w * .5f, hz = d * .5f;
        float dock = 1.0f, wallTop = 5.6f, fasciaTop = 6.0f, parapet = 6.25f;
        var s = Node(b, "Shell", Vector3.zero);
        Box(s, "Dock plinth", new Vector3(0, dock * .5f, 0), new Vector3(w + .1f, dock, d + .1f), Concrete());
        Box(s, "Cladding", new Vector3(0, (dock + wallTop) * .5f, 0), new Vector3(w, wallTop - dock, d), Cladding());
        Ring(s, "Belt", w, d, 3.0f, 3.2f, .08f, .05f, Limestone(), false);
        Ring(s, "Fascia", w, d, wallTop, fasciaTop, .08f, .06f, Gold());
        Ring(s, "LED line", w, d, wallTop - .07f, wallTop - .01f, .04f, .08f, Led());
        Ring(s, "Parapet", w, d, fasciaTop, parapet, .3f, .1f, Limestone());
        Box(s, "Roof", new Vector3(0, fasciaTop - .1f, 0), new Vector3(w - .4f, .12f, d - .4f), RoofSeam());
        float[] px = { -hx, -hx * .5f, 0, hx * .5f, hx };
        foreach (float x in px) foreach (int k in new[] { -1, 1 })
            Box(s, "Pilaster", new Vector3(Mathf.Clamp(x, -hx + .15f, hx - .15f), parapet * .5f, k * (hz - .15f)), new Vector3(.55f, parapet, .55f), Limestone());
        // Clerestory glazing between the pilasters on the long sides.
        for (int i = 0; i < px.Length - 1; i++)
            foreach (int k in new[] { -1, 1 })
            {
                float cx = (px[i] + px[i + 1]) * .5f, span = (px[i + 1] - px[i]) - .9f;
                if (k < 0 && cx < -hx + 4.8f) continue; // the office block covers this bay
                Box(s, "Clerestory", new Vector3(cx, 4.65f, k * (hz + .03f)), new Vector3(span, .9f, .04f), WindowGlow());
                Box(s, "Clerestory sill", new Vector3(cx, 4.15f, k * (hz + .1f)), new Vector3(span + .2f, .08f, .18f), Limestone());
                for (int m = 1; m < 4; m++) Box(s, "Clerestory mullion", new Vector3(cx - span * .5f + span * m / 4, 4.65f, k * (hz + .07f)), new Vector3(.07f, .9f, .05f), Navy());
            }
        foreach (float z in new[] { -hz + .3f, hz - .3f }) Cyl(s, "Downpipe", new Vector3(-hx - .08f, dock, z), .08f, wallTop - dock, Gold());
        // West gable (seen from the car park): pilasters and a clerestory like the long sides.
        float[] pz = { -hz, -hz * .5f, 0, hz * .5f, hz };
        foreach (float z in new[] { -hz * .5f, 0, hz * .5f }) Box(s, "Pilaster", new Vector3(-hx + .15f, parapet * .5f, z), new Vector3(.55f, parapet, .55f), Limestone());
        for (int i = 0; i < pz.Length - 1; i++)
        {
            float cz = (pz[i] + pz[i + 1]) * .5f, span = (pz[i + 1] - pz[i]) - .9f;
            Box(s, "Clerestory", new Vector3(-hx - .03f, 4.65f, cz), new Vector3(.04f, .9f, span), WindowGlow());
            Box(s, "Clerestory sill", new Vector3(-hx - .1f, 4.15f, cz), new Vector3(.18f, .08f, span + .2f), Limestone());
            for (int m = 1; m < 3; m++) Box(s, "Clerestory mullion", new Vector3(-hx - .07f, 4.65f, cz - span * .5f + span * m / 3), new Vector3(.05f, .9f, .07f), Navy());
        }

        // Office block on the south-west corner: two storeys of lit glass in a limestone frame.
        var office = Node(s, "Office", new Vector3(-hx + 2.4f, 0, -hz - .5f));
        Box(office, "Office frame", new Vector3(0, 2.7f, 0), new Vector3(4.8f, 5.4f, 1.0f), Limestone());
        foreach (float y in new[] { 1.45f, 3.75f })
        {
            Box(office, "Office glass", new Vector3(0, y, -.52f), new Vector3(4.0f, 1.55f, .04f), WindowGlow());
            for (int m = -2; m <= 2; m++) Box(office, "Office mullion", new Vector3(m * 1.0f, y, -.55f), new Vector3(.08f, 1.55f, .05f), Navy());
        }
        Box(office, "Office spandrel", new Vector3(0, 2.6f, -.53f), new Vector3(4.0f, .6f, .05f), Navy());
        Box(office, "Office cap", new Vector3(0, 5.5f, 0), new Vector3(5.0f, .22f, 1.2f), Gold());
        Box(office, "Office canopy", new Vector3(1.2f, 2.45f, -1.05f), new Vector3(1.8f, .12f, 1.1f), Navy());
        Box(office, "Office canopy edge", new Vector3(1.2f, 2.45f, -1.6f), new Vector3(1.8f, .16f, .05f), Gold());
        Box(office, "Office canopy light", new Vector3(1.2f, 2.38f, -1.05f), new Vector3(1.4f, .02f, .5f), Led());

        // Rooftop name board over the south front, lit and with chasing bulbs.
        var sign = Node(s, "Name board", new Vector3(1.4f, parapet, -hz + .4f));
        float sw = 9.2f, sh = 1.3f, lift = .7f;
        foreach (float x in new[] { -sw * .35f, 0, sw * .35f })
        {
            Box(sign, "Board leg", new Vector3(x, lift * .5f, .2f), new Vector3(.16f, lift, .16f), Navy());
            Beam(sign, "Board strut", new Vector3(x, lift + sh * .4f, .2f), new Vector3(x, 0, 1.4f), .1f, Galvanized());
        }
        float cy = lift + sh * .5f;
        Box(sign, "Board", new Vector3(0, cy, .1f), new Vector3(sw, sh, .18f), Navy());
        foreach (float y in new[] { cy + sh * .5f + .05f, cy - sh * .5f - .05f }) Box(sign, "Board trim", new Vector3(0, y, .06f), new Vector3(sw + .16f, .1f, .24f), Gold());
        foreach (float x in new[] { -sw * .5f - .04f, sw * .5f + .04f }) Box(sign, "Board trim", new Vector3(x, cy, .06f), new Vector3(.1f, sh + .2f, .24f), Gold());
        Letters3D(sign, "ARMAZÉM CENTRAL", new Vector3(0, cy + .04f, -.02f), .075f);
        Box(sign, "Board LED", new Vector3(0, cy - sh * .5f + .15f, -.02f), new Vector3(sw * .84f, .04f, .02f), Led());
        var bulbs = Node(sign, "Anim bulbs", Vector3.zero);
        for (int i = 0; i < 17; i++) Box(bulbs, "Bulb", new Vector3(-sw * .5f + .25f + i * (sw - .5f) / 16f, cy + sh * .5f + .2f, .02f), Vector3.one * .11f, Led(), PrimitiveType.Sphere);

        // East dock: three bays with shelters, bumpers, levelers, signal lights and numbers under a long canopy.
        var yard = world.Find(CheckoutMarketLayout.GrandYard + "/Bays");
        float[] bayZ = { 30.4f, 33.4f, 36.4f };
        var doors = new List<CheckoutStorageLife.Door>();
        for (int i = 0; i < bayZ.Length; i++)
        {
            float z = bayZ[i] - b.position.z;
            RollerDoorBay(s, "Dock door " + (i + 1), new Vector3(hx, dock, z), 2.6f, 3.0f, true, out var pivot);
            var shelter = Node(s, "Dock shelter " + (i + 1), new Vector3(hx + .25f, dock, z));
            Box(shelter, "Shelter top", new Vector3(0, 3.25f, 0), new Vector3(.5f, .45f, 3.3f), Rubber());
            foreach (int k in new[] { -1, 1 }) Box(shelter, "Shelter side", new Vector3(0, 1.6f, k * 1.5f), new Vector3(.5f, 3.2f, .32f), Rubber());
            foreach (int k in new[] { -1, 1 }) Box(shelter, "Bumper", new Vector3(.18f, -.28f, k * 1.05f), new Vector3(.22f, .38f, .26f), Rubber());
            Box(shelter, "Leveler", new Vector3(.05f, .01f, 0), new Vector3(.6f, .04f, 2.3f), Galvanized());
            Box(shelter, "Signal box", new Vector3(.02f, 1.9f, 1.95f), new Vector3(.16f, .5f, .22f), Navy());
            var lamp = Node(shelter, "Anim signal " + (i + 1), new Vector3(.12f, 2.0f, 1.95f));
            Box(lamp, "Signal lamp", Vector3.zero, Vector3.one * .16f, RedLamp(), PrimitiveType.Sphere);
            Box(shelter, "Number plate", new Vector3(-.2f, 4.35f, 0), new Vector3(.08f, .55f, .55f), Navy());
            var number = Text(shelter, (i + 1).ToString(), new Vector3(-.15f, 4.35f, 0), -90, new Color(1f, .84f, .38f), .06f);
            var bayMark = yard ? yard.Cast<Transform>().OrderBy(t => Mathf.Abs(t.position.z - bayZ[i])).FirstOrDefault() : null;
            doors.Add(new CheckoutStorageLife.Door { pivot = pivot, watch = bayMark ? world.Find(bayMark.name) : null, watchHome = bayMark ? bayMark.position : Vector3.zero, signal = lamp.GetComponentInChildren<Renderer>(), period = 20, offset = i * 5 });
        }
        Box(s, "Dock edge", new Vector3(hx + .04f, dock - .1f, 0), new Vector3(.08f, .2f, d - .6f), Hazard());
        var canopy = Node(s, "Dock canopy", new Vector3(hx, 0, 0));
        Box(canopy, "Canopy deck", new Vector3(1.2f, 5.0f, 0), new Vector3(2.4f, .2f, d - .8f), Navy());
        Box(canopy, "Canopy fascia", new Vector3(2.4f, 5.0f, 0), new Vector3(.08f, .32f, d - .8f), Gold());
        Box(canopy, "Canopy LED", new Vector3(1.2f, 4.88f, 0), new Vector3(2.0f, .03f, d - 1.2f), Led());
        for (float z = -hz + .8f; z <= hz - .7f; z += (d - 1.6f) / 4) Beam(canopy, "Canopy tie", new Vector3(0, 5.9f, z), new Vector3(2.35f, 5.1f, z), .04f, Galvanized());

        // South: a loading ramp and roller door for the forklift, with a pallet rack outside.
        float rampX = 3.0f;
        RollerDoorBay(s, "Forklift door", new Vector3(rampX, dock, -hz), 2.4f, 2.5f, false, out var forkliftPivot);
        var ramp = Box(s, "Ramp", new Vector3(rampX, dock * .5f - .05f, -hz - 1.7f), new Vector3(2.4f, .1f, Mathf.Sqrt(3.4f * 3.4f + dock * dock)), Concrete());
        ramp.transform.localRotation = Quaternion.Euler(-Mathf.Atan2(dock, 3.4f) * Mathf.Rad2Deg, 0, 0);
        Box(s, "Ramp fill", new Vector3(rampX, dock * .25f, -hz - .9f), new Vector3(2.3f, dock * .5f, 1.7f), Concrete());
        foreach (int k in new[] { -1, 1 }) Box(s, "Ramp kerb", new Vector3(rampX + k * 1.25f, dock * .5f, -hz - 1.7f), new Vector3(.1f, .12f, 3.4f), Hazard()).transform.localRotation = ramp.transform.localRotation;
        var rack = Node(s, "Pallet rack", new Vector3(rampX + 4.4f, 0, -hz - 3.4f), Quaternion.Euler(0, -90, 0));
        foreach (float x in new[] { -1.4f, 0, 1.4f }) foreach (float z in new[] { -.5f, .5f }) Box(rack, "Upright", new Vector3(x, 1.4f, z), new Vector3(.08f, 2.8f, .08f), Navy());
        foreach (float y in new[] { .15f, 1.45f, 2.75f }) foreach (float z in new[] { -.5f, .5f }) Box(rack, "Beam", new Vector3(0, y, z), new Vector3(2.9f, .1f, .08f), RackOrange());
        foreach (float y in new[] { 1.5f, 2.8f }) foreach (float x in new[] { -.7f, .7f })
        {
            Box(rack, "Rack pallet", new Vector3(x, y + .07f, 0), new Vector3(1.2f, .12f, .95f), Planks());
            Box(rack, "Rack boxes", new Vector3(x, y + .38f, 0), new Vector3(1.05f, .5f, .85f), Cardboard());
        }
        PalletStack(s, new Vector3(rampX + 5.6f, 0, -hz - 1.2f), 0, 2, false, 9);

        // Rooftop: skylights, solar arrays, AC units, turbine vents and an antenna with a beacon.
        var roofKit = Node(s, "Roof kit", new Vector3(0, fasciaTop - .04f, 0));
        foreach (float z in new[] { -1.2f, 2.2f })
        {
            Box(roofKit, "Skylight", new Vector3(-1.0f, .18f, z), new Vector3(w - 5f, .28f, 1.0f), Skylight());
            Box(roofKit, "Skylight frame", new Vector3(-1.0f, .06f, z), new Vector3(w - 4.8f, .12f, 1.2f), Galvanized());
        }
        for (int i = 0; i < 6; i++)
        {
            var panel = Box(roofKit, "Solar panel", new Vector3(-hx + 2.0f + i * 1.9f, .45f, -hz + 2.0f), new Vector3(1.8f, .05f, 2.0f), Solar());
            panel.transform.localRotation = Quaternion.Euler(-18, 0, 0);
            Box(roofKit, "Solar leg", new Vector3(-hx + 2.0f + i * 1.9f, .2f, -hz + 2.75f), new Vector3(1.5f, .4f, .06f), Galvanized());
        }
        var fans = new[] { AirUnit(roofKit, new Vector3(hx - 2.2f, 0, hz - 1.6f), 0), AirUnit(roofKit, new Vector3(-hx + 3.0f, 0, hz - 1.6f), 0) };
        var vents = new[] { Vent(roofKit, new Vector3(-4f, 0, .5f)), Vent(roofKit, new Vector3(0f, 0, .5f)), Vent(roofKit, new Vector3(4f, 0, .5f)) };
        var antenna = Node(roofKit, "Antenna", new Vector3(-hx + .8f, 0, hz - .8f));
        Cyl(antenna, "Mast", Vector3.zero, .05f, 2.6f, Galvanized());
        var beacon = Node(antenna, "Anim beacon", new Vector3(0, 2.7f, 0));
        Box(beacon, "Beacon", Vector3.zero, Vector3.one * .2f, RedLamp(), PrimitiveType.Sphere);

        // Forklift (navy with gold, the shop's colours) that shuttles pallets from the rack up the ramp.
        var forklift = Node(b, "Anim forklift", new Vector3(rampX + 2.8f, 0, -hz - 3.4f), Quaternion.Euler(0, 90, 0));
        var body = Node(forklift, "Body", Vector3.zero);
        Box(body, "Chassis", new Vector3(0, .45f, -.2f), new Vector3(1.05f, .5f, 1.7f), Navy());
        Box(body, "Counterweight", new Vector3(0, .55f, -1.0f), new Vector3(1.05f, .75f, .4f), Concrete());
        Box(body, "Stripe", new Vector3(0, .72f, -.2f), new Vector3(1.07f, .06f, 1.72f), Gold());
        Box(body, "Seat", new Vector3(0, .85f, -.45f), new Vector3(.5f, .3f, .45f), Cable());
        foreach (float x in new[] { -.45f, .45f }) foreach (float z in new[] { .35f, -.85f })
            Box(body, "Guard post", new Vector3(x, 1.45f, z), new Vector3(.06f, 1.5f, .06f), Galvanized());
        Box(body, "Guard roof", new Vector3(0, 2.2f, -.25f), new Vector3(1.0f, .06f, 1.3f), Galvanized());
        Box(body, "Beacon base", new Vector3(0, 2.26f, -.6f), new Vector3(.12f, .06f, .12f), Navy());
        Box(body, "Beacon light", new Vector3(0, 2.34f, -.6f), Vector3.one * .12f, AmberLamp(), PrimitiveType.Sphere);
        foreach (float x in new[] { -.28f, .28f }) Box(body, "Mast rail", new Vector3(x, 1.2f, .7f), new Vector3(.08f, 2.3f, .08f), Galvanized());
        var wheels = new List<Transform>();
        foreach (float x in new[] { -.5f, .5f }) foreach (float z in new[] { .45f, -.8f })
        {
            var wheel = Node(forklift, "Anim wheel", new Vector3(x, .24f, z));
            Box(wheel, "Tyre", Vector3.zero, new Vector3(.48f, .1f, .48f), Rubber(), PrimitiveType.Cylinder).transform.localRotation = Quaternion.Euler(0, 0, 90);
            wheels.Add(wheel);
        }
        var forks = Node(forklift, "Anim forks", new Vector3(0, .1f, .78f));
        Box(forks, "Carriage", new Vector3(0, .35f, 0), new Vector3(.8f, .6f, .06f), Galvanized());
        foreach (float x in new[] { -.25f, .25f }) Box(forks, "Fork", new Vector3(x, .03f, .55f), new Vector3(.1f, .04f, 1.1f), Cable());
        var load = Node(forks, "Anim load", new Vector3(0, .1f, .6f));
        Box(load, "Load pallet", Vector3.zero, new Vector3(1.1f, .12f, .9f), Planks());
        Box(load, "Load boxes", new Vector3(0, .32f, 0), new Vector3(1.0f, .5f, .8f), Cardboard());
        Box(load, "Load band", new Vector3(0, .38f, .41f), new Vector3(1.02f, .05f, .01f), Navy());

        Bake(s, "CentralWarehouse");
        Bake(body, "Forklift");
        var life = b.gameObject.AddComponent<CheckoutStorageLife>();
        var all = new List<CheckoutStorageLife.Door>(doors) { new CheckoutStorageLife.Door { pivot = forkliftPivot, period = 999 } };
        life.doors = all.ToArray(); life.forkliftDoor = all.Count - 1;
        life.fans = fans; life.vents = vents; life.beacon = beacon;
        life.bulbs = bulbs.GetComponentsInChildren<Renderer>(); life.bulbOn = Led(); life.bulbOff = BulbOff();
        life.signalGreen = GreenLamp(); life.signalRed = RedLamp();
        life.forklift = forklift; life.forks = forks; life.forkLoad = load; life.wheels = wheels.ToArray();
        Vector3 W(float x, float y, float z) => b.TransformPoint(new Vector3(x, y, z));
        life.route = new[] { W(rampX + 2.8f, 0, -hz - 3.4f), W(rampX, 0, -hz - 3.6f), W(rampX, dock, -hz - .05f), W(rampX, dock, -hz + 2.2f) };
        // The unloader walks in through the middle dock door.
        var dockPoint = world.Find(CheckoutMarketLayout.GrandYard + "/Worker path/Dock door");
        if (dockPoint) dockPoint.position = new Vector3(max.x + .15f, dockPoint.position.y, bayZ[1] - .6f);
        Debug.Log("STORAGE_CENTRAL built " + min.ToString("F2") + " " + max.ToString("F2"));
    }

    // ------------------------------------------------------------------ construction kit
    static void BuildConstructionKit(CheckoutStageConstruction show)
    {
        var old = show.transform.Find(KitName); if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var kit = new GameObject(KitName).transform;
        kit.SetParent(show.transform, false); kit.rotation = Quaternion.identity; kit.position = new Vector3(0, -50, 0);

        // Lattice mast section, 2 m tall.
        var mast = Node(kit, "Mast section", Vector3.zero);
        float m = .42f, sec = 2f;
        var corners = new[] { new Vector3(-m, 0, -m), new Vector3(m, 0, -m), new Vector3(m, 0, m), new Vector3(-m, 0, m) };
        foreach (var c in corners) Box(mast, "Chord", c + Vector3.up * sec * .5f, new Vector3(.1f, sec, .1f), CranePaint());
        for (int i = 0; i < 4; i++)
        {
            var a = corners[i]; var b = corners[(i + 1) % 4];
            Beam(mast, "Strut", a + Vector3.up * .06f, b + Vector3.up * .06f, .06f, CranePaint());
            Beam(mast, "Diagonal", a + Vector3.up * .08f, b + Vector3.up * (sec * .5f), .05f, CranePaint());
            Beam(mast, "Diagonal", b + Vector3.up * (sec * .5f), a + Vector3.up * (sec - .02f), .05f, CranePaint());
        }
        Bake(mast, "CraneMastSection");

        var cbase = Node(kit, "Crane base", Vector3.zero);
        Box(cbase, "Footing", new Vector3(0, .35f, 0), new Vector3(2.6f, .7f, 2.6f), Concrete());
        foreach (int i in new[] { -1, 1 }) Box(cbase, "Ballast", new Vector3(i * .95f, .95f, 0), new Vector3(.6f, .5f, 2.2f), Concrete());
        Box(cbase, "Hazard band", new Vector3(0, .62f, -1.31f), new Vector3(2.6f, .16f, .02f), Hazard());
        Box(cbase, "Hazard band", new Vector3(-1.31f, .62f, 0), new Vector3(.02f, .16f, 2.6f), Hazard());
        foreach (var c in corners) Box(cbase, "Anchor plate", c + Vector3.up * .72f, new Vector3(.3f, .04f, .3f), Galvanized());
        Bake(cbase, "CraneBase");

        var top = Node(kit, "Crane top", Vector3.zero);
        Cyl(top, "Slew ring", Vector3.zero, .62f, .3f, Galvanized());
        Box(top, "Platform", new Vector3(0, .35f, 0), new Vector3(1.4f, .1f, 1.6f), Galvanized());
        var cab = Node(top, "Cab", new Vector3(.8f, -.25f, .55f));
        Box(cab, "Cab body", new Vector3(0, .55f, 0), new Vector3(.95f, 1.1f, 1.05f), TruckWhite());
        Box(cab, "Cab front glass", new Vector3(0, .65f, .53f), new Vector3(.8f, .6f, .02f), DarkGlass());
        Box(cab, "Cab side glass", new Vector3(.48f, .65f, .1f), new Vector3(.02f, .5f, .7f), DarkGlass());
        Box(cab, "Cab roof", new Vector3(0, 1.13f, 0), new Vector3(1.0f, .08f, 1.1f), Navy());
        Box(cab, "Cab stripe", new Vector3(0, .25f, 0), new Vector3(.97f, .08f, 1.07f), Gold());
        // A-frame peak.
        float peak = 3.4f;
        foreach (var c in new[] { new Vector3(-m, .4f, -m), new Vector3(m, .4f, -m), new Vector3(m, .4f, m), new Vector3(-m, .4f, m) })
            Beam(top, "Peak chord", c, new Vector3(0, peak, 0), .08f, CranePaint());
        for (float y = 1.2f; y < peak - .3f; y += .9f) { float k = 1 - (y - .4f) / (peak - .4f); Ring(Node(top, "Peak ring", Vector3.zero), "Peak ring", 2 * m * k, 2 * m * k, y, y + .05f, .04f, 0, CranePaint()); }
        // Triangular jib, 13 m, and counter-jib with ballast.
        float jib = 13f, jw = .36f, jh = .75f;
        Vector3 L(float z) => new Vector3(-jw, .45f, z); Vector3 R(float z) => new Vector3(jw, .45f, z); Vector3 T(float z) => new Vector3(0, .45f + jh, z);
        Beam(top, "Jib chord", L(.4f), L(jib), .08f, CranePaint()); Beam(top, "Jib chord", R(.4f), R(jib), .08f, CranePaint()); Beam(top, "Jib chord", T(.4f), T(jib - .6f), .08f, CranePaint());
        for (float z = .4f; z < jib - .5f; z += 1f)
        {
            Beam(top, "Jib lace", L(z), T(z + .5f), .045f, CranePaint()); Beam(top, "Jib lace", T(z + .5f), L(z + 1), .045f, CranePaint());
            Beam(top, "Jib lace", R(z), T(z + .5f), .045f, CranePaint()); Beam(top, "Jib lace", T(z + .5f), R(z + 1), .045f, CranePaint());
            Beam(top, "Jib floor", L(z), R(z), .045f, CranePaint());
        }
        Box(top, "Jib walkway", new Vector3(0, .42f, jib * .5f), new Vector3(.5f, .03f, jib - 1), Galvanized());
        Box(top, "Jib tip", new Vector3(0, .8f, jib), new Vector3(.8f, .8f, .12f), Hazard());
        float cj = 5f;
        Beam(top, "Counter chord", L(-.4f), L(-cj), .1f, CranePaint()); Beam(top, "Counter chord", R(-.4f), R(-cj), .1f, CranePaint());
        for (float z = -.4f; z > -cj; z -= 1f) Beam(top, "Counter lace", L(z), R(z - .5f), .05f, CranePaint());
        Box(top, "Counter deck", new Vector3(0, .43f, -cj * .5f), new Vector3(.9f, .04f, cj - .6f), Galvanized());
        for (int i = 0; i < 3; i++) Box(top, "Counterweight", new Vector3(0, .0f, -cj + .3f + i * .52f), new Vector3(1.1f, 1.0f, .48f), Concrete());
        Box(top, "Counter hazard", new Vector3(0, .5f, -cj - .02f), new Vector3(1.1f, .5f, .04f), Hazard());
        Beam(top, "Pendant", new Vector3(0, peak, 0), T(jib * .62f), .035f, Galvanized());
        Beam(top, "Pendant", new Vector3(0, peak, 0), new Vector3(0, .5f, -cj + .4f), .035f, Galvanized());
        var lights = Node(top, "Anim lights", Vector3.zero);
        Box(lights, "Peak light", new Vector3(0, peak + .12f, 0), Vector3.one * .2f, RedLamp(), PrimitiveType.Sphere);
        Box(lights, "Tip light", new Vector3(0, 1.3f, jib), Vector3.one * .18f, RedLamp(), PrimitiveType.Sphere);
        Bake(top, "CraneTop");

        var trolley = Node(kit, "Crane trolley", Vector3.zero);
        Box(trolley, "Trolley frame", new Vector3(0, 0, 0), new Vector3(.9f, .22f, .7f), Galvanized());
        foreach (float x in new[] { -.36f, .36f }) foreach (float z in new[] { -.25f, .25f }) Box(trolley, "Trolley wheel", new Vector3(x, .14f, z), new Vector3(.16f, .06f, .16f), Cable(), PrimitiveType.Cylinder).transform.localRotation = Quaternion.Euler(0, 0, 90);
        Box(trolley, "Sheaves", new Vector3(0, -.15f, 0), new Vector3(.3f, .12f, .3f), CranePaint());
        Bake(trolley, "CraneTrolley");

        var hook = Node(kit, "Crane hook", Vector3.zero);
        Box(hook, "Hook block", new Vector3(0, -.2f, 0), new Vector3(.36f, .42f, .24f), Hazard());
        Box(hook, "Hook shank", new Vector3(0, -.5f, 0), new Vector3(.07f, .22f, .07f), Galvanized());
        Beam(hook, "Hook bend", new Vector3(0, -.6f, 0), new Vector3(0, -.72f, .12f), .06f, Galvanized());
        Beam(hook, "Hook bend", new Vector3(0, -.72f, .12f), new Vector3(0, -.62f, .2f), .06f, Galvanized());
        Bake(hook, "CraneHook");

        var load = Node(kit, "Crane load", Vector3.zero);
        Box(load, "Pallet", new Vector3(0, -1.05f, 0), new Vector3(1.2f, .12f, .95f), Planks());
        Box(load, "Bricks", new Vector3(0, -.78f, 0), new Vector3(1.05f, .45f, .82f), Brick());
        foreach (int i in new[] { -1, 1 }) Beam(load, "Sling", new Vector3(i * .45f, -.55f, 0), new Vector3(0, 0, 0), .025f, Cable());
        Bake(load, "CraneLoad");

        // Concrete mixer truck (forward = +z): navy chassis, white cab, turning drum and a swinging chute.
        var truck = Node(kit, "Mixer truck", Vector3.zero);
        var tb = Node(truck, "Body", Vector3.zero);
        Box(tb, "Chassis", new Vector3(0, .75f, -.3f), new Vector3(1.9f, .35f, 5.6f), Navy());
        Box(tb, "Chassis stripe", new Vector3(0, .82f, -.3f), new Vector3(1.92f, .06f, 5.62f), Gold());
        Box(tb, "Cab", new Vector3(0, 1.75f, 2.0f), new Vector3(2.0f, 1.65f, 1.5f), TruckWhite());
        Box(tb, "Windscreen", new Vector3(0, 2.05f, 2.76f), new Vector3(1.7f, .75f, .03f), DarkGlass());
        foreach (int i in new[] { -1, 1 }) Box(tb, "Side window", new Vector3(i * 1.01f, 2.05f, 2.2f), new Vector3(.02f, .6f, .8f), DarkGlass());
        Box(tb, "Grille", new Vector3(0, 1.15f, 2.77f), new Vector3(1.2f, .45f, .04f), Galvanized());
        Box(tb, "Bumper", new Vector3(0, .72f, 2.8f), new Vector3(2.05f, .22f, .15f), Galvanized());
        foreach (int i in new[] { -1, 1 }) Box(tb, "Headlight", new Vector3(i * .75f, 1.05f, 2.78f), new Vector3(.3f, .16f, .03f), WindowGlow());
        Box(tb, "Cab stripe", new Vector3(0, 1.4f, 2.0f), new Vector3(2.02f, .12f, 1.52f), Gold());
        Box(tb, "Cab roof light", new Vector3(0, 2.62f, 2.0f), new Vector3(.8f, .08f, .2f), AmberLamp());
        foreach (int i in new[] { -1, 1 }) Box(tb, "Fender", new Vector3(i * .95f, 1.0f, -1.6f), new Vector3(.3f, .08f, 2.6f), Navy());
        Box(tb, "Drum cradle", new Vector3(0, 1.3f, -.9f), new Vector3(1.2f, .6f, .2f), Navy());
        Box(tb, "Drum cradle", new Vector3(0, 1.3f, -2.9f), new Vector3(1.2f, .9f, .2f), Navy());
        Box(tb, "Water tank", new Vector3(.75f, 1.35f, .7f), new Vector3(.4f, .5f, .9f), Galvanized());
        Box(tb, "Ladder", new Vector3(.4f, 1.9f, -3.2f), new Vector3(.4f, 1.8f, .05f), Galvanized());
        Bake(tb, "MixerBody");
        var drum = Node(truck, "Anim drum", new Vector3(0, 2.05f, -1.7f), Quaternion.Euler(-12, 0, 0));
        Box(drum, "Drum shell", Vector3.zero, new Vector3(1.75f, 1.6f, 1.75f), TruckWhite(), PrimitiveType.Cylinder).transform.localRotation = Quaternion.Euler(90, 0, 0);
        Box(drum, "Drum cone", new Vector3(0, 0, -1.8f), new Vector3(1.2f, .4f, 1.2f), TruckWhite(), PrimitiveType.Cylinder).transform.localRotation = Quaternion.Euler(90, 0, 0);
        for (int i = 0; i < 5; i++)
        {
            var band = Box(drum, "Drum band", new Vector3(0, 0, -1.3f + i * .65f), new Vector3(1.8f, .06f, 1.8f), i % 2 == 0 ? Navy() : Gold(), PrimitiveType.Cylinder);
            band.transform.localRotation = Quaternion.Euler(90 + 14, 0, 0);
        }
        Bake(drum, "MixerDrum");
        var chute = Node(truck, "Anim chute", new Vector3(0, 1.3f, -3.35f));
        Box(chute, "Chute", new Vector3(0, -.05f, -.7f), new Vector3(.45f, .08f, 1.4f), Galvanized());
        foreach (int i in new[] { -1, 1 }) Box(chute, "Chute side", new Vector3(i * .22f, .05f, -.7f), new Vector3(.04f, .18f, 1.4f), Galvanized());
        Bake(chute, "MixerChute");
        foreach (float z in new[] { 2.0f, -1.2f, -2.4f }) foreach (int i in new[] { -1, 1 })
        {
            var wheel = Node(truck, "Anim wheel", new Vector3(i * .88f, .5f, z));
            Box(wheel, "Tyre", Vector3.zero, new Vector3(1f, .17f, 1f), Rubber(), PrimitiveType.Cylinder).transform.localRotation = Quaternion.Euler(0, 0, 90);
            Box(wheel, "Hub", new Vector3(i * .18f, 0, 0), new Vector3(.5f, .02f, .5f), Galvanized(), PrimitiveType.Cylinder).transform.localRotation = Quaternion.Euler(0, 0, 90);
        }

        // Hoarding panel 2.4 m wide along local z, printed side facing +x.
        var panel = Node(kit, "Hoarding panel", Vector3.zero);
        Box(panel, "Board", new Vector3(0, 1.1f, 0), new Vector3(.06f, 1.9f, 2.36f), Navy());
        var print = GameObject.CreatePrimitive(PrimitiveType.Quad); UnityEngine.Object.DestroyImmediate(print.GetComponent<Collider>());
        print.name = "Print"; print.transform.SetParent(panel, false);
        print.transform.localPosition = new Vector3(.035f, 1.1f, 0); print.transform.localRotation = Quaternion.Euler(0, -90, 0);
        print.transform.localScale = new Vector3(2.3f, 1.15f, 1); print.GetComponent<Renderer>().sharedMaterial = Printed("MS_HoardingPrint", "MS_HoardingPrint");
        Box(panel, "Post", new Vector3(0, 1.05f, -1.2f), new Vector3(.08f, 2.1f, .08f), Galvanized());
        Box(panel, "Foot", new Vector3(0, .09f, -1.2f), new Vector3(.7f, .18f, .3f), Concrete());
        Box(panel, "Top rail", new Vector3(0, 2.07f, 0), new Vector3(.08f, .06f, 2.4f), Gold());
        Bake(panel, "HoardingPanel");

        var gate = Node(kit, "Gate leaf", Vector3.zero);
        Box(gate, "Gate frame", new Vector3(0, 1.05f, .9f), new Vector3(.06f, 1.9f, 1.8f), Galvanized());
        Box(gate, "Gate mesh", new Vector3(0, 1.05f, .9f), new Vector3(.03f, 1.75f, 1.65f), Navy());
        Box(gate, "Gate stripe", new Vector3(0, 1.4f, .9f), new Vector3(.05f, .25f, 1.7f), Hazard());
        Bake(gate, "GateLeaf");

        var hat = Node(kit, "Hard hat", Vector3.zero);
        var hatMesh = HardHatMesh();
        var hatGo = new GameObject("Hat"); hatGo.transform.SetParent(hat, false);
        hatGo.AddComponent<MeshFilter>().sharedMesh = hatMesh;
        hatGo.AddComponent<MeshRenderer>().sharedMaterials = new[] { HatYellow(), Navy() };

        var bundle = Node(kit, "Brick bundle", Vector3.zero);
        Box(bundle, "Bundle", Vector3.zero, new Vector3(.55f, .32f, .38f), Brick());
        Box(bundle, "Strap", Vector3.zero, new Vector3(.57f, .34f, .04f), Navy());
        Bake(bundle, "BrickBundle");

        var stack = Node(kit, "Material stack", Vector3.zero);
        PalletStack(stack, Vector3.zero, 0, 4, true, 21);
        Box(stack, "Sand heap", new Vector3(.6f, .3f, -1.6f), new Vector3(2.4f, .8f, 1.8f), Mat("MS_Sand", "D8C08A", .05f), PrimitiveType.Sphere);
        foreach (int i in new[] { 0, 1, 2, 3 }) Box(stack, "Steel beam", new Vector3(3.0f, .1f + i * .15f, .4f + (i % 2) * .1f), new Vector3(.22f, .14f, 3.2f), Navy());
        Bake(stack, "MaterialStack");

        foreach (var r in kit.GetComponentsInChildren<Renderer>(true)) r.shadowCastingMode = r.bounds.size.magnitude > 1.5f ? ShadowCastingMode.On : ShadowCastingMode.Off;
        kit.gameObject.SetActive(false);

        var site = show.GetComponent<CheckoutConstructionSite>();
        if (!site) site = show.gameObject.AddComponent<CheckoutConstructionSite>();
        site.kit = kit;
        site.galvanized = Galvanized(); site.planks = Planks(); site.concrete = Concrete(); site.hazard = Hazard();
        site.navyPaint = Navy(); site.goldTrim = Gold(); site.cable = Cable(); site.redLamp = RedLamp(); site.rebar = Mat("MS_Rebar", "6B4A36", .3f);
        site.boardFont = font;
        site.crew = new[] { Crew("Worker_ConstructionA"), Crew("Worker_ConstructionB") };
        EditorUtility.SetDirty(site);
        Debug.Log("CONSTRUCTION_KIT built parts=" + kit.childCount);
    }

    // Hard hat: a lathed shell with a brim and a raised ridge; sub-mesh 1 is the navy band.
    static Mesh HardHatMesh()
    {
        Folders();
        var verts = new List<Vector3>(); var tris = new List<int>(); var band = new List<int>();
        // Profile (radius, height) from brim edge to crown.
        var profile = new[] { new Vector2(.60f, 0), new Vector2(.60f, .03f), new Vector2(.45f, .05f), new Vector2(.44f, .12f), new Vector2(.43f, .22f), new Vector2(.40f, .34f), new Vector2(.32f, .45f), new Vector2(.2f, .52f), new Vector2(.0f, .55f) };
        int seg = 24;
        for (int p = 0; p < profile.Length; p++)
            for (int i = 0; i <= seg; i++)
            {
                float a = i * Mathf.PI * 2 / seg;
                float front = Mathf.Max(0, Mathf.Cos(a)); // longer peak at the front (+z)
                float r = profile[p].x * (p < 2 ? 1 + .25f * front : 1);
                verts.Add(new Vector3(Mathf.Sin(a) * r, profile[p].y, Mathf.Cos(a) * r));
            }
        for (int p = 0; p < profile.Length - 1; p++)
            for (int i = 0; i < seg; i++)
            {
                int a = p * (seg + 1) + i, b = a + seg + 1;
                var list = p == 3 ? band : tris;
                list.AddRange(new[] { a, a + 1, b, b, a + 1, b + 1 });
            }
        // Underside of the brim.
        int c = verts.Count; verts.Add(new Vector3(0, .01f, 0));
        for (int i = 0; i < seg; i++) tris.AddRange(new[] { c, (i + 1), i });
        var mesh = new Mesh { name = "HardHat" };
        mesh.SetVertices(verts); mesh.subMeshCount = 2; mesh.SetTriangles(tris, 0); mesh.SetTriangles(band, 1);
        mesh.RecalculateNormals(); mesh.RecalculateBounds();
        string path = MeshFolder + "HardHat.asset";
        var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (existing) { existing.Clear(); EditorUtility.CopySerialized(mesh, existing); return existing; }
        AssetDatabase.CreateAsset(mesh, path);
        return mesh;
    }
}
