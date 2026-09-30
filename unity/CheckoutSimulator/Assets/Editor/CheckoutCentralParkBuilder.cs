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
using Area = Checkout.CheckoutExpansionNeighborhood.Area;
using Random = System.Random;

// Rebuilds the scenery around the supermarket block:
//  * the block across the avenue becomes the southern tip of a Central Park style park and the avenue
//    becomes Central Park South (59th Street: hexagonal pavers, perimeter wall, benches);
//  * the west avenue junction becomes a Columbus Circle style roundabout with a monument;
//  * the two side blocks across the local streets are filled with houses and shops;
//  * the houses on the supermarket block are replaced by an abandoned warehouse (future expansion)
//    and a Harbour Quay style public square whose pieces give way as the market expands.
// Safe to run again: it rebuilds only the objects it owns.
public static class CheckoutCentralParkBuilder
{
    const string Root = "Assets/Art/CityPark/";
    const string ParkName = "Central Park South", CircleName = "Columbus Circle", PlazaName = "Harbour Quay Plaza";
    const string WarehouseName = "Abandoned Warehouse (future expansion)", SidePrefix = "Side ", SignPrefix = "City storefront ";
    // Trees and shop fronts stay out of City Establishments (its children get doors and the Supermarket
    // World root is turned 180 degrees, so this root is re-aligned with the world axes).
    const string GardensName = "Side Block Details";
    const float Ground = .13f;
    static readonly Vector3 CircleCenter = new Vector3(-23.5f, 0, -18.5f);
    // Behind the widened west sidewalk (block edge x -15.75).
    static readonly Vector3 WarehouseCenter = new Vector3(-8.15f, 0, 34.2f);
    static readonly Vector3 WarehouseSize = new Vector3(14.7f, 6.2f, 10.1f); // The market's opening footprint.
    static readonly Vector2 BasinCenter = new Vector2(7.4f, 36.5f); // Former dock basin, now open paving.
    // Same stage sizes as the app (src/services/simulator-layout.ts) and the Expansion Preview window.
    static readonly float[,] Scales = { { .82f, .72f }, { .96f, .82f }, { 1.1f, .92f }, { 1.24f, 1.03f }, { 1.38f, 1.14f } };

    static readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
    static readonly HashSet<GameObject> primitives = new HashSet<GameObject>();
    static Transform world;
    static Transform[] treeTemplates;
    static int meshCounter;

    [MenuItem("Supermarket/Build Central Park, Columbus Circle and Harbour Quay")]
    public static void Apply()
    {
        if (EditorApplication.isPlaying) throw new InvalidOperationException("Leave Play Mode first.");
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        if (!simulation) throw new InvalidOperationException("Open the supermarket scene.");
        world = simulation.world;
        var scenePath = simulation.gameObject.scene.path;
        Directory.CreateDirectory("../scene-backups");
        string backup = "../scene-backups/Supermarket-before-central-park.unity";
        if (!File.Exists(backup) && File.Exists(scenePath)) File.Copy(scenePath, backup);
        Folder("Assets/Art", "CityPark"); Folder("Assets/Art/CityPark", "Meshes");
        materials.Clear(); primitives.Clear(); meshCounter = 0;
        treeTemplates = new[] { "City Tree 01", "City Tree 02", "City Tree 04", "City Tree 05" }
            .Select(n => world.Find("Landscape Models/" + n)).Where(t => t).ToArray();
        if (treeTemplates.Length == 0) throw new InvalidOperationException("Missing landscape tree templates.");

        foreach (var name in new[] { ParkName, CircleName, PlazaName, WarehouseName, GardensName, CheckoutMarketLayout.GrandWarehouse, CheckoutMarketLayout.GrandYard })
        {
            var old = world.Find(name);
            if (old) UnityEngine.Object.DestroyImmediate(old.gameObject);
        }
        var establishments = world.Find("City Establishments");
        foreach (Transform child in establishments.Cast<Transform>().ToArray())
            if (child.name.StartsWith(SidePrefix) || child.name.StartsWith(SignPrefix)) UnityEngine.Object.DestroyImmediate(child.gameObject);
        var oldGardens = world.Find("Side Block Gardens");
        if (oldGardens) UnityEngine.Object.DestroyImmediate(oldGardens.gameObject);

        RetireOldScenery();
        BuildCircle();
        BuildPark();
        var gardens = NewRoot(GardensName);
        RespaceStreetFurniture();
        ShiftSideBuildings();
        // Side blocks across the local streets (north of the avenue), then the two corners beside the park.
        FillSideBlock(-1, establishments, gardens, CheckoutStreetLayout.BlockNorthZ + .4f, 47.4f, new[] { null, null, "LIVRARIA", "LAVANDERIA" });
        FillSideBlock(1, establishments, gardens, CheckoutStreetLayout.BlockNorthZ + .4f, 47.4f, new[] { "FLORICULTURA", "PIZZARIA", "SORVETERIA", "BARBEARIA" });
        // Corners beside the park: a small apartment block and a house, close to the street, with room between them.
        FillSideBlock(-1, establishments, gardens, -43.6f, CheckoutStreetLayout.BlockSouthZ - .4f, new string[0], "south west ", 3, 6.4f, 2.2f, .8f, 6.5f, false);
        FillSideBlock(1, establishments, gardens, -43.6f, CheckoutStreetLayout.BlockSouthZ - .4f, new string[0], "south east ", 7, 6.4f, 2.2f, .8f, 6.5f, false);
        CornerTrees(-1, establishments, gardens); CornerTrees(1, establishments, gardens);
        BuildWarehouse();
        BuildGrandWarehouse();
        BuildPlaza();
        StripTreeBeds();
        ConfigureGround();

        EditorSceneManager.MarkSceneDirty(simulation.gameObject.scene);
        EditorSceneManager.SaveScene(simulation.gameObject.scene);
        AssetDatabase.SaveAssets();
        Debug.Log("CENTRAL_PARK_BUILD_OK primitives baked into " + meshCounter + " meshes");
        Review();
    }

    // ------------------------------------------------------------------ old scenery
    static void RetireOldScenery()
    {
        // Fewer trees around the market: every other landscape tree near the premium corner, and one by the promenade.
        foreach (var tree in new[] { "City Tree 06", "City Tree 03", "City Tree 03 (1)", "City Tree 03 (2)" })
        {
            var t = world.Find("Landscape Models/" + tree);
            if (t) t.gameObject.SetActive(false);
        }
        var rides = world.Find("City Park and Crossings/Amusement park");
        if (rides) rides.gameObject.SetActive(false);
        // A roundabout gives way instead of using signals.
        var signals = world.Find("City Park and Crossings");
        if (signals)
            foreach (Transform signal in signals.Cast<Transform>().ToArray())
                if (signal.name.StartsWith("Traffic signal") && Flat(signal.position - CircleCenter).magnitude < 13f)
                    UnityEngine.Object.DestroyImmediate(signal.gameObject);
        // The houses on the market block go away; the square below takes their place as locked ground.
        var neighborhood = world.GetComponentInChildren<CheckoutExpansionNeighborhood>(true);
        if (neighborhood)
        {
            foreach (Transform house in neighborhood.transform.Cast<Transform>().ToArray())
                UnityEngine.Object.DestroyImmediate(house.gameObject);
            neighborhood.lots = Array.Empty<CheckoutExpansionNeighborhood.Lot>();
        }
    }

    // ------------------------------------------------------------------ Columbus Circle
    static void BuildCircle()
    {
        var root = NewRoot(CircleName);
        var circle = root.gameObject.AddComponent<CheckoutRoundabout>();
        circle.center = CircleCenter; circle.islandRadius = 3.4f; circle.outerRadius = 7.5f; circle.travelRadius = 6.45f; // outer of the two painted lanes circle.clipRadius = 9f;
        var monument = Group(root, "Monument", CircleCenter);
        Material granite = Mat("Granite", "C9C3B6"), stone = Mat("MonumentStone", "A8A195"), bronze = Mat("Bronze", "6E5A3C", .45f);
        Cyl(monument, "Fountain basin", Vector3.up * Ground, 2.55f, .42f, stone);
        var basinWater = WaterSurface(root, "Fountain water", new Vector2(CircleCenter.x, CircleCenter.z), new Vector2(2.36f, 2.36f), Ground + .425f, 0, .55f);
        FountainJets(root, basinWater);
        Cyl(monument, "Plinth", Vector3.up * Ground, 1.35f, .62f, granite);
        Box(monument, "Pedestal", Vector3.up * (Ground + .62f + .6f), new Vector3(1.55f, 1.2f, 1.55f), granite);
        Box(monument, "Pedestal cornice", Vector3.up * (Ground + 1.82f + .12f), new Vector3(1.75f, .24f, 1.75f), stone);
        Box(monument, "Upper step", Vector3.up * (Ground + 2.06f + .25f), new Vector3(1.15f, .5f, 1.15f), granite);
        float columnBase = Ground + 2.56f;
        Cyl(monument, "Column", Vector3.up * columnBase, .3f, 5.4f, granite);
        for (int i = 0; i < 3; i++) Cyl(monument, "Bronze band", Vector3.up * (columnBase + 1.5f + i * 1.25f), .36f, .14f, bronze);
        Cyl(monument, "Column base ring", Vector3.up * columnBase, .42f, .25f, stone);
        Box(monument, "Capital", Vector3.up * (columnBase + 5.4f + .15f), new Vector3(.82f, .3f, .82f), stone);
        Cyl(monument, "Statue body", Vector3.up * (columnBase + 5.7f), .2f, .95f, bronze);
        var head = Prim(monument, "Statue head", PrimitiveType.Sphere, Vector3.up * (columnBase + 6.8f), Vector3.one * .3f, bronze);
        var arm = Box(monument, "Statue arm", new Vector3(.22f, columnBase + 6.35f, 0), new Vector3(.12f, .55f, .12f), bronze);
        arm.transform.localRotation = Quaternion.Euler(0, 0, -35);
        for (int i = 0; i < 10; i++)
        {
            float a = i * Mathf.PI * 2 / 10;
            var shrub = Prim(monument, "Island shrub", PrimitiveType.Sphere, new Vector3(Mathf.Cos(a + .3f) * 2.75f, Ground + .12f, Mathf.Sin(a + .3f) * 2.75f), new Vector3(.45f, .32f, .45f), Mat(i % 3 == 0 ? "ShrubFlower" : "Shrub", i % 3 == 0 ? "C77A92" : "4D7A3A"));
        }
        // Give-way signs on the right of every approach arm.
        var signs = Group(root, "Give way signs", Vector3.zero);
        foreach (var (p, facing) in new[] { (new Vector3(-33.2f, 0, -26.15f), 90f), (new Vector3(-14.6f, 0, -10.85f), 270f), (new Vector3(-27.4f, 0, -8.6f), 180f), (new Vector3(-19.6f, 0, -28.4f), 0f) })
            GiveWay(signs, p, facing);
        StreetSign(root, new Vector3(-18.4f, 0, -27.2f), "CENTRAL PARK S", "COLUMBUS CIRCLE");
        StreetSign(root, new Vector3(-17.2f, 0, -9.6f), "W 59 ST", "COLUMBUS CIRCLE");
        Bake(root);
    }

    static void GiveWay(Transform parent, Vector3 p, float yaw)
    {
        var sign = Group(parent, "Give way", p);
        sign.localRotation = Quaternion.Euler(0, yaw, 0);
        Cyl(sign, "Pole", Vector3.up * Ground, .045f, 2.1f, Mat("SignPole", "8E9496"));
        var red = Prim(sign, "Give way triangle", PrimitiveType.Quad, new Vector3(0, Ground + 2.05f, -.05f), Vector3.one * .62f, Mat("SignRed", "C23B32"));
        red.GetComponent<MeshFilter>().sharedMesh = Triangle();
        var white = Prim(sign, "Give way face", PrimitiveType.Quad, new Vector3(0, Ground + 2.05f, -.06f), Vector3.one * .42f, Mat("SignWhite", "F2EFE6"));
        white.GetComponent<MeshFilter>().sharedMesh = Triangle();
    }

    static void StreetSign(Transform parent, Vector3 p, string first, string second)
    {
        var post = Group(parent, "Street name sign", p);
        Material pole = Mat("SignPole", "8E9496"), green = Mat("StreetSignGreen", "1F6B45");
        Cyl(post, "Pole", Vector3.up * Ground, .05f, 3.1f, pole);
        Box(post, "Blade " + first, new Vector3(0, Ground + 3f, 0), new Vector3(1.9f, .3f, .04f), green);
        Label(post, first, new Vector3(0, Ground + 3f, -.03f), 0, Color.white, .045f);
        var blade = Box(post, "Blade " + second, new Vector3(0, Ground + 2.62f, 0), new Vector3(1.9f, .3f, .04f), green);
        blade.transform.localRotation = Quaternion.Euler(0, 90, 0);
        Label(post, second, new Vector3(.03f, Ground + 2.62f, 0), 270, Color.white, .045f); // faces the game camera (east)
    }

