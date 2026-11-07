using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // The snow on the city during the "nevasca" event (Lucas 06/11: "a maioria dos lugares fica com neve por cima da
    // calçada... óbvio que não dentro do mercado"). The outdoor surface shaders (Soft Painted, City Tiles, Painted
    // Terrain Tiles, City Park Triplanar, Painted Standard) include CheckoutPaint/CheckoutSnow.cginc, which whitens the
    // faces looking up by the global _CheckoutSnow; here it settles over ~12 s (patchy first) and melts in ~4 s when
    // the event ends. The shop floor and its walls (_CheckoutSnowCut) stay clear: the market has a roof.
    // The city's buildings, trees and cars use the built-in Standard shader: while it snows their opaque Standard
    // materials (outside the shop) are swapped for a copy with "MarketDay/Snowy Standard" (the same look plus the
    // snow), new ones every few seconds (cars that drive in), and put back once the snow has melted.
    public class CheckoutSnowCover : MonoBehaviour
    {
        static readonly int Amount = Shader.PropertyToID("_CheckoutSnow"), Cut = Shader.PropertyToID("_CheckoutSnowCut");
        float level, target;
        public float Level => level;

        public void SetSnowing(bool on, bool instant = false)
        {
            target = on ? 1 : 0;
            if (on) nextScan = 0;
            if (instant) level = target;
            enabled = true; Apply();
        }

        void Update()
        {
            level = Mathf.MoveTowards(level, target, Time.deltaTime / (target > level ? 12f : 4f));
            Apply();
            if (target > 0 && Time.unscaledTime >= nextScan) { nextScan = Time.unscaledTime + 3f; Dress(); }
            if (level == 0 && target == 0) { Undress(); enabled = false; }
        }

        // ------------------------------------------------------------------ the city's Standard materials
        Shader snowy;
        float nextScan;
        readonly Dictionary<Material, Material> snowyOf = new Dictionary<Material, Material>();
        readonly Dictionary<Material, Material> originalOf = new Dictionary<Material, Material>();
        readonly HashSet<Renderer> dressed = new HashSet<Renderer>();
        readonly List<Material> mats = new List<Material>();

        void Dress()
        {
            if (!snowy) snowy = Shader.Find("MarketDay/Snowy Standard");
            if (!snowy) return;
            var cut = ShopCut();
            foreach (var r in FindObjectsByType<Renderer>(FindObjectsSortMode.None))
            {
                if (!r || dressed.Contains(r) || r is ParticleSystemRenderer || r is SkinnedMeshRenderer || r.gameObject.layer == 5 || r.name == "Luminous lens") continue;
                var c = r.bounds.center;
                if (c.x > cut.x && c.x < cut.z && c.z > cut.y && c.z < cut.w) continue;   // the shop: under its roof
                r.GetSharedMaterials(mats);
                bool changed = false;
                for (int i = 0; i < mats.Count; i++) { var copy = SnowyCopy(mats[i]); if (copy) { mats[i] = copy; changed = true; } }
                if (changed) { r.sharedMaterials = mats.ToArray(); dressed.Add(r); }
                mats.Clear();
            }
        }

        void Undress()
        {
            foreach (var r in dressed)
            {
                if (!r) continue;
                r.GetSharedMaterials(mats);
                bool changed = false;
                for (int i = 0; i < mats.Count; i++) if (mats[i] && originalOf.TryGetValue(mats[i], out var o)) { mats[i] = o; changed = true; }
                if (changed) r.sharedMaterials = mats.ToArray();
                mats.Clear();
            }
            dressed.Clear();
        }

        Material SnowyCopy(Material m)
        {
            if (!m) return null;
            if (snowyOf.TryGetValue(m, out var cached)) return cached;
            Material copy = null;
            // opaque or cut-out Standard only (the glass and other see-through ones stay as they are), never the lamps
            // (the street lights' glow is driven on their own materials: CheckoutEventVisuals.SetStreetlights)
            var n = m.name;
            bool lamp = m.IsKeywordEnabled("_EMISSION") || n.Contains("glow") || n.Contains("Glow") || n.Contains("Lamp") || n.Contains("Light") || n.Contains("Bulb");
            if (!lamp && m.shader && m.shader.name == "Standard" && m.renderQueue < 2500 && !m.IsKeywordEnabled("_ALPHABLEND_ON") && !m.IsKeywordEnabled("_ALPHAPREMULTIPLY_ON"))
            {
                copy = new Material(snowy) { name = m.name + " (snow)" };
                copy.SetColor("_Color", m.color);
                copy.mainTexture = m.mainTexture; copy.mainTextureScale = m.mainTextureScale; copy.mainTextureOffset = m.mainTextureOffset;
                copy.SetFloat("_Glossiness", m.GetFloat("_Glossiness")); copy.SetFloat("_Metallic", m.GetFloat("_Metallic"));
                if (m.IsKeywordEnabled("_NORMALMAP") && m.GetTexture("_BumpMap"))
                { copy.SetTexture("_BumpMap", m.GetTexture("_BumpMap")); copy.SetFloat("_BumpScale", m.GetFloat("_BumpScale")); copy.EnableKeyword("_NORMALMAP"); }
                copy.SetColor("_EmissionColor", Color.black);
                if (m.IsKeywordEnabled("_ALPHATEST_ON")) { copy.EnableKeyword("_ALPHATEST_ON"); copy.SetFloat("_Cutoff", m.GetFloat("_Cutoff")); copy.renderQueue = m.renderQueue; }
                originalOf[copy] = m;
            }
            snowyOf[m] = copy;
            return copy;
        }

        void Apply()
        {
            Shader.SetGlobalFloat(Amount, level);
            Shader.SetGlobalVector(Cut, ShopCut());
        }

        /// <summary>The shop floor with its walls (x min, z min, x max, z max): no snow there.</summary>
        public static Vector4 ShopCut()
        {
            var inside = CheckoutInterior.Active;
            if (!inside) return new Vector4(-9.7f, -7.5f, 9.7f, 7.5f);
            var r = inside.FloorRect;
            return new Vector4(r.xMin - .35f, r.yMin - .35f, r.xMax + .35f, r.yMax + .35f);
        }

        void OnDestroy() { Shader.SetGlobalFloat(Amount, 0); Undress(); }
    }
}
