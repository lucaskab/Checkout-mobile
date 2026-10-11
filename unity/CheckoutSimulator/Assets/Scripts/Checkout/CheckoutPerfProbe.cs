using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using Unity.Profiling;
using UnityEngine;

namespace Checkout
{
    // Performance probe (Editor and development builds only). F9 records 20 s of play at the iPhone's quality level
    // (QualitySettings for iPhone = Medium) and writes Logs/perf_<time>.txt next to Assets: frame time (avg, p50, p95,
    // worst), main-thread time, GC memory allocated per frame, draw calls / SetPass / triangles / shadow casters, and
    // the time of the big Unity markers (scripts' Update and LateUpdate, rendering, UI canvases). The same numbers
    // before and after a change show what the change bought. CHECKOUT_PERF=1 in the environment starts one capture
    // 25 s after the game opens (for unattended runs).
    public sealed class CheckoutPerfProbe : MonoBehaviour
    {
        const float Seconds = 20f;
        const int IphoneQuality = 2;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (!Debug.isDebugBuild && !Application.isEditor) return;
            var go = new GameObject("CheckoutPerfProbe") { hideFlags = HideFlags.HideInHierarchy };
            DontDestroyOnLoad(go);
            go.AddComponent<CheckoutPerfProbe>();
        }

        bool running;

        void Start()
        {
            if (System.Environment.GetEnvironmentVariable("CHECKOUT_PERF") == "1") StartCoroutine(Delayed());
        }

        IEnumerator Delayed()
        {
            yield return new WaitForSecondsRealtime(25);
            if (!running) StartCoroutine(Capture());
        }

        void Update()
        {
            if (Input.GetKeyDown(KeyCode.F9) && !running) StartCoroutine(Capture());
        }

        static ProfilerRecorder Rec(ProfilerCategory category, string name) => ProfilerRecorder.StartNew(category, name, 1);

