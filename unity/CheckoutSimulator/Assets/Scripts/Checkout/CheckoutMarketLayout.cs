using System;
using System.Collections.Generic;
using System.Linq;
using MarketDay;
using UnityEngine;

namespace Checkout
{
    [Serializable]
    public class MarketLayout
    {
        public int stage;
        public float widthScale = 1, depthScale = 1;
        public bool storage, parking, loadingYard, premium;
        // The large central warehouse replaces the small storage building; its truck yard replaces the old one.
        public bool storageLarge;
        public string[] sectorIds;
    }

    // Only projects purchased areas. Level and payment remain owned by React Native.
    public class CheckoutMarketLayout : MonoBehaviour
    {
        class Placement { public Transform root; public Vector3 position, scale, expectedPosition, expectedScale; public Quaternion expectedRotation; public bool resize; }
        readonly List<Placement> placements = new List<Placement>();
        readonly List<GameObject> parkingDetails = new List<GameObject>();
        readonly List<GameObject> premiumDetails = new List<GameObject>();
        readonly List<GameObject> storageDetails = new List<GameObject>();
        MarketDeliveryWorker delivery;
        Vector3[] deliveryRoute;
        Vector3 storageDoor;
        Transform world;
        MarketSimulation simulation;
        CheckoutCityTraffic traffic;
        CheckoutExpansionNeighborhood neighborhood;
        string signature;
        public MarketLayout State { get; private set; } = new MarketLayout();
        // Set by the map just before a paid growth so the new facade waits for the timelapse reveal.
        public bool holdNewDressing;
        CheckoutStageDressing dressing;
        CheckoutMarketShell shell;
        // The west wall stays put: the shop grows east towards the street and north towards the yard.
        // z -10.6 is where the entrance steps meet the sidewalk.
        public static readonly Vector3 Anchor = new Vector3(-9.4f, 0, -10.6f);
        // The block is a grid of equal lots (src/data/market-lots.ts: columns A B C from the west, rows 1-4 from the
        // avenue) and the market fills whole lots from the corner on the left of the avenue (A1). The whole shop
        // sits 7.45 m west of the supplied map, so its west wall stands on the A1 edge (x -17.1), and 2.1 m
        // further into the block, so the entrance steps start at the back edge of the sidewalk.
        public static readonly Vector3 Offset = new Vector3(-7.45f, 0, 2.1f);
        public static Vector3 WorldAnchor => Anchor + Offset;
        public Vector3 Point(Vector3 point) => Project(point, State);
        public static Vector3 CheckoutPoint(Vector3 point, MarketLayout layout) => Project(point, layout);
        public static Vector3 Project(Vector3 point, MarketLayout layout)
        {
            return Anchor + Offset + Vector3.Scale(point - Anchor, new Vector3(layout.widthScale, 1, layout.depthScale));
        }
        public bool HasSector(string id) => State.sectorIds == null || Array.IndexOf(State.sectorIds, id) >= 0;
        // The front sliding doors and the rear roller door keep their real size when the shop grows (a door
        // stretched 1.78 times reads as a giant): only the walls and the glass sidelights around them widen.
        // Small shops (width under 1) shrink them with the facade. Base door centres: front -1.75, rear 4.02.
        public const float FrontDoorX = -1.75f, RearDoorX = 4.02f;
        public static float DoorScale(MarketLayout layout) => layout == null ? 1 : Mathf.Min(1, layout.widthScale);
        public static float DoorPoint(float baseX, float centre, MarketLayout layout) =>
            Project(new Vector3(centre, 0, 0), layout).x + (baseX - centre) * DoorScale(layout);
        static bool IsDoor(Transform t) => t.name.StartsWith("Anim_Door") || (t.parent && t.parent.name == "Clean entrance frame");

