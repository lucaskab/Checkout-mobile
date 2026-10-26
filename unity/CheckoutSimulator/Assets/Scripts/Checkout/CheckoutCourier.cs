using System.Collections.Generic;
using MarketDay;
using TMPro;
using UnityEngine;
using UnityEngine.EventSystems;

namespace Checkout
{
    // The delivery motoboys in the 3D city (one bike per order that has a courier). Presentation only: the store
    // decides the order's state; this drives the bike from the road entry to a curb spot in front of the shop
    // (arriving around arriveAt), greets the player with a horn and a bubble. After the handover it rides the city
    // roads (CheckoutCityViews.RoadRoute) to the customer's door, timed to deliverAt, says the delivered line, then
    // rides off to the nearest map edge. Bikes yield to the same traffic pools through CheckoutTrafficJunctions.
    // A click on a parked courier sends handOverDelivery.
    public sealed class CheckoutCourier : MonoBehaviour
    {
        // Road lanes (CheckoutStreetLayout): avenue curb lane z -14, inner lane z -17. The bike parks just inside the
        // curb lane's kerb edge (the kerb is at z -12.5) so passing cars keep their own lane.
        const float InnerLane = -17f, CurbLane = -14f, ParkZ = -13.1f, Ground = .15f;
        const float Wheel = .34f, Cruise = 6.5f, Accel = 2f, Brake = 2.2f;
        const float Horn = .6f, HornAgain = .3f, LeaveVolume = .35f, ArriveVolume = .3f, CoinVolume = .18f;
        // Delivery drive: the speed is chosen so the bike reaches the door at order.deliverAt, clamped to this range.
        const float MinCruise = 2.6f, MaxCruise = 14f, DoorWait = 2f, HurriedWait = .6f;
        static readonly string[] DefaultArrive = { "Tô chegando, chefe!", "Já tô na porta!", "Chegou o pedido, chefe!" };
        static readonly string[] DefaultLeave = { "Valeu, chefe! Bora!", "Partiu entrega!", "Tô indo, chefe!" };
        static readonly string[] DefaultThanks = { "Entregue, chefe!", "Pedido na mão, valeu!", "Missão cumprida!" };

        // The courier currently in the scene (one per CheckoutCourier); used by the static route/position queries.
        static CheckoutCourier running;

        enum Phase { Waiting, Approach, Parked, Deliver, AtDoor, Leave }
        sealed class Bike
        {
            public string orderId;
            public Transform root, model, bubble, marker;
            public Transform[] wheels;
            public GameObject riding, parked;
            public Light headlight;
            public GameObject click;
            public AudioSource audio;
            public TMP_Text text;
            public Transform bubbleEdge, bubbleBody;
            public Phase phase;
            public readonly List<Vector3> path = new List<Vector3>();
            // Lucas 26/10 (smooth turns): `path` as one smooth path the bike rides at distance s, facing where it goes.
            public readonly CheckoutVehiclePath track = new CheckoutVehiclePath();
            public float s;
            public float speed, cruise, spotX, wheelAngle, lean, yaw, bubbleUntil, nextHorn, handedAt, pulse, doorUntil, routeLength;
            public double startAt;
            public bool greeted, announced, dirty, hurry, dropped;
            public Color color;
            public string[] arrive, leave, thanks;
            public readonly List<Vector3> route = new List<Vector3>();
        }

        CheckoutBridge bridge;
        CheckoutMap map;
        CheckoutEventAssets art;
        CheckoutNeighborhoodTraffic neighborhood;
        CheckoutCityTraffic city;
        Bounds cityBounds = new Bounds(new Vector3(0, 0, 6), new Vector3(80, 1, 84));
        readonly Dictionary<string, Bike> bikes = new Dictionary<string, Bike>();
        // Orders whose bike has already ridden off: never recreated while the order is still in the snapshot.
        readonly HashSet<string> departed = new HashSet<string>();
        // Preview routes (store curb to customer door) for orders whose bike is not out yet.
        readonly Dictionary<string, List<Vector3>> previews = new Dictionary<string, List<Vector3>>();
        // Per-frame scratch lists for Update (cleared and refilled, so the frame allocates nothing here).
        readonly HashSet<string> liveOrders = new HashSet<string>();
        readonly List<string> goneOrders = new List<string>();
        readonly List<Bike> stepBikes = new List<Bike>();
        static GameObject riderModel, parkedModel;
        static bool modelsLoaded;
        Vector3 spawnEast, despawnWest;

        public void Initialize(CheckoutBridge owner, CheckoutMap mapRef)
        {
            bridge = owner; map = mapRef;
            art = new CheckoutEventAssets();
            var streets = FindAnyObjectByType<CheckoutCityStreets>();
            if (streets && streets.cityBounds.size.sqrMagnitude > 1) cityBounds = streets.cityBounds;
            neighborhood = FindAnyObjectByType<CheckoutNeighborhoodTraffic>();
            city = FindAnyObjectByType<CheckoutCityTraffic>();
            spawnEast = new Vector3(cityBounds.max.x + 4f, Ground, InnerLane);
            despawnWest = new Vector3(cityBounds.min.x - 4f, Ground, InnerLane);
            running = this;
            if (!modelsLoaded)
            {
                modelsLoaded = true;
                riderModel = Resources.Load<GameObject>("CheckoutDelivery/delivery_bike_riding");
                parkedModel = Resources.Load<GameObject>("CheckoutDelivery/delivery_bike_parked");
            }
        }

