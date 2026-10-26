using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;

namespace Checkout
{
    // Right of way for every driven vehicle (the city's cars, the market visitors' cars, couriers, supplier trucks),
    // shared through Hold(). In order:
    // 1. Zebra crossings (CheckoutCityStreets records their carriageway part): a vehicle stops with its nose half a metre
    //    before the stripes while someone is on the crossing heading into its lane, and only drives onto them when there is
    //    room to clear them on the far side ("don't block the box"). Past that stop line it never stops for a rule again.
    // 2. A plain junction: the box with its four crossings is reserved at the stop line, first come first served; a car
    //    following the holder in the same direction may join it. Released once the holder has driven out of it.
    // 3. The roundabout: cars on the ring always have priority. An entering car decides once, at its stop line (before the
    //    arm's crossing, or the ring edge on the arm without one), and waits while a ring car is coming towards its entry;
    //    past that line it never yields again, so nobody stands with its nose in the ring waiting for a ring car that is
    //    waiting for it.
    // 4. Two vehicles that see each other ahead (paths crossing) never both wait: the one on the ring / holding the junction,
    //    else the older one, goes. A car queued behind a waiting car just waits for it; any other hold that lasts too long
    //    creeps forward, so the city never freezes (never into people on a crossing).
    public static class CheckoutTrafficJunctions
    {
        sealed class Driver{public Transform t;public Vector3 dir=Vector3.forward,last;public float bodyFront=2.2f,bodyRear=2.2f,half=.95f,speed,seen=-10;public bool measured,waiting;}
        static readonly Dictionary<Transform,Driver> table=new Dictionary<Transform,Driver>();
        static readonly List<Driver> drivers=new List<Driver>();
        static readonly Dictionary<Transform,float> heldSince=new Dictionary<Transform,float>();
        static readonly List<Rect> crossings=new List<Rect>(); // x,z of the striped carriageway
        static readonly Vector3[] centers={new Vector3(-23.5f,0,-18.5f),new Vector3(23.5f,0,-18.5f)};
        static readonly List<Driver>[] holders={new List<Driver>(),new List<Driver>()};
        const float StopGap=.5f,Window=1f,StuckSeconds=8f,CreepSeconds=1.5f,QueueSeconds=20f,Lane=1.4f;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void Reset(){table.Clear();drivers.Clear();heldSince.Clear();crossings.Clear();foreach(var h in holders)h.Clear();agents=new NavMeshAgent[0];agentsAt=-10;peopleFrame=-1;}
        static Vector3 Flat(Vector3 v){v.y=0;return v;}
        static bool Live(Driver d)=>d.t&&d.t.gameObject.activeInHierarchy;

        // ------------------------------------------------------------------ crossings
        public static void ClearCrossings()=>crossings.Clear();
        /// <summary>A zebra from a to b (the walk strip of the navigation); only its part on the road is kept.</summary>
        public static void AddCrossing(Vector3 a,Vector3 b,float width)
        {
            float cx=(a.x+b.x)*.5f,cz=(a.z+b.z)*.5f,w=width*.5f;
            if(Mathf.Abs(a.x-b.x)>Mathf.Abs(a.z-b.z)){float half=(CheckoutStreetLayout.LocalCurbOuter-CheckoutStreetLayout.LocalCurbInner)*.5f;crossings.Add(Rect.MinMaxRect(cx-half,cz-w,cx+half,cz+w));}
            else crossings.Add(Rect.MinMaxRect(cx-w,CheckoutStreetLayout.AvenueCurbSouth,cx+w,CheckoutStreetLayout.AvenueCurbNorth));
        }
        public static IReadOnlyList<Rect> Crossings=>crossings;
        /// <summary>Whether `p` is on the striped (road) part of a crossing.</summary>
        public static bool IsOnCrossing(Vector3 p){var q=new Vector2(p.x,p.z);foreach(var c in crossings)if(c.Contains(q))return true;return false;}
        // People about to step on: the cycle lane beside the curb counts as part of the crossing.
        static Rect Watch(Rect r)=>r.width>r.height?Rect.MinMaxRect(r.xMin-CheckoutStreetLayout.LaneEnd,r.yMin-.3f,r.xMax+CheckoutStreetLayout.LaneEnd,r.yMax+.3f):Rect.MinMaxRect(r.xMin-.3f,r.yMin-CheckoutStreetLayout.LaneEnd,r.xMax+.3f,r.yMax+CheckoutStreetLayout.LaneEnd);

