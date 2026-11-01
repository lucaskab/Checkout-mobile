using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using MarketDay;

namespace Checkout
{
    // Effects on the map for a conquest (desktop/celebration.ts), in the spirit of Township's and Hay Day's new areas:
    // the camera glides over the lot, a cloud of dust puffs up where the ruin stood, a column of golden light rises,
    // a ring sweeps the ground, sparkles twinkle and confetti flies. Buying a lot pops its padlock open (it jumps,
    // spins and vanishes in sparkles). Everything is generated here (soft textures, meshes and particles), nothing
    // stays in the scene afterwards.
    public class CheckoutConquestFx : MonoBehaviour
    {
        static CheckoutConquestFx instance;
        public static CheckoutConquestFx Instance
        {
            get
            {
                if (!instance) instance = new GameObject("Conquest FX").AddComponent<CheckoutConquestFx>();
                return instance;
            }
        }

        Material puffMat, starMat, flatMat, beamMat, ringMat;
        MarketSimulation simulation;
        (Vector3 focus, float zoom)? cameraBefore;

        // ------------------------------------------------------------------ the big one: a lot is the player's
        public float LotCleared(Vector3 center, float width, float depth, bool moveCamera)
        {
            cinematicTarget = false;
            StartCoroutine(LotRoutine(center, width, depth, moveCamera));
            return moveCamera ? 2.1f : 1.5f;
        }

        IEnumerator LotRoutine(Vector3 center, float width, float depth, bool moveCamera)
        {
            if (moveCamera) yield return Glide(center, Mathf.Clamp(Mathf.Max(width, depth) * 1.35f, 14f, 26f), .75f, true);
            float size = Mathf.Max(width, depth);
            Dust(center, width, depth);
            StartCoroutine(Beam(center, Mathf.Min(width, depth) * .38f, 2.4f));
            StartCoroutine(Ring(center, size * .8f, 1.1f));
            yield return new WaitForSeconds(.25f);
            Sparkles(center, width, depth, 34);
            Confetti(center + Vector3.up * .5f, 110, 1f);
        }

        // Padlock of a lot that was just bought: a copy jumps up, spins, swells and bursts into sparkles.
        public void LockPop(Transform badge, Texture openTexture)
        {
            if (!badge) return;
            var copy = Instantiate(badge.gameObject, badge.parent);
            copy.name = "Padlock pop";
            foreach (var c in copy.GetComponentsInChildren<Collider>()) Destroy(c);
            var r = copy.GetComponent<Renderer>();
            if (r && openTexture) { var m = new Material(r.sharedMaterial) { mainTexture = openTexture }; r.sharedMaterial = m; }
            copy.SetActive(true);
            StartCoroutine(LockRoutine(copy.transform));
        }

        IEnumerator LockRoutine(Transform t)
        {
            var from = t.position; var scale = t.localScale; var rot = t.rotation;
            for (float k = 0; k < 1; k += Time.deltaTime / .7f)
            {
                if (!t) yield break;
                float up = Mathf.Sin(k * Mathf.PI * .5f) * 2.4f;
                float swell = k < .35f ? Mathf.Lerp(1, 1.45f, k / .35f) : Mathf.Lerp(1.45f, 0, (k - .35f) / .65f);
                t.position = from + Vector3.up * up;
                t.localScale = scale * swell;
                t.rotation = rot * Quaternion.Euler(0, 0, Mathf.Sin(k * Mathf.PI * 3) * 14);
                yield return null;
            }
            var at = t ? t.position : from;
            if (t) Destroy(t.gameObject);
            Sparkles(at, 2.5f, 2.5f, 18);
            Confetti(at, 40, .6f);
        }

        // ------------------------------------------------------------------ camera
        bool CameraFree()
        {
            if (!simulation) simulation = FindAnyObjectByType<MarketSimulation>();
            return simulation && simulation.view && !CheckoutBuildMode.Open && !CheckoutLotView.Open && !CheckoutMapEditor.Open;
        }

        bool cinematicTarget;
        IEnumerator Glide(Vector3 point, float zoom, float seconds, bool remember)
        {
            if (!CameraFree()) yield break;
            var from = simulation.CameraState;
            if (remember && cameraBefore == null) cameraBefore = from;
            for (float k = 0; k < 1; k += CheckoutUiKit.Dt / seconds)
            {
                float e = k * k * (3 - 2 * k);
                simulation.FocusCinematic(Vector3.Lerp(from.focus, point, e), Mathf.Lerp(from.zoom, zoom, e));
                yield return null;
            }
            if (cinematicTarget) simulation.FocusCinematic(point, zoom); else simulation.Focus(point, zoom);
        }

