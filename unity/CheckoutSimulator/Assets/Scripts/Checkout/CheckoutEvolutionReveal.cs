using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using UnityEngine.UI;
using K = Checkout.CheckoutDesktopKit;
using N = Checkout.CheckoutDesktopCard;

namespace Checkout
{
    // The reveal of an evolution (claude/evolucoes-recompensas.md, Lucas 01/11). When an evolution ends the piece goes
    // under a navy cloth with a gold ribbon and bow (the new model is never seen early: the snapshot lists it in
    // `reveals` until its celebration is seen). When its celebration comes up (CheckoutDesktopHUD.Conquest) the side HUD
    // fades away (coins and diamonds stay) and the reveal plays, about 3.7 s from cloth to card:
    //   0.0  the camera eases in (0.8 s) until the piece fills ~40% of the screen's height, a bit below the middle;
    //        the cloth sways; a drum roll;
    //   1.3  the cloth is pulled up with a flutter and dissolves into gold sparkles;
    //   1.75 the new model pops (squash and stretch 0.85 → 1.08 → 1.0 in 0.45 s), a soft burst of rays behind it, a
    //        warm rim light on it, navy/gold/cream confetti;
    //   2.0  the products drop in one by one, each with a little bounce and a puff (sectors: the worker hops, the price
    //        screens light up one by one); cream chips rise over the model ("+5 por produto", "+1 lugar", "NOVO: …");
    //   3.3  ta-da with a coin shimmer; the card comes once every product has landed.
    // The camera stays close until the card closes, then glides back to exactly where the player was. Generated meshes,
    // particles and synthesized sounds only: cheap on an iPhone. Times use CheckoutUiKit.Dt (videos at a fixed rate).
    public class CheckoutEvolutionReveal : MonoBehaviour
    {
        static CheckoutEvolutionReveal instance;
        public static CheckoutEvolutionReveal Instance { get { if (!instance) instance = new GameObject("Evolution reveal").AddComponent<CheckoutEvolutionReveal>(); return instance; } }

        static readonly Color Navy = new Color(.114f, .169f, .31f), Gold = new Color(.878f, .69f, .25f), Cream = new Color(1f, .96f, .86f);
        static readonly Color[] Palette = { Navy, Gold, Cream, new Color(.2f, .3f, .55f), new Color(1f, .82f, .36f) };
        static float Dt => CheckoutUiKit.Dt;

        class Veil
        {
            public string key, id; public List<Transform> roots = new List<Transform>(); public List<Renderer> hidden = new List<Renderer>();
            public Transform cloth; public Mesh mesh; public Vector3[] rest; public Bounds bounds; public float ripple = .3f, sway = 1, dropped = 1, phase;
        }
        readonly Dictionary<string, Veil> veils = new Dictionary<string, Veil>();
        readonly HashSet<string> played = new HashSet<string>();
        static readonly HashSet<Transform> busy = new HashSet<Transform>();
        Material clothMat, ribbonMat, burstMat;
        AudioSource audioSource;
        RectTransform chipLayer; readonly List<(RectTransform chip, CanvasGroup group, Vector3 anchor, float lift)> chips = new List<(RectTransform, CanvasGroup, Vector3, float)>();
        public bool Playing { get; private set; }
        /// <summary>QA: the moment of the reveal (0 cloth, 1 pulled, 2 popped, 3 products, 4 done) for the frame grabs.</summary>
        public int Stage { get; private set; }
        /// <summary>The piece's products are being dropped in: CheckoutInterior.SetFill leaves them to the reveal.</summary>
        public static bool Busy(Transform root) => root && busy.Contains(root);

        static string KeyOf(string kind, string target) => kind + ":" + target;

        // ---------------------------------------------------------------- the pieces
        static List<Transform> Targets(string kind, string target)
        {
            var list = new List<Transform>();
            var inside = CheckoutInterior.Active;
            if (kind == "coldroom") { if (CheckoutColdRoom.Root) list.Add(CheckoutColdRoom.Root); return list; }
            if (!inside) return list;
            foreach (var it in inside.items.Values)
            {
                if (!it.root || it.ghost) continue;
                bool hit = kind == "shelf" ? it.id == "shelf:" + target
                    : kind == "sector" ? it.id == "sector:" + target
                    : kind == "checkout" ? it.type == "checkout"
                    : kind == "decor" && it.type == target;
                if (hit) list.Add(it.root);
            }
            return list;
        }

        static Bounds BoundsOf(IEnumerable<Transform> roots)
        {
            Bounds b = default; bool any = false;
            foreach (var root in roots)
                foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                {
                    if (r is ParticleSystemRenderer || r.GetComponent<TMP_Text>()) continue;
                    if (r.name == "Evolution ring" || (r.transform.parent && r.transform.parent.name == "Evolution ring")) continue;
                    if (!any) { b = r.bounds; any = true; } else b.Encapsulate(r.bounds);
                }
            if (!any) foreach (var root in roots) { b = new Bounds(root.position + Vector3.up, new Vector3(1.5f, 2, 1)); break; }
            return b;
        }

