using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Lucas 06/11 (legs walking strangely, feet sliding): how far a character walks in one cycle of a walking clip,
    // measured from the clip itself instead of one fixed number for every body (0.733 m for the shoppers, 1.33 m for the
    // staff...). The walks are made by ArtSource/NPCs/walk_cycles.py with a stride that follows each body's legs. While a
    // foot is flat on the ground it is pushed back exactly as fast as the body walks, so the cycle distance is that
    // speed (per clip cycle): the median over the samples where the foot is at its lowest. Measured once per clip, cached.
    public static class CheckoutWalkCycle
    {
        static readonly Dictionary<AnimationClip, float> cache = new Dictionary<AnimationClip, float>();

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void Reset() { cache.Clear(); }

        /// <summary>Metres (world) walked per cycle of `clip` on `anim` at its current scale; `fallback` if it cannot be measured.</summary>
        public static float World(Animation anim, string clip, float fallback)
        {
            if (!anim) return fallback;
            var state = anim[clip];
            if (!state || !state.clip) return fallback;
            float local = Local(anim, state.clip);
            return local > 0 ? local * Mathf.Abs(anim.transform.lossyScale.z) : fallback;
        }

        /// <summary>Playback speed of `clip` so the feet keep pace with a body moving at `worldSpeed` (m/s).</summary>
        public static float Rate(Animation anim, string clip, float worldSpeed, float fallbackCycle = 1.2f)
        {
            if (!anim) return 1;
            var state = anim[clip];
            if (!state) return 1;
            return Mathf.Clamp(worldSpeed * state.length / Mathf.Max(.05f, World(anim, clip, fallbackCycle)), 0, 3);
        }

        // In the Animation object's own space (model units).
        static float Local(Animation anim, AnimationClip clip)
        {
            if (cache.TryGetValue(clip, out var known)) return known;
            Transform left = null, right = null;
            foreach (var t in anim.GetComponentsInChildren<Transform>(true))
            {
                if (t.name == "Foot_L") left = t; else if (t.name == "Foot_R") right = t;
            }
            float result = 0;
            if (left && right && clip.length > 0)
            {
                const int Samples = 64;
                var root = anim.transform;
                var feet = new[] { new Vector3[Samples], new Vector3[Samples] };
                for (int i = 0; i < Samples; i++)
                {
                    clip.SampleAnimation(anim.gameObject, clip.length * i / Samples);
                    feet[0][i] = root.InverseTransformPoint(left.position); feet[1][i] = root.InverseTransformPoint(right.position);
                }
                // the walking axis: the one the feet travel most along (z for the game's models)
                int axis = Range(feet[0], 2) >= Range(feet[0], 0) ? 2 : 0;
                var speeds = new List<float>();
                foreach (var foot in feet)
                {
                    float low = float.MaxValue, high = float.MinValue;
                    foreach (var p in foot) { low = Mathf.Min(low, p.y); high = Mathf.Max(high, p.y); }
                    float flat = low + Mathf.Max(.003f, (high - low) * .03f);
                    for (int i = 0; i < Samples; i++)
                    {
                        var a = foot[i]; var b = foot[(i + 1) % Samples];
                        if (a.y <= flat && b.y <= flat) speeds.Add(Mathf.Abs(b[axis] - a[axis]) * Samples);
                    }
                }
                if (speeds.Count >= 4) { speeds.Sort(); result = speeds[speeds.Count / 2]; }
                if (result < .05f) result = 0;
            }
            cache[clip] = result;
            return result;
        }

        static float Range(Vector3[] points, int axis)
        {
            float min = float.MaxValue, max = float.MinValue;
            foreach (var p in points) { min = Mathf.Min(min, p[axis]); max = Mathf.Max(max, p[axis]); }
            return max - min;
        }
    }
}
