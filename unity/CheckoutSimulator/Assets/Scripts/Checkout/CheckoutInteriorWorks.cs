using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    // A shelf, sector counter or checkout the player paid for and the builders are still putting up
    // (src/services/interior-construction.ts). The piece stands where it will be, hidden behind low
    // hoardings with scaffolding, a material stack and two builders at work; a board over it counts down and
    // offers to finish the works now for diamonds. When the works end the piece pops into view.
    public class CheckoutInteriorWorks : MonoBehaviour
    {
        class Worker
        {
            public Transform body, handL, handR, prop; public Animation anim; public string clip;
            public bool carrier; public Vector3 a, b; public int phase; public float clock;
        }

        public string BuildId { get; private set; }
        double startedAt, endsAt; int skipCost; string title; bool queued;
        CheckoutInterior.Item item;
        Transform works, board, progressFill, speedUp;
        TextMesh caption, countdown, countdownShadow, speedUpText;
        readonly List<Renderer> hidden = new List<Renderer>();
        readonly List<Worker> workers = new List<Worker>();
        readonly List<Material> owned = new List<Material>();
        CheckoutConstructionSite art; float refresh;
        public static long Now => DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();

        public static CheckoutInteriorWorks Show(CheckoutInterior.Item it, BuildEntry build)
        {
            var works = it.root.GetComponent<CheckoutInteriorWorks>();
            if (!works) { works = it.root.gameObject.AddComponent<CheckoutInteriorWorks>(); works.item = it; works.BuildId = build.id; works.Build(); }
            works.Refresh(build);
            return works;
        }

        public static void Finish(CheckoutInterior.Item it)
        {
            var works = it?.root ? it.root.GetComponent<CheckoutInteriorWorks>() : null;
            if (works) works.Done();
        }

        public void Refresh(BuildEntry build)
        {
            BuildId = build.id; startedAt = build.startedAt; endsAt = build.endsAt; skipCost = build.skipCost; queued = build.queued;
            title = string.IsNullOrEmpty(build.name) ? "Obra" : build.name;
            UpdateBoard(true);
        }

        float Progress => endsAt <= startedAt ? 1 : Mathf.Clamp01((float)((Now - startedAt) / (endsAt - startedAt)));

        // ---------------------------------------------------------------- set up
        Material Mat(Material preferred, string hex, float gloss = .1f)
        {
            if (preferred) return preferred;
            var m = new Material(Shader.Find("Standard")); ColorUtility.TryParseHtmlString("#" + hex, out var c); m.color = c; m.SetFloat("_Glossiness", gloss);
            owned.Add(m); return m;
        }

        Transform Part(Transform parent, string name, Vector3 local, Vector3 size, Material m, PrimitiveType type = PrimitiveType.Cube)
        {
            var go = GameObject.CreatePrimitive(type); go.name = name;
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false); go.transform.localPosition = local; go.transform.localScale = size;
            var r = go.GetComponent<Renderer>(); r.sharedMaterial = m; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return go.transform;
        }

        Transform Kit(string name, Transform parent, Vector3 local, float yaw)
        {
            var template = art && art.kit ? art.kit.Find(name) : null;
            if (!template) return null;
            var copy = Instantiate(template.gameObject, parent).transform;
            copy.name = name; copy.localPosition = local; copy.localRotation = Quaternion.Euler(0, yaw, 0);
            foreach (var mb in copy.GetComponentsInChildren<MonoBehaviour>(true)) Destroy(mb);
            copy.gameObject.SetActive(true);
            return copy;
        }

        void Build()
        {
            art = FindAnyObjectByType<CheckoutConstructionSite>(FindObjectsInactive.Include);
            var piece = item.piece;
            // The finished piece waits hidden behind the hoardings.
            foreach (var r in item.root.GetComponentsInChildren<Renderer>(true)) if (!r.forceRenderingOff) { r.forceRenderingOff = true; hidden.Add(r); }

            works = new GameObject("Works").transform;
            works.SetParent(item.root, false);
            // The piece may be resized in the map editor: the works keep their real size.
            float s = Mathf.Max(.2f, item.scale); works.localScale = Vector3.one / s;
            Vector2 min = piece.min * s, max = piece.max * s;
            float w = max.x - min.x, d = max.y - min.y, cx = (min.x + max.x) * .5f, cz = (min.y + max.y) * .5f;
            var navy = Mat(art ? art.navyPaint : null, "1D2B4F", .25f);
            var gold = Mat(art ? art.goldTrim : null, "E0B040", .4f);
            var steel = Mat(art ? art.galvanized : null, "A9B2BC", .5f);
            var planks = Mat(art ? art.planks : null, "B98B55");
            var hazard = Mat(art ? art.hazard : null, "F2C230");

            // Dusty boards on the floor and the frame of the piece being assembled.
            Part(works, "Floor boards", new Vector3(cx, .012f, cz), new Vector3(w - .1f, .02f, d - .1f), planks);
            float h = Mathf.Clamp(piece.markerHeight - .3f, 1.4f, 2.6f);
            foreach (var x in new[] { min.x + .12f, max.x - .12f })
                foreach (var z in new[] { min.y + .12f, max.y - .12f })
                    Part(works, "Scaffold pole", new Vector3(x, h * .5f, z), new Vector3(.06f, h, .06f), steel);
            foreach (var y in new[] { h * .45f, h - .05f })
            {
                Part(works, "Scaffold rail", new Vector3(cx, y, min.y + .12f), new Vector3(w - .2f, .05f, .05f), steel);
                Part(works, "Scaffold rail", new Vector3(cx, y, max.y - .12f), new Vector3(w - .2f, .05f, .05f), steel);
                Part(works, "Scaffold rail", new Vector3(min.x + .12f, y, cz), new Vector3(.05f, .05f, d - .2f), steel);
                Part(works, "Scaffold rail", new Vector3(max.x - .12f, y, cz), new Vector3(.05f, .05f, d - .2f), steel);
            }
            Part(works, "Scaffold deck", new Vector3(cx, h * .45f + .04f, cz), new Vector3(w - .3f, .04f, Mathf.Min(.5f, d - .3f)), planks);

            // Low hoardings round the works (navy panels, gold cap, hazard band); the customer side stays
            // open so the builders are seen at work.
            const float hoard = .95f, off = .08f;
            void Hoarding(Vector3 a, Vector3 b)
            {
                var mid = (a + b) * .5f; var len = Vector3.Distance(a, b); if (len < .2f) return;
                var g = new GameObject("Hoarding").transform; g.SetParent(works, false); g.localPosition = mid;
                g.localRotation = Quaternion.LookRotation(b - a);
                Part(g, "Panel", new Vector3(0, hoard * .5f, 0), new Vector3(.05f, hoard, len), navy);
                Part(g, "Cap", new Vector3(0, hoard + .02f, 0), new Vector3(.08f, .04f, len + .04f), gold);
                Part(g, "Band", new Vector3(0, .12f, 0), new Vector3(.06f, .12f, len), hazard);
            }
            Hoarding(new Vector3(min.x - off, 0, max.y + off), new Vector3(max.x + off, 0, max.y + off));
            Hoarding(new Vector3(min.x - off, 0, min.y - off), new Vector3(min.x - off, 0, max.y + off));
            Hoarding(new Vector3(max.x + off, 0, min.y - off), new Vector3(max.x + off, 0, max.y + off));
            // Front: two short wings leave a gap in the middle.
            float gap = Mathf.Min(1.1f, w * .45f);
            Hoarding(new Vector3(min.x - off, 0, min.y - off), new Vector3(cx - gap * .5f, 0, min.y - off));
            Hoarding(new Vector3(cx + gap * .5f, 0, min.y - off), new Vector3(max.x + off, 0, min.y - off));
            // Traffic cones by the gap.
            foreach (var x in new[] { cx - gap * .5f - .15f, cx + gap * .5f + .15f })
            {
                Part(works, "Cone", new Vector3(x, .17f, min.y - .35f), new Vector3(.16f, .17f, .16f), hazard, PrimitiveType.Cylinder);
                Part(works, "Cone base", new Vector3(x, .015f, min.y - .35f), new Vector3(.24f, .03f, .24f), navy);
            }

            var stackAt = new Vector3(max.x - .45f, 0, max.y - .4f);
            // A few boxes of parts, in the market's colours.
            Part(works, "Parts box", stackAt + new Vector3(0, .15f, 0), new Vector3(.5f, .3f, .35f), planks);
            Part(works, "Parts box", stackAt + new Vector3(-.05f, .42f, .02f), new Vector3(.38f, .24f, .3f), navy);
            Crew(new Vector3(cx, 0, min.y - .15f), stackAt, new Vector3(cx, 0, cz));

            // Board over the works.
            board = new GameObject("Works board").transform; board.SetParent(works, false);
            board.localPosition = new Vector3(cx, Mathf.Max(piece.markerHeight, h) + 1.05f, cz);
            Part(board, "Board", new Vector3(0, 0, .03f), new Vector3(2.5f, .92f, .05f), navy);
            Part(board, "Trim top", new Vector3(0, .48f, .02f), new Vector3(2.6f, .06f, .07f), gold);
            Part(board, "Trim bottom", new Vector3(0, -.48f, .02f), new Vector3(2.6f, .06f, .07f), gold);
            Part(board, "Bar back", new Vector3(0, -.28f, 0), new Vector3(2.1f, .09f, .03f), steel);
            progressFill = Part(board, "Bar fill", new Vector3(0, -.28f, -.02f), new Vector3(2.1f, .09f, .03f), gold);
            caption = Text(board, new Vector3(0, .25f, -.03f), new Color(1, 1, 1), .036f);
            countdownShadow = Text(board, new Vector3(.012f, -.01f, 0), new Color(.03f, .05f, .12f, .9f), .052f);
            countdown = Text(board, new Vector3(0, 0, -.03f), new Color(1f, .9f, .45f), .052f);
            speedUp = new GameObject("Speed up").transform; speedUp.SetParent(board, false); speedUp.localPosition = new Vector3(0, -.78f, 0);
            Part(speedUp, "Plate edge", new Vector3(0, 0, .04f), new Vector3(1.85f, .5f, .06f), navy);
            Part(speedUp, "Plate", new Vector3(0, 0, .01f), new Vector3(1.75f, .42f, .06f), gold);
            var gem = Part(speedUp, "Diamond", new Vector3(.62f, 0, -.04f), new Vector3(.2f, .2f, .06f), Mat(null, "59D9FF", .9f));
            gem.localRotation = Quaternion.Euler(0, 0, 45);
            speedUpText = Text(speedUp, new Vector3(-.15f, 0, -.04f), new Color(.08f, .12f, .24f), .036f);
            var click = speedUp.gameObject.AddComponent<BoxCollider>(); click.size = new Vector3(1.9f, .55f, .3f);
            var target = speedUp.gameObject.AddComponent<CheckoutTarget>(); target.panel = "finishBuild"; target.requestId = BuildId;
            var boardClick = board.gameObject.AddComponent<BoxCollider>(); boardClick.size = new Vector3(2.6f, 1f, .2f); boardClick.center = new Vector3(0, .05f, 0);
            // The board opens the page of what is being built; only the gold plate spends diamonds.
            var boardTarget = board.gameObject.AddComponent<CheckoutTarget>();
            if (item.type == "shelf") { boardTarget.panel = "store"; boardTarget.shelfId = item.id.Substring(6); }
            else if (item.type == "sector") { boardTarget.panel = "sectors"; boardTarget.sectorId = item.id.Substring(7); }
            else boardTarget.panel = "shop";
        }

        TextMesh Text(Transform parent, Vector3 local, Color color, float size)
        {
            var go = new GameObject("Text"); go.transform.SetParent(parent, false); go.transform.localPosition = local;
            var t = go.AddComponent<TextMesh>();
            var font = art && art.boardFont ? art.boardFont : null;
            var stage = FindAnyObjectByType<CheckoutStageConstruction>(FindObjectsInactive.Include);
            if (!font && stage) font = stage.titleFont;
            if (font) { t.font = font; go.GetComponent<MeshRenderer>().sharedMaterial = stage && stage.titleMaterial ? stage.titleMaterial : font.material; }
            t.fontSize = 64; t.characterSize = size; t.anchor = TextAnchor.MiddleCenter; t.alignment = TextAlignment.Center; t.fontStyle = FontStyle.Bold; t.color = color;
            return t;
        }

        // ---------------------------------------------------------------- builders
        void Crew(Vector3 front, Vector3 stack, Vector3 center)
        {
            var template = FindAnyObjectByType<MarketDay.MarketDeliveryWorker>(FindObjectsInactive.Include);
            if (!template) return;
            Spawn(template, front + new Vector3(-.35f, 0, 0), center, false, 0);
            Spawn(template, stack + new Vector3(-.5f, 0, -.3f), center + new Vector3(.3f, 0, 0), true, 1);
        }

        void Spawn(MarketDay.MarketDeliveryWorker template, Vector3 a, Vector3 b, bool carrier, int variant)
        {
            var holder = new GameObject("Builder holder"); holder.SetActive(false);
            var clone = Instantiate(template.gameObject, holder.transform);
            DestroyImmediate(clone.GetComponent<MarketDay.MarketDeliveryWorker>());
            foreach (Transform child in clone.transform.Cast<Transform>().ToArray()) if (child.name != "Visual") DestroyImmediate(child.gameObject);
            foreach (var c in clone.GetComponentsInChildren<Collider>(true)) DestroyImmediate(c);
            foreach (var agent in clone.GetComponentsInChildren<UnityEngine.AI.NavMeshAgent>(true)) DestroyImmediate(agent);
            clone.name = "Builder";
            var crew = art ? art.crew : null;
            foreach (var r in clone.GetComponentsInChildren<Renderer>(true))
            {
                r.enabled = true; r.forceRenderingOff = false;
                if (r is SkinnedMeshRenderer skin && crew != null && crew.Length > 0 && crew[variant % crew.Length]) skin.sharedMaterial = crew[variant % crew.Length];
            }
            clone.transform.SetParent(works, false);
            Destroy(holder);
            clone.transform.localPosition = a;
            clone.transform.localRotation = Quaternion.LookRotation(new Vector3(b.x - a.x, 0, b.z - a.z).sqrMagnitude > .01f ? new Vector3(b.x - a.x, 0, b.z - a.z) : Vector3.forward);
            var want = template.transform.lossyScale; var parent = works.lossyScale;
            clone.transform.localScale = new Vector3(want.x / Mathf.Max(.0001f, parent.x), want.y / Mathf.Max(.0001f, parent.y), want.z / Mathf.Max(.0001f, parent.z));
            var bones = clone.GetComponentsInChildren<Transform>(true);
            var w = new Worker
            {
                body = clone.transform, carrier = carrier, a = a, b = b, anim = clone.GetComponentInChildren<Animation>(true),
                handL = bones.FirstOrDefault(x => x.name == "Hand_L"), handR = bones.FirstOrDefault(x => x.name == "Hand_R"),
                clock = variant * .8f,
            };
            var head = bones.FirstOrDefault(x => x.name == "Head");
            var hat = head ? Kit("Hard hat", works, Vector3.zero, 0) : null;
            if (hat)
            {
                hat.localScale = Vector3.one * .56f;
                hat.SetPositionAndRotation(clone.transform.position + Vector3.up * 2.13f * clone.transform.lossyScale.y + clone.transform.forward * .02f, clone.transform.rotation);
                hat.SetParent(head, true);
            }
            if (carrier) { w.prop = Kit("Brick bundle", works, a, 0); if (w.prop) w.prop.gameObject.SetActive(false); }
            clone.SetActive(true);
            Play(w, "Idle");
            workers.Add(w);
        }

        void Play(Worker w, string clip)
        {
            if (!w.anim || w.clip == clip || !w.anim[clip]) return;
            w.clip = clip; w.anim[clip].time = 0; w.anim.CrossFade(clip, .15f);
        }

        float Length(Worker w, string clip) => w.anim && w.anim[clip] ? w.anim[clip].length : 1.4f;

        bool Walk(Worker w, Vector3 target, float dt, bool loaded)
        {
            var delta = target - w.body.localPosition; delta.y = 0;
            if (delta.magnitude < .05f) return true;
            var dir = works.TransformDirection(delta);
            w.body.rotation = Quaternion.RotateTowards(w.body.rotation, Quaternion.LookRotation(dir), dt * 300);
            Play(w, loaded ? "CarryWalking" : "Walking");
            w.body.localPosition = Vector3.MoveTowards(w.body.localPosition, new Vector3(target.x, w.body.localPosition.y, target.z), dt * (loaded ? .9f : 1.1f));
            return false;
        }

        void Face(Worker w, Vector3 local, float dt)
        {
            var d = works.TransformPoint(local) - w.body.position; d.y = 0;
            if (d.sqrMagnitude > .001f) w.body.rotation = Quaternion.RotateTowards(w.body.rotation, Quaternion.LookRotation(d), dt * 220);
        }

        void AnimateCrew(float dt)
        {
            foreach (var w in workers)
            {
                if (!w.body) continue;
                w.clock += dt;
                if (!w.carrier)
                {
                    // Kneels at the piece and works on it (crouch, stand, look over the job).
                    Face(w, w.b, dt);
                    if (w.phase == 0) { Play(w, "Pickup"); if (w.clock > Length(w, "Pickup")) { w.phase = 1; w.clock = 0; } }
                    else if (w.phase == 1) { Play(w, "PutDown"); if (w.clock > Length(w, "PutDown")) { w.phase = UnityEngine.Random.value < .3f ? 2 : 0; w.clock = 0; } }
                    else { Play(w, "Idle"); if (w.clock > 1.2f) { w.phase = 0; w.clock = 0; } }
                    continue;
                }
                // Carries parts from the stack to the piece and back.
                switch (w.phase)
                {
                    case 0: Play(w, "Pickup"); Face(w, w.a + (w.a - w.b).normalized, dt); if (w.clock > Length(w, "Pickup") * .55f && w.prop) w.prop.gameObject.SetActive(true); if (w.clock > Length(w, "Pickup")) { w.phase = 1; w.clock = 0; } break;
                    case 1: if (Walk(w, w.b, dt, true)) { w.phase = 2; w.clock = 0; } break;
                    case 2: Play(w, "PutDown"); if (w.clock > Length(w, "PutDown") * .6f && w.prop) w.prop.gameObject.SetActive(false); if (w.clock > Length(w, "PutDown")) { w.phase = 3; w.clock = 0; } break;
                    case 3: if (Walk(w, w.a, dt, false)) { w.phase = 0; w.clock = 0; } break;
                }
            }
        }

        void LateUpdate()
        {
            foreach (var w in workers)
                if (w.prop && w.prop.gameObject.activeSelf && w.handL && w.handR)
                { w.prop.position = (w.handL.position + w.handR.position) * .5f + Vector3.down * .3f + w.body.forward * .1f; w.prop.rotation = w.body.rotation; }
        }

        void Update()
        {
            if (!works) return;
            AnimateCrew(Time.deltaTime);
            UpdateBoard(false);
        }

        void UpdateBoard(bool force)
        {
            if (!board) return;
            var cam = Camera.main; if (cam) board.rotation = cam.transform.rotation;
            refresh -= Time.unscaledDeltaTime;
            if (!force && refresh > 0) return;
            refresh = .25f;
            double remaining = endsAt - Now;
            // Placed while the builders were busy elsewhere: it waits its turn in the queue.
            bool waitingTurn = queued && Now < startedAt;
            if (caption) caption.text = ((waitingTurn ? "NA FILA · " : "OBRA · ") + title).ToUpperInvariant();
            string label = waitingTurn ? "COMEÇA EM " + CheckoutConstructionSite.Countdown(startedAt - Now) : remaining > 0 ? CheckoutConstructionSite.Countdown(remaining) : "FINALIZANDO...";
            if (countdown) { countdown.text = label; countdownShadow.text = label; }
            int cost = remaining <= 0 ? 0 : waitingTurn ? skipCost : Mathf.Max(1, Mathf.CeilToInt((float)(remaining / 600000.0)));
            if (speedUp) speedUp.gameObject.SetActive(remaining > 0);
            if (speedUpText) speedUpText.text = "ACELERAR  " + cost;
            if (progressFill)
            {
                float p = Progress;
                progressFill.localScale = new Vector3(Mathf.Max(.001f, 2.1f * p), .09f, .03f);
                progressFill.localPosition = new Vector3(-1.05f + 1.05f * p, -.28f, -.02f);
            }
        }

        // ---------------------------------------------------------------- finished
        void Done()
        {
            foreach (var r in hidden) if (r) r.forceRenderingOff = false;
            hidden.Clear();
            if (works) Destroy(works.gameObject);
            if (item != null && item.root) StartCoroutine(Pop(item.root));
            else Destroy(this);
        }

        System.Collections.IEnumerator Pop(Transform t)
        {
            var full = t.localScale; float time = 0;
            while (time < .45f)
            {
                time += Time.deltaTime; float k = time / .45f;
                float s = k < .6f ? Mathf.Lerp(.7f, 1.08f, k / .6f) : Mathf.Lerp(1.08f, 1f, (k - .6f) / .4f);
                t.localScale = full * s; yield return null;
            }
            t.localScale = full;
            Destroy(this);
        }

        void OnDestroy() { foreach (var r in hidden) if (r) r.forceRenderingOff = false; foreach (var m in owned) if (m) Destroy(m); }
    }
}
