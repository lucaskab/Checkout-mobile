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
        class Rider { public CheckoutRigPose pose; public CheckoutBicycle bike; public Vector3[] lane; public int next = 1, route; public float speed, wheel, crank; }
        readonly List<Rider> riders = new List<Rider>();
        List<Vector3[]> routes;
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
            var lane = routes[route];
            foreach (var other in riders) if (other.route == route && Vector3.Distance(other.bike.root.position, lane[0]) < 8) return;
            var bike = CheckoutBicycle.Build(transform);
            var pose = CheckoutRigPose.Spawn(bike.root, "Cyclist");
            if (pose == null) { Destroy(bike.root.gameObject); return; }
            // Hips on the saddle; the rig faces its root -Z, the bike +Z.
            pose.root.localPosition = new Vector3(0, CheckoutBicycle.Saddle.y + .06f - .92f, CheckoutBicycle.Saddle.z);
            pose.root.localRotation = Quaternion.Euler(0, 180, 0);
            var rider = new Rider { pose = pose, bike = bike, lane = lane, route = route, speed = Random.Range(3.2f, 4.6f) };
            bike.root.SetPositionAndRotation(lane[0], Quaternion.LookRotation(lane[1] - lane[0]));
            riders.Add(rider);
        }

        bool Ride(Rider rider, float dt)
        {
            var bike = rider.bike.root;
            float step = rider.speed * dt, travelled = step;
            var position = bike.position;
            while (step > 0 && rider.next < rider.lane.Length)
            {
                var target = rider.lane[rider.next]; float d = Vector3.Distance(position, target);
                if (d <= step) { position = target; step -= d; rider.next++; } else { position += (target - position) / d * step; step = 0; }
            }
            if (rider.next >= rider.lane.Length) return false;
            var heading = rider.lane[rider.next] - position; heading.y = 0;
            bike.position = position;
            if (heading.sqrMagnitude > 1e-4f) bike.rotation = Quaternion.RotateTowards(bike.rotation, Quaternion.LookRotation(heading), 220 * dt);
            rider.crank = rider.bike.Roll(travelled, ref rider.wheel);
            return true;
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
