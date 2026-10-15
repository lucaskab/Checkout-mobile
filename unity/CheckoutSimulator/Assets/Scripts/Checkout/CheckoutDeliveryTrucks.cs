using System;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;

namespace Checkout
{
    // The suppliers' trucks (Anim_Truck_5 / 8 / 11): where each one unloads for the market's current layout, how it
    // gets there along the city's streets (forwards, then backing onto its bay) and how it drives off again, plus the
    // delivery worker's walk between the storage door and the truck's tail. Presentation only: CheckoutMap decides
    // which truck comes for which order and the economy decides when it is done.
    //
    //  mercadinho (no storage)   no yard of its own: the truck stops at the avenue curb in front of the shop and the
    //                            parcels go in through the front door; cars swerve round it like round an event.
    //  supermercado (depot, C2)  the depot stands on lot C2 beside the shop; the truck comes down the east street,
    //                            backs in across the sidewalk and stops alongside it (lot C1 is the car park).
    //  hipermercado (central)    three docks on the central warehouse's yard (rows 3-4), in from the east street.
    // A truck faces its own +Z; its rear (cargo door) is at the -Z end of its body.
    public sealed class CheckoutDeliveryTrucks : MonoBehaviour
    {
        public static CheckoutDeliveryTrucks Current { get; private set; }
        public enum Yard { Curb, Depot, Grand, OldYard }
        public Yard Kind { get; private set; } = Yard.Curb;

        enum State { Away, Arriving, Docked, Leaving }
        sealed class Truck
        {
            public Transform t;
            public Bounds box;                 // body in the truck's own space
            public float y;                    // pivot height (wheels on the road)
            public Vector3 sceneHome; public Quaternion sceneRotation;
            public Vector3 home; public Quaternion rotation;
            public int spot;
            public State state;
            public readonly List<Vector3> path = new List<Vector3>();
            public readonly List<bool> back = new List<bool>();
            public int index; public float speed; public float since;
            public Vector3 RearLocal => new Vector3(box.center.x, 0, box.min.z);
            public float Length => box.size.z * Mathf.Abs(t.lossyScale.z);
        }
        readonly Dictionary<string, Truck> trucks = new Dictionary<string, Truck>();
        Transform world; MarketDeliveryWorker worker; Func<Vector3> entrance;
        Bounds city = new Bounds(new Vector3(0, 0, 6), new Vector3(80, 1, 84));
        MarketLayout layout;
        float curbRear;                        // the curb stop in use (x of the truck's tail)

        // Streets (CheckoutStreetLayout): east street southbound x 22.4, northbound 24.6; avenue westbound curb lane
        // z -14 and inner lane -17. There is no street behind the block.
        const float EastSouth = 22.4f, AvenueCurb = -14f, AvenueInner = -17f;
        // Supermarket depot yard on lot C2: the truck's tail stops by the corridor between the shop and the depot.
        public const float DepotTruckZ = 5.85f, DepotRearX = 8.3f, DepotDriveZ0 = 4.55f, DepotDriveZ1 = 7.4f;
        // Curb stops for the small markets (x of the truck's tail; it faces west): east of the entrance crossing,
        // in front of A1, or further east. The first one an event leaves free is used.
        static readonly float[] CurbStops = { 8.4f, -3.4f, 19.2f };

        public IEnumerable<Transform> All => trucks.Values.Select(v => v.t).Where(t => t);
        /// <summary>Where the suppliers panel opens when the player taps the yard.</summary>
        public Vector3 SuppliersSpot { get; private set; } = new Vector3(3, 1, 18);

        public void Initialize(Transform root, MarketDeliveryWorker delivery, Func<Vector3> door)
        {
            Current = this; world = root; worker = delivery; entrance = door;
            var streets = FindAnyObjectByType<CheckoutCityStreets>();
            if (streets && streets.cityBounds.size.sqrMagnitude > 1) city = streets.cityBounds;
            foreach (Transform t in world)
            {
                if (!t.name.StartsWith("Anim_Truck")) continue;
                var tr = new Truck { t = t, y = t.position.y, sceneHome = t.position, sceneRotation = t.rotation, home = t.position, rotation = t.rotation };
                tr.box = LocalBox(t);
                trucks[t.name] = tr;
                t.gameObject.SetActive(false);
            }
            if (worker) worker.approach = Approach;
        }

