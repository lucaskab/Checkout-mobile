using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Now and then a city character strolls to a free bench on the market block, sits for a while and leaves.
    public class CheckoutPlazaSitters : MonoBehaviour
    {
        public int maxSitters = 3;
        public Vector2 interval = new Vector2(6, 20), sitTime = new Vector2(14, 40);
        const float WalkSpeed = 1.15f, SitSeconds = .8f, HipHeight = .92f;
        enum Stage { Arriving, SittingDown, Sitting, StandingUp, Leaving }
        class Sitter { public CheckoutRigPose pose; public CheckoutBenchSeat bench; public Stage stage; public Vector3 approach, seat, exit; public float timer, sit, idle; public List<Vector3> path; public int node; public Vector3 benchAt; }
        readonly List<Sitter> sitters = new List<Sitter>();
        CheckoutBenchSeat[] benches;
        float nextVisit;

        void Start() { nextVisit = Time.time + Random.Range(1f, 5f); }

        // A bench hidden by the map design has no one sitting on it.
        static bool Visible(CheckoutBenchSeat b)
        {
            var rs = b.GetComponentsInChildren<Renderer>();
            if (rs.Length == 0 && b.transform.parent) rs = b.transform.parent.GetComponentsInChildren<Renderer>();
            foreach (var r in rs) if (r.enabled && !r.forceRenderingOff) return true;
            return rs.Length == 0;
        }

        static bool OnMarketBlock(Vector3 p) => Mathf.Abs(p.x) < 18f && p.z > -10f && p.z < 46f;

        void Update()
        {
            if (Time.time >= nextVisit)
            {
                nextVisit = Time.time + Random.Range(interval.x, interval.y);
                if (sitters.Count < maxSitters) Visit();
            }
            for (int i = sitters.Count - 1; i >= 0; i--)
                if (!Step(sitters[i], Time.deltaTime)) { if (sitters[i].bench) sitters[i].bench.sitters--; Destroy(sitters[i].pose.root.gameObject); sitters.RemoveAt(i); }
        }

        void Visit()
        {
            // Looked up every visit: the map editor moves, hides and copies benches.
            benches = FindObjectsByType<CheckoutBenchSeat>(FindObjectsInactive.Include);
            var free = new List<CheckoutBenchSeat>();
            foreach (var b in benches) if (b && b.isActiveAndEnabled && b.sitters == 0 && OnMarketBlock(b.transform.position) && Visible(b)) free.Add(b);
            if (free.Count == 0) return;
            var bench = free[Random.Range(0, free.Count)];
            var pose = CheckoutRigPose.Spawn(transform, "Bench visitor");
            if (pose == null) return;
            var t = bench.transform; float along = Random.Range(-.4f, .4f) * bench.width * .5f;
            var s = new Sitter { pose = pose, bench = bench, timer = Random.Range(sitTime.x, sitTime.y) };
            s.seat = t.TransformPoint(new Vector3(along, 0, .04f)); s.seat.y = t.position.y + bench.seatHeight + .07f - HipHeight;
            s.approach = t.TransformPoint(new Vector3(along, 0, -.62f)); s.approach.y = CheckoutPlazaCyclists.Ground;
            // Visitors come in from the footway round the block and walk round everything in their way.
            var start = CheckoutBlockPaths.EdgePoint(); start.y = CheckoutPlazaCyclists.Ground;
            s.exit = CheckoutBlockPaths.EdgePoint(); s.exit.y = CheckoutPlazaCyclists.Ground;
            s.path = CheckoutBlockPaths.Route(start, s.approach);
            bench.sitters++; s.benchAt = t.position;
            pose.root.position = start;
            var first = s.path.Count > 0 ? s.path[0] : s.approach;
            if ((first - start).sqrMagnitude > .01f) pose.root.rotation = Quaternion.LookRotation(-(first - start));
            sitters.Add(s);
        }

        bool Step(Sitter s, float dt)
        {
            var root = s.pose.root;
            switch (s.stage)
            {
                case Stage.Arriving:
                    if (Gone(s)) { s.stage = Stage.Leaving; s.path = CheckoutBlockPaths.Route(root.position, s.exit); s.node = 0; break; }
                    if (Follow(s, dt)) { s.stage = Stage.SittingDown; s.sit = 0; } break;
                case Stage.SittingDown:
                    if (Gone(s)) { s.stage = Stage.StandingUp; break; }
                    s.sit = Mathf.Min(1, s.sit + dt / SitSeconds);
                    root.rotation = Quaternion.Slerp(root.rotation, s.bench.transform.rotation, dt * 8);
                    root.position = Vector3.Lerp(s.approach, s.seat, Smooth(s.sit));
                    if (s.sit >= 1) s.stage = Stage.Sitting;
                    break;
                case Stage.Sitting:
                    if (Gone(s)) { s.stage = Stage.StandingUp; break; }
                    root.position = s.seat; root.rotation = s.bench.transform.rotation;
                    s.timer -= dt;
                    if (s.timer <= 0) s.stage = Stage.StandingUp;
                    break;
                case Stage.StandingUp:
                    s.sit = Mathf.Max(0, s.sit - dt / SitSeconds);
                    root.position = Vector3.Lerp(s.approach, s.seat, Smooth(s.sit));
                    if (s.sit <= 0) { s.stage = Stage.Leaving; s.path = CheckoutBlockPaths.Route(s.approach, s.exit); s.node = 0; }
                    break;
                case Stage.Leaving: if (Follow(s, dt)) return false; break;
            }
            return true;
        }

        static bool Follow(Sitter s, float dt)
        {
            if (s.path == null || s.path.Count == 0) return true;
            var target = s.path[Mathf.Min(s.node, s.path.Count - 1)]; target.y = s.pose.root.position.y;
            if (Walk(s, target, dt)) s.node++;
            return s.node >= s.path.Count;
        }

        // The bench was removed, hidden or moved away (map editor): get up.
        static bool Gone(Sitter s) => !s.bench || !s.bench.isActiveAndEnabled || !Visible(s.bench) || (s.bench.transform.position - s.benchAt).sqrMagnitude > .0025f;

        static float Smooth(float t) => t * t * (3 - 2 * t);

        static bool Walk(Sitter s, Vector3 target, float dt)
        {
            var root = s.pose.root; var delta = target - root.position; delta.y = 0;
            float step = Mathf.Min(delta.magnitude, WalkSpeed * dt);
            if (delta.magnitude < .02f) return true;
            root.position += delta.normalized * step;
            root.rotation = Quaternion.RotateTowards(root.rotation, Quaternion.LookRotation(-delta), 360 * dt);
            s.pose.Walk(step);
            return false;
        }

        void LateUpdate()
        {
            foreach (var s in sitters)
            {
                if (s.stage == Stage.Arriving || s.stage == Stage.Leaving) continue;
                s.idle += Time.deltaTime * .25f;
                s.pose.Sample("Idle", s.idle);
                if (s.sit > 0) Seat(s.pose, Smooth(s.sit));
            }
        }

        // Thighs forward along the seat, shins down, hands resting on the knees.
        static void Seat(CheckoutRigPose pose, float weight)
        {
            Vector3 forward = pose.Forward, down = Vector3.down;
            for (int i = 0; i < 2; i++)
            {
                if (!pose.shin[i]) continue;
                var thigh = pose.thigh[i]; var original = thigh.rotation;
                CheckoutRigPose.Aim(thigh, forward + down * .12f);
                thigh.rotation = Quaternion.Slerp(original, thigh.rotation, weight);
                var shin = pose.shin[i]; original = shin.rotation;
                CheckoutRigPose.Aim(shin, down + forward * .08f);
                shin.rotation = Quaternion.Slerp(original, shin.rotation, weight);
                if (!pose.forearm[i] || !pose.hand[i]) continue;
                Quaternion upper = pose.upperArm[i].rotation, fore = pose.forearm[i].rotation;
                CheckoutRigPose.Reach(pose.upperArm[i], pose.forearm[i], pose.hand[i], shin.position - forward * .12f + Vector3.up * .06f, -forward);
                pose.upperArm[i].rotation = Quaternion.Slerp(upper, pose.upperArm[i].rotation, weight);
                pose.forearm[i].rotation = Quaternion.Slerp(fore, pose.forearm[i].rotation, weight);
            }
        }
    }
}
