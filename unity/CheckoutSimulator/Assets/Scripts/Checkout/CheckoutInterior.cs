using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using MarketDay;
using UnityEngine;

namespace Checkout
{
    // The furniture inside the market: shelves, sector counters, checkouts, kiosks and bought decorations,
    // built from the "Interior Kit" templates and placed where the player put them in build mode.
    //
    // Positions are stored in the unprojected base map (walls at x ±9.4, z ±7.4) and shown at the projected
    // spot of the bought stage, at their natural size. The shop only ever grows, so a layout that fits once
    // keeps fitting. Pieces without a saved spot start at a default and slide to the nearest free place.
    public class CheckoutInterior : MonoBehaviour
    {
        public class Item
        {
            public string id, type, template;
            public float x, z, rot, scale = 1;
            // design: extra furniture/decoration from the map design (fixed in the game, edited in "Modo edição").
            public bool functional, placed, ghost, saved, outside, design;
            // Paid for, still being built (a works site stands in its place).
            public bool building;
            public Vector3 baseScale = Vector3.one;
            public Transform root;
            public CheckoutInteriorPiece piece;
        }

        public struct Footprint { public Vector2 c, ax, az; public float hx, hz; }

        public const float Floor = .74f, DoorX = -1.75f, Ground = .13f, RearDoorX = 4.02f;
        public static CheckoutInterior Active { get; private set; }
        public readonly Dictionary<string, Item> items = new Dictionary<string, Item>();
        // Shop furniture the player owns but has not placed yet (build-mode inventory "Para colocar"): a new shop
        // starts empty with the checkout, two shelves and the drinks cooler waiting here. id -> kit template.
        public readonly Dictionary<string, (string type, string template)> waiting = new Dictionary<string, (string type, string template)>();
        // Bought pieces (from the shop) among the waiting ones: their works start once they are placed.
        public BuildEntry PendingBuild(string id) => lastBuilds.FirstOrDefault(b => b != null && b.pending && PieceIds(b).Contains(id));
        BuildEntry[] lastBuilds = Array.Empty<BuildEntry>();
        public static string[] PieceIds(BuildEntry b) =>
            b.kind == "shelf" ? new[] { "shelf:" + b.targetId } : b.kind == "sector" ? new[] { "sector:" + b.targetId }
            : b.targetId == CheckoutLanes.ExtraItem ? new[] { "checkout:extra" } : b.targetId == CheckoutLanes.SelfItem ? new[] { "kiosk:1", "kiosk:2" } : Array.Empty<string>();
        public bool Ready => kit;
        // Build mode owns the positions while it is open; snapshots then only refresh stock.
        public bool editing;
        // "Modo edição": the map design owns every position (the sandbox save's own layout is ignored).
        public bool designMode;
        public MarketLayout LayoutState => layout.State;
        public Transform Holder => holder;

        Transform world, kit, holder;
        CheckoutMarketLayout layout;
        CheckoutMap map;
        InteriorItem[] pending; float pendingAt; string lastSize;
        readonly Dictionary<string, int> owned = new Dictionary<string, int>();

        // Default spots in the base map, laid out so they already fit the corner shop (stage 0).
        static readonly Dictionary<string, Vector3> Defaults = new Dictionary<string, Vector3>
        {
            { "checkout:main", new Vector3(-5.74f, 0, -4.63f) }, { "checkout:extra", new Vector3(2.55f, 0, -4.63f) },
            { "kiosk:1", new Vector3(5.6f, 0, -4.45f) }, { "kiosk:2", new Vector3(7.45f, 0, -4.45f) },
            { "shelf:produce", new Vector3(-6.96f, 0, 2.32f) }, { "shelf:dairy", new Vector3(-3.18f, 0, 2.32f) },
            { "shelf:bakery", new Vector3(.6f, 0, 2.32f) }, { "shelf:snacks", new Vector3(4.38f, 0, 2.32f) },
            { "shelf:drinks", new Vector3(-6.35f, 0, -.88f) }, { "shelf:coffee", new Vector3(-1.72f, 0, -.88f) },
            { "shelf:pizza", new Vector3(2.92f, 0, -.88f) },
            // The four staffed departments are big rounded counters (3.96 x 3.36 m) along the back wall, leaving a
            // 2 m service corridor in front of the rear roller door (x 4.02) for the stock clerks.
            { "sector:padaria", new Vector3(-7.0f, 0, 4.92f) }, { "sector:queijaria", new Vector3(-2.98f, 0, 4.92f) },
            { "sector:peixaria", new Vector3(1.04f, 0, 4.92f) }, { "sector:acougue", new Vector3(7.0f, 0, 4.92f) },
            { "sector:bebidas", new Vector3(-7.3f, 270, -3.2f) }, { "sector:sorvetes", new Vector3(-7.3f, 270, .3f) },
            { "sector:adega", new Vector3(7.8f, 90, -1.2f) },
        };
        // y above holds the yaw. Side-wall counters turn so their customer side (-Z) faces into the shop:
        // 270° points it east (west wall), 90° west (east wall).

        // The spot (x, yaw, z) and size a piece starts at: the map design of this stage, else the built-in default.
        public DesignStage Design => CheckoutMapDesign.For(layout.State.stage);
        public DesignPiece DesignEntry(string id) => Design?.interior?.FirstOrDefault(p => p != null && p.id == id);
        Vector3 DefaultFor(string id, out float scale)
        {
            scale = 1;
            var e = DesignEntry(id);
            if (e != null) { scale = e.scale > 0 ? e.scale : 1; return new Vector3(e.x, e.rot, e.z); }
            return Defaults.TryGetValue(id, out var v) ? v : Vector3.zero;
        }

        public void Initialize(Transform root, CheckoutMarketLayout marketLayout, CheckoutMap owner)
        {
            world = root; layout = marketLayout; map = owner;
            kit = world.Find("Interior Kit");
            if (!kit) { Debug.LogWarning("CHECKOUT_INTERIOR no Interior Kit in the scene: using the old fixtures."); return; }
            kit.gameObject.SetActive(false);
            Active = this;
            holder = new GameObject("Market Interior").transform;
            holder.gameObject.AddComponent<CheckoutInteriorLife>();
            // Bench visitors route around the decorations placed on the block.
            CheckoutBlockPaths.Extras = () => items.Values.Where(i => i.root && i.outside).Select(i =>
            {
                var f = FootprintOf(i);
                float ex = f.hx * Mathf.Abs(f.ax.x) + f.hz * Mathf.Abs(f.az.x), ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
                return new Bounds(new Vector3(f.c.x, 1, f.c.y), new Vector3(ex * 2, 2, ez * 2));
            }).ToArray();
            HideOldInterior();
        }

        void OnDestroy() { if (Active == this) Active = null; if (holder) Destroy(holder.gameObject); }

