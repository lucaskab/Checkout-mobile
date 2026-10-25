using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    /// <summary>
    /// The skip (Works_Dumpster) of a lot being cleared fills up for real (Lucas 12/10: the rubble was dropped beside
    /// it and its fill stayed a thin layer): every load a hauler tips over the rim flies into the skip and stays there
    /// as a lump of rubble, layer by layer, until a mound rises above the rim. The countdown keeps a minimum
    /// (a lot opened half way through shows a half-full skip). The model's own flat "Fill" is hidden.
    /// </summary>
    public class CheckoutSkipLoad : MonoBehaviour
    {
        const int Cols = 3, Rows = 2, Layers = 4;
        Transform skip; Bounds inside; float rim;
        readonly List<Transform> lumps = new List<Transform>();
        readonly List<(Transform t, Vector3 from, Vector3 to, Quaternion spin, float time)> flying = new List<(Transform, Vector3, Vector3, Quaternion, float)>();
        int placed; System.Random rnd;

        public Vector3 Centre => inside.center;
        public Vector3 Position => skip ? skip.position : transform.position;
        /// <summary>Half the skip's size on the ground (to stand beside it).</summary>
        public float Radius => Mathf.Max(inside.extents.x, inside.extents.z) + .25f;

        public static CheckoutSkipLoad Attach(CheckoutWorksScene scene, Transform skip)
        {
            if (!scene || !skip) return null;
            var load = scene.gameObject.AddComponent<CheckoutSkipLoad>();
            load.skip = skip; load.rnd = new System.Random(skip.name.GetHashCode() ^ Mathf.RoundToInt(skip.position.x * 100));
            var fill = CheckoutWorksKit.FindPart(skip, "Fill");
            if (fill) fill.gameObject.SetActive(false);
            var b = CheckoutWorksKit.Bounds(skip.gameObject);
            load.rim = b.max.y;
            // The inside: the box a little in from the walls, from a floor just above the ground.
            var size = new Vector3(b.size.x * .74f, b.size.y, b.size.z * .74f);
            load.inside = new Bounds(new Vector3(b.center.x, b.min.y + b.size.y * .5f, b.center.z), size);
            scene.OnProgress(load.Progress);
            return load;
        }

        int Slots => Cols * Rows * Layers;

        // The countdown's minimum: a lot cleared half way shows a skip about half full.
        void Progress(float p)
        {
            int want = Mathf.FloorToInt(Mathf.Clamp01(p * 1.05f) * Slots * .85f);
            while (placed < want) Lump(null, false);
        }

        /// <summary>A hauler tips his load over the rim: it flies in and lands on the pile.</summary>
        public void Receive(Transform load)
        {
            if (!load) return;
            var from = load.position;
            load.gameObject.SetActive(false);
            Lump(from, true);
        }

        void Lump(Vector3? from, bool fly)
        {
            int i = placed;
            if (i >= Slots) { if (fly) Bump(); return; }
            placed++;
            int layer = i / (Cols * Rows), slot = i % (Cols * Rows), col = slot % Cols, row = slot / Cols;
            // Long side of the skip along its larger ground size.
            bool alongX = inside.size.x >= inside.size.z;
            float u = (col + .5f) / Cols - .5f + ((float)rnd.NextDouble() - .5f) * .12f;
            float v = (row + .5f) / Rows - .5f + ((float)rnd.NextDouble() - .5f) * .2f;
            float floor = inside.min.y + inside.size.y * .18f;
            float step = (rim - floor) / (Layers - .6f);
            float y = floor + layer * step * .9f;
            // The top layer heaps up in the middle.
            if (layer == Layers - 1) { u *= .7f; v *= .7f; y += step * .25f; }
            var at = new Vector3(inside.center.x + (alongX ? u * inside.size.x : v * inside.size.x), y, inside.center.z + (alongX ? v * inside.size.z : u * inside.size.z));
            var piece = CheckoutWorksKit.Spawn("Prop_Rubble", transform, at, Quaternion.Euler(0, (float)rnd.NextDouble() * 360f, 0) * Vector3.forward);
            float span = Mathf.Min(inside.size.x, inside.size.z);
            var pb = CheckoutWorksKit.Bounds(piece.gameObject);
            float fit = pb.size.x > 0 ? span * .62f / Mathf.Max(pb.size.x, pb.size.z) : 1;
            piece.localScale = Vector3.one * fit * (.9f + (float)rnd.NextDouble() * .3f);
            piece.name = "Skip rubble " + i;
            // Bits of the ruin itself on each load (its tiles, plaster, bricks), so the skip fills with that lot.
            lumps.Add(piece);
            DressLoads(GetComponent<CheckoutRuinDemolition>());
            if (fly && from.HasValue)
            {
                var to = piece.position; piece.position = from.Value;
                flying.Add((piece, from.Value, to, Random.rotation, 0));
            }
        }

        readonly HashSet<Transform> dressed = new HashSet<Transform>();
        /// <summary>Puts bits of the ruin on every load not dressed yet (once its pieces exist).</summary>
        public void DressLoads(CheckoutRuinDemolition demo)
        {
            if (!demo) return;
            foreach (var l in lumps)
            {
                if (!l || dressed.Contains(l)) continue;
                int before = l.childCount;
                demo.Dress(l, 4, .1f, .22f);
                if (l.childCount > before) dressed.Add(l);
            }
        }

        // The skip is full: the last loads just settle on the mound.
        void Bump()
        {
            if (lumps.Count == 0) return;
            var top = lumps[lumps.Count - 1 - rnd.Next(Mathf.Min(4, lumps.Count))];
            top.localScale *= 1.04f;
        }

        void Update()
        {
            for (int i = flying.Count - 1; i >= 0; i--)
            {
                var f = flying[i];
                if (!f.t) { flying.RemoveAt(i); continue; }
                f.time += Time.deltaTime / .55f;
                float k = Mathf.Clamp01(f.time);
                var p = Vector3.Lerp(f.from, f.to, k) + Vector3.up * Mathf.Sin(k * Mathf.PI) * .6f;
                f.t.position = p;
                f.t.rotation = Quaternion.Slerp(f.t.rotation, f.spin, Time.deltaTime * 3f);
                if (k >= 1) { f.t.position = f.to; flying.RemoveAt(i); continue; }
                flying[i] = f;
            }
        }

        void OnDestroy() { foreach (var l in lumps) if (l) Destroy(l.gameObject); }
    }
}
