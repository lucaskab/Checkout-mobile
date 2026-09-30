using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    // ------------------------------------------------------------------ saved data
    // The map design made in "Modo edição" (CheckoutMapEditor). One entry per shop stage (0 = corner shop,
    // 4 = every wing bought). A stage without its own entry uses the closest lower one, so a design made
    // for stage 0 carries on until a later stage is designed. The file is Assets/Resources/CheckoutMapDesign.json
    // (read with Resources.Load in builds); standalone builds that edit the map keep their copy in persistentDataPath.

    // A piece of shop furniture: the game's own pieces ("shelf:dairy", "sector:padaria", ...) keep only their
    // spot; "design-N" pieces are extra furniture/decoration the designer added (template = Interior Kit child).
    [Serializable]
    public class DesignPiece
    {
        public string id, type, template;
        public float x, z, rot, scale = 1;
        public bool outside;
    }

    // Any object of the scene. With `path` it changes an object that is already in the map (moved, turned,
    // resized or hidden); with `source` it is a new copy of another object ("path:<scene path>") or of an
    // Interior Kit template ("kit:<name>").
    [Serializable]
    public class DesignObject
    {
        public string id, path, source;
        // Copies made together (all the parts of one bench, lamp, garden...) share a group: one item.
        public string group;
        public Vector3 position, euler, scale = Vector3.one;
        public bool hidden;
    }

    [Serializable]
    public class DesignStage
    {
        public int stage;
        public DesignPiece[] interior = new DesignPiece[0];
        public DesignObject[] objects = new DesignObject[0];
        // Painted ground: "x,z,ground,mark;..." on the 1 m map grid (CheckoutPaintLayer kinds).
        public string paint = "";
        public DesignStage Clone() => JsonUtility.FromJson<DesignStage>(JsonUtility.ToJson(this));
    }

    [Serializable]
    public class DesignFile
    {
        public int version = 1;
        public DesignStage[] stages = new DesignStage[0];
    }

    public static class CheckoutMapDesign
    {
        public const int Stages = 5;
        public const string ResourceName = "CheckoutMapDesign";
        static DesignFile file;
        public static event Action Changed;

        static string EditorPath => Path.Combine(Application.dataPath, "Resources", ResourceName + ".json");
        static string PlayerPath => Path.Combine(Application.persistentDataPath, ResourceName + ".json");
        public static string SavePath => Application.isEditor ? EditorPath : PlayerPath;

        public static DesignFile File { get { if (file == null) Load(); return file; } }

        public static void Load()
        {
            string json = null;
            try
            {
                if (Application.isEditor) { if (System.IO.File.Exists(EditorPath)) json = System.IO.File.ReadAllText(EditorPath); }
                else if (System.IO.File.Exists(PlayerPath)) json = System.IO.File.ReadAllText(PlayerPath);
                if (json == null) { var asset = Resources.Load<TextAsset>(ResourceName); if (asset) json = asset.text; }
                file = string.IsNullOrWhiteSpace(json) ? new DesignFile() : JsonUtility.FromJson<DesignFile>(json) ?? new DesignFile();
            }
            catch (Exception ex) { Debug.LogError("CHECKOUT_DESIGN could not read the map design: " + ex.Message); file = new DesignFile(); }
            if (file.stages == null) file.stages = new DesignStage[0];
            foreach (var s in file.stages) Normalize(s);
        }

        static void Normalize(DesignStage s)
        {
            if (s == null) return;
            if (s.interior == null) s.interior = new DesignPiece[0];
            if (s.objects == null) s.objects = new DesignObject[0];
            if (s.paint == null) s.paint = "";
            foreach (var p in s.interior) if (p != null && p.scale <= 0) p.scale = 1;
            foreach (var o in s.objects) if (o != null && o.scale == Vector3.zero) o.scale = Vector3.one;
        }

        public static bool Save(out string error)
        {
            error = null;
            try
            {
                var path = SavePath;
                Directory.CreateDirectory(Path.GetDirectoryName(path));
                File.stages = File.stages.Where(s => s != null).OrderBy(s => s.stage).ToArray();
                var json = JsonUtility.ToJson(File, true);
                System.IO.File.WriteAllText(path + ".tmp", json);
                if (System.IO.File.Exists(path)) System.IO.File.Delete(path);
                System.IO.File.Move(path + ".tmp", path);
#if UNITY_EDITOR
                UnityEditor.AssetDatabase.ImportAsset("Assets/Resources/" + ResourceName + ".json");
#endif
                Changed?.Invoke();
                return true;
            }
            catch (Exception ex) { error = ex.Message; Debug.LogError("CHECKOUT_DESIGN could not save: " + ex.Message); return false; }
        }

        // The design used at this stage: its own entry, or the closest lower stage that has one.
        public static DesignStage For(int stage)
        {
            DesignStage best = null;
            foreach (var s in File.stages) if (s != null && s.stage <= stage && (best == null || s.stage > best.stage)) best = s;
            return best;
        }
        public static bool Explicit(int stage) => File.stages.Any(s => s != null && s.stage == stage);
        public static int SourceStage(int stage) => For(stage)?.stage ?? -1;

        public static void Set(int stage, DesignStage value)
        {
            value = value.Clone(); value.stage = stage; Normalize(value);
            var list = File.stages.Where(s => s != null && s.stage != stage).ToList();
            list.Add(value);
            File.stages = list.OrderBy(s => s.stage).ToArray();
        }
        public static void Clear(int stage) => File.stages = File.stages.Where(s => s != null && s.stage != stage).ToArray();

        // The shop the game would show at this stage (src/services/simulator-layout.ts), used by the editor to
        // preview every stage without buying anything.
        public static MarketLayout LayoutFor(int stage, bool warehouse)
        {
            stage = Mathf.Clamp(stage, 0, Stages - 1);
            float[,] sizes = { { .82f, .72f }, { .96f, .82f }, { 1.1f, .92f }, { 1.24f, 1.03f }, { 1.38f, 1.14f } };
            var ids = new[] { "fresh-wing", "service-wing", "stock-annex", "premium-hall" }.Take(stage).ToList();
            var sectors = new List<string> { "padaria" };
            if (ids.Contains("fresh-wing")) sectors.Add("queijaria");
            if (ids.Contains("service-wing")) sectors.Add("acougue");
            if (ids.Contains("stock-annex")) sectors.Add("peixaria");
            if (ids.Contains("service-wing")) sectors.Add("bebidas");
            if (ids.Contains("premium-hall")) sectors.Add("sorvetes");
            if (warehouse) sectors.Add("adega");
            return new MarketLayout
            {
                stage = stage, widthScale = sizes[stage, 0], depthScale = sizes[stage, 1],
                storage = ids.Contains("fresh-wing") || warehouse, parking = ids.Contains("service-wing"),
                loadingYard = ids.Contains("stock-annex"), premium = ids.Contains("premium-hall"), storageLarge = warehouse,
                sectorIds = sectors.ToArray(),
            };
        }

        public static string StageName(int stage) => "Loja " + (stage + 1);

        // ------------------------------------------------------------------ scene paths
        // "Root/Child/Grandchild"; siblings sharing a name get "#n" (n-th of that name).
        public static string PathOf(Transform t)
        {
            if (!t) return null;
            var parts = new List<string>();
            while (t)
            {
                int index = 0, count = 0;
                IEnumerable<Transform> siblings = t.parent ? t.parent.Cast<Transform>() : t.gameObject.scene.GetRootGameObjects().Select(g => g.transform);
                foreach (var s in siblings) if (s.name == t.name) { if (s == t) index = count; count++; }
                parts.Add(count > 1 ? t.name + "#" + index : t.name);
                t = t.parent;
            }
            parts.Reverse();
            return string.Join("/", parts);
        }

        public static Transform Find(string path)
        {
            if (string.IsNullOrEmpty(path)) return null;
            var parts = path.Split('/');
            Transform current = null;
            for (int i = 0; i < parts.Length; i++)
            {
                string name = parts[i]; int index = 0;
                int hash = name.LastIndexOf('#');
                if (hash > 0 && int.TryParse(name.Substring(hash + 1), out var n)) { name = name.Substring(0, hash); index = n; }
                IEnumerable<Transform> pool = current ? current.Cast<Transform>() : UnityEngine.SceneManagement.SceneManager.GetActiveScene().GetRootGameObjects().Select(g => g.transform);
                current = pool.Where(c => c.name == name).Skip(index).FirstOrDefault();
                if (!current) return null;
            }
            return current;
        }
    }

    // ------------------------------------------------------------------ the design in the scene
    // Moves, hides and adds scene objects and paints the ground as the design says. Objects keep their
    // original pose so the design can be switched (stage change, editor undo) without drift.
    public class CheckoutDesignWorld : MonoBehaviour
    {
        public static CheckoutDesignWorld Active { get; private set; }
        class Baseline { public Vector3 position, scale; public Quaternion rotation; public bool[] rendering; public bool[] colliders; }
        readonly Dictionary<Transform, Baseline> baselines = new Dictionary<Transform, Baseline>();
        readonly Dictionary<string, DesignObject> overrides = new Dictionary<string, DesignObject>();
        readonly Dictionary<string, (DesignObject data, Transform root)> clones = new Dictionary<string, (DesignObject, Transform)>();
        Transform cloneRoot, staging, world;
        public CheckoutPaintLayer Paint { get; private set; }
        public int AppliedStage { get; private set; } = -99;
        float reapply;

        public void Initialize(Transform worldRoot)
        {
            Active = this; world = worldRoot;
            cloneRoot = new GameObject("Map Design Objects").transform;
            staging = new GameObject("Map Design Staging").transform; staging.gameObject.SetActive(false);
            Paint = new GameObject("Map Design Paint").AddComponent<CheckoutPaintLayer>();
        }

        void OnDestroy() { if (Active == this) Active = null; }

        public Transform CloneRoot => cloneRoot;
        public IEnumerable<DesignObject> Overrides => overrides.Values;
        public IEnumerable<(DesignObject data, Transform root)> Clones => clones.Values;
        public bool IsClone(Transform t, out DesignObject data)
        {
            foreach (var c in clones.Values) if (c.root == t) { data = c.data; return true; }
            data = null; return false;
        }
        public DesignObject OverrideOf(string path) => path != null && overrides.TryGetValue(path, out var o) ? o : null;

        // The game follows the design of the stage it shows (the editor drives this itself while open).
        public bool Sync(int stage, bool force = false)
        {
            if (!force && stage == AppliedStage) return false;
            ApplyStage(CheckoutMapDesign.For(stage), stage);
            AppliedStage = stage;
            CheckoutBlockPaths.Invalidate();
            return true;
        }

        // `stage`: the stage shown. A design inherited from a smaller shop never puts objects inside the bigger
        // shop's walls (those stay where the game has them until that stage gets its own design).
        public void ApplyStage(DesignStage d, int stage = -1)
        {
            RevertAll();
            if (d != null)
            {
                Rect? shop = null;
                if (stage > d.stage && CheckoutInterior.Active) { var f = CheckoutInterior.Active.FloorRect; shop = Rect.MinMaxRect(f.xMin - .6f, f.yMin - 1.4f, f.xMax + .6f, f.yMax + .6f); }
                bool Inside(Vector3 p) => shop.HasValue && shop.Value.Contains(new Vector2(p.x, p.z));
                foreach (var o in d.objects.Where(o => o != null && !string.IsNullOrEmpty(o.path)).OrderBy(o => o.path.Count(ch => ch == '/')))
                    if (!Inside(o.position) || o.hidden) SetOverride(o);
                foreach (var o in d.objects.Where(o => o != null && string.IsNullOrEmpty(o.path) && !string.IsNullOrEmpty(o.source)))
                    if (!Inside(o.position)) AddClone(o);
            }
            Paint.Load(d?.paint);
        }

        public void RevertAll()
        {
            foreach (var path in overrides.Keys.ToArray()) RemoveOverride(path);
            foreach (var id in clones.Keys.ToArray()) RemoveClone(id);
            overrides.Clear();
        }

        // ---------------------------------------------------------------- overrides of existing objects
        public void SetOverride(DesignObject o)
        {
            var t = CheckoutMapDesign.Find(o.path);
            if (!t) { overrides[o.path] = o; return; } // kept: the object may exist at another stage
            if (!baselines.ContainsKey(t)) baselines[t] = Capture(t);
            overrides[o.path] = o;
            Pose(t, o);
        }

        static Baseline Capture(Transform t) => new Baseline
        {
            position = t.position, rotation = t.rotation, scale = t.localScale,
            rendering = t.GetComponentsInChildren<Renderer>(true).Select(r => r.forceRenderingOff).ToArray(),
            colliders = t.GetComponentsInChildren<Collider>(true).Select(c => c.enabled).ToArray(),
        };

        static void Pose(Transform t, DesignObject o)
        {
            t.SetPositionAndRotation(o.position, Quaternion.Euler(o.euler));
            t.localScale = o.scale;
            foreach (var r in t.GetComponentsInChildren<Renderer>(true)) if (o.hidden) r.forceRenderingOff = true;
            if (o.hidden) foreach (var c in t.GetComponentsInChildren<Collider>(true)) c.enabled = false;
        }

        public void RemoveOverride(string path)
        {
            overrides.Remove(path);
            var t = CheckoutMapDesign.Find(path);
            if (!t || !baselines.TryGetValue(t, out var b)) return;
            t.SetPositionAndRotation(b.position, b.rotation); t.localScale = b.scale;
            var rs = t.GetComponentsInChildren<Renderer>(true); for (int i = 0; i < rs.Length && i < b.rendering.Length; i++) rs[i].forceRenderingOff = b.rendering[i];
            var cs = t.GetComponentsInChildren<Collider>(true); for (int i = 0; i < cs.Length && i < b.colliders.Length; i++) cs[i].enabled = b.colliders[i];
            baselines.Remove(t);
        }

        // Remembers the object's own pose before the editor changes it for the first time.
        public void Touch(Transform t) { if (t && !baselines.ContainsKey(t)) baselines[t] = Capture(t); }

        // The pose an object had before the design touched it (editor "Resetar").
        public bool Original(Transform t, out Vector3 position, out Quaternion rotation, out Vector3 scale)
        {
            if (baselines.TryGetValue(t, out var b)) { position = b.position; rotation = b.rotation; scale = b.scale; return true; }
            position = t.position; rotation = t.rotation; scale = t.localScale; return false;
        }

        // ---------------------------------------------------------------- new objects
        public Transform AddClone(DesignObject o)
        {
            if (string.IsNullOrEmpty(o.id)) { int n = 1; while (clones.ContainsKey("obj-" + n)) n++; o.id = "obj-" + n; }
            if (clones.TryGetValue(o.id, out var existing)) { if (existing.root) Destroy(existing.root.gameObject); clones.Remove(o.id); }
            var source = Source(o.source);
            if (!source) { Debug.LogWarning("CHECKOUT_DESIGN missing source " + o.source); return null; }
            // Copied inside an inactive parent so none of the source's behaviours wake up on the copy.
            var go = Instantiate(source.gameObject, staging);
            go.name = "Design " + o.id + " (" + source.name + ")";
            // Only the bench seat marker stays, so people can sit on copied benches too.
            foreach (var mb in go.GetComponentsInChildren<MonoBehaviour>(true)) if (!(mb is CheckoutBenchSeat)) DestroyImmediate(mb);
            foreach (var c in go.GetComponentsInChildren<Collider>(true)) DestroyImmediate(c);
            foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.forceRenderingOff = false;
            foreach (var a in go.GetComponentsInChildren<Animator>(true)) DestroyImmediate(a);
            go.transform.SetParent(cloneRoot, true);
            go.SetActive(true);
            go.transform.SetPositionAndRotation(o.position, Quaternion.Euler(o.euler)); go.transform.localScale = o.scale;
            if (o.hidden) foreach (var r in go.GetComponentsInChildren<Renderer>(true)) r.forceRenderingOff = true;
            clones[o.id] = (o, go.transform);
            return go.transform;
        }

        public Transform Source(string source)
        {
            if (string.IsNullOrEmpty(source)) return null;
            if (source.StartsWith("kit:")) return world ? world.Find("Interior Kit/" + source.Substring(4)) : null;
            if (source.StartsWith("path:")) return CheckoutMapDesign.Find(source.Substring(5));
            return null;
        }

        public void UpdateClone(Transform t)
        {
            foreach (var c in clones.Values)
                if (c.root == t) { c.data.position = t.position; c.data.euler = t.eulerAngles; c.data.scale = t.localScale; return; }
        }

        public void RemoveClone(string id)
        {
            if (!clones.TryGetValue(id, out var c)) return;
            if (c.root) Destroy(c.root.gameObject);
            clones.Remove(id);
        }

        // Everything the design currently changes, as saved data.
        public DesignObject[] CaptureObjects()
        {
            var list = new List<DesignObject>();
            foreach (var o in overrides.Values) list.Add(new DesignObject { path = o.path, position = o.position, euler = o.euler, scale = o.scale, hidden = o.hidden });
            foreach (var c in clones.Values)
            {
                if (c.root) { c.data.position = c.root.position; c.data.euler = c.root.eulerAngles; c.data.scale = c.root.localScale; }
                list.Add(new DesignObject { id = c.data.id, source = c.data.source, group = c.data.group, position = c.data.position, euler = c.data.euler, scale = c.data.scale, hidden = c.data.hidden });
            }
            return list.ToArray();
        }

        // Solid boxes (centre, size, yaw) of what the design moved or added outside the shop, so the people of
        // the city walk round them (MarketSimulation bakes them into the navigation).
        public IEnumerable<(Vector3 center, Vector3 size, float yaw)> Obstacles()
        {
            var shop = CheckoutInterior.Active ? CheckoutInterior.Active.FloorRect : new Rect();
            var roots = new List<Transform>();
            foreach (var o in overrides.Values) if (!o.hidden) { var t = CheckoutMapDesign.Find(o.path); if (t) roots.Add(t); }
            foreach (var c in clones.Values) if (c.root && !c.data.hidden) roots.Add(c.root);
            foreach (var t in roots)
                foreach (var r in t.GetComponentsInChildren<MeshRenderer>())
                {
                    if (!r.enabled || r.forceRenderingOff) continue;
                    var b = r.bounds;
                    if (b.size.y < .12f || b.min.y > 1.1f || b.size.x * b.size.z > 40f) continue;
                    if (shop.Contains(new Vector2(b.center.x, b.center.z))) continue;
                    if (b.size.y > 2.5f && b.size.x < 3 && b.size.z < 3) { yield return (new Vector3(b.center.x, 1.5f, b.center.z), new Vector3(.6f, 3, .6f), 0); continue; } // trunks, poles
                    yield return (new Vector3(b.center.x, 1.5f, b.center.z), new Vector3(b.size.x + .1f, 3, b.size.z + .1f), 0);
                }
        }

        // Other systems (stage growth animations, layout projection) may put a moved object back: keep it
        // where the design wants it.
        void LateUpdate()
        {
            reapply -= Time.unscaledDeltaTime;
            if (reapply > 0 || CheckoutMapEditor.Dragging) return;
            reapply = 1.5f;
            foreach (var o in overrides.Values)
            {
                var t = CheckoutMapDesign.Find(o.path);
                if (!t) continue;
                if (!baselines.ContainsKey(t)) baselines[t] = Capture(t);
                if ((t.position - o.position).sqrMagnitude > 1e-6f || Quaternion.Angle(t.rotation, Quaternion.Euler(o.euler)) > .05f || (t.localScale - o.scale).sqrMagnitude > 1e-6f)
                    Pose(t, o);
            }
        }
    }
}
