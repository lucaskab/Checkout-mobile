using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // "Obra em timelapse": when a market expansion (or the central warehouse) is bought, scaffolding
    // and a crane go up, the building rises out of the dust in a few choppy time-lapse seconds, the
    // new facade pops in and the moment ends with confetti, fireworks and the new name of the shop.
    public class CheckoutStageConstruction : MonoBehaviour
    {
        public Material scaffoldMaterial, plankMaterial, netMaterial, craneMaterial, craneDarkMaterial;
        public Material dustMaterial, confettiMaterial, sparkMaterial, titleMaterial;
        public Mesh confettiMesh;
        public Font titleFont;
        public float duration = 3.4f;

        public bool Playing { get; private set; }
        readonly List<Transform> shells = new List<Transform>();
        readonly Dictionary<Transform, (Vector3 position, Vector3 scale)> shellBase = new Dictionary<Transform, (Vector3, Vector3)>();
        Light sun; float sunIntensity; Quaternion sunRotation;
        Coroutine running; GameObject rig; CheckoutStageDressing revealing;

        public void Play(IList<Transform> rising, Bounds footprint, float floorY, string title, CheckoutStageDressing dressing)
        {
            Finish();
            revealing = dressing;
            running = StartCoroutine(Run(rising, footprint, floorY, title, dressing));
        }

        // Snap everything to its final state (a new snapshot during the show, or leaving the scene).
        public void Finish()
        {
            if (running != null) StopCoroutine(running);
            running = null;
            foreach (var shell in shells) if (shell && shellBase.TryGetValue(shell, out var b)) { shell.localPosition = b.position; shell.localScale = b.scale; }
            shells.Clear(); shellBase.Clear();
            if (sun) { sun.intensity = sunIntensity; sun.transform.rotation = sunRotation; sun = null; }
            if (rig) Destroy(rig);
            if (revealing) revealing.RevealNow();
            revealing = null;
            Playing = false;
        }

        void OnDisable() => Finish();

        IEnumerator Run(IList<Transform> rising, Bounds footprint, float floorY, string title, CheckoutStageDressing dressing)
        {
            Playing = true;
            rig = new GameObject("Construction timelapse");
            rig.transform.SetParent(transform, false);
            foreach (var shell in rising)
            {
                if (!shell) continue;
                shells.Add(shell); shellBase[shell] = (shell.localPosition, shell.localScale);
            }
            sun = RenderSettings.sun ? RenderSettings.sun : FindAnyObjectByType<Light>();
            if (sun) { sunIntensity = sun.intensity; sunRotation = sun.transform.rotation; }

            float height = Mathf.Max(3f, footprint.max.y - floorY + .8f);
            var scaffold = Scaffold(footprint, floorY, height);
            var crane = Crane(footprint, floorY, height);
            var dust = Dust(footprint, floorY);
            SetRise(0.08f, floorY);

            float t = 0, lastStep = -1;
            while (t < duration)
            {
                t += Time.deltaTime;
                // Scaffolding and crane shoot up first.
                scaffold.localScale = new Vector3(1, Ease(Mathf.Clamp01(t / .45f)), 1);
                crane.localScale = new Vector3(1, Ease(Mathf.Clamp01((t - .1f) / .55f)), 1);
                var jib = crane.Find("Jib");
                if (jib) jib.localRotation = Quaternion.Euler(0, Mathf.Sin(t * 2.1f) * 55f, 0);
                // Choppy time-lapse frames: the building only updates about 9 times a second.
                float step = Mathf.Floor(t * 9f) / 9f;
                if (step != lastStep)
                {
                    lastStep = step;
                    float k = Mathf.Clamp01((step - .35f) / (duration - .85f));
                    SetRise(Mathf.Lerp(.08f, 1f, Mathf.SmoothStep(0, 1, k)), floorY);
                    // Days fly by: the sun sweeps a full turn and dims at "night".
                    if (sun)
                    {
                        float day = Mathf.Clamp01(t / duration);
                        sun.transform.rotation = Quaternion.AngleAxis(day * 360f, Vector3.up) * sunRotation;
                        sun.intensity = sunIntensity * (.55f + .45f * Mathf.Abs(Mathf.Cos(day * Mathf.PI * 2f)));
                    }
                }
                yield return null;
            }
            SetRise(1, floorY);
            if (sun) { sun.intensity = sunIntensity; sun.transform.rotation = sunRotation; }
            var emission = dust.emission; emission.enabled = false;

            // Scaffolding comes down, the new look pops in, and the party starts.
            if (dressing) dressing.StartCoroutine(dressing.Reveal());
            revealing = null;
            Confetti(footprint);
            StartCoroutine(Fireworks(footprint));
            var label = Title(title, footprint);
            for (float d = 0; d < .5f; d += Time.deltaTime)
            {
                float k = 1 - Ease(d / .5f);
                scaffold.localScale = new Vector3(1, Mathf.Max(.001f, k), 1);
                crane.localScale = new Vector3(1, Mathf.Max(.001f, k), 1);
                yield return null;
            }
            scaffold.gameObject.SetActive(false); crane.gameObject.SetActive(false);
            yield return TitleShow(label);
            yield return new WaitForSeconds(1.5f);
            shells.Clear(); shellBase.Clear(); sun = null;
            if (rig) Destroy(rig);
            running = null; Playing = false;
        }

        static float Ease(float k) { k = Mathf.Clamp01(k); return 1 - Mathf.Pow(1 - k, 3); }

        // Walls grow up from the shop floor (the floor itself stays put under the shoppers).
        void SetRise(float amount, float floorY)
        {
            foreach (var shell in shells)
            {
                if (!shell || !shellBase.TryGetValue(shell, out var b)) continue;
                var parent = shell.parent;
                float parentFloor = parent ? parent.InverseTransformPoint(new Vector3(0, floorY, 0)).y : floorY;
                var position = b.position;
                position.y = parentFloor + (b.position.y - parentFloor) * amount;
                shell.localPosition = position;
                shell.localScale = new Vector3(b.scale.x, b.scale.y * amount, b.scale.z);
            }
        }

        GameObject Part(Transform parent, string name, Vector3 position, Vector3 scale, Material material, PrimitiveType type = PrimitiveType.Cube)
        {
            var go = GameObject.CreatePrimitive(type);
            go.name = name;
            var collider = go.GetComponent<Collider>(); if (collider) Destroy(collider);
            go.transform.SetParent(parent, false);
            go.transform.localPosition = position; go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = material;
            go.GetComponent<Renderer>().shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            return go;
        }

        Transform Scaffold(Bounds footprint, float floorY, float height)
        {
            var root = new GameObject("Scaffolding").transform;
            root.SetParent(rig.transform, false);
            root.position = new Vector3(footprint.center.x, floorY - .6f, footprint.center.z);
            float hx = footprint.extents.x + .55f, hz = footprint.extents.z + .55f, h = height + .6f;
            void Side(Vector3 from, Vector3 to, bool net)
            {
                float length = Vector3.Distance(from, to);
                int bays = Mathf.Max(1, Mathf.RoundToInt(length / 2.2f));
                var dir = (to - from) / length;
                var normal = new Vector3(dir.z, 0, -dir.x);
                for (int i = 0; i <= bays; i++)
                {
                    var p = Vector3.Lerp(from, to, i / (float)bays);
                    Part(root, "Pole", p + Vector3.up * h * .5f, new Vector3(.08f, h, .08f), scaffoldMaterial);
                    Part(root, "Pole", p + normal * .7f + Vector3.up * h * .5f, new Vector3(.08f, h, .08f), scaffoldMaterial);
                }
                var mid = (from + to) * .5f;
                var rotation = Quaternion.LookRotation(dir);
                for (float y = 1.1f; y < h; y += 1.25f)
                {
                    var rail = Part(root, "Ledger", mid + Vector3.up * y, new Vector3(.06f, .06f, length), scaffoldMaterial); rail.transform.localRotation = rotation;
                    var plank = Part(root, "Plank", mid + normal * .35f + Vector3.up * (y - .05f), new Vector3(.62f, .05f, length), plankMaterial); plank.transform.localRotation = rotation;
                }
                if (net && netMaterial)
                {
                    var screen = Part(root, "Safety net", mid + normal * .75f + Vector3.up * h * .55f, new Vector3(.02f, h * .7f, length), netMaterial);
                    screen.transform.localRotation = rotation;
                }
            }
            var a = new Vector3(-hx, 0, -hz); var b = new Vector3(hx, 0, -hz); var c = new Vector3(hx, 0, hz); var d = new Vector3(-hx, 0, hz);
            // The camera looks from the south-east: nets only on the far sides so the site stays readable.
            Side(a, b, false); Side(b, c, false); Side(c, d, true); Side(d, a, true);
            root.localScale = new Vector3(1, .001f, 1);
            return root;
        }

        Transform Crane(Bounds footprint, float floorY, float height)
        {
            var root = new GameObject("Tower crane").transform;
            root.SetParent(rig.transform, false);
            root.position = new Vector3(footprint.max.x + 1.6f, floorY - .6f, footprint.max.z + 1.2f);
            float mast = height + 6.5f;
            Part(root, "Base", new Vector3(0, .2f, 0), new Vector3(1.6f, .4f, 1.6f), craneDarkMaterial);
            for (int i = 0; i < 4; i++)
            {
                var corner = new Vector3(i % 2 == 0 ? -.35f : .35f, 0, i < 2 ? -.35f : .35f);
                Part(root, "Mast", corner + Vector3.up * mast * .5f, new Vector3(.1f, mast, .1f), craneMaterial);
            }
            for (float y = .8f; y < mast; y += .9f)
            {
                var brace = Part(root, "Brace", new Vector3(0, y, -.35f), new Vector3(.9f, .05f, .05f), craneMaterial); brace.transform.localRotation = Quaternion.Euler(0, 0, 40);
                var brace2 = Part(root, "Brace", new Vector3(-.35f, y + .45f, 0), new Vector3(.05f, .05f, .9f), craneMaterial); brace2.transform.localRotation = Quaternion.Euler(-40, 0, 0);
            }
            var jib = new GameObject("Jib").transform; jib.SetParent(root, false); jib.localPosition = new Vector3(0, mast, 0);
            // Point the jib over the building.
            var toCenter = footprint.center - root.position; toCenter.y = 0;
            var holder = new GameObject("Jib heading").transform; holder.SetParent(root, false); holder.localPosition = new Vector3(0, mast, 0);
            holder.rotation = Quaternion.LookRotation(toCenter.sqrMagnitude > .01f ? toCenter.normalized : Vector3.forward);
            jib.SetParent(holder, false); jib.localPosition = Vector3.zero;
            float reach = Mathf.Min(toCenter.magnitude + 1.5f, 12f);
            Part(jib, "Jib arm", new Vector3(0, .25f, reach * .5f), new Vector3(.55f, .5f, reach), craneMaterial);
            Part(jib, "Counter jib", new Vector3(0, .25f, -1.9f), new Vector3(.5f, .45f, 3.2f), craneMaterial);
            Part(jib, "Counterweight", new Vector3(0, -.1f, -3.2f), new Vector3(.9f, .8f, .9f), craneDarkMaterial);
            Part(jib, "Cab", new Vector3(.55f, -.25f, .3f), new Vector3(.6f, .7f, .7f), craneDarkMaterial);
            Part(jib, "Peak", new Vector3(0, 1.4f, 0), new Vector3(.12f, 2.3f, .12f), craneMaterial);
            var cable = Part(jib, "Cable", new Vector3(0, -2.6f, reach * .7f), new Vector3(.03f, 5.2f, .03f), craneDarkMaterial);
            Part(jib, "Load", new Vector3(0, -5.3f, reach * .7f), new Vector3(1.3f, .45f, .8f), plankMaterial);
            root.localScale = new Vector3(1, .001f, 1);
            return root;
        }

        ParticleSystem Dust(Bounds footprint, float floorY)
        {
            var go = new GameObject("Construction dust");
            go.transform.SetParent(rig.transform, false);
            go.transform.position = new Vector3(footprint.center.x, floorY, footprint.center.z);
            go.transform.rotation = Quaternion.Euler(-90, 0, 0);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.duration = duration; main.loop = false; main.startLifetime = new ParticleSystem.MinMaxCurve(1.2f, 2.2f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.4f, 1.6f); main.startSize = new ParticleSystem.MinMaxCurve(2.2f, 4.2f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(.9f, .84f, .74f, .85f), new Color(.78f, .72f, .64f, .7f));
            main.gravityModifier = -.05f; main.maxParticles = 400; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Box;
            shape.scale = new Vector3(footprint.size.x + 1.5f, footprint.size.z + 1.5f, .2f);
            var emission = ps.emission; emission.rateOverTime = 110;
            var size = ps.sizeOverLifetime; size.enabled = true; size.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .6f, 1, 1.6f));
            var color = ps.colorOverLifetime; color.enabled = true;
            var fade = new Gradient(); fade.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) }, new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, .2f), new GradientAlphaKey(0, 1) });
            color.color = fade;
            go.GetComponent<ParticleSystemRenderer>().sharedMaterial = dustMaterial;
            ps.Play();
            return ps;
        }

        void Confetti(Bounds footprint)
        {
            var go = new GameObject("Confetti");
            go.transform.SetParent(rig.transform, false);
            go.transform.position = new Vector3(footprint.center.x, footprint.max.y + 3f, footprint.center.z);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.duration = 1; main.loop = false; main.startLifetime = new ParticleSystem.MinMaxCurve(2.4f, 3.6f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(5f, 11f); main.startSize = new ParticleSystem.MinMaxCurve(.12f, .24f);
            main.startRotation3D = true; main.startRotationX = new ParticleSystem.MinMaxCurve(0, 6.28f); main.startRotationY = new ParticleSystem.MinMaxCurve(0, 6.28f); main.startRotationZ = new ParticleSystem.MinMaxCurve(0, 6.28f);
            var palette = new Gradient();
            palette.SetKeys(new[] { new GradientColorKey(new Color(1f, .3f, .35f), 0), new GradientColorKey(new Color(1f, .8f, .15f), .25f), new GradientColorKey(new Color(.25f, .8f, .45f), .5f), new GradientColorKey(new Color(.25f, .6f, 1f), .75f), new GradientColorKey(new Color(.85f, .4f, 1f), 1) },
                new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(1, 1) });
            main.startColor = new ParticleSystem.MinMaxGradient(palette) { mode = ParticleSystemGradientMode.RandomColor };
            main.gravityModifier = .55f; main.maxParticles = 600; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Hemisphere; shape.radius = 1.2f;
            go.transform.rotation = Quaternion.Euler(-90, 0, 0);
            var emission = ps.emission; emission.rateOverTime = 0; emission.SetBursts(new[] { new ParticleSystem.Burst(0, 320), new ParticleSystem.Burst(.25f, 160) });
            var rotation = ps.rotationOverLifetime; rotation.enabled = true; rotation.separateAxes = true;
            rotation.x = new ParticleSystem.MinMaxCurve(-6, 6); rotation.y = new ParticleSystem.MinMaxCurve(-6, 6); rotation.z = new ParticleSystem.MinMaxCurve(-6, 6);
            var drag = ps.limitVelocityOverLifetime; drag.enabled = true; drag.drag = 1.6f; drag.limit = 4f;
            var renderer = go.GetComponent<ParticleSystemRenderer>();
            renderer.renderMode = ParticleSystemRenderMode.Mesh; renderer.mesh = confettiMesh; renderer.sharedMaterial = confettiMaterial;
            renderer.alignment = ParticleSystemRenderSpace.Local;
            go.transform.localScale = new Vector3(1, 1, 1);
            ps.Play();
        }

        IEnumerator Fireworks(Bounds footprint)
        {
            var colors = new[] { new Color(1f, .35f, .4f), new Color(1f, .85f, .25f), new Color(.35f, .9f, .55f), new Color(.4f, .7f, 1f), new Color(.95f, .5f, 1f), new Color(1f, .6f, .2f) };
            for (int i = 0; i < 7; i++)
            {
                var start = new Vector3(Random.Range(footprint.min.x, footprint.max.x), footprint.min.y, Random.Range(footprint.min.z, footprint.max.z));
                StartCoroutine(Rocket(start, start + new Vector3(Random.Range(-2f, 2f), Random.Range(8f, 12f), Random.Range(-2f, 2f)), colors[i % colors.Length]));
                yield return new WaitForSeconds(Random.Range(.15f, .35f));
            }
        }

        IEnumerator Rocket(Vector3 from, Vector3 to, Color color)
        {
            var root = new GameObject("Firework");
            root.transform.SetParent(rig ? rig.transform : transform, false);
            var head = Part(root.transform, "Rocket", Vector3.zero, Vector3.one * .18f, sparkMaterial, PrimitiveType.Sphere);
            var trail = head.AddComponent<TrailRenderer>();
            trail.time = .35f; trail.startWidth = .14f; trail.endWidth = 0; trail.sharedMaterial = sparkMaterial;
            trail.startColor = color; trail.endColor = new Color(color.r, color.g, color.b, 0);
            head.GetComponent<Renderer>().material.color = color;
            for (float t = 0; t < .7f; t += Time.deltaTime)
            {
                if (!head) yield break;
                head.transform.position = Vector3.Lerp(from, to, Ease(t / .7f));
                yield return null;
            }
            if (!head) yield break;
            head.SetActive(false);
            var burst = new GameObject("Burst");
            burst.transform.SetParent(root.transform, false);
            burst.transform.position = to;
            var ps = burst.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main;
            main.duration = .5f; main.loop = false; main.startLifetime = new ParticleSystem.MinMaxCurve(.9f, 1.4f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(4f, 6.5f); main.startSize = new ParticleSystem.MinMaxCurve(.25f, .45f);
            main.startColor = new ParticleSystem.MinMaxGradient(color, Color.Lerp(color, Color.white, .5f));
            main.gravityModifier = .35f; main.maxParticles = 200; main.simulationSpace = ParticleSystemSimulationSpace.World;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Sphere; shape.radius = .1f;
            var emission = ps.emission; emission.rateOverTime = 0; emission.SetBursts(new[] { new ParticleSystem.Burst(0, 110) });
            var fade = ps.colorOverLifetime; fade.enabled = true;
            var gradient = new Gradient(); gradient.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) }, new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(1, .6f), new GradientAlphaKey(0, 1) });
            fade.color = gradient;
            var drag = ps.limitVelocityOverLifetime; drag.enabled = true; drag.drag = 2.2f; drag.limit = 6f;
            var trails = ps.trails; trails.enabled = true; trails.lifetime = .25f; trails.widthOverTrail = .5f;
            var renderer = burst.GetComponent<ParticleSystemRenderer>();
            renderer.sharedMaterial = dustMaterial; renderer.trailMaterial = sparkMaterial;
            ps.Play();
            yield return new WaitForSeconds(2f);
            if (root) Destroy(root);
        }

        Transform Title(string title, Bounds footprint)
        {
            var go = new GameObject("Stage title");
            go.transform.SetParent(rig.transform, false);
            go.transform.position = new Vector3(footprint.center.x, footprint.max.y + 6f, footprint.center.z);
            var text = go.AddComponent<TextMesh>();
            text.text = title; text.font = titleFont; text.fontSize = 96; text.characterSize = .16f; text.anchor = TextAnchor.MiddleCenter;
            text.fontStyle = FontStyle.Bold; text.color = new Color(1f, .93f, .45f);
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = titleMaterial ? titleMaterial : titleFont ? titleFont.material : null;
            // A darker copy behind reads like an outline on the busy map.
            var shadow = new GameObject("Shadow"); shadow.transform.SetParent(go.transform, false); shadow.transform.localPosition = new Vector3(.1f, -.1f, .03f);
            var back = shadow.AddComponent<TextMesh>(); back.text = title; back.font = titleFont; back.fontSize = 96; back.characterSize = .16f; back.anchor = TextAnchor.MiddleCenter; back.fontStyle = FontStyle.Bold; back.color = new Color(.35f, .12f, .05f, .9f);
            shadow.GetComponent<MeshRenderer>().sharedMaterial = renderer.sharedMaterial;
            go.transform.localScale = Vector3.one * .01f;
            return go.transform;
        }

        IEnumerator TitleShow(Transform label)
        {
            var camera = Camera.main;
            for (float t = 0; t < 3.2f; t += Time.deltaTime)
            {
                if (!label) yield break;
                if (camera) label.rotation = camera.transform.rotation;
                float pop = t < .5f ? 1 + 2.2f * Mathf.Pow(t / .5f - 1, 3) + 1.2f * Mathf.Pow(t / .5f - 1, 2) : 1;
                float fade = t > 2.6f ? 1 - (t - 2.6f) / .6f : 1;
                label.localScale = Vector3.one * Mathf.Max(.01f, pop) * Mathf.Max(.01f, fade);
                label.position += Vector3.up * Time.deltaTime * .35f;
                yield return null;
            }
            if (label) label.gameObject.SetActive(false);
        }
    }
}