        // Distances along the line p + d*t where it is inside r (x,z); false when it misses.
        static bool Span(Vector3 p,Vector3 d,Rect r,out float t0,out float t1){t0=-1e5f;t1=1e5f;return Slab(p.x,d.x,r.xMin,r.xMax,ref t0,ref t1)&&Slab(p.z,d.z,r.yMin,r.yMax,ref t0,ref t1);}
        static bool Slab(float p,float d,float min,float max,ref float t0,ref float t1)
        {
            if(Mathf.Abs(d)<1e-5f)return p>min&&p<max;
            float a=(min-p)/d,b=(max-p)/d;if(a>b){float s=a;a=b;b=s;}
            t0=Mathf.Max(t0,a);t1=Mathf.Min(t1,b);return t0<t1;
        }

        /// <summary>Moves a stopping point (a drop-off) back along `dir` until a car standing there keeps its nose before every crossing.</summary>
        public static Vector3 OffCrossings(Vector3 p,Vector3 dir,float front=2.4f,float rear=2.4f)
        {
            dir=Flat(dir).normalized;
            for(int pass=0;pass<3;pass++)
            {
                bool moved=false;
                foreach(var c in crossings)
                    if(Span(p,dir,c,out float t0,out float t1)&&t0-StopGap<front&&t1+.3f>-rear){p+=dir*(t0-StopGap-front);moved=true;}
                if(!moved)break;
            }
            return p;
        }

        // ------------------------------------------------------------------ people on the crossings
        struct Walker{public int crossing;public Vector3 p,v;}
        static NavMeshAgent[] agents=new NavMeshAgent[0];static float agentsAt=-10;static int peopleFrame=-1;
        static readonly List<Walker> onCrossings=new List<Walker>();
        static void RefreshAgents(){if(Time.time-agentsAt>2f||Time.time<agentsAt){agents=Object.FindObjectsByType<NavMeshAgent>(FindObjectsSortMode.None);agentsAt=Time.time;}}
        static void ScanPeople()
        {
            if(peopleFrame==Time.frameCount)return;peopleFrame=Time.frameCount;onCrossings.Clear();
            if(crossings.Count==0)return;RefreshAgents();
            foreach(var a in agents)
            {
                if(!a||!a.isActiveAndEnabled)continue;var p=a.transform.position;var q=new Vector2(p.x,p.z);
                for(int i=0;i<crossings.Count;i++)if(Watch(crossings[i]).Contains(q)){onCrossings.Add(new Walker{crossing=i,p=p,v=a.velocity});break;}
            }
        }