        // The supplied fixtures stay in the scene (other systems still look them up) but are no longer drawn.
        void HideOldInterior()
        {
            string[] roots = { "Checkout", "Bakery", "Butcher", "Fishery", "Produce", "Groceries", "Owned Shelf Slots", "Sector Construction" };
            foreach (Transform child in world)
            {
                bool inside = false;
                if (child.name.StartsWith("ReplacementVisual"))
                {
                    var rs = child.GetComponentsInChildren<Renderer>(true);
                    if (rs.Length > 0) { var c = rs[0].bounds.center; inside = c.x > -9.6f && c.x < 9.6f && c.z > -7.6f && c.z < 7.6f; }
                }
                if (!(roots.Contains(child.name) || child.name.StartsWith("Stock_") || child.name.StartsWith("Sector_") || inside)) continue;
                foreach (var r in child.GetComponentsInChildren<Renderer>(true)) r.forceRenderingOff = true;
                foreach (var c in child.GetComponentsInChildren<Collider>(true)) c.enabled = false;
            }
            // Stage decor that stood among the old fixtures: department boards, islands and the floor path.
            var dressing = world.GetComponentInChildren<CheckoutStageDressing>(true);
            if (dressing)
                foreach (var item in dressing.GetComponentsInChildren<CheckoutStageItem>(true))
                {
                    var n = item.name;
                    if (n.StartsWith("Dept ") || n.StartsWith("Banner ") || n == "Promo island" || n == "Gondola island" || n == "Gondola sign" || n == "Floor path")
                    { item.minStage = 99; item.gameObject.SetActive(false); }
                }
        }

        // ------------------------------------------------------------------ snapshot
        static string ShelfTemplate(Shelf shelf)
        {
            string c = (shelf.category ?? "").ToLowerInvariant();
            if (c.Length == 0)
                switch (shelf.id)
                {
                    case "produce": return "shelf-produce";
                    case "dairy": return "shelf-dairy";
                    case "bakery": return "shelf-bakery";
                    case "snacks": return "shelf-snacks";
                    case "drinks": return "shelf-cooler";
                    case "pizza": return "shelf-freezer";
                    default: return "shelf-grocery";
                }
            if (c.Contains("bebida") || c.Contains("refrigerante") || c.Contains("energetic") || c.Contains("agua") || c.Contains("drink")) return "shelf-cooler";
            if (c.Contains("laticin") || c.Contains("queijo") || c.Contains("frios") || c.Contains("carne") || c.Contains("peixe")) return "shelf-dairy";
            if (c.Contains("hortifruti") || c.Contains("organic") || c.Contains("fruta")) return "shelf-produce";
            if (c.Contains("congelad") || c.Contains("sorvete")) return "shelf-freezer";
            if (c.Contains("padaria") || c.Contains("pao")) return "shelf-bakery";
            if (c.Contains("doce") || c.Contains("snack") || c.Contains("sazona")) return "shelf-snacks";
            if (c.Contains("limpeza") || c.Contains("higiene") || c.Contains("pet")) return "shelf-cleaning";
            return "shelf-grocery";
        }

        public static bool IsFunctional(string type) => type == "shelf" || type == "sector" || type == "checkout" || type == "kiosk";

        public int Owned(string decor) => owned.TryGetValue(decor, out var n) ? n : 0;
        public int Placed(string decor) => items.Values.Count(i => i.type == decor);