        /// <summary>From the snapshot: the pieces whose reveal is due stay under the cloth; the others come out.</summary>
        public void Sync(RevealEntry[] reveals)
        {
            var due = new HashSet<string>();
            foreach (var r in reveals ?? Array.Empty<RevealEntry>())
            {
                if (r == null || string.IsNullOrEmpty(r.kind) || played.Contains(r.id)) continue;
                var key = KeyOf(r.kind, r.targetId); due.Add(key);
                if (veils.TryGetValue(key, out var v) && v.cloth) { Rehide(v); continue; }
                var roots = Targets(r.kind, r.targetId);
                if (roots.Count == 0) continue;
                veils[key] = Cover(key, r.id, roots, false);
            }
            foreach (var key in veils.Keys.ToList())
                if (!due.Contains(key) && !(Playing && playingKey == key)) { Uncover(veils[key]); veils.Remove(key); }
        }

        Veil Cover(string key, string id, List<Transform> roots, bool drop)
        {
            var v = new Veil { key = key, id = id, roots = roots, phase = UnityEngine.Random.value * 6 };
            v.bounds = BoundsOf(roots);
            foreach (var root in roots)
                foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                    if (!r.forceRenderingOff) { r.forceRenderingOff = true; v.hidden.Add(r); }
            BuildCloth(v);
            v.dropped = drop ? 0 : 1;
            return v;
        }

        void Rehide(Veil v)
        {
            foreach (var root in v.roots.Where(t => t))
                foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                    if (!r.forceRenderingOff && !(v.cloth && r.transform.IsChildOf(v.cloth))) { r.forceRenderingOff = true; v.hidden.Add(r); }
        }

        void Uncover(Veil v)
        {
            foreach (var r in v.hidden) if (r) r.forceRenderingOff = false;
            v.hidden.Clear();
            if (v.cloth) Destroy(v.cloth.gameObject);
            if (v.mesh) Destroy(v.mesh);
        }

        // ---------------------------------------------------------------- the cloth
        // A draped cloth: a soft tent over the piece with folds that deepen towards the hem, navy; two gold ribbons cross
        // over the top and are tied in a bow with two tails. A grid mesh, so it can sway, ripple and flutter.
        void BuildCloth(Veil v)
        {
            if (!clothMat) { clothMat = new Material(Shader.Find("Standard")) { color = Navy }; clothMat.SetFloat("_Glossiness", .5f); }
            if (!ribbonMat) { ribbonMat = new Material(Shader.Find("Standard")) { color = Gold }; ribbonMat.SetFloat("_Glossiness", .75f); ribbonMat.SetFloat("_Metallic", .35f); }
            var b = v.bounds; var size = b.size + new Vector3(.16f, .1f, .16f);
            var root = new GameObject("Evolution cloth").transform; root.SetParent(transform, false);
            root.position = new Vector3(b.center.x, b.min.y, b.center.z);
            var go = new GameObject("Cloth", typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(root, false);
            v.mesh = ClothMesh(size); v.rest = v.mesh.vertices;
            go.GetComponent<MeshFilter>().sharedMesh = v.mesh;
            var mr = go.GetComponent<MeshRenderer>(); mr.sharedMaterial = clothMat;
            float top = size.y + .1f;
            // the ribbons follow the drape: down the four sides from the top, a little out from the cloth
            float rx = size.x * .5f * 1.07f, rz = size.z * .5f * 1.07f;
            foreach (var side in new[] { -1, 1 })
            {
                Box(root, "Ribbon", new Vector3(side * rx, top * .5f, 0), new Vector3(.035f, top, .17f), ribbonMat);
                Box(root, "Ribbon", new Vector3(0, top * .5f, side * rz), new Vector3(.17f, top, .035f), ribbonMat);
            }
            Box(root, "Ribbon top", new Vector3(0, top + .005f, 0), new Vector3(size.x * 1.02f, .035f, .17f), ribbonMat);
            Box(root, "Ribbon top", new Vector3(0, top + .01f, 0), new Vector3(.17f, .035f, size.z * 1.02f), ribbonMat);
            // the bow: two loops, a knot and two tails
            float bow = Mathf.Clamp(Mathf.Min(size.x, size.z) * .22f, .18f, .42f);
            var knotAt = new Vector3(0, top + .06f, 0);
            foreach (var s in new[] { -1, 1 })
            {
                var loop = GameObject.CreatePrimitive(PrimitiveType.Sphere); Destroy(loop.GetComponent<Collider>()); loop.name = "Bow loop";
                loop.transform.SetParent(root, false); loop.transform.localPosition = knotAt + new Vector3(s * bow * .62f, bow * .28f, 0);
                loop.transform.localScale = new Vector3(bow * 1.1f, bow * .62f, bow * .34f); loop.transform.localRotation = Quaternion.Euler(0, 0, s * -28);
                loop.GetComponent<Renderer>().sharedMaterial = ribbonMat;
                var tail = Box(root, "Bow tail", knotAt + new Vector3(s * bow * .35f, -.01f, bow * .3f), new Vector3(.1f, .025f, bow * 1.1f), ribbonMat);
                tail.localRotation = Quaternion.Euler(18, s * 24, 0);
            }
            var knot = GameObject.CreatePrimitive(PrimitiveType.Sphere); Destroy(knot.GetComponent<Collider>()); knot.name = "Bow knot";
            knot.transform.SetParent(root, false); knot.transform.localPosition = knotAt + new Vector3(0, bow * .2f, 0); knot.transform.localScale = Vector3.one * bow * .42f;
            knot.GetComponent<Renderer>().sharedMaterial = ribbonMat;
            v.cloth = root;
        }

        static Transform Box(Transform parent, string name, Vector3 at, Vector3 size, Material m)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(go.GetComponent<Collider>()); go.name = name;
            go.transform.SetParent(parent, false); go.transform.localPosition = at; go.transform.localScale = size;
            go.GetComponent<Renderer>().sharedMaterial = m;
            return go.transform;
        }

