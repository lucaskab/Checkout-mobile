using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
using MarketDay;
using Tool = Checkout.CheckoutWorksScene.Tool;

namespace Checkout
{
    // The land around the market (src/services/market-lots.ts): a grid of 12 equal lots, each with its own old
    // building (abandoned house, closed shop, old gas station...). Like the locked areas of Township, Hay Day or
    // Idle Supermarket Tycoon there are no fences or sale boards: a lot that is not the player's yet has its ground
    // tinted in the colour of its status (about 25% opaque), a dashed white border a little inside its edge and a
    // padlock badge in the middle (Game/lot_lock*.png, ArtSource/lock_art.py): gold padlock on green when it can be
    // bought now, steel on slate when it is not next to the player's land yet. A bought lot shows none of it any more
    // (its ruin waits to be cleared). Clicking the lot (or its padlock) opens a small panel with what it needs (CheckoutLotPopup):
    // buy it, clear it, or speed the clearing up.
    // Clearing is a works scene that fits what stands there (CheckoutWorksScene): sledgehammers and a skip for
    // the house, a tow truck for the workshop's old car, brush cutters on the overgrown plot, a wrecking ball
    // for the factory... while the ruin comes down with the countdown.
    // The old plaza decorations that stood on the block (benches, trees, lamps, planters) are cleared away: the
    // block is all lots now; the player's own map-design objects only wait while a lot still has its ruin.
    // Ruin models: Resources/CheckoutLots/Lot_<Name> (Blender, ArtSource/lot_kit.py and lot_kit2.py).
    public class CheckoutLotSites : MonoBehaviour
    {
        /// <summary>Ruins standing on the block, solid for the navigation.</summary>
        public static readonly List<Bounds> Obstacles = new List<Bounds>();

        class Site
        {
            public string id, status, signature;
            public GameObject root, dim, dirt;
            public Transform ruin, marker;
            public Renderer fill, dash, badge;
            public Collider click, lockClick;
            public LotRect lot;
            public CheckoutWorksScene works;
            public float top;
            public readonly List<GameObject> hidden = new List<GameObject>();
        }

        Transform world; MarketSimulation simulation; CheckoutMap map;
        readonly Dictionary<string, Site> sites = new Dictionary<string, Site>();
        // Every lot of the last snapshot (also the cleared ones, whose site is gone): where to celebrate.
        readonly Dictionary<string, LotRect> known = new Dictionary<string, LotRect>();
        readonly Dictionary<string, Material> areaMats = new Dictionary<string, Material>();
        static Texture2D dashTexture;
        float clock;
        public double Coins { get; private set; }
        public double Diamonds { get; private set; }
        public bool ClearingBusy { get; private set; }

        public void Initialize(Transform root, CheckoutMap owner)
        {
            world = root; map = owner; simulation = FindAnyObjectByType<MarketSimulation>();
        }

        // ------------------------------------------------------------------ snapshot
        public void Apply(Snapshot snapshot)
        {
            var era = snapshot?.era;
            if (snapshot != null) { Coins = snapshot.coins; Diamonds = snapshot.diamonds; }
            var lots = era?.lotRects;
            if (!CheckoutMapEditor.Open) ClearBlock();
            var want = new HashSet<string>();
            bool changed = false;
            ClearingBusy = false;
            if (lots != null) foreach (var lot in lots) if (lot != null) { known[lot.id] = lot; if (lot.status == "limpando") ClearingBusy = true; }
            if (lots != null && !CheckoutMapEditor.Open)
                foreach (var lot in lots)
                {
                    if (lot == null || string.IsNullOrEmpty(lot.status) || lot.occupied) continue;
                    if (lot.status != "venda" && lot.status != "bloqueado" && lot.status != "comprado" && lot.status != "limpando") continue;
                    want.Add(lot.id);
                    var signature = lot.status + ":" + lot.clearEndsAt;
                    if (sites.TryGetValue(lot.id, out var existing))
                    {
                        existing.lot = lot;
                        if (existing.signature == signature) continue;
                        bool wasLocked = existing.status == "venda" || existing.status == "bloqueado";
                        existing.signature = signature; existing.status = lot.status;
                        // Just bought: its padlock pops open before the marker goes away.
                        if (wasLocked && lot.status != "venda" && lot.status != "bloqueado" && existing.marker && existing.marker.gameObject.activeSelf)
                            CheckoutConquestFx.Instance.LockPop(existing.marker, Resources.Load<Texture2D>("CheckoutDesktop/Game/lot_lock_open"));
                        Refresh(existing);
                        continue;
                    }
                    sites[lot.id] = Build(lot, signature);
                    changed = true;
                }
            foreach (var id in new List<string>(sites.Keys))
            {
                if (want.Contains(id)) continue;
                Remove(sites[id]); sites.Remove(id); changed = true;
            }
            if (changed) RebuildObstacles();
            CheckoutLotPopup.Refresh(this);
        }

