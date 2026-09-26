using UnityEngine;
using UnityEngine.AI;
using System.Linq;
using System.Collections.Generic;

namespace Checkout
{
    // Ambient visits never create purchases or modify the React Native simulation.
    [DefaultExecutionOrder(120)]
    public class CheckoutNeighborhoodTraffic : MonoBehaviour
    {
        [System.Serializable]
        public class Visit
        {
            public Vector3 road, sidewalk, entrance;
            public bool edge; // The street ends here: the car leaves the map instead of turning around.
            public bool detour; // Only driven while the road works block the curbside lane.
        }
        [System.Serializable]
        public class Car
        {
            public Transform vehicle;
            public NavMeshAgent visitor;
            [System.NonSerialized] public int waypoint, phase, visits;
            [System.NonSerialized] public float wait;
            [System.NonSerialized] public Renderer[] body;
            [System.NonSerialized] public int destination=-1;
            [System.NonSerialized] public bool passengerWalking;
        }
        const float MarketStopX=8.5f; // Past the road works, so a car dropping off never blocks them.
        public Visit[] route;
        public Car[] cars;
        CheckoutCityTraffic marketTraffic;
        CheckoutCityPedestrian[] pedestrians;
        void Start()
        {
            marketTraffic=FindAnyObjectByType<CheckoutCityTraffic>();
            pedestrians=FindObjectsByType<CheckoutCityPedestrian>();
            BuildRoute();
            for(int i=0;i<cars.Length;i++)
            {
                var car=cars[i];
                car.waypoint=i*route.Length/cars.Length;
                car.vehicle.position=route[car.waypoint].road;
                car.visitor.GetComponent<CheckoutCityAppearance>()?.Prepare();
                car.body=car.visitor.GetComponentsInChildren<Renderer>(true).Where(r=>r.enabled).ToArray();
                car.visitor.gameObject.SetActive(false);
                car.waypoint=(car.waypoint+1)%route.Length;
                ChooseDestination(car);
                if(i==0)
                {
                    car.destination=System.Array.FindIndex(route,s=>s.road.x==MarketStopX && s.road.z== -14);
                    car.waypoint=car.destination;
                    car.vehicle.position=route[car.waypoint-1].road;
                }
                car.vehicle.rotation=Quaternion.LookRotation((route[car.waypoint].road-car.vehicle.position).normalized);
            }
        }
        void Update()
        {
            foreach(var car in cars)
            {
                UpdatePassenger(car);
                var stop=route[car.waypoint];
                if(car.phase==0)
                {
                    var delta=stop.road-car.vehicle.position;delta.y=0;
                    if(delta.sqrMagnitude>.04f)
                    {
                        var direction=delta.normalized;
                        if(CheckoutTrafficJunctions.Hold(car.vehicle,direction,Blocked(car,direction)))continue;
                        var heading=Quaternion.LookRotation(direction);
                        float speed=3.4f*Mathf.Lerp(.25f,1,1-Mathf.Clamp01(Quaternion.Angle(car.vehicle.rotation,heading)/70));
                        car.vehicle.rotation=Quaternion.RotateTowards(car.vehicle.rotation,heading,Time.deltaTime*110);
                        car.vehicle.position=Vector3.MoveTowards(car.vehicle.position,stop.road,Time.deltaTime*speed);
                        continue;
                    }
                    if(stop.entrance==Vector3.zero||car.waypoint!=car.destination){Next(car);continue;}
                    car.destination=-1; // Consume the sole stop before starting the drop-off.
                    car.visitor.gameObject.SetActive(true);
                    car.visitor.updateRotation=false;
                    car.visitor.updateUpAxis=false;
                    if(!NavMesh.SamplePosition(stop.sidewalk,out var hit,1,NavMesh.AllAreas)||!car.visitor.Warp(hit.position))
                    {car.visitor.gameObject.SetActive(false);Next(car);continue;}
                    var path=new NavMeshPath();
                    if(!car.visitor.CalculatePath(stop.entrance,path)||path.status!=NavMeshPathStatus.PathComplete)
                    {car.visitor.gameObject.SetActive(false);Next(car);continue;}
                    var facing=path.corners.Length>1?path.corners[1]-hit.position:stop.entrance-hit.position;facing.y=0;
                    if(facing.sqrMagnitude>.001f)car.visitor.transform.rotation=Quaternion.LookRotation(-facing);
                    car.visitor.SetPath(path);car.visitor.isStopped=false;car.passengerWalking=true;car.phase=1;car.wait=0;car.visits++;
                }
                else if(car.phase==2)
                {
                    car.wait+=Time.deltaTime;
                    if(car.wait<0||cars.Any(o=>o!=car&&o.vehicle.gameObject.activeSelf&&(o.vehicle.position-car.vehicle.position).sqrMagnitude<25))continue;
                    var ahead=route[(car.waypoint+1)%route.Length].road-car.vehicle.position;ahead.y=0;
                    if(ahead.sqrMagnitude>.01f)car.vehicle.rotation=Quaternion.LookRotation(ahead);
                    car.vehicle.gameObject.SetActive(true);car.phase=0;car.wait=0;
                }
                else
                {
                    car.wait+=Time.deltaTime;
                    if(car.wait>1.2f)Next(car); // Leave while the passenger continues on foot.
                }
            }
        }
        void UpdatePassenger(Car car)
        {
            var agent=car.visitor;
            if(!car.passengerWalking||!agent.isOnNavMesh)return;
            var velocity=agent.velocity;velocity.y=0;
            if(velocity.sqrMagnitude>.004f)agent.transform.rotation=Quaternion.RotateTowards(agent.transform.rotation,Quaternion.LookRotation(-velocity),Time.deltaTime*540);
            if(!agent.pathPending&&agent.remainingDistance<=.2f){agent.gameObject.SetActive(false);car.passengerWalking=false;}
        }
        void Next(Car car)
        {
            // Start a new journey only at the city boundary, never at another doorstep.
            var stop=route[car.waypoint];
            if(stop.edge && stop.road.x>35 && !car.passengerWalking)ChooseDestination(car);
            car.waypoint=(car.waypoint+1)%route.Length;car.phase=0;car.wait=0;
            while(route[car.waypoint].detour&&!CheckoutEventVisuals.RoadWorks)car.waypoint=(car.waypoint+1)%route.Length;
            // Leave at the end of the street and come back later from the other lane.
            if(stop.edge){car.phase=2;car.wait=-Random.Range(2f,5f);car.vehicle.gameObject.SetActive(false);car.vehicle.position=route[car.waypoint].road;}
        }
        void ChooseDestination(Car car)
        {
            var available=Enumerable.Range(0,route.Length).Where(i=>route[i].entrance!=Vector3.zero&&i!=car.destination).ToArray();
            int market=System.Array.FindIndex(route,s=>s.road.x==MarketStopX && s.road.z== -14);
            car.destination=Random.value<.4f?-1:Random.value<.5f?market:available.Length==0?-1:available[Random.Range(0,available.Length)];
        }
        void BuildRoute()
        {
            var streets=FindAnyObjectByType<CheckoutCityStreets>();
            var stops=new List<Visit>();var b=streets.cityBounds;
            void Road(float x,float z){stops.Add(new Visit{road=new Vector3(x,.15f,z)});}
            void Edge(float x,float z){Road(x,z);stops[stops.Count-1].edge=true;}
            void Detour(float x,float z){Road(x,z);stops[stops.Count-1].detour=true;}
            void Stop(Vector3 door,float x,float z,Vector3 sidewalk){stops.Add(new Visit{road=new Vector3(x,.15f,z),sidewalk=sidewalk,entrance=door});}
            // Right-hand traffic. Local streets: x ±24.6 / ±22.4. Avenue lanes: eastbound z -23 (curb) and -20,
            // westbound z -17 and -14 (curb). There is no street behind the market block.
            Road(24.6f,-20);
            foreach(var door in streets.entrances.Where(p=>p.x>26).OrderBy(p=>p.z))Stop(door,24.6f,door.z,new Vector3(27.5f,.15f,door.z));
            Edge(24.6f,b.max.z-3);Road(22.4f,b.max.z-3);
            foreach(var door in streets.entrances.Where(p=>p.x>10 && p.x<19.5f && p.z>-11 && p.z<20).OrderByDescending(p=>p.z))Stop(door,22.4f,door.z,new Vector3(19.5f,.15f,door.z));
            Road(22.4f,-14);
            var map=FindAnyObjectByType<CheckoutMap>();
            Stop(map.Point(new Vector3(-1.75f,.74f,-6)),MarketStopX,-14,new Vector3(MarketStopX,.15f,-11.5f));
            // Swerve into the inner westbound lane around the road works (x -0.4 to 5.5), back after the entrance crossing.
            Detour(6.6f,-17);Detour(-1.2f,-17);Detour(-3.6f,-14);
            Road(-22.4f,-14);Edge(-22.4f,b.max.z-3);Road(-24.6f,b.max.z-3);
            foreach(var door in streets.entrances.Where(p=>p.x< -26).OrderByDescending(p=>p.z))Stop(door,-24.6f,door.z,new Vector3(-27.5f,.15f,door.z));
            Road(-24.6f,-20);Edge(b.max.x-3,-20);
            // Through traffic on the avenue: back west in the inner lane, then east again in the curb lane.
            Road(b.max.x-3,-17);Edge(b.min.x+3,-17);
            Road(b.min.x+3,-23);Road(8,-23);Road(14,-20);
            route=AroundRoundabout(stops).ToArray();
        }
        // Bends every drive through the west roundabout around its island. Stops inside the circle
        // are plain corners, so they are replaced by the arc; edges (teleports) are never joined.
        static List<Visit> AroundRoundabout(List<Visit> stops)
        {
            var circle=CheckoutRoundabout.Current;if(!circle)return stops;
            bool Corner(Visit v)=>circle.Inside(v.road)&&v.entrance==Vector3.zero&&!v.edge;
            var result=new List<Visit>();int n=stops.Count;
            for(int i=0;i<n;i++)
            {
                var current=stops[i];
                if(Corner(current))continue;
                result.Add(current);
                if(current.edge)continue;
                var inner=new List<Vector3>();int j=(i+1)%n,guard=0;
                while(Corner(stops[j])&&guard++<n){inner.Add(stops[j].road);j=(j+1)%n;}
                foreach(var p in circle.Arc(current.road,inner,stops[j].road))
                    result.Add(new Visit{road=p,detour=current.detour&&stops[j].detour});
            }
            return result;
        }
        bool Blocked(Car car,Vector3 direction)
        {
            bool Ahead(Vector3 position,float distance)
            {
                var delta=position-car.vehicle.position;delta.y=0;
                float forward=Vector3.Dot(delta,direction);
                return forward>0 && forward<distance && (delta-direction*forward).sqrMagnitude<1.6f;
            }
            foreach(var other in cars)if(other!=car&&other.vehicle.gameObject.activeSelf&&Ahead(other.vehicle.position,4.4f))return true;
            if(marketTraffic&&marketTraffic.enabled)foreach(var other in marketTraffic.vehicles)if(other.gameObject.activeInHierarchy&&Ahead(other.position,4.4f))return true;
            foreach(var person in pedestrians)if(person&&person.gameObject.activeInHierarchy&&Ahead(person.transform.position,2.8f))return true;
            return false;
        }
    }
}
