using System;
using System.Collections.Generic;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

// "Interior Kit": every piece of furniture the player can place inside the market, modelled here from
// scratch in the shop's look (navy + brushed gold + cream enamel, light oak, white tiles, marble tops).
// Meshes carry metric UVs so the textures travel with a piece when it is moved; packaged goods come from
// one product atlas (Assets/Art/Interior/Textures/IK_Products). Static parts are merged per template, the
// stock on display is merged per fill group ("Anim Fill n") so shelves can empty and refill.
public static partial class CheckoutMarketStagesBuilder
{
    const string KitFolder = "Assets/Art/Interior/";
    const string KitRootName = "Interior Kit";
    static readonly List<Mesh> scratch = new List<Mesh>();
    static readonly Dictionary<string, Mesh> productMeshes = new Dictionary<string, Mesh>();

    [MenuItem("Supermarket/Build interior kit (furniture + decor)")]
    public static void BuildInteriorKitMenu()
    {
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation || !simulation.world) throw new InvalidOperationException("Open the Supermarket scene first.");
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        materials.Clear(); productMeshes.Clear(); persisted.Clear(); sphereCache = null;
        font = Resources.Load<Font>("MarketBold") ?? Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        BuildInteriorKit(simulation.world);
        EditorSceneManager.MarkSceneDirty(simulation.world.gameObject.scene);
        EditorSceneManager.SaveScene(simulation.world.gameObject.scene);
        AssetDatabase.SaveAssets();
    }

    public static void BuildInteriorKit(Transform world)
    {
        foreach (var f in new[] { "Interior", "Interior/Meshes", "Interior/Materials" })
        {
            var parts = f.Split('/');
            string parent = "Assets/Art" + (parts.Length > 1 ? "/" + parts[0] : ""), leaf = parts[parts.Length - 1];
            if (!AssetDatabase.IsValidFolder(parent + "/" + leaf)) AssetDatabase.CreateFolder(parent, leaf);
        }
        var old = world.Find(KitRootName); if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var kit = new GameObject(KitRootName).transform;
        kit.SetParent(world, false); kit.rotation = Quaternion.identity; kit.position = new Vector3(0, -40, 0);
        int slot = 0;
        Transform Next(string id) { var t = new GameObject(id).transform; t.SetParent(kit, false); t.localPosition = new Vector3((slot % 8) * 4f, 0, (slot / 8) * 4f); slot++; return t; }

        foreach (var v in new[] { "grocery", "snacks", "cleaning" }) Gondola(Next("shelf-" + v), v);
        Cooler(Next("shelf-cooler"));
        Dairy(Next("shelf-dairy"));
        Produce(Next("shelf-produce"));
        Freezer(Next("shelf-freezer"));
        BakeryRack(Next("shelf-bakery"));
        foreach (var s in new[] { "padaria", "queijaria", "acougue", "peixaria", "bebidas", "sorvetes", "adega" }) SectorCounter(Next("sector-" + s), s);
        CheckoutCounter(Next("checkout"));
        Kiosk(Next("kiosk"));
        Decor(Next("basket-stack"), "basket-stack"); Decor(Next("plant-small"), "plant-small"); Decor(Next("balloons"), "balloons");
        Decor(Next("floor-lamp"), "floor-lamp"); Decor(Next("bench"), "bench"); Decor(Next("cart-corral"), "cart-corral");
        Decor(Next("plant-palm"), "plant-palm"); Decor(Next("promo-stand"), "promo-stand"); Decor(Next("water-cooler"), "water-cooler");
        Decor(Next("gumball"), "gumball"); Decor(Next("flower-stand"), "flower-stand"); Decor(Next("watermelon-pile"), "watermelon-pile");
        Decor(Next("claw-machine"), "claw-machine"); Decor(Next("atm"), "atm"); Decor(Next("digital-totem"), "digital-totem");
        foreach (var id in OutsideDecor) Decor(Next(id), id);
        if (skipNode) UnityEngine.Object.DestroyImmediate(skipNode);

        foreach (var m in scratch) if (m && !AssetDatabase.Contains(m)) UnityEngine.Object.DestroyImmediate(m);
        scratch.Clear();
        kit.gameObject.SetActive(false);
    }

    // ------------------------------------------------------------------ materials
    static Material KMat(string name, string hex, float gloss, float metal = 0, string texture = null, Vector2? tile = null, bool normal = true, string emission = null)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = KitFolder + "Materials/" + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("Standard");
        material.color = MarketSimulation.C(hex);
        material.SetFloat("_Glossiness", gloss); material.SetFloat("_Metallic", metal);
        material.mainTexture = null; material.SetTexture("_BumpMap", null); material.DisableKeyword("_NORMALMAP");
        if (texture != null)
        {
            string albedo = KitFolder + "Textures/" + texture + "_albedo.png", bump = KitFolder + "Textures/" + texture + "_normal.png";
            KitTexture(albedo, false);
            material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(albedo);
            material.mainTextureScale = tile ?? Vector2.one;
            if (normal && AssetDatabase.LoadAssetAtPath<Texture2D>(bump))
            {
                KitTexture(bump, true);
                material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(bump)); material.SetFloat("_BumpScale", .8f); material.EnableKeyword("_NORMALMAP");
            }
        }
        if (emission != null)
        {
            material.EnableKeyword("_EMISSION");
            material.SetColor("_EmissionColor", MarketSimulation.C(emission) * 1.4f);
            if (texture != null && emission == "FFFFFF") material.SetTexture("_EmissionMap", material.mainTexture);
            material.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
        }
        else material.DisableKeyword("_EMISSION");
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static void KitTexture(string path, bool normal)
    {
        var importer = AssetImporter.GetAtPath(path) as TextureImporter;
        if (!importer) throw new InvalidOperationException("Missing texture " + path);
        var type = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
        // The product label atlas (8x8 labels) keeps its full 2048 so the printed names stay readable.
        int size = path.Contains("IK_Labels") ? 2048 : 1024;
        if (importer.textureType != type || importer.sRGBTexture == normal || importer.anisoLevel != 4 || importer.maxTextureSize != size)
        { importer.textureType = type; importer.sRGBTexture = !normal; importer.anisoLevel = 4; importer.maxTextureSize = size; importer.SaveAndReimport(); }
    }

    // ------------------------------------------------------------------ Blender models (scripts/blender/build_interior_kit.py)
    // Instantiates Assets/Art/Interior/Models/<template>.fbx under the template and maps its material names to the
    // game's painted look. Returns false (primitive fallback) when the model has not been exported yet.
    static bool KitModel(Transform t)
    {
        string path = KitFolder + "Models/" + t.name + ".fbx";
        var importer = AssetImporter.GetAtPath(path) as ModelImporter;
        if (!importer) { skipBody = false; return false; }
        if (importer.importNormals != ModelImporterNormals.Import || importer.addCollider || importer.importAnimation || importer.materialLocation != ModelImporterMaterialLocation.InPrefab || importer.bakeAxisConversion)
        {
            importer.importNormals = ModelImporterNormals.Import; importer.addCollider = false; importer.importAnimation = false;
            importer.materialLocation = ModelImporterMaterialLocation.InPrefab; importer.bakeAxisConversion = false; importer.SaveAndReimport();
        }
        var source = AssetDatabase.LoadAssetAtPath<GameObject>(path);
        if (!source) { skipBody = false; return false; }
        var model = UnityEngine.Object.Instantiate(source, t, false);
        // Keep the imported root rotation: a single-object FBX carries Blender's axis conversion on its root.
        model.name = "Model"; model.transform.localPosition = Vector3.zero;
        foreach (var r in model.GetComponentsInChildren<Renderer>(true))
        {
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++) mats[i] = KitRemap(mats[i]);
            r.sharedMaterials = mats;
        }
        skipBody = true;
        return true;
    }

    static readonly Dictionary<string, Vector2> KitTiling = new Dictionary<string, Vector2>
    {
        { "IK_Pegboard", Vector2.one * 1.2f }, { "IK_WoodLight", Vector2.one * .8f }, { "IK_Tile", Vector2.one * 1.6f }, { "IK_Marble", Vector2.one * .7f },
        { "IK_Steel", Vector2.one }, { "IK_Crate", Vector2.one * 2.2f }, { "IK_Belt", Vector2.one * 1.6f }, { "IK_PriceRail", new Vector2(1, 20) },
    };

    static Material KitRemap(Material source)
    {
        string n = source ? source.name : "C_FFFFFF";
        int dot = n.IndexOf('.'); if (dot > 0) n = n.Substring(0, dot);
        if (n.StartsWith("C_") && n.Length >= 8) return Painted("IK_P_" + n.Substring(2, 6), n.Substring(2, 6), null, Vector2.one);
        if (n.StartsWith("S_") && n.Length >= 8) return Painted("IK_PS_" + n.Substring(2, 6), n.Substring(2, 6), "IK_Stripes", new Vector2(1.25f, 1));
        if (n.StartsWith("E_") && n.Length >= 8) return KGlow(n.Substring(2, 6));
        if (n == "G_Glass") return KGlass();
        if (n.StartsWith("T_"))
        {
            var tex = n.Substring(2);
            if (tex == "IK_Screen") return KScreen();
            return Painted("IK_PT_" + tex.Substring(3), "FFFFFF", tex, KitTiling.TryGetValue(tex, out var tile) ? tile : Vector2.one);
        }
        return source;
    }

    // The game's "MarketDay/Soft Painted" shader: soft light ramp and a warm ink contour, like the characters.
    static Material Painted(string name, string hex, string texture, Vector2 tiling, float outline = .8f)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = KitFolder + "Materials/" + name + ".mat";
        var shader = Shader.Find("MarketDay/Soft Painted");
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(shader); AssetDatabase.CreateAsset(material, path); }
        material.shader = shader;
        material.color = MarketSimulation.C(hex);
        material.mainTexture = null;
        if (texture != null)
        {
            string albedo = KitFolder + "Textures/" + texture + "_albedo.png";
            KitTexture(albedo, false);
            material.mainTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(albedo);
            material.mainTextureScale = tiling;
        }
        material.SetFloat("_Outline", outline);
        material.SetColor("_OutlineColor", new Color(.22f, .115f, .055f, 1));
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static Material KNavy() => KMat("IK_Navy", "1D2B4F", .45f);
    static Material KGold() => KMat("IK_Gold", "D9A937", .72f, .65f);
    static Material KCream() => KMat("IK_Cream", "F4EFE4", .55f);
    static Material KPeg() => KMat("IK_Pegboard", "FFFFFF", .5f, 0, "IK_Pegboard", Vector2.one * 1.2f);
    static Material KWood() => KMat("IK_WoodLight", "FFFFFF", .3f, 0, "IK_WoodLight", Vector2.one * .8f);
    static Material KTile() => KMat("IK_Tile", "FFFFFF", .8f, 0, "IK_Tile", Vector2.one * 1.6f);
    static Material KMarble() => KMat("IK_Marble", "FFFFFF", .85f, 0, "IK_Marble", Vector2.one * .7f);
    static Material KSteel() => KMat("IK_Steel", "FFFFFF", .62f, .6f, "IK_Steel", Vector2.one);
    static Material KCrate() => KMat("IK_Crate", "FFFFFF", .2f, 0, "IK_Crate", Vector2.one * 2.2f);
    static Material KBelt() => KMat("IK_Belt", "FFFFFF", .35f, 0, "IK_Belt", Vector2.one * 1.6f);
    static Material KRail() => KMat("IK_PriceRail", "FFFFFF", .4f, 0, "IK_PriceRail", new Vector2(1, 20), false);
    static Material KProducts() => Painted("IK_PT_Products", "FFFFFF", "IK_Products", Vector2.one, .35f);
    static Material KScreen() => KMat("IK_Screen", "FFFFFF", .9f, 0, "IK_Screen", new Vector2(1, 1f / 3), false, "FFFFFF");
    static Material KPromo() => KMat("IK_PromoCard", "FFFFFF", .3f, 0, "IK_PromoCard", Vector2.one, false);
    static Material KStripe(string name, string hex) => KMat("IK_Awning_" + name, hex, .3f, 0, "IK_Stripes", new Vector2(1.25f, 1), false);
    static Material KChrome() => KMat("IK_Chrome", "DCE1E6", .88f, .9f);
    static Material KBlack() => KMat("IK_Black", "24262B", .35f);
    static Material KWhite() => KMat("IK_White", "FBFAF6", .6f);
    static Material KLed() => KMat("IK_Led", "FFFFFF", .5f, 0, null, null, true, "FFF6E0");
    static Material KColor(string hex, float gloss = .45f) => KMat("IK_C_" + hex, hex, gloss);
    static Material KGlow(string hex) => KMat("IK_Glow_" + hex, hex, .6f, 0, null, null, true, hex);
    static Material KGlass() => Transparent("IK_Glass", new Color(.78f, .9f, .97f, .22f));
    static Material KIce() => KMat("IK_Ice", "E8F4FA", .85f);
    static Material KLeaf() => KMat("IK_Leaf", "4F9B3C", .35f);
    static Material KLeafDark() => KMat("IK_LeafDark", "2F6F2C", .3f);
    static Material KTerracotta() => KMat("IK_Terracotta", "C4673D", .25f);

    // ------------------------------------------------------------------ meshes
    // Box with chamfered edges (flat shaded) and UVs in metres, projected from the dominant axis.
    static Mesh ChamferMesh(Vector3 size, float bevel)
    {
        var h = size * .5f; float b = Mathf.Min(bevel, h.x * .45f, h.y * .45f, h.z * .45f);
        var verts = new List<Vector3>(); var norms = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
        Vector3 P(int axis, float sx, float sy, float sz)
        {
            var v = new Vector3(sx * (h.x - (axis == 0 ? 0 : b)), sy * (h.y - (axis == 1 ? 0 : b)), sz * (h.z - (axis == 2 ? 0 : b)));
            return v;
        }
        void Poly(params Vector3[] p)
        {
            var n = Vector3.Cross(p[1] - p[0], p[2] - p[0]);
            if (n.sqrMagnitude < 1e-12f) return;
            n.Normalize();
            var centre = Vector3.zero; foreach (var q in p) centre += q; centre /= p.Length;
            bool flip = Vector3.Dot(n, centre) < 0;
            if (flip) { Array.Reverse(p); n = -n; }
            int start = verts.Count;
            var a = new Vector3(Mathf.Abs(n.x), Mathf.Abs(n.y), Mathf.Abs(n.z));
            foreach (var q in p)
            {
                verts.Add(q); norms.Add(n);
                uvs.Add(a.x >= a.y && a.x >= a.z ? new Vector2(q.z * Mathf.Sign(n.x), q.y) : a.y >= a.z ? new Vector2(q.x, q.z * Mathf.Sign(n.y)) : new Vector2(-q.x * Mathf.Sign(n.z), q.y));
            }
            for (int i = 1; i < p.Length - 1; i++) { tris.Add(start); tris.Add(start + i); tris.Add(start + i + 1); }
        }
        // Main faces.
        foreach (var s in new[] { -1f, 1f })
        {
            Poly(P(0, s, -1, -1), P(0, s, 1, -1), P(0, s, 1, 1), P(0, s, -1, 1));
            Poly(P(1, -1, s, -1), P(1, 1, s, -1), P(1, 1, s, 1), P(1, -1, s, 1));
            Poly(P(2, -1, -1, s), P(2, 1, -1, s), P(2, 1, 1, s), P(2, -1, 1, s));
        }
        if (b > 0.0005f)
        {
            foreach (var sx in new[] { -1f, 1f }) foreach (var sy in new[] { -1f, 1f })
                {
                    Poly(P(0, sx, sy, -1), P(1, sx, sy, -1), P(1, sx, sy, 1), P(0, sx, sy, 1));      // edges along z
                    Poly(P(0, sx, -1, sy), P(2, sx, -1, sy), P(2, sx, 1, sy), P(0, sx, 1, sy));      // edges along y
                    Poly(P(1, -1, sx, sy), P(2, -1, sx, sy), P(2, 1, sx, sy), P(1, 1, sx, sy));      // edges along x
                    foreach (var sz in new[] { -1f, 1f }) Poly(P(0, sx, sy, sz), P(1, sx, sy, sz), P(2, sx, sy, sz));
                }
        }
        var mesh = new Mesh { name = "Chamfer" };
        mesh.SetVertices(verts); mesh.SetNormals(norms); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
        mesh.RecalculateBounds(); mesh.RecalculateTangents();
        scratch.Add(mesh);
        return mesh;
    }

    static GameObject MeshNode(Transform parent, string name, Mesh mesh, Vector3 local, Material material, Quaternion? rotation = null, Vector3? scale = null)
    {
        if (skipBody && !productMode) return Skip();
        var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
        go.transform.SetParent(parent, false); go.transform.localPosition = local; go.transform.localRotation = rotation ?? Quaternion.identity;
        go.transform.localScale = scale ?? Vector3.one;
        go.GetComponent<MeshFilter>().sharedMesh = mesh; go.GetComponent<MeshRenderer>().sharedMaterial = material;
        return go;
    }

    // Chamfered box centred at `local`.
    static GameObject KBox(Transform parent, string name, Vector3 local, Vector3 size, Material material, float bevel = .012f, float yaw = 0, float pitch = 0) =>
        skipBody ? Skip() : MeshNode(parent, name, ChamferMesh(size, bevel), local, material, Quaternion.Euler(pitch, yaw, 0));

    // With a Blender model the template keeps only its stock (products); the primitive body is skipped.
    static bool skipBody, productMode;
    static GameObject skipNode;
    static GameObject Skip() { if (!skipNode) skipNode = new GameObject("IK skipped part"); return skipNode; }
    static void KLetters(Transform parent, string value, Vector3 at, float size, bool flat = false, Color? face = null, Color? side = null) { if (!skipBody) Letters3D(parent, value, at, size, flat, face, side); }

    // Surface of revolution: profile points (radius, height) from bottom to top. `cell` maps UVs into an
    // atlas cell (x, y = column, row from the top of an 8x8 atlas); otherwise UVs are metric.
    static Mesh Lathe(Vector2[] profile, int segments, Vector2Int? cell = null, bool capTop = true, bool smooth = true)
    {
        var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
        float total = 0; var along = new float[profile.Length];
        for (int i = 1; i < profile.Length; i++) { total += Vector2.Distance(profile[i], profile[i - 1]); along[i] = total; }
        Vector2 Map(float u, float v)
        {
            if (cell == null) return new Vector2(u * 2 * Mathf.PI * profile.Max(p => p.x), v * total);
            var c = cell.Value; float s = 1f / 8;
            return new Vector2((c.x + .04f + u * .92f) * s, 1 - (c.y + 1) * s + (.04f + v * .92f) * s);
        }
        for (int i = 0; i < profile.Length; i++)
            for (int k = 0; k <= segments; k++)
            {
                float a = k * Mathf.PI * 2 / segments;
                verts.Add(new Vector3(Mathf.Cos(a) * profile[i].x, profile[i].y, Mathf.Sin(a) * profile[i].x));
                uvs.Add(Map(k / (float)segments, total > 0 ? along[i] / total : 0));
            }
        int row = segments + 1;
        for (int i = 0; i < profile.Length - 1; i++)
            for (int k = 0; k < segments; k++)
            {
                int a = i * row + k, b = a + 1, c = a + row, d = c + 1;
                tris.AddRange(new[] { a, c, b, b, c, d });
            }
        if (capTop && profile[profile.Length - 1].x > .001f)
        {
            int centre = verts.Count; var top = profile[profile.Length - 1];
            verts.Add(new Vector3(0, top.y, 0)); uvs.Add(Map(.5f, 1));
            int ring = (profile.Length - 1) * row;
            for (int k = 0; k < segments; k++) tris.AddRange(new[] { centre, ring + k + 1, ring + k });
        }
        if (profile[0].x > .001f)
        {
            int centre = verts.Count; verts.Add(new Vector3(0, profile[0].y, 0)); uvs.Add(Map(.5f, 0));
            for (int k = 0; k < segments; k++) tris.AddRange(new[] { centre, k, k + 1 });
        }
        var mesh = new Mesh { name = "Lathe" };
        mesh.SetVertices(verts); mesh.SetUVs(0, uvs); mesh.SetTriangles(tris, 0);
        mesh.RecalculateNormals(); mesh.RecalculateBounds(); mesh.RecalculateTangents();
        if (!smooth) { }
        scratch.Add(mesh);
        return mesh;
    }

    static GameObject KLathe(Transform parent, string name, Vector3 local, Material material, int segments, params Vector2[] profile) =>
        MeshNode(parent, name, Lathe(profile, segments), local, material);

    static GameObject KSphere(Transform parent, string name, Vector3 local, Vector3 size, Material material) =>
        MeshNode(parent, name, Sphere(10, 7, null), local, material, null, size);

    static Mesh sphereCache;
    static Mesh Sphere(int seg, int rings, Vector2Int? cell)
    {
        if (cell == null && sphereCache) return sphereCache;
        var profile = new Vector2[rings + 1];
        for (int i = 0; i <= rings; i++) { float a = -Mathf.PI / 2 + Mathf.PI * i / rings; profile[i] = new Vector2(Mathf.Cos(a) * .5f, Mathf.Sin(a) * .5f); }
        profile[0].x = 0; profile[rings].x = 0;
        var m = Lathe(profile, seg, cell, false);
        if (cell == null) sphereCache = m;
        return m;
    }

    // ------------------------------------------------------------------ packaged goods (atlas cells)
    static Mesh ProductBox(Vector3 size, Vector2Int cell, float bevel = .004f)
    {
        string key = "box" + size + cell + bevel;
        if (productMeshes.TryGetValue(key, out var cached)) return cached;
        var mesh = ChamferMesh(size, bevel);
        var v = mesh.vertices; var n = mesh.normals; var uv = new Vector2[v.Length]; var h = size * .5f; float s = 1f / 8;
        for (int i = 0; i < v.Length; i++)
        {
            var a = new Vector3(Mathf.Abs(n[i].x), Mathf.Abs(n[i].y), Mathf.Abs(n[i].z));
            float u, w;
            if (a.z >= a.x && a.z >= a.y) { u = Mathf.InverseLerp(-h.x, h.x, v[i].x * -Mathf.Sign(n[i].z)); w = Mathf.InverseLerp(-h.y, h.y, v[i].y); }
            else if (a.x >= a.y) { u = Mathf.InverseLerp(-h.z, h.z, v[i].z); w = Mathf.InverseLerp(-h.y, h.y, v[i].y); u = .1f + u * .2f; }
            else { u = Mathf.InverseLerp(-h.x, h.x, v[i].x); w = .9f; }
            uv[i] = new Vector2((cell.x + .03f + u * .94f) * s, 1 - (cell.y + 1) * s + (.03f + w * .94f) * s);
        }
        mesh.uv = uv;
        productMeshes[key] = mesh;
        return mesh;
    }

    static Mesh ProductLathe(string kind, float r, float height, Vector2Int cell)
    {
        string key = kind + r + height + cell;
        if (productMeshes.TryGetValue(key, out var cached)) return cached;
        Vector2[] p;
        switch (kind)
        {
            case "bottle": p = new[] { new Vector2(r * .85f, 0), new Vector2(r, height * .04f), new Vector2(r, height * .58f), new Vector2(r * .78f, height * .7f), new Vector2(r * .34f, height * .82f), new Vector2(r * .34f, height * .96f), new Vector2(r * .4f, height) }; break;
            case "wine": p = new[] { new Vector2(r * .9f, 0), new Vector2(r, height * .03f), new Vector2(r, height * .6f), new Vector2(r * .45f, height * .74f), new Vector2(r * .28f, height * .8f), new Vector2(r * .28f, height) }; break;
            case "jug": p = new[] { new Vector2(r * .9f, 0), new Vector2(r, height * .05f), new Vector2(r, height * .72f), new Vector2(r * .55f, height * .86f), new Vector2(r * .3f, height * .9f), new Vector2(r * .32f, height) }; break;
            case "tub": p = new[] { new Vector2(r * .82f, 0), new Vector2(r, height * .9f), new Vector2(r * 1.04f, height) }; break;
            case "wheel": p = new[] { new Vector2(r * .9f, 0), new Vector2(r, height * .15f), new Vector2(r, height * .85f), new Vector2(r * .9f, height) }; break;
            default: p = new[] { new Vector2(r * .92f, 0), new Vector2(r, height * .06f), new Vector2(r, height * .94f), new Vector2(r * .92f, height) }; break; // can
        }
        var mesh = Lathe(p, 8, cell);
        productMeshes[key] = mesh;
        return mesh;
    }

    static Mesh Fruit(Vector2Int cell)
    {
        string key = "fruit" + cell;
        if (productMeshes.TryGetValue(key, out var cached)) return cached;
        var mesh = Sphere(7, 5, cell);
        productMeshes[key] = mesh;
        return mesh;
    }

    static readonly System.Random dice = new System.Random(11);
    static float Jitter(float amount) => ((float)dice.NextDouble() * 2 - 1) * amount;

    // A row of the same product along x, `deep` rows back, from `left` to `right` (item centres).
    static void Row(Transform group, Mesh mesh, Vector3 size, float left, float right, float y, float z, int deep = 2, float gap = .012f, float depthGap = .01f, bool stand = true, float yawJitter = 4)
    {
        var material = KProducts(); productMode = true;
        int count = Mathf.Max(1, Mathf.FloorToInt((right - left + size.x) / (size.x + gap)));
        float span = (count - 1) * (size.x + gap), start = (left + right) * .5f - span * .5f;
        for (int d = 0; d < deep; d++)
            for (int i = 0; i < count; i++)
            {
                var at = new Vector3(start + i * (size.x + gap) + Jitter(.004f), y + (stand ? size.y * .5f : 0), z + d * (size.z + depthGap));
                MeshNode(group, "Item", mesh, at, material, Quaternion.Euler(0, Jitter(yawJitter), 0));
            }
        productMode = false;
    }

    static void LatheRow(Transform group, Mesh mesh, float r, float left, float right, float y, float z, int deep = 2, float gap = .01f)
    {
        var material = KProducts(); productMode = true;
        int count = Mathf.Max(1, Mathf.FloorToInt((right - left + 2 * r) / (2 * r + gap)));
        float span = (count - 1) * (2 * r + gap), start = (left + right) * .5f - span * .5f;
        for (int d = 0; d < deep; d++)
            for (int i = 0; i < count; i++)
                MeshNode(group, "Item", mesh, new Vector3(start + i * (2 * r + gap), y, z + d * (2 * r + .008f)), material, Quaternion.Euler(0, 90 + Jitter(25), 0));
        productMode = false;
    }

    // A heap of fruit on a (possibly tilted) bed: w x d area centred at `at`.
    static void Heap(Transform group, Vector2Int cell, float r, Vector3 at, float w, float d, float tilt, int layers = 2)
    {
        var mesh = Fruit(cell); var material = KProducts(); productMode = true;
        for (int l = 0; l < layers; l++)
        {
            float rr = r * 2.05f; int nx = Mathf.Max(1, Mathf.FloorToInt((w - l * rr) / rr)), nz = Mathf.Max(1, Mathf.FloorToInt((d - l * rr) / rr));
            for (int x = 0; x < nx; x++)
                for (int z = 0; z < nz; z++)
                {
                    float px = -((nx - 1) * rr) * .5f + x * rr + Jitter(r * .15f), pz = -((nz - 1) * rr) * .5f + z * rr + Jitter(r * .15f);
                    var p = at + new Vector3(px, r + l * r * 1.5f + pz * Mathf.Tan(tilt * Mathf.Deg2Rad), pz);
                    MeshNode(group, "Fruit", mesh, p, material, Quaternion.Euler(Jitter(30), Jitter(180), Jitter(30)), Vector3.one * r * 2 * (1 + Jitter(.08f)));
                }
        }
        productMode = false;
    }

    static Transform Group(Transform parent, string name) { var t = new GameObject(name).transform; t.SetParent(parent, false); return t; }

    // Bakes the static body (everything outside "Anim" nodes) and every fill group; returns the groups in order.
    static GameObject[] Finish(Transform t, CheckoutInteriorPiece piece, List<Transform> fills)
    {
        skipBody = false;
        Bake(t, "IK_" + t.name, KitFolder + "Meshes/");
        var result = new List<GameObject>();
        for (int i = 0; i < fills.Count; i++)
        {
            if (fills[i].childCount == 0) continue;
            var baked = Bake(fills[i], "IK_" + t.name + "_fill" + i, KitFolder + "Meshes/");
            if (baked) { baked.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off; result.Add(fills[i].gameObject); }
        }
        piece.fill = result.ToArray();
        foreach (var r in t.GetComponentsInChildren<Renderer>(true)) if (r.GetComponent<TextMesh>()) r.shadowCastingMode = ShadowCastingMode.Off;
        PersistLooseMeshes(t);
        return piece.fill;
    }

    // Animated parts stay separate objects: their generated meshes must be saved too, or they vanish when
    // the scratch meshes are cleaned up.
    static readonly Dictionary<Mesh, Mesh> persisted = new Dictionary<Mesh, Mesh>();
    static void PersistLooseMeshes(Transform t)
    {
        foreach (var f in t.GetComponentsInChildren<MeshFilter>(true))
        {
            var m = f.sharedMesh; if (!m || EditorUtility.IsPersistent(m)) continue;
            if (!persisted.TryGetValue(m, out var saved))
            {
                string path = KitFolder + "Meshes/IK_part_" + persisted.Count + ".asset";
                saved = UnityEngine.Object.Instantiate(m); saved.name = "IK_part_" + persisted.Count;
                var existing = AssetDatabase.LoadAssetAtPath<Mesh>(path);
                if (existing) { existing.Clear(); EditorUtility.CopySerialized(saved, existing); UnityEngine.Object.DestroyImmediate(saved); saved = existing; }
                else AssetDatabase.CreateAsset(saved, path);
                persisted[m] = saved;
            }
            f.sharedMesh = saved;
        }
    }

    static CheckoutInteriorPiece Piece(Transform t, Vector2 min, Vector2 max, float approach, float marker)
    {
        var p = t.gameObject.AddComponent<CheckoutInteriorPiece>();
        p.min = min; p.max = max; p.markerHeight = marker;
        p.serves = approach != 0; p.approach = new Vector3(0, 0, approach);
        return p;
    }

    static void Sign(Transform parent, string text, Vector3 at, float width, float size, Material face = null)
    {
        if (skipBody) return;
        KBox(parent, "Sign board", at, new Vector3(width, .26f, .05f), face ?? KNavy(), .02f);
        KBox(parent, "Sign trim", at + new Vector3(0, -.14f, 0), new Vector3(width + .02f, .025f, .06f), KGold(), .006f);
        KLetters(parent, text, at + new Vector3(0, 0, -.035f), size);
    }

    // ------------------------------------------------------------------ gondola shelves (grocery, snacks, cleaning)
    static void Gondola(Transform t, string variant)
    {
        KitModel(t);
        // The detailed aisle gondola (scripts/blender/rk_gondola.py) is double-sided with end caps and carries its
        // own stock as "Anim Fill 0..3" (quarters along the run, both faces): use those as the fill groups.
        var model = t.Find("Model");
        if (skipBody && model)
        {
            var stock = new List<Transform>();
            for (int i = 0; i < 4; i++)
            {
                var node = model.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "Anim Fill " + i);
                if (node) stock.Add(node);
            }
            if (stock.Count == 4)
            {
                var aisle = Piece(t, new Vector2(-1.42f, -.48f), new Vector2(1.42f, .48f), -.95f, 2.4f);
                var groups = new List<Transform>();
                for (int i = 0; i < 4; i++)
                {
                    var g = Group(t, "Anim Fill " + i);
                    stock[i].name = "Stock " + i; stock[i].SetParent(g, true);
                    groups.Add(g);
                }
                Finish(t, aisle, groups);
                return;
            }
        }
        var piece = Piece(t, new Vector2(-.95f, -.33f), new Vector2(.95f, .33f), -.9f, 2.15f);
        KBox(t, "Plinth", new Vector3(0, .06f, 0), new Vector3(1.9f, .12f, .6f), KNavy(), .01f);
        KBox(t, "Kick trim", new Vector3(0, .12f, -.3f), new Vector3(1.9f, .018f, .02f), KGold(), .004f);
        KBox(t, "Back", new Vector3(0, .98f, .26f), new Vector3(1.82f, 1.62f, .04f), KPeg(), .006f);
        foreach (var x in new[] { -.925f, .925f })
        {
            KBox(t, "Upright", new Vector3(x, 1.0f, 0), new Vector3(.05f, 1.76f, .6f), KCream(), .012f);
            KBox(t, "Upright cap", new Vector3(x, 1.89f, 0), new Vector3(.06f, .03f, .62f), KGold(), .006f);
        }
        float[] levels = { .16f, .52f, .88f, 1.24f, 1.6f };
        foreach (var y in levels)
        {
            KBox(t, "Shelf", new Vector3(0, y, -.02f), new Vector3(1.8f, .028f, .52f), KCream(), .006f);
            KBox(t, "Price rail", new Vector3(0, y - .005f, -.285f), new Vector3(1.8f, .05f, .012f), KRail(), .002f);
        }
        string title = variant == "snacks" ? "DOCES & SNACKS" : variant == "cleaning" ? "LIMPEZA" : "MERCEARIA";
        Sign(t, title, new Vector3(0, 2.02f, .22f), 1.5f, .011f);
        var fills = new List<Transform>();
        for (int l = 0; l < 5; l++) for (int half = 0; half < 2; half++) fills.Add(Group(t, "Anim Fill " + (l * 2 + half)));
        for (int l = 0; l < 5; l++)
        {
            float y = levels[l] + .014f;
            for (int half = 0; half < 2; half++)
            {
                var g = fills[l * 2 + half]; float left = half == 0 ? -.86f : .04f, right = half == 0 ? -.04f : .86f;
                int pick = (l * 2 + half) % 4;
                switch (variant)
                {
                    case "snacks":
                        if (l == 0) Row(g, ProductBox(new Vector3(.2f, .28f, .09f), new Vector2Int(pick, 3), .025f), new Vector3(.2f, .28f, .09f), left, right, y, -.16f, 3);
                        else if (l == 1) Row(g, ProductBox(new Vector3(.16f, .08f, .11f), new Vector2Int(4 + pick, 3)), new Vector3(.16f, .08f, .11f), left, right, y, -.16f, 3);
                        else if (l == 2) Row(g, ProductBox(new Vector3(.14f, .2f, .06f), new Vector2Int(4 + (pick + 2) % 4, 3)), new Vector3(.14f, .2f, .06f), left, right, y, -.17f, 4);
                        else if (l == 3) Row(g, ProductBox(new Vector3(.2f, .26f, .09f), new Vector2Int((pick + 2) % 4, 3), .025f), new Vector3(.2f, .26f, .09f), left, right, y, -.16f, 3);
                        else LatheRow(g, ProductLathe("tub", .055f, .12f, new Vector2Int(4 + pick, 3)), .055f, left, right, y, -.15f, 3);
                        break;
                    case "cleaning":
                        if (l == 0) Row(g, ProductBox(new Vector3(.3f, .24f, .2f), new Vector2Int(3, 4)), new Vector3(.3f, .24f, .2f), left, right, y, -.13f, 2);
                        else if (l == 1 || l == 3) LatheRow(g, ProductLathe("jug", .065f, .27f, new Vector2Int(pick % 3, 4)), .065f, left, right, y, -.16f, 3);
                        else if (l == 2) Row(g, ProductBox(new Vector3(.12f, .16f, .07f), new Vector2Int(4 + (pick % 4), 4)), new Vector3(.12f, .16f, .07f), left, right, y, -.17f, 4);
                        else LatheRow(g, ProductLathe("bottle", .04f, .2f, new Vector2Int(5, 4)), .04f, left, right, y, -.17f, 3);
                        break;
                    default:
                        if (l == 0) Row(g, ProductBox(new Vector3(.24f, .22f, .16f), new Vector2Int(5, 0)), new Vector3(.24f, .22f, .16f), left, right, y, -.13f, 2);
                        else if (l == 1) LatheRow(g, ProductLathe("can", .045f, .11f, new Vector2Int(pick, 1)), .045f, left, right, y, -.18f, 4);
                        else if (l == 2) Row(g, ProductBox(new Vector3(.2f, .29f, .07f), new Vector2Int(pick, 0)), new Vector3(.2f, .29f, .07f), left, right, y, -.17f, 4);
                        else if (l == 3) Row(g, ProductBox(new Vector3(.15f, .22f, .08f), new Vector2Int(4 + pick, 0)), new Vector3(.15f, .22f, .08f), left, right, y, -.17f, 4);
                        else LatheRow(g, ProductLathe("bottle", .04f, .24f, new Vector2Int(2 + pick % 2, 2)), .04f, left, right, y, -.17f, 3);
                        break;
                }
            }
        }
        Finish(t, piece, fills);
    }

    // ------------------------------------------------------------------ glass door cooler (drinks)
    static void Cooler(Transform t)
    {
        KitModel(t);
        var piece = Piece(t, new Vector2(-.95f, -.42f), new Vector2(.95f, .42f), -.95f, 2.4f);
        KBox(t, "Base", new Vector3(0, .09f, .02f), new Vector3(1.9f, .18f, .8f), KNavy(), .01f);
        KBox(t, "Back", new Vector3(0, 1.1f, .39f), new Vector3(1.9f, 1.86f, .04f), KWhite(), .01f);
        foreach (var x in new[] { -.93f, .93f }) KBox(t, "Side", new Vector3(x, 1.1f, .02f), new Vector3(.04f, 1.86f, .8f), KNavy(), .01f);
        KBox(t, "Top", new Vector3(0, 2.06f, .02f), new Vector3(1.9f, .08f, .8f), KNavy(), .01f);
        KBox(t, "Header", new Vector3(0, 2.2f, -.34f), new Vector3(1.9f, .22f, .08f), KGlow("2E8CAE"), .01f);
        KLetters(t, "BEBIDAS GELADAS", new Vector3(0, 2.2f, -.39f), .011f, false, Color.white, new Color(.1f, .3f, .4f));
        KBox(t, "Inner light", new Vector3(0, 2.0f, -.1f), new Vector3(1.8f, .02f, .05f), KLed(), .004f);
        float[] levels = { .2f, .6f, 1.0f, 1.4f };
        foreach (var y in levels) KBox(t, "Wire shelf", new Vector3(0, y, .02f), new Vector3(1.82f, .02f, .7f), KChrome(), .004f);
        for (int d = 0; d < 3; d++)
        {
            float x = -.62f + d * .62f;
            KBox(t, "Door frame", new Vector3(x, 1.08f, -.37f), new Vector3(.6f, 1.8f, .03f), KSteel(), .01f);
            KBox(t, "Glass", new Vector3(x, 1.08f, -.39f), new Vector3(.52f, 1.68f, .012f), KGlass(), .002f);
            KBox(t, "Handle", new Vector3(x + .22f, 1.12f, -.43f), new Vector3(.025f, .5f, .03f), KChrome(), .008f);
            // The glass is see-through: hide the frame's middle by keeping only the edges visible.
        }
        var fills = new List<Transform>();
        for (int i = 0; i < 8; i++) fills.Add(Group(t, "Anim Fill " + i));
        for (int l = 0; l < 4; l++)
            for (int half = 0; half < 2; half++)
            {
                var g = fills[l * 2 + half]; float left = half == 0 ? -.86f : .04f, right = half == 0 ? -.04f : .86f; float y = levels[l] + .012f;
                if (l % 2 == 0) LatheRow(g, ProductLathe("bottle", .042f, .3f, new Vector2Int((l + half) % 4, 2)), .042f, left, right, y, -.2f, 3);
                else LatheRow(g, ProductLathe("can", .036f, .12f, new Vector2Int(4 + (l + half) % 4, 1)), .036f, left, right, y, -.22f, 4);
            }
        // Door frames hide the stock: only a thin frame should show, so replace each frame with 4 bars.
        foreach (var f in t.GetComponentsInChildren<Transform>().Where(c => c.name == "Door frame").ToArray())
        {
            var p = f.localPosition; UnityEngine.Object.DestroyImmediate(f.gameObject);
            KBox(t, "Door bar", p + new Vector3(0, .88f, 0), new Vector3(.6f, .05f, .035f), KSteel(), .008f);
            KBox(t, "Door bar", p + new Vector3(0, -.88f, 0), new Vector3(.6f, .05f, .035f), KSteel(), .008f);
            KBox(t, "Door bar", p + new Vector3(-.28f, 0, 0), new Vector3(.04f, 1.8f, .035f), KSteel(), .008f);
            KBox(t, "Door bar", p + new Vector3(.28f, 0, 0), new Vector3(.04f, 1.8f, .035f), KSteel(), .008f);
        }
        Finish(t, piece, fills);
    }

    // ------------------------------------------------------------------ open multideck fridge (dairy, cold cuts)
    static void Dairy(Transform t)
    {
        KitModel(t);
        var piece = Piece(t, new Vector2(-.95f, -.5f), new Vector2(.95f, .42f), -1.0f, 2.3f);
        KBox(t, "Base", new Vector3(0, .25f, -.05f), new Vector3(1.9f, .5f, .9f), KNavy(), .015f);
        KBox(t, "Base trim", new Vector3(0, .5f, -.5f), new Vector3(1.9f, .03f, .03f), KGold(), .006f);
        KBox(t, "Well", new Vector3(0, .52f, -.05f), new Vector3(1.84f, .04f, .86f), KWhite(), .006f);
        KBox(t, "Back", new Vector3(0, 1.2f, .38f), new Vector3(1.9f, 1.4f, .08f), KWhite(), .01f);
        foreach (var x in new[] { -.93f, .93f })
        {
            KBox(t, "Side", new Vector3(x, 1.0f, -.05f), new Vector3(.04f, 1.95f, .9f), KNavy(), .012f);
            KBox(t, "Side glass", new Vector3(x, 1.2f, -.3f), new Vector3(.02f, .9f, .3f), KGlass(), .002f);
        }
        KBox(t, "Canopy", new Vector3(0, 1.97f, .02f), new Vector3(1.9f, .1f, .76f), KNavy(), .012f);
        KBox(t, "Canopy light", new Vector3(0, 1.91f, -.1f), new Vector3(1.8f, .02f, .06f), KLed(), .004f);
        KBox(t, "Canopy sign", new Vector3(0, 1.97f, -.37f), new Vector3(1.9f, .16f, .02f), KGlow("5DA0D8"), .004f);
        KLetters(t, "LATICÍNIOS & FRIOS", new Vector3(0, 1.97f, -.39f), .01f, false, Color.white, new Color(.1f, .25f, .45f));
        float[] levels = { .56f, .9f, 1.2f, 1.5f };
        float[] depth = { .78f, .5f, .44f, .38f };
        for (int l = 1; l < 4; l++)
        {
            KBox(t, "Shelf", new Vector3(0, levels[l], .34f - depth[l] * .5f), new Vector3(1.84f, .025f, depth[l]), KSteel(), .005f);
            KBox(t, "Price rail", new Vector3(0, levels[l] - .005f, .34f - depth[l] - .006f), new Vector3(1.84f, .045f, .01f), KRail(), .002f);
        }
        var fills = new List<Transform>();
        for (int i = 0; i < 8; i++) fills.Add(Group(t, "Anim Fill " + i));
        for (int l = 0; l < 4; l++)
            for (int half = 0; half < 2; half++)
            {
                var g = fills[l * 2 + half]; float left = half == 0 ? -.86f : .04f, right = half == 0 ? -.04f : .86f; float y = levels[l] + .014f;
                float z0 = .3f - depth[l] + .06f;
                if (l == 0) Row(g, ProductBox(new Vector3(.18f, .1f, .12f), new Vector2Int(half == 0 ? 0 : 1, 5), .02f), new Vector3(.18f, .1f, .12f), left, right, y, z0, 5, .015f, .02f);
                else if (l == 1) Row(g, ProductBox(new Vector3(.09f, .2f, .09f), new Vector2Int(6, 2)), new Vector3(.09f, .2f, .09f), left, right, y, z0, 3);
                else if (l == 2) LatheRow(g, ProductLathe("tub", .045f, .07f, new Vector2Int(7, 2)), .045f, left, right, y, z0 + .04f, 4);
                else Row(g, ProductBox(new Vector3(.14f, .06f, .1f), new Vector2Int(half == 0 ? 1 : 0, 5), .015f), new Vector3(.14f, .06f, .1f), left, right, y, z0, 3);
            }
        Finish(t, piece, fills);
    }

    // ------------------------------------------------------------------ produce display (tiered crates)
    static void Produce(Transform t)
    {
        KitModel(t);
        var piece = Piece(t, new Vector2(-.95f, -.6f), new Vector2(.95f, .5f), -1.1f, 2.1f);
        KBox(t, "Base", new Vector3(0, .2f, -.05f), new Vector3(1.9f, .4f, 1.1f), KWood(), .02f);
        KBox(t, "Base trim", new Vector3(0, .02f, -.05f), new Vector3(1.92f, .04f, 1.12f), KNavy(), .006f);
        float[] tierY = { .42f, .66f, .9f }, tierZ = { -.38f, -.05f, .28f };
        var fills = new List<Transform>();
        for (int i = 0; i < 9; i++) fills.Add(Group(t, "Anim Fill " + i));
        Vector2Int[] fruit = { new Vector2Int(0, 7), new Vector2Int(1, 7), new Vector2Int(2, 7), new Vector2Int(3, 7), new Vector2Int(4, 7), new Vector2Int(5, 7), new Vector2Int(6, 7), new Vector2Int(7, 7), new Vector2Int(1, 7) };
        for (int tier = 0; tier < 3; tier++)
        {
            if (tier > 0) KBox(t, "Riser", new Vector3(0, tierY[tier] * .5f + .2f, tierZ[tier]), new Vector3(1.86f, tierY[tier] - .4f, .32f), KWood(), .01f);
            for (int c = 0; c < 3; c++)
            {
                float x = -.62f + c * .62f; var at = new Vector3(x, tierY[tier], tierZ[tier]);
                var crate = Group(t, "Crate");
                crate.localPosition = at; crate.localRotation = Quaternion.Euler(-10, 0, 0);
                KBox(crate, "Crate bottom", new Vector3(0, .02f, 0), new Vector3(.58f, .03f, .32f), KCrate(), .004f);
                KBox(crate, "Crate front", new Vector3(0, .07f, -.155f), new Vector3(.58f, .12f, .02f), KCrate(), .004f);
                KBox(crate, "Crate back", new Vector3(0, .07f, .155f), new Vector3(.58f, .12f, .02f), KCrate(), .004f);
                KBox(crate, "Crate side", new Vector3(-.28f, .07f, 0), new Vector3(.02f, .12f, .32f), KCrate(), .004f);
                KBox(crate, "Crate side", new Vector3(.28f, .07f, 0), new Vector3(.02f, .12f, .32f), KCrate(), .004f);
                var g = fills[tier * 3 + c];
                var cell = fruit[tier * 3 + c];
                float r = cell.x == 4 ? .05f : cell.x == 7 ? .07f : cell.x == 5 ? .03f : .042f;
                var heap = Group(g, "Heap"); heap.localPosition = at; heap.localRotation = Quaternion.Euler(-10, 0, 0);
                Heap(heap, cell, r, new Vector3(0, .03f, 0), .52f, .28f, 0, 2);
            }
        }
        // Back board with a little striped awning and the department name.
        KBox(t, "Back board", new Vector3(0, 1.05f, .47f), new Vector3(1.9f, 1.3f, .05f), KWood(), .01f);
        KBox(t, "Awning", new Vector3(0, 1.62f, .3f), new Vector3(1.96f, .03f, .42f), KStripe("Green", "3FA34D"), .006f, 0, -18);
        Sign(t, "HORTIFRUTI", new Vector3(0, 1.9f, .44f), 1.3f, .012f);
        Finish(t, piece, fills);
    }

    // ------------------------------------------------------------------ chest freezer (frozen food, ice cream)
    static void Freezer(Transform t)
    {
        KitModel(t);
        var piece = Piece(t, new Vector2(-.95f, -.48f), new Vector2(.95f, .48f), -1.05f, 1.9f);
        KBox(t, "Body", new Vector3(0, .38f, 0), new Vector3(1.9f, .76f, .95f), KWhite(), .04f);
        KBox(t, "Bumper", new Vector3(0, .5f, -.48f), new Vector3(1.9f, .08f, .03f), KNavy(), .01f);
        KBox(t, "Kick", new Vector3(0, .04f, 0), new Vector3(1.86f, .08f, .9f), KBlack(), .005f);
        KBox(t, "Rim", new Vector3(0, .77f, 0), new Vector3(1.9f, .03f, .95f), KSteel(), .008f);
        KBox(t, "Well", new Vector3(0, .5f, 0), new Vector3(1.8f, .02f, .85f), KIce(), .004f);
        KBox(t, "Lid glass A", new Vector3(-.46f, .8f, 0), new Vector3(.92f, .012f, .9f), KGlass(), .002f);
        KBox(t, "Lid glass B", new Vector3(.46f, .82f, 0), new Vector3(.92f, .012f, .9f), KGlass(), .002f);
        KBox(t, "Lid bar", new Vector3(0, .83f, 0), new Vector3(.03f, .03f, .92f), KChrome(), .006f);
        KBox(t, "Sign post", new Vector3(0, 1.2f, .4f), new Vector3(.04f, .8f, .04f), KChrome(), .008f);
        Sign(t, "CONGELADOS", new Vector3(0, 1.62f, .4f), 1.1f, .011f, KMat("IK_IceBlue", "2E86DE", .5f));
        var fills = new List<Transform>();
        for (int i = 0; i < 6; i++) fills.Add(Group(t, "Anim Fill " + i));
        for (int i = 0; i < 6; i++)
        {
            float x0 = -.88f + (i % 3) * .59f, x1 = x0 + .55f; float z = i < 3 ? -.34f : .0f;
            var g = fills[i];
            if (i % 3 == 1) Row(g, ProductBox(new Vector3(.26f, .04f, .26f), new Vector2Int(4, 6)), new Vector3(.26f, .04f, .26f), x0, x1, .52f, z + .02f, 1, .02f, .01f, true, 2);
            if (i % 3 == 1) Row(g, ProductBox(new Vector3(.26f, .04f, .26f), new Vector2Int(4, 6)), new Vector3(.26f, .04f, .26f), x0, x1, .565f, z + .02f, 1, .02f, .01f, true, 6);
            else LatheRow(g, ProductLathe("tub", .07f, .12f, new Vector2Int(i % 4, 6)), .07f, x0, x1, .52f, z, 2, .02f);
        }
        Finish(t, piece, fills);
    }

    // ------------------------------------------------------------------ bakery rack (breads on slanted wooden shelves)
    static void BakeryRack(Transform t)
    {
        KitModel(t);
        var piece = Piece(t, new Vector2(-.95f, -.45f), new Vector2(.95f, .4f), -.95f, 2.1f);
        foreach (var x in new[] { -.92f, .92f }) KBox(t, "Frame", new Vector3(x, .85f, 0), new Vector3(.06f, 1.7f, .8f), KWood(), .015f);
        KBox(t, "Back", new Vector3(0, .9f, .37f), new Vector3(1.8f, 1.6f, .03f), KWood(), .006f);
        KBox(t, "Base", new Vector3(0, .08f, 0), new Vector3(1.9f, .16f, .8f), KNavy(), .01f);
        float[] levels = { .3f, .72f, 1.14f };
        var fills = new List<Transform>();
        for (int i = 0; i < 6; i++) fills.Add(Group(t, "Anim Fill " + i));
        for (int l = 0; l < 3; l++)
        {
            var shelf = Group(t, "Shelf"); shelf.localPosition = new Vector3(0, levels[l], 0); shelf.localRotation = Quaternion.Euler(-14, 0, 0);
            KBox(shelf, "Board", Vector3.zero, new Vector3(1.8f, .03f, .66f), KWood(), .006f);
            KBox(shelf, "Lip", new Vector3(0, .04f, -.33f), new Vector3(1.8f, .07f, .02f), KWood(), .004f);
            for (int half = 0; half < 2; half++)
            {
                var g = Group(fills[l * 2 + half], "Breads"); g.localPosition = shelf.localPosition; g.localRotation = shelf.localRotation;
                float left = half == 0 ? -.84f : .04f, right = half == 0 ? -.04f : .84f;
                if (l == 0) Row(g, ProductBox(new Vector3(.3f, .11f, .14f), new Vector2Int(4, 5), .04f), new Vector3(.3f, .11f, .14f), left, right, .015f, -.24f, 3, .02f, .04f, true, 8);
                else if (l == 1) Row(g, ProductBox(new Vector3(.08f, .07f, .5f), new Vector2Int(5, 5), .03f), new Vector3(.08f, .07f, .5f), left, right, .015f, -.02f, 1, .025f, .02f, true, 6);
                else Row(g, ProductBox(new Vector3(.12f, .07f, .09f), new Vector2Int(6, 5), .03f), new Vector3(.12f, .07f, .09f), left, right, .015f, -.22f, 4, .02f, .03f, true, 25);
            }
        }
        Sign(t, "PÃES FRESQUINHOS", new Vector3(0, 1.88f, .3f), 1.6f, .011f, KMat("IK_Bread", "B8672A", .3f));
        Finish(t, piece, fills);
    }

    // ------------------------------------------------------------------ sector counters
    static void SectorCounter(Transform t, string id)
    {
        KitModel(t);
        string title, hex;
        switch (id)
        {
            case "padaria": title = "PADARIA"; hex = "D98E2B"; break;
            case "queijaria": title = "QUEIJARIA"; hex = "8E6CCF"; break;
            case "acougue": title = "AÇOUGUE"; hex = "D64541"; break;
            case "peixaria": title = "PEIXARIA"; hex = "2E86DE"; break;
            case "bebidas": title = "BEBIDAS"; hex = "27AE60"; break;
            case "sorvetes": title = "SORVETES"; hex = "E86A9E"; break;
            default: title = "ADEGA"; hex = "8E2240"; break;
        }
        bool staffed = id == "padaria" || id == "queijaria" || id == "acougue" || id == "peixaria";
        // Big rounded departments modelled in Blender carry their own stock ("Anim Fill 0..3", left to right):
        // wider footprint, attendant behind the curved case, customers in front of its middle.
        var stock = new List<Transform>();
        var model = t.Find("Model");
        if (skipBody && model)
            for (int i = 0; i < 4; i++)
            {
                var node = model.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "Anim Fill " + i);
                if (node) stock.Add(node);
            }
        if (stock.Count == 4)
        {
            // Open wall-backed departments (ice cream, drinks, wine) have no attendant and a shallower footprint.
            // Footprints of the detailed Blender models (scripts/blender/rk_*.py): the drinks bank is only the
            // coolers against the wall, the wine wall has its tasting barrel in front, the ice cream parlour its case.
            var big = staffed ? Piece(t, new Vector2(-1.98f, -1.3f), new Vector2(1.98f, 2.06f), -1.62f, 3.1f)
                    : id == "bebidas" ? Piece(t, new Vector2(-1.66f, .66f), new Vector2(1.66f, 1.54f), .15f, 2.9f)
                    : id == "adega" ? Piece(t, new Vector2(-1.62f, -.5f), new Vector2(1.62f, 1.52f), -1.0f, 3.2f)
                    : Piece(t, new Vector2(-1.62f, -.92f), new Vector2(1.62f, 1.52f), -1.3f, 3.0f);
            big.staffed = staffed; big.staff = new Vector3(0, 0, .45f);
            var groups = new List<Transform>();
            for (int i = 0; i < 4; i++)
            {
                var g = Group(t, "Anim Fill " + i);
                stock[i].name = "Stock " + i; stock[i].SetParent(g, true);
                groups.Add(g);
            }
            Finish(t, big, groups);
            return;
        }
        var piece = Piece(t, new Vector2(-1.4f, -.62f), new Vector2(1.4f, 1.5f), -1.12f, 2.9f);
        piece.staffed = staffed; piece.staff = new Vector3(0, 0, .8f);
        var accent = KColor(hex, .45f);
        // Back wall with the striped awning and the department board.
        KBox(t, "Back wall", new Vector3(0, 1.22f, 1.44f), new Vector3(2.8f, 2.44f, .1f), id == "peixaria" || id == "acougue" ? KTile() : id == "adega" ? KWood() : KCream(), .02f);
        KBox(t, "Back wall base", new Vector3(0, .1f, 1.37f), new Vector3(2.8f, .2f, .06f), accent, .01f);
        var awning = KStripe(char.ToUpper(id[0]) + id.Substring(1), hex);
        KBox(t, "Awning", new Vector3(0, 2.22f, 1.14f), new Vector3(2.9f, .03f, .62f), awning, .006f, 0, -20);
        KBox(t, "Awning valance", new Vector3(0, 2.07f, .86f), new Vector3(2.9f, .14f, .02f), awning, .004f);
        KBox(t, "Board", new Vector3(0, 2.62f, 1.36f), new Vector3(2.2f, .44f, .08f), KNavy(), .03f);
        KBox(t, "Board trim", new Vector3(0, 2.38f, 1.34f), new Vector3(2.24f, .035f, .1f), KGold(), .008f);
        KLetters(t, title, new Vector3(0, 2.62f, 1.3f), .02f);
        foreach (var x in new[] { -1.35f, 1.35f }) KBox(t, "Pilaster", new Vector3(x, 1.25f, 1.3f), new Vector3(.1f, 2.5f, .3f), accent, .02f);
        var fills = new List<Transform>();
        for (int i = 0; i < 4; i++) fills.Add(Group(t, "Anim Fill " + i));
        if (staffed || id == "sorvetes")
        {
            // Serving counter: panelled front, marble top, curved sneeze-guard display on the customer side.
            KBox(t, "Counter", new Vector3(0, .5f, -.2f), new Vector3(2.7f, 1.0f, .8f), id == "padaria" ? KWood() : id == "sorvetes" ? KColor("F6D6E1") : KTile(), .02f);
            KBox(t, "Counter band", new Vector3(0, .84f, -.605f), new Vector3(2.7f, .1f, .02f), accent, .006f);
            KBox(t, "Kick", new Vector3(0, .05f, -.2f), new Vector3(2.66f, .1f, .76f), KNavy(), .006f);
            KBox(t, "Top", new Vector3(0, 1.02f, -.2f), new Vector3(2.76f, .045f, .86f), KMarble(), .01f);
            KBox(t, "Display bed", new Vector3(0, 1.06f, -.28f), new Vector3(2.5f, .03f, .5f), id == "peixaria" ? KIce() : KWhite(), .005f);
            KBox(t, "Glass front", new Vector3(0, 1.28f, -.55f), new Vector3(2.5f, .44f, .012f), KGlass(), .002f, 0, -18);
            KBox(t, "Glass top", new Vector3(0, 1.5f, -.33f), new Vector3(2.5f, .012f, .36f), KGlass(), .002f);
            KBox(t, "Display light", new Vector3(0, 1.49f, -.18f), new Vector3(2.4f, .02f, .04f), KLed(), .003f);
            foreach (var x in new[] { -1.26f, 1.26f }) KBox(t, "Glass end", new Vector3(x, 1.3f, -.36f), new Vector3(.012f, .46f, .42f), KGlass(), .002f);
            // Work bench along the back wall.
            KBox(t, "Back bench", new Vector3(0, .45f, 1.22f), new Vector3(2.6f, .9f, .36f), KSteel(), .01f);
            for (int i = 0; i < 4; i++)
            {
                var g = fills[i]; float x0 = -1.18f + i * .6f, x1 = x0 + .54f;
                switch (id)
                {
                    case "padaria": Row(g, ProductBox(new Vector3(.22f, .09f, .13f), new Vector2Int(4 + i % 2, 5), .04f), new Vector3(.22f, .09f, .13f), x0, x1, 1.075f, -.44f, 2, .03f, .05f, true, 10);
                        Row(g, ProductBox(new Vector3(.11f, .07f, .09f), new Vector2Int(6, 5), .03f), new Vector3(.11f, .07f, .09f), x0, x1, 1.075f, -.12f, 1, .03f, .03f, true, 25); break;
                    case "queijaria": LatheRow(g, ProductLathe("wheel", .1f, .09f, new Vector2Int(0, 5)), .1f, x0, x1, 1.075f, -.4f, 2, .04f); break;
                    case "acougue": Row(g, ProductBox(new Vector3(.2f, .045f, .14f), new Vector2Int(2, 5), .02f), new Vector3(.2f, .045f, .14f), x0, x1, 1.075f, -.46f, 3, .03f, .02f, true, 8); break;
                    case "peixaria": Row(g, ProductBox(new Vector3(.08f, .05f, .34f), new Vector2Int(3, 5), .025f), new Vector3(.08f, .05f, .34f), x0, x1, 1.075f, -.3f, 1, .04f, .02f, true, 14); break;
                    default: LatheRow(g, ProductLathe("tub", .085f, .1f, new Vector2Int(i % 4, 6)), .085f, x0, x1, 1.075f, -.42f, 2, .03f); break;
                }
            }
            switch (id)
            {
                case "padaria":
                    // Brick oven with a glowing mouth, and bread baskets on the bench.
                    KBox(t, "Oven", new Vector3(.8f, 1.35f, 1.2f), new Vector3(.9f, .9f, .36f), KColor("A8543A", .2f), .05f);
                    KBox(t, "Oven mouth", new Vector3(.8f, 1.3f, 1.01f), new Vector3(.46f, .26f, .02f), KGlow("FF8A2A"), .02f);
                    for (int i = 0; i < 3; i++) MeshNode(t, "Loaf", ProductBox(new Vector3(.28f, .1f, .13f), new Vector2Int(4, 5), .04f), new Vector3(-.9f + i * .32f, .95f, 1.2f), KProducts(), Quaternion.Euler(0, 10 * i, 0));
                    break;
                case "queijaria":
                    for (int i = 0; i < 5; i++) MeshNode(t, "Wheel", ProductLathe("wheel", .16f, .12f, new Vector2Int(0, 5)), new Vector3(-1f + i * .5f, 1.6f, 1.3f), KProducts());
                    KBox(t, "Cheese shelf", new Vector3(0, 1.58f, 1.3f), new Vector3(2.6f, .03f, .24f), KWood(), .005f);
                    break;
                case "acougue":
                    KBox(t, "Hook rail", new Vector3(0, 1.85f, 1.25f), new Vector3(2.4f, .03f, .03f), KChrome(), .006f);
                    for (int i = 0; i < 5; i++) MeshNode(t, "Ham", ProductLathe("bottle", .07f, .32f, new Vector2Int(2, 5)), new Vector3(-.9f + i * .45f, 1.48f, 1.25f), KProducts(), Quaternion.Euler(180, 0, 0));
                    break;
                case "peixaria":
                    KBox(t, "Fish board", new Vector3(0, 1.6f, 1.38f), new Vector3(1.0f, .5f, .03f), KMat("IK_IceBlue", "2E86DE", .5f), .02f);
                    MeshNode(t, "Fish sign", ProductBox(new Vector3(.7f, .22f, .06f), new Vector2Int(3, 5), .1f), new Vector3(0, 1.6f, 1.35f), KProducts());
                    break;
                default:
                    MeshNode(t, "Giant cone", Lathe(new[] { new Vector2(0, 0), new Vector2(.14f, .5f), new Vector2(.16f, .52f) }, 12), new Vector3(1.05f, 1.2f, 1.3f), KMat("IK_Cone", "D9A45A", .3f));
                    KSphere(t, "Scoop", new Vector3(1.05f, 1.78f, 1.3f), Vector3.one * .34f, KColor("F4A6C1"));
                    KSphere(t, "Scoop", new Vector3(1.05f, 1.98f, 1.3f), Vector3.one * .28f, KColor("B8E6D2"));
                    break;
            }
        }
        else
        {
            // Self-service: shelving on the back wall and a low island in front.
            for (int l = 0; l < 3; l++) KBox(t, "Wall shelf", new Vector3(0, .55f + l * .5f, 1.25f), new Vector3(2.6f, .03f, .32f), id == "adega" ? KWood() : KSteel(), .005f);
            KBox(t, "Island", new Vector3(0, .38f, -.15f), new Vector3(2.5f, .76f, .8f), id == "adega" ? KWood() : KNavy(), .02f);
            KBox(t, "Island top", new Vector3(0, .77f, -.15f), new Vector3(2.56f, .03f, .86f), id == "adega" ? KColor("5B2A1E", .3f) : KMarble(), .006f);
            KBox(t, "Island band", new Vector3(0, .6f, -.56f), new Vector3(2.5f, .08f, .02f), accent, .004f);
            for (int i = 0; i < 4; i++)
            {
                var g = fills[i]; float x0 = -1.18f + i * .6f, x1 = x0 + .54f;
                if (id == "adega")
                {
                    for (int l = 0; l < 3; l++) LatheRow(g, ProductLathe("wine", .038f, .3f, new Vector2Int(4, 2)), .038f, x0, x1, .565f + l * .5f, 1.14f, 1, .02f);
                    LatheRow(g, ProductLathe("wine", .038f, .3f, new Vector2Int(4, 2)), .038f, x0, x1, .785f, -.4f, 3, .03f);
                }
                else
                {
                    for (int l = 0; l < 3; l++) LatheRow(g, ProductLathe("bottle", .042f, .28f, new Vector2Int((i + l) % 4, 2)), .042f, x0, x1, .565f + l * .5f, 1.14f, 1, .015f);
                    Row(g, ProductBox(new Vector3(.3f, .2f, .2f), new Vector2Int(4 + i % 4, 1)), new Vector3(.3f, .2f, .2f), x0, x1, .785f, -.4f, 2, .02f, .03f);
                }
            }
            if (id == "adega")
            {
                MeshNode(t, "Barrel", Lathe(new[] { new Vector2(.22f, 0), new Vector2(.27f, .3f), new Vector2(.22f, .6f) }, 14), new Vector3(1.05f, .78f, -.3f), KMat("IK_Barrel", "8A5A34", .25f), Quaternion.Euler(0, 0, 90));
            }
            else
            {
                MeshNode(t, "Ice bucket", Lathe(new[] { new Vector2(.2f, 0), new Vector2(.26f, .36f), new Vector2(.27f, .38f) }, 14, null, false), new Vector3(1.0f, .8f, -.2f), KChrome());
                KSphere(t, "Ice", new Vector3(1.0f, 1.12f, -.2f), new Vector3(.46f, .12f, .46f), KIce());
            }
        }
        Finish(t, piece, fills);
    }

    // ------------------------------------------------------------------ checkout counter
    static void CheckoutCounter(Transform t)
    {
        KitModel(t);
        var piece = Piece(t, new Vector2(-1.25f, -.45f), new Vector2(1.25f, 1.25f), 0, 2.4f);
        piece.staffed = true; piece.staff = new Vector3(.2f, 0, .78f);
        piece.queue = new[] { new Vector3(.55f, 0, -1.0f), new Vector3(-.3f, 0, -1.0f), new Vector3(-1.15f, 0, -1.0f), new Vector3(-2.0f, 0, -1.0f) };
        piece.register = new Vector3(.55f, 0, .1f);
        piece.beltStart = new Vector3(-1.0f, .86f, -.05f); piece.beltEnd = new Vector3(.25f, .86f, -.05f);
        KBox(t, "Cabinet", new Vector3(0, .42f, 0), new Vector3(2.4f, .84f, .9f), KNavy(), .025f);
        KBox(t, "Front panel", new Vector3(-.1f, .45f, -.455f), new Vector3(2.1f, .62f, .02f), KWood(), .006f);
        KBox(t, "Gold band", new Vector3(0, .8f, -.46f), new Vector3(2.4f, .04f, .02f), KGold(), .006f);
        KBox(t, "Top", new Vector3(0, .86f, 0), new Vector3(2.44f, .04f, .94f), KMarble(), .01f);
        KBox(t, "Belt", new Vector3(-.38f, .885f, -.08f), new Vector3(1.3f, .02f, .44f), KBelt(), .006f);
        KBox(t, "Belt rail", new Vector3(-.38f, .9f, -.32f), new Vector3(1.32f, .04f, .025f), KChrome(), .006f);
        KBox(t, "Belt rail", new Vector3(-.38f, .9f, .16f), new Vector3(1.32f, .04f, .025f), KChrome(), .006f);
        KBox(t, "Divider", new Vector3(-.7f, .92f, -.08f), new Vector3(.03f, .05f, .4f), KColor("E15533"), .008f);
        KBox(t, "Scanner", new Vector3(.4f, .89f, -.05f), new Vector3(.3f, .02f, .3f), KBlack(), .006f);
        KBox(t, "Scanner glass", new Vector3(.4f, .902f, -.05f), new Vector3(.2f, .005f, .2f), KGlow("FF4A3A"), .002f);
        KBox(t, "Bagging well", new Vector3(.95f, .86f, -.05f), new Vector3(.46f, .04f, .7f), KSteel(), .006f);
        // Register: screen facing the cashier, card machine for the customer.
        KBox(t, "Screen post", new Vector3(.6f, 1.0f, .3f), new Vector3(.05f, .25f, .05f), KChrome(), .01f);
        KBox(t, "Screen", new Vector3(.6f, 1.2f, .3f), new Vector3(.36f, .24f, .04f), KBlack(), .015f, 180, -12);
        KBox(t, "Screen glow", new Vector3(.6f, 1.2f, .325f), new Vector3(.32f, .2f, .01f), KGlow("7BD3F7"), .004f, 180, -12);
        KBox(t, "Cash drawer", new Vector3(.6f, .74f, .43f), new Vector3(.4f, .12f, .06f), KBlack(), .01f);
        KBox(t, "Card machine", new Vector3(.62f, .95f, -.34f), new Vector3(.1f, .16f, .06f), KBlack(), .012f, 0, 20);
        KBox(t, "Card keys", new Vector3(.62f, .96f, -.375f), new Vector3(.07f, .08f, .005f), KGlow("5DA637"), .002f, 0, 20);
        // Lane light with the checkout number.
        KBox(t, "Lane pole", new Vector3(-1.15f, 1.35f, .35f), new Vector3(.05f, 1.0f, .05f), KChrome(), .01f);
        KLathe(t, "Lane lamp", new Vector3(-1.15f, 1.85f, .35f), KGlow("F2C45A"), 14, new Vector2(.02f, 0), new Vector2(.12f, .04f), new Vector2(.12f, .2f), new Vector2(.02f, .24f));
        KLetters(t, "CAIXA", new Vector3(-1.15f, 1.98f, .22f), .008f, false, new Color(.11f, .17f, .31f), new Color(.5f, .4f, .2f));
        // Impulse rack at the start of the lane.
        KBox(t, "Impulse rack", new Vector3(-1.1f, .55f, -.62f), new Vector3(.3f, 1.1f, .28f), KNavy(), .015f);
        var fills = new List<Transform> { Group(t, "Anim Fill 0") };
        for (int l = 0; l < 3; l++) Row(fills[0], ProductBox(new Vector3(.07f, .1f, .03f), new Vector2Int(4 + l, 3)), new Vector3(.07f, .1f, .03f), -1.22f, -.98f, .35f + l * .3f, -.75f, 1, .01f);
        Finish(t, piece, fills);
    }

    // ------------------------------------------------------------------ self-checkout kiosk
    static void Kiosk(Transform t)
    {
        KitModel(t);
        var piece = Piece(t, new Vector2(-.52f, -.34f), new Vector2(1.05f, .34f), 0, 2.2f);
        piece.queue = new[] { new Vector3(-.14f, 0, -.95f), new Vector3(-.14f, 0, -1.7f) };
        piece.register = new Vector3(-.14f, 0, 0);
        KBox(t, "Pedestal", new Vector3(-.12f, .42f, .05f), new Vector3(.62f, .84f, .5f), KNavy(), .03f);
        KBox(t, "Pedestal band", new Vector3(-.12f, .7f, -.205f), new Vector3(.62f, .05f, .02f), KGold(), .005f);
        KBox(t, "Scanner deck", new Vector3(-.14f, .86f, -.06f), new Vector3(.6f, .05f, .5f), KSteel(), .01f);
        KBox(t, "Scanner glass", new Vector3(-.14f, .89f, -.08f), new Vector3(.24f, .005f, .24f), KGlow("FF4A3A"), .002f);
        KBox(t, "Screen neck", new Vector3(-.12f, 1.05f, .18f), new Vector3(.06f, .35f, .06f), KChrome(), .01f);
        KBox(t, "Screen", new Vector3(-.12f, 1.32f, .15f), new Vector3(.46f, .34f, .05f), KBlack(), .02f, 0, 15);
        KBox(t, "Screen glow", new Vector3(-.12f, 1.32f, .122f), new Vector3(.42f, .3f, .01f), KGlow("7BD3F7"), .004f, 0, 15);
        KBox(t, "Card slot", new Vector3(.12f, .96f, -.16f), new Vector3(.1f, .12f, .06f), KBlack(), .01f, 0, 15);
        // Bagging stand with a white bag.
        KBox(t, "Bag stand", new Vector3(.78f, .34f, 0), new Vector3(.04f, .68f, .04f), KChrome(), .008f);
        KBox(t, "Bag plate", new Vector3(.78f, .68f, 0), new Vector3(.44f, .03f, .44f), KSteel(), .006f);
        KBox(t, "Bag", new Vector3(.78f, .84f, 0), new Vector3(.34f, .3f, .22f), KWhite(), .03f);
        KBox(t, "Light pole", new Vector3(-.4f, 1.4f, .22f), new Vector3(.04f, 1.1f, .04f), KChrome(), .008f);
        KLathe(t, "Light", new Vector3(-.4f, 1.95f, .22f), KGlow("5DA637"), 12, new Vector2(.02f, 0), new Vector2(.09f, .04f), new Vector2(.09f, .16f), new Vector2(.02f, .2f));
        Finish(t, piece, new List<Transform>());
    }

    // ------------------------------------------------------------------ decorations (build-mode shop)
    // Footprint half-size (x, z) and marker height of every decoration, inside and outside the shop.
    static readonly Dictionary<string, Vector3> DecorSize = new Dictionary<string, Vector3>
    {
        { "basket-stack", new Vector3(.3f, .24f, 1.2f) }, { "plant-small", new Vector3(.28f, .28f, 1.3f) }, { "balloons", new Vector3(.34f, .34f, 2.3f) },
        { "floor-lamp", new Vector3(.24f, .24f, 1.9f) }, { "bench", new Vector3(.8f, .3f, 1.2f) }, { "cart-corral", new Vector3(.42f, 1.0f, 1.4f) },
        { "plant-palm", new Vector3(.45f, .45f, 2.4f) }, { "promo-stand", new Vector3(.58f, .44f, 1.9f) }, { "water-cooler", new Vector3(.22f, .22f, 1.7f) },
        { "gumball", new Vector3(.24f, .24f, 1.6f) }, { "flower-stand", new Vector3(.72f, .4f, 1.9f) }, { "watermelon-pile", new Vector3(.72f, .56f, 1.3f) },
        { "claw-machine", new Vector3(.45f, .45f, 2.4f) }, { "atm", new Vector3(.38f, .34f, 2.1f) }, { "digital-totem", new Vector3(.34f, .2f, 2.2f) },
        // Outside the shop (city block).
        { "park-bench", new Vector3(.86f, .36f, 1.2f) }, { "tree-planter", new Vector3(.72f, .72f, 3.2f) }, { "flower-bed", new Vector3(1.04f, .44f, 1.2f) },
        { "street-lamp", new Vector3(.24f, .24f, 3.9f) }, { "fountain", new Vector3(1.12f, 1.12f, 1.9f) }, { "bike-rack", new Vector3(.92f, .3f, 1.3f) },
        { "popcorn-cart", new Vector3(.8f, .42f, 2.5f) }, { "ice-cream-cart", new Vector3(.8f, .42f, 2.5f) }, { "parasol-table", new Vector3(1.0f, 1.0f, 2.7f) },
        { "kiddie-ride", new Vector3(.46f, .62f, 1.5f) }, { "billboard", new Vector3(.94f, .3f, 2.8f) }, { "recycle-bins", new Vector3(.8f, .24f, 1.3f) },
    };
    public static readonly string[] OutsideDecor = { "park-bench", "tree-planter", "flower-bed", "street-lamp", "fountain", "bike-rack", "popcorn-cart", "ice-cream-cart", "parasol-table", "kiddie-ride", "billboard", "recycle-bins" };

    static void Decor(Transform t, string id)
    {
        var s = DecorSize[id];
        var piece = Piece(t, new Vector2(-s.x, -s.y), new Vector2(s.x, s.y), 0, s.z);
        if (!KitModel(t)) DecorPrimitives(t, id);
        Finish(t, piece, new List<Transform>());
    }

    // Fallback look when the Blender model is missing.
    static void DecorPrimitives(Transform t, string id)
    {
        void P(float hx, float hz, float marker = 1.6f) { }
        switch (id)
        {
            case "basket-stack":
            {
                P(.3f, .24f);
                var red = KColor("D8423A", .5f);
                for (int i = 0; i < 6; i++)
                {
                    float y = .05f + i * .09f;
                    KBox(t, "Basket", new Vector3(0, y + .07f, 0), new Vector3(.46f - i * .004f, .14f, .34f), red, .02f);
                    KBox(t, "Basket rim", new Vector3(0, y + .145f, 0), new Vector3(.47f, .012f, .35f), KColor("A92E28"), .004f);
                }
                KBox(t, "Handle", new Vector3(0, .72f, 0), new Vector3(.36f, .02f, .02f), KBlack(), .006f);
                KBox(t, "Sign", new Vector3(0, .95f, .15f), new Vector3(.3f, .12f, .02f), KNavy(), .01f);
                KLetters(t, "CESTAS", new Vector3(0, .95f, .135f), .005f);
                break;
            }
            case "plant-small":
            {
                P(.28f, .28f, 1.3f);
                KLathe(t, "Pot", Vector3.zero, KTerracotta(), 16, new Vector2(.15f, 0), new Vector2(.22f, .38f), new Vector2(.25f, .4f), new Vector2(.25f, .44f), new Vector2(.21f, .44f));
                KLathe(t, "Soil", new Vector3(0, .41f, 0), KColor("4A3526", .1f), 16, new Vector2(.21f, 0), new Vector2(0, .01f));
                var sway = Group(t, "Anim Sway"); sway.localPosition = new Vector3(0, .42f, 0);
                for (int i = 0; i < 7; i++)
                {
                    float a = i * 51f;
                    KSphere(sway, "Leaf", Quaternion.Euler(0, a, 0) * new Vector3(.1f, .22f + (i % 3) * .08f, 0), new Vector3(.2f, .34f, .12f), i % 2 == 0 ? KLeaf() : KLeafDark());
                }
                break;
            }
            case "balloons":
            {
                P(.32f, .32f, 2.3f);
                KLathe(t, "Weight", Vector3.zero, KGold(), 14, new Vector2(.14f, 0), new Vector2(.14f, .08f), new Vector2(.06f, .12f), new Vector2(0, .13f));
                string[] colors = { "E15533", "F2B03D", "2E8CAE", "5DA637", "E86A9E", "8E6CCF" };
                for (int i = 0; i < 6; i++)
                {
                    var bob = Group(t, "Anim Bob");
                    var top = new Vector3(Mathf.Cos(i * 1.05f) * .2f, 1.5f + (i % 3) * .2f, Mathf.Sin(i * 1.05f) * .2f);
                    bob.localPosition = top;
                    KSphere(bob, "Balloon", Vector3.zero, new Vector3(.32f, .38f, .32f), KMat("IK_Balloon_" + colors[i], colors[i], .8f));
                    Beam(t, "String", new Vector3(0, .13f, 0), top - new Vector3(0, .19f, 0), .006f, KWhite());
                }
                break;
            }
            case "floor-lamp":
            {
                P(.24f, .24f, 1.9f);
                KLathe(t, "Base", Vector3.zero, KGold(), 16, new Vector2(.2f, 0), new Vector2(.2f, .03f), new Vector2(.05f, .06f), new Vector2(0, .06f));
                KBox(t, "Pole", new Vector3(0, .85f, 0), new Vector3(.03f, 1.6f, .03f), KGold(), .01f);
                KLathe(t, "Shade", new Vector3(0, 1.45f, 0), KMat("IK_Shade", "F7EBD2", .2f, 0, null, null, true, "8A6A3A"), 18, new Vector2(.26f, 0), new Vector2(.16f, .32f), new Vector2(0, .33f));
                KLathe(t, "Bulb glow", new Vector3(0, 1.44f, 0), KLed(), 12, new Vector2(.2f, 0), new Vector2(0, .01f));
                break;
            }
            case "bench":
            {
                P(.78f, .28f, 1.2f);
                foreach (var x in new[] { -.62f, .62f })
                {
                    KBox(t, "Leg", new Vector3(x, .22f, 0), new Vector3(.06f, .44f, .46f), KNavy(), .01f);
                    KBox(t, "Arm", new Vector3(x, .62f, -.02f), new Vector3(.06f, .04f, .44f), KGold(), .008f);
                }
                for (int i = 0; i < 3; i++) KBox(t, "Seat slat", new Vector3(0, .45f, -.15f + i * .15f), new Vector3(1.5f, .04f, .12f), KWood(), .008f);
                for (int i = 0; i < 2; i++) KBox(t, "Back slat", new Vector3(0, .65f + i * .16f, .2f), new Vector3(1.5f, .11f, .03f), KWood(), .008f, 0, -8);
                break;
            }
            case "cart-corral":
            {
                P(.4f, 1.0f, 1.4f);
                KBox(t, "Rail", new Vector3(-.36f, .45f, 0), new Vector3(.04f, .04f, 1.9f), KChrome(), .01f);
                KBox(t, "Rail", new Vector3(.36f, .45f, 0), new Vector3(.04f, .04f, 1.9f), KChrome(), .01f);
                foreach (var z in new[] { -.95f, .95f }) foreach (var x in new[] { -.36f, .36f }) KBox(t, "Post", new Vector3(x, .23f, z), new Vector3(.04f, .46f, .04f), KChrome(), .01f);
                KBox(t, "Roof sign", new Vector3(0, 1.2f, .95f), new Vector3(.6f, .2f, .03f), KNavy(), .015f);
                KBox(t, "Sign post", new Vector3(0, .82f, .95f), new Vector3(.03f, .6f, .03f), KChrome(), .006f);
                KLetters(t, "CARRINHOS", new Vector3(0, 1.2f, .93f), .005f);
                for (int i = 0; i < 4; i++) Cart(t, new Vector3(0, 0, -.7f + i * .3f));
                break;
            }
            case "plant-palm":
            {
                P(.45f, .45f, 2.4f);
                KLathe(t, "Pot", Vector3.zero, KGold(), 18, new Vector2(.24f, 0), new Vector2(.34f, .5f), new Vector2(.36f, .55f), new Vector2(.31f, .55f));
                KLathe(t, "Soil", new Vector3(0, .5f, 0), KColor("4A3526", .1f), 16, new Vector2(.31f, 0), new Vector2(0, .01f));
                var sway = Group(t, "Anim Sway"); sway.localPosition = new Vector3(0, .5f, 0);
                for (int i = 0; i < 4; i++) KBox(sway, "Trunk", new Vector3(Mathf.Sin(i) * .02f, .15f + i * .3f, 0), new Vector3(.1f - i * .012f, .3f, .1f - i * .012f), KMat("IK_Trunk", "8A6A45", .15f), .02f, i * 20);
                for (int i = 0; i < 8; i++)
                {
                    var frond = Group(sway, "Frond"); frond.localPosition = new Vector3(0, 1.25f, 0); frond.localRotation = Quaternion.Euler(0, i * 45, 0);
                    KBox(frond, "Leaf", new Vector3(0, .05f, .35f), new Vector3(.2f, .02f, .7f), i % 2 == 0 ? KLeaf() : KLeafDark(), .01f, 0, 25 + (i % 3) * 8);
                }
                break;
            }
            case "promo-stand":
            {
                P(.58f, .44f, 1.9f);
                KBox(t, "Pallet", new Vector3(0, .07f, 0), new Vector3(1.1f, .14f, .85f), KCrate(), .01f);
                var g = Group(t, "Stack");
                for (int l = 0; l < 3; l++) Row(g, ProductBox(new Vector3(.3f, .3f, .2f), new Vector2Int(l, 0)), new Vector3(.3f, .3f, .2f), -.4f + l * .04f, .4f - l * .04f, .14f + l * .31f, -.3f + l * .03f, 3 - l, .02f, .02f, true, 2);
                KBox(t, "Card post", new Vector3(.45f, .9f, .32f), new Vector3(.03f, 1.6f, .03f), KChrome(), .006f);
                var card = GameObject.CreatePrimitive(PrimitiveType.Quad); UnityEngine.Object.DestroyImmediate(card.GetComponent<Collider>());
                card.name = "Promo card"; card.transform.SetParent(t, false); card.transform.localPosition = new Vector3(.45f, 1.55f, .3f); card.transform.localScale = new Vector3(.6f, .3f, 1);
                card.GetComponent<Renderer>().sharedMaterial = KPromo();
                var back = GameObject.CreatePrimitive(PrimitiveType.Quad); UnityEngine.Object.DestroyImmediate(back.GetComponent<Collider>());
                back.name = "Promo card back"; back.transform.SetParent(t, false); back.transform.localPosition = new Vector3(.45f, 1.55f, .31f); back.transform.localRotation = Quaternion.Euler(0, 180, 0); back.transform.localScale = new Vector3(.6f, .3f, 1);
                back.GetComponent<Renderer>().sharedMaterial = KPromo();
                break;
            }
            case "water-cooler":
            {
                P(.22f, .22f, 1.7f);
                KBox(t, "Body", new Vector3(0, .5f, 0), new Vector3(.34f, 1.0f, .34f), KWhite(), .04f);
                KBox(t, "Tray", new Vector3(0, .62f, -.18f), new Vector3(.2f, .02f, .08f), KBlack(), .005f);
                KBox(t, "Tap hot", new Vector3(-.06f, .8f, -.18f), new Vector3(.04f, .06f, .04f), KColor("E15533"), .01f);
                KBox(t, "Tap cold", new Vector3(.06f, .8f, -.18f), new Vector3(.04f, .06f, .04f), KColor("2E86DE"), .01f);
                KLathe(t, "Bottle", new Vector3(0, 1.0f, 0), Transparent("IK_WaterBlue", new Color(.45f, .7f, .95f, .55f)), 16, new Vector2(.05f, 0), new Vector2(.05f, .06f), new Vector2(.15f, .12f), new Vector2(.15f, .42f), new Vector2(.12f, .46f), new Vector2(0, .47f));
                break;
            }
            case "gumball":
            {
                P(.24f, .24f, 1.6f);
                KLathe(t, "Stand", Vector3.zero, KColor("D8423A", .6f), 16, new Vector2(.2f, 0), new Vector2(.2f, .04f), new Vector2(.05f, .1f), new Vector2(.05f, .75f), new Vector2(.16f, .8f), new Vector2(.16f, 1.0f), new Vector2(0, 1.0f));
                KBox(t, "Coin plate", new Vector3(0, .9f, -.16f), new Vector3(.12f, .12f, .02f), KChrome(), .01f);
                string[] colors = { "E15533", "F2B03D", "2E8CAE", "5DA637", "E86A9E", "FFFFFF" };
                for (int i = 0; i < 22; i++)
                {
                    var p = new Vector3(Jitter(.13f), 1.08f + Mathf.Abs(Jitter(.16f)), Jitter(.13f));
                    KSphere(t, "Gum", p, Vector3.one * .05f, KColor(colors[i % colors.Length], .8f));
                }
                KSphere(t, "Globe", new Vector3(0, 1.17f, 0), Vector3.one * .36f, KGlass());
                KLathe(t, "Cap", new Vector3(0, 1.33f, 0), KColor("D8423A", .6f), 14, new Vector2(.08f, 0), new Vector2(.06f, .06f), new Vector2(0, .08f));
                break;
            }
            case "flower-stand":
            {
                P(.7f, .4f, 1.7f);
                KBox(t, "Cart", new Vector3(0, .42f, 0), new Vector3(1.3f, .12f, .7f), KWood(), .02f);
                foreach (var x in new[] { -.55f, .55f }) foreach (var z in new[] { -.28f, .28f }) KBox(t, "Leg", new Vector3(x, .18f, z), new Vector3(.05f, .36f, .05f), KNavy(), .01f);
                MeshNode(t, "Wheel", Lathe(new[] { new Vector2(.18f, 0), new Vector2(.18f, .04f) }, 16), new Vector3(-.68f, .2f, 0), KBlack(), Quaternion.Euler(0, 0, 90));
                string[] colors = { "E15533", "F2B03D", "E86A9E", "FFFFFF", "8E6CCF", "F28C38" };
                for (int i = 0; i < 6; i++)
                {
                    var at = new Vector3(-.45f + (i % 3) * .45f, .48f, -.15f + (i / 3) * .3f);
                    KLathe(t, "Bucket", at, KSteel(), 12, new Vector2(.1f, 0), new Vector2(.13f, .26f), new Vector2(.135f, .27f));
                    var sway = Group(t, "Anim Sway"); sway.localPosition = at + new Vector3(0, .26f, 0);
                    for (int k = 0; k < 7; k++)
                    {
                        var head = new Vector3(Jitter(.08f), .18f + Jitter(.06f), Jitter(.08f));
                        Beam(sway, "Stem", Vector3.zero, head, .012f, KLeafDark());
                        KSphere(sway, "Bloom", head, Vector3.one * .085f, KMat("IK_Bloom_" + colors[i], colors[i], .35f));
                    }
                }
                KBox(t, "Canopy post", new Vector3(.62f, 1.0f, .3f), new Vector3(.04f, 1.1f, .04f), KNavy(), .008f);
                KBox(t, "Canopy post", new Vector3(-.62f, 1.0f, .3f), new Vector3(.04f, 1.1f, .04f), KNavy(), .008f);
                KBox(t, "Canopy", new Vector3(0, 1.55f, .12f), new Vector3(1.4f, .03f, .6f), KStripe("Pink", "E86A9E"), .006f, 0, -15);
                break;
            }
            case "watermelon-pile":
            {
                P(.7f, .55f, 1.3f);
                KBox(t, "Bin", new Vector3(0, .25f, 0), new Vector3(1.36f, .5f, 1.06f), KCrate(), .02f);
                KBox(t, "Bin rim", new Vector3(0, .5f, 0), new Vector3(1.4f, .04f, 1.1f), KWood(), .01f);
                var melon = KStripe("Melon", "3E8E3A");
                for (int l = 0; l < 3; l++)
                    for (int i = 0; i < (3 - l) * 2; i++)
                    {
                        float x = -.4f + (i % (3 - l)) * .4f + l * .2f, z = (i < 3 - l ? -.2f : .2f) * (1 - l * .3f);
                        KSphere(t, "Melon", new Vector3(x, .62f + l * .22f, z), new Vector3(.38f, .3f, .3f), melon).transform.localRotation = Quaternion.Euler(0, 90 + Jitter(20), 0);
                    }
                MeshNode(t, "Slice", Lathe(new[] { new Vector2(0, 0), new Vector2(.17f, .02f), new Vector2(.19f, .08f), new Vector2(.18f, .1f), new Vector2(0, .1f) }, 14), new Vector3(.45f, 1.02f, -.3f), KColor("E0453A", .5f), Quaternion.Euler(0, 0, 90));
                KBox(t, "Price", new Vector3(-.4f, .9f, -.5f), new Vector3(.3f, .2f, .02f), KColor("F2C23F", .3f), .01f);
                break;
            }
            case "claw-machine":
            {
                P(.44f, .44f, 2.4f);
                var pink = KColor("E86A9E", .55f);
                KBox(t, "Cabinet", new Vector3(0, .45f, 0), new Vector3(.82f, .9f, .82f), pink, .04f);
                KBox(t, "Control panel", new Vector3(0, .95f, -.36f), new Vector3(.7f, .1f, .16f), KNavy(), .02f, 0, -15);
                KBox(t, "Joystick", new Vector3(-.15f, 1.04f, -.38f), new Vector3(.03f, .1f, .03f), KBlack(), .01f);
                KSphere(t, "Knob", new Vector3(-.15f, 1.1f, -.38f), Vector3.one * .06f, KColor("E15533", .8f));
                KSphere(t, "Button", new Vector3(.15f, 1.0f, -.38f), new Vector3(.08f, .03f, .08f), KColor("F2B03D", .8f));
                foreach (var x in new[] { -.39f, .39f }) foreach (var z in new[] { -.39f, .39f }) KBox(t, "Post", new Vector3(x, 1.4f, z), new Vector3(.04f, 1.0f, .04f), KGold(), .01f);
                foreach (var face in new[] { 0, 90, 180, 270 }) KBox(t, "Glass", Quaternion.Euler(0, face, 0) * new Vector3(0, 1.4f, -.39f), new Vector3(.76f, .96f, .01f), KGlass(), .002f, face);
                KBox(t, "Roof", new Vector3(0, 1.94f, 0), new Vector3(.86f, .1f, .86f), pink, .03f);
                KBox(t, "Marquee", new Vector3(0, 2.12f, -.3f), new Vector3(.8f, .26f, .06f), KNavy(), .03f);
                KLetters(t, "PEGUE!", new Vector3(0, 2.12f, -.34f), .012f);
                string[] colors = { "F2B03D", "2E8CAE", "5DA637", "FFFFFF", "8E6CCF" };
                for (int i = 0; i < 14; i++) KSphere(t, "Plush", new Vector3(Jitter(.28f), .98f + Mathf.Abs(Jitter(.1f)), Jitter(.28f)), Vector3.one * .14f, KColor(colors[i % colors.Length], .2f));
                var claw = Group(t, "Anim Spin"); claw.localPosition = new Vector3(.1f, 1.7f, .05f);
                KBox(claw, "Cable", new Vector3(0, .1f, 0), new Vector3(.01f, .2f, .01f), KBlack(), .002f);
                for (int k = 0; k < 3; k++) KBox(claw, "Finger", Quaternion.Euler(0, k * 120, 0) * new Vector3(.04f, -.05f, 0), new Vector3(.015f, .12f, .015f), KChrome(), .004f, k * 120, 0).transform.localRotation = Quaternion.Euler(0, k * 120, 20);
                for (int i = 0; i < 8; i++)
                {
                    var blink = Group(t, "Anim Blink"); blink.localPosition = new Vector3(-.36f + i * .103f, 1.96f, -.44f);
                    KSphere(blink, "Bulb", Vector3.zero, Vector3.one * .045f, KGlow(i % 2 == 0 ? "FFE066" : "FF6FA8"));
                }
                break;
            }
            case "atm":
            {
                P(.38f, .34f, 2.1f);
                var teal = KColor("2E8CAE", .5f);
                KBox(t, "Body", new Vector3(0, .8f, .04f), new Vector3(.7f, 1.6f, .6f), KSteel(), .04f);
                KBox(t, "Fascia", new Vector3(0, 1.0f, -.27f), new Vector3(.62f, .9f, .04f), teal, .02f);
                KBox(t, "Screen", new Vector3(0, 1.25f, -.3f), new Vector3(.36f, .26f, .02f), KGlow("7BD3F7"), .01f, 0, -10);
                KBox(t, "Keypad", new Vector3(-.1f, .92f, -.33f), new Vector3(.2f, .03f, .14f), KBlack(), .006f, 0, -20);
                KBox(t, "Card slot", new Vector3(.18f, 1.0f, -.3f), new Vector3(.1f, .04f, .03f), KGlow("5DA637"), .006f);
                KBox(t, "Cash slot", new Vector3(0, .72f, -.3f), new Vector3(.3f, .04f, .03f), KBlack(), .006f);
                KBox(t, "Top sign", new Vector3(0, 1.75f, -.1f), new Vector3(.7f, .22f, .1f), KNavy(), .03f);
                KLetters(t, "24H", new Vector3(0, 1.75f, -.16f), .012f);
                break;
            }
            case "digital-totem":
            {
                P(.34f, .2f, 2.2f);
                KBox(t, "Base", new Vector3(0, .04f, 0), new Vector3(.6f, .08f, .34f), KGold(), .02f);
                KBox(t, "Frame", new Vector3(0, 1.0f, 0), new Vector3(.62f, 1.84f, .12f), KNavy(), .04f);
                var scroll = Group(t, "Anim Scroll");
                var screen = GameObject.CreatePrimitive(PrimitiveType.Quad); UnityEngine.Object.DestroyImmediate(screen.GetComponent<Collider>());
                screen.name = "Screen"; screen.transform.SetParent(scroll, false); screen.transform.localPosition = new Vector3(0, 1.05f, -.065f); screen.transform.localScale = new Vector3(.52f, 1.56f, 1);
                screen.GetComponent<Renderer>().sharedMaterial = KScreen();
                KBox(t, "Crest", new Vector3(0, 1.97f, 0), new Vector3(.64f, .06f, .14f), KGold(), .01f);
                break;
            }
        }
    }

    static void Cart(Transform parent, Vector3 at)
    {
        var cart = Group(parent, "Cart"); cart.localPosition = at;
        var wire = KChrome();
        KBox(cart, "Basket floor", new Vector3(0, .5f, 0), new Vector3(.5f, .02f, .7f), wire, .004f);
        foreach (var x in new[] { -.25f, .25f }) KBox(cart, "Basket side", new Vector3(x, .68f, 0), new Vector3(.015f, .36f, .7f), Transparent("IK_Wire", new Color(.8f, .83f, .86f, .55f)), .002f);
        KBox(cart, "Basket front", new Vector3(0, .68f, .35f), new Vector3(.5f, .36f, .015f), Transparent("IK_Wire", new Color(.8f, .83f, .86f, .55f)), .002f);
        KBox(cart, "Handle", new Vector3(0, .95f, -.4f), new Vector3(.52f, .035f, .035f), KColor("D8423A", .6f), .01f);
        foreach (var x in new[] { -.2f, .2f }) { KBox(cart, "Frame", new Vector3(x, .3f, 0), new Vector3(.02f, .5f, .02f), wire, .004f); KBox(cart, "Push bar", new Vector3(x, .82f, -.33f), new Vector3(.02f, .28f, .02f), wire, .004f, 0, 20); }
        foreach (var x in new[] { -.2f, .2f }) foreach (var z in new[] { -.28f, .28f })
                MeshNode(cart, "Wheel", Lathe(new[] { new Vector2(.05f, 0), new Vector2(.05f, .03f) }, 10), new Vector3(x - .015f, .05f, z), KBlack(), Quaternion.Euler(0, 0, 90));
    }
}
