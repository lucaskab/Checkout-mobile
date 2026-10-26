using UnityEngine;
using UnityEngine.AI;

namespace Checkout
{
    // How people on foot turn (Lucas 26/10: "the people walking in the street also turn all at once, it isn't smooth").
    // Before, a walker went straight from corner to corner of its route and its body swung round to the new direction at
    // 360-540 degrees a second, a snap at every corner. Now:
    // - the corners of the way are rounded (about a metre: the walker looks a metre ahead along its way and heads there,
    //   so it starts turning before the corner and comes out of it on the next leg), a little slower in a sharp turn;
    // - the body eases round to the way it really moves (a critically damped turn with a top rate, never instant), and
    //   turning on the spot, when it stops or sets off, is eased the same way at up to ~360 degrees a second.
    // For a NavMeshAgent the agent stays in charge of the way (its path, avoidance, stops at the kerb): Steer only turns
    // its velocity round the corners and is the one thing that turns the body. The walk cycle follows the distance really
    // walked (MarketCharacterAnimator), so the feet do not slide. Nothing here allocates per frame.
    public sealed class CheckoutStride
    {
        public const float LookAhead = 1f, WalkTurnTime = .07f, StandTurnTime = .14f, WalkTurnRate = 540f, StandTurnRate = 360f;
        // The city's characters face their holder's -Z; the delivery worker and the works crews +Z.
        readonly bool minusZ;
        float yawSpeed;
        // the agent's path (refreshed only when it changes: a new destination, a re-plan)
        readonly Vector3[] corners = new Vector3[32]; int count, seg; Vector3 refreshedFor = Vector3.one * 1e9f;
        public CheckoutStride(bool facesMinusZ = true) { minusZ = facesMinusZ; }
        /// <summary>The body was put somewhere else (appeared, warped): no turning from where it was.</summary>
        public void Reset(Transform body) { yawSpeed = 0; count = 0; seg = 0; refreshedFor = Vector3.one * 1e9f; }

        static Vector3 Flat(Vector3 v) { v.y = 0; return v; }
        float Yaw(Transform body) { var f = minusZ ? -body.forward : body.forward; return Mathf.Atan2(f.x, f.z) * Mathf.Rad2Deg; }
        void SetYaw(Transform body, float yaw) => body.rotation = Quaternion.Euler(0, minusZ ? yaw + 180f : yaw, 0);

        /// <summary>Eases the body round to face `direction` (walking: quick and smooth; standing: an eased turn on the spot).</summary>
        public void Face(Transform body, Vector3 direction, float dt, bool walking, float maxRate = 0)
        {
            direction.y = 0; if (direction.sqrMagnitude < 1e-6f || dt <= 0) return;
            FaceYaw(body, Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg, dt, walking, maxRate);
        }
        void FaceYaw(Transform body, float want, float dt, bool walking, float maxRate)
        {
            float rate = maxRate > 0 ? maxRate : walking ? WalkTurnRate : StandTurnRate;
            SetYaw(body, Mathf.SmoothDampAngle(Yaw(body), want, ref yawSpeed, walking ? WalkTurnTime : StandTurnTime, rate, dt));
        }

