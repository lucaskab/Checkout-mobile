using System.Collections.Generic;
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
    // For a NavMeshAgent the agent stays in charge of the way (its path, speed, avoidance, stops at the kerb): Steer only
    // turns its velocity round the corners it can cut, and is the one thing that turns the body. The walk cycle follows the distance really
    // walked (MarketCharacterAnimator), so the feet do not slide. Nothing here allocates per frame.
    public sealed class CheckoutStride
    {
        public const float LookAhead = 1f, WalkTurnTime = .12f, StandTurnTime = .14f, WalkTurnRate = 540f, StandTurnRate = 360f;
        // The city's characters face their holder's -Z; the delivery worker and the works crews +Z.
        readonly bool minusZ;
        float yawSpeed;
        // the corner after the agent's steering target (read when that target or the path's end changes: once a corner)
        readonly Vector3[] corners = new Vector3[32]; int next = -1; Vector3 cornerFor = Far, endFor = Far, legFrom; float swerve, swerveSpeed, look, slid; bool onLeg;
        static readonly Vector3 Far = Vector3.one * 1e9f;
        // the swerve round someone is eased over this (seconds, critically damped), so avoidance does not wag the body
        const float SwerveTime = .5f, TightLook = .25f, MinAim = .6f;
        public CheckoutStride(bool facesMinusZ = true) { minusZ = facesMinusZ; }
        // Everyone walking by an agent this frame or the one before (where they are), so a walker with someone close by is
        // left to its agent's avoidance: walked round a corner into them, the crowd shoved one of the two aside.
        static readonly List<CheckoutStride> walking = new List<CheckoutStride>();
        Vector3 seenAt; int seenFrame = -10; bool listed;
        bool Crowded(Vector3 at)
        {
            int frame = Time.frameCount;
            for (int i = walking.Count - 1; i >= 0; i--)
            {
                var other = walking[i];
                if (frame - other.seenFrame > 30) { other.listed = false; walking.RemoveAt(i); continue; }   // gone (hidden, inside)
                if (other == this || frame - other.seenFrame > 1) continue;
                if (Flat(other.seenAt - at).sqrMagnitude < Personal * Personal) return true;
            }
            return false;
        }
        const float Personal = 1.3f;
        /// <summary>The body was put somewhere else (appeared, warped): no turning from where it was.</summary>
        public void Reset(Transform body) { yawSpeed = swerveSpeed = 0; swerve = 0; look = slid = 0; next = -1; cornerFor = endFor = Far; }

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
        // to the next one). Now one thing decides both, from the agent's live path: away from a corner, the straight line
        // to it; within LookAhead of it, the point that slides from the corner along the next leg as the walker comes up
        // to it (so the turn only ever goes one way, and when the agent moves on to the next corner it is further the same
        // way). The body eases round to that. Where the straight line to the point is clear on the NavMesh the agent walks
        // there too (a rounded corner); where it is not (the corner hugs a wall or a kerb, cutting it would scrape along the
        // edge) the agent takes the corner as it plans it and the body looks round it a little later (TightLook).
        // 29/10 (QA): the agent keeps its speed and its avoidance. Turning its velocity and scaling it down each frame
        // fought its steering and people crawled at ~0.4 m/s, and a path remembered across re-plans pointed some of them
        // backwards. Now only the corner is read from the path, the pace is the agent's wish (eased by its acceleration, a
        // little slower round a sharp corner) and its swerve round someone is carried over, eased.
        /// <summary>Steers a walking agent round the corners of its path and turns its body (the one place that does).
        /// `wanted`: where it means to go when it stands (turning on the spot to set off). Call before reading
        /// agent.nextPosition for the frame. `maxRate`: a slower top turn (a shopper pushing a cart).</summary>
        public void Steer(NavMeshAgent agent, Transform body, Vector3 wanted, float dt, float maxRate = 0)
        {
            if (dt <= 0) return;
            var at = agent.isOnNavMesh ? agent.nextPosition : body.position;
            var velocity = agent.isOnNavMesh ? Flat(agent.velocity) : Vector3.zero; float speed = velocity.magnitude;
            var desired = agent.isOnNavMesh ? Flat(agent.desiredVelocity) : Vector3.zero;
            bool moving = agent.isOnNavMesh && !agent.isStopped && !agent.pathPending && agent.hasPath && desired.sqrMagnitude > .0025f;
            seenAt = at; seenFrame = Time.frameCount; if (!listed) { listed = true; walking.Add(this); }
            if (moving)
            {
                bool crowded = Crowded(at);
                var target = agent.steeringTarget; var toCorner = Flat(target - at); float d = toCorner.magnitude;
                if (Flat(target - cornerFor).sqrMagnitude > 1e-4f || Flat(agent.pathEndPosition - endFor).sqrMagnitude > 1e-4f) NextCorner(agent, target);
                // the swerve round someone: its wish against the straight line to its corner, eased
                float dodge = d > .3f ? Vector3.SignedAngle(toCorner, desired, Vector3.up) : 0;
                if (d > .3f) swerve = Mathf.SmoothDamp(swerve, Mathf.Clamp(dodge, -60f, 60f), ref swerveSpeed, SwerveTime, Mathf.Infinity, dt);
                var way = d > 1e-3f ? toCorner / d : desired.normalized;
                // how far it still is to the corner along the leg it is on (not straight at it: cutting the corner it gets
                // closer to it sideways too)
                var into = Flat(target - legFrom); float span = into.magnitude, along = span > 1e-2f ? Vector3.Dot(toCorner, into / span) : d;
                // Out of a corner it cut, it is beside the new leg: it heads for a point on the leg that starts LookAhead
                // ahead and recedes to the corner as it walks on (twice its progress), so it eases onto the leg and on
                // towards the corner without turning back (straight at the far corner would turn it back a little).
                // The agent is walked there too (where that is clear and it is not stepping round someone), so it does not
                // swing wide past the leg out of a corner it took itself and then turn back onto it.
                if (onLeg && span > 1e-2f && along >= LookAhead)
                {
                    float done = span - along, ahead = Mathf.Min(span, done + LookAhead + Mathf.Max(0, done));
                    var point = legFrom + into / span * ahead; var to = Flat(point - at);
                    if (to.sqrMagnitude > 1e-4f)
                    {
                        way = to.normalized;
                        if (!crowded && Mathf.Abs(dodge) < 10f && Vector3.Angle(toCorner, way) > 3f && !NavMesh.Raycast(at, point, out _, agent.areaMask))
                            agent.velocity = Quaternion.AngleAxis(swerve, Vector3.up) * way * Mathf.MoveTowards(speed, desired.magnitude, Mathf.Max(agent.acceleration, 1f) * dt);
                    }
                }
                if (next >= 0 && ((along < LookAhead && d < LookAhead + 1.5f) || slid > 0))
                {
                    var leg = Flat(corners[next] - target); float len = leg.magnitude;
                    if (len > 1e-3f)
                    {
                        // cut round, or (blocked when it first comes up to the corner) looked round later: decided once a
                        // corner, so the point never jumps back and forth between the two
                        if (look <= 0) look = NavMesh.Raycast(at, target + leg / len * Mathf.Min(Mathf.Max(0, LookAhead - along), len), out _, agent.areaMask) ? TightLook : LookAhead;
                        // only ever further along: `look` past the corner as it comes up to it, `look` ahead along the next
                        // leg once it is past the corner (cutting it, it moves away from the corner again before the agent
                        // takes the next one)
                        float past = Vector3.Dot(Flat(at - target), leg / len);
                        slid = Mathf.Max(slid, Mathf.Max(look - along, past > 0 ? past + look : 0));
                        var carrot = target + leg / len * Mathf.Min(slid, len);
                        // never aimed at a point right under its feet (the way to it swings with every small step aside)
                        float gap = Flat(carrot - at).magnitude;
                        if (gap < MinAim && slid < len) { slid = Mathf.Min(len, slid + MinAim - gap); carrot = target + leg / len * slid; }
                        // (stepping round someone right now, short of the corner: the agent's avoidance has the say, it is not
                        // steered; past the corner it is, or the agent would turn back to the corner it has cut)
                        bool clear = look >= LookAhead && !crowded && (past > 0 || Mathf.Abs(dodge) < 10f) && !NavMesh.Raycast(at, carrot, out _, agent.areaMask);
                        var to = Flat(carrot - at);
                        if (to.sqrMagnitude > 1e-4f)
                        {
                            way = to.normalized;
                            if (clear)
                            {
                                var bent = Quaternion.AngleAxis(swerve, Vector3.up) * way;
                                float sharp = Mathf.Clamp01(Vector3.Angle(toCorner, way) / 90f);
                                float pace = Mathf.MoveTowards(speed, desired.magnitude * (1f - .2f * sharp), Mathf.Max(agent.acceleration, 1f) * dt);
                                agent.velocity = bent * pace;
                            }
                        }
                    }
                }
                // the last steps onto the spot: the way there swings about as it is nudged (others passing), so it keeps facing
                // as it is; it turns where it has to once it stands
                if (next < 0 && d < .6f) return;
                way = Quaternion.AngleAxis(swerve, Vector3.up) * way;
                // (setting off from a standstill it turns as on the spot, eased, up to StandTurnRate)
                FaceYaw(body, Mathf.Atan2(way.x, way.z) * Mathf.Rad2Deg, dt, speed > .35f, maxRate);
                return;
            }
            wanted.y = 0;
            if (speed > .2f) Face(body, velocity, dt, true, maxRate);
            else if (wanted.sqrMagnitude > .01f) Face(body, wanted, dt, false, maxRate);
        }
        // The corner after `target` on the agent's path (agent.path allocates: read once a corner, never per frame).
        void NextCorner(NavMeshAgent agent, Vector3 target)
        {
            // the leg into it starts at the corner it has just passed (the one it was steering for), else where the path did
            // (and only while it is still by that corner: a path planned anew from elsewhere may pass the same points)
            bool onward = next >= 0 && Flat(corners[next] - target).sqrMagnitude < 1e-4f && Flat(agent.pathEndPosition - endFor).sqrMagnitude <= 1e-4f
                && Flat(agent.nextPosition - cornerFor).sqrMagnitude < 9f;
            legFrom = onward ? cornerFor : agent.nextPosition; onLeg = onward;
            cornerFor = target; endFor = agent.pathEndPosition; next = -1; look = slid = 0;
            int count = agent.path.GetCornersNonAlloc(corners);
            for (int i = 0; i < count; i++)
                if (Flat(corners[i] - target).sqrMagnitude < 1e-4f) { if (!onward && i > 0) legFrom = corners[i - 1]; next = i + 1 < count ? i + 1 : -1; break; }
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