        static Mesh ClothMesh(Vector3 size)
        {
            const int around = 72, rows = 12;
            var verts = new List<Vector3>(); var tris = new List<int>();
            float hx = size.x * .5f, hz = size.z * .5f, h = size.y;
            float perimeter = 2 * (size.x + size.z);
            int folds = Mathf.Clamp(Mathf.RoundToInt(perimeter / .32f), 10, 36);
            Vector3 Edge(float u, float flare, float foldAmp)
            {
                float a = u * Mathf.PI * 2; var d = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                float k = 1 / Mathf.Max(Mathf.Abs(d.x) / hx, Mathf.Abs(d.y) / hz);
                var p = d * k; p = Vector2.Lerp(p, d * Mathf.Min(hx, hz), .15f);
                // folds: soft vertical waves, irregular so it reads as cloth and not as a fluted column
                float fold = Mathf.Sin(u * folds * Mathf.PI * 2) * .7f + Mathf.Sin(u * folds * 1.7f * Mathf.PI * 2 + 1.3f) * .3f;
                return new Vector3(p.x * flare * (1 + foldAmp * fold), 0, p.y * flare * (1 + foldAmp * fold));
            }
            for (int r = 0; r <= rows; r++)
            {
                float v = r / (float)rows, y = h * v, hem = 1 - v;
                float flare = 1 + .09f * hem * hem, foldAmp = .015f + .07f * hem;
                for (int i = 0; i <= around; i++) { var e = Edge(i / (float)around, flare, foldAmp); verts.Add(new Vector3(e.x, y, e.z)); }
            }
            int top0 = verts.Count;
            for (int ring = 1; ring <= 5; ring++)
            {
                float s = 1 - ring / 5f, y = h + .1f * Mathf.Sin(ring / 5f * Mathf.PI * .5f);
                for (int i = 0; i <= around; i++) { var e = Edge(i / (float)around, 1, .015f * s); verts.Add(new Vector3(e.x * s, y, e.z * s)); }
            }
            int W = around + 1;
            for (int r = 0; r < rows + 5; r++)
            {
                int a0 = r < rows ? r * W : (r == rows ? rows * W : top0 + (r - rows - 1) * W);
                int b0 = r < rows ? (r + 1) * W : top0 + (r - rows) * W;
                for (int i = 0; i < around; i++) { tris.Add(a0 + i); tris.Add(b0 + i); tris.Add(b0 + i + 1); tris.Add(a0 + i); tris.Add(b0 + i + 1); tris.Add(a0 + i + 1); }
            }
            var m = new Mesh { name = "Evolution cloth" }; m.SetVertices(verts); m.SetTriangles(tris, 0); m.RecalculateNormals(); m.RecalculateBounds();
            return m;
        }

        void Update()
        {
            float t = Time.time;
            foreach (var v in veils.Values)
            {
                if (!v.cloth || v.mesh == null) continue;
                var verts = v.mesh.vertices; float h = Mathf.Max(.1f, v.bounds.size.y);
                for (int i = 0; i < verts.Length; i++)
                {
                    var r = v.rest[i]; float hem = 1 - Mathf.Clamp01(r.y / h);
                    float w = v.ripple * (.012f + .05f * hem) * Mathf.Sin(t * 5.2f + r.x * 3.1f + r.z * 2.3f + r.y * 4f + v.phase);
                    var outDir = new Vector3(r.x, 0, r.z); outDir = outDir.sqrMagnitude > 1e-4f ? outDir.normalized : Vector3.zero;
                    verts[i] = r + outDir * w + Vector3.up * w * .25f;
                }
                v.mesh.vertices = verts; v.mesh.RecalculateNormals();
                // a little sway of the whole drape while it waits
                v.cloth.localRotation = Quaternion.Euler(Mathf.Sin(t * 1.9f + v.phase) * 1.6f * v.sway, 0, Mathf.Sin(t * 1.4f + v.phase * .7f) * 1.9f * v.sway);
            }
            UpdateChips();
        }