        public void Initialize(Transform root)
        {
            world = root;
            neighborhood = world.GetComponentInChildren<CheckoutExpansionNeighborhood>(true);
            dressing = world.GetComponentInChildren<CheckoutStageDressing>(true);
            shell = world.GetComponentInChildren<CheckoutMarketShell>(true);
            if (shell)
            {
                // The textured shell replaces the supplied building mesh and the old entrance slab/steps.
                foreach (var name in new[] { "Building", "City Detail Repairs" })
                {
                    var old = world.Find(name);
                    if (old) foreach (var r in old.GetComponentsInChildren<Renderer>(true)) r.forceRenderingOff = true;
                }
                // The shell's entrance has its own planters where these flower boxes stood.
                foreach (var t in world.GetComponentsInChildren<Transform>(true))
                    if (t.name.StartsWith("Entrance flowers")) foreach (var r in t.GetComponentsInChildren<Renderer>(true)) r.forceRenderingOff = true;
            }
            simulation = FindAnyObjectByType<MarketSimulation>();
            traffic = FindAnyObjectByType<CheckoutCityTraffic>();
            // The depot: its pose in the scene is the old one behind the shop; PlaceDepot moves it per layout.
            depot = world.Find("Warehouse");
            if (depot) { depotBasePosition = depot.position; depotBaseRotation = depot.rotation; }
            // The old parking stripes painted along the west edge of the block: the parking lot is on C1/C3 now.
            var paint = world.Find("City Block/CityPaint"); if (paint) paint.gameObject.SetActive(false);
            // The hypermarket's open-air café stood where its parking lot (lot C3) is now.
            var cafe = world.Find("Market Stage Dressing/S4 plaza cafe");
            if (cafe) { var item = cafe.GetComponent<CheckoutStageItem>(); if (item) DestroyImmediate(item); cafe.gameObject.SetActive(false); }
            delivery = world.GetComponentInChildren<MarketDeliveryWorker>(true);
            if(delivery){deliveryRoute=(Vector3[])delivery.route.Clone();storageDoor=delivery.storageDoor.position;}
            if (depot)
            {
                // The door the parcels go in by (the worker walks into it northwards in the scene), in the depot's frame.
                doorLocal = depot.InverseTransformPoint(storageDoor);
                doorInLocal = depot.InverseTransformDirection(Vector3.forward);
                StorageDoor = storageDoor;
            }
            string[] interior = { "Building", "Checkout", "Bakery", "Butcher", "Fishery", "Produce", "Groceries", "Owned Shelf Slots", "Sector Construction" };
            foreach (Transform child in world)
            {
                bool actor = child.name.StartsWith("Worker_") && child.name != "Worker_Delivery";
                if (interior.Contains(child.name) || child.name.StartsWith("Sector_") || child.name.StartsWith("Stock_") || child.name.StartsWith("ReplacementVisual") || child.name.StartsWith("Anim_Door") || actor)
                    placements.Add(new Placement { root = child, position = child.position, scale = child.localScale, resize = !actor });
            }
            foreach (var child in world.GetComponentsInChildren<Transform>(true))
            {
                if (child.name.StartsWith("Parking bay") || child.name == "Parking wheel stop") parkingDetails.Add(child.gameObject);
                if (child.name.StartsWith("Banco ")) premiumDetails.Add(child.gameObject);
                // The park trees stand where the lot houses are until the park is bought.
                if (child.name.StartsWith("City Tree 03")) premiumDetails.Add(child.gameObject);
                if (child.name.StartsWith("Loading garden flowers")) premiumDetails.Add(child.gameObject);
                if (child.name.StartsWith("Entrance flowers")) placements.Add(new Placement { root=child,position=child.position,scale=child.localScale,resize=true });
                if (child.parent && child.parent.name=="Clean entrance frame") placements.Add(new Placement { root=child,position=child.position,scale=child.localScale,resize=true });
                if (child.parent&&child.parent.name=="Supplied Delivery Cargo"&&child.name!="Carried cardboard box"&&child.name!="Warehouse delivery doorstep") storageDetails.Add(child.gameObject);
            }
            // The pallets and boxes by the depot door go wherever the depot goes.
            if (depot) foreach (var detail in storageDetails) depotFollowers.Add((detail.transform, depot.InverseTransformPoint(detail.transform.position), Quaternion.Inverse(depot.rotation) * detail.transform.rotation));
        }

