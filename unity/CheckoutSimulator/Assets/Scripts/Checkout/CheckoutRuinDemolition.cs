using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Checkout
{
    /// <summary>
    /// The ruin of a lot comes down piece by piece while it is cleared (Lucas 12/10: the house used to shrink in place).
    /// When the clearing starts the ruin's meshes are cut into chunks on a grid (Resources/CheckoutLots models are
    /// imported readable for this). As the countdown goes on the chunks break off — the roof and the upper floor
    /// first, then the walls, the side facing the crew a little ahead of the back — each one on the next blow of a
    /// sledgehammer or a machine (or after a moment if no blow comes): it shakes, dust bursts, it tips and falls,
    /// lands in front of the ruin and crumbles into the rubble heaps there. The haulers take loads from the heaps to
    /// the skip (CheckoutSkipLoad). Overgrown or loose lots (Style.Cut) are cut and gathered instead: their chunks
    /// sink into the heaps without falling. Leaving the clearing puts the whole ruin back.
    /// </summary>
    public class CheckoutRuinDemolition : MonoBehaviour
    {
        public enum Style { Smash, Cut }

        class Chunk
        {
            public Transform t; public Vector3 home; public Quaternion homeRot; public float at; public float volume;
            public int state;            // 0 standing, 1 waiting for a blow, 2 shaking, 3 falling, 4 resting, 5 gone
            public float timer; public Vector3 velocity, spin; public float low, size;
            public Vector2[] colours; public Material material; public Bounds box;     // for the bits it sheds
        }

        // Small broken bits (bricks, tile, plaster) that fly off a piece when it gives way and when it lands.
        class Bit { public Transform t; public Mesh mesh; public Vector3 velocity, spin; public float life; public int bounces; }
        readonly List<Bit> bits = new List<Bit>();

        /// <summary>A heap of rubble in front of the ruin (grows with what falls, shrinks with every load taken away).</summary>
        public class Heap { public Transform t; public Vector3 at; public float volume, full; public Vector3 baseScale; }

        readonly List<Chunk> chunks = new List<Chunk>();
        readonly List<Renderer> originals = new List<Renderer>();
        readonly List<Mesh> meshes = new List<Mesh>();
        public readonly List<Heap> Heaps = new List<Heap>();
        CheckoutWorksScene scene; Transform ruin, broken; Style style;
        Vector3 crew; float ground, last = -1, height = 4, totalVolume = 1;
        bool built;

        /// <summary>Cuts the ruin into chunks and lays out the rubble heaps on the crew's side
        /// (`towardCrew`: the horizontal direction from the ruin to where the crew works).</summary>
        public void Begin(CheckoutWorksScene works, Transform ruinRoot, Vector3 towardCrew, Style how)
        {
            scene = works; ruin = ruinRoot; style = how; crew = CheckoutWorksKit.Flat(towardCrew);
            if (scene) { scene.Blow += OnBlow; scene.WorkAt = WorkPoint; }
            var watch = System.Diagnostics.Stopwatch.StartNew();
            built = Fracture();
            Debug.Log("CHECKOUT_RUIN_FRACTURE_MS " + (ruin ? ruin.name : "-") + " " + watch.ElapsedMilliseconds);
            if (!built) return;
            var b = Bounds();
            // Two heaps at the front corners of the ruin, clear of the crew working on its face (the haulers then
            // never walk into the sledgehammers).
            var side = Vector3.Cross(Vector3.up, crew);
            float halfFront = Mathf.Abs(Vector3.Dot(b.extents, new Vector3(Mathf.Abs(crew.x), 0, Mathf.Abs(crew.z))));
            float halfSide = Mathf.Abs(Vector3.Dot(b.extents, new Vector3(Mathf.Abs(side.x), 0, Mathf.Abs(side.z))));
            foreach (float k in new[] { -1f, 1f })
            {
                var at = b.center + crew * (halfFront - .2f) + side * (k * (halfSide + .35f));
                at.y = ground;
                var heap = new Heap { at = at, full = totalVolume * .5f };
                heap.t = CheckoutWorksKit.Spawn(style == Style.Cut ? "Prop_GreenWaste" : "Prop_DebrisPile", scene ? scene.transform : transform, at, -crew);
                heap.baseScale = heap.t.localScale;
                heap.t.gameObject.SetActive(false);
                Heaps.Add(heap);
            }
        }

        // ------------------------------------------------------------------ the chunks
        // Lucas 12/10 (2nd look): the pieces came off like paper cut with a knife — the lot models are built of big
        // flat boxes whose faces are single long triangles, so a grid of cells sliced them along straight lines and
        // each wall face fell as a sheet; the underside of the roof (in shadow, black) stayed up after the roof went.
        // Now the faces are first cut into small triangles, the pieces are irregular cells (jittered seeds, a noisy
        // border), the two faces of a wall or a roof plate always go together (each triangle is placed by the middle of
        // its plate), every piece gets a rough broken edge as thick as its wall, and a dark inner box (the "inner"
        // parts that fill the windows) is put away for the clearing.
        struct V { public Vector3 p, n; public Vector2 uv; }
        struct Tri { public V a, b, c; public int part; public float thick; }

        static V Mid(V a, V b) => new V { p = (a.p + b.p) * .5f, n = (a.n + b.n).normalized, uv = (a.uv + b.uv) * .5f };

        // Longest-edge bisection until no edge is longer than the piece size allows (same winding as the source).
        static void Split(V a, V b, V c, float max2, int depth, int part, float thick, List<Tri> into)
        {
            float ab = (a.p - b.p).sqrMagnitude, bc = (b.p - c.p).sqrMagnitude, ca = (c.p - a.p).sqrMagnitude;
            float m = Mathf.Max(ab, Mathf.Max(bc, ca));
            if (m <= max2 || depth >= 12 || into.Count > 60000) { into.Add(new Tri { a = a, b = b, c = c, part = part, thick = thick }); return; }
            if (m == ab) { var d = Mid(a, b); Split(a, d, c, max2, depth + 1, part, thick, into); Split(d, b, c, max2, depth + 1, part, thick, into); }
            else if (m == bc) { var d = Mid(b, c); Split(a, b, d, max2, depth + 1, part, thick, into); Split(a, d, c, max2, depth + 1, part, thick, into); }
            else { var d = Mid(c, a); Split(a, b, d, max2, depth + 1, part, thick, into); Split(d, b, c, max2, depth + 1, part, thick, into); }
        }

        static Vector3Int Q(Vector3 p) => new Vector3Int(Mathf.RoundToInt(p.x * 500), Mathf.RoundToInt(p.y * 500), Mathf.RoundToInt(p.z * 500));

        bool Fracture()
        {
            if (!ruin) return false;
            var filters = new List<MeshFilter>();
            foreach (var mf in ruin.GetComponentsInChildren<MeshFilter>(false))
            {
                var r = mf.GetComponent<MeshRenderer>();
                if (!mf.sharedMesh || !r || !r.enabled) continue;
                if (mf.name.ToLowerInvariant().Contains("inner")) { r.enabled = false; originals.Add(r); continue; }
                if (!mf.sharedMesh.isReadable) { Debug.LogWarning("CHECKOUT_RUIN_NOT_READABLE " + mf.sharedMesh.name); foreach (var o in originals) o.enabled = true; originals.Clear(); return false; }
                filters.Add(mf);
            }
            if (filters.Count == 0) return false;
            var all = new Bounds(); bool any = false;
            foreach (var mf in filters)
            {
                var wb = mf.GetComponent<Renderer>().bounds;
                if (!any) { all = wb; any = true; } else all.Encapsulate(wb);
            }
            ground = all.min.y; height = Mathf.Max(.5f, all.size.y);
            float cell = Mathf.Clamp(Mathf.Max(all.size.x, all.size.z) / 6f, .55f, 1.2f);
            float rise = Mathf.Clamp(all.size.y / 5f, .45f, .95f);
            float piece = Mathf.Min(.32f, cell * .3f);

            // Parts: (filter, submesh) -> material slot of the chunks.
            var parts = new List<Material>(); var partIndex = new Dictionary<(int, int), int>();
            var tris = new List<Tri>();
            for (int f = 0; f < filters.Count; f++)
            {
                var mf = filters[f]; var mesh = mf.sharedMesh; var m = mf.transform.localToWorldMatrix;
                var v = mesh.vertices; var n = mesh.normals; var uv = mesh.uv;
                // How thick this part is (a wall, a roof plate, a tile): its thinnest side.
                // (in the part's own axes: a tilted roof plate is thin even though its box in the world is not)
                var ls = Vector3.Scale(mesh.bounds.size, mf.transform.lossyScale);
                float thick = Mathf.Min(Mathf.Abs(ls.x), Mathf.Min(Mathf.Abs(ls.y), Mathf.Abs(ls.z)));
                var rm = mf.GetComponent<Renderer>().sharedMaterials;
                for (int sm = 0; sm < mesh.subMeshCount; sm++)
                {
                    if (!partIndex.TryGetValue((f, sm), out int part))
                    {
                        part = parts.Count; partIndex[(f, sm)] = part;
                        parts.Add(rm.Length > 0 ? rm[Mathf.Min(sm, rm.Length - 1)] : null);
                    }
                    var t = mesh.GetTriangles(sm);
                    for (int i = 0; i < t.Length; i += 3)
                    {
                        V Vx(int k) => new V { p = m.MultiplyPoint3x4(v[k]), n = n.Length == v.Length ? m.MultiplyVector(n[k]).normalized : Vector3.up, uv = uv.Length > k ? uv[k] : Vector2.zero };
                        Split(Vx(t[i]), Vx(t[i + 1]), Vx(t[i + 2]), piece * piece, 0, part, thick, tris);
                    }
                }
            }

            // Jittered seeds, one per cell of a coarse grid, each with its own wobble on the border.
            var rnd = new System.Random(Mathf.RoundToInt(ruin.position.x * 100 + ruin.position.z * 7));
            float R() => (float)rnd.NextDouble();
            var seeds = new Dictionary<Vector3Int, (Vector3 at, Vector2 wobble)>();
            Vector3Int Cell(Vector3 p) => new Vector3Int(Mathf.FloorToInt((p.x - all.min.x) / cell), Mathf.FloorToInt((p.y - all.min.y) / rise), Mathf.FloorToInt((p.z - all.min.z) / cell));
            (Vector3 at, Vector2 wobble) Seed(Vector3Int c)
            {
                if (!seeds.TryGetValue(c, out var s))
                    seeds[c] = s = (all.min + new Vector3((c.x + .15f + .7f * R()) * cell, (c.y + .15f + .7f * R()) * rise, (c.z + .15f + .7f * R()) * cell), new Vector2(R() * 100, R() * 100));
                return s;
            }
            float vScale = cell / rise;
            Vector3Int Owner(Vector3 p)
            {
                var c = Cell(p); var best = c; float d = float.MaxValue;
                for (int x = -1; x <= 1; x++) for (int y = -1; y <= 1; y++) for (int z = -1; z <= 1; z++)
                {
                    var k = new Vector3Int(c.x + x, c.y + y, c.z + z); var s = Seed(k);
                    var o = p - s.at; o.y *= vScale;
                    float wob = Mathf.PerlinNoise(p.x * 2.3f + s.wobble.x, (p.z + p.y * .7f) * 2.3f + s.wobble.y);
                    float e = o.magnitude * (.72f + .56f * wob);
                    if (e < d) { d = e; best = k; }
                }
                return best;
            }

            // Each triangle goes to the piece of the middle of its plate (both faces of a wall land together).
            var groups = new Dictionary<Vector3Int, List<int>>();
            for (int i = 0; i < tris.Count; i++)
            {
                var t = tris[i];
                var fn = Vector3.Cross(t.b.p - t.a.p, t.c.p - t.a.p);
                fn = fn.sqrMagnitude > 1e-12f ? fn.normalized : t.a.n;
                var mid = (t.a.p + t.b.p + t.c.p) / 3f - fn * Mathf.Min(.2f, t.thick * .5f);
                var key = Owner(mid);
                if (!groups.TryGetValue(key, out var list)) groups[key] = list = new List<int>();
                list.Add(i);
            }

            broken = new GameObject("Broken ruin").transform; broken.SetParent(ruin, false);
            foreach (var pair in groups)
            {
                if (pair.Value.Count == 0) continue;
                var verts = new List<Vector3>(); var norms = new List<Vector3>(); var uvs = new List<Vector2>();
                var subs = new Dictionary<int, List<int>>();
                var cb = new Bounds(tris[pair.Value[0]].a.p, Vector3.zero);
                // Edges of the piece by position: an edge used once is on its border (or the model's own edge).
                var edges = new Dictionary<(Vector3Int, Vector3Int), int>();
                var edgeOf = new List<(V a, V b, Vector3 fn, Vector3 centre, float depth, int part)>();
                foreach (int i in pair.Value)
                {
                    var t = tris[i];
                    if (!subs.TryGetValue(t.part, out var list)) subs[t.part] = list = new List<int>();
                    int b0 = verts.Count;
                    foreach (var x in new[] { t.a, t.b, t.c }) { verts.Add(x.p); norms.Add(x.n); uvs.Add(x.uv); cb.Encapsulate(x.p); }
                    list.Add(b0); list.Add(b0 + 1); list.Add(b0 + 2);
                    var fn = Vector3.Cross(t.b.p - t.a.p, t.c.p - t.a.p); fn = fn.sqrMagnitude > 1e-12f ? fn.normalized : t.a.n;
                    var centre = (t.a.p + t.b.p + t.c.p) / 3f;
                    float depth = Mathf.Clamp(t.thick * .5f, .015f, .13f);
                    void E(V a, V b)
                    {
                        Vector3Int qa = Q(a.p), qb = Q(b.p);
                        var k = (qa.x < qb.x || (qa.x == qb.x && (qa.y < qb.y || (qa.y == qb.y && qa.z <= qb.z)))) ? (qa, qb) : (qb, qa);
                        if (edges.TryGetValue(k, out int idx)) { edges[k] = -1; return; }
                        edges[k] = edgeOf.Count; edgeOf.Add((a, b, fn, centre, depth, t.part));
                    }
                    E(t.a, t.b); E(t.b, t.c); E(t.c, t.a);
                }
                // The broken edge: a strip going into the wall from every border edge, so a piece (and the hole it
                // leaves) shows the thickness of the wall instead of a paper-thin cut.
                foreach (var kv in edges)
                {
                    if (kv.Value < 0) continue;
                    var e = edgeOf[kv.Value];
                    var dir = e.b.p - e.a.p; if (dir.sqrMagnitude < 1e-8f) continue;
                    var mid = (e.a.p + e.b.p) * .5f;
                    var outward = mid - e.centre; outward -= Vector3.Dot(outward, dir.normalized) * dir.normalized; outward -= Vector3.Dot(outward, e.fn) * e.fn;
                    if (outward.sqrMagnitude < 1e-10f) continue; outward.Normalize();
                    // A rough edge: the inner side of the strip wanders a little.
                    float j1 = .7f + .6f * Mathf.PerlinNoise(e.a.p.x * 7f, e.a.p.z * 7f + e.a.p.y * 5f), j2 = .7f + .6f * Mathf.PerlinNoise(e.b.p.x * 7f, e.b.p.z * 7f + e.b.p.y * 5f);
                    Vector3 p0 = e.a.p, p1 = e.b.p, p2 = e.b.p - e.fn * e.depth * j2 + outward * e.depth * .25f * (j2 - .7f), p3 = e.a.p - e.fn * e.depth * j1 + outward * e.depth * .25f * (j1 - .7f);
                    int b0 = verts.Count;
                    verts.Add(p0); verts.Add(p1); verts.Add(p2); verts.Add(p3);
                    for (int k = 0; k < 4; k++) norms.Add(outward);
                    // Its colour: the face it breaks from, a little further in.
                    uvs.Add(e.a.uv); uvs.Add(e.b.uv); uvs.Add(Vector2.Lerp(e.b.uv, e.a.uv, .1f)); uvs.Add(Vector2.Lerp(e.a.uv, e.b.uv, .1f));
                    if (!subs.TryGetValue(e.part, out var list)) subs[e.part] = list = new List<int>();
                    bool facing = Vector3.Dot(Vector3.Cross(p1 - p0, p2 - p0), outward) > 0;
                    if (facing) { list.Add(b0); list.Add(b0 + 1); list.Add(b0 + 2); list.Add(b0); list.Add(b0 + 2); list.Add(b0 + 3); }
                    else { list.Add(b0); list.Add(b0 + 2); list.Add(b0 + 1); list.Add(b0); list.Add(b0 + 3); list.Add(b0 + 2); }
                }
                var go = new GameObject("Chunk " + pair.Key); go.layer = ruin.gameObject.layer;
                go.transform.SetParent(broken, false);
                go.transform.position = new Vector3(cb.center.x, cb.min.y, cb.center.z);
                go.transform.rotation = Quaternion.identity; go.transform.localScale = Vector3.one;
                var w2l = go.transform.worldToLocalMatrix;
                for (int i = 0; i < verts.Count; i++) { verts[i] = w2l.MultiplyPoint3x4(verts[i]); norms[i] = w2l.MultiplyVector(norms[i]).normalized; }
                var chunkMesh = new Mesh { name = "Ruin chunk", indexFormat = verts.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                chunkMesh.SetVertices(verts); chunkMesh.SetNormals(norms); chunkMesh.SetUVs(0, uvs);
                chunkMesh.subMeshCount = subs.Count;
                var mats = new List<Material>(); int si = 0;
                foreach (var sub in subs) { chunkMesh.SetTriangles(sub.Value, si++); mats.Add(parts[sub.Key]); }
                chunkMesh.RecalculateBounds();
                meshes.Add(chunkMesh);
                go.AddComponent<MeshFilter>().sharedMesh = chunkMesh;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = mats.ToArray(); mr.shadowCastingMode = ShadowCastingMode.On;
                float h = (cb.center.y - all.min.y) / height;
                float fr = Vector3.Dot(cb.center - all.center, crew) / Mathf.Max(.5f, Mathf.Max(all.extents.x, all.extents.z));
                var sample = new Vector2[Mathf.Min(6, uvs.Count)];
                for (int k = 0; k < sample.Length; k++) sample[k] = uvs[rnd.Next(uvs.Count)];
                chunks.Add(new Chunk
                {
                    t = go.transform, home = go.transform.localPosition, homeRot = go.transform.localRotation,
                    volume = cb.size.x * cb.size.z * Mathf.Max(.2f, cb.size.y), low = cb.min.y - all.min.y, size = Mathf.Max(.2f, cb.size.magnitude * .5f),
                    at = h + fr * .3f + R() * .12f,          // sort key for now: high and front first
                    colours = sample, material = mats.Count > 0 ? mats[0] : null, box = cb,
                });
            }
            if (chunks.Count == 0) { Destroy(broken.gameObject); foreach (var o in originals) if (o) o.enabled = true; originals.Clear(); return false; }
            // Order: the highest (and front) pieces come down first; the foundations last, when the lot is all but clear.
            chunks.Sort((a, b) => b.at.CompareTo(a.at));
            totalVolume = 0; foreach (var c in chunks) totalVolume += c.volume;
            for (int i = 0; i < chunks.Count; i++) chunks[i].at = Mathf.Lerp(.03f, .93f, chunks.Count == 1 ? 0 : (float)i / (chunks.Count - 1));
            foreach (var mf in filters) { var r = mf.GetComponent<Renderer>(); r.enabled = false; originals.Add(r); }
            Debug.Log("CHECKOUT_RUIN_FRACTURE " + ruin.name + " pieces " + chunks.Count + " triangles " + tris.Count);
            return true;
        }

        Bounds Bounds()
        {
            var b = new Bounds(); bool any = false;
            foreach (var c in chunks) { var r = c.t.GetComponent<Renderer>().bounds; if (!any) { b = r; any = true; } else b.Encapsulate(r); }
            return b;
        }

        // ------------------------------------------------------------------ the countdown
        /// <summary>Called by the works scene with its progress (0..1).</summary>
        public void SetProgress(float p)
        {
            if (!built) return;
            bool first = last < 0; last = p;
            foreach (var c in chunks)
            {
                if (c.state != 0 || p < c.at) continue;
                if (first || p > c.at + .08f)
                {
                    // Opening a lot that was already being cleared (or a jump in time): what came down is gone already,
                    // and the latest part of it waits in the heaps.
                    c.state = 5; c.t.gameObject.SetActive(false);
                    if (p - c.at < .2f) AddRubble(c.volume * .5f, c.t.position);
                    continue;
                }
                c.state = 1; c.timer = 0;
            }
        }

        // A sledgehammer (or a machine) hits the ruin: the next piece waiting gives way.
        void OnBlow(Vector3 at)
        {
            Chunk best = null; float near = float.MaxValue;
            foreach (var c in chunks)
            {
                if (c.state != 1) continue;
                float d = (c.t.position - at).sqrMagnitude;
                if (d < near) { near = d; best = c; }
            }
            if (best != null) Break(best);
        }

        void Break(Chunk c)
        {
            c.state = 2; c.timer = 0;
            if (scene) scene.Burst(c.t.position + Vector3.up * c.size * .5f, style == Style.Cut ? 2 : 5);
            if (style == Style.Smash) Shed(c, c.box.center, UnityEngine.Random.Range(6, 10), .8f);
        }

        // Bits of the piece, coloured like it (each takes one spot of the piece's texture), thrown off at `from`.
        void Shed(Chunk c, Vector3 from, int count, float force)
        {
            if (!c.material || c.colours == null || c.colours.Length == 0 || bits.Count > 90) return;
            for (int i = 0; i < count; i++)
            {
                var uv = c.colours[UnityEngine.Random.Range(0, c.colours.Length)];
                var mesh = Rock(uv, UnityEngine.Random.Range(.06f, .16f));
                var go = new GameObject("Ruin bit"); go.layer = ruin ? ruin.gameObject.layer : 0;
                go.transform.SetParent(broken ? broken : transform, false);
                var e = c.box.extents;
                go.transform.position = from + new Vector3(UnityEngine.Random.Range(-e.x, e.x), UnityEngine.Random.Range(-e.y, e.y) * .6f, UnityEngine.Random.Range(-e.z, e.z)) * .7f;
                go.transform.rotation = UnityEngine.Random.rotation;
                go.AddComponent<MeshFilter>().sharedMesh = mesh;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterial = c.material; mr.shadowCastingMode = ShadowCastingMode.Off;
                var away = CheckoutWorksKit.Flat(go.transform.position - CentreFloor()) * .8f + crew * .7f + UnityEngine.Random.insideUnitSphere * .6f;
                away.y = 0;
                bits.Add(new Bit
                {
                    t = go.transform, mesh = mesh, life = 0,
                    velocity = (away * UnityEngine.Random.Range(.8f, 2.2f) + Vector3.up * UnityEngine.Random.Range(.8f, 2.6f)) * force,
                    spin = UnityEngine.Random.onUnitSphere * UnityEngine.Random.Range(200f, 600f),
                });
            }
        }

        // A lumpy little stone: a box with its corners pushed about, flat-shaded, one colour of the texture.
        static Mesh Rock(Vector2 uv, float size)
        {
            var corners = new Vector3[8];
            for (int i = 0; i < 8; i++)
                corners[i] = new Vector3((i & 1) == 0 ? -1 : 1, (i & 2) == 0 ? -.7f : .7f, (i & 4) == 0 ? -1 : 1) * size * .5f
                    + UnityEngine.Random.insideUnitSphere * size * .22f;
            int[][] faces = { new[] { 0, 2, 3, 1 }, new[] { 4, 5, 7, 6 }, new[] { 0, 1, 5, 4 }, new[] { 2, 6, 7, 3 }, new[] { 0, 4, 6, 2 }, new[] { 1, 3, 7, 5 } };
            var v = new List<Vector3>(); var t = new List<int>();
            foreach (var f in faces)
            {
                int b = v.Count; foreach (int k in f) v.Add(corners[k]);
                var centre = (v[b] + v[b + 1] + v[b + 2] + v[b + 3]) * .25f;
                bool outward = Vector3.Dot(Vector3.Cross(v[b + 1] - v[b], v[b + 2] - v[b]), centre) > 0;
                t.AddRange(outward ? new[] { b, b + 1, b + 2, b, b + 2, b + 3 } : new[] { b, b + 2, b + 1, b, b + 3, b + 2 });
            }
            var m = new Mesh { name = "Ruin bit" };
            m.SetVertices(v); m.SetTriangles(t, 0);
            var uvs = new Vector2[v.Count]; for (int i = 0; i < uvs.Length; i++) uvs[i] = uv; m.uv = uvs;
            m.RecalculateNormals(); m.RecalculateBounds();
            return m;
        }

        void Bits(float dt)
        {
            for (int i = bits.Count - 1; i >= 0; i--)
            {
                var b = bits[i];
                if (!b.t) { bits.RemoveAt(i); continue; }
                b.life += dt;
                if (b.bounces < 2)
                {
                    b.velocity += Physics.gravity * dt;
                    b.t.position += b.velocity * dt;
                    b.t.rotation = Quaternion.Euler(b.spin * dt) * b.t.rotation;
                    if (b.t.position.y <= ground + .03f && b.velocity.y < 0)
                    {
                        b.t.position = new Vector3(b.t.position.x, ground + .03f, b.t.position.z);
                        b.velocity = new Vector3(b.velocity.x * .35f, -b.velocity.y * .25f, b.velocity.z * .35f); b.spin *= .3f;
                        b.bounces++; if (b.bounces >= 2) b.life = 0;
                    }
                }
                else
                {
                    // Lies a moment, then sinks away (it is part of the heap now).
                    if (b.life > 1.6f) b.t.localScale = Vector3.one * Mathf.Clamp01(1 - (b.life - 1.6f) / .5f);
                    if (b.life > 2.1f || b.t.localScale.x < .02f) { Destroy(b.t.gameObject); Destroy(b.mesh); bits.RemoveAt(i); continue; }
                }
                if (b.life > 6f) { Destroy(b.t.gameObject); Destroy(b.mesh); bits.RemoveAt(i); }
            }
        }

        /// <summary>For the roaming sledgehammers (CheckoutWorksScene.WorkAt): a piece still standing low enough to
        /// reach that comes down soon, near `from` if there is one.</summary>
        public Vector3 WorkPoint(Vector3 from)
        {
            Chunk best = null; float score = float.MaxValue; int seen = 0;
            foreach (var c in chunks)
            {
                if (c.state >= 2) continue;
                if (c.low > 1.8f) continue;
                float d = Vector3.Distance(new Vector3(c.t.position.x, 0, c.t.position.z), new Vector3(from.x, 0, from.z)) + UnityEngine.Random.value * 1.5f;
                if (d < score) { score = d; best = c; }
                if (++seen >= 10) break;
            }
            return best != null ? best.box.center : from;
        }

        void Update()
        {
            if (!built) return;
            float dt = Time.deltaTime;
            Bits(dt);
            foreach (var c in chunks)
            {
                switch (c.state)
                {
                    case 1:                 // waits for a blow, gives way on its own after a moment
                        if ((c.timer += dt) > 1.6f) Break(c);
                        break;
                    case 2:                 // shakes, cracks
                    {
                        c.timer += dt;
                        float a = Mathf.Sin(c.timer * 70f) * .04f * (1 - c.timer / .45f);
                        c.t.localPosition = c.home + new Vector3(a, 0, -a * .6f);
                        if (c.timer < .45f) break;
                        c.t.localPosition = c.home; c.timer = 0; c.state = 3;
                        if (style == Style.Cut) break;
                        var away = CheckoutWorksKit.Flat(c.t.position - CentreFloor()) * .9f + crew * .5f;
                        // It crumbles off rather than flying like a sheet: a short drop with a slow tip, shedding bits.
                        c.velocity = away * UnityEngine.Random.Range(.3f, .75f) + Vector3.up * UnityEngine.Random.Range(.15f, .7f);
                        c.spin = Vector3.Cross(Vector3.up, away.normalized) * UnityEngine.Random.Range(40f, 110f) + UnityEngine.Random.onUnitSphere * 20f;
                        break;
                    }
                    case 3:                 // falls (or, cut, sinks into a bundle)
                    {
                        c.timer += dt;
                        if (style == Style.Cut)
                        {
                            float k = Mathf.Clamp01(c.timer / .8f);
                            c.t.localScale = Vector3.one * Mathf.Lerp(1, .05f, k * k);
                            if (k >= 1) Settle(c);
                            break;
                        }
                        c.velocity += Physics.gravity * dt;
                        c.t.position += c.velocity * dt;
                        c.t.localScale = Vector3.one * Mathf.Lerp(1f, .8f, Mathf.Clamp01(c.timer / .7f));
                        if (UnityEngine.Random.value < dt * 6f) Shed(c, c.t.position + Vector3.up * c.size * .4f, 1, .4f);
                        c.t.rotation = Quaternion.Euler(c.spin * dt) * c.t.rotation;
                        if (c.t.position.y <= ground + .02f && c.velocity.y < 0)
                        {
                            c.t.position = new Vector3(c.t.position.x, ground + .02f, c.t.position.z);
                            if (scene) scene.Burst(c.t.position, 4);
                            // It shatters on the ground: more bits, and what is left is smaller.
                            Shed(c, c.t.position + Vector3.up * .15f, UnityEngine.Random.Range(3, 6), .55f);
                            c.t.localScale = Vector3.one * .8f;
                            c.state = 4; c.timer = 0;
                        }
                        break;
                    }
                    case 4:                 // lies there a moment, then crumbles into the heap
                    {
                        c.timer += dt;
                        if (c.timer < .7f) break;
                        float k = Mathf.Clamp01((c.timer - .7f) / .6f);
                        c.t.localScale = Vector3.one * Mathf.Lerp(.8f, .05f, k);
                        c.t.position += Vector3.down * dt * .4f;
                        if (k >= 1) Settle(c);
                        break;
                    }
                }
            }
            // The heaps grow and shrink smoothly with what they hold.
            foreach (var h in Heaps)
            {
                if (!h.t) continue;
                float k = h.full > 0 ? Mathf.Clamp01(h.volume / h.full) : 0;
                bool show = k > .01f;
                if (h.t.gameObject.activeSelf != show) h.t.gameObject.SetActive(show);
                var want = h.baseScale * (.35f + .85f * Mathf.Sqrt(k));
                h.t.localScale = Vector3.Lerp(h.t.localScale, want, dt * 4f);
            }
        }

        Vector3 CentreFloor() { var b = Bounds(); return new Vector3(b.center.x, ground, b.center.z); }

        void Settle(Chunk c)
        {
            c.state = 5; c.t.gameObject.SetActive(false);
            AddRubble(c.volume, c.t.position);
        }

        void AddRubble(float volume, Vector3 near)
        {
            Heap best = null; float d = float.MaxValue;
            foreach (var h in Heaps) { float e = (h.at - near).sqrMagnitude; if (e < d) { d = e; best = h; } }
            if (best != null) best.volume = Mathf.Min(best.full * 1.4f, best.volume + volume);
        }

        // ------------------------------------------------------------------ the haulers (CheckoutWorksScene.Hauler)
        /// <summary>Where a hauler loads next: the fullest heap (it stands on the crew's side of it).</summary>
        public Vector3 LoadPoint() => LoadPoint(-1);

        /// <summary>Hauler number `who` keeps to his own heap (two haulers never crowd the same one) unless it is
        /// empty and the other one has rubble.</summary>
        public Func<Vector3> LoadPointFor(int who) => () => LoadPoint(who);

        Vector3 LoadPoint(int who)
        {
            Heap best = null;
            if (who >= 0 && Heaps.Count > 0)
            {
                var own = Heaps[who % Heaps.Count];
                best = own;
                if (own.volume < totalVolume * .03f) foreach (var h in Heaps) if (h.volume > best.volume) best = h;
            }
            else foreach (var h in Heaps) if (best == null || h.volume > best.volume) best = h;
            var side = Vector3.Cross(Vector3.up, crew) * (who < 0 ? 0 : (who % 2 == 0 ? -.35f : .35f));
            return best == null ? transform.position : best.at + crew * .55f + side;
        }

        /// <summary>Where the heap the hauler loads from is (he faces it).</summary>
        public Vector3 HeapNear(Vector3 at)
        {
            Heap best = null; float d = float.MaxValue;
            foreach (var h in Heaps) { float e = (h.at - at).sqrMagnitude; if (e < d) { d = e; best = h; } }
            return best == null ? at : best.at;
        }

        /// <summary>A load is taken from the heap next to `at`.</summary>
        public void Take(Vector3 at)
        {
            Heap best = null; float d = float.MaxValue;
            foreach (var h in Heaps) { float e = (h.at - at).sqrMagnitude; if (e < d) { d = e; best = h; } }
            if (best != null) best.volume = Mathf.Max(0, best.volume - totalVolume * .035f);
        }

        void OnDestroy()
        {
            if (scene) { scene.Blow -= OnBlow; if (scene.WorkAt == (Func<Vector3, Vector3>)WorkPoint) scene.WorkAt = null; }
            foreach (var b in bits) { if (b.t) Destroy(b.t.gameObject); if (b.mesh) Destroy(b.mesh); }
            // Leaving the clearing (cancelled, or the scene goes away): the whole ruin stands again.
            foreach (var r in originals) if (r) r.enabled = true;
            if (broken) Destroy(broken.gameObject);
            foreach (var h in Heaps) if (h.t) Destroy(h.t.gameObject);
            foreach (var m in meshes) if (m) Destroy(m);
        }
    }
}