        void OnDestroy()
        {
            foreach (var bike in bikes.Values) if (bike.root) Destroy(bike.root.gameObject);
            bikes.Clear();
            if (running == this) running = null;
            art?.Dispose();
        }

        // ------------------------------------------------------------------ queries for the app map
        // World position of the order's bike and its progress along the delivery route (0 at the store, 1 at the door
        // and after). False while the bike is not on the map (not yet arrived, or no bike for this order).
        public static bool TryGetBike(string orderId, out Vector3 worldPos, out float progress01)
        {
            worldPos = Vector3.zero; progress01 = 0f;
            var self = running;
            if (!self || string.IsNullOrEmpty(orderId)) return false;
            if (!self.bikes.TryGetValue(orderId, out var bike) || !bike.root) return false;
            if (bike.phase == Phase.Waiting) return false;
            worldPos = bike.root.position;
            progress01 = self.Progress(bike);
            return true;
        }

        // The delivery route points (store curb to the customer door); a preview while the bike is still at the store.
        // Empty when there is no route.
        public static List<Vector3> RouteOf(string orderId)
        {
            var self = running;
            if (!self || string.IsNullOrEmpty(orderId)) return new List<Vector3>();
            if (self.bikes.TryGetValue(orderId, out var bike) && bike.route.Count > 1) return new List<Vector3>(bike.route);
            var order = self.FindOrder(orderId);
            if (order != null && (order.status == "aguardando-moto" || order.status == "moto-na-porta") && self.map)
                return new List<Vector3>(self.PreviewRoute(orderId));
            return new List<Vector3>();
        }

        float Progress(Bike bike)
        {
            if (bike.phase == Phase.Deliver)
            {
                if (!bike.track.Ready || bike.routeLength <= .01f) return 0f;
                return Mathf.Clamp01(1f - (bike.track.Length - bike.s) / bike.routeLength);
            }
            if (bike.phase == Phase.Parked || bike.phase == Phase.Approach) return 0f;
            return bike.dropped ? 1f : 0f;
        }

        List<Vector3> PreviewRoute(string orderId)
        {
            if (!previews.TryGetValue(orderId, out var list))
            {
                // drawn as it will be ridden: corners rounded, round the roundabout's island
                list = new List<Vector3>();
                preview.Build(RideRoute(StoreCurb(), CheckoutCityViews.CustomerDoor(orderId))).Points(list);
                previews[orderId] = list;
            }
            return list;
        }

        readonly CheckoutVehiclePath preview = new CheckoutVehiclePath();
        Vector3 StoreCurb() => new Vector3(map.Entrance.x + .6f, Ground, ParkZ);

        // ------------------------------------------------------------------ snapshot sync
        void Update()
        {
            if (!bridge || !map) return;
            bool paused = CheckoutBuildMode.Open || CheckoutMapEditor.Open;
            if (paused)
            {
                foreach (var bike in bikes.Values) if (bike.root && bike.root.gameObject.activeSelf) bike.root.gameObject.SetActive(false);
                return;
            }
            var orders = bridge.State != null && bridge.State.delivery != null ? bridge.State.delivery.orders : null;
            liveOrders.Clear();
            var live = liveOrders;
            if (orders != null)
            {
                foreach (var order in orders)
                {
                    if (order == null || string.IsNullOrEmpty(order.id)) continue;
                    live.Add(order.id);
                    Sync(order);
                }
            }
            goneOrders.Clear();
            var gone = goneOrders;
            foreach (var pair in bikes) if (!live.Contains(pair.Key)) gone.Add(pair.Key);
            foreach (var id in gone) { Discard(bikes[id]); bikes.Remove(id); departed.Remove(id); }

            float dt = Time.deltaTime;
            // The bikes as they are at the start of this frame (a bike may leave the dictionary while the loop runs).
            stepBikes.Clear();
            foreach (var b in bikes.Values) stepBikes.Add(b);
            for (int i = 0; i < stepBikes.Count; i++)
            {
                var bike = stepBikes[i];
                if (!bike.root) continue;
                if (!bike.root.gameObject.activeSelf && bike.phase != Phase.Waiting) bike.root.gameObject.SetActive(true);
                if (bike.phase == Phase.Waiting) UpdateWaiting(bike);
                else if (bike.phase == Phase.Approach) { if (Drive(bike, dt, bike.cruise)) Park(bike); }
                else if (bike.phase == Phase.Parked) UpdateParked(bike);
                else if (bike.phase == Phase.Deliver) UpdateDelivery(bike, dt);
                else if (bike.phase == Phase.AtDoor) { if (Time.time >= bike.doorUntil) BeginRideOff(bike); }
                else if (bike.phase == Phase.Leave)
                {
                    if (Drive(bike, dt, Cruise)) { bikes.Remove(bike.orderId); departed.Add(bike.orderId); Discard(bike); }
                }
            }
            foreach (var bike in bikes.Values) Present(bike);
            ClickInput();
        }

