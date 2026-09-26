using System;
using System.Linq;
using Checkout;
using MarketDay;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.AI;

public static class CheckoutMapModelsPlaytest
{
    const string Pending = "CheckoutMapModelsPlaytest.Pending";
    static double started;
    static Vector3[] homes;
    static bool[] moved;
    static bool applied, initialChecks, sawShopper, sawCheckout;
    static Transform shopper;

    public static void Run()
    {
        CheckoutMapModelsBuilder.Apply();
        PreviewCurrentScene();
    }

    [MenuItem("Supermarket/Preview current level")]
    public static void PreviewCurrentScene()
    {
        applied = initialChecks = sawShopper = sawCheckout = false;
        SessionState.SetBool(Pending, true);
        EditorApplication.update -= Tick;
        EditorApplication.update += Tick;
        EditorApplication.isPlaying = true;
    }

    [InitializeOnLoadMethod]
    static void Initialize()
    {
        if (SessionState.GetBool(Pending, false)) EditorApplication.update += Tick;
    }

    static void Tick()
    {
        if (!EditorApplication.isPlaying || EditorApplication.isCompiling) return;
        try
        {
            var bridge = UnityEngine.Object.FindAnyObjectByType<CheckoutBridge>();
            var map = UnityEngine.Object.FindAnyObjectByType<CheckoutMap>();
            if (!bridge || !map) return;
            var world = UnityEngine.Object.FindAnyObjectByType<MarketSimulation>().world;
            var trucks = world.Cast<Transform>().Where(t => t.name.StartsWith("Anim_Truck")).OrderBy(t => t.name).ToArray();
            if (!applied)
            {
                homes = trucks.Select(t => t.position).ToArray();
                moved = new bool[trucks.Length];
                var snapshot = new Snapshot {
                    kind = "snapshot", protocol = 1, session = "map-models-preview", revision = 1, isOpen = true,
                    shelves = new[] { "produce", "dairy", "bakery", "snacks", "drinks", "coffee", "pizza" }.Select(id => new Shelf { id = id, unlocked = true, stock = 10, capacity = 20 }).ToArray(),
                    sectors = new[] { "padaria", "acougue", "peixaria", "queijaria" }.Select(id => new Sector { id = id, unlocked = true }).ToArray(),
                    employees = Array.Empty<Employee>(), jobs = Array.Empty<Job>(), customers = Array.Empty<Customer>(),
                    orders = new[] {
                        new Order { id = "preview-fresh", status = "em-transporte", productCategory = "hortifruti" },
                        new Order { id = "preview-fish", status = "em-transporte", productCategory = "peixes" },
                        new Order { id = "preview-frozen", status = "em-transporte", productCategory = "congelados" },
                    },
                    expansions = Array.Empty<string>(), ownedItems = Array.Empty<string>(), @event = new MarketEvent()
                };
                bridge.Receive(JsonUtility.ToJson(snapshot));
                snapshot.revision = 2;
                snapshot.customers = new[] { new Customer { id = "map-preview-customer", spent = 12,
                    purchases = new[] { new Purchase { shelfId = "snacks", quantity = 1 }, new Purchase { shelfId = "drinks", quantity = 1 } } } };
                bridge.Receive(JsonUtility.ToJson(snapshot));
                shopper = null;
                started = Time.time;
                applied = true;
                return;
            }
            for (int i = 0; i < trucks.Length; i++) moved[i] |= Vector3.Distance(trucks[i].position, homes[i]) > .1f;
            if (Time.time - started < 3) return;
            if (initialChecks)
            {
                // The bridge hands visits to a random walker, so follow whichever one took the preview customer.
                if (!shopper) shopper = UnityEngine.Object.FindObjectsByType<CheckoutWalker>().FirstOrDefault(w => w.CustomerId == "map-preview-customer")?.transform;
                sawShopper |= shopper && shopper.gameObject.activeSelf;
                if (bridge.Queue.Count > 0 && !sawCheckout)
                {
                    sawCheckout = true;
                    MarketBuilder.Capture("/tmp/checkout-counter-in-use.png");
                }
                if (sawShopper && sawCheckout && !shopper.gameObject.activeSelf)
                {
                    MarketBuilder.Capture("/tmp/checkout-map-playtest.png");
                    Debug.Log("CHECKOUT_MAP_PLAYTEST_OK trucks=3 reachableAisles=7 customerVisit=complete");
                    Finish(0);
                }
                else if (Time.time - started > (UnityEngine.Object.FindAnyObjectByType<CheckoutCityTraffic>() ? 360 : 120))
                    throw new Exception("Customer did not finish the shelf, checkout and exit route.");
                return;
            }
            if (trucks.Length != 3) throw new Exception("Expected three delivery trucks.");
            for (int i = 0; i < trucks.Length; i++)
                if (!moved[i]) throw new Exception("Truck no longer moves: " + trucks[i].name);
            foreach (string id in new[] { "produce", "dairy", "bakery", "snacks", "drinks", "coffee", "pizza" })
            {
                var path = new NavMeshPath();
                if (!NavMesh.SamplePosition(new Vector3(-1.75f, .74f, -6f), out var start, 1f, NavMesh.AllAreas) ||
                    !NavMesh.SamplePosition(map.Approach(id), out var end, 1f, NavMesh.AllAreas) ||
                    !NavMesh.CalculatePath(start.position, end.position, NavMesh.AllAreas, path) || path.status != NavMeshPathStatus.PathComplete)
                    throw new Exception("Shelf approach is unreachable: " + id);
            }
            foreach (var approach in new[] { new Vector3(-3.8f, .74f, 2.85f), new Vector3(1.5f, .74f, 2.85f), new Vector3(6.5f, .74f, 2.85f) })
            {
                var path = new NavMeshPath();
                if (!NavMesh.SamplePosition(approach, out var end, .15f, NavMesh.AllAreas)
                    || !NavMesh.CalculatePath(new Vector3(-1.75f, .74f, -6f), end.position, NavMesh.AllAreas, path)
                    || path.status != NavMeshPathStatus.PathComplete)
                    throw new Exception("New sector approach is blocked: " + approach);
            }
            Debug.Log("CHECKOUT_SECTOR_ROUTES_OK counters=3");
            var deliveryPath = new NavMeshPath();
            if (!NavMesh.SamplePosition(new Vector3(4f,.15f,17.2f), out var loading, .3f, NavMesh.AllAreas)
                || !NavMesh.CalculatePath(new Vector3(-1.75f,.74f,-6f), loading.position, NavMesh.AllAreas, deliveryPath)
                || deliveryPath.status != NavMeshPathStatus.PathComplete)
                throw new Exception("Expanded warehouse is unreachable through the service entrance.");
            Debug.Log("CHECKOUT_TERRAIN_ROUTES_OK warehouse=reachable");
            MarketBuilder.Capture("/tmp/checkout-map-playtest.png");
            initialChecks = true;
            Debug.Log("CHECKOUT_MAP_ROUTES_OK trucks=3 reachableAisles=7");
        }
        catch (Exception error) { Debug.LogException(error); Finish(1); }
    }

    static void Finish(int result)
    {
        SessionState.SetBool(Pending, false);
        EditorApplication.update -= Tick;
        if (Application.isBatchMode) EditorApplication.Exit(result);
    }
}
