using System;
using System.Collections;
using System.Collections.Generic;
using System.Linq;
using TMPro;
using UnityEngine;
using K = Checkout.CheckoutDesktopKit;

namespace Checkout
{
    // The reveal of an evolution (claude/evolucoes-recompensas.md, Lucas 01/11). When an evolution ends the piece goes
    // under a navy cloth with a gold ribbon (the new model is never seen early; the snapshot lists it in `reveals` until
    // its celebration is seen). When its celebration comes up (CheckoutDesktopHUD.Conquest) the reveal plays, ~3 s:
    //   0.0  the camera eases to the piece (0.6 s); the cloth ripples, a drum roll;
    //   1.4  the cloth is pulled up and vanishes in gold sparkle;
    //   1.7  the new model pops (squash and stretch 0.85 → 1.08 → 1.0) with light rays and navy/gold/cream confetti;
    //   2.0  the products drop in one by one with a bounce (sectors: the worker hops, the price screens light up);
    //   2.1  floating chips rise ("+5 por produto", "+1 lugar", "NOVO: Morango");
    //   2.8  ta-da with a coin shimmer.
    // Then the celebration card. Generated meshes, particles and synthesized sounds only: cheap on an iPhone.
    public class CheckoutEvolutionReveal : MonoBehaviour
    {
        static CheckoutEvolutionReveal instance;
        public static CheckoutEvolutionReveal Instance { get { if (!instance) instance = new GameObject("Evolution reveal").AddComponent<CheckoutEvolutionReveal>(); return instance; } }

        static readonly Color Navy = new Color(.114f, .169f, .31f), Gold = new Color(.878f, .69f, .25f), Cream = new Color(1f, .96f, .86f);
        static readonly Color[] Palette = { Navy, Gold, Cream, new Color(.2f, .3f, .55f), new Color(1f, .82f, .36f) };

        // A piece (or the pieces of a kind) under the cloth.
        class Veil
        {
            public string key, id; public List<Transform> roots = new List<Transform>(); public List<Renderer> hidden = new List<Renderer>();
            public Transform cloth; public Mesh mesh; public Vector3[] rest; public Bounds bounds; public float ripple = .25f, dropped = 1;
        }
        readonly Dictionary<string, Veil> veils = new Dictionary<string, Veil>();
        readonly HashSet<string> played = new HashSet<string>();
        Material clothMat, ribbonMat, chipMat;
        AudioSource audioSource;
        public bool Playing { get; private set; }
        /// <summary>QA: the moment of the reveal (0 cloth, 1 pulled, 2 popped, 3 products, 4 done) for the frame grabs.</summary>
        public int Stage { get; private set; }

        static string KeyOf(string kind, string target) => kind + ":" + target;

        // ---------------------------------------------------------------- the pieces
        /// <summary>The pieces an evolution changed: a fixture, a sector, every checkout, every machine of a kind, the cold room.</summary>
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