        // The Editor expansion preview lets artists move objects while a projected layout is
        // active. Convert those edits back into the unprojected scene coordinates so changing
        // preview stages never loses them and the saved scene remains the runtime baseline.
        public bool CaptureEditorEdits()
        {
            if (!Application.isEditor || State == null) return false;
            bool changed = false;
            foreach (var placement in placements)
            {
                var root = placement.root;
                if (!root) continue;
                if ((root.position - placement.expectedPosition).sqrMagnitude < .000001f &&
                    (root.localScale - placement.expectedScale).sqrMagnitude < .000001f &&
                    Quaternion.Angle(root.rotation, placement.expectedRotation) < .05f) continue;

                var position = root.position;
                bool door = root.name.StartsWith("Anim_Door") || (root.parent && root.parent.name == "Clean entrance frame");
                if (door)
                {
                    float height = Mathf.Lerp(.9f, 1, Mathf.InverseLerp(.78f, 1, State.widthScale));
                    position.y = .63f + (position.y - .63f) / height;
                }
                placement.position = Unproject(position, State);
                if (door) placement.position.x = FrontDoorX + (position.x - Project(new Vector3(FrontDoorX, 0, 0), State).x) / Mathf.Max(.0001f, DoorScale(State));

                var projection = door ? new Vector3(DoorScale(State), 1, 1) : new Vector3(State.widthScale, 1, State.depthScale);
                var scaleAxes = placement.resize
                    ? new Vector3(Vector3.Scale(root.right, projection).magnitude,
                        Vector3.Scale(root.up, projection).magnitude,
                        Vector3.Scale(root.forward, projection).magnitude)
                    : Vector3.one;
                if (door)
                {
                    float height = Mathf.Lerp(.9f, 1, Mathf.InverseLerp(.78f, 1, State.widthScale));
                    var verticalScale = new Vector3(1, height, 1);
                    scaleAxes = Vector3.Scale(scaleAxes, new Vector3(
                        Vector3.Scale(root.right, verticalScale).magnitude,
                        Vector3.Scale(root.up, verticalScale).magnitude,
                        Vector3.Scale(root.forward, verticalScale).magnitude));
                }
                placement.scale = Divide(root.localScale, scaleAxes);
                changed = true;
            }

            if (changed)
            {
                signature = null;
                Apply(State);
            }
            return changed;
        }

        // Puts every projected object back on its unprojected (saved-scene) position. Editor tools call
        // this instead of applying a scale-1 layout, which is not the identity because of Offset.
        public void ResetToBase()
        {
            foreach (var placement in placements)
            {
                if (!placement.root) continue;
                placement.root.position = placement.position;
                placement.root.localScale = placement.scale;
            }
            signature = null;
        }

