using System;
using System.Collections.Generic;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

// The market building and its growth, in the navy / brushed-gold / white-light palette:
// * "Market Shell": our own textured, resizable building (CheckoutMarketShell) that replaces the supplied
//   MarketStructure mesh and the old entrance steps.
// * "Market Stage Dressing": what each paid expansion adds (corner shop -> neighbourhood market ->
//   supermarket -> big supermarket -> hypermarket), authored in the unprojected market space (walls at
//   x ±9.4 / z ±7.4, floor .74) and re-placed for the bought stage by CheckoutStageDressing.
// * The construction timelapse (CheckoutStageConstruction) that plays on every growth.
public static partial class CheckoutMarketStagesBuilder
{
    const string ShellName = "Market Shell", RootName = "Market Stage Dressing";
    const string Folder = "Assets/Art/MarketStages/";
    const float Floor = .74f, Ground = .13f, WallTop = 3.23f, HalfX = 9.4f, HalfZ = 7.4f, DoorX = -1.75f;
    // Same stage sizes as the app (src/services/simulator-layout.ts) and the Expansion Preview window.
    public static readonly float[,] Scales = { { .82f, .72f }, { .96f, .82f }, { 1.1f, .92f }, { 1.24f, 1.03f }, { 1.38f, 1.14f } };
    static readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
    static Transform root;
    static Font font;

    [MenuItem("Supermarket/Build market stages (facades + timelapse)")]
    public static void Build()
    {
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation || !simulation.world) throw new InvalidOperationException("Open the Supermarket scene first.");
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        var world = simulation.world;
        materials.Clear();
        if (!AssetDatabase.IsValidFolder("Assets/Art/MarketStages")) AssetDatabase.CreateFolder("Assets/Art", "MarketStages");
        font = Resources.Load<Font>("MarketBold") ?? Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");

        BuildShell(world);

        var old = world.Find(RootName); if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        root = new GameObject(RootName).transform;
        root.SetParent(world, false);
        // The world root is turned 180°: author the dressing in plain world axes.
        root.rotation = Quaternion.identity; root.position = Vector3.zero;
        var dressing = root.gameObject.AddComponent<CheckoutStageDressing>();
        var show = root.gameObject.AddComponent<CheckoutStageConstruction>();
        SetupConstruction(show);

        Stage0(); Stage1(); Stage2(); Stage3(); Stage4();
        Interior();
        dressing.external = ClearPlaza(world);
        BuildStorages(world);
        BuildConstructionKit(show);