        /// <summary>Glides the camera to `point` (remembered for RestoreCamera). The evolution reveal uses it.</summary>
        public Coroutine FocusOn(Vector3 point, float zoom, float seconds)
        {
            if (!CameraFree()) return null;
            MarketSimulation.Cinematic = true; cinematicTarget = true;
            return StartCoroutine(Glide(point, zoom, seconds, true));
        }
        public void PuffAt(Vector3 at, float size, int count)
        {
            var ps = System("Puff", at, Puff());
            var main = ps.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(.35f, .6f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.3f * size, 1.1f * size);
            main.startSize = new ParticleSystem.MinMaxCurve(.25f * size, .55f * size);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1f, .97f, .9f, .75f), new Color(.93f, .88f, .78f, .6f));
            main.gravityModifier = -.02f; main.maxParticles = count + 4;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Circle; shape.radius = .12f * size;
            var emission = ps.emission; emission.rateOverTime = 0; emission.SetBursts(new[] { new ParticleSystem.Burst(0, (short)count) });
            Fade(ps, .05f); ps.Play(); Destroy(ps.gameObject, 1f);
        }

        // The evolution reveal (CheckoutEvolutionReveal): the same effects, called from outside.
        public void SparkleAt(Vector3 center, float width, float depth, int count) => Sparkles(center, width, depth, count);
        public void DustAt(Vector3 center, float width, float depth) => Dust(center, width, depth);
        public void ConfettiAt(Vector3 at, int count, float power, Color[] colors = null) => Confetti(at, count, power, colors);
        public void LightRays(Vector3 center, float radius, float seconds) { StartCoroutine(Beam(center, radius, seconds)); StartCoroutine(Ring(center, radius * 2.2f, seconds * .6f)); }

        /// <summary>Back to where the player was looking before the celebration flew the camera away.</summary>
        public void RestoreCamera()
        {
            if (cameraBefore == null) { MarketSimulation.Cinematic = false; return; }
            var back = cameraBefore.Value; cameraBefore = null;
            StartCoroutine(GlideBack(back.focus, back.zoom));
        }

        IEnumerator GlideBack(Vector3 focus, float zoom)
        {
            cinematicTarget = false;
            yield return Glide(focus, zoom, .6f, false);
            MarketSimulation.Cinematic = false;
        }

        // ------------------------------------------------------------------ effects
        void Dust(Vector3 center, float width, float depth)
        {
            var ps = System("Dust", center + Vector3.up * .3f, Puff());
            var main = ps.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(1.3f, 2.2f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.6f, 2.4f);
            main.startSize = new ParticleSystem.MinMaxCurve(1.4f, 3.2f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0, 6.28f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(.93f, .86f, .72f, .8f), new Color(.78f, .66f, .5f, .75f));
            main.gravityModifier = -.04f;
            main.maxParticles = 140;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Box; shape.scale = new Vector3(width * .75f, depth * .75f, .3f);
            var emission = ps.emission; emission.rateOverTime = 0;
            emission.SetBursts(new[] { new ParticleSystem.Burst(0, 70), new ParticleSystem.Burst(.2f, 30) });
            var grow = ps.sizeOverLifetime; grow.enabled = true; grow.size = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, .7f, 1, 1.6f));
            var spin = ps.rotationOverLifetime; spin.enabled = true; spin.z = new ParticleSystem.MinMaxCurve(-.6f, .6f);
            Fade(ps, .15f);
            ps.Play();
            Destroy(ps.gameObject, 3f);
        }

        void Sparkles(Vector3 center, float width, float depth, int count)
        {
            var ps = System("Sparkles", center + Vector3.up * 1.2f, Star());
            var main = ps.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(.7f, 1.4f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(.4f, 1.6f);
            main.startSize = new ParticleSystem.MinMaxCurve(.35f, .8f);
            main.startColor = new ParticleSystem.MinMaxGradient(new Color(1, .95f, .7f), new Color(1, .82f, .35f));
            main.maxParticles = count + 10;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Box; shape.scale = new Vector3(width * .7f, depth * .7f, 2f);
            var emission = ps.emission; emission.rateOverTime = 0; emission.SetBursts(new[] { new ParticleSystem.Burst(0, (short)count) });
            var twinkle = ps.sizeOverLifetime; twinkle.enabled = true;
            twinkle.size = new ParticleSystem.MinMaxCurve(1, new AnimationCurve(new Keyframe(0, 0), new Keyframe(.25f, 1), new Keyframe(.6f, .6f), new Keyframe(1, 0)));
            ps.Play();
            Destroy(ps.gameObject, 2f);
        }

        void Confetti(Vector3 at, int count, float power, Color[] palette = null)
        {
            var ps = System("Confetti", at, Flat());
            var main = ps.main;
            main.startLifetime = new ParticleSystem.MinMaxCurve(2f, 3f);
            main.startSpeed = new ParticleSystem.MinMaxCurve(6f * power, 11f * power);
            main.startSize = new ParticleSystem.MinMaxCurve(.14f, .26f);
            main.startRotation = new ParticleSystem.MinMaxCurve(0, 6.28f);
            main.gravityModifier = .9f;
            var colors = new Gradient();
            colors.SetKeys(new[] { new GradientColorKey(new Color(.88f, .33f, .2f), 0), new GradientColorKey(new Color(.95f, .69f, .24f), .25f), new GradientColorKey(new Color(.18f, .55f, .68f), .5f), new GradientColorKey(new Color(.36f, .65f, .22f), .75f), new GradientColorKey(new Color(.91f, .44f, .65f), 1) },
                new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(1, 1) });
            if (palette != null && palette.Length > 1)
            {
                var keys = new GradientColorKey[Mathf.Min(8, palette.Length)];
                for (int i = 0; i < keys.Length; i++) keys[i] = new GradientColorKey(palette[i], keys.Length == 1 ? 0 : i / (float)(keys.Length - 1));
                colors = new Gradient(); colors.SetKeys(keys, new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(1, 1) });
            }
            main.startColor = new ParticleSystem.MinMaxGradient(colors) { mode = ParticleSystemGradientMode.RandomColor };
            main.maxParticles = count + 10;
            var shape = ps.shape; shape.shapeType = ParticleSystemShapeType.Cone; shape.angle = 32; shape.radius = .4f;
            var emission = ps.emission; emission.rateOverTime = 0; emission.SetBursts(new[] { new ParticleSystem.Burst(0, (short)count) });
            var spin = ps.rotationOverLifetime; spin.enabled = true; spin.z = new ParticleSystem.MinMaxCurve(-6f, 6f);
            var drag = ps.limitVelocityOverLifetime; drag.enabled = true; drag.drag = 1.2f; drag.multiplyDragByParticleSize = false;
            Fade(ps, .02f);
            ps.Play();
            Destroy(ps.gameObject, 3.5f);
        }

        ParticleSystem System(string name, Vector3 at, Material material)
        {
            var go = new GameObject("Conquest " + name) { layer = 2 };
            go.transform.SetParent(transform, false);
            go.transform.position = at;
            go.transform.rotation = Quaternion.Euler(-90, 0, 0);
            var ps = go.AddComponent<ParticleSystem>();
            ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            var main = ps.main; main.playOnAwake = false; main.loop = false; main.duration = 1; main.simulationSpace = ParticleSystemSimulationSpace.World;
            main.cullingMode = ParticleSystemCullingMode.AlwaysSimulate;
            var r = go.GetComponent<ParticleSystemRenderer>(); r.sharedMaterial = material;
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return ps;
        }

        static void Fade(ParticleSystem ps, float fadeIn)
        {
            var fade = ps.colorOverLifetime; fade.enabled = true;
            var g = new Gradient();
            g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                new[] { new GradientAlphaKey(0, 0), new GradientAlphaKey(1, fadeIn), new GradientAlphaKey(1, .6f), new GradientAlphaKey(0, 1) });
            fade.color = g;
        }

        // A column of soft golden light that grows, glows and fades (two open cylinders, the inner one brighter).
        IEnumerator Beam(Vector3 center, float radius, float seconds)
        {
            var outer = Column("Light column", center, beamMat ? beamMat : (beamMat = Mat(BeamTexture())));
            var inner = Column("Light core", center, new Material(beamMat));
            var mo = outer.GetComponent<MeshRenderer>().material; var mi = inner.GetComponent<MeshRenderer>().sharedMaterial;
            for (float k = 0; k < 1; k += Time.deltaTime / seconds)
            {
                float a = k < .2f ? k / .2f : 1 - (k - .2f) / .8f;
                float r = radius * Mathf.Lerp(.3f, 1f, Mathf.Sqrt(Mathf.Min(1, k * 2.5f)));
                outer.transform.localScale = new Vector3(r, 16, r);
                inner.transform.localScale = new Vector3(r * .45f, 18, r * .45f);
                outer.transform.Rotate(0, 40 * Time.deltaTime, 0);
                mo.color = new Color(1f, .86f, .45f, .5f * a);
                mi.color = new Color(1f, .97f, .82f, .75f * a);
                yield return null;
            }
            Destroy(outer); Destroy(inner); Destroy(mo); Destroy(mi);
        }

        GameObject Column(string name, Vector3 center, Material material)
        {
            const int n = 28;
            var verts = new Vector3[(n + 1) * 2]; var uvs = new Vector2[verts.Length]; var tris = new int[n * 6];
            for (int i = 0; i <= n; i++)
            {
                float a = i * Mathf.PI * 2 / n, x = Mathf.Cos(a), z = Mathf.Sin(a);
                verts[i * 2] = new Vector3(x, 0, z); verts[i * 2 + 1] = new Vector3(x, 1, z);
                uvs[i * 2] = new Vector2((float)i / n, 0); uvs[i * 2 + 1] = new Vector2((float)i / n, 1);
                if (i < n) { int k = i * 6, v = i * 2; tris[k] = v; tris[k + 1] = v + 1; tris[k + 2] = v + 3; tris[k + 3] = v; tris[k + 4] = v + 3; tris[k + 5] = v + 2; }
            }
            var mesh = new Mesh { name = name, vertices = verts, uv = uvs, triangles = tris }; mesh.RecalculateBounds();
            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer)) { layer = 2 };
            go.transform.SetParent(transform, false); go.transform.position = center; go.transform.localScale = Vector3.zero;
            go.GetComponent<MeshFilter>().sharedMesh = mesh;
            var r = go.GetComponent<MeshRenderer>(); r.sharedMaterial = material; r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
            return go;
        }

        // A bright ring sweeping the ground from the middle of the lot to its edges.
        IEnumerator Ring(Vector3 center, float radius, float seconds)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Quad); go.name = "Ground ring"; go.layer = 2;
            Destroy(go.GetComponent<Collider>());
            go.transform.SetParent(transform, false);
            go.transform.position = center + Vector3.up * .12f; go.transform.rotation = Quaternion.Euler(90, 0, 0);
            var r = go.GetComponent<MeshRenderer>(); r.material = new Material(ringMat ? ringMat : (ringMat = Mat(RingTexture())));
            r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var m = r.material;
            for (float k = 0; k < 1; k += Time.deltaTime / seconds)
            {
                float e = 1 - (1 - k) * (1 - k);
                go.transform.localScale = Vector3.one * Mathf.Lerp(.5f, radius * 2, e);
                m.color = new Color(1f, .93f, .62f, .85f * (1 - k));
                yield return null;
            }
            Destroy(m); Destroy(go);
        }

        // ------------------------------------------------------------------ evolution confetti (3D)
        // Small two-sided pieces (strips, discs, curled serpentines, gold stars and sparkles) that tumble on their own
        // axes and flutter down; the burst covers the piece's own footprint and height (a sector gets a wide one, a shelf
        // a tight one). One pooled particle system, one material (the CheckoutConfettiArt atlas): one draw call.
        ParticleSystem confetti3d; Color confettiAccent = Color.clear;
        /// <summary>QA: what the last burst cost (pieces, ms to build the atlas when it was new, ms to emit).</summary>
        public int LastConfettiCount { get; private set; }
        public float LastConfettiSetupMs { get; private set; }
        public int ConfettiAlive => confetti3d ? confetti3d.particleCount : 0;

        /// <summary>Draws the confetti atlas for this accent over the next frames (call it as a reveal begins).</summary>
        public void WarmConfetti(Color accent) => StartCoroutine(CheckoutConfettiArt.Prepare(accent));

        public void ConfettiBurst(Bounds b, Color accent)
        {
            var watch = global::System.Diagnostics.Stopwatch.StartNew();
            var ps = ConfettiSystem(accent);
            float w = Mathf.Max(.6f, b.size.x), d = Mathf.Max(.6f, b.size.z), h = Mathf.Max(.5f, b.size.y);
            float span = Mathf.Max(w, d), lift = Mathf.Clamp(Mathf.Sqrt(h / 1.4f), .85f, 1.5f);
            int count = Mathf.Clamp(Mathf.RoundToInt(15 * w * d + 9 * h), 36, 170);
            ps.transform.position = new Vector3(b.center.x, b.min.y + h * .8f, b.center.z);
            var shape = ps.shape; shape.scale = new Vector3(w * .85f, d * .85f, h * .35f);
            shape.randomDirectionAmount = Mathf.Lerp(.25f, .45f, Mathf.InverseLerp(1.5f, 5f, span));
            var main = ps.main;
            main.startSpeed = new ParticleSystem.MinMaxCurve(2.3f * lift, 4.3f * lift);
            float size = Mathf.Clamp(Mathf.Sqrt(span) / 1.3f, .9f, 1.25f);
            main.startSize = new ParticleSystem.MinMaxCurve(.13f * size, .25f * size);
            ps.Emit(count);
            LastConfettiCount = count; LastConfettiSetupMs = (float)watch.Elapsed.TotalMilliseconds;
        }

        /// <summary>QA: emits `count` pieces far below the map and simulates `steps` frames of 1/30 s on the main thread;
        /// returns the ms per frame, then clears them (nothing is ever drawn).</summary>
        public float QaConfettiBench(int count, int steps)
        {
            var ps = ConfettiSystem(confettiAccent == Color.clear ? CheckoutConfettiArt.Gold : confettiAccent);
            ps.Clear(); ps.transform.position = new Vector3(0, -500, 0);
            var shape = ps.shape; shape.scale = new Vector3(3, 2.5f, .8f); ps.Emit(count);
            var watch = global::System.Diagnostics.Stopwatch.StartNew();
            for (int i = 0; i < steps; i++) ps.Simulate(1 / 30f, false, false, false);
            float ms = (float)watch.Elapsed.TotalMilliseconds / steps;
            ps.Clear(); ps.Play();
            return ms;
        }

        ParticleSystem ConfettiSystem(Color accent)
        {
            if (!confetti3d)
            {
                var go = new GameObject("Evolution confetti") { layer = 2 };
                go.transform.SetParent(transform, false); go.transform.rotation = Quaternion.Euler(-90, 0, 0);
                var ps = go.AddComponent<ParticleSystem>(); ps.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                var main = ps.main; main.playOnAwake = false; main.loop = true; main.duration = 5; main.simulationSpace = ParticleSystemSimulationSpace.World;
                main.cullingMode = ParticleSystemCullingMode.AlwaysSimulate; main.maxParticles = 420;
                main.startLifetime = new ParticleSystem.MinMaxCurve(2.1f, 3.1f);
                main.startRotation3D = true;
                main.startRotationX = main.startRotationY = main.startRotationZ = new ParticleSystem.MinMaxCurve(0, Mathf.PI * 2);
                main.startColor = Color.white; main.gravityModifier = .32f;
                var emission = ps.emission; emission.enabled = true; emission.rateOverTime = 0;
                var shape = ps.shape; shape.enabled = true; shape.shapeType = ParticleSystemShapeType.Box;
                // tumbling on all three axes, a side-to-side drift and air drag: it flutters down instead of falling
                var spin = ps.rotationOverLifetime; spin.enabled = true; spin.separateAxes = true;
                spin.x = new ParticleSystem.MinMaxCurve(-9, 9); spin.y = new ParticleSystem.MinMaxCurve(-7, 7); spin.z = new ParticleSystem.MinMaxCurve(-5, 5);
                var drag = ps.limitVelocityOverLifetime; drag.enabled = true; drag.limit = 50; drag.drag = 1.5f;
                drag.multiplyDragByParticleSize = false; drag.multiplyDragByParticleVelocity = false;
                var noise = ps.noise; noise.enabled = true; noise.strength = .55f; noise.frequency = .8f; noise.scrollSpeed = .6f;
                noise.quality = ParticleSystemNoiseQuality.Low; noise.octaveCount = 1; noise.damping = true;
                var fade = ps.colorOverLifetime; fade.enabled = true; var g = new Gradient();
                g.SetKeys(new[] { new GradientColorKey(Color.white, 0), new GradientColorKey(Color.white, 1) },
                    new[] { new GradientAlphaKey(1, 0), new GradientAlphaKey(1, .78f), new GradientAlphaKey(0, 1) });
                fade.color = g;
                // the atlas: one row per piece, its columns the piece turning (the gold ones flash)
                var sheet = ps.textureSheetAnimation; sheet.enabled = true; sheet.mode = ParticleSystemAnimationMode.Grid;
                sheet.numTilesX = CheckoutConfettiArt.Cols; sheet.numTilesY = CheckoutConfettiArt.Rows;
                sheet.animation = ParticleSystemAnimationType.SingleRow; sheet.rowMode = ParticleSystemAnimationRowMode.Random;
                sheet.frameOverTime = new ParticleSystem.MinMaxCurve(1, AnimationCurve.Linear(0, 0, 1, 1)); sheet.cycleCount = 5;
                sheet.startFrame = new ParticleSystem.MinMaxCurve(0, CheckoutConfettiArt.Cols - .01f);
                var r = go.GetComponent<ParticleSystemRenderer>();
                r.renderMode = ParticleSystemRenderMode.Mesh; r.mesh = Resources.GetBuiltinResource<Mesh>("Quad.fbx");
                r.alignment = ParticleSystemRenderSpace.World; r.sortMode = ParticleSystemSortMode.None;
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off; r.receiveShadows = false;
                confetti3d = ps; ps.Play();
            }
            if (accent != confettiAccent || !confetti3d.GetComponent<ParticleSystemRenderer>().sharedMaterial)
            {
                confettiAccent = accent;
                confetti3d.GetComponent<ParticleSystemRenderer>().sharedMaterial = CheckoutConfettiArt.Material(accent);
            }
            if (!confetti3d.isPlaying) confetti3d.Play();
            return confetti3d;
        }

        // ------------------------------------------------------------------ generated art
        static Material Mat(Texture2D texture) => new Material(Shader.Find("Sprites/Default")) { mainTexture = texture, renderQueue = 3100 };
        Material Puff() => puffMat ? puffMat : (puffMat = Mat(PuffTexture()));
        Material Star()
        {
            if (starMat) return starMat;
            var t = Resources.Load<Texture2D>("CheckoutDesktop/Game/sparkle");
            return starMat = Mat(t ? t : PuffTexture());
        }
        Material Flat() => flatMat ? flatMat : (flatMat = Mat(Texture2D.whiteTexture));

        static Texture2D PuffTexture()
        {
            const int n = 96; var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp }; var px = new Color32[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float dx = (x + .5f) / n * 2 - 1, dy = (y + .5f) / n * 2 - 1, d = Mathf.Sqrt(dx * dx + dy * dy);
                float lumps = .82f + .18f * Mathf.PerlinNoise(x * .09f, y * .09f);
                float a = Mathf.Clamp01((lumps - d) / .45f); a = a * a * (3 - 2 * a);
                byte shade = (byte)(220 + 35 * Mathf.Clamp01(1 - dy));
                px[y * n + x] = new Color32(shade, shade, shade, (byte)(a * 255));
            }
            t.SetPixels32(px); t.Apply(); return t;
        }

        static Texture2D BeamTexture()
        {
            const int w = 8, h = 128; var t = new Texture2D(w, h, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp }; var px = new Color32[w * h];
            for (int y = 0; y < h; y++)
            {
                float v = (y + .5f) / h; float a = Mathf.Clamp01(1 - v) * Mathf.Clamp01(1 - v) * Mathf.Clamp01(v * 12);
                for (int x = 0; x < w; x++) px[y * w + x] = new Color32(255, 255, 255, (byte)(a * 255));
            }
            t.SetPixels32(px); t.Apply(); return t;
        }

        static Texture2D RingTexture()
        {
            const int n = 128; var t = new Texture2D(n, n, TextureFormat.RGBA32, false) { wrapMode = TextureWrapMode.Clamp }; var px = new Color32[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float dx = (x + .5f) / n * 2 - 1, dy = (y + .5f) / n * 2 - 1, d = Mathf.Sqrt(dx * dx + dy * dy);
                float a = Mathf.Clamp01(1 - Mathf.Abs(d - .86f) / .12f); a = a * a;
                px[y * n + x] = new Color32(255, 255, 255, (byte)(a * 255));
            }
            t.SetPixels32(px); t.Apply(); return t;
        }
    }

    /// <summary>The evolution confetti's art (claude/evolucoes-recompensas.md, Lucas 01/11): one atlas of small pieces in
    /// navy, gold, cream, white and the sector's accent (strips, discs, curled serpentines, gold stars and sparkles); each
    /// row is one piece, its columns the piece turning in the light (gold ones flash). The 3D burst uses it as a texture
    /// sheet, the card's 2D confetti as sprites, so both look alike. Generated once per accent colour.</summary>
    public static class CheckoutConfettiArt
    {
        public const int Cols = 8, Rows = 16, Cell = 48;
        public static readonly Color Navy = new Color32(0x1D, 0x2B, 0x4F, 255), Gold = new Color32(0xF0, 0xB4, 0x3C, 255),
            Cream = new Color32(0xF7, 0xE8, 0xC8, 255), White = new Color32(0xFA, 0xFA, 0xF7, 255);
        enum Shape { Strip, Disc, Curl, Star, Sparkle }
        // colour: 0 navy, 1 gold, 2 cream, 3 white, 4 accent; metal: the gold flash
        static readonly (Shape shape, int colour, bool metal)[] Layout = {
            (Shape.Strip, 0, false), (Shape.Strip, 1, true), (Shape.Strip, 2, false), (Shape.Strip, 3, false), (Shape.Strip, 4, false),
            (Shape.Strip, 1, true), (Shape.Strip, 4, false), (Shape.Disc, 3, false), (Shape.Disc, 1, true), (Shape.Disc, 2, false),
            (Shape.Disc, 4, false), (Shape.Curl, 1, true), (Shape.Curl, 4, false), (Shape.Curl, 3, false), (Shape.Star, 1, true),
            (Shape.Sparkle, 1, true) };
        public static int RowCount => Layout.Length;

        /// <summary>The accent of a sector (its signage colour); the shelves have none (gold).</summary>
        public static Color AccentFor(string kind, string targetId)
        {
            if (kind != "sector") return Gold;
            switch (targetId)
            {
                case "padaria": return new Color32(0xD9, 0x7A, 0x2B, 255);
                case "queijaria": return new Color32(0xE8, 0x9F, 0x2A, 255);
                case "acougue": return new Color32(0xC8, 0x40, 0x2F, 255);
                case "bebidas": return new Color32(0x2E, 0x8C, 0xAE, 255);
                case "peixaria": return new Color32(0x3B, 0xA3, 0xB8, 255);
                case "sorvetes": return new Color32(0xE8, 0x6F, 0xA6, 255);
                case "adega": return new Color32(0x8E, 0x2F, 0x4F, 255);
                default: return new Color32(0xE1, 0x55, 0x33, 255);
            }
        }

        static readonly Dictionary<Color, Texture2D> atlases = new Dictionary<Color, Texture2D>();
        static readonly Dictionary<Color, Material> materials = new Dictionary<Color, Material>();
        static readonly Dictionary<(Color, int, int), Sprite> sprites = new Dictionary<(Color, int, int), Sprite>();
        /// <summary>QA: ms the last new atlas took to draw.</summary>
        public static float LastAtlasMs { get; private set; }

        public static Material Material(Color accent)
        {
            if (materials.TryGetValue(accent, out var m) && m) return m;
            m = new Material(Shader.Find("Sprites/Default")) { mainTexture = Atlas(accent), renderQueue = 3100, name = "Evolution confetti" };
            materials[accent] = m; return m;
        }

        /// <summary>Piece `row` turned to `col` (0..Cols-1), as a sprite for the card.</summary>
        public static Sprite Sprite(Color accent, int row, int col)
        {
            var key = (accent, row, col);
            if (sprites.TryGetValue(key, out var s) && s) return s;
            var tex = Atlas(accent);
            s = UnityEngine.Sprite.Create(tex, new Rect(col * Cell, (Rows - 1 - row) * Cell, Cell, Cell), new Vector2(.5f, .5f), 100);
            sprites[key] = s; return s;
        }
        public static bool IsStar(int row) => Layout[row].shape == Shape.Star || Layout[row].shape == Shape.Sparkle;

        /// <summary>A gold five-point star (the card's tier pips).</summary>
        public static Sprite StarSprite(bool filled)
        {
            var key = (filled ? Color.white : Color.black, -1, -1);
            if (sprites.TryGetValue(key, out var s) && s) return s;
            const int n = 96; var tex = new Texture2D(n, n, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Clamp, name = "Tier pip" };
            var px = new Color32[n * n];
            for (int y = 0; y < n; y++) for (int x = 0; x < n; x++)
            {
                float cover = 0;
                for (int i = 0; i < 4; i++) for (int j = 0; j < 4; j++)
                { float u = ((x + (i + .5f) / 4) / n) * 2 - 1, v = ((y + (j + .5f) / 4) / n) * 2 - 1; if (InStar(u, v * 1.02f + .04f, .94f, .42f)) cover++; }
                cover /= 16;
                float uu = (x + .5f) / n * 2 - 1, vv = (y + .5f) / n * 2 - 1;
                bool inner = InStar(uu, vv * 1.02f + .04f, .74f, .33f);
                Color c = filled ? (inner ? Color.Lerp(Gold, new Color(1, .93f, .6f), Mathf.Clamp01(.55f + vv * .5f)) : new Color(.72f, .48f, .12f))
                                 : (inner ? new Color(1, 1, 1, .16f) : new Color(1, 1, 1, .55f));
                px[y * n + x] = new Color(c.r, c.g, c.b, c.a * cover);
            }
            tex.SetPixels32(px); tex.Apply(true);
            s = UnityEngine.Sprite.Create(tex, new Rect(0, 0, n, n), new Vector2(.5f, .5f), 100);
            sprites[key] = s; return s;
        }

        // The atlas is drawn row by row: Prepare() spreads it over frames from the start of a reveal (no hitch at the pop);
        // anything that needs it at once finishes the rows left.
        sealed class AtlasJob { public Color32[] px; public int row; public float ms; }
        static readonly Dictionary<Color, AtlasJob> jobs = new Dictionary<Color, AtlasJob>();
        public static IEnumerator Prepare(Color accent)
        {
            while (!atlases.ContainsKey(accent))
            {
                var job = Job(accent); DrawRow(job, accent);
                if (job.row >= Rows) { Atlas(accent); yield break; }
                yield return null;
            }
        }
        static AtlasJob Job(Color accent)
        {
            if (!jobs.TryGetValue(accent, out var job)) jobs[accent] = job = new AtlasJob { px = new Color32[Cols * Cell * Rows * Cell] };
            return job;
        }

        static Texture2D Atlas(Color accent)
        {
            if (atlases.TryGetValue(accent, out var t) && t) return t;
            var job = Job(accent);
            while (job.row < Rows) DrawRow(job, accent);
            var watch = global::System.Diagnostics.Stopwatch.StartNew();
            t = new Texture2D(Cols * Cell, Rows * Cell, TextureFormat.RGBA32, true) { wrapMode = TextureWrapMode.Clamp, filterMode = FilterMode.Trilinear, name = "Evolution confetti" };
            t.SetPixels32(job.px); t.Apply(true, false);
            atlases[accent] = t; jobs.Remove(accent); LastAtlasMs = job.ms + (float)watch.Elapsed.TotalMilliseconds;
            return t;
        }

        static void DrawRow(AtlasJob job, Color accent)
        {
            if (job.row >= Rows) return;
            var watch = global::System.Diagnostics.Stopwatch.StartNew();
            int W = Cols * Cell, row = job.row; var px = job.px;
            Color[] palette = { Navy, Gold, Cream, White, accent };
            var (shape, colour, metal) = Layout[row];
            for (int col = 0; col < Cols; col++)
            {
                float phase = col / (float)Cols * Mathf.PI * 2;
                int ox = col * Cell, oy = (Rows - 1 - row) * Cell;
                for (int y = 0; y < Cell; y++) for (int x = 0; x < Cell; x++)
                {
                    float u = (x + .5f) / Cell * 2 - 1, v = (y + .5f) / Cell * 2 - 1;
                    float cover = Cover(shape, u, v);
                    if (cover <= 0) { px[(oy + y) * W + ox + x] = new Color32(0, 0, 0, 0); continue; }
                    bool edge = Cover(shape, u * 1.12f, v * 1.12f) < .5f;   // a rim, so tiny pieces stay crisp
                    var c = palette[colour];
                    float light = metal ? .8f + .24f * Mathf.Cos(phase) : .82f + .18f * Mathf.Cos(phase);
                    light *= 1 + .1f * (v - u) * .5f;                                     // light from the top left
                    if (shape == Shape.Curl) light *= .84f + .16f * Mathf.Cos(v * Mathf.PI * 2.4f + phase);
                    var col3 = new Color(c.r * light, c.g * light, c.b * light);
                    if (metal)
                    {
                        float band = Mathf.Exp(-Mathf.Pow((u + v) * .7f - 1.7f * Mathf.Sin(phase), 2) * 5);   // a sheen sweeping over
                        float flash = Mathf.Pow(Mathf.Max(0, Mathf.Cos(phase)), 14);                         // the moment it faces the light
                        col3 = Color.Lerp(col3, new Color(1, .97f, .84f), Mathf.Max(band * .5f, flash * .65f));
                    }
                    if (edge) col3 *= colour == 0 ? 1.25f : .84f;
                    px[(oy + y) * W + ox + x] = new Color(Mathf.Clamp01(col3.r), Mathf.Clamp01(col3.g), Mathf.Clamp01(col3.b), cover);
                }
            }
            job.row++; job.ms += (float)watch.Elapsed.TotalMilliseconds;
        }

        // How much of the pixel at (u, v) (-1..1 in the cell) the piece covers, anti-aliased over about one pixel.
        static float Cover(Shape shape, float u, float v)
        {
            const float px = 2f / Cell;
            switch (shape)
            {
                case Shape.Strip:
                {   // a thin rounded rectangle, a little skewed so it is not a perfect bar
                    float x = Mathf.Abs(u + v * .08f) - .25f, y = Mathf.Abs(v) - .78f;
                    float dist = Mathf.Min(Mathf.Max(x, y), 0) + new Vector2(Mathf.Max(x, 0), Mathf.Max(y, 0)).magnitude - .04f;
                    return Mathf.Clamp01(.5f - dist / px);
                }
                case Shape.Disc:
                    return Mathf.Clamp01(.5f - (new Vector2(u, v * 1.08f).magnitude - .5f) / px);
                case Shape.Curl:
                {   // a serpentine: a band along a sine, rounded at the ends
                    float vv = Mathf.Clamp(v, -.78f, .78f), f = .34f * Mathf.Sin(vv * Mathf.PI * 1.3f), df = .34f * Mathf.PI * 1.3f * Mathf.Cos(vv * Mathf.PI * 1.3f);
                    float dist = new Vector2((u - f) / Mathf.Sqrt(1 + df * df), v - vv).magnitude - .12f;
                    return Mathf.Clamp01(.5f - dist / px);
                }
                case Shape.Star:
                {
                    float cover = 0;
                    for (int i = 0; i < 3; i++) for (int j = 0; j < 3; j++) if (InStar(u + (i - 1) * px / 3, v + .06f + (j - 1) * px / 3, .82f, .36f)) cover++;
                    return cover / 9;
                }
                default:
                {   // a four-point sparkle (an astroid)
                    float k = Mathf.Pow(Mathf.Pow(Mathf.Abs(u) / .85f, .6f) + Mathf.Pow(Mathf.Abs(v) / .85f, .6f), 1 / .6f);
                    return Mathf.Clamp01((1 - k) / (px * 1.6f));
                }
            }
        }

        static bool InStar(float u, float v, float outer, float inner)
        {
            float a = Mathf.Atan2(u, v), r = Mathf.Sqrt(u * u + v * v);
            if (r > outer) return false; if (r < inner) return true;
            // the star's edge between an outer point and the next inner corner (a straight line)
            float seg = Mathf.PI * 2 / 10; float k = Mathf.Repeat(a + seg, seg * 2) - seg;     // -seg..seg, 0 at a point
            float ka = Mathf.Abs(k);
            var p1 = new Vector2(0, outer); var p2 = new Vector2(Mathf.Sin(seg), Mathf.Cos(seg)) * inner;
            var p = new Vector2(Mathf.Sin(ka), Mathf.Cos(ka)) * r;
            float cross = (p2.x - p1.x) * (p.y - p1.y) - (p2.y - p1.y) * (p.x - p1.x);
            return cross <= 0;
        }
    }
}
