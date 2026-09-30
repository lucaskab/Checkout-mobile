using UnityEngine;

namespace Checkout
{
    // Ducks paddling about the pond: they wander between random spots, turn gently, keep apart,
    // bob on the swell, now and then tip up to feed (tail in the air) and leave ripples behind them.
    public class CheckoutPondDucks : MonoBehaviour
    {
        public Vector2 centre = new Vector2(9.5f, -37.5f), radii = new Vector2(5.2f, 3.3f);
        public float waterY = .15f;
        public Transform[] ducks = new Transform[0];

        class Duck
        {
            public Vector2 position, target; public float heading, speed, wait, bob, feed = -1, nextFeed, nextRipple;
        }
        Duck[] state;

        void OnEnable()
        {
            state = new Duck[ducks.Length];
            for (int i = 0; i < ducks.Length; i++)
            {
                if (!ducks[i]) continue;
                var p = ducks[i].position;
                state[i] = new Duck
                {
                    position = Inside(new Vector2(p.x, p.z), .8f), heading = ducks[i].eulerAngles.y, bob = Random.value * 10,
                    target = RandomSpot(), wait = Random.Range(0f, 3f), nextFeed = Random.Range(4f, 14f),
                };
            }
        }

        Vector2 RandomSpot()
        {
            var a = Random.value * Mathf.PI * 2; var r = Mathf.Sqrt(Random.value) * .72f;
            return centre + new Vector2(Mathf.Cos(a) * radii.x * r, Mathf.Sin(a) * radii.y * r);
        }

        Vector2 Inside(Vector2 p, float limit)
        {
            var q = new Vector2((p.x - centre.x) / radii.x, (p.y - centre.y) / radii.y);
            if (q.magnitude > limit) q = q.normalized * limit;
            return centre + new Vector2(q.x * radii.x, q.y * radii.y);
        }

        void Update()
        {
            if (state == null) return;
            float dt = Time.deltaTime, time = Time.time;
            for (int i = 0; i < state.Length; i++)
            {
                var d = state[i]; var t = ducks[i];
                if (d == null || !t) continue;
                // Feeding: tip forward for a moment, bottom up, then right themselves.
                float tip = 0;
                if (d.feed >= 0)
                {
                    d.feed += dt;
                    float k = d.feed / 2.6f;
                    tip = Mathf.Sin(Mathf.Clamp01(k) * Mathf.PI);
                    tip = Mathf.SmoothStep(0, 1, Mathf.Clamp01(tip * 1.6f));
                    if (d.feed > .25f && d.feed - dt <= .25f) CheckoutWaterRipples.Add(t.position, 1.2f, .38f, 2.6f);
                    if (k >= 1) { d.feed = -1; d.nextFeed = time + Random.Range(7f, 20f); CheckoutWaterRipples.Add(t.position, .8f); }
                    d.speed = Mathf.MoveTowards(d.speed, 0, dt * .6f);
                }
                else if (d.wait > 0)
                {
                    d.wait -= dt; d.speed = Mathf.MoveTowards(d.speed, .04f, dt * .3f); // drifting
                    if (time > d.nextFeed) d.feed = 0;
                }
                else
                {
                    var to = d.target - d.position;
                    if (to.magnitude < .35f) { d.target = RandomSpot(); d.wait = Random.Range(1.5f, 6f); }
                    // Keep a little apart from the others.
                    for (int j = 0; j < state.Length; j++)
                    {
                        if (j == i || state[j] == null) continue;
                        var away = d.position - state[j].position;
                        if (away.magnitude < .9f && away.sqrMagnitude > 1e-4f) to += away.normalized * (1 - away.magnitude / .9f) * 2;
                    }
                    float want = Mathf.Atan2(to.x, to.y) * Mathf.Rad2Deg;
                    d.heading = Mathf.MoveTowardsAngle(d.heading, want, 70 * dt);
                    float align = Mathf.Clamp01(1 - Mathf.Abs(Mathf.DeltaAngle(d.heading, want)) / 120f);
                    d.speed = Mathf.MoveTowards(d.speed, .32f * (.35f + .65f * align), dt * .4f);
                    if (time > d.nextFeed && Random.value < dt * .3f) d.feed = 0;
                }
                var forward = new Vector2(Mathf.Sin(d.heading * Mathf.Deg2Rad), Mathf.Cos(d.heading * Mathf.Deg2Rad));
                d.position = Inside(d.position + forward * d.speed * dt, .86f);
                if (d.speed > .12f && time > d.nextRipple) { CheckoutWaterRipples.Add(t.position - new Vector3(forward.x, 0, forward.y) * .1f, .45f, .3f, 1.8f); d.nextRipple = time + .7f; }

                d.bob += dt;
                float bob = Mathf.Sin(d.bob * 2.1f) * .012f + Mathf.Sin(d.bob * 3.3f + 1) * .006f;
                float pitch = Mathf.Sin(d.bob * 1.7f) * 2.5f + tip * 72;
                float roll = Mathf.Sin(d.bob * 1.3f + 2) * 2f;
                // Tip about the chest so the tail rises out of the water.
                var rotation = Quaternion.Euler(pitch, d.heading, roll);
                var pivot = new Vector3(d.position.x, waterY + bob, d.position.y) + Quaternion.Euler(0, d.heading, 0) * new Vector3(0, 0, .12f);
                t.SetPositionAndRotation(pivot + rotation * new Vector3(0, -tip * .05f, -.12f), rotation);
            }
        }
    }
}
