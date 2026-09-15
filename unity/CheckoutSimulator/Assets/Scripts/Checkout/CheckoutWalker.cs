using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using MarketDay;
namespace Checkout {
 public class CheckoutWalker:MonoBehaviour {
  CheckoutBridge bridge;CheckoutMap map;NavMeshAgent agent;MarketCharacterAnimator motion;Customer customer;int phase,index;float wait;bool cart;Vector3 target;Quaternion facing;
  public void Initialize(CheckoutBridge owner,NavMeshAgent navigation,CheckoutMap projection){bridge=owner;map=projection;agent=navigation;motion=GetComponent<MarketCharacterAnimator>();cart=name=="Customer_02"||name=="Customer_05"||name=="Customer_07";agent.avoidancePriority=40+(cart?5:0);}
  public bool Reserved {get;private set;}
  public bool HasPaid {get;private set;}
  public Vector3 CarDoor=>parkingDoor;
  public int VisitPhase=>phase;
  Vector3 parkingDoor;System.Action<CheckoutWalker> returnedToCar;
  public void Reserve(){Reserved=true;CheckoutShoppingProps.SetVisible(transform,false);}
  public void CancelVisit(){if(agent&&agent.isOnNavMesh){agent.ResetPath();agent.isStopped=true;}bridge.Queue.Remove(this);returnedToCar=null;Reserved=false;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);}
  public void BeginFromCar(Customer visit,Vector3 door,System.Action<CheckoutWalker> completed){parkingDoor=door;returnedToCar=completed;customer=visit;phase=9;index=0;wait=0;HasPaid=false;Reserved=true;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(true);if(!NavMesh.SamplePosition(door,out var hit,.8f,NavMesh.AllAreas)||!agent.Warp(hit.position))throw new System.InvalidOperationException("Parking door is outside the customer NavMesh");Sync();Go(new Vector3(-19.5f,.15f,parkingDoor.z));}
  public void Begin(Customer visit){returnedToCar=null;HasPaid=false;Reserved=true;customer=visit;phase=0;index=0;wait=0;gameObject.SetActive(true);var spawn=new Vector3(-1.75f,.3f,-8.7f);NavMesh.SamplePosition(spawn,out var hit,2,NavMesh.AllAreas);agent.Warp(hit.position);transform.rotation=Quaternion.Euler(0,180,0);Sync();NextShelf();}
  void Go(Vector3 destination){if(NavMesh.SamplePosition(destination,out var hit,2,NavMesh.AllAreas))destination=hit.position;target=destination;agent.isStopped=false;agent.SetDestination(destination);}
  void NextShelf(){CheckoutShoppingProps.SetVisible(transform,customer.purchases!=null&&customer.purchases.Length>0);if(customer.purchases!=null&&index<customer.purchases.Length){phase=0;Go(map.Approach(customer.purchases[index].shelfId));}else {phase=2;Go(new Vector3(-7.2f,.74f,-3.4f));}}
  void Update(){if(!agent.isOnNavMesh)return;
   if(wait>0){wait-=Time.deltaTime;agent.isStopped=true;transform.rotation=Quaternion.RotateTowards(transform.rotation,facing,Time.deltaTime*180);Sync();if(wait<=0){if(phase==1){index++;NextShelf();}else if(phase==8){phase=4;wait=Mathf.Max(motion.Perform("PayAtCheckout"),map.PaymentDuration);}else if(phase==4){HasPaid=true;bridge.Queue.Remove(this);phase=5;Go(new Vector3(-1.75f,.3f,-8.7f));}}return;}
   if(phase==3){var q=bridge.Queue.IndexOf(this);var position=QueuePosition(q);if((position-target).sqrMagnitude>.05f)Go(position);}
   agent.speed=cart?.88f:1.04f;agent.acceleration=3.5f;
   var velocity=agent.velocity;velocity.y=0;if(velocity.sqrMagnitude>.004f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(-velocity),Time.deltaTime*(cart?145:230));Sync();
   bool arrived=!agent.pathPending&&((agent.hasPath&&agent.pathStatus==NavMeshPathStatus.PathComplete&&agent.remainingDistance<.25f)||Vector3.Distance(agent.nextPosition,target)<.3f);
   if(!arrived)return;agent.isStopped=true;
   if(phase==0){var id=customer.purchases[index].shelfId;var direction=map.Fixture(id)-transform.position;direction.y=0;facing=Quaternion.LookRotation(-direction);phase=1;agent.velocity=Vector3.zero;wait=Mathf.Max(1.5f,motion.Perform(map.Special(id)?"BuyAtSpecialSector":"GetFromShelf"));}
   else if(phase==2){bridge.Queue.Add(this);phase=3;Go(QueuePosition(bridge.Queue.IndexOf(this)));}
   else if(phase==3&&bridge.Queue.Count>0&&bridge.Queue[0]==this){if(customer.spent<=0){bridge.Queue.Remove(this);phase=5;Go(new Vector3(-1.75f,.3f,-8.7f));return;}phase=8;agent.velocity=Vector3.zero;facing=Quaternion.LookRotation(-(MarketSimulation.Register-transform.position));wait=map.ScanCustomer(customer);}
   else if(phase==5){if(returnedToCar!=null){phase=12;Go(new Vector3(-19.5f,.15f,-11.5f));}else{Reserved=false;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);}}
   else if(phase==6){NextShelf();}
   else if(phase==9){phase=11;Go(new Vector3(-19.5f,.15f,-11.5f));}
   else if(phase==11){phase=6;Go(new Vector3(-1.75f,.74f,-6f));}
   else if(phase==12){phase=10;Go(new Vector3(-19.5f,.15f,parkingDoor.z));}
   else if(phase==10){phase=7;Go(parkingDoor);}
   else if(phase==7){var completed=returnedToCar;returnedToCar=null;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);completed?.Invoke(this);Reserved=false;}
  }
  void Sync(){transform.position=agent.nextPosition;var p=transform.position;p.y=p.x< -9.4f||p.z< -10.6f?.15f:MarketSimulation.Ground(p.z);transform.position=p;}
  static Vector3 QueuePosition(int i){Vector3[] p={new Vector3(-3.15f,.74f,-6.15f),new Vector3(-4.5f,.74f,-6.15f),new Vector3(-5.85f,.74f,-6.15f),new Vector3(-7.2f,.74f,-5.05f),new Vector3(-7.2f,.74f,-3.9f)};return p[Mathf.Clamp(i,0,4)];}
 }
}
