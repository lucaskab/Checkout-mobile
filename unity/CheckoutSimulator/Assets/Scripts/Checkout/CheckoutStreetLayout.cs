using UnityEngine;

namespace Checkout
{
    // Street cross-sections painted by the City Tiles shader (keep both in sync).
    // Local streets run north-south at x ±23.5 (road |x| 21.25..25.75), the avenue east-west
    // (road z -24.5..-12.5). Sidewalks are 4 m wide everywhere (as in front of the market);
    // the one-way cycle lane runs along the curb (0.2..1.4 m from it) and the footway is behind it.
    public static class CheckoutStreetLayout
    {
        public const float LocalCurbInner = 21.25f, LocalCurbOuter = 25.75f, LocalWalk = 4f;
        public const float AvenueCurbNorth = -12.5f, AvenueCurbSouth = -24.5f, AvenueWalk = 4f;
        public const float LaneCentre = .8f, LaneHalf = .6f, LaneEnd = 1.4f;
        // Block edges behind the sidewalks.
        public const float BlockInnerX = LocalCurbInner - LocalWalk, BlockOuterX = LocalCurbOuter + LocalWalk;
        public const float BlockNorthZ = AvenueCurbNorth + AvenueWalk, BlockSouthZ = AvenueCurbSouth - AvenueWalk;
        // Centre lines of the footways (between the cycle lane and the block).
        public const float InnerWalkX = (LocalCurbInner - LaneEnd + BlockInnerX) * .5f, OuterWalkX = (LocalCurbOuter + LaneEnd + BlockOuterX) * .5f;
        public const float NorthWalkZ = (AvenueCurbNorth + LaneEnd + BlockNorthZ) * .5f, SouthWalkZ = (AvenueCurbSouth - LaneEnd + BlockSouthZ) * .5f;
        // Columbus Circle: road ring up to 7.5 m, sidewalk ring 4 m, crossings on the arms beyond it.
        public static readonly Vector2 Circle = new Vector2(-23.5f, -18.5f);
        public const float CircleRoad = 7.5f, CircleCrossing = 12.3f;

        // Street furniture keeps clear of the cycle lane: anything standing on it moves just behind it.
        public static Vector3 OffLane(Vector3 p)
        {
            const float clear = LaneEnd + .3f;
            var c = new Vector2(p.x - Circle.x, p.z - Circle.y);
            if (c.magnitude < CircleRoad + AvenueWalk + .5f)
            {
                if (c.magnitude > CircleRoad - .1f && c.magnitude < CircleRoad + clear)
                {
                    var n = c.normalized * (CircleRoad + clear);
                    p.x = Circle.x + n.x; p.z = Circle.y + n.y;
                }
                return p;
            }
            float ax = Mathf.Abs(p.x), sx = Mathf.Sign(p.x);
            if (ax > LocalCurbInner - clear && ax < LocalCurbInner) p.x = sx * (LocalCurbInner - clear);
            else if (ax > LocalCurbOuter && ax < LocalCurbOuter + clear) p.x = sx * (LocalCurbOuter + clear);
            if (p.z > AvenueCurbNorth && p.z < AvenueCurbNorth + clear) p.z = AvenueCurbNorth + clear;
            else if (p.z < AvenueCurbSouth && p.z > AvenueCurbSouth - clear) p.z = AvenueCurbSouth - clear;
            return p;
        }
    }
}
