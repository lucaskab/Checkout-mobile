using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    // Walking routes across the market block for the scripted visitors (bench sitters). The block has no
    // navigation mesh of its own, so a coarse grid is rasterised from what stands on it right now: the shop,
    // the storages, the fenced lot, construction sites and every bench, planter, bin, lamp and tree trunk.
    // Routes are A* on that grid, then straightened wherever the way is clear.
    public static class CheckoutBlockPaths
    {
        public const float MinX = -18f, MaxX = 18f, MinZ = -10f, MaxZ = 46f, Cell = .5f;
        static readonly int W = Mathf.CeilToInt((MaxX - MinX) / Cell), H = Mathf.CeilToInt((MaxZ - MinZ) / Cell);
        static bool[] blocked, fixedBlocked;
        static float builtAt = -99;
        // Decorations the player placed on the block (build mode): visitors walk around them too.
        public static System.Func<IEnumerable<Bounds>> Extras;
        public static void Invalidate() => builtAt = -99;
        static readonly string[] BuildingRoots = { "Market Shell", "Warehouse", "Warehouse Large", "Abandoned Warehouse (future expansion)" };
        static readonly string[] FurnitureRoots = { "Harbour Quay Plaza", "Individual Street Furniture", "Expansion Park", "Market Stage Dressing", "Loading Yard Details", "Landscape Models" };

        static int Index(int x, int z) => z * W + x;
        static bool Inside(int x, int z) => x >= 0 && z >= 0 && x < W && z < H;
        static Vector2Int CellOf(Vector3 p) => new Vector2Int(Mathf.Clamp(Mathf.FloorToInt((p.x - MinX) / Cell), 0, W - 1), Mathf.Clamp(Mathf.FloorToInt((p.z - MinZ) / Cell), 0, H - 1));
        static Vector3 Center(int x, int z, float y) => new Vector3(MinX + (x + .5f) * Cell, y, MinZ + (z + .5f) * Cell);

        static void Block(Bounds b, float pad)
        {
            var a = CellOf(b.min - new Vector3(pad, 0, pad)); var c = CellOf(b.max + new Vector3(pad, 0, pad));
            for (int z = a.y; z <= c.y; z++) for (int x = a.x; x <= c.x; x++) blocked[Index(x, z)] = true;
        }

        // Rebuilt at most every few seconds; expansions and construction sites change the block.
        static void Build()
        {
            if (blocked != null && Time.time - builtAt < 4f) return;
            builtAt = Time.time;
            blocked = new bool[W * H];
            var world = GameObject.Find("Supermarket World");
            if (!world) { fixedBlocked = blocked; return; }
            foreach (var name in BuildingRoots)
            {
                var root = world.transform.Find(name);
                if (!root || !root.gameObject.activeInHierarchy) continue;
                var rs = root.GetComponentsInChildren<Renderer>();
                if (rs.Length == 0) continue;
                var b = rs[0].bounds; foreach (var r in rs) if (!(r is ParticleSystemRenderer)) b.Encapsulate(r.bounds);
                Block(b, .35f);
            }
            foreach (var go in Object.FindObjectsByType<Transform>(FindObjectsSortMode.None))
                if (go.parent == null && go.name.StartsWith("Construction site"))
                {
                    var rs = go.GetComponentsInChildren<Renderer>();
                    if (rs.Length == 0) continue;
                    var b = rs[0].bounds; foreach (var r in rs) if (!(r is ParticleSystemRenderer) && r.bounds.size.y < 12) b.Encapsulate(r.bounds);
                    Block(b, .3f);
                }
            // Plus whatever the map design moved or added (CheckoutDesignWorld), wherever it sits in the scene.
            var furniture = new List<Transform>();
            foreach (var name in FurnitureRoots) { var root = world.transform.Find(name); if (root && root.gameObject.activeInHierarchy) furniture.Add(root); }
            var design = CheckoutDesignWorld.Active;
            if (design)
            {
                if (design.CloneRoot) furniture.Add(design.CloneRoot);
                foreach (var o in design.Overrides) { var t = o.hidden ? null : CheckoutMapDesign.Find(o.path); if (t && !furniture.Any(f => t.IsChildOf(f))) furniture.Add(t); }
            }
            foreach (var root in furniture)
            {
                foreach (var r in root.GetComponentsInChildren<Renderer>())
                {
                    if (r is ParticleSystemRenderer || r.GetComponent<TextMesh>() || r.forceRenderingOff) continue;
                    var b = r.bounds;
                    if (b.max.x < MinX || b.min.x > MaxX || b.max.z < MinZ || b.min.z > MaxZ) continue;
                    if (b.size.y < .12f) continue;                  // paving, markings
                    if (b.min.y > 1.1f) continue;                    // canopies, lamp heads, awnings
                    bool tree = r.name.IndexOf("Tree", System.StringComparison.OrdinalIgnoreCase) >= 0 || r.name.StartsWith("Trunk") || b.size.y > 2.5f;
                    if (tree) { Block(new Bounds(new Vector3(b.center.x, 0, b.center.z), new Vector3(.6f, 1, .6f)), .2f); continue; }
                    if (b.size.x * b.size.z > 40f) continue;         // big ground pieces
                    Block(b, .25f);
                }
            }
            fixedBlocked = (bool[])blocked.Clone();
            if (Extras != null) foreach (var b in Extras()) Block(b, .25f);
        }

        // Free of buildings and street furniture (ignores the player's own decorations).
        public static bool FixedFree(Vector3 p)
        {
            Build();
            if (p.x < MinX || p.x > MaxX || p.z < MinZ || p.z > MaxZ) return false;
            var c = CellOf(p); return !fixedBlocked[Index(c.x, c.y)];
        }

        public static bool Free(Vector3 p) { Build(); var c = CellOf(p); return !blocked[Index(c.x, c.y)]; }

        // A spot on the footway around the block, where visitors come from and go back to.
        public static Vector3 EdgePoint()
        {
            Build();
            for (int i = 0; i < 20; i++)
            {
                Vector3 p;
                float r = Random.value;
                // Side footways only: the front of the block is the shop entrance, where a visitor
                // vanishing would look like someone walking into the (possibly closed) market.
                p = new Vector3(r < .5f ? MinX + .6f : MaxX - .6f, 0, Random.Range(2f, 44f));
                if (Free(p)) return p;
            }
            return new Vector3(MaxX - .6f, 0, 10);
        }

        public static List<Vector3> Route(Vector3 from, Vector3 to)
        {
            Build();
            var start = CellOf(from); var goal = CellOf(to);
            // The bench's own approach cell is always allowed, even though the bench is an obstacle.
            var open = new SortedSet<(float f, int id)>();
            var g = new Dictionary<int, float>(); var came = new Dictionary<int, int>();
            int s = Index(start.x, start.y), e = Index(goal.x, goal.y);
            g[s] = 0; open.Add((Heuristic(start, goal), s));
            int[] dx = { 1, -1, 0, 0, 1, 1, -1, -1 }, dz = { 0, 0, 1, -1, 1, -1, 1, -1 };
            int guard = 0;
            while (open.Count > 0 && guard++ < 20000)
            {
                var cur = open.Min; open.Remove(cur);
                if (cur.id == e) break;
                int cx = cur.id % W, cz = cur.id / W;
                for (int k = 0; k < 8; k++)
                {
                    int nx = cx + dx[k], nz = cz + dz[k];
                    if (!Inside(nx, nz)) continue;
                    int n = Index(nx, nz);
                    if (blocked[n] && n != e && n != s) continue;
                    if (k >= 4 && (blocked[Index(cx + dx[k], cz)] || blocked[Index(cx, cz + dz[k])])) continue; // no corner cutting
                    float cost = g[cur.id] + (k < 4 ? 1f : 1.414f);
                    if (g.TryGetValue(n, out var old) && old <= cost) continue;
                    if (g.ContainsKey(n)) open.Remove((old + Heuristic(new Vector2Int(nx, nz), goal), n));
                    g[n] = cost; came[n] = cur.id;
                    open.Add((cost + Heuristic(new Vector2Int(nx, nz), goal), n));
                }
            }
            var path = new List<Vector3>();
            if (!came.ContainsKey(e) && s != e) { path.Add(to); return path; }
            var cells = new List<int>();
            for (int c = e; c != s; c = came[c]) cells.Add(c);
            cells.Reverse();
            // String pulling: keep only corners where the straight way is blocked.
            var anchor = from; int last = -1;
            for (int i = 0; i < cells.Count; i++)
            {
                var p = Center(cells[i] % W, cells[i] / W, from.y);
                if (!Clear(anchor, p) && last >= 0)
                {
                    var corner = Center(cells[last] % W, cells[last] / W, from.y);
                    path.Add(corner); anchor = corner;
                }
                last = i;
            }
            path.Add(to);
            return path;
        }

        static float Heuristic(Vector2Int a, Vector2Int b) => Vector2Int.Distance(a, b);

        static bool Clear(Vector3 a, Vector3 b)
        {
            float d = Vector3.Distance(new Vector3(a.x, 0, a.z), new Vector3(b.x, 0, b.z));
            int steps = Mathf.CeilToInt(d / (Cell * .5f));
            for (int i = 1; i < steps; i++)
            {
                var p = Vector3.Lerp(a, b, i / (float)steps);
                var c = CellOf(p);
                if (blocked[Index(c.x, c.y)]) return false;
            }
            return true;
        }
    }
}
