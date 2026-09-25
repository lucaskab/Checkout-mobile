using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace Checkout
{
    public sealed class CheckoutRainPuddles : MonoBehaviour
    {
        sealed class Puddle
        {
            public GameObject root;
            public SpriteRenderer surface;
            public float dryAt = float.PositiveInfinity;
            public float fadeDuration;
        }

        readonly List<Puddle> puddles = new List<Puddle>();
        Sprite[] variations = System.Array.Empty<Sprite>();
        readonly Vector3[] locations =
        {
            new Vector3(-7.3f, .36f, -11.4f), new Vector3(-4.5f, .36f, -12.1f),
            new Vector3(-1.5f, .36f, -11.2f), new Vector3(2.1f, .36f, -12.4f),
            new Vector3(5.8f, .36f, -11.2f), new Vector3(9.8f, .36f, -7.1f),
            new Vector3(11.2f, .36f, -3.6f), new Vector3(10.9f, .36f, .2f),
            new Vector3(11.4f, .36f, 4.3f), new Vector3(8.5f, .36f, 10.8f),
            new Vector3(4.8f, .36f, 11.5f), new Vector3(1f, .36f, 10.9f),
            new Vector3(-3.4f, .36f, 11.6f), new Vector3(-7.4f, .36f, 10.8f),
            new Vector3(-10.7f, .36f, 6.2f), new Vector3(-11.1f, .36f, 1.8f),
            new Vector3(-10.6f, .36f, -3.6f), new Vector3(-9.8f, .36f, -7.4f)
        };

        bool raining;
        int nextLocation;
        float spawnIn;

        public void Initialize()
        {
            variations = Resources.LoadAll<Texture2D>("RainPuddles")
                .OrderBy(texture => texture.name)
                .Select(texture => Sprite.Create(texture, new Rect(0, 0, texture.width, texture.height), new Vector2(.5f, .5f), 1024))
                .ToArray();
        }

        public void SetRaining(bool value)
        {
            if (raining == value) return;
            raining = value;
            if (raining)
            {
                spawnIn = 1.2f;
                foreach (var puddle in puddles)
                {
                    puddle.dryAt = float.PositiveInfinity;
                    var tint = puddle.surface.color;
                    tint.a = .82f;
                    puddle.surface.color = tint;
                }
                return;
            }

            foreach (var puddle in puddles)
            {
                puddle.dryAt = Time.time + Random.Range(3f, 13f);
                puddle.fadeDuration = Random.Range(4f, 8f);
            }
        }

        void Update()
        {
            if (raining)
            {
                spawnIn -= Time.deltaTime;
                if (spawnIn <= 0)
                {
                    SpawnNext();
                    spawnIn = 2.4f;
                }
            }

            for (int i = puddles.Count - 1; i >= 0; i--)
            {
                var puddle = puddles[i];
                if (!puddle.root) { puddles.RemoveAt(i); continue; }
                if (raining || float.IsPositiveInfinity(puddle.dryAt)) continue;

                float fade = Mathf.Clamp01((Time.time - puddle.dryAt) / Mathf.Max(.1f, puddle.fadeDuration));
                var tint = puddle.surface.color;
                tint.a = 1 - fade;
                puddle.surface.color = tint;
                if (fade >= 1)
                {
                    Destroy(puddle.root);
                    puddles.RemoveAt(i);
                }
            }
        }

        void SpawnNext()
        {
            if (variations.Length == 0 || puddles.Count(puddle => puddle.root) >= locations.Length) return;
            for (int attempts = 0; attempts < locations.Length; attempts++)
            {
                int index = nextLocation++ % locations.Length;
                if (puddles.Any(puddle => puddle.root && puddle.root.name == "Rain puddle " + index)) continue;

                var root = new GameObject("Rain puddle " + index);
                root.transform.SetParent(transform, true);
                root.transform.position = locations[index];
                root.transform.rotation = Quaternion.Euler(-90, 0, 0);
                var renderer = root.AddComponent<SpriteRenderer>();
                renderer.sprite = variations[index % variations.Length];
                renderer.color = new Color(.78f, .92f, .97f, .82f);
                renderer.sortingOrder = -1;
                float size = index % 3 == 0 ? 1.12f : index % 3 == 1 ? .78f : .94f;
                root.transform.localScale = new Vector3(size, size, 1);
                puddles.Add(new Puddle { root = root, surface = renderer });
                return;
            }
        }

        void OnDestroy()
        {
            foreach (var sprite in variations) if (sprite) Destroy(sprite);
        }
    }
}
