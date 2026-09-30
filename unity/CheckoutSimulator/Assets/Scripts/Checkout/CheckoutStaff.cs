using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout
{
    // The hired stock clerks and cleaners, played from the app's task timeline (src/services/staff-work.ts).
    // Every job has a start and an end; the effect lands in the app at the end, and here the walk in between is
    // laid out so that it finishes on time:
    //  restock  - through the rear roller door, down the service ramp and along the staff walkway to the storage
    //             (parcels on a pallet by the ramp, the depot or the central warehouse dock), pick one box of the
    //             right kind (cardboard, produce crate, fish box...), carry it back to the shelf or counter, put it
    //             down and fill the slot.
    //  incident - a cleaner pushes the cart to the mess and mops it (or climbs the ladder and swaps the bulb);
    //             a clerk re-tags the prices.
    // Idle staff wait just inside the rear door. The door rolls up whenever someone walks through it.
    public class CheckoutStaff : MonoBehaviour
    {
        const float Floor = .74f, Yard = .15f;

        class Step
        {
            public float t0, t1;
            public List<Vector3> path; public float[] cum; public float length;
            public string clip; public Vector3 face;
            public bool walk, carry, push, ladder, cutter, mop, bulb, floorBox, pickup, putDown;
            public Vector3 cartAt; public Quaternion cartRot; public bool cartParked;
            public Vector3 ladderAt; public Quaternion ladderRot;
        }

        class Plan
        {
            public string id; public double startedAt; public string box = "caixa";
            public readonly List<Step> steps = new List<Step>();
            public Vector3 End => steps.Count == 0 ? Vector3.zero : Last(steps[steps.Count - 1]);
        }

        class Actor
        {
            public string id, role, clip; public Transform root, rig; public Animation anim; public float phase, pushWeight, lift;
            public readonly Dictionary<string, GameObject> boxes = new Dictionary<string, GameObject>();
            public readonly Dictionary<string, Quaternion> boxRest = new Dictionary<string, Quaternion>();
            public GameObject cutter, mop, bulb; public Transform cart, ladder, floorBox;
            public Plan plan; public bool idle; public int slot; public Vector3 lastPosition; public Transform visual;
        }

        Transform world, kit, holder, door, curtain, walkway, pallet;
        CheckoutMap map;
        CheckoutMarketShell shell;
        CheckoutMarketLayout layout;
        MarketDeliveryWorker delivery;
        Snapshot state;
        readonly Dictionary<string, Actor> actors = new Dictionary<string, Actor>();
        readonly List<Vector3> yardRoute = new List<Vector3>(), walkPoints = new List<Vector3>(), stairs = new List<Vector3>();
        // Staff entrance of the central warehouse (left of the forklift ramp) and its swinging door leaf.
        const float EntranceX = -8.2f;
        Transform entrance, leafHinge; float leafOpen;
        Vector3 storageSpot, storageFace;
        string routeKey;
        MarketDay.MarketDeliveryWorker[] couriers; float nextCourierScan;
        float doorOpen, curtainHeight; Vector3 curtainPosition, curtainScale; int curtainAxis = 1;

        public void Initialize(Transform root, CheckoutMap owner)
        {
            world = root; map = owner;
            kit = world.Find("Staff Kit");
            shell = world.GetComponentInChildren<CheckoutMarketShell>(true);
            layout = GetComponent<CheckoutMarketLayout>();
            delivery = world.GetComponentInChildren<MarketDeliveryWorker>(true);
            holder = new GameObject("Market Staff").transform;
            if (!kit) { Debug.LogWarning("CHECKOUT_STAFF no Staff Kit in the scene (Supermarket/Build staff kit)."); return; }
            kit.gameObject.SetActive(false);
            door = Clone("staff-door", holder);
            if (door)
            {
                door.name = "Rear roller door";
                curtain = door.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith("Anim Curtain"));
                if (curtain)
                {
                    // The curtain rolls up into the coil: shrink it along whichever local axis is world up.
                    float ux = Mathf.Abs(curtain.right.y), uy = Mathf.Abs(curtain.up.y), uz = Mathf.Abs(curtain.forward.y);
                    curtainAxis = ux > uy && ux > uz ? 0 : uy > uz ? 1 : 2;
                    curtainScale = curtain.localScale; curtainPosition = curtain.localPosition;
                    var r = curtain.GetComponentInChildren<Renderer>(); curtainHeight = r ? r.bounds.size.y : 2.2f;
                }
            }
            pallet = Clone("staff-pallet", holder); if (pallet) { pallet.name = "Rear doorstep pallet"; pallet.gameObject.SetActive(false); }
            entrance = Clone("staff-warehouse-door", holder);
            if (entrance)
            {
                entrance.name = "Warehouse staff entrance"; entrance.gameObject.SetActive(false);
                var leaf = entrance.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name.StartsWith("Anim Leaf"));
                var r = leaf ? leaf.GetComponentInChildren<Renderer>() : null;
                if (r)
                {
                    // Hinge on the leaf's west edge: the door swings out over the landing.
                    leafHinge = new GameObject("Leaf hinge").transform;
                    leafHinge.SetParent(leaf.parent, false);
                    leafHinge.position = new Vector3(r.bounds.min.x, r.bounds.center.y, r.bounds.center.z);
                    leafHinge.rotation = entrance.rotation;
                    leaf.SetParent(leafHinge, true);
                }
            }
            if (shell) { var light = shell.Walls.Find("Rear light"); if (light) light.gameObject.SetActive(false); }
        }

        Transform Clone(string template, Transform parent)
        {
            var t = kit ? kit.Find(template) : null;
            if (!t) return null;
            var go = Instantiate(t.gameObject, parent, false);
            go.name = template; go.SetActive(true);
            go.transform.localPosition = Vector3.zero; go.transform.localRotation = Quaternion.identity;
            return go.transform;
        }

        // ------------------------------------------------------------------ geometry of the service route
        bool Ready => kit && shell && door;
        float DoorX => shell.RearDoor.x;
        Vector3 DoorInside => new Vector3(DoorX, Floor, shell.RearWall - .95f);
        Vector3 DoorSill => new Vector3(DoorX, Floor, shell.RearWall);
        Vector3 RampTop => shell.RampTop;
        Vector3 RampFoot => new Vector3(DoorX, Yard, shell.RampEnd.z);
        Vector3 YardStart => new Vector3(DoorX, Yard, shell.RampEnd.z + .6f);
        bool Outside(Vector3 p) => shell && p.z > shell.RearWall - .05f;

        // Rebuilt when the shop grows or a storage is bought: the pallet, the storage spot and the walkway.
        void UpdateRoute()
        {
            var s = layout.State;
            string key = s.stage + ":" + s.widthScale + ":" + s.depthScale + ":" + s.storage + ":" + s.storageLarge + ":" + shell.RearWall;
            // Door and ramp first, they follow the wall.
            door.SetPositionAndRotation(shell.RearDoor, Quaternion.Euler(0, 180, 0));
            if (key == routeKey) return;
            routeKey = key;
            if (pallet) pallet.gameObject.SetActive(false);
            if (entrance) entrance.gameObject.SetActive(false);
            stairs.Clear();
            Vector3 approach; // where the walkway ends, heading north into the storage door
            if (s.storageLarge && entrance && GrandFacade(out var facade, out float floorY))
            {
                // Staff entrance on the central warehouse's south front, left of the forklift ramp: stairs up to a
                // landing and a steel door; the clerk steps in, picks a box inside and comes back out with it.
                var at = new Vector3(EntranceX, facade.y, facade.z);
                entrance.SetPositionAndRotation(at, Quaternion.identity); entrance.gameObject.SetActive(true);
                var foot = new Vector3(EntranceX, Yard, facade.z - 2.75f);
                stairs.Add(new Vector3(EntranceX, Yard, facade.z - 2.63f));
                stairs.Add(new Vector3(EntranceX, floorY, facade.z - .97f));
                stairs.Add(new Vector3(EntranceX, floorY, facade.z - .45f));
                stairs.Add(new Vector3(EntranceX, floorY, facade.z - .1f));
                storageSpot = stairs[stairs.Count - 1]; storageFace = storageSpot + Vector3.forward;
                approach = foot;
            }
            else if (s.storage)
            {
                var d = delivery && delivery.storageDoor ? delivery.storageDoor.position : new Vector3(-1.65f, Yard, 16.72f);
                storageFace = new Vector3(d.x, Yard, d.z + 1); storageSpot = new Vector3(d.x, Yard, d.z - .5f);
                approach = storageSpot;
            }
            else if (pallet)
            {
                // Before there is a storage the supplier leaves a pallet of boxes by the foot of the ramp.
                var p = RampFoot + new Vector3(1.75f, 0, 1.1f);
                pallet.SetPositionAndRotation(p, Quaternion.Euler(0, 90, 0)); pallet.gameObject.SetActive(true);
                storageFace = p; storageSpot = p + new Vector3(-1.05f, 0, 0);
                approach = storageSpot;
            }
            else { storageSpot = YardStart + new Vector3(0, 0, 1); storageFace = storageSpot + Vector3.forward; approach = storageSpot; }
            walkPoints.Clear(); walkPoints.AddRange(CurvedRoute(RampFoot, approach));
            yardRoute.Clear(); yardRoute.AddRange(walkPoints.Skip(1)); yardRoute.AddRange(stairs);
            BuildWalkway();
        }

        // The central warehouse's south front (x, yard level, z) and its raised floor.
        bool GrandFacade(out Vector3 facade, out float floorY)
        {
            facade = Vector3.zero; floorY = Yard + 1f;
            var model = world.Find(CheckoutMarketLayout.GrandWarehouse + "/Warehouse model");
            var rs = model ? model.GetComponentsInChildren<Renderer>(true) : new Renderer[0];
            if (rs.Length == 0) return false;
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            facade = new Vector3(b.center.x, b.min.y, b.min.z);
            var forklift = world.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "Forklift door");
            floorY = forklift ? forklift.position.y : b.min.y + 1f;
            return true;
        }

        // A walkway that leaves the ramp heading straight out and arrives square to the storage door, sweeping between
        // the two in one smooth curve; around anything standing in the way it follows the block's route, smoothed.
        List<Vector3> CurvedRoute(Vector3 from, Vector3 to)
        {
            CheckoutBlockPaths.Invalidate();
            float span = Vector3.Distance(Flat(from, 0), Flat(to, 0));
            var p0 = Flat(from, Yard); var p3 = Flat(to, Yard);
            // Try gentler and tighter sweeps before giving up on a single curve.
            foreach (float k in new[] { .45f, .35f, .55f, .25f, .65f })
            {
                var p1 = p0 + Vector3.forward * Mathf.Max(1.2f, span * k);
                var p2 = p3 - Vector3.forward * Mathf.Max(1.2f, span * k);
                var curve = new List<Vector3>();
                int n = Mathf.Max(8, Mathf.CeilToInt(span / .3f));
                for (int i = 0; i <= n; i++)
                {
                    float t = i / (float)n, u = 1 - t;
                    curve.Add(u * u * u * p0 + 3 * u * u * t * p1 + 3 * u * t * t * p2 + t * t * t * p3);
                }
                if (Clear(curve)) return curve;
            }
            // Obstacles: grid route between the straight lead-in and lead-out, corners rounded off.
            var lead = p0 + Vector3.forward * 1.2f; var tail = p3 - Vector3.forward * 1.2f;
            var route = new List<Vector3> { p0, lead };
            foreach (var q in CheckoutBlockPaths.Route(lead, tail)) route.Add(Flat(q, Yard));
            route.Add(p3);
            for (int k = 4; k >= 0; k--)
            {
                var smooth = Chaikin(route, k);
                if (k == 0 || Clear(smooth)) return Resample(smooth, .3f);
            }
            return route;
        }

        // Free of buildings and street furniture. The last stretch into the storage door is left out: the block grid
        // counts everything around a building (ramp, rack, forklift yard) as the building itself; likewise the foot of the
        // shop's own service ramp.
        static bool Clear(List<Vector3> path)
        {
            var start = path[0]; var end = path[path.Count - 1];
            for (int i = 2; i < path.Count - 2; i++)
                if (Horizontal(path[i] - end) > 3.2f && Horizontal(path[i] - start) > 1.6f && !CheckoutBlockPaths.Free(path[i])) return false;
            return true;
        }

        static List<Vector3> Chaikin(List<Vector3> path, int iterations)
        {
            var p = new List<Vector3>(path);
            for (int it = 0; it < iterations; it++)
            {
                var q = new List<Vector3> { p[0] };
                for (int i = 0; i + 1 < p.Count; i++)
                {
                    q.Add(Vector3.Lerp(p[i], p[i + 1], .25f));
                    q.Add(Vector3.Lerp(p[i], p[i + 1], .75f));
                }
                q.Add(p[p.Count - 1]); p = q;
            }
            return p;
        }

        static List<Vector3> Resample(List<Vector3> path, float step)
        {
            var o = new List<Vector3> { path[0] }; float carry = 0;
            for (int i = 0; i + 1 < path.Count; i++)
            {
                var a = path[i]; var b = path[i + 1]; float d = Vector3.Distance(a, b), t = step - carry;
                while (t <= d) { o.Add(Vector3.Lerp(a, b, t / d)); t += step; }
                carry = d - (t - step);
            }
            if ((o[o.Count - 1] - path[path.Count - 1]).sqrMagnitude > .0001f) o.Add(path[path.Count - 1]);
            return o;
        }

        // Staff walkway: a continuous band of grey pavers with yellow edge lines following the curve (world-planar UVs).
        void BuildWalkway()
        {
            if (walkway) Destroy(walkway.gameObject);
            var template = kit.Find("staff-path");
            var mats = template ? template.GetComponentsInChildren<Renderer>(true).SelectMany(r => r.sharedMaterials).Where(m => m).Distinct().ToArray() : new Material[0];
            var paver = mats.FirstOrDefault(m => m.name.Contains("Paver")) ?? mats.FirstOrDefault();
            var line = mats.FirstOrDefault(m => m.name.Contains("F2C23F")) ?? paver;
            if (!paver || walkPoints.Count < 2) return;
            walkway = new GameObject("Staff walkway").transform; walkway.SetParent(holder, false);
            Band(walkway, "Pavers", walkPoints, -.5f, .5f, Yard + .012f, paver);
            Band(walkway, "Edge line L", walkPoints, -.5f, -.41f, Yard + .016f, line);
            Band(walkway, "Edge line R", walkPoints, .41f, .5f, Yard + .016f, line);
        }

        static void Band(Transform parent, string name, List<Vector3> pts, float from, float to, float y, Material material)
        {
            var verts = new List<Vector3>(); var tris = new List<int>();
            for (int i = 0; i < pts.Count; i++)
            {
                var prev = pts[Mathf.Max(0, i - 1)]; var next = pts[Mathf.Min(pts.Count - 1, i + 1)];
                var dir = next - prev; dir.y = 0; if (dir.sqrMagnitude < 1e-6f) dir = Vector3.forward; dir.Normalize();
                var side = new Vector3(dir.z, 0, -dir.x);
                var c = new Vector3(pts[i].x, y, pts[i].z);
                verts.Add(c + side * from); verts.Add(c + side * to);
                if (i > 0) { int k = verts.Count - 4; tris.AddRange(new[] { k, k + 2, k + 1, k + 1, k + 2, k + 3 }); }
            }
            var mesh = new Mesh { name = name };
            mesh.SetVertices(verts); mesh.SetUVs(0, verts.Select(v => new Vector2(v.x, v.z)).ToList()); mesh.SetTriangles(tris, 0);
            mesh.RecalculateNormals();
            // Faces up whatever the winding came out as.
            if (mesh.normals.Length > 0 && mesh.normals[0].y < 0) { tris.Reverse(); mesh.SetTriangles(tris, 0); mesh.RecalculateNormals(); }
            mesh.RecalculateBounds();
            var go = new GameObject(name); go.transform.SetParent(parent, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.AddComponent<MeshRenderer>(); r.sharedMaterial = material; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
        }

        // Inside the shop along the navigation mesh (around the furniture); straight when there is none.
        NavMeshPath navPath;
        List<Vector3> Indoors(Vector3 a, Vector3 b)
        {
            var list = new List<Vector3> { a };
            if (navPath == null) navPath = new NavMeshPath();
            if (NavMesh.SamplePosition(a, out var ha, 1.2f, NavMesh.AllAreas) && NavMesh.SamplePosition(b, out var hb, 1.2f, NavMesh.AllAreas)
                && NavMesh.CalculatePath(ha.position, hb.position, NavMesh.AllAreas, navPath) && navPath.status == NavMeshPathStatus.PathComplete)
                foreach (var c in navPath.corners.Skip(1).Take(Mathf.Max(0, navPath.corners.Length - 2))) list.Add(new Vector3(c.x, Floor, c.z));
            list.Add(b);
            return list;
        }

        // Any two points of the job: inside, through the rear door and down the ramp, along the walkway.
        List<Vector3> Way(Vector3 from, Vector3 to)
        {
            bool fo = Outside(from), too = Outside(to);
            if (!fo && !too) return Indoors(from, to);
            var outward = new List<Vector3>();
            if (!fo) { outward.AddRange(Indoors(from, DoorInside)); outward.Add(DoorSill); outward.Add(RampTop); outward.Add(RampFoot); }
            else outward.Add(from);
            if (too)
            {
                if (fo) { outward.Add(to); return outward; }
                outward.AddRange(yardRoute); if ((yardRoute.Last() - to).sqrMagnitude > .01f) outward.Add(to);
                return outward;
            }
            // From the yard back in.
            var back = new List<Vector3>(yardRoute); back.Reverse();
            outward.AddRange(back); outward.Add(RampFoot); outward.Add(RampTop); outward.Add(DoorSill);
            outward.AddRange(Indoors(DoorInside, to));
            return outward;
        }

        static Step Walk(List<Vector3> path, string clip)
        {
            var clean = new List<Vector3>();
            foreach (var p in path) if (clean.Count == 0 || (clean[clean.Count - 1] - p).sqrMagnitude > .0004f) clean.Add(p);
            if (clean.Count == 1) clean.Add(clean[0]);
            var s = new Step { walk = true, clip = clip, path = clean, cum = new float[clean.Count] };
            for (int i = 1; i < clean.Count; i++) s.cum[i] = s.cum[i - 1] + Vector3.Distance(clean[i - 1], clean[i]);
            s.length = s.cum[clean.Count - 1];
            return s;
        }

        static Step Act(Vector3 at, Vector3 face, string clip) => new Step { path = new List<Vector3> { at }, cum = new[] { 0f }, face = face, clip = clip };
        static Vector3 Last(Step s) => s.path[s.path.Count - 1];

        Vector3 Flat(Vector3 p, float y) => new Vector3(p.x, y, p.z);
        Vector3 Home(Actor a)
        {
            // Just inside the rear door, off the way in: clerks on the west side, cleaners (with the cart) east.
            float side = a.role == "cleaner" ? 1 : -1;
            return DoorInside + new Vector3(side * (.65f + .15f * (a.slot / 2)), 0, -.35f - .85f * (a.slot % 2));
        }

        float ClipLength(Actor a, string clip, float fallback) => a.anim && a.anim[clip] ? a.anim[clip].length : fallback;

        // ------------------------------------------------------------------ planning
        Plan PlanRestock(Actor a, StaffTask task)
        {
            var plan = new Plan { id = task.id, startedAt = task.startedAt, box = string.IsNullOrEmpty(task.box) ? "caixa" : task.box };
            var from = a.root.position;
            var target = Flat(map.Approach(task.shelfId), Floor); var fixture = Flat(map.Fixture(task.shelfId), Floor);
            var go = Walk(Way(from, storageSpot), "Walking");
            var back = Walk(Way(storageSpot, target), "CarryWalking"); back.carry = true;
            var pick = Act(storageSpot, storageFace, "Pickup"); pick.pickup = true;
            var put = Act(target, fixture, "PutDown"); put.putDown = true; put.carry = true;
            var fill = Act(target, fixture, "Restock"); fill.floorBox = true; fill.cutter = true;
            float duration = (float)((task.endsAt - task.startedAt) / 1000.0);
            float pickT = ClipLength(a, "Pickup", 2), putT = ClipLength(a, "PutDown", 2.25f);
            float walking = go.length + back.length, available = duration - pickT - putT - 2.5f;
            float speed = Mathf.Clamp(walking / Mathf.Max(.1f, available), 1.0f, 2.3f);
            float t = 0;
            t = Place(go, t, go.length / speed); t = Place(pick, t, pickT); t = Place(back, t, back.length / speed); t = Place(put, t, putT);
            Place(fill, t, Mathf.Max(1.2f, duration - t));
            plan.steps.AddRange(new[] { go, pick, back, put, fill });
            return plan;
        }

        Plan PlanIncident(Actor a, StaffTask task)
        {
            var plan = new Plan { id = task.id, startedAt = task.startedAt };
            var spot = Flat(map.Approach(task.shelfId), Floor); var fixture = Flat(map.Fixture(task.shelfId), Floor);
            var toFixture = fixture - spot; toFixture.y = 0; if (toFixture.sqrMagnitude < .01f) toFixture = Vector3.forward; toFixture.Normalize();
            var side = Vector3.Cross(Vector3.up, toFixture);
            float duration = (float)((task.endsAt - task.startedAt) / 1000.0);
            bool cleaner = a.role == "cleaner";
            Vector3 stand, face; Step work;
            if (task.incidentKind == "lampada")
            {
                // Under the flickering lamp, on the step ladder.
                stand = spot + toFixture * .45f; face = stand + toFixture;
                work = Act(stand, face, "ReachUp"); work.ladder = true; work.bulb = true;
                work.ladderAt = stand; work.ladderRot = Quaternion.LookRotation(toFixture);
            }
            else if (task.incidentKind == "etiqueta") { stand = spot; face = fixture; work = Act(stand, face, "Restock"); work.cutter = true; }
            else { stand = spot + side * .75f; face = spot; work = Act(stand, face, "Mop"); work.mop = true; }
            if (cleaner)
            {
                // The cart stays beside the job, out of the way of the mess, on the side away from the camera (south)
                // so it never hides the cleaner.
                var away = side.z >= 0 ? side : -side;
                if (task.incidentKind != "lampada" && task.incidentKind != "etiqueta") { stand = spot + away * .75f; work.path[0] = stand; work.face = spot; }
                work.cartParked = true; work.cartAt = stand + away * .9f; work.cartRot = Quaternion.LookRotation(-toFixture);
            }
            var go = Walk(Way(a.root.position, stand), cleaner ? "PushWalking" : "Walking"); go.push = cleaner;
            float speed = Mathf.Clamp(go.length / Mathf.Max(.1f, duration - 3f), .9f, 2.2f);
            float t = Place(go, 0, go.length / speed);
            Place(work, t, Mathf.Max(1f, duration - t));
            plan.steps.Add(go); plan.steps.Add(work);
            return plan;
        }

        Plan PlanIdle(Actor a)
        {
            var plan = new Plan { id = "idle", startedAt = CheckoutBridge.Now };
            var home = Home(a); var face = home + Vector3.back * 2 + new Vector3(-(home.x - DoorX), 0, 0);
            bool cleaner = a.role == "cleaner";
            var go = Walk(Way(a.root.position, home), cleaner ? "PushWalking" : "Walking"); go.push = cleaner;
            var wait = Act(home, face, "Idle");
            if (cleaner) { wait.cartParked = true; wait.cartAt = home + new Vector3(.8f, 0, 0); wait.cartRot = Quaternion.Euler(0, 180, 0); }
            float t = Place(go, 0, go.length / 1.15f);
            Place(wait, t, 1e7f);
            plan.steps.Add(go); plan.steps.Add(wait);
            return plan;
        }

        static float Place(Step s, float t, float duration) { s.t0 = t; s.t1 = t + Mathf.Max(.01f, duration); return s.t1; }

        // ------------------------------------------------------------------ snapshot
        public void Apply(Snapshot next)
        {
            state = next;
            if (!Ready) return;
            UpdateRoute();
            var staff = (next.employees ?? new Employee[0]).Where(e => e.role == "stock_clerk" || e.role == "cleaner").ToList();
            foreach (var id in actors.Keys.Where(k => staff.All(e => e.id != k)).ToList())
            { if (actors[id].root) Destroy(actors[id].root.gameObject); Clean(actors[id]); actors.Remove(id); }
            int clerks = 0, cleaners = 0;
            foreach (var e in staff.OrderBy(e => e.id))
            {
                if (!actors.TryGetValue(e.id, out var a)) { a = Spawn(e); if (a == null) continue; actors[e.id] = a; }
                a.slot = e.role == "cleaner" ? cleaners++ : clerks++;
                bool on = e.isWorking && next.isOpen;
                if (a.root.gameObject.activeSelf != on)
                {
                    a.root.gameObject.SetActive(on); if (a.cart) a.cart.gameObject.SetActive(on);
                    if (on) { a.root.position = Home(a); a.plan = null; }
                    else { if (a.ladder) a.ladder.gameObject.SetActive(false); if (a.floorBox) a.floorBox.gameObject.SetActive(false); }
                }
                if (!on) continue;
                var task = next.staffTasks?.FirstOrDefault(t => t.employeeId == e.id);
                if (task != null)
                {
                    if (a.plan == null || a.plan.id != task.id)
                    {
                        a.plan = task.kind == "restock" ? PlanRestock(a, task) : PlanIncident(a, task);
                        a.idle = false; if (a.floorBox) a.floorBox.gameObject.SetActive(false);
                    }
                }
                else if (a.plan == null || !a.idle || FinishedWalk(a)) { a.plan = PlanIdle(a); a.idle = true; }
            }
        }

        // An idle plan made before the furniture or the door moved: walk to the new home.
        bool FinishedWalk(Actor a) => a.idle && a.plan != null && (Last(a.plan.steps[a.plan.steps.Count - 1]) - Home(a)).sqrMagnitude > .01f;

        Actor Spawn(Employee e)
        {
            var root = Clone(e.role == "cleaner" ? "Staff Cleaner" : "Staff Clerk", holder);
            if (!root) return null;
            root.name = "Staff_" + e.id;
            var a = new Actor { id = e.id, role = e.role, root = root };
            a.anim = root.GetComponentInChildren<Animation>(true);
            a.visual = root.Find("Visual");
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                if (t.name.StartsWith("Box_")) { a.boxes[t.name.Substring(4)] = t.gameObject; a.boxRest[t.name.Substring(4)] = Quaternion.Inverse(root.rotation) * t.rotation; t.gameObject.SetActive(false); }
                else if (t.name == "Cutter") { a.cutter = t.gameObject; t.gameObject.SetActive(false); }
                else if (t.name == "Mop") { a.mop = t.gameObject; t.gameObject.SetActive(false); }
                else if (t.name == "Bulb") { a.bulb = t.gameObject; t.gameObject.SetActive(false); }
            }
            if (e.role == "cleaner")
            {
                a.cart = Clone("staff-cart", holder); if (a.cart) a.cart.name = "Cleaning cart " + e.id;
                a.ladder = Clone("staff-ladder", holder); if (a.ladder) { a.ladder.name = "Step ladder " + e.id; a.ladder.gameObject.SetActive(false); }
            }
            // Clicking an employee opens the team panel.
            var box = root.gameObject.AddComponent<BoxCollider>(); box.center = new Vector3(0, 1.05f, 0); box.size = new Vector3(.8f, 2.1f, .8f);
            root.gameObject.AddComponent<CheckoutTarget>().panel = "team";
            root.position = DoorInside; a.lastPosition = root.position;
            return a;
        }

        void Clean(Actor a)
        {
            if (a.cart) Destroy(a.cart.gameObject);
            if (a.ladder) Destroy(a.ladder.gameObject);
            if (a.floorBox) Destroy(a.floorBox.gameObject);
        }

        void OnDestroy() { if (holder) Destroy(holder.gameObject); }

        // ------------------------------------------------------------------ playback
        void Update()
        {
            if (!Ready || state == null) return;
            double now = CheckoutBridge.Now;
            bool nearDoor = false;
            foreach (var a in actors.Values)
            {
                if (!a.root.gameObject.activeSelf || a.plan == null || a.plan.steps.Count == 0) continue;
                float t = (float)((now - a.plan.startedAt) / 1000.0);
                var step = a.plan.steps.FirstOrDefault(s => t < s.t1) ?? a.plan.steps[a.plan.steps.Count - 1];
                float local = Mathf.Clamp(t - step.t0, 0, step.t1 - step.t0);
                Play(a, step, local);
                var flat = a.root.position - shell.RearDoor; flat.y = 0;
                if (flat.magnitude < 2.3f && step.walk) nearDoor = true;
            }
            // The delivery driver carries the boxes in through the same rear roller door: it rolls up for him too.
            if (!nearDoor && shell)
            {
                if (Time.time > nextCourierScan) { nextCourierScan = Time.time + 2; couriers = FindObjectsByType<MarketDay.MarketDeliveryWorker>(FindObjectsSortMode.None); }
                if (couriers != null)
                    foreach (var courier in couriers)
                    {
                        if (!courier) continue;
                        courier.gateAt = shell.RearDoor; courier.gateOpen ??= () => doorOpen;
                        if (!courier.isActiveAndEnabled || courier.Phase == MarketDay.MarketDeliveryWorker.DeliveryPhase.Waiting) continue;
                        if (Horizontal(courier.transform.position - shell.RearDoor) < 2.6f) { nearDoor = true; break; }
                    }
            }
            doorOpen = Mathf.MoveTowards(doorOpen, nearDoor ? 1 : 0, Time.deltaTime * (nearDoor ? 1.4f : .7f));
            if (leafHinge && entrance.gameObject.activeSelf)
            {
                bool atEntrance = actors.Values.Any(a => a.root.gameObject.activeSelf && Horizontal(a.root.position - storageSpot) < 1.3f);
                leafOpen = Mathf.MoveTowards(leafOpen, atEntrance ? 1 : 0, Time.deltaTime * (atEntrance ? 1.6f : .9f));
                leafHinge.rotation = entrance.rotation * Quaternion.Euler(0, 95 * Mathf.SmoothStep(0, 1, leafOpen), 0);
            }
            if (curtain)
            {
                float k = 1 - .9f * Mathf.SmoothStep(0, 1, doorOpen);
                var scale = curtainScale; scale[curtainAxis] *= k; curtain.localScale = scale;
                curtain.localPosition = curtainPosition; curtain.position += Vector3.up * curtainHeight * (1 - k) * .5f;
            }
        }

        static float Horizontal(Vector3 v) { v.y = 0; return v.magnitude; }

        void Play(Actor a, Step step, float local)
        {
            Vector3 position; Vector3 heading;
            if (step.walk)
            {
                float d = step.length * (local / Mathf.Max(.01f, step.t1 - step.t0));
                int i = 1; while (i < step.path.Count - 1 && step.cum[i] < d) i++;
                var p0 = step.path[i - 1]; var p1 = step.path[i]; float seg = Mathf.Max(.0001f, step.cum[i] - step.cum[i - 1]);
                position = Vector3.Lerp(p0, p1, Mathf.Clamp01((d - step.cum[i - 1]) / seg));
                heading = p1 - p0; heading.y = 0;
                if (step.length < .01f || d >= step.length - .001f) heading = Vector3.zero;
            }
            else { position = step.path[0]; heading = step.face - position; heading.y = 0; }

            // Standing on the ladder lifts the cleaner onto its second step.
            float lift = step.ladder ? Mathf.SmoothStep(0, .6f, local / .5f) : 0;
            a.root.position = position + Vector3.up * lift;
            if (heading.sqrMagnitude > .0004f)
            {
                var want = Quaternion.LookRotation(-heading.normalized);
                a.root.rotation = step.walk ? Quaternion.RotateTowards(a.root.rotation, want, Time.deltaTime * 520) : Quaternion.RotateTowards(a.root.rotation, want, Time.deltaTime * 300);
            }

            // Clip: walks follow the distance covered, actions their own time.
            string clip = step.clip;
            if (step.walk && step.length > .01f && local >= step.t1 - step.t0 - .001f) clip = step.carry ? "CarryIdle" : step.push ? "PushIdle" : "Idle";
            if (a.anim && a.anim[clip])
            {
                if (a.clip != clip) { a.anim.CrossFade(clip, .2f); a.clip = clip; }
                var st = a.anim[clip]; st.speed = 0;
                if (step.walk && clip == step.clip)
                {
                    var moved = a.root.position - a.lastPosition; moved.y = 0;
                    float cycle = clip == "Walking" ? 1.33f : clip == "CarryWalking" ? 1.36f : 1.2f; // delivery-worker clips at the staff scale
                    if (moved.magnitude < 2) a.phase = Mathf.Repeat(a.phase + moved.magnitude / cycle, 1);
                    st.normalizedTime = a.phase;
                }
                else
                {
                    bool once = clip == "Pickup" || clip == "PutDown";
                    st.time = once ? Mathf.Min(local, st.length - .01f) : Mathf.Repeat(local, st.length);
                }
            }
            a.lastPosition = a.root.position;

            // Props: the box of the job, the cutter while filling, the mop, the bulb, the ladder and the cart.
            float f = local / Mathf.Max(.01f, step.t1 - step.t0);
            // At the warehouse's staff door the clerk steps inside to pick the box and comes back out with it.
            bool inside = step.pickup && entrance && entrance.gameObject.activeSelf && Horizontal(step.path[0] - storageSpot) < .05f && f > .12f && f < .82f;
            if (a.visual && a.visual.gameObject.activeSelf == inside) a.visual.gameObject.SetActive(!inside);
            bool carrying = step.carry && !(step.putDown && f > .55f) || step.pickup && f > .45f;
            foreach (var pair in a.boxes) pair.Value.SetActive(carrying && pair.Key == (a.plan?.box ?? "caixa"));
            if (step.putDown && f > .55f || step.floorBox) ShowFloorBox(a, step);
            else if (a.floorBox && a.floorBox.gameObject.activeSelf) a.floorBox.gameObject.SetActive(false);
            if (a.cutter) a.cutter.SetActive(step.cutter);
            if (a.mop) a.mop.SetActive(step.mop);
            if (a.bulb) a.bulb.SetActive(step.bulb);
            if (a.ladder)
            {
                a.ladder.gameObject.SetActive(step.ladder);
                if (step.ladder) a.ladder.SetPositionAndRotation(step.ladderAt + step.ladderRot * new Vector3(0, 0, .1f), step.ladderRot);
            }
            if (a.cart)
            {
                a.pushWeight = Mathf.MoveTowards(a.pushWeight, step.push && step.walk ? 1 : 0, Time.deltaTime * 2.5f);
                var ahead = a.root.position - a.root.forward * .78f; ahead.y = position.y;
                var parkedAt = step.cartParked ? step.cartAt : a.root.position + a.root.right * .8f;
                var parkedRot = step.cartParked ? step.cartRot : a.root.rotation;
                a.cart.position = Vector3.Lerp(parkedAt, ahead, a.pushWeight);
                a.cart.rotation = Quaternion.Slerp(parkedRot, a.root.rotation * Quaternion.Euler(0, 180, 0), a.pushWeight);
                if (!step.cartParked && a.pushWeight <= 0) a.cart.rotation = a.root.rotation * Quaternion.Euler(0, 180, 0);
            }
        }

        // The box set down on the floor beside the shelf while the clerk fills it.
        void ShowFloorBox(Actor a, Step step)
        {
            string kind = a.plan?.box ?? "caixa";
            if (!a.boxes.TryGetValue(kind, out var source)) return;
            if (!a.floorBox || a.floorBox.name != "Floor box " + kind)
            {
                if (a.floorBox) Destroy(a.floorBox.gameObject);
                bool was = source.activeSelf; source.SetActive(true);
                var copy = Instantiate(source, holder, true); source.SetActive(was);
                copy.name = "Floor box " + kind; a.floorBox = copy.transform;
            }
            if (a.floorBox.gameObject.activeSelf) return;
            a.floorBox.gameObject.SetActive(true);
            // Upright, on the floor, half a metre in front of the clerk and a little to the side.
            // Upright as in the bind pose (the carried box leans with the torso), turned like the clerk.
            a.floorBox.rotation = a.root.rotation * (a.boxRest.TryGetValue(kind, out var rest) ? rest : Quaternion.identity);
            var r = a.floorBox.GetComponentInChildren<Renderer>(); if (!r) return;
            var b = r.bounds;
            var spot = step.path[0] - a.root.forward * .1f + a.root.right * .55f;
            a.floorBox.position += new Vector3(spot.x - b.center.x, Floor + .005f - b.min.y, spot.z - b.center.z);
        }
    }
}
