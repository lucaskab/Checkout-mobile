using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Columbus Circle style roundabout at the west avenue junction. Vehicles circulate
    // counter-clockwise seen from above (right-hand traffic): any route that passes through the
    // circle is bent around the central island instead of crossing it.
    public class CheckoutRoundabout : MonoBehaviour
    {
        public Vector3 center = new Vector3(-23.5f, 0, -18.5f);
        public float islandRadius = 3.4f, outerRadius = 7.5f, travelRadius = 5.5f, clipRadius = 9f;

        static CheckoutRoundabout current;
        static bool searched;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() { current = null; searched = false; }
        void OnEnable() { current = this; searched = true; }
        void OnDisable() { if (current == this) { current = null; searched = false; } }

        public static CheckoutRoundabout Current
        {
            get
            {
                if (!current && !searched) { current = FindAnyObjectByType<CheckoutRoundabout>(); searched = true; }
                return current;
            }
        }

        public bool Inside(Vector3 p) { var d = p - center; d.y = 0; return d.magnitude < clipRadius; }

        // Points strictly between a and b (exclusive) that take a polyline around the island.
        // `through` lists interior polyline corners (inside the circle) that are replaced by the arc.
        public List<Vector3> Arc(Vector3 a, IList<Vector3> through, Vector3 b)
        {
            var result = new List<Vector3>();
            var line = new List<Vector3> { a };
            if (through != null) line.AddRange(through);
            line.Add(b);
            bool found = false; Vector3 entry = default, exit = default;
            for (int i = 0; i < line.Count - 1; i++)
            {
                if (!Intersections(line[i], line[i + 1], out float t0, out float t1)) continue;
                var p0 = Vector3.Lerp(line[i], line[i + 1], t0);
                var p1 = Vector3.Lerp(line[i], line[i + 1], t1);
                if (!found && t0 > 0f) { entry = p0; found = true; }
                else if (!found && !Inside(line[i])) { entry = p0; found = true; }
                if (found && t1 < 1f) exit = p1;
            }
            if (!found || exit == default) return result;
            float y = a.y;
            float start = Angle(entry), end = Angle(exit);
            float sweep = Mathf.Repeat(end - start, Mathf.PI * 2);
            if (sweep < .15f) return result; // Only grazes the edge: keep the straight line.
            result.Add(new Vector3(entry.x, y, entry.z));
            int steps = Mathf.Max(4, Mathf.CeilToInt(sweep / .2f));
            float ease = .5f; // Radians spent merging from the approach onto the travel radius.
            for (int s = 1; s < steps; s++)
            {
                float t = s / (float)steps, angle = start + sweep * t;
                float edge = Mathf.Min(sweep * t, sweep * (1 - t));
                float radius = Mathf.Lerp(clipRadius, travelRadius, Mathf.SmoothStep(0, 1, Mathf.Clamp01(edge / ease)));
                result.Add(new Vector3(center.x + Mathf.Cos(angle) * radius, y, center.z + Mathf.Sin(angle) * radius));
            }
            result.Add(new Vector3(exit.x, y, exit.z));
            return result;
        }

        float Angle(Vector3 p) => Mathf.Atan2(p.z - center.z, p.x - center.x);

        bool Intersections(Vector3 a, Vector3 b, out float t0, out float t1)
        {
            t0 = t1 = 0;
            var d = new Vector2(b.x - a.x, b.z - a.z); var f = new Vector2(a.x - center.x, a.z - center.z);
            float A = Vector2.Dot(d, d); if (A < 1e-6f) return false;
            float B = 2 * Vector2.Dot(f, d), C = Vector2.Dot(f, f) - clipRadius * clipRadius;
            float disc = B * B - 4 * A * C; if (disc <= 0) return false;
            disc = Mathf.Sqrt(disc);
            t0 = (-B - disc) / (2 * A); t1 = (-B + disc) / (2 * A);
            if (t1 < 0 || t0 > 1) return false;
            t0 = Mathf.Max(0, t0); t1 = Mathf.Min(1, t1);
            return true;
        }

        // Rewrites a simple driven polyline (no teleports) so every pass through the circle goes round it.
        public static Vector3[] Route(Vector3[] points)
        {
            var circle = Current;
            if (!circle || points == null || points.Length < 2) return points;
            var result = new List<Vector3>();
            for (int i = 0; i < points.Length; i++)
            {
                if (i > 0 && i < points.Length - 1 && circle.Inside(points[i])) continue;
                result.Add(points[i]);
                if (i == points.Length - 1) break;
                var inner = new List<Vector3>(); int j = i + 1;
                while (j < points.Length - 1 && circle.Inside(points[j])) inner.Add(points[j++]);
                result.AddRange(circle.Arc(points[i], inner, points[j]));
            }
            return result.ToArray();
        }
    }
}