        void Sync(DeliveryOrder order)
        {
            if (departed.Contains(order.id)) return;
            bool waiting = order.status == "aguardando-moto", door = order.status == "moto-na-porta";
            bool delivering = order.status == "a-caminho", finished = order.status == "entregue";
            bool leaving = delivering || finished || order.status == "expirado" || order.status == "cancelado";
            if (!bikes.TryGetValue(order.id, out var bike))
            {
                // A handed-over order whose bike is missing (e.g. after a reload) gets its bike back at the curb, if it is still on the way.
                bool onTheWay = delivering && order.deliverAt > CheckoutBridge.Now;
                if (!waiting && !door && !onTheWay) return;
                bike = Create(order, delivering || (door && !waiting));
                bikes[order.id] = bike;
            }
            if (bike.phase == Phase.Leave) return;
            bike.arrive = Phrases(order.courier, true);
            bike.leave = Phrases(order.courier, false);
            bike.thanks = DeliveredPhrases(order.courier);
            if (delivering)
            {
                if (bike.phase == Phase.Waiting) { bike.root.position = Spot(bike); bike.phase = Phase.Parked; }
                if (bike.phase == Phase.Parked || bike.phase == Phase.Approach) BeginDelivery(bike);
            }
            else if (finished && (bike.phase == Phase.Deliver || bike.phase == Phase.AtDoor)) HurryUp(bike);
            else if (leaving)
            {
                if (bike.phase == Phase.Waiting) { bikes.Remove(order.id); Discard(bike); return; }
                if (bike.phase == Phase.Parked || bike.phase == Phase.Approach) BeginLeave(bike, false);
            }
            if (bike.phase == Phase.Parked && door && !bike.greeted) Greet(bike);
        }

        // ------------------------------------------------------------------ creating a bike
        Bike Create(DeliveryOrder order, bool parkedNow)
        {
            var bike = new Bike { orderId = order.id, color = CourierColor(order.courier), arrive = Phrases(order.courier, true), leave = Phrases(order.courier, false), thanks = DeliveredPhrases(order.courier) };
            var go = new GameObject("Courier " + order.id);
            go.transform.SetParent(transform, false);
            bike.root = go.transform;
            bike.model = new GameObject("Model").transform;
            // A touch bigger than life so it reads from the city camera, like the other vehicles.
            bike.model.SetParent(bike.root, false);
            bike.model.localScale = Vector3.one * 1.35f;
            BuildModels(bike);
            bike.spotX = ChooseSpot(bike);
            var spot = Spot(bike);
            bike.path.AddRange(ApproachPath(bike));
            bike.track.Build(bike.path, CheckoutVehiclePath.StreetRadius); bike.s = 0;
            if (parkedNow)
            {
                // Already at the door when the store opened (or loaded): no drive, no horn.
                bike.root.position = spot; bike.root.rotation = Quaternion.LookRotation(Vector3.left);
                bike.phase = Phase.Parked; bike.greeted = false; bike.nextHorn = Time.time + 15f;
            }
            else
            {
                bike.root.position = spawnEast; bike.root.rotation = Quaternion.LookRotation(Vector3.left);
                bike.phase = Phase.Waiting; bike.root.gameObject.SetActive(false);
                bike.cruise = Cruise;
            }
            return bike;
        }

        void UpdateWaiting(Bike bike)
        {
            double arriveAt = ArriveAt(bike);
            double length = bike.track.Length;
            double lead = length / Cruise * 1000.0;
            if (arriveAt > 0 && CheckoutBridge.Now < arriveAt - lead) return;
            double remaining = arriveAt > 0 ? (arriveAt - CheckoutBridge.Now) / 1000.0 : length / Cruise;
            bike.cruise = Mathf.Clamp((float)(length / System.Math.Max(1.0, remaining)), 4f, 9f);
            bike.s = 0; bike.speed = 0; bike.phase = Phase.Approach;
            bike.root.SetPositionAndRotation(bike.track.Sample(0, out var heading), Quaternion.LookRotation(heading));
            bike.root.gameObject.SetActive(true);
            PlayOne(bike, CheckoutDeliverySound.BikeArrive, ArriveVolume);
        }

        double ArriveAt(Bike bike)
        {
            var o = FindOrder(bike.orderId);
            return o != null ? o.arriveAt : 0;
        }

        DeliveryOrder FindOrder(string id)
        {
            var orders = bridge.State != null && bridge.State.delivery != null ? bridge.State.delivery.orders : null;
            if (orders == null) return null;
            foreach (var o in orders) if (o != null && o.id == id) return o;
            return null;
        }

        void Park(Bike bike)
        {
            bike.phase = Phase.Parked; bike.speed = 0;
            bike.root.position = Spot(bike);
            bike.root.rotation = Quaternion.LookRotation(Vector3.left);
            bike.nextHorn = Time.time + 15f;
            ShowParkedModel(bike, true);
            var order = FindOrder(bike.orderId);
            if (order != null && order.status == "moto-na-porta") Greet(bike);
        }

        void Greet(Bike bike)
        {
            if (bike.greeted) return;
            bike.greeted = true;
            if (bike.click) bike.click.SetActive(true);
            PlayOne(bike, CheckoutDeliverySound.Horn, Horn);
            bike.nextHorn = Time.time + 15f + Random.Range(-2f, 2f);
            Say(bike, bike.arrive[Random.Range(0, bike.arrive.Length)], float.MaxValue);
        }