        public bool Apply(MarketLayout next)
        {
            // Older standalone fixtures can omit layout; the current app always sends it.
            next = next ?? new MarketLayout { stage = 4, storage = true, parking = true, loadingYard = true, premium = true };
            string key = JsonUtility.ToJson(next);
            if (signature == key) return false;
            signature = key;
            State = next;
            foreach (var placement in placements)
            {
                placement.root.position = Point(placement.position);
                if (IsDoor(placement.root)) { var d = placement.root.position; d.x = DoorPoint(placement.position.x, FrontDoorX, next); placement.root.position = d; }
                bool checkout = placement.root.name == "Checkout" || placement.root.name == "Worker_Cashier";
                if (checkout) placement.root.position = CheckoutPoint(placement.position, next);
                if (placement.resize)
                {
                    // FBX roots use different up axes. Resize in world X/Z without flattening their height.
                    var scale=IsDoor(placement.root)?new Vector3(DoorScale(next),1,1):new Vector3(next.widthScale,1,next.depthScale);
                    var axes=new Vector3(Vector3.Scale(placement.root.right,scale).magnitude,Vector3.Scale(placement.root.up,scale).magnitude,Vector3.Scale(placement.root.forward,scale).magnitude);
                    placement.root.localScale=Vector3.Scale(placement.scale,axes);
                }
                if (placement.root.name.StartsWith("Anim_Door") || (placement.root.parent && placement.root.parent.name=="Clean entrance frame"))
                {
                    float height = Mathf.Lerp(.9f, 1, Mathf.InverseLerp(.78f, 1, next.widthScale));
                    var axes = new Vector3(Vector3.Scale(placement.root.right,new Vector3(1,height,1)).magnitude,Vector3.Scale(placement.root.up,new Vector3(1,height,1)).magnitude,Vector3.Scale(placement.root.forward,new Vector3(1,height,1)).magnitude);
                    placement.root.localScale = Vector3.Scale(placement.root.localScale,axes);
                    var p = placement.root.position; p.y = .63f + (p.y - .63f) * height; placement.root.position = p;
                }
                placement.expectedPosition = placement.root.position;
                placement.expectedScale = placement.root.localScale;
                placement.expectedRotation = placement.root.rotation;
            }
            foreach (var progress in world.GetComponentsInChildren<CheckoutSectorProgress>(true)) progress.RebaseHomes();
            bool grand = next.storageLarge;
            bool oldYard = next.loadingYard && !grand;
            PlaceDepot(next);
            SetActive("Warehouse", next.storage && !grand);
            SetActive(GrandWarehouse, grand);
            // The lots have their own ruins now (CheckoutLotSites): the old "future warehouse" dressing goes.
            SetActive(GrandWarehouseSite, false);
            SetActive(GrandYard, grand);
            SetActive("Loading Yard Details", oldYard);
            SetActive("Expansion Park", next.premium);
            if (shell) shell.Apply(next);
            if (dressing) dressing.Apply(this, next.stage, holdNewDressing);
            holdNewDressing = false;
            // The supermarket's flags and totem stood by the east wall, on lot C2 (now the depot) and later on the car
            // park and the cycle lane: they stand on the shop's own forecourt instead, between the entrance steps and
            // the east corner, a little back from the sidewalk. The flags turn to run along the facade.
            {
                float east = Point(new Vector3(9.4f, 0, 0)).x, z = WorldAnchor.z + 1.35f;
                bool forecourt = next.stage >= 2 && next.stage <= 3;
                Settle("Market Stage Dressing/S2 flags", forecourt, new Vector3(east - 5.2f, .13f, z), Quaternion.Euler(0, 90, 0));
                Settle("Market Stage Dressing/S2 totem", forecourt, new Vector3(east - 1.25f, .13f, z), null);
            }
            if (neighborhood) neighborhood.Apply(next);
            foreach(var renderer in FindObjectsByType<UnityEngine.Tilemaps.TilemapRenderer>())
            {
                if(!renderer.sharedMaterial||renderer.sharedMaterial.shader.name!="MarketDay/City Tiles")continue;
                var properties=new MaterialPropertyBlock();renderer.GetPropertyBlock(properties);
                var center=Point(Vector3.zero);
                properties.SetFloat("_ExpansionProjection",1);
                // The service driveway across the north sidewalk only exists once the loading yard is bought.
                properties.SetFloat("_LoadingAccessEnabled",oldYard?1:0);
                properties.SetFloat("_GrandYardEnabled",grand?1:0);
                // The parking bays are drawn on lot C1 or C3 (BuildGround), not painted by the tiles any more.
                properties.SetFloat("_ParkingSpaces",0);
                // The tiles' own car park (west of the entrance, from before the lots) stays off: BuildGround draws it.
                properties.SetVector("_ExpansionFeatures",new Vector4(next.storage?1:0,0,oldYard?1:0,next.premium?1:0));
                properties.SetVector("_MarketFootprint",new Vector4(center.x,center.z,9.4f*next.widthScale,7.4f*next.depthScale));
                renderer.SetPropertyBlock(properties);
            }
            foreach (var detail in parkingDetails) detail.SetActive(false);
            var parking=world.GetComponentInChildren<CheckoutParkingSpaces>(true);
            if(parking)parking.Apply(0);
            var lot = next.stage >= 3 ? CheckoutCityTraffic.ParkingLot.Back : CheckoutCityTraffic.ParkingLot.Front;
            if (lot != CheckoutCityTraffic.Lot && traffic) traffic.ResetVisits();
            CheckoutCityTraffic.Lot = lot;
            BuildGround(next);
            foreach (var detail in premiumDetails) detail.SetActive(next.premium);
            foreach (var detail in storageDetails) detail.SetActive(next.storage && !grand);
            // Where the suppliers' trucks unload and the delivery worker's walk (CheckoutDeliveryTrucks).
            if (CheckoutDeliveryTrucks.Current) CheckoutDeliveryTrucks.Current.Configure(this, next);
            if (traffic)
            {
                if (!next.parking) traffic.ResetVisits();
                traffic.enabled = next.parking;
                traffic.Capacity=CheckoutCityTraffic.Bays;
            }
            var cashier = world.Find("Worker_Cashier")?.GetComponent<CheckoutCashier>();
            if (cashier) { cashier.beltStart = CheckoutPoint(new Vector3(-4.65f, 1.57f, -4.7f),next); cashier.beltEnd = CheckoutPoint(new Vector3(-3.25f, 1.57f, -4.7f),next); }
            simulation.GetComponent<MarketAmbientLife>()?.RebaseDoors();
            return true;
        }

