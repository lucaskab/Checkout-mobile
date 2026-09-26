using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using MarketDay;
namespace Checkout {
 public class CheckoutWalker:MonoBehaviour {
  CheckoutBridge bridge;CheckoutMap map;NavMeshAgent agent;MarketCharacterAnimator motion;Customer customer;CheckoutLane lane;int phase,index;float wait,helpWait,tillWait;bool cart,snapHeading,asked;CheckoutRequestBubble bubble;Vector3 target;Quaternion facing;
  public void Initialize(CheckoutBridge owner,NavMeshAgent navigation,CheckoutMap projection){bridge=owner;map=projection;agent=navigation;motion=GetComponent<MarketCharacterAnimator>();cart=name=="Customer_02"||name=="Customer_05"||name=="Customer_07";agent.avoidancePriority=40+(cart?5:0);}
  List<CheckoutWalker> Line=>lane!=null?lane.queue:bridge.Queue;
  // Customers with a special request wait by the entrance until the player answers (or they give up).
  static readonly List<CheckoutWalker> helpLine=new List<CheckoutWalker>();
  DayRequest Request=>bridge.RequestFor(customer?.id);
  Vector3 HelpPoint(){int i=Mathf.Max(0,helpLine.IndexOf(this));return map.Point(new Vector3(.9f+i*.85f,.74f,-5.9f));}
  public string CustomerId=>customer?.id;
  public bool Reserved {get;private set;}
  public bool HasPaid {get;private set;}
  public Vector3 CarDoor=>parkingDoor;
  public int VisitPhase=>phase;
  Vector3 parkingDoor;System.Action<CheckoutWalker> returnedToCar;
  public void Reserve(){Reserved=true;CheckoutShoppingProps.SetVisible(transform,false);}
  public void CancelVisit(){helpLine.Remove(this);if(agent&&agent.isOnNavMesh){agent.ResetPath();agent.isStopped=true;}map.Lanes.Remove(this);bridge.Queue.Remove(this);lane=null;returnedToCar=null;Reserved=false;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);}
  public void BeginFromCar(Customer visit,Vector3 door,System.Action<CheckoutWalker> completed){parkingDoor=door;returnedToCar=completed;customer=visit;phase=9;index=0;wait=0;asked=false;HasPaid=false;Reserved=true;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(true);if(!NavMesh.SamplePosition(door,out var hit,.8f,NavMesh.AllAreas)||!agent.Warp(hit.position))throw new System.InvalidOperationException("Parking door is outside the customer NavMesh");Sync();Go(new Vector3(-19.5f,.15f,parkingDoor.z));snapHeading=true;}
  public void Begin(Customer visit){returnedToCar=null;HasPaid=false;Reserved=true;customer=visit;phase=0;index=0;wait=0;asked=false;gameObject.SetActive(true);var spawn=map.Entrance;NavMesh.SamplePosition(spawn,out var hit,2,NavMesh.AllAreas);agent.Warp(hit.position);transform.rotation=Quaternion.Euler(0,180,0);Sync();NextShelf();snapHeading=true;}
  public void RebaseLayout(MarketLayout previous,MarketLayout next){
   if(!gameObject.activeInHierarchy||!agent)return;
   Vector3 Remap(Vector3 p){var original=CheckoutMarketLayout.Anchor+Vector3.Scale(p-CheckoutMarketLayout.Anchor,new Vector3(1/previous.widthScale,1,1/previous.depthScale));return original.x> -9.5f&&original.x<9.5f&&original.z> -10.61f&&original.z<7.5f?CheckoutMarketLayout.Project(original,next):p;}
   var position=Remap(transform.position);target=Remap(target);if(NavMesh.SamplePosition(position,out var hit,3,NavMesh.AllAreas)){agent.Warp(hit.position);Go(target);Sync();}
  }
  void Go(Vector3 destination){if(NavMesh.SamplePosition(destination,out var hit,2,NavMesh.AllAreas))destination=hit.position;target=destination;agent.isStopped=false;agent.SetDestination(destination);}
  void NextShelf(){
   if(!asked&&index==0){var request=Request;if(request!=null&&request.status=="pending"){asked=true;helpWait=0;helpLine.Add(this);phase=20;Go(HelpPoint());return;}}
   CheckoutShoppingProps.SetVisible(transform,customer.purchases!=null&&customer.purchases.Length>0);if(customer.purchases!=null&&index<customer.purchases.Length){phase=0;Go(map.Approach(customer.purchases[index].shelfId));}else {lane=map.Lanes.Pick();if(lane.places==null){phase=2;Go(map.Point(new Vector3(-7.2f,.74f,-3.4f)));}else{Line.Add(this);phase=3;Go(QueuePosition(Line.IndexOf(this)));}}}
  void Update(){if(!agent.isOnNavMesh)return;
   UpdateBubble();
   if(phase==30){ // At the register until the basket is rung up (player, cashier) or they give up.
    agent.isStopped=true;tillWait+=Time.deltaTime;transform.rotation=Quaternion.RotateTowards(transform.rotation,facing,Time.deltaTime*240);Sync();
    if(bridge.CheckoutFor(customer?.id)==null||tillWait>300){var result=bridge.CheckoutResultFor(customer?.id);
     if(result!=null&&result.status=="left"){Line.Remove(this);lane=null;phase=5;Go(map.Entrance);}
     else if(result!=null&&result.status=="paid"){phase=4;wait=Mathf.Max(motion.Perform("PayAtCheckout"),.8f);}
     else{phase=8;wait=map.ScanCustomer(customer,lane);}}
    return;}
   if(phase==21){ // Waiting for help, facing the camera so the bubble reads well.
    agent.isStopped=true;helpWait+=Time.deltaTime;var view=Camera.main?Camera.main.transform.forward:Vector3.forward;view.y=0;
    if(view.sqrMagnitude>.01f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(view),Time.deltaTime*240);Sync();
    var request=Request;if(request==null||request.status!="pending"||helpWait>120){helpLine.Remove(this);phase=0;NextShelf();snapHeading=true;}
    return;}
   if(wait>0){wait-=Time.deltaTime;agent.isStopped=true;transform.rotation=Quaternion.RotateTowards(transform.rotation,facing,Time.deltaTime*180);if(phase==8&&lane!=null&&lane.kiosk&&!motion.Busy)motion.Perform("GetFromShelf",false); // Scanning their own items.
   Sync();if(wait<=0){if(phase==1){index++;NextShelf();}else if(phase==8){phase=4;wait=Mathf.Max(motion.Perform("PayAtCheckout"),lane!=null&&lane.kiosk?0:map.PaymentDuration);}else if(phase==4){HasPaid=true;Line.Remove(this);lane=null;phase=5;Go(map.Entrance);}}return;}
   // Gave up while still in line: the basket stays behind and they walk out.
   if(phase==3&&bridge.CheckoutFor(customer?.id)==null&&bridge.CheckoutResultFor(customer?.id)?.status=="left"){Line.Remove(this);lane=null;phase=5;Go(map.Entrance);return;}
   if(phase==3){var q=Line.IndexOf(this);var position=QueuePosition(q);if((position-target).sqrMagnitude>.05f)Go(position);}
   agent.speed=cart?.88f:1.04f;agent.acceleration=3.5f;
   // Rigs face -Z. Step out of a car or doorway already facing the route, then steer toward where the agent
   // wants to go (desired velocity) instead of trailing the actual velocity, so nobody walks sideways.
   if(snapHeading&&!agent.pathPending&&agent.hasPath){snapHeading=false;FacePath();}
   var velocity=agent.desiredVelocity;velocity.y=0;if(velocity.sqrMagnitude<.004f){velocity=agent.velocity;velocity.y=0;}
   if(velocity.sqrMagnitude>.004f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(-velocity),Time.deltaTime*(cart?220:420));Sync();
   bool arrived=!agent.pathPending&&((agent.hasPath&&agent.pathStatus==NavMeshPathStatus.PathComplete&&agent.remainingDistance<.25f)||Vector3.Distance(agent.nextPosition,target)<.3f);
   if(!arrived)return;agent.isStopped=true;
   if(phase==0){var id=customer.purchases[index].shelfId;var direction=map.Fixture(id)-transform.position;direction.y=0;facing=Quaternion.LookRotation(-direction);phase=1;agent.velocity=Vector3.zero;wait=Mathf.Max(1.5f,motion.Perform(map.Special(id)?"BuyAtSpecialSector":"GetFromShelf"));}
   else if(phase==20){phase=21;agent.velocity=Vector3.zero;}
   else if(phase==2){lane=null;Line.Add(this);phase=3;Go(QueuePosition(Line.IndexOf(this)));}
   else if(phase==3&&Line.Count>0&&Line[0]==this){if(customer.spent<=0){Line.Remove(this);lane=null;phase=5;Go(map.Entrance);return;}
    if(bridge.CheckoutFor(customer.id)!=null){phase=30;tillWait=0;agent.velocity=Vector3.zero;facing=Quaternion.LookRotation(-(map.LaneRegister(lane)-transform.position));return;}
    phase=8;agent.velocity=Vector3.zero;facing=Quaternion.LookRotation(-(map.LaneRegister(lane)-transform.position));wait=map.ScanCustomer(customer,lane);}
   else if(phase==5){if(returnedToCar!=null){phase=12;Go(new Vector3(-19.5f,.15f,-11.5f));}else{phase=13;Go(Away());}}
   else if(phase==13){Reserved=false;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);}
   else if(phase==6){NextShelf();}
   else if(phase==9){phase=11;Go(new Vector3(-19.5f,.15f,-11.5f));}
   else if(phase==11){phase=6;Go(map.Point(new Vector3(-1.75f,.74f,-6f)));}
   else if(phase==12){phase=10;Go(new Vector3(-19.5f,.15f,parkingDoor.z));}
   else if(phase==10){phase=7;Go(parkingDoor);}
   else if(phase==7){var completed=returnedToCar;returnedToCar=null;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);completed?.Invoke(this);Reserved=false;}
  }
  // Walk-in customers leave along the sidewalks like city pedestrians: into a building or off the map edge.
  Vector3 Away(){var streets=FindAnyObjectByType<CheckoutCityStreets>();if(!streets)return map.Entrance;var points=new List<Vector3>(streets.entrances);if(streets.patrolPoints!=null)points.AddRange(streets.patrolPoints);var path=new NavMeshPath();
   for(int tries=0;tries<8&&points.Count>0;tries++){var p=points[Random.Range(0,points.Count)];if(agent.CalculatePath(p,path)&&path.status==NavMeshPathStatus.PathComplete)return p;}return new Vector3(-1.75f,.15f,-11.5f);}
  // One bubble: a pending special request first, then the basket waiting at the register.
  void UpdateBubble(){
   if(!bubble)bubble=CheckoutRequestBubble.For(transform);
   var request=Request;if(request!=null&&request.status=="pending"){bubble.Apply(request);return;}
   bubble.Apply(request);
   var checkout=bridge.CheckoutFor(customer?.id);
   if(checkout!=null&&(phase==3||phase==30)&&checkout.readyAt<=CheckoutBridge.Now)bubble.Show(checkout.id,"cart",checkout.readyAt,checkout.expiresAt,"checkout",checkout.id);
   else if(checkout==null){var result=bridge.CheckoutResultFor(customer?.id);if(result!=null)bubble.Resolve(result.id,result.status!="left");}
  }
  void Sync(){transform.position=agent.nextPosition;var p=transform.position;p.y=p.x< -9.4f||CheckoutMarketLayout.Anchor.x+(p.x-CheckoutMarketLayout.Anchor.x)/(bridge.State.layout?.widthScale??1)>9.4f||p.z< -10.6f?.15f:MarketSimulation.Ground(CheckoutMarketLayout.Anchor.z+(p.z-CheckoutMarketLayout.Anchor.z)/(bridge.State.layout?.depthScale??1));transform.position=p;}
  void FacePath(){foreach(var corner in agent.path.corners){var direction=corner-transform.position;direction.y=0;if(direction.sqrMagnitude>.01f){transform.rotation=Quaternion.LookRotation(-direction);return;}}}
  Vector3 QueuePosition(int i){if(lane!=null&&lane.places!=null)return map.Point(lane.places[Mathf.Clamp(i,0,lane.places.Length-1)]);Vector3[] p={new Vector3(-3.15f,.74f,-6.15f),new Vector3(-4.5f,.74f,-6.15f),new Vector3(-5.85f,.74f,-6.15f),new Vector3(-7.2f,.74f,-5.05f),new Vector3(-7.2f,.74f,-3.9f)};return i<3?map.CheckoutPoint(p[Mathf.Clamp(i,0,4)]):map.Point(p[Mathf.Clamp(i,0,4)]);}
 }
}