    // ------------------------------------------------------------------ Central Park South
    static void BuildPark()
    {
        var root = NewRoot(ParkName);
        Material wall = Mat("ParkWall", "8F8A80"), coping = Mat("ParkWallCoping", "B8B2A6"), pier = Mat("GatePier", "A39D92");
        // Perimeter wall with openings at the gates, the drive and Merchants' Gate plaza.
        var walls = Group(root, "Perimeter wall", Vector3.zero);
        float N = CheckoutCityPark.North - .25f, E = CheckoutCityPark.East + .25f, W = CheckoutCityPark.West - .25f;
        float driveEast = CheckoutCityPark.DriveZ(CheckoutCityPark.East);
        float gateX = CheckoutCityPark.PathX(CheckoutCityPark.North), eastGate = CheckoutCityPark.EastPath[0].x;
        float driveWest = CheckoutCityPark.DriveZ(CheckoutCityPark.West);
        // The wall runs right into the corner by Columbus Circle; the drive opens onto both side streets.
        var piers = new[] { new Vector3(W, 0, N), new Vector3(gateX - 1.3f, 0, N), new Vector3(gateX + 1.3f, 0, N), new Vector3(eastGate - 1.1f, 0, N),
            new Vector3(eastGate + 1.1f, 0, N), new Vector3(E, 0, driveEast + 1.9f), new Vector3(E, 0, driveEast - 1.9f), new Vector3(W, 0, driveWest + 1.9f), new Vector3(W, 0, driveWest - 1.9f) };
        WallRun(walls, piers[0], piers[1], wall, coping);
        WallRun(walls, piers[2], piers[3], wall, coping);
        WallRun(walls, piers[4], new Vector3(E, 0, N), wall, coping);
        WallRun(walls, new Vector3(E, 0, N), piers[5], wall, coping);
        WallRun(walls, piers[6], new Vector3(E, 0, -43.9f), wall, coping);
        WallRun(walls, piers[0], piers[7], wall, coping);
        WallRun(walls, piers[8], new Vector3(W, 0, -43.9f), wall, coping);
        foreach (var p in piers)
        {
            Box(walls, "Gate pier", p + Vector3.up * (Ground + .65f), new Vector3(.62f, 1.3f, .62f), pier);
            Box(walls, "Gate pier cap", p + Vector3.up * (Ground + 1.36f), new Vector3(.74f, .12f, .74f), coping);
            Prim(walls, "Gate pier finial", PrimitiveType.Sphere, p + Vector3.up * (Ground + 1.55f), Vector3.one * .28f, coping);
        }
        // Benches along the wall, facing the street, as on Central Park South.
        var benches = Group(root, "59th Street benches", Vector3.zero);
        for (float x = W + 1.6f; x < E - 1f; x += 4.3f)
        {
            if (Mathf.Abs(x - gateX) < 2.4f || Mathf.Abs(x - eastGate) < 2.2f) continue;
            ParkBench(benches, new Vector3(x, 0, N + .55f), 180);
        }
        foreach (var x in new[] { gateX - 2.35f, gateX + 2.35f, eastGate - 1.6f })
            Bin(benches, new Vector3(x, 0, N + .5f));

        var occupied = new List<Vector2>();
        var trees = Group(root, "Park trees", Vector3.zero);
        // Existing trees that now stand on a path, in the pond or on the plaza are replanted.
        var landscape = world.Find("Landscape Models");
        var displaced = new List<Transform>();
        foreach (Transform tree in landscape)
        {
            var c = Flat2(BoundsOf(tree).center);
            if (!CheckoutCityPark.InPark(c, -1)) continue;
            if (CheckoutCityPark.PathDistance(c) < 1.2f || CheckoutCityPark.PondDistance(c) < 1.4f) displaced.Add(tree);
            else occupied.Add(c);
        }
        // An irregular avenue of elms inside the wall and along the side walls, then a few groves with open
        // lawn between them, and single specimen trees by the water. Nothing stands on a path or the pond.
        var random = new Random(59);
        float J() => (float)random.NextDouble() - .5f;
        bool Plant(Vector2 p, float spacing, float height)
        {
            if (!TryTree(trees, p, occupied, spacing, height, displaced.Count > 0 ? displaced[0] : null)) return false;
            if (displaced.Count > 0) displaced.RemoveAt(0);
            return true;
        }
        for (float x = -9.2f; x < 15f; x += 4.4f) Plant(new Vector2(x + J() * .9f, -29.9f + J() * .4f), 3.2f, 5.6f + J());
        for (float z = -34f; z > -43.5f; z -= 3.9f) { Plant(new Vector2(16.1f + J() * .4f, z + J()), 3.2f, 5.3f + J()); Plant(new Vector2(-16.1f + J() * .4f, z + J()), 3.2f, 5.3f + J()); }
        foreach (var grove in new[] { new Vector2(-12.6f, -38.4f), new Vector2(-11.8f, -43f), new Vector2(-5.4f, -40.6f), new Vector2(-5.6f, -35.4f), new Vector2(14.2f, -42.8f) })
        {
            int inGrove = 0;
            for (int attempt = 0; attempt < 60 && inGrove < 4; attempt++)
            {
                float a = (float)random.NextDouble() * Mathf.PI * 2, r = inGrove == 0 && attempt < 6 ? (float)random.NextDouble() * 1.2f : 1.9f + (float)random.NextDouble() * 2.2f;
                if (Plant(grove + new Vector2(Mathf.Cos(a), Mathf.Sin(a)) * r, 2.7f, 4.4f + (float)random.NextDouble() * 1.8f)) inGrove++;
            }
        }
        foreach (var p in new[] { new Vector2(-8.5f, -30.1f), new Vector2(9.5f, -29.6f), new Vector2(14.6f, -30.4f), new Vector2(1.2f, -43.2f) }) Plant(p, 3f, 6.2f);
        foreach (var tree in displaced) tree.gameObject.SetActive(false);

        // Lamps along the drive and the paths; benches facing the drive and the pond.
        var furniture = Group(root, "Park furniture", Vector3.zero);
        for (float x = -14f; x < 15f; x += 7f)
        {
            float side = Mathf.Repeat(x, 14f) < 7f ? 1 : -1;
            ParkLamp(furniture, new Vector3(x, 0, CheckoutCityPark.DriveZ(x) + side * 1.75f));
        }
        for (float x = -12.5f; x < 15f; x += 9f)
            if (CheckoutCityPark.PondDistance(new Vector2(x, CheckoutCityPark.DriveZ(x) + 2f)) > 2.5f)
                ParkBench(furniture, new Vector3(x, 0, CheckoutCityPark.DriveZ(x) + 1.95f), 0);
        for (float z = -34.5f; z > -44f; z -= 5f) ParkLamp(furniture, new Vector3(CheckoutCityPark.PathX(z) + 1.05f, 0, z));
        for (int i = 0; i < 6; i++)
        {
            float a = i * Mathf.PI * 2 / 6 + .35f;
            var dir = new Vector2(Mathf.Cos(a) * CheckoutCityPark.PondRadii.x, Mathf.Sin(a) * CheckoutCityPark.PondRadii.y).normalized;
            var p = PondPoint(a, 2.55f);
            if (!CheckoutCityPark.InPark(p, .6f)) continue;
            if (i % 2 == 0) ParkLamp(furniture, new Vector3(p.x, 0, p.y));
            else ParkBench(furniture, new Vector3(p.x, 0, p.y), Mathf.Atan2(-(p.x - CheckoutCityPark.Pond.x), -(p.y - CheckoutCityPark.Pond.y)) * Mathf.Rad2Deg + 180);
        }
        // Manhattan schist outcrops.
        var rocks = Group(root, "Schist outcrops", Vector3.zero);
        Material schist = Mat("Schist", "7E7B74"), schistDark = Mat("SchistDark", "66635D");
        foreach (var p in new[] { new Vector2(-4.4f, -43f), new Vector2(-9.6f, -41.2f), new Vector2(-13.4f, -35.4f), new Vector2(14.2f, -38.2f), new Vector2(3.4f, -30.3f) })
        {
            if (CheckoutCityPark.PathDistance(p) < 1.3f || CheckoutCityPark.PondDistance(p) < .8f) continue;
            for (int i = 0; i < 3; i++)
            {
                var rock = Prim(rocks, "Rock", PrimitiveType.Sphere, new Vector3(p.x + (i - 1) * .75f, Ground + .1f, p.y + (i % 2) * .5f), new Vector3(1.5f - i * .3f, .8f - i * .15f, 1.1f), i == 1 ? schistDark : schist);
                rock.transform.localRotation = Quaternion.Euler(0, i * 47 + p.x * 10, 8);
            }
        }
        BuildPond(root);
        Bake(root);
    }

    static Vector2 PondPoint(float angle, float offset)
    {
        var e = new Vector2(Mathf.Cos(angle) * CheckoutCityPark.PondRadii.x, Mathf.Sin(angle) * CheckoutCityPark.PondRadii.y);
        return CheckoutCityPark.Pond + e + e.normalized * offset;
    }

    static bool TryTree(Transform parent, Vector2 p, List<Vector2> occupied, float spacing, float height, Transform reuse = null)
    {
        if (!CheckoutCityPark.InPark(p, .9f)) return false;
        if (CheckoutCityPark.PathDistance(p) < 1.4f || CheckoutCityPark.PondDistance(p) < 1.7f) return false;
        if (occupied.Any(o => (o - p).magnitude < spacing)) return false;
        if (Mathf.Abs(p.x - CheckoutCityPark.BridgeX) < 1.8f && Mathf.Abs(p.y - CheckoutCityPark.Pond.y) < 5.2f) return false; // bridge
        occupied.Add(p);
        if (reuse) PlaceOnGround(reuse, new Vector3(p.x, 0, p.y)); // stays in Landscape Models
        else Tree(parent, new Vector3(p.x, 0, p.y), height, occupied.Count);
        return true;
    }

    static void WallRun(Transform parent, Vector3 a, Vector3 b, Material body, Material top)
    {
        var d = b - a; float length = d.magnitude; if (length < .1f) return;
        var mid = (a + b) * .5f; var rot = Quaternion.LookRotation(d.normalized);
        var w = Box(parent, "Park wall", mid + Vector3.up * (Ground + .36f), new Vector3(.42f, .72f, length), body); w.transform.localRotation = rot;
        var c = Box(parent, "Park wall coping", mid + Vector3.up * (Ground + .77f), new Vector3(.54f, .1f, length + .04f), top); c.transform.localRotation = rot;
    }

    const string BridgeModel = "Assets/Art/Models/MapModels/ParkBridge/ParkBridge.fbx", DuckModel = "Assets/Art/Models/MapModels/ParkDuck/ParkDuck.fbx";

    static void BuildPond(Transform root)
    {
        var pond = Group(root, "The Pond", Vector3.zero);
        pond.gameObject.AddComponent<CheckoutWaterRipples>();
        WaterSurface(pond, "Pond water", CheckoutCityPark.Pond, CheckoutCityPark.PondRadii + new Vector2(.08f, .08f), Ground + .02f, 1, 1);
        // Gapstow style arched stone footbridge across the west lobe (modelled in Blender).
        var model = AssetDatabase.LoadAssetAtPath<GameObject>(BridgeModel);
        if (!model) throw new InvalidOperationException("Missing " + BridgeModel);
        var bridge = (GameObject)PrefabUtility.InstantiatePrefab(model, pond);
        bridge.name = "Stone footbridge";
        var byName = new Dictionary<string, Material>
        {
            {"BridgeStone", Mat("BridgeStone", "9C968B")}, {"BridgeArchStone", Mat("BridgeStoneDark", "7F7A70")},
            {"BridgeCoping", Mat("ParkWallCoping", "B8B2A6")}, {"BridgePath", Mat("BridgePath", "A89C88")},
        };
        foreach (var renderer in bridge.GetComponentsInChildren<Renderer>())
            renderer.sharedMaterials = renderer.sharedMaterials.Select(m => m && byName.TryGetValue(m.name, out var r) ? r : Mat("BridgeStone", "9C968B")).ToArray();
        var span = BoundsOf(bridge.transform);
        if (span.size.x > span.size.z) bridge.transform.rotation = Quaternion.Euler(0, 90, 0) * bridge.transform.rotation; // span runs north-south
        // Stretch the span a little so the arch clears the whole width of the water.
        var along = bridge.transform.InverseTransformDirection(Vector3.forward);
        bridge.transform.localScale = Vector3.Scale(bridge.transform.localScale, new Vector3(1 + Mathf.Abs(along.x) * .1f, 1 + Mathf.Abs(along.y) * .1f, 1 + Mathf.Abs(along.z) * .1f));
        span = BoundsOf(bridge.transform);
        Debug.Log("PARK_BRIDGE size=" + span.size);
        bridge.transform.position += new Vector3(CheckoutCityPark.BridgeX - span.center.x, Ground - .02f - (span.min.y + .3f), CheckoutCityPark.Pond.y - span.center.z);
        GameObjectUtility.SetStaticEditorFlags(bridge, (StaticEditorFlags)0); // not batched: the map editor moves these props

        Material pad = Mat("LilyPad", "4F8A3E");
        var random = new Random(7);
        for (int i = 0; i < 14; i++)
        {
            float a = (float)random.NextDouble() * Mathf.PI * 2;
            var p = PondPoint(a, -.5f - (float)random.NextDouble() * 1.1f);
            if (Mathf.Abs(p.x - CheckoutCityPark.BridgeX) < 1.5f) continue;
            var lily = Cyl(pond, "Lily pad", new Vector3(p.x, Ground + .045f, p.y), .22f + (float)random.NextDouble() * .14f, .012f, pad);
            if (i % 4 == 0) Prim(pond, "Lily flower", PrimitiveType.Sphere, new Vector3(p.x + .06f, Ground + .07f, p.y), new Vector3(.1f, .06f, .1f), Mat("LilyFlower", "F2D6E0"));
        }

        // Mallards (drakes and hens) and a white farmyard duck, paddling about.
        var duckModel = AssetDatabase.LoadAssetAtPath<GameObject>(DuckModel);
        if (!duckModel) throw new InvalidOperationException("Missing " + DuckModel);
        var flock = Group(pond, "Ducks", Vector3.zero);
        var paint = new Dictionary<string, string[]>
        {   // DuckBody, DuckChest, DuckHead, DuckNeckRing, DuckWing, DuckTail, DuckBeak, DuckEye
            {"Drake", new[] { "9C9A92", "5E3A26", "1F5E36", "EDEDE6", "7E7466", "22252A", "D8B43A", "111111" }},
            {"Hen", new[] { "8A6A48", "7E5E40", "7A5C3E", "7A5C3E", "6A5038", "5A4430", "D88A3A", "111111" }},
            {"White", new[] { "EDEAE2", "F2EFE8", "F2EFE8", "F2EFE8", "E4E0D6", "E8E4DC", "E89A2E", "111111" }},
        };
        string[] slots = { "DuckBody", "DuckChest", "DuckHead", "DuckNeckRing", "DuckWing", "DuckTail", "DuckBeak", "DuckEye" };
        var kinds = new[] { "Drake", "Hen", "Drake", "Hen", "White", "Hen" };
        var ducks = new List<Transform>();
        for (int i = 0; i < kinds.Length; i++)
        {
            float a = i * 1.1f + .4f;
            var p = CheckoutCityPark.Pond + new Vector2(Mathf.Cos(a) * CheckoutCityPark.PondRadii.x * .5f, Mathf.Sin(a) * CheckoutCityPark.PondRadii.y * .5f);
            var duck = Group(flock, kinds[i] + " duck", new Vector3(p.x, Ground + .03f, p.y));
            duck.localRotation = Quaternion.Euler(0, i * 83, 0);
            var body = (GameObject)PrefabUtility.InstantiatePrefab(duckModel, duck);
            body.transform.localPosition = Vector3.zero;
            var colours = paint[kinds[i]];
            foreach (var renderer in body.GetComponentsInChildren<Renderer>())
                renderer.sharedMaterials = renderer.sharedMaterials.Select(m =>
                {
                    int slot = m ? Array.IndexOf(slots, m.name) : -1; if (slot < 0) slot = 0;
                    return Mat(kinds[i] + slots[slot], colours[slot], slot == 7 ? .8f : slot == 2 && kinds[i] == "Drake" ? .45f : .15f);
                }).ToArray();
            FaceBeakForward(duck, body.transform);
            ducks.Add(duck);
        }
        var swim = flock.gameObject.AddComponent<CheckoutPondDucks>();
        swim.centre = CheckoutCityPark.Pond; swim.radii = CheckoutCityPark.PondRadii; swim.waterY = Ground + .03f; swim.ducks = ducks.ToArray();
    }

    // The model's beak must point along the duck's local +Z (whatever axes the FBX came in with).
    static void FaceBeakForward(Transform duck, Transform model)
    {
        var renderer = model.GetComponentInChildren<MeshRenderer>(); var filter = renderer ? renderer.GetComponent<MeshFilter>() : null;
        if (!filter || !filter.sharedMesh) return;
        var mesh = filter.sharedMesh; int beak = Array.FindIndex(renderer.sharedMaterials, m => m && m.name.EndsWith("DuckBeak"));
        if (beak < 0 || beak >= mesh.subMeshCount) return;
        var tip = duck.InverseTransformPoint(filter.transform.TransformPoint(mesh.GetSubMesh(beak).bounds.center));
        var middle = duck.InverseTransformPoint(filter.transform.TransformPoint(mesh.bounds.center));
        var dir = tip - middle; dir.y = 0;
        if (dir.sqrMagnitude > 1e-6f) model.localRotation = Quaternion.FromToRotation(dir.normalized, Vector3.forward) * model.localRotation;
        // Waterline: the keel sits a few centimetres under the surface.
        var b = BoundsOf(model);
        model.position += Vector3.up * (duck.position.y - .05f - b.min.y);
    }

