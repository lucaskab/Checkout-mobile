using System;
using System.Collections.Generic;
using UnityEngine;

namespace MarketDay
{
    // Presentation only: stock and order completion remain owned by the game economy.
    public class MarketDeliveryWorker : MonoBehaviour
    {
        class DeliveryStop
        {
            public Transform truck;
            public Vector3 home;
            public double endsAt;
        }

        public enum DeliveryPhase { Waiting, ToTruck, Pickup, ToStorage, PutDown, Returning }
        public Animation animationPlayer;
        public Transform truck, leftHand, rightHand, cargo, storageDoor;
        public Vector3 truckHome, pickupPoint;
        public Vector3[] route;
        public float walkSpeed = 1.25f;
        public DeliveryPhase Phase { get; private set; }
        public int CompletedDeliveries { get; private set; }
        public bool HoldingTruck => Phase != DeliveryPhase.Waiting && Phase != DeliveryPhase.Returning;
        public bool Carrying { get; private set; }
        // A door on the route (the rear roller door): the worker waits in front of it until it has rolled up.
        // Set by whoever animates the door; without it the route is walked freely.
        public Vector3? gateAt;
        public Func<float> gateOpen;
        float gateWait;
        public Vector3 LastDropPosition { get; private set; }

        readonly Queue<DeliveryStop> deliveries = new Queue<DeliveryStop>();
        readonly HashSet<Transform> reservedTrucks = new HashSet<Transform>();
        MarketSimulation simulation;
        Transform cargoParent;
        Renderer[] bodyRenderers;
        Vector3 cargoScale, pickupLocalPosition;
        float clock;
        int waypoint;
        string currentClip;
        bool released;
        double deliveryEndsAt;

        public void SetDestination(Vector3 doorstep, Vector3[] path)
        {
            storageDoor.position = doorstep;
            route = path;
            if (Phase == DeliveryPhase.ToTruck) waypoint = 0;
            else if (Phase == DeliveryPhase.ToStorage) waypoint = route.Length - 2;
            else if (Phase == DeliveryPhase.Returning) waypoint = Mathf.Min(waypoint, route.Length - 1);
            else if (Phase == DeliveryPhase.Waiting) transform.position = route[0];
        }

        public bool QueueDelivery(Transform candidate, Vector3 home, double endsAt = double.PositiveInfinity)
        {
            if (!candidate || reservedTrucks.Contains(candidate)) return false;
            deliveries.Enqueue(new DeliveryStop { truck = candidate, home = home, endsAt = endsAt });
            reservedTrucks.Add(candidate);
            return true;
        }

        public bool HasDeliveryFor(Transform candidate)
        {
            return candidate && reservedTrucks.Contains(candidate);
        }

        public static bool IsUnloading(Transform candidate)
        {
            var worker = candidate && candidate.parent
                ? candidate.parent.GetComponentInChildren<MarketDeliveryWorker>()
                : null;
            return worker && worker.truck == candidate && worker.HoldingTruck;
        }

        void Start()
        {
            simulation = FindAnyObjectByType<MarketSimulation>();
            cargoParent = cargo.parent;
            cargoScale = cargo.localScale;
            pickupLocalPosition = truck ? truck.InverseTransformPoint(pickupPoint) : Vector3.zero;
            cargo.gameObject.SetActive(false);
            // Off shift the worker is out of sight; they come out of the door when a truck needs unloading.
            bodyRenderers = Array.FindAll(GetComponentsInChildren<Renderer>(true), r => !r.transform.IsChildOf(cargo));
            SetVisible(false);
            Play("Idle");
        }

        void Update()
        {
            float rate = simulation ? simulation.speed : 1;
            float dt = Time.deltaTime * rate;
            if (animationPlayer && currentClip != null) animationPlayer[currentClip].speed = rate;
            if (dt <= 0 || !storageDoor || route == null || route.Length == 0) return;
            if (Phase != DeliveryPhase.Waiting && Phase != DeliveryPhase.Returning && DeliveryTimeHasElapsed())
            {
                FinishDelivery();
                return;
            }
            clock += dt;
            switch (Phase)
            {
                case DeliveryPhase.Waiting:
                    if (deliveries.Count == 0) break;
                    BeginNextDelivery();
                    break;
                case DeliveryPhase.ToTruck:
                    // The truck first reverses into its dock. The worker only approaches once it is parked.
                    if (Vector3.Distance(truck.position, truckHome) > .04f) { Play("Idle"); break; }
                    if (Move(RoutePoint(waypoint), dt, false) && ++waypoint == route.Length)
                    {
                        Face(PickupPoint(), dt);
                        Phase = DeliveryPhase.Pickup;
                        clock = 0;
                        Play("Pickup");
                    }
                    break;
                case DeliveryPhase.Pickup:
                    Face(PickupPoint(), dt);
                    // Keep the parcel inside the truck while the worker handles its rear door.
                    if (!Carrying && clock >= Length("Pickup") * .55f) AttachCargo();
                    if (clock >= Length("Pickup"))
                    {
                        Phase = DeliveryPhase.ToStorage;
                        waypoint = route.Length - 2;
                        clock = 0;
                    }
                    break;
                case DeliveryPhase.ToStorage:
                    if (Move(RoutePoint(waypoint), dt, true) && --waypoint < 0)
                    {
                        Phase = DeliveryPhase.PutDown;
                        clock = 0;
                        released = false;
                        Play("PutDown");
                    }
                    break;
                case DeliveryPhase.PutDown:
                    Face(storageDoor.position, dt);
                    if (!released && clock >= Length("PutDown") * .65f)
                    {
                        Carrying = false;
                        released = true;
                        cargo.SetParent(cargoParent, true);
                        cargo.localScale = cargoScale;
                        cargo.SetPositionAndRotation(storageDoor.position, Quaternion.identity);
                        cargo.gameObject.SetActive(false);
                        LastDropPosition = storageDoor.position;
                        CompletedDeliveries++;
                    }
                    if (clock >= Length("PutDown"))
                    {
                        BeginAnotherUnloadTrip();
                    }
                    break;
                case DeliveryPhase.Returning:
                    // Walk back along the route and go in through the door before disappearing.
                    if (Move(route[Mathf.Max(0, waypoint)], dt, false) && --waypoint < 0)
                    {
                        Phase = DeliveryPhase.Waiting;
                        Play("Idle");
                        SetVisible(deliveries.Count > 0);
                    }
                    break;
            }
        }

