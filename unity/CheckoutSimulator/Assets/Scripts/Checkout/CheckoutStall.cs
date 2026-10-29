using System.Collections.Generic;
using UnityEngine;
using MarketDay;

namespace Checkout
{
    // The first expansions (mesinha, tenda, banca, contêiner, Späti, quitanda, minimercado) are not the market
    // building: the player sells from a small stall or shop (snapshot era.building = false). The mesinha stands
    // on the sidewalk in front of lot A1 (the corner on the left of the avenue), the tenda and the small shops on
    // A1, the minimercado on A1 + B1 (src/data/market-lots.ts).
    // While one of them is active the building, its
    // interior and the staff that belong to it are hidden, the shop floor leaves the navigation and the
    // customers browse the stall's crates and pay at it (CheckoutMap asks this class for those points).
    // Era models: Assets/Resources/CheckoutEras (made in Blender, ArtSource/Checkout_Workspace.blend).
    public class CheckoutStall : MonoBehaviour
    {
        /// <summary>A small era is on: the market building is hidden and customers use the stall.</summary>
        public static bool Small { get; private set; }
        public static int Era { get; private set; } = -1;

        // Stall centre (front faces the avenue, -Z): the middle of lot A1 (x -17.25..-5.75); the minimercado is
        // wider than one lot and stands across A1 and B1 from the A1 west edge.
        public static Vector3 Centre => new Vector3(Era == 6 ? -9.3f : -11.5f, .1f, FrontLine + 1.4f);
        const float Scale = 1.2f;
        static float FrontZ => FrontLine - .85f; // where shoppers stand to pick from the crates
        static readonly float[] CrateX = { -1.3f, -.65f, 0f, .65f, 1.3f }; // along the counter, from the centre

        Transform world; CheckoutMap map; MarketSimulation simulation; CheckoutLotSites sites; CheckoutEraWorks works;
        readonly Dictionary<string, GameObject> models = new Dictionary<string, GameObject>();
        readonly List<GameObject> hidden = new List<GameObject>();
        GameObject shown;

        public void Initialize(Transform root, CheckoutMap owner)
        {
            world = root; map = owner; simulation = FindAnyObjectByType<MarketSimulation>();
            sites = gameObject.AddComponent<CheckoutLotSites>(); sites.Initialize(root, owner);
            works = gameObject.AddComponent<CheckoutEraWorks>(); works.Initialize(root);
        }

