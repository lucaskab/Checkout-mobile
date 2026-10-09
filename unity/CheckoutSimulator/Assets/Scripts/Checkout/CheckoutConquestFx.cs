using System.Collections;
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

        IEnumerator Glide(Vector3 point, float zoom, float seconds, bool remember)
        {
            if (!CameraFree()) yield break;
            var from = simulation.CameraState;
            if (remember && cameraBefore == null) cameraBefore = from;
            for (float k = 0; k < 1; k += Time.unscaledDeltaTime / seconds)
            {
                float e = k * k * (3 - 2 * k);
                simulation.Focus(Vector3.Lerp(from.focus, point, e), Mathf.Lerp(from.zoom, zoom, e));
                yield return null;
            }
            simulation.Focus(point, zoom);
        }

        /// <summary>Back to where the player was looking before the celebration flew the camera away.</summary>
        public void RestoreCamera()
        {
            if (cameraBefore == null) return;
            var back = cameraBefore.Value; cameraBefore = null;
            StartCoroutine(Glide(back.focus, back.zoom, .6f, false));
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

        void Confetti(Vector3 at, int count, float power)
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
}
