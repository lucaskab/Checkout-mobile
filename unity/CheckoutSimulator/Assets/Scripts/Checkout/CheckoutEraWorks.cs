using UnityEngine;
using MarketDay;

namespace Checkout
{
    // The works of each expansion (snapshot era.construction), each with what makes sense for that step:
    //  tenda        — the tent goes up on lot A1: poles carried from a pickup, stakes hammered, the frame rises;
    //  banca        — carpenters: a sawhorse, planks carried, the wooden stall frame rises behind the tent;
    //  contêiner    — a crane truck sets a container down behind the stall; a welder cuts the window, a painter;
    //  Späti        — a small brick shop: walls rise, mixer turning, bricks carried, a scaffold tower;
    //  quitanda     — a bigger brick shop: walls, two scaffolds, roof trusses, mixer;
    //  minimercado  — grows into lot B1: a mini excavator digs the footings into a dumper truck, slab, walls;
    //  mercadinho   — the first real building: excavator and dumper, foundation, steel beams, glass, forklift;
    //  supermercado — the tower-crane site (CheckoutConstructionSite) behind the shop, on lots A2/B2;
    //  hipermercado — the tower-crane site on lots C1/C2, trucks in from the east street;
    //  rede         — the chain's big sign goes up on the roof from two aerial platforms, painters below.
    // The old expansion keeps selling while the next one is built next to it (the works never stand on it).
    // A small countdown floats over the works; clicking it opens Loja → Expansões.
    public class CheckoutEraWorks : MonoBehaviour
    {
        CheckoutWorksScene scene; string key;
        CheckoutConstructionSite bigSite; Transform world;

        public void Initialize(Transform root) { world = root; }

        public void Apply(Snapshot snapshot)
        {
            var obra = snapshot?.era?.construction;
            string next = obra != null && !string.IsNullOrEmpty(obra.eraId) && !CheckoutMapEditor.Open ? obra.eraId + ":" + obra.startedAt : null;
            if (next == key) { if (scene && obra != null) scene.SetTimes(obra.startedAt, obra.endsAt); return; }
            Clear();
            key = next;
            if (next == null) return;
            scene = CheckoutWorksScene.Create("Expansion works " + obra.eraId, obra.startedAt, obra.endsAt);
            scene.transform.SetParent(transform, false);
            Build(obra.eraId, snapshot);
        }

        void Clear()
        {
            if (scene) Destroy(scene.gameObject);
            scene = null;
            if (bigSite) bigSite.Hide();
        }

        void OnDestroy() => Clear();

        static Vector3 G(float x, float z) => new Vector3(x, .13f, z);
        static readonly Vector3 East = Vector3.right, West = Vector3.left, North = Vector3.forward, South = Vector3.back;