        // ---------------------------------------------------------------- the reveal
        string playingKey;
        /// <summary>Plays the reveal of `data` (from the celebration). Returns how long to wait before the card.</summary>
        public float Play(DesktopCelebrationReveal data, string celebrationId, bool moveCamera)
        {
            if (data == null || string.IsNullOrEmpty(data.kind)) return 0;
            var key = KeyOf(data.kind, data.targetId);
            played.Add(celebrationId ?? key);
            if (!veils.TryGetValue(key, out var v) || !v.cloth)
            {
                var roots = Targets(data.kind, data.targetId);
                if (roots.Count == 0) return 0;      // not in this shop's view (e.g. the cold room in a stall)
                v = Cover(key, celebrationId, roots, true); veils[key] = v;
            }
            StopAllCoroutines(); ClearChips();
            int products = 0;
            foreach (var root in v.roots) { var piece = PieceOf(root); if (piece != null && piece.fill != null) products += piece.fill.Count(g => g && g.activeSelf); }
            products = Mathf.Min(products, 12);
            float step = products > 0 ? Mathf.Min(.12f, 1.1f / products) : 0;
            float landed = DropAt + products * step + .42f;
            StartCoroutine(Run(v, data, moveCamera, step));
            return Mathf.Clamp(Mathf.Max(landed, 3.45f) + .25f, 3.6f, 4.0f);
        }

        const float PullAt = 1.3f, PopAt = 1.75f, DropAt = 2.0f;
        static CheckoutInteriorPiece PieceOf(Transform root)
        {
            if (!root) return null;
            var p = root.GetComponent<CheckoutInteriorPiece>();
            if (!p) p = root.GetComponentInChildren<CheckoutInteriorPiece>();
            return p ? p : null;
        }

        /// <summary>Where to point the camera and how close: the piece fills `fill` of the screen's height (and at most
        /// 80% of its width), its middle a little below the screen's middle; the aim is on the ground along the view.</summary>
        static (Vector3 aim, float size) Framing(Bounds b, Camera cam, float fill = .4f, float below = .05f)
        {
            var rot = cam.transform.rotation; var up = rot * Vector3.up; var right = rot * Vector3.right; var fwd = rot * Vector3.forward;
            float minU = float.MaxValue, maxU = float.MinValue, minR = float.MaxValue, maxR = float.MinValue;
            for (int i = 0; i < 8; i++)
            {
                var c = new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z);
                float u = Vector3.Dot(c, up), r = Vector3.Dot(c, right);
                minU = Mathf.Min(minU, u); maxU = Mathf.Max(maxU, u); minR = Mathf.Min(minR, r); maxR = Mathf.Max(maxR, r);
            }
            float size = Mathf.Max((maxU - minU) / (2 * fill), (maxR - minR) / (1.6f * Mathf.Max(.3f, cam.aspect)));
            size = Mathf.Clamp(size, 2.4f, 14f);
            // the piece's projected middle, then the screen's middle is put a little above it
            var mid = b.center + up * ((minU + maxU) * .5f - Vector3.Dot(b.center, up)) + right * ((minR + maxR) * .5f - Vector3.Dot(b.center, right));
            var look = mid + up * (below * 2 * size);
            var aim = fwd.y < -.05f ? look + fwd * ((look.y - .1f) / -fwd.y) : new Vector3(look.x, 0, look.z);
            return (aim, size);
        }

