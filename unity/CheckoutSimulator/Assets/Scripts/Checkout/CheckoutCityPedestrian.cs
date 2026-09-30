using UnityEngine;
using UnityEngine.AI;
using System.Linq;

namespace Checkout
{
    [DefaultExecutionOrder(100)]
    public class CheckoutCityPedestrian : MonoBehaviour
    {
        public Vector3 home;
        NavMeshAgent agent;
        CheckoutCityStreets streets;
        int destination;
        public int completedVisits { get; private set; }
        public bool IsSheltered => inside;
        float wait;
        Renderer[] body;
        bool visitingBuilding, inside;
        void OnEnable(){CheckoutShoppingProps.SetVisible(transform,false);}
        void Start()
        {
            agent=GetComponent<NavMeshAgent>();
            // The rigs face -Z, so this script owns the heading. Letting the agent rotate the transform
            // as well made the two fight: characters left doorways sideways and slowly turned.
            agent.updateRotation=false;
            streets=FindAnyObjectByType<CheckoutCityStreets>();
            body=GetComponentsInChildren<Renderer>().Where(r=>r.enabled).ToArray();
            // Passers-by stay on the city surfaces: the shop floor, its ramps and the service path out back
            // are baked as ShopArea, so nobody uses the supermarket as a shortcut across the block.
            agent.areaMask&=~(1<<MarketDay.MarketSimulation.ShopArea);
            if(!NavMesh.SamplePosition(home,out var hit,12,agent.areaMask)){enabled=false;return;}
            agent.Warp(hit.position);
            destination=Mathf.Abs(GetEntityId().GetHashCode()) % streets.entrances.Length;
            VisitNext();
            FacePath();
        }
        void Update()
        {
            if(!agent||!agent.isOnNavMesh)return;
            var heading=agent.desiredVelocity;heading.y=0;
            if(heading.sqrMagnitude<.004f){heading=agent.velocity;heading.y=0;}
            if(heading.sqrMagnitude>.004f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(-heading),Time.deltaTime*540);
            if(agent.pathPending||agent.remainingDistance>.35f)return;
            wait+=Time.deltaTime;
            if(visitingBuilding && !inside && wait>.2f){inside=true;agent.isStopped=true;foreach(var r in body)r.enabled=false;}
            if(wait<(visitingBuilding?1.2f:.1f))return;
            wait=0;completedVisits++;VisitNext();
            if(inside)
            {
                // Step out already facing the street: plan the next route first, turn to it, then appear.
                agent.isStopped=false;FacePath();
                foreach(var r in body)r.enabled=true;inside=false;CheckoutShoppingProps.SetVisible(transform,false);
            }
        }
        void FacePath()
        {
            if(!agent.hasPath)return;
            var corners=agent.path.corners;
            for(int i=0;i<corners.Length;i++)
            {
                var direction=corners[i]-transform.position;direction.y=0;
                if(direction.sqrMagnitude>.01f){transform.rotation=Quaternion.LookRotation(-direction);return;}
            }
        }
        void VisitNext()
        {
            var points=completedVisits%2==0?streets.entrances:streets.patrolPoints;
            visitingBuilding=completedVisits%2==0;
            for(int i=0;i<points.Length;i++)
            {
                destination=(destination+1)%points.Length;
                var path=new NavMeshPath();
                if(agent.CalculatePath(points[destination],path)&&path.status==NavMeshPathStatus.PathComplete){agent.SetPath(path);return;}
            }
        }
    }
}
