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
        struct ShopPlan
        {
            public Rect floor;            // inner floor, wall to wall
            public float doorMin, doorMax; // door opening along x, in the front wall
            public Rect counter;          // the fixed counter with the register and the clerk's stool
            public Vector2 pay, queueStep; // where the customer pays, and how the line grows from there
            public float floorY;          // top of the floor slab
        }
        static readonly Dictionary<string, ShopPlan> Plans = new Dictionary<string, ShopPlan>
        {
            ["Era4_Spati"] = new ShopPlan { floor = Rect.MinMaxRect(-2.85f, -1.12f, 2.85f, 2.25f), doorMin = .72f, doorMax = 1.62f, counter = Rect.MinMaxRect(1.3f, .0f, 3.03f, 1.4f), pay = new Vector2(2.15f, -.35f), queueStep = new Vector2(-.75f, 0), floorY = .03f },
            ["Era5_Quitanda"] = new ShopPlan { floor = Rect.MinMaxRect(-4.1f, -2.4f, 4.1f, 2.6f), doorMin = -3.45f, doorMax = .55f, counter = Rect.MinMaxRect(1.35f, -1.7f, 3.15f, -.3f), pay = new Vector2(2.25f, -2.0f), queueStep = new Vector2(-.75f, 0), floorY = .06f },
            ["Era6_Minimercado"] = new ShopPlan { floor = Rect.MinMaxRect(-5.65f, -2.9f, 5.65f, 2.95f), doorMin = -1.2f, doorMax = .2f, counter = Rect.MinMaxRect(2.55f, -2.75f, 3.95f, -.75f), pay = new Vector2(2.25f, -1.75f), queueStep = new Vector2(0, .75f), floorY = .16f },
        };
        /// <summary>The current expansion is a shop with an inside the player furnishes (Späti, quitanda, minimercado).</summary>
        public static bool ShopInside { get; private set; }
        /// <summary>Inner floor of the shop (world x/z) where shelves and coolers may stand.</summary>
        public static Rect InteriorFloor { get; private set; }
        /// <summary>The fixed counter of the shop (world x/z): nothing else may stand there.</summary>
        public static Rect CounterArea { get; private set; }
        /// <summary>Centre of the door opening (world x/z) and its half width.</summary>
        public static Vector2 Door { get; private set; }
        public static float DoorHalf { get; private set; }
        /// <summary>World height of the shop floor (where the placed furniture stands).</summary>
        public static float FloorY { get; private set; }
        static Vector3 payPoint, queueStep;
        /// <summary>Solid parts of the stall for the navigation: walls with the door left open and the counter in a
        /// shop, the whole model otherwise.</summary>
        public static readonly List<Bounds> Obstacles = new List<Bounds>();

        void PlanShop(GameObject model)
        {
            Obstacles.Clear();
            ShopInside = Small && model && Plans.TryGetValue(model.name, out _);
            if (!ShopInside) { Obstacles.Add(Footprint); return; }
            var plan = Plans[model.name];
            var o = model.transform.position; float k = model.transform.localScale.x;
            Vector2 W(float x, float z) => new Vector2(o.x + x * k, o.z + z * k);
            Rect WR(Rect r) { var a = W(r.xMin, r.yMin); var b = W(r.xMax, r.yMax); return Rect.MinMaxRect(a.x, a.y, b.x, b.y); }
            var f = WR(plan.floor); InteriorFloor = f; CounterArea = WR(plan.counter); FloorY = o.y + plan.floorY * k;
            var d0 = W(plan.doorMin, plan.floor.yMin); var d1 = W(plan.doorMax, plan.floor.yMin);
            Door = new Vector2((d0.x + d1.x) * .5f, f.yMin); DoorHalf = (d1.x - d0.x) * .5f;
            var p = W(plan.pay.x, plan.pay.y); payPoint = new Vector3(p.x, .15f, p.y); queueStep = new Vector3(plan.queueStep.x * k, 0, plan.queueStep.y * k);
            const float t = .35f, h = 2f;
            void Wall(float x0, float z0, float x1, float z1) { if (x1 - x0 > .05f && z1 - z0 > .05f) Obstacles.Add(new Bounds(new Vector3((x0 + x1) * .5f, 1f, (z0 + z1) * .5f), new Vector3(x1 - x0, h, z1 - z0))); }
            Wall(f.xMin - t, f.yMax, f.xMax + t, f.yMax + t);           // back
            Wall(f.xMin - t, f.yMin - t, f.xMin, f.yMax);               // left
            Wall(f.xMax, f.yMin - t, f.xMax + t, f.yMax);               // right
            Wall(f.xMin - t, f.yMin - t, d0.x, f.yMin);                 // front, left of the door
            Wall(d1.x, f.yMin - t, f.xMax + t, f.yMin);                 // front, right of the door
            var c = CounterArea; Wall(c.xMin, c.yMin, c.xMax, c.yMax);  // counter
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
            // In a shop the line starts at the counter and grows inside; the late ones wait by the door.
            if (ShopInside)
            {
                var spot = payPoint + queueStep * Mathf.Min(i, 3);
                if (i <= 3) return spot;
                return new Vector3(Door.x + .6f * ((i - 4) % 3 - 1), .15f, Door.y - 1.2f - .8f * ((i - 4) / 3));
            }
            // A short line from the cooler end of the stall towards the sidewalk.
            var p = new Vector3(Centre.x + 1.9f, .15f, FrontZ - .1f);
            if (i <= 0) return p;
            return i < 3 ? p + new Vector3(.25f * i, 0, -.85f * i) : p + new Vector3(.5f + .85f * (i - 2), 0, -1.7f);
        }
        public static Vector3 HelpSpot(int i) => ShopInside
            ? new Vector3(Mathf.Clamp(Door.x - .5f + .7f * (i % 3), InteriorFloor.xMin + .4f, InteriorFloor.xMax - .4f), .15f, Door.y + .8f + .7f * (i / 3))
            : new Vector3(Centre.x - 2.6f - .8f * (i % 3), .15f, FrontZ - .8f * (i / 3));

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
            Era = era; Small = small;
            if (small) HideMarket();
            else if (changed) ShowMarket();
            if (sites) sites.Apply(snapshot);
            if (works) works.Apply(snapshot);
            bool wasShop = ShopInside;
            ShowModel(small ? ModelFor(era) : null);
            if (!small) { ShopInside = false; Obstacles.Clear(); }
            // The furniture the player placed stands inside the shop expansions.
            var holder = map.Interior ? map.Interior.Holder : null;
            if (holder && small) { holder.gameObject.SetActive(ShopInside); if (ShopInside) hidden.Remove(holder.gameObject); else if (!hidden.Contains(holder.gameObject)) hidden.Add(holder.gameObject); }
            // Entering or leaving a shop expansion: the furniture moves between the shop's floor and the market's.
            if (wasShop != ShopInside && map.Interior)
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
            model.transform.position += new Vector3(Centre.x - b.center.x, 0, FrontLine - b.min.z);
            b.center += new Vector3(Centre.x - b.center.x, 0, FrontLine - b.min.z);
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
            if (!model) return;
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
            // Clicking the stall opens the playable checkout, like the register of the market.
            var click = new GameObject("Stall checkout");
            click.transform.SetParent(go.transform, false);
            click.transform.localPosition = new Vector3(1.25f, .8f, -.6f);
            click.AddComponent<BoxCollider>().size = new Vector3(1.2f, 1.6f, 1.2f);
            click.AddComponent<CheckoutTarget>().panel = "checkout";
            return go;
        }
    }
}