        // ------------------------------------------------------------------ shops the player furnishes
        // The Späti, the quitanda and the minimercado are real little shops: empty inside, so the player places
        // the game's shelves and coolers there (build mode) and customers walk in through the door. Measured on
        // the Blender models (model metres: x right, z back, front wall towards -z).
        // Lucas 29/10 (a tester's Conveniência packed with furniture and customers: "os clientes ficam meio bugados ali
        // na fila"): the three shops grew (Späti +50 %, quitanda +30 %, minimercado +30 % of floor) away from the door
        // and the old floor, so every piece a player placed keeps its saved spot inside; the line runs along a lane of
        // its own instead of across the doorway, and when the shop is full the next customers wait outside by the door.
        struct ShopPlan
        {
            public Rect floor;            // inner floor, wall to wall
            public float doorMin, doorMax; // door opening along x, in the front wall
            public float keepMin, keepMax; // the way in kept free of furniture (x; 0/0 = the door): the old door when it grew
            public Rect counter;          // the fixed counter with the register and the clerk's stool
            public Vector2[] queue;       // the line: [0] where the customer pays, then the places behind, in order
            public float floorY;          // top of the floor slab
            public bool placedCounter;    // no counter in the model: the player places the game's checkout
            public Vector2 wait;          // outside, first place of those waiting to get in (3 a row, rows towards the street)
            public (string part, Rect rect)[] solids; // parts of the model outside the walls people walk round (when present)
            public Rect oldFloor;         // the floor before the shop grew: the places of the line beyond it are kept free
        }
        static readonly Dictionary<string, ShopPlan> Plans = new Dictionary<string, ShopPlan>
        {
            // 28.9 m² of floor (was 19.2): 0.4 m more on the left, a 0.8 m lane on the right where the line runs from the
            // counter to the back, 0.7 m more at the back. The door is 1.2 m wide (was 0.9) on the same spot.
            ["Era4_Spati"] = new ShopPlan
            {
                floor = Rect.MinMaxRect(-3.25f, -1.12f, 3.85f, 2.95f), doorMin = .58f, doorMax = 1.78f, keepMin = .72f, keepMax = 1.62f, oldFloor = Rect.MinMaxRect(-2.85f, -1.12f, 2.85f, 2.25f),
                counter = Rect.MinMaxRect(1.3f, .0f, 3.03f, 1.4f), floorY = .06f, wait = new Vector2(2.75f, -1.9f),
                queue = new[] { new Vector2(2.15f, -.35f), new Vector2(2.9f, -.5f), new Vector2(3.45f, -.05f), new Vector2(3.45f, .7f), new Vector2(3.45f, 1.45f), new Vector2(3.45f, 2.2f), new Vector2(2.75f, 2.5f), new Vector2(2.0f, 2.5f) },
                solids = new[] { ("ERA4_Table", Rect.MinMaxRect(-2.8f, -2.12f, -1.0f, -1.52f)) },
            },
            // 53.3 m² (was 41): 1.5 m more at the back; the line runs from the counter along the east wall.
            ["Era5_Quitanda"] = new ShopPlan
            {
                floor = Rect.MinMaxRect(-4.1f, -2.4f, 4.1f, 4.1f), doorMin = -3.45f, doorMax = .55f, oldFloor = Rect.MinMaxRect(-4.1f, -2.4f, 4.1f, 2.6f),
                counter = Rect.MinMaxRect(1.35f, -1.7f, 3.15f, -.3f), floorY = .06f, wait = new Vector2(1.1f, -3.7f),
                queue = new[] { new Vector2(2.25f, -2.0f), new Vector2(3.05f, -2.0f), new Vector2(3.65f, -1.5f), new Vector2(3.65f, -.75f), new Vector2(3.65f, 0f), new Vector2(3.65f, .75f), new Vector2(3.65f, 1.5f), new Vector2(3.65f, 2.25f), new Vector2(3.65f, 3.0f) },
                solids = new[] { ("ERA5_Produce", Rect.MinMaxRect(.78f, -3.22f, 3.52f, -2.66f)) },
            },
            // 86.1 m² (was 66.1): 0.5 m more on the west side, 1.45 m more at the back; the east wall (where the player
            // places the checkouts) and the door stay where they were.
            ["Era6_Minimercado"] = new ShopPlan
            {
                floor = Rect.MinMaxRect(-6.15f, -2.9f, 5.65f, 4.4f), doorMin = -1.2f, doorMax = .2f, oldFloor = Rect.MinMaxRect(-5.65f, -2.9f, 5.65f, 2.95f),
                counter = Rect.MinMaxRect(2.55f, -2.75f, 3.95f, -.75f), floorY = .16f, placedCounter = true, wait = new Vector2(1.0f, -4.35f),
                queue = new[] { new Vector2(2.25f, -1.75f) },
            },
        };
        /// <summary>The current expansion is a shop with an inside the player furnishes (Späti, quitanda, minimercado).</summary>
        public static bool ShopInside { get; private set; }
        /// <summary>The shop has no counter of its own (minimercado): the player places the game's checkout in the
        /// checkout area along the east wall, like in the market building (CheckoutInterior.CheckoutZone).</summary>
        public static bool PlacedCounter { get; private set; }
        // Model parts of that shop's old counter (register and stool), hidden in the game.
        static readonly Dictionary<string, string> CounterParts = new Dictionary<string, string> { ["Era6_Minimercado"] = "ERA6_Counter" };
        /// <summary>Inner floor of the shop (world x/z) where shelves and coolers may stand.</summary>
        public static Rect InteriorFloor { get; private set; }
        /// <summary>The fixed counter of the shop (world x/z): nothing else may stand there.</summary>
        public static Rect CounterArea { get; private set; }
        /// <summary>Centre of the door opening (world x/z) and its half width.</summary>
        public static Vector2 Door { get; private set; }
        public static float DoorHalf { get; private set; }
        /// <summary>World height of the shop floor (where the placed furniture stands).</summary>
        public static float FloorY { get; private set; }
        static Vector2[] queuePlan = new Vector2[0]; static Vector2 waitPlan; static float planScale = 1; static Vector3 planOrigin;
        /// <summary>A stall with no inside (mesinha, tenda, banca, contêiner): what the player buys for it (the bread
        /// basket...) stands on the paving around the stall, in <see cref="InteriorFloor"/> (the stall's yard).</summary>
        public static bool Yard => Small && !ShopInside;
        /// <summary>The stall model itself (world x/z) while <see cref="Yard"/>: nothing may stand there.</summary>
        public static Rect StallArea { get; private set; }
        /// <summary>In front of the stall, where customers pick from the crates and queue to pay: kept free.</summary>
        public static Rect StallFront { get; private set; }
        /// <summary>Fixtures that are part of the stall model in this expansion (the register, the produce crates,
        /// the styrofoam cooler, the fair stall's display): they stay where the stall has them and are never placed
        /// in build mode. In the first expansions nothing is relocated; the shops are furnished piece by piece.</summary>
        public static bool BuiltIn(string pieceId)
        {
            if (!Yard) return false;
            switch (pieceId)
            {
                case "checkout:main": case "shelf:produce": case "shelf:drinks": return true;
                case "shelf:dairy": return Era >= 2;
                case "shelf:snacks": return Era >= 3;
                default: return false;
            }
        }
        // Lot A1 (src/data/market-lots.ts): the stall's yard never leaves it.
        const float LotMinX = -17.25f, LotMaxX = -5.75f, LotMaxZ = 4.75f;
        /// <summary>Solid parts of the stall for the navigation: walls with the door left open and the counter in a
        /// shop, the whole model otherwise.</summary>
        public static readonly List<Bounds> Obstacles = new List<Bounds>();