        IEnumerator Run(Veil v, DesktopCelebrationReveal data, bool moveCamera, float dropStep)
        {
            Playing = true; playingKey = v.key; Stage = 0;
            var fx = CheckoutConquestFx.Instance;
            var b = v.bounds; var center = b.center; var size = b.size;
            var cam = Camera.main;
            if (moveCamera && cam) { var f = Framing(b, cam); fx.FocusOn(f.aim, f.size, .8f); }
            float clock = 0;
            IEnumerator Until(float at) { while (clock < at) { clock += Dt; yield return null; } }
            // The cloth falls into place first if it was not there yet.
            if (v.dropped < 1)
            {
                var rest = v.cloth.position;
                for (float k = 0; k < 1; k += Dt / .42f) { float e = k * k; v.cloth.position = rest + Vector3.up * (1 - e) * 2f; v.ripple = 1.3f; clock += Dt; yield return null; }
                v.cloth.position = rest; v.dropped = 1; Play(Thud(), .6f);
            }
            v.ripple = .45f; v.sway = 1;
            yield return Until(.3f);
            Play(DrumRoll(), .5f);
            while (clock < PullAt) { v.ripple = Mathf.Lerp(.45f, 1.5f, Mathf.InverseLerp(.3f, PullAt, clock)); v.sway = Mathf.Lerp(1, 2.2f, Mathf.InverseLerp(.3f, PullAt, clock)); clock += Dt; yield return null; }
            // Pulled up with a flutter: it rises, twists, narrows and dissolves into gold sparkles.
            Stage = 1; Play(CheckoutUiKit.Sfx("whoosh"), .55f);
            var cloth = v.cloth; var from = cloth.position; int bursts = 0;
            for (float k = 0; k < 1; k += Dt / .45f)
            {
                if (!cloth) break;
                float e = k * k * (3 - 2 * k);
                v.ripple = 2.6f; v.sway = 0;
                cloth.position = from + Vector3.up * e * 1.5f;
                cloth.localRotation = Quaternion.Euler(Mathf.Sin(k * 18) * 6 * (1 - k), e * 70, Mathf.Cos(k * 15) * 5 * (1 - k));
                float narrow = Mathf.Lerp(1, .15f, e * e);
                cloth.localScale = new Vector3(narrow, Mathf.Lerp(1, .55f, e), narrow);
                if (bursts < 3 && k > bursts * .33f + .1f) { bursts++; fx.SparkleAt(cloth.position + Vector3.up * size.y * .6f, Mathf.Max(.8f, size.x * narrow), Mathf.Max(.8f, size.z * narrow), 14); }
                clock += Dt; yield return null;
            }
            if (cloth) { fx.SparkleAt(cloth.position + Vector3.up * size.y * .5f, .9f, .9f, 22); Destroy(cloth.gameObject); }
            v.cloth = null;
            yield return Until(PopAt);
            // The new model pops, with a soft burst of rays behind it and a warm rim light on it.
            Stage = 2;
            var products = new List<GameObject>();
            foreach (var root in v.roots)
            {
                var piece = PieceOf(root);
                if (piece != null && piece.fill != null) foreach (var g in piece.fill) if (g && g.activeSelf) { products.Add(g); g.SetActive(false); }
                if (root) busy.Add(root);
            }
            foreach (var r in v.hidden) if (r) r.forceRenderingOff = false;
            v.hidden.Clear();
            foreach (var root in v.roots) if (root) StartCoroutine(Pop(root));
            StartCoroutine(Burst(center, Mathf.Max(size.x, size.y, size.z), cam));
            StartCoroutine(RimLight(center, Mathf.Max(size.x, size.y, size.z), cam));
            fx.ConfettiAt(new Vector3(center.x, b.max.y + .15f, center.z), 80, .55f, Palette);
            Play(CheckoutUiKit.Sfx("pop"), .8f);
            yield return Until(DropAt);
            // Products in, one by one (sectors: the worker hops, the price screens light up); the chips rise.
            Stage = 3;
            if (data.kind == "sector") SectorShow(v);
            StartCoroutine(Chips(new Vector3(center.x, b.max.y, center.z), data.chips ?? Array.Empty<string>(), data.chipIcons ?? Array.Empty<string>()));
            int n = 0;
            foreach (var g in products.OrderBy(p => -p.transform.position.y).ThenBy(p => p.transform.position.x))
            {
                if (!g) continue;
                if (n >= 12) { g.SetActive(true); continue; }
                StartCoroutine(Drop(g, n * dropStep, size)); n++;
            }
            float landed = DropAt + n * dropStep + .42f;
            yield return Until(Mathf.Max(3.3f, landed - .1f));
            Play(TaDa(), .7f);
            for (int i = 0; i < 4; i++) { Play(CheckoutUiKit.Sfx("coin_" + (i % 3)), .3f, 1.2f + i * .12f); yield return CheckoutUiKit.Wait(.07f); }
            foreach (var root in v.roots) busy.Remove(root);
            Stage = 4; veils.Remove(v.key);
            Playing = false; playingKey = null;
            yield return CheckoutUiKit.Wait(.4f);
            FadeChips();
        }

        static IEnumerator Pop(Transform t)
        {
            var full = t.localScale;
            for (float k = 0; k < 1; k += Dt / .45f)
            {
                if (!t) yield break;
                // squash 0.85 → stretch 1.08 → 1.0 (wider when squashed, thinner when stretched)
                float y = k < .4f ? Mathf.Lerp(.85f, 1.08f, Ease(k / .4f)) : Mathf.Lerp(1.08f, 1f, Ease((k - .4f) / .6f));
                float xz = 1 + (1 - y) * .55f;
                t.localScale = new Vector3(full.x * xz, full.y * y, full.z * xz); yield return null;
            }
            if (t) t.localScale = full;
        }
        static float Ease(float k) => k * k * (3 - 2 * k);

        IEnumerator Drop(GameObject g, float delay, Vector3 pieceSize)
        {
            yield return CheckoutUiKit.Wait(delay);
            if (!g) yield break;
            var t = g.transform; var rest = t.localPosition; var restScale = t.localScale;
            float fall = Mathf.Clamp(pieceSize.y * .35f, .35f, .8f);
            var up = t.parent ? t.parent.InverseTransformVector(Vector3.up * fall) : Vector3.up * fall;
            g.SetActive(true); bool puffed = false;
            for (float k = 0; k < 1; k += Dt / .42f)
            {
                if (!t) yield break;
                float y, squash = 1;
                if (k < .5f) { float q = k / .5f; y = 1 - q * q; }
                else { float q = (k - .5f) / .5f; y = .16f * Mathf.Sin(q * Mathf.PI) * (1 - q * .3f); if (!puffed) { puffed = true; Landed(t); } squash = 1 - .12f * Mathf.Sin(Mathf.Min(1, q * 2) * Mathf.PI); }
                t.localPosition = rest + up * y;
                t.localScale = new Vector3(restScale.x * (2 - squash), restScale.y * squash, restScale.z * (2 - squash));
                yield return null;
            }
            if (t) { t.localPosition = rest; t.localScale = restScale; }
        }