        foreach (var item in root.GetComponentsInChildren<CheckoutStageItem>(true)) item.Capture();
        foreach (var renderer in root.GetComponentsInChildren<Renderer>(true))
            if (renderer.GetComponent<TextMesh>() || renderer.transform.position.y > 2.6f && renderer.transform.position.y < 3.6f && renderer.bounds.size.y < .5f) renderer.shadowCastingMode = ShadowCastingMode.Off;
        // The saved scene is the unprojected base map (scale 1).
        dressing.Apply(null, 3, false);
        EditorSceneManager.MarkSceneDirty(world.gameObject.scene);
        EditorSceneManager.SaveScene(world.gameObject.scene);
        AssetDatabase.SaveAssets();
        Debug.Log("CHECKOUT_MARKET_STAGES_BUILT items=" + root.GetComponentsInChildren<CheckoutStageItem>(true).Length + " plazaCleared=" + dressing.external.Length);
    }

    // ------------------------------------------------------------------ building shell
    static void BuildShell(Transform world)
    {
        var old = world.Find(ShellName); if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        var shellRoot = new GameObject(ShellName).transform;
        shellRoot.SetParent(world, false);
        shellRoot.rotation = Quaternion.identity; shellRoot.position = Vector3.zero;
        var shell = shellRoot.gameObject.AddComponent<CheckoutMarketShell>();
        shell.navy = Navy(); shell.plaster = Tri("MS_Plaster", "MS_Plaster", 2f, .15f);
        shell.limestone = Limestone(); shell.gold = Gold(); shell.floorTiles = Tri("MS_FloorTiles", "MS_FloorTiles", 2.4f, .7f);
        shell.pavers = Tri("MS_Pavers", "MS_Pavers", 1.6f, .2f); shell.led = Led();
        shell.darkMetal = Park("castiron", "ShellDarkMetal", .45f, .6f);
        shell.soil = Park("soil", "ShellSoil", .05f, 0); shell.flowers = Park("flowers", "ShellFlowers", .1f, 0);
        shell.glass = Glass(); shell.font = font; shell.fontMaterial = font.material;
        shell.Apply(new MarketLayout());
        foreach (var r in shellRoot.GetComponentsInChildren<Renderer>(true))
            if (r.name.StartsWith("Floor") || r.name.StartsWith("Plinth") || r.name.StartsWith("Step") || r.name.StartsWith("Landing") || r.name.Contains("LED") || r.name.Contains("light") || r.name.StartsWith("Lantern"))
                r.shadowCastingMode = r.name.StartsWith("Floor") || r.name.StartsWith("Landing") ? ShadowCastingMode.Off : r.shadowCastingMode;
        // Hide the supplied building mesh and the old entrance in the saved scene too.
        foreach (var name in new[] { "Building", "City Detail Repairs" })
        {
            var t = world.Find(name);
            if (t) foreach (var r in t.GetComponentsInChildren<Renderer>(true)) r.forceRenderingOff = true;
        }
    }

    // ------------------------------------------------------------------ stage looks
    // 0 · Mercadinho: striped awning over the door, a wooden name board with gold letters, crates outside.
    static void Stage0()
    {
        var awning = Item("S0 door awning", new Vector3(DoorX, 2.55f, -HalfZ - .55f), 0, 1, stretchX: true);
        Awning(awning, 5.4f, 1.1f);
        var board = Item("S0 name board", new Vector3(0, WallTop + .13f, HalfZ - .25f), 0, 0);
        Box(board, "Post L", new Vector3(-1.8f, .45f, .12f), new Vector3(.14f, .9f, .14f), Wood());
        Box(board, "Post R", new Vector3(1.8f, .45f, .12f), new Vector3(.14f, .9f, .14f), Wood());
        Box(board, "Board", new Vector3(0, .8f, 0), new Vector3(4.2f, .8f, .12f), Wood());
        Box(board, "Board face", new Vector3(0, .8f, -.05f), new Vector3(3.95f, .6f, .06f), Navy());
        Box(board, "Board trim", new Vector3(0, 1.22f, -.02f), new Vector3(4.3f, .06f, .16f), Gold());
        Letters3D(board, "MERCADINHO", new Vector3(0, .8f, -.09f), .058f);
        Bulbs(board, new Vector3(-1.9f, 1.3f, -.06f), new Vector3(1.9f, 1.3f, -.06f), 9);
        var crates = Item("S0 pavement crates", new Vector3(5.7f, Ground, -HalfZ - .7f), 0, 1);
        Model(crates, "VegetableCrate", Vector3.zero, new Vector3(1.2f, .8f, .7f), 0);
        var chalk = Item("S0 chalkboard", new Vector3(-6.3f, Ground, -HalfZ - 1.2f), 0, 1);
        Chalkboard(chalk, "OFERTAS");
    }

    // 1 · Mercado do bairro: a long striped awning and a lit name board on the back wall.
    static void Stage1()
    {
        var board = Item("S1 rear sign", new Vector3(0, WallTop + .13f, HalfZ - .25f), 1, 1);
        Box(board, "Post L", new Vector3(-3.3f, .6f, .15f), new Vector3(.3f, 1.2f, .3f), Limestone());
        Box(board, "Post R", new Vector3(3.3f, .6f, .15f), new Vector3(.3f, 1.2f, .3f), Limestone());
        Box(board, "Panel", new Vector3(0, 1.3f, 0), new Vector3(7.6f, 1.3f, .2f), Navy());
        Box(board, "Panel top", new Vector3(0, 1.98f, 0), new Vector3(7.8f, .08f, .3f), Gold());
        Box(board, "Panel bottom", new Vector3(0, .62f, 0), new Vector3(7.8f, .08f, .3f), Gold());
        Letters3D(board, "MERCADO DO BAIRRO", new Vector3(0, 1.3f, -.11f), .072f);
        Bulbs(board, new Vector3(-3.7f, 2.12f, -.05f), new Vector3(3.7f, 2.12f, -.05f), 16);
        var planters = Item("S1 front planters", new Vector3(7.4f, Ground, -HalfZ - .55f), 1, 4);
        Model(planters, "FlowerPlanter", Vector3.zero, new Vector3(1.6f, .8f, .6f), 0);
    }

    // 2 · Supermercado: a navy parapet with gold cornice and big gold letters, an entrance canopy,
    // a totem and flags.
    static void Stage2()
    {
        Parapet("S2 rear facade", 2, 3, 1.7f, false);
        Letters("S2 name", "SUPERMERCADO", 2, 3, 1.7f);
        Canopy("S2 entrance canopy", 2, 3, 6.8f, 2.1f, "SUPERMERCADO", glass: false);
        Totem("S2 totem", 2, 3, 4.2f, "SUPER", new Vector3(HalfX + 1.3f, Ground, HalfZ - 2f), attachEast: true);
        Flags("S2 flags", 2, 3, new Vector3(HalfX + .9f, Ground, 2.6f), 3);
    }

    // 3 · Supermercado maior: a clock tower, a side parapet and a street market by the east wall.
    static void Stage3()
    {
        Tower("S3 clock tower", new Vector3(-HalfX + .7f, WallTop, HalfZ - .7f), 3, 3, 4.4f);
        SideParapet("S3 west parapet", 3, 3, 1.1f);
        var stand = Item("S3 street market", new Vector3(HalfX + 1.6f, Ground, -3.4f), 3, 3, attachEast: true);
        Model(stand, "FruitMarketStand", Vector3.zero, new Vector3(2.0f, 1.8f, 2.4f), 90);
        var crates = Item("S3 street crates", new Vector3(HalfX + 1.2f, Ground, -5.8f), 3, 3, attachEast: true);
        Model(crates, "VegetableCrate", Vector3.zero, new Vector3(1.2f, .8f, .7f), 90);
    }

    // 4 · Hipermercado: a taller facade with marquee lights, twin towers, a glass canopy along the
    // whole front, a tall lit totem and a sidewalk café by the east corner (the shop now reaches the street).
    static void Stage4()
    {
        Parapet("S4 rear facade", 4, 4, 2.4f, true);
        Letters("S4 name", "HIPERMERCADO", 4, 4, 2.4f);
        Tower("S4 tower west", new Vector3(-HalfX + .7f, WallTop, HalfZ - .7f), 4, 4, 5.4f);
        SideParapet("S4 west parapet", 4, 4, 1.6f);
        Tower("S4 tower east", new Vector3(HalfX - .7f, WallTop, HalfZ - .7f), 4, 4, 5.4f);
        Canopy("S4 glass canopy", 4, 4, 9.4f, 2.2f, "HIPERMERCADO", glass: true);
        Totem("S4 totem", 4, 4, 6.2f, "HIPER", new Vector3(8.7f, Ground, -HalfZ - 1.25f), attachEast: false);
        Cafe();
        PlazaCafe();
    }

    // ------------------------------------------------------------------ inside the shop
    static void Interior()
    {
        var mat = Item("Entrance mat", new Vector3(DoorX, Floor + .006f, -HalfZ + 1.05f), 0, 4);
        Box(mat, "Mat", Vector3.zero, new Vector3(2.6f, .012f, 1.1f), Navy());
        Box(mat, "Mat border", new Vector3(0, -.001f, 0), new Vector3(2.75f, .01f, 1.25f), Gold());
        Letters3D(mat, "BEM-VINDO", new Vector3(0, .012f, 0), .02f, flat: true);
        var promo = Item("Promo pallet", new Vector3(-8.2f, Ground, -HalfZ - 1.3f), 0, 4);
        PromoPallet(promo, "OFERTA");
        Bunting("Bunting A", -1.2f, 0, 4);
        // Pendant lamps over the shop floor from the supermarket on: gold shades with white light.
        foreach (var x in new[] { -5.4f, -1.8f, 1.8f, 5.4f })
            foreach (var z in new[] { -5.8f, -2.8f, 1.2f })
            {
                var lamp = Item("Pendant " + x.ToString("0.0") + "," + z.ToString("0.0"), new Vector3(x, 3.1f, z), 2, 4);
                Box(lamp, "Wire", new Vector3(0, .35f, 0), new Vector3(.015f, .7f, .015f), Gold());
                Cyl(lamp, "Shade", new Vector3(0, -.08f, 0), .26f, .16f, Gold());
                Cyl(lamp, "Glow", new Vector3(0, -.1f, 0), .2f, .03f, Led());
            }
        Bunting("Bunting B", 2.6f, 2, 4);
        Bunting("Bunting C", -4.3f, 4, 4);
        Banner("Banner mercearia", new Vector3(-1.6f, 3.35f, .3f), 2, 4, "MERCEARIA");
        Banner("Banner bebidas", new Vector3(2f, 3.35f, -1.2f), 2, 4, "BEBIDAS");
        Banner("Banner hortifruti", new Vector3(6.55f, 3.35f, .45f), 3, 4, "HORTIFRUTI");
        DeptSign("PADARIA", new Vector3(-5.9f, 2.95f, HalfZ - .56f), 0, "D98E2B");
        DeptSign("QUEIJARIA", new Vector3(-1.75f, 2.95f, HalfZ - .56f), 0, "8E6CCF");
        DeptSign("PEIXARIA", new Vector3(1.5f, 2.95f, HalfZ - .56f), 0, "2E86DE");
        DeptSign("AÇOUGUE", new Vector3(6.5f, 2.95f, HalfZ - .56f), 0, "D64541");
        DeptSign("BEBIDAS", new Vector3(-HalfX + .56f, 2.95f, -.45f), 270, "27AE60");
        DeptSign("SORVETES", new Vector3(-HalfX + .56f, 2.95f, -5.2f), 270, "E86A9E");
        DeptSign("ADEGA", new Vector3(8.2f, 2.8f, -2.3f), 0, "8E2240");
        // Promo islands in the open floor of the bigger shops (shoppers walk around them).
        var island = Item("Promo island", new Vector3(.9f, Floor, -2.8f), 2, 4, blocks: true);
        PromoPallet(island, "OFERTAS");
        var gondola = Item("Gondola island", new Vector3(5f, Floor, -2.75f), 3, 4, blocks: true);
        Model(gondola, "GroceryShelf", Vector3.zero, new Vector3(2.4f, 1.6f, .9f), 0);
        var gondolaSign = Item("Gondola sign", new Vector3(5f, 2.75f, -2.75f), 3, 4);
        Box(gondolaSign, "Board", Vector3.zero, new Vector3(1.5f, .36f, .05f), Navy());
        Letters3D(gondolaSign, "MERCEARIA", new Vector3(0, 0, -.04f), .016f);
        var path = Item("Floor path", new Vector3(DoorX, Floor + .008f, -4.3f), 2, 4, stretchZ: true);
        Box(path, "Path", Vector3.zero, new Vector3(1.3f, .01f, 4.6f), Navy());
        Box(path, "Edge L", new Vector3(-.68f, .002f, 0), new Vector3(.08f, .01f, 4.6f), Gold());
        Box(path, "Edge R", new Vector3(.68f, .002f, 0), new Vector3(.08f, .01f, 4.6f), Gold());
    }

    // ------------------------------------------------------------------ pieces
    static void Parapet(string name, int from, int to, float height, bool marquee)
    {
        var item = Item(name, new Vector3(0, WallTop, HalfZ - .22f), from, to, stretchX: true);
        Box(item, "Wall", new Vector3(0, height * .5f, 0), new Vector3(HalfX * 2 + .1f, height, .36f), Navy());
        Box(item, "Cornice", new Vector3(0, height + .09f, -.03f), new Vector3(HalfX * 2 + .3f, .18f, .52f), Gold());
        Box(item, "Base trim", new Vector3(0, .06f, -.2f), new Vector3(HalfX * 2 + .1f, .12f, .06f), Gold());
        Box(item, "LED", new Vector3(0, height - .1f, -.2f), new Vector3(HalfX * 2 + .1f, .06f, .04f), Led());
        // Plain navy face (no pilasters) so the big name and the cart logo read cleanly.
        if (marquee) Bulbs(item, new Vector3(-HalfX + .2f, height + .26f, -.2f), new Vector3(HalfX - .2f, height + .26f, -.2f), 44);
    }

    static void SideParapet(string name, int from, int to, float height)
    {
        var item = Item(name, new Vector3(-HalfX + .22f, WallTop, 0), from, to, stretchZ: true);
        Box(item, "Wall", new Vector3(0, height * .5f, 0), new Vector3(.36f, height, HalfZ * 2 + .1f), Navy());
        Box(item, "Cornice", new Vector3(.03f, height + .09f, 0), new Vector3(.52f, .18f, HalfZ * 2 + .3f), Gold());
        Box(item, "LED", new Vector3(-.2f, height - .1f, 0), new Vector3(.04f, .06f, HalfZ * 2), Led());
    }

    static void Letters(string name, string text, int from, int to, float height)
    {
        var item = Item(name, new Vector3(.8f, WallTop + height * .5f, HalfZ - .5f), from, to);
        Letters3D(item, text, Vector3.zero, height * .05f);
        // Round gold logo with a cart.
        float x = -(text.Length * height * .19f + height * .45f);
        var disc = Box(item, "Logo", new Vector3(x, 0, .02f), Vector3.one, Gold(), PrimitiveType.Cylinder);
        disc.transform.localRotation = Quaternion.Euler(90, 0, 0);
        disc.transform.localScale = new Vector3(height * .7f, .05f, height * .7f);
        var face = Box(item, "Logo face", new Vector3(x, 0, -.035f), Vector3.one, Navy(), PrimitiveType.Cylinder);
        face.transform.localRotation = Quaternion.Euler(90, 0, 0);
        face.transform.localScale = new Vector3(height * .58f, .02f, height * .58f);
        Cart(item, new Vector3(x, -height * .02f, -.06f), height * .28f);
    }

    // A tiny shopping cart icon in gold, facing south.
    static void Cart(Transform parent, Vector3 at, float s)
    {
        var g = Gold();
        Box(parent, "Cart basket", at + new Vector3(0, s * .15f, 0), new Vector3(s * 1.1f, s * .6f, .03f), g);
        Box(parent, "Cart handle", at + new Vector3(-s * .7f, s * .5f, 0), new Vector3(s * .5f, s * .1f, .03f), g);
        foreach (var dx in new[] { -.35f, .35f })
            Box(parent, "Cart wheel", at + new Vector3(s * dx, -s * .35f, 0), new Vector3(s * .22f, s * .22f, .03f), g, PrimitiveType.Sphere);
    }

    static void Canopy(string name, int from, int to, float width, float depth, string label, bool glass)
    {
        // Only around the door: the low front wall must keep the shop floor in view.
        var item = Item(name, new Vector3(DoorX, 3.05f, -HalfZ - .25f - depth * .5f), from, to, stretchX: true);
        Box(item, "Roof", Vector3.zero, new Vector3(width, .08f, depth), glass ? Glass() : Navy());
        Box(item, "Frame", new Vector3(0, .02f, 0), new Vector3(width + .1f, .06f, depth + .1f), Navy());
        if (glass) UnityEngine.Object.DestroyImmediate(item.Find("Frame").gameObject);
        Box(item, "Fascia", new Vector3(0, -.06f, -depth * .5f), new Vector3(width + .1f, .36f, .12f), Navy());
        Box(item, "Fascia trim", new Vector3(0, .12f, -depth * .5f - .01f), new Vector3(width + .14f, .05f, .14f), Gold());
        Box(item, "Fascia LED", new Vector3(0, -.22f, -depth * .5f - .04f), new Vector3(width, .04f, .04f), Led());
        Box(item, "Edge L", new Vector3(-width * .5f, -.04f, 0), new Vector3(.1f, .28f, depth), Navy());
        Box(item, "Edge R", new Vector3(width * .5f, -.04f, 0), new Vector3(.1f, .28f, depth), Navy());
        int columns = glass ? 4 : 2;
        for (int i = 0; i < columns; i++)
        {
            float x = Mathf.Lerp(-width * .5f + .2f, width * .5f - .2f, i / (float)(columns - 1));
            if (glass && Mathf.Abs(x) < 3.4f) continue;
            float h = 3.05f - Ground;
            Box(item, "Column", new Vector3(x, -h * .5f, -depth * .5f + .12f), new Vector3(.18f, h, .18f), Navy());
            Box(item, "Column base", new Vector3(x, -h + .15f, -depth * .5f + .12f), new Vector3(.3f, .3f, .3f), Limestone());
            Box(item, "Column cap", new Vector3(x, -.12f, -depth * .5f + .12f), new Vector3(.26f, .08f, .26f), Gold());
            Box(item, "Downlight", new Vector3(x, -.05f, -.05f), new Vector3(.3f, .03f, .3f), Led());
        }
        if (label != null) Letters3D(item, label, new Vector3(0, -.06f, -depth * .5f - .07f), .028f);
    }

    static void Totem(string name, int from, int to, float height, string label, Vector3 at, bool attachEast)
    {
        var item = Item(name, at, from, to, attachEast: attachEast);
        Box(item, "Base", new Vector3(0, .22f, 0), new Vector3(1.6f, .44f, 1.1f), Limestone());
        Box(item, "Base cap", new Vector3(0, .46f, 0), new Vector3(1.66f, .05f, 1.16f), Gold());
        Box(item, "Body", new Vector3(0, height * .5f + .45f, 0), new Vector3(1.15f, height, .55f), Navy());
        Box(item, "Side L", new Vector3(-.6f, height * .5f + .45f, 0), new Vector3(.08f, height, .6f), Gold());
        Box(item, "Side R", new Vector3(.6f, height * .5f + .45f, 0), new Vector3(.08f, height, .6f), Gold());
        Box(item, "Lightbox", new Vector3(0, height - .45f, -.29f), new Vector3(.95f, .95f, .04f), Led());
        Letters3D(item, label, new Vector3(0, height - .45f, -.32f), .024f, face: new Color(.12f, .18f, .33f), side: new Color(.08f, .1f, .18f));
        Letters3D(item, "ABERTO", new Vector3(0, height - 1.4f, -.3f), .014f);
        var star = Box(item, "Star", new Vector3(0, height + .85f, 0), Vector3.one, GoldGlow(), PrimitiveType.Sphere);
        star.transform.localScale = new Vector3(.62f, .62f, .2f);
        Box(item, "Top cap", new Vector3(0, height + .47f, 0), new Vector3(1.25f, .06f, .65f), Gold());
        item.localRotation = Quaternion.Euler(0, -30, 0);
    }

    static void Tower(string name, Vector3 at, int from, int to, float height)
    {
        var item = Item(name, at, from, to);
        Box(item, "Shaft", new Vector3(0, height * .5f, 0), new Vector3(1.7f, height, 1.7f), Limestone());
        Box(item, "Band", new Vector3(0, height * .55f, 0), new Vector3(1.78f, .14f, 1.78f), Gold());
        Box(item, "Crown", new Vector3(0, height + .25f, 0), new Vector3(1.9f, .5f, 1.9f), Navy());
        Box(item, "Crown trim", new Vector3(0, height + .52f, 0), new Vector3(2.02f, .1f, 2.02f), Gold());
        Box(item, "Crown LED", new Vector3(0, height + .05f, 0), new Vector3(1.94f, .05f, 1.94f), Led());
        var roof = Box(item, "Roof", new Vector3(0, height + 1.05f, 0), Vector3.one, Navy(), PrimitiveType.Cylinder);
        roof.transform.localScale = new Vector3(1.5f, .5f, 1.5f);
        var spire = Box(item, "Spire", new Vector3(0, height + 1.85f, 0), Vector3.one, GoldGlow(), PrimitiveType.Sphere);
        spire.transform.localScale = new Vector3(.34f, .34f, .34f);
        foreach (var face in new[] { (new Vector3(0, 0, -.87f), Quaternion.Euler(90, 0, 0)), (new Vector3(.87f, 0, 0), Quaternion.Euler(0, 0, 90)) })
        {
            var clock = Box(item, "Clock", new Vector3(0, height - .8f, 0) + face.Item1, Vector3.one, Led(), PrimitiveType.Cylinder);
            clock.transform.localRotation = face.Item2; clock.transform.localScale = new Vector3(1.05f, .04f, 1.05f);
            var ring = Box(item, "Clock ring", new Vector3(0, height - .8f, 0) + face.Item1 * .99f, Vector3.one, Gold(), PrimitiveType.Cylinder);
            ring.transform.localRotation = face.Item2; ring.transform.localScale = new Vector3(1.2f, .03f, 1.2f);
        }
        Box(item, "Hand H", new Vector3(0, height - .68f, -.92f), new Vector3(.06f, .28f, .02f), Navy());
        var minute = Box(item, "Hand M", new Vector3(.12f, height - .8f, -.92f), new Vector3(.05f, .42f, .02f), Navy());
        minute.transform.localRotation = Quaternion.Euler(0, 0, -70);
        for (int i = 0; i < 3; i++)
            Box(item, "Window", new Vector3(.86f, .7f + i * 1.05f, 0), new Vector3(.03f, .6f, .5f), Glass());
    }

    static void Flags(string name, int from, int to, Vector3 at, int count)
    {
        var item = Item(name, at, from, to, attachEast: true);
        var colors = new[] { Navy(), Gold(), Canvas() };
        for (int i = 0; i < count; i++)
        {
            var z = -i * 2.2f;
            Box(item, "Pole", new Vector3(0, 2.6f, z), new Vector3(.08f, 5.2f, .08f), Park("brushed", "StageSteel", .6f, .8f));
            Box(item, "Knob", new Vector3(0, 5.25f, z), new Vector3(.15f, .15f, .15f), GoldGlow(), PrimitiveType.Sphere);
            var flag = Box(item, "Flag", new Vector3(.62f, 4.6f, z), new Vector3(1.2f, .8f, .03f), colors[i % colors.Length]);
            flag.transform.localRotation = Quaternion.Euler(0, 35, 0);
        }
    }

    // Sidewalk café along the front, by the east corner: only while the small storage's truck yard still
    // fills the strip behind the shop (with the central warehouse the café moves there, see PlazaCafe).
    static void Cafe()
    {
        var item = Item("S4 sidewalk cafe", new Vector3(4.6f, Ground, -HalfZ - 1.15f), 4, 4);
        item.GetComponent<CheckoutStageItem>().centralWarehouse = -1;
        Box(item, "Deck", new Vector3(0, .04f, 0), new Vector3(5.8f, .08f, 1.7f), Wood());
        Box(item, "Rail", new Vector3(0, .5f, -.82f), new Vector3(5.8f, .06f, .06f), Gold());
        for (int k = 0; k < 7; k++) Box(item, "Rail post", new Vector3(-2.85f + k * .95f, .27f, -.82f), new Vector3(.06f, .5f, .06f), Navy());
        for (int i = 0; i < 3; i++)
        {
            float x = -1.9f + i * 1.9f;
            Cyl(item, "Table", new Vector3(x, .08f, 0), .06f, .7f, Navy());
            Cyl(item, "Table top", new Vector3(x, .76f, 0), .42f, .04f, Limestone());
            Cyl(item, "Chair", new Vector3(x - .62f, .08f, 0), .19f, .42f, Navy());
            Cyl(item, "Chair", new Vector3(x + .62f, .08f, 0), .19f, .42f, Navy());
            Cyl(item, "Umbrella pole", new Vector3(x, .8f, 0), .03f, 1.5f, Gold());
            var shade = Cyl(item, "Umbrella", new Vector3(x, 2.25f, 0), .8f, .14f, i % 2 == 0 ? Canvas() : NavyCanvas());
            Box(item, "Umbrella tip", new Vector3(x, 2.46f, 0), Vector3.one * .1f, GoldGlow(), PrimitiveType.Sphere);
        }
        Letters3D(item, "CAFÉ", new Vector3(3.1f, .85f, -.2f), .02f);
        Box(item, "Sign", new Vector3(3.1f, .85f, -.14f), new Vector3(.8f, .36f, .06f), Navy());
        Box(item, "Sign post", new Vector3(3.1f, .35f, -.12f), new Vector3(.06f, .7f, .06f), Gold());
    }

    // Café and social corner ("área de convivência") of the hypermarket, modelled in Blender (plaza-cafe in
    // scripts/blender/build_interior_kit.py): coffee kiosk, pergola terrace, lounge and garden on the strip
    // between the shop's back-east corner and the central warehouse's truck yard. Authored in world space for
    // the hypermarket (stage 4) layout: east of the rear stairs and the staff walkway, inside the plaza kerb.
    static void PlazaCafe()
    {
        var item = Item("S4 plaza cafe", new Vector3(14.15f, Ground - .02f, 21.0f), 4, 4);
        var stage = item.GetComponent<CheckoutStageItem>();
        stage.fixedPosition = true; stage.centralWarehouse = 1;
        const string path = "Assets/Art/Interior/Models/plaza-cafe.fbx";
        var importer = AssetImporter.GetAtPath(path) as ModelImporter;
        if (!importer) throw new InvalidOperationException("Missing " + path + " (run scripts/blender/build_interior_kit.py plaza-cafe).");
        importer.importNormals = ModelImporterNormals.Import; importer.addCollider = false; importer.importAnimation = false;
        importer.importCameras = false; importer.importLights = false; importer.animationType = ModelImporterAnimationType.None;
        importer.materialLocation = ModelImporterMaterialLocation.InPrefab; importer.bakeAxisConversion = false;
        importer.SaveAndReimport();
        var model = (GameObject)UnityEngine.Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(path), item, false);
        model.name = "Model"; model.transform.localPosition = Vector3.zero;
        foreach (var r in model.GetComponentsInChildren<Renderer>(true))
        {
            var mats = r.sharedMaterials;
            for (int i = 0; i < mats.Length; i++) mats[i] = KitRemap(mats[i]);
            r.sharedMaterials = mats; r.shadowCastingMode = ShadowCastingMode.On;
        }
    }

    static void Awning(Transform parent, float width, float depth, float gapCenter = 0, float gapWidth = 0)
    {
        var canvas = Canvas3D();
        var holder = new GameObject("Canvas").transform;
        holder.SetParent(parent, false);
        holder.localRotation = Quaternion.Euler(-22, 0, 0);
        void Piece(float a, float b)
        {
            if (b - a < .1f) return;
            float c = (a + b) * .5f, w = b - a;
            Box(holder, "Canvas", new Vector3(c, 0, 0), new Vector3(w, .05f, depth), canvas);
            Box(holder, "Valance", new Vector3(c, -.13f, -depth * .5f), new Vector3(w, .26f, .03f), canvas);
            Box(holder, "Valance trim", new Vector3(c, -.27f, -depth * .5f - .005f), new Vector3(w, .03f, .035f), Gold());
            Box(parent, "Bar", new Vector3(c, .32f, depth * .42f), new Vector3(w, .06f, .06f), Gold());
        }
        float left = -width * .5f, right = width * .5f;
        if (gapWidth > 0) { Piece(left, gapCenter - gapWidth * .5f); Piece(gapCenter + gapWidth * .5f, right); }
        else Piece(left, right);
    }

    static void Chalkboard(Transform parent, string text)
    {
        var front = Box(parent, "Front", new Vector3(0, .5f, -.12f), new Vector3(.62f, .92f, .04f), Mat("StageChalk", "22302B", .05f));
        front.transform.localRotation = Quaternion.Euler(-12, 0, 0);
        var frame = Box(parent, "Frame", new Vector3(0, .5f, -.1f), new Vector3(.7f, 1f, .03f), Wood());
        frame.transform.localRotation = Quaternion.Euler(-12, 0, 0);
        var back = Box(parent, "Back", new Vector3(0, .5f, .12f), new Vector3(.62f, .92f, .04f), Wood());
        back.transform.localRotation = Quaternion.Euler(12, 0, 0);
        var label = Text(parent, text, new Vector3(0, .62f, -.16f), 0, Color.white, .012f);
        label.transform.localRotation = Quaternion.Euler(-12, 0, 0);
    }

    static void PromoPallet(Transform parent, string label)
    {
        Box(parent, "Pallet", new Vector3(0, .07f, 0), new Vector3(1.2f, .14f, 1f), Wood());
        for (int i = 0; i < 4; i++)
            for (int j = 0; j < 2; j++)
                Box(parent, "Box", new Vector3(-.3f + (i % 2) * .6f, .34f + j * .42f, -.24f + (i / 2) * .48f), new Vector3(.56f, .4f, .44f), Park("canvas", "StageCardboard", .05f, 0, "C99A62"));
        Box(parent, "Sign post", new Vector3(0, 1.35f, 0), new Vector3(.05f, .5f, .05f), Gold());
        Box(parent, "Sign", new Vector3(0, 1.72f, 0), new Vector3(.95f, .42f, .05f), Navy());
        Letters3D(parent, label, new Vector3(0, 1.72f, -.04f), .018f);
    }

    static void Bunting(string name, float z, int from, int to)
    {
        var item = Item(name, new Vector3(0, 3.2f, z), from, to, stretchX: true);
        float span = HalfX * 2 - 1;
        Box(item, "String", Vector3.zero, new Vector3(span, .02f, .02f), Mat("StageString", "EDE6D8"));
        var colors = new[] { Navy(), Gold(), Mat("StageWhiteFlag", "F7F3EA", .2f) };
        int count = 26;
        for (int i = 0; i < count; i++)
        {
            float x = -span * .5f + (i + .5f) * span / count;
            float sag = -.25f * (1 - Mathf.Pow(2 * (x / span), 2));
            var flag = Box(item, "Pennant", new Vector3(x, sag - .14f, 0), new Vector3(.22f, .22f, .01f), colors[i % colors.Length]);
            flag.transform.localRotation = Quaternion.Euler(0, 0, 45);
        }
        // Little white lights along the string.
        for (int i = 0; i < 13; i++)
        {
            float x = -span * .5f + (i + .5f) * span / 13f;
            float sag = -.25f * (1 - Mathf.Pow(2 * (x / span), 2));
            Box(item, "Bulb", new Vector3(x, sag, 0), Vector3.one * .07f, Led(), PrimitiveType.Sphere);
        }
    }

    static void Banner(string name, Vector3 at, int from, int to, string text)
    {
        var item = Item(name, at, from, to);
        Box(item, "Wire L", new Vector3(-.7f, .45f, 0), new Vector3(.01f, .9f, .01f), Gold());
        Box(item, "Wire R", new Vector3(.7f, .45f, 0), new Vector3(.01f, .9f, .01f), Gold());
        Box(item, "Board", Vector3.zero, new Vector3(1.8f, .44f, .05f), Navy());
        Box(item, "Trim", new Vector3(0, -.24f, 0), new Vector3(1.84f, .04f, .07f), Gold());
        Letters3D(item, text, new Vector3(0, 0, -.04f), .02f);
    }

    static void DeptSign(string text, Vector3 at, float yaw, string accent)
    {
        var item = Item("Dept " + text, at, 0, 4);
        item.localRotation = Quaternion.Euler(0, yaw, 0);
        float w = text.Length * .24f + .6f;
        Box(item, "Board", Vector3.zero, new Vector3(w, .48f, .06f), Navy());
        Box(item, "Trim", new Vector3(0, .27f, 0), new Vector3(w + .04f, .05f, .08f), Gold());
        Box(item, "Accent", new Vector3(0, -.27f, 0), new Vector3(w + .04f, .07f, .08f), Mat("StageDept" + accent, accent, .3f));
        Letters3D(item, text, new Vector3(0, 0, -.05f), .03f);
    }

    static void Bulbs(Transform parent, Vector3 from, Vector3 to, int count)
    {
        for (int i = 0; i < count; i++)
            Box(parent, "Bulb", Vector3.Lerp(from, to, count == 1 ? .5f : i / (float)(count - 1)), Vector3.one * .11f, Led(), PrimitiveType.Sphere);
    }

    // Gold letters with depth: a few stacked TextMesh layers, darker towards the back.
    static void Letters3D(Transform parent, string value, Vector3 at, float size, bool flat = false, Color? face = null, Color? side = null)
    {
        var front = face ?? new Color(1f, .82f, .38f);
        var back = side ?? new Color(.55f, .36f, .1f);
        int layers = flat ? 1 : 5;
        for (int i = layers - 1; i >= 0; i--)
        {
            var t = Text(parent, value, at + new Vector3(0, 0, i * .012f), 0, i == 0 ? front : Color.Lerp(back, front, .25f), size);
            if (flat) t.transform.localRotation = Quaternion.Euler(90, 0, 0);
        }
    }

    // ------------------------------------------------------------------ plaza clearance
    // Street scenery that stands where the growing shop or one of its stage pieces goes is hidden from that stage on.
    static CheckoutStageItem[] ClearPlaza(Transform world)
    {
        var result = new List<CheckoutStageItem>();
        var lots = new HashSet<GameObject>((world.GetComponentInChildren<CheckoutExpansionNeighborhood>(true)?.lots ?? new CheckoutExpansionNeighborhood.Lot[0]).Select(l => l.building).Where(g => g));
        var candidates = new List<Transform>();
        foreach (var group in new[] { "Harbour Quay Plaza", "City Establishments", "Landscape Models", "Individual Street Furniture" })
        {
            var g = world.Find(group); if (!g) continue;
            foreach (var old in g.GetComponentsInChildren<CheckoutStageItem>(true)) UnityEngine.Object.DestroyImmediate(old);
            foreach (Transform child in g)
                if (group != "Landscape Models" || (child.name.StartsWith("City Tree") && !child.name.StartsWith("City Tree 03"))) candidates.Add(child); // Tree 03 belongs to the park purchase
        }
        var pieces = root.GetComponentsInChildren<CheckoutStageItem>(true).Where(i => i.transform.parent == root && !i.name.StartsWith("Bunting") && !i.name.StartsWith("Banner") && !i.name.StartsWith("Dept") && i.name != "Entrance mat").ToArray();
        foreach (var child in candidates)
        {
            if (lots.Contains(child.gameObject)) continue;
            var renderers = child.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) continue;
            var b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
            if (b.size.x > 12 || b.size.z > 12) continue; // paving, not furniture
            var flat = new Rect(b.min.x, b.min.z, b.size.x, b.size.z);
            int first = 99;
            for (int stage = 0; stage <= 4 && first > 4; stage++)
            {
                var layout = new MarketLayout { stage = stage, widthScale = Scales[stage, 0], depthScale = Scales[stage, 1] };
                // The building itself (with its entrance steps) at this size.
                var lo = CheckoutMarketLayout.Project(new Vector3(-HalfX, 0, -HalfZ), layout); var hi = CheckoutMarketLayout.Project(new Vector3(HalfX, 0, HalfZ), layout);
                if (flat.Overlaps(Rect.MinMaxRect(lo.x - .5f, lo.z - .5f, hi.x + .5f, hi.z + .5f))) { first = stage; break; }
                var door = CheckoutMarketLayout.Project(new Vector3(DoorX, 0, 0), layout).x;
                if (flat.Overlaps(Rect.MinMaxRect(door - 3.2f, CheckoutMarketLayout.WorldAnchor.z - .3f, door + 3.2f, lo.z))) { first = stage; break; }
                foreach (var piece in pieces)
                {
                    if (!piece.Visible(stage)) continue;
                    var pr = piece.GetComponentsInChildren<Renderer>(true);
                    if (pr.Length == 0) continue;
                    var pb = pr[0].bounds; foreach (var r in pr) pb.Encapsulate(r.bounds);
                    var moved = CheckoutStageDressing.Place(piece, layout) - piece.transform.position;
                    float sx = piece.stretchX ? layout.widthScale : 1, sz = piece.stretchZ ? layout.depthScale : 1;
                    var at = Rect.MinMaxRect(pb.center.x + moved.x - pb.extents.x * sx - .4f, pb.center.z + moved.z - pb.extents.z * sz - .4f,
                        pb.center.x + moved.x + pb.extents.x * sx + .4f, pb.center.z + moved.z + pb.extents.z * sz + .4f);
                    if (flat.Overlaps(at)) { first = stage; break; }
                }
            }
            if (first > 4) continue;
            var marker = child.gameObject.AddComponent<CheckoutStageItem>();
            marker.fixedPosition = true; marker.minStage = 0; marker.maxStage = first - 1;
            result.Add(marker);
            Debug.Log("CHECKOUT_STAGE_CLEARS " + child.name + " from stage " + first);
        }
        return result.ToArray();
    }

    // ------------------------------------------------------------------ construction timelapse
    static void SetupConstruction(CheckoutStageConstruction show)
    {
        show.scaffoldMaterial = Park("brushed", "StageScaffold", .55f, .7f);
        show.plankMaterial = Wood();
        show.netMaterial = Transparent("StageSafetyNet", new Color(1f, .45f, .1f, .38f));
        show.craneMaterial = Park("paint", "StageCrane", .35f, .2f, "F2C230");
        show.craneDarkMaterial = Park("castiron", "StageCraneDark", .3f, .5f);
        show.dustMaterial = Particle("StageDust", "Legacy Shaders/Particles/Alpha Blended", AssetDatabase.GetBuiltinExtraResource<Texture2D>("Default-Particle.psd"));
        show.confettiMaterial = Particle("StageConfetti", "Legacy Shaders/Particles/Alpha Blended", null);
        show.sparkMaterial = Particle("StageSpark", "Legacy Shaders/Particles/Additive", AssetDatabase.GetBuiltinExtraResource<Texture2D>("Default-Particle.psd"));
        show.confettiMesh = Resources.GetBuiltinResource<Mesh>("Quad.fbx");
        show.titleFont = font;
        show.titleMaterial = font ? font.material : null;
    }

    static Material Particle(string name, string shader, Texture2D texture)
    {
        string path = Folder + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        var s = Shader.Find(shader);
        if (!material) { material = new Material(s); AssetDatabase.CreateAsset(material, path); }
        material.shader = s;
        if (texture) material.mainTexture = texture;
        if (material.HasProperty("_TintColor")) material.SetColor("_TintColor", new Color(.5f, .5f, .5f, .5f));
        EditorUtility.SetDirty(material);
        return material;
    }

    // ------------------------------------------------------------------ palette
    static Material Navy() => Tri("MS_NavyPanel", "MS_NavyPanel", 1.2f, .5f);
    static Material Limestone() => Tri("MS_Limestone", "MS_Limestone", 2.4f, .25f);
    static Material Gold() => Tri("MS_Gold", "MS_Gold", .9f, .7f, .25f);
    static Material Canvas3D() => Tri("MS_Awning", "MS_Awning", 1.2f, .2f);
    static Material Wood() => Park("wood", "StageWood", .25f, 0);
    static Material Canvas() => Mat("StageWhiteCanvas", "F7F3EA", .15f);
    static Material NavyCanvas() => Mat("StageNavyCanvas", "1D2B4F", .2f);
    static Material Led() => Mat("MS_LED", "FFFFFF", .5f, "FFFFFF");
    static Material GoldGlow() => Mat("MS_GoldGlow", "F2C45A", .8f, "C8942A");

    // World-space triplanar material from one of our textures (Assets/Art/MarketStages/Textures).
    static Material Tri(string name, string texture, float tiling, float gloss, float metallic = 0)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Folder + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("MarketDay/City Park Triplanar")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("MarketDay/City Park Triplanar");
        string albedo = Folder + "Textures/" + texture + "_albedo.png", normal = Folder + "Textures/" + texture + "_normal.png";
        ConfigureTexture(albedo, false); ConfigureTexture(normal, true);
        material.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(albedo));
        material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(normal));
        material.SetFloat("_Tiling", tiling); material.SetFloat("_BumpScale", 1f);
        material.SetFloat("_Glossiness", gloss); material.SetFloat("_Metallic", metallic);
        material.SetFloat("_Variation", .06f); material.SetVector("_Scroll", Vector4.zero);
        material.color = Color.white;
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static void ConfigureTexture(string path, bool normal)
    {
        var importer = AssetImporter.GetAtPath(path) as TextureImporter;
        if (!importer) throw new InvalidOperationException("Missing texture " + path);
        bool dirty = false;
        var type = normal ? TextureImporterType.NormalMap : TextureImporterType.Default;
        if (importer.textureType != type) { importer.textureType = type; dirty = true; }
        if (importer.wrapMode != TextureWrapMode.Repeat) { importer.wrapMode = TextureWrapMode.Repeat; dirty = true; }
        if (importer.sRGBTexture == normal) { importer.sRGBTexture = !normal; dirty = true; }
        if (importer.anisoLevel != 4) { importer.anisoLevel = 4; dirty = true; }
        if (dirty) importer.SaveAndReimport();
    }

    // One of the procedural city textures (CheckoutCityParkTextures), triplanar and optionally tinted.
    static Material Park(string kind, string name, float gloss, float metallic, string tint = null)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Folder + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("MarketDay/City Park Triplanar")); AssetDatabase.CreateAsset(material, path); }
        var surface = CheckoutCityParkTextures.Get(kind);
        material.shader = Shader.Find("MarketDay/City Park Triplanar");
        material.SetTexture("_MainTex", surface.albedo); material.SetTexture("_BumpMap", surface.normal);
        material.SetFloat("_Tiling", surface.tiling); material.SetFloat("_BumpScale", surface.bump);
        material.SetFloat("_Glossiness", Mathf.Clamp01(.35f + gloss)); material.SetFloat("_Metallic", metallic);
        material.SetFloat("_Variation", .1f); material.SetVector("_Scroll", Vector4.zero);
        material.color = tint != null ? MarketSimulation.C(tint) : Color.white;
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    // ------------------------------------------------------------------ helpers
    static Transform Item(string name, Vector3 basePosition, int from, int to, bool stretchX = false, bool stretchZ = false, bool blocks = false, bool attachEast = false)
    {
        var go = new GameObject(name);
        go.transform.SetParent(root, false);
        go.transform.position = basePosition;
        var item = go.AddComponent<CheckoutStageItem>();
        item.minStage = from; item.maxStage = to; item.stretchX = stretchX; item.stretchZ = stretchZ; item.blocksNavigation = blocks; item.attachEast = attachEast;
        return go.transform;
    }

    static GameObject Box(Transform parent, string name, Vector3 localPosition, Vector3 size, Material material, PrimitiveType type = PrimitiveType.Cube)
    {
        var go = GameObject.CreatePrimitive(type);
        go.name = name;
        var collider = go.GetComponent<Collider>(); if (collider) UnityEngine.Object.DestroyImmediate(collider);
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPosition; go.transform.localScale = size;
        go.GetComponent<Renderer>().sharedMaterial = material;
        return go;
    }

    static GameObject Cyl(Transform parent, string name, Vector3 localBase, float radius, float height, Material material) =>
        Box(parent, name, localBase + Vector3.up * height * .5f, new Vector3(radius * 2, height * .5f, radius * 2), material, PrimitiveType.Cylinder);

    static GameObject Text(Transform parent, string value, Vector3 localPosition, float yaw, Color color, float size)
    {
        var go = new GameObject("Text " + value, typeof(TextMesh));
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPosition; go.transform.localRotation = Quaternion.Euler(0, yaw, 0);
        var text = go.GetComponent<TextMesh>();
        text.text = value; text.font = font; text.fontSize = 96; text.characterSize = size; text.anchor = TextAnchor.MiddleCenter; text.fontStyle = FontStyle.Bold;
        text.color = color;
        go.GetComponent<MeshRenderer>().sharedMaterial = font.material;
        go.GetComponent<MeshRenderer>().shadowCastingMode = ShadowCastingMode.Off;
        return go;
    }

    // Instantiates one of the supplied map models, fitted into a box whose bottom-centre is `at`.
    static Transform Model(Transform parent, string model, Vector3 at, Vector3 box, float yaw)
    {
        var holder = new GameObject(model).transform;
        holder.SetParent(parent, false);
        holder.localPosition = at;
        var visual = CheckoutMapModelsBuilder.Create(holder, model, "Visual", yaw);
        var renderers = visual.GetComponentsInChildren<Renderer>(true);
        var b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
        var size = holder.TransformVector(box);
        visual.localScale *= Mathf.Min(Mathf.Abs(size.x) / b.size.x, Mathf.Abs(size.y) / b.size.y, Mathf.Abs(size.z) / b.size.z);
        b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
        var target = holder.position;
        visual.position += new Vector3(target.x - b.center.x, target.y - b.min.y, target.z - b.center.z);
        return holder;
    }

    static Material Mat(string name, string hex, float gloss = .08f, string emission = null)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Folder + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("Standard");
        material.color = MarketSimulation.C(hex);
        material.SetFloat("_Glossiness", gloss);
        if (emission != null)
        {
            material.EnableKeyword("_EMISSION");
            material.SetColor("_EmissionColor", MarketSimulation.C(emission) * 1.6f);
            material.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
        }
        else material.DisableKeyword("_EMISSION");
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static Material Transparent(string name, Color color)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Folder + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("Standard");
        material.color = color; material.SetFloat("_Glossiness", .85f);
        material.SetFloat("_Mode", 3); material.SetOverrideTag("RenderType", "Transparent");
        material.SetInt("_SrcBlend", (int)BlendMode.One); material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha); material.SetInt("_ZWrite", 0);
        material.DisableKeyword("_ALPHATEST_ON"); material.DisableKeyword("_ALPHABLEND_ON"); material.EnableKeyword("_ALPHAPREMULTIPLY_ON");
        material.renderQueue = (int)RenderQueue.Transparent;
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static Material Glass() => Transparent("StageGlass", new Color(.72f, .86f, .95f, .32f));
}