        void PlanShop(GameObject model)
        {
            Obstacles.Clear();
            ShopInside = Small && model && Plans.TryGetValue(model.name, out _);
            PlacedCounter = false;
            if (!ShopInside) { Obstacles.Add(Footprint); PlanYard(); return; }
            var plan = Plans[model.name];
            PlacedCounter = plan.placedCounter;
            var o = model.transform.position; float k = model.transform.localScale.x;
            Vector2 W(float x, float z) => new Vector2(o.x + x * k, o.z + z * k);
            Rect WR(Rect r) { var a = W(r.xMin, r.yMin); var b = W(r.xMax, r.yMax); return Rect.MinMaxRect(a.x, a.y, b.x, b.y); }
            var f = WR(plan.floor); InteriorFloor = f; CounterArea = WR(plan.counter); FloorY = o.y + plan.floorY * k;
            var d0 = W(plan.doorMin, plan.floor.yMin); var d1 = W(plan.doorMax, plan.floor.yMin);
            Door = new Vector2((d0.x + d1.x) * .5f, f.yMin); DoorHalf = (d1.x - d0.x) * .5f;
            queuePlan = plan.queue ?? new Vector2[0]; waitPlan = plan.wait; planScale = k; planOrigin = o; queueBuilt = -1;
            // The line's lane on the new floor is kept free of furniture (build mode): a piece a player placed before
            // the shop grew stands on the old floor and never on it, so it stays valid where it is.
            ReservedQueue.Clear();
            if (!plan.placedCounter) for (int i = 1; i < queuePlan.Length; i++) if (!plan.oldFloor.Contains(queuePlan[i])) ReservedQueue.Add(W(queuePlan[i].x, queuePlan[i].y));
            var keep0 = plan.keepMax > plan.keepMin ? W(plan.keepMin, 0).x : d0.x; var keep1 = plan.keepMax > plan.keepMin ? W(plan.keepMax, 0).x : d1.x;
            KeepClear = new Vector2((keep0 + keep1) * .5f, (keep1 - keep0) * .5f);
            const float t = .35f, h = 2f;
            // Parts of the model outside the walls (the produce stand under the window...): people walk round them.
            foreach (var (part, rect) in plan.solids ?? new (string, Rect)[0])
            {
                bool present = false; foreach (var tr in model.GetComponentsInChildren<Transform>(false)) if (tr.name.StartsWith(part)) { present = true; break; }
                if (!present) continue;
                var r = WR(rect); Obstacles.Add(new Bounds(new Vector3(r.center.x, 1f, r.center.y), new Vector3(r.width, h, r.height)));
            }
            void Wall(float x0, float z0, float x1, float z1) { if (x1 - x0 > .05f && z1 - z0 > .05f) Obstacles.Add(new Bounds(new Vector3((x0 + x1) * .5f, 1f, (z0 + z1) * .5f), new Vector3(x1 - x0, h, z1 - z0))); }
            Wall(f.xMin - t, f.yMax, f.xMax + t, f.yMax + t);           // back
            Wall(f.xMin - t, f.yMin - t, f.xMin, f.yMax);               // left
            Wall(f.xMax, f.yMin - t, f.xMax + t, f.yMax);               // right
            Wall(f.xMin - t, f.yMin - t, d0.x, f.yMin);                 // front, left of the door
            Wall(d1.x, f.yMin - t, f.xMax + t, f.yMin);                 // front, right of the door
            if (PlacedCounter) { CounterArea = new Rect(f.xMax, f.yMin, 0, 0); return; } // no counter in the model
            var c = CounterArea; Wall(c.xMin, c.yMin, c.xMax, c.yMax);  // counter
        }

