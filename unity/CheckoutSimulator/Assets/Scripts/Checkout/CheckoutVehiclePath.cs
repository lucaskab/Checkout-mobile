using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // The one smooth path every driven vehicle follows (Lucas 26/10: "when the cars turn, at the roundabout or at the
    // corners, the curves aren't smooth, they look locked, like a badly made game").
    // Before, a vehicle moved point by point along its waypoint polyline while its body chased the new direction at a
    // fixed turn rate: at every corner it changed direction at once and slid sideways until the body caught up, then
    // snapped straight, slowing down by how far it was off. Now:
    // - the polyline's corners are rounded with circular arcs of a street radius (~5 m), never more than 45% of either
    //   leg, so the arc stays inside the corner and the lanes and stop lines between corners stay where they were;
    // - a polyline through the roundabout is bent round its island here: a gentle right turn onto the ring, a true circle
    //   at the travel radius (a polygon circumscribing it, each corner rounded at that radius, is exactly the circle), a
    //   right turn off it;
    // - it is sampled densely (0.25 m, at most 1.7 degrees apart on a bend) with the arc length, the direction and the
    //   curvature of every sample.
    // A vehicle advances a distance s along it: its position is the point at s and it faces the direction there, so the
    // body always points where it goes (no sliding, no snapping), and Allowed() limits its speed by the bends ahead
    // (v <= sqrt(a_lat * R), braking in time before them). A path is driven one way only: backing out of a bay, or onto a
    // truck bay, is a path of its own (the vehicle stops to change gear).
    // Building reuses the buffers (no garbage once they have grown); following allocates nothing.
    public sealed class CheckoutVehiclePath
    {
        public const float StreetRadius = 5f, Spacing = .25f, LateralAccel = 2.4f;
        // A right turn hugs the kerb corner (the lanes run ~1.2-1.5 m off the kerbs): a wide arc would cut across the
        // sidewalk, so a sharp right turn is tighter. Onto / off the roundabout the bends are a bit wider than a corner.
        const float RightRadius = 3.2f, RingBend = 6.5f;
        const float MaxStep = .03f, Share = .45f, RingStep = .45f;

        Vector3[] point = new Vector3[256], tangent = new Vector3[256];
        float[] at = new float[256], bend = new float[256];
        int count;
        float[] waypoint = new float[16]; int waypoints;
        // scratch for building
        readonly List<Vector3> work = new List<Vector3>(), bent = new List<Vector3>();
        readonly List<float> hint = new List<float>(), bentHint = new List<float>(), trim = new List<float>();
        readonly List<int> origin = new List<int>(), bentOrigin = new List<int>(), repeated = new List<int>(), skipped = new List<int>();
        readonly List<bool> rigid = new List<bool>();

        public int Count => count;
        public bool Ready => count >= 2;
        public float Length => count > 0 ? at[count - 1] : 0;
        public Vector3 End => count > 0 ? point[count - 1] : Vector3.zero;
        public Vector3 EndTangent => count > 0 ? tangent[count - 1] : Vector3.forward;
        /// <summary>How far along the path the vehicle passes input point `i` (the middle of its bend).</summary>
        public float WaypointAt(int i) => waypoints == 0 ? 0 : waypoint[Mathf.Clamp(i, 0, waypoints - 1)];
        public void Clear() { count = 0; waypoints = 0; }

        /// <summary>Builds the path through `points` (the first is where the vehicle stands). `heading`: the way the vehicle
        /// already faces, so a path rebuilt mid-drive carries on smoothly. `radius`: the street radius of its corners.
        /// `radii`: a fixed radius for some corners (> 0), e.g. a bend that has to end exactly where the path ends.</summary>
        public CheckoutVehiclePath Build(IList<Vector3> points, float radius = StreetRadius, Vector3? heading = null, bool roundabout = true, IList<float> radii = null)
        {
            Clear(); work.Clear(); hint.Clear(); origin.Clear(); repeated.Clear(); skipped.Clear();
            int input = points == null ? 0 : points.Count;
            Grow(ref waypoint, input); waypoints = input;
            for (int i = 0; i < input; i++) waypoint[i] = -1;
            for (int i = 0; i < input; i++)
            {
                var p = points[i];
                if (work.Count > 0 && Flat(p - work[work.Count - 1]).sqrMagnitude < 1e-6f) { repeated.Add(i); continue; } // the same corner again
                work.Add(p); hint.Add(radii != null && i < radii.Count ? radii[i] : 0); origin.Add(i);
            }
            if (work.Count < 2)
            {
                if (work.Count == 1) { Grow(1); point[0] = work[0]; tangent[0] = heading.HasValue ? Flat(heading.Value).normalized : Vector3.forward; at[0] = 0; bend[0] = 0; count = 1; }
                for (int i = 0; i < input; i++) waypoint[i] = 0;
                return this;
            }
            // Facing elsewhere than the first leg: a short lead-in along the current heading so the turn is a bend too. A
            // first point just behind the vehicle (stopped a little past it, e.g. a truck sent off before reaching its bay)
            // is skipped rather than turned round to.
            if (heading.HasValue)
            {
                var ahead = Flat(heading.Value);
                while (work.Count > 2 && Vector3.Dot(ahead, Flat(work[1] - work[0])) < 0 && Flat(work[1] - work[0]).sqrMagnitude < 9f)
                { skipped.Add(origin[1]); work.RemoveAt(1); hint.RemoveAt(1); origin.RemoveAt(1); }
                var h = Flat(heading.Value); var first = Flat(work[1] - work[0]);
                if (h.sqrMagnitude > 1e-6f && Vector3.Angle(h, first) > 2f)
                {
                    float lead = Mathf.Min(1.5f, first.magnitude * .35f);
                    work.Insert(1, work[0] + h.normalized * lead); hint.Insert(1, 0); origin.Insert(1, -1);
                }
            }
            if (roundabout) Bend(CheckoutRoundabout.Current);
            Round(radius);
            // A repeated point is passed with the one before it; points dropped inside the roundabout where the next kept one is.
            for (int i = input - 1, next = -1; i >= 0; i--) { if (waypoint[i] < 0 && !repeated.Contains(i)) waypoint[i] = next < 0 ? Length : waypoint[next]; else if (waypoint[i] >= 0) next = i; }
            foreach (int i in repeated) waypoint[i] = waypoint[i - 1];
            foreach (int i in skipped) waypoint[i] = 0;
            return this;
        }

        // ------------------------------------------------------------------ corners
        void Round(float radius)
        {
            int m = work.Count;
            trim.Clear(); rigid.Clear();
            for (int i = 0; i < m; i++) { trim.Add(0); rigid.Add(false); }
            // Wanted tangent length of every corner: radius * tan(turn / 2), capped by its two legs.
            for (int i = 1; i < m - 1; i++)
            {
                var a = Flat(work[i] - work[i - 1]); var b = Flat(work[i + 1] - work[i]);
                float la = a.magnitude, lb = b.magnitude; if (la < 1e-4f || lb < 1e-4f) continue;
                float turn = Vector3.Angle(a, b) * Mathf.Deg2Rad;
                if (turn < .005f || turn > 3.13f) continue; // straight on, or an exact reversal (never inside one run)
                bool fixedRadius = hint[i] > 0; float r = fixedRadius ? hint[i] : radius;
                if (!fixedRadius && Cross(a, b) < 0) r = Mathf.Lerp(r, Mathf.Min(r, RightRadius), Mathf.InverseLerp(.52f, 1.57f, turn));
                float t = r * Mathf.Tan(turn * .5f);
                if (!fixedRadius) t = Mathf.Min(t, la * Share, lb * Share);
                trim[i] = t; rigid[i] = fixedRadius;
            }
            // Two corners never share more than their leg: a fixed-radius corner keeps its arc, the other one gives way.
            for (int i = 0; i < m - 1; i++)
            {
                float len = Flat(work[i + 1] - work[i]).magnitude, sum = trim[i] + trim[i + 1];
                if (sum <= len) continue;
                if (rigid[i] && !rigid[i + 1]) trim[i + 1] = Mathf.Max(0, len - trim[i]);
                else if (rigid[i + 1] && !rigid[i]) trim[i] = Mathf.Max(0, len - trim[i + 1]);
                sum = trim[i] + trim[i + 1];
                if (sum > len) { float k = len / sum; trim[i] *= k; trim[i + 1] *= k; }
            }
            // Samples: straight from where the last bend ended to where the next one starts, then the bend.
            var cur = work[0]; var dir0 = Flat(work[1] - work[0]).normalized;
            Emit(cur, dir0, 0, true);
            for (int i = 1; i < m; i++)
            {
                var a = Flat(work[i] - work[i - 1]).normalized;
                var start = work[i] - a * trim[i];
                Straight(cur, start, a);
                if (trim[i] <= 1e-4f || i == m - 1) { Mark(i, at[count - 1]); cur = start; continue; }
                var b = Flat(work[i + 1] - work[i]).normalized;
                float turn = Vector3.Angle(a, b) * Mathf.Deg2Rad, r = trim[i] / Mathf.Tan(turn * .5f);
                float side = a.x * b.z - a.z * b.x > 0 ? 1 : -1; // > 0: a left turn (counter-clockwise seen from above)
                var normal = new Vector3(-a.z, 0, a.x) * side;
                var center = start + normal * r; var end = work[i] + b * trim[i];
                int steps = Mathf.Max(2, Mathf.CeilToInt(turn / Mathf.Min(Spacing / r, MaxStep)));
                float startS = at[count - 1];
                var arm = Flat(start - center);
                for (int k = 1; k <= steps; k++)
                {
                    float phi = turn * k / steps * side, c = Mathf.Cos(phi), s = Mathf.Sin(phi);
                    var q = center + new Vector3(arm.x * c - arm.z * s, 0, arm.x * s + arm.z * c);
                    q.y = Mathf.Lerp(start.y, end.y, k / (float)steps);
                    Emit(q, new Vector3(a.x * c - a.z * s, 0, a.x * s + a.z * c), 1f / r, false);
                }
                Mark(i, startS + r * turn * .5f);
                cur = end;
            }
            Mark(0, 0);
        }
        void Mark(int workIndex, float s) { int o = origin[workIndex]; if (o >= 0 && o < waypoints) waypoint[o] = s; }
        void Straight(Vector3 from, Vector3 to, Vector3 dir)
        {
            float len = Flat(to - from).magnitude; if (len < 1e-4f) return;
            int steps = Mathf.CeilToInt(len / Spacing);
            for (int k = 1; k <= steps; k++) Emit(Vector3.Lerp(from, to, k / (float)steps), dir, 0, false);
        }
        void Emit(Vector3 p, Vector3 dir, float curvature, bool first)
        {
            Grow(count + 1);
            point[count] = p; tangent[count] = dir; bend[count] = curvature;
            at[count] = first || count == 0 ? 0 : at[count - 1] + Flat(p - point[count - 1]).magnitude;
            count++;
        }
        void Grow(int n) { if (n <= point.Length) return; int size = Mathf.Max(n, point.Length * 2); System.Array.Resize(ref point, size); System.Array.Resize(ref tangent, size); System.Array.Resize(ref at, size); System.Array.Resize(ref bend, size); }
        static void Grow(ref float[] a, int n) { if (n > a.Length) System.Array.Resize(ref a, Mathf.Max(n, a.Length * 2)); }
        static Vector3 Flat(Vector3 v) { v.y = 0; return v; }
        static float Cross(Vector3 a, Vector3 b) => a.x * b.z - a.z * b.x;

        // ------------------------------------------------------------------ the roundabout
        // Every stretch of the polyline that crosses the circle is replaced by: the point where it turns off its lane, a
        // ring of corners circumscribing the travel circle (counter-clockwise, right-hand traffic) and the point where it
        // turns back onto its exit lane. The turns on and off are right turns of about the street radius, tangent to the
        // ring, so lane -> bend -> circle -> bend -> lane has no kink anywhere.
        void Bend(CheckoutRoundabout circle)
        {
            if (!circle) return;
            bent.Clear(); bentHint.Clear(); bentOrigin.Clear();
            int n = work.Count; bool changed = false;
            void Keep(int k) { bent.Add(work[k]); bentHint.Add(hint[k]); bentOrigin.Add(origin[k]); }
            Keep(0);
            int i = 0;
            while (i < n - 1)
            {
                int j = i + 1; while (j < n - 1 && circle.Inside(work[j])) j++;
                if (!circle.Inside(work[i]) && !circle.Inside(work[j]) && Crossing(circle, i, j, out var entry, out var u, out var exit, out var w)
                    && Ring(circle, entry, u, exit, w, Flat(entry - work[i]).magnitude - .5f, Flat(work[j] - exit).magnitude - .5f)) changed = true;
                else for (int k = i + 1; k < j; k++) Keep(k);
                Keep(j); i = j;
            }
            if (!changed) return;
            work.Clear(); work.AddRange(bent); hint.Clear(); hint.AddRange(bentHint); origin.Clear(); origin.AddRange(bentOrigin);
        }
        // Where the chain work[i..j] goes into the clip circle and where it comes out (with the directions of those legs).
        bool Crossing(CheckoutRoundabout circle, int i, int j, out Vector3 entry, out Vector3 u, out Vector3 exit, out Vector3 w)
        {
            entry = exit = u = w = Vector3.zero; bool found = false, left = false;
            for (int k = i; k < j; k++)
            {
                if (!Hits(circle, work[k], work[k + 1], out float t0, out float t1)) continue;
                var d = Flat(work[k + 1] - work[k]).normalized;
                if (!found) { entry = Vector3.Lerp(work[k], work[k + 1], t0); u = d; found = true; }
                if (t1 < 1f) { exit = Vector3.Lerp(work[k], work[k + 1], t1); w = d; left = true; }
            }
            return found && left;
        }
        static bool Hits(CheckoutRoundabout circle, Vector3 a, Vector3 b, out float t0, out float t1)
        {
            t0 = t1 = 0;
            var d = new Vector2(b.x - a.x, b.z - a.z); var f = new Vector2(a.x - circle.center.x, a.z - circle.center.z);
            float A = Vector2.Dot(d, d); if (A < 1e-6f) return false;
            float B = 2 * Vector2.Dot(f, d), C = Vector2.Dot(f, f) - circle.clipRadius * circle.clipRadius;
            float disc = B * B - 4 * A * C; if (disc <= 0) return false;
            disc = Mathf.Sqrt(disc);
            t0 = (-B - disc) / (2 * A); t1 = (-B + disc) / (2 * A);
            if (t1 < 0 || t0 > 1) return false;
            t0 = Mathf.Max(0, t0); t1 = Mathf.Min(1, t1);
            return true;
        }
        // `before` / `after`: how far the turn may start before the entry point / end after the exit point (the legs' room).
        bool Ring(CheckoutRoundabout circle, Vector3 entry, Vector3 u, Vector3 exit, Vector3 w, float before, float after)
        {
            var c = circle.center; float R = circle.travelRadius;
            float aE = Mathf.Atan2(entry.z - c.z, entry.x - c.x), sweep = Mathf.Repeat(Mathf.Atan2(exit.z - c.z, exit.x - c.x) - aE, Mathf.PI * 2);
            if (sweep < .15f) return false; // only grazes the edge: the straight line stays
            float dE = Flat(entry - c).magnitude, dX = Flat(exit - c).magnitude;
            if (dE <= R || dX <= R) return false;
            // Onto the ring: the tangent from the entry point touches the circle at a0; joining it earlier moves the turn off
            // the lane further in and tightens it. The first ring angle back from a0 whose bend is down to RingBend (never
            // under the street radius) is where the circle starts, the bend ending exactly there. Off it the same, mirrored.
            float a0 = aE + Mathf.Acos(R / dE), b0 = aE + sweep - Mathf.Acos(R / dX);
            float alpha = a0, rIn = 0; Vector3 kIn = entry; bool inOk = false;
            for (float a = a0; a > aE - 1.5f; a -= .01f) { if (!OnTo(c, R, entry, u, a, before, out var k, out var r)) break; alpha = a; kIn = k; rIn = r; inOk = true; if (r <= RingBend) break; }
            float beta = b0, rOut = 0; Vector3 kOut = exit; bool outOk = false;
            for (float b = b0; b < aE + sweep + 1.5f; b += .01f) { if (!OffFrom(c, R, exit, w, b, after, out var k, out var r)) break; beta = b; kOut = k; rOut = r; outOk = true; if (r <= RingBend) break; }
            float y = entry.y;
            if (beta - alpha < .02f)
            {
                // No room for the ring (a first exit right after the entry): one right turn from lane to lane.
                float den = Cross(u, w); if (Mathf.Abs(den) < 1e-3f) return false;
                float lambda = Cross(Flat(exit - entry), w) / den;
                if (lambda < -before) return false;
                var corner = entry + u * lambda; corner.y = y;
                bent.Add(corner); bentHint.Add(0); bentOrigin.Add(-1);
                return true;
            }
            // (without a fitting bend the lane meets the ring at the clip circle and the corner is rounded as it fits)
            if (!inOk) { kIn = entry; rIn = 0; }
            if (!outOk) { kOut = exit; rOut = 0; }
            kIn.y = y; bent.Add(kIn); bentHint.Add(rIn); bentOrigin.Add(-1);
            int steps = Mathf.Max(1, Mathf.CeilToInt((beta - alpha) / RingStep)); float step = (beta - alpha) / steps, reach = R / Mathf.Cos(step * .5f);
            for (int k = 0; k < steps; k++)
            {
                float a = alpha + (k + .5f) * step;
                bent.Add(new Vector3(c.x + Mathf.Cos(a) * reach, y, c.z + Mathf.Sin(a) * reach)); bentHint.Add(R); bentOrigin.Add(-1);
            }
            kOut.y = y; bent.Add(kOut); bentHint.Add(rOut); bentOrigin.Add(-1);
            return true;
        }
        // The corner where the entry lane meets the ring's tangent at angle a, if a right-turn bend of at least the
        // street radius fits between them (and its radius).
        static bool OnTo(Vector3 c, float R, Vector3 e, Vector3 u, float a, float before, out Vector3 corner, out float radius)
        {
            corner = e; radius = 0;
            var t = new Vector3(c.x + Mathf.Cos(a) * R, 0, c.z + Mathf.Sin(a) * R); var tau = new Vector3(-Mathf.Sin(a), 0, Mathf.Cos(a));
            float den = Cross(u, tau); if (den > -1e-3f) return false; // must be a right turn
            var d = Flat(t - e); float lambda = Cross(d, tau) / den, mu = Cross(d, u) / den;
            if (mu > -1e-3f || lambda < -Mathf.Min(3f, before)) return false;
            float half = Vector3.Angle(u, tau) * Mathf.Deg2Rad * .5f, need = StreetRadius * Mathf.Tan(half);
            if (-mu < need) return false;
            corner = e + u * lambda; radius = -mu / Mathf.Tan(half);
            return true;
        }
        static bool OffFrom(Vector3 c, float R, Vector3 x, Vector3 w, float b, float after, out Vector3 corner, out float radius)
        {
            corner = x; radius = 0;
            var t = new Vector3(c.x + Mathf.Cos(b) * R, 0, c.z + Mathf.Sin(b) * R); var tau = new Vector3(-Mathf.Sin(b), 0, Mathf.Cos(b));
            float den = Cross(tau, w); if (den > -1e-3f) return false;
            var d = Flat(x - t); float mu = Cross(d, w) / den, lambda = Cross(d, tau) / den;
            if (mu < 1e-3f || lambda > Mathf.Min(3f, after)) return false;
            float half = Vector3.Angle(tau, w) * Mathf.Deg2Rad * .5f, need = StreetRadius * Mathf.Tan(half);
            if (mu < need) return false;
            corner = x + w * lambda; radius = mu / Mathf.Tan(half);
            return true;
        }

        // ------------------------------------------------------------------ following
        int Index(float s)
        {
            int lo = 0, hi = count - 1;
            if (s <= 0) return 0; if (s >= at[hi]) return Mathf.Max(0, hi - 1);
            while (hi - lo > 1) { int mid = (lo + hi) >> 1; if (at[mid] <= s) lo = mid; else hi = mid; }
            return lo;
        }
        /// <summary>The point `s` metres along, and the direction of travel there.</summary>
        public Vector3 Sample(float s, out Vector3 direction)
        {
            if (count == 0) { direction = Vector3.forward; return Vector3.zero; }
            if (count == 1) { direction = tangent[0]; return point[0]; }
            int i = Index(s); float span = at[i + 1] - at[i], k = span > 1e-6f ? Mathf.Clamp01((s - at[i]) / span) : 0;
            direction = Vector3.Lerp(tangent[i], tangent[i + 1], k); direction.y = 0; direction.Normalize();
            return Vector3.LerpUnclamped(point[i], point[i + 1], k);
        }
        public Vector3 Direction(float s) { Sample(s, out var d); return d; }
        /// <summary>Points every `step` metres along the path (a route drawn on a map).</summary>
        public void Points(List<Vector3> into, float step = 1f)
        {
            into.Clear(); if (count == 0) return;
            for (float s = 0; s < Length; s += step) into.Add(Sample(s, out _));
            into.Add(point[count - 1]);
        }
        /// <summary>The fastest speed at `s` from which the vehicle can still take every bend ahead at no more than `lateral`
        /// m/s^2 sideways, braking at `brake`.</summary>
        public float Allowed(float s, float cruise, float brake, float lateral = LateralAccel)
        {
            float best = cruise; if (count < 2) return best;
            float horizon = cruise * cruise / (2 * brake) + 1.5f;
            for (int j = Index(s) + 1; j < count; j++)
            {
                float ahead = at[j] - s; if (ahead > horizon) break;
                float k = bend[j]; if (k < 1e-3f) continue;
                float v2 = lateral / k + 2 * brake * Mathf.Max(0, ahead);
                if (v2 < best * best) best = Mathf.Sqrt(v2);
            }
            return best;
        }
        /// <summary>Speed from which it still stops at the end of the path.</summary>
        public float StopSpeed(float s, float brake) => Mathf.Sqrt(2 * brake * Mathf.Max(0, Length - s));
    }
}