        void LateUpdate()
        {
            if (!Carrying || !cargo.gameObject.activeSelf) return;
            // Follow both animated hands. The package moves with the pickup/bend clips.
            cargo.position = (leftHand.position + rightHand.position) * .5f + Vector3.down * .5f + transform.forward * .08f;
            cargo.rotation = transform.rotation;
        }

        void BeginNextDelivery()
        {
            var delivery = deliveries.Dequeue();
            truck = delivery.truck;
            truckHome = delivery.home;
            deliveryEndsAt = delivery.endsAt;
            waypoint = 0;
            clock = 0;
            released = false;
            Carrying = false;
            cargo.gameObject.SetActive(false);
            Phase = DeliveryPhase.ToTruck;
            SetVisible(true);
        }

        void BeginAnotherUnloadTrip()
        {
            waypoint = 0;
            clock = 0;
            released = false;
            Carrying = false;
            cargo.gameObject.SetActive(false);
            Phase = DeliveryPhase.ToTruck;
        }

        void FinishDelivery()
        {
            Carrying = false;
            cargo.SetParent(cargoParent, true);
            cargo.localScale = cargoScale;
            cargo.gameObject.SetActive(false);
            reservedTrucks.Remove(truck);
            truck = null;
            deliveryEndsAt = double.PositiveInfinity;
            // Heading out, the next target is behind the worker; heading in, it is still ahead.
            if (Phase == DeliveryPhase.ToTruck) waypoint--;
            else if (Phase == DeliveryPhase.Pickup) waypoint = route.Length - 2;
            else if (Phase == DeliveryPhase.PutDown) waypoint = -1;
            Phase = DeliveryPhase.Returning;
            clock = 0;
        }

        void SetVisible(bool visible)
        {
            foreach (var body in bodyRenderers) if (body) body.enabled = visible;
        }

        bool DeliveryTimeHasElapsed()
        {
            return !double.IsPositiveInfinity(deliveryEndsAt) &&
                   DateTimeOffset.UtcNow.ToUnixTimeMilliseconds() >= deliveryEndsAt;
        }

        Vector3 PickupPoint() => truck ? truck.TransformPoint(pickupLocalPosition) : pickupPoint;

        Vector3 RoutePoint(int index)
        {
            var point = route[index];
            // The loading bays share the same footway. Only the final two approach points move per dock.
            if (index >= route.Length - 2) point += Vector3.right * (PickupPoint().x - pickupPoint.x);
            return point;
        }

        void AttachCargo()
        {
            Carrying = true;
            cargo.gameObject.SetActive(true);
            cargo.SetParent(transform, true);
        }

        bool Move(Vector3 destination, float dt, bool loaded)
        {
            if (Vector3.Distance(transform.position, destination) < .02f) return true;
            Face(destination, dt);
            // Turn before stepping, so the model does not walk sideways around corners.
            var direction = destination - transform.position;
            direction.y = 0;
            if (Vector3.Angle(transform.forward, direction) > 35) { Play(loaded ? "CarryIdle" : "Idle"); return false; }
            if (gateAt.HasValue && gateOpen != null)
            {
                var gate = gateAt.Value; gate.y = transform.position.y;
                var step = Vector3.MoveTowards(transform.position, destination, dt * walkSpeed);
                bool under = Vector3.Distance(step, gate) < .8f;
                if (under && gateOpen() < .85f && gateWait < 3) { gateWait += dt; Play(loaded ? "CarryIdle" : "Idle"); return false; }
                if (!under) gateWait = 0;
            }
            Play(loaded ? "CarryWalking" : "Walking");
            transform.position = Vector3.MoveTowards(transform.position, destination, dt * walkSpeed * (loaded ? .85f : 1));
            return Vector3.Distance(transform.position, destination) < .02f;
        }

        void Face(Vector3 point, float dt)
        {
            var direction = point - transform.position;
            direction.y = 0;
            if (direction.sqrMagnitude > .0001f)
                transform.rotation = Quaternion.RotateTowards(transform.rotation, Quaternion.LookRotation(direction), dt * 240);
        }

        float Length(string clip) => animationPlayer[clip].length;
        void Play(string clip)
        {
            if (currentClip == clip) return;
            currentClip = clip;
            animationPlayer[clip].time = 0;
            animationPlayer.CrossFade(clip, .12f);
        }
    }
}
