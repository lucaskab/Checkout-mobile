using System;
using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Visual projection of authoritative customer visits. This never credits money or removes stock.
    public class CheckoutCityTraffic : MonoBehaviour
    {
        public Transform[] vehicles;
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
        float nextArrival;
        int maneuverOwner = -1;
        void Awake() { pedestrians=FindObjectsByType<CheckoutCityPedestrian>();ResetVisits(); }
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
            for (int i = 0; i < trips.Length; i++)
            {
                var trip = trips[i];
                if (trip.phase != Phase.Available) continue;
                trip.customer = customer; trip.walker = walker; walker.Reserve();
                trip.phase = Phase.Arriving; trip.waypoint = 0; maneuverOwner = i;
                float z = BayZ(i);
                trip.route = Smooth(new[] { P(-38,-17),P(-13.4f,-17),P(-11.2f,-14),P(-11.2f,z),P(-16.1f,z) });
                vehicles[i].SetPositionAndRotation(trip.route[0], Quaternion.LookRotation(Vector3.right));
                vehicles[i].gameObject.SetActive(true); nextArrival = Time.time + 6f;
                return true;
            }
            return false;
        }
        void Update()
        {
            for (int i = 0; i < trips.Length; i++)
            {
                var trip = trips[i];
                if (trip.phase == Phase.Available || trip.phase == Phase.Shopping) continue;
                if (trip.delay > 0) { trip.delay -= Time.deltaTime; continue; }
                var car = vehicles[i];
                if (trip.phase == Phase.Leaving && car.position.z > -14f && car.position.z < 20f && car.position.x < -8)
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
                        trip.walker.BeginFromCar(trip.customer, P(-16.1f,BayZ(i)-1.9f), walker => ReturnToCar(slot,walker));
                    }
                    else { if(maneuverOwner==i)maneuverOwner=-1;trip.phase = Phase.Available; trip.walker = null; trip.customer = null; car.gameObject.SetActive(false); CompletedVisits++; Debug.Log("CITY_VISIT_COMPLETE car="+i+" total="+CompletedVisits); }
                    continue;
                }
                Vector3 delta = trip.route[trip.waypoint] - car.position;
                if (delta.magnitude < .06f) { trip.waypoint++; continue; }
                Vector3 direction = delta.normalized;
                bool reverse = trip.phase == Phase.Leaving && car.position.x < -11.25f && Mathf.Abs(car.position.z-BayZ(i)) < .2f;
                float speed = car.position.x > -20 && car.position.x < -8 && car.position.z > -12 ? 1.6f : 4.2f;
                // Keep a safe following gap, and yield to customers crossing the parking aisle.
                bool blocked = false;
                for (int j = 0; j < trips.Length; j++)
                {
                    if (j != i && trips[j].phase != Phase.Available)
                    {
                        var separation=vehicles[j].position-car.position;
                        if(separation.magnitude<4.1f && Vector3.Dot(direction,separation.normalized)>.65f) blocked=true;
                    }
                    var pedestrian=trips[j].walker;
                    if(pedestrian&&pedestrian.gameObject.activeSelf)
                    {
                        var separation=pedestrian.transform.position-car.position;separation.y=0;
                        if(separation.magnitude<2.5f&&Vector3.Dot(direction,separation.normalized)>.35f)blocked=true;
                    }
                }
                foreach(var pedestrian in pedestrians)
                {
                    if(!pedestrian||!pedestrian.gameObject.activeInHierarchy)continue;
                    var gap=pedestrian.transform.position-car.position;gap.y=0;
                    if(gap.magnitude<4&&Vector3.Dot(direction,gap.normalized)>.4f)blocked=true;
                }
                if (blocked) continue;
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
            float z=BayZ(index);
            // Reverse into the aisle, then follow the right-hand lane around the neighborhood.
            trip.route=Smooth(new[]{P(-16.1f,z),P(-11.2f,z),P(-11.2f,-13),P(-9,-17),P(22,-17),P(25,-14),P(25,28.5f),P(22,31.5f),P(-38,31.5f)});
        }
        public static float BayZ(int index) => -5.5f + index*8f;
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
