using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    // The boosters (Melhorias → Boosters) seen in the market while they run (snapshot.boosts):
    //  · Café Energético: a spinning amber ring under every working cashier and stock clerk, with sparks and little
    //    lightning bolts rising from them: the team is on caffeine.
    //  · Happy Hour: confetti drifting down over the market, coloured party lights gliding on the floor and
    //    sparkles popping over the customers.
    //  · Liquidação Relâmpago: a red sale tag swinging over every shelf, a red pulse on the floor in front of
    //    each one and gold glints, like a sale in full swing.
    // Everything is generated here (textures, quads and particles), on the Ignore Raycast layer, and cleaned up
    // when the booster ends.
    public class CheckoutBoostFx : MonoBehaviour
    {
        Transform world;
        CheckoutMap map;
        readonly HashSet<string> running = new HashSet<string>();
        float nextScan, nextBurst;
        Material ringMat, sparkMat, boltMat, tagMat, glowMat, flatMat;

        // Café Energético
        readonly Dictionary<Transform, GameObject> auras = new Dictionary<Transform, GameObject>();
        Transform registerAnchor;
        ParticleSystem energy;
        // Happy Hour
        ParticleSystem confetti, party;
        readonly List<GameObject> lights = new List<GameObject>();
        // Liquidação Relâmpago
        readonly List<GameObject> tags = new List<GameObject>();
        ParticleSystem glints;

        static readonly Color Amber = new Color(1f, .68f, .2f), Pink = new Color(.89f, .36f, .69f), SaleRed = new Color(.9f, .27f, .17f);
        static readonly Color[] PartyColors = { new Color(.89f, .36f, .69f), new Color(.61f, .36f, .9f), new Color(.97f, .77f, .28f), new Color(.24f, .76f, .83f) };

        public void Initialize(Transform root, CheckoutMap owner) { world = root; map = owner; }

        public void Apply(string[] boosts)
        {
            var next = new HashSet<string>(boosts ?? new string[0]);
            foreach (var id in running.Except(next).ToList()) End(id);
            foreach (var id in next.Except(running).ToList()) Begin(id);
            running.Clear(); running.UnionWith(next);
            nextScan = 0;
        }

        void Begin(string id)
        {
            switch (id)
            {
                case "energy-coffee": energy = Energy(); break;
                case "happy-hour": confetti = Confetti(); party = Party(); for (int i = 0; i < 4; i++) lights.Add(Light(i)); break;
                case "flash-sale": glints = Glints(); break;
            }
        }

        void End(string id)
        {
            switch (id)
            {
                case "energy-coffee":
                    foreach (var a in auras.Values) if (a) Destroy(a);
                    auras.Clear(); Fade(energy); energy = null; break;
                case "happy-hour":
                    Fade(confetti); Fade(party); confetti = party = null;
                    foreach (var l in lights) if (l) Destroy(l);
                    lights.Clear(); break;
                case "flash-sale":
                    foreach (var t in tags) if (t) Destroy(t);
                    tags.Clear(); Fade(glints); glints = null; break;
            }
        }

        // Stop emitting, let what is in the air finish, then remove it.
        static void Fade(ParticleSystem ps)
        {
            if (!ps) return;
            ps.Stop(true, ParticleSystemStopBehavior.StopEmitting);
            Destroy(ps.gameObject, 4f);
        }

        void Update()
        {
            if (running.Count == 0) return;
            float now = Time.time;
            if (now >= nextScan) { nextScan = now + 1f; Scan(); }
            bool burst = now >= nextBurst;
            if (burst) nextBurst = now + .45f;
            if (running.Contains("energy-coffee")) UpdateEnergy(now, burst);
            if (running.Contains("happy-hour")) UpdateParty(now, burst);
            if (running.Contains("flash-sale")) UpdateSale(now, burst);
        }

        // Who and what the effects follow (staff come and go, shelves get placed and moved).
        void Scan()
        {
            if (running.Contains("energy-coffee"))
            {
                var people = Workers().ToList();
                // Nobody hired yet: the till itself buzzes (the player is the one at the register).
                if (people.Count == 0 && map)
                {
                    if (!registerAnchor) { registerAnchor = new GameObject("Boost register anchor").transform; registerAnchor.SetParent(transform, false); }
                    registerAnchor.position = map.Register + Vector3.up * .2f;
                    people.Add(registerAnchor);
                }
                foreach (var t in people) if (!auras.ContainsKey(t)) auras[t] = Ring("Coffee aura", Amber, 2.2f);
                foreach (var gone in auras.Keys.Where(t => !t || !people.Contains(t)).ToList()) { if (auras[gone]) Destroy(auras[gone]); auras.Remove(gone); }
            }
            if (running.Contains("flash-sale"))
            {
                var spots = map ? map.BoostShelfPoints().ToList() : new List<Vector3>();
                while (tags.Count < spots.Count) tags.Add(Tag(tags.Count));
                for (int i = 0; i < tags.Count; i++)
                {
                    bool on = i < spots.Count; tags[i].SetActive(on);
                    if (on) tags[i].transform.position = spots[i] + Vector3.up * 1.3f;
                }
            }
        }

        IEnumerable<Transform> Workers()
        {
            if (!world) yield break;
            // The cashiers behind the registers and the hired stock clerks and cleaners walking about.
            foreach (Transform t in world)
                if (t.name.StartsWith("Worker_Cashier") && t.gameObject.activeInHierarchy) yield return t;
            var holder = GameObject.Find("Market Staff");
            if (!holder) yield break;
            foreach (Transform t in holder.transform)
                if (t.name.StartsWith("Staff_") && t.gameObject.activeInHierarchy) yield return t;
        }

        // ------------------------------------------------------------------ Café Energético
        void UpdateEnergy(float now, bool burst)
        {
            float beat = Mathf.Pow(Mathf.Abs(Mathf.Sin(now * Mathf.PI * 2.4f)), 6);
            foreach (var pair in auras)
            {
                if (!pair.Key || !pair.Value) continue;
                bool on = pair.Key.gameObject.activeInHierarchy; pair.Value.SetActive(on);
                if (!on) continue;
                var ring = pair.Value.transform;
                // People stand on the floor; the till's ring sits on the register itself so the counter doesn't hide it.
                ring.position = pair.Key == registerAnchor ? pair.Key.position + Vector3.up * .55f : Ground(pair.Key.position) + Vector3.up * .06f;
                ring.rotation = Quaternion.Euler(90, now * 220, 0);
                ring.localScale = Vector3.one * (2.2f + .45f * beat);
                Tint(pair.Value, new Color(Amber.r, Amber.g, Amber.b, .55f + .4f * beat));
                if (burst && energy) Emit(energy, pair.Key.position + Vector3.up * 1.2f, 5, Amber);
            }
        }

        ParticleSystem Energy()
        {
            var ps = System("Coffee sparks", Bolt());
            var main = ps.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(.7f, 1.1f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.8f, 1.6f);
            main.startSize = new ParticleSystem.MinMaxCurve(.45f, .75f);
            main.startRotation = new ParticleSystem.MinMaxCurve(-.4f, .4f);
            main.gravityModifier = -.15f;
            main.maxParticles = 300;
            var shape = ps.shape; shape.enabled = true; shape.shapeType = ParticleSystemShapeType.Sphere; shape.radius = .35f;
            Twinkle(ps);
            ps.Play();
            return ps;
        }

        // ------------------------------------------------------------------ Happy Hour
        void UpdateParty(float now, bool burst)
        {
            var center = Center(out float size);
            if (confetti) { confetti.transform.position = center + Vector3.up * 7f; var shape = confetti.shape; shape.scale = new Vector3(size, size, .2f); }
            for (int i = 0; i < lights.Count; i++)
            {
                if (!lights[i]) continue;
                // Each light glides on its own loop over the floor and slides through the party colours.
                float t = now * (.35f + i * .07f) + i * 1.7f;
                var at = center + new Vector3(Mathf.Sin(t * 1.3f) * size * .42f, .07f, Mathf.Sin(t * .9f + i) * size * .36f);
                lights[i].transform.position = Ground(at) + Vector3.up * .07f;
                lights[i].transform.rotation = Quaternion.Euler(90, now * 40 * (i % 2 == 0 ? 1 : -1), 0);
                float h = (now * .4f + i * .9f) % PartyColors.Length; int a = (int)h;
                var c = Color.Lerp(PartyColors[a], PartyColors[(a + 1) % PartyColors.Length], h - a);
                Tint(lights[i], new Color(c.r, c.g, c.b, .7f + .2f * Mathf.Sin(now * 6 + i)));
                lights[i].transform.localScale = Vector3.one * (5f + .8f * Mathf.Sin(now * 2 + i));
            }
            if (burst && party)
            {
                // Sparkles pop over a couple of customers at a time.
                var people = FindObjectsByType<CheckoutWalker>(FindObjectsSortMode.None).Where(w => w.gameObject.activeInHierarchy).ToArray();
                for (int k = 0; k < Mathf.Min(2, people.Length); k++)
                {
                    var who = people[Random.Range(0, people.Length)];
                    Emit(party, who.transform.position + Vector3.up * 2.1f, 6, PartyColors[Random.Range(0, PartyColors.Length)]);
                }
            }
        }

        ParticleSystem Confetti()
        {
            var ps = System("Happy hour confetti", Flat());
            ps.transform.rotation = Quaternion.Euler(90, 0, 0);
            var main = ps.main;
            main.loop = true; main.duration = 5;
            main.startLifetime = new ParticleSystem.MinMaxCurve(4f, 6f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.4f, 1.2f);
            main.startSize = new ParticleSystem.MinMaxCurve(.25f, .42f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0, 6.28f);
            main.gravityModifier = .12f;
            main.maxParticles = 400;
            var colors = new Gradient();
            colors.SetKeys(PartyColors.Select((c, i) => new GradientColorKey(c, i / (PartyColors.Length - 1f))).ToArray(),
                new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(1, 1) });
            main.startColor = new ParticleSystem.MinMaxGradient(colors) { mode = ParticleSystemGradientMode.RandomColor };
            var shape = ps.shape; shape.enabled = true; shape.shapeType = ParticleSystemShapeType.Box; shape.scale = new Vector3(14, 14, .2f);
            var emission = ps.emission; emission.rateOverTime = 45;
            var spin = ps.rotationOverLifetime; spin.enabled = true; spin.z = new ParticleSystem.MinMaxCurve(-4f, 4f);
            var wobble = ps.noise; wobble.enabled = true; wobble.strength = .6f; wobble.frequency = .4f;
            Fades(ps, .05f);
            ps.Play();
            return ps;
        }

        ParticleSystem Party()
        {
            var ps = System("Happy hour sparkles", Spark());
            var main = ps.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(.6f, 1f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.6f, 1.8f);
            main.startSize = new ParticleSystem.MinMaxCurve(.5f, .9f);
            main.maxParticles = 200;
            var shape = ps.shape; shape.enabled = true; shape.shapeType = ParticleSystemShapeType.Sphere; shape.radius = .2f;
            Twinkle(ps);
            ps.Play();
            return ps;
        }

        GameObject Light(int i) => Ring("Party light " + i, PartyColors[i % PartyColors.Length], 5f, true);

        // ------------------------------------------------------------------ Liquidação Relâmpago
        void UpdateSale(float now, bool burst)
        {
            var cam = Camera.main;
            for (int i = 0; i < tags.Count; i++)
            {
                var tag = tags[i]; if (!tag || !tag.activeSelf) continue;
                // The tag hangs over the shelf facing the camera, swings and blinks like a shop light.
                var face = cam ? cam.transform.rotation : Quaternion.identity;
                tag.transform.rotation = face * Quaternion.Euler(0, 0, Mathf.Sin(now * 3.4f + i) * 14);
                float pop = 1 + .12f * Mathf.Max(0, Mathf.Sin(now * Mathf.PI * 3 + i * .6f));
                tag.transform.localScale = Vector3.one * 2.1f * pop;
                var pulse = tag.transform.Find("Pulse");
                if (pulse)
                {
                    float k = Mathf.Repeat(now * .8f + i * .23f, 1);
                    pulse.position = Ground(tag.transform.position) + Vector3.up * .06f;
                    pulse.rotation = Quaternion.Euler(90, 0, 0);
                    pulse.localScale = Vector3.one * Mathf.Lerp(1f, 4.5f, k) / Mathf.Max(.01f, tag.transform.localScale.x);
                    Tint(pulse.gameObject, new Color(SaleRed.r, SaleRed.g, SaleRed.b, .7f * (1 - k)));
                }
                if (burst && glints && Random.value < .5f) Emit(glints, tag.transform.position + Vector3.down * .5f, 4, new Color(1, .85f, .35f));
            }
        }

        GameObject Tag(int i)
        {
            var go = Quad("Sale tag " + i, Price());
            go.transform.localScale = Vector3.one * .9f;
            // The red pulse on the floor in front of the shelf (kept as a child so it comes and goes with the tag).
            var pulse = Ring("Pulse", SaleRed, 1f);
            pulse.transform.SetParent(go.transform, true);
            return go;
        }

        ParticleSystem Glints()
        {
            var ps = System("Sale glints", Spark());
            var main = ps.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(.5f, .9f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.3f, 1f);
            main.startSize = new ParticleSystem.MinMaxCurve(.45f, .7f);
            main.gravityModifier = .3f;
            main.maxParticles = 200;
            var shape = ps.shape; shape.enabled = true; shape.shapeType = ParticleSystemShapeType.Sphere; shape.radius = .3f;
            Twinkle(ps);
            ps.Play();
            return ps;
        }

        // ------------------------------------------------------------------ helpers
        // The middle of the market (its shelves and entrance) and roughly how big it is.
        Vector3 Center(out float size)
        {
            var points = map ? map.BoostShelfPoints().ToList() : new List<Vector3>();
            if (map) points.Add(map.Entrance);
            if (points.Count == 0) { size = 10; return Vector3.zero; }
            var b = new Bounds(points[0], Vector3.zero);
            foreach (var p in points) b.Encapsulate(p);
            size = Mathf.Clamp(Mathf.Max(b.size.x, b.size.z) + 4, 8, 30);
            return new Vector3(b.center.x, points.Min(p => p.y), b.center.z);
        }

        // The floor under a point (the market's floor is near y=.74; nothing is ever placed below 0).
        static Vector3 Ground(Vector3 at) => Physics.Raycast(new Vector3(at.x, Mathf.Min(at.y, 1.6f), at.z), Vector3.down, out var hit, 4, ~(1 << 2), QueryTriggerInteraction.Ignore) ? hit.point : new Vector3(at.x, .74f, at.z);

        static void Emit(ParticleSystem ps, Vector3 at, int count, Color color)
        {
            var p = new ParticleSystem.EmitParams { position = at, startColor = color, applyShapeToPosition = true };
            ps.Emit(p, count);
        }

        static void Tint(GameObject go, Color color)
        {
            var r = go.GetComponent<Renderer>();
            if (r) r.material.color = color;
        }

        ParticleSystem System(string name, Material material)
        {
            var go = new GameObject("Boost " + name) { layer = 2 };
            go.transform.SetParent(transform, false);
            go.transform.rotation = Quaternion.Euler(-90, 0, 0);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.playOnAwake = false; main.loop = true; main.duration = 1; main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.cullingMode = ParticleSystemCullingMode.AlwaysSimulate;
            var emission = ps.emission; emission.rateOverTime = 0;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.sharedMaterial = material;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return ps;
        }

        static void Twinkle(ParticleSystem ps)
        {
            var size = ps.sizeOverLifetime; size.enabled = true;
            size.size = new ParticleSystem.MinMaxCurve(1, new AnimationCurve(new Keyframe(0, 0), new Keyframe(.2f, 1), new Keyframe(.7f, .7f), new Keyframe(1, 0)));
            Fades(ps, .1f);
        }

        static void Fades(ParticleSystem ps, float fadeIn)
        {
            var fade = ps.colorOverLifetime; fade.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, fadeIn), new GradientAlphaKey(1, .65f), new GradientAlphaKey(0, 1) });
            fade.color = g;
        }

        GameObject Ring(string name, Color color, float scale, bool soft = false)
        {
            var go = Quad(name, soft ? Glow() : RingMat());
            go.transform.rotation = Quaternion.Euler(90, 0, 0);
            go.transform.localScale = Vector3.one * scale;
            Tint(go, color);
            return go;
        }

        GameObject Quad(string name, Material material)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad); go.name = name; go.layer = 2;
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(transform, false);
            var r = go.GetComponent<MeshRenderer>(); r.material = new Material(material);
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return go;
        }

        static Material Mat(Texture2D texture) => new Material(Shader.Find("Sprites/Default")) { mainTexture = texture, renderQueue = 3100 };
        Material Flat() => flatMat ? flatMat : (flatMat = Mat(Texture2D.whiteTexture));
        Material RingMat() => ringMat ? ringMat : (ringMat = Mat(RingTexture()));
        Material Glow() => glowMat ? glowMat : (glowMat = Mat(GlowTexture()));
        Material Spark()
        {
            if (sparkMat) return sparkMat;
            var t = Resources.Load<Texture2D>("CheckoutDesktop/Game/sparkle");
            return sparkMat = Mat(t ? t : GlowTexture());
        }
        Material Bolt()
        {
            if (boltMat) return boltMat;
            var t = Resources.Load<Texture2D>("CheckoutDesktop/Game/bolt");
            if (!t) t = Resources.Load<Texture2D>("CheckoutDesktop/Icons/lightning");
            return boltMat = Mat(t ? t : GlowTexture());
        }
        Material Price()
        {
            if (tagMat) return tagMat;
            var t = Resources.Load<Texture2D>("CheckoutDesktop/Icons/price-tag");
            return tagMat = Mat(t ? t : Texture2D.whiteTexture);
        }

        // A dashed ring (eight arcs) so the spin shows.
        static Texture2D RingTexture()
        {
            const int n = 128; var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp }; var px = new Color32[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float dx = (x + .5f) / n * 2 - 1, dy = (y + .5f) / n * 2 - 1, d = Mathf.Sqrt(dx * dx + dy * dy);
                float ring = Mathf.Clamp01(1 - Mathf.Abs(d - .82f) / .09f); ring *= ring;
                float dash = Mathf.Repeat(Mathf.Atan2(dy, dx) / (Mathf.PI * 2) * 8, 1) < .62f ? 1 : .25f;
                float inner = Mathf.Clamp01(1 - d / .8f) * .18f;
                float a = Mathf.Clamp01(ring * dash + inner);
                px[y * n + x] = new Color32(255, 255, 255, (byte)(a * 255));
            }
            t.SetPixels32(px); t.Apply(); return t;
        }

        static Texture2D GlowTexture()
        {
            const int n = 96; var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp }; var px = new Color32[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float dx = (x + .5f) / n * 2 - 1, dy = (y + .5f) / n * 2 - 1, d = Mathf.Sqrt(dx * dx + dy * dy);
                // A bright core that fades softly: reads on the cream floor of the market.
                float a = Mathf.Clamp01(1 - d); a = Mathf.Pow(a, 1.3f);
                px[y * n + x] = new Color32(255, 255, 255, (byte)(a * 255));
            }
            t.SetPixels32(px); t.Apply(); return t;
        }
    }
}