        // ------------------------------------------------------------------ depot
        // The supermarket's depot stands on lot C2, beside the shop: turned so its stairs face the shop across a
        // corridor (the clerks come round from the shop's rear ramp) and its roller door faces the truck bay on the
        // south side of the lot. Later stages without the central warehouse keep it behind the shop, on lot B3.
        Transform depot; Vector3 depotBasePosition; Quaternion depotBaseRotation;
        Vector3 doorLocal, doorInLocal = Vector3.back;
        readonly List<(Transform t, Vector3 p, Quaternion r)> depotFollowers = new List<(Transform, Vector3, Quaternion)>();
        public const float DepotWest = 7.25f, DepotNorth = 17.9f;
        /// <summary>Where parcels go into the depot, and the direction one walks in through it.</summary>
        public Vector3 StorageDoor { get; private set; }
        public Vector3 StorageFacing { get; private set; } = Vector3.forward;
        /// <summary>True while the depot stands beside the shop (lot C2) instead of behind it.</summary>
        public static bool StorageBeside { get; private set; }
        public Vector3[] SceneDeliveryRoute => deliveryRoute;

        void PlaceDepot(MarketLayout next)
        {
            if (!depot) return;
            bool beside = next.storage && !next.storageLarge && next.stage <= 2;
            StorageBeside = beside;
            if (beside)
            {
                depot.rotation = Quaternion.Euler(0, 90, 0) * depotBaseRotation;
                depot.position = depotBasePosition;
                var b = MeshBounds(depot);
                depot.position += new Vector3(DepotWest - b.min.x, 0, DepotNorth - b.max.z);
            }
            else { depot.rotation = depotBaseRotation; depot.position = depotBasePosition + new Vector3(.9f, 0, 0); }
            foreach (var f in depotFollowers) if (f.t) f.t.SetPositionAndRotation(depot.TransformPoint(f.p), depot.rotation * f.r);
            var door = depot.TransformPoint(doorLocal); door.y = storageDoor.y; StorageDoor = door;
            var into = depot.TransformDirection(doorInLocal); into.y = 0; StorageFacing = into.sqrMagnitude > .01f ? into.normalized : Vector3.forward;
        }

