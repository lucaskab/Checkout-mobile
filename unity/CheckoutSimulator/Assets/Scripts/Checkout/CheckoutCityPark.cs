using UnityEngine;

namespace Checkout
{
    // Layout of the southern tip of the Central Park style block across the avenue (59th Street)
    // from the supermarket. The City Tiles shader paints the same shapes, so keep both in sync.
    public static class CheckoutCityPark
    {
        // Park interior (inside the perimeter wall). The block is x ±21.25 up to the avenue; the 4 m
        // sidewalks take the outer band.
        public const float West = -17.25f, East = 17.25f, North = -28.5f, South = -44f;
        public static readonly Vector2 Pond = new Vector2(7.2f, -39f), PondRadii = new Vector2(5.4f, 3.2f);
        public const float BridgeX = 6.4f;
        public const float RingOffset = 1.3f; // the footpath loop round the pond
        // The diagonal footpath leaves the drive near the west gate and runs south-east.
        public static readonly Vector2[] Diagonal = { new Vector2(-13.2f, -33.2f), new Vector2(-9.8f, -35f), new Vector2(-7.2f, -39.5f), new Vector2(-6.6f, -44.5f) };
        public static readonly Vector2[] EastPath = { new Vector2(12.9f, -28.5f), new Vector2(12.7f, -31.5f), new Vector2(11.6f, -34.6f) };

        // The park drive crossing the whole block (width 2.7 m).
        public static float DriveZ(float x) => -32.3f + 1.05f * Mathf.Sin(x * .21f + 1.3f);
        public static float PathX(float z) => -1.75f + 1.4f * Mathf.Sin((z + 28.5f) * .28f);

        static float Segment(Vector2 p, Vector2 a, Vector2 b)
        {
            var pa = p - a; var ba = b - a; float h = Mathf.Clamp01(Vector2.Dot(pa, ba) / Vector2.Dot(ba, ba));
            return (pa - ba * h).magnitude;
        }

        static float Polyline(Vector2 p, Vector2[] points)
        {
            float d = 99;
            for (int i = 0; i < points.Length - 1; i++) d = Mathf.Min(d, Segment(p, points[i], points[i + 1]));
            return d;
        }

        public static float PondDistance(Vector2 p)
        {
            var q = new Vector2((p.x - Pond.x) / PondRadii.x, (p.y - Pond.y) / PondRadii.y);
            return (q.magnitude - 1) * Mathf.Min(PondRadii.x, PondRadii.y);
        }

        // Signed distance to the nearest walking surface (paths, drive, plaza); negative on it.
        public static float PathDistance(Vector2 p)
        {
            float drive = Mathf.Abs(p.y - DriveZ(p.x)) - 1.35f;
            float diagonal = Polyline(p, Diagonal) - .75f;
            float central = p.y < North ? Mathf.Abs(p.x - PathX(p.y)) - .7f : 99;
            float ring = Mathf.Abs(PondDistance(p) - RingOffset) - .6f;
            float east = Polyline(p, EastPath) - .7f;
            return Mathf.Min(Mathf.Min(Mathf.Min(drive, diagonal), Mathf.Min(central, ring)), east);
        }

        public static bool InPark(Vector2 p, float margin = 0) =>
            p.x > West + margin && p.x < East - margin && p.y < North - margin && p.y > South + margin;
    }
}