        // ------------------------------------------------------------------ NavMeshAgent walkers
        // Lucas 26/10 21:01: "the pedestrians glitch as they start to turn: they turn, go back to the angle they had, walk
        // a bit and then turn where they should". The body used to follow the way the agent actually moved, and near a
        // corner that went one way (the rounding) and back (the agent still heading for the corner itself, then switching
        // to the next one). Now one thing decides both, continuously: the point LookAhead metres further along the agent's
        // path from where the walker is (its projection on the path, which only moves on). The agent's velocity is turned
        // towards that point, keeping its speed (so it still slows, waits at the kerb and steps aside for others), and the
        // body eases round to it. As the walker comes up to a corner the point slides round it, so the turn only ever goes
        // one way and the walk is a rounded curve.
        /// <summary>Steers a walking agent round the corners of its path and turns its body (the one place that does).
        /// `wanted`: where it means to go when it stands (turning on the spot to set off). Call before reading
        /// agent.nextPosition for the frame. `maxRate`: a slower top turn (a shopper pushing a cart).</summary>
        public void Steer(NavMeshAgent agent, Transform body, Vector3 wanted, float dt, float maxRate = 0)
        {
            if (dt <= 0) return;
            var at = agent.isOnNavMesh ? agent.nextPosition : body.position;
            var velocity = agent.isOnNavMesh ? Flat(agent.velocity) : Vector3.zero; float speed = velocity.magnitude;
            bool moving = agent.isOnNavMesh && !agent.isStopped && !agent.pathPending && agent.hasPath && Flat(agent.desiredVelocity).sqrMagnitude > .0025f;
            if (moving && Ahead(agent, at, out var way))
            {
                // round the corner, a little slower the sharper it is (avoidance still acts on it from here)
                if (speed > .05f) agent.velocity = way * speed * (1f - .2f * Mathf.Clamp01(Vector3.Angle(Flat(agent.desiredVelocity), way) / 90f));
                FaceYaw(body, Mathf.Atan2(way.x, way.z) * Mathf.Rad2Deg, dt, true, maxRate);
                return;
            }
            wanted.y = 0;
            if (speed > .2f) Face(body, velocity, dt, true, maxRate);
            else if (wanted.sqrMagnitude > .01f) Face(body, wanted, dt, false, maxRate);
        }
        // The direction to the point LookAhead metres along the path beyond where `at` projects on it.
        bool Ahead(NavMeshAgent agent, Vector3 at, out Vector3 way)
        {
            way = Vector3.zero;
            var target = agent.steeringTarget;
            int k = count > 1 ? Find(target, seg + 1) : -1;
            if (k < 0)
            {
                // a new path (another destination, a re-plan): read once (allocates, once per path)
                if (Flat(target - refreshedFor).sqrMagnitude <= 1e-4f) return false;
                refreshedFor = target; var path = agent.path; count = path.GetCornersNonAlloc(corners); seg = 0;
                k = Find(target, 1); if (k < 0) return false;
            }
            // on the leg into corner k, or already on the next one (round the corner): whichever it is nearer
            int from = Mathf.Max(seg, k - 1); float best = float.MaxValue; int on = from; float t = 0;
            for (int i = from; i <= Mathf.Min(k, count - 2); i++)
            {
                var a = Flat(corners[i]); var ab = Flat(corners[i + 1]) - a; float len2 = ab.sqrMagnitude; if (len2 < 1e-6f) continue;
                float u = Mathf.Clamp01(Vector3.Dot(Flat(at) - a, ab) / len2); float d = (Flat(at) - (a + ab * u)).sqrMagnitude;
                if (d < best) { best = d; on = i; t = u; }
            }
            seg = on = Mathf.Min(on, count - 2);
            // walk LookAhead along the path from the projection
            float left = LookAhead + Flat(corners[on + 1] - corners[on]).magnitude * t; var carrot = corners[on];
            for (int i = on; i < count - 1; i++)
            {
                var ab = Flat(corners[i + 1] - corners[i]); float len = ab.magnitude;
                if (len >= left) { carrot = corners[i] + ab / Mathf.Max(len, 1e-4f) * left; left = 0; break; }
                carrot = corners[i + 1]; left -= len;
            }
            way = Flat(carrot - at); if (way.sqrMagnitude < .0025f) return false;   // at the end of the way: as it was
            way.Normalize();
            return true;
        }
        int Find(Vector3 target, int from)
        {
            for (int i = Mathf.Max(0, from); i < count; i++) if (Flat(corners[i] - target).sqrMagnitude < 1e-4f) return i;
            return -1;
        }

        // ------------------------------------------------------------------ walkers moved by hand (no NavMesh)
        /// <summary>Walks towards `target` the way people do: along the way it faces, turning smoothly towards the target,
        /// slowing (to a turn on the spot) when the target is behind it. `pass`: the target is a corner on the way, passed
        /// within that distance (cutting it round) instead of stepped on. True on arrival.</summary>
        public bool WalkTo(Transform body, Vector3 target, float speed, float dt, float pass = 0)
        {
            var to = Flat(target - body.position); float dist = to.magnitude;
            if (dist < Mathf.Max(.03f, pass)) { if (pass <= 0) body.position = new Vector3(target.x, body.position.y, target.z); return true; }
            Face(body, to, dt, true, 400f);
            var f = minusZ ? -body.forward : body.forward; f.y = 0; f.Normalize();
            float off = Vector3.Angle(f, to);
            // facing well away: turn on the spot first; otherwise walk on, slower the more it still has to turn
            float k = off > 70f ? 0 : Mathf.Clamp01(Mathf.Cos(off * Mathf.Deg2Rad) * 1.2f);
            float step = Mathf.Min(speed * k * dt, dist);
            // close to the spot it steps straight on to it (no orbiting round it)
            var dir = dist < .6f || off < 2f ? to / dist : f;
            body.position += dir * step;
            return false;
        }
    }
}
