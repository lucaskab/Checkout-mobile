using System;
using System.Collections.Generic;
using MarketDay;
using UnityEngine;

namespace Checkout
{
    // Live views of the real 3D city for the Delivery app and the packing room (presentation only, no game state):
    //  MapTexture     top-down orthographic render of the whole city, refreshed every ~2 s and on demand (RefreshMap).
    //  WindowTexture  perspective view from the store front across the avenue to the park; rendered only while
    //                 WindowViewActive is true (the packing room sets it).
    //  RoadRoute      shortest path over the real road lanes (avenue, local streets, roundabout), never across blocks.
    //  CustomerDoor   deterministic door of a house or apartment of the neighbourhood, reachable by road.
    public sealed class CheckoutCityViews : MonoBehaviour
    {
        public const int MapSize = 1024, WindowWidth = 960, WindowHeight = 540;

        // Road lanes (CheckoutNeighborhoodTraffic, CheckoutDeliveryTrucks): local streets at x +-22.4 and +-24.6, and the
        // avenue lanes at z -14, -17, -20 and -23 (CheckoutEventTraffic). The network stops LaneMargin inside the city bounds.
        const float LaneInner = 22.4f, LaneOuter = 24.6f, LaneMargin = 3f;
        const float GroundY = .15f, MapHeight = 150f, MapRefreshSeconds = 2f, DoorRefreshSeconds = 2f;
        const float StoreMinDistance = 14f, MaxPullIn = 10f, MaxDoorRoadDistance = 6f, SnapTolerance = .05f, JoinTolerance = .02f;
        const int RingNodes = 32;
        const int UiLayer = 5; // Project layer 5 is "UI"; it is left out of both city cameras.

        static readonly string[] HomeWords = { "resident", "house", "apartment", "flat", "home", "casa", "predio" };
        static readonly string[] ShopWords = { "storefront", "shop", "loja" };
        static readonly string[] NotBuilding = { "vehicle", "car", "driver", "customer", "pedestrian", "worker", "sign", "tree", "bench" };

        // Set by the packing room while its window is on screen: the window camera renders every frame only then.
        public static bool WindowViewActive;

        public static CheckoutCityViews Instance { get; private set; }
        static CheckoutCityStreets streets;
        static RenderTexture mapTexture, windowTexture;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics()
        {
            Instance = null; WindowViewActive = false; streets = null; mapTexture = null; windowTexture = null;
        }

        // Top-down city render (1024 x 1024). Its uv space is WorldToMap; MapWorldRect is the square of the world it covers.
        public static RenderTexture MapTexture { get { EnsureTextures(); return mapTexture; } }
        public static RenderTexture WindowTexture { get { EnsureTextures(); return windowTexture; } }
        public static Rect MapWorldRect => MapRect(CityBounds());

        // World x/z to a 0..1 uv of MapTexture (u to the right, v up, the way RawImage shows it).
        public static Vector2 WorldToMap(Vector3 world)
        {
            Rect rect = MapWorldRect;
            return new Vector2((world.x - rect.xMin) / rect.width, (world.z - rect.yMin) / rect.height);
        }

        // While something shows the map (the delivery app's GPS), it asks for it every frame and the map renders every
        // frame (LateUpdate, after the cars and bikes moved), so it plays like a live view instead of 2 s snapshots.
        static float mapLiveUntil, mapLiveNext;
        const float LiveMapInterval = 1f / 12f;
        float windowNext;
        public static void KeepMapLive() { mapLiveUntil = Time.unscaledTime + .25f; }

        // Renders the map now (it is also rendered every ~2 s by itself).
        public static void RefreshMap()
        {
            if (Instance != null) Instance.RenderMap();
        }

        // Road route from one point to another: the points follow the lanes, start at `from` and end at `to` with a
        // short pull-in onto the kerb. Falls back to the straight line when the roads are not known yet.
        public static List<Vector3> RoadRoute(Vector3 from, Vector3 to)
        {
            try
            {
                List<Vector3> route = Instance != null ? Instance.Route(from, to) : null;
                if (route != null && route.Count >= 2) return route;
            }
            catch (Exception ex)
            {
                Debug.LogWarning("CITY_ROUTE " + ex.Message);
            }
            return new List<Vector3> { Ground(from), Ground(to) };
        }