        // ------------------------------------------------------------------ vehicles
        static Driver Track(Transform car,Vector3 dir)
        {
            if(!table.TryGetValue(car,out var d))
            {
                drivers.RemoveAll(x=>!x.t);
                d=new Driver{t=car,last=car.position};table[car]=d;drivers.Add(d);
            }
            if(!d.measured)Measure(d);
            float dt=Time.time-d.seen;var p=car.position;
            if(dt>1e-4f){d.speed=dt<.5f?Flat(p-d.last).magnitude/dt:0;d.last=p;d.seen=Time.time;}
            d.dir=dir;return d;
        }
        // Body length ahead of / behind the pivot and half width, from the renderers (cars, bikes and trucks differ).
        static void Measure(Driver d)
        {
            d.measured=true;var t=d.t;float lo=0,hi=0,side=0;bool any=false;
            foreach(var r in t.GetComponentsInChildren<Renderer>())
            {
                if(!(r is MeshRenderer)&&!(r is SkinnedMeshRenderer))continue; // the body, not particles, decals or trails
                var b=r.localBounds;
                for(int i=0;i<8;i++)
                {
                    var c=r.transform.TransformPoint(new Vector3((i&1)==0?b.min.x:b.max.x,(i&2)==0?b.min.y:b.max.y,(i&4)==0?b.min.z:b.max.z))-t.position;
                    float z=Vector3.Dot(c,t.forward),x=Mathf.Abs(Vector3.Dot(c,t.right));
                    if(!any){lo=hi=z;side=x;any=true;}else{lo=Mathf.Min(lo,z);hi=Mathf.Max(hi,z);side=Mathf.Max(side,x);}
                }
            }
            if(any&&hi-lo>.8f&&hi-lo<16f){d.bodyFront=Mathf.Clamp(hi,.3f,10f);d.bodyRear=Mathf.Clamp(-lo,.3f,10f);d.half=Mathf.Clamp(side,.3f,1.6f);}
        }
        // Length ahead of / behind the pivot along the way it moves (reversing swaps them).
        static void Lengths(Driver d,Vector3 dir,out float front,out float rear)
        {
            bool backwards=d.t&&Vector3.Dot(Flat(d.t.forward),dir)< -.3f;
            front=backwards?d.bodyRear:d.bodyFront;rear=backwards?d.bodyFront:d.bodyRear;
        }

        // ------------------------------------------------------------------ the one entry point
        /// <summary>True while the vehicle must stay put this frame. `stopDistance` is how far it still rolls once told
        /// to stop (vehicles with inertia), so it is told early enough to stop before the stripes.</summary>
        public static bool Hold(Transform car,Vector3 direction,bool blocked,float stopDistance=0)
        {
            direction.y=0;if(direction.sqrMagnitude<1e-6f)return blocked;direction.Normalize();
            var me=Track(car,direction);var pos=car.position;Lengths(me,direction,out float front,out float rear);
            float window=Window+Mathf.Max(0,stopDistance);
            // Someone on the crossing ahead: wait at the stop line, never crept through.
            bool noRoom=Gate(me,pos,direction,front,rear,window,out bool people);
            if(people){heldSince.Remove(car);return me.waiting=true;}
            if(blocked&&GoesFirst(me,pos,direction,front))blocked=false;
            bool wait=blocked||noRoom||MustWait(me,pos,direction,front,rear,window);
            if(!wait){heldSince.Remove(car);return me.waiting=false;}
            float now=Time.time;
            if(!heldSince.TryGetValue(car,out float since)){heldSince[car]=now;return me.waiting=true;}
            // Queued behind a vehicle that is itself waiting: its own rule lets it go, the queue follows.
            if(blocked&&now-since<QueueSeconds&&BehindWaiting(me,pos,direction))return me.waiting=true;
            if(now-since<StuckSeconds)return me.waiting=true;
            if(now-since>StuckSeconds+CreepSeconds)heldSince[car]=now;
            return me.waiting=false;
        }

        // Crossings just ahead (the nose within `window` of the stop line): people heading into this lane, or no room past them.
        static bool Gate(Driver me,Vector3 pos,Vector3 dir,float front,float rear,float window,out bool people)
        {
            people=false;bool noRoom=false;
            for(int i=0;i<crossings.Count;i++)
            {
                if(!Span(pos,dir,crossings[i],out float t0,out float t1)||t1<=0)continue;
                float line=t0-StopGap-front;if(line<0||line>window)continue;
                ScanPeople();var side=new Vector3(-dir.z,0,dir.x);
                foreach(var w in onCrossings)
                {
                    if(w.crossing!=i)continue;
                    float s=Vector3.Dot(Flat(w.p-pos),side),v=Vector3.Dot(Flat(w.v),side);
                    // In (or next to) this lane, or walking towards it and there within ~3.5 s.
                    if(Mathf.Abs(s)<1.9f||(Mathf.Abs(s)<6.5f&&s*v<0&&Mathf.Abs(s)<3.5f*Mathf.Abs(v))){people=true;return noRoom;}
                }
                if(!noRoom&&RoomTaken(me,pos,dir,t1+rear+.3f,front))noRoom=true;
            }
            return noRoom;
        }
        // Something in this lane before the point where the tail has cleared the stripes (`need` metres on, plus a gap).
        static bool RoomTaken(Driver me,Vector3 pos,Vector3 dir,float need,float front)
        {
            foreach(var o in drivers)
            {
                if(o==me||!Live(o))continue;
                var delta=Flat(o.t.position-pos);float f=Vector3.Dot(delta,dir);if(f<=0)continue;
                if((delta-dir*f).sqrMagnitude>Lane*Lane)continue;
                float back=Vector3.Dot(Flat(o.t.forward),dir)>=0?o.bodyRear:o.bodyFront;
                // A car driving on ahead will have moved on by then (keeping the gap is the caller's following check).
                bool moving=Time.time-o.seen<.5f&&o.speed>2f;
                if(f-back<(moving?1.5f:need+.6f))return true;
            }
            return CheckoutEventTraffic.Blocks(pos+dir*front,dir,Mathf.Max(.5f,need+.6f-front),.9f,me.t);
        }