    // Flat water surface (a fan of rings) whose vertex alpha carries the normalised depth: 0 at the
    // edge, 1 in the middle. uv = world xz, tangents along +x so the scrolling normals line up.
    static Transform WaterSurface(Transform parent, string name, Vector2 centre, Vector2 radii, float y, int kind, float depthScale)
    {
        string path = Root + "Meshes/" + Safe(name) + ".asset";
        const int segments = 64, rings = 8;
        var vertices = new List<Vector3>(); var colours = new List<Color>(); var uvs = new List<Vector2>(); var triangles = new List<int>();
        vertices.Add(new Vector3(centre.x, 0, centre.y)); colours.Add(new Color(1, 1, 1, depthScale)); uvs.Add(centre);
        for (int r = 1; r <= rings; r++)
        {
            float k = r / (float)rings;
            float radial = Mathf.Sqrt(k); // more rings near the edge where the foam is
            for (int s = 0; s < segments; s++)
            {
                float a = s * Mathf.PI * 2 / segments;
                var p = centre + new Vector2(Mathf.Cos(a) * radii.x, Mathf.Sin(a) * radii.y) * radial;
                vertices.Add(new Vector3(p.x, 0, p.y)); uvs.Add(p);
                colours.Add(new Color(1, 1, 1, Mathf.Clamp01((1 - radial) * 2.2f) * depthScale));
            }
        }
        for (int s = 0; s < segments; s++) { triangles.Add(0); triangles.Add(1 + (s + 1) % segments); triangles.Add(1 + s); }
        for (int r = 1; r < rings; r++)
            for (int s = 0; s < segments; s++)
            {
                int a = 1 + (r - 1) * segments + s, b = 1 + (r - 1) * segments + (s + 1) % segments, c = a + segments, d = b + segments;
                triangles.AddRange(new[] { a, b, d, a, d, c });
            }
        var mesh = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (!mesh) { mesh = new Mesh(); AssetDatabase.CreateAsset(mesh, path); }
        mesh.Clear(); mesh.name = name;
        mesh.SetVertices(vertices); mesh.SetColors(colours); mesh.SetUVs(0, uvs); mesh.SetTriangles(triangles, 0);
        mesh.SetNormals(Enumerable.Repeat(Vector3.up, vertices.Count).ToList());
        mesh.SetTangents(Enumerable.Repeat(new Vector4(1, 0, 0, 1), vertices.Count).ToList());
        mesh.RecalculateBounds();
        EditorUtility.SetDirty(mesh);
        var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
        go.transform.SetParent(parent, false);
        // The surface transform doubles as the collision plane that ends the jets' particles.
        go.transform.SetPositionAndRotation(new Vector3(0, y, 0), Quaternion.identity);
        go.GetComponent<MeshFilter>().sharedMesh = mesh;
        var renderer = go.GetComponent<MeshRenderer>();
        renderer.sharedMaterial = Water(kind);
        renderer.shadowCastingMode = ShadowCastingMode.Off;
        return go.transform;
    }