        public LotRect Lot(string id) => sites.TryGetValue(id, out var s) ? s.lot : null;

        /// <summary>The lot is the player's: dust, light and confetti over it (the camera flies there when it may).
        /// Returns how long the show takes before the celebration card comes up.</summary>
        public float CelebrateLot(string id, bool moveCamera)
        {
            if (string.IsNullOrEmpty(id) || !known.TryGetValue(id, out var lot) || lot == null) return 0;
            var center = new Vector3((lot.x0 + lot.x1) * .5f, 0, (lot.z0 + lot.z1) * .5f);
            return CheckoutConquestFx.Instance.LotCleared(center, Mathf.Abs(lot.x1 - lot.x0), Mathf.Abs(lot.z1 - lot.z0), moveCamera);
        }

        void Remove(Site site)
        {
            foreach (var go in site.hidden) if (go) go.SetActive(true);
            if (site.works) Destroy(site.works.gameObject);
            if (site.root) Destroy(site.root);
        }

        void RebuildObstacles()
        {
            Obstacles.Clear();
            foreach (var site in sites.Values)
                if (site.ruin)
                {
                    var b = CheckoutWorksKit.Bounds(site.ruin.gameObject);
                    if (b.size.sqrMagnitude > 0) Obstacles.Add(new Bounds(new Vector3(b.center.x, 1f, b.center.z), new Vector3(b.size.x, 2f, b.size.z)));
                }
            if (simulation && map && map.Layout) simulation.RebuildLayoutNavigation(map.Layout.State);
        }

        // ------------------------------------------------------------------ a site
        Site Build(LotRect lot, string signature)
        {
            var site = new Site { id = lot.id, status = lot.status, signature = signature, lot = lot };
            site.root = new GameObject("Lot site " + lot.id);
            site.root.transform.SetParent(world, false);
            float x0 = lot.x0, z0 = lot.z0, x1 = lot.x1, z1 = lot.z1;
            HideDecor(site, x0, z0, x1, z1);
            site.ruin = Ruin(site.root.transform, lot.ruin, x0, z0, x1, z1);
            var rb = CheckoutWorksKit.Bounds(site.ruin.gameObject);
            site.top = rb.size.sqrMagnitude > 0 ? rb.max.y : 4f;
            // The lot is clicked on its ground (the ruins have no colliders, so a click on them reaches it).
            var click = new GameObject("Lot click"); click.transform.SetParent(site.root.transform, false);
            click.transform.position = new Vector3((x0 + x1) * .5f, .15f, (z0 + z1) * .5f);
            var box = click.AddComponent<BoxCollider>(); box.size = new Vector3(x1 - x0 - .1f, .3f, z1 - z0 - .1f);
            site.click = box;
            site.dirt = Dirt(site, x0, z0, x1, z1);
            site.dim = Area(site, x0, z0, x1, z1);
            site.marker = Badge(site, new Vector3((x0 + x1) * .5f, BadgeY, (z0 + z1) * .5f));
            Refresh(site);
            return site;
        }

        // Status changed: padlock colour, dim, the clearing works.
        void Refresh(Site site)
        {
            string st = site.status;
            // Only a lot that is still locked shows its area and padlock: once bought it is the player's (the ruin
            // waits to be cleared, clicking the ground still opens the panel).
            bool locked = st == "venda" || st == "bloqueado";
            if (site.dim) site.dim.SetActive(locked);
            if (site.fill) site.fill.sharedMaterial = AreaMaterial(st, false);
            if (site.dash) site.dash.sharedMaterial = AreaMaterial(st, true);
            if (site.marker)
            {
                site.marker.gameObject.SetActive(locked);
                if (site.badge) site.badge.sharedMaterial = AreaMaterial(st, false, true);
            }
            if (st == "limpando" && !site.works) StartClearing(site);
            if (st != "limpando" && site.works) { Destroy(site.works.gameObject); site.works = null; ResetRuin(site); }
        }

        // Map decorations (trees, benches, planters) that stand inside the lot wait until it is cleared.
        void HideDecor(Site site, float x0, float z0, float x1, float z1)
        {
            foreach (var rootName in new[] { "Map Design Objects", "Market Stage Dressing", "Harbour Quay Plaza" })
            {
                var parent = GameObject.Find(rootName);
                if (!parent) continue;
                foreach (Transform child in parent.transform)
                {
                    if (!child.gameObject.activeSelf) continue;
                    var b = CheckoutWorksKit.Bounds(child.gameObject);
                    if (b.size.sqrMagnitude <= 0) continue;
                    var c = b.center;
                    bool inside = c.x > x0 && c.x < x1 && c.z > z0 && c.z < z1;
                    bool small = b.size.x < (x1 - x0) + 1f && b.size.z < (z1 - z0) + 1f;
                    if (inside && small) { child.gameObject.SetActive(false); site.hidden.Add(child.gameObject); }
                }
            }
        }