        // The door of a house or apartment that orders go to: a deterministic pick (by hashing the order id) among the
        // neighbourhood's buildings reachable by road, never the store or the park.
        public static Vector3 CustomerDoor(string orderId)
        {
            uint hash = Hash(orderId);
            try
            {
                CheckoutCityViews self = Instance;
                if (self != null && self.doors.Count > 0) return Ground(self.doors[(int)(hash % (uint)self.doors.Count)]);
            }
            catch (Exception ex)
            {
                Debug.LogWarning("CITY_DOOR " + ex.Message);
            }
            return FallbackDoor(hash);
        }

        // ------------------------------------------------------------------ scene setup and the two cameras
        public void Initialize(CheckoutBridge owner, CheckoutMap mapRef)
        {
            map = mapRef;
            Instance = this;
            streets = FindAnyObjectByType<CheckoutCityStreets>();
            EnsureTextures();

            mapCamera = MakeCamera("City map camera");
            mapCamera.orthographic = true;
            mapCamera.nearClipPlane = 1f;
            mapCamera.farClipPlane = 300f;
            mapCamera.clearFlags = CameraClearFlags.SolidColor;
            mapCamera.backgroundColor = new Color(.24f, .30f, .34f);
            mapCamera.cullingMask = ~(1 << UiLayer);
            mapCamera.allowHDR = false;
            mapCamera.allowMSAA = false;
            mapCamera.useOcclusionCulling = false;
            mapCamera.targetTexture = mapTexture;

            windowCamera = MakeCamera("City window camera");
            windowCamera.fieldOfView = 52f;
            windowCamera.aspect = WindowWidth / (float)WindowHeight;
            windowCamera.nearClipPlane = .05f;
            windowCamera.farClipPlane = 400f;
            windowCamera.clearFlags = CameraClearFlags.Skybox;
            windowCamera.cullingMask = ~(1 << UiLayer);
            windowCamera.allowHDR = false;
            windowCamera.targetTexture = windowTexture;

            mapTimer = 0f;
            doorTimer = 0f;
            RenderMap();
            RefreshDoors();
        }

        Camera MakeCamera(string label)
        {
            GameObject go = new GameObject(label);
            go.transform.SetParent(transform, false);
            Camera cam = go.AddComponent<Camera>();
            cam.enabled = false; // rendered by hand (RenderMap, LateUpdate), never by the engine
            return cam;
        }

        void Update()
        {
            float dt = Time.deltaTime;
            mapTimer -= dt;
            if (mapTimer <= 0f && Time.unscaledTime >= mapLiveUntil)
            {
                mapTimer = MapRefreshSeconds;
                RenderMap();
            }
            doorTimer -= dt;
            if (doorTimer <= 0f)
            {
                doorTimer = DoorRefreshSeconds;
                RefreshDoors();
            }
        }

        // The window is the store front looking across the avenue at the park (CheckoutCityPark), 1.6 m high.
        void LateUpdate()
        {
            // Live map: ~12 renders a second instead of every frame (each render draws the whole city a second time).
            if (Time.unscaledTime < mapLiveUntil && Time.unscaledTime >= mapLiveNext)
            {
                mapLiveNext = Time.unscaledTime + LiveMapInterval;
                mapTimer = MapRefreshSeconds;
                RenderMap();
            }
            if (!WindowViewActive || windowCamera == null || map == null) return;
            if (Time.unscaledTime < windowNext) return; // 20 renders a second is plenty for the view out of the window
            windowNext = Time.unscaledTime + .05f;
            Vector3 entrance = map.Entrance;
            // A little up and to the side of the door (clear of the lamp posts), so the view clears the parked cars and
            // looks over the avenue into the park.
            Vector3 eye = new Vector3(entrance.x + 1.3f, 3.4f, entrance.z - 1.2f);
            Vector3 look = new Vector3((CheckoutCityPark.West + CheckoutCityPark.East) * .5f, 1.2f,
                (CheckoutCityPark.North + CheckoutCityPark.South) * .5f + 2f);
            windowCamera.transform.SetPositionAndRotation(eye, Quaternion.LookRotation(look - eye));
            windowCamera.fieldOfView = 44f;
            windowCamera.Render();
        }