        // Builds, moves and removes pieces for this snapshot. Returns true when the floor plan changed.
        public bool Apply(Snapshot s)
        {
            if (!kit) return false;
            owned.Clear();
            if (s.interior?.owned != null) foreach (var o in s.interior.owned) if (o != null && !string.IsNullOrEmpty(o.type)) owned[o.type] = o.count;
            var saved = designMode ? Array.Empty<InteriorItem>() : s.interior?.items ?? Array.Empty<InteriorItem>();
            // Our own save is in flight: keep showing it until the app echoes it back.
            if (pending != null && !designMode)
            {
                if (Same(saved, pending) || Time.unscaledTime - pendingAt > 8f) pending = null;
                else saved = pending;
            }
            var want = new List<(string id, string type, string template)>();
            var outsideIds = new HashSet<string>();
            // Pieces still being built stand in their place as a works site (CheckoutInteriorWorks).
            var builds = s.builds ?? Array.Empty<BuildEntry>(); lastBuilds = builds;
            BuildEntry BuildOf(string kind, string target) => builds.FirstOrDefault(b => b != null && b.kind == kind && b.targetId == target);
            var works = new Dictionary<string, BuildEntry>();
            want.Add(("checkout:main", "checkout", "checkout"));
            bool extra = s.ownedItems != null && s.ownedItems.Contains(CheckoutLanes.ExtraItem), self = s.ownedItems != null && s.ownedItems.Contains(CheckoutLanes.SelfItem);
            var extraWorks = BuildOf("shop", CheckoutLanes.ExtraItem); var selfWorks = BuildOf("shop", CheckoutLanes.SelfItem);
            if (extra || extraWorks != null) { want.Add(("checkout:extra", "checkout", "checkout")); if (!extra) works["checkout:extra"] = extraWorks; }
            if (self || selfWorks != null)
            {
                want.Add(("kiosk:1", "kiosk", "kiosk")); want.Add(("kiosk:2", "kiosk", "kiosk"));
                if (!self) { works["kiosk:1"] = selfWorks; works["kiosk:2"] = selfWorks; }
            }
            foreach (var sector in s.sectors ?? Array.Empty<Sector>())
            {
                var sectorWorks = sector.unlocked ? null : BuildOf("sector", sector.id);
                if ((sector.unlocked || sectorWorks != null) && layout.HasSector(sector.id) && kit.Find("sector-" + sector.id))
                {
                    want.Add(("sector:" + sector.id, "sector", "sector-" + sector.id));
                    if (sectorWorks != null) works["sector:" + sector.id] = sectorWorks;
                }
            }
            foreach (var shelf in s.shelves ?? Array.Empty<Shelf>())
            {
                var shelfWorks = shelf.unlocked ? null : BuildOf("shelf", shelf.id);
                if (shelf.unlocked || shelfWorks != null)
                {
                    want.Add(("shelf:" + shelf.id, "shelf", ShelfTemplate(shelf)));
                    if (shelfWorks != null) works["shelf:" + shelf.id] = shelfWorks;
                }
            }
            // Furniture the app keeps stored waits in the build-mode inventory instead of standing in the shop.
            // So does everything bought that still has to be built: the player picks its spot and the works
            // start once the layout is saved (until the app echoes that, the placed piece shows as furniture).
            if (designMode) waiting.Clear();
            else if (!editing)
            {
                waiting.Clear();
                var stored = new HashSet<string>(saved.Where(e => e != null && e.stored && IsFunctional(e.type)).Select(e => e.id));
                foreach (var w in want.Where(w => stored.Contains(w.id) && !works.ContainsKey(w.id)).ToList()) { waiting[w.id] = (w.type, w.template); want.Remove(w); }
                var placedIds = new HashSet<string>(saved.Where(e => e != null && !e.stored).Select(e => e.id));
                foreach (var w in want.Where(w => works.TryGetValue(w.id, out var b) && b.pending && !placedIds.Contains(w.id)).ToList()) { waiting[w.id] = (w.type, w.template); want.Remove(w); }
            }
            else want.RemoveAll(w => waiting.ContainsKey(w.id));
            foreach (var id in works.Where(p => p.Value.pending).Select(p => p.Key).ToList()) works.Remove(id);
            var designEntries = new Dictionary<string, DesignPiece>();
            if (!editing)
            {
                // Decorations the map design puts on the block are part of the map. Inside, the shop belongs to
                // the player: the design's own furniture only shows in the map editor.
                foreach (var d in Design?.interior ?? Array.Empty<DesignPiece>())
                {
                    if (d == null || string.IsNullOrEmpty(d.id) || !d.id.StartsWith("design-") || string.IsNullOrEmpty(d.template) || !kit.Find(d.template)) continue;
                    if (!d.outside && !designMode) continue;
                    want.Add((d.id, "design", d.template)); designEntries[d.id] = d;
                    if (d.outside) outsideIds.Add(d.id);
                }
                var placedDecor = new Dictionary<string, int>();
                foreach (var entry in saved)
                {
                    if (entry == null || entry.stored || IsFunctional(entry.type) || !kit.Find(entry.type)) continue;
                    placedDecor.TryGetValue(entry.type, out var n);
                    if (n >= Owned(entry.type)) continue;
                    placedDecor[entry.type] = n + 1;
                    want.Add((entry.id, entry.type, entry.type));
                    if (entry.outside) outsideIds.Add(entry.id);
                }
            }
            else foreach (var it in items.Values) if (!it.functional) { want.Add((it.id, it.type, it.template)); if (it.outside) outsideIds.Add(it.id); }

            // Pieces the player never placed follow the defaults of the current shop size.
            string size = layout.State.stage + ":" + layout.State.widthScale + ":" + layout.State.depthScale;
            if (size != lastSize) { lastSize = size; foreach (var it in items.Values) if (!it.saved && !it.outside) it.placed = false; CheckoutBlockPaths.Invalidate(); }
            bool changed = false;
            var keep = new HashSet<string>(want.Select(w => w.id));
            foreach (var id in items.Keys.Where(k => !keep.Contains(k)).ToArray())
            { if (items[id].root) Destroy(items[id].root.gameObject); items.Remove(id); changed = true; }

            var fresh = new List<Item>();
            foreach (var w in want)
            {
                items.TryGetValue(w.id, out var it);
                if (it == null) { it = new Item { id = w.id, type = w.type, functional = IsFunctional(w.type), outside = outsideIds.Contains(w.id), design = w.type == "design" }; items[w.id] = it; changed = true; }
                if (it.template != w.template || !it.root)
                {
                    if (it.root) Destroy(it.root.gameObject);
                    it.template = w.template; Build(it); changed = true;
                    if (!it.root) { items.Remove(w.id); continue; }
                }
                if (it.design && designEntries.TryGetValue(w.id, out var fixedSpot))
                {
                    if (Mathf.Abs(fixedSpot.x - it.x) > .001f || Mathf.Abs(fixedSpot.z - it.z) > .001f || Mathf.Abs(Mathf.DeltaAngle(fixedSpot.rot, it.rot)) > .1f || Mathf.Abs(fixedSpot.scale - it.scale) > .001f) changed = true;
                    it.x = fixedSpot.x; it.z = fixedSpot.z; it.rot = fixedSpot.rot; it.scale = fixedSpot.scale > 0 ? fixedSpot.scale : 1; it.outside = fixedSpot.outside; it.placed = true; it.saved = true;
                    continue;
                }
                var entry = editing ? null : saved.FirstOrDefault(e => e != null && e.id == w.id && !e.stored);
                if (entry != null)
                {
                    if (Mathf.Abs(entry.x - it.x) > .001f || Mathf.Abs(entry.z - it.z) > .001f || Mathf.Abs(Mathf.DeltaAngle(entry.rot, it.rot)) > .1f) changed = true;
                    it.x = entry.x; it.z = entry.z; it.rot = entry.rot; it.placed = true; it.saved = true;
                    // The player moves pieces; their size comes from the map design.
                    var sized = DesignEntry(w.id); it.scale = sized != null && sized.scale > 0 ? sized.scale : 1;
                }
                else if (!it.placed) fresh.Add(it);
            }
            foreach (var it in fresh) it.ghost = true;
            foreach (var it in items.Values) if (it.root) Place(it);
            // New pieces: default spot, or the nearest free one. Checkouts first, then counters, then shelves.
            foreach (var it in fresh.OrderBy(i => i.type == "checkout" || i.type == "kiosk" ? 0 : i.type == "sector" ? 1 : 2))
            {
                var d = DefaultFor(it.id, out var startScale);
                it.x = d.x; it.z = d.z; it.rot = d.y; it.scale = startScale; it.placed = true;
                Place(it);
                Settle(it);
                it.ghost = false;
            }
            // Layouts saved before the rear service door existed: pieces standing in its corridor move to the nearest
            // free spot, and the new arrangement is saved so it sticks.
            if (!editing && !designMode)
            {
                bool moved = false;
                // Also pieces that ended up under furniture the map design added.
                var fixedPieces = items.Values.Where(i => i.root && i.design && !i.outside).Select(i => FootprintOf(i, -.012f)).ToList();
                foreach (var it in items.Values.Where(i => i.root && !i.outside && !i.ghost && !i.design).OrderBy(i => i.id).ToList())
                    if ((Overlap(FootprintOf(it), ServiceDoor) || fixedPieces.Any(f => Overlap(FootprintOf(it), f)) || !InItsArea(it)) && Settle(it)) moved = true;
                if (moved) { changed = true; MarkPending(); map?.SaveInterior(); }
            }
            // Works sites: shown over pieces still being built, removed (with a little pop) when done.
            foreach (var it in items.Values)
            {
                if (!it.root) continue;
                bool building = works.TryGetValue(it.id, out var entry);
                it.building = building;
                if (building) CheckoutInteriorWorks.Show(it, entry);
                else CheckoutInteriorWorks.Finish(it);
            }
            MarkCheckoutZone();
            if (changed) CheckoutBlockPaths.Invalidate();
            return changed;
        }

        static bool Same(InteriorItem[] a, InteriorItem[] b)
        {
            if (a.Length != b.Length) return false;
            foreach (var x in b)
            {
                var y = a.FirstOrDefault(e => e != null && e.id == x.id);
                if (y == null || Mathf.Abs(y.x - x.x) > .01f || Mathf.Abs(y.z - x.z) > .01f || Mathf.Abs(Mathf.DeltaAngle(y.rot, x.rot)) > .5f) return false;
            }
            return true;
        }

        void Build(Item it)
        {
            var template = kit.Find(it.template);
            if (!template) { Debug.LogWarning("CHECKOUT_INTERIOR missing template " + it.template); it.root = null; return; }
            var go = Instantiate(template.gameObject, holder);
            go.name = it.id; go.SetActive(true);
            it.root = go.transform; it.baseScale = go.transform.localScale; it.piece = go.GetComponent<CheckoutInteriorPiece>();
            if (!it.piece) it.piece = go.AddComponent<CheckoutInteriorPiece>();
            // Clicks: the footprint opens the matching panel (and build mode picks pieces with it).
            var box = go.AddComponent<BoxCollider>();
            var p = it.piece; float h = Mathf.Max(1.2f, p.markerHeight - .2f);
            box.center = new Vector3((p.min.x + p.max.x) * .5f, h * .5f, (p.min.y + p.max.y) * .5f);
            box.size = new Vector3(p.max.x - p.min.x, h, p.max.y - p.min.y);
            if (it.functional && it.id != "checkout:extra" && it.type != "kiosk")
            {
                var target = go.AddComponent<CheckoutTarget>();
                if (it.type == "shelf") { target.panel = "store"; target.shelfId = it.id.Substring(6); }
                else if (it.type == "sector") { target.panel = "sectors"; target.sectorId = it.id.Substring(7); }
                else target.panel = "checkout";
            }
            if (it.type == "kiosk" && !go.GetComponent<CheckoutKiosk>()) go.AddComponent<CheckoutKiosk>();
        }

        public Vector3 WorldOf(float x, float z) => CheckoutMarketLayout.Project(new Vector3(x, Floor, z), layout.State);

