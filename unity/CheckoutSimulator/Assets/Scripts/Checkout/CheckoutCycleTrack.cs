using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Meandering two-way cycle track on the market block: north along the east promenade, round a
    // bend and west along the north quay. The City Tiles shader paints the same curve, keep both in sync.
    public static class CheckoutCycleTrack
    {
        public const float HalfWidth = .9f, South = -12.5f, West = -20f;
        public const float CornerX = 11.5f, CornerZ = 38.5f, Radius = 4f;

        // Centre line of the east leg (x for a given z) and of the north leg (z for a given x).
        public static float EastX(float z) => 15.5f + .9f * Mathf.Sin((z + 12.5f) * .19f) * Smooth(CornerZ - z);
        public static float NorthZ(float x) => 42.5f + .75f * Mathf.Sin((CornerX - x) * .24f) * Smooth(CornerX - x);
        static float Smooth(float s) { float t = Mathf.Clamp01(s / 6f); return t * t * (3 - 2 * t); }

        // Centre line from the avenue end to the west end, sampled every ~0.5 m.
        public static List<Vector3> CentreLine(float y)
        {
            var points = new List<Vector3>();
            for (float z = South; z < CornerZ; z += .5f) points.Add(new Vector3(EastX(z), y, z));
            for (int i = 0; i <= 12; i++)
            {
                float a = i / 12f * Mathf.PI * .5f;
                points.Add(new Vector3(CornerX + Radius * Mathf.Cos(a), y, CornerZ + Radius * Mathf.Sin(a)));
            }
            for (float x = CornerX - .5f; x > West; x -= .5f) points.Add(new Vector3(x, y, NorthZ(x)));
            points.Add(new Vector3(West, y, NorthZ(West)));
            return points;
        }

        // A riding lane: the centre line offset to the right of the direction of travel.
        public static Vector3[] Lane(bool northbound, float offset, float y)
        {
            var centre = CentreLine(y);
            if (!northbound) centre.Reverse();
            var lane = new Vector3[centre.Count];
            for (int i = 0; i < centre.Count; i++)
            {
                var forward = centre[Mathf.Min(i + 1, centre.Count - 1)] - centre[Mathf.Max(i - 1, 0)];
                var right = Vector3.Cross(Vector3.up, forward.normalized);
                lane[i] = centre[i] + right * offset;
            }
            return lane;
        }
    }
}