        void OnDestroy()
        {
            if (Instance == this) Instance = null;
            WindowViewActive = false;
        }

        // Shadows are switched off and the delivery bikes hidden (the app draws its own dot) only for this render.
        void RenderMap()
        {
            if (mapCamera == null) return;
            Rect rect = MapRect(CityBounds());
            mapCamera.transform.SetPositionAndRotation(new Vector3(rect.center.x, MapHeight, rect.center.y), Quaternion.Euler(90f, 0f, 0f));
            mapCamera.orthographicSize = rect.height * .5f;
            List<KeyValuePair<Transform, int>> hidden = new List<KeyValuePair<Transform, int>>();
            List<KeyValuePair<Light, LightShadows>> shadows = new List<KeyValuePair<Light, LightShadows>>();
            try
            {
                if (cachedCourier == null || lightsTimer <= 0f)
                {
                    cachedCourier = FindAnyObjectByType<CheckoutCourier>();
                    cachedLights = FindObjectsByType<Light>(FindObjectsSortMode.None);
                    lightsTimer = 2f;
                }
                lightsTimer -= Time.unscaledDeltaTime;
                CheckoutCourier courier = cachedCourier;
                if (courier != null)
                {
                    foreach (Transform child in courier.transform)
                    {
                        if (!child.name.StartsWith("Courier ")) continue;
                        foreach (Transform part in child.GetComponentsInChildren<Transform>(true))
                        {
                            hidden.Add(new KeyValuePair<Transform, int>(part, part.gameObject.layer));
                            part.gameObject.layer = UiLayer;
                        }
                    }
                }
                foreach (Light light in cachedLights)
                {
                    if (light == null || light.shadows == LightShadows.None) continue;
                    shadows.Add(new KeyValuePair<Light, LightShadows>(light, light.shadows));
                    light.shadows = LightShadows.None;
                }
                mapCamera.Render();
            }
            finally
            {
                foreach (KeyValuePair<Transform, int> pair in hidden)
                    if (pair.Key != null) pair.Key.gameObject.layer = pair.Value;
                foreach (KeyValuePair<Light, LightShadows> pair in shadows)
                    if (pair.Key != null) pair.Key.shadows = pair.Value;
            }
        }

        // ------------------------------------------------------------------ city bounds and textures
        static Bounds CityBounds()
        {
            if (streets != null && streets.cityBounds.size.sqrMagnitude > 1f) return streets.cityBounds;
            return new Bounds(new Vector3(0f, 0f, 6f), new Vector3(80f, 1f, 84f));
        }

        // A square around the city, so one uv scale covers both axes.
        static Rect MapRect(Bounds city)
        {
            float half = Mathf.Max(city.size.x, city.size.z) * .5f + 1f;
            return new Rect(city.center.x - half, city.center.z - half, half * 2f, half * 2f);
        }

        static void EnsureTextures()
        {
            if (mapTexture == null)
            {
                mapTexture = new RenderTexture(MapSize, MapSize, 16, RenderTextureFormat.ARGB32);
                mapTexture.name = "City map";
                mapTexture.filterMode = FilterMode.Bilinear;
                mapTexture.wrapMode = TextureWrapMode.Clamp;
                mapTexture.Create();
            }
            if (windowTexture == null)
            {
                windowTexture = new RenderTexture(WindowWidth, WindowHeight, 24, RenderTextureFormat.ARGB32);
                windowTexture.name = "City window";
                windowTexture.filterMode = FilterMode.Bilinear;
                windowTexture.wrapMode = TextureWrapMode.Clamp;
                windowTexture.Create();
            }
        }

