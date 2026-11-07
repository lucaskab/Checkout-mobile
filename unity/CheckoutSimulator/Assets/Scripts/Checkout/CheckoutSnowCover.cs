using UnityEngine;

namespace Checkout
{
    // The snow on the city during the "nevasca" event (Lucas 06/11: "a maioria dos lugares fica com neve por cima da
    // calçada... óbvio que não dentro do mercado"). The outdoor surface shaders (Soft Painted, City Tiles, Painted
    // Terrain Tiles, City Park Triplanar, Painted Standard) include CheckoutPaint/CheckoutSnow.cginc, which whitens the
    // faces looking up by the global _CheckoutSnow; here it settles over ~12 s (patchy first) and melts in ~4 s when
    // the event ends. The shop floor and its walls (_CheckoutSnowCut) stay clear: the market has a roof.
    public class CheckoutSnowCover : MonoBehaviour
    {
        static readonly int Amount = Shader.PropertyToID("_CheckoutSnow"), Cut = Shader.PropertyToID("_CheckoutSnowCut");
        float level, target;
        public float Level => level;

        public void SetSnowing(bool on, bool instant = false)
        {
            target = on ? 1 : 0;
            if (instant) level = target;
            enabled = true; Apply();
        }

        void Update()
        {
            level = Mathf.MoveTowards(level, target, Time.deltaTime / (target > level ? 12f : 4f));
            Apply();
            if (level == 0 && target == 0) enabled = false;
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

        void OnDestroy() { Shader.SetGlobalFloat(Amount, 0); }
    }
}
