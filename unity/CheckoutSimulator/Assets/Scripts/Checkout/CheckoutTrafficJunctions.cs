using UnityEngine;

namespace Checkout
{
    // Shared by both traffic pools: one car owns a junction until it clears the exit.
    public static class CheckoutTrafficJunctions
    {
        static readonly Vector3[] centers={new Vector3(-23.5f,0,-15.5f),new Vector3(23.5f,0,-15.5f),new Vector3(-23.5f,0,30),new Vector3(23.5f,0,30)};
        static readonly Transform[] owners=new Transform[4];
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        static void Reset(){System.Array.Clear(owners,0,owners.Length);}
        static float Distance(Vector3 a,Vector3 b)=>Mathf.Max(Mathf.Abs(a.x-b.x),Mathf.Abs(a.z-b.z));
        public static bool MustWait(Transform car,Vector3 direction)
        {
            for(int i=0;i<centers.Length;i++)
            {
                var owner=owners[i];
                if(owner&&(!owner.gameObject.activeInHierarchy||Distance(owner.position,centers[i])>8.5f))owners[i]=null;
                float distance=Distance(car.position,centers[i]);
                if(distance>8.5f||Vector3.Dot(centers[i]-car.position,direction)<-3)continue;
                if(!owners[i])owners[i]=car;
                if(owners[i]!=car)return true;
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
