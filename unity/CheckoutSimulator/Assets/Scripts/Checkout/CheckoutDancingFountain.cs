using UnityEngine;

namespace Checkout
{
    // Ground jets on the square that "dance": the heights run through a set of choreographies
    // (all together, a wave across, rings from the centre, a checkerboard, a chase round the edge),
    // cross-fading from one to the next every few seconds.
    public class CheckoutDancingFountain : MonoBehaviour
    {
        public ParticleSystem[] jets = new ParticleSystem[0];
        public Vector2[] grid = new Vector2[0]; // jet positions, roughly -1..1
        public float minSpeed = 1.4f, maxSpeed = 5.4f, patternSeconds = 7f;
        public bool ripples = true;

        const int Patterns = 5;
        float clock, nextRipple;

        float Height(int pattern, int i, float t)
        {
            var p = grid[i];
            switch (pattern)
            {
                case 0: return .5f + .5f * Mathf.Sin(t * 2.4f);                                   // breathe together
                case 1: return .5f + .5f * Mathf.Sin(t * 3.2f - p.x * 2.6f);                      // wave across
                case 2: return .5f + .5f * Mathf.Sin(t * 3.6f - p.magnitude * 3.4f);              // rings outwards
                case 3:                                                                           // checkerboard
                {
                    int cell = Mathf.RoundToInt((p.x + p.y) * 1.5f + 10);
                    float beat = Mathf.Repeat(t * .9f, 2f);
                    return ((cell & 1) == 0) == (beat < 1) ? Mathf.Sin(Mathf.Repeat(beat, 1) * Mathf.PI) : .05f;
                }
                default:                                                                          // chase round the edge
                {
                    float a = Mathf.Atan2(p.y, p.x);
                    float phase = Mathf.Repeat((a / (Mathf.PI * 2)) - t * .45f, 1);
                    return p.magnitude < .4f ? .6f + .4f * Mathf.Sin(t * 5) : Mathf.Pow(1 - phase, 3);
                }
            }
        }

        void Update()
        {
            if (jets.Length == 0 || grid.Length != jets.Length) return;
            clock += Time.deltaTime;
            float slot = clock / patternSeconds;
            int current = (int)slot % Patterns, next = (current + 1) % Patterns;
            float blend = Mathf.SmoothStep(0, 1, Mathf.Clamp01((Mathf.Repeat(slot, 1) - .85f) / .15f));
            for (int i = 0; i < jets.Length; i++)
            {
                var jet = jets[i]; if (!jet) continue;
                float h = Mathf.Lerp(Height(current, i, clock), Height(next, i, clock), blend);
                var main = jet.main;
                main.startSpeed = Mathf.Lerp(minSpeed, maxSpeed, h);
                var emission = jet.emission;
                emission.enabled = h > .08f;
            }
            if (ripples && clock > nextRipple)
            {
                var jet = jets[Random.Range(0, jets.Length)];
                if (jet && jet.emission.enabled) CheckoutWaterRipples.Add(jet.transform.position, .5f, .45f, 1.2f);
                nextRipple = clock + .18f;
            }
        }
    }
}