        static bool MustWait(Driver me,Vector3 pos,Vector3 dir,float front,float rear,float window)
        {
            var circle=CheckoutRoundabout.Current;
            for(int i=0;i<centers.Length;i++)
            {
                if(circle&&Flat(circle.center-centers[i]).magnitude<1){if(YieldAtEntry(me,pos,dir,front,rear,circle,window))return true;continue;}
                if(Reserve(i,me,pos,dir,front,window))return true;
            }
            return false;
        }

        // ------------------------------------------------------------------ plain junction: reserve the box at the stop line
        // The box plus the crossings on its four arms (a car waiting for it stands before the stripes).
        static Rect Zone(Vector3 c)
        {
            float hx=CheckoutStreetLayout.OuterWalkX-(CheckoutStreetLayout.LocalCurbInner+CheckoutStreetLayout.LocalCurbOuter)*.5f+.8f;
            float hz=(CheckoutStreetLayout.AvenueCurbNorth+CheckoutStreetLayout.AvenueCurbSouth)*.5f-CheckoutStreetLayout.SouthWalkZ+.8f;
            return Rect.MinMaxRect(c.x-hx,c.z-hz,c.x+hx,c.z+hz);
        }
        static bool Reserve(int i,Driver me,Vector3 pos,Vector3 dir,float front,float window)
        {
            var zone=Zone(centers[i]);var list=holders[i];
            list.RemoveAll(h=>!Live(h)||Time.time-h.seen>.6f||Left(h,zone));
            if(list.Contains(me))return false;
            if(zone.Contains(new Vector2(pos.x,pos.z))){if(CanJoin(list,me,pos,dir))list.Add(me);return false;} // already in: drive out
            if(!Span(pos,dir,zone,out float t0,out float t1)||t0<0)return false;
            float line=t0-StopGap-front;
            if(line>window)return false;
            if(CanJoin(list,me,pos,dir)){list.Add(me);return false;}
            return line>-StopGap; // nose not on the stripes yet: wait at the line
        }
        static bool Left(Driver h,Rect zone)
        {
            var p=h.t.position;float reach=Mathf.Max(h.bodyFront,h.bodyRear);
            var grown=Rect.MinMaxRect(zone.xMin-reach,zone.yMin-reach,zone.xMax+reach,zone.yMax+reach);
            return !grown.Contains(new Vector2(p.x,p.z))&&Vector3.Dot(new Vector3(zone.center.x-p.x,0,zone.center.y-p.z),h.dir)<0;
        }
        // Free, or every holder is ahead of this car going the same way (same lane, or a parallel one).
        static bool CanJoin(List<Driver> list,Driver me,Vector3 pos,Vector3 dir)
        {
            foreach(var h in list)
            {
                if(Vector3.Dot(h.dir,dir)<.95f)return false;
                var delta=Flat(h.t.position-pos);float f=Vector3.Dot(delta,dir);if(f<=0)return false;
                float lateral=(delta-dir*f).magnitude;if(lateral>Lane&&lateral<2.4f)return false;
            }
            return true;
        }