        void Landed(Transform t)
        {
            var at = t.position; var rs = t.GetComponentsInChildren<Renderer>();
            if (rs.Length > 0) { var bb = rs[0].bounds; foreach (var r in rs) bb.Encapsulate(r.bounds); at = new Vector3(bb.center.x, bb.min.y, bb.center.z); }
            CheckoutConquestFx.Instance.PuffAt(at, .7f, 6);
            Play(CheckoutUiKit.Sfx("pop"), .22f, 1.3f + UnityEngine.Random.value * .4f);
        }

        void SectorShow(Veil v)
        {
            foreach (var root in v.roots)
            {
                if (!root) continue;
                var screens = root.GetComponentInChildren<CheckoutSectorScreens>(true);
                if (screens) StartCoroutine(screens.LightUp(.2f));
                var c = root.position; CheckoutSectorWorker best = null; float bestD = 5f;
                foreach (var w in FindObjectsByType<CheckoutSectorWorker>(FindObjectsSortMode.None))
                { float d = Vector3.Distance(new Vector3(w.transform.position.x, 0, w.transform.position.z), new Vector3(c.x, 0, c.z)); if (d < bestD) { bestD = d; best = w; } }
                if (best) { var body = best.transform.Find("Visual"); if (!body && best.transform.childCount > 0) body = best.transform.GetChild(0); StartCoroutine(Hop(body)); }
            }
        }

        static IEnumerator Hop(Transform t)
        {
            if (!t) yield break;
            var rest = t.localPosition;
            var lift = t.parent ? t.parent.InverseTransformVector(Vector3.up * .45f) : Vector3.up * .45f;
            for (int i = 0; i < 2; i++)
                for (float k = 0; k < 1; k += Dt / .32f)
                {
                    if (!t) yield break;
                    t.localPosition = rest + lift * Mathf.Sin(k * Mathf.PI);
                    yield return null;
                }
            if (t) t.localPosition = rest;
        }

