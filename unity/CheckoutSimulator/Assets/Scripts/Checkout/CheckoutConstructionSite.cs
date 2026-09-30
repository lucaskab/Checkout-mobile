using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    // A live building site that stays on the map while a paid expansion is being built (the works take
    // real time in the app). Printed hoardings with a gate close off the ground, the new walls rise with
    // the countdown behind scaffolding, lattice tower cranes lift pallets from the stacks onto the site,
    // a mixer truck backs in through the gate to pour concrete and drives off again, and a crew of the
    // game's own workers (hard hats and hi-vis) carry bricks, weld on the scaffold deck and supervise.
    // The countdown board opens the expansions sheet, where the works can be finished with diamonds.
    // Parts come from the "Construction Kit" built by CheckoutMarketStagesBuilder (textured, baked meshes).
    public class CheckoutConstructionSite : MonoBehaviour
    {
        public class Plan
        {
            public string id;
            public Bounds site;                 // everything inside the hoardings
            public Bounds walls;                // footprint of the building being built
            public float groundY = .15f, floorY = .15f;
            public float[] wallHeights = new float[4];   // rising wall per side (S, E, N, W), 0 = none
            public bool[] scaffold = new bool[4];
            public List<Vector3> fences = new List<Vector3>();   // pairs of points
            public Vector3 gateA, gateB, truckFrom, truckPark;
            public Bounds work;                 // open ground for the stacks and the board
            public Bounds crewArea;             // where the crew carries bricks (inside the new walls)
            public bool cranesInside;
            public double startedAt, endsAt; public int skipCost;
        }

        public Transform kit;
        public Material galvanized, planks, concrete, hazard, navyPaint, goldTrim, cable, redLamp, rebar;
        public Material[] crew = new Material[0];
        public Font boardFont;

        class Crane { public Transform slew, trolley, cable, hook, load, lights; public float pick, drop, reachPick, reachDrop, top, groundPick, groundDrop, offset, cycle; }
        enum Job { Carrier, Welder, Foreman }
        class Worker
        {
            public Transform body, handL, handR, prop; public Animation anim; public string clip; public Job job;
            public Vector3 a, b, target; public int phase; public float clock, wait; public bool released;
        }
        class Wall { public Transform wall; public float full; public Transform[] columns; public Transform[] rebars; }

        readonly List<Crane> cranes = new List<Crane>();
        readonly List<Worker> workers = new List<Worker>();
        readonly List<Wall> walls = new List<Wall>();
        readonly List<Material> owned = new List<Material>();
        GameObject root; TextMesh countdown, countdownShadow, speedUpText; Transform board, progressFill, speedUp;
        ParticleSystem sparks, pour; Vector3[] deckSpots = Array.Empty<Vector3>();
        Transform truck, drum, chute, gateL, gateR; Transform[] truckWheels = Array.Empty<Transform>();
        int truckState; float truckClock, drumSpeed = 40, gateOpen;
        Plan plan; string key;
        CheckoutStageConstruction art;
        Material fallback;

        public bool Active => root;
        public static long Now => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
        float Progress => plan == null || plan.endsAt <= plan.startedAt ? 1 : Mathf.Clamp01((float)((Now - plan.startedAt) / (plan.endsAt - plan.startedAt)));

        public void Show(Plan next)
        {
            if (root && key == next.id && plan != null) { plan.startedAt = next.startedAt; plan.endsAt = next.endsAt; plan.skipCost = next.skipCost; UpdateBoard(true); return; }
            Hide();
            plan = next; key = next.id;
            art = GetComponent<CheckoutStageConstruction>();
            // Kept at the scene root: the map root is turned 180° and everything here is authored in world space.
            root = new GameObject("Construction site " + next.id);
            Build();
            UpdateBoard(true); UpdateWalls();
        }

        public void Hide()
        {
            if (root) Destroy(root);
            root = null; key = null; plan = null; truck = null;
            cranes.Clear(); workers.Clear(); walls.Clear(); deckSpots = Array.Empty<Vector3>();
        }

        void OnDestroy() { Hide(); foreach (var m in owned) if (m) Destroy(m); owned.Clear(); }

        Material gemMaterial;
        Material Gem()
        {
            if (!gemMaterial)
            {
                gemMaterial = new Material(Shader.Find("Standard")); gemMaterial.color = new Color(.35f, .85f, 1f);
                gemMaterial.SetFloat("_Glossiness", .9f); gemMaterial.EnableKeyword("_EMISSION"); gemMaterial.SetColor("_EmissionColor", new Color(.15f, .5f, .7f));
                owned.Add(gemMaterial);
            }
            return gemMaterial;
        }

        Material Fallback() { if (!fallback) { fallback = new Material(Shader.Find("Standard")); fallback.color = new Color(.3f, .35f, .45f); owned.Add(fallback); } return fallback; }
        Material M(Material m) => m ? m : Fallback();

        GameObject Part(Transform parent, string name, Vector3 position, Vector3 scale, Material material, PrimitiveType type = PrimitiveType.Cube)
        {
            var go = GameObject.CreatePrimitive(type);
            go.name = name;
            var collider = go.GetComponent<Collider>(); if (collider) Destroy(collider);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = position; go.transform.localScale = scale;
            var renderer = go.GetComponent<Renderer>();
            renderer.sharedMaterial = M(material);
            renderer.shadowCastingMode = scale.y > 1.5f || scale.x > 2f || scale.z > 2f ? UnityEngine.Rendering.ShadowCastingMode.On : UnityEngine.Rendering.ShadowCastingMode.Off;
            return go;
        }

        Transform Group(Transform parent, string name, Vector3 position, Quaternion? rotation = null)
        {
            var t = new GameObject(name).transform; t.SetParent(parent, false); t.position = position; t.rotation = rotation ?? Quaternion.identity; return t;
        }

        Transform Kit(string name, Vector3 position, Quaternion rotation, Transform parent)
        {
            var template = kit ? kit.Find(name) : null;
            if (!template) return Group(parent, name + " (missing)", position, rotation);
            var copy = Instantiate(template.gameObject, parent).transform;
            copy.name = name; copy.SetPositionAndRotation(position, rotation);
            copy.gameObject.SetActive(true);
            return copy;
        }

        Vector3 G(float x, float z) => new Vector3(x, plan.groundY, z);

        void Build()
        {
            var t = root.transform;
            var site = plan.site; var min = site.min; var max = site.max;

            for (int i = 0; i + 1 < plan.fences.Count; i += 2) Hoarding(t, G(plan.fences[i].x, plan.fences[i].z), G(plan.fences[i + 1].x, plan.fences[i + 1].z));
            Gate(t);
            RisingWalls(t);

            // Cranes on the far corners, or inside the lot when it sits at the edge of the map.
            float tall = plan.wallHeights.Max() + plan.floorY - plan.groundY;
            var work = plan.work;
            var stackA = plan.cranesInside ? G(max.x - 3.4f, min.z + 1.3f) : G(max.x + 1.2f, max.z + 3.4f);
            var stackB = plan.cranesInside ? G(min.x + 3.8f, min.z + 1.3f) : G(Mathf.Lerp(min.x, max.x, .3f), max.z + 3.2f);
            var craneA = plan.cranesInside ? G(max.x - 2f, max.z - 2f) : G(max.x + 2.4f, max.z + 2f);
            var craneB = plan.cranesInside ? G(min.x + 2f, max.z - 2f) : G(min.x + 1.6f, max.z + 2f);
            var dropA = G(plan.walls.max.x - .6f, (plan.walls.min.z + plan.walls.max.z) * .5f);
            var dropB = G(Mathf.Lerp(plan.walls.min.x, plan.walls.max.x, .4f), plan.walls.max.z - .8f);
            Kit("Material stack", stackA, Quaternion.identity, t);
            cranes.Add(TowerCrane(t, craneA, tall + 7.5f, dropA, stackA + new Vector3(.6f, 0, .5f), 0));
            if (site.size.x > 9f) { Kit("Material stack", stackB, Quaternion.Euler(0, 90, 0), t); cranes.Add(TowerCrane(t, craneB, tall + 6f, dropB, stackB + new Vector3(.5f, 0, .6f), 7.3f)); }

            MixerTruck(t);
            Crew(t);
            Dust(t);
            sparks = Sparks(t);

            // Countdown board over the works.
            board = Group(t, "Countdown board", new Vector3(work.center.x, plan.floorY + plan.wallHeights.Max() + 3.6f, Mathf.Lerp(site.center.z, work.center.z, .5f)));
            Part(board, "Board", new Vector3(0, 0, .06f), new Vector3(5.8f, 1.6f, .1f), navyPaint);
            Part(board, "Trim", new Vector3(0, -.86f, .05f), new Vector3(6f, .12f, .12f), goldTrim);
            Part(board, "Trim", new Vector3(0, .86f, .05f), new Vector3(6f, .12f, .12f), goldTrim);
            foreach (float x in new[] { -2.95f, 2.95f }) Part(board, "Trim", new Vector3(x, 0, .05f), new Vector3(.12f, 1.8f, .12f), goldTrim);
            Part(board, "Bar back", new Vector3(0, -.5f, .01f), new Vector3(4.8f, .18f, .04f), galvanized);
            progressFill = Part(board, "Bar fill", new Vector3(0, -.5f, -.02f), new Vector3(4.8f, .18f, .04f), goldTrim).transform;
            countdown = Text(board, new Vector3(0, .15f, -.03f), new Color(1f, .9f, .45f));
            countdownShadow = Text(board, new Vector3(.02f, .13f, 0), new Color(.05f, .08f, .16f, .9f));
            var click = board.gameObject.AddComponent<BoxCollider>(); click.size = new Vector3(6.2f, 2f, .4f);
            board.gameObject.AddComponent<CheckoutTarget>().panel = "expansions";
            // "Acelerar" plate under the board: finishes the works now for diamonds.
            speedUp = new GameObject("Speed up").transform; speedUp.SetParent(board, false); speedUp.localPosition = new Vector3(0, -1.45f, 0);
            Part(speedUp, "Plate", new Vector3(0, 0, .05f), new Vector3(3.9f, .8f, .12f), goldTrim);
            Part(speedUp, "Plate edge", new Vector3(0, 0, .09f), new Vector3(4.05f, .95f, .08f), navyPaint);
            var gem = Part(speedUp, "Diamond", new Vector3(1.35f, 0, -.05f), new Vector3(.36f, .36f, .12f), Gem());
            gem.transform.localRotation = Quaternion.Euler(0, 0, 45);
            speedUpText = Text(speedUp, new Vector3(-.35f, 0, -.04f), new Color(.08f, .12f, .24f));
            speedUpText.characterSize = .06f;
            var plateClick = speedUp.gameObject.AddComponent<BoxCollider>(); plateClick.size = new Vector3(4.1f, 1f, .5f);
            speedUp.gameObject.AddComponent<CheckoutTarget>().panel = "finishWorks";

            // Static parts batched into a few draw calls.
            foreach (Transform child in t)
                if (child.name == "Hoarding" || child.name == "Scaffolding" || child.name == "Material stack") StaticBatchingUtility.Combine(child.gameObject);
        }

        TextMesh Text(Transform parent, Vector3 position, Color color)
        {
            var go = new GameObject("Countdown"); go.transform.SetParent(parent, false); go.transform.localPosition = position;
            var text = go.AddComponent<TextMesh>();
            var font = boardFont ? boardFont : art ? art.titleFont : null;
            text.font = font; text.fontSize = 64; text.characterSize = .075f; text.anchor = TextAnchor.MiddleCenter; text.alignment = TextAlignment.Center;
            text.fontStyle = FontStyle.Bold; text.color = color;
            go.GetComponent<MeshRenderer>().sharedMaterial = art && art.titleMaterial ? art.titleMaterial : font ? font.material : null;
            return text;
        }

        // ---------------------------------------------------------------- hoardings and gate
        void Hoarding(Transform parent, Vector3 from, Vector3 to)
        {
            float length = Vector3.Distance(from, to); if (length < .5f) return;
            var dir = (to - from) / length;
            var g = Group(parent, "Hoarding", from, Quaternion.LookRotation(dir));
            int panels = Mathf.Max(1, Mathf.RoundToInt(length / 2.4f));
            float w = length / panels;
            for (int i = 0; i < panels; i++)
            {
                var p = Kit("Hoarding panel", from + dir * (w * (i + .5f)), g.rotation, g);
                p.localScale = new Vector3(1, 1, w / 2.4f);
            }
            Part(g, "End post", new Vector3(0, 1.05f, length), new Vector3(.08f, 2.1f, .08f), galvanized);
        }

        void Gate(Transform parent)
        {
            if ((plan.gateB - plan.gateA).sqrMagnitude < .5f) return;
            var a = G(plan.gateA.x, plan.gateA.z); var b = G(plan.gateB.x, plan.gateB.z);
            gateL = Kit("Gate leaf", a, Quaternion.LookRotation(b - a), parent);
            gateR = Kit("Gate leaf", b, Quaternion.LookRotation(a - b), parent);
            float width = Vector3.Distance(a, b);
            gateL.localScale = gateR.localScale = new Vector3(1, 1, width * .5f / 1.8f);
            foreach (var p in new[] { a, b }) Part(parent, "Gate post", p + Vector3.up * 1.15f, new Vector3(.14f, 2.3f, .14f), goldTrim);
        }

        // ---------------------------------------------------------------- rising walls and scaffolding
        void RisingWalls(Transform parent)
        {
            var w = plan.walls; float y = plan.groundY;
            var c = new[] { G(w.min.x, w.min.z), G(w.max.x, w.min.z), G(w.max.x, w.max.z), G(w.min.x, w.max.z) };
            var spots = new List<Vector3>();
            for (int side = 0; side < 4; side++)
            {
                float full = plan.wallHeights[side] + plan.floorY - y;
                var a = c[side]; var b = c[(side + 1) % 4];
                float length = Vector3.Distance(a, b);
                if (plan.wallHeights[side] > 0 && length > .5f)
                {
                    var dir = (b - a) / length;
                    var g = Group(parent, "Rising wall", a, Quaternion.LookRotation(dir));
                    var wall = Part(g, "Blockwork", new Vector3(0, 0, length * .5f), new Vector3(.3f, 1, length), concrete).transform;
                    int n = Mathf.Max(2, Mathf.RoundToInt(length / 3f) + 1);
                    var cols = new Transform[n]; var bars = new Transform[n];
                    for (int i = 0; i < n; i++)
                    {
                        float z = length * i / (n - 1);
                        cols[i] = Part(g, "Column", new Vector3(0, 0, z), new Vector3(.5f, 1, .5f), concrete).transform;
                        var bar = Group(g, "Rebar", g.TransformPoint(new Vector3(0, 0, z)), g.rotation);
                        foreach (var o in new[] { new Vector3(-.14f, 0, -.14f), new Vector3(.14f, 0, -.14f), new Vector3(-.14f, 0, .14f), new Vector3(.14f, 0, .14f) })
                            Part(bar, "Bar", o + Vector3.up * .45f, new Vector3(.035f, .9f, .035f), rebar);
                        bars[i] = bar;
                    }
                    walls.Add(new Wall { wall = wall, full = full, columns = cols, rebars = bars });
                }
                if (plan.scaffold[side] && length > .5f) Scaffold(parent, a, b, Mathf.Max(full, 3f) + .8f, spots);
            }
            deckSpots = spots.ToArray();
        }

        void UpdateWalls()
        {
            float p = Progress;
            foreach (var w in walls)
            {
                float h = w.full * Mathf.Lerp(.12f, .9f, p), ch = w.full * Mathf.Min(1, .3f + p * .9f);
                if (w.wall) { w.wall.localScale = new Vector3(.3f, h, w.wall.localScale.z); w.wall.localPosition = new Vector3(0, h * .5f, w.wall.localPosition.z); }
                for (int i = 0; i < w.columns.Length; i++)
                {
                    var col = w.columns[i]; if (!col) continue;
                    col.localScale = new Vector3(.5f, ch, .5f); col.localPosition = new Vector3(0, ch * .5f, col.localPosition.z);
                    if (w.rebars[i]) { var pos = w.rebars[i].localPosition; w.rebars[i].localPosition = new Vector3(pos.x, ch, pos.z); w.rebars[i].gameObject.SetActive(p < .97f); }
                }
            }
        }

        void Scaffold(Transform parent, Vector3 from, Vector3 to, float height, List<Vector3> spots)
        {
            float length = Vector3.Distance(from, to);
            var dir = (to - from) / length; var outward = new Vector3(dir.z, 0, -dir.x);
            var g = Group(parent, "Scaffolding", from + outward * .45f, Quaternion.LookRotation(dir));
            // Local +x points away from the wall. Decks every 2.6 m so a worker (2.4 m) fits under the next.
            int bays = Mathf.Max(1, Mathf.RoundToInt(length / 2.4f));
            for (int i = 0; i <= bays; i++)
            {
                float z = length * i / bays;
                foreach (float x in new[] { 0f, 1.1f }) Part(g, "Standard", new Vector3(x, height * .5f, z), new Vector3(.07f, height, .07f), galvanized);
                Part(g, "Base plate", new Vector3(.55f, .02f, z), new Vector3(1.4f, .04f, .2f), planks);
            }
            var decks = new List<float>();
            for (float y = 2.6f; y < height - .6f; y += 2.6f) decks.Add(y);
            if (decks.Count == 0) decks.Add(Mathf.Max(1.6f, height - 1.2f));
            for (int k = 0; k < decks.Count; k++)
            {
                float y = decks[k];
                Part(g, "Deck", new Vector3(.55f, y, length * .5f), new Vector3(1.05f, .06f, length), planks);
                Part(g, "Toe board", new Vector3(1.12f, y + .1f, length * .5f), new Vector3(.03f, .18f, length), goldTrim);
                Part(g, "Guard rail", new Vector3(1.12f, y + 1.0f, length * .5f), new Vector3(.05f, .05f, length), galvanized);
                Part(g, "Mid rail", new Vector3(1.12f, y + .55f, length * .5f), new Vector3(.04f, .04f, length), galvanized);
                Part(g, "Ledger", new Vector3(0, y - .05f, length * .5f), new Vector3(.05f, .05f, length), galvanized);
                // Only the top deck has head room above it for the crew.
                if (k == decks.Count - 1)
                    for (int i = 0; i < bays; i++) spots.Add(g.TransformPoint(new Vector3(.55f, y + .03f, length * (i + .5f) / bays)));
            }
            for (int i = 0; i < bays; i += 2)
            {
                float z = length * (i + .5f) / bays, span = length / bays;
                var brace = Part(g, "Brace", new Vector3(1.14f, height * .5f, z), new Vector3(.04f, Mathf.Sqrt(height * height + span * span), .04f), galvanized);
                brace.transform.localRotation = Quaternion.Euler(Mathf.Atan2(span, height) * Mathf.Rad2Deg, 0, 0);
            }
            // Ladder on the first bay.
            Part(g, "Ladder", new Vector3(.9f, decks[decks.Count - 1] * .5f, .6f), new Vector3(.05f, decks[decks.Count - 1] + .9f, .45f), goldTrim).transform.localRotation = Quaternion.Euler(-12, 0, 0);
            if (art && art.netMaterial) Part(g, "Safety net", new Vector3(1.16f, height * .55f, length * .5f), new Vector3(.02f, height * .75f, length), art.netMaterial);
        }

        // ---------------------------------------------------------------- cranes
        Crane TowerCrane(Transform parent, Vector3 at, float mast, Vector3 drop, Vector3 stack, float offset)
        {
            var g = Group(parent, "Tower crane", at);
            Kit("Crane base", at, Quaternion.identity, g);
            int sections = Mathf.Max(3, Mathf.CeilToInt((mast - .8f) / 2f));
            for (int i = 0; i < sections; i++) Kit("Mast section", at + Vector3.up * (.74f + i * 2f), Quaternion.identity, g);
            float topY = at.y + .74f + sections * 2f;
            var slew = Group(g, "Slew", new Vector3(at.x, topY, at.z));
            Kit("Crane top", slew.position, Quaternion.identity, slew);
            float reachPick = Mathf.Clamp(Horizontal(stack - at), 3f, 12.4f), reachDrop = Mathf.Clamp(Horizontal(drop - at), 3f, 12.4f);
            var trolley = Kit("Crane trolley", slew.TransformPoint(new Vector3(0, .3f, reachDrop)), Quaternion.identity, slew);
            var cableT = Part(trolley, "Cable", Vector3.zero, new Vector3(.03f, 1, .03f), cable).transform;
            var hook = Kit("Crane hook", trolley.position, Quaternion.identity, trolley);
            var load = Kit("Crane load", hook.position + Vector3.down * .72f, Quaternion.identity, hook);
            var c = new Crane
            {
                slew = slew, trolley = trolley, cable = cableT, hook = hook, load = load, lights = slew.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "Anim lights"),
                pick = Heading(stack - at), drop = Heading(drop - at), reachPick = reachPick, reachDrop = reachDrop,
                top = topY + .3f, groundPick = stack.y + .95f, groundDrop = drop.y + .2f, offset = offset, cycle = 22f
            };
            if (Mathf.Abs(Mathf.DeltaAngle(c.pick, c.drop)) < 35) c.drop = c.pick + 70;
            return c;
        }

        static float Horizontal(Vector3 v) { v.y = 0; return v.magnitude; }
        static float Heading(Vector3 v) => Mathf.Atan2(v.x, v.z) * Mathf.Rad2Deg;

        void AnimateCrane(Crane c, float time)
        {
            if (!c.slew) return;
            float p = Mathf.Repeat(time + c.offset, c.cycle) / c.cycle;
            float Phase(float a, float b) => Mathf.SmoothStep(0, 1, Mathf.InverseLerp(a, b, p));
            float carry = 3.2f, low = c.top - c.groundPick - 1.2f, lowDrop = c.top - c.groundDrop - 1.2f;
            float heading, reach, drop; bool loaded;
            if (p < .12f) { heading = c.pick; reach = c.reachPick; drop = Mathf.Lerp(carry, low, Phase(0, .12f)); loaded = false; }
            else if (p < .18f) { heading = c.pick; reach = c.reachPick; drop = low; loaded = true; }
            else if (p < .3f) { heading = c.pick; reach = c.reachPick; drop = Mathf.Lerp(low, carry, Phase(.18f, .3f)); loaded = true; }
            else if (p < .52f) { heading = Mathf.LerpAngle(c.pick, c.drop, Phase(.3f, .52f)); reach = Mathf.Lerp(c.reachPick, c.reachDrop, Phase(.3f, .52f)); drop = carry; loaded = true; }
            else if (p < .64f) { heading = c.drop; reach = c.reachDrop; drop = Mathf.Lerp(carry, lowDrop, Phase(.52f, .64f)); loaded = true; }
            else if (p < .7f) { heading = c.drop; reach = c.reachDrop; drop = lowDrop; loaded = false; }
            else if (p < .8f) { heading = c.drop; reach = c.reachDrop; drop = Mathf.Lerp(lowDrop, carry, Phase(.7f, .8f)); loaded = false; }
            else { heading = Mathf.LerpAngle(c.drop, c.pick, Phase(.8f, 1f)); reach = Mathf.Lerp(c.reachDrop, c.reachPick, Phase(.8f, 1f)); drop = carry; loaded = false; }
            c.slew.rotation = Quaternion.Euler(0, heading, 0);
            c.trolley.localPosition = new Vector3(0, .3f, reach);
            drop = Mathf.Max(1f, drop);
            c.cable.localScale = new Vector3(.03f, drop, .03f);
            c.cable.localPosition = new Vector3(0, -.2f - drop * .5f, 0);
            c.hook.localPosition = new Vector3(0, -.2f - drop, 0);
            c.hook.localRotation = Quaternion.Euler(Mathf.Sin(time * 1.7f + c.offset) * (loaded ? 3f : 1.5f), 0, Mathf.Cos(time * 1.3f) * 2f);
            if (c.load.gameObject.activeSelf != loaded) c.load.gameObject.SetActive(loaded);
            if (c.lights) c.lights.gameObject.SetActive(Mathf.Repeat(time + c.offset, 1.2f) < .6f);
        }

        // ---------------------------------------------------------------- mixer truck
        void MixerTruck(Transform parent)
        {
            if ((plan.truckPark - plan.truckFrom).sqrMagnitude < 1) return;
            truck = Kit("Mixer truck", G(plan.truckFrom.x, plan.truckFrom.z), Quaternion.identity, parent);
            drum = truck.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "Anim drum");
            chute = truck.GetComponentsInChildren<Transform>(true).FirstOrDefault(x => x.name == "Anim chute");
            truckWheels = truck.GetComponentsInChildren<Transform>(true).Where(x => x.name == "Anim wheel").ToArray();
            pour = Pour(chute ? chute : truck);
            truck.gameObject.SetActive(false);
            truckState = 0; truckClock = 2f;
        }

        void AnimateTruck(float dt)
        {
            if (!truck) return;
            var gate = G((plan.gateA.x + plan.gateB.x) * .5f, (plan.gateA.z + plan.gateB.z) * .5f);
            var from = G(plan.truckFrom.x, plan.truckFrom.z); var park = G(plan.truckPark.x, plan.truckPark.z);
            bool nearGate = truck.gameObject.activeSelf && Horizontal(truck.position - gate) < 7.5f;
            // A truck that pours over the hoarding parks outside; otherwise it backs in through the gate.
            bool parkOutside = Vector3.Dot(park - gate, from - gate) > 0;
            gateOpen = Mathf.MoveTowards(gateOpen, nearGate ? 1 : 0, dt * .8f);
            if (gateL) gateL.localRotation = Quaternion.LookRotation(G(plan.gateB.x, plan.gateB.z) - G(plan.gateA.x, plan.gateA.z)) * Quaternion.Euler(0, -100 * Mathf.SmoothStep(0, 1, gateOpen), 0);
            if (gateR) gateR.localRotation = Quaternion.LookRotation(G(plan.gateA.x, plan.gateA.z) - G(plan.gateB.x, plan.gateB.z)) * Quaternion.Euler(0, 100 * Mathf.SmoothStep(0, 1, gateOpen), 0);
            if (drum) drum.Rotate(0, 0, drumSpeed * dt, Space.Self);
            truckClock -= dt;
            switch (truckState)
            {
                case 0: // away
                    if (truckClock > 0) return;
                    truck.position = from; truck.rotation = Quaternion.LookRotation((from - gate).normalized);
                    truck.gameObject.SetActive(true); truckState = 1; drumSpeed = 60;
                    break;
                case 1: // backing in through the gate
                    if (Drive(!parkOutside && Horizontal(truck.position - gate) > .3f && Vector3.Dot(truck.position - gate, from - gate) > 0 ? gate : park, dt, false, 2.4f) && Horizontal(truck.position - park) < .05f)
                    { truckState = 2; truckClock = 8f; if (pour) pour.Play(); }
                    break;
                case 2: // pouring
                    drumSpeed = Mathf.MoveTowards(drumSpeed, -160, dt * 120);
                    if (chute) chute.localRotation = Quaternion.Euler(-32, Mathf.Sin(Time.time * .8f) * 25, 0);
                    if (truckClock <= 0) { truckState = 3; if (pour) pour.Stop(); }
                    break;
                case 3: // driving out
                    drumSpeed = Mathf.MoveTowards(drumSpeed, 40, dt * 120);
                    if (chute) chute.localRotation = Quaternion.RotateTowards(chute.localRotation, Quaternion.identity, dt * 40);
                    bool pastGate = parkOutside || Vector3.Dot(truck.position - gate, from - gate) > -.1f;
                    if (Drive(pastGate ? from : gate, dt, true, 3.2f) && pastGate && Horizontal(truck.position - from) < .05f)
                    { truck.gameObject.SetActive(false); truckState = 0; truckClock = UnityEngine.Random.Range(9f, 16f); }
                    break;
            }
        }

        // Moves the truck towards `target`; it faces away from the site the whole time (reverses in, drives out).
        bool Drive(Vector3 target, float dt, bool forward, float speed)
        {
            var delta = target - truck.position; delta.y = 0;
            if (delta.magnitude < .05f) { truck.position = new Vector3(target.x, truck.position.y, target.z); return true; }
            var facing = forward ? delta.normalized : -delta.normalized;
            truck.rotation = Quaternion.RotateTowards(truck.rotation, Quaternion.LookRotation(facing), 60 * dt);
            float step = Mathf.Min(delta.magnitude, speed * dt);
            truck.position += delta.normalized * step;
            foreach (var w in truckWheels) if (w) w.Rotate(step / .5f * Mathf.Rad2Deg * (forward ? 1 : -1), 0, 0, Space.Self);
            return false;
        }

        ParticleSystem Pour(Transform at)
        {
            var go = new GameObject("Concrete pour"); go.transform.SetParent(at, false); go.transform.localPosition = new Vector3(0, -.05f, -1.4f);
            go.transform.localRotation = Quaternion.Euler(90, 0, 0);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.loop = true; main.playOnAwake = false; main.startLifetime = .6f; main.startSpeed = 1.2f;
            main.startSize = new ParticleSystem.MinMaxCurve(.18f, .3f); main.startColor = new Color(.62f, .6f, .56f, 1); main.gravityModifier = 1.4f;
            main.maxParticles = 150; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Cone; shape.angle = 6; shape.radius = .08f;
            var emission = ps.emission; emission.rateOverTime = 70;
            go.GetComponent<ParticleSystemRenderer>().sharedMaterial = art ? art.dustMaterial : null;
            return ps;
        }

        // ---------------------------------------------------------------- crew
        void Crew(Transform parent)
        {
            var template = FindAnyObjectByType<MarketDay.MarketDeliveryWorker>(FindObjectsInactive.Include);
            if (!template) return;
            var rnd = new System.Random(key.GetHashCode());
            var work = plan.crewArea.size.sqrMagnitude > .1f ? plan.crewArea : plan.work;
            Vector3 Ground(Bounds b) => G(Mathf.Lerp(b.min.x + .6f, b.max.x - .6f, (float)rnd.NextDouble()), Mathf.Lerp(b.min.z + .6f, b.max.z - .6f, (float)rnd.NextDouble()));
            var stack = G(Mathf.Lerp(work.min.x, work.max.x, .5f), work.max.z - 1.2f);
            Kit("Material stack", stack + new Vector3(-.6f, 0, .3f), Quaternion.Euler(0, 90, 0), parent);
            for (int i = 0; i < 3; i++)
                Spawn(template, parent, Job.Carrier, stack + new Vector3(.9f - i * .5f, 0, -1.3f), Ground(work), i);
            for (int i = 0; i < 2 && deckSpots.Length > 1; i++)
                Spawn(template, parent, Job.Welder, deckSpots[rnd.Next(deckSpots.Length)], deckSpots[rnd.Next(deckSpots.Length)], i + 1);
            var gate = (plan.gateA + plan.gateB) * .5f;
            var inside = (plan.truckPark - gate).normalized;
            Spawn(template, parent, Job.Foreman, G(gate.x, gate.z) + inside * 2.2f + new Vector3(inside.z, 0, -inside.x) * 1.6f, G(gate.x, gate.z) + inside * 3.2f, 0);
        }

        void Spawn(MarketDay.MarketDeliveryWorker template, Transform parent, Job job, Vector3 a, Vector3 b, int variant)
        {
            var holder = new GameObject("Crew holder"); holder.SetActive(false);
            var clone = Instantiate(template.gameObject, holder.transform);
            DestroyImmediate(clone.GetComponent<MarketDay.MarketDeliveryWorker>());
            foreach (Transform child in clone.transform.Cast<Transform>().ToArray()) if (child.name != "Visual") DestroyImmediate(child.gameObject);
            clone.name = "Construction worker " + job;
            foreach (var r in clone.GetComponentsInChildren<Renderer>(true))
            {
                r.enabled = true;
                if (r is SkinnedMeshRenderer skin && crew != null && crew.Length > 0 && crew[variant % crew.Length]) skin.sharedMaterial = crew[variant % crew.Length];
            }
            clone.transform.SetParent(parent, false);
            Destroy(holder);
            clone.transform.SetPositionAndRotation(a, Quaternion.LookRotation(Horizontal(b - a) > .1f ? new Vector3(b.x - a.x, 0, b.z - a.z) : Vector3.forward));
            var bones = clone.GetComponentsInChildren<Transform>(true);
            var head = bones.FirstOrDefault(x => x.name == "Head");
            var worker = new Worker
            {
                body = clone.transform, job = job, a = a, b = b, target = job == Job.Carrier ? a : b,
                anim = clone.GetComponentInChildren<Animation>(true),
                handL = bones.FirstOrDefault(x => x.name == "Hand_L"), handR = bones.FirstOrDefault(x => x.name == "Hand_R"),
                wait = variant * .7f
            };
            if (head && kit && kit.Find("Hard hat"))
            {
                var hat = Kit("Hard hat", Vector3.zero, clone.transform.rotation, head);
                hat.SetParent(null, false);
                hat.localScale = Vector3.one * .56f;
                hat.SetPositionAndRotation(clone.transform.position + Vector3.up * 2.13f + clone.transform.forward * .02f, clone.transform.rotation);
                hat.SetParent(head, true);
            }
            if (job == Job.Carrier)
            {
                worker.prop = Kit("Brick bundle", clone.transform.position, clone.transform.rotation, clone.transform);
                worker.prop.gameObject.SetActive(false);
            }
            clone.SetActive(true);
            Play(worker, "Idle");
            workers.Add(worker);
        }

        void Play(Worker w, string clip)
        {
            if (!w.anim || w.clip == clip || !w.anim[clip]) return;
            w.clip = clip; w.anim[clip].time = 0; w.anim.CrossFade(clip, .15f);
        }

        float Length(Worker w, string clip) => w.anim && w.anim[clip] ? w.anim[clip].length : 1.5f;

        bool Walk(Worker w, Vector3 target, float dt, bool loaded)
        {
            var delta = target - w.body.position; delta.y = 0;
            if (delta.magnitude < .05f) return true;
            w.body.rotation = Quaternion.RotateTowards(w.body.rotation, Quaternion.LookRotation(delta), dt * 260);
            if (Vector3.Angle(w.body.forward, delta) > 35) { Play(w, loaded ? "CarryIdle" : "Idle"); return false; }
            Play(w, loaded ? "CarryWalking" : "Walking");
            var step = Vector3.MoveTowards(w.body.position, new Vector3(target.x, w.body.position.y, target.z), dt * (loaded ? 1.05f : 1.25f));
            w.body.position = step;
            return false;
        }

        void Face(Worker w, Vector3 point, float dt)
        {
            var d = point - w.body.position; d.y = 0;
            if (d.sqrMagnitude > .001f) w.body.rotation = Quaternion.RotateTowards(w.body.rotation, Quaternion.LookRotation(d), dt * 200);
        }

        void AnimateCrew(float dt)
        {
            var rnd = UnityEngine.Random.value;
            foreach (var w in workers)
            {
                if (!w.body) continue;
                if (w.wait > 0) { w.wait -= dt; Play(w, w.prop && w.prop.gameObject.activeSelf ? "CarryIdle" : "Idle"); continue; }
                w.clock += dt;
                switch (w.job)
                {
                    case Job.Carrier:
                        if (w.phase == 0 && Walk(w, w.a, dt, false)) { w.phase = 1; w.clock = 0; w.released = false; Play(w, "Pickup"); }
                        else if (w.phase == 1)
                        {
                            Face(w, w.a + (w.b - w.a).normalized * -1f, dt);
                            if (w.clock > Length(w, "Pickup") * .55f && w.prop) w.prop.gameObject.SetActive(true);
                            if (w.clock > Length(w, "Pickup")) { w.phase = 2; w.clock = 0; }
                        }
                        else if (w.phase == 2 && Walk(w, w.b, dt, true)) { w.phase = 3; w.clock = 0; Play(w, "PutDown"); }
                        else if (w.phase == 3)
                        {
                            if (w.clock > Length(w, "PutDown") * .65f && w.prop) w.prop.gameObject.SetActive(false);
                            if (w.clock > Length(w, "PutDown"))
                            {
                                w.phase = 0; w.clock = 0;
                                var wk = plan.crewArea.size.sqrMagnitude > .1f ? plan.crewArea : plan.work;
                                w.b = G(Mathf.Lerp(wk.min.x + .6f, wk.max.x - .6f, UnityEngine.Random.value), Mathf.Lerp(wk.min.z + .6f, wk.max.z - 2f, UnityEngine.Random.value));
                            }
                        }
                        break;
                    case Job.Welder:
                        if (w.phase == 0 && Walk(w, w.target, dt, false)) { w.phase = 1; w.clock = 0; Play(w, "Pickup"); }
                        else if (w.phase == 1)
                        {
                            // Crouched at the wall: sparks fly from the torch.
                            if (sparks && Mathf.Repeat(w.clock, .45f) < dt && w.handR)
                            { sparks.transform.position = w.handR.position; sparks.Emit(UnityEngine.Random.Range(10, 20)); }
                            if (w.clock > Length(w, "Pickup") * 1.6f) { w.phase = 2; w.clock = 0; Play(w, "Idle"); }
                        }
                        else if (w.phase == 2 && w.clock > 1.2f + rnd)
                        {
                            w.phase = 0; w.clock = 0;
                            var next = deckSpots.Length > 0 ? deckSpots[UnityEngine.Random.Range(0, deckSpots.Length)] : w.a;
                            // Stay on the same scaffold run (same deck height).
                            w.target = Mathf.Abs(next.y - w.body.position.y) < .2f ? next : w.a;
                        }
                        break;
                    case Job.Foreman:
                        if (truck && truck.gameObject.activeSelf) Face(w, truck.position, dt); else Face(w, w.b, dt);
                        if (w.phase == 0 && w.clock > 5f) { w.phase = 1; w.clock = 0; }
                        if (w.phase == 1 && Walk(w, w.clock < 3f ? w.b : w.a, dt, false) && w.clock > 3.5f) { w.phase = 0; w.clock = 0; Play(w, "Idle"); }
                        if (w.phase == 0) Play(w, "Idle");
                        break;
                }
            }
        }

        void LateUpdate()
        {
            foreach (var w in workers)
                if (w.prop && w.prop.gameObject.activeSelf && w.handL && w.handR)
                {
                    w.prop.position = (w.handL.position + w.handR.position) * .5f + Vector3.down * .35f + w.body.forward * .1f;
                    w.prop.rotation = w.body.rotation;
                }
        }

        // ---------------------------------------------------------------- effects
        void Dust(Transform parent)
        {
            var site = plan.site;
            var go = new GameObject("Site dust"); go.transform.SetParent(parent, false);
            go.transform.position = new Vector3(plan.work.center.x, plan.groundY + .1f, plan.work.center.z);
            go.transform.rotation = Quaternion.Euler(-90, 0, 0);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.loop = true; main.startLifetime = new ParticleSystem.MinMaxCurve(2f, 3.5f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.2f, .7f); main.startSize = new ParticleSystem.MinMaxCurve(1.2f, 2.4f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(.9f, .84f, .74f, .3f), new Color(.8f, .74f, .66f, .2f));
            main.gravityModifier = -.02f; main.maxParticles = 50; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Box; shape.scale = new Vector3(plan.work.size.x, plan.work.size.z, .2f);
            var emission = ps.emission; emission.rateOverTime = 5;
            var color = ps.colorOverLifetime; color.enabled = true;
            var fade = new Gradient(); fade.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) }, new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, .25f), new GradientAlphaKey(0, 1) });
            color.color = fade;
            go.GetComponent<ParticleSystemRenderer>().sharedMaterial = art ? art.dustMaterial : null;
            ps.Play();
        }

        ParticleSystem Sparks(Transform parent)
        {
            var go = new GameObject("Welding sparks"); go.transform.SetParent(parent, false);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.loop = false; main.playOnAwake = false; main.startLifetime = new ParticleSystem.MinMaxCurve(.3f, .7f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(1.5f, 3.5f); main.startSize = new ParticleSystem.MinMaxCurve(.05f, .1f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, .95f, .6f), new Color(1f, .6f, .15f));
            main.gravityModifier = 1.2f; main.maxParticles = 120; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Sphere; shape.radius = .05f;
            var emission = ps.emission; emission.rateOverTime = 0;
            var renderer = go.GetComponent<ParticleSystemRenderer>();
            renderer.sharedMaterial = art && art.sparkMaterial ? art.sparkMaterial : null;
            renderer.renderMode = ParticleSystemRenderMode.Stretch; renderer.velocityScale = .06f; renderer.lengthScale = 1;
            return ps;
        }

        void Update()
        {
            if (!root) return;
            float dt = Time.deltaTime, time = Time.time;
            foreach (var c in cranes) AnimateCrane(c, time);
            AnimateTruck(dt);
            AnimateCrew(dt);
            if (Time.frameCount % 30 == 0) UpdateWalls();
            UpdateBoard(false);
        }

        void UpdateBoard(bool force)
        {
            if (!board || !countdown) return;
            var camera = Camera.main;
            if (camera) board.rotation = camera.transform.rotation;
            if (!force && Time.frameCount % 15 != 0) return;
            double remaining = plan.endsAt - Now;
            string label = remaining > 0 ? "EM OBRA  " + Countdown(remaining) : "FINALIZANDO...";
            countdown.text = label; countdownShadow.text = label;
            if (speedUp)
            {
                speedUp.gameObject.SetActive(remaining > 0);
                int cost = remaining <= 0 ? 0 : Mathf.Max(1, Mathf.CeilToInt((float)(remaining / 600000.0)));
                if (speedUpText) speedUpText.text = "ACELERAR  " + cost;
            }
            float progress = Progress;
            if (progressFill)
            {
                progressFill.localScale = new Vector3(Mathf.Max(.001f, 4.8f * progress), .18f, .04f);
                progressFill.localPosition = new Vector3(-2.4f + 2.4f * progress, -.5f, -.02f);
            }
        }

        public static string Countdown(double ms)
        {
            long total = (long)Math.Ceiling(Math.Max(0, ms) / 1000);
            long d = total / 86400, h = total % 86400 / 3600, m = total % 3600 / 60, s = total % 60;
            if (d > 0) return $"{d}d {h:00}h";
            if (h > 0) return $"{h}:{m:00}:{s:00}";
            return $"{m}:{s:00}";
        }
    }
}