        // ------------------------------------------------------------------ roundabout: yield once, at the stop line
        // Counter-clockwise circulation. Cars on the ring never yield; an entering car waits at its stop line while a ring
        // car is coming towards its entry point (how far upstream it looks grows with the way still to go to the ring).
        static bool YieldAtEntry(Driver me,Vector3 pos,Vector3 dir,float front,float rear,CheckoutRoundabout circle,float window)
        {
            var d=Flat(pos-circle.center);float r=d.magnitude;
            if(r<circle.clipRadius-.1f||r>circle.clipRadius+25f||Vector3.Dot(-d/r,dir)<.25f)return false;
            if(!RayCircle(pos,dir,circle.center,circle.outerRadius,out float ring))return false;
            float line=ring;
            // The arm's own crossing (CheckoutStreetLayout.CircleCrossing), not one further along the street.
            foreach(var c in crossings)if(Span(pos,dir,c,out float t0,out float t1)&&t1>-rear&&t0<ring&&Flat(pos+dir*t0-circle.center).magnitude<CheckoutStreetLayout.CircleCrossing+2f)line=Mathf.Min(line,t0);
            line-=StopGap+front;
            if(line<0||line>window)return false; // committed, or not at the line yet
            var entry=pos+dir*ring;float angle=Mathf.Atan2(entry.z-circle.center.z,entry.x-circle.center.x);
            float reach=Mathf.Clamp(.9f+.15f*ring,1.2f,2.3f);
            foreach(var o in drivers)
            {
                if(o==me||!Live(o))continue;
                var od=Flat(o.t.position-circle.center);float radius=od.magnitude;
                if(radius>circle.outerRadius+.3f)continue;
                if(Time.time-o.seen<.5f&&radius>.01f&&Vector3.Dot(od/radius,o.dir)>.35f)continue; // turning off the ring
                float upstream=Mathf.Repeat(angle-Mathf.Atan2(od.z,od.x),Mathf.PI*2);
                if(upstream<reach||upstream>Mathf.PI*2-.25f)return true;
            }
            return false;
        }
        static bool RayCircle(Vector3 p,Vector3 d,Vector3 c,float radius,out float t)
        {
            var f=Flat(p-c);float b=Vector3.Dot(f,d),k=f.sqrMagnitude-radius*radius,disc=b*b-k;
            t=0;if(disc<0)return false;t=-b-Mathf.Sqrt(disc);return t>=0;
        }

        // ------------------------------------------------------------------ two vehicles waiting for each other
        static int Rank(Driver d)
        {
            var circle=CheckoutRoundabout.Current;
            if(circle&&Flat(d.t.position-circle.center).magnitude<circle.clipRadius)return 2;
            foreach(var h in holders)if(h.Contains(d))return 1;
            return 0;
        }
        // Blocked only by vehicles that are blocked by this one: exactly one of each such pair goes, at once.
        static bool GoesFirst(Driver me,Vector3 pos,Vector3 dir,float front)
        {
            bool mutual=false;int rank=Rank(me);
            foreach(var o in drivers)
            {
                if(o==me||!Live(o))continue;
                var delta=Flat(o.t.position-pos);float f=Vector3.Dot(delta,dir);
                if(f<=0||f>5f||(delta-dir*f).sqrMagnitude>Lane*Lane)continue;
                var back=-delta;float g=Vector3.Dot(back,o.dir);
                if(Time.time-o.seen>.5f||g<=0||g>5f||(back-o.dir*g).sqrMagnitude>Lane*Lane)return false; // a real queue
                int other=Rank(o);
                if(other>rank||(other==rank&&o.t.GetEntityId().GetHashCode()<me.t.GetEntityId().GetHashCode()))return false;
                mutual=true;
            }
            if(!mutual)return false;
            RefreshAgents();
            foreach(var a in agents)
            {
                if(!a||!a.isActiveAndEnabled)continue;
                var delta=Flat(a.transform.position-pos);float f=Vector3.Dot(delta,dir);
                if(f>0&&f<front+1.2f&&(delta-dir*f).sqrMagnitude<1.2f*1.2f)return false;
            }
            return !CheckoutEventTraffic.Blocks(pos+dir*front,dir,2.6f,.9f,me.t);
        }
        static bool BehindWaiting(Driver me,Vector3 pos,Vector3 dir)
        {
            foreach(var o in drivers)
            {
                if(o==me||!Live(o)||!o.waiting||Time.time-o.seen>.5f)continue;
                var delta=Flat(o.t.position-pos);float f=Vector3.Dot(delta,dir);
                if(f>0&&f<5.5f&&(delta-dir*f).sqrMagnitude<Lane*Lane)return true;
            }
            return false;
        }