    static Material Water(int kind)
    {
        string name = kind == 1 ? "PondWater" : kind == 2 ? "SplashPadWater" : "FountainWaterMoving";
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Root + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("MarketDay/City Water")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("MarketDay/City Water");
        material.SetTexture("_BumpMap", CheckoutCityParkTextures.Get("water").normal);
        if (kind == 1)
        {   // Pond: green-brown shallows, deep teal middle.
            material.SetColor("_ShallowColor", MarketSimulation.C("5E7F66")); material.SetColor("_DeepColor", MarketSimulation.C("1C4B55"));
            material.SetFloat("_Tiling", 3.2f); material.SetFloat("_BumpScale", .5f); material.SetFloat("_Speed", .045f); material.SetFloat("_FoamWidth", .1f);
        }
        else if (kind == 2)
        {   // A film of water on dark granite.
            material.SetColor("_ShallowColor", MarketSimulation.C("86A0A4")); material.SetColor("_DeepColor", MarketSimulation.C("6A8C92"));
            material.SetFloat("_Tiling", 1.2f); material.SetFloat("_BumpScale", .35f); material.SetFloat("_Speed", .09f); material.SetFloat("_FoamWidth", .05f);
        }
        else
        {   // Fountain basin: clear, bright turquoise, choppy under the jets.
            material.SetColor("_ShallowColor", MarketSimulation.C("5FA8B0")); material.SetColor("_DeepColor", MarketSimulation.C("2A7A8C"));
            material.SetFloat("_Tiling", 1.4f); material.SetFloat("_BumpScale", .8f); material.SetFloat("_Speed", .14f); material.SetFloat("_FoamWidth", .12f);
        }
        material.SetFloat("_Glossiness", .93f);
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    // ------------------------------------------------------------------ water jets (particles)
    static Material spray;
    static Material Spray()
    {
        if (spray) return spray;
        string path = Root + "WaterSpray.mat";
        spray = AssetDatabase.LoadAssetAtPath<Material>(path);
        var source = AssetDatabase.GetBuiltinExtraResource<Material>("Default-ParticleSystem.mat");
        if (!spray) { spray = new Material(source); AssetDatabase.CreateAsset(spray, path); }
        else spray.CopyPropertiesFromMaterial(source);
        spray.shader = source.shader;
        spray.SetColor("_Color", new Color(.86f, .95f, 1f, .85f));
        EditorUtility.SetDirty(spray);
        return spray;
    }

    // One nozzle; the particles die where they hit the water plane (surfaceY).
    static ParticleSystem Jet(Transform parent, string name, Vector3 position, Vector3 direction, float speed, Transform surface, float size = .11f, float rate = 70)
    {
        var go = new GameObject(name, typeof(ParticleSystem));
        go.transform.SetParent(parent, false);
        go.transform.SetPositionAndRotation(position, Quaternion.LookRotation(direction.normalized, Mathf.Abs(direction.normalized.y) > .99f ? Vector3.forward : Vector3.up));
        var ps = go.GetComponent<ParticleSystem>();
        ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
        var main = ps.main;
        main.duration = 2; main.loop = true; main.prewarm = true; main.playOnAwake = true;
        main.startLifetime = new ParticleSystem.MinMaxCurve(1.6f, 2f);
        main.startSpeed = new ParticleSystem.MinMaxCurve(speed * .97f, speed * 1.03f);
        main.startSize = new ParticleSystem.MinMaxCurve(size * .7f, size * 1.2f);
        main.startColor = new Color(.9f, .97f, 1f, .8f);
        main.gravityModifier = 1; main.simulationSpace = ParticleSystemSimulationSpace.World;
        main.maxParticles = 400; main.scalingMode = ParticleSystemScalingMode.Shape;
        var emission = ps.emission; emission.rateOverTime = rate;
        var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Cone; shape.angle = 1.5f; shape.radius = .015f;
        var colour = ps.colorOverLifetime; colour.enabled = true;
        var fade = new Gradient();
        fade.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(new Color(.85f, .93f, 1f), 1) },
            new[] { new GradientAlphaKey(.9f, 0), new GradientAlphaKey(.7f, .7f), new GradientAlphaKey(.2f, 1) });
        colour.color = fade;
        var grow = ps.sizeOverLifetime; grow.enabled = true; grow.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .8f, 1, 1.6f));
        // Die on the water surface.
        var collision = ps.collision; collision.enabled = true; collision.type = ParticleSystemCollisionType.Planes;
        collision.SetPlane(0, surface); collision.lifetimeLoss = 1; collision.dampen = 1; collision.bounce = 0;
        var renderer = go.GetComponent<ParticleSystemRenderer>();
        renderer.sharedMaterial = Spray(); renderer.renderMode = ParticleSystemRenderMode.Stretch;
        renderer.velocityScale = .05f; renderer.lengthScale = 1.6f; renderer.shadowCastingMode = ShadowCastingMode.Off; renderer.receiveShadows = false;
        ps.Play();
        return ps;
    }

    // Columbus Circle: arching jets from the rim towards the plinth, and a ring of bubbling spouts.
    static void FountainJets(Transform root, Transform water)
    {
        var jets = Group(root, "Fountain jets", Vector3.zero);
        float surface = water.position.y;
        for (int i = 0; i < 12; i++)
        {
            float a = i * Mathf.PI * 2 / 12;
            var radial = new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a));
            Jet(jets, "Arching jet", CircleCenter + radial * 2.15f + Vector3.up * (surface + .02f), -radial * .36f + Vector3.up, 3.5f, water, .12f);
            if (i % 2 == 0) Jet(jets, "Bubbler", CircleCenter + radial * 1.6f + Vector3.up * (surface + .01f), Vector3.up, 2.6f, water, .16f, 45);
        }
    }

    // Dancing water: a square of ground jets set in dark granite, choreographed by CheckoutDancingFountain.
    static void DancingFountain(Transform parent)
    {
        Cyl(parent, "Fountain pad", Vector3.up * Ground, 1.95f, .025f, Mat("FountainPad", "4B5256", .7f));
        Cyl(parent, "Fountain pad rim", Vector3.up * Ground, 2.05f, .018f, Mat("QuayCoping", "B9B4AA"));
        var film = WaterSurface(parent, "Splash pad water", Flat2(parent.position), new Vector2(1.9f, 1.9f), Ground + .03f, 2, .3f);
        var group = Group(parent, "Dancing jets", Vector3.zero);
        var jets = new List<ParticleSystem>(); var grid = new List<Vector2>();
        Material nozzle = Mat("RackSteel", "9DA3A6", .5f);
        for (int x = 0; x < 4; x++)
            for (int z = 0; z < 4; z++)
            {
                var g = new Vector2((x - 1.5f) / 1.5f, (z - 1.5f) / 1.5f);
                var local = new Vector3(g.x * 1.1f, 0, g.y * 1.1f);
                Cyl(parent, "Nozzle", local + Vector3.up * Ground, .06f, .035f, nozzle);
                jets.Add(Jet(group, "Dancing jet", parent.position + local + Vector3.up * (Ground + .04f), Vector3.up, 4f, film, .16f, 85));
                grid.Add(g);
            }
        var dance = group.gameObject.AddComponent<CheckoutDancingFountain>();
        dance.jets = jets.ToArray(); dance.grid = grid.ToArray();
    }

    // Trees keep their stone-and-mulch beds only on the supermarket block (the square and its planters);
    // everywhere else the trunk stands straight in the grass.
    static void StripTreeBeds()
    {
        var lowered = new HashSet<Transform>(); int removed = 0;
        foreach (var t in world.GetComponentsInChildren<Transform>(true).ToArray())
        {
            if (t.name != "Planter Base" && t.name != "Soil") continue;
            var instance = PrefabUtility.GetNearestPrefabInstanceRoot(t.gameObject);
            var tree = instance ? instance.transform : t.parent;
            var c = BoundsOf(tree, true).center;
            if (Mathf.Abs(c.x) < CheckoutStreetLayout.BlockInnerX && c.z > CheckoutStreetLayout.BlockNorthZ - .5f) continue;
            if (t.gameObject.activeSelf) { t.gameObject.SetActive(false); removed++; }
            lowered.Add(tree);
        }
        foreach (var tree in lowered)
        {
            var b = BoundsOf(tree);
            if (b.size.y > .01f && b.min.y > Ground + .005f) tree.position += Vector3.up * (Ground - b.min.y);
            if (PrefabUtility.IsPartOfPrefabInstance(tree)) PrefabUtility.RecordPrefabInstancePropertyModifications(tree);
        }
        Debug.Log("TREE_BEDS_REMOVED " + removed + " trees=" + lowered.Count);
    }

    static void ParkBench(Transform parent, Vector3 p, float yaw)
    {
        // Classic Central Park bench: wooden slats on a black cast iron frame. Faces local -Z rotated by yaw.
        var bench = Group(parent, "Park bench", p);
        bench.localRotation = Quaternion.Euler(0, yaw, 0);
        Material wood = Mat("BenchSlat", "8A6A45"), iron = Mat("CastIron", "22272A");
        for (int i = 0; i < 3; i++) Box(bench, "Seat slat", new Vector3(0, Ground + .45f, -.14f + i * .14f), new Vector3(1.7f, .05f, .11f), wood);
        for (int i = 0; i < 2; i++)
        {
            var back = Box(bench, "Back slat", new Vector3(0, Ground + .66f + i * .16f, .2f + i * .03f), new Vector3(1.7f, .1f, .04f), wood);
            back.transform.localRotation = Quaternion.Euler(-12, 0, 0);
        }
        foreach (float x in new[] { -.72f, .72f })
        {
            Box(bench, "Bench leg", new Vector3(x, Ground + .22f, 0), new Vector3(.06f, .44f, .5f), iron);
            Box(bench, "Bench arm", new Vector3(x, Ground + .62f, -.02f), new Vector3(.06f, .06f, .46f), iron);
        }
    }

    static void ParkLamp(Transform parent, Vector3 p)
    {
        var lamp = Group(parent, "Park lamppost", p);
        Material iron = Mat("CastIron", "22272A"), glow = Mat("LampGlobe", "FFF1C9", .3f, "E0B35A");
        Cyl(lamp, "Lamp base", Vector3.up * Ground, .13f, .45f, iron);
        Cyl(lamp, "Lamp post", Vector3.up * (Ground + .45f), .055f, 2.6f, iron);
        Cyl(lamp, "Lamp collar", Vector3.up * (Ground + 3.02f), .11f, .1f, iron);
        Prim(lamp, "Lamp globe", PrimitiveType.Sphere, Vector3.up * (Ground + 3.32f), new Vector3(.32f, .44f, .32f), glow);
        Cyl(lamp, "Lamp cap", Vector3.up * (Ground + 3.52f), .12f, .08f, iron);
    }

    static void Bin(Transform parent, Vector3 p)
    {
        var bin = Group(parent, "Litter basket", p);
        Cyl(bin, "Basket", Vector3.up * Ground, .26f, .8f, Mat("BinGreen", "2E5A3F"));
        Cyl(bin, "Basket rim", Vector3.up * (Ground + .78f), .28f, .05f, Mat("CastIron", "22272A"));
    }

    // ------------------------------------------------------------------ side blocks
    // Lamps, signals and street lights stand behind the cycle lane, never on it.
    static void RespaceStreetFurniture()
    {
        int moved = 0;
        foreach (var (group, prefixes) in new[] { ("City Circulation Repairs", new[] { "Streetlight" }), ("Individual Street Furniture", new[] { "Street Lamp", "Parking Lamp" }), ("City Park and Crossings", new[] { "Traffic signal" }) })
        {
            var g = world.Find(group); if (!g) continue;
            foreach (Transform t in g)
            {
                if (!prefixes.Any(p => t.name.StartsWith(p))) continue;
                var p = CheckoutStreetLayout.OffLane(t.position);
                if ((p - t.position).sqrMagnitude < 1e-6f) continue;
                t.position = p; moved++;
                if (PrefabUtility.IsPartOfPrefabInstance(t)) PrefabUtility.RecordPrefabInstancePropertyModifications(t);
            }
        }
        Debug.Log("STREET_FURNITURE_OFF_LANES " + moved);
    }

    // The wide sidewalks push the side-block buildings back: their street fronts line up behind them.
    static void ShiftSideBuildings()
    {
        float front = CheckoutStreetLayout.BlockOuterX + .3f;
        foreach (string group in new[] { "Supplied City Models", "City Establishments" })
        {
            var g = world.Find(group); if (!g) continue;
            foreach (Transform building in g)
            {
                if (building.name.StartsWith(SidePrefix) || building.name.Contains("vehicle") || building.name.StartsWith("City ") || building.name.StartsWith("Neighborhood car")) continue;
                var b = BoundsOf(building, true); if (b.size == Vector3.zero || b.size.y > 30) continue;
                if (Mathf.Abs(b.center.x) < 26f || Mathf.Abs(b.center.x) > 41f) continue;
                float side = Mathf.Sign(b.center.x), street = side < 0 ? -b.max.x : b.min.x;
                if (Mathf.Abs(street - front) < .01f) continue;
                building.position += Vector3.right * side * (front - street);
                if (PrefabUtility.IsPartOfPrefabInstance(building)) PrefabUtility.RecordPrefabInstancePropertyModifications(building);
                Debug.Log("SIDE_BUILDING_SHIFTED " + building.name + " by " + (front - street).ToString("F2"));
            }
        }
    }

    static void FillSideBlock(int side, Transform establishments, Transform gardens, float zStart, float zEnd, string[] shopSigns, string label = null, int firstModel = -1,
        float maxWidth = 99, float gap = .55f, float heightScale = 1, float depthCap = 99, bool streetTrees = true)
    {
        // Buildings face the local street; their fronts line up behind the (wide) sidewalk.
        float front = side * (CheckoutStreetLayout.BlockOuterX + .3f), edge = side * 39.4f;
        float maxDepth = Mathf.Min(depthCap, Mathf.Abs(edge - front) - .2f);
        var occupied = new List<Vector2>(); // z ranges along the frontage
        var fronts = new List<Bounds>();
        foreach (string group in new[] { "Supplied City Models", "City Establishments" })
        {
            var g = world.Find(group); if (!g) continue;
            foreach (Transform building in g)
            {
                if (building.name.Contains("vehicle") || building.name.StartsWith("City ") || building.name.StartsWith("Neighborhood car")) continue;
                if (!building.gameObject.activeInHierarchy) continue;
                var b = BoundsOf(building); if (b.size == Vector3.zero) continue;
                if (b.center.x * side < 27f || Mathf.Abs(b.center.x) > 41f || b.max.z < zStart || b.min.z > zEnd) continue;
                occupied.Add(new Vector2(b.min.z - .4f, b.max.z + .4f)); fronts.Add(b);
            }
        }
        foreach (Transform tree in world.Find("Landscape Models"))
        {
            if (!tree.gameObject.activeInHierarchy) continue;
            var b = BoundsOf(tree);
            if (b.center.x * side > 28f && Mathf.Abs(b.center.x) < 38f) occupied.Add(new Vector2(b.center.z - 1.3f, b.center.z + 1.3f));
        }
        occupied.Add(new Vector2(-99, zStart)); occupied.Add(new Vector2(zEnd, 99));
        occupied = Merge(occupied);
        var palette = new[]
        {
            ("StylizedBuilding", 8.5f, 9f, "CAFÉ"), ("clone:Corner house", 6f, 8.5f, "PADARIA"), ("StylizedHouse", 6.2f, 8.5f, ""),
            ("clone:West apartment building", 8.8f, 8.5f, "LIVRARIA"), ("CuteHouse", 5.6f, 7.5f, ""), ("clone:East townhouse", 6.2f, 8.5f, "FLORICULTURA"),
            ("Gym", 7.2f, 9f, ""), ("StylizedBuilding", 9.5f, 9f, "PIZZARIA"), ("StylizedHouse", 5.8f, 8f, "SORVETERIA"), ("CuteHouse", 5.4f, 7.5f, "BARBEARIA"),
        };
        int pick = firstModel >= 0 ? firstModel : side < 0 ? 0 : 5, count = 0, failures = 0;
        var signs = new Queue<string>(shopSigns);
        label ??= side < 0 ? "west " : "east ";
        for (int i = 0; i < occupied.Count - 1; i++)
        {
            float cursor = occupied[i].y, limit = occupied[i + 1].x;
            while (limit - cursor >= 4.2f)
            {
                var (model, height, depth, _) = palette[pick % palette.Length]; pick++;
                float width = Mathf.Min(limit - cursor, Mathf.Min(maxWidth, 7.6f + (count % 3) * .6f));
                var building = Building(establishments, model, SidePrefix + label + (++count) + " " + model.Replace("clone:", ""), side);
                if (!building) { if (++failures > 20) break; continue; }
                Fit(building, new Vector3(width - .2f, height * heightScale, Mathf.Min(depth, maxDepth)));
                var b = BoundsOf(building);
                building.position += new Vector3(front - (side < 0 ? b.max.x : b.min.x), Ground - b.min.y, cursor - b.min.z);
                b = BoundsOf(building);
                fronts.Add(b);
                if (signs.Count > 0 && b.size.z > 4.5f && count % 2 == 1) { var sign = signs.Dequeue(); if (sign != null) Storefront(gardens, b, side, sign); }
                cursor = b.max.z + gap;
            }
            if (streetTrees && limit - cursor > 2.2f) Tree(gardens, new Vector3(side * (CheckoutStreetLayout.BlockOuterX + 1.4f), 0, (cursor + limit) * .5f), 4.8f, count + 90, "Street tree");
        }
        // Back gardens: trees fill the strip between shallow buildings and the edge of the map.
        if (!streetTrees) return; // the corner blocks get just a couple (CornerTrees)
        foreach (var b in fronts)
        {
            float back = side < 0 ? b.min.x : b.max.x;
            if (Mathf.Abs(back) > Mathf.Abs(edge) - 3f) continue;
            for (float z = b.min.z + 1.6f; z < b.max.z - .8f; z += 3.6f)
                Tree(gardens, new Vector3((back + edge) * .5f, 0, z), 4.2f + Mathf.Abs(Mathf.Sin(z)) * 1.6f, (int)(z * 13), "Garden tree");
        }
    }

    // Trees round the buildings on the corner blocks beside the park, so no paving is left bare.
    static void CornerTrees(int side, Transform establishments, Transform gardens)
    {
        var buildings = establishments.Cast<Transform>().Where(t => t.name.Contains(side < 0 ? "south west" : "south east")).Select(t => BoundsOf(t)).ToList();
        var planted = new List<Vector2>();
        bool Free(Vector2 p) => !buildings.Any(b => p.x > b.min.x - .5f && p.x < b.max.x + .5f && p.y > b.min.z - .5f && p.y < b.max.z + .5f) && planted.All(q => (q - p).magnitude > 3f);
        int seed = side < 0 ? 300 : 400;
        // Just a couple of garden trees behind the buildings.
        foreach (var p in new[] { new Vector2(38.2f, -30.4f), new Vector2(38.4f, -41.4f) })
        {
            var q = new Vector2(p.x * side, p.y);
            if (!Free(q)) continue;
            planted.Add(q);
            Tree(gardens, new Vector3(q.x, 0, q.y), 4.4f + (seed % 3) * .5f, seed++, "Corner tree");
        }
    }

    static List<Vector2> Merge(List<Vector2> ranges)
    {
        var sorted = ranges.OrderBy(r => r.x).ToList(); var result = new List<Vector2>();
        foreach (var r in sorted)
        {
            if (result.Count > 0 && r.x <= result[result.Count - 1].y) result[result.Count - 1] = new Vector2(result[result.Count - 1].x, Mathf.Max(result[result.Count - 1].y, r.y));
            else result.Add(r);
        }
        return result;
    }

    static Transform Building(Transform parent, string model, string name, int side)
    {
        Transform building;
        if (model.StartsWith("clone:"))
        {
            var template = world.Find("Supplied City Models/" + model.Substring(6));
            if (!template) return null;
            var source = PrefabUtility.GetCorrespondingObjectFromSource(template.gameObject);
            var go = source ? (GameObject)PrefabUtility.InstantiatePrefab(source, parent) : UnityEngine.Object.Instantiate(template.gameObject, parent);
            building = go.transform; building.name = name;
            building.localScale = template.localScale;
            foreach (var pair in template.GetComponentsInChildren<Renderer>(true).Zip(building.GetComponentsInChildren<Renderer>(true), (a, b) => (a, b)))
                pair.b.sharedMaterials = pair.a.sharedMaterials;
        }
        else
        {
            try { building = CheckoutMapModelsBuilder.Create(parent, model, name, 0); }
            catch (Exception e) { Debug.LogWarning("Side block model skipped: " + model + " " + e.Message); return null; }
        }
        building.rotation = Quaternion.Euler(-90, side < 0 ? 90 : 270, 0);
        return building;
    }

    static void Fit(Transform t, Vector3 size)
    {
        var b = BoundsOf(t);
        float scale = Mathf.Min(size.z / b.size.z, Mathf.Min(size.y / b.size.y, size.x / b.size.x));
        t.localScale *= scale;
    }

    static void Storefront(Transform parent, Bounds b, int side, string name)
    {
        var shop = Group(parent, SignPrefix + name, new Vector3(side < 0 ? b.max.x : b.min.x, 0, b.center.z));
        shop.localRotation = Quaternion.Euler(0, side < 0 ? -90 : 90, 0); // local -Z faces the street
        var colors = new[] { ("AwningRed", "B8483B"), ("AwningGreen", "3E7A55"), ("AwningBlue", "3C6394"), ("AwningOchre", "C9922F") };
        var (key, hex) = colors[Mathf.Abs(name.GetHashCode()) % colors.Length];
        Material awning = Mat(key, hex), board = Mat("SignBoard", "2D3436"), rod = Mat("CastIron", "22272A");
        float width = Mathf.Min(b.size.z - 1f, 4.2f);
        var cover = Box(shop, "Awning", new Vector3(0, Ground + 2.55f, -.55f), new Vector3(width, .08f, 1.1f), awning);
        cover.transform.localRotation = Quaternion.Euler(-14, 0, 0);
        Box(shop, "Awning valance", new Vector3(0, Ground + 2.33f, -1.08f), new Vector3(width, .22f, .04f), awning);
        Box(shop, "Sign board", new Vector3(0, Ground + 3.15f, -.08f), new Vector3(width, .55f, .1f), board);
        Label(shop, name, new Vector3(0, Ground + 3.15f, -.15f), 0, new Color(.97f, .93f, .82f), .055f);
        foreach (float x in new[] { -width * .5f + .2f, width * .5f - .2f })
            Box(shop, "Awning rod", new Vector3(x, Ground + 2.45f, -.6f), new Vector3(.03f, .03f, 1.1f), rod);
        Bake(shop);
    }

    // ------------------------------------------------------------------ abandoned warehouse
    static void BuildWarehouse()
    {
        var root = NewRoot(WarehouseName);
        var w = Group(root, "Warehouse shell", WarehouseCenter);
        Vector3 s = WarehouseSize; float hx = s.x / 2, hz = s.z / 2, top = Ground + s.y;
        // Flat, warm colours like the rest of the stylised city (no photographic brick or rust textures).
        Material brick = Mat("WarehouseBrick", "C46A4C"), brickDark = Mat("WarehouseBrickDark", "A65440"), brickPatch = Mat("WarehouseBrickPatch", "D98464");
        Material concrete = Mat("WarehouseTrim", "EADCC0"), grime = Mat("WarehouseGrime", "8A5E4C"), rust = Mat("WarehouseRust", "C0703F", .15f);
        Material roofMetal = Mat("WarehouseRoof", "6F9A94", .2f), hole = Mat("WarehouseInterior", "2B2624"), glass = Mat("WarehouseGlass", "6E9EA6", .55f);
        Material wood = Mat("WarehouseBoard", "C99158"), woodDark = Mat("WarehouseBoardDark", "946842"), door = Mat("WarehouseShutter", "D08A45", .2f), pipe = Mat("WarehousePipe", "4F6668", .2f);
        Box(w, "Brick walls", new Vector3(0, Ground + s.y / 2, 0), new Vector3(s.x, s.y, s.z), brick);
        Box(w, "Concrete plinth", new Vector3(0, Ground + .35f, 0), new Vector3(s.x + .12f, .7f, s.z + .12f), concrete);
        Box(w, "Parapet band", new Vector3(0, top - .12f, 0), new Vector3(s.x + .16f, .24f, s.z + .16f), concrete);
        // Chunky corner pilasters and a sill band, like the bevelled trims on the city buildings.
        foreach (int i in new[] { -1, 1 }) foreach (int k in new[] { -1, 1 })
            Box(w, "Corner pilaster", new Vector3(i * (hx - .2f), Ground + s.y / 2, k * (hz - .2f)), new Vector3(.62f, s.y, .62f), brickDark);
        Box(w, "Sill band", new Vector3(0, Ground + 3.35f, 0), new Vector3(s.x + .1f, .16f, s.z + .1f), concrete);
        // Gabled corrugated roof running east-west, rusted, with a collapsed patch.
        float pitch = 18f, slope = hz / Mathf.Cos(pitch * Mathf.Deg2Rad) + .25f, rise = Mathf.Tan(pitch * Mathf.Deg2Rad) * hz;
        foreach (int n in new[] { -1, 1 })
        {
            var slab = Box(w, "Roof slope", new Vector3(0, top + rise / 2, n * hz / 2), new Vector3(s.x + .4f, .16f, slope), roofMetal);
            slab.transform.localRotation = Quaternion.Euler(n * pitch, 0, 0);
            for (float x = -hx + .4f; x <= hx; x += 1.2f)
            {
                var rib = Box(w, "Roof rib", new Vector3(x, top + rise / 2 + .1f, n * hz / 2), new Vector3(.16f, .1f, slope), Mat("WarehouseRoofRib", "5E8680", .2f));
                rib.transform.localRotation = slab.transform.localRotation;
            }
        }
        Box(w, "Roof ridge", new Vector3(0, top + rise + .05f, 0), new Vector3(s.x + .45f, .16f, .35f), rust);
        var gap = Box(w, "Collapsed roof panel", new Vector3(2.8f, top + rise * .55f + .09f, -hz * .45f), new Vector3(2.2f, .06f, 1.9f), hole);
        gap.transform.localRotation = Quaternion.Euler(-pitch, 0, 0);
        var loose = Box(w, "Loose roof sheet", new Vector3(-4.6f, top + rise * .55f + .25f, -hz * .5f), new Vector3(1.1f, .05f, 2.1f), rust);
        loose.transform.localRotation = Quaternion.Euler(-pitch - 16, 12, 9);
        foreach (int n in new[] { -1, 1 })
        {
            var gable = Prim(w, "Gable end", PrimitiveType.Quad, new Vector3(n * (hx + .01f), top, 0), Vector3.one, brickDark);
            gable.GetComponent<MeshFilter>().sharedMesh = Gable(hz, rise);
            gable.transform.localRotation = Quaternion.Euler(0, n * 90, 0);
        }
        // South facade (toward the square): roller door jammed half open, boarded doors, broken windows.
        float face = -hz - .04f;
        Box(w, "Door frame", new Vector3(-2.2f, Ground + 1.9f, face + .02f), new Vector3(4.1f, 3.8f, .12f), concrete);
        Box(w, "Dark opening", new Vector3(-2.2f, Ground + .6f, face - .01f), new Vector3(3.6f, 1.2f, .1f), hole);
        Box(w, "Roller shutter", new Vector3(-2.2f, Ground + 2.45f, face - .02f), new Vector3(3.6f, 2.5f, .1f), door);
        for (float y = Ground + 1.3f; y < Ground + 3.7f; y += .22f) Box(w, "Shutter rib", new Vector3(-2.2f, y, face - .08f), new Vector3(3.6f, .04f, .03f), rust);
        Box(w, "Shutter dent", new Vector3(-1.1f, Ground + 1.7f, face - .09f), new Vector3(.9f, .5f, .02f), grime);
        foreach (float x in new[] { -6f, 3.4f })
        {
            Box(w, "Side door", new Vector3(x, Ground + 1.15f, face), new Vector3(1.15f, 2.3f, .1f), hole);
            for (int i = 0; i < 3; i++)
            {
                var plank = Box(w, "Boarding plank", new Vector3(x, Ground + .55f + i * .7f, face - .07f), new Vector3(1.45f, .2f, .04f), i == 1 ? woodDark : wood);
                plank.transform.localRotation = Quaternion.Euler(0, 0, (i - 1) * 14);
            }
        }
        var windowRow = new[] { -6.3f, -4.2f, -.2f, 1.7f, 3.6f, 5.5f };
        for (int i = 0; i < windowRow.Length; i++) Window(w, new Vector3(windowRow[i], Ground + 4.1f, face), 0, i, concrete, glass, hole, wood, grime);
        Box(w, "Faded sign band", new Vector3(0, Ground + 5.45f, face - .01f), new Vector3(7.6f, .75f, .06f), Mat("WarehouseSign", "EFE3C6"));
        Label(w, "ARMAZÉM CENTRAL", new Vector3(0, Ground + 5.45f, face - .06f), 0, new Color(.48f, .40f, .33f), .085f);
        Box(w, "Paint peel", new Vector3(2.4f, Ground + 5.6f, face - .05f), new Vector3(1.1f, .35f, .02f), brick);
        // Side and rear walls: rows of windows, some boarded, some broken.
        for (int i = 0; i < 4; i++)
        {
            float z = -3.6f + i * 2.4f;
            Window(w, new Vector3(-hx - .04f, Ground + 4.1f, z), 90, i + 2, concrete, glass, hole, wood, grime);
            Window(w, new Vector3(hx + .04f, Ground + 4.1f, z), 270, i + 5, concrete, glass, hole, wood, grime);
        }
        for (int i = 0; i < 5; i++) Window(w, new Vector3(-5.6f + i * 2.8f, Ground + 4.1f, hz + .04f), 180, i + 3, concrete, glass, hole, wood, grime);
        // Brick repairs, damp stains and the drainpipes, one of them broken.
        var random = new Random(11);
        for (int i = 0; i < 14; i++)
        {
            float x = Mathf.Lerp(-hx + .6f, hx - .6f, (float)random.NextDouble()), y = Ground + 1f + (float)random.NextDouble() * 4.2f;
            if (Mathf.Abs(x + 2.2f) < 2.4f && y < Ground + 4) continue;
            Box(w, "Brick patch", new Vector3(x, y, face + .02f), new Vector3(.5f + (float)random.NextDouble() * .9f, .3f + (float)random.NextDouble() * .5f, .03f), i % 3 == 0 ? brickDark : brickPatch);
        }
        foreach (float x in windowRow) Box(w, "Damp stain", new Vector3(x + .25f, Ground + 3.1f, face - .005f), new Vector3(.5f, .75f, .015f), brickDark);
        foreach (var (x, z, broken) in new[] { (-hx - .12f, face + .15f, false), (hx + .12f, face + .15f, true), (-hx - .12f, hz - .15f, false) })
        {
            float h = broken ? s.y * .55f : s.y;
            Cyl(w, "Drainpipe", new Vector3(x, broken ? top - h : Ground, z), .08f, h, pipe);
        }
        var gutter = Box(w, "Hanging gutter", new Vector3(hx - 1.4f, top - .6f, face - .2f), new Vector3(2.8f, .12f, .14f), pipe);
        gutter.transform.localRotation = Quaternion.Euler(0, 0, -24);
        // The derelict shell is gone: the lot waits, fenced off, for the central warehouse (an expansion).
        UnityEngine.Object.DestroyImmediate(w.gameObject);
        // Yard: a crumbling loading dock, pallets, drums, a skip, weeds and a sagging chain-link fence.
        var yard = Group(root, "Derelict yard", WarehouseCenter);
        Box(yard, "Loading dock", new Vector3(4.9f, Ground + .5f, -hz - 1.2f), new Vector3(3.6f, 1f, 2.3f), concrete);
        Box(yard, "Dock edge", new Vector3(4.9f, Ground + .95f, -hz - 2.36f), new Vector3(3.6f, .12f, .12f), Mat("SafetyYellowFaded", "B79D45"));
        for (int i = 0; i < 3; i++) Box(yard, "Dock step", new Vector3(2.75f, Ground + .17f + i * .3f, -hz - 1.9f + i * .35f), new Vector3(.8f, .34f, .5f), concrete);
        for (int i = 0; i < 3; i++)
        {
            var pallet = Box(yard, "Broken pallet", new Vector3(-7.8f + i * .35f, Ground + .07f + i * .15f, -hz - 1.6f), new Vector3(1.2f, .14f, 1f), i == 2 ? woodDark : wood);
            pallet.transform.localRotation = Quaternion.Euler(i == 2 ? 8 : 0, i * 17, 0);
        }
        Material drum = Mat("WarehouseDrum", "C0603A", .2f), drumBlue = Mat("FadedDrum", "4A6377", .2f);
        foreach (var (x, z, tipped) in new[] { (6.6f, -hz - .8f, false), (7.3f, -hz - .9f, false), (7f, -hz - 1.7f, true), (-hx + .9f, -hz - 1f, false) })
        {
            var d = Cyl(yard, "Oil drum", new Vector3(x, Ground + (tipped ? .3f : 0), z), .3f, .9f, tipped ? drumBlue : drum);
            if (tipped) { d.transform.localRotation = Quaternion.Euler(90, 30, 0); d.transform.localPosition += new Vector3(0, 0, .45f); }
        }
        Box(yard, "Old skip", new Vector3(-4.3f, Ground + .55f, -hz - 2.1f), new Vector3(2.8f, 1.1f, 1.6f), Mat("SkipGreen", "3E5E4A", .1f));
        Box(yard, "Skip debris", new Vector3(-4.1f, Ground + 1.12f, -hz - 2.1f), new Vector3(2.1f, .2f, 1.2f), woodDark);
        Material weed = Mat("Weeds", "5C7A3A"), weedDry = Mat("WeedsDry", "8C8A4A");
        for (int i = 0; i < 26; i++)
        {
            float a = (float)random.NextDouble();
            Vector3 p = i % 3 == 0 ? new Vector3(Mathf.Lerp(-hx, hx, a), 0, -hz - .25f) : i % 3 == 1 ? new Vector3(-hx - .25f, 0, Mathf.Lerp(-hz, hz, a)) : new Vector3(Mathf.Lerp(-hx, hx + 1.5f, a), 0, -hz - .6f - (float)random.NextDouble() * 1.4f);
            if (p.z < -hz - .3f && Mathf.Abs(p.x - 4.9f) < 2.2f) continue;
            Prim(yard, "Weed tuft", PrimitiveType.Sphere, p + Vector3.up * (Ground + .1f), new Vector3(.35f, .28f, .35f) * (.7f + (float)random.NextDouble() * .8f), i % 4 == 0 ? weedDry : weed);
        }
        Tree(yard, WarehouseCenter + new Vector3(-hx + 1.1f, 0, -hz - 1.3f), 3.2f, 5, "Self-seeded tree");
        Fence(root);
        Bake(root);
    }

    static void Window(Transform w, Vector3 p, float yaw, int index, Material frame, Material glass, Material hole, Material wood, Material grime)
    {
        var win = Group(w, "Window", p);
        win.localRotation = Quaternion.Euler(0, yaw, 0);
        Box(win, "Window frame", Vector3.zero, new Vector3(1.35f, 1.15f, .06f), frame);
        int kind = index % 4;
        Box(win, "Window pane", new Vector3(0, 0, -.03f), new Vector3(1.15f, .95f, .04f), kind == 1 || kind == 3 ? hole : glass);
        if (kind != 1) { Box(win, "Mullion", new Vector3(0, 0, -.06f), new Vector3(.05f, .95f, .03f), frame); Box(win, "Transom", new Vector3(0, 0, -.06f), new Vector3(1.15f, .05f, .03f), frame); }
        if (kind == 3)
            for (int i = 0; i < 2; i++)
            {
                var board = Box(win, "Window board", new Vector3(0, -.2f + i * .4f, -.08f), new Vector3(1.4f, .18f, .03f), wood);
                board.transform.localRotation = Quaternion.Euler(0, 0, i == 0 ? 9 : -6);
            }
        if (kind == 1)
        {
            var shard = Prim(win, "Glass shard", PrimitiveType.Quad, new Vector3(-.3f, .22f, -.06f), new Vector3(.45f, .4f, 1), glass);
            shard.GetComponent<MeshFilter>().sharedMesh = Triangle();
        }
    }

    static void Fence(Transform root)
    {
        var fence = Group(root, "Chain-link fence", Vector3.zero);
        Material post = Mat("GalvanizedPost", "9A9E9F", .4f), mesh = ChainLink();
        float x0 = WarehouseCenter.x - 7.5f, x1 = WarehouseCenter.x + 7.55f, z0 = 25.8f, z1 = 40f;
        var corners = new[] { new Vector3(x0, 0, z0), new Vector3(x1, 0, z0), new Vector3(x1, 0, z1), new Vector3(x0, 0, z1), new Vector3(x0, 0, z0) };
        int panel = 0;
        for (int c = 0; c < 4; c++)
        {
            var a = corners[c]; var b = corners[c + 1]; float length = (b - a).magnitude; int n = Mathf.CeilToInt(length / 2.6f);
            for (int i = 0; i < n; i++)
            {
                var p0 = Vector3.Lerp(a, b, i / (float)n); var p1 = Vector3.Lerp(a, b, (i + 1) / (float)n);
                Cyl(fence, "Fence post", p0 + Vector3.up * Ground, .045f, 2f, post);
                panel++;
                bool gateGap = c == 0 && Mathf.Abs((p0.x + p1.x) * .5f - (WarehouseCenter.x - 2.2f)) < 1.4f;
                if (panel % 9 == 4 || gateGap) continue; // missing panel / open gate
                var mid = (p0 + p1) * .5f; float len = (p1 - p0).magnitude;
                var cloth = Box(fence, "Chain link", mid + Vector3.up * (Ground + 1f), new Vector3(.02f, 1.9f, len), mesh);
                cloth.transform.localRotation = Quaternion.LookRotation((p1 - p0).normalized);
                if (panel % 7 == 3) { cloth.transform.localRotation *= Quaternion.Euler(0, 0, 11); cloth.transform.localPosition += Vector3.up * -.08f; }
                var rail = Box(fence, "Top rail", mid + Vector3.up * (Ground + 1.98f), new Vector3(.05f, .05f, len), post);
                rail.transform.localRotation = cloth.transform.localRotation;
            }
        }
        // For-sale board hung on the fence facing the square: the building is a future expansion.
        var board = Group(fence, "Sale board", new Vector3(WarehouseCenter.x + 1.6f, 0, z0 - .06f));
        Box(board, "Board", new Vector3(0, Ground + 1.25f, 0), new Vector3(1.9f, 1f, .05f), Mat("SaleBoard", "F1ECE0"));
        Box(board, "Board stripe", new Vector3(0, Ground + 1.62f, -.03f), new Vector3(1.9f, .26f, .02f), Mat("SaleRed", "B93A32"));
        Label(board, "VENDE-SE", new Vector3(0, Ground + 1.62f, -.05f), 0, Color.white, .05f);
        Label(board, "ÁREA DO ARMAZÉM CENTRAL", new Vector3(0, Ground + 1.18f, -.04f), 0, new Color(.2f, .2f, .2f), .026f);
    }

    // ------------------------------------------------------------------ Harbour Quay square
    static void BuildPlaza()
    {
        var root = NewRoot(PlazaName);
        var neighborhood = world.GetComponentInChildren<CheckoutExpansionNeighborhood>(true);
        var lots = new List<CheckoutExpansionNeighborhood.Lot>();
        var storage = world.Find("Warehouse");
        var storageBounds = storage ? BoundsOf(storage, true) : new Bounds(new Vector3(-1.66f, 2, 20.7f), new Vector3(8, 4, 8));
        storageBounds.Expand(new Vector3(1.6f, 0, 1.6f));

        Transform Piece(string name, Vector3 p) => Group(root, name, p);
        // The car park corner (west of the market, x -18.7..-9.5) stays clear: nothing stands where the cars go.
        // East promenade between the market and the cycle track.
        foreach (float z in new[] { -4.5f, 6f }) QuayBench(Piece("Promenade bench", new Vector3(13.6f, 0, z)), Vector3.zero, 270);
        // Planters sit between the promenade trees (City Tree 04/05/06 at z 1.5, -8.7, 10.5), not under them.
        foreach (float z in new[] { -1.8f, 8f }) Planter(Piece("Flower planter", new Vector3(13.6f, 0, z)), Vector3.zero, new Vector3(1.4f, .45f, 1.4f), false, (int)z);
        foreach (float z in new[] { -6f, 3f, 12f, 21f, 30f }) ModernLamp(Piece("Square lamp", new Vector3(15.3f, 0, z)), Vector3.zero);
        // All the cycle racks together on the east promenade, clear of the car park and the loading yard.
        var eastRacks = Piece("Cycle racks", new Vector3(14.9f, 0, -7.2f));
        for (int i = 0; i < 6; i++) BikeHoop(eastRacks, new Vector3(0, 0, i * .8f), 90);
        // Ground the market will grow over: benches and trees in grates around the building.
        foreach (var p in new[] { new Vector3(9.4f, 0, -3.2f), new Vector3(9.4f, 0, 4.6f), new Vector3(-8.2f, 0, 5.8f), new Vector3(-4.2f, 0, 6.8f), new Vector3(2.2f, 0, 6.2f) })
        {
            bool tree = p.z != 4.6f && p.z != 6.8f;
            var piece = Piece(tree ? "Tree and bench" : "Bench", p);
            if (tree) GratedTree(piece, Vector3.zero, (int)(p.x * 7 + p.z));
            // Bench clear of the canopy so the tree never looks planted on it.
            QuayBench(piece, new Vector3(0, 0, tree ? -2.3f : 0), 0);
        }
        // Behind the market, beside the delivery path.
        var linear = Piece("Linear planter", new Vector3(-3.4f, 0, 12.2f));
        Planter(linear, Vector3.zero, new Vector3(5.2f, .5f, 1.1f), false, 3);
        QuayBench(linear, new Vector3(-1.2f, 0, -.95f), 0); QuayBench(linear, new Vector3(1.2f, 0, -.95f), 0);
        GratedTree(Piece("Grated tree", new Vector3(-7.6f, 0, 12.4f)), Vector3.zero, 17);
        var westStrip = Piece("Planter and bench", new Vector3(-13.3f, 0, 15.2f));
        Planter(westStrip, Vector3.zero, new Vector3(2.6f, .5f, 1.1f), false, 5); QuayBench(westStrip, new Vector3(0, 0, -.95f), 0);
        // Premium corner (becomes the purchased park).
        var premium = Piece("Garden square", new Vector3(-12.2f, 0, 21f));
        Planter(premium, new Vector3(0, 0, 1.7f), new Vector3(2.6f, .5f, 2.6f), true, 23);
        QuayBench(premium, new Vector3(-2.4f, 0, 0), 0); QuayBench(premium, new Vector3(2.4f, 0, 0), 0);
        ModernLamp(Piece("Square lamp", new Vector3(-15.3f, 0, 20.5f)), Vector3.zero);
        // Storage ground: a pair of trees and benches until the stock room is bought.
        var storagePiece = Piece("Storage garden", new Vector3(storageBounds.center.x, 0, storageBounds.center.z));
        GratedTree(storagePiece, new Vector3(-2.2f, 0, 0), 29);
        QuayBench(storagePiece, new Vector3(.6f, 0, -1.6f), 0);
        // Loading access ground (trucks use it once the yard is bought).
        foreach (float x in new[] { 12.5f }) GratedTree(Piece("Access tree", new Vector3(x, 0, 28.2f)), Vector3.zero, (int)x);
        BuildHarbour(root, Piece);

        // Each piece gives way to whichever purchase first covers its ground.
        foreach (Transform piece in root)
        {
            var b = BoundsOf(piece);
            var lot = Classify(b, storageBounds);
            if (lot != null) { lot.building = piece.gameObject; lots.Add(lot); piece.name += " [" + lot.area + (lot.area == Area.Market ? " " + lot.replacedAtStage : "") + "]"; }
            Bake(piece);
        }
        if (neighborhood) neighborhood.lots = lots.ToArray();
        Debug.Log("HARBOUR_QUAY_PIECES total=" + root.childCount + " expansionLots=" + lots.Count);
    }

    static CheckoutExpansionNeighborhood.Lot Classify(Bounds b, Bounds storage)
    {
        // From stage 0: ground already under the opening-size shop never shows (it used to poke through the walls).
        for (int stage = 0; stage < Scales.GetLength(0); stage++)
        {
            float w = Scales[stage, 0], d = Scales[stage, 1];
            var probe = new MarketLayout { widthScale = w, depthScale = d };
            var lo = CheckoutMarketLayout.Project(new Vector3(-9.4f, 0, -7.4f), probe); var hi = CheckoutMarketLayout.Project(new Vector3(9.4f, 0, 7.4f), probe);
            var min = new Vector2(lo.x - 1f, lo.z - 1f);
            var max = new Vector2(hi.x + 1f, hi.z + 1f);
            if (Overlaps(b, min, max)) return new CheckoutExpansionNeighborhood.Lot { area = Area.Market, replacedAtStage = stage };
        }
        if (Overlaps(b, new Vector2(-19f, -12.5f), new Vector2(-8.9f, 13.5f))) return new CheckoutExpansionNeighborhood.Lot { area = Area.Parking };
        if (Overlaps(b, Flat2(storage.min), Flat2(storage.max))) return new CheckoutExpansionNeighborhood.Lot { area = Area.Storage };
        bool oldYard = Overlaps(b, new Vector2(2.1f, 15f), new Vector2(16.4f, 25.7f)) || Overlaps(b, new Vector2(4.4f, 25.2f), new Vector2(21.4f, 30.6f));
        bool grandYard = Overlaps(b, GrandYardMin, GrandYardMax);
        if (oldYard && grandYard) return new CheckoutExpansionNeighborhood.Lot { area = Area.BothYards };
        if (grandYard) return new CheckoutExpansionNeighborhood.Lot { area = Area.GrandWarehouse };
        if (oldYard) return new CheckoutExpansionNeighborhood.Lot { area = Area.LoadingYard };
        if (Overlaps(b, new Vector2(-18.7f, 16.9f), new Vector2(-9.5f, 25.1f))) return new CheckoutExpansionNeighborhood.Lot { area = Area.Premium };
        return null;
    }

    // ------------------------------------------------------------------ central warehouse (expansion)
    // The large Tripo warehouse stands on the fenced lot at the back of the block; its loading dock faces
    // east onto a new truck yard with three bays, reached from the east street.
    const string GrandModel = "Assets/Art/Models/MapModels/WarehouseLarge/";
    static readonly Vector2 GrandYardMin = new Vector2(-.4f, 28.4f), GrandYardMax = new Vector2(17.25f, 38.8f);
    const float GrandLength = 15.6f, DockX = -.35f;
    static readonly float[] BayZ = { 30.4f, 33.4f, 36.4f };
    public static float GrandDockYaw = 0; // extra turn if the model's dock end comes in facing the other way

    static void BuildGrandWarehouse()
    {
        var root = NewRoot(CheckoutMarketLayout.GrandWarehouse);
        var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(GrandModel + "WarehouseLarge.fbx"), root);
        model.name = "Warehouse model";
        var material = GrandMaterial();
        foreach (var r in model.GetComponentsInChildren<Renderer>()) r.sharedMaterial = material;
        var t = model.transform;
        var b = BoundsOf(t);
        // Long side along the street (x); the gable end with the dock looks east.
        if (b.size.z > b.size.x) t.rotation = Quaternion.Euler(0, 90, 0) * t.rotation;
        t.rotation = Quaternion.Euler(0, GrandDockYaw, 0) * t.rotation;
        b = BoundsOf(t);
        t.localScale *= GrandLength / b.size.x;
        b = BoundsOf(t);
        t.position += new Vector3(DockX - b.max.x, Ground - b.min.y, WarehouseCenter.z - b.center.z);
        b = BoundsOf(t);
        Debug.Log("GRAND_WAREHOUSE bounds=" + b.min.ToString("F2") + " " + b.max.ToString("F2"));
        foreach (var r in model.GetComponentsInChildren<Renderer>()) r.shadowCastingMode = ShadowCastingMode.On;
        GameObjectUtility.SetStaticEditorFlags(model, (StaticEditorFlags)0); // not batched: the map editor moves these props
        root.gameObject.SetActive(false); // shown by CheckoutMarketLayout once the expansion is bought
        BuildGrandYard(b);
    }

    static Material GrandMaterial()
    {
        string path = GrandModel + "WarehouseLarge.mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.shader = Shader.Find("Standard");
        material.SetTexture("_MainTex", AssetDatabase.LoadAssetAtPath<Texture2D>(GrandModel + "WarehouseLarge_Albedo.jpg"));
        string normal = GrandModel + "WarehouseLarge_Normal.png";
        var importer = AssetImporter.GetAtPath(normal) as TextureImporter;
        if (importer && importer.textureType != TextureImporterType.NormalMap) { importer.textureType = TextureImporterType.NormalMap; importer.SaveAndReimport(); }
        material.SetTexture("_BumpMap", AssetDatabase.LoadAssetAtPath<Texture2D>(normal));
        material.EnableKeyword("_NORMALMAP");
        material.SetFloat("_Glossiness", .15f);
        material.color = Color.white;
        EditorUtility.SetDirty(material);
        return material;
    }

    static void BuildGrandYard(Bounds warehouse)
    {
        var root = NewRoot(CheckoutMarketLayout.GrandYard);
        Material paint = Mat("YardLinePaint", "F5E6B9"), yellow = Mat("SafetyYellow", "E9B93F"), charcoal = Mat("YardStopCharcoal", "354949");
        float rear = warehouse.max.x + .45f;
        // Bays: trucks reverse in with their rear to the dock, cab pointing east (they arrive from the street).
        var bays = Group(root, "Bays", Vector3.zero);
        var trucks = world.Cast<Transform>().Where(x => x.name.StartsWith("Anim_Truck")).OrderBy(x => x.name).ToArray();
        for (int i = 0; i < trucks.Length && i < BayZ.Length; i++)
        {
            var truck = trucks[i];
            var tb = BoundsOf(truck.Find("ReplacementVisual") ?? truck);
            var turn = Quaternion.Euler(0, 90, 0);
            var length = Mathf.Max(tb.size.x, tb.size.z);
            var center = new Vector3(rear + length / 2, 0, BayZ[i]);
            var offset = truck.position - new Vector3(tb.center.x, 0, tb.center.z);
            var bay = new GameObject(truck.name).transform;
            bay.SetParent(bays, false);
            bay.SetPositionAndRotation(new Vector3(center.x, truck.position.y, center.z) + turn * offset, turn * truck.rotation);
        }
        var marks = Group(root, "Markings", Vector3.zero);
        float end = rear + 6.4f;
        for (int i = 0; i <= BayZ.Length; i++)
        {
            float z = BayZ[0] - 1.5f + i * 3f;
            Box(marks, "Bay line", new Vector3((rear + end) / 2, Ground + .02f, z), new Vector3(end - rear, .015f, .1f), paint);
        }
        for (int i = 0; i < BayZ.Length; i++)
        {
            Box(marks, "Wheel stop", new Vector3(rear + .5f, Ground + .09f, BayZ[i]), new Vector3(.22f, .17f, 1.65f), charcoal);
            for (int k = 0; k < 3; k++) Box(marks, "Reflector", new Vector3(rear + .5f, Ground + .18f, BayZ[i] - .6f + k * .6f), new Vector3(.22f, .015f, .28f), yellow);
            Label(marks, (i + 1).ToString(), new Vector3(end + .6f, Ground + .03f, BayZ[i]), 0, paint.color, .12f);
            marks.GetChild(marks.childCount - 1).localRotation = Quaternion.Euler(90, 270, 0);
        }
        // Yellow hatching keeps the dock apron clear, bollards at its ends.
        for (float z = BayZ[0] - 1.4f; z < BayZ[BayZ.Length - 1] + 1.5f; z += .72f)
        {
            var hatch = Box(marks, "Dock hatch", new Vector3(warehouse.max.x + .22f, Ground + .02f, z), new Vector3(.36f, .015f, .1f), yellow);
            hatch.transform.localRotation = Quaternion.Euler(0, 30, 0);
        }
        foreach (float z in new[] { BayZ[0] - 1.8f, BayZ[BayZ.Length - 1] + 1.8f })
        {
            Box(marks, "Dock bollard", new Vector3(rear + .2f, Ground + .45f, z), new Vector3(.16f, .9f, .16f), charcoal);
            Box(marks, "Bollard reflector", new Vector3(rear + .2f, Ground + .7f, z), new Vector3(.18f, .16f, .18f), yellow);
        }
        foreach (var p in new[] { new Vector3(15.8f, 0, 29.2f), new Vector3(15.8f, 0, 37.9f) }) ModernLamp(marks, p);
        // The unloader walks from the dock door to the bays.
        var path = Group(root, "Worker path", Vector3.zero);
        foreach (var (name, p) in new[] { ("Dock door", new Vector3(warehouse.max.x + .15f, .15f, WarehouseCenter.z)), ("Bay apron", new Vector3(rear + .15f, .15f, BayZ[1] - 1.5f)) })
        {
            var point = new GameObject(name).transform; point.SetParent(path, false); point.position = p;
        }
        Bake(marks);
        root.gameObject.SetActive(false);
    }

    static bool Overlaps(Bounds b, Vector2 min, Vector2 max) => b.max.x > min.x && b.min.x < max.x && b.max.z > min.y && b.min.z < max.y;

    static void BuildHarbour(Transform root, Func<string, Vector3, Transform> Piece)
    {
        // Where the old dock basin was: dancing water jets in the paving, between a pair of round flower beds,
        // in front of the café terrace.
        DancingFountain(Piece("Dancing fountain", new Vector3(BasinCenter.x, 0, BasinCenter.y)));
        foreach (float x in new[] { -4.4f, 4.4f })
            Planter(Piece("Quay flower bed", new Vector3(BasinCenter.x + x, 0, BasinCenter.y)), Vector3.zero, new Vector3(2f, .45f, 2f), false, (int)(x * 10));
        // Promenades on both quays and the café terrace beyond the cycle track.
        foreach (float x in new[] { 1.5f, 4.6f, 10.2f, 13.2f })
        {
            QuayBench(Piece("Quay bench", new Vector3(x, 0, 32.3f)), Vector3.zero, 180);
            QuayBench(Piece("Quay bench", new Vector3(x, 0, 39.6f)), Vector3.zero, 0);
        }
        foreach (float x in new[] { 3f, 11.8f }) { ModernLamp(Piece("Quay lamp", new Vector3(x, 0, 31.2f)), Vector3.zero); ModernLamp(Piece("Quay lamp", new Vector3(x, 0, 40.1f)), Vector3.zero); }
        var cafe = Piece("Harbour café", new Vector3(6.2f, 0, 45.8f));
        Kiosk(cafe);
        foreach (float x in new[] { -3.8f, 4.2f, 7.4f }) Terrace(Piece("Café terrace", new Vector3(6.2f + x, 0, 45.4f)));
        for (float x = -14.4f; x < -1f; x += 4.4f)
        {
            GratedTree(Piece("North row tree", new Vector3(x, 0, 45.9f)), Vector3.zero, (int)(x * 3));
            if (x + 2.2f < -1f) QuayBench(Piece("North row bench", new Vector3(x + 2.2f, 0, 45.9f)), Vector3.zero, 0);
        }
        foreach (float x in new[] { 14.4f }) GratedTree(Piece("North row tree", new Vector3(x, 0, 46.4f)), Vector3.zero, (int)(x * 5));
    }

    static void Kiosk(Transform parent)
    {
        Material glass = Glass(), frame = Mat("KioskFrame", "2F3538", .4f), roof = Mat("KioskRoof", "D9D5CC"), counter = Mat("KioskCounter", "A07D55"), sign = Mat("KioskSign", "1E5C6B");
        Box(parent, "Kiosk floor", new Vector3(0, Ground + .06f, 0), new Vector3(4.6f, .12f, 2.8f), Mat("QuayCoping", "B9B4AA"));
        Box(parent, "Kiosk back", new Vector3(0, Ground + 1.35f, 1.3f), new Vector3(4.4f, 2.5f, .12f), counter);
        Box(parent, "Kiosk glass", new Vector3(0, Ground + 1.35f, -1.3f), new Vector3(4.4f, 2.5f, .05f), glass);
        foreach (float x in new[] { -2.2f, 2.2f }) Box(parent, "Kiosk side", new Vector3(x, Ground + 1.35f, 0), new Vector3(.05f, 2.5f, 2.6f), glass);
        foreach (float x in new[] { -2.2f, 0, 2.2f }) Box(parent, "Kiosk mullion", new Vector3(x, Ground + 1.35f, -1.32f), new Vector3(.08f, 2.5f, .08f), frame);
        Box(parent, "Kiosk counter", new Vector3(0, Ground + .55f, -.6f), new Vector3(4f, .9f, .6f), counter);
        Box(parent, "Kiosk roof", new Vector3(0, Ground + 2.72f, -.2f), new Vector3(5.2f, .22f, 3.6f), roof);
        Box(parent, "Kiosk fascia", new Vector3(0, Ground + 2.5f, -1.4f), new Vector3(4.4f, .3f, .06f), sign);
        Label(parent, "HARBOUR CAFÉ", new Vector3(0, Ground + 2.5f, -1.45f), 0, Color.white, .05f);
    }

    static void Terrace(Transform parent)
    {
        Material metal = Mat("TerraceMetal", "3A4043", .4f), top = Mat("TableTop", "E7E3DA"), canvas = Mat("ParasolCanvas", "E4DCC8");
        Cyl(parent, "Table", Vector3.up * Ground, .06f, .72f, metal);
        Cyl(parent, "Table top", Vector3.up * (Ground + .72f), .42f, .04f, top);
        for (int i = 0; i < 3; i++)
        {
            float a = i * Mathf.PI * 2 / 3 + .4f;
            var chair = Group(parent, "Chair", new Vector3(Mathf.Cos(a) * .72f, 0, Mathf.Sin(a) * .72f));
            chair.localRotation = Quaternion.LookRotation(new Vector3(-Mathf.Cos(a), 0, -Mathf.Sin(a)));
            Box(chair, "Chair seat", new Vector3(0, Ground + .44f, 0), new Vector3(.4f, .05f, .4f), metal);
            Box(chair, "Chair back", new Vector3(0, Ground + .68f, -.19f), new Vector3(.4f, .45f, .04f), metal);
            foreach (float x in new[] { -.17f, .17f }) Box(chair, "Chair leg", new Vector3(x, Ground + .22f, 0), new Vector3(.03f, .44f, .36f), metal);
        }
        Cyl(parent, "Parasol pole", Vector3.up * (Ground + .72f), .03f, 1.6f, metal);
        Cyl(parent, "Parasol", Vector3.up * (Ground + 2.2f), 1.25f, .1f, canvas);
        Cyl(parent, "Parasol crown", Vector3.up * (Ground + 2.3f), .6f, .1f, canvas);
    }

    static void QuayBench(Transform parent, Vector3 p, float yaw)
    {
        // Modern square bench: granite block with a timber top.
        var bench = Group(parent, "Quay bench", p);
        bench.localRotation = Quaternion.Euler(0, yaw, 0);
        Box(bench, "Bench block", new Vector3(0, Ground + .2f, 0), new Vector3(1.9f, .4f, .55f), Mat("QuayCoping", "B9B4AA"));
        Box(bench, "Bench timber", new Vector3(0, Ground + .43f, 0), new Vector3(1.8f, .07f, .5f), Mat("BenchTimber", "A77F52"));
        Box(bench, "Bench back", new Vector3(0, Ground + .72f, .24f), new Vector3(1.8f, .5f, .06f), Mat("BenchTimber", "A77F52"));
        bench.gameObject.AddComponent<CheckoutBenchSeat>().seatHeight = Ground + .465f; // Plaza life seats people here.
    }

    static void Planter(Transform parent, Vector3 p, Vector3 size, bool tree, int seed)
    {
        var box = Group(parent, "Planter", p);
        // Square footprints become round beds, so a tree planted in them never looks crooked.
        bool round = Mathf.Approximately(size.x, size.z);
        if (round)
        {
            Cyl(box, "Planter wall", Vector3.up * Ground, size.x / 2, size.y, Mat("PlanterStone", "E3D2B4"));
            Cyl(box, "Planter soil", Vector3.up * (Ground + size.y - .01f), size.x / 2 - .12f, .04f, Mat("PlanterSoil", "5B4A3A"));
        }
        else
        {
            Box(box, "Planter wall", new Vector3(0, Ground + size.y / 2, 0), size, Mat("PlanterStone", "E3D2B4"));
            Box(box, "Planter soil", new Vector3(0, Ground + size.y + .01f, 0), new Vector3(size.x - .2f, .04f, size.z - .2f), Mat("PlanterSoil", "5B4A3A"));
        }
        var random = new Random(seed * 31 + 7);
        int shrubs = Mathf.Max(2, Mathf.RoundToInt(size.x * size.z * 1.2f));
        for (int i = 0; i < shrubs; i++)
        {
            var q = new Vector3(((float)random.NextDouble() - .5f) * (size.x - .5f), Ground + size.y + .12f, ((float)random.NextDouble() - .5f) * (size.z - .5f));
            if (round && new Vector2(q.x, q.z).magnitude > size.x / 2 - .35f) { var flat = new Vector2(q.x, q.z).normalized * (size.x / 2 - .35f); q.x = flat.x; q.z = flat.y; }
            if (tree && new Vector2(q.x, q.z).magnitude < 1.15f) continue; // the tree's own bed
            string[] colors = { "4D7A3A", "5F8C45", "C77A92", "E0B64A" };
            int c = random.Next(colors.Length);
            Prim(box, "Planter shrub", PrimitiveType.Sphere, q, new Vector3(.45f, .35f, .45f), Mat(c < 2 ? "Shrub" + c : "Flower" + c, colors[c]));
        }
        if (tree) Tree(box, box.position + Vector3.up * size.y, 4.6f, seed, "Planter tree");
    }

    static void GratedTree(Transform parent, Vector3 p, int seed)
    {
        // The tree model brings its own round bed of garden stones and mulch.
        var grate = Group(parent, "Tree bed", p);
        Tree(grate, grate.position, 4.4f + (seed % 5) * .3f, seed, "Square tree");
    }

    static void ModernLamp(Transform parent, Vector3 p)
    {
        Material pole = Mat("ModernLampPole", "3A4145", .4f), glow = Mat("ModernLampGlow", "FFF4D8", .2f, "E8C170");
        Cyl(parent, "Lamp pole", p + Vector3.up * Ground, .07f, 4.3f, pole);
        Box(parent, "Lamp arm", p + new Vector3(.3f, Ground + 4.3f, 0), new Vector3(.7f, .08f, .12f), pole);
        Box(parent, "Lamp head", p + new Vector3(.62f, Ground + 4.25f, 0), new Vector3(.5f, .1f, .26f), pole);
        Box(parent, "Lamp light", p + new Vector3(.62f, Ground + 4.19f, 0), new Vector3(.42f, .02f, .2f), glow);
    }

    static void BikeHoop(Transform parent, Vector3 p, float yaw = 0)
    {
        var hoop = Group(parent, "Cycle hoop", p); hoop.localRotation = Quaternion.Euler(0, yaw, 0);
        Material steel = Mat("RackSteel", "9DA3A6", .5f);
        foreach (float x in new[] { -.3f, .3f }) Box(hoop, "Hoop leg", new Vector3(x, Ground + .42f, 0), new Vector3(.05f, .84f, .05f), steel);
        Box(hoop, "Hoop top", new Vector3(0, Ground + .84f, 0), new Vector3(.65f, .05f, .05f), steel);
    }

    // ------------------------------------------------------------------ ground shader
    static void ConfigureGround()
    {
        var material = AssetDatabase.LoadAssetAtPath<Material>(CheckoutCityBuilder.AssetRoot + "CityTiles.mat");
        if (!material) throw new InvalidOperationException("Missing CityTiles.mat");
        material.SetFloat("_RoundaboutEnabled", 1);
        material.SetVector("_Roundabout", new Vector4(CircleCenter.x, CircleCenter.z, 3.4f, 7.5f));
        material.SetFloat("_CityPark", 1);
        material.SetFloat("_HarbourPlaza", 1);
        material.SetVector("_Basin", new Vector4(999, 999, 0, 0)); // No dock basin any more.
        material.SetVector("_DerelictLot", new Vector4(WarehouseCenter.x, 32.9f, 7.45f, 7.3f));
        material.SetVector("_GrandYard", new Vector4((GrandYardMin.x + GrandYardMax.x) / 2, (GrandYardMin.y + GrandYardMax.y) / 2, (GrandYardMax.x - GrandYardMin.x) / 2, (GrandYardMax.y - GrandYardMin.y) / 2));
        material.SetVector("_GrandAccess", new Vector4(19.25f, BayZ[1], 2.05f, 2.2f));
        material.SetFloat("_GrandYardEnabled", 0);
        EditorUtility.SetDirty(material);
    }

    // ------------------------------------------------------------------ review captures
    [MenuItem("Supermarket/Capture Central Park review shots")]
    public static void Review()
    {
        var simulation = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>();
        world = simulation.world;
        var main = Camera.main;
        foreach (var ps in world.GetComponentsInChildren<ParticleSystem>()) ps.Simulate(2.5f, true, true); // jets in mid-flow

        // A new player's view (nothing bought) at the authored market size, then everything bought.
        using (new PurchasePreview(world, new MarketLayout { stage = 3 }))
        {
            foreach (var shot in new (string, Vector3, float)[] {
                ("Overview", new Vector3(0, 0, 2), 36), ("Park", new Vector3(-1, 0, -33), 13.5f), ("Circle", new Vector3(-23.5f, 0, -18.5f), 9.5f),
                ("Warehouse", new Vector3(-9, 0, 31), 11), ("Harbour", new Vector3(7, 0, 38), 10.5f), ("MarketBlock", new Vector3(0, 0, 14), 20),
                ("WestBlock", new Vector3(-33, 0, 19), 17), ("EastBlock", new Vector3(33, 0, 19), 17),
                ("SouthWestCorner", new Vector3(-33, 0, -34), 12), ("SouthEastCorner", new Vector3(33, 0, -34), 12) })
                Shot("ArtSource/TerrainTiles/CentralPark_" + shot.Item1 + ".png", shot.Item2, shot.Item3, main);
            MarketBuilder.Capture("ArtSource/TerrainTiles/CentralPark_GameView.png");
        }
        using (new PurchasePreview(world, new MarketLayout { stage = 4, storage = true, parking = true, loadingYard = true, premium = true, storageLarge = true }))
        {
            Shot("ArtSource/TerrainTiles/CentralPark_GrandWarehouse.png", new Vector3(2, 0, 33), 14, main);
            Shot("ArtSource/TerrainTiles/CentralPark_MarketBlock_Grand.png", new Vector3(0, 0, 14), 20, main);
        }
        using (new PurchasePreview(world, new MarketLayout { stage = 4, storage = true, parking = true, loadingYard = true, premium = true }))
        {
            Shot("ArtSource/TerrainTiles/CentralPark_MarketBlock_AllBought.png", new Vector3(0, 0, 14), 20, main);
            MarketBuilder.Capture("ArtSource/TerrainTiles/CentralPark_GameView_AllBought.png");
        }
        Debug.Log("CENTRAL_PARK_REVIEW_OK");
    }

    // Temporarily shows the scene the way CheckoutMarketLayout projects a purchase state, without
    // moving the market itself; everything is restored on Dispose so the saved scene is untouched.
    sealed class PurchasePreview : IDisposable
    {
        readonly List<(GameObject, bool)> states = new List<(GameObject, bool)>();
        readonly List<Renderer> blocks = new List<Renderer>();
        readonly List<(Transform, Vector3, Quaternion)> moved = new List<(Transform, Vector3, Quaternion)>();
        public PurchasePreview(Transform world, MarketLayout layout)
        {
            void Set(GameObject go, bool active) { if (!go) return; states.Add((go, go.activeSelf)); go.SetActive(active); }
            var neighborhood = world.GetComponentInChildren<CheckoutExpansionNeighborhood>(true);
            if (neighborhood) foreach (var lot in neighborhood.lots) if (lot.building) states.Add((lot.building, lot.building.activeSelf));
            neighborhood?.Apply(layout);
            bool grand = layout.storageLarge, oldYard = layout.loadingYard && !grand;
            Set(world.Find("Warehouse")?.gameObject, layout.storage && !grand);
            Set(world.Find("Loading Yard Details")?.gameObject, oldYard);
            Set(world.Find(CheckoutMarketLayout.GrandWarehouse)?.gameObject, grand);
            Set(world.Find(CheckoutMarketLayout.GrandWarehouseSite)?.gameObject, !grand);
            Set(world.Find(CheckoutMarketLayout.GrandYard)?.gameObject, grand);
            // Trucks sit in their bays for the review shots.
            foreach (Transform truck in world)
            {
                if (!truck.name.StartsWith("Anim_Truck")) continue;
                states.Add((truck.gameObject, truck.gameObject.activeSelf)); moved.Add((truck, truck.position, truck.rotation));
                var bay = grand ? world.Find(CheckoutMarketLayout.GrandYard + "/Bays/" + truck.name) : null;
                if (bay) truck.SetPositionAndRotation(bay.position, bay.rotation);
                truck.gameObject.SetActive(grand || layout.loadingYard);
            }
            Set(world.Find("Expansion Park")?.gameObject, layout.premium);
            int spaces = layout.parking ? (layout.stage >= 3 ? 5 : 3) : 0;
            var parking = world.GetComponentInChildren<CheckoutParkingSpaces>(true);
            if (parking) for (int i = 0; i < parking.spaces.Length; i++) Set(parking.spaces[i], i < spaces);
            foreach (var t in world.GetComponentsInChildren<Transform>(true))
            {
                if (t.name.StartsWith("Parking bay") || t.name == "Parking wheel stop") Set(t.gameObject, layout.parking);
                if (t.name.StartsWith("Banco ") || t.name.StartsWith("City Tree 03") || t.name.StartsWith("Loading garden flowers")) Set(t.gameObject, layout.premium);
                if (t.parent && t.parent.name == "Supplied Delivery Cargo" && t.name != "Carried cardboard box" && t.name != "Warehouse delivery doorstep") Set(t.gameObject, layout.storage && !grand);
                if (t.name.EndsWith("customer vehicle") || t.name.StartsWith("Parking customer vehicle")) Set(t.gameObject, false);
            }
            foreach (var renderer in UnityEngine.Object.FindObjectsByType<UnityEngine.Tilemaps.TilemapRenderer>())
            {
                if (!renderer.sharedMaterial || renderer.sharedMaterial.shader.name != "MarketDay/City Tiles") continue;
                var properties = new MaterialPropertyBlock();
                properties.SetFloat("_ExpansionProjection", 1);
                properties.SetFloat("_LoadingAccessEnabled", oldYard ? 1 : 0);
                properties.SetFloat("_GrandYardEnabled", grand ? 1 : 0);
                properties.SetFloat("_ParkingSpaces", spaces);
                properties.SetVector("_ExpansionFeatures", new Vector4(layout.storage ? 1 : 0, layout.parking ? 1 : 0, oldYard ? 1 : 0, layout.premium ? 1 : 0));
                renderer.SetPropertyBlock(properties); blocks.Add(renderer);
            }
        }
        public void Dispose()
        {
            for (int i = states.Count - 1; i >= 0; i--) if (states[i].Item1) states[i].Item1.SetActive(states[i].Item2);
            foreach (var (t, p, r) in moved) if (t) t.SetPositionAndRotation(p, r);
            foreach (var renderer in blocks) if (renderer) renderer.SetPropertyBlock(null);
        }
    }

    static void Shot(string path, Vector3 focus, float size, Camera main)
    {
        var go = new GameObject("Review camera") { hideFlags = HideFlags.HideAndDontSave };
        var cam = go.AddComponent<Camera>();
        if (main) { cam.clearFlags = main.clearFlags; cam.backgroundColor = main.backgroundColor; }
        cam.orthographic = true; cam.orthographicSize = size; cam.nearClipPlane = .1f; cam.farClipPlane = 250;
        cam.transform.position = focus + new Vector3(28, 33, -38).normalized * 90; cam.transform.LookAt(focus);
        var rt = new RenderTexture(1600, 1000, 24) { antiAliasing = 4 };
        var active = RenderTexture.active;
        cam.targetTexture = rt; cam.Render(); RenderTexture.active = rt;
        var image = new Texture2D(1600, 1000, TextureFormat.RGB24, false);
        image.ReadPixels(new Rect(0, 0, 1600, 1000), 0, 0); image.Apply();
        File.WriteAllBytes(path, image.EncodeToPNG());
        RenderTexture.active = active; cam.targetTexture = null;
        UnityEngine.Object.DestroyImmediate(image); UnityEngine.Object.DestroyImmediate(rt); UnityEngine.Object.DestroyImmediate(go);
    }

    // ------------------------------------------------------------------ helpers
    static void Folder(string parent, string name) { if (!AssetDatabase.IsValidFolder(parent + "/" + name)) AssetDatabase.CreateFolder(parent, name); }

    static Transform NewRoot(string name)
    {
        var root = new GameObject(name).transform;
        root.SetParent(world, false); root.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
        return root;
    }

    // Groups are positioned in their parent's space (every root sits at the world origin).
    static Transform Group(Transform parent, string name, Vector3 localPosition)
    {
        var g = new GameObject(name).transform;
        g.SetParent(parent, false); g.localPosition = localPosition; g.localRotation = Quaternion.identity;
        return g;
    }

    // Textured surface for each material: (texture kind, tint the texture with the hex colour?, extra tint, metallic).
    static readonly Dictionary<string, (string kind, bool useHex, string tint, float metallic)> Surfaces = new Dictionary<string, (string, bool, string, float)>
    {
        {"OldBrick",("brick",false,null,0)}, {"OldBrickDark",("brick",false,"B4A8A2",0)}, {"OldBrickPatch",("brick",false,"FFEDE0",0)},
        {"StainedConcrete",("concrete",false,null,0)}, {"Grime",("concrete",false,"6A625A",0)}, {"RustyRoof",("corrugated_rust",false,null,.2f)},
        {"WeatheredRoof",("corrugated_paint",false,null,.25f)}, {"DirtyGlass",("dirtyglass",false,null,0)}, {"BoardWood",("wood",false,null,0)},
        {"BoardWoodDark",("wood",false,"8A7A6A",0)}, {"RustyDoor",("rust",false,null,.2f)}, {"RustyPipe",("rust",false,"C0A090",.2f)},
        {"RustyDrum",("rust",false,null,.2f)}, {"FadedDrum",("paint",true,null,.2f)}, {"SkipGreen",("paint",true,null,.2f)},
        {"SafetyYellowFaded",("paint",true,null,0)}, {"Weeds",("foliage",false,"D8E0C0",0)}, {"WeedsDry",("foliage",false,"D9C28A",0)},
        {"GalvanizedPost",("brushed",false,"C0C4C4",.6f)}, {"SaleBoard",("paint",true,null,0)}, {"SaleRed",("paint",true,null,0)}, {"FadedPaint",("paint",true,null,0)},
        {"ParkWall",("stone_blocks",false,null,0)}, {"ParkWallCoping",("granite",false,"E6E0D6",0)}, {"GatePier",("stone_blocks",false,"E8E2D8",0)},
        {"BenchSlat",("wood",false,null,0)}, {"CastIron",("castiron",false,null,.35f)}, {"BinGreen",("castiron",false,"7FB08A",.3f)},
        {"Schist",("rock",false,null,0)}, {"SchistDark",("rock",false,"A09A94",0)}, {"BridgeStone",("stone_blocks",false,null,0)},
        {"BridgeStoneDark",("stone_blocks",false,"B8B0A6",0)}, {"LilyPad",("foliage",false,"B8E0A0",0)}, {"Granite",("granite",false,null,0)},
        {"MonumentStone",("stone_blocks",false,"F0EAE0",0)}, {"Bronze",("bronze",false,null,.6f)}, {"Gilded",("gold",false,null,.9f)},
        {"FountainWater",("water",false,null,0)}, {"Shrub",("foliage",false,null,0)}, {"ShrubFlower",("flowers",false,null,0)},
        {"Shrub0",("foliage",false,null,0)}, {"Shrub1",("foliage",false,"D0F0B0",0)}, {"Flower2",("flowers",false,null,0)}, {"Flower3",("flowers",false,"FFF0C0",0)},
        {"CartSteel",("brushed",false,null,.7f)}, {"CartDark",("castiron",false,null,.35f)}, {"CartYellow",("canvas",true,null,0)}, {"CartBlue",("canvas",true,null,0)},
        {"SignPole",("brushed",false,"B8BCBC",.6f)}, {"SignRed",("paint",true,null,0)}, {"SignWhite",("paint",true,null,0)}, {"StreetSignGreen",("paint",true,null,.1f)},
        {"SignBoard",("paint",true,null,.1f)}, {"AwningRed",("awning",true,null,0)}, {"AwningGreen",("awning",true,null,0)}, {"AwningBlue",("awning",true,null,0)},
        {"AwningOchre",("awning",true,null,0)}, {"QuayCoping",("granite",false,null,0)}, {"QuayRail",("castiron",false,null,.4f)}, {"BridgeWhite",("paint",true,null,.2f)},
        {"BridgeDeck",("wood",false,"C8C0B4",0)}, {"HullGreen",("paintedwood",true,null,0)}, {"CabinRed",("paintedwood",true,null,0)}, {"CabinRoof",("paint",true,null,.1f)},
        {"BoatTrim",("paint",true,null,.3f)}, {"HullRed",("paintedwood",true,null,0)}, {"KioskFrame",("castiron",false,"B8C0C4",.4f)}, {"KioskRoof",("brushed",false,"F2F0EA",.3f)},
        {"KioskCounter",("wood",false,null,0)}, {"KioskSign",("paint",true,null,.1f)}, {"TerraceMetal",("castiron",false,"C8CCCC",.4f)}, {"TableTop",("granite",false,"F4F0E8",0)},
        {"ParasolCanvas",("canvas",true,null,0)}, {"BenchTimber",("wood",false,"F0E0D0",0)}, {"PlanterSoil",("mulch",false,null,0)}, {"PlanterStone",("stone_blocks",false,"F4E6CC",0)}, {"TreeGrate",("grate",false,null,.4f)},
        {"ModernLampPole",("castiron",false,"B0B8BC",.45f)}, {"RackSteel",("brushed",false,null,.7f)}, {"FountainPad",("granite",false,"8A8A86",0)},
        {"BridgePath",("granite",false,"D8CCB8",0)}, {"BasinFloor",("stone_blocks",false,"8FA8A8",0)}, {"LilyFlower",("flowers",false,"FFF0F4",0)},
    };

    static Material Mat(string name, string hex, float gloss = .08f, string emission = null)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Root + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        if (emission == null && Surfaces.TryGetValue(name, out var surface) && CheckoutCityParkTextures.Has(surface.kind))
        {
            // Textured, triplanar-projected material with relief (normal map) instead of a flat colour.
            var textures = CheckoutCityParkTextures.Get(surface.kind);
            material.shader = Shader.Find("MarketDay/City Park Triplanar");
            material.SetTexture("_MainTex", textures.albedo);
            material.SetTexture("_BumpMap", textures.normal);
            material.SetFloat("_Tiling", textures.tiling);
            material.SetFloat("_BumpScale", textures.bump);
            material.SetFloat("_Metallic", surface.metallic);
            material.SetFloat("_Glossiness", Mathf.Clamp01(.35f + gloss));
            material.SetFloat("_Variation", surface.kind == "water" ? .04f : .14f);
            material.SetVector("_Scroll", surface.kind == "water" ? new Vector4(.03f, .02f, 0, 0) : Vector4.zero);
            material.color = surface.useHex ? MarketSimulation.C(hex) : surface.tint != null ? MarketSimulation.C(surface.tint) : Color.white;
            EditorUtility.SetDirty(material);
            materials[name] = material;
            return material;
        }
        material.shader = Shader.Find("Standard");
        material.color = MarketSimulation.C(hex);
        material.SetFloat("_Glossiness", gloss);
        if (emission != null)
        {
            material.EnableKeyword("_EMISSION");
            material.SetColor("_EmissionColor", MarketSimulation.C(emission));
            material.globalIlluminationFlags = MaterialGlobalIlluminationFlags.None;
        }
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static Material Transparent(string name, Color color, Texture2D texture = null, Vector2 tiling = default)
    {
        if (materials.TryGetValue(name, out var cached)) return cached;
        string path = Root + name + ".mat";
        var material = AssetDatabase.LoadAssetAtPath<Material>(path);
        if (!material) { material = new Material(Shader.Find("Standard")); AssetDatabase.CreateAsset(material, path); }
        material.color = color; material.SetFloat("_Glossiness", .5f);
        material.SetFloat("_Mode", 2); material.SetOverrideTag("RenderType", "Transparent");
        material.SetInt("_SrcBlend", (int)BlendMode.SrcAlpha); material.SetInt("_DstBlend", (int)BlendMode.OneMinusSrcAlpha); material.SetInt("_ZWrite", 0);
        material.DisableKeyword("_ALPHATEST_ON"); material.EnableKeyword("_ALPHABLEND_ON"); material.DisableKeyword("_ALPHAPREMULTIPLY_ON");
        material.renderQueue = (int)RenderQueue.Transparent;
        if (texture) { material.mainTexture = texture; material.mainTextureScale = tiling; }
        EditorUtility.SetDirty(material);
        materials[name] = material;
        return material;
    }

    static Material Glass() => Transparent("CityGlassPanel", new Color(.72f, .86f, .9f, .32f));

    static Material ChainLink()
    {
        string path = Root + "ChainLink.png";
        if (!File.Exists(path))
        {
            var texture = new Texture2D(64, 64, TextureFormat.RGBA32, false);
            for (int y = 0; y < 64; y++)
                for (int x = 0; x < 64; x++)
                {
                    float a = Mathf.Abs(((x + y) % 32) - 16) < 2 || Mathf.Abs(((x - y + 64) % 32) - 16) < 2 ? .9f : 0f;
                    texture.SetPixel(x, y, new Color(.72f, .74f, .75f, a));
                }
            texture.Apply();
            File.WriteAllBytes(path, texture.EncodeToPNG());
            UnityEngine.Object.DestroyImmediate(texture);
            AssetDatabase.ImportAsset(path);
            var importer = (TextureImporter)AssetImporter.GetAtPath(path);
            importer.alphaIsTransparency = true; importer.wrapMode = TextureWrapMode.Repeat; importer.mipmapEnabled = true;
            importer.SaveAndReimport();
        }
        return Transparent("ChainLink", Color.white, AssetDatabase.LoadAssetAtPath<Texture2D>(path), new Vector2(12, 9));
    }

    static GameObject Prim(Transform parent, string name, PrimitiveType type, Vector3 localPosition, Vector3 scale, Material material)
    {
        var go = GameObject.CreatePrimitive(type);
        go.name = name;
        go.transform.SetParent(parent, false);
        go.transform.localPosition = localPosition; go.transform.localRotation = Quaternion.identity; go.transform.localScale = scale;
        var collider = go.GetComponent<Collider>(); if (collider) UnityEngine.Object.DestroyImmediate(collider);
        go.GetComponent<Renderer>().sharedMaterial = material;
        primitives.Add(go);
        return go;
    }

    static GameObject Box(Transform parent, string name, Vector3 localPosition, Vector3 size, Material material) => Prim(parent, name, PrimitiveType.Cube, localPosition, size, material);

    // Cylinder standing on localBase (bottom centre).
    static GameObject Cyl(Transform parent, string name, Vector3 localBase, float radius, float height, Material material) =>
        Prim(parent, name, PrimitiveType.Cylinder, localBase + Vector3.up * height * .5f, new Vector3(radius * 2, height * .5f, radius * 2), material);

    static void Label(Transform parent, string value, Vector3 localPosition, float yaw, Color color, float size)
    {
        var item = new GameObject(value, typeof(TextMesh));
        item.transform.SetParent(parent, false);
        item.transform.localPosition = localPosition; item.transform.localRotation = Quaternion.Euler(0, yaw, 0);
        var text = item.GetComponent<TextMesh>();
        text.text = value; text.fontSize = 64; text.characterSize = size; text.anchor = TextAnchor.MiddleCenter; text.color = color;
        text.font = Resources.Load<Font>("MarketBold") ?? Resources.GetBuiltinResource<Font>("LegacyRuntime.ttf");
        item.GetComponent<Renderer>().sharedMaterial = text.font.material;
    }

    static Mesh triangle, gable;
    static Mesh Triangle()
    {
        string path = Root + "Meshes/SignTriangle.asset";
        if (triangle) return triangle;
        triangle = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (triangle) return triangle;
        // Point-down give-way triangle, double sided, 1 unit wide.
        triangle = new Mesh { name = "SignTriangle" };
        var v = new[] { new Vector3(-.5f, .29f, 0), new Vector3(.5f, .29f, 0), new Vector3(0, -.58f, 0) };
        triangle.vertices = new[] { v[0], v[1], v[2], v[0], v[1], v[2] };
        triangle.triangles = new[] { 0, 1, 2, 5, 4, 3 };
        triangle.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.forward, Vector3.forward, Vector3.forward };
        triangle.uv = new Vector2[6];
        triangle.RecalculateBounds();
        AssetDatabase.CreateAsset(triangle, path);
        return triangle;
    }

    static Mesh Gable(float halfDepth, float rise)
    {
        string path = Root + "Meshes/WarehouseGable.asset";
        gable = AssetDatabase.LoadAssetAtPath<Mesh>(path);
        if (gable) return gable;
        // Triangle in the local XY plane (width along X), both faces.
        gable = new Mesh { name = "WarehouseGable" };
        var v = new[] { new Vector3(-halfDepth, 0, 0), new Vector3(halfDepth, 0, 0), new Vector3(0, rise, 0) };
        gable.vertices = new[] { v[0], v[1], v[2], v[0], v[1], v[2] };
        gable.triangles = new[] { 0, 2, 1, 3, 4, 5 };
        gable.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.forward, Vector3.forward, Vector3.forward };
        gable.uv = new Vector2[6];
        gable.RecalculateBounds();
        AssetDatabase.CreateAsset(gable, path);
        return gable;
    }

    static void Tree(Transform parent, Vector3 p, float height, int seed, string name = "Park tree")
    {
        var template = treeTemplates[Mathf.Abs(seed) % treeTemplates.Length];
        var source = PrefabUtility.GetCorrespondingObjectFromSource(template.gameObject);
        var go = source ? (GameObject)PrefabUtility.InstantiatePrefab(source, parent) : UnityEngine.Object.Instantiate(template.gameObject, parent);
        go.name = name; go.SetActive(true);
        var t = go.transform;
        t.rotation = Quaternion.AngleAxis((seed * 47) % 360, Vector3.up) * template.rotation;
        t.localScale = template.localScale;
        foreach (var pair in template.GetComponentsInChildren<Renderer>(true).Zip(t.GetComponentsInChildren<Renderer>(true), (a, b) => (a, b)))
            pair.b.sharedMaterials = pair.a.sharedMaterials;
        var b = BoundsOf(t);
        if (b.size.y > .01f) t.localScale *= height / b.size.y;
        PlaceOnGround(t, p);
    }

    static void PlaceOnGround(Transform t, Vector3 p)
    {
        var b = BoundsOf(t);
        t.position += new Vector3(p.x - b.center.x, Mathf.Max(Ground, p.y) - b.min.y, p.z - b.center.z);
    }

    static Bounds BoundsOf(Transform t, bool includeInactive = false)
    {
        var renderers = t.GetComponentsInChildren<Renderer>(includeInactive).Where(r => !(r is ParticleSystemRenderer)).ToArray();
        if (renderers.Length == 0) return new Bounds(t.position, Vector3.zero);
        var b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
        return b;
    }

    static Vector3 Flat(Vector3 v) => new Vector3(v.x, 0, v.z);
    static Vector2 Flat2(Vector3 v) => new Vector2(v.x, v.z);

    // Combines this group's primitives by material into saved meshes, so the scene stays light.
    static void Bake(Transform group)
    {
        var parts = group.GetComponentsInChildren<MeshFilter>(true).Where(f => primitives.Contains(f.gameObject) && f.sharedMesh).ToArray();
        if (parts.Length == 0) return;
        foreach (var byMaterial in parts.GroupBy(p => p.GetComponent<Renderer>().sharedMaterial))
        {
            var combine = byMaterial.Select(p => new CombineInstance { mesh = p.sharedMesh, transform = group.worldToLocalMatrix * p.transform.localToWorldMatrix }).ToArray();
            var mesh = new Mesh { name = group.name + " " + byMaterial.Key.name };
            if (combine.Sum(c => c.mesh.vertexCount) > 65000) mesh.indexFormat = IndexFormat.UInt32;
            mesh.CombineMeshes(combine, true, true);
            mesh.RecalculateBounds();
            string file = Root + "Meshes/" + Safe(group.name) + "_" + (meshCounter++) + ".asset";
            AssetDatabase.CreateAsset(mesh, file);
            var baked = new GameObject(byMaterial.Key.name, typeof(MeshFilter), typeof(MeshRenderer));
            baked.transform.SetParent(group, false);
            baked.GetComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = baked.GetComponent<MeshRenderer>(); renderer.sharedMaterial = byMaterial.Key;
            if (byMaterial.Key.renderQueue >= (int)RenderQueue.Transparent) renderer.shadowCastingMode = ShadowCastingMode.Off;
            GameObjectUtility.SetStaticEditorFlags(baked, (StaticEditorFlags)0); // not batched: the map editor moves these props
        }
        foreach (var part in parts) { primitives.Remove(part.gameObject); UnityEngine.Object.DestroyImmediate(part.gameObject); }
        // Drop now-empty helper groups.
        foreach (var t in group.GetComponentsInChildren<Transform>(true).Reverse().ToArray())
            if (t != group && t.childCount == 0 && t.GetComponents<Component>().Length == 1) UnityEngine.Object.DestroyImmediate(t.gameObject);
    }

    static string Safe(string name) => new string(name.Select(c => char.IsLetterOrDigit(c) ? c : '_').ToArray());
}
