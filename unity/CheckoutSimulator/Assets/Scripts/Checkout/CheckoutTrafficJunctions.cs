using System.Collections.Generic;
using UnityEngine;

namespace Checkout
{
    // Shared by both traffic pools. A plain junction is owned by one car until it clears the exit;
    // the roundabout instead uses yield-at-entry, so cars already circulating always keep moving.
    // A car held for too long creeps forward anyway: the city must never freeze in a gridlock.
    public static class CheckoutTrafficJunctions
    {
        static readonly Vector3[] centers={new Vector3(-23.5f,0,-18.5f),new Vector3(23.5f,0,-18.5f)};
        static readonly Transform[] owners=new Transform[2];
        static readonly List<Transform> drivers=new List<Transform>();
        static readonly Dictionary<Transform,float> heldSince=new Dictionary<Transform,float>();
        const float StuckSeconds=5f,CreepSeconds=1.5f;
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void Reset(){System.Array.Clear(owners,0,owners.Length);drivers.Clear();heldSince.Clear();}
        static float Distance(Vector3 a,Vector3 b)=>Mathf.Max(Mathf.Abs(a.x-b.x),Mathf.Abs(a.z-b.z));

        // Single entry point for both pools: true while the car must stay put this frame.
        public static bool Hold(Transform car,Vector3 direction,bool blocked)
        {
            if(!blocked&&!MustWait(car,direction)){heldSince.Remove(car);return false;}
            float now=Time.time;
            if(!heldSince.TryGetValue(car,out float since)){heldSince[car]=now;return true;}
            if(now-since<StuckSeconds)return true;
            if(now-since>StuckSeconds+CreepSeconds)heldSince[car]=now;
            return false;
        }

        public static bool MustWait(Transform car,Vector3 direction)
        {
            if(!drivers.Contains(car))drivers.Add(car);
            var circle=CheckoutRoundabout.Current;
            for(int i=0;i<centers.Length;i++)
            {
                if(circle&&Distance(circle.center,centers[i])<1){if(YieldAtEntry(car,direction,circle))return true;continue;}
                var owner=owners[i];
                if(owner&&(!owner.gameObject.activeInHierarchy||Distance(owner.position,centers[i])>8.5f))owners[i]=null;
                float distance=Distance(car.position,centers[i]);
                if(distance>8.5f||Vector3.Dot(centers[i]-car.position,direction)<-3)continue;
                if(!owners[i])owners[i]=car;
                if(owners[i]!=car)return true;
            }
            return false;
        }

        // Counter-clockwise circulation: a car about to enter gives way to any car on the ring
        // that is coming towards its entry point (up to ~95 degrees upstream).
        static bool YieldAtEntry(Transform car,Vector3 direction,CheckoutRoundabout circle)
        {
            var d=car.position-circle.center;d.y=0;float r=d.magnitude;
            if(r<circle.clipRadius-.25f||r>circle.clipRadius+2.5f||Vector3.Dot(-d,direction)<=0)return false;
            float entry=Mathf.Atan2(d.z,d.x);
            drivers.RemoveAll(t=>!t);
            foreach(var other in drivers)
            {
                if(other==car||!other.gameObject.activeInHierarchy)continue;
                var o=other.position-circle.center;o.y=0;
                if(o.magnitude>circle.clipRadius-.25f)continue;
                float upstream=Mathf.Repeat(entry-Mathf.Atan2(o.z,o.x),Mathf.PI*2);
                if(upstream>.05f&&upstream<1.65f)return true;
            }
            return false;
        }

        public static bool Ahead(Vector3 from,Vector3 direction,Vector3 other,float distance,float halfWidth=1.15f)
        {
            var delta=other-from;delta.y=0;float ahead=Vector3.Dot(delta,direction);
            return ahead>0&&ahead<distance&&(delta-direction*ahead).sqrMagnitude<halfWidth*halfWidth;
        }
    }
}
