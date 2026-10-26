using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // City characters cycle along the street bike lanes and through the park, at random intervals.
    public class CheckoutPlazaCyclists : MonoBehaviour
    {
        public int maxRiders = 5;
        public Vector2 interval = new Vector2(4, 14);
        public const float Ground = .13f;
        // Lucas 26/10 (smooth turns): each lane is ridden as a smooth path (CheckoutVehiclePath: corners rounded) at
        // distance s, the bike facing along it, instead of turning at a fixed rate after every corner.
        class Rider { public CheckoutRigPose pose; public CheckoutBicycle bike; public CheckoutVehiclePath lane; public int route; public float s, speed, wheel, crank, offset, steer; public Vector3 along; }
        readonly List<Rider> riders = new List<Rider>();
        List<Vector3[]> routes;
        readonly Dictionary<int, CheckoutVehiclePath> lanes = new Dictionary<int, CheckoutVehiclePath>();
        const float BendRadius = 3f;
        float nextRide;

        void Start() { nextRide = Time.time + Random.Range(2f, 8f); }

        void Update()
        {
            if (Time.time >= nextRide)
            {
                nextRide = Time.time + Random.Range(interval.x, interval.y);
                if (riders.Count < maxRiders) Launch(Random.Range(0, (routes ??= CheckoutCycleTrack.Routes(Ground)).Count));
            }
            for (int i = riders.Count - 1; i >= 0; i--) if (!Ride(riders[i], Time.deltaTime)) { Destroy(riders[i].bike.root.gameObject); riders.RemoveAt(i); }
        }

        void Launch(int route)
        {
            if (!lanes.TryGetValue(route, out var lane)) lanes[route] = lane = new CheckoutVehiclePath().Build(routes[route], BendRadius, null, false);
            if (!lane.Ready) return;
            var start = lane.Sample(0, out var first);
            foreach (var other in riders) if (other.route == route && Vector3.Distance(other.bike.root.position, start) < 8) return;
            var bike = CheckoutBicycle.Build(transform);
            var pose = CheckoutRigPose.Spawn(bike.root, "Cyclist");
            if (pose == null) { Destroy(bike.root.gameObject); return; }
            // Hips on the saddle; the rig faces its root -Z, the bike +Z.
            pose.root.localPosition = new Vector3(0, CheckoutBicycle.Saddle.y + .06f - .92f, CheckoutBicycle.Saddle.z);
            pose.root.localRotation = Quaternion.Euler(0, 180, 0);
            var rider = new Rider { pose = pose, bike = bike, lane = lane, route = route, speed = Random.Range(3.2f, 4.6f) };
            bike.root.SetPositionAndRotation(start, Quaternion.LookRotation(first)); rider.along = start;
            riders.Add(rider);
        }

        bool Ride(Rider rider, float dt)
        {
            var bike = rider.bike.root;
            // An event vehicle parked on the lane (the power company's bucket truck, a delivery van): the rider swings
            // round it, slowing down while he changes side, and comes back to the lane after it.
            rider.lane.Sample(rider.s, out var fwd); var side = Vector3.Cross(Vector3.up, fwd);
            float want = DodgeFor(rider.along, fwd, side);
            float gap = want - rider.offset;
            rider.offset += Mathf.Clamp(gap, -2.2f * dt, 2.2f * dt);
            float step = rider.speed * dt * (Mathf.Abs(gap) > .25f ? .45f : 1f), travelled = step;
            rider.s += step;
            if (rider.s >= rider.lane.Length) return false;
            var position = rider.lane.Sample(rider.s, out var heading);
            side = Vector3.Cross(Vector3.up, heading);
            rider.along = position;
            bike.position = position + side * rider.offset;
            // swinging round an obstacle it steers towards the side it moves to (its sideways speed over its speed), eased
            float sideways = Mathf.Abs(gap) > .02f ? Mathf.Clamp(Mathf.Clamp(gap, -2.2f * dt, 2.2f * dt) / Mathf.Max(1e-3f, step), -.6f, .6f) : 0;
            rider.steer = Mathf.Lerp(rider.steer, sideways, 1 - Mathf.Exp(-dt / .15f));
            bike.rotation = Quaternion.LookRotation(heading + side * rider.steer);
            rider.crank = rider.bike.Roll(travelled, ref rider.wheel);
            return true;
        }

        // The smallest sideways shift that keeps the rider (and the next couple of metres of his lane) off every
        // event obstacle; 0 when the lane is clear.
        static readonly float[] Dodges = { 0, 1f, -1f, 1.7f, -1.7f, 2.4f, -2.4f, 3.1f, -3.1f, 3.8f, -3.8f };
        static float DodgeFor(Vector3 at, Vector3 forward, Vector3 side)
        {
            foreach (var o in Dodges)
            {
                bool clear = true;
                for (float s = -1.2f; s <= 3.2f && clear; s += .8f) clear = !CheckoutEventTraffic.Covered(at + forward * s + side * o, .45f);
                if (clear) return o;
            }
            return 0;
        }

        void LateUpdate()
        {
            foreach (var rider in riders) Pose(rider);
        }

        static void Pose(Rider rider)
        {
            var pose = rider.pose; var bike = rider.bike.root;
            pose.Sample("Idle", 0);
            Vector3 forward = bike.forward, right = bike.right, up = bike.up;
            pose.torso.rotation = Quaternion.AngleAxis(34, right) * pose.torso.rotation;
            if (pose.head) pose.head.rotation = Quaternion.AngleAxis(-26, right) * pose.head.rotation;
            for (int i = 0; i < 2; i++)
            {
                int side = bike.InverseTransformPoint(pose.thigh[i].position).x > 0 ? 1 : -1;
                if (pose.shin[i] && pose.foot[i])
                    CheckoutRigPose.Reach(pose.thigh[i], pose.shin[i], pose.foot[i], rider.bike.Pedal(side, rider.crank) + up * .1f, forward + up * .3f);
                if (pose.forearm[i])
                {
                    var grip = bike.TransformPoint(new Vector3(side * CheckoutBicycle.Grip.x, CheckoutBicycle.Grip.y, CheckoutBicycle.Grip.z));
                    CheckoutRigPose.Reach(pose.upperArm[i], pose.forearm[i], pose.hand[i], grip, -forward * .4f - up * .6f + right * side * .5f);
                }
            }
        }
    }
}
