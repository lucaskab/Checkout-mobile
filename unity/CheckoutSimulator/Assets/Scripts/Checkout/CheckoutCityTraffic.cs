using System;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Visual projection of authoritative customer visits. This never credits money or removes stock.
    public class CheckoutCityTraffic : MonoBehaviour
    {
        public Transform[] vehicles;
        public int Capacity {get;set;}=3;
        public int ParkedVisits { get; private set; }
        public int PaidVisits { get; private set; }
        public int CompletedVisits { get; private set; }
        enum Phase { Available, Arriving, Shopping, Leaving }
        class Trip
        {
            public Phase phase;
            public Customer customer;
            public CheckoutWalker walker;
            public Vector3[] route;
            public float delay;
            // Lucas 26/10 (smooth turns): the car drives along a smooth path (CheckoutVehiclePath) at distance s; leaving,
            // it first backs out of the bay along `path` (reverse) and then drives on along `next`.
            public CheckoutVehiclePath path = new CheckoutVehiclePath(), next = new CheckoutVehiclePath();
            public float s, speed;
            public bool reverse;
        }
        // Driving: m/s and m/s^2. A held car brakes hard (the checks ahead reach as far as it needs to stop).
        const float Cruise = 4.2f, LotCruise = 1.6f, ReverseCruise = 1.2f, Accel = 2.4f, Brake = 2.6f, HardBrake = 6f;
        // Backing out of a bay (Lucas 26/10, instead of turning on the spot in the aisle) the car backs straight into the
        // aisle and swings its tail 45 degrees up it on this radius, stops, and drives off turning the other 45 degrees: it
        // needs no more room up the aisle than the old turn on the spot (the bays by the depot's truck drive) and keeps its
        // tail clear of the cars parked across the aisle (it turns BackOutShift short of the aisle's centre line).
        const float BackOutRadius = 1.6f, BackOutShift = .4f;
        Trip[] trips;
        CheckoutCityPedestrian[] pedestrians;
        CheckoutNeighborhoodTraffic neighborhood;
        float nextArrival;
        int maneuverOwner = -1;
        void Awake() { pedestrians=FindObjectsByType<CheckoutCityPedestrian>();neighborhood=FindAnyObjectByType<CheckoutNeighborhoodTraffic>();ResetVisits(); }
        public void ResetVisits()
        {
            if (trips != null)
                foreach (var trip in trips) if (trip.walker) trip.walker.CancelVisit();
            trips = new Trip[vehicles.Length];
            for (int i = 0; i < vehicles.Length; i++) { trips[i] = new Trip(); vehicles[i].gameObject.SetActive(false); }
            ParkedVisits = PaidVisits = CompletedVisits = 0;
            nextArrival = 0; maneuverOwner = -1;
        }
        public bool TryBegin(Customer customer, CheckoutWalker walker)
        {
            if (Time.time < nextArrival || maneuverOwner >= 0) return false;
            for (int i = 0; i < Mathf.Min(Capacity,trips.Length); i++)
            {
                var trip = trips[i];
                if (trip.phase != Phase.Available) continue;
                trip.customer = customer; trip.walker = walker; walker.Reserve();
                trip.phase = Phase.Arriving; maneuverOwner = i;
                trip.route = ArriveRoute(i);
                trip.path.Build(trip.route); trip.next.Clear(); trip.reverse = false; trip.s = 0; trip.speed = Cruise;
                var start = trip.path.Sample(0, out var heading);
                vehicles[i].SetPositionAndRotation(start, Quaternion.LookRotation(heading));
                vehicles[i].gameObject.SetActive(true); nextArrival = Time.time + 6f;
                return true;
            }
            return false;
        }
        void Update()
        {
            if (trips == null) return;
            for (int i = 0; i < trips.Length; i++)
            {
                var trip = trips[i];
                if (trip.phase == Phase.Available || trip.phase == Phase.Shopping) continue;
                if (trip.delay > 0) { trip.delay -= Time.deltaTime; continue; }
                var car = vehicles[i];
                // A visit cancelled mid-drive (the walker was reused) or without a route just ends.
                if (!car || trip.route == null || (trip.phase == Phase.Arriving && !trip.walker)) { if (maneuverOwner == i) maneuverOwner = -1; trip.phase = Phase.Available; trip.walker = null; trip.customer = null; if (car) car.gameObject.SetActive(false); continue; }
                if (trip.phase == Phase.Leaving && InLot(car.position))
                {
                    if (maneuverOwner >= 0 && maneuverOwner != i) continue;
                    maneuverOwner = i;
                }
                else if (trip.phase == Phase.Leaving && maneuverOwner == i) maneuverOwner = -1;
                if (trip.s >= trip.path.Length - .01f)
                {
                    // Out of the bay: change gear (it stands still a moment) and drive on.
                    if (trip.reverse && trip.next.Ready) { var done = trip.path; trip.path = trip.next; trip.next = done; done.Clear(); trip.reverse = false; trip.s = 0; trip.speed = 0; continue; }
                    if (trip.phase == Phase.Arriving)
                    {
                        trip.phase = Phase.Shopping; ParkedVisits++; maneuverOwner = -1; trip.speed = 0;
                        int slot = i;
                        trip.walker.BeginFromCar(trip.customer, Door(i), walker => ReturnToCar(slot,walker));
                    }
                    else { if(maneuverOwner==i)maneuverOwner=-1;trip.phase = Phase.Available; trip.walker = null; trip.customer = null; car.gameObject.SetActive(false); CompletedVisits++; Debug.Log("CITY_VISIT_COMPLETE car="+i+" total="+CompletedVisits); }
                    continue;
                }
                float dt = Time.deltaTime;
                trip.path.Sample(trip.s, out var direction);   // the way it moves (backwards out of the bay)
                bool reverse = trip.reverse;
                float speed = trip.speed, reach = speed * speed / (2 * HardBrake);
                // Keep a safe following gap, and yield to customers crossing the parking aisle (looking as far ahead as
                // it needs to stop).
                bool blocked = false;
                for (int j = 0; j < trips.Length; j++)
                {
                    if (j != i && trips[j].phase != Phase.Available && vehicles[j])
                        if(CheckoutTrafficJunctions.Ahead(car.position,direction,vehicles[j].position,4.1f+reach))blocked=true;
                    var pedestrian=trips[j].walker;
                    if(pedestrian&&pedestrian.gameObject.activeSelf)
                    {
                        var separation=pedestrian.transform.position-car.position;separation.y=0;
                        if(separation.magnitude<2.5f+reach&&Vector3.Dot(direction,separation.normalized)>.35f)blocked=true;
                    }
                }
                if(pedestrians!=null)foreach(var pedestrian in pedestrians)
                {
                    if(!pedestrian||!pedestrian.gameObject.activeInHierarchy)continue;
                    if(CheckoutTrafficJunctions.Ahead(car.position,direction,pedestrian.transform.position,2.8f+reach,.7f))blocked=true;
                }
                if(neighborhood&&neighborhood.cars!=null)foreach(var other in neighborhood.cars)
                {
                    if(other==null||!other.vehicle||!other.vehicle.gameObject.activeSelf)continue;
                    var gap=other.vehicle.position-car.position;gap.y=0;
                    float ahead=Vector3.Dot(direction,gap);
                    if(ahead>0&&ahead<4.4f+reach&&(gap-direction*ahead).sqrMagnitude<1.6f)blocked=true;
                }
                // event vehicles (a bus at its stop, the jam's queues…) are waited for, never crept through
                bool held = !reverse && CheckoutEventTraffic.Blocks(car.position+direction*1.9f,direction,2.6f+reach,.9f);
                held |= CheckoutTrafficJunctions.Hold(car,direction,blocked,reach);
                // Its speed: the street or the lot, slower into the bends ahead, to a stop at the bay / where it changes gear.
                float cruise = reverse ? ReverseCruise : InLot(car.position) ? LotCruise : Cruise;
                float top = Mathf.Min(cruise, trip.path.Allowed(trip.s, cruise, Brake));
                if (reverse || trip.phase == Phase.Arriving) top = Mathf.Min(top, Mathf.Max(.35f, trip.path.StopSpeed(trip.s, Brake)));
                if (held) top = 0;
                speed = speed < top ? Mathf.Min(top, speed + Accel * dt) : Mathf.Max(top, speed - (held ? HardBrake : Brake) * dt);
                trip.speed = speed;
                trip.s = Mathf.Min(trip.path.Length, trip.s + speed * dt);
                var at = trip.path.Sample(trip.s, out var heading);
                car.SetPositionAndRotation(at, Quaternion.LookRotation(reverse ? -heading : heading));
            }
        }
        /// <summary>QA (trafficturns): the customers of the parked cars stop shopping and drive off, backing out of their bays.</summary>
        public int QaSendBack(){int n=0;for(int i=0;i<trips.Length;i++){var trip=trips[i];if(trip.phase!=Phase.Shopping||!trip.walker)continue;var w=trip.walker;w.CancelVisit();ReturnToCar(i,w);n++;}return n;}
        void ReturnToCar(int index, CheckoutWalker walker)
        {
            var trip = trips[index];
            if (walker.HasPaid) PaidVisits++;
            trip.walker=null;
            trip.phase = Phase.Leaving; trip.delay = .8f;
            trip.route=LeaveRoute(index);
            // The route's first leg (bay -> aisle) is driven backwards: see BackOutRadius.
            var route=trip.route;
            var back=route[1]-route[0];back.y=0;back.Normalize();          // the way it backs out
            var outward=route[2]-route[1];outward.y=0;outward.Normalize(); // the way out along the aisle
            var turn=route[1]-back*BackOutShift;
            float leg=BackOutRadius*Mathf.Tan(22.5f*Mathf.Deg2Rad);
            var cusp=turn+(back-outward).normalized*leg;
            backOut[0]=route[0];backOut[1]=turn;backOut[2]=cusp;turnRadii[1]=BackOutRadius;
            trip.path.Build(backOut,BackOutRadius,null,false,turnRadii);
            onward.Clear();onward.Add(cusp);onward.Add(turn);onward.Add(turn+outward*2f);for(int k=2;k<route.Length;k++)onward.Add(route[k]);
            trip.next.Build(onward,CheckoutVehiclePath.StreetRadius,null,true,turnRadii);
            trip.reverse=true;trip.s=0;trip.speed=0;
        }
        static readonly Vector3[] backOut=new Vector3[3];static readonly float[] turnRadii=new float[2];static readonly List<Vector3> onward=new List<Vector3>();

        // ------------------------------------------------------------------ the market's parking lot
        // The block is a grid of lots (src/data/market-lots.ts) and the market fills them from the corner on the
        // left of the avenue. The supermarket's parking lot is C1, the lot on the right of the avenue: an aisle in
        // from the avenue with bays on both sides (its depot's truck bay is on the south edge of C2, just behind).
        // The hypermarket takes C1 for the building, so its parking lot is C3, behind it: an aisle in from the east
        // street and bays nose-first towards the back of the block.
        public enum ParkingLot { Front, Back }
        public static ParkingLot Lot { get; set; } = ParkingLot.Front;
        public static int Bays => 5;
        static float BackOut(int index) => Lot == ParkingLot.Back ? BackBayZ - BackAisle : Mathf.Abs(Bay(index).x - FrontAisle);
        const float BackAisle = 22f, BackBayZ = 25.9f, FrontAisle = 11.2f, FrontBayX = 16.1f;
        public const float FrontAisleX = FrontAisle, FrontWestBayX = 7.3f;
        public static float BayZ(int index) => -5.5f + index*4f;
        static float BackBayX(int index) => 7.2f + index * 2.3f;
        /// <summary>Where the car of bay `index` stands (front lot: three along the east edge, two on the west side).</summary>
        public static Vector3 Bay(int index) => Lot == ParkingLot.Back ? P(BackBayX(index), BackBayZ) : index < 3 ? P(FrontBayX, BayZ(index)) : P(FrontWestBayX, BayZ(index - 2));
        /// <summary>Where its customer gets out (behind the car in the back lot, beside it in the front one).</summary>
        public static Vector3 Door(int index) => Lot == ParkingLot.Back ? P(BackBayX(index), BackBayZ - 2.9f) : Bay(index) + new Vector3(0, 0, -1.9f);
        /// <summary>Walkable strips from the doors to the sidewalk (baked into the navigation).</summary>
        public static IEnumerable<Bounds> WalkStrips()
        {
            if (Lot == ParkingLot.Back)
            {
                float z = BackBayZ - 2.9f, x0 = BackBayX(0) - .7f, x1 = 19.9f;
                yield return new Bounds(new Vector3((x0 + x1) * .5f, .05f, z), new Vector3(x1 - x0, .2f, 1.3f));
                yield break;
            }
            // From each door across to the aisle, and down the aisle to the avenue sidewalk.
            for (int bay = 0; bay < Bays; bay++)
            {
                var door = Door(bay); float x0 = Mathf.Min(door.x, FrontAisle) - .6f, x1 = Mathf.Max(door.x, FrontAisle) + .6f;
                yield return new Bounds(new Vector3((x0 + x1) * .5f, .05f, door.z), new Vector3(x1 - x0, .2f, 1.3f));
            }
            yield return new Bounds(new Vector3(FrontAisle, .05f, -3.6f), new Vector3(1.3f, .2f, 15.6f));
        }
        /// <summary>The customer walks from the door to this line (the aisle, or the east sidewalk for the back lot),
        /// then to the corner and the entrance.</summary>
        public static float WalkX => Lot == ParkingLot.Back ? 19.5f : FrontAisle;
        public static Vector3 Corner => Lot == ParkingLot.Back ? P(19.5f, -11.5f) : P(FrontAisle, -10.6f);
        static bool InLot(Vector3 p) => Lot == ParkingLot.Back
            ? p.x > 5.5f && p.x < 26f && p.z > 19f && p.z < 28.5f
            : p.x > 5.5f && p.x < 18.5f && p.z > -14f && p.z < 5f;
        static Vector3[] ArriveRoute(int i)
        {
            var bay = Bay(i);
            // Along the eastbound avenue lane; the west junction may be a roundabout (the route goes round it).
            if (Lot == ParkingLot.Back)
                // Left at the east street (northbound lane), left again into the aisle, right into the bay.
                return new[] { P(-38,-20),P(21.4f,-20),P(24.6f,-16.5f),P(24.6f,BackAisle-2.4f),P(22f,BackAisle),P(bay.x,BackAisle),bay };
            // Left across the westbound lanes into the aisle, right into the bay.
            return new[] { P(-38,-20),P(9f,-20),P(FrontAisle,-16.5f),P(FrontAisle,bay.z),bay };
        }
        static Vector3[] LeaveRoute(int i)
        {
            var bay = Bay(i);
            if (Lot == ParkingLot.Back)
                // Back out into the aisle, right onto the southbound lane, right again into the westbound avenue.
                return new[] { bay,P(bay.x,BackAisle),P(21f,BackAisle),P(22.4f,BackAisle-2.2f),P(22.4f,-12.4f),P(20f,-14),P(-38,-14) };
            // Back out into the aisle, then right into the westbound curbside lane of the avenue; when a market event
            // blocks that lane (CheckoutEventTraffic) the car keeps to the inner lane past it.
            if (CheckoutEventTraffic.HasCurbBlock)
            {
                float from=CheckoutEventTraffic.BlockFrom,to=CheckoutEventTraffic.BlockTo;
                if (to+2.2f<8.8f-1f) return new[] { bay,P(FrontAisle,bay.z),P(FrontAisle,-13),P(8.8f,-14),P(to+2.2f,-17),P(from-1f,-17),P(Mathf.Max(from-3.4f,-13.5f),-14),P(-38,-14) };
                if (to>FrontAisle-1.5f) return new[] { bay,P(FrontAisle,bay.z),P(FrontAisle,-12.9f),P(to+1.2f,-13.2f),P(to+1.2f,-17),P(from-1f,-17),P(Mathf.Max(from-3.4f,-13.5f),-14),P(-38,-14) };
                return new[] { bay,P(FrontAisle,bay.z),P(FrontAisle,-13),P(FrontAisle-.8f,-17),P(from-1f,-17),P(Mathf.Max(from-3.4f,-13.5f),-14),P(-38,-14) };
            }
            return new[] { bay,P(FrontAisle,bay.z),P(FrontAisle,-13),P(8.8f,-14),P(-38,-14) };
        }
        static Vector3 P(float x,float z) => new Vector3(x,.15f,z);
    }
}