        public void Place(Item it)
        {
            if (!it.root) return;
            // Outside pieces sit on the block's paving in world coordinates; shop pieces follow the projected floor.
            var at = it.outside ? new Vector3(it.x, Ground, it.z) : WorldOf(it.x, it.z);
            it.root.SetPositionAndRotation(at, Quaternion.Euler(0, it.rot, 0));
            it.root.localScale = it.baseScale * (it.scale > 0 ? it.scale : 1);
        }

        public void MoveTo(Item it, Vector3 worldPosition)
        {
            if (it.outside) { it.x = worldPosition.x; it.z = worldPosition.z; Place(it); return; }
            var b = CheckoutMarketLayout.Unproject(worldPosition, layout.State);
            it.x = b.x; it.z = b.z; Place(it);
        }

        // ------------------------------------------------------------------ the city block (outside decorations)
        public static readonly Rect BlockRect = Rect.MinMaxRect(CheckoutBlockPaths.MinX + .4f, CheckoutBlockPaths.MinZ + .4f, CheckoutBlockPaths.MaxX - .4f, CheckoutBlockPaths.MaxZ - .4f);
        // Where a piece may stand: checkouts and self-checkouts inside the checkout area, shelves and counters in
        // the rest of the shop, decorations anywhere on the floor (or on the block outside).
        public Rect RegionOf(Item it)
        {
            if (it.outside) return BlockRect;
            if (designMode || it.design) return FloorRect;
            if (IsCounter(it)) return CheckoutZone;
            if (it.functional) { var f = FloorRect; return Rect.MinMaxRect(f.xMin, CheckoutZone.yMax, f.xMax, f.yMax); }
            return FloorRect;
        }
        static bool IsCounter(Item it) => it.type == "checkout" || it.type == "kiosk";
        // The checkout area is painted on the floor: a darker band of tiles with a gold line where it ends.
        Transform zoneMarks; Rect zoneDrawn;
        void MarkCheckoutZone()
        {
            if (!holder) return;
            var zone = CheckoutZone;
            if (zoneMarks && zone == zoneDrawn) return;
            zoneDrawn = zone;
            if (!zoneMarks)
            {
                zoneMarks = new GameObject("Checkout Area").transform; zoneMarks.SetParent(holder, false);
                Mark("Band", new Color(.16f, .24f, .42f, .2f), 3000);
                Mark("Line", new Color(.93f, .72f, .3f, 1f), 3001);
                Mark("Line shadow", new Color(.16f, .24f, .42f, .55f), 3000);
            }
            void Put(string name, float x0, float z0, float x1, float z1, float y)
            {
                var t = zoneMarks.Find(name);
                t.SetPositionAndRotation(new Vector3((x0 + x1) * .5f, y, (z0 + z1) * .5f), Quaternion.Euler(90, 0, 0));
                t.localScale = new Vector3(x1 - x0, z1 - z0, 1);
            }
            Put("Band", zone.xMin, zone.yMin, zone.xMax, zone.yMax, Floor + .004f);
            Put("Line shadow", zone.xMin, zone.yMax - .05f, zone.xMax, zone.yMax + .12f, Floor + .005f);
            Put("Line", zone.xMin, zone.yMax - .05f, zone.xMax, zone.yMax + .07f, Floor + .006f);
        }
        void Mark(string name, Color color, int queue)
        {
            var q = GameObject.CreatePrimitive(PrimitiveType.Quad); q.name = name; Destroy(q.GetComponent<Collider>());
            q.transform.SetParent(zoneMarks, false);
            var m = new Material(Shader.Find("Sprites/Default")) { color = color, renderQueue = queue };
            var r = q.GetComponent<Renderer>(); r.sharedMaterial = m; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
        }

        // Layouts saved before the checkout area existed: counters outside it, or shelves inside it, move.
        bool InItsArea(Item it)
        {
            if (it.outside || it.design || !it.functional || !it.root) return true;
            var zone = CheckoutZone;
            foreach (var c in Corners(FootprintOf(it)))
                if (IsCounter(it) ? c.y > zone.yMax + .01f : c.y < zone.yMax - .01f) return false;
            return true;
        }

        // The checkout area: a strip along the front wall (6 half squares deep) where only the manual checkouts and
        // the self-checkouts stand, marked on the floor. Customers pass through it to pay and to leave.
        public const float CheckoutZoneDepth = 3f;
        public Rect CheckoutZone { get { var f = FloorRect; return Rect.MinMaxRect(f.xMin, f.yMin, f.xMax, Mathf.Min(f.yMax, f.yMin + CheckoutZoneDepth)); } }

        // The shop with its entrance steps, the parking bays and the delivery path stay clear.
        IEnumerable<Rect> KeepClear()
        {
            var lo = CheckoutMarketLayout.Project(new Vector3(-9.4f, 0, -10.6f), layout.State); var hi = CheckoutMarketLayout.Project(new Vector3(9.4f, 0, 7.4f), layout.State);
            yield return Rect.MinMaxRect(lo.x - .5f, lo.z - 1.2f, hi.x + .5f, hi.z + .5f);
            if (layout.State.parking) yield return Rect.MinMaxRect(-30, -14, -13.6f, 14);
            var rear = CheckoutMarketLayout.Project(new Vector3(RearDoorX, 0, 8.8f), layout.State);
            yield return Rect.MinMaxRect(rear.x - 1.1f, rear.z - .5f, rear.x + 1.1f, 18.5f);
        }

        bool FitsOutside(Item it, Vector3 position, float rot, out string why)
        {
            var f = FootprintAt(it, position, rot);
            foreach (var c in Corners(f))
                if (!BlockRect.Contains(c)) { why = "Fora do terreno"; return false; }
            foreach (var r in KeepClear())
                if (Overlap(f, FromRect(r))) { why = "Deixe o caminho livre"; return false; }
            // Buildings, trees, benches, lamps... sampled over the footprint.
            for (float u = -f.hx; u <= f.hx + .001f; u += Mathf.Max(.2f, f.hx / 4))
                for (float v = -f.hz; v <= f.hz + .001f; v += Mathf.Max(.2f, f.hz / 4))
                {
                    var p = f.c + f.ax * u + f.az * v;
                    if (!CheckoutBlockPaths.FixedFree(new Vector3(p.x, 0, p.y))) { why = "Sem espaço aqui"; return false; }
                }
            foreach (var other in items.Values)
                if (other != it && other.root && other.outside && !other.ghost && Overlap(f, FootprintOf(other, -.012f))) { why = "Sem espaço aqui"; return false; }
            why = null; return true;
        }

        static Footprint FromRect(Rect r) => new Footprint { c = r.center, ax = Vector2.right, az = Vector2.up, hx = r.width / 2, hz = r.height / 2 };

        // Keeps the piece inside its area (shop floor or block) and, inside the shop, pulls it flush against a
        // wall when it gets close, so layouts never poke through the walls.
        public Vector3 Clamp(Item it, Vector3 position, float rot, float snap = .35f)
        {
            var f = FootprintAt(it, position, rot);
            var offset = new Vector2(position.x, position.z) - f.c;
            float ex = f.hx * Mathf.Abs(f.ax.x) + f.hz * Mathf.Abs(f.az.x), ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
            var r = RegionOf(it); var c = f.c;
            float minX = r.xMin + ex, maxX = r.xMax - ex, minZ = r.yMin + ez, maxZ = r.yMax - ez;
            c.x = minX > maxX ? r.center.x : Mathf.Clamp(c.x, minX, maxX);
            c.y = minZ > maxZ ? r.center.y : Mathf.Clamp(c.y, minZ, maxZ);
            if (!it.outside)
            {
                if (c.x - minX < snap) c.x = minX; else if (maxX - c.x < snap) c.x = maxX;
                if (maxZ - c.y < snap) c.y = maxZ; else if (c.y - minZ < snap) c.y = minZ;
            }
            var p = c + offset;
            return new Vector3(p.x, position.y, p.y);
        }

