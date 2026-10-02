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
            public int waypoint;
            public float delay;
        }
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
                trip.phase = Phase.Arriving; trip.waypoint = 0; maneuverOwner = i;
                trip.route = Smooth(CheckoutRoundabout.Route(ArriveRoute(i)));
                vehicles[i].SetPositionAndRotation(trip.route[0], Quaternion.LookRotation(Vector3.right));
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
                if (trip.waypoint >= trip.route.Length)
                {
                    if (trip.phase == Phase.Arriving)
                    {
                        trip.phase = Phase.Shopping; ParkedVisits++; maneuverOwner = -1;
                        int slot = i;
                        trip.walker.BeginFromCar(trip.customer, Door(i), walker => ReturnToCar(slot,walker));
                    }
                    else { if(maneuverOwner==i)maneuverOwner=-1;trip.phase = Phase.Available; trip.walker = null; trip.customer = null; car.gameObject.SetActive(false); CompletedVisits++; Debug.Log("CITY_VISIT_COMPLETE car="+i+" total="+CompletedVisits); }
                    continue;
                }
                Vector3 delta = trip.route[trip.waypoint] - car.position;
                if (delta.magnitude < .06f) { trip.waypoint++; continue; }
                Vector3 direction = delta.normalized;
                // Backing out of the bay (nose first in, so the first stretch of the way out is in reverse).
                bool reverse = trip.phase == Phase.Leaving && Vector3.Distance(car.position, Bay(i)) < BackOut - .05f && trip.waypoint < 12;
                float speed = InLot(car.position) ? 1.6f : 4.2f;
                // Keep a safe following gap, and yield to customers crossing the parking aisle.
                bool blocked = false;
                for (int j = 0; j < trips.Length; j++)
                {
                    if (j != i && trips[j].phase != Phase.Available && vehicles[j])
                    {
                        var separation=vehicles[j].position-car.position;
                        if(CheckoutTrafficJunctions.Ahead(car.position,direction,vehicles[j].position,4.1f))blocked=true;
                    }
                    var pedestrian=trips[j].walker;
                    if(pedestrian&&pedestrian.gameObject.activeSelf)
                    {
                        var separation=pedestrian.transform.position-car.position;separation.y=0;
                        if(separation.magnitude<2.5f&&Vector3.Dot(direction,separation.normalized)>.35f)blocked=true;
                    }
                }
                if(pedestrians!=null)foreach(var pedestrian in pedestrians)
                {
                    if(!pedestrian||!pedestrian.gameObject.activeInHierarchy)continue;
                    var gap=pedestrian.transform.position-car.position;gap.y=0;
                    if(CheckoutTrafficJunctions.Ahead(car.position,direction,pedestrian.transform.position,2.8f,.7f))blocked=true;
                }
                if(neighborhood&&neighborhood.cars!=null)foreach(var other in neighborhood.cars)
                {
                    if(other==null||!other.vehicle||!other.vehicle.gameObject.activeSelf)continue;
                    var gap=other.vehicle.position-car.position;gap.y=0;
                    float ahead=Vector3.Dot(direction,gap);
                    if(ahead>0&&ahead<4.4f&&(gap-direction*ahead).sqrMagnitude<1.6f)blocked=true;
                }
                if (CheckoutTrafficJunctions.Hold(car,direction,blocked)) continue;
                var heading=Quaternion.LookRotation(reverse?-direction:direction);
                speed*=Mathf.Lerp(.3f,1f,1-Mathf.Clamp01(Quaternion.Angle(car.rotation,heading)/70));
                car.rotation = Quaternion.RotateTowards(car.rotation,heading,Time.deltaTime*130);
                car.position = Vector3.MoveTowards(car.position,trip.route[trip.waypoint],speed*Time.deltaTime);
            }
        }
        void ReturnToCar(int index, CheckoutWalker walker)
        {
            var trip = trips[index];
            if (walker.HasPaid) PaidVisits++;
            trip.walker=null;
            trip.phase = Phase.Leaving; trip.waypoint = 0; trip.delay = .8f;
            trip.route=Smooth(CheckoutRoundabout.Route(LeaveRoute(index)));
        }

        // ------------------------------------------------------------------ the market's parking lot
        // The block is a grid of lots (src/data/market-lots.ts) and the market fills them from the corner on the
        // left of the avenue. The supermarket's parking lot is C1, the lot on the right of the avenue: bays along
        // the east edge, an aisle from the avenue. The hypermarket takes C1 for the building, so its parking lot
        // is C3, behind it: an aisle in from the east street and bays nose-first towards the back of the block.
        public enum ParkingLot { Front, Back }
        public static ParkingLot Lot { get; set; } = ParkingLot.Front;
        public static int Bays => Lot == ParkingLot.Back ? 5 : 3;
        static float BackOut => Lot == ParkingLot.Back ? BackBayZ - BackAisle : FrontBayX - FrontAisle;
        const float BackAisle = 22f, BackBayZ = 25.9f, FrontAisle = 11.2f, FrontBayX = 16.1f;
        public static float BayZ(int index) => -5.5f + index*4f;
        static float BackBayX(int index) => 7.2f + index * 2.3f;
        /// <summary>Where the car of bay `index` stands.</summary>
        public static Vector3 Bay(int index) => Lot == ParkingLot.Back ? P(BackBayX(index), BackBayZ) : P(FrontBayX, BayZ(index));
        /// <summary>Where its customer gets out (behind the car in the back lot, beside it in the front one).</summary>
        public static Vector3 Door(int index) => Lot == ParkingLot.Back ? P(BackBayX(index), BackBayZ - 2.9f) : P(FrontBayX, BayZ(index) - 1.9f);
        /// <summary>Walkable strips from the doors to the sidewalk (baked into the navigation).</summary>
        public static IEnumerable<Bounds> WalkStrips()
        {
            if (Lot == ParkingLot.Back)
            {
                float z = BackBayZ - 2.9f, x0 = BackBayX(0) - .7f, x1 = 19.9f;
                yield return new Bounds(new Vector3((x0 + x1) * .5f, .05f, z), new Vector3(x1 - x0, .2f, 1.3f));
            }
            else for (int bay = 0; bay < Bays; bay++) yield return new Bounds(new Vector3(17.1f, .05f, BayZ(bay) - 1.9f), new Vector3(5.4f, .2f, 1.3f));
        }
        /// <summary>The customer walks from the door to this sidewalk line, then to the corner and the entrance.</summary>
        public static float WalkX => 19.5f;
        public static Vector3 Corner => P(19.5f, -11.5f);
        static bool InLot(Vector3 p) => Lot == ParkingLot.Back
            ? p.x > 5.5f && p.x < 26f && p.z > 19f && p.z < 28.5f
            : p.x > 9f && p.x < 18.5f && p.z > -14f && p.z < 5f;
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
            // Back out into the aisle, then right into the westbound curbside lane of the avenue.
            return new[] { bay,P(FrontAisle,bay.z),P(FrontAisle,-13),P(8.8f,-14),P(-38,-14) };
        }
        static Vector3 P(float x,float z) => new Vector3(x,.15f,z);
        // Rounded waypoint corners avoid snapping the vehicle by ninety degrees at a junction.
        static Vector3[] Smooth(Vector3[] points)
        {
            var route=new List<Vector3>{points[0]};
            for(int i=1;i<points.Length-1;i++)
            {
                float radius=Mathf.Min(1.1f,Vector3.Distance(points[i-1],points[i])*.3f,Vector3.Distance(points[i],points[i+1])*.3f);
                var a=points[i]+(points[i-1]-points[i]).normalized*radius;
                var b=points[i]+(points[i+1]-points[i]).normalized*radius;
                for(int step=0;step<=8;step++){float t=step/8f;route.Add((1-t)*(1-t)*a+2*(1-t)*t*points[i]+t*t*b);}
            }
            route.Add(points[points.Length-1]);return route.ToArray();
        }
    }
}