        // The paving around the stall: beside and behind it on lot A1, inside the walkable court, plus a strip in
        // front of it (kept free for the shoppers, StallFront).
        static void PlanYard()
        {
            var f = Footprint; var court = Court;
            StallArea = Rect.MinMaxRect(f.min.x, f.min.z, f.max.x, f.max.z);
            StallFront = Rect.MinMaxRect(f.min.x - .4f, FrontLine - 1.15f, f.max.x + 1.6f, FrontLine);
            float x0 = Mathf.Max(LotMinX + .3f, court.min.x + .3f, f.min.x - 3f), x1 = Mathf.Min(LotMaxX - .3f, court.max.x - .3f, f.max.x + 3f);
            float z0 = Mathf.Max(court.min.z + .3f, FrontLine - 1.5f), z1 = Mathf.Min(LotMaxZ - .3f, court.max.z - .3f, f.max.z + 2.5f);
            InteriorFloor = Rect.MinMaxRect(x0, z0, x1, Mathf.Max(z1, f.max.z + .5f));
            CounterArea = StallArea; FloorY = .13f;
            Door = new Vector2(f.center.x, FrontLine); DoorHalf = f.size.x * .5f;
        }

        /// <summary>Places of the line (world x/z) that build mode keeps free of furniture (the lane on the floor the shop
        /// grew by).</summary>
        public static readonly List<Vector2> ReservedQueue = new List<Vector2>();
        /// <summary>The way in kept free of furniture inside the door (world x centre, half width): the door, or where the
        /// door was before the shop grew, so no piece a player placed then stands in the way in now.</summary>
        public static Vector2 KeepClear { get; private set; }