        // ------------------------------------------------------------------ road graph
        // Nodes are lane crossings, the roundabout's ring and the lane ends; edges join neighbours along a lane.
        // Roads are two-way (the bikes keep to the lanes, the graph does not make a one-way loop unreachable).
        sealed class RoadGraph
        {
            public readonly List<Vector3> Points = new List<Vector3>();
            public readonly List<List<int>> Adjacent = new List<List<int>>();
            public readonly List<int> EdgeFrom = new List<int>();
            public readonly List<int> EdgeTo = new List<int>();
            public int NodeCount => Points.Count;
        }

        CheckoutMap map;
        Camera mapCamera, windowCamera;
        CheckoutCourier cachedCourier;
        Light[] cachedLights = new Light[0];
        float lightsTimer;
        float mapTimer, doorTimer;
        RoadGraph graph;
        string graphKey = "";

        // Rebuilt when the city bounds, the roundabout or the market layout (era expansions) change.
        RoadGraph Graph()
        {
            CheckoutRoundabout circle = CheckoutRoundabout.Current;
            bool hasCircle = circle != null;
            Bounds city = CityBounds();
            string key = city.min.ToString() + city.max.ToString() + LayoutKey()
                + (hasCircle ? circle.center.ToString() + circle.clipRadius + "/" + circle.travelRadius : "-");
            if (graph == null || key != graphKey)
            {
                graphKey = key;
                Vector2 centre = hasCircle ? new Vector2(circle.center.x, circle.center.z) : Vector2.zero;
                graph = BuildGraph(city, hasCircle, centre, hasCircle ? circle.clipRadius : 0f, hasCircle ? circle.travelRadius : 0f);
            }
            return graph;
        }

        string LayoutKey()
        {
            MarketLayout state = map != null && map.Layout != null ? map.Layout.State : null;
            if (state == null) return "-";
            return state.stage + "/" + state.widthScale + "/" + state.depthScale + "/" + state.storage + "/" + state.parking
                + "/" + state.loadingYard + "/" + state.premium + "/" + state.storageLarge;
        }

        static RoadGraph BuildGraph(Bounds city, bool hasCircle, Vector2 centre, float clipR, float travelR)
        {
            RoadGraph g = new RoadGraph();
            Dictionary<Vector2Int, int> index = new Dictionary<Vector2Int, int>();
            List<int> boundary = new List<int>();
            float z0 = city.min.z + LaneMargin, z1 = city.max.z - LaneMargin;
            float x0 = city.min.x + LaneMargin, x1 = city.max.x - LaneMargin;
            float[] verticals = { -LaneOuter, -LaneInner, LaneInner, LaneOuter };
            float[] horizontals = { CheckoutEventTraffic.CurbLane, CheckoutEventTraffic.InnerWest, CheckoutEventTraffic.InnerEast, CheckoutEventTraffic.CurbEast };
            foreach (float x in verticals) AddLane(g, index, boundary, true, x, z0, z1, horizontals, hasCircle, centre, clipR);
            foreach (float z in horizontals) AddLane(g, index, boundary, false, z, x0, x1, verticals, hasCircle, centre, clipR);
            if (hasCircle) AddRing(g, index, boundary, centre, travelR);
            return g;
        }

        // One straight lane: nodes at its crossings and ends, cut where it enters the roundabout (the ring replaces the island).
        static void AddLane(RoadGraph g, Dictionary<Vector2Int, int> index, List<int> boundary, bool vertical, float fixedValue,
            float lo, float hi, float[] crossings, bool hasCircle, Vector2 centre, float clipR)
        {
            List<float> ts = new List<float> { lo, hi };
            foreach (float c in crossings) if (c > lo && c < hi) ts.Add(c);
            if (hasCircle)
            {
                float across = vertical ? centre.x : centre.y;
                float along = vertical ? centre.y : centre.x;
                float off = fixedValue - across;
                if (Mathf.Abs(off) < clipR)
                {
                    float half = Mathf.Sqrt(clipR * clipR - off * off);
                    ts.Add(along - half);
                    ts.Add(along + half);
                }
            }
            ts.Sort();
            List<int> kept = new List<int>();
            bool any = false;
            float previous = 0f;
            foreach (float t in ts)
            {
                if (t < lo - .001f || t > hi + .001f) continue;
                if (any && t - previous < .001f) continue;
                any = true;
                previous = t;
                Vector3 p = vertical ? new Vector3(fixedValue, GroundY, t) : new Vector3(t, GroundY, fixedValue);
                float d = DistToCentre(p, centre);
                if (hasCircle && d < clipR - JoinTolerance) continue; // inside the roundabout: the ring takes over
                int n = NodeAt(g, index, p);
                if (hasCircle && Mathf.Abs(d - clipR) < JoinTolerance && !boundary.Contains(n)) boundary.Add(n);
                kept.Add(n);
            }
            for (int i = 0; i + 1 < kept.Count; i++)
            {
                if (hasCircle)
                {
                    Vector3 mid = (g.Points[kept[i]] + g.Points[kept[i + 1]]) * .5f;
                    if (DistToCentre(mid, centre) < clipR - JoinTolerance) continue; // a chord across the island
                }
                AddEdge(g, kept[i], kept[i + 1]);
            }
        }

