using System.Collections.Generic;
using UnityEngine;
using UnityEngine.AI;
using MarketDay;
namespace Checkout {
 public class CheckoutWalker:MonoBehaviour {
  CheckoutBridge bridge;CheckoutMap map;NavMeshAgent agent;MarketCharacterAnimator motion;Customer customer;CheckoutLane lane;int phase,index;float wait,tillWait;bool snapHeading;bool Cart=>rig&&rig.cart;CheckoutRequestBubble bubble;CheckoutShopperRig rig;Vector3 target;Quaternion facing;
  public void Initialize(CheckoutBridge owner,NavMeshAgent navigation,CheckoutMap projection){bridge=owner;map=projection;agent=navigation;agent.updateRotation=false;/*the copies (Customer_Extra*) came with the agent turning them too: the body is turned here only*/motion=GetComponent<MarketCharacterAnimator>();rig=CheckoutShopperRig.For(transform);agent.avoidancePriority=40+(CheckoutShopperRig.WantsCart(name)?5:0);if(!All.Contains(this))All.Add(this);}
  void OnDestroy(){All.Remove(this);}
  static readonly List<CheckoutWalker> All=new List<CheckoutWalker>();
  // A basket can be rung up only while its customer stands at the register (phase 30), never while they are still
  // shopping, queueing or on their way in. A customer with no walker on the map does not block the register (the
  // store then waits CHECKOUT_READY_DELAY_MS for them).
  public static bool AtRegister(string customerId){if(string.IsNullOrEmpty(customerId))return true;foreach(var w in All)if(w&&w.gameObject.activeInHierarchy&&w.customer!=null&&w.customer.id==customerId)return w.phase==30;return true;}
  float arrivalPing;
  // Lucas 26/10: the corners of the way rounded and the body eased round to where it walks, turns on the spot eased too,
  // never a snap (CheckoutStride). A heading is set at once only as the customer appears.
  readonly CheckoutStride stride=new CheckoutStride();int shownAt=-100;
  void Shown(){shownAt=Time.frameCount;stride.Reset(transform);}
  void TurnTo(Quaternion rotation){stride.Face(transform,-(rotation*Vector3.forward),Time.deltaTime,false);}
  List<CheckoutWalker> Line=>lane!=null?lane.queue:bridge.Queue;
  public string CustomerId=>customer?.id;
  // QA (CheckoutAutoTest "eventscrowd"): where they are heading, and how often the safety net below had to step in.
  public Vector3 QaTarget=>target;public static int QaUnsticks,QaForceExits;
  // A little shop (Späti, quitanda, minimercado) lets in only as many people as it has room for (CheckoutStall.Capacity,
  // Lucas 29/10: a tester saw them jam in a packed Conveniência): the next ones wait outside by the door, in the order
  // they came (phase 18), and go in as others leave. `admitted`: this visit is inside (or the shop had room).
  static readonly List<CheckoutWalker> waitLine=new List<CheckoutWalker>();bool admitted;
  static int InsideCount(){int n=0;foreach(var w in All)if(w&&w.gameObject.activeInHierarchy&&w.admitted&&(w.phase<=4||w.phase==8||w.phase==30))n++;return n;}
  /// <summary>Two rows already wait outside the full little shop: no one else sets off for it until there is room.</summary>
  public static bool ShopCrowded=>CheckoutStall.ShopInside&&waitLine.Count>=6;
  bool MustWait()=>CheckoutStall.ShopInside&&(InsideCount()>=CheckoutStall.Capacity||(waitLine.Count>0&&waitLine[0]!=this));
  public bool Reserved {get;private set;}
  public bool HasPaid {get;private set;}
  public Vector3 CarDoor=>parkingDoor;
  public int VisitPhase=>phase;
  Vector3 parkingDoor;System.Action<CheckoutWalker> returnedToCar;
  // The shop just closed: people outside turn back, people inside head straight for the door.
  public void MarketClosed(){if(!gameObject.activeInHierarchy||!agent||!agent.isOnNavMesh)return;
   if(phase==9||phase==11||phase==6){phase=12;Go(CheckoutCityTraffic.Corner);return;}
   if(phase==14||phase==15||phase==16||phase==17||phase==18){LeaveEventLine();waitLine.Remove(this);phase=13;Go(Away());return;}
   if(phase==5||phase==13||phase==12||phase==10||phase==7||phase==30||phase==8||phase==4)return;
   Line.Remove(this);map.Lanes.Remove(this);lane=null;wait=0;
   var u=CheckoutMarketLayout.Unproject(transform.position,bridge.State.layout??new MarketLayout());
   bool inside=u.z> -7.2f&&u.x> -9.4f&&u.x<9.4f;
   if(!inside){phase=returnedToCar!=null?12:13;Go(returnedToCar!=null?CheckoutCityTraffic.Corner:Away());}
   else{phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);}}
  // Furniture was moved in build mode: head for the new spot of whatever they were walking to.
  public void FurnitureMoved(){if(!gameObject.activeInHierarchy||!agent||!agent.isOnNavMesh)return;
   if(phase==0&&customer?.purchases!=null&&index<customer.purchases.Length)Go(map.Approach(customer.purchases[index].shelfId));
   else if(phase==1&&customer?.purchases!=null&&index<customer.purchases.Length){var spot=map.Approach(customer.purchases[index].shelfId);if((transform.position-spot).sqrMagnitude>.3f){wait=0;phase=0;Go(spot);}}
   else if(phase==3)Go(QueuePosition(Line.IndexOf(this)));}
  public void Reserve(){Reserved=true;CheckoutShoppingProps.SetVisible(transform,false);}
  public void CancelVisit(){LeaveEventLine();waitLine.Remove(this);admitted=false;if(agent&&agent.isOnNavMesh){agent.ResetPath();agent.isStopped=true;}map.Lanes.Remove(this);bridge.Queue.Remove(this);lane=null;returnedToCar=null;Reserved=false;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);}
  public void BeginFromCar(Customer visit,Vector3 door,System.Action<CheckoutWalker> completed){eventOrigin=null;lead=null;parkingDoor=door;returnedToCar=completed;customer=visit;admitted=false;phase=9;index=0;wait=0;HasPaid=false;Reserved=true;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(true);if(!(NavMesh.SamplePosition(door,out var hit,.8f,NavMesh.AllAreas)||NavMesh.SamplePosition(door,out hit,3f,NavMesh.AllAreas))||!agent.Warp(hit.position)){Debug.LogWarning("CHECKOUT_WALKER the parking door is off the NavMesh; the visit is dropped");ForceExit();return;}Sync();Shown();Go(new Vector3(CheckoutCityTraffic.WalkX,.15f,parkingDoor.z));snapHeading=true;}
  // Walk-in customers arrive on foot like the passers-by (Lucas 15/10: they used to pop up right at the stall's
  // front): they appear further along the avenue sidewalk, or across the avenue at the park crossing, and walk to
  // the entrance (phase 14) before shopping. If no such spot is walkable, they start at the entrance as before.
  public void Begin(Customer visit){eventOrigin=null;lead=null;returnedToCar=null;HasPaid=false;Reserved=true;customer=visit;admitted=false;phase=0;index=0;wait=0;gameObject.SetActive(true);CheckoutShoppingProps.SetVisible(transform,false);
   var entrance=map.Entrance;
   if(ArrivalSpot(entrance,out var start)&&agent.Warp(start)){Sync();Shown();phase=14;Go(entrance);snapHeading=true;return;}
   if(!(NavMesh.SamplePosition(entrance,out var hit,2,NavMesh.AllAreas)||NavMesh.SamplePosition(entrance,out hit,6,NavMesh.AllAreas))||!agent.Warp(hit.position)){ForceExit();return;}transform.rotation=Quaternion.Euler(0,180,0);Sync();Shown();NextShelf();snapHeading=true;}
  // ---------------------------------------------------------------- customers an event brought (Customer.origin)
  // Lucas 15/10: "the people at the event must really go into the market and buy". A visit the running event brought
  // walks through its scene first (CheckoutEventVisuals.Market.cs hands over the lead-in): it either starts at a given
  // spot (off the rush-hour or the school bus) or arrives on foot like a walk-in, then stops at the event (phase 15 →
  // 17: the street fair's stall, the ice-cream cart, the prize wheel…; phase 16: the ATM queue on payday) and walks
  // in to shop with its real basket (phase 14 → the usual shelves, register and payment).
  string eventOrigin;CheckoutEventVisuals.LeadIn lead;bool leadActed;Vector3 lineGoal=Vector3.one*1e5f;float leadSince;
  public string EventOrigin=>eventOrigin;
  CheckoutEventVisuals fx;CheckoutEventVisuals Fx=>fx?fx:(fx=bridge?bridge.GetComponent<CheckoutEventVisuals>():null);
  // QA (CheckoutAutoTest "eventsmarket"): per event, walkers that [0] began in its scene, [1] reached the entrance,
  // [2] stood at the register, [3] paid.
  public static readonly Dictionary<string,int[]> EventQa=new Dictionary<string,int[]>();
  void CountEvent(int step){if(string.IsNullOrEmpty(eventOrigin))return;if(!EventQa.TryGetValue(eventOrigin,out var c))EventQa[eventOrigin]=c=new int[4];c[step]++;}
  /// <summary>Starts a visit through the event's scene; false when no walkable start was found (the caller begins it normally).</summary>
  public bool BeginFromEvent(Customer visit,CheckoutEventVisuals.LeadIn leadIn){
   returnedToCar=null;HasPaid=false;Reserved=true;customer=visit;admitted=false;index=0;wait=0;leadActed=false;gameObject.SetActive(true);CheckoutShoppingProps.SetVisible(transform,false);
   var entrance=map.Entrance;Vector3 start;
   if(leadIn.start.HasValue){if(!(NavMesh.SamplePosition(leadIn.start.Value,out var hit,1.6f,NavMesh.AllAreas)||NavMesh.SamplePosition(leadIn.start.Value,out hit,3f,NavMesh.AllAreas))){gameObject.SetActive(false);Reserved=false;return false;}start=hit.position;}
   else if(!ArrivalSpot(entrance,out start)){gameObject.SetActive(false);Reserved=false;return false;}
   if(!agent.Warp(start)){gameObject.SetActive(false);Reserved=false;return false;}
   eventOrigin=visit.origin;lead=leadIn;leadSince=Time.time;Sync();Shown();snapHeading=true;CountEvent(0);
   if(leadIn.line&&Fx){phase=15;var tail=Fx.LineTail(this);if(tail.HasValue){lineGoal=tail.Value;Go(tail.Value);return true;}}
   if(leadIn.stand.HasValue){phase=15;Go(leadIn.stand.Value);return true;}
   phase=14;Go(entrance);return true;}
  void LeaveEventLine(){if(Fx)Fx.LeaveLine(this);}
  // Outside, walking the street (arriving, at the event, leaving): the phases that get an umbrella in the rain.
  public bool OutdoorWalk=>gameObject.activeInHierarchy&&(phase==14||phase==18||phase==15||phase==16||phase==17||phase==13||phase==9||phase==11||phase==12||phase==10||phase==7);
  // Where a walk-in customer appears (Lucas 15/10: "pode colocar de mais longe, pra não ficar óbvio"): a building
  // door or a sidewalk spot of the city, 25-45 m of walking from the entrance, so they look like any passer-by who
  // decides to go in. Never right beside another arriving customer.
  public static readonly int[] ArrivalMisses=new int[4]; // QA: distance, off the NavMesh, crowded, no path
  static readonly List<Vector3> arrivalPool=new List<Vector3>();
  /// <summary>When the market last opened (Time.time), set by CheckoutBridge.</summary>
  public static float MarketOpenedAt=-999;
  bool ArrivalSpot(Vector3 entrance,out Vector3 spot){
   spot=entrance;var path=new NavMeshPath();
   // Right after opening (Lucas 24/10: a long empty start felt like nothing happened) the first shoppers come from
   // the nearest corners: they reach the shop in a few seconds instead of half a minute.
   bool opening=Time.time-MarketOpenedAt<25;
   float min=opening?8:25,max=opening?18:45;
   arrivalPool.Clear();
   var streets=FindAnyObjectByType<CheckoutCityStreets>();
   if(streets){if(streets.entrances!=null)arrivalPool.AddRange(streets.entrances);if(streets.patrolPoints!=null)arrivalPool.AddRange(streets.patrolPoints);}
   // Sidewalk spots along the avenue (both sides, across the local streets too) and across it at the park.
   for(float dx=-44;dx<=44;dx+=4){arrivalPool.Add(new Vector3(entrance.x+dx,.15f,CheckoutStreetLayout.NorthWalkZ));arrivalPool.Add(new Vector3(entrance.x+dx,.15f,CheckoutStreetLayout.SouthWalkZ));}
   for(int tries=0;tries<14&&arrivalPool.Count>0;tries++){
    var candidate=arrivalPool[Random.Range(0,arrivalPool.Count)];
    float straight=Vector3.Distance(new Vector3(candidate.x,0,candidate.z),new Vector3(entrance.x,0,entrance.z));
    if(straight<min*.6f||straight>max){ArrivalMisses[0]++;continue;}
    if(!NavMesh.SamplePosition(candidate,out var hit,1.2f,NavMesh.AllAreas)){ArrivalMisses[1]++;continue;}
    bool crowded=false;foreach(var w in All)if(w!=this&&w&&w.gameObject.activeInHierarchy&&(w.transform.position-hit.position).sqrMagnitude<1.5f){crowded=true;break;}
    if(crowded){ArrivalMisses[2]++;continue;}
    if(!NavMesh.CalculatePath(hit.position,entrance,NavMesh.AllAreas,path)||path.status!=NavMeshPathStatus.PathComplete){ArrivalMisses[3]++;continue;}
    float walk=0;var corners=path.corners;for(int i=1;i<corners.Length;i++)walk+=Vector3.Distance(corners[i-1],corners[i]);
    if(walk<min||walk>max*1.35f){ArrivalMisses[0]++;continue;}
    spot=hit.position;return true;}
   return false;}
  public void RebaseLayout(MarketLayout previous,MarketLayout next){
   if(!gameObject.activeInHierarchy||!agent)return;
   Vector3 Remap(Vector3 p){var original=CheckoutMarketLayout.Unproject(p,previous);return original.x> -9.5f&&original.x<9.5f&&original.z> -10.61f&&original.z<7.5f?CheckoutMarketLayout.Project(original,next):p;}
   var position=Remap(transform.position);target=Remap(target);if(NavMesh.SamplePosition(position,out var hit,3,NavMesh.AllAreas)){agent.Warp(hit.position);Go(target);Sync();}
  }
  void Go(Vector3 destination){holding=false;if(NavMesh.SamplePosition(destination,out var hit,2,NavMesh.AllAreas))destination=hit.position;target=destination;agent.isStopped=false;
   // just appeared (not drawn yet this frame): the way is planned now and they stand facing along it, so nobody pops
   // round in view (29/10 QA: the turn to the way used to come a few frames later, 110 degrees in one frame)
   if(Time.frameCount==shownAt){var path=new NavMeshPath();if(agent.CalculatePath(destination,path)&&path.status!=NavMeshPathStatus.PathInvalid&&agent.SetPath(path)){FaceAlong(path.corners);stride.Reset(transform);return;}}
   agent.SetDestination(destination);}
  // Standing still (at the till, at a shelf, waiting for help): stay exactly on the spot. A stopped agent still got
  // nudged every frame by the avoidance of the customers queueing behind, and Sync() followed it, so people at the
  // register shook in place. A real move (Go, a warp after the layout changed: more than 0.6 m) takes a new spot.
  bool holding;Vector3 hold;
  void Hold(){
   if(!holding||(agent.nextPosition-hold).sqrMagnitude>.36f){holding=true;hold=agent.nextPosition;}
   agent.velocity=Vector3.zero;agent.nextPosition=hold;Sync();
  }
  void NextShelf(){
   if(!admitted){
    if(MustWait()){if(!waitLine.Contains(this))waitLine.Add(this);phase=18;CheckoutShoppingProps.SetVisible(transform,false);Go(CheckoutStall.WaitSpot(waitLine.IndexOf(this)));return;}
    admitted=true;waitLine.Remove(this);}
   CheckoutShoppingProps.SetVisible(transform,customer.purchases!=null&&customer.purchases.Length>0);if(customer.purchases!=null&&index<customer.purchases.Length){phase=0;Go(map.Approach(customer.purchases[index].shelfId));}else {lane=CheckoutStall.Small&&map.Lanes.lanes.Count>0?map.Lanes.lanes[0]:map.Lanes.Pick();if(lane.places==null&&lane.itemId==null){phase=2;Go(map.Point(new Vector3(-7.2f,.74f,-3.4f)));}else{Line.Add(this);phase=3;Go(QueuePosition(Line.IndexOf(this)));}}}
  // Safety net: a customer who is off the NavMesh (the floor was rebuilt under them) or makes no progress is put back
  // on the way, and as a last resort finishes the step (or leaves) instead of freezing the line forever.
  float offMesh,stuckFor;Vector3 lastSpot;
  void ForceExit(){QaForceExits++;LeaveEventLine();waitLine.Remove(this);admitted=false;Line.Remove(this);if(map&&map.Lanes)map.Lanes.Remove(this);bridge.Queue.Remove(this);lane=null;wait=0;
   var completed=returnedToCar;returnedToCar=null;CheckoutShoppingProps.SetVisible(transform,false);if(agent&&agent.isOnNavMesh){agent.ResetPath();agent.isStopped=true;}
   Reserved=false;gameObject.SetActive(false);completed?.Invoke(this);}
  // Stuck far from the spot: hop onto the nearest walkable point by the destination, or skip what can be skipped.
  void Unstick(){QaUnsticks++;
   if(phase==0&&customer?.purchases!=null){index++;NextShelf();return;}
   if(phase==15||phase==16||phase==17){LeaveEventLine();phase=14;}
   if(phase==14){if(NavMesh.SamplePosition(map.Entrance,out var door,3f,NavMesh.AllAreas)&&agent.Warp(door.position)){Sync();NextShelf();}else ForceExit();return;}
   if(NavMesh.SamplePosition(target,out var hit,2.5f,NavMesh.AllAreas)&&agent.Warp(hit.position)){Sync();Go(target);return;}
   if(phase==5||phase==13||phase==12||phase==10||phase==7||phase==11||phase==9||phase==6){ForceExit();return;}
   if(NavMesh.SamplePosition(transform.position,out hit,4f,NavMesh.AllAreas)&&agent.Warp(hit.position)){Sync();Go(target);}}
  void Update(){
   if(!agent.isOnNavMesh){
    offMesh+=Time.deltaTime;if(offMesh<.5f)return;offMesh=0;
    if(NavMesh.SamplePosition(transform.position,out var back,4f,NavMesh.AllAreas)&&agent.Warp(back.position)){Sync();Go(target);}
    else ForceExit();
    return;}
   offMesh=0;
   UpdateBubble();
   if(phase==30){ // At the register until the basket is rung up (player, cashier) or they give up.
    agent.isStopped=true;tillWait+=Time.deltaTime;TurnTo(facing);Hold();
    // Tell the store they are here: the basket becomes ready and their patience starts now (sent again if lost).
    var waiting=bridge.CheckoutFor(customer?.id);if(waiting!=null&&waiting.readyAt>CheckoutBridge.Now&&Time.time>=arrivalPing){arrivalPing=Time.time+3;bridge.Command("checkoutArrived","[\""+customer.id+"\"]");}
    if(bridge.CheckoutFor(customer?.id)==null||tillWait>150){var result=bridge.CheckoutResultFor(customer?.id);
     if(result!=null&&result.status=="left"){Line.Remove(this);lane=null;phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);}
     else if(result!=null&&result.status=="paid"){phase=4;wait=Mathf.Max(motion.Perform("PayAtCheckout"),.8f);}
     else{phase=8;wait=map.ScanCustomer(customer,lane);}}
    return;}
   if(phase==18){ // Waiting outside the full little shop: their place by the door; in as soon as there is room.
    if(!CheckoutStall.ShopInside){waitLine.Remove(this);admitted=true;NextShelf();return;}
    int at=waitLine.IndexOf(this);if(at<0){waitLine.Add(this);at=waitLine.Count-1;}
    if(at==0&&InsideCount()<CheckoutStall.Capacity){waitLine.Remove(this);admitted=true;NextShelf();snapHeading=true;return;}
    var spot=CheckoutStall.WaitSpot(at);if(NavMesh.SamplePosition(spot,out var near,1.5f,NavMesh.AllAreas))spot=near.position;
    if((spot-target).sqrMagnitude>.05f)Go(spot);
    else if(!agent.pathPending&&Vector3.Distance(agent.nextPosition,target)<.4f){agent.isStopped=true;var look=new Vector3(CheckoutStall.Door.x,0,CheckoutStall.Door.y)-transform.position;look.y=0;if(look.sqrMagnitude>.01f)stride.Face(transform,look,Time.deltaTime,false);Hold();return;}}
   if(phase==16){ // In the event's line (the ATM): follow the slot; when the scene lets them go, walk in.
    var spot=Fx?Fx.LineSpot(this):null;
    if(!spot.HasValue){phase=14;leadActed=false;Go(map.Entrance);snapHeading=true;}
    else{if((spot.Value-lineGoal).sqrMagnitude>.04f){lineGoal=spot.Value;Go(spot.Value);Fx.LineStanding(this,false);}
     else if(!agent.pathPending&&(Vector3.Distance(agent.nextPosition,target)<.35f||(agent.isStopped&&Vector3.Distance(agent.nextPosition,target)<1.2f))){agent.isStopped=true;agent.velocity=Vector3.zero;Hold();var look=Fx.LineLook(this)-transform.position;look.y=0;if(look.sqrMagnitude>.01f)stride.Face(transform,look,Time.deltaTime,false);Fx.LineStanding(this,true);
      if(Fx.LineFront(this)&&!leadActed){leadActed=true;motion.Perform("PayAtCheckout",false);}
      return;}}}
   // On the way to the event: a stop or the line's end that cannot be reached in 40 s is skipped (straight in).
   if(phase==15&&Time.time-leadSince>40f){phase=14;Go(map.Entrance);}
   if(phase==15&&lead!=null&&lead.line&&Fx){var tail=Fx.LineTail(this);
    if(!tail.HasValue){phase=14;Go(map.Entrance);}
    else{if((tail.Value-lineGoal).sqrMagnitude>.3f){lineGoal=tail.Value;Go(tail.Value);}
     // close to the end of the line, or as close as the path gets (the spot may be just off the walkable area)
     bool near=Vector3.Distance(agent.nextPosition,tail.Value)<2.2f||(!agent.pathPending&&agent.hasPath&&agent.remainingDistance<.6f);
     if(near&&Fx.JoinLine(this)){phase=16;lineGoal=Vector3.one*1e5f;}}}
   if(wait>0){wait-=Time.deltaTime;agent.isStopped=true;TurnTo(facing);if(phase==8&&lane!=null&&lane.kiosk&&!motion.Busy)motion.Perform("GetFromShelf",false); // Scanning their own items.
   Hold();if(wait<=0){if(phase==1){index++;NextShelf();}else if(phase==8){phase=4;wait=Mathf.Max(motion.Perform("PayAtCheckout"),lane!=null&&lane.kiosk?0:map.PaymentDuration);}else if(phase==17){phase=14;Go(map.Entrance);}else if(phase==4){HasPaid=true;CountEvent(3);Line.Remove(this);lane=null;phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);}}return;}
   // Gave up while still in line: the basket stays behind and they walk out.
   if(phase==3&&bridge.CheckoutFor(customer?.id)==null&&bridge.CheckoutResultFor(customer?.id)?.status=="left"){Line.Remove(this);lane=null;phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);return;}
   if(phase==3){var q=Line.IndexOf(this);var position=QueuePosition(q);if((position-target).sqrMagnitude>.05f)Go(position);}
   agent.speed=(Cart?.88f:1.04f)*(rig?rig.SpeedFactor:1);agent.acceleration=3.5f;
   // Rigs face -Z. They step out of a car or doorway already facing the route (Go, as they appear), then the body
   // eases round along the way ahead (CheckoutStride.Steer); a new way later is turned to like any other.
   if(snapHeading&&!agent.pathPending&&agent.hasPath)snapHeading=false;
   var velocity=agent.desiredVelocity;velocity.y=0;if(velocity.sqrMagnitude<.004f){velocity=agent.velocity;velocity.y=0;}
   stride.Steer(agent,transform,velocity,Time.deltaTime,Cart?220:0);Sync();
   bool arrived=!agent.pathPending&&((agent.hasPath&&agent.pathStatus==NavMeshPathStatus.PathComplete&&agent.remainingDistance<.25f)||Vector3.Distance(agent.nextPosition,target)<.3f);
   if(!arrived){
    if((transform.position-lastSpot).sqrMagnitude>.0025f){lastSpot=transform.position;stuckFor=0;}else stuckFor+=Time.deltaTime;
    // Jammed right next to the spot (someone stands on it, a corner of furniture): close enough.
    if(stuckFor>2.5f&&Vector3.Distance(agent.nextPosition,target)<1.2f)arrived=true;
    else if(stuckFor>12f){stuckFor=0;Unstick();return;}
    else if(stuckFor>4f&&!agent.pathPending&&(agent.pathStatus!=NavMeshPathStatus.PathComplete||!agent.hasPath)){stuckFor=2f;Go(target);}
    if(!arrived)return;}
   stuckFor=0;agent.isStopped=true;
   if(phase==0){var id=customer.purchases[index].shelfId;var direction=map.Fixture(id)-transform.position;direction.y=0;facing=Quaternion.LookRotation(-direction);phase=1;agent.velocity=Vector3.zero;wait=Mathf.Max(1.5f,motion.Perform(map.Special(id)?"BuyAtSpecialSector":"GetFromShelf"));}
   else if(phase==18){agent.velocity=Vector3.zero;}
   else if(phase==14){agent.isStopped=false;CountEvent(1);NextShelf();}
   else if(phase==15){agent.velocity=Vector3.zero;if(lead!=null&&lead.line){phase=14;Go(map.Entrance);return;}
    phase=17;var look=(lead!=null?lead.look:transform.position+Vector3.forward)-transform.position;look.y=0;facing=look.sqrMagnitude>.01f?Quaternion.LookRotation(-look):transform.rotation;
    wait=Mathf.Max(lead!=null?lead.pause:1.5f,!string.IsNullOrEmpty(lead?.clip)?motion.Perform(lead.clip,false):0);if(wait<=0)wait=.1f;}
   else if(phase==2){lane=null;Line.Add(this);phase=3;Go(QueuePosition(Line.IndexOf(this)));}
   else if(phase==3&&Line.Count>0&&Line[0]==this){if(customer.spent<=0){Line.Remove(this);lane=null;phase=5;CheckoutShoppingProps.SetVisible(transform,false);Go(map.Entrance);return;}
    CountEvent(2);if(bridge.CheckoutFor(customer.id)!=null){phase=30;tillWait=0;arrivalPing=0;agent.velocity=Vector3.zero;facing=Quaternion.LookRotation(-(map.LaneRegister(lane)-transform.position));return;}
    phase=8;agent.velocity=Vector3.zero;facing=Quaternion.LookRotation(-(map.LaneRegister(lane)-transform.position));wait=map.ScanCustomer(customer,lane);}
   else if(phase==5){if(returnedToCar!=null){phase=12;Go(CheckoutCityTraffic.Corner);}else{phase=13;Go(Away());}}
   else if(phase==13){Reserved=false;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);}
   else if(phase==6){NextShelf();}
   else if(phase==9){phase=11;Go(CheckoutCityTraffic.Corner);}
   else if(phase==11){phase=6;Go(map.Point(new Vector3(-1.75f,.74f,-6f)));}
   else if(phase==12){phase=10;Go(new Vector3(CheckoutCityTraffic.WalkX,.15f,parkingDoor.z));}
   else if(phase==10){phase=7;Go(parkingDoor);}
   else if(phase==7){var completed=returnedToCar;returnedToCar=null;CheckoutShoppingProps.SetVisible(transform,false);gameObject.SetActive(false);completed?.Invoke(this);Reserved=false;}
  }
  // Walk-in customers leave along the sidewalks like city pedestrians: into a building or off the map edge.
  Vector3 Away(){var streets=FindAnyObjectByType<CheckoutCityStreets>();if(!streets)return map.Entrance;var points=new List<Vector3>(streets.entrances);if(streets.patrolPoints!=null)points.AddRange(streets.patrolPoints);var path=new NavMeshPath();
   for(int tries=0;tries<8&&points.Count>0;tries++){var p=points[Random.Range(0,points.Count)];if(agent.CalculatePath(p,path)&&path.status==NavMeshPathStatus.PathComplete)return p;}return new Vector3(-1.75f,.15f,-11.5f);}
  // The bubble over the head: the basket waiting at the register.
  void UpdateBubble(){
   if(!bubble)bubble=CheckoutRequestBubble.For(transform);
   var checkout=bridge.CheckoutFor(customer?.id);
   if(checkout!=null&&phase==30&&checkout.readyAt<=CheckoutBridge.Now)bubble.Show(checkout.id,"cart",checkout.readyAt,checkout.expiresAt,"checkout",checkout.id);
   else if(checkout==null){var result=bridge.CheckoutResultFor(customer?.id);if(result!=null)bubble.Resolve(result.id,result.status!="left");}
  }
  void Sync(){transform.position=agent.nextPosition;var p=transform.position;var u=CheckoutMarketLayout.Unproject(p,bridge.State.layout??new MarketLayout());p.y=CheckoutStall.ShopInside&&CheckoutStall.InteriorFloor.Contains(new Vector2(p.x,p.z))?CheckoutStall.FloorY:CheckoutStall.Small||u.x< -9.4f||u.x>9.4f||u.z< -10.6f?.15f:MarketSimulation.Ground(u.z);transform.position=p;}
  void FaceAlong(Vector3[] corners){foreach(var corner in corners){var direction=corner-transform.position;direction.y=0;if(direction.sqrMagnitude>.01f){transform.rotation=Quaternion.LookRotation(-direction);return;}}}
  Vector3 QueuePosition(int i){if(lane!=null&&lane.itemId!=null)return map.QueueSpot(lane,i);if(lane!=null&&lane.places!=null)return map.Point(lane.places[Mathf.Clamp(i,0,lane.places.Length-1)]);Vector3[] p={new Vector3(-3.15f,.74f,-6.15f),new Vector3(-4.5f,.74f,-6.15f),new Vector3(-5.85f,.74f,-6.15f),new Vector3(-7.2f,.74f,-5.05f),new Vector3(-7.2f,.74f,-3.9f)};return i<3?map.CheckoutPoint(p[Mathf.Clamp(i,0,4)]):map.Point(p[Mathf.Clamp(i,0,4)]);}
 }
}
