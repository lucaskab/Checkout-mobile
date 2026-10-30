using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    // The cold room ("câmara fria", docs-drafts/evolucoes-moveis.md 3.2b): where the chilled stock is kept. Its tier comes
    // from the app (snapshot fixtureTiers.coldRoom / coldRoomTemplate); the models are Resources/CheckoutFixtureTiers/
    // coldroom_T1..T4 (customer side -Z: the T2/T3 door, the T4 dock).
    //  - T1 (stock freezer): inside, behind the fixed counter of the small shops (Conveniência, Quitanda). Elsewhere it
    //    stands in the stockroom, out of sight.
    //  - T2/T3: outside, its door against a side wall of the depot (or of the central warehouse once that replaces the
    //    depot; before there is any depot, against the back wall of the shop). The side is the first one where the
    //    room stays on the block and clear of the shop, the sidewalk, the yards, the truck lanes, the storage door and
    //    everything built on the block: opposite the loading side first, then the back, then the others.
    //  - T4: beside the central warehouse, its dock facing the same yard as the trucks, never in a truck lane.
    // While the builders work the new tier shows behind a works fence (CheckoutConstructionSite style tape).
    public static class CheckoutColdRoom
    {
        static Transform root; static string shownKey = "";
        static readonly List<Rect> land = new List<Rect>();
        static readonly Dictionary<string, int> refusals = new Dictionary<string, int>();
        public static string Side { get; private set; } = "";
        public static Bounds Bounds { get; private set; }
        public static bool Shown => root && root.gameObject.activeSelf;
        public static Transform Root => root;

        public static void Apply(Snapshot s, Transform world, CheckoutMarketLayout layout)
        {
            var tiers = s?.fixtureTiers;
            if (tiers == null || world == null || layout == null || CheckoutMapEditor.Open) { Hide(); return; }
            var interior = CheckoutInterior.Active;
            if (!interior) { Hide(); return; }
            string building = tiers.coldRoomBuilding ?? "";
            string template = !string.IsNullOrEmpty(building) ? building : tiers.coldRoomTemplate;
            var state = layout.State;
            string key = template + "|" + building + "|" + CheckoutStall.Small + CheckoutStall.Era + "|" + state.stage + state.storage + state.storageLarge + "|" + CheckoutMarketLayout.StorageBeside;
            if (key == shownKey && (root || string.IsNullOrEmpty(template))) return;
            shownKey = key;
            Hide(false);
            if (string.IsNullOrEmpty(template)) return;
            int tier = template.Length > 0 ? template[template.Length - 1] - '0' : 1;
            // T1 indoors (small shops only); nothing outside before the shop has walls of its own.
            if (tier <= 1) { PlaceIndoors(interior, template); return; }
            if (CheckoutStall.Small && !CheckoutStall.ShopInside) return; // the stalls: no wall to lean on
            // Only on the player's own land (bought and cleared lots, src/data/market-lots.ts): never on a ruin or a lot for sale.
            land.Clear();
            foreach (var lot in s.era?.lotRects ?? System.Array.Empty<LotRect>())
                if (lot != null && (lot.status == "seu" || lot.occupied)) land.Add(Rect.MinMaxRect(lot.x0, lot.z0, lot.x1, lot.z1));
            PlaceOutside(world, layout, interior, template, tier, !string.IsNullOrEmpty(building));
            CheckoutBlockPaths.Invalidate();
        }

        static void Hide(bool forget = true)
        {
            if (root) Object.Destroy(root.gameObject);
            root = null; Side = ""; Bounds = new Bounds();
            if (forget) shownKey = "";
        }

        static GameObject Spawn(CheckoutInterior interior, string template)
        {
            var prefab = interior.TemplateObject(template);
            if (!prefab) { Debug.LogWarning("CHECKOUT_COLDROOM missing model " + template); return null; }
            var go = Object.Instantiate(prefab);
            go.name = "Cold room (" + template + ")"; go.SetActive(true);
            foreach (var c in go.GetComponentsInChildren<Collider>()) Object.Destroy(c);
            return go;
        }

        // ------------------------------------------------------------------ T1: behind the fixed counter
        static void PlaceIndoors(CheckoutInterior interior, string template)
        {
            if (!CheckoutStall.ShopInside || CheckoutStall.PlacedCounter) return;
            var floor = CheckoutStall.InteriorFloor; var counter = CheckoutStall.CounterArea;
            var go = Spawn(interior, template); if (!go) return;
            var piece = go.GetComponent<CheckoutInteriorPiece>();
            float w = piece ? piece.max.x - piece.min.x : 1.25f, d = piece ? piece.max.y - piece.min.y : .75f;
            // Behind the counter (the side away from the door), its back against the back wall, lid towards the clerk.
            float x = Mathf.Clamp(counter.center.x, floor.xMin + w * .5f + .05f, floor.xMax - w * .5f - .05f);
            float z = floor.yMax - d * .5f - .04f;
            if (z - d * .5f < counter.yMax + .55f) { go.SetActive(false); Object.Destroy(go); Side = "no room behind the counter"; return; }
            go.transform.SetPositionAndRotation(new Vector3(x, CheckoutStall.FloorY, z), Quaternion.Euler(0, 180, 0));
            root = go.transform; Side = "indoors";
            Bounds = new Bounds(new Vector3(x, 1, z), new Vector3(w, 2, d));
            CheckoutMarketPaint.Touch(go);
        }

        // ------------------------------------------------------------------ T2–T4: outside
        struct Candidate { public string side; public Vector3 center; public float yaw; public Rect rect; }

        static void PlaceOutside(Transform world, CheckoutMarketLayout layout, CheckoutInterior interior, string template, int tier, bool works)
        {
            var state = layout.State;
            var depot = world.Find("Warehouse"); var grand = world.Find(CheckoutMarketLayout.GrandWarehouse);
            Transform host = null; string hostName;
            if (tier >= 4 && grand && grand.gameObject.activeInHierarchy) { host = grand; hostName = "central warehouse"; }
            else if (depot && depot.gameObject.activeInHierarchy && state.storage && !state.storageLarge) { host = depot; hostName = "depot"; }
            else if (grand && grand.gameObject.activeInHierarchy) { host = grand; hostName = "central warehouse"; }
            else hostName = CheckoutStall.Small ? "small shop" : "shop";
            Rect hostRect;
            if (host) hostRect = FlatBounds(host);
            else if (CheckoutStall.Small) { var f = CheckoutStall.Footprint; hostRect = Rect.MinMaxRect(f.min.x, f.min.z, f.max.x, f.max.z); }
            else
            {
                var lo = CheckoutMarketLayout.Project(new Vector3(-9.4f, 0, -7.4f), state); var hi = CheckoutMarketLayout.Project(new Vector3(9.4f, 0, 7.4f), state);
                hostRect = Rect.MinMaxRect(lo.x - .3f, lo.z, hi.x + .3f, hi.z + .3f);
            }
            var blockers = Blockers(world, layout, host, hostRect);
            refusals.Clear();
            // The Supermercado: a wing of the depot itself (Lucas, option a), along its east wall.
            if (host == depot && host && tier <= 3 && PlaceDepotWing(depot, interior, tier, works, blockers, hostRect)) return;
            // The biggest model of this tier that fits (a T4 owner without the central warehouse gets what fits).
            for (int t = tier; t >= 2; t--)
            {
                var name = "coldroom_T" + t;
                var prefab = interior.TemplateObject(name); if (!prefab) continue;
                var piece = prefab.GetComponent<CheckoutInteriorPiece>();
                var lmin = piece ? piece.min : new Vector2(-1, -1); var lmax = piece ? piece.max : new Vector2(1, 1);
                float w = lmax.x - lmin.x, d = lmax.y - lmin.y;
                foreach (var c0 in Candidates(hostRect, world, layout, w, d, t >= 4 && host == grand))
                {
                    // The model's own footprint (condensers, dock and ramp included, not centred on the pivot) turned to
                    // face the way the side asks, its wall side against the host.
                    var c = Fit(c0, lmin, lmax);
                    if (!Clear(c.rect, blockers, hostRect)) continue;
                    var go = Spawn(interior, name); if (!go) return;
                    go.transform.SetPositionAndRotation(new Vector3(c.center.x, CheckoutInterior.Ground, c.center.z), Quaternion.Euler(0, c.yaw, 0));
                    root = go.transform; Side = hostName + " · " + c.side + (t < tier ? " (T" + t + ", no room for T" + tier + ")" : "");
                    Bounds = new Bounds(new Vector3(c.rect.center.x, 1.5f, c.rect.center.y), new Vector3(c.rect.width, 3, c.rect.height));
                    if (works) Fence(go.transform, lmin, lmax);
                    CheckoutMarketPaint.Touch(go);
                    Debug.Log("CHECKOUT_COLDROOM " + name + " at " + Side + " " + c.rect);
                    return;
                }
            }
            Side = "no free side at the " + hostName + " " + hostRect.ToString("0.0") + " (" + string.Join(", ", refusals.Select(r => r.Key + " x" + r.Value)) + "): kept in the stockroom";
            Debug.LogWarning("CHECKOUT_COLDROOM " + template + ": " + Side);
        }

        // ------------------------------------------------------------------ T2/T3 at the depot: its own wing
        // coldroom_depotwing_T2/T3 are modelled in the depot mesh's own space (pivot = Depot_74x71's pivot): a shallow
        // insulated wing along the east wall (≤ 1.49 m out, inside lot C2, clear of the truck drive), the cladding round the
        // south-east corner, the condensers on the depot roof. Its door is through the depot's wall, from inside.
        static bool PlaceDepotWing(Transform depot, CheckoutInterior interior, int tier, bool works, List<Rect> blockers, Rect hostRect)
        {
            string name = "coldroom_depotwing_T" + Mathf.Clamp(tier, 2, 3);
            if (!interior.TemplateObject(name)) return false;
            var mesh = depot.GetComponentsInChildren<MeshFilter>(true).FirstOrDefault(f => f.sharedMesh && f.sharedMesh.name.StartsWith("Depot_74x71"));
            if (!mesh) { Refuse("no depot mesh"); return false; }
            var go = Spawn(interior, name); if (!go) return false;
            var at = mesh.transform;
            go.transform.SetPositionAndRotation(at.position, at.rotation); go.transform.localScale = at.lossyScale;
            // Its ground footprint (the roof condensers stand on the depot).
            bool first = true; var b = new Bounds(at.position, Vector3.zero);
            foreach (var r in go.GetComponentsInChildren<Renderer>())
            {
                if (r.bounds.min.y > 2.5f) continue;
                if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds);
            }
            var rect = Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z);
            // (the cladding on the depot's own walls is inside the host: only the part that stands out must be clear)
            var outside = Rect.MinMaxRect(Mathf.Max(rect.xMin, hostRect.xMax - .05f), rect.yMin, rect.xMax, rect.yMax);
            if (outside.width > .1f && !Clear(outside, blockers, hostRect)) { Object.Destroy(go); return false; }
            root = go.transform; Side = "depot · east wing";
            Bounds = new Bounds(new Vector3(outside.center.x, 1.5f, outside.center.y), new Vector3(Mathf.Max(.1f, outside.width), 3, outside.height));
            var piece = go.GetComponent<CheckoutInteriorPiece>();
            if (works && piece) Fence(go.transform, piece.min, piece.max);
            CheckoutMarketPaint.Touch(go);
            Debug.Log("CHECKOUT_COLDROOM " + name + " at the depot's east wall " + outside);
            return true;
        }

        static Rect FlatBounds(Transform t)
        {
            bool first = true; var b = new Bounds(t.position, Vector3.zero);
            foreach (var r in t.GetComponentsInChildren<Renderer>())
            {
                if (!r.enabled || r.forceRenderingOff || r is ParticleSystemRenderer) continue;
                if (r.bounds.min.y > 2.5f) continue; // roof units, signs, antennas
                if (first) { b = r.bounds; first = false; } else b.Encapsulate(r.bounds);
            }
            return Rect.MinMaxRect(b.min.x, b.min.z, b.max.x, b.max.z);
        }

        // The four sides of the host, the preferred ones first. T2/T3: the room's -Z (its door) faces the wall and goes
        // through it, the loading side is never used. T4: its back against the yard-facing wall beside the ramp, the dock
        // (-Z) facing the yard.
        static IEnumerable<Candidate> Candidates(Rect host, Transform world, CheckoutMarketLayout layout, float w, float d, bool dock)
        {
            string loading = LoadingSide(host, world, layout);
            string opposite = loading == "north" ? "south" : loading == "south" ? "north" : loading == "east" ? "west" : "east";
            // (behind a shop the room hides from the game's camera: its sides come first there)
            bool shop = !layout.State.storage;
            var order = dock ? new List<string> { loading, "east", "west", "north", "south" }
                : shop ? new List<string> { "east", "west", "north" }
                : new List<string> { opposite, "east", "north", "west", "south" };
            const float gap = .03f;
            foreach (var side in order.Distinct())
            {
                if (!dock && side == loading) continue;
                // Several spots along the wall: the middle (not for the T4: the ramp is there), then towards the corners.
                var along = dock ? new[] { .3f, -.3f, .45f, -.45f, .6f, -.6f } : new[] { 0f, .3f, -.3f, .45f, -.45f };
                foreach (var t in along)
                {
                    bool ns = side == "north" || side == "south";
                    float run = ns ? host.width : host.height;
                    float o = Mathf.Clamp(t * run, -(run - w) * .5f - w * .5f, (run - w) * .5f + w * .5f);
                    Vector2 c; float yawIn;
                    switch (side)
                    {
                        case "north": c = new Vector2(host.center.x + o, host.yMax + d * .5f + gap); yawIn = 0; break;
                        case "south": c = new Vector2(host.center.x + o, host.yMin - d * .5f - gap); yawIn = 180; break;
                        case "east": c = new Vector2(host.xMax + d * .5f + gap, host.center.y + o); yawIn = 90; break;
                        default: c = new Vector2(host.xMin - d * .5f - gap, host.center.y + o); yawIn = 270; break;
                    }
                    var r = ns ? Rect.MinMaxRect(c.x - w * .5f, c.y - d * .5f, c.x + w * .5f, c.y + d * .5f) : Rect.MinMaxRect(c.x - d * .5f, c.y - w * .5f, c.x + d * .5f, c.y + w * .5f);
                    yield return new Candidate { side = side + (t == 0 ? "" : t > 0 ? "+" : "-") + Mathf.Abs(t).ToString("0.00"), center = new Vector3(c.x, 0, c.y), yaw = dock ? yawIn + 180 : yawIn, rect = r };
                }
            }
        }

        // Where the trucks load: the side of the host nearest the bays (central warehouse) or the storage door (depot).
        static string LoadingSide(Rect host, Transform world, CheckoutMarketLayout layout)
        {
            var bays = world.Find(CheckoutMarketLayout.GrandYard + "/Bays");
            if (layout.State.storageLarge && bays && bays.childCount > 0)
            {
                var mean = Vector3.zero; foreach (Transform b in bays) mean += b.position; mean /= bays.childCount;
                return Nearest(host, new Vector2(mean.x, mean.z));
            }
            if (layout.State.storage) { var door = layout.StorageDoor; return Nearest(host, new Vector2(door.x, door.z)); }
            return "south"; // the shop's front: never against it
        }

        // Moves the pivot so the turned footprint [lmin, lmax] covers the candidate's rect (same size), flush with the wall.
        static Candidate Fit(Candidate c, Vector2 lmin, Vector2 lmax)
        {
            var q = Quaternion.Euler(0, c.yaw, 0);
            float x0 = float.MaxValue, z0 = float.MaxValue, x1 = float.MinValue, z1 = float.MinValue;
            foreach (var p in new[] { new Vector3(lmin.x, 0, lmin.y), new Vector3(lmax.x, 0, lmin.y), new Vector3(lmin.x, 0, lmax.y), new Vector3(lmax.x, 0, lmax.y) })
            { var r = q * p; x0 = Mathf.Min(x0, r.x); x1 = Mathf.Max(x1, r.x); z0 = Mathf.Min(z0, r.z); z1 = Mathf.Max(z1, r.z); }
            var pivot = new Vector3(c.rect.center.x - (x0 + x1) * .5f, 0, c.rect.center.y - (z0 + z1) * .5f);
            c.center = pivot;
            c.rect = Rect.MinMaxRect(pivot.x + x0, pivot.z + z0, pivot.x + x1, pivot.z + z1);
            return c;
        }

        static string Nearest(Rect r, Vector2 p)
        {
            float n = Mathf.Abs(p.y - r.yMax), s = Mathf.Abs(p.y - r.yMin), e = Mathf.Abs(p.x - r.xMax), w = Mathf.Abs(p.x - r.xMin);
            float m = Mathf.Min(Mathf.Min(n, s), Mathf.Min(e, w));
            return m == n ? "north" : m == s ? "south" : m == e ? "east" : "west";
        }

        // Everything the room must stay clear of, in world XZ.
        static List<Rect> Blockers(Transform world, CheckoutMarketLayout layout, Transform host, Rect hostRect)
        {
            var list = new List<Rect>();
            var state = layout.State;
            if (CheckoutStall.Small)
            {
                var court = CheckoutStall.Court; list.Add(Rect.MinMaxRect(court.min.x, court.min.z, court.max.x, Mathf.Min(court.max.z, CheckoutStall.Footprint.min.z)));
                // the shop's front, with room to walk in (its sides and back are walls the room can lean on)
                var f = CheckoutStall.Footprint; list.Add(Rect.MinMaxRect(f.min.x - 1.2f, f.min.z - 1.5f, f.max.x + 1.2f, f.min.z + .6f));
            }
            else
            {
                // The shop with its entrance steps and the sidewalk, and the corridor of the rear service door.
                var lo = CheckoutMarketLayout.Project(new Vector3(-9.4f, 0, -10.6f), state); var hi = CheckoutMarketLayout.Project(new Vector3(9.4f, 0, 7.4f), state);
                // (leaning on the shop itself, before there is a depot: only its front and sides stay clear)
                list.Add(Rect.MinMaxRect(lo.x - .6f, lo.z - 1.5f, hi.x + .6f, host ? hi.z + .6f : hi.z - .05f));
                var rear = CheckoutMarketLayout.Project(new Vector3(CheckoutInterior.RearDoorX, 0, 8.8f), state);
                list.Add(Rect.MinMaxRect(rear.x - 1.3f, rear.z - .5f, rear.x + 1.3f, rear.z + 4f));
            }
            // The avenue's sidewalk along the front of the block.
            list.Add(Rect.MinMaxRect(-40, -40, 40, CheckoutBlockPaths.MinZ + .6f));
            // Truck lanes and stops of the yard in use (CheckoutDeliveryTrucks).
            bool depotYard = state.storage && !state.storageLarge && state.stage <= 2;
            if (depotYard)
            {
                float z0 = CheckoutDeliveryTrucks.DepotDriveZ0, z1 = CheckoutDeliveryTrucks.DepotDriveZ1;
                list.Add(Rect.MinMaxRect(5.75f, z0 - .4f, 22f, z1 + .4f));
                list.Add(Rect.MinMaxRect(CheckoutDeliveryTrucks.DepotRearX - .6f, CheckoutDeliveryTrucks.DepotTruckZ - 2f, CheckoutDeliveryTrucks.DepotRearX + 9f, CheckoutDeliveryTrucks.DepotTruckZ + 2f));
            }
            if (state.storageLarge)
            {
                var bays = world.Find(CheckoutMarketLayout.GrandYard + "/Bays");
                if (bays)
                    foreach (Transform bay in bays)
                    {
                        // the truck at its bay (about 8.5 m long, backing in) and its way out to the street
                        var fwd = bay.forward; fwd.y = 0; fwd = fwd.sqrMagnitude > .01f ? fwd.normalized : Vector3.forward;
                        var a = bay.position - fwd * 1.5f; var b = bay.position + fwd * 10f;
                        list.Add(Rect.MinMaxRect(Mathf.Min(a.x, b.x) - 1.6f, Mathf.Min(a.z, b.z) - 1.6f, Mathf.Max(a.x, b.x) + 1.6f, Mathf.Max(a.z, b.z) + 1.6f));
                        list.Add(Rect.MinMaxRect(Mathf.Min(bay.position.x, 12f) - 1.6f, bay.position.z - 1.8f, 22.4f, bay.position.z + 1.8f));
                    }
                list.Add(Rect.MinMaxRect(12f, 28.4f, 22.4f, 34.8f)); // gate and turning area
                var path = world.Find(CheckoutMarketLayout.GrandYard + "/Worker path");
                if (path) foreach (Transform p in path) list.Add(new Rect(p.position.x - .9f, p.position.z - .9f, 1.8f, 1.8f));
            }
            // The storage door and the clerks' walk from it.
            var door = layout.StorageDoor;
            if (state.storage) list.Add(Rect.MinMaxRect(door.x - 1.6f, door.z - 2.5f, door.x + 1.6f, door.z + 2.5f));
            // Decorations the player placed on the block.
            foreach (var it in CheckoutInterior.Active.items.Values)
                if (it.root && it.outside) { var f = CheckoutInterior.Active.FootprintOf(it); list.Add(new Rect(f.c.x - f.hx - .2f, f.c.y - f.hz - .2f, (f.hx + .2f) * 2, (f.hz + .2f) * 2)); }
            return list;
        }

        static bool Refuse(string why) { refusals.TryGetValue(why, out var n); refusals[why] = n + 1; return false; }

        static bool Clear(Rect r, List<Rect> blockers, Rect host)
        {
            // On the block, off the streets.
            var block = CheckoutInterior.BlockRect;
            if (r.xMin < block.xMin || r.xMax > block.xMax || r.yMin < block.yMin || r.yMax > block.yMax) return Refuse("off the block");
            for (int i = 0; i < blockers.Count; i++) if (r.Overlaps(blockers[i])) return Refuse("blocker " + i);
            // The player's land only.
            for (float x = r.xMin + .05f; x <= r.xMax; x += Mathf.Max(.1f, (r.width - .1f) / 4))
                for (float z = r.yMin + .05f; z <= r.yMax; z += Mathf.Max(.1f, (r.height - .1f) / 4))
                    if (!land.Any(l => l.Contains(new Vector2(x, z)))) return Refuse("not the player's land");
            // Buildings, trees, benches, lamps (sampled; the host's own wall is next to it).
            for (float x = r.xMin + .45f; x <= r.xMax - .45f + .001f; x += .5f)
                for (float z = r.yMin + .45f; z <= r.yMax - .45f + .001f; z += .5f)
                    if (!CheckoutBlockPaths.FixedFree(new Vector3(x, 0, z)) && !NearHost(x, z, host)) return Refuse("built-up");
            return true;
        }

        // Points within 1.1 m of the host count as the host's own margin (the paths grid blocks round every building).
        static bool NearHost(float x, float z, Rect host)
        {
            float dx = Mathf.Max(host.xMin - x, 0, x - host.xMax), dz = Mathf.Max(host.yMin - z, 0, z - host.yMax);
            return dx * dx + dz * dz < 1.21f;
        }

        // A works fence round the room while the builders put it up.
        static void Fence(Transform room, Vector2 lmin, Vector2 lmax)
        {
            float w = lmax.x - lmin.x, d = lmax.y - lmin.y; var mid = new Vector3((lmin.x + lmax.x) * .5f, 0, (lmin.y + lmax.y) * .5f);
            var mat = new Material(Shader.Find("Standard")) { name = "FT_Works_Tape", color = new Color(.96f, .76f, .2f) };
            var fence = new GameObject("Works fence").transform; fence.SetParent(room, false); fence.localPosition = mid;
            void Rail(Vector3 at, Vector3 size)
            {
                var q = GameObject.CreatePrimitive(PrimitiveType.Cube); Object.Destroy(q.GetComponent<Collider>());
                q.transform.SetParent(fence, false); q.transform.localPosition = at; q.transform.localScale = size;
                var r = q.GetComponent<Renderer>(); r.sharedMaterial = mat; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            }
            float hx = w * .5f + .25f, hz = d * .5f + .25f;
            foreach (var y in new[] { .45f, .85f })
            {
                Rail(new Vector3(0, y, -hz), new Vector3(hx * 2, .06f, .03f)); Rail(new Vector3(0, y, hz), new Vector3(hx * 2, .06f, .03f));
                Rail(new Vector3(-hx, y, 0), new Vector3(.03f, .06f, hz * 2)); Rail(new Vector3(hx, y, 0), new Vector3(.03f, .06f, hz * 2));
            }
            foreach (var x in new[] { -hx, hx }) foreach (var z in new[] { -hz, hz }) Rail(new Vector3(x, .5f, z), new Vector3(.06f, 1f, .06f));
        }
    }
}
