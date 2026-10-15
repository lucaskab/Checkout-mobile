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
        float stalled, holdFor; int stalls;
        bool curbWait; Vector3 curbPoint;
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
            // Sidewalk manners (Lucas 15/10: people bumped and shoved each other). Everyone had the same avoidance
            // priority, so two people meeting head-on both pushed; now each has its own, the higher one yields.
            // Good-quality avoidance, a slimmer body, and see Update for the stall handling.
            int seed=Mathf.Abs(GetEntityId().GetHashCode());
            agent.avoidancePriority=25+seed%50;agent.obstacleAvoidanceType=ObstacleAvoidanceType.HighQualityObstacleAvoidance;agent.radius=Mathf.Min(agent.radius,.3f);
            agent.speed*=.92f+(seed%17)*.01f; // Not everyone walks at the same pace (fewer people stuck in step side by side).
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
            if(agent.pathPending)return;
            // At the curb: a car on the zebra crossing (or already past its stop line) goes first; then cross.
            if(!inside)
            {
                var step=agent.desiredVelocity;step.y=0;
                var ahead=transform.position+(step.sqrMagnitude>.01f?step.normalized*1.2f:Vector3.zero);
                bool atCurb=step.sqrMagnitude>.01f&&!CheckoutTrafficJunctions.IsOnCrossing(transform.position)&&CheckoutTrafficJunctions.IsOnCrossing(ahead);
                if((atCurb||curbWait)&&CheckoutTrafficJunctions.CrossingBusy(curbWait?curbPoint:ahead)){if(!curbWait){curbWait=true;curbPoint=ahead;}agent.isStopped=true;return;}
                if(curbWait){curbWait=false;agent.isStopped=false;}
            }
            if(agent.remainingDistance>.35f)
            {
                // Blocked by someone (or someone already standing on the spot): close to the spot counts as there;
                // otherwise stop and let the other one pass for a moment instead of shoving, and after a few
                // tries pick another destination.
                if(holdFor>0){holdFor-=Time.deltaTime;if(holdFor<=0)agent.isStopped=false;return;}
                if(agent.velocity.sqrMagnitude<.04f&&agent.desiredVelocity.sqrMagnitude>.01f)stalled+=Time.deltaTime;else stalled=0;
                if(stalled<.9f)return;
                stalled=0;
                if(agent.remainingDistance<1.6f){agent.ResetPath();}
                else if(++stalls<3){agent.isStopped=true;holdFor=Random.Range(.5f,1.1f);return;}
                else{stalls=0;completedVisits++;visitingBuilding=false;VisitNext();return;}
            }
            stalls=0;
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
                // Patrol points get a small personal offset, so two people heading for the same corner don't
                // fight for the exact same spot (building doors stay exact: they walk in there).
                var goal=points[destination];
                if(!visitingBuilding){var offset=Random.insideUnitCircle*.9f;if(NavMesh.SamplePosition(goal+new Vector3(offset.x,0,offset.y),out var near,.6f,agent.areaMask))goal=near.position;}
                if(agent.CalculatePath(goal,path)&&path.status==NavMeshPathStatus.PathComplete){agent.SetPath(path);return;}
            }
        }
    }
}