        // A soft burst of rays behind the model (fans out and fades in 0.8 s); low alpha so the model stays clear.
        IEnumerator Burst(Vector3 center, float extent, Camera cam)
        {
            if (!burstMat) burstMat = new Material(Shader.Find("Sprites/Default")) { mainTexture = RaysTexture(), renderQueue = 2990 };
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad); Destroy(go.GetComponent<Collider>()); go.name = "Evolution burst"; go.layer = 2;
            go.transform.SetParent(transform, false);
            var r = go.GetComponent<MeshRenderer>(); var m = new Material(burstMat); r.sharedMaterial = m; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            var fwd = cam ? cam.transform.forward : Vector3.forward;
            go.transform.position = center + fwd * (extent * .9f + .3f);
            float spin = 0;
            for (float k = 0; k < 1; k += Dt / .8f)
            {
                if (cam) go.transform.rotation = cam.transform.rotation * Quaternion.Euler(0, 0, spin);
                spin += Dt * 30;
                float s = extent * Mathf.Lerp(1.2f, 3.2f, 1 - (1 - k) * (1 - k));
                go.transform.localScale = new Vector3(s, s, 1);
                float a = k < .15f ? k / .15f : 1 - (k - .15f) / .85f;
                m.color = new Color(1f, .9f, .6f, .38f * a);
                yield return null;
            }
            Destroy(m); Destroy(go);
        }

        // A brief warm light from the front and above: the new model's edges catch it as it pops.
        IEnumerator RimLight(Vector3 center, float extent, Camera cam)
        {
            var go = new GameObject("Evolution rim light"); go.transform.SetParent(transform, false);
            var back = cam ? -cam.transform.forward : Vector3.back;
            go.transform.position = center + back * (extent * .8f + .6f) + Vector3.up * extent * .8f;
            var l = go.AddComponent<Light>(); l.type = LightType.Point; l.color = new Color(1f, .82f, .52f); l.range = extent * 3.2f + 2; l.shadows = LightShadows.None; l.renderMode = LightRenderMode.ForcePixel;
            for (float k = 0; k < 1; k += Dt / .75f) { l.intensity = 2.4f * Mathf.Sin(Mathf.Min(1, k * 1.2f) * Mathf.PI); yield return null; }
            Destroy(go);
        }

        static Texture2D raysTexture;
        static Texture2D RaysTexture()
        {
            if (raysTexture) return raysTexture;
            const int n = 256; var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp }; var px = new Color32[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float dx = (x + .5f) / n * 2 - 1, dy = (y + .5f) / n * 2 - 1, d = Mathf.Sqrt(dx * dx + dy * dy), a = Mathf.Atan2(dy, dx);
                float rays = Mathf.Pow(Mathf.Abs(Mathf.Cos(a * 7)), 6) * .85f + .15f;
                float fall = Mathf.Clamp01(1 - d) * Mathf.Clamp01(d * 4 - .2f);   // hollow middle: the model, not a glow, sits there
                float v = rays * fall * fall;
                px[y * n + x] = new Color32(255, 255, 255, (byte)(Mathf.Clamp01(v) * 255));
            }
            t.SetPixels32(px); t.Apply(); raysTexture = t; return t;
        }

        // ---------------------------------------------------------------- chips (screen space: readable on a phone)
        void EnsureChipLayer()
        {
            if (chipLayer) return;
            var go = new GameObject("Evolution chips", typeof(RectTransform)); go.transform.SetParent(transform, false);
            var canvas = go.AddComponent<Canvas>(); canvas.renderMode = RenderMode.ScreenSpaceOverlay; canvas.sortingOrder = 94;
            var scaler = go.AddComponent<CanvasScaler>(); CheckoutScreen.Fit(scaler);
            chipLayer = (RectTransform)go.transform;
        }

        IEnumerator Chips(Vector3 anchor, string[] texts, string[] icons)
        {
            EnsureChipLayer();
            for (int i = 0; i < texts.Length && i < 4; i++)
            {
                if (string.IsNullOrEmpty(texts[i])) continue;
                var pill = N.Image(chipLayer, "Chip", Cream, 30);
                var rt = pill.rectTransform; rt.anchorMin = rt.anchorMax = Vector2.zero; rt.pivot = new Vector2(.5f, .5f);
                var edge = pill.gameObject.AddComponent<Outline>(); edge.effectColor = Navy; edge.effectDistance = new Vector2(3, -3);
                var row = pill.gameObject.AddComponent<HorizontalLayoutGroup>(); row.padding = new RectOffset(16, 26, 8, 8); row.spacing = 12; row.childAlignment = TextAnchor.MiddleCenter;
                row.childControlWidth = row.childControlHeight = true; row.childForceExpandWidth = row.childForceExpandHeight = false;
                var fit = pill.gameObject.AddComponent<ContentSizeFitter>(); fit.horizontalFit = fit.verticalFit = ContentSizeFitter.FitMode.PreferredSize;
                var iconPath = i < icons.Length ? icons[i] : "";
                var sprite = string.IsNullOrEmpty(iconPath) ? null : K.Icon(iconPath);
                if (sprite)
                {
                    var icon = N.Image(pill.transform, "Icon", Color.white, 0); icon.sprite = sprite; icon.preserveAspect = true;
                    var le = icon.gameObject.AddComponent<LayoutElement>(); le.preferredWidth = le.preferredHeight = 48;
                }
                var label = N.Text(pill.transform, "Text", K.Headline, 34, Navy); label.textWrappingMode = TextWrappingModes.NoWrap; label.text = K.Clean(texts[i]);
                var group = pill.gameObject.AddComponent<CanvasGroup>(); group.alpha = 0;
                chips.Add((rt, group, anchor, 0));
                int index = chips.Count - 1;
                StartCoroutine(RiseChip(index, i));
                Play(CheckoutUiKit.Sfx("pop"), .3f, 1.5f + i * .1f);
                yield return CheckoutUiKit.Wait(.32f);
            }
        }

        IEnumerator RiseChip(int index, int order)
        {
            float target = 70 + order * 86;
            for (float k = 0; k < 1; k += Dt / .45f)
            {
                if (index >= chips.Count || !chips[index].chip) yield break;
                var c = chips[index]; float e = 1 - (1 - k) * (1 - k);
                c.group.alpha = Mathf.Min(1, k * 2.5f);
                c.chip.localScale = Vector3.one * (k < .6f ? Mathf.Lerp(.5f, 1.08f, k / .6f) : Mathf.Lerp(1.08f, 1f, (k - .6f) / .4f));
                chips[index] = (c.chip, c.group, c.anchor, target * e);
                yield return null;
            }
            if (index < chips.Count && chips[index].chip) { var c = chips[index]; c.chip.localScale = Vector3.one; chips[index] = (c.chip, c.group, c.anchor, target); }
        }

        void UpdateChips()
        {
            if (!chipLayer || chips.Count == 0) return;
            var cam = Camera.main; if (!cam) return;
            foreach (var c in chips)
            {
                if (!c.chip) continue;
                var screen = cam.WorldToScreenPoint(c.anchor);
                RectTransformUtility.ScreenPointToLocalPointInRectangle(chipLayer, screen, null, out var local);
                c.chip.anchoredPosition = local + chipLayer.rect.size * .5f + new Vector2(0, 40 + c.lift);
            }
        }

        void FadeChips() { StartCoroutine(FadeChipsRun()); }
        IEnumerator FadeChipsRun()
        {
            for (float k = 0; k < 1; k += Dt / .3f) { foreach (var c in chips) if (c.group) c.group.alpha = 1 - k; yield return null; }
            ClearChips();
        }
        void ClearChips() { foreach (var c in chips) if (c.chip) Destroy(c.chip.gameObject); chips.Clear(); }

        // ---------------------------------------------------------------- sounds (synthesized: no new assets)
        void Play(AudioClip clip, float volume, float pitch = 1)
        {
            if (!clip) return;
            if (!audioSource) { audioSource = gameObject.AddComponent<AudioSource>(); audioSource.playOnAwake = false; }
            audioSource.pitch = pitch; audioSource.PlayOneShot(clip, volume);
        }

        static AudioClip drum, tada, thud;
        static AudioClip DrumRoll()
        {
            if (drum) return drum;
            int rate = 22050, n = (int)(rate * 1.0f); var d = new float[n]; var rnd = new System.Random(7);
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)rate, hit = Mathf.Repeat(t * 26f, 1), env = Mathf.Exp(-hit * 9) * Mathf.Lerp(.35f, 1f, t);
                float noise = (float)(rnd.NextDouble() * 2 - 1), body = Mathf.Sin(2 * Mathf.PI * 180 * t) * .5f;
                d[i] = (noise * .55f + body) * env * .6f * Mathf.Clamp01((1 - t) * 12);
            }
            drum = AudioClip.Create("evolution drum roll", n, 1, rate, false); drum.SetData(d, 0); return drum;
        }
        static AudioClip TaDa()
        {
            if (tada) return tada;
            int rate = 22050, n = (int)(rate * 1.1f); var d = new float[n];
            float[] first = { 523.25f, 659.25f, 783.99f }, second = { 523.25f, 659.25f, 783.99f, 1046.5f };
            for (int i = 0; i < n; i++)
            {
                float t = i / (float)rate; float v = 0;
                if (t < .16f) foreach (var f in first) v += Tone(f, t) * Mathf.Clamp01(1 - t / .16f);
                else { float u = t - .2f; if (u > 0) foreach (var f in second) v += Tone(f, u) * Mathf.Exp(-u * 2.4f); }
                d[i] = v * .16f * Mathf.Clamp01(t * 200);
            }
            tada = AudioClip.Create("evolution ta-da", n, 1, rate, false); tada.SetData(d, 0); return tada;
        }
        static float Tone(float f, float t) => Mathf.Sin(2 * Mathf.PI * f * t) + .35f * Mathf.Sin(4 * Mathf.PI * f * t) + .15f * Mathf.Sin(6 * Mathf.PI * f * t);
        static AudioClip Thud()
        {
            if (thud) return thud;
            int rate = 22050, n = (int)(rate * .25f); var d = new float[n];
            for (int i = 0; i < n; i++) { float t = i / (float)rate; d[i] = Mathf.Sin(2 * Mathf.PI * 95 * t) * Mathf.Exp(-t * 18) * .7f; }
            thud = AudioClip.Create("evolution thud", n, 1, rate, false); thud.SetData(d, 0); return thud;
        }

        // ---------------------------------------------------------------- the card's picture of the new look
        /// <summary>The new tier's picture for the card: the build-mode sprite of its model (bright 3/4 render), or null.</summary>
        public static Sprite TierSprite(string template) => string.IsNullOrEmpty(template) ? null : K.Icon("Decor/" + template);

        /// <summary>Fallback: a picture of the piece as it stands now, lit from the front.</summary>
        public static Texture2D Portrait(string kind, string target, int size = 256)
        {
            var roots = Targets(kind, target); if (roots.Count == 0) return null;
            var main = Camera.main; if (!main) return null;
            var root = roots[0]; var b = BoundsOf(new[] { root });
            const int layer = 31;
            var renderers = root.GetComponentsInChildren<Renderer>(true).Where(r => r.enabled && !r.forceRenderingOff && !(r is ParticleSystemRenderer)).ToList();
            var layers = renderers.Select(r => r.gameObject.layer).ToList();
            foreach (var r in renderers) r.gameObject.layer = layer;
            var go = new GameObject("Evolution portrait camera"); var cam = go.AddComponent<Camera>();
            var lightGo = new GameObject("Evolution portrait light"); var light = lightGo.AddComponent<Light>();
            try
            {
                light.type = LightType.Directional; light.intensity = 1.1f; light.cullingMask = 1 << layer; light.color = new Color(1f, .97f, .9f);
                cam.CopyFrom(main); cam.cullingMask = 1 << layer; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0, 0, 0, 0);
                // three-quarter view from the customers' side, a bit from above
                var dir = Quaternion.Euler(28, root.eulerAngles.y + 180 + 35, 0) * Vector3.forward;
                float r0 = b.extents.magnitude;
                cam.orthographic = true; cam.orthographicSize = r0 * 1.05f;
                go.transform.rotation = Quaternion.LookRotation(-dir); go.transform.position = b.center + dir * (r0 * 4 + 5);
                lightGo.transform.rotation = go.transform.rotation * Quaternion.Euler(-15, 20, 0);
                cam.nearClipPlane = .1f; cam.farClipPlane = r0 * 8 + 20;
                var rt = RenderTexture.GetTemporary(size, size, 24, RenderTextureFormat.ARGB32); rt.antiAliasing = 4;
                cam.targetTexture = rt; cam.Render();
                var prev = RenderTexture.active; RenderTexture.active = rt;
                var tex = new Texture2D(size, size, TextureFormat.RGBA32, false); tex.ReadPixels(new Rect(0, 0, size, size), 0, 0); tex.Apply();
                RenderTexture.active = prev; cam.targetTexture = null; RenderTexture.ReleaseTemporary(rt);
                return tex;
            }
            finally
            {
                for (int i = 0; i < renderers.Count; i++) if (renderers[i]) renderers[i].gameObject.layer = layers[i];
                Destroy(go); Destroy(lightGo);
            }
        }
    }
}
