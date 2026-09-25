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
            streets=FindAnyObjectByType<CheckoutCityStreets>();
            body=GetComponentsInChildren<Renderer>().Where(r=>r.enabled).ToArray();
            if(!NavMesh.SamplePosition(home,out var hit,12,NavMesh.AllAreas)){enabled=false;return;}
            agent.Warp(hit.position);
            destination=Mathf.Abs(GetEntityId().GetHashCode()) % streets.entrances.Length;
            VisitNext();
        }
        void Update()
        {
            if(!agent||!agent.isOnNavMesh)return;
            var velocity=agent.velocity;velocity.y=0;
            if(velocity.sqrMagnitude>.004f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(-velocity),Time.deltaTime*180);
            if(agent.pathPending||agent.remainingDistance>.35f)return;
            wait+=Time.deltaTime;
            if(visitingBuilding && !inside && wait>.2f){inside=true;foreach(var r in body)r.enabled=false;}
            if(wait<(visitingBuilding?1.2f:.1f))return;
            if(inside){foreach(var r in body)r.enabled=true;inside=false;CheckoutShoppingProps.SetVisible(transform,false);}
            wait=0;completedVisits++;VisitNext();
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
