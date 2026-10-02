using System;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout
{
    // Construction machines, site props and hand tools made in Blender (ArtSource/works_kit.py, works_kit2.py):
    // Resources/CheckoutWorks/Works_<Machine>.fbx (one machine per file, moving parts kept as separate objects:
    // Cab, Boom, Arm, Bucket, Bed, Wheel_0…) and three kits with many small items each (Works_Site, Works_Carry,
    // Works_Tools: one root object per item, found by name). Every file has one baked atlas <file>_BaseColor.
    public static class CheckoutWorksKit
    {
        static readonly string[] Kits = { "Works_Site", "Works_Carry", "Works_Tools" };
        static readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
        static readonly Dictionary<string, GameObject> prefabs = new Dictionary<string, GameObject>();
        static Material missing;

        static GameObject Prefab(string file)
        {
            if (prefabs.TryGetValue(file, out var p)) return p;
            p = Resources.Load<GameObject>("CheckoutWorks/" + file);
            prefabs[file] = p;
            return p;
        }

        static Material Atlas(string file)
        {
            if (materials.TryGetValue(file, out var m) && m) return m;
            var tex = Resources.Load<Texture2D>("CheckoutWorks/" + file + "_BaseColor");
            m = new Material(Shader.Find("Standard")) { name = file + " (baked)" };
            if (tex) m.mainTexture = tex; else m.color = new Color(.85f, .7f, .3f);
            m.SetFloat("_Glossiness", .12f);
            materials[file] = m;
            return m;
        }

        public static Transform FindPart(Transform root, string name)
        {
            if (!root) return null;
            if (root.name == name) return root;
            foreach (Transform child in root) { var found = FindPart(child, name); if (found) return found; }
            return null;
        }

        /// <summary>
        /// An item standing at `position` facing `forward` (its front: the cab of a vehicle, the boom of an
        /// excavator). Returns a holder; the model is its child, turned so that its front is the holder's +Z.
        /// </summary>
        public static Transform Spawn(string name, Transform parent, Vector3 position, Vector3 forward, float scale = 1)
        {
            var holder = new GameObject(name).transform;
            holder.SetParent(parent, false);
            holder.position = position;
            holder.rotation = Quaternion.LookRotation(Flat(forward), Vector3.up);
            GameObject source = null; string file = null; Quaternion rotation = Quaternion.identity; Vector3 size = Vector3.one;
            var direct = Prefab(name);
            if (direct) { source = direct; file = name; rotation = direct.transform.localRotation; size = direct.transform.localScale; }
            else
                foreach (var kit in Kits)
                {
                    var k = Prefab(kit); if (!k) continue;
                    var child = FindPart(k.transform, name);
                    if (!child) continue;
                    source = child.gameObject; file = kit;
                    rotation = k.transform.localRotation * child.localRotation;
                    size = Vector3.Scale(k.transform.localScale, child.localScale);
                    break;
                }
            if (!source)
            {
                // Stand-in while a model is missing.
                var cube = GameObject.CreatePrimitive(PrimitiveType.Cube);
                UnityEngine.Object.Destroy(cube.GetComponent<Collider>());
                cube.name = name + " (missing)";
                cube.transform.SetParent(holder, false);
                cube.transform.localScale = new Vector3(.6f, .6f, .6f); cube.transform.localPosition = new Vector3(0, .3f, 0);
                if (!missing) missing = new Material(Shader.Find("Standard")) { color = new Color(1, .3f, .7f) };
                cube.GetComponent<Renderer>().sharedMaterial = missing;
                return holder;
            }
            var model = UnityEngine.Object.Instantiate(source, holder);
            model.name = "Model";
            model.transform.localPosition = Vector3.zero;
            model.transform.localRotation = rotation;
            model.transform.localScale = size * scale;
            model.SetActive(true);
            var mat = Atlas(file);
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials; for (int i = 0; i < mats.Length; i++) mats[i] = mat; r.sharedMaterials = mats;
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            }
            // Turn the model so its front (measured on its parts) looks along the holder's +Z.
            var front = Front(model.transform);
            if (front.sqrMagnitude > .0001f)
            {
                float angle = Vector3.SignedAngle(front, holder.forward, Vector3.up);
                model.transform.rotation = Quaternion.AngleAxis(angle, Vector3.up) * model.transform.rotation;
            }
            // Stand on the ground: the lowest point of the model on the holder.
            var b = Bounds(model);
            if (b.size.sqrMagnitude > 0) model.transform.position += Vector3.up * (holder.position.y - b.min.y);
            return holder;
        }

        // Where a machine's front is, from its parts (front wheels, the boom over the cab, the forks...).
        static Vector3 Front(Transform model)
        {
            Transform P(string n) => FindPart(model, n);
            // Wheel_0/1 are the front axle (left, right), then rearwards: front-left minus rear-left.
            var w0 = P("Wheel_0"); var wLast = P("Wheel_4") ?? P("Wheel_2");
            if (w0 && wLast) return Flat(w0.position - wLast.position);
            var cab = P("Cab"); var boom = P("Boom");
            if (cab && boom) { var tip = P("BoomTip") ?? P("Arm"); return Flat((tip ? tip.position : boom.position) - cab.position); }
            var arms = P("Arms"); var bucket = P("Bucket");
            if (arms && bucket) return Flat(bucket.position - arms.position);
            var mast = P("Mast"); var body = P("Body");
            if (mast && body) return Flat(mast.position - Bounds(body.gameObject).center);
            return Vector3.zero;
        }

        public static Vector3 Flat(Vector3 v) { v.y = 0; return v.sqrMagnitude < 1e-6f ? Vector3.forward : v.normalized; }

        public static Bounds Bounds(GameObject go)
        {
            var rs = go.GetComponentsInChildren<Renderer>(false);
            if (rs.Length == 0) return new Bounds(go.transform.position, Vector3.zero);
            var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
            return b;
        }
    }

    /// <summary>
    /// A live works scene: the crew (the game's workers in hard hats, carrying things or using tools), the
    /// machines (excavators digging, cranes swinging loads, a wrecking ball, a skid loader, trucks...), dust and
    /// things that follow the progress of the works (a frame rising, a skip filling, a heap growing). The scenes
    /// themselves are put together by CheckoutEraWorks (one per expansion) and CheckoutLotSites (clearing a lot).
    /// </summary>
    public class CheckoutWorksScene : MonoBehaviour
    {
        public double startedAt, endsAt;
        public float Progress => endsAt <= startedAt ? 1 : Mathf.Clamp01((float)((CheckoutConstructionSite.Now - startedAt) / (endsAt - startedAt)));
        public Action<CheckoutWorksScene> onProgress;

        public enum Tool { None, Hammer, Sledge, Saw, Shovel, Trimmer, Drill, Roller, Crowbar, Wrench, Broom, Trowel, Weld }
        static readonly Dictionary<Tool, string> ToolModels = new Dictionary<Tool, string>
        {
            [Tool.Hammer] = "Tool_Hammer", [Tool.Sledge] = "Tool_Sledgehammer", [Tool.Saw] = "Tool_Saw", [Tool.Shovel] = "Tool_Shovel",
            [Tool.Trimmer] = "Tool_BrushCutter", [Tool.Drill] = "Tool_Drill", [Tool.Roller] = "Tool_PaintRoller", [Tool.Crowbar] = "Tool_Crowbar",
            [Tool.Wrench] = "Tool_Wrench", [Tool.Broom] = "Tool_Broom", [Tool.Trowel] = "Tool_Trowel", [Tool.Weld] = "Tool_Drill",
        };

        class Worker
        {
            public Transform body, handL, handR, upperL, upperR, foreR, tool, prop, ride;
            public Animation anim; public string clip;
            public Tool use; public Vector3 a, b, look; public string carry;
            public int phase; public float clock, wait, speed = 1, yaw, seed; public bool carrier, foreman;
        }
        readonly List<Worker> workers = new List<Worker>();

        abstract class Machine { public Transform root; public float clock, offset; public abstract void Tick(CheckoutWorksScene s, float dt); }
        readonly List<Machine> machines = new List<Machine>();
        readonly List<Action<float>> progressItems = new List<Action<float>>();

        ParticleSystem dust, sparks, chips;
        Material dustMat, sparkMat, cableMat;
        Transform pill; TextMeshPro pillText; Transform pillFill;
        CheckoutConstructionSite art;
        float boardClock;

        public static CheckoutWorksScene Create(string name, double startedAt, double endsAt)
        {
            var go = new GameObject(name);
            var s = go.AddComponent<CheckoutWorksScene>();
            s.startedAt = startedAt; s.endsAt = endsAt;
            s.art = FindAnyObjectByType<CheckoutConstructionSite>(FindObjectsInactive.Include);
            var show = s.art ? s.art.GetComponent<CheckoutStageConstruction>() : FindAnyObjectByType<CheckoutStageConstruction>(FindObjectsInactive.Include);
            s.dustMat = show ? show.dustMaterial : null; s.sparkMat = show ? show.sparkMaterial : null;
            s.Effects();
            return s;
        }

        public void SetTimes(double start, double end) { startedAt = start; endsAt = end; }

        // ---------------------------------------------------------------- props
        public Transform Prop(string name, Vector3 at, Vector3 forward, float scale = 1) => CheckoutWorksKit.Spawn(name, transform, at, forward, scale);

        /// <summary>Something that grows with the works (a frame going up, a skip filling): scale 0→1 over [from, to].</summary>
        public void Grow(Transform item, float from, float to, bool vertical = true)
        {
            if (!item) return;
            var full = item.localScale;
            progressItems.Add(p =>
            {
                if (!item) return;
                float k = Mathf.Clamp01(Mathf.InverseLerp(from, to, p));
                item.localScale = vertical ? new Vector3(full.x, Mathf.Max(.02f, full.y * k), full.z) : full * Mathf.Max(.02f, k);
                item.gameObject.SetActive(k > .005f);
            });
        }

        public void OnProgress(Action<float> step) => progressItems.Add(step);

        /// <summary>Walls of a small building rising with the works (brick or block, with a door gap in front).</summary>
        public Transform Walls(Vector3 centre, Vector2 size, float height, Color colour, float from, float to, float door = 1.2f)
        {
            var g = new GameObject("Rising walls").transform; g.SetParent(transform, false); g.position = centre;
            var m = new Material(Shader.Find("Standard")) { color = colour }; m.SetFloat("_Glossiness", .05f);
            void W(Vector3 c, Vector3 s)
            {
                var w = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(w.GetComponent<Collider>());
                w.transform.SetParent(g, false); w.transform.localPosition = c; w.transform.localScale = s;
                w.GetComponent<Renderer>().sharedMaterial = m;
            }
            const float t = .25f; float hx = size.x * .5f, hz = size.y * .5f, side = (size.x - door) * .5f;
            W(new Vector3(0, .5f, hz), new Vector3(size.x, 1, t));
            W(new Vector3(-hx, .5f, 0), new Vector3(t, 1, size.y));
            W(new Vector3(hx, .5f, 0), new Vector3(t, 1, size.y));
            W(new Vector3(-hx + side * .5f, .5f, -hz), new Vector3(side, 1, t));
            W(new Vector3(hx - side * .5f, .5f, -hz), new Vector3(side, 1, t));
            // A slab under it.
            var slab = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(slab.GetComponent<Collider>());
            slab.transform.SetParent(transform, false); slab.transform.position = centre + Vector3.up * .06f; slab.transform.localScale = new Vector3(size.x + .4f, .12f, size.y + .4f);
            var concrete = new Material(Shader.Find("Standard")) { color = new Color(.72f, .71f, .68f) };
            slab.GetComponent<Renderer>().sharedMaterial = concrete;
            g.localScale = new Vector3(1, .02f, 1);
            progressItems.Add(p => { if (g) g.localScale = new Vector3(1, Mathf.Max(.02f, height * Mathf.Clamp01(Mathf.InverseLerp(from, to, p))), 1); });
            return g;
        }

        // ---------------------------------------------------------------- crew
        MarketDay.MarketDeliveryWorker template;
        Worker NewWorker(Vector3 a, Vector3 look, int variant)
        {
            if (!template) template = FindAnyObjectByType<MarketDay.MarketDeliveryWorker>(FindObjectsInactive.Include);
            if (!template) return null;
            var holder = new GameObject("Crew holder"); holder.SetActive(false);
            var clone = Instantiate(template.gameObject, holder.transform);
            DestroyImmediate(clone.GetComponent<MarketDay.MarketDeliveryWorker>());
            foreach (Transform child in clone.transform.Cast<Transform>().ToArray()) if (child.name != "Visual") DestroyImmediate(child.gameObject);
            clone.name = "Worker";
            var crew = art ? art.crew : null;
            foreach (var r in clone.GetComponentsInChildren<Renderer>(true))
            {
                r.enabled = true;
                if (r is SkinnedMeshRenderer skin && crew != null && crew.Length > 0 && crew[variant % crew.Length]) skin.sharedMaterial = crew[variant % crew.Length];
            }
            clone.transform.SetParent(transform, false);
            Destroy(holder);
            clone.transform.SetPositionAndRotation(a, Quaternion.LookRotation(CheckoutWorksKit.Flat(look - a)));
            var bones = clone.GetComponentsInChildren<Transform>(true);
            Transform B(string n) => bones.FirstOrDefault(x => x.name == n);
            var w = new Worker
            {
                body = clone.transform, a = a, look = look, anim = clone.GetComponentInChildren<Animation>(true),
                handL = B("Hand_L"), handR = B("Hand_R"), upperL = B("UpperArm_L"), upperR = B("UpperArm_R"), foreR = B("Forearm_R"),
                wait = variant * .6f, speed = .85f + variant % 3 * .12f, clock = variant * 1.37f, seed = UnityEngine.Random.value * 7f,
            };
            var head = B("Head");
            var hatKit = art && art.kit ? art.kit.Find("Hard hat") : null;
            if (head && hatKit)
            {
                var hat = Instantiate(hatKit.gameObject).transform; hat.gameObject.SetActive(true);
                hat.localScale = Vector3.one * .56f;
                hat.SetPositionAndRotation(clone.transform.position + Vector3.up * 2.13f + clone.transform.forward * .02f, clone.transform.rotation);
                hat.SetParent(head, true);
            }
            clone.SetActive(true);
            Play(w, "Idle");
            workers.Add(w);
            return w;
        }

        /// <summary>A worker using a tool at `spot`, facing `look` (hammering, sawing, digging, trimming...).</summary>
        public void ToolWorker(Vector3 spot, Vector3 look, Tool tool, int variant = 0)
        {
            var w = NewWorker(spot, look, variant); if (w == null) return;
            w.use = tool;
            if (ToolModels.TryGetValue(tool, out var model))
            {
                w.tool = CheckoutWorksKit.Spawn(model, transform, spot, Vector3.forward);
                // The tool's handle sits in the hand: drop the holder's ground snap.
                var m = w.tool.Find("Model"); if (m) m.localPosition = Vector3.zero;
            }
        }

        /// <summary>A worker carrying `prop` from `from` to `to` and walking back, over and over.</summary>
        public void Carrier(Vector3 from, Vector3 to, string prop, int variant = 0)
        {
            var w = NewWorker(from, to, variant); if (w == null) return;
            w.carrier = true; w.a = from; w.b = to; w.carry = prop;
            if (!string.IsNullOrEmpty(prop))
            {
                w.prop = CheckoutWorksKit.Spawn(prop, transform, from, Vector3.forward);
                var m = w.prop.Find("Model"); if (m) m.localPosition = Vector3.zero;
                w.prop.gameObject.SetActive(false);
            }
        }

        /// <summary>The foreman: walks a little, looks at the works, checks the plans.</summary>
        public void Foreman(Vector3 a, Vector3 b, Vector3 look, int variant = 1)
        {
            var w = NewWorker(a, look, variant); if (w == null) return;
            w.foreman = true; w.a = a; w.b = b; w.look = look;
        }

        /// <summary>A worker standing in a moving basket (aerial platform), working with a tool.</summary>
        public void Rider(Transform basket, Vector3 look, Tool tool)
        {
            var w = NewWorker(basket.position, look, 2); if (w == null) return;
            w.ride = basket; w.use = tool;
            if (ToolModels.TryGetValue(tool, out var model)) { w.tool = CheckoutWorksKit.Spawn(model, transform, basket.position, Vector3.forward); var m = w.tool.Find("Model"); if (m) m.localPosition = Vector3.zero; }
        }

        void Play(Worker w, string clip)
        {
            if (!w.anim || w.clip == clip || !w.anim[clip]) return;
            w.clip = clip; w.anim[clip].time = 0; w.anim.CrossFade(clip, .15f);
        }
        float Length(Worker w, string clip) => w.anim && w.anim[clip] ? w.anim[clip].length : 1.5f;

        bool Walk(Worker w, Vector3 target, float dt, bool loaded)
        {
            var delta = target - w.body.position; delta.y = 0;
            if (delta.magnitude < .06f) return true;
            w.body.rotation = Quaternion.RotateTowards(w.body.rotation, Quaternion.LookRotation(delta), dt * 260);
            if (Vector3.Angle(w.body.forward, delta) > 35) { Play(w, loaded ? "CarryIdle" : "Idle"); return false; }
            Play(w, loaded ? "CarryWalking" : "Walking");
            w.body.position = Vector3.MoveTowards(w.body.position, new Vector3(target.x, w.body.position.y, target.z), dt * (loaded ? 1.05f : 1.25f));
            return false;
        }

        void Face(Worker w, Vector3 point, float dt)
        {
            var d = point - w.body.position; d.y = 0;
            if (d.sqrMagnitude > .001f) w.body.rotation = Quaternion.RotateTowards(w.body.rotation, Quaternion.LookRotation(d), dt * 200);
        }

        void Crew(float dt)
        {
            foreach (var w in workers)
            {
                if (!w.body) continue;
                if (w.ride) { w.body.position = w.ride.position; Face(w, w.look, dt); Play(w, "Idle"); continue; }
                if (w.wait > 0) { w.wait -= dt; Play(w, "Idle"); continue; }
                w.clock += dt;
                if (w.carrier)
                {
                    bool loaded = w.prop && w.prop.gameObject.activeSelf;
                    if (w.phase == 0 && Walk(w, w.a, dt, false)) { w.phase = 1; w.clock = 0; Play(w, "Pickup"); }
                    else if (w.phase == 1)
                    {
                        if (w.clock > Length(w, "Pickup") * .55f && w.prop) w.prop.gameObject.SetActive(true);
                        if (w.clock > Length(w, "Pickup")) { w.phase = 2; w.clock = 0; }
                    }
                    else if (w.phase == 2 && Walk(w, w.b, dt, true)) { w.phase = 3; w.clock = 0; Play(w, "PutDown"); }
                    else if (w.phase == 3)
                    {
                        if (w.clock > Length(w, "PutDown") * .65f && w.prop) w.prop.gameObject.SetActive(false);
                        if (w.clock > Length(w, "PutDown")) { w.phase = 0; w.clock = 0; w.wait = .4f; }
                    }
                    continue;
                }
                if (w.foreman)
                {
                    // Looks at the works, walks to the other end, looks again, walks back.
                    if (w.phase == 0 || w.phase == 2) { Play(w, "Idle"); Face(w, w.look, dt); if (w.clock > 4.5f) { w.phase++; w.clock = 0; } }
                    else if (Walk(w, w.phase == 1 ? w.b : w.a, dt, false)) { w.phase = w.phase == 1 ? 2 : 0; w.clock = 0; }
                    continue;
                }
                // Tool work: stand at the spot and face the work.
                Play(w, "Idle");
                Face(w, w.look, dt);
            }
        }

        // Procedural arm swings over the Idle pose, and the tool in the hand.
        void LateUpdate()
        {
            float t = Time.time;
            foreach (var w in workers)
            {
                if (!w.body) continue;
                if (w.prop && w.prop.gameObject.activeSelf && w.handL && w.handR)
                {
                    w.prop.position = (w.handL.position + w.handR.position) * .5f + Vector3.down * .3f + w.body.forward * .15f;
                    w.prop.rotation = Quaternion.LookRotation(w.body.right, Vector3.up);
                }
                if (w.use == Tool.None || w.carrier || w.foreman) continue;
                var right = w.body.right; var fwd = w.body.forward;
                float s = w.clock * w.speed + w.seed;
                float raiseR = 0, raiseL = 0; float twist = 0; bool both = false;
                switch (w.use)
                {
                    case Tool.Hammer: { float c = Mathf.Repeat(s * 1.6f, 1); raiseR = c < .7f ? Mathf.Lerp(50, 120, c / .7f) : Mathf.Lerp(120, 45, (c - .7f) / .3f); raiseL = 40; break; }
                    case Tool.Sledge: { float c = Mathf.Repeat(s * .75f, 1); raiseR = raiseL = c < .65f ? Mathf.Lerp(40, 165, c / .65f) : Mathf.Lerp(165, 25, (c - .65f) / .35f); both = true; if (c > .95f) Burst(w.body.position + fwd * 1.3f, 4); break; }
                    case Tool.Saw: raiseR = 60 + 18 * Mathf.Sin(s * 9f); raiseL = 35; break;
                    case Tool.Shovel: { float c = Mathf.Repeat(s * .6f, 1); raiseR = raiseL = c < .5f ? Mathf.Lerp(25, 55, c * 2) : Mathf.Lerp(55, 95, (c - .5f) * 2); both = true; if (Mathf.Abs(c - .52f) < .01f) Burst(w.body.position + fwd * 1.1f, 2); break; }
                    case Tool.Trimmer: raiseR = raiseL = 45; both = true; twist = 28 * Mathf.Sin(s * 1.6f); EmitChips(w, fwd, s); break;
                    case Tool.Drill: raiseR = 88 + 3 * Mathf.Sin(s * 40); raiseL = 70; both = true; break;
                    case Tool.Weld: raiseR = 75; raiseL = 60; if (Mathf.Repeat(s, .5f) < Time.deltaTime * w.speed && sparks && w.handR) { sparks.transform.position = w.handR.position + fwd * .3f; sparks.Emit(UnityEngine.Random.Range(8, 16)); } break;
                    case Tool.Roller: raiseR = raiseL = 95 + 50 * Mathf.Sin(s * 1.8f); both = true; break;
                    case Tool.Crowbar: raiseR = raiseL = 55 + 25 * Mathf.Abs(Mathf.Sin(s * 1.2f)); both = true; break;
                    case Tool.Wrench: raiseR = 80; raiseL = 30; twist = 10 * Mathf.Sin(s * 4); break;
                    case Tool.Broom: raiseR = raiseL = 35 + 12 * Mathf.Sin(s * 2.4f); both = true; break;
                    case Tool.Trowel: raiseR = 65 + 15 * Mathf.Sin(s * 3f); raiseL = 30; break;
                }
                if (twist != 0) { w.body.rotation = Quaternion.LookRotation(CheckoutWorksKit.Flat(w.look - w.body.position)) * Quaternion.Euler(0, twist, 0); right = w.body.right; fwd = w.body.forward; }
                if (w.upperR) w.upperR.rotation = Quaternion.AngleAxis(-raiseR, right) * w.upperR.rotation;
                if (w.upperL) w.upperL.rotation = Quaternion.AngleAxis(-raiseL, right) * w.upperL.rotation;
                if (!w.tool || !w.handR) continue;
                var hand = both && w.handL ? (w.handR.position + w.handL.position) * .5f : w.handR.position;
                Vector3 up;
                switch (w.use)
                {
                    case Tool.Trimmer: up = (Vector3.up * .55f - fwd * .85f).normalized; break;
                    case Tool.Shovel: case Tool.Broom: up = (fwd * .55f - Vector3.up * .83f).normalized; break;
                    case Tool.Roller: up = (Vector3.up * .9f + fwd * .3f).normalized; break;
                    default:
                        var d = w.foreR ? (w.handR.position - w.foreR.position).normalized : fwd;
                        up = Vector3.Cross(d, right).normalized; if (up.sqrMagnitude < .01f) up = Vector3.up; break;
                }
                w.tool.position = hand;
                w.tool.rotation = Quaternion.LookRotation(Vector3.Cross(right, up).sqrMagnitude > .01f ? Vector3.Cross(right, up) : fwd, up);
            }
        }

        void EmitChips(Worker w, Vector3 fwd, float s)
        {
            if (!chips || Mathf.Repeat(s, .25f) > Time.deltaTime * w.speed * 1.2f) return;
            chips.transform.position = w.body.position + fwd * 1.3f + Vector3.up * .15f;
            chips.Emit(UnityEngine.Random.Range(4, 8));
        }

        // ---------------------------------------------------------------- effects
        void Effects()
        {
            dust = Particles("Dust", dustMat, new Color(.88f, .82f, .72f, .55f), new Color(.75f, .7f, .62f, .4f), 1.2f, 2.6f, .6f, 1.6f, -.05f, 1.6f, 3.2f, ParticleSystemRenderMode.Billboard);
            chips = Particles("Clippings", dustMat, new Color(.45f, .7f, .25f, .9f), new Color(.6f, .55f, .25f, .9f), .08f, .16f, 1.5f, 3f, .9f, .5f, 1f, ParticleSystemRenderMode.Billboard);
            sparks = Particles("Sparks", sparkMat, new Color(1f, .95f, .6f), new Color(1f, .6f, .15f), .05f, .1f, 1.5f, 3.5f, 1.2f, .3f, .7f, ParticleSystemRenderMode.Stretch);
        }

        ParticleSystem Particles(string name, Material m, Color a, Color b, float size0, float size1, float speed0, float speed1, float gravity, float life0, float life1, ParticleSystemRenderMode mode)
        {
            var go = new GameObject(name); go.transform.SetParent(transform, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.loop = false; main.playOnAwake = false;
            main.startLifetime = new ParticleSystem.MinMaxCurve(life0, life1); main.startSpeed = new ParticleSystem.MinMaxCurve(speed0, speed1);
            main.startSize = new ParticleSystem.MinMaxCurve(size0, size1); main.startColor = new ParticleSystem.MinMaxGradient(a, b);
            main.gravityModifier = gravity; main.maxParticles = 200; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Sphere; shape.radius = name == "Dust" ? .8f : .1f;
            var emission = ps.emission; emission.rateOverTime = 0;
            var col = ps.colorOverLifetime; col.enabled = true;
            var fade = new Gradient(); fade.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) }, new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(1, .6f), new GradientAlphaKey(0, 1) });
            col.color = fade;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.sharedMaterial = m; r.renderMode = mode;
            if (mode == ParticleSystemRenderMode.Stretch) { r.velocityScale = .06f; r.lengthScale = 1; }
            return ps;
        }

        /// <summary>A puff of dust (a wall knocked, a bucket emptied).</summary>
        public void Burst(Vector3 at, int count = 6)
        {
            if (!dust) return;
            dust.transform.position = at + Vector3.up * .4f; dust.Emit(count);
        }

        // ---------------------------------------------------------------- machines
        static Vector3 RightOf(Transform t) => Vector3.Cross(Vector3.up, CheckoutWorksKit.Flat(t.forward));

        class Pose
        {
            public Transform t; public Quaternion rest;
            public Pose(Transform part) { t = part; rest = part ? part.localRotation : Quaternion.identity; }
            public void Reset() { if (t) t.localRotation = rest; }
            public void Turn(float angle, Vector3 worldAxis) { if (t) t.rotation = Quaternion.AngleAxis(angle, worldAxis) * t.rotation; }
        }

        static float Smooth(float a, float b, float t) => Mathf.Lerp(a, b, Mathf.SmoothStep(0, 1, Mathf.Clamp01(t)));

        /// <summary>Excavator (mini or big): digs at `dig` and empties the bucket over `dump`, over and over.</summary>
        public Transform Excavator(string model, Vector3 at, Vector3 forward, Vector3 dig, Vector3 dump, bool demolish = false)
        {
            var root = Prop(model, at, forward);
            machines.Add(new Digger(root, dig, dump, demolish) { offset = UnityEngine.Random.value * 3 });
            return root;
        }

        class Digger : Machine
        {
            readonly Pose cab, boom, arm, bucket; readonly float digYaw, dumpYaw; readonly bool demolish; readonly Vector3 dig, dump;
            public Digger(Transform r, Vector3 dig, Vector3 dump, bool demolish)
            {
                root = r; this.dig = dig; this.dump = dump; this.demolish = demolish;
                Transform P(string n) => CheckoutWorksKit.FindPart(r, n);
                cab = new Pose(P("Cab")); boom = new Pose(P("Boom")); arm = new Pose(P("Arm")); bucket = new Pose(P("Bucket"));
                digYaw = Vector3.SignedAngle(CheckoutWorksKit.Flat(r.forward), CheckoutWorksKit.Flat(dig - r.position), Vector3.up);
                dumpYaw = Vector3.SignedAngle(CheckoutWorksKit.Flat(r.forward), CheckoutWorksKit.Flat(dump - r.position), Vector3.up);
            }
            public override void Tick(CheckoutWorksScene s, float dt)
            {
                clock += dt;
                float c = Mathf.Repeat(clock + offset, 9f);
                float yaw, b, a, k;
                if (c < 1.5f) { yaw = Smooth(dumpYaw, digYaw, c / 1.5f); b = -10; a = -20; k = 30; }
                else if (c < 3.5f) { float u = (c - 1.5f) / 2; yaw = digYaw; b = Smooth(-10, demolish ? 5 : 22, u); a = Smooth(-20, 25, u); k = Smooth(30, -40, u); }
                else if (c < 4.5f) { yaw = digYaw; b = Smooth(demolish ? 5 : 22, -18, c - 3.5f); a = 25; k = -40; }
                else if (c < 6f) { yaw = Smooth(digYaw, dumpYaw, (c - 4.5f) / 1.5f); b = -18; a = 25; k = -40; }
                else if (c < 7.2f) { yaw = dumpYaw; b = -18; a = Smooth(25, -10, (c - 6f) / 1.2f); k = Smooth(-40, 45, (c - 6f) / 1.2f); }
                else { yaw = dumpYaw; b = Smooth(-18, -10, (c - 7.2f) / 1.8f); a = Smooth(-10, -20, (c - 7.2f) / 1.8f); k = Smooth(45, 30, (c - 7.2f) / 1.8f); }
                if (Mathf.Abs(c - 3.4f) < dt) s.Burst(dig, demolish ? 10 : 4);
                if (Mathf.Abs(c - 6.9f) < dt) s.Burst(dump, 5);
                cab.Reset(); boom.Reset(); arm.Reset(); bucket.Reset();
                cab.Turn(yaw, Vector3.up);
                var right = cab.t ? Vector3.Cross(Vector3.up, CheckoutWorksKit.Flat(Quaternion.AngleAxis(yaw, Vector3.up) * root.forward)) : RightOf(root);
                boom.Turn(b, right); arm.Turn(a, right); bucket.Turn(k, right);
            }
        }

        /// <summary>Crane truck (munck): lifts `load` from `pick` and sets it at `drop`, then puts the hook back.
        /// With `once`, the lift follows the works progress between `from` and `to` and the load stays.</summary>
        public Transform CraneTruck(Vector3 at, Vector3 forward, Transform load, Vector3 pick, Vector3 drop, bool once = false, float from = 0, float to = 1)
        {
            var root = Prop("Works_CraneTruck", at, forward);
            machines.Add(new Munck(this, root, load, pick, drop, once, from, to) { offset = UnityEngine.Random.value * 4 });
            return root;
        }

        class Munck : Machine
        {
            readonly Pose crane, arm; readonly Transform tip, hook, load, cable; readonly Vector3 pick, drop; readonly bool once; readonly float from, to;
            readonly float pickYaw, dropYaw; readonly CheckoutWorksScene scene;
            public Munck(CheckoutWorksScene s, Transform r, Transform load, Vector3 pick, Vector3 drop, bool once, float from, float to)
            {
                scene = s; root = r; this.load = load; this.pick = pick; this.drop = drop; this.once = once; this.from = from; this.to = to;
                crane = new Pose(CheckoutWorksKit.FindPart(r, "CraneBase")); arm = new Pose(CheckoutWorksKit.FindPart(r, "CraneArm"));
                tip = CheckoutWorksKit.FindPart(r, "CraneTip"); hook = CheckoutWorksKit.FindPart(r, "Hook");
                var basePos = crane.t ? crane.t.position : r.position;
                // Yaw relative to the arm's rest direction (it rests pointing back over the deck).
                var rest = tip ? CheckoutWorksKit.Flat(tip.position - basePos) : -CheckoutWorksKit.Flat(r.forward);
                pickYaw = Vector3.SignedAngle(rest, CheckoutWorksKit.Flat(pick - basePos), Vector3.up);
                dropYaw = Vector3.SignedAngle(rest, CheckoutWorksKit.Flat(drop - basePos), Vector3.up);
                cable = s.Line("Crane cable");
            }
            public override void Tick(CheckoutWorksScene s, float dt)
            {
                clock += dt;
                float yaw, lift, u; bool carrying;
                if (once)
                {
                    u = Mathf.Clamp01(Mathf.InverseLerp(from, to, s.Progress));
                    carrying = u > .05f && u < .95f;
                    yaw = u < .2f ? Smooth(0, pickYaw, u / .2f) : u < .8f ? Smooth(pickYaw, dropYaw, (u - .2f) / .6f) : Smooth(dropYaw, 0, (u - .8f) / .2f);
                    lift = u < .2f ? 0 : u < .3f ? (u - .2f) * 10 : u < .7f ? 1 : u < .8f ? (.8f - u) * 10 : 0;
                }
                else
                {
                    float c = Mathf.Repeat(clock + offset, 14f);
                    carrying = c > 3 && c < 9;
                    yaw = c < 2 ? Smooth(0, pickYaw, c / 2) : c < 3 ? pickYaw : c < 8 ? Smooth(pickYaw, dropYaw, (c - 3) / 5) : c < 9 ? dropYaw : c < 12 ? Smooth(dropYaw, pickYaw, (c - 9) / 3) : pickYaw;
                    lift = c < 2 ? 0 : c < 3 ? c - 2 : c < 8 ? 1 : c < 9 ? 9 - c : 0;
                    u = c;
                }
                crane.Reset(); arm.Reset();
                crane.Turn(yaw, Vector3.up);
                var dir = tip && crane.t ? CheckoutWorksKit.Flat(tip.position - crane.t.position) : root.forward;
                arm.Turn(-25 * lift - 8, Vector3.Cross(Vector3.up, dir));
                if (!tip) return;
                var target = carrying ? (load ? load.position : tip.position) : tip.position;
                float hookY = Mathf.Lerp(Mathf.Max(.6f, (once ? drop.y : pick.y) + 1.4f), tip.position.y - .8f, lift);
                var hookPos = new Vector3(tip.position.x, hookY, tip.position.z);
                if (hook) hook.position = hookPos;
                if (load && carrying) load.position = hookPos + Vector3.down * 1.0f - Vector3.up * .3f;
                if (load && once && u >= .95f) load.position = new Vector3(drop.x, drop.y, drop.z);
                if (load && once && u <= .05f) load.position = pick;
                scene.Stretch(cable, tip.position, hookPos);
            }
        }

        /// <summary>Crawler crane swinging a wrecking ball into `target`.</summary>
        public Transform WreckingCrane(Vector3 at, Vector3 forward, Vector3 target)
        {
            var root = Prop("Works_WreckingCrane", at, forward);
            machines.Add(new Wrecker(this, root, target) { offset = UnityEngine.Random.value * 3 });
            return root;
        }

        class Wrecker : Machine
        {
            readonly Pose cab; readonly Transform tip, ball, cable; readonly Vector3 target; readonly float yaw;
            public Wrecker(CheckoutWorksScene s, Transform r, Vector3 target)
            {
                root = r; this.target = target;
                cab = new Pose(CheckoutWorksKit.FindPart(r, "Cab")); tip = CheckoutWorksKit.FindPart(r, "BoomTip"); ball = CheckoutWorksKit.FindPart(r, "Ball");
                var basePos = cab.t ? cab.t.position : r.position;
                yaw = tip ? Vector3.SignedAngle(CheckoutWorksKit.Flat(tip.position - basePos), CheckoutWorksKit.Flat(target - basePos), Vector3.up) : 0;
                cable = s.Line("Wrecking cable");
            }
            public override void Tick(CheckoutWorksScene s, float dt)
            {
                clock += dt;
                cab.Reset(); cab.Turn(yaw + 12 * Mathf.Sin((clock + offset) * .35f), Vector3.up);
                if (!tip || !ball) return;
                // Pendulum from the boom tip towards the building; a hit at the far end of the swing.
                float length = Mathf.Max(3f, tip.position.y - 2.2f);
                var towards = CheckoutWorksKit.Flat(target - tip.position);
                float swing = Mathf.Sin((clock + offset) * 1.1f);
                float angle = Mathf.Lerp(-20, 38, (swing + 1) * .5f) * Mathf.Deg2Rad;
                var p = tip.position + towards * Mathf.Sin(angle) * length + Vector3.down * Mathf.Cos(angle) * length;
                ball.position = p;
                if (swing > .985f && Mathf.Repeat(clock, 5.7f) > .2f) s.Burst(p + towards * .6f, 3);
                s.Stretch(cable, tip.position, p + Vector3.up * .5f);
            }
        }

        /// <summary>Skid loader shuttling between `pile` and `dump`, raising the bucket to empty it.</summary>
        public Transform SkidLoader(Vector3 pile, Vector3 dump)
        {
            var root = Prop("Works_SkidLoader", pile, dump - pile);
            machines.Add(new Loader(root, pile, dump) { offset = UnityEngine.Random.value * 3 });
            return root;
        }

        class Loader : Machine
        {
            readonly Pose arms, bucket; readonly Vector3 a, b;
            public Loader(Transform r, Vector3 a, Vector3 b) { root = r; this.a = a; this.b = b; arms = new Pose(CheckoutWorksKit.FindPart(r, "Arms")); bucket = new Pose(CheckoutWorksKit.FindPart(r, "Bucket")); }
            public override void Tick(CheckoutWorksScene s, float dt)
            {
                clock += dt;
                float c = Mathf.Repeat(clock + offset, 12f);
                var dir = CheckoutWorksKit.Flat(b - a);
                var near = a + dir * 1.2f; var far = b - dir * 2.2f;
                float lift = 0, tip = 0;
                if (c < 1.5f) { root.position = Vector3.Lerp(root.position, near, dt * 2); tip = Smooth(0, -30, c / 1.5f); if (c > 1.4f && c - dt <= 1.4f) s.Burst(a, 4); }
                else if (c < 5f) { float u = (c - 1.5f) / 3.5f; root.position = Vector3.Lerp(near, far, Mathf.SmoothStep(0, 1, u)); lift = Smooth(0, 1, u * 2); tip = -30; }
                else if (c < 6.5f) { lift = 1; tip = Smooth(-30, 50, (c - 5) / 1.5f); if (c > 6f && c - dt <= 6f) s.Burst(b, 5); }
                else if (c < 10f) { float u = (c - 6.5f) / 3.5f; root.position = Vector3.Lerp(far, near, Mathf.SmoothStep(0, 1, u)); lift = Smooth(1, 0, u * 2); tip = Smooth(50, 0, u * 2); }
                root.rotation = Quaternion.LookRotation(dir);
                arms.Reset(); bucket.Reset();
                var right = RightOf(root);
                arms.Turn(-45 * lift, right); bucket.Turn(tip, right);
            }
        }

        /// <summary>Forklift moving pallets between `a` and `b` (forks up while driving).</summary>
        public Transform Forklift(Vector3 a, Vector3 b, string cargo = "Prop_Pallet")
        {
            var root = Prop("Works_Forklift", a, b - a);
            var load = string.IsNullOrEmpty(cargo) ? null : Prop(cargo, a, b - a);
            machines.Add(new Lift(root, a, b, load) { offset = UnityEngine.Random.value * 3 });
            return root;
        }

        class Lift : Machine
        {
            readonly Pose mast; readonly Transform forks, load; readonly Vector3 a, b, forkRest;
            public Lift(Transform r, Vector3 a, Vector3 b, Transform load) { root = r; this.a = a; this.b = b; this.load = load; mast = new Pose(CheckoutWorksKit.FindPart(r, "Mast")); forks = CheckoutWorksKit.FindPart(r, "Forks"); if (forks) forkRest = forks.localPosition; }
            public override void Tick(CheckoutWorksScene s, float dt)
            {
                clock += dt;
                float c = Mathf.Repeat(clock + offset, 16f);
                var dir = CheckoutWorksKit.Flat(b - a);
                float up = 0; bool carrying;
                if (c < 6f) { root.position = Vector3.Lerp(a, b - dir * 1.6f, Mathf.SmoothStep(0, 1, c / 6f)); root.rotation = Quaternion.LookRotation(dir); up = Smooth(0, 1, c); carrying = true; }
                else if (c < 8f) { up = Smooth(1, 0, c - 6f); carrying = c < 7.5f; }
                else if (c < 14f) { root.position = Vector3.Lerp(b - dir * 1.6f, a, Mathf.SmoothStep(0, 1, (c - 8f) / 6f)); root.rotation = Quaternion.LookRotation(dir); carrying = false; }
                else { up = 0; carrying = c > 15f; }
                if (forks) forks.localPosition = forkRest + forks.parent.InverseTransformVector(Vector3.up) * .6f * up;
                if (load)
                {
                    if (carrying && forks) { load.position = new Vector3(forks.position.x, forks.position.y, forks.position.z) + root.forward * .5f; load.rotation = root.rotation; }
                    else if (c >= 7.5f && c < 15f) load.position = b - dir * .9f;
                }
            }
        }

        /// <summary>A small concrete mixer turning its drum.</summary>
        public Transform Mixer(Vector3 at, Vector3 forward)
        {
            var root = Prop("Works_CementMixer", at, forward);
            machines.Add(new Drum(root));
            return root;
        }

        class Drum : Machine
        {
            readonly Pose drum;
            public Drum(Transform r) { root = r; drum = new Pose(CheckoutWorksKit.FindPart(r, "Drum")); }
            public override void Tick(CheckoutWorksScene s, float dt) { clock += dt; if (drum.t) drum.t.localRotation = drum.rest * Quaternion.Euler(0, 0, clock * 140f); }
        }

        /// <summary>Tow truck pulling `vehicle` up onto its bed over [from, to] of the works.</summary>
        public Transform TowTruck(Vector3 at, Vector3 forward, Transform vehicle, float from, float to)
        {
            var root = Prop("Works_TowTruck", at, forward);
            machines.Add(new Tow(this, root, vehicle, from, to));
            return root;
        }

        class Tow : Machine
        {
            readonly Pose bed; readonly Transform vehicle, cable, hook; readonly Vector3 start; readonly float from, to; readonly Quaternion startRot;
            public Tow(CheckoutWorksScene s, Transform r, Transform vehicle, float from, float to)
            {
                root = r; this.vehicle = vehicle; this.from = from; this.to = to;
                bed = new Pose(CheckoutWorksKit.FindPart(r, "Bed")); hook = CheckoutWorksKit.FindPart(r, "Hook");
                if (vehicle) { start = vehicle.position; startRot = vehicle.rotation; }
                cable = s.Line("Tow cable");
            }
            public override void Tick(CheckoutWorksScene s, float dt)
            {
                float u = Mathf.Clamp01(Mathf.InverseLerp(from, to, s.Progress));
                float tilt = u < .15f ? u / .15f : u < .8f ? 1 : (1 - u) / .2f;
                bed.Reset(); bed.Turn(-11 * tilt, RightOf(root));
                if (!vehicle || !bed.t) return;
                var onBed = bed.t.position + Vector3.up * .55f + root.forward * .3f;
                float pull = Mathf.Clamp01((u - .15f) / .6f);
                vehicle.position = Vector3.Lerp(start, onBed, Mathf.SmoothStep(0, 1, pull));
                vehicle.rotation = Quaternion.Slerp(startRot, Quaternion.LookRotation(root.forward), pull);
                if (hook && pull < 1) s.Stretch(cable, hook.position, vehicle.position + Vector3.up * .4f); else s.Stretch(cable, Vector3.zero, Vector3.zero);
            }
        }

        /// <summary>Aerial platform truck lifting its basket up to `work` (a sign on the roof); returns the basket.</summary>
        public Transform CherryPicker(Vector3 at, Vector3 forward, Vector3 work)
        {
            var root = Prop("Works_CherryPicker", at, forward);
            var lift = new Basket(root, work);
            machines.Add(lift);
            return lift.basket.t ? lift.basket.t : root;
        }

        class Basket : Machine
        {
            readonly Pose turret, arm1, arm2; public readonly Pose basket; readonly Vector3 work; readonly float yaw;
            public Basket(Transform r, Vector3 work)
            {
                root = r; this.work = work;
                Transform P(string n) => CheckoutWorksKit.FindPart(r, n);
                turret = new Pose(P("Turret")); arm1 = new Pose(P("Arm1")); arm2 = new Pose(P("Arm2")); basket = new Pose(P("Basket"));
                yaw = turret.t && arm2.t ? Vector3.SignedAngle(CheckoutWorksKit.Flat(arm2.t.position - turret.t.position), CheckoutWorksKit.Flat(work - turret.t.position), Vector3.up) : 0;
            }
            public override void Tick(CheckoutWorksScene s, float dt)
            {
                clock += dt;
                float bob = Mathf.Sin(clock * .3f) * 4;
                turret.Reset(); arm1.Reset(); arm2.Reset(); basket.Reset();
                turret.Turn(yaw, Vector3.up);
                var dir = arm2.t && turret.t ? CheckoutWorksKit.Flat(arm2.t.position - turret.t.position) : root.forward;
                var right = Vector3.Cross(Vector3.up, dir);
                arm1.Turn(-42 + bob, right); arm2.Turn(-25 - bob, right);
                // Keep the basket level: undo the two arm pitches.
                basket.Turn(67, right);
            }
        }

        /// <summary>A truck that drives in along `path`, waits, drives out again and comes back, over and over.</summary>
        public Transform Truck(string model, Vector3[] path, float wait = 8f)
        {
            var root = Prop(model, path[0], path.Length > 1 ? path[1] - path[0] : Vector3.forward);
            machines.Add(new Shuttle(root, path, wait));
            return root;
        }

        class Shuttle : Machine
        {
            readonly Vector3[] path; readonly float wait; readonly List<Transform> wheels = new List<Transform>(); readonly List<Quaternion> rest = new List<Quaternion>();
            float total; float spin;
            public Shuttle(Transform r, Vector3[] path, float wait)
            {
                root = r; this.path = path; this.wait = wait;
                for (int i = 0; i < 8; i++) { var w = CheckoutWorksKit.FindPart(r, "Wheel_" + i); if (w) { wheels.Add(w); rest.Add(w.localRotation); } }
                for (int i = 1; i < path.Length; i++) total += Vector3.Distance(path[i - 1], path[i]);
            }
            Vector3 At(float d, out Vector3 dir)
            {
                dir = Vector3.forward;
                for (int i = 1; i < path.Length; i++)
                {
                    float seg = Vector3.Distance(path[i - 1], path[i]);
                    dir = (path[i] - path[i - 1]).normalized;
                    if (d <= seg) return Vector3.Lerp(path[i - 1], path[i], seg < .001f ? 1 : d / seg);
                    d -= seg;
                }
                return path[path.Length - 1];
            }
            public override void Tick(CheckoutWorksScene s, float dt)
            {
                clock += dt;
                float drive = total / 3.2f, cycle = drive * 2 + wait * 2;
                float c = Mathf.Repeat(clock, cycle);
                float d; bool moving; bool backwards = false;
                if (c < drive) { d = total * Mathf.SmoothStep(0, 1, c / drive); moving = true; }
                else if (c < drive + wait) { d = total; moving = false; }
                else if (c < drive * 2 + wait) { d = total * (1 - Mathf.SmoothStep(0, 1, (c - drive - wait) / drive)); moving = true; backwards = true; }
                else { d = 0; moving = false; }
                var p = At(d, out var dir);
                root.position = p; root.rotation = Quaternion.LookRotation(dir);
                if (moving) spin += dt * 220 * (backwards ? -1 : 1);
                for (int i = 0; i < wheels.Count; i++) wheels[i].localRotation = rest[i] * Quaternion.Euler(spin, 0, 0);
                // Away (at the start of the path, out on the street): not shown until it drives in again.
                if (root.childCount > 0) root.GetChild(0).gameObject.SetActive(moving || d > .01f);
            }
        }

        // ---------------------------------------------------------------- cables
        public Transform Line(string name)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(go.GetComponent<Collider>());
            go.name = name; go.transform.SetParent(transform, false);
            if (!cableMat) { cableMat = art && art.cable ? art.cable : new Material(Shader.Find("Standard")) { color = new Color(.12f, .12f, .14f) }; }
            go.GetComponent<Renderer>().sharedMaterial = cableMat;
            go.transform.localScale = Vector3.zero;
            return go.transform;
        }

        public void Stretch(Transform line, Vector3 a, Vector3 b)
        {
            if (!line) return;
            float len = Vector3.Distance(a, b);
            if (len < .01f) { line.localScale = Vector3.zero; return; }
            line.position = (a + b) * .5f; line.rotation = Quaternion.LookRotation(b - a); line.localScale = new Vector3(.04f, .04f, len);
        }

        // ---------------------------------------------------------------- countdown pill
        /// <summary>A small floating countdown over the works; clicking it opens `route` (the shop page).</summary>
        public void Countdown(Vector3 at, string label, string route)
        {
            pill = new GameObject("Works countdown").transform; pill.SetParent(transform, false); pill.position = at;
            var face = GameObject.CreatePrimitive(PrimitiveType.Cube); face.name = "Pill"; face.transform.SetParent(pill, false);
            face.transform.localScale = new Vector3(3.4f, .9f, .08f);
            var m = new Material(Shader.Find("Standard")) { color = new Color(.11f, .17f, .33f) }; face.GetComponent<Renderer>().sharedMaterial = m;
            var bar = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(bar.GetComponent<Collider>()); bar.transform.SetParent(pill, false);
            bar.transform.localPosition = new Vector3(0, -.32f, -.05f); bar.transform.localScale = new Vector3(3.0f, .1f, .02f);
            bar.GetComponent<Renderer>().sharedMaterial = new Material(Shader.Find("Standard")) { color = new Color(.3f, .35f, .5f) };
            var fill = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(fill.GetComponent<Collider>()); fill.transform.SetParent(pill, false);
            fill.transform.localPosition = new Vector3(0, -.32f, -.07f); fill.transform.localScale = new Vector3(.01f, .1f, .02f);
            fill.GetComponent<Renderer>().sharedMaterial = new Material(Shader.Find("Standard")) { color = new Color(1f, .78f, .25f) };
            pillFill = fill.transform;
            var text = new GameObject("Text"); text.transform.SetParent(pill, false); text.transform.localPosition = new Vector3(0, .07f, -.06f);
            pillText = text.AddComponent<TextMeshPro>(); pillText.font = K.Headline; pillText.alignment = TextAlignmentOptions.Center;
            pillText.color = new Color(1f, .9f, .5f); pillText.rectTransform.sizeDelta = new Vector2(3.2f, .6f);
            pillText.enableAutoSizing = true; pillText.fontSizeMin = 1; pillText.fontSizeMax = 4;
            pillLabel = label; pillRoute = route;
            var click = face.GetComponent<BoxCollider>(); if (click) click.size = new Vector3(1.1f, 1.3f, 4f);
        }
        string pillLabel, pillRoute;

        public bool Clicked(Collider c) => pill && c && c.transform.IsChildOf(pill);
        public string Route => pillRoute;

        void Update()
        {
            float dt = Time.deltaTime, p = Progress;
            foreach (var step in progressItems) step(p);
            foreach (var m in machines) if (m.root) m.Tick(this, dt);
            Crew(dt);
            onProgress?.Invoke(this);
            if (pill)
            {
                var cam = Camera.main; if (cam) { var f = cam.transform.forward; f.y = 0; if (f.sqrMagnitude > .001f) pill.rotation = Quaternion.LookRotation(f.normalized); }
                if ((boardClock += dt) > .25f)
                {
                    boardClock = 0;
                    double left = endsAt - CheckoutConstructionSite.Now;
                    pillText.text = (string.IsNullOrEmpty(pillLabel) ? "" : pillLabel + "  ") + (left > 0 ? CheckoutConstructionSite.Countdown(left) : "PRONTO!");
                    pillFill.localScale = new Vector3(Mathf.Max(.01f, 3f * p), .1f, .02f);
                    pillFill.localPosition = new Vector3(-1.5f + 1.5f * p, -.32f, -.07f);
                }
            }
            if (Input.GetMouseButtonDown(0) && pill && !CheckoutBuildMode.Open)
            {
                if (UnityEngine.EventSystems.EventSystem.current && UnityEngine.EventSystems.EventSystem.current.IsPointerOverGameObject()) return;
                var cam = Camera.main; if (!cam) return;
                foreach (var hit in Physics.RaycastAll(cam.ScreenPointToRay(Input.mousePosition), 300))
                    if (Clicked(hit.collider)) { var host = FindAnyObjectByType<CheckoutDesktopHost>(); if (host && !string.IsNullOrEmpty(pillRoute)) host.Route(pillRoute); break; }
            }
        }
    }
}