        // ------------------------------------------------------------------ geometry (world space, current stage)
        public Rect FloorRect
        {
            // Wall to wall (inner faces, rail excluded). The shell sizes its walls so this is always a whole
            // number of half squares: the grid starts on the west/front walls and ends exactly on the others.
            get => CheckoutMarketShell.ClearRect(layout.State);
        }

        // Kept clear in front of the doors so people can always get in.
        public Footprint Entrance
        {
            get
            {
                var door = WorldOf(DoorX, -7f); var f = FloorRect;
                return new Footprint { c = new Vector2(door.x, f.yMin + .9f), ax = Vector2.right, az = Vector2.up, hx = 1.35f, hz = .9f };
            }
        }
        public Vector3 EntrancePoint => WorldOf(DoorX, -6.2f);

        // The staff corridor inside the rear roller door: nothing may stand there (stock clerks carry boxes through).
        public Footprint ServiceDoor
        {
            get
            {
                var door = WorldOf(RearDoorX, 7f); var f = FloorRect;
                return new Footprint { c = new Vector2(door.x, f.yMax - 1.3f), ax = Vector2.right, az = Vector2.up, hx = .98f, hz = 1.3f };
            }
        }

        static Vector2 XZ(Vector3 v) => new Vector2(v.x, v.z);

        public Footprint FootprintAt(Item it, Vector3 position, float rot, float pad = 0)
        {
            var q = Quaternion.Euler(0, rot, 0);
            float s = it.scale > 0 ? it.scale : 1;
            var min = Square(it.piece.min) * s; var max = Square(it.piece.max) * s;
            var center = position + q * new Vector3((min.x + max.x) * .5f, 0, (min.y + max.y) * .5f);
            return new Footprint { c = XZ(center), ax = XZ(q * Vector3.right), az = XZ(q * Vector3.forward), hx = (max.x - min.x) * .5f + pad, hz = (max.y - min.y) * .5f + pad };
        }
        // Footprint edges within 6 cm of a quarter square land on it (a 3.96 m counter takes exactly 4 m), so
        // pieces line up in whole squares against the walls and each other without growing visibly.
        static float Square(float v) { float q = Mathf.Round(v * 4) / 4; return Mathf.Abs(q - v) <= .061f ? q : v; }
        static Vector2 Square(Vector2 v) => new Vector2(Square(v.x), Square(v.y));
        public Footprint FootprintOf(Item it, float pad = 0) => FootprintAt(it, it.root.position, it.rot, pad);

        public static bool Overlap(Footprint a, Footprint b)
        {
            foreach (var axis in new[] { a.ax, a.az, b.ax, b.az })
            {
                float ra = a.hx * Mathf.Abs(Vector2.Dot(a.ax, axis)) + a.hz * Mathf.Abs(Vector2.Dot(a.az, axis));
                float rb = b.hx * Mathf.Abs(Vector2.Dot(b.ax, axis)) + b.hz * Mathf.Abs(Vector2.Dot(b.az, axis));
                if (Mathf.Abs(Vector2.Dot(b.c - a.c, axis)) > ra + rb) return false;
            }
            return true;
        }

        public static bool Contains(Footprint f, Vector2 p)
        {
            var d = p - f.c;
            return Mathf.Abs(Vector2.Dot(d, f.ax)) <= f.hx && Mathf.Abs(Vector2.Dot(d, f.az)) <= f.hz;
        }

        static IEnumerable<Vector2> Corners(Footprint f)
        {
            yield return f.c + f.ax * f.hx + f.az * f.hz; yield return f.c - f.ax * f.hx + f.az * f.hz;
            yield return f.c + f.ax * f.hx - f.az * f.hz; yield return f.c - f.ax * f.hx - f.az * f.hz;
        }

        // Where people need to stand to use this piece.
        public IEnumerable<Vector3> ServicePoints(Item it, Vector3 position, float rot)
        {
            var q = Quaternion.Euler(0, rot, 0); float k = it.scale > 0 ? it.scale : 1;
            if (it.piece.serves) yield return position + q * (it.piece.approach * k);
            if (it.piece.queue != null) foreach (var s in it.piece.queue) yield return position + q * (s * k);
        }

        // Can the piece stand here? `why` says what is wrong (shown in build mode).
        public bool Fits(Item it, Vector3 position, float rot, out string why)
        {
            if (it.outside) return FitsOutside(it, position, rot, out why);
            var f = FootprintAt(it, position, rot);
            var floor = FloorRect;
            // Flush against a wall is inside: a few millimetres of rounding never count.
            const float eps = .01f;
            foreach (var c in Corners(f))
                if (c.x < floor.xMin - eps || c.x > floor.xMax + eps || c.y < floor.yMin - eps || c.y > floor.yMax + eps) { why = "Fora da loja"; return false; }
            if (!designMode && !it.design)
            {
                var zone = CheckoutZone;
                if (IsCounter(it)) { foreach (var c in Corners(f)) if (c.y > zone.yMax + eps) { why = "O caixa fica na área dos caixas"; return false; } }
                else if (it.functional) { foreach (var c in Corners(f)) if (c.y < zone.yMax - eps) { why = "Área só para caixas"; return false; } }
            }
            if (Overlap(f, Entrance)) { why = "Deixe a entrada livre"; return false; }
            if (Overlap(f, ServiceDoor)) { why = "Deixe a porta dos fundos livre"; return false; }
            foreach (var other in items.Values)
            {
                if (other == it || !other.root || other.ghost || other.outside) continue;
                // Pieces may stand flush against each other (the grid snaps them edge to edge).
                var o = FootprintOf(other, -.012f);
                if (Overlap(f, o)) { why = "Sem espaço aqui"; return false; }
                foreach (var s in ServicePoints(other, other.root.position, other.rot))
                    if (Contains(FootprintAt(it, position, rot, .3f), XZ(s))) { why = "Bloqueia outro móvel"; return false; }
            }
            foreach (var s in ServicePoints(it, position, rot))
            {
                var p = XZ(s);
                if (p.x < floor.xMin + .3f || p.x > floor.xMax - .3f || p.y < floor.yMin + .3f || p.y > floor.yMax - .3f) { why = "Clientes não alcançam"; return false; }
                foreach (var other in items.Values)
                    if (other != it && other.root && !other.ghost && !other.outside && Contains(FootprintOf(other, .3f), p)) { why = "Clientes não alcançam"; return false; }
            }
            why = null; return true;
        }