        static readonly Dictionary<string, string> Models = new Dictionary<string, string>
        {
            ["casa"] = "Lot_Casa", ["galpao"] = "Lot_Galpao", ["entulho"] = "Lot_Entulho", ["armazem"] = "Lot_Armazem",
            ["loja"] = "Lot_Loja", ["sobrado"] = "Lot_Sobrado", ["oficina"] = "Lot_Oficina", ["posto"] = "Lot_Posto",
            ["garagem"] = "Lot_Garagem", ["mato"] = "Lot_Mato", ["fabrica"] = "Lot_Fabrica", ["patio"] = "Lot_Patio",
        };

        // The ruin stands in a holder at the lot's centre, so the clearing can shrink it in place.
        Transform Ruin(Transform parent, string ruin, float x0, float z0, float x1, float z1)
        {
            var holder = new GameObject("Ruin").transform; holder.SetParent(parent, false);
            var centre = new Vector3((x0 + x1) * .5f, .02f, (z0 + z1) * .5f + .25f);
            holder.position = centre;
            float lw = x1 - x0 - 1.4f, ld = z1 - z0 - 1.4f;
            var prefab = Models.TryGetValue(ruin ?? "", out var name) ? Resources.Load<GameObject>("CheckoutLots/" + name) : null;
            GameObject piece;
            if (prefab) piece = Instantiate(prefab);
            else
            {
                piece = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(piece.GetComponent<Collider>());
                piece.transform.localScale = new Vector3(7, 4, 6);
            }
            piece.name = name ?? "Ruin";
            piece.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            if (prefab) piece.transform.localScale = Vector3.one;
            Paint(piece);
            var b = CheckoutWorksKit.Bounds(piece);
            bool turn = (b.size.x >= b.size.z) != (lw >= ld);
            float mx = turn ? b.size.z : b.size.x, mz = turn ? b.size.x : b.size.z;
            float s = Mathf.Clamp(Mathf.Min(lw / Mathf.Max(.1f, mx), ld / Mathf.Max(.1f, mz)), .25f, 1.15f);
            piece.transform.SetParent(holder, true);
            piece.transform.localScale = piece.transform.localScale * s;
            piece.transform.rotation = Quaternion.Euler(0, turn ? 90 : 0, 0);
            piece.transform.position = centre;
            var cb = CheckoutWorksKit.Bounds(piece);
            piece.transform.position += new Vector3(centre.x - cb.center.x, -cb.min.y + .02f, centre.z - cb.center.z);
            // Each ruin model stands on its own ground slab ("*_pad": concrete, a yard...), each a different colour.
            // The lot shows the shared bare earth instead (Dirt), so every abandoned lot reads the same; the slab
            // still sized and placed the ruin above.
            foreach (var t in piece.GetComponentsInChildren<Transform>(true))
                if (t != piece.transform && t.name.EndsWith("_pad", System.StringComparison.OrdinalIgnoreCase)) t.gameObject.SetActive(false);
            return holder;
        }

        void Paint(GameObject piece)
        {
            var tex = Resources.Load<Texture2D>("CheckoutLots/" + piece.name.Replace("(Clone)", "").Trim() + "_BaseColor");
            if (!tex) return;
            var m = new Material(Shader.Find("Standard")) { name = piece.name + " (baked)", mainTexture = tex };
            m.SetFloat("_Glossiness", .08f);
            foreach (var r in piece.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = m;
                r.sharedMaterials = mats;
            }
        }

        // ------------------------------------------------------------------ look of a locked lot
        const float DirtY = .222f, AreaY = .234f, DashY = .248f, DashInset = .34f, DashWidth = .26f, DashPeriod = 1.15f, BadgeY = 1.7f;
        // Ground tint (about 25% opaque, the dirt shows through) and border of each status: for sale, not reachable yet, bought.
        static Color FillOf(string st) => st == "venda" ? new Color(.98f, .74f, .22f, .25f) : st == "comprado" ? new Color(.97f, .52f, .16f, .25f) : new Color(.16f, .2f, .33f, .25f);
        static Color DashOf(string st) => st == "bloqueado" ? new Color(.84f, .88f, .97f, .85f) : new Color(1f, .98f, .92f, .97f);
        static string BadgeOf(string st) => st == "venda" ? "lot_lock" : st == "comprado" ? "lot_lock_open" : "lot_lock_grey";