        void Build(string era, Snapshot snapshot)
        {
            var s = scene;
            const float cx = -11.5f; // middle of lot A1
            switch (era)
            {
                case "tenda":
                {
                    // The mesinha sells on the sidewalk; the tent goes up right behind it, on lot A1.
                    var frame = s.Prop("Works_TentFrame", G(cx, -4.9f), South, 1.2f); s.Grow(frame, 0, .85f);
                    var truck = s.Prop("Works_Pickup", G(cx + 1, 1.8f), East);
                    s.Prop("Prop_TentPoles", G(cx + 3.6f, -1.6f), East); s.Prop("Prop_CanvasRoll", G(cx + 3.4f, -.6f), East);
                    s.Prop("Prop_Toolbox", G(cx - 3.2f, -2.8f), South);
                    s.Prop("Prop_Cone", G(cx - 3.4f, -7.9f), South); s.Prop("Prop_Cone", G(cx + 3.4f, -7.9f), South);
                    s.Carrier(G(cx + 3.2f, -1.1f), G(cx + 1.4f, -4.4f), "Prop_Pole", 0);
                    s.Carrier(G(cx - .8f, .8f), G(cx - 1.4f, -4.2f), "Prop_Pole", 2);
                    s.ToolWorker(G(cx - 2.6f, -6.6f), G(cx - 2.2f, -5.9f), CheckoutWorksScene.Tool.Hammer, 1);
                    s.Foreman(G(cx + 3.6f, -3.6f), G(cx + 3.6f, -6.4f), G(cx, -4.9f), 3);
                    break;
                }
                case "banca":
                {
                    // Carpenters build the wooden stall behind the tent.
                    var frame = s.Prop("Works_StallFrame", G(cx, 1.0f), South, 1.15f); s.Grow(frame, 0, .9f);
                    s.Prop("Prop_Sawhorse", G(cx - 4.2f, -1.6f), East);
                    s.ToolWorker(G(cx - 4.2f, -2.4f), G(cx - 4.2f, -1.6f), CheckoutWorksScene.Tool.Saw, 0);
                    s.Prop("Prop_PlankStack", G(cx + 4.1f, 3.3f), North);
                    s.Carrier(G(cx + 4.1f, 2.4f), G(cx + 1.2f, -1.2f), "Prop_Plank", 1);
                    s.ToolWorker(G(cx + 3.3f, .9f), G(cx + 2.4f, .9f), CheckoutWorksScene.Tool.Hammer, 2);
                    s.Prop("Works_Pickup", G(cx - 2.5f, 3.6f), West);
                    s.Prop("Prop_Toolbox", G(cx - 4.6f, .2f), South);
                    s.Foreman(G(cx + 4.4f, -1.2f), G(cx - 3f, -1.4f), G(cx, 1f), 3);
                    break;
                }
                case "conteiner":
                {
                    // A crane truck brings the container and sets it down behind the stall; then it is cut and painted.
                    var box = s.Prop("Works_Container", G(cx, 3.3f), East);
                    s.CraneTruck(G(cx, 3.3f), East, box, G(cx, 3.6f), G(cx, -.6f), true, .05f, .45f);
                    s.ToolWorker(G(cx - 2.2f, -2.4f), G(cx - 2.2f, -1.5f), CheckoutWorksScene.Tool.Weld, 0);
                    s.ToolWorker(G(cx + 2.4f, -2.4f), G(cx + 2.4f, -1.5f), CheckoutWorksScene.Tool.Roller, 1);
                    s.Prop("Prop_Generator", G(cx + 4.8f, -1.6f), South); s.Prop("Prop_WorkLight", G(cx - 4.9f, -1.8f), East);
                    s.Prop("Prop_PaintBuckets", G(cx + 4.6f, -.4f), South);
                    s.Foreman(G(cx - 4.6f, .8f), G(cx - 4.6f, -2.6f), G(cx, -.6f), 3);
                    break;
                }
                case "spati":
                {
                    s.Walls(G(cx, 1.3f), new Vector2(7.2f, 3.6f), 2.9f, new Color(.72f, .42f, .3f), .05f, .9f);
                    s.Prop("Prop_ScaffoldTower", G(cx - 4.7f, 1.3f), East);
                    s.Mixer(G(cx + 4.7f, -.6f), West);
                    s.Prop("Prop_BrickPallet", G(cx + 4.6f, 3.8f), North); s.Prop("Prop_CementBags", G(cx - 4.6f, 4f), North);
                    s.Prop("Prop_WheelbarrowFull", G(cx + 3.4f, -1.9f), West);
                    s.Carrier(G(cx + 4.6f, 3.0f), G(cx + 1.6f, -.8f), "Prop_Brick", 0);
                    s.ToolWorker(G(cx - 1.4f, -1.3f), G(cx - 1.4f, -.2f), CheckoutWorksScene.Tool.Trowel, 1);
                    s.ToolWorker(G(cx + 3.9f, .2f), G(cx + 4.7f, -.6f), CheckoutWorksScene.Tool.Shovel, 2);
                    s.Foreman(G(cx - 3.5f, -1.9f), G(cx + 1f, -1.9f), G(cx, 1.3f), 3);
                    break;
                }
                case "quitanda":
                {
                    s.Walls(G(cx, 2.1f), new Vector2(9.6f, 3.9f), 3.2f, new Color(.93f, .85f, .66f), .05f, .85f, 1.8f);
                    s.Prop("Prop_ScaffoldTower", G(cx - 3.3f, -.8f), East); s.Prop("Prop_ScaffoldTower", G(cx + 3.3f, -.8f), East);
                    s.Mixer(G(cx + 5.0f, 4.1f), West);
                    s.Prop("Prop_RoofTrusses", G(cx + 5.1f, -.6f), North);
                    s.Prop("Prop_CementBags", G(cx - 5.2f, 4.3f), North);
                    s.ToolWorker(G(cx - 1.0f, -.6f), G(cx - 1.0f, .3f), CheckoutWorksScene.Tool.Trowel, 0);
                    s.ToolWorker(G(cx + 5.0f, 3.2f), G(cx + 5.0f, 4.1f), CheckoutWorksScene.Tool.Shovel, 1);
                    s.Carrier(G(cx - 5.1f, 3.4f), G(cx - 4.3f, .2f), "Prop_CementBag", 2);
                    s.Foreman(G(cx + 1.5f, -1.8f), G(cx + 5f, -1.8f), G(cx, 2.1f), 3);
                    break;
                }
                case "minimercado":
                {
                    // The shop grows into lot B1: a mini excavator digs the footings into a dumper truck that comes
                    // in from the avenue, the slab is poured and the new walls go up next to the quitanda.
                    var slab = s.Prop("Works_Foundation", G(-1.6f, -3.6f), South); slab.localScale = new Vector3(.9f, 1, .95f);
                    s.Walls(G(-1.6f, -3.6f), new Vector2(7.0f, 5.4f), 3f, new Color(.95f, .93f, .88f), .35f, .95f, 2f);
                    s.Excavator("Works_MiniExcavator", G(-.4f, 2.4f), South, G(-1.0f, -.6f), G(4.1f, 1.4f));
                    s.Truck("Works_DumpTruck", new[] { G(4.1f, -16f), G(4.1f, -11f), G(4.1f, -.6f) }, 22f);
                    s.Prop("Prop_RebarBundle", G(-4.4f, 3.6f), East); s.Prop("Prop_BrickPallet", G(-4.8f, -7.7f), East);
                    s.Mixer(G(-4.5f, 1.2f), East);
                    s.Carrier(G(-4.0f, -7.0f), G(-2.6f, -6.6f), "Prop_Brick", 0);
                    s.ToolWorker(G(2.6f, -3.6f), G(1.8f, -3.6f), CheckoutWorksScene.Tool.Trowel, 1);
                    s.ToolWorker(G(-3.4f, 1.0f), G(-4.4f, 1.2f), CheckoutWorksScene.Tool.Shovel, 2);
                    s.Foreman(G(5.2f, -7.4f), G(5.2f, -6.2f), G(-1.6f, -3.6f), 3);
                    break;
                }
                case "mercadinho":
                {
                    // The first real building over A1 + B1: the new wing goes up on B1 next to the minimercado, the
                    // footings behind it are dug, beams and glass wait on the back strip, a forklift moves pallets.
                    var east = s.Prop("Works_Foundation", G(1.9f, -3.5f), South); east.localScale = new Vector3(.875f, 1, 1.37f);
                    s.Walls(G(1.9f, -3.5f), new Vector2(6.6f, 7.8f), 3.3f, new Color(.93f, .9f, .82f), .3f, .95f, 2.4f);
                    var skip = s.Prop("Works_Dumpster", G(-2.6f, 2.9f), East);
                    var fill = CheckoutWorksKit.FindPart(skip, "Fill"); if (fill) s.Grow(fill, 0, .9f, false);
                    s.Excavator("Works_MiniExcavator", G(2.4f, 2.6f), West, G(2.4f, .2f), G(-2.6f, 2.9f));
                    s.Prop("Prop_SteelBeams", G(-13.2f, 3.6f), East); s.Prop("Prop_GlassCrate", G(-9.4f, 3.6f), East);
                    s.Forklift(G(-15.8f, 2.4f), G(-6.4f, 2.4f), "Prop_BrickPallet");
                    s.Prop("Prop_ScaffoldTower", G(5.0f, -8.0f), West);
                    s.ToolWorker(G(-1.2f, -1.4f), G(-.3f, -1.4f), CheckoutWorksScene.Tool.Weld, 0);
                    s.ToolWorker(G(5.4f, -5.0f), G(4.6f, -5.0f), CheckoutWorksScene.Tool.Trowel, 1);
                    s.Carrier(G(-9.4f, 2.6f), G(-1.6f, -.6f), "Prop_Box", 2);
                    s.Foreman(G(-1.6f, -8.0f), G(-1.6f, -5.2f), G(1.9f, -3.5f), 3);
                    break;
                }
                case "supermercado":
                    // Behind the mercadinho, over lots A2 and B2; trucks come in from lot B3 at the back.
                    Big(snapshot, new Bounds(new Vector3(-5.7f, 0, 10.4f), new Vector3(22.2f, 0, 10.4f)), back: true);
                    break;
                case "hipermercado":
                    // Lots C1 and C2, next to the supermarket; trucks come in from the east street.
                    Big(snapshot, new Bounds(new Vector3(11.4f, 0, 5.6f), new Vector3(11.2f, 0, 19.6f)), back: false);
                    break;
                case "rede":
                {
                    // The chain's sign goes up on the roof from two aerial platforms; painters below.
                    var sign = s.Prop("Works_SignFrame", new Vector3(0, 3.35f, -3.6f), South, 1.3f); s.Grow(sign, 0, .9f, false);
                    var b1 = s.CherryPicker(G(-7.5f, -7.4f), East, new Vector3(-4f, 4.4f, -3.9f));
                    var b2 = s.CherryPicker(G(7.5f, -7.4f), West, new Vector3(4f, 4.4f, -3.9f));
                    s.Rider(b1, new Vector3(-4f, 4.4f, -3.6f), CheckoutWorksScene.Tool.Drill);
                    s.Rider(b2, new Vector3(4f, 4.4f, -3.6f), CheckoutWorksScene.Tool.Weld);
                    s.Prop("Prop_PaintBuckets", G(-1.2f, -7.2f), South); s.Prop("Prop_SitePlate", G(12.6f, -7.6f), South);
                    s.Prop("Prop_Cone", G(-10.6f, -8.1f), South); s.Prop("Prop_Cone", G(10.6f, -8.1f), South);
                    s.ToolWorker(G(.8f, -6.9f), G(.8f, -4.4f), CheckoutWorksScene.Tool.Roller, 1);
                    s.Foreman(G(-2.6f, -7.6f), G(2.6f, -7.6f), new Vector3(0, 3.5f, -3.6f), 3);
                    break;
                }
            }
            // The countdown floats over the works.
            var b = CheckoutWorksKit.Bounds(s.gameObject);
            float top = b.size.sqrMagnitude > 0 ? Mathf.Clamp(b.max.y + 1.4f, 4.2f, 9f) : 5f;
            var centre = b.size.sqrMagnitude > 0 ? b.center : G(cx, 0);
            if (era == "supermercado" || era == "hipermercado") { centre = BigCentre; top = 13f; }
            s.Countdown(new Vector3(centre.x, top, centre.z), "OBRA", "~loja:expansoes");
        }

