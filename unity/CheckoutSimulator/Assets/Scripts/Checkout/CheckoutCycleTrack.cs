using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Cycle routes. On the streets they follow the Berlin style "Radweg" that the City Tiles shader paints
    // on every sidewalk, right next to the curb: one-way, in the direction of the traffic beside it.
    // In the park they use the drive and the footpaths (two-way, keep right).
    public static class CheckoutCycleTrack
    {
        // Lane centre lines (see CityTiles.shader and CheckoutStreetLayout): 0.8 m from the curb.
        public const float AvenueNorth = CheckoutStreetLayout.AvenueCurbNorth + CheckoutStreetLayout.LaneCentre;
        public const float AvenueSouth = CheckoutStreetLayout.AvenueCurbSouth - CheckoutStreetLayout.LaneCentre;
        public const float InnerX = CheckoutStreetLayout.LocalCurbInner - CheckoutStreetLayout.LaneCentre;
        public const float OuterX = CheckoutStreetLayout.LocalCurbOuter + CheckoutStreetLayout.LaneCentre;
        public const float MapNorth = 47.6f, MapSouth = -43.8f, MapEast = 39.8f, MapWest = -39.8f;
        public const float HalfWidth = CheckoutStreetLayout.LaneHalf;
        static readonly Vector3 Circle = new Vector3(-23.5f, 0, -18.5f);
        const float CircleLane = CheckoutStreetLayout.CircleRoad + CheckoutStreetLayout.LaneCentre;

        public static List<Vector3[]> Routes(float y)
        {
            return new List<Vector3[]>
            {
                // Around the market block: down the east street, west along the avenue, up the west street.
                Line(y, P(InnerX, MapNorth), P(InnerX, AvenueNorth + .9f), P(InnerX - .7f, AvenueNorth + .25f), P(InnerX - 1.6f, AvenueNorth),
                    P(-InnerX + 1.6f, AvenueNorth), P(-InnerX + .7f, AvenueNorth + .35f), P(-InnerX, AvenueNorth + .8f), P(-InnerX, MapNorth)),
                // Outer west sidewalk southbound, then west along the avenue out of town.
                Line(y, P(-OuterX, MapNorth), P(-OuterX, AvenueNorth + .8f), P(-OuterX - .4f, AvenueNorth + .35f), P(-OuterX - 1.3f, AvenueNorth), P(MapWest, AvenueNorth)),
                // Into town along the avenue, then north up the east street's outer sidewalk.
                Line(y, P(MapEast, AvenueNorth), P(OuterX + 1.4f, AvenueNorth), P(OuterX + .5f, AvenueNorth + .3f), P(OuterX, AvenueNorth + 1.1f), P(OuterX, MapNorth)),
                // Central Park South, eastbound, curving round the south side of Columbus Circle.
                AvenueSouthEastbound(y),
                // The park: up the central path, then along the drive either way.
                Offset(Join(CentralPathNorth(y), DriveEast(y), EastExitSouth(y)), .3f),
                Offset(Join(CentralPathNorth(y), DriveWest(y), DiagonalSouth(y)), .3f),
                Offset(Join(Reverse(DiagonalSouth(y)), DriveEast(y, CheckoutCityPark.Diagonal[1].x), EastExitSouth(y)), .3f),
            };
        }

        static Vector3 P(float x, float z) => new Vector3(x, 0, z);

        static Vector3[] Line(float y, params Vector3[] corners)
        {
            var points = new List<Vector3>();
            for (int i = 0; i < corners.Length - 1; i++)
            {
                var a = corners[i]; var b = corners[i + 1]; int n = Mathf.Max(1, Mathf.CeilToInt(Vector3.Distance(a, b) / .6f));
                for (int k = 0; k < n; k++) { var p = Vector3.Lerp(a, b, k / (float)n); p.y = y; points.Add(p); }
            }
            var last = corners[corners.Length - 1]; last.y = y; points.Add(last);
            return points.ToArray();
        }

        // Counter-clockwise (seen from above) round the south of the circle, like the traffic. Lucas 26/10 (smooth turns):
        // the lane met the ring at a 35 degree kink, so the bikes jinked right, then left round the ring, then right again
        // within a second; now a wide right bend (EaseRadius) leaves the lane tangent to it and meets the ring tangent to it.
        const float EaseRadius = 9f;
        static Vector3[] AvenueSouthEastbound(float y)
        {
            var points = new List<Vector3>();
            // the bends' centres: EaseRadius south of the lane and EaseRadius off the ring
            float fz = AvenueSouth - EaseRadius, fx = Mathf.Sqrt((CircleLane + EaseRadius) * (CircleLane + EaseRadius) - (fz - Circle.z) * (fz - Circle.z));
            var west = new Vector3(Circle.x - fx, 0, fz); var east = new Vector3(Circle.x + fx, 0, fz);
            for (float x = MapWest; x < west.x; x += .6f) points.Add(new Vector3(x, y, AvenueSouth));
            void Arc(Vector3 centre, float radius, float from, float to, int steps, bool ends)
            {
                for (int i = ends ? 0 : 1; i <= (ends ? steps : steps - 1); i++)
                {
                    float a = Mathf.Lerp(from, to, i / (float)steps);
                    points.Add(new Vector3(centre.x + Mathf.Cos(a) * radius, y, centre.z + Mathf.Sin(a) * radius));
                }
            }
            float onto = Mathf.Atan2(west.z - Circle.z, west.x - Circle.x), off = Mathf.Atan2(east.z - Circle.z, east.x - Circle.x);
            if (off < onto) off += Mathf.PI * 2;
            Arc(west, EaseRadius, Mathf.PI * .5f, Mathf.Atan2(Circle.z - west.z, Circle.x - west.x), 8, true);
            Arc(Circle, CircleLane, onto, off, 12, false);
            Arc(east, EaseRadius, Mathf.Atan2(Circle.z - east.z, Circle.x - east.x), Mathf.PI * .5f, 8, true);
            for (float x = east.x + .6f; x <= MapEast; x += .6f) points.Add(new Vector3(x, y, AvenueSouth));
            return points.ToArray();
        }

        // ------------------------------------------------------------------ park paths (CheckoutCityPark)
        static float JoinZ => CheckoutCityPark.DriveZ(-1.75f);
        static List<Vector3> CentralPathNorth(float y)
        {
            var points = new List<Vector3>();
            for (float z = MapSouth; z < JoinZ; z += .5f) points.Add(new Vector3(CheckoutCityPark.PathX(z), y, z));
            return points;
        }
        // (from: where it joins the drive, the central path's end unless given)
        static List<Vector3> DriveEast(float y, float? from = null)
        {
            var points = new List<Vector3>();
            for (float x = from ?? CheckoutCityPark.PathX(JoinZ); x < CheckoutCityPark.East + .7f; x += .5f) points.Add(new Vector3(x, y, CheckoutCityPark.DriveZ(Mathf.Min(x, CheckoutCityPark.East))));
            return points;
        }
        static List<Vector3> DriveWest(float y)
        {
            var points = new List<Vector3>();
            float end = CheckoutCityPark.Diagonal[1].x;
            for (float x = CheckoutCityPark.PathX(JoinZ); x > end; x -= .5f) points.Add(new Vector3(x, y, CheckoutCityPark.DriveZ(x)));
            return points;
        }
        // Out of the east gate onto the street's cycle lane (southbound on that side).
        static List<Vector3> EastExitSouth(float y)
        {
            float z = CheckoutCityPark.DriveZ(CheckoutCityPark.East);
            var points = new List<Vector3> { new Vector3(InnerX - .3f, y, z - .5f) };
            for (float s = z - 1.2f; s > MapSouth; s -= .6f) points.Add(new Vector3(InnerX, y, s));
            return points;
        }
        static List<Vector3> DiagonalSouth(float y)
        {
            var d = CheckoutCityPark.Diagonal;
            var corners = new[] { new Vector3(d[1].x, y, CheckoutCityPark.DriveZ(d[1].x)), new Vector3(d[1].x, y, d[1].y), new Vector3(d[2].x, y, d[2].y), new Vector3(d[3].x, y, MapSouth) };
            var points = new List<Vector3>();
            for (int i = 0; i < corners.Length - 1; i++)
                for (int k = 0; k < 10; k++) points.Add(Vector3.Lerp(corners[i], corners[i + 1], k / 10f));
            points.Add(corners[corners.Length - 1]);
            return points;
        }
        static List<Vector3> Reverse(List<Vector3> points) { var copy = new List<Vector3>(points); copy.Reverse(); return copy; }
        static List<Vector3> Join(params List<Vector3>[] parts) { var all = new List<Vector3>(); foreach (var p in parts) all.AddRange(p); return all; }

        // Keep right on two-way paths. Lucas 26/10 (smooth turns): each point moves out along the bisector of its two legs
        // (mitred, so the lane keeps its width round a corner); two parts joined on the same spot count once, and inside a
        // corner the points that would step back past the corner's own are left out (the bikes turned back on themselves
        // there, a pivot on the spot).
        static Vector3[] Offset(List<Vector3> centre, float offset)
        {
            var points = new List<Vector3>(centre.Count);
            foreach (var p in centre) if (points.Count == 0 || Flat(p - points[points.Count - 1]).sqrMagnitude >= .15f * .15f) points.Add(p);
            var lane = new List<Vector3>(points.Count);
            for (int i = 0; i < points.Count; i++)
            {
                var a = Flat(points[i] - points[Mathf.Max(i - 1, 0)]).normalized; var b = Flat(points[Mathf.Min(i + 1, points.Count - 1)] - points[i]).normalized;
                if (a == Vector3.zero) a = b;
                if (b == Vector3.zero) b = a;
                var forward = (a + b).sqrMagnitude > 1e-6f ? (a + b).normalized : a;
                var q = points[i] + Vector3.Cross(Vector3.up, forward) * (offset / Mathf.Max(.5f, Vector3.Dot(forward, a)));
                if (i > 0) while (lane.Count > 1 && Vector3.Dot(Flat(q - lane[lane.Count - 1]), a) < .05f) lane.RemoveAt(lane.Count - 1);
                lane.Add(q);
            }
            return lane.ToArray();
        }
        static Vector3 Flat(Vector3 v) { v.y = 0; return v; }
    }
}
