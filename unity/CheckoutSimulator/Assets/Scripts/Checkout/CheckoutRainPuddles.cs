using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout
{
    // Puddles that form on the streets and sidewalks while it rains hard: irregular blobs at random spots
    // (more of them near the market, where the camera usually is), each a thin glossy film of water with
    // raindrop ripples (shader "MarketDay/Rain Puddle"). They swell in one by one while it rains and dry
    // out (shrink and fade) after the rain stops; the next shower puts them somewhere else.
    public sealed class CheckoutRainPuddles : MonoBehaviour
    {
        sealed class Puddle
        {
            public GameObject root;
            public Material material;
            public float size, grow, born, dryAt = float.PositiveInfinity, dryTime;
        }

        const int Count = 26;
        readonly List<Puddle> puddles = new List<Puddle>();
        readonly List<Rect> blocked = new List<Rect>();
        Shader shader;
        bool raining, surveyed;
        float spawnIn, rain;

        public void Initialize()
        {
            shader = Shader.Find("MarketDay/Rain Puddle");
            if (!shader) Debug.LogWarning("CHECKOUT_PUDDLES missing shader MarketDay/Rain Puddle");
        }

        public void SetRaining(bool value)
        {
            if (raining == value) return;
            raining = value;
            if (raining) { spawnIn = .8f; foreach (var p in puddles) p.dryAt = float.PositiveInfinity; return; }
            foreach (var p in puddles) { p.dryAt = Time.time + Random.Range(2f, 12f); p.dryTime = Random.Range(6f, 12f); }
        }

        void Update()
        {
            rain = Mathf.MoveTowards(rain, raining ? 1 : 0, Time.deltaTime * .5f);
            if (raining && shader)
            {
                spawnIn -= Time.deltaTime;
                if (spawnIn <= 0 && puddles.Count < Count) { Spawn(); spawnIn = Random.Range(.5f, 1.6f); }
            }
            for (int i = puddles.Count - 1; i >= 0; i--)
            {
                var p = puddles[i];
                if (!p.root) { puddles.RemoveAt(i); continue; }
                // Swell in over a few seconds; dry out by shrinking and fading.
                float grown = Mathf.SmoothStep(0, 1, Mathf.Clamp01((Time.time - p.born) / p.grow));
                float dry = float.IsPositiveInfinity(p.dryAt) ? 0 : Mathf.Clamp01((Time.time - p.dryAt) / Mathf.Max(.1f, p.dryTime));
                float scale = p.size * Mathf.Max(.02f, grown * (1 - dry * .6f));
                p.root.transform.localScale = new Vector3(scale, 1, scale);
                p.material.SetFloat("_Fade", Mathf.Clamp01(grown * 3) * (1 - dry));
                p.material.SetFloat("_Rain", rain);
                if (dry >= 1) { Destroy(p.material); Destroy(p.root.GetComponent<MeshFilter>().sharedMesh); Destroy(p.root); puddles.RemoveAt(i); }
            }
        }

        // ------------------------------------------------------------------ where
        // Paved ground only: the avenue and the two side streets with their sidewalks, never inside the
        // market, on the steps, in buildings or on the roundabout island.
        void Survey()
        {
            surveyed = true;
            blocked.Clear();
            var shell = FindAnyObjectByType<CheckoutMarketShell>();
            if (shell) { var b = shell.Footprint; blocked.Add(Rect.MinMaxRect(b.min.x - .5f, b.min.z - 3.2f, b.max.x + .5f, b.max.z + .5f)); }
            var sim = FindAnyObjectByType<MarketDay.MarketSimulation>();
            if (sim && sim.world)
                foreach (string group in new[] { "Supplied City Models", "City Establishments", "Expansion Neighborhood" })
                {
                    var g = sim.world.Find(group); if (!g) continue;
                    foreach (Transform building in g)
                    {
                        if (!building.gameObject.activeInHierarchy || building.name.Contains("vehicle") || building.name.StartsWith("Neighborhood car")) continue;
                        var renderers = building.GetComponentsInChildren<MeshRenderer>(); if (renderers.Length == 0) continue;
                        var b = renderers[0].bounds; foreach (var r in renderers) b.Encapsulate(r.bounds);
                        blocked.Add(Rect.MinMaxRect(b.min.x - .3f, b.min.z - .3f, b.max.x + .3f, b.max.z + .3f));
                    }
                }
        }

        bool Pick(out Vector3 point, out float radius)
        {
            if (!surveyed) Survey();
            radius = Random.Range(.55f, 1.35f);
            var streets = FindAnyObjectByType<CheckoutCityStreets>();
            var city = streets ? streets.cityBounds : new Bounds(Vector3.zero, new Vector3(80, 1, 90));
            for (int attempt = 0; attempt < 40; attempt++)
            {
                float x, z;
                float band = Random.value;
                // Most of them where the player looks: the avenue in front of the market.
                if (band < .5f) { x = Random.Range(-26f, 26f); z = Random.Range(CheckoutStreetLayout.AvenueCurbSouth - 3.6f, CheckoutStreetLayout.AvenueCurbNorth + 3.6f); }
                else if (band < .7f) { x = Random.Range(city.min.x + 3, city.max.x - 3); z = Random.Range(CheckoutStreetLayout.AvenueCurbSouth - 3.6f, CheckoutStreetLayout.AvenueCurbNorth + 3.6f); }
                else { float side = Random.value < .5f ? -1 : 1; x = side * Random.Range(CheckoutStreetLayout.LocalCurbInner - 3.6f, CheckoutStreetLayout.LocalCurbOuter + 3.6f); z = Random.Range(city.min.z + 4, city.max.z - 4); }
                var c = new Vector2(x - CheckoutStreetLayout.Circle.x, z - CheckoutStreetLayout.Circle.y);
                if (c.magnitude < 4.4f + radius) continue;
                bool bad = false;
                var area = new Rect(x - radius, z - radius, radius * 2, radius * 2);
                foreach (var r in blocked) if (r.Overlaps(area)) { bad = true; break; }
                if (bad) continue;
                foreach (var p in puddles)
                {
                    if (!p.root) continue;
                    var d = p.root.transform.position - new Vector3(x, 0, z); d.y = 0;
                    if (d.magnitude < p.size + radius + .4f) { bad = true; break; }
                }
                if (bad) continue;
                float y = .15f;
                if (NavMesh.SamplePosition(new Vector3(x, .15f, z), out var hit, .8f, NavMesh.AllAreas) && hit.position.y < .5f) y = hit.position.y;
                point = new Vector3(x, y + .012f, z);
                return true;
            }
            point = default;
            return false;
        }

        // ------------------------------------------------------------------ what
        void Spawn()
        {
            if (!Pick(out var at, out float radius)) return;
            var root = new GameObject("Rain puddle");
            root.transform.SetParent(transform, true);
            root.transform.SetPositionAndRotation(at, Quaternion.Euler(0, Random.Range(0f, 360f), 0));
            root.AddComponent<MeshFilter>().sharedMesh = Blob(Random.Range(1f, 1.7f));
            var renderer = root.AddComponent<MeshRenderer>();
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            var material = new Material(shader) { name = "Rain puddle" };
            material.SetFloat("_Fade", 0);
            renderer.sharedMaterial = material;
            puddles.Add(new Puddle { root = root, material = material, size = radius, born = Time.time, grow = Random.Range(3f, 7f) });
        }

        // An irregular unit blob (radius about 1, stretched along x): a fan of rings whose outer edge wobbles
        // with a few random harmonics. Vertex alpha: 1 inside, 0 at the rim.
        static Mesh Blob(float stretch)
        {
            const int Sides = 48, Rings = 4;
            var phases = new float[4]; var amps = new float[4];
            for (int k = 0; k < 4; k++) { phases[k] = Random.Range(0f, Mathf.PI * 2); amps[k] = Random.Range(.04f, .16f) / (k + 1); }
            float Edge(float a)
            {
                float r = 1;
                for (int k = 0; k < 4; k++) r += amps[k] * Mathf.Sin(a * (k + 2) + phases[k]);
                return r;
            }
            var vertices = new List<Vector3> { Vector3.zero };
            var colors = new List<Color> { new Color(1, 1, 1, 1) };
            var triangles = new List<int>();
            for (int ring = 1; ring <= Rings; ring++)
            {
                float t = ring / (float)Rings;
                // Most of the surface is open water; the last ring is the soft wet edge.
                float along = ring == Rings ? 1 : t * .82f;
                float alpha = ring == Rings ? 0 : ring == Rings - 1 ? .55f : 1;
                for (int s = 0; s < Sides; s++)
                {
                    float a = s * Mathf.PI * 2 / Sides, r = Edge(a) * along;
                    vertices.Add(new Vector3(Mathf.Cos(a) * r * stretch, 0, Mathf.Sin(a) * r));
                    colors.Add(new Color(1, 1, 1, alpha));
                }
            }
            for (int s = 0; s < Sides; s++) { triangles.Add(0); triangles.Add(1 + (s + 1) % Sides); triangles.Add(1 + s); }
            for (int ring = 1; ring < Rings; ring++)
            {
                int inner = 1 + (ring - 1) * Sides, outer = 1 + ring * Sides;
                for (int s = 0; s < Sides; s++)
                {
                    int s1 = (s + 1) % Sides;
                    triangles.Add(inner + s); triangles.Add(inner + s1); triangles.Add(outer + s);
                    triangles.Add(inner + s1); triangles.Add(outer + s1); triangles.Add(outer + s);
                }
            }
            var mesh = new Mesh { name = "Rain puddle" };
            mesh.SetVertices(vertices); mesh.SetColors(colors); mesh.SetTriangles(triangles, 0);
            var normals = new Vector3[vertices.Count]; var tangents = new Vector4[vertices.Count];
            for (int i = 0; i < normals.Length; i++) { normals[i] = Vector3.up; tangents[i] = new Vector4(1, 0, 0, 1); }
            mesh.normals = normals; mesh.tangents = tangents;
            mesh.RecalculateBounds();
            return mesh;
        }

        void OnDestroy()
        {
            foreach (var p in puddles) if (p.material) Destroy(p.material);
        }
    }
}