        // World bounds of a model's meshes, also while it is hidden.
        static Bounds MeshBounds(Transform root)
        {
            bool first = true; var box = new Bounds(root.position, Vector3.zero);
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
            {
                // Only what is drawn (the model carries a few switched-off helper meshes).
                var renderer = mf.GetComponent<MeshRenderer>();
                if (!mf.sharedMesh || !renderer || !renderer.enabled || renderer.forceRenderingOff || !mf.gameObject.activeSelf) continue;
                var b = mf.sharedMesh.bounds;
                for (int i = 0; i < 8; i++)
                {
                    var c = mf.transform.TransformPoint(new Vector3((i & 1) == 0 ? b.min.x : b.max.x, (i & 2) == 0 ? b.min.y : b.max.y, (i & 4) == 0 ? b.min.z : b.max.z));
                    if (first) { box = new Bounds(c, Vector3.zero); first = false; } else box.Encapsulate(c);
                }
            }
            return box;
        }

        void Move(string path, Vector3 position) { var t = world.Find(path); if (t) t.position = position; }
        // A dressing piece put somewhere else than its projected spot: its parts' centre lands on `centre` (turned to
        // `turn` when given); otherwise it keeps the spot CheckoutStageDressing gave it and its own rotation.
        readonly Dictionary<Transform, Quaternion> dressingTurns = new Dictionary<Transform, Quaternion>();
        void Settle(string path, bool moved, Vector3 centre, Quaternion? turn)
        {
            var t = world.Find(path); if (!t) return;
            if (!dressingTurns.ContainsKey(t)) dressingTurns[t] = t.rotation;
            t.rotation = moved && turn.HasValue ? turn.Value : dressingTurns[t];
            if (!moved) return;
            // Mean of the parts' pivots (valid while the piece is still hidden for the construction reveal).
            var renderers = t.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length == 0) { t.position = centre; return; }
            var mean = Vector3.zero; foreach (var r in renderers) mean += r.transform.position; mean /= renderers.Length;
            var shift = centre - mean; shift.y = 0; t.position += shift;
        }