        Material AreaMaterial(string st, bool dash, bool badge = false)
        {
            var key = (badge ? "badge:" : dash ? "dash:" : "fill:") + st;
            if (areaMats.TryGetValue(key, out var m) && m) return m;
            if (badge)
            {
                // Drawn over everything (like the game's other map icons) so a tall ruin never hides it.
                m = new Material(Shader.Find("UI/Default")) { name = "Lot badge " + st, mainTexture = Resources.Load<Texture2D>("CheckoutDesktop/Game/" + BadgeOf(st)) };
                m.SetInt("unity_GUIZTestMode", (int)UnityEngine.Rendering.CompareFunction.Always);
                m.renderQueue = 3200;
            }
            else
            {
                m = new Material(Shader.Find("Sprites/Default")) { name = (dash ? "Lot border " : "Lot area ") + st, color = dash ? DashOf(st) : FillOf(st) };
                if (dash) m.mainTexture = DashTexture();
                m.renderQueue = dash ? 3051 : 3050;
            }
            return areaMats[key] = m;
        }

        // One dash and its gap, with soft ends and edges (the strip repeats it along each side).
        static Texture2D DashTexture()
        {
            if (dashTexture) return dashTexture;
            const int w = 64, h = 8; const float on = .62f;
            var t = new Texture2D(w, h, TextureFormat.RGBA32, false) { name = "Lot dash", wrapModeU = TextureWrapMode.Repeat, wrapModeV = TextureWrapMode.Clamp, filterMode = FilterMode.Bilinear };
            var px = new Color32[w * h];
            for (int y = 0; y < h; y++)
                for (int x = 0; x < w; x++)
                {
                    float u = (x + .5f) / w, v = (y + .5f) / h;
                    float along = Mathf.Clamp01(Mathf.Min(u, on - u) * w / 2.2f);          // rounded-ish ends
                    float across = Mathf.Clamp01(Mathf.Min(v, 1 - v) * h / 1.4f);           // soft edges
                    px[y * w + x] = new Color32(255, 255, 255, (byte)(u < on ? along * across * 255 : 0));
                }
            t.SetPixels32(px); t.Apply(false, true);
            return dashTexture = t;
        }

        // Lot rectangles come in world coordinates (the ruins are placed with .position too): the area meshes and the
        // badge hang from a holder that sits at the world origin, whatever the transform of the map root.
        static Transform WorldHolder(Transform parent, string name)
        {
            var t = new GameObject(name).transform; t.SetParent(parent, false);
            t.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            var ls = parent.lossyScale; t.localScale = new Vector3(1 / Mathf.Max(ls.x, 1e-4f), 1 / Mathf.Max(ls.y, 1e-4f), 1 / Mathf.Max(ls.z, 1e-4f));
            return t;
        }

        // Outline of a rectangle with round corners (clockwise seen from above), corner arcs of `steps` segments.
        static List<Vector3> RoundedRect(float x0, float z0, float x1, float z1, float r, float y, int steps = 8)
        {
            r = Mathf.Min(r, (x1 - x0) * .5f, (z1 - z0) * .5f);
            var pts = new List<Vector3>();
            void Arc(float cx, float cz, float from)
            {
                for (int i = 0; i <= steps; i++)
                {
                    float a = (from - 90f * i / steps) * Mathf.Deg2Rad;
                    pts.Add(new Vector3(cx + Mathf.Cos(a) * r, y, cz + Mathf.Sin(a) * r));
                }
            }
            Arc(x0 + r, z1 - r, 180); // top left, going clockwise
            Arc(x1 - r, z1 - r, 90);
            Arc(x1 - r, z0 + r, 0);
            Arc(x0 + r, z0 + r, -90);
            return pts;
        }

        // Bare ground of an abandoned lot (Game/lot_dirt.png, ArtSource/lot_dirt_tex.py) over the paving, until the lot
        // is bought and cleared (the site goes away and the paving shows again). Mapped in world units, so neighbouring
        // lots join without a seam.
        Material dirtMat;
        const float DirtTile = 7f;
        GameObject Dirt(Site site, float x0, float z0, float x1, float z1)
        {
            if (!dirtMat)
            {
                dirtMat = new Material(Shader.Find("Standard")) { name = "Lot dirt", mainTexture = Resources.Load<Texture2D>("CheckoutDesktop/Game/lot_dirt") };
                dirtMat.SetFloat("_Glossiness", .04f); dirtMat.SetFloat("_Metallic", 0);
            }
            var holder = WorldHolder(site.root.transform, "Lot ground");
            var corners = new[] { new Vector3(x0, DirtY, z0), new Vector3(x0, DirtY, z1), new Vector3(x1, DirtY, z1), new Vector3(x1, DirtY, z0) };
            var uv = new Vector2[4];
            for (int i = 0; i < 4; i++) uv[i] = new Vector2(corners[i].x / DirtTile, corners[i].z / DirtTile);
            var r = MeshObject(holder, "Lot dirt", corners, uv, new[] { 0, 1, 2, 0, 2, 3 });
            r.sharedMaterial = dirtMat; r.receiveShadows = true;
            return holder.gameObject;
        }