        void UpdateParked(Bike bike)
        {
            var order = FindOrder(bike.orderId);
            if (order != null && order.status == "moto-na-porta" && !bike.greeted) Greet(bike);
            if (bike.greeted && Time.time >= bike.nextHorn)
            {
                PlayOne(bike, CheckoutDeliverySound.Horn, HornAgain);
                bike.nextHorn = Time.time + 15f + Random.Range(-2f, 2f);
            }
        }

        void BeginLeave(Bike bike, bool announce)
        {
            bike.phase = Phase.Leave; bike.speed = 0;
            bike.path.Clear();
            var from = bike.root.position; from.y = Ground;
            bike.path.Add(from);
            if (Mathf.Abs(from.z - InnerLane) > .6f) bike.path.Add(new Vector3(from.x - 4f, Ground, InnerLane));
            bike.path.Add(despawnWest);
            Track(bike);
            ShowParkedModel(bike, false);
            if (announce)
            {
                Say(bike, bike.leave[Random.Range(0, bike.leave.Length)], 3f);
                PlayOne(bike, CheckoutDeliverySound.BikeLeave, LeaveVolume);
            }
            bike.greeted = false;
            bike.root.gameObject.SetActive(true);
        }

        // ------------------------------------------------------------------ delivery drive
        // Handover: the bike rides the city roads from its curb spot to the customer's door.
        void BeginDelivery(Bike bike)
        {
            var from = bike.phase == Phase.Parked ? Spot(bike) : Flat(bike.root.position);
            from.y = Ground;
            var door = CheckoutCityViews.CustomerDoor(bike.orderId);
            bike.path.Clear();
            bike.path.AddRange(RideRoute(from, door));
            Track(bike);
            bike.track.Points(bike.route);
            bike.routeLength = bike.track.Length;
            bike.cruise = Cruise;
            bike.hurry = false; bike.dropped = false; bike.greeted = false;
            bike.phase = Phase.Deliver;
            bike.root.gameObject.SetActive(true);
            ShowParkedModel(bike, false);
            Say(bike, bike.leave[Random.Range(0, bike.leave.Length)], 3f);
            PlayOne(bike, CheckoutDeliverySound.BikeLeave, LeaveVolume);
        }

        void UpdateDelivery(Bike bike, float dt)
        {
            bike.cruise = Mathf.Lerp(bike.cruise, DeliveryCruise(bike), Mathf.Clamp01(dt * 2f));
            if (Drive(bike, dt, bike.cruise)) ArriveAtDoor(bike);
        }

        // Speed that covers the rest of the route by order.deliverAt, clamped. Late: full speed. Early: slow.
        float DeliveryCruise(Bike bike)
        {
            if (bike.hurry) return MaxCruise;
            if (bike.s >= bike.track.Length) return Cruise;
            var order = FindOrder(bike.orderId);
            double at = order != null ? order.deliverAt : 0;
            if (at <= 0) return Cruise;
            double seconds = (at - CheckoutBridge.Now) / 1000.0;
            double meters = bike.track.Length - bike.s;
            float need = (float)(meters / System.Math.Max(.5, seconds));
            return Mathf.Clamp(need, MinCruise, MaxCruise);
        }

        // The order was finished before the bike got there: finish the ride quickly, no teleport.
        void HurryUp(Bike bike)
        {
            bike.hurry = true;
            if (bike.phase == Phase.AtDoor) bike.doorUntil = Mathf.Min(bike.doorUntil, Time.time + HurriedWait);
        }

        void ArriveAtDoor(Bike bike)
        {
            bike.phase = Phase.AtDoor; bike.speed = 0; bike.dropped = true;
            bike.doorUntil = Time.time + (bike.hurry ? HurriedWait : DoorWait);
            ShowParkedModel(bike, true);
            if (bike.click) bike.click.SetActive(false);
            Say(bike, bike.thanks[Random.Range(0, bike.thanks.Length)], DoorWait + HurriedWait + .4f);
            PlayOne(bike, CheckoutDeliverySound.Coin, CoinVolume);
        }

        // After the door: ride off along the roads to the nearest edge of the city, then despawn.
        void BeginRideOff(Bike bike)
        {
            var from = Flat(bike.root.position); from.y = Ground;
            bike.path.Clear();
            bike.path.AddRange(RideRoute(from, EdgePoint(from)));
            Track(bike);
            bike.speed = 0; bike.cruise = Cruise;
            bike.phase = Phase.Leave;
            ShowParkedModel(bike, false);
            Say(bike, bike.leave[Random.Range(0, bike.leave.Length)], 3f);
            PlayOne(bike, CheckoutDeliverySound.BikeLeave, LeaveVolume);
        }

        // The smooth path of a new bike.path, setting off the way the bike faces.
        static void Track(Bike bike) { bike.track.Build(bike.path, CheckoutVehiclePath.StreetRadius, bike.root ? bike.root.forward : (Vector3?)null); bike.s = 0; }

        // Road route from one point to another as a polyline at ground level (its corners are rounded by the path the
        // bike rides). Always at least two points.
        List<Vector3> RideRoute(Vector3 from, Vector3 to)
        {
            from.y = Ground; to.y = Ground;
            var raw = CheckoutCityViews.RoadRoute(from, to);
            var points = new List<Vector3>();
            points.Add(from);
            if (raw != null)
                foreach (var p in raw)
                {
                    var q = new Vector3(p.x, Ground, p.z);
                    if (Flat(q - points[points.Count - 1]).magnitude > .02f) points.Add(q);
                }
            if (Flat(to - points[points.Count - 1]).magnitude > .02f) points.Add(to);
            while (points.Count < 2) points.Add(to);
            return points;
        }