        IEnumerator Capture()
        {
            running = true;
            int previousQuality = QualitySettings.GetQualityLevel();
            QualitySettings.SetQualityLevel(IphoneQuality, true);
            Debug.Log("CHECKOUT_PERF capture started (" + Seconds + " s at quality " + QualitySettings.names[IphoneQuality] + ")");
            yield return new WaitForSecondsRealtime(1f);

            var recorders = new (string label, ProfilerRecorder rec, double scale, string unit)[]
            {
                ("Main thread", Rec(ProfilerCategory.Internal, "Main Thread"), 1e-6, "ms"),
                ("GC alloc / frame", Rec(ProfilerCategory.Memory, "GC Allocated In Frame"), 1.0 / 1024, "KB"),
                ("Batches (draw calls)", Rec(ProfilerCategory.Render, "Batches Count"), 1, ""),
                ("SetPass calls", Rec(ProfilerCategory.Render, "SetPass Calls Count"), 1, ""),
                ("Triangles", Rec(ProfilerCategory.Render, "Triangles Count"), 1e-3, "k"),
                ("Shadow casters", Rec(ProfilerCategory.Render, "Shadow Casters Count"), 1, ""),
                ("Scripts Update", Rec(ProfilerCategory.Scripts, "BehaviourUpdate"), 1e-6, "ms"),
                ("Scripts LateUpdate", Rec(ProfilerCategory.Scripts, "LateBehaviourUpdate"), 1e-6, "ms"),
                ("Coroutines", Rec(ProfilerCategory.Scripts, "CoroutinesDelayedCalls"), 1e-6, "ms"),
                ("Camera.Render", Rec(ProfilerCategory.Render, "Camera.Render"), 1e-6, "ms"),
                ("Shadows", Rec(ProfilerCategory.Render, "Shadows.RenderShadowMap"), 1e-6, "ms"),
                ("UI canvases", Rec(ProfilerCategory.Gui, "Canvas.SendWillRenderCanvases"), 1e-6, "ms"),
                ("UI batching", Rec(ProfilerCategory.Gui, "Canvas.BuildBatch"), 1e-6, "ms"),
                ("Animation", Rec(ProfilerCategory.Animation, "Animation.Update"), 1e-6, "ms"),
                ("Skinning", Rec(ProfilerCategory.Animation, "MeshSkinning.Update"), 1e-6, "ms"),
                ("Particles", Rec(ProfilerCategory.Particles, "ParticleSystem.Update"), 1e-6, "ms"),
                ("Physics", Rec(ProfilerCategory.Physics, "Physics.Processing"), 1e-6, "ms"),
                ("NavMesh", Rec(ProfilerCategory.Ai, "NavMeshManager"), 1e-6, "ms"),
            };
            var samples = recorders.Select(_ => new List<double>()).ToArray();
            // A few scripts known to be heavy, timed by name (Unity names script calls "<Type>.<Method>() [Invoke]").
            string[] scriptNames = { "CheckoutCityViews.LateUpdate() [Invoke]", "CheckoutDeliveryApp.Update() [Invoke]", "CheckoutCounterGame.Update() [Invoke]",
                "CheckoutStockroom.Update() [Invoke]", "CheckoutCourier.Update() [Invoke]", "CheckoutMap.Update() [Invoke]", "CheckoutBridge.Update() [Invoke]",
                "CheckoutDesktopHUD.Update() [Invoke]", "MarketCharacterAnimator.LateUpdate() [Invoke]", "MarketAmbientLife.Update() [Invoke]",
                "CheckoutI18nText.LateUpdate() [Invoke]", "CheckoutWalker.Update() [Invoke]", "CheckoutDesktopHost.Update() [Invoke]",
                "CheckoutIncidents.Update() [Invoke]", "CheckoutStaff.Update() [Invoke]", "CheckoutDancingFountain.Update() [Invoke]",
                "CheckoutStorageLife.Update() [Invoke]", "CheckoutCityTraffic.Update() [Invoke]", "CheckoutNeighborhoodTraffic.Update() [Invoke]",
                "CheckoutCityPedestrian.Update() [Invoke]", "CheckoutPlazaCyclists.LateUpdate() [Invoke]", "CheckoutEventVisuals.Update() [Invoke]",
                "CheckoutLotSites.LateUpdate() [Invoke]", "CheckoutStatusMarker.LateUpdate() [Invoke]", "CheckoutRequestBubble.LateUpdate() [Invoke]" };
            var scripts = scriptNames.Select(n => (name: n, rec: ProfilerRecorder.StartNew(ProfilerCategory.Scripts, n, 1))).ToArray();
            var scriptTotals = new double[scripts.Length];
            var scriptMax = new double[scripts.Length];
            var frames = new List<double>();
            int frameCount = 0;
            float end = Time.realtimeSinceStartup + Seconds;
            while (Time.realtimeSinceStartup < end)
            {
                yield return null;
                frames.Add(Time.unscaledDeltaTime * 1000.0);
                frameCount++;
                for (int i = 0; i < recorders.Length; i++)
                    if (recorders[i].rec.Valid) samples[i].Add(recorders[i].rec.LastValue * recorders[i].scale);
                for (int i = 0; i < scripts.Length; i++)
                    if (scripts[i].rec.Valid) { double ms = scripts[i].rec.LastValue * 1e-6; scriptTotals[i] += ms; if (ms > scriptMax[i]) scriptMax[i] = ms; }
            }

            var sb = new StringBuilder();
            sb.AppendLine($"Checkout perf capture {System.DateTime.Now:yyyy-MM-dd HH:mm:ss}  ({frameCount} frames, {Seconds} s, quality {QualitySettings.names[IphoneQuality]}, screen {Screen.width}x{Screen.height}, target fps {Application.targetFrameRate})");
            sb.AppendLine(Line("Frame time (ms)", frames));
            for (int i = 0; i < recorders.Length; i++)
            {
                sb.AppendLine(samples[i].ToArray().Length > 0 ? Line($"{recorders[i].label} ({recorders[i].unit})", samples[i]) : $"{recorders[i].label}: n/a");
                recorders[i].rec.Dispose();
            }
            sb.AppendLine();
            sb.AppendLine("Scripts by time (avg ms per frame / worst frame):");
            if (frameCount < 1) frameCount = 1;
            var order = new int[scriptTotals.Length];
            for (int k = 0; k < order.Length; k++) order[k] = k;
            System.Array.Sort(order, (a, b) => scriptTotals[b].CompareTo(scriptTotals[a]));
            for (int n = 0; n < order.Length && n < 30; n++)
            {
                int k = order[n];
                if (scriptTotals[k] > 0) sb.AppendLine("  " + (scriptTotals[k] / frameCount).ToString("0.000") + "  /  " + scriptMax[k].ToString("0.00") + "   " + scripts[k].name);
            }
            foreach (var s in scripts) s.rec.Dispose();
            sb.AppendLine();
            // Where the triangles come from: visible renderers grouped by mesh (instances x triangles).
            var groups = new Dictionary<string, (long tris, int count, int casters)>();
            foreach (var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None))
            {
                if (!r.enabled || !r.gameObject.activeInHierarchy || !r.isVisible) continue;
                Mesh mesh = r is SkinnedMeshRenderer sk ? sk.sharedMesh : r.TryGetComponent<MeshFilter>(out var mf) ? mf.sharedMesh : null;
                if (!mesh) continue;
                long tris = 0; for (int m = 0; m < mesh.subMeshCount; m++) tris += (long)mesh.GetIndexCount(m) / 3;
                string key = mesh.name + "  [" + r.gameObject.name + "]";
                groups.TryGetValue(key, out var g);
                groups[key] = (g.tris + tris, g.count + 1, g.casters + (r.shadowCastingMode != UnityEngine.Rendering.ShadowCastingMode.Off ? 1 : 0));
            }
            sb.AppendLine($"Visible triangles by mesh (total {groups.Values.Sum(g => g.tris) / 1000}k):");
            foreach (var pair in groups.OrderByDescending(p => p.Value.tris).Take(40))
                sb.AppendLine($"  {pair.Value.tris / 1000,8}k  x{pair.Value.count,-3} casters {pair.Value.casters,-3} {pair.Key}");
            sb.AppendLine();
            sb.AppendLine("Scene counts (active):");
            sb.AppendLine($"  GameObjects {FindObjectsByType<Transform>(FindObjectsSortMode.None).Length}");
            var renderers = FindObjectsByType<Renderer>(FindObjectsSortMode.None);
            sb.AppendLine($"  Renderers {renderers.Count(r => r.enabled && r.gameObject.activeInHierarchy)} (casting shadows {renderers.Count(r => r.enabled && r.gameObject.activeInHierarchy && r.shadowCastingMode != UnityEngine.Rendering.ShadowCastingMode.Off)})");
            sb.AppendLine($"  SkinnedMeshRenderers {FindObjectsByType<SkinnedMeshRenderer>(FindObjectsSortMode.None).Count(r => r.enabled)}");
            sb.AppendLine($"  Animation components {FindObjectsByType<Animation>(FindObjectsSortMode.None).Count(a => a.enabled)}");
            var lights = FindObjectsByType<Light>(FindObjectsSortMode.None);
            sb.AppendLine($"  Lights enabled {lights.Count(l => l.enabled && l.gameObject.activeInHierarchy)} of {lights.Length} (with shadows {lights.Count(l => l.enabled && l.gameObject.activeInHierarchy && l.shadows != LightShadows.None)})");
            var cams = FindObjectsByType<Camera>(FindObjectsSortMode.None).Where(c => c.enabled && c.gameObject.activeInHierarchy).ToArray();
            sb.AppendLine($"  Cameras enabled {cams.Length}: {string.Join(", ", cams.Select(c => c.name + (c.targetTexture ? " (RT " + c.targetTexture.width + ")" : "")))}");
            sb.AppendLine($"  ParticleSystems playing {FindObjectsByType<ParticleSystem>(FindObjectsSortMode.None).Count(p => p.isPlaying)}");
            sb.AppendLine($"  MonoBehaviours {FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None).Count(m => m.isActiveAndEnabled)}");
            sb.AppendLine($"  Canvases {FindObjectsByType<Canvas>(FindObjectsSortMode.None).Count(c => c.isActiveAndEnabled)}, TMP texts {FindObjectsByType<TMPro.TMP_Text>(FindObjectsSortMode.None).Count(t => t.isActiveAndEnabled)}");
            var top = FindObjectsByType<MonoBehaviour>(FindObjectsSortMode.None).Where(m => m.isActiveAndEnabled)
                .GroupBy(m => m.GetType().Name).OrderByDescending(g => g.Count()).Take(15);
            sb.AppendLine("  Most common scripts: " + string.Join(", ", top.Select(g => g.Key + " " + g.Count())));
            sb.AppendLine($"  Memory: total used {UnityEngine.Profiling.Profiler.GetTotalAllocatedMemoryLong() / 1048576} MB, managed heap {System.GC.GetTotalMemory(false) / 1048576} MB, textures {UnityEngine.Profiling.Profiler.GetAllocatedMemoryForGraphicsDriver() / 1048576} MB (driver)");

            var dir = Path.Combine(Path.GetDirectoryName(Application.dataPath) ?? ".", "Logs");
            Directory.CreateDirectory(dir);
            var file = Path.Combine(dir, $"perf_{System.DateTime.Now:yyyyMMdd_HHmmss}.txt");
            File.WriteAllText(file, sb.ToString());
            Debug.Log("CHECKOUT_PERF written " + file + "\n" + sb);
            QualitySettings.SetQualityLevel(previousQuality, true);
            running = false;
        }

        static string Line(string label, List<double> values)
        {
            var sorted = values.ToArray();
            if (sorted.Length == 0) return label + ": n/a";
            System.Array.Sort(sorted);
            double sum = 0; foreach (var v in sorted) sum += v;
            double P(double q) => sorted[Mathf.Clamp((int)(q * (sorted.Length - 1)), 0, sorted.Length - 1)];
            return label + ": avg " + (sum / sorted.Length).ToString("0.00") + "  p50 " + P(.5).ToString("0.00") + "  p95 " + P(.95).ToString("0.00") + "  max " + sorted[sorted.Length - 1].ToString("0.00");
        }
    }
}
