using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;
using UnityEngine.EventSystems;
using UnityEngine.AI;

namespace MarketDay
{
    public class MarketSimulation : MonoBehaviour
    {
        public MarketEconomy Economy { get; private set; }
        public Camera view;
        public Transform world;
        public MarketHUD hud;
        public int speed=1;
        public int selected=-1;
        public bool quietCapture;
        public event Action Changed;
        public readonly Vector3[] browse = {P(-3.8,2.55),P(-.18,.5),P(1.5,3),P(6.5,3),P(5.1,-1.2)};
        public static Vector3 P(double x,double z)=>new Vector3((float)x,.74f,(float)z);
        public readonly string[] names={"Bakery","Groceries","Fishmonger","Butcher","Farm fresh"};
        public readonly string[] descriptions={"Warm loaves, sweet pastries and celebration cakes.","Everyday groceries, juices and colorful fresh staples.","Fresh fish on ice, delivered from the coast.","A friendly counter for freshly prepared cuts.","Crisp vegetables picked for your neighborhood."};
        public readonly Color[] accents={C("CE9140"),C("249787"),C("439CBD"),C("CD665C"),C("74A146")};
        public static Color C(string s){ColorUtility.TryParseHtmlString("#"+s,out var c);return c;}
        class Walker
        {
            public Transform root; public List<Vector3> path=new List<Vector3>(); public int node; public float wait;public int phase;public int department;public int receipt;public int basket;
            public Transform[] limbs; public Vector3 baseline; public float stride;public bool worker;public int job=-1;public float idle;
            public float radius=.32f;public Vector3 velocity;public float blocked;public bool cart;public Vector3 destination;public int completedTrips;public NavMeshAgent agent;public Quaternion? facing;
        }
        readonly List<Walker> customers=new List<Walker>();
        readonly List<Walker> staff=new List<Walker>();
        readonly List<Walker> checkoutQueue=new List<Walker>();
        readonly List<Rect> obstacles=new List<Rect>();
        readonly Queue<int> requests=new Queue<int>();
        Walker routingWalker;
        Vector2 pointerDown,lastPointer;bool dragged;float saveTimer;float autoTimer;
        float zoom=20.5f;Vector3 focus=new Vector3(0f,.1f,6f);bool initialized;
        const string SaveName="market-save-v1.json";
        public string SavePath=>Path.Combine(Application.persistentDataPath,SaveName);
        static readonly Vector3 Entrance=P(-1.75f,-8.7f);
        public static readonly Vector3 Register=P(-3.15f,-4.70f);
        void Start(){Initialize();}