        Vector3 BigCentre;

        // The tower-crane building site (shared with the old wing expansions): hoardings, cranes, mixer truck,
        // walls rising with the countdown. Its own board is hidden: the works countdown is the pill above.
        void Big(Snapshot snapshot, Bounds walls, bool back)
        {
            if (!bigSite)
            {
                var show = world ? world.GetComponentInChildren<CheckoutStageConstruction>(true) : null;
                var template = show ? show.GetComponent<CheckoutConstructionSite>() : null;
                if (!show) return;
                bigSite = show.gameObject.AddComponent<CheckoutConstructionSite>();
                if (template)
                {
                    bigSite.kit = template.kit; bigSite.galvanized = template.galvanized; bigSite.planks = template.planks; bigSite.concrete = template.concrete;
                    bigSite.hazard = template.hazard; bigSite.navyPaint = template.navyPaint; bigSite.goldTrim = template.goldTrim; bigSite.cable = template.cable;
                    bigSite.redLamp = template.redLamp; bigSite.rebar = template.rebar; bigSite.crew = template.crew; bigSite.boardFont = template.boardFont;
                }
            }
            var obra = snapshot.era.construction;
            Vector3 F(float x, float z) => new Vector3(x, 0, z);
            var min = walls.min; var max = walls.max;
            var plan = new CheckoutConstructionSite.Plan { id = "era-" + obra.eraId, startedAt = obra.startedAt, endsAt = obra.endsAt, skipCost = obra.skipCost };
            plan.groundY = plan.floorY = .13f;
            plan.walls = new Bounds(F(walls.center.x, walls.center.z), F(walls.size.x, walls.size.z));
            plan.wallHeights = new[] { 0f, 3.3f, 3.3f, 3.3f }; plan.scaffold = new[] { false, true, true, false };
            float x0 = min.x - .1f, x1 = max.x + .1f, z0 = min.z - .1f, z1 = max.z + 1.6f;
            if (back)
            {
                float gc = (x0 + x1) * .5f + 4f;
                plan.fences.AddRange(new[] { F(x0, z0), F(x0, z1), F(x0, z1), F(gc - 2.2f, z1), F(gc + 2.2f, z1), F(x1, z1), F(x1, z1), F(x1, z0) });
                plan.gateA = F(gc - 2.2f, z1); plan.gateB = F(gc + 2.2f, z1); plan.truckFrom = F(gc, z1 + 12f); plan.truckPark = F(gc, z1 - 3.4f);
            }
            else
            {
                float gz = (z0 + z1) * .5f;
                x1 = 17.2f;
                plan.fences.AddRange(new[] { F(x0, z0), F(x1, z0), F(x1, z0), F(x1, gz - 2.2f), F(x1, gz + 2.2f), F(x1, z1), F(x1, z1), F(x0, z1) });
                plan.gateA = F(x1, gz - 2.2f); plan.gateB = F(x1, gz + 2.2f); plan.truckFrom = F(x1 + 12f, gz); plan.truckPark = F(x1 - 3.4f, gz);
            }
            plan.site = new Bounds(F((x0 + x1) * .5f, (z0 + z1) * .5f), F(x1 - x0, z1 - z0));
            plan.work = new Bounds(F(walls.center.x, walls.center.z), F(walls.size.x - 1f, walls.size.z - 1f));
            plan.crewArea = new Bounds(walls.center, F(walls.size.x - 2f, walls.size.z - 2f));
            plan.cranesInside = true;
            bigSite.Show(plan);
            BigCentre = walls.center;
            // Hide its own board (the countdown pill is ours) once it is built.
            var site = GameObject.Find("Construction site " + plan.id);
            var board = site ? site.transform.Find("Countdown board") : null;
            if (board) board.gameObject.SetActive(false);
        }
    }
}
