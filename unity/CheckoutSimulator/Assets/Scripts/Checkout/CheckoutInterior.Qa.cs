using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    // QA (autotest "eventsangle"): stands any kit / tier model in the shop as a throwaway piece and measures how straight it
    // really looks: the yaw of its root against `rot`, the yaw of every child, and the angle of the outline of everything it
    // draws (minimum-area rectangle of the rendered vertices seen from above) against the shop's walls (world X / Z).
    public partial class CheckoutInterior
    {
        public struct Straightness
        {
            public float rootYaw, worstChildYaw, outlineAngle, outlineSaving; public string worstChild; public int vertices, unreadable;
            public Rect drawn, footprint;
        }

        public Item QaSpawn(string template, Vector3 world, float rot)
        {
            if (!TemplateObject(template)) return null;
            var it = new Item { id = "qa-angle:" + template, type = "qa", template = template, desired = template, placed = true, saved = true, rot = rot };
            if (items.TryGetValue(it.id, out var old) && old.root) Destroy(old.root.gameObject);
            Build(it); if (!it.root) return null;
            items[it.id] = it; MoveTo(it, world);
            return it;
        }

        public void QaDespawn(Item it)
        {
            if (it == null) return;
            if (it.root) Destroy(it.root.gameObject);
            items.Remove(it.id);
        }

        /// <summary>Angle (−45..45°) of `v` against the nearest world axis.</summary>
        public static float AxisOffset(float yaw) => Mathf.DeltaAngle(0, yaw) - Mathf.Round(Mathf.DeltaAngle(0, yaw) / 90f) * 90f;

        public Straightness QaMeasure(Item it)
        {
            var m = new Straightness { rootYaw = it.root.eulerAngles.y };
            // children: yaw of every upright transform against the piece's own turn
            float worst = 0;
            foreach (var t in it.root.GetComponentsInChildren<Transform>())
            {
                if (t == it.root || Vector3.Dot(t.up, Vector3.up) < .999f) continue;
                var f = t.forward; f.y = 0; if (f.sqrMagnitude < 1e-6f) continue;
                float d = AxisOffset(Quaternion.LookRotation(f).eulerAngles.y - it.rot);
                if (Mathf.Abs(d) > Mathf.Abs(worst)) { worst = d; m.worstChild = t.name; }
            }
            m.worstChildYaw = worst;
            // outline of what is drawn, seen from above (world space)
            var pts = new List<Vector2>();
            foreach (var r in it.root.GetComponentsInChildren<Renderer>())
            {
                if (!r.enabled || !r.gameObject.activeInHierarchy) continue;
                Mesh mesh = null;
                if (r is SkinnedMeshRenderer sk) mesh = sk.sharedMesh;
                else { var mf = r.GetComponent<MeshFilter>(); if (mf) mesh = mf.sharedMesh; }
                if (!mesh) continue;
                if (!mesh.isReadable && !Application.isEditor) { m.unreadable++; continue; }
                var l2w = r.transform.localToWorldMatrix;
                foreach (var v in mesh.vertices) { var w = l2w.MultiplyPoint3x4(v); pts.Add(new Vector2(w.x, w.z)); }
            }
            m.vertices = pts.Count;
            if (pts.Count >= 3)
            {
                var hull = Hull(pts);
                float bestArea = float.MaxValue, bestAngle = 0;
                for (int i = 0; i < hull.Count; i++)
                {
                    var e = hull[(i + 1) % hull.Count] - hull[i]; if (e.sqrMagnitude < 1e-8f) continue;
                    float a = Mathf.Atan2(e.y, e.x);
                    float area = RectArea(hull, a, out _, out _);
                    if (area < bestArea - 1e-6f) { bestArea = area; bestAngle = a * Mathf.Rad2Deg; }
                }
                float aabb = RectArea(hull, 0, out var mn, out var mx);
                m.outlineAngle = AxisOffset(bestAngle); m.outlineSaving = aabb > 0 ? 1 - bestArea / aabb : 0;
                m.drawn = Rect.MinMaxRect(mn.x, mn.y, mx.x, mx.y);
            }
            var fp = FootprintOf(it); m.footprint = Aabb(fp);
            return m;
        }

        static float RectArea(List<Vector2> hull, float a, out Vector2 min, out Vector2 max)
        {
            float c = Mathf.Cos(a), s = Mathf.Sin(a); min = new Vector2(float.MaxValue, float.MaxValue); max = -min;
            foreach (var p in hull) { var q = new Vector2(p.x * c + p.y * s, -p.x * s + p.y * c); min = Vector2.Min(min, q); max = Vector2.Max(max, q); }
            return (max.x - min.x) * (max.y - min.y);
        }

        static List<Vector2> Hull(List<Vector2> input)
        {
            var p = input.Select(v => new Vector2(Mathf.Round(v.x * 1000) / 1000, Mathf.Round(v.y * 1000) / 1000)).Distinct().OrderBy(v => v.x).ThenBy(v => v.y).ToList();
            if (p.Count < 3) return p;
            float Cross(Vector2 o, Vector2 a, Vector2 b) => (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
            var h = new List<Vector2>();
            foreach (var v in p) { while (h.Count >= 2 && Cross(h[h.Count - 2], h[h.Count - 1], v) <= 0) h.RemoveAt(h.Count - 1); h.Add(v); }
            int lower = h.Count + 1;
            for (int i = p.Count - 2; i >= 0; i--) { var v = p[i]; while (h.Count >= lower && Cross(h[h.Count - 2], h[h.Count - 1], v) <= 0) h.RemoveAt(h.Count - 1); h.Add(v); }
            h.RemoveAt(h.Count - 1);
            return h;
        }
    }
}
