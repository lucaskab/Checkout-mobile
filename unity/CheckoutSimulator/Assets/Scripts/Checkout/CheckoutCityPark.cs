using UnityEngine;

namespace Checkout
{
    // Layout of the southern tip of the Central Park style block across the avenue (59th Street)
    // from the supermarket. The City Tiles shader paints the same shapes, so keep both in sync.
    public static class CheckoutCityPark
    {
        // Park interior (inside the perimeter wall). The block itself is x ±21.25 up to the avenue sidewalk.
        public const float West = -18.5f, East = 18.5f, North = -26.5f, South = -44f;
        public static readonly Vector2 Pond = new Vector2(9.5f, -37.5f), PondRadii = new Vector2(5.2f, 3.3f);
        public static readonly Vector2 Gate = new Vector2(-18.5f, -26.5f); // Merchants' Gate plaza corner
        public const float GateRadius = 6f;

        // The park drive crossing the whole block (width 2.7 m).
        public static float DriveZ(float x) => -30.8f + 1.1f * Mathf.Sin(x * .21f + 1.3f);
        public static float PathX(float z) => -1.75f + 1.4f * Mathf.Sin((z + 26.5f) * .28f);

        static float Segment(Vector2 p, Vector2 a, Vector2 b)
        {
            var pa = p - a; var ba = b - a; float h = Mathf.Clamp01(Vector2.Dot(pa, ba) / Vector2.Dot(ba, ba));
            return (pa - ba * h).magnitude;
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
            float diagonal = Mathf.Min(Segment(p, new Vector2(-16.5f, -29f), new Vector2(-11.5f, -33.5f)),
                Mathf.Min(Segment(p, new Vector2(-11.5f, -33.5f), new Vector2(-8f, -38.5f)), Segment(p, new Vector2(-8f, -38.5f), new Vector2(-7f, -44.5f)))) - .75f;
            float central = p.y < North ? Mathf.Abs(p.x - PathX(p.y)) - .7f : 99;
            float ring = Mathf.Abs(PondDistance(p) - 1.6f) - .6f;
            float east = Mathf.Min(Segment(p, new Vector2(15.5f, -26.5f), new Vector2(15.2f, -31.5f)), Segment(p, new Vector2(15.2f, -31.5f), new Vector2(13.6f, -35f))) - .7f;
            float plaza = (p - Gate).magnitude - GateRadius;
            return Mathf.Min(Mathf.Min(Mathf.Min(drive, diagonal), Mathf.Min(central, ring)), Mathf.Min(east, plaza));
        }

        public static bool InPark(Vector2 p, float margin = 0) =>
            p.x > West + margin && p.x < East - margin && p.y < North - margin && p.y > South + margin;
    }
}
