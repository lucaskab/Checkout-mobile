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
        }

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
            if (scene) scene.Blow += OnBlow;
            built = Fracture();
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
        bool Fracture()
        {
            if (!ruin) return false;
            var filters = new List<MeshFilter>();
            foreach (var mf in ruin.GetComponentsInChildren<MeshFilter>(false))
            {
                var r = mf.GetComponent<MeshRenderer>();
                if (!mf.sharedMesh || !r || !r.enabled) continue;
                if (!mf.sharedMesh.isReadable) { Debug.LogWarning("CHECKOUT_RUIN_NOT_READABLE " + mf.sharedMesh.name); return false; }
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
            float cell = Mathf.Clamp(Mathf.Max(all.size.x, all.size.z) / 5f, .7f, 1.5f);
            float rise = Mathf.Clamp(all.size.y / 4f, .55f, 1.3f);
            Vector3Int Cell(Vector3 p) => new Vector3Int(Mathf.FloorToInt((p.x - all.min.x) / cell), Mathf.FloorToInt((p.y - all.min.y) / rise), Mathf.FloorToInt((p.z - all.min.z) / cell));

            // Triangles grouped by the cell of their centre: cell -> (source mesh, submesh) -> triangle indices.
            var groups = new Dictionary<Vector3Int, Dictionary<(int, int), List<int>>>();
            var worldVerts = new List<Vector3[]>(); var worldNormals = new List<Vector3[]>();
            for (int f = 0; f < filters.Count; f++)
            {
                var mesh = filters[f].sharedMesh; var m = filters[f].transform.localToWorldMatrix;
                var v = mesh.vertices; var n = mesh.normals;
                var wv = new Vector3[v.Length]; var wn = new Vector3[v.Length];
                for (int i = 0; i < v.Length; i++) { wv[i] = m.MultiplyPoint3x4(v[i]); wn[i] = n.Length == v.Length ? m.MultiplyVector(n[i]).normalized : Vector3.up; }
                worldVerts.Add(wv); worldNormals.Add(wn);
                for (int sm = 0; sm < mesh.subMeshCount; sm++)
                {
                    var tris = mesh.GetTriangles(sm);
                    for (int i = 0; i < tris.Length; i += 3)
                    {
                        var c = (wv[tris[i]] + wv[tris[i + 1]] + wv[tris[i + 2]]) / 3f;
                        var key = Cell(c);
                        if (!groups.TryGetValue(key, out var g)) groups[key] = g = new Dictionary<(int, int), List<int>>();
                        if (!g.TryGetValue((f, sm), out var list)) g[(f, sm)] = list = new List<int>();
                        list.Add(tris[i]); list.Add(tris[i + 1]); list.Add(tris[i + 2]);
                    }
                }
            }
            broken = new GameObject("Broken ruin").transform; broken.SetParent(ruin, false);
            var rnd = new System.Random(Mathf.RoundToInt(ruin.position.x * 100 + ruin.position.z * 7));
            foreach (var pair in groups)
            {
                // One chunk per cell; its submeshes keep the materials of the parts they came from.
                var verts = new List<Vector3>(); var norms = new List<Vector3>(); var uvs = new List<Vector2>();
                var subs = new List<List<int>>(); var mats = new List<Material>();
                var centre = Vector3.zero; int count = 0; var cb = new Bounds();
                foreach (var part in pair.Value)
                {
                    var mf = filters[part.Key.Item1]; var mesh = mf.sharedMesh;
                    var srcUv = mesh.uv; var wv = worldVerts[part.Key.Item1]; var wn = worldNormals[part.Key.Item1];
                    var map = new Dictionary<int, int>(); var tris = new List<int>();
                    foreach (int i in part.Value)
                    {
                        if (!map.TryGetValue(i, out int j))
                        {
                            j = verts.Count; map[i] = j;
                            verts.Add(wv[i]); norms.Add(wn[i]); uvs.Add(srcUv.Length > i ? srcUv[i] : Vector2.zero);
                            centre += wv[i]; if (count++ == 0) cb = new Bounds(wv[i], Vector3.zero); else cb.Encapsulate(wv[i]);
                        }
                        tris.Add(j);
                    }
                    subs.Add(tris);
                    var rm = mf.GetComponent<Renderer>().sharedMaterials;
                    mats.Add(rm.Length > 0 ? rm[Mathf.Min(part.Key.Item2, rm.Length - 1)] : null);
                }
                if (count < 3) continue;
                centre /= count;
                var go = new GameObject("Chunk " + pair.Key); go.layer = ruin.gameObject.layer;
                go.transform.SetParent(broken, false);
                go.transform.position = new Vector3(centre.x, cb.min.y, centre.z);
                go.transform.rotation = Quaternion.identity;
                var w2l = go.transform.worldToLocalMatrix;
                for (int i = 0; i < verts.Count; i++) { verts[i] = w2l.MultiplyPoint3x4(verts[i]); norms[i] = w2l.MultiplyVector(norms[i]).normalized; }
                var chunkMesh = new Mesh { name = "Ruin chunk", indexFormat = verts.Count > 65000 ? IndexFormat.UInt32 : IndexFormat.UInt16 };
                chunkMesh.SetVertices(verts); chunkMesh.SetNormals(norms); chunkMesh.SetUVs(0, uvs);
                chunkMesh.subMeshCount = subs.Count;
                for (int s = 0; s < subs.Count; s++) chunkMesh.SetTriangles(subs[s], s);
                chunkMesh.RecalculateBounds();
                meshes.Add(chunkMesh);
                go.AddComponent<MeshFilter>().sharedMesh = chunkMesh;
                var mr = go.AddComponent<MeshRenderer>(); mr.sharedMaterials = mats.ToArray(); mr.shadowCastingMode = ShadowCastingMode.On;
                float h = (cb.center.y - all.min.y) / height;
                float f = Vector3.Dot(cb.center - all.center, crew) / Mathf.Max(.5f, Mathf.Max(all.extents.x, all.extents.z));
                chunks.Add(new Chunk
                {
                    t = go.transform, home = go.transform.localPosition, homeRot = go.transform.localRotation,
                    volume = cb.size.x * cb.size.z * Mathf.Max(.2f, cb.size.y), low = cb.min.y - all.min.y, size = Mathf.Max(.2f, cb.size.magnitude * .5f),
                    at = h + f * .3f + (float)rnd.NextDouble() * .12f,          // sort key for now: high and front first
                });
            }
            if (chunks.Count == 0) { Destroy(broken.gameObject); return false; }
            // Order: the highest (and front) pieces come down first; the foundations last, when the lot is all but clear.
            chunks.Sort((a, b) => b.at.CompareTo(a.at));
            totalVolume = 0; foreach (var c in chunks) totalVolume += c.volume;
            for (int i = 0; i < chunks.Count; i++) chunks[i].at = Mathf.Lerp(.03f, .93f, chunks.Count == 1 ? 0 : (float)i / (chunks.Count - 1));
            foreach (var mf in filters) { var r = mf.GetComponent<Renderer>(); r.enabled = false; originals.Add(r); }
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
        }

        void Update()
        {
            if (!built) return;
            float dt = Time.deltaTime;
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
                        c.velocity = away * UnityEngine.Random.Range(.6f, 1.4f) + Vector3.up * UnityEngine.Random.Range(.4f, 1.6f);
                        c.spin = UnityEngine.Random.onUnitSphere * UnityEngine.Random.Range(90f, 260f);
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
                        c.t.rotation = Quaternion.Euler(c.spin * dt) * c.t.rotation;
                        if (c.t.position.y <= ground + .02f && c.velocity.y < 0)
                        {
                            c.t.position = new Vector3(c.t.position.x, ground + .02f, c.t.position.z);
                            if (scene) scene.Burst(c.t.position, 4);
                            c.state = 4; c.timer = 0;
                        }
                        break;
                    }
                    case 4:                 // lies there a moment, then crumbles into the heap
                    {
                        c.timer += dt;
                        if (c.timer < .7f) break;
                        float k = Mathf.Clamp01((c.timer - .7f) / .6f);
                        c.t.localScale = Vector3.one * Mathf.Lerp(1, .05f, k);
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
            if (scene) scene.Blow -= OnBlow;
            // Leaving the clearing (cancelled, or the scene goes away): the whole ruin stands again.
            foreach (var r in originals) if (r) r.enabled = true;
            if (broken) Destroy(broken.gameObject);
            foreach (var h in Heaps) if (h.t) Destroy(h.t.gameObject);
            foreach (var m in meshes) if (m) Destroy(m);
        }
    }
}