        // ------------------------------------------------------------------ the line and the room inside a shop
        // The places of the line (world), from the plan: a place a piece of furniture now stands on (the player's own
        // layout from before the shop grew), the doorway or the counter is skipped, and the line goes on behind; with
        // fewer than three left it carries on at the free spots nearest its end. Rebuilt when the furniture moves.
        static readonly List<Vector3> queueSpots = new List<Vector3>();
        static int queueBuilt = -1; static float queueAt = -99;
        /// <summary>Places in the line inside the shop.</summary>
        public static int QueueInside { get { if (!ShopInside) return 3; BuildQueue(); var inside = CheckoutInterior.Active; return PlacedCounter && inside && inside.Get("checkout:main") != null ? inside.QueueLength("checkout:main") : Mathf.Max(1, queueSpots.Count); } }
        /// <summary>How many customers may be inside the shop at once (shopping, in line, paying): the rest wait outside.
        /// About one per 3 m² of floor left free by the furniture and the counter, never more than the line can take.</summary>
        public static int Capacity { get { if (!ShopInside) return 99; BuildQueue(); return capacity; } }
        static int capacity = 99;
        static Rect DoorZone => Rect.MinMaxRect(Door.x - DoorHalf - .25f, Door.y - .2f, Door.x + DoorHalf + .25f, Door.y + 1.3f);
        static void BuildQueue()
        {
            var inside = CheckoutInterior.Active;
            int sign = inside ? inside.items.Count * 7919 : 0;
            if (inside) foreach (var it in inside.items.Values) if (it.root && !it.outside) sign += Mathf.RoundToInt(it.root.position.x * 13 + it.root.position.z * 31 + it.rot);
            sign ^= Mathf.RoundToInt(InteriorFloor.xMin * 101 + InteriorFloor.yMax * 59) ^ (PlacedCounter ? 1 : 0);
            if (sign == queueBuilt && Time.unscaledTime - queueAt < 2f) return;
            queueBuilt = sign; queueAt = Time.unscaledTime; queueSpots.Clear();
            var boxes = new List<CheckoutInterior.Footprint>();
            if (inside) foreach (var it in inside.items.Values) if (it.root && !it.outside) boxes.Add(inside.FootprintOf(it, .3f));
            var f = InteriorFloor; var door = DoorZone; var counter = CounterArea;
            bool Free(Vector2 q)
            {
                if (q.x < f.xMin + .35f || q.x > f.xMax - .35f || q.y < f.yMin + .3f || q.y > f.yMax - .35f) return false;
                if (door.Contains(q)) return false;
                if (!PlacedCounter && Rect.MinMaxRect(counter.xMin - .3f, counter.yMin - .3f, counter.xMax + .3f, counter.yMax + .3f).Contains(q)) return false;
                foreach (var b in boxes) if (CheckoutInterior.Contains(b, q)) return false;
                foreach (var s in queueSpots) if ((new Vector2(s.x, s.z) - q).sqrMagnitude < .55f * .55f) return false;
                return true;
            }
            Vector3 Spot(Vector2 m) { var w = new Vector2(planOrigin.x + m.x * planScale, planOrigin.z + m.y * planScale); return new Vector3(w.x, .15f, w.y); }
            for (int i = 0; i < queuePlan.Length; i++)
            {
                var s = Spot(queuePlan[i]); var q = new Vector2(s.x, s.z);
                // where the customer pays always counts (the counter is there); the places behind only when free
                if (i == 0 || Free(q)) queueSpots.Add(s);
            }
            // Short line (furniture on the lane): free spots around its end, never in the doorway.
            for (int tries = 0; queueSpots.Count < 3 && queueSpots.Count > 0 && tries < 4; tries++)
            {
                var end = queueSpots[queueSpots.Count - 1]; bool added = false;
                for (float r = .75f; r < 3.5f && !added; r += .25f)
                    for (int k = 0; k < 16 && !added; k++)
                    {
                        float a = k * Mathf.PI / 8; var q = new Vector2(end.x + Mathf.Cos(a) * r, end.z + Mathf.Sin(a) * r);
                        if (Free(q)) { queueSpots.Add(new Vector3(q.x, .15f, q.y)); added = true; }
                    }
                if (!added) break;
            }
            // Room for people: the floor left free by the furniture (counted without the padding) and the counter.
            float area = f.width * f.height;
            if (inside) foreach (var it in inside.items.Values) if (it.root && !it.outside) { var b = inside.FootprintOf(it); area -= 4 * b.hx * b.hz; }
            if (!PlacedCounter) area -= counter.width * counter.height;
            int line = PlacedCounter && inside ? Mathf.Max(4, inside.QueueLength("checkout:main") + (inside.Get("checkout:extra") != null ? inside.QueueLength("checkout:extra") : 0) + 6) : queueSpots.Count;
            capacity = Mathf.Clamp(Mathf.FloorToInt(area / 3f), 3, Mathf.Max(3, line));
        }
        /// <summary>Outside the shop, where the i-th customer waiting to get in stands (3 a row by the door, rows towards
        /// the street).</summary>
        public static Vector3 WaitSpot(int i)
        {
            var m = waitPlan + new Vector2(.75f * (i % 3), -.75f * (i / 3));
            return new Vector3(planOrigin.x + m.x * planScale, .15f, planOrigin.z + m.y * planScale);
        }

