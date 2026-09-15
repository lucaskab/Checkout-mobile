using UnityEngine;
using UnityEngine.AI;

namespace Checkout
{
    [DefaultExecutionOrder(100)]
    public class CheckoutCityPedestrian : MonoBehaviour
    {
        public Vector3 home;
        NavMeshAgent agent;
        bool returning;
        float wait;
        void OnEnable(){CheckoutShoppingProps.SetVisible(transform,false);}
        void Start()
        {
            agent=GetComponent<NavMeshAgent>();
            if(!NavMesh.SamplePosition(home,out var hit,1.5f,NavMesh.AllAreas)){enabled=false;return;}
            agent.Warp(hit.position);agent.SetDestination(new Vector3(-16f,.15f,20f));
        }
        void Update()
        {
            if(!agent||!agent.isOnNavMesh)return;
            var velocity=agent.velocity;velocity.y=0;
            if(velocity.sqrMagnitude>.004f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(-velocity),Time.deltaTime*180);
            if(agent.pathPending||agent.remainingDistance>.35f)return;
            wait+=Time.deltaTime;
            if(wait<5)return;
            wait=0;returning=!returning;
            agent.SetDestination(returning?home:new Vector3(-16f,.15f,20f));
        }
    }
}