        public static bool Ahead(Vector3 from,Vector3 direction,Vector3 other,float distance,float halfWidth=1.15f)
        {
            var delta=other-from;delta.y=0;float ahead=Vector3.Dot(delta,direction);
            return ahead>0&&ahead<distance&&(delta-direction*ahead).sqrMagnitude<halfWidth*halfWidth;
        }

        // ------------------------------------------------------------------ for people on foot and QA
        // Points along a vehicle's body (three lines, nose to tail) in its own orientation.
        static bool BodyHits(Driver d,System.Func<Vector3,bool> hit)
        {
            var p=Flat(d.t.position);var f=Flat(d.t.forward).normalized;var s=new Vector3(-f.z,0,f.x)*(d.half*.85f);
            for(float z=-d.bodyRear;z<=d.bodyFront+.01f;z+=.5f){var q=p+f*z;if(hit(q)||hit(q+s)||hit(q-s))return true;}
            return false;
        }
        /// <summary>For pedestrians: true while a vehicle stands on, or is about to drive over, the crossing at `point`
        /// (a person should wait at the curb instead of walking into it).</summary>
        public static bool CrossingBusy(Vector3 point)
        {
            var q=new Vector2(point.x,point.z);int index=-1;
            for(int i=0;i<crossings.Count;i++)if(Watch(crossings[i]).Contains(q)){index=i;break;}
            if(index<0)return false;var c=crossings[index];
            foreach(var d in drivers)
            {
                if(!Live(d))continue;
                if(BodyHits(d,p=>c.Contains(new Vector2(p.x,p.z))))return true;
                // Driving towards it and past the stop line already (it will not stop any more).
                if(Time.time-d.seen<.5f&&d.speed>.5f&&Span(d.t.position,d.dir,c,out float t0,out float t1)&&t1>0&&t0>0&&t0<d.bodyFront+StopGap+.2f)return true;
            }
            return false;
        }
        public static string QaBody(Transform car)=>table.TryGetValue(car,out var d)?$"front {d.bodyFront:0.00} rear {d.bodyRear:0.00} half width {d.half:0.00}":"not tracked";
        public static List<Transform> QaVehicles(){var list=new List<Transform>();foreach(var d in drivers)if(Live(d))list.Add(d.t);return list;}
        public static bool QaOnCrossing(Transform car)
        {
            if(!table.TryGetValue(car,out var d)||!Live(d))return false;
            foreach(var c in crossings)if(BodyHits(d,p=>c.Contains(new Vector2(p.x,p.z))))return true;
            return false;
        }
        public static bool QaInside(Transform car,Vector3 point,float pad=0)
        {
            if(!table.TryGetValue(car,out var d)||!Live(d))return false;
            var delta=Flat(point-car.position);var f=Flat(car.forward).normalized;float z=Vector3.Dot(delta,f),x=Mathf.Abs(Vector3.Dot(delta,new Vector3(-f.z,0,f.x)));
            return z>-d.bodyRear-pad&&z<d.bodyFront+pad&&x<d.half+pad;
        }
        /// <summary>Inside a junction: a plain junction's box with its crossings, or the roundabout out to its crossings.</summary>
        public static bool QaInJunction(Vector3 p)
        {
            var circle=CheckoutRoundabout.Current;var q=new Vector2(p.x,p.z);
            foreach(var c in centers)
            {
                if(circle&&Flat(circle.center-c).magnitude<1){if(Flat(p-circle.center).magnitude<CheckoutStreetLayout.CircleCrossing+.8f)return true;continue;}
                if(Zone(c).Contains(q))return true;
            }
            return false;
        }
    }
}
