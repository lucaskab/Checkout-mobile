using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Feeds the expanding ripple rings drawn by the "MarketDay/City Water" shader.
    // Anything on the water (ducks, landing jets) calls Add; one instance in the scene animates them.
    public class CheckoutWaterRipples : MonoBehaviour
    {
        const int Max = 12;
        static readonly int Id = Shader.PropertyToID("_CheckoutRipples");
        static readonly Vector4[] slots = new Vector4[Max];
        struct Ripple { public Vector2 centre; public float age, life, speed, strength; }
        static readonly List<Ripple> active = new List<Ripple>();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void ResetStatics() => active.Clear();

        public static void Add(Vector3 position, float strength = 1, float speed = .32f, float life = 2.4f)
        {
            if (active.Count >= Max) active.RemoveAt(0);
            active.Add(new Ripple { centre = new Vector2(position.x, position.z), life = life, speed = speed, strength = strength });
        }

        void OnEnable() => Shader.SetGlobalVectorArray(Id, slots);
        void OnDisable() { System.Array.Clear(slots, 0, Max); Shader.SetGlobalVectorArray(Id, slots); }

        void Update()
        {
            for (int i = active.Count - 1; i >= 0; i--)
            {
                var r = active[i]; r.age += Time.deltaTime;
                if (r.age >= r.life) active.RemoveAt(i); else active[i] = r;
            }
            for (int i = 0; i < Max; i++)
            {
                if (i >= active.Count) { slots[i] = Vector4.zero; continue; }
                var r = active[i]; float k = r.age / r.life;
                slots[i] = new Vector4(r.centre.x, r.centre.y, .04f + r.age * r.speed, r.strength * (1 - k) * (1 - k));
            }
            Shader.SetGlobalVectorArray(Id, slots);
        }
    }
}