        // Every counter, shelf and queue can be walked to from the door (coarse grid over the shop floor).
        public bool Reachable(out Item blocked)
        {
            blocked = null;
            var floor = FloorRect; const float cell = .25f;
            int w = Mathf.CeilToInt(floor.width / cell), h = Mathf.CeilToInt(floor.height / cell);
            var solid = new bool[w * h];
            var boxes = items.Values.Where(i => i.root && !i.outside).Select(i => FootprintOf(i, .27f)).ToArray();
            for (int z = 0; z < h; z++)
                for (int x = 0; x < w; x++)
                {
                    var p = new Vector2(floor.xMin + (x + .5f) * cell, floor.yMin + (z + .5f) * cell);
                    bool edge = p.x < floor.xMin + .2f || p.x > floor.xMax - .2f || p.y > floor.yMax - .2f;
                    solid[z * w + x] = edge || boxes.Any(b => Contains(b, p));
                }
            int Cell(Vector3 p) { int x = Mathf.Clamp(Mathf.FloorToInt((p.x - floor.xMin) / cell), 0, w - 1), z = Mathf.Clamp(Mathf.FloorToInt((p.z - floor.yMin) / cell), 0, h - 1); return z * w + x; }
            var seen = new bool[w * h]; var open = new Queue<int>();
            int start = Cell(EntrancePoint); seen[start] = true; open.Enqueue(start);
            while (open.Count > 0)
            {
                int c = open.Dequeue(), cx = c % w, cz = c / w;
                for (int k = 0; k < 4; k++)
                {
                    int nx = cx + (k == 0 ? 1 : k == 1 ? -1 : 0), nz = cz + (k == 2 ? 1 : k == 3 ? -1 : 0);
                    if (nx < 0 || nz < 0 || nx >= w || nz >= h) continue;
                    int n = nz * w + nx; if (seen[n] || solid[n]) continue;
                    seen[n] = true; open.Enqueue(n);
                }
            }
            foreach (var it in items.Values)
            {
                if (!it.root || it.outside) continue;
                foreach (var s in ServicePoints(it, it.root.position, it.rot))
                {
                    int c = Cell(s);
                    // The point itself may sit in the padded ring of its own piece: accept a reached neighbour.
                    bool ok = seen[c] || Near(seen, c, w, h);
                    if (!ok) { blocked = it; return false; }
                }
            }
            return true;
        }

        static bool Near(bool[] seen, int c, int w, int h)
        {
            int cx = c % w, cz = c / w;
            for (int dz = -1; dz <= 1; dz++) for (int dx = -1; dx <= 1; dx++)
                { int x = cx + dx, z = cz + dz; if (x >= 0 && z >= 0 && x < w && z < h && seen[z * w + x]) return true; }
            return false;
        }

        // Nearest place (and turn) around the current spot where the piece fits.
        public bool Settle(Item it)
        {
            if (!it.root) return false;
            var start = it.root.position;
            if (Fits(it, start, it.rot, out _)) return true;
            // Slide first (keeping the way it faces), turn only when there is no room at all.
            float[] turns = { it.rot, it.rot + 90, it.rot + 270, it.rot + 180 };
            foreach (var t in turns)
                for (float r = .25f; r < 14f; r += .25f)
                {
                    int steps = Mathf.Max(8, Mathf.CeilToInt(2 * Mathf.PI * r / .35f));
                    for (int k = 0; k < steps; k++)
                    {
                        float a = k * Mathf.PI * 2 / steps;
                        var p = start + new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * r;
                        if (Fits(it, p, Mathf.Repeat(t, 360), out _)) { it.rot = Mathf.Repeat(t, 360); MoveTo(it, p); return true; }
                    }
                }
            Debug.LogWarning("CHECKOUT_INTERIOR no room for " + it.id);
            return false;
        }

        // ------------------------------------------------------------------ grid snapping ("lógica de quadrados")
        // Pieces move on a square grid laid from the shop's corner, stop flush against the walls, stick edge to
        // edge to the pieces next to them and never go into them.
        public static float GridSize = .25f;
        public static bool GridOn = true;
        const float Stick = .3f;

        static Rect Aabb(Footprint f)
        {
            float ex = f.hx * Mathf.Abs(f.ax.x) + f.hz * Mathf.Abs(f.az.x), ez = f.hx * Mathf.Abs(f.ax.y) + f.hz * Mathf.Abs(f.az.y);
            return Rect.MinMaxRect(f.c.x - ex, f.c.y - ez, f.c.x + ex, f.c.y + ez);
        }

        // What a piece must keep out of: the other pieces of its area, plus the doors' clear zones inside.
        public List<Rect> Blockers(Item it)
        {
            var list = new List<Rect>();
            foreach (var other in items.Values)
                if (other != it && other.root && !other.ghost && other.outside == it.outside) list.Add(Aabb(FootprintOf(other)));
            if (!it.outside) { list.Add(Aabb(Entrance)); list.Add(Aabb(ServiceDoor)); }
            return list;
        }

        // Best spot for the piece near `desired` (world position of its pivot). `fallback` is returned when
        // there is no free place there (e.g. dragged right into a crowd).
        public Vector3 Snap(Item it, Vector3 desired, float rot, Vector3 fallback)
        {
            // Sticking to a neighbour can cover where customers stand to use it: then the plain grid spot wins.
            var stuck = SnapCore(it, desired, rot, fallback, true);
            if (Fits(it, stuck, rot, out _)) return stuck;
            var free = SnapCore(it, desired, rot, fallback, false);
            return Fits(it, free, rot, out _) ? free : stuck;
        }

        Vector3 SnapCore(Item it, Vector3 desired, float rot, Vector3 fallback, bool stick)
        {
            var f = FootprintAt(it, desired, rot);
            var offset = new Vector2(desired.x, desired.z) - f.c;
            var box = Aabb(f); float ex = box.width * .5f, ez = box.height * .5f;
            var region = RegionOf(it); var c = f.c;
            if (GridOn && GridSize > .01f)
            {
                c.x = region.xMin + Mathf.Round((c.x - ex - region.xMin) / GridSize) * GridSize + ex;
                c.y = region.yMin + Mathf.Round((c.y - ez - region.yMin) / GridSize) * GridSize + ez;
            }
            var blockers = Blockers(it);
            // Stick to neighbours: touching edges or lined-up edges when close enough.
            float bestX = Stick, bestZ = Stick, sx = c.x, sz = c.y;
            if (stick) foreach (var o in blockers)
            {
                bool rowZ = c.y + ez > o.yMin - Stick && c.y - ez < o.yMax + Stick, rowX = c.x + ex > o.xMin - Stick && c.x - ex < o.xMax + Stick;
                if (rowZ)
                    foreach (var x in new[] { o.xMax + ex, o.xMin - ex, o.xMin + ex, o.xMax - ex })
                        if (Mathf.Abs(x - c.x) < bestX) { bestX = Mathf.Abs(x - c.x); sx = x; }
                if (rowX)
                    foreach (var z in new[] { o.yMax + ez, o.yMin - ez, o.yMin + ez, o.yMax - ez })
                        if (Mathf.Abs(z - c.y) < bestZ) { bestZ = Mathf.Abs(z - c.y); sz = z; }
            }
            c = new Vector2(sx, sz);
            c = Inside(c, ex, ez, region, !it.outside);
            // Never inside another piece: push out along the shortest way, a few rounds.
            for (int round = 0; round < 10; round++)
            {
                bool pushed = false;
                foreach (var o in blockers)
                {
                    float px = Mathf.Min(c.x + ex - o.xMin, o.xMax - (c.x - ex)), pz = Mathf.Min(c.y + ez - o.yMin, o.yMax - (c.y - ez));
                    if (px <= .002f || pz <= .002f) continue;
                    if (px < pz) c.x += c.x < o.center.x ? -(c.x + ex - o.xMin) : o.xMax - (c.x - ex);
                    else c.y += c.y < o.center.y ? -(c.y + ez - o.yMin) : o.yMax - (c.y - ez);
                    c = Inside(c, ex, ez, region, false);
                    pushed = true;
                }
                if (!pushed) return new Vector3(c.x + offset.x, desired.y, c.y + offset.y);
            }
            foreach (var o in blockers)
                if (Mathf.Min(c.x + ex - o.xMin, o.xMax - (c.x - ex)) > .002f && Mathf.Min(c.y + ez - o.yMin, o.yMax - (c.y - ez)) > .002f) return fallback;
            return new Vector3(c.x + offset.x, desired.y, c.y + offset.y);
        }