        // The travel ring of the roundabout; every entry point on the outer kerb joins the ring at its own angle.
        static void AddRing(RoadGraph g, Dictionary<Vector2Int, int> index, List<int> boundary, Vector2 centre, float travelR)
        {
            int[] ring = new int[RingNodes];
            for (int k = 0; k < RingNodes; k++)
            {
                float angle = Mathf.PI * 2f * k / RingNodes;
                ring[k] = NodeAt(g, index, new Vector3(centre.x + Mathf.Cos(angle) * travelR, GroundY, centre.y + Mathf.Sin(angle) * travelR));
            }
            for (int k = 0; k < RingNodes; k++) AddEdge(g, ring[k], ring[(k + 1) % RingNodes]);
            foreach (int entry in boundary)
            {
                Vector3 p = g.Points[entry];
                float angle = Mathf.Atan2(p.z - centre.y, p.x - centre.x);
                int slot = Mathf.RoundToInt(angle / (Mathf.PI * 2f) * RingNodes);
                slot = ((slot % RingNodes) + RingNodes) % RingNodes;
                AddEdge(g, entry, ring[slot]);
            }
        }

        static int NodeAt(RoadGraph g, Dictionary<Vector2Int, int> index, Vector3 p)
        {
            Vector2Int key = new Vector2Int(Mathf.RoundToInt(p.x * 100f), Mathf.RoundToInt(p.z * 100f));
            int found;
            if (index.TryGetValue(key, out found)) return found;
            found = g.Points.Count;
            g.Points.Add(new Vector3(p.x, GroundY, p.z));
            g.Adjacent.Add(new List<int>());
            index[key] = found;
            return found;
        }

        static void AddEdge(RoadGraph g, int a, int b)
        {
            if (a == b || g.Adjacent[a].Contains(b)) return;
            g.Adjacent[a].Add(b);
            g.Adjacent[b].Add(a);
            g.EdgeFrom.Add(a);
            g.EdgeTo.Add(b);
        }

        // A graph plus the start and end points snapped onto the road, for one query (the cached graph stays unchanged).
        sealed class Query
        {
            readonly RoadGraph graph;
            public readonly List<Vector3> Points = new List<Vector3>();
            public readonly List<List<int>> Adjacent = new List<List<int>>();

            public Query(RoadGraph g)
            {
                graph = g;
                Points.AddRange(g.Points);
                foreach (List<int> links in g.Adjacent) Adjacent.Add(new List<int>(links));
            }

            // Node index of the road point nearest to p (-1 when there are no roads); `point` is that road point.
            public int Snap(Vector3 p, out Vector3 point)
            {
                float best = float.MaxValue;
                int bestA = -1, bestB = -1;
                Vector3 bestPoint = Ground(p);
                for (int e = 0; e < graph.EdgeFrom.Count; e++)
                {
                    int a = graph.EdgeFrom[e], b = graph.EdgeTo[e];
                    Vector3 q = OnSegment(p, graph.Points[a], graph.Points[b]);
                    float d = Dist(q, p);
                    if (d < best)
                    {
                        best = d;
                        bestA = a;
                        bestB = b;
                        bestPoint = q;
                    }
                }
                point = bestPoint;
                if (bestA < 0) return -1;
                if (Dist(bestPoint, Points[bestA]) < SnapTolerance) { point = Points[bestA]; return bestA; }
                if (Dist(bestPoint, Points[bestB]) < SnapTolerance) { point = Points[bestB]; return bestB; }
                int node = Points.Count;
                Points.Add(bestPoint);
                Adjacent.Add(new List<int> { bestA, bestB });
                Adjacent[bestA].Add(node);
                Adjacent[bestB].Add(node);
                return node;
            }
        }

