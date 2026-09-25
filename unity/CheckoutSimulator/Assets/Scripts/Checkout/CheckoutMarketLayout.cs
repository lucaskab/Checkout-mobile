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
        public static readonly Vector3 Anchor = new Vector3(-1.75f, 0, -10.6f);
        public Vector3 Point(Vector3 point) => Project(point, State);
        public static Vector3 CheckoutPoint(Vector3 point, MarketLayout layout) => Project(point, layout) + new Vector3(-1.5f, 0, .2f) * Mathf.Clamp01((1 - layout.widthScale) / .22f);
        public static Vector3 Project(Vector3 point, MarketLayout layout)
        {
            return Anchor + Vector3.Scale(point - Anchor, new Vector3(layout.widthScale, 1, layout.depthScale));
        }
        public bool HasSector(string id) => State.sectorIds == null || Array.IndexOf(State.sectorIds, id) >= 0;

        public void Initialize(Transform root)
        {
            world = root;
            neighborhood = world.GetComponentInChildren<CheckoutExpansionNeighborhood>(true);
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
                bool checkout = root.name == "Checkout" || root.name == "Worker_Cashier";
                bool door = root.name.StartsWith("Anim_Door") || (root.parent && root.parent.name == "Clean entrance frame");
                if (door)
                {
                    float height = Mathf.Lerp(.9f, 1, Mathf.InverseLerp(.78f, 1, State.widthScale));
                    position.y = .63f + (position.y - .63f) / height;
                }
                if (checkout)
                {
                    position.x += 1.5f * Mathf.Clamp01((1 - State.widthScale) / .22f);
                    position.z -= .2f;
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
            SetActive("Warehouse", next.storage);
            SetActive("Loading Yard Details", next.loadingYard);
            SetActive("Expansion Park", next.premium);
            if (neighborhood) neighborhood.Apply(next);
            foreach(var renderer in FindObjectsByType<UnityEngine.Tilemaps.TilemapRenderer>())
            {
                if(!renderer.sharedMaterial||renderer.sharedMaterial.shader.name!="MarketDay/City Tiles")continue;
                var properties=new MaterialPropertyBlock();renderer.GetPropertyBlock(properties);
                var center=Point(Vector3.zero);
                properties.SetFloat("_ExpansionProjection",1);
                properties.SetFloat("_ParkingSpaces",next.parking?(next.stage>=3?5:3):0);
                properties.SetVector("_ExpansionFeatures",new Vector4(next.storage?1:0,next.parking?1:0,next.loadingYard?1:0,next.premium?1:0));
                properties.SetVector("_MarketFootprint",new Vector4(center.x,center.z,9.4f*next.widthScale,7.4f*next.depthScale));
                renderer.SetPropertyBlock(properties);
            }
            foreach (var detail in parkingDetails) detail.SetActive(next.parking);
            var parking=world.GetComponentInChildren<CheckoutParkingSpaces>(true);
            if(parking)parking.Apply(next.parking?(next.stage>=3?5:3):0);
            foreach (var detail in premiumDetails) detail.SetActive(next.premium);
            foreach (var detail in storageDetails) detail.SetActive(next.storage);
            if(delivery)
            {
                // Before the warehouse is bought, parcels are delivered to the shop's rear door.
                var doorstep=next.storage?storageDoor:Point(new Vector3(4,.74f,6.65f));
                var rear=Point(new Vector3(4,.15f,8.9f));
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

        void SetActive(string path, bool active) { var root = world.Find(path); if (root) root.gameObject.SetActive(active); }

        static Vector3 Unproject(Vector3 point, MarketLayout layout)
        {
            var size = new Vector3(Mathf.Max(.0001f, layout.widthScale), 1, Mathf.Max(.0001f, layout.depthScale));
            return Anchor + Vector3.Scale(point - Anchor, new Vector3(1 / size.x, 1, 1 / size.z));
        }

        static Vector3 Divide(Vector3 value, Vector3 divisor) => new Vector3(
            value.x / Mathf.Max(.0001f, divisor.x),
            value.y / Mathf.Max(.0001f, divisor.y),
            value.z / Mathf.Max(.0001f, divisor.z));
    }
}