        static Vector2 Inside(Vector2 c, float ex, float ez, Rect r, bool walls)
        {
            float minX = r.xMin + ex, maxX = r.xMax - ex, minZ = r.yMin + ez, maxZ = r.yMax - ez;
            c.x = minX > maxX ? r.center.x : Mathf.Clamp(c.x, minX, maxX);
            c.y = minZ > maxZ ? r.center.y : Mathf.Clamp(c.y, minZ, maxZ);
            if (walls)
            {
                if (c.x - minX < Stick) c.x = minX; else if (maxX - c.x < Stick) c.x = maxX;
                if (maxZ - c.y < Stick) c.y = maxZ; else if (c.y - minZ < Stick) c.y = minZ;
            }
            return c;
        }

        // ------------------------------------------------------------------ map design (editor + growth)
        public IEnumerable<string> Templates => kit ? kit.Cast<Transform>().Select(t => t.name).Where(n => !n.StartsWith("_")) : Enumerable.Empty<string>();
        public bool HasTemplate(string name) => kit && !string.IsNullOrEmpty(name) && kit.Find(name);

        // Every piece as design data (the editor saves this for the stage it shows).
        public DesignPiece[] CaptureDesign() => items.Values.Where(i => i.root && (i.design || i.functional)).OrderBy(i => i.id).Select(i => new DesignPiece
        {
            id = i.id, type = i.type, template = i.design ? i.template : null, x = Mathf.Round(i.x * 1000) / 1000, z = Mathf.Round(i.z * 1000) / 1000,
            rot = Mathf.Repeat(Mathf.Round(i.rot * 10) / 10, 360), scale = Mathf.Round((i.scale > 0 ? i.scale : 1) * 1000) / 1000, outside = i.outside,
        }).ToArray();

        // Rebuilds the design pieces and puts every game piece where `d` says (or its default), e.g. after the
        // editor switched stage or undid a change.
        public void ResetTo(DesignStage d)
        {
            if (!kit) return;
            foreach (var it in items.Values.Where(i => i.design).ToList()) { if (it.root) Destroy(it.root.gameObject); items.Remove(it.id); }
            var pieces = d?.interior ?? Array.Empty<DesignPiece>();
            foreach (var p in pieces)
            {
                if (p == null || string.IsNullOrEmpty(p.id) || !p.id.StartsWith("design-") || !HasTemplate(p.template) || items.ContainsKey(p.id)) continue;
                var it = new Item { id = p.id, type = "design", template = p.template, design = true, placed = true, saved = true, x = p.x, z = p.z, rot = p.rot, scale = p.scale > 0 ? p.scale : 1, outside = p.outside };
                Build(it); if (!it.root) continue;
                items[it.id] = it; Place(it);
            }
            var functional = items.Values.Where(i => i.root && i.functional).OrderBy(i => i.type == "checkout" || i.type == "kiosk" ? 0 : i.type == "sector" ? 1 : 2).ThenBy(i => i.id).ToList();
            foreach (var it in functional)
            {
                var e = pieces.FirstOrDefault(p => p != null && p.id == it.id);
                Vector3 spot; float size = 1;
                if (e != null) { spot = new Vector3(e.x, e.rot, e.z); size = e.scale > 0 ? e.scale : 1; }
                else spot = Defaults.TryGetValue(it.id, out var v) ? v : Vector3.zero;
                it.x = spot.x; it.z = spot.z; it.rot = spot.y; it.scale = size; it.placed = true; it.ghost = false;
                Place(it);
            }
            foreach (var it in functional) if (!Fits(it, it.root.position, it.rot, out _)) Settle(it);
            CheckoutBlockPaths.Invalidate();
        }

        // A piece of furniture/decoration that belongs to the map design ("design-N").
        public Item AddDesign(string template, Vector3 near, bool outside = false, float rot = 0, float scale = 1)
        {
            if (!HasTemplate(template)) return null;
            int n = 1; while (items.ContainsKey("design-" + n)) n++;
            var it = new Item { id = "design-" + n, type = "design", template = template, design = true, placed = true, saved = true, outside = outside, rot = rot, scale = scale };
            Build(it); if (!it.root) return null;
            items[it.id] = it;
            MoveTo(it, near);
            if (!Settle(it)) { Destroy(it.root.gameObject); items.Remove(it.id); return null; }
            return it;
        }

        // The shop grew in this session and the map design has a layout for the new stage: the game's pieces
        // move to it (the player can still rearrange them afterwards).
        public bool AdoptDesign()
        {
            // The player arranges the shop: growing it never moves their furniture to the map design's layout.
            if (designMode || editing || !kit || !CheckoutMapDesign.Explicit(layout.State.stage)) return false;
            if (!designMode) return false;
            var d = Design; bool moved = false;
            foreach (var it in items.Values.Where(i => i.root && i.functional))
            {
                var e = d.interior.FirstOrDefault(p => p != null && p.id == it.id);
                if (e == null) continue;
                it.x = e.x; it.z = e.z; it.rot = e.rot; it.scale = e.scale > 0 ? e.scale : 1; it.saved = true; Place(it); moved = true;
            }
            if (!moved) return false;
            foreach (var it in items.Values.Where(i => i.root && i.functional).OrderBy(i => i.id).ToList())
                if (!Fits(it, it.root.position, it.rot, out _)) Settle(it);
            MarkPending(); map?.SaveInterior(); CheckoutBlockPaths.Invalidate();
            return true;
        }

        // ------------------------------------------------------------------ queries used by customers and staff
        public Item Get(string id) => id != null && items.TryGetValue(id, out var it) && it.root ? it : null;
        public static string ShelfKey(string shelfId) => "shelf:" + shelfId;
        public static string SectorKey(string sectorId) => "sector:" + sectorId;
        public Vector3 Point(Item it, Vector3 local) => it.root.TransformPoint(local);
        public Vector3 Approach(Item it) => it.root.TransformPoint(it.piece.approach);
        public Vector3 StaffPoint(Item it) => it.root.TransformPoint(it.piece.staff);
        public int QueueLength(string id) { var it = Get(id); return it != null && it.piece.queue != null && it.piece.queue.Length > 0 ? it.piece.queue.Length : 1; }
        public Vector3 QueueSpot(string id, int i)
        {
            var it = Get(id); if (it == null || it.piece.queue == null || it.piece.queue.Length == 0) return EntrancePoint;
            return it.root.TransformPoint(it.piece.queue[Mathf.Clamp(i, 0, it.piece.queue.Length - 1)]);
        }
        public Vector3 Register(string id) { var it = Get(id); return it != null ? it.root.TransformPoint(it.piece.register) : EntrancePoint; }

