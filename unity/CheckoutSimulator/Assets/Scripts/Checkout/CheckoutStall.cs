using System.Collections.Generic;
using UnityEngine;
using MarketDay;

namespace Checkout
{
    // The first eras (0–4: mesinha, banca, tenda, contêiner, Späti) are not the market building: the player
    // sells from a small stall in front of lots B1/C1. While one of them is active the building, its
    // interior and the staff that belong to it are hidden, the shop floor leaves the navigation and the
    // customers browse the stall's crates and pay at it (CheckoutMap asks this class for those points).
    // Era models: Assets/Resources/CheckoutEras (made in Blender, ArtSource/Checkout_Workspace.blend).
    public class CheckoutStall : MonoBehaviour
    {
        /// <summary>A small era is on: the market building is hidden and customers use the stall.</summary>
        public static bool Small { get; private set; }
        public static int Era { get; private set; } = -1;

        // Stall centre on the paving where the building stands later (front faces the avenue, -Z).
        public static readonly Vector3 Centre = new Vector3(-1.2f, .1f, -4.9f);
        const float Scale = 1.2f;
        const float FrontZ = -7.15f;           // where shoppers stand to pick from the crates
        static readonly float[] CrateX = { -1.3f, -.65f, 0f, .65f, 1.3f }; // along the counter, from the centre

        Transform world; CheckoutMap map; MarketSimulation simulation;
        readonly Dictionary<string, GameObject> models = new Dictionary<string, GameObject>();
        readonly List<GameObject> hidden = new List<GameObject>();
        GameObject shown;

        public void Initialize(Transform root, CheckoutMap owner)
        {
            world = root; map = owner; simulation = FindAnyObjectByType<MarketSimulation>();
        }

        // ------------------------------------------------------------------ points for the customers
        public static Vector3 Entrance => new Vector3(-1.75f, .15f, -9.7f);
        public static Vector3 Crate(string id)
        {
            int i = Mathf.Abs((id ?? "").GetHashCode()) % CrateX.Length;
            return new Vector3(Centre.x + CrateX[i] * Scale, 1.1f, Centre.z - .4f);
        }
        public static Vector3 Approach(string id)
        {
            var crate = Crate(id);
            return new Vector3(crate.x, .15f, FrontZ);
        }
        public static Vector3 Register => new Vector3(Centre.x + 1.1f, .9f, Centre.z - .6f);
        public static Vector3 QueueSpot(int i)
        {
            // A short line from the cooler end of the stall towards the sidewalk.
            var p = new Vector3(Centre.x + 1.9f, .15f, FrontZ - .1f);
            if (i <= 0) return p;
            return i < 3 ? p + new Vector3(.25f * i, 0, -.85f * i) : p + new Vector3(.5f + .85f * (i - 2), 0, -1.7f);
        }
        public static Vector3 HelpSpot(int i) => new Vector3(Centre.x - 2.6f - .8f * (i % 3), .15f, FrontZ - .8f * (i / 3));

        /// <summary>Walkable paving in front of and around the stall while a small era is on.</summary>
        public static Bounds Court => new Bounds(new Vector3(-1.2f, .05f, -6.3f), new Vector3(10.5f, .2f, 6.4f));

        // ------------------------------------------------------------------ era switch
        public void Apply(Snapshot snapshot)
        {
            int era = snapshot?.era != null && !string.IsNullOrEmpty(snapshot.era.id) ? snapshot.era.index : 5;
            if (CheckoutMapEditor.Open) era = 5;
            bool small = era < 5;
            bool changed = small != Small;
            Era = era; Small = small;
            if (small) HideMarket();
            else if (changed) ShowMarket();
            ShowModel(small ? (era == 0 ? "Era0_Mesinha" : "Era1_Banca") : null);
            if (changed && simulation && map.Layout) simulation.RebuildLayoutNavigation(map.Layout.State);
        }

        static readonly string[] MarketRoots =
        {
            "Building", "Market Shell", "Market Stage Dressing", "Checkout", "Produce", "Butcher", "Fishery", "Bakery",
            "Groceries", "Owned Shelf Slots", "Sector Construction", "Anim_Door_Left", "Anim_Door_Right", "Market Staff",
            "Worker_Delivery", "Warehouse", "Loading Yard Details", "Supplied Delivery Cargo", "Delivery",
        };

        void Hide(GameObject go)
        {
            if (!go || !go.activeSelf) return;
            go.SetActive(false);
            if (!hidden.Contains(go)) hidden.Add(go);
        }

        void HideMarket()
        {
            foreach (var name in MarketRoots) { var t = world.Find(name); if (t) Hide(t.gameObject); else { var go = GameObject.Find(name); if (go) Hide(go); } }
            foreach (Transform t in world)
                if (t.name.StartsWith("Stock_") || t.name.StartsWith("ReplacementVisual") || t.name.StartsWith("Sector_") ||
                    t.name.StartsWith("Worker_") || t.name.StartsWith("Employee_") || t.name.StartsWith("Anim_Truck"))
                    Hide(t.gameObject);
            if (map.Interior && map.Interior.Holder) Hide(map.Interior.Holder.gameObject);
            // Shelf markers and click targets of the building live under the map object.
            foreach (Transform t in map.transform)
                if (t.name.StartsWith("Status ") || t.name.StartsWith("Open ") || t.name.StartsWith("Upgrade ")) Hide(t.gameObject);
        }

        void ShowMarket()
        {
            foreach (var go in hidden) if (go) go.SetActive(true);
            hidden.Clear();
            map.Reapply();
        }

        void ShowModel(string name)
        {
            if (shown && shown.name != name) { shown.SetActive(false); shown = null; }
            if (name == null) return;
            if (!models.TryGetValue(name, out var model))
            {
                model = Load(name);
                models[name] = model;
            }
            if (!model) return;
            model.SetActive(true);
            shown = model;
        }

        GameObject Load(string name)
        {
            var prefab = Resources.Load<GameObject>("CheckoutEras/" + name);
            if (!prefab) { Debug.LogWarning("CHECKOUT_STALL missing model CheckoutEras/" + name); return null; }
            var go = Instantiate(prefab, world);
            go.name = name;
            go.transform.SetPositionAndRotation(Centre, Quaternion.identity);
            // The Blender set is modelled in real metres; the game's characters are a bit taller than life.
            go.transform.localScale = Vector3.one * Scale;
            var texture = Resources.Load<Texture2D>("CheckoutEras/" + name + "_BaseColor");
            var material = new Material(Shader.Find("Standard")) { name = name + " (baked)" };
            if (texture) material.mainTexture = texture;
            material.SetFloat("_Glossiness", .12f);
            foreach (var r in go.GetComponentsInChildren<Renderer>(true))
            {
                var mats = r.sharedMaterials;
                for (int i = 0; i < mats.Length; i++) mats[i] = material;
                r.sharedMaterials = mats;
                r.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.On;
            }
            // Clicking the stall opens the playable checkout, like the register of the market.
            var click = new GameObject("Stall checkout");
            click.transform.SetParent(go.transform, false);
            click.transform.localPosition = new Vector3(1.25f, .8f, -.6f);
            click.AddComponent<BoxCollider>().size = new Vector3(1.2f, 1.6f, 1.2f);
            click.AddComponent<CheckoutTarget>().panel = "checkout";
            return go;
        }
    }
}