        // The nearest point on the city's outer edge (the bike leaves the map there).
        Vector3 EdgePoint(Vector3 p)
        {
            float left = p.x - cityBounds.min.x, right = cityBounds.max.x - p.x;
            float down = p.z - cityBounds.min.z, up = cityBounds.max.z - p.z;
            float least = Mathf.Min(Mathf.Min(left, right), Mathf.Min(down, up));
            var edge = new Vector3(p.x, Ground, p.z);
            if (least == left) edge.x = cityBounds.min.x;
            else if (least == right) edge.x = cityBounds.max.x;
            else if (least == down) edge.z = cityBounds.min.z;
            else edge.z = cityBounds.max.z;
            return edge;
        }

        static string[] DeliveredPhrases(DeliveryCourier courier)
        {
            var list = courier != null && courier.phrases != null ? courier.phrases.delivered : null;
            if (list != null && list.Length > 0) return list;
            return DefaultThanks;
        }

        // ------------------------------------------------------------------ driving
        // Rides the bike's smooth path; true once its end is reached.
        bool Drive(Bike bike, float dt, float cruise)
        {
            if (dt <= 0) return false;
            var t = bike.root; var track = bike.track;
            if (!track.Ready || bike.s >= track.Length - .02f) return true;
            track.Sample(bike.s, out var dir);
            float limit = Mathf.Max(.35f, track.StopSpeed(bike.s, Brake));
            // a bike leans into its bends and takes them a little quicker than a car
            float top = Mathf.Min(cruise, limit, track.Allowed(bike.s, cruise, Brake, 3f));
            bool blocked = Blocked(bike, dir);
            if (CheckoutTrafficJunctions.Hold(t, dir, blocked, bike.speed * bike.speed / (2 * Brake * 1.8f))) top = 0;
            bike.speed = bike.speed < top ? Mathf.Min(top, bike.speed + Accel * dt) : Mathf.Max(top, bike.speed - Brake * 1.8f * dt);
            float step = Mathf.Min(bike.speed * dt, track.Length - bike.s);
            bike.s += step;
            float yawBefore = t.eulerAngles.y;
            var p = track.Sample(bike.s, out var heading); p.y = Ground;
            t.SetPositionAndRotation(p, Quaternion.LookRotation(heading));
            float yawRate = Mathf.DeltaAngle(yawBefore, t.eulerAngles.y) / dt;
            bike.lean = Mathf.Lerp(bike.lean, Mathf.Clamp(-yawRate * .1f * Mathf.Clamp01(bike.speed / 4f), -14f, 14f), Mathf.Clamp01(dt * 6f));
            bike.wheelAngle += step / Wheel * Mathf.Rad2Deg;
            return false;
        }

        // Anything ahead in the same lane: cars, trucks, other couriers.
        bool Blocked(Bike bike, Vector3 dir)
        {
            var from = bike.root.position;
            if (neighborhood && neighborhood.cars != null)
                foreach (var car in neighborhood.cars)
                    if (car != null && car.vehicle && car.vehicle.gameObject.activeInHierarchy && CheckoutTrafficJunctions.Ahead(from, dir, car.vehicle.position, 4.6f, 1.3f)) return true;
            if (city && city.vehicles != null)
                foreach (var v in city.vehicles)
                    if (v && v.gameObject.activeInHierarchy && CheckoutTrafficJunctions.Ahead(from, dir, v.position, 4.6f, 1.3f)) return true;
            var trucks = map.Trucks;
            if (trucks)
                foreach (var t in trucks.All)
                    if (t && t.gameObject.activeInHierarchy && CheckoutTrafficJunctions.Ahead(from, dir, t.position, 9f, 2f)) return true;
            foreach (var other in bikes.Values)
                if (other != bike && other.root && other.root.gameObject.activeInHierarchy && other.phase != Phase.Waiting && other.phase != Phase.Parked
                    && CheckoutTrafficJunctions.Ahead(from, dir, other.root.position, 3.2f, 1f)) return true;
            return false;
        }

        // Approach: from off the east end along the inner lane, merging into the curb lane at the spot.
        List<Vector3> ApproachPath(Bike bike)
        {
            float sx = bike.spotX;
            var points = new List<Vector3>
            {
                spawnEast,
                new Vector3(sx + 12f, Ground, InnerLane),
                new Vector3(sx + 6f, Ground, InnerLane),
                // the last metres along the kerb, so it pulls up already facing the way it stands parked
                new Vector3(sx + 2.5f, Ground, ParkZ),
                new Vector3(sx, Ground, ParkZ),
            };
            return points;
        }

        static Vector3 Flat(Vector3 v) { v.y = 0; return v; }

        // ------------------------------------------------------------------ curb spots
        Vector3 Spot(Bike bike) => new Vector3(bike.spotX, Ground, ParkZ);

        // The first spot in front of (or near) the store that no road works, parked truck or other courier takes.
        float ChooseSpot(Bike bike)
        {
            float ex = map.Entrance.x;
            float[] offsets = { .6f, -2.4f, -4.8f, -7.2f, 3f, 5.4f, 8f };
            foreach (var off in offsets)
            {
                float x = ex + off;
                if (!MergeClear(x)) continue;
                if (OtherSpotNear(bike, x)) continue;
                if (TruckAt(x)) continue;
                return x;
            }
            return ex + .6f;
        }

