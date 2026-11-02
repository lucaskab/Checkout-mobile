using System;
using System.Collections.Generic;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout
{
    // A piece the evolution crew is working on (src/data/fixture-evolution.ts; claude/evolucoes-recompensas.md): the
    // piece keeps its old look and keeps selling, a builder from the works crew kneels in front of it with his toolbox
    // and hammers away (sparks at every blow, a little dust), and a navy ring with a gold rim floats over it with the
    // time left. A tap on the ring offers the diamond skip on a gold plate under it ("TERMINAR JÁ"); a second tap on
    // the plate spends the diamonds. Queued evolutions show the ring dimmed with "NA FILA" and no builder yet.
    // Everything is a few primitives and one generated mesh: cheap on an iPhone.
    public class CheckoutEvolutionSite : MonoBehaviour
    {
        public string EvolutionId { get; private set; }
        Evolution data; CheckoutInterior.Item item;
        CheckoutWorksScene crew; Transform ring, plate; MeshFilter arc; TextMeshPro timeText, tagText, plateText;
        Material navy, gold, track, arcMat, dim; readonly List<Material> owned = new List<Material>();
        float shownProgress = -1, refresh, plateUntil; bool crewQueued;
        static readonly Dictionary<string, CheckoutEvolutionSite> byEvolution = new Dictionary<string, CheckoutEvolutionSite>();
        static long Now => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        const float R = .78f;

        public static CheckoutEvolutionSite Show(CheckoutInterior.Item it, Evolution evolution)
        {
            if (it?.root == null || evolution == null) return null;
            var site = it.root.GetComponent<CheckoutEvolutionSite>();
            if (!site) { site = it.root.gameObject.AddComponent<CheckoutEvolutionSite>(); site.item = it; site.Build(); }
            site.Refresh(evolution);
            return site;
        }

        public static void Finish(CheckoutInterior.Item it)
        {
            var site = it?.root ? it.root.GetComponent<CheckoutEvolutionSite>() : null;
            if (site) Destroy(site);
        }

        /// <summary>The ring was tapped: show (or hide) the diamond skip under it.</summary>
        public static void Tapped(string evolutionId)
        {
            if (!byEvolution.TryGetValue(evolutionId ?? "", out var site) || !site) return;
            site.plateUntil = site.plateUntil > Time.unscaledTime ? 0 : Time.unscaledTime + 5f;
            site.UpdateRing(true);
            if (site.ring) site.StartCoroutine(Bump(site.ring));
        }

        public static bool Has(string evolutionId) => byEvolution.TryGetValue(evolutionId ?? "", out var s) && s;
        /// <summary>QA: the ring of a piece (to aim the camera and the taps).</summary>
        public Transform Ring => ring;
        public Transform Plate => plate;
        public bool PlateOpen => plate && plate.gameObject.activeSelf;

        void Refresh(Evolution evolution)
        {
            if (!string.IsNullOrEmpty(EvolutionId) && EvolutionId != evolution.id) byEvolution.Remove(EvolutionId);
            data = evolution; EvolutionId = evolution.id; byEvolution[EvolutionId] = this;
            foreach (var t in GetComponentsInChildren<CheckoutTarget>(true)) if (t.panel == "evolution" || t.panel == "finishEvolution") t.requestId = EvolutionId;
            bool queued = evolution.queued && Now < evolution.startedAt;
            if (crew) crew.SetTimes(evolution.startedAt, evolution.endsAt);
            if (queued != crewQueued || (!queued && !crew)) { crewQueued = queued; SetCrew(!queued); }
            UpdateRing(true);
        }

        // ---------------------------------------------------------------- set up
        Material Mat(string hex, float gloss = .2f, bool unlit = false)
        {
            var m = new Material(Shader.Find(unlit ? "Unlit/Color" : "Standard"));
            ColorUtility.TryParseHtmlString("#" + hex, out var c); m.color = c;
            if (!unlit) m.SetFloat("_Glossiness", gloss);
            owned.Add(m); return m;
        }

        Bounds PieceBounds()
        {
            // In the piece's own (unscaled) frame: item.root carries the map editor's scale.
            var p = item.piece;
            var min = p ? p.min : new Vector2(-.9f, -.4f); var max = p ? p.max : new Vector2(.9f, .4f);
            float h = p ? Mathf.Max(1.2f, p.markerHeight) : 2f;
            return new Bounds(new Vector3((min.x + max.x) * .5f, h * .5f, (min.y + max.y) * .5f), new Vector3(max.x - min.x, h, max.y - min.y));
        }

        void Build()
        {
            // Unlit: the ring keeps the market's navy and gold whatever the light (lit, the navy read as grey).
            navy = Mat("1D2B4F", 0, true); gold = Mat("E0B040", 0, true); track = Mat("0B1328", 0, true);
            arcMat = Mat("F2C84B", 0, true); dim = Mat("3A4566", 0, true);
            var b = PieceBounds();
            // The ring floats over the piece (always the same size on the screen: it faces the camera).
            ring = new GameObject("Evolution ring").transform; ring.SetParent(transform, false);
            ring.localScale = Vector3.one / Mathf.Max(.2f, item.scale);
            // over the piece and over the builder's head (with room for the skip plate under the ring)
            ring.localPosition = new Vector3(b.center.x, Mathf.Max(b.size.y, 1.9f) + 2.0f / Mathf.Max(.2f, item.scale), b.center.z);
            Disc(ring, "Rim", R + .13f, .05f, gold, .06f);
            Disc(ring, "Face", R, .02f, navy, .0f);
            Annulus(ring, "Track", R * .72f, R * .9f, track, -.035f);
            arc = Annulus(ring, "Progress", R * .72f, R * .9f, arcMat, -.04f).GetComponent<MeshFilter>();
            timeText = Label(ring, new Vector3(0, -.02f, -.06f), new Vector2(1.1f, .5f), 3.2f, new Color(1f, .93f, .62f));
            tagText = Label(ring, new Vector3(0, .3f, -.06f), new Vector2(1.0f, .22f), 1.4f, new Color(.85f, .9f, 1f));
            var hit = ring.gameObject.AddComponent<SphereCollider>(); hit.radius = R + .2f;
            var target = ring.gameObject.AddComponent<CheckoutTarget>(); target.panel = "evolution";
            // The skip plate (hidden until the ring is tapped).
            plate = new GameObject("Skip plate").transform; plate.SetParent(ring, false); plate.localPosition = new Vector3(0, -R - .5f, 0);
            Box(plate, "Edge", new Vector3(0, 0, .02f), new Vector3(2.1f, .56f, .06f), navy);
            Box(plate, "Face", new Vector3(0, 0, -.01f), new Vector3(1.98f, .46f, .06f), gold);
            var gem = Box(plate, "Diamond", new Vector3(.72f, 0, -.05f), new Vector3(.22f, .22f, .06f), Mat("59D9FF", .9f));
            gem.localRotation = Quaternion.Euler(0, 0, 45);
            plateText = Label(plate, new Vector3(-.14f, 0, -.06f), new Vector2(1.5f, .4f), 2.2f, new Color(.08f, .12f, .24f));
            var pc = plate.gameObject.AddComponent<BoxCollider>(); pc.size = new Vector3(2.15f, .6f, .3f);
            var pt = plate.gameObject.AddComponent<CheckoutTarget>(); pt.panel = "finishEvolution";
            plate.gameObject.SetActive(false);
        }

        void SetCrew(bool on)
        {
            if (crew) { Destroy(crew.gameObject); crew = null; }
            if (!on || item?.root == null) return;
            var b = PieceBounds();
            // In front of the piece, on the customers' side (-Z), a bit off centre, facing it; the toolbox by his side.
            Vector3 W(float x, float z) => item.root.TransformPoint(new Vector3(x, 0, z));
            float s = Mathf.Max(.2f, item.scale);
            var front = b.min.z - .55f / s;
            var spot = W(b.center.x + b.extents.x * .35f, front);
            var look = W(b.center.x + b.extents.x * .35f, b.center.z);
            crew = CheckoutWorksScene.Create("Evolution crew", data.startedAt, data.endsAt);
            crew.transform.SetParent(transform, true);
            crew.ToolWorker(spot, look, CheckoutWorksScene.Tool.Hammer, Mathf.Abs(item.id.GetHashCode()) % 4);
            var side = item.root.TransformDirection(Vector3.right);
            crew.Prop("Prop_Toolbox", spot - side * .55f, item.root.TransformDirection(Vector3.back));
            var c = crew;
            int blows = 0;
            crew.Blow += at => { if (!c) return; c.Sparks(at, UnityEngine.Random.Range(6, 11)); if (++blows % 3 == 0) c.Burst(at + Vector3.down * .3f, 2); };
        }

        static Transform Box(Transform parent, string name, Vector3 local, Vector3 size, Material m)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube); go.name = name; Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false); go.transform.localPosition = local; go.transform.localScale = size;
            var r = go.GetComponent<Renderer>(); r.sharedMaterial = m; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return go.transform;
        }

        // A flat disc facing -Z (towards the camera once the ring is turned to it), `thick` deep.
        static void Disc(Transform parent, string name, float radius, float thick, Material m, float z)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cylinder); go.name = name; Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false); go.transform.localPosition = new Vector3(0, 0, z);
            go.transform.localRotation = Quaternion.Euler(90, 0, 0); go.transform.localScale = new Vector3(radius * 2, thick, radius * 2);
            var r = go.GetComponent<Renderer>(); r.sharedMaterial = m; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
        }

        static Transform Annulus(Transform parent, string name, float inner, float outer, Material m, float z)
        {
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(parent, false); go.transform.localPosition = new Vector3(0, 0, z);
            go.GetComponent<MeshFilter>().sharedMesh = Arc(inner, outer, 1);
            var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = m; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return go.transform;
        }

        // The part [0, fill] of a ring, clockwise from 12 o'clock, in the XY plane facing -Z.
        static Mesh Arc(float inner, float outer, float fill)
        {
            int n = Mathf.Max(2, Mathf.CeilToInt(64 * Mathf.Clamp01(fill)) + 1);
            var v = new Vector3[n * 2]; var t = new int[(n - 1) * 6];
            for (int i = 0; i < n; i++)
            {
                float a = Mathf.PI * .5f - Mathf.Clamp01(fill) * Mathf.PI * 2 * i / (n - 1);
                var d = new Vector3(Mathf.Cos(a), Mathf.Sin(a), 0);
                v[i * 2] = d * inner; v[i * 2 + 1] = d * outer;
                if (i < n - 1) { int k = i * 6, j = i * 2; t[k] = j; t[k + 1] = j + 1; t[k + 2] = j + 3; t[k + 3] = j; t[k + 4] = j + 3; t[k + 5] = j + 2; }
            }
            var mesh = new Mesh { name = "Evolution arc", vertices = v, triangles = t }; mesh.RecalculateNormals(); mesh.RecalculateBounds();
            return mesh;
        }

        static TextMeshPro Label(Transform parent, Vector3 local, Vector2 size, float max, Color color)
        {
            var go = new GameObject("Text"); go.transform.SetParent(parent, false); go.transform.localPosition = local;
            var t = go.AddComponent<TextMeshPro>(); CheckoutI18nText.Register(t);
            t.font = K.Headline; t.alignment = TextAlignmentOptions.Center; t.color = color;
            t.rectTransform.sizeDelta = size; t.enableAutoSizing = true; t.fontSizeMin = .5f; t.fontSizeMax = max;
            t.textWrappingMode = TextWrappingModes.NoWrap; t.outlineWidth = .12f; t.outlineColor = new Color32(10, 16, 36, 220);
            return t;
        }

        static System.Collections.IEnumerator Bump(Transform t)
        {
            var full = t.localScale;
            for (float k = 0; k < 1; k += Time.unscaledDeltaTime / .25f) { if (!t) yield break; t.localScale = full * (1 + .12f * Mathf.Sin(k * Mathf.PI)); yield return null; }
            if (t) t.localScale = full;
        }

        // ---------------------------------------------------------------- every frame
        void Update()
        {
            if (!ring) return;
            var cam = Camera.main; if (cam) ring.rotation = cam.transform.rotation;
            // A gentle bob, so the eye finds it.
            ring.localPosition = new Vector3(ring.localPosition.x, BaseY + .06f * Mathf.Sin(Time.time * 2.2f), ring.localPosition.z);
            UpdateRing(false);
        }
        float baseY = float.NaN;
        float BaseY { get { if (float.IsNaN(baseY) && ring) baseY = ring.localPosition.y; return baseY; } }

        void UpdateRing(bool force)
        {
            if (!ring || data == null) return;
            refresh -= Time.unscaledDeltaTime;
            if (!force && refresh > 0) return;
            refresh = .2f;
            long now = Now;
            bool queued = now < data.startedAt;
            if (queued != crewQueued) { crewQueued = queued; SetCrew(!queued); }
            double left = queued ? data.durationMs : Math.Max(0, data.endsAt - now);
            float p = queued || data.durationMs <= 0 ? 0 : Mathf.Clamp01((float)(1 - left / data.durationMs));
            if (Mathf.Abs(p - shownProgress) > .002f) { shownProgress = p; arc.sharedMesh = Arc(R * .72f, R * .9f, Mathf.Max(.005f, p)); }
            timeText.text = left > 0 ? CheckoutConstructionSite.Countdown(left) : "...";
            tagText.text = queued ? "NA FILA" : "EVOLUINDO";
            var face = ring.Find("Face"); if (face) face.GetComponent<Renderer>().sharedMaterial = queued ? dim : navy;
            int cost = left <= 0 ? 0 : CheckoutSkipPrice.Cost(left);
            bool showPlate = cost > 0 && plateUntil > Time.unscaledTime && !CheckoutSocial.Visiting;
            if (plate.gameObject.activeSelf != showPlate) plate.gameObject.SetActive(showPlate);
            plateText.text = "TERMINAR JÁ  " + cost;
        }

        void OnDestroy()
        {
            if (!string.IsNullOrEmpty(EvolutionId) && byEvolution.TryGetValue(EvolutionId, out var s) && s == this) byEvolution.Remove(EvolutionId);
            if (crew) Destroy(crew.gameObject);
            if (ring) Destroy(ring.gameObject);
            if (arc && arc.sharedMesh) Destroy(arc.sharedMesh);
            foreach (var m in owned) if (m) Destroy(m);
        }
    }
}