        // ------------------------------------------------------------------ parking lot and truck yard
        // Asphalt, bay lines and the driveways over the sidewalks: the supermarket's car park on lot C1 (in from the
        // avenue, bays on both sides of the aisle) with its depot's truck bay on the south edge of lot C2 (in from the
        // east street); the hypermarket's car park on lot C3 (in from the east street, bays towards the back of the
        // block). CheckoutCityTraffic drives the cars, CheckoutDeliveryTrucks the trucks.
        GameObject parkingLot; string groundKey; Material asphalt, stripes, yellow;
        readonly List<GameObject> parkingHidden = new List<GameObject>();
        List<Rect> lotAreas = new List<Rect>();
        float lotCheck;
        // Map-design pieces (copies and moved scene objects: a bike rack, a lamp) standing on the car park or a truck
        // yard wait hidden while it is one. The map design re-applies itself after the layout (stage changes), so
        // this runs again every second, not only when the ground is rebuilt. Where a piece stands is the mean of its
        // parts' pivots, which stays valid while it is hidden.
        void ClearLots()
        {
            if (CheckoutMapEditor.Open) return;
            bool On(Transform t)
            {
                var rs = t.GetComponentsInChildren<Renderer>(true);
                var p = t.position;
                if (rs.Length > 0) { p = Vector3.zero; foreach (var r in rs) p += r.transform.position; p /= rs.Length; }
                var q = new Vector2(p.x, p.z);
                return lotAreas.Exists(r => r.Contains(q));
            }
            // Pieces that moved off the lot (the design was reverted) come back.
            for (int i = parkingHidden.Count - 1; i >= 0; i--)
            {
                var go = parkingHidden[i];
                if (!go) { parkingHidden.RemoveAt(i); continue; }
                if (!On(go.transform)) { go.SetActive(true); parkingHidden.RemoveAt(i); }
            }
            if (lotAreas.Count == 0) return;
            void Hide(Transform t) { if (t && t.gameObject.activeSelf && On(t)) { t.gameObject.SetActive(false); parkingHidden.Add(t.gameObject); } }
            var design = CheckoutDesignWorld.Active;
            if (!design) return;
            if (design.CloneRoot) foreach (Transform child in design.CloneRoot) Hide(child);
            foreach (var o in design.Overrides) if (o != null && !o.hidden) Hide(CheckoutMapDesign.Find(o.path));
        }
        void LateUpdate()
        {
            if (Time.unscaledTime < lotCheck) return;
            lotCheck = Time.unscaledTime + 1;
            if (lotAreas.Count > 0 || parkingHidden.Count > 0) ClearLots();
        }
        void BuildGround(MarketLayout next)
        {
            bool show = next.parking, depotYard = next.storage && !next.storageLarge && next.stage <= 2, grandYard = next.storageLarge;
            string key = show + ":" + CheckoutCityTraffic.Lot + ":" + depotYard + ":" + grandYard;
            if (key == groundKey) return;
            groundKey = key;
            if (parkingLot) Destroy(parkingLot);
            parkingLot = null;
            foreach (var go in parkingHidden) if (go) go.SetActive(true);
            parkingHidden.Clear();
            lotAreas = new List<Rect>();
            if (!show && !depotYard && !grandYard) return;
            parkingLot = new GameObject("Market parking lot"); parkingLot.transform.SetParent(world, false);
            if (!asphalt) { asphalt = new Material(Shader.Find("Standard")) { color = new Color(.25f, .26f, .28f) }; asphalt.SetFloat("_Glossiness", .05f); }
            if (!stripes) { stripes = new Material(Shader.Find("Standard")) { color = new Color(.95f, .94f, .88f) }; stripes.SetFloat("_Glossiness", .05f); }
            if (!yellow) { yellow = new Material(Shader.Find("Standard")) { color = new Color(.96f, .76f, .2f) }; yellow.SetFloat("_Glossiness", .05f); }
            void Quad(float x0, float z0, float x1, float z1, float y, Material m)
            {
                var q = GameObject.CreatePrimitive(PrimitiveType.Cube); Destroy(q.GetComponent<Collider>());
                q.transform.SetParent(parkingLot.transform, false);
                q.transform.position = new Vector3((x0 + x1) * .5f, y, (z0 + z1) * .5f);
                q.transform.localScale = new Vector3(Mathf.Abs(x1 - x0), .02f, Mathf.Abs(z1 - z0));
                q.GetComponent<Renderer>().sharedMaterial = m;
            }
            const float ground = .19f, line = .205f, w = .1f;
            // Map-design decorations standing on the asphalt (a bike rack, a lamp) wait while it is a car park or a yard.
            var areas = new List<Rect>();
            if (show) areas.Add(CheckoutCityTraffic.Lot == CheckoutCityTraffic.ParkingLot.Back ? Rect.MinMaxRect(5.95f, 20.9f, 17.1f, 28.35f) : Rect.MinMaxRect(5.95f, -8.35f, 17.1f, 4.6f));
            if (show && CheckoutCityTraffic.Lot != CheckoutCityTraffic.ParkingLot.Back) areas.Add(Rect.MinMaxRect(9.6f, -12.6f, 12.8f, -8.3f)); // its driveway
            if (depotYard) areas.Add(Rect.MinMaxRect(5.75f, 4.5f, 17.25f, 18f));
            if (grandYard) areas.Add(Rect.MinMaxRect(-.5f, 28.3f, 17.25f, 39f));
            lotAreas = areas;
            ClearLots();
            if (show && CheckoutCityTraffic.Lot == CheckoutCityTraffic.ParkingLot.Back)
            {
                Quad(5.95f, 20.9f, 17.1f, 28.35f, ground, asphalt);
                Quad(17.1f, 20.6f, 21.3f, 23.4f, ground + .01f, asphalt);          // driveway over the east sidewalk
                for (int i = 0; i <= CheckoutCityTraffic.Bays; i++)
                {
                    float x = CheckoutCityTraffic.Bay(Mathf.Min(i, CheckoutCityTraffic.Bays - 1)).x + (i == CheckoutCityTraffic.Bays ? 1.15f : -1.15f);
                    Quad(x - w * .5f, 23.7f, x + w * .5f, 28.1f, line, stripes);
                }
                Quad(5.95f + .3f, 28.1f, 17.1f - .3f, 28.2f, line, stripes);
            }
            else if (show)
            {
                Quad(5.95f, -8.35f, 17.1f, 4.6f, ground, asphalt);
                Quad(9.9f, -12.5f, 12.5f, -8.35f, ground + .01f, asphalt);         // driveway over the avenue sidewalk
                // Bays on both sides of the aisle (x 11.2), noses towards the lot's edges; the spare one by the
                // driveway is painted too.
                var bays = new List<Vector3>();
                for (int i = 0; i < CheckoutCityTraffic.Bays; i++) bays.Add(CheckoutCityTraffic.Bay(i));
                bays.Add(new Vector3(CheckoutCityTraffic.FrontWestBayX, 0, CheckoutCityTraffic.BayZ(0)));
                foreach (var bay in bays)
                {
                    bool eastRow = bay.x > CheckoutCityTraffic.FrontAisleX;
                    float x0 = eastRow ? 13.9f : 6.1f, x1 = eastRow ? 17.0f : 9.2f, end = eastRow ? 16.95f : 6.05f;
                    Quad(x0, bay.z - 1.3f - w * .5f, x1, bay.z - 1.3f + w * .5f, line, stripes);
                    Quad(x0, bay.z + 1.3f - w * .5f, x1, bay.z + 1.3f + w * .5f, line, stripes);
                    Quad(end, bay.z - 1.3f, end + w, bay.z + 1.3f, line, stripes);
                }
            }
            if (depotYard)
            {
                // The depot's truck bay along the south edge of lot C2, joined to the east street by a driveway.
                float z0 = CheckoutDeliveryTrucks.DepotDriveZ0, z1 = CheckoutDeliveryTrucks.DepotDriveZ1;
                Quad(5.95f, show ? 4.6f : z0, 17.1f, z1 + .1f, ground, asphalt);
                Quad(17.1f, z0, 21.3f, z1, ground + .01f, asphalt);
                Quad(17.1f, z0, 21.3f, z0 + .1f, line, stripes);
                Quad(17.1f, z1 - .1f, 21.3f, z1, line, stripes);
                // Yellow box of the loading bay.
                float bx0 = CheckoutDeliveryTrucks.DepotRearX - .3f, bx1 = CheckoutDeliveryTrucks.DepotRearX + 6.2f, bz0 = CheckoutDeliveryTrucks.DepotTruckZ - 1.45f, bz1 = CheckoutDeliveryTrucks.DepotTruckZ + 1.45f;
                Quad(bx0, bz0, bx1, bz0 + w, line, yellow); Quad(bx0, bz1 - w, bx1, bz1, line, yellow);
                Quad(bx0, bz0, bx0 + w, bz1, line, yellow);
                for (float x = bx0 + 1.2f; x < bx1 - .6f; x += 1.2f) Quad(x, bz0 + .2f, x + .35f, bz0 + .45f, line, yellow);
            }
        }

        public const string GrandWarehouse = "Warehouse Large", GrandWarehouseSite = "Abandoned Warehouse (future expansion)", GrandYard = "Grand Loading Yard";

        void SetActive(string path, bool active) { var root = world.Find(path); if (root) root.gameObject.SetActive(active); }

        public static Vector3 Unproject(Vector3 point, MarketLayout layout)
        {
            var size = new Vector3(Mathf.Max(.0001f, layout.widthScale), 1, Mathf.Max(.0001f, layout.depthScale));
            return Anchor + Vector3.Scale(point - Anchor - Offset, new Vector3(1 / size.x, 1, 1 / size.z));
        }

        static Vector3 Divide(Vector3 value, Vector3 divisor) => new Vector3(
            value.x / Mathf.Max(.0001f, divisor.x),
            value.y / Mathf.Max(.0001f, divisor.y),
            value.z / Mathf.Max(.0001f, divisor.z));
    }
}