        static List<int> AStar(List<Vector3> pts, List<List<int>> adj, int start, int goal)
        {
            int count = pts.Count;
            float[] cost = new float[count];
            int[] came = new int[count];
            bool[] closed = new bool[count];
            for (int k = 0; k < count; k++)
            {
                cost[k] = float.MaxValue;
                came[k] = -1;
            }
            cost[start] = 0f;
            List<int> open = new List<int> { start };
            while (open.Count > 0)
            {
                int pick = 0;
                float bestF = float.MaxValue;
                for (int k = 0; k < open.Count; k++)
                {
                    int id = open[k];
                    float f = cost[id] + Dist(pts[id], pts[goal]);
                    if (f < bestF)
                    {
                        bestF = f;
                        pick = k;
                    }
                }
                int current = open[pick];
                open.RemoveAt(pick);
                if (current == goal) break;
                closed[current] = true;
                foreach (int next in adj[current])
                {
                    if (closed[next]) continue;
                    float step = cost[current] + Dist(pts[current], pts[next]);
                    if (step >= cost[next]) continue;
                    cost[next] = step;
                    came[next] = current;
                    if (!open.Contains(next)) open.Add(next);
                }
            }
            if (goal != start && came[goal] < 0) return null;
            List<int> path = new List<int>();
            for (int node = goal; node != -1; node = came[node])
            {
                path.Add(node);
                if (node == start) break;
            }
            path.Reverse();
            return path;
        }

        // Route on the current graph; null when the roads cannot be used (the caller then falls back to a straight line).
        List<Vector3> Route(Vector3 from, Vector3 to)
        {
            RoadGraph g = Graph();
            if (g.NodeCount == 0) return null;
            Query q = new Query(g);
            Vector3 fromRoad, toRoad;
            int a = q.Snap(from, out fromRoad);
            int b = q.Snap(to, out toRoad);
            if (a < 0 || b < 0) return null;
            List<int> nodes = AStar(q.Points, q.Adjacent, a, b);
            if (nodes == null) return null;
            List<Vector3> route = new List<Vector3>();
            AddPoint(route, Ground(from));
            AddPoint(route, fromRoad);
            foreach (int node in nodes) AddPoint(route, q.Points[node]);
            AddPoint(route, toRoad);
            // Curb pull-in: the last leg leaves the lane straight onto the kerb in front of the target.
            if (Dist(toRoad, to) <= MaxPullIn) AddPoint(route, Ground(to));
            return route;
        }

        // ------------------------------------------------------------------ customer doors
        readonly List<Vector3> doors = new List<Vector3>();

        // Doors of the houses and apartments that can be reached by road from the store, away from the store.
        // Storefronts are used only when the neighbourhood has no houses.
        void RefreshDoors()
        {
            doors.Clear();
            if (map == null) return;
            RoadGraph g = Graph();
            if (g.NodeCount == 0) return;
            Vector3 store = map.Entrance;
            List<Vector3> homes = new List<Vector3>();
            List<Vector3> shops = new List<Vector3>();
            CollectDoors(homes, shops);
            List<Vector3> pool = homes.Count > 0 ? homes : shops;
            foreach (Vector3 door in pool)
            {
                if (Dist(door, store) < StoreMinDistance) continue;
                Query q = new Query(g);
                Vector3 storeRoad, doorRoad;
                int s = q.Snap(store, out storeRoad);
                int d = q.Snap(door, out doorRoad);
                if (s < 0 || d < 0 || Dist(doorRoad, door) > MaxDoorRoadDistance) continue;
                if (AStar(q.Points, q.Adjacent, s, d) == null) continue;
                doors.Add(new Vector3(door.x, GroundY, door.z));
            }
        }

