using UnityEngine;
using UnityEngine.Rendering;

namespace Checkout
{
    // Cheap, global render savings for phones, applied to whatever is in the scene (the city and the events spawn
    // their props at runtime, so it sweeps again now and then):
    //  - small props (a crate, a bottle, a bench leg) stop casting shadows: their shadows are a few pixels wide but
    //    each one is an extra draw in the shadow pass;
    //  - Mesh LOD (generated on import, CheckoutMeshLodTool): on phones each model is held at its first level under
    //    PhoneTriangles (the Tripo models came at 150-185k triangles each, the city drew ~38M a frame).
    public sealed class CheckoutMobilePerf : MonoBehaviour
    {
        const float SmallProp = .8f;      // largest side, metres
        const float SweepEvery = 15f;     // seconds

        const float BigPiece = 15f;       // metres
        const int PhoneTriangles = 12000; // per mesh: the Tripo models came at 150-185k each

        // Phone mode caps every model that has Mesh LODs at its first level under PhoneTriangles. On by default on
        // phones; F8 toggles it in the Editor and development builds to compare.
        // In the Editor the file Logs/phone_mode.flag containing "on" turns it on too (to measure the phone setup on the PC).
        public static bool Phone = Application.isMobilePlatform ||
            (Application.isEditor && EditorFlag());

        static bool EditorFlag()
        {
            try
            {
                string path = System.IO.Path.Combine(Application.dataPath, "..", "Logs", "phone_mode.flag");
                return System.IO.File.Exists(path) && System.IO.File.ReadAllText(path).Trim() == "on";
            }
            catch (System.Exception) { return false; }
        }
        float next;
        static int capped;
        static readonly System.Collections.Generic.Dictionary<Mesh, short> capFor = new System.Collections.Generic.Dictionary<Mesh, short>();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (FindAnyObjectByType<CheckoutMobilePerf>()) return;
            var go = new GameObject("Checkout mobile perf");
            DontDestroyOnLoad(go);
            go.AddComponent<CheckoutMobilePerf>();
            if (Application.isMobilePlatform) QualitySettings.meshLodThreshold = Mathf.Max(QualitySettings.meshLodThreshold, 1.5f);
        }

        void Start() { next = Time.unscaledTime + 2f; }

        void Update()
        {
            if ((Application.isEditor || Debug.isDebugBuild) && Input.GetKeyDown(KeyCode.F8))
            {
                Phone = !Phone;
                Debug.Log("CHECKOUT_PERF phone mode " + (Phone ? "on" : "off") + ": " + Sweep() + " renderers changed");
                return;
            }
            if (Time.unscaledTime < next) return;
            next = Time.unscaledTime + SweepEvery;
            int changed = Sweep();
            if (Debug.isDebugBuild && changed > 0) Debug.Log($"CHECKOUT_PERF sweep phone={Phone} changed={changed} capped meshes={capped}/{capFor.Count}");
        }

        public static int Sweep()
        {
            int changed = 0;
            foreach (var r in FindObjectsByType<MeshRenderer>(FindObjectsInactive.Exclude, FindObjectsSortMode.None))
            {
                if (r.TryGetComponent<MeshFilter>(out var filter) && filter.sharedMesh)
                {
                    // Very large pieces (the market shell, the ground) keep automatic selection: they fill the screen.
                    Vector3 extent = r.bounds.size;
                    bool big = Mathf.Max(extent.x, extent.z) > BigPiece;
                    short want = Phone && !big ? Cap(filter.sharedMesh) : (short)-1;
                    if (r.forceMeshLod != want) { r.forceMeshLod = want; changed++; }
                }
                if (r.shadowCastingMode != ShadowCastingMode.On) continue;
                Vector3 size = r.bounds.size;
                if (Mathf.Max(size.x, Mathf.Max(size.y, size.z)) >= SmallProp) continue;
                r.shadowCastingMode = ShadowCastingMode.Off;
                changed++;
            }
            return changed;
        }

        // The first LOD level at or under the phone budget (-1 = no LODs or already light: automatic selection).
        static short Cap(Mesh mesh)
        {
            if (capFor.TryGetValue(mesh, out var cached)) return cached;
            short level = -1;
            int levels = mesh.lodCount;
            if (levels > 1 && Triangles(mesh, 0) > PhoneTriangles)
            {
                level = (short)(levels - 1);
                for (int l = 1; l < levels; l++) if (Triangles(mesh, l) <= PhoneTriangles) { level = (short)l; break; }
            }
            capFor[mesh] = level;
            if (level >= 0) capped++;
            if (Debug.isDebugBuild && levels > 1) Debug.Log($"CHECKOUT_PERF lod cap {mesh.name}: {levels} levels, {Triangles(mesh, 0)} -> level {level} ({(level >= 0 ? Triangles(mesh, level) : 0)})");
            return level;
        }

        static int Triangles(Mesh mesh, int level)
        {
            int count = 0;
            for (int s = 0; s < mesh.subMeshCount; s++) count += (int)mesh.GetLod(s, level).indexCount / 3;
            return count;
        }
    }
}