        // ------------------------------------------------------------------ points for the customers
        public static Vector3 Entrance => ShopInside ? new Vector3(Door.x, .15f, Door.y - 1.6f) : Era <= 0 ? new Vector3(Centre.x - 3.2f, .15f, FrontZ) : new Vector3(Centre.x - .55f, .15f, -9.7f);
        public static Vector3 Crate(string id)
        {
            int i = Mathf.Abs((id ?? "").GetHashCode()) % CrateX.Length;
            return new Vector3(Centre.x + CrateX[i] * Scale, 1.1f, Centre.z - .4f);
        }
        public static Vector3 Approach(string id)
        {
            var crate = Crate(id);
            return new Vector3(crate.x, .15f, FrontZ);
        }
        public static Vector3 Register => ShopInside ? new Vector3((CounterArea.xMin + CounterArea.xMax) * .5f, .9f, (CounterArea.yMin + CounterArea.yMax) * .5f) : new Vector3(Centre.x + 1.1f, .9f, Centre.z - .6f);
        public static Vector3 QueueSpot(int i)
        {
            // In a shop the line starts at the counter and runs along its own lane, never across the doorway (the shop
            // lets in no more people than it has places for; the rare extra one waits at the last place's side).
            if (ShopInside)
            {
                BuildQueue();
                if (queueSpots.Count == 0) return new Vector3(Register.x, .15f, Register.z - 1f);
                if (i < queueSpots.Count) return queueSpots[i];
                var last = queueSpots[queueSpots.Count - 1]; var before = queueSpots.Count > 1 ? queueSpots[queueSpots.Count - 2] : last + Vector3.back;
                var side = Vector3.Cross(Vector3.up, (last - before).normalized);
                return last + side * (.6f * (1 + (i - queueSpots.Count) % 2) * ((i - queueSpots.Count) % 2 == 0 ? 1 : -1));
            }
            // A short line from the cooler end of the stall towards the sidewalk.
            var p = new Vector3(Centre.x + 1.9f, .15f, FrontZ - .1f);
            if (i <= 0) return p;
            return i < 3 ? p + new Vector3(.25f * i, 0, -.85f * i) : p + new Vector3(.5f + .85f * (i - 2), 0, -1.7f);
        }

        /// <summary>Walkable paving in front of and around the stall while a small era is on.</summary>
        public static Bounds Court
        {
            get
            {
                // The sidewalk in front of the stall, grown to walk around the bigger shops (quitanda, minimercado).
                var court = new Bounds(new Vector3(Centre.x, .05f, -5.25f), new Vector3(11f, .2f, 8.5f));
                var f = Footprint;
                court.Encapsulate(new Bounds(new Vector3(f.center.x, .05f, f.center.z), new Vector3(f.size.x + 3f, .2f, f.size.z + 3f)));
                return court;
            }
        }

        /// <summary>Ground the shown model covers (a solid block for the navigation).</summary>
        public static Bounds Footprint { get; private set; } = new Bounds(new Vector3(-11.5f, 1f, -4.9f), new Vector3(4.2f, 2f, 2.7f));
        // Every model stands with its front on this line, so bigger eras grow towards the back of the lot.
        static float FrontLine => Era <= 0 ? -9.9f : -6.3f;