        void OnDestroy() { if (Current == this) Current = null; CheckoutEventTraffic.ClearDeliveryBlock(); }

        // Body of a truck in its own space from the meshes (works while it is hidden).
        static Bounds LocalBox(Transform t)
        {
            bool first = true; var box = new Bounds(Vector3.zero, new Vector3(2.4f, 3, 7));
            void Add(Mesh mesh, Transform part)
            {
                if (!mesh) return;
                var b = mesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z);
                    var l = t.InverseTransformPoint(part.TransformPoint(c));
                    if (first) { box = new Bounds(l, Vector3.zero); first = false; } else box.Encapsulate(l);
                }
            }
            foreach (var mf in t.GetComponentsInChildren<MeshFilter>(true)) Add(mf.sharedMesh, mf.transform);
            foreach (var sm in t.GetComponentsInChildren<SkinnedMeshRenderer>(true)) Add(sm.sharedMesh, sm.transform);
            return box;
        }

        Vector3 RearWorld(Truck tr) => tr.t.TransformPoint(tr.RearLocal);
        /// <summary>Where the delivery worker stands to take a parcel out of this truck: just behind its tail.</summary>
        public Vector3 Approach(Transform t)
        {
            if (!t || !trucks.TryGetValue(t.name, out var tr)) return t ? t.position : Vector3.zero;
            var back = -t.forward; back.y = 0; back.Normalize();
            var p = RearWorld(tr) + back * .75f; p.y = .15f;
            return p;
        }
        public Vector3 Home(Transform t) => t && trucks.TryGetValue(t.name, out var tr) ? tr.home : t ? t.position : Vector3.zero;
        public Quaternion HomeRotation(Transform t) => t && trucks.TryGetValue(t.name, out var tr) ? tr.rotation : Quaternion.identity;

        // Pivot that puts the truck's tail on `rear` facing `heading`.
        Vector3 PivotFor(Truck tr, Vector3 rear, Vector3 heading, out Quaternion rotation)
        {
            heading.y = 0; rotation = Quaternion.LookRotation(heading.normalized);
            var p = rear - rotation * Vector3.Scale(tr.RearLocal, tr.t.lossyScale);
            p.y = tr.y; return p;
        }
        Vector3 R(Truck tr, float x, float z) => new Vector3(x, tr.y, z);

        // ------------------------------------------------------------------ layout
        /// <summary>Called by CheckoutMarketLayout after every layout change.</summary>
        public void Configure(CheckoutMarketLayout market, MarketLayout next)
        {
            layout = next;
            var kind = next.storageLarge ? Yard.Grand : next.storage ? (next.stage <= 2 ? Yard.Depot : Yard.OldYard) : Yard.Curb;
            bool changed = kind != Kind; Kind = kind;
            var grandBays = world.Find(CheckoutMarketLayout.GrandYard + "/Bays");
            foreach (var tr in trucks.Values)
            {
                tr.spot = 0;
                switch (kind)
                {
                    case Yard.Grand:
                    {
                        var bay = grandBays ? grandBays.Find(tr.t.name) : null;
                        // The bay markers were saved with the pivot height doubled: keep the truck's own height.
                        tr.home = bay ? new Vector3(bay.position.x + .2f, tr.y, bay.position.z) : tr.sceneHome;
                        tr.rotation = bay ? bay.rotation : tr.sceneRotation;
                        tr.spot = bay ? bay.GetSiblingIndex() : 0;
                        break;
                    }
                    case Yard.Depot:
                        tr.home = PivotFor(tr, new Vector3(DepotRearX, 0, DepotTruckZ), Vector3.right, out tr.rotation);
                        break;
                    case Yard.OldYard:
                        tr.home = tr.sceneHome; tr.rotation = tr.sceneRotation; tr.spot = tr.t.GetSiblingIndex();
                        break;
                    default:
                        tr.home = PivotFor(tr, new Vector3(curbRear == 0 ? CurbStops[0] : curbRear, 0, AvenueCurb), Vector3.left, out tr.rotation);
                        break;
                }
                // A truck already standing in a yard that no longer exists just goes.
                if (changed && tr.state != State.Away) { tr.state = State.Away; tr.t.gameObject.SetActive(false); CheckoutEventTraffic.Unregister(tr.t); }
            }
            if (changed) CheckoutEventTraffic.ClearDeliveryBlock();
            ConfigureWorker(market, next);
            // Dock lights and roller doors that watch a truck follow its new bay.
            foreach (var life in world.GetComponentsInChildren<CheckoutStorageLife>(true))
                foreach (var d in life.doors)
                    if (d != null && d.watch && trucks.TryGetValue(d.watch.name, out var w)) d.watchHome = w.home;
            SuppliersSpot = kind == Yard.Grand ? new Vector3(9, 1, 33.4f)
                : kind == Yard.Depot ? new Vector3(11.5f, 1, 12.5f)
                : kind == Yard.OldYard ? new Vector3(3, 1, 18)
                : new Vector3(CurbStops[0] - 3.5f, 1, -11.6f);
        }

        void ConfigureWorker(CheckoutMarketLayout market, MarketLayout next)
        {
            if (!worker) return;
            Vector3 G(float x, float z) => new Vector3(x, .15f, z);
            switch (Kind)
            {
                case Yard.Grand:
                {
                    var path = world.Find(CheckoutMarketLayout.GrandYard + "/Worker path");
                    if (path && path.childCount >= 2)
                    {
                        var points = new List<Vector3>();
                        for (int i = 0; i < path.childCount; i++) points.Add(path.GetChild(i).position);
                        // Out of the dock door, onto the bay apron, then to the tail of whichever truck it is.
                        points.Add(points[points.Count - 1] + Vector3.right * .8f);
                        worker.approach = Approach;
                        worker.SetDestination(points[0], points.ToArray());
                    }
                    break;
                }
                case Yard.Depot:
                {
                    // Down the depot's stairs into the corridor beside the shop, along it to the yard.
                    var door = market.StorageDoor; var into = market.StorageFacing;
                    var foot = door - into * 1.3f; foot.y = .15f;
                    float lane = Mathf.Min(foot.x, DepotRearX - 1.1f);
                    worker.approach = Approach;
                    worker.SetDestination(door, new[] { door, foot, G(lane, foot.z), G(lane, DepotTruckZ + 1.9f), G(DepotRearX - .8f, DepotTruckZ) });
                    break;
                }
                case Yard.OldYard:
                {
                    worker.approach = null;
                    worker.SetDestination(market.StorageDoor, market.SceneDeliveryRoute);
                    break;
                }
                default:
                {
                    // Out of the front door, down the steps, along the sidewalk to the curb behind the truck.
                    var door = entrance != null ? entrance() : market.Point(new Vector3(-1.75f, .74f, -8.7f));
                    float tail = (curbRear == 0 ? CurbStops[0] : curbRear) + .8f;
                    worker.approach = Approach;
                    worker.SetDestination(door, new[] { door, G(door.x, -9.6f), G(tail, -10.4f), G(tail, -12.2f), G(tail, AvenueCurb) });
                    break;
                }
            }
        }

        // ------------------------------------------------------------------ comings and goings
        /// <summary>Brings the truck in (if its bay is free); true once it stands on its bay.</summary>
        public bool Arrive(Transform t)
        {
            if (!t || !trucks.TryGetValue(t.name, out var tr)) return false;
            if (tr.state == State.Docked) return true;
            if (tr.state != State.Away) return false;
            // One truck per bay: the next one waits round the corner until it has gone.
            foreach (var other in trucks.Values) if (other != tr && other.spot == tr.spot && other.state != State.Away) return false;
            if (Kind == Yard.Curb)
            {
                if (CheckoutEventTraffic.AvenueJammed || !PickCurb(tr)) return false;
                ConfigureWorker(FindAnyObjectByType<CheckoutMarketLayout>(), layout);
            }
            BuildArrival(tr);
            if (tr.path.Count < 2) { Dock(tr); }
            else
            {
                t.position = tr.path[0];
                var first = tr.path[1] - tr.path[0]; first.y = 0;
                t.rotation = Quaternion.LookRotation(tr.back[1] ? -first : first);
                tr.index = 1; tr.speed = 0; tr.state = State.Arriving; tr.since = Time.time;
            }
            t.gameObject.SetActive(true);
            CheckoutEventTraffic.Register(t, tr.box);
            return tr.state == State.Docked;
        }

        /// <summary>The truck is no longer needed: it drives off (or simply stays away).</summary>
        public void Release(Transform t)
        {
            if (!t || !trucks.TryGetValue(t.name, out var tr) || reviewing) return;
            if (tr.state == State.Away) { if (t.gameObject.activeSelf) t.gameObject.SetActive(false); return; }
            if (tr.state == State.Leaving) return;
            if (Kind == Yard.Curb) CheckoutEventTraffic.ClearDeliveryBlock();
            BuildDeparture(tr);
            tr.index = 1; tr.speed = 0; tr.state = State.Leaving; tr.since = Time.time;
        }

        public void ReleaseAll() { foreach (var tr in trucks.Values) Release(tr.t); }

        bool reviewing;
        /// <summary>QA: the trucks stay where the review puts them until EndReview.</summary>
        public void EndReview() { reviewing = false; ReleaseAll(); }
        /// <summary>QA: every truck straight onto its bay (one per bay).</summary>
        public void DockAllForReview()
        {
            reviewing = true;
            var used = new HashSet<int>();
            foreach (var tr in trucks.Values)
            {
                if (Kind == Yard.Curb && !PickCurb(tr)) continue;
                if (!used.Add(tr.spot)) { tr.state = State.Away; tr.t.gameObject.SetActive(false); continue; }
                tr.t.gameObject.SetActive(true); Dock(tr);
            }
        }
        /// <summary>QA: the first truck starts driving in from the street edge.</summary>
        public Transform DriveInForReview()
        {
            reviewing = true;
            foreach (var tr in trucks.Values) { tr.state = State.Away; tr.t.gameObject.SetActive(false); CheckoutEventTraffic.Unregister(tr.t); }
            CheckoutEventTraffic.ClearDeliveryBlock();
            var first = trucks.Values.FirstOrDefault();
            return first != null && Arrive(first.t) ? first.t : first?.t;
        }
        public bool Docked(Transform t) => t && trucks.TryGetValue(t.name, out var tr) && tr.state == State.Docked;
        public string Describe()
        {
            var lines = new List<string> { $"truck yard {Kind}" };
            foreach (var tr in trucks.Values)
            {
                var rear = tr.home + tr.rotation * Vector3.Scale(tr.RearLocal, tr.t.lossyScale);
                lines.Add($"truck {tr.t.name}: home ({tr.home.x:0.00},{tr.home.z:0.00}) yaw {tr.rotation.eulerAngles.y:0} rear ({rear.x:0.00},{rear.z:0.00}) length {tr.Length:0.00} width {tr.box.size.x * Mathf.Abs(tr.t.lossyScale.x):0.00} box {tr.box.min:0.00}..{tr.box.max:0.00} spot {tr.spot} state {tr.state}");
            }
            return string.Join("\n", lines);
        }

        void Dock(Truck tr)
        {
            tr.t.SetPositionAndRotation(tr.home, tr.rotation);
            tr.state = State.Docked; tr.speed = 0;
            if (Kind == Yard.Curb) CheckoutEventTraffic.SetDeliveryBlock(curbRear - tr.Length - .6f, curbRear + .6f);
            CheckoutEventTraffic.Register(tr.t, tr.box);
        }

        // The first curb stop the events leave free.
        bool PickCurb(Truck tr)
        {
            var blocked = CheckoutEventTraffic.EventBlock;
            foreach (var rear in CurbStops)
            {
                float from = rear - tr.Length - 1.2f, to = rear + 1.2f;
                if (blocked.HasValue && blocked.Value.y > from && blocked.Value.x < to) continue;
                bool covered = false;
                for (float x = from; x <= to && !covered; x += 1f) covered = CheckoutEventTraffic.Covered(new Vector3(x, .5f, AvenueCurb), .4f, tr.t);
                if (covered) continue;
                curbRear = rear;
                foreach (var other in trucks.Values) other.home = PivotFor(other, new Vector3(rear, 0, AvenueCurb), Vector3.left, out other.rotation);
                return true;
            }
            return false;
        }

        void Leg(Truck tr, Vector3 p, bool reverse) { tr.path.Add(p); tr.back.Add(reverse); }

        void BuildArrival(Truck tr)
        {
            tr.path.Clear(); tr.back.Clear();
            float north = city.max.z - 2f, east = city.max.x - 1f;
            switch (Kind)
            {
                case Yard.Grand:
                {
                    // Down the east street, past the yard gate, then back in across the sidewalk onto the bay.
                    var heading = tr.rotation * Vector3.forward; heading.y = 0;
                    Leg(tr, R(tr, EastSouth, north), false);
                    Leg(tr, R(tr, EastSouth, 29.2f), false);
                    Leg(tr, R(tr, 18.4f, 33.4f), true);
                    Leg(tr, R(tr, 12f, tr.home.z), true);
                    Leg(tr, tr.home + heading.normalized * 4f, true);
                    Leg(tr, tr.home, true);
                    break;
                }
                case Yard.Depot:
                    // Down the east street, past the driveway, then back in alongside the depot.
                    Leg(tr, R(tr, EastSouth, north), false);
                    Leg(tr, R(tr, EastSouth, 2.4f), false);
                    Leg(tr, R(tr, 19.2f, DepotTruckZ), true);
                    Leg(tr, tr.home, true);
                    break;
                case Yard.OldYard:
                {
                    var forward = tr.rotation * Vector3.forward;
                    Leg(tr, tr.home + forward * 9f, true);
                    Leg(tr, tr.home, true);
                    break;
                }
                default:
                    // Along the avenue's inner westbound lane from the east end of the map, into the curb lane just
                    // before the stop (a car dropping someone off or a bus stays in the curb lane).
                    Leg(tr, R(tr, east, AvenueInner), false);
                    Leg(tr, R(tr, tr.home.x + 10f, AvenueInner), false);
                    Leg(tr, R(tr, tr.home.x + 3.5f, AvenueCurb), false);
                    Leg(tr, tr.home, false);
                    break;
            }
            Round(tr);
        }

        void BuildDeparture(Truck tr)
        {
            var from = tr.t.position; from.y = tr.y;
            tr.path.Clear(); tr.back.Clear();
            Leg(tr, from, false);
            float west = city.min.x + 1f;
            switch (Kind)
            {
                case Yard.Grand:
                    Leg(tr, R(tr, 12f, from.z), false);
                    Leg(tr, R(tr, 18.6f, 33.4f), false);
                    Leg(tr, R(tr, EastSouth, 28.6f), false);
                    break;
                case Yard.Depot:
                    Leg(tr, R(tr, 18.4f, DepotTruckZ), false);
                    Leg(tr, R(tr, EastSouth, 2.6f), false);
                    break;
                case Yard.OldYard:
                    Leg(tr, from + tr.t.forward * 9f, false);
                    Round(tr); return;
                default:
                    // Out into the inner lane and off the map along the avenue (round the roundabout at the west end).
                    Leg(tr, R(tr, from.x - 2.5f, AvenueCurb), false);
                    Leg(tr, R(tr, from.x - 8f, AvenueInner), false);
                    Leg(tr, R(tr, west, AvenueInner), false);
                    Round(tr); return;
            }
            // Down the east street and away west along the avenue's inner lane.
            Leg(tr, R(tr, EastSouth, -12.2f), false);
            Leg(tr, R(tr, 19.8f, AvenueInner), false);
            Leg(tr, R(tr, west, AvenueInner), false);
            Round(tr);
        }

        // Rounds the corners of every forward stretch and bends anything through the roundabout round its island.
        void Round(Truck tr)
        {
            // back[k] tells how the leg that ends on path[k] is driven; legs driven the same way make a run, and a
            // run's ends are where the truck stops (to change gear), so only the corners inside a run are rounded.
            if (tr.path.Count < 2) return;
            var points = new List<Vector3> { tr.path[0] }; var flags = new List<bool> { false };
            int i = 1;
            while (i < tr.path.Count)
            {
                bool reverse = tr.back[i]; int j = i;
                while (j + 1 < tr.path.Count && tr.back[j + 1] == reverse) j++;
                var run = new List<Vector3> { tr.path[i - 1] };
                for (int k = i; k <= j; k++) run.Add(tr.path[k]);
                var array = run.ToArray();
                if (!reverse) array = CheckoutRoundabout.Route(array);
                var smooth = Smooth(array, reverse ? 2.2f : 3.2f);
                for (int k = 1; k < smooth.Count; k++) { points.Add(smooth[k]); flags.Add(reverse); }
                i = j + 1;
            }
            tr.path.Clear(); tr.path.AddRange(points); tr.back.Clear(); tr.back.AddRange(flags);
        }

        static List<Vector3> Smooth(Vector3[] points, float maxRadius)
        {
            var route = new List<Vector3> { points[0] };
            for (int i = 1; i < points.Length - 1; i++)
            {
                float radius = Mathf.Min(maxRadius, Vector3.Distance(points[i - 1], points[i]) * .45f, Vector3.Distance(points[i], points[i + 1]) * .45f);
                var a = points[i] + (points[i - 1] - points[i]).normalized * radius;
                var b = points[i] + (points[i + 1] - points[i]).normalized * radius;
                for (int step = 0; step <= 8; step++) { float t = step / 8f; route.Add((1 - t) * (1 - t) * a + 2 * (1 - t) * t * points[i] + t * t * b); }
            }
            if (points.Length > 1) route.Add(points[points.Length - 1]);
            return route;
        }

        // ------------------------------------------------------------------ driving
        void Update()
        {
            foreach (var tr in trucks.Values)
            {
                if (!tr.t) continue;
                if (tr.state == State.Arriving || tr.state == State.Leaving) Drive(tr);
            }
        }

        // Distance left before the truck has to stop (end of the path or where it changes direction).
        float StopDistance(Truck tr)
        {
            float d = Flat(tr.path[tr.index] - tr.t.position).magnitude;
            bool reverse = tr.back[tr.index];
            for (int i = tr.index + 1; i < tr.path.Count && tr.back[i] == reverse; i++) d += Flat(tr.path[i] - tr.path[i - 1]).magnitude;
            return d;
        }
        static Vector3 Flat(Vector3 v) { v.y = 0; return v; }

        void Drive(Truck tr)
        {
            float dt = Time.deltaTime; if (dt <= 0) return;
            var t = tr.t;
            while (tr.index < tr.path.Count && Flat(tr.path[tr.index] - t.position).magnitude < .06f) tr.index++;
            if (tr.index >= tr.path.Count)
            {
                if (tr.state == State.Arriving) Dock(tr);
                else { tr.state = State.Away; tr.speed = 0; CheckoutEventTraffic.Unregister(t); t.gameObject.SetActive(false); }
                return;
            }
            var delta = Flat(tr.path[tr.index] - t.position);
            float dist = delta.magnitude; var dir = delta / dist;
            bool reverse = tr.back[tr.index];
            var heading = reverse ? -dir : dir;
            bool last = tr.state == State.Arriving && tr.index == tr.path.Count - 1;
            var want = last && dist < 3f ? tr.rotation : Quaternion.LookRotation(heading);
            float turn = Quaternion.Angle(t.rotation, want);
            const float accel = 2f, brake = 2.6f;
            float cruise = reverse ? 1.7f : InYard(t.position) ? 3f : 6f;
            float stop = StopDistance(tr);
            float limit = Mathf.Max(.35f, Mathf.Sqrt(2 * brake * Mathf.Max(0, stop - .05f)));
            float top = Mathf.Min(cruise, limit, Mathf.Lerp(cruise, 1.2f, Mathf.Clamp01(turn / 50f)));
            // Wait for whatever is ahead (or behind, backing up): cars, pedestrians, event vehicles, junctions.
            float scale = Mathf.Abs(t.lossyScale.z);
            var nose = reverse ? t.position + t.rotation * new Vector3(0, 0, tr.box.min.z * scale) : t.position + t.rotation * new Vector3(0, 0, tr.box.max.z * scale);
            float look = 1.4f + tr.speed * tr.speed / (2 * brake);
            bool blocked = CheckoutEventTraffic.CityAhead(nose, dir, look) || CheckoutEventTraffic.Blocks(nose - dir * .3f, dir, look, 1.1f, t);
            if (!reverse && CheckoutTrafficJunctions.Hold(t, dir, blocked, tr.speed * tr.speed / (2 * brake * 1.8f))) top = 0;
            else if (blocked && Time.time - tr.since < 40f) top = 0;   // never stuck for ever
            tr.speed = tr.speed < top ? Mathf.Min(top, tr.speed + accel * dt) : Mathf.Max(top, tr.speed - brake * 1.8f * dt);
            float step = Mathf.Min(tr.speed * dt, dist);
            t.rotation = Quaternion.RotateTowards(t.rotation, want, dt * Mathf.Lerp(40f, 110f, Mathf.Clamp01(tr.speed / 3f)) * (tr.speed > .05f ? 1 : .2f));
            var p = t.position + dir * step; p.y = tr.y; t.position = p;
            if (tr.speed > .3f) tr.since = Time.time;
        }

        static bool InYard(Vector3 p) => Mathf.Abs(p.x) < 21.25f && p.z > -8.5f;
    }
}