        public void Initialize(bool load=true)
        {
            if(initialized)return;initialized=true;
            if(Array.IndexOf(Environment.GetCommandLineArgs(),"--market-qa")>=0)quietCapture=true;
            Economy=MarketEconomy.Fresh();
            if(load&&!quietCapture&&File.Exists(SavePath))
            {
                try {var saved=JsonUtility.FromJson<MarketEconomy>(File.ReadAllText(SavePath));if(saved!=null&&saved.Valid())Economy=saved;}
                catch(Exception ex){Debug.LogWarning("Save could not be loaded: "+ex.Message);}
            }
            Application.targetFrameRate=60;Application.runInBackground=true;
            // Obstacles use the same coordinate map as the exported Blender asset.
            if(world.GetComponentInChildren<Checkout.CheckoutShelfSlots>())
            {
                foreach(var p in Checkout.CheckoutShelfSlots.Positions)Block(p.x,p.z,2.05f,1.4f);
                Block(-3.9f,-4.7f,2.6f,1.6f);
                foreach(Transform sector in world)if(sector.name.StartsWith("Sector_"))
                    foreach(var renderer in sector.GetComponentsInChildren<Renderer>(true))if(renderer.enabled){var b=renderer.bounds;Block(b.center.x,b.center.z,b.size.x,b.size.z);}
            // Stage decor (produce islands, promo pallets...) that shoppers walk around.
            foreach(var item in world.GetComponentsInChildren<Checkout.CheckoutStageItem>())if(item.blocksNavigation)
                foreach(var renderer in item.GetComponentsInChildren<Renderer>())if(renderer.enabled){var b=renderer.bounds;Block(b.center.x,b.center.z,b.size.x,b.size.z);}
            }
            else
            {
            Block(-1.6f,.3f,1.50f,3.90f);Block(2,-1.18f,1.50f,4.75f);
            Block(-6.45f,1.05f,4.05f,1.98f);Block(-6.4f,-1.6f,4.05f,1.98f);Block(4.85f,-5.36f,4.15f,2);
            Block(-4.5f,4.14f,3.6f,1.9f);Block(-7.15f,5.6f,2.9f,2.8f);
            Block(1.5f,4.71f,3.85f,2.74f);Block(6.5f,4.65f,4.15f,2.62f);Block(6.55f,.45f,3.3f,2.5f);
            Block(7.33f,-2.68f,2.6f,2.3f);
            Block(-3.9f,-4.70f,3.4f,1.94f);Block(-2.2f,6.37f,3.8f,1.5f);
            Block(-3.8f,4.15f,2.4f,1.61f);
            }
            BuildNavigation();
            for(int i=1;i<=9;i++)
            {
                var t=world.Find($"Customer_{i:00}");if(t==null)continue;
                var w=NewWalker(t,false);w.department=(i-1)%5;w.wait=i*2.5f;w.phase=0;w.root.position=Entrance+new Vector3(0,0,-(i-1)*1.3f);w.root.gameObject.SetActive(false);customers.Add(w);
            }
            var stocker=world.Find("Worker_Stocker");
            if(stocker!=null)
            {
                for(int i=0;i<3;i++)
                {
                    var t=i==0?stocker:Instantiate(stocker,world);t.name="StockWorker_"+i;t.position=P(4.2f+i*.5f,2.3f);t.gameObject.SetActive(i<Economy.workers);staff.Add(NewWalker(t,true));
                }
            }
            UpdateCamera();hud.Build(this);Changed?.Invoke();
        }
        Walker NewWalker(Transform root,bool worker)
        {
            var limbs=new List<Transform>();foreach(Transform t in root.GetComponentsInChildren<Transform>())if(t.name.StartsWith("Arm_")||t.name.StartsWith("Leg_"))limbs.Add(t);
            bool cart=root.name=="Customer_02"||root.name=="Customer_05"||root.name=="Customer_07";
            var agent=root.GetComponent<NavMeshAgent>();if(!agent)agent=root.gameObject.AddComponent<NavMeshAgent>();agent.radius=cart?.48f:.30f;agent.height=2.3f;agent.baseOffset=0;agent.updatePosition=false;agent.updateRotation=false;
            agent.acceleration=4;agent.angularSpeed=220;agent.stoppingDistance=.13f;agent.obstacleAvoidanceType=ObstacleAvoidanceType.HighQualityObstacleAvoidance;agent.avoidancePriority=worker?35:45+customers.Count*4;
            return new Walker{root=root,limbs=limbs.ToArray(),worker=worker,baseline=root.position,cart=cart,radius=agent.radius,agent=agent};
        }
        NavMeshDataInstance navigation;
        Checkout.MarketLayout marketLayout=new Checkout.MarketLayout();
        // Furniture placed in build mode (CheckoutInterior): rotated solid boxes (centre, size, yaw).
        public Func<IEnumerable<(Vector3 center,Vector3 size,float yaw)>> Furniture;
        readonly List<(Vector3 center,Vector3 size,float yaw)> furniture=new List<(Vector3 center,Vector3 size,float yaw)>();
        public void RebuildLayoutNavigation(Checkout.MarketLayout layout)
        {
            marketLayout=layout;
            obstacles.Clear();furniture.Clear();
            if(Furniture!=null&&!Checkout.CheckoutStall.Small)furniture.AddRange(Furniture());
            var slots=world.GetComponentInChildren<Checkout.CheckoutShelfSlots>();
            if(slots&&Furniture==null)foreach(Transform slot in slots.transform)if(slot.gameObject.activeSelf)
            {
                var p=Checkout.CheckoutMarketLayout.Project(Checkout.CheckoutShelfSlots.Position(slot.name),layout);
                Block(p.x,p.z,2.05f*layout.widthScale,1.4f*layout.depthScale);
            }
            var register=Checkout.CheckoutMarketLayout.CheckoutPoint(new Vector3(-3.9f,.74f,-4.7f),layout);
            if(Furniture==null)Block(register.x,register.z,2.6f*layout.widthScale,1.6f*layout.depthScale);
            if(Furniture==null)foreach(Transform sector in world)if(sector.name.StartsWith("Sector_")&&(layout.sectorIds==null||Array.IndexOf(layout.sectorIds,sector.name.Substring(7))>=0))
                foreach(var renderer in sector.GetComponentsInChildren<Renderer>(true))if(renderer.enabled){var b=renderer.bounds;Block(b.center.x,b.center.z,b.size.x,b.size.z);}
            var pedestrians=FindObjectsByType<NavMeshAgent>().Where(a=>a.isOnNavMesh&&!a.GetComponent<Checkout.CheckoutWalker>()).Select(a=>(agent:a,position:a.nextPosition,destination:a.destination,moving:a.hasPath)).ToArray();
            BuildNavigation();
            foreach(var pedestrian in pedestrians)if(NavMesh.SamplePosition(pedestrian.position,out var hit,2,pedestrian.agent.areaMask))
            {pedestrian.agent.Warp(hit.position);if(pedestrian.moving)pedestrian.agent.SetDestination(pedestrian.destination);}
        }
        // Navigation area of the shop floor, entrance ramp and rear service path. Shoppers and staff walk
        // everywhere; city pedestrians exclude it so they never cut through the building.
        public const int ShopArea=3;
        void BuildNavigation()
        {
            var sources=new List<NavMeshBuildSource>();
            void Box(Vector3 center,Vector3 size,int area,Quaternion rotation){sources.Add(new NavMeshBuildSource{shape=NavMeshBuildSourceShape.Box,transform=Matrix4x4.TRS(center,rotation,Vector3.one),size=size,area=area});}
            var anchor=Checkout.CheckoutMarketLayout.Anchor;
            var layoutMatrix=Matrix4x4.Translate(anchor+Checkout.CheckoutMarketLayout.Offset)*Matrix4x4.Scale(new Vector3(marketLayout.widthScale,1,marketLayout.depthScale))*Matrix4x4.Translate(-anchor);
            void Interior(Vector3 center,Vector3 size,Quaternion rotation){sources.Add(new NavMeshBuildSource{shape=NavMeshBuildSourceShape.Box,transform=layoutMatrix*Matrix4x4.TRS(center,rotation,Vector3.one),size=size,area=ShopArea});}
            // Eras 0-4 sell from a stall on the paving (CheckoutStall): no shop floor, ramp or rear path yet.
            bool stall=Checkout.CheckoutStall.Small;
            if(stall){var court=Checkout.CheckoutStall.Court;Box(court.center,court.size,ShopArea,Quaternion.identity);}
            else{
            Interior(new Vector3(0,.64f,0),new Vector3(18,.2f,14),Quaternion.identity);
            Interior(new Vector3(-1.75f,.345f,-8.825f),new Vector3(2.8f,.2f,3.6f),Quaternion.Euler(-9.44f,0,0));
            Interior(new Vector3(4,.37f,7.8f),new Vector3(1.1f,.2f,2.2f),Quaternion.Euler(20,0,0));
            var rear=Checkout.CheckoutMarketLayout.Project(new Vector3(4,.05f,8.8f),marketLayout);
            Box(new Vector3(rear.x,.05f,(rear.z+17.9f)*.5f),new Vector3(1.3f,.2f,17.9f-rear.z),ShopArea,Quaternion.identity);
            }
            // Outdoor customers use the same sidewalk surfaces as city pedestrians.
            // Do not bake the vehicle aisle: it creates shortcuts through parking bays.
            if(FindAnyObjectByType<Checkout.CheckoutCityTraffic>())
                for(int bay=0;bay<(marketLayout.stage>=3?5:3);bay++)Box(new Vector3(-17.1f,.05f,Checkout.CheckoutCityTraffic.BayZ(bay)-1.9f),new Vector3(5.4f,.2f,1.3f),0,Quaternion.identity);
            var streets=FindAnyObjectByType<Checkout.CheckoutCityStreets>();
            if(streets)streets.AddNavigation(sources);
            foreach(var r in obstacles)Box(new Vector3(r.center.x,1.5f,r.center.y),new Vector3(r.width,3,r.height),1,Quaternion.identity);
            foreach(var f in furniture)Box(f.center,f.size,1,Quaternion.Euler(0,f.yaw,0));
            // The shop's plinth: park and street surfaces under the building are not walkable, so city
            // pedestrians cannot cut through the walls. It stays well below the shop floor (.74) so the
            // floor itself is not merged with it.
            var low=Checkout.CheckoutMarketLayout.Project(new Vector3(-9.4f,0,-7.4f),marketLayout);var high=Checkout.CheckoutMarketLayout.Project(new Vector3(9.4f,0,7.4f),marketLayout);
            if(stall){var s=Checkout.CheckoutStall.Centre;Box(new Vector3(s.x,1f,s.z),new Vector3(4.2f,2f,2.7f),1,Quaternion.identity);}
            else Box(new Vector3((low.x+high.x)*.5f,-.4f,(low.z+high.z)*.5f),new Vector3(high.x-low.x+.3f,1.3f,high.z-low.z+.3f),1,Quaternion.identity);
            var settings=NavMesh.GetSettingsByID(0);settings.agentRadius=.28f;settings.agentHeight=2.3f;settings.agentClimb=.3f;settings.agentSlope=45;settings.overrideVoxelSize=true;settings.voxelSize=.075f;
            var navigationBounds=streets?streets.cityBounds:new Bounds(new Vector3(0,0,8),new Vector3(80,12,80));
            navigationBounds.Expand(new Vector3(4,12,4));
            var data=NavMeshBuilder.BuildNavMeshData(settings,sources,navigationBounds,Vector3.zero,Quaternion.identity);
            if(data==null)throw new InvalidOperationException("Navigation surface could not be built.");if(navigation.valid)navigation.Remove();navigation=NavMesh.AddNavMeshData(data);
        }
        void OnDestroy(){if(navigation.valid)navigation.Remove();}
        void Block(float x,float z,float w,float d){obstacles.Add(new Rect(x-w/2,z-d/2,w,d));}
        bool Clear(Vector3 p,float radius=.30f)
        {
            if(p.x < -8.9f+radius||p.x>8.9f-radius||p.z>17.5f||p.z< -9.5f)return false;
            if(p.z>6.65f&&(p.x<3.45f+radius||p.x>4.50f-radius))return false;
            // Store entrance is the only opening through the front wall.
            if(p.z< -6.9f+radius&&(p.x< -3.1f+radius||p.x>-.42f-radius))return false;
            foreach(var r in obstacles){float x=Mathf.Clamp(p.x,r.xMin,r.xMax),z=Mathf.Clamp(p.z,r.yMin,r.yMax);if((p.x-x)*(p.x-x)+(p.z-z)*(p.z-z)<radius*radius)return false;}
            if(routingWalker!=null)foreach(var other in Crowd())if(other!=routingWalker&&Vector3.Distance(p,Anchor(other))<radius+other.radius+.05f)return false;
            return true;
        }
        const float Step=.2f;const int W=94,H=137;
        public static float Ground(float z)=>z< -7.05f?Mathf.Lerp(.15f,.74f,Mathf.InverseLerp(-10.6f,-7.05f,z)):Mathf.Lerp(.74f,.15f,Mathf.InverseLerp(7.1f,8.7f,z));
        Vector3 Cell(int id){float z=-9.6f+(id/W)*Step;return new Vector3(-9.2f+(id%W)*Step,Ground(z),z);}
        int Nearest(Vector3 p,float radius)
        {
            float best=float.MaxValue;int found=-1;
            for(int i=0;i<W*H;i++){Vector3 q=Cell(i);if(!Clear(q,radius))continue;float d=(q-p).sqrMagnitude;if(d<best){best=d;found=i;}}
            return found;
        }
        public List<Vector3> Route(Vector3 start,Vector3 target,float radius=.30f)
        {
            var output=new List<Vector3>();int from=Nearest(start,radius),to=Nearest(target,radius);if(from<0||to<0)return output;
            var parent=new int[W*H];for(int i=0;i<parent.Length;i++)parent[i]=-2;
            var frontier=new Queue<int>();frontier.Enqueue(from);parent[from]=-1;
            int[] delta={-1,1,-W,W};
            while(frontier.Count>0)
            {
                int a=frontier.Dequeue();if(a==to)break;
                foreach(int d in delta){int b=a+d;if(b<0||b>=W*H||parent[b]!=-2||Math.Abs(b%W-a%W)+Math.Abs(b/W-a/W)!=1||!Clear(Cell(b),radius))continue;parent[b]=a;frontier.Enqueue(b);}
            }
            if(parent[to]==-2)return output;
            for(int n=to;n>=0;n=parent[n])output.Add(Cell(n));output.Reverse();
            // Visibility pruning removes grid zigzags while retaining swept-circle clearance.
            for(int i=0;i<output.Count-2;i++){int far=i+1;for(int j=i+2;j<output.Count;j++){if(!SegmentClear(output[i],output[j],radius))break;far=j;}if(far>i+1)output.RemoveRange(i+1,far-i-1);}
            return output;
        }
        bool SegmentClear(Vector3 a,Vector3 b,float radius)
        {int steps=Mathf.CeilToInt(Vector3.Distance(a,b)/.08f);Vector3 last=a;for(int i=0;i<=steps;i++){var p=Vector3.Lerp(a,b,steps==0?0:(float)i/steps);if(!Clear(p,radius))return false;last=p;}return true;}
        IEnumerable<Walker> Crowd(){foreach(var c in customers)if(c.root.gameObject.activeSelf)yield return c;foreach(var c in staff)if(c.root.gameObject.activeSelf)yield return c;}
        public string CrowdDiagnostics()
        {
            var lines=new List<string>();foreach(var w in Crowd())lines.Add(w.root.name+" position="+w.root.position+" phase="+w.phase+" node="+w.node+"/"+w.path.Count+" trips="+w.completedTrips+" blocked="+w.blocked.ToString("F1"));return string.Join("\n",lines);
        }
        public int CustomersServedAtLeastOnce(){int count=0;foreach(var w in customers)if(w.completedTrips>0)count++;return count;}
        public int CrowdOverlapCount()
        {
            var list=new List<Walker>(Crowd());int count=0;for(int i=0;i<list.Count;i++)for(int j=i+1;j<list.Count;j++)
            {Vector3 d=Anchor(list[i])-Anchor(list[j]);d.y=0;if(d.magnitude<list[i].radius+list[j].radius-.035f){count++;if(quietCapture)Debug.Log("CROWD_CONTACT "+list[i].root.name+" / "+list[j].root.name+" distance="+d.magnitude+" positions="+Anchor(list[i])+" / "+Anchor(list[j]));}}return count;
        }
        bool Walk(Walker w,float dt)
        {
            if(!w.agent.isOnNavMesh)return false;
            w.agent.isStopped=false;w.agent.speed=(w.worker?1.18f:(w.cart?.88f:1.04f))*speed;w.agent.acceleration=3.5f*speed*speed;
            Vector3 motion=w.agent.velocity;motion.y=0;
            if(motion.sqrMagnitude>.002f)w.root.rotation=Quaternion.RotateTowards(w.root.rotation,Quaternion.LookRotation(-motion),dt*(w.cart?145:230));
            w.root.position=w.agent.nextPosition+(w.cart?w.root.forward*.55f:Vector3.zero);
            if(w.cart){var grounded=w.root.position;grounded.y=Ground(grounded.z);w.root.position=grounded;}
            w.velocity=motion;
            if(!w.agent.pathPending&&w.agent.hasPath&&w.agent.remainingDistance<.22f){w.agent.isStopped=true;w.node=w.path.Count;return true;}
            if(!w.agent.pathPending&&Vector3.Distance(w.agent.nextPosition,w.destination)<.30f){w.agent.isStopped=true;return true;}
            return false;
        }
        static Vector3 Anchor(Walker w)=>w.root.position-(w.cart?w.root.forward*.55f:Vector3.zero);
        void Go(Walker w,Vector3 target)
        {
            w.facing=null;w.path=Route(Anchor(w),target,w.radius);w.node=0;w.blocked=0;
            if(NavMesh.SamplePosition(target,out var hit,1.25f,NavMesh.AllAreas))target=hit.position;
            w.destination=target;
            if(w.agent.isOnNavMesh){w.agent.isStopped=false;w.agent.SetDestination(target);}
        }
        void Idle(Walker w){w.velocity=Vector3.zero;if(w.agent.isOnNavMesh)w.agent.isStopped=true;}
        void ResolveCrowdContacts()
        {
            var agents=new List<Walker>(Crowd());
            for(int pass=0;pass<6;pass++)for(int i=0;i<agents.Count;i++)for(int j=i+1;j<agents.Count;j++)
            {
                var a=agents[i];var b=agents[j];if(!a.agent.isOnNavMesh||!b.agent.isOnNavMesh)continue;
                Vector3 delta=a.agent.nextPosition-b.agent.nextPosition;delta.y=0;
                float depth=a.radius+b.radius+.04f-delta.magnitude;if(depth<=0)continue;
                Vector3 correction=(delta.sqrMagnitude>.0001f?delta.normalized:Vector3.right)*Mathf.Min(depth*.51f,.06f);
                Nudge(a,correction);Nudge(b,-correction);
            }
            // Avoidance can move a stopped agent too. Keep its visible body at that position.
            foreach(var w in agents)if(w.agent.isOnNavMesh){w.root.position=w.agent.nextPosition+(w.cart?w.root.forward*.55f:Vector3.zero);if(w.cart){var ground=w.root.position;ground.y=Ground(ground.z);w.root.position=ground;}}
        }
        void Nudge(Walker w,Vector3 correction)
        {
            Vector3 from=w.agent.nextPosition,target=from+correction;
            if(NavMesh.Raycast(from,target,out _,NavMesh.AllAreas))return;
            if(!NavMesh.SamplePosition(target,out var surface,.12f,NavMesh.AllAreas))return;
            w.agent.nextPosition=surface.position;w.root.position=surface.position+(w.cart?w.root.forward*.55f:Vector3.zero);
            if(w.cart){var grounded=w.root.position;grounded.y=Ground(grounded.z);w.root.position=grounded;}
        }
        void Update()
        {
            if(!initialized)return;
            HandleCamera();float dt=Time.deltaTime*speed;
            if(Economy.Tick(dt)){hud.Toast("Delivery arrived at central storage",C("448F70"));Changed?.Invoke();Save();}
            if(Economy.opened&&speed>0)
            {
                foreach(var c in customers)TickCustomer(c,dt);
                TickStaff(dt);
                ResolveCrowdContacts();
            }
            saveTimer+=Time.unscaledDeltaTime;if(saveTimer>12){saveTimer=0;Save();}
            hud.Refresh();
        }
        void TickCustomer(Walker w,float dt)
        {
            if(w.wait>0){w.wait-=dt;Idle(w);if(w.facing.HasValue){w.root.rotation=Quaternion.RotateTowards(w.root.rotation,w.facing.Value,dt*180);if(w.cart&&w.agent.isOnNavMesh){w.root.position=w.agent.nextPosition+w.root.forward*.55f;}}return;}
            if(!w.root.gameObject.activeSelf)
            {
                Vector3 spawn=Entrance+(w.cart?Vector3.forward*.55f:Vector3.zero);
                foreach(var other in Crowd())if(Vector3.Distance(Anchor(other),spawn)<other.radius+w.radius+.3f)return;
                if(NavMesh.SamplePosition(spawn,out var start,2,NavMesh.AllAreas))spawn=start.position;
                w.root.rotation=Quaternion.Euler(0,180,0);w.root.position=spawn+(w.cart?w.root.forward*.55f:Vector3.zero);w.root.gameObject.SetActive(true);w.agent.Warp(spawn);w.root.position=spawn+(w.cart?w.root.forward*.55f:Vector3.zero);
            }
            bool atDisplay=w.phase==1&&Vector3.Distance(Anchor(w),w.destination)<.85f;
            if(w.phase!=0&&w.phase!=5&&w.phase!=6&&!atDisplay&&!Walk(w,dt))return;
            if(atDisplay)Idle(w);
            if(w.phase==0){w.department=(w.department+1)%5;Go(w,browse[w.department]);w.phase=1;}
            else if(w.phase==1)
            {
                Idle(w);FaceDisplay(w);
                bool special=w.department==0||w.department==2||w.department==3;
                w.wait=w.root.GetComponent<MarketCharacterAnimator>().Perform(special?"BuyAtSpecialSector":"GetFromShelf");
                if(special){string worker=w.department==0?"Worker_Baker":w.department==2?"Worker_Fishmonger":"Worker_Butcher";var server=world.Find(worker);if(server)server.GetComponent<MarketCharacterAnimator>().Perform("BuyAtSpecialSector");}
                w.phase=5;
            }
            else if(w.phase==5)
            {
                if(Economy.TakeFromShelf(w.department)){w.receipt+=Economy.departments[w.department].Price;w.basket++;hud.FloatLabel(w.root.position+Vector3.up*2.5f,"+1",accents[w.department]);}
                if(w.basket<2){w.department=(w.department+2)%5;Go(w,browse[w.department]);w.phase=1;w.basket++;}
                else{Go(w,P(-7.2,-3.4));w.phase=4;}
                w.wait=.2f;Changed?.Invoke();
            }
            else if(w.phase==4)
            {checkoutQueue.Add(w);Go(w,QueuePosition(checkoutQueue.Count-1));w.phase=2;}
            else if(w.phase==2)
            {
                // Only the first customer in checkout service may complete this tick.
                if(checkoutQueue.Count==0||checkoutQueue[0]!=w){w.wait=.3f;return;}
                Idle(w);w.facing=Quaternion.LookRotation(-(Register-w.root.position).normalized);
                w.wait=w.root.GetComponent<MarketCharacterAnimator>().Perform("PayAtCheckout");w.phase=6;
                var cashier=world.Find("Worker_Cashier");if(cashier)cashier.GetComponent<MarketCharacterAnimator>().Perform("PayAtCheckout");
            }
            else if(w.phase==6)
            {
                Economy.Checkout(w.receipt);if(w.receipt>0)hud.FloatLabel(w.root.position+Vector3.up*2.5f,"+"+w.receipt,C("DDA533"));
                w.completedTrips++;
                w.receipt=0;w.basket=0;w.wait=1.5f;w.phase=3;Go(w,Entrance);Changed?.Invoke();
                checkoutQueue.Remove(w);for(int q=0;q<checkoutQueue.Count;q++)Go(checkoutQueue[q],QueuePosition(q));
            }
            else{w.phase=0;w.wait=3+UnityEngine.Random.value*5;w.root.gameObject.SetActive(false);}
        }
        void FaceDisplay(Walker w)
        {
            Vector3[] targets={P(-4.5,4.14),P(-1.6,.3),P(1.5,4.3),P(6.5,4.3),P(6.55,.45)};
            Vector3 direction=targets[w.department]-w.root.position;direction.y=0;
            if(direction.sqrMagnitude>.01f)w.facing=Quaternion.LookRotation(-direction);
        }
        static Vector3 QueuePosition(int index) { Vector3[] places={P(-4.9,-6.2),P(-6.05,-6.2),P(-7.2,-6.2),P(-7.2,-5.05),P(-7.2,-3.9)};return places[Mathf.Clamp(index,0,4)]; }
        void TickStaff(float dt)
        {
            autoTimer+=dt;
            if(autoTimer>3)
            {
                autoTimer=0;
                for(int i=0;i<5;i++)if(Economy.departments[i].stock<6&&Economy.departments[i].reserve>0)QueueRefill(i,false);
            }
            for(int n=0;n<staff.Count;n++)
            {
                var w=staff[n];w.root.gameObject.SetActive(n<Economy.workers);if(n>=Economy.workers)continue;
                if(w.job<0)
                {
                    if(requests.Count==0){if(w.agent.hasPath)Walk(w,dt);continue;}
                    w.job=requests.Dequeue();w.phase=0;Go(w,P(4,17.2f));
                }
                if(w.wait>0){w.wait-=dt;Idle(w);continue;}
                if(!Walk(w,dt))continue;
                if(w.phase==0){w.phase=1;w.wait=1.2f;Go(w,browse[w.job]);}
                else
                {
                    int filled=Economy.Refill(w.job);
                    if(filled>0)hud.FloatLabel(w.root.position+Vector3.up*2.5f,"+"+filled+" stock",C("248B75"));
                    w.job=-1;w.wait=.4f;Go(w,P(4,6.1));Changed?.Invoke();
                }
            }
        }
        public void QueueRefill(int i,bool notify=true)
        {
            var d=Economy.departments[i];
            if(d.reserve<=0){if(notify)hud.Toast("Order a delivery to replenish storage.",C("CD665C"));return;}
            if(d.stock>=d.Capacity){if(notify)hud.Toast("This display is already full.",C("249787"));return;}
            if(requests.Contains(i))return;foreach(var w in staff)if(w.job==i)return;
            requests.Enqueue(i);if(notify)hud.Toast("Worker assigned to restock "+names[i],accents[i]);
        }
        public void Select(int i){selected=i;hud.DepartmentPanel(i);}
        public void OpenStore(){Economy.opened=true;hud.ClosePanel();hud.Toast("Welcome in! Your supermarket is open.",C("249787"));Save();}
        public void Order(int i){Economy.Order(i,out var m);hud.Toast(m,accents[i]);Changed?.Invoke();Save();}
        public void Upgrade(int i){Economy.Upgrade(i,out var m);hud.Toast(m,accents[i]);hud.DepartmentPanel(i);Changed?.Invoke();Save();}
        public void Hire(){Economy.Hire(out var m);hud.Toast(m,C("249787"));hud.WorkersPanel();Changed?.Invoke();Save();}
        public void Claim(int i){if(Economy.Claim(i)){hud.Toast("Goal complete! +100 coins",C("DDA533"));hud.GoalsPanel();Save();}}
        public void Save()
        {
            if(quietCapture||Economy==null)return;
            try{Directory.CreateDirectory(Application.persistentDataPath);string temp=SavePath+".tmp";File.WriteAllText(temp,JsonUtility.ToJson(Economy,true));File.Copy(temp,SavePath,true);File.Delete(temp);}
            catch(Exception ex){Debug.LogWarning("Could not save market: "+ex.Message);}
        }
        void OnApplicationPause(bool paused){if(paused)Save();}
        void OnApplicationQuit(){Save();}
        public void HomeCamera(){focus=new Vector3(0f,.1f,6f);zoom=20.5f;UpdateCamera();}
        // Build mode frames the shop floor and holds the camera still while a piece is dragged.
        public bool cameraLocked,pinchLocked;
        public void Focus(Vector3 point,float size){focus=new Vector3(point.x,.1f,point.z);zoom=Mathf.Clamp(size,6,38);UpdateCamera();}
        public (Vector3 focus,float zoom) CameraState=>(focus,zoom);
        public void Zoom(float amount){zoom=Mathf.Clamp(zoom+amount,6,38);UpdateCamera();}
        void UpdateCamera(){if(!view)return;view.orthographicSize=zoom;view.transform.position=focus+new Vector3(28,33,-38);view.transform.LookAt(focus);}
        public void ExternalCamera(){HandleCamera();}
        void HandleCamera()
        {
            if(Input.touchCount==2)
            {
                if(pinchLocked)return; // Build mode: two fingers turn the selected piece instead.
                var a=Input.GetTouch(0);var b=Input.GetTouch(1);float before=((a.position-a.deltaPosition)-(b.position-b.deltaPosition)).magnitude;
                Zoom((before-(a.position-b.position).magnitude)*.018f);dragged=true;return;
            }
            bool over=EventSystem.current&&(Input.touchCount>0?EventSystem.current.IsPointerOverGameObject(Input.GetTouch(0).fingerId):EventSystem.current.IsPointerOverGameObject());
            if(!over&&Mathf.Abs(Input.mouseScrollDelta.y)>.01f)Zoom(-Input.mouseScrollDelta.y*.8f);
            if(Input.GetMouseButtonDown(0)){pointerDown=lastPointer=Input.mousePosition;dragged=over;}
            if(Input.GetMouseButton(0)&&!over&&!cameraLocked)
            {
                Vector2 now=Input.mousePosition;var delta=now-lastPointer;
                if((now-pointerDown).magnitude>10)dragged=true;
                if(dragged){Vector3 right=view.transform.right;Vector3 forward=Vector3.Cross(right,Vector3.up);focus-=(right*delta.x+forward*delta.y)*zoom*2/Screen.height;focus.x=Mathf.Clamp(focus.x,-26,26);focus.z=Mathf.Clamp(focus.z,-16,34);UpdateCamera();}
                lastPointer=now;
            }
            if(Input.GetMouseButtonUp(0)&&!over&&!dragged)
            {
                Ray r=view.ScreenPointToRay(Input.mousePosition);
                if(enabled&&Physics.Raycast(r,out var hit,200))
                {
                    var target=hit.collider.GetComponent<DepartmentTarget>();if(target!=null)Select(target.department);
                }
            }
            if(Input.GetKeyDown(KeyCode.Escape))hud.ClosePanel();
        }
    }
}
