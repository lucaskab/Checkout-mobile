using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using MarketDay;
namespace Checkout {
 public class CheckoutWalker:MonoBehaviour {
  CheckoutBridge bridge;CheckoutMap map;NavMeshAgent agent;MarketCharacterAnimator motion;Customer customer;int phase,index;float wait;bool cart;Vector3 target;Quaternion facing;
  public void Initialize(CheckoutBridge owner,NavMeshAgent navigation,CheckoutMap projection){bridge=owner;map=projection;agent=navigation;motion=GetComponent<MarketCharacterAnimator>();cart=name=="Customer_02"||name=="Customer_05";agent.avoidancePriority=40+(cart?5:0);}
  public void Begin(Customer visit){customer=visit;phase=0;index=0;wait=0;gameObject.SetActive(true);var spawn=new Vector3(-1.75f,.3f,-8.7f);NavMesh.SamplePosition(spawn,out var hit,2,NavMesh.AllAreas);agent.Warp(hit.position);transform.rotation=Quaternion.Euler(0,180,0);Sync();NextShelf();}
  void Go(Vector3 destination){if(NavMesh.SamplePosition(destination,out var hit,2,NavMesh.AllAreas))destination=hit.position;target=destination;agent.isStopped=false;agent.SetDestination(destination);}
  void NextShelf(){if(customer.purchases!=null&&index<customer.purchases.Length){phase=0;Go(map.Approach(customer.purchases[index].shelfId));}else {phase=2;Go(new Vector3(-7.2f,.74f,-3.4f));}}
  void Update(){if(!agent.isOnNavMesh)return;
   if(wait>0){wait-=Time.deltaTime;agent.isStopped=true;transform.rotation=Quaternion.RotateTowards(transform.rotation,facing,Time.deltaTime*180);Sync();if(wait<=0){if(phase==1){index++;NextShelf();}else if(phase==4){bridge.Queue.Remove(this);phase=5;Go(new Vector3(-1.75f,.3f,-8.7f));}}return;}
   if(phase==3){var q=bridge.Queue.IndexOf(this);var position=QueuePosition(q);if((position-target).sqrMagnitude>.05f)Go(position);}
   agent.speed=cart?.88f:1.04f;agent.acceleration=3.5f;
   var velocity=agent.velocity;velocity.y=0;if(velocity.sqrMagnitude>.004f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(-velocity),Time.deltaTime*(cart?145:230));Sync();
   bool arrived=!agent.pathPending&&((agent.hasPath&&agent.remainingDistance<.25f)||Vector3.Distance(agent.nextPosition,target)<.3f);
   if(!arrived)return;agent.isStopped=true;
   if(phase==0){var id=customer.purchases[index].shelfId;var direction=map.Fixture(id)-transform.position;direction.y=0;facing=Quaternion.LookRotation(-direction);phase=1;wait=motion.Perform(map.Special(id)?"BuyAtSpecialSector":"GetFromShelf");}
   else if(phase==2){bridge.Queue.Add(this);phase=3;Go(QueuePosition(bridge.Queue.IndexOf(this)));}
   else if(phase==3&&bridge.Queue.Count>0&&bridge.Queue[0]==this){if(customer.spent<=0){bridge.Queue.Remove(this);phase=5;Go(new Vector3(-1.75f,.3f,-8.7f));return;}phase=4;facing=Quaternion.LookRotation(-(new Vector3(-3.5f,.74f,-5.7f)-transform.position));wait=motion.Perform("PayAtCheckout");}
   else if(phase==5){gameObject.SetActive(false);}
  }
  void Sync(){transform.position=agent.nextPosition+(cart?transform.forward*.55f:Vector3.zero);var p=transform.position;p.y=MarketSimulation.Ground(p.z);transform.position=p;}
  static Vector3 QueuePosition(int i){Vector3[] p={new Vector3(-4.9f,.74f,-6.2f),new Vector3(-6.05f,.74f,-6.2f),new Vector3(-7.2f,.74f,-6.2f),new Vector3(-7.2f,.74f,-5.05f),new Vector3(-7.2f,.74f,-3.9f)};return p[Mathf.Clamp(i,0,4)];}
 }
}