        // The bike merges from the inner lane over the four metres before its spot: keep that clear of road works.
        static bool MergeClear(float x)
        {
            if (!CheckoutEventVisuals.RoadWorks) return true;
            return x + 4f <= -1.6f || x >= 6.6f;
        }

        bool OtherSpotNear(Bike bike, float x)
        {
            foreach (var other in bikes.Values)
                if (other != bike && other.phase != Phase.Leave && Mathf.Abs(other.spotX - x) < 2.4f) return true;
            return false;
        }

        bool TruckAt(float x)
        {
            var trucks = map.Trucks;
            if (!trucks) return false;
            foreach (var t in trucks.All)
            {
                if (!t || !t.gameObject.activeInHierarchy) continue;
                var renderers = t.GetComponentsInChildren<Renderer>();
                if (renderers.Length == 0) continue;
                var b = renderers[0].bounds;
                foreach (var r in renderers) b.Encapsulate(r.bounds);
                if (b.min.x < x + 1.5f && b.max.x > x - 1.5f && b.min.z < ParkZ + .6f && b.max.z > ParkZ - .6f) return true;
            }
            return false;
        }

        // ------------------------------------------------------------------ models
        void BuildModels(Bike bike)
        {
            if (riderModel)
            {
                bike.riding = Instantiate(riderModel, bike.model);
                bike.riding.name = "Riding";
                bike.riding.transform.localPosition = Vector3.zero;
                bike.riding.transform.localRotation = Quaternion.identity;
                bike.wheels = FindWheels(bike.riding.transform);
                TintPaint(bike.riding, bike.color);
                SeatRider(bike.riding);
            }
            else BuildFallback(bike);
            if (parkedModel)
            {
                bike.parked = Instantiate(parkedModel, bike.model);
                bike.parked.name = "Parked";
                bike.parked.transform.localPosition = Vector3.zero;
                bike.parked.transform.localRotation = Quaternion.identity;
                bike.parked.SetActive(false);
                TintPaint(bike.parked, bike.color);
            }
            // Headlight (only while the bike moves).
            var lightGo = new GameObject("Headlight");
            lightGo.transform.SetParent(bike.model, false);
            lightGo.transform.localPosition = new Vector3(0, .8f, .9f);
            lightGo.transform.localRotation = Quaternion.Euler(-8, 0, 0);
            bike.headlight = lightGo.AddComponent<Light>();
            bike.headlight.type = LightType.Spot;
            bike.headlight.range = 7f; bike.headlight.spotAngle = 70f; bike.headlight.intensity = 1.1f;
            bike.headlight.shadows = LightShadows.None; bike.headlight.color = new Color(1f, .95f, .85f);
            bike.headlight.enabled = false;
            // Clickable body (only while a courier waits at the kerb).
            var clickGo = new GameObject("Handover");
            clickGo.transform.SetParent(bike.root, false);
            var box = clickGo.AddComponent<BoxCollider>();
            box.center = new Vector3(0, .8f, 0); box.size = new Vector3(1f, 1.6f, 2.2f);
            clickGo.AddComponent<HandoverTarget>().orderId = bike.orderId;
            bike.click = clickGo;
            clickGo.SetActive(false);
            // Engine sound from the bike itself (3D).
            bike.audio = bike.root.gameObject.AddComponent<AudioSource>();
            bike.audio.playOnAwake = false; bike.audio.spatialBlend = 1f;
            bike.audio.minDistance = 4f; bike.audio.maxDistance = 40f; bike.audio.dopplerLevel = 0f;
            BuildBubble(bike);
        }

        // The motoboy on the seat (Lucas 12/10): delivery_rider.fbx, built by ArtSource/NPCs/build_motoboy_ride.py in the
        // bike's own frame, replaces the rider modelled into delivery_bike_riding (its courier and helmet meshes are hidden).
        static GameObject riderMesh; static Material riderMaterial; static bool riderLoaded;
        static void SeatRider(GameObject riding)
        {
            if (!riderLoaded) { riderLoaded = true; riderMesh = Resources.Load<GameObject>("CheckoutDelivery/delivery_rider"); riderMaterial = Resources.Load<Material>("CheckoutDelivery/delivery_rider"); }
            if (!riderMesh) return;
            foreach (var r in riding.GetComponentsInChildren<Renderer>(true))
                if (r.name.StartsWith("fx_riding_DK_courier") || r.name.StartsWith("fx_riding_DK_helm")) r.enabled = false;
            var rider = Instantiate(riderMesh, riding.transform, false);
            rider.name = "Rider";
            rider.transform.localPosition = Vector3.zero; rider.transform.localRotation = Quaternion.identity; rider.transform.localScale = Vector3.one;
            if (riderMaterial) foreach (var r in rider.GetComponentsInChildren<Renderer>(true)) r.sharedMaterial = riderMaterial;
        }

        void ShowParkedModel(Bike bike, bool parked)
        {
            bool useParked = parked && bike.parked;
            if (bike.riding) bike.riding.SetActive(!useParked);
            if (bike.parked) bike.parked.SetActive(useParked);
            bike.lean = parked ? 6f : 0f;
            if (bike.headlight) bike.headlight.enabled = !parked;
            if (bike.click) bike.click.SetActive(parked && bike.greeted);
        }

