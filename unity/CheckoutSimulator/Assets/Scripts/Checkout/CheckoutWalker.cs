using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using MarketDay;
namespace Checkout {
 public class CheckoutWalker:MonoBehaviour {
  CheckoutBridge bridge;CheckoutMap map;NavMeshAgent agent;MarketCharacterAnimator motion;Customer customer;CheckoutLane lane;int phase,index;float wait,helpWait,tillWait;bool cart,snapHeading,asked;CheckoutRequestBubble bubble;CheckoutShopperRig rig;Vector3 target;Quaternion facing;
  public void Initialize(CheckoutBridge owner,NavMeshAgent navigation,CheckoutMap projection){bridge=owner;map=projection;agent=navigation;motion=GetComponent<MarketCharacterAnimator>();cart=name=="Customer_02"||name=="Customer_05"||name=="Customer_07";agent.avoidancePriority=40+(cart?5:0);rig=CheckoutShopperRig.For(transform);}
  List<CheckoutWalker> Line=>lane!=null?lane.queue:bridge.Queue;
  // Customers with a special request wait by the entrance until the player answers (or they give up).
  static readonly List<CheckoutWalker> helpLine=new List<CheckoutWalker>();
  DayRequest Request=>bridge.RequestFor(customer?.id);
  // A customer who needs the player does not wait in one fixed spot by the door: they browse the shop
  // as if looking for the product, standing in front of a shelf or sector for a while, then trying
  // another one, always a little apart from the others who are waiting too.
  Vector3 browseLook;float browseFor;
  Vector3 HelpPoint(){
   var interior=map.Interior;
   if(interior&&interior.Ready&&!CheckoutStall.Small){
    var fixtures=new List<CheckoutInterior.Item>();
    foreach(var it in interior.items.Values)if(it.root&&it.piece!=null&&!it.building&&!it.outside&&it.functional&&(it.type=="shelf"||it.type=="sector"))fixtures.Add(it);
    for(int attempt=0;attempt<10&&fixtures.Count>0;attempt++){
     var it=fixtures[Random.Range(0,fixtures.Count)];
     var spot=interior.Approach(it)+it.root.right*Random.Range(-.7f,.7f)*it.root.lossyScale.x;
     if(!NavMesh.SamplePosition(spot,out var hit,.8f,NavMesh.AllAreas))continue;
     if((hit.position-transform.position).sqrMagnitude<.5f&&fixtures.Count>1)continue;
     bool taken=false;foreach(var other in helpLine)if(other!=this&&other&&(other.target-hit.position).sqrMagnitude<1.2f){taken=true;break;}
     if(taken)continue;
     browseLook=it.root.position;return hit.position;
    }
   }
   int i=Mathf.Max(0,helpLine.IndexOf(this));var fallback=map.HelpSpot(i);browseLook=fallback+Vector3.forward;return fallback;}
  public string CustomerId=>customer?.id;
  public bool Reserved {get;private set;}
  public bool HasPaid {get;private set;}
  public Vector3 CarDoor=>parkingDoor;
  public int VisitPhase=>phase;
  Vector3 parkingDoor;System.Action<CheckoutWalker> returnedToCar;
  // The shop just closed: people outside turn back, people inside head straight for the door.
  public void MarketClosed(){if(!gameObject.activeInHierarchy||!agent||!agent.isOnNavMesh)return;
   if(phase==9||phase==11||phase==6){phase=12;Go(new Vector3(-19.5f,.15f,-11.5f));return;}
   if(phase==5||phase==13||phase==12||phase==10||phase==7||phase==30||phase==8||phase==4)return;
   helpLine.Remove(this);Line.Remove(this);map.Lanes.Remove(this);lane=null;wait=0;
   var u=CheckoutMarketLayout.Unproject(transform.position,bridge.State.layout??new MarketLayout());
   bool inside=u.z> -7.2f&&u.x> -9.4f&&u.x<9.4f;
   if(!inside){phase=returnedToCar!=null?12:13;Go(returnedToCar!=null?new Vector3(-19.5f,.15f,-11.5f):Away());}
   else{phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);}}
  // Furniture was moved in build mode: head for the new spot of whatever they were walking to.
  public void FurnitureMoved(){if(!gameObject.activeInHierarchy||!agent||!agent.isOnNavMesh)return;
   if(phase==0&&customer?.purchases!=null&&index<customer.purchases.Length)Go(map.Approach(customer.purchases[index].shelfId));
   else if(phase==1&&customer?.purchases!=null&&index<customer.purchases.Length){var spot=map.Approach(customer.purchases[index].shelfId);if((transform.position-spot).sqrMagnitude>.3f){wait=0;phase=0;Go(spot);}}
   else if(phase==3)Go(QueuePosition(Line.IndexOf(this)));
   else if(phase==20)Go(HelpPoint());}
  public void Reserve(){Reserved=true;CheckoutShoppingProps.SetVisible(transform,false);}
  public void CancelVisit(){helpLine.Remove(this);if(agent&&agent.isOnNavMesh){agent.ResetPath();agent.isStopped=true;}map.Lanes.Remove(this);bridge.Queue.Remove(this);lane=null;returnedToCar=null;Reserved=false;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);}
  public void BeginFromCar(Customer visit,Vector3 door,System.Action<CheckoutWalker> completed){parkingDoor=door;returnedToCar=completed;customer=visit;phase=9;index=0;wait=0;asked=false;HasPaid=false;Reserved=true;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(true);if(!NavMesh.SamplePosition(door,out var hit,.8f,NavMesh.AllAreas)||!agent.Warp(hit.position))throw new System.InvalidOperationException("Parking door is outside the customer NavMesh");Sync();Go(new Vector3(-19.5f,.15f,parkingDoor.z));snapHeading=true;}
  public void Begin(Customer visit){returnedToCar=null;HasPaid=false;Reserved=true;customer=visit;phase=0;index=0;wait=0;asked=false;gameObject.SetActive(true);var spawn=map.Entrance;NavMesh.SamplePosition(spawn,out var hit,2,NavMesh.AllAreas);agent.Warp(hit.position);transform.rotation=Quaternion.Euler(0,180,0);Sync();NextShelf();snapHeading=true;}
  public void RebaseLayout(MarketLayout previous,MarketLayout next){
   if(!gameObject.activeInHierarchy||!agent)return;
   Vector3 Remap(Vector3 p){var original=CheckoutMarketLayout.Unproject(p,previous);return original.x> -9.5f&&original.x<9.5f&&original.z> -10.61f&&original.z<7.5f?CheckoutMarketLayout.Project(original,next):p;}
   var position=Remap(transform.position);target=Remap(target);if(NavMesh.SamplePosition(position,out var hit,3,NavMesh.AllAreas)){agent.Warp(hit.position);Go(target);Sync();}
  }
  void Go(Vector3 destination){if(NavMesh.SamplePosition(destination,out var hit,2,NavMesh.AllAreas))destination=hit.position;target=destination;agent.isStopped=false;agent.SetDestination(destination);}
  void NextShelf(){
   if(!asked&&index==0){var request=Request;if(request!=null&&request.status=="pending"){asked=true;helpWait=0;helpLine.Add(this);phase=20;Go(HelpPoint());return;}}
   CheckoutShoppingProps.SetVisible(transform,customer.purchases!=null&&customer.purchases.Length>0);if(customer.purchases!=null&&index<customer.purchases.Length){phase=0;Go(map.Approach(customer.purchases[index].shelfId));}else {lane=CheckoutStall.Small&&map.Lanes.lanes.Count>0?map.Lanes.lanes[0]:map.Lanes.Pick();if(lane.places==null&&lane.itemId==null){phase=2;Go(map.Point(new Vector3(-7.2f,.74f,-3.4f)));}else{Line.Add(this);phase=3;Go(QueuePosition(Line.IndexOf(this)));}}}
  void Update(){if(!agent.isOnNavMesh)return;
   UpdateBubble();
   if(phase==30){ // At the register until the basket is rung up (player, cashier) or they give up.
    agent.isStopped=true;tillWait+=Time.deltaTime;transform.rotation=Quaternion.RotateTowards(transform.rotation,facing,Time.deltaTime*240);Sync();
    if(bridge.CheckoutFor(customer?.id)==null||tillWait>300){var result=bridge.CheckoutResultFor(customer?.id);
     if(result!=null&&result.status=="left"){Line.Remove(this);lane=null;phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);}
     else if(result!=null&&result.status=="paid"){phase=4;wait=Mathf.Max(motion.Perform("PayAtCheckout"),.8f);}
     else{phase=8;wait=map.ScanCustomer(customer,lane);}}
    return;}
   if(phase==21){ // Waiting for help, facing the camera so the bubble reads well.
    agent.isStopped=true;helpWait+=Time.deltaTime;browseFor-=Time.deltaTime;var look=browseLook-transform.position;look.y=0;
    if(look.sqrMagnitude>.01f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(-look),Time.deltaTime*240);Sync();
    if(browseFor<=0&&helpWait<110){phase=20;Go(HelpPoint());snapHeading=true;return;}
    var request=Request;if(request==null||request.status!="pending"||helpWait>120){helpLine.Remove(this);phase=0;NextShelf();snapHeading=true;}
    return;}
   if(wait>0){wait-=Time.deltaTime;agent.isStopped=true;transform.rotation=Quaternion.RotateTowards(transform.rotation,facing,Time.deltaTime*180);if(phase==8&&lane!=null&&lane.kiosk&&!motion.Busy)motion.Perform("GetFromShelf",false); // Scanning their own items.
   Sync();if(wait<=0){if(phase==1){index++;NextShelf();}else if(phase==8){phase=4;wait=Mathf.Max(motion.Perform("PayAtCheckout"),lane!=null&&lane.kiosk?0:map.PaymentDuration);}else if(phase==4){HasPaid=true;Line.Remove(this);lane=null;phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);}}return;}
   // Gave up while still in line: the basket stays behind and they walk out.
   if(phase==3&&bridge.CheckoutFor(customer?.id)==null&&bridge.CheckoutResultFor(customer?.id)?.status=="left"){Line.Remove(this);lane=null;phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);return;}
   if(phase==3){var q=Line.IndexOf(this);var position=QueuePosition(q);if((position-target).sqrMagnitude>.05f)Go(position);}
   agent.speed=(cart?.88f:1.04f)*(rig?rig.SpeedFactor:1);agent.acceleration=3.5f;
   // Rigs face -Z. Step out of a car or doorway already facing the route, then steer toward where the agent
   // wants to go (desired velocity) instead of trailing the actual velocity, so nobody walks sideways.
   if(snapHeading&&!agent.pathPending&&agent.hasPath){snapHeading=false;FacePath();}
   var velocity=agent.desiredVelocity;velocity.y=0;if(velocity.sqrMagnitude<.004f){velocity=agent.velocity;velocity.y=0;}
   if(velocity.sqrMagnitude>.004f)transform.rotation=Quaternion.RotateTowards(transform.rotation,Quaternion.LookRotation(-velocity),Time.deltaTime*(cart?220:420));Sync();
   bool arrived=!agent.pathPending&&((agent.hasPath&&agent.pathStatus==NavMeshPathStatus.PathComplete&&agent.remainingDistance<.25f)||Vector3.Distance(agent.nextPosition,target)<.3f);
   if(!arrived)return;agent.isStopped=true;
   if(phase==0){var id=customer.purchases[index].shelfId;var direction=map.Fixture(id)-transform.position;direction.y=0;facing=Quaternion.LookRotation(-direction);phase=1;agent.velocity=Vector3.zero;wait=Mathf.Max(1.5f,motion.Perform(map.Special(id)?"BuyAtSpecialSector":"GetFromShelf"));}
   else if(phase==20){phase=21;agent.velocity=Vector3.zero;browseFor=Random.Range(7f,12f);}
   else if(phase==2){lane=null;Line.Add(this);phase=3;Go(QueuePosition(Line.IndexOf(this)));}
   else if(phase==3&&Line.Count>0&&Line[0]==this){if(customer.spent<=0){Line.Remove(this);lane=null;phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);return;}
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
  void Sync(){transform.position=agent.nextPosition;var p=transform.position;var u=CheckoutMarketLayout.Unproject(p,bridge.State.layout??new MarketLayout());p.y=CheckoutStall.Small||u.x< -9.4f||u.x>9.4f||u.z< -10.6f?.15f:MarketSimulation.Ground(u.z);transform.position=p;}
  void FacePath(){foreach(var corner in agent.path.corners){var direction=corner-transform.position;direction.y=0;if(direction.sqrMagnitude>.01f){transform.rotation=Quaternion.LookRotation(-direction);return;}}}
  Vector3 QueuePosition(int i){if(lane!=null&&lane.itemId!=null)return map.QueueSpot(lane,i);if(lane!=null&&lane.places!=null)return map.Point(lane.places[Mathf.Clamp(i,0,lane.places.Length-1)]);Vector3[] p={new Vector3(-3.15f,.74f,-6.15f),new Vector3(-4.5f,.74f,-6.15f),new Vector3(-5.85f,.74f,-6.15f),new Vector3(-7.2f,.74f,-5.05f),new Vector3(-7.2f,.74f,-3.9f)};return i<3?map.CheckoutPoint(p[Mathf.Clamp(i,0,4)]):map.Point(p[Mathf.Clamp(i,0,4)]);}
 }
}
