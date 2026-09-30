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
        // The west wall (next to the parking aisle) stays put: the shop grows east towards the street and
        // north towards the yard. z -10.6 is where the entrance steps meet the sidewalk.
        public static readonly Vector3 Anchor = new Vector3(-9.4f, 0, -10.6f);
        // The whole shop sits 2.1 m further into the block than the supplied map, so the entrance steps
        // start at the back edge of the sidewalk instead of on the footway and the cycle lane.
        public static readonly Vector3 Offset = new Vector3(0, 0, 2.1f);
        public static Vector3 WorldAnchor => Anchor + Offset;
        public Vector3 Point(Vector3 point) => Project(point, State);
        public static Vector3 CheckoutPoint(Vector3 point, MarketLayout layout) => Project(point, layout);
        public static Vector3 Project(Vector3 point, MarketLayout layout)
        {
            return Anchor + Offset + Vector3.Scale(point - Anchor, new Vector3(layout.widthScale, 1, layout.depthScale));
        }
        public bool HasSector(string id) => State.sectorIds == null || Array.IndexOf(State.sectorIds, id) >= 0;

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
            delivery = world.GetComponentInChildren<MarketDeliveryWorker>(true);
            if(delivery){deliveryRoute=(Vector3[])delivery.route.Clone();storageDoor=delivery.storageDoor.position;}
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

                var projection = new Vector3(State.widthScale, 1, State.depthScale);
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
                bool checkout = placement.root.name == "Checkout" || placement.root.name == "Worker_Cashier";
                if (checkout) placement.root.position = CheckoutPoint(placement.position, next);
                if (placement.resize)
                {
                    // FBX roots use different up axes. Resize in world X/Z without flattening their height.
                    var scale=new Vector3(next.widthScale,1,next.depthScale);
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
            SetActive("Warehouse", next.storage && !grand);
            SetActive(GrandWarehouse, grand);
            SetActive(GrandWarehouseSite, !grand);
            SetActive(GrandYard, grand);
            SetActive("Loading Yard Details", oldYard);
            SetActive("Expansion Park", next.premium);
            if (shell) shell.Apply(next);
            if (dressing) dressing.Apply(this, next.stage, holdNewDressing);
            holdNewDressing = false;
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
                properties.SetFloat("_ParkingSpaces",next.parking?(next.stage>=3?5:3):0);
                properties.SetVector("_ExpansionFeatures",new Vector4(next.storage?1:0,next.parking?1:0,oldYard?1:0,next.premium?1:0));
                properties.SetVector("_MarketFootprint",new Vector4(center.x,center.z,9.4f*next.widthScale,7.4f*next.depthScale));
                renderer.SetPropertyBlock(properties);
            }
            foreach (var detail in parkingDetails) detail.SetActive(next.parking);
            var parking=world.GetComponentInChildren<CheckoutParkingSpaces>(true);
            if(parking)parking.Apply(next.parking?(next.stage>=3?5:3):0);
            foreach (var detail in premiumDetails) detail.SetActive(next.premium);
            foreach (var detail in storageDetails) detail.SetActive(next.storage && !grand);
            var grandPath = grand ? world.Find(GrandYard + "/Worker path") : null;
            if(delivery && grandPath && grandPath.childCount >= 2)
            {
                // Trucks unload at the dock of the central warehouse.
                var path = new Vector3[grandPath.childCount];
                for (int i = 0; i < path.Length; i++) path[i] = grandPath.GetChild(i).position;
                delivery.SetDestination(path[0], path);
            }
            else if(delivery)
            {
                // Before the warehouse is bought, parcels are delivered to the shop's rear door.
                var doorstep=next.storage?storageDoor:Point(new Vector3(CheckoutInterior.RearDoorX,.74f,6.65f));
                var rear=Point(new Vector3(CheckoutInterior.RearDoorX,.15f,8.9f));
                var route=next.storage?deliveryRoute:new[]{doorstep,rear,new Vector3(rear.x,.15f,16.19f),deliveryRoute[2],deliveryRoute[3]};
                delivery.SetDestination(doorstep,route);
            }
            if (traffic)
            {
                if (!next.parking) traffic.ResetVisits();
                traffic.enabled = next.parking;
                traffic.Capacity=next.stage>=3?5:3;
            }
            var cashier = world.Find("Worker_Cashier")?.GetComponent<CheckoutCashier>();
            if (cashier) { cashier.beltStart = CheckoutPoint(new Vector3(-4.65f, 1.57f, -4.7f),next); cashier.beltEnd = CheckoutPoint(new Vector3(-3.25f, 1.57f, -4.7f),next); }
            simulation.GetComponent<MarketAmbientLife>()?.RebaseDoors();
            return true;
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
