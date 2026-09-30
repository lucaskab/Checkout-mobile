using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // The market building itself, built from textured blocks so it can take any size: a limestone plinth,
    // a tiled shop floor, navy fluted walls with a limestone base, brushed-gold coping, white LED strips,
    // corner pillars with lanterns, pilasters with wall lights, a portal over the door, grand entrance
    // steps with planters and a service ramp at the back. It replaces the supplied MarketStructure mesh,
    // which could only be stretched. Everything is re-placed from the projected footprint on every layout.
    public class CheckoutMarketShell : MonoBehaviour
    {
        public Material navy, plaster, limestone, gold, floorTiles, pavers, led, darkMetal, soil, flowers, glass;
        public Font font;
        public Material fontMaterial;

        const float Floor = .74f, Top = 3.23f, Thick = .5f, Sidewalk = .15f;
        // The camera looks in over the front (south) and east walls: those stay low so the whole shop
        // floor is visible. Only the back and west walls and the door portal stand at full height.
        const float LowTop = Floor + .75f;
        // Unprojected (scale 1) market: outer wall faces, front door and rear service door openings.
        const float X0 = -9.4f, X1 = 9.4f, Z0 = -7.4f, Z1 = 7.4f, DoorA = -3.25f, DoorB = -.25f, RearA = 3.12f, RearB = 4.92f;
        // The sliding door leaves open 1.32 m to each side: glass sidelights, not wall, stand there.
        const float SlideA = DoorA - 1.4f, SlideB = DoorB + 1.4f;
        const int PilasterPool = 48;
        // Clear floor stops this far inside a wall's inner plaster: the wainscot rail sticks out 5 cm.
        const float Rail = .05f, Square = .5f;

        // Wall thickness per side for a layout. The nominal wall is 50 cm; each pair of opposite walls gets up
        // to 12.5 cm thicker or thinner so the clear floor between them is an exact number of half squares
        // (the build grid then starts on one wall and ends exactly on the other).
        static float Fit(float outer)
        {
            float clear = outer - 2 * (Thick + Rail);
            float exact = Mathf.Max(Square, Mathf.Round(clear / Square) * Square);
            return Thick + (clear - exact) * .5f;
        }
        public static void Thickness(MarketLayout layout, out float sides, out float ends)
        {
            if (layout == null) layout = new MarketLayout();
            Vector3 P(float x, float z) => CheckoutMarketLayout.Project(new Vector3(x, 0, z), layout);
            sides = Fit(P(X1, 0).x - P(X0, 0).x); ends = Fit(P(0, Z1).z - P(0, Z0).z);
        }
        // The shop floor anything can stand on (world XZ): wall to wall, rail excluded. Width and depth are
        // whole half squares at every stage.
        public static Rect ClearRect(MarketLayout layout)
        {
            if (layout == null) layout = new MarketLayout();
            Vector3 P(float x, float z) => CheckoutMarketLayout.Project(new Vector3(x, 0, z), layout);
            Thickness(layout, out var sides, out var ends);
            float x0 = P(X0, 0).x, x1 = P(X1, 0).x, z0 = P(0, Z0).z, z1 = P(0, Z1).z;
            return Rect.MinMaxRect(x0 + sides + Rail, z0 + ends + Rail, x1 - sides - Rail, z1 - ends - Rail);
        }
        float tSide = Thick, tEnd = Thick;

        readonly Dictionary<string, Transform> parts = new Dictionary<string, Transform>();
        Transform walls, ground;
        public Transform Walls => walls ? walls : (walls = Group("Walls"));

        public Bounds Footprint { get; private set; }
        // Rear service door (CheckoutStaff hangs the roller door here): centre of the opening on the floor, in the
        // middle of the wall; the wall's outer face; the top and the foot of the service ramp.
        public Vector3 RearDoor { get; private set; }
        public float RearWall { get; private set; }
        public Vector3 RampTop { get; private set; }
        public Vector3 RampEnd { get; private set; }

        Transform Group(string name)
        {
            var t = transform.Find(name);
            if (!t) { t = new GameObject(name).transform; t.SetParent(transform, false); }
            return t;
        }

        Transform Part(Transform group, string name, Material material, PrimitiveType type = PrimitiveType.Cube)
        {
            string key = group.name + "/" + name;
            if (parts.TryGetValue(key, out var cached) && cached) return cached;
            var t = group.Find(name);
            if (!t)
            {
                var go = GameObject.CreatePrimitive(type);
                go.name = name;
                var collider = go.GetComponent<Collider>();
                if (collider) { if (Application.isPlaying) Destroy(collider); else DestroyImmediate(collider); }
                t = go.transform; t.SetParent(group, false);
            }
            var renderer = t.GetComponent<Renderer>();
            if (renderer && material) renderer.sharedMaterial = material;
            parts[key] = t;
            return t;
        }

        void Box(Transform group, string name, Material material, Vector3 min, Vector3 max)
        {
            var t = Part(group, name, material);
            t.gameObject.SetActive(true);
            t.localRotation = Quaternion.identity;
            t.position = (min + max) * .5f;
            t.localScale = new Vector3(Mathf.Max(.001f, max.x - min.x), Mathf.Max(.001f, max.y - min.y), Mathf.Max(.001f, max.z - min.z));
        }

        void Hide(Transform group, string name) { var t = group.Find(name); if (t) t.gameObject.SetActive(false); }

        public void Apply(MarketLayout layout)
        {
            if (layout == null) layout = new MarketLayout();
            walls = Group("Walls"); ground = Group("Base");
            Vector3 P(float x, float z) => CheckoutMarketLayout.Project(new Vector3(x, 0, z), layout);
            float x0 = P(X0, 0).x, x1 = P(X1, 0).x, z0 = P(0, Z0).z, z1 = P(0, Z1).z;
            float da = P(DoorA, 0).x, db = P(DoorB, 0).x, ra = P(RearA, 0).x, rb = P(RearB, 0).x;
            float sa = P(SlideA, 0).x, sb = P(SlideB, 0).x;
            Thickness(layout, out tSide, out tEnd);
            Footprint = new Bounds(new Vector3((x0 + x1) * .5f, (Floor + Top) * .5f, (z0 + z1) * .5f), new Vector3(x1 - x0, Top - Floor, z1 - z0));

            // Plinth and shop floor.
            Box(ground, "Plinth", limestone, new Vector3(x0 - .2f, 0, z0 - .2f), new Vector3(x1 + .2f, Floor - .025f, z1 + .2f));
            Box(ground, "Plinth trim", gold, new Vector3(x0 - .23f, Floor - .06f, z0 - .23f), new Vector3(x1 + .23f, Floor - .02f, z1 + .23f));
            Box(ground, "Floor", floorTiles, new Vector3(x0 + tSide - .02f, Floor - .03f, z0 + tEnd - .02f), new Vector3(x1 - tSide + .02f, Floor + .002f, z1 - tEnd + .02f));

            // Walls: front and back are split around their doors.
            Wall("Front L", new Vector3(x0, 0, z0), new Vector3(sa, 0, z0), Vector3.back, LowTop);
            Wall("Front R", new Vector3(sb, 0, z0), new Vector3(x1, 0, z0), Vector3.back, LowTop);
            Wall("Rear L", new Vector3(x0, 0, z1), new Vector3(ra, 0, z1), Vector3.forward, Top);
            Wall("Rear R", new Vector3(rb, 0, z1), new Vector3(x1, 0, z1), Vector3.forward, Top);
            Wall("West", new Vector3(x0, 0, z0), new Vector3(x0, 0, z1), Vector3.left, Top);
            Wall("East", new Vector3(x1, 0, z0), new Vector3(x1, 0, z1), Vector3.right, LowTop);

            // Corner pillars with a gold cap and a lantern.
            int c = 0;
            foreach (var corner in new[] { new Vector3(x0, 0, z0), new Vector3(x1, 0, z0), new Vector3(x0, 0, z1), new Vector3(x1, 0, z1) })
            {
                var inward = new Vector3(corner.x < (x0 + x1) * .5f ? .18f : -.18f, 0, corner.z < (z0 + z1) * .5f ? .18f : -.18f);
                var p = corner + inward;
                // Only the front-east corner joins two low walls.
                float h = c == 1 ? LowTop + .25f : Top + .3f;
                Box(walls, "Pillar " + c, limestone, new Vector3(p.x - .45f, Floor - .1f, p.z - .45f), new Vector3(p.x + .45f, h, p.z + .45f));
                Box(walls, "Pillar base " + c, limestone, new Vector3(p.x - .52f, Floor - .1f, p.z - .52f), new Vector3(p.x + .52f, Floor + .35f, p.z + .52f));
                Box(walls, "Pillar cap " + c, gold, new Vector3(p.x - .53f, h, p.z - .53f), new Vector3(p.x + .53f, h + .12f, p.z + .53f));
                Box(walls, "Lantern " + c, led, new Vector3(p.x - .16f, h + .12f, p.z - .16f), new Vector3(p.x + .16f, h + .42f, p.z + .16f));
                Box(walls, "Lantern roof " + c, gold, new Vector3(p.x - .22f, h + .42f, p.z - .22f), new Vector3(p.x + .22f, h + .5f, p.z + .22f));
                c++;
            }

            // Pilasters with a wall light every ~3 m along every facade (skipping doors and corners).
            int used = 0;
            void Run(Vector3 a, Vector3 b, Vector3 normal, float gapA, float gapB, float top)
            {
                float length = Vector3.Distance(a, b);
                int count = Mathf.Max(0, Mathf.FloorToInt(length / 3f) - 1);
                for (int i = 1; i <= count && used < PilasterPool; i++)
                {
                    var q = Vector3.Lerp(a, b, i / (float)(count + 1));
                    float along = normal.z != 0 ? q.x : q.z;
                    if (along > gapA - .9f && along < gapB + .9f) continue;
                    bool alongX = normal.z != 0;
                    var half = alongX ? new Vector3(.2f, 0, 0) : new Vector3(0, 0, .2f);
                    var outward = normal * .1f;
                    bool low = top < Top - .1f;
                    Box(walls, "Pilaster " + used, limestone, Vector3.Min(q - half, q - half + outward) + Vector3.up * (Floor - .05f), Vector3.Max(q + half, q + half + outward) + Vector3.up * (low ? top + .18f : top));
                    var lamp = q + normal * (low ? 0 : .16f);
                    var lh = alongX ? new Vector3(.09f, 0, .05f) : new Vector3(.05f, 0, .09f);
                    // Low walls get a small light on top of each post, tall walls a sconce.
                    if (low) Box(walls, "Wall light " + used, led, lamp - lh * 1.2f + Vector3.up * (top + .18f), lamp + lh * 1.2f + Vector3.up * (top + .32f));
                    else Box(walls, "Wall light " + used, led, lamp - lh + Vector3.up * 2.45f, lamp + lh + Vector3.up * 2.7f);
                    used++;
                }
            }
            Run(new Vector3(x0, 0, z0), new Vector3(x1, 0, z0), Vector3.back, sa - .4f, sb + .4f, LowTop);
            Run(new Vector3(x0, 0, z1), new Vector3(x1, 0, z1), Vector3.forward, ra, rb, Top);
            Run(new Vector3(x0, 0, z0), new Vector3(x0, 0, z1), Vector3.left, 1e6f, -1e6f, Top);
            Run(new Vector3(x1, 0, z0), new Vector3(x1, 0, z1), Vector3.right, 1e6f, -1e6f, LowTop);
            for (int i = used; i < PilasterPool; i++) { Hide(walls, "Pilaster " + i); Hide(walls, "Wall light " + i); }

            // Portal over the front door.
            // Portal: tall limestone jambs, a navy header with gold trim and glass sidelights that the
            // sliding doors open behind.
            Box(walls, "Portal jamb L", limestone, new Vector3(sa - .42f, Floor - .1f, z0 - .25f), new Vector3(sa + .02f, Top + .7f, z0 + tEnd));
            Box(walls, "Portal jamb R", limestone, new Vector3(sb - .02f, Floor - .1f, z0 - .25f), new Vector3(sb + .42f, Top + .7f, z0 + tEnd));
            Box(walls, "Portal header", navy, new Vector3(sa - .02f, Top - .15f, z0 - .2f), new Vector3(sb + .02f, Top + .6f, z0 + .3f));
            Box(walls, "Portal trim top", gold, new Vector3(sa - .5f, Top + .7f, z0 - .3f), new Vector3(sb + .5f, Top + .82f, z0 + tEnd + .05f));
            Box(walls, "Portal trim low", gold, new Vector3(sa - .02f, Top - .2f, z0 - .23f), new Vector3(sb + .02f, Top - .15f, z0 + .3f));
            Box(walls, "Portal light", led, new Vector3(sa + .1f, Top - .26f, z0 - .2f), new Vector3(sb - .1f, Top - .2f, z0 - .14f));
            Box(walls, "Sidelight L", glass, new Vector3(sa, Floor, z0 - .07f), new Vector3(da, Top - .2f, z0 - .03f));
            Box(walls, "Sidelight R", glass, new Vector3(db, Floor, z0 - .07f), new Vector3(sb, Top - .2f, z0 - .03f));
            Box(walls, "Sidelight kick L", navy, new Vector3(sa, Floor - .05f, z0 - .09f), new Vector3(da, Floor + .22f, z0 - .02f));
            Box(walls, "Sidelight kick R", navy, new Vector3(db, Floor - .05f, z0 - .09f), new Vector3(sb, Floor + .22f, z0 - .02f));
            Box(walls, "Mullion L", gold, new Vector3(da - .04f, Floor, z0 - .1f), new Vector3(da + .04f, Top - .2f, z0 - .02f));
            Box(walls, "Mullion R", gold, new Vector3(db - .04f, Floor, z0 - .1f), new Vector3(db + .04f, Top - .2f, z0 - .02f));
            // The entrance awning sits on the header (high enough for customers to walk under), so the
            // "BEM-VINDO" sign stands on top of the portal: a navy board with gold edges.
            Box(walls, "Portal sign", navy, new Vector3(sa + .15f, Top + .82f, z0 - .18f), new Vector3(sb - .15f, Top + 1.42f, z0 + .1f));
            Box(walls, "Portal sign trim", gold, new Vector3(sa + .1f, Top + 1.42f, z0 - .22f), new Vector3(sb - .1f, Top + 1.5f, z0 + .14f));
            PortalLabel(new Vector3((sa + sb) * .5f, Top + 1.12f, z0 - .195f), sb - sa);

            // Rear service door: limestone jambs up to the coping and a lintel over the roller door (2.2 m clear).
            Box(walls, "Rear jamb L", limestone, new Vector3(ra - .25f, Floor - .05f, z1 - tEnd), new Vector3(ra + .02f, Top, z1 + .12f));
            Box(walls, "Rear jamb R", limestone, new Vector3(rb - .02f, Floor - .05f, z1 - tEnd), new Vector3(rb + .25f, Top, z1 + .12f));
            Box(walls, "Rear lintel", limestone, new Vector3(ra - .25f, Floor + 2.3f, z1 - .42f), new Vector3(rb + .25f, Top, z1 - .08f));
            Hide(walls, "Rear light");
            RearDoor = new Vector3((ra + rb) * .5f, Floor, z1 - tEnd * .5f); RearWall = z1;

            Entrance(da, db, z0);
            RearRamp(ra, rb, z1, P(0, 8.85f).z);
        }

        // One straight run of wall: navy fluted outside, limestone base, cream plaster inside with a navy
        // wainscot and a gold rail, brushed-gold coping and a white LED strip under it.
        void Wall(string name, Vector3 a, Vector3 b, Vector3 normal, float top)
        {
            bool alongX = normal.z != 0;
            if ((alongX ? Mathf.Abs(b.x - a.x) : Mathf.Abs(b.z - a.z)) < .05f)
            {
                foreach (var n in new[] { "Outer", "Base", "Inner", "Wainscot", "Rail", "Coping", "LED" }) Hide(walls, name + " " + n);
                return;
            }
            Vector3 lo = Vector3.Min(a, b), hi = Vector3.Max(a, b);
            // Offsets along the normal: positive = outwards.
            Vector3 Span(float from, float to, float y0, float y1, float extend = 0)
            {
                var min = lo; var max = hi;
                if (alongX) { min.x -= extend; max.x += extend; } else { min.z -= extend; max.z += extend; }
                var o0 = normal * from; var o1 = normal * to;
                spanMin = Vector3.Min(min + o0, min + o1); spanMin.y = y0;
                spanMax = Vector3.Max(max + o0, max + o1); spanMax.y = y1;
                return spanMin;
            }
            bool low = top < Top - .1f;
            float thick = alongX ? tEnd : tSide;
            Span(-.3f, 0, Floor, top); Box(walls, name + " Outer", navy, spanMin, spanMax);
            Span(-.02f, .06f, Floor - .08f, Floor + (low ? .3f : .5f)); Box(walls, name + " Base", limestone, spanMin, spanMax);
            Span(-thick, -.3f, Floor, top - .02f); Box(walls, name + " Inner", plaster, spanMin, spanMax);
            float wainscot = low ? top - Floor - .1f : .95f;
            Span(-thick - .03f, -thick + .01f, Floor, Floor + wainscot); Box(walls, name + " Wainscot", navy, spanMin, spanMax);
            Span(-thick - .05f, -thick + .01f, Floor + wainscot, Floor + wainscot + .07f); Box(walls, name + " Rail", gold, spanMin, spanMax);
            Span(-thick - .06f, .08f, top, top + .13f, .06f); Box(walls, name + " Coping", gold, spanMin, spanMax);
            Span(.0f, .04f, top - .2f, top - .13f); Box(walls, name + " LED", led, spanMin, spanMax);
        }
        Vector3 spanMin, spanMax;

        void PortalLabel(Vector3 at, float width)
        {
            var t = transform.Find("Walls/Portal label");
            if (!t)
            {
                var go = new GameObject("Portal label", typeof(TextMesh));
                t = go.transform; t.SetParent(Walls, false);
                var text = go.GetComponent<TextMesh>();
                text.text = "BEM-VINDO"; text.font = font; text.fontSize = 96; text.anchor = TextAnchor.MiddleCenter; text.fontStyle = FontStyle.Bold;
                text.color = new Color(.93f, .76f, .35f);
                go.GetComponent<MeshRenderer>().sharedMaterial = fontMaterial;
            }
            t.position = at; t.rotation = Quaternion.identity;
            t.GetComponent<TextMesh>().characterSize = Mathf.Clamp(width * .0105f, .02f, .045f);
        }

        // Grand steps from the sidewalk to the shop floor, limestone with gold nosings, flanked by planters
        // with flowers and lit bollards, on a paved landing.
        void Entrance(float da, float db, float front)
        {
            float start = CheckoutMarketLayout.WorldAnchor.z, length = Mathf.Max(.8f, front - start);
            float cx = (da + db) * .5f, half = (db - da) * .5f + .55f;
            const int steps = 5;
            float rise = (Floor - Sidewalk) / steps, tread = length / steps;
            for (int i = 0; i < steps; i++)
            {
                float z = start + i * tread, top = Sidewalk + (i + 1) * rise;
                Box(ground, "Step " + i, limestone, new Vector3(cx - half, 0, z), new Vector3(cx + half, top, front + .05f));
                Box(ground, "Nosing " + i, gold, new Vector3(cx - half, top - .025f, z - .01f), new Vector3(cx + half, top + .004f, z + .05f));
            }
            // Planter cheeks on both sides.
            foreach (var side in new[] { -1, 1 })
            {
                float inner = cx + side * half, outer = inner + side * .75f;
                float a = Mathf.Min(inner, outer), b = Mathf.Max(inner, outer);
                string s = side < 0 ? "L" : "R";
                Box(ground, "Planter " + s, limestone, new Vector3(a, 0, start), new Vector3(b, Floor + .22f, front));
                Box(ground, "Planter cap " + s, gold, new Vector3(a - .03f, Floor + .22f, start - .03f), new Vector3(b + .03f, Floor + .26f, front));
                Box(ground, "Planter soil " + s, soil, new Vector3(a + .08f, Floor + .2f, start + .08f), new Vector3(b - .08f, Floor + .28f, front - .1f));
                Box(ground, "Planter flowers " + s, flowers, new Vector3(a + .1f, Floor + .26f, start + .1f), new Vector3(b - .1f, Floor + .5f, front - .15f));
                float bx = (a + b) * .5f;
                Box(ground, "Bollard " + s, darkMetal, new Vector3(bx - .09f, Floor + .26f, start + .1f), new Vector3(bx + .09f, Floor + 1.05f, start + .28f));
                Box(ground, "Bollard light " + s, led, new Vector3(bx - .1f, Floor + 1.05f, start + .09f), new Vector3(bx + .1f, Floor + 1.2f, start + .29f));
                Box(ground, "Bollard cap " + s, gold, new Vector3(bx - .12f, Floor + 1.2f, start + .07f), new Vector3(bx + .12f, Floor + 1.25f, start + .31f));
            }
            foreach (var n in new[] { "Landing", "Landing border", "Landing inlay" }) Hide(ground, n);
        }

        // Service ramp from the rear door down to the yard: a sloped limestone deck with anti-slip strips, a
        // hazard nosing at the top, side curbs and handrails. Staff carry boxes up and down it.
        void RearRamp(float ra, float rb, float wall, float end)
        {
            for (int i = 0; i < 4; i++) Hide(ground, "Rear step " + i);
            float cx = (ra + rb) * .5f, half = (rb - ra) * .5f + .15f, start = wall + .2f, top = Floor - .02f;
            end = Mathf.Max(end, start + 2.1f);
            RampTop = new Vector3(cx, top, start); RampEnd = new Vector3(cx, Sidewalk, end);
            float len = end - start, drop = top - Sidewalk, slope = Mathf.Sqrt(len * len + drop * drop);
            var tilt = Quaternion.Euler(Mathf.Atan2(drop, len) * Mathf.Rad2Deg, 0, 0);
            var mid = new Vector3(cx, (top + Sidewalk) * .5f, (start + end) * .5f);
            void Slab(string name, Material m, float x, float w, float above, float thick, float along = 0, float length = -1)
            {
                var t = Part(ground, name, m); t.gameObject.SetActive(true);
                t.rotation = tilt; t.localScale = new Vector3(w, thick, length < 0 ? slope : length);
                t.position = mid + new Vector3(x - cx, 0, 0) + tilt * new Vector3(0, above - thick * .5f, along);
            }
            Slab("Rear ramp", limestone, cx, half * 2, 0, .35f);
            for (int i = 0; i < 5; i++) Slab("Rear ramp grip " + i, darkMetal, cx, half * 2 - .2f, .006f, .02f, -slope * .5f + slope * (i + .5f) / 5, .06f);
            foreach (var s in new[] { -1, 1 })
            {
                string n = s < 0 ? "L" : "R";
                float x = cx + s * (half + .09f);
                Slab("Rear ramp curb " + n, limestone, x, .18f, .14f, .5f);
                Slab("Rear ramp curb cap " + n, gold, x, .2f, .16f, .03f);
                // Handrail on two posts.
                for (int p = 0; p < 2; p++)
                {
                    float along = -slope * .5f + slope * (p == 0 ? .12f : .88f);
                    var post = Part(ground, "Rear rail post " + n + p, darkMetal); post.gameObject.SetActive(true);
                    var basePoint = mid + new Vector3(x - cx, 0, 0) + tilt * new Vector3(0, .14f, along);
                    post.rotation = Quaternion.identity; post.localScale = new Vector3(.05f, .9f, .05f); post.position = basePoint + Vector3.up * .45f;
                }
                Slab("Rear rail " + n, gold, x, .06f, 1.04f, .05f, 0, slope * .8f);
            }
            Box(ground, "Rear ramp nosing", gold, new Vector3(cx - half, top - .01f, wall - .02f), new Vector3(cx + half, top + .012f, start + .02f));
        }
    }
}