        static Bounds BoundsOf(IEnumerable<Transform> roots, IEnumerable<Renderer> skip = null)
        {
            Bounds b = default; bool any = false; var no = skip != null ? new HashSet<Renderer>(skip) : null;
            foreach (var root in roots)
                foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                {
                    if (r is ParticleSystemRenderer || r.GetComponent<TextMeshPro>() || (no != null && no.Contains(r))) continue;
                    if (r.name == "Evolution ring" || r.transform.parent && r.transform.parent.name == "Evolution ring") continue;
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
            var v = new Veil { key = key, id = id, roots = roots };
            v.bounds = BoundsOf(roots);
            foreach (var root in roots)
                foreach (var r in root.GetComponentsInChildren<Renderer>(true))
                    if (!r.forceRenderingOff) { r.forceRenderingOff = true; v.hidden.Add(r); }
            BuildCloth(v);
            v.dropped = drop ? 0 : 1;
            return v;
        }

        // Pieces rebuilt under the cloth (a new template, a resized shop): hide what appeared.
        void Rehide(Veil v)
        {
            var roots = v.roots.Where(t => t).ToList();
            if (roots.Count == 0) return;
            foreach (var root in roots)
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

        // The cloth: a box draped over the piece (rounded on top, a bit wider at the hem), navy, two gold ribbons
        // crossing over the top with a bow. A grid mesh so it can ripple.
        void BuildCloth(Veil v)
        {
            if (!clothMat) { clothMat = new Material(Shader.Find("Standard")) { color = Navy }; clothMat.SetFloat("_Glossiness", .45f); }
            if (!ribbonMat) { ribbonMat = new Material(Shader.Find("Standard")) { color = Gold }; ribbonMat.SetFloat("_Glossiness", .7f); ribbonMat.SetFloat("_Metallic", .4f); }
            var b = v.bounds; var size = b.size + new Vector3(.18f, .12f, .18f);
            var root = new GameObject("Evolution cloth").transform; root.SetParent(transform, false);
            root.position = new Vector3(b.center.x, b.min.y, b.center.z);
            // (the size comes from the world bounds: the cloth stays axis-aligned)
            root.rotation = Quaternion.identity;
            var go = new GameObject("Cloth", typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(root, false);
            v.mesh = ClothMesh(size); v.rest = v.mesh.vertices;
            go.GetComponent<MeshFilter>().sharedMesh = v.mesh;
            var mr = go.GetComponent<MeshRenderer>(); mr.sharedMaterial = clothMat; mr.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            float top = size.y + .02f;
            Ribbon(root, new Vector3(0, top * .5f, 0), new Vector3(.16f, top + .02f, size.z + .04f));
            Ribbon(root, new Vector3(0, top * .5f, 0), new Vector3(size.x + .04f, top + .02f, .16f));
            var bow = new GameObject("Bow").transform; bow.SetParent(root, false); bow.localPosition = new Vector3(0, top + .06f, 0);
            foreach (var side in new[] { -1, 1 })
            {
                var loop = GameObject.CreatePrimitive(PrimitiveType.Sphere); Destroy(loop.GetComponent<Collider>()); loop.name = "Loop";
                loop.transform.SetParent(bow, false); loop.transform.localPosition = new Vector3(side * .13f, .04f, 0); loop.transform.localScale = new Vector3(.24f, .12f, .14f);
                loop.transform.localRotation = Quaternion.Euler(0, 0, side * -20); loop.GetComponent<Renderer>().sharedMaterial = ribbonMat;
            }
            var knot = GameObject.CreatePrimitive(PrimitiveType.Sphere); Destroy(knot.GetComponent<Collider>()); knot.name = "Knot";
            knot.transform.SetParent(bow, false); knot.transform.localScale = Vector3.one * .1f; knot.GetComponent<Renderer>().sharedMaterial = ribbonMat;
            v.cloth = root;
        }

        void Ribbon(Transform parent, Vector3 at, Vector3 size)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(go.GetComponent<Collider>()); go.name = "Ribbon";
            go.transform.SetParent(parent, false); go.transform.localPosition = at; go.transform.localScale = size;
            go.GetComponent<Renderer>().sharedMaterial = ribbonMat;
        }

        // A closed "tent": four sides and a domed top, `n` rows high, with a slight flare at the hem.
        static Mesh ClothMesh(Vector3 size)
        {
            const int around = 48, rows = 10;
            var verts = new List<Vector3>(); var tris = new List<int>();
            float hx = size.x * .5f, hz = size.z * .5f, h = size.y;
            Vector3 Edge(float u, float flare)
            {
                // u in [0,1) around a rounded rectangle
                float a = u * Mathf.PI * 2; var d = new Vector2(Mathf.Cos(a), Mathf.Sin(a));
                float k = 1 / Mathf.Max(Mathf.Abs(d.x) / hx, Mathf.Abs(d.y) / hz);
                var p = d * k; p = Vector2.Lerp(p, d * Mathf.Min(hx, hz), .12f);
                return new Vector3(p.x * flare, 0, p.y * flare);
            }
            for (int r = 0; r <= rows; r++)
            {
                float v = r / (float)rows, y = h * v, flare = 1 + .06f * (1 - v);
                for (int i = 0; i <= around; i++) { var e = Edge(i / (float)around, flare); verts.Add(new Vector3(e.x, y, e.z)); }
            }
            int top0 = verts.Count;
            // dome: rings shrinking to the middle, slightly raised
            for (int ring = 1; ring <= 4; ring++)
            {
                float s = 1 - ring / 4f, y = h + .08f * Mathf.Sin(ring / 4f * Mathf.PI * .5f);
                for (int i = 0; i <= around; i++) { var e = Edge(i / (float)around, 1); verts.Add(new Vector3(e.x * s, y, e.z * s)); }
            }
            int W = around + 1;
            for (int r = 0; r < rows + 4; r++)
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
            foreach (var v in veils.Values)
            {
                if (!v.cloth || v.mesh == null) continue;
                // A soft breeze on the cloth (stronger in the drum roll), the hem moving most.
                var verts = v.mesh.vertices; float t = Time.time; float h = Mathf.Max(.1f, v.bounds.size.y);
                for (int i = 0; i < verts.Length; i++)
                {
                    var r = v.rest[i]; float hem = 1 - Mathf.Clamp01(r.y / h);
                    float w = v.ripple * (.02f + .06f * hem) * Mathf.Sin(t * 5.5f + r.x * 3.1f + r.z * 2.3f + r.y * 4f);
                    var outDir = new Vector3(r.x, 0, r.z); outDir = outDir.sqrMagnitude > 1e-4f ? outDir.normalized : Vector3.zero;
                    verts[i] = r + outDir * w + Vector3.up * w * .3f;
                }
                v.mesh.vertices = verts; v.mesh.RecalculateNormals();
            }
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
            StopAllCoroutines();
            StartCoroutine(Run(v, data, moveCamera));
            return 3.2f;
        }

        IEnumerator Run(Veil v, DesktopCelebrationReveal data, bool moveCamera)
        {
            Playing = true; playingKey = v.key; Stage = 0;
            var fx = CheckoutConquestFx.Instance;
            var b = v.bounds; var center = b.center; var size = b.size;
            if (moveCamera) fx.FocusOn(new Vector3(center.x, 0, center.z), Mathf.Clamp(Mathf.Max(size.x, size.z) * 2.6f + 5, 8, 14), .6f);
            // The cloth falls into place if it was not there yet.
            if (v.dropped < 1)
            {
                var rest = v.cloth.position;
                for (float k = 0; k < 1; k += Time.unscaledDeltaTime / .45f)
                {
                    float e = k * k; v.cloth.position = rest + Vector3.up * (1 - e) * 2.2f; v.ripple = 1.2f; yield return null;
                }
                v.cloth.position = rest; v.dropped = 1; Play(Thud(), .6f);
            }
            else yield return new WaitForSecondsRealtime(.45f);
            // Drum roll, the cloth trembling more and more.
            Play(DrumRoll(), .55f);
            for (float k = 0; k < 1; k += Time.unscaledDeltaTime / .95f) { v.ripple = Mathf.Lerp(.4f, 1.6f, k); yield return null; }
            // Pulled up: it rises, narrows and fades into gold sparkle.
            Stage = 1; Play(CheckoutUiKit.Sfx("whoosh"), .6f);
            var cloth = v.cloth; var from = cloth.position; var scale = cloth.localScale;
            for (float k = 0; k < 1; k += Time.unscaledDeltaTime / .32f)
            {
                if (!cloth) break;
                float e = 1 - (1 - k) * (1 - k);
                cloth.position = from + Vector3.up * e * 1.6f;
                cloth.localScale = new Vector3(scale.x * Mathf.Lerp(1, .25f, e), scale.y * Mathf.Lerp(1, .6f, e), scale.z * Mathf.Lerp(1, .25f, e));
                yield return null;
            }
            fx.SparkleAt(center + Vector3.up * size.y * .5f, Mathf.Max(1.5f, size.x), Mathf.Max(1.5f, size.z), 30);
            if (cloth) Destroy(cloth.gameObject);
            v.cloth = null;
            // The new model pops.
            Stage = 2;
            var products = new List<GameObject>();
            foreach (var root in v.roots)
            {
                if (!root) continue;
                var piece = root.GetComponent<CheckoutInteriorPiece>() ?? root.GetComponentInChildren<CheckoutInteriorPiece>();
                if (piece?.fill != null) foreach (var g in piece.fill) if (g && g.activeSelf) { products.Add(g); g.SetActive(false); }
            }
            foreach (var r in v.hidden) if (r) r.forceRenderingOff = false;
            v.hidden.Clear();
            foreach (var root in v.roots) if (root) StartCoroutine(Pop(root));
            fx.LightRays(new Vector3(center.x, b.min.y, center.z), Mathf.Max(.8f, Mathf.Min(size.x, size.z) * .55f), 1.8f);
            fx.ConfettiAt(new Vector3(center.x, b.max.y + .2f, center.z), 90, .8f, Palette);
            Play(CheckoutUiKit.Sfx("pop"), .8f);
            yield return new WaitForSecondsRealtime(.3f);
            // Products in, one by one (sectors: the worker hops and the price screens light up).
            Stage = 3;
            if (data.kind == "sector") SectorShow(v);
            StartCoroutine(Chips(center + Vector3.up * (size.y * .5f + .8f), data.chips ?? Array.Empty<string>()));
            int n = 0;
            foreach (var g in products.OrderBy(p => -p.transform.position.y).ThenBy(p => p.transform.position.x))
            {
                if (!g) continue;
                StartCoroutine(Drop(g, n * .07f)); n++;
                if (n > 16) { foreach (var rest in products.Skip(17)) if (rest) rest.SetActive(true); break; }
            }
            yield return new WaitForSecondsRealtime(Mathf.Min(.8f, .3f + n * .05f));
            Play(TaDa(), .7f);
            yield return new WaitForSecondsRealtime(.12f);
            for (int i = 0; i < 4; i++) { Play(CheckoutUiKit.Sfx("coin_" + (i % 3)), .35f, 1.2f + i * .12f); yield return new WaitForSecondsRealtime(.07f); }
            Stage = 4; veils.Remove(v.key);
            Playing = false; playingKey = null;
        }

        static IEnumerator Pop(Transform t)
        {
            var full = t.localScale;
            for (float k = 0; k < 1; k += Time.unscaledDeltaTime / .5f)
            {
                if (!t) yield break;
                // squash 0.85 → stretch 1.08 → 1.0 (the volume roughly kept: wider when squashed)
                float y = k < .35f ? Mathf.Lerp(.85f, 1.08f, k / .35f) : Mathf.Lerp(1.08f, 1f, (k - .35f) / .65f);
                float xz = 1 + (1 - y) * .5f;
                t.localScale = new Vector3(full.x * xz, full.y * y, full.z * xz); yield return null;
            }
            if (t) t.localScale = full;
        }

        IEnumerator Drop(GameObject g, float delay)
        {
            yield return new WaitForSecondsRealtime(delay);
            if (!g) yield break;
            var t = g.transform; var rest = t.localPosition; var up = t.parent ? t.parent.InverseTransformVector(Vector3.up * .55f) : Vector3.up * .55f;
            g.SetActive(true);
            for (float k = 0; k < 1; k += Time.unscaledDeltaTime / .3f)
            {
                if (!t) yield break;
                // fall, then one little bounce
                float y = k < .6f ? 1 - (k / .6f) * (k / .6f) : .18f * Mathf.Sin((k - .6f) / .4f * Mathf.PI);
                t.localPosition = rest + up * y; yield return null;
            }
            if (t) t.localPosition = rest;
            if (UnityEngine.Random.value < .5f) Play(CheckoutUiKit.Sfx("pop"), .25f, 1.3f + UnityEngine.Random.value * .4f);
        }

        void SectorShow(Veil v)
        {
            foreach (var root in v.roots)
            {
                if (!root) continue;
                var screens = root.GetComponentInChildren<CheckoutSectorScreens>(true);
                if (screens) StartCoroutine(screens.LightUp());
                // the sector's worker (behind its counter) hops twice
                var c = root.position; CheckoutSectorWorker best = null; float bestD = 4f;
                foreach (var w in FindObjectsByType<CheckoutSectorWorker>(FindObjectsSortMode.None))
                { float d = Vector3.Distance(new Vector3(w.transform.position.x, 0, w.transform.position.z), new Vector3(c.x, 0, c.z)); if (d < bestD) { bestD = d; best = w; } }
                if (best && best.transform.childCount > 0) StartCoroutine(Hop(best.transform.GetChild(0)));
            }
        }

        static IEnumerator Hop(Transform t)
        {
            var rest = t.localPosition;
            for (int i = 0; i < 2; i++)
                for (float k = 0; k < 1; k += Time.unscaledDeltaTime / .3f) { if (!t) yield break; t.localPosition = rest + Vector3.up * .35f * Mathf.Sin(k * Mathf.PI); yield return null; }
            if (t) t.localPosition = rest;
        }

        // Floating chips over the piece: navy pills with gold text, rising one after the other.
        IEnumerator Chips(Vector3 at, string[] chips)
        {
            if (!chipMat) chipMat = new Material(Shader.Find("Unlit/Color")) { color = Navy };
            var cam = Camera.main;
            for (int i = 0; i < chips.Length && i < 4; i++)
            {
                if (string.IsNullOrEmpty(chips[i])) continue;
                var chip = new GameObject("Evolution chip").transform; chip.SetParent(transform, false);
                chip.position = at + Vector3.right * ((i % 2 == 0 ? -1 : 1) * .35f * Mathf.Min(1, i));
                var back = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(back.GetComponent<Collider>()); back.transform.SetParent(chip, false);
                back.transform.localPosition = new Vector3(0, 0, .03f); back.GetComponent<Renderer>().sharedMaterial = chipMat;
                var rim = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(rim.GetComponent<Collider>()); rim.transform.SetParent(chip, false);
                rim.transform.localPosition = new Vector3(0, 0, .05f); rim.GetComponent<Renderer>().sharedMaterial = ribbonMat ? ribbonMat : chipMat;
                var label = new GameObject("Text").AddComponent<TextMeshPro>(); label.transform.SetParent(chip, false); label.transform.localPosition = Vector3.zero;
                CheckoutI18nText.Register(label);
                label.font = K.Headline; label.alignment = TextAlignmentOptions.Center; label.color = new Color(1f, .9f, .5f);
                label.textWrappingMode = TextWrappingModes.NoWrap; label.fontSize = 2.6f; label.rectTransform.sizeDelta = new Vector2(4, .6f);
                label.text = chips[i]; label.ForceMeshUpdate();
                float w = Mathf.Max(1.2f, label.preferredWidth + .45f);
                back.transform.localScale = new Vector3(w, .52f, .04f); rim.transform.localScale = new Vector3(w + .1f, .62f, .04f);
                StartCoroutine(Rise(chip, cam));
                Play(CheckoutUiKit.Sfx("pop"), .3f, 1.5f + i * .1f);
                yield return new WaitForSecondsRealtime(.28f);
            }
        }

        static IEnumerator Rise(Transform chip, Camera cam)
        {
            var from = chip.position;
            for (float k = 0; k < 1; k += Time.unscaledDeltaTime / 2.1f)
            {
                if (!chip) yield break;
                if (cam) chip.rotation = cam.transform.rotation;
                float s = k < .15f ? Mathf.Lerp(.2f, 1.1f, k / .15f) : k < .25f ? Mathf.Lerp(1.1f, 1f, (k - .15f) / .1f) : 1;
                chip.localScale = Vector3.one * s * (k > .85f ? Mathf.Lerp(1, 0, (k - .85f) / .15f) : 1);
                chip.position = from + Vector3.up * (1.3f * (1 - (1 - k) * (1 - k)));
                yield return null;
            }
            if (chip) Destroy(chip.gameObject);
        }

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
        /// <summary>A picture of the piece as it stands now (after the reveal), for the celebration card.</summary>
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
            try
            {
                cam.CopyFrom(main); cam.cullingMask = 1 << layer; cam.clearFlags = CameraClearFlags.SolidColor; cam.backgroundColor = new Color(0, 0, 0, 0);
                var dir = main.transform.forward; float r0 = b.extents.magnitude;
                cam.orthographic = true; cam.orthographicSize = r0 * 1.05f;
                go.transform.rotation = main.transform.rotation; go.transform.position = b.center - dir * (r0 * 4 + 5);
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
                Destroy(go);
            }
        }
    }
}
