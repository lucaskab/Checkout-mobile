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
            [System.NonSerialized] public bool passengerWalking, toMarket;
            // Lucas 26/10 (smooth turns): the stretch of the route it is driving, as one smooth path, the route stops on it
            // (plan[k] is passed at path.WaypointAt(k + 1); point 0 is where the car stood) and how far along it is.
            [System.NonSerialized] public CheckoutVehiclePath path;
            [System.NonSerialized] public List<int> plan;
            [System.NonSerialized] public int planNext, planSig;
            [System.NonSerialized] public bool planned;
            [System.NonSerialized] public float s, speed;
        }
        const float Cruise=3.4f,Accel=2.2f,Brake=2.6f,HardBrake=6f;
        readonly List<Vector3> planPoints=new List<Vector3>();
        const float MarketStopX=8.5f; // Past the road works, so a car dropping off never blocks them.
        public Visit[] route;
        public Car[] cars;
        CheckoutCityTraffic marketTraffic;
        CheckoutCityPedestrian[] pedestrians;
        CheckoutBridge bridge;int marketStop=-1;
        // The swerve round a blocked curb lane (CheckoutEventTraffic: road works, a parked truck, the street market):
        // these stops move with the block, and the drop-off at the market moves past it.
        Visit marketVisit,detourIn,detourMid,detourOut;bool hidden;
        // Nobody is dropped at the supermarket while it is closed: they would walk in and vanish.
        bool MarketOpen{get{if(!bridge)bridge=FindAnyObjectByType<CheckoutBridge>();return !bridge||bridge.State==null||bridge.State.isOpen;}}
        void Start()
        {
            marketTraffic=FindAnyObjectByType<CheckoutCityTraffic>();
            pedestrians=FindObjectsByType<CheckoutCityPedestrian>();
            BuildRoute();
            marketStop=System.Array.FindIndex(route,st=>st.road.x==MarketStopX && st.road.z== -14);
            marketVisit=marketStop>=0?route[marketStop]:null;
            for(int i=0;i<cars.Length;i++)
            {
                var car=cars[i];
                car.waypoint=i*route.Length/cars.Length;
                car.vehicle.position=route[car.waypoint].road;
                car.visitor.GetComponent<CheckoutCityAppearance>()?.Prepare();
                car.body=car.visitor.GetComponentsInChildren<Renderer>(true).Where(r=>r.enabled).ToArray();
                car.visitor.gameObject.SetActive(false);
                car.waypoint=(car.waypoint+1)%route.Length;
                // Never start on a map edge: the next point would be on the other side of the city.
                if(route[(car.waypoint-1+route.Length)%route.Length].edge){car.vehicle.position=route[car.waypoint].road;car.waypoint=(car.waypoint+1)%route.Length;}
                ChooseDestination(car);
                if(i==0)
                {
                    car.destination=marketStop;
                    car.waypoint=car.destination;
                    car.vehicle.position=route[car.waypoint-1].road;
                }
                car.vehicle.rotation=Quaternion.LookRotation((route[car.waypoint].road-car.vehicle.position).normalized);
            }
        }
        // Event detour: the three swerve stops follow the blocked stretch [from, to] of the curb lane.
        void FollowBlock()
        {
            bool blocked=CheckoutEventTraffic.HasCurbBlock;
            float from=blocked?CheckoutEventTraffic.BlockFrom:-.4f,to=blocked?CheckoutEventTraffic.BlockTo:5.5f;
            if(detourIn!=null)detourIn.road=new Vector3(Mathf.Max(to+2.2f,from+1f),.15f,-17);
            if(detourMid!=null)detourMid.road=new Vector3(from-1f,.15f,-17);
            if(detourOut!=null)detourOut.road=new Vector3(Mathf.Max(from-3.4f,-13.5f),.15f,-14);
            if(marketVisit!=null){marketVisit.road=new Vector3(blocked?Mathf.Max(MarketStopX,to+2.8f):MarketStopX,.15f,-14);marketVisit.sidewalk=new Vector3(marketVisit.road.x,.15f,CheckoutStreetLayout.NorthWalkZ);}
        }
        void Update()
        {
            FollowBlock();
            // A market event jams the avenue: its own queues are the traffic, the city's cars wait off stage.
            if(CheckoutEventTraffic.AvenueJammed!=hidden)
            {
                hidden=CheckoutEventTraffic.AvenueJammed;
                foreach(var c in cars)if(c.vehicle&&c.phase!=2)c.vehicle.gameObject.SetActive(!hidden);
            }
            if(hidden){foreach(var car in cars)UpdatePassenger(car);return;}
            foreach(var car in cars)
            {
                UpdatePassenger(car);
                if(car.phase==0)
                {
                    Drive(car);
                }
                else if(car.phase==2)
                {
                    car.wait+=Time.deltaTime;
                    if(car.wait<0||cars.Any(o=>o!=car&&o.vehicle.gameObject.activeSelf&&(o.vehicle.position-car.vehicle.position).sqrMagnitude<25))continue;
                    var ahead=route[(car.waypoint+1)%route.Length].road-car.vehicle.position;ahead.y=0;
                    if(ahead.sqrMagnitude>.01f)car.vehicle.rotation=Quaternion.LookRotation(ahead);
                    car.vehicle.gameObject.SetActive(true);car.phase=0;car.wait=0;car.planned=false;car.speed=Cruise; // comes in at road speed
                }
                else
                {
                    car.wait+=Time.deltaTime;
                    if(car.wait>1.2f)Next(car); // Leave while the passenger continues on foot.
                }
            }
        }
        // Drives along the planned stretch, passing its stops; plans the next one when it has none (or the road works it
        // swerves round have moved). Speed: road speed, slower into the bends ahead, braking for whatever is ahead.
        void Drive(Car car)
        {
            // what the plan depends on: the stretch the road works block (the swerve follows it), the market being open (a drop-off there)
            int sig=(CheckoutEventTraffic.HasCurbBlock?Mathf.RoundToInt(CheckoutEventTraffic.BlockFrom*10)*7919+Mathf.RoundToInt(CheckoutEventTraffic.BlockTo*10):int.MinValue)^(MarketOpen?1:0);
            var circle=CheckoutRoundabout.Current;
            if(car.planned&&car.planSig!=sig&&!(circle&&circle.Inside(car.vehicle.position)))car.planned=false; // never re-plan on the ring
            if(!car.planned&&!Plan(car,sig))return;
            float dt=Time.deltaTime;var path=car.path;
            var position=path.Sample(car.s,out var direction);
            float reach=car.speed*car.speed/(2*HardBrake);
            // event vehicles (a bus at its stop, the sound car…) are waited for, never crept through
            bool held=CheckoutEventTraffic.Blocks(car.vehicle.position+direction*1.9f,direction,2.6f+reach,.9f);
            held|=CheckoutTrafficJunctions.Hold(car.vehicle,direction,Blocked(car,direction,reach),reach);
            float top=Mathf.Min(Cruise,path.Allowed(car.s,Cruise,Brake));
            bool dropOff=car.plan.Count>0&&!route[car.plan[car.plan.Count-1]].edge;
            if(dropOff)top=Mathf.Min(top,Mathf.Max(.35f,path.StopSpeed(car.s,Brake)));
            if(held)top=0;
            car.speed=car.speed<top?Mathf.Min(top,car.speed+Accel*dt):Mathf.Max(top,car.speed-(held?HardBrake:Brake)*dt);
            car.s=Mathf.Min(path.Length,car.s+car.speed*dt);
            position=path.Sample(car.s,out var heading);
            car.vehicle.SetPositionAndRotation(position,Quaternion.LookRotation(heading));
            // the stops it has reached
            while(car.planned&&car.phase==0&&car.planNext<car.plan.Count&&car.s>=path.WaypointAt(car.planNext+1)-.02f)
            {
                if(car.plan[car.planNext]!=car.waypoint){car.planned=false;break;} // the way on changed (a destination, the road works)
                car.planNext++;
                if(!Arrive(car)){car.planned=false;break;}
            }
            if(car.planned&&car.planNext>=car.plan.Count)car.planned=false;
        }
        // The stretch from where the car is, through the stops it just passes, to the next one where it stops (its
        // drop-off) or leaves the map; with the same rules as Next().
        bool Plan(Car car,int sig)
        {
            if(car.path==null){car.path=new CheckoutVehiclePath();car.plan=new List<int>();}
            // standing on its stop already (it just came in at the map edge, or was placed there)
            for(int guard=0;guard<route.Length&&car.phase==0;guard++)
            {
                var gap=route[car.waypoint].road-car.vehicle.position;gap.y=0;
                if(gap.sqrMagnitude>.09f)break;
                if(!Arrive(car))return false;
            }
            if(car.phase!=0)return false;
            car.plan.Clear();planPoints.Clear();planPoints.Add(car.vehicle.position);
            int index=car.waypoint;
            for(int k=0;k<48;k++)
            {
                car.plan.Add(index);planPoints.Add(route[index].road);
                var stop=route[index];
                if(stop.edge||(stop.entrance!=Vector3.zero&&index==car.destination&&!(index==marketStop&&!MarketOpen)))break;
                index=(index+1)%route.Length;
                while(route[index].detour&&!CheckoutEventTraffic.HasCurbBlock)index=(index+1)%route.Length;
            }
            car.path.Build(planPoints,CheckoutVehiclePath.StreetRadius,car.vehicle.forward);
            car.s=0;car.planNext=0;car.planSig=sig;car.planned=true;
            return true;
        }
        // At the stop car.waypoint: drives on (true), or stops there to drop someone off / leaves the map (false).
        bool Arrive(Car car)
        {
            var stop=route[car.waypoint];
            if(stop.entrance==Vector3.zero||car.waypoint!=car.destination||(car.waypoint==marketStop&&!MarketOpen)){Next(car);return car.phase==0;}
            car.destination=-1; // Consume the sole stop before starting the drop-off.
            car.speed=0;
            car.visitor.gameObject.SetActive(true);
            car.visitor.updateRotation=false;
            car.visitor.updateUpAxis=false;
            if(!NavMesh.SamplePosition(stop.sidewalk,out var hit,1,NavMesh.AllAreas)||!car.visitor.Warp(hit.position))
            {car.visitor.gameObject.SetActive(false);Next(car);return car.phase==0;}
            var path=new NavMeshPath();
            if(!car.visitor.CalculatePath(stop.entrance,path)||path.status!=NavMeshPathStatus.PathComplete)
            {car.visitor.gameObject.SetActive(false);Next(car);return car.phase==0;}
            var facing=path.corners.Length>1?path.corners[1]-hit.position:stop.entrance-hit.position;facing.y=0;
            if(facing.sqrMagnitude>.001f)car.visitor.transform.rotation=Quaternion.LookRotation(-facing);
            car.visitor.SetPath(path);car.visitor.isStopped=false;car.passengerWalking=true;car.toMarket=car.waypoint==marketStop;car.phase=1;car.wait=0;car.visits++;
            return false;
        }
        void UpdatePassenger(Car car)
        {
            var agent=car.visitor;
            if(!car.passengerWalking||!agent.isOnNavMesh)return;
            var velocity=agent.velocity;velocity.y=0;
            if(velocity.sqrMagnitude>.004f)agent.transform.rotation=Quaternion.RotateTowards(agent.transform.rotation,Quaternion.LookRotation(-velocity),Time.deltaTime*540);
            // The market closed while they were on their way: carry on along the sidewalk instead.
            if(car.toMarket&&!MarketOpen)
            {
                car.toMarket=false;
                var p=agent.transform.position;float dir=p.x<0?-1:1;
                var along=new Vector3(p.x+dir*16,.15f,CheckoutStreetLayout.NorthWalkZ);
                if(NavMesh.SamplePosition(along,out var hit,3,NavMesh.AllAreas))agent.SetDestination(hit.position);
            }
            if(!agent.pathPending&&agent.remainingDistance<=.2f){agent.gameObject.SetActive(false);car.passengerWalking=false;car.toMarket=false;}
        }
        void Next(Car car)
        {
            // Start a new journey only at the city boundary, never at another doorstep.
            var stop=route[car.waypoint];
            if(stop.edge && stop.road.x>35 && !car.passengerWalking)ChooseDestination(car);
            car.waypoint=(car.waypoint+1)%route.Length;car.phase=0;car.wait=0;
            while(route[car.waypoint].detour&&!CheckoutEventTraffic.HasCurbBlock)car.waypoint=(car.waypoint+1)%route.Length;
            // Leave at the end of the street and come back later from the other lane.
            if(stop.edge){car.phase=2;car.wait=-Random.Range(2f,5f);car.vehicle.gameObject.SetActive(false);car.vehicle.position=route[car.waypoint].road;}
        }
        void ChooseDestination(Car car)
        {
            var available=Enumerable.Range(0,route.Length).Where(i=>route[i].entrance!=Vector3.zero&&i!=car.destination).ToArray();
            int market=marketStop;
            car.destination=Random.value<.4f?-1:Random.value<.5f?market:available.Length==0?-1:available[Random.Range(0,available.Length)];
            if(car.destination==market&&!MarketOpen)car.destination=available.Length==0?-1:available[Random.Range(0,available.Length)];
            if(car.destination==market&&!MarketOpen)car.destination=-1;
        }
        void BuildRoute()
        {
            var streets=FindAnyObjectByType<CheckoutCityStreets>();
            var stops=new List<Visit>();var b=streets.cityBounds;
            void Road(float x,float z){stops.Add(new Visit{road=new Vector3(x,.15f,z)});}
            void Edge(float x,float z){Road(x,z);stops[stops.Count-1].edge=true;}
            void Detour(float x,float z){Road(x,z);stops[stops.Count-1].detour=true;}
            // A drop-off never stands on a zebra crossing: it moves back to the stop line before it (the passenger with it).
            void Stop(Vector3 door,float x,float z,Vector3 sidewalk)
            {
                var lane=Mathf.Abs(z+14)<.01f&&Mathf.Abs(x)<20?Vector3.left:x>23.5f?Vector3.forward:Vector3.back;
                var road=CheckoutTrafficJunctions.OffCrossings(new Vector3(x,.15f,z),lane);
                stops.Add(new Visit{road=road,sidewalk=sidewalk+(road-new Vector3(x,.15f,z)),entrance=door});
            }
            // Right-hand traffic. Local streets: x ±24.6 / ±22.4. Avenue lanes: eastbound z -23 (curb) and -20,
            // westbound z -17 and -14 (curb). There is no street behind the market block.
            // Every drive runs from one end of the map to another (an edge: the car leaves and a later one
            // comes in elsewhere), never back along the street it came: no U-turns at the dead ends.
            // East street, northbound from its south end across the avenue.
            Road(24.6f,b.min.z+3);
            foreach(var door in streets.entrances.Where(p=>p.x>26).OrderBy(p=>p.z))Stop(door,24.6f,door.z,new Vector3(CheckoutStreetLayout.OuterWalkX,.15f,door.z));
            Edge(24.6f,b.max.z-3);
            // East street southbound from the north, then west along the avenue past the market.
            Road(22.4f,b.max.z-3);
            foreach(var door in streets.entrances.Where(p=>p.x>10 && p.x<CheckoutStreetLayout.LocalCurbInner && p.z>-11 && p.z<20).OrderByDescending(p=>p.z))Stop(door,22.4f,door.z,new Vector3(CheckoutStreetLayout.InnerWalkX,.15f,door.z));
            Road(22.4f,-14);
            var map=FindAnyObjectByType<CheckoutMap>();
            Stop(map.Point(new Vector3(-1.75f,.74f,-6)),MarketStopX,-14,new Vector3(MarketStopX,.15f,CheckoutStreetLayout.NorthWalkZ));
            // Swerve into the inner westbound lane around the road works (x -0.4 to 5.5), back after the entrance crossing.
            Detour(6.6f,-17);detourIn=stops[stops.Count-1];Detour(-1.2f,-17);detourMid=stops[stops.Count-1];Detour(-3.6f,-14);detourOut=stops[stops.Count-1];
            Road(-22.4f,-14);Edge(-22.4f,b.max.z-3);
            // West street southbound from the north, through the roundabout, out at its south end.
            Road(-24.6f,b.max.z-3);
            foreach(var door in streets.entrances.Where(p=>p.x< -26).OrderByDescending(p=>p.z))Stop(door,-24.6f,door.z,new Vector3(-CheckoutStreetLayout.OuterWalkX,.15f,door.z));
            Edge(-24.6f,b.min.z+3);
            // Through traffic on the avenue, end to end in each lane.
            Road(b.min.x+3,-20);Edge(b.max.x-3,-20);
            Road(b.max.x-3,-17);Edge(b.min.x+3,-17);
            Road(b.min.x+3,-23);Edge(b.max.x-3,-23);
            // The stops inside the roundabout stay: every path through it is bent round the island (CheckoutVehiclePath).
            route=stops.ToArray();
        }
        bool Blocked(Car car,Vector3 direction,float reach)
        {
            bool Ahead(Vector3 position,float distance)
            {
                var delta=position-car.vehicle.position;delta.y=0;
                float forward=Vector3.Dot(delta,direction);
                return forward>0 && forward<distance && (delta-direction*forward).sqrMagnitude<1.6f;
            }
            foreach(var other in cars)if(other!=car&&other.vehicle.gameObject.activeSelf&&Ahead(other.vehicle.position,4.4f+reach))return true;
            if(marketTraffic&&marketTraffic.enabled)foreach(var other in marketTraffic.vehicles)if(other.gameObject.activeInHierarchy&&Ahead(other.position,4.4f+reach))return true;
            foreach(var person in pedestrians)if(person&&person.gameObject.activeInHierarchy&&Ahead(person.transform.position,2.8f+reach))return true;
            return false;
        }
    }
}