        void CollectDoors(List<Vector3> homes, List<Vector3> shops)
        {
            MarketSimulation sim = FindAnyObjectByType<MarketSimulation>();
            if (sim == null || sim.world == null) return;
            string[] groups = { "City Establishments", "Expansion Neighborhood", "Side Block Details" };
            foreach (string group in groups)
            {
                Transform root = sim.world.Find(group);
                if (root == null) continue;
                for (int i = 0; i < root.childCount; i++)
                {
                    Transform child = root.GetChild(i);
                    if (!child.gameObject.activeInHierarchy) continue;
                    string label = child.name.ToLowerInvariant();
                    if (ContainsAny(label, NotBuilding)) continue;
                    bool home = ContainsAny(label, HomeWords);
                    bool shop = !home && ContainsAny(label, ShopWords);
                    if (!home && !shop) continue;
                    Bounds box;
                    if (!Footprint(child, out box)) continue;
                    Vector3 door;
                    if (!RoadsideDoor(box, out door)) continue;
                    if (home) homes.Add(door);
                    else shops.Add(door);
                }
            }
        }

        // The point in front of a building that faces the street (the street is at the x side the building stands on).
        static bool RoadsideDoor(Bounds box, out Vector3 door)
        {
            door = Vector3.zero;
            float cx = box.center.x;
            if (Mathf.Abs(cx) <= CheckoutStreetLayout.LocalCurbOuter) return false;
            float side = Mathf.Sign(cx);
            door = new Vector3(cx - side * (box.extents.x + .5f), GroundY, box.center.z);
            return true;
        }

        static bool Footprint(Transform t, out Bounds box)
        {
            box = new Bounds();
            bool any = false;
            foreach (Renderer r in t.GetComponentsInChildren<Renderer>(true))
            {
                if (r is ParticleSystemRenderer) continue;
                if (!any)
                {
                    box = r.bounds;
                    any = true;
                }
                else box.Encapsulate(r.bounds);
            }
            return any;
        }

        static Vector3 FallbackDoor(uint hash)
        {
            float z = -2f + (float)(hash % 4u) * 8f; // the east footway, clear of the store
            return new Vector3(CheckoutStreetLayout.OuterWalkX, GroundY, z);
        }

        // ------------------------------------------------------------------ small helpers
        static bool ContainsAny(string text, string[] words)
        {
            foreach (string word in words) if (text.Contains(word)) return true;
            return false;
        }

        // FNV-1a: the same order id gives the same door in every session (string.GetHashCode is randomised per run).
        static uint Hash(string text)
        {
            uint hash = 2166136261u;
            if (text == null) return hash;
            for (int i = 0; i < text.Length; i++) hash = unchecked((hash ^ (uint)text[i]) * 16777619u);
            return hash;
        }

        static Vector3 Ground(Vector3 p) => new Vector3(p.x, GroundY, p.z);

        // Distance on the ground plane (x and z).
        static float Dist(Vector3 a, Vector3 b)
        {
            float dx = a.x - b.x, dz = a.z - b.z;
            return Mathf.Sqrt(dx * dx + dz * dz);
        }

        static float DistToCentre(Vector3 p, Vector2 c)
        {
            float dx = p.x - c.x, dz = p.z - c.y;
            return Mathf.Sqrt(dx * dx + dz * dz);
        }

        static Vector3 OnSegment(Vector3 p, Vector3 a, Vector3 b)
        {
            float dx = b.x - a.x, dz = b.z - a.z;
            float len2 = dx * dx + dz * dz;
            float t = len2 < 1e-6f ? 0f : Mathf.Clamp01(((p.x - a.x) * dx + (p.z - a.z) * dz) / len2);
            return new Vector3(a.x + dx * t, GroundY, a.z + dz * t);
        }

        static void AddPoint(List<Vector3> list, Vector3 p)
        {
            if (list.Count == 0 || Dist(list[list.Count - 1], p) > JoinTolerance) list.Add(p);
        }
    }
}