        static Transform[] FindWheels(Transform root)
        {
            var list = new List<Transform>();
            foreach (var t in root.GetComponentsInChildren<Transform>(true))
            {
                var n = t.name.ToLowerInvariant();
                if (n.Contains("wheel") || n.Contains("tire") || n.Contains("tyre")) list.Add(t);
            }
            return list.ToArray();
        }

        static void TintPaint(GameObject model, Color color)
        {
            var block = new MaterialPropertyBlock();
            block.SetColor("_BaseColor", color); block.SetColor("_Color", color);
            foreach (var r in model.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                if (mats.Length != 1 || !mats[0]) continue;
                var name = mats[0].name.ToLowerInvariant();
                if (name.Contains("paint") || name.Contains("body")) r.SetPropertyBlock(block);
            }
        }

        // Primitive stand-in when the bike model is not in Resources yet.
        void BuildFallback(Bike bike)
        {
            var root = bike.model;
            var wheels = new List<Transform>();
            foreach (var z in new[] { -.52f, .52f })
            {
                var pivot = new GameObject(z < 0 ? "Wheel R" : "Wheel F").transform;
                pivot.SetParent(root, false); pivot.localPosition = new Vector3(0, Wheel, z);
                art.Part(pivot, "Tyre", Vector3.zero, new Vector3(Wheel * 2, .06f, Wheel * 2), "354451", PrimitiveType.Cylinder).localRotation = Quaternion.Euler(0, 0, 90);
                art.Part(pivot, "Rim", Vector3.zero, new Vector3(Wheel * 1.4f, .07f, Wheel * 1.4f), "C9CDD0", PrimitiveType.Cylinder).localRotation = Quaternion.Euler(0, 0, 90);
                wheels.Add(pivot);
            }
            bike.wheels = wheels.ToArray();
            string paint = bike.color.a > 0 ? ColorUtility.ToHtmlStringRGB(bike.color) : "EF8B40";
            art.Part(root, "Frame", new Vector3(0, .62f, .05f), new Vector3(.1f, .12f, 1.2f), "354451");
            art.Part(root, "Tank", new Vector3(0, .9f, .25f), new Vector3(.3f, .22f, .6f), paint);
            art.Part(root, "Seat", new Vector3(0, .82f, -.12f), new Vector3(.22f, .06f, .42f), "354451");
            art.Part(root, "Fork", new Vector3(0, .7f, .45f), new Vector3(.07f, .6f, .07f), "354451");
            art.Part(root, "Bars", new Vector3(0, 1.05f, .42f), new Vector3(.5f, .05f, .05f), "354451");
            art.Part(root, "Delivery box", new Vector3(0, 1.02f, -.5f), new Vector3(.62f, .5f, .55f), "2E8CAE");
            art.Part(root, "Box stripe", new Vector3(0, 1.27f, -.5f), new Vector3(.64f, .04f, .57f), "EF8B40");
            art.Part(root, "Rider jacket", new Vector3(0, 1.2f, .05f), new Vector3(.36f, .5f, .28f), "354451");
            art.Part(root, "Helmet", new Vector3(0, 1.5f, .05f), new Vector3(.26f, .26f, .26f), "E15533", PrimitiveType.Sphere);
        }

        // ------------------------------------------------------------------ bubble and marker
        void BuildBubble(Bike bike)
        {
            var go = new GameObject("Courier bubble");
            go.transform.SetParent(bike.root, false);
            go.transform.localPosition = new Vector3(0, 2.55f, 0);
            go.transform.localScale = Vector3.one * 2.2f;
            bike.bubble = go.transform;
            bike.bubbleEdge = art.Part(bike.bubble, "Bubble edge", new Vector3(0, 0, .012f), new Vector3(1.6f, .46f, .03f), "4A3624");
            bike.bubbleBody = art.Part(bike.bubble, "Bubble", Vector3.zero, new Vector3(1.5f, .4f, .04f), "FFF7EC");
            var tail = art.Part(bike.bubble, "Tail", new Vector3(0, -.27f, .004f), new Vector3(.14f, .14f, .035f), "FFF7EC");
            tail.localRotation = Quaternion.Euler(0, 0, 45);
            var textGo = new GameObject("Text");
            textGo.transform.SetParent(bike.bubble, false);
            textGo.transform.localPosition = new Vector3(0, 0, -.05f);
            var tmp = textGo.AddComponent<TextMeshPro>();
            tmp.font = CheckoutDesktopKit.Label;
            tmp.fontSize = 36;
            tmp.alignment = TextAlignmentOptions.Center;
            tmp.textWrappingMode = TextWrappingModes.NoWrap;
            tmp.color = CheckoutDesktopKit.Ink;
            tmp.text = "";
            CheckoutI18nText.Register(tmp);
            bike.text = tmp;
            var markerGo = new GameObject("Marker");
            markerGo.transform.SetParent(bike.root, false);
            markerGo.transform.localPosition = new Vector3(0, 2.05f, 0);
            bike.marker = markerGo.transform;
            art.Part(bike.marker, "Pin", Vector3.zero, new Vector3(.42f, .42f, .42f), "EF8B40").localRotation = Quaternion.Euler(45, 45, 45);
            bike.bubble.gameObject.SetActive(false);
            bike.marker.gameObject.SetActive(false);
        }