        GameObject Area(Site site, float x0, float z0, float x1, float z1)
        {
            var root = WorldHolder(site.root.transform, "Locked area").gameObject;
            // Tint: the whole lot with soft round corners, as a fan around its middle.
            const float e = .08f;
            var rim = RoundedRect(x0 + e, z0 + e, x1 - e, z1 - e, .9f, AreaY);
            var fv = new List<Vector3> { new Vector3((x0 + x1) * .5f, AreaY, (z0 + z1) * .5f) }; fv.AddRange(rim);
            var fu = new List<Vector2>(); foreach (var v in fv) fu.Add(new Vector2(.5f, .5f));
            var ft = new List<int>();
            for (int i = 0; i < rim.Count; i++) ft.AddRange(new[] { 0, 1 + i, 1 + (i + 1) % rim.Count });
            site.fill = MeshObject(root.transform, "Area fill", fv.ToArray(), fu.ToArray(), ft.ToArray());
            // Border: a dashed ribbon a little inside the edge, round at the corners; the dash length is fitted so a
            // whole number of dashes goes around and the pattern closes without a seam.
            var path = RoundedRect(x0 + DashInset, z0 + DashInset, x1 - DashInset, z1 - DashInset, .6f, DashY);
            float perimeter = 0;
            for (int i = 0; i < path.Count; i++) perimeter += Vector3.Distance(path[i], path[(i + 1) % path.Count]);
            float period = perimeter / Mathf.Max(4, Mathf.Round(perimeter / DashPeriod));
            var verts = new List<Vector3>(); var uvs = new List<Vector2>(); var tris = new List<int>();
            float run = 0;
            for (int i = 0; i <= path.Count; i++)
            {
                var p = path[i % path.Count];
                var prev = path[(i - 1 + path.Count) % path.Count]; var next = path[(i + 1) % path.Count];
                var tangent = (next - prev); tangent.y = 0; tangent.Normalize();
                var side = new Vector3(-tangent.z, 0, tangent.x) * (DashWidth * .5f);
                if (i > 0) run += Vector3.Distance(path[i - 1], p);
                verts.Add(p - side); verts.Add(p + side);
                uvs.Add(new Vector2(run / period, 0)); uvs.Add(new Vector2(run / period, 1));
                if (i > 0) { int k = verts.Count - 4; tris.AddRange(new[] { k, k + 1, k + 3, k, k + 3, k + 2 }); }
            }
            site.dash = MeshObject(root.transform, "Area border", verts.ToArray(), uvs.ToArray(), tris.ToArray());
            return root;
        }