        // The i-th free standing spot near `near` (spaced .8 m apart), e.g. where customers wait for help.
        public Vector3 FreeSpotNear(Vector3 near, int i)
        {
            var floor = FloorRect; var found = new List<Vector3>();
            var boxes = items.Values.Where(x => x.root && !x.outside).Select(x => FootprintOf(x, .4f)).ToArray();
            for (float r = 0; r < 10f && found.Count <= i; r += .3f)
            {
                int steps = r == 0 ? 1 : Mathf.CeilToInt(2 * Mathf.PI * r / .3f);
                for (int k = 0; k < steps && found.Count <= i; k++)
                {
                    float a = k * Mathf.PI * 2 / steps;
                    var p = near + new Vector3(Mathf.Cos(a), 0, Mathf.Sin(a)) * r;
                    if (p.x < floor.xMin + .4f || p.x > floor.xMax - .4f || p.z < floor.yMin + .4f || p.z > floor.yMax - .4f) continue;
                    var q = XZ(p);
                    if (boxes.Any(b => Contains(b, q)) || found.Any(f => (f - p).sqrMagnitude < .64f)) continue;
                    found.Add(p);
                }
            }
            return found.Count > i ? found[i] : near;
        }

        // Stock clerks work in front of the shelves, walking along them.
        public bool ClerkSpot(int n, out Vector3 spot, out Vector3 axis)
        {
            var shelves = items.Values.Where(i => i.root && i.type == "shelf" && !i.building).OrderBy(i => i.id).ToList();
            if (shelves.Count == 0) { spot = EntrancePoint; axis = Vector3.right; return false; }
            var s = shelves[n % shelves.Count];
            spot = s.root.TransformPoint(s.piece.approach + new Vector3(0, 0, .15f)); axis = s.root.right;
            return true;
        }

        public void SetFill(Item it, float ratio)
        {
            if (it?.piece?.fill == null) return;
            var groups = it.piece.fill; int n = groups.Length;
            int visible = ratio <= 0 ? 0 : Mathf.Clamp(Mathf.CeilToInt(n * ratio), 1, n);
            for (int i = 0; i < n; i++) if (groups[i]) groups[i].SetActive(i < visible);
        }

        // Solid boxes for the navigation mesh: (center, size, yaw).
        public IEnumerable<(Vector3 center, Vector3 size, float yaw)> Obstacles()
        {
            foreach (var it in items.Values)
            {
                if (!it.root) continue;
                var f = FootprintOf(it);
                yield return (new Vector3(f.c.x, 1.5f, f.c.y), new Vector3(f.hx * 2 + .06f, 3, f.hz * 2 + .06f), it.rot);
            }
        }

        // ------------------------------------------------------------------ saving
        public void MarkPending() { pending = Export(); pendingAt = Time.unscaledTime; foreach (var it in items.Values) it.saved = true; }

        public InteriorItem[] Export() => items.Values.Where(i => i.root && !i.design).Select(i => new InteriorItem { id = i.id, type = i.type, x = i.x, z = i.z, rot = Mathf.Repeat(Mathf.Round(i.rot), 360), outside = i.outside })
            .Concat(waiting.Where(w => !items.ContainsKey(w.Key)).Select(w => new InteriorItem { id = w.Key, type = w.Value.type, stored = true })).ToArray();

        public string ExportJson()
        {
            var sb = new StringBuilder("[");
            bool first = true;
            foreach (var i in Export())
            {
                if (!first) sb.Append(','); first = false;
                sb.Append("{\"id\":\"").Append(i.id).Append("\",\"type\":\"").Append(i.type).Append("\",\"x\":")
                  .Append(i.x.ToString("0.###", CultureInfo.InvariantCulture)).Append(",\"z\":").Append(i.z.ToString("0.###", CultureInfo.InvariantCulture))
                  .Append(",\"rot\":").Append(i.rot.ToString("0", CultureInfo.InvariantCulture)).Append(i.stored ? ",\"stored\":true" : "").Append(i.outside ? ",\"outside\":true}" : "}");
            }
            return sb.Append(']').ToString();
        }

        // A new decoration from the build-mode inventory, dropped at `near` (or the closest free spot).
        public Item AddDecor(string type, Vector3 near, bool outside = false)
        {
            if (!kit.Find(type)) return null;
            int n = 1; while (items.ContainsKey("decor-" + n)) n++;
            var it = new Item { id = "decor-" + n, type = type, template = type, functional = false, placed = true, outside = outside };
            Build(it); if (!it.root) return null;
            items[it.id] = it;
            MoveTo(it, near);
            if (!Settle(it)) { Destroy(it.root.gameObject); items.Remove(it.id); return null; }
            return it;
        }

        // Takes a piece of shop furniture out of the inventory and stands it at `near` (or the closest free spot).
        public Item PlaceWaiting(string id, Vector3 near)
        {
            if (!waiting.TryGetValue(id, out var w) || items.ContainsKey(id) || !kit.Find(w.template)) return null;
            var it = new Item { id = id, type = w.type, template = w.template, functional = true, placed = true };
            var d = DefaultFor(id, out _); it.rot = d.y;
            Build(it); if (!it.root) return null;
            items[id] = it;
            MoveTo(it, near);
            if (!Settle(it)) { Destroy(it.root.gameObject); items.Remove(id); return null; }
            waiting.Remove(id);
            return it;
        }

        // Build mode was cancelled: a piece stored during the session stands where it was.
        public Item RestoreWaiting(InteriorItem saved)
        {
            if (saved == null || !waiting.TryGetValue(saved.id, out var w) || items.ContainsKey(saved.id) || !kit.Find(w.template)) return null;
            var it = new Item { id = saved.id, type = w.type, template = w.template, functional = true, placed = true, saved = true, x = saved.x, z = saved.z, rot = saved.rot };
            Build(it); if (!it.root) return null;
            items[it.id] = it; Place(it); waiting.Remove(it.id);
            return it;
        }

        // Puts a piece of shop furniture back in the inventory.
        public void Unplace(Item it)
        {
            if (it == null || !it.functional || it.building) return;
            waiting[it.id] = (it.type, it.template);
            CheckoutInteriorWorks.Finish(it);
            if (it.root) Destroy(it.root.gameObject);
            items.Remove(it.id);
        }

        // Puts back a decoration that was stored during a cancelled build-mode session.
        public Item RestoreDecor(InteriorItem saved)
        {
            if (saved == null || IsFunctional(saved.type) || items.ContainsKey(saved.id) || !kit.Find(saved.type)) return null;
            var it = new Item { id = saved.id, type = saved.type, template = saved.type, placed = true, x = saved.x, z = saved.z, rot = saved.rot, outside = saved.outside };
            Build(it); if (!it.root) return null;
            items[it.id] = it; Place(it);
            return it;
        }

        public void RemoveDecor(Item it)
        {
            if (it == null || it.functional) return;
            if (it.root) Destroy(it.root.gameObject);
            items.Remove(it.id);
        }

        // Build mode leaves the map design's own pieces alone; the map editor picks everything.
        public Item Pick(Ray ray, bool includeDesign = false)
        {
            Item best = null; float bestDistance = float.MaxValue;
            foreach (var it in items.Values)
            {
                if (!it.root || (it.design && !includeDesign)) continue;
                var box = it.root.GetComponent<BoxCollider>();
                if (box && box.Raycast(ray, out var hit, 200) && hit.distance < bestDistance) { best = it; bestDistance = hit.distance; }
            }
            return best;
        }
    }

    // Serializable pieces of the snapshot (src/services/simulator-snapshot.ts: interior, decorCatalog).
    [Serializable] public class InteriorState { public InteriorItem[] items; public DecorOwned[] owned; }
    [Serializable] public class InteriorItem { public string id, type; public float x, z, rot; public bool stored, outside; }
    [Serializable] public class DecorOwned { public string type; public int count; }
    [Serializable] public class DecorEntry { public string id, name, description, zone; public int coinPrice, diamondPrice, requiredLevel; }
}