        // ------------------------------------------------------------------ era switch
        public void Apply(Snapshot snapshot)
        {
            var state = snapshot?.era;
            bool known = state != null && !string.IsNullOrEmpty(state.id);
            int era = known ? state.index : EraModels.Length;
            bool small = known && !state.building && !CheckoutMapEditor.Open;
            bool changed = small != Small;
            int wasFloor = ShopInside ? 2 : Yard ? 1 : 0, wasEra = Era; // (before Small changes: Yard reads it)
            Era = era; Small = small;
            if (small) HideMarket();
            else if (changed) ShowMarket();
            if (sites) sites.Apply(snapshot);
            if (works) works.Apply(snapshot);
            ShowModel(small ? ModelFor(era) : null);
            if (!small) { ShopInside = false; PlacedCounter = false; Obstacles.Clear(); }
            // The furniture the player placed stands inside the shop expansions, or around the stall (its yard).
            var holder = map.Interior ? map.Interior.Holder : null;
            if (holder && small) { holder.gameObject.SetActive(true); hidden.Remove(holder.gameObject); }
            // Entering or leaving a shop or stall expansion: the furniture moves between its floor and the market's
            // (from one stall to the next, the stall's own fixtures change too: CheckoutStall.BuiltIn). From one shop to
            // the next (Späti -> quitanda) the floor changes size: the furniture was just measured against the old one
            // (CheckoutMap.Apply runs this last), so it is put on the new floor again now, not at the next snapshot.
            int floor = ShopInside ? 2 : Yard ? 1 : 0;
            if ((wasFloor != floor || (floor != 0 && wasEra != era)) && map.Interior)
            {
                map.Reapply();
                foreach (var it in map.Interior.items.Values) map.Interior.Place(it);
            }
            if (changed && simulation && map.Layout) simulation.RebuildLayoutNavigation(map.Layout.State);
        }

        static readonly string[] MarketRoots =
        {
            "Building", "Market Shell", "Market Stage Dressing", "Checkout", "Produce", "Butcher", "Fishery", "Bakery",
            "Groceries", "Owned Shelf Slots", "Sector Construction", "Anim_Door_Left", "Anim_Door_Right", "Market Staff",
            "Worker_Delivery", "Warehouse", "Loading Yard Details", "Supplied Delivery Cargo", "Delivery",
        };

        void Hide(GameObject go)
        {
            if (!go || !go.activeSelf) return;
            go.SetActive(false);
            if (!hidden.Contains(go)) hidden.Add(go);
        }

        void HideMarket()
        {
            foreach (var name in MarketRoots) { var t = world.Find(name); if (t) Hide(t.gameObject); else { var go = GameObject.Find(name); if (go) Hide(go); } }
            foreach (Transform t in world)
                if (t.name.StartsWith("Stock_") || t.name.StartsWith("ReplacementVisual") || t.name.StartsWith("Sector_") ||
                    t.name.StartsWith("Worker_") || t.name.StartsWith("Employee_") || t.name.StartsWith("Anim_Truck"))
                    Hide(t.gameObject);
            // (the interior holder is shown or hidden after the model is placed: shops keep their furniture)
            // Shelf markers and click targets of the building live under the map object.
            foreach (Transform t in map.transform)
                if (t.name.StartsWith("Status ") || t.name.StartsWith("Open ") || t.name.StartsWith("Upgrade ")) Hide(t.gameObject);
        }

        void ShowMarket()
        {
            foreach (var go in hidden) if (go) go.SetActive(true);
            hidden.Clear();
            map.Reapply();
        }

        // Front on FrontLine, centred on Centre.x; the footprint follows the visible parts.
        void Place(GameObject model)
        {
            model.transform.position = Centre;
            var renderers = model.GetComponentsInChildren<Renderer>(false);
            if (renderers.Length == 0) return;
            var b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
            // A walk-in shop stands with its model origin on Centre.x (its floor keeps its world coordinates when the
            // model grows to one side: the furniture players placed stays where it was); a stall is centred on it.
            float dx = Plans.ContainsKey(model.name) ? Centre.x - model.transform.position.x : Centre.x - b.center.x;
            model.transform.position += new Vector3(dx, 0, FrontLine - b.min.z);
            b.center += new Vector3(dx, 0, FrontLine - b.min.z);
            Footprint = new Bounds(new Vector3(b.center.x, 1f, b.center.z), new Vector3(b.size.x, 2f, b.size.z));
            PlanShop(model);
            if (simulation && map.Layout) simulation.RebuildLayoutNavigation(map.Layout.State);
        }

        // Index = expansion index of the stall eras (the market building starts after the last one).
        static readonly string[] EraModels = { "Era0_Mesinha", "Era1_Tenda", "Era2_Banca", "Era3_Conteiner", "Era4_Spati", "Era5_Quitanda", "Era6_Minimercado" };