        static Renderer MeshObject(Transform parent, string name, Vector3[] verts, Vector2[] uvs, int[] tris)
        {
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer)); go.transform.SetParent(parent, false);
            var white = new Color[verts.Length]; for (int i = 0; i < white.Length; i++) white[i] = Color.white;
            var mesh = new Mesh { name = name, vertices = verts, uv = uvs, colors = white, triangles = tris };
            mesh.RecalculateBounds(); mesh.RecalculateNormals();
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.GetComponent<MeshRenderer>();
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return r;
        }

        // The padlock badge: a square picture that always faces the camera, over the middle of the lot.
        Transform Badge(Site site, Vector3 at)
        {
            var r = MeshObject(WorldHolder(site.root.transform, "Padlock holder"), "Padlock badge",
                new[] { new Vector3(-.5f, -.5f, 0), new Vector3(-.5f, .5f, 0), new Vector3(.5f, .5f, 0), new Vector3(.5f, -.5f, 0) },
                new[] { Vector2.zero, Vector2.up, Vector2.one, Vector2.right }, new[] { 0, 1, 2, 0, 2, 3 });
            r.transform.position = at;
            site.badge = r;
            var box = r.gameObject.AddComponent<BoxCollider>(); box.size = new Vector3(.8f, .8f, .1f);
            site.lockClick = box;
            return r.transform;
        }

        // ------------------------------------------------------------------ clearing works
        void ResetRuin(Site site)
        {
            if (!site.ruin) return;
            var lot = site.lot;
            site.ruin.position = new Vector3((lot.x0 + lot.x1) * .5f, .02f, (lot.z0 + lot.z1) * .5f + .25f);
            site.ruin.localScale = Vector3.one;
        }

        void StartClearing(Site site)
        {
            var lot = site.lot;
            var s = CheckoutWorksScene.Create("Clearing " + lot.id, lot.clearStartedAt, lot.clearEndsAt);
            s.transform.SetParent(site.root.transform, false);
            site.works = s;
            float cx = (lot.x0 + lot.x1) * .5f, z0 = lot.z0, ld = lot.z1 - lot.z0;
            // The crew works from the front strip of the lot: the ruin is pushed to the back and comes down
            // (lower and lower) with the countdown.
            var ruin = site.ruin; var basePos = new Vector3(cx, .02f, z0 + ld * .5f + .25f + ld * .11f);
            s.OnProgress(p =>
            {
                if (!ruin) return;
                ruin.position = basePos;
                float k = Mathf.Lerp(1f, .12f, Mathf.SmoothStep(0, 1, p));
                ruin.localScale = new Vector3(.76f, .76f * k, .76f);
            });
            Vector3 P(float u, float v) => new Vector3(cx + u, .13f, z0 + v);
            Vector3 E = Vector3.right, W = Vector3.left, N = Vector3.forward;
            var front = P(0, 4.6f); // the ruin's face
            switch (lot.ruin)
            {
                case "casa":
                {
                    var skip = s.Prop("Works_Dumpster", P(3.4f, 1.6f), E); Fill(s, skip);
                    s.ToolWorker(P(-2.2f, 3.7f), P(-2.2f, 5f), Tool.Sledge, 0);
                    s.ToolWorker(P(.6f, 3.7f), P(.6f, 5f), Tool.Sledge, 1);
                    s.Carrier(P(-.8f, 3.5f), P(3.4f, 3.0f), "Prop_Rubble", 2);
                    s.Foreman(P(-4.4f, 1.2f), P(-4.4f, 3f), front, 3);
                    break;
                }
                case "loja":
                {
                    s.Prop("Works_Pickup", P(2.6f, 1.5f), E);
                    var skip = s.Prop("Works_Dumpster", P(-3.4f, 1.6f), E); Fill(s, skip);
                    s.ToolWorker(P(-1.2f, 3.8f), P(-1.2f, 5f), Tool.Crowbar, 0);
                    s.Carrier(P(.6f, 3.6f), P(.6f, 2.9f), "Prop_Box", 1);
                    s.Carrier(P(-.4f, 3.6f), P(-3.4f, 3.0f), "Prop_Rubble", 2);
                    s.Foreman(P(4.6f, 3.4f), P(4.6f, .8f), front, 3);
                    break;
                }
                case "sobrado":
                {
                    var skip = s.Prop("Works_Dumpster", P(3.6f, 1.5f), E); Fill(s, skip);
                    s.Excavator("Works_Excavator", P(-2.2f, 1.8f), E, P(-1.8f, 5.2f), P(3.6f, 1.5f), true);
                    s.ToolWorker(P(1.6f, 3.8f), P(1.6f, 5f), Tool.Sledge, 0);
                    s.Foreman(P(-5f, .6f), P(-5f, 3.2f), front, 3);
                    break;
                }
                case "oficina":
                {
                    // The tow truck takes the old car away; tyres and drums go to the pickup.
                    var car = OldCar(P(-.2f, 3.9f));
                    if (car) car.SetParent(s.transform, true);
                    s.TowTruck(P(.4f, 1.7f), W, car, .02f, .4f);
                    s.Prop("Prop_TireStack", P(4.7f, 3.4f), E);
                    s.Carrier(P(3.2f, 4.0f), P(4.4f, 2.8f), "Prop_Tire", 0);
                    s.ToolWorker(P(-4.2f, 3.8f), P(-4.2f, 5f), Tool.Wrench, 1);
                    s.Foreman(P(-4.8f, .8f), P(-2.6f, .8f), front, 3);
                    break;
                }
                case "posto":
                {
                    // A crane truck lifts the pumps and the canopy beams onto its deck.
                    var beams = s.Prop("Prop_SteelBeams", P(-1.2f, 4.1f), E);
                    s.CraneTruck(P(1.2f, 1.7f), E, beams, P(-1.2f, 4.1f), P(-1.0f, 1.7f) + Vector3.up * 1.25f);
                    s.ToolWorker(P(3.6f, 3.8f), P(3.6f, 5f), Tool.Wrench, 0);
                    s.ToolWorker(P(-4.0f, 3.8f), P(-4.0f, 5f), Tool.Drill, 1);
                    s.Prop("Prop_Barrier", P(-4.6f, .7f), E); s.Prop("Prop_Cone", P(4.9f, .6f), E);
                    break;
                }
                case "galpao":
                {
                    // The metal sheets come off with a drill and are stacked; a forklift takes the pallets.
                    s.ToolWorker(P(-2.6f, 3.8f), P(-2.6f, 5f), Tool.Drill, 0);
                    s.ToolWorker(P(2.2f, 3.8f), P(2.2f, 5f), Tool.Weld, 1);
                    s.Carrier(P(-.6f, 3.6f), P(4.2f, 2.4f), "Prop_Sheet", 2);
                    s.Forklift(P(-4.6f, 1.6f), P(3.6f, 1.6f));
                    s.Prop("Prop_Generator", P(-4.8f, 3.6f), E);
                    break;
                }
                case "garagem":
                {
                    var skip = s.Prop("Works_Dumpster", P(3.4f, 1.6f), E); Fill(s, skip);
                    s.Excavator("Works_MiniExcavator", P(-2.4f, 2.0f), E, P(-2.2f, 5.0f), P(3.4f, 1.6f), true);
                    s.ToolWorker(P(.9f, 3.8f), P(.9f, 5f), Tool.Sledge, 0);
                    s.Foreman(P(-4.9f, .7f), P(-.6f, .7f), front, 3);
                    break;
                }
                case "mato":
                {
                    // Brush cutters on the overgrown plot; the cut grass goes to a green-waste heap.
                    var heap = s.Prop("Prop_GreenWaste", P(3.9f, 1.6f), E); s.Grow(heap, 0, .95f, false);
                    s.ToolWorker(P(-2.6f, 3.6f), P(-2.6f, 5.2f), Tool.Trimmer, 0);
                    s.ToolWorker(P(.8f, 4.0f), P(.8f, 5.6f), Tool.Trimmer, 1);
                    s.Carrier(P(-.8f, 3.4f), P(3.9f, 2.9f), "Prop_GrassBundle", 2);
                    s.Prop("Prop_WheelbarrowFull", P(-4.6f, 1.6f), E);
                    s.ToolWorker(P(-4.6f, 2.8f), P(-4.6f, 4.2f), Tool.Broom, 3);
                    break;
                }
                case "entulho":
                {
                    var skip = s.Prop("Works_Dumpster", P(3.6f, 1.5f), E); Fill(s, skip);
                    s.SkidLoader(P(-3.6f, 3.4f), P(3.6f, 1.5f));
                    s.ToolWorker(P(-.4f, 3.9f), P(-.4f, 5.2f), Tool.Shovel, 0);
                    s.ToolWorker(P(-4.8f, 1.0f), P(-4.8f, 2.4f), Tool.Broom, 1);
                    break;
                }
                case "armazem":
                {
                    s.WreckingCrane(P(-2.4f, 1.9f), E, P(-1.0f, 6.2f) + Vector3.up * 3f);
                    var skip = s.Prop("Works_Dumpster", P(3.9f, 1.4f), E); Fill(s, skip);
                    s.ToolWorker(P(2.6f, 3.6f), P(2.6f, 5f), Tool.Shovel, 0);
                    s.Foreman(P(4.9f, 3.6f), P(4.9f, 2.6f), front, 3);
                    break;
                }
                case "fabrica":
                {
                    // The wrecking ball takes the chimney and the saw-tooth roof down.
                    s.WreckingCrane(P(-2.0f, 1.9f), E, P(1.0f, 6.8f) + Vector3.up * 4f);
                    s.ToolWorker(P(3.4f, 3.8f), P(3.4f, 5f), Tool.Sledge, 0);
                    s.Prop("Prop_DebrisPile", P(4.0f, 1.4f), E);
                    s.Foreman(P(4.9f, .6f), P(1.6f, .6f), front, 3);
                    break;
                }
                case "patio":
                {
                    // The old container goes onto a crane truck; a worker unbolts the guard booth.
                    var box = s.Prop("Works_Container", P(-1.6f, 3.9f), E);
                    s.CraneTruck(P(1.6f, 1.6f), E, box, P(-1.6f, 3.9f), P(-.6f, 1.6f) + Vector3.up * 1.25f, true, .05f, .45f);
                    s.ToolWorker(P(4.0f, 3.8f), P(4.0f, 5f), Tool.Wrench, 0);
                    s.Prop("Prop_Cone", P(-4.8f, .6f), E); s.Prop("Prop_Cone", P(4.8f, .6f), E);
                    break;
                }
                default:
                    s.ToolWorker(P(-1f, 3.8f), P(-1f, 5f), Tool.Shovel, 0);
                    break;
            }
            s.Countdown(new Vector3(cx, Mathf.Max(4.5f, site.top * .8f + 2f), z0 + ld * .5f), "LIMPANDO", "~loja:terrenos");
        }

        // The skip fills up as the works go on.
        static void Fill(CheckoutWorksScene s, Transform skip)
        {
            var fill = CheckoutWorksKit.FindPart(skip, "Fill");
            if (fill) s.Grow(fill, 0, .95f, false);
        }

        // An old car for the workshop: a copy of one of the city's parked cars.
        Transform OldCar(Vector3 at)
        {
            Transform source = null;
            foreach (var t in FindObjectsByType<Transform>(FindObjectsInactive.Include, FindObjectsSortMode.None))
                if (t.name.StartsWith("Parking customer vehicle") && t.GetComponentInChildren<Renderer>(true)) { source = t; break; }
            if (!source) return null;
            var car = Instantiate(source.gameObject).transform;
            car.name = "Old car"; car.gameObject.SetActive(true);
            foreach (var mb in car.GetComponentsInChildren<MonoBehaviour>(true)) Destroy(mb);
            car.SetPositionAndRotation(at + Vector3.up * .02f, Quaternion.Euler(0, 90, 0));
            return car;
        }

        // ------------------------------------------------------------------ the old plaza decorations
        static readonly string[] ClutterRoots = { "Harbour Quay Plaza", "Landscape Models", "Individual Street Furniture" };
        readonly List<GameObject> clutter = new List<GameObject>();
        bool clutterFound;
        void ClearBlock()
        {
            if (!clutterFound)
            {
                clutterFound = true;
                foreach (var name in ClutterRoots)
                {
                    var root = world ? world.Find(name) : null;
                    if (!root) { var go = GameObject.Find(name); root = go ? go.transform : null; }
                    if (!root) continue;
                    foreach (Transform child in root)
                    {
                        if (child.name.StartsWith("Entrance flowers")) continue; // the shop's own planters
                        var rs = child.GetComponentsInChildren<Renderer>(true);
                        if (rs.Length == 0) continue;
                        var b = rs[0].bounds; foreach (var r in rs) b.Encapsulate(r.bounds);
                        var c = b.center;
                        if (c.x > -17.4f && c.x < 17.4f && c.z > -8.4f && c.z < 44.4f && b.size.x < 20 && b.size.z < 20) clutter.Add(child.gameObject);
                    }
                }
            }
            foreach (var go in clutter) if (go && go.activeSelf) go.SetActive(false);
        }

        static readonly CultureInfo Br = CultureInfo.GetCultureInfo("pt-BR");
        public static string Money(double value) => value.ToString("N0", Br);

        // ------------------------------------------------------------------ padlocks, clicks
        void LateUpdate()
        {
            var cam = simulation && simulation.view ? simulation.view : Camera.main;
            if (!cam) return;
            float t = Time.time;
            // The border of the lots for sale glows softly.
            if (areaMats.TryGetValue("dash:venda", out var saleDash) && saleDash) { var c = DashOf("venda"); c.a = .72f + .25f * (.5f + .5f * Mathf.Sin(t * 3f)); saleDash.color = c; }
            foreach (var site in sites.Values)
            {
                if (!site.marker || !site.marker.gameObject.activeSelf) continue;
                var lot = site.lot;
                // In the middle of the lot, bobbing gently; the one for sale breathes to call the eye.
                float size = Mathf.Clamp(Mathf.Min(lot.x1 - lot.x0, lot.z1 - lot.z0) * .36f, 1.8f, 3.2f);
                site.marker.position = new Vector3((lot.x0 + lot.x1) * .5f, BadgeY + Mathf.Sin(t * 1.6f + lot.x0) * .12f, (lot.z0 + lot.z1) * .5f);
                site.marker.rotation = cam.transform.rotation;
                site.marker.localScale = Vector3.one * (site.status == "venda" ? size * (1.06f + Mathf.Sin(t * 3f) * .04f) : size);
            }
        }

        void Update()
        {
            if ((clock += Time.deltaTime) >= .5f) { clock = 0; if (!CheckoutMapEditor.Open) ClearBlock(); }
            if (!Input.GetMouseButtonDown(0) || !simulation || !simulation.view || CheckoutBuildMode.Open || CheckoutMapEditor.Open) return;
            if (UnityEngine.EventSystems.EventSystem.current && UnityEngine.EventSystems.EventSystem.current.IsPointerOverGameObject()) return;
            var ray = simulation.view.ScreenPointToRay(Input.mousePosition);
            Site best = null; float near = float.MaxValue;
            foreach (var hit in Physics.RaycastAll(ray, 400))
                foreach (var site in sites.Values)
                {
                    if (site.works && site.works.Clicked(hit.collider)) return; // the countdown handles it
                    if ((site.click && hit.collider == site.click || site.lockClick && hit.collider == site.lockClick) && hit.distance < near) { near = hit.distance; best = site; }
                }
            if (best != null) CheckoutLotPopup.Show(this, best.lot);
        }

        void OnDestroy()
        {
            foreach (var site in sites.Values) { foreach (var go in site.hidden) if (go) go.SetActive(true); if (site.works) Destroy(site.works.gameObject); }
            foreach (var go in clutter) if (go) go.SetActive(true);
            Obstacles.Clear();
        }
    }
}