        // Shows `line` above the bike for `seconds` (float.MaxValue: until it leaves).
        void Say(Bike bike, string line, float seconds)
        {
            if (!bike.text) return;
            bike.text.text = line;
            bike.text.ForceMeshUpdate();
            // Fit the bubble to the line: one line of text about 0.22 m tall.
            float h = Mathf.Max(.01f, bike.text.preferredHeight);
            float s = .22f / h;
            bike.text.transform.localScale = Vector3.one * s;
            float width = bike.text.preferredWidth * s + .3f;
            bike.bubbleBody.localScale = new Vector3(width, .4f, .04f);
            bike.bubbleEdge.localScale = new Vector3(width + .1f, .46f, .03f);
            bike.bubbleUntil = seconds >= float.MaxValue ? float.MaxValue : Time.time + seconds;
            bike.bubble.gameObject.SetActive(true);
        }

        // Billboard, pulse and hide timers.
        void Present(Bike bike)
        {
            if (!bike.root || !bike.model) return;
            bike.pulse += Time.deltaTime;
            bool parked = bike.phase == Phase.Parked;
            if (bike.bubble && bike.bubble.gameObject.activeSelf && Time.time > bike.bubbleUntil)
                bike.bubble.gameObject.SetActive(false);
            if (bike.marker) bike.marker.gameObject.SetActive(parked && bike.greeted);
            if (bike.marker && bike.marker.gameObject.activeSelf)
                bike.marker.localScale = Vector3.one * (1 + Mathf.Sin(bike.pulse * 6f) * .12f);
            if (bike.bubble && bike.bubble.gameObject.activeSelf)
            {
                bike.bubble.localPosition = new Vector3(0, 3.4f + Mathf.Sin(bike.pulse * 3f) * .05f, 0);
                if (Camera.main) bike.bubble.rotation = Camera.main.transform.rotation;
            }
            // Lean, bob and wheel roll.
            bool moving = bike.phase == Phase.Approach || bike.phase == Phase.Deliver || bike.phase == Phase.Leave;
            float bob = moving ? Mathf.Sin(bike.pulse * 14f) * .012f : 0f;
            bike.model.localPosition = new Vector3(0, bob, 0);
            bike.model.localRotation = Quaternion.Euler(0, 0, bike.lean);
            if (bike.wheels != null) foreach (var w in bike.wheels) if (w) w.localRotation = Quaternion.Euler(bike.wheelAngle, 0, 0);
            if (bike.headlight) bike.headlight.enabled = moving;
        }

        // ------------------------------------------------------------------ sound
        void PlayOne(Bike bike, AudioClip clip, float volume)
        {
            if (!clip || !bike.audio || !bike.root || !bike.root.gameObject.activeInHierarchy) return;
            bike.audio.PlayOneShot(clip, volume);
        }

        // ------------------------------------------------------------------ click to hand over
        float pressX = -1, pressY = -1; bool dragged;

        void ClickInput()
        {
            if (Input.GetMouseButtonDown(0)) { pressX = Input.mousePosition.x; pressY = Input.mousePosition.y; dragged = false; }
            if (Input.GetMouseButton(0) && (Mathf.Abs(Input.mousePosition.x - pressX) > 10 || Mathf.Abs(Input.mousePosition.y - pressY) > 10)) dragged = true;
            if (!Input.GetMouseButtonUp(0) || dragged) return;
            if (CheckoutBuildMode.Open || CheckoutMapEditor.Open) return;
            if (CheckoutPointer.OverUi) return;
            var cam = CurrentCamera();
            if (!cam) return;
            if (!Physics.Raycast(cam.ScreenPointToRay(Input.mousePosition), out var hit, 150)) return;
            var target = hit.collider.GetComponent<HandoverTarget>();
            if (!target) return;
            if (!bikes.TryGetValue(target.orderId, out var bike) || bike.phase != Phase.Parked) return;
            if (Time.time - bike.handedAt < 3f) return;
            bike.handedAt = Time.time;
            bridge.Command("handOverDelivery", "[\"" + bike.orderId + "\"]");
        }

        Camera CurrentCamera()
        {
            var sim = FindAnyObjectByType<MarketSimulation>();
            if (sim && sim.view) return sim.view;
            return Camera.main;
        }

        void Discard(Bike bike)
        {
            if (bike.root) Destroy(bike.root.gameObject);
        }

        static string[] Phrases(DeliveryCourier courier, bool arrive)
        {
            var list = courier != null && courier.phrases != null ? (arrive ? courier.phrases.arrive : courier.phrases.leave) : null;
            if (list != null && list.Length > 0) return list;
            return arrive ? DefaultArrive : DefaultLeave;
        }

        static Color CourierColor(DeliveryCourier courier)
        {
            var fallback = new Color(.16f, .55f, .62f);
            if (courier == null || string.IsNullOrEmpty(courier.color)) return fallback;
            var text = courier.color.StartsWith("#") ? courier.color : "#" + courier.color;
            return ColorUtility.TryParseHtmlString(text, out var c) ? c : fallback;
        }

        // Clickable collider of a courier; not a CheckoutTarget, so the bridge never sends a panel for it.
        sealed class HandoverTarget : MonoBehaviour { public string orderId; }
    }
}