        // The era's own model, or the closest earlier one while its model is not in the game yet.
        string ModelFor(int era)
        {
            for (int i = Mathf.Clamp(era, 0, EraModels.Length - 1); i >= 0; i--)
            {
                var name = EraModels[i];
                if (models.TryGetValue(name, out var cached) ? cached : Resources.Load<GameObject>("CheckoutEras/" + name)) return name;
            }
            return EraModels[0];
        }

        void ShowModel(string name)
        {
            if (shown && shown.name != name) { shown.SetActive(false); shown = null; }
            if (name == null) return;
            if (!models.TryGetValue(name, out var model))
            {
                model = Load(name);
                models[name] = model;
            }
            if (!model) { if (Small) PlanShop(null); return; } // no model: plain yard around the default footprint
            model.SetActive(true);
            bool changed = shown != model;
            shown = model;
            if (changed) Place(model);
        }

        // Shop windows, fridge doors and freezer lids (Blender material "EraGlass"): see-through.
        static Material glass;
        static Material Glass()
        {
            if (glass) return glass;
            glass = new Material(Shader.Find("Standard")) { name = "Era glass" };
            glass.SetFloat("_Mode", 3);
            glass.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.One);
            glass.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            glass.SetInt("_ZWrite", 0);
            glass.DisableKeyword("_ALPHATEST_ON");
            glass.DisableKeyword("_ALPHABLEND_ON");
            glass.EnableKeyword("_ALPHAPREMULTIPLY_ON");
            glass.renderQueue = 3000;
            glass.color = new Color(.75f, .88f, .95f, .25f);
            glass.SetFloat("_Glossiness", .9f);
            return glass;
        }

        GameObject Load(string name)
        {
            var prefab = Resources.Load<GameObject>("CheckoutEras/" + name);
            if (!prefab) { Debug.LogWarning("CHECKOUT_STALL missing model CheckoutEras/" + name); return null; }
            var go = Instantiate(prefab, world);
            go.name = name;
            go.transform.SetPositionAndRotation(Centre, Quaternion.identity);
            // The Blender set is modelled in real metres; the game's characters are a bit taller than life.
            go.transform.localScale = Vector3.one * Scale;
            var texture = Resources.Load<Texture2D>("CheckoutEras/" + name + "_BaseColor");
            var material = new Material(Shader.Find("Standard")) { name = name + " (baked)" };
            if (texture) material.mainTexture = texture;
            material.SetFloat("_Glossiness", .12f);
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++)
                    mats[i] = mats[i] && mats[i].name.Contains("Glass") ? Glass() : material;
                r.sharedMaterials = mats;
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            }
            // Roof and upper walls (objects named "CUT_…" in Blender) stay off so the camera sees inside,
            // like the low walls of the market building.
            foreach (var t in go.GetComponentsInChildren<Transform>(true))
                if (t.name.StartsWith("CUT_")) t.gameObject.SetActive(false);
            // The tent's bread basket is the one the player buys and places (shelf "bakery"), not part of the tent.
            foreach (var t in go.GetComponentsInChildren<Transform>(true))
                if (t.name.StartsWith("ERA1_Bread")) t.gameObject.SetActive(false);
            // A shop where the player places the checkout loses the counter of the model (and its click).
            if (CounterParts.TryGetValue(name, out var counterPrefix))
            {
                foreach (var t in go.GetComponentsInChildren<Transform>(true))
                    if (t.name.StartsWith(counterPrefix)) t.gameObject.SetActive(false);
                return go;
            }
            // Clicking the stall opens the playable checkout, like the register of the market.
            var click = new GameObject("Stall checkout");
            click.transform.SetParent(go.transform, false);
            click.transform.localPosition = new Vector3(1.25f, .8f, -.6f);
            var box = click.AddComponent<BoxCollider>(); box.size = new Vector3(1.2f, 1.6f, 1.2f);
            // A shop's own counter (Späti, quitanda) is further in: the box covers that counter and its register.
            if (Plans.TryGetValue(name, out var shop))
            {
                var c = shop.counter;
                click.transform.localPosition = new Vector3(c.center.x, shop.floorY + .8f, c.center.y);
                box.size = new Vector3(c.width + .2f, 1.6f, c.height + .2f);
            }
            click.AddComponent<CheckoutTarget>().panel = "checkout";
            return go;
        }
    }
}
